from app import create_app


def _context_payload(**overrides):
    payload = {
        "mode": "mock",
        "company_text": "# Example Co\n\n## Values\nPrivacy-first HR analytics.",
        "role_description": "# Analyst\n\n## Responsibilities\nAnalyze customer success data.",
        "resume_text": "# Resume\n\n## Skills\nSQL, Python\n\n## Experience\n### Analyst, HR SaaS",
        "profile_text": "# Profile\nCustomer-facing analytics experience.",
    }
    payload.update(overrides)
    return payload


def _build_context(client):
    response = client.post("/api/hr/context", json=_context_payload())
    assert response.status_code == 200
    return response.get_json()["context_id"]


def test_hr_assistant_guides_setup_without_context_id():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/hr/assistant", json={"message": "How do I start?"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema_version"] == "hr-assistant-response.v1"
    assert data["status"] == "needs_setup"
    assert data["context_id"] is None
    assert data["missing_fields"] == [
        "company_url_or_text",
        "role_description",
        "resume_text",
    ]
    assert data["tool_results"] == []


def test_hr_assistant_answers_with_context_and_exposes_tools():
    app = create_app()
    client = app.test_client()
    context_id = _build_context(client)

    response = client.post(
        "/api/hr/assistant",
        json={
            "context_id": context_id,
            "message": "What privacy HR analytics facts should the interview test?",
            "mode": "mock",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["context_id"] == context_id
    assert [tool["tool_name"] for tool in data["tool_results"]] == [
        "extract_candidate_profile",
        "retrieve_company_context",
    ]
    assert data["sources"]


def test_hr_assistant_rejects_invalid_context_id():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/assistant",
        json={"context_id": "missing", "message": "Help", "mode": "mock"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid context_id"}


def test_hr_interview_mock_start_and_turn_include_retrieval():
    app = create_app()
    client = app.test_client()
    context_id = _build_context(client)

    start = client.post(
        "/api/hr/interview/start",
        json={
            "context_id": context_id,
            "mode": "mock",
            "max_question_roundtrips": 1,
        },
    )

    assert start.status_code == 200
    start_data = start.get_json()
    assert start_data["context_id"] == context_id
    assert start_data["interview_enabled"] is True
    assert start_data["tool_results"][0]["tool_name"] == "retrieve_company_context"
    assert start_data["sources"]

    turn = client.post(
        "/api/hr/interview",
        json={
            "context_id": context_id,
            "interview_id": start_data["interview_id"],
            "message": "I like privacy-first HR analytics.",
        },
    )

    assert turn.status_code == 200
    turn_data = turn.get_json()
    assert turn_data["interview_complete"] is True
    assert turn_data["final_result"]["passed"] is True
    assert turn_data["tool_results"][0]["tool_name"] == "retrieve_company_context"


def test_hr_interview_rejects_invalid_context_id():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/interview/start",
        json={"context_id": "missing", "mode": "mock"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid context_id"}
