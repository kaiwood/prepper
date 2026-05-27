import json
from types import SimpleNamespace

from prepper_cli import main
from prepper_cli.hr_context import build_mock_hr_context, hr_context_to_dict
from prepper_cli.hr_fixtures import validate_hr_fixture


def _summary(path="tmp/hr-workflow-demo_hr-strong.md"):
    return {
        "schema_version": "hr-workflow-summary.v1",
        "workflow": "hr_workflow",
        "mode": "mock",
        "execution": "run",
        "fixture_id": "demo_hr",
        "candidate": "strong",
        "context": {
            "schema_version": "hr-context.v2",
            "context_id": "hrctx_demo_hr_fake",
            "mode": "mock",
            "fixture_id": "demo_hr",
            "company_input_count": 1,
            "candidate_input_count": 2,
            "source_count": 6,
            "chunk_count": 8,
            "tool_result_count": 1,
            "replay_transcript_count": 2,
        },
        "interview": {
            "execution": "replay",
            "candidate": "strong",
            "final_result": {"overall_score": 8.4, "passed": True},
        },
        "transcript": {"path": path},
        "models": {"runtime": None, "scoring": None, "embeddings": "mock"},
        "tool_call_count": 1,
        "source_count": 1,
        "final_result": {
            "overall_score": 8.4,
            "passed": True,
            "strengths": [],
            "improvements": [],
        },
        "interview_complete": True,
        "steps": {"context_build": "completed", "interview": "replay"},
    }


def test_hr_workflow_run_command_prints_json(monkeypatch, capsys):
    calls = []

    def fake_run_hr_workflow(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(summary=_summary())

    monkeypatch.setattr(main, "run_hr_workflow", fake_run_hr_workflow)
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
            "--pass-threshold",
            "7.5",
            "hr",
            "workflow",
            "run",
            "--fixture",
            "demo_hr",
            "--mode",
            "llm",
            "--candidate",
            "strong",
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "hr-workflow-summary.v1"
    assert payload["workflow"] == "hr_workflow"
    assert calls == [
        {
            "fixture_id": "demo_hr",
            "mode": "llm",
            "candidate": "strong",
            "out_path": None,
            "model": "runtime-model",
            "scoring_model": "scoring-model",
            "question_limit_override": 1,
            "pass_threshold_override": 7.5,
        }
    ]


def test_hr_workflow_run_command_prints_safe_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "run_hr_workflow",
        lambda **kwargs: SimpleNamespace(summary=_summary()),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "workflow",
            "run",
            "--fixture",
            "demo_hr",
            "--mode",
            "mock",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "HR workflow run: demo_hr / strong (mock)" in captured.out
    assert "Context: hrctx_demo_hr_fake" in captured.out
    assert "Final score: 8.4" in captured.out
    assert "Passed: true" in captured.out
    assert "Jordan Lee" not in captured.out
    assert "privacy-first handling" not in captured.out


def test_hr_workflow_run_command_reports_error(monkeypatch, capsys):
    def fake_run_hr_workflow(**kwargs):
        raise ValueError("llm workflow requires --candidate")

    monkeypatch.setattr(main, "run_hr_workflow", fake_run_hr_workflow)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "workflow",
            "run",
            "--fixture",
            "demo_hr",
            "--mode",
            "llm",
            "--json",
        ],
    )

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "llm workflow requires --candidate" in captured.err


def test_build_hr_context_via_api_sends_fixture_source_metadata(monkeypatch):
    calls = []
    fixture = validate_hr_fixture("demo_hr")
    context_payload = hr_context_to_dict(build_mock_hr_context(fixture))

    def fake_post_json(url, payload):
        calls.append((url, payload))
        return {"context": context_payload, "errors": []}

    monkeypatch.setattr(main, "_post_json", fake_post_json)

    context = main._build_hr_context_via_api(
        fixture_id="demo_hr",
        mode="mock",
        api_url="http://127.0.0.1:5000/",
    )

    assert context.context_id == context_payload["context_id"]
    assert calls[0][0] == "http://127.0.0.1:5000/api/hr/context"
    assert calls[0][1]["fixture_id"] == "demo_hr"
    assert calls[0][1]["source_uris"] == {
        "company": "fixture://company.md",
        "role": "fixture://role.md",
        "resume": "fixture://resume.md",
        "profile": "fixture://profile.md",
    }


def test_hr_workflow_run_command_supports_api_transport(monkeypatch, capsys):
    calls = []
    fake_context = object()

    def fake_build_context(**kwargs):
        calls.append(("api", kwargs))
        return fake_context

    def fake_run_hr_workflow(**kwargs):
        calls.append(("workflow", kwargs))
        summary = _summary()
        summary["transport"] = "api"
        return SimpleNamespace(summary=summary)

    monkeypatch.setattr(main, "_build_hr_context_via_api", fake_build_context)
    monkeypatch.setattr(main, "run_hr_workflow", fake_run_hr_workflow)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "workflow",
            "run",
            "--fixture",
            "demo_hr",
            "--mode",
            "mock",
            "--transport",
            "api",
            "--api-url",
            "http://127.0.0.1:5000",
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["transport"] == "api"
    assert calls == [
        (
            "api",
            {
                "fixture_id": "demo_hr",
                "mode": "mock",
                "api_url": "http://127.0.0.1:5000",
            },
        ),
        (
            "workflow",
            {
                "fixture_id": "demo_hr",
                "mode": "mock",
                "candidate": None,
                "out_path": None,
                "model": None,
                "scoring_model": None,
                "question_limit_override": None,
                "pass_threshold_override": None,
                "context": fake_context,
                "transport": "api",
            },
        ),
    ]
