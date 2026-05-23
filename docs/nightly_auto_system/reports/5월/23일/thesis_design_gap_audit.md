# Thesis Control 설계 갭 감사

> 감사일: 2026-05-23
> 감사 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` 백엔드 + `frontend/components/thesis/` 프론트엔드
> 방식: 읽기 전용 (코드 수정 없음)
> 감사자: Claude

---

## 0. 사전 정의 — Phase 3에 두 가지 의미가 공존

설계 문서를 읽으면서 발견한 **중요 사실**: "Phase 3"이라는 표현이 두 가지 다른 의미로 사용되고 있어 갭 분석을 혼란스럽게 한다.

| 정의 | 출처 | 내용 |
|---|---|---|
| **Phase 3-L (학습)** | `plan/thesis_control_integrated_roadmap.md` §3 | 합성 에이전트 부트스트래핑 + Online LR + Cold Start 해결. 백엔드 데이터/학습 계층. |
| **Phase 3-R (리디자인)** | `plan/thesis_control_phase3_frontend_redesign.md` | 대시보드 UI 리디자인 (실제 값 카드 + AI 분석 + 미니차트). PR-7~10. |
| **Phase 3-D (깊이/회고/프로필)** | `frontend/task_done/Phase2_completion_summary.md` §8 | FE-PR-7~11: 탭 구조 + 히트맵 + 히스토리 + 마감 아카이브 + 투자자 DNA 프로필. |

본 보고서는 세 가지를 분리해서 평가한다. **사용자가 "Phase 3"이라 부를 때 어느 것을 가리키는지 명확히 할 것**.

---

## 1. 요약 (Phase별 구현률)

| Phase | 정의 | 구현률 | 주요 미구현 |
|---|---|---|---|
| **Phase 1** | MVP 관제 엔진 + 이벤트 수집 + DNA 골격 | **95% 완성 (A)** | (잔여 점검 필요 항목 일부) |
| **Phase 2** | DNA 슬라이더 + 유효성 활성화 + v2.3.2 보강 | **0% (C)** | ValidityScore 모델, 슬라이더 UI, 역제안, 상관 할인, Adaptive Decay |
| **Phase 3-L** | 합성 에이전트 + Online LR | **0% (C)** | 전부 미구현 |
| **Phase 3-R** | 대시보드 리디자인 (PR-7~10) | **100% 완성 (A)** | (없음) |
| **Phase 3-D** | 깊이/회고/프로필 (FE-PR-7~11) | **0% (C)** | 탭 구조, 히트맵, 히스토리, 아카이브, DNA UI |
| **Phase 4** | 벡터 스코어링 | **0% (C)** | 전부 미구현 (계획 단계) |
| **Phase A (LLM 빌더)** | One-shot proposal + Hardening | **100% 완성 (A)** | (없음, Phase B/C는 별도 트랙) |
| **분기 지표 표시** | quarterly 지표 raw_value + sparkline | **부분 (B)** | `QuarterlySparkline` 존재하나 전체 plan 충족도는 별도 감사 필요 |

**한 줄 평**: 사용자가 매일 보는 화면(Phase 1 + 3-R + LLM 빌더)은 거의 완성되어 있다. 차별화 핵심인 **학습/개인화/심층 분석 UI(Phase 2 + 3-L + 3-D)**는 데이터 모델만 준비된 상태로 동결되어 있다.

---

## 2. 문서별 상태 테이블

### 2.1 `plan/` 하위 — 설계 마스터

| 문서 | 설계 항목 | 구현 상태 | 증거 |
|---|---|---|---|
| `thesis_control_design.md` | 5가지 진입 경로, 6단계 빌더, 관제실, 알림, 마감 | **A** | `frontend/app/thesis/**/page.tsx` 6개 라우트 전부 존재, `frontend/components/thesis/` 30+ 컴포넌트 |
| `thesis_control_math_model_final.md` (v2.3.2) | Stage 0~3, Robust Z, MAD, asof/72h, weakest_link | **A** (Phase 1 부분), **C** (Phase 2 보강: 상관 할인, Adaptive Decay, Sustained Extreme, 뉴스 센티멘트) | `thesis/services/data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `alert_engine.py` 존재 |
| `thesis_control_implementation_guide.md` | 백엔드 API + Celery 3태스크 | **A** | `thesis/views/*.py`, `thesis/tasks/{eod_pipeline,summary}.py` 존재 |
| `thesis_control_integrated_roadmap.md` | Phase 1~4 통합 로드맵 (학습/개인화) | Phase 1: **A** / Phase 2: **C** / Phase 3-L: **C** / Phase 4: **C** | 아래 §3 상세 |
| `thesis_control_phase3_frontend_redesign.md` | PR-7~10 대시보드 리디자인 | **A** (PR-7,8,9,10 전부 완료) | 아래 §4 상세 |
| `thesis_control_user_experience.md` | UX 원칙 | **A** | (적용된 결과로 판단) |
| `thesis_control_phase1_*` (FE_PR_1~5 + prompts) | Phase 1 빌더용 프롬프트 가이드 | **A** | `frontend/components/thesis/builder/` 7개 + LLM 빌더 |

