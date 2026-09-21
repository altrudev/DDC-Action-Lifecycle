from __future__ import annotations

import argparse
import json
import sys

from .assurance import assess_decision, next_transition_admissibility
from .bundle import build_evidence_bundle
from .io import load_jsonl
from .ledger import LifecycleValidationError


def _summary(ledger):
    phases = {}
    for event in ledger.events:
        phases[event.phase] = phases.get(event.phase, 0) + 1
    latest = ledger.latest_reconstruction()
    return {
        "valid": True,
        "lifecycle_id": ledger.lifecycle_id,
        "event_count": len(ledger.events),
        "phases": phases,
        "branches": {
            key: [event.event_id for event in value]
            for key, value in ledger.branches().items()
        },
        "latest_reconstruction_event_id": latest.event_id if latest else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ddc-lifecycle")
    sub = parser.add_subparsers(dest="cmd", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("jsonl")

    summary = sub.add_parser("summary")
    summary.add_argument("jsonl")

    decision = sub.add_parser("assess-decision")
    decision.add_argument("jsonl")
    decision.add_argument("event_id")

    bundle = sub.add_parser("bundle")
    bundle.add_argument("jsonl")

    args = parser.parse_args(argv)
    try:
        ledger = load_jsonl(args.jsonl)
        if args.cmd == "validate":
            result = {"valid": True, "lifecycle_id": ledger.lifecycle_id}
        elif args.cmd == "summary":
            result = _summary(ledger)
        elif args.cmd == "assess-decision":
            assessment = assess_decision(ledger, args.event_id)
            result = {
                "assessment": assessment.to_dict(),
                "next_transition": next_transition_admissibility(
                    ledger, args.event_id
                ),
            }
        else:
            result = build_evidence_bundle(ledger)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (LifecycleValidationError, OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
