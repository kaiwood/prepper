from __future__ import annotations

import socket
from dataclasses import replace
from email.message import Message
from urllib.error import URLError

import pytest

from prepper_cli.hr_context import build_mock_hr_context
from prepper_cli.hr_fixtures import validate_hr_fixture
from prepper_cli.hr_tools import (
    EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
    FETCH_COMPANY_WEBSITE_TOOL_NAME,
    RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
    HrToolError,
    candidate_profile_tool_result_to_profile,
    company_website_tool_result_to_context_entries,
    hr_tool_result_to_dict,
    run_extract_candidate_profile_tool,
    run_fetch_company_website_tool,
    run_retrieve_company_context_tool,
)


class FakeLlmResponse:
    def __init__(self, content: str):
        self.content = content


class FakeCandidateProfileLlm:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return FakeLlmResponse(self.content)


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


def test_extract_candidate_profile_mock_returns_structured_profile():
    fixture = validate_hr_fixture("demo_hr")

    result = run_extract_candidate_profile_tool(mode="mock", fixture=fixture)
    payload = hr_tool_result_to_dict(result)

    assert payload["tool_name"] == EXTRACT_CANDIDATE_PROFILE_TOOL_NAME
    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "mock"
    assert "SQL" in payload["output"]["profile"]["skills"]
    assert "Customer Insights Analyst, BrightPath HR Software" in payload["output"]["profile"]["experience"]
    assert payload["output"]["profile"]["seniority_signals"]
    assert payload["output"]["profile"]["risks"]
    assert payload["output"]["profile"]["interview_focus_areas"]
    assert payload["output"]["input_metadata"]["combined_char_count"] > 0


def test_extract_candidate_profile_converts_to_context_profile():
    result = run_extract_candidate_profile_tool(
        mode="mock", fixture=validate_hr_fixture("demo_hr")
    )

    profile = candidate_profile_tool_result_to_profile(result)

    assert "SQL" in profile.skills
    assert profile.interview_focus_areas


def test_retrieve_company_context_mock_returns_source_snippets():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    result = run_retrieve_company_context_tool(
        mode="mock",
        context=context,
        query="company values",
    )
    payload = hr_tool_result_to_dict(result)

    assert payload["tool_name"] == RETRIEVE_COMPANY_CONTEXT_TOOL_NAME
    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "mock"
    assert payload["output"]["query"] == "company values"
    assert payload["output"]["result_count"] == 2
    assert [snippet["chunk_id"] for snippet in payload["output"]["snippets"]] == [
        "company_chunk_003",
        "company_chunk_004",
    ]
    assert payload["output"]["snippets"][0]["source_title"] == "Northstar Analytics"
    assert payload["output"]["snippets"][0]["source_uri"] == "fixture://company.md"
    assert payload["output"]["snippets"][0]["metadata"]["source_kind"] == "company"


def test_retrieve_company_context_can_return_role_snippets():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    result = run_retrieve_company_context_tool(
        mode="mock",
        context=context,
        query="success signals customer-facing hr analytics",
    )
    payload = hr_tool_result_to_dict(result)

    assert any(
        snippet["source_kind"] == "role" for snippet in payload["output"]["snippets"]
    )


def test_retrieve_company_context_empty_chunks_returns_empty_result():
    context = replace(build_mock_hr_context(validate_hr_fixture("demo_hr")), chunks=())

    result = run_retrieve_company_context_tool(
        mode="mock",
        context=context,
        query="company values",
    )
    payload = hr_tool_result_to_dict(result)

    assert payload["output"]["snippets"] == []
    assert payload["output"]["result_count"] == 0


def test_retrieve_company_context_rejects_empty_query():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    with pytest.raises(HrToolError, match="query"):
        run_retrieve_company_context_tool(
            mode="mock",
            context=context,
            query="   ",
        )


def test_extract_candidate_profile_rejects_empty_inputs():
    with pytest.raises(HrToolError, match="must not be empty"):
        run_extract_candidate_profile_tool(
            mode="mock",
            resume_text="  ",
            profile_text="\n",
        )


def test_extract_candidate_profile_rejects_oversized_inputs():
    with pytest.raises(HrToolError, match="size limit"):
        run_extract_candidate_profile_tool(
            mode="mock",
            resume_text="x" * 11,
            profile_text="",
            max_chars=10,
        )


def test_extract_candidate_profile_llm_parses_langchain_json(monkeypatch):
    fake_llm = FakeCandidateProfileLlm(
        '{"skills":["SQL"],"experience":["Analyst"],'
        '"seniority_signals":["Four years experience"],'
        '"risks":["Verify depth"],'
        '"interview_focus_areas":["Probe HR analytics"]}'
    )
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_candidate_profile_llm",
        lambda model: fake_llm,
    )

    result = run_extract_candidate_profile_tool(
        mode="llm",
        resume_text="# Resume\nSQL analyst",
        profile_text="# Profile\nFour years experience",
    )
    payload = hr_tool_result_to_dict(result)

    assert payload["output"]["mode"] == "llm"
    assert payload["output"]["profile"]["skills"] == ["SQL"]
    assert fake_llm.messages[0][0] == "system"


def test_extract_candidate_profile_llm_reports_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_candidate_profile_llm",
        lambda model: FakeCandidateProfileLlm("not json"),
    )

    with pytest.raises(HrToolError, match="invalid JSON"):
        run_extract_candidate_profile_tool(
            mode="llm",
            resume_text="# Resume\nSQL analyst",
            profile_text="# Profile\nFour years experience",
        )


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
