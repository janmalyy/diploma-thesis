import json
from pathlib import Path

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from diploma_thesis.settings import DATA_DIR, logger
from diploma_thesis.utils.helpers import write_xml
from diploma_thesis.utils.json_structure import write_json

PUBTATOR_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications"
BIODIVERSITY_PMC_URL = "https://biodiversitypmc.sibils.org/api/fetch"


def get_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def map_pubtator_xml(
    root: etree._Element,
    cache_dir: Path,
    database: str,
) -> dict[str, etree._Element]:
    """Map PubTator XML documents by PMC or Pubmed ID and persist them to cache.

    Args:
        root: Root XML element returned by PubTator.
        cache_dir: Directory where individual article XML files are cached.
        database: "pubmed" or "pmc"

    Returns:
        Mapping from PMC or Pubmed ID to XML document element.
    """
    mapping: dict[str, etree._Element] = {}

    prefix = ""
    if database == "pmc":
        prefix = "PMC"

    for doc in root.xpath("document"):
        id_element = doc.find("id")
        if id_element is None or not id_element.text:
            continue

        article_id = f"{prefix}{id_element.text}"
        mapping[article_id] = doc

        cache_path = cache_dir / f"{article_id}.xml"
        doc_tree = etree.ElementTree(doc)
        write_xml(doc_tree.getroot(), cache_path)

    return mapping


def fetch_pubtator(
    session: requests.Session,
    ids_list: list[str],
    database: str,
) -> dict[str, etree._Element]:
    """Fetch PubTator XML documents with filesystem caching.

    Cached files are loaded first. Only missing PMC/PubMed IDs are requested
    from the PubTator API.

    Args:
        session: Requests session to use for HTTP calls.
        ids_list: List of PMC IDs (e.g. ["PMC12345"]) or Pubmed IDS (e.g.[32050665]).
        database: "pubmed" or "pmc"

    Returns:
        Mapping from PMC ID to XML document element.
    """
    if database not in ("pubmed", "pmc"):
        raise ValueError("Choose one of these: pubmed or pmc.")

    cache_dir = DATA_DIR / "pubtator_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, etree._Element] = {}

    for article_id in ids_list:
        cache_path = cache_dir / f"{article_id}.xml"
        if cache_path.exists():
            try:
                mapping[article_id] = etree.parse(cache_path).getroot()
            except Exception as e:
                raise RuntimeError(f"Corrupted PubTator cache file: {cache_path}") from e

    not_cached_ids = [article_id for article_id in ids_list if article_id not in mapping]
    if not not_cached_ids:
        return mapping

    if database == "pmc":
        url = "/pmc_export/biocxml"
        ids_type = "pmcids"
    else:
        url = "/export/biocxml"
        ids_type = "pmids"
    try:
        response = session.get(
            PUBTATOR_BASE_URL + url,
            params={ids_type: ",".join(not_cached_ids)},
            verify=False,
            timeout=15,
        )
        response.raise_for_status()

        root = etree.fromstring(response.content)
        mapping.update(map_pubtator_xml(root, cache_dir, database))

    except requests.RequestException as e:
        # TODO add negative caching of articles, about which I know that they are not in PubTator. This would prevent trying to fetch them all the time.
        # see: https://chatgpt.com/share/697cbd7c-1bd0-8009-9530-15ec028e38e9 or https://chatgpt.com/c/697c869e-9214-8330-a063-621e53f4b673
        logger.info(f"Request failed. But it can only mean that none of the ids requested is available in Pubtator. Error message: {e}")
    except Exception as e:
        raise RuntimeError("Failed to parse PubTator response") from e

    return mapping


def map_biodiversity_pmc_json(article_set: dict, cache_dir: Path) -> dict[str, dict]:
    """
    Maps a SIBiLS JSON article set to a dictionary keyed by PMCID,
    and writes each article to its own cache file.

    Args:
        article_set: JSON response containing 'sibils_article_set'.
        cache_dir: Directory to write individual article JSON files.

    Returns:
        Mapping from PMCID strings to article data dictionaries.
    """
    mapping: dict[str, dict] = {}

    for article in article_set.get("sibils_article_set", []):
        pmcid = article.get("_id")
        if not pmcid:
            continue

        mapping[pmcid] = article

        cache_path = cache_dir / f"{pmcid}.json"
        write_json(article, cache_path)

    return mapping


def fetch_biodiversity_pmc(
    session: requests.Session,
    ids_list: list[str],
) -> dict[str, dict]:
    """
    Fetch SIBiLS BiodiversityPMC articles with JSON file caching.

    Cached files are loaded first. Only missing PMC IDs are requested.

    Args:
        session: Requests session for HTTP requests.
        ids_list: List of PMC IDs to fetch.

    Returns:
        Mapping from PMCID to article data dictionary.
    """
    cache_dir = DATA_DIR / "biodiversity_pmc_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, dict] = {}

    # Load cached articles
    for pmcid in ids_list:
        cache_path = cache_dir / f"{pmcid}.json"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    mapping[pmcid] = json.load(f)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Corrupted BiodiversityPMC cache file: {cache_path}") from e

    not_cached_ids = [pmcid for pmcid in ids_list if pmcid not in mapping]
    if not not_cached_ids:
        return mapping

    params = {"col": "pmc", "ids": ",".join(not_cached_ids)}

    try:
        response = session.post(BIODIVERSITY_PMC_URL, data=params, timeout=25)
        response.raise_for_status()
        article_set = response.json()
        mapping.update(map_biodiversity_pmc_json(article_set, cache_dir))
    except requests.RequestException as e:
        raise RuntimeError("BiodiversityPMC request failed") from e
    except Exception as e:
        raise RuntimeError("Failed to parse BiodiversityPMC response") from e

    return mapping
