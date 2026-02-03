from diploma_thesis.utils.helpers import to_machine_comparable, to_human_readable


class Variant:
    def __init__(self, input_variant: str):
        self.gene: str = ""
        self.change: str = ""
        self.terms: list[str] = []
        self.variant_string = self._normalize(input_variant)

    def _normalize(self, input_variant: str) -> str:
        """
        Normalizes variant string. 
        Handles basic HGVS-like formats.
        """
        if not input_variant:
            return ""
        v = input_variant.strip()
        # Extract gene if present (e.g. "BRCA1 C24R")
        parts = v.split()
        if len(parts) == 2:
            self.gene = parts[0]
            self.change = parts[1]
        elif len(parts) == 1:
            # Check if it's like BRCA1:c.70T>C
            if ":" in v:
                g, c = v.split(":", 1)
                self.gene = g
                self.change = c
            else:
                self.change = v
        return v

    def __str__(self):
        return f"Variant {self.variant_string}"


class TextBlock:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.human_readable, self.machine_comparable = self.build_text_block()

    def build_text_block(self):
        human_readable = to_human_readable(self.raw_text)
        machine_comparable = to_machine_comparable(human_readable)
        return human_readable, machine_comparable

    def __str__(self):
        return self.human_readable

    def __len__(self):
        return len(self.human_readable)


class SupplData:
    def __init__(self, raw_text: str, score: float, snippets: list[str] = None):
        self.raw_text = raw_text
        self.score = score
        self.snippets = snippets or []

        self.paragraphs: list[str] = []


class Article:
    def __init__(self, data_source: str, pmid: str = "", pmcid: str = "", fulltext_snippets: list[TextBlock] = None):
        self.pmid: str = pmid or ""  # for medline articles only
        self.pmcid: str = pmcid or ""
        self.data_sources: set[str] = set()   # possible combinations: (medline), (pmc), (supp), (medline, pmc, supp), (pmc, supp)
        self.data_sources.add(data_source)

        self.title: str = ""
        self.abstract: str = ""

        self.fulltext_snippets: list[TextBlock] = fulltext_snippets or []
        self.paragraphs: list[str] = []  # if variant found in the article

        self.suppl_data_list: list[SupplData] = []

        self.annotation_source: str = ""
        self.study_type: str = "Unknown"
        self.disease: str = "Unknown"
        self.relevance_score: float = 0.0

    def get_context(self) -> str:
        context = f"Article {self.pmcid if self.pmcid else self.pmid}\n"
        if self.title:
            context += f"Title: {self.title}\n"
        if self.abstract:
            context += f"Abstract: {self.abstract}\n"
        if self.paragraphs:
            context += "Relevant paragraphs:\n" + "\n".join(self.paragraphs)
        if len(self.suppl_data_list) > 0:
            context += "\nSupplementary evidence records:\n"
            for sd in self.suppl_data_list:
                context += f"(relevancy score {sd.score:.2f}):\n" + "\n".join(sd.paragraphs)
                context += "\n"
        return context

    def shorten_context(self, max_length: int = 2000):
        """Intelligently shortens the context. Mock implementation."""  # TODO
        shortened = []
        for p in self.paragraphs:
            if len(p) > max_length:
                shortened.append(p[:max_length] + "...")
            else:
                shortened.append(p)
        self.paragraphs = shortened
