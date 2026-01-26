import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3 import Retry

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
