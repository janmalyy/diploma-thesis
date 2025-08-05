from lxml import etree
from pathlib import Path
import neo4j
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
    """
    Extract article information from an XML file and return it as a dictionary.

    Returns: data ready to be written to neo4j
    """
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


class Neo4jConnection:

    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = neo4j.GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query(self, query, parameters=None, db=None, print_results=False):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.__driver.session(database=db) if db is not None else self.__driver.session()
            response = list(session.run(query, parameters))
            if parameters and "id" in parameters:
                print(f"Document {parameters['id']} uploaded to Neo4j.")
            if print_results:
                for record in response:
                    print(dict(record))

        except Exception as e:
            print(f"Query {query[:50]}... failed:", e)
        finally:
            if session is not None:
                session.close()
        return response


if __name__ == "__main__":
    push_doc_query = """
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
        MERGE (g:Gene {id: gene_data.id})
        SET g.name = gene_data.name,
            g.ncbi_homologene = gene_data.ncbi_homologene
        MERGE (g)-[r:is_in]->(d)
        SET r.count = gene_data.count
    """

    article_data = extract_article(DATA_DIR / "test2" / "article_31888550.xml")
    conn = Neo4jConnection(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

    # conn.query('CREATE CONSTRAINT constraint_document IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE')
    # conn.query('CREATE CONSTRAINT constraint_author IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE')
    # conn.query('CREATE CONSTRAINT constraint_gene IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE')
    # conn.query("SHOW CONSTRAINTS", print_results=True)
    conn.query(push_doc_query, article_data)
