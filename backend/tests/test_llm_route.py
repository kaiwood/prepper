from app import create_app
from prepper_cli.system_prompts import PromptDescriptor


def _make_descriptor(id: str, name: str | None = None, **overrides) -> PromptDescriptor:
    defaults = dict(
        temperature=0.5,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=500,
        content=f"prompt::{id}",
    )
    defaults.update(overrides)
    return PromptDescriptor(id=id, name=name or id, **defaults)


def test_chat_uses_default_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    default_descriptor = _make_descriptor(
        "coding_focus", name="Coding Interview")
    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor",
        lambda selected_name=None: default_descriptor,
    )

    captured = {}

    def fake_get_chat_reply(
        message,
        conversation=None,
        history_limit=10,
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
    ):
        captured["message"] = message
        captured["system_prompt"] = system_prompt
        captured["language"] = language
        captured["temperature"] = temperature
        return "ok"

    monkeypatch.setattr("app.routes.llm.get_chat_reply", fake_get_chat_reply)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.get_json() == {"reply": "ok"}
    assert captured["message"] == "hello"
    assert captured["system_prompt"] == "prompt::coding_focus"
    assert captured["language"] is None
    assert captured["temperature"] == 0.5


def test_chat_accepts_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    captured = {}

    def fake_resolver(selected_name=None):
        captured["selected_name"] = selected_name
        return _make_descriptor(selected_name or "default", content=f"prompt::{selected_name}")

    def fake_get_chat_reply(
        message,
        conversation=None,
        history_limit=10,
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
    ):
        captured["message"] = message
        captured["system_prompt"] = system_prompt
        captured["language"] = language
        return "ok"

    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor", fake_resolver)
    monkeypatch.setattr("app.routes.llm.get_chat_reply", fake_get_chat_reply)

    response = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "system_prompt_name": "coding_focus",
            "language": "de",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"reply": "ok"}
    assert captured["selected_name"] == "coding_focus"
    assert captured["message"] == "hello"
    assert captured["system_prompt"] == "prompt::coding_focus"
    assert captured["language"] == "de"


def test_chat_rejects_invalid_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor", bad_resolver)

    response = client.post(
        "/api/chat",
        json={"message": "hello", "system_prompt_name": "missing"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unknown system prompt 'missing'"}


def test_chat_returns_502_when_default_prompt_resolution_fails(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor", bad_resolver)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "LLM request failed: Unknown system prompt 'missing'"
    }


def test_prompts_returns_prompt_objects_with_metadata(monkeypatch):
    app = create_app()
    client = app.test_client()

    descriptors = [
        _make_descriptor("behavioral_focus", name="Behavioral Interview", temperature=0.5,
                         top_p=0.95, frequency_penalty=0.2, presence_penalty=0.1, max_tokens=700),
        _make_descriptor("coding_focus", name="Coding Interview", temperature=0.3,
                         top_p=1.0, frequency_penalty=0.2, presence_penalty=0.0, max_tokens=700),
        _make_descriptor("interview_coach", name="Interview Coach", temperature=0.4,
                         top_p=0.95, frequency_penalty=0.2, presence_penalty=0.1, max_tokens=800),
    ]
    monkeypatch.setattr(
        "app.routes.llm.list_prompt_descriptors",
        lambda: descriptors,
    )
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
    data = response.get_json()
    assert data["default"] == "coding_focus"
    assert len(data["prompts"]) == 3

    coding = next(p for p in data["prompts"] if p["id"] == "coding_focus")
    assert coding["name"] == "Coding Interview"
    assert coding["temperature"] == 0.3
    assert coding["top_p"] == 1.0
    assert coding["frequency_penalty"] == 0.2
    assert coding["presence_penalty"] == 0.0
    assert coding["max_tokens"] == 700


def test_chat_start_uses_default_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    default_descriptor = _make_descriptor(
        "coding_focus", name="Coding Interview")
    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor",
        lambda selected_name=None: default_descriptor,
    )

    captured = {}

    def fake_get_interview_opener(
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
    ):
        captured["system_prompt"] = system_prompt
        captured["language"] = language
        captured["temperature"] = temperature
        return "opening question"

    monkeypatch.setattr("app.routes.llm.get_interview_opener",
                        fake_get_interview_opener)

    response = client.post("/api/chat/start", json={})

    assert response.status_code == 200
    assert response.get_json() == {"reply": "opening question"}
    assert captured["system_prompt"] == "prompt::coding_focus"
    assert captured["language"] is None
    assert captured["temperature"] == 0.5


def test_chat_start_accepts_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    captured = {}

    def fake_resolver(selected_name=None):
        captured["selected_name"] = selected_name
        return _make_descriptor(selected_name or "default", content=f"prompt::{selected_name}")

    def fake_get_interview_opener(
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
    ):
        captured["system_prompt"] = system_prompt
        captured["language"] = language
        return "opening question"

    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor", fake_resolver)
    monkeypatch.setattr("app.routes.llm.get_interview_opener",
                        fake_get_interview_opener)

    response = client.post(
        "/api/chat/start",
        json={"system_prompt_name": "coding_focus", "language": "de"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"reply": "opening question"}
    assert captured["selected_name"] == "coding_focus"
    assert captured["system_prompt"] == "prompt::coding_focus"
    assert captured["language"] == "de"


def test_chat_start_rejects_invalid_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor", bad_resolver)

    response = client.post(
        "/api/chat/start",
        json={"system_prompt_name": "missing"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unknown system prompt 'missing'"}


def test_chat_start_returns_502_when_llm_request_fails(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.llm._resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor("coding_focus"),
    )

    def fake_get_interview_opener(
        system_prompt=None,
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
    ):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.routes.llm.get_interview_opener",
                        fake_get_interview_opener)

    response = client.post("/api/chat/start", json={})

    assert response.status_code == 502
    assert response.get_json() == {"error": "LLM request failed: boom"}


def test_chat_rejects_non_string_language():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/chat", json={"message": "hello", "language": 123})

    assert response.status_code == 400
    assert response.get_json() == {"error": "language must be a string"}


def test_chat_start_rejects_non_string_language():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/chat/start", json={"language": 123})

    assert response.status_code == 400
    assert response.get_json() == {"error": "language must be a string"}
