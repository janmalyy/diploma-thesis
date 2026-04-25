import json
import os

import numpy as np

from diploma_thesis.settings import DATA_DIR


def compute_and_print_stats(metric: str, value_data: list, unit: str):
    print(f"------ {metric} ------ in {unit} ------")
    value_data = [value for value in value_data if value is not None]
    if value_data:
        print(f"min: {min(value_data)}")
        print(f"max: {max(value_data)}")
        print(f"mean: {round(np.mean(value_data), 2)}")
        print(f"median: {round(np.median(value_data), 2)}")
        print(f"third quartile: {round(np.quantile(value_data, 0.75), 2)}")
        print(f"std: {round(np.std(value_data), 2)}")
        print(f"values_in_total: {len(value_data)}")
        print(f"values:\nhead: {value_data[:10]}\ntail: {value_data[-10:]}")
    print(value_data)
    print()


def analyze_data():
    """print basic statistics about the data. Works with multiple JSON files, each containing a single variant."""
    data = []
    for filename in os.listdir(DATA_DIR / "100variants"):
        with open(DATA_DIR / "100variants" / filename, "r", encoding="utf-8") as f:
            # Every file contains one dict with one variant
            data.append(json.load(f))

    # data → variant → articles → paragraphs
    metrics = [
        ("time_to_process_articles", [v.get("time_to_process_articles") for v in data if v.get("aggregation_token_count")], "seconds"),
        ("total_time", [v.get("total_time") for v in data if v.get("aggregation_token_count")], "seconds"),
        ("context_length", [v.get("context_length") for v in data], "characters"),
        ("analysis_input_token", [run["input"] for v in data for run in v.get("analysis_token_counts")], "tokens"),
        ("analysis_output_token", [run["output"] for v in data for run in v.get("analysis_token_counts")], "tokens"),
        ("aggregation_input_token", [v.get("aggregation_token_count")["input"] for v in data if v.get("aggregation_token_count")], "tokens"),
        ("aggregation_output_token", [v.get("aggregation_token_count")["output"] for v in data if v.get("aggregation_token_count")], "tokens"),

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

        ("suppl_paragraphs_per_article",
         [count
          for v in data
          for a in v.get("articles", [])
          for count in a.get("suppl_paragraphs_counts_per_file", [])
          if "suppl" in a["data_sources"] and count != [0] and count != 0],
         "just_number"),

        ("suppl_paragraphs_lengths",
         [p_len
          for v in data
          for a in v.get("articles", [])
          for file_lengths in a.get("suppl_paragraphs_lengths", [])
          for p_len in file_lengths
          if "suppl" in a["data_sources"] and p_len != [0] and p_len != 0
          ],
         "characters"),

        ("mentions_per_article",
         [len(article_mention["mentions"])
          for v in data
          for article_mention in v.get("article_mentions", [])],
         "just_number"),
    ]

    for value, value_data, unit in metrics:
        compute_and_print_stats(value, value_data, unit)


def compute_rel_freq():
    """
    Compute the relative frequency of the article's mean at the current stage
    compared to the total number of articles at that stage and the initial stage.

    Also prints the stats for the number of articles at each stage per data source and in total.
    """
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
        "total_before_pruning": [],
        "total_before_removing": [],
        "total_after_removal": [],
        "total_with_evidences": [],
    }

    folder_path = DATA_DIR / "100variants"
    for filepath in os.listdir(folder_path):
        with open(folder_path / filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extrakce dat pro jednotlivé fáze
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
        res["only_suppl_after_removal"].append(
            len([art for art in data["articles"] if art["data_sources"] == ["suppl"]]))
        res["only_suppl_with_evidences"].append(
            len([ment for ment in data["article_mentions"] if ment["data_sources"] == ["suppl"]]))

        res["total_before_pruning"].append(data["before_pruning"]["articles_in_total"])
        res["total_before_removing"].append(data["before_removing"]["articles_in_total"])
        res["total_after_removal"].append(data["after_removal"]["articles_in_total"])
        res["total_with_evidences"].append(len(data["article_mentions"]))

    for metric, value_data in res.items():
        compute_and_print_stats(metric, value_data, "just_number")

    # Výpočet průměrů pro každou metriku
    # from now on we do not continue with total values
    mean_res = {key: np.mean(value) for key, value in res.items()
                if not key.startswith("total_")}

    # Celkové počty článků v každé fázi (součet všech zdrojů)
    stage_totals = {
        "before_pruning": sum([v for k, v in mean_res.items() if k.endswith("before_pruning")]),
        "before_removing": sum([v for k, v in mean_res.items() if k.endswith("before_removing")]),
        "after_removal": sum([v for k, v in mean_res.items() if k.endswith("after_removal")]),
        "with_evidences": sum([v for k, v in mean_res.items() if k.endswith("with_evidences")]),
    }

    initial_total = stage_totals["before_pruning"]

    rel_mean_res = {}
    for key, value in mean_res.items():
        # Identifikace fáze z klíče
        current_stage = None
        for stage in stage_totals.keys():
            if key.endswith(stage):
                current_stage = stage
                break

        if current_stage:
            # Relativní podíl v rámci dané fáze (v %)
            rel_within_stage = (value / stage_totals[current_stage]) * 100 if stage_totals[current_stage] > 0 else 0

            # Relativní podíl vzhledem k úplnému začátku (v %)
            rel_to_initial = (value / initial_total) * 100 if initial_total > 0 else 0

            rel_mean_res[key] = {
                "rel_in_stage": round(rel_within_stage, 2),
                "rel_to_initial": round(rel_to_initial, 2),
                "absolute_mean": round(value, 2)
            }

    # Výpis výsledků
    for key, metrics in rel_mean_res.items():
        print(
            f"{key:40} | In Stage: {metrics['rel_in_stage']:6}% | To Initial: {metrics['rel_to_initial']:6}% | Abs: {metrics['absolute_mean']}")


if __name__ == '__main__':
    analyze_data()

    compute_rel_freq()

    # compute_evaluation_consistency()
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
