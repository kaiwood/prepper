import io

from prepper_cli import benchmark
from prepper_cli import interview as interview_module
from prepper_cli.conversation import Conversation
from prepper_cli.system_prompts import PromptDescriptor


def _make_descriptor(
    id: str,
    *,
    interview_rating_enabled: bool = True,
    difficulty_enabled: bool = True,
) -> PromptDescriptor:
    return PromptDescriptor(
        id=id,
        name=id,
        temperature=0.4,
        top_p=0.95,
        frequency_penalty=0.1,
        presence_penalty=0.0,
        max_tokens=500,
        content=f"prompt::{id}",
        interview_rating_enabled=interview_rating_enabled,
        default_question_roundtrips=2,
        min_question_roundtrips=1,
        max_question_roundtrips=5,
        pass_threshold=7.0,
        rubric_criteria=("Story structure", "Communication"),
        difficulty_enabled=difficulty_enabled,
        difficulty_levels=("easy", "medium", "hard"),
        default_difficulty="medium",
        easy_pass_threshold=6.5,
        medium_pass_threshold=7.0,
        hard_pass_threshold=7.5,
    )


def test_run_benchmark_interview_uses_defaults_and_returns_summary(monkeypatch):
    interviewer = _make_descriptor("behavioral_focus")

    calls = {"run_turn": 0, "candidate_reply": 0}

    def fake_run_interview_turn(
        message: str,
        conversation: Conversation | None,
        descriptor,
        language,
        question_limit,
        pass_threshold,
        model_settings,
        difficulty,
        model=None,
        prior_question_count=None,
    ):
        calls["run_turn"] += 1
        assert descriptor.id == "behavioral_focus"
        assert language == "de"
        assert question_limit == interviewer.default_question_roundtrips
        assert pass_threshold == interviewer.medium_pass_threshold
        assert difficulty == "medium"
        assert model_settings == {
            "temperature": interviewer.temperature,
            "top_p": interviewer.top_p,
            "frequency_penalty": interviewer.frequency_penalty,
            "presence_penalty": interviewer.presence_penalty,
            "max_tokens": interviewer.max_tokens,
        }

        assert conversation is not None
        conversation.add_user_message(message)

        if calls["run_turn"] == 1:
            conversation.add_assistant_reply("Tell me about a tough team conflict you handled.")
            return {
                "reply": "Tell me about a tough team conflict you handled.",
                "turn_type": "question",
                "question_count": 1,
                "question_limit": question_limit,
                "interview_complete": False,
                "pass_threshold": pass_threshold,
                "metadata_warning": False,
                "final_result": None,
            }

        conversation.add_assistant_reply("Thank you, the interview is now over.")
        return {
            "reply": "Thank you, the interview is now over.",
            "turn_type": "other",
            "question_count": 2,
            "question_limit": question_limit,
            "interview_complete": True,
            "pass_threshold": pass_threshold,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 8.0,
                "pass_threshold": pass_threshold,
                "passed": True,
                "criterion_scores": [
                    {"criterion": "Story structure", "score": 7.8},
                    {"criterion": "Communication", "score": 8.2},
                ],
                "strengths": ["Clear examples"],
                "improvements": ["More measurable outcomes"],
                "parse_warning": False,
            },
        }

    def fake_get_chat_reply(
        message,
        conversation=None,
        history_limit=10,
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
        conversation_reply_override=None,
        model=None,
        include_diagnostics=False,
    ):
        calls["candidate_reply"] += 1
        assert "Interviewer question:" in message
        assert "candidate" in message.lower()
        assert system_prompt is not None and "You are a candidate" in system_prompt
        assert language == "de"
        assert temperature == interviewer.temperature
        assert top_p == interviewer.top_p
        assert frequency_penalty == interviewer.frequency_penalty
        assert presence_penalty == interviewer.presence_penalty
        assert max_tokens == interviewer.max_tokens
        return "I handled a production incident by coordinating rollback and communication."

    monkeypatch.setattr(benchmark, "run_interview_turn", fake_run_interview_turn)
    monkeypatch.setattr(benchmark, "get_chat_reply", fake_get_chat_reply)
    def fake_score_interviewer_performance(**kwargs):
        assert kwargs["model"] == "benchmark-model"
        return {
            "overall_score": 7.9,
            "rubric_overall_score": 7.8,
            "candidate_score_component": 8.0,
            "weights": {"interviewer_rubric": 1.0, "candidate_outcome": 0.0},
            "pass_threshold": 7.0,
            "passed": True,
            "criterion_scores": [
                {"criterion": "Question clarity", "score": 8.0},
            ],
            "strengths": ["Focused follow-ups"],
            "improvements": ["Increase challenge depth"],
            "difficulty_alignment": "aligned",
            "parse_warning": False,
        }

    monkeypatch.setattr(benchmark, "score_interviewer_performance", fake_score_interviewer_performance)

    output = io.StringIO()

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        language="de",
        model="runtime-model",
        benchmark_model="benchmark-model",
        output=output,
    )

    assert calls["run_turn"] == 2
    assert calls["candidate_reply"] == 1
    assert result["summary_json"]["mode"] == "benchmark"
    assert "candidate_system_prompt" not in result["summary_json"]
    assert "candidate_profile" not in result["summary_json"]
    assert "final_result" not in result["summary_json"]
    assert "pass_threshold" not in result["summary_json"]
    assert result["summary_json"]["difficulty"] == "medium"
    assert result["summary_json"]["question_roundtrips_limit"] == 2
    assert result["summary_json"]["models"] == {
        "runtime": "runtime-model",
        "benchmark_scoring": "benchmark-model",
    }
    assert result["summary_json"]["runtime_model"] == "runtime-model"
    assert result["summary_json"]["benchmark_model"] == "benchmark-model"
    assert result["summary_json"]["model_settings"]["temperature"] == 0.4
    assert result["summary_json"]["interviewer_result"]["passed"] is True
    assert result["conversation"][0]["role"] == "user"
    assert result["conversation"][1]["role"] == "assistant"

    rendered = output.getvalue()
    summary_index = rendered.index("## Evaluation Summary")
    details_index = rendered.index("## Evaluation Details")
    candidate_index = rendered.index("### Candidate Score")
    interviewer_index = rendered.index("### Interviewer Score")
    assert summary_index < details_index < candidate_index < interviewer_index
    assert "candidate_overall_score: 8.00" in rendered
    assert "interviewer_overall_score: 7.90" in rendered
    assert "runtime_model: runtime-model" in rendered
    assert "benchmark_model: benchmark-model" in rendered
    assert "model_settings: temperature=0.4" in rendered


