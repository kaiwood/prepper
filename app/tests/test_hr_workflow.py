from pathlib import Path
from types import SimpleNamespace

import pytest

from prepper_cli import hr_workflow
from prepper_cli.hr_workflow import (
    HR_WORKFLOW_SUMMARY_SCHEMA_VERSION,
    HrWorkflowError,
    run_hr_workflow,
)


def test_run_hr_workflow_mock_defaults_to_strong_replay():
    result = run_hr_workflow(fixture_id="demo_hr", mode="mock")

    summary = result.summary
    assert summary["schema_version"] == HR_WORKFLOW_SUMMARY_SCHEMA_VERSION
    assert summary["workflow"] == "hr_workflow"
    assert summary["mode"] == "mock"
    assert summary["execution"] == "run"
    assert summary["fixture_id"] == "demo_hr"
    assert summary["candidate"] == "strong"
    assert summary["context"]["context_id"].startswith("hrctx_demo_hr_")
    assert summary["context"]["source_count"] == 6
    assert summary["context"]["chunk_count"] == 8
    assert summary["context"]["tool_result_count"] == 1
    assert summary["tools"] == {
        "context": [{"tool_name": "extract_candidate_profile", "status": "success"}],
        "interview_call_count": 1,
    }
    assert summary["retrieval"] == {"call_count": 1, "source_count": 1}
    assert summary["interview"]["execution"] == "replay"
    assert summary["interview"]["candidate"] == "strong"
    assert summary["final_result"]["overall_score"] == pytest.approx(8.4)
    assert summary["interview_complete"] is True
    assert summary["steps"] == {
        "context_build": "completed",
        "interview": "replay",
    }


def test_run_hr_workflow_mock_supports_weak_candidate():
    result = run_hr_workflow(fixture_id="demo_hr", mode="mock", candidate="weak")

    assert result.summary["candidate"] == "weak"
    assert result.summary["interview"]["candidate"] == "weak"
    assert result.summary["final_result"]["passed"] is False


def test_run_hr_workflow_llm_delegates_to_simulation_with_auto_path(monkeypatch):
    calls = []

    def fake_simulate_hr_interview(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            summary={
                "schema_version": "hr-interview-summary.v1",
                "workflow": "hr_interview",
                "mode": "llm",
                "execution": "simulate",
                "fixture_id": "demo_hr",
                "candidate": "strong",
                "context_id": kwargs["context"].context_id,
                "transcript": {
                    "path": str(kwargs["out_path"]),
                    "turn_count": 3,
                    "tool_event_count": 2,
                    "source_count": 1,
                },
                "models": {
                    "runtime": "runtime-model",
                    "scoring": "scoring-model",
                    "embeddings": "embedding-model",
                },
                "turn_counts": {
                    "total": 3,
                    "interviewer": 2,
                    "candidate": 1,
                    "tool_events": 2,
                    "sources": 1,
                },
                "tool_calls": [{"tool_name": "retrieve_company_context"}],
                "sources": [{"title": "Company", "url": "fixture://company.md", "excerpt": "Values"}],
                "final_result": {
                    "overall_score": 8.2,
                    "passed": True,
                    "strengths": [],
                    "improvements": [],
                },
                "interview_complete": True,
            }
        )

    monkeypatch.setattr(hr_workflow, "simulate_hr_interview", fake_simulate_hr_interview)

    result = run_hr_workflow(
        fixture_id="demo_hr",
        mode="llm",
        candidate="strong",
        model="runtime-model",
        scoring_model="scoring-model",
        question_limit_override=1,
        pass_threshold_override=7.5,
    )

    assert calls[0]["fixture_id"] == "demo_hr"
    assert calls[0]["candidate"] == "strong"
    assert calls[0]["mode"] == "llm"
    assert calls[0]["out_path"] == Path("tmp/hr-workflow-demo_hr-strong.md")
    assert calls[0]["model"] == "runtime-model"
    assert calls[0]["scoring_model"] == "scoring-model"
    assert calls[0]["question_limit_override"] == 1
    assert calls[0]["pass_threshold_override"] == 7.5
    assert calls[0]["context"].context_id.startswith("hrctx_demo_hr_")
    assert result.summary["schema_version"] == "hr-workflow-summary.v1"
    assert result.summary["interview"]["execution"] == "simulate"
    assert result.summary["transcript"]["path"] == "tmp/hr-workflow-demo_hr-strong.md"
    assert result.summary["retrieval"] == {"call_count": 1, "source_count": 1}
    assert result.summary["tool_call_count"] == 1
    assert result.summary["source_count"] == 1


def test_run_hr_workflow_llm_accepts_out_path(monkeypatch, tmp_path):
    out_path = tmp_path / "custom.md"

    def fake_simulate_hr_interview(**kwargs):
        return SimpleNamespace(
            summary={
                "execution": "simulate",
                "transcript": {"path": str(kwargs["out_path"])},
                "models": {},
                "tool_calls": [],
                "sources": [],
                "final_result": {"overall_score": 7.0, "passed": True},
                "interview_complete": True,
            }
        )

    monkeypatch.setattr(hr_workflow, "simulate_hr_interview", fake_simulate_hr_interview)

    result = run_hr_workflow(
        fixture_id="demo_hr",
        mode="llm",
        candidate="weak",
        out_path=out_path,
    )

    assert result.summary["candidate"] == "weak"
    assert result.summary["transcript"]["path"] == str(out_path)


def test_run_hr_workflow_llm_requires_candidate():
    with pytest.raises(HrWorkflowError, match="requires --candidate"):
        run_hr_workflow(fixture_id="demo_hr", mode="llm")
