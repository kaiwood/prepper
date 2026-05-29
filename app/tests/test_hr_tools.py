from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import replace
from email.message import Message
from urllib.error import URLError

import pytest

import prepper_cli.hr_tools as hr_tools
from prepper_cli.hr_context import build_mock_hr_context
from prepper_cli.hr_fixtures import validate_hr_fixture
from prepper_cli.hr_tools import (
    EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
    FETCH_COMPANY_WEBSITE_TOOL_NAME,
    FETCH_ROLE_DESCRIPTION_TOOL_NAME,
    FETCH_SOCIAL_PROFILE_TOOL_NAME,
    RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
    HrToolError,
    candidate_profile_tool_result_to_profile,
    company_website_tool_result_to_context_entries,
    hr_tool_result_to_dict,
    role_description_tool_result_to_context_entries,
    run_extract_candidate_profile_tool,
    run_fetch_company_website_tool,
    run_fetch_role_description_tool,
    run_fetch_social_profile_tool,
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


@pytest.fixture(autouse=True)
def isolated_vector_store(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_HR_VECTOR_STORE_DIR", str(tmp_path / "faiss"))
    monkeypatch.delenv("PREPPER_ALLOW_PRIVATE_URL_FETCH", raising=False)

    def fake_resolve(hostname):
        try:
            return (ipaddress.ip_address(hostname),)
        except ValueError:
            return (ipaddress.ip_address("93.184.216.34"),)

    monkeypatch.setattr(
        "prepper_cli.hr_tools._resolve_company_website_host_ips",
        fake_resolve,
    )
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_company_website_markdown_llm",
        lambda *, model=None: FakeCandidateProfileLlm(
            '{"company_markdown":"# Example Careers\\n\\nWe build useful HR software.\\n\\n- Privacy-first analytics for hiring teams."}'
        ),
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
    ]


def test_fetch_role_description_mock_returns_fixture_role():
    fixture = validate_hr_fixture("demo_hr")

    result = run_fetch_role_description_tool(mode="mock", fixture=fixture)
    payload = hr_tool_result_to_dict(result)

    assert payload["tool_name"] == FETCH_ROLE_DESCRIPTION_TOOL_NAME
    assert payload["status"] == "success"
    assert payload["output"]["mode"] == "mock"
    assert payload["output"]["source"]["uri"] == "fixture://role.md"
    assert payload["output"]["source"]["kind"] == "role"
    assert "Customer Success Data Analyst" in payload["output"]["role_description"]



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


def test_tool_call_logs_success(caplog):
    caplog.set_level(logging.INFO, logger="prepper_cli.observability")

    run_extract_candidate_profile_tool(mode="mock", fixture=validate_hr_fixture("demo_hr"))

    assert any(
        'event="tool_call"' in record.getMessage()
        and 'tool_name="extract_candidate_profile"' in record.getMessage()
        and 'status="success"' in record.getMessage()
        and 'duration_ms=' in record.getMessage()
        for record in caplog.records
    )


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
    assert payload["output"]["result_count"] == 3
    snippets = payload["output"]["snippets"]
    assert any(snippet["source_kind"] == "company" for snippet in snippets)
    assert any(snippet["metadata"]["field_path"] == "sources" for snippet in snippets)
    assert 0 < snippets[0]["score"] <= 1
    assert 0 < snippets[0]["relevance_percent"] <= 100
    company_snippet = next(snippet for snippet in snippets if snippet["source_kind"] == "company")
    assert company_snippet["source_title"] == "Northstar Analytics"
    assert company_snippet["source_uri"] == "fixture://company.md"
    assert company_snippet["source"] == {
        "id": "company",
        "kind": "company",
        "title": "Northstar Analytics",
        "uri": "fixture://company.md",
    }
    assert company_snippet["metadata"]["source_kind"] == "company"
    assert payload["output"]["sources"][0]["relevance_percent"] == snippets[0]["relevance_percent"]


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


def test_tool_call_logs_failure(caplog):
    caplog.set_level(logging.WARNING, logger="prepper_cli.observability")

    with pytest.raises(HrToolError, match="size limit"):
        run_extract_candidate_profile_tool(
            mode="mock",
            resume_text="candidate@example.com",
            profile_text="",
            max_chars=1,
        )

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        'event="tool_call"' in message
        and 'tool_name="extract_candidate_profile"' in message
        and 'status="error"' in message
        for message in messages
    )
    assert "candidate@example.com" not in "\n".join(messages)


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


