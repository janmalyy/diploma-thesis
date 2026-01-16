"""
Workflow:
1. Normalise variant input.
2. Fetch relevant literature data and snippets from SIBiLS Variomes.
3. Retrieve full-text annotations from PubTator 3.
4. Fallback to direct PMC access if PubTator data is missing (mocked).
5. Intelligently shorten and filter context based on relevance (mocked).
6. Generate a concise summary using a LLM (BioMistral).

Output:
- Article-level attributes: Study type, quality, disease.
- Comprehensive variant summary.
"""
import time
from diploma_thesis.new.models import Variant
from diploma_thesis.new.variomes import VariomesProvider
from diploma_thesis.new.pubtator import PubTatorProvider
from diploma_thesis.new.llm_api import LLMSummarizer
from diploma_thesis.settings import logger


def main():
    start_time = time.time()
    
    # Configuration / Input
    variant_input = "NHP2	c.302G>A"
    logger.info(f"Processing variant: {variant_input}")
    
    # 1. Initialize Variant (handles normalisation)
    variant = Variant(variant_input)
    
    # 2. Fetch Data from Variomes
    logger.info("Fetching data from SIBiLS Variomes...")
    variomes = VariomesProvider()
    articles = variomes.fetch_data(variant)
    
    if not articles:
        logger.info("No articles found for this variant.")
        return
    logger.info(f"Found {len(articles)} articles. IDs: {[a.pmcid for a in articles]}")
    
    # 3 & 4. Fetch Annotations from PubTator (with PMC fallback)
    logger.info("Fetching annotations from PubTator...")
    pubtator = PubTatorProvider()
    pubtator.fetch_annotations(articles)
    
    # 5. Shorten and Filter Context
    logger.info("Processing and shortening context...")
    for article in articles:
        article.shorten_context(max_length=200)
    
    # 6. Generate Summary
    print("\n" + "="*50)
    print("ARTICLE DETAILS")
    print("="*50)
    for article in articles:
        print(f"[{article.pmcid}]")
        print(f"  Study Type: {article.study_type}")
        print(f"  Quality:    {article.quality}")
        print(f"  Disease:    {article.disease}")
        print("-" * 20)

    print("\n" + "="*50)
    print("GENERATING LLM SUMMARY")
    print("="*50)
    
    try:
        summarizer = LLMSummarizer()
        response_gen = summarizer.summarize(variant, articles, stream=True)
        
        print(f"Summary for {variant}:")
        for chunk in response_gen:
            if 'content' in chunk['choices'][0]['delta']:
                token = chunk['choices'][0]['delta']['content']
                print(token, end="", flush=True)
        print("\n")
        
    except Exception as e:
        logger.error(f"\nLLM Summarization failed: {e}")

    end_time = time.time()
    logger.info(f"\nWorkflow completed in {round(end_time - start_time, 2)}s")


if __name__ == '__main__':
    main()
