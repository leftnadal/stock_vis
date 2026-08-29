# DSS-W8-LOAD-1 — DSS 8회차 주간 적재 + 장부 편승 지시서

## 계약 헤더
- 트랙: DSS 주간 운영(수동 1회차) + 장부 편승 / ID: DSS-W8-LOAD-1
- 집행 시점: 2026-08-28(금) EstimateSnapshot 8회차 발화 이후 (STEP 0에서 기계 확인)
- worktree ~/worktrees/sv-dss-w8 · 브랜치 monorepo/sess-dss-w8 (origin/main 기점 신규)
- 쓰기 허용 (이외 전면 금지):
  (W1) docs 4파일: docs/instructions/DSS-W8-LOAD-1.md · TASKQUEUE.md · INCIDENTS.md · PROGRESS.md
  (W2) DB INSERT 한정: SymbolDemandSignal(anchor 2026-08-28) · ThemeDemandScore(date 2026-08-28, 11행).
       기존 행 UPDATE/DELETE 절대 금지. 마이그레이션 금지. 코드 수정 금지 — 기존 demand_signal 서비스 경로로만.
- FMP 0회 · foreground · machine clock · add 명시 · force 금지. push=D-PUSH-DELEG. behind 흡수=docs-only D-GOBS-REBASE-STANDING.
- 커밋: 1 = 지시서(0게이트) → 적재·검산 → 2 = 장부. 중간 승인 게이트 없음. HALT-0.

## STEP 0 / T1~T4 = 지시서 원문 준수 (아래 집행 결과)

---

## 집행 결과 (DSS-W8-LOAD-1, 재개 2026-08-29 machine clock)

> 최초 STEP 0(08-27 목)에서 8회차 미발화(집행 시점 미도래) HALT → 08-28 8회차 발화 후 재개.

### STEP 0 (재기점 origin/main `1177e0ce`, clock 2026-08-29 11:20 KST)
| # | 결과 |
|---|---|
| 0-1 | health 15 OK / 1 WARN((i) runtime_check) / 0 ERROR. 신규 (ii)형 0(#119) → HALT 아님 |
| 0-2 | **8회차 08-28 발화 ✅ rows=1005 · syms=503**(최신 EstimateSnapshot=08-28) |
| 0-3 | SymbolDemandSignal anchor 08-28 부재 → T1 적재 진행. 최신 anchor=08-21 |
