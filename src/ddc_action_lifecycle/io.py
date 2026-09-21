from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .ledger import LifecycleEvent, LifecycleLedger, LifecycleValidationError, event_from_dict

DEFAULT_MAX_JSONL_BYTES = 32 * 1024 * 1024


def _reject_constant(value: str):
    raise ValueError(f"non-finite JSON value is not permitted: {value}")


def _reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def dumps_jsonl(events: Iterable[LifecycleEvent]) -> str:
    return "\n".join(
        json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for event in events
    ) + "\n"


def loads_jsonl(
    text: str,
    *,
    max_bytes: int = DEFAULT_MAX_JSONL_BYTES,
) -> LifecycleLedger:
    if not isinstance(text, str):
        raise LifecycleValidationError("lifecycle JSONL must be text")
    if len(text.encode("utf-8")) > max_bytes:
        raise LifecycleValidationError("lifecycle JSONL byte limit exceeded")
    ledger: LifecycleLedger | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(
                line,
                parse_constant=_reject_constant,
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (json.JSONDecodeError, RecursionError, ValueError) as exc:
            raise LifecycleValidationError(
                f"line {line_no}: invalid JSON: {exc}"
            ) from exc
        event = event_from_dict(raw)
        if ledger is None:
            ledger = LifecycleLedger(event.lifecycle_id)
        ledger.append(event)

    if ledger is None:
        raise LifecycleValidationError("lifecycle JSONL contains no events")
    ledger.verify()
    return ledger


def load_jsonl(
    path: str | Path,
    *,
    max_bytes: int = DEFAULT_MAX_JSONL_BYTES,
) -> LifecycleLedger:
    source = Path(path)
    if source.stat().st_size > max_bytes:
        raise LifecycleValidationError("lifecycle JSONL byte limit exceeded")
    return loads_jsonl(source.read_text(encoding="utf-8"), max_bytes=max_bytes)


def save_jsonl(path: str | Path, ledger: LifecycleLedger) -> None:
    ledger.verify()
    Path(path).write_text(dumps_jsonl(ledger.events), encoding="utf-8")
