"""Canonical event type and deterministic event construction."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

EVENT_SOURCES = frozenset({"gmail", "webhook", "fixture", "manual"})
_EVENT_NAMESPACE = uuid.UUID("d977d087-919d-46f4-8485-dc83b772b3a0")
_PROVENANCE_FIELDS = frozenset({"source_id", "received_at", "transform_version", "raw_payload_ref"})


def canonical_json(value: Any) -> str:
    """Serialize JSON data consistently so hashes and stored events are repeatable."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("event data must contain only finite JSON values") from exc


def utc_timestamp(value: str | datetime | None = None) -> str:
    """Return a normalized UTC timestamp with a Z suffix."""

    if value is None:
        parsed = datetime.now(UTC)
    elif isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"invalid ISO 8601 timestamp: {value}") from exc
    else:
        raise TypeError("timestamps must be ISO 8601 strings or datetime values")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def idempotency_key_for(source: str, source_id: str) -> str:
    """Hash the stable source lane and source identifier into an idempotency key."""

    if source not in EVENT_SOURCES:
        raise ValueError(f"source must be one of: {', '.join(sorted(EVENT_SOURCES))}")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be a non-empty string")
    identity = canonical_json({"source": source, "source_id": source_id})
    return "sha256:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _event_id_for(key: str) -> str:
    return "evt_" + uuid.uuid5(_EVENT_NAMESPACE, key).hex


def _json_object(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a JSON object")
    result = json.loads(canonical_json(dict(value)))
    if not isinstance(result, dict):
        raise TypeError(f"{label} must be a JSON object")
    return result


@dataclass(frozen=True)
class CanonicalEvent:
    """The shared OpsOS event envelope used by every later module."""

    id: str
    source: str
    provenance: dict[str, str]
    idempotency_key: str
    payload: dict[str, Any]
    occurred_at: str
    ingested_at: str

    def __post_init__(self) -> None:
        if self.source not in EVENT_SOURCES:
            raise ValueError(f"source must be one of: {', '.join(sorted(EVENT_SOURCES))}")
        if not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be an object")
        provenance = {str(key): str(value) for key, value in self.provenance.items()}
        missing = _PROVENANCE_FIELDS.difference(provenance)
        if missing:
            raise ValueError(f"provenance is missing: {', '.join(sorted(missing))}")
        if not all(provenance[field].strip() for field in _PROVENANCE_FIELDS):
            raise ValueError("provenance values must be non-empty strings")
        provenance["received_at"] = utc_timestamp(provenance["received_at"])
        expected_key = idempotency_key_for(self.source, provenance["source_id"])
        if self.idempotency_key != expected_key:
            raise ValueError("idempotency_key does not match source and provenance source_id")
        if self.id != _event_id_for(expected_key):
            raise ValueError("id does not match the deterministic idempotency key")
        raw_ref = provenance["raw_payload_ref"]
        if len(raw_ref) != 71 or not raw_ref.startswith("sha256:"):
            raise ValueError("raw_payload_ref must be sha256 followed by 64 hexadecimal digits")
        try:
            int(raw_ref[7:], 16)
        except ValueError as exc:
            raise ValueError("raw_payload_ref must contain a hexadecimal SHA-256 digest") from exc

        object.__setattr__(self, "provenance", deepcopy(provenance))
        object.__setattr__(self, "payload", _json_object(self.payload, "payload"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at))
        object.__setattr__(self, "ingested_at", utc_timestamp(self.ingested_at))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "provenance": deepcopy(self.provenance),
            "idempotency_key": self.idempotency_key,
            "payload": deepcopy(self.payload),
            "occurred_at": self.occurred_at,
            "ingested_at": self.ingested_at,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=False, allow_nan=False, sort_keys=True, indent=indent
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CanonicalEvent:
        return cls(
            id=value["id"],
            source=value["source"],
            provenance=value["provenance"],
            idempotency_key=value["idempotency_key"],
            payload=value["payload"],
            occurred_at=value["occurred_at"],
            ingested_at=value["ingested_at"],
        )


@dataclass(frozen=True)
class IngestOutcome:
    """An event plus whether this call inserted it into the event store."""

    event: CanonicalEvent
    created: bool

    @property
    def duplicate(self) -> bool:
        return not self.created


class EventIngestor:
    """Normalize source payloads and store one canonical event per source identity."""

    def __init__(self, store: Any, clock: Callable[[], datetime] | None = None):
        self.store = store
        self.clock = clock or (lambda: datetime.now(UTC))

    def build_event(
        self,
        *,
        source: str,
        source_id: str,
        payload: Mapping[str, Any],
        received_at: str | datetime | None = None,
        occurred_at: str | datetime | None = None,
        transform_version: str = "identity-v1",
        raw_payload: bytes | str | None = None,
        transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> CanonicalEvent:
        source_payload = _json_object(payload, "payload")
        normalized = transform(deepcopy(source_payload)) if transform else source_payload
        normalized = _json_object(normalized, "normalized payload")
        if raw_payload is None:
            raw_bytes = canonical_json(source_payload).encode("utf-8")
        elif isinstance(raw_payload, str):
            raw_bytes = raw_payload.encode("utf-8")
        elif isinstance(raw_payload, bytes):
            raw_bytes = raw_payload
        else:
            raise TypeError("raw_payload must be bytes, text, or omitted")

        key = idempotency_key_for(source, source_id)
        received = utc_timestamp(received_at if received_at is not None else self.clock())
        source_occurred = occurred_at or normalized.get("occurred_at") or received
        return CanonicalEvent(
            id=_event_id_for(key),
            source=source,
            provenance={
                "source_id": source_id,
                "received_at": received,
                "transform_version": transform_version,
                "raw_payload_ref": "sha256:" + hashlib.sha256(raw_bytes).hexdigest(),
            },
            idempotency_key=key,
            payload=normalized,
            occurred_at=utc_timestamp(source_occurred),
            ingested_at=utc_timestamp(self.clock()),
        )

    def ingest(self, **kwargs: Any) -> IngestOutcome:
        event = self.build_event(**kwargs)
        stored, created = self.store.get_or_create(event)
        return IngestOutcome(event=stored, created=created)
