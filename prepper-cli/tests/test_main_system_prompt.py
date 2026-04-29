import pytest

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


def test_default_mode_is_interactive_with_selected_system_prompt(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepper-cli"])
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["coding_focus"])
    monkeypatch.setattr(
        main, "get_default_system_prompt_name", lambda: "coding_focus")
    monkeypatch.setattr(
        main,
        "list_prompt_descriptors",
        lambda: [_make_descriptor("coding_focus")],
    )
    monkeypatch.setattr(
        main,
        "load_prompt_descriptor",
        lambda name: _make_descriptor(name),
    )

    called = {}
    inputs = iter(["", "help me prepare", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calls = []

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
        model=None,
    ):
        calls.append(
            {
                "message": message,
                "system_prompt": system_prompt,
                "temperature": temperature,
            }
        )
        return "ok"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert calls[0]["message"] == "I am ready for the interview. Please begin."
    assert calls[0]["system_prompt"] == "prompt::coding_focus"
    assert calls[1]["message"] == "help me prepare"
    assert calls[1]["system_prompt"] == "prompt::coding_focus"
    assert calls[1]["temperature"] == 0.5


def test_interactive_selection_applies_selected_prompt(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prepper-cli"])
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["first", "second"])
    monkeypatch.setattr(
        main, "get_default_system_prompt_name", lambda: "first")
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
        language=None,
        temperature=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
        model=None,
    ):
        calls.append((message, system_prompt, conversation is not None))
        return "assistant"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert calls == [
        ("I am ready for the interview. Please begin.", "prompt::second", True),
        ("practice question", "prompt::second", True),
    ]


def test_system_prompt_starts_interview_immediately(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv", ["prepper-cli", "--system-prompt", "behavioral_focus"])
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["behavioral_focus"])
    monkeypatch.setattr(main, "get_default_system_prompt_name",
                        lambda: "behavioral_focus")
    monkeypatch.setattr(main, "load_prompt_descriptor",
                        lambda name: _make_descriptor(name))

    inputs = iter(["quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    called = {}

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
        model=None,
    ):
        called["message"] = message
        return "Opening question"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert called["message"] == "I am ready for the interview. Please begin."
    captured = capsys.readouterr()
    assert "Assistant" in captured.out
    assert "Opening question" in captured.out


def test_list_system_prompts_option_prints_prompt_names(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "--list-system-prompts"])
    monkeypatch.setattr(main, "list_system_prompt_names", lambda: ["a", "b"])

    exit_code = main.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == "a\nb\n"


