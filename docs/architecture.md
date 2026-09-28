# OpsOS architecture foundation

OpsOS is under construction. This repository establishes the ingestion boundary and retains the inherited typed workflow runtime, SQLAlchemy persistence, bounded worker retries, policy and approval gates, dashboard skeleton, and versioned workflow manifests.

```text
event sources -> ingest -> runtime -> policy -> approvals -> execute -> verify
                               |          |                                |
                               +-> context+                           follow-ups
                                                                          |
                                                                          v
                                                                        audit
                                                                          |
                                                                          v
                                                                    web and demo
```

Current code locations:

- `packages/opsos-ingest/`: canonical event schema, signed receive, deduplication, transforms, in-process delivery, retries, dead letters, and JSONL logs.
- `apps/api/`: inherited typed API and workflow runtime, SQLAlchemy models, policy and approval logic.
- `apps/worker/`: inherited Dramatiq worker with bounded retries.
- `packages/workflows/`: versioned workflow YAML manifests.
- `apps/web/`: inherited Next.js dashboard skeleton.
- Context retrieval, verification, follow-up scheduling, buyer-facing dashboard work, and demo fixtures remain planned work.

This document describes repository structure and planned module boundaries. It is not evidence of customer use or an OpsOS deployment.
