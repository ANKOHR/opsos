"""Command line entry point for ingesting a local fixture or event payload."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .event import EVENT_SOURCES, EventIngestor
from .store import SQLiteEventStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opsos-ingest")
    parser.add_argument("--source", choices=sorted(EVENT_SOURCES), default="fixture")
    parser.add_argument("--source-id", required=True)
    payload = parser.add_mutually_exclusive_group(required=True)
    payload.add_argument("--payload-json", help="JSON object supplied directly")
    payload.add_argument("--payload-file", type=Path, help="path to a JSON object fixture")
    parser.add_argument("--store", default=".opsos/events.sqlite3")
    parser.add_argument("--transform-version", default="fixture-identity-v1")
    parser.add_argument("--occurred-at")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        raw = (
            args.payload_file.read_bytes()
            if args.payload_file is not None
            else args.payload_json.encode("utf-8")
        )
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object")
        with SQLiteEventStore(args.store) as store:
            outcome = EventIngestor(store).ingest(
                source=args.source,
                source_id=args.source_id,
                payload=payload,
                occurred_at=args.occurred_at,
                transform_version=args.transform_version,
                raw_payload=raw,
            )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"opsos-ingest: {exc}", file=sys.stderr)
        return 2

    print(outcome.event.to_json())
    return 0
