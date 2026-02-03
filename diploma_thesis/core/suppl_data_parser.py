import re

from rapidfuzz import fuzz

from diploma_thesis.core.models import Article, Variant
from diploma_thesis.utils.helpers import to_human_readable


def compile_pattern(input_list: list[str]):
    input_list = sorted(input_list, key=len, reverse=True)
    escaped = [r"[^\d\*\+a-zA-Z-]" + re.escape(v) for v in input_list]
    return re.compile("|".join(escaped))


def update_suppl_data(articles: list[Article], variant: Variant):
    """Pro všechny články od jedné varianty zpracuje jeich suppl. data, s evidences nebo i bez."""
    articles_with_suppl_data = [a for a in articles if len(a.suppl_data_list) > 0]

    for article in articles_with_suppl_data:
        for sd in article.suppl_data_list:
            # if there are evidences from the variomes api, we use them, if not, we search for a match in the expanded list of variant terms
            if sd.snippets:
                pattern = compile_pattern(sd.snippets)
            else:
                pattern = compile_pattern(variant.terms)

            for m in re.finditer(pattern, sd.raw_text):
                if not m.group().strip():
                    continue
                paragraph = to_human_readable(
                    # +1 here cause we match also a char before but this char should not be a part of the highlighted variant
                    sd.raw_text[m.start()-100:m.start()+1] + "!!!" + sd.raw_text[m.start()+1:m.end()] + "!!!" + sd.raw_text[m.end():m.end()+100]
                )

                # skip paragraphs that are too similar to existing ones
                # (can happen if variant is mentioned in the text two times differently one after each other
                # e.g. "c.50C>G" and then "p.Ala17Gly" in the table
                is_new_paragraph = True
                for p in sd.paragraphs:
                    if p == paragraph or fuzz.partial_ratio(p, paragraph) > 90:
                        is_new_paragraph = False
                        break
                if is_new_paragraph:
                    sd.paragraphs.append(paragraph)

        # remove supp-only articles without match
        if article.data_sources == {"supp"}:
            at_least_one_paragraph = False
            for sd in article.suppl_data_list:
                if len(sd.paragraphs) > 0:
                    at_least_one_paragraph = True
                    break
            if not at_least_one_paragraph:
                articles.remove(article)
