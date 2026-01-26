"""
for given PubmedIDs, find corresponding PMCIDs, if existed, and return links to the articles, either from PMC or Pubmed.
"""
import csv
import requests

from diploma_thesis.settings import logger
from diploma_thesis.utils.helpers import make_batches


def convert_ids(ids_to_convert: list[str], convert_from: str) -> list[dict]:
    """
    Convert article identifiers using the PMC ID Converter API. Operates per batches of 200.

    Args:
        ids_to_convert: List of IDs (as string) to convert.
        convert_from: One of "pmcid", "pmid", "mid", "doi".

    Returns:
        list[dict]: Each dict contains keys "pmid", "pmcid", and "doi".
    """
    if convert_from not in ("pmcid", "pmid", "mid", "doi"):
        raise ValueError(
            f"You can only convert from one of ('pmcid', 'pmid', 'mid', 'doi'), not: {convert_from}."
        )
    service_root_url = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
    logger.info(f"Going to convert {len(ids_to_convert)} ids starting with: {ids_to_convert[:3]}, ending with: {ids_to_convert[-3:]}...")

    params = {
        "idtype": convert_from,
        "versions": "no",
        "format": "csv"
    }
    decoded = []
    for batch in make_batches(ids_to_convert, 200):
        params["ids"] = ",".join(str(x) for x in batch)

        response = requests.get(service_root_url, params=params, timeout=30)
        response.raise_for_status()

        decoded.extend(response.text.splitlines())
    reader = csv.DictReader(decoded)

    results: list[dict] = []
    for i, row in enumerate(reader):
        results.append(
            {
                "pmid": row.get("PMID", None),
                "pmcid": row.get("PMCID", None),
                "doi": row.get("DOI", None)
            }
        )

    logger.info(f"Converted {len(results)} ids.")
    return results


def connect_pubmed_ids_with_links(ids_list: list[dict]) -> list[tuple[str, str]]:
    """
    For given pubmed ids, return a link to PMC article, if available, or to PubMed article.
    Removes all invalid ids.
    Args:
        ids_list: list of ids as a dictionary with ids for pubmed, pmc and doi.
    Returns: list of tuples of a pubmed id and a link to the corresponding article.

    """
    logger.info(f"Going to connect {len(ids_list)} ids with links...")

    results = []
    pubmed_root = "https://pubmed.ncbi.nlm.nih.gov/"
    pmc_root = "https://pmc.ncbi.nlm.nih.gov/articles/"
    for article in ids_list:
        pmcid = article["pmcid"]
        if pmcid != "" and pmcid is not None:
            results.append((article["pmid"], (pmc_root + pmcid)))
        else:
            url = pubmed_root + article["pmid"]
            #   Follows redirects (PubMed always redirects first so without it, we cannot distinguish existing from fictitious PubmedIDs)
            #   and avoids downloading the full response body by using a streamed request to make it faster
            response = requests.get(url, allow_redirects=True, stream=True, timeout=5)
            if response.status_code == 200:
                results.append((article["pmid"], url))
            else:
                logger.warning(f"No article was found for given id: {article['pmid']}.")

    logger.info(f"Successfully connected ids to links. There are {len(results)} valid links in total. The results start with: {results[:3]}...")

    return results


if __name__ == "__main__":
    ids = [
        2574186846546, 24944790, 26801900, 29193749, 25110414, 22552919, 25746798,
        25027354, 19104657, 23988873, 26099996, 29065426, 29372689, 21362212,
        30356105, 23942539, 23328581, 27527855, 31076604, 29507678, 28972045,
        29152729, 26457012
    ]

    output = convert_ids(ids, "pmid")
    for row in output:
        print(row)

    results = connect_pubmed_ids_with_links(output)
    for result in results:
        print(result)
