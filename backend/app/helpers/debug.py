import logging
import json
import re

from flask import current_app

_ANSI_CYAN = "\033[36m"
_ANSI_GREEN = "\033[32m"
_ANSI_RESET = "\033[0m"
_PREPPER_JSON_MARKER = "[PREPPER_JSON]"
_STRING_FIELD_PATTERN = re.compile(
    r'(^\s*)"([^"]+)"\s*:\s*"((?:\\.|[^"\\])*)"(,?)',
    flags=re.MULTILINE,
)


def debug_enabled() -> bool:
    return current_app.logger.isEnabledFor(logging.DEBUG)


def truncate_debug_value(value, max_length: int = 5000):
    if isinstance(value, str):
        if len(value) <= max_length:
            return value
        return value[:max_length] + "... [truncated]"

    if isinstance(value, list):
        return [truncate_debug_value(item, max_length=max_length) for item in value]

    if isinstance(value, dict):
        return {
            str(key): truncate_debug_value(item, max_length=max_length)
            for key, item in value.items()
        }

    return value


def debug_request_context(payload: dict, endpoint: str) -> dict:
    return {
        "endpoint": endpoint,
        "system_prompt_name": payload.get("system_prompt_name"),
        "language": payload.get("language"),
        "difficulty": payload.get("difficulty"),
        "has_conversation_history": isinstance(payload.get("conversation_history"), list),
        "conversation_history_size": (
            len(payload.get("conversation_history"))
            if isinstance(payload.get("conversation_history"), list)
            else 0
        ),
        "max_question_roundtrips": payload.get("max_question_roundtrips"),
    }


def format_debug_json(payload, max_length: int = 5000) -> str:
    sanitized = truncate_debug_value(payload, max_length=max_length)
    rendered = json.dumps(sanitized, indent=2, ensure_ascii=False, default=str)
    rendered = _format_prepper_json_in_string_fields(rendered)
    return f"{_ANSI_CYAN}{rendered}{_ANSI_RESET}"


def _format_prepper_json_in_string_fields(rendered: str) -> str:
    def replace_string_field(match: re.Match) -> str:
        indent = match.group(1)
        field_name = match.group(2)
        encoded_value = match.group(3)
        trailing_comma = match.group(4)

        try:
            field_value = json.loads(f'"{encoded_value}"')
        except json.JSONDecodeError:
            return match.group(0)

        if _PREPPER_JSON_MARKER not in field_value:
            return match.group(0)

        clean_text, metadata_blocks = _extract_prepper_json_blocks(field_value)
        if not metadata_blocks:
            return match.group(0)

        escaped_clean_text = json.dumps(clean_text, ensure_ascii=False)[1:-1]
        formatted_blocks: list[str] = []
        for metadata_json in metadata_blocks:
            formatted_metadata = json.dumps(metadata_json, indent=2, ensure_ascii=False)
            metadata_lines = "\n".join(
                f"{indent}{line}" for line in formatted_metadata.splitlines()
            )
            formatted_blocks.append(
                f"{indent}{_PREPPER_JSON_MARKER}\n"
                f"{_ANSI_GREEN}{metadata_lines}{_ANSI_RESET}{_ANSI_CYAN}"
            )

        return (
            f'{indent}"{field_name}": "{escaped_clean_text}"\n'
            f"{'\n\n'.join(formatted_blocks)}{trailing_comma}"
        )

    return _STRING_FIELD_PATTERN.sub(replace_string_field, rendered)


def _extract_prepper_json_blocks(raw_reply: str) -> tuple[str, list[dict]]:
    clean_parts: list[str] = []
    metadata_blocks: list[dict] = []
    index = 0

    while True:
        marker_index = raw_reply.find(_PREPPER_JSON_MARKER, index)
        if marker_index == -1:
            clean_parts.append(raw_reply[index:])
            break

        clean_parts.append(raw_reply[index:marker_index])
        json_start = marker_index + len(_PREPPER_JSON_MARKER)
        while json_start < len(raw_reply) and raw_reply[json_start].isspace():
            json_start += 1

        if json_start >= len(raw_reply) or raw_reply[json_start] != "{":
            clean_parts.append(_PREPPER_JSON_MARKER)
            index = marker_index + len(_PREPPER_JSON_MARKER)
            continue

        extracted = _extract_json_object(raw_reply, json_start)
        if extracted is None:
            clean_parts.append(raw_reply[marker_index:])
            break

        json_text, end_index = extracted
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            clean_parts.append(raw_reply[marker_index:end_index])
            index = end_index
            continue

        if isinstance(parsed, dict):
            metadata_blocks.append(parsed)
        else:
            clean_parts.append(raw_reply[marker_index:end_index])

        index = end_index

    return "".join(clean_parts).rstrip(), metadata_blocks


def _extract_json_object(text: str, start_index: int) -> tuple[str, int] | None:
    if start_index >= len(text) or text[start_index] != "{":
        return None

    depth = 0
    in_string = False
    escaping = False

    for index in range(start_index, len(text)):
        char = text[index]
        if in_string:
            if escaping:
                escaping = False
            elif char == "\\":
                escaping = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
            continue

        if char == "}":
            depth -= 1
            if depth == 0:
                return text[start_index:index + 1], index + 1

    return None
