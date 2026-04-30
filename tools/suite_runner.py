import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CLI_DIR = PROJECT_ROOT / "app"

LogFn = Callable[[str], None]

ANSI_BLUE = "\033[34m"
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_MAGENTA = "\033[35m"
ANSI_RESET = "\033[0m"


@dataclass(frozen=True)
class SuiteConfig:
    key: str
    name: str
    cmd: List[str]
    cwd: Path
    env: Optional[Dict[str, str]]


def color_env(env: Dict[str, str], enable_color: bool) -> Dict[str, str]:
    if enable_color:
        env["FORCE_COLOR"] = "1"
        env.pop("NO_COLOR", None)
    return env


def format_prefix(name: str, enable_color: bool) -> str:
    prefix = f"[{name}]"
    if not enable_color:
        return prefix

    colors = {
        "backend-test": ANSI_GREEN,
        "prepper-cli-test": ANSI_CYAN,
        "tools-test": ANSI_MAGENTA,
        "frontend-test": ANSI_BLUE,
    }
    return f"{colors.get(name, ANSI_BLUE)}{prefix}{ANSI_RESET}"


def stream_output(name: str, pipe, log: LogFn, enable_color: bool = False) -> None:
    if pipe is None:
        return

    try:
        for line in iter(pipe.readline, ""):
            log(f"{format_prefix(name, enable_color)} {line.rstrip()}")
    finally:
        pipe.close()


def python_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return env


def pytest_cmd(backend_python: str, path: str, enable_color: bool) -> List[str]:
    cmd = [backend_python, "-m", "pytest", path, "-q"]
    if enable_color:
        cmd.append("--color=yes")
    return cmd


def build_test_suites(backend_python: str, enable_color: bool = False) -> List[SuiteConfig]:
    backend_env = python_env()

    return [
        SuiteConfig(
            key="backend",
            name="backend-test",
            cmd=pytest_cmd(backend_python, "tests", enable_color),
            cwd=BACKEND_DIR,
            env=backend_env,
        ),
        SuiteConfig(
            key="cli",
            name="prepper-cli-test",
            cmd=pytest_cmd(backend_python, "tests", enable_color),
            cwd=CLI_DIR,
            env=backend_env,
        ),
        SuiteConfig(
            key="tools",
            name="tools-test",
            cmd=pytest_cmd(backend_python, "tools", enable_color),
            cwd=PROJECT_ROOT,
            env=backend_env,
        ),
        SuiteConfig(
            key="frontend",
            name="frontend-test",
            cmd=["npm", "run", "test:unit"],
            cwd=FRONTEND_DIR,
            env=color_env(os.environ.copy(), enable_color),
        ),
    ]


def select_test_suites(backend_python: str, suite: str, enable_color: bool = False) -> List[SuiteConfig]:
    suites = build_test_suites(backend_python, enable_color=enable_color)
    if suite == "all":
        return suites

    selected = [test_suite for test_suite in suites if test_suite.key == suite]
    if not selected:
        raise ValueError(f"Unsupported test suite: {suite}")
    return selected


def run_command(
    name: str,
    cmd: List[str],
    cwd: Path,
    env: Optional[Dict[str, str]],
    log: LogFn,
    enable_color: bool = False,
) -> int:
    log(f"{format_prefix(name, enable_color)} Running: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    stream_output(name, proc.stdout, log, enable_color=enable_color)
    return proc.wait()


def run_test_mode(backend_python: str, suite: str, log: LogFn, enable_color: bool = False) -> int:
    test_suites = select_test_suites(
        backend_python,
        suite,
        enable_color=enable_color,
    )

    for test_suite in test_suites:
        code = run_command(
            test_suite.name,
            test_suite.cmd,
            test_suite.cwd,
            test_suite.env,
            log,
            enable_color=enable_color,
        )
        if code != 0:
            log(
                f"{format_prefix(test_suite.name, enable_color)} Failed with exit code {code}; stopping test run."
            )
            return code

    if suite == "all":
        log("All test suites passed.")
    else:
        log(f"{test_suites[0].name} passed.")
    return 0
