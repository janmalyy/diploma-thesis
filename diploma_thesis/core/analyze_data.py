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
from diploma_thesis.core.models import Variant
from diploma_thesis.core.update_article_fulltext import update_articles_fulltext
from diploma_thesis.api.variomes import fetch_variomes_data, parse_variomes_data
from diploma_thesis.settings import logger, DATA_DIR


def end(start):
    return round(time.time() - start, 2)


def get_data_for_analysis(results_path: Path | str):
    with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
        text = f.read()
    variants = text.split("\n")

    to_be_json = []

    for i, variant in enumerate(variants[:10]):
        start = time.time()
        variant_info = {}

        # 1. Initialize Variant (handles normalisation)
        variant = Variant(variant)

        # 2. Fetch and Parse Data from Variomes
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
            continue

        # 3 & 4. Fetch Data from PubTator or BiodiversityPMC
        update_articles_fulltext(articles)

        full_articles = [a for a in articles if a.fulltext_snippets or a.paragraphs]
        supp_articles = [a for a in articles if not a.fulltext_snippets]
        variant_info = {
            "variant": variant.variant_string,
            "time_to_fetch_data": end(start),
            "context_length": len("\n".join(article.get_context() for article in articles)),
            "articles":
                [
                    {
                        "pmcid": a.pmcid,
                        "source_of_annotation": a.source,
                        "title_length": len(a.title),
                        "abstract_length": len(a.abstract),
                        "number_of_unmatched_snippets": len(a.fulltext_snippets),
                        "unmatched_snippets": [s.machine_comparable for s in a.fulltext_snippets],
                        "number_of_paragraphs": len(a.paragraphs),
                        "paragraphs_lengths": [len(p) for p in a.paragraphs]
                    }
                    for a in full_articles
                ],
            "supplementary_files":
                [
                    {
                        "pmcid": a.pmcid,
                        "source_of_annotation": a.source,
                        "title_length": len(a.title),
                        "abstract_length": len(a.abstract),
                    }
                    for a in supp_articles
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
    print()


def analyze_data(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    # data → variant → articles → paragraphs
    metrics = [
        ("articles_per_variant", [len(variant.get("articles")) for variant in data], "just_number"),
        ("supplementary_files_per_variant", [len(variant.get("supplementary_files")) for variant in data], "just_number"),
        ("time_to_fetch", [variant.get("time_to_fetch_data") for variant in data], "seconds"),
        ("context_length", [variant.get("context_length") for variant in data], "characters"),
        ("title_length", [article.get("title_length") for variant in data for article in variant.get("articles")+variant.get("supplementary_files")], "characters"),
        ("abstract_length", [article.get("abstract_length") for variant in data for article in variant.get("articles")+variant.get("supplementary_files")], "characters"),
        ("number_of_unmatched_snippets", [article.get("number_of_unmatched_snippets") for variant in data for article in variant.get("articles")], "just_number"),
        ("number_of_paragraphs", [article.get("number_of_paragraphs") for variant in data for article in variant.get("articles")], "just_number"),
        ("paragraph_lengths", [paragraph_length
                               for variant in data
                               for article in (variant.get("articles"))
                               for paragraph_length in (article.get("paragraphs_lengths"))
                               ], "characters")
    ]

    for value, value_data, unit in metrics:
        compute_and_print_stats(value, value_data, unit)


if __name__ == '__main__':
    results_path = DATA_DIR / "results_updated_ver3.json"
    get_data_for_analysis(results_path)
    analyze_data(results_path)
