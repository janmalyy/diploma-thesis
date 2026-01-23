import requests
from rapidfuzz import fuzz
from requests.adapters import HTTPAdapter
import urllib3
from urllib3 import Retry
from lxml import etree

from diploma_thesis.new.json_structure import write_json
from diploma_thesis.new.models import Article, TextBlock
from diploma_thesis.new.helpers import write_xml

urllib3.disable_warnings()


def check_text_for_snippets(text: TextBlock, snippets: list[TextBlock]) -> tuple[bool, list[TextBlock]]:
    """
    Checks if a piece of text contains any of the provided snippets.
    Uses normalization to handle whitespace/newline inconsistencies.
    """
    if not text or not snippets:
        return False, []
    matched_snippets = []
    for snippet in snippets:
        if len(snippet) < 5:
            continue
        score = fuzz.partial_ratio(snippet.machine_comparable, text.machine_comparable)
        if score > 90 and score != 100:
            print("score", round(score, 2))
            print("snippet", snippet.machine_comparable)
            print("text", text.machine_comparable)
        if score > 92:                          # this is an important threshold!
            matched_snippets.append(snippet)

    return len(matched_snippets) > 0, matched_snippets


def _parse_pubtator_document(article: Article, document: etree._Element) -> None:
    """
    Parses BioC-XML Pubtator document, applies annotations to relevant passages.
    """
    annotated_paragraphs = []

    for passage in document.xpath(".//passage"):
        text_element = passage.find("text")
        if text_element is None or text_element.text is None:
            continue
        text = TextBlock(text_element.text)

        passage_type_elem = passage.xpath("./infon[@key='type']")
        passage_type = passage_type_elem[0].text if passage_type_elem else ""

        match, matched_snippets = check_text_for_snippets(text, article.snippets)
        [article.snippets.remove(s) for s in matched_snippets]

        if passage_type in ("front", "abstract") or match:
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
            annotated_text = text.human_readable
            for ann in annotations:
                start, end = ann['start'], ann['end']
                label = f"[{ann['type']}: {annotated_text[start:end]}]"
                annotated_text = annotated_text[:start] + label + annotated_text[end:]

            text.human_readable = annotated_text

            if passage_type == "front":
                article.title = text.human_readable
            elif passage_type == "abstract":
                article.abstract += annotated_text
            else:
                annotated_paragraphs.append(text.human_readable)

    article.paragraphs = annotated_paragraphs

    if article.snippets:
        article.paragraphs += [s.human_readable for s in article.snippets]  # todo není anotované! protože nevím offset, nedokážu to v dokumentu najít...
        write_xml(document, f"nomatch_{article.pmcid}.xml")


