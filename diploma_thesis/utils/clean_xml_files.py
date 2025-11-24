import os
import shutil
from pathlib import Path

from diploma_thesis.settings import DATA_DIR
from diploma_thesis.utils.parse_xml import get_document_from_xml


def has_abstract(xml_file_path) -> bool:
    document = get_document_from_xml(xml_file_path)
    for passage in document.findall("passage"):
        for infon in passage.findall("infon"):
            if infon.get("key") == "type":
                infon_type = infon.text
                break

        if infon_type == "abstract":
            text_el = passage.find("text")
            return text_el is not None and text_el.text is not None and text_el.text.strip() != ""

    return False


def remove_articles_without_abstract(dir: Path, delete: bool) -> None:
    new_dir_name = dir.stem.strip("pubmed") + "to_be_removed"
    new_dir_path = DATA_DIR / "2025_11_19" / "to_be_removed" / new_dir_name
    if delete:
        for file in dir.iterdir():
            if not has_abstract(file):
                file.unlink()
    else:
        if not new_dir_path.exists():
            new_dir_path.mkdir()
        for file in dir.iterdir():
            if not has_abstract(file):
                shutil.move(file, new_dir_path / file.name)


if __name__ == '__main__':
    for directory in (DATA_DIR / "2025_11_19").iterdir():
        remove_articles_without_abstract(directory, False)
