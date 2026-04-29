import argparse
import os
import sys

from .benchmark import run_benchmark_interview
from .chat import get_chat_reply
from .cli_output import print_final_result, print_turn
from .conversation import Conversation
from .interview import resolve_pass_threshold, run_interview_turn
from .system_prompts import (
    get_default_system_prompt_name,
    list_prompt_descriptors,
    list_system_prompt_names,
    load_prompt_descriptor,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send prompts to OpenRouter",
        prog=os.environ.get("PREPPER_CLI_PROG"),
    )
    parser.add_argument(
        "--system-prompt",
        help="System prompt name from the prompts folder",
    )
    parser.add_argument(
        "--list-system-prompts",
        action="store_true",
        help="List available system prompts and exit",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        help="Interview difficulty override",
    )
    parser.add_argument(
        "--language",
        choices=["en", "de"],
        help="Response language code",
    )
    parser.add_argument(
        "--pass-threshold",
        type=float,
        help="Interview pass threshold override",
    )
    parser.add_argument(
        "--question-limit",
        type=int,
        help="Interview question roundtrip limit override",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Model temperature override",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        help="Model top-p override",
    )
    parser.add_argument(
        "--frequency-penalty",
        type=float,
        help="Model frequency penalty override",
    )
    parser.add_argument(
        "--presence-penalty",
        type=float,
        help="Model presence penalty override",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Model max tokens override",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="Enable colorized transcript output",
    )
    parser.add_argument(
        "--model",
        help="Model name to use for runtime chat and benchmark candidate generation",
    )
    parser.add_argument(
        "--benchmark-model",
        help="Model name to use for final benchmark scoring",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run benchmark mode with simulated candidate responses (required for benchmark-only options)",
    )
    candidate_group = parser.add_mutually_exclusive_group()
    candidate_group.add_argument(
        "--strong-candidate",
        dest="strong_candidate",
        action="store_true",
        help="Benchmark-only: use a strong candidate simulation (default)",
    )
    candidate_group.add_argument(
        "--weak-candidate",
        dest="weak_candidate",
        action="store_true",
        help="Benchmark-only: use a weak candidate simulation",
    )
    return parser


