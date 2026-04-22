from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

from .config import load_default_system_prompt_name

PROMPTS_DIRECTORY = "prompts"

_FRONT_MATTER_DELIMITER = "---"

# Known numeric fields and their expected Python types.
_FLOAT_FIELDS = {"temperature", "top_p", "frequency_penalty", "presence_penalty"}
_INT_FIELDS = {"max_tokens"}
_STR_FIELDS = {"id", "name"}


@dataclass(frozen=True)
class PromptDescriptor:
    """Structured representation of a bundled prompt file."""

    id: str
    name: str
    temperature: float
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    max_tokens: int
    content: str


def _parse_front_matter(raw: str) -> tuple[dict[str, object], str]:
    """Parse YAML-style front matter from raw prompt file text.

    Returns a (metadata_dict, body) tuple.  If the file does not start with
    a ``---`` delimiter the metadata dict will be empty and the full text is
    treated as the body.
    """
    stripped = raw.strip()
    if not stripped.startswith(_FRONT_MATTER_DELIMITER):
        return {}, stripped

    # Find the closing delimiter (skip the opening one)
    rest = stripped[len(_FRONT_MATTER_DELIMITER):]
    close_idx = rest.find(_FRONT_MATTER_DELIMITER)
    if close_idx == -1:
        return {}, stripped

    front_matter_block = rest[:close_idx]
    body = rest[close_idx + len(_FRONT_MATTER_DELIMITER):].strip()

    metadata: dict[str, object] = {}
    for line in front_matter_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in _FLOAT_FIELDS:
            metadata[key] = float(value)
        elif key in _INT_FIELDS:
            metadata[key] = int(value)
        elif key in _STR_FIELDS:
            metadata[key] = value

    return metadata, body


def _load_raw_prompt_text(name: str) -> str:
    prompt_path = resources.files("prepper_cli").joinpath(
        PROMPTS_DIRECTORY, f"{name}.md"
    )
    return prompt_path.read_text(encoding="utf-8")


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

    _, body = _parse_front_matter(_load_raw_prompt_text(normalized_name))
    return body


def load_prompt_descriptor(name: str) -> PromptDescriptor:
    """Load a prompt file and return a fully-typed :class:`PromptDescriptor`."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("system prompt name is required")

    available = list_system_prompt_names()
    if normalized_name not in available:
        available_text = ", ".join(available)
        raise ValueError(
            f"Unknown system prompt '{normalized_name}'. Available: {available_text}"
        )

    metadata, body = _parse_front_matter(_load_raw_prompt_text(normalized_name))

    try:
        return PromptDescriptor(
            id=str(metadata.get("id", normalized_name)),
            name=str(metadata.get("name", normalized_name)),
            temperature=float(metadata.get("temperature", 0.7)),
            top_p=float(metadata.get("top_p", 1.0)),
            frequency_penalty=float(metadata.get("frequency_penalty", 0.0)),
            presence_penalty=float(metadata.get("presence_penalty", 0.0)),
            max_tokens=int(metadata.get("max_tokens", 800)),
            content=body,
        )
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid front matter in prompt '{normalized_name}': {exc}"
        ) from exc


def list_prompt_descriptors() -> list[PromptDescriptor]:
    """Return :class:`PromptDescriptor` objects for every bundled prompt, sorted by id."""
    return [load_prompt_descriptor(name) for name in list_system_prompt_names()]


def get_default_system_prompt_name() -> str:
    return load_default_system_prompt_name()