def test_run_benchmark_interview_keeps_counting_after_early_close(monkeypatch):
    interviewer = _make_descriptor("behavioral_focus")
    active_replies = [
        "Question 1\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
        "Question 2\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
        "Question 3\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
        "Thanks, that concludes the interview.\n[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}",
        "Question 4\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
        "Question 5\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
    ]
    candidate_calls = {"count": 0}

    def fake_interviewer_get_chat_reply(message, **kwargs):
        system_prompt = kwargs.get("system_prompt") or ""
        if message.startswith("Score this interview transcript"):
            return (
                "{\"overall_score\":8.0,\"criterion_scores\":{\"Story structure\":8.0,"
                "\"Communication\":8.0},\"strengths\":[\"Clear\"],"
                "\"improvements\":[\"More detail\"]}"
            )

        if "Runtime override: The interview must end now" in system_prompt:
            return (
                "Thanks for your time today. The interview is now over.\n"
                "[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}"
            )

        raw_reply = active_replies.pop(0)
        active_conversation = kwargs.get("conversation")
        if active_conversation is not None:
            active_conversation.add_user_message(message)
            active_conversation.add_assistant_reply(raw_reply)
        return raw_reply

    def fake_candidate_get_chat_reply(*args, **kwargs):
        candidate_calls["count"] += 1
        return f"Candidate answer {candidate_calls['count']}"

    monkeypatch.setattr(interview_module, "get_chat_reply", fake_interviewer_get_chat_reply)
    monkeypatch.setattr(benchmark, "get_chat_reply", fake_candidate_get_chat_reply)
    monkeypatch.setattr(
        benchmark,
        "score_interviewer_performance",
        lambda **kwargs: {
            "overall_score": 8.0,
            "rubric_overall_score": 8.0,
            "candidate_score_component": 8.0,
            "weights": {"interviewer_rubric": 1.0, "candidate_outcome": 0.0},
            "pass_threshold": 7.0,
            "passed": True,
            "criterion_scores": [],
            "strengths": [],
            "improvements": [],
            "difficulty_alignment": "aligned",
            "parse_warning": False,
        },
    )

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        question_limit_override=5,
        output=io.StringIO(),
    )

    assert result["summary_json"]["counted_question_roundtrips"] == 5
    assert result["summary_json"]["question_roundtrips_limit"] == 5
    assert result["summary_json"]["interview_complete"] is True
    assert active_replies == []
    assert candidate_calls["count"] == 5
    assert all(
        "[PREPPER_JSON]" not in message["content"]
        for message in result["conversation"]
    )
    assert all(
        "concludes the interview" not in message["content"]
        for message in result["conversation"]
    )


