from lxml import etree

from diploma_thesis.core.models import Article, TextBlock, Variant
from diploma_thesis.utils.helpers import shorten_paragraph, to_human_readable
from diploma_thesis.utils.text_matching import (
    find_relevant_paragraphs_with_snippets,
    find_relevant_paragraphs_without_snippets)


def apply_annotations_pubtator(passage: etree._Element, meta: dict) -> str:
    annotations = []
    text = meta["text_block"]

    for ann in passage.xpath("annotation"):
        ann_text_elem = ann.find("text")
        ann_text = ann_text_elem.text if ann_text_elem is not None else ""
        ann_type_elem = ann.xpath("./infon[@key='type']")
        ann_type = ann_type_elem[0].text if ann_type_elem else ""
        # we don't want to annotate neoplasm-related terms because they are too common
        if any(word in ann_text.lower() for word in ["cancer", "tumor", "tumour", "neoplasm", "malignancy"]):
            continue
        if ann_type == "Species":
            continue

        loc = ann.find("location")
        if loc is None:
            continue

        local_offset = int(loc.get("offset")) - meta["offset"]
        length = int(loc.get("length"))

        annotations.append({
            "start": local_offset,
            "end": local_offset + length,
            "type": ann_type,
            "text": ann_text,
        })

    annotations.sort(key=lambda x: x["start"], reverse=True)
    # here ugly things happen... I take the original text from TextBlock,
    # annotate it and then return this annotated text as human_readable...
    annotated_text = text.original

    for ann in annotations:
        start, end = ann["start"], ann["end"]
        label = f"[{ann['type']}: {annotated_text[start:end]}]"
        annotated_text = annotated_text[:start] + label + annotated_text[end:]

    return to_human_readable(annotated_text)


def parse_pubtator_document(article: Article, document: etree._Element, variant: Variant) -> None:
    """
    Parses BioC-XML PubTator document using competitive snippet assignment.
    """
    blocks: list[tuple[TextBlock, etree._Element]] = []
    passage_meta: dict[etree._Element, dict] = {}

    for passage in document.xpath(".//passage"):
        text_elem = passage.find("text")
        if text_elem is None or not text_elem.text:
            continue

        text = TextBlock(text_elem.text)

        passage_type_elem = passage.xpath("./infon[@key='type']")
        passage_type = passage_type_elem[0].text if passage_type_elem else ""

        offset_elem = passage.find("offset")
        passage_offset = int(offset_elem.text) if offset_elem is not None else 0

        blocks.append((text, passage))
        passage_meta[passage] = {
            "type": passage_type,
            "offset": passage_offset,
            "text_block": text,
        }

    # -------- Competitive assignment --------
    relevant_payloads: list[object] = []
    used_snippets: list[TextBlock] = []
    if "pmc" in article.data_sources:
        if not article.fulltext_snippets:  # = there are no evidences from variomes -> we try to search by variant.terms
            relevant_payloads = find_relevant_paragraphs_without_snippets(
                variant.terms,
                blocks,
            )
        else:
            used_snippets, relevant_payloads = find_relevant_paragraphs_with_snippets(
                article.fulltext_snippets,
                blocks,
            )
        title_tag_name = "front"
    elif article.data_sources == {"medline"}:
        title_tag_name = "title"
    elif article.data_sources == {"suppl"}:
        title_tag_name = "front"
    else:
        raise ValueError(f"Unsupported data source: {article.data_sources}")

    annotated_paragraphs: list[str] = []
    abstract_raw = ""
    abstract_ann = ""
    for passage, meta in passage_meta.items():
        passage_type = meta["type"]

        if passage_type in (title_tag_name, "abstract") or passage in relevant_payloads:

            if "table" in passage_type:
                annotated_paragraphs.append(
                    shorten_paragraph(meta["text_block"].human_readable, variant.terms)
                )
                continue

            annotated_text = apply_annotations_pubtator(passage, meta)

            if passage_type in title_tag_name:
                article.title = meta["text_block"]
                article.title.annotated = annotated_text
            elif passage_type == "abstract":
                abstract_raw += meta["text_block"].original
                abstract_ann += annotated_text
            else:
                annotated_paragraphs.append(
                    shorten_paragraph(annotated_text, variant.terms)
                )

    article.abstract = TextBlock(raw_text=abstract_raw, annotated=abstract_ann)
    article.paragraphs = annotated_paragraphs

    for snippet in used_snippets:
        article.fulltext_snippets.remove(snippet)

    if article.fulltext_snippets:
        article.paragraphs += [
            s.human_readable for s in article.fulltext_snippets
        ]


