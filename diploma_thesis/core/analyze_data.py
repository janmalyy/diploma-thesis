import asyncio
import json
import os
import time
from collections import Counter
from pathlib import Path
from pprint import pprint

import numpy as np

from diploma_thesis.api.clinvar import (clinvar_efetch,
                                        clinvar_esearch_variant_ids,
                                        convert_pubmed_ids, extract_pubmed_ids)
from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import (Variant, prune_articles,
                                        remove_articles_with_no_match)
from diploma_thesis.core.run_llm import run_pipeline
from diploma_thesis.core.update_article_fulltext import \
    update_articles_fulltext
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import DATA_DIR, logger
from diploma_thesis.utils.helpers import end, get_unique_safe_filename


async def get_data_for_analysis(input_filename: str, results_dir: Path | str):
    """
    Run the whole pipeline and save the results per variant.
    Args:
        input_filename: The name of the file containing the variants to analyze
        (typically 100variants.txt or 15variants.txt).
        results_dir: The name of the directory where the JSON files with variant data will be saved.
    """
    with open(DATA_DIR / input_filename, "r", encoding="utf-8") as f:
        text = f.read()
    variants = text.split("\n")

    for i, variant in enumerate(variants):
        variant_info = {}
        start = time.time()
        if variant.split(" ")[2] == "p":
            variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "protein")
        else:
            variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "transcript")
        # variant = Variant("BRCA1", "A1623G", "protein")
        articles = parse_variomes_data(fetch_variomes_data(variant), variant)

        if not articles:
            logger.info(f"No articles found for this variant {variant.variant_string}.")
            variant_info = {
                "variant": variant.variant_string,
                "time_to_process_articles": end(start),
                "context_length": 0,
                "articles": [],
                "supplementary_files": [],
                "narrative_summary": "No relevant evidence found.",
                "structured_summary": {},
                "article_mentions": [],
                "analysis_token_counts": {},
            }
            with open(DATA_DIR / results_dir / get_unique_safe_filename(variant.variant_string), "w", encoding="utf-8") as f:
                json.dump(variant_info, f, indent=4)
            continue
        variant_info.update({"before_pruning": {
            "articles_in_total": len(articles),
            "only_medline_count": len([a for a in articles if a.data_sources == {"medline"}]),
            "only_pmc_count": len([a for a in articles if a.data_sources == {"pmc"}]),
            "only_suppl_count": len([a for a in articles if a.data_sources == {"suppl"}]),
            "both_pmc_and_suppl_count": len(
                [a for a in articles if a.data_sources == {"suppl", "pmc"}]),
            "all_three_count": len(
                [a for a in articles if a.data_sources == {"suppl", "pmc", "medline"}]),
        }
        })
        articles = prune_articles(articles)

        update_articles_fulltext(articles, variant)
        update_suppl_data(articles, variant)

        variant_info.update({"before_removing": {
            "articles_in_total": len(articles),
            "only_medline_count": len([a for a in articles if a.data_sources == {"medline"}]),
            "only_pmc_count": len([a for a in articles if a.data_sources == {"pmc"}]),
            "only_suppl_count": len([a for a in articles if a.data_sources == {"suppl"}]),
            "both_pmc_and_suppl_count": len(
                [a for a in articles if a.data_sources == {"suppl", "pmc"}]),
            "all_three_count": len(
                [a for a in articles if a.data_sources == {"suppl", "pmc", "medline"}]),
        }
        })
        articles = remove_articles_with_no_match(articles)

        variant_info.update({
            "variant": variant.variant_string,
            "time_to_process_articles": end(start),
            "context_length": len("\n".join(str(article.get_structured_context()) for article in articles)),
            "after_removal": {
                "articles_in_total": len(articles),
                "only_medline_count": len([a for a in articles if a.data_sources == {"medline"}]),
                "only_pmc_count": len([a for a in articles if a.data_sources == {"pmc"}]),
                "only_suppl_count": len([a for a in articles if a.data_sources == {"suppl"}]),
                "both_pmc_and_suppl_count": len(
                    [a for a in articles if a.data_sources == {"suppl", "pmc"}]),
                "all_three_count": len(
                    [a for a in articles if a.data_sources == {"suppl", "pmc", "medline"}]),
            },
            "articles":
                [
                    {
                        "pmid": a.pmid,
                        "pmcid": a.pmcid,
                        "data_sources": [source for source in a.data_sources],
                        "source_of_annotation": a.annotation_source,
                        "title_length": len(a.title),
                        "abstract_length": len(a.abstract),
                        "number_of_unmatched_snippets": len(a.fulltext_snippets),
                        "unmatched_snippets": [s.machine_comparable for s in a.fulltext_snippets],
                        "number_of_paragraphs": len(a.paragraphs),
                        "paragraphs_lengths": [len(p) for p in a.paragraphs],

                        "number_of_suppl_files": len(a.suppl_data_list),
                        "suppl_paragraphs_counts_per_file": [len(sd.paragraphs) for sd in a.suppl_data_list],
                        "suppl_paragraphs_lengths": [[len(str(p)) for p in sd.paragraphs] for sd in a.suppl_data_list],
                    }
                    for a in articles
                ],
        })
        # ------- LLM part ----------------------------

        pipeline_task = asyncio.create_task(
            run_pipeline(variant, articles)
        )
        final_result = await pipeline_task

        variant_info.update(
            final_result,
        )
        variant_info.update(
            {"total_time": end(start)}
        )
        # ---------------------------------------------
        with open(DATA_DIR / results_dir / get_unique_safe_filename(variant.variant_string), "w", encoding="utf-8") as f:
            json.dump(variant_info, f, indent=4)


