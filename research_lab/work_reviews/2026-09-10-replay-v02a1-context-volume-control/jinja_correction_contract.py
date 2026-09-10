#!/usr/bin/env python3
"""Pure contract helpers for the v0.2A.1 Jinja correction lineage."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PYPI_INDEX = "https://pypi.org/simple"
TRANSFORMERS_PIN = "5.16.1"
TOKENIZERS_PIN = "0.23.2"
JINJA2_PIN = "3.1.6"
MARKUPSAFE_PIN = "3.0.2"
CORRECTION_ID = "jinja2-pinned-001"
ORIGINAL_ACQUISITION_ID = "official-pinned-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_command(python: Path, destination: Path) -> list[str]:
    """One official-PyPI request for exactly the predeclared correction wheels."""
    return [
        str(python), "-m", "pip", "download",
        "--dest", str(destination),
        "--only-binary=:all:",
        "--no-deps",
        "--index-url", PYPI_INDEX,
        "--disable-pip-version-check",
        f"Jinja2=={JINJA2_PIN}",
        f"MarkupSafe=={MARKUPSAFE_PIN}",
    ]


def install_command(
    python: Path, original_wheels: Path, correction_wheels: Path,
) -> list[str]:
    """Install the original frozen stack plus correction wheels without network."""
    return [
        str(python), "-m", "pip", "install",
        "--no-index",
        "--find-links", str(original_wheels),
        "--find-links", str(correction_wheels),
        f"transformers=={TRANSFORMERS_PIN}",
        f"tokenizers=={TOKENIZERS_PIN}",
        f"Jinja2=={JINJA2_PIN}",
        f"MarkupSafe=={MARKUPSAFE_PIN}",
    ]


def verify_original_files(manifest_path: Path, artifact_root: Path, key: str) -> list[dict]:
    manifest = json.loads(manifest_path.read_text())
    rows = manifest[key]
    expected = {row.get("filename", row.get("path")): row for row in rows}
    actual = {path.name: path for path in artifact_root.iterdir() if path.is_file()}
    if set(actual) != set(expected):
        raise ValueError("original_artifact_set_mismatch")
    verified = []
    for name in sorted(expected):
        row = expected[name]
        path = actual[name]
        digest = sha256_file(path)
        if path.stat().st_size != row["bytes"] or digest != row["sha256"]:
            raise ValueError("original_artifact_integrity_mismatch:" + name)
        verified.append({"filename": name, "bytes": path.stat().st_size, "sha256": digest})
    return verified


def verify_freeze(freeze: str, original_freeze: list[str]) -> None:
    actual = {line.strip().lower() for line in freeze.splitlines() if line.strip()}
    expected = {line.strip().lower() for line in original_freeze}
    expected.update({
        f"jinja2=={JINJA2_PIN}".lower(),
        f"markupsafe=={MARKUPSAFE_PIN}".lower(),
    })
    if actual != expected:
        raise ValueError("corrected_environment_freeze_mismatch")

