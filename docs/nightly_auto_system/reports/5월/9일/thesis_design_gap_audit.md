# Thesis Control 설계 갭 감사

> 작성일: 2026-05-10
> 감사 대상: `docs/thesis_control/` 설계 문서 vs `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드)
> 모드: 읽기 전용 (코드 수정 없음)

---

## 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 상태 |
|-------|------|-------|------|
| **Phase 1 (MVP)** | 관제 엔진 v2.3.2 (Stage 0~3) | **100%** | A |
| **Phase 1 (MVP)** | 학습 레이어 모델 (HypothesisEvent, ValidityRecord, InvestorDNA) | **100%** | A |
| **Phase 2 핵심 루프** | FE-PR-1~6 (목록/빌더/지표/대시보드/알림/마감) | **100%** | A |
| **Phase A (LLM 빌더)** | one-shot proposal 모드 | **100%** | A |
| **Phase 3 백엔드 PR-7** | display_unit + raw_value 확장 + IndicatorReadingsView | **100%** | A |
| **Phase 3 백엔드 PR-10** | AI 요약 Celery task (`summary.py`) | **80%** | B (notable_changes 풍부화 미완) |
| **Phase 3 프론트 PR-8** | RealValueIndicatorCard / AISummarySection / NotableChangesSection | **70%** | B (RealValueIndicatorCard는 IndicatorRow로 대체) |
| **Phase 3 프론트 PR-9** | ChartToggleButton + PeriodSelector + IndividualMiniCharts | **30%** | B (컴포넌트 작성됨, 페이지에서 미사용 — orphan) |
| **원안 FE-PR-7** | 대시보드 탭(관제/상세/히스토리) + 전제 CRUD | **0%** | C (설계 변경으로 폐기) |
| **원안 FE-PR-8** | Finviz 히트맵 + 지표 weight/direction 편집 | **0%** | C/D (히트맵 백엔드는 잔존, FE 미구현) |
| **원안 FE-PR-9** | 히스토리 탭 (recharts 라인 + 스냅샷 타임라인) | **0%** | C |
| **원안 FE-PR-10** | 마감 아카이브 + ValidityMatrix UI | **0%** | C |
| **원안 FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing/CategoryChart) | **0%** | C |
| **Phase 2 (개인화)** | DNA 슬라이더 / 역제안 / ValidityScore 활성화 | **0%** | C |
| **Phase 3 (지능 강화)** | 합성 에이전트 / Online LR | **0%** | C |
| **Phase 4 (벡터 스코어링)** | DNA 벡터화 / 코사인 유사도 | **0%** | C |

**핵심 발견**:
1. Phase 1 MVP + Phase 2 핵심 루프 + Phase A LLM 빌더는 **완전 구현**.
2. **Phase 3는 두 갈래로 분기**되어 있음 — 원안(`Phase2_completion_summary.md` §8) FE-PR-7~11은 **사실상 폐기**되고, `thesis_control_phase3_frontend_redesign.md` (PR-7~10)으로 **선회**. 명시적 "폐기 결정" 문서는 없으나 redesign 문서가 우선됨.
3. Phase 3 redesign에서도 PR-9 차트 컴포넌트는 **작성 후 미연결**. `IndicatorRow.tsx` (설계에 없는 신규 컴포넌트)가 카드 + 인라인 토글 + 차트를 통합 처리하는 형태로 진화.
4. `MoonPhase` / `scoreToPhaseMeta`는 redesign에서 "삭제" 명시되었으나 **목록 화면(ThesisListCard)에서 여전히 사용 중** — 부분 폐기.

---

## 문서별 상태 테이블

| # | 문서 | 상태 | 분류 | 비고 |
|---|------|------|------|------|
| 1 | `plan/thesis_control_design.md` (1370줄) | Phase 1~2 충족, Phase 3 일부 | A/B | 핵심 설계 문서. 모델·뷰 모두 일치. |
| 2 | `plan/thesis_control_implementation_guide.md` (286줄) | 구현 완료 | A | 구현 가이드 그대로 반영됨. |
| 3 | `plan/thesis_control_integrated_roadmap.md` (660줄) | Phase 1만 완료 | B | Phase 2~4 미구현(설계상 시간 투자 후순위). |
| 4 | `plan/thesis_control_math_model_final.md` (1153줄) | 완전 구현 | A | Stage 0~3, MAD_FLOOR, decay, validation 모두 `indicator_scorer.py` / `snapshot_builder.py` 반영. |
| 5 | `plan/thesis_control_phase3_frontend_redesign.md` | 부분 구현 | B | PR-7 ✓, PR-8 부분, PR-9 orphan, PR-10 ✓ (notable_changes 풍부화 미완). |
| 6 | `thesis_control_user_experience.md` (435줄) | Phase 2 루프 충족 | A | 6단계 빌더 → 대시보드 → 마감 모두 구현. |
| 7 | `thesis_control_phase1_frontend_FE_PR_1.md` ~ `FE_PR_5.md` | 완료 | A | `frontend/task_done/Phase2_completion_summary.md`로 검증. |
| 8 | `thesis_control_phase1_frontend_prompts.md` | 가이드 (적용 완료) | A | — |
| 9 | `thesis_control_phase1_prompts.md` | 가이드 (적용 완료) | A | — |
| 10 | `plan/talking_builder/llm_builder_plan.md` | 완료 | A | `work_done/phase_a_llm_builder.md` 참조. PR-1~3 모두 머지. |
| 11 | `plan/talking_builder/thesis_builder_redesign_v2.md` | 부분 구현 | B | LLM 빌더 골격은 완성, hardening 단계는 일부만. |
| 12 | `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 구현됨 | A | `quarterly_metric_fetcher.py` + `QuarterlySparkline.tsx` + `IndicatorRow` 분기 표시까지 반영. |
| 13 | `plan/talking_builder/redesign_build_plan/00~05` | 부분 구현 | B | Phase A MVP/Hardening은 완료, Phase B(키워드)·C(고급)은 미착수. |
| 14 | `frontend/task_done/FE-PR-1` ~ `FE-PR-6` (+ Phase2 summary) | 완료 보고서 | A | 모두 정합. 6 PRs / 84 files / ~3,380 lines. |
| 15 | `frontend/task_done/FE-PR-3_plan_review_v3.md` | 리뷰 문서 | A | 적용 결과 코드에 반영. |
| 16 | `work_done/phase_a_llm_builder.md` | 완료 보고서 | A | 09b0f8b/6d72432 커밋. PR-1~3 머지. |

