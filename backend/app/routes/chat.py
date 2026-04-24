from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from app import limiter
from app.helpers.utils import (
    build_difficulty_instruction,
    resolve_difficulty,
    resolve_model_settings,
    resolve_pass_threshold,
    resolve_prompt_descriptor,
    resolve_roundtrip_limit,
)
from prepper_cli import (
    Conversation,
    get_chat_reply,
    get_interview_opener,
    parse_reply_metadata,
    run_interview_turn,
)

chat_bp = Blueprint("chat", __name__)


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

    message = data.get("message", "").strip()
    conversation_history = data.get("conversation_history")
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

    active_pass_threshold = resolve_pass_threshold(descriptor, resolved_difficulty)

    if descriptor.interview_rating_enabled:
        try:
            turn_result = run_interview_turn(
                message=message,
                conversation=conversation,
                descriptor=descriptor,
                language=language,
                question_limit=question_limit,
                pass_threshold=active_pass_threshold,
                model_settings=model_settings,
                difficulty=resolved_difficulty,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": f"LLM request failed: {exc}"}), 502

        response_payload = {
            "reply": turn_result["reply"],
            "interview_enabled": True,
            "interview_complete": turn_result["interview_complete"],
            "counted_question_roundtrips": turn_result["question_count"],
            "question_roundtrips_limit": turn_result["question_limit"],
            "pass_threshold": turn_result["pass_threshold"],
            "current_turn_type": turn_result["turn_type"],
            "metadata_warning": turn_result["metadata_warning"],
        }
        if resolved_difficulty is not None:
            response_payload["difficulty"] = resolved_difficulty
        if turn_result["final_result"] is not None:
            response_payload["final_result"] = turn_result["final_result"]
    else:
        system_prompt = descriptor.content
        if resolved_difficulty is not None:
            system_prompt += build_difficulty_instruction(resolved_difficulty)

        try:
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
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": f"LLM request failed: {exc}"}), 502

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
    system_prompt_name = data.get("system_prompt_name")
    language = data.get("language")
    difficulty = data.get("difficulty")

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

    system_prompt = descriptor.content
    if resolved_difficulty is not None:
        system_prompt += build_difficulty_instruction(resolved_difficulty)

    try:
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

    parsed = parse_reply_metadata(reply)
    return jsonify({"reply": parsed["reply"]})


