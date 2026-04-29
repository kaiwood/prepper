from openai import OpenAI

from .config import load_config, resolve_model_name


def get_client(model: str | None = None) -> tuple[OpenAI, str]:
    config = load_config()
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    return client, resolve_model_name(model)
