from ddc_action_lifecycle import (
    LifecycleLedger,
    assess_decision,
    create_event,
    next_transition_admissibility,
)


ledger = LifecycleLedger("payment-001")

ledger.append(create_event(
    lifecycle_id="payment-001",
    event_id="status-before-retry",
    phase="EVIDENCE_STATE",
    actor="payment-status",
    event_time="2026-09-20T10:01:00Z",
    recorded_at="2026-09-20T10:01:00Z",
    epistemic_state="OBSERVED",
    payload={
        "profile": "ddc.evidence-state.v1",
        "available_to": ["agent-a"],
        "available_at": "2026-09-20T10:01:00Z",
        "evidence_created_at": "2026-09-20T10:01:00Z",
        "availability": {
            "existed": True,
            "reachable": True,
            "discoverable": True,
            "fresh": True,
            "accessible": True,
            "trusted": True
        },
        "state": "NO_CONFIRMATION",
        "branch_id": "attempt-1"
    },
))

ledger.append(create_event(
    lifecycle_id="payment-001",
    event_id="retry-decision",
    phase="DECISION",
    actor="agent-a",
    event_time="2026-09-20T10:05:00Z",
    recorded_at="2026-09-20T10:05:00Z",
    parent_event_ids=["status-before-retry"],
    epistemic_state="ATTESTED",
    payload={
        "profile": "ddc.decision-state.v1",
        "decision": "ALLOW",
        "required_evidence_event_ids": ["status-before-retry"],
        "consulted_evidence_event_ids": ["status-before-retry"],
        "unresolved_assumptions": [],
        "contradictions": [],
        "branch_id": "attempt-2"
    },
))

# At 10:08 authoritative evidence arrives proving the original payment
# had already been accepted at 10:01. It improves consequence reconstruction,
# but it must not enter the agent's 10:05 historical evidence horizon.
ledger.append(create_event(
    lifecycle_id="payment-001",
    event_id="late-provider-confirmation",
    phase="EVIDENCE_STATE",
    actor="provider",
    event_time="2026-09-20T10:01:00Z",
    recorded_at="2026-09-20T10:08:00Z",
    epistemic_state="ATTESTED",
    payload={
        "profile": "ddc.evidence-state.v1",
        "available_to": ["agent-a"],
        "available_at": "2026-09-20T10:08:00Z",
        "evidence_created_at": "2026-09-20T10:08:00Z",
        "availability": {
            "existed": True,
            "reachable": True,
            "discoverable": True,
            "fresh": True,
            "accessible": True,
            "trusted": True
        },
        "state": "ORIGINAL_ACCEPTED",
        "branch_id": "attempt-1"
    },
))

assessment = assess_decision(ledger, "retry-decision")
print(assessment.to_dict())
print(next_transition_admissibility(ledger, "retry-decision"))
