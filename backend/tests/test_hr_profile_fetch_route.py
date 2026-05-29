from app import create_app
from prepper_cli.hr_context import HrToolResult


def test_hr_company_fetch_endpoint_returns_text(monkeypatch):
    def fake_fetch(*, mode, url):
        assert mode == "llm"
        assert url == "https://example.com/about"
        return HrToolResult(
            tool_name="fetch_company_website",
            status="success",
            output={
                "mode": "llm",
                "source": {"id": "company_website", "uri": url},
                "document": {
                    "markdown": "# Example Co\nAnalytics platform.",
                    "summary": "Analytics platform.",
                },
                "chunks": [{"text": "raw chunk should not leak"}],
            },
        )

    monkeypatch.setattr("app.routes.hr.run_fetch_company_website_tool", fake_fetch)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/company/fetch",
        json={"company_url": "https://example.com/about"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["company_text"].startswith("# Example Co")
    assert data["source"]["uri"] == "https://example.com/about"
    assert "chunks" not in data


def test_hr_role_fetch_endpoint_returns_description(monkeypatch):
    def fake_fetch(*, mode, url, model=None):
        assert mode == "llm"
        assert url == "https://example.com/jobs/analyst"
        assert model is None
        return HrToolResult(
            tool_name="fetch_role_description",
            status="success",
            output={
                "mode": "llm",
                "role_description": "# Data Analyst\nBuild dashboards.",
                "source": {"id": "role_description", "uri": url},
                "document": {"markdown": "raw document should not leak"},
            },
        )

    monkeypatch.setattr("app.routes.hr.run_fetch_role_description_tool", fake_fetch)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/role/fetch",
        json={"role_url": "https://example.com/jobs/analyst"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["role_description"].startswith("# Data Analyst")
    assert data["source"]["uri"] == "https://example.com/jobs/analyst"
    assert "document" not in data


def test_hr_company_fetch_endpoint_rejects_missing_url():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/hr/company/fetch", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "company_url is required"


def test_hr_profile_fetch_endpoint_returns_summary(monkeypatch):
    def fake_fetch(*, profile_url, oauth_token, model=None):
        assert profile_url == "https://www.linkedin.com/in/jane-doe"
        assert oauth_token == "secret-token"
        assert model is None
        return HrToolResult(
            tool_name="fetch_social_profile",
            status="success",
            output={
                "mode": "llm",
                "profile_text": "## Profile\n- Senior analytics leader",
                "source": {
                    "provider": "linkedin",
                    "uri": profile_url,
                    "profile_identifier": "jane-doe",
                },
                "api_payload": {"secret": "raw provider data"},
            },
        )

    monkeypatch.setattr("app.routes.hr.run_fetch_social_profile_tool", fake_fetch)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/profile/fetch",
        json={
            "profile_url": "https://www.linkedin.com/in/jane-doe",
            "oauth_token": "secret-token",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["profile_text"].startswith("## Profile")
    assert data["source"]["provider"] == "linkedin"
    assert "secret-token" not in str(data)
    assert "api_payload" not in data


def test_hr_profile_fetch_endpoint_rejects_missing_token():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/profile/fetch",
        json={"profile_url": "https://www.linkedin.com/in/jane-doe"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "oauth_token is required"


def test_hr_profile_fetch_endpoint_returns_safe_tool_error(monkeypatch):
    def fake_fetch(**_kwargs):
        raise ValueError("Social profile API access was denied")

    monkeypatch.setattr("app.routes.hr.run_fetch_social_profile_tool", fake_fetch)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/profile/fetch",
        json={
            "profile_url": "https://www.xing.com/profile/Jane_Doe",
            "oauth_token": "secret-token",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Social profile API access was denied"
