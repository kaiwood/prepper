import json

from prepper_cli import main
from prepper_cli.hr_context import HrToolResult


def test_hr_tool_run_fetch_company_website_mock_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "fetch_company_website",
            "--fixture",
            "demo_hr",
            "--mode",
            "mock",
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["tool_name"] == "fetch_company_website"
    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "mock"
    assert payload["output"]["source"]["uri"] == "fixture://company.md"
    assert payload["output"]["document"]["title"] == "Northstar Analytics"


def test_hr_tool_run_fetch_company_website_mock_prints_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "fetch_company_website",
            "--fixture",
            "demo_hr",
            "--mode",
            "mock",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Tool: fetch_company_website" in captured.out
    assert "Status: success" in captured.out
    assert "Source: Northstar Analytics (fixture://company.md)" in captured.out
    assert "Chunks: 4" in captured.out
    assert "workforce-planning software" not in captured.out


def test_hr_tool_run_fetch_company_website_live_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "prepper_cli.main.run_fetch_company_website_tool",
        lambda **_kwargs: HrToolResult(
            tool_name="fetch_company_website",
            status="success",
            output={
                "mode": "llm",
                "source": {
                    "id": "company_website",
                    "kind": "company",
                    "title": "Example",
                    "uri": "https://example.com",
                    "content_sha256": "abc",
                },
                "document": {
                    "source_id": "company_website",
                    "title": "Example",
                    "markdown": "Example company facts",
                    "summary": "Example company facts",
                },
                "chunks": [],
                "fetch_metadata": {
                    "url": "https://example.com",
                    "content_type": "text/html",
                    "byte_count": 21,
                    "truncated": False,
                },
            },
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "fetch_company_website",
            "--url",
            "https://example.com",
            "--mode",
            "llm",
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["output"]["mode"] == "llm"
    assert payload["output"]["source"]["uri"] == "https://example.com"


def test_hr_tool_run_fetch_company_website_reports_missing_fixture(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "fetch_company_website",
            "--mode",
            "mock",
            "--json",
        ],
    )

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "requires --fixture" in captured.err


def test_hr_tool_run_fetch_company_website_reports_live_error(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "fetch_company_website",
            "--url",
            "file:///etc/passwd",
            "--mode",
            "llm",
            "--json",
        ],
    )

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "scheme" in captured.err
