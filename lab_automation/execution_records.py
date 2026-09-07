"""Shared execution records for StockVis Lab Automation.

A Run is a logical unit of work. An Invocation is one physical model/tool/backend
attempt within that Run. Retries and replications must not overwrite each other.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4


EXECUTION_INTENTS = {
    "primary",
    "retry",
    "replication",
    "accidental_duplicate",
    "unknown",
}


@dataclass(frozen=True)
class InvocationRecord:
    run_id: str
    actor: str
    backend: str
    execution_intent: str = "primary"
    invocation_id: str = field(default_factory=lambda: str(uuid4()))
    parent_invocation_id: str | None = None
    input_snapshot_ref: str | None = None
    output_ref: str | None = None
    requested_identity: str | None = None
    returned_identity: str | None = None
    identity_assurance: str = "unknown"
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: str | None = None
    status: str = "started"
    finish_reason: str | None = None
    returncode: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.execution_intent not in EXECUTION_INTENTS:
            raise ValueError(f"invalid execution_intent: {self.execution_intent}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
