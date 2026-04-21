from app import create_app


def test_chat_uses_default_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr("app.routes.llm._resolve_system_prompt_text", lambda: "default")

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


def test_chat_rejects_system_prompt_fields():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={"message": "hello", "system_prompt_name": "coding_focus"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "system prompt is only supported in the CLI"
    }


def test_chat_returns_502_when_default_prompt_resolution_fails(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_prompt_resolver():
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr("app.routes.llm._resolve_system_prompt_text", bad_prompt_resolver)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "LLM request failed: Unknown system prompt 'missing'"
    }
