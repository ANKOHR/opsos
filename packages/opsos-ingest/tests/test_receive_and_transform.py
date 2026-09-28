import hashlib
import json

import pytest
from opsos_ingest import MappingRule, Receiver, SignatureInvalid, Transform, WebhookHub
from opsos_ingest.receive import sign

SECRET = "test-secret"


def request_body(event_id="webhook-001"):
    return json.dumps(
        {
            "event_id": event_id,
            "occurred_at": "2026-09-28T11:30:00Z",
            "data": {"customer": {"email": "fixture@example.test"}, "subject": "Help"},
        },
        sort_keys=True,
    ).encode()


def headers(raw_body):
    return {"X-Signature-256": sign(SECRET, raw_body)}


def test_receiver_accepts_valid_hmac_and_rejects_invalid_hmac():
    raw_body = request_body()
    event = Receiver(SECRET).receive(raw_body, headers(raw_body))
    assert event.event_id == "webhook-001"

    with pytest.raises(SignatureInvalid):
        Receiver(SECRET).receive(raw_body, {"X-Signature-256": "sha256=" + ("0" * 64)})


def test_dot_path_transform_builds_canonical_event_with_provenance():
    raw_body = request_body()
    hub = WebhookHub(
        SECRET,
        [
            MappingRule("data.customer.email", "customer.email"),
            MappingRule("data.subject", "subject"),
            MappingRule("occurred_at", "occurred_at"),
        ],
        transform_version="webhook-v3",
    )
    result = hub.handle(raw_body, headers(raw_body))

    assert result.status == "stored"
    assert result.event is not None
    assert result.event.payload == {
        "customer": {"email": "fixture@example.test"},
        "occurred_at": "2026-09-28T11:30:00Z",
        "subject": "Help",
    }
    assert result.event.provenance["source_id"] == "webhook-001"
    assert result.event.provenance["received_at"]
    assert result.event.provenance["transform_version"] == "webhook-v3"
    assert (
        result.event.provenance["raw_payload_ref"]
        == "sha256:" + hashlib.sha256(raw_body).hexdigest()
    )


def test_transform_writes_nested_paths_and_constants():
    mapped = Transform(
        [MappingRule("data.customer.email", "customer.email")], {"source": "webhook"}
    ).apply({"data": {"customer": {"email": "fixture@example.test"}}})
    assert mapped == {"customer": {"email": "fixture@example.test"}, "source": "webhook"}
