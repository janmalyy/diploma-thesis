import re

import requests
from lxml import etree

from diploma_thesis.api.annotations import get_session
from diploma_thesis.settings import DATA_DIR, logger
from diploma_thesis.utils.helpers import normalize_variant, uniq, write_xml

session = get_session()


def fetch_synvar(gene: str | None, variant: str, level: str) -> etree._Element | None:
    """
    Description: https://sibils.org/api/synvar/
    We use map=false: Output syntactic variations even if the variant could not be mapped on genome. (That is we don't check whether this variant exists on the genome.)
    We use iso=true: Validate on and generate synonyms for isoforms.
    more about map and iso here: https://gemini.google.com/share/75130b9596be
    Gene can be None if the level is dbsnp or clingen.
    Use caching for faster development.
    # todo improve caching cause now we search only for exactly same filename so there can be more files for the same variant with different naming
    """
    logger.info(f"Fetching data from SynVar for {gene} {variant}, level {level}...")

    if level not in ("protein", "transcript", "genome", "dbsnp", "clingen"):
        raise ValueError(f"Invalid synvar level: {level}")

    if level not in ("dbsnp", "clingen") and (gene is None or gene == ""):
        raise ValueError(f"Gene is required for level: {level}.")

    synvar_dir = DATA_DIR / "synvar_cache"
    synvar_dir.mkdir(parents=True, exist_ok=True)
    if gene:
        filename = re.sub(r'[<>:"/\\|?*]', "_", gene + "_" + variant + "_" + level).upper()
    else:
        filename = re.sub(r'[<>:"/\\|?*]', "_", variant + "_" + level).upper()
    cache_path = synvar_dir / f"{filename}.xml"
    if cache_path.exists():
        try:
            root = etree.parse(cache_path).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise RuntimeError(f"Corrupted SynVar cache file: {cache_path}") from e

        if root.xpath(".//variant[@valid='false']"):
            raise ValueError(f"SynVar could not find valid variant for: {gene}, {variant}")

        return root

    else:
        try:
            r = session.get(
                url=f"https://synvar.sibils.org/generate/literature/fromMutation?ref={gene}&variant={variant}&level={level}&map=false&iso=true",
                timeout=10)
            r.raise_for_status()
            root = etree.fromstring(r.content)
        except requests.RequestException as e:
            raise RuntimeError(f"SynVar API request failed for: {gene}, {variant}") from e
        except etree.XMLSyntaxError as e:
            raise RuntimeError(f"Invalid XML returned by SynVar for: {gene}, {variant}") from e

        if root.xpath("//error"):
            write_xml(root, cache_path, only_print=True)
            raise ValueError(f"SynVar returned error for: {gene}, {variant}, level: {level}.")

        if root.xpath("//variant[@valid='false']"):
            write_xml(root, cache_path, only_print=True)
            raise ValueError(f"SynVar returned this to be a false variant: {gene}, {variant}, level: {level}.")

        if not root.xpath("//variant"):
            write_xml(root, cache_path, only_print=True)
            raise ValueError(f"SynVar returned no data for variant: {gene}, {variant}, level: {level}.")

        write_xml(root, cache_path)     # todo improve caching to store a list of invalid variants - možná(?)

        return root


def parse_synvar(root: etree._Element) -> dict:
    """
    Parse description-variant XML into a canonical, LLM-friendly structure, collapsing syntactic noise.
    """
    if root is None:
        raise ValueError("Nothing to parse, root is None.")
    raw: list[str] = []
    for e in root.xpath(".//synonym[not(ancestor::gene-synonym-list)] | .//hgvs | .//syntactic-variation | .//rsid | .//caid"):
        if e.text:
            raw.append(e.text.strip())

    raw = uniq(raw)

    gene: list[str] = []
    for e in root.xpath(".//gene-synonym-list/synonym"):
        new_gene_name = e.text.strip()
        if e.text and new_gene_name not in gene:
            gene.append(new_gene_name)

    genomic_hgvs = []
    hgvs_c = []
    hgvs_p = []
    dbsnpid = []
    caid = []
    for v in raw:
        if v.startswith("NC_") and ":g." in v and v not in genomic_hgvs:
            genomic_hgvs.append(v)

        elif v.startswith("NM_") and ":c." in v and v not in hgvs_c:
            hgvs_c.append(v)
        elif v.startswith("NP_") and ":p." in v and v not in hgvs_p:
            hgvs_p.append(v)
        elif re.search(r"^rs\d*$", v, flags=re.IGNORECASE) and v not in dbsnpid:
            dbsnpid.append(v)
        elif re.search(r"^ca\d*$", v, flags=re.IGNORECASE) and v not in caid:
            caid.append(v)

    canonical_values = {
        *hgvs_c,
        *hgvs_p,
        *dbsnpid,
        *caid,
        *genomic_hgvs,
    }

    alias_map: dict[str, str] = {}
    for v in raw:
        if v in canonical_values:
            continue
        norm = normalize_variant(v)
        if norm not in alias_map:       # todo add fuzz.partial_ratio - teď je těch aliasů totiž pořád strašně moc stejných - možná to ale radši nechci, kdo ví, co by to udělalo
            alias_map[norm] = v

    variant_string = ""
    if len(gene) > 0 and len(hgvs_c) > 0:
        variant_string = gene[0] + " " + hgvs_c[0].split(":")[1]
    elif len(gene) > 0 and len(hgvs_p) > 0:
        variant_string = gene[0] + " " + hgvs_p[0].split(":")[1]
    elif len(gene) > 0:
        regexp_c_variant = None
        for v in alias_map.values():
            if re.search(r"^c\.\d.*$", v):
                regexp_c_variant = v
                break
        if regexp_c_variant:
            variant_string = gene[0] + " " + regexp_c_variant
    return {
        "gene": gene,
        "variant_string": variant_string,
        "genomic_hgvs": genomic_hgvs,
        "dbsnpid": dbsnpid,
        "caid": caid,
        "hgvs_c": hgvs_c,
        "hgvs_p": hgvs_p,
        "aliases": list(alias_map.values()),
    }


if __name__ == '__main__':
    # fetch = fetch_synvar("nola3", "   c.34 g  >c", "transcript")
    # fetch = fetch_synvar("EGFR", "E746_A750del", "protein")
    # fetch = fetch_synvar("", "rs146261631", "dbsnp")
    fetch = fetch_synvar(None, " CA789456", "clingen")
    # fetch = fetch_synvar("", "rs146261631", "dbsnp")
    # fetch = fetch_synvar(None, "CA391622325", "clingen")
    # fetch = fetch_synvar(None, "NC_000015.9:g.34635241C>G", level="")
    parsed = parse_synvar(fetch)
    print(parsed)
