"""Shared OpenRouter client utilities and CLI for Prepper."""

from .chat import get_chat_reply, get_interview_opener
from .conversation import Conversation
from .interview import (
    build_difficulty_instruction,
    build_runtime_interview_instruction,
    classify_assistant_turn,
    clamp_score,
    coerce_string_list,
    count_scored_questions,
    extract_json_object,
    parse_reply_metadata,
    parse_scoring_payload,
    resolve_pass_threshold,
    run_interview_turn,
    score_interview,
)
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
    "build_difficulty_instruction",
    "build_runtime_interview_instruction",
    "classify_assistant_turn",
    "clamp_score",
    "coerce_string_list",
    "count_scored_questions",
    "extract_json_object",
    "parse_reply_metadata",
    "parse_scoring_payload",
    "resolve_pass_threshold",
    "run_interview_turn",
    "score_interview",
    "PromptDescriptor",
    "get_default_system_prompt_name",
    "list_prompt_descriptors",
    "list_system_prompt_names",
    "load_prompt_descriptor",
    "load_system_prompt",
]
