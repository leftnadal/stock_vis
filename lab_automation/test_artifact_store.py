from pathlib import Path

from lab_automation.artifact_store import LocalArtifactStore


def test_content_addressed_identity_is_stable(tmp_path: Path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    first = store.put_text("same content", kind="test")
    second = store.put_text("same content", kind="other")

    assert first.sha256 == second.sha256
    assert first.logical_uri == second.logical_uri
    assert store.verify(first)


def test_physical_root_does_not_define_logical_identity(tmp_path: Path):
    payload = "portable artifact"
    first_store = LocalArtifactStore(tmp_path / "internal")
    second_store = LocalArtifactStore(tmp_path / "external")

    first = first_store.put_text(payload, kind="test")
    second = second_store.put_text(payload, kind="test")

    assert first.logical_uri == second.logical_uri
    assert first.replicas[0].locator != second.replicas[0].locator


def test_verify_detects_corruption(tmp_path: Path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    ref = store.put_text("original", kind="test")
    store.path_for(ref).write_text("corrupt", encoding="utf-8")

    assert not store.verify(ref)
