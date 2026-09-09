# Replay 0.1.1 working recovery candidate

Original candidate c5f1c67f8c38ad29f6ea69a53ff616abf2cb5908 is preserved.
Original batch: 0b5220e04007446695d092f763b72020.
User-provided terminal evidence: hard-003/A received stop, matching model, 922 completion tokens, but JSONDecodeError. Five later runs did not execute. Raw response appears to be a JSON Markdown fence; exact original bytes remain on the Mac and must pass the parser there.

Added files only; original replay.py, plan, frozen summaries, visible prompts, checksums and historical artifacts are not changed.

Parser policy: plain JSON or exactly one entire ```json / unlabelled fence. No prose extraction, malformed fence repair, JSON content repair, duplicate keys or nonfinite numbers. Validate final answer and string-list source/changes/limitations fields. Preserve response wrapping telemetry. Same parser applies to saved A and all new runs. This is an experiment-local serialization change, not methodology adoption. Original format failure remains an execution observation.

resume_replay.py verifies original SHA256SUMS, first failed result/spec/config, absence of later run directories and exact saved request equality. It reprocesses saved A through replay_v011 and executes only the remaining five conditions. Model, prompt, frozen summary, generation config, token/call budget and retry policy are unchanged. New continuations directory is exclusive-created; a second launch stops without new calls. All failures stop the batch and return nonzero. No prompt expected labels are added.

The recovered result's call latency measures local replay, NOT original inference. Original inference telemetry is retained in continuation.json.original_inference_calls. First source is saved_response and first_run_reinvoked=false. New invocation counter includes attempted calls. Original files receive hashes in the continuation record. Actual original request/response/result are still Mac-local and are not included in this GitHub candidate. No claim of completed live recovery is made here.

Tests: 9 passed (4 existing + 5 new), synthetic mocks only. Covers fenced/plain equivalence, malformed/prose/multiple fence rejection, strict schema, duplicate/nonfinite rejection, retrieval, recovery+five calls, duplicate launch guard, byte-identical original preservation. No actual provider calls during development.

Semantic note based on pasted A output (provisional, not full source-verified evaluation): final answer abstains on likelihood while changes claims low-likelihood conclusion preserved. This contradiction remains for post-run review. Arithmetic versus industry-rate-as-company-cap must be evaluated separately. No A/B/C superiority inference yet.

Run from the task directory: python3 -m unittest -v test_replay test_recovery; then python3 resume_replay.py. Runtime .env is parsed by the existing safe provider adapter without printing credentials. No GitHub upload, merge, deployment or memory admission is performed by the script.

Continuation results need post-run evaluation of all 12 profile fields, actual B retrieval use, condition preservation, latency and unknown cost. Keep observed protocol failures separate from semantic quality. Calibration only; not held-out, production or Mac-local-model benchmark evidence.
