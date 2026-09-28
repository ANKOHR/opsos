from datetime import UTC, datetime

from opsos_ingest import EventIngestor, SQLiteEventStore, idempotency_key_for


def test_same_source_payload_returns_existing_event_and_key(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    clock = lambda: datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    ingestor = EventIngestor(store, clock=clock)
    payload = {"subject": "Fixture message", "sender": {"email": "fixture@example.test"}}

    first = ingestor.ingest(
        source="fixture",
        source_id="fixture-001",
        payload=payload,
        received_at="2026-09-28T11:59:00Z",
    )
    second = ingestor.ingest(
        source="fixture",
        source_id="fixture-001",
        payload=payload,
        received_at="2026-09-28T11:59:00Z",
    )

    assert first.created is True
    assert second.created is False
    assert second.event == first.event
    assert first.event.idempotency_key == idempotency_key_for("fixture", "fixture-001")
    assert store.count() == 1
    store.close()


def test_source_identity_is_stable_across_store_reopen(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    first_store = SQLiteEventStore(path)
    first = EventIngestor(first_store).ingest(
        source="manual", source_id="operator-42", payload={"action": "review"}
    )
    first_store.close()

    second_store = SQLiteEventStore(path)
    second = EventIngestor(second_store).ingest(
        source="manual", source_id="operator-42", payload={"action": "review"}
    )
    assert second.created is False
    assert second.event.id == first.event.id
    assert second_store.count() == 1
    second_store.close()
