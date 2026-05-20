from types import SimpleNamespace

from prepper_cli import main


def test_hr_fixtures_list_command_prints_fixture_ids(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["prepper-cli", "hr", "fixtures", "list"])
    monkeypatch.setattr(main, "list_hr_fixture_ids", lambda: ["demo_hr", "other"])

    assert main.main() == 0

    assert capsys.readouterr().out == "demo_hr\nother\n"


def test_hr_fixtures_validate_command_prints_success(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["prepper-cli", "hr", "fixtures", "validate", "--fixture", "demo_hr"],
    )
    called = {}

    def fake_validate_hr_fixture(fixture_id: str):
        called["fixture_id"] = fixture_id
        return SimpleNamespace(id=fixture_id)

    monkeypatch.setattr(main, "validate_hr_fixture", fake_validate_hr_fixture)

    assert main.main() == 0

    assert called == {"fixture_id": "demo_hr"}
    assert capsys.readouterr().out == "Fixture 'demo_hr' is valid.\n"


def test_hr_fixtures_validate_command_reports_errors(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["prepper-cli", "hr", "fixtures", "validate", "--fixture", "missing"],
    )

    def fake_validate_hr_fixture(fixture_id: str):
        raise ValueError(f"HR fixture '{fixture_id}' was not found")

    monkeypatch.setattr(main, "validate_hr_fixture", fake_validate_hr_fixture)

    assert main.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Error: HR fixture 'missing' was not found" in captured.err


def test_hr_prompt_preview_command_prints_rendered_prompt(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepper-cli",
            "hr",
            "prompt",
            "preview",
            "--fixture",
            "demo_hr",
            "--interview-style",
            "hr_candidate_fit",
        ],
    )
    fixture = SimpleNamespace(id="demo_hr")
    descriptor = SimpleNamespace(id="hr_candidate_fit")
    called = {}

    def fake_validate_hr_fixture(fixture_id: str):
        called["fixture_id"] = fixture_id
        return fixture

    def fake_load_prompt_descriptor(interview_style: str):
        called["interview_style"] = interview_style
        return descriptor

    def fake_render_hr_prompt_preview(received_fixture, received_descriptor):
        called["fixture"] = received_fixture
        called["descriptor"] = received_descriptor
        return "rendered prompt\n"

    monkeypatch.setattr(main, "validate_hr_fixture", fake_validate_hr_fixture)
    monkeypatch.setattr(main, "load_prompt_descriptor", fake_load_prompt_descriptor)
    monkeypatch.setattr(
        main, "render_hr_prompt_preview", fake_render_hr_prompt_preview
    )

    assert main.main() == 0

    assert called == {
        "fixture_id": "demo_hr",
        "interview_style": "hr_candidate_fit",
        "fixture": fixture,
        "descriptor": descriptor,
    }
    assert capsys.readouterr().out == "rendered prompt\n"
