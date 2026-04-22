import argparse
import sys

from .chat import get_chat_reply
from .conversation import Conversation
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


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_system_prompts:
        for name in list_system_prompt_names():
            print(name)
        return 0

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
