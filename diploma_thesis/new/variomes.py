import json
import re
import requests
from diploma_thesis.new.models import Variant, Article
from diploma_thesis.settings import logger


def clean_variant_tags(text: str) -> str:
    """Cleans span tags that contain angle brackets within their attributes.

    Args:
        text: Raw text string with potentially complex HTML attributes.

    Returns:
        The text with span tags removed but content preserved.
    """
    # [^">] matches anything not a quote or a closing bracket
    # "[^"]*" matches a full quoted string (allowing > inside)
    # The combination ensures we only stop at a > that is NOT inside quotes
    pattern = r'<span(?:[^">]|"[^"]*")*>(.*?)</span>'

    return re.sub(pattern, r"\1", text)

    # TODO Budu chtít nějak zachovat tu pozici, abych ji tam pak mohl zvýrazněnou vrátit do závěrečného kontextu
    #  If you need to extract those IDs later, you can use: re.findall(r'concept_id=\"(.*?)\"', text)


def _process_suppl_data(data: dict, pattern: re.Pattern) -> str:
    """
    Extracts snippets from supplementary data based on variant terms.
    """
    # TODO je potřeba nějak inteligentně hledat tu variantu v raw suppl data; když použiju expandované hledání přes všechny termy, tak mám strašně moc nálezů - k ničemu
    # TODO nevím, jak to zvýrazňují a hledají ve webovém rozhraní; vypadá to, že v jsonu z variomes je jen daná ta suppl. file a žádná anotace
    # TODO nápad: parsovat a hledat to různě vzhledem k příponě?
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
        # with open("variomes_data.json", "w") as f:
        #     f.write(json.dumps(data, indent=4))
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
        snippets = [
            clean_variant_tags(ev.get("text"))
            for ev in evidences
            if ev.get("text")
        ]
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

    logger.info(f"Found {len(articles)} articles for variant {variant.variant_string}.")
    return articles
