from diploma_thesis.new.helpers import to_machine_comparable, to_human_readable


class Variant:
    def __init__(self, input_variant: str):
        self.variant_string = self._normalize(input_variant)
        self.gene: str = ""
        self.change: str = ""
        self.terms: list[str] = []

    def _normalize(self, input_variant: str) -> str:
        """
        Normalizes variant string. 
        TODO: Implement normalization (e.g. handle rsIDs, different HGVS formats)
        """
        return input_variant.strip()

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


class Article:
    def __init__(self, pmcid: str, snippets: list[TextBlock] = None):
        self.pmcid: str = pmcid
        self.snippets: list[TextBlock] = snippets or []

        self.title: str = ""
        self.abstract: str = ""
        self.paragraphs: list[str] = []       # if variant found in the article
        self.suppl_info: str = ""       # if variant found in the supplementary data

        self.source: str = ""
        self.study_type: str = "Unknown"
        self.disease: str = "Unknown"
        self.relevance_score: float = 0.0

    def get_context(self) -> str:
        context = f"Article {self.pmcid}\n"
        if self.title:
            context += f"Title: {self.title}\n"
        if self.abstract:
            context += f"Abstract: {self.abstract}\n"
        if self.paragraphs:
            context += "Relevant paragraphs:\n" + "\n".join(self.paragraphs) + "\n"
        # if self.suppl_info:
        #     context += "Supplementary information:\n" + self.suppl_info + "\n"
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

