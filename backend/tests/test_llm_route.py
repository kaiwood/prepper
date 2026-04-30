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
        "app.routes.chat.resolve_prompt_descriptor",
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
        **kwargs,
    ):
        captured["message"] = message
        captured["system_prompt"] = system_prompt
        captured["language"] = language
        captured["temperature"] = temperature
        captured["treat_input_as_untrusted"] = kwargs.get(
            "treat_input_as_untrusted")
        return "ok"

    monkeypatch.setattr("app.routes.chat.get_chat_reply", fake_get_chat_reply)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.get_json() == {"reply": "ok"}
    assert captured["message"] == "hello"
    assert captured["system_prompt"] == "prompt::coding_focus"
    assert captured["language"] is None
    assert captured["temperature"] == 0.5
    assert captured["treat_input_as_untrusted"] is True


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
        **kwargs,
    ):
        captured["message"] = message
        captured["system_prompt"] = system_prompt
        captured["language"] = language
        return "ok"

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor", fake_resolver)
    monkeypatch.setattr("app.routes.chat.get_chat_reply", fake_get_chat_reply)

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


def test_chat_allows_model_setting_overrides(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor("coding_focus"),
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
        **kwargs,
    ):
        captured["temperature"] = temperature
        captured["top_p"] = top_p
        captured["frequency_penalty"] = frequency_penalty
        captured["presence_penalty"] = presence_penalty
        captured["max_tokens"] = max_tokens
        return "ok"

    monkeypatch.setattr("app.routes.chat.get_chat_reply", fake_get_chat_reply)

    response = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "temperature": 1.2,
            "top_p": 0.6,
            "frequency_penalty": -0.4,
            "presence_penalty": 0.8,
            "max_tokens": 900,
        },
    )

    assert response.status_code == 200
    assert captured["temperature"] == 1.2
    assert captured["top_p"] == 0.6
    assert captured["frequency_penalty"] == -0.4
    assert captured["presence_penalty"] == 0.8
    assert captured["max_tokens"] == 900


def test_chat_rejects_invalid_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor", bad_resolver)

    response = client.post(
        "/api/chat",
        json={"message": "hello", "system_prompt_name": "missing"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unknown system prompt 'missing'"}


def test_chat_rejects_invalid_model_setting(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor("coding_focus"),
    )

    response = client.post(
        "/api/chat",
        json={"message": "hello", "temperature": 2.5},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "temperature must be between 0.0 and 2.0"}


def test_chat_returns_502_when_default_prompt_resolution_fails(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor", bad_resolver)

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
                         top_p=0.95, frequency_penalty=0.2, presence_penalty=0.1, max_tokens=1200),
        _make_descriptor("coding_focus", name="Coding Interview", temperature=0.3,
                         top_p=1.0, frequency_penalty=0.2, presence_penalty=0.0, max_tokens=1200,
                         difficulty_enabled=True, difficulty_levels=("easy", "medium", "hard"),
                         default_difficulty="medium"),
    ]
    monkeypatch.setattr(
        "app.routes.prompts.list_prompt_descriptors",
        lambda: descriptors,
    )
    monkeypatch.setattr(
        "app.routes.prompts.list_system_prompt_names",
        lambda: ["behavioral_focus", "coding_focus"],
    )
    monkeypatch.setattr(
        "app.routes.prompts.get_default_system_prompt_name",
        lambda: "coding_focus",
    )

    response = client.get("/api/prompts")

    assert response.status_code == 200
    data = response.get_json()
    assert data["default"] == "coding_focus"
    assert len(data["prompts"]) == 2

    coding = next(p for p in data["prompts"] if p["id"] == "coding_focus")
    assert coding["name"] == "Coding Interview"
    assert coding["temperature"] == 0.3
    assert coding["top_p"] == 1.0
    assert coding["frequency_penalty"] == 0.2
    assert coding["presence_penalty"] == 0.0
    assert coding["max_tokens"] == 1200
    assert coding["interview_rating_enabled"] is False
    assert coding["default_question_roundtrips"] == 5
    assert coding["min_question_roundtrips"] == 1
    assert coding["max_question_roundtrips"] == 10
    assert coding["pass_threshold"] == 7.0
    assert coding["rubric_criteria"] == []
    assert coding["difficulty_enabled"] is True
    assert coding["difficulty_levels"] == ["easy", "medium", "hard"]
    assert coding["default_difficulty"] == "medium"


def test_health_returns_ok():
    app = create_app()
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_prompts_returns_502_when_default_prompt_is_missing(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.prompts.list_system_prompt_names",
        lambda: ["coding_focus"],
    )
    monkeypatch.setattr(
        "app.routes.prompts.get_default_system_prompt_name",
        lambda: "missing",
    )

    response = client.get("/api/prompts")

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "LLM request failed: Unknown system prompt 'missing'"
    }


