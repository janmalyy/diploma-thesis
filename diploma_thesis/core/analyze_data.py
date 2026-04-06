"""
vyberu si nějaké geny, k nim si stáhnu (a uložím) všechna data a chci zjistit:
- kolik najdu článků, kolik najdu suppl. files ve variomes
    - porovnat s LitVar2 ten počet - pro počet článků, bez SD, je to v článku https://academic.oup.com/bioinformatics/article/38/9/2595/6547047 v sekci 3.4.1
    - jak velký je typický kontext pro jednu variantu
    - jak dlouho trvá získat data k variantě
    - kolik se mi daří najít snippetů
    - jak velký jsou typicky suppl. data
    - kolik článků není v pubtatoru
- (porovnat kvalitu anotací pubtator vs variomes?)

udělám 5x a zajímá mě průnik přes všechny pokusy:
- jak se změní vybrané články
- jestli je někdy narrative summary chybný
overall_confidence exact match
overall_pathogenicity exact match
pomocí quoted text budu chtít srovnat evidences a chci exact match u evidenceType a Claim

"""
import asyncio
import json
import os
import time
from collections import Counter
from pathlib import Path
from pprint import pprint

import numpy as np

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


async def get_data_for_analysis(results_path: Path | str):
    # with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
    #     text = f.read()
    # variants = text.split("\n")

    to_be_json = []

    # for i, variant in enumerate(variants[:1]):
    variant_info = {}
    start = time.time()

    # variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "protein")
    variant = Variant("NOP10", "c.34G>C", "transcript")
    articles = parse_variomes_data(fetch_variomes_data(variant), variant)

    if not articles:
        logger.info(f"No articles found for this variant {variant.variant_string}.")
        variant_info = {
            "variant": variant.variant_string,
            "time_to_process_articles": end(start),
            "context_length": 0,
            "articles": [],
            "supplementary_files": [],
        }
        to_be_json.append(variant_info)
        # continue
    variant_info.update({"articles_before_pruning": len(articles)})
    articles = prune_articles(articles)

    update_articles_fulltext(articles, variant)
    update_suppl_data(articles, variant)

    variant_info.update({"articles_before_removing": len(articles)})
    articles = remove_articles_with_no_match(articles)

    variant_info.update({
        "variant": variant.variant_string,
        "time_to_process_articles": end(start),
        "context_length": len("\n".join(str(article.get_structured_context()) for article in articles)),
        "articles_after_removal": len(articles),
        "only_medline_count": len([a for a in articles if a.data_sources == {"medline"}]),
        "only_pmc_count": len([a for a in articles if a.data_sources == {"pmc"}]),
        "only_suppl_count": len([a for a in articles if a.data_sources == {"suppl"}]),
        "both_pmc_and_supplcount": len([a for a in articles if a.data_sources == {"suppl", "pmc"}]),
        "all_three_count": len([a for a in articles if a.data_sources == {"suppl", "pmc", "medline"}]),
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
    to_be_json.append(variant_info)

    # if i % 10 == 0:
    #     logger.info(f"progress: {i / len(variants) * 100:.2f}%")

    with open(DATA_DIR / results_path, "w", encoding="utf-8") as f:
        json.dump(to_be_json, f, indent=4)


def compute_and_print_stats(value: str, value_data: list, unit: str):
    print(f"------ {value} ------ in {unit} ------")
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

    Args:
        paths: List of relative paths to JSON results.
        variant: The genetic variant identifier to compare.

    Returns:
        A dictionary containing counts and matching ratios across runs.
    """
    if len(paths) < 2:
        raise ValueError("At least two runs are required for comparison.")

    overall_confidences = []
    overall_pathogenicities = []

    runs_mentions = []
    article_ids_per_run = []

    for path in paths:
        with open(DATA_DIR / "results" / path, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        variant_data = next((v for v in result_data if v["variant"].upper() == variant.upper()), None)
        if variant_data is None:
            raise ValueError(f"Variant {variant} not found in file {path}.")

        overall_pathogenicities.append(variant_data["structured_summary"]["overall_pathogenicity"])
        overall_confidences.append(variant_data["structured_summary"]["overall_confidence"])

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
    if article_ids_per_run:
        unique_articles_length = len(set.union(*article_ids_per_run))
        # 1. Ratio of articles in all runs / all unique articles
        common_article_ids = set.intersection(*article_ids_per_run)
        matching_articles_ratio = len(common_article_ids) / unique_articles_length

        # 2. Ratio of articles in all runs or at least all runs except one run / all unique articles
        all_article_counts = Counter([art_id for s in article_ids_per_run for art_id in s])
        pprint(all_article_counts)
        matching_articles_minus_one_ratio = sum(1 for count in all_article_counts.values() if count >= len(paths) - 1) / unique_articles_length
    else:
        matching_articles_ratio = 0
        matching_articles_minus_one_ratio = 0

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
        "overall_confidences": overall_confidences,
        "overall_pathogenicities": overall_pathogenicities,
        "quoted_text_matching_ratio": round(quoted_text_matching_ratio, 3),
        "mention_types_matching_ratio": round(mention_types_matching_ratio, 3),
        "claims_matching_ratio": round(claims_matching_ratio, 3),
    }


async def main():
    filename = get_unique_safe_filename("C34G>C")
    results_path = DATA_DIR / "results" / filename
    res = await get_data_for_analysis(results_path)
    # analyze_data(results_path)


if __name__ == '__main__':
    # for i in range(3):
    #     asyncio.run(main())
    paths = [path for path in os.listdir(DATA_DIR / "results") if path.startswith("NOP10")]
    pprint(compare_runs(paths, "NOP10 c.34G>C"))
