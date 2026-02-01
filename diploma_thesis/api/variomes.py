import json
import re
import requests
from diploma_thesis.core.models import Variant, Article, TextBlock
from diploma_thesis.settings import logger, DATA_DIR


def fetch_variomes_data(variant: Variant) -> dict:
    """
    Fetches data from Variomes API for a given variant.
    For faster development, if the file is already downloaded, it is loaded from disk.
    """
    variant_string = variant.variant_string
    variomes_dir = DATA_DIR / "variomes_cache"
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

    return data


def parse_variomes_data(data: dict, variant: Variant) -> list[Article]:
    """
    Args:
        data: JSON object returned by Variomes API
        variant: Variant object for which the data is being parsed
    Returns:
        list of Articles with fulltext_snippets for fulltext annotations
                         and with raw supplemental data string
    """
    # Populate terms and gene in variant for later use in matching
    try:
        norm_q = data.get("normalized_query")
        variant.terms = norm_q.get("variants")[0].get("terms")
        if not variant.gene:
            variant.gene = norm_q.get("genes")[0].get("preferred_term")
    except (IndexError, KeyError):
        pass

    articles = []
    publications = data.get("publications")

    # Process Medline articles - the variant is always mentioned in the title or abstract, so we don't need to care about snippets
    medline_list = publications.get("medline")
    for pub in medline_list:
        pm_id = pub.get("id")
        articles.append(Article(data_source="medline", pmid=pm_id))

    # Process PMC articles
    pmc_list = publications.get("pmc")
    for pub in pmc_list:
        pmc_id = pub.get("pmcid")
        evidences = pub.get("evidences")
        snippets = [
            TextBlock(ev.get("text"))
            for ev in evidences
            if ev.get("text")
        ]
        if snippets:                # TODO we skip articles without evidences=fulltext_snippets for now
            article = next((a for a in articles if a.pmcid == pmc_id), None)
            if article is None:
                articles.append(Article(data_source="pmc", pmcid=pmc_id, fulltext_snippets=snippets))
            else:
                article.fulltext_snippets = snippets

    # Process Supplemental data
    supp_list = publications.get("supp")
    for pub in supp_list:
        pmc_id = pub.get("pmcid")
        evidences = pub.get("evidences")

        snippets = [
            TextBlock(ev.get("text"))
            for ev in evidences
            if ev.get("text")
        ]
        if snippets:  # TODO we skip suppl. files without evidences=suppl_snippets for now (that means skipping more than 90 % of them)
            article = next((a for a in articles if a.pmcid == pmc_id), None)

            if article is None:
                article = Article(data_source="supp", pmcid=pmc_id, suppl_snippets=snippets)
                articles.append(article)
            else:
                article.suppl_snippets = snippets
                article.raw_suppl_data = pub.get("text")

    logger.info(f"Found {len(medline_list)} medline articles, {len([a for a in articles if a.fulltext_snippets])} articles with fulltext snippets and {len([a for a in articles if a.suppl_snippets])} articles with suppl. snippets for variant {variant.variant_string}.")
    return articles
