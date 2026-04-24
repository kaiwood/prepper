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
    candidate = _make_descriptor("interview_coach", difficulty_enabled=False)

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
    ):
        calls["run_turn"] += 1
        assert descriptor.id == "behavioral_focus"
        assert language == "de"
        assert question_limit == interviewer.default_question_roundtrips
        assert pass_threshold == interviewer.medium_pass_threshold
        assert difficulty == "medium"

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
        include_diagnostics=False,
    ):
        calls["candidate_reply"] += 1
        assert "Interviewer question:" in message
        assert "candidate" in message.lower()
        assert system_prompt is not None and "You are the candidate" in system_prompt
        assert language == "de"
        assert temperature == candidate.temperature
        assert top_p == candidate.top_p
        assert frequency_penalty == candidate.frequency_penalty
        assert presence_penalty == candidate.presence_penalty
        assert max_tokens == candidate.max_tokens
        return "I handled a production incident by coordinating rollback and communication."

    monkeypatch.setattr(benchmark, "run_interview_turn", fake_run_interview_turn)
    monkeypatch.setattr(benchmark, "get_chat_reply", fake_get_chat_reply)

    result = benchmark.run_benchmark_interview(
        interviewer_descriptor=interviewer,
        candidate_descriptor=candidate,
        language="de",
    )

    assert calls["run_turn"] == 2
    assert calls["candidate_reply"] == 1
    assert result["summary_json"]["mode"] == "benchmark"
    assert result["summary_json"]["difficulty"] == "medium"
    assert result["summary_json"]["question_roundtrips_limit"] == 2
    assert result["summary_json"]["final_result"]["passed"] is True
    assert result["conversation"][0]["role"] == "user"
    assert result["conversation"][1]["role"] == "assistant"


def test_run_benchmark_interview_rejects_invalid_difficulty():
    interviewer = _make_descriptor("coding_focus")
    candidate = _make_descriptor("interview_coach", difficulty_enabled=False)

    try:
        benchmark.run_benchmark_interview(
            interviewer_descriptor=interviewer,
            candidate_descriptor=candidate,
            difficulty="invalid",
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "difficulty" in str(exc)