def test_interactive_rating_prompt_stops_when_interview_completes(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv", ["prepper-cli", "--system-prompt", "coding_focus"])
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["coding_focus"])
    monkeypatch.setattr(
        main, "get_default_system_prompt_name", lambda: "coding_focus")
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

    inputs = iter(["quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    calls = []

    def fake_run_interview_turn(**kwargs):
        calls.append(kwargs["message"])
        return {
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
        }

    monkeypatch.setattr(
        main,
        "run_interview_turn",
        fake_run_interview_turn,
    )

    exit_code = main.main()

    assert exit_code == 0
    assert calls == ["I am ready for the interview. Please begin."]
    captured = capsys.readouterr()
    assert "Interviewer" in captured.out
    assert "Thanks for your answer." in captured.out
    assert "Final Candidate Score" in captured.out
    assert "Overall: 8.00 / 10.00 | Threshold: 7.00 | Passed: true" in captured.out
    assert '"final_result"' not in captured.out
    assert "Interview is now over." not in captured.out
    assert "Question limit:" not in captured.out


def test_benchmark_mode_dispatches_with_selected_prompts(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--benchmark",
            "--color",
            "--system-prompt",
            "coding_focus",
            "--difficulty",
            "hard",
            "--language",
            "de",
            "--question-limit",
            "3",
            "--pass-threshold",
            "7.2",
        ],
    )

    descriptors = {
        "coding_focus": _make_descriptor("coding_focus", name="Coding Interview"),
    }

    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["coding_focus"])
    monkeypatch.setattr(
        main, "get_default_system_prompt_name", lambda: "coding_focus")
    monkeypatch.setattr(main, "load_prompt_descriptor",
                        lambda name: descriptors[name])

    called = {}

    def fake_run_benchmark_interview(
        interviewer_descriptor,
        difficulty=None,
        language=None,
        question_limit_override=None,
        pass_threshold_override=None,
        candidate_profile="strong",
        output=None,
        enable_color=False,
        model=None,
        benchmark_model=None,
        temperature_override=None,
        top_p_override=None,
        frequency_penalty_override=None,
        presence_penalty_override=None,
        max_tokens_override=None,
    ):
        called["interviewer"] = interviewer_descriptor.id
        called["difficulty"] = difficulty
        called["language"] = language
        called["question_limit_override"] = question_limit_override
        called["pass_threshold_override"] = pass_threshold_override
        called["candidate_profile"] = candidate_profile
        called["enable_color"] = enable_color
        called["temperature_override"] = temperature_override
        called["top_p_override"] = top_p_override
        called["frequency_penalty_override"] = frequency_penalty_override
        called["presence_penalty_override"] = presence_penalty_override
        called["max_tokens_override"] = max_tokens_override
        return {
            "summary_json": {
                "mode": "benchmark",
                "interviewer_system_prompt": interviewer_descriptor.id,
            },
            "conversation": [],
        }

    monkeypatch.setattr(main, "run_benchmark_interview",
                        fake_run_benchmark_interview)

    exit_code = main.main()

    assert exit_code == 0
    assert called["interviewer"] == "coding_focus"
    assert called["difficulty"] == "hard"
    assert called["language"] == "de"
    assert called["question_limit_override"] == 3
    assert called["pass_threshold_override"] == 7.2
    assert called["candidate_profile"] == "strong"
    assert called["enable_color"] is True
    assert called["temperature_override"] is None
    assert called["top_p_override"] is None
    assert called["frequency_penalty_override"] is None
    assert called["presence_penalty_override"] is None
    assert called["max_tokens_override"] is None

    captured = capsys.readouterr()
    assert captured.out == ""


def test_benchmark_mode_uses_default_candidate_profile(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--benchmark",
            "--system-prompt",
            "behavioral_focus",
        ],
    )

    descriptor = _make_descriptor(
        "behavioral_focus", name="Behavioral Interview")
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["behavioral_focus"])
    monkeypatch.setattr(main, "get_default_system_prompt_name",
                        lambda: "behavioral_focus")
    monkeypatch.setattr(main, "load_prompt_descriptor", lambda _: descriptor)

    called = {}

    def fake_run_benchmark_interview(
        interviewer_descriptor,
        difficulty=None,
        language=None,
        question_limit_override=None,
        pass_threshold_override=None,
        candidate_profile="strong",
        output=None,
        enable_color=False,
        model=None,
        benchmark_model=None,
        temperature_override=None,
        top_p_override=None,
        frequency_penalty_override=None,
        presence_penalty_override=None,
        max_tokens_override=None,
    ):
        called["interviewer"] = interviewer_descriptor.id
        called["language"] = language
        called["candidate_profile"] = candidate_profile
        called["enable_color"] = enable_color
        return {
            "summary_json": {
                "mode": "benchmark",
                "interviewer_system_prompt": interviewer_descriptor.id,
            },
            "conversation": [],
        }

    monkeypatch.setattr(main, "run_benchmark_interview",
                        fake_run_benchmark_interview)

    exit_code = main.main()

    assert exit_code == 0
    assert called["interviewer"] == "behavioral_focus"
    assert called["language"] == "en"
    assert called["candidate_profile"] == "strong"
    assert called["enable_color"] is False

    captured = capsys.readouterr()
    assert captured.out == ""


