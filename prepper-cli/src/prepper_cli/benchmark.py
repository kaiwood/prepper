from __future__ import annotations

import sys
from typing import TextIO

from .chat import get_chat_reply
from .conversation import Conversation
from .interview import resolve_pass_threshold, run_interview_turn
from .system_prompts import PromptDescriptor


_ANSI_RESET = "\033[0m"
_ANSI_WHITE = "\033[37m"
_ANSI_YELLOW = "\033[33m"
_ANSI_GREEN = "\033[32m"


def _resolve_stream(output: TextIO | None) -> TextIO:
    return output if output is not None else sys.stdout


def _supports_color(stream: TextIO) -> bool:
    is_tty = getattr(stream, "isatty", None)
    return bool(callable(is_tty) and is_tty())


def _colorize(text: str, color: str, stream: TextIO) -> str:
    if not _supports_color(stream):
        return text
    return f"{color}{text}{_ANSI_RESET}"


def _write_line(output: TextIO | None, text: str = "", color: str = _ANSI_WHITE) -> None:
    stream = _resolve_stream(output)
    stream.write(f"{_colorize(text, color, stream)}\n")


def _build_model_settings(descriptor: PromptDescriptor) -> dict[str, float | int]:
    return {
        "temperature": descriptor.temperature,
        "top_p": descriptor.top_p,
        "frequency_penalty": descriptor.frequency_penalty,
        "presence_penalty": descriptor.presence_penalty,
        "max_tokens": descriptor.max_tokens,
    }


def _resolve_difficulty(
    descriptor: PromptDescriptor,
    difficulty_override: str | None,
) -> str | None:
    if not descriptor.difficulty_enabled:
        return None

    if difficulty_override is None:
        return descriptor.default_difficulty

    if difficulty_override not in descriptor.difficulty_levels:
        options = ", ".join(descriptor.difficulty_levels)
        raise ValueError(
            f"difficulty '{difficulty_override}' is not valid for prompt '{descriptor.id}'. "
            f"Available: {options}"
        )

    return difficulty_override


def _build_candidate_system_prompt(candidate_profile: str) -> str:
    if candidate_profile == "good":
        return (
            "You are a candidate in a mock interview benchmark. "
            "Answer the interviewer's prompts naturally and concisely as a human candidate would. "
            "Do not act like an interviewer, coach, or evaluator. "
            "Do not include control tags, metadata blocks, JSON, or special suffixes. "
            "Only provide the candidate's spoken answer."
        )

    if candidate_profile == "bad":
        return (
            "You are a weak candidate in a mock interview benchmark. "
            "Give short, vague, and minimally helpful answers that often omit concrete actions, outcomes, and metrics. "
            "Avoid structured STAR storytelling, provide little ownership detail, and sound uncertain when possible. "
            "Do not act like an interviewer, coach, or evaluator. "
            "Do not include control tags, metadata blocks, JSON, or special suffixes. "
            "Only provide the candidate's spoken answer."
        )

    raise ValueError(f"Unsupported candidate_profile: {candidate_profile}")


def _generate_candidate_reply(
    interviewer_message: str,
    interviewer_descriptor: PromptDescriptor,
    language: str | None,
    candidate_profile: str,
) -> str:
    candidate_input = (
        "Interviewer question:\n"
        f"{interviewer_message}\n\n"
        "Respond as the candidate in this interview."
    )

    return get_chat_reply(
        candidate_input,
        system_prompt=_build_candidate_system_prompt(candidate_profile),
        language=language,
        temperature=interviewer_descriptor.temperature,
        top_p=interviewer_descriptor.top_p,
        frequency_penalty=interviewer_descriptor.frequency_penalty,
        presence_penalty=interviewer_descriptor.presence_penalty,
        max_tokens=interviewer_descriptor.max_tokens,
    )


def _print_header(
    output: TextIO | None,
    interviewer_descriptor: PromptDescriptor,
    candidate_profile: str,
    difficulty: str | None,
    question_limit: int,
    pass_threshold: float,
    language: str | None,
) -> None:
    _write_line(output, "=== Benchmark Mock Interview ===")
    _write_line(output, f"Interviewer prompt: {interviewer_descriptor.name} ({interviewer_descriptor.id})")
    _write_line(output, f"Candidate prompt: benchmark_candidate_{candidate_profile}")
    _write_line(output, f"Difficulty: {difficulty or 'default'}")
    _write_line(output, f"Language: {language or 'default'}")
    _write_line(output, f"Question limit: {question_limit}")
    _write_line(output, f"Pass threshold: {pass_threshold:.2f}")
    _write_line(output)


