import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CLI_DIR = PROJECT_ROOT / "prepper-cli"

LogFn = Callable[[str], None]


@dataclass(frozen=True)
class SuiteConfig:
    key: str
    name: str
    cmd: List[str]
    cwd: Path
    env: Optional[Dict[str, str]]


def stream_output(name: str, pipe, log: LogFn) -> None:
    if pipe is None:
        return

    try:
        for line in iter(pipe.readline, ""):
            log(f"[{name}] {line.rstrip()}")
    finally:
        pipe.close()


def python_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return env


def build_test_suites(backend_python: str) -> List[SuiteConfig]:
    backend_env = python_env()

    return [
        SuiteConfig(
            key="backend",
            name="backend-test",
            cmd=[backend_python, "-m", "pytest", "tests", "-q"],
            cwd=BACKEND_DIR,
            env=backend_env,
        ),
        SuiteConfig(
            key="cli",
            name="prepper-cli-test",
            cmd=[backend_python, "-m", "pytest", "tests", "-q"],
            cwd=CLI_DIR,
            env=backend_env,
        ),
        SuiteConfig(
            key="tools",
            name="tools-test",
            cmd=[backend_python, "-m", "pytest", "tools", "-q"],
            cwd=PROJECT_ROOT,
            env=backend_env,
        ),
        SuiteConfig(
            key="frontend",
            name="frontend-test",
            cmd=["npm", "run", "test:unit"],
            cwd=FRONTEND_DIR,
            env=os.environ.copy(),
        ),
    ]


def select_test_suites(backend_python: str, suite: str) -> List[SuiteConfig]:
    suites = build_test_suites(backend_python)
    if suite == "all":
        return suites

    selected = [test_suite for test_suite in suites if test_suite.key == suite]
    if not selected:
        raise ValueError(f"Unsupported test suite: {suite}")
    return selected


def run_command(name: str, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]], log: LogFn) -> int:
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

    stream_output(name, proc.stdout, log)
    return proc.wait()


def run_test_mode(backend_python: str, suite: str, log: LogFn) -> int:
    test_suites = select_test_suites(backend_python, suite)

    for test_suite in test_suites:
        code = run_command(
            test_suite.name,
            test_suite.cmd,
            test_suite.cwd,
            test_suite.env,
            log,
        )
        if code != 0:
            log(f"[{test_suite.name}] Failed with exit code {code}; stopping test run.")
            return code

    if suite == "all":
        log("All test suites passed.")
    else:
        log(f"{test_suites[0].name} passed.")
    return 0
