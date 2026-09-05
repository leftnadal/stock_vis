"""Append-only JSONL ledger for StockVis Lab Automation runs.

The ledger is operational history, not Lab epistemic authority. Existing events
are never rewritten; corrections are appended as new events that reference the
superseded event when needed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


@dataclass(frozen=True)
class RunEvent:
    job_id: str
    run_id: str
    stage: str
    status: str
    actor: str
    runner_version: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    base_sha: str | None = None
    candidate_sha: str | None = None
    authority_refs: tuple[str, ...] = field(default_factory=tuple)
    artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    test_summary: str = ""
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    supersedes_event_id: str | None = None


class AppendOnlyLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: RunEvent) -> None:
        payload = asdict(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
