"""Signed webhook front door coordinating canonical storage and target delivery."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from .delivery import DeadLetter, DeadLetterQueue, Deliverer, DeliveryResult
from .event import CanonicalEvent, EventIngestor, idempotency_key_for
from .log import ExecutionLog
from .receive import InvalidPayload, MissingEventId, Receiver, SignatureInvalid, SignatureMissing
from .store import EventStore, InMemoryEventStore
from .transform import MappingRule, MissingField, Transform


def _event_id_hint(raw_body: bytes) -> str:
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return "<unknown>"
    if isinstance(payload, dict) and payload.get("event_id") is not None:
        candidate = str(payload["event_id"])
        if candidate.strip():
            return candidate
    return "<unknown>"


@dataclass(frozen=True)
class HubResult:
    event_id: str
    status: str
    event: CanonicalEvent | None = None
    deliveries: tuple[DeliveryResult, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "status": self.status,
            "event": self.event.to_dict() if self.event else None,
            "deliveries": [asdict(item) for item in self.deliveries],
            "reason": self.reason,
        }


class WebhookHub:
    """Receive signed webhook bytes and run dedup, transform, retry, and logging."""

    def __init__(
        self,
        secret: str | bytes,
        transform_rules: list[MappingRule],
        constants: dict[str, Any] | None = None,
        deliverer_config: dict[str, Any] | None = None,
        dedup: EventStore | None = None,
        log: ExecutionLog | None = None,
        dead_letter_target: Callable[[DeadLetter], Any] | None = None,
        transform_version: str = "webhookhub-dotpath-v1",
        clock: Callable[[], Any] | None = None,
    ):
        self.receiver = Receiver(secret, clock=clock)
        self.transformer = Transform(transform_rules, constants)
        self.store = dedup or InMemoryEventStore()
        self.ingestor = EventIngestor(self.store, clock=clock)
        self.deliverer = Deliverer(**(deliverer_config or {}))
        self.log = log or ExecutionLog()
        self.transform_version = transform_version
        self.dead_letters = DeadLetterQueue()
        self.dead_letter_target = dead_letter_target or self.dead_letters.put

    def register_target(self, name: str, fn: Callable[[CanonicalEvent], bool]) -> None:
        self.deliverer.register_target(name, fn)

    def handle(self, raw_body: bytes, headers: dict[str, Any]) -> HubResult:
        hinted_id = _event_id_hint(raw_body)
        self.log.append(hinted_id, "receive", "ok", f"received {len(raw_body)} bytes")
        try:
            received = self.receiver.receive(raw_body, headers)
        except (InvalidPayload, MissingEventId, SignatureInvalid, SignatureMissing) as exc:
            reason = str(exc) or type(exc).__name__
            self.log.append(hinted_id, "validate", "error", f"{type(exc).__name__}: {reason}")
            return HubResult(hinted_id, "rejected", reason=reason)

        event_id = received.event_id
        self.log.append(event_id, "validate", "ok", "signature and payload accepted")
        key = idempotency_key_for("webhook", event_id)
        existing = self.store.get_by_idempotency_key(key)
        if existing is not None:
            self.log.append(event_id, "dedup", "skipped", "event id already processed")
            return HubResult(event_id, "duplicate", event=existing)

        try:
            normalized = self.transformer.apply(received.payload)
        except (MissingField, TypeError, ValueError) as exc:
            reason = str(exc) or type(exc).__name__
            self.log.append(event_id, "transform", "error", f"{type(exc).__name__}: {reason}")
            return HubResult(event_id, "rejected", reason=reason)

        self.log.append(
            event_id,
            "transform",
            "ok",
            f"mapped {len(normalized)} top-level fields",
        )
        try:
            outcome = self.ingestor.ingest(
                source="webhook",
                source_id=event_id,
                payload=received.payload,
                received_at=received.received_at,
                occurred_at=normalized.get("occurred_at", received.received_at),
                transform_version=self.transform_version,
                raw_payload=raw_body,
                transform=lambda _source: normalized,
            )
        except (sqlite3.Error, TypeError, ValueError) as exc:
            reason = str(exc) or type(exc).__name__
            self.log.append(event_id, "ingest", "error", f"{type(exc).__name__}: {reason}")
            return HubResult(event_id, "rejected", reason=reason)

        event = outcome.event
        if outcome.duplicate:
            self.log.append(event_id, "dedup", "skipped", "event id already processed")
            return HubResult(event_id, "duplicate", event=event)
        self.log.append(event_id, "dedup", "ok", "event id stored once")

        results: list[DeliveryResult] = []
        for target_name in self.deliverer.targets:
            result = self.deliverer.deliver_to(target_name, event)
            results.append(result)
            for attempt_no, _outcome, delay in result.attempt_log:
                if delay is not None:
                    self.log.append(
                        event_id,
                        "retry",
                        "ok",
                        f"target={target_name} attempt={attempt_no} delay={delay:g}s",
                    )
            self.log.append(
                event_id,
                "deliver",
                "ok" if result.delivered else "error",
                f"target={target_name} attempts={result.attempts}",
            )
            if result.dead_lettered:
                dead_letter = DeadLetter(
                    event=event,
                    target=target_name,
                    attempts=result.attempts,
                    reason=result.reason or "delivery failed",
                )
                try:
                    self.dead_letter_target(dead_letter)
                    self.log.append(
                        event_id, "dead_letter", "ok", f"target={target_name}: {dead_letter.reason}"
                    )
                except Exception as exc:  # noqa: BLE001
                    self.log.append(
                        event_id,
                        "dead_letter",
                        "error",
                        f"target={target_name}: {type(exc).__name__}: {exc}",
                    )

        delivered = sum(1 for result in results if result.delivered)
        if not results:
            status = "stored"
        elif delivered == len(results):
            status = "delivered"
        elif delivered:
            status = "partially_delivered"
        else:
            status = "dead_lettered"
        return HubResult(event_id, status, event=event, deliveries=tuple(results))
