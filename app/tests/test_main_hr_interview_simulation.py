import json
from types import SimpleNamespace

from prepper_cli import main


def _summary(path="tmp/hr-strong-run.md"):
    return {
        "schema_version": "hr-interview-summary.v1",
        "workflow": "hr_interview",
        "mode": "llm",
        "execution": "simulate",
        "fixture_id": "demo_hr",
        "candidate": "strong",
        "context_id": "hrctx_demo_hr_fake",
        "transcript": {"path": path, "turn_count": 3, "tool_event_count": 2, "source_count": 1},
        "models": {"runtime": "runtime-model", "scoring": "scoring-model", "embeddings": "embedding-model"},
        "model_settings": {"temperature": 0.4, "top_p": 0.95, "frequency_penalty": 0.2, "presence_penalty": 0.1, "max_tokens": 1200},
        "turn_counts": {"total": 3, "interviewer": 2, "candidate": 1, "tool_events": 2, "sources": 1},
        "tool_calls": [{"tool_name": "retrieve_company_context", "query": "company", "result": {}}],
        "sources": [{"title": "Company", "url": "fixture://company.md", "excerpt": "Values"}],
        "final_result": {"overall_score": 8.2, "passed": True, "strengths": [], "improvements": []},
        "interview_complete": True,
        "metadata_warning": False,
    }


def test_hr_interview_simulate_command_prints_json(monkeypatch, capsys, tmp_path):
    out_path = tmp_path / "run.md"
    calls = []

    def fake_simulate_hr_interview(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(summary=_summary(str(out_path)))

    monkeypatch.setattr(main, "simulate_hr_interview", fake_simulate_hr_interview)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--model",
            "runtime-model",
            "--benchmark-model",
            "scoring-model",
            "--question-limit",
            "1",
            "hr",
            "interview",
            "simulate",
            "--fixture",
            "demo_hr",
            "--candidate",
            "strong",
            "--mode",
            "llm",
            "--out",
            str(out_path),
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["execution"] == "simulate"
    assert payload["transcript"]["path"] == str(out_path)
    assert calls == [
        {
            "fixture_id": "demo_hr",
            "candidate": "strong",
            "mode": "llm",
            "out_path": str(out_path),
            "model": "runtime-model",
            "scoring_model": "scoring-model",
            "question_limit_override": 1,
            "pass_threshold_override": None,
        }
    ]


def test_hr_interview_simulate_command_prints_safe_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "simulate_hr_interview",
        lambda **kwargs: SimpleNamespace(summary=_summary()),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "interview",
            "simulate",
            "--fixture",
            "demo_hr",
            "--candidate",
            "strong",
            "--mode",
            "llm",
            "--out",
            "tmp/hr-strong-run.md",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "HR interview simulate: demo_hr / strong" in captured.out
    assert "Final score: 8.2" in captured.out
    assert "Passed: true" in captured.out
