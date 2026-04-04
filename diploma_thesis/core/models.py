from pydantic import BaseModel

from diploma_thesis.api.synvar import fetch_synvar, parse_synvar
from diploma_thesis.settings import logger
from diploma_thesis.utils.helpers import (to_human_readable,
                                          to_machine_comparable)


class Variant:
    """if you create a variant with dbSNP or CLINGEN identifier, write the ID
    to the variant field and leave the gene field empty.
    In such cases, it is recommended to fetch the data from SynVar ASAP after the Variant object creation
    to ensure the following processes will work properly."""
    def __init__(self, gene: str | None, variant: str, level: str, fetch_data: bool = False):
        self.level: str = level.strip().lower()
        if self.level in ["dbsnp", "clingen"]:
            self.gene = ""
        else:
            self.gene: str = gene.strip().upper() if gene else ""
        self.variant: str = variant.strip() or ""
        self.variant_string = f"{self.gene} {self.variant}".strip()

        self.terms: list[str] = []
        self.variant_dict = {}
        if fetch_data:
            self.fetch_synvar_data()

    def fetch_synvar_data(self):
        self.variant_dict = parse_synvar(fetch_synvar(self.gene, self.variant, self.level))
        if self.level in ["dbsnp", "clingen"]:
            if not self.gene and self.variant_dict.get("gene"):
                self.gene = self.variant_dict.get("gene")[0]
            if self.variant_dict.get("variant_string"):
                self.variant_string = self.variant_dict.get("variant_string")

    def __str__(self):
        return f"Variant {self.variant_string}"


class TextBlock:
    def __init__(self, raw_text: str, annotated: str | None = None):
        self.original: str = raw_text
        self.annotated: str | None = annotated
        self._human_readable: str = to_human_readable(self.original)
        self._machine_comparable: str = to_machine_comparable(self.human_readable)

    @property
    def human_readable(self) -> str:
        return self._human_readable

    @property
    def machine_comparable(self) -> str:
        return self._machine_comparable

    def __str__(self):
        return self.human_readable

    def __len__(self):
        return len(self.human_readable)


class SupplParagraph(BaseModel):
    title: str = ""
    header: str = ""
    context: list[str] = []


class SupplData(BaseModel):
    raw_text: str
    score: float
    snippets: list[str] = []
    paragraphs: list[SupplParagraph] = []


class Article:
    def __init__(self, data_source: str, relevance_score: float, pmid: str = "", pmcid: str = "", pub_year: int | None = None, fulltext_snippets: list[TextBlock] = None):
        self.pmid: str = pmid or ""  # for medline articles only
        self.pmcid: str = pmcid or ""
        self.relevance_score: float = round(relevance_score, 2)
        self.pub_year: int | None = pub_year
        self.data_sources: set[str] = set()   # possible combinations: (medline), (pmc), (suppl), (pmc, suppl)
        self.data_sources.add(data_source)

        self.title: TextBlock = TextBlock("")       # needs to be TextBlock because it is put on display on UI
        self.abstract: TextBlock = TextBlock("")    # it is TextBlock just in case it would be useful later (e.g. also for display)

        self.fulltext_snippets: list[TextBlock] = fulltext_snippets or []
        self.paragraphs: list[str] = []  # if variant found in the article

        self.suppl_data_list: list[SupplData] = []

        self.annotation_source: str = ""

    def get_context(self) -> str:
        """Returns a string representation of the article. For people."""
        context = f"Article {self.pmcid if self.pmcid else self.pmid}\n"
        context += f"Relevance score: {self.relevance_score}\n"
        if self.title:
            context += f"Title: {self.title.original}\n"
        if self.abstract:
            context += f"Abstract: {self.abstract.original}\n"
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
        """Returns a JSON representation of the article. For LLMs."""
        suppl_data_mentions = []
        for sd in self.suppl_data_list:
            for i, p in enumerate(sd.paragraphs):
                suppl_data_mentions.append({
                    f"suppl{i}": {
                        key: value
                        for key, value in p.model_dump().items()
                        if value not in [None, "", []]
                    }
                })
        return {
            "ARTICLE_ID": self.pmcid if self.pmcid else self.pmid,
            "TITLE": self.title.annotated,
            "ABSTRACT": self.abstract.annotated,
            "FULLTEXT_MENTIONS": self.paragraphs,
            "SUPPLEMENTARY_DATA_MENTIONS": suppl_data_mentions
        }

    def get_structured_metadata(self) -> dict:
        """Returns a JSON representation of the article metadata. For UI display."""
        return {
            "article_id": self.pmcid if self.pmcid else self.pmid,
            "title": self.title.original,
            "relevance_score": self.relevance_score,
            "pub_year": self.pub_year,
            "data_sources": list(self.data_sources)
        }


def prune_articles(articles: list[Article], max_articles: int = 50) -> list[Article]:
    """
    Prune the list of articles to the maximum number of articles based on relevance_score
    with the exception that all medline articles are kept.
    """
    if len(articles) < max_articles:
        return articles
    medline_articles = [a for a in articles if "medline" in a.data_sources]
    if len(medline_articles) > max_articles:
        return sorted(medline_articles, key=lambda a: a.relevance_score, reverse=True)[:max_articles]

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
            if article.data_sources == {"suppl"}:
                if all((len(sd.paragraphs) == 0) or sd.paragraphs == [""] for sd in article.suppl_data_list):
                    to_remove.append(article)

            if article.data_sources == {"pmc"}:
                if not article.paragraphs or article.paragraphs == [""]:
                    to_remove.append(article)

            if article.data_sources == {"pmc", "suppl"}:
                if ((all((len(sd.paragraphs) == 0) or sd.paragraphs == [""] for sd in article.suppl_data_list)) and
                        (not article.paragraphs or article.paragraphs == [""])):
                    to_remove.append(article)
    for a in to_remove:
        articles.remove(a)
    logger.info(f"Removed {len(to_remove)} articles with no matches")
    return articles
