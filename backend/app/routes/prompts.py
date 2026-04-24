from flask import Blueprint, jsonify
from flask_cors import cross_origin
from app import limiter
from prepper_cli import get_default_system_prompt_name, list_prompt_descriptors, list_system_prompt_names

prompts_bp = Blueprint("prompts", __name__)


@prompts_bp.get("/api/prompts")
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
