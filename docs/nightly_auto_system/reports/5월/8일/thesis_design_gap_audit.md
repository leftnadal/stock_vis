# Thesis Control 설계 갭 감사

> 감사일: 2026-05-08
> 감사 범위: `docs/thesis_control/` (설계) vs `thesis/` + `frontend/components/thesis/` + `frontend/app/thesis/` (구현)
> 모드: 읽기 전용 (코드 수정 없음)

---

## 0. 사전 정리: "Phase 3" 정의 충돌

설계 문서 4종이 서로 다른 "Phase 3"를 정의하고 있어 본 감사에서는 다음과 같이 구분한다.

| 정의 출처 | 의미 | 본 감사에서의 호칭 |
| --- | --- | --- |
| `plan/thesis_control_design.md` §7 | 커뮤니티 + 가설 마감 복기 + Neo4j 가설 그래프 | **Phase 3-A (커뮤니티)** |
| `plan/thesis_control_integrated_roadmap.md` §3 | 합성 에이전트 + Online LR + 블렌딩 | **Phase 3-B (학습 엔진)** |
| `frontend/task_done/Phase2_completion_summary.md` §8 | "깊이 + 회고 + 프로필" — FE-PR-7~11 (탭/히트맵/히스토리/마감 아카이브/DNA 프로필) | **Phase 3-C (구 FE 계획)** |
| `plan/thesis_control_phase3_frontend_redesign.md` | 실제 값 카드 + AI 분석 + 미니차트 (PR-7~10) — Phase 3-C를 **대체** | **Phase 3-D (FE 리디자인 v1)** |

⚠️ 사용자 질문에 등장한 "Phase 3 (깊이 + 회고 + 프로필)"과 "FE-PR-7~11"은 **Phase 3-C**를 가리킨다. 그러나 Phase 3-C는 `phase3_frontend_redesign.md`(2026-03-18)에서 **명시적으로 폐기 → Phase 3-D로 대체**되었다. 이 폐기/대체 사실 자체가 본 감사의 핵심 발견 중 하나다.

---

## 1. 요약 (Phase별 구현률)

| Phase | 정의 | 구현률 | 등급 |
| --- | --- | --- | --- |
| **Phase 1 (MVP)** — 관제 엔진 + 모델 + 빌더 + 카드뷰 + 알림 + 마감 | 설계 §7, integrated_roadmap §1 | **약 95%** | A |
| **Phase 1 학습 골격** (HypothesisEvent / ValidityRecord / InvestorDNA) | integrated_roadmap §1.2~1.4 | **모델 100% / 통합 부분** | B+ |
| **Phase 2 (강화)** — 히트맵·그래프 뷰 / [근거] 캐싱 / 일일 요약 / 뉴스 센티먼트 / 오늘 이슈 | 설계 §7, integrated_roadmap §2 | **약 35%** | C+ |
| **Phase 2 학습** — ValidityScore 집계 / 슬라이더 / 역제안 | integrated_roadmap §2 | **0%** | D (미시작) |
| **Phase 3-A (커뮤니티)** — 인기 가설 / 따라하기 / 템플릿 / Chain Sight 진입 / Neo4j 가설 그래프 | 설계 §7 | **모델 일부 / API·UI 0%** | D |
| **Phase 3-B (학습 엔진)** — 합성 에이전트 / Online LR / 블렌딩 | integrated_roadmap §3 | **0%** | D (미시작) |
| **Phase 3-C (구 FE 계획)** — 탭/히트맵/히스토리/아카이브/DNA 프로필 (FE-PR-7~11) | Phase2_completion_summary §8 | **0% — 공식 폐기** | (폐기) |
| **Phase 3-D (FE 리디자인 v1)** — 실제 값 카드 + AI 분석 + 미니차트 (PR-7~10) | phase3_frontend_redesign.md | **PR-7~9 약 90% / PR-10 부분** | A- |
| **Phase 4 (벡터 스코어링)** | integrated_roadmap §4 | **0%** | D (계획 단계) |

---

## 2. 문서별 상태 테이블

### 2.1 백엔드 모델 (설계 §4)

