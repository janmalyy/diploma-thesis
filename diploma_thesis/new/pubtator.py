import re
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from xml.etree import ElementTree as ET
from diploma_thesis.settings import logger
from diploma_thesis.new.models import Article


class PubTatorProvider:
    def __init__(self):
        self.base_url = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/pmc_export/biocxml"
        self.headers = {
            "Host": "www.ncbi.nlm.nih.gov",
            "User-Agent": "Mozilla/5.0"
        }
        self.session = self._setup_session()

    def _setup_session(self):
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        return session

    def fetch_annotations(self, articles: list[Article]):
        """
        Fetches annotations from PubTator for a list of articles and updates them.
        """
        if not articles:
            return

        # Prepare PMC IDs (remove PMC prefix for API call)
        pmc_ids = []
        for a in articles:
            if a.pmcid.startswith("PMC"):
                pmc_ids.append(a.pmcid[3:])
            else:
                pmc_ids.append(a.pmcid)

        pmc_ids_string = ",".join(pmc_ids)
        url = f"{self.base_url}?pmcids={pmc_ids_string}"

        try:
            # verify=False is not recommended but needed
            response = self.session.get(url, headers=self.headers, verify=False, timeout=15)
            response.raise_for_status()

            if "xml" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("Received non-XML response from PubTator API.")

            root = ET.fromstring(response.content.decode(encoding="utf-8"))

            doc_map = {}
            for document in root.findall("document"):
                pmc_id = "PMC" + document.find("id").text
                doc_map[pmc_id] = document

            for article in articles:
                if article.pmcid in doc_map:
                    document = doc_map[article.pmcid]
                    article.annotated_content = self._parse_pubtator_document(document, article.snippets)
                    self._extract_attributes(article, document)
                else:
                    # TODO: If not found in PubTator, find directly via PMC (mocked for now)
                    self._mock_pmc_fetch(article)

        except Exception as e:
            logger.error(f"Error fetching PubTator data: {e}")
            for article in articles:
                if not article.annotated_content:
                    article.annotated_content = article.get_context()

    def _parse_pubtator_document(self, document: ET.Element, snippets: list[str]) -> str:
        """
        Parses BioC-XML document and applies annotations to relevant passages.
        """
        output_passages = []
        snippets_to_match = list(snippets)

        for passage in document.findall(".//passage"):
            text_element = passage.find("text")
            if text_element is None or text_element.text is None:
                continue
            original_text = text_element.text

            match = False
            for snippet in snippets_to_match:
                # Use first 20 chars for matching as in original code
                # TODO hledat podle prvních 20 znaků je takový hodně hrubý zjednodušení
                snippets.remove(snippet)
                if re.search(re.escape(snippet[:20].strip()), original_text, flags=re.IGNORECASE):
                    snippets_to_match.remove(snippet)
                    match = True
                    break

            passage_type_elem = passage.find("./infon[@key='type']")
            passage_type = passage_type_elem.text if passage_type_elem is not None else ""

            if match or passage_type in ("front", "abstract"):
                passage_offset = int(passage.find("offset").text)
                annotations = []
                for ann in passage.findall("annotation"):
                    ann_type = ann.find("./infon[@key='type']").text
                    if ann_type == "Species":
                        continue

                    loc = ann.find("location")
                    local_offset = int(loc.get("offset")) - passage_offset
                    length = int(loc.get("length"))

                    annotations.append({
                        'start': local_offset,
                        'end': local_offset + length,
                        'type': ann_type,
                        'text': ann.find("text").text
                    })

                # Sort annotations reverse to avoid index shift
                annotations.sort(key=lambda x: x['start'], reverse=True)
                annotated_text = original_text
                for ann in annotations:
                    start, end = ann['start'], ann['end']
                    label = f"[{ann['type']}: {annotated_text[start:end]}]"
                    annotated_text = annotated_text[:start] + label + annotated_text[end:]

                if passage_type == "front":
                    annotated_text = "Title: " + annotated_text
                elif passage_type == "abstract":
                    annotated_text = "Abstract: " + annotated_text

                output_passages.append(annotated_text)

        return "\n".join(output_passages)

    def _extract_attributes(self, article: Article, document: ET.Element):
        """Extracts article attributes. Mock implementation."""
        # Study Type
        text = " ".join([t.text for t in document.findall(".//text") if t.text])
        if "clinical trial" in text.lower():
            article.study_type = "Clinical Trial"
        elif "case report" in text.lower():
            article.study_type = "Case Report"
        else:
            article.study_type = "Observational Study"

        # Quality
        article.quality = "High" if article.pmcid in ["PMC6594079", "PMC6471801"] else "Medium"

        # Disease
        for ann in document.findall(".//annotation"):
            if ann.find("./infon[@key='type']").text == "Disease":
                article.disease = ann.find("text").text
                break

    def _mock_pmc_fetch(self, article: Article):
        """Mocks fetching content directly from PMC."""
        article.title = f"PMC Article {article.pmcid} (Direct Fetch Mock)"
        article.abstract = "Abstract not available in PubTator. Fetched from PMC directly."
        article.study_type = "Unknown (PMC)"

    def annotate_raw_text(self, text: str) -> str:
        """
        Cleans raw text and submits it to PubTator for annotations. 
        Mock implementation as original was not working.
        """
        return f"[Annotated Raw Text Mock]\n{text}"
