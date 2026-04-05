import asyncio
import json
from pprint import pprint

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from diploma_thesis.core.llm_response_models import (AggregatedSummary,
                                                     ArticleAnalysis, Claim,
                                                     ConfidenceLevel, Mention,
                                                     Pathogenicity)
from diploma_thesis.core.models import Article, Variant
from diploma_thesis.settings import (E_INFRA_API_KEY, EINFRA_URL, MODEL_NAME,
                                     logger)
from diploma_thesis.utils.helpers import (build_prompt, get_prompt,
                                          transform_paragraph_for_display)

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
    Returns: JSON object (so-called 'article_mention') with evidence data and article metadata or None if not relevant
    """
    async with semaphore:
        try:
            replacements = {
                "_GENE_": variant.gene,
                "_VARIANT_": variant.variant,
                "_VARIANTINFO_": variant.variant_dict,
                **article.get_structured_context()
            }
            ready_prompt = build_prompt(replacements, prompt_template)
            # print("ready_prompt", ready_prompt)
            result = await analysis_agent.run(ready_prompt)

            data: ArticleAnalysis = result.output
            print(f"article {article.pmcid or article.pmid}")
            print(data.overall_article_summary)
            print(data.uncertainties_or_limitations)
            pprint(data.mentions)
            if progress_callback:
                await progress_callback("Analysis")

            relevant_mentions: list[Mention] = [mention for mention in data.mentions if mention.is_relevant]
            if relevant_mentions:
                formatted_mentions = []
                paragraphs_mentions = article.get_structured_context().get("_MENTIONS_")
                for m in relevant_mentions:
                    formatted_mentions.append(
                        {
                            "quoted_text": transform_paragraph_for_display(
                                paragraphs_mentions[m.mention_id], variant.terms
                            ),
                            "mention_type": m.mention_type,
                            "claim": m.claim,
                            "strength": m.strength,
                        }
                    )

                article_mention = {
                    "mentions": formatted_mentions,
                    "overall_article_summary": data.overall_article_summary,
                    "uncertainties_or_limitations": data.uncertainties_or_limitations,
                }
                article_mention.update(**article.get_structured_metadata())

                return article_mention
            return None

        except Exception as e:
            error_type = e.__class__.__name__
            error_msg = f"{error_type}: {str(e)}"
            logger.error(f"Process single article: error processing {article.pmcid or article.pmid}: {error_msg}")
            # Even on failure, we notify the callback to keep the count accurate
            if progress_callback:
                await progress_callback("Analysis")
            return None


def compute_structured_summary(article_mentions: list[dict]) -> dict:
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

    for article in article_mentions:
        for mention in article.get("mentions", []):
            claim = mention.get("claim", None)
            if not claim:
                continue
            claim = claim.lower()
            if claim not in ("", Claim.no_claim.value):
                total_evidences += 1
                claim = mention.get("claim").lower()

                strength = mention.get("strength", None)
                if not strength:
                    continue
                strength = strength.lower()

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

    # choose appropriate prompt template
    prompt_basic = get_prompt("user_evaluate_and_extract.txt")
    prompt_one = get_prompt("user_evaluate_and_extract_one.txt")
    prompt_medline = get_prompt("user_evaluate_and_extract_medline.txt")

    tasks = []
    for i, article in enumerate(articles):
        if article.data_sources == {"medline"}:
            tasks.append(process_single_article(article, variant, prompt_medline, semaphore, progress_callback))
        elif len(article.paragraphs) + len(article.suppl_data_list) == 1:
            tasks.append(process_single_article(article, variant, prompt_one, semaphore, progress_callback))
        else:
            tasks.append(process_single_article(article, variant, prompt_basic, semaphore, progress_callback))

    results = await asyncio.gather(*tasks)
    # it is called article_mention because it is something in between, it is a Mention with some Article data
    valid_article_mentions = [res for res in results if res is not None]

    if not valid_article_mentions:
        return {"narrative_summary": "No relevant evidence found.", "article_mentions": []}

    if progress_callback:
        await progress_callback("Aggregating")

    agg_replacements = {
        "_GENE_": variant.gene,
        "_VARIANT_": variant.variant,
        "_VARIANTINFO_": variant.variant_dict,
        "_STRUCTURED_EVIDENCE_LIST_": json.dumps(valid_article_mentions)
    }

    agg_prompt = build_prompt(agg_replacements, get_prompt("user_aggregate.txt"))
    agg_result = await aggregator_agent.run(agg_prompt)
    narrative = agg_result.output.narrative_summary
    while len(narrative) < 50:
        logger.warning(f"Narrative summary is too short: {narrative}. Redoing aggregation.")
        agg_result = await aggregator_agent.run(agg_prompt)
        narrative = agg_result.output.narrative_summary

    logger.info(f"narrative: {narrative}")

    structured_summary = compute_structured_summary(valid_article_mentions)
    [print(key, value) for key, value in structured_summary.items()]

    final_output = agg_result.output.model_dump()
    final_output["structured_summary"] = structured_summary
    final_output["article_mentions"] = valid_article_mentions

    return final_output
