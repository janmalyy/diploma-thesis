import urllib3
from lxml import etree

from diploma_thesis.settings import logger, DATA_DIR
from diploma_thesis.utils.json_structure import write_json
from diploma_thesis.core.models import Article, TextBlock
from diploma_thesis.utils.helpers import write_xml

from diploma_thesis.api.annotations import get_session, fetch_pubtator, fetch_biodiversity_pmc
from diploma_thesis.core.document_parsers import parse_pubtator_document, parse_biodiversity_pmc_document

urllib3.disable_warnings()


def update_articles_fulltext(articles: list[Article]):
    """
    Orchestrates the data fetching pipeline.
    Gets articles from Variomes and fetches fulltexts (or only abstract ofr medline articles)
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
            parse_pubtator_document(article, doc)
            article.source = "pubtator"

    # get data for fulltext articles not present in pubtator from biodiversity_pmc
    missing_ids = [pmcid for pmcid in pmcid_to_article if pmcid not in pubtator_results]
    if missing_ids:
        biodiversity_pmc_data = fetch_biodiversity_pmc(session, missing_ids)
        for pmcid in missing_ids:
            if pmcid in biodiversity_pmc_data:
                article = pmcid_to_article[pmcid]
                parse_biodiversity_pmc_document(article, biodiversity_pmc_data[pmcid])
                article.source = "pmc"

    # get data for medline articles from pubtator
    pmid_to_article = {a.pmid: a for a in articles if a.pmid}
    if pmid_to_article:
        medline_results = fetch_pubtator(session, list(pmid_to_article.keys()), "pubmed")

        for pmid, doc in medline_results.items():
            if pmid in pmid_to_article:
                article = pmid_to_article[pmid]
                parse_pubtator_document(article, doc)
                article.source = "pubtator"


if __name__ == '__main__':
    # pmcid = "PMC8794197"      # in both
    # test_article = Article(pmcid=pmcid, fulltext_snippets=["We selected 5 families with at least 2 cases of cutaneous melanoma among first-degree relatives, for a total of 10 individuals for WES."])

    pmcid = "PMC3725882"
    test_article = Article(pmcid=pmcid, snippets=[TextBlock("shkenazi AB47 Br (33) Br-male")])
    #
    # # biodiversitypmc
    # res = fetch_biodiversity_pmc(get_session(), params={
    #     "ids": pmcid,
    #     "col": "pmc",
    # })
    # if pmcid in res:
    #     _parse_biodiversity_pmc_document(test_article, res[pmcid])
    #     print("--- BiodiversityPMC ---")
    #     print(test_article.get_context())

    # pubtator
    # res = fetch_pubtator(get_session(), params={
    #     "pmcids": pmcid,
    # })
    # if pmcid in res:
    #     _parse_pubtator_document(test_article, res[pmcid])
    #     print("--- Pubtator ---")
    #     print(test_article.get_context())

    # with open("test.json", "w") as f:
    #     json.dump(fetch_biodiversity_pmc(get_session(), params={
    #         "ids": "PMC4925265",
    #         "col": "pmc",
    #     }), f, indent=4)
    #
    write_xml(fetch_pubtator(get_session(), ["PMC8794197", "PMC8794197"], "pmc"), "test.xml")
