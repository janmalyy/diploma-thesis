import json
import re

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from diploma_thesis.core.models import Article, Variant
from diploma_thesis.settings import (DATA_DIR, E_INFRA_API_KEY, EINFRA_URL,
                                     PACKAGE_DIR, logger)


def get_prompt(path: str) -> str:
    with open(PACKAGE_DIR / "prompts" / path) as f:
        return f.read()


def build_prompt(replacements: dict[str, str], prompt: str) -> str:
    # keys not present in the prompt are ignored
    for key, value in replacements.items():
        prompt = prompt.replace(key, str(value))

    return prompt


def parse_llm_json(raw_text: str) -> dict | ValueError:
    """
    Tries to parse the output of the LLM as JSON.
    Args:
        raw_text: output of the LLM
    Returns:
        the parsed JSON object or a ValueError if parsing fails
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    # First try: strict JSON
    try:
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError(f"Expected a JSON object, got {type(obj).__name__}")
        return obj
    except json.JSONDecodeError:
        pass

    # Second try: extract the first JSON object within the text
    match = re.search(r"\{[\s\S]*}", text)
    if not match:
        raise ValueError("No JSON object found in LLM output.")
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        # Third try: if there are multiple objects or trailing text, try to find a balanced one
        # This is a bit more complex, for now let's try to just find the LAST closing brace
        # or maybe the first { and the last } was already tried by re.search(r"\{[\s\S]*}", text)
        logger.info(f"This was not possible to parse: {obj}")
        raise ValueError("Found something that looks like JSON but failed to parse.")
    if not isinstance(obj, dict):
        raise ValueError(f"Expected a JSON object, got {type(obj).__name__}")
    return obj


model = OpenAIChatModel(
        model_name="gpt-oss-120b",
        provider=OpenAIProvider(
            base_url=EINFRA_URL,
            api_key=E_INFRA_API_KEY,
        ),
    )

checker_agent = Agent(model, system_prompt=get_prompt("system_check_relevance.txt"))

extractor_agent = Agent(model, system_prompt=get_prompt("system_extract_evidence.txt"))

aggregator_agent = Agent(model, system_prompt=get_prompt("system_aggregate.txt"))


async def relevance_check(variant: Variant, articles: list[Article], progress_callback=None) -> list[Article]:
    if not articles:
        return []
    relevant_articles = []
    prompt = get_prompt("user_check_relevance.txt")

    total = len(articles)
    for i, article in enumerate(articles):
        try:
            if progress_callback:
                await progress_callback(i + 1, "Relevance check")

            replacements = {
                "_GENE_": variant.gene,
                "_VARIANT_": variant.variant,
                "VARIANT_INFO": variant.variant_dict,
            }
            replacements.update(article.get_structured_context())

            ready_prompt = build_prompt(replacements, prompt)
            result = await checker_agent.run(ready_prompt)
            logger.debug(f"ARTICLE_ID: {article.pmcid if article.pmcid else article.pmid}")
            logger.debug(f"OUTPUT: {result.output}")

            data = parse_llm_json(result.output)
            if data.get("is_relevant"):
                relevant_articles.append(article)
        except Exception as e:
            logger.error(f"Error checking relevance of article {article.pmcid if article.pmcid else article.pmid}: {e}")
            continue

    return relevant_articles


async def extract_evidences(variant: Variant, articles: list[Article], progress_callback=None) -> list[dict]:
    if not articles:
        return []

    evidences = []
    prompt = get_prompt("user_extract_evidence.txt")

    for i, article in enumerate(articles):
        try:
            if progress_callback:
                await progress_callback(i + 1, "Evidence extraction")
            replacements = {
                "_GENE_": variant.gene,
                "_VARIANT_": variant.variant,
                "VARIANT_INFO": variant.variant_dict}
            replacements.update(article.get_structured_context())

            ready_prompt = build_prompt(replacements, prompt)
            result = await extractor_agent.run(ready_prompt)
            logger.debug(f"ARTICLE_ID: {article.pmcid if article.pmcid else article.pmid}")
            logger.debug(f"OUTPUT: {result.output}")

            data = parse_llm_json(result.output)
            # Add article ID to data for reference in aggregation
            data["article_id"] = article.pmcid if article.pmcid else article.pmid
            evidences.append(data)
        except Exception as e:
            logger.error(f"Error extracting evidence from article {article.pmcid if article.pmcid else article.pmid}: {e}")
            continue

    return evidences


async def aggregate_evidences(variant: Variant, evidences: list[dict]) -> dict:
    if not evidences:
        return {
            "narrative_summary": "No evidence was found in the analyzed articles.",
            "structured_summary": {
                "overall_pathogenicity": "uncertain",
                "evidence_counts": {"functional": 0, "clinical": 0, "population": 0, "computational": 0},
                "conflicting_evidence": False,
                "overall_confidence": "low"
            }
        }

    prompt = get_prompt("user_aggregate.txt")

    replacements = {
        "_GENE_": variant.gene,
        "_VARIANT_": variant.variant,
        "VARIANT_INFO": variant.variant_dict,
        "STRUCTURED_EVIDENCE_LIST": json.dumps(evidences)
    }

    ready_prompt = build_prompt(replacements, prompt)
    try:
        result = await aggregator_agent.run(ready_prompt)
        logger.debug(f"AGGREGATION OUTPUT: {result.output}")
        data = parse_llm_json(result.output)
        return data
    except Exception as e:
        logger.error(f"Error aggregating for variant {variant}: {e}")
        # If we failed to get structured JSON, at least return the raw output as narrative if it exists
        try:
            if 'result' in locals() and result.output:
                return {
                    "narrative_summary": result.output,
                    "structured_summary": None,
                    "error": "Failed to parse structured JSON from LLM"
                }
        except:
            pass

        return {
            "narrative_summary": f"Error during summary aggregation: {str(e)}",
            "structured_summary": None
        }
