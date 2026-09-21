import json
from pathlib import Path

import pytest

from ddc_action_lifecycle import (
    LifecycleLedger,
    LifecycleValidationError,
    assess_channel_event,
    channel_state_at,
    assess_decision,
    create_event,
    dumps_jsonl,
    loads_jsonl,
    next_transition_admissibility,
    action_receipt_reference,
    admissibility_event,
    build_evidence_bundle,
    replay_reconstruction_reference,
    relationship_event,
    verify_evidence_bundle,
)
from ddc_action_lifecycle.ledger import canonical_bytes


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
    independence_group=None,
    contamination=(),
    channel_event_id=None,
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
            "independence_group": independence_group,
            "contamination_from_event_ids": list(contamination),
            **({"channel_event_id": channel_event_id} if channel_event_id else {}),
        },
    )


def _decision(*, required=("ev-1",), consulted=("ev-1",), decision="ALLOW",
              assumptions=(), contradictions=(), minimum_independent_sources=0,
              require_channel_assurance=False):
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
            "minimum_independent_sources": minimum_independent_sources,
            "require_channel_assurance": require_channel_assurance,
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


def test_canonicalization_uses_utf16_key_order():
    assert canonical_bytes({"\ue000": 1, "\U00010000": 2}) == (
        b'{"\xf0\x90\x80\x80":2,"\xee\x80\x80":1}'
    )


def test_equivalent_timezone_forms_canonicalize_event_timestamps():
    event = e(
        event_id="time-normalized",
        phase="INTENT",
        event_time="2026-09-20T03:00:00-07:00",
        recorded_at="2026-09-20T10:00:00Z",
        epistemic_state="OBSERVED",
    )
    assert event.event_time == "2026-09-20T10:00:00.000000Z"


def test_ledger_enforces_resource_bounds():
    ledger = LifecycleLedger("life-1", max_events=1)
    ledger.append(e(
        event_id="one",
        phase="INTENT",
        event_time="2026-09-20T10:00:00Z",
        epistemic_state="OBSERVED",
    ))
    with pytest.raises(LifecycleValidationError, match="event limit"):
        ledger.append(e(
            event_id="two",
            phase="OBSERVATION",
            event_time="2026-09-20T10:00:00Z",
            epistemic_state="OBSERVED",
        ))


def test_ledger_rejects_parent_fan_in_over_limit():
    ledger = LifecycleLedger("life-1", max_parents=1)
    for event_id in ("p1", "p2"):
        ledger.append(e(
            event_id=event_id,
            phase="OBSERVATION",
            event_time="2026-09-20T10:00:00Z",
            epistemic_state="OBSERVED",
        ))
    with pytest.raises(LifecycleValidationError, match="parent event limit"):
        ledger.append(e(
            event_id="child-many",
            phase="RECONSTRUCTION",
            event_time="2026-09-20T10:00:00Z",
            parent_event_ids=["p1", "p2"],
            epistemic_state="INFERRED",
        ))


def test_later_backfilled_evidence_cannot_rewrite_historical_horizon():
    ledger = LifecycleLedger("life-1")
    late_record = e(
        event_id="backfilled",
        phase="EVIDENCE_STATE",
        actor="provider",
        event_time="2026-09-20T10:01:00Z",
        recorded_at="2026-09-20T10:08:00Z",
        epistemic_state="ATTESTED",
        payload={
            "available_to": ["agent-a"],
            "available_at": "2026-09-20T10:01:00Z",
        },
    )
    ledger.append(late_record)
    assert ledger.evidence_horizon(
        actor="agent-a",
        decision_time="2026-09-20T10:05:00Z",
    ) == ()


def test_non_allow_with_false_consultation_claim_is_invalid():
    ledger = LifecycleLedger("life-1")
    ledger.append(_decision(
        required=(),
        consulted=("missing-evidence",),
        decision="BLOCK",
    ))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "INVALID"


def test_profiled_evidence_cannot_claim_availability_after_record_creation():
    with pytest.raises(LifecycleValidationError, match="available_at cannot be after recorded_at"):
        e(
            event_id="future-availability",
            phase="EVIDENCE_STATE",
            actor="sensor",
            event_time="2026-09-20T10:00:00Z",
            recorded_at="2026-09-20T10:01:00Z",
            epistemic_state="OBSERVED",
            payload={
                "profile": "ddc.evidence-state.v1",
                "available_to": ["agent-a"],
                "available_at": "2026-09-20T10:02:00Z",
                "evidence_created_at": "2026-09-20T10:01:00Z",
                "availability": {
                    "existed": True,
                    "reachable": True,
                    "discoverable": True,
                    "fresh": True,
                    "accessible": True,
                    "trusted": True,
                },
            },
        )


