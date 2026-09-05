#!/usr/bin/env bash
set -euo pipefail

# StockVis Lab Automation — first guarded job launcher
# Default behavior: preflight + dry-run only.
# Real execution requires explicit --execute.

REPO_ROOT="$(git rev-parse --show-toplevel)"
JOB_FILE="${STOCKVIS_LAB_JOB_FILE:-$REPO_ROOT/lab_automation/jobs/math_daily_price_readiness.example.json}"
WORKTREE_ROOT="${STOCKVIS_LAB_WORKTREE_ROOT:-$HOME/.stockvis-lab-automation/worktrees}"
STATE_ROOT="${STOCKVIS_LAB_STATE_ROOT:-$HOME/.stockvis-lab-automation}"
MODE="dry-run"

if [[ "${1:-}" == "--execute" ]]; then
  MODE="execute"
fi

cd "$REPO_ROOT"

# Force PostgreSQL sessions created by child processes into read-only mode.
# A dedicated DB read-only role is still recommended as the stronger control.
export PGOPTIONS="${PGOPTIONS:-} -c default_transaction_read_only=on -c statement_timeout=15000"
export STOCKVIS_LAB_DB_ACCESS="read_only"

# Prefer dedicated lab DB credentials when supplied; mirror them into the
# project's existing DB_* settings interface without storing secrets in Git.
if [[ -n "${STOCKVIS_LAB_DB_USER:-}" ]]; then export DB_USER="$STOCKVIS_LAB_DB_USER"; fi
if [[ -n "${STOCKVIS_LAB_DB_PASSWORD:-}" ]]; then export DB_PASSWORD="$STOCKVIS_LAB_DB_PASSWORD"; fi
if [[ -n "${STOCKVIS_LAB_DB_HOST:-}" ]]; then export DB_HOST="$STOCKVIS_LAB_DB_HOST"; fi
if [[ -n "${STOCKVIS_LAB_DB_PORT:-}" ]]; then export DB_PORT="$STOCKVIS_LAB_DB_PORT"; fi

mkdir -p "$WORKTREE_ROOT" "$STATE_ROOT"

# Run through Poetry because the StockVis project declares Python/Django/psycopg2
# dependencies there. The doctor performs no DB writes.
poetry run python -m lab_automation.doctor \
  --repo "$REPO_ROOT" \
  --branch "math-lab/data-eligibility-v0.1"

if [[ "$MODE" == "dry-run" ]]; then
  echo ""
  echo "=== DRY RUN: no worktree, Codex execution, candidate commit, or push ==="
  poetry run python -m lab_automation.local_runner \
    --repo "$REPO_ROOT" \
    --job "$JOB_FILE" \
    --worktree-root "$WORKTREE_ROOT" \
    --state-root "$STATE_ROOT"
  echo ""
  echo "Dry-run completed. Re-run with --execute only after reviewing doctor output."
  exit 0
fi

echo ""
echo "=== RESTRICTED REAL RUN ==="
echo "This may create a LOCAL lab-run/* branch and candidate commit."
echo "It will not push, merge, or deploy."

poetry run python -m lab_automation.local_runner \
  --repo "$REPO_ROOT" \
  --job "$JOB_FILE" \
  --worktree-root "$WORKTREE_ROOT" \
  --state-root "$STATE_ROOT" \
  --execute

echo ""
echo "Runner finished. Inspect $STATE_ROOT/ledger and the local lab-run/* branch."
echo "Do NOT push until CEO approval is recorded for the exact candidate SHA."
