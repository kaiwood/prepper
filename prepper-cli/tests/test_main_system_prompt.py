from prepper_cli import main
from prepper_cli.system_prompts import PromptDescriptor


def _make_descriptor(id: str, name: str | None = None) -> PromptDescriptor:
    return PromptDescriptor(
        id=id,
        name=name or id,
        temperature=0.5,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=500,
        content=f"prompt::{id}",
    )


def test_non_interactive_uses_default_system_prompt(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "help me prepare"])
    monkeypatch.setattr(main, "list_system_prompt_names", lambda: ["interview_coach"])
    monkeypatch.setattr(main, "get_default_system_prompt_name", lambda: "interview_coach")
    monkeypatch.setattr(
        main,
        "load_prompt_descriptor",
        lambda name: _make_descriptor(name),
    )

    called = {}

    def fake_get_chat_reply(
        message,
        conversation=None,
        history_limit=10,
        system_prompt=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
    ):
        called["message"] = message
        called["system_prompt"] = system_prompt
        called["temperature"] = temperature
        return "ok"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert called["message"] == "help me prepare"
    assert called["system_prompt"] == "prompt::interview_coach"
    assert called["temperature"] == 0.5


def test_interactive_selection_applies_selected_prompt(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "--interactive"])
    monkeypatch.setattr(main, "list_system_prompt_names", lambda: ["first", "second"])
    monkeypatch.setattr(main, "get_default_system_prompt_name", lambda: "first")
    monkeypatch.setattr(
        main,
        "list_prompt_descriptors",
        lambda: [_make_descriptor("first"), _make_descriptor("second")],
    )
    monkeypatch.setattr(
        main,
        "load_prompt_descriptor",
        lambda name: _make_descriptor(name),
    )

    inputs = iter(["2", "practice question", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calls = []

    def fake_get_chat_reply(
        message,
        conversation=None,
        history_limit=10,
        system_prompt=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
    ):
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


def test_interactive_rating_prompt_stops_when_interview_completes(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "--interactive", "--system-prompt", "coding_focus"])
    monkeypatch.setattr(main, "list_system_prompt_names", lambda: ["coding_focus"])
    monkeypatch.setattr(main, "get_default_system_prompt_name", lambda: "coding_focus")
    monkeypatch.setattr(
        main,
        "load_prompt_descriptor",
        lambda name: PromptDescriptor(
            id=name,
            name="Coding Interview",
            temperature=0.3,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            max_tokens=600,
            content="prompt::coding_focus",
            interview_rating_enabled=True,
            default_question_roundtrips=1,
            pass_threshold=7.0,
            rubric_criteria=("Problem understanding",),
        ),
    )

    inputs = iter(["answer", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(
        main,
        "run_interview_turn",
        lambda **kwargs: {
            "reply": "Thanks for your answer.",
            "turn_type": "other",
            "question_count": 1,
            "question_limit": 1,
            "interview_complete": True,
            "pass_threshold": 7.0,
            "metadata_warning": False,
            "final_result": {
                "overall_score": 8.0,
                "pass_threshold": 7.0,
                "passed": True,
                "criterion_scores": [{"criterion": "Problem understanding", "score": 8.0}],
                "strengths": ["Structured"],
                "improvements": ["Deeper examples"],
                "parse_warning": False,
            },
        },
    )

    exit_code = main.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Interview is now over." in captured.out
    assert '"final_result"' in captured.out
