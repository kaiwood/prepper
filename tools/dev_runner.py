#!/usr/bin/env python3

import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

if __package__ in (None, ""):
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import dev_server, test_runner  # noqa: E402


PRINT_LOCK = threading.Lock()


@dataclass(frozen=True)
class RunnerArgs:
    mode: str
    test_suite: Optional[str] = None


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


def validate_layout() -> None:
    if not BACKEND_DIR.is_dir() or not FRONTEND_DIR.is_dir():
        log(
            "Error: tools/dev_runner.py must be run from the prepper project root (with backend/ and frontend/)."
        )
        sys.exit(1)


def print_usage() -> None:
    log("Usage: ./run.sh [--dev | --test [--all | --backend | --frontend | --cli | --tools] | --help | -h]")
    log("  --dev       Run backend and frontend development servers (default).")
    log("  --test      Run all test suites unless a suite selector is provided.")
    log("  --all       Run backend, prepper-cli, tooling, and frontend tests.")
    log("  --backend   Run backend tests only.")
    log("  --frontend  Run frontend tests only.")
    log("  --cli       Run prepper-cli tests only.")
    log("  --tools     Run local tooling tests only.")
    log("  --help      Show this usage information and exit.")
    log("  -h          Show this usage information and exit.")


def resolve_backend_python() -> str:
    venv_python = BACKEND_DIR / ".venv" / "bin" / "python"
    if venv_python.exists() and os.access(venv_python, os.X_OK):
        return str(venv_python)
    if sys.executable:
        return sys.executable
    return "python3"


def parse_args(argv: List[str]) -> RunnerArgs:
    if len(argv) == 0:
        return RunnerArgs(mode="dev")

    if argv[0] in ("--help", "-h"):
        if len(argv) != 1:
            print_usage()
            raise ValueError("Help does not accept additional flags.")
        return RunnerArgs(mode="help")

    if argv[0] == "--dev":
        if len(argv) != 1:
            print_usage()
            raise ValueError("--dev does not accept additional flags.")
        return RunnerArgs(mode="dev")

    if argv[0] == "--test":
        if len(argv) == 1:
            return RunnerArgs(mode="test", test_suite="all")
        if len(argv) == 2 and argv[1] in TEST_SELECTORS:
            return RunnerArgs(mode="test", test_suite=TEST_SELECTORS[argv[1]])
        print_usage()
        if len(argv) > 2:
            raise ValueError("Expected at most one test suite selector.")
        raise ValueError(f"Unsupported test suite selector: {argv[1]}")

    if argv[0] in TEST_SELECTORS:
        print_usage()
        raise ValueError(f"{argv[0]} must be used with --test.")

    print_usage()
    raise ValueError(f"Unsupported flag: {argv[0]}")


def parse_mode(argv: List[str]) -> str:
    return parse_args(argv).mode


def main() -> int:
    validate_layout()
    try:
        args = parse_args(sys.argv[1:])
    except ValueError as err:
        log(f"Error: {err}")
        return 2

    backend_python = resolve_backend_python()

    if args.mode == "help":
        print_usage()
        return 0

    if args.mode == "test":
        return test_runner.run_test_mode(
            backend_python=backend_python,
            suite=args.test_suite or "all",
            log=log,
        )

    return dev_server.run_dev_server(backend_python=backend_python, log=log)


if __name__ == "__main__":
    sys.exit(main())
