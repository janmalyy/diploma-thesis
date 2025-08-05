from lxml import etree
from pathlib import Path
from neo4j import GraphDatabase
from typing import Any

from diploma_thesis.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, DATA_DIR


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
    genes = set()

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

        for annotation in passage.findall("annotation"):
            infon_type = annotation.find("infon[@key='type']")
            if infon_type is not None and infon_type.text == "Gene":
                gene_text = annotation.findtext("text")
                if gene_text:
                    genes.add(gene_text.strip())

    return {
        "id": doc_id,
        "year": year,
        "journal": journal,
        "title": title,
        "abstract": abstract,
        "pmcid": pmcid,
        "authors": [a.strip() for a in authors_raw.split(",")] if authors_raw else [],
        "genes": list(genes)
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
        d.authors = $authors,
        d.genes = $genes

    WITH d
    UNWIND $authors AS author_name
        MERGE (a:Author {name: author_name})
        MERGE (a)-[:is_author_of]->(d)

    WITH d
    UNWIND $genes AS gene_name
        MERGE (g:Gene {name: gene_name})
        MERGE (g)-[:is_in]->(d)
    """
    tx.run(query, **data)


if __name__ == "__main__":
    article_data = extract_article(DATA_DIR / "test" / "test.xml")
    push_to_neo4j(article_data)
    print(f"Document {article_data['id']} uploaded to Neo4j.")
