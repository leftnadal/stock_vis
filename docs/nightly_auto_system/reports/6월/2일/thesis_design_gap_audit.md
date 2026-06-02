# Thesis Control 설계 갭 감사

> 감사일: 2026-06-02 · 읽기 전용 (코드 수정 없음)
> 범위: `docs/thesis_control/` 설계서 ↔ `thesis/`(BE) + `frontend/components/thesis/`·`frontend/app/thesis/`(FE)
> 분류 기준: **(A)** 완전 구현 · **(B)** 부분 구현 · **(C)** 미구현 · **(D)** 폐기/대체

---

## 0. 핵심 발견 — "Phase 3"는 서로 다른 3개 트랙을 가리킨다

감사 중 가장 중요한 사실: 설계 문서마다 **"Phase 3"·"PR-7~11"이라는 명칭을 충돌되게 사용**하고 있다. 갭을 정확히 보려면 먼저 트랙을 분리해야 한다.

| 트랙 | 출처 문서 | "Phase 3"가 의미하는 것 | PR 번호 |
|------|----------|------------------------|---------|
| **T1. 백엔드 학습/개인화** | `plan/thesis_control_integrated_roadmap.md` | 합성 에이전트 + Online LR 자동학습 (특허 핵심) | — |
| **T2. 대시보드 리디자인** | `plan/thesis_control_phase3_frontend_redesign.md` (v1.0 FINAL) | 내부점수 숨기고 **실제값** 카드 + AI요약 + 미니차트 | PR-7~10 |
| **T3. 대시보드 고도화** | `frontend/task_done/Phase2_completion_summary.md` §8 | **깊이+회고+프로필**: 탭 구조 + 히트맵 + 히스토리 + 아카이브 + DNA 프로필 | FE-PR-7~11 |

> ⚠️ T2와 T3은 **둘 다 "PR-7~10/11"이라는 번호를 쓰지만 완전히 다른 작업**이다. 사용자가 진행 상황으로 인지하는 "Phase 3 (깊이+회고+프로필: FE-PR-7~11)"은 **T3**이다. 그러나 **실제로 코드에 구현된 것은 대부분 T2**이며, **T3은 거의 착수되지 않았다.** 이 명칭 충돌이 "진행 중"이라는 인식과 실제 구현 사이의 갭의 근본 원인이다.
>
> `redesign_build_plan/00_total_plan.md`의 talking_builder(LLM 빌더 재설계)는 또 다른 **별개 트랙**으로, "FE-PR-7~11 완료 후 착수"가 선행조건이라 명시되어 있다.

---

## 1. 요약 — Phase별 구현률

| 트랙 / Phase | 구현률 | 상태 | 비고 |
|--------------|--------|------|------|
| **Phase 1 (관제 엔진 + 이벤트/유효성 기록)** | ~95% | 🟢 거의 완료 | 모델·기록·DNA 집계 동작. 이벤트 13종 중 11종만 기록 |
| **Phase 2-FE (핵심 루프, FE-PR-1~6)** | 100% | 🟢 완료 | 목록→빌더→지표→대시보드→알림→마감 |
| **T2. 대시보드 리디자인 (PR-7~10)** | ~70% | 🟡 부분 | PR-7/PR-10 BE 완료, PR-8/9 기능은 `IndicatorRow`로 통합 재구현, 설계 컴포넌트 다수 고립 |
| **T1. 백엔드 Phase 2 (유효성 활성화)** | 0% | 🔴 미착수 | ValidityScore·DNA슬라이더·역제안 전무 |
| **T1. 백엔드 Phase 3 (합성에이전트/LR)** | 0% | 🔴 미착수 | SyntheticBootstrapper·ThesisWeightLearner 전무 |
| **T1. 백엔드 Phase 4 (벡터)** | 0% | 🔴 미착수 | — |
| **T3. 대시보드 고도화 (FE-PR-7~11)** | ~3% | 🔴 거의 미착수 | 탭/히트맵/히스토리/아카이브/DNA프로필 전무 |
| **talking_builder (LLM 빌더)** | 부분 | 🟡 | Phase A-MVP/Hardening 완료(work_done), Phase B 일부 흔적(KeywordCache migration) |

---

## 2. 문서별 상태 테이블