| 모델 | 설계에 명시 | 구현 위치 | 상태 |
| --- | --- | --- | --- |
| `Thesis` | §4.2 | `thesis/models/thesis.py` | (A) 완전 구현 + v2.3.2 추가 필드 (`premise_universe_ids`, `indicator_universe_ids`, `current_state`, `outcome`) 반영 |
| `ThesisPremise` | §4.2 | `thesis/models/thesis.py` | (A) 완전 구현 (+`is_paused`, `category`, `weight`) |
| `ThesisIndicator` | §4.2 | `thesis/models/indicator.py` | (A) 완전 + v2.3.2 (`epsilon`, `max_change_pct`, `allow_extreme_jump`, `display_unit`, `recommendation_reason`) |
| `IndicatorReading` | §4.2 | `thesis/models/indicator.py` | (A) 완전 + `validation_status`, `asof` 필드 |
| `ThesisSnapshot` | §4.2 | `thesis/models/monitoring.py` | (A) 완전 + v2.3.2 (`asof_date`, `data_coverage`, `universe_snapshot`, `ordered_indicator_ids`, `notable_changes`, `ai_summary`) |
| `ThesisAlert` | §4.2 | `thesis/models/monitoring.py` | (A) 완전 + v2.3.2 (`target_id`, `cooldown_hours`, `severity` 4단계, alert_type 11종) |
| `ThesisFollow` | §4.2 | `thesis/models/community.py` | (B) 모델만 존재, View/URL/serializer 미구현 |
| `PopularThesisCache` | §4.2 | `thesis/models/community.py` | (B) 모델만 존재, 캐시 갱신 태스크 미구현 |
| `HypothesisEvent` (특허) | integrated_roadmap §1.2 | `thesis/models/learning.py` | (B) 모델 + 인덱스 완료, 일부 코드 경로(`thesis_views.py`/`thesis_builder.py`)에서 참조됨. 13가지 event_type 모두 일관되게 발행되는지는 미확인 |
| `ValidityRecord` (특허) | integrated_roadmap §1.3 | `thesis/models/learning.py` | (B) 모델 완료, 마감 시 자동 생성 로직은 일부 경로에만. `is_synthetic` 필드 부재 → Phase 3-B 미대비 |
| `InvestorDNA` (특허) | integrated_roadmap §1.4 | `thesis/models/learning.py` | (B) 모델 + property(top_down_ratio, accuracy_rate, ai_accept_rate) 완료. 자동 갱신 signal 통합 미확인 |
| `KeywordCache` | redesign v2 추가 | `thesis/models/keyword.py` | (A) 빌더 재설계 부산물 — 설계 외 추가됨 |

### 2.2 백엔드 서비스 (설계 §4.1, §5)

| 서비스 | 설계에 명시 | 구현 위치 | 상태 |
| --- | --- | --- | --- |
| `thesis_builder.py` (LLM 대화) | §4.1, §5.5 | `thesis/services/thesis_builder.py` | (A) 구현 |
| `indicator_matcher.py` | §4.1, §5.2 | `thesis/services/indicator_matcher.py` | (A) 구현 |
| `arrow_calculator.py` | §4.1, §5.4 | `thesis/services/arrow_calculator.py` | (A) 구현 |
| `monitoring_engine.py` (변화 감지) | §4.1 | `thesis/services/alert_engine.py` (이름 변경) | (D) 이름 변경 — 폐기·대체 |
| `news_connector.py` (뉴스→가설) | §4.1 | 없음 | (C) 미구현. 대체로 keyword_collectors/news.py가 제한적으로 그 역할 |
| `summary_generator.py` (LLM 요약) | §4.1, §5.5 | `thesis/services/llm_postprocess.py` + `thesis/tasks/summary.py` | (A) 분리 구현 |
| Stage 0 `data_validator.py` | 수학 모델 v2.3.2 | `thesis/services/data_validator.py` | (A) |
| Stage 1 `indicator_scorer.py` | 수학 모델 | `thesis/services/indicator_scorer.py` | (A) |
| Stage 2 `premise_aggregator.py` | 수학 모델 | `thesis/services/premise_aggregator.py` | (A) |
| Stage 3 `thesis_state_machine.py` | 수학 모델 | `thesis/services/thesis_state_machine.py` | (A) |
| `snapshot_builder.py` | 수학 모델 §9 | `thesis/services/snapshot_builder.py` | (A) |
| `quarterly_metric_fetcher.py` | redesign v1 부산물 | 동일 | (A) 분기 지표 — 설계 외 추가 |
| `keyword_cache.py`, `keyword_collectors/`, `keyword_hint.py` | builder redesign v2 | 동일 | (A) 빌더 재설계 산출물 |

