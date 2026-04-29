from prepper_cli.conversation import Conversation
from prepper_cli.interview import (
    build_active_interview_system_prompt,
    build_forced_closing_system_prompt,
    build_interviewer_scoring_system_prompt,
    build_interview_opener_system_prompt,
    count_scored_questions,
    parse_interviewer_scoring_payload,
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


def test_build_interview_opener_system_prompt_includes_base_and_difficulty():
    descriptor = _descriptor(content="Base interviewer prompt.")

    prompt = build_interview_opener_system_prompt(descriptor, "hard")

    assert "Base interviewer prompt." in prompt
    assert "Difficulty mode: Principal-level (hard)." in prompt
    assert "Response format requirement" not in prompt
    assert "Runtime rule:" not in prompt


def test_build_active_interview_system_prompt_includes_runtime_sections():
    descriptor = _descriptor(content="Base interviewer prompt.")

    prompt = build_active_interview_system_prompt(
        descriptor=descriptor,
        difficulty="medium",
        question_count=1,
        question_limit=3,
    )

    assert "Base interviewer prompt." in prompt
    assert "Response format requirement" in prompt
    assert "[PREPPER_JSON]" in prompt
    assert "Difficulty mode: Senior-level (medium)." in prompt
    assert "Scored interview questions asked so far: 1/3." in prompt
    assert "Remaining scored questions: 2." in prompt


def test_build_forced_closing_system_prompt_includes_closing_override():
    descriptor = _descriptor(content="Base interviewer prompt.")

    prompt = build_forced_closing_system_prompt(
        descriptor=descriptor,
        difficulty="easy",
        question_count=3,
        question_limit=3,
    )

    assert "Base interviewer prompt." in prompt
    assert "Response format requirement" in prompt
    assert "Difficulty mode: Junior-level (easy)." in prompt
    assert "Runtime override: The interview must end now" in prompt
    assert "roundtrip limit has been reached (3/3)." in prompt
    assert "turn_type OTHER and interview_complete true" in prompt


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


def test_run_interview_turn_returns_debug_diagnostics_when_enabled(monkeypatch):
    descriptor = _descriptor(default_question_roundtrips=2)
    conversation = Conversation.from_messages([])

    def fake_get_chat_reply(*args, **kwargs):
        if kwargs.get("include_diagnostics"):
            return (
                "First question\n"
                "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
                {
                    "request": {"model": "mock-model"},
                    "raw_response": {"id": "resp-1"},
                    "raw_reply": "First question\\n[PREPPER_JSON] {...}",
                    "normalized_reply": "First question\\n[PREPPER_JSON] {...}",
                },
            )

        return (
            "First question\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        )

    monkeypatch.setattr("prepper_cli.interview.get_chat_reply", fake_get_chat_reply)

    result = run_interview_turn(
        message="Here is my answer",
        conversation=conversation,
        descriptor=descriptor,
        language=None,
        question_limit=2,
        pass_threshold=7.0,
        model_settings={
            "temperature": 0.3,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "max_tokens": 300,
        },
        include_diagnostics=True,
    )

    assert result["turn_type"] == "question"
    assert result["interview_complete"] is False
    assert "debug" in result
    assert "turn_chat" in result["debug"]
    assert "raw_turn_reply" in result["debug"]


def test_run_interview_turn_preserves_final_question_before_closing(
    monkeypatch,
):
    descriptor = _descriptor(default_question_roundtrips=1)
    conversation = Conversation.from_messages([])
    calls = {"count": 0}

    def fake_get_chat_reply(*args, **kwargs):
        message = args[0]
        calls["count"] += 1

        if "Score this interview transcript" in message:
            return (
                "{\"overall_score\":8.2,\"criterion_scores\":{\"Problem understanding\":8.0,"
                "\"Communication\":8.4},\"strengths\":[\"Clear reasoning\"],"
                "\"improvements\":[\"More edge cases\"]}"
            )

        if calls["count"] == 1:
            active_conversation = kwargs.get("conversation")
            if active_conversation is not None:
                active_conversation.add_user_message(message)
                active_conversation.add_assistant_reply(
                    "Can you explain your approach in more detail?\n"
                    "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
                )
            return (
                "Can you explain your approach in more detail?\n"
                "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
            )

        assert kwargs.get("conversation") is None
        return (
            "Thanks for your time today. The interview is now over.\n"
            "[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}"
        )

    monkeypatch.setattr("prepper_cli.interview.get_chat_reply", fake_get_chat_reply)
    monkeypatch.setattr(
        "prepper_cli.interview.classify_assistant_turn",
        lambda *_: "question",
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

    assert result["interview_complete"] is False
    assert result["turn_type"] == "question"
    assert result["reply"].startswith("Can you explain your approach")
    assert result["question_count"] == 1
    assert result["metadata_warning"] is False

    messages = conversation.get_messages()
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"].startswith("Can you explain your approach")
    assert "[PREPPER_JSON]" not in messages[-1]["content"]

    closing_result = run_interview_turn(
        message="My answer to that final question",
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

    assert closing_result["interview_complete"] is True
    assert closing_result["turn_type"] == "other"
    assert closing_result["reply"].startswith("Thanks for your time today")


def test_run_interview_turn_uses_fallback_goodbye_when_post_limit_close_metadata_invalid(
    monkeypatch,
):
    descriptor = _descriptor(default_question_roundtrips=1)
    conversation = Conversation.from_messages([])
    calls = {"count": 0}

    def fake_get_chat_reply(*args, **kwargs):
        message = args[0]
        calls["count"] += 1

        if "Score this interview transcript" in message:
            return (
                "{\"overall_score\":7.0,\"criterion_scores\":{\"Problem understanding\":7.0,"
                "\"Communication\":7.0},\"strengths\":[\"Structured\"],"
                "\"improvements\":[\"Depth\"]}"
            )

        if calls["count"] == 1:
            active_conversation = kwargs.get("conversation")
            if active_conversation is not None:
                active_conversation.add_user_message(message)
                active_conversation.add_assistant_reply(
                    "Follow-up question\n"
                    "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
                )
            return (
                "Follow-up question\n"
                "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
            )

        assert kwargs.get("conversation") is None
        return "Closing without metadata"

    monkeypatch.setattr("prepper_cli.interview.get_chat_reply", fake_get_chat_reply)
    monkeypatch.setattr(
        "prepper_cli.interview.classify_assistant_turn",
        lambda *_: "question",
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

    assert result["interview_complete"] is False
    assert result["turn_type"] == "question"
    assert result["reply"] == "Follow-up question"
    assert result["metadata_warning"] is False

    result_after_final_answer = run_interview_turn(
        message="Final answer",
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

    assert result_after_final_answer["interview_complete"] is True
    assert result_after_final_answer["turn_type"] == "other"
    assert result_after_final_answer["reply"] == "Thank you for your time today. The interview is now over."
    assert result_after_final_answer["metadata_warning"] is True

    messages = conversation.get_messages()
    assert messages[-1]["content"] == "Thank you for your time today. The interview is now over."
    assert "[PREPPER_JSON]" not in messages[-1]["content"]


def test_parse_interviewer_scoring_payload_uses_weighted_formula():
    descriptor = _descriptor()
    raw_payload = (
        "{"
        '"interviewer_overall_score":8.5,'
        '"criterion_scores":{'
        '"Question clarity":8.0,'
        '"Follow-up depth":9.0,'
        '"Behavior realism":8.0,'
        '"Candidate challenge level":8.0,'
        '"Adaptation to candidate responses":9.0,'
        '"Difficulty calibration":9.0'
        "},"
        '"strengths":["Clear prompts"],'
        '"improvements":["Probe edge cases"],'
        '"difficulty_alignment":"aligned"'
        "}"
    )

    parsed = parse_interviewer_scoring_payload(
        raw_payload,
        descriptor=descriptor,
        interviewer_pass_threshold=7.0,
        candidate_overall_score=6.0,
    )

    assert parsed["rubric_overall_score"] == 8.5
    assert parsed["candidate_score_component"] == 6.0
    assert parsed["overall_score"] == 8.0
    assert parsed["passed"] is True
    assert parsed["difficulty_alignment"] == "aligned"
    assert len(parsed["criterion_scores"]) == 6


def test_build_interviewer_scoring_system_prompt_mentions_difficulty_and_json_contract():
    descriptor = _descriptor()
    prompt = build_interviewer_scoring_system_prompt(descriptor, "hard")

    assert "Configured difficulty baseline: hard" in prompt
    assert "interviewer_overall_score" in prompt
    assert "difficulty_alignment" in prompt
