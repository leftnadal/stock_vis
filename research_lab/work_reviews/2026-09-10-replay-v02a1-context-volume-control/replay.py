#!/usr/bin/env python3
"""Execute the two sealed v0.2A.1 arms once; no retry or selective rerun."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

import provider_adapter as provider
from completion_contract import classify_response
from replay_protocol import parse_action

SCRIPT_ROOT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("REPLAY_EXPERIMENT_ROOT", SCRIPT_ROOT)).resolve()


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(value))


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def execute():
    plan = json.loads((ROOT / "plan.json").read_text())
    token = os.environ.get("DEEPINFRA_TOKEN") or os.environ.get("DEEP_INFRA_API_KEY")
    if not token:
        token = provider.token_from_file(SCRIPT_ROOT.parents[3] / ".env")
    token = provider.valid_token(token)
    out = ROOT / "executions" / uuid.uuid4().hex
    out.mkdir(parents=True, exist_ok=False)
    ledger = {
        "experiment": plan["experiment"],
        "batch_id": out.name,
        "harness_version": "0.2.1",
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "running",
        "model_invocations": 0,
        "results": [],
    }
    write(out / "manifest.json", ledger)
    try:
        for spec in plan["runs"]:
            run = out / spec["run_id"]
            run.mkdir()
            raw = (ROOT / "visible" / f"{spec['run_id']}.json").read_bytes()
            if sha_bytes(raw) != spec["input_sha256"]:
                raise ValueError("input_hash_mismatch")
            messages = json.loads(raw)
            payload = {key: plan["config"][key] for key in ["model", "temperature", "top_p", "seed", "reasoning"]}
            payload.update({"messages": messages, "max_tokens": 8192, "stream": False, "n": 1})
            write(run / "request-0.json", payload)
            ledger["model_invocations"] += 1
            write(out / "manifest.json", ledger)
            started = time.perf_counter()
            response = provider.sanitize_response(
                provider.post_json(payload, token, plan["config"]["timeout_seconds"]),
                plan["config"]["model"], token,
            )
            latency = time.perf_counter() - started
            write(run / "response-0.json", response)
            completion = classify_response(
                response,
                expected_model=plan["config"]["model"],
                requested_max_tokens=8192,
                parse_action=parse_action,
            )
            final = None
            if completion["protocol_completion"] == "complete":
                final, _ = parse_action(response["answer"])
            result = {
                "run_id": spec["run_id"],
                "condition": spec["condition"],
                "case_id": plan["case"],
                "local_preflight_prompt_tokens": spec["local_prompt_tokens"],
                "provider_reported_prompt_tokens": (response.get("usage") or {}).get("prompt_tokens"),
                "input_sha256": spec["input_sha256"],
                "execution_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "latency_seconds": latency,
                "usage": response.get("usage"),
                "returned_model": response.get("returned_model"),
                "completion": completion,
                "final_output": final,
                "semantic_review": "pending" if final else "unassessed",
                "actual_cost_usd": None,
            }
            write(run / "result.json", result)
            ledger["results"].append({
                "run_id": spec["run_id"],
                "condition": spec["condition"],
                "protocol_completion": completion["protocol_completion"],
                "semantic_review": result["semantic_review"],
            })
            write(out / "manifest.json", ledger)
        ledger["status"] = "execution_finished_pending_review"
        return 0
    except Exception as exc:
        ledger["status"] = "systemic_execution_error"
        ledger["safe_error_type"] = type(exc).__name__
        return 1
    finally:
        ledger["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(out / "manifest.json", ledger)
        print("RESULT_PATH=" + str(out), flush=True)


if __name__ == "__main__":
    raise SystemExit(execute())