def _parse_biodiversity_pmc_document(article: Article, article_data: dict) -> None:
    """
    Parses a SIBiLS JSON PMC article and updates the Article object
    with annotated title, abstract, and body paragraphs.
    We annotate only based on these sources: "uniprot_swissprot", "nextprot".   # TODO CHOOSE RELEVANT SOURCES
    """
    document = article_data.get("document", {})
    sentences = article_data.get("sentences", [])
    annotations = article_data.get("annotations", [])

    annotations = [
        ann for ann in annotations
        if ann.get("concept_source") in ("uniprot_swissprot", "nextprot")
    ]

    def apply_annotations(text: str, sentence_num: int) -> str:
        """
        There is magic happening inside because we must somehow resolve overlapping annotations.
        """
        if not text:
            return ""

        relevant = [
            ann for ann in annotations
            if ann.get("sentence_number") == sentence_num
            and ann.get("start_index") is not None
            and ann.get("end_index") is not None
            and ann.get("type")
        ]

        span_map: dict[tuple[int, int], set[str]] = {}
        for ann in relevant:
            span = (ann["start_index"], ann["end_index"])
            span_map.setdefault(span, set()).add(ann["type"])

        sorted_spans = sorted(
            span_map.items(),
            key=lambda x: (x[0][1] - x[0][0]),
            reverse=True,
        )

        occupied = [False] * len(text)
        final_spans: list[tuple[int, int, str]] = []

        for (start, end), types in sorted_spans:
            if start < 0 or end > len(text):
                continue
            if any(occupied[start:end]):
                continue

            for i in range(start, end):
                occupied[i] = True

            final_spans.append(
                (start, end, "/".join(sorted(types)))
            )

        final_spans.sort(key=lambda x: x[0], reverse=True)

        annotated = text
        for start, end, label in final_spans:
            entity = annotated[start:end]
            annotated = (
                    annotated[:start]
                    + f"[{label}: {entity}]"
                    + annotated[end:]
            )

        return annotated

    # -------- Title and Abstract --------
    title = document.get("title", "")
    if title:
        article.title = apply_annotations(title, 1)

    abstract_sentences = [s for s in sentences if s.get("field") == "abstract"]
    abstract_parts: list[str] = []
    for s in abstract_sentences:
        annotated = apply_annotations(
            s.get("sentence", ""),
            s.get("sentence_number"),
        )
        if annotated:
            abstract_parts.append(annotated)

    if abstract_parts:
        article.abstract = " ".join(abstract_parts)

    # -------- Body text (PARAGRAPH-AWARE) --------
    body_sentences = [
        s for s in sentences if s.get("field") == "text" or s.get("tag") == "table"
        # IMPORTANT: the snippet can be both in text and in table (todo - hotovo, todo je zde jen pro zvýraznění informace)
    ]

    paragraphs: dict[str, list[dict]] = {}

    for s in body_sentences:
        content_id = s.get("content_id")
        if not content_id:
            continue
        paragraphs.setdefault(content_id, []).append(s)

    relevant_paragraphs: list[str] = []
    all_contents = {}
    for section_key in ["body_sections", "back_sections", "float_sections"]:
        for section in document.get(section_key):
            for content in section.get("contents"):
                if content.get("id"):
                    all_contents[content.get("id")] = content.get("text")

    for para_sentences in paragraphs.values():
        p_id = para_sentences[0].get("content_id")
        p_paragraph = all_contents.get(p_id, "")

        if not p_paragraph:
            continue
        else:
            p_paragraph = TextBlock(p_paragraph)

        match, matched_snippets = check_text_for_snippets(p_paragraph, article.snippets)
        if not match:  # we skip paragraphs that do not contain any of the snippets
            continue
        [article.snippets.remove(s) for s in matched_snippets]

        para_sentences.sort(key=lambda x: x["sentence_number"])
        annotated_sentences: list[str] = []
        for i, s in enumerate(para_sentences):
            raw = s.get("sentence")
            if not raw:
                continue

            annotated = apply_annotations(raw, s["sentence_number"])
            annotated_sentences.append(annotated)

        relevant_paragraphs.append(" ".join(annotated_sentences))

    if relevant_paragraphs:
        article.paragraphs = relevant_paragraphs

    if article.snippets:
        article.paragraphs += [s.human_readable for s in article.snippets]
        write_json(article_data, f"nomatch_{article.pmcid}.json")


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
BIODIVERSITY_PMC_URL = "https://biodiversitypmc.sibils.org/api/fetch"


def get_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def map_pubtator_xml(root: etree._Element) -> dict[str, etree._Element]:
    """Parses XML content and maps IDs to their respective document elements."""
    article_map = {}
    for doc in root.xpath("document"):
        id_elem = doc.find("id")
        if id_elem is not None and id_elem.text:
            article_map[f"PMC{id_elem.text}"] = doc
    return article_map


def map_biodiversity_pmc_json(article_set: dict) -> dict[str, dict]:
    """
    Maps a SIBiLS JSON article set to a to_be_json keyed by PMCID.

    Args:
        article_set: The full JSON response containing the 'sibils_article_set' list.

    Returns:
        A to_be_json mapping PMCID strings to their respective article data dictionaries.
    """
    return {
        article.get("_id"): article
        for article in article_set.get("sibils_article_set", [])
        if article.get("_id")
    }