def test_benchmark_mode_uses_explicit_weak_candidate_profile(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--benchmark",
            "--system-prompt",
            "behavioral_focus",
            "--weak-candidate",
        ],
    )

    descriptor = _make_descriptor(
        "behavioral_focus", name="Behavioral Interview")
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["behavioral_focus"])
    monkeypatch.setattr(main, "get_default_system_prompt_name",
                        lambda: "behavioral_focus")
    monkeypatch.setattr(main, "load_prompt_descriptor", lambda _: descriptor)

    called = {}

    def fake_run_benchmark_interview(
        interviewer_descriptor,
        difficulty=None,
        language=None,
        question_limit_override=None,
        pass_threshold_override=None,
        candidate_profile="strong",
        output=None,
        enable_color=False,
        model=None,
        benchmark_model=None,
        temperature_override=None,
        top_p_override=None,
        frequency_penalty_override=None,
        presence_penalty_override=None,
        max_tokens_override=None,
    ):
        called["interviewer"] = interviewer_descriptor.id
        called["candidate_profile"] = candidate_profile
        called["enable_color"] = enable_color
        return {
            "summary_json": {
                "mode": "benchmark",
                "interviewer_system_prompt": interviewer_descriptor.id,
            },
            "conversation": [],
        }

    monkeypatch.setattr(main, "run_benchmark_interview",
                        fake_run_benchmark_interview)

    exit_code = main.main()

    assert exit_code == 0
    assert called["interviewer"] == "behavioral_focus"
    assert called["candidate_profile"] == "weak"
    assert called["enable_color"] is False

    captured = capsys.readouterr()
    assert captured.out == ""


