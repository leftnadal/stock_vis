# Thesis Control 설계 갭 감사

> 감사일: 2026-05-12
> 감사 대상: `docs/thesis_control/` (설계) ↔ `thesis/` + `frontend/components/thesis/` + `frontend/app/thesis/` (구현)
> 감사 범위: Phase 1~3 설계 전체, FE-PR-1~11 cross-reference
> 모드: 읽기 전용 (코드 수정 없음)

---

## 0. 가장 먼저 짚어야 할 점 — "Phase 3"이 세 갈래로 정의됨

설계 문서를 가로질러 보면 **"Phase 3"이라는 단어가 서로 다른 세 개의 작업 묶음을 가리키고 있다.** 갭 분석을 시작하기 전에 이 모호함을 정리해야 한다.

| 출처 문서 | 다루는 범위 | FE-PR-7~11 번호 의미 |
|----------|------------|----------------------|
| **A. `Phase2_completion_summary.md` §8 "Phase 3 계획"** | **깊이 + 회고 + 프로필** — 사용자 질문의 원안 | PR-7 탭구조 / PR-8 히트맵 / PR-9 히스토리 / PR-10 마감 아카이브 / PR-11 DNA 프로필 |
| **B. `thesis_control_phase3_frontend_redesign.md`** | **대시보드 UI 리디자인** (실세계 값으로 표시 전환) | PR-7 BE 확장 / PR-8 카드+요약 / PR-9 미니차트 / PR-10 Celery 요약 (PR-11 없음) |
| **C. `thesis_control_integrated_roadmap.md` §3** | **합성 에이전트 + 자동학습** (특허 차별점) | FE-PR 번호 사용하지 않음 |
| 부수 흐름 | `talking_builder/llm_builder_plan.md`, `quarterly_indicator_dashboard_plan.md` | "Phase 3 FE-PR-7~11 완료 후 착수" 명시 — A 또는 B에 종속 |

같은 번호(`FE-PR-7~11`)가 두 문서에서 의미를 다르게 갖는 충돌이 존재한다. 실제 커밋된 코드를 보면 **B(리디자인) 쪽의 산출물이 dashboard 컴포넌트로 다수 존재**하지만, **A(탭구조/DNA)의 산출물은 거의 없다**. 보고서는 A·B·C를 각각 분리해서 평가한다.

---

## 1. 요약 — Phase별 구현률

| Phase | 정의 | 구현률 | 상태 |
|-------|------|--------|------|
| Phase 1 (MVP) | 관제 엔진 v2.3.2 + 이벤트 수집 + 유효성 기록 + DNA 골격 | **~95%** | (A) 완전 구현 |
| Phase 2 핵심 루프 | 가설 목록 / 빌더 / 지표 설정 / 대시보드 / 알림 / 마감 (FE-PR-1~6) | **100%** | (A) 완전 구현 |
| Phase 2 후속 (v2.3.2 정교화) | 상관계수 할인·Adaptive Decay·Sustained Extreme·뉴스 센티먼트 | **~10%** | (C) 미구현 (정교화만 미적용) |
| **Phase 3-A (깊이+회고+프로필)** | 탭구조 / 히트맵 / 히스토리 / 마감 아카이브 / DNA 프로필 (FE-PR-7~11) | **~15%** | **(C) 거의 미구현** |
| **Phase 3-B (UI 리디자인)** | 실세계 값 카드 / AI 요약 / 미니차트 / Celery 요약 | **~90%** | (A) 사실상 완료 |
| Phase 3-C (합성 에이전트) | LLM 페르소나 → 합성 가설 → ValidityScore 사전학습 | **0%** | (C) 미구현 |
| 후속 흐름 (Phase 4+) | LLM 빌더 v2 리디자인 / Quarterly indicator dashboard | **부분 (분기 fetcher만)** | (B) 부분 구현 |

> 사용자 질문의 "Phase 3 (깊이+회고+프로필)"은 **A 갈래**이고, 이쪽이 가장 비어있다. 반면 dashboard 디렉토리에 새로 추가된 컴포넌트들은 B 갈래의 산출물이다.

---

## 2. 문서별 상태 테이블

### 2.1 `docs/thesis_control/plan/`

