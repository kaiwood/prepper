import argparse
import json
import sys

from .benchmark import run_benchmark_interview
from .chat import get_chat_reply
from .conversation import Conversation
from .interview import resolve_pass_threshold, run_interview_turn
from .system_prompts import (
    get_default_system_prompt_name,
    list_prompt_descriptors,
    list_system_prompt_names,
    load_prompt_descriptor,
    load_system_prompt,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send prompts to OpenRouter")
    parser.add_argument("message", nargs="?", help="Prompt to send")
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start interactive chat mode",
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
        "--benchmark",
        action="store_true",
        help="Run benchmark mode with simulated candidate responses",
    )
    parser.add_argument(
        "--candidate-system-prompt",
        help="System prompt name for the simulated candidate in benchmark mode",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        help="Interview difficulty override for benchmark mode",
    )
    parser.add_argument(
        "--language",
        choices=["en", "de"],
        help="Language code for benchmark mode",
    )
    parser.add_argument(
        "--question-limit",
        type=int,
        help="Question roundtrip limit override for benchmark mode",
    )
    parser.add_argument(
        "--pass-threshold",
        type=float,
        help="Pass threshold override for benchmark mode",
    )
    return parser


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


def _run_interactive(system_prompt: str | None) -> int:
    print("Interactive mode. Type 'exit' or 'quit' to leave.")

    descriptor = load_prompt_descriptor(system_prompt) if system_prompt else None
    if descriptor:
        print(f"Using system prompt: {descriptor.name}")
    else:
        print("Using system prompt: none")

    conversation = Conversation()
    question_limit = descriptor.default_question_roundtrips if descriptor else 5
    difficulty = descriptor.default_difficulty if descriptor and descriptor.difficulty_enabled else None
    pass_threshold = resolve_pass_threshold(descriptor, difficulty) if descriptor else 7.0
    model_settings = (
        {
            "temperature": descriptor.temperature,
            "top_p": descriptor.top_p,
            "frequency_penalty": descriptor.frequency_penalty,
            "presence_penalty": descriptor.presence_penalty,
            "max_tokens": descriptor.max_tokens,
        }
        if descriptor
        else {
            "temperature": 0.7,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "max_tokens": 800,
        }
    )

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
                    language=None,
                    question_limit=question_limit,
                    pass_threshold=pass_threshold,
                    model_settings=model_settings,
                    difficulty=difficulty,
                )
                print(result["reply"])
                if result["interview_complete"]:
                    print("Interview is now over.")
                    print(
                        json.dumps(
                            {
                                "reply": result["reply"],
                                "interview_complete": result["interview_complete"],
                                "counted_question_roundtrips": result["question_count"],
                                "question_roundtrips_limit": result["question_limit"],
                                "current_turn_type": result["turn_type"],
                                "pass_threshold": result["pass_threshold"],
                                "final_result": result["final_result"],
                            },
                            ensure_ascii=True,
                        )
                    )
                    return 0
            else:
                reply = get_chat_reply(
                    text,
                    conversation=conversation,
                    system_prompt=descriptor.content if descriptor else None,
                    temperature=descriptor.temperature if descriptor else None,
                    top_p=descriptor.top_p if descriptor else None,
                    frequency_penalty=descriptor.frequency_penalty if descriptor else None,
                    presence_penalty=descriptor.presence_penalty if descriptor else None,
                    max_tokens=descriptor.max_tokens if descriptor else None,
                )
                print(reply)
        except Exception as exc:  # pragma: no cover - direct CLI safety net
            print(f"Error: {exc}", file=sys.stderr)
            return 1


def _run_benchmark(args: argparse.Namespace) -> int:
    interviewer_prompt_name = _resolve_system_prompt_name(args.system_prompt)

    candidate_prompt_name = args.candidate_system_prompt
    if candidate_prompt_name is None:
        candidate_prompt_name = interviewer_prompt_name
    else:
        candidate_prompt_name = _resolve_system_prompt_name(candidate_prompt_name)

    interviewer_descriptor = load_prompt_descriptor(interviewer_prompt_name)
    candidate_descriptor = load_prompt_descriptor(candidate_prompt_name)

    if args.question_limit is not None and args.question_limit <= 0:
        raise ValueError("question_limit must be greater than 0")

    result = run_benchmark_interview(
        interviewer_descriptor=interviewer_descriptor,
        candidate_descriptor=candidate_descriptor,
        difficulty=args.difficulty,
        language=args.language,
        question_limit_override=args.question_limit,
        pass_threshold_override=args.pass_threshold,
    )

    print(json.dumps(result["summary_json"], ensure_ascii=True))
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_system_prompts:
        for name in list_system_prompt_names():
            print(name)
        return 0

    if args.benchmark:
        try:
            return _run_benchmark(args)
        except Exception as exc:  # pragma: no cover - direct CLI safety net
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.interactive:
        selected = args.system_prompt
        if selected is None:
            selected = _choose_interactive_system_prompt(get_default_system_prompt_name())
        elif selected:
            selected = _resolve_system_prompt_name(selected)
        return _run_interactive(selected)

    if not args.message:
        parser.error("message is required unless --interactive is set")

    try:
        prompt_name = _resolve_system_prompt_name(args.system_prompt)
        descriptor = load_prompt_descriptor(prompt_name)
        reply = get_chat_reply(
            args.message,
            system_prompt=descriptor.content,
            temperature=descriptor.temperature,
            top_p=descriptor.top_p,
            frequency_penalty=descriptor.frequency_penalty,
            presence_penalty=descriptor.presence_penalty,
            max_tokens=descriptor.max_tokens,
        )
    except Exception as exc:  # pragma: no cover - direct CLI safety net
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
