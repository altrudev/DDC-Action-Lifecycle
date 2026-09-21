import pytest

from ddc_action_lifecycle import (
    LifecycleLedger,
    LifecycleValidationError,
    assess_decision,
    create_event,
    dumps_jsonl,
    loads_jsonl,
    next_transition_admissibility,
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


def _profile_evidence(
    *,
    event_id="ev-1",
    actor="sensor",
    available_to=("agent-a",),
    available_at="2026-09-20T10:01:00Z",
    created_at="2026-09-20T10:01:00Z",
    availability=None,
):
    return e(
        event_id=event_id,
        phase="EVIDENCE_STATE",
        actor=actor,
        event_time="2026-09-20T10:01:00Z",
        recorded_at=available_at,
        epistemic_state="OBSERVED",
        payload={
            "profile": "ddc.evidence-state.v1",
            "available_to": list(available_to),
            "available_at": available_at,
            "evidence_created_at": created_at,
            "availability": availability or {
                "existed": True,
                "reachable": True,
                "discoverable": True,
                "fresh": True,
                "accessible": True,
                "trusted": True,
            },
        },
    )


def _decision(*, required=("ev-1",), consulted=("ev-1",), decision="ALLOW",
              assumptions=(), contradictions=()):
    return e(
        event_id="decision-1",
        phase="DECISION",
        event_time="2026-09-20T10:05:00Z",
        recorded_at="2026-09-20T10:05:00Z",
        epistemic_state="ATTESTED",
        payload={
            "profile": "ddc.decision-state.v1",
            "decision": decision,
            "required_evidence_event_ids": list(required),
            "consulted_evidence_event_ids": list(consulted),
            "unresolved_assumptions": list(assumptions),
            "contradictions": list(contradictions),
        },
    )


def test_profiled_allow_is_valid_only_when_evidence_is_in_actor_horizon():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    ledger.append(_decision())
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "VALID"
    assert next_transition_admissibility(ledger, "decision-1")["disposition"] == "ALLOW"


def test_allow_fails_closed_when_required_evidence_was_not_consulted():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    ledger.append(_decision(consulted=()))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "INVALID"
    assert assessment.missing_required_event_ids == ("ev-1",)
    assert next_transition_admissibility(ledger, "decision-1")["disposition"] == "BLOCK"


def test_allow_rejects_evidence_that_arrived_after_decision():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence(
        available_at="2026-09-20T10:08:00Z",
        created_at="2026-09-20T10:08:00Z",
    ))
    ledger.append(_decision())
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.unavailable_consulted_event_ids == ("ev-1",)
    assert assessment.status == "INVALID"


def test_allow_rejects_unusable_consulted_evidence():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence(
        availability={
            "existed": True,
            "reachable": True,
            "discoverable": True,
            "fresh": False,
            "accessible": True,
            "trusted": True,
        }
    ))
    ledger.append(_decision())
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.unusable_consulted_event_ids == ("ev-1",)
    assert assessment.status == "INVALID"


def test_allow_rejects_unresolved_assumptions_and_contradictions():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    ledger.append(_decision(
        assumptions=("provider status unknown",),
        contradictions=("local timeout conflicts with provider record",),
    ))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "INVALID"
    assert len(assessment.reasons) == 2


def test_non_allow_can_preserve_uncertainty_without_becoming_invalid():
    ledger = LifecycleLedger("life-1")
    ledger.append(_decision(
        required=(),
        consulted=(),
        decision="RECHECK",
        assumptions=("confirmation pending",),
    ))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "VALID"
    assert next_transition_admissibility(ledger, "decision-1")["disposition"] == "RECHECK"


def test_profile_rejects_impossible_evidence_clock_order():
    with pytest.raises(LifecycleValidationError, match="cannot be after available_at"):
        _profile_evidence(
            available_at="2026-09-20T10:01:00Z",
            created_at="2026-09-20T10:02:00Z",
        )


def test_nested_payload_is_immutable_after_creation():
    raw = {
        "available_to": ["agent-a"],
        "available_at": "2026-09-20T10:01:00Z",
        "nested": {"value": ["original"]},
    }
    event = e(
        event_id="immutable",
        phase="EVIDENCE_STATE",
        event_time="2026-09-20T10:01:00Z",
        recorded_at="2026-09-20T10:01:00Z",
        epistemic_state="OBSERVED",
        payload=raw,
    )
    raw["nested"]["value"][0] = "changed"
    assert event.payload["nested"]["value"][0] == "original"
    with pytest.raises(TypeError):
        event.payload["nested"]["value"] = ("changed",)


def test_parent_must_already_be_recorded_before_child_record():
    ledger = LifecycleLedger("life-1")
    parent = e(
        event_id="parent",
        phase="OBSERVATION",
        event_time="2026-09-20T10:00:00Z",
        recorded_at="2026-09-20T10:10:00Z",
        epistemic_state="ATTESTED",
    )
    ledger.append(parent)
    child = e(
        event_id="child-recorded-too-early",
        phase="RECONSTRUCTION",
        event_time="2026-09-20T10:00:00Z",
        recorded_at="2026-09-20T10:05:00Z",
        parent_event_ids=["parent"],
        epistemic_state="INFERRED",
    )
    with pytest.raises(LifecycleValidationError, match="not yet recorded"):
        ledger.append(child)


def test_jsonl_roundtrip_revalidates_hashes_and_graph():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    ledger.append(_decision())
    encoded = dumps_jsonl(ledger.events)
    recovered = loads_jsonl(encoded)
    assert [x.to_dict() for x in recovered.events] == [
        x.to_dict() for x in ledger.events
    ]


def test_jsonl_rejects_digest_tampering():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    encoded = dumps_jsonl(ledger.events).replace(
        ledger.events[0].digest,
        "sha256:" + "0" * 64,
    )
    with pytest.raises(LifecycleValidationError, match="digest mismatch"):
        loads_jsonl(encoded)
