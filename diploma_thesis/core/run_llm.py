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
        temperature=0,
        presence_penalty=0,
        frequency_penalty=0,
        extra_body={
            "reasoning_effort": "medium",
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
        temperature=0,
        presence_penalty=0,
        frequency_penalty=0,
        extra_body={
            "reasoning_effort": "medium",
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
) -> tuple[dict | None, dict]:
    """
    Evaluate the relevance of the article and extract evidences if it is relevant. Add metadata.
    Returns: Tuple of (article_mention dict or None, usage_stats dict)
    """
    async with semaphore:
        usage_stats = {"input": 0, "output": 0}
        try:
            replacements = {
                "_GENE_": variant.gene,
                "_VARIANT_": variant.variant,
                "_VARIANTINFO_": variant.variant_dict,
                **article.get_structured_context()
            }
            ready_prompt = build_prompt(replacements, prompt_template)
            result = await analysis_agent.run(ready_prompt)

            usage = result.usage()
            usage_stats["input"] = usage.input_tokens or 0
            usage_stats["output"] = usage.output_tokens or 0

            data: ArticleAnalysis = result.output
            if progress_callback:
                await progress_callback("Analysis")

            relevant_mentions: list[Mention] = [mention for mention in data.mentions if mention.is_relevant]
            if relevant_mentions:
                formatted_mentions = []
                paragraphs_mentions = article.get_structured_context()["_MENTIONS_"]
                for m in relevant_mentions:
                    # fallback logic
                    ment_id = paragraphs_mentions.get(m.mention_id, list(paragraphs_mentions.values())[
                        0] if paragraphs_mentions else "")

                    formatted_mentions.append(
                        {
                            "quoted_text": transform_paragraph_for_display(
                                ment_id, variant.terms
                            ),
                            "mention_type": m.mention_type,
                            "claim": m.claim,
                        }
                    )

                article_mention = {
                    "mentions": formatted_mentions,
                    "overall_article_summary": data.overall_article_summary,
                    "uncertainties_or_limitations": data.uncertainties_or_limitations,
                }
                article_mention.update(**article.get_structured_metadata())

                return article_mention, usage_stats

            return None, usage_stats

        except Exception:
            logger.exception(f"Process single article: error processing {article.pmcid or article.pmid}")
            # Even on failure, we notify the callback to keep the count accurate
            if progress_callback:
                await progress_callback("Analysis")
            return None, usage_stats


def compute_structured_summary(article_mentions: list[dict]) -> dict:
    """
    Compute a structured summary with a conservative approach.
    Prioritizes lower certainty in case of ambiguity or ties.
    Exclude no_claim mentions.
    """
    counts = {key: 0 for key in {Claim.uncertain.value, Claim.supports_pathogenicity.value, Claim.supports_benignity.value}}
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

                if claim in counts:
                    counts[claim] += 1
                else:
                    counts["uncertain"] += 1

    if total_evidences == 0:
        return {
            "overall_pathogenicity": Pathogenicity.UNCERTAIN,
            "overall_confidence": ConfidenceLevel.LOW,
            "pathogenicity_counts": counts,
            "conflicting_evidence": False
        }

    score_p = counts[Claim.supports_pathogenicity.value]
    score_b = counts[Claim.supports_benignity.value]

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
        max_score = max(counts.values())

        if counts["uncertain"] * 1.1 >= max_score:  # we want to be sure that the uncertain is not the most frequent
            final_patho = Pathogenicity.UNCERTAIN
        elif score_b == max_score:
            if score_b > counts["uncertain"] * 1.3:
                final_patho = Pathogenicity.BENIGN
            else:
                final_patho = Pathogenicity.LIKELY_BENIGN
        elif score_p == max_score:
            if score_p > counts["uncertain"] * 1.3:
                final_patho = Pathogenicity.PATHOGENIC
            else:
                final_patho = Pathogenicity.LIKELY_PATHOGENIC

    return {
        "overall_pathogenicity": final_patho,
        "pathogenicity_counts": counts,
        "conflicting_evidence": is_conflicting
    }


async def run_pipeline(variant: Variant, articles: list[Article], progress_callback=None) -> dict:
    semaphore = asyncio.Semaphore(4)

    prompt_basic = get_prompt("user_evaluate_and_extract.txt")
    prompt_one = get_prompt("user_evaluate_and_extract_one.txt")
    prompt_medline = get_prompt("user_evaluate_and_extract_medline.txt")

    tasks = []
    for article in articles:
        if article.data_sources == {"medline"}:
            tasks.append(process_single_article(article, variant, prompt_medline, semaphore, progress_callback))
        elif len(article.paragraphs) + len(article.suppl_data_list) == 1:
            tasks.append(process_single_article(article, variant, prompt_one, semaphore, progress_callback))
        else:
            tasks.append(process_single_article(article, variant, prompt_basic, semaphore, progress_callback))

    results = await asyncio.gather(*tasks)

    valid_article_mentions = [res[0] for res in results if res[0] is not None]
    analysis_token_counts = [res[1] for res in results]

    if not valid_article_mentions:
        return {
            "narrative_summary": "No relevant evidence found.",
            "article_mentions": [],
            "analysis_token_counts": analysis_token_counts,
            "structured_summary": {}
        }

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
    usage = agg_result.usage()
    total_agg_input = (usage.input_tokens or 0)
    total_agg_output = (usage.output_tokens or 0)

    narrative = agg_result.output.narrative_summary
    while len(narrative) < 50:
        logger.warning(f"Narrative summary is too short: {narrative}. Redoing aggregation.")
        agg_result = await aggregator_agent.run(agg_prompt)
        usage = agg_result.usage()
        total_agg_input += (usage.input_tokens or 0)
        total_agg_output += (usage.output_tokens or 0)
        narrative = agg_result.output.narrative_summary

    aggregation_token_count = {
        "input": total_agg_input,
        "output": total_agg_output
    }

    structured_summary = compute_structured_summary(valid_article_mentions)

    final_output = agg_result.output.model_dump()
    final_output["structured_summary"] = structured_summary
    final_output["article_mentions"] = valid_article_mentions
    final_output["analysis_token_counts"] = analysis_token_counts
    final_output["aggregation_token_count"] = aggregation_token_count

    return final_output
