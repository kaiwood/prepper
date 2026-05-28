from __future__ import annotations

import json
import time

from prepper_cli.hr_context import HrToolResult
from prepper_cli.hr_langchain_tools import record_hr_tool_result
from prepper_cli.hr_tool_events import HrToolEventRecorder


def test_tool_event_recorder_sanitizes_sensitive_payloads(tmp_path):
    log_path = tmp_path / "hr_tool_events.jsonl"
    recorder = HrToolEventRecorder(flow="test_flow", log_path=log_path)
    result = HrToolResult(
        tool_name="extract_candidate_profile",
        status="success",
        output={
            "mode": "mock",
            "profile": {
                "skills": ["SQL"],
                "experience": ["Analyst"],
                "risks": [],
                "interview_focus_areas": [],
            },
        },
    )

    record_hr_tool_result(
        recorder=recorder,
        tool_name="extract_candidate_profile",
        started_at=time.monotonic(),
        input_payload={
            "resume_text": "candidate@example.com secret resume",
            "profile_text": "private profile",
        },
        result=result,
    )

    events = recorder.to_public_dicts()
    assert len(events) == 1
    event = events[0]
    assert event["flow"] == "test_flow"
    assert event["tool_name"] == "extract_candidate_profile"
    assert event["status"] == "success"
    assert event["input"]["resume_text"] == {"redacted": True, "char_count": 35}
    assert event["output"]["profile_counts"]["skills"] == 1
    assert "candidate@example.com" not in json.dumps(event)
    assert log_path.exists()
    assert "candidate@example.com" not in log_path.read_text(encoding="utf-8")
