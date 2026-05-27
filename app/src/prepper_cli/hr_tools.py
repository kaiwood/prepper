from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .hr_context import (
    HrContextChunk,
    HrContextInputDocument,
    HrContextSource,
    HrToolResult,
)
from .hr_fixtures import HrFixture
from .hr_retrieval import build_document_retrieval_chunks

FETCH_COMPANY_WEBSITE_TOOL_NAME = "fetch_company_website"
DEFAULT_COMPANY_WEBSITE_TIMEOUT_SECONDS = 10.0
DEFAULT_COMPANY_WEBSITE_MAX_BYTES = 1_000_000
_ALLOWED_COMPANY_WEBSITE_SCHEMES = {"http", "https"}
_HTML_NOISE_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "form",
    "header",
    "footer",
    "nav",
}


class HrToolError(ValueError):
    """Raised when an HR domain tool cannot complete safely."""


@dataclass(frozen=True)
class CompanyWebsiteFetch:
    title: str
    uri: str
    text: str
    content_type: str
    byte_count: int
    truncated: bool


def run_fetch_company_website_tool(
    *,
    mode: str,
    fixture: HrFixture | None = None,
    url: str | None = None,
    timeout_seconds: float = DEFAULT_COMPANY_WEBSITE_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_COMPANY_WEBSITE_MAX_BYTES,
) -> HrToolResult:
    """Fetch company website content in mock or live mode."""
    if mode == "mock":
        if fixture is None:
            raise HrToolError("fetch_company_website mock mode requires --fixture")
        fetch = _fetch_company_website_from_fixture(fixture)
    elif mode == "llm":
        if url is None or not url.strip():
            raise HrToolError("fetch_company_website llm mode requires --url")
        fetch = _fetch_company_website_from_url(
            url.strip(), timeout_seconds=timeout_seconds, max_bytes=max_bytes
        )
    else:
        raise HrToolError("Tool mode must be one of: llm, mock")

    return _build_company_website_tool_result(fetch, mode=mode)


def company_website_tool_result_to_context_entries(
    result: HrToolResult,
) -> tuple[HrContextSource, HrContextInputDocument, tuple[HrContextChunk, ...]]:
    """Convert a successful fetch_company_website result into context entries."""
    if result.tool_name != FETCH_COMPANY_WEBSITE_TOOL_NAME:
        raise HrToolError(
            f"Expected tool result '{FETCH_COMPANY_WEBSITE_TOOL_NAME}', got '{result.tool_name}'"
        )
    if result.status != "success":
        raise HrToolError("Cannot convert a failed tool result into HR context entries")

    source_payload = _require_mapping(result.output, "source")
    document_payload = _require_mapping(result.output, "document")

    source = HrContextSource(
        id=_require_str(source_payload, "id"),
        kind=_require_str(source_payload, "kind"),
        title=_require_str(source_payload, "title"),
        uri=_require_str(source_payload, "uri"),
        content_sha256=_require_str(source_payload, "content_sha256"),
    )
    document = HrContextInputDocument(
        source_id=_require_str(document_payload, "source_id"),
        title=_require_str(document_payload, "title"),
        markdown=_require_str(document_payload, "markdown"),
        summary=_require_str(document_payload, "summary"),
    )
    chunks = build_document_retrieval_chunks(document=document, source=source)
    return source, document, chunks


def hr_tool_result_to_dict(result: HrToolResult) -> dict[str, Any]:
    return {
        "tool_name": result.tool_name,
        "status": result.status,
        "output": result.output,
    }


def _fetch_company_website_from_fixture(fixture: HrFixture) -> CompanyWebsiteFetch:
    raw = fixture.company_markdown
    return CompanyWebsiteFetch(
        title=_first_heading(raw, "Company website"),
        uri="fixture://company.md",
        text=raw.strip(),
        content_type="text/markdown; charset=utf-8",
        byte_count=len(raw.encode("utf-8")),
        truncated=False,
    )


