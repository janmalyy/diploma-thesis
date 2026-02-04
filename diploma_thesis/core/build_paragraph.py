import re
from typing import Tuple, List

from diploma_thesis.settings import logger
from diploma_thesis.utils.helpers import to_human_readable

COLUMN_KEYWORDS = {
    "gene", "genes", "variant", "mutation", "chromosome", "position", "start", "end",
    "hgvs", "protein", "amino", "exon", "ref", "alt", "allele", "id", "sample",
    "patient", "type", "classification", "significance", "frequency", "maf", "patient id", "phenotype group",
    "zygosity", "rs", "dbsnp", "build", "transcript", "symbol", "case", "control"
}
DELIMITERS = [",", "\t", ";"]
CELL_COORD_RE = re.compile(r"^\d+\t\d+\t.+$")


def find_line_bounds(raw_text: str, pos: int) -> Tuple[int, int]:
    """Find the start and end indices of the line containing the given position."""
    logger.info(f"Finding line bounds for position {pos}")
    line_start = raw_text.rfind("\n", 0, pos) + 1
    line_end = raw_text.find("\n", pos)
    if line_end == -1:
        line_end = len(raw_text)
    logger.info(f"Line bounds found: {line_start} to {line_end}")
    return line_start, line_end


def split_columns(line: str) -> List[str]:
    """Split a line into columns using various delimiters."""
    logger.info("Splitting line into columns")
    for d in DELIMITERS:
        if line.count(d) >= 2:
            logger.info(f"Split using delimiter '{d}'")
            return [c.strip() for c in line.split(d)]
    # Fallback to multiple spaces
    logger.info("Split using multiple spaces fallback")
    return re.split(r"\s{2,}", line)


def header_score(columns: List[str]) -> float:
    """Score how likely a list of columns is a header row."""
    logger.info(f"Scoring header candidates for columns: {columns[:5]}...")
    if len(columns) < 2:
        return 0.0
    score = 0.0
    for c in columns:
        cl = c.lower()
        if cl in COLUMN_KEYWORDS:
            score += 2.0
        elif any(k in cl for k in COLUMN_KEYWORDS):
            score += 1.0
        if re.fullmatch(r"[^\t\d]{2,50}", c):
            score += 0.5
        if re.search(r"\d", c):
            score -= 0.5
    logger.info(f"Final header score: {score}")
    return score


def is_cell_coordinate_table(text: str) -> bool:
    """Detect if text is in cell-coordinate format (row col value)."""
    logger.info("Checking for cell-coordinate table format")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    min_lines = min(20, len(lines))

    matching = []
    for i, line in enumerate(lines[:min_lines]):
        if i == 0:
            if not re.match(r"^0\t0\t.+$", line):                   # the first line has to be 0 0 some-text
                return False
            else:
                matching.append(line)
        elif i == 1:
            if not re.match(r"^(0\t1\t.+)|(1\t0\t.+)$", line):      # the second line has to be 0 1 some-text or 1 0 some-text
                return False
            else:
                matching.append(line)
        else:
            if CELL_COORD_RE.match(line):
                matching.append(line)

    if len(matching) < min_lines * 0.8:                                    # 80 % of the first 20 lines or of all lines must match
        return False

    cols = []
    for l in matching:
        parts = l.split(maxsplit=2)
        if len(parts) >= 2:
            cols.append(int(parts[1]))

    is_coord = max(cols or [0]) >= 1        # has at least two columns
    logger.info(f"Is cell-coordinate table: {is_coord}")
    return is_coord


def reconstruct_coordinate_table(text: str) -> List[List[str]]:
    """Convert cell-coordinate format to a 2D list of rows."""
    logger.info("Reconstructing cell-coordinate table")
    cells = []
    max_col = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or not CELL_COORD_RE.match(line):
            continue
        parts = line.split(maxsplit=2)
        row_index, column_index = int(parts[0]), int(parts[1])
        value = parts[2] if len(parts) > 2 else ""
        cells.append((row_index, column_index, value))
        max_col = max(max_col, column_index)

    max_col = min(max_col, 100)

    rows_dict = {}
    for r, c, v in cells:
        if r not in rows_dict:
            rows_dict[r] = [""] * (max_col + 1)
        if c < len(rows_dict[r]):
            rows_dict[r][c] = v

    table = [rows_dict[r] for r in sorted(rows_dict.keys())]
    logger.info(f"Reconstructed table with {len(table)} rows and {max(len(r) for r in table)} columns.")
    return table


def build_paragraph(match: re.Match, raw_text: str) -> str:
    """Construct a contextual paragraph around a regex match."""
    logger.info(f"Building paragraph for match '{match.group()[1:]}'")
    start, end = match.start(), match.end()
    # Ensure start doesn't land on a leading non-alphanumeric if it was part of the regex prefix
    variant_start = start + 1 if not raw_text[start].isalnum() else start

    line_start, line_end = find_line_bounds(raw_text, variant_start)
    current_line = raw_text[line_start:line_end]

    header, context = "", ""

    if is_cell_coordinate_table(raw_text):
        logger.info("Processing as cell-coordinate table")
        table = reconstruct_coordinate_table(raw_text)
        if table:
            best_score = 0
            header_row = []
            for i in range(min(len(table), 5)):
                score = header_score(table[i])
                if score > best_score:
                    best_score, header_row = score, table[i]
            header = "|".join([column for column in header_row if column.strip()])
            match_val = match.group(0).strip()
            # Find the row containing the match
            for row in table:
                if any(match_val in cell for cell in row):
                    context = "|".join(row)
                    break

    else:
        return ""  # TODO we don't process free text
        # logger.info("Processing as free text")
        # context = current_line
        # header = find_text_header(raw_text, line_start)

    if header and context:
        result = "header:" + to_human_readable(header) + "\n" + "context:" + to_human_readable(context)
    elif context:
        result = "context:" + to_human_readable(context)
    else:
        return ""
    logger.info(f"Paragraph built: {result[:100]}...")
    return result
