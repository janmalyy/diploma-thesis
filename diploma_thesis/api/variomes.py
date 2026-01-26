import json
import re
import requests
from diploma_thesis.core.models import Variant, Article, TextBlock
from diploma_thesis.settings import logger, DATA_DIR


def _process_suppl_data(data: dict, pattern: re.Pattern) -> str:
    """
    Extracts snippets from supplementary data based on variant terms.
    """
    # TODO je potřeba nějak inteligentně hledat tu variantu v raw suppl data; když použiju expandované hledání přes všechny termy, tak mám strašně moc nálezů - k ničemu
    # TODO nevím, jak to zvýrazňují a hledají ve webovém rozhraní; vypadá to, že v jsonu z variomes je jen daná ta suppl. file a žádná anotace
    # TODO nápad: parsovat a hledat to různě vzhledem k příponě článku/suppl. file?
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
    For faster development, if the file is already downloaded, it is loaded from disk.
    """
    variant_string = variant.variant_string
    variomes_dir = DATA_DIR / "variomes"
    filename = re.sub(r'[<>:"/\\|?*]', "_", variant_string)
    cache_path = variomes_dir / f"{filename}.json"
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Corrupted Variomes cache file: {cache_path}") from e
    else:
        try:
            r = requests.get(url=f"https://variomes.sibils.org/api/rankLit?genvars={variant.variant_string}")
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Variomes API request failed for {variant_string}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON returned by Variomes for {variant_string}") from e

        tmp_path = cache_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        tmp_path.replace(cache_path)

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
            TextBlock(ev.get("text"))
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

    logger.info(f"Found {len([a for a in articles if a.snippets])} articles and {len([a for a in articles if not a.snippets])} suppl. files for variant {variant.variant_string}.")
    return articles