def fetch_pubtator(session: requests.Session, params: dict) -> dict[str, etree._Element]:
    try:
        response = session.get(PUBTATOR_URL, params=params, verify=False, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return {}

    root = etree.fromstring(response.content)
    return map_pubtator_xml(root)


def fetch_biodiversity_pmc(session: requests.Session, params: dict) -> dict[str, dict]:
    """
    Args:
        session: The active requests' session.
        params: Parameters to_be_json containing 'ids' (comma-separated PMCIDs) and 'col' (collection).
    Returns:
        A dictionary mapping PMCID strings to their article data dictionaries.
    """
    try:
        response = session.post(BIODIVERSITY_PMC_URL, data=params, timeout=15)
        response.raise_for_status()
        article_set = response.json()
        return map_biodiversity_pmc_json(article_set)
    except Exception as e:
        print(f"SIBiLS BiodiversityPMC fetch failed: {e}")
        return {}


def update_articles_fulltext(articles: list[Article]):
    """
    Orchestrates the data fetching pipeline.
    """
    if not articles:
        return

    session = get_session()
    pmcid_to_article = {a.pmcid: a for a in articles}
    pubtator_results: dict[str, etree._Element] = {}
    for i in range(0, len(articles), 100):
        batch = articles[i: i + 100]
        ids_query = ",".join([a.pmcid for a in batch if a.pmcid])
        results = fetch_pubtator(session, {"pmcids": ids_query})
        pubtator_results.update(results)

    for pmcid, doc in pubtator_results.items():
        if pmcid in pmcid_to_article:
            article = pmcid_to_article[pmcid]
            _parse_pubtator_document(article, doc)
            article.source = "pubtator"

    missing_ids = [pmcid for pmcid in pmcid_to_article if pmcid not in pubtator_results]
    if missing_ids:
        biodiversity_pmc_params = {
            "col": "pmc",
            "ids": ",".join(missing_ids),
        }
        biodiversity_pmc_data = fetch_biodiversity_pmc(session, biodiversity_pmc_params)
        for pmcid in missing_ids:
            if pmcid in biodiversity_pmc_data:
                article = pmcid_to_article[pmcid]
                _parse_biodiversity_pmc_document(article, biodiversity_pmc_data[pmcid])
                article.source = "pmc"


if __name__ == '__main__':
    # pmcid = "PMC8794197"      # in both
    # test_article = Article(pmcid=pmcid, snippets=["We selected 5 families with at least 2 cases of cutaneous melanoma among first-degree relatives, for a total of 10 individuals for WES."])

    pmcid = "PMC3725882"
    test_article = Article(pmcid=pmcid, snippets=[TextBlock("shkenazi AB47 Br (33) Br-male")])
    #
    # # biodiversitypmc
    # res = fetch_biodiversity_pmc(get_session(), params={
    #     "ids": pmcid,
    #     "col": "pmc",
    # })
    # if pmcid in res:
    #     _parse_biodiversity_pmc_document(test_article, res[pmcid])
    #     print("--- BiodiversityPMC ---")
    #     print(test_article.get_context())

    # pubtator
    # res = fetch_pubtator(get_session(), params={
    #     "pmcids": pmcid,
    # })
    # if pmcid in res:
    #     _parse_pubtator_document(test_article, res[pmcid])
    #     print("--- Pubtator ---")
    #     print(test_article.get_context())

    # with open("test.json", "w") as f:
    #     json.dump(fetch_biodiversity_pmc(get_session(), params={
    #         "ids": "PMC4925265",
    #         "col": "pmc",
    #     }), f, indent=4)
    #
    write_xml(fetch_pubtator(get_session(), params={
        "pmcids": "PMC8794197"})["PMC8794197"], "test.xml")