| 설계 문서 | 정의 대상 | 구현 상태 | 근거 |
|-----------|----------|-----------|------|
| `plan/thesis_control_integrated_roadmap.md` | 4-Phase 학습 로드맵 | Phase 1만 ~95%, Phase 2~4 = (C) | `thesis/models/learning.py` 존재, ValidityScore 등 부재 |
| `plan/thesis_control_design.md` | 수학엔진(Stage0~3)+모델 | (A) 관제 엔진 가동 | `services/` 다수, `tasks/eod_pipeline.py` |
| `plan/thesis_control_implementation_guide.md` | 구현 가이드 | (A) 기반 완료 | — |
| `plan/thesis_control_phase3_frontend_redesign.md` (T2) | PR-7~10 실제값 대시보드 | (B) ~70% | 아래 §3 |
| `frontend/task_done/Phase2_completion_summary.md` §8 (T3) | FE-PR-7~11 고도화 | (C) 미구현 | 아래 §4 |
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 핵심 루프 | (A) 6개 PR 전부 완료 | `app/thesis/*` 라우팅 7개 가동 |
| `plan/talking_builder/redesign_build_plan/*` | LLM 빌더 재설계 | (B) Spike+A 완료 | `work_done/phase_a_llm_builder.md` |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 대시보드 | (A) 구현 | `QuarterlySparkline.tsx`, `is_quarterly`/`quarterly_history` |

---

## 3. T2 — 대시보드 리디자인(PR-7~10) 상세

설계서 `phase3_frontend_redesign.md` 기준 PR별 대조.

### PR-7 (백엔드 확장) — (A) 완전 구현
- `thesis/models/indicator.py:73` `display_unit` 필드 존재
- migration `0004_add_display_unit.py` + `0005_populate_display_unit.py` 존재
- `IndicatorReadingsView` → `thesis/urls.py`에 등록(`<thesis_id>/indicators/<indicator_id>/readings/`)
- `raw_value`/`change_pct` Dashboard 응답 포함 (FE `IndicatorRow.tsx:46`에서 소비)

### PR-8 (실제값 카드 + AI분석) — (B) 부분 / 설계와 다르게 통합
- `AISummarySection.tsx`, `NotableChangesSection.tsx` → **page에 연결됨** `app/thesis/[thesisId]/page.tsx:75,81` ✅
- **`RealValueIndicatorCard.tsx`는 (D) 대체됨**: page는 이 컴포넌트 대신 `IndicatorRow.tsx`를 렌더(`page.tsx:115`). `RealValueIndicatorCard`는 테스트(`__tests__/thesis/RealValueIndicatorCard.test.tsx`)에서만 참조되는 **고립 컴포넌트**. 기능(raw_value·지지/반박·분기 스파크라인)은 `IndicatorRow`가 흡수.

### PR-9 (미니차트 + 기간선택 + 정리) — (B) 부분 / 다수 고립
- `ChartToggleButton.tsx`, `PeriodSelector.tsx`, `IndividualMiniCharts.tsx` 모두 **생성됐으나 `app/thesis/[thesisId]/page.tsx`에서 import되지 않음 → 고립(dead) 컴포넌트**
- `useAllIndicatorReadings` 훅(`lib/thesis/queries.ts:73`)도 어디서도 호출되지 않음
- 대신 **차트는 `IndicatorRow.tsx:59`가 `useIndicatorReadings`로 행(行)별 인라인 렌더** → 토글/기간선택 UI 없이 단순화 구현
- 설계의 "삭제 대상"(`OverallMoon`/`DashboardIndicatorCard`/`RecentChange`)은 대시보드에서 제거됨. 단 **`MoonPhase.tsx`는 의도대로 유지**되어 목록(`app/thesis/(list)/page.tsx:140`)·`ThesisListCard.tsx:23`에서 여전히 사용 중(설계 허용 범위)