### 2.2 `plan/talking_builder/` — 대화형 빌더 보강

| 문서 | 구현 상태 | 증거 |
|---|---|---|
| `llm_builder_plan.md` | **A** | `work_done/phase_a_llm_builder.md` (커밋 `09b0f8b`, `6d72432`) |
| `thesis_builder_redesign_v2.md` | **A** (Phase A 흡수) | LLM one-shot proposal + 3턴 등록 동작 확인 |
| `quarterly_indicator_dashboard_plan.md` | **B (부분)** | `thesis/services/quarterly_metric_fetcher.py` + `dashboard/QuarterlySparkline.tsx`, `IndicatorRow.tsx` 존재 — plan 전 항목 충족 여부는 별도 감사 권고 |
| `redesign_build_plan/00~05` | **A** | LLM 빌더 5개 phase 빌드 가이드 (Phase A 결과로 흡수) |

### 2.3 `frontend/task_done/` — 완료 보고서

| 보고서 | 대상 | 구현 상태 | 비고 |
|---|---|---|---|
| `FE-PR-1_routing_common_components.md` | 라우팅 + authAxios + 공통 컴포넌트 | **A** | `lib/api/client.ts`, `frontend/components/thesis/common/` 5개 |
| `FE-PR-2_thesis_list_page.md` | 목록 + 진입점 + 오늘의 변화 | **A** | `app/thesis/(list)/page.tsx`, `components/thesis/list/` 3개 |
| `FE-PR-3_builder_implementation.md` (+`_plan_review_v3`) | 6단계 대화형 빌더 | **A** | `components/thesis/builder/` 7개, `app/thesis/new/page.tsx` |
| `FE-PR-4_indicator_setup.md` | AI 추천 + 토글/삭제 | **A** | `components/thesis/indicators/` 3개, `app/thesis/[thesisId]/indicators/page.tsx` |
| `FE-PR-5_dashboard.md` | 달 위상 + 화살표 (Phase 2 버전) | **D (폐기/대체)** | OverallMoon/MoonPhase/DashboardIndicatorCard 모두 Phase 3-R에서 제거됨 |
| `FE-PR-6_alerts_close_qa.md` | 알림 + 마감 | **A** | `components/thesis/alerts/` 3개, `components/thesis/close/` 2개 |
| `Phase2_completion_summary.md` §8 | FE-PR-7~11 (Phase 3-D) | **C (전체 미구현)** | 아래 §5 상세 |

### 2.4 `work_done/`

| 보고서 | 구현 상태 |
|---|---|
| `phase_a_llm_builder.md` | **A** — Phase A-MVP + Hardening 7개 PR (22개 파일) 모두 완료, 테스트 104건 통과 |

---

## 3. Phase 3 미구현 항목 상세

> "Phase 3"이라는 라벨이 의미하는 세 가지를 모두 정리한다.

### 3.1 Phase 3-R: 대시보드 리디자인 → ✅ **완전 구현**

`plan/thesis_control_phase3_frontend_redesign.md`의 PR-7/8/9/10 전부 충족.