| 문서 | 라인 | 다루는 범위 | 구현 상태 | 비고 |
|------|------|-------------|-----------|------|
| `thesis_control_design.md` | 1,370 | 전체 사용자 경험 + 정보 구조 + 마감 복기 + 깊이 조절([더 자세히]) | (B) 부분 구현 | "[근거] 탭", "마감 복기", "[더 자세히]" 버튼 등 깊이성 UX 미반영 |
| `thesis_control_math_model_final.md` | 1,153 | v2.3.2 수학 모델 (Stage 0~3) | (A) 거의 완전 구현 | 상관계수 자동 할인·Adaptive Decay·Sustained Extreme은 미적용 (Phase 2 후속) |
| `thesis_control_implementation_guide.md` | 286 | 디렉토리/모델/태스크 가이드 | (A) 완전 구현 | thesis/models, /services, /tasks, /views 모두 매핑 일치 |
| `thesis_control_integrated_roadmap.md` | 660 | Phase 1~3 단계별 모델 + 마이그레이션 | (B) Phase 1·2 구현, Phase 3 미구현 | 합성 에이전트(§3)는 0% — `SyntheticBootstrapper`, `ValidityScore` 모델 없음 |
| `thesis_control_phase3_frontend_redesign.md` | 1,095 | UI 실세계 값 리디자인 (FE-PR-7~10 재정의) | (A) 사실상 완료 | display_unit 마이그레이션·IndicatorReadingsView·dashboard 컴포넌트 6종 모두 존재 |

### 2.2 `docs/thesis_control/plan/talking_builder/`

| 문서 | 라인 | 다루는 범위 | 구현 상태 | 비고 |
|------|------|-------------|-----------|------|
| `llm_builder_plan.md` | 563 | 빌더 LLM 모드 보강 (Gemini) | (A) 구현 완료 | `thesis_builder.py`, `builder_state.py`, `builder_events.py`, `prompt_builder.py`, `llm_postprocess.py` 모두 존재 |
| `thesis_builder_redesign_v2.md` | 1,110 | 빌더 UX 리디자인 (Phase 3 FE-PR-7~11 후 착수) | (C) 미구현 | 선행 PR-7~11(A 정의) 미완으로 자동 보류 상태 |
| `quarterly_indicator_dashboard_plan.md` | 424 | 분기 지표 대시보드 (스파크라인 + 20분기 히스토리) | (B) 부분 구현 | `quarterly_metric_fetcher.py` + `QuarterlySparkline.tsx` 존재, 별도 분기 대시보드 페이지 미구현 |

### 2.3 `docs/thesis_control/frontend/task_done/` — 완료 보고서 cross-reference

| 완료 보고서 | 자칭 산출물 | 실제 코드 확인 |
|-------------|-------------|---------------|
| `FE-PR-1_routing_common_components.md` | 라우팅 7개 + 공통 컴포넌트 5개 + authAxios | ✅ `app/thesis/(list)/`, `app/thesis/new`, `app/thesis/[thesisId]/`, `components/thesis/common/{AlertBell,ArrowIndicator,BottomSheet,MoonPhase,ThesisBadge}.tsx` |
| `FE-PR-2_thesis_list_page.md` | 가설 목록 + 오늘의 변화 + 진입점 | ✅ `(list)/page.tsx`, `list/{ThesisListCard,TodayChangeCard,EntryPointGrid}.tsx` |
| `FE-PR-3_builder_implementation.md` + `FE-PR-3_plan_review_v3.md` | 대화형 빌더 (6단계) | ✅ `new/page.tsx`, `builder/{ChatBubble,OptionButton,PremiseCard,ProgressBar,SuggestionCard,MultiSelectFooter,TextInput,NewsSelector,BottomSheet}.tsx` |
| `FE-PR-4_indicator_setup.md` | 지표 설정 (AI 추천 + 토글/삭제) | ✅ `[thesisId]/indicators/page.tsx`, `indicators/{IndicatorSetupCard,AddIndicatorSheet,RecommendCard}.tsx` |
| `FE-PR-5_dashboard.md` | 관제실 대시보드 (달 위상 + 화살표) | ⚠️ 부분 — `OverallMoon`/`DashboardIndicatorCard`/`RecentChange`는 **이미 삭제됨** (Phase 3-B 리디자인이 대체) |
| `FE-PR-6_alerts_close_qa.md` | 알림 + 마감 + API 수정 + QA | ✅ `(list)/alerts/page.tsx`, `[thesisId]/close/page.tsx`, `alerts/*`, `close/*` |
| `Phase2_completion_summary.md` | Phase 2 종합 + Phase 3-A 계획 (PR-7~11) 명시 | ✅ Phase 2 본문 모두 구현, **Phase 3-A 계획 부분은 거의 미구현** |

