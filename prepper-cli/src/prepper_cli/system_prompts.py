from __future__ import annotations

from importlib import resources

from .config import load_default_system_prompt_name

PROMPTS_DIRECTORY = "prompts"


def list_system_prompt_names() -> list[str]:
    prompts_dir = resources.files("prepper_cli").joinpath(PROMPTS_DIRECTORY)
    return sorted(
        path.stem
        for path in prompts_dir.iterdir()
        if path.is_file() and path.suffix == ".md"
    )


def load_system_prompt(name: str) -> str:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("system prompt name is required")

    available = list_system_prompt_names()
    if normalized_name not in available:
        available_text = ", ".join(available)
        raise ValueError(
            f"Unknown system prompt '{normalized_name}'. Available: {available_text}"
        )

    prompt_path = resources.files("prepper_cli").joinpath(
        PROMPTS_DIRECTORY, f"{normalized_name}.md"
    )
    return prompt_path.read_text(encoding="utf-8").strip()


def get_default_system_prompt_name() -> str:
    return load_default_system_prompt_name()
