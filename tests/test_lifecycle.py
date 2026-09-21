import pytest

from ddc_action_lifecycle import (
    LifecycleLedger,
    LifecycleValidationError,
    create_event,
)


def e(**kw):
    defaults = {
        "lifecycle_id": "life-1",
        "actor": "agent-a",
        "recorded_at": "2026-09-20T10:00:00Z",
        "claim_scope": [],
        "evidence_refs": [],
        "payload": {},
    }
    defaults.update(kw)
    return create_event(**defaults)


def test_append_only_event_digest_detects_tampering():
    ledger = LifecycleLedger("life-1")
    event = e(
        event_id="intent-1",
        phase="INTENT",
        event_time="2026-09-20T10:00:00Z",
        epistemic_state="OBSERVED",
    )
    ledger.append(event)
    object.__setattr__(event, "payload", {"changed": True})
    with pytest.raises(LifecycleValidationError, match="digest mismatch"):
        ledger.verify()


def test_later_truth_does_not_enter_historical_evidence_horizon():
    ledger = LifecycleLedger("life-1")
    early = e(
        event_id="evidence-early",
        phase="EVIDENCE_STATE",
        event_time="2026-09-20T10:01:00Z",
        recorded_at="2026-09-20T10:01:00Z",
        epistemic_state="OBSERVED",
        payload={
            "available_to": ["agent-a"],
            "available_at": "2026-09-20T10:01:00Z",
        },
    )
    later = e(
        event_id="evidence-later",
        phase="EVIDENCE_STATE",
        event_time="2026-09-20T10:01:00Z",
        recorded_at="2026-09-20T10:08:00Z",
        epistemic_state="ATTESTED",
        payload={
            "available_to": ["agent-a"],
            "available_at": "2026-09-20T10:08:00Z",
        },
    )
    ledger.append(early)
    ledger.append(later)

    horizon = ledger.evidence_horizon(
        actor="agent-a",
        decision_time="2026-09-20T10:05:00Z",
    )
    assert [item.event_id for item in horizon] == ["evidence-early"]


def test_actor_specific_horizon_prevents_knowledge_leakage():
    ledger = LifecycleLedger("life-1")
    evidence = e(
        event_id="provider-only",
        phase="EVIDENCE_STATE",
        event_time="2026-09-20T10:01:00Z",
        recorded_at="2026-09-20T10:01:00Z",
        epistemic_state="OBSERVED",
        payload={
            "available_to": ["provider"],
            "available_at": "2026-09-20T10:01:00Z",
        },
    )
    ledger.append(evidence)

    assert ledger.evidence_horizon(
        actor="agent-a",
        decision_time="2026-09-20T10:05:00Z",
    ) == ()
    assert [x.event_id for x in ledger.evidence_horizon(
        actor="provider",
        decision_time="2026-09-20T10:05:00Z",
    )] == ["provider-only"]


def test_retry_branches_are_preserved_not_collapsed():
    ledger = LifecycleLedger("life-1")
    for event in [
        e(
            event_id="dispatch-1",
            phase="DISPATCH",
            event_time="2026-09-20T10:02:00Z",
            recorded_at="2026-09-20T10:02:00Z",
            epistemic_state="OBSERVED",
            payload={"branch_id": "attempt-1"},
        ),
        e(
            event_id="dispatch-2",
            phase="DISPATCH",
            event_time="2026-09-20T10:05:00Z",
            recorded_at="2026-09-20T10:05:00Z",
            epistemic_state="OBSERVED",
            payload={"branch_id": "attempt-2"},
        ),
    ]:
        ledger.append(event)

    branches = ledger.branches()
    assert list(branches) == ["attempt-1", "attempt-2"]
    assert branches["attempt-1"][0].event_id == "dispatch-1"
    assert branches["attempt-2"][0].event_id == "dispatch-2"


def test_reconstruction_is_appended_not_rewrite():
    ledger = LifecycleLedger("life-1")
    original = e(
        event_id="execution-1",
        phase="EXECUTION",
        event_time="2026-09-20T10:02:00Z",
        recorded_at="2026-09-20T10:02:00Z",
        epistemic_state="UNPROVEN",
        payload={"status": "UNKNOWN"},
    )
    ledger.append(original)
    reconstruction = e(
        event_id="replay-1",
        phase="RECONSTRUCTION",
        event_time="2026-09-20T10:02:00Z",
        recorded_at="2026-09-20T10:10:00Z",
        parent_event_ids=["execution-1"],
        epistemic_state="ATTESTED",
        payload={"as_of": "2026-09-20T10:10:00Z", "status": "SUCCEEDED"},
    )
    ledger.append(reconstruction)

    assert ledger.events[0].payload["status"] == "UNKNOWN"
    assert ledger.latest_reconstruction().payload["status"] == "SUCCEEDED"


def test_parent_must_exist_before_child():
    ledger = LifecycleLedger("life-1")
    child = e(
        event_id="child",
        phase="EXECUTION",
        event_time="2026-09-20T10:02:00Z",
        recorded_at="2026-09-20T10:02:00Z",
        parent_event_ids=["missing"],
        epistemic_state="OBSERVED",
    )
    with pytest.raises(LifecycleValidationError, match="unknown parent"):
        ledger.append(child)


def test_float_payload_rejected_to_keep_hashing_deterministic():
    with pytest.raises(LifecycleValidationError, match="floating point"):
        e(
            event_id="bad",
            phase="INTENT",
            event_time="2026-09-20T10:00:00Z",
            epistemic_state="OBSERVED",
            payload={"confidence": 0.9},
        )