def test_run_benchmark_interview_uses_non_repeating_fallbacks_after_repair_failure(
    monkeypatch,
):
    interviewer = _make_descriptor("coding_focus")
    active_replies = [
        "Question 1\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
        "Question 2\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
        "Thanks, that concludes the interview.\n[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}",
        "Thanks, that concludes the interview.\n[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}",
        "Thanks, that concludes the interview.\n[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}",
        "Thanks, that concludes the interview.\n[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}",
        "Question 5\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
    ]
    candidate_calls = {"count": 0}

    def fake_interviewer_get_chat_reply(message, **kwargs):
        system_prompt = kwargs.get("system_prompt") or ""
        if message.startswith("Score this interview transcript"):
            return (
                "{\"overall_score\":8.0,\"criterion_scores\":{\"Story structure\":8.0,"
                "\"Communication\":8.0},\"strengths\":[\"Clear\"],"
                "\"improvements\":[\"More detail\"]}"
            )

        if "Runtime override: The interview must end now" in system_prompt:
            return (
                "Thanks for your time today. The interview is now over.\n"
                "[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}"
            )

        raw_reply = active_replies.pop(0)
        active_conversation = kwargs.get("conversation")
        if active_conversation is not None:
            active_conversation.add_user_message(message)
            active_conversation.add_assistant_reply(raw_reply)
        return raw_reply

    def fake_candidate_get_chat_reply(*args, **kwargs):
        candidate_calls["count"] += 1
        return f"Candidate answer {candidate_calls['count']}"

    monkeypatch.setattr(interview_module, "get_chat_reply", fake_interviewer_get_chat_reply)
    monkeypatch.setattr(benchmark, "get_chat_reply", fake_candidate_get_chat_reply)
    monkeypatch.setattr(
        benchmark,
        "score_interviewer_performance",
        lambda **kwargs: {
            "overall_score": 8.0,
            "rubric_overall_score": 8.0,
            "candidate_score_component": 8.0,
            "weights": {"interviewer_rubric": 1.0, "candidate_outcome": 0.0},
            "pass_threshold": 7.0,
            "passed": True,
            "criterion_scores": [],
            "strengths": [],
            "improvements": [],
            "difficulty_alignment": "aligned",
            "parse_warning": False,
        },
    )

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        question_limit_override=5,
        output=io.StringIO(),
    )

    assistant_messages = [
        message["content"]
        for message in result["conversation"]
        if message["role"] == "assistant"
    ]
    fallback_messages = [
        message
        for message in assistant_messages
        if message.startswith("Let's make one operation precise")
        or message.startswith("Let's check correctness")
    ]

    assert result["summary_json"]["counted_question_roundtrips"] == 5
    assert result["summary_json"]["interview_complete"] is True
    assert active_replies == []
    assert candidate_calls["count"] == 5
    assert len(fallback_messages) == 2
    assert len(set(fallback_messages)) == 2
    assert all(
        "[PREPPER_JSON]" not in message["content"]
        for message in result["conversation"]
    )
    assert all(
        "concludes the interview" not in message["content"]
        for message in result["conversation"]
    )


