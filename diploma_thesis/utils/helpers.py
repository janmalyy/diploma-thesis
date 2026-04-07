import datetime
import html
import json
import re
import string
import time
from pathlib import Path
from xml.dom.minidom import parseString

from lxml import etree

from diploma_thesis.settings import DATA_DIR, PACKAGE_DIR, logger

# TODO Budu chtít nějak zachovat tu pozici, abych ji tam pak mohl zvýrazněnou vrátit do závěrečného kontextu
#  If you need to extract those IDs later, you can use: re.findall(r'concept_id=\"(.*?)\"', text)
# [^">] matches anything not a quote or a closing bracket
# "[^"]*" matches a full quoted string (allowing > inside)
# The combination ensures we only stop at a > that is NOT inside quotes

SPAN_PATTERN = r'<span(?:[^">]|"[^"]*")*>(.*?)</span>'
ALL_SPACES_PATTERN = r"(?:&nbsp;?|&#160;|[  \s])+"
ANNOTATION_PATTERN = re.compile(r"\[[^\]]+:\s*([^\]]+)\]")


def to_human_readable(text: str) -> str:
    text = re.sub(SPAN_PATTERN, r"\1", text)
    text = html.unescape(text)
    text = re.sub(ALL_SPACES_PATTERN, " ", text.strip())
    return text


def to_machine_comparable(text: str) -> str:
    text = re.sub("→", ">", text)
    punctuation_map = str.maketrans(string.punctuation, " " * len(string.punctuation))
    text = text.translate(punctuation_map)
    return " ".join(text.split()).lower()


def write_xml(root, filename: str | Path, make_machine_comparable: bool = False, only_print: bool = False) -> None:
    """Writes an XML element tree to a file with pretty formatting with indents."""
    if make_machine_comparable:
        for passage in root.xpath(".//passage"):
            text_element = passage.find("text")
            if text_element is None or text_element.text is None:
                continue
            text_element.text = to_machine_comparable(text_element.text)

    xml_str = etree.tostring(root, encoding="utf-8")
    parsed_xml = parseString(xml_str).toprettyxml(indent="  ")
    lines = [line for line in parsed_xml.splitlines() if line.strip()]

    if only_print:
        print("Printing XML to console:")
        for line in lines:
            print(line)
        print("End of XML.")
    else:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


THREE_TO_ONE = {
    "ala": "a",
    "arg": "r",
    "asn": "n",
    "asp": "d",
    "asx": "b",
    "cys": "c",
    "gln": "q",
    "glu": "e",
    "glx": "z",
    "gly": "g",
    "his": "h",
    "ile": "i",
    "leu": "l",
    "lys": "k",
    "met": "m",
    "phe": "f",
    "pro": "p",
    "ser": "s",
    "thr": "t",
    "trp": "w",
    "tyr": "y",
    "val": "v",
}
THREE_TO_ONE_PATTERN = re.compile("|".join(THREE_TO_ONE.keys()))

ONE_TO_THREE = {v: k for k, v in THREE_TO_ONE.items()}
ONE_TO_THREE_PATTERN = re.compile("|".join(ONE_TO_THREE.keys()))


