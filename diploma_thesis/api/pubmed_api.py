import requests
from xml.etree import ElementTree as ET


def get_pubmed_ids_by_query(query: str, max_results=100) -> list[str]:
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    search_params = {
        "db": "pubmed",
        "term": f"{query}",
        "retmax": max_results,
        "retmode": "xml"
    }

    # Perform the search
    search_response = requests.get(search_url, params=search_params)
    search_tree = ET.fromstring(search_response.content)
    id_list = [id_elem.text for id_elem in search_tree.findall(".//Id")]

    return id_list


def fetch_pubmed_abstracts(id_list: list[str]) -> list[dict[str, str]]:
    """
    Fetches PubMed titles and abstracts based on pubmed IDs.

    Args:
        id_list: list of pubmed IDs

    Returns:
        list: A list of dictionaries containing 'title' and 'abstract' for each article.
    """
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    abstracts = []

    # Fetch details for each ID
    for pubmed_id in id_list:
        fetch_params = {
            "db": "pubmed",
            "id": pubmed_id,
            "retmode": "xml"
        }
        fetch_response = requests.get(fetch_url, params=fetch_params)
        fetch_tree = ET.fromstring(fetch_response.content)

        article = fetch_tree.find(".//Article")
        if article is not None:
            title_elem = article.find(".//ArticleTitle")
            abstract_elem = article.find(".//AbstractText")
            title = title_elem.text if title_elem is not None else "No title available"
            abstract = abstract_elem.text if abstract_elem is not None else "No abstract available"
            abstracts.append({"title": title, "abstract": abstract})

    return abstracts


if __name__ == '__main__':
    breast_cancer_ids = get_pubmed_ids_by_query("Angiosarcoma AND 2025[dp]")
    breast_cancer_data = fetch_pubmed_abstracts(breast_cancer_ids)
    print(f"Retrieved {len(breast_cancer_ids)} abstracts.")
    print(breast_cancer_data[:2])
