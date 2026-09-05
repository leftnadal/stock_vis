"""Preflight checks for the StockVis Lab Automation MacBook runner.

This command performs only read-only checks. It never writes to PostgreSQL or
Git remotes. For DB verification it forces PostgreSQL transaction_read_only=on
for the probe connection.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _cmd(command: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _check_binary(name: str, args: list[str]) -> dict:
    path = shutil.which(name)
    if not path:
        return {"name": name, "ok": False, "detail": "not found in PATH"}
    proc = subprocess.run(
        [path, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    text = (proc.stdout or proc.stderr).strip().splitlines()
    return {
        "name": name,
        "ok": proc.returncode == 0,
        "detail": text[0] if text else path,
        "path": path,
    }


def _git_checks(repo: Path, branch: str) -> list[dict]:
    checks: list[dict] = []
    code, out, err = _cmd(["git", "rev-parse", "--show-toplevel"], repo)
    checks.append({"name": "git_repo", "ok": code == 0, "detail": out or err})

    code, out, err = _cmd(["git", "rev-parse", "--verify", branch], repo)
    checks.append({"name": "job_branch_exists", "ok": code == 0, "detail": out or err})

    code, out, err = _cmd(["git", "status", "--porcelain"], repo)
    checks.append(
        {
            "name": "source_checkout_clean",
            "ok": code == 0 and out == "",
            "detail": "clean" if code == 0 and out == "" else (out or err),
            "warning_only": True,
        }
    )
    return checks


def _db_probe() -> dict:
    """Verify connectivity while forcing read-only transaction mode.

    This does not prove the configured DB role lacks all write privileges; a
    dedicated read-only PostgreSQL role remains the stronger control. It does
    prove the probe session itself is read-only.
    """

    try:
        import psycopg2
    except Exception as exc:  # pragma: no cover - environment dependent
        return {
            "name": "postgres_read_only_probe",
            "ok": False,
            "detail": f"psycopg2 import failed: {exc}",
        }

    kwargs = {
        "dbname": os.getenv("DB_NAME", "stock_vis"),
        "user": os.getenv("STOCKVIS_LAB_DB_USER") or os.getenv("DB_USER") or os.getenv("USER"),
        "password": os.getenv("STOCKVIS_LAB_DB_PASSWORD") or os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("STOCKVIS_LAB_DB_HOST") or os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("STOCKVIS_LAB_DB_PORT") or os.getenv("DB_PORT", "5432"),
        "connect_timeout": 5,
        "options": "-c default_transaction_read_only=on -c statement_timeout=5000",
    }
    try:
        with psycopg2.connect(**kwargs) as conn:
            with conn.cursor() as cur:
                cur.execute("SHOW transaction_read_only")
                read_only = cur.fetchone()[0]
                cur.execute("SELECT current_user, current_database()")
                user, database = cur.fetchone()
        return {
            "name": "postgres_read_only_probe",
            "ok": read_only == "on",
            "detail": {
                "transaction_read_only": read_only,
                "user": user,
                "database": database,
                "host": kwargs["host"],
                "port": kwargs["port"],
            },
        }
    except Exception as exc:  # pragma: no cover - environment dependent
        return {
            "name": "postgres_read_only_probe",
            "ok": False,
            "detail": f"connection/probe failed: {type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--branch", default="math-lab/data-eligibility-v0.1")
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    checks = [
        _check_binary("git", ["--version"]),
        _check_binary("python", ["--version"]),
        _check_binary("poetry", ["--version"]),
        _check_binary("codex", ["--version"]),
        *_git_checks(repo, args.branch),
    ]
    if not args.skip_db:
        checks.append(_db_probe())

    hard_failures = [
        check
        for check in checks
        if not check.get("ok") and not check.get("warning_only", False)
    ]
    payload = {
        "ok": not hard_failures,
        "repo": str(repo),
        "branch": args.branch,
        "checks": checks,
        "notes": [
            "DB probe forces transaction_read_only=on for the probe session.",
            "A dedicated PostgreSQL read-only role is still recommended for real runs.",
            "This command never pushes, merges, deploys, or mutates the database.",
        ],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("StockVis Lab Automation doctor")
        for check in checks:
            marker = "OK" if check.get("ok") else ("WARN" if check.get("warning_only") else "FAIL")
            print(f"[{marker}] {check['name']}: {check.get('detail')}")
        print(f"\nOverall: {'READY' if payload['ok'] else 'NOT READY'}")

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