def test_run_benchmark_interview_reports_default_model_when_model_is_omitted(
    monkeypatch,
):
    interviewer = _make_descriptor("behavioral_focus")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/default-from-env")

    def fake_run_interview_turn(
        message: str,
        conversation: Conversation | None,
        descriptor,
        language,
        question_limit,
        pass_threshold,
        model_settings,
        difficulty,
        model=None,
        prior_question_count=None,
    ):
        assert conversation is not None
        conversation.add_user_message(message)
        conversation.add_assistant_reply("Done.")
        return {
            "reply": "Done.",
            "turn_type": "other",
            "question_count": 1,
            "question_limit": question_limit,
            "interview_complete": True,
            "pass_threshold": pass_threshold,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 8.0,
                "pass_threshold": pass_threshold,
                "passed": True,
                "criterion_scores": [],
                "strengths": [],
                "improvements": [],
                "parse_warning": False,
            },
        }

    monkeypatch.setattr(benchmark, "run_interview_turn", fake_run_interview_turn)
    monkeypatch.setattr(
        benchmark,
        "score_interviewer_performance",
        lambda **kwargs: {
            "overall_score": 8.0,
            "rubric_overall_score": 8.0,
            "candidate_score_component": 8.0,
            "weights": {"interviewer_rubric": 1.0, "candidate_outcome": 0.0},
            "pass_threshold": 7.0,
            "passed": True,
            "criterion_scores": [],
            "strengths": [],
            "improvements": [],
            "difficulty_alignment": "aligned",
            "parse_warning": False,
        },
    )

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        output=io.StringIO(),
    )

    assert result["summary_json"]["models"] == {
        "runtime": "openrouter/default-from-env",
        "benchmark_scoring": "openrouter/default-from-env",
    }
    assert result["summary_json"]["runtime_model"] == "openrouter/default-from-env"
    assert result["summary_json"]["benchmark_model"] == "openrouter/default-from-env"


def test_run_benchmark_interview_rejects_invalid_difficulty():
    interviewer = _make_descriptor("coding_focus")

    try:
        benchmark.run_benchmark_interview(
            interviewer_descriptor=interviewer,
            difficulty="invalid",
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "difficulty" in str(exc)


def test_run_benchmark_interview_uses_good_candidate_profile_prompt(monkeypatch):
    interviewer = _make_descriptor("behavioral_focus")

    calls = {"candidate_reply": 0}

    def fake_run_interview_turn(
        message: str,
        conversation: Conversation | None,
        descriptor,
        language,
        question_limit,
        pass_threshold,
        model_settings,
        difficulty,
        model=None,
        prior_question_count=None,
    ):
        assert language == "en"
        assert model == "runtime-model"
        assert model_settings == {
            "temperature": interviewer.temperature,
            "top_p": interviewer.top_p,
            "frequency_penalty": interviewer.frequency_penalty,
            "presence_penalty": interviewer.presence_penalty,
            "max_tokens": interviewer.max_tokens,
        }
        assert conversation is not None
        conversation.add_user_message(message)
        if calls["candidate_reply"] == 0:
            conversation.add_assistant_reply("Describe a conflict you resolved.")
            return {
                "reply": "Describe a conflict you resolved.",
                "turn_type": "question",
                "question_count": 1,
                "question_limit": question_limit,
                "interview_complete": False,
                "pass_threshold": pass_threshold,
                "metadata_warning": False,
                "final_result": None,
            }

        conversation.add_assistant_reply("Thank you, the interview is now over.")
        return {
            "reply": "Thank you, the interview is now over.",
            "turn_type": "other",
            "question_count": 1,
            "question_limit": question_limit,
            "interview_complete": True,
            "pass_threshold": pass_threshold,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 4.0,
                "pass_threshold": pass_threshold,
                "passed": False,
                "criterion_scores": [
                    {"criterion": "Story structure", "score": 4.0},
                    {"criterion": "Communication", "score": 4.0},
                ],
                "strengths": [],
                "improvements": ["More concrete details"],
                "parse_warning": False,
            },
        }

    def fake_get_chat_reply(
        message,
        conversation=None,
        history_limit=10,
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
        conversation_reply_override=None,
        model=None,
        include_diagnostics=False,
    ):
        calls["candidate_reply"] += 1
        assert "weak candidate" in system_prompt
        assert "vague" in system_prompt
        assert language == "en"
        assert model == "runtime-model"
        return "Not sure, but I fixed some things quickly."

    monkeypatch.setattr(benchmark, "run_interview_turn", fake_run_interview_turn)
    monkeypatch.setattr(benchmark, "get_chat_reply", fake_get_chat_reply)
    monkeypatch.setattr(
        benchmark,
        "score_interviewer_performance",
        lambda **kwargs: {
            "overall_score": 4.5,
            "rubric_overall_score": 4.6,
            "candidate_score_component": 4.0,
            "weights": {"interviewer_rubric": 1.0, "candidate_outcome": 0.0},
            "pass_threshold": 7.0,
            "passed": False,
            "criterion_scores": [
                {"criterion": "Question clarity", "score": 4.5},
            ],
            "strengths": [],
            "improvements": ["Ask deeper follow-ups"],
            "difficulty_alignment": "aligned",
            "parse_warning": False,
        },
    )

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        candidate_profile="weak",
        model="runtime-model",
    )

    assert "candidate_system_prompt" not in result["summary_json"]
    assert "candidate_profile" not in result["summary_json"]
    assert result["summary_json"]["language"] == "en"
    assert result["summary_json"]["interviewer_result"]["passed"] is False


