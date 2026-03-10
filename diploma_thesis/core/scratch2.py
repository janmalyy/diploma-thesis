from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import Article, SupplData, Variant
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import DATA_DIR, logger

if __name__ == '__main__':
    variant = Variant("BRCA1", "D12H", "protein", fetch_data=False)
    variant.terms = ["D12H"]
    a1 = Article("pmc", 0.8, pmcid="PMC123")
    a1_list = [a1]
    text = """
    header ________________________________________________________________________________________________________________________ _______________ _______________ _______________ ______________________________ _____________________________________________ _______________ _______________ _______________
     první D12H _______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________
     druhé D12H __________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________
    """
    supp1 = SupplData(text, 0.75)
    supp2 = SupplData("raw text without anything", 0.85)
    # supp1.paragraphs = [{
    #     "header": "head1",
    #     "title": "title1",
    #     "context": ["context1", "context2"],
    # },
    #     {"header": "head2",
    #      "title": "title2",
    #      "context": ["context3", "context4"]
    #      }
    # ]
    a1.suppl_data_list.append(supp1)
    update_suppl_data(a1_list, variant)
    print(a1.get_context())
    # print(a1.get_structured_context())

    # with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
    #     text = f.read()
    # variants = text.split("\n")
    #
    # for i, variant in enumerate(variants[10:15]):
    #
    #     variant = Variant(variant)
    #     logger.info(f"Processing variant: {variant}")
    #
    #     logger.info("Fetching data from SIBiLS Variomes...")
    #     data = fetch_variomes_data(variant)
    #
    #     articles = parse_variomes_data(data, variant)
    #
    #     articles = update_suppl_data(articles, variant)
    #
    #     for article in articles:
    #         if article.suppl_data_list:
    #             print("ARTICLE:", article.pmcid, flush=True)
    #             for sd in article.suppl_data_list:
    #                 # print("SCORE:", round(sd.score, 2))
    #                 print("FIRST 1000 chars:", flush=True)
    #                 print(sd.raw_text[:1000], flush=True)
    #                 print("----------------------------", flush=True)
    #                 print("Matches:", flush=True)
    #                 for p in sd.paragraphs:
    #                     print(p, flush=True)
    #             print(flush=True)
