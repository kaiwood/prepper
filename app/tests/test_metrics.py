from prepper_cli.metrics import get_metrics_snapshot, record_metric_event


def test_metrics_snapshot_aggregates_sanitized_events(tmp_path):
    db_path = tmp_path / "metrics.sqlite3"

    record_metric_event(
        "route_request",
        status="success",
        route="/api/hr/context",
        method="POST",
        status_code=200,
        duration_ms=120,
        db_path=db_path,
    )
    record_metric_event(
        "tool_call",
        status="error",
        tool_name="fetch_company_website",
        duration_ms=50,
        error_type="UnsafeCompanyWebsiteUrlError",
        error_message="Company website URL resolves to blocked address: 127.0.0.1",
        resume_text="secret resume",
        db_path=db_path,
    )
    record_metric_event(
        "retrieval",
        status="success",
        duration_ms=25,
        result_count=2,
        chunk_count=8,
        top_score=0.75,
        snippets=["must not be stored"],
        db_path=db_path,
    )

    snapshot = get_metrics_snapshot(db_path=db_path)

    assert snapshot["overview"]["requests_total"] == 1
    assert snapshot["overview"]["rag_retrievals"] == 1
    assert snapshot["rag"]["avg_top_relevance_percent"] == 75
    assert snapshot["safety"]["blocked_url_attempts"] == 1
    assert snapshot["tools"][0]["name"] == "fetch_company_website"
    tool_event = next(
        event for event in snapshot["recent_events"] if event["label"] == "fetch_company_website"
    )
    assert tool_event["error_message"] == "Company website URL resolves to blocked address: 127.0.0.1"
    assert all("secret resume" not in str(event) for event in snapshot["recent_events"])
