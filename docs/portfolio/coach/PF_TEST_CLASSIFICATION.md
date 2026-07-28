# PF-TEST mini-slice — STEP 1 실패 분류표 (43건)

> 측정일: 2026-07-13 · 측정 트리: worktree `monorepo/sess-pf-test` (base origin/main `3b50612`)
> 측정 명령: `pytest apps/portfolio -q --no-header --maxfail=1000`
> 베이스라인: **43 failed / 524 passed** (총 567)
> 근본 원인: 전부 PR7 앱 재배치(`portfolio/` → `apps/portfolio/`, `git mv`) 잔재. **로직 회귀 0**.

## 유형 A — 경로 문자열 stale (31건) → `"portfolio.…"` → `"apps.portfolio.…"`

`git mv`가 갱신하지 못하는 **문자열로 표기된 모듈 경로**. `ModuleNotFoundError: No module named 'portfolio'`.

| 파일 | 건수 | stale 문자열 | 성격 |
|---|---|---|---|
| `tests/api/test_e1_endpoint.py` | 4 | `patch("portfolio.api.views.run_e1_coach")` | mock.patch 타깃 |
| `tests/api/test_e2_endpoint.py` | 4 | `"portfolio.api.views.run_e2_coach"` | mock.patch 타깃 |
| `tests/api/test_e3_endpoint.py` | 4 | `"portfolio.api.views.run_e3_coach"` | mock.patch 타깃 |
| `tests/api/test_e4_endpoint.py` | 4 | `"portfolio.api.views.run_e4_coach"` | mock.patch 타깃 |
| `tests/api/test_e5_endpoint.py` | 4 | `"portfolio.api.views.run_e5_coach"` | mock.patch 타깃 |
| `tests/api/test_e6_endpoint.py` | 4 | `"portfolio.api.views.run_e6_coach"` | mock.patch 타깃 |
| `tests/test_cost_ledger.py` | 1 | `patch("portfolio.llm.cost_ledger.append_call")` | mock.patch 타깃 |
| `tests/test_s16_step0_ledger_integration.py` | 6 | `@parametrize("portfolio.services.coach.eN_service")` (N=1..6) | `importlib.import_module` 인자 |

소계 **31건**.

## 유형 B — 경로 오프셋 (12건) → `parents[2]` → `parents[3]`

앱이 `apps/` 하위로 **한 단계 깊어져** `Path(__file__).resolve().parents[N]`의 repo_root 계산이 어긋남.

| 파일 | 건수 | 증상 | 수정 |
|---|---|---|---|
| `tests/test_rubric_samples.py` | 7 | `RUBRIC_PATH = parents[2]/docs/...` → `apps/docs/...` `FileNotFoundError` | `parents[2]→[3]` |
| `tests/test_slice7_part4_scripts.py` | 5 | `ROOT = parents[2]` → 데이터 경로 오류 → 빈 `load_raw()` → `assert 0 == 14` | `parents[2]→[3]` |

소계 **12건** (rubric 7 + fixture 경로 5).

## 무접촉 대상 (stale 아님 — 오탐 방지)

같은 grep(`[\"']portfolio\.`)에 걸리나 **현재 통과 중**이며 stale이 아니므로 건드리지 않는다:

| 파일:라인 | 문자열 | 성격 | 판정 |
|---|---|---|---|
| `tests/test_cost_guard_pre_call.py:147,159,169` | `caplog.at_level(logger="portfolio.llm.cost_guard")` | 로거 이름 | 무접촉 (21 passed 유지) |
| `tests/slice9/test_regression_classifier.py:27,33` | `["portfolio/llm/cost_guard.py"]` | 회귀 분류기 경로 패턴 데이터 | 무접촉 |

필터 규칙: **"실패 목록(43건)에 대응하는 것만 수정"** — 통과 테스트를 깨지 않는다.

## 착시 주의

기본 `addopts`의 `maxfail`이 "5 failed"에서 조기 중단 → 43건을 과소평가(TASKQUEUE도 "5건"으로 등재됨). **전수 판정은 `--maxfail=1000`.** (`-o addopts=""`로 덮으면 ini `filterwarnings`의 구 Django 카테고리까지 노출돼 별도 에러 → addopts 유지 + `--maxfail`만 CLI 오버라이드.)

## 종결 수치

수리 후: **567 passed / 0 failed** (`pytest apps/portfolio`, 2026-07-13). 회귀 0. architecture 7 passed. LLM 0 / 비용 $0.
