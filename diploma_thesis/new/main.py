"""
uživatel by si mohl nastavovat recall precision trade off (jak píšou zde: https://pmc.ncbi.nlm.nih.gov/articles/PMC10066029/)
variomes mi dá k variantě data a snippety z fultextů
já si dohledám pmc full texty s anotacemi - pubtator
přes pubtator si anotuji i raw data z suppl. files - to možná ne, zatím nefunguje
a pak nasypu do llmka na souhrn - biomistral


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

    variant = "NOP10 c.34G>C"
    data = fetch_variomes_data(variant)
    parsed_variomes_data = parse_variomes_data(data)
    print("pmc_ids", parsed_variomes_data["pmc_ids"])
    print("pmc", parsed_variomes_data["pmc"])
    print("pmc len", len(parsed_variomes_data["pmc"]))
    print("suppl len", len(parsed_variomes_data["suppl"]))
    pubtator_data = fetch_pubtator_data_by_ids(list(set(parsed_variomes_data["pmc_ids"])))
    # TODO když nenajdu článek v pubtatoru, najdu si ho přímo přes PMC a použiju ho bez anotací!
    print("pubtator_data len", len(pubtator_data))
    print("pubtator_data", pubtator_data)
    current_id = "PMC8794197"
    print("current PMCID: ", current_id)
    print("SNIPPETS", parsed_variomes_data["pmc"][current_id])

    print("PUBTATOR PREPARED DATA", parse_pubtator_data(pubtator_data[current_id], parsed_variomes_data["pmc"][current_id]))

    print("time: ", round(time.time() - start, 2), "s")
