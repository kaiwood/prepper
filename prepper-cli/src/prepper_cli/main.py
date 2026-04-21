import argparse
import sys

from .chat import get_chat_reply
from .conversation import Conversation
from .system_prompts import (
    get_default_system_prompt_name,
    list_system_prompt_names,
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
    available = list_system_prompt_names()
    default_choice = default_name if default_name in available else available[0]

    print("Select system prompt for this session:")
    print("0) none")
    for index, name in enumerate(available, start=1):
        marker = " (default)" if name == default_choice else ""
        print(f"{index}) {name}{marker}")

    while True:
        choice = input(f"Prompt selection [Enter for {default_choice}]: ").strip()
        if not choice:
            return default_choice
        if choice == "0":
            return None
        if choice.isdigit():
            selected_index = int(choice)
            if 1 <= selected_index <= len(available):
                return available[selected_index - 1]

        print("Please enter a valid option number.")


def _run_interactive(system_prompt: str | None) -> int:
    print("Interactive mode. Type 'exit' or 'quit' to leave.")
    if system_prompt:
        print(f"Using system prompt: {system_prompt}")
    else:
        print("Using system prompt: none")

    conversation = Conversation()
    system_prompt_text = load_system_prompt(system_prompt) if system_prompt else None

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
                system_prompt=system_prompt_text,
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
        system_prompt_text = load_system_prompt(prompt_name)
        reply = get_chat_reply(args.message, system_prompt=system_prompt_text)
    except Exception as exc:  # pragma: no cover - direct CLI safety net
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
