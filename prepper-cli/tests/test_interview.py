from prepper_cli.conversation import Conversation
from prepper_cli.interview import (
    count_scored_questions,
    parse_reply_metadata,
    run_interview_turn,
)
from prepper_cli.system_prompts import PromptDescriptor


def _descriptor(**overrides) -> PromptDescriptor:
    defaults = {
        "id": "coding_focus",
        "name": "Coding Interview",
        "temperature": 0.3,
        "top_p": 1.0,
        "frequency_penalty": 0.2,
        "presence_penalty": 0.0,
        "max_tokens": 700,
        "content": "You are an interviewer.",
        "interview_rating_enabled": True,
        "default_question_roundtrips": 2,
        "min_question_roundtrips": 1,
        "max_question_roundtrips": 5,
        "pass_threshold": 7.0,
        "rubric_criteria": ("Problem understanding", "Communication"),
    }
    defaults.update(overrides)
    return PromptDescriptor(**defaults)


def test_parse_reply_metadata_extracts_suffix_json():
    parsed = parse_reply_metadata(
        "Question text\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
    )

    assert parsed["reply"] == "Question text"
    assert parsed["metadata"]["turn_type"] == "QUESTION"
    assert parsed["metadata"]["interview_complete"] is False
    assert parsed["metadata_valid"] is True


def test_count_scored_questions_uses_metadata_without_classifier(monkeypatch):
    conversation = Conversation.from_messages(
        [
            {
                "role": "assistant",
                "content": "Q1\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
            },
            {
                "role": "assistant",
                "content": "Thanks\n[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":false}",
            },
        ]
    )

    monkeypatch.setattr(
        "prepper_cli.interview.classify_assistant_turn",
        lambda *_: (_ for _ in ()).throw(AssertionError("classifier should not be called")),
    )

    assert count_scored_questions(conversation, None) == 1


def test_count_scored_questions_fallback_handles_non_question_mark(monkeypatch):
    conversation = Conversation.from_messages(
        [
            {"role": "assistant", "content": "Walk me through your approach:"},
        ]
    )

    monkeypatch.setattr(
        "prepper_cli.interview.get_chat_reply",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("classifier unavailable")),
    )

    assert count_scored_questions(conversation, None) == 1


def test_run_interview_turn_strips_metadata_and_includes_final_result(monkeypatch):
    descriptor = _descriptor(default_question_roundtrips=1)
    conversation = Conversation.from_messages([])

    def fake_get_chat_reply(*args, **kwargs):
        message = args[0]
        if "Score this interview transcript" in message:
            return (
                "{\"overall_score\":8.0,\"criterion_scores\":{\"Problem understanding\":8.0,"
                "\"Communication\":7.5},\"strengths\":[\"Structured\"],"
                "\"improvements\":[\"More depth\"]}"
            )

        active_conversation = kwargs.get("conversation")
        if active_conversation is not None:
            active_conversation.add_user_message(message)
            active_conversation.add_assistant_reply(
                "Thanks for your answers. The interview is now over.\n"
                "[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}"
            )

        return (
            "Thanks for your answers. The interview is now over.\n"
            "[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}"
        )

    monkeypatch.setattr(
        "prepper_cli.interview.get_chat_reply",
        fake_get_chat_reply,
    )

    result = run_interview_turn(
        message="Here is my answer",
        conversation=conversation,
        descriptor=descriptor,
        language=None,
        question_limit=1,
        pass_threshold=7.0,
        model_settings={
            "temperature": 0.3,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "max_tokens": 300,
        },
    )

    assert result["reply"].startswith("Thanks for your answers")
    assert result["interview_complete"] is True
    assert result["final_result"] is not None
    assert result["final_result"]["passed"] is True

    messages = conversation.get_messages()
    assert messages[-1]["role"] == "assistant"
    assert "[PREPPER_JSON]" not in messages[-1]["content"]
