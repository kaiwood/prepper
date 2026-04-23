from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from app import limiter
from app.helpers.utils import (
    _build_difficulty_instruction,
    _build_runtime_interview_instruction,
    _build_scoring_input,
    _build_scoring_system_prompt,
    _classify_assistant_turn,
    _coerce_string_list,
    _clamp_score,
    _count_scored_questions,
    _extract_json_object,
    _parse_scoring_payload,
    _resolve_difficulty,
    _resolve_model_setting_override,
    _resolve_model_settings,
    _resolve_pass_threshold,
    _resolve_prompt_descriptor,
    _resolve_roundtrip_limit,
    _score_interview,
)
from prepper_cli import (
    Conversation,
    PromptDescriptor,
    get_chat_reply,
    get_default_system_prompt_name,
    get_interview_opener,
    list_prompt_descriptors,
    list_system_prompt_names,
    load_prompt_descriptor,
)

llm_bp = Blueprint("llm", __name__)


@llm_bp.route("/api/chat", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat_options():
    return "", 204


@llm_bp.route("/api/chat/start", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat_start_options():
    return "", 204


@llm_bp.post("/api/chat")
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
        descriptor = _resolve_prompt_descriptor(system_prompt_name)
    except ValueError as exc:
        if system_prompt_name is not None:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    try:
        question_limit = _resolve_roundtrip_limit(max_question_roundtrips, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        resolved_difficulty = _resolve_difficulty(difficulty, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        model_settings = _resolve_model_settings(data, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    active_pass_threshold = _resolve_pass_threshold(descriptor, resolved_difficulty)

    prior_question_count = 0
    system_prompt = descriptor.content
    if resolved_difficulty is not None:
        system_prompt += _build_difficulty_instruction(resolved_difficulty)

    if descriptor.interview_rating_enabled:
        prior_question_count = _count_scored_questions(conversation, language)
        system_prompt += _build_runtime_interview_instruction(
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
        current_turn_kind = _classify_assistant_turn(reply, language)
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
                interview_status["rating"] = _score_interview(
                    scoring_conversation,
                    descriptor,
                    language,
                    active_pass_threshold,
                )
            except Exception as exc:
                return jsonify({"error": f"LLM request failed: {exc}"}), 502

        response_payload["interview_status"] = interview_status

    return jsonify(response_payload)


@llm_bp.post("/api/chat/start")
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
        descriptor = _resolve_prompt_descriptor(system_prompt_name)
    except ValueError as exc:
        if system_prompt_name is not None:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    try:
        resolved_difficulty = _resolve_difficulty(difficulty, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        model_settings = _resolve_model_settings(data, descriptor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    system_prompt = descriptor.content
    if resolved_difficulty is not None:
        system_prompt += _build_difficulty_instruction(resolved_difficulty)

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


@llm_bp.get("/api/prompts")
@limiter.limit("20 per minute")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def prompts():
    available_names = list_system_prompt_names()
    default_prompt = get_default_system_prompt_name().strip()

    if default_prompt not in available_names:
        return jsonify({"error": f"LLM request failed: Unknown system prompt '{default_prompt}'"}), 502

    descriptors = list_prompt_descriptors()
    prompts_payload = [
        {
            "id": d.id,
            "name": d.name,
            "temperature": d.temperature,
            "top_p": d.top_p,
            "frequency_penalty": d.frequency_penalty,
            "presence_penalty": d.presence_penalty,
            "max_tokens": d.max_tokens,
            "interview_rating_enabled": d.interview_rating_enabled,
            "default_question_roundtrips": d.default_question_roundtrips,
            "min_question_roundtrips": d.min_question_roundtrips,
            "max_question_roundtrips": d.max_question_roundtrips,
            "pass_threshold": d.pass_threshold,
            "rubric_criteria": list(d.rubric_criteria),
            "difficulty_enabled": d.difficulty_enabled,
            "difficulty_levels": list(d.difficulty_levels),
            "default_difficulty": d.default_difficulty,
        }
        for d in descriptors
    ]

    return jsonify({"prompts": prompts_payload, "default": default_prompt})
