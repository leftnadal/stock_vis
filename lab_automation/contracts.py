"""Shared contracts for StockVis Lab Automation Platform.

These objects describe workflow authority and promotion state only. They do not
replace Lab-specific research/design methodology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class Lab(str, Enum):
    RESEARCH = "research_lab"
    DESIGN = "design_lab"
    MATH = "math_lab"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANDIDATE_READY = "candidate_ready"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class PromotionStage(str, Enum):
    PUSH = "push"
    MERGE = "merge"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"


class ApprovalStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


@dataclass(frozen=True)
class JobEnvelope:
    job_id: str
    lab: Lab
    goal: str
    branch: str
    authority_refs: Tuple[str, ...]
    expected_outputs: Tuple[str, ...]
    allowed_write_paths: Tuple[str, ...]
    db_access: str = "none"
    network_policy: str = "restricted"
    destructive_actions_allowed: bool = False
    status: JobStatus = JobStatus.QUEUED
    parent_job_ids: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CandidateRevision:
    job_id: str
    revision_sha: str
    test_summary: str
    changed_paths: Tuple[str, ...]
    risk_summary: str
    result_manifest_path: str


@dataclass(frozen=True)
class ApprovalRecord:
    job_id: str
    stage: PromotionStage
    revision_sha: str
    status: ApprovalStatus
    approved_by: str | None = None
    note: str = ""


def approval_applies(approval: ApprovalRecord, current_revision_sha: str) -> bool:
    """An approval is valid only for the exact revision it reviewed."""
    return (
        approval.status is ApprovalStatus.APPROVED
        and approval.revision_sha == current_revision_sha
    )


def can_promote(stage: PromotionStage, approval: ApprovalRecord, revision_sha: str) -> bool:
    """Common promotion gate.

    A later stage never inherits approval from an earlier stage. PUSH, MERGE,
    DEPLOY, and ROLLBACK are distinct decisions.
    """
    return approval.stage is stage and approval_applies(approval, revision_sha)
