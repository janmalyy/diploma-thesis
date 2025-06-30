import csv
import os
import random
import time

import pandas as pd

from diploma_thesis.utils.parse_xml import get_document_from_xml, get_nodes_from_xml, write_pretty_xml
from diploma_thesis.api.pubtator_api import fetch_pubtator_data_by_id


def extract_gene_disease_associations_from_xml(xml_file_path: str) -> set[tuple[str, str, str]]:
    """
    Extracts unique Gene-Disease associations from an XML file.
    Genes and diseases are stored as IDs.

    Args:
        xml_file_path (str): Path to the input XML file.

    Returns:
        set[tuple[str, str, str]]: Set of unique (id1, id2, relation_type) triplets.
        E.g.: {('7341', 'MESH:C566419', 'Association'), ('100313772', 'MESH:C566419', 'Association')}
    """
    document = get_document_from_xml(xml_file_path)
    triplets_set = set()

    for relation in document.findall("relation"):
        type1 = type2 = id1 = id2 = relation_type = None

        for infon in relation.findall("infon"):
            key = infon.get("key")
            if key == "role1":
                type1, id1 = infon.text.split("|")  # origin looks like "Gene|7157"
            elif key == "role2":
                type2, id2 = infon.text.split("|")
            elif key == "type":
                relation_type = infon.text

        if None in (type1, type2, id1, id2, relation_type):
            continue  # skip malformed relation

        if {type1, type2} == {"Gene", "Disease"}:
            normalized_ids = tuple(sorted([id1, id2]))
            triplets_set.add((normalized_ids[0], normalized_ids[1], relation_type))

    return triplets_set


def get_gene_disease_associations_with_names(xml_file_path: str) -> set[tuple[str, str, str]]:
    """
    Extracts unique Gene-Disease associations from an XML file.
    Genes and diseases are stored as names as they appear in the XML file.
    Args:
        xml_file_path (str): Path to the input XML file.

    Returns set[tuple[str, str, str]]: Set of unique (name1, name2, relation_type) triplets.
        E.g.: {('SUMO1', 'orofacial cleft', 'Association'), ('MIR54', 'orofacial cleft', 'Association')}
    """
    nodes_list = get_nodes_from_xml(xml_file_path)
    id_to_name = {node.identifier: node.name for node in nodes_list}
    triplets = extract_gene_disease_associations_from_xml(xml_file_path)
    triplets_with_names = set()
    for triplet in triplets:
        triplets_with_names.add((id_to_name[triplet[0]], id_to_name[triplet[1]], triplet[2]))

    return triplets_with_names


def get_title_with_abstract(xml_file_path: str) -> str:
    document = get_document_from_xml(xml_file_path)
    title_with_abstract = ""
    for passage in document.findall("passage"):
        for text in passage.findall("text"):
            title_with_abstract += " " + str(text.text)

    return title_with_abstract


def create_df_from_xmls(directory_path: str) -> pd.DataFrame:
    """
    Notes: We skip anyhow malformed xmls.
    """
    to_be_df = []
    for xml_file in os.listdir(directory_path):
        try:
            triplets_with_names = list(get_gene_disease_associations_with_names(f"{directory_path}/{xml_file}"))
            text = get_title_with_abstract(f"{directory_path}/{xml_file}")
            file_id = xml_file.split("_")[1].split(".")[0]  # article_15824.xml --> 15824
            row = [file_id, text, *triplets_with_names]
            to_be_df.append(row)
        except:
            continue
    # count the maximum length of row => max number of triplets => number of columns in df
    max_len = max([len(row) for row in to_be_df])
    df = pd.DataFrame(to_be_df, columns=["file_id", "text", *[f"triplet{i}" for i in range(max_len - 2)]])

    return df


def create_testset(df: pd.DataFrame) -> pd.DataFrame:
    # get xmls with at least 1 relation but omit few examples with many annotations just to not have that many columns
    with_relation_df = df[df["triplet0"].notna() & df["triplet15"].isna()].copy(deep=True)
    # get randomly n xmls without relations, where the text has at least 150 chars and where n = 70 % of number of samples with at least one relation
    without_relation_df_sample = (df[df["triplet0"].isna() & (df["text"].str.len() > 150)]
                                  .sample(n=int(len(df[df["triplet0"].notna()]) * 0.7),
                                          random_state=42).copy(deep=True))
    test_dataset = pd.concat([without_relation_df_sample, with_relation_df])
    test_dataset = test_dataset.dropna(axis=1, how="all")  # drop columns without annotations

    return test_dataset


if __name__ == "__main__":
    # fetch many xmls
    # for i in range(3000):
    #     pmid = random.randint(1, 38_000_000)
    #     try:
    #         result = fetch_pubtator_data_by_id(pmid)
    #         time.sleep(0.3)
    #         write_pretty_xml(result, f"data/article_{pmid}.xml")
    #     except Exception as e:
    #         continue

    print("Number of articles fetched:", len(os.listdir("../data")))

    df = create_df_from_xmls("../data")

    testset = create_testset(df)
    print(testset.info())

    testset.to_csv("test_dataset.csv", index=False, quoting=csv.QUOTE_ALL)