### 2.3 백엔드 API (설계 §6.1)

| 엔드포인트 | 설계 | 구현 (`thesis/urls.py` + view) | 상태 |
| --- | --- | --- | --- |
| `POST /` 가설 생성 | §6.1 | `ThesisViewSet` | (A) |
| `GET /` 목록 / `GET /{id}/` 상세 / `PATCH /{id}/` / `POST /{id}/close/` | §6.1 | `ThesisViewSet` | (A) |
| `POST /conversation/start/`, `respond/` | §6.1 | `ConversationStartView`, `ConversationRespondView` | (A) |
| `GET /conversation/news-issues/` | redesign v2 추가 | `NewsIssuesView` | (A) 설계 외 |
| `POST /conversation/suggest/` | redesign v2 | `SuggestThesesView` | (A) 설계 외 |
| `GET/POST /{id}/premises/`, `PATCH/DELETE /premises/{pid}/` | §6.1 | `ThesisPremiseViewSet` (nested) | (A) |
| `GET/POST /{id}/indicators/`, `PATCH/DELETE` | §6.1 | `ThesisIndicatorViewSet` (nested) | (A) |
| `POST /{id}/indicators/auto/` | §6.1 | ViewSet action 추정 | (A) |
| `GET /{id}/dashboard/` | §6.1, §6.2 | `DashboardView` | (A) — 카드뷰 + 히트맵 데이터까지 + raw_value 포함 |
| `GET /{id}/snapshots/` (히스토리) | §6.1 | 없음 | **(C) 미구현** — 그래프뷰/히스토리탭 차단 |
| `GET /{id}/summary/` (쉐이크) | §6.1 | 없음 | **(C) 미구현** — `dashboard.thesis.ai_summary`로 대체 사용 중 (D) |
| `GET /{id}/indicators/{iid}/readings/` | redesign v1 | `IndicatorReadingsView` | (A) |
| `GET /{id}/indicators/{iid}/explanation/` ([근거]) | §6.1 | 없음 | **(C) 미구현** |
| `GET /alerts/`, `PATCH /alerts/{aid}/read/` | §6.1 | `AlertListView`, `AlertReadView` | (A) |
| `GET /daily-issues/` | §6.1 | 없음 (`conversation/news-issues/`가 부분 대체) | **(B)** 부분/대체 |
| `GET /popular/`, `POST /popular/{id}/follow/`, `GET /popular/{id}/detail/` | §6.1 | 없음 | **(C) 미구현** |
| `GET /templates/`, `GET /templates/{type}/` | §6.1 | 없음 | **(C) 미구현** |

### 2.4 프론트엔드 라우팅 / 페이지 (설계 §2)

| 라우트 | 설계상 역할 | 실제 파일 | 상태 |
| --- | --- | --- | --- |
| `/thesis` | 첫 화면 (관제 중 / 오늘의 변화 / 5진입점) | `app/thesis/(list)/page.tsx` | (B) 부분 — 5진입점 → 단일 버튼 (§2.4 참조) |
| `/thesis/new` | 6단계 대화형 빌더 | `app/thesis/new/page.tsx` (40 KB) | (A) FE-PR-3 완료 — redesign v2의 talking builder 별도 트랙 진행 중 |
| `/thesis/[id]` | 관제실 (카드/히트맵/그래프 3뷰 + 달 위상) | `app/thesis/[thesisId]/page.tsx` | (D) 카드뷰만 — 3뷰 탭 폐기, 달 위상 폐기 (Phase 3-D로 대체) |
| `/thesis/[id]/indicators` | 지표 설정 (FE-PR-4) | 동일 | (A) |
| `/thesis/[id]/close` | 마감 + 복기 | 동일 | (B) 마감 가능, 복기/아카이브 화면(§3.9) **미구현** |
| `/thesis/alerts` | 알림 (FE-PR-6) | `app/thesis/(list)/alerts/` | (A) |
| 인기 가설 라우트 / 템플릿 / 마감 아카이브 / DNA 프로필 | §2.3 / Phase 3-C | 없음 | **(C) 미구현** |

