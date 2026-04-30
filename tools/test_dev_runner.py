import io
import sys
from types import SimpleNamespace

import pytest

from tools import dev_runner, dev_server, setup_runner, test_runner


def test_parse_mode_defaults_to_dev():
    assert dev_runner.parse_mode([]) == "dev"
    assert dev_runner.parse_args([]) == dev_runner.RunnerArgs(mode="dev")


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--dev"], dev_runner.RunnerArgs(mode="dev")),
        (["-d"], dev_runner.RunnerArgs(mode="dev")),
        (["--setup"], dev_runner.RunnerArgs(mode="setup")),
        (["--test"], dev_runner.RunnerArgs(mode="test", test_suite="all")),
        (["-t"], dev_runner.RunnerArgs(mode="test", test_suite="all")),
        (["--test", "--all"], dev_runner.RunnerArgs(mode="test", test_suite="all")),
        (["--test", "--backend"], dev_runner.RunnerArgs(mode="test", test_suite="backend")),
        (["-t", "--backend"], dev_runner.RunnerArgs(mode="test", test_suite="backend")),
        (["--test", "--frontend"], dev_runner.RunnerArgs(mode="test", test_suite="frontend")),
        (["--test", "--cli"], dev_runner.RunnerArgs(mode="test", test_suite="cli")),
        (["--test", "--tools"], dev_runner.RunnerArgs(mode="test", test_suite="tools")),
        (["--color"], dev_runner.RunnerArgs(mode="dev", enable_color=True)),
        (["--dev", "--color"], dev_runner.RunnerArgs(mode="dev", enable_color=True)),
        (["-d", "--color"], dev_runner.RunnerArgs(mode="dev", enable_color=True)),
        (["--color", "--dev"], dev_runner.RunnerArgs(mode="dev", enable_color=True)),
        (["--test", "--color"], dev_runner.RunnerArgs(mode="test", test_suite="all", enable_color=True)),
        (["-t", "--color"], dev_runner.RunnerArgs(mode="test", test_suite="all", enable_color=True)),
        (["--color", "--test"], dev_runner.RunnerArgs(mode="test", test_suite="all", enable_color=True)),
        (
            ["--test", "--backend", "--color"],
            dev_runner.RunnerArgs(mode="test", test_suite="backend", enable_color=True),
        ),
        (
            ["--color", "--test", "--frontend"],
            dev_runner.RunnerArgs(mode="test", test_suite="frontend", enable_color=True),
        ),
        (
            ["--interactive", "--color", "--interview-style", "behavioral_focus"],
            dev_runner.RunnerArgs(
                mode="interactive",
                cli_args=("--color", "--interview-style", "behavioral_focus"),
            ),
        ),
        (
            ["-i", "--help"],
            dev_runner.RunnerArgs(mode="interactive", cli_args=("--help",)),
        ),
        (
            ["--color", "-i", "--interview-style", "behavioral_focus"],
            dev_runner.RunnerArgs(
                mode="interactive",
                cli_args=("--color", "--interview-style", "behavioral_focus"),
            ),
        ),
        (
            ["--benchmark", "--interview-style", "behavioral_focus"],
            dev_runner.RunnerArgs(
                mode="interactive",
                cli_args=("--benchmark", "--color", "--interview-style", "behavioral_focus"),
            ),
        ),
        (
            ["--color", "-b", "--interview-style", "behavioral_focus"],
            dev_runner.RunnerArgs(
                mode="interactive",
                cli_args=("--benchmark", "--color", "--interview-style", "behavioral_focus"),
            ),
        ),
        (
            ["-b", "--color", "--interview-style", "behavioral_focus"],
            dev_runner.RunnerArgs(
                mode="interactive",
                cli_args=("--benchmark", "--color", "--interview-style", "behavioral_focus"),
            ),
        ),
        (["--help"], dev_runner.RunnerArgs(mode="help")),
        (["--help", "--color"], dev_runner.RunnerArgs(mode="help", enable_color=True)),
        (["-h"], dev_runner.RunnerArgs(mode="help")),
    ],
)
def test_parse_args_accepts_known_flags(argv, expected):
    assert dev_runner.parse_args(argv) == expected


