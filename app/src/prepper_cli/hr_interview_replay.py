from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hr_context import build_mock_hr_context
from .hr_fixtures import (
    ExpectedFinalResult,
    HrFixture,
    Transcript,
    TranscriptSource,
    TranscriptToolEvent,
    parse_transcript_file,
    validate_hr_fixture,
)
from .hr_tools import (
    RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
    hr_tool_result_to_dict,
    run_retrieve_company_context_tool,
)

HR_INTERVIEW_SUMMARY_SCHEMA_VERSION = "hr-interview-summary.v1"


class HrInterviewReplayError(ValueError):
    """Raised when an HR interview transcript cannot be replayed safely."""


@dataclass(frozen=True)
class HrInterviewReplay:
    summary: dict[str, Any]


def replay_hr_interview_transcript(
    *,
    fixture_id: str,
    transcript_path: str | Path,
) -> HrInterviewReplay:
    """Replay a stored HR interview transcript through deterministic mock tooling."""
    fixture = validate_hr_fixture(fixture_id)
    transcript = parse_transcript_file(transcript_path)
    _validate_transcript_metadata(fixture, transcript, transcript_path)

    context = build_mock_hr_context(fixture)
    tool_results = []
    retrieved_source_urls: set[str] = set()

    for event in transcript.tool_events:
        result = _replay_tool_event(event, context=context)
        result_payload = hr_tool_result_to_dict(result)
        tool_results.append(
            {
                "declared": _tool_event_to_dict(event),
                "result": result_payload,
            }
        )
        retrieved_source_urls.update(_source_urls_from_tool_result(result_payload))

    _validate_declared_sources(transcript.sources, retrieved_source_urls)

    return HrInterviewReplay(
        summary={
            "schema_version": HR_INTERVIEW_SUMMARY_SCHEMA_VERSION,
            "workflow": "hr_interview",
            "mode": "mock",
            "execution": "replay",
            "fixture_id": fixture.id,
            "candidate": transcript.candidate,
            "context_id": context.context_id,
            "transcript": {
                "path": str(transcript_path),
                "metadata": dict(transcript.metadata),
                "turn_count": len(transcript.turns),
                "tool_event_count": len(transcript.tool_events),
                "source_count": len(transcript.sources),
            },
            "models": {
                "runtime": None,
                "scoring": None,
                "embeddings": "mock",
            },
            "turn_counts": {
                "total": len(transcript.turns),
                "interviewer": sum(1 for turn in transcript.turns if turn.role == "interviewer"),
                "candidate": sum(1 for turn in transcript.turns if turn.role == "candidate"),
                "tool_events": len(transcript.tool_events),
                "sources": len(transcript.sources),
            },
            "tool_calls": tool_results,
            "sources": [_source_to_dict(source) for source in transcript.sources],
            "final_result": _expected_final_result_to_dict(
                transcript.expected_final_result
            ),
            "interview_complete": True,
            "validation": {
                "turn_order": "passed",
                "tool_events": "matched",
                "sources": "matched",
                "expected_final_result": "present",
            },
        }
    )


def _validate_transcript_metadata(
    fixture: HrFixture,
    transcript: Transcript,
    transcript_path: str | Path,
) -> None:
    if transcript.fixture_id != fixture.id:
        raise HrInterviewReplayError(
            f"Transcript '{transcript_path}' declares fixture '{transcript.fixture_id}', expected '{fixture.id}'"
        )
    if not transcript.candidate.strip():
        raise HrInterviewReplayError(f"Transcript '{transcript_path}' is missing candidate metadata")


def _replay_tool_event(event: TranscriptToolEvent, *, context):
    if event.tool_name != RETRIEVE_COMPANY_CONTEXT_TOOL_NAME:
        raise HrInterviewReplayError(
            f"Unsupported replay tool '{event.tool_name}'. Supported: {RETRIEVE_COMPANY_CONTEXT_TOOL_NAME}"
        )

    query = event.data.get("query", "").strip()
    if not query:
        raise HrInterviewReplayError(
            f"Tool event '{event.tool_name}' must include a non-empty query"
        )

    try:
        return run_retrieve_company_context_tool(
            context=context,
            query=query,
            mode="mock",
        )
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        raise HrInterviewReplayError(
            f"Replay tool '{event.tool_name}' failed: {exc}"
        ) from exc


def _validate_declared_sources(
    declared_sources: tuple[TranscriptSource, ...],
    retrieved_source_urls: set[str],
) -> None:
    for source in declared_sources:
        if source.url not in retrieved_source_urls:
            available = ", ".join(sorted(retrieved_source_urls)) or "none"
            raise HrInterviewReplayError(
                f"Transcript source '{source.url}' was not returned by mock retrieval. Available: {available}"
            )


def _source_urls_from_tool_result(result_payload: dict[str, Any]) -> set[str]:
    output = result_payload.get("output")
    if not isinstance(output, dict):
        return set()
    snippets = output.get("snippets")
    if not isinstance(snippets, list):
        return set()

    urls = set()
    for snippet in snippets:
        if not isinstance(snippet, dict):
            continue
        source_uri = snippet.get("source_uri")
        if isinstance(source_uri, str) and source_uri.strip():
            urls.add(source_uri.strip())
    return urls


def _tool_event_to_dict(event: TranscriptToolEvent) -> dict[str, Any]:
    return {
        "tool_name": event.tool_name,
        "data": dict(event.data),
    }


def _source_to_dict(source: TranscriptSource) -> dict[str, str]:
    return {
        "title": source.title,
        "url": source.url,
        "excerpt": source.excerpt,
    }


def _expected_final_result_to_dict(result: ExpectedFinalResult) -> dict[str, Any]:
    return {
        "overall_score": result.overall_score,
        "passed": result.passed,
        "strengths": list(result.strengths),
        "improvements": list(result.improvements),
    }
