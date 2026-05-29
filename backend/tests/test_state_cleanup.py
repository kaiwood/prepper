from app import create_app
from app.helpers.state_cleanup import cleanup_state_store, mark_state_created
from app.routes import chat as chat_routes
from app.routes import hr as hr_routes
from prepper_cli.system_prompts import PromptDescriptor


def _descriptor(id: str = "coding_focus") -> PromptDescriptor:
    return PromptDescriptor(
        id=id,
        name=id,
        content=f"prompt::{id}",
        temperature=0.5,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=500,
        interview_rating_enabled=True,
        default_question_roundtrips=1,
        pass_threshold=7.0,
        rubric_criteria=("Problem solving",),
    )


def _hr_context_payload(**overrides):
    payload = {
        "mode": "mock",
        "company_text": "# Example Co\n\nPrivacy-first HR analytics.",
        "role_description": "# Analyst\n\nAnalyze customer success data.",
        "resume_text": "# Resume\n\nSQL and Python analyst experience.",
        "profile_text": "# Profile\n\nCustomer-facing analytics experience.",
    }
    payload.update(overrides)
    return payload


def _clear_state_stores() -> None:
    chat_routes._INTERVIEW_SESSIONS.clear()
    hr_routes._HR_CONTEXTS.clear()
    hr_routes._HR_CONTEXT_METADATA.clear()
    hr_routes._HR_INTERVIEW_SESSIONS.clear()


def test_cleanup_state_store_evicts_oldest_over_max_entries():
    store = {}
    for index, key in enumerate(("old", "middle", "new"), start=1):
        store[key] = {}
        mark_state_created(store[key], now=float(index))

    removed = cleanup_state_store(store, now=10.0, ttl_seconds=100, max_entries=2)

    assert removed == {"old"}
    assert list(store) == ["middle", "new"]


def test_expired_chat_interview_session_uses_existing_invalid_id_error(monkeypatch):
    _clear_state_stores()
    monkeypatch.setenv("PREPPER_STATE_TTL_SECONDS", "60")
    descriptor = _descriptor()
    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: descriptor,
    )
    expired_session = {"descriptor": descriptor}
    mark_state_created(expired_session, now=900.0)
    chat_routes._INTERVIEW_SESSIONS["expired"] = expired_session
    monkeypatch.setattr("app.helpers.state_cleanup.time.time", lambda: 1000.0)

    app = create_app()
    client = app.test_client()
    response = client.post(
        "/api/chat",
        json={"message": "hello", "interview_id": "expired"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid interview_id"}
    assert "expired" not in chat_routes._INTERVIEW_SESSIONS


def test_expired_hr_context_uses_existing_invalid_context_error(monkeypatch):
    _clear_state_stores()
    monkeypatch.setenv("PREPPER_STATE_TTL_SECONDS", "60")
    current_time = {"value": 1000.0}
    monkeypatch.setattr(
        "app.helpers.state_cleanup.time.time",
        lambda: current_time["value"],
    )
    app = create_app()
    client = app.test_client()

    context_response = client.post("/api/hr/context", json=_hr_context_payload())
    assert context_response.status_code == 200
    context_id = context_response.get_json()["context_id"]

    current_time["value"] = 1061.0
    response = client.post(
        "/api/hr/assistant",
        json={"context_id": context_id, "message": "Help", "mode": "mock"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid context_id"}
    assert context_id not in hr_routes._HR_CONTEXTS


def test_expired_hr_interview_session_uses_existing_invalid_id_error(monkeypatch):
    _clear_state_stores()
    monkeypatch.setenv("PREPPER_STATE_TTL_SECONDS", "60")
    current_time = {"value": 1000.0}
    monkeypatch.setattr(
        "app.helpers.state_cleanup.time.time",
        lambda: current_time["value"],
    )
    app = create_app()
    client = app.test_client()

    context_response = client.post("/api/hr/context", json=_hr_context_payload())
    context_id = context_response.get_json()["context_id"]
    start_response = client.post(
        "/api/hr/interview/start",
        json={"context_id": context_id, "mode": "mock"},
    )
    assert start_response.status_code == 200
    interview_id = start_response.get_json()["interview_id"]

    mark_state_created(hr_routes._HR_INTERVIEW_SESSIONS[interview_id], now=900.0)
    mark_state_created(hr_routes._HR_CONTEXT_METADATA[context_id], now=1060.0)
    current_time["value"] = 1061.0
    response = client.post(
        "/api/hr/interview",
        json={
            "context_id": context_id,
            "interview_id": interview_id,
            "message": "I like the role.",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid interview_id"}
    assert interview_id not in hr_routes._HR_INTERVIEW_SESSIONS


def test_hr_context_access_refreshes_inactivity_ttl(monkeypatch):
    _clear_state_stores()
    monkeypatch.setenv("PREPPER_STATE_TTL_SECONDS", "60")
    current_time = {"value": 1000.0}
    monkeypatch.setattr(
        "app.helpers.state_cleanup.time.time",
        lambda: current_time["value"],
    )
    app = create_app()
    client = app.test_client()

    context_response = client.post("/api/hr/context", json=_hr_context_payload())
    context_id = context_response.get_json()["context_id"]

    current_time["value"] = 1030.0
    first_access = client.post(
        "/api/hr/assistant",
        json={"context_id": context_id, "message": "Help", "mode": "mock"},
    )
    assert first_access.status_code == 200

    current_time["value"] = 1061.0
    second_access = client.post(
        "/api/hr/assistant",
        json={"context_id": context_id, "message": "Help again", "mode": "mock"},
    )

    assert second_access.status_code == 200
    assert context_id in hr_routes._HR_CONTEXTS
