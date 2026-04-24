import json
import re
from typing import Any

from .chat import get_chat_reply
from .conversation import Conversation
from .system_prompts import PromptDescriptor

_ROUNDTRIP_CLASSIFIER_PROMPT = (
    "You classify interviewer messages. Respond with exactly one token: QUESTION or OTHER. "
    "QUESTION means the interviewer is asking a new substantive interview question. "
    "OTHER means clarification, acknowledgement, recap, or closing statement."
)
_METADATA_PREFIX = "[PREPPER_JSON]"
_VALID_TURN_TYPES = {"QUESTION", "OTHER"}
_FALLBACK_CLOSING_REPLY = "Thank you for your time today. The interview is now over."


def extract_json_object(raw: str) -> dict:
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


def clamp_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(10.0, score))


def coerce_string_list(value: object, max_items: int = 3) -> list[str]:
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


def build_difficulty_instruction(difficulty: str) -> str:
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


def resolve_pass_threshold(descriptor: PromptDescriptor, difficulty: str | None) -> float:
    if difficulty == "easy" and descriptor.easy_pass_threshold is not None:
        return descriptor.easy_pass_threshold
    if difficulty == "medium" and descriptor.medium_pass_threshold is not None:
        return descriptor.medium_pass_threshold
    if difficulty == "hard" and descriptor.hard_pass_threshold is not None:
        return descriptor.hard_pass_threshold
    return descriptor.pass_threshold


def build_metadata_contract_instruction() -> str:
    return (
        "\n\nResponse format requirement: End EVERY interviewer reply with a single metadata suffix "
        f"line in this exact format: {_METADATA_PREFIX} {{\"turn_type\":\"QUESTION|OTHER\",\"interview_complete\":true|false}}. "
        "Do not add extra keys. Keep metadata valid JSON on a single line."
    )


def build_runtime_interview_instruction(
    question_count: int,
    question_limit: int,
) -> str:
    if question_count >= question_limit:
        return (
            "\n\nRuntime rule: You already asked the configured number of scored interview "
            "questions. Do not ask another new question. Provide a concise closing response, "
            "state that the interview is now over, and thank the candidate. "
            "Set interview_complete to true in your metadata."
        )

    remaining = question_limit - question_count
    return (
        "\n\nRuntime rule: You are still in active interview mode. "
        f"Scored interview questions asked so far: {question_count}/{question_limit}. "
        f"Remaining scored questions: {remaining}. Ask at most one new focused question in this turn. "
        "Clarifications are allowed but should be concise. "
        "Set interview_complete to false unless this turn explicitly closes the interview."
    )


def build_forced_closing_instruction(
    question_count: int,
    question_limit: int,
) -> str:
    return (
        "\n\nRuntime override: The interview must end now because the scored question "
        f"roundtrip limit has been reached ({question_count}/{question_limit}). "
        "Do not ask any new question. Provide a brief closing statement that clearly says "
        "the interview is now over and thanks the candidate. "
        "End with metadata using turn_type OTHER and interview_complete true."
    )


def parse_reply_metadata(raw_reply: str) -> dict[str, Any]:
    text = (raw_reply or "").strip()
    if not text:
        return {
            "reply": "",
            "metadata": {},
            "metadata_valid": False,
        }

    marker_index = text.rfind(_METADATA_PREFIX)
    if marker_index == -1:
        return {
            "reply": text,
            "metadata": {},
            "metadata_valid": False,
        }

    reply_text = text[:marker_index].rstrip()
    metadata_text = text[marker_index + len(_METADATA_PREFIX):].strip()
    metadata = extract_json_object(metadata_text)

    return {
        "reply": reply_text,
        "metadata": metadata,
        "metadata_valid": bool(metadata),
    }


