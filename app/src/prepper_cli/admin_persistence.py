from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SQLITE_ENV_VAR = "PREPPER_SQLITE_PATH"
_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class AdminHrSetupRecord:
    id: int
    created_at: str
    setup_fields: dict[str, str]
    context_id: str | None
    response_payload: dict[str, Any]
    context_payload: dict[str, Any] | None


def default_sqlite_path() -> Path:
    configured = os.getenv(DEFAULT_SQLITE_ENV_VAR)
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / ".prepper" / "prepper.sqlite3"


def save_admin_hr_setup(
    *,
    setup_fields: dict[str, str | None],
    response_payload: dict[str, Any],
    context_payload: dict[str, Any] | None,
    db_path: Path | str | None = None,
) -> AdminHrSetupRecord:
    path = Path(db_path).expanduser() if db_path is not None else default_sqlite_path()
    normalized_setup = _normalize_setup_fields(setup_fields)
    context_id = None
    if context_payload is not None:
        raw_context_id = context_payload.get("context_id")
        context_id = raw_context_id if isinstance(raw_context_id, str) else None
    if context_id is None:
        raw_context_id = response_payload.get("context_id")
        context_id = raw_context_id if isinstance(raw_context_id, str) else None

    with _connect(path) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO admin_hr_setups (
                company_url,
                company_text,
                role_description,
                role_url,
                resume_text,
                profile_text,
                context_id,
                response_json,
                context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_setup["company_url"],
                normalized_setup["company_text"],
                normalized_setup["role_description"],
                normalized_setup["role_url"],
                normalized_setup["resume_text"],
                normalized_setup["profile_text"],
                context_id,
                json.dumps(response_payload, sort_keys=True),
                json.dumps(context_payload, sort_keys=True) if context_payload is not None else None,
            ),
        )
        record_id = int(cursor.lastrowid)
        conn.commit()
        row = conn.execute(
            "SELECT * FROM admin_hr_setups WHERE id = ?",
            (record_id,),
        ).fetchone()
    if row is None:  # pragma: no cover - sqlite should return inserted row
        raise RuntimeError("Saved admin HR setup could not be loaded")
    return _row_to_record(row)


def load_latest_admin_hr_setup(
    *, db_path: Path | str | None = None
) -> AdminHrSetupRecord | None:
    path = Path(db_path).expanduser() if db_path is not None else default_sqlite_path()
    if not path.exists():
        return None
    with _connect(path) as conn:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT * FROM admin_hr_setups ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_hr_schema (
            version INTEGER PRIMARY KEY
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_hr_setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            company_url TEXT NOT NULL DEFAULT '',
            company_text TEXT NOT NULL DEFAULT '',
            role_description TEXT NOT NULL DEFAULT '',
            role_url TEXT NOT NULL DEFAULT '',
            resume_text TEXT NOT NULL DEFAULT '',
            profile_text TEXT NOT NULL DEFAULT '',
            context_id TEXT,
            response_json TEXT NOT NULL,
            context_json TEXT
        )
        """
    )
    _ensure_column(conn, "admin_hr_setups", "role_url", "TEXT NOT NULL DEFAULT ''")
    conn.execute(
        "INSERT OR IGNORE INTO admin_hr_schema (version) VALUES (?)",
        (_SCHEMA_VERSION,),
    )



def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")



def _normalize_setup_fields(setup_fields: dict[str, str | None]) -> dict[str, str]:
    return {
        "company_url": _normalize_string(setup_fields.get("company_url")),
        "company_text": _normalize_string(setup_fields.get("company_text")),
        "role_description": _normalize_string(setup_fields.get("role_description")),
        "role_url": _normalize_string(setup_fields.get("role_url")),
        "resume_text": _normalize_string(setup_fields.get("resume_text")),
        "profile_text": _normalize_string(setup_fields.get("profile_text")),
    }


def _normalize_string(value: str | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def _row_to_record(row: sqlite3.Row) -> AdminHrSetupRecord:
    context_json = row["context_json"]
    return AdminHrSetupRecord(
        id=int(row["id"]),
        created_at=str(row["created_at"]),
        setup_fields={
            "company_url": str(row["company_url"]),
            "company_text": str(row["company_text"]),
            "role_description": str(row["role_description"]),
            "role_url": str(row["role_url"]),
            "resume_text": str(row["resume_text"]),
            "profile_text": str(row["profile_text"]),
        },
        context_id=row["context_id"] if row["context_id"] is not None else None,
        response_payload=json.loads(str(row["response_json"])),
        context_payload=json.loads(str(context_json)) if context_json is not None else None,
    )
