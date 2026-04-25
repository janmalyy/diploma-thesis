import asyncio
import json
import time
from pathlib import Path

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

        # 100 variants
        variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "protein")

        # 15 variants
        # if variant.split(" ")[2] == "p":
        #     variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "protein")
        # else:
        #     variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "transcript")

        # single run
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


async def main():
    results_dir = "100variants"
    res = await get_data_for_analysis("100variants.txt", results_dir)


if __name__ == '__main__':
    asyncio.run(main())