---

## Phase 3 미구현 항목 상세

### 1. Phase 3 redesign 문서(`plan/thesis_control_phase3_frontend_redesign.md`) 기준

#### PR-7 백엔드 — **완전 구현 (A)**

| 설계 항목 | 구현 위치 | 상태 |
|-----------|-----------|------|
| `ThesisIndicator.display_unit` 필드 추가 | `thesis/models/indicator.py:73-76` | ✓ |
| 마이그레이션 + 데이터 채움 | `thesis/migrations/0004_add_display_unit.py`, `0005_populate_display_unit.py` | ✓ |
| `DashboardView`에 `raw_value` / `previous_raw_value` / `change_pct` / `raw_value_unit` 추가 | `thesis/views/monitoring_views.py:94-112,150-174` | ✓ |
| `thesis` 응답에 `ai_summary` / `notable_changes` 추가 | `thesis/views/monitoring_views.py:216-218` | ✓ |
| `_infer_unit()` fallback 함수 | `thesis/views/monitoring_views.py:346-364` | ✓ |
| `IndicatorReadingsView` (`/{thesis_id}/indicators/{indicator_id}/readings/`) | `thesis/views/monitoring_views.py:260-290` | ✓ + days 한도 90 → **1825** 확장 + FMP fallback 추가 |

> 설계 대비 **확장 구현**: days 90일 → 5Y(1825), `_fetch_fmp_history()` fallback 추가 (`monitoring_views.py:293-343`).

