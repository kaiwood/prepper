import pytest

from prepper_cli.system_prompts import (
    get_default_system_prompt_name,
    list_system_prompt_names,
    load_system_prompt,
)


def test_list_system_prompts_contains_bundled_prompts():
    names = list_system_prompt_names()

    assert "interview_coach" in names
    assert "behavioral_focus" in names
    assert "coding_focus" in names


def test_load_system_prompt_reads_prompt_content():
    text = load_system_prompt("interview_coach")

    assert "interview preparation coach" in text


def test_load_system_prompt_rejects_unknown_name():
    with pytest.raises(ValueError, match="Unknown system prompt"):
        load_system_prompt("does_not_exist")


def test_default_system_prompt_is_configurable_via_env(monkeypatch):
    monkeypatch.setenv("PREPPER_DEFAULT_SYSTEM_PROMPT", "coding_focus")

    assert get_default_system_prompt_name() == "coding_focus"
