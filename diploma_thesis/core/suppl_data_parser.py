import re

from rapidfuzz import fuzz

from diploma_thesis.core.models import Article, Variant
from diploma_thesis.utils.helpers import to_human_readable


grid_pattern = re.compile(r"^(\d+)\t(\d+)\t(.*)$")


def compile_pattern(input_list: list[str]) -> re.Pattern:
    input_list = sorted(input_list, key=len, reverse=True)
    escaped = [r"[^\d\*\+a-zA-Z-]" + re.escape(v) for v in input_list]
    return re.compile("|".join(escaped))


def remove_articles_with_no_match(articles: list[Article]) -> list[Article]:
    """
    Remove articles that originate solely from supplementary data
    and none of their supplementary data objects contain any paragraphs.
    """
    for article in articles:
        if article.data_sources == {"supp"}:
            at_least_one_paragraph = False
            for sd in article.suppl_data_list:
                if len(sd.paragraphs) > 0:
                    at_least_one_paragraph = True
                    break
            if not at_least_one_paragraph:
                articles.remove(article)

    return articles


def is_new_paragraph(paragraph: str, existing_paragraphs: list[str]) -> bool:
    """Determine whether a paragraph is sufficiently different from existing ones."""
    is_new_paragraph = True
    for p in existing_paragraphs:
        if p == paragraph or fuzz.partial_ratio(p, paragraph) > 90:
            is_new_paragraph = False
            break

    return is_new_paragraph


def get_nearby_lines(
    text: str,
    l_start: int,
    l_end: int,
    count: int = 200,
) -> tuple[list[str], list[str]]:
    """
    Collect lines before and after a given line range.

    Args:
        text: Full raw text.
        l_start: Start index of the current line.
        l_end: End index of the current line.
        count: Maximum number of lines to collect in each direction.

    Returns:
        A tuple containing:
        - Lines before the current line (in original order)
        - Lines after the current line
    """
    lines = []
    curr = l_start
    for _ in range(count):
        if curr <= 0:
            break
        prev = text.rfind("\n", 0, curr - 1)
        ls = prev + 1 if prev != -1 else 0
        lines.append(text[ls:curr - 1])
        curr = ls

    lines_after = []
    curr = l_end
    for _ in range(count):
        if curr >= len(text):
            break
        nxt = text.find("\n", curr + 1)
        le = nxt if nxt != -1 else len(text)
        lines_after.append(text[curr + 1:le])
        curr = le

    return list(reversed(lines)), lines_after


def find_line_bounds(raw_text: str, variant_start: int) -> tuple[int, int]:
    """
    Find the start and end indices of the line containing a variant.

    Args:
        raw_text: Full raw text.
        variant_start: Character index where the variant begins.

    Returns:
        Tuple of (line_start, line_end).
    """
    line_start = raw_text.rfind("\n", 0, variant_start) + 1
    line_end = raw_text.find("\n", variant_start)
    if line_end == -1:
        line_end = len(raw_text)
    return line_start, line_end


def highlight_span(text: str, start: int, end: int) -> str:
    return text[:start] + "!!!" + text[start:end] + "!!!" + text[end:]


def reconstruct_grid_row(
    all_lines: list[str],
    current_idx: int,
    row_id: int,
) -> list[tuple[int, str, bool]]:
    """
    Reconstruct a logical grid row from adjacent tabular lines.

    Args:
        all_lines: Lines surrounding the current line.
        current_idx: Index of the current line in all_lines.
        row_id: Target row identifier.

    Returns:
        List of tuples (column_id, cell_value, is_match_line).
    """
    row_cells = []

    for i in range(current_idx, -1, -1):
        m = grid_pattern.match(all_lines[i])
        if m and int(m.group(1)) == row_id:
            row_cells.append((int(m.group(2)), m.group(3), i == current_idx))
        else:
            break

    row_cells.reverse()

    for i in range(current_idx + 1, len(all_lines)):
        m = grid_pattern.match(all_lines[i])
        if m and int(m.group(1)) == row_id:
            row_cells.append((int(m.group(2)), m.group(3), False))
        else:
            break

    row_cells.sort(key=lambda x: x[0])
    return row_cells


def build_grid_context(
    row_cells: list[tuple[int, str, bool]],
    current_line: str,
    variant_start: int,
    line_start: int,
    end: int,
) -> str:
    """
    Build a readable context string from grid row cells.

    The matched cell is highlighted if possible.

    Args:
        row_cells: Grid row cells with metadata.
        current_line: Raw line containing the variant.
        variant_start: Start index of the variant in raw text.
        line_start: Start index of the current line.
        end: End index of the variant.

    Returns:
        Human-readable context string.
    """
    context_parts = []

    for _, val, is_match_line in row_cells:
        if not is_match_line:
            context_parts.append(val)
            continue

        v_start_in_line = variant_start - line_start
        v_end_in_line = end - line_start

        val_match = grid_pattern.match(current_line)
        if val_match:
            prefix_len = val_match.start(3)
            rel_start = v_start_in_line - prefix_len
            rel_end = v_end_in_line - prefix_len

            if rel_start >= 0:
                val = highlight_span(val, rel_start, rel_end)

        context_parts.append(val)

    return " | ".join(context_parts)