#### PR-8 프론트엔드 — **부분 구현 (B)**

| 설계 항목 | 실제 상태 | 비고 |
|-----------|----------|------|
| `RealValueIndicatorCard.tsx` | ✓ 작성됨 (`components/thesis/dashboard/RealValueIndicatorCard.tsx`) | **그러나 page.tsx에서 미사용** |
| `AISummarySection.tsx` | ✓ 작성·연결 (`page.tsx:75-78`) | snapshotDate 필드 추가됨 |
| `NotableChangesSection.tsx` | ✓ 작성·연결 (`page.tsx:81-84`) | snapshotDate 필드 추가됨 |
| `app/thesis/[thesisId]/page.tsx` 교체 | ✓ 부분 — `OverallMoon` 제거됨, `IndicatorRow`로 진화 | RealValueIndicatorCard 대신 IndicatorRow 사용 |
| `formatRawValue` / `formatChangePct` / `supportLabel` | ✓ `lib/thesis/utils.ts` |
| Mock 데이터 확장 (raw_value 등) | ✓ `lib/thesis/mock.ts` (확인 미상) |

**핵심 차이**: `RealValueIndicatorCard`(고정 카드 + 분기 스파크라인)는 작성됐지만, 실제 사용되는 컴포넌트는 `IndicatorRow.tsx` (Phase 3 설계 문서에 없음). `IndicatorRow`는 카드 + 인라인 토글로 일간/분기 차트를 펼칠 수 있는 형태로, 사용자 메모리 `feedback_dashboard_layout.md`("1xN 세로 나열, 지표별 토글 차트")의 결정과 일치. → 즉 **설계가 진화**한 것이며, Phase 3 redesign 문서는 갱신되지 않음.

#### PR-9 프론트엔드 — **거의 미구현 (B/C)**

| 설계 항목 | 실제 상태 | 비고 |
|-----------|----------|------|
| `ChartToggleButton.tsx` | ✓ 작성됨 | **page.tsx에서 미사용** |
| `PeriodSelector.tsx` | ✓ 작성됨 | **page.tsx에서 미사용** |
| `IndividualMiniCharts.tsx` | ✓ 작성됨 | **page.tsx에서 미사용** (`useAllIndicatorReadings` 훅도 함께 orphan) |
| `CHART_COLORS` / `PERIOD_OPTIONS` 상수 | ✓ `constants.ts` | IndicatorRow 자체 차트가 사용 |
| `useAllIndicatorReadings` 쿼리 훅 | ✓ `queries.ts` | orphan |
| `MOCK_READINGS` Mock 데이터 | 확인 필요 | — |
| **삭제 대상**: `OverallMoon.tsx` | ✓ 파일 자체가 부재 → 삭제 완료 |
| **삭제 대상**: `DashboardIndicatorCard.tsx` | ✓ 파일 부재 |
| **삭제 대상**: `RecentChange.tsx` | ✓ 파일 부재 |
| **삭제 대상**: `MoonPhase.tsx` (common) | ✗ **잔존 + 사용 중** (`ThesisListCard.tsx:23`, `app/thesis/(list)/page.tsx:140`) |
| **삭제 대상**: `scoreToPhaseMeta()` (utils.ts) | ✗ **잔존** (`utils.ts:31`, `MoonPhase.tsx:36`에서 호출) |

**결론**: Phase 3 redesign PR-9는 컴포넌트만 만들고 **페이지 통합이 안 된 상태로 멈춤**. 대신 IndicatorRow 인라인 차트로 우회했음. 이는 redesign 문서의 "내부 점수 숨기기 + 차트 토글" 원칙은 충족하지만, "여러 지표 한 화면에 통합 미니차트" 의도는 미달성. orphan 컴포넌트 3개 + 1 훅 정리 필요.

#### PR-10 백엔드 — **부분 구현 (B)**

