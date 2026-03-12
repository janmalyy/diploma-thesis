import asyncio
import json

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from diploma_thesis.core.llm_response_models import (AggregatedSummary,
                                                     ArticleAnalysis)
from diploma_thesis.core.models import Article, Variant
from diploma_thesis.settings import (E_INFRA_API_KEY, EINFRA_URL, MODEL_NAME,
                                     logger)
from diploma_thesis.utils.helpers import build_prompt, get_prompt

model = OpenAIChatModel(
    model_name=MODEL_NAME,
    provider=OpenAIProvider(base_url=EINFRA_URL, api_key=E_INFRA_API_KEY),
)

analysis_agent = Agent(
    model,
    output_type=ArticleAnalysis,
    system_prompt=get_prompt("system_evaluate_and_extract.txt"),
    retries=3
)

aggregator_agent = Agent(
    model,
    output_type=AggregatedSummary,
    system_prompt=get_prompt("system_aggregate.txt"),
    retries=3
)


async def process_single_article(
        article: Article,
        variant: Variant,
        prompt_template: str,
        semaphore: asyncio.Semaphore,
        progress_callback=None
) -> dict | None:
    """Processes one article, respecting the concurrency limit."""
    async with semaphore:
        try:
            replacements = {
                "GENE": variant.gene,
                "VARIANT": variant.variant,
                "VARIANT_INFO": variant.variant_dict,
                **article.get_structured_context()
            }
            ready_prompt = build_prompt(replacements, prompt_template)

            result = await analysis_agent.run(ready_prompt)

            data = result.output

            if progress_callback:
                await progress_callback("Analysis")

            if data.is_relevant:
                evidence_data = data.model_dump()
                evidence_data["article_id"] = article.pmcid or article.pmid
                return evidence_data
            return None

        except Exception as e:
            logger.error(f"Error processing {article.pmcid or article.pmid}: {e}")
            # Even on failure, we notify the callback to keep the count accurate
            if progress_callback:
                await progress_callback("Analysis")
            return None


async def run_pipeline(variant: Variant, articles: list[Article], progress_callback=None) -> dict:
    semaphore = asyncio.Semaphore(4)
    prompt_template = get_prompt("user_evaluate_and_extract.txt")

    tasks = [
        process_single_article(article, variant, prompt_template, semaphore, progress_callback)
        for i, article in enumerate(articles)
    ]

    results = await asyncio.gather(*tasks)
    valid_evidences = [res for res in results if res is not None and res.get("is_relevant") is True]

    if not valid_evidences:
        return {"narrative_summary": "No relevant evidence found.", "article_evidences": []}

    if progress_callback:
        await progress_callback("Aggregating")

    agg_replacements = {
        "GENE": variant.gene,
        "VARIANT": variant.variant,
        "VARIANT_INFO": variant.variant_dict,
        "STRUCTURED_EVIDENCE_LIST": json.dumps(valid_evidences)
    }

    agg_prompt = build_prompt(agg_replacements, get_prompt("user_aggregate.txt"))
    agg_result = await aggregator_agent.run(agg_prompt)

    final_output = agg_result.output.model_dump()
    final_output["article_evidences"] = valid_evidences
    return final_output
