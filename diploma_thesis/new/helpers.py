import re

from diploma_thesis.new.models import TextBlock


def clean_variant_tags(text: str) -> str:
    """Cleans span tags that contain angle brackets within their attributes.

    Args:
        text: Raw text string with potentially complex HTML attributes.

    Returns:
        The text with span tags removed but content preserved.
    """
    # [^">] matches anything not a quote or a closing bracket
    # "[^"]*" matches a full quoted string (allowing > inside)
    # The combination ensures we only stop at a > that is NOT inside quotes
    pattern = r'<span(?:[^">]|"[^"]*")*>(.*?)</span>'

    return re.sub(pattern, r"\1", text)

    # TODO Budu chtít nějak zachovat tu pozici, abych ji tam pak mohl zvýrazněnou vrátit do závěrečného kontextu
    #  If you need to extract those IDs later, you can use: re.findall(r'concept_id=\"(.*?)\"', text)


all_spaces_pattern = r"(?:&nbsp;?|&#160;|[  \s])+"


def normalize_text(text: str) -> str:
    text = re.sub(all_spaces_pattern, " ", text.strip())
    return " ".join(text.split()).lower()


def check_text_for_snippets(text: TextBlock, snippets: list[TextBlock]) -> tuple[bool, list[TextBlock]]:
    """
    Checks if a piece of text contains any of the provided snippets.
    Uses normalization to handle whitespace/newline inconsistencies.
    """
    if not text or not snippets:
        return False, []
    matched_snippets = []
    for snippet in snippets:
        if len(snippet) < 5:
            continue
        if snippet.machine_comparable in text.machine_comparable:
            matched_snippets.append(snippet)

    return len(matched_snippets) > 0, matched_snippets
