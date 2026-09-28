# Workflow definitions

Workflow definitions are versioned, immutable inputs to the runtime. Each run stores the exact
version used, so later edits cannot rewrite history.

The API seeds the three showcase workflows from the same graph-shaped model:

- `inbound-revenue.yaml`: sales qualification and approval-gated reply
- `ap-exception.yaml`: invoice validation and exception routing
- `support-escalation.yaml`: severity classification and human routing

The demo uses deterministic adapters, but the graph contract is the same one used by real
connectors and provider-backed steps.

