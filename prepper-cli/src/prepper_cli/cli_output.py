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
) -> None:
    if final_result is None:
        write_line(output, "Final score: unavailable", enable_color=enable_color)
        return

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
) -> None:
    if interviewer_result is None:
        return

    write_line(output, "", enable_color=enable_color)
    write_line(output, "----------------------", enable_color=enable_color)
    write_line(output, "| Interviewer Quality |", enable_color=enable_color)
    write_line(output, "----------------------", enable_color=enable_color)
    write_line(output, "", enable_color=enable_color)
    write_line(
        output,
        f"Weighted score: {interviewer_result['overall_score']:.2f} / 10.00 | "
        f"Threshold: {interviewer_result['pass_threshold']:.2f} | "
        f"Passed: {str(interviewer_result['passed']).lower()}",
        enable_color=enable_color,
    )
    write_line(
        output,
        f"Rubric-only score: {interviewer_result['rubric_overall_score']:.2f} | "
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
