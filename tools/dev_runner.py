#!/usr/bin/env python3

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

PRINT_LOCK = threading.Lock()


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
    log("Usage: ./run.sh [--dev | --test | --help | -h]")
    log("  --dev   Run backend and frontend development servers (default).")
    log("  --test  Run backend, prepper-cli, and frontend tests in sequence.")
    log("  --help  Show this usage information and exit.")
    log("  -h      Show this usage information and exit.")


def resolve_backend_python() -> str:
    venv_python = BACKEND_DIR / ".venv" / "bin" / "python"
    if venv_python.exists() and os.access(venv_python, os.X_OK):
        return str(venv_python)
    if sys.executable:
        return sys.executable
    return "python3"


def stream_output(name: str, pipe) -> None:
    if pipe is None:
        return

    try:
        for line in iter(pipe.readline, ""):
            log(f"[{name}] {line.rstrip()}")
    finally:
        pipe.close()


def parse_mode(argv: List[str]) -> str:
    if len(argv) == 0:
        return "dev"

    if len(argv) != 1:
        print_usage()
        raise ValueError("Expected at most one flag.")

    flag = argv[0]
    if flag == "--dev":
        return "dev"
    if flag == "--test":
        return "test"
    if flag in ("--help", "-h"):
        return "help"

    print_usage()
    raise ValueError(f"Unsupported flag: {flag}")


def run_command(name: str, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]] = None) -> int:
    log(f"[{name}] Running: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    stream_output(name, proc.stdout)
    return proc.wait()


def run_test_mode(backend_python: str) -> int:
    backend_env = os.environ.copy()
    backend_env["PYTHONUNBUFFERED"] = "1"

    test_steps = [
        ("backend-test", [backend_python, "-m", "pytest",
         "tests", "-q"], BACKEND_DIR, backend_env),
        (
            "prepper-cli-test",
            [backend_python, "-m", "pytest", "tests", "-q"],
            PROJECT_ROOT / "prepper-cli",
            backend_env,
        ),
        ("frontend-test", ["npm", "run", "test:unit"],
         FRONTEND_DIR, os.environ.copy()),
    ]

    for name, cmd, cwd, env in test_steps:
        code = run_command(name, cmd, cwd, env)
        if code != 0:
            log(f"[{name}] Failed with exit code {code}; stopping test run.")
            return code

    log("All test suites passed.")
    return 0


def start_processes(backend_python: str) -> Dict[str, subprocess.Popen]:
    processes: Dict[str, subprocess.Popen] = {}

    backend_env = os.environ.copy()
    backend_env["PYTHONUNBUFFERED"] = "1"

    processes["backend"] = subprocess.Popen(
        [backend_python, "run.py"],
        cwd=BACKEND_DIR,
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )

    processes["frontend"] = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )

    return processes


def send_group_signal(proc: subprocess.Popen, sig: signal.Signals) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


def terminate_processes(processes: Dict[str, subprocess.Popen], timeout_seconds: float = 5.0) -> None:
    for proc in processes.values():
        send_group_signal(proc, signal.SIGTERM)

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if all(proc.poll() is not None for proc in processes.values()):
            break
        time.sleep(0.1)

    for proc in processes.values():
        if proc.poll() is None:
            send_group_signal(proc, signal.SIGKILL)

    for proc in processes.values():
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def main() -> int:
    validate_layout()
    try:
        mode = parse_mode(sys.argv[1:])
    except ValueError as err:
        log(f"Error: {err}")
        return 2

    backend_python = resolve_backend_python()

    if mode == "help":
        print_usage()
        return 0

    if mode == "test":
        return run_test_mode(backend_python)

    processes = start_processes(backend_python)

    stream_threads: List[threading.Thread] = []
    for name, proc in processes.items():
        thread = threading.Thread(
            target=stream_output, args=(name, proc.stdout), daemon=True)
        thread.start()
        stream_threads.append(thread)

    backend_pid = processes["backend"].pid
    frontend_pid = processes["frontend"].pid
    log(f"Started backend (PID {backend_pid}) and frontend (PID {frontend_pid}).")
    log("Press Ctrl+C to stop both services.")

    stop_signal: Optional[signal.Signals] = None

    def handle_signal(signum: int, _frame) -> None:
        nonlocal stop_signal
        stop_signal = signal.Signals(signum)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    early_exit = False
    early_exit_name: Optional[str] = None
    early_exit_code: Optional[int] = None

    while True:
        if stop_signal is not None:
            break

        codes: Dict[str, Optional[int]] = {
            name: proc.poll() for name, proc in processes.items()}
        running = [name for name, code in codes.items() if code is None]
        exited: List[Tuple[str, int]] = [
            (name, code) for name, code in codes.items() if code is not None]

        if len(exited) == len(processes):
            break

        if exited and running:
            early_exit = True
            early_exit_name, early_exit_code = exited[0]
            break

        time.sleep(0.1)

    if early_exit and early_exit_name is not None:
        log(f"{early_exit_name} exited first with code {early_exit_code}; stopping remaining services.")

    terminate_processes(processes)

    for thread in stream_threads:
        thread.join(timeout=1)

    final_codes = {name: proc.returncode for name, proc in processes.items()}

    if stop_signal is not None:
        return 130 if stop_signal == signal.SIGINT else 143

    if not early_exit and all(code == 0 for code in final_codes.values()):
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