def compute_and_print_stats(value: str, value_data: list, unit: str):
    print(f"------ {value} ------ in {unit} ------")
    value_data = [value for value in value_data if value is not None]
    if value_data:
        print(f"min: {min(value_data)}")
        print(f"max: {max(value_data)}")
        print(f"mean: {round(np.mean(value_data), 2)}")
        print(f"median: {round(np.median(value_data), 2)}")
        print(f"std: {round(np.std(value_data), 2)}")
        print(f"values_in_total: {len(value_data)}")
        print(f"values:\nhead: {value_data[:10]}\ntail: {value_data[-10:]}")
    print(value_data)
    print()


def analyze_data(filename: str):
    """print basic statistics about the data. Works with multiple variants in one JSON file."""
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    # data → variant → articles → paragraphs
    metrics = [
        ("articles_after_removal_per_variant", [v.get("articles_after_removal") for v in data], "just_number"),
        ("only_medline_articles_per_variant", [v.get("only_medline_count") for v in data], "just_number"),
        ("only_pmc_articles_per_variant", [v.get("only_pmc_count") for v in data], "just_number"),
        ("only_suppl_articles_per_variant", [v.get("only_suppl_count") for v in data], "just_number"),
        ("both_pmc_and_suppl_articles_per_variant", [v.get("both_pmc_and_suppl_count") for v in data], "just_number"),
        ("all_three_articles_per_variant", [v.get("all_three_count") for v in data], "just_number"),

        ("time_to_process_articles", [v.get("time_to_process_articles") for v in data], "seconds"),
        ("context_length", [v.get("context_length") for v in data], "characters"),

        ("title_length", [a.get("title_length") for v in data for a in v.get("articles", [])], "characters"),
        ("abstract_length", [a.get("abstract_length") for v in data for a in v.get("articles", [])], "characters"),

        ("number_of_unmatched_snippets",
         [a.get("number_of_unmatched_snippets", 0) for v in data for a in v.get("articles", [])
          if "pmc" in a["data_sources"]],
         "just_number"),

        ("number_of_paragraphs",
         [a.get("number_of_paragraphs", 0) for v in data for a in v.get("articles", [])
          if "pmc" in a["data_sources"]],
         "just_number"),

        ("paragraph_lengths",
         [p_len
          for v in data
          for a in v.get("articles", [])
          for p_len in a.get("paragraphs_lengths", [])
          ], "characters"),

        ("suppl_files_per_article",
         [a.get("number_of_suppl_files", 0) for v in data for a in v.get("articles", [])],
         "just_number"),

        ("suppl_paragraphs_per_file",
         [count
          for v in data
          for a in v.get("articles", [])
          for count in a.get("suppl_paragraphs_counts_per_file", [])
          if "suppl" in a["data_sources"]],
         "just_number"),

        ("suppl_paragraphs_lengths_per_variant",
         [p_len
          for v in data
          for a in v.get("articles", [])
          for file_lengths in a.get("suppl_paragraphs_lengths", [])
          for p_len in file_lengths
          ],
         "characters"),
    ]

    for value, value_data, unit in metrics:
        compute_and_print_stats(value, value_data, unit)