### 2.5 프론트엔드 컴포넌트 (FE-PR 보고서 cross-reference)

| FE-PR | 보고서 | 핵심 컴포넌트 | 상태 |
| --- | --- | --- | --- |
| **FE-PR-1** routing + common | `task_done/FE-PR-1_*.md` | `ArrowIndicator`, `MoonPhase`, `ThesisBadge`, `BottomSheet`, `AlertBell`, `IndicatorCard`, authAxios | (A) 컴포넌트 5종 모두 존재 |
| **FE-PR-2** 가설 목록 | `task_done/FE-PR-2_*.md` | `ThesisListCard`, `TodayChangeCard`, `EntryPointGrid` | (B) 카드/오늘의 변화 (A), 진입점 그리드는 단일 버튼으로 축소 |
| **FE-PR-3** 빌더 6단계 | `task_done/FE-PR-3_*.md` + `plan_review_v3.md` | `BottomSheet`, `ChatBubble`, `MultiSelectFooter`, `NewsSelector`, `OptionButton`, `PremiseCard`, `ProgressBar`, `SuggestionCard`, `TextInput` | (A) 9개 빌더 컴포넌트 모두 존재 |
| **FE-PR-4** 지표 설정 | `task_done/FE-PR-4_*.md` | `IndicatorSetupCard`, `AddIndicatorSheet`, `RecommendCard` | (A) |
| **FE-PR-5** 대시보드 v1 (달위상) | `task_done/FE-PR-5_*.md` | `OverallMoon`, `DashboardIndicatorCard`, `RecentChange` | **(D) Phase 3-D에서 폐기 대상** — `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 디렉토리에서 발견되지 않음(삭제됨), `MoonPhase`(common)는 list 페이지 빈 상태에 잔존 |
| **FE-PR-6** 알림 + 마감 | `task_done/FE-PR-6_*.md` | `AlertCard`, `AlertFilterTabs`, `EmptyAlerts`, `OutcomeSelector`, `CloseConfirmDialog` | (A) |
| **FE-PR-7** (구 계획) 대시보드 탭 + 전제 CRUD | Phase2_completion §8 | `Tabs`, `PremiseEditor` … | **(D) 폐기** — `phase3_frontend_redesign.md`에서 `dashboardV2`/별도 탭 구조 도입 금지 결정 |
| **FE-PR-7** (리디자인) 백엔드 raw_value | `phase3_frontend_redesign.md` §4 | migration 0004/0005 (`display_unit`), `IndicatorReadingsView`, dashboard 응답 확장 | (A) 완료 |
| **FE-PR-8** (구 계획) 히트맵 + 지표 상세 편집 | Phase2_completion §8 | `HeatmapView`, `IndicatorDetailEdit` | **(D) 폐기** — Finviz 히트맵 별도 화면 미도입 |
| **FE-PR-8** (리디자인) 실제 값 카드 + AI 분석 | `phase3_frontend_redesign.md` §5 | `RealValueIndicatorCard`, `AISummarySection`, `NotableChangesSection` | (A) 모두 존재 + `IndicatorRow` 추가 |
| **FE-PR-9** (구 계획) 히스토리 탭 (recharts 라인) | Phase2_completion §8 | `HistoryTab`, `SnapshotTimeline` | **(C) 미구현** — `GET /{id}/snapshots/` 백엔드 부재로 차단 |
| **FE-PR-9** (리디자인) 미니차트 + 기간 | `phase3_frontend_redesign.md` §6 | `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, `QuarterlySparkline` | (A) 4개 모두 존재 |
| **FE-PR-10** (구 계획) 마감 아카이브 + ValidityMatrix | Phase2_completion §8 | `ArchiveList`, `ValidityMatrix`, `ClosedThesisDetail` | **(C) 미구현** |
| **FE-PR-10** (리디자인) AI 파이프라인 (Celery) | `phase3_frontend_redesign.md` §7 | `tasks/summary.py`, `notable_changes` 채우기 | (B) `tasks/summary.py` 존재. `notable_changes`가 `alert_engine` 이벤트 기반으로 구조화돼 채워지는지 미검증 |
| **FE-PR-11** (구 계획) 투자자 DNA 프로필 | Phase2_completion §8 | `AccuracyRing`, `CategoryChart`, `DnaProfilePage` | **(C) 미구현** — 모델은 있으나 페이지·API 부재 |

