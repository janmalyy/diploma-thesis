from llama_cpp import Llama
from diploma_thesis.settings import DATA_DIR
from diploma_thesis.core.models import Variant, Article


class LLMSummarizer:
    def __init__(self, model_path: str = None, config: dict = None):
        """
        Initializes the LLMSummarizer.
        :param model_path: Path to the GGUF model file.
        :param config: Dictionary with LLM parameters (temperature, top_p, etc.)
        """
        self.model_path = model_path or str(DATA_DIR / "BioMistral-7B.Q4_K_M.gguf")
        self.config = config or {
            "temperature": 0.1,
            "repeat_penalty": 1.2,
            "top_p": 0.9,
            "top_k": 40,
            "max_tokens": 1024
        }
        self.llm = None

    def _ensure_model_loaded(self):
        if self.llm is None:
            try:
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=4096,
                    n_threads=4,
                    n_gpu_layers=5,
                    chat_format="llama-2",
                    verbose=False
                )
            except Exception as e:
                print(f"Failed to load LLM model from {self.model_path}: {e}")
                raise

    def build_prompt(self, variant: Variant, articles: list[Article]) -> str:
        """
        Constructs the prompt for the LLM based on variant and articles context.
        """
        context = ""
        for article in articles:
            # Use annotated content if available, otherwise fallback to fulltext_snippets
            context += f"Article {article.pmcid}\n"
            context += article.get_context() + "\n\n"

        with open(DATA_DIR / "prompts" / "test_prompt.md") as f:
            prompt = f.read()

        prompt = prompt.replace("CONTEXT", context)
        prompt = prompt.replace("GENE_SYMBOL", variant.gene)
        prompt = prompt.replace("VARIANT", str(variant))

        return prompt

    def summarize(self, variant: Variant, articles: list[Article], stream: bool = True):
        """
        Generates a summary for the given variant and context.
        """
        self._ensure_model_loaded()
        prompt = self.build_prompt(variant, articles)

        messages = [
            {
                "role": "system",
                "content": "You are a medical bioinformatics assistant. Extract clinical and genetic data accurately from provided scientific context."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        return self.llm.create_chat_completion(
            messages=messages,
            stream=stream,
            **self.config
        )


if __name__ == '__main__':
    # Simple test of the summarizer
    summarizer = LLMSummarizer()
    variant = Variant("NHP2 c.302G>A")
    articles = [
        Article(pmcid="PMC6594079", snippets=["Telomere length in patients..."])
    ]
    try:
        response = summarizer.summarize(variant, articles)
        for chunk in response:
            if 'content' in chunk['choices'][0]['delta']:
                print(chunk['choices'][0]['delta']['content'], end="", flush=True)
    except Exception as e:
        print(f"Test failed (likely missing model file): {e}")
