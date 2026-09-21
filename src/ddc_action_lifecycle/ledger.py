from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping


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
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise LifecycleValidationError(f"{path}: object keys must be strings")
            _validate_json(item, f"{path}.{key}")
        return
    raise LifecycleValidationError(f"{path}: unsupported JSON value {type(value).__name__}")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    materialized = _thaw_json(value)
    _validate_json(materialized)
    return json.dumps(
        materialized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _strings(name: str, values: Iterable[str]) -> tuple[str, ...]:
    result = tuple(values)
    if any(not isinstance(item, str) or not item for item in result):
        raise LifecycleValidationError(f"{name} must contain non-empty strings")
    if len(result) != len(set(result)):
        raise LifecycleValidationError(f"{name} must not contain duplicates")
    return result


def _validate_profile_payload(phase: str, payload: Mapping[str, Any]) -> None:
    if phase == "EVIDENCE_STATE" and payload.get("profile") == "ddc.evidence-state.v1":
        required = {
            "available_to",
            "available_at",
            "evidence_created_at",
            "availability",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise LifecycleValidationError(
                "evidence-state profile missing: " + ", ".join(missing)
            )
        available_to = payload["available_to"]
        if not isinstance(available_to, (list, tuple)) or not available_to:
            raise LifecycleValidationError("available_to must contain at least one actor")
        if any(not isinstance(actor, str) or not actor for actor in available_to):
            raise LifecycleValidationError("available_to must contain non-empty actor ids")
        available_at = _parse_time(payload["available_at"])
        created_at = _parse_time(payload["evidence_created_at"])
        if created_at > available_at:
            raise LifecycleValidationError(
                "evidence_created_at cannot be after available_at"
            )
        availability = payload["availability"]
        if not isinstance(availability, Mapping):
            raise LifecycleValidationError("availability must be an object")
        required_facets = {
            "existed",
            "reachable",
            "discoverable",
            "fresh",
            "accessible",
            "trusted",
        }
        missing_facets = sorted(required_facets - set(availability))
        if missing_facets:
            raise LifecycleValidationError(
                "availability missing facets: " + ", ".join(missing_facets)
            )
        for facet in required_facets:
            if availability[facet] not in (True, False, None):
                raise LifecycleValidationError(
                    f"availability.{facet} must be true, false, or null"
                )

    if phase == "DECISION" and payload.get("profile") == "ddc.decision-state.v1":
        required = {
            "decision",
            "required_evidence_event_ids",
            "consulted_evidence_event_ids",
            "unresolved_assumptions",
            "contradictions",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise LifecycleValidationError(
                "decision-state profile missing: " + ", ".join(missing)
            )
        if payload["decision"] not in {
            "ALLOW",
            "BLOCK",
            "RECHECK",
            "REQUIRE_HUMAN",
            "SIMULATE_FIRST",
            "UNKNOWN",
        }:
            raise LifecycleValidationError("unsupported decision-state decision")
        for field in ("required_evidence_event_ids", "consulted_evidence_event_ids"):
            value = payload[field]
            if not isinstance(value, (list, tuple)):
                raise LifecycleValidationError(f"{field} must be an array")
            if any(not isinstance(item, str) or not item for item in value):
                raise LifecycleValidationError(f"{field} must contain event ids")
            if len(value) != len(set(value)):
                raise LifecycleValidationError(f"{field} must not contain duplicates")
        for field in ("unresolved_assumptions", "contradictions"):
            value = payload[field]
            if not isinstance(value, (list, tuple)):
                raise LifecycleValidationError(f"{field} must be an array")
            if any(not isinstance(item, str) or not item for item in value):
                raise LifecycleValidationError(f"{field} must contain non-empty strings")


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
    payload: Mapping[str, Any]
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
            "payload": _thaw_json(self.payload),
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

    event_dt = _parse_time(event_time)
    recorded_dt = _parse_time(recorded_at)
    if recorded_dt < event_dt:
        raise LifecycleValidationError("recorded_at cannot precede event_time")

    parents = _strings("parent_event_ids", parent_event_ids)
    if event_id in parents:
        raise LifecycleValidationError("event cannot parent itself")

    scope = _strings("claim_scope", claim_scope)
    evidence = _strings("evidence_refs", evidence_refs)
    body = payload or {}
    if not isinstance(body, dict):
        raise LifecycleValidationError("payload must be an object")
    _validate_json(body)
    _validate_profile_payload(phase, body)

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
        payload=_freeze_json(body),
        digest=event_digest(core),
    )


def event_from_dict(raw: dict[str, Any]) -> LifecycleEvent:
    if not isinstance(raw, dict):
        raise LifecycleValidationError("event must be an object")
    required = {
        "lifecycle_id",
        "event_id",
        "phase",
        "actor",
        "event_time",
        "recorded_at",
        "parent_event_ids",
        "claim_scope",
        "epistemic_state",
        "evidence_refs",
        "payload",
        "digest",
    }
    missing = sorted(required - set(raw))
    extra = sorted(set(raw) - required)
    if missing:
        raise LifecycleValidationError("event missing fields: " + ", ".join(missing))
    if extra:
        raise LifecycleValidationError("event has unknown fields: " + ", ".join(extra))

    event = create_event(
        lifecycle_id=raw["lifecycle_id"],
        event_id=raw["event_id"],
        phase=raw["phase"],
        actor=raw["actor"],
        event_time=raw["event_time"],
        recorded_at=raw["recorded_at"],
        parent_event_ids=raw["parent_event_ids"],
        claim_scope=raw["claim_scope"],
        epistemic_state=raw["epistemic_state"],
        evidence_refs=raw["evidence_refs"],
        payload=raw["payload"],
    )
    if raw["digest"] != event.digest:
        raise LifecycleValidationError("event digest mismatch")
    return event


class LifecycleLedger:
    """Append-only lifecycle graph with historical evidence horizons."""

    def __init__(self, lifecycle_id: str):
        if not lifecycle_id:
            raise LifecycleValidationError("lifecycle_id is required")
        self.lifecycle_id = lifecycle_id
        self._events: list[LifecycleEvent] = []
        self._by_id: dict[str, LifecycleEvent] = {}

    @property
    def events(self) -> tuple[LifecycleEvent, ...]:
        return tuple(self._events)

    def get(self, event_id: str) -> LifecycleEvent:
        try:
            return self._by_id[event_id]
        except KeyError as exc:
            raise LifecycleValidationError(f"unknown event: {event_id}") from exc

    def append(self, event: LifecycleEvent) -> None:
        if event.lifecycle_id != self.lifecycle_id:
            raise LifecycleValidationError("event belongs to another lifecycle")
        if event.event_id in self._by_id:
            raise LifecycleValidationError("duplicate event id")
        if event.digest != event_digest(event.core()):
            raise LifecycleValidationError("event digest mismatch")

        child_event_time = _parse_time(event.event_time)
        child_recorded_at = _parse_time(event.recorded_at)
        for parent_id in event.parent_event_ids:
            parent = self._by_id.get(parent_id)
            if parent is None:
                raise LifecycleValidationError(f"unknown parent event: {parent_id}")
            if _parse_time(parent.event_time) > child_event_time:
                raise LifecycleValidationError("parent event occurs after child event")
            if _parse_time(parent.recorded_at) > child_recorded_at:
                raise LifecycleValidationError(
                    "parent record was not yet recorded when child was recorded"
                )

        self._events.append(event)
        self._by_id[event.event_id] = event

    def verify(self) -> None:
        replay = LifecycleLedger(self.lifecycle_id)
        for event in self._events:
            replay.append(event)

    def evidence_horizon(
        self,
        *,
        actor: str,
        decision_time: str,
    ) -> tuple[LifecycleEvent, ...]:
        """Evidence legitimately available to an actor by a historical decision time."""
        cutoff = _parse_time(decision_time)
        out: list[LifecycleEvent] = []
        for event in self._events:
            if event.phase != "EVIDENCE_STATE":
                continue
            available_to = event.payload.get("available_to", ())
            available_at = event.payload.get("available_at")
            if not isinstance(available_to, (list, tuple)) or actor not in available_to:
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
