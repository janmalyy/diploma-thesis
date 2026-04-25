from urllib.parse import quote

from diploma_thesis.api.annotations import get_session
from diploma_thesis.api.clinvar import convert_pubmed_ids
from diploma_thesis.settings import DATA_DIR, logger

LITVAR_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/litvar2-api/variant/"


def get_litvar_ids_for_query(query: str) -> list[int]:
    """Fetch PMIDs and PMCIDs from LitVar for the query.

    Args:
        query: The search term for the variant.

    Returns:
        A list of publication IDs. PMCID returned if available, PMID otherwise.
    """
    session = get_session()

    # 1. get litvarID
    response = session.get(f"{LITVAR_BASE_URL}autocomplete/?query={query}")
    response.raise_for_status()
    data = response.json()

    if not data:
        logger.warning(f"No LitVar ID found for query: {query}. Returning an empty list.")
        return []
    # print(data)
    litvar_id = data[0]["_id"]

    # 2. encode the ID and get publications IDs
    # litvar@rs146261631## contains characters that must be escaped
    encoded_id = quote(litvar_id, safe="")

    response = session.get(f"{LITVAR_BASE_URL}get/{encoded_id}/publications")
    response.raise_for_status()
    data = response.json()

    return convert_pubmed_ids(data["pmids"])


if __name__ == '__main__':
    with open(DATA_DIR / "15variants.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]

    for line in lines:
        query = line.split(" ")[0] + " " + line.split(" ")[1]
        print(query)
        print(get_litvar_ids_for_query(query))
        print()
