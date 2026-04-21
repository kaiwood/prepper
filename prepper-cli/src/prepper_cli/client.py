from openai import OpenAI

from .config import load_config


def get_client() -> tuple[OpenAI, str]:
    config = load_config()
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    return client, config.model
