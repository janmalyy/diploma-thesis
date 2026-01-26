import html
import re
import string
from pathlib import Path
from typing import Generator, Any
from xml.dom.minidom import parseString

from lxml import etree

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


def write_xml(root, filename: str | Path) -> None:
    """Writes an XML element tree to a file with pretty formatting with indents."""
    for passage in root.xpath(".//passage"):
        text_element = passage.find("text")
        if text_element is None or text_element.text is None:
            continue
        text_element.text = to_machine_comparable(text_element.text)

    xml_str = etree.tostring(root, encoding="utf-8")
    parsed_xml = parseString(xml_str).toprettyxml(indent="  ")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(parsed_xml)