def _resolve_turn_type(
    metadata: dict[str, Any],
    reply: str,
    language: str | None,
    include_diagnostics: bool,
) -> tuple[str, dict[str, Any] | None]:
    raw_turn_type = metadata.get("turn_type")
    if isinstance(raw_turn_type, str) and raw_turn_type.upper() in _VALID_TURN_TYPES:
        turn_type = "question" if raw_turn_type.upper() == "QUESTION" else "other"
        return turn_type, None

    if include_diagnostics:
        turn_type, classify_diagnostics = classify_assistant_turn_with_diagnostics(
            reply,
            language,
        )
        return turn_type, classify_diagnostics

    return classify_assistant_turn(reply, language), None


def request_forced_closing_turn(
    descriptor: PromptDescriptor,
    language: str | None,
    model_settings: dict[str, float | int],
    question_count: int,
    question_limit: int,
    difficulty: str | None = None,
    include_diagnostics: bool = False,
) -> dict[str, Any]:
    system_prompt = descriptor.content + build_metadata_contract_instruction()
    if difficulty is not None:
        system_prompt += build_difficulty_instruction(difficulty)
    system_prompt += build_forced_closing_instruction(question_count, question_limit)

    override_message = (
        "Runtime override: end the interview now and provide the final closing statement."
    )

    diagnostics: dict[str, Any] = {}
    if include_diagnostics:
        raw_reply, chat_diagnostics = get_chat_reply(
            override_message,
            conversation=None,
            system_prompt=system_prompt,
            language=language,
            temperature=model_settings["temperature"],
            top_p=model_settings["top_p"],
            frequency_penalty=model_settings["frequency_penalty"],
            presence_penalty=model_settings["presence_penalty"],
            max_tokens=model_settings["max_tokens"],
            include_diagnostics=True,
        )
        diagnostics["turn_chat"] = chat_diagnostics
    else:
        raw_reply = get_chat_reply(
            override_message,
            conversation=None,
            system_prompt=system_prompt,
            language=language,
            temperature=model_settings["temperature"],
            top_p=model_settings["top_p"],
            frequency_penalty=model_settings["frequency_penalty"],
            presence_penalty=model_settings["presence_penalty"],
            max_tokens=model_settings["max_tokens"],
        )

    parsed_reply = parse_reply_metadata(raw_reply)
    clean_reply = parsed_reply["reply"] or _FALLBACK_CLOSING_REPLY
    metadata = parsed_reply["metadata"] if isinstance(parsed_reply["metadata"], dict) else {}

    if not parsed_reply["metadata_valid"]:
        clean_reply = _FALLBACK_CLOSING_REPLY
        turn_type = "other"
    else:
        turn_type, classify_diagnostics = _resolve_turn_type(
            metadata,
            clean_reply,
            language,
            include_diagnostics,
        )
        if include_diagnostics and classify_diagnostics is not None:
            diagnostics["turn_classifier"] = classify_diagnostics

    if include_diagnostics:
        diagnostics["raw_turn_reply"] = raw_reply
        diagnostics["parsed_turn_reply"] = parsed_reply

    return {
        "reply": clean_reply,
        "turn_type": turn_type,
        "metadata_valid": parsed_reply["metadata_valid"],
        "metadata": metadata,
        "diagnostics": diagnostics,
    }


def classify_assistant_turn(message: str, language: str | None) -> str:
    text = (message or "").strip()
    if not text:
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
        if lowered.startswith(
            ("can you", "what", "how", "why", "tell me", "walk me")
        ) or ":" in lowered:
            return "question"
        return "other"

    normalized = result.strip().upper()
    return "question" if normalized.startswith("QUESTION") else "other"


