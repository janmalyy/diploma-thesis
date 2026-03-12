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
"""
import json
import time
from pathlib import Path

import numpy as np

from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import (Variant, prune_articles,
                                        remove_articles_with_no_match)
from diploma_thesis.core.update_article_fulltext import \
    update_articles_fulltext
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import DATA_DIR, logger


def end(start):
    return round(time.time() - start, 2)


def get_data_for_analysis(results_path: Path | str):
    with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
        text = f.read()
    variants = text.split("\n")

    to_be_json = []

    for i, variant in enumerate(variants[:20]):
        start = time.time()

        variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "protein")

        articles = parse_variomes_data(fetch_variomes_data(variant), variant)

        if not articles:
            logger.info(f"No articles found for this variant {variant.variant_string}.")
            variant_info = {
                "variant": variant.variant_string,
                "time_to_fetch_data": end(start),
                "context_length": 0,
                "articles": [],
                "supplementary_files": [],
            }
            to_be_json.append(variant_info)
            continue

        articles = prune_articles(articles)

        update_articles_fulltext(articles, variant)
        update_suppl_data(articles, variant)

        articles = remove_articles_with_no_match(articles)

        variant_info = {
            "variant": variant.variant_string,
            "time_to_fetch_data": end(start),
            "context_length": len("\n".join(article.get_context() for article in articles)),
            "articles_in_total": len(articles),
            "only_medline_count": len([a for a in articles if a.data_sources == {"medline"}]),
            "only_pmc_count": len([a for a in articles if a.data_sources == {"pmc"}]),
            "only_supp_count": len([a for a in articles if a.data_sources == {"supp"}]),
            "both_pmc_and_supp_count": len([a for a in articles if a.data_sources == {"supp", "pmc"}]),
            "all_three_count": len([a for a in articles if a.data_sources == {"supp", "pmc", "medline"}]),
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

                        "number_of_supp_files": len(a.suppl_data_list),
                        "supp_paragraphs_counts_per_file": [len(sd.paragraphs) for sd in a.suppl_data_list],
                        "supp_paragraphs_lengths": [[len(str(p)) for p in sd.paragraphs] for sd in a.suppl_data_list],
                    }
                    for a in articles
                ],
        }
        to_be_json.append(variant_info)

        if i % 10 == 0:
            logger.info(f"progress: {i / len(variants) * 100:.2f}%")

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
        ("articles_in_total_per_variant", [len(v.get("articles", [])) for v in data], "just_number"),
        ("only_medline_articles_per_variant", [v.get("only_medline_count") for v in data], "just_number"),
        ("only_pmc_articles_per_variant", [v.get("only_pmc_count") for v in data], "just_number"),
        ("only_supp_articles_per_variant", [v.get("only_supp_count") for v in data], "just_number"),
        ("both_pmc_and_supp_articles_per_variant", [v.get("both_pmc_and_supp_count") for v in data], "just_number"),
        ("all_three_articles_per_variant", [v.get("all_three_count") for v in data], "just_number"),

        ("time_to_fetch", [v.get("time_to_fetch_data") for v in data], "seconds"),
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

        ("supp_files_per_article",
         [a.get("number_of_supp_files", 0) for v in data for a in v.get("articles", [])],
         "just_number"),

        ("supp_paragraphs_per_file",
         [count
          for v in data
          for a in v.get("articles", [])
          for count in a.get("supp_paragraphs_counts_per_file", [])
          if "supp" in a["data_sources"]],
         "just_number"),

        ("supp_paragraphs_lengths_per_variant",
         [p_len
          for v in data
          for a in v.get("articles", [])
          for file_lengths in a.get("supp_paragraphs_lengths", [])
          for p_len in file_lengths
          ],
         "characters"),
    ]

    for value, value_data, unit in metrics:
        compute_and_print_stats(value, value_data, unit)


if __name__ == '__main__':
    results_path = DATA_DIR / "results_updated_ver4.json"
    # get_data_for_analysis(results_path)
    analyze_data(results_path)