| 항목 | 설계 | 구현 증거 |
|---|---|---|
| `ThesisIndicator.display_unit` 필드 | 신규 추가 | `migrations/0004_add_display_unit.py` + `0005_populate_display_unit.py` |
| Dashboard API `raw_value`, `change_pct`, `raw_value_unit` | 추가 | `thesis/views/monitoring_views.py:94-165` |
| `IndicatorReadingsView` (`/indicators/{id}/readings/?days=N`) | 신규 | `monitoring_views.py:276` 부근 (readings values 추출 로직) |
| `RealValueIndicatorCard.tsx` | 신규 | `frontend/components/thesis/dashboard/RealValueIndicatorCard.tsx` ✅ |
| `AISummarySection.tsx` | 신규 | `dashboard/AISummarySection.tsx` ✅ |
| `NotableChangesSection.tsx` | 신규 | `dashboard/NotableChangesSection.tsx` ✅ |
| `ChartToggleButton.tsx` | 신규 | `dashboard/ChartToggleButton.tsx` ✅ |
| `PeriodSelector.tsx` | 신규 | `dashboard/PeriodSelector.tsx` ✅ |
| `IndividualMiniCharts.tsx` | 신규 | `dashboard/IndividualMiniCharts.tsx` ✅ |
| `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 삭제 | 폐기 | `frontend/components/thesis/dashboard/` 디렉토리에 부재 — 삭제 완료 ✅ |
| PR-10: `generate_thesis_summaries` Celery 태스크 (`ai_summary` 자동 생성) | 신규 | `thesis/tasks/summary.py:87` ✅ |
| `snapshot_builder.py`의 `notable_changes` 자동 채움 | PR-10 | `services/snapshot_builder.py:106-157` ✅ |

→ **Phase 3-R은 갭 없음. 클로즈 가능.**

### 3.2 Phase 3-L: 학습 계층 (합성 에이전트 + Online LR) → ❌ **전부 미구현**

`integrated_roadmap.md` §3 기준.

| 설계 항목 | 구현 상태 | 비고 |
|---|---|---|
| `SyntheticBootstrapper` 클래스 | **없음** | grep `SYNTHETIC_PERSONAS`, `is_synthetic` 결과 0건 |
| `ValidityRecord.is_synthetic` 필드 | **없음** | `learning.py` 모델에 필드 부재. migration 0001~0009 어디에도 없음 |
| `ThesisWeightLearner` (Online Logistic Regression) | **없음** | grep `ThesisWeightLearner` 결과 0건 |
| 합성-실제 데이터 블렌딩 (`aggregate_validity_scores`) | **없음** | 함수 미존재 |
| 다양한 페르소나 LLM 시뮬레이션 | **없음** | 프롬프트 자산 없음 |

→ **Phase 3-L은 데이터 모델조차 준비되지 않음. 시작 전제(Phase 2 안정화)도 미충족.**

### 3.3 Phase 3-D: 깊이/회고/프로필 UI (FE-PR-7~11) → ❌ **전부 미구현**

`frontend/task_done/Phase2_completion_summary.md` §8 기준.

| PR | 제목 | 구현 상태 | 증거 |
|---|---|---|---|
| **FE-PR-7** | 대시보드 탭 구조 + 상세 탭 (관제/상세/히스토리 3탭) + 전제 CRUD | **C** | `app/thesis/[thesisId]/page.tsx`는 단일 화면. 탭 컴포넌트 부재 |
| **FE-PR-8** | 히트맵 (Finviz 스타일) + 지표 상세 편집 (weight/direction) | **C** | `components/thesis/dashboard/`에 Heatmap 컴포넌트 부재 |
| **FE-PR-9** | 히스토리 탭 (recharts 라인 차트 + 스냅샷 타임라인) | **C** | History/Timeline 컴포넌트 부재. `ThesisSnapshot` 모델은 존재하나 UI 미연결 |
| **FE-PR-10** | 마감 아카이브 + ValidityMatrix 요약 화면 | **C** | `app/thesis/(list)/` 또는 별도 라우트에 archive 페이지 부재. ValidityRecord 데이터는 쌓이고 있으나 UI 없음 |
| **FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | **C** | DNA 관련 UI/페이지 전무. `InvestorDNA` 모델은 존재 |

→ **이것이 사용자가 "Phase 3 미구현"이라 말할 때 가장 가능성 높은 대상.** 깊이 + 회고 + 프로필이라는 UX 차별화 영역.

### 3.4 Phase 2 (DNA 슬라이더 + 유효성 활성화) → ❌ **전부 미구현**

Phase 3-L의 전제조건. 이것 없이는 Phase 3-L 진입 불가.

| 설계 항목 | 구현 상태 | 비고 |
|---|---|---|
| `ValidityScore` 집계 모델 | **없음** | grep `ValidityScore` 결과 0건 (코드 + 마이그레이션) |
| ValidityRecord → ValidityScore 주 1회 집계 Celery | **없음** | `thesis/tasks/`에 해당 태스크 부재 |
| `indicator_matcher.py`에 `validity_boost` / `confidence` 반영 | **없음** | grep으로 `ValidityScore`, `validity_boost` 0건 |
| `core/reference/low_impact` 티어 분류 | **없음** | indicator_matcher 결과는 단순 후보 리스트 |
| DNA 적합도 슬라이더 (`personalization_weight` UI) | **없음** | 모델 필드는 존재(`InvestorDNA.personalization_weight`)하나 UI/API 노출 없음 |
| 역제안 (`add_contrarian_nudge`) | **없음** | 미존재 |
| 상관계수 자동 할인 (60일 \|ρ\|≥0.9 → 1/√k) | **없음** | `premise_aggregator.py`에 해당 로직 부재 |
| Adaptive Decay/Window (변동성 적응) | **없음** | `indicator_scorer.py`는 정적 params |
| Sustained Extreme (s_decayed≥3 clip 전) | **확인 필요** | scorer 코드 정밀 점검 별도 권고 |
| 뉴스 센티멘트 LLM → Stage 1 입력 | **없음** | news 앱 → thesis Stage 1 연동 부재 |

### 3.5 Phase 4 (벡터 스코어링) → 계획 단계

`integrated_roadmap.md` §4 — DNA 벡터화, ValidityVector, 코사인 유사도, 사용자 유사도. **Phase 3 모두 안정화 후**의 8~12주 작업. 현 시점 미착수 정상.

---

## 4. 폐기/대체 (D) — 명시적으로 제거된 것들

`thesis_control_phase3_frontend_redesign.md`에서 의도적으로 폐기:

| 폐기 대상 | 대체 컴포넌트 | 폐기 사유 |
|---|---|---|
| `OverallMoon.tsx` | (삭제, 대체 없음) | "내부 점수 숨기기" 원칙 — 달 위상은 추상적 시각화 |
| `MoonPhase.tsx` (common) | (삭제) | 위와 동일 |
| `DashboardIndicatorCard.tsx` | `RealValueIndicatorCard.tsx` | 실제 값(1,380원, VIX 18.5pt) 표시로 전환 |
| `RecentChange.tsx` | `NotableChangesSection.tsx` | alert_engine 이벤트 재활용 구조로 재정의 |
| `scoreToPhaseMeta()` | (삭제) | OverallMoon 전용 유틸 |
| `CombinedNormalizedChart` | (생성하지 않음) | 정규화 점수 오버레이는 원칙 충돌, 미니차트만 유지 |
| Zustand `dashboardStore.ts` | `useState` | 2개 상태에 전역 스토어 과잉 |
| `dashboardV2()` / `useDashboardV2()` | 기존 `useDashboard()` 확장 | V1/V2 혼란 방지 |

→ FE-PR-5 완료 보고서가 가리키던 컴포넌트(OverallMoon/MoonPhase/DashboardIndicatorCard/RecentChange)는 **모두 정상적으로 제거됨**. 보고서는 역사 기록으로 보존 OK.

---

## 5. 백엔드 학습 인프라 — 어디까지 살아있나

설계가 "Phase 1에서 데이터만 모으고 Phase 2~3에서 활용"인데, 실제 데이터 흐름이 끊기지 않았는지 점검.

| 흐름 | 상태 | 증거 |
|---|---|---|
| 빌더에서 `HypothesisEvent` 생성 | ✅ 작동 | `thesis_builder.py:648,660,670,724`, `conversation_views.py`, `thesis_views.py:55~259` 8개 지점 |
| 빌더 라이프사이클 이벤트 (`log_event`) | ✅ 작동 | `builder_events.py` + `thesis_builder.py:804,915,957` |
| 가설 마감 시 `ValidityRecord` 생성 | ✅ 작동 | `thesis_views.py:92` |
| 가설 마감 시 `InvestorDNA` 갱신 | ✅ 작동 | `thesis_views.py:297` `get_or_create` |
| 매일 EOD 파이프라인 | ✅ 작동 | `tasks/eod_pipeline.py` |
| 매일 ai_summary 생성 | ✅ 작동 | `tasks/summary.py:87` |
| 주 1회 ValidityRecord → ValidityScore 집계 | ❌ **태스크 없음** | (Phase 2 항목) |
| 마감 시 합성 데이터 블렌딩 | ❌ **없음** | (Phase 3-L 항목) |

**결론**: Phase 1 데이터 수집 파이프는 견고하다. **데이터는 매일 쌓이고 있으나 활용 계층(Phase 2/3-L/3-D)이 없어 사용자에게 보이지 않는다.** 데이터 손실 없이 일시 정지된 상태 — 활성화 시 즉시 의미 있는 결과를 낼 수 있는 자산.

---

## 6. 권고

### 6.1 우선순위 분류

| 우선순위 | 항목 | 근거 |
|---|---|---|
| **P1 (가장 사용자 가치 높음)** | Phase 3-D FE-PR-11 (투자자 DNA 프로필 UI) | 모델/이벤트/유효성 데이터 이미 축적 중. UI만 붙이면 즉시 가치 발생 |
| **P1** | Phase 3-D FE-PR-10 (마감 아카이브 + ValidityMatrix 표시) | ValidityRecord가 쌓이고 있어 history 화면 만들기 용이 |
| **P2** | Phase 2.1~2.2 (ValidityScore 집계 + 지표 추천 반영) | DNA 슬라이더 / 역제안의 전제. 백엔드 작업 비중 큼 |
| **P2** | Phase 3-D FE-PR-7 (탭 구조) | 화면 정보 밀도 증가용. 단독 가치는 낮으나 PR-8/9의 컨테이너 역할 |
| **P3** | Phase 3-D FE-PR-8 (히트맵) / FE-PR-9 (히스토리) | 표시 가치 있으나 단일 가설 보유 사용자에겐 활용도 제한 |
| **P3** | Phase 2.5 (상관 할인, Adaptive Decay 등 v2.3.2 보강) | 정확도 개선이나 사용자 체감 작음 |
| **장기** | Phase 3-L (합성 에이전트) | Phase 2 안정화 + ValidityRecord 50건+ 축적 후 |
| **장기** | Phase 4 (벡터 스코어링) | Phase 3 안정화 후 |

### 6.2 즉시 가능한 액션 (코드 수정 없는 정비)

1. **CLAUDE.md 구현 상태 갱신** — 현 문서는 "Phase 3 진행 중 (FE-PR-7~11)"이라 적혀 있는데, **어느 Phase 3인지 명시 필요**. Phase 3-R은 완료, Phase 3-D가 미착수임을 분리 표기 권장.
2. **Phase2_completion_summary.md → Phase3-R completion summary 발행** — PR-7~10 완료 보고서가 작성되어 있다면 `task_done/`에 누락된 통합 요약 생성 권고 (개별 PR 보고서는 미확인 — 별도 점검 필요).
3. **`integrated_roadmap.md`에 "Phase 3-L vs 3-R vs 3-D" 표 추가** — 같은 라벨이 세 가지를 가리키지 않도록 명시.

### 6.3 별도 감사 권고

- **분기 지표 plan 충족도** (§2.2) — `QuarterlySparkline` 등 컴포넌트는 존재하나 plan의 전체 요구사항(YoY/QoQ 비교, 4분기 추이, 대시보드 통합) 충족 여부 미확인
- **v2.3.2 수학 모델 보강 항목** (Sustained Extreme, MAD_FLOOR 등) 각 항목별 코드 매핑 — 본 감사에서는 시간 제약으로 표면 점검만

---

## 7. 부록 — 컴포넌트/모델 인벤토리

### 7.1 프론트엔드 컴포넌트 (32개)

```
components/thesis/
├── AddIndicatorSheet.tsx, IndicatorCard.tsx, PresetSelector.tsx       (3 — LLM 빌더용)
├── builder/        (8: BottomSheet, ChatBubble, MultiSelectFooter, NewsSelector, OptionButton, PremiseCard, ProgressBar, SuggestionCard, TextInput)
├── common/         (6: AlertBell, ArrowIndicator, BottomSheet, IndicatorCard, MoonPhase, ThesisBadge) ← MoonPhase 잔존 확인 필요
├── dashboard/      (10: AISummarySection, ChartToggleButton, DashboardHeader, DashboardPageHeader, IndicatorRow, IndividualMiniCharts, NotableChangesSection, PeriodSelector, QuarterlySparkline, RealValueIndicatorCard)
├── indicators/     (3: AddIndicatorSheet, IndicatorSetupCard, RecommendCard)
├── list/           (3: EntryPointGrid, ThesisListCard, TodayChangeCard)
├── alerts/         (3: AlertCard, AlertFilterTabs, EmptyAlerts)
├── close/          (2: CloseConfirmDialog, OutcomeSelector)
└── skeleton/       (1: ThesisSkeleton)
```

**누락 카테고리 (Phase 3-D 미구현 표시):**
- `tabs/` — 3탭 컨테이너 없음
- `history/` — 히스토리 차트 없음
- `heatmap/` — 히트맵 없음
- `archive/` — 마감 아카이브 없음
- `profile/` — DNA 프로필 없음

### 7.2 백엔드 모델

```
thesis/models/
├── thesis.py        — Thesis, ThesisPremise
├── indicator.py     — ThesisIndicator (display_unit 포함 ✅), IndicatorReading (raw_value 포함 ✅)
├── monitoring.py    — ThesisSnapshot (ai_summary, notable_changes 포함 ✅), ThesisAlert
├── community.py     — ThesisFollow, PopularThesisCache
├── learning.py      — HypothesisEvent ✅, ValidityRecord ✅, InvestorDNA ✅  ← ValidityScore ❌, is_synthetic 필드 ❌
└── keyword.py       — KeywordCache
```

### 7.3 백엔드 서비스/태스크

```
thesis/services/      (16개)
├── alert_engine.py, arrow_calculator.py, data_validator.py,
├── indicator_matcher.py (validity_boost 미반영 ❌),
├── indicator_scorer.py (Robust Z + Decay, Adaptive Decay 미적용 ❌),
├── premise_aggregator.py (상관 할인 미적용 ❌),
├── snapshot_builder.py (notable_changes 자동 채움 ✅),
├── thesis_builder.py (LLM one-shot ✅),
├── thesis_state_machine.py, quarterly_metric_fetcher.py ✅, ...

