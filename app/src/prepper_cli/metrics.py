from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .admin_persistence import default_sqlite_path

_SCHEMA_VERSION = 1
_DEFAULT_WINDOW_HOURS = 24
_DEFAULT_RECENT_LIMIT = 30
_MAX_METADATA_BYTES = 8_000


@dataclass(frozen=True)
class MetricEvent:
    timestamp: str
    event: str
    status: str
    duration_ms: int | None
    operation: str
    tool_name: str
    model: str
    mode: str
    route: str
    method: str
    status_code: int | None
    error_type: str
    metadata: dict[str, Any]


def record_metric_event(
    event: str,
    *,
    status: str,
    timestamp: str | None = None,
    db_path: Path | str | None = None,
    **fields: Any,
) -> None:
    """Persist a sanitized observability event for the dashboard.

    Metrics intentionally store only operational metadata. Callers must not pass raw
    prompts, resumes, profiles, retrieved chunks, API keys, or secrets.
    """
    normalized_event = _normalize_text(event, fallback="event", max_length=80)
    normalized_status = _normalize_text(status, fallback="unknown", max_length=40)
    path = Path(db_path).expanduser() if db_path is not None else default_sqlite_path()
    metadata = _sanitize_metadata(fields)
    encoded_metadata = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    if len(encoded_metadata.encode("utf-8")) > _MAX_METADATA_BYTES:
        metadata = {
            "truncated": True,
            "keys": sorted(str(key) for key in metadata.keys())[:50],
        }
        encoded_metadata = json.dumps(metadata, sort_keys=True, separators=(",", ":"))

    with _connect(path) as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO prepper_metric_events (
                timestamp,
                event,
                status,
                duration_ms,
                operation,
                tool_name,
                model,
                mode,
                route,
                method,
                status_code,
                error_type,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp or _utc_now_iso(),
                normalized_event,
                normalized_status,
                _optional_int(fields.get("duration_ms")),
                _normalize_text(fields.get("operation"), max_length=120),
                _normalize_text(fields.get("tool_name"), max_length=120),
                _normalize_text(fields.get("model"), max_length=160),
                _normalize_text(fields.get("mode"), max_length=40),
                _normalize_text(fields.get("route"), max_length=240),
                _normalize_text(fields.get("method"), max_length=16),
                _optional_int(fields.get("status_code")),
                _normalize_text(fields.get("error_type"), max_length=120),
                encoded_metadata,
            ),
        )
        conn.commit()


def get_metrics_snapshot(
    *,
    window_hours: int = _DEFAULT_WINDOW_HOURS,
    recent_limit: int = _DEFAULT_RECENT_LIMIT,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    path = Path(db_path).expanduser() if db_path is not None else default_sqlite_path()
    if not path.exists():
        return _empty_snapshot(window_hours=window_hours)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, window_hours))
    cutoff_iso = _datetime_to_iso(cutoff)
    with _connect(path) as conn:
        _ensure_schema(conn)
        rows = [
            _row_to_event(row)
            for row in conn.execute(
                """
                SELECT * FROM prepper_metric_events
                WHERE timestamp >= ?
                ORDER BY timestamp DESC, id DESC
                """,
                (cutoff_iso,),
            )
        ]

    route_rows = [row for row in rows if row.event == "route_request"]
    tool_rows = [row for row in rows if row.event == "tool_call"]
    retrieval_rows = [row for row in rows if row.event == "retrieval"]
    llm_rows = [row for row in rows if row.event == "llm_call"]

    snapshot = {
        "schema_version": "prepper-metrics.v1",
        "generated_at": _utc_now_iso(),
        "window_hours": max(1, window_hours),
        "overview": _build_overview(rows, route_rows, tool_rows, retrieval_rows),
        "time_buckets": _build_time_buckets(route_rows, cutoff=cutoff),
        "tools": _build_tool_breakdown(tool_rows),
        "rag": _build_rag_summary(retrieval_rows),
        "llm": _build_llm_summary(llm_rows),
        "safety": _build_safety_summary(rows),
        "recent_events": _build_recent_events(rows, limit=recent_limit),
    }
    return snapshot


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prepper_metrics_schema (
            version INTEGER PRIMARY KEY
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prepper_metric_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms INTEGER,
            operation TEXT NOT NULL DEFAULT '',
            tool_name TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            mode TEXT NOT NULL DEFAULT '',
            route TEXT NOT NULL DEFAULT '',
            method TEXT NOT NULL DEFAULT '',
            status_code INTEGER,
            error_type TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_prepper_metric_events_timestamp ON prepper_metric_events(timestamp)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_prepper_metric_events_event ON prepper_metric_events(event)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO prepper_metrics_schema (version) VALUES (?)",
        (_SCHEMA_VERSION,),
    )


