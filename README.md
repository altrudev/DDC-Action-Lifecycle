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

Internally, the reference model is an append-only causal/evidence graph. The lifecycle above is a projection over that graph.

## Frequency integration

The v0.2 architecture adds a live action-state layer without discarding AL-001:

- `ActionIR` — canonical semantic representation of an action
- `FrequencyDelta` — dimension-by-dimension change between action-field states
- `TransitionGate` — explicit decision boundary between consequential phases
- semantic resonance — multidimensional meaning-drift detection
- runtime context — infrastructure state kept separate from action validity
- recoverability — rollback/restore readiness as a first-class dimension
- artifact lineage and admissible next-transition trajectories
- compatibility path for future FQPK/FQPX representations

See `spec/FREQUENCY-ACTION-LIFECYCLE-v0.2.md`.

Core rules:

1. A later phase may reference an earlier evidence state, but it may never mutate it.
2. Each consequential transition earns its own authority and evidence decision.
3. Dispatch does not prove execution; observation does not prove causation.
4. Retries and recovery paths are distinct branches, not edits to prior history.
5. Evidence existence, reachability, freshness, authorization, trustworthiness, and consultation remain separate facts.
6. World-state changes and evidence about those changes are distinct events.
7. Unknown or unavailable evidence remains explicit; it is never converted into fabricated certainty.
8. Evidence horizons are content-addressed so accidental or retrospective mutation is detectable.
9. Semantic meaning and structural binding are checked independently.
10. Runtime degradation remains distinct from action invalidity.

## Canonical fixtures

### AL-001 — Mid-Run State Mutation and Evidence-Latency Recovery

AL-001 changes target state after the original decision, records that mutation independently from evidence about it, delays propagation of the new evidence, allows the committed action to reach execution, then verifies that recovery opens a new branch without rewriting the original decision horizon.

### AL-001 v0.2 projection

The v0.2 projection expresses the same scenario through ActionIR + FrequencyDelta + TransitionGate and demonstrates that semantic identity can remain resonant while temporal conditions still require a recheck.

See:

- `spec/ACTION-LIFECYCLE.md`
- `spec/FREQUENCY-ACTION-LIFECYCLE-v0.2.md`
- `schema/action-lifecycle-event.schema.json`
- `schema/action-ir.schema.json`
- `schema/frequency-delta.schema.json`
- `schema/transition-gate.schema.json`
- `fixtures/al-001-mid-run-mutation.json`
- `fixtures/al-001-v02-action-ir.json`
- `tests/test_al001.py`
- `tests/test_v02_architecture.py`

The broader DDC architecture is designed and developed by **Valentyn Rukhaylo / Altru.dev**.

Status: AL-001 implemented; Frequency-integrated v0.2 architecture under conformance development.