def _print_turn(output: TextIO | None, turn_number: int, speaker: str, content: str) -> None:
    color = _ANSI_WHITE
    if speaker == "Interviewer":
        color = _ANSI_YELLOW
    elif speaker == "Candidate":
        color = _ANSI_GREEN

    _write_line(output, f"Turn {turn_number:02d} | {speaker}", color=color)
    _write_line(output, content, color=color)
    _write_line(output)


def _print_final_result(output: TextIO | None, final_result: dict | None) -> None:
    if final_result is None:
        _write_line(output, "Final score: unavailable")
        return

    _write_line(output, "=== Final Score ===")
    _write_line(
        output,
        f"Overall: {final_result['overall_score']:.2f} / 10.00 | "
        f"Threshold: {final_result['pass_threshold']:.2f} | "
        f"Passed: {str(final_result['passed']).lower()}",
    )

    _write_line(output, "Rubric:")
    for row in final_result.get("criterion_scores", []):
        _write_line(output, f"- {row['criterion']}: {row['score']:.2f}")

    strengths = final_result.get("strengths", [])
    improvements = final_result.get("improvements", [])

    _write_line(output, "Strengths:")
    if strengths:
        for item in strengths:
            _write_line(output, f"- {item}")
    else:
        _write_line(output, "- none")

    _write_line(output, "Improvements:")
    if improvements:
        for item in improvements:
            _write_line(output, f"- {item}")
    else:
        _write_line(output, "- none")


def run_benchmark_interview(
    interviewer_descriptor: PromptDescriptor,
    difficulty: str | None = None,
    language: str | None = None,
    question_limit_override: int | None = None,
    pass_threshold_override: float | None = None,
    candidate_profile: str = "good",
    output: TextIO | None = None,
) -> dict:
    conversation = Conversation()

    resolved_difficulty = _resolve_difficulty(interviewer_descriptor, difficulty)
    question_limit = (
        question_limit_override
        if question_limit_override is not None
        else interviewer_descriptor.default_question_roundtrips
    )
    if question_limit <= 0:
        raise ValueError("question_limit must be greater than 0")

    pass_threshold = (
        pass_threshold_override
        if pass_threshold_override is not None
        else resolve_pass_threshold(interviewer_descriptor, resolved_difficulty)
    )

    model_settings = _build_model_settings(interviewer_descriptor)
    _print_header(
        output,
        interviewer_descriptor,
        candidate_profile,
        resolved_difficulty,
        question_limit,
        pass_threshold,
        language,
    )

    start_message = "I am ready for the interview. Please begin."
    turn_index = 1
    result = run_interview_turn(
        message=start_message,
        conversation=conversation,
        descriptor=interviewer_descriptor,
        language=language,
        question_limit=question_limit,
        pass_threshold=pass_threshold,
        model_settings=model_settings,
        difficulty=resolved_difficulty,
    )

    _print_turn(output, turn_index, "Interviewer", result["reply"])

    max_steps = max(12, question_limit * 4)
    step_count = 0

    while not result["interview_complete"]:
        step_count += 1
        if step_count > max_steps:
            raise RuntimeError("benchmark exceeded safety turn limit")

        candidate_reply = _generate_candidate_reply(
            interviewer_message=result["reply"],
            interviewer_descriptor=interviewer_descriptor,
            language=language,
            candidate_profile=candidate_profile,
        )

        _print_turn(output, turn_index, "Candidate", candidate_reply)

        turn_index += 1
        result = run_interview_turn(
            message=candidate_reply,
            conversation=conversation,
            descriptor=interviewer_descriptor,
            language=language,
            question_limit=question_limit,
            pass_threshold=pass_threshold,
            model_settings=model_settings,
            difficulty=resolved_difficulty,
        )

        _print_turn(output, turn_index, "Interviewer", result["reply"])

    _write_line(output, "Interview complete.")
    _print_final_result(output, result.get("final_result"))

    summary_json = {
        "mode": "benchmark",
        "interviewer_system_prompt": interviewer_descriptor.id,
        "candidate_system_prompt": f"benchmark_candidate_{candidate_profile}",
        "difficulty": resolved_difficulty,
        "language": language,
        "question_roundtrips_limit": question_limit,
        "counted_question_roundtrips": result["question_count"],
        "interview_complete": result["interview_complete"],
        "current_turn_type": result["turn_type"],
        "pass_threshold": pass_threshold,
        "final_result": result.get("final_result"),
    }

    return {
        "summary_json": summary_json,
        "conversation": conversation.get_messages(),
    }
