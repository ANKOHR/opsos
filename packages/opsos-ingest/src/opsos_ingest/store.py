"""Thread-safe in-memory and SQLite event stores with a unique idempotency key."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol, Self

from .event import CanonicalEvent


class EventStore(Protocol):
    def get_by_idempotency_key(self, key: str) -> CanonicalEvent | None: ...

    def get_or_create(self, event: CanonicalEvent) -> tuple[CanonicalEvent, bool]: ...

    def count(self) -> int: ...


class InMemoryEventStore:
    """Useful for isolated processes and tests. Use SQLite for restart-safe deduplication."""

    def __init__(self) -> None:
        self._events: dict[str, CanonicalEvent] = {}
        self._lock = RLock()

    def get_by_idempotency_key(self, key: str) -> CanonicalEvent | None:
        with self._lock:
            return self._events.get(key)

    def get_or_create(self, event: CanonicalEvent) -> tuple[CanonicalEvent, bool]:
        with self._lock:
            existing = self._events.get(event.idempotency_key)
            if existing is not None:
                return existing, False
            self._events[event.idempotency_key] = event
            return event, True

    def count(self) -> int:
        with self._lock:
            return len(self._events)


class SQLiteEventStore:
    """SQLite event store with a unique key that survives process restarts."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        self._connection.execute("PRAGMA busy_timeout = 30000")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS canonical_events (
                id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                event_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def get_by_idempotency_key(self, key: str) -> CanonicalEvent | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT event_json FROM canonical_events WHERE idempotency_key = ?", (key,)
            ).fetchone()
        return CanonicalEvent.from_dict(json.loads(row[0])) if row else None

    def get_or_create(self, event: CanonicalEvent) -> tuple[CanonicalEvent, bool]:
        serialized = event.to_json(indent=None)
        with self._lock:
            cursor = self._connection.execute(
                "INSERT OR IGNORE INTO canonical_events (id, idempotency_key, event_json) "
                "VALUES (?, ?, ?)",
                (event.id, event.idempotency_key, serialized),
            )
            self._connection.commit()
            created = cursor.rowcount == 1
            row = self._connection.execute(
                "SELECT event_json FROM canonical_events WHERE idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
        if row is None:
            raise RuntimeError("event store could not retrieve the inserted event")
        return CanonicalEvent.from_dict(json.loads(row[0])), created

    def count(self) -> int:
        with self._lock:
            row = self._connection.execute("SELECT COUNT(*) FROM canonical_events").fetchone()
        return int(row[0])

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