| 설계 항목 | 실제 상태 | 비고 |
|-----------|----------|------|
| `generate_thesis_summaries` Celery task | ✓ `thesis/tasks/summary.py:79-142` | Gemini 2.5 Flash 동기 호출 (Bug #8 회피) |
| `ai_summary` 멱등 생성 (force=True 옵션) | ✓ | — |
| Celery Beat 등록 (07:30 KST) | 확인 필요 | `config/settings/` 또는 DB scheduler 점검 필요 |
| `notable_changes` 풍부화 — `change_type`(sharp_move/direction_flip/threshold_cross/streak), `description`, `raw_value_before/after`, `change_pct`, `severity` | ✗ **미구현** | `snapshot_builder.py:106-122`는 **score 기반 단순 형식**(`indicator_id`/`indicator_name`/`prev_score`/`curr_score`/`delta`)만 저장. alert_engine 이벤트 재활용 안 함. |

**프론트엔드 영향**: `NotableChangesSection.tsx`는 `description`/`severity` 필드를 사용하지만 백엔드가 채우지 않으므로 **항상 fallback("오늘은 특별한 변화가 없어요") 또는 빈 description**이 표시될 가능성. `lib/thesis/types.ts`의 `NotableChange` 타입과 백엔드 실제 페이로드 불일치. 통합 점검 필요.

---

### 2. 원안 Phase 3 (Phase2_completion_summary.md §8 기준) — **전체 미구현 (C)**

| PR | 제목 | 핵심 설계 | 구현 상태 |
|----|------|-----------|----------|
| FE-PR-7 | 대시보드 탭 구조 + 상세 탭 | 3탭(관제/상세/히스토리) + 전제 CRUD UI | **C — 단일 페이지 구조 유지** (탭 없음) |
| FE-PR-8 | 히트맵 + 지표 상세 편집 | Finviz 스타일 히트맵 + weight/direction 편집 | **C** — 백엔드 `heatmap` 페이로드는 살아있음(`monitoring_views.py:222-225`) but 프론트 미사용. weight 편집 UI 없음. |
| FE-PR-9 | 히스토리 탭 | recharts 라인 차트 + 스냅샷 타임라인 | **C — 현재 IndicatorRow 인라인 차트가 부분 대체** |
| FE-PR-10 | 마감 아카이브 + 요약 | 마감 가설 목록 + ValidityMatrix UI | **C** — 백엔드 ValidityRecord는 저장 중이나 노출 화면 없음 |
| FE-PR-11 | 투자자 DNA 프로필 | AccuracyRing + CategoryChart + 기술 부채 정리 | **C** — 백엔드 InvestorDNA 갱신 중이나 사용자 노출 화면 없음 |

**판단**: 원안 FE-PR-7~11은 `thesis_control_phase3_frontend_redesign.md` 작성 시점에 **사실상 폐기**된 것으로 보임. redesign 문서가 "원칙 변경"(달 위상 추상 → 실제 값) 명시하면서 새 PR-7~10을 정의. 그러나 **명시적 폐기 결정 또는 "원안 미수행" 기록은 어디에도 없음** → DECISIONS.md 등에 기록되지 않은 암묵적 전환.

---

### 3. 통합 로드맵 Phase 2 / 3 / 4 — **전체 미구현 (C)**

`plan/thesis_control_integrated_roadmap.md`는 Phase 1만 명확히 구현되었음을 가정하고, Phase 2~4를 시간 차로 연기:

| 항목 | 모델/구현 위치 | 상태 |
|------|---------------|------|
| Phase 1 — `HypothesisEvent` | `models/learning.py:7-52` ✓ | A |
| Phase 1 — `ValidityRecord` | `models/learning.py:55-94` ✓ | A |
| Phase 1 — `InvestorDNA` 골격 | `models/learning.py:97-152` ✓ | A |
| Phase 1 — 마감 시 `ValidityRecord` 1건/지표 생성 | `views/thesis_views.py:85-103` ✓ | A |
| Phase 1 — 마감 시 `InvestorDNA` 갱신 | `views/thesis_views.py:295-336` ✓ | A |
| Phase 2 — `ValidityScore` 모델 | 부재 | **C** |
| Phase 2 — DNA 슬라이더 (`personalization_weight` UI) | 미구현 (필드는 있음) | **C** |
| Phase 2 — 역제안 (Contrarian Nudge) | 미구현 | **C** |
| Phase 2 — 상관계수 자동 할인 / Adaptive Decay / Sustained Extreme / 뉴스 센티먼트 | 미구현 | **C** |
| Phase 3 — `SyntheticBootstrapper` | 부재 | **C** |
| Phase 3 — `ThesisWeightLearner` (Online LR) | 부재 | **C** |
| Phase 3 — `is_synthetic` 필드 | `ValidityRecord`에 미존재 | **C** |
| Phase 4 — DNA 벡터화 / 코사인 유사도 / 사용자 유사도 | 부재 | **C** |

---

### 4. 검증 / 테스트 갭 (지표 신호)

- `frontend/__tests__/thesis/RealValueIndicatorCard.test.tsx` 존재 → 컴포넌트 자체는 단위 테스트가 있음. orphan 코드를 테스트로 보호하는 형태. 테스트가 **실사용 페이지 회귀를 잡지 못함.**
- `IndicatorRow.test.tsx`도 존재 → 실사용 컴포넌트.
- `IndividualMiniCharts.test.tsx` / `ChartToggleButton.test.tsx` / `PeriodSelector.test.tsx`는 부재로 보임 (미확인).

---

## 권고사항 (보고서 범위 외, 참고용)

1. **DECISIONS.md 갱신**: 원안 FE-PR-7~11 → Phase 3 redesign(PR-7~10) 전환 + IndicatorRow로 PR-8/9 통합한 결정을 명시 기록.
2. **orphan 컴포넌트 정리 또는 통합**: `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, `useAllIndicatorReadings` 훅 → 사용처가 없으면 제거하거나 page.tsx로 끌어올리기. 특히 RealValueIndicatorCard는 단위 테스트만 있고 실사용처 없음.
3. **`MoonPhase` / `scoreToPhaseMeta` 처리 결정**: 목록 화면에서 계속 쓸지, 아니면 redesign 문서대로 완전 제거할지 일관성 결정 필요.
4. **`notable_changes` 페이로드 풍부화**: PR-10 설계의 `change_type` / `description` / `raw_value_before/after` / `severity` 형식으로 `snapshot_builder.py` 또는 별도 task에서 alert_engine 이벤트 재활용해 채우기. 안 하면 NotableChangesSection이 사실상 빈 컴포넌트.
5. **InvestorDNA 노출 결정**: 데이터는 쌓이는데 UI가 없음 → 원안 FE-PR-11에 해당. Phase 2에 진입할 시점이면 노출, 아니면 기록만 한다는 의도를 명시.
6. **Beat 등록 확인**: `generate_thesis_summaries` task가 PeriodicTask DB에 등록되었는지 점검 (CLAUDE.md 버그 #28 — Beat schedule drift).

---

## 출처 참조

- 백엔드 모델: `thesis/models/{indicator,learning,monitoring,thesis,community,keyword}.py`
- 백엔드 뷰: `thesis/views/{thesis_views,monitoring_views,conversation_views}.py`
- 백엔드 서비스: `thesis/services/{snapshot_builder,alert_engine,arrow_calculator,thesis_state_machine,prompt_builder,thesis_builder,quarterly_metric_fetcher,...}.py`
- 백엔드 태스크: `thesis/tasks/{eod_pipeline,summary}.py`
- 백엔드 마이그레이션: `thesis/migrations/0001~0009`
- 프론트 라우트: `frontend/app/thesis/{(list),new,[thesisId]/{indicators,close}}/page.tsx`
- 프론트 컴포넌트: `frontend/components/thesis/{builder,dashboard,list,alerts,close,common,indicators,skeleton}/*.tsx`
- 프론트 라이브러리: `frontend/lib/thesis/{types,api,queries,mutations,mock,utils,constants,conversation}.ts`
- 설계 문서: `docs/thesis_control/plan/`, `docs/thesis_control/frontend/task_done/`, `docs/thesis_control/work_done/`
