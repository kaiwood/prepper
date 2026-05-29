from io import BytesIO

import pytest

from app import create_app
from prepper_cli.hr_context import HrToolResult


@pytest.fixture(autouse=True)
def isolated_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_SQLITE_PATH", str(tmp_path / "prepper.sqlite3"))


def test_hr_resume_extract_endpoint_returns_profile(monkeypatch):
    def fake_extract(*, pdf_bytes, filename=None, mode="llm", model=None):
        assert pdf_bytes.startswith(b"%PDF-")
        assert filename == "resume.pdf"
        assert mode == "llm"
        return HrToolResult(
            tool_name="extract_candidate_profile",
            status="success",
            output={
                "mode": "llm",
                "profile": {
                    "skills": ["Python", "SQL"],
                    "experience": ["Data analyst"],
                    "seniority_signals": ["Led analytics projects"],
                    "risks": ["No management scope shown"],
                    "interview_focus_areas": ["Validate stakeholder examples"],
                },
                "resume_text": "# Resume\nPython and SQL analyst",
                "document": {"markdown": "secret resume text"},
            },
        )

    monkeypatch.setattr(
        "app.routes.hr.run_extract_resume_pdf_profile_tool",
        fake_extract,
    )
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/resume/extract",
        data={"file": (BytesIO(b"%PDF-1.4\n..."), "resume.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["tool_result"]["tool_name"] == "extract_candidate_profile"
    assert data["tool_result"]["output"]["profile"]["skills"] == ["Python", "SQL"]
    assert data["tool_result"]["output"]["resume_text"] == "# Resume\nPython and SQL analyst"
    assert "document" not in data["tool_result"]["output"]

    latest_response = client.get("/api/hr/setup/latest")
    assert latest_response.status_code == 200
    latest = latest_response.get_json()
    assert latest["setup"]["resume_text"] == "# Resume\nPython and SQL analyst"
    assert "resume.pdf" not in str(latest)
    assert latest["context_result"] is None


def test_hr_resume_extract_endpoint_rejects_missing_file():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/hr/resume/extract", data={}, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Resume PDF file is required"


def test_hr_resume_extract_endpoint_rejects_non_pdf():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/resume/extract",
        data={"file": (BytesIO(b"hello"), "resume.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Resume upload must be a PDF file"


def test_hr_resume_extract_endpoint_rejects_oversized_pdf():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/hr/resume/extract",
        data={"file": (BytesIO(b"%PDF-" + b"x" * (5 * 1024 * 1024)), "resume.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Resume PDF exceeds 5 MB limit"
