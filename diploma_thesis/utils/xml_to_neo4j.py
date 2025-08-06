"""
Prerequisites: downloaded articles as xmls; titles+abstracts embedded into vectors and stored as csv
Result: articles are loaded into neo4j database
"""
import csv
import os
import time

from lxml import etree
from pathlib import Path
import neo4j
from typing import Any, Generator

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
                gene_name = annotation.findtext("text", default="notKnownGeneName").strip()
                gene_id = annotation.findtext("infon[@key='identifier']", default="notKnownGeneID")
                homologene = annotation.findtext("infon[@key='NCBI Homologene']", default="notKnownHomologene")

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


def batch(iterable: list, size: int) -> Generator[list, Any, None]:
    """
    Split a list into smaller batches of fixed size.

    This generator function yields consecutive slices of the input list,
    each of length `size`, except possibly the last one if the total number
    of items is not evenly divisible by the batch size.

    It is particularly useful for processing large collections (e.g., database inserts)
    in manageable chunks to avoid excessive memory use or transaction overhead.

    Example:
        >>> list(batch([1, 2, 3, 4, 5, 6, 7], size=3))
        [[1, 2, 3], [4, 5, 6], [7]]

    Args:
        iterable (list): The input list to be divided into batches.
        size (int): The number of elements in each batch.

    Yields:
        list: A sublist of the input list of length up to `size`.

    Logic:
        - The function loops over the input list in steps of `size` using `range`.
        - On each step, it slices a chunk `iterable[i:i + size]` and yields it.
        - Uses `yield` to avoid creating all chunks at once, improving memory usage.
    """
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


if __name__ == "__main__":
    batch_upload_articles_query = """
        UNWIND $batch AS data
    MERGE (d:Document {id: data.id})
    SET d.title = data.title,
        d.year = data.year,
        d.journal = data.journal,
        d.abstract = data.abstract,
        d.article_id_pmc = data.pmcid,
        d.authors = data.authors
    
    FOREACH (author IN data.authors |
        MERGE (a:Author {name: author})
        MERGE (a)-[:is_author_of]->(d)
    )
    
    FOREACH (gene IN data.genes |
        MERGE (g:Gene {id: gene.id})
        SET g.name = gene.name,
            g.ncbi_homologene = gene.ncbi_homologene
        MERGE (g)-[r:is_in]->(d)
        SET r.count = gene.count
    )
    """
    batch_upload_embeddings_query = """
        UNWIND $batch AS data
        MATCH (d:Document {id: data.id})
        SET d.embedding = apoc.convert.fromJsonList(data.embedding)
    """
    batch_size = 500
    conn = Neo4jConnection(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    # conn.query("MATCH (n) DETACH DELETE n")
    # conn.query('CREATE CONSTRAINT constraint_document IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE')
    # conn.query('CREATE CONSTRAINT constraint_author IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE')
    # conn.query('CREATE CONSTRAINT constraint_gene IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE')
    # conn.query("SHOW CONSTRAINTS", print_results=True)

    start = time.time()

    # extract data from xmls into list of dictionaries ready to be fed into the db
    article_data_list = []
    for dir in os.listdir(DATA_DIR / "breast_cancer"):
        for file in os.listdir(DATA_DIR / "breast_cancer" / dir):
            article_data_list.append(extract_article(DATA_DIR / "breast_cancer" / dir / file))
        print(dir + " done.")

    # upload articles data
    for i, batch_chunk in enumerate(batch(article_data_list, batch_size)):
        print(f"Pushing batch {i + 1}...")
        conn.query(batch_upload_articles_query, {"batch": batch_chunk})

    # read embeddings data from csv
    emb_data_list = []
    with open(DATA_DIR / "breast_cancer_embeddings_2020_2025.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=",", quotechar='|')
        for row in reader:
            emb_data_list.append({"id": row[0], "embedding": row[1]})
        print("All data from csv have been read.")

    # upload embeddings data
    for i, batch_chunk in enumerate(batch(emb_data_list, batch_size)):
        print(f"Pushing batch {i + 1}...")
        conn.query(batch_upload_embeddings_query, {"batch": batch_chunk})

    end = time.time()
    # time for aura: ~ 60 s; time for desktop ~ 75 min!
    print(f"Total time: {round(end - start, 2)} seconds.")
