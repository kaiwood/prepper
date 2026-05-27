from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin

from app import limiter
from prepper_cli.hr_context import (
    HrContext,
    HrContextBuildResult,
    HrContextValidationError,
    build_hr_context_from_inputs,
    hr_context_to_dict,
)
from prepper_cli.hr_tools import hr_tool_result_to_dict

hr_bp = Blueprint("hr", __name__)

_HR_CONTEXTS: dict[str, HrContext] = {}


@hr_bp.route("/api/hr/context", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def hr_context_options():
    return "", 204


@hr_bp.post("/api/hr/context")
@limiter.limit("10 per minute")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def build_hr_context():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object body is required"}), 400

    try:
        mode = _optional_string(data, "mode") or "mock"
        company_text = _optional_string(data, "company_text")
        company_url = _optional_string(data, "company_url")
        role_description = _required_string(data, "role_description")
        resume_text = _required_string(data, "resume_text")
        profile_text = _optional_string(data, "profile_text") or ""
        model = _optional_string(data, "model")
        fixture_id = _optional_string(data, "fixture_id")
        source_uris = _optional_string_mapping(data, "source_uris")

        result = build_hr_context_from_inputs(
            mode=mode,
            company_text=company_text,
            company_url=company_url,
            role_description=role_description,
            resume_text=resume_text,
            profile_text=profile_text,
            model=model,
            fixture_id=fixture_id,
            source_uris=source_uris,
        )
    except HrContextValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - defensive API safety net
        return jsonify({"error": f"HR context build failed: {exc}"}), 502

    if result.context is not None:
        _HR_CONTEXTS[result.context.context_id] = result.context

    return jsonify(_build_response_payload(result))


def get_stored_hr_context(context_id: str) -> HrContext | None:
    return _HR_CONTEXTS.get(context_id)


def _build_response_payload(result: HrContextBuildResult) -> dict[str, Any]:
    context_payload = hr_context_to_dict(result.context) if result.context else None
    return {
        "schema_version": "hr-context-response.v1",
        "status": result.status,
        "context_id": result.context.context_id if result.context else None,
        "context": context_payload,
        "summaries": context_payload["summaries"] if context_payload else None,
        "sources": context_payload["sources"] if context_payload else [],
        "tool_results": [
            hr_tool_result_to_dict(tool_result) for tool_result in result.tool_results
        ],
        "errors": [
            {"tool_name": error.tool_name, "message": error.message}
            for error in result.errors
        ],
    }


def _optional_string(data: dict[str, Any], field_name: str) -> str | None:
    if field_name not in data or data[field_name] is None:
        return None
    value = data[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value.strip()


def _required_string(data: dict[str, Any], field_name: str) -> str:
    value = _optional_string(data, field_name)
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def _optional_string_mapping(data: dict[str, Any], field_name: str) -> dict[str, str] | None:
    if field_name not in data or data[field_name] is None:
        return None
    value = data[field_name]
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    result = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or not isinstance(item_value, str):
            raise ValueError(f"{field_name} must contain only string keys and values")
        if item_value.strip():
            result[item_key] = item_value.strip()
    return result
