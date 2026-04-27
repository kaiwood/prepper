from prepper_cli import benchmark
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
            "weights": {"interviewer_rubric": 0.8, "candidate_outcome": 0.2},
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

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        language="de",
        model="runtime-model",
        benchmark_model="benchmark-model",
    )

    assert calls["run_turn"] == 2
    assert calls["candidate_reply"] == 1
    assert result["summary_json"]["mode"] == "benchmark"
    assert result["summary_json"]["candidate_system_prompt"] == "benchmark_candidate_strong"
    assert result["summary_json"]["difficulty"] == "medium"
    assert result["summary_json"]["question_roundtrips_limit"] == 2
    assert result["summary_json"]["final_result"]["passed"] is True
    assert result["summary_json"]["interviewer_result"]["passed"] is True
    assert result["conversation"][0]["role"] == "user"
    assert result["conversation"][1]["role"] == "assistant"


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
            "weights": {"interviewer_rubric": 0.8, "candidate_outcome": 0.2},
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

    assert result["summary_json"]["candidate_system_prompt"] == "benchmark_candidate_weak"
    assert result["summary_json"]["language"] == "en"
    assert result["summary_json"]["final_result"]["passed"] is False
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
            "weights": {"interviewer_rubric": 0.8, "candidate_outcome": 0.2},
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
