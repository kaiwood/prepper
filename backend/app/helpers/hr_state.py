from __future__ import annotations

from typing import Any

from app.helpers.state_cleanup import (
    cleanup_state_metadata,
    cleanup_state_store,
    mark_state_seen,
    state_timestamps,
)
from prepper_cli.hr_context import HrContext

HR_CONTEXTS: dict[str, HrContext] = {}
HR_CONTEXT_METADATA: dict[str, dict[str, Any]] = {}
HR_INTERVIEW_SESSIONS: dict[str, dict[str, Any]] = {}


def clear_hr_state() -> None:
    HR_CONTEXTS.clear()
    HR_CONTEXT_METADATA.clear()
    HR_INTERVIEW_SESSIONS.clear()


def cleanup_hr_state() -> None:
    for context_id in list(HR_CONTEXT_METADATA):
        if context_id not in HR_CONTEXTS:
            HR_CONTEXT_METADATA.pop(context_id, None)

    removed_context_ids = cleanup_state_metadata(HR_CONTEXT_METADATA)
    for context_id in removed_context_ids:
        HR_CONTEXTS.pop(context_id, None)

    cleanup_state_store(HR_INTERVIEW_SESSIONS)
    if removed_context_ids:
        removed_context_ids_set = set(removed_context_ids)
        for interview_id, session in list(HR_INTERVIEW_SESSIONS.items()):
            if session.get("context_id") in removed_context_ids_set:
                HR_INTERVIEW_SESSIONS.pop(interview_id, None)


def store_hr_context(context: HrContext) -> None:
    HR_CONTEXTS[context.context_id] = context
    HR_CONTEXT_METADATA[context.context_id] = state_timestamps()
    cleanup_hr_state()


def get_stored_hr_context(context_id: str) -> HrContext | None:
    return HR_CONTEXTS.get(context_id)


def require_stored_context(context_id: str) -> HrContext:
    context = get_stored_hr_context(context_id)
    if context is None:
        raise ValueError("invalid context_id")
    metadata = HR_CONTEXT_METADATA.get(context_id)
    if metadata is None:
        HR_CONTEXT_METADATA[context_id] = state_timestamps()
    else:
        mark_state_seen(metadata)
    return context


def store_hr_interview_session(interview_id: str, session: dict[str, Any]) -> None:
    HR_INTERVIEW_SESSIONS[interview_id] = session
    cleanup_hr_state()


def get_hr_interview_session(interview_id: str) -> dict[str, Any] | None:
    return HR_INTERVIEW_SESSIONS.get(interview_id)
