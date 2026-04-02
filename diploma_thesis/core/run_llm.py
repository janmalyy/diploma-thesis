import asyncio
import json

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from diploma_thesis.core.llm_response_models import (AggregatedSummary,
                                                     ArticleAnalysis, Claim,
                                                     ConfidenceLevel,
                                                     Pathogenicity)
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
    model_settings=ModelSettings(
        # Standard settings
        temperature=1.0,  # Recommended 1.0 for reasoning models OpenAI-specific reasoning settings via extra_body
        extra_body={
            "reasoning_effort": "high",
            "max_completion_tokens": 2048
        }
    ),
    retries=3
)

aggregator_agent = Agent(
    model,
    output_type=AggregatedSummary,
    system_prompt=get_prompt("system_aggregate.txt"),
    model_settings=ModelSettings(
        # Standard settings
        temperature=1.0,  # Recommended 1.0 for reasoning models OpenAI-specific reasoning settings via extra_body
        extra_body={
            "reasoning_effort": "high",
            "max_completion_tokens": 4096
        }
    ),
    retries=3
)


async def process_single_article(
        article: Article,
        variant: Variant,
        prompt_template: str,
        semaphore: asyncio.Semaphore,
        progress_callback=None
) -> dict | None:
    """
    Evaluate the relevance of the article and extract evidences if it is relevant. Add metadata.
    Returns: JSON object with evidence data and article metadata or None if not relevant
    """
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
            print(f"evidence {article.pmcid or article.pmid}: {data.is_relevant}")
            print(data.reason)
            print(data.overall_article_summary)
            print(data.uncertainties_or_limitations)
            print(data.evidence)
            if progress_callback:
                await progress_callback("Analysis")

            if data.is_relevant:
                evidence_data = data.model_dump()
                evidence_data.update(**article.get_structured_metadata())
                return evidence_data
            return None

        except Exception as e:
            logger.error(f"Error processing {article.pmcid or article.pmid}: {e}")
            # Even on failure, we notify the callback to keep the count accurate
            if progress_callback:
                await progress_callback("Analysis")
            return None


def compute_structured_summary(valid_evidences: list[dict]) -> dict:
    """
    Compute a structured summary with a conservative approach.
    Prioritizes lower certainty in case of ambiguity or ties.
    """
    strength_weights = {"high": 4, "moderate": 2}
    default_weight = 1

    scores = {
        Claim.uncertain.value: 0.0,
        Claim.supports_pathogenicity.value: 0.0,
        Claim.supports_benignity.value: 0.0,
    }

    counts = {key: 0 for key in scores.keys()}
    strength_counts = {"high": 0, "moderate": 0}
    total_evidences = 0

    for article in valid_evidences:
        for ev in article.get("evidence", []):
            if ev.get("claim", "").lower() not in ("", Claim.no_claim.value):
                total_evidences += 1
                claim = ev.get("claim").lower()
                strength = ev.get("strength", "").lower()

                weight = strength_weights.get(strength, default_weight)

                if strength in strength_counts:
                    strength_counts[strength] += 1

                if claim in scores:
                    scores[claim] += weight
                    counts[claim] += 1
                else:
                    scores["uncertain"] += weight
                    counts["uncertain"] += 1

    if total_evidences == 0:
        return {
            "overall_pathogenicity": Pathogenicity.UNCERTAIN,
            "overall_confidence": ConfidenceLevel.LOW,
            "pathogenicity_counts": counts,
            "conflicting_evidence": False
        }

    score_p = scores[Claim.supports_pathogenicity.value]
    score_b = scores[Claim.supports_benignity.value]

    # If there are both "supports pathogenicity" and "supports benignity" claims
    # and the ratio is less than 3:1, it is conflicting
    is_conflicting = False
    if score_p > 0 and score_b > 0:
        ratio = max(score_p, score_b) / min(score_p, score_b)
        if ratio < 3.0:
            is_conflicting = True

    final_patho = Pathogenicity.UNCERTAIN
    if is_conflicting:
        final_patho = Pathogenicity.UNCERTAIN
    else:
        max_score = max(scores.values())

        if scores["uncertain"] * 1.1 >= max_score:  # we want to be sure that the uncertain is not the most frequent
            final_patho = Pathogenicity.UNCERTAIN
        elif score_b == max_score:
            if score_b > scores["uncertain"] * 1.3:
                final_patho = Pathogenicity.BENIGN
            else:
                final_patho = Pathogenicity.LIKELY_BENIGN
        elif score_p == max_score:
            if score_p > scores["uncertain"] * 1.3:
                final_patho = Pathogenicity.PATHOGENIC
            else:
                final_patho = Pathogenicity.LIKELY_PATHOGENIC

    # Confidence computation
    ratio_high = strength_counts["high"] / total_evidences
    ratio_combined = (strength_counts["high"] + strength_counts["moderate"]) / total_evidences

    if ratio_high >= 0.7 or ratio_combined >= 0.8:
        overall_conf = ConfidenceLevel.HIGH
    elif ratio_combined >= 0.6:
        overall_conf = ConfidenceLevel.MODERATE
    else:
        overall_conf = ConfidenceLevel.LOW

    return {
        "overall_pathogenicity": final_patho,
        "overall_confidence": overall_conf,
        "pathogenicity_counts": counts,
        "conflicting_evidence": is_conflicting
    }


async def run_pipeline(variant: Variant, articles: list[Article], progress_callback=None) -> dict:
    semaphore = asyncio.Semaphore(4)
    prompt_template = get_prompt("user_evaluate_and_extract.txt")

    tasks = [
        process_single_article(article, variant, prompt_template, semaphore, progress_callback)
        for i, article in enumerate(articles)
    ]

    results = await asyncio.gather(*tasks)
    valid_evidences = [res for res in results if res is not None]

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
    logger.info(f"aggregation {variant}:")
    logger.info(f"narrative: {agg_result.output.narrative_summary}")

    structured_summary = compute_structured_summary(valid_evidences)
    [print(key, value) for key, value in structured_summary.items()]

    final_output = agg_result.output.model_dump()
    final_output["structured_summary"] = structured_summary
    final_output["article_evidences"] = valid_evidences
    return final_output
