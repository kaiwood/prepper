from __future__ import annotations

import os
import time
from collections.abc import MutableMapping
from typing import Any

DEFAULT_STATE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_STATE_MAX_ENTRIES = 1000
STATE_TTL_SECONDS_ENV = "PREPPER_STATE_TTL_SECONDS"
STATE_MAX_ENTRIES_ENV = "PREPPER_STATE_MAX_ENTRIES"

_STATE_CREATED_AT_KEY = "_state_created_at"
_STATE_LAST_SEEN_KEY = "_state_last_seen"


def cleanup_state_store(
    store: MutableMapping[str, MutableMapping[str, Any]],
    *,
    now: float | None = None,
    ttl_seconds: int | None = None,
    max_entries: int | None = None,
) -> set[str]:
    """Remove expired and over-limit entries from a dict-backed state store."""
    effective_now = _now(now)
    effective_ttl = ttl_seconds if ttl_seconds is not None else state_ttl_seconds()
    effective_max_entries = (
        max_entries if max_entries is not None else state_max_entries()
    )
    removed: set[str] = set()

    for key, entry in list(store.items()):
        last_seen = _entry_last_seen(entry, effective_now)
        if effective_now - last_seen > effective_ttl:
            store.pop(key, None)
            removed.add(key)

    overflow = len(store) - effective_max_entries
    if overflow > 0:
        oldest_keys = sorted(
            store,
            key=lambda key: _entry_last_seen(store[key], effective_now),
        )[:overflow]
        for key in oldest_keys:
            store.pop(key, None)
            removed.add(key)

    return removed


def cleanup_state_metadata(
    metadata: MutableMapping[str, MutableMapping[str, Any]],
    *,
    now: float | None = None,
    ttl_seconds: int | None = None,
    max_entries: int | None = None,
) -> set[str]:
    """Remove expired and over-limit IDs from metadata for non-dict state."""
    return cleanup_state_store(
        metadata,
        now=now,
        ttl_seconds=ttl_seconds,
        max_entries=max_entries,
    )


def mark_state_created(entry: MutableMapping[str, Any], *, now: float | None = None) -> None:
    timestamp = _now(now)
    entry[_STATE_CREATED_AT_KEY] = timestamp
    entry[_STATE_LAST_SEEN_KEY] = timestamp


def mark_state_seen(entry: MutableMapping[str, Any], *, now: float | None = None) -> None:
    timestamp = _now(now)
    entry.setdefault(_STATE_CREATED_AT_KEY, timestamp)
    entry[_STATE_LAST_SEEN_KEY] = timestamp


def state_timestamps(*, now: float | None = None) -> dict[str, float]:
    timestamp = _now(now)
    return {
        _STATE_CREATED_AT_KEY: timestamp,
        _STATE_LAST_SEEN_KEY: timestamp,
    }


def state_ttl_seconds() -> int:
    return _positive_int_from_env(STATE_TTL_SECONDS_ENV, DEFAULT_STATE_TTL_SECONDS)


def state_max_entries() -> int:
    return _positive_int_from_env(STATE_MAX_ENTRIES_ENV, DEFAULT_STATE_MAX_ENTRIES)


def _entry_last_seen(entry: MutableMapping[str, Any], fallback: float) -> float:
    raw_last_seen = entry.get(_STATE_LAST_SEEN_KEY, entry.get(_STATE_CREATED_AT_KEY))
    if isinstance(raw_last_seen, (int, float)):
        return float(raw_last_seen)
    return fallback


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _now(now: float | None) -> float:
    return time.time() if now is None else now
