import re

import requests


def fetch_variomes_data(variant: str) -> dict:
    r = requests.get(url=f"https://variomes.sibils.org/api/rankLit?genvars={variant}")
    data = r.json()
    return data


def process_suppl_data(data: dict, pattern) -> str:
    # TODO vylepšit zkracování suppl. data
    title = data.get("title")
    fulltext = data.get("text")
    snippets = []
    for match in re.finditer(pattern, fulltext):
        snippets.append(fulltext[match.start()-100:match.end()+100])

    return f"title: {title}\n beggining: {fulltext[:200]}\nsnippets: {('\n'.join(snippets))}"


def parse_variomes_data(data) -> dict:
    """
    Parses Variomes JSON output.

    Returns:
    {
        "pmc_ids": []
        "pmc": {"id": ["snippet", "snippet"]},
        "suppl": {"id": "text"},
    }
    """
    parsed_data = {
        "pmc_ids": [],
        "pmc": {},
        "suppl": {}
    }
    publications = data.get("publications")

    pmc_list = publications.get("pmc")
    for pub in pmc_list:
        pmc_id = pub.get("pmcid")
        parsed_data["pmc_ids"].append(pmc_id)

        evidences = pub.get("evidences")
        # TODO vymazat z těch snippets ty span znaky
        snippets = [ev.get("text") for ev in evidences if ev.get("text")]

        parsed_data["pmc"][pmc_id] = snippets

    terms = data.get("normalized_query").get("variants")[0].get("terms")
    pattern = re.compile(("|".join(terms)))
    supp_list = publications.get("supp")
    for supp in supp_list:
        pmc_id = supp.get("id")
        parsed_data["pmc_ids"].append(pmc_id)
        shortened_suppl = process_suppl_data(supp, pattern)

        parsed_data["suppl"][pmc_id] = shortened_suppl

    return parsed_data


