import datetime
import os

from dateutil.relativedelta import relativedelta
import logging
import time
import warnings

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from xml.etree import ElementTree as ET
from Bio import Entrez

from diploma_thesis.settings import DATA_DIR
from diploma_thesis.utils.parse_xml import write_pretty_xml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
warnings.filterwarnings(
    "ignore",
    message="Unverified HTTPS request"
)


def get_pubmed_ids_by_query_with_pubtator_and_entrez(query: str, email: str,
                                                     maxdate: datetime.datetime, mindate: datetime.datetime,
                                                     limit: int = 20,) -> list[int]:
    """
    Uses PubTator3 to autocomplete a biomedical entity, and then fetches PubMed IDs using Entrez.

    Notes: Entrez.esearch favour more recent articles. However, these are not yet available for download
    (but they can be found at web interface) and when trying to access them, HTTP 400 Error is raised.
    In order to overcome this issue, if too recent dates are used, pre-set dates
    (mindate = actual_date - 3 months; maxdate = actual_date - 2 months) are used.

    Args:
        query (str): Free-text biomedical concept (e.g., "cancer", "BRCA1", etc.).
        email (str): Email required by Entrez.
        maxdate (datetime.datetime): The maximal publication date of the articles.
        mindate (datetime.datetime): The minimal publication date of the articles.
        limit (int): Max number of PubMed IDs to return.

    Returns:
        list[int]: List of PubMed IDs relevant to the concept.
    """
    # Step 1: Get top autocomplete suggestion from PubTator3
    ac_url = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/entity/autocomplete/"
    try:
        resp = requests.get(ac_url, params={"query": query, "limit": 1}, timeout=10)
        resp.raise_for_status()
        suggestions = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"PubTator3 autocomplete failed: {e}")

    if not suggestions:
        logger.info(f"No suggestions found for {query}.")
        return []

    label = suggestions[0].get("_id", "").replace("_", " ").strip()
    if not label:
        logger.info(f"No label found in {suggestions[0]}.")
        return []

    logger.info(f"Searching for '{label}' given the free text query: '{query}'.")

    # Step 2: Use label to search in PubMed via Entrez
    Entrez.email = email
    term = f"{label}[MeSH Terms]"  # e.g., "Breast Neoplasms[MeSH Terms]"
    maximal_accepted_date = datetime.datetime.today() - relativedelta(months=2)
    to_be_used_mindate = mindate if mindate < maximal_accepted_date else maximal_accepted_date - relativedelta(months=1)
    to_be_used_maxdate = maxdate if maxdate < maximal_accepted_date else maximal_accepted_date

    try:
        with Entrez.esearch(db="pubmed",
                            term=term,
                            retmax=limit,
                            mindate=to_be_used_mindate.strftime("%Y/%m/%d"),
                            maxdate=to_be_used_maxdate.strftime("%Y/%m/%d"),
                            ) as handle:
            record = Entrez.read(handle)
    except Exception as e:
        raise RuntimeError(f"Entrez search failed: {e}")

    return list(map(int, record.get("IdList", [])))


def fetch_pubtator_data_by_id(pubmed_id: int) -> ET.Element | None:
    """
    Fetches data from PubTator for given PubMed ID.

    Args:
        pubmed_id (str): The ID of article to retrieve data for.

    Returns:
        xml.etree.ElementTree.Element: Embedded xml structure.
    """
    # note we use direct IP as there are problems with DNS resolution
    url = f"https://130.14.29.110/research/pubtator3-api/publications/export/biocxml?pmids={pubmed_id}"

    # Fix SSL verification issue by setting 'Host' in headers
    headers = {
        "Host": "www.ncbi.nlm.nih.gov",  # Manually set the correct hostname
        "User-Agent": "Mozilla/5.0"  # Helps avoid bot blocking
    }

    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    try:
        # verify=False is not recommended, but with True it does not work :/
        search_response = session.get(url, headers=headers, verify=False, timeout=10)

        search_response.raise_for_status()  # check for HTTP errors

        if "xml" not in search_response.headers.get("Content-Type", "").lower():
            raise ValueError("Received non-XML response from PubTator API.")

        root = ET.fromstring(search_response.content.decode(encoding="utf-8"))

        return root

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        raise


if __name__ == '__main__':
    for year in range(2020, 2025):
        year_dir = DATA_DIR / str(year)
        if not os.path.exists(year_dir):
            os.mkdir(year_dir)
        pmids = get_pubmed_ids_by_query_with_pubtator_and_entrez("breast cancer", "526325@mail.muni.cz",
                                                                 mindate=datetime.datetime(year, 1, 1),
                                                                 maxdate=datetime.datetime(year, 12, 31),
                                                                 limit=10000)
        for pmid in pmids:
            try:
                result = fetch_pubtator_data_by_id(pmid)
                time.sleep(0.3)
                write_pretty_xml(result, year_dir / f"article_{pmid}.xml")
            except Exception as e:
                print(f"Error fetching data: {e}.")
                continue
