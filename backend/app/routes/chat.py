import logging
import os
import uuid
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin
from app import limiter
from app.helpers.debug import debug_enabled, debug_request_context, format_debug_json
from app.helpers.utils import (
    resolve_difficulty,
    resolve_model_settings,
    resolve_prompt_descriptor,
    resolve_roundtrip_limit,
)
from app.helpers.validation import (
    InputLengthError,
    input_length_error_payload,
    validate_string_length,
)
from app.helpers.state_cleanup import (
    cleanup_state_store,
    mark_state_created,
    mark_state_seen,
)
from prepper_cli import (
    Conversation,
    get_chat_reply,
    get_interview_opener,
    parse_reply_metadata,
    resolve_pass_threshold,
    run_interview_turn,
)
from prepper_cli.structured_logging import exception_log_fields, log_structured_event
from prepper_cli.interview_prompts import (
    build_forced_closing_system_prompt,
    build_interview_opener_system_prompt,
    build_prompt_with_difficulty,
)

chat_bp = Blueprint("chat", __name__)

_FALLBACK_CLOSING_REPLY = "Thank you for your time today. The interview is now over."
_CHAT_TEXT_LIMITS = {
    "message": 8_000,
    "current_question": 8_000,
    "conversation_history.content": 8_000,
    "system_prompt_name": 100,
    "language": 32,
    "difficulty": 32,
    "interview_id": 128,
}
_INTERVIEW_SESSIONS: dict[str, dict[str, Any]] = {}


def _cleanup_interview_sessions() -> None:
    cleanup_state_store(_INTERVIEW_SESSIONS)


def _presentation_mode_enabled() -> bool:
    return os.environ.get("PREPPER_PRESENTATION_MODE") == "1"


def _build_candidate_answer_system_prompt(descriptor, difficulty: str | None) -> str:
    difficulty_line = (
        f"Interview difficulty: {difficulty}."
        if difficulty
        else "Interview difficulty: unspecified."
    )
    return (
        "You are the candidate in a software interview simulation.\n"
        f"Interview style: {descriptor.name}.\n"
        f"{difficulty_line}\n"
        "Draft a short, credible answer to the interviewer's current question.\n"
        "Answer in first person as the candidate.\n"
        "Keep the answer to 2-4 short sentences and under 90 words.\n"
        "Prefer one clear example or reasoning path over a broad checklist.\n"
        "Do not use bullet points, headings, preambles, or closing summaries.\n"
        "Do not mention that you are an AI, a helper, or drafting text.\n"
        "Return only the candidate answer, ready to place in the chat input."
    )


def _build_forced_closing_reply(
    descriptor,
    language: str | None,
    model_settings: dict[str, float | int],
    question_count: int,
    question_limit: int,
    difficulty: str | None,
) -> str:
    raw_reply = get_chat_reply(
        "Runtime override: end the interview now and provide the final closing statement.",
        conversation=None,
        system_prompt=build_forced_closing_system_prompt(
            descriptor=descriptor,
            difficulty=difficulty,
            question_count=question_count,
            question_limit=question_limit,
        ),
        language=language,
        temperature=model_settings["temperature"],
        top_p=model_settings["top_p"],
        frequency_penalty=model_settings["frequency_penalty"],
        presence_penalty=model_settings["presence_penalty"],
        max_tokens=model_settings["max_tokens"],
    )

    parsed = parse_reply_metadata(raw_reply)
    reply = parsed["reply"].strip()
    if reply:
        return reply

    return _FALLBACK_CLOSING_REPLY