def test_fetch_social_profile_fetches_and_summarizes(monkeypatch):
    fake_llm = FakeCandidateProfileLlm(
        '{"profile_text":"## Profile\\n- Senior analytics leader at ExampleCo"}'
    )

    def fake_api_json(*, provider, profile_identifier, oauth_token, timeout_seconds):
        assert provider == "linkedin"
        assert profile_identifier == "jane-doe"
        assert oauth_token == "token-123"
        return {"localizedFirstName": "Jane", "headline": "Senior analytics leader"}

    monkeypatch.setattr(
        "prepper_cli.hr_tools._fetch_social_profile_api_json",
        fake_api_json,
    )
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_social_profile_llm",
        lambda model: fake_llm,
    )

    result = run_fetch_social_profile_tool(
        profile_url="https://www.linkedin.com/in/jane-doe/",
        oauth_token="token-123",
    )
    payload = hr_tool_result_to_dict(result)

    assert payload["tool_name"] == FETCH_SOCIAL_PROFILE_TOOL_NAME
    assert payload["output"]["profile_text"].startswith("## Profile")
    assert payload["output"]["source"]["provider"] == "linkedin"
    assert "api_payload" not in payload["output"]
    assert fake_llm.messages[0][0] == "system"


def test_fetch_social_profile_rejects_unsupported_url():
    with pytest.raises(HrToolError, match="LinkedIn or Xing"):
        run_fetch_social_profile_tool(
            profile_url="https://example.com/person/jane",
            oauth_token="token-123",
        )



def test_fetch_role_description_llm_fetches_and_extracts(monkeypatch):
    html = b"""
    <html><head><title>Analyst job</title></head><body>
      <h1>Data Analyst</h1><p>Analyze customer success data.</p>
    </body></html>
    """

    def fake_open(request, *, timeout_seconds, allow_private_url_fetch):
        assert request.full_url == "https://example.com/jobs/analyst"
        assert "job ad fetcher" in request.headers["User-agent"]
        return FakeResponse(html, url="https://example.com/jobs/analyst")

    fake_llm = FakeCandidateProfileLlm(
        '{"role_description":"# Data Analyst\\n\\nAnalyze customer success data."}'
    )
    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_role_description_llm",
        lambda model: fake_llm,
    )

    result = run_fetch_role_description_tool(
        mode="llm", url="https://example.com/jobs/analyst"
    )
    payload = hr_tool_result_to_dict(result)

    assert payload["tool_name"] == FETCH_ROLE_DESCRIPTION_TOOL_NAME
    assert payload["output"]["role_description"].startswith("# Data Analyst")
    assert payload["output"]["source"]["uri"] == "https://example.com/jobs/analyst"
    assert fake_llm.messages[0][0] == "system"



def test_fetch_role_description_llm_reports_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        lambda _request, **_kwargs: FakeResponse(b"<html><body>Job text</body></html>"),
    )
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_role_description_llm",
        lambda model: FakeCandidateProfileLlm("not json"),
    )

    with pytest.raises(HrToolError, match="invalid JSON"):
        run_fetch_role_description_tool(
            mode="llm", url="https://example.com/jobs/analyst"
        )



def test_role_description_tool_result_converts_to_context_entries():
    fixture = validate_hr_fixture("demo_hr")
    result = run_fetch_role_description_tool(mode="mock", fixture=fixture)

    source, document, chunks = role_description_tool_result_to_context_entries(result)

    assert source.kind == "role"
    assert source.uri == "fixture://role.md"
    assert document.source_id == "role_job_ad"
    assert chunks[0].source_id == "role_job_ad"



def test_fetch_company_website_llm_fetches_and_extracts_markdown(monkeypatch):
    html = b"""
    <html><head><title>Example Careers</title></head><body>
      <nav>ignore menu</nav>
      <h1>Example Company</h1>
      <p>We build useful HR software.</p>
      <p>Privacy-first analytics for hiring teams.</p>
    </body></html>
    """

    def fake_open(request, *, timeout_seconds, allow_private_url_fetch):
        assert request.full_url == "https://example.com/about"
        assert "company website fetcher" in request.headers["User-agent"]
        return FakeResponse(html)

    fake_llm = FakeCandidateProfileLlm(
        '{"company_markdown":"# Example Company\\n\\n- Builds useful HR software.\\n- Privacy-first analytics for hiring teams."}'
    )
    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_company_website_markdown_llm",
        lambda model: fake_llm,
    )

    result = run_fetch_company_website_tool(
        mode="llm", url="https://example.com/about"
    )
    payload = hr_tool_result_to_dict(result)

    assert payload["tool_name"] == FETCH_COMPANY_WEBSITE_TOOL_NAME
    assert payload["output"]["document"]["markdown"].startswith("# Example Company")
    assert payload["output"]["source"]["title"] == "Example Company"
    assert fake_llm.messages[0][0] == "system"
    assert "ignore menu" not in fake_llm.messages[1][1]