def classify_assistant_turn_with_diagnostics(
    message: str,
    language: str | None,
) -> tuple[str, dict[str, Any]]:
    text = (message or "").strip()
    if not text:
        return "other", {"reason": "empty_message", "fallback": "rule_based"}

    classifier_input = (
        "Interviewer message:\n"
        f"{text}\n\n"
        "Answer with one token only: QUESTION or OTHER."
    )

    try:
        result, chat_diagnostics = get_chat_reply(
            classifier_input,
            system_prompt=_ROUNDTRIP_CLASSIFIER_PROMPT,
            language=language,
            temperature=0.0,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            max_tokens=8,
            include_diagnostics=True,
        )
    except Exception as exc:
        lowered = text.lower()
        fallback = "question" if lowered.startswith(
            ("can you", "what", "how", "why", "tell me", "walk me")
        ) or ":" in lowered else "other"
        return fallback, {
            "reason": "classifier_exception",
            "fallback": "rule_based",
            "error": str(exc),
        }

    normalized = result.strip().upper()
    classification = "question" if normalized.startswith("QUESTION") else "other"
    return classification, {
        "classifier_reply": result,
        "classification": classification,
        "llm": chat_diagnostics,
    }


def count_scored_questions(
    conversation: Conversation | None,
    language: str | None,
) -> int:
    if conversation is None:
        return 0

    count = 0
    for message in conversation.get_messages():
        if message["role"] != "assistant":
            continue

        parsed = parse_reply_metadata(message["content"])
        metadata = parsed["metadata"]
        raw_turn_type = metadata.get("turn_type") if isinstance(metadata, dict) else None
        if isinstance(raw_turn_type, str) and raw_turn_type.upper() in _VALID_TURN_TYPES:
            if raw_turn_type.upper() == "QUESTION":
                count += 1
            continue

        if classify_assistant_turn(parsed["reply"], language) == "question":
            count += 1

    return count


def build_scoring_system_prompt(descriptor: PromptDescriptor) -> str:
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


def build_scoring_input(conversation: Conversation) -> str:
    lines = [
        f"{message['role'].upper()}: {parse_reply_metadata(message['content'])['reply']}"
        if message["role"] == "assistant"
        else f"{message['role'].upper()}: {message['content']}"
        for message in conversation.get_messages()
    ]
    transcript = "\n".join(lines)
    return f"Score this interview transcript:\n\n{transcript}"


