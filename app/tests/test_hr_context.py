import copy
import json
from pathlib import Path

import pytest

from prepper_cli.hr_context import (
    HR_CONTEXT_SCHEMA_VERSION,
    HrContextValidationError,
    build_hr_context_from_fixture,
    build_mock_hr_context,
    hr_context_from_dict,
    hr_context_from_json,
    hr_context_to_dict,
    hr_context_to_json,
    load_hr_context,
    write_hr_context,
)
from prepper_cli.hr_fixtures import validate_hr_fixture


def test_build_mock_hr_context_from_demo_fixture():
    fixture = validate_hr_fixture("demo_hr")

    context = build_mock_hr_context(fixture)

    assert context.schema_version == HR_CONTEXT_SCHEMA_VERSION
    assert context.context_id.startswith("hrctx_demo_hr_")
    assert context.fixture_id == "demo_hr"
    assert context.mode == "mock"
    assert context.company_inputs[0].source_id == "company"
    assert "Northstar Analytics" in context.company_inputs[0].markdown
    assert context.role_description.source_id == "role"
    assert "Customer Success Data Analyst" in context.role_description.markdown
    assert [document.source_id for document in context.candidate_inputs] == [
        "resume",
        "profile",
    ]
    assert "Northstar Analytics" in context.summaries.company
    assert "Customer Success Data Analyst" in context.summaries.role
    assert "SQL" in context.summaries.candidate
    assert "SQL" in context.candidate_profile.skills
    assert "Customer Insights Analyst, BrightPath HR Software" in context.candidate_profile.experience
    assert context.candidate_profile.interview_focus_areas
    assert len(context.chunks) == 8
    assert context.chunks[0].id == "company_chunk_001"
    assert context.chunks[0].source_id == "company"
    assert context.chunks[0].metadata["source_uri"] == "fixture://company.md"
    assert context.chunks[0].metadata["source_kind"] == "company"
    assert context.chunks[4].id == "role_chunk_001"
    assert context.chunks[4].metadata["source_uri"] == "fixture://role.md"
    assert [result.tool_name for result in context.tool_results] == [
        "extract_candidate_profile"
    ]

    assert {source.uri for source in context.sources} == {
        "fixture://company.md",
        "fixture://role.md",
        "fixture://resume.md",
        "fixture://profile.md",
        "fixture://transcripts/strong.md",
        "fixture://transcripts/weak.md",
    }

    replay_by_candidate = {
        transcript.candidate: transcript
        for transcript in context.replay_metadata.transcripts
    }
    assert replay_by_candidate["strong"].turn_count == 4
    assert replay_by_candidate["strong"].tool_event_count == 1
    assert replay_by_candidate["strong"].source_count == 1
    assert replay_by_candidate["strong"].expected_overall_score == pytest.approx(8.4)
    assert replay_by_candidate["strong"].expected_passed is True
    assert replay_by_candidate["weak"].expected_passed is False


def test_build_hr_context_from_fixture_rejects_non_mock_mode():
    fixture = validate_hr_fixture("demo_hr")

    with pytest.raises(HrContextValidationError, match="mock mode"):
        build_hr_context_from_fixture(fixture, mode="llm")


def test_hr_context_json_is_deterministic_and_round_trips():
    fixture = validate_hr_fixture("demo_hr")
    context = build_mock_hr_context(fixture)
    rebuilt_context = build_mock_hr_context(fixture)

    assert rebuilt_context.context_id == context.context_id
    assert hr_context_to_json(rebuilt_context) == hr_context_to_json(context)

    payload = hr_context_to_dict(context)
    assert hr_context_to_dict(hr_context_from_dict(payload)) == payload

    raw = hr_context_to_json(context)
    assert raw.endswith("\n")
    assert json.loads(raw)["context_id"] == context.context_id
    assert hr_context_to_dict(hr_context_from_json(raw)) == payload


def test_write_and_load_hr_context(tmp_path: Path):
    fixture = validate_hr_fixture("demo_hr")
    context = build_mock_hr_context(fixture)
    output_path = tmp_path / "nested" / "hr-context.json"

    written_path = write_hr_context(context, output_path)
    loaded_context = load_hr_context(output_path)

    assert written_path == output_path
    assert output_path.is_file()
    assert hr_context_to_dict(loaded_context) == hr_context_to_dict(context)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda payload: payload.pop("schema_version"), "schema_version"),
        (lambda payload: payload.update({"schema_version": "old"}), "Unsupported"),
        (lambda payload: payload.update({"mode": "live"}), "mode"),
        (lambda payload: payload.update({"company_inputs": []}), "company_inputs"),
        (lambda payload: payload.update({"candidate_inputs": []}), "candidate_inputs"),
        (lambda payload: payload["role_description"].pop("markdown"), "role_description.markdown"),
        (lambda payload: payload.pop("candidate_profile"), "candidate_profile"),
        (lambda payload: payload["candidate_profile"].update({"skills": [""]}), "candidate_profile.skills"),
        (lambda payload: payload["sources"][0].update({"uri": ""}), r"sources\[0\].uri"),
        (
            lambda payload: payload["replay_metadata"]["transcripts"][0].update(
                {"turn_count": True}
            ),
            "turn_count",
        ),
    ],
)
def test_hr_context_from_dict_reports_invalid_payloads(mutate, match):
    payload = hr_context_to_dict(build_mock_hr_context(validate_hr_fixture("demo_hr")))
    broken_payload = copy.deepcopy(payload)
    mutate(broken_payload)

    with pytest.raises(HrContextValidationError, match=match):
        hr_context_from_dict(broken_payload)


def test_hr_context_from_dict_accepts_legacy_v1_without_candidate_profile():
    payload = hr_context_to_dict(build_mock_hr_context(validate_hr_fixture("demo_hr")))
    payload["schema_version"] = "hr-context.v1"
    payload.pop("candidate_profile")

    context = hr_context_from_dict(payload)

    assert context.schema_version == "hr-context.v1"
    assert context.candidate_profile.experience == (payload["summaries"]["candidate"],)


def test_hr_context_from_json_reports_invalid_json():
    with pytest.raises(HrContextValidationError, match="Invalid HR context JSON"):
        hr_context_from_json("not json")
