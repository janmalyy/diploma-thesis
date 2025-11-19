import os
import time
import datetime
import calendar
from pathlib import Path
from typing import Any
from dateutil.relativedelta import relativedelta

import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3 import Retry
from xml.etree import ElementTree as ET
from Bio import Entrez

from diploma_thesis.settings import DATA_DIR, logger
from diploma_thesis.utils.parse_xml import write_pretty_xml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_pubmed_ids_by_query(query: str, email: str,
                            maxdate: datetime.datetime, mindate: datetime.datetime) -> \
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

    Returns:
        list[int]: List of PubMed IDs relevant to the concept.
    """
    Entrez.email = email
    maximal_accepted_date = datetime.datetime.today() - relativedelta(months=2)
    to_be_used_mindate = mindate if mindate < maximal_accepted_date else maximal_accepted_date - relativedelta(months=1)
    to_be_used_maxdate = maxdate if maxdate < maximal_accepted_date else maximal_accepted_date

    try:
        with Entrez.esearch(db="pubmed",
                            term=query,
                            retmax=10000,
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


def make_batches(input_list: list[Any], batch_size: int = 100) -> list[list[Any]]:
    """Split a list into equally sized batches.

    Args:
        input_list (list[Any]): Items to split.
        batch_size (int): Size of each batch.

    Returns:
        list[list[Any]]: List of batches.
    """
    return [input_list[i:i + batch_size] for i in range(0, len(input_list), batch_size)]


def split_batch_to_separate_articles(root: ET.Element, directory: Path) -> None:
    for document in root.findall("document"):
        pubmed_id = document.find("id").text
        write_pretty_xml(document, directory / f"article_{pubmed_id}.xml")


if __name__ == '__main__':
    keywords = ['Breast Neoplasms[MeSH]', 'breast neoplas*', 'breast malignant neoplasm*',
                'breast cancer*', 'cancer of breast', 'cancer of the breast',
                'breast tumor*', 'breast malignanc*', 'breast malignant tumor*',
                'mammary cancer*', 'mammary carcinoma*', 'mammary neoplasm*',
                'lobular carcinoma*', 'lobular neoplas*',
                'ductal carcinoma*', 'ductal neoplas*'
                ]
    query = '("' + '" OR "'.join(keywords) + '")'.lstrip(" OR ")

    for year in range(2020, 2025):
        logger.info(f"Starting year: {year}.")
        logger.info(f"...searching for IDs matching: '{query}'.")
        year_dir = DATA_DIR / "2025_11_19" / str(year)
        if not os.path.exists(year_dir):
            os.mkdir(year_dir)

        pmids = []
        for month in range(1, 13):      # we split it to months because of limits of bulk downloads to 10k
            days = calendar.monthrange(year, month)[1]
            this_month_pmids = get_pubmed_ids_by_query(query, "526325@mail.muni.cz",
                                                       mindate=datetime.datetime(year, month, 1),
                                                       maxdate=datetime.datetime(year, month, days),
                                                       )
            if this_month_pmids:
                pmids.extend(this_month_pmids)

        logger.info(f"Fetched {len(pmids)} matching PubMed IDs for the query.")
        pmid_batches = make_batches(pmids, 100)
        logger.info("...starts downloading the articles by IDs.")
        for batch in pmid_batches:
            try:
                result = fetch_pubtator_data_by_ids(batch)
                time.sleep(0.34)
                split_batch_to_separate_articles(result, year_dir)

            except Exception as e:
                logger.error(f"Error fetching data: {e}.")
                continue
        logger.info(f"Finished downloading the articles.")
        logger.info(f"Ending year: {year}.")
    logger.info(f"All downloading completed.")
