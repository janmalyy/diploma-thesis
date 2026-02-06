import re

import requests
from lxml import etree

from diploma_thesis.settings import logger, DATA_DIR
from diploma_thesis.utils.helpers import uniq, normalize_variant, write_xml


def fetch_synvar(gene: str | None, variant: str, level: str) -> etree._Element | None:
    """
    Description: https://sibils.org/api/synvar/
    We use map=true: Output syntactic variations even if the variant could not be mapped on genome.
    We use iso=true: Validate on and generate synonyms for isoforms.
    Gene can be None if the level is dbsnp or cosmic.
    """
    logger.info(f"Fetching data from SynVar for {gene}:{variant}, level {level}...")

    if level not in ("protein", "transcript", "genome", "dbsnp", "cosmic"):
        raise ValueError(f"Invalid synvar level: {level}")

    if level not in ("dbsnp", "cosmic") and gene is None:
        raise ValueError(f"Gene is required for level {level}")

    synvar_dir = DATA_DIR / "synvar_cache"
    filename = re.sub(r'[<>:"/\\|?*]', "_", gene + "_" + variant + "_" + level)
    cache_path = synvar_dir / f"{filename}.xml"
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return etree.parse(cache_path).getroot()
        except Exception as e:
            raise RuntimeError(f"Corrupted SynVar cache file: {cache_path}") from e

    else:
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

        write_xml(root, cache_path)
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


if __name__ == '__main__':
    fetch_synvar("BRCA1", "p.Cys61Gly", "protein")