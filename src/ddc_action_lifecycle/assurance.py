from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .channel import assess_channel_event
from .ledger import LifecycleEvent, LifecycleLedger, LifecycleValidationError, create_event


@dataclass(frozen=True)
class DecisionAssessment:
    event_id: str
    decision: str
    status: str
    horizon_event_ids: tuple[str, ...]
    required_evidence_event_ids: tuple[str, ...]
    consulted_evidence_event_ids: tuple[str, ...]
    missing_required_event_ids: tuple[str, ...]
    unavailable_consulted_event_ids: tuple[str, ...]
    unusable_consulted_event_ids: tuple[str, ...]
    contaminated_consulted_event_ids: tuple[str, ...]
    channel_event_ids: tuple[str, ...]
    inadequate_channel_event_ids: tuple[str, ...]
    missing_channel_assurance_event_ids: tuple[str, ...]
    evidence_channel_status: str
    independent_source_groups: tuple[str, ...]
    minimum_independent_sources: int
    independence_shortfall: int
    unresolved_assumptions: tuple[str, ...]
    contradictions: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "decision": self.decision,
            "status": self.status,
            "horizon_event_ids": list(self.horizon_event_ids),
            "required_evidence_event_ids": list(self.required_evidence_event_ids),
            "consulted_evidence_event_ids": list(self.consulted_evidence_event_ids),
            "missing_required_event_ids": list(self.missing_required_event_ids),
            "unavailable_consulted_event_ids": list(self.unavailable_consulted_event_ids),
            "unusable_consulted_event_ids": list(self.unusable_consulted_event_ids),
            "contaminated_consulted_event_ids": list(self.contaminated_consulted_event_ids),
            "channel_event_ids": list(self.channel_event_ids),
            "inadequate_channel_event_ids": list(self.inadequate_channel_event_ids),
            "missing_channel_assurance_event_ids": list(self.missing_channel_assurance_event_ids),
            "evidence_channel_status": self.evidence_channel_status,
            "independent_source_groups": list(self.independent_source_groups),
            "minimum_independent_sources": self.minimum_independent_sources,
            "independence_shortfall": self.independence_shortfall,
            "unresolved_assumptions": list(self.unresolved_assumptions),
            "contradictions": list(self.contradictions),
            "reasons": list(self.reasons),
        }


def _strings(event: LifecycleEvent, field: str) -> tuple[str, ...]:
    value = event.payload.get(field, ())
    if not isinstance(value, (tuple, list)):
        raise LifecycleValidationError(f"{field} must be an array")
    return tuple(value)


def _is_usable_evidence(event: LifecycleEvent) -> bool:
    if event.phase != "EVIDENCE_STATE":
        return False
    if event.payload.get("profile") != "ddc.evidence-state.v1":
        return False
    availability = event.payload.get("availability")
    if availability is None:
        return False
    if not hasattr(availability, "get"):
        return False
    for facet in ("existed", "reachable", "discoverable", "fresh", "accessible", "trusted"):
        if availability.get(facet) is not True:
            return False
    return True


