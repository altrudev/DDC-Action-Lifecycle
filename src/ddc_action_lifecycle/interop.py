from __future__ import annotations

from typing import Iterable

from .ledger import LifecycleEvent, LifecycleValidationError, create_event


def _require_sha256(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(ch not in "0123456789abcdef" for ch in value[7:])
    ):
        raise LifecycleValidationError(f"{name} must be a sha256 digest")


def action_receipt_reference(
    *,
    lifecycle_id: str,
    event_id: str,
    actor: str,
    event_time: str,
    recorded_at: str,
    receipt_digest: str,
    decision: str,
    parent_event_ids: Iterable[str] = (),
    branch_id: str | None = None,
) -> LifecycleEvent:
    _require_sha256(receipt_digest, "receipt_digest")
    if decision not in {"ALLOW", "BLOCK", "HUMAN-REVIEW", "RECHECK", "REQUIRE_HUMAN", "SIMULATE_FIRST", "UNKNOWN"}:
        raise LifecycleValidationError("unsupported Action Receipt decision")
    payload = {
        "artifact_type": "ddc-action-receipt",
        "receipt_digest": receipt_digest,
        "decision": decision,
    }
    if branch_id is not None:
        payload["branch_id"] = branch_id
    return create_event(
        lifecycle_id=lifecycle_id,
        event_id=event_id,
        phase="ACTION_RECEIPT",
        actor=actor,
        event_time=event_time,
        recorded_at=recorded_at,
        parent_event_ids=parent_event_ids,
        claim_scope=("decision commitment", "exact action commitment"),
        epistemic_state="ATTESTED",
        evidence_refs=(receipt_digest,),
        payload=payload,
    )


def replay_reconstruction_reference(
    *,
    lifecycle_id: str,
    event_id: str,
    actor: str,
    event_time: str,
    recorded_at: str,
    report_digest: str,
    parent_event_ids: Iterable[str],
    consequence_status: str = "UNKNOWN",
    decision_status: str = "UNKNOWN",
    as_of: str | None = None,
) -> LifecycleEvent:
    _require_sha256(report_digest, "report_digest")
    return create_event(
        lifecycle_id=lifecycle_id,
        event_id=event_id,
        phase="RECONSTRUCTION",
        actor=actor,
        event_time=event_time,
        recorded_at=recorded_at,
        parent_event_ids=parent_event_ids,
        claim_scope=("consequence reconstruction", "decision reconstruction"),
        epistemic_state="ATTESTED",
        evidence_refs=(report_digest,),
        payload={
            "artifact_type": "agent-replay-report",
            "report_digest": report_digest,
            "as_of": as_of or recorded_at,
            "consequence_status": consequence_status,
            "decision_status": decision_status,
        },
    )
