import json
from pathlib import Path

from prepper_cli import main


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "hr" / "demo_hr"


def test_hr_interview_replay_command_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "interview",
            "replay",
            "--fixture",
            "demo_hr",
            "--transcript",
            str(FIXTURE_ROOT / "transcripts" / "strong.md"),
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "hr-interview-summary.v1"
    assert payload["workflow"] == "hr_interview"
    assert payload["mode"] == "mock"
    assert payload["execution"] == "replay"
    assert payload["candidate"] == "strong"
    assert payload["final_result"]["overall_score"] == 8.4
    assert payload["tool_calls"][0]["result"]["tool_name"] == "retrieve_company_context"


def test_hr_interview_replay_command_prints_safe_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "interview",
            "replay",
            "--fixture",
            "demo_hr",
            "--transcript",
            str(FIXTURE_ROOT / "transcripts" / "weak.md"),
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "HR interview replay: demo_hr / weak" in captured.out
    assert "Final score: 4.2" in captured.out
    assert "Passed: false" in captured.out
    assert "I helped with a dashboard" not in captured.out
    assert "Jordan Lee" not in captured.out


def test_hr_interview_replay_command_reports_invalid_transcript(monkeypatch, tmp_path, capsys):
    transcript_path = tmp_path / "bad.md"
    transcript_path.write_text(
        "---\nfixture: demo_hr\ncandidate: strong\n---\n\n## Candidate\n\nAnswer",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "interview",
            "replay",
            "--fixture",
            "demo_hr",
            "--transcript",
            str(transcript_path),
            "--json",
        ],
    )

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "first turn" in captured.err
