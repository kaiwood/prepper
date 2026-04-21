"""Shared OpenRouter client utilities and CLI for Prepper."""

from .chat import get_chat_reply
from .conversation import Conversation

__all__ = ["get_chat_reply", "Conversation"]
