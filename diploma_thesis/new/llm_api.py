from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from diploma_thesis.settings import DATA_DIR


def build_prompt(context: str, gene_symbol: str, variant: str) -> str:
    with open(DATA_DIR / "prompts" / "test_prompt.md") as f:
        prompt = f.read()
    prompt = prompt.replace("CONTEXT", context)
    prompt = prompt.replace("GENE_SYMBOL", gene_symbol)
    prompt = prompt.replace("VARIANT", variant)

    return prompt


model_name = "BioMistral/BioMistral-7B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)


def run_bio_mistral(prompt: str) -> str:
    """
    Runs BioMistral locally using the Transformers library.
    """
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    outputs = model.generate(
        **inputs,
        max_new_tokens=500,
        temperature=0.2,
        do_sample=True
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return response.strip()


if __name__ == '__main__':
    prompt = "Return OK if you can hear me."
    response = run_bio_mistral(prompt)
    print(response)