def apply_annotations_biodiversity_pmc(text: str, sentence_num: int, annotations: list[dict]) -> str:
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


def parse_biodiversity_pmc_document(article: Article, article_data: dict, variant: Variant) -> None:
    """
    Parses SIBiLS JSON PMC article using competitive snippet assignment.
    """
    document = article_data.get("document", {})
    sentences = article_data.get("sentences", [])
    annotations = [
        ann for ann in article_data.get("annotations", [])
        if ann.get("concept_source") in ("uniprot_swissprot", "nextprot")
    ]

    # -------- Title --------
    article.title = TextBlock(raw_text=document.get("title"),
                              annotated=apply_annotations_biodiversity_pmc(
                                  document.get("title"), 1, annotations)
                              )

    # -------- Abstract --------
    abstract_parts: list[TextBlock] = []
    for s in sentences:
        sentence_text = s.get("sentence", "")
        if s.get("field") != "abstract":
            continue
        annotated = apply_annotations_biodiversity_pmc(
            sentence_text,
            s.get("sentence_number"),
            annotations,
        )
        if annotated:
            abstract_parts.append(TextBlock(raw_text=sentence_text, annotated=annotated))

    if abstract_parts:
        abstract_raw = " ".join([text_block.original for text_block in abstract_parts])
        abstract_annotated = " ".join([text_block.annotated for text_block in abstract_parts])
        article.abstract = TextBlock(raw_text=abstract_raw, annotated=abstract_annotated)

    if "pmc" not in article.data_sources:
        return

    # -------- Collect paragraph sentences --------
    body_sentences = [
        s for s in sentences
        if s.get("field") == "text" or s.get("tag") == "table"
    ]

    paragraphs: dict[str, list[dict]] = {}
    for s in body_sentences:
        cid = s.get("content_id")
        if cid:
            paragraphs.setdefault(cid, []).append(s)

    # -------- Full paragraph texts --------
    all_contents: dict[str, str] = {}
    for section_key in ("body_sections", "back_sections", "float_sections"):
        for section in document.get(section_key, []):
            for content in section.get("contents", []):
                if content.get("id"):
                    all_contents[content["id"]] = content.get("text", "")

    # -------- Build matchable blocks --------
    blocks: list[tuple[TextBlock, list[dict]]] = []

    for para_sentences in paragraphs.values():
        is_table = para_sentences[0].get("tag") == "table"

        if is_table:
            for s in para_sentences:
                if s.get("sentence"):
                    blocks.append((TextBlock(s["sentence"]), para_sentences))
        else:
            pid = para_sentences[0].get("content_id")
            text = all_contents.get(pid)
            if text:
                blocks.append((TextBlock(text), para_sentences))

    # -------- Competitive assignment --------
    used_snippets: list[TextBlock] = []
    if not article.fulltext_snippets:
        relevant_payloads = find_relevant_paragraphs_without_snippets(
            variant.terms,
            blocks,
        )
    else:
        used_snippets, relevant_payloads = find_relevant_paragraphs_with_snippets(
            article.fulltext_snippets,
            blocks
        )

    used_paragraphs: set[int] = set()
    relevant_paragraphs: list[str] = []

    for para_sentences in relevant_payloads:
        pid = id(para_sentences)
        if pid in used_paragraphs:
            continue
        used_paragraphs.add(pid)

        para_sentences.sort(key=lambda x: x.get("sentence_number", 0))
        annotated_sentences: list[str] = []

        for s in para_sentences:
            raw = s.get("sentence")
            if not raw:
                continue
            is_table = para_sentences[0].get("tag") == "table"
            # we don't want to annotate tables because they have too many entities and it only becomes messy
            if is_table:
                continue

            annotated = apply_annotations_biodiversity_pmc(
                raw,
                s.get("sentence_number"),
                annotations,
            )
            annotated_sentences.append(annotated)

        if annotated_sentences:
            relevant_paragraphs.append(
                shorten_paragraph(" ".join(annotated_sentences), variant.terms)
            )

    # -------- Finalize --------
    article.paragraphs = relevant_paragraphs

    for snippet in used_snippets:
        article.fulltext_snippets.remove(snippet)

    if article.fulltext_snippets:
        article.paragraphs += [
            s.human_readable for s in article.fulltext_snippets
        ]
