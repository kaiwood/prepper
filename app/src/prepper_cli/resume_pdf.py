from __future__ import annotations

import io
import logging
import time
from typing import Any

from .hr_context import HrToolResult
from .hr_tools import (
    DEFAULT_CANDIDATE_PROFILE_MAX_CHARS,
    HrToolError,
    run_extract_candidate_profile_tool,
)
from .structured_logging import duration_ms, exception_log_fields, log_structured_event

DEFAULT_RESUME_PDF_MAX_BYTES = 5 * 1024 * 1024


def extract_resume_text_from_pdf_bytes(
    pdf_bytes: bytes,
    *,
    max_chars: int = DEFAULT_CANDIDATE_PROFILE_MAX_CHARS,
) -> str:
    """Extract readable resume text from PDF bytes."""
    if not pdf_bytes:
        raise HrToolError("Resume PDF must not be empty")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HrToolError("Resume upload must be a PDF file")
    if max_chars <= 0:
        raise HrToolError("Resume PDF max_chars must be greater than 0")

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency/package safety net
        raise HrToolError("PDF extraction requires pypdf to be installed") from exc

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        page_texts = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise HrToolError("Resume PDF could not be read") from exc

    text = _normalize_pdf_text("\n\n".join(page_texts))
    if not text:
        raise HrToolError("Resume PDF did not contain readable text")
    if len(text) > max_chars:
        raise HrToolError("Resume PDF text exceeded size limit")
    return text


def run_extract_resume_pdf_profile_tool(
    *,
    pdf_bytes: bytes,
    filename: str | None = None,
    mode: str = "llm",
    model: str | None = None,
    max_chars: int = DEFAULT_CANDIDATE_PROFILE_MAX_CHARS,
) -> HrToolResult:
    """Extract an existing candidate-profile tool result from an uploaded resume PDF."""
    started_at = time.monotonic()
    log_fields: dict[str, Any] = {
        "tool_name": "extract_resume_pdf_profile",
        "mode": mode,
        "model": model,
        "filename": filename or "",
        "pdf_byte_count": len(pdf_bytes),
        "max_chars": max_chars,
    }
    try:
        resume_text = extract_resume_text_from_pdf_bytes(pdf_bytes, max_chars=max_chars)
        result = run_extract_candidate_profile_tool(
            mode=mode,
            resume_text=resume_text,
            profile_text="",
            model=model,
            max_chars=max_chars,
        )
        if isinstance(result.output, dict):
            result.output["resume_text"] = resume_text
    except Exception as exc:
        log_structured_event(
            "tool_call",
            status="error",
            level=logging.WARNING,
            duration_ms=duration_ms(started_at),
            **log_fields,
            **exception_log_fields(exc),
        )
        raise

    log_structured_event(
        "tool_call",
        status=result.status,
        duration_ms=duration_ms(started_at),
        extracted_char_count=len(resume_text),
        **log_fields,
    )
    return result


def _normalize_pdf_text(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.splitlines()]
    paragraphs = [line for line in lines if line]
    return "\n".join(paragraphs).strip()
