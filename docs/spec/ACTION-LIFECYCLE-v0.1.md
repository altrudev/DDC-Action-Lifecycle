# DDC Action Lifecycle Public Interoperability Profile v0.1

SPDX-License-Identifier: Apache-2.0

This document defines the public event language for interoperating with DDC Action Lifecycle. It does not license the proprietary runtime, DDC Radial implementation, enforcement engine, or commercial orchestration logic.

## Event envelope

Every lifecycle event carries:

- lifecycle_id: stable identifier for one action lineage;
- event_id: unique identifier inside that lifecycle;
- phase: semantic lifecycle boundary;
- actor: the actor/source associated with the event;
- event_time: when the represented event occurred;
- recorded_at: when this immutable record was created;
- parent_event_ids: explicit graph ancestry;
- claim_scope: claims this event is competent to support;
- epistemic_state: OBSERVED, ATTESTED, INFERRED, UNPROVEN, ADJUDICATED, or UNKNOWN;
- evidence_refs: external evidence references/digests;
- payload: phase-specific content;
- digest: SHA-256 commitment over the event core.

## Immutable history

Accepted events are append-only. A later observation, adjudication, or reconstruction MUST be represented by a new event. It MUST NOT mutate an earlier event.

## Historical evidence horizons

Evidence availability is actor-specific and time-specific.

An EVIDENCE_STATE using profile ddc.evidence-state.v1 records at minimum:

- evidence creation time;
- evidence availability time;
- actors to whom it was available;
- availability facets: existed, reachable, discoverable, fresh, accessible, trusted.

A later event may describe an earlier real-world occurrence. Such evidence MUST NOT be included in an actor's historical decision horizon unless both its claimed availability and its immutable lifecycle record existed by that decision point. A later backfilled record can improve reconstruction, but it cannot rewrite the historical horizon.

## Decision state

A DECISION using profile ddc.decision-state.v1 identifies:

- disposition;
- required evidence event ids;
- consulted evidence event ids;
- unresolved assumptions;
- contradictions;
- an optional minimum number of independent evidence source groups.

ALLOW is not valid under the reference invariant set when required evidence was not consulted, consulted evidence was outside the actor's historical horizon, consulted evidence was unusable, consulted evidence carries post-action contamination, the declared independent-source minimum is not met, or unresolved contradictions/assumptions remain.

A decision using the profiled assurance rules must not treat an unprofiled EVIDENCE_STATE as fully usable merely because it has a timestamp. Usability requires the ddc.evidence-state.v1 availability facets.

## Consequence versus decision reconstruction

A conforming consumer keeps two questions separate:

1. What can admissible evidence establish happened?
2. What was the actor justified in concluding at the historical decision point?

Later evidence may strengthen the first answer without altering the second.

## Evidence causality and independence

An evidence-state event may identify a causal origin, an independence group, and contaminating lifecycle events.

Multiple records from the same independence group MUST NOT be counted as independent confirmation. Evidence marked as contaminated by later action/retry state MUST NOT silently support an ALLOW decision as if it were an untouched observation of the earlier state.

## Branches

Retries, recovery paths, fallbacks, and alternate routes SHOULD carry a branch_id. Consumers MUST NOT collapse branches merely because later records converge on the same downstream state.

## Interoperability roles

DDC Action Receipt may be referenced from ACTION_RECEIPT events.
Agent Replay may emit RECONSTRUCTION events.
DDC Physical Gate may consume historical evidence state and emit ADMISSIBILITY events.
BoundaryProof may evaluate whether claims or certainty crossed unsupported evidentiary boundaries.

## Security boundary

An event digest establishes integrity of the serialized event content. It does not by itself authenticate actor identity, prove source honesty, prove trusted time, establish legal authority, or prove a downstream physical/economic consequence.

Those claims require appropriate independent evidence and trust anchors.
