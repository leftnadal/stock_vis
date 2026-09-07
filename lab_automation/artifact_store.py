"""Content-addressed artifact storage for StockVis Lab Automation.

Artifact identity is independent from the current physical storage location.
The first implementation uses a local filesystem backend, but callers should
persist and exchange logical artifact URIs rather than absolute paths.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


RETENTION_CLASSES = {
    "irreplaceable",
    "reconstructable",
    "redownloadable",
    "ephemeral",
}
ARTIFACT_URI_PREFIX = "artifact://sha256/"


@dataclass(frozen=True)
class ArtifactReplica:
    backend: str
    locator: str
    state: str = "verified"


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    sha256: str
    byte_size: int
    kind: str
    logical_uri: str
    retention_class: str
    replicas: tuple[ArtifactReplica, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LocalArtifactStore:
    """Filesystem-backed content-addressed store.

    The same content always receives the same logical identity. Moving the root
    to another disk does not change the logical URI or SHA-256 identity.
    """

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for_digest(self, digest: str) -> Path:
        return self.root / "sha256" / digest[:2] / digest

    @staticmethod
    def _logical_uri(digest: str) -> str:
        return f"{ARTIFACT_URI_PREFIX}{digest}"

    @staticmethod
    def _artifact_id(digest: str) -> str:
        return f"art-sha256-{digest}"

    @staticmethod
    def digest_from_uri(logical_uri: str) -> str:
        if not logical_uri.startswith(ARTIFACT_URI_PREFIX):
            raise ValueError(f"unsupported artifact URI: {logical_uri}")
        digest = logical_uri[len(ARTIFACT_URI_PREFIX) :]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"invalid sha256 artifact URI: {logical_uri}")
        return digest

    def put_bytes(
        self,
        payload: bytes,
        *,
        kind: str,
        retention_class: str = "irreplaceable",
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        if retention_class not in RETENTION_CLASSES:
            raise ValueError(f"invalid retention_class: {retention_class}")
        digest = hashlib.sha256(payload).hexdigest()
        target = self._path_for_digest(digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(payload)
        replica = ArtifactReplica(
            backend="local_filesystem",
            locator=str(target),
            state="verified",
        )
        return ArtifactRef(
            artifact_id=self._artifact_id(digest),
            sha256=digest,
            byte_size=len(payload),
            kind=kind,
            logical_uri=self._logical_uri(digest),
            retention_class=retention_class,
            replicas=(replica,),
            metadata=dict(metadata or {}),
        )

    def put_text(
        self,
        text: str,
        *,
        kind: str,
        retention_class: str = "irreplaceable",
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        return self.put_bytes(
            text.encode("utf-8"),
            kind=kind,
            retention_class=retention_class,
            metadata=metadata,
        )

    def put_json(
        self,
        payload: Any,
        *,
        kind: str,
        retention_class: str = "irreplaceable",
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return self.put_text(
            text,
            kind=kind,
            retention_class=retention_class,
            metadata=metadata,
        )

    def put_file(
        self,
        path: Path,
        *,
        kind: str,
        retention_class: str = "irreplaceable",
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        return self.put_bytes(
            path.read_bytes(),
            kind=kind,
            retention_class=retention_class,
            metadata=metadata,
        )

    def path_for_uri(self, logical_uri: str) -> Path:
        return self._path_for_digest(self.digest_from_uri(logical_uri))

    def read_bytes(self, logical_uri: str) -> bytes:
        return self.path_for_uri(logical_uri).read_bytes()

    def verify_uri(self, logical_uri: str) -> bool:
        digest = self.digest_from_uri(logical_uri)
        target = self._path_for_digest(digest)
        if not target.is_file():
            return False
        return hashlib.sha256(target.read_bytes()).hexdigest() == digest

    def verify(self, ref: ArtifactRef) -> bool:
        return self.verify_uri(ref.logical_uri)

    def path_for(self, ref: ArtifactRef) -> Path:
        return self.path_for_uri(ref.logical_uri)
