"""Shared runtime integrity checks for StockVis Lab Automation.

These checks protect execution provenance and artifact integrity. They do not
replace Lab-specific epistemic or design evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from lab_automation.artifact_store import ArtifactRef, LocalArtifactStore


@dataclass(frozen=True)
class IntegrityFinding:
    code: str
    status: str
    message: str


def verify_artifacts(
    store: LocalArtifactStore,
    refs: Iterable[ArtifactRef],
) -> list[IntegrityFinding]:
    findings: list[IntegrityFinding] = []
    for ref in refs:
        ok = store.verify(ref)
        findings.append(
            IntegrityFinding(
                code="artifact_hash",
                status="PASS" if ok else "FAIL",
                message=(
                    f"verified {ref.logical_uri}"
                    if ok
                    else f"missing or hash mismatch: {ref.logical_uri}"
                ),
            )
        )
    return findings


def check_exact_target(
    *,
    expected_run_id: str | None,
    actual_run_id: str | None,
    expected_artifact_hash: str | None = None,
    actual_artifact_hash: str | None = None,
) -> IntegrityFinding:
    if expected_run_id is not None and expected_run_id != actual_run_id:
        return IntegrityFinding(
            code="target_run",
            status="FAIL",
            message=f"expected target run {expected_run_id}, got {actual_run_id}",
        )
    if (
        expected_artifact_hash is not None
        and expected_artifact_hash != actual_artifact_hash
    ):
        return IntegrityFinding(
            code="target_artifact",
            status="FAIL",
            message="target artifact hash mismatch",
        )
    return IntegrityFinding(
        code="exact_target",
        status="PASS",
        message="target identity matches declared expectation",
    )


def require_output_contract(
    origins: dict[str, str],
    required_names: Iterable[str],
) -> IntegrityFinding:
    missing = [
        name
        for name in required_names
        if origins.get(name) != "agent_generated"
    ]
    if missing:
        return IntegrityFinding(
            code="output_contract",
            status="FAIL",
            message=f"required agent outputs were not produced: {missing}",
        )
    return IntegrityFinding(
        code="output_contract",
        status="PASS",
        message="required agent outputs were produced by the agent",
    )