---

## 3. Phase 3 미구현 항목 상세

> 본 절은 **Phase 3-C (구 FE 계획: 깊이 + 회고 + 프로필 / FE-PR-7~11)** 기준으로 정리한다. Phase 3-D (리디자인)로 대체된 항목은 그 사실을 명기한다.

### 3.1 FE-PR-7 (구) — 대시보드 3탭 구조 + 전제 CRUD UI

- 설계: `Phase2_completion_summary.md` §8 — "3탭 (관제/상세/히스토리) + 전제 CRUD"
- 현재 구현 (`app/thesis/[thesisId]/page.tsx`): **단일 페이지 세로 스크롤** — 탭 컨테이너 부재
- **폐기 사유**: `phase3_frontend_redesign.md` §0.3 — "달 위상/추상적 시각화 폐기, 실제 값 노출, dashboardV2/별도 탭 구조 금지" 결정
- **잔존 갭**:
  - 전제 CRUD UI는 (구 PR-7과 무관하게) 여전히 미존재. 백엔드는 `ThesisPremiseViewSet`로 CRUD 가능하지만 프론트는 빌더 시점 외에 전제를 추가/수정하는 UI가 없음 → 설계 §2.3 "[전제 추가할래]" 흐름이 마감/관제 단계에서는 막혀 있음
  - 분류: **(C) 미구현 (전제 편집)** + (D) 탭 구조 자체는 폐기

### 3.2 FE-PR-8 (구) — 히트맵 + 지표 상세 편집

- 설계: Finviz 스타일 색상 그리드, 지표 weight/direction 인라인 편집
- 현재 구현:
  - `DashboardView` 응답에 `heatmap.cells[]`/`rows`/`cols` 포함 (백엔드 데이터는 준비됨)
  - 그러나 프론트엔드에는 히트맵 렌더링 컴포넌트가 **없음** (`Heatmap*` 파일 0건)
- **폐기 사유**: 리디자인에서 카드뷰 단일화로 통합. 단, 설계 §3.4의 3뷰 비전(카드/히트맵/그래프)과 충돌 → **명시적 비전 축소** 자체가 결정 사항으로 문서화됨
- 지표 상세 편집(weight/support_direction 변경)은 백엔드 PATCH 가능하나 프론트 편집 UI 부재 → **(C) 미구현**

### 3.3 FE-PR-9 (구) — 히스토리 탭 (recharts 라인 차트 + 스냅샷 타임라인)

- 설계: 시간축 그래프, 가설 점수 변화 추적
- 현재 구현:
  - `IndividualMiniCharts.tsx` + `useAllIndicatorReadings` 로 **지표별 raw_value 시계열 미니차트는 존재** (리디자인 PR-9)
  - 그러나 **가설 전체 overall_score의 시계열 그래프는 부재** — `GET /{id}/snapshots/` API가 백엔드에 없어 차단
  - 스냅샷 타임라인 UI 없음
- 분류: **(C) 미구현 (가설 점수 히스토리)** + (B) 부분 (지표별 raw_value만 가능)

### 3.4 FE-PR-10 (구) — 마감 아카이브 + ValidityMatrix 요약

