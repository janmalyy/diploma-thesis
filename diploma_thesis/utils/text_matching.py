from rapidfuzz import fuzz

from diploma_thesis.core.models import TextBlock


def assign_snippets_to_blocks(
    blocks: list[tuple[TextBlock, object]],
    snippets: list[TextBlock],
) -> dict[TextBlock, object]:
    """
    Assigns each snippet to at most one block (best match wins).

    Args:
        blocks: list of (TextBlock, payload) where payload is parser-specific
        snippets: remaining fulltext snippets

    Returns:
        mapping: snippet -> payload
    """
    snippet_best: dict[TextBlock, tuple[float, object]] = {}

    for text_block, payload in blocks:
        matches = get_snippet_scores_for_text(text_block, snippets)

        for snippet, score in matches.items():
            best = snippet_best.get(snippet)
            if best is None or score > best[0]:
                snippet_best[snippet] = (score, payload)

    return {snippet: payload for snippet, (_, payload) in snippet_best.items()}


def get_snippet_scores_for_text(
    text: TextBlock,
    snippets: list[TextBlock],
    *,
    min_partial_score: int = 90,
) -> dict[TextBlock, float]:
    """
    Finds the best-scoring snippets for a given text block.

    Matching is two-stage:
    1) permissive candidate detection via partial_ratio
    2) strict validation via token coverage + final score

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
