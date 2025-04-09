import requests
from xml.etree import ElementTree as ET


def fetch_pubmed_abstracts(query, year, max_results=100):
    """
    Fetches PubMed abstracts based on the specified query and publication year.

    Args:
        query (str): The search query.
        year (int): The publication year.
        max_results (int): Maximum number of results to fetch.

    Returns:
        list: A list of dictionaries containing 'title' and 'abstract' for each article.
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = f"{base_url}esearch.fcgi"
    fetch_url = f"{base_url}efetch.fcgi"

    # Define search parameters
    search_params = {
        "db": "pubmed",
        "term": f"{query} AND {year}[dp]",
        "retmax": max_results,
        "retmode": "xml"
    }

    # Perform the search
    search_response = requests.get(search_url, params=search_params)
    search_tree = ET.fromstring(search_response.content)
    id_list = [id_elem.text for id_elem in search_tree.findall(".//Id")]

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
    breast_cancer_abstracts_2024 = fetch_pubmed_abstracts("Angiosarcoma", 2025)
    print(f"Retrieved {len(breast_cancer_abstracts_2024)} abstracts.")
    print(breast_cancer_abstracts_2024[:2])
