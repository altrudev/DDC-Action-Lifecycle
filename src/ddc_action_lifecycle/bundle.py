from __future__ import annotations

import hashlib
from typing import Any

from .assurance import assess_decision, next_transition_admissibility
from .ledger import LifecycleLedger, canonical_bytes


BUNDLE_PROFILE = "ddc.lifecycle-evidence-bundle.v1"


def build_evidence_bundle(ledger: LifecycleLedger) -> dict[str, Any]:
    """Build a deterministic customer/auditor-facing evidence bundle.

    This is a summary/commitment artifact, not a replacement for source events.
    """
    ledger.verify()

    canonical_events = sorted(
        ledger.events,
        key=lambda event: (event.recorded_at, event.event_id),
    )

    decisions = []
    for event in canonical_events:
        if (
            event.phase == "DECISION"
            and event.payload.get("profile") == "ddc.decision-state.v1"
        ):
            assessment = assess_decision(ledger, event.event_id)
            decisions.append({
                "assessment": assessment.to_dict(),
                "next_transition": next_transition_admissibility(
                    ledger, event.event_id
                ),
            })

    latest = ledger.latest_reconstruction()
    checkpoint = ledger.checkpoint()

    core = {
        "profile": BUNDLE_PROFILE,
        "lifecycle_id": ledger.lifecycle_id,
        "event_count": len(ledger.events),
        "event_digests": [event.digest for event in canonical_events],
        "checkpoint": checkpoint,
        "branches": {
            key: [
                event.event_id
                for event in sorted(value, key=lambda item: (item.recorded_at, item.event_id))
            ]
            for key, value in sorted(ledger.branches().items())
        },
        "decisions": decisions,
        "latest_reconstruction": (
            latest.to_dict() if latest is not None else None
        ),
        "limitations": [
            "Event integrity does not independently prove actor identity.",
            "Event integrity does not independently prove legal authority.",
            "Event integrity does not independently prove source honesty or trusted time.",
            "Dispatch or execution evidence does not by itself prove downstream consequence.",
            "Independent signing or transparency anchoring is required to make checkpoint omission externally detectable.",
        ],
    }
    return {
        **core,
        "bundle_digest": "sha256:"
        + hashlib.sha256(canonical_bytes(core)).hexdigest(),
    }


def verify_evidence_bundle(
    ledger: LifecycleLedger,
    bundle: dict[str, Any],
) -> None:
    expected = build_evidence_bundle(ledger)
    if bundle != expected:
        from .ledger import LifecycleValidationError

        raise LifecycleValidationError(
            "evidence bundle does not match lifecycle"
        )
