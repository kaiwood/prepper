from pathlib import Path

import pytest

from prepper_cli.hr_fixtures import (
    FixtureValidationError,
    list_hr_fixture_ids,
    parse_transcript_markdown,
    validate_hr_fixture,
)


def test_list_hr_fixture_ids_contains_demo_fixture():
    assert "demo_hr" in list_hr_fixture_ids()


def test_validate_hr_fixture_loads_demo_fixture():
    fixture = validate_hr_fixture("demo_hr")

    assert fixture.id == "demo_hr"
    assert "Northstar Analytics" in fixture.company_markdown
    assert "Customer Success Data Analyst" in fixture.role_markdown
    assert set(fixture.transcripts) == {"strong", "weak"}
    assert fixture.transcripts["strong"].expected_final_result.passed is True
    assert fixture.transcripts["weak"].expected_final_result.passed is False


def test_validate_hr_fixture_rejects_missing_required_files(tmp_path: Path):
    fixture_dir = tmp_path / "broken"
    fixture_dir.mkdir()
    (fixture_dir / "company.md").write_text("company", encoding="utf-8")

    with pytest.raises(FixtureValidationError, match="role.md"):
        validate_hr_fixture("broken", root=tmp_path)


def test_validate_hr_fixture_rejects_path_traversal_fixture_id(tmp_path: Path):
    with pytest.raises(FixtureValidationError, match="Invalid HR fixture id"):
        validate_hr_fixture("../demo_hr", root=tmp_path)


def test_parse_transcript_markdown_reads_turns_tools_sources_and_result():
    raw = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "hr"
        / "demo_hr"
        / "transcripts"
        / "strong.md"
    ).read_text(encoding="utf-8")

    transcript = parse_transcript_markdown(raw, source_name="strong.md")

    assert transcript.fixture_id == "demo_hr"
    assert transcript.candidate == "strong"
    assert [turn.role for turn in transcript.turns] == [
        "interviewer",
        "candidate",
        "interviewer",
        "candidate",
    ]
    assert transcript.tool_events[0].tool_name == "retrieve_company_context"
    assert transcript.sources[0].url == "fixture://resume.md"
    assert transcript.expected_final_result.overall_score == pytest.approx(8.4)


@pytest.mark.parametrize(
    ("raw", "match"),
    [
        ("## Interviewer\n\nHello", "front matter"),
        (
            "---\nfixture: demo_hr\ncandidate: strong\n---\n\n## Unknown\n\nText",
            "unknown section",
        ),
        (
            "---\nfixture: demo_hr\ncandidate: strong\n---\n\n## Candidate\n\nAnswer",
            "first turn",
        ),
        (
            "---\nfixture: demo_hr\ncandidate: strong\n---\n\n## Interviewer\n\nQuestion\n\n## Candidate\n\nAnswer",
            "Expected Final Result",
        ),
        (
            "---\nfixture: demo_hr\ncandidate: strong\n---\n\n## Interviewer\n\nQuestion\n\n## Candidate\n\nAnswer\n\n## Expected Final Result\n\noverall_score: 7.0\npassed: true\nstrengths: Clear\nimprovements: More detail",
            "Tool Event",
        ),
    ],
)
def test_parse_transcript_markdown_reports_malformed_markdown(raw: str, match: str):
    with pytest.raises(FixtureValidationError, match=match):
        parse_transcript_markdown(raw, source_name="bad.md")
