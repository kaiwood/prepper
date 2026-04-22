"""Shared OpenRouter client utilities and CLI for Prepper."""

from .chat import get_chat_reply, get_interview_opener
from .conversation import Conversation
from .system_prompts import (
    PromptDescriptor,
    get_default_system_prompt_name,
    list_prompt_descriptors,
    list_system_prompt_names,
    load_prompt_descriptor,
    load_system_prompt,
)

__all__ = [
    "get_chat_reply",
    "get_interview_opener",
    "Conversation",
    "PromptDescriptor",
    "get_default_system_prompt_name",
    "list_prompt_descriptors",
    "list_system_prompt_names",
    "load_prompt_descriptor",
    "load_system_prompt",
]
