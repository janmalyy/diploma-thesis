import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3 import Retry
from lxml import etree
from diploma_thesis.new.models import Article
from diploma_thesis.utils.parse_xml import write_pretty_xml

urllib3.disable_warnings()


def stringify_children(node: etree._Element) -> str:
    """Joins all string parts excluding empty parts using lxml's itertext."""
    return "".join(text.strip() for text in node.itertext() if text)


def is_text_relevant(text: str, snippets: list[str]) -> bool:
    """
    Checks if a piece of text contains any of the provided snippets.
    Uses normalization to handle whitespace/newline inconsistencies.
    """
    if not text:
        return False

    normalized_text = " ".join(text.split()).lower()

    for snippet in snippets:
        if len(snippet) < 5:
            continue

        normalized_snippet = " ".join(snippet.split()).lower()

        search_term = normalized_snippet[:50]
        if search_term in normalized_text:
            return True
    return False


def _parse_pubtator_document(article: Article, document: etree._Element) -> None:
    """
    Parses BioC-XML Pubtator document, applies annotations to relevant passages.
    """
    annotated_paragraphs = []

    for passage in document.xpath(".//passage"):
        text_element = passage.find("text")
        if text_element is None or text_element.text is None:
            continue
        original_text = text_element.text

        passage_type_elem = passage.xpath("./infon[@key='type']")
        passage_type = passage_type_elem[0].text if passage_type_elem else ""

        if passage_type in ("front", "abstract") or is_text_relevant(original_text, article.snippets):
            offset_elem = passage.find("offset")
            passage_offset = int(offset_elem.text) if offset_elem is not None else 0

            annotations = []
            for ann in passage.xpath("annotation"):
                ann_type_elem = ann.xpath("./infon[@key='type']")
                ann_type = ann_type_elem[0].text if ann_type_elem else ""

                if ann_type == "Species":
                    continue

                loc = ann.find("location")
                if loc is not None:
                    local_offset = int(loc.get("offset")) - passage_offset
                    length = int(loc.get("length"))

                    ann_text_elem = ann.find("text")
                    annotations.append({
                        'start': local_offset,
                        'end': local_offset + length,
                        'type': ann_type,
                        'text': ann_text_elem.text if ann_text_elem is not None else ""
                    })

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


def _parse_pmc_document(article: Article, article_root: etree._Element) -> None:
    """
    Parses PMC XML, retaining abstract subparagraph titles and fixing snippet finding.
    """
    title_elems = article_root.xpath(".//front//article-title")
    if title_elems:
        article.title = stringify_children(title_elems[0])

    abstract_nodes = article_root.xpath(".//front//abstract//*[self::p or self::title]")
    if abstract_nodes:
        abstract_parts = []
        for node in abstract_nodes:
            node_text = stringify_children(node)
            if node.tag == "title":
                abstract_parts.append(f"{node_text}: " if node_text else "")
            else:
                abstract_parts.append(node_text)
        article.abstract = " ".join(filter(None, abstract_parts))

    found_content = []
    seen_texts = set()
    target_tags = {'p', 'title', 'td', 'li'}

    for section_name in ['body', 'back']:
        sections = article_root.xpath(f".//{section_name}")
        if not sections:
            continue

        for node in sections[0].iter():
            if node.tag in target_tags:
                original_text = stringify_children(node)

                if not original_text or original_text in seen_texts:
                    continue

                if is_text_relevant(original_text, article.snippets):
                    found_content.append(original_text)
                    seen_texts.add(original_text)

    article.paragraphs = "\n".join(found_content)


def _extract_attributes(article: Article, document: etree._Element):
    """Extracts article attributes. Mock implementation."""  # TODO
    # Study Type
    text_nodes = document.xpath(".//text")
    combined_text = " ".join([t.text for t in text_nodes if t.text])

    if "clinical trial" in combined_text.lower():
        article.study_type = "Clinical Trial"
    elif "case report" in combined_text.lower():
        article.study_type = "Case Report"
    else:
        article.study_type = "Observational Study"

    # Disease
    for ann in document.xpath(".//annotation"):
        ann_type_elem = ann.xpath("./infon[@key='type']")
        if ann_type_elem and ann_type_elem[0].text == "Disease":
            text_elem = ann.find("text")
            article.disease = text_elem.text if text_elem is not None else ""
            break