def uniq(values: list[str]) -> list[str]:
    """Remove duplicates from a list while preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def normalize_variant(v: str) -> str:
    # todo vylepšit, nějak neumím regexpy
    v = v.lower()
    v = re.sub(r"\s+", "", v)
    v = re.sub(r"[^\w]", "", v)
    v = re.sub(r"[->/.]", "", v)
    v = re.sub(r"\bto\b", "", v)
    v = THREE_TO_ONE_PATTERN.sub(lambda m: THREE_TO_ONE[m.group()], v)
    return v


def extend_variant_name(variant: str) -> str:
    """
    Example:
        input: BRCA1 A7C
        output: BRCA1 p.arg7cys
    """
    gene, change = variant.split()
    change = change.lower()
    change = ONE_TO_THREE_PATTERN.sub(lambda m: ONE_TO_THREE[m.group()], change)
    return gene + f" p.{change}"


def compile_variant_pattern(input_list: list[str]) -> re.Pattern:
    """Compile a regex pattern for variant terms."""
    # Sort by length descending to match longer terms first
    input_list = sorted(input_list, key=len, reverse=True)
    # Prefix with a non-alphanumeric character (except some symbols) to avoid partial matches
    escaped = [r"[^\d\*\+a-zA-Z-]" + re.escape(v) for v in input_list]
    pattern = re.compile("|".join(escaped))
    return pattern


def get_prompt(path: str) -> str:
    with open(PACKAGE_DIR / "prompts" / path) as f:
        return f.read()


def build_prompt(replacements: dict[str, str], prompt: str) -> str:
    """keys not present in the prompt text are ignored."""
    for key, value in replacements.items():
        prompt = prompt.replace(key, str(value))

    return prompt


def shorten_paragraph(
        text: str,
        terms: list[str],
        window_size: int = 200,
        max_gap: int = 400,
        max_paragraph_length: int = 2100,
        total_max_paragraph_length: int = 4000,
) -> str:
    """
    Processes a paragraph to create a context-aware summary of genetic variant mentions.

    Args:
        text: The full text of the paragraph.
        terms: A list of search variants or terms to locate.
        window_size: Number of characters to preserve as context around each match.
        max_gap: The maximum distance between ranges to merge them into a single fragment.
        max_paragraph_length: The maximum length of the paragraph to leave the paragraph as is.
                              At default set to 2100 which is +- Q3 for fulltext paragraphs lengths.
        total_max_paragraph_length: The total maximum length of the paragraph to return.
                                    Anything after this limit is cut.
                                    At default set to 4000 which covers +- 97 % of fulltext paragraphs lengths.

    Returns:
        A string containing the extracted fragments joined by ellipses,
        or an empty string if no terms are found.
    """
    if len(text) < max_paragraph_length:
        return text

    pattern = compile_variant_pattern(terms)
    matches = list(re.finditer(pattern, text))

    if not matches:
        # logger.info(f"No matches found in paragraph: {text}, with terms: {terms}.")
        return ""

    # 1. Define base ranges around each match
    ranges = []
    for m in matches:
        ranges.append({
            "start": max(0, m.start() - window_size),
            "end": min(len(text), m.end() + window_size),
            "match_start": m.start(),
            "match_end": m.end()
        })

    # 2. Merge overlapping or nearby ranges
    merged_chunks = []
    if ranges:
        curr = ranges[0]
        # Rule: Start from 0 if the first match is close to the beginning
        if curr["start"] < max_gap:
            curr["start"] = 0

        for i in range(1, len(ranges)):
            nxt = ranges[i]
            if nxt["start"] <= curr["end"] + max_gap:
                curr["end"] = max(curr["end"], nxt["end"])
                # Keep track of the last match's end in this merged chunk
                curr["match_end"] = nxt["match_end"]
            else:
                merged_chunks.append(curr)
                curr = nxt
        merged_chunks.append(curr)

    # 3. Extract fragments with precise word alignment
    actual_length = 0
    fragments = []
    for chunk in merged_chunks:
        start, end = chunk["start"], chunk["end"]

        # Align start to the next space, but do not cross the first match of this chunk
        actual_start = start
        if start > 0:
            first_space = text.find(" ", start)
            if 0 <= first_space < chunk["match_start"]:
                actual_start = first_space + 1

        # Align end to the previous space, but do not cross the last match of this chunk
        actual_end = end
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > chunk["match_end"]:
                actual_end = last_space

        fragment = text[actual_start:actual_end].strip()

        # Add ellipses as needed
        if actual_start > 0:
            fragment = "..." + fragment
        if actual_end < len(text):
            fragment = fragment + "..."

        actual_length += len(fragment)
        fragments.append(fragment)
        if actual_length > total_max_paragraph_length:
            break

    # Join and clean up redundant ellipses
    final_text = " ".join(fragments)
    final_text = re.sub(r"\.{4,}", "...", final_text)

    return final_text


def transform_mim2gene_to_json(input_path: str | Path, output_path: str | Path) -> None:
    """
    throw-away function to transform MIM2Gene mapping file to JSON Gene2MIM mapping JSON file.
    use: transform_mim2gene_to_json(DATA_DIR / "mim2gene.txt", DATA_DIR / "gene2mim.json")
    """
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
        lines = text.split("\n")

    gene2mim = {}
    for i, line in enumerate(lines):
        if "\tgene\t" in line:
            splits = line.split("\t")
            gene2mim[splits[3]] = splits[0]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(gene2mim, f, indent=4)


def get_omim_url(gene_symbol: str) -> str | None:
    """
    Construct the OMIM URL for a given gene symbol.
    """
    if not gene_symbol:
        logger.warning("No gene symbol provided.")
        return None

    gene2mim_path = PACKAGE_DIR / "utils" / "gene2mim.json"
    if not gene2mim_path.exists():
        logger.warning(f"Gene2MIM mapping file not found, searched at '{gene2mim_path}'.")
        return None

    with open(gene2mim_path, "r", encoding="utf-8") as f:
        gene2mim = json.load(f)
    try:
        omim_id = gene2mim.get(gene_symbol.upper())
    except KeyError:
        logger.warning(f"No OMIM ID found in the mapping for gene symbol '{gene_symbol}'.")
        return None

    return f"https://www.omim.org/entry/{omim_id}"


def end(start):
    return round(time.time() - start, 2)


def transform_paragraph_for_display(paragraph: str | dict, terms: list[str]) -> str | None:
    """
    1)
    If the paragraph is string (it is fulltext): remove annotations
    If the paragraph is dict (it is suppl data): transform it to string

    2)
    makes all specified terms bold
    """
    if isinstance(paragraph, str):
        # 1. [type: value] -> value
        text = ANNOTATION_PATTERN.sub(r"\1", paragraph)

        if not terms:
            return text

    elif isinstance(paragraph, dict):
        text = ""
        if paragraph.get("title"):
            text += "Table title: " + paragraph["title"] + "\n"
        if paragraph.get("header"):
            text += "Column names:\n" + paragraph["header"] + "\n"
        if paragraph.get("context"):
            text += "Rows:\n" + "\n".join(paragraph["context"])
    else:
        raise TypeError(f"Unsupported paragraph type: {type(paragraph)}, content: {paragraph}")

    # 2. term -> **term**
    escaped_terms = sorted([re.escape(t) for t in terms], key=len, reverse=True)
    terms_pattern = "|".join(escaped_terms)
    pattern_string = rf"(?<![\d\*\+a-zA-Z-])({terms_pattern})(?![\d\*\+a-zA-Z-])"
    final_pattern = re.compile(pattern_string, re.IGNORECASE)

    return final_pattern.sub(r"**\1**", text)


def get_unique_safe_filename(original_filename: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

    filename = f"{original_filename}_{timestamp}.json"

    return re.sub(r'[<>:"/\\|?*]', "_", filename)
