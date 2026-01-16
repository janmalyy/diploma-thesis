import re
import requests
from diploma_thesis.new.models import Variant, Article


def _process_suppl_data(data: dict, pattern: re.Pattern) -> str:
    """
    Extracts snippets from supplementary data based on variant terms.
    """
    title = data.get("title", "No Title")
    fulltext = data.get("text", "")
    snippets = []
    for match in re.finditer(pattern, fulltext):
        start = max(0, match.start() - 100)
        end = min(len(fulltext), match.end() + 100)
        snippets.append(fulltext[start:end])

    return f"title: {title}\n beginning: {fulltext[:200]}\nsnippets: {('\n'.join(snippets))}"


def fetch_variomes_data(variant: Variant) -> list[Article]:
    """
    Fetches data from Variomes API for a given variant and returns a list of Article objects.
    """
    try:
        r = requests.get(url=f"https://variomes.sibils.org/api/rankLit?genvars={variant.variant_string}")
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Error fetching Variomes data: {e}")
        return []

    # Populate terms in variant for later use in snippet matching
    try:
        variant.terms = data.get("normalized_query", {}).get("variants", [{}])[0].get("terms", [])
    except (IndexError, KeyError):
        variant.terms = []

    articles = []
    publications = data.get("publications", {})

    # Process PMC articles
    pmc_list = publications.get("pmc", [])
    for pub in pmc_list:
        pmc_id = pub.get("pmcid")
        evidences = pub.get("evidences", [])
        # TODO vymazat z těch snippets ty span znaky
        # Clean snippets (remove span tags if any, though original code just TODO'd it)
        snippets = [ev.get("text") for ev in evidences if ev.get("text")]
        articles.append(Article(pmcid=pmc_id, snippets=snippets))

    # Process Supplemental data
    supp_list = publications.get("supp", [])
    if supp_list and variant.terms:
        pattern = re.compile(("|".join(variant.terms)))
        for supp in supp_list:
            pmc_id = supp.get("id")
            # Check if article already exists in the list
            article = next((a for a in articles if a.pmcid == pmc_id), None)
            if not article:
                article = Article(pmcid=pmc_id)
                articles.append(article)

            article.suppl_info = _process_suppl_data(supp, pattern)

    return articles
