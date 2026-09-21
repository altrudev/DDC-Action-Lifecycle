from ddc_action_lifecycle import LifecycleLedger, create_event


ledger = LifecycleLedger("transfer-001")

ledger.append(create_event(
    lifecycle_id="transfer-001",
    event_id="intent",
    phase="INTENT",
    actor="agent-a",
    event_time="2026-09-20T10:00:00Z",
    recorded_at="2026-09-20T10:00:00Z",
    epistemic_state="OBSERVED",
    payload={"operation": "transfer", "amount": "500.00", "currency": "CAD"},
))

ledger.append(create_event(
    lifecycle_id="transfer-001",
    event_id="status-evidence",
    phase="EVIDENCE_STATE",
    actor="status-service",
    event_time="2026-09-20T10:01:00Z",
    recorded_at="2026-09-20T10:01:00Z",
    parent_event_ids=["intent"],
    epistemic_state="OBSERVED",
    payload={
        "available_to": ["agent-a"],
        "available_at": "2026-09-20T10:01:00Z",
        "state": "NO_CONFIRMATION",
    },
))

print([
    event.event_id
    for event in ledger.evidence_horizon(
        actor="agent-a",
        decision_time="2026-09-20T10:05:00Z",
    )
])
