import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3 import Retry
from xml.etree import ElementTree as ET
from diploma_thesis.new.models import Article
from diploma_thesis.utils.parse_xml import write_pretty_xml

urllib3.disable_warnings()


def _parse_pubtator_document(article: Article, document: ET.Element) -> None:
    """
    Parses BioC-XML Pubtator document, applies annotations to relevant passages,
    and sets title, abstract, and paragraphs to the article.
    """
    annotated_paragraphs = []

    for passage in document.findall(".//passage"):
        text_element = passage.find("text")
        if text_element is None or text_element.text is None:
            continue
        original_text = text_element.text

        # TODO možná hledat líp než jako prvních 20 znaků
        is_relevant = any(
            re.search(re.escape(snippet[:20].strip()), original_text, flags=re.IGNORECASE)
            for snippet in article.snippets if len(snippet) >= 5
        )

        passage_type_elem = passage.find("./infon[@key='type']")
        passage_type = passage_type_elem.text if passage_type_elem is not None else ""

        if is_relevant or passage_type in ("front", "abstract"):
            passage_offset = int(passage.find("offset").text)
            annotations = []
            for ann in passage.findall("annotation"):
                ann_type = ann.find("./infon[@key='type']").text
                if ann_type == "Species":
                    continue

                loc = ann.find("location")
                local_offset = int(loc.get("offset")) - passage_offset
                length = int(loc.get("length"))

                annotations.append({
                    'start': local_offset,
                    'end': local_offset + length,
                    'type': ann_type,
                    'text': ann.find("text").text
                })

            # Sort annotations reverse to avoid index shift
            annotations.sort(key=lambda x: x['start'], reverse=True)
            annotated_text = original_text
            for ann in annotations:
                start, end = ann['start'], ann['end']
                label = f"[{ann['type']}: {annotated_text[start:end]}]"
                annotated_text = annotated_text[:start] + label + annotated_text[end:]

            if passage_type == "front":
                article.title = annotated_text
            elif passage_type == "abstract":
                article.abstract = annotated_text
            else:
                annotated_paragraphs.append(annotated_text)

    article.paragraphs = "\n".join(annotated_paragraphs)


def _get_clean_text(element: ET.Element) -> str:
    """
    Recursively extracts all text from an element and its children,
    handling nested tags like <italic> or <xref> gracefully.
    """
    if element is None:
        return ""
    text = "".join(element.itertext())
    return " ".join(text.split()).strip()


def _parse_pmc_document(article: Article, article_root: ET.Element) -> None:
    """
    Parses PMC XML using tag filtering to handle complex body structures.
    """
    # 1. Extract Title
    title_elem = article_root.find(".//front//article-title")
    if title_elem is not None:
        article.title = _get_clean_text(title_elem)

    # 2. Extract Abstract
    abstract_paras = article_root.findall(".//front//abstract//p")
    if abstract_paras:
        article.abstract = " ".join(_get_clean_text(p) for p in abstract_paras)

    # 3. Extract Body & Back (Handling tables, lists, and sections)
    found_content = []
    seen_texts = set()

    # Tags we want to extract text from
    target_tags = {'p', 'title', 'td', 'li'}

    for section_name in ['body', 'back']:
        section = article_root.find(f".//{section_name}")
        if section is None:
            continue

        for node in section.iter():
            if node.tag in target_tags:
                original_text = _get_clean_text(node)

                if not original_text or original_text in seen_texts:
                    continue

                is_relevant = any(
                    re.search(re.escape(snippet[:20].strip()), original_text, flags=re.IGNORECASE)
                    for snippet in article.snippets if len(snippet) >= 5
                )

                if is_relevant:
                    found_content.append(original_text)
                    seen_texts.add(original_text)

    article.paragraphs = "\n".join(found_content)


