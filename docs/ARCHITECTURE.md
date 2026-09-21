# DDC Action Lifecycle v0.1 Architecture

## Purpose

DDC Action Lifecycle is the integration layer joining the strongest properties of DDC Action Receipt and Agent Replay without collapsing their evidence boundaries.

It is not a replacement for either product.

- **Action Receipt** remains the signed decision/execution commitment.
- **Agent Replay** remains the reconstruction engine.
- **Action Lifecycle** supplies the append-only evidence graph that connects before, during, and after execution.

## Core invariant

> A later phase may reference an earlier evidence state, but it may never mutate it.

The lifecycle therefore uses immutable events. Reconstruction is an appended interpretation of prior evidence, never an edit of history.

## Lifecycle

Intent -> Authority -> Evidence State -> Decision -> Action Receipt -> Dispatch -> Execution -> Observation -> Consequence -> Reconstruction -> Admissibility of next transition

Retries and alternate routes are branches of the same lifecycle, not overwritten attempts.

## Two kinds of truth

The runtime MUST preserve both:

1. **Consequence reconstruction** — given admissible evidence now, what can be established happened?
2. **Decision reconstruction** — using only evidence available to the actor then, was the action justified?

A later authoritative record can improve consequence reconstruction while remaining excluded from the historical evidence horizon used to judge an earlier decision.

## Evidence horizon

Evidence availability is actor- and time-specific.

An evidence item may exist, be unreachable, be undiscoverable, be stale, be inaccessible to the actor, be untrusted, or never actually be consulted.

The lifecycle must not reduce these states to a single global available boolean.

## Evidence causality

Evidence is not passive. Retries, reconciliation, recovery, investigation, and later execution may create or alter evidence.

Each evidence-bearing event SHOULD preserve event time, record creation time, actor availability time, source and claim scope, causal provenance, transformation lineage, independence group, contradictions, and epistemic state.

## Product boundaries

### DDC Action Receipt
Produces immutable decision/execution commitments and may be referenced by an ACTION_RECEIPT event.

### Agent Replay
Consumes lifecycle events plus independent evidence and emits versioned RECONSTRUCTION events.

### DDC Physical Gate
Consumes current lifecycle/evidence state and emits or enforces ADMISSIBILITY decisions for consequential next transitions.

### BoundaryProof
Verifies that certainty, identity, authority, and consequence claims do not leak across unsupported boundaries.

## Release invariants

A conforming implementation must preserve chronology != causality; dispatch != consequence; observation != reconstruction; later truth != retroactive knowledge; identity certainty != authority certainty; each transition earns its own certainty; claim authority is claim-specific; actor-specific evidence horizons; available, required, and consulted evidence are distinct; unknown is representable; contradictions stay visible; retries and alternate routes remain separate branches; reconstruction is versioned; missing evidence != evidence of absence; and no later event can mutate an accepted earlier event.

## Attribution

The broader DDC architecture and DDC Action Lifecycle are designed and developed by **Valentyn Rukhaylo / Altru.dev**.

Several evidence/replay invariants were materially sharpened through Valentyn Rukhaylo's public technical engagement with **Jason McGill**, particularly around downstream consequence boundaries, contemporaneous versus later evidence, the three-clock model, actor-specific evidence horizons, and consequence versus decision reconstruction.

DDC Radial analysis extended those refinements into required-versus-consulted evidence, evidence-channel adequacy, causal evidence provenance, post-action contamination, branch preservation, and continuous evidence-bound execution.
