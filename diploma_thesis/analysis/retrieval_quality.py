import json
import os

from diploma_thesis.api.clinvar import (clinvar_efetch, convert_pubmed_ids,
                                        extract_pubmed_ids)
from diploma_thesis.api.litvar import get_litvar_ids_for_query
from diploma_thesis.settings import DATA_DIR, logger


def get_model_output_ids() -> dict[str, list]:
    variant2ids = {}
    for path in os.listdir(DATA_DIR / "15variants_data_evaluated_by_molecular_geneticist"):
        article_ids = []
        with open(DATA_DIR / "15variants_data_evaluated_by_molecular_geneticist" / path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data = data[0]  # IMPORTANT! The data are stored as a list with one element

        variant = data["variant"]
        for article in data.get("article_mentions"):
            art_id = article["article_id"]
            article_ids.append(art_id)

        variant2ids[variant] = list(set(article_ids))

    return variant2ids


def get_clinvar_ids() -> dict[str, list]:
    variant2ids = {}

    # we have to do it manually because the clinvar efetch returns also non-matching variants
    variant2clinvar_ids = {
        "APC c.487C>T": [217991],
        "ATM c.829G>T": [234216],
        "BRCA1 R7C": [37440],
        "BARD1 c.1670G>C": [8045],
        "CDH1 c.8C>G": [142469],
        "EPCAM c.556-14A>G": [157603],
        "BRCA2 c.1141G>A": [91747],
        "MLH1 c.-42C>T": [89593],
        "MSH2 p.Met1Leu": [90834, 90832],
        "MSH6 p.D180D": [36597],
        "PALB2 G998E": [126699],
        "POLE A252V": [380210],
        "RAD51C c.577C>T": [140849],
        "TP53 c.666G>A": [187714]
    }
    for variant, clinvar_ids in variant2clinvar_ids.items():
        print("variant", variant)
        root = clinvar_efetch(variant, clinvar_ids)
        extracted = extract_pubmed_ids(root)
        article_ids = convert_pubmed_ids(extracted)
        print("converted", article_ids)
        variant2ids[variant] = article_ids

    return variant2ids


def get_litvar_ids() -> dict[str, list]:
    variant2ids = {}
    with open(DATA_DIR / "15variants.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]

    for line in lines:
        query = line.split(" ")[0] + " " + line.split(" ")[1]
        litvar_ids = get_litvar_ids_for_query(query)
        variant2ids[query] = litvar_ids

    return variant2ids


def compare_ids(model_output_ids: dict, clinvar_ids: dict, litvar_ids: dict):
    variant2all_ids = {}
    for variant, model_ids in model_output_ids.items():
        variant2all_ids[variant] = {
            "model_ids": model_ids,
            "clinvar_ids": clinvar_ids.get(variant, []),
            "litvar_ids": litvar_ids.get(variant, []),
        }
        logger.info(f"Variant {variant} successfully processed.")

    print(variant2all_ids)
    # recall_m_c = False


if __name__ == '__main__':
    model_output_ids = get_model_output_ids()
    clinvar_ids = get_clinvar_ids()
    litvar_ids = get_litvar_ids()
    compare_ids(model_output_ids, clinvar_ids, litvar_ids)