def test_run_benchmark_interview_applies_model_setting_overrides(monkeypatch):
    interviewer = _make_descriptor("behavioral_focus")

    calls = {"run_turn": 0, "candidate_reply": 0}

    def fake_run_interview_turn(
        message: str,
        conversation: Conversation | None,
        descriptor,
        language,
        question_limit,
        pass_threshold,
        model_settings,
        difficulty,
        model=None,
        prior_question_count=None,
    ):
        calls["run_turn"] += 1
        assert model_settings == {
            "temperature": 0.2,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": -0.1,
            "max_tokens": 444,
        }
        assert conversation is not None
        conversation.add_user_message(message)
        if calls["run_turn"] == 1:
            conversation.add_assistant_reply("Tell me about a tough decision you made.")
            return {
                "reply": "Tell me about a tough decision you made.",
                "turn_type": "question",
                "question_count": 1,
                "question_limit": question_limit,
                "interview_complete": False,
                "pass_threshold": pass_threshold,
                "metadata_warning": False,
                "final_result": None,
            }

        conversation.add_assistant_reply("Thanks, this interview is now complete.")
        return {
            "reply": "Thanks, this interview is now complete.",
            "turn_type": "other",
            "question_count": 1,
            "question_limit": question_limit,
            "interview_complete": True,
            "pass_threshold": pass_threshold,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 7.0,
                "pass_threshold": pass_threshold,
                "passed": True,
                "criterion_scores": [
                    {"criterion": "Story structure", "score": 7.0},
                    {"criterion": "Communication", "score": 7.0},
                ],
                "strengths": ["Clear response"],
                "improvements": ["More depth"],
                "parse_warning": False,
            },
        }

    def fake_get_chat_reply(
        message,
        conversation=None,
        history_limit=10,
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
        conversation_reply_override=None,
        model=None,
        include_diagnostics=False,
    ):
        calls["candidate_reply"] += 1
        assert temperature == 0.2
        assert top_p == 0.9
        assert frequency_penalty == 0.3
        assert presence_penalty == -0.1
        assert max_tokens == 444
        return "I balanced tradeoffs and picked the least risky option."

    monkeypatch.setattr(benchmark, "run_interview_turn", fake_run_interview_turn)
    monkeypatch.setattr(benchmark, "get_chat_reply", fake_get_chat_reply)
    monkeypatch.setattr(
        benchmark,
        "score_interviewer_performance",
        lambda **kwargs: {
            "overall_score": 7.0,
            "rubric_overall_score": 7.0,
            "candidate_score_component": 7.0,
            "weights": {"interviewer_rubric": 1.0, "candidate_outcome": 0.0},
            "pass_threshold": 7.0,
            "passed": True,
            "criterion_scores": [{"criterion": "Question clarity", "score": 7.0}],
            "strengths": ["Clear questioning"],
            "improvements": ["Deeper follow-up"],
            "difficulty_alignment": "aligned",
            "parse_warning": False,
        },
    )

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        temperature_override=0.2,
        top_p_override=0.9,
        frequency_penalty_override=0.3,
        presence_penalty_override=-0.1,
        max_tokens_override=444,
    )

    assert calls["run_turn"] == 2
    assert calls["candidate_reply"] == 1
    assert result["summary_json"]["mode"] == "benchmark"


def test_run_benchmark_interview_rejects_invalid_candidate_profile():
    interviewer = _make_descriptor("behavioral_focus")

    try:
        benchmark.run_benchmark_interview(
            interviewer_descriptor=interviewer,
            candidate_profile="unknown",
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "candidate_profile" in str(exc)