def test_chat_options_preflight_returns_cors_headers():
    app = create_app()
    client = app.test_client()

    response = client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]


def test_chat_start_options_preflight_returns_cors_headers():
    app = create_app()
    client = app.test_client()

    response = client.options(
        "/api/chat/start",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]


def test_chat_rejects_legacy_system_prompt_field():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={"message": "hello", "system_prompt": "legacy"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "system_prompt is not supported"}


def test_chat_start_rejects_legacy_system_prompt_field():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/chat/start", json={"system_prompt": "legacy"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "system_prompt is not supported"}


def test_chat_rejects_invalid_conversation_history_role():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "conversation_history": [{"role": "system", "content": "nope"}],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "conversation_history contains an invalid role"
    }


def test_chat_rejects_non_string_difficulty(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus", difficulty_enabled=True),
    )

    response = client.post(
        "/api/chat", json={"message": "hello", "difficulty": 123})

    assert response.status_code == 400
    assert response.get_json() == {"error": "difficulty must be a string"}


def test_chat_rejects_invalid_difficulty_value(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus", difficulty_enabled=True),
    )

    response = client.post(
        "/api/chat",
        json={"message": "hello", "difficulty": "expert"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "difficulty must be one of: easy, medium, hard"
    }


def test_chat_rejects_difficulty_for_unsupported_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "behavioral_focus", difficulty_enabled=False),
    )

    response = client.post(
        "/api/chat",
        json={"message": "hello", "difficulty": "easy"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "difficulty is not supported for this interview type"
    }


def test_chat_applies_difficulty_instruction_and_threshold(monkeypatch):
    app = create_app()
    client = app.test_client()

    descriptor = _make_descriptor(
        "coding_focus",
        interview_rating_enabled=True,
        default_question_roundtrips=1,
        pass_threshold=7.0,
        rubric_criteria=("Problem understanding",),
        difficulty_enabled=True,
        difficulty_levels=("easy", "medium", "hard"),
        default_difficulty="medium",
        easy_pass_threshold=6.5,
    )
    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: descriptor,
    )

    captured = {}

    def fake_run_interview_turn(
        message,
        conversation,
        descriptor,
        language,
        question_limit,
        pass_threshold,
        model_settings,
        difficulty=None,
        **kwargs,
    ):
        captured["pass_threshold"] = pass_threshold
        captured["difficulty"] = difficulty
        captured["treat_candidate_input_as_untrusted"] = kwargs.get(
            "treat_candidate_input_as_untrusted"
        )
        return {
            "reply": "Thanks, that concludes the interview.",
            "turn_type": "other",
            "question_count": 1,
            "question_limit": question_limit,
            "interview_complete": True,
            "pass_threshold": pass_threshold,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 6.8,
                "pass_threshold": pass_threshold,
                "passed": 6.8 >= pass_threshold,
                "criterion_scores": [
                    {"criterion": "Problem understanding", "score": 6.8},
                ],
                "strengths": ["Clear structure"],
                "improvements": ["Deeper edge cases"],
                "parse_warning": False,
            },
        }

    monkeypatch.setattr("app.routes.chat.run_interview_turn",
                        fake_run_interview_turn)
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "opening question\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    start_response = client.post(
        "/api/chat/start", json={"difficulty": "easy"})
    assert start_response.status_code == 200
    interview_id = start_response.get_json()["interview_id"]

    response = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "difficulty": "easy",
            "interview_id": interview_id,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert captured["difficulty"] == "easy"
    assert data["difficulty"] == "easy"
    assert data["pass_threshold"] == 6.5
    assert data["final_result"]["pass_threshold"] == 6.5
    assert captured["pass_threshold"] == 6.5
    assert captured["treat_candidate_input_as_untrusted"] is True


