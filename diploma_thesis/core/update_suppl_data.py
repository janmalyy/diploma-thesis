import re

from diploma_thesis.core.build_paragraph import build_paragraph
from diploma_thesis.core.models import Article, Variant
from diploma_thesis.utils.helpers import compile_variant_pattern
from diploma_thesis.utils.text_matching import is_new_paragraph


def remove_articles_with_no_match(articles: list[Article]) -> list[Article]:
    """Remove articles that have no extracted paragraphs from supplementary data."""
    # logger.info(f"Filtering {len(articles)} articles for matches")
    to_remove = []
    for article in articles:
        if article.data_sources == {"supp"}:
            if all((len(sd.paragraphs) == 0) or sd.paragraphs == [""] for sd in article.suppl_data_list):
                to_remove.append(article)
    for a in to_remove:
        articles.remove(a)
    # logger.info(f"Removed {len(to_remove)} articles with no matches")
    return articles


def get_preview(raw_text: str, match: re.Match, window: int = 50) -> str:
    """Return a small text window around the match for a quick similarity check."""
    start = max(match.start() - window, 0)
    end = min(match.end() + window, len(raw_text))
    return raw_text[start:end].strip()


def update_suppl_data(articles: list[Article], variant: Variant) -> list[Article]:
    """Main entry point to update articles with supplementary data findings."""
    # logger.info(f"Updating supplementary data for variant {variant.terms[0] if variant.terms else 'unknown'}")
    articles_with_suppl = [a for a in articles if a.suppl_data_list]

    for article in articles_with_suppl:
        # logger.info(f"Processing article {article.pmcid or 'unknown'}")
        for sd in article.suppl_data_list:
            pattern = compile_variant_pattern(sd.snippets if sd.snippets else variant.terms)
            for m in re.finditer(pattern, sd.raw_text):
                if not m.group().strip():
                    continue

                preview = get_preview(sd.raw_text, m)
                if not is_new_paragraph(preview, sd.paragraphs, 80):
                    # logger.info("Skipping reconstruction — preview too similar to existing paragraph")
                    continue

                paragraph = build_paragraph(m, sd.raw_text)
                if is_new_paragraph(paragraph, sd.paragraphs, 90):
                    sd.paragraphs.append(paragraph)

    articles = remove_articles_with_no_match(articles)
    # logger.info("Supplementary data update complete")
    return articles