def _build_interview_response_payload(
    *,
    interview_id: str,
    turn_result: dict[str, Any],
    difficulty: str | None,
) -> dict[str, Any]:
    response_payload = {
        "reply": turn_result["reply"],
        "interview_id": interview_id,
        "interview_enabled": True,
        "interview_complete": turn_result["interview_complete"],
        "counted_question_roundtrips": turn_result["question_count"],
        "question_roundtrips_limit": turn_result["question_limit"],
        "pass_threshold": turn_result["pass_threshold"],
        "current_turn_type": turn_result["turn_type"],
        "metadata_warning": turn_result["metadata_warning"],
    }
    if difficulty is not None:
        response_payload["difficulty"] = difficulty
    if turn_result.get("final_result") is not None:
        response_payload["final_result"] = turn_result["final_result"]
    return response_payload


def _log_chat_route_failure(operation: str, exc: Exception) -> None:
    log_structured_event(
        "route_failure",
        status="error",
        level=logging.WARNING,
        logger=current_app.logger,
        route=request.path,
        method=request.method,
        operation=operation,
        **exception_log_fields(exc),
    )


@chat_bp.route("/api/chat", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat_options():
    return "", 204


@chat_bp.route("/api/chat/start", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat_start_options():
    return "", 204


@chat_bp.route("/api/presentation/candidate-answer", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def presentation_candidate_answer_options():
    return "", 204


@chat_bp.post("/api/presentation/candidate-answer")
@limiter.limit("10 per minute")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def presentation_candidate_answer():
    if not _presentation_mode_enabled():
        return jsonify({"error": "presentation mode is not enabled"}), 404

    data = request.get_json(silent=True) or {}
    raw_current_question = data.get("current_question", "")
    system_prompt_name = data.get("system_prompt_name")
    language = data.get("language")
    difficulty = data.get("difficulty")

    if not isinstance(raw_current_question, str):
        return jsonify({"error": "current_question must be a string"}), 400
    current_question = raw_current_question.strip()

    if not current_question:
        return jsonify({"error": "current_question is required"}), 400

    try:
        _validate_text_length(raw_current_question, "current_question")
    except InputLengthError as exc:
        return jsonify(input_length_error_payload(exc)), 400

    if system_prompt_name is not None and not isinstance(system_prompt_name, str):
        return jsonify({"error": "system_prompt_name must be a string"}), 400

    if language is not None and not isinstance(language, str):
        return jsonify({"error": "language must be a string"}), 400

    if difficulty is not None and not isinstance(difficulty, str):
        return jsonify({"error": "difficulty must be a string"}), 400

    try:
        for field_name, value in {
            "system_prompt_name": system_prompt_name,
            "language": language,
            "difficulty": difficulty,
        }.items():
            if isinstance(value, str):
                _validate_text_length(value, field_name)
    except InputLengthError as exc:
        return jsonify(input_length_error_payload(exc)), 400

    try:
        descriptor = resolve_prompt_descriptor(system_prompt_name)
    except ValueError as exc:
        if system_prompt_name is not None:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    try:
        resolved_difficulty = resolve_difficulty(difficulty, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        model_settings = resolve_model_settings(data, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        answer = get_chat_reply(
            current_question,
            conversation=None,
            system_prompt=_build_candidate_answer_system_prompt(
                descriptor,
                resolved_difficulty,
            ),
            language=language,
            temperature=model_settings["temperature"],
            top_p=model_settings["top_p"],
            frequency_penalty=model_settings["frequency_penalty"],
            presence_penalty=model_settings["presence_penalty"],
            max_tokens=min(model_settings["max_tokens"], 500),
            treat_input_as_untrusted=True,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        _log_chat_route_failure("presentation_candidate_answer_llm", exc)
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    return jsonify({"answer": answer})


@chat_bp.post("/api/chat")
@limiter.limit("10 per minute")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat():
    _cleanup_interview_sessions()
    data = request.get_json(silent=True) or {}
    debug_mode = debug_enabled()

    raw_message = data.get("message", "")
    if not isinstance(raw_message, str):
        return jsonify({"error": "message must be a string"}), 400
    message = raw_message.strip()
    conversation_history = data.get("conversation_history")
    system_prompt_name = data.get("system_prompt_name")
    language = data.get("language")
    difficulty = data.get("difficulty")
    max_question_roundtrips = data.get("max_question_roundtrips")
    interview_id = data.get("interview_id")

    if "system_prompt" in data:
        return jsonify({"error": "system_prompt is not supported"}), 400

    if system_prompt_name is not None and not isinstance(system_prompt_name, str):
        return jsonify({"error": "system_prompt_name must be a string"}), 400

    if language is not None and not isinstance(language, str):
        return jsonify({"error": "language must be a string"}), 400

    if difficulty is not None and not isinstance(difficulty, str):
        return jsonify({"error": "difficulty must be a string"}), 400

    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        _validate_text_length(raw_message, "message")
        for field_name, value in {
            "system_prompt_name": system_prompt_name,
            "language": language,
            "difficulty": difficulty,
            "interview_id": interview_id,
        }.items():
            if isinstance(value, str):
                _validate_text_length(value, field_name)
        _validate_conversation_history_lengths(conversation_history)
    except InputLengthError as exc:
        return jsonify(input_length_error_payload(exc)), 400

    conversation = None
    if conversation_history is not None:
        if not isinstance(conversation_history, list):
            return jsonify({"error": "conversation_history must be a list"}), 400
        try:
            conversation = Conversation.from_messages(conversation_history)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    try:
        descriptor = resolve_prompt_descriptor(system_prompt_name)
    except ValueError as exc:
        if system_prompt_name is not None:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    try:
        question_limit = resolve_roundtrip_limit(max_question_roundtrips, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        resolved_difficulty = resolve_difficulty(difficulty, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        model_settings = resolve_model_settings(data, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if debug_mode:
        current_app.logger.debug(
            "prepper_cli request context:\n%s",
            format_debug_json(debug_request_context(data, "/api/chat")),
        )
        current_app.logger.debug(
            "prepper_cli model settings:\n%s",
            format_debug_json(model_settings),
        )

    active_pass_threshold = resolve_pass_threshold(descriptor, resolved_difficulty)

    if descriptor.interview_rating_enabled:
        if not isinstance(interview_id, str) or not interview_id.strip():
            return jsonify({"error": "interview_id is required for interview chat"}), 400

        session = _INTERVIEW_SESSIONS.get(interview_id)
        if session is None:
            return jsonify({"error": "invalid interview_id"}), 400

        if session["descriptor"].id != descriptor.id:
            return jsonify(
                {
                    "error": "interview_id does not match the selected system prompt"
                }
            ), 400

        mark_state_seen(session)

        if session["interview_complete"]:
            turn_result = {
                "reply": session["closing_reply"],
                "turn_type": "other",
                "question_count": session["question_count"],
                "question_limit": session["question_limit"],
                "interview_complete": True,
                "pass_threshold": session["pass_threshold"],
                "metadata_warning": False,
                "final_result": session.get("final_result"),
            }
            return jsonify(
                _build_interview_response_payload(
                    interview_id=interview_id,
                    turn_result=turn_result,
                    difficulty=session["difficulty"],
                )
            )

        try:
            interview_kwargs = {
                "message": message,
                "conversation": session["conversation"],
                "descriptor": session["descriptor"],
                "language": session["language"],
                "question_limit": session["question_limit"],
                "pass_threshold": session["pass_threshold"],
                "model_settings": session["model_settings"],
                "difficulty": session["difficulty"],
                "treat_candidate_input_as_untrusted": True,
                "prior_question_count": session["question_count"],
            }
            if debug_mode:
                interview_kwargs["include_diagnostics"] = True
            turn_result = run_interview_turn(**interview_kwargs)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            _log_chat_route_failure("chat_interview_turn_llm", exc)
            return jsonify({"error": f"LLM request failed: {exc}"}), 502

        if turn_result["interview_complete"] and turn_result["turn_type"] != "other":
            try:
                forced_reply = _build_forced_closing_reply(
                    descriptor=session["descriptor"],
                    language=session["language"],
                    model_settings=session["model_settings"],
                    question_count=turn_result["question_count"],
                    question_limit=session["question_limit"],
                    difficulty=session["difficulty"],
                )
                turn_result["reply"] = forced_reply
                turn_result["turn_type"] = "other"
                turn_result["metadata_warning"] = True
            except Exception as exc:
                _log_chat_route_failure("chat_forced_closing_llm", exc)
                return jsonify({"error": f"LLM request failed: {exc}"}), 502

        if debug_mode:
            current_app.logger.debug(
                "prepper_cli interview diagnostics:\n%s",
                format_debug_json(turn_result.get("debug", {})),
            )

        session["question_count"] = turn_result["question_count"]
        session["interview_complete"] = bool(turn_result["interview_complete"])
        if session["interview_complete"]:
            session["final_result"] = turn_result.get("final_result")
            session["closing_reply"] = turn_result["reply"]

        turn_result.pop("debug", None)
        response_payload = _build_interview_response_payload(
            interview_id=interview_id,
            turn_result=turn_result,
            difficulty=session["difficulty"],
        )
    else:
        system_prompt = build_prompt_with_difficulty(descriptor, resolved_difficulty)

        try:
            if debug_mode:
                reply, chat_diagnostics = get_chat_reply(
                    message,
                    conversation=conversation,
                    system_prompt=system_prompt,
                    language=language,
                    temperature=model_settings["temperature"],
                    top_p=model_settings["top_p"],
                    frequency_penalty=model_settings["frequency_penalty"],
                    presence_penalty=model_settings["presence_penalty"],
                    max_tokens=model_settings["max_tokens"],
                    include_diagnostics=True,
                    treat_input_as_untrusted=True,
                )
            else:
                reply = get_chat_reply(
                    message,
                    conversation=conversation,
                    system_prompt=system_prompt,
                    language=language,
                    temperature=model_settings["temperature"],
                    top_p=model_settings["top_p"],
                    frequency_penalty=model_settings["frequency_penalty"],
                    presence_penalty=model_settings["presence_penalty"],
                    max_tokens=model_settings["max_tokens"],
                    treat_input_as_untrusted=True,
                )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            _log_chat_route_failure("chat_reply_llm", exc)
            return jsonify({"error": f"LLM request failed: {exc}"}), 502

        if debug_mode:
            current_app.logger.debug(
                "prepper_cli chat diagnostics:\n%s",
                format_debug_json(chat_diagnostics),
            )

        response_payload = {"reply": reply}

    return jsonify(response_payload)


@chat_bp.post("/api/chat/start")
@limiter.limit("10 per minute")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat_start():
    _cleanup_interview_sessions()
    data = request.get_json(silent=True) or {}
    debug_mode = debug_enabled()
    system_prompt_name = data.get("system_prompt_name")
    language = data.get("language")
    difficulty = data.get("difficulty")
    max_question_roundtrips = data.get("max_question_roundtrips")

    if "system_prompt" in data:
        return jsonify({"error": "system_prompt is not supported"}), 400

    if system_prompt_name is not None and not isinstance(system_prompt_name, str):
        return jsonify({"error": "system_prompt_name must be a string"}), 400

    if language is not None and not isinstance(language, str):
        return jsonify({"error": "language must be a string"}), 400

    if difficulty is not None and not isinstance(difficulty, str):
        return jsonify({"error": "difficulty must be a string"}), 400

    try:
        for field_name, value in {
            "system_prompt_name": system_prompt_name,
            "language": language,
            "difficulty": difficulty,
        }.items():
            if isinstance(value, str):
                _validate_text_length(value, field_name)
    except InputLengthError as exc:
        return jsonify(input_length_error_payload(exc)), 400

    try:
        descriptor = resolve_prompt_descriptor(system_prompt_name)
    except ValueError as exc:
        if system_prompt_name is not None:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    try:
        resolved_difficulty = resolve_difficulty(difficulty, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        model_settings = resolve_model_settings(data, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if descriptor.interview_rating_enabled:
        try:
            question_limit = resolve_roundtrip_limit(max_question_roundtrips, descriptor)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        active_pass_threshold = resolve_pass_threshold(descriptor, resolved_difficulty)

    if debug_mode:
        current_app.logger.debug(
            "prepper_cli request context:\n%s",
            format_debug_json(debug_request_context(data, "/api/chat/start")),
        )
        current_app.logger.debug(
            "prepper_cli model settings:\n%s",
            format_debug_json(model_settings),
        )

    system_prompt = build_interview_opener_system_prompt(
        descriptor,
        resolved_difficulty,
    )

    try:
        if debug_mode:
            reply, chat_diagnostics = get_interview_opener(
                system_prompt=system_prompt,
                language=language,
                temperature=model_settings["temperature"],
                top_p=model_settings["top_p"],
                frequency_penalty=model_settings["frequency_penalty"],
                presence_penalty=model_settings["presence_penalty"],
                max_tokens=model_settings["max_tokens"],
                include_diagnostics=True,
            )
        else:
            reply = get_interview_opener(
                system_prompt=system_prompt,
                language=language,
                temperature=model_settings["temperature"],
                top_p=model_settings["top_p"],
                frequency_penalty=model_settings["frequency_penalty"],
                presence_penalty=model_settings["presence_penalty"],
                max_tokens=model_settings["max_tokens"],
            )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        _log_chat_route_failure("chat_start_llm", exc)
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    if debug_mode:
        current_app.logger.debug(
            "prepper_cli opener diagnostics:\n%s",
            format_debug_json(chat_diagnostics),
        )

    parsed = parse_reply_metadata(reply)

    if descriptor.interview_rating_enabled:
        interview_id = uuid.uuid4().hex
        session_conversation = Conversation()
        session_conversation.add_assistant_reply(parsed["reply"])
        metadata = parsed["metadata"] if isinstance(parsed.get("metadata"), dict) else {}
        metadata_turn_type = metadata.get("turn_type")
        question_count = (
            1
            if isinstance(metadata_turn_type, str)
            and metadata_turn_type.strip().upper() == "QUESTION"
            else 0
        )
        metadata_complete = metadata.get("interview_complete")
        interview_complete = bool(metadata_complete) if isinstance(metadata_complete, bool) else False

        session = {
            "descriptor": descriptor,
            "conversation": session_conversation,
            "language": language,
            "difficulty": resolved_difficulty,
            "question_limit": question_limit,
            "question_count": question_count,
            "pass_threshold": active_pass_threshold,
            "model_settings": model_settings,
            "interview_complete": interview_complete,
            "closing_reply": parsed["reply"] if interview_complete else _FALLBACK_CLOSING_REPLY,
            "final_result": None,
        }
        mark_state_created(session)
        _INTERVIEW_SESSIONS[interview_id] = session
        _cleanup_interview_sessions()

        response_payload = {
            "reply": parsed["reply"],
            "interview_id": interview_id,
            "interview_enabled": True,
            "interview_complete": interview_complete,
            "counted_question_roundtrips": question_count,
            "question_roundtrips_limit": question_limit,
            "pass_threshold": active_pass_threshold,
        }
        if resolved_difficulty is not None:
            response_payload["difficulty"] = resolved_difficulty
        return jsonify(response_payload)

    return jsonify({"reply": parsed["reply"]})


def _validate_text_length(value: str, field_name: str) -> None:
    max_length = _CHAT_TEXT_LIMITS.get(field_name)
    if max_length is not None:
        validate_string_length(value, field=field_name, max_length=max_length)


def _validate_conversation_history_lengths(conversation_history: Any) -> None:
    if not isinstance(conversation_history, list):
        return
    for index, item in enumerate(conversation_history):
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if isinstance(content, str):
            validate_string_length(
                content,
                field=f"conversation_history[{index}].content",
                max_length=_CHAT_TEXT_LIMITS["conversation_history.content"],
            )
