import sys
from types import SimpleNamespace

import pytest

from tools import dev_runner, dev_server, test_runner


def test_parse_mode_defaults_to_dev():
    assert dev_runner.parse_mode([]) == "dev"
    assert dev_runner.parse_args([]) == dev_runner.RunnerArgs(mode="dev")


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--dev"], dev_runner.RunnerArgs(mode="dev")),
        (["--test"], dev_runner.RunnerArgs(mode="test", test_suite="all")),
        (["--test", "--all"], dev_runner.RunnerArgs(mode="test", test_suite="all")),
        (["--test", "--backend"], dev_runner.RunnerArgs(mode="test", test_suite="backend")),
        (["--test", "--frontend"], dev_runner.RunnerArgs(mode="test", test_suite="frontend")),
        (["--test", "--cli"], dev_runner.RunnerArgs(mode="test", test_suite="cli")),
        (["--test", "--tools"], dev_runner.RunnerArgs(mode="test", test_suite="tools")),
        (["--help"], dev_runner.RunnerArgs(mode="help")),
        (["-h"], dev_runner.RunnerArgs(mode="help")),
    ],
)
def test_parse_args_accepts_known_flags(argv, expected):
    assert dev_runner.parse_args(argv) == expected


@pytest.mark.parametrize(
    ("argv", "match"),
    [
        (["--dev", "--frontend"], "--dev does not accept additional flags"),
        (["--test", "--backend", "--frontend"], "Expected at most one test suite selector"),
        (["--test", "--unknown"], "Unsupported test suite selector"),
        (["--backend"], "--backend must be used with --test"),
        (["--unknown"], "Unsupported flag"),
    ],
)
def test_parse_args_rejects_invalid_combinations(argv, match):
    with pytest.raises(ValueError, match=match):
        dev_runner.parse_args(argv)


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

    def fake_run_command(name, cmd, cwd, env, log):
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


def test_run_test_mode_runs_one_suite(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env, log):
        calls.append(name)
        return 0

    monkeypatch.setattr(test_runner, "run_command", fake_run_command)

    assert test_runner.run_test_mode("python", "frontend", lambda _message: None) == 0
    assert calls == ["frontend-test"]


def test_run_test_mode_stops_on_first_failure(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env, log):
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


def test_validate_layout_exits_when_required_dirs_missing(monkeypatch, tmp_path):
    messages = []

    monkeypatch.setattr(dev_runner, "BACKEND_DIR", tmp_path / "backend")
    monkeypatch.setattr(dev_runner, "FRONTEND_DIR", tmp_path / "frontend")
    monkeypatch.setattr(dev_runner, "log", messages.append)

    with pytest.raises(SystemExit) as exc:
        dev_runner.validate_layout()

    assert exc.value.code == 1
    assert "backend/ and frontend/" in messages[0]
