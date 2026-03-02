import json
import re

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from diploma_thesis.settings import E_INFRA_API_KEY, DATA_DIR, PACKAGE_DIR, EINFRA_URL, logger

from diploma_thesis.core.models import Article, Variant


def get_prompt(path: str) -> str:
    with open(PACKAGE_DIR / "prompts" / path) as f:
        return f.read()


def build_prompt(replacements: dict[str, str], prompt: str) -> str:
    # keys not present in the prompt are ignored
    for key, value in replacements.items():
        prompt = prompt.replace(key, str(value))

    return prompt


def parse_llm_json(raw_text: str) -> dict:
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
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected a JSON object, got {type(obj).__name__}")
    return obj


model = OpenAIChatModel(
        model_name="gemma3:27b-it",
        provider=OpenAIProvider(
            base_url=EINFRA_URL,
            api_key=E_INFRA_API_KEY,
        ),
    )

checker_agent = Agent(model, system_prompt=get_prompt("system_check_relevance.txt"))

extractor_agent = Agent(model, system_prompt=get_prompt("system_extract_evidence.txt"))

aggregator_agent = Agent(model, system_prompt=get_prompt("system_aggregate.txt"))


async def relevance_check(variant: Variant, articles: list[Article]) -> list[Article]:
    if not articles:
        raise ValueError("No articles were given to process for the variant.")
    relevant_articles = []
    prompt = get_prompt("user_check_relevance.txt")

    for article in articles:
        replacements = {
            "_GENE_": variant.gene,
            "_VARIANT_": variant.variant,
            "VARIANT_INFO": variant.variant_dict,
        }
        replacements.update(article.get_structured_context())

        ready_prompt = build_prompt(replacements, prompt)
        result = await checker_agent.run(ready_prompt)
        print("ARTICLE_ID", article.pmcid if article.pmcid else article.pmid)
        print("PROMPT", ready_prompt)
        print("OUTPUT", result.output)
        try:
            data = parse_llm_json(result.output)
            if data["is_relevant"]:
                relevant_articles.append(article)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON returned by LLM: {result.output}")
        except Exception as e:
            raise RuntimeError(f"Error checking relevance of article {article.pmcid if article.pmcid else article.pmid}: {e}")

    return relevant_articles


async def extract_evidences(variant: Variant, articles: list[Article]) -> list[dict]:
    if not articles:
        raise ValueError("No articles were given to process for the variant.")

    evidences = []
    prompt = get_prompt("user_extract_evidence.txt")

    for article in articles:
        replacements = {
            "_GENE_": variant.gene,
            "_VARIANT_": variant.variant,
            "VARIANT_INFO": variant.variant_dict}
        replacements.update(article.get_structured_context())

        ready_prompt = build_prompt(replacements, prompt)
        result = await extractor_agent.run(ready_prompt)
        print("ARTICLE_ID", article.pmcid if article.pmcid else article.pmid)
        print("PROMPT", ready_prompt)
        print("OUTPUT", result.output)
        try:
            data = parse_llm_json(result.output)
            evidences.append(data)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON returned by LLM: {result.output}")
        except Exception as e:
            raise RuntimeError(f"Error checking relevance of article {article.pmcid if article.pmcid else article.pmid}: {e}")

    return evidences


async def aggregate_evidences(variant: Variant, evidences: list[dict]) -> dict:
    if not evidences:
        raise ValueError("No evidences were given to process for the variant.")

    prompt = get_prompt("user_aggregate.txt")

    replacements = {
        "_GENE_": variant.gene,
        "_VARIANT_": variant.variant,
        "VARIANT_INFO": variant.variant_dict,
        "STRUCTURED_EVIDENCE_LIST": json.dumps(evidences)
    }

    ready_prompt = build_prompt(replacements, prompt)
    result = await extractor_agent.run(ready_prompt)
    print("PROMPT", ready_prompt)
    print("OUTPUT", result.output)
    try:
        data = parse_llm_json(result.output)
        return data
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON returned by LLM: {result.output}")
    except Exception as e:
        raise RuntimeError(f"Error aggregating for variant {variant}: {e}")



