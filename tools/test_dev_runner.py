import sys

import pytest

from tools import dev_runner


def test_parse_mode_defaults_to_dev():
    assert dev_runner.parse_mode([]) == "dev"


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--dev"], "dev"),
        (["--test"], "test"),
        (["--help"], "help"),
        (["-h"], "help"),
    ],
)
def test_parse_mode_accepts_known_flags(argv, expected):
    assert dev_runner.parse_mode(argv) == expected


def test_parse_mode_rejects_extra_or_unknown_flags():
    with pytest.raises(ValueError, match="Expected at most one flag"):
        dev_runner.parse_mode(["--dev", "--test"])

    with pytest.raises(ValueError, match="Unsupported flag"):
        dev_runner.parse_mode(["--unknown"])


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


def test_run_test_mode_runs_suites_in_order(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env):
        calls.append((name, cmd, cwd, env.get("PYTHONUNBUFFERED")))
        return 0

    monkeypatch.setattr(dev_runner, "run_command", fake_run_command)

    assert dev_runner.run_test_mode("python") == 0
    assert [call[0] for call in calls] == [
        "backend-test",
        "prepper-cli-test",
        "tools-test",
        "frontend-test",
    ]
    assert calls[0][1] == ["python", "-m", "pytest", "tests", "-q"]
    assert calls[1][2] == dev_runner.PROJECT_ROOT / "prepper-cli"
    assert calls[2][1] == ["python", "-m", "pytest", "tools", "-q"]
    assert calls[2][2] == dev_runner.PROJECT_ROOT
    assert calls[3][1] == ["npm", "run", "test:unit"]
    assert calls[0][3] == "1"


def test_run_test_mode_stops_on_first_failure(monkeypatch):
    calls = []

    def fake_run_command(name, cmd, cwd, env):
        calls.append(name)
        return 7 if name == "prepper-cli-test" else 0

    monkeypatch.setattr(dev_runner, "run_command", fake_run_command)

    assert dev_runner.run_test_mode("python") == 7
    assert calls == ["backend-test", "prepper-cli-test"]


def test_validate_layout_exits_when_required_dirs_missing(monkeypatch, tmp_path):
    messages = []

    monkeypatch.setattr(dev_runner, "BACKEND_DIR", tmp_path / "backend")
    monkeypatch.setattr(dev_runner, "FRONTEND_DIR", tmp_path / "frontend")
    monkeypatch.setattr(dev_runner, "log", messages.append)

    with pytest.raises(SystemExit) as exc:
        dev_runner.validate_layout()

    assert exc.value.code == 1
    assert "backend/ and frontend/" in messages[0]