def _fetch_company_website_from_url(
    url: str, *, timeout_seconds: float, max_bytes: int
) -> CompanyWebsiteFetch:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_COMPANY_WEBSITE_SCHEMES:
        allowed = ", ".join(sorted(_ALLOWED_COMPANY_WEBSITE_SCHEMES))
        raise HrToolError(f"Company website URL scheme must be one of: {allowed}")
    if not parsed.netloc:
        raise HrToolError("Company website URL must include a host")
    if timeout_seconds <= 0:
        raise HrToolError("Company website timeout must be greater than 0")
    if max_bytes <= 0:
        raise HrToolError("Company website max_bytes must be greater than 0")

    request = Request(
        url,
        headers={
            "User-Agent": "prepper-cli/0.1 HR company website fetcher",
            "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
        },
    )

    response = None
    try:
        response = urlopen(request, timeout=timeout_seconds)
        content_length = _safe_int(response.headers.get("Content-Length"))
        if content_length is not None and content_length > max_bytes:
            raise HrToolError("Company website response exceeded size limit")

        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise HrToolError("Company website response exceeded size limit")

        content_type = response.headers.get("Content-Type", "") or "application/octet-stream"
        charset = _response_charset(response) or "utf-8"
        decoded = raw.decode(charset, errors="replace")
        final_url = response.geturl() or url
    except TimeoutError as exc:
        raise HrToolError("Company website fetch timed out") from exc
    except HrToolError:
        raise
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise HrToolError(f"Company website fetch failed: {reason}") from exc
    except OSError as exc:
        raise HrToolError(f"Company website fetch failed: {exc}") from exc
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()

    title, text = _extract_readable_text(
        decoded, content_type=content_type, fallback_title=final_url
    )
    if not text.strip():
        raise HrToolError("Company website response did not contain readable text")

    return CompanyWebsiteFetch(
        title=title,
        uri=final_url,
        text=text,
        content_type=content_type,
        byte_count=len(raw),
        truncated=False,
    )


def _build_company_website_tool_result(
    fetch: CompanyWebsiteFetch, *, mode: str
) -> HrToolResult:
    source = HrContextSource(
        id="company_website",
        kind="company",
        title=fetch.title,
        uri=fetch.uri,
        content_sha256=_sha256_text(fetch.text),
    )
    document = HrContextInputDocument(
        source_id=source.id,
        title=fetch.title,
        markdown=fetch.text,
        summary=_summarize_text(fetch.text),
    )
    chunks = build_document_retrieval_chunks(document=document, source=source)

    return HrToolResult(
        tool_name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
        status="success",
        output={
            "mode": mode,
            "source": _source_to_dict(source),
            "document": _document_to_dict(document),
            "chunks": [_chunk_to_dict(chunk) for chunk in chunks],
            "fetch_metadata": {
                "url": fetch.uri,
                "content_type": fetch.content_type,
                "byte_count": fetch.byte_count,
                "truncated": fetch.truncated,
            },
        },
    )


def _extract_readable_text(
    raw_text: str, *, content_type: str, fallback_title: str
) -> tuple[str, str]:
    if "html" not in content_type.lower() and not _looks_like_html(raw_text):
        normalized = _normalize_text_lines(raw_text)
        return _first_heading(normalized, fallback_title), normalized

    soup = BeautifulSoup(raw_text, "html.parser")
    for tag in soup(_HTML_NOISE_TAGS):
        tag.decompose()

    title = ""
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(" ", strip=True)
    if not title:
        heading = soup.find(["h1", "h2"])
        if heading:
            title = heading.get_text(" ", strip=True)
    if not title:
        title = fallback_title

    body = soup.body or soup
    text = _normalize_text_lines(body.get_text("\n"))
    return title.strip(), text


def _looks_like_html(raw_text: str) -> bool:
    return bool(re.search(r"<\s*(html|body|main|article|section|p|h1|h2)\b", raw_text, re.I))


def _normalize_text_lines(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def _first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
        if stripped:
            return stripped[:120]
    return fallback


def _summarize_text(text: str, *, max_chars: int = 280) -> str:
    normalized = " ".join(
        re.sub(r"^#{1,6}\s*", "", line.strip())
        for line in text.splitlines()
        if line.strip()
    )
    if len(normalized) <= max_chars:
        return normalized
    truncated = normalized[: max_chars - 3].rsplit(" ", 1)[0].rstrip()
    return f"{truncated or normalized[: max_chars - 3].rstrip()}..."


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _response_charset(response: Any) -> str | None:
    get_content_charset = getattr(response.headers, "get_content_charset", None)
    if callable(get_content_charset):
        return get_content_charset()

    content_type = response.headers.get("Content-Type", "") or ""
    match = re.search(r"charset=([^;]+)", content_type, re.I)
    if match:
        return match.group(1).strip()
    return None


def _source_to_dict(source: HrContextSource) -> dict[str, str]:
    return {
        "id": source.id,
        "kind": source.kind,
        "title": source.title,
        "uri": source.uri,
        "content_sha256": source.content_sha256,
    }


def _document_to_dict(document: HrContextInputDocument) -> dict[str, str]:
    return {
        "source_id": document.source_id,
        "title": document.title,
        "markdown": document.markdown,
        "summary": document.summary,
    }


def _chunk_to_dict(chunk: HrContextChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "source_id": chunk.source_id,
        "text": chunk.text,
        "metadata": dict(chunk.metadata),
    }


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise HrToolError(f"Tool output field '{key}' must be an object")
    return value


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HrToolError(f"Tool output field '{key}' must be a non-empty string")
    return value
