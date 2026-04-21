import os
from flask import Blueprint, request, jsonify
from openai import OpenAI

llm_bp = Blueprint("llm", __name__)


def _get_client():
    return OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )


@llm_bp.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "message is required"}), 400

    client = _get_client()
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": message}],
    )

    reply = response.choices[0].message.content
    return jsonify({"reply": reply})
