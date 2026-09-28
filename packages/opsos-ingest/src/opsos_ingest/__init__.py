"""Canonical event ingestion for OpsOS."""

from .event import CanonicalEvent, EventIngestor, IngestOutcome, idempotency_key_for
from .hub import HubResult, WebhookHub
from .receive import Receiver, SignatureInvalid, SignatureMissing, sign
from .store import InMemoryEventStore, SQLiteEventStore
from .transform import MappingRule, Transform

__all__ = [
    "CanonicalEvent",
    "EventIngestor",
    "HubResult",
    "InMemoryEventStore",
    "IngestOutcome",
    "MappingRule",
    "Receiver",
    "SQLiteEventStore",
    "SignatureInvalid",
    "SignatureMissing",
    "Transform",
    "WebhookHub",
    "idempotency_key_for",
    "sign",
]