def parse_scoring_payload(
    raw_response: str,
    descriptor: PromptDescriptor,
    pass_threshold: float,
) -> dict:
    parsed = extract_json_object(raw_response)
    criterion_map = parsed.get("criterion_scores", {}) if isinstance(parsed, dict) else {}

    criterion_scores = []
    if isinstance(criterion_map, dict):
        for criterion in descriptor.rubric_criteria:
            criterion_scores.append(
                {
                    "criterion": criterion,
                    "score": clamp_score(criterion_map.get(criterion)),
                }
            )
    else:
        for criterion in descriptor.rubric_criteria:
            criterion_scores.append({"criterion": criterion, "score": 0.0})

    overall = clamp_score(parsed.get("overall_score") if isinstance(parsed, dict) else None)
    strengths = coerce_string_list(parsed.get("strengths") if isinstance(parsed, dict) else None)
    improvements = coerce_string_list(
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


def score_interview(
    conversation: Conversation,
    descriptor: PromptDescriptor,
    language: str | None,
    pass_threshold: float,
) -> dict:
    score_raw = get_chat_reply(
        build_scoring_input(conversation),
        system_prompt=build_scoring_system_prompt(descriptor),
        language=language,
        temperature=0.0,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=300,
    )
    return parse_scoring_payload(score_raw, descriptor, pass_threshold)


def score_interview_with_diagnostics(
    conversation: Conversation,
    descriptor: PromptDescriptor,
    language: str | None,
    pass_threshold: float,
) -> tuple[dict, dict[str, Any]]:
    score_raw, chat_diagnostics = get_chat_reply(
        build_scoring_input(conversation),
        system_prompt=build_scoring_system_prompt(descriptor),
        language=language,
        temperature=0.0,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=300,
        include_diagnostics=True,
    )
    parsed = parse_scoring_payload(score_raw, descriptor, pass_threshold)
    return parsed, {
        "raw_reply": score_raw,
        "llm": chat_diagnostics,
        "parsed": parsed,
    }


def run_interview_turn(
    message: str,
    conversation: Conversation | None,
    descriptor: PromptDescriptor,
    language: str | None,
    question_limit: int,
    pass_threshold: float,
    model_settings: dict[str, float | int],
    difficulty: str | None = None,
    include_diagnostics: bool = False,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}

    prior_question_count = count_scored_questions(conversation, language)

    system_prompt = descriptor.content + build_metadata_contract_instruction()
    if difficulty is not None:
        system_prompt += build_difficulty_instruction(difficulty)

    system_prompt += build_runtime_interview_instruction(
        prior_question_count,
        question_limit,
    )

    if include_diagnostics:
        raw_reply, chat_diagnostics = get_chat_reply(
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
        )
        diagnostics["turn_chat"] = chat_diagnostics
    else:
        raw_reply = get_chat_reply(
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

    parsed_reply = parse_reply_metadata(raw_reply)
    clean_reply = parsed_reply["reply"]
    diagnostics["raw_turn_reply"] = raw_reply
    diagnostics["parsed_turn_reply"] = parsed_reply
    if conversation is not None:
        # Persist clean assistant text to conversation history so metadata does not leak into context.
        conversation.replace_last_assistant_reply(clean_reply)

    metadata = parsed_reply["metadata"] if isinstance(parsed_reply["metadata"], dict) else {}

    turn_type, classify_diagnostics = _resolve_turn_type(
        metadata,
        clean_reply,
        language,
        include_diagnostics,
    )
    if include_diagnostics and classify_diagnostics is not None:
        diagnostics["turn_classifier"] = classify_diagnostics

    count_after = prior_question_count + (1 if turn_type == "question" else 0)
    count_after = min(count_after, question_limit)

    metadata_interview_complete = metadata.get("interview_complete")
    metadata_complete = (
        metadata_interview_complete if isinstance(metadata_interview_complete, bool) else None
    )

    reached_limit = count_after >= question_limit
    model_provided_valid_closing = metadata_complete is True and turn_type == "other"
    needs_forced_closing = reached_limit and not model_provided_valid_closing

    metadata_warning = not parsed_reply["metadata_valid"]

    if needs_forced_closing:
        forced_turn = request_forced_closing_turn(
            descriptor=descriptor,
            language=language,
            model_settings=model_settings,
            question_count=count_after,
            question_limit=question_limit,
            difficulty=difficulty,
            include_diagnostics=include_diagnostics,
        )

        clean_reply = forced_turn["reply"]
        turn_type = forced_turn["turn_type"]
        metadata_warning = not forced_turn["metadata_valid"]

        if include_diagnostics:
            diagnostics["forced_closing"] = forced_turn["diagnostics"]

        if conversation is not None:
            conversation.replace_last_assistant_reply(clean_reply)

        interview_complete = True
    else:
        interview_complete = metadata_complete if metadata_complete is not None else reached_limit
        # Safety guard: completion must not disagree with reached limit.
        interview_complete = bool(interview_complete or reached_limit)

    final_result = None
    if interview_complete:
        scoring_conversation = conversation or Conversation.from_messages(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": clean_reply},
            ]
        )

        if include_diagnostics:
            final_result, score_diagnostics = score_interview_with_diagnostics(
                scoring_conversation,
                descriptor,
                language,
                pass_threshold,
            )
            diagnostics["final_scoring"] = score_diagnostics
        else:
            final_result = score_interview(
                scoring_conversation,
                descriptor,
                language,
                pass_threshold,
            )

    result = {
        "reply": clean_reply,
        "turn_type": turn_type,
        "question_count": count_after,
        "question_limit": question_limit,
        "interview_complete": interview_complete,
        "pass_threshold": pass_threshold,
        "metadata_warning": metadata_warning,
        "final_result": final_result,
    }

    if include_diagnostics:
        result["debug"] = diagnostics

    return result
