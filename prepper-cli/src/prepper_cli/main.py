import argparse
import sys

from .chat import get_chat_reply


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send prompts to OpenRouter")
    parser.add_argument("message", nargs="?", help="Prompt to send")
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start interactive chat mode",
    )
    return parser


def _run_interactive() -> int:
    print("Interactive mode. Type 'exit' or 'quit' to leave.")

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
            reply = get_chat_reply(text)
            print(reply)
        except Exception as exc:  # pragma: no cover - direct CLI safety net
            print(f"Error: {exc}", file=sys.stderr)
            return 1


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.interactive:
        return _run_interactive()

    if not args.message:
        parser.error("message is required unless --interactive is set")

    try:
        reply = get_chat_reply(args.message)
    except Exception as exc:  # pragma: no cover - direct CLI safety net
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