### PR-10 (AI 모니터링 파이프라인) — (A) 구현 (사후 추가)
- `thesis/tasks/summary.py` `generate_thesis_summaries` 존재 (Gemini 2.5 Flash **동기** 호출, Bug #8 회피 준수, 멱등). 주석상 "audit P0 #15"로 사후 채워진 것으로 보임
- `notable_changes`는 `snapshot_builder.py:108-160`이 채움. 단 설계는 *alert_engine 이벤트(direction_flip/sharp_move) 재활용*을 명시했으나 **실제 구현은 `|score 변화|≥0.3` 기반** → 기능적 충족이나 데이터 출처가 설계와 상이 (경미한 갭)

---

## 4. T3 — Phase 3 "깊이+회고+프로필"(FE-PR-7~11) 미구현 항목 상세

> 출처: `Phase2_completion_summary.md` §8 "Phase 3 계획". **이것이 사용자가 인지하는 진행 중 작업이나, 코드 근거상 거의 착수되지 않음.**

| PR | 설계 범위 | 상태 | 근거 (부재 확인) |
|----|----------|------|------------------|
| **FE-PR-7** | 대시보드 **탭 구조**(관제/상세/히스토리) + 전제 CRUD 탭 | **(C) 미구현** | `app/thesis/[thesisId]/page.tsx`는 단일 스크롤 레이아웃. 탭 컴포넌트 없음. `Tabs` grep 결과 thesis 도메인 내 0건 |
| **FE-PR-8** | **히트맵**(Finviz 스타일) + 지표 weight/direction 편집 | **(C) 미구현** | 히트맵 컴포넌트는 `screener/SectorHeatmap`만 존재, thesis용 없음 |
| **FE-PR-9** | **히스토리 탭** (recharts 라인 + 스냅샷 타임라인) | **(C) 미구현** | 스냅샷 타임라인 화면 부재. (지표별 인라인 차트는 T2에서 별도 구현) |
| **FE-PR-10** | 마감 **아카이브** + 요약 + ValidityMatrix | **(C) 미구현** | `close/`에는 `CloseConfirmDialog`·`OutcomeSelector`만. 마감 가설 아카이브 목록·ValidityMatrix 화면 없음 |
| **FE-PR-11** | **투자자 DNA 프로필** (AccuracyRing + CategoryChart) | **(C) 미구현** | `AccuracyRing`/`CategoryChart`/`DnaProfile` grep 0건. BE `InvestorDNA` 모델은 있으나 이를 노출하는 API·화면 없음 |

### 연결된 백엔드 갭 (T1 Phase 2~4 = 전부 미착수)
FE-PR-10/11(회고·프로필)은 백엔드 학습 레이어에 의존하는데 해당 레이어가 비어 있다:

| 백엔드 항목 | Phase | 상태 | 근거 |
|-------------|-------|------|------|
| `HypothesisEvent` 모델 | 1 | (A) | `models/learning.py:7` (13종 정의) |
| 이벤트 **기록 삽입** | 1 | **(B)** | 13종 중 **`ai_suggestion_rejected`·`premise_modified` 2종 미기록** |
| `ValidityRecord` + 2×2 매트릭스 | 1 | (A) | `views/thesis_views.py:284-293` (점수 0.3/-0.2/-0.15/0.05 일치). 단 `market_regime`은 `'normal'` 하드코딩 |
| `InvestorDNA` 집계 | 1 | (A) | `views/thesis_views.py:302-343` 마감 시 갱신. `top_down_ratio`/`ai_accept_rate` property 동작 |
| `ValidityScore` 집계 + 활성화 | 2 | **(C)** | 모델·태스크 전무 |
| DNA 슬라이더 / 역제안(Contrarian Nudge) | 2 | **(C)** | `indicator_matcher.py` 순수 키워드 룰만. `personalization_weight` 필드는 있으나 **미사용** |
| `SyntheticBootstrapper` / Online LR | 3 | **(C)** | 페르소나·합성가설·가중치학습 전무 |
| `ValidityRecord.is_synthetic` 필드 | 3 | **(C)** | 미생성 (Phase 3 블렌딩 전제) |
| DNA 벡터화 / 코사인 유사도 | 4 | **(C)** | 전무 |

---

## 5. 즉시 정리 권장 (감사 관점 — 수정은 별도 승인 필요)

1. **고립 컴포넌트 4종 처리 결정**: `RealValueIndicatorCard`·`ChartToggleButton`·`PeriodSelector`·`IndividualMiniCharts` + `useAllIndicatorReadings` 훅은 page에 연결되지 않은 채 빌드에 포함. `IndicatorRow`로 기능 통합이 최종안이면 **삭제 또는 page 연결** 중 택1 (현재는 죽은 코드 + 테스트만 유지).
2. **PR 번호 충돌 해소**: T2(`phase3_frontend_redesign`)와 T3(`Phase2_completion_summary §8`)이 동일 번호(PR-7~10/11)를 사용 → 문서에 트랙 접두어(예: `RDS-PR-7` vs `DASH-PR-7`) 부여 권장. 현 상태로는 "FE-PR-7 완료 여부"를 물으면 답이 트랙에 따라 갈림.
3. **이벤트 기록 2종 누락**: `ai_suggestion_rejected`·`premise_modified` 미기록 → DNA·유효성 학습의 입력 데이터 결손. Phase 2 착수 전 보강 필요.
4. **notable_changes 데이터 출처 불일치**: 설계(alert 이벤트 재활용) vs 구현(score Δ≥0.3). 의도된 단순화면 설계서 갱신, 아니면 alert 연동 보강.

---

## 부록 — 판정 근거 파일 인덱스

- BE 모델: `thesis/models/learning.py`, `thesis/models/indicator.py:73`, `thesis/models/monitoring.py`
- BE 로직: `thesis/views/thesis_views.py`(이벤트/유효성/DNA), `thesis/services/snapshot_builder.py`, `thesis/services/indicator_matcher.py`, `thesis/tasks/summary.py`
- BE migration: `thesis/migrations/0004·0005`(display_unit), `0006`(keyword_cache), `0009`(recommendation_reason)
- FE page: `frontend/app/thesis/[thesisId]/page.tsx`(연결 컴포넌트 확정 근거)
- FE 컴포넌트: `frontend/components/thesis/dashboard/`(IndicatorRow 사용 / Chart·RealValue 고립)
- 설계: `docs/thesis_control/plan/*`, `docs/thesis_control/frontend/task_done/Phase2_completion_summary.md`, `docs/thesis_control/work_done/phase_a_llm_builder.md`
