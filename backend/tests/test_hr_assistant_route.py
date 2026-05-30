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


def test_hr_context_rejects_oversized_pasted_text():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/context",
        json=_context_payload(resume_text="x" * 40001),
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "input_too_long",
        "field": "resume_text",
        "max_length": 40000,
        "actual_length": 40001,
    }


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
    assert isinstance(data["sources"][0]["relevance_percent"], int)
    assert 0 < data["sources"][0]["relevance_percent"] <= 100
    assert 0 < data["sources"][0]["score"] <= 1
    assert "debug_context" not in data
    assert "profile" not in data["tool_results"][0]["output"]
    assert "query" not in data["tool_results"][-1]["output"]
    assert "snippets" not in data["tool_results"][-1]["output"]


def test_hr_assistant_can_return_explicit_debug_context():
    app = create_app()
    client = app.test_client()
    context_id = _build_context(client)

    response = client.post(
        "/api/hr/assistant",
        json={
            "context_id": context_id,
            "message": "What should I test?",
            "mode": "mock",
            "include_debug_context": True,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["debug_context"]["context_id"] == context_id
    assert data["debug_context"]["candidate_profile"]["skills"]
    assert data["debug_context"]["chunks"]


def test_hr_assistant_rejects_invalid_context_id():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/assistant",
        json={"context_id": "missing", "message": "Help", "mode": "mock"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid context_id"}


def test_hr_assistant_redacts_unexpected_error(monkeypatch):
    def fail_assistant(**kwargs):
        raise RuntimeError("candidate private detail")

    monkeypatch.setattr("app.routes.hr.run_hr_assistant", fail_assistant)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/assistant",
        json={"message": "Help", "mode": "mock"},
    )

    assert response.status_code == 502
    assert response.get_json() == {"error": "HR assistant failed"}
    assert "candidate private detail" not in response.get_data(as_text=True)


def test_hr_assistant_rate_limit_is_enforced():
    app = create_app()
    client = app.test_client()

    responses = [
        client.post(
            "/api/hr/assistant",
            json={"message": f"Help {index}", "mode": "mock"},
            environ_overrides={"REMOTE_ADDR": "192.0.2.44"},
        )
        for index in range(11)
    ]

    assert [response.status_code for response in responses[:10]] == [200] * 10
    assert responses[10].status_code == 429
    assert responses[10].get_json() == {"error": "rate limit exceeded"}


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
            "include_debug_context": True,
        },
    )

    assert start.status_code == 200
    start_data = start.get_json()
    assert start_data["context_id"] == context_id
    assert start_data["interview_enabled"] is True
    assert start_data["debug_context"]["context_id"] == context_id
    assert start_data["debug_context"]["chunks"]
    assert start_data["tool_results"][0]["tool_name"] == "retrieve_company_context"
    assert start_data["sources"]
    assert isinstance(start_data["sources"][0]["relevance_percent"], int)
    assert 0 < start_data["sources"][0]["score"] <= 1

    turn = client.post(
        "/api/hr/interview",
        json={
            "context_id": context_id,
            "interview_id": start_data["interview_id"],
            "message": "I like privacy-first HR analytics.",
            "include_debug_context": True,
        },
    )

    assert turn.status_code == 200
    turn_data = turn.get_json()
    assert turn_data["interview_complete"] is True
    assert turn_data["final_result"]["passed"] is True
    assert turn_data["debug_context"]["context_id"] == context_id
    assert turn_data["tool_results"][0]["tool_name"] == "retrieve_company_context"
    assert "query" not in turn_data["tool_results"][0]["output"]
    assert "snippets" not in turn_data["tool_results"][0]["output"]


