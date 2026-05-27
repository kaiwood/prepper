import json
from pathlib import Path

import pytest

from prepper_cli.hr_context import HrToolResult
from prepper_cli.hr_fixtures import parse_transcript_file
from prepper_cli import hr_interview_simulation as simulation


class _FakeChatModel:
    def __init__(self, responses):
        self.responses = responses
        self.messages = []

    def invoke(self, messages):
        self.messages.append(messages)
        if not self.responses:
            raise AssertionError("unexpected LLM call")
        return type("FakeResponse", (), {"content": self.responses.pop(0)})()


def test_simulate_hr_interview_writes_parseable_transcript_and_summary(monkeypatch, tmp_path):
    fake_chat = _FakeChatModel(
        [
            "What specifically interests you about Northstar and this role?\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}",
            "I am drawn to the privacy-first people analytics work and can connect it to my dashboard experience.",
            "Thank you for your time today. The interview is now over.\n[PREPPER_JSON] {\"turn_type\":\"OTHER\",\"interview_complete\":true}",
            json.dumps(
                {
                    "overall_score": 8.2,
                    "criterion_scores": {
                        "Role fit": 8,
                        "Evidence quality": 8,
                        "Communication": 9,
                        "Company interest": 8,
                    },
                    "strengths": ["Specific company interest"],
                    "improvements": ["Add more metrics"],
                }
            ),
        ]
    )
    retrieval_queries = []

    def fake_build_chat_model(**kwargs):
        assert kwargs["model"] == "runtime-model" or kwargs["model"] == "scoring-model"
        return fake_chat

    def fake_retrieve_tool(*, context, query, mode, limit=3):
        assert mode == "llm"
        retrieval_queries.append(query)
        return HrToolResult(
            tool_name="retrieve_company_context",
            status="success",
            output={
                "mode": "llm",
                "query": query,
                "result_count": 1,
                "snippets": [
                    {
                        "chunk_id": "company_chunk_001",
                        "source_id": "company",
                        "source_title": "Northstar Analytics Company Overview",
                        "source_uri": "fixture://company.md",
                        "text": "Northstar values evidence-led decisions and privacy-first handling of people data.",
                        "metadata": {"source_uri": "fixture://company.md"},
                    }
                ],
            },
        )

    monkeypatch.setattr(simulation, "_build_langchain_chat_model", fake_build_chat_model)
    monkeypatch.setattr(simulation, "run_retrieve_company_context_tool", fake_retrieve_tool)
    monkeypatch.setattr(simulation, "_resolve_embedding_model_label", lambda: None)

    out_path = tmp_path / "hr-strong-run.md"
    result = simulation.simulate_hr_interview(
        fixture_id="demo_hr",
        candidate="strong",
        mode="llm",
        out_path=out_path,
        model="runtime-model",
        scoring_model="scoring-model",
        question_limit_override=1,
    )

    assert len(retrieval_queries) == 2
    assert result.summary["execution"] == "simulate"
    assert result.summary["mode"] == "llm"
    assert result.summary["candidate"] == "strong"
    assert result.summary["models"] == {
        "runtime": "runtime-model",
        "scoring": "scoring-model",
        "embeddings": None,
    }
    assert result.summary["final_result"]["overall_score"] == pytest.approx(8.2)
    assert result.summary["tool_calls"][0]["result"]["tool_name"] == "retrieve_company_context"
    assert result.summary["transcript"]["path"] == str(out_path)
    assert out_path.exists()

    transcript = parse_transcript_file(out_path)
    assert transcript.fixture_id == "demo_hr"
    assert transcript.candidate == "strong"
    assert transcript.expected_final_result.overall_score == pytest.approx(8.2)
    assert transcript.sources[0].url == "fixture://company.md"


def test_simulate_hr_interview_rejects_non_llm_mode(tmp_path):
    with pytest.raises(simulation.HrInterviewSimulationError, match="only llm mode"):
        simulation.simulate_hr_interview(
            fixture_id="demo_hr",
            candidate="strong",
            mode="mock",
            out_path=tmp_path / "run.md",
        )


def test_simulate_hr_interview_rejects_unknown_candidate(tmp_path):
    with pytest.raises(simulation.HrInterviewSimulationError, match="candidate must be"):
        simulation.simulate_hr_interview(
            fixture_id="demo_hr",
            candidate="average",
            mode="llm",
            out_path=tmp_path / "run.md",
        )
