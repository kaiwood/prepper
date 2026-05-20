from prepper_cli.hr_fixtures import validate_hr_fixture
from prepper_cli.hr_prompt_preview import render_hr_prompt_preview
from prepper_cli.system_prompts import load_prompt_descriptor


def test_render_hr_prompt_preview_includes_prompt_metadata_and_fixture_context():
    fixture = validate_hr_fixture("demo_hr")
    descriptor = load_prompt_descriptor("hr_candidate_fit")

    preview = render_hr_prompt_preview(fixture, descriptor)

    assert preview.startswith("# HR Prompt Preview: HR Candidate Fit Interview")
    assert "- id: hr_candidate_fit" in preview
    assert "- rubric_criteria: Role fit, Evidence quality, Communication, Company interest" in preview
    assert "## System Prompt" in preview
    assert "You are an HR interviewer" in preview
    assert "## Fixture Context" in preview
    assert "untrusted preview data" in preview
    assert "### Company (untrusted)" in preview
    assert "Northstar Analytics" in preview
    assert "### Role (untrusted)" in preview
    assert "Customer Success Data Analyst" in preview
    assert "### Resume (untrusted)" in preview
    assert "Jordan Lee" in preview
    assert "### Profile (untrusted)" in preview
    assert "responsible AI for HR" in preview
