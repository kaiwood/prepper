from __future__ import annotations

import sys
from typing import TextIO


ANSI_RESET = "\033[0m"
ANSI_WHITE = "\033[37m"
ANSI_YELLOW = "\033[33m"
ANSI_GREEN = "\033[32m"


def resolve_stream(output: TextIO | None) -> TextIO:
    return output if output is not None else sys.stdout


def supports_color(stream: TextIO) -> bool:
    is_tty = getattr(stream, "isatty", None)
    return bool(callable(is_tty) and is_tty())


def colorize(text: str, color: str, stream: TextIO, enable_color: bool = False) -> str:
    if not enable_color or not supports_color(stream):
        return text
    return f"{color}{text}{ANSI_RESET}"


def write_line(
    output: TextIO | None,
    text: str = "",
    color: str = ANSI_WHITE,
    *,
    enable_color: bool = False,
) -> None:
    stream = resolve_stream(output)
    stream.write(f"{colorize(text, color, stream, enable_color=enable_color)}\n")


def print_turn(
    output: TextIO | None,
    speaker: str,
    content: str,
    *,
    enable_color: bool = False,
) -> None:
    color = ANSI_WHITE
    if speaker == "Interviewer":
        color = ANSI_YELLOW
    elif speaker == "Candidate":
        color = ANSI_GREEN

    write_line(output, speaker, color=color, enable_color=enable_color)
    write_line(output, content, color=color, enable_color=enable_color)
    write_line(output, enable_color=enable_color)


def print_final_result(
    output: TextIO | None,
    final_result: dict | None,
    *,
    enable_color: bool = False,
    show_heading: bool = True,
) -> None:
    if final_result is None:
        write_line(output, "Final score: unavailable", enable_color=enable_color)
        return

    if show_heading:
        write_line(output, "## Final Candidate Score", enable_color=enable_color)
    write_line(
        output,
        f"Overall: {final_result['overall_score']:.2f} / 10.00 | "
        f"Threshold: {final_result['pass_threshold']:.2f} | "
        f"Passed: {str(final_result['passed']).lower()}",
        enable_color=enable_color,
    )

    write_line(output, "Rubric:", enable_color=enable_color)
    for row in final_result.get("criterion_scores", []):
        write_line(output, f"- {row['criterion']}: {row['score']:.2f}", enable_color=enable_color)

    strengths = final_result.get("strengths", [])
    improvements = final_result.get("improvements", [])

    write_line(output, "Strengths:", enable_color=enable_color)
    if strengths:
        for item in strengths:
            write_line(output, f"- {item}", enable_color=enable_color)
    else:
        write_line(output, "- none", enable_color=enable_color)

    write_line(output, "Improvements:", enable_color=enable_color)
    if improvements:
        for item in improvements:
            write_line(output, f"- {item}", enable_color=enable_color)
    else:
        write_line(output, "- none", enable_color=enable_color)


def print_interviewer_result(
    output: TextIO | None,
    interviewer_result: dict | None,
    *,
    enable_color: bool = False,
    show_heading: bool = True,
) -> None:
    if interviewer_result is None:
        return

    if show_heading:
        write_line(output, "", enable_color=enable_color)
        write_line(output, "----------------------", enable_color=enable_color)
        write_line(output, "| Interviewer Quality |", enable_color=enable_color)
        write_line(output, "----------------------", enable_color=enable_color)
        write_line(output, "", enable_color=enable_color)
    write_line(
        output,
        f"Interviewer score: {interviewer_result['overall_score']:.2f} / 10.00 | "
        f"Threshold: {interviewer_result['pass_threshold']:.2f} | "
        f"Passed: {str(interviewer_result['passed']).lower()}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"Rubric score: {interviewer_result['rubric_overall_score']:.2f} | "
        f"Candidate component: {interviewer_result['candidate_score_component']:.2f}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"Difficulty alignment: {interviewer_result['difficulty_alignment']}",
        enable_color=enable_color,
    )

    write_line(output, "Interviewer rubric:", enable_color=enable_color)
    for row in interviewer_result.get("criterion_scores", []):
        write_line(output, f"- {row['criterion']}: {row['score']:.2f}", enable_color=enable_color)

    strengths = interviewer_result.get("strengths", [])
    improvements = interviewer_result.get("improvements", [])

    write_line(output, "Interviewer strengths:", enable_color=enable_color)
    if strengths:
        for item in strengths:
            write_line(output, f"- {item}", enable_color=enable_color)
    else:
        write_line(output, "- none", enable_color=enable_color)

    write_line(output, "Interviewer improvements:", enable_color=enable_color)
    if improvements:
        for item in improvements:
            write_line(output, f"- {item}", enable_color=enable_color)
    else:
        write_line(output, "- none", enable_color=enable_color)


def _format_optional_score(result: dict | None, key: str = "overall_score") -> str:
    if not isinstance(result, dict):
        return "unavailable"
    value = result.get(key)
    if not isinstance(value, int | float):
        return "unavailable"
    return f"{value:.2f}"


def _format_optional_bool(result: dict | None, key: str = "passed") -> str:
    if not isinstance(result, dict) or key not in result:
        return "unavailable"
    return str(result[key]).lower()


def _format_model_settings(model_settings: dict | None) -> str:
    if not isinstance(model_settings, dict):
        return "unavailable"
    return ", ".join(
        f"{key}={model_settings[key]}"
        for key in (
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "max_tokens",
        )
        if key in model_settings
    )


def _format_difficulty_alignment(interviewer_result: dict | None) -> str:
    if not isinstance(interviewer_result, dict):
        return "unavailable"
    return str(interviewer_result.get("difficulty_alignment", "unavailable"))


def print_benchmark_evaluation(
    output: TextIO | None,
    summary: dict,
    *,
    candidate_result: dict | None = None,
    enable_color: bool = False,
) -> None:
    interviewer_result = summary.get("interviewer_result")
    model_settings = summary.get("model_settings")

    write_line(output, "## Evaluation Summary", enable_color=enable_color)
    write_line(
        output,
        f"candidate_overall_score: {_format_optional_score(candidate_result)}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"candidate_passed: {_format_optional_bool(candidate_result)}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"interviewer_overall_score: {_format_optional_score(interviewer_result)}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"interviewer_passed: {_format_optional_bool(interviewer_result)}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"difficulty_alignment: {_format_difficulty_alignment(interviewer_result)}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"runtime_model: {summary.get('runtime_model') or 'default'}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"benchmark_model: {summary.get('benchmark_model') or 'default'}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"model_settings: {_format_model_settings(model_settings)}",
        enable_color=enable_color,
    )
    write_line(output, "", enable_color=enable_color)
    write_line(output, "## Evaluation Details", enable_color=enable_color)
    write_line(output, "### Candidate Score", enable_color=enable_color)
    print_final_result(
        output,
        candidate_result,
        enable_color=enable_color,
        show_heading=False,
    )
    write_line(output, "", enable_color=enable_color)
    write_line(output, "### Interviewer Score", enable_color=enable_color)
    print_interviewer_result(
        output,
        interviewer_result,
        enable_color=enable_color,
        show_heading=False,
    )
