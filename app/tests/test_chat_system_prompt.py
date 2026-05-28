from types import SimpleNamespace

from prepper_cli.chat import (
    _PROMPT_INJECTION_GUARDRAIL,
    get_chat_reply,
    get_interview_opener,
)
from prepper_cli.conversation import Conversation


class _FakeChatModel:
    def __init__(self, captured: dict, *, content="assistant reply", error=None):
        self.captured = captured
        self.content = content
        self.error = error

    def invoke(self, messages):
        self.captured.setdefault("calls", []).append(messages)
        self.captured["messages"] = messages
        if self.error is not None:
            raise self.error
        return SimpleNamespace(content=self.content)


def _patch_fake_chat_model(monkeypatch, *, content="assistant reply", error=None):
    captured: dict = {}

    def fake_build_chat_model(**kwargs):
        captured["model_kwargs"] = kwargs
        return _FakeChatModel(captured, content=content, error=error)

    monkeypatch.setattr("prepper_cli.chat.build_chat_model", fake_build_chat_model)
    return captured


def test_get_chat_reply_prepends_system_prompt_and_context(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    conversation = Conversation.from_messages(
        [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ]
    )

    reply = get_chat_reply(
        "new question",
        conversation=conversation,
        history_limit=3,
        system_prompt="You are a coach.",
        language="de",
    )

    assert reply == "assistant reply"
    assert captured["messages"] == [
        (
            "system",
            _PROMPT_INJECTION_GUARDRAIL,
        ),
        (
            "system",
            "Respond in German. Keep the full response in German unless the user explicitly asks to switch language.",
        ),
        ("system", "You are a coach."),
        ("human", "previous question"),
        ("ai", "previous answer"),
        ("human", "new question"),
    ]

    assert conversation.get_messages()[-2:] == [
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "assistant reply"},
    ]


def test_get_chat_reply_uses_french_language_prompt(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    get_chat_reply("bonjour", language="fr")

    assert captured["messages"][1] == (
        "system",
        "Respond in French. Keep the full response in French unless the user explicitly asks to switch language.",
    )


def test_get_chat_reply_forwards_tuning_params(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    get_chat_reply(
        "question",
        temperature=0.3,
        top_p=0.95,
        frequency_penalty=0.2,
        presence_penalty=0.1,
        max_tokens=700,
    )

    assert captured["model_kwargs"]["temperature"] == 0.3
    assert captured["model_kwargs"]["top_p"] == 0.95
    assert captured["model_kwargs"]["frequency_penalty"] == 0.2
    assert captured["model_kwargs"]["presence_penalty"] == 0.1
    assert captured["model_kwargs"]["max_tokens"] == 700


def test_get_chat_reply_omits_tuning_params_when_not_provided(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    get_chat_reply("question")

    assert "temperature" not in captured["model_kwargs"]
    assert "top_p" not in captured["model_kwargs"]
    assert "frequency_penalty" not in captured["model_kwargs"]
    assert "presence_penalty" not in captured["model_kwargs"]
    assert "max_tokens" not in captured["model_kwargs"]


def test_get_chat_reply_omits_individual_none_tuning_params(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    get_chat_reply("question", temperature=0.5, top_p=None)

    assert captured["model_kwargs"]["temperature"] == 0.5
    assert "top_p" not in captured["model_kwargs"]


def test_get_interview_opener_prepends_system_prompt_and_bootstrap_message(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch, content="  first question?  ")

    reply = get_interview_opener(
        system_prompt="You are an interviewer.", language="de"
    )

    assert reply == "first question?"
    assert captured["messages"] == [
        (
            "system",
            _PROMPT_INJECTION_GUARDRAIL,
        ),
        (
            "system",
            "Respond in German. Keep the full response in German unless the user explicitly asks to switch language.",
        ),
        ("system", "You are an interviewer."),
        (
            "human",
            "Begin the interview now. Ask the first interview question and wait for the candidate's response.",
        ),
    ]


def test_get_chat_reply_includes_guardrail_without_other_system_prompts(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    get_chat_reply("hello")

    assert captured["messages"][0] == (
        "system",
        _PROMPT_INJECTION_GUARDRAIL,
    )
    assert captured["messages"][1] == ("human", "hello")


def test_get_chat_reply_does_not_retry_errors(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch, error=RuntimeError("Connection error."))

    try:
        get_chat_reply("hello")
    except RuntimeError as exc:
        assert str(exc) == "Connection error."
    else:
        raise AssertionError("expected RuntimeError")

    assert len(captured["calls"]) == 1


def test_get_chat_reply_wraps_only_current_message_when_untrusted(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    conversation = Conversation.from_messages(
        [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ]
    )

    get_chat_reply(
        "hello",
        conversation=conversation,
        history_limit=3,
        treat_input_as_untrusted=True,
    )

    assert captured["messages"][1] == ("human", "previous question")
    assert captured["messages"][2] == ("ai", "previous answer")
    assert captured["messages"][3] == (
        "human",
        '<untrusted_input source="current_user_message">\nhello\n</untrusted_input>',
    )


def test_get_interview_opener_forwards_tuning_params(monkeypatch):
    captured = _patch_fake_chat_model(monkeypatch)

    get_interview_opener(
        temperature=0.3,
        top_p=0.95,
        frequency_penalty=0.2,
        presence_penalty=0.1,
        max_tokens=700,
    )

    assert captured["model_kwargs"]["temperature"] == 0.3
    assert captured["model_kwargs"]["top_p"] == 0.95
    assert captured["model_kwargs"]["frequency_penalty"] == 0.2
    assert captured["model_kwargs"]["presence_penalty"] == 0.1
    assert captured["model_kwargs"]["max_tokens"] == 700