def test_chat_start_includes_difficulty_instruction(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            difficulty_enabled=True,
            difficulty_levels=("easy", "medium", "hard"),
            default_difficulty="medium",
        ),
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
        return "opening question"

    monkeypatch.setattr("app.routes.chat.get_interview_opener",
                        fake_get_interview_opener)

    response = client.post("/api/chat/start", json={"difficulty": "hard"})

    assert response.status_code == 200
    assert "Difficulty mode: Principal-level (hard)." in captured["system_prompt"]


def test_chat_rejects_non_integer_max_question_roundtrips(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor("coding_focus"),
    )

    response = client.post(
        "/api/chat",
        json={"message": "hello", "max_question_roundtrips": "five"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "max_question_roundtrips must be an integer"
    }


def test_chat_rejects_out_of_range_max_question_roundtrips(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
            min_question_roundtrips=1,
            max_question_roundtrips=10,
        ),
    )

    response = client.post(
        "/api/chat",
        json={"message": "hello", "max_question_roundtrips": 11},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "max_question_roundtrips must be between 1 and 10"
    }


def test_chat_requires_interview_id_when_rating_enabled(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
        ),
    )

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "interview_id is required for interview chat"
    }


def test_chat_rejects_invalid_interview_id(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
        ),
    )

    response = client.post(
        "/api/chat",
        json={"message": "hello", "interview_id": "missing"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid interview_id"}


def test_chat_rejects_interview_id_for_different_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    descriptors = {
        "coding_focus": _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
        ),
        "behavioral_focus": _make_descriptor(
            "behavioral_focus",
            interview_rating_enabled=True,
        ),
    }

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: descriptors[selected_name or "coding_focus"],
    )
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "opening question\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    start_response = client.post(
        "/api/chat/start",
        json={"system_prompt_name": "coding_focus"},
    )
    assert start_response.status_code == 200
    interview_id = start_response.get_json()["interview_id"]

    response = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "interview_id": interview_id,
            "system_prompt_name": "behavioral_focus",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "interview_id does not match the selected system prompt"
    }


def test_chat_start_returns_interview_id_for_interview_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
            default_question_roundtrips=5,
        ),
    )
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "Welcome.\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    response = client.post("/api/chat/start", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["reply"] == "Welcome."
    assert data["interview_enabled"] is True
    assert isinstance(data["interview_id"], str)
    assert data["counted_question_roundtrips"] == 1
    assert data["question_roundtrips_limit"] == 5


def test_chat_start_stores_selected_limit_and_session_count(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
            default_question_roundtrips=5,
            min_question_roundtrips=1,
            max_question_roundtrips=10,
        ),
    )
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "opening question\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    captured = {}

    def fake_run_interview_turn(
        message,
        conversation,
        descriptor,
        language,
        question_limit,
        pass_threshold,
        model_settings,
        difficulty=None,
        prior_question_count=None,
        **kwargs,
    ):
        captured["question_limit"] = question_limit
        captured["prior_question_count"] = prior_question_count
        return {
            "reply": "follow-up question",
            "turn_type": "question",
            "question_count": prior_question_count + 1,
            "question_limit": question_limit,
            "interview_complete": False,
            "pass_threshold": pass_threshold,
            "metadata_warning": False,
            "final_result": None,
        }

    monkeypatch.setattr("app.routes.chat.run_interview_turn",
                        fake_run_interview_turn)

    start_response = client.post(
        "/api/chat/start",
        json={"max_question_roundtrips": 4},
    )
    assert start_response.status_code == 200
    start_data = start_response.get_json()
    assert start_data["counted_question_roundtrips"] == 1
    assert start_data["question_roundtrips_limit"] == 4

    response = client.post(
        "/api/chat",
        json={
            "message": "candidate answer",
            "interview_id": start_data["interview_id"],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert captured["question_limit"] == 4
    assert captured["prior_question_count"] == 1
    assert data["counted_question_roundtrips"] == 2
    assert data["question_roundtrips_limit"] == 4


def test_chat_keeps_interview_closed_after_completion(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
            default_question_roundtrips=2,
            pass_threshold=7.0,
            rubric_criteria=("Problem understanding",),
        ),
    )
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "Opening question.\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    call_counter = {"count": 0}

    def fake_run_interview_turn(*args, **kwargs):
        call_counter["count"] += 1
        return {
            "reply": "Thanks, that concludes the interview.",
            "turn_type": "other",
            "question_count": 2,
            "question_limit": 2,
            "interview_complete": True,
            "pass_threshold": 7.0,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 8.0,
                "pass_threshold": 7.0,
                "passed": True,
                "criterion_scores": [
                    {"criterion": "Problem understanding", "score": 8.0},
                ],
                "strengths": ["Clear communication"],
                "improvements": ["None"],
                "parse_warning": False,
            },
        }

    monkeypatch.setattr("app.routes.chat.run_interview_turn",
                        fake_run_interview_turn)

    start_response = client.post("/api/chat/start", json={})
    interview_id = start_response.get_json()["interview_id"]

    first_response = client.post(
        "/api/chat",
        json={"message": "candidate answer", "interview_id": interview_id},
    )
    assert first_response.status_code == 200
    assert call_counter["count"] == 1

    second_response = client.post(
        "/api/chat",
        json={
            "message": "another answer",
            "interview_id": interview_id,
            "conversation_history": [],
        },
    )

    assert second_response.status_code == 200
    second_payload = second_response.get_json()
    assert second_payload["interview_complete"] is True
    assert second_payload["reply"] == "Thanks, that concludes the interview."
    assert call_counter["count"] == 1