def compare_runs(paths: list[str], variant: str) -> dict:
    """
    Compares multiple analysis runs for a specific genetic variant.
    Used as a helper in compute_evaluation_consistency function.

    Args:
        paths: List of relative paths to JSON results.
        variant: The genetic variant identifier to compare.

    Returns:
        A dictionary containing counts and matching ratios across runs.
    """
    if len(paths) < 2:
        raise ValueError("At least two runs are required for comparison.")

    overall_pathogenicities = []

    runs_mentions = []
    article_ids_per_run = []

    for path in paths:
        with open(DATA_DIR / "15variants" / path, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        variant_data = result_data
        if variant_data is None:
            raise ValueError(f"Variant {variant} not found in file {path}.")

        overall_pathogenicities.append(variant_data.get("structured_summary").get("overall_pathogenicity"))

        id2mentions = {}
        current_run_article_ids = []

        for article in variant_data.get("article_mentions"):
            art_id = article["article_id"]
            current_run_article_ids.append(art_id)

            id2mentions[art_id] = [
                {
                    "quoted_text": ment["quoted_text"],
                    "mention_type": ment["mention_type"],
                    "claim": ment["claim"]
                }
                for ment in article.get("mentions")
            ]

        runs_mentions.append(id2mentions)
        article_ids_per_run.append(set(current_run_article_ids))
    common_article_ids = set()
    unique_articles_length = len(set.union(*article_ids_per_run))
    # 1. Ratio of articles in all runs / all unique articles
    common_article_ids = set.intersection(*article_ids_per_run)
    matching_articles_ratio = len(common_article_ids) / unique_articles_length

    # 2. Ratio of articles in all runs or at least all runs except one run / all unique articles
    all_article_counts = Counter([art_id for s in article_ids_per_run for art_id in s])
    pprint(all_article_counts)
    matching_articles_minus_one_ratio = sum(
        1 for count in all_article_counts.values() if count >= len(paths) - 1) / unique_articles_length

    # 3. Matching ratios for mention_types and claims
    total_matched_quotes = 0
    total_matched_types = 0
    total_matched_claims = 0

    mentions_per_run_list = [
        sum(len(run[art_id]) for art_id in common_article_ids)
        for run in runs_mentions
    ]
    if mentions_per_run_list:
        avg_mentions_per_run = sum(mentions_per_run_list) / len(mentions_per_run_list)
    else:
        avg_mentions_per_run = 0

    for art_id in common_article_ids:
        # We take Run 0 as the reference to match against others
        base_mentions = runs_mentions[0][art_id]

        for base_mention in base_mentions:
            matched_group = [base_mention]

            # Try to find a matching mention in all other runs (1 to N)
            for run_idx in range(1, len(runs_mentions)):
                for candidate_ment in runs_mentions[run_idx][art_id]:
                    if base_mention["quoted_text"] == candidate_ment["quoted_text"]:
                        matched_group.append(candidate_ment)
                        break
            if len(matched_group) == len(runs_mentions):
                total_matched_quotes += 1
                # Check the exact match for enums across all 5 runs
                if all(e["mention_type"] == matched_group[0]["mention_type"] for e in matched_group):
                    total_matched_types += 1
                if all(e["claim"] == matched_group[0]["claim"] for e in matched_group):
                    total_matched_claims += 1

    # Final ratios (prevent division by zero)
    if avg_mentions_per_run > 0:
        quoted_text_matching_ratio = total_matched_quotes / avg_mentions_per_run
        mention_types_matching_ratio = total_matched_types / avg_mentions_per_run
        claims_matching_ratio = total_matched_claims / avg_mentions_per_run
    else:
        quoted_text_matching_ratio = 0
        mention_types_matching_ratio = 0
        claims_matching_ratio = 0

    return {
        "matching_articles_ratio": round(matching_articles_ratio, 3),
        "matching_articles_minus_one_ratio": round(matching_articles_minus_one_ratio, 3),
        "overall_pathogenicities": overall_pathogenicities,
        "quoted_text_matching_ratio": round(quoted_text_matching_ratio, 3),
        "mention_types_matching_ratio": round(mention_types_matching_ratio, 3),
        "claims_matching_ratio": round(claims_matching_ratio, 3),
        "article_counts": all_article_counts.values(),
    }


def compare_ids(export_paths: list[str], variant_string: str):
    """compare which articles my tool uses versus which articles are cited in ClinVar for the variant."""
    if len(export_paths) < 2:
        raise ValueError("At least two runs are required for comparison.")

    article_ids_per_run = []
    for path in export_paths:
        with open(DATA_DIR / "results" / path, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        variant_data = next((v for v in result_data if v["variant"].upper() == variant_string.upper()), None)
        if variant_data is None:
            raise ValueError(f"Variant {variant_string} not found in file {path}.")

        current_run_article_ids = []

        for article in variant_data.get("article_mentions"):
            art_id = article["article_id"]
            current_run_article_ids.append(art_id)

        article_ids_per_run.append(set(current_run_article_ids))

    article_ids_in_tool = set.union(*article_ids_per_run)

    clinvar_ids = clinvar_esearch_variant_ids(variant_string)
    print("clinvar ids for the variant", clinvar_ids)
    root = clinvar_efetch(clinvar_ids)
    extracted = extract_pubmed_ids(root)
    print("extracted pubmed ids", extracted)
    article_ids_in_clinvar = convert_pubmed_ids(extracted)
    print("tool", article_ids_in_tool)
    print("clinvar", article_ids_in_clinvar)


def compute_rel_freq():
    """compute the relative frequency of the article's mean at the current stage
    compared to the total number of articles at that stage"""
    # todo opravit aby to bylo relative i vzhledem k velikosti prvního sloupce
    res = {
        "medline_before_pruning": [],
        "medline_before_removing": [],
        "medline_after_removal": [],
        "medline_with_evidences": [],
        "only_pmc_before_pruning": [],
        "only_pmc_before_removing": [],
        "only_pmc_after_removal": [],
        "only_pmc_with_evidences": [],
        "pmc_suppl_before_pruning": [],
        "pmc_suppl_before_removing": [],
        "pmc_suppl_after_removal": [],
        "pmc_suppl_with_evidences": [],
        "only_suppl_before_pruning": [],
        "only_suppl_before_removing": [],
        "only_suppl_after_removal": [],
        "only_suppl_with_evidences": [],
    }
    for filepath in os.listdir(DATA_DIR / "100variants"):
        with open(DATA_DIR / "100variants" / filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        res["medline_before_pruning"].append(data["before_pruning"]["only_medline_count"])
        res["medline_before_removing"].append(data["before_removing"]["only_medline_count"])
        res["medline_after_removal"].append(
            len([art for art in data["articles"] if art["data_sources"] == ["medline"]]))
        res["medline_with_evidences"].append(
            len([ment for ment in data["article_mentions"] if ment["data_sources"] == ["medline"]]))

        res["only_pmc_before_pruning"].append(data["before_pruning"]["only_pmc_count"])
        res["only_pmc_before_removing"].append(data["before_removing"]["only_pmc_count"])
        res["only_pmc_after_removal"].append(len([art for art in data["articles"] if art["data_sources"] == ["pmc"]]))
        res["only_pmc_with_evidences"].append(
            len([ment for ment in data["article_mentions"] if ment["data_sources"] == ["pmc"]]))

        res["pmc_suppl_before_pruning"].append(data["before_pruning"]["both_pmc_and_suppl_count"])
        res["pmc_suppl_before_removing"].append(data["before_removing"]["both_pmc_and_suppl_count"])
        res["pmc_suppl_after_removal"].append(len([art for art in data["articles"] if len(art["data_sources"]) == 2]))
        res["pmc_suppl_with_evidences"].append(
            len([ment for ment in data["article_mentions"] if len(ment["data_sources"]) == 2]))

        res["only_suppl_before_pruning"].append(data["before_pruning"]["only_suppl_count"])
        res["only_suppl_before_removing"].append(data["before_removing"]["only_suppl_count"])
        res["only_suppl_after_removal"].append(len([art for art in data["articles"] if art["data_sources"] == ["suppl"]]))
        res["only_suppl_with_evidences"].append(
            len([ment for ment in data["article_mentions"] if ment["data_sources"] == ["suppl"]]))

    mean_res = {}
    for key, value in res.items():
        mean_res[key] = np.mean(value)

    # for key, value in mean_res.items():
    #     print(key, value)

    count = {
        "before_pruning": sum([value for key, value in mean_res.items() if key.endswith("before_pruning")]),
        "before_removing": sum([value for key, value in mean_res.items() if key.endswith("before_removing")]),
        "after_removal": sum([value for key, value in mean_res.items() if key.endswith("after_removal")]),
        "with_evidences": sum([value for key, value in mean_res.items() if key.endswith("with_evidences")]),
    }
    # print("counts")
    # [print(key, value) for key, value in count.items()]
    # print()

    rel_mean_res = {}
    for key, value in mean_res.items():
        if key.startswith("medline"):
            rel_mean_res[key] = round((value / count[key.split("_")[1] + "_" + key.split("_")[2]]) * 100, 2)
        else:
            rel_mean_res[key] = round((value / count[key.split("_")[2] + "_" + key.split("_")[3]]) * 100, 2)
    return rel_mean_res


def compute_evaluation_consistency():
    from itertools import groupby

    folder_path = DATA_DIR / "15variants"
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    files.sort(key=lambda x: x[:10])
    res = {
        "matching_articles_ratio": [],
        "matching_articles_minus_one_ratio": [],
        "overall_pathogenicities": [],
        "quoted_text_matching_ratio": [],
        "mention_types_matching_ratio": [],
        "claims_matching_ratio": [],
        "article_counts": [],
    }
    for prefix, group in groupby(files, key=lambda x: x[:10]):
        file_list = list(group)
        # print(f"Group {prefix} contains: {file_list}")
        with open(folder_path / file_list[0], "r", encoding="utf-8") as f:
            variant = json.load(f)["variant"]
        if variant == "NTHL1 S5C":
            continue
        print("Variant", variant)
        compared = compare_runs(file_list, variant)
        print(compared)
        for key, value in compared.items():
            if key == "overall_pathogenicities":
                res[key].append(all(patho == value[0] for patho in value))
            res[key].append(value)
        print("________________________________________________________")

    for key, value in res.items():
        try:
            print(key, np.nanmean(value))
        except:
            continue


async def main():
    # filename = get_unique_safe_filename("100variants")
    results_dir = "100variants"
    res = await get_data_for_analysis("100variants.txt", results_dir)
    # analyze_data(results_path)


if __name__ == '__main__':
    pass

    # paths = [path for path in os.listdir(DATA_DIR / "results") if path.startswith("EPCAM")]
    # pprint(compare_runs(paths, "EPCAM c.556-14A>G"))
    # compare_ids(paths, "BRCA1 R7C")
    # compare_ids(paths, "EPCAM c.556-14A>G")
    # analyze_data(r"old\results_from_analyze_data\results_updated_ver8.json")

    # with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
    #     text = f.read()
    # variants = text.split("\n")
    # hundred_vars = random.choices(variants, k=100)
    # with open(DATA_DIR / "100variants.txt", "w", encoding="utf-8") as f:
    #     for var in hundred_vars:
    #         f.write(var + "\n")
