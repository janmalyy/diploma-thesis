from lxml import etree
from pathlib import Path
from neo4j import GraphDatabase
from typing import Any

from diploma_thesis.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, DATA_DIR


def count_gene_mentions(annotations: list[etree._Element]) -> dict[str, int]:
    """
    Count occurrences of each gene mention in the document.

    Args:
        annotations: List of annotation elements

    Returns:
        Dictionary mapping gene name to count
    """
    counts = {}
    for ann in annotations:
        infon_type = ann.find("infon[@key='type']")
        if infon_type is not None and infon_type.text == "Gene":
            gene_text = ann.findtext("text")
            if gene_text:
                name = gene_text.strip()
                counts[name] = counts.get(name, 0) + 1
    return counts


def extract_article(xml_file: Path) -> dict[str, Any]:
    tree = etree.parse(str(xml_file))
    root = tree.getroot()

    document = root.find("document")

    doc_id = document.findtext("id")
    passages = document.findall("passage")

    journal = None
    year = None
    pmcid = None
    title = None
    abstract = None
    authors_raw = None
    all_annotations = []

    genes: dict[str, dict] = {}

    for passage in passages:
        infons = {infon.attrib["key"]: infon.text for infon in passage.findall("infon")}
        if "journal" in infons:
            journal = infons.get("journal")
        if "year" in infons:
            year = infons.get("year")
        if "article-id_pmc" in infons:
            pmcid = infons.get("article-id_pmc")
        if "authors" in infons:
            authors_raw = infons.get("authors")

        passage_type = infons.get("type")
        if passage_type == "title":
            title = passage.findtext("text")
        elif passage_type == "abstract":
            abstract = passage.findtext("text")

        annotations = passage.findall("annotation")
        all_annotations.extend(annotations)

        for annotation in annotations:
            infon_type = annotation.find("infon[@key='type']")
            if infon_type is not None and infon_type.text == "Gene":
                gene_name = annotation.findtext("text").strip()
                gene_id = annotation.findtext("infon[@key='identifier']")
                homologene = annotation.findtext("infon[@key='NCBI Homologene']")

                if gene_name not in genes:
                    genes[gene_name] = {
                        "name": gene_name,
                        "id": gene_id,
                        "ncbi_homologene": homologene,
                        "count": 1
                    }
                else:
                    genes[gene_name]["count"] += 1

    return {
        "id": doc_id,
        "year": year,
        "journal": journal,
        "title": title,
        "abstract": abstract,
        "pmcid": pmcid,
        "authors": [a.strip() for a in authors_raw.split(",")] if authors_raw else [],
        "genes": list(genes.values())  # list of dicts with name, id, ncbi_homologene, count
    }


def push_to_neo4j(data: dict[str, Any]) -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    with driver.session() as session:
        session.execute_write(create_document_graph, data)
    driver.close()


def create_document_graph(tx, data: dict[str, Any]) -> None:
    query = """
    MERGE (d:Document {id: $id})
    SET d.year = $year,
        d.journal = $journal,
        d.title = $title,
        d.abstract = $abstract,
        d.article_id_pmc = $pmcid,
        d.authors = $authors

    WITH d
    UNWIND $authors AS author_name
        MERGE (a:Author {name: author_name})
        MERGE (a)-[:is_author_of]->(d)

    WITH d
    UNWIND $genes AS gene_data
        MERGE (g:Gene {name: gene_data.name})
        SET g.id = gene_data.id,
            g.ncbi_homologene = gene_data.ncbi_homologene
        MERGE (g)-[r:is_in]->(d)
        SET r.count = gene_data.count
    """
    tx.run(query, **data)


if __name__ == "__main__":
    article_data = extract_article(DATA_DIR / "test" / "test2.xml")
    push_to_neo4j(article_data)
    print(f"Document {article_data['id']} uploaded to Neo4j.")
