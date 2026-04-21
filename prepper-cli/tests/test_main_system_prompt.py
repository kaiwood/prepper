from prepper_cli import main


def test_non_interactive_uses_default_system_prompt(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "help me prepare"])
    monkeypatch.setattr(main, "list_system_prompt_names", lambda: ["interview_coach"])
    monkeypatch.setattr(main, "get_default_system_prompt_name", lambda: "interview_coach")
    monkeypatch.setattr(main, "load_system_prompt", lambda name: f"prompt::{name}")

    called = {}

    def fake_get_chat_reply(message, conversation=None, history_limit=10, system_prompt=None):
        called["message"] = message
        called["system_prompt"] = system_prompt
        return "ok"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert called == {
        "message": "help me prepare",
        "system_prompt": "prompt::interview_coach",
    }


def test_interactive_selection_applies_selected_prompt(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "--interactive"])
    monkeypatch.setattr(main, "list_system_prompt_names", lambda: ["first", "second"])
    monkeypatch.setattr(main, "get_default_system_prompt_name", lambda: "first")
    monkeypatch.setattr(main, "load_system_prompt", lambda name: f"prompt::{name}")

    inputs = iter(["2", "practice question", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calls = []

    def fake_get_chat_reply(message, conversation=None, history_limit=10, system_prompt=None):
        calls.append((message, system_prompt, conversation is not None))
        return "assistant"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert calls == [("practice question", "prompt::second", True)]


def test_list_system_prompts_option_prints_prompt_names(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "--list-system-prompts"])
    monkeypatch.setattr(main, "list_system_prompt_names", lambda: ["a", "b"])

    exit_code = main.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == "a\nb\n"
