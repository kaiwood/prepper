from __future__ import annotations

from typing import Any

from .config import load_config, resolve_model_name


def build_chat_model(
    *,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    max_tokens: int | None = None,
    timeout: float | int | None = 60,
    max_retries: int | None = 1,
    model_kwargs: dict[str, Any] | None = None,
):
    """Build the shared LangChain chat model for OpenRouter-compatible providers."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - depends on installed env
        raise RuntimeError("langchain-openai is required for LLM chat") from exc

    config = load_config()
    request_model_kwargs = dict(model_kwargs or {})
    for key, value in {
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
    }.items():
        if value is not None:
            request_model_kwargs[key] = value

    kwargs: dict[str, Any] = {
        "model": resolve_model_name(model),
        "api_key": config.api_key,
        "base_url": config.base_url,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if timeout is not None:
        kwargs["timeout"] = timeout
    if max_retries is not None:
        kwargs["max_retries"] = max_retries
    if request_model_kwargs:
        kwargs["model_kwargs"] = request_model_kwargs

    return ChatOpenAI(**kwargs)


def coerce_llm_content(content: Any) -> str:
    """Normalize LangChain/OpenAI message content into plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)
