#!/usr/bin/env bash
set -euo pipefail

# StockVis Research Runtime — guarded first model-backed vertical slice launcher.
# This script performs no git push/merge/deploy and writes runtime state outside
# the repository by default.

REPO_ROOT="$(git rev-parse --show-toplevel)"
EXPECTED_BRANCH="lab-automation/bootstrap-v0.1"
CONFIG_PATH="${1:-$REPO_ROOT/lab_automation/research_runtime/model_backend.example.json}"
STATE_ROOT="${STOCKVIS_LAB_STATE_ROOT:-$HOME/.stockvis-lab-automation}"

cd "$REPO_ROOT"

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
  echo "ERROR: expected branch $EXPECTED_BRANCH, found $CURRENT_BRANCH" >&2
  echo "Use the dedicated stock_vis_lab_automation worktree before running this script." >&2
  exit 10
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: automation worktree is not clean. Commit/stash/review local changes first." >&2
  git status --short >&2
  exit 11
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "ERROR: backend config not found: $CONFIG_PATH" >&2
  exit 12
fi

if ! command -v poetry >/dev/null 2>&1; then
  echo "ERROR: poetry not found in PATH" >&2
  exit 13
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: codex CLI not found in PATH" >&2
  exit 14
fi

mkdir -p "$STATE_ROOT"

echo "=== Research Runtime model-backed vertical slice preflight ==="
echo "repo:        $REPO_ROOT"
echo "branch:      $CURRENT_BRANCH"
echo "commit:      $(git rev-parse HEAD)"
echo "config:      $CONFIG_PATH"
echo "state root:  $STATE_ROOT"
echo "codex:       $(codex --version 2>&1 | head -1)"
echo ""

echo "=== Unit tests ==="
poetry run python -m pytest \
  lab_automation/test_artifact_store.py \
  lab_automation/test_execution_records.py \
  lab_automation/test_ledger.py \
  lab_automation/test_local_runner.py \
  lab_automation/research_runtime/test_preflight.py \
  lab_automation/research_runtime/test_profile_io.py \
  lab_automation/research_runtime/test_vertical_slice.py \
  lab_automation/research_runtime/test_backends.py \
  lab_automation/research_runtime/test_model_vertical_slice.py \
  -q

echo ""
echo "=== Deterministic fixture sanity check ==="
poetry run python -m lab_automation.research_runtime.vertical_slice \
  --state-root "$STATE_ROOT" >/tmp/stockvis-research-fixture-summary.json
cat /tmp/stockvis-research-fixture-summary.json

echo ""
echo "=== First real command-backed synthetic run ==="
set +e
poetry run python -m lab_automation.research_runtime.model_vertical_slice \
  --config "$CONFIG_PATH" \
  --state-root "$STATE_ROOT"
MODEL_RC=$?
set -e

echo ""
echo "=== Run inspection pointers ==="
SUMMARY_ROOT="$STATE_ROOT/research_runtime/SV-RES-RUNTIME-MODEL-E2E-001"
if [[ -d "$SUMMARY_ROOT" ]]; then
  LATEST_SUMMARY="$(find "$SUMMARY_ROOT" -name summary.json -type f -print 2>/dev/null | while read -r f; do printf '%s %s\n' "$(stat -f '%m' "$f" 2>/dev/null || stat -c '%Y' "$f")" "$f"; done | sort -nr | head -1 | cut -d' ' -f2-)"
  if [[ -n "${LATEST_SUMMARY:-}" ]]; then
    echo "latest summary: $LATEST_SUMMARY"
  else
    echo "latest summary: none (the run may have failed before summary creation)"
  fi
else
  echo "latest summary: none (no model experiment summary directory yet)"
fi

LATEST_LEDGER="$(find "$STATE_ROOT/ledger" -name 'SV-RES-RUNTIME-MODEL-E2E-001-*.jsonl' -type f -print 2>/dev/null | while read -r f; do printf '%s %s\n' "$(stat -f '%m' "$f" 2>/dev/null || stat -c '%Y' "$f")" "$f"; done | sort -nr | head -1 | cut -d' ' -f2-)"
if [[ -n "${LATEST_LEDGER:-}" ]]; then
  echo "latest ledger:  $LATEST_LEDGER"
  echo "last ledger events:"
  tail -5 "$LATEST_LEDGER"
fi

echo "artifact root:  $STATE_ROOT/artifacts/sha256"
echo ""

if [[ "$MODEL_RC" -ne 0 ]]; then
  echo "MODEL RUN DID NOT COMPLETE SUCCESSFULLY (exit $MODEL_RC)." >&2
  echo "This is acceptable for the first adapter probe. Preserve the ledger/artifacts and inspect raw stdout/stderr before changing parsing." >&2
  exit "$MODEL_RC"
fi

echo "MODEL RUN COMPLETED. Review summary, evaluator output, benchmark, integrity findings, and invocation identities before drawing any model-quality conclusion."
