from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .ledger import LifecycleEvent, LifecycleLedger, LifecycleValidationError, event_from_dict


def dumps_jsonl(events: Iterable[LifecycleEvent]) -> str:
    return "\n".join(
        json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for event in events
    ) + "\n"


def loads_jsonl(text: str) -> LifecycleLedger:
    ledger: LifecycleLedger | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
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


def load_jsonl(path: str | Path) -> LifecycleLedger:
    return loads_jsonl(Path(path).read_text(encoding="utf-8"))


def save_jsonl(path: str | Path, ledger: LifecycleLedger) -> None:
    ledger.verify()
    Path(path).write_text(dumps_jsonl(ledger.events), encoding="utf-8")