def test_chat_returns_interview_fields_when_rating_enabled(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
            default_question_roundtrips=5,
            pass_threshold=7.0,
            rubric_criteria=("Problem understanding", "Communication"),
        ),
    )
    monkeypatch.setattr(
        "app.routes.chat.run_interview_turn",
        lambda *args, **kwargs: {
            "reply": "What would you optimize next?",
            "turn_type": "question",
            "question_count": 3,
            "question_limit": 5,
            "interview_complete": False,
            "pass_threshold": 7.0,
            "metadata_warning": False,
            "final_result": None,
        },
    )
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "opening question\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    start_response = client.post("/api/chat/start", json={})
    assert start_response.status_code == 200
    interview_id = start_response.get_json()["interview_id"]

    response = client.post(
        "/api/chat",
        json={
            "message": "I would optimize memory usage",
            "interview_id": interview_id,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["reply"] == "What would you optimize next?"
    assert data["interview_enabled"] is True
    assert data["interview_complete"] is False
    assert data["counted_question_roundtrips"] == 3
    assert data["question_roundtrips_limit"] == 5


def test_chat_returns_rating_when_interview_completed(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
            default_question_roundtrips=5,
            pass_threshold=7.0,
            rubric_criteria=("Problem understanding", "Communication"),
        ),
    )
    monkeypatch.setattr(
        "app.routes.chat.run_interview_turn",
        lambda *args, **kwargs: {
            "reply": "Thanks, that concludes the interview.",
            "turn_type": "other",
            "question_count": 5,
            "question_limit": 5,
            "interview_complete": True,
            "pass_threshold": 7.0,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 8.2,
                "pass_threshold": 7.0,
                "passed": True,
                "criterion_scores": [
                    {"criterion": "Problem understanding", "score": 8.0},
                    {"criterion": "Communication", "score": 8.5},
                ],
                "strengths": ["Structured thinking"],
                "improvements": ["Add more edge cases"],
                "parse_warning": False,
            },
        },
    )
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "opening question\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    start_response = client.post("/api/chat/start", json={})
    assert start_response.status_code == 200
    interview_id = start_response.get_json()["interview_id"]

    response = client.post(
        "/api/chat",
        json={
            "message": "Thanks",
            "interview_id": interview_id,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["interview_complete"] is True
    assert data["final_result"]["passed"] is True


def test_chat_start_uses_default_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    default_descriptor = _make_descriptor(
        "coding_focus", name="Coding Interview")
    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
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

    monkeypatch.setattr("app.routes.chat.get_interview_opener",
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
        "app.routes.chat.resolve_prompt_descriptor", fake_resolver)
    monkeypatch.setattr("app.routes.chat.get_interview_opener",
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


def test_chat_start_strips_metadata_suffix_from_reply(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor("coding_focus"),
    )
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            "Welcome to the interview.\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    response = client.post("/api/chat/start", json={})

    assert response.status_code == 200
    assert response.get_json() == {"reply": "Welcome to the interview."}


def test_chat_start_allows_model_setting_overrides(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor("coding_focus"),
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
        captured["temperature"] = temperature
        captured["top_p"] = top_p
        captured["frequency_penalty"] = frequency_penalty
        captured["presence_penalty"] = presence_penalty
        captured["max_tokens"] = max_tokens
        return "opening question"

    monkeypatch.setattr("app.routes.chat.get_interview_opener",
                        fake_get_interview_opener)

    response = client.post(
        "/api/chat/start",
        json={
            "temperature": 0.2,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": -0.2,
        },
    )

    assert response.status_code == 200
    assert captured["temperature"] == 0.2
    assert captured["top_p"] == 0.9
    assert captured["frequency_penalty"] == 0.3
    assert captured["presence_penalty"] == -0.2
    assert captured["max_tokens"] == 500


def test_chat_start_rejects_non_numeric_model_setting(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor("coding_focus"),
    )

    response = client.post(
        "/api/chat/start",
        json={"top_p": "high"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "top_p must be a number"}


def test_chat_start_rejects_invalid_selected_system_prompt(monkeypatch):
    app = create_app()
    client = app.test_client()

    def bad_resolver(selected_name=None):
        raise ValueError("Unknown system prompt 'missing'")

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor", bad_resolver)

    response = client.post(
        "/api/chat/start",
        json={"system_prompt_name": "missing"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unknown system prompt 'missing'"}


def test_chat_uses_diagnostics_in_debug_mode(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus",
            interview_rating_enabled=True,
            default_question_roundtrips=2,
            pass_threshold=7.0,
            rubric_criteria=("Problem understanding",),
        ),
    )

    captured = {}

    def fake_run_interview_turn(
        message,
        conversation,
        descriptor,
        language,
        question_limit,
        pass_threshold,
        model_settings,
        difficulty=None,
        include_diagnostics=False,
        **kwargs,
    ):
        captured["include_diagnostics"] = include_diagnostics
        return {
            "reply": "Follow-up question",
            "turn_type": "question",
            "question_count": 1,
            "question_limit": question_limit,
            "interview_complete": False,
            "pass_threshold": pass_threshold,
            "metadata_warning": False,
            "final_result": None,
            "debug": {"raw_turn_reply": "raw model output"},
        }

    monkeypatch.setattr("app.routes.chat.run_interview_turn",
                        fake_run_interview_turn)
    monkeypatch.setattr(
        "app.routes.chat.get_interview_opener",
        lambda **kwargs: (
            (
                "opening question\n"
                "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
            ),
            {"raw": "diagnostics"},
        ) if kwargs.get("include_diagnostics") else (
            "opening question\n"
            "[PREPPER_JSON] {\"turn_type\":\"QUESTION\",\"interview_complete\":false}"
        ),
    )

    start_response = client.post("/api/chat/start", json={})
    assert start_response.status_code == 200
    interview_id = start_response.get_json()["interview_id"]

    response = client.post(
        "/api/chat",
        json={"message": "hello", "interview_id": interview_id},
    )

    assert response.status_code == 200
    assert captured["include_diagnostics"] is True
    data = response.get_json()
    assert data["reply"] == "Follow-up question"
    assert "debug" not in data


def test_chat_start_returns_502_when_llm_request_fails(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
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

    monkeypatch.setattr("app.routes.chat.get_interview_opener",
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


def test_chat_rate_limit_exceeded(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr(
        "app.routes.chat.resolve_prompt_descriptor",
        lambda selected_name=None: _make_descriptor(
            "coding_focus", name="Coding Interview"),
    )
    monkeypatch.setattr("app.routes.chat.get_chat_reply",
                        lambda *args, **kwargs: "ok")

    for _ in range(10):
        response = client.post("/api/chat", json={"message": "hello"})
        assert response.status_code == 200

    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 429
    assert response.get_json() == {"error": "rate limit exceeded"}
