# DDC Action Lifecycle v0.2 — Frequency Integration

## Status

This document defines the next architecture layer above AL-001. It does not replace the original lifecycle projection. It makes the runtime model explicit enough to support continuous state change, semantic drift detection, transition gating, artifact provenance, recovery, and replay.

## 1. Architectural shift

DDC Action Lifecycle v0.1 answers:

- what happened,
- what was authorized,
- what evidence existed,
- what executed,
- and what can be reconstructed.

v0.2 additionally models:

- what is happening now,
- which dimensions of the action field changed,
- whether those changes are consequential,
- whether semantic meaning still resonates across representations,
- whether another transition remains admissible,
- and whether recovery or re-authorization is required.

The lifecycle is therefore treated as a projection over a live causal graph, not as a single mutable status record.

## 2. ActionIR

`ActionIR` is the canonical semantic representation of a consequential action.

Required dimensions:

- identity
- intent
- target
- parameters
- authority
- evidence horizon
- policy
- environment
- dependencies
- branch
- transition
- expected effect
- actual effect
- uncertainty
- provenance
- runtime context
- recoverability

JSON, receipts, replay views, UI projections, FQPK/FQPX, and future transport formats are representations of this IR.

Core invariant:

```text
decode(encode(ActionIR)) == ActionIR
```

A representation may omit presentation detail, but it must not change semantic identity.

## 3. Action Field

An action is evaluated within a time-varying Action Field.

```text
ActionField(t) = {
  action,
  authority,
  evidence,
  world_state,
  environment,
  dependencies,
  policy,
  tools,
  runtime_context,
  recoverability
}
```

A change in the field does not automatically invalidate the action. It produces a `FrequencyDelta`, which is then classified for transition impact.

## 4. FrequencyDelta

`FrequencyDelta` is the normalized difference between two action-field snapshots.

It records changes independently across dimensions such as:

- target state
- authority
- evidence
- policy
- dependency state
- environment
- tool availability
- runtime health
- recoverability
- semantic meaning

A delta has an impact classification:

- `NONE`
- `NON_CONSEQUENTIAL`
- `RECHECK_REQUIRED`
- `REAUTHORIZE_REQUIRED`
- `RECOVERY_REQUIRED`
- `HOLD_UNKNOWN`

The classification is a decision result, not an intrinsic property of the raw delta.

## 5. TransitionGate

A `TransitionGate` sits between consequential lifecycle stages.

Canonical gates:

- decision -> receipt
- receipt -> dispatch
- dispatch -> execution
- execution -> consequence
- consequence -> next transition

A gate evaluates:

- current ActionIR
- current evidence horizon
- current authority state
- FrequencyDelta since the previous gate
- semantic resonance
- runtime context
- recoverability

Possible outcomes:

- `CONTINUE`
- `RECHECK`
- `REAUTHORIZE`
- `RECOVER`
- `WAIT`
- `ABORT`
- `UNKNOWN`

A gate must not silently mutate the prior decision. If re-evaluation is required, a new transition or branch is created.

## 6. SemanticResonance

Structural binding is necessary but not sufficient.

Semantic resonance checks whether successive lifecycle representations still refer to the same consequential action.

Independent resonance dimensions include:

- identity
- target
- parameter
- authority
- temporal
- policy
- dependency
- effect

Resonance outcomes:

- `RESONANT`
- `DRIFTED`
- `UNKNOWN`

A single scalar similarity score is not sufficient for conformance.

## 7. Horizon evolution

Evidence horizons remain immutable and content-addressed.

Long-running actions may use a sequence:

```text
H0 -> H1 -> H2 -> ...
```

Different lifecycle boundaries may therefore bind to different horizons:

- decision horizon
- dispatch horizon
- execution horizon
- observation horizon

Later horizons do not replace earlier ones.

## 8. RuntimeContext

Runtime conditions are modeled separately from action validity.

Examples:

- CPU pressure
- memory pressure
- disk pressure
- queue delay
- worker availability
- network health
- clock drift
- storage integrity
- backup freshness
- dependency health

This allows the lifecycle to distinguish:

```text
action invalid
```

from:

```text
action valid, infrastructure inadequate
```

## 9. RecoverabilityState

Recoverability is a first-class action dimension.

It may include:

- pre-state captured
- rollback available
- backup current
- restoration path known
- restoration tested
- restore dependencies reachable

Consequential actions may require a minimum recoverability state before a transition gate allows execution.

## 10. Artifact lineage

Actions may produce artifacts, and artifacts may become evidence or inputs to later actions.

```text
Action -> Artifact -> Evidence -> Decision -> Action
```

Artifact references should capture:

- artifact identity
- digest
- producer action/transition
- creation time
- mutation lineage
- branch
- provenance

A later artifact mutation must not retroactively alter the artifact identity used by an earlier decision.

## 11. Waiting and dormant states

The lifecycle supports explicit waiting states:

- `WAITING_FOR_EVIDENCE`
- `WAITING_FOR_AUTHORITY`
- `WAITING_FOR_DEPENDENCY`
- `WAITING_FOR_HUMAN`
- `WAITING_FOR_REMOTE_EXECUTOR`
- `WAITING_FOR_TIME`
- `WAITING_FOR_EXTERNAL_STATE`

Waiting is a state with provenance, not absence of activity.

## 12. Lifecycle heartbeat

Long-running actions may emit compact heartbeats without rewriting history.

Heartbeat states include:

- `ALIVE`
- `STALLED`
- `WAITING`
- `DEGRADED`
- `DIVERGENT`
- `RECOVERING`

A heartbeat is observational runtime context, not a replacement for lifecycle events.

## 13. Admissible trajectories

The runtime may expose the currently admissible next transitions.

Example:

```text
current transition
  |- continue
  |- retry
  |- recover
  |- abort
  |- ask human
  `- wait for evidence
```

This is not outcome prediction. It is an explicit representation of transitions currently permitted by policy, evidence, authority, and runtime state.

## 14. FQPK / FQPX compatibility

FQPK and FQPX are not mandatory in v0.2.

The architecture should, however, allow them to become compact and expanded transport representations of ActionIR without changing ActionIR semantics.

Any future codec must satisfy round-trip and semantic-resonance tests before becoming normative.

## 15. v0.2 invariants

1. ActionIR is the canonical semantic representation.
2. Lifecycle views are projections, not independent sources of truth.
3. FrequencyDelta records dimension changes without deciding their policy effect.
4. TransitionGate decisions never rewrite prior horizons or decisions.
5. Semantic resonance is multidimensional.
6. Runtime degradation remains distinct from action invalidity.
7. Recoverability is explicit before destructive or irreversible transitions.
8. Artifact lineage preserves producer and mutation provenance.
9. Waiting is explicit and attributable.
10. Admissible trajectories are permissions, not predictions.
11. FQPK/FQPX remain optional until round-trip conformance is proven.
