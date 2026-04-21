from prepper_cli import get_chat_reply


def test_package_exports_chat_function():
    assert callable(get_chat_reply)
