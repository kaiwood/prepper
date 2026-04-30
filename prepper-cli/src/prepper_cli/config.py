import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_OPENROUTER_MODEL = "openai/gpt-5.4"


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    base_url: str
    model: str
    default_system_prompt: str


def load_default_system_prompt_name() -> str:
    load_dotenv()

    default_system_prompt = os.environ.get(
        "PREPPER_DEFAULT_SYSTEM_PROMPT", "coding_focus"
    ).strip()
    if not default_system_prompt:
        raise ValueError("PREPPER_DEFAULT_SYSTEM_PROMPT cannot be empty")
    return default_system_prompt


def resolve_model_name(model: str | None = None) -> str:
    load_dotenv()
    resolved = model or os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    return resolved.strip() or DEFAULT_OPENROUTER_MODEL


def load_config() -> OpenRouterConfig:
    load_dotenv()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required")

    base_url = os.environ.get(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    ).strip()
    model = resolve_model_name()
    default_system_prompt = load_default_system_prompt_name()

    return OpenRouterConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        default_system_prompt=default_system_prompt,
    )
