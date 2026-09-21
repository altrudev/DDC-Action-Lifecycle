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
    "EVIDENCE_CHANNEL",
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

DEFAULT_MAX_EVENTS = 100_000
DEFAULT_MAX_PARENTS = 64
DEFAULT_MAX_EVENT_BYTES = 1 * 1024 * 1024
DEFAULT_MAX_DEPTH = 128


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


def _validate_json(value: Any, path: str = "$", depth: int = 0) -> None:
    if depth > DEFAULT_MAX_DEPTH:
        raise LifecycleValidationError(f"{path}: JSON nesting exceeds limit")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise LifecycleValidationError(
                f"{path}: unpaired surrogate is not permitted"
            ) from exc
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 2**53 - 1:
            raise LifecycleValidationError(f"{path}: integer exceeds safe JSON range")
        return
    if isinstance(value, float):
        raise LifecycleValidationError(f"{path}: floating point values are not allowed")
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]", depth + 1)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise LifecycleValidationError(f"{path}: object keys must be strings")
            _validate_json(item, f"{path}.{key}", depth + 1)
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


def _utf16_sort_key(value: str) -> bytes:
    try:
        return value.encode("utf-16-be")
    except UnicodeEncodeError as exc:
        raise LifecycleValidationError("unpaired surrogate in object key") from exc


