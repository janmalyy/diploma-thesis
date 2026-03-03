
import requests
from lxml import etree
from rapidfuzz import fuzz

from diploma_thesis.settings import DATA_DIR
from diploma_thesis.utils.helpers import extend_variant_name

ENTREZ_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CLINVAR_DB = "clinvar"
DEFAULT_TIMEOUT = 15


def clinvar_esearch_variant_ids(query: str, max_results: int = 100) -> list[int]:
    """
    Search ClinVar for a variant and return ClinVar Variation IDs.

    Args:
        query: Search string (HGVS, rsID, gene + variant).
        max_results: Maximum number of IDs to return.

    Returns:
        List of ClinVar Variation IDs.
    """
    params = {
        "db": CLINVAR_DB,
        "term": query,
        "retmode": "json",
        "retmax": max_results
    }

    response = requests.get(
        f"{ENTREZ_BASE_URL}/esearch.fcgi",
        params=params,
        timeout=DEFAULT_TIMEOUT
    )
    response.raise_for_status()

    payload = response.json()
    id_list = payload.get("esearchresult", {}).get("idlist", [])

    return [int(i) for i in id_list]


def clinvar_efetch(variation_ids: list[int]) -> etree._Element:
    """
    Retrieve ClinVar efetch for given Variation IDs.

    Args:
        variation_ids: List of ClinVar Variation IDs.

    Returns:
        Raw efetch XML payload.
    """
    if not variation_ids:
        raise ValueError("variation_ids must not be empty")
    params = {
        "db": CLINVAR_DB,
        "id": ",".join(str(i) for i in variation_ids),
        "rettype": "vcv",
        "is_variationid": True,
        "from_esearch": True
    }

    response = requests.get(
        f"{ENTREZ_BASE_URL}/efetch.fcgi",
        params=params,
        timeout=DEFAULT_TIMEOUT
    )
    response.raise_for_status()
    root = etree.fromstring(response.content)
    # write_xml(root, f"clinvar_efetch_{round(time.time(), 2)}.xml")
    return root


def parse_clinical_significance(query: str, efetch: etree._Element) -> dict:
    """
    Identifies the correct variant from efetch XML and returns clinical significance.
    Warnings: Works well only with formats similar to: EPHB3 c.1202G>C, EPHB3 p.Arg401Pro, NM_004443.4(EPHB3):c.1202G>C (p.Arg401Pro).
              Does not guarantee to work with rsID or COSMICid.
              Because of fuzzy matching.
    Args:
        query: The variant search string (e.g., HGVS or gene name) to match.
        efetch: The XML root element from a ClinVar efetch response.

    Returns:
        dict: A dictionary containing variation metadata and clinical significance.
    """
    archives = efetch.xpath("//VariationArchive")
    if not archives:
        return {}

    target_archive = archives[0]
    query_lower = query.lower()
    best_score = 0
    for archive in archives:
        name = archive.get("VariationName").lower()
        score = fuzz.partial_ratio(query_lower, name)
        if score > best_score:
            target_archive = archive
            best_score = score

    classification_node = target_archive.xpath("./ClassifiedRecord/Classifications/GermlineClassification")

    node = classification_node[0]
    significance = node.xpath("./Description/text()")
    review_status = node.xpath("./ReviewStatus/text()")
    explanation = node.xpath("./Explanation/text()")

    return {
        "variation_id": target_archive.get("VariationID"),
        "variation_name": target_archive.get("VariationName"),
        "clinical_significance": significance[0] if significance else "Unknown",
        "review_status": review_status[0] if review_status else "Unknown",
        "explanation": explanation[0] if explanation else "Unknown"
    }


if __name__ == "__main__":
    with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]
    for variant in lines[:10]:
        query_str = extend_variant_name(variant)
        ids = clinvar_esearch_variant_ids(query_str)
        print(f"{query_str}: {ids}")

        if ids:
            summary = clinvar_efetch(ids)
            clinical = parse_clinical_significance(query_str, summary)
            print(f"Clinical Significance: {clinical}")
