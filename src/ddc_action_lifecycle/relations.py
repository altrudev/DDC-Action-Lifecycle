from __future__ import annotations

from .ledger import LifecycleEvent, LifecycleLedger, LifecycleValidationError, create_event


RELATIONSHIP_PROFILE = "ddc.relationship.v1"
RELATION_TYPES = {
    "CAUSED_BY",
    "OBSERVED_BY",
    "SUPPORTED_BY",
    "DERIVED_FROM",
    "CONTAMINATED_BY",
    "SUPERSEDES",
    "RECONSTRUCTS",
    "RECONCILES",
}


def relationship_event(
    ledger: LifecycleLedger,
    *,
    event_id: str,
    actor: str,
    relation_type: str,
    source_event_id: str,
    target_event_id: str,
    recorded_at: str,
    claim_scope: tuple[str, ...] = (),
) -> LifecycleEvent:
    """Create an explicit typed relationship without overloading parent ancestry."""
    if relation_type not in RELATION_TYPES:
        raise LifecycleValidationError("unsupported relationship type")
    source = ledger.get(source_event_id)
    target = ledger.get(target_event_id)
    latest_time = max(source.recorded_at, target.recorded_at, recorded_at)
    return create_event(
        lifecycle_id=ledger.lifecycle_id,
        event_id=event_id,
        phase="RELATIONSHIP",
        actor=actor,
        event_time=latest_time,
        recorded_at=latest_time,
        claim_scope=claim_scope,
        epistemic_state="ATTESTED",
        evidence_refs=(source.digest, target.digest),
        payload={
            "profile": RELATIONSHIP_PROFILE,
            "relation_type": relation_type,
            "source_event_id": source_event_id,
            "target_event_id": target_event_id,
        },
    )
