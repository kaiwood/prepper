import pytest

import prepper_cli.resume_pdf as resume_pdf
from prepper_cli.hr_context import HrToolResult
from prepper_cli.hr_tools import HrToolError


def test_extract_resume_text_rejects_non_pdf_bytes():
    with pytest.raises(HrToolError, match="PDF"):
        resume_pdf.extract_resume_text_from_pdf_bytes(b"not a pdf")


def test_run_extract_resume_pdf_profile_tool_uses_candidate_profile_tool(monkeypatch):
    calls = {}

    def fake_extract_pdf(pdf_bytes, *, max_chars):
        calls["pdf_bytes"] = pdf_bytes
        calls["max_chars"] = max_chars
        return "# Resume\nPython developer"

    def fake_candidate_tool(**kwargs):
        calls["candidate_kwargs"] = kwargs
        return HrToolResult(
            tool_name="extract_candidate_profile",
            status="success",
            output={"profile": {"skills": ["Python"]}},
        )

    monkeypatch.setattr(resume_pdf, "extract_resume_text_from_pdf_bytes", fake_extract_pdf)
    monkeypatch.setattr(resume_pdf, "run_extract_candidate_profile_tool", fake_candidate_tool)

    result = resume_pdf.run_extract_resume_pdf_profile_tool(
        pdf_bytes=b"%PDF-1.4",
        filename="resume.pdf",
        model="test-model",
        max_chars=123,
    )

    assert result.output["profile"]["skills"] == ["Python"]
    assert result.output["resume_text"] == "# Resume\nPython developer"
    assert calls["pdf_bytes"] == b"%PDF-1.4"
    assert calls["max_chars"] == 123
    assert calls["candidate_kwargs"] == {
        "mode": "llm",
        "resume_text": "# Resume\nPython developer",
        "profile_text": "",
        "model": "test-model",
        "max_chars": 123,
    }
