import re

from rapidfuzz import fuzz

from diploma_thesis.core.models import TextBlock
from diploma_thesis.utils.helpers import compile_variant_pattern


def get_snippet_scores_for_text(
    text: TextBlock,
    snippets: list[TextBlock],
    *,
    min_partial_score: int = 90,
) -> dict[TextBlock, float]:
    """
    Finds the best-scoring snippets for a given text block.

    Returns:
        {snippet: final_score}
    """
    if not text or not snippets:
        return False, {}

    text_mc = text.machine_comparable
    matched: dict[TextBlock, float] = {}
    for snippet in snippets:
        snippet_mc = snippet.machine_comparable

        if len(snippet_mc) < 10 or len(snippet_mc) > len(text_mc):
            continue

        score = fuzz.partial_ratio(snippet_mc, text_mc)
        # TODO IMPLEMENT MORE COMPLEX MATCHING, more stages: e.g., starting with partial, then fuzz.ratio, then comparing tag sets
        if score > min_partial_score:
            matched[snippet] = score

    return matched


def find_relevant_paragraphs_with_snippets(
    snippets: list[TextBlock],
    blocks: list[tuple[TextBlock, object]],
) -> tuple[list[TextBlock], list[object]]:
    """
    For each snippet, try to find one best-scoring text block.
    Args:
        blocks: list of (TextBlock, payload) where payload is parser-specific. Payload is the raw content of the block.
        We have to care about the payload because it is then used for annotation.
        snippets: remaining fulltext snippets

    Returns:
        list of snippets with match; list of payloads - raw paragraphs, where the snippets were found, to be annotated
    """
    snippet_best: dict[TextBlock, tuple[float, object]] = {}

    for text_block, payload in blocks:
        matches = get_snippet_scores_for_text(text_block, snippets)

        for snippet, score in matches.items():
            best = snippet_best.get(snippet)
            if best is None or score > best[0]:
                snippet_best[snippet] = (score, payload)

    return list(snippet_best.keys()), [payload for (score, payload) in snippet_best.values()]


def find_relevant_paragraphs_without_snippets(
    terms: list[str],
    blocks: list[tuple[TextBlock, object]]
) -> list[object]:
    """
    This function is used when there are no evidences from variomes for PMC fulltext articles.
    Args:
        blocks: list of (TextBlock, payload) where payload is parser-specific. Payload is the raw content of the block.
        We have to care about the payload because it is then used for annotation.
        terms: a list of possible notations of the searched variant

    Returns: list of payloads - raw paragraphs, where some variant term was found, to be annotated

    """
    pattern = compile_variant_pattern(terms)
    relevant_texts = []
    relevant_payloads = []
    for text_block, payload in blocks:
        text = text_block.raw_text
        if re.search(pattern, text):
            if is_new_paragraph(text, relevant_texts, 90):
                relevant_texts.append(text)
                relevant_payloads.append(payload)

    return relevant_payloads


def is_new_paragraph(paragraph: str, existing_paragraphs: list[str], threshold: int) -> bool:
    """Determine whether a paragraph is sufficiently different from existing ones."""
    # logger.info("Checking if paragraph is new")
    for p in existing_paragraphs:
        if p == paragraph:
            # logger.info("Exact match found, paragraph is not new")
            return False
        if fuzz.partial_ratio(p, paragraph) > threshold:
            # logger.info(f"High similarity ({fuzz.partial_ratio(p, paragraph)}%) with existing paragraph, not new")
            return False
    # logger.info("Paragraph is considered new")
    return True
