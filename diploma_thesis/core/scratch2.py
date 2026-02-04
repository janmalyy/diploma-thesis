from diploma_thesis.api.variomes import fetch_variomes_data, parse_variomes_data
from diploma_thesis.core.models import Variant
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import DATA_DIR, logger

if __name__ == '__main__':
    with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
        text = f.read()
    variants = text.split("\n")

    for i, variant in enumerate(variants[20:25]):

        variant = Variant(variant)
        logger.info(f"Processing variant: {variant}")

        logger.info("Fetching data from SIBiLS Variomes...")
        data = fetch_variomes_data(variant)

        articles = parse_variomes_data(data, variant)

        articles = update_suppl_data(articles, variant)

        for article in articles:
            if article.suppl_data_list:
                print("ARTICLE:", article.pmcid, flush=True)
                for sd in article.suppl_data_list:
                    # print("SCORE:", round(sd.score, 2))
                    print("FIRST 1000 chars:", flush=True)
                    print(sd.raw_text[:1000], flush=True)
                    print("----------------------------", flush=True)
                    print("Matches:", flush=True)
                    for p in sd.paragraphs:
                        print(p, flush=True)
                print(flush=True)
