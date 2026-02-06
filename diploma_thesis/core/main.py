"""
todo ve variomes mají advanced filtry, ty bych taky asi mohl využít...

Workflow:
1. Normalise variant input. - nějak použít jejich synvar, umí to: https://sibils.org/synvar/
2. Fetch relevant literature data and fulltext_snippets from SIBiLS Variomes.        TODO improve check text for fulltext_snippets
    - if snippet not found, it is added to paragraphs as is
# TODO brát pmc ids aji z litvar2, ne jen z variomes
3. Retrieve full-text annotations from PubTator 3.
4. Fallback to BiodiversityPMC access if PubTator data is missing.
5. Intelligently shorten and filter context based on relevance (mocked).    TODO
6. Generate a concise summary using a LLM.                     TODO

Output:
- Article-level attributes: Study type, quality, disease.                   TODO
- Comprehensive variant summary.
"""
import time
from diploma_thesis.core.models import Variant
from diploma_thesis.api.local_llm import LLMSummarizer
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.core.update_article_fulltext import update_articles_fulltext
from diploma_thesis.api.variomes import fetch_variomes_data, parse_variomes_data
from diploma_thesis.settings import logger, DATA_DIR


def main():
    with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
        text = f.read()
    variants = text.split("\n")

    for i, variant in enumerate(variants[:1]):
        start_time = time.time()

        # 1. Initialize Variant (handles normalisation)
        variant = Variant("BRCA1", "A322P", "protein")
        logger.info(f"Processing variant: {variant}")

        # 2. Fetch Data from Variomes
        logger.info("Fetching data from SIBiLS Variomes...")
        data = fetch_variomes_data(variant)

        # 2b. Parse Data from Variomes
        articles = parse_variomes_data(data, variant)

        # raw_text = supp.get("text")
        # title = supp.get("title")
        # process_suppl_data(article, variant, raw_text, title)
        # print()

        if not articles:
            logger.info("No articles found for this variant.")
            return
        logger.info(f"Found {len(articles)} articles. IDs: {[a.pmcid if a.pmcid != "" else a.pmid for a in articles]}")

        # 3 & 4. Fetch Data from PubTator (with PMC fallback)
        logger.info("Fetching data from PubTator and PMC...")
        update_articles_fulltext(articles)

        # 4b. Parse Suppl. Data
        update_suppl_data(articles, variant)

        # 5. Shorten and Filter Context
        # logger.info("Processing and shortening context...")
        # for article in articles:
        #     article.shorten_context(max_length=200)

        # 6. Generate Summary
        print("\n" + "="*50)
        print("ARTICLE DETAILS")
        print("="*50)
        for article in articles:
            # print(f"  Study Type: {article.study_type}")
            # print(f"  Disease:    {article.disease}")
            # print(f"  Relevance:  {round(article.relevance_score, 2)}")
            # print("-" * 20)

            print(article.get_context())
            print("\n")
        # print("\n" + "="*50)
        # print("GENERATING LLM SUMMARY")
        # print("="*50)
        #
        # try:
        #     summarizer = LLMSummarizer()
        #     response_gen = summarizer.summarize(variant, articles, stream=True)
        #
        #     print(f"Summary for {variant}:")
        #     for chunk in response_gen:
        #         if 'content' in chunk['choices'][0]['delta']:
        #             token = chunk['choices'][0]['delta']['content']
        #             print(token, end="", flush=True)
        #     print("\n")
        #
        # except Exception as e:
        #     logger.error(f"\nLLM Summarization failed: {e}")

        end_time = time.time()
        logger.info(f"\nWorkflow completed in {round(end_time - start_time, 2)}s")


if __name__ == '__main__':
    main()
