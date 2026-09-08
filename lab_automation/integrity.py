"""Shared runtime integrity checks for StockVis Lab Automation.

These checks protect execution provenance and artifact integrity. They do not
replace Lab-specific epistemic or design evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
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


def validate_json_artifact(
    path: Path,
    *,
    reject_empty_object: bool = False,
) -> IntegrityFinding:
    """Validate JSON syntax and the non-empty result-object invariant."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return IntegrityFinding(
            code="json_artifact",
            status="FAIL",
            message=f"{path.name} contains invalid JSON: {exc}",
        )
    if reject_empty_object and payload == {}:
        return IntegrityFinding(
            code="json_artifact",
            status="FAIL",
            message=f"{path.name} must not be an empty JSON object",
        )
    return IntegrityFinding(
        code="json_artifact",
        status="PASS",
        message=f"parsed valid JSON artifact: {path.name}",
    )


def validate_nonempty_text_artifact(path: Path) -> IntegrityFinding:
    """Reject an executor report that exists but contains no text."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return IntegrityFinding(
            code="text_artifact",
            status="FAIL",
            message=f"{path.name} could not be read as UTF-8 text: {exc}",
        )
    if not text.strip():
        return IntegrityFinding(
            code="text_artifact",
            status="FAIL",
            message=f"{path.name} must not be empty",
        )
    return IntegrityFinding(
        code="text_artifact",
        status="PASS",
        message=f"read non-empty text artifact: {path.name}",
    )
