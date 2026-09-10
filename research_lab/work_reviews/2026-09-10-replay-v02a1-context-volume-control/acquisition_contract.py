#!/usr/bin/env python3
"""Pure validation helpers for the one-attempt tokenizer acquisition."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

MODEL_REPOSITORY = "Qwen/Qwen3.5-122B-A10B"
TRANSFORMERS_PIN = "5.16.1"
TOKENIZERS_PIN = "0.23.2"
PYPI_INDEX = "https://pypi.org/simple"
ACQUISITION_ID = "official-pinned-001"
HF_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_TOKENIZER_FILES = {"tokenizer.json", "tokenizer_config.json"}
OPTIONAL_TOKENIZER_FILES = {
    "added_tokens.json",
    "chat_template.jinja",
    "config.json",
    "generation_config.json",
    "special_tokens_map.json",
}
FORBIDDEN_SUFFIXES = {
    ".bin", ".ckpt", ".gguf", ".h5", ".msgpack", ".onnx", ".ot",
    ".pt", ".pth", ".safetensors",
}
MAX_TOKENIZER_ASSET_BYTES = 100 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pip_download_command(python: Path, wheel_dir: Path) -> list[str]:
    return [
        str(python), "-m", "pip", "download",
        "--dest", str(wheel_dir),
        "--only-binary=:all:",
        "--index-url", PYPI_INDEX,
        "--disable-pip-version-check",
        f"transformers=={TRANSFORMERS_PIN}",
        f"tokenizers=={TOKENIZERS_PIN}",
    ]


def pip_install_command(python: Path, wheel_dir: Path) -> list[str]:
    return [
        str(python), "-m", "pip", "install",
        "--no-index", "--find-links", str(wheel_dir),
        f"transformers=={TRANSFORMERS_PIN}",
        f"tokenizers=={TOKENIZERS_PIN}",
    ]


def select_tokenizer_assets(sibling_names: list[str]) -> list[str]:
    """Return only root-level, explicitly allowed small tokenizer/config files."""
    names = set(sibling_names)
    if not REQUIRED_TOKENIZER_FILES <= names:
        missing = sorted(REQUIRED_TOKENIZER_FILES - names)
        raise ValueError("required_tokenizer_assets_missing:" + ",".join(missing))
    selected = sorted((REQUIRED_TOKENIZER_FILES | OPTIONAL_TOKENIZER_FILES) & names)
    for name in selected:
        path = Path(name)
        if path.name != name or ".." in path.parts or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError("unsafe_tokenizer_asset_name")
    return selected


def validate_revision(revision: str) -> None:
    if not HF_REVISION_RE.fullmatch(revision):
        raise ValueError("immutable_revision_unavailable")


def validate_downloaded_assets(snapshot: Path, selected: list[str]) -> list[dict]:
    rows = []
    for name in selected:
        path = snapshot / name
        if not path.is_file():
            raise ValueError("selected_tokenizer_asset_not_downloaded")
        size = path.stat().st_size
        if size > MAX_TOKENIZER_ASSET_BYTES:
            raise ValueError("tokenizer_asset_exceeds_size_boundary")
        rows.append({"path": name, "bytes": size, "sha256": sha256_file(path)})
    return rows
