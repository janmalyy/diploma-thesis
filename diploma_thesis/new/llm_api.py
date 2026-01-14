from llama_cpp import Llama

from diploma_thesis.settings import DATA_DIR


def build_prompt(context: str, gene_symbol: str, variant: str) -> str:
    with open(DATA_DIR / "prompts" / "test_prompt.md") as f:
        prompt = f.read()
    prompt = prompt.replace("CONTEXT", context)
    prompt = prompt.replace("GENE_SYMBOL", gene_symbol)
    prompt = prompt.replace("VARIANT", variant)

    return prompt


if __name__ == '__main__':
    # prompt = "Return OK if you can hear me."
    # Chat Completion API
    # Set gpu_layers to the number of layers to offload to GPU. Set to 0 if no GPU acceleration is available on your system.
    llm = Llama(
        model_path=str(DATA_DIR / "BioMistral-7B.Q4_K_M.gguf"),  # Download the model file first
        n_ctx=4096,  # The max sequence length to use - note that longer sequence lengths require much more resources
        n_threads=6,  # The number of CPU threads to use, tailor to your system and the resulting performance
        n_gpu_layers=0,  # The number of layers to offload to GPU, if you have GPU acceleration available
        chat_format="llama-2",  # Set chat_format according to the model you are using
        verbose=True
    )
    response_generator = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": "You are a story writing assistant."},
            {
                "role": "user",
                "content": "Write a story about llamas."
            }
        ],
        stream=True
    )
    for chunk in response_generator:
        # Each chunk follows the OpenAI 'delta' format
        if 'content' in chunk['choices'][0]['delta']:
            token = chunk['choices'][0]['delta']['content']
            print(token, end="", flush=True)  # flush=True ensures it prints immediately

    print(response_generator)
