from lxml import etree

from diploma_thesis.core.models import Article, TextBlock
from diploma_thesis.settings import DATA_DIR
from diploma_thesis.utils.helpers import write_xml
from diploma_thesis.utils.json_structure import write_json
from diploma_thesis.utils.text_matching import check_text_for_snippets


def apply_annotations(text: str, sentence_num: int, annotations: list[dict]) -> str:
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


def parse_pubtator_document(article: Article, document: etree._Element) -> None:
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
        article.paragraphs += [s.human_readable for s in
                               article.snippets]  # todo není anotované! protože nevím offset, nedokážu to v dokumentu najít...
        # write_xml(document, DATA_DIR / f"nomatch_{article.pmcid}.xml")


def parse_biodiversity_pmc_document(article: Article, article_data: dict) -> None:
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

    # -------- Title and Abstract --------
    title = document.get("title", "")
    if title:
        article.title = apply_annotations(title, 1, annotations)

    abstract_sentences = [s for s in sentences if s.get("field") == "abstract"]
    abstract_parts: list[str] = []
    for s in abstract_sentences:
        annotated = apply_annotations(
            s.get("sentence", ""),
            s.get("sentence_number"),
            annotations
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
        if para_sentences[0].get(
                "tag") == "table":  # because table "sentences" do not have their respective full paragraph in contents, we compare each "sentence" alone and store as paragraph only this sentence
            # TODO když je match, tak pak jako paragraph dát nějak intelignetně tu tabulku, ne jen tu nalezenou "sentence", např najít caption a sloupce
            #   podobně když je nalezen paragraph, tak ho nedávat celý, ale třeba jen začátek, dvě věty okolo a konec
            for i, para_sent in enumerate(para_sentences):
                match, matched_snippets = check_text_for_snippets(TextBlock(para_sent.get("sentence")),
                                                                  article.snippets)
                if match:  # we found a matching table_part, and we continue to the annotation with these para_sentences
                    [article.snippets.remove(s) for s in matched_snippets]
                    continue
        else:
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

            annotated = apply_annotations(raw,
                                          s["sentence_number"],
                                          annotations
                                          )
            annotated_sentences.append(annotated)

        relevant_paragraphs.append(" ".join(annotated_sentences))

    if relevant_paragraphs:
        article.paragraphs = relevant_paragraphs

    if article.snippets:
        article.paragraphs += [s.human_readable for s in article.snippets]
        # write_json(article_data, DATA_DIR / f"nomatch_{article.pmcid}.json")


def extract_attributes(article: Article, document: etree._Element):
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
