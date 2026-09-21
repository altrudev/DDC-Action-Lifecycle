# DDC Action Lifecycle

**A continuous, evidence-bound lifecycle for consequential agent actions.**

DDC Action Lifecycle connects decision-time assurance, signed action commitments, execution evidence, downstream observations, and forensic reconstruction without allowing later knowledge to rewrite what was knowable earlier.

This repository is the integration layer for the lifecycle:

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

Core rule:

> A later phase may reference an earlier evidence state, but it may never mutate it.

The broader DDC architecture is designed and developed by **Valentyn Rukhaylo / Altru.dev**.

Status: early reference implementation.
