import csv
import io
import re
import statistics

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
UNNAMED_RE = re.compile(r"(?:^|\|)Unnamed:\s*\d+", flags=re.IGNORECASE)


def find_line_bounds(raw_text: str, pos: int) -> tuple[int, int]:
    """Find the start and end indices of the line containing the given position."""
    # logger.info(f"Finding line bounds for position {pos}")
    line_start = raw_text.rfind("\n", 0, pos) + 1
    line_end = raw_text.find("\n", pos)
    if line_end == -1:
        line_end = len(raw_text)
    # logger.info(f"Line bounds found: {line_start} to {line_end}")
    return line_start, line_end


def split_columns(line: str) -> list[str]:
    """Split a line into columns using various delimiters."""
    # logger.info("Splitting line into columns")
    for d in DELIMITERS:
        if line.count(d) >= 2:
            # logger.info(f"Split using delimiter '{d}'")
            return [c.strip() for c in line.split(d)]
    # Fallback to multiple spaces
    # logger.info("Split using multiple spaces fallback")
    return re.split(r"\s{2,}", line)


def header_score(columns: list[str]) -> float:
    """Score how likely a list of columns is a header row."""
    # logger.info(f"Scoring header candidates for columns: {columns[:5]}...")
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
    # logger.info(f"Final header score: {score}")
    return score


def is_cell_coordinate_table(text: str) -> tuple[bool, int]:
    """
    Detect if text is in cell-coordinate format (row col value).
    Return also the number of columns.
    """
    # logger.info("Checking for cell-coordinate table format")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    min_lines = min(20, len(lines))

    matching = []
    for i, line in enumerate(lines[:min_lines]):
        if i == 0:
            if not re.match(r"^0\t0\t.+$", line):                   # the first line has to be 0 0 some-text
                return False, -1
            else:
                matching.append(line)
        else:
            if CELL_COORD_RE.match(line):
                matching.append(line)

    if len(matching) < min_lines * 0.8:                                    # 80 % of the first 20 lines or of all lines must match
        return False, -1

    cols = []
    for l in matching:
        parts = l.split(maxsplit=2)
        if len(parts) >= 2:
            cols.append(int(parts[1]))

    return True, len(set(cols))


def reconstruct_coordinate_table(text: str) -> list[list[str]]:
    """Convert cell-coordinate format to a 2D list of rows."""
    # logger.info("Reconstructing cell-coordinate table")
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
    # logger.info(f"Reconstructed table with {len(table)} rows and {max(len(r) for r in table)} columns.")
    return table


def is_csv_like_table(text: str) -> tuple[bool, str | None]:
    """
    Heuristically detect whether text resembles a CSV-like table.
    We detect it in at most 20 lines by counting the number of delimiters in each line.
    Return also the delimiter used if found.
    """
    lines = []
    for line in text.splitlines():
        if line.strip():
            lines.append(line)
            if len(lines) == 20:
                break

    if not lines:
        return False, None

    delimiter_totals = {}
    delimiter_line_hits = {}

    for delimiter in DELIMITERS:
        total = 0
        hits = 0

        for line in lines:
            count = line.count(delimiter)
            if count:
                total += count
                hits += 1

        if hits >= max(3, len(lines) // 2):
            delimiter_totals[delimiter] = total
            delimiter_line_hits[delimiter] = hits

    if not delimiter_totals:
        return False, None

    probable_delimiter = max(
        delimiter_totals,
        key=lambda d: (delimiter_line_hits[d], delimiter_totals[d]),
    )

    counts = []
    for line in lines:
        count = line.count(probable_delimiter)
        if count:
            counts.append(count)

    if len(counts) < 3:
        return False, None

    median = statistics.median(counts)
    for value in counts:
        if abs(value - median) > 2:
            return False, None

    return True, probable_delimiter


def reconstruct_csv_like_table(text: str, delimiter: str) -> list[list[str]]:
    """Convert CSV-like table format to a 2D list of rows."""
    try:
        buffer = io.StringIO(text)
        reader = csv.reader(buffer, delimiter=delimiter)
        return list(reader)

    except Exception:
        # logger.warning("Failed to reconstruct CSV-like table. Fallback to split lines manually.")
        return list(
            map(lambda line: line.split(delimiter), text.splitlines())
        )


def get_title_header_and_context_from_table(table: list[list[str]], match_val: str):
    # TODO vylepšit, aby se header a context párovali k sobě jako dictionary
    row, title, context = "", "", ""
    best_score = 0
    header_index = -1
    header_row = []
    for i in range(min(len(table), 10)):
        score = header_score(table[i])
        if score > best_score:
            best_score, header_row, header_index = score, table[i], i
    header = "|".join([column for column in header_row if column.strip()])

    if header_index != 0:
        title = "|".join(table[0])
        title = re.sub(UNNAMED_RE, "", title)
        if title == "" and header_index != 1:       # can happen that in the first row there are only unnamed columns and the title is in the second row
            title = re.sub(UNNAMED_RE, "", "|".join(table[1]))
        title = re.sub(r"\s*\|{2,}\s*", "", title)

    for row in table:
        if any(match_val in cell for cell in row):
            context = "|".join(row)

    return title, header, context


def build_paragraph(match: re.Match, raw_text: str) -> str:
    """Construct a contextual paragraph around a regex match."""
    match_val = str(match.group()[1:].strip())
    # logger.info(f"Building paragraph for match '{match_val}'")

    is_cell_table, number_of_cols = is_cell_coordinate_table(raw_text)
    if is_cell_table:
        if number_of_cols <= 1:
            # logger.info("Too little columns in table. Skipping.")
            return ""
        else:
            # logger.info("Processing as cell-coordinate table")
            table = reconstruct_coordinate_table(raw_text)
            title, header, context = get_title_header_and_context_from_table(table, match_val)

    else:
        is_csv_table, delimiter = is_csv_like_table(raw_text)
        if is_csv_table:
            # logger.info("Processing as csv-like table")
            table = reconstruct_csv_like_table(raw_text, delimiter)
            title, header, context = get_title_header_and_context_from_table(table, match_val)

        else:
            # logger.info("Did not match either as cell-coordinate table or csv-like table")
            return ""  # TODO we don't process free text yet

    result = ""
    if header and context:
        if title:
            result = "title:" + to_human_readable(title) + "\n"
        result += "header:" + to_human_readable(header) + "\n" + "context:" + to_human_readable(context)
    elif context:
        if title:
            result = "title:" + to_human_readable(title) + "\n"
        result += "context:" + to_human_readable(context)
    else:
        return ""
    # logger.info(f"Paragraph built: {result[:100]}...")
    return result