def test_action_receipt_bridge_keeps_artifact_as_separate_boundary():
    digest = "sha256:" + "a" * 64
    event = action_receipt_reference(
        lifecycle_id="life-1",
        event_id="receipt-1",
        actor="gate-a",
        event_time="2026-09-20T10:05:00Z",
        recorded_at="2026-09-20T10:05:00Z",
        receipt_digest=digest,
        decision="ALLOW",
    )
    assert event.phase == "ACTION_RECEIPT"
    assert event.evidence_refs == (digest,)
    assert event.payload["artifact_type"] == "ddc-action-receipt"


def test_replay_bridge_appends_reconstruction_without_mutating_source():
    ledger = LifecycleLedger("life-1")
    source = e(
        event_id="execution-unknown",
        phase="EXECUTION",
        event_time="2026-09-20T10:06:00Z",
        recorded_at="2026-09-20T10:06:00Z",
        epistemic_state="UNKNOWN",
        payload={"status": "UNKNOWN"},
    )
    ledger.append(source)
    report_digest = "sha256:" + "b" * 64
    replay = replay_reconstruction_reference(
        lifecycle_id="life-1",
        event_id="replay-1",
        actor="agent-replay",
        event_time="2026-09-20T10:06:00Z",
        recorded_at="2026-09-20T10:10:00Z",
        report_digest=report_digest,
        parent_event_ids=["execution-unknown"],
        consequence_status="SUCCEEDED",
        decision_status="JUSTIFIED",
    )
    ledger.append(replay)
    assert ledger.get("execution-unknown").payload["status"] == "UNKNOWN"
    assert ledger.latest_reconstruction().payload["consequence_status"] == "SUCCEEDED"


def test_interop_bridge_rejects_non_digest_reference():
    with pytest.raises(LifecycleValidationError, match="sha256"):
        action_receipt_reference(
            lifecycle_id="life-1",
            event_id="bad-receipt",
            actor="gate-a",
            event_time="2026-09-20T10:05:00Z",
            recorded_at="2026-09-20T10:05:00Z",
            receipt_digest="not-a-digest",
            decision="ALLOW",
        )


def test_jsonl_import_has_byte_limit():
    with pytest.raises(LifecycleValidationError, match="byte limit"):
        loads_jsonl(" " * 64, max_bytes=16)


def test_profiled_decision_does_not_treat_unprofiled_evidence_as_fully_usable():
    ledger = LifecycleLedger("life-1")
    ledger.append(e(
        event_id="ev-1",
        phase="EVIDENCE_STATE",
        actor="sensor",
        event_time="2026-09-20T10:01:00Z",
        recorded_at="2026-09-20T10:01:00Z",
        epistemic_state="OBSERVED",
        payload={
            "available_to": ["agent-a"],
            "available_at": "2026-09-20T10:01:00Z",
        },
    ))
    ledger.append(_decision())
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "INVALID"
    assert assessment.unusable_consulted_event_ids == ("ev-1",)


def test_independent_confirmation_counts_groups_not_records():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence(
        event_id="ev-1",
        independence_group="provider-a",
    ))
    ledger.append(_profile_evidence(
        event_id="ev-2",
        independence_group="provider-a",
    ))
    ledger.append(_decision(
        required=("ev-1", "ev-2"),
        consulted=("ev-1", "ev-2"),
        minimum_independent_sources=2,
    ))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.independent_source_groups == ("provider-a",)
    assert assessment.independence_shortfall == 1
    assert assessment.status == "INVALID"


def test_two_independent_source_groups_can_satisfy_requirement():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence(
        event_id="ev-1",
        independence_group="provider-a",
    ))
    ledger.append(_profile_evidence(
        event_id="ev-2",
        independence_group="provider-b",
    ))
    ledger.append(_decision(
        required=("ev-1", "ev-2"),
        consulted=("ev-1", "ev-2"),
        minimum_independent_sources=2,
    ))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.independence_shortfall == 0
    assert assessment.status == "VALID"


def test_contaminated_evidence_cannot_silently_support_allow():
    ledger = LifecycleLedger("life-1")
    retry = e(
        event_id="retry-1",
        phase="DISPATCH",
        event_time="2026-09-20T10:00:30Z",
        recorded_at="2026-09-20T10:00:30Z",
        epistemic_state="OBSERVED",
    )
    ledger.append(retry)
    ledger.append(_profile_evidence(
        event_id="ev-1",
        available_at="2026-09-20T10:01:00Z",
        created_at="2026-09-20T10:01:00Z",
        contamination=("retry-1",),
        independence_group="provider-a",
    ))
    ledger.append(_decision())
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.contaminated_consulted_event_ids == ("ev-1",)
    assert assessment.status == "INVALID"


