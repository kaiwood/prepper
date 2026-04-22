from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from app import limiter
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


def _resolve_prompt_descriptor(selected_name: str | None = None) -> PromptDescriptor:
    prompt_name = (selected_name or get_default_system_prompt_name()).strip()
    return load_prompt_descriptor(prompt_name)


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

    if "system_prompt" in data:
        return jsonify({"error": "system_prompt is not supported"}), 400

    if system_prompt_name is not None and not isinstance(system_prompt_name, str):
        return jsonify({"error": "system_prompt_name must be a string"}), 400

    if language is not None and not isinstance(language, str):
        return jsonify({"error": "language must be a string"}), 400

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
        reply = get_chat_reply(
            message,
            conversation=conversation,
            system_prompt=descriptor.content,
            language=language,
            temperature=descriptor.temperature,
            top_p=descriptor.top_p,
            frequency_penalty=descriptor.frequency_penalty,
            presence_penalty=descriptor.presence_penalty,
            max_tokens=descriptor.max_tokens,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    return jsonify({"reply": reply})


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

    if "system_prompt" in data:
        return jsonify({"error": "system_prompt is not supported"}), 400

    if system_prompt_name is not None and not isinstance(system_prompt_name, str):
        return jsonify({"error": "system_prompt_name must be a string"}), 400

    if language is not None and not isinstance(language, str):
        return jsonify({"error": "language must be a string"}), 400

    try:
        descriptor = _resolve_prompt_descriptor(system_prompt_name)
    except ValueError as exc:
        if system_prompt_name is not None:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    try:
        reply = get_interview_opener(
            system_prompt=descriptor.content,
            language=language,
            temperature=descriptor.temperature,
            top_p=descriptor.top_p,
            frequency_penalty=descriptor.frequency_penalty,
            presence_penalty=descriptor.presence_penalty,
            max_tokens=descriptor.max_tokens,
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
        }
        for d in descriptors
    ]

    return jsonify({"prompts": prompts_payload, "default": default_prompt})
