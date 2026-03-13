from pydantic import BaseModel

from diploma_thesis.api.synvar import fetch_synvar, parse_synvar
from diploma_thesis.settings import logger
from diploma_thesis.utils.helpers import (to_human_readable,
                                          to_machine_comparable)


class Variant:
    def __init__(self, gene: str, variant: str, level: str, fetch_data: bool = True):
        self.gene: str = gene.upper() if gene else ""
        self.variant: str = variant.upper() if variant else ""
        self.variant_string = f"{self.gene} {self.variant}"

        self.terms: list[str] = []
        self.variant_dict = {}
        if fetch_data:
            self.fetch_synvar_data(level)

    def fetch_synvar_data(self, level: str):
        self.variant_dict = parse_synvar(fetch_synvar(self.gene, self.variant, level))

    def __str__(self):
        return f"Variant {self.variant_string}"


class TextBlock:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.human_readable, self.machine_comparable = self.build_text_block()

    def build_text_block(self):
        human_readable = to_human_readable(self.raw_text)
        machine_comparable = to_machine_comparable(human_readable)
        return human_readable, machine_comparable

    def __str__(self):
        return self.human_readable

    def __len__(self):
        return len(self.human_readable)


class SuppParagraph(BaseModel):
    title: str = ""
    header: str = ""
    context: list[str] = []


class SupplData(BaseModel):
    raw_text: str
    score: float
    snippets: list[str] = []
    paragraphs: list[SuppParagraph] = []


class Article:
    def __init__(self, data_source: str, relevance_score: float, pmid: str = "", pmcid: str = "", fulltext_snippets: list[TextBlock] = None):
        self.pmid: str = pmid or ""  # for medline articles only
        self.pmcid: str = pmcid or ""
        self.relevance_score: float = round(relevance_score, 2)
        self.data_sources: set[str] = set()   # possible combinations: (medline), (pmc), (supp), (medline, pmc, supp), (pmc, supp)
        self.data_sources.add(data_source)

        self.title: str = ""
        self.abstract: str = ""

        self.fulltext_snippets: list[TextBlock] = fulltext_snippets or []
        self.paragraphs: list[str] = []  # if variant found in the article

        self.suppl_data_list: list[SupplData] = []

        self.annotation_source: str = ""
        self.study_type: str = "Unknown"
        self.disease: str = "Unknown"

    def get_context(self) -> str:
        """Returns a string representation of the article. For people."""
        context = f"Article {self.pmcid if self.pmcid else self.pmid}\n"
        context += f"Relevance score: {self.relevance_score}\n"
        if self.title:
            context += f"Title: {self.title}\n"
        if self.abstract:
            context += f"Abstract: {self.abstract}\n"
        if self.paragraphs:
            context += "Relevant paragraphs:\n" + "\n".join(self.paragraphs)
        if len(self.suppl_data_list) > 0:
            context += "\nSupplementary evidence records:\n"
            for sd in self.suppl_data_list:
                context += "\n".join([
                    f"{key}: {value}" for p in sd.paragraphs
                    for key, value in p.model_dump().items()
                    if value not in [None, "", []]
                ])
                context += "\n"
        return context

    def get_structured_context(self) -> dict:
        """Returns a json representation of the article. For LLMs."""
        supp_data_mentions = []
        for sd in self.suppl_data_list:
            for i, p in enumerate(sd.paragraphs):
                supp_data_mentions.append({
                    f"supp{i}": {
                        key: value
                        for key, value in p.model_dump().items()
                        if value not in [None, "", []]
                    }
                })
        return {
            "ARTICLE_ID": self.pmcid if self.pmcid else self.pmid,
            "TITLE": self.title,
            "ABSTRACT": self.abstract,
            "FULLTEXT_MENTIONS": self.paragraphs,
            "SUPPLEMENTARY_DATA_MENTIONS": supp_data_mentions
        }

    def shorten_context(self, max_length: int = 2000):
        """Intelligently shortens the context. Mock implementation."""  # TODO
        shortened = []
        for p in self.paragraphs:
            if len(p) > max_length:
                shortened.append(p[:max_length] + "...")
            else:
                shortened.append(p)
        self.paragraphs = shortened


def prune_articles(articles: list[Article], max_articles: int = 50) -> list[Article]:
    """
    Prune the list of articles to the maximum number of articles based on relevance_score
    with the exception that all medline articles are kept.
    """
    if len(articles) < max_articles:
        return articles
    medline_articles = [a for a in articles if "medline" in a.data_sources]
    sorted_articles = sorted(articles, key=lambda a: a.relevance_score, reverse=True)
    relevant_articles = sorted_articles[:max_articles-len(medline_articles)]
    relevant_articles.extend(medline_articles)
    return relevant_articles


def remove_articles_with_no_match(articles: list[Article]) -> list[Article]:
    """
    Remove articles that have no match and that are not presumably relevant then.
    Remove only if the relevance score is lower than 0.5. Never remove medline articles.
    """
    # logger.info(f"Filtering {len(articles)} articles for matches")
    to_remove = []
    for article in articles:
        if "medline" not in article.data_sources and article.relevance_score < 0.5:
            if article.data_sources == {"supp"}:
                if all((len(sd.paragraphs) == 0) or sd.paragraphs == [""] for sd in article.suppl_data_list):
                    to_remove.append(article)

            if article.data_sources == {"pmc"}:
                if not article.paragraphs or article.paragraphs == [""]:
                    to_remove.append(article)

            if article.data_sources == {"pmc", "supp"}:
                if ((all((len(sd.paragraphs) == 0) or sd.paragraphs == [""] for sd in article.suppl_data_list)) and
                        (not article.paragraphs or article.paragraphs == [""])):
                    to_remove.append(article)
    for a in to_remove:
        articles.remove(a)
    logger.info(f"Removed {len(to_remove)} articles with no matches")
    return articles