def _row_to_event(row: sqlite3.Row) -> MetricEvent:
    try:
        metadata = json.loads(str(row["metadata_json"] or "{}"))
    except json.JSONDecodeError:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    return MetricEvent(
        timestamp=str(row["timestamp"]),
        event=str(row["event"]),
        status=str(row["status"]),
        duration_ms=_optional_int(row["duration_ms"]),
        operation=str(row["operation"] or ""),
        tool_name=str(row["tool_name"] or ""),
        model=str(row["model"] or ""),
        mode=str(row["mode"] or ""),
        route=str(row["route"] or ""),
        method=str(row["method"] or ""),
        status_code=_optional_int(row["status_code"]),
        error_type=str(row["error_type"] or ""),
        metadata=metadata,
    )


def _build_overview(
    rows: list[MetricEvent],
    route_rows: list[MetricEvent],
    tool_rows: list[MetricEvent],
    retrieval_rows: list[MetricEvent],
) -> dict[str, Any]:
    route_errors = [row for row in route_rows if _is_error_row(row)]
    route_durations = [row.duration_ms for row in route_rows if row.duration_ms is not None]
    successful_tools = [row for row in tool_rows if row.status == "success"]
    completed_interviews = [row for row in rows if row.event == "hr_interview" and row.status == "completed"]
    started_interviews = [row for row in rows if row.event == "hr_interview" and row.status == "started"]
    built_contexts = [row for row in rows if row.event == "hr_context" and row.status == "success"]
    return {
        "requests_total": len(route_rows),
        "error_count": len(route_errors),
        "error_rate": _ratio(len(route_errors), len(route_rows)),
        "avg_latency_ms": _average(route_durations),
        "p95_latency_ms": _percentile(route_durations, 95),
        "rate_limit_hits": sum(1 for row in rows if row.event == "rate_limit"),
        "hr_contexts_built": len(built_contexts),
        "interviews_started": len(started_interviews),
        "interviews_completed": len(completed_interviews),
        "rag_retrievals": len(retrieval_rows),
        "tool_success_rate": _ratio(len(successful_tools), len(tool_rows)),
        "llm_failures": sum(1 for row in rows if row.event == "llm_call" and row.status == "error"),
    }


def _build_time_buckets(route_rows: list[MetricEvent], *, cutoff: datetime) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    start = cutoff.replace(minute=0, second=0, microsecond=0)
    for index in range(25):
        bucket_time = start + timedelta(hours=index)
        key = bucket_time.strftime("%Y-%m-%dT%H:00:00Z")
        buckets[key] = {"bucket": key, "requests": 0, "errors": 0, "avg_latency_ms": 0, "_durations": []}

    for row in route_rows:
        parsed = _parse_iso(row.timestamp)
        if parsed is None:
            continue
        key = parsed.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00:00Z")
        if key not in buckets:
            buckets[key] = {"bucket": key, "requests": 0, "errors": 0, "avg_latency_ms": 0, "_durations": []}
        buckets[key]["requests"] += 1
        if _is_error_row(row):
            buckets[key]["errors"] += 1
        if row.duration_ms is not None:
            buckets[key]["_durations"].append(row.duration_ms)

    result = []
    for bucket in sorted(buckets.values(), key=lambda item: str(item["bucket"])):
        durations = bucket.pop("_durations")
        bucket["avg_latency_ms"] = _average(durations)
        result.append(bucket)
    return result


