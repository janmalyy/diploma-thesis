from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom.minidom import parseString


def write_pretty_xml(root: ET.Element, filename: str | Path) -> None:
    """Writes an XML element tree to a file with pretty formatting with indents."""
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed_xml = parseString(xml_str).toprettyxml(indent="  ")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(parsed_xml)


def get_document_from_xml(xml_file_path: str) -> ET.Element:
    """
    Returns:
        ET.Element: xml structure with document element as root.
    """
    with open(xml_file_path, "r", encoding="utf-8") as file:
        xml_as_string = file.read()
        root = ET.fromstring(xml_as_string)  # Root is <collection>

    document = root.find("document")
    if document is None:
        raise ValueError("No <document> element found in XML.")

    return document


def get_title_with_abstract(xml_file_path: str) -> str:
    document = get_document_from_xml(xml_file_path)
    title_with_abstract = ""
    for passage in document.findall("passage"):
        for text in passage.findall("text"):
            title_with_abstract += " " + str(text.text)

    return title_with_abstract