def annotate_raw_text(text: str) -> str:
    """
    Cleans raw text and submits it to PubTator for annotations.
    Mock implementation as original was not working.
    """
    return f"[Annotated Raw Text Mock]\n{text}"  # TODO


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


def map_pubtator_xml(root: etree._Element) -> dict[str, etree._Element]:
    """Parses XML content and maps IDs to their respective document elements."""
    article_map = {}
    for doc in root.xpath("document"):
        id_elem = doc.find("id")
        if id_elem is not None and id_elem.text:
            article_map[f"PMC{id_elem.text}"] = doc
    return article_map


def map_pmc_xml(root: etree._Element) -> dict[str, etree._Element]:
    """Parses XML content and maps IDs to their respective document elements."""
    id_xpath = ".//article-meta/article-id[@pub-id-type='pmcid']"

    article_map = {}
    for article in root.xpath("article"):
        id_elements = article.xpath(id_xpath)
        if id_elements and id_elements[0].text:
            pmc_id = id_elements[0].text.strip()
            article_map[pmc_id] = article

    return article_map


def fetch_resource(session: requests.Session, url: str, params: dict) -> dict[str, etree._Element]:
    """Generic fetcher that returns a mapped dictionary of lxml elements."""
    try:
        response = session.get(url, params=params, verify=False, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return {}

    # lxml.etree.fromstring handles bytes directly and is more robust
    root = etree.fromstring(response.content)
    write_pretty_xml(root, f"xml_response{pmcid}.xml")
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
    ids_query = ",".join([a.pmcid for a in articles])

    pubtator_results = fetch_resource(session, PUBTATOR_URL, {"pmcids": ids_query})

    for pmcid, doc in pubtator_results.items():
        if pmcid in pmcid_to_article:
            article = pmcid_to_article[pmcid]
            _parse_pubtator_document(article, doc)
            article.source = "pubtator"

    missing_ids = [pmcid for pmcid in pmcid_to_article if pmcid not in pubtator_results]
    if missing_ids:
        ncbi_params = {
            "db": "pmc",
            "id": ",".join(missing_ids),
            "rettype": "full",
            "retmode": "xml"
        }
        ncbi_results = fetch_resource(session, EUTILS_URL, ncbi_params)
        for pmcid in missing_ids:
            if pmcid in ncbi_results:
                article = pmcid_to_article[pmcid]
                _parse_pmc_document(article, ncbi_results[pmcid])
                article.source = "pmc"


if __name__ == '__main__':
    pmcid = "PMC8794197"    # pmc
    # test_article = Article(pmcid=pmcid, snippets=["Approximately 500 patients with AML and 350 with MDS were referred to the Department of Leukemia at UTMDACC during this same time period. "])
    test_article = Article(pmcid=pmcid, snippets=[
        "We selected 5 families with at least 2 cases of cutaneous melanoma among first-degree relatives, for a total of 10 individuals for WES."])
    res = fetch_resource(get_session(), EUTILS_URL, params={
        "db": "pmc",
        "id": pmcid,
        "rettype": "full",
        "retmode": "xml"
    })

    if pmcid in res:
        print(_parse_pmc_document(test_article, res[pmcid]))
        print(test_article.get_context())

    pmcid = "PMC8794197"  # pubtator
    test_article = Article(pmcid=pmcid, snippets=[
        "We selected 5 families with at least 2 cases of cutaneous melanoma among first-degree relatives, for a total of 10 individuals for WES."])
    res = fetch_resource(get_session(), PUBTATOR_URL, params={
        "pmcids": pmcid,
    })
    if pmcid in res:
        _parse_pubtator_document(test_article, res[pmcid])
        print(test_article.get_context())
