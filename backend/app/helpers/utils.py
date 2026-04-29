from prepper_cli import (
    PromptDescriptor,
    get_default_system_prompt_name,
    load_prompt_descriptor,
)

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_MODEL_SETTING_BOUNDS = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "frequency_penalty": (-2.0, 2.0),
    "presence_penalty": (-2.0, 2.0),
}


def resolve_roundtrip_limit(
    requested_limit: object,
    descriptor: PromptDescriptor,
) -> int:
    default_limit = descriptor.default_question_roundtrips
    min_limit = descriptor.min_question_roundtrips
    max_limit = descriptor.max_question_roundtrips

    if min_limit < 1 or max_limit < min_limit or not (min_limit <= default_limit <= max_limit):
        raise ValueError("prompt roundtrip configuration is invalid")

    if requested_limit is None:
        return default_limit

    if isinstance(requested_limit, bool) or not isinstance(requested_limit, int):
        raise ValueError("max_question_roundtrips must be an integer")

    if requested_limit < min_limit or requested_limit > max_limit:
        raise ValueError(
            f"max_question_roundtrips must be between {min_limit} and {max_limit}"
        )

    return requested_limit


def resolve_difficulty(
    requested_difficulty: object,
    descriptor: PromptDescriptor,
) -> str | None:
    if requested_difficulty is None:
        if descriptor.difficulty_enabled:
            return descriptor.default_difficulty
        return None

    if not isinstance(requested_difficulty, str):
        raise ValueError("difficulty must be a string")

    normalized = requested_difficulty.strip().lower()
    if not normalized:
        if descriptor.difficulty_enabled:
            return descriptor.default_difficulty
        return None

    if normalized not in _VALID_DIFFICULTIES:
        raise ValueError("difficulty must be one of: easy, medium, hard")

    if not descriptor.difficulty_enabled:
        raise ValueError("difficulty is not supported for this interview type")

    if normalized not in descriptor.difficulty_levels:
        supported = ", ".join(descriptor.difficulty_levels)
        raise ValueError(
            f"difficulty '{normalized}' is not supported for this prompt. Supported: {supported}"
        )

    return normalized


def resolve_model_setting_override(name: str, value: object) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")

    minimum, maximum = _MODEL_SETTING_BOUNDS[name]
    numeric_value = float(value)
    if numeric_value < minimum or numeric_value > maximum:
        raise ValueError(f"{name} must be between {minimum:.1f} and {maximum:.1f}")

    return numeric_value


def resolve_model_settings(
    data: dict,
    descriptor: PromptDescriptor,
) -> dict[str, float | int]:
    temperature = resolve_model_setting_override(
        "temperature", data.get("temperature")
    )
    top_p = resolve_model_setting_override("top_p", data.get("top_p"))
    frequency_penalty = resolve_model_setting_override(
        "frequency_penalty", data.get("frequency_penalty")
    )
    presence_penalty = resolve_model_setting_override(
        "presence_penalty", data.get("presence_penalty")
    )

    return {
        "temperature": descriptor.temperature if temperature is None else temperature,
        "top_p": descriptor.top_p if top_p is None else top_p,
        "frequency_penalty": (
            descriptor.frequency_penalty
            if frequency_penalty is None
            else frequency_penalty
        ),
        "presence_penalty": (
            descriptor.presence_penalty
            if presence_penalty is None
            else presence_penalty
        ),
        "max_tokens": descriptor.max_tokens,
    }


def resolve_prompt_descriptor(selected_name: str | None = None) -> PromptDescriptor:
    prompt_name = (selected_name or get_default_system_prompt_name()).strip()
    return load_prompt_descriptor(prompt_name)
