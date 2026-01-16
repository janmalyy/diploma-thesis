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


class Article:
    def __init__(self, pmcid: str, snippets: list[str] = None):
        self.pmcid = pmcid
        self.snippets = snippets or []
        self.title: str = ""
        self.abstract: str = ""
        self.annotated_content: str = ""
        self.suppl_info: str = ""
        self.study_type: str = "Unknown"
        self.quality: str = "Unknown"
        self.disease: str = "Unknown"
        self.relevance_score: float = 0.0

    def get_context(self) -> str:
        if self.annotated_content:
            return self.annotated_content
        
        context = f"Article {self.pmcid}\n"
        if self.title:
            context += f"Title: {self.title}\n"
        if self.abstract:
            context += f"Abstract: {self.abstract}\n"
        if self.snippets:
            context += "Snippets:\n" + "\n".join(self.snippets) + "\n"
        if self.suppl_info:
            context += f"Supplemental Info: {self.suppl_info}\n"
        return context

    def shorten_context(self, max_length: int = 2000):
        """Intelligently shortens the context. Mock implementation."""
        if len(self.annotated_content) > max_length:
            # In a real implementation, we would keep the most relevant paragraphs
            self.annotated_content = self.annotated_content[:max_length] + "... [shortened]"
