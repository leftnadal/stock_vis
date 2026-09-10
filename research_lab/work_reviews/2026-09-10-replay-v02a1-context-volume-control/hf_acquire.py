#!/usr/bin/env python3
"""Acquire the declared official tokenizer revision and minimum assets once."""
from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
from pathlib import Path

from acquisition_contract import (
    MODEL_REPOSITORY, select_tokenizer_assets, validate_downloaded_assets,
    validate_revision,
)


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().model_info(MODEL_REPOSITORY, revision="main", files_metadata=True)
    if info.id != MODEL_REPOSITORY or getattr(info, "author", "Qwen") != "Qwen":
        raise ValueError("official_repository_identity_mismatch")
    revision = str(info.sha)
    validate_revision(revision)
    names = [item.rfilename for item in info.siblings]
    selected = select_tokenizer_assets(names)
    snapshot = args.external_root / "tokenizer_snapshot"
    returned = Path(snapshot_download(
        repo_id=MODEL_REPOSITORY,
        revision=revision,
        allow_patterns=selected,
        local_dir=snapshot,
    )).resolve()
    if returned != snapshot.resolve():
        raise ValueError("unexpected_snapshot_location")
    assets = validate_downloaded_assets(snapshot, selected)
    for row in assets:
        row["canonical_locator"] = (
            f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/{revision}/{row['path']}"
        )
    result = {
        "status": "tokenizer_assets_acquired",
        "acquired_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository": MODEL_REPOSITORY,
        "repository_provider": "Hugging Face official Qwen repository",
        "repository_locator": f"https://huggingface.co/{MODEL_REPOSITORY}/tree/{revision}",
        "requested_revision": "main",
        "immutable_revision": revision,
        "selected_files": selected,
        "assets": assets,
        "model_weights_downloaded": False,
        "trust_remote_code": False,
        "python": sys.version,
        "platform": platform.platform(),
        "snapshot_path": str(snapshot.resolve()),
    }
    args.output.write_text(dump(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