def _extract_attributes(article: Article, document: ET.Element):
    """Extracts article attributes. Mock implementation."""
    # Study Type
    text = " ".join([t.text for t in document.findall(".//text") if t.text])
    if "clinical trial" in text.lower():
        article.study_type = "Clinical Trial"
    elif "case report" in text.lower():
        article.study_type = "Case Report"
    else:
        article.study_type = "Observational Study"

    # Disease
    for ann in document.findall(".//annotation"):
        if ann.find("./infon[@key='type']").text == "Disease":
            article.disease = ann.find("text").text
            break


def annotate_raw_text(text: str) -> str:
    """
    Cleans raw text and submits it to PubTator for annotations.
    Mock implementation as original was not working.
    """
    return f"[Annotated Raw Text Mock]\n{text}"


# Constants
PUBTATOR_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/pmc_export/biocxml"
EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
HEADERS = {"Host": "www.ncbi.nlm.nih.gov", "User-Agent": "Mozilla/5.0"}


def get_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(HEADERS)
    return session


def map_pubtator_xml(root: ET.Element) -> dict[str, ET.Element] | None:
    """Parses XML content and maps IDs to their respective document elements."""
    return {
        f"PMC{doc.find('id').text}": doc
        for doc in root.findall("document")
        if doc.find("id") is not None
    }


def map_pmc_xml(root: ET.Element) -> dict[str, ET.Element] | None:
    """Parses XML content and maps IDs to their respective document elements."""
    id_xpath = ".//article-meta/article-id[@pub-id-type='pmcid']"

    article_map = {}
    for article in root.findall("article"):
        id_element = article.find(id_xpath)

        if id_element is not None and id_element.text:
            pmc_id = id_element.text.strip()
            article_map[pmc_id] = article

    return article_map


def fetch_resource(session: requests.Session, url: str, params: dict) -> dict[str, ET.Element]:
    """Generic fetcher that returns a mapped dictionary of XML elements."""
    try:
        # verify=False is not recommended but needed
        response = session.get(url, params=params, verify=False, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(e)

    root = root = ET.fromstring(response.content.decode("utf-8"))
    if "pubtator" in url:
        return map_pubtator_xml(root)
    elif "eutils" in url:
        return map_pmc_xml(root)
    else:
        raise ValueError(f"Invalid URL: {url}")


def update_articles_fulltext(articles: list[Article]):
    """
    Orchestrates the data fetching pipeline.
    """
    if not articles:
        return

    session = get_session()

    pmcid_to_article = {a.pmcid: a for a in articles}
    raw_ids = [a.pmcid for a in articles]
    ids_query = ",".join(raw_ids)

    pubtator_results = fetch_resource(session, PUBTATOR_URL, {"pmcids": ids_query})

    for pmcid, doc in pubtator_results.items():
        if pmcid in pmcid_to_article.keys():
            article = pmcid_to_article[pmcid]
            _parse_pubtator_document(article, doc)

    missing_ids = [pmcid for pmcid in pmcid_to_article.keys() if pmcid not in pubtator_results.keys()]
    if missing_ids:
        ncbi_params = {
            "db": "pmc",
            "id": ",".join(missing_ids),
            "rettype": "full",
            "retmode": "xml"
        }
        ncbi_results = fetch_resource(session, EUTILS_URL, ncbi_params)
        for pmcid in missing_ids:
            article = pmcid_to_article[pmcid]
            _parse_pmc_document(article, ncbi_results[pmcid])

    # _extract_attributes(article, ncbi_results[pmcid])


if __name__ == '__main__':
    pmcid = "PMC4925265"
    # pmcid = "PMC9516015"
    article = Article(pmcid=pmcid, snippets=["es with concern for predisposit"])
    results = fetch_resource(get_session(), EUTILS_URL, params={
        "db": "pmc",
        "id": "PMC4925265",
        "rettype": "full",
        "retmode": "xml"
    })
    _parse_pmc_document(article, results[pmcid])
    print(article.get_context())
