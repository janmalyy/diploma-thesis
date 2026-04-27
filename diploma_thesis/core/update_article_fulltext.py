import urllib3
from lxml import etree

from diploma_thesis.api.annotations import (fetch_biodiversity_pmc,
                                            fetch_pubtator, get_session)
from diploma_thesis.core.document_parsers import (
    parse_biodiversity_pmc_document, parse_pubtator_document)
from diploma_thesis.core.models import Article, Variant

urllib3.disable_warnings()


def update_articles_fulltext(articles: list[Article], variant: Variant):
    """
    Orchestrates the data fetching pipeline.
    Gets articles from Variomes and fetches fulltexts (or only abstract for medline articles)
    from Pubtator or BiodiversityPMC, depending on availability,
    and applies annotations to the articles.
    """
    if not articles:
        raise ValueError("No articles were sent to be processed.")

    session = get_session()
    pmcid_to_article = {a.pmcid: a for a in articles if a.pmcid}

    # try to get data from pubtator for all pmcids
    pubtator_results: dict[str, etree._Element] = {}
    for i in range(0, len(articles), 100):
        batch = articles[i: i + 100]
        ids_list = [a.pmcid for a in batch if a.pmcid]
        if ids_list is not None:
            results = fetch_pubtator(session, ids_list, "pmc")
            pubtator_results.update(results)

    for pmcid, doc in pubtator_results.items():
        if pmcid in pmcid_to_article:
            article = pmcid_to_article[pmcid]
            parse_pubtator_document(article, doc, variant)
            article.annotation_source = "pubtator"

    # get data for fulltext articles not present in pubtator from biodiversity_pmc
    missing_ids = [pmcid for pmcid in pmcid_to_article if pmcid not in pubtator_results]
    if missing_ids:
        biodiversity_pmc_data = fetch_biodiversity_pmc(session, missing_ids)
        for pmcid in missing_ids:
            if pmcid in biodiversity_pmc_data:
                article = pmcid_to_article[pmcid]
                parse_biodiversity_pmc_document(article, biodiversity_pmc_data[pmcid], variant)
                article.annotation_source = "pmc"

    # get data for medline articles from pubtator
    pmid_to_article = {a.pmid: a for a in articles if a.pmid}
    if pmid_to_article:
        medline_results = fetch_pubtator(session, list(pmid_to_article.keys()), "pubmed")

        for pmid, doc in medline_results.items():
            if pmid in pmid_to_article:
                article = pmid_to_article[pmid]
                parse_pubtator_document(article, doc, variant)
                article.annotation_source = "pubtator"
