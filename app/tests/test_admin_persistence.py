from prepper_cli.admin_persistence import load_latest_admin_hr_setup, save_admin_hr_setup


def test_save_and_load_latest_admin_hr_setup(tmp_path):
    db_path = tmp_path / "prepper.sqlite3"

    first = save_admin_hr_setup(
        db_path=db_path,
        setup_fields={
            "company_url": None,
            "company_text": " Company ",
            "role_description": " Role ",
            "resume_text": " Resume ",
            "profile_text": " Profile ",
        },
        response_payload={"context_id": "hrctx_first", "status": "success"},
        context_payload={"context_id": "hrctx_first", "schema_version": "hr-context.v2"},
    )
    second = save_admin_hr_setup(
        db_path=db_path,
        setup_fields={
            "company_url": "https://example.com",
            "role_description": "New role",
            "resume_text": "New resume",
        },
        response_payload={"context_id": "hrctx_second", "status": "success"},
        context_payload={"context_id": "hrctx_second", "schema_version": "hr-context.v2"},
    )

    latest = load_latest_admin_hr_setup(db_path=db_path)

    assert latest is not None
    assert first.id < second.id
    assert latest.id == second.id
    assert latest.context_id == "hrctx_second"
    assert latest.setup_fields == {
        "company_url": "https://example.com",
        "company_text": "",
        "role_description": "New role",
        "resume_text": "New resume",
        "profile_text": "",
    }
    assert latest.response_payload["status"] == "success"
    assert latest.context_payload["context_id"] == "hrctx_second"


def test_load_latest_admin_hr_setup_returns_none_for_missing_db(tmp_path):
    assert load_latest_admin_hr_setup(db_path=tmp_path / "missing.sqlite3") is None
