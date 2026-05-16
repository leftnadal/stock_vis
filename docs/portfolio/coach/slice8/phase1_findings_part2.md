# Slice 8 Part 2 — 사전 점검 보고서

> **작성일**: 2026-05-16
> **브랜치**: `slice8`
> **상태**: Phase 2 진입 준비 완료 ✓ (환경 이슈 처리 + 사실관계 점검 모두 완료)

---

## Q-1 E2 iCloud 표지 결과

- [x] iCloud 측 `DO_NOT_EDIT_USE_DESKTOP.md` 작성: **PASS** (`~/Library/Mobile Documents/com~apple~CloudDocs/Desktop/stock_vis/DO_NOT_EDIT_USE_DESKTOP.md`, 423 bytes)
- [x] Desktop 측 `WORKSPACE_ROOT.md` 작성: **PASS** (`/Users/byeongjinjeong/Desktop/stock_vis/WORKSPACE_ROOT.md`, 441 bytes)
- [x] Desktop 표지 commit: **ace3d4c** `[slice8] add WORKSPACE_ROOT.md (#38)` (자동 브랜치 전환 발생, cherry-pick으로 slice8 복귀)
- **부채 #38: close ✓**

### 자동 전환 사고 1회 (Q-1 commit 시)
- `slice8` → `test/sec-pipeline-tests-20260516`로 commit 직후 전환
- 대응: `git checkout slice8 && git cherry-pick 1127e93` → `ace3d4c`로 정상 적재

---

## Q-2 F4 pre-commit hook 결과

- [x] hook 설치: **PASS** (`.git/hooks/pre-commit`, 1692 bytes)
- [x] 실행 권한: **PASS** (`-rwxr-xr-x`)
- [x] 정상 케이스 통과: **PASS** (Q-2 정책 문서 commit 시 `✅ pre-commit 검증 통과 (branch=slice8)` 출력 + commit 성공)
- [x] 차단 케이스 확인: **PASS** (가짜 브랜치 `fix/foo-20260516` 시뮬에서 exit 1, 정상 케이스 `slice8` 시뮬에서 exit 0)
- [x] 정책 문서 작성: **PASS** (`docs/portfolio/coach/slice8/pre_commit_policy.md`)
- **부채 #39: close ✓**

### Q-2 자연 검증 효과
- 정책 문서 commit (`913002b`)에서 hook이 자동 실행 + slice8 유지됨 (자동 전환 차단 성공!)
- 이전 Q-1 commit과 달리 cherry-pick 불필요

---

## Q-3 자동 브랜치 전환 도구 추적 결과

### 후보별 검출

| 후보 | 검출 | 비고 |
|------|------|------|
| 1. VS Code Git extensions | 미검출 | `code --list-extensions` 결과 git 관련 0건 |
| 2. 외부 Git GUI (GitHub Desktop / GitKraken / Sourcetree) | 미검출 | 프로세스 0건 |
| 3. AI 도구 프로세스 | **부분 검출** | Cursor UIViewService (UI 도우미만, 핵심 아님) |
| 4. GitHub Actions / hooks | 미검출 | `.github/workflows/` 0건, `.git/hooks/`에 pre-commit만 (Q-2 설치본) |
| 5. macOS launchctl | **검출 ★** | `com.stockvis.celery-worker`, **`com.stockvis.nightly` (PID 36878)**, `com.stockvis.celery-beat`, `com.stockvis.celery-watchdog` |
| 6. reflog 패턴 | **확정 ★** | `fix/*-20260516`, `test/*-20260516`, `chore/*-20260516` 매 commit 직후 자동 전환 |

### 가장 의심 후보 → **확정**

**원인: `~/stock-vis-nightly/` launchd 야간 자동화 시스템**

- launchd label: `com.stockvis.nightly` (PID 36878)
- 스크립트 4종: `run_tier1.sh`, `run_tier2_be.sh`, `run_tier2_fe.sh`, `run_tier3_audits.sh`
- 각 스크립트의 동작 (확인됨):
  1. `PROJECT_DIR=$HOME/Desktop/stock_vis`로 진입 (=내가 작업하는 같은 경로!)
  2. `BASE_BRANCH=$(git branch --show-current)` 저장
  3. 새 일자별 브랜치 생성 (예: `test/users-unit-tests-20260516`)
  4. `claude -p` CLI로 자동 작업 (예: "users 앱의 단위 테스트를 25개 이상 작성해")
  5. commit 후 BASE_BRANCH로 복귀
