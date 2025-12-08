from typing import Optional

import requests
import time
from xml.etree import ElementTree as ET

from diploma_thesis.api.convert_ids import convert_ids
from diploma_thesis.utils.parse_xml import write_pretty_xml


def _clean_text(text: str | None) -> str:
    cleaned = " ".join(text.split())
    return cleaned.strip()


def _request_with_retry(url: str, params: dict, retries: int = 3) -> str | None:
    """
    Returns:
        str | None: Response text or None.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.text
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5)
            else:
                return None
    return None


def fetch_ncbi_data(ids: list[str], source: str) -> ET.Element | None:
    """
    Fetch XML from NCBI EFetch (PubMed or PMC).

    Args:
        ids (list[str]): IDs to fetch.
        source (str): "pubmed" or "pmc".

    Returns:
        ET.Element | None: XML root or None.
    """
    if not ids:
        return None
    if source not in ["pubmed", "pmc"]:
        raise ValueError(f"{source} is not supported, choose one of: pubmed, pmc.")
    ids_string = ",".join(ids)

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": source,
        "id": ids_string,
        "rettype": "full",
        "retmode": "xml"
    }

    xml_text = _request_with_retry(url, params)
    if xml_text is None:
        return None

    try:
        root = ET.fromstring(xml_text)
        return root
    except Exception:
        return None


def _extract_pubmed_abstract(article: ET.Element) -> str:
    parts = []
    for node in article.findall(".//AbstractText"):
        part = _clean_text(node.text)
        if part:
            parts.append(part)

    return "\n".join(parts).strip()


def _extract_pmc_sections(article: ET.Element) -> dict[str, str]:
    """
    Extract sections (Introduction, Methods, Results, Discussion, Conclusions)
    from a PMC <article> structure with improved coverage.

    Args:
        article (ET.Element): PMC <article> element.

    Returns:
        Dict[str, str]: Extracted sections with normalized titles (e.g., 'Methods').
    """

    # Keywords are ordered from most specific to general. The first match is used.
    # Key: keyword in title (lowercase) | Value: Normalized Section Name (Title Case)
    target_mapping = {
        "materials and methods": "Methods",
        "experimental procedures": "Methods",
        "methodology": "Methods",
        "data analysis": "Methods",
        "methods": "Methods",

        "background": "Introduction",
        "introduction": "Introduction",

        "results and discussion": "Results",
        "experimental results": "Results",
        "results": "Results",

        "discussion": "Discussion",
        "summary and discussion": "Discussion",
        "conclusions": "Conclusions",
        "summary": "Conclusions",
    }

    extracted_sections: dict[str, list[str]] = {}

    body = article.find("body")
    if body is None:
        return {}

    # Use './/sec' to find ALL sections, including nested subsections.
    for sec in body.findall(".//sec"):
        title = sec.findtext("title", default="").strip().lower()

        normalized_key: Optional[str] = None
        for key, normalized in target_mapping.items():
            if key in title:
                normalized_key = normalized
                break

        if not normalized_key:
            continue

        paragraphs: list[str] = []
        for p in sec.findall("p"):
            full_text = "".join(p.itertext()).strip()

            if full_text:
                cleaned = _clean_text(full_text)
                paragraphs.append(cleaned)

        if paragraphs:
            if normalized_key not in extracted_sections:
                extracted_sections[normalized_key] = []

            extracted_sections[normalized_key].append("\n".join(paragraphs))

    final_sections: dict[str, str] = {}
    for name, content_list in extracted_sections.items():
        if content_list:
            final_sections[name] = "\n".join(content_list)

    return final_sections


def build_context_for_llm(ids_dicts: list[dict]) -> str:
    """
    Build final LLM text context from PMC & PubMed XML.

    Args:
        ids_dicts (list[dict]): Entries with "pmid" and "pmcid".

    Returns:
        str: Cleaned multi-article textual context.
    """
    pmcids = []
    pmids = []

    for entry in ids_dicts:
        if entry["pmcid"]:
            pmcids.append(entry["pmcid"])
        else:
            pmids.append(entry["pmid"])

    pmcid_root = fetch_ncbi_data(pmcids, "pmc")
    pmid_root = fetch_ncbi_data(pmids, "pubmed")

    context_parts: list[str] = []

    # ---- PMC FULLTEXT ----
    if pmcid_root is not None:
        write_pretty_xml(pmcid_root, "testing.xml")
        for article in pmcid_root.findall("article"):
            pmcid = article.findtext(".//article-id[@pub-id-type='pmcid']", default="")

            sections = _extract_pmc_sections(article)
            if not sections:
                continue

            block = [f"{pmcid}"]
            for name, content in sections.items():
                cleaned = _clean_text(content)
                if cleaned:
                    block.append(f"{name}:\n{cleaned}\n")

            context_parts.append("\n".join(block).strip())

    # ---- PUBMED ABSTRACTS ----
    if pmid_root is not None:
        for article in pmid_root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID", default="")
            abstract = _extract_pubmed_abstract(article)

            if abstract:
                context_parts.append(f"PMID {pmid} (Abstract):\n{abstract}")

    return "\n\n---\n\n".join(context_parts)


if __name__ == '__main__':
    ids = [
        2574186846546, 24944790, 26801900, 29193749, 25110414, 22552919, 25746798,
        25027354, 19104657, 23988873, 26099996, 29065426, 29372689, 21362212,
        30356105, 23942539, 23328581, 27527855, 31076604, 29507678, 28972045,
        29152729, 26457012
    ]
    output = convert_ids(ids, "pmid")
    context = build_context_for_llm(output)
    print(context)