def _encode_canonical(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        try:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except UnicodeEncodeError as exc:
            raise LifecycleValidationError("unpaired surrogate in string") from exc
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode_canonical(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=_utf16_sort_key)
        return "{" + ",".join(
            _encode_canonical(key) + ":" + _encode_canonical(value[key])
            for key in keys
        ) + "}"
    raise LifecycleValidationError(
        f"unsupported canonical value {type(value).__name__}"
    )


def canonical_bytes(value: Any) -> bytes:
    _validate_json(value)
    materialized = _thaw_json(value)
    return _encode_canonical(materialized).encode("utf-8")


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
        if len(available_to) != len(set(available_to)):
            raise LifecycleValidationError("available_to must not contain duplicates")
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
        extra_facets = sorted(set(availability) - required_facets)
        if extra_facets:
            raise LifecycleValidationError(
                "availability has unknown facets: " + ", ".join(extra_facets)
            )
        for facet in required_facets:
            if availability[facet] not in (True, False, None):
                raise LifecycleValidationError(
                    f"availability.{facet} must be true, false, or null"
                )
        independence_group = payload.get("independence_group")
        if independence_group is not None and (
            not isinstance(independence_group, str) or not independence_group
        ):
            raise LifecycleValidationError(
                "independence_group must be a non-empty string or null"
            )
        causal_origin = payload.get("causal_origin_event_id")
        if causal_origin is not None and (
            not isinstance(causal_origin, str) or not causal_origin
        ):
            raise LifecycleValidationError(
                "causal_origin_event_id must be a non-empty string or null"
            )
        for field in (
            "transformation_chain",
            "source_authority_scope",
            "contamination_from_event_ids",
        ):
            value = payload.get(field, ())
            if not isinstance(value, (list, tuple)):
                raise LifecycleValidationError(f"{field} must be an array")
            if any(not isinstance(item, str) or not item for item in value):
                raise LifecycleValidationError(
                    f"{field} must contain non-empty strings"
                )
            if (
                field == "contamination_from_event_ids"
                and len(value) != len(set(value))
            ):
                raise LifecycleValidationError(
                    "contamination_from_event_ids must not contain duplicates"
                )

    if phase == "EVIDENCE_CHANNEL" and payload.get("profile") == "ddc.evidence-channel.v1":
        required = {"channel_id", "state", "visible_to"}
        missing = sorted(required - set(payload))
        if missing:
            raise LifecycleValidationError(
                "evidence-channel profile missing: " + ", ".join(missing)
            )
        if not isinstance(payload["channel_id"], str) or not payload["channel_id"]:
            raise LifecycleValidationError("channel_id must be a non-empty string")
        if payload["state"] not in {
            "HEALTHY", "DEGRADED", "STALE", "UNREACHABLE", "UNTRUSTED", "UNKNOWN"
        }:
            raise LifecycleValidationError("unsupported evidence channel state")
        visible_to = payload["visible_to"]
        if not isinstance(visible_to, (list, tuple)) or not visible_to:
            raise LifecycleValidationError("visible_to must contain at least one actor")
        if any(not isinstance(actor, str) or not actor for actor in visible_to):
            raise LifecycleValidationError("visible_to must contain non-empty actor ids")
        if len(visible_to) != len(set(visible_to)):
            raise LifecycleValidationError("visible_to must not contain duplicates")
        for field in ("delivery_latency_ms", "max_delivery_latency_ms"):
            value = payload.get(field)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                raise LifecycleValidationError(f"{field} must be a non-negative integer or null")
        provenance = payload.get("provenance_event_ids", ())
        if not isinstance(provenance, (list, tuple)):
            raise LifecycleValidationError("provenance_event_ids must be an array")
        if any(not isinstance(item, str) or not item for item in provenance):
            raise LifecycleValidationError("provenance_event_ids must contain event ids")
        if len(provenance) != len(set(provenance)):
            raise LifecycleValidationError("provenance_event_ids must not contain duplicates")

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
        minimum_independent = payload.get("minimum_independent_sources", 0)
        if (
            not isinstance(minimum_independent, int)
            or isinstance(minimum_independent, bool)
            or minimum_independent < 0
            or minimum_independent > 64
        ):
            raise LifecycleValidationError(
                "minimum_independent_sources must be an integer from 0 to 64"
            )


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
    event_time = event_dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
    recorded_at = recorded_dt.isoformat(timespec="microseconds").replace("+00:00", "Z")

    parents = _strings("parent_event_ids", parent_event_ids)
    if event_id in parents:
        raise LifecycleValidationError("event cannot parent itself")

    scope = _strings("claim_scope", claim_scope)
    evidence = _strings("evidence_refs", evidence_refs)
    if not isinstance(payload, (dict, type(None))):
        raise LifecycleValidationError("payload must be an object")
    body = dict(payload or {})
    _validate_json(body)
    _validate_profile_payload(phase, body)
    if phase == "EVIDENCE_STATE" and body.get("profile") == "ddc.evidence-state.v1":
        available_dt = _parse_time(body["available_at"])
        created_dt = _parse_time(body["evidence_created_at"])
        if available_dt > recorded_dt:
            raise LifecycleValidationError(
                "available_at cannot be after recorded_at"
            )
        if created_dt > recorded_dt:
            raise LifecycleValidationError(
                "evidence_created_at cannot be after recorded_at"
            )
        body["available_at"] = available_dt.isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
        body["evidence_created_at"] = created_dt.isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")

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

    def __init__(
        self,
        lifecycle_id: str,
        *,
        max_events: int = DEFAULT_MAX_EVENTS,
        max_parents: int = DEFAULT_MAX_PARENTS,
        max_event_bytes: int = DEFAULT_MAX_EVENT_BYTES,
    ):
        if not lifecycle_id:
            raise LifecycleValidationError("lifecycle_id is required")
        if max_events < 1 or max_parents < 1 or max_event_bytes < 1:
            raise LifecycleValidationError("ledger limits must be positive")
        self.lifecycle_id = lifecycle_id
        self.max_events = max_events
        self.max_parents = max_parents
        self.max_event_bytes = max_event_bytes
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
        if len(self._events) >= self.max_events:
            raise LifecycleValidationError("lifecycle event limit exceeded")
        if len(event.parent_event_ids) > self.max_parents:
            raise LifecycleValidationError("parent event limit exceeded")
        if len(canonical_bytes(event.to_dict())) > self.max_event_bytes:
            raise LifecycleValidationError("event byte limit exceeded")
        if event.lifecycle_id != self.lifecycle_id:
            raise LifecycleValidationError("event belongs to another lifecycle")
        if event.event_id in self._by_id:
            raise LifecycleValidationError("duplicate event id")
        if event.digest != event_digest(event.core()):
            raise LifecycleValidationError("event digest mismatch")

        child_event_time = _parse_time(event.event_time)
        child_recorded_at = _parse_time(event.recorded_at)

        if event.phase == "EVIDENCE_CHANNEL" and event.payload.get("profile") == "ddc.evidence-channel.v1":
            for provenance_id in event.payload.get("provenance_event_ids", ()):
                provenance_event = self._by_id.get(provenance_id)
                if provenance_event is None:
                    raise LifecycleValidationError(
                        f"unknown channel provenance event: {provenance_id}"
                    )
                if _parse_time(provenance_event.recorded_at) > child_recorded_at:
                    raise LifecycleValidationError(
                        "channel provenance event was not yet recorded"
                    )

        if event.phase == "EVIDENCE_STATE" and event.payload.get("profile") == "ddc.evidence-state.v1":
            causal_origin = event.payload.get("causal_origin_event_id")
            if causal_origin is not None:
                if not isinstance(causal_origin, str) or not causal_origin:
                    raise LifecycleValidationError("causal_origin_event_id must be an event id or null")
                origin = self._by_id.get(causal_origin)
                if origin is None:
                    raise LifecycleValidationError(
                        f"unknown causal origin event: {causal_origin}"
                    )
                if _parse_time(origin.recorded_at) > child_recorded_at:
                    raise LifecycleValidationError(
                        "causal origin was not yet recorded"
                    )

            contamination = event.payload.get("contamination_from_event_ids", ())
            if not isinstance(contamination, (list, tuple)):
                raise LifecycleValidationError(
                    "contamination_from_event_ids must be an array"
                )
            if len(contamination) != len(set(contamination)):
                raise LifecycleValidationError(
                    "contamination_from_event_ids must not contain duplicates"
                )
            for contaminating_id in contamination:
                if not isinstance(contaminating_id, str) or not contaminating_id:
                    raise LifecycleValidationError(
                        "contamination_from_event_ids must contain event ids"
                    )
                contaminating = self._by_id.get(contaminating_id)
                if contaminating is None:
                    raise LifecycleValidationError(
                        f"unknown contaminating event: {contaminating_id}"
                    )
                if _parse_time(contaminating.recorded_at) > child_recorded_at:
                    raise LifecycleValidationError(
                        "contaminating event was not yet recorded"
                    )

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
        replay = LifecycleLedger(
            self.lifecycle_id,
            max_events=self.max_events,
            max_parents=self.max_parents,
            max_event_bytes=self.max_event_bytes,
        )
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
            if (
                _parse_time(available_at) <= cutoff
                and _parse_time(event.recorded_at) <= cutoff
            ):
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
        return max(
            items,
            key=lambda item: (_parse_time(item.recorded_at), item.event_id),
        )

    def checkpoint(self, *, previous_root: str | None = None) -> dict[str, Any]:
        """Commit to the complete current event set.

        External signing or transparency registration is required to make omission
        detectable to another party.
        """
        entries = [
            {
                "recorded_at": event.recorded_at,
                "event_id": event.event_id,
                "digest": event.digest,
            }
            for event in sorted(
                self._events,
                key=lambda item: (_parse_time(item.recorded_at), item.event_id),
            )
        ]
        core = {
            "profile": "ddc.lifecycle-checkpoint.v1",
            "lifecycle_id": self.lifecycle_id,
            "event_count": len(entries),
            "entries": entries,
            "previous_root": previous_root,
        }
        return {
            **core,
            "root": "sha256:" + hashlib.sha256(canonical_bytes(core)).hexdigest(),
        }

    def verify_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        if not isinstance(checkpoint, dict):
            raise LifecycleValidationError("checkpoint must be an object")
        root = checkpoint.get("root")
        core = {key: value for key, value in checkpoint.items() if key != "root"}
        expected = "sha256:" + hashlib.sha256(canonical_bytes(core)).hexdigest()
        if root != expected:
            raise LifecycleValidationError("checkpoint root mismatch")
        current = self.checkpoint(previous_root=checkpoint.get("previous_root"))
        if checkpoint != current:
            raise LifecycleValidationError("checkpoint does not match lifecycle")
