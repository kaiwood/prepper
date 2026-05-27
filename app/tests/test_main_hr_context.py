import json
from pathlib import Path

from prepper_cli import main
from prepper_cli.hr_context import build_mock_hr_context, hr_context_to_json, write_hr_context
from prepper_cli.hr_fixtures import validate_hr_fixture


def test_hr_context_build_command_writes_context(monkeypatch, tmp_path: Path, capsys):
    output_path = tmp_path / "hr-context.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "context",
            "build",
            "--fixture",
            "demo_hr",
            "--mode",
            "mock",
            "--out",
            str(output_path),
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Wrote HR context 'hrctx_demo_hr_" in captured.out
    assert output_path.is_file()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["fixture_id"] == "demo_hr"
    assert payload["mode"] == "mock"
    assert len(payload["chunks"]) == 8
    assert payload["chunks"][0]["id"] == "company_chunk_001"
    assert payload["candidate_profile"]["skills"]
    assert [result["tool_name"] for result in payload["tool_results"]] == [
        "extract_candidate_profile"
    ]


def test_hr_context_inspect_command_prints_safe_summary(monkeypatch, tmp_path: Path, capsys):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    context_path = write_hr_context(context, tmp_path / "hr-context.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "context",
            "inspect",
            "--context",
            str(context_path),
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert f"Context: {context.context_id}" in captured.out
    assert "Sources: 6" in captured.out
    assert "Chunks: 8" in captured.out
    assert "Replay transcripts: 2" in captured.out
    assert "Jordan Lee" not in captured.out


def test_hr_context_inspect_command_prints_validated_json(monkeypatch, tmp_path: Path, capsys):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    context_path = write_hr_context(context, tmp_path / "hr-context.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "context",
            "inspect",
            "--context",
            str(context_path),
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == hr_context_to_json(context)


def test_hr_context_retrieve_command_prints_json(monkeypatch, tmp_path: Path, capsys):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    context_path = write_hr_context(context, tmp_path / "hr-context.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "context",
            "retrieve",
            "--context",
            str(context_path),
            "--query",
            "company values",
            "--mode",
            "mock",
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["query"] == "company values"
    assert [result["id"] for result in payload["results"]] == [
        "company_chunk_003",
        "company_chunk_004",
    ]


def test_hr_context_retrieve_command_reports_llm_config_error(
    monkeypatch, tmp_path: Path, capsys
):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    context_path = write_hr_context(context, tmp_path / "hr-context.json")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "")
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "context",
            "retrieve",
            "--context",
            str(context_path),
            "--query",
            "company values",
            "--mode",
            "llm",
            "--json",
        ],
    )

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "OPENROUTER_API_KEY" in captured.err
