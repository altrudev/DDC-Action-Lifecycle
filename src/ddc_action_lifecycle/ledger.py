from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable


PHASES = {
    "INTENT",
    "AUTHORITY",
    "EVIDENCE_STATE",
    "DECISION",
    "ACTION_RECEIPT",
    "DISPATCH",
    "EXECUTION",
    "OBSERVATION",
    "CONSEQUENCE",
    "RECONSTRUCTION",
    "ADMISSIBILITY",
}

EPISTEMIC_STATES = {
    "OBSERVED",
    "ATTESTED",
    "INFERRED",
    "UNPROVEN",
    "ADJUDICATED",
    "UNKNOWN",
}


class LifecycleValidationError(ValueError):
    pass


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise LifecycleValidationError("timestamp must be a non-empty string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleValidationError("timestamp must be RFC3339/ISO-8601") from exc
    if parsed.tzinfo is None:
        raise LifecycleValidationError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _validate_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 2**53 - 1:
            raise LifecycleValidationError(f"{path}: integer exceeds safe JSON range")
        return
    if isinstance(value, float):
        raise LifecycleValidationError(f"{path}: floating point values are not allowed")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise LifecycleValidationError(f"{path}: object keys must be strings")
            _validate_json(item, f"{path}.{key}")
        return
    raise LifecycleValidationError(f"{path}: unsupported JSON value {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    _validate_json(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class LifecycleEvent:
    lifecycle_id: str
    event_id: str
    phase: str
    actor: str
    event_time: str
    recorded_at: str
    parent_event_ids: tuple[str, ...]
    claim_scope: tuple[str, ...]
    epistemic_state: str
    evidence_refs: tuple[str, ...]
    payload: dict[str, Any]
    digest: str

    def core(self) -> dict[str, Any]:
        return {
            "lifecycle_id": self.lifecycle_id,
            "event_id": self.event_id,
            "phase": self.phase,
            "actor": self.actor,
            "event_time": self.event_time,
            "recorded_at": self.recorded_at,
            "parent_event_ids": list(self.parent_event_ids),
            "claim_scope": list(self.claim_scope),
            "epistemic_state": self.epistemic_state,
            "evidence_refs": list(self.evidence_refs),
            "payload": self.payload,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.core(), "digest": self.digest}


def event_digest(core: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(core)).hexdigest()


def create_event(
    *,
    lifecycle_id: str,
    event_id: str,
    phase: str,
    actor: str,
    event_time: str,
    recorded_at: str,
    parent_event_ids: Iterable[str] = (),
    claim_scope: Iterable[str] = (),
    epistemic_state: str = "UNKNOWN",
    evidence_refs: Iterable[str] = (),
    payload: dict[str, Any] | None = None,
) -> LifecycleEvent:
    if phase not in PHASES:
        raise LifecycleValidationError(f"unsupported phase: {phase}")
    if epistemic_state not in EPISTEMIC_STATES:
        raise LifecycleValidationError(f"unsupported epistemic state: {epistemic_state}")
    for name, value in (
        ("lifecycle_id", lifecycle_id),
        ("event_id", event_id),
        ("actor", actor),
    ):
        if not isinstance(value, str) or not value:
            raise LifecycleValidationError(f"{name} must be a non-empty string")

    _parse_time(event_time)
    _parse_time(recorded_at)
    if _parse_time(recorded_at) < _parse_time(event_time):
        raise LifecycleValidationError("recorded_at cannot precede event_time")

    parents = tuple(parent_event_ids)
    if len(parents) != len(set(parents)):
        raise LifecycleValidationError("duplicate parent event id")
    if event_id in parents:
        raise LifecycleValidationError("event cannot parent itself")

    scope = tuple(claim_scope)
    evidence = tuple(evidence_refs)
    body = payload or {}
    _validate_json(body)

    core = {
        "lifecycle_id": lifecycle_id,
        "event_id": event_id,
        "phase": phase,
        "actor": actor,
        "event_time": event_time,
        "recorded_at": recorded_at,
        "parent_event_ids": list(parents),
        "claim_scope": list(scope),
        "epistemic_state": epistemic_state,
        "evidence_refs": list(evidence),
        "payload": body,
    }
    return LifecycleEvent(
        lifecycle_id=lifecycle_id,
        event_id=event_id,
        phase=phase,
        actor=actor,
        event_time=event_time,
        recorded_at=recorded_at,
        parent_event_ids=parents,
        claim_scope=scope,
        epistemic_state=epistemic_state,
        evidence_refs=evidence,
        payload=body,
        digest=event_digest(core),
    )


class LifecycleLedger:
    """Append-only lifecycle graph.

    The ledger never mutates an accepted event. Later evidence and reconstruction
    are appended as new events that may reference earlier events.
    """

    def __init__(self, lifecycle_id: str):
        if not lifecycle_id:
            raise LifecycleValidationError("lifecycle_id is required")
        self.lifecycle_id = lifecycle_id
        self._events: list[LifecycleEvent] = []
        self._by_id: dict[str, LifecycleEvent] = {}

    @property
    def events(self) -> tuple[LifecycleEvent, ...]:
        return tuple(self._events)

    def append(self, event: LifecycleEvent) -> None:
        if event.lifecycle_id != self.lifecycle_id:
            raise LifecycleValidationError("event belongs to another lifecycle")
        if event.event_id in self._by_id:
            raise LifecycleValidationError("duplicate event id")
        if event.digest != event_digest(event.core()):
            raise LifecycleValidationError("event digest mismatch")

        for parent_id in event.parent_event_ids:
            parent = self._by_id.get(parent_id)
            if parent is None:
                raise LifecycleValidationError(f"unknown parent event: {parent_id}")
            if _parse_time(parent.event_time) > _parse_time(event.event_time):
                raise LifecycleValidationError("parent event occurs after child event")

        self._events.append(event)
        self._by_id[event.event_id] = event

    def verify(self) -> None:
        replay = LifecycleLedger(self.lifecycle_id)
        for event in self._events:
            replay.append(event)

    def evidence_horizon(self, *, actor: str, decision_time: str) -> tuple[LifecycleEvent, ...]:
        """Evidence legitimately available to an actor by a historical decision time.

        EVIDENCE_STATE payloads may provide available_to and available_at.
        Later evidence is intentionally excluded even when it describes an earlier event.
        """
        cutoff = _parse_time(decision_time)
        out: list[LifecycleEvent] = []
        for event in self._events:
            if event.phase != "EVIDENCE_STATE":
                continue
            available_to = event.payload.get("available_to", [])
            available_at = event.payload.get("available_at")
            if not isinstance(available_to, list) or actor not in available_to:
                continue
            if not isinstance(available_at, str):
                continue
            if _parse_time(available_at) <= cutoff:
                out.append(event)
        return tuple(out)

    def branches(self) -> dict[str, tuple[LifecycleEvent, ...]]:
        """Return explicit branches without collapsing retry paths."""
        grouped: dict[str, list[LifecycleEvent]] = {}
        for event in self._events:
            branch_id = event.payload.get("branch_id")
            if isinstance(branch_id, str) and branch_id:
                grouped.setdefault(branch_id, []).append(event)
        return {key: tuple(value) for key, value in grouped.items()}

    def latest_reconstruction(self) -> LifecycleEvent | None:
        items = [event for event in self._events if event.phase == "RECONSTRUCTION"]
        if not items:
            return None
        return max(items, key=lambda item: _parse_time(item.recorded_at))
