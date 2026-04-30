#!/usr/bin/env python3

import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import _colorize
except ImportError:  # pragma: no cover - Python < 3.14 fallback
    _colorize = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CLI_DIR = PROJECT_ROOT / "prepper-cli"
CLI_VENV_PYTHON = CLI_DIR / ".venv" / "bin" / "python"

if __package__ in (None, ""):
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import dev_servers, bootstrap, suite_runner  # noqa: E402


PRINT_LOCK = threading.Lock()


@dataclass(frozen=True)
class RunnerArgs:
    mode: str
    test_suite: Optional[str] = None
    enable_color: bool = False
    cli_args: Tuple[str, ...] = ()


TEST_SELECTORS = {
    "--all": "all",
    "--backend": "backend",
    "--frontend": "frontend",
    "--cli": "cli",
    "--tools": "tools",
}


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def _argparse_theme(force_color: bool = False):
    if _colorize is None:
        return None
    if force_color:
        return _colorize.get_theme(force_color=True).argparse
    if not _colorize.can_colorize(file=sys.stdout):
        return None
    return _colorize.get_theme(tty_file=sys.stdout).argparse


def _color(text: str, color_code: str, theme) -> str:
    if theme is None:
        return text
    return f"{color_code}{text}{theme.reset}"


def _usage_line(summary: str, theme) -> str:
    if theme is None:
        return f"Usage: ./prepper.sh {summary}"
    usage = _color("Usage:", theme.usage, theme)
    program = _color("./prepper.sh", theme.prog, theme)
    return f"{usage} {program} {summary}"


def _heading(text: str, theme) -> str:
    if theme is None:
        return text
    return _color(text, theme.heading, theme)


def _long_option(text: str, theme) -> str:
    if theme is None:
        return text
    return _color(text, theme.long_option, theme)


def _short_option(text: str, theme) -> str:
    if theme is None:
        return text
    return _color(text, theme.short_option, theme)


def _summary_long_option(text: str, theme) -> str:
    if theme is None:
        return text
    return _color(text, theme.summary_long_option, theme)


def _summary_short_option(text: str, theme) -> str:
    if theme is None:
        return text
    return _color(text, theme.summary_short_option, theme)


def _label(text: str, theme) -> str:
    if theme is None:
        return text
    return _color(text, theme.label, theme)


def _summary_label(text: str, theme) -> str:
    if theme is None:
        return text
    return _color(text, theme.summary_label, theme)


def _color_option_spec(text: str, theme, *, summary: bool = False) -> str:
    if " " in text:
        option, label = text.split(" ", 1)
    else:
        option, label = text, ""

    if option.startswith("--"):
        option_text = (
            _summary_long_option(option, theme)
            if summary
            else _long_option(option, theme)
        )
    elif option.startswith("-"):
        option_text = (
            _summary_short_option(option, theme)
            if summary
            else _short_option(option, theme)
        )
    else:
        option_text = _summary_label(option, theme) if summary else _label(option, theme)

    if not label:
        return option_text

    if label.startswith("-"):
        label_text = _color_option_spec(label, theme, summary=summary)
    elif label.isupper() or label.startswith("{") or "|" in label:
        label_text = _summary_label(label, theme) if summary else _label(label, theme)
    else:
        label_text = label
    return f"{option_text} {label_text}"


def _summary_option(text: str, theme) -> str:
    if text.startswith("[-"):
        body = text[1:-1]
        return "[" + " | ".join(
            _color_option_spec(part, theme, summary=True)
            for part in body.split(" | ")
        ) + "]"
    return text


def _option_line(flags: str, description: str, theme) -> str:
    colored_flags = [
        _color_option_spec(flag, theme)
        for flag in flags.split(", ")
    ]
    padding = " " * max(1, 33 - len(flags))
    return f"  {', '.join(colored_flags)}{padding} {description}"


def validate_layout() -> None:
    if not BACKEND_DIR.is_dir() or not FRONTEND_DIR.is_dir() or not CLI_DIR.is_dir():
        log(
            "Error: tools/local_cli.py must be run from the prepper project root (with backend/, frontend/, and prepper-cli/)."
        )
        sys.exit(1)


