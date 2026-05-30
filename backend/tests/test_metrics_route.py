from app import create_app
from prepper_cli.metrics import record_metric_event


def test_metrics_route_returns_dashboard_payload(monkeypatch, tmp_path):
    db_path = tmp_path / "prepper.sqlite3"
    monkeypatch.setenv("PREPPER_SQLITE_PATH", str(db_path))
    record_metric_event(
        "route_request",
        status="success",
        route="/api/hr/context",
        method="POST",
        status_code=200,
        duration_ms=100,
    )
    record_metric_event(
        "llm_call",
        status="error",
        operation="chat_completion",
        model="test-model",
        duration_ms=20,
    )

    app = create_app()
    client = app.test_client()

    response = client.get("/api/metrics")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema_version"] == "prepper-metrics.v1"
    assert payload["overview"]["requests_total"] == 1
    assert payload["overview"]["llm_failures"] == 1
    assert payload["llm"]["errors"] == 1


def test_metrics_route_validates_query(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_SQLITE_PATH", str(tmp_path / "prepper.sqlite3"))
    app = create_app()
    client = app.test_client()

    response = client.get("/api/metrics?window_hours=0")

    assert response.status_code == 400
    assert response.get_json() == {"error": "window_hours must be between 1 and 168"}
