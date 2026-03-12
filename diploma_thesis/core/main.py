"""
todo ve variomes mají advanced filtry, ty bych taky asi mohl využít...

Workflow:
1. Normalise variant input. - SynVar
2. Fetch relevant literature data and fulltext_snippets from SIBiLS Variomes.        TODO improve check text for fulltext_snippets
    - if snippet not found, it is added to paragraphs as is
# TODO brát pmc ids aji z litvar2, ne jen z variomes
3. Retrieve full-text annotations from PubTator 3.
4. Fallback to BiodiversityPMC access if PubTator data is missing.
5. Intelligently shorten and filter context based on relevance (mocked).    TODO
6. Generate a concise summary using a LLM.

Output:
- Article-level attributes: Study type, quality, disease.
- Comprehensive variant summary.
"""
import asyncio
import time

from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import (Variant, prune_articles,
                                        remove_articles_with_no_match)
from diploma_thesis.core.run_llm import run_pipeline
from diploma_thesis.core.update_article_fulltext import \
    update_articles_fulltext
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import DATA_DIR, logger


async def main():
    with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
        text = f.read()
    variants = text.split("\n")

    for i, variant in enumerate(variants[:1]):
        start_time = time.time()

        # 1. Initialize Variant (handles normalisation)
        variant = Variant("BRCA1", "V11A", "protein")
        # variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "protein")
        logger.info(f"Processing variant: {variant}")

        # 2. Fetch Data from Variomes
        logger.info("Fetching data from SIBiLS Variomes...")
        data = fetch_variomes_data(variant)

        # 2b. Parse Data from Variomes
        articles = parse_variomes_data(data, variant)
        if not articles:
            logger.info("No articles found for this variant.")
            return
        logger.info(f"Found {len(articles)} articles. IDs: {[a.pmcid if a.pmcid != "" else a.pmid for a in articles]}")

        articles = prune_articles(articles)

        # 3. Fetch and Parse Data from PubTator and BiodiversityPMC
        logger.info("Fetching data from PubTator and BiodiversityPMC...")
        update_articles_fulltext(articles, variant)

        # 4. Parse Suppl. Data
        update_suppl_data(articles, variant)

        # 5. Shorten and Filter Context
        # logger.info("Processing and shortening context...")
        # for article in articles:
        #     article.shorten_context(max_length=200)
        articles = remove_articles_with_no_match(articles)

        print("\n" + "="*50)
        print("ARTICLE DETAILS")
        print("="*50)
        for article in articles:
            print(article.get_context())
            print("Annotation source:", article.annotation_source)
            print("\n")

        # 6. Generate Summary
        final_result = await run_pipeline(variant, articles)
        print(final_result)

        end_time = time.time()
        logger.info(f"\nWorkflow completed in {round(end_time - start_time, 2)}s")

if __name__ == '__main__':
    asyncio.run(main())
