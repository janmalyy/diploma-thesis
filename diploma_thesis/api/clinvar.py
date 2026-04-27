import csv
from typing import Any, Generator

import requests
from lxml import etree
from rapidfuzz import fuzz

from diploma_thesis.settings import DATA_DIR
from diploma_thesis.utils.helpers import get_unique_safe_filename, write_xml

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

    data = response.json()
    id_list = data.get("esearchresult", {}).get("idlist", [])

    return [int(i) for i in id_list]


def clinvar_efetch(variant: str, variation_ids: list[int]) -> etree._Element:
    """
    Retrieve ClinVar efetch for given Variation IDs.

    Args:
        variant: the query variant that returned the variation_ids; used only for logging purposes
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
    write_xml(root, DATA_DIR / "clinvar" / f"{get_unique_safe_filename(variant)}.xml")
    return root


def get_clinvar_urls(query: str, max_results: int = 10) -> list[str]:
    """
    Search ClinVar for a variant and return ClinVar Variation URLs.
    """
    try:
        variation_ids = clinvar_esearch_variant_ids(query, max_results)
        return [f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{vid}" for vid in variation_ids]
    except Exception:
        return []


def extract_pubmed_ids(root: etree._Element) -> list[str]:
    """
    Extracts all PubMed IDs from a ClinVar XML response using manual tree traversal.

    Returns:
        A list of unique PubMed IDs found in the document.
    """
    uniq_ids = set()

    assertion_list = root.find(".//ClinicalAssertionList")
    if assertion_list is not None:
        for assertion in assertion_list:
            classification = assertion.find("Classification")
            if classification is not None:
                for citation in classification.findall("Citation"):
                    id_element = citation.find("ID")
                    if id_element is not None and id_element.text:      # there are also citations without IDs but with URL instead
                        uniq_ids.add(str(id_element.text).strip())

    return sorted(list(uniq_ids))


def make_batches(iterable: list, size: int) -> Generator[list, Any, None]:
    """
    Split a list into smaller batches of fixed size.
    Example:
        >>> list(make_batches([1, 2, 3, 4, 5, 6, 7], size=3))
        [[1, 2, 3], [4, 5, 6], [7]]
    """
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def convert_pubmed_ids(ids_to_convert: list[str]) -> list:
    """
    Convert article identifiers using the PMC ID Converter API. Operates per batches of 200.

    Args:
        ids_to_convert: List of PubMedIDs (as string) to convert.
    Returns:
        list: A list of converted IDs. If PMC ID exists, it is returned, if not, PMID is returned.
    """
    service_root_url = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"

    params = {
        "idtype": "pmid",
        "versions": "no",
        "format": "csv"
    }
    decoded = []
    for batch in make_batches(ids_to_convert, 200):
        params["ids"] = ",".join(str(x) for x in batch)

        response = requests.get(service_root_url, params=params, timeout=30)
        response.raise_for_status()

        decoded.extend(response.text.splitlines())
    reader = csv.DictReader(decoded)

    final_ids = []
    for i, row in enumerate(reader):
        if row.get("PMCID"):
            final_ids.append(row["PMCID"])
        else:
            final_ids.append(row["PMID"])

    return final_ids


if __name__ == "__main__":
    query_str = "BRCA1 R7C"
    ids = clinvar_esearch_variant_ids(query_str)
    root = clinvar_efetch(query_str, ids)
    extracted = extract_pubmed_ids(root)
    print(extracted)
    converted = convert_pubmed_ids(extracted)
    print(converted)
    print(len(converted) is len(extracted))