def test_contamination_reference_must_exist():
    ledger = LifecycleLedger("life-1")
    evidence = _profile_evidence(
        contamination=("missing-retry",),
    )
    with pytest.raises(LifecycleValidationError, match="unknown contaminating event"):
        ledger.append(evidence)


def test_public_conformance_vector():
    root = Path(__file__).resolve().parents[1]
    ledger = loads_jsonl(
        (root / "conformance" / "valid-profiled-allow-v0.1.jsonl").read_text()
    )
    expected = json.loads(
        (root / "conformance" / "valid-profiled-allow-v0.1.expected.json").read_text()
    )
    assessment = assess_decision(ledger, expected["decision_event_id"])
    transition = next_transition_admissibility(
        ledger, expected["decision_event_id"]
    )
    assert assessment.status == expected["expected_assessment_status"]
    assert transition["disposition"] == expected["expected_next_transition"]
    assert list(assessment.independent_source_groups) == expected[
        "expected_independent_source_groups"
    ]
    assert assessment.independence_shortfall == expected[
        "expected_independence_shortfall"
    ]


def test_admissibility_event_closes_decision_to_execution_loop():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    ledger.append(_decision())
    gate = admissibility_event(
        ledger,
        "decision-1",
        event_id="admissibility-1",
        actor="physical-gate",
        recorded_at="2026-09-20T10:05:01Z",
    )
    ledger.append(gate)
    assert gate.phase == "ADMISSIBILITY"
    assert gate.payload["disposition"] == "ALLOW"
    assert gate.payload["decision_event_id"] == "decision-1"
    assert gate.evidence_refs == (ledger.get("decision-1").digest,)


def test_checkpoint_binds_complete_event_set():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    checkpoint = ledger.checkpoint()
    ledger.verify_checkpoint(checkpoint)

    ledger.append(_decision())
    with pytest.raises(LifecycleValidationError, match="does not match lifecycle"):
        ledger.verify_checkpoint(checkpoint)


def test_checkpoint_detects_root_tampering():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    checkpoint = ledger.checkpoint()
    checkpoint["root"] = "sha256:" + "0" * 64
    with pytest.raises(LifecycleValidationError, match="root mismatch"):
        ledger.verify_checkpoint(checkpoint)


def test_jsonl_rejects_duplicate_keys():
    raw = '{"lifecycle_id":"a","lifecycle_id":"b"}\n'
    with pytest.raises(LifecycleValidationError, match="duplicate JSON key"):
        loads_jsonl(raw)


def test_jsonl_rejects_nonfinite_constants():
    raw = '{"x":NaN}\n'
    with pytest.raises(LifecycleValidationError, match="non-finite"):
        loads_jsonl(raw)


def test_evidence_bundle_is_deterministic_and_bound_to_checkpoint():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence(independence_group="provider-a"))
    ledger.append(_decision(minimum_independent_sources=1))
    bundle = build_evidence_bundle(ledger)
    verify_evidence_bundle(ledger, bundle)

    again = build_evidence_bundle(ledger)
    assert bundle == again
    assert bundle["checkpoint"] == ledger.checkpoint()
    assert bundle["decisions"][0]["assessment"]["status"] == "VALID"
    assert bundle["decisions"][0]["next_transition"]["disposition"] == "ALLOW"
    assert bundle["bundle_digest"].startswith("sha256:")


def test_evidence_bundle_detects_lifecycle_change():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence(independence_group="provider-a"))
    bundle = build_evidence_bundle(ledger)

    ledger.append(_decision(
        required=("ev-1",),
        consulted=("ev-1",),
        minimum_independent_sources=1,
    ))
    with pytest.raises(LifecycleValidationError, match="does not match lifecycle"):
        verify_evidence_bundle(ledger, bundle)


def _channel_event(*, event_id="channel-1", state="HEALTHY",
                   recorded_at="2026-09-20T10:00:30Z",
                   visible_to=("agent-a",), latency=100, max_latency=1000):
    return e(
        event_id=event_id,
        phase="EVIDENCE_CHANNEL",
        actor="provider-channel",
        event_time=recorded_at,
        recorded_at=recorded_at,
        epistemic_state="OBSERVED",
        payload={
            "profile": "ddc.evidence-channel.v1",
            "channel_id": "provider-status",
            "state": state,
            "visible_to": list(visible_to),
            "delivery_latency_ms": latency,
            "max_delivery_latency_ms": max_latency,
            "provenance_event_ids": [],
        },
    )