def collect_row_cells(
    start_idx: int,
    target_row_id: int,
    all_lines: list[str],
) -> list[tuple[int, str]]:
    """
    Collect all cells belonging to a specific grid row.

    Args:
        start_idx: Index to start searching from.
        target_row_id: Row identifier to collect.
        all_lines: All nearby lines.

    Returns:
        Sorted list of (column_id, cell_value).
    """
    cells = []

    for i in range(start_idx, -1, -1):
        m = grid_pattern.match(all_lines[i])
        if m and int(m.group(1)) == target_row_id:
            cells.append((int(m.group(2)), m.group(3)))
        else:
            break

    cells.reverse()

    for i in range(start_idx + 1, len(all_lines)):
        m = grid_pattern.match(all_lines[i])
        if m and int(m.group(1)) == target_row_id:
            cells.append((int(m.group(2)), m.group(3)))
        else:
            break

    cells.sort()
    return cells


def find_grid_header(
    all_lines: list[str],
    current_idx: int,
    row_id: int,
) -> str:
    candidate_headers = []

    for i in range(current_idx, -1, -1):
        m = grid_pattern.match(all_lines[i])
        if not m:
            continue

        cid = int(m.group(1))
        if cid in (0, 1) and cid != row_id:
            candidate_headers.append((cid, i))

    for header_row_id, header_line_idx in candidate_headers:
        h_cells = collect_row_cells(header_line_idx, header_row_id, all_lines)

        if h_cells and all(c[1].strip().lower().startswith("unnamed") for c in h_cells):
            continue

        return " | ".join(c[1] for c in h_cells)

    return ""


def find_text_header(raw_text: str, line_start: int) -> str:
    """
    Find a descriptive header preceding a line in free text.

    Args:
        raw_text: Full raw text.
        line_start: Start index of the current line.

    Returns:
        Header string or empty string if not found.
    """
    curr_pos = line_start

    for _ in range(10):
        if curr_pos <= 0:
            break
        prev_nl = raw_text.rfind("\n", 0, curr_pos - 1)
        ls = prev_nl + 1 if prev_nl != -1 else 0
        le = curr_pos - 1
        l_text = raw_text[ls:le].strip()

        if l_text and re.search(r"table|supplementary|figure|file", l_text, flags=re.IGNORECASE):
            return l_text

        curr_pos = ls

    first_lines = [l.strip() for l in raw_text[:500].splitlines() if l.strip()]
    return first_lines[0] if first_lines else ""


def build_paragraph(match: re.Match, raw_text: str) -> str:
    """
    Build a human-readable paragraph around a matched variant.
    Handles both tabular (grid) and free-text formats.
    """
    start = match.start()
    end = match.end()

    variant_start = start + 1 if not raw_text[start].isalnum() else start

    line_start, line_end = find_line_bounds(raw_text, variant_start)
    current_line = raw_text[line_start:line_end]

    grid_match = grid_pattern.match(current_line)

    if grid_match:
        row_id = int(grid_match.group(1))

        before, after = get_nearby_lines(raw_text, line_start, line_end)
        all_nearby = before + [current_line] + after
        current_idx = len(before)

        row_cells = reconstruct_grid_row(all_nearby, current_idx, row_id)

        context = build_grid_context(
            row_cells,
            current_line,
            variant_start,
            line_start,
            end,
        )

        header = find_grid_header(all_nearby, current_idx, row_id)

    else:
        v_start = variant_start - line_start
        v_end = end - line_start
        context = highlight_span(current_line, v_start, v_end)
        header = find_text_header(raw_text, line_start)

    result = f"[{header}] {context}" if header else context
    return to_human_readable(result)


def update_suppl_data(articles: list[Article], variant: Variant) -> None:
    articles_with_suppl_data = [a for a in articles if len(a.suppl_data_list) > 0]

    for article in articles_with_suppl_data:
        for sd in article.suppl_data_list:
            if sd.snippets:
                pattern = compile_pattern(sd.snippets)
            else:
                pattern = compile_pattern(variant.terms)

            for m in re.finditer(pattern, sd.raw_text):
                if not m.group().strip():
                    continue
                paragraph = build_paragraph(m, sd.raw_text)

                if is_new_paragraph(paragraph, sd.paragraphs):
                    sd.paragraphs.append(paragraph)

    remove_articles_with_no_match(articles_with_suppl_data)


if __name__ == "__main__":
    grid_text = (
        "0\t0\tGene\n0\t1\tVariant\n0\t2\tEffect\n"
        "1\t0\tBRCA1\n1\t1\tc.70T>C\n1\t2\tPathogenic"
    )
    match_obj = re.search(r"[^\d\*\+a-zA-Z-]c\.70T>C", grid_text)
    print(build_paragraph(match_obj, grid_text))

    reg_text = (
        "Supplementary Table 1. Clinical findings.\n"
        "Patient ID\tVariant\tPhenotype\n1\tc.70T>C\tBreast cancer"
    )
    match_obj_reg = re.search(r"[^\d\*\+a-zA-Z-]c\.70T>C", reg_text)
    print(build_paragraph(match_obj_reg, reg_text))

    reg_text_2 = "Table 1\nc.70T>C is a variant"
    match_obj_reg_2 = re.search(r"\nc\.70T>C", reg_text_2)
    print(build_paragraph(match_obj_reg_2, reg_text_2))
