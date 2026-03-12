import asyncio
import json

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from diploma_thesis.core.llm_response_models import (AggregatedSummary,
                                                     ArticleAnalysis)
from diploma_thesis.core.models import Article, Variant
from diploma_thesis.settings import E_INFRA_API_KEY, EINFRA_URL, logger
from diploma_thesis.utils.helpers import build_prompt, get_prompt

model = OpenAIChatModel(
    model_name="qwen3.5",
    provider=OpenAIProvider(base_url=EINFRA_URL, api_key=E_INFRA_API_KEY),
)

analysis_agent = Agent(
    model,
    output_type=ArticleAnalysis,
    system_prompt=get_prompt("system_evaluate_and_extract.txt")
)

aggregator_agent = Agent(
    model,
    output_type=AggregatedSummary,
    system_prompt=get_prompt("system_aggregate.txt")
)


async def process_single_article(
        article: Article,
        variant: Variant,
        prompt_template: str,
        index: int,
        semaphore: asyncio.Semaphore,
        progress_callback=None
) -> dict | None:
    """Processes one article, respecting the concurrency limit."""
    # 1. Prepare data before entering the semaphore to allow potential parallelization of this fast sync step
    replacements = {
        "_GENE_": variant.gene,
        "_VARIANT_": variant.variant,
        "VARIANT_INFO": variant.variant_dict,
        **article.get_structured_context()
    }
    ready_prompt = build_prompt(replacements, prompt_template)

    # 2. Acquire semaphore and run LLM
    async with semaphore:
        if progress_callback:
            # Notify that we've started actively processing this article
            await progress_callback(index, "Processing")

        try:
            result = await analysis_agent.run(ready_prompt)
            data = result.output

            if progress_callback:
                # Notify that we've finished this article
                await progress_callback(index, "Done")

            if data.is_relevant:
                evidence_data = data.model_dump()
                evidence_data["article_id"] = article.pmcid or article.pmid
                return evidence_data
            return None

        except Exception as e:
            logger.error(f"Error processing {article.pmcid or article.pmid}: {e}")
            if progress_callback:
                await progress_callback(index, "Error")
            return None


async def run_pipeline(variant: Variant, articles: list[Article], progress_callback=None) -> dict:
    # 1. Configuration
    semaphore = asyncio.Semaphore(3)        # more than 3 raises 429 error "Too Many Requests"
    prompt_template = get_prompt("user_evaluate_and_extract.txt")

    # 2. Create tasks
    tasks = [
        process_single_article(article, variant, prompt_template, i + 1, semaphore, progress_callback)
        for i, article in enumerate(articles)
    ]

    # 3. Gather results concurrently
    results = await asyncio.gather(*tasks)
    valid_evidences = [res for res in results if res is not None]

    if not valid_evidences:
        return {"narrative_summary": "No relevant evidence found.", "article_evidences": []}

    # 4. Aggregation
    if progress_callback:
        await progress_callback(0, "Aggregating")

    agg_replacements = {
        "_GENE_": variant.gene,
        "_VARIANT_": variant.variant,
        "VARIANT_INFO": variant.variant_dict,
        "STRUCTURED_EVIDENCE_LIST": json.dumps(valid_evidences)
    }

    agg_prompt = build_prompt(agg_replacements, get_prompt("user_aggregate.txt"))
    agg_result = await aggregator_agent.run(agg_prompt)

    final_output = agg_result.output.model_dump()
    final_output["article_evidences"] = valid_evidences
    return final_output