@pytest.mark.parametrize(
    ("argv", "match"),
    [
        (["--dev", "--frontend"], "--dev does not accept additional flags"),
        (["-d", "--benchmark"], "benchmark cannot be combined with dev mode"),
        (["--test", "--backend", "--frontend"], "Expected at most one test suite selector"),
        (["--test", "--benchmark"], "benchmark cannot be combined with test mode"),
        (["--test", "--unknown"], "Unsupported test suite selector"),
        (["--backend"], "--backend must be used with --test"),
        (["--benchmark-json"], "--benchmark-json is a prepper-cli flag"),
        (["--unknown"], "Unsupported flag"),
        (["--color", "--color"], "--color can only be used once"),
    ],
)
def test_parse_args_rejects_invalid_combinations(argv, match):
    with pytest.raises(ValueError, match=match):
        dev_runner.parse_args(argv)


def test_print_usage_groups_modes(monkeypatch):
    messages = []

    monkeypatch.setattr(dev_runner, "log", messages.append)

    dev_runner.print_usage()
    help_text = "\n".join(messages)

    assert "Usage: ./prepper.sh [-h] [--setup]" in help_text
    assert "[--interview-style INTERVIEW_STYLE]" in help_text
    assert "[--list-interview-styles]" in help_text
    assert "[--temperature TEMPERATURE]" in help_text
    assert "[--benchmark-model BENCHMARK_MODEL]" in help_text
    assert "Setup:" in help_text
    assert "Dev servers:" in help_text
    assert "Tests:" in help_text
    assert "Interactive CLI:" in help_text
    assert "Benchmark:" in help_text
    assert "--interactive --help" in help_text
    assert "--temperature N" in help_text
    assert "--top-p N" in help_text
    assert "--frequency-penalty N" in help_text
    assert "--presence-penalty N" in help_text
    assert "--max-tokens N" in help_text
    assert "--benchmark-model MODEL" in help_text
    assert "transcript color is on by default" in help_text


