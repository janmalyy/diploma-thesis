import html
import re
import string
from pathlib import Path
from typing import Any, Generator
from xml.dom.minidom import parseString

from lxml import etree

from diploma_thesis.settings import PACKAGE_DIR

# TODO Budu chtít nějak zachovat tu pozici, abych ji tam pak mohl zvýrazněnou vrátit do závěrečného kontextu
#  If you need to extract those IDs later, you can use: re.findall(r'concept_id=\"(.*?)\"', text)
# [^">] matches anything not a quote or a closing bracket
# "[^"]*" matches a full quoted string (allowing > inside)
# The combination ensures we only stop at a > that is NOT inside quotes

span_pattern = r'<span(?:[^">]|"[^"]*")*>(.*?)</span>'
all_spaces_pattern = r"(?:&nbsp;?|&#160;|[  \s])+"


def make_batches(iterable: list, size: int) -> Generator[list, Any, None]:
    """
    Split a list into smaller batches of fixed size.
    Example:
        >>> list(make_batches([1, 2, 3, 4, 5, 6, 7], size=3))
        [[1, 2, 3], [4, 5, 6], [7]]
    """
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def to_human_readable(text: str) -> str:
    text = re.sub(span_pattern, r"\1", text)
    text = html.unescape(text)
    text = re.sub(all_spaces_pattern, " ", text.strip())
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
    # logger.info(f"Compiling variant pattern for {len(input_list)} terms")
    # Sort by length descending to match longer terms first
    input_list = sorted(input_list, key=len, reverse=True)
    # Prefix with a non-alphanumeric character (except some symbols) to avoid partial matches
    escaped = [r"[^\d\*\+a-zA-Z-]" + re.escape(v) for v in input_list]
    pattern = re.compile("|".join(escaped))
    # logger.info("Variant pattern compiled successfully")
    return pattern


def get_prompt(path: str) -> str:
    with open(PACKAGE_DIR / "prompts" / path) as f:
        return f.read()


def build_prompt(replacements: dict[str, str], prompt: str) -> str:
    # keys not present in the prompt are ignored
    for key, value in replacements.items():
        prompt = prompt.replace(key, str(value))

    return prompt
