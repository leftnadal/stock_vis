# StockVis Lab Automation Platform v0.1

**Status:** Working / Bootstrap Candidate  
**Scope:** Research Lab, Design Lab, Math Lab 공통 실행 인프라

## 0. 한눈에 보는 요약

이 디렉터리는 각 Lab의 연구 방법론을 통합하지 않는다. 대신 Job 실행, branch/worktree 격리, agent 호출, 결과 기록, telemetry, approval, promotion, deployment handoff 같은 **공통 운영 인프라**만 제공한다.

핵심 원칙:

1. Lab별 epistemic/design authority는 유지한다.
2. local work와 canonical promotion을 분리한다.
3. push / merge / deploy는 서로 다른 approval gate다.
4. 승인은 특정 revision SHA에만 유효하다.
5. 승인 후 revision이 바뀌면 기존 승인은 무효화된다.
6. destructive action, secret mutation, force-push, production data deletion은 일반 promotion approval보다 더 강한 별도 consequential decision을 요구한다.
7. runtime telemetry는 Lab Knowledge와 구분한다.
8. 각 실행 단계는 append-only run event로 남기며, 이 기록은 platform 자체를 평가·개선하는 근거로 사용한다.
9. Artifact identity는 physical storage path와 분리한다.
10. Lab-specific experiment semantics는 shared runtime schema를 오염시키지 않고 adapter/profile layer에 둔다.

## 1. Shared Core

```text
Lab Job
  -> Local Runner
  -> Run
       -> Invocation(s)
       -> content-addressed Artifacts
       -> Tests / Runtime Events
  -> Candidate Result
  -> Review
  -> CEO Approval Gates
       push
       merge
       deploy
  -> Promotion / Deployment
  -> Verification / Rollback
```

## 2. Shared Execution vs Lab-specific Semantics

공통 layer는 실행 사실을 담당한다.

- Job / Run / Event
- Invocation identity
- immutable input snapshot
- Artifact logical identity / hash
- runtime integrity
- approval / promotion state

각 Lab adapter/profile은 자기 영역의 의미만 정의한다.

- authority references
- allowed write scope
- expected output contract
- evaluation/review entrypoint
- Lab-specific escalation rules
- Lab-specific experiment semantics

공통 runner는 Research Claim, Design object, Math Experiment의 의미를 재정의하지 않는다.

Research Lab의 Critic exposure, blinding, holdout, independence, evaluation linkage는 `research_runtime/` profile에 둔다.

## 3. Artifact Store

기본 local store:

```text
~/.stockvis-lab-automation/artifacts/sha256/...
```

logical identity:

```text
artifact://sha256/<digest>
```

`--state-root`를 외장 NVMe/NAS mount로 옮겨도 artifact identity는 바뀌지 않는다. 현재 내부 SSD 용량은 architecture constraint로 사용하지 않는다.

## 4. First customer

첫 vertical slice는 Math Lab의 `DailyPrice readiness probe`다. 하지만 core contract는 처음부터 `research_lab`, `design_lab`, `math_lab`을 모두 지원한다.

## 5. Current bootstrap files

- `contracts.py` — Job / candidate revision / approval 공통 contract
- `ledger.py` — append-only runtime event ledger
- `execution_records.py` — Run과 분리된 Invocation contract
- `artifact_store.py` — content-addressed local Artifact Store
- `integrity.py` — shared runtime integrity checks
- `local_runner.py` — local candidate commit까지만 수행하는 runner
- `issue_queue.py` — queued intake와 명시적 running-issue resume
- `research_runtime/` — Research Experiment Profile + research-specific preflight
- `doctor.py` — git / Python / Poetry / Codex / PostgreSQL preflight
- `run_first_job.sh` — doctor + dry-run + explicit restricted real-run launcher
- `first_run_ko.md` — 첫 end-to-end 실행 절차와 hard-stop 조건
- `approval_and_promotion_ko.md` — push / merge / deploy 승인 경계
- `run_ledger_ko.md` — 운영 기록과 platform learning 원칙
- `jobs/math_daily_price_readiness.example.json` — 첫 Math Lab Job

## 6. 이미 running인 Issue의 안전한 재개

정상 intake는 계속 `lab-automation` + `queued` Issue만 선택한다. 이미 claim되어
`running`으로 바뀐 Issue의 Job 파일만 복구할 때는 명시적인 resume 경로를 사용한다.

Issue #34의 정확한 명령:

```bash
poetry run python -m lab_automation.issue_queue \
  --repo-slug leftnadal/stock_vis \
  --state-root "$HOME/.stockvis-lab-automation" \
  --issue 34 \
  --resume-running
```

이 경로는 해당 Issue 하나를 read-only로 조회하고, `OPEN` + `lab-automation` +
`running` 상태와 기존 `claims/issue-34.claim`의 issue/job identity를 확인한다. claim을
다시 만들거나 GitHub label을 변경하지 않는다. 기존 Job이 같으면 그대로 반환하고,
다르면 덮어쓰지 않고 실패한다.

## 7. Current boundary

실제 실행의 최종 상태는 다음이다.

```text
local candidate branch + one final commit
        ↓
external ledger records exact final SHA
        ↓
waiting_for_push_approval
```

자동 push, PR merge, deploy는 아직 구현하지 않으며 CEO 승인 전에는 실행하지 않는다.
