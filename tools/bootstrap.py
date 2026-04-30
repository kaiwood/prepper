import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREPPER_CLI_DIR = PROJECT_ROOT / "prepper-cli"
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

LogFn = Callable[[str], None]
RunCommandFn = Callable[[Sequence[str], Path], None]


def validate_layout() -> None:
    if (
        not PREPPER_CLI_DIR.is_dir()
        or not BACKEND_DIR.is_dir()
        or not FRONTEND_DIR.is_dir()
    ):
        raise ValueError("run setup from the prepper project root")


def default_run_command(cmd: Sequence[str], cwd: Path) -> None:
    subprocess.check_call(list(cmd), cwd=cwd)


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise ValueError(f"'{name}' not found. Install it first or adjust PATH.")


def python_bin() -> str:
    return os.environ.get("PYTHON_BIN", "python3")


def create_venv_if_missing(dir_path: Path, log: LogFn, run_command: RunCommandFn) -> None:
    venv_dir = dir_path / ".venv"
    if venv_dir.is_dir():
        log(f"Using existing virtual environment: {venv_dir}")
        return

    log(f"Creating virtual environment: {venv_dir}")
    run_command([python_bin(), "-m", "venv", str(venv_dir)], PROJECT_ROOT)


def ensure_file_from_example_or_default(
    target: Path,
    example: Path,
    default_content: str,
    log: LogFn,
) -> None:
    if target.exists():
        return

    if example.exists():
        shutil.copyfile(example, target)
        log(f"Created {target} from {example}")
        return

    target.write_text(default_content, encoding="utf-8")
    log(f"Created {target} with defaults")


def ensure_env_files(log: LogFn) -> None:
    ensure_file_from_example_or_default(
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".env.example",
        "\n".join(
            [
                "OPENROUTER_API_KEY=",
                "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1",
                "PREPPER_DEFAULT_SYSTEM_PROMPT=coding_focus",
                "OPENROUTER_MODEL=openai/gpt-5.4",
                "",
            ]
        ),
        log,
    )
    ensure_file_from_example_or_default(
        FRONTEND_DIR / ".env.local",
        FRONTEND_DIR / ".env.local.example",
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:5000\n",
        log,
    )


def setup_commands(prepper_cli_python: Path, backend_python: Path) -> List[tuple[List[str], Path]]:
    return [
        ([str(prepper_cli_python), "-m", "pip", "install", "--upgrade", "pip"], PREPPER_CLI_DIR),
        (
            [str(prepper_cli_python), "-m", "pip", "install", "--editable", str(PREPPER_CLI_DIR)],
            PREPPER_CLI_DIR,
        ),
        ([str(backend_python), "-m", "pip", "install", "--upgrade", "pip"], BACKEND_DIR),
        ([str(backend_python), "-m", "pip", "install", "-r", "requirements.txt"], BACKEND_DIR),
        (["npm", "install"], FRONTEND_DIR),
    ]


def run_setup(log: LogFn, run_command: RunCommandFn = default_run_command) -> int:
    validate_layout()
    require_command(python_bin())
    require_command("npm")

    ensure_env_files(log)

    log("==> Setting up prepper-cli")
    create_venv_if_missing(PREPPER_CLI_DIR, log, run_command)

    log("==> Setting up backend")
    create_venv_if_missing(BACKEND_DIR, log, run_command)

    log("==> Setting up frontend")
    prepper_cli_python = PREPPER_CLI_DIR / ".venv" / "bin" / "python"
    backend_python = BACKEND_DIR / ".venv" / "bin" / "python"
    for cmd, cwd in setup_commands(prepper_cli_python, backend_python):
        run_command(cmd, cwd)

    log("")
    log("Setup complete.")
    log("Set OPENROUTER_API_KEY or LLM_API_KEY in:")
    log(f"  - {PROJECT_ROOT / '.env'}")
    return 0
