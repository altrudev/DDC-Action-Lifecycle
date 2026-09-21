# DDC Radial Review — v0.1 Foundation

This review treats DDC Action Lifecycle as an evidence-bearing runtime boundary, not as a logging format.

## 1. Semantic lens
Risk: lifecycle phases become labels with no enforceable meaning.

Response: v0.1 defines explicit event phases, epistemic states, decision/evidence profiles, and public schemas. The runtime does not infer stronger claims from a phase name alone.

## 2. Temporal lens
Risk: later evidence is treated as if it were available earlier.

Response: event_time, recorded_at, evidence_created_at, available_at, and decision time remain distinct. Historical evidence horizons are actor- and time-scoped. Later truth cannot become retroactive knowledge.

## 3. Authority lens
Risk: identity is mistaken for authority.

Response: lifecycle events carry actor identity and claim_scope separately. Authority artifacts are referenced rather than inferred from actor names. Future integrations must bind authority independently.

## 4. Evidence lens
Risk: available, required, and consulted evidence collapse into one set.

Response: decision profiles keep required and consulted evidence separate. The runtime computes the actor's historical evidence horizon independently.

## 5. Causal lens
Risk: chronology, graph ancestry, evidence dependency, and causality are collapsed into one relationship.

Response: `parent_event_ids` remains graph ancestry only. v0.1 now also supports explicit `RELATIONSHIP` events with typed relations such as CAUSED_BY, SUPPORTED_BY, DERIVED_FROM, CONTAMINATED_BY, RECONSTRUCTS, and RECONCILES. A temporal or ancestry relationship does not by itself assert causality.

## 6. Branch / retry lens
Risk: retries overwrite or collapse prior attempts.

Response: branch_id preserves alternate attempts. Reconstruction is append-only and cannot rewrite prior branch state.

## 7. Consequence lens
Risk: dispatch or executor claims become proof of external consequence.

Response: DISPATCH, EXECUTION, OBSERVATION, and CONSEQUENCE are distinct boundaries. A downstream consequence requires its own evidence.

## 8. Representation lens
Risk: cross-language serialization changes event digests.

Response: the reference runtime rejects floats, bounds integers to safe JSON range, canonicalizes timestamps to UTC, orders object keys by UTF-16 code-unit order, and hashes canonical UTF-8 bytes.

## 9. Integrity / mutation lens
Risk: nested payloads are changed after a digest is created.

Response: payloads are recursively frozen inside LifecycleEvent. Import re-computes digests and graph validation.

## 10. Evidence-channel lens
Risk: evidence existed but was stale, unreachable, inaccessible, undiscoverable, untrusted, or delivered through a channel that was itself degraded.

Response: the profiled evidence state models evidence usability facets independently. First-class EVIDENCE_CHANNEL events record channel identity, actor visibility, state, latency, policy latency bounds, and provenance. A decision may require channel assurance. Decision quality and channel quality are reported separately so a bad outcome does not automatically become a bad-decision claim.

## 11. Uncertainty lens
Risk: unknowns or contradictions are silently converted to certainty.

Response: UNKNOWN and UNPROVEN are explicit epistemic states. Contradictions and unresolved assumptions invalidate profiled ALLOW while RECHECK, REQUIRE_HUMAN, SIMULATE_FIRST, and BLOCK remain legitimate outcomes.

## 12. Security / resource lens
Risk: oversized events, parent fan-in, or unbounded histories create denial-of-service conditions.

Response: the ledger enforces configurable event-count, parent-count, and per-event byte limits. Parent references must already exist, preventing cycles by construction.

## 13. Determinism lens
Risk: equivalent lifecycle graphs produce different customer bundles because independent siblings were ingested in different orders.

Response: evidence bundles canonicalize events, branches, and decision summaries by declared stable keys rather than relying on append order. Deterministic export does not erase the original event timestamps or graph.

## 14. Interoperability lens
Risk: Action Lifecycle absorbs Action Receipt or Agent Replay and destroys their independent trust boundaries.

Response: Action Receipt remains the signed action/decision commitment. Agent Replay remains the reconstruction engine. Lifecycle provides the immutable graph joining them. Physical Gate and BoundaryProof consume or verify separate boundaries.

## 15. Licensing lens
Risk: public interoperability work accidentally licenses the commercial engine.

Response: schemas, examples, public specification, and future conformance vectors are Apache-2.0. Runtime, DDC Radial logic, orchestration, and enforcement remain proprietary unless separately licensed.

## Release blockers before v0.1 is declared PASS

- Execute the complete test suite in a governed DSR environment.
- Produce a signed/hashed evidence bundle bound to the exact commit.
- Verify package build/install in an isolated environment.
- Run the retry / delayed-confirmation end-to-end fixture across Action Receipt -> Lifecycle -> Replay.
- Run an independent examiner pass against the evidence bundle.
- Do not merge or label a release PASS until those artifacts exist.
