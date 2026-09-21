from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ledger import LifecycleEvent, LifecycleLedger, LifecycleValidationError


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
    availability = event.payload.get("availability")
    if availability is None:
        return True
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
    for event_id in consulted:
        if event_id not in horizon_set:
            continue
        evidence = ledger.get(event_id)
        if not _is_usable_evidence(evidence):
            unusable.append(event_id)

    reasons: list[str] = []
    if missing_required:
        reasons.append("required evidence was not consulted")
    if unavailable_consulted:
        reasons.append("consulted evidence was outside the actor's historical horizon")
    if unusable:
        reasons.append("consulted evidence was not fully usable at decision time")
    if contradictions:
        reasons.append("decision state contains unresolved contradictions")
    if assumptions:
        reasons.append("decision state contains unresolved assumptions")

    hard_invalid = bool(unavailable_consulted or unusable)
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