### 2.4 `docs/thesis_control/work_done/`

| 보고서 | 다루는 범위 | 상태 |
|--------|-------------|------|
| `phase_a_llm_builder.md` | LLM 빌더 인프라 (services/, models/, tasks/) | ✅ 구현 완료 |

> **누락**: Phase 3-B 리디자인(PR-7~10)에 해당하는 완료 보고서 `FE-PR-7~10_*.md`가 `task_done/` 폴더에 **존재하지 않는다**. 실제 코드는 들어있는데 완료 보고서가 비어있는 비대칭. 보고서 폴더에 회수가 필요한 항목.

---

## 3. Phase 3-A (깊이 + 회고 + 프로필) 미구현 항목 상세

> 본 절은 사용자 질문의 "Phase 3 (깊이+회고+프로필) 설계 vs 현재 구현 상태"에 집중한다.
> 그라운드 트루스: `frontend/task_done/Phase2_completion_summary.md` §8.

### 3.1 FE-PR-7 — 대시보드 탭 구조 + 상세 탭 + 전제 CRUD

| 항목 | 설계 | 현재 코드 | 분류 |
|------|------|-----------|------|
| 3탭(관제/상세/히스토리) 구조 | 필요 | `[thesisId]/page.tsx` 단일 페이지, 탭 컴포넌트 없음 | **(C) 미구현** |
| 전제 추가/수정/삭제 UI | 필요 | `ThesisPremiseViewSet` BE는 존재, FE에서 전제 CRUD 화면 없음 | **(C) 미구현** |
| `PremiseCard` 인라인 편집 | 필요 | `builder/PremiseCard.tsx`는 빌더 전용 (편집 없음, 카테고리 배지만) | (C) 미구현 |
| `/thesis/[id]/detail` 또는 `/edit` 라우트 | 필요 | 없음 | (C) 미구현 |

> 검색 결과 `TabSection`, `HistoryTab` 등 탭 관련 컴포넌트 0건 (`Grep thesis_tabs|TabSection|HistoryTab` → No files found).

### 3.2 FE-PR-8 — 히트맵 + 지표 상세 편집 (Finviz 스타일)

| 항목 | 설계 | 현재 코드 | 분류 |
|------|------|-----------|------|
| Finviz 스타일 히트맵 | 필요 | 없음. dashboard에 `RealValueIndicatorCard`(B 리디자인)만 존재 | **(C) 미구현** |
| 지표별 weight / direction 인라인 편집 | 필요 | `IndicatorSetupCard.tsx`는 토글/삭제만, weight·epsilon·window·decay 편집 UI 없음 | **(C) 미구현** |
| `ThesisIndicator` PATCH API에 가중치 노출 | 필요 | `ThesisIndicatorViewSet`은 존재하나 FE에서 가중치 PATCH 호출 없음 | (C) 미구현 |
| `HeatmapView`/`HeatmapCell` 컴포넌트 | 필요 | 없음 (`Grep HeatmapView` → 0건) | (C) 미구현 |

### 3.3 FE-PR-9 — 히스토리 탭 (스냅샷 타임라인)

| 항목 | 설계 | 현재 코드 | 분류 |
|------|------|-----------|------|
| recharts 라인 차트로 스냅샷 타임라인 | 필요 | `IndividualMiniCharts.tsx`로 **부분 대체** — 단, 이는 지표별 raw_value 시계열이지 "스냅샷 overall_score 타임라인"이 아님 | **(B) 부분 구현** |
| ThesisSnapshot 시계열 조회 API | 필요 | `ThesisSnapshot` 모델 존재, 시계열 조회용 list 엔드포인트 없음 (DashboardView는 latest 1건) | (C) 미구현 |
| 기간 선택 (7D/14D/30D) | 필요 | `PeriodSelector.tsx` 존재 — IndividualMiniCharts에서 활용 중 | (A) 완전 구현 |
| 알림 타임라인과 결합 | 필요 | 알림은 `/thesis/alerts` 별도 화면, 히스토리 탭과 통합 안 됨 | (C) 미구현 |

> 정리: PeriodSelector·IndividualMiniCharts는 **B 리디자인 산출물**로 만들어졌고, A의 "히스토리 탭"이 요구하는 overall_score 타임라인은 아직 없다.

### 3.4 FE-PR-10 — 마감 아카이브 + 마감 요약 (ValidityMatrix)

