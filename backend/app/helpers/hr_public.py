from __future__ import annotations

from copy import deepcopy
from typing import Any

from prepper_cli.hr_context import HrContext, HrContextBuildResult, hr_context_to_dict
from prepper_cli.hr_tools import (
    EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
    FETCH_COMPANY_WEBSITE_TOOL_NAME,
    FETCH_ROLE_DESCRIPTION_TOOL_NAME,
    FETCH_SOCIAL_PROFILE_TOOL_NAME,
    RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
    hr_tool_result_to_dict,
)

HR_TOOL_METADATA = [
    {
        "name": FETCH_COMPANY_WEBSITE_TOOL_NAME,
        "label": "Fetch company website",
        "phase": "context",
        "description": "Fetch readable public company website content from a URL.",
    },
    {
        "name": FETCH_ROLE_DESCRIPTION_TOOL_NAME,
        "label": "Fetch role description",
        "phase": "context",
        "description": "Fetch a public job-ad URL and extract a clean role description.",
    },
    {
        "name": FETCH_SOCIAL_PROFILE_TOOL_NAME,
        "label": "Fetch social profile",
        "phase": "context",
        "description": "Fetch public candidate profile text using the provided profile URL and token.",
    },
    {
        "name": "extract_resume_pdf_profile",
        "label": "Extract resume PDF profile",
        "phase": "context",
        "description": "Extract resume text from an uploaded PDF and enrich it for candidate profiling.",
    },
    {
        "name": EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
        "label": "Extract candidate profile",
        "phase": "context",
        "description": "Extract structured candidate facts, risks, and interview focus areas.",
    },
    {
        "name": RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
        "label": "Retrieve company context",
        "phase": "interview",
        "description": "Retrieve relevant company and role context snippets during the HR interview.",
    },
]


def build_response_payload(
    result: HrContextBuildResult,
    *,
    include_debug_context: bool = False,
) -> dict[str, Any]:
    context_payload = public_hr_context_payload(result.context) if result.context else None
    payload = {
        "schema_version": "hr-context-response.v1",
        "status": result.status,
        "context_id": result.context.context_id if result.context else None,
        "context": context_payload,
        "resolved_setup": resolved_setup_fields(result.context),
        "summaries": context_payload["summaries"] if context_payload else None,
        "sources": context_payload["sources"] if context_payload else [],
        "tools": deepcopy(HR_TOOL_METADATA),
        "tool_results": [
            sanitize_public_tool_result(hr_tool_result_to_dict(tool_result))
            for tool_result in result.tool_results
        ],
        "tool_call_events": list(result.tool_call_events),
        "errors": [
            {
                "tool_name": error.tool_name,
                "message": public_tool_error_message(error.tool_name),
            }
            for error in result.errors
        ],
    }
    return attach_debug_context(payload, result.context, include_debug_context)


def resolved_setup_fields(context: HrContext | None) -> dict[str, str] | None:
    if context is None:
        return None
    company_text = context.company_inputs[0].markdown if context.company_inputs else ""
    return {
        "company_text": company_text,
        "role_description": context.role_description.markdown,
    }


def public_hr_error(message: str) -> dict[str, str]:
    return {"error": message}


def is_public_validation_error(message: str) -> bool:
    return (
        message in {"invalid context_id", "mode must be one of: llm, mock"}
        or message.endswith(" is required")
        or message.endswith(" must be a string")
        or message.endswith(" must be an object")
        or " must contain only string keys and values" in message
    )


def sanitize_public_hr_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = deepcopy(payload)
    context_payload = sanitized.get("context")
    if isinstance(context_payload, dict):
        sanitized["context"] = sanitize_public_context_dict(context_payload)
    tool_results = sanitized.get("tool_results")
    if isinstance(tool_results, list):
        sanitized["tool_results"] = [
            sanitize_public_tool_result(tool_result)
            if isinstance(tool_result, dict)
            else tool_result
            for tool_result in tool_results
        ]
    return sanitized


def public_hr_context_payload(context: HrContext) -> dict[str, Any]:
    return sanitize_public_context_dict(hr_context_to_dict(context))


def sanitize_public_context_dict(context_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": context_payload.get("schema_version"),
        "context_id": context_payload.get("context_id"),
        "fixture_id": context_payload.get("fixture_id"),
        "mode": context_payload.get("mode"),
        "summaries": deepcopy(context_payload.get("summaries")),
        "sources": public_sources_from_context_sources(context_payload.get("sources")),
        "tool_results": [
            sanitize_public_tool_result(tool_result)
            for tool_result in context_payload.get("tool_results", [])
            if isinstance(tool_result, dict)
        ],
    }