def _validate_benchmark_candidate_flags(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    if (args.strong_candidate or args.weak_candidate) and not args.benchmark:
        parser.error("--strong-candidate/--weak-candidate require --benchmark")


def _resolve_system_prompt_name(selected_name: str | None) -> str:
    available = list_system_prompt_names()
    if not available:
        raise ValueError("No system prompts found in prompts folder")

    prompt_name = (selected_name or get_default_system_prompt_name()).strip()
    if prompt_name not in available:
        available_text = ", ".join(available)
        raise ValueError(
            f"System prompt '{prompt_name}' not found. Available: {available_text}"
        )
    return prompt_name


def _choose_interactive_system_prompt(default_name: str) -> str | None:
    descriptors = list_prompt_descriptors()
    ids = [d.id for d in descriptors]
    default_choice = default_name if default_name in ids else (ids[0] if ids else None)

    print("Select system prompt for this session:")
    print("0) none")
    for index, descriptor in enumerate(descriptors, start=1):
        marker = " (default)" if descriptor.id == default_choice else ""
        print(f"{index}) {descriptor.name}{marker}")

    while True:
        choice = input(f"Prompt selection [Enter for {default_choice}]: ").strip()
        if not choice:
            return default_choice
        if choice == "0":
            return None
        if choice.isdigit():
            selected_index = int(choice)
            if 1 <= selected_index <= len(descriptors):
                return descriptors[selected_index - 1].id

        print("Please enter a valid option number.")


def _resolve_interview_settings(
    descriptor,
    difficulty_override: str | None,
    question_limit_override: int | None,
    pass_threshold_override: float | None,
) -> tuple[str | None, int, float]:
    difficulty = None
    if descriptor and descriptor.difficulty_enabled:
        difficulty = difficulty_override or descriptor.default_difficulty
        if difficulty not in descriptor.difficulty_levels:
            options = ", ".join(descriptor.difficulty_levels)
            raise ValueError(
                f"difficulty '{difficulty}' is not valid for prompt '{descriptor.id}'. Available: {options}"
            )

    question_limit = (
        question_limit_override
        if question_limit_override is not None
        else (descriptor.default_question_roundtrips if descriptor else 5)
    )
    if question_limit <= 0:
        raise ValueError("question_limit must be greater than 0")

    resolved_pass_threshold = (
        pass_threshold_override
        if pass_threshold_override is not None
        else (resolve_pass_threshold(descriptor, difficulty) if descriptor else 7.0)
    )

    return difficulty, question_limit, resolved_pass_threshold


def _resolve_runtime_model_settings(
    descriptor,
    *,
    temperature_override: float | None,
    top_p_override: float | None,
    frequency_penalty_override: float | None,
    presence_penalty_override: float | None,
    max_tokens_override: int | None,
) -> dict[str, float | int] | None:
    if descriptor is None:
        return None

    return {
        "temperature": (
            descriptor.temperature
            if temperature_override is None
            else temperature_override
        ),
        "top_p": descriptor.top_p if top_p_override is None else top_p_override,
        "frequency_penalty": (
            descriptor.frequency_penalty
            if frequency_penalty_override is None
            else frequency_penalty_override
        ),
        "presence_penalty": (
            descriptor.presence_penalty
            if presence_penalty_override is None
            else presence_penalty_override
        ),
        "max_tokens": (
            descriptor.max_tokens if max_tokens_override is None else max_tokens_override
        ),
    }


def _run_interactive(
    system_prompt: str | None,
    *,
    language: str | None,
    enable_color: bool,
    difficulty_override: str | None,
    question_limit_override: int | None,
    pass_threshold_override: float | None,
    model: str | None,
    temperature_override: float | None,
    top_p_override: float | None,
    frequency_penalty_override: float | None,
    presence_penalty_override: float | None,
    max_tokens_override: int | None,
) -> int:
    print("Interactive mode. Type 'exit' or 'quit' to leave.")

    descriptor = load_prompt_descriptor(system_prompt) if system_prompt else None
    if descriptor:
        print(f"Using system prompt: {descriptor.name}")
    else:
        print("Using system prompt: none")

    conversation = Conversation()
    opener_message = "I am ready for the interview. Please begin."
    difficulty, question_limit, pass_threshold = _resolve_interview_settings(
        descriptor,
        difficulty_override,
        question_limit_override,
        pass_threshold_override,
    )
    model_settings = _resolve_runtime_model_settings(
        descriptor,
        temperature_override=temperature_override,
        top_p_override=top_p_override,
        frequency_penalty_override=frequency_penalty_override,
        presence_penalty_override=presence_penalty_override,
        max_tokens_override=max_tokens_override,
    )

    try:
        if descriptor and descriptor.interview_rating_enabled:
            result = run_interview_turn(
                message=opener_message,
                conversation=conversation,
                descriptor=descriptor,
                language=language,
                question_limit=question_limit,
                pass_threshold=pass_threshold,
                model_settings=model_settings,
                difficulty=difficulty,
                model=model,
            )
            print_turn(None, "Interviewer", result["reply"], enable_color=enable_color)
            if result["interview_complete"]:
                print_final_result(None, result["final_result"], enable_color=enable_color)
                return 0
        elif descriptor:
            reply = get_chat_reply(
                opener_message,
                conversation=conversation,
                system_prompt=descriptor.content,
                language=language,
                temperature=model_settings["temperature"] if model_settings else None,
                top_p=model_settings["top_p"] if model_settings else None,
                frequency_penalty=model_settings["frequency_penalty"] if model_settings else None,
                presence_penalty=model_settings["presence_penalty"] if model_settings else None,
                max_tokens=model_settings["max_tokens"] if model_settings else None,
                model=model,
            )
            print_turn(None, "Assistant", reply, enable_color=enable_color)
    except Exception as exc:  # pragma: no cover - direct CLI safety net
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    while True:
        try:
            message = input("> ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 0

        text = message.strip()
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            return 0

        try:
            if descriptor and descriptor.interview_rating_enabled:
                result = run_interview_turn(
                    message=text,
                    conversation=conversation,
                    descriptor=descriptor,
                    language=language,
                    question_limit=question_limit,
                    pass_threshold=pass_threshold,
                    model_settings=model_settings,
                    difficulty=difficulty,
                    model=model,
                )
                print_turn(None, "Interviewer", result["reply"], enable_color=enable_color)
                if result["interview_complete"]:
                    print_final_result(None, result["final_result"], enable_color=enable_color)
                    return 0
            else:
                reply = get_chat_reply(
                    text,
                    conversation=conversation,
                    system_prompt=descriptor.content if descriptor else None,
                    language=language,
                    temperature=model_settings["temperature"] if model_settings else None,
                    top_p=model_settings["top_p"] if model_settings else None,
                    frequency_penalty=model_settings["frequency_penalty"] if model_settings else None,
                    presence_penalty=model_settings["presence_penalty"] if model_settings else None,
                    max_tokens=model_settings["max_tokens"] if model_settings else None,
                    model=model,
                )
                print_turn(None, "Assistant", reply, enable_color=enable_color)
        except Exception as exc:  # pragma: no cover - direct CLI safety net
            print(f"Error: {exc}", file=sys.stderr)
            return 1


def _run_benchmark(args: argparse.Namespace) -> int:
    interviewer_prompt_name = _resolve_system_prompt_name(args.system_prompt)

    interviewer_descriptor = load_prompt_descriptor(interviewer_prompt_name)
    candidate_profile = "weak" if args.weak_candidate else "strong"

    if args.question_limit is not None and args.question_limit <= 0:
        raise ValueError("question_limit must be greater than 0")

    result = run_benchmark_interview(
        interviewer_descriptor=interviewer_descriptor,
        difficulty=args.difficulty,
        language=args.language or "en",
        question_limit_override=args.question_limit,
        pass_threshold_override=args.pass_threshold,
        candidate_profile=candidate_profile,
        enable_color=args.color,
        model=args.model,
        benchmark_model=args.benchmark_model,
        temperature_override=args.temperature,
        top_p_override=args.top_p,
        frequency_penalty_override=args.frequency_penalty,
        presence_penalty_override=args.presence_penalty,
        max_tokens_override=args.max_tokens,
    )

    # Benchmark mode prints the conversational transcript/final score from the
    # benchmark runner; keep the machine-readable summary internal.
    _ = result["summary_json"]
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_system_prompts:
        for name in list_system_prompt_names():
            print(name)
        return 0

    _validate_benchmark_candidate_flags(parser, args)

    if args.benchmark:
        try:
            return _run_benchmark(args)
        except Exception as exc:  # pragma: no cover - direct CLI safety net
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    try:
        selected = args.system_prompt
        if selected is None:
            selected = _choose_interactive_system_prompt(get_default_system_prompt_name())
        elif selected:
            selected = _resolve_system_prompt_name(selected)
        return _run_interactive(
            selected,
            language=args.language,
            enable_color=args.color,
            difficulty_override=args.difficulty,
            question_limit_override=args.question_limit,
            pass_threshold_override=args.pass_threshold,
            model=args.model,
            temperature_override=args.temperature,
            top_p_override=args.top_p,
            frequency_penalty_override=args.frequency_penalty,
            presence_penalty_override=args.presence_penalty,
            max_tokens_override=args.max_tokens,
        )
    except Exception as exc:  # pragma: no cover - direct CLI safety net
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