def test_healthy_evidence_channel_can_support_profiled_allow():
    ledger = LifecycleLedger("life-1")
    channel = _channel_event()
    ledger.append(channel)
    ledger.append(_profile_evidence(channel_event_id=channel.event_id))
    ledger.append(_decision(require_channel_assurance=True))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "VALID"
    assert assessment.evidence_channel_status == "ADEQUATE"
    assert assessment.channel_event_ids == ("channel-1",)


def test_degraded_evidence_channel_is_separate_failure_dimension():
    ledger = LifecycleLedger("life-1")
    channel = _channel_event(state="DEGRADED")
    ledger.append(channel)
    ledger.append(_profile_evidence(channel_event_id=channel.event_id))
    ledger.append(_decision(require_channel_assurance=True))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "INVALID"
    assert assessment.evidence_channel_status == "INADEQUATE"
    assert assessment.inadequate_channel_event_ids == ("channel-1",)
    assert "evidence channel was inadequate at decision time" in assessment.reasons


def test_required_channel_assurance_fails_closed_when_missing():
    ledger = LifecycleLedger("life-1")
    ledger.append(_profile_evidence())
    ledger.append(_decision(require_channel_assurance=True))
    assessment = assess_decision(ledger, "decision-1")
    assert assessment.status == "INVALID"
    assert assessment.evidence_channel_status == "UNKNOWN"
    assert assessment.missing_channel_assurance_event_ids == ("ev-1",)


def test_channel_state_at_preserves_historical_actor_view():
    ledger = LifecycleLedger("life-1")
    ledger.append(_channel_event(
        event_id="channel-early",
        state="HEALTHY",
        recorded_at="2026-09-20T10:01:00Z",
    ))
    ledger.append(_channel_event(
        event_id="channel-late",
        state="DEGRADED",
        recorded_at="2026-09-20T10:08:00Z",
    ))
    historical = channel_state_at(
        ledger,
        channel_id="provider-status",
        actor="agent-a",
        decision_time="2026-09-20T10:05:00Z",
    )
    assert historical is not None
    assert historical.channel_event_id == "channel-early"
    assert historical.status == "ADEQUATE"


def test_channel_latency_policy_can_make_healthy_transport_inadequate():
    event = _channel_event(latency=1500, max_latency=1000)
    assessment = assess_channel_event(event)
    assert assessment.status == "INADEQUATE"
    assert "latency" in assessment.reasons[0]


def test_typed_relationship_does_not_claim_causality_from_chronology():
    ledger = LifecycleLedger("life-1")
    attempt = e(
        event_id="attempt-a",
        phase="EXECUTION",
        event_time="2026-09-20T10:01:00Z",
        recorded_at="2026-09-20T10:01:00Z",
        epistemic_state="OBSERVED",
    )
    later = e(
        event_id="later-record",
        phase="OBSERVATION",
        event_time="2026-09-20T10:08:00Z",
        recorded_at="2026-09-20T10:08:00Z",
        epistemic_state="ATTESTED",
    )
    ledger.append(attempt)
    ledger.append(later)
    relation = relationship_event(
        ledger,
        event_id="rel-1",
        actor="agent-replay",
        relation_type="SUPPORTED_BY",
        source_event_id="attempt-a",
        target_event_id="later-record",
        recorded_at="2026-09-20T10:09:00Z",
        claim_scope=("attempt reconstruction support",),
    )
    ledger.append(relation)
    assert relation.parent_event_ids == ()
    assert relation.payload["relation_type"] == "SUPPORTED_BY"
    assert relation.payload["source_event_id"] == "attempt-a"
    assert relation.payload["target_event_id"] == "later-record"


def test_bundle_is_canonical_across_independent_ingestion_order():
    first = e(
        event_id="a",
        phase="OBSERVATION",
        event_time="2026-09-20T10:00:00Z",
        recorded_at="2026-09-20T10:00:00Z",
        epistemic_state="OBSERVED",
    )
    second = e(
        event_id="b",
        phase="OBSERVATION",
        event_time="2026-09-20T10:00:00Z",
        recorded_at="2026-09-20T10:00:00Z",
        epistemic_state="OBSERVED",
    )
    left = LifecycleLedger("life-1")
    left.append(first)
    left.append(second)
    right = LifecycleLedger("life-1")
    right.append(second)
    right.append(first)
    assert build_evidence_bundle(left) == build_evidence_bundle(right)
