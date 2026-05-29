import ipaddress
import logging
from email.message import Message

from app import create_app
from app.routes.hr import get_stored_hr_context


class FakeResponse:
    def __init__(self, body: bytes, *, url: str = "https://example.com/about"):
        self._body = body
        self._url = url
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"

    def read(self, _size: int) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url

    def close(self) -> None:
        pass


def _payload(**overrides):
    payload = {
        "mode": "mock",
        "company_text": "# Example Co\n\n## Values\nPrivacy-first HR analytics.",
        "role_description": "# Analyst\n\n## Responsibilities\nAnalyze customer success data.",
        "resume_text": "# Resume\n\n## Skills\nSQL, Python\n\n## Experience\n### Analyst, HR SaaS",
        "profile_text": "# Profile\nCustomer-facing analytics experience.",
    }
    payload.update(overrides)
    return payload


def test_hr_context_endpoint_builds_and_stores_context_from_text(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_SQLITE_PATH", str(tmp_path / "prepper.sqlite3"))
    app = create_app()
    client = app.test_client()

    response = client.post("/api/hr/context", json=_payload())

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema_version"] == "hr-context-response.v1"
    assert data["status"] == "success"
    assert data["context_id"].startswith("hrctx_input_")
    assert data["context"]["context_id"] == data["context_id"]
    assert data["context"]["fixture_id"] is None
    assert "debug_context" not in data
    assert "company_inputs" not in data["context"]
    assert "role_description" not in data["context"]
    assert "candidate_inputs" not in data["context"]
    assert "candidate_profile" not in data["context"]
    assert "chunks" not in data["context"]
    assert data["summaries"]["company"].startswith("Example Co")
    assert data["tool_results"][0]["tool_name"] == "extract_candidate_profile"
    assert "profile" not in data["tool_results"][0]["output"]
    assert data["tool_call_events"][0]["tool_name"] == "extract_candidate_profile"
    assert data["tool_call_events"][0]["status"] == "success"
    assert data["errors"] == []
    assert get_stored_hr_context(data["context_id"]).context_id == data["context_id"]

    latest_response = client.get("/api/hr/setup/latest")
    assert latest_response.status_code == 200
    latest = latest_response.get_json()
    assert latest["setup"] == {
        "company_url": "",
        "company_text": payload_company_text(),
        "role_description": _payload()["role_description"],
        "role_url": "",
        "resume_text": _payload()["resume_text"],
        "profile_text": _payload()["profile_text"],
    }
    assert latest["context_result"]["context_id"] == data["context_id"]


def payload_company_text():
    return _payload()["company_text"]


def test_latest_hr_setup_rehydrates_saved_context(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_SQLITE_PATH", str(tmp_path / "prepper.sqlite3"))
    app = create_app()
    client = app.test_client()

    response = client.post("/api/hr/context", json=_payload())
    assert response.status_code == 200
    context_id = response.get_json()["context_id"]

    from app.routes import hr as hr_routes

    hr_routes._HR_CONTEXTS.pop(context_id, None)
    hr_routes._HR_CONTEXT_METADATA.pop(context_id, None)
    assert get_stored_hr_context(context_id) is None

    latest_response = client.get("/api/hr/setup/latest")

    assert latest_response.status_code == 200
    latest = latest_response.get_json()
    assert latest["context_result"]["context_id"] == context_id
    assert get_stored_hr_context(context_id).context_id == context_id


def test_latest_hr_setup_returns_empty_when_no_saved_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_SQLITE_PATH", str(tmp_path / "prepper.sqlite3"))
    app = create_app()
    client = app.test_client()

    response = client.get("/api/hr/setup/latest")

    assert response.status_code == 200
    assert response.get_json() == {"setup": None, "context_result": None}


def test_demo_hr_setup_returns_fixture_fields():
    app = create_app()
    client = app.test_client()

    response = client.get("/api/hr/setup/demo")

    assert response.status_code == 200
    setup = response.get_json()["setup"]
    assert setup["company_url"] == ""
    assert setup["company_text"].startswith("# Northstar Analytics")
    assert setup["role_description"].startswith("# Role: Customer Success Data Analyst")
    assert setup["role_url"] == ""
    assert setup["resume_text"].startswith("# Candidate Resume: Jordan Lee")
    assert setup["profile_text"].startswith("# Candidate Profile Summary")


def test_hr_context_endpoint_fetches_company_url(monkeypatch):
    def fake_open(request, *, timeout_seconds, allow_private_url_fetch):
        assert request.full_url == "https://example.com/about"
        assert allow_private_url_fetch is False
        return FakeResponse(
            b"<html><head><title>Example</title></head><body><p>HR analytics platform.</p></body></html>"
        )

    monkeypatch.setattr(
        "prepper_cli.hr_tools._resolve_company_website_host_ips",
        lambda _hostname: (ipaddress.ip_address("93.184.216.34"),),
    )
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        fake_open,
    )
    app = create_app()
    client = app.test_client()

    payload = _payload(company_text=None, company_url="https://example.com/about")
    response = client.post("/api/hr/context", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["sources"][0]["uri"] == "https://example.com/about"
    assert [tool["tool_name"] for tool in data["tool_results"]] == [
        "fetch_company_website",
        "extract_candidate_profile",
    ]
    assert "document" not in data["tool_results"][0]["output"]
    assert "chunks" not in data["tool_results"][0]["output"]
    assert data["tool_results"][0]["output"]["summary"] == "HR analytics platform."


def test_hr_context_endpoint_fetches_role_url(monkeypatch):
    from prepper_cli.hr_context import HrToolResult

    def fake_role_tool(**kwargs):
        assert kwargs["mode"] == "llm"
        assert kwargs["url"] == "https://example.com/jobs/analyst"
        return HrToolResult(
            tool_name="fetch_role_description",
            status="success",
            output={
                "mode": "llm",
                "role_description": "# Analyst\n\nAnalyze customer success data.",
                "source": {
                    "id": "role_job_ad",
                    "kind": "role",
                    "title": "Analyst",
                    "uri": "https://example.com/jobs/analyst",
                    "content_sha256": "x",
                },
                "document": {
                    "source_id": "role_job_ad",
                    "title": "Analyst",
                    "markdown": "# Analyst\n\nAnalyze customer success data.",
                    "summary": "Analyze customer success data.",
                },
                "chunks": [],
                "fetch_metadata": {
                    "url": "https://example.com/jobs/analyst",
                    "content_type": "text/html",
                    "byte_count": 10,
                    "truncated": False,
                    "fetched_char_count": 10,
                    "role_char_count": 41,
                    "max_chars": 40000,
                },
            },
        )

    def fake_candidate_tool(**kwargs):
        return HrToolResult(
            tool_name="extract_candidate_profile",
            status="success",
            output={
                "mode": kwargs["mode"],
                "profile": {
                    "skills": ["SQL"],
                    "experience": ["Analyst"],
                    "seniority_signals": [],
                    "risks": [],
                    "interview_focus_areas": ["Validate analytics depth"],
                },
                "input_metadata": {},
                "sources": [],
            },
        )

    monkeypatch.setattr(
        "prepper_cli.hr_tools._resolve_company_website_host_ips",
        lambda _hostname: (ipaddress.ip_address("93.184.216.34"),),
    )
    monkeypatch.setattr("prepper_cli.hr_langchain_tools.run_fetch_role_description_tool", fake_role_tool)
    monkeypatch.setattr("prepper_cli.hr_langchain_tools.run_extract_candidate_profile_tool", fake_candidate_tool)
    app = create_app()
    client = app.test_client()

    payload = _payload(role_description="", role_url="https://example.com/jobs/analyst", mode="llm")
    response = client.post("/api/hr/context", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["sources"][1]["uri"] == "https://example.com/jobs/analyst"
    assert [tool["tool_name"] for tool in data["tool_results"]] == [
        "fetch_role_description",
        "extract_candidate_profile",
    ]



def test_hr_context_endpoint_can_return_explicit_debug_context():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/context",
        json=_payload(include_debug_context=True),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["context"]["context_id"] == data["context_id"]
    assert "company_inputs" not in data["context"]
    assert data["debug_context"]["context_id"] == data["context_id"]
    assert data["debug_context"]["company_inputs"][0]["markdown"].startswith(
        "# Example Co"
    )
    assert data["debug_context"]["role_description"]["markdown"].startswith(
        "# Analyst"
    )
    assert data["debug_context"]["candidate_profile"]["skills"]
    assert data["debug_context"]["chunks"]


def test_hr_context_endpoint_rejects_validation_errors():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/context",
        json=_payload(company_url="https://example.com"),
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Exactly one of company_text or company_url is required"
    }


def test_hr_context_endpoint_rejects_private_company_url(monkeypatch):
    monkeypatch.delenv("PREPPER_ALLOW_PRIVATE_URL_FETCH", raising=False)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/context",
        json=_payload(company_text=None, company_url="http://127.0.0.1/about"),
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Company website URL resolves to blocked address: 127.0.0.1"
    }


def test_hr_context_endpoint_allows_private_company_url_with_env(monkeypatch):
    monkeypatch.setenv("PREPPER_ALLOW_PRIVATE_URL_FETCH", "1")
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        lambda _request, **_kwargs: FakeResponse(
            b"<html><head><title>Local</title></head><body><p>Local HR platform.</p></body></html>",
            url="http://127.0.0.1/about",
        ),
    )
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/context",
        json=_payload(company_text=None, company_url="http://127.0.0.1/about"),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["sources"][0]["uri"] == "http://127.0.0.1/about"


