from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from app import limiter
from app.helpers.utils import (
    build_difficulty_instruction,
    build_runtime_interview_instruction,
    build_scoring_input,
    build_scoring_system_prompt,
    classify_assistant_turn,
    coerce_string_list,
    clamp_score,
    count_scored_questions,
    extract_json_object,
    parse_scoring_payload,
    resolve_difficulty,
    resolve_model_setting_override,
    resolve_model_settings,
    resolve_pass_threshold,
    resolve_prompt_descriptor,
    resolve_roundtrip_limit,
    score_interview,
)
from prepper_cli import (
    Conversation,
    PromptDescriptor,
    get_chat_reply,
    get_interview_opener,
    load_prompt_descriptor,
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

    prior_question_count = 0
    system_prompt = descriptor.content
    if resolved_difficulty is not None:
        system_prompt += build_difficulty_instruction(resolved_difficulty)

    if descriptor.interview_rating_enabled:
        prior_question_count = count_scored_questions(conversation, language)
        system_prompt += build_runtime_interview_instruction(
            descriptor, prior_question_count, question_limit
        )

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
    if descriptor.interview_rating_enabled:
        current_turn_kind = classify_assistant_turn(reply, language)
        count_after = prior_question_count + (1 if current_turn_kind == "question" else 0)
        interview_complete = prior_question_count >= question_limit

        interview_status = {
            "enabled": True,
            "is_completed": interview_complete,
            "counted_question_roundtrips": count_after,
            "question_roundtrips_limit": question_limit,
            "pass_threshold": active_pass_threshold,
            "current_turn_type": current_turn_kind,
        }
        if resolved_difficulty is not None:
            interview_status["difficulty"] = resolved_difficulty

        if interview_complete:
            try:
                scoring_conversation = conversation or Conversation.from_messages(
                    [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": reply},
                    ]
                )
                interview_status["rating"] = score_interview(
                    scoring_conversation,
                    descriptor,
                    language,
                    active_pass_threshold,
                )
            except Exception as exc:
                return jsonify({"error": f"LLM request failed: {exc}"}), 502

        response_payload["interview_status"] = interview_status

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

    return jsonify({"reply": reply})


