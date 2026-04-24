from typing import Any

from .client import get_client
from .conversation import Conversation

_INTERVIEW_OPENER_MESSAGE = (
    "Begin the interview now. Ask the first interview question and wait for the candidate's response."
)
_LANGUAGE_NAMES = {
    "en": "English",
    "de": "German",
}


def _request_chat_reply(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    max_tokens: int | None = None,
    include_diagnostics: bool = False,
) -> str | tuple[str, dict[str, Any]]:
    client, model = get_client()

    kwargs: dict = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if top_p is not None:
        kwargs["top_p"] = top_p
    if frequency_penalty is not None:
        kwargs["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        kwargs["presence_penalty"] = presence_penalty
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    response = client.chat.completions.create(**kwargs)

    raw_reply = response.choices[0].message.content or ""
    normalized_reply = raw_reply.strip()

    if not include_diagnostics:
        return normalized_reply

    return normalized_reply, {
        "request": {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "max_tokens": max_tokens,
        },
        "raw_response": _serialize_response(response),
        "raw_reply": raw_reply,
        "normalized_reply": normalized_reply,
    }


def _serialize_response(response: Any) -> Any:
    if hasattr(response, "model_dump") and callable(response.model_dump):
        try:
            return response.model_dump()
        except Exception:
            pass

    if hasattr(response, "dict") and callable(response.dict):
        try:
            return response.dict()
        except Exception:
            pass

    return str(response)


def _build_language_prompt(language: str | None) -> str | None:
    normalized_language = (language or "").strip().lower()
    language_name = _LANGUAGE_NAMES.get(normalized_language)
    if language_name is None:
        return None

    return (
        f"Respond in {language_name}. Keep the full response in {language_name} unless "
        "the user explicitly asks to switch language."
    )


def _prepend_system_prompts(
    messages: list[dict[str, str]],
    language: str | None,
    system_prompt: str | None,
) -> list[dict[str, str]]:
    prefixed_messages: list[dict[str, str]] = []

    language_prompt = _build_language_prompt(language)
    if language_prompt:
        prefixed_messages.append(
            {"role": "system", "content": language_prompt})

    normalized_system_prompt = (system_prompt or "").strip()
    if normalized_system_prompt:
        prefixed_messages.append(
            {"role": "system", "content": normalized_system_prompt})

    return prefixed_messages + messages if prefixed_messages else messages


def get_chat_reply(
    message: str,
    conversation: Conversation | None = None,
    history_limit: int = 10,
    system_prompt: str | None = None,
    language: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    max_tokens: int | None = None,
    conversation_reply_override: str | None = None,
    include_diagnostics: bool = False,
) -> str | tuple[str, dict[str, Any]]:
    prompt = message.strip()
    if not prompt:
        raise ValueError("message is required")

    messages = [{"role": "user", "content": prompt}]
    if conversation is not None and history_limit > 1:
        context_messages = conversation.get_recent_messages(
            limit=history_limit - 1)
        messages = context_messages + messages

    messages = _prepend_system_prompts(
        messages, language=language, system_prompt=system_prompt)

    chat_result = _request_chat_reply(
        messages,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        max_tokens=max_tokens,
        include_diagnostics=include_diagnostics,
    )

    diagnostics = None
    if include_diagnostics:
        normalized_reply, diagnostics = chat_result
    else:
        normalized_reply = chat_result

    if conversation is not None:
        conversation.add_user_message(prompt)
        conversation.add_assistant_reply(
            conversation_reply_override
            if conversation_reply_override is not None
            else normalized_reply
        )

    if include_diagnostics and diagnostics is not None:
        diagnostics["conversation_updated"] = conversation is not None
        return normalized_reply, diagnostics

    return normalized_reply


def get_interview_opener(
    system_prompt: str | None = None,
    language: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    max_tokens: int | None = None,
    include_diagnostics: bool = False,
) -> str | tuple[str, dict[str, Any]]:
    messages = [{"role": "user", "content": _INTERVIEW_OPENER_MESSAGE}]
    messages = _prepend_system_prompts(
        messages, language=language, system_prompt=system_prompt)

    return _request_chat_reply(
        messages,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        max_tokens=max_tokens,
        include_diagnostics=include_diagnostics,
    )
