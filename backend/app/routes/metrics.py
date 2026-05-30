from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin

from app import limiter
from prepper_cli.metrics import get_metrics_snapshot

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/api/metrics", methods=["OPTIONS"])
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def metrics_options():
    return "", 204


@metrics_bp.get("/api/metrics")
@limiter.limit("30 per minute")
@cross_origin(
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization"],
)
def metrics():
    try:
        window_hours = _int_query("window_hours", default=24, minimum=1, maximum=168)
        recent_limit = _int_query("recent_limit", default=30, minimum=0, maximum=100)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        get_metrics_snapshot(
            window_hours=window_hours,
            recent_limit=recent_limit,
        )
    )


def _int_query(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value
