"""Shared OpenRouter client utilities and CLI for Prepper."""

from .chat import get_chat_reply
from .conversation import Conversation
from .system_prompts import (
    get_default_system_prompt_name,
    list_system_prompt_names,
    load_system_prompt,
)

__all__ = [
    "get_chat_reply",
    "Conversation",
    "get_default_system_prompt_name",
    "list_system_prompt_names",
    "load_system_prompt",
]
