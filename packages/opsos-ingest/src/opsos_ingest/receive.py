"""Webhook JSON receive and HMAC-SHA256 signature validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


class SignatureMissing(ValueError):
    """Raised when the signature header is absent."""


class SignatureInvalid(ValueError):
    """Raised when the signature is malformed or does not match."""


class InvalidPayload(ValueError):
    """Raised when the request body is not a JSON object."""


class MissingEventId(ValueError):
    """Raised when a JSON payload does not contain a usable event id."""


@dataclass(frozen=True)
class WebhookEvent:
    event_id: str
    payload: dict[str, Any]
    received_at: str
    source: str | None = None


_SIGNATURE_PATTERN = re.compile(r"sha256=[0-9a-fA-F]{64}\Z")


def sign(secret: str | bytes, body: bytes) -> str:
    """Return the X-Signature-256 value for the exact request bytes."""

    secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
    digest = hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _header(headers: dict[str, Any], name: str) -> Any:
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return value
    return None


class Receiver:
    def __init__(self, secret: str | bytes, clock: Any = None):
        self.secret = secret
        self.clock = clock or (lambda: datetime.now(UTC))

    def receive(self, raw_body: bytes, headers: dict[str, Any]) -> WebhookEvent:
        supplied = _header(headers, "X-Signature-256")
        if supplied is None:
            raise SignatureMissing("X-Signature-256 header is required")
        if not isinstance(supplied, str) or not _SIGNATURE_PATTERN.fullmatch(supplied):
            raise SignatureInvalid("signature must use sha256=<64 hex characters>")

        expected = sign(self.secret, raw_body)
        if not hmac.compare_digest(expected.lower(), supplied.lower()):
            raise SignatureInvalid("signature does not match request body")

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise InvalidPayload("request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise InvalidPayload("request JSON must be an object")

        raw_event_id = payload.get("event_id")
        if raw_event_id is None or str(raw_event_id).strip() == "":
            raise MissingEventId("payload must include event_id")
        source = _header(headers, "X-Webhook-Source")
        received_at = self.clock()
        if isinstance(received_at, datetime):
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=UTC)
            received_at = (
                received_at.astimezone(UTC)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            )
        return WebhookEvent(
            event_id=str(raw_event_id),
            payload=payload,
            received_at=str(received_at),
            source=str(source) if source is not None else None,
        )