def test_benchmark_mode_rejects_conflicting_candidate_flags(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--benchmark",
            "--strong-candidate",
            "--weak-candidate",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 2


def test_candidate_flags_require_benchmark(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--strong-candidate",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 2


def test_color_flag_is_allowed_in_interactive_mode(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--color",
            "--system-prompt",
            "coding_focus",
        ],
    )
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["coding_focus"])
    monkeypatch.setattr(main, "load_prompt_descriptor",
                        lambda _: _make_descriptor("coding_focus"))

    inputs = iter(["hello", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    called = {}

    def fake_get_chat_reply(*args, **kwargs):
        called["system_prompt"] = kwargs["system_prompt"]
        return "assistant"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert called["system_prompt"] == "prompt::coding_focus"


def test_language_flag_is_forwarded_in_interactive_mode(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--language",
            "de",
            "--system-prompt",
            "coding_focus",
        ],
    )
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["coding_focus"])
    monkeypatch.setattr(main, "load_prompt_descriptor",
                        lambda _: _make_descriptor("coding_focus"))

    inputs = iter(["hello", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    called = {}

    def fake_get_chat_reply(*args, **kwargs):
        called["language"] = kwargs["language"]
        return "assistant"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert called["language"] == "de"


def test_interactive_passes_interview_overrides(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--system-prompt",
            "coding_focus",
            "--difficulty",
            "hard",
            "--language",
            "de",
            "--question-limit",
            "3",
            "--pass-threshold",
            "7.2",
        ],
    )
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["coding_focus"])
    monkeypatch.setattr(
        main, "get_default_system_prompt_name", lambda: "coding_focus")
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
            difficulty_enabled=True,
            difficulty_levels=("easy", "medium", "hard"),
            default_difficulty="medium",
            easy_pass_threshold=6.5,
            medium_pass_threshold=7.0,
            hard_pass_threshold=7.5,
        ),
    )

    inputs = iter(["answer", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    called = {}

    def fake_run_interview_turn(**kwargs):
        called.update(
            {
                "language": kwargs["language"],
                "question_limit": kwargs["question_limit"],
                "pass_threshold": kwargs["pass_threshold"],
                "difficulty": kwargs["difficulty"],
            }
        )
        return {
            "reply": "Thanks for your answer.",
            "turn_type": "other",
            "question_count": 0,
            "question_limit": kwargs["question_limit"],
            "interview_complete": False,
            "pass_threshold": kwargs["pass_threshold"],
            "metadata_warning": False,
            "final_result": None,
        }

    monkeypatch.setattr(main, "run_interview_turn", fake_run_interview_turn)

    exit_code = main.main()

    assert exit_code == 0
    assert called == {
        "language": "de",
        "question_limit": 3,
        "pass_threshold": 7.2,
        "difficulty": "hard",
    }


def test_interactive_passes_model_setting_overrides(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--system-prompt",
            "coding_focus",
            "--temperature",
            "0.2",
            "--top-p",
            "0.8",
            "--frequency-penalty",
            "0.4",
            "--presence-penalty",
            "-0.3",
            "--max-tokens",
            "321",
        ],
    )
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["coding_focus"])
    monkeypatch.setattr(main, "load_prompt_descriptor",
                        lambda _: _make_descriptor("coding_focus"))

    inputs = iter(["hello", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calls = []

    def fake_get_chat_reply(*args, **kwargs):
        calls.append(kwargs)
        return "assistant"

    monkeypatch.setattr(main, "get_chat_reply", fake_get_chat_reply)

    exit_code = main.main()

    assert exit_code == 0
    assert len(calls) == 2
    assert calls[0]["temperature"] == 0.2
    assert calls[0]["top_p"] == 0.8
    assert calls[0]["frequency_penalty"] == 0.4
    assert calls[0]["presence_penalty"] == -0.3
    assert calls[0]["max_tokens"] == 321
    assert calls[1]["temperature"] == 0.2
    assert calls[1]["top_p"] == 0.8
    assert calls[1]["frequency_penalty"] == 0.4
    assert calls[1]["presence_penalty"] == -0.3
    assert calls[1]["max_tokens"] == 321


def test_benchmark_mode_passes_model_setting_overrides(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "--benchmark",
            "--system-prompt",
            "behavioral_focus",
            "--temperature",
            "0.2",
            "--top-p",
            "0.9",
            "--frequency-penalty",
            "0.3",
            "--presence-penalty",
            "-0.2",
            "--max-tokens",
            "500",
        ],
    )
    monkeypatch.setattr(main, "list_system_prompt_names",
                        lambda: ["behavioral_focus"])
    monkeypatch.setattr(main, "load_prompt_descriptor",
                        lambda _: _make_descriptor("behavioral_focus"))

    called = {}

    def fake_run_benchmark_interview(**kwargs):
        called.update(kwargs)
        return {"summary_json": {"mode": "benchmark"}, "conversation": []}

    monkeypatch.setattr(main, "run_benchmark_interview",
                        fake_run_benchmark_interview)

    exit_code = main.main()

    assert exit_code == 0
    assert called["temperature_override"] == 0.2
    assert called["top_p_override"] == 0.9
    assert called["frequency_penalty_override"] == 0.3
    assert called["presence_penalty_override"] == -0.2
    assert called["max_tokens_override"] == 500


def test_help_makes_candidate_flags_benchmark_only_clear():
    help_text = main._build_parser().format_help()

    assert "--language {en,de}" in help_text
    assert "--temperature TEMPERATURE" in help_text
    assert "--top-p TOP_P" in help_text
    assert "--frequency-penalty FREQUENCY_PENALTY" in help_text
    assert "--presence-penalty PRESENCE_PENALTY" in help_text
    assert "--max-tokens MAX_TOKENS" in help_text
    assert "Response language code" in help_text
    assert "--color" in help_text
    assert "Enable colorized transcript output" in help_text
    assert "Benchmark-only: use a strong candidate simulation" in help_text
    assert "Benchmark-only: use a weak candidate simulation" in help_text
    assert "required for benchmark-only options" in help_text


def test_help_lists_benchmark_options_in_expected_order():
    help_text = main._build_parser().format_help()

    difficulty_index = help_text.index("--difficulty {easy,medium,hard}")
    language_index = help_text.index("--language {en,de}")
    pass_threshold_index = help_text.index("--pass-threshold PASS_THRESHOLD")
    question_limit_index = help_text.index("--question-limit QUESTION_LIMIT")
    temperature_index = help_text.index("--temperature TEMPERATURE")
    top_p_index = help_text.index("--top-p TOP_P")
    frequency_penalty_index = help_text.index(
        "--frequency-penalty FREQUENCY_PENALTY")
    presence_penalty_index = help_text.index(
        "--presence-penalty PRESENCE_PENALTY")
    max_tokens_index = help_text.index("--max-tokens MAX_TOKENS")
    color_index = help_text.index("--color")
    benchmark_index = help_text.index("--benchmark")
    strong_index = help_text.index("--strong-candidate")
    weak_index = help_text.index("--weak-candidate")

    assert difficulty_index < language_index < pass_threshold_index
    assert pass_threshold_index < question_limit_index < temperature_index
    assert temperature_index < top_p_index < frequency_penalty_index
    assert frequency_penalty_index < presence_penalty_index < max_tokens_index
    assert max_tokens_index < color_index
    assert color_index < benchmark_index < strong_index < weak_index