def test_hr_context_endpoint_returns_partial_when_candidate_tool_fails(monkeypatch):
    def fail_candidate_profile(**kwargs):
        raise RuntimeError("profile model unavailable: candidate@example.com")

    monkeypatch.setattr(
        "prepper_cli.hr_tools.run_extract_candidate_profile_tool",
        fail_candidate_profile,
    )
    app = create_app()
    client = app.test_client()

    response = client.post("/api/hr/context", json=_payload())

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "partial"
    assert data["context_id"].startswith("hrctx_input_")
    assert data["tool_results"][0]["status"] == "error"
    safe_message = "extract_candidate_profile failed; review server logs or rerun the workflow locally."
    assert data["tool_results"][0]["output"]["error"] == safe_message
    assert data["context"]["tool_results"][0]["output"]["error"] == safe_message
    assert "candidate_profile" not in data["context"]
    assert data["errors"] == [
        {
            "tool_name": "extract_candidate_profile",
            "message": safe_message,
        }
    ]
    assert "candidate@example.com" not in response.get_data(as_text=True)


def test_hr_context_endpoint_returns_partial_without_context_when_url_fetch_fails(monkeypatch):
    def fail_open(request, *, timeout_seconds, allow_private_url_fetch):
        raise TimeoutError("slow private site details")

    monkeypatch.setattr(
        "prepper_cli.hr_tools._resolve_company_website_host_ips",
        lambda _hostname: (ipaddress.ip_address("93.184.216.34"),),
    )
    monkeypatch.setattr(
        "prepper_cli.hr_tools._open_company_website_request",
        fail_open,
    )
    app = create_app()
    client = app.test_client()

    payload = _payload(company_text=None, company_url="https://example.com/about")
    response = client.post("/api/hr/context", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "partial"
    assert data["context_id"] is None
    assert data["context"] is None
    assert data["errors"][0] == {
        "tool_name": "fetch_company_website",
        "message": "fetch_company_website failed; review server logs or rerun the workflow locally.",
    }
    assert "slow private site details" not in response.get_data(as_text=True)


def test_hr_context_endpoint_redacts_unexpected_exception(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)

    def fail_build(**kwargs):
        raise RuntimeError("resume secret: candidate@example.com")

    monkeypatch.setattr("app.routes.hr.build_hr_context_from_inputs", fail_build)
    app = create_app()
    client = app.test_client()

    response = client.post("/api/hr/context", json=_payload())

    assert response.status_code == 502
    assert response.get_json() == {"error": "HR context build failed"}
    assert "candidate@example.com" not in response.get_data(as_text=True)
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        'event="route_failure"' in message
        and 'operation="hr_context_build"' in message
        and 'status="error"' in message
        for message in messages
    )
    assert "candidate@example.com" not in "\n".join(messages)


def test_hr_context_options_preflight_returns_cors_headers():
    app = create_app()
    client = app.test_client()

    response = client.options(
        "/api/hr/context",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]
