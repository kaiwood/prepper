from prepper_cli import Conversation


def test_conversation_tracks_messages_and_recent_window():
    conversation = Conversation()

    conversation.add_user_message("first question")
    conversation.add_assistant_reply("first answer")
    conversation.add_user_message("second question")
    conversation.add_assistant_reply("second answer")

    assert conversation.get_messages() == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "second question"},
        {"role": "assistant", "content": "second answer"},
    ]

    assert conversation.get_recent_messages(limit=2) == [
        {"role": "user", "content": "second question"},
        {"role": "assistant", "content": "second answer"},
    ]


def test_from_messages_rejects_invalid_role():
    bad_history = [{"role": "system", "content": "invalid"}]

    try:
        Conversation.from_messages(bad_history)
    except ValueError as exc:
        assert str(exc) == "conversation_history contains an invalid role"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected ValueError for invalid role")


def test_from_messages_rejects_non_object_items():
    bad_history = ["not-a-message"]

    try:
        Conversation.from_messages(bad_history)
    except ValueError as exc:
        assert str(exc) == "conversation_history must contain objects"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected ValueError for non-object history item")