| 항목 | 설계 | 현재 코드 | 분류 |
|------|------|-----------|------|
| 마감 가설 목록 페이지 (`/thesis/archive` 또는 필터) | 필요 | 없음. `(list)/page.tsx`는 active 가설만 조회하는 구조로 보임 | **(C) 미구현** |
| 마감 가설 상세 요약 페이지 | 필요 | 없음 | (C) 미구현 |
| `ValidityMatrix` 2×2 표 시각화 | 필요 | `ValidityRecord` BE 모델 + score 매트릭스 로직은 존재, FE 컴포넌트 없음 | **(C) 미구현** |
| 마감 시 AI 복기 텍스트 표시 | `thesis_control_design.md §3.9`에 정의 | BE 미생성, FE 미렌더 | **(C) 미구현** |

> `thesis_control_design.md §3.9` "가설 마감 시 AI 복기"는 별도 LLM 호출이 필요한데, `thesis/tasks/summary.py`의 `generate_thesis_summaries`는 일일 ai_summary 생성용으로 close 시점 복기와 다름.

### 3.5 FE-PR-11 — 투자자 DNA 프로필

| 항목 | 설계 | 현재 코드 | 분류 |
|------|------|-----------|------|
| `/profile` 또는 `/thesis/dna` 라우트 | 필요 | 없음 | **(C) 미구현** |
| `AccuracyRing` 컴포넌트 (적중률 도넛) | 필요 | 없음 (`Grep AccuracyRing` → 0건) | (C) 미구현 |
| `CategoryChart` (전제 카테고리/지표 유형 분포) | 필요 | 없음 (`Grep CategoryChart` → 0건) | (C) 미구현 |
| InvestorDNA 조회 API | 필요 | `InvestorDNA` BE 모델 존재, **DRF View/Serializer/URL 없음** | **(C) 미구현 (BE도 일부 누락)** |
| 사용자 가설 통계 (top_down_ratio 등) | `InvestorDNA` @property 존재 | 노출 API 없음 | (C) 미구현 |
| 기술 부채 정리 (Phase 2 완료 보고서 §8 명시) | 필요 | 미수행 (예: `(list) 2/`, `2.tsx` suffix 중복 파일, `0009` 이후 마이그레이션 미정리) | (C) 미구현 |

### 3.6 추가로 누락된 항목 (`thesis_control_design.md` 정의지만 PR 번호 미할당)

| 항목 | 설계 출처 | 현재 코드 | 분류 |
|------|----------|-----------|------|
| [근거] 탭 (지표 → 가설 연결 설명) | `design.md §2.4` | dashboard에 [근거] 탭 UI 없음 | (C) 미구현 |
| [더 자세히] 버튼 (깊이 조절) | `design.md §2.5` | 없음 | (C) 미구현 |
| 선택지 롱프레스 → 용어 설명 팝업 | `design.md §2.6` | 빌더에는 `BottomSheet` 통한 long-press 설명 있음, dashboard에는 없음 | (B) 부분 구현 |
| 커뮤니티(`ThesisFollow`/`PopularThesisCache`) FE 노출 | `community.py` BE 모델 존재 | FE 화면 0건 (`Grep follow|popular` → frontend/components/thesis 외부만 매칭) | (C) 미구현 |

---

## 4. 백엔드 갭 (Phase 3-A 관점)

| 영역 | 모델/서비스 | 상태 |
|------|------------|------|
| 회고 / 마감 복기 LLM | 모델 없음, 별도 태스크 없음 (`generate_thesis_summaries`는 일일 요약용) | **(C) 미구현** |
| 투자자 DNA API | `InvestorDNA` 모델 존재, **View/Serializer/URL 0건** | **(C) 미구현** |
| 마감 아카이브 조회 | `ThesisViewSet` filter 추가 필요 (status='closed') | (C) 미구현 |
| ValidityRecord 통계 API | 모델 존재, 집계 View 없음 | (C) 미구현 |
| 인기 가설 노출 API | `PopularThesisCache` 모델 + 캐싱 로직 존재 가능성, **View/URL 0건** | (C) 미구현 |
| Phase 3-C 합성 에이전트 (`SyntheticBootstrapper`) | 0% | (C) 미구현 |
| `ValidityScore` 집계 테이블 (Phase 2 후속) | 모델 없음, ValidityRecord만 존재 | (C) 미구현 |

---

## 5. Phase 3-B (UI 리디자인) — 실제로 완료된 것

