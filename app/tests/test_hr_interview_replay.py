from pathlib import Path

import pytest

from prepper_cli.hr_fixtures import FixtureValidationError
from prepper_cli.hr_interview_replay import (
    HR_INTERVIEW_SUMMARY_SCHEMA_VERSION,
    HrInterviewReplayError,
    replay_hr_interview_transcript,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "hr" / "demo_hr"


def test_replay_hr_interview_transcript_returns_canonical_summary():
    replay = replay_hr_interview_transcript(
        fixture_id="demo_hr",
        transcript_path=FIXTURE_ROOT / "transcripts" / "strong.md",
    )

    summary = replay.summary
    assert summary["schema_version"] == HR_INTERVIEW_SUMMARY_SCHEMA_VERSION
    assert summary["workflow"] == "hr_interview"
    assert summary["mode"] == "mock"
    assert summary["execution"] == "replay"
    assert summary["fixture_id"] == "demo_hr"
    assert summary["candidate"] == "strong"
    assert summary["context_id"].startswith("hrctx_demo_hr_")
    assert summary["turn_counts"] == {
        "total": 4,
        "interviewer": 2,
        "candidate": 2,
        "tool_events": 1,
        "sources": 1,
    }
    assert summary["models"] == {
        "runtime": None,
        "scoring": None,
        "embeddings": "mock",
    }
    assert summary["tool_calls"][0]["declared"]["tool_name"] == "retrieve_company_context"
    assert summary["tool_calls"][0]["result"]["output"]["result_count"] == 2
    assert summary["sources"] == [
        {
            "title": "Northstar Analytics Company Overview",
            "url": "fixture://company.md",
            "excerpt": "Northstar Analytics values evidence-led decisions, customer empathy, privacy-first handling of employee and candidate data, and practical automation that keeps humans accountable.",
        }
    ]
    assert summary["final_result"]["overall_score"] == pytest.approx(8.4)
    assert summary["final_result"]["passed"] is True
    assert summary["interview_complete"] is True
    assert summary["validation"] == {
        "turn_order": "passed",
        "tool_events": "matched",
        "sources": "matched",
        "expected_final_result": "present",
    }


def test_replay_hr_interview_transcript_supports_weak_fixture():
    replay = replay_hr_interview_transcript(
        fixture_id="demo_hr",
        transcript_path=FIXTURE_ROOT / "transcripts" / "weak.md",
    )

    assert replay.summary["candidate"] == "weak"
    assert replay.summary["final_result"]["passed"] is False
    assert replay.summary["tool_calls"][0]["result"]["output"]["result_count"] == 2


def test_replay_rejects_malformed_transcript(tmp_path: Path):
    transcript_path = tmp_path / "bad.md"
    transcript_path.write_text(
        "---\nfixture: demo_hr\ncandidate: strong\n---\n\n## Candidate\n\nAnswer",
        encoding="utf-8",
    )

    with pytest.raises(FixtureValidationError, match="first turn"):
        replay_hr_interview_transcript(
            fixture_id="demo_hr",
            transcript_path=transcript_path,
        )


def test_replay_rejects_missing_expected_final_result(tmp_path: Path):
    transcript_path = tmp_path / "missing-result.md"
    transcript_path.write_text(
        "---\n"
        "fixture: demo_hr\n"
        "candidate: strong\n"
        "---\n\n"
        "## Interviewer\n\nQuestion?\n\n"
        "## Candidate\n\nAnswer.\n\n"
        "## Tool Event\n\n"
        "tool: retrieve_company_context\n"
        "query: company values\n\n"
        "## Source\n\n"
        "title: Northstar Analytics Company Overview\n"
        "url: fixture://company.md\n"
        "excerpt: Values\n",
        encoding="utf-8",
    )

    with pytest.raises(FixtureValidationError, match="Expected Final Result"):
        replay_hr_interview_transcript(
            fixture_id="demo_hr",
            transcript_path=transcript_path,
        )


def test_replay_rejects_tool_mismatch(tmp_path: Path):
    transcript_path = _write_valid_transcript(
        tmp_path,
        tool_name="fetch_company_website",
        source_url="fixture://company.md",
    )

    with pytest.raises(HrInterviewReplayError, match="Unsupported replay tool"):
        replay_hr_interview_transcript(
            fixture_id="demo_hr",
            transcript_path=transcript_path,
        )


def test_replay_rejects_source_mismatch(tmp_path: Path):
    transcript_path = _write_valid_transcript(
        tmp_path,
        tool_name="retrieve_company_context",
        source_url="fixture://missing.md",
    )

    with pytest.raises(HrInterviewReplayError, match="was not returned by mock retrieval"):
        replay_hr_interview_transcript(
            fixture_id="demo_hr",
            transcript_path=transcript_path,
        )


def _write_valid_transcript(
    tmp_path: Path,
    *,
    tool_name: str,
    source_url: str,
) -> Path:
    transcript_path = tmp_path / "transcript.md"
    transcript_path.write_text(
        "---\n"
        "fixture: demo_hr\n"
        "candidate: strong\n"
        "---\n\n"
        "## Interviewer\n\nQuestion?\n\n"
        "## Candidate\n\nAnswer.\n\n"
        "## Tool Event\n\n"
        f"tool: {tool_name}\n"
        "query: company values\n\n"
        "## Source\n\n"
        "title: Northstar Analytics Company Overview\n"
        f"url: {source_url}\n"
        "excerpt: Values\n\n"
        "## Expected Final Result\n\n"
        "overall_score: 7.0\n"
        "passed: true\n"
        "strengths: Clear\n"
        "improvements: More detail\n",
        encoding="utf-8",
    )
    return transcript_path
