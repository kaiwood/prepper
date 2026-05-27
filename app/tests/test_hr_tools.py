from __future__ import annotations

import socket
from email.message import Message
from urllib.error import URLError

import pytest

from prepper_cli.hr_fixtures import validate_hr_fixture
from prepper_cli.hr_tools import (
    FETCH_COMPANY_WEBSITE_TOOL_NAME,
    HrToolError,
    company_website_tool_result_to_context_entries,
    hr_tool_result_to_dict,
    run_fetch_company_website_tool,
)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        url: str = "https://example.com/about",
        content_type: str = "text/html; charset=utf-8",
        content_length: int | None = None,
    ):
        self._body = body
        self._url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self.closed = False

    def read(self, _size: int) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url

    def close(self) -> None:
        self.closed = True


def test_fetch_company_website_mock_returns_fixture_content():
    fixture = validate_hr_fixture("demo_hr")

    result = run_fetch_company_website_tool(mode="mock", fixture=fixture)
    payload = hr_tool_result_to_dict(result)

    assert payload["tool_name"] == FETCH_COMPANY_WEBSITE_TOOL_NAME
    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "mock"
    assert payload["output"]["source"]["uri"] == "fixture://company.md"
    assert payload["output"]["source"]["title"] == "Northstar Analytics"
    assert "Northstar Analytics builds workforce-planning" in payload["output"]["document"]["markdown"]
    assert payload["output"]["fetch_metadata"]["content_type"] == "text/markdown; charset=utf-8"
    assert [chunk["id"] for chunk in payload["output"]["chunks"]] == [
        "company_website_chunk_001",
        "company_website_chunk_002",
        "company_website_chunk_003",
        "company_website_chunk_004",
    ]


def test_fetch_company_website_live_extracts_readable_html(monkeypatch):
    html = b"""
    <html>
      <head><title>Example Careers</title><script>ignore()</script></head>
      <body>
        <nav>menu should not appear</nav>
        <h1>Example Company</h1>
        <p>We build useful HR software.</p>
        <p>Privacy-first analytics for hiring teams.</p>
      </body>
    </html>
    """

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://example.com/about"
        assert timeout == 10.0
        return FakeResponse(html)

    monkeypatch.setattr("prepper_cli.hr_tools.urlopen", fake_urlopen)

    result = run_fetch_company_website_tool(
        mode="llm", url="https://example.com/about"
    )
    payload = hr_tool_result_to_dict(result)

    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "llm"
    assert payload["output"]["source"]["uri"] == "https://example.com/about"
    assert payload["output"]["source"]["title"] == "Example Careers"
    assert "We build useful HR software." in payload["output"]["document"]["markdown"]
    assert "menu should not appear" not in payload["output"]["document"]["markdown"]
    assert payload["output"]["fetch_metadata"]["byte_count"] == len(html)


def test_fetch_company_website_rejects_invalid_scheme():
    with pytest.raises(HrToolError, match="scheme"):
        run_fetch_company_website_tool(mode="llm", url="file:///etc/passwd")


def test_fetch_company_website_reports_timeout(monkeypatch):
    def fake_urlopen(_request, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr("prepper_cli.hr_tools.urlopen", fake_urlopen)

    with pytest.raises(HrToolError, match="timed out"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com")


def test_fetch_company_website_reports_url_failure(monkeypatch):
    def fake_urlopen(_request, timeout):
        raise URLError("blocked")

    monkeypatch.setattr("prepper_cli.hr_tools.urlopen", fake_urlopen)

    with pytest.raises(HrToolError, match="fetch failed"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com")


def test_fetch_company_website_reports_socket_timeout(monkeypatch):
    def fake_urlopen(_request, timeout):
        raise socket.timeout("slow")

    monkeypatch.setattr("prepper_cli.hr_tools.urlopen", fake_urlopen)

    with pytest.raises(HrToolError, match="timed out"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com")


def test_fetch_company_website_rejects_oversized_content_length(monkeypatch):
    def fake_urlopen(_request, timeout):
        return FakeResponse(b"small", content_length=20)

    monkeypatch.setattr("prepper_cli.hr_tools.urlopen", fake_urlopen)

    with pytest.raises(HrToolError, match="size limit"):
        run_fetch_company_website_tool(
            mode="llm", url="https://example.com", max_bytes=10
        )


def test_fetch_company_website_rejects_oversized_body(monkeypatch):
    def fake_urlopen(_request, timeout):
        return FakeResponse(b"01234567890", content_length=None)

    monkeypatch.setattr("prepper_cli.hr_tools.urlopen", fake_urlopen)

    with pytest.raises(HrToolError, match="size limit"):
        run_fetch_company_website_tool(
            mode="llm", url="https://example.com", max_bytes=10
        )


def test_fetch_company_website_mock_and_live_have_same_output_shape(monkeypatch):
    fixture = validate_hr_fixture("demo_hr")
    monkeypatch.setattr(
        "prepper_cli.hr_tools.urlopen",
        lambda _request, timeout: FakeResponse(
            b"<html><head><title>Example</title></head><body><p>Company facts</p></body></html>"
        ),
    )

    mock_payload = hr_tool_result_to_dict(
        run_fetch_company_website_tool(mode="mock", fixture=fixture)
    )
    live_payload = hr_tool_result_to_dict(
        run_fetch_company_website_tool(mode="llm", url="https://example.com")
    )

    assert mock_payload.keys() == live_payload.keys()
    assert mock_payload["output"].keys() == live_payload["output"].keys()
    assert mock_payload["output"]["source"].keys() == live_payload["output"]["source"].keys()
    assert mock_payload["output"]["document"].keys() == live_payload["output"]["document"].keys()
    assert mock_payload["output"]["fetch_metadata"].keys() == live_payload["output"]["fetch_metadata"].keys()


def test_company_website_tool_result_converts_to_context_entries():
    result = run_fetch_company_website_tool(
        mode="mock", fixture=validate_hr_fixture("demo_hr")
    )

    source, document, chunks = company_website_tool_result_to_context_entries(result)

    assert source.id == "company_website"
    assert source.uri == "fixture://company.md"
    assert document.source_id == source.id
    assert document.title == "Northstar Analytics"
    assert chunks[0].metadata["source_uri"] == "fixture://company.md"
    assert chunks[0].source_id == "company_website"
