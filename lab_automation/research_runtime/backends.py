"""Configurable model/tool backends for Research Runtime vertical slices.

The first implementation deliberately keeps the contract small: a backend
receives a role-scoped structured request, executes one isolated invocation,
and returns both raw execution material and an optional parsed JSON object.
Model/provider choice is configuration, not Research Lab semantic authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any, Mapping, Protocol


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BackendRequest:
    role: str
    run_id: str
    instruction: str
    payload: Mapping[str, Any]
    response_contract: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render_prompt(self) -> str:
        envelope = {
            "role": self.role,
            "instruction": self.instruction,
            "input": dict(self.payload),
            "response_contract": dict(self.response_contract),
        }
        return (
            "You are executing one bounded StockVis Research Runtime role.\n"
            "Return ONLY one valid JSON object. Do not use markdown fences, commentary, "
            "or hidden fields outside the declared response contract.\n\n"
            + json.dumps(envelope, ensure_ascii=False, indent=2, default=str)
        )


@dataclass(frozen=True)
class BackendExecution:
    backend: str
    requested_identity: str
    identity_assurance: str
    status: str
    raw_stdout: str
    raw_stderr: str
    parsed_output: Mapping[str, Any] | None
    command: tuple[str, ...] = field(default_factory=tuple)
    returncode: int | None = None
    started_at: str = field(default_factory=_utc_now)
    ended_at: str | None = None
    returned_identity: str | None = None
    finish_reason: str | None = None
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResearchBackend(Protocol):
    def execute(self, request: BackendRequest) -> BackendExecution: ...


@dataclass(frozen=True)
class CommandBackendConfig:
    command: tuple[str, ...]
    backend_name: str = "command_json"
    requested_identity: str = "command/unknown"
    identity_assurance: str = "requested_only"
    timeout_seconds: float = 300.0
    cwd: str | None = None
    extra_env: Mapping[str, str] = field(default_factory=dict)


class CommandJSONBackend:
    """Subprocess backend that requires the final stdout to be one JSON object."""

    def __init__(self, config: CommandBackendConfig):
        self.config = config

    def execute(self, request: BackendRequest) -> BackendExecution:
        started = _utc_now()
        prompt = request.render_prompt()
        env = os.environ.copy()
        env.update({str(k): str(v) for k, v in self.config.extra_env.items()})
        env["STOCKVIS_RESEARCH_ROLE"] = request.role
        env["STOCKVIS_RESEARCH_RUN_ID"] = request.run_id
        cwd = self.config.cwd or None
        try:
            proc = subprocess.run(
                list(self.config.command),
                cwd=cwd,
                input=prompt,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
                timeout=self.config.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return BackendExecution(
                backend=self.config.backend_name,
                requested_identity=self.config.requested_identity,
                identity_assurance=self.config.identity_assurance,
                status="timed_out",
                raw_stdout=exc.stdout or "",
                raw_stderr=exc.stderr or "",
                parsed_output=None,
                command=self.config.command,
                returncode=None,
                started_at=started,
                ended_at=_utc_now(),
                finish_reason="timeout",
                error=f"timeout after {self.config.timeout_seconds}s",
            )

        ended = _utc_now()
        if proc.returncode != 0:
            return BackendExecution(
                backend=self.config.backend_name,
                requested_identity=self.config.requested_identity,
                identity_assurance=self.config.identity_assurance,
                status="failed",
                raw_stdout=proc.stdout,
                raw_stderr=proc.stderr,
                parsed_output=None,
                command=self.config.command,
                returncode=proc.returncode,
                started_at=started,
                ended_at=ended,
                finish_reason="nonzero_returncode",
                error=f"backend exited with returncode {proc.returncode}",
            )

        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            return BackendExecution(
                backend=self.config.backend_name,
                requested_identity=self.config.requested_identity,
                identity_assurance=self.config.identity_assurance,
                status="invalid_output",
                raw_stdout=proc.stdout,
                raw_stderr=proc.stderr,
                parsed_output=None,
                command=self.config.command,
                returncode=proc.returncode,
                started_at=started,
                ended_at=ended,
                finish_reason="invalid_json",
                error=f"stdout was not one valid JSON object: {exc}",
            )
        if not isinstance(parsed, dict):
            return BackendExecution(
                backend=self.config.backend_name,
                requested_identity=self.config.requested_identity,
                identity_assurance=self.config.identity_assurance,
                status="invalid_output",
                raw_stdout=proc.stdout,
                raw_stderr=proc.stderr,
                parsed_output=None,
                command=self.config.command,
                returncode=proc.returncode,
                started_at=started,
                ended_at=ended,
                finish_reason="non_object_json",
                error="stdout JSON must be an object",
            )
        return BackendExecution(
            backend=self.config.backend_name,
            requested_identity=self.config.requested_identity,
            identity_assurance=self.config.identity_assurance,
            status="completed",
            raw_stdout=proc.stdout,
            raw_stderr=proc.stderr,
            parsed_output=parsed,
            command=self.config.command,
            returncode=proc.returncode,
            started_at=started,
            ended_at=ended,
            finish_reason="completed",
        )


def _tuple_command(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(shlex.split(value))
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return tuple(value)
    raise ValueError("backend command must be a string or list[str]")


def load_command_backend(config_path: Path, role: str) -> CommandJSONBackend:
    """Load one role backend from a shared JSON configuration file."""
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if raw.get("backend_type", "command_json") != "command_json":
        raise ValueError("v0.1 supports backend_type=command_json only")
    merged: dict[str, Any] = dict(raw.get("default", {}))
    merged.update(raw.get("roles", {}).get(role, {}))
    if "command" not in merged:
        raise ValueError(f"no command configured for role: {role}")
    config = CommandBackendConfig(
        command=_tuple_command(merged["command"]),
        backend_name=str(merged.get("backend_name", "command_json")),
        requested_identity=str(merged.get("requested_identity", f"{role}/unknown")),
        identity_assurance=str(merged.get("identity_assurance", "requested_only")),
        timeout_seconds=float(merged.get("timeout_seconds", 300.0)),
        cwd=(
            str((config_path.parent / merged["cwd"]).resolve())
            if merged.get("cwd") and not Path(str(merged["cwd"])).is_absolute()
            else merged.get("cwd")
        ),
        extra_env={str(k): str(v) for k, v in merged.get("extra_env", {}).items()},
    )
    return CommandJSONBackend(config)
