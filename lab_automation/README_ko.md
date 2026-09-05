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

## 1. Shared Core

```text
Lab Job
  -> Local Runner
  -> Agent / Codex / Frontier API
  -> Workspace / Tests / Artifacts
  -> Candidate Result
  -> Review
  -> CEO Approval Gates
       push
       merge
       deploy
  -> Promotion / Deployment
  -> Verification / Rollback
```

## 2. Lab-specific layer

각 Lab adapter는 다음만 정의한다.

- authority references
- allowed write scope
- expected output contract
- evaluation/review entrypoint
- Lab-specific escalation rules

공통 runner는 Research Claim, Design object, Math Experiment의 의미를 재정의하지 않는다.

## 3. First customer

첫 vertical slice는 Math Lab의 `DailyPrice readiness probe`다. 하지만 core contract는 처음부터 `research_lab`, `design_lab`, `math_lab`을 모두 지원한다.

## 4. Current bootstrap files

- `contracts.py` — Job / candidate revision / approval 공통 contract
- `ledger.py` — append-only runtime ledger
- `local_runner.py` — local candidate commit까지만 수행하는 MacBook runner
- `doctor.py` — git / Python / Poetry / Codex / PostgreSQL preflight
- `run_first_job.sh` — doctor + dry-run + explicit restricted real-run launcher
- `first_run_ko.md` — 첫 end-to-end 실행 절차와 hard-stop 조건
- `approval_and_promotion_ko.md` — push / merge / deploy 승인 경계
- `run_ledger_ko.md` — 운영 기록과 platform learning 원칙
- `jobs/math_daily_price_readiness.example.json` — 첫 Math Lab Job

## 5. First-run boundary

현재 구현의 최종 상태는 다음이다.

```text
local candidate branch + commit
        ↓
waiting_for_push_approval
```

자동 push, PR merge, deploy는 아직 구현하지 않으며 CEO 승인 전에는 실행하지 않는다.
