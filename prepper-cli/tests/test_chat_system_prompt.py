from types import SimpleNamespace

from prepper_cli.chat import get_chat_reply
from prepper_cli.conversation import Conversation


def test_get_chat_reply_prepends_system_prompt_and_context(monkeypatch):
    captured_messages = []

    def fake_create(*, model, messages):
        captured_messages.extend(messages)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="assistant reply"))]
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
    )

    assert reply == "assistant reply"
    assert captured_messages == [
        {"role": "system", "content": "You are a coach."},
        {"role": "user", "content": "previous question"},
        {"role": "assistant", "content": "previous answer"},
        {"role": "user", "content": "new question"},
    ]

    assert conversation.get_messages()[-2:] == [
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "assistant reply"},
    ]
