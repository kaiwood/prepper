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
from prepper_cli import (
    Conversation,
    get_chat_reply,
    get_interview_opener,
    parse_reply_metadata,
    resolve_pass_threshold,
    run_interview_turn,
)
from prepper_cli.interview_prompts import (
    build_forced_closing_system_prompt,
    build_interview_opener_system_prompt,
    build_prompt_with_difficulty,
)

chat_bp = Blueprint("chat", __name__)

_FALLBACK_CLOSING_REPLY = "Thank you for your time today. The interview is now over."
_INTERVIEW_SESSIONS: dict[str, dict[str, Any]] = {}


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


@chat_bp.post("/api/chat")
@limiter.limit("10 per minute")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat():
    data = request.get_json(silent=True) or {}
    debug_mode = debug_enabled()

    message = data.get("message", "").strip()
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

        _INTERVIEW_SESSIONS[interview_id] = {
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