def print_usage(force_color: bool = False) -> None:
    theme = _argparse_theme(force_color=force_color)
    summary = " ".join(
        [
            _summary_option("[-h]", theme),
            _summary_option("[--setup]", theme),
            _summary_option("[--dev | -d]", theme),
            _summary_option("[--test | -t]", theme),
            _summary_option("[--all]", theme),
            _summary_option("[--backend]", theme),
            _summary_option("[--frontend]", theme),
            _summary_option("[--cli]", theme),
            _summary_option("[--tools]", theme),
            _summary_option("[--interactive | -i]", theme),
            _summary_option("[--benchmark | -b]", theme),
            _summary_option("[--benchmark-json]", theme),
            _summary_option("[--interview-style INTERVIEW_STYLE]", theme),
            _summary_option("[--list-interview-styles]", theme),
            _summary_option("[--difficulty {easy,medium,hard}]", theme),
            _summary_option("[--language {en,de,fr}]", theme),
            _summary_option("[--pass-threshold PASS_THRESHOLD]", theme),
            _summary_option("[--question-limit QUESTION_LIMIT]", theme),
            _summary_option("[--temperature TEMPERATURE]", theme),
            _summary_option("[--top-p TOP_P]", theme),
            _summary_option("[--frequency-penalty FREQUENCY_PENALTY]", theme),
            _summary_option("[--presence-penalty PRESENCE_PENALTY]", theme),
            _summary_option("[--max-tokens MAX_TOKENS]", theme),
            _summary_option("[--color]", theme),
            _summary_option("[--model MODEL]", theme),
            _summary_option("[--benchmark-model BENCHMARK_MODEL]", theme),
            _summary_option("[--strong-candidate | --weak-candidate]", theme),
        ]
    )

    log(_usage_line(summary, theme))
    log("")
    log(_heading("Setup:", theme))
    log(_option_line("--setup", "Create env files, Python venvs, and install dependencies.", theme))
    log("")
    log(_heading("Dev servers:", theme))
    log(_option_line("--dev, -d", "Run backend and frontend development servers.", theme))
    log("  (no mode)                       Same as --dev.")
    log(_option_line("--color", "With --dev, force colored runner and child output.", theme))
    log("")
    log(_heading("Tests:", theme))
    log(_option_line("--test, -t", "Run all test suites.", theme))
    log(_option_line("--test --all", "Run backend, prepper-cli, tooling, and frontend tests.", theme))
    log(_option_line("--test --backend", "Run backend tests only.", theme))
    log(_option_line("--test --frontend", "Run frontend tests only.", theme))
    log(_option_line("--test --cli", "Run prepper-cli tests only.", theme))
    log(_option_line("--test --tools", "Run local tooling tests only.", theme))
    log(_option_line("--color", "With --test, force colored runner and child output.", theme))
    log("")
    log(_heading("Interactive CLI:", theme))
    log(_option_line("--interactive, -i [cli flags]", "Run prepper-cli and pass through remaining flags.", theme))
    log(_option_line("--interactive --help", "Show prepper-cli help.", theme))
    log("")
    log(_heading("Benchmark:", theme))
    log(_option_line("--benchmark, -b [cli flags]", "Run prepper-cli benchmark mode.", theme))
    log(_option_line("--benchmark-json", "Print benchmark result JSON; use after --interactive.", theme))
    log(_option_line("--strong-candidate", "Use strong candidate simulation (default).", theme))
    log(_option_line("--weak-candidate", "Use weak candidate simulation.", theme))
    log(_option_line("--difficulty easy|medium|hard", "Override interviewer difficulty.", theme))
    log(_option_line("--language en|de|fr", "Override response language.", theme))
    log(_option_line("--question-limit N", "Override interview question roundtrip limit.", theme))
    log(_option_line("--pass-threshold N", "Override required pass score.", theme))
    log(_option_line("--temperature N", "Override runtime model temperature.", theme))
    log(_option_line("--top-p N", "Override runtime model top-p.", theme))
    log(_option_line("--frequency-penalty N", "Override runtime frequency penalty.", theme))
    log(_option_line("--presence-penalty N", "Override runtime presence penalty.", theme))
    log(_option_line("--max-tokens N", "Override runtime max tokens.", theme))
    log(_option_line("--model MODEL", "Runtime chat and benchmark candidate model.", theme))
    log(_option_line("--benchmark-model MODEL", "Final benchmark scoring model.", theme))
    log(_option_line("--color", "Accepted for benchmark; transcript color is on by default.", theme))
    log("  Example: ./prepper.sh -b --interview-style behavioral_focus")
    log("")
    log(_heading("General:", theme))
    log(_option_line("--help, -h", "Show this usage information and exit.", theme))


def resolve_backend_python() -> str:
    venv_python = BACKEND_DIR / ".venv" / "bin" / "python"
    if venv_python.exists() and os.access(venv_python, os.X_OK):
        return str(venv_python)
    if sys.executable:
        return sys.executable
    return "python3"