def _build_tool_breakdown(tool_rows: list[MetricEvent]) -> list[dict[str, Any]]:
    grouped: dict[str, list[MetricEvent]] = defaultdict(list)
    for row in tool_rows:
        grouped[row.tool_name or row.operation or "unknown"].append(row)
    return [
        {
            "name": name,
            "calls": len(items),
            "successes": sum(1 for item in items if item.status == "success"),
            "errors": sum(1 for item in items if item.status == "error"),
            "avg_duration_ms": _average([item.duration_ms for item in items if item.duration_ms is not None]),
            "last_status": items[0].status if items else "unknown",
            "last_error_type": next((item.error_type for item in items if item.error_type), ""),
        }
        for name, items in sorted(grouped.items())
    ]


def _build_rag_summary(retrieval_rows: list[MetricEvent]) -> dict[str, Any]:
    successes = [row for row in retrieval_rows if row.status == "success"]
    errors = [row for row in retrieval_rows if row.status == "error"]
    result_counts = [_metadata_number(row, "result_count") for row in successes]
    result_counts = [value for value in result_counts if value is not None]
    chunk_counts = [_metadata_number(row, "chunk_count") for row in retrieval_rows]
    chunk_counts = [value for value in chunk_counts if value is not None]
    top_scores = [_metadata_number(row, "top_score") for row in successes]
    top_scores = [value for value in top_scores if value is not None]
    return {
        "retrievals": len(retrieval_rows),
        "successes": len(successes),
        "errors": len(errors),
        "success_rate": _ratio(len(successes), len(retrieval_rows)),
        "avg_duration_ms": _average([row.duration_ms for row in retrieval_rows if row.duration_ms is not None]),
        "avg_result_count": _average(result_counts),
        "no_result_count": sum(1 for value in result_counts if value == 0),
        "avg_chunk_count": _average(chunk_counts),
        "avg_top_relevance_percent": round((_average_float(top_scores) or 0) * 100),
        "embedding_failures": sum(1 for row in errors if "embedding" in row.error_type.lower() or "embedding" in str(row.metadata).lower()),
    }


def _build_llm_summary(llm_rows: list[MetricEvent]) -> dict[str, Any]:
    grouped: dict[str, list[MetricEvent]] = defaultdict(list)
    for row in llm_rows:
        grouped[row.operation or "chat_completion"].append(row)
    return {
        "calls": len(llm_rows),
        "successes": sum(1 for row in llm_rows if row.status == "success"),
        "errors": sum(1 for row in llm_rows if row.status == "error"),
        "avg_duration_ms": _average([row.duration_ms for row in llm_rows if row.duration_ms is not None]),
        "operations": [
            {
                "operation": operation,
                "calls": len(items),
                "errors": sum(1 for item in items if item.status == "error"),
                "avg_duration_ms": _average([item.duration_ms for item in items if item.duration_ms is not None]),
                "models": sorted({item.model for item in items if item.model}),
            }
            for operation, items in sorted(grouped.items())
        ],
    }


def _build_safety_summary(rows: list[MetricEvent]) -> dict[str, Any]:
    return {
        "rate_limit_hits": sum(1 for row in rows if row.event == "rate_limit"),
        "blocked_url_attempts": sum(1 for row in rows if _is_blocked_url_event(row)),
        "oversized_input_rejections": sum(1 for row in rows if _contains(row, "exceeded size") or _contains(row, "too_long")),
        "invalid_pdf_uploads": sum(1 for row in rows if _contains(row, "pdf") and row.status == "error"),
        "client_validation_errors": sum(1 for row in rows if row.event == "route_request" and row.status_code == 400),
        "debug_context_requests": sum(1 for row in rows if _metadata_bool(row, "include_debug_context")),
    }


