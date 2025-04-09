import xml.etree.ElementTree
from types import NoneType

import requests
from xml.etree import ElementTree as ET
from xml.dom.minidom import parseString
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from diploma_thesis.settings import PACKAGE_DIR


def get_pubtator_data(query: str) -> ET.Element | None:
    """
    Fetches data from PubTator based on the specified query.

    Args:
        query (str): The search query.

    Returns:
        xml.etree.ElementTree.Element: Embedded xml structure.
    """
    # note we use direct IP as there are problems with DNS resolution
    base_url = "https://130.14.29.110/research/pubtator3-api/publications/export/biocxml?pmids="
    query_processed = query.replace(" ", "%20")
    search_url = base_url + query_processed

    # Fix SSL verification issue by setting 'Host' in headers
    headers = {
        "Host": "www.ncbi.nlm.nih.gov",  # Manually set the correct hostname
        "User-Agent": "Mozilla/5.0"  # Helps avoid bot blocking
    }

    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    try:
        # verify=False is not recommended, but with True it does not work :/
        search_response = session.get(search_url, headers=headers, verify=False, timeout=10)

        search_response.raise_for_status()  # check for HTTP errors

        if "xml" not in search_response.headers.get("Content-Type", "").lower():
            raise ValueError("Received non-XML response from PubTator API")

        root = ET.fromstring(search_response.content.decode(encoding="utf-8"))

        return root

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        raise


def write_pretty_xml(root: ET.Element, filename: str) -> None:
    """Writes an XML element tree to a file with pretty formatting with indents."""
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed_xml = parseString(xml_str).toprettyxml(indent="  ")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(parsed_xml)


class Node:
    def __init__(self, name, identifier, ner_type, count=1):
        self.name = name
        self.identifier = identifier
        self.ner_type = ner_type
        self.count = count


def node_pretty_print(node: Node) -> None:
    print(f"Node")
    print(f"ner_type:\t{node.ner_type}")
    print(f"name:\t{node.name}")
    print(f"id:\t\t{node.identifier}")
    print(f"count:\t{node.count}")
    print()


class Edge:
    def __init__(self, relation_type, node1, node2, score):
        self.relation_type = relation_type
        self.node1 = node1
        self.node2 = node2
        self.score = score


def edge_pretty_print(edge: Edge) -> None:
    print(f"Edge")
    print(f"relation_type:\t{edge.relation_type}")
    print(f"node1:\t{edge.node1}")
    print(f"node2:\t{edge.node2}")
    print(f"score:\t{edge.score}")
    print()


def get_document_from_xml(xml_file_path: str) -> ET.Element:
    with open(xml_file_path, "r", encoding="utf-8") as file:
        xml_as_string = file.read()
        root = ET.fromstring(xml_as_string)  # Root is <collection>

    document = root.find("document")
    if document is None:
        raise ValueError("No <document> element found in XML")

    return document


def get_nodes_from_xml(xml_file_path: str) -> list[Node]:
    document = get_document_from_xml(xml_file_path)

    nodes_dict = {}  # Dictionary for fast lookup (identifier -> Node)

    for passage in document.findall("passage"):
        for annotation in passage.findall("annotation"):
            identifier = None

            for infon in annotation.findall("infon"):
                key = infon.get("key")
                if key == "identifier":
                    identifier = infon.text
                elif key == "type":
                    ner_type = infon.text
            if identifier is None:  # there is no id associated with the entity
                identifier = f"UNKNOWN:{annotation.get("id")}"
            if identifier in nodes_dict:
                nodes_dict[identifier].count += 1  # Increase count for existing node
            else:
                name = annotation.find("text").text
                nodes_dict[identifier] = Node(name, identifier, ner_type)  # Add new node

    return list(nodes_dict.values())  # Convert dictionary values to a list


def get_edges_from_xml(xml_file_path: str) -> list[Edge]:
    document = get_document_from_xml(xml_file_path)

    edges_list = []

    for relation in document.findall("relation"):
        for infon in relation.findall("infon"):
            key = infon.get("key")
            if key == "score":
                score = infon.text
            elif key == "role1":
                node1 = infon.text.split("|")[1]  # origin looks like "Gene|7157" and we retain only the identifier
            elif key == "role2":
                node2 = infon.text.split("|")[1]
            elif key == "type":
                relation_type = infon.text

        edges_list.append(Edge(relation_type, node1, node2, score))

    return edges_list


if __name__ == "__main__":
    result = get_pubtator_data("23747889")  # Example PubMed ID
    write_pretty_xml(result, "test2.xml")
    nodes_list = get_nodes_from_xml(PACKAGE_DIR / "pubtator3" / "test2.xml")
    edges_list = get_edges_from_xml(PACKAGE_DIR / "pubtator3" / "test2.xml")

    for i in range(len(nodes_list)):
        node_pretty_print(nodes_list[i])
    print(len(nodes_list))

    for i in range(len(edges_list)):
        edge_pretty_print(edges_list[i])
    print(len(edges_list))