- 설계: 마감된 가설 목록 + 2×2 매트릭스 시각화 + 가장 유용했던 지표 표시 (설계 §3.9)
- 현재 구현:
  - `Thesis.outcome` 필드 존재, 마감 동작 가능
  - `ValidityRecord` 모델 존재 (마감 시 기록되도록 설계됨)
  - 그러나 **마감 가설 목록 페이지/라우트 없음** (`/thesis` 목록은 `status='active'`만 필터)
  - 복기 화면 (§3.9 "가장 유용했던 지표", "예상과 달랐던 부분") **부재**
  - ValidityMatrix 시각화 컴포넌트 부재
- 분류: **(C) 미구현** — 데이터 파이프라인은 일부 준비되었으나 사용자 노출 0%

### 3.5 FE-PR-11 (구) — 투자자 DNA 프로필

- 설계: AccuracyRing, CategoryChart (전제 카테고리 분포), 기술 부채 정리
- 현재 구현:
  - `InvestorDNA` 모델 + properties (`accuracy_rate`, `top_down_ratio`, `ai_accept_rate`) 존재
  - 그러나 **DNA 조회 API 없음, 페이지 없음, 컴포넌트 0건** (`*DNA*`, `*Profile*` 파일 0건)
  - `personalization_weight` 슬라이더 (Phase 2 통합 로드맵 §2.3) 미연결
- 분류: **(C) 미구현** — 모델만 갖춘 상태

### 3.6 Phase 3-A (커뮤니티) — 설계 §2.3 경로 3·4·5

| 항목 | 설계 위치 | 상태 |
| --- | --- | --- |
| 인기 가설 카드 / 따라하기 | §2.3 경로 3 | (C) 미구현 (모델만 `PopularThesisCache`/`ThesisFollow` 존재) |
| 템플릿 시스템 (이벤트형/추세형/비교형/괴리형) | §2.3 경로 4 | (C) 미구현 — API/UI 없음 |
| Chain Sight 진입 / 역방향 제안 | §2.3 경로 5 | (C) 미구현 — Chain Sight ↔ Thesis 양방향 링크 없음 |
| Neo4j 가설 그래프 (HAS_PREMISE / SIMILAR_TO / OPPOSITE_OF) | §4.4 | (C) 미구현 |
| 가설 마감 시점 도래 알림 + 복기 흐름 | §3.8, §3.9 | (B) `target_date` 알림은 alert_type에 정의되어 있으나 복기 UI 부재 |

### 3.7 Phase 3-B (학습 엔진) — integrated_roadmap §3

| 항목 | 상태 |
| --- | --- |
| `SyntheticBootstrapper` 페르소나 시뮬레이션 | (C) 미구현 — `is_synthetic` 필드도 부재 |
| `ThesisWeightLearner` (Online Logistic Regression) | (C) 미구현 |
| 합성/실제 블렌딩 (`effective_blend = blend_ratio × max(0, 1 - real_count/50)`) | (C) 미구현 |
| `ValidityScore` 집계 (Phase 2) | (C) 미구현 — 집계 테이블/태스크 없음 |

### 3.8 설계 §2 UX 자체의 갭 (Phase 3 외 누락 포함)

| 항목 | 상태 |
| --- | --- |
| 첫 화면 5진입점 (오늘 이슈/내 생각/인기 가설/템플릿/Chain Sight) | (B) 부분 — `EntryPointGrid`가 단일 "새 가설 세우기" 버튼. 빌더 내부에서 News/FreeInput/Suggest는 분기되지만 진입 화면 다양성은 축소됨 |
| 양쪽 추적 ("잘 모르겠어 → 가설 A/B 동시 생성") | (C) 미구현 |
| [근거] 시스템 (롱프레스 용어 설명, 전제 탭 맥락 설명, 지표 [근거] 탭) | (B) 빌더 단계의 long-press 설명은 FE-PR-3에 구현. 관제실 단계의 [근거] 탭은 미구현 (`GET /{id}/indicators/{iid}/explanation/` 부재) |
| 모바일 제스처 (롱프레스/스와이프/쉐이크) | (B) 빌더 long-press만, 그 외 미구현 |
| 그래프뷰 (지지/중립/반박 Y축 + 시간 흐름) | (D) 폐기 (Phase 3-D에서 미니차트로 대체) |
| 알림 푸시 (서버 → 디바이스) | (B) `is_pushed` 필드만, 실제 푸시 채널 미연결 |