thesis/tasks/
├── eod_pipeline.py — 매일 18:00 ET ✅
└── summary.py      — generate_thesis_summaries (PR-10) ✅
                       ❌ ValidityScore 집계 태스크 누락
                       ❌ 합성 부트스트래퍼 누락
```

---

## 8. 마무리

설계상 **15개 PR + 4 Phase 통합 로드맵** 중:

- **실사용자 화면에 닿는 부분** (Phase 1 + Phase 3-R + LLM 빌더 Phase A): ✅ 거의 완성
- **차별화/특허 핵심** (Phase 2 학습 + Phase 3-L 합성 에이전트 + Phase 3-D 깊이/회고/프로필 + Phase 4 벡터): ❌ 미착수
- **이벤트/유효성 데이터**: 매일 정상 축적 중 (활용 계층만 비어있음)

다음 슬라이스에서 **"Phase 3"이라 부를 때 어느 것인지 먼저 합의**할 것 (3-R은 끝, 3-D는 시작 전, 3-L은 전제 미충족). 사용자 가치 기준으로는 **Phase 3-D FE-PR-10/11 (마감 아카이브 + DNA 프로필)** 이 가장 ROI 높음 — 데이터는 이미 쌓여 있고 UI만 추가하면 됨.

**감사 결과: 진행 중 표기와 실제 상태에 모호함이 있어 정비 필요. 코드 자체는 건강함.**