def test_print_usage_can_use_argparse_colors(monkeypatch):
    messages = []

    monkeypatch.setenv("PYTHON_COLORS", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(dev_runner, "log", messages.append)

    dev_runner.print_usage()
    help_text = "\n".join(messages)

    assert "\033[1;34mUsage:\033[0m" in help_text
    assert "[\033[36m--interview-style\033[0m \033[33mINTERVIEW_STYLE\033[0m]" in help_text
    assert "[\033[36m--temperature\033[0m \033[33mTEMPERATURE\033[0m]" in help_text
    assert "\033[1;36m--max-tokens\033[0m \033[1;33mN\033[0m" in help_text


def test_main_can_force_colored_help(monkeypatch):
    messages = []

    monkeypatch.setattr(dev_runner, "log", messages.append)
    monkeypatch.setattr(dev_runner, "validate_layout", lambda: None)
    monkeypatch.setattr("sys.argv", ["prepper.sh", "--help", "--color"])

    assert dev_runner.main() == 0
    assert "\033[1;34mUsage:\033[0m" in "\n".join(messages)


def test_resolve_backend_python_prefers_backend_venv(monkeypatch, tmp_path):
    backend_dir = tmp_path / "backend"
    venv_bin = backend_dir / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    python_path = venv_bin / "python"
    python_path.write_text("#!/bin/sh\n", encoding="utf-8")
    python_path.chmod(0o755)

    monkeypatch.setattr(dev_runner, "BACKEND_DIR", backend_dir)

    assert dev_runner.resolve_backend_python() == str(python_path)


def test_resolve_backend_python_falls_back_to_current_interpreter(monkeypatch, tmp_path):
    monkeypatch.setattr(dev_runner, "BACKEND_DIR", tmp_path / "backend")

    assert dev_runner.resolve_backend_python() == sys.executable


def test_run_cli_mode_requires_prepper_cli_venv(monkeypatch, tmp_path):
    messages = []

    monkeypatch.setattr(dev_runner, "CLI_VENV_PYTHON", tmp_path / "python")
    monkeypatch.setattr(dev_runner, "log", messages.append)

    assert dev_runner.run_cli_mode(("--help",)) == 1
    assert "prepper-cli virtualenv is missing" in messages[0]
    assert "Run ./prepper.sh --setup" in messages[1]


def test_run_cli_mode_forwards_args_with_wrapper_prog(monkeypatch, tmp_path):
    calls = []
    cli_dir = tmp_path / "prepper-cli"
    cli_dir.mkdir()
    python_path = tmp_path / "python"
    python_path.write_text("#!/bin/sh\n", encoding="utf-8")
    python_path.chmod(0o755)

    def fake_call(cmd, cwd, env):
        calls.append((cmd, cwd, env["PREPPER_CLI_PROG"]))
        return 0

    monkeypatch.setattr(dev_runner, "CLI_DIR", cli_dir)
    monkeypatch.setattr(dev_runner, "CLI_VENV_PYTHON", python_path)
    monkeypatch.setattr(dev_runner.subprocess, "call", fake_call)

    assert dev_runner.run_cli_mode(("--benchmark", "--color", "--interview-style", "behavioral_focus")) == 0
    assert calls == [
        (
            [str(python_path), "-m", "prepper_cli.main", "--benchmark", "--color", "--interview-style", "behavioral_focus"],
            cli_dir,
            "./prepper.sh --interactive",
        )
    ]


def test_setup_runner_validates_layout(monkeypatch, tmp_path):
    monkeypatch.setattr(setup_runner, "PREPPER_CLI_DIR", tmp_path / "prepper-cli")
    monkeypatch.setattr(setup_runner, "BACKEND_DIR", tmp_path / "backend")
    monkeypatch.setattr(setup_runner, "FRONTEND_DIR", tmp_path / "frontend")

    with pytest.raises(ValueError, match="project root"):
        setup_runner.validate_layout()


def test_setup_runner_creates_missing_env_files_from_examples(monkeypatch, tmp_path):
    messages = []
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (tmp_path / ".env.example").write_text("LLM_API_KEY=\n", encoding="utf-8")
    (frontend_dir / ".env.local.example").write_text(
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:5000\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(setup_runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(setup_runner, "FRONTEND_DIR", frontend_dir)

    setup_runner.ensure_env_files(messages.append)

    assert (tmp_path / ".env").read_text(encoding="utf-8") == "LLM_API_KEY=\n"
    assert (frontend_dir / ".env.local").read_text(encoding="utf-8").startswith("NEXT_PUBLIC_API_URL=")
    assert len(messages) == 2


def test_setup_runner_builds_expected_install_commands(tmp_path):
    cli_python = tmp_path / "prepper-cli" / ".venv" / "bin" / "python"
    backend_python = tmp_path / "backend" / ".venv" / "bin" / "python"

    commands = setup_runner.setup_commands(cli_python, backend_python)

    assert commands[0] == (
        [str(cli_python), "-m", "pip", "install", "--upgrade", "pip"],
        setup_runner.PREPPER_CLI_DIR,
    )
    assert commands[1][0] == [
        str(cli_python),
        "-m",
        "pip",
        "install",
        "--editable",
        str(setup_runner.PREPPER_CLI_DIR),
    ]
    assert commands[-1] == (["npm", "install"], setup_runner.FRONTEND_DIR)


def test_select_test_suites_defaults_to_all_in_order():
    suites = test_runner.select_test_suites("python", "all")

    assert [suite.name for suite in suites] == [
        "backend-test",
        "prepper-cli-test",
        "tools-test",
        "frontend-test",
    ]
    assert suites[0].cmd == ["python", "-m", "pytest", "tests", "-q"]
    assert suites[1].cwd == test_runner.CLI_DIR
    assert suites[2].cmd == ["python", "-m", "pytest", "tools", "-q"]
    assert suites[2].cwd == test_runner.PROJECT_ROOT
    assert suites[3].cmd == ["npm", "run", "test:unit"]
    assert suites[0].env is not None
    assert suites[0].env["PYTHONUNBUFFERED"] == "1"
    assert "FORCE_COLOR" not in suites[0].env


def test_select_test_suites_can_enable_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")

    suites = test_runner.select_test_suites("python", "all", enable_color=True)

    assert suites[0].cmd == ["python", "-m", "pytest", "tests", "-q", "--color=yes"]
    assert suites[1].cmd == ["python", "-m", "pytest", "tests", "-q", "--color=yes"]
    assert suites[2].cmd == ["python", "-m", "pytest", "tools", "-q", "--color=yes"]
    assert suites[3].cmd == ["npm", "run", "test:unit"]
    for suite in suites[:3]:
        assert suite.env is not None
        assert "FORCE_COLOR" not in suite.env
        assert suite.env["NO_COLOR"] == "1"
    assert suites[3].env is not None
    assert suites[3].env["FORCE_COLOR"] == "1"
    assert "NO_COLOR" not in suites[3].env


@pytest.mark.parametrize(
    ("selector", "expected_name"),
    [
        ("backend", "backend-test"),
        ("frontend", "frontend-test"),
        ("cli", "prepper-cli-test"),
        ("tools", "tools-test"),
    ],
)
def test_select_test_suites_can_select_one_suite(selector, expected_name):
    suites = test_runner.select_test_suites("python", selector)

    assert [suite.name for suite in suites] == [expected_name]


def test_run_test_mode_runs_all_suites_in_order(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env, log, enable_color=False):
        calls.append((name, cmd, cwd, env.get("PYTHONUNBUFFERED")))
        return 0

    monkeypatch.setattr(test_runner, "run_command", fake_run_command)

    assert test_runner.run_test_mode("python", "all", lambda _message: None) == 0
    assert [call[0] for call in calls] == [
        "backend-test",
        "prepper-cli-test",
        "tools-test",
        "frontend-test",
    ]


def test_run_test_mode_passes_color_to_commands(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env, log, enable_color=False):
        calls.append((name, enable_color))
        return 0

    monkeypatch.setattr(test_runner, "run_command", fake_run_command)

    assert test_runner.run_test_mode("python", "all", lambda _message: None, enable_color=True) == 0
    assert calls == [
        ("backend-test", True),
        ("prepper-cli-test", True),
        ("tools-test", True),
        ("frontend-test", True),
    ]


def test_run_test_mode_runs_one_suite(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env, log, enable_color=False):
        calls.append(name)
        return 0

    monkeypatch.setattr(test_runner, "run_command", fake_run_command)

    assert test_runner.run_test_mode("python", "frontend", lambda _message: None) == 0
    assert calls == ["frontend-test"]


def test_run_test_mode_stops_on_first_failure(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env, log, enable_color=False):
        calls.append(name)
        return 7 if name == "prepper-cli-test" else 0

    monkeypatch.setattr(test_runner, "run_command", fake_run_command)

    assert test_runner.run_test_mode("python", "all", lambda _message: None) == 7
    assert calls == ["backend-test", "prepper-cli-test"]


def test_start_processes_configures_dev_server_commands(monkeypatch):
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(pid=100 + len(calls), stdout=None)

    monkeypatch.setattr(dev_server.subprocess, "Popen", fake_popen)

    processes = dev_server.start_processes("python")

    assert list(processes.keys()) == ["backend", "frontend"]
    assert calls[0][0][0] == ["python", "run.py"]
    assert calls[0][1]["cwd"] == dev_server.BACKEND_DIR
    assert calls[0][1]["env"]["PYTHONUNBUFFERED"] == "1"
    assert calls[0][1]["preexec_fn"] == dev_server.os.setsid
    assert calls[1][0][0] == ["npm", "run", "dev"]
    assert calls[1][1]["cwd"] == dev_server.FRONTEND_DIR
    assert calls[1][1]["preexec_fn"] == dev_server.os.setsid


def test_start_processes_can_enable_color(monkeypatch):
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(pid=100 + len(calls), stdout=None)

    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(dev_server.subprocess, "Popen", fake_popen)

    processes = dev_server.start_processes("python", enable_color=True)

    assert list(processes.keys()) == ["backend", "frontend"]
    assert calls[0][1]["env"]["PYTHONUNBUFFERED"] == "1"
    assert calls[0][1]["env"]["FORCE_COLOR"] == "1"
    assert "NO_COLOR" not in calls[0][1]["env"]
    assert calls[1][1]["env"]["FORCE_COLOR"] == "1"
    assert "NO_COLOR" not in calls[1][1]["env"]


def test_stream_output_colorizes_only_prefix():
    messages = []
    pipe = io.StringIO("child \033[31moutput\033[0m\n")

    dev_server.stream_output("backend", pipe, messages.append, enable_color=True)

    assert messages == ["\033[32m[backend]\033[0m child \033[31moutput\033[0m"]


def test_test_runner_stream_output_colorizes_only_prefix():
    messages = []
    pipe = io.StringIO("child output\n")

    test_runner.stream_output("frontend-test", pipe, messages.append, enable_color=True)

    assert messages == ["\033[34m[frontend-test]\033[0m child output"]


def test_validate_layout_exits_when_required_dirs_missing(monkeypatch, tmp_path):
    messages = []

    monkeypatch.setattr(dev_runner, "BACKEND_DIR", tmp_path / "backend")
    monkeypatch.setattr(dev_runner, "FRONTEND_DIR", tmp_path / "frontend")
    monkeypatch.setattr(dev_runner, "log", messages.append)

    with pytest.raises(SystemExit) as exc:
        dev_runner.validate_layout()

    assert exc.value.code == 1
    assert "backend/, frontend/, and prepper-cli/" in messages[0]
