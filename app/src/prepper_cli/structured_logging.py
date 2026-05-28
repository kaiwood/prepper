from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

LOGGER_NAME = "prepper_cli.observability"
MAX_LOG_STRING_LENGTH = 240

_SENSITIVE_FIELD_NAMES = {
    "resume",
    "resume_text",
    "profile",
    "profile_text",
    "company_text",
    "role_description",
    "markdown",
    "document",
    "documents",
    "chunks",
    "snippets",
    "api_key",
    "authorization",
    "token",
    "secret",
}
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_SECRET_RE = re.compile(r"\b(?:sk-or-|sk-)[A-Za-z0-9_-]{12,}\b")


def duration_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def safe_snippet(value: Any, *, max_length: int = MAX_LOG_STRING_LENGTH) -> str:
    text = " ".join(str(value or "").split())
    text = _scrub_text(text)
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


def exception_log_fields(exc: Exception) -> dict[str, str]:
    return {
        "error_type": type(exc).__name__,
        "error_message": safe_snippet(str(exc)),
    }


def log_structured_event(
    event: str,
    *,
    status: str,
    level: int = logging.INFO,
    logger: logging.Logger | None = None,
    **fields: Any,
) -> None:
    target_logger = logger or logging.getLogger(LOGGER_NAME)
    safe_fields = _sanitize_mapping(fields)
    parts = [f"event={_format_value(event)}", f"status={_format_value(status)}"]
    parts.extend(
        f"{key}={_format_value(value)}"
        for key, value in sorted(safe_fields.items())
        if value is not None
    )
    target_logger.log(level, " ".join(parts))


def _sanitize_mapping(fields: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _sanitize_value(str(key), value) for key, value in fields.items()}


def _sanitize_value(key: str, value: Any) -> Any:
    if key.lower() in _SENSITIVE_FIELD_NAMES:
        return _summarize_sensitive_value(value)
    if isinstance(value, dict):
        return {str(item_key): _sanitize_value(str(item_key), item_value) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(key, item) for item in list(value)[:10]]
    if isinstance(value, str):
        return safe_snippet(value)
    return value


def _summarize_sensitive_value(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"redacted": True, "char_count": len(value)}
    if isinstance(value, (list, tuple)):
        return {"redacted": True, "item_count": len(value)}
    if isinstance(value, dict):
        return {"redacted": True, "keys": sorted(str(key) for key in value.keys())[:20]}
    return {"redacted": True}


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if value is None:
        return "null"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _scrub_text(text: str) -> str:
    return _SECRET_RE.sub("[redacted-secret]", _EMAIL_RE.sub("[redacted-email]", text))
