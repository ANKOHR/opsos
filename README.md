# OpsOS

OpsOS is becoming a reliable operations system for automating business workflows with explicit policy checks, human approval, execution, verification, scheduled follow-up, and an audit trail. This repository is the foundation of a system under construction, based on the OpsPilot typed runtime and service skeleton with a new canonical ingestion package. It does not claim real-world validation, customer use, or an OpsOS deployment. Demo fixtures and the buyer dashboard are planned for later tasks.

## Architecture

The current repository keeps the inherited typed workflow runtime, SQLAlchemy models, bounded Dramatiq worker, policy and approval gates, dashboard skeleton, and versioned workflow manifests. The longer-term module layout is:

```text
Sources
  |-- Gmail
  |-- signed webhooks
  |-- fixtures and manual events
  v
ingest -> runtime -> policy -> approvals
                      |             |
                      v             v
                   context       execute
                      |             |
                      +------> verify -> follow-ups
                                  |          |
                                  +-----> audit
                                             |
                                             v
                                       web and demo
```

The current source layout maps to that direction:

```text
packages/opsos-ingest/  canonical event type and signed webhook front door
apps/api/               typed runtime, API, SQLAlchemy models and policy gates
apps/worker/            Dramatiq worker
packages/workflows/     versioned workflow YAML manifests
apps/web/               Next.js dashboard skeleton
packages/evals/         synthetic evaluation utilities inherited from OpsPilot
```

## Canonical event schema

Every new OpsOS lane uses the `CanonicalEvent` dataclass from `opsos_ingest`:

| Field | Meaning |
| --- | --- |
| `id` | Stable event identifier derived from the idempotency key. |
| `source` | One of `gmail`, `webhook`, `fixture`, or `manual`. |
| `provenance` | `source_id`, `received_at`, `transform_version`, and `raw_payload_ref`. The source ID is the original message ID or webhook ID. The raw payload reference is `sha256:` plus the SHA-256 digest of the original payload bytes. |
| `idempotency_key` | SHA-256 key derived from the pair `(source, source_id)`. |
| `payload` | Normalized JSON object for downstream modules. |
| `occurred_at` | Source occurrence time when provided, otherwise the receive time. |
| `ingested_at` | UTC time when the event was first stored. |

The store has a unique constraint on `idempotency_key`. Ingesting the same source and source ID again returns the first stored event, including its original timestamps and normalized payload. It does not create another row or dispatch another webhook delivery. Different source lanes have different keys, even when their source IDs match. SQLite storage persists this contract across restarts; the in-memory store is available for short-lived use and tests.

The receive path verifies the `X-Signature-256` HMAC-SHA256 header over the exact request bytes, parses the event, applies configurable dot-path mappings, stores one canonical event, retries in-process targets with bounded exponential backoff, sends exhausted deliveries to a dead-letter target, and appends each stage to a JSONL execution log. Invalid signatures are rejected before storage.

## Local use

Install the independent, standard-library-only ingestion package:

```powershell
python -m pip install -e .\packages\opsos-ingest
```

Ingest a local fixture and print its canonical event JSON:

```powershell
opsos-ingest --source fixture --source-id fixture-001 --payload-json '{"subject":"Fixture only"}'
```

The default event database is `.opsos/events.sqlite3`. Use `--payload-file` to read a JSON object from disk, and `--store :memory:` for a one-shot process. The signed receive API is available through `opsos_ingest.WebhookHub`; no external service is contacted by that in-process interface.

Run the local Python suite from the repository root:

```powershell
python -m pytest
```

The source tree is inherited from OpsPilot. Existing `opspilot_api` module names and the Gmail OAuth implementation are retained in this task. Historical OpsPilot deployment records do not constitute OpsOS validation.
