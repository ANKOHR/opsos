from pathlib import Path

import yaml
from opspilot_api.schemas import EventIngestRequest, RunStatus


def test_versioned_workflow_manifest_runs_through_existing_runtime(runtime):
    engine, _repository = runtime
    root = Path(__file__).parents[3]
    manifest = yaml.safe_load(
        (root / "packages" / "workflows" / "definitions" / "inbound-revenue.yaml").read_text(
            encoding="utf-8"
        )
    )
    run = engine.process_event(
        "demo-org",
        "fixture-operator",
        EventIngestRequest(
            event_type=manifest["trigger"],
            idempotency_key="workflow-manifest-fixture-1",
            payload={
                "from": "fixture@example.test",
                "subject": "Fixture question",
                "body": "A deterministic workflow fixture for local regression checks.",
            },
        ),
    )

    assert run["workflow_id"] == manifest["id"]
    assert run["workflow_version"] == manifest["version"]
    assert run["status"] == RunStatus.WAITING_FOR_APPROVAL
    assert any(item["event_type"] == "approval.requested" for item in run["trace"])
