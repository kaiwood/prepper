import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    base_url: str
    model: str


def load_config() -> OpenRouterConfig:
    load_dotenv()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required")

    base_url = os.environ.get(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    ).strip()
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()

    return OpenRouterConfig(api_key=api_key, base_url=base_url, model=model)
