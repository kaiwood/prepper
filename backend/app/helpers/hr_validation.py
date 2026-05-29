from __future__ import annotations

from typing import Any

from app.helpers.validation import validate_string_length

HR_TEXT_LIMITS = {
    "company_text": 40_000,
    "company_url": 2_048,
    "role_description": 40_000,
    "role_url": 2_048,
    "resume_text": 40_000,
    "profile_text": 40_000,
    "profile_url": 2_048,
    "oauth_token": 8_000,
    "message": 8_000,
    "context_id": 128,
    "interview_id": 128,
    "mode": 32,
    "language": 32,
    "model": 200,
    "fixture_id": 128,
    "difficulty": 32,
    "filename": 255,
}


def optional_string(data: dict[str, Any], field_name: str) -> str | None:
    if field_name not in data or data[field_name] is None:
        return None
    value = data[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    max_length = HR_TEXT_LIMITS.get(field_name)
    if max_length is not None:
        validate_string_length(value, field=field_name, max_length=max_length)
    return value.strip()


def required_string(data: dict[str, Any], field_name: str) -> str:
    value = optional_string(data, field_name)
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def optional_string_mapping(data: dict[str, Any], field_name: str) -> dict[str, str] | None:
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
