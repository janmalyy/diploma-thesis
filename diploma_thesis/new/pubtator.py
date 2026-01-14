import re
import time
from typing import Generator

import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3 import Retry
from xml.etree import ElementTree as ET

from diploma_thesis.settings import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_pubtator_data_by_ids(pmc_ids: list[int]) -> dict:
    """
    Fetches data from PubTator for given PMC IDs.

    Args:
        pmc_ids (list[int]): The PMC IDs of articles to retrieve data for.
    """
    pmc_ids_string = ",".join(map(str, pmc_ids))
    # note we use direct IP as there are problems with DNS resolution
    url = f"https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/pmc_export/biocxml?pmcids={pmc_ids_string}"

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

        result = {}
        for document in root.findall("document"):
            pmc_id = "PMC" + document.find("id").text
            result[pmc_id] = document
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data for ids: {pmc_ids}", e)
        raise


def annotate_raw_text(text: str) -> str:
    """
    Cleans raw text, submits it to PubTator 3 for 'All' bioconcepts,
    and polls for the BioC-XML results.
    """
    raise NotImplementedError("Mají někde nějakou chybu v pubtatoru se mi zdá...")
    import unicodedata
    import re
    from unidecode import unidecode
    # 1. Text Preprocessing (Logic from your request.py)
    # Normalizing and cleaning text to ensure compatibility
    text = unicodedata.normalize('NFC', text)
    text = unidecode(text)
    # Remove non-standard characters based on your specific regex pattern
    pattern = r'[^0-9a-zA-Z\!\@\#\$\%\^\&\*\(\)\_\+\{\}\|\:\"\<\>\?\-\=\[\]\\;\'\,\.\/ \t\n\r]'
    cleaned_text = re.sub(pattern, ' ', text)

    # 2. Submit Request
    submit_url = "https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/request.cgi"
    # Using 'All' to get annotations for Genes, Diseases, Chemicals, etc.
    payload = {'text': cleaned_text, 'bioconcept': 'All'}

    response = requests.post(submit_url, data=payload)

    # Extract Session ID (Note: API usually returns ID as plain text)
    if response.status_code == 200:
        try:
            session_id = response.json().get('id')
        except:
            session_id = response.text.strip()
    else:
        raise Exception(f"Submission failed: {response.status_code} - {response.text}")
    # 3. Poll for Results (Logic from your retrieve.py with added polling)
    retrieve_url = "https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/retrieve.cgi"
    params = {"id": session_id}

    print(f"Request submitted. Session ID: {session_id}. Waiting for results...")
    time.sleep(30)

    while True:
        # PubTator returns 404 while processing and 200 when finished
        result_response = requests.get(retrieve_url, params=params)

        if result_response.status_code == 200:
            return result_response.text
        elif result_response.status_code == 404:
            # Wait 5 seconds before trying again to avoid rate limiting
            time.sleep(5)
        else:
            result_response.raise_for_status()


def parse_pubtator_data(document: ET.Element, snippets: list[str]) -> str:
    # TODO vylepšit definování chunků, např. sekat podle celých vět
    # název, abstrakt, pmcid, snippets, vše anotované v rámci toho
    output_passages = []

    for passage in document.findall(".//passage"):
        text_element = passage.find("text")
        if text_element is None or text_element.text is None:
            continue
        original_text = text_element.text

        match = False
        for snippet in snippets:
            if re.search(re.escape(snippet[:20].strip()), original_text, flags=re.IGNORECASE):     # TODO hledat podle prvních 20 znaků je takový hodně hrubý zjednodušení
                snippets.remove(snippet)
                match = True
                break

        passage_type = passage.find("./infon[@key='type']").text

        if match or passage_type in ("front", "abstract"):
            passage_offset = int(passage.find("offset").text)

            # Collect all annotations for this passage
            annotations = []
            for ann in passage.findall("annotation"):
                ann_type = ann.find("./infon[@key='type']").text
                if ann_type == "Species":
                    continue
                # BioC offsets are global. We subtract the passage offset to get local index
                loc = ann.find("location")
                local_offset = int(loc.get("offset")) - passage_offset
                length = int(loc.get("length"))

                annotations.append({
                    'start': local_offset,
                    'end': local_offset + length,
                    'type': ann_type,
                    'text': ann.find("text").text
                })

            # Sort annotations by start position in REVERSE order
            # This prevents index shifting as we insert tags
            annotations.sort(key=lambda x: x['start'], reverse=True)

            annotated_text = original_text
            for ann in annotations:
                start, end = ann['start'], ann['end']
                label = f"[{ann['type']}: {annotated_text[start:end]}]"
                # Splice the label into the text
                annotated_text = annotated_text[:start] + label + annotated_text[end:]
            output_passages.append(annotated_text)
    output_passages[0] = "Title: " + output_passages[0]
    output_passages[1] = "Abstract: " + output_passages[1]
    # output_passages[2] = "Snippets which mention the variant:\n" + output_passages[2]
    return "\n".join(output_passages)