- 추가 증거: PID 50610에 `claude -p` CLI 활성 (users 단위 테스트 작성 중)

### 즉시 비활성화 가능 여부

- **가능** (`launchctl bootout gui/$(id -u) com.stockvis.nightly` 또는 `.plist` 비활성화)
- 다만 사용자가 의도적으로 만든 시스템 (`docs/nightly_auto_system/` 정식 존재) → 임의 비활성화는 destructive
- 현재 pre-commit hook으로 충분히 차단됨
- **부채 #40: keep_open** (식별 완료, 비활성화 결정은 사용자 위임)

---

## Q-4 사실관계 점검 결과

### R1. `portfolio/llm/` 현재 구조 (Part 1 commits 이후)

| 파일 | 라인 | 비고 |
|------|-----:|------|
| `__init__.py` | 21 | — |
| `budget_estimator.py` | **553** | Part 1 Step 0-2 #β2 섹션 합산 estimator 추가 |
| `client.py` | **310** | Part 1 #33 record_llm_call / record_response 분리 |
| `cost_guard.py` | **196** | Part 1 #33 이중 카운터 (PER_INSTANCE/PER_SLICE) |
| `eval_metrics.py` | 45 | — |
| `exceptions.py` | **69** | Part 1 #33 BudgetExceededError(scope/count/limit) 확장 |
| `mocks.py` | 195 | — |
| `parsers.py` | 49 | — |
| `token_budgets.py` | 55 | — |
| **합계** | **1493** | Part 1 변경 4개 파일 (cost_guard, exceptions, client, budget_estimator) |

### R2. `portfolio/schemas/` 현재 구조 (Part 1 #27 schema close 이후)

| 파일 | 라인 | 비고 |
|------|-----:|------|
| `__init__.py` | 87 | — |
| `analysis_context.py` | 165 | — |
| **`commentary_input.py`** | **57** | **Part 1 #27 신규** (TimeSeriesContext) |
| `diagnostic.py` | 80 | — |
| `e4_conversation.py` | 126 | `E4ConversationOutput` 정의 |
| `holding.py` | 62 | — |
| `llm.py` | 289 | `LLMResponse`, `E5Response`, `E2Response` 정의 |
| `llm_outputs.py` | 334 | `E3PortfolioCommentary`, `E6ComparisonResponse`, `ConversationResponse` 정의 |
| `metric_result.py` | **116** | Part 1 #27: `time_series: Optional[TimeSeriesContext]` 필드 추가 |
| `return_breakdown.py` | 140 | — |
| `user_profile.py` | 66 | — |
| **합계** | **1522** | Part 1 변경: commentary_input.py 신규 + metric_result.py 1개 필드 추가 |

- **TimeSeriesContext 위치**: `portfolio/schemas/commentary_input.py:18`
- **commentary input schema 파일**: `portfolio/schemas/commentary_input.py` (Part 1 신규)
- **output schema 파일 존재 여부**:
  - 전용 `commentary_output.py` 파일은 **없음**
  - 진입점별 output 모델은 3개 파일에 분산:
    - `e4_conversation.py:80` — `E4ConversationOutput`
    - `llm.py:18 / 95 / 222` — `LLMResponse`, `E5Response`, `E2Response`
    - `llm_outputs.py:103 / 181 / 228` — `E3PortfolioCommentary`, `E6ComparisonResponse`, `ConversationResponse`
  - **Part 2 #28에서 신규 `action_items` 슬롯 추가 필요** (현재 정의 0건)

### R3. 기존 output schema

