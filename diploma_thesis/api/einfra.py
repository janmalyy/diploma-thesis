import asyncio
import requests
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from diploma_thesis.settings import E_INFRA_API_KEY, DATA_DIR, EINFRA_URL


def fetch_list_of_supported_einfra_models(api_token: str) -> list[dict]:
    url = EINFRA_URL + "models"
    headers = {"Authorization": f"Bearer {api_token}"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json().get("data", [])
    models_list = [model.get("id") for model in data]

    return models_list


async def run_einfra(prompt: str, model_name: str) -> str:
    available_models = ['aya-expanse:32b', 'command-a:latest', 'deepseek-r1', 'eocs-knowledge-base', 'gemma3:27b-it', 'gpt-oss-120b', 'llama-4-scout-17b-16e-instruct', 'llama3.3:latest', 'medgemma:27b-it', 'metacentrum-docs-problemsolver', 'mistral-small3.1:24b-instruct-2503-q8_0', 'mistral-small3.2:24b-instruct-2506-q8_0', 'phi4:14b-q8_0', 'qwen2.5-coder:32b', 'qwen2.5-coder:32b-instruct-q8_0', 'qwen3-coder', 'qwen3-coder-30b', 'qwen3-embedding-4b', 'rsqkit-research-software-quality', 'sec-certs-common-criteria']

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