def assess_decision(
    ledger: LifecycleLedger,
    decision_event_id: str,
) -> DecisionAssessment:
    event = ledger.get(decision_event_id)
    if event.phase != "DECISION":
        raise LifecycleValidationError("assessment target must be a DECISION event")
    if event.payload.get("profile") != "ddc.decision-state.v1":
        raise LifecycleValidationError(
            "decision event does not use ddc.decision-state.v1"
        )

    decision = str(event.payload["decision"])
    required = _strings(event, "required_evidence_event_ids")
    consulted = _strings(event, "consulted_evidence_event_ids")
    assumptions = _strings(event, "unresolved_assumptions")
    contradictions = _strings(event, "contradictions")

    horizon = ledger.evidence_horizon(
        actor=event.actor,
        decision_time=event.event_time,
    )
    horizon_ids = tuple(item.event_id for item in horizon)
    horizon_set = set(horizon_ids)
    consulted_set = set(consulted)

    missing_required = tuple(item for item in required if item not in consulted_set)
    unavailable_consulted = tuple(
        item for item in consulted if item not in horizon_set
    )

    unusable: list[str] = []
    contaminated: list[str] = []
    channel_event_ids: list[str] = []
    inadequate_channel_event_ids: list[str] = []
    missing_channel_assurance_event_ids: list[str] = []
    independence_groups: set[str] = set()
    for event_id in consulted:
        if event_id not in horizon_set:
            continue
        evidence = ledger.get(event_id)
        if not _is_usable_evidence(evidence):
            unusable.append(event_id)
        contamination = evidence.payload.get("contamination_from_event_ids", ())
        if isinstance(contamination, (list, tuple)) and contamination:
            contaminated.append(event_id)

        channel_event_id = evidence.payload.get("channel_event_id")
        if isinstance(channel_event_id, str) and channel_event_id:
            channel_event_ids.append(channel_event_id)
            channel_assessment = assess_channel_event(ledger.get(channel_event_id))
            if channel_assessment.status != "ADEQUATE":
                inadequate_channel_event_ids.append(channel_event_id)
        elif event.payload.get("require_channel_assurance") is True:
            missing_channel_assurance_event_ids.append(event_id)

        group = evidence.payload.get("independence_group")
        if isinstance(group, str) and group:
            independence_groups.add(group)

    minimum_independent = event.payload.get("minimum_independent_sources", 0)
    independence_shortfall = max(0, minimum_independent - len(independence_groups))

    reasons: list[str] = []
    if missing_required:
        reasons.append("required evidence was not consulted")
    if unavailable_consulted:
        reasons.append("consulted evidence was outside the actor's historical horizon")
    if unusable:
        reasons.append("consulted evidence was not fully usable at decision time")
    if contaminated:
        reasons.append("consulted evidence carries post-action contamination")
    if inadequate_channel_event_ids:
        reasons.append("evidence channel was inadequate at decision time")
    if missing_channel_assurance_event_ids:
        reasons.append("required evidence channel assurance was missing")
    if independence_shortfall:
        reasons.append("independent evidence source requirement was not met")
    if contradictions:
        reasons.append("decision state contains unresolved contradictions")
    if assumptions:
        reasons.append("decision state contains unresolved assumptions")

    if inadequate_channel_event_ids:
        evidence_channel_status = "INADEQUATE"
    elif missing_channel_assurance_event_ids:
        evidence_channel_status = "UNKNOWN"
    elif channel_event_ids:
        evidence_channel_status = "ADEQUATE"
    else:
        evidence_channel_status = "NOT_ASSESSED"

    hard_invalid = bool(
        unavailable_consulted
        or unusable
        or contaminated
        or inadequate_channel_event_ids
        or missing_channel_assurance_event_ids
    )
    if hard_invalid:
        status = "INVALID"
    elif decision == "ALLOW":
        status = "INVALID" if reasons else "VALID"
    elif decision in {"BLOCK", "RECHECK", "REQUIRE_HUMAN", "SIMULATE_FIRST"}:
        status = "VALID"
    else:
        status = "INCOMPLETE"

    return DecisionAssessment(
        event_id=event.event_id,
        decision=decision,
        status=status,
        horizon_event_ids=horizon_ids,
        required_evidence_event_ids=required,
        consulted_evidence_event_ids=consulted,
        missing_required_event_ids=missing_required,
        unavailable_consulted_event_ids=unavailable_consulted,
        unusable_consulted_event_ids=tuple(unusable),
        contaminated_consulted_event_ids=tuple(contaminated),
        channel_event_ids=tuple(channel_event_ids),
        inadequate_channel_event_ids=tuple(inadequate_channel_event_ids),
        missing_channel_assurance_event_ids=tuple(missing_channel_assurance_event_ids),
        evidence_channel_status=evidence_channel_status,
        independent_source_groups=tuple(sorted(independence_groups)),
        minimum_independent_sources=minimum_independent,
        independence_shortfall=independence_shortfall,
        unresolved_assumptions=assumptions,
        contradictions=contradictions,
        reasons=tuple(reasons),
    )


def next_transition_admissibility(
    ledger: LifecycleLedger,
    decision_event_id: str,
) -> dict[str, Any]:
    assessment = assess_decision(ledger, decision_event_id)
    mapping = {
        "ALLOW": "ALLOW",
        "BLOCK": "BLOCK",
        "RECHECK": "RECHECK",
        "REQUIRE_HUMAN": "REQUIRE_HUMAN",
        "SIMULATE_FIRST": "SIMULATE_FIRST",
        "UNKNOWN": "UNKNOWN",
    }
    disposition = mapping[assessment.decision]
    if assessment.decision == "ALLOW" and assessment.status != "VALID":
        disposition = "BLOCK"
    return {
        "decision_event_id": assessment.event_id,
        "disposition": disposition,
        "assessment_status": assessment.status,
        "reasons": list(assessment.reasons),
    }


def admissibility_event(
    ledger: LifecycleLedger,
    decision_event_id: str,
    *,
    event_id: str,
    actor: str,
    recorded_at: str,
) -> LifecycleEvent:
    """Appendable evidence-bound result for the next execution boundary."""
    assessment = assess_decision(ledger, decision_event_id)
    transition = next_transition_admissibility(ledger, decision_event_id)
    decision_event = ledger.get(decision_event_id)
    return create_event(
        lifecycle_id=ledger.lifecycle_id,
        event_id=event_id,
        phase="ADMISSIBILITY",
        actor=actor,
        event_time=recorded_at,
        recorded_at=recorded_at,
        parent_event_ids=(decision_event_id,),
        claim_scope=("next-transition admissibility",),
        epistemic_state="ATTESTED",
        evidence_refs=(decision_event.digest,),
        payload={
            "profile": "ddc.admissibility.v1",
            "decision_event_id": decision_event_id,
            "decision_event_digest": decision_event.digest,
            "disposition": transition["disposition"],
            "assessment_status": assessment.status,
            "reasons": list(assessment.reasons),
            "historical_horizon_event_ids": list(assessment.horizon_event_ids),
        },
    )
