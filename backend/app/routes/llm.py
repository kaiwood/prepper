from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from prepper_cli import Conversation, get_chat_reply
from prepper_cli.system_prompts import (
    get_default_system_prompt_name,
    load_system_prompt,
)

llm_bp = Blueprint("llm", __name__)


def _resolve_system_prompt_text(selected_name: str | None = None) -> str:
    prompt_name = (selected_name or get_default_system_prompt_name()).strip()
    return load_system_prompt(prompt_name)


@llm_bp.route("/api/chat", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat_options():
    return "", 204


@llm_bp.post("/api/chat")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def chat():
    data = request.get_json(silent=True) or {}

    if "system_prompt" in data or "system_prompt_name" in data:
        return jsonify({"error": "system prompt is only supported in the CLI"}), 400

    message = data.get("message", "").strip()
    conversation_history = data.get("conversation_history")

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
        system_prompt_text = _resolve_system_prompt_text()
    except ValueError as exc:
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    try:
        reply = get_chat_reply(
            message,
            conversation=conversation,
            system_prompt=system_prompt_text,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"LLM request failed: {exc}"}), 502

    return jsonify({"reply": reply})
