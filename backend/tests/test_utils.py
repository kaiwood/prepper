import pytest

from app.helpers.utils import (
    resolve_difficulty,
    resolve_max_tokens_override,
    resolve_model_setting_override,
    resolve_model_settings,
    resolve_roundtrip_limit,
)
from prepper_cli.system_prompts import PromptDescriptor


def _make_descriptor(**overrides) -> PromptDescriptor:
    defaults = dict(
        id="coding_focus",
        name="Coding Interview",
        temperature=0.5,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=500,
        content="prompt",
        interview_rating_enabled=True,
        default_question_roundtrips=5,
        min_question_roundtrips=1,
        max_question_roundtrips=10,
        pass_threshold=7.0,
        difficulty_enabled=True,
        difficulty_levels=("easy", "medium", "hard"),
        default_difficulty="medium",
    )
    defaults.update(overrides)
    return PromptDescriptor(**defaults)


def test_resolve_roundtrip_limit_uses_default_and_accepts_bounds():
    descriptor = _make_descriptor(default_question_roundtrips=4)

    assert resolve_roundtrip_limit(None, descriptor) == 4
    assert resolve_roundtrip_limit(1, descriptor) == 1
    assert resolve_roundtrip_limit(10, descriptor) == 10


def test_resolve_roundtrip_limit_rejects_invalid_prompt_configuration():
    descriptor = _make_descriptor(
        default_question_roundtrips=11,
        min_question_roundtrips=1,
        max_question_roundtrips=10,
    )

    with pytest.raises(ValueError, match="prompt roundtrip configuration is invalid"):
        resolve_roundtrip_limit(None, descriptor)


def test_resolve_roundtrip_limit_rejects_bool_as_non_integer():
    descriptor = _make_descriptor()

    with pytest.raises(ValueError, match="max_question_roundtrips must be an integer"):
        resolve_roundtrip_limit(True, descriptor)


def test_resolve_difficulty_defaults_and_normalizes_supported_values():
    descriptor = _make_descriptor(default_difficulty="hard")

    assert resolve_difficulty(None, descriptor) == "hard"
    assert resolve_difficulty(" EASY ", descriptor) == "easy"


def test_resolve_difficulty_rejects_prompt_specific_unsupported_level():
    descriptor = _make_descriptor(difficulty_levels=("easy", "medium"))

    with pytest.raises(
        ValueError,
        match="difficulty 'hard' is not supported for this prompt",
    ):
        resolve_difficulty("hard", descriptor)


def test_resolve_difficulty_ignores_blank_when_disabled():
    descriptor = _make_descriptor(difficulty_enabled=False)

    assert resolve_difficulty("   ", descriptor) is None


def test_resolve_model_setting_override_rejects_bool():
    with pytest.raises(ValueError, match="temperature must be a number"):
        resolve_model_setting_override("temperature", True)


def test_resolve_model_settings_merges_overrides_with_prompt_defaults():
    descriptor = _make_descriptor(
        temperature=0.4,
        top_p=0.95,
        frequency_penalty=0.2,
        presence_penalty=0.1,
        max_tokens=700,
    )

    settings = resolve_model_settings(
        {"temperature": 0.9, "presence_penalty": -0.3},
        descriptor,
    )

    assert settings == {
        "temperature": 0.9,
        "top_p": 0.95,
        "frequency_penalty": 0.2,
        "presence_penalty": -0.3,
        "max_tokens": 700,
    }


def test_resolve_max_tokens_override_accepts_positive_integer():
    assert resolve_max_tokens_override(1200) == 1200


def test_resolve_max_tokens_override_rejects_bool_and_non_positive_values():
    with pytest.raises(ValueError, match="max_tokens must be an integer"):
        resolve_max_tokens_override(True)

    with pytest.raises(ValueError, match="max_tokens must be between"):
        resolve_max_tokens_override(0)


def test_resolve_model_settings_allows_max_tokens_override():
    descriptor = _make_descriptor(max_tokens=1200)

    settings = resolve_model_settings({"max_tokens": 900}, descriptor)

    assert settings["max_tokens"] == 900
