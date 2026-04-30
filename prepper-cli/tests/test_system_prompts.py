import pytest

from prepper_cli.system_prompts import (
    PromptDescriptor,
    _parse_front_matter,
    get_default_system_prompt_name,
    list_prompt_descriptors,
    list_system_prompt_names,
    load_prompt_descriptor,
    load_system_prompt,
)


def test_list_system_prompts_contains_bundled_prompts():
    names = list_system_prompt_names()

    assert "behavioral_focus" in names
    assert "coding_focus" in names


def test_load_system_prompt_reads_prompt_content():
    text = load_system_prompt("behavioral_focus")

    assert "interview preparation coach" in text.lower() or "interviewer" in text.lower()


def test_load_system_prompt_strips_front_matter():
    text = load_system_prompt("coding_focus")

    assert not text.startswith("---")
    assert "temperature" not in text.split("\n")[0]


def test_load_system_prompt_rejects_unknown_name():
    with pytest.raises(ValueError, match="Unknown system prompt"):
        load_system_prompt("does_not_exist")


def test_default_system_prompt_is_configurable_via_env(monkeypatch):
    monkeypatch.setenv("PREPPER_DEFAULT_SYSTEM_PROMPT", "coding_focus")

    assert get_default_system_prompt_name() == "coding_focus"


# --- PromptDescriptor parsing ---


def test_parse_front_matter_extracts_known_fields():
    raw = "---\nid: my_prompt\nname: My Prompt\ntemperature: 0.3\ntop_p: 0.95\nfrequency_penalty: 0.1\npresence_penalty: 0.0\nmax_tokens: 600\ninterview_rating_enabled: true\ndefault_question_roundtrips: 5\nmin_question_roundtrips: 1\nmax_question_roundtrips: 10\npass_threshold: 7.0\nrubric_criteria: Problem understanding|Technical quality\ndifficulty_enabled: true\ndifficulty_levels: easy|medium|hard\ndefault_difficulty: medium\neasy_pass_threshold: 6.5\nmedium_pass_threshold: 7.0\nhard_pass_threshold: 7.5\n---\n\nBody text here."

    metadata, body = _parse_front_matter(raw)

    assert metadata["id"] == "my_prompt"
    assert metadata["name"] == "My Prompt"
    assert metadata["temperature"] == pytest.approx(0.3)
    assert metadata["top_p"] == pytest.approx(0.95)
    assert metadata["frequency_penalty"] == pytest.approx(0.1)
    assert metadata["presence_penalty"] == pytest.approx(0.0)
    assert metadata["max_tokens"] == 600
    assert metadata["interview_rating_enabled"] is True
    assert metadata["default_question_roundtrips"] == 5
    assert metadata["min_question_roundtrips"] == 1
    assert metadata["max_question_roundtrips"] == 10
    assert metadata["pass_threshold"] == pytest.approx(7.0)
    assert metadata["rubric_criteria"] == (
        "Problem understanding",
        "Technical quality",
    )
    assert metadata["difficulty_enabled"] is True
    assert metadata["difficulty_levels"] == ("easy", "medium", "hard")
    assert metadata["default_difficulty"] == "medium"
    assert metadata["easy_pass_threshold"] == pytest.approx(6.5)
    assert metadata["medium_pass_threshold"] == pytest.approx(7.0)
    assert metadata["hard_pass_threshold"] == pytest.approx(7.5)
    assert body == "Body text here."


def test_parse_front_matter_returns_empty_dict_when_no_front_matter():
    raw = "Just plain text with no front matter."

    metadata, body = _parse_front_matter(raw)

    assert metadata == {}
    assert body == raw


def test_load_prompt_descriptor_returns_correct_fields():
    descriptor = load_prompt_descriptor("coding_focus")

    assert isinstance(descriptor, PromptDescriptor)
    assert descriptor.id == "coding_focus"
    assert descriptor.name == "Coding Interview"
    assert descriptor.temperature == pytest.approx(0.3)
    assert descriptor.top_p == pytest.approx(1.0)
    assert descriptor.frequency_penalty == pytest.approx(0.2)
    assert descriptor.presence_penalty == pytest.approx(0.0)
    assert descriptor.max_tokens == 1200
    assert descriptor.interview_rating_enabled is True
    assert descriptor.default_question_roundtrips == 5
    assert descriptor.min_question_roundtrips == 1
    assert descriptor.max_question_roundtrips == 10
    assert descriptor.pass_threshold == pytest.approx(7.0)
    assert descriptor.rubric_criteria == (
        "Problem understanding",
        "Technical quality",
        "Communication",
    )
    assert descriptor.difficulty_enabled is True
    assert descriptor.difficulty_levels == ("easy", "medium", "hard")
    assert descriptor.default_difficulty == "medium"
    assert descriptor.easy_pass_threshold == pytest.approx(6.5)
    assert descriptor.medium_pass_threshold == pytest.approx(7.0)
    assert descriptor.hard_pass_threshold == pytest.approx(7.5)
    assert "interviewer" in descriptor.content.lower()
    assert not descriptor.content.startswith("---")


def test_load_prompt_descriptor_behavioral_focus():
    descriptor = load_prompt_descriptor("behavioral_focus")

    assert descriptor.id == "behavioral_focus"
    assert descriptor.name == "Behavioral Interview"
    assert descriptor.temperature == pytest.approx(0.5)
    assert descriptor.max_tokens == 1200
    assert descriptor.interview_rating_enabled is True
    assert descriptor.pass_threshold == pytest.approx(7.0)


def test_load_prompt_descriptor_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown system prompt"):
        load_prompt_descriptor("does_not_exist")


def test_load_prompt_descriptor_rejects_invalid_default_difficulty(monkeypatch):
    raw = "---\nid: sample\nname: Sample\ndifficulty_enabled: true\ndifficulty_levels: easy|hard\ndefault_difficulty: medium\n---\n\nBody"

    monkeypatch.setattr(
        "prepper_cli.system_prompts.list_system_prompt_names",
        lambda: ["sample"],
    )
    monkeypatch.setattr(
        "prepper_cli.system_prompts._load_raw_prompt_text",
        lambda name: raw,
    )

    with pytest.raises(ValueError, match="default_difficulty"):
        load_prompt_descriptor("sample")


def test_list_prompt_descriptors_returns_all_bundled():
    descriptors = list_prompt_descriptors()

    ids = [d.id for d in descriptors]
    assert "coding_focus" in ids
    assert "behavioral_focus" in ids
    for d in descriptors:
        assert isinstance(d, PromptDescriptor)
        assert d.name  # non-empty
        assert d.content  # non-empty
