from types import SimpleNamespace

from prepper_cli.chat import get_chat_reply, get_interview_opener
from prepper_cli.conversation import Conversation


def _make_fake_client(captured: dict):
    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="assistant reply"))]
        )

    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )


def test_get_chat_reply_prepends_system_prompt_and_context(monkeypatch):
    captured_messages = []

    def fake_create(*, model, messages, **kwargs):
        captured_messages.extend(messages)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="assistant reply"))]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    monkeypatch.setattr(
        "prepper_cli.chat.get_client", lambda: (fake_client, "fake-model")
    )

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
    assert captured_messages == [
        {
            "role": "system",
            "content": "Respond in German. Keep the full response in German unless the user explicitly asks to switch language.",
        },
        {"role": "system", "content": "You are a coach."},
        {"role": "user", "content": "previous question"},
        {"role": "assistant", "content": "previous answer"},
        {"role": "user", "content": "new question"},
    ]

    assert conversation.get_messages()[-2:] == [
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "assistant reply"},
    ]


def test_get_chat_reply_forwards_tuning_params(monkeypatch):
    captured: dict = {}
    fake_client = _make_fake_client(captured)

    monkeypatch.setattr(
        "prepper_cli.chat.get_client", lambda: (fake_client, "fake-model")
    )

    get_chat_reply(
        "question",
        temperature=0.3,
        top_p=0.95,
        frequency_penalty=0.2,
        presence_penalty=0.1,
        max_tokens=700,
    )

    assert captured["temperature"] == 0.3
    assert captured["top_p"] == 0.95
    assert captured["frequency_penalty"] == 0.2
    assert captured["presence_penalty"] == 0.1
    assert captured["max_tokens"] == 700


def test_get_chat_reply_omits_tuning_params_when_not_provided(monkeypatch):
    captured: dict = {}
    fake_client = _make_fake_client(captured)

    monkeypatch.setattr(
        "prepper_cli.chat.get_client", lambda: (fake_client, "fake-model")
    )

    get_chat_reply("question")

    assert "temperature" not in captured
    assert "top_p" not in captured
    assert "frequency_penalty" not in captured
    assert "presence_penalty" not in captured
    assert "max_tokens" not in captured


def test_get_chat_reply_omits_individual_none_tuning_params(monkeypatch):
    captured: dict = {}
    fake_client = _make_fake_client(captured)

    monkeypatch.setattr(
        "prepper_cli.chat.get_client", lambda: (fake_client, "fake-model")
    )

    get_chat_reply("question", temperature=0.5, top_p=None)

    assert captured["temperature"] == 0.5
    assert "top_p" not in captured


def test_get_interview_opener_prepends_system_prompt_and_bootstrap_message(monkeypatch):
    captured_messages = []

    def fake_create(*, model, messages, **kwargs):
        captured_messages.extend(messages)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(
                    content="  first question?  "))
            ]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    monkeypatch.setattr(
        "prepper_cli.chat.get_client", lambda: (fake_client, "fake-model")
    )

    reply = get_interview_opener(
        system_prompt="You are an interviewer.", language="de")

    assert reply == "first question?"
    assert captured_messages == [
        {
            "role": "system",
            "content": "Respond in German. Keep the full response in German unless the user explicitly asks to switch language.",
        },
        {"role": "system", "content": "You are an interviewer."},
        {
            "role": "user",
            "content": "Begin the interview now. Ask the first interview question and wait for the candidate's response.",
        },
    ]


def test_get_interview_opener_forwards_tuning_params(monkeypatch):
    captured: dict = {}
    fake_client = _make_fake_client(captured)

    monkeypatch.setattr(
        "prepper_cli.chat.get_client", lambda: (fake_client, "fake-model")
    )

    get_interview_opener(
        temperature=0.3,
        top_p=0.95,
        frequency_penalty=0.2,
        presence_penalty=0.1,
        max_tokens=700,
    )

    assert captured["temperature"] == 0.3
    assert captured["top_p"] == 0.95
    assert captured["frequency_penalty"] == 0.2
    assert captured["presence_penalty"] == 0.1
    assert captured["max_tokens"] == 700
