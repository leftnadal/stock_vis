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
