import json

from opsos_ingest.cli import main


def test_cli_ingests_fixture_and_prints_canonical_event(capsys):
    exit_code = main(
        [
            "--source",
            "fixture",
            "--source-id",
            "cli-fixture-1",
            "--payload-json",
            '{"subject":"Fixture only","from":"fixture@example.test"}',
            "--store",
            ":memory:",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    event = json.loads(captured.out)
    assert event["source"] == "fixture"
    assert event["provenance"]["source_id"] == "cli-fixture-1"
    assert event["payload"]["subject"] == "Fixture only"
