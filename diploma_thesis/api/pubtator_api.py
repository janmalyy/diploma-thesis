import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from xml.etree import ElementTree as ET


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
