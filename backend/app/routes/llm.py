import json
import re

from flask import Blueprint, jsonify, request
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

_ROUNDTRIP_CLASSIFIER_PROMPT = (
    "You classify interviewer messages. Respond with exactly one token: QUESTION or OTHER. "
    "QUESTION means the interviewer is asking a new substantive interview question. "
    "OTHER means clarification, acknowledgement, recap, or closing statement."
)
_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_MODEL_SETTING_BOUNDS = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "frequency_penalty": (-2.0, 2.0),
    "presence_penalty": (-2.0, 2.0),
}


def _extract_json_object(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _clamp_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(10.0, score))


def _coerce_string_list(value: object, max_items: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        trimmed = item.strip()
        if trimmed:
            normalized.append(trimmed)
        if len(normalized) >= max_items:
            break
    return normalized


def _resolve_roundtrip_limit(
    requested_limit: object,
    descriptor: PromptDescriptor,
) -> int:
    default_limit = descriptor.default_question_roundtrips
    min_limit = descriptor.min_question_roundtrips
    max_limit = descriptor.max_question_roundtrips

    if min_limit < 1 or max_limit < min_limit or not (min_limit <= default_limit <= max_limit):
        raise ValueError("prompt roundtrip configuration is invalid")

    if requested_limit is None:
        return default_limit

    if not isinstance(requested_limit, int):
        raise ValueError("max_question_roundtrips must be an integer")

    if requested_limit < min_limit or requested_limit > max_limit:
        raise ValueError(
            f"max_question_roundtrips must be between {min_limit} and {max_limit}"
        )

    return requested_limit


def _resolve_difficulty(
    requested_difficulty: object,
    descriptor: PromptDescriptor,
) -> str | None:
    if requested_difficulty is None:
        if descriptor.difficulty_enabled:
            return descriptor.default_difficulty
        return None

    if not isinstance(requested_difficulty, str):
        raise ValueError("difficulty must be a string")

    normalized = requested_difficulty.strip().lower()
    if not normalized:
        if descriptor.difficulty_enabled:
            return descriptor.default_difficulty
        return None

    if normalized not in _VALID_DIFFICULTIES:
        raise ValueError("difficulty must be one of: easy, medium, hard")

    if not descriptor.difficulty_enabled:
        raise ValueError("difficulty is not supported for this interview type")

    if normalized not in descriptor.difficulty_levels:
        supported = ", ".join(descriptor.difficulty_levels)
        raise ValueError(
            f"difficulty '{normalized}' is not supported for this prompt. Supported: {supported}"
        )

    return normalized


def _resolve_pass_threshold(descriptor: PromptDescriptor, difficulty: str | None) -> float:
    if difficulty == "easy" and descriptor.easy_pass_threshold is not None:
        return descriptor.easy_pass_threshold
    if difficulty == "medium" and descriptor.medium_pass_threshold is not None:
        return descriptor.medium_pass_threshold
    if difficulty == "hard" and descriptor.hard_pass_threshold is not None:
        return descriptor.hard_pass_threshold
    return descriptor.pass_threshold


def _resolve_model_setting_override(name: str, value: object) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")

    minimum, maximum = _MODEL_SETTING_BOUNDS[name]
    numeric_value = float(value)
    if numeric_value < minimum or numeric_value > maximum:
        raise ValueError(f"{name} must be between {minimum:.1f} and {maximum:.1f}")

    return numeric_value


def _resolve_model_settings(
    data: dict,
    descriptor: PromptDescriptor,
) -> dict[str, float | int]:
    temperature = _resolve_model_setting_override(
        "temperature", data.get("temperature")
    )
    top_p = _resolve_model_setting_override("top_p", data.get("top_p"))
    frequency_penalty = _resolve_model_setting_override(
        "frequency_penalty", data.get("frequency_penalty")
    )
    presence_penalty = _resolve_model_setting_override(
        "presence_penalty", data.get("presence_penalty")
    )

    return {
        "temperature": descriptor.temperature if temperature is None else temperature,
        "top_p": descriptor.top_p if top_p is None else top_p,
        "frequency_penalty": (
            descriptor.frequency_penalty
            if frequency_penalty is None
            else frequency_penalty
        ),
        "presence_penalty": (
            descriptor.presence_penalty
            if presence_penalty is None
            else presence_penalty
        ),
        "max_tokens": descriptor.max_tokens,
    }


def _build_difficulty_instruction(difficulty: str) -> str:
    if difficulty == "easy":
        return (
            "\n\nDifficulty mode: Junior-level (easy). "
            "Favor practical, well-scoped coding problems with lower ambiguity. "
            "Offer concise hints when the candidate is clearly stuck. "
            "Keep follow-ups implementation-focused and moderate in depth."
        )

    if difficulty == "hard":
        return (
            "\n\nDifficulty mode: Principal-level (hard). "
            "Use more ambiguous, open-ended problems and probe system-level trade-offs. "
            "Push deeper follow-ups on architecture, scaling, reliability, and constraints. "
            "Keep hints minimal unless explicitly requested."
        )

    return (
        "\n\nDifficulty mode: Senior-level (medium). "
        "Use realistic production-oriented coding challenges with moderate ambiguity. "
        "Expect strong trade-off reasoning, robust edge-case handling, and clear communication. "
        "Provide limited hints only when appropriate."
    )


def _build_runtime_interview_instruction(
    descriptor: PromptDescriptor,
    question_count: int,
    question_limit: int,
) -> str:
    if question_count >= question_limit:
        return (
            "\n\nRuntime rule: You already asked the configured number of scored interview "
            "questions. Do not ask another new question. Provide a concise closing response "
            "and thank the candidate."
        )

    remaining = question_limit - question_count
    return (
        "\n\nRuntime rule: You are still in active interview mode. "
        f"Scored interview questions asked so far: {question_count}/{question_limit}. "
        f"Remaining scored questions: {remaining}. Ask at most one new focused question in this turn. "
        "Clarifications are allowed but should be concise."
    )


def _classify_assistant_turn(message: str, language: str | None) -> str:
    text = (message or "").strip()
    if not text or "?" not in text:
        return "other"

    classifier_input = (
        "Interviewer message:\n"
        f"{text}\n\n"
        "Answer with one token only: QUESTION or OTHER."
    )

    try:
        result = get_chat_reply(
            classifier_input,
            system_prompt=_ROUNDTRIP_CLASSIFIER_PROMPT,
            language=language,
            temperature=0.0,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            max_tokens=8,
        )
    except Exception:
        lowered = text.lower()
        if lowered.startswith(("can you", "what", "how", "why", "tell me", "walk me")):
            return "question"
        return "other"

    normalized = result.strip().upper()
    return "question" if normalized.startswith("QUESTION") else "other"


def _count_scored_questions(
    conversation: Conversation | None,
    language: str | None,
) -> int:
    if conversation is None:
        return 0

    count = 0
    for message in conversation.get_messages():
        if message["role"] != "assistant":
            continue
        if _classify_assistant_turn(message["content"], language) == "question":
            count += 1

    return count


def _build_scoring_system_prompt(descriptor: PromptDescriptor) -> str:
    rubric_items = "\n".join(
        f"- {criterion}: score 0 to 10"
        for criterion in descriptor.rubric_criteria
    )
    return (
        "You are an expert interview evaluator. Score the candidate using ONLY the rubric below. "
        "Return strict JSON with keys: overall_score, criterion_scores, strengths, improvements. "
        "criterion_scores must be an object where each rubric criterion maps to a 0-10 number. "
        "strengths and improvements must be arrays of short bullet-style strings (max 3 each).\n\n"
        f"Rubric:\n{rubric_items}"
    )


def _build_scoring_input(conversation: Conversation) -> str:
    lines = [
        f"{message['role'].upper()}: {message['content']}"
        for message in conversation.get_messages()
    ]
    transcript = "\n".join(lines)
    return f"Score this interview transcript:\n\n{transcript}"


def _parse_scoring_payload(
    raw_response: str,
    descriptor: PromptDescriptor,
    pass_threshold: float,
) -> dict:
    parsed = _extract_json_object(raw_response)
    criterion_map = parsed.get("criterion_scores", {}) if isinstance(parsed, dict) else {}

    criterion_scores = []
    if isinstance(criterion_map, dict):
        for criterion in descriptor.rubric_criteria:
            criterion_scores.append(
                {
                    "criterion": criterion,
                    "score": _clamp_score(criterion_map.get(criterion)),
                }
            )
    else:
        for criterion in descriptor.rubric_criteria:
            criterion_scores.append({"criterion": criterion, "score": 0.0})

    overall = _clamp_score(parsed.get("overall_score") if isinstance(parsed, dict) else None)
    strengths = _coerce_string_list(parsed.get("strengths") if isinstance(parsed, dict) else None)
    improvements = _coerce_string_list(
        parsed.get("improvements") if isinstance(parsed, dict) else None
    )

    return {
        "overall_score": overall,
        "pass_threshold": pass_threshold,
        "passed": overall >= pass_threshold,
        "criterion_scores": criterion_scores,
        "strengths": strengths,
        "improvements": improvements,
        "parse_warning": not bool(parsed),
    }


def _score_interview(
    conversation: Conversation,
    descriptor: PromptDescriptor,
    language: str | None,
    pass_threshold: float,
) -> dict:
    score_raw = get_chat_reply(
        _build_scoring_input(conversation),
        system_prompt=_build_scoring_system_prompt(descriptor),
        language=language,
        temperature=0.0,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=300,
    )
    return _parse_scoring_payload(score_raw, descriptor, pass_threshold)


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
