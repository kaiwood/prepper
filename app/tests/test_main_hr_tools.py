import json

from prepper_cli import main
from prepper_cli.hr_context import HrToolResult, build_mock_hr_context, write_hr_context
from prepper_cli.hr_fixtures import validate_hr_fixture


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
    assert "Chunks: 1" in captured.out
    assert "workforce-planning software" not in captured.out


def test_hr_tool_run_extract_candidate_profile_mock_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "extract_candidate_profile",
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
    assert payload["tool_name"] == "extract_candidate_profile"
    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "mock"
    assert "SQL" in payload["output"]["profile"]["skills"]


def test_hr_tool_run_extract_candidate_profile_mock_prints_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "extract_candidate_profile",
            "--fixture",
            "demo_hr",
            "--mode",
            "mock",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Tool: extract_candidate_profile" in captured.out
    assert "Status: success" in captured.out
    assert "Skills:" in captured.out
    assert "Experience:" in captured.out
    assert "SQL" not in captured.out


def test_hr_tool_run_retrieve_company_context_mock_prints_json(
    monkeypatch, tmp_path, capsys
):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    context_path = write_hr_context(context, tmp_path / "hr-context.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "retrieve_company_context",
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
    assert payload["tool_name"] == "retrieve_company_context"
    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "mock"
    assert payload["output"]["query"] == "company values"
    assert any(
        snippet["source_uri"] == "fixture://company.md"
        for snippet in payload["output"]["snippets"]
    )


def test_hr_tool_run_retrieve_company_context_mock_prints_summary(
    monkeypatch, tmp_path, capsys
):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    context_path = write_hr_context(context, tmp_path / "hr-context.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "retrieve_company_context",
            "--context",
            str(context_path),
            "--query",
            "company values",
            "--mode",
            "mock",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Tool: retrieve_company_context" in captured.out
    assert "Status: success" in captured.out
    assert "Query: company values" in captured.out
    assert "Snippets: 3" in captured.out
    assert "workforce-planning software" not in captured.out


def test_hr_tool_run_retrieve_company_context_reports_missing_context(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "retrieve_company_context",
            "--query",
            "company values",
            "--mode",
            "mock",
            "--json",
        ],
    )

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "requires --context" in captured.err


def test_hr_tool_run_extract_candidate_profile_reports_missing_fixture(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "tool",
            "run",
            "extract_candidate_profile",
            "--mode",
            "mock",
            "--json",
        ],
    )

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "requires --fixture" in captured.err or "candidate text" in captured.err


def test_hr_tool_run_fetch_company_website_live_prints_json(monkeypatch, capsys):
    captured_kwargs = {}

    def fake_fetch(**kwargs):
        captured_kwargs.update(kwargs)
        return HrToolResult(
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
        )

    monkeypatch.setattr(
        "prepper_cli.main.run_fetch_company_website_tool",
        fake_fetch,
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
            "--allow-private-url-fetch",
            "--json",
        ],
    )

    assert main.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert captured_kwargs["allow_private_url_fetch"] is True
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