def public_resume_profile_tool_result(tool_result: dict[str, Any]) -> dict[str, Any]:
    public_result = sanitize_public_tool_result(tool_result)
    output = tool_result.get("output")
    if isinstance(output, dict):
        public_output = public_result.setdefault("output", {})
        if isinstance(public_output, dict):
            if isinstance(output.get("profile"), dict):
                public_output["profile"] = deepcopy(output["profile"])
            if isinstance(output.get("resume_text"), str):
                public_output["resume_text"] = output["resume_text"]
    return public_result


def sanitize_public_tool_result(tool_result: dict[str, Any]) -> dict[str, Any]:
    public_result: dict[str, Any] = {
        "tool_name": tool_result.get("tool_name"),
        "status": tool_result.get("status"),
    }
    output = tool_result.get("output")
    if tool_result.get("status") == "error":
        public_output: dict[str, Any] = {
            "error": public_tool_error_message(
                str(tool_result.get("tool_name") or "HR tool")
            )
        }
        if isinstance(output, dict) and "mode" in output:
            public_output["mode"] = output["mode"]
        public_result["output"] = public_output
        return public_result

    if isinstance(output, dict):
        public_result["output"] = sanitize_public_tool_output(output)
    return public_result


def sanitize_public_tool_output(output: dict[str, Any]) -> dict[str, Any]:
    public_output: dict[str, Any] = {}
    for key in ("mode", "result_count", "decision", "summary"):
        value = output.get(key)
        if is_public_scalar(value):
            public_output[key] = value

    source = output.get("source")
    if isinstance(source, dict):
        public_source = public_source_from_mapping(source)
        if public_source:
            public_output["source"] = public_source

    sources = output.get("sources")
    if isinstance(sources, list):
        public_sources = public_sources_from_context_sources(sources)
        if public_sources:
            public_output["sources"] = public_sources

    document = output.get("document")
    if isinstance(document, dict):
        title = document.get("title")
        summary = document.get("summary")
        if is_public_scalar(title):
            public_output["document_title"] = title
        if is_public_scalar(summary):
            public_output["summary"] = summary

    for metadata_key in ("input_metadata", "fetch_metadata"):
        metadata = output.get(metadata_key)
        if isinstance(metadata, dict):
            public_metadata = {
                str(key): value
                for key, value in metadata.items()
                if is_public_scalar(value)
            }
            if public_metadata:
                public_output[metadata_key] = public_metadata

    return public_output


def public_sources_from_context_sources(sources: Any) -> list[dict[str, Any]]:
    if not isinstance(sources, list):
        return []

    public_sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        public_source = public_source_from_mapping(source)
        if not public_source:
            continue
        key = str(
            public_source.get("uri")
            or public_source.get("url")
            or public_source.get("id")
            or f"source-{index}"
        )
        if key in seen:
            continue
        seen.add(key)
        public_sources.append(public_source)
    return public_sources


def public_sources_from_tool_sources(sources: list[Any]) -> list[dict[str, Any]]:
    public_sources: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        uri = source.get("uri") or source.get("url")
        if not uri:
            continue
        public_sources.append(
            {
                "title": str(source.get("title") or uri),
                "uri": str(uri),
                "excerpt": str(source.get("excerpt") or ""),
                "score": source.get("score"),
                "relevance_percent": source.get("relevance_percent"),
            }
        )
    return public_sources


def public_source_from_mapping(source: dict[str, Any]) -> dict[str, Any]:
    public_source: dict[str, Any] = {}
    field_aliases = {
        "id": ("id", "source_id"),
        "kind": ("kind", "source_kind"),
        "title": ("title", "source_title"),
        "uri": ("uri", "url", "source_uri"),
        "excerpt": ("excerpt",),
        "score": ("score",),
        "relevance_percent": ("relevance_percent",),
        "char_count": ("char_count",),
    }
    for public_key, aliases in field_aliases.items():
        for alias in aliases:
            value = source.get(alias)
            if is_public_scalar(value):
                public_source[public_key] = value
                break
    return public_source


def attach_debug_context(
    payload: dict[str, Any],
    context: HrContext | None,
    include_debug_context: bool,
) -> dict[str, Any]:
    if include_debug_context and context is not None:
        payload["debug_context"] = hr_context_to_dict(context)
    return payload


def include_debug_context(data: dict[str, Any]) -> bool:
    return data.get("include_debug_context") is True


def is_public_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def public_tool_error_message(tool_name: str) -> str:
    return f"{tool_name} failed; review server logs or rerun the workflow locally."
