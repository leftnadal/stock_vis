"""GitHub Issue intake adapter for StockVis Lab Automation Platform.

This module deliberately keeps GitHub as a coordination surface, not the
canonical runtime ledger. It uses the local `gh` CLI so credentials remain on
the MacBook and are not embedded in job files.

v0.1 behavior:
- list open issues carrying `lab-automation` + `queued`
- parse exactly one fenced YAML job block from the issue body
- atomically claim an issue by replacing `queued` with `running`
- materialize a local JSON job file
- never execute push/merge/deploy itself
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - doctor handles this
    yaml = None


JOB_BLOCK_RE = re.compile(r"```ya?ml\s*(.*?)```", re.DOTALL | re.IGNORECASE)
REQUIRED_JOB_KEYS = {"job_id", "lab", "status", "branch", "goal"}


def _run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def _gh(repo_slug: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["gh", *args, "--repo", repo_slug], check=check)


def parse_job_body(body: str) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required for GitHub Issue job intake")
    matches = JOB_BLOCK_RE.findall(body or "")
    if len(matches) != 1:
        raise ValueError(f"expected exactly one fenced YAML job block, found {len(matches)}")
    raw = yaml.safe_load(matches[0])
    if not isinstance(raw, dict):
        raise ValueError("job YAML must decode to an object")
    missing = REQUIRED_JOB_KEYS - set(raw)
    if missing:
        raise ValueError(f"job YAML missing required keys: {sorted(missing)}")
    if raw["status"] != "queued":
        raise ValueError("issue job must have status=queued before claim")

    execution = raw.pop("execution", {}) or {}
    promotion = raw.pop("promotion", {}) or {}
    raw["db_access"] = execution.get("db_access", "none")
    raw["network_policy"] = execution.get("network_policy", "restricted")
    raw["destructive_actions_allowed"] = bool(execution.get("destructive_actions_allowed", False))
    raw["runner"] = execution.get("runner")
    raw["agent"] = execution.get("agent")
    raw["promotion"] = promotion
    raw.setdefault("authority_refs", [])
    raw.setdefault("allowed_write_paths", [])
    raw.setdefault("expected_outputs", [])
    raw.setdefault("parent_job_ids", [])
    raw.setdefault("codex_command", ["codex", "exec", "-"])
    raw.setdefault("test_commands", [])
    return raw


def list_queued_issues(repo_slug: str, limit: int = 20) -> list[dict[str, Any]]:
    proc = _gh(
        repo_slug,
        "issue",
        "list",
        "--state",
        "open",
        "--label",
        "lab-automation",
        "--label",
        "queued",
        "--limit",
        str(limit),
        "--json",
        "number,title,body,labels,url,updatedAt",
    )
    return json.loads(proc.stdout or "[]")


def _label_names(issue: dict[str, Any]) -> set[str]:
    labels = issue.get("labels") or []
    return {label.get("name") for label in labels if isinstance(label, dict) and label.get("name")}


def validate_queue_issue(issue: dict[str, Any]) -> None:
    labels = _label_names(issue)
    if "lab-automation" not in labels or "queued" not in labels:
        raise ValueError("issue is not an eligible queued lab-automation issue")
    if "running" in labels:
        raise ValueError("issue already carries running label")


def claim_issue(repo_slug: str, issue_number: int) -> None:
    # GitHub issue labels are the coordination lock in v0.1. The runner first
    # removes queued and then adds running. Duplicate execution is also blocked
    # locally by the claim file written before the job runs.
    _gh(repo_slug, "issue", "edit", str(issue_number), "--remove-label", "queued")
    _gh(repo_slug, "issue", "edit", str(issue_number), "--add-label", "running")


def materialize_job(issue: dict[str, Any], state_root: Path) -> Path:
    validate_queue_issue(issue)
    raw = parse_job_body(issue.get("body") or "")
    issue_number = int(issue["number"])
    raw["source_issue_number"] = issue_number
    raw["source_issue_url"] = issue.get("url")

    jobs_dir = state_root / "jobs"
    claims_dir = state_root / "claims"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    claims_dir.mkdir(parents=True, exist_ok=True)

    claim_path = claims_dir / f"issue-{issue_number}.claim"
    try:
        fd = claim_path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise RuntimeError(f"local duplicate-claim guard exists: {claim_path}") from exc
    with fd:
        fd.write(json.dumps({"issue_number": issue_number, "job_id": raw["job_id"]}, ensure_ascii=False))

    job_path = jobs_dir / f"{raw['job_id']}.json"
    job_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return job_path


def update_issue_result(repo_slug: str, issue_number: int, *, status: str, summary: str) -> None:
    if status not in {"waiting-for-push-approval", "failed", "aborted"}:
        raise ValueError(f"unsupported issue terminal status: {status}")
    _gh(repo_slug, "issue", "edit", str(issue_number), "--remove-label", "running", check=False)
    _gh(repo_slug, "issue", "edit", str(issue_number), "--add-label", status)
    _gh(
        repo_slug,
        "issue",
        "comment",
        str(issue_number),
        "--body",
        summary,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-slug", default="leftnadal/stock_vis")
    parser.add_argument("--state-root", type=Path, default=Path.home() / ".stockvis-lab-automation")
    parser.add_argument("--issue", type=int, help="claim one explicit issue number")
    parser.add_argument("--list", action="store_true", help="list eligible queued issues only")
    parser.add_argument("--claim", action="store_true", help="materialize and mark running")
    args = parser.parse_args()

    issues = list_queued_issues(args.repo_slug)
    if args.issue is not None:
        issues = [row for row in issues if int(row["number"]) == args.issue]
        if not issues:
            print(f"queued issue #{args.issue} not found", file=sys.stderr)
            return 2

    if args.list or not args.claim:
        for issue in issues:
            print(f"#{issue['number']} {issue['title']}")
        if not args.claim:
            return 0

    if len(issues) != 1:
        print("claim requires exactly one queued issue; use --issue NUMBER", file=sys.stderr)
        return 2

    issue = issues[0]
    job_path = materialize_job(issue, args.state_root)
    try:
        claim_issue(args.repo_slug, int(issue["number"]))
    except Exception:
        # Local claim intentionally remains as evidence of an incomplete claim.
        raise
    print(job_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
