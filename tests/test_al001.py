import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "al-001-mid-run-mutation.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def events_by_id(data):
    return {event["event_id"]: event for event in data["events"]}


def find_event(data, event_type, branch_id=None):
    found = [
        e for e in data["events"]
        if e["event_type"] == event_type
        and (branch_id is None or e["branch_id"] == branch_id)
    ]
    assert found, f"missing {event_type} on {branch_id or 'any branch'}"
    return found


def test_al001_invariants():
    data = load_fixture()
    by_id = events_by_id(data)

    assert len(by_id) == len(data["events"]), "event IDs must be unique"

    h0 = data["evidence_horizons"]["H0"]
    h1 = data["evidence_horizons"]["H1"]
    assert h0 == ["E0"], "H0 must remain immutable"
    assert "E1" not in h0, "later evidence must not be inserted into H0"
    assert set(h1) == {"E0", "E1"}, "H1 must include the newly reachable evidence"

    d0 = next(e for e in data["events"] if e.get("payload", {}).get("decision_id") == "D0")
    r0 = next(e for e in data["events"] if e.get("payload", {}).get("receipt_id") == "R0")
    dispatch = find_event(data, "DISPATCH", "b0")[0]
    execution0 = find_event(data, "EXECUTION", "b0")[0]

    assert d0["evidence_horizon_id"] == "H0"
    assert r0["decision_ref"] == "D0"
    assert r0["evidence_horizon_id"] == "H0"
    assert dispatch["receipt_ref"] == "R0"
    assert dispatch["event_id"] != execution0["event_id"]
    assert execution0["status"] == "DIVERGED"

    fork = find_event(data, "BRANCH_FORK", "b1")[0]
    assert fork["parent_branch_id"] == "b0"
    assert "ev-009" in fork["caused_by"]

    recovery_decision = next(e for e in data["events"] if e.get("payload", {}).get("decision_id") == "D1")
    assert recovery_decision["transition_id"] == "tr-1"
    assert recovery_decision["evidence_horizon_id"] == "H1"
    assert recovery_decision["authority_ref"] == "AUTH-1"

    replay = find_event(data, "REPLAY", "b1")[0]
    assert replay["payload"]["collapsed"] is False
    assert set(replay["payload"]["branches_reconstructed"]) == {"b0", "b1"}

    assessment = find_event(data, "ASSURANCE_ASSESSMENT", "b1")[0]
    assert assessment["payload"]["actor_compliance"] == "VALID"
    assert assessment["payload"]["evidence_channel_adequacy"] == "INADEQUATE"

    e1 = next(
        e for e in data["events"]
        if e["event_type"] == "EVIDENCE" and e["payload"].get("evidence_id") == "E1"
    )
    assert e1["payload"]["available_at"] < dispatch["recorded_at"]
    assert e1["payload"]["reachable_at"] > dispatch["recorded_at"]


if __name__ == "__main__":
    test_al001_invariants()
    print("AL-001 PASS")
