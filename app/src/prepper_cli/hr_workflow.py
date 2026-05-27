from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hr_context import HrContext, build_mock_hr_context
from .hr_fixtures import HrFixture, validate_hr_fixture
from .hr_interview_replay import replay_hr_interview_transcript
from .hr_interview_simulation import (
    SUPPORTED_HR_SIMULATION_CANDIDATES,
    simulate_hr_interview,
)

HR_WORKFLOW_SUMMARY_SCHEMA_VERSION = "hr-workflow-summary.v1"
DEFAULT_HR_WORKFLOW_MOCK_CANDIDATE = "strong"
DEFAULT_HR_WORKFLOW_OUTPUT_DIR = Path("tmp")


class HrWorkflowError(ValueError):
    """Raised when a full HR workflow run cannot complete."""


@dataclass(frozen=True)
class HrWorkflowRun:
    summary: dict[str, Any]


def run_hr_workflow(
    *,
    fixture_id: str,
    mode: str,
    candidate: str | None = None,
    out_path: str | Path | None = None,
    model: str | None = None,
    scoring_model: str | None = None,
    question_limit_override: int | None = None,
    pass_threshold_override: float | None = None,
) -> HrWorkflowRun:
    """Run the full fixture-backed HR prototype workflow."""
    if mode not in {"mock", "llm"}:
        raise HrWorkflowError("HR workflow mode must be one of: llm, mock")

    fixture = validate_hr_fixture(fixture_id)
    context = build_mock_hr_context(fixture)

    if mode == "mock":
        resolved_candidate = _resolve_mock_candidate(fixture, candidate)
        transcript_path = fixture.path / "transcripts" / f"{resolved_candidate}.md"
        interview_summary = replay_hr_interview_transcript(
            fixture_id=fixture.id,
            transcript_path=transcript_path,
            fixture=fixture,
            context=context,
        ).summary
    else:
        resolved_candidate = _resolve_llm_candidate(candidate)
        resolved_out_path = out_path or _default_llm_transcript_path(
            fixture.id,
            resolved_candidate,
        )
        interview_summary = simulate_hr_interview(
            fixture_id=fixture.id,
            candidate=resolved_candidate,
            mode="llm",
            out_path=resolved_out_path,
            model=model,
            scoring_model=scoring_model,
            question_limit_override=question_limit_override,
            pass_threshold_override=pass_threshold_override,
            context=context,
        ).summary

    return HrWorkflowRun(
        summary=_build_workflow_summary(
            fixture=fixture,
            context=context,
            mode=mode,
            candidate=resolved_candidate,
            interview_summary=interview_summary,
        )
    )


def _resolve_mock_candidate(fixture: HrFixture, candidate: str | None) -> str:
    resolved = (candidate or DEFAULT_HR_WORKFLOW_MOCK_CANDIDATE).strip().lower()
    if resolved not in fixture.transcripts:
        options = ", ".join(sorted(fixture.transcripts))
        raise HrWorkflowError(f"mock candidate must be one of: {options}")
    return resolved


def _resolve_llm_candidate(candidate: str | None) -> str:
    if candidate is None or not candidate.strip():
        options = ", ".join(sorted(SUPPORTED_HR_SIMULATION_CANDIDATES))
        raise HrWorkflowError(f"llm workflow requires --candidate ({options})")
    resolved = candidate.strip().lower()
    if resolved not in SUPPORTED_HR_SIMULATION_CANDIDATES:
        options = ", ".join(sorted(SUPPORTED_HR_SIMULATION_CANDIDATES))
        raise HrWorkflowError(f"candidate must be one of: {options}")
    return resolved


def _default_llm_transcript_path(fixture_id: str, candidate: str) -> Path:
    return DEFAULT_HR_WORKFLOW_OUTPUT_DIR / f"hr-workflow-{fixture_id}-{candidate}.md"


def _build_workflow_summary(
    *,
    fixture: HrFixture,
    context: HrContext,
    mode: str,
    candidate: str,
    interview_summary: dict[str, Any],
) -> dict[str, Any]:
    tool_calls = interview_summary.get("tool_calls", [])
    sources = interview_summary.get("sources", [])
    tool_call_count = len(tool_calls) if isinstance(tool_calls, list) else 0
    source_count = len(sources) if isinstance(sources, list) else 0
    return {
        "schema_version": HR_WORKFLOW_SUMMARY_SCHEMA_VERSION,
        "workflow": "hr_workflow",
        "mode": mode,
        "execution": "run",
        "fixture_id": fixture.id,
        "candidate": candidate,
        "context": _context_summary(context),
        "tools": {
            "context": _context_tool_summaries(context),
            "interview_call_count": tool_call_count,
        },
        "retrieval": {
            "call_count": _count_retrieval_calls(tool_calls),
            "source_count": source_count,
        },
        "interview": interview_summary,
        "transcript": interview_summary.get("transcript"),
        "models": interview_summary.get("models"),
        "tool_call_count": tool_call_count,
        "source_count": source_count,
        "final_result": interview_summary.get("final_result"),
        "interview_complete": bool(interview_summary.get("interview_complete")),
        "steps": {
            "context_build": "completed",
            "interview": interview_summary.get("execution"),
        },
    }


def _context_summary(context: HrContext) -> dict[str, Any]:
    return {
        "schema_version": context.schema_version,
        "context_id": context.context_id,
        "mode": context.mode,
        "fixture_id": context.fixture_id,
        "company_input_count": len(context.company_inputs),
        "candidate_input_count": len(context.candidate_inputs),
        "source_count": len(context.sources),
        "chunk_count": len(context.chunks),
        "tool_result_count": len(context.tool_results),
        "replay_transcript_count": len(context.replay_metadata.transcripts),
    }


def _context_tool_summaries(context: HrContext) -> list[dict[str, str]]:
    return [
        {
            "tool_name": result.tool_name,
            "status": result.status,
        }
        for result in context.tool_results
    ]


def _count_retrieval_calls(tool_calls: Any) -> int:
    if not isinstance(tool_calls, list):
        return 0

    count = 0
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        if call.get("tool_name") == "retrieve_company_context":
            count += 1
            continue
        result = call.get("result")
        if isinstance(result, dict) and result.get("tool_name") == "retrieve_company_context":
            count += 1
    return count
