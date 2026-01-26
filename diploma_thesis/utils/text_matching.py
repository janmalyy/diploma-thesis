from rapidfuzz import fuzz

from diploma_thesis.core.models import TextBlock


def check_text_for_snippets(text: TextBlock, snippets: list[TextBlock]) -> tuple[bool, list[TextBlock]]:
    """
    Checks if a piece of text contains any of the provided snippets.
    Uses normalization to handle whitespace/newline inconsistencies.
    """
    if not text or not snippets:
        return False, []

    matched_snippets = []
    for snippet in snippets:
        if len(snippet) < 5 or len(snippet) > len(text):        # že je text delší než snippet se může stát, když sem jdou jako text data z tabulky a to má nebezpečně vysoké skóre, i když je společné třeba jen jedno slovo
            continue
        score = fuzz.partial_ratio(snippet.machine_comparable, text.machine_comparable)
        if 85 < score < 92:
            print("score:", round(score, 2))
            print("snippet:", snippet.machine_comparable)
            print("text:", text.machine_comparable)
        if score > 92:                          # this is an important threshold!
            matched_snippets.append(snippet)

    return len(matched_snippets) > 0, matched_snippets