def parse_root_color(argv: List[str]) -> tuple[List[str], bool]:
    enable_color = "--color" in argv
    if argv.count("--color") > 1:
        print_usage()
        raise ValueError("--color can only be used once.")

    return [arg for arg in argv if arg != "--color"], enable_color


def parse_args(argv: List[str]) -> RunnerArgs:
    argv, enable_color = parse_root_color(argv)
    cli_color_args = ("--color",) if enable_color else ()

    if len(argv) > 0 and argv[0] in ("--interactive", "-i"):
        return RunnerArgs(mode="interactive", cli_args=(*cli_color_args, *tuple(argv[1:])))

    if len(argv) > 0 and argv[0] in ("--benchmark", "-b"):
        return RunnerArgs(
            mode="interactive",
            cli_args=("--benchmark", "--color", *tuple(argv[1:])),
        )

    if len(argv) == 0:
        return RunnerArgs(mode="dev", enable_color=enable_color)

    if argv[0] in ("--help", "-h"):
        if len(argv) != 1:
            print_usage()
            raise ValueError("Help does not accept additional flags.")
        return RunnerArgs(mode="help", enable_color=enable_color)

    if argv[0] in ("--dev", "-d"):
        if len(argv) != 1:
            print_usage()
            if "--benchmark" in argv[1:] or "-b" in argv[1:]:
                raise ValueError("benchmark cannot be combined with dev mode; use ./prepper.sh --benchmark ...")
            raise ValueError(f"{argv[0]} does not accept additional flags except --color.")
        return RunnerArgs(mode="dev", enable_color=enable_color)

    if argv[0] == "--setup":
        if len(argv) != 1:
            print_usage()
            raise ValueError("--setup does not accept additional flags.")
        return RunnerArgs(mode="setup")

    if argv[0] in ("--test", "-t"):
        if len(argv) == 1:
            return RunnerArgs(mode="test", test_suite="all", enable_color=enable_color)
        if "--benchmark" in argv[1:] or "-b" in argv[1:]:
            print_usage()
            raise ValueError("benchmark cannot be combined with test mode; use ./prepper.sh --benchmark ...")
        if len(argv) == 2 and argv[1] in TEST_SELECTORS:
            return RunnerArgs(
                mode="test",
                test_suite=TEST_SELECTORS[argv[1]],
                enable_color=enable_color,
            )
        print_usage()
        if len(argv) > 2:
            raise ValueError("Expected at most one test suite selector.")
        raise ValueError(f"Unsupported test suite selector: {argv[1]}")

    if argv[0] in TEST_SELECTORS:
        print_usage()
        raise ValueError(f"{argv[0]} must be used with --test.")

    if argv[0] in ("--benchmark-json", "--strong-candidate", "--weak-candidate"):
        print_usage()
        raise ValueError(f"{argv[0]} is a prepper-cli flag; use ./prepper.sh --interactive {argv[0]} ...")

    print_usage()
    raise ValueError(f"Unsupported flag: {argv[0]}")


def parse_mode(argv: List[str]) -> str:
    return parse_args(argv).mode


def run_cli_mode(cli_args: Tuple[str, ...]) -> int:
    if not CLI_VENV_PYTHON.exists() or not os.access(CLI_VENV_PYTHON, os.X_OK):
        log("Error: prepper-cli virtualenv is missing at prepper-cli/.venv.")
        log("Run ./prepper.sh --setup and try again.")
        return 1

    env = os.environ.copy()
    env["PREPPER_CLI_PROG"] = "./prepper.sh --interactive"
    return subprocess.call(
        [str(CLI_VENV_PYTHON), "-m", "prepper_cli.main", *cli_args],
        cwd=CLI_DIR,
        env=env,
    )


def main() -> int:
    validate_layout()
    try:
        args = parse_args(sys.argv[1:])
    except ValueError as err:
        log(f"Error: {err}")
        return 2

    backend_python = resolve_backend_python()

    if args.mode == "help":
        print_usage(force_color=args.enable_color)
        return 0

    if args.mode == "setup":
        try:
            return bootstrap.run_setup(log=log)
        except ValueError as err:
            log(f"Error: {err}")
            return 1

    if args.mode == "interactive":
        return run_cli_mode(args.cli_args)

    if args.mode == "test":
        return suite_runner.run_test_mode(
            backend_python=backend_python,
            suite=args.test_suite or "all",
            log=log,
            enable_color=args.enable_color,
        )

    return dev_servers.run_dev_servers(
        backend_python=backend_python,
        log=log,
        enable_color=args.enable_color,
    )


if __name__ == "__main__":
    sys.exit(main())
