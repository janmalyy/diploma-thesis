import json
import re
import requests
from lxml import etree

from diploma_thesis.core.models import Variant, Article, TextBlock, SupplData
from diploma_thesis.settings import logger, DATA_DIR
from diploma_thesis.utils.helpers import write_xml, uniq, normalize_variant


def fetch_synvar(variant: str, level: str, gene: str | None = None) -> etree._Element | None:
    """
    Description: https://sibils.org/api/synvar/
    We use map=true: Output syntactic variations even if the variant could not be mapped on genome.
    We use iso=true: Validate on and generate synonyms for isoforms.
    """
    if level not in ("protein", "transcript", "genome", "dbsnp", "cosmic"):
        raise ValueError(f"Invalid synvar level: {level}")

    if level not in ("dbsnp", "cosmic") and gene is None:
        raise ValueError(f"Gene is required for level {level}")

    try:
        r = requests.get(
            url=f"https://synvar.sibils.org/generate/literature/fromMutation?ref={gene}&variant={variant}&level={level}&map=true&iso=true")
        r.raise_for_status()
        root = etree.fromstring(r.content)
    except requests.RequestException as e:
        raise RuntimeError(f"SynVar API request failed for: {gene}, {variant}") from e
    except etree.XMLSyntaxError as e:
        raise RuntimeError(f"Invalid XML returned by SynVar for: {gene}, {variant}") from e

    if root.xpath("//error"):
        logger.warning(f"SynVar returned error for: {gene}, {variant}")
        return None

    write_xml(root, f"{gene}_{variant}_{level}.xml")
    return root


def parse_synvar(root: etree._Element) -> dict:
    """
    Parse description-variant XML into a canonical, LLM-friendly structure,
    storing both GRCh37 and GRCh38 and collapsing syntactic noise.
    """
    if root is None:
        logger.warning("Nothing to parse, root is None, returning empty dict.")
        return {}
    raw: list[str] = []
    for e in root.xpath(".//synonym[not(ancestor::gene-synonym-list)] | .//hgvs | .//syntactic-variation | .//rsid | .//caid"):
        if e.text:
            raw.append(e.text.strip())

    raw = uniq(raw)

    gene: list[str] = []
    for e in root.xpath(".//gene-synonym-list/synonym"):
        if e.text:
            gene.append(e.text.strip())

    genomic_hgvs = {}
    for v in raw:
        if v.startswith("NC_") and ":g." in v:
            if "17.11" in v:
                genomic_hgvs["GRCh38"] = v
            elif "17.10" in v:
                genomic_hgvs["GRCh37"] = v

    hgvs_c = next((v for v in raw if v.startswith("NM_") and ":c." in v), None)
    hgvs_p = next((v for v in raw if v.startswith("NP_") and ":p." in v), None)
    dbsnpid = next((v for v in raw if v.startswith("rs")), None)
    caid = next((v for v in raw if v.startswith("CA")), None)

    canonical_values = {
        hgvs_c,
        hgvs_p,
        dbsnpid,
        caid,
        *genomic_hgvs.values(),
    }

    alias_map: dict[str, str] = {}
    for v in raw:
        if v in canonical_values:
            continue
        norm = normalize_variant(v)
        if norm not in alias_map:       # todo add fuzz.partial_ratio
            alias_map[norm] = v

    return {
        "gene": gene,
        "genomic_hgvs": genomic_hgvs,
        "dbsnpid": dbsnpid,
        "caid": caid,
        "hgvs_c": hgvs_c,
        "hgvs_p": hgvs_p,
        "aliases": list(alias_map.values()),
    }


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
        articles.append(Article(data_source="medline", pmid=pm_id, relevance_score=pub.get("score")))

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
        if snippets:  # TODO we skip articles without evidences=fulltext_snippets for now
            article = next((a for a in articles if a.pmcid == pmc_id), None)
            if article is None:
                articles.append(Article(data_source="pmc", pmcid=pmc_id, relevance_score=pub.get("score"),
                                        fulltext_snippets=snippets))
            else:
                article.data_sources.add("pmc")
                article.fulltext_snippets = snippets

    # Process Supplemental data
    supp_list = publications.get("supp")
    for pub in supp_list:
        pmc_id = pub.get("pmcid")

        article = next((a for a in articles if a.pmcid == pmc_id), None)
        if article is None:
            article = Article(data_source="supp", pmcid=pmc_id, relevance_score=pub.get("score"))
            articles.append(article)

        article.data_sources.add("supp")
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
        f"Found {len(medline_list)} medline articles, {len([a for a in articles if a.fulltext_snippets])} articles with fulltext snippets and {len([a for a in articles if len(a.suppl_data_list) > 0])} articles with suppl. snippets for variant {variant.variant_string}.")
    return articles
