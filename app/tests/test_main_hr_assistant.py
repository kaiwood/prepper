import json

from prepper_cli import main


def test_hr_assistant_ask_command_prints_json(capsys, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "assistant",
            "ask",
            "--fixture",
            "demo_hr",
            "--message",
            "What should I ask this candidate first?",
            "--mode",
            "mock",
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "hr-assistant-response.v1"
    assert payload["status"] == "success"
    assert payload["context_id"].startswith("hrctx_demo_hr_")
    assert payload["tool_results"][-1]["tool_name"] == "retrieve_company_context"


def test_hr_assistant_ask_command_guides_setup_without_fixture(capsys, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "assistant",
            "ask",
            "--message",
            "How do I start?",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "HR assistant: needs_setup (mock)" in captured.out
    assert "company_url_or_text" in captured.out
