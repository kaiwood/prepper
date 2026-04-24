from __future__ import annotations

from typing import TextIO

from .chat import get_chat_reply
from .cli_output import print_final_result, print_interviewer_result, print_turn, write_line
from .conversation import Conversation
from .interview import resolve_pass_threshold, run_interview_turn, score_interviewer_performance
from .system_prompts import PromptDescriptor


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
    enable_color: bool = False,
) -> None:
    write_line(output, "## Benchmark Mock Interview", enable_color=enable_color)
    write_line(output, "", enable_color=enable_color)
    write_line(
        output,
        f"Interviewer prompt: {interviewer_descriptor.name} ({interviewer_descriptor.id})",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"Candidate prompt: benchmark_candidate_{candidate_profile}",
        enable_color=enable_color,
    )
    write_line(output, f"Difficulty: {difficulty or 'default'}", enable_color=enable_color)
    write_line(output, f"Language: {language or 'default'}", enable_color=enable_color)
    write_line(output, f"Question limit: {question_limit}", enable_color=enable_color)
    write_line(output, f"Pass threshold: {pass_threshold:.2f}", enable_color=enable_color)
    write_line(output, enable_color=enable_color)


def run_benchmark_interview(
    interviewer_descriptor: PromptDescriptor,
    difficulty: str | None = None,
    language: str | None = "en",
    question_limit_override: int | None = None,
    pass_threshold_override: float | None = None,
    candidate_profile: str = "good",
    output: TextIO | None = None,
    enable_color: bool = False,
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
        enable_color=enable_color,
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

    print_turn(output, "Interviewer", result["reply"], enable_color=enable_color)

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

        print_turn(output, "Candidate", candidate_reply, enable_color=enable_color)

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

        print_turn(output, "Interviewer", result["reply"], enable_color=enable_color)

    write_line(output, "Interview complete.", enable_color=enable_color)
    write_line(output, "", enable_color=enable_color)
    write_line(output, "## Final Score", enable_color=enable_color)
    write_line(output, "", enable_color=enable_color)
    print_final_result(output, result.get("final_result"), enable_color=enable_color)

    interviewer_result = None
    candidate_result = result.get("final_result")
    if isinstance(candidate_result, dict):
        interviewer_result = score_interviewer_performance(
            conversation=conversation,
            descriptor=interviewer_descriptor,
            language=language,
            difficulty=resolved_difficulty,
            candidate_overall_score=float(candidate_result.get("overall_score", 0.0)),
            interviewer_pass_threshold=interviewer_descriptor.interviewer_pass_threshold,
        )
        print_interviewer_result(output, interviewer_result, enable_color=enable_color)

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
        "interviewer_result": interviewer_result,
    }

    return {
        "summary_json": summary_json,
        "conversation": conversation.get_messages(),
    }
