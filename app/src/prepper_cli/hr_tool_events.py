from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {
    "resume",
    "resume_text",
    "profile",
    "profile_text",
    "company_text",
    "role_description",
    "markdown",
    "text",
    "document",
    "documents",
    "chunks",
    "snippets",
}
MAX_PUBLIC_STRING_LENGTH = 240


@dataclass(frozen=True)
class HrToolCallEvent:
    event_id: str
    timestamp: str
    flow: str
    sequence: int
    tool_name: str
    status: str
    duration_ms: int
    input: dict[str, Any]
    output: dict[str, Any]


def hr_tool_call_event_to_dict(event: HrToolCallEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "timestamp": event.timestamp,
        "flow": event.flow,
        "sequence": event.sequence,
        "tool_name": event.tool_name,
        "status": event.status,
        "duration_ms": event.duration_ms,
        "input": event.input,
        "output": event.output,
    }


class HrToolEventRecorder:
    def __init__(self, *, flow: str, log_path: str | Path | None = None):
        self.flow = flow
        self.log_path = Path(log_path) if log_path is not None else _default_log_path()
        self.events: list[HrToolCallEvent] = []

    def record(
        self,
        *,
        tool_name: str,
        status: str,
        started_at: float,
        input_payload: dict[str, Any] | None = None,
        output_payload: dict[str, Any] | None = None,
    ) -> HrToolCallEvent:
        event = HrToolCallEvent(
            event_id=uuid.uuid4().hex,
            timestamp=_utc_timestamp(),
            flow=self.flow,
            sequence=len(self.events) + 1,
            tool_name=tool_name,
            status=status,
            duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            input=sanitize_tool_event_payload(input_payload or {}),
            output=sanitize_tool_event_payload(output_payload or {}),
        )
        self.events.append(event)
        self._append_event(event)
        return event

    def to_public_dicts(self) -> list[dict[str, Any]]:
        return [hr_tool_call_event_to_dict(event) for event in self.events]

    def _append_event(self, event: HrToolCallEvent) -> None:
        if self.log_path is None:
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(hr_tool_call_event_to_dict(event), sort_keys=True) + "\n")
        except OSError:
            # Tool event persistence is useful for observability but must not break HR flows.
            return


def sanitize_tool_event_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in SENSITIVE_KEYS:
                sanitized[key_text] = _summarize_sensitive_value(item)
            else:
                sanitized[key_text] = sanitize_tool_event_payload(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_tool_event_payload(item) for item in value[:10]]
    if isinstance(value, tuple):
        return [sanitize_tool_event_payload(item) for item in value[:10]]
    if isinstance(value, str):
        return _truncate(value)
    return value


def summarize_tool_result_output(output: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if "mode" in output:
        summary["mode"] = output["mode"]
    if "query" in output:
        summary["query"] = output["query"]
    if "result_count" in output:
        summary["result_count"] = output["result_count"]
    if "profile" in output and isinstance(output["profile"], dict):
        profile = output["profile"]
        summary["profile_counts"] = {
            key: len(value) for key, value in profile.items() if isinstance(value, list)
        }
    if "source" in output and isinstance(output["source"], dict):
        source = output["source"]
        summary["source"] = {
            "id": source.get("id"),
            "kind": source.get("kind"),
            "title": source.get("title"),
            "uri": source.get("uri"),
        }
    if "fetch_metadata" in output:
        summary["fetch_metadata"] = output["fetch_metadata"]
    if "error" in output:
        summary["error"] = output["error"]
    return sanitize_tool_event_payload(summary or output)


def _summarize_sensitive_value(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"redacted": True, "char_count": len(value)}
    if isinstance(value, list) or isinstance(value, tuple):
        return {"redacted": True, "item_count": len(value)}
    if isinstance(value, dict):
        return {"redacted": True, "keys": sorted(str(key) for key in value.keys())[:20]}
    return {"redacted": True}


def _truncate(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= MAX_PUBLIC_STRING_LENGTH:
        return normalized
    return normalized[: MAX_PUBLIC_STRING_LENGTH - 1] + "…"


def _default_log_path() -> Path | None:
    raw_path = os.environ.get("PREPPER_HR_TOOL_EVENT_LOG_PATH", "").strip()
    if raw_path:
        return Path(raw_path)
    return None


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
