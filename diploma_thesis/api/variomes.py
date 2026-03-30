import json
import re

import requests

from diploma_thesis.core.models import Article, SupplData, TextBlock, Variant
from diploma_thesis.settings import DATA_DIR, logger


def fetch_variomes_data(variant: Variant) -> dict:
    """
    Fetches data from Variomes API for a given variant.
    For faster development, if the file is already downloaded, it is loaded from disk.
    """
    variant_string = variant.variant_string.strip()
    variomes_dir = DATA_DIR / "variomes_cache"
    variomes_dir.mkdir(parents=True, exist_ok=True)
    filename = re.sub(r'[<>:"/\\|?*]', "_", variant_string).upper()
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
            raise RuntimeError(f"Variomes API request failed for: '{variant_string}'.") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON returned by Variomes for: '{variant_string}'.") from e

        tmp_path = cache_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        tmp_path.replace(cache_path)

    return data


def parse_variomes_data(data: dict, variant: Variant) -> list[Article]:
    """
    Apart from parsing, it sets the preferred terms for the variant and the gene and populates the terms list.
    Args:
        data: JSON object returned by Variomes API
        variant: Variant object for which the data is being parsed
    Returns:
        list of Articles with fulltext_snippets for fulltext annotations
                         and with raw supplemental data string
    """
    # Populate terms and normalize gene and variant to preferred terms
    try:
        norm_q = data.get("normalized_query")
        variant.terms = norm_q.get("variants")[0].get("terms")
        variant.gene = norm_q.get("genes")[0].get("preferred_term")
        variant.variant = norm_q.get("variants")[0].get("preferred_term")
    except (IndexError, KeyError):
        pass

    articles = []
    publications = data.get("publications")

    # Process Medline articles - the variant is always mentioned in the title or abstract, so we don't need to care about snippets
    medline_list = publications.get("medline")
    for pub in medline_list:
        pm_id = pub.get("id")
        articles.append(Article(data_source="medline", pmid=pm_id,
                                relevance_score=pub.get("score"), pub_year=pub.get("date")))

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
        # it can happen that there are no evidences, so None is in fulltext_snippets; we handle it later
        article = next((a for a in articles if a.pmcid == pmc_id), None)
        if article is None:
            articles.append(Article(data_source="pmc", pmcid=pmc_id, relevance_score=pub.get("score"),
                                    pub_year=pub.get("date"), fulltext_snippets=snippets))
        else:
            article.data_sources.add("pmc")
            article.fulltext_snippets = snippets

    # Process Supplemental data
    supp_list = publications.get("supp")
    for pub in supp_list:
        pmc_id = pub.get("pmcid")

        article = next((a for a in articles if a.pmcid == pmc_id), None)
        if article is None:
            article = Article(data_source="suppl", pmcid=pmc_id,
                              relevance_score=pub.get("score"), pub_year=pub.get("date"))
            articles.append(article)
        else:
            article.data_sources.add("suppl")

        evidences = pub.get("evidences")
        snippets = [
            ev.get("text")
            for ev in evidences
            if ev.get("text")
        ]

        article.suppl_data_list.append(
            SupplData(
                raw_text=pub.get("text"),
                score=pub.get("score"),
                snippets=snippets,
            ))

    logger.info(
        f"Found {len(medline_list)} medline articles, "
        f"{len([a for a in articles if a.fulltext_snippets])} articles with fulltext snippets, "
        f"{len([a for a in articles if a.data_sources == {'pmc'} and not a.fulltext_snippets])} PMC articles without fulltext snippets, "
        f"and {len([a for a in articles if len(a.suppl_data_list) > 0])} articles with suppl. snippets "
        f"for variant {variant.variant_string}.")
    return articles
