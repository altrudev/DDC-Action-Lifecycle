# DDC Action Lifecycle

**A continuous, evidence-bound lifecycle for consequential agent actions.**

DDC Action Lifecycle connects decision-time assurance, signed action commitments, execution evidence, downstream observations, recovery, and forensic reconstruction without allowing later knowledge to rewrite what was knowable earlier.

The human-facing lifecycle projection is:

```text
Intent
  ↓
Authority
  ↓
Evidence Horizon
  ↓
Decision
  ↓
Action Receipt
  ↓
Dispatch
  ↓
Execution
  ↓
Observation
  ↓
Consequence
  ↓
Replay / Reconstruction
  ↓
Next-transition admissibility
```

Internally, the reference model is **not a mutable linear log**. It is an append-only causal/evidence graph. The linear lifecycle above is a projection over that graph.

Core rules:

1. A later phase may reference an earlier evidence state, but it may never mutate it.
2. Each consequential transition earns its own authority and evidence decision.
3. Dispatch does not prove execution; observation does not prove causation.
4. Retries and recovery paths are distinct branches, not edits to prior history.
5. Evidence existence, reachability, freshness, authorization, trustworthiness, and consultation remain separate facts.
6. Unknown or unavailable evidence remains explicit; it is never converted into fabricated certainty.

## First canonical fixture

`AL-001 — Mid-Run State Mutation and Evidence-Latency Recovery`

AL-001 intentionally changes target state after the original decision, delays propagation of the new evidence, allows the committed action to reach execution, then verifies that recovery opens a new branch without rewriting the original decision horizon.

See:

- `spec/ACTION-LIFECYCLE.md`
- `schema/action-lifecycle-event.schema.json`
- `fixtures/al-001-mid-run-mutation.json`
- `tests/test_al001.py`

The broader DDC architecture is designed and developed by **Valentyn Rukhaylo / Altru.dev**.

Status: executable reference fixture under construction.