def _build_recent_events(rows: list[MetricEvent], *, limit: int) -> list[dict[str, Any]]:
    visible_events = {
        "tool_call",
        "retrieval",
        "llm_call",
        "route_failure",
        "rate_limit",
        "hr_context",
        "hr_interview",
    }
    result = []
    for row in rows:
        if row.event not in visible_events:
            continue
        error_message = _normalize_text(row.metadata.get("error_message"), max_length=500)
        if row.event == "rate_limit" and not error_message:
            error_message = "Rate limit exceeded for this route."
        result.append(
            {
                "timestamp": row.timestamp,
                "event": row.event,
                "status": row.status,
                "label": row.tool_name or row.operation or row.route or row.event,
                "duration_ms": row.duration_ms,
                "model": row.model,
                "mode": row.mode,
                "operation": row.operation,
                "tool_name": row.tool_name,
                "route": row.route,
                "method": row.method,
                "error_type": row.error_type,
                "error_message": error_message,
                "status_code": row.status_code,
            }
        )
        if len(result) >= limit:
            break
    return result


def _empty_snapshot(*, window_hours: int) -> dict[str, Any]:
    return {
        "schema_version": "prepper-metrics.v1",
        "generated_at": _utc_now_iso(),
        "window_hours": max(1, window_hours),
        "overview": _build_overview([], [], [], []),
        "time_buckets": [],
        "tools": [],
        "rag": _build_rag_summary([]),
        "llm": _build_llm_summary([]),
        "safety": _build_safety_summary([]),
        "recent_events": [],
    }


def _sanitize_metadata(fields: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in fields.items():
        safe_key = _normalize_text(key, fallback="field", max_length=80)
        if safe_key in {"api_key", "authorization", "token", "secret", "resume_text", "profile_text", "company_text", "role_description", "snippets", "chunks"}:
            result[safe_key] = {"redacted": True}
        elif isinstance(value, (str, int, float, bool)) or value is None:
            result[safe_key] = _sanitize_scalar(value)
        elif isinstance(value, dict):
            result[safe_key] = {"keys": sorted(str(item_key) for item_key in value.keys())[:20]}
        elif isinstance(value, (list, tuple)):
            result[safe_key] = {"item_count": len(value)}
        else:
            result[safe_key] = _normalize_text(str(value), max_length=240)
    return result


def _sanitize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return _normalize_text(value, max_length=240)
    return value


def _normalize_text(value: Any, fallback: str = "", max_length: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _metadata_number(row: MetricEvent, key: str) -> float | None:
    value = row.metadata.get(key)
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metadata_bool(row: MetricEvent, key: str) -> bool:
    return row.metadata.get(key) is True


def _is_error_row(row: MetricEvent) -> bool:
    return row.status == "error" or (row.status_code is not None and row.status_code >= 400)


def _is_blocked_url_event(row: MetricEvent) -> bool:
    return row.error_type == "UnsafeCompanyWebsiteUrlError" or _contains(row, "blocked address")


def _contains(row: MetricEvent, needle: str) -> bool:
    haystack = " ".join(
        str(value)
        for value in (
            row.error_type,
            row.metadata.get("error_message"),
            row.metadata.get("error"),
            row.metadata.get("route"),
        )
    ).lower()
    return needle.lower() in haystack


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _average(values: list[int | float | None]) -> int:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return 0
    return round(sum(clean) / len(clean))


def _average_float(values: list[int | float | None]) -> float:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return 0.0
    return round(sum(clean) / len(clean), 4)


def _percentile(values: list[int | float], percentile: int) -> int:
    clean = sorted(float(value) for value in values)
    if not clean:
        return 0
    index = min(len(clean) - 1, max(0, round((percentile / 100) * (len(clean) - 1))))
    return round(clean[index])


def _utc_now_iso() -> str:
    return _datetime_to_iso(datetime.now(timezone.utc))


def _datetime_to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
