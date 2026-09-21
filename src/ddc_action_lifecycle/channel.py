from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .ledger import LifecycleEvent, LifecycleLedger, LifecycleValidationError, _parse_time


CHANNEL_PROFILE = "ddc.evidence-channel.v1"
CHANNEL_STATES = {
    "HEALTHY",
    "DEGRADED",
    "STALE",
    "UNREACHABLE",
    "UNTRUSTED",
    "UNKNOWN",
}


@dataclass(frozen=True)
class ChannelAssessment:
    channel_event_id: str
    channel_id: str
    status: str
    state: str
    reasons: tuple[str, ...]
    delivery_latency_ms: int | None
    max_delivery_latency_ms: int | None
    observed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_event_id": self.channel_event_id,
            "channel_id": self.channel_id,
            "status": self.status,
            "state": self.state,
            "reasons": list(self.reasons),
            "delivery_latency_ms": self.delivery_latency_ms,
            "max_delivery_latency_ms": self.max_delivery_latency_ms,
            "observed_at": self.observed_at,
        }


def assess_channel_event(event: LifecycleEvent) -> ChannelAssessment:
    if event.phase != "EVIDENCE_CHANNEL":
        raise LifecycleValidationError(
            "channel assessment target must be an EVIDENCE_CHANNEL event"
        )
    if event.payload.get("profile") != CHANNEL_PROFILE:
        raise LifecycleValidationError(
            "channel event does not use ddc.evidence-channel.v1"
        )

    channel_id = event.payload["channel_id"]
    state = event.payload["state"]
    delivery_latency_ms = event.payload.get("delivery_latency_ms")
    max_delivery_latency_ms = event.payload.get("max_delivery_latency_ms")
    reasons: list[str] = []

    if state != "HEALTHY":
        reasons.append(f"channel state is {state}")

    if (
        delivery_latency_ms is not None
        and max_delivery_latency_ms is not None
        and delivery_latency_ms > max_delivery_latency_ms
    ):
        reasons.append("channel delivery latency exceeded policy bound")

    status = "ADEQUATE" if not reasons else "INADEQUATE"
    return ChannelAssessment(
        channel_event_id=event.event_id,
        channel_id=channel_id,
        status=status,
        state=state,
        reasons=tuple(reasons),
        delivery_latency_ms=delivery_latency_ms,
        max_delivery_latency_ms=max_delivery_latency_ms,
        observed_at=event.recorded_at,
    )


def channel_state_at(
    ledger: LifecycleLedger,
    *,
    channel_id: str,
    actor: str,
    decision_time: str,
) -> ChannelAssessment | None:
    cutoff = _parse_time(decision_time)
    candidates: list[LifecycleEvent] = []
    for event in ledger.events:
        if event.phase != "EVIDENCE_CHANNEL":
            continue
        if event.payload.get("profile") != CHANNEL_PROFILE:
            continue
        if event.payload.get("channel_id") != channel_id:
            continue
        visible_to = event.payload.get("visible_to", ())
        if not isinstance(visible_to, (tuple, list)) or actor not in visible_to:
            continue
        if _parse_time(event.recorded_at) <= cutoff:
            candidates.append(event)

    if not candidates:
        return None

    selected = max(
        candidates,
        key=lambda item: (_parse_time(item.recorded_at), item.event_id),
    )
    return assess_channel_event(selected)
