import datetime
import os
from pathlib import Path
from typing import Any

from dateutil.relativedelta import relativedelta
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from xml.etree import ElementTree as ET
from Bio import Entrez

from diploma_thesis.settings import DATA_DIR, logger
from diploma_thesis.utils.parse_xml import write_pretty_xml


def get_pubmed_ids_by_query(query: str, email: str,
                            maxdate: datetime.datetime, mindate: datetime.datetime, limit: int = float("inf"), ) -> \
        list[int]:
    """
    Fetches PubMed IDs matching the query using Entrez.

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
    logger.info(f"Searching for IDs matching: '{query}'.")

    Entrez.email = email
    maximal_accepted_date = datetime.datetime.today() - relativedelta(months=2)
    to_be_used_mindate = mindate if mindate < maximal_accepted_date else maximal_accepted_date - relativedelta(months=1)
    to_be_used_maxdate = maxdate if maxdate < maximal_accepted_date else maximal_accepted_date

    try:
        with Entrez.esearch(db="pubmed",
                            term=query,
                            retmax=limit,
                            mindate=to_be_used_mindate.strftime("%Y/%m/%d"),
                            maxdate=to_be_used_maxdate.strftime("%Y/%m/%d"),
                            ) as handle:
            record = Entrez.read(handle)
    except Exception as e:
        raise RuntimeError(f"Entrez search failed: {e}")

    return list(map(int, record.get("IdList", [])))


def fetch_pubtator_data_by_ids(pubmed_ids: list[int]) -> ET.Element | None:
    """
    Fetches data from PubTator for given PubMed ID.

    Args:
        pubmed_ids (list[int]): The IDs of articles to retrieve data for.

    Returns:
        xml.etree.ElementTree.Element: Embedded xml structure.
    """
    pubmed_ids_string = ",".join(map(str, pubmed_ids))
    # note we use direct IP as there are problems with DNS resolution
    url = f"https://130.14.29.110/research/pubtator3-api/publications/export/biocxml?pmids={pubmed_ids_string}"

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


def make_batches(input_list: list[Any], batch_size: int = 100) -> list[Any]:
    batches = []
    max_length = len(input_list)
    end = 0
    for i in range(max_length // batch_size):
        start = end
        end = (i + 1) * batch_size
        if end <= max_length:
            batches.append(input_list[start:end])
        else:
            batches.append(input_list[start:max_length])

    return batches


def split_batch_to_separate_articles(root: ET.Element, directory: Path) -> None:
    for document in root.findall("document"):
        pubmed_id = document.find("id").text
        write_pretty_xml(document, directory / f"article_{pubmed_id}.xml")


if __name__ == '__main__':
    # TIAB = will search within a citation's title, collection title, abstract, other abstract, and author keywords
    keywords = ['"Breast Neoplasms"[MeSH]', '"breast cancer*"[TIAB]', '"breast neoplasm*"[TIAB]',
                '"mammary carcinoma"[TIAB]', '"breast tumor*"[TIAB]']
    query = "(" + " OR ".join(keywords) + ")".lstrip(" OR ")

    for year in range(2020, 2025):
        year_dir = DATA_DIR / "2025_11_18" / str(year)
        if not os.path.exists(year_dir):
            os.mkdir(year_dir)
        pmids = get_pubmed_ids_by_query(query, "526325@mail.muni.cz",
                                        mindate=datetime.datetime(year, 1, 1),
                                        maxdate=datetime.datetime(year, 1, 20),
                                        limit=10)
        logger.info(f"Fetched {len(pmids)} matching PubMed IDs for the query.")
        pmid_batches = make_batches(pmids, 2)
        for batch in pmid_batches:
            try:
                result = fetch_pubtator_data_by_ids(batch)
                time.sleep(0.3)
                split_batch_to_separate_articles(result, year_dir)
                break
            except Exception as e:
                print(f"Error fetching data: {e}.")
                continue
        logger.info(f"Downloading finished.")
        break
