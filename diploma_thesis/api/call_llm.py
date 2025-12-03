import requests
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from diploma_thesis.settings import E_INFRA_API_KEY


def fetch_list_of_supported_einfra_models(api_token: str) -> list[dict]:
    url = "https://chat.ai.e-infra.cz/api/models"
    headers = {"Authorization": f"Bearer {api_token}"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json().get("data", [])
    models_list = [model.get("id") for model in data]

    return models_list


def run_einfra(prompt: str, model_name: str) -> str:
    available_models = ['gpt-oss-120b', 'deepseek-r1', 'qwen3-coder', 'qwen2.5-coder:32b-instruct-q8_0', 'medgemma:27b-it', 'mistral-small3.2:24b-instruct-2506-q8_0', 'phi4:14b-q8_0', 'aya-expanse:32b', 'llama-4-scout-17b-16e-instruct', 'eocs-knowledge-base', 'metacentrum-docs-problemsolver', 'command-a:latest', 'mistral-small3.1:24b-instruct-2503-q8_0', 'llama3.3:latest', 'gemma3:27b-it', 'qwen2.5-coder:32b', 'rsqkit-research-software-quality', 'qwen3-coder-30b', 'qwen3-embedding-4b', 'sec-certs-common-criteria']
    if model_name not in available_models:
        raise ValueError(f"Model {model_name} is not supported. Try e.g. 'gpt-oss-120b' instead.")

    model = OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            base_url='https://chat.ai.e-infra.cz/api',
            api_key=E_INFRA_API_KEY,
        ),
    )
    agent = Agent(model)
    result = agent.run_sync(prompt)
    return result.output


# ids > články > texty > prompt > odpověď
if __name__ == '__main__':
    prompt = "Return OK if you can hear me."
    model_name = 'gpt-oss-120b'
    response = run_einfra(prompt, model_name)
    print(response)
