"""
uživatel by si mohl nastavovat recall precision trade off (jak píšou zde: https://pmc.ncbi.nlm.nih.gov/articles/PMC10066029/)
variomes mi dá k variantě data a snippety z fultextů
já si dohledám pmc full texty s anotacemi - pubtator
přes pubtator si anotuji i raw data z suppl. files - to možná ne, zatím nefunguje
a pak nasypu do llmka na souhrn - biomistral

výstupem bude:
- ke každému článku pár atributů: typ studie, kvalita, zmiňovaná nemoc
- pak celkový souhrn té varianty vzhledem k literatuře

DATABÁZE VE VARIOMES NENÍ STEJNÁ JAKO V PUBTATORU!!!
variomes používá open access, pubtator mining subset nebo co
"""
import time

import xml.etree.ElementTree as ET

from diploma_thesis.new.pubtator import fetch_pubtator_data_by_ids, annotate_raw_text, parse_pubtator_data
from diploma_thesis.new.sibils import fetch_variomes_data, parse_variomes_data
from diploma_thesis.utils.parse_xml import get_title_with_abstract

if __name__ == '__main__':
    start = time.time()
    # todo normalizovat varianty zadávané do variomes; nebere rsIDs
    # variant = "NOP10 c.34G>C" # akorát dat
    # variant = "XPC c.416T>C"  #skoro žádná data
    variant = "NHP2	c.302G>A"
    data = fetch_variomes_data(variant)
    parsed_variomes_data = parse_variomes_data(data)
    print("all_pmc_ids_found_in_variomes", parsed_variomes_data["pmc_ids"])
    print("pmc with snippets", parsed_variomes_data["pmc"])
    print("pmc len", len(parsed_variomes_data["pmc"]))
    print("suppl len", len(parsed_variomes_data["suppl"]))
    pubtator_data = fetch_pubtator_data_by_ids(list(set(parsed_variomes_data["pmc_ids"])))
    # TODO když nenajdu článek v pubtatoru, najdu si ho přímo přes PMC a použiju ho bez anotací!
    print("pubtator_data len", len(pubtator_data))
    print("pubtator_found_ids", pubtator_data.keys())
    # current_id = "PMC8794197"
    # print("current PMCID: ", current_id)
    # print("SNIPPETS", parsed_variomes_data["pmc"][current_id])
    # print("PUBTATOR PREPARED DATA", parse_pubtator_data(pubtator_data[current_id], parsed_variomes_data["pmc"][current_id]))

    context = ""
    for pmc_id in parsed_variomes_data["pmc"].keys():
        if pmc_id not in pubtator_data.keys():
            print(f"{pmc_id} not found in PubTator.")
            continue
        context += f"Article {pmc_id}\n" + parse_pubtator_data(pubtator_data[pmc_id], parsed_variomes_data["pmc"][pmc_id]) + "\n\n"
    print(context)
    print("time: ", round(time.time() - start, 2), "s")