def test_fetch_company_website_llm_reports_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        lambda _request, **_kwargs: FakeResponse(b"<html><body>Company text</body></html>"),
    )
    monkeypatch.setattr(
        "prepper_cli.hr_tools._build_company_website_markdown_llm",
        lambda model: FakeCandidateProfileLlm("not json"),
    )

    with pytest.raises(HrToolError, match="invalid JSON"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com/about")



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

    def fake_open(request, *, timeout_seconds, allow_private_url_fetch):
        assert request.full_url == "https://example.com/about"
        assert timeout_seconds == 10.0
        assert allow_private_url_fetch is False
        return FakeResponse(html)

    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)

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


def test_fetch_company_website_rejects_loopback_url():
    with pytest.raises(HrToolError, match="blocked address: 127.0.0.1"):
        run_fetch_company_website_tool(mode="llm", url="http://127.0.0.1/admin")


def test_fetch_company_website_rejects_private_dns_resolution(monkeypatch):
    monkeypatch.setattr(
        "prepper_cli.hr_tools._resolve_company_website_host_ips",
        lambda _hostname: (ipaddress.ip_address("10.0.0.5"),),
    )

    with pytest.raises(HrToolError, match="blocked address: 10.0.0.5"):
        run_fetch_company_website_tool(mode="llm", url="https://internal.example")


def test_fetch_company_website_allows_private_url_with_flag(monkeypatch):
    def fake_open(request, *, timeout_seconds, allow_private_url_fetch):
        assert request.full_url == "http://127.0.0.1/about"
        assert allow_private_url_fetch is True
        return FakeResponse(
            b"<html><body><p>Local company facts</p></body></html>",
            url="http://127.0.0.1/about",
        )

    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)

    result = run_fetch_company_website_tool(
        mode="llm",
        url="http://127.0.0.1/about",
        allow_private_url_fetch=True,
    )

    assert result.status == "success"
    assert result.output["source"]["uri"] == "http://127.0.0.1/about"


def test_fetch_company_website_allows_private_url_with_env(monkeypatch):
    monkeypatch.setenv("PREPPER_ALLOW_PRIVATE_URL_FETCH", "1")
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        lambda _request, **_kwargs: FakeResponse(
            b"<html><body><p>Local company facts</p></body></html>",
            url="http://127.0.0.1/about",
        ),
    )

    result = run_fetch_company_website_tool(
        mode="llm",
        url="http://127.0.0.1/about",
    )

    assert result.status == "success"


def test_fetch_company_website_rejects_unsafe_redirect_before_following():
    handler = hr_tools._CompanyWebsiteRedirectHandler(allow_private_url_fetch=False)

    with pytest.raises(HrToolError, match="redirect URL resolves to blocked address"):
        handler.redirect_request(
            None,
            None,
            302,
            "Found",
            Message(),
            "http://127.0.0.1/about",
        )


def test_fetch_company_website_rejects_unsafe_final_url(monkeypatch):
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        lambda _request, **_kwargs: FakeResponse(
            b"<html><body><p>Private company facts</p></body></html>",
            url="http://127.0.0.1/about",
        ),
    )

    with pytest.raises(HrToolError, match="final URL resolves to blocked address"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com/about")


def test_fetch_company_website_reports_timeout(monkeypatch):
    def fake_open(_request, *, timeout_seconds, allow_private_url_fetch):
        raise TimeoutError("timed out")

    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)

    with pytest.raises(HrToolError, match="timed out"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com")


def test_fetch_company_website_reports_url_failure(monkeypatch):
    def fake_open(_request, *, timeout_seconds, allow_private_url_fetch):
        raise URLError("blocked")

    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)

    with pytest.raises(HrToolError, match="fetch failed"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com")


def test_fetch_company_website_reports_socket_timeout(monkeypatch):
    def fake_open(_request, *, timeout_seconds, allow_private_url_fetch):
        raise socket.timeout("slow")

    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)

    with pytest.raises(HrToolError, match="timed out"):
        run_fetch_company_website_tool(mode="llm", url="https://example.com")


def test_fetch_company_website_rejects_oversized_content_length(monkeypatch):
    def fake_open(_request, *, timeout_seconds, allow_private_url_fetch):
        return FakeResponse(b"small", content_length=20)

    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)

    with pytest.raises(HrToolError, match="size limit"):
        run_fetch_company_website_tool(
            mode="llm", url="https://example.com", max_bytes=10
        )


def test_fetch_company_website_rejects_oversized_body(monkeypatch):
    def fake_open(_request, *, timeout_seconds, allow_private_url_fetch):
        return FakeResponse(b"01234567890", content_length=None)

    monkeypatch.setattr("prepper_cli.hr_tools._open_company_website_request", fake_open)

    with pytest.raises(HrToolError, match="size limit"):
        run_fetch_company_website_tool(
            mode="llm", url="https://example.com", max_bytes=10
        )


def test_fetch_company_website_mock_and_live_have_same_output_shape(monkeypatch):
    fixture = validate_hr_fixture("demo_hr")
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        lambda _request, **_kwargs: FakeResponse(
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
