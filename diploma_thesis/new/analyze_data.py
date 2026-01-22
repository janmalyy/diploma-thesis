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

from diploma_thesis.new.models import Variant
from diploma_thesis.new.update_article_fulltext import update_articles_fulltext
from diploma_thesis.new.variomes import fetch_variomes_data
from diploma_thesis.settings import logger

with open("brca_variants.txt", "r", encoding="utf-8") as f:
    text = f.read()
variants = text.split("\n")

to_be_json = []
example = {
    "time_to_fetch_data": 0,
    "context_length": 0,        # nemám tam teď suppl data vůbec
    "variant": "",
    "articles": {
        "pmcid": "",
        "source_of_annotation": "",
        "title_length": 0,
        "abstract_length": 0,
        "number_of_snippets": 0,
        "number_of_found_paragraphs": 0,
        "paragraphs_lengths": []
    },
    "supplementary_files": {
        "pmcid": "",
        "source_of_annotation": "",
        "title_length": 0,
        "abstract_length": 0,
    },
}


def end(start):
    return round(time.time() - start, 2)


for i, variant in enumerate(variants):
    start = time.time()
    variant_info = {}
    if i == 3:
        break

    # 1. Initialize Variant (handles normalisation)
    variant = Variant(variant)

    # 2. Fetch Data from Variomes
    articles = fetch_variomes_data(variant)

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

    full_articles = [a for a in articles if a.snippets or a.paragraphs]
    supp_articles = [a for a in articles if not a.snippets]
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
                    "number_of_unmatched_snippets": len(a.snippets),
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
        logger.info(f"progress: {i / len(variants) * 100:.2f}%, time elapsed: {end(start):.2f} s.")

with open("results_updated_ver4.json", "w", encoding="utf-8") as f:
    json.dump(to_be_json, f, indent=4)
