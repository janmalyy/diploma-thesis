import asyncio

import requests
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from diploma_thesis.settings import E_INFRA_API_KEY, EINFRA_URL


def fetch_list_of_supported_einfra_models(api_token: str) -> list[dict]:
    url = EINFRA_URL + "models"
    headers = {"Authorization": f"Bearer {api_token}"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json().get("data", [])
    models_list = [model.get("id") for model in data]

    return models_list


async def run_einfra(prompt: str, model_name: str) -> str:
    available_models = ['mini', 'coder', 'agentic', 'thinker', 'qwen3-reranker-4b', 'qwen3-embedding-4b', 'llama-4-scout-17b-16e-instruct', 'mxbai-embed-large:latest', 'multilingual-e5-large-instruct', 'nomic-embed-text-v2-moe', 'nomic-embed-text-v1.5', 'qwen3-coder', 'mistral-large', 'qwen3-coder-next', 'qwen3-coder-30b', 'kimi-k2.5', 'gpt-oss-120b', 'deepseek-v3.2-thinking', 'glm-4.7', 'deepseek-v3.2', 'qwen3.5']

    if model_name not in available_models:
        raise ValueError(f"Model {model_name} is not supported. Try e.g. 'gpt-oss-120b' instead.")

    model = OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            base_url=EINFRA_URL,
            api_key=E_INFRA_API_KEY,
        ),
    )
    agent = Agent(model)
    result = await agent.run(prompt)
    return result.output


async def main() -> None:
    prompt = "Return OK if you can hear me."
    model_name = "gpt-oss-120b"

    response = await run_einfra(prompt, model_name)
    print(response)


if __name__ == "__main__":
    # asyncio.run(main())
    print(fetch_list_of_supported_einfra_models(E_INFRA_API_KEY))