def test_hr_interview_mock_end_scores_current_conversation():
    app = create_app()
    client = app.test_client()
    context_id = _build_context(client)

    start = client.post(
        "/api/hr/interview/start",
        json={"context_id": context_id, "mode": "mock", "max_question_roundtrips": 5},
    )
    assert start.status_code == 200
    start_data = start.get_json()

    response = client.post(
        "/api/hr/interview/end",
        json={
            "context_id": context_id,
            "interview_id": start_data["interview_id"],
            "include_debug_context": True,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["interview_complete"] is True
    assert data["current_turn_type"] == "other"
    assert data["final_result"]["passed"] is True
    assert data["final_result"]["pass_threshold"] == data["pass_threshold"]
    assert data["tool_results"][0]["tool_name"] == "retrieve_company_context"
    assert data["debug_context"]["context_id"] == context_id


def test_hr_interview_llm_end_scores_current_conversation(monkeypatch):
    captured = {}

    def fake_retrieval(**kwargs):
        captured["retrieval_query"] = kwargs["query"]
        return {
            "tool_name": "retrieve_company_context",
            "status": "success",
            "output": {"mode": "llm", "query": kwargs["query"], "snippets": []},
        }

    def fake_opener(**kwargs):
        return "Opening question?\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"

    def fake_score(conversation, descriptor, language, pass_threshold, model=None):
        captured["score_messages"] = conversation.get_messages()
        captured["score_descriptor"] = descriptor.content
        captured["score_language"] = language
        return {
            "overall_score": 7.0,
            "pass_threshold": pass_threshold,
            "passed": True,
            "criterion_scores": [],
            "strengths": ["clear examples"],
            "improvements": [],
        }

    monkeypatch.setattr("app.routes.hr._run_hr_interview_retrieval", fake_retrieval)
    monkeypatch.setattr("app.routes.hr.get_interview_opener", fake_opener)
    monkeypatch.setattr("app.routes.hr.score_interview", fake_score)

    app = create_app()
    client = app.test_client()
    context_id = _build_context(client)

    start = client.post(
        "/api/hr/interview/start",
        json={"context_id": context_id, "mode": "llm", "language": "fr"},
    )
    assert start.status_code == 200
    start_data = start.get_json()

    response = client.post(
        "/api/hr/interview/end",
        json={"context_id": context_id, "interview_id": start_data["interview_id"]},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["interview_complete"] is True
    assert data["final_result"]["overall_score"] == 7.0
    assert captured["retrieval_query"] == "final HR candidate fit interview scoring"
    assert captured["score_messages"][0]["role"] == "assistant"
    assert "Resume/profile skills" in captured["score_descriptor"]
    assert captured["score_language"] == "fr"


def test_hr_interview_llm_uses_start_language(monkeypatch):
    captured = {}

    def fake_retrieval(**kwargs):
        return {
            "tool_name": "retrieve_company_context",
            "status": "success",
            "output": {"mode": "llm", "query": kwargs["query"], "snippets": []},
        }

    def fake_opener(**kwargs):
        captured["opener_language"] = kwargs["language"]
        captured["opener_system_prompt"] = kwargs["system_prompt"]
        return "Eröffnungsfrage?\n[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"

    def fake_turn(**kwargs):
        captured["turn_language"] = kwargs["language"]
        captured["turn_descriptor_content"] = kwargs["descriptor"].content
        return {
            "reply": "Nächste Frage?",
            "interview_complete": False,
            "question_count": 1,
            "question_limit": kwargs["question_limit"],
            "pass_threshold": kwargs["pass_threshold"],
            "turn_type": "question",
            "metadata_warning": False,
        }

    monkeypatch.setattr("app.routes.hr._run_hr_interview_retrieval", fake_retrieval)
    monkeypatch.setattr("app.routes.hr.get_interview_opener", fake_opener)
    monkeypatch.setattr("app.routes.hr.run_interview_turn", fake_turn)

    app = create_app()
    client = app.test_client()
    context_id = _build_context(client)

    start = client.post(
        "/api/hr/interview/start",
        json={"context_id": context_id, "mode": "llm", "language": "de"},
    )

    assert start.status_code == 200
    start_data = start.get_json()
    assert captured["opener_language"] == "de"
    assert "Resume/profile skills" in captured["opener_system_prompt"]
    assert "SQL" in captured["opener_system_prompt"]
    assert "specific past-experience questions" in captured["opener_system_prompt"]
    assert "You may reference specific resume/profile details" in captured["opener_system_prompt"]

    turn = client.post(
        "/api/hr/interview",
        json={
            "context_id": context_id,
            "interview_id": start_data["interview_id"],
            "message": "Meine Antwort.",
        },
    )

    assert turn.status_code == 200
    assert captured["turn_language"] == "de"
    assert "Resume/profile experience signals" in captured["turn_descriptor_content"]
    assert "representative examples" in captured["turn_descriptor_content"]
    assert "at least 1-2 questions grounded in resume/profile" in captured["turn_descriptor_content"]


def test_hr_interview_rejects_non_string_language():
    app = create_app()
    client = app.test_client()
    context_id = _build_context(client)

    response = client.post(
        "/api/hr/interview/start",
        json={"context_id": context_id, "mode": "mock", "language": 123},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "language must be a string"}


def test_hr_interview_rejects_invalid_context_id():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/interview/start",
        json={"context_id": "missing", "mode": "mock"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid context_id"}