> 참고용: 사용자 질문의 "Phase 3"과 무관하지만, 같은 PR 번호를 점유하므로 명시한다.

| PR (리디자인) | 산출물 | 코드 |
|---------------|--------|------|
| PR-7 (BE) | `ThesisIndicator.display_unit` + DashboardView ai_summary/notable_changes/raw_value 확장 + `IndicatorReadingsView` | ✅ migrations `0004_add_display_unit`, `0005_populate_display_unit` + `thesis/views/monitoring_views.py:260` |
| PR-8 (FE) | `RealValueIndicatorCard.tsx`, `AISummarySection.tsx`, `NotableChangesSection.tsx` | ✅ `components/thesis/dashboard/` |
| PR-9 (FE) | `ChartToggleButton.tsx`, `PeriodSelector.tsx`, `IndividualMiniCharts.tsx` + OverallMoon/DashboardIndicatorCard/RecentChange 삭제 | ✅ 신규 3개 존재, 구 3개 삭제 확인 |
| PR-10 (BE) | `generate_thesis_summaries` Celery 태스크 (Gemini 2.5 Flash 동기) | ✅ `thesis/tasks/summary.py` |

이 리디자인 묶음은 사실상 모두 머지되어 있고, dashboard 디렉토리의 컴포넌트 11개가 이 산출물이다.

---

## 6. 권장 조치 (보고서 범위)

1. **용어 충돌 해소** — `Phase2_completion_summary.md` §8과 `thesis_control_phase3_frontend_redesign.md`가 같은 PR 번호를 다른 의미로 사용. 다음 중 하나로 정리 필요:
   - 리디자인 묶음을 `FE-PR-7B~10B`로 재명명하고 A 정의는 그대로 유지
   - A 정의를 `FE-PR-12~16`으로 밀어 번호 충돌 제거
2. **`task_done/` 비대칭 회수** — Phase 3-B 산출물(dashboard 6 컴포넌트 + migration 2 + view 1)에 대한 완료 보고서가 없다. 코드는 있는데 문서가 없음.
3. **Phase 3-A 우선순위 결정 필요** — 사용자 질문의 "깊이+회고+프로필"은 본 시점 ~15% 구현. FE 작업이 사실상 전부 남았고, BE 쪽도 DNA/아카이브/복기 API 신설 필요.
4. **`InvestorDNA` 모델 노출 결정** — 모델/시그널 갱신 로직은 있는데 외부 노출 API 0건. Phase 3-A FE-PR-11의 핵심 의존이므로 BE 우선 처리 권장.
5. **삭제된 컴포넌트 보고서 갱신** — `FE-PR-5_dashboard.md`가 언급한 `OverallMoon`/`DashboardIndicatorCard`/`RecentChange`는 이미 삭제됨. 문서에 deprecation 표기 필요.

---

## 7. 부록 — 검색 증거

| 증거 | 결과 |
|------|------|
| `Grep AccuracyRing\|CategoryChart\|ValidityMatrix\|HeatmapView\|HistoryTab\|TabSection` in `frontend/` | **No files found** |
| `Grep archive\|retrospect\|investor_dna\|InvestorDNA\|popular_thesis\|PopularThesis\|follow_thesis\|ThesisFollow` in `frontend/components/thesis/` | **0 hits** (다른 도메인 매칭만 존재) |
| `Grep generate_thesis_summaries\|ai_summary\|notable_changes` in `thesis/` | 7 파일 매칭 (모두 B 리디자인 산출물) |
| `Grep popular\|follow\|investor.?dna\|/dna\|/profile\|archive\|회고\|복기` in `thesis/` | learning.py, community.py 등 모델 존재, View/URL 0건 |
| `thesis/migrations/` | 0001~0009 (display_unit·recommendation_reason·metrics_data_source·keyword_cache·keyword_cache_strength) — 회고/DNA 관련 마이그레이션 없음 |
| `thesis/tasks/` | `eod_pipeline.py`, `summary.py` — 회고/DNA/아카이브 태스크 없음 |
| `app/thesis/` 라우트 | `(list)/`, `new/`, `[thesisId]/`, `[thesisId]/indicators/`, `[thesisId]/close/` — `/profile`, `/dna`, `/archive`, `/[thesisId]/detail`, `/[thesisId]/history` 모두 없음 |

---

> 본 보고서는 코드 수정 없이 정적 cross-reference만 수행했다. 마이그레이션 적용 여부·Celery beat 등록 여부 등 런타임 상태는 확인하지 않았다.
