import json
import os
from collections import Counter
from itertools import groupby
from pprint import pprint

import numpy as np
from statsmodels.stats import inter_rater as ir

from diploma_thesis.settings import DATA_DIR, logger


def compare_runs(paths: list[str], variant: str) -> dict:
    """
    Compares multiple analysis runs for a specific genetic variant.
    Used as a helper in the compute_evaluation_consistency function.

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

    quoted_text_matching_ratio = total_matched_quotes / avg_mentions_per_run

    return {
        "matching_articles_ratio": matching_articles_ratio,
        "matching_articles_minus_one_ratio": matching_articles_minus_one_ratio,
        "overall_pathogenicities": overall_pathogenicities,
        "quoted_text_matching_ratio": quoted_text_matching_ratio,
        "article_counts": list(all_article_counts.values()),
    }


def compute_fleiss_kappa(paths: list[str], attribute: str) -> float:
    """
    Computes Fleiss' Kappa for a specific attribute across multiple runs.

    Args:
        paths: List of relative paths to JSON results
        attribute: The key to evaluate (e.g., "mention_type" or "claim").

    Returns:
        The Fleiss' Kappa score.
    """
    if len(paths) < 2:
        raise ValueError("At least two runs are required for comparison.")

    runs_data = []
    for path in paths:
        with open(DATA_DIR / "15variants" / path, "r", encoding="utf-8") as f:
            runs_data.append(json.load(f))

    # 1. Identify common mentions across all runs using (article_id, quoted_text) as a key
    # We use a reference run (Run 0) to define the set of mentions to check
    ref_run = runs_data[0]

    # Pre-map all runs for O(1) lookup: run_idx -> article_id -> quoted_text -> label
    run_maps = []
    for run in runs_data:
        lookup = {}
        for art in run.get("article_mentions", []):
            art_id = art["article_id"]
            lookup[art_id] = {m["quoted_text"]: m.get(attribute) for m in art.get("mentions", [])}
        run_maps.append(lookup)

    # 2. Build the Raw Data Matrix (Mentions x Runs)
    raw_labels = []
    for art in ref_run.get("article_mentions", []):
        art_id = art["article_id"]
        for mention in art.get("mentions", []):
            q_text = mention["quoted_text"]

            # Check if this exact mention exists in ALL runs
            current_mention_labels = []
            exists_in_all = True

            for r_map in run_maps:
                label = r_map.get(art_id, {}).get(q_text)
                if label is None:
                    exists_in_all = False
                    break
                current_mention_labels.append(str(label))

            if exists_in_all:
                raw_labels.append(current_mention_labels)

    if not raw_labels:
        return np.nan

    # 3. Aggregate for statsmodels
    # aggregate_raters expects (n_subjects, n_raters)
    # returns (n_subjects, n_categories)
    # print("raw_labels", raw_labels)
    arr, categories = ir.aggregate_raters(raw_labels)
    # print("arr", arr)
    return ir.fleiss_kappa(arr, method="fleiss")


def compute_evaluation_consistency():

    folder_path = DATA_DIR / "15variants"
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    files.sort(key=lambda x: x[:10])
    res = {
        "matching_articles_ratio": [],
        "matching_articles_minus_one_ratio": [],
        "overall_pathogenicities": [],
        "quoted_text_matching_ratio": [],
        "mention_types_kappa": [],
        "claims_kappa": [],
        "article_counts": [],
    }
    for prefix, group in groupby(files, key=lambda x: x[:10]):
        file_list = list(group)
        print(f"Group {prefix} contains: {file_list}")
        with open(folder_path / file_list[0], "r", encoding="utf-8") as f:
            variant = json.load(f)["variant"]
        if variant == "NTHL1 S5C":
            continue
        print("Variant", variant)
        compared = compare_runs(file_list, variant)
        res["mention_types_kappa"].append(compute_fleiss_kappa(file_list, "mention_type"))
        res["claims_kappa"].append(compute_fleiss_kappa(file_list, "claim"))

        print("compared", compared)
        for key, value in compared.items():
            if key == "overall_pathogenicities":
                res[key].append(all(patho == value[0] for patho in value))
            res[key].append(value)
        print("________________________________________________________")

    for key, value in res.items():
        try:
            print(key, "mean", np.nanmean(value))
            print(key, "std", np.nanstd(value))
        except Exception as e:
            logger.exception("Error in computing mean/std", e)
            continue


if __name__ == '__main__':
    compute_evaluation_consistency()
