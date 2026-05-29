import pytest

import prepper_cli.resume_pdf as resume_pdf
from prepper_cli.hr_context import HrToolResult
from prepper_cli.hr_tools import HrToolError


def test_extract_resume_text_rejects_non_pdf_bytes():
    with pytest.raises(HrToolError, match="PDF"):
        resume_pdf.extract_resume_text_from_pdf_bytes(b"not a pdf")


def test_enrich_resume_text_markdown_llm_returns_markdown(monkeypatch):
    calls = {}

    class FakeLlm:
        def invoke(self, messages):
            calls["messages"] = messages
            return "```markdown\n# Jane Candidate\n\n## Skills\n- Python\n```"

    def fake_build_chat_model(**kwargs):
        calls["build_kwargs"] = kwargs
        return FakeLlm()

    monkeypatch.setattr(resume_pdf, "build_chat_model", fake_build_chat_model)

    result = resume_pdf.enrich_resume_text_markdown_llm(
        "Jane Candidate Python developer",
        model="test-model",
        max_chars=1000,
    )

    assert result == "# Jane Candidate\n\n## Skills\n- Python"
    assert calls["build_kwargs"]["model"] == "test-model"
    assert "semantic markdown" in calls["messages"][0][1]
    assert "Jane Candidate Python developer" in calls["messages"][1][1]


def test_enrich_resume_text_markdown_llm_rejects_oversized_output(monkeypatch):
    class FakeLlm:
        def invoke(self, messages):
            return "# Resume\n" + ("x" * 50)

    monkeypatch.setattr(
        resume_pdf,
        "build_chat_model",
        lambda **kwargs: FakeLlm(),
    )

    with pytest.raises(HrToolError, match="exceeded size limit"):
        resume_pdf.enrich_resume_text_markdown_llm("Jane Candidate", max_chars=10)


def test_run_extract_resume_pdf_profile_tool_enriches_before_candidate_profile(monkeypatch):
    calls = {}

    def fake_extract_pdf(pdf_bytes, *, max_chars):
        calls["pdf_bytes"] = pdf_bytes
        calls["max_chars"] = max_chars
        return "Jane Candidate Python developer"

    def fake_enrich(resume_text, *, model, max_chars):
        calls["enrich_kwargs"] = {
            "resume_text": resume_text,
            "model": model,
            "max_chars": max_chars,
        }
        return "# Jane Candidate\n\n## Skills\n- Python"

    def fake_candidate_tool(**kwargs):
        calls["candidate_kwargs"] = kwargs
        return HrToolResult(
            tool_name="extract_candidate_profile",
            status="success",
            output={"profile": {"skills": ["Python"]}},
        )

    monkeypatch.setattr(resume_pdf, "extract_resume_text_from_pdf_bytes", fake_extract_pdf)
    monkeypatch.setattr(resume_pdf, "enrich_resume_text_markdown_llm", fake_enrich)
    monkeypatch.setattr(resume_pdf, "run_extract_candidate_profile_tool", fake_candidate_tool)

    result = resume_pdf.run_extract_resume_pdf_profile_tool(
        pdf_bytes=b"%PDF-1.4",
        filename="resume.pdf",
        model="test-model",
        max_chars=123,
    )

    assert result.output["profile"]["skills"] == ["Python"]
    assert result.output["resume_text"] == "# Jane Candidate\n\n## Skills\n- Python"
    assert calls["pdf_bytes"] == b"%PDF-1.4"
    assert calls["max_chars"] == 123
    assert calls["enrich_kwargs"] == {
        "resume_text": "Jane Candidate Python developer",
        "model": "test-model",
        "max_chars": 123,
    }
    assert calls["candidate_kwargs"] == {
        "mode": "llm",
        "resume_text": "# Jane Candidate\n\n## Skills\n- Python",
        "profile_text": "",
        "model": "test-model",
        "max_chars": 123,
    }


def test_run_extract_resume_pdf_profile_tool_skips_enrichment_in_mock_mode(monkeypatch):
    calls = {}

    def fake_extract_pdf(pdf_bytes, *, max_chars):
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
        mode="mock",
        max_chars=123,
    )

    assert result.output["resume_text"] == "# Resume\nPython developer"
    assert calls["candidate_kwargs"]["mode"] == "mock"
    assert calls["candidate_kwargs"]["resume_text"] == "# Resume\nPython developer"
