import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "al-001-mid-run-mutation.json"
SCHEMA = ROOT / "schema" / "action-lifecycle-event.schema.json"


def ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def canonical_digest(evidence_ids):
    encoded = json.dumps(evidence_ids, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def load_schema():
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def events_by_id(data):
    return {event["event_id"]: event for event in data["events"]}


def find_one(data, event_type, branch_id=None):
    found = [
        e for e in data["events"]
        if e["event_type"] == event_type
        and (branch_id is None or e["branch_id"] == branch_id)
    ]
    assert len(found) == 1, f"expected exactly one {event_type} on {branch_id or 'any branch'}, got {len(found)}"
    return found[0]


def test_event_contract_surface():
    data = load_fixture()
    schema = load_schema()

    allowed_types = set(schema["properties"]["event_type"]["enum"])
    allowed_confidence = set(schema["properties"]["confidence_class"]["enum"])
    allowed_status = set(schema["properties"]["status"]["enum"])
    required = set(schema["required"])
    allowed_keys = set(schema["properties"])

    for event in data["events"]:
        assert required <= set(event), f"{event.get('event_id')} missing required fields"
        assert set(event) <= allowed_keys, f"{event['event_id']} contains undeclared top-level fields"
        assert event["event_type"] in allowed_types
        assert event["confidence_class"] in allowed_confidence
        assert event.get("status") in allowed_status


def test_al001_invariants():
    data = load_fixture()
    by_id = events_by_id(data)

    assert len(by_id) == len(data["events"]), "event IDs must be unique"

    for event in data["events"]:
        for parent in event.get("caused_by", []):
            assert parent in by_id, f"{event['event_id']} references missing cause {parent}"
            assert ts(by_id[parent]["recorded_at"]) <= ts(event["recorded_at"]), "cause cannot be recorded after child"

    h0 = data["evidence_horizons"]["H0"]
    h1 = data["evidence_horizons"]["H1"]
    assert h0["evidence_ids"] == ["E0"], "H0 must remain immutable"
    assert "E1" not in h0["evidence_ids"], "later evidence must not be inserted into H0"
    assert set(h1["evidence_ids"]) == {"E0", "E1"}, "H1 must contain E0 and newly reachable E1"
    assert h0["sha256"] == canonical_digest(h0["evidence_ids"])
    assert h1["sha256"] == canonical_digest(h1["evidence_ids"])

    d0 = next(e for e in data["events"] if e.get("payload", {}).get("decision_id") == "D0")
    r0 = next(e for e in data["events"] if e.get("payload", {}).get("receipt_id") == "R0")
    mutation = find_one(data, "WORLD_STATE_MUTATION", "b0")
    dispatch0 = find_one(data, "DISPATCH", "b0")
    execution0 = find_one(data, "EXECUTION", "b0")

    assert d0["evidence_horizon_id"] == "H0"
    assert d0["authority_ref"] == "AUTH-0"
    assert r0["decision_ref"] == "D0"
    assert r0["evidence_horizon_id"] == "H0"
    assert r0["payload"]["horizon_sha256"] == h0["sha256"]
    assert dispatch0["receipt_ref"] == "R0"
    assert dispatch0["event_id"] != execution0["event_id"]
    assert execution0["status"] == "DIVERGED"
    assert mutation["event_id"] in execution0["caused_by"]
    assert dispatch0["event_id"] in execution0["caused_by"]

    e1 = next(
        e for e in data["events"]
        if e["event_type"] == "EVIDENCE" and e["payload"].get("evidence_id") == "E1"
    )
    assert mutation["event_id"] in e1["caused_by"], "E1 must describe the external mutation, not cause it"
    assert ts(e1["payload"]["available_at"]) < ts(dispatch0["recorded_at"])
    assert ts(e1["payload"]["reachable_at"]) > ts(dispatch0["recorded_at"])
    assert ts(e1["payload"]["consulted_at"]) >= ts(e1["payload"]["reachable_at"])

    fork = find_one(data, "BRANCH_FORK", "b1")
    assert data["branches"]["b1"]["fork_event"] == fork["event_id"]
    assert fork["parent_branch_id"] == "b0"
    assert execution0["event_id"] in fork["caused_by"]

    horizon1_event = find_one(data, "EVIDENCE_HORIZON", "b1")
    authority1 = find_one(data, "AUTHORITY", "b1")
    d1 = next(e for e in data["events"] if e.get("payload", {}).get("decision_id") == "D1")
    r1 = next(e for e in data["events"] if e.get("payload", {}).get("receipt_id") == "R1")
    dispatch1 = find_one(data, "DISPATCH", "b1")
    execution1 = find_one(data, "EXECUTION", "b1")

    assert "authority_ref" not in horizon1_event, "evidence horizon must not pre-bind authority"
    assert authority1["authority_ref"] == "AUTH-1"
    assert d1["transition_id"] == "tr-1"
    assert d1["evidence_horizon_id"] == "H1"
    assert d1["authority_ref"] == "AUTH-1"
    assert horizon1_event["event_id"] in d1["caused_by"]
    assert authority1["event_id"] in d1["caused_by"]
    assert r1["decision_ref"] == "D1"
    assert r1["payload"]["horizon_sha256"] == h1["sha256"]
    assert dispatch1["receipt_ref"] == "R1"
    assert dispatch1["event_id"] != execution1["event_id"]
    assert execution1["status"] == "SUCCEEDED"

    observation = find_one(data, "OBSERVATION", "b1")
    consequence = find_one(data, "CONSEQUENCE", "b1")
    assert observation["event_id"] in consequence["caused_by"]

    replay = find_one(data, "REPLAY", "b1")
    assert replay["payload"]["collapsed"] is False
    assert set(replay["payload"]["branches_reconstructed"]) == {"b0", "b1"}

    assessment = find_one(data, "ASSURANCE_ASSESSMENT", "b1")
    assert assessment["payload"]["actor_compliance"] == "VALID"
    assert assessment["payload"]["evidence_channel_adequacy"] == "INADEQUATE"

    admissibility = find_one(data, "ADMISSIBILITY", "b1")
    assert admissibility["payload"]["next_transition"] == "ADMISSIBLE_WITH_CHANNEL_REMEDIATION"
    assert "evidence propagation latency" in admissibility["payload"]["unresolved"]


if __name__ == "__main__":
    test_event_contract_surface()
    test_al001_invariants()
    print("AL-001 PASS")