---

## 4. 추가 발견사항 (보너스)

1. **빌더 재설계 v2 진행 중 (별도 트랙)**: `plan/talking_builder/redesign_build_plan/` (00~05) 가 별도 PR 트랙으로 진행. "선행 조건: Phase 3 대시보드 PR (FE-PR-7~11) 완료 후 착수"라 명시되어 있으나, 위 §3에서 보듯 Phase 3-C는 이미 폐기됐으므로 **선행 조건 자체가 의미 없음** → 문서 정리 필요.
2. **`MoonPhase` 잔존**: 리디자인 PR-9 체크리스트 §6.8에 `MoonPhase.tsx`/`OverallMoon.tsx` import 검색 후 삭제하라고 명시되어 있으나, `app/thesis/(list)/page.tsx:10`이 여전히 `MoonPhase`를 빈 상태 placeholder로 사용 중 → 의도적 잔존인지 청소 누락인지 판단 필요.
3. **현재 브랜치는 `portfolio`** — Thesis Control 작업 브랜치가 아니라 Portfolio Coach 작업 중. Phase 3 후속 작업은 별도 브랜치 분리 필요.
4. **`FE-PR-3_plan_review_v3.md`** 가 `task_done/`에 있음에도 빌더 재설계 v2가 진행 중 → 빌더 영역은 **재설계 사이클 진입** 상태로, 단순 "Phase 3 후속"이 아님.
5. **분기 지표(`quarterly_metric_fetcher.py`, `QuarterlySparkline.tsx`)**: 설계 문서에 명시 없음. 실서비스 운영 중 추가된 기능 → 설계 문서 업데이트 필요.
6. **3계층 아키텍처 일치도**: `monitoring_views.py`의 `DashboardView`가 모델 직접 쿼리 + service 호출이 혼합. CLAUDE.md의 "View → Service → Models" 패턴과 일부 어긋남 — 단, 설계 §6.2 응답 형태와 일치 우선이 더 중요해 보임.

---

## 5. 결론 및 권고

### 5.1 한 줄 요약

> **Phase 1 + Phase 3-D는 거의 완성**. Phase 3-C (사용자 질문의 "깊이 + 회고 + 프로필")는 **공식 폐기 후 Phase 3-D로 부분 대체**됐으며, 마감 아카이브 / DNA 프로필 / 커뮤니티는 **모델만 있고 UI·API 0%**.

### 5.2 사용자가 "Phase 3 (깊이 + 회고 + 프로필) 진행 중"이라 인지하고 있다면

CLAUDE.md "구현 상태 요약"에 적힌 "Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"은 **현재 코드와 불일치**. 다음 중 하나로 정리 필요:

| 선택지 | 의미 |
| --- | --- |
| **A.** Phase 3-D를 Phase 3 공식 정의로 채택하고 CLAUDE.md 갱신 | 현재 구현 상태와 일치. "깊이 + 회고 + 프로필" 표현은 삭제 |
| **B.** Phase 3-C를 살리고 FE-PR-9~11 (히스토리/아카이브/DNA)을 진짜로 구현 | 마감 아카이브 + DNA 프로필이 핵심 가치라면 이 길 |
| **C.** Phase 3-A (커뮤니티)를 우선시 | 인기 가설 + 템플릿이 Phase 3의 핵심이라면 |

### 5.3 가장 가시적 갭 Top 3

1. **마감 아카이브 + 복기 화면** — 데이터(ValidityRecord, outcome)는 쌓이는데 사용자가 볼 곳이 없음.
2. **투자자 DNA 프로필 페이지** — 모델·property 모두 준비됐는데 노출 0%.
3. **가설 점수 시계열(`/snapshots/` API + 히스토리 차트)** — 매일 스냅샷이 쌓이는데 그걸 보여주는 UI가 없음.

이 셋은 데이터·모델 측면에서 이미 70% 이상 준비된 상태라 **착수 비용 대비 회수 효과가 큼**.
