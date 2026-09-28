import json
import threading
from concurrent.futures import ThreadPoolExecutor

from opsos_ingest import MappingRule, SQLiteEventStore, WebhookHub
from opsos_ingest.log import ExecutionLog
from opsos_ingest.receive import sign

SECRET = "storm-secret"


def signed_request(event_id="storm-1"):
    raw_body = json.dumps({"event_id": event_id, "data": {"value": 7}}, sort_keys=True).encode()
    return raw_body, {"x-signature-256": sign(SECRET, raw_body)}


def test_failed_target_retries_with_backoff_and_reaches_dead_letter(tmp_path):
    delays = []
    log_path = tmp_path / "execution.jsonl"
    hub = WebhookHub(
        SECRET,
        [MappingRule("data.value", "value")],
        deliverer_config={
            "max_attempts": 3,
            "base_delay": 0.25,
            "backoff_factor": 2,
            "sleep": delays.append,
        },
        log=ExecutionLog(log_path),
    )
    hub.register_target("unavailable", lambda _event: False)
    raw_body, signed_headers = signed_request("retry-1")

    result = hub.handle(raw_body, signed_headers)

    assert result.status == "dead_lettered"
    assert result.deliveries[0].attempts == 3
    assert delays == [0.25, 0.5]
    assert len(hub.dead_letters.items) == 1
    assert hub.dead_letters.items[0].event.id == result.event.id
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert any(row["stage"] == "retry" for row in rows)
    assert any(row["stage"] == "dead_letter" and row["outcome"] == "ok" for row in rows)


def test_duplicate_delivery_storm_stores_and_dispatches_once(tmp_path):
    store = SQLiteEventStore(tmp_path / "storm.sqlite3")
    hub = WebhookHub(
        SECRET,
        [MappingRule("data.value", "value")],
        dedup=store,
        deliverer_config={"sleep": lambda _delay: None},
    )
    received = 0
    received_lock = threading.Lock()

    def target(_event):
        nonlocal received
        with received_lock:
            received += 1
        return True

    hub.register_target("collector", target)
    raw_body, signed_headers = signed_request("storm-same-id")

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _index: hub.handle(raw_body, signed_headers), range(48)))

    assert store.count() == 1
    assert sum(1 for result in results if result.status == "delivered") == 1
    assert sum(1 for result in results if result.status == "duplicate") == 47
    assert received == 1
    store.close()


def test_invalid_signature_is_rejected_without_storing_event():
    store = SQLiteEventStore(":memory:")
    hub = WebhookHub(SECRET, [MappingRule("data.value", "value")], dedup=store)
    raw_body, _signed_headers = signed_request("bad-signature")

    result = hub.handle(raw_body, {"X-Signature-256": "sha256=" + ("f" * 64)})

    assert result.status == "rejected"
    assert store.count() == 0
    store.close()
