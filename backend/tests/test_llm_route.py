from app import create_app


def test_chat_uses_default_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.llm._resolve_system_prompt_text",
        lambda selected_name=None: "default",
    )

    captured = {}

    def fake_get_chat_reply(message, conversation=None, history_limit=10, system_prompt=None):
        captured["message"] = message
        captured["system_prompt"] = system_prompt
        return "ok"

    monkeypatch.setattr("app.routes.llm.get_chat_reply", fake_get_chat_reply)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.get_json() == {"reply": "ok"}
    assert captured == {"message": "hello", "system_prompt": "default"}


def test_chat_accepts_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    captured = {}

    def fake_resolver(selected_name=None):
        captured["selected_name"] = selected_name
        return "selected"

    def fake_get_chat_reply(message, conversation=None, history_limit=10, system_prompt=None):
        captured["message"] = message
        captured["system_prompt"] = system_prompt
        return "ok"

    monkeypatch.setattr("app.routes.llm._resolve_system_prompt_text", fake_resolver)
    monkeypatch.setattr("app.routes.llm.get_chat_reply", fake_get_chat_reply)

    response = client.post(
        "/api/chat",
        json={"message": "hello", "system_prompt_name": "coding_focus"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"reply": "ok"}
    assert captured == {
        "selected_name": "coding_focus",
        "message": "hello",
        "system_prompt": "selected",
    }


def test_chat_rejects_invalid_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_prompt_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr("app.routes.llm._resolve_system_prompt_text", bad_prompt_resolver)

    response = client.post(
        "/api/chat",
        json={"message": "hello", "system_prompt_name": "missing"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unknown system prompt 'missing'"}


def test_chat_returns_502_when_default_prompt_resolution_fails(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_prompt_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr("app.routes.llm._resolve_system_prompt_text", bad_prompt_resolver)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "LLM request failed: Unknown system prompt 'missing'"
    }


def test_prompts_returns_available_and_default(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.llm.list_system_prompt_names",
        lambda: ["behavioral_focus", "coding_focus", "interview_coach"],
    )
    monkeypatch.setattr(
        "app.routes.llm.get_default_system_prompt_name",
        lambda: "coding_focus",
    )

    response = client.get("/api/prompts")

    assert response.status_code == 200
    assert response.get_json() == {
        "available": ["behavioral_focus", "coding_focus", "interview_coach"],
        "default": "coding_focus",
    }
