import pytest

from prepper_cli.hr_assistant import (
    HR_ASSISTANT_RESPONSE_SCHEMA_VERSION,
    HrAssistantError,
    run_hr_assistant,
)
from prepper_cli.hr_context import build_mock_hr_context
from prepper_cli.hr_fixtures import validate_hr_fixture


def _context():
    return build_mock_hr_context(validate_hr_fixture("demo_hr"))


def test_hr_assistant_guides_setup_without_context():
    result = run_hr_assistant(message="What should I do next?")

    payload = result.payload
    assert payload["schema_version"] == HR_ASSISTANT_RESPONSE_SCHEMA_VERSION
    assert payload["status"] == "needs_setup"
    assert payload["context_id"] is None
    assert payload["missing_fields"] == [
        "company_url_or_text",
        "role_description",
        "resume_text",
    ]
    assert payload["tool_results"] == []
    assert "Build HR context" in payload["next_steps"][-1]


def test_hr_assistant_mock_answers_with_context_and_tool_results():
    context = _context()

    result = run_hr_assistant(
        message="What company facts should the interview test?",
        mode="mock",
        context=context,
    )

    payload = result.payload
    assert payload["status"] == "success"
    assert payload["context_id"] == context.context_id
    assert "Test whether the candidate" in payload["reply"]
    assert [tool["tool_name"] for tool in payload["tool_results"]] == [
        "extract_candidate_profile",
        "retrieve_company_context",
    ]
    assert payload["sources"]


def test_hr_assistant_rejects_invalid_mode():
    with pytest.raises(HrAssistantError, match="mode must be one of"):
        run_hr_assistant(message="Hello", mode="live")
