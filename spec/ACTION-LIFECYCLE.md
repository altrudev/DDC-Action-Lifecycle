# DDC Action Lifecycle — Reference Model

## 1. Purpose

The Action Lifecycle records consequential agent activity so that a later reviewer can distinguish:

- what was true,
- what changed in the world,
- what was observable,
- what evidence existed,
- what evidence was reachable,
- what evidence was actually consulted,
- what authority was valid,
- what decision was made,
- what was dispatched,
- what actually executed,
- what consequence followed,
- and what can or cannot be reconstructed later.

The reference representation is an append-only causal/evidence graph.

## 2. Event identity and causality

Every event MUST have a globally unique `event_id`, an immutable `event_type`, and an event-local `recorded_at`.

Where applicable, an event SHOULD also carry:

- `caused_by`: direct causal parents;
- `branch_id`: execution lineage;
- `transition_id`: the consequential transition this event belongs to;
- `evidence_horizon_id`: the evidence snapshot used for a decision;
- `authority_ref`: the authority state relied upon;
- `confidence_class`: epistemic classification.

A timestamp orders records; it does not by itself establish causality. Causal relationships MUST be represented explicitly through `caused_by`.

A world-state mutation and evidence describing that mutation MUST be separate events. Evidence is caused by, derived from, or otherwise linked to the state change it represents; the evidence record is not the state change itself.

## 3. Evidence semantics

Evidence is not represented by a single reliability score.

The model separates:

- existence,
- provenance,
- integrity,
- freshness,
- completeness,
- reachability,
- authorization,
- independence,
- corroboration,
- timeliness,
- consultation.

An item may exist without being reachable. It may be reachable without being consulted. It may be consulted while stale. These states MUST NOT be collapsed.

Each evidence item MAY carry distinct times:

- `created_at`
- `available_at`
- `reachable_at`
- `consulted_at`
- `observed_at`

Missing times remain absent or explicit unknowns; they MUST NOT be inferred merely to complete a timeline.

## 4. Evidence horizons

A decision binds to an immutable evidence horizon.

A horizon contains evidence identifiers only. Authority is a separate decision input and MUST NOT be smuggled into the horizon.

Each horizon MUST include a deterministic content digest computed from its canonical evidence-ID list. This makes accidental or retrospective mutation detectable.

Once a decision is committed:

- the horizon MUST NOT change;
- later evidence MUST NOT be inserted into it;
- later reconstruction MAY reference the old horizon;
- later evaluators MAY judge the horizon inadequate without rewriting the historical decision input.

## 5. Authority and decision binding

Authority is evaluated independently from the evidence horizon.

A consequential decision MUST bind to both:

- the exact evidence horizon used; and
- the authority state relied upon.

A retry or recovery transition MUST receive a fresh authority evaluation even when the principal identity is unchanged.

## 6. Branch semantics

Retries, recovery, reconciliation, and alternate execution paths create new branches.

A branch MUST have a stable `branch_id` and SHOULD identify its parent branch and fork event.

A later successful branch MUST NOT erase or collapse an earlier failed, partial, or divergent branch.

## 7. Epistemic classes

Claims SHOULD be labeled using one of:

- `OBSERVED`
- `DERIVED`
- `RECONSTRUCTED`
- `INFERRED`
- `COUNTERFACTUAL`
- `UNKNOWN`

A stronger class MUST NOT be assigned without corresponding evidence.

## 8. Failure and uncertainty

The lifecycle distinguishes uncertainty causes, including:

- `UNKNOWN`
- `UNOBSERVED`
- `UNAVAILABLE`
- `UNREACHABLE`
- `UNAUTHORIZED`
- `STALE`
- `CONFLICTED`
- `UNVERIFIABLE`

A run MUST NOT receive PASS solely because recovery eventually succeeded.

## 9. AL-001 invariants

The canonical AL-001 fixture MUST demonstrate:

1. H0 is immutable and content-addressed.
2. D0 remains bound to H0 and AUTH-0.
3. R0 remains bound to D0.
4. The external mutation is represented independently from E1.
5. E1 created after H0 is not inserted into H0.
6. E1 can exist before dispatch while remaining unreachable to the actor.
7. Dispatch is represented independently from execution.
8. Execution divergence is preserved and causally linked to both dispatch and changed world state.
9. Recovery creates a new branch.
10. The recovery branch receives H1 and a fresh AUTH-1 evaluation.
11. D1 binds independently to H1 and AUTH-1.
12. Original and recovery branches remain independently replayable.
13. Evidence-channel adequacy is assessed separately from actor compliance.
14. UNKNOWN is preserved where the trace cannot establish a fact.
15. Observation and consequence remain distinct.
16. Next-transition admissibility can carry unresolved remediation obligations.

## 10. AL-001 sequence

```text
T0  establish intent
T1  resolve AUTH-0
T2  capture E0 and immutable H0
T3  make D0 using H0 + AUTH-0
T4  create R0
T5  external world-state mutation A -> B
T6  create E1 describing the mutation
T7  E1 exists but is not yet reachable
T8  dispatch action committed under H0
T9  execution encounters B and diverges
T10 preserve original branch and fork recovery branch
T11 E1 becomes reachable
T12 capture H1
T13 resolve fresh AUTH-1
T14 make D1 using H1 + AUTH-1
T15 create R1 and dispatch recovery
T16 execute recovery
T17 observe resulting state
T18 record consequence
T19 replay both branches
T20 assess actor compliance and evidence-channel adequacy separately
T21 determine next-transition admissibility
```

## 11. Semantic resonance

Runtime state, trace records, receipts, replay output, human UI, machine JSON, and test expectations MUST describe the same underlying semantic event.

Presentation MAY simplify wording. It MUST NOT erase:

- UNKNOWN vs FALSE,
- dispatch vs execution,
- mutation vs evidence of mutation,
- original branch vs retry,
- historical evidence horizon vs later evidence,
- evidence availability vs reachability vs consultation,
- observed correlation vs established causation.
