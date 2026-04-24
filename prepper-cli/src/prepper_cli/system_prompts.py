from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

from .config import load_default_system_prompt_name

PROMPTS_DIRECTORY = "prompts"

_FRONT_MATTER_DELIMITER = "---"

# Known numeric fields and their expected Python types.
_FLOAT_FIELDS = {
    "temperature",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "pass_threshold",
    "easy_pass_threshold",
    "medium_pass_threshold",
    "hard_pass_threshold",
    "interviewer_pass_threshold",
}
_INT_FIELDS = {
    "max_tokens",
    "default_question_roundtrips",
    "min_question_roundtrips",
    "max_question_roundtrips",
}
_STR_FIELDS = {"id", "name", "default_difficulty"}
_BOOL_FIELDS = {"interview_rating_enabled", "difficulty_enabled"}
_LIST_FIELDS = {"rubric_criteria", "difficulty_levels", "interviewer_rubric_criteria"}


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
    interview_rating_enabled: bool = False
    default_question_roundtrips: int = 5
    min_question_roundtrips: int = 1
    max_question_roundtrips: int = 10
    pass_threshold: float = 7.0
    rubric_criteria: tuple[str, ...] = ()
    difficulty_enabled: bool = False
    difficulty_levels: tuple[str, ...] = ("easy", "medium", "hard")
    default_difficulty: str = "medium"
    easy_pass_threshold: float | None = None
    medium_pass_threshold: float | None = None
    hard_pass_threshold: float | None = None
    interviewer_pass_threshold: float = 7.0
    interviewer_rubric_criteria: tuple[str, ...] = ()


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
        elif key in _BOOL_FIELDS:
            metadata[key] = value.lower() in {"1", "true", "yes", "on"}
        elif key in _LIST_FIELDS:
            metadata[key] = tuple(
                item.strip() for item in value.split("|") if item.strip()
            )

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

    metadata, body = _parse_front_matter(
        _load_raw_prompt_text(normalized_name))

    try:
        descriptor = PromptDescriptor(
            id=str(metadata.get("id", normalized_name)),
            name=str(metadata.get("name", normalized_name)),
            temperature=float(metadata.get("temperature", 0.7)),
            top_p=float(metadata.get("top_p", 1.0)),
            frequency_penalty=float(metadata.get("frequency_penalty", 0.0)),
            presence_penalty=float(metadata.get("presence_penalty", 0.0)),
            max_tokens=int(metadata.get("max_tokens", 800)),
            content=body,
            interview_rating_enabled=bool(
                metadata.get("interview_rating_enabled", False)
            ),
            default_question_roundtrips=int(
                metadata.get("default_question_roundtrips", 5)
            ),
            min_question_roundtrips=int(
                metadata.get("min_question_roundtrips", 1)),
            max_question_roundtrips=int(
                metadata.get("max_question_roundtrips", 10)),
            pass_threshold=float(metadata.get("pass_threshold", 7.0)),
            rubric_criteria=tuple(metadata.get("rubric_criteria", ())),
            difficulty_enabled=bool(metadata.get("difficulty_enabled", False)),
            difficulty_levels=tuple(metadata.get(
                "difficulty_levels", ("easy", "medium", "hard"))),
            default_difficulty=str(metadata.get(
                "default_difficulty", "medium")),
            easy_pass_threshold=(
                float(metadata["easy_pass_threshold"])
                if "easy_pass_threshold" in metadata
                else None
            ),
            medium_pass_threshold=(
                float(metadata["medium_pass_threshold"])
                if "medium_pass_threshold" in metadata
                else None
            ),
            hard_pass_threshold=(
                float(metadata["hard_pass_threshold"])
                if "hard_pass_threshold" in metadata
                else None
            ),
            interviewer_pass_threshold=float(metadata.get("interviewer_pass_threshold", 7.0)),
            interviewer_rubric_criteria=tuple(metadata.get("interviewer_rubric_criteria", ())),
        )

        if descriptor.difficulty_enabled:
            allowed = set(descriptor.difficulty_levels)
            if not allowed:
                raise ValueError(
                    "difficulty_levels must include at least one value")
            if descriptor.default_difficulty not in allowed:
                raise ValueError(
                    "default_difficulty must be one of difficulty_levels"
                )

        return descriptor
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid front matter in prompt '{normalized_name}': {exc}"
        ) from exc


def list_prompt_descriptors() -> list[PromptDescriptor]:
    """Return :class:`PromptDescriptor` objects for every bundled prompt, sorted by id."""
    return [load_prompt_descriptor(name) for name in list_system_prompt_names()]


def get_default_system_prompt_name() -> str:
    return load_default_system_prompt_name()
