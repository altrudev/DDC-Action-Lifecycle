import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "al-001-v02-action-ir.json"
ACTION_SCHEMA = ROOT / "schema" / "action-ir.schema.json"
DELTA_SCHEMA = ROOT / "schema" / "frequency-delta.schema.json"
GATE_SCHEMA = ROOT / "schema" / "transition-gate.schema.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v02_contracts_are_self_consistent():
    data = load(FIXTURE)
    action_schema = load(ACTION_SCHEMA)
    delta_schema = load(DELTA_SCHEMA)
    gate_schema = load(GATE_SCHEMA)

    action = data["action_ir"]
    delta = data["delta"]
    gate = data["gate"]

    for field in action_schema["required"]:
        assert field in action, f"ActionIR missing {field}"

    assert action["authority"]["status"] in action_schema["properties"]["authority"]["properties"]["status"]["enum"]
    assert len(action["evidence_horizon"]["sha256"]) == 64
    assert action["recoverability"]["status"] == "VERIFIED"

    for field in delta_schema["required"]:
        assert field in delta, f"FrequencyDelta missing {field}"

    allowed_impact = set(delta_schema["properties"]["impact"]["enum"])
    assert delta["impact"] in allowed_impact
    assert delta["changed_dimensions"]["target_state"] is True
    assert delta["changed_dimensions"]["evidence"] is True

    for field in gate_schema["required"]:
        assert field in gate, f"TransitionGate missing {field}"

    assert gate["delta_ref"] == delta["delta_id"]
    assert gate["action_id"] == action["action_id"]
    assert gate["transition_id"] == action["transition_id"]
    assert gate["decision"] == "RECHECK"

    resonance = gate["resonance"]
    assert resonance["overall"] == "RESONANT"
    assert resonance["dimensions"]["temporal"] == "DRIFTED"
    assert resonance["dimensions"]["effect"] == "UNKNOWN"

    # Frequency principle: semantic identity may remain stable while temporal
    # conditions change enough to require a fresh decision boundary.
    assert resonance["overall"] == "RESONANT"
    assert delta["impact"] == "RECHECK_REQUIRED"
    assert gate["decision"] == "RECHECK"


def test_runtime_validity_is_separate_from_action_validity():
    data = load(FIXTURE)
    action = data["action_ir"]

    assert action["authority"]["status"] == "VALID"
    assert action["runtime_context"]["health"] == "HEALTHY"

    degraded = json.loads(json.dumps(action))
    degraded["runtime_context"]["health"] = "DEGRADED"

    assert degraded["authority"]["status"] == "VALID"
    assert degraded["runtime_context"]["health"] == "DEGRADED"


if __name__ == "__main__":
    test_v02_contracts_are_self_consistent()
    test_runtime_validity_is_separate_from_action_validity()
    print("DDC Action Lifecycle v0.2 architecture PASS")
