# Slice 8 Part 1 종결 보고서

> **작성일**: 2026-05-16
> **브랜치**: `slice8` (main에서 분기)
> **종결 상태**: PASS — Part 2 진입 가능 (회귀 +22, Fallback 임계 +25 대비 88%)

---

## KPI 통과 현황

| 항목 | 기준 | 결과 | 통과 |
|------|------|------|:----:|
| 회귀 증가량 | 410 → ___ (시작점 메모 410 → 실제 392) | 392 → **414** (**+22**) | ✓ |
| Fallback 대비 | +25 이하 | +22 / +25 = **88%** | ✓ |
| IDENTICAL hash 7/7 | PASS | 7/7 | ✓ |
| #33 단위 테스트 | 5건 PASS | 5/5 | ✓ |
| #β2 max delta | ≤30% | **1.88%** | ✓ |
| #27 backward-compat | PASS | 기존 fixture 무영향 | ✓ |
| smoke 4건 | PASS | 5/5 (4건 + snapshot 1건) | ✓ |
| 비용 | $1.60 사전 경고 이하 | $1.595 → **$1.595** (LLM 호출 0) | ✓ |

**baseline 시작점 정정**: 메모의 "410"은 잘못된 기록 (실제 392). Slice 7 종결 후 portfolio + main 둘 다 392. Slice 8 누적은 392 + 22 = **414**.

---

## 부채 처리 결과

| 부채 | 처리 | 비고 |
|------|------|------|
| #33 budget 분리 | **closed** ✓ | PER_INSTANCE=50 / PER_SLICE=100, BudgetExceededError(scope) |
| #β2 estimator 재설계 | **closed** ✓ | 섹션 합산 + 9건 fit, max delta 1.88% |
| #26 rubric 강화 | **closed (예비)** | docs 갱신 + 룰 명문화. 분포 폭 자동 close는 Slice 8 Part 4 평가에서 자연 검증 |
| #27 input 보강 | **closed (Part 1)** | TimeSeriesContext schema 정착 + smoke 검증. Part 2~4에서 fixture 확장 |

---

## Part 1 commits 요약 (6 commits, main..slice8)

```
bba94fb [slice8] Step 2 mock smoke (E3 concentrated + E2 fixture v2)         +5
6a6c70c [slice8] Step 1 #27: TimeSeriesContext schema (raw + 4Q/12Q 시계열)   +5
a853b2b [slice8] Step 0-3 #26: rubric 10단계 척도 + 분포 폭 게이트 명문화      +4
b13538e [slice8] Step 0-2 #β2: 섹션 합산 estimator + 9건 fit (#β2 close)      +3
28486f3 [slice8] Step 0-1 #33: CostGuard 이중 카운터 분리                     +5
3e5ea38 [slice8] Step 0-1: COST_POLICY 임계 $1.50 → $2.00 갱신                0
─────────────────────────────────────────────────────────────────────────────
                                                                       총 +22
8eecca3 (cherry-picked) docs: 코드베이스 감사 보고서 생성                   0
```

---

## Part 2 진입 판정

### 회귀 증가량 판정

- 증가량 **+22** → **+12~+24 정상 범위**
- 판정: **Part 2 진입 PASS** ✓

### 비용 점검

- 누적 $1.595 유지 (Part 1은 LLM 호출 0)
- 사전 경고 $1.60 미초과 → 정상

### 결론

**Part 2 진입 가능**. 다음 작업:
- Part 2: #28 output schema action_items 강제 슬롯 (PS 3.0)
- Part 3: #29 system prompt 4요소 + Sample 5 few-shot (PS 2.5)
- Part 4: manual eval + 종결

Part 2 작업 지시서 작성 후 진입.

---

## Slice 9 등록 항목

| 항목 | 사유 |
|------|------|
| (없음) | Part 1 KPI 모두 PASS, keep_open 항목 없음 |

다만 다음 항목은 Slice 8 Part 4 평가 결과에 따라 결정:
- #26 분포 폭 ≥ 6.0 (10단계) 달성 시 자연 close. 미달 시 Slice 9 Step 0 재후보.

---

## 환경 이슈 (Slice 8 진행 중 발견)

### iCloud sync 충돌

- 프로젝트 디렉토리가 두 경로에 존재:
  - `/Users/byeongjinjeong/Desktop/stock_vis` (로컬, working tree)
  - `/Users/byeongjinjeong/Library/Mobile Documents/com~apple~CloudDocs/Desktop/stock_vis` (iCloud)
- 두 경로의 .git inode가 별개지만 commit hash는 동일하게 sync 됨
- 처리: 로컬 Desktop을 source of truth로 사용 (사용자 결정, 2026-05-16)

### 브랜치 자동 전환

- Step 1 (#27), Step 2 commit 시 working directory의 git HEAD가 `fix/ts-compile-errors-20260516`, `fix/broken-tests-20260516`로 자동 전환됨
- 추정 원인: 다른 세션·도구가 일자별 패치 브랜치 작업 중 + iCloud sync로 .git/HEAD 갱신
- 대응: 매 commit 전 `git branch --show-current` 확인 + 필요 시 slice8로 cherry-pick

---

## 산출물 체크리스트 (지시서 §산출물 12건 매핑)

| # | 지시서 경로 | 실제 경로 | 종류 | 상태 |
| - | --- | --- | --- | :-: |
| 1 | `portfolio/coach/cost_guard.py` v2 | `portfolio/llm/cost_guard.py` | 코드 | ✓ |
| 2 | `portfolio/coach/exceptions.py` | `portfolio/llm/exceptions.py` | 코드 | ✓ |
| 3 | `portfolio/coach/token_budgets.py` v2 | `portfolio/llm/budget_estimator.py` | 코드 | ✓ |
| 4 | `portfolio/coach/schemas/commentary_input.py` v2 | `portfolio/schemas/commentary_input.py` | 코드 | ✓ |
| 5 | `tests/portfolio/coach/test_cost_guard.py` | `portfolio/tests/test_cost_guard.py` | 테스트 (5건) | ✓ |
| 6 | `tests/portfolio/coach/test_budget_estimator.py` | `portfolio/tests/test_budget_estimator.py` | 테스트 (3건) | ✓ |
| 7 | `tests/portfolio/coach/test_commentary_input_schema.py` | `portfolio/tests/test_commentary_input_schema.py` | 테스트 (4건) | ✓ |
| 8 | `tests/portfolio/coach/slice8/test_input_v2_smoke.py` | `portfolio/tests/slice8/test_input_v2_smoke.py` | 테스트 (4건 + fixture 2건) | ✓ |
| 9 | `docs/portfolio/coach/COST_POLICY.md` | 동일 | docs (§LLM budget + §Appendix A) | ✓ |
| 10 | `docs/portfolio/coach/manual_eval_rubric.md` v2 | 동일 | docs (10단계 + 양극단 + 분포 폭 게이트) | ✓ |
| 11 | `docs/portfolio/coach/slice8/budget_estimator_v2.md` | 동일 | docs (fit 보고서) | ✓ |
| 12 | `docs/portfolio/coach/slice8/part1_closing.md` | 동일 | docs (본 보고서) | ✓ |

**경로 매핑 메모**: 지시서의 `portfolio/coach/`는 실제 `portfolio/llm/`로 매핑. `tests/portfolio/coach/`는 `portfolio/tests/`로 매핑. 새 `portfolio/tests/slice8/`만 신규 디렉토리. 사용자 결정 (2026-05-16, "경로만 매핑해 지시서 그대로 실행").

---

**Part 1 종결.** Part 2 지시서 작성 대기.
