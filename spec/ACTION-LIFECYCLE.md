# DDC Action Lifecycle — Reference Model

## 1. Purpose

The Action Lifecycle records consequential agent activity so that a later reviewer can distinguish:

- what was true,
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

## 2. Event identity

Every event MUST have a globally unique `event_id`, an immutable `event_type`, and an event-local `recorded_at`.

Where applicable, an event SHOULD also carry:

- `caused_by`: direct causal parents;
- `branch_id`: execution lineage;
- `transition_id`: the consequential transition this event belongs to;
- `evidence_horizon_id`: the evidence snapshot used for a decision;
- `authority_ref`: the authority state relied upon;
- `confidence_class`: epistemic classification.

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

A horizon is the set of evidence identifiers and authority references that were admissible for a decision at that transition.

Once a decision is committed:

- the horizon MUST NOT change;
- later evidence MUST NOT be inserted into it;
- later reconstruction MAY reference the old horizon;
- later evaluators MAY judge the horizon inadequate without rewriting the historical decision input.

## 5. Branch semantics

Retries, recovery, reconciliation, and alternate execution paths create new branches.

A branch MUST have a stable `branch_id` and SHOULD identify its parent branch and fork event.

A later successful branch MUST NOT erase or collapse an earlier failed, partial, or divergent branch.

## 6. Epistemic classes

Claims SHOULD be labeled using one of:

- `OBSERVED`
- `DERIVED`
- `RECONSTRUCTED`
- `INFERRED`
- `COUNTERFACTUAL`
- `UNKNOWN`

A stronger class MUST NOT be assigned without corresponding evidence.

## 7. Failure and uncertainty

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

## 8. AL-001 invariants

The canonical AL-001 fixture MUST demonstrate:

1. H0 is immutable.
2. D0 remains bound to H0.
3. R0 remains bound to D0.
4. Evidence E1 created after H0 is not inserted into H0.
5. Dispatch is represented independently from execution.
6. Execution divergence is preserved.
7. Recovery creates a new branch.
8. The recovery branch receives a new evidence horizon.
9. The retry/recovery transition receives a fresh authority/policy decision.
10. Original and recovery branches remain independently replayable.
11. Evidence-channel adequacy is assessed separately from actor compliance.
12. UNKNOWN is preserved where the trace cannot establish a fact.

## 9. AL-001 sequence

```text
T0 establish intent
T1 resolve authority
T2 capture H0
T3 make D0
T4 create R0
T5 mutate target state externally
T6 create E1 describing mutation
T7 delay E1 propagation
T8 dispatch action committed under H0
T9 execution detects divergence
T10 preserve original branch
T11 open recovery branch
T12 capture H1 including E1
T13 re-evaluate authority/policy
T14 recover, retry, or abort
T15 observe consequence
T16 replay both branches
T17 assess evidence-channel adequacy
T18 determine next-transition admissibility
```

## 10. Semantic resonance

Runtime state, trace records, receipts, replay output, human UI, machine JSON, and test expectations MUST describe the same underlying semantic event.

Presentation MAY simplify wording. It MUST NOT erase:

- UNKNOWN vs FALSE,
- dispatch vs execution,
- original branch vs retry,
- historical evidence horizon vs later evidence,
- observed correlation vs established causation.