| 위치 | 클래스 | 진입점 |
|------|--------|--------|
| `portfolio/schemas/llm.py:18` | `LLMResponse` | 공통 |
| `portfolio/schemas/llm.py:95` | `E5Response` | E5 (조정 파싱) |
| `portfolio/schemas/llm.py:222` | `E2Response` | E2 (진단 카드) |
| `portfolio/schemas/llm_outputs.py:103` | `E3PortfolioCommentary` | E3 portfolio |
| `portfolio/schemas/llm_outputs.py:181` | `E6ComparisonResponse` | E6 (비교) |
| `portfolio/schemas/llm_outputs.py:228` | `ConversationResponse` | E4 (대화) |
| `portfolio/schemas/e4_conversation.py:80` | `E4ConversationOutput` | E4 (대화, 확장본) |

- **`action_items` 또는 `ActionItem` 기존 정의: 없음** (Part 2 #28에서 신규 도입 필요)
- **기존 commentary 출력 schema**: 진입점별로 `llm.py` + `llm_outputs.py`에 분산 정의. 통합 base 모델 없음.

### R4. 진입점별 output 처리 흐름

- **service 파일 위치**: `portfolio/services/`
  - `e1_garp.py` (E1)
  - `e2_diagnostic_card.py` (E2)
  - `e3_metric_comment.py` (E3)
  - `e3_portfolio_service.py` (E3 portfolio)
  - `e5_adjustment_parser.py` (E5)
  - `e6_comparison.py` (E6)
  - (E4 conversation의 service는 별도 파일 없이 통합되어 있을 가능성)
- **DIMENSION_LOOKUP 위치**: `scripts/validation/score_step8.py:33`
- **현재 entry 수**: **7건** (e1, e5, e2, e6, e3, e3_portfolio, e4_conversation)
  - Slice 1 (e1) → Slice 7 (e4_conversation)까지 순차 추가
- **output schema 사용 방식**:
  - 각 service가 자체적으로 자기 진입점의 `*Response` 또는 `*Output` 모델을 import
  - LLMClient가 prompt → response 파싱 시 진입점별 schema 적용
  - DIMENSION_LOOKUP은 채점 시점에 (manual eval scoring)에서만 활용

### R5. 기존 fixture에서 output 형태

- **portfolio/tests/fixtures/** 디렉토리:
  - `e4_conversation/` (15건, S01~S15, Slice 7 mock fixture)
  - `e3_portfolio/` (Slice 6 mock fixture)
  - `mock_responses/`
  - 진입점별 sample context (`sample_analysis_context.py`, `sample_adjustment_context.py` 등)
- **Slice 8 Part 1 신규 fixture**:
  - `portfolio/tests/slice8/fixtures/e3_concentrated_v2.json` (5 metrics, time_series 포함)
  - `portfolio/tests/slice8/fixtures/e2_v2.json` (3 metrics, time_series None 케이스 포함)
- **snapshot 파일 위치**: 별도 snapshot 패턴 미사용. fixture 자체가 schema dump 역할
- **기존 LLM 응답 fixture**: `mock_responses/` 디렉토리 (구체 내용은 Part 2 진입 시 확인)
- **Part 1 추가 fixture와의 관계**: 별개 격리. Slice 8 Part 4 평가 데이터로 통합 여부 결정.

### R6. Part 1 산출물 검증

#### Part 1 commits에서 추가/수정된 portfolio 영역 파일 (21건)

##### 코드 (8건)
- `portfolio/llm/budget_estimator.py` (Step 0-2)
- `portfolio/llm/client.py` (Step 0-1 #33)
- `portfolio/llm/cost_guard.py` (Step 0-1 #33)
- `portfolio/llm/exceptions.py` (Step 0-1 #33)
- `portfolio/schemas/commentary_input.py` (Step 1 #27 신규)
- `portfolio/schemas/metric_result.py` (Step 1 #27 time_series 필드 추가)
- `portfolio/tests/slice8/__init__.py` (Step 2 디렉토리)
- WORKSPACE_ROOT.md (Q-1 #38)

##### 테스트 (6건)
- `portfolio/tests/test_budget_estimator.py` (Step 0-2 +3 tests)
- `portfolio/tests/test_commentary_input_schema.py` (Step 1 +5 tests)
- `portfolio/tests/test_cost_guard.py` (Step 0-1 +5 tests)
- `portfolio/tests/test_rubric_samples.py` (Step 0-3 +4 tests)
- `portfolio/tests/slice8/test_input_v2_smoke.py` (Step 2 +5 tests)
- `portfolio/tests/slice8/fixtures/e2_v2.json`, `e3_concentrated_v2.json` (Step 2 fixture 2건)

##### 문서 (7건)
- `docs/portfolio/coach/COST_POLICY.md` (Step 0-1)
- `docs/portfolio/coach/manual_eval_rubric.md` (Step 0-3)
- `docs/portfolio/coach/slice8/budget_estimator_v2.md` (Step 0-2)
- `docs/portfolio/coach/slice8/part1.md` (Step 3 사용자 작성)
- `docs/portfolio/coach/slice8/part1_closing.md` (Step 3 종결)
- `docs/portfolio/coach/slice8/pre_commit_policy.md` (Q-2 #39)
- `docs/portfolio/coach/slice8/phase1_findings_part2.md` (본 보고서, Q-5)

#### 종결 보고서 KPI 재확인

| 항목 | 기준 | 결과 |
|------|------|:----:|
| 회귀 | 410 → ___ (실제 392 → 414, **+22**) | ✓ |
| Fallback 대비 | +25 이하 | ✓ (88%) |
| IDENTICAL hash 7/7 | PASS | ✓ |
| #33 단위 테스트 | 5건 PASS | ✓ |
| #β2 max delta | ≤30% | ✓ (1.88%) |
| #27 backward-compat | PASS | ✓ |
| smoke | PASS | ✓ |
| 비용 | $1.60 이하 | ✓ ($1.595 유지) |

**모든 KPI PASS, 종결 보고서 검증 정합**.

---

## Phase 2 진입 준비 완료 여부

- [x] 환경 이슈 처리 (E2 + F4) 완료
- [x] 사실관계 점검 6종 (R1~R6) 완료
- [x] 사용자 회수 대기 ← **현재 상태**

---

## 신규 발견 (Part 2 작업에 영향)

### 1. ActionItem / action_items 기존 정의 없음 (#28 핵심)

- Part 2 #28의 "output schema action_items 강제 슬롯"은 완전 신규 도입
- 기존 진입점 7개의 output schema 모두 `action_items` 필드 없음
- **선택지**:
  - A) 진입점별 schema에 `action_items: list[E4ActionItem]` 필드 추가 (분산)
  - B) 통합 base 모델 `CommentaryOutputBase` 도입 → 진입점별 상속 (통합)

### 2. output schema 분산 (3개 파일)

- 진입점별 output schema가 `llm.py`, `llm_outputs.py`, `e4_conversation.py` 3개 파일에 분산
- Part 2에서 일관된 action_items 슬롯 도입 시 **schema 정리 작업 동반**될 가능성
- **부채 후보 #41**: output schema 통합 (선택 사항, Slice 9 후보)

### 3. 야간 자동화 동시 작업 (Part 2 진행 중 모니터링 필요)

- Q-3에서 식별된 `~/stock-vis-nightly/` 시스템이 같은 working directory에서 자동 작업 중
- pre-commit hook으로 차단되지만, 다른 세션의 file I/O가 우리 작업에 race condition 유발 가능
- **운영 가이드**:
  - 매 commit 전 `git branch --show-current` + `git status` 확인
  - 야간 자동화 시간대(자정~새벽) 작업 시 충돌 위험 증가 → 주간 작업 권장
  - 또는 사용자 결정으로 `launchctl bootout`으로 일시 중지

### 4. portfolio/schemas/commentary_input.py 확장 여지

- 현재 TimeSeriesContext만 정의 (#27 closed)
- Part 2 #28 ActionItem도 동일 파일에 추가하면 일관성 유지
- 또는 별도 `commentary_output.py` 신규 가능 — Part 2 지시서 v2에서 결정 사항

### 추가 부채 후보

| ID | 항목 | 사유 | 우선순위 |
|----|------|------|:--------:|
| #41 | output schema 통합 (`CommentaryOutputBase`) | 진입점 7개 분산 정의 → 일관성 부족 | Slice 9 |
| #42 | 야간 자동화 작업 격리 | 동일 working dir 충돌 위험 | 즉시 결정 필요 |

---

**Phase 1 사전 점검 종료.** Part 2 지시서 v2 작성 의뢰 대기.
