# Thesis Control 설계 갭 감사

> 작성일: 2026-05-17
> 감사자: orchestrator (read-only)
> 범위: `docs/thesis_control/` ↔ `thesis/` ↔ `frontend/components/thesis/` + `frontend/app/thesis/`
> 결론: **Phase 1 완전, Phase 2 부분, Phase 3 ‘리디자인 안’ 채택 + 원안 FE-PR-7~11 폐기/대체**

---

## 요약 (Phase별 구현률)

| Phase | 원안 | 실제 채택안 | 백엔드 구현률 | 프론트엔드 구현률 | 종합 |
|-------|------|------------|--------------|------------------|------|
| **Phase 1 (MVP)** | 가설 CRUD, 카드뷰, Celery 3태스크, v2.3.2 스코어링 | 동일 | **100%** (12 모델 + 4 task + 7 service) | **100%** (FE-PR-1~6) | **A: 완전 구현** |
| **Phase 2 (모니터링 강화)** | 카드/히트맵/그래프 3뷰, [근거], DNA 슬라이더, 역제안, 뉴스 센티먼트 | 카드뷰 + AI 요약만 + 분기 지표 인라인 차트 | **약 55%** | **약 35%** | **B: 부분 구현** |
| **Phase 3 원안 (FE-PR-7~11)** | 3탭 구조 / 히트맵 / 히스토리 탭 / 마감 아카이브 / DNA 프로필 | **폐기 — Phase 3 리디자인으로 대체** | – | – | **D: 폐기/대체** |
| **Phase 3 리디자인 (PR-7~10)** | display_unit + 실제값 카드 + AI 분석 + 토글 차트 + AI 파이프라인 | 동일 (단 page.tsx에서 컴포넌트 통합 방식만 변형) | **100%** (PR-7, PR-10) | **약 90%** (PR-8, PR-9 컴포넌트는 존재하나 page에서 미사용·대체) | **A: 거의 완전** |
| **Phase 4 (지능화)** | 벡터화 / 반대 가설 / 합성 에이전트 / Online LR | 미진입 | **0%** | **0%** | **C: 미구현** |

> 핵심 발견: Phase 2 완료 보고서 §8 의 **FE-PR-7~11(깊이+회고+프로필)** 안은 `thesis_control_phase3_frontend_redesign.md` (2026-03-18 FINAL)로 교체되었다. 따라서 원안 5개 FE PR(3탭, 히트맵, 히스토리, 아카이브, DNA 프로필)은 **"폐기/대체(D)"** 로 분류된다.

---

## 문서별 상태 테이블

### 1. 설계 문서 매핑

| 설계 문서 | 위치 | 마지막 갱신 | 실제 채택 여부 | 비고 |
|----------|------|-------------|---------------|------|
| `thesis_control_design.md` | plan/ | 2026-02-27 | **채택 (1차 진실의 소스)** | UX/모델/API 명세서 |
| `thesis_control_math_model_final.md` | plan/ | 2026-02-27 | **채택** | v2.3.2 스코어링 엔진 |
| `thesis_control_implementation_guide.md` | plan/ | – | **채택** | Phase 1~4 구현 가이드 |
| `thesis_control_integrated_roadmap.md` | plan/ | – | **채택** | DNA/유효성/합성 통합 |
| `thesis_control_phase3_frontend_redesign.md` | plan/ | 2026-03-18 FINAL | **채택 (Phase 2 §8 FE-PR-7~11 안을 대체)** | 달위상 폐기 + 실제값 |
| `thesis_control_phase1_frontend_FE_PR_1~5.md` | docs/thesis_control/ | – | **채택, 완료** | 각 PR 지시서 |
| `thesis_control_phase1_frontend_prompts.md` | docs/thesis_control/ | – | 채택, 완료 | 프롬프트 정의 |
| `thesis_control_user_experience.md` | docs/thesis_control/ | – | 채택, 일부 미구현 | 제스처/롱프레스 |
| `work_done/phase_a_llm_builder.md` | docs/thesis_control/work_done/ | – | 완료 | LLM 빌더 PR |
| `plan/talking_builder/*.md` (5개) | docs/thesis_control/plan/talking_builder/ | – | 일부 채택 (LLM 빌더 적용) | redesign_build_plan/ 포함 |

### 2. Phase 2 FE-PR 완료 보고서 (`docs/thesis_control/frontend/task_done/`)

| 완료 보고서 | 대응 구현 | 상태 |
|-------------|----------|------|
| `FE-PR-1_routing_common_components.md` | `frontend/app/thesis/layout.tsx` + `components/thesis/common/` + `lib/api/authAxios.ts` | **A: 완전** |
| `FE-PR-2_thesis_list_page.md` | `app/thesis/(list)/page.tsx` + `components/thesis/list/` 3개 | **A: 완전** |
| `FE-PR-3_builder_implementation.md` (+v3 리뷰) | `app/thesis/new/page.tsx` + `components/thesis/builder/` 9개 | **A: 완전** |
| `FE-PR-4_indicator_setup.md` | `app/thesis/[thesisId]/indicators/page.tsx` + `components/thesis/indicators/` 3개 | **A: 완전** |
| `FE-PR-5_dashboard.md` (달 위상 + 화살표) | `app/thesis/[thesisId]/page.tsx` + `components/thesis/dashboard/` (옛 카드) | **D: 폐기/대체** (PR-7~9 리디자인에서 OverallMoon/DashboardIndicatorCard/RecentChange 삭제) |
| `FE-PR-6_alerts_close_qa.md` | `app/thesis/(list)/alerts/page.tsx`, `app/thesis/[thesisId]/close/page.tsx` + `components/thesis/alerts/`, `close/` | **A: 완전** |
| `Phase2_completion_summary.md` §8 (FE-PR-7~11) | – | **D: 폐기/대체** (아래 §3 참조) |

### 3. Phase 3 리디자인 PR (`thesis_control_phase3_frontend_redesign.md`)

| PR | 설계 명세 | 실제 구현 | 갭 분류 | 비고 |
|----|----------|----------|---------|------|
| **PR-7 (BE 확장)** | `ThesisIndicator.display_unit` + 마이그레이션 + Dashboard에 raw_value/change_pct + `IndicatorReadingsView` | `indicator.py:73-76` `display_unit` 필드, migration `0004_add_display_unit.py` + `0005_populate_display_unit.py`, `monitoring_views.py:94-174` raw_value 분기, `urls.py:30-34` readings endpoint, `IndicatorReadingsView` (`monitoring_views.py:260`) FMP fallback 추가 | **A: 완전 구현 (+확장)** | 설계 외 추가: 분기지표 fiscal_label/quarterly_history/comparison_type, `description`/`recommendation_reason` 응답에 포함 |
| **PR-8 (실제값 카드 + AI 분석)** | `AISummarySection`, `NotableChangesSection`, `RealValueIndicatorCard`, OverallMoon 삭제, `page.tsx` 교체 | `AISummarySection.tsx`, `NotableChangesSection.tsx` 존재 + 페이지 통합 ✓. `RealValueIndicatorCard.tsx` 존재(테스트도 있음)이나 **`page.tsx`는 `IndicatorRow.tsx`(분기/일간 토글 카드)** 사용. OverallMoon import 없음 (페이지에서 미사용) | **B: 부분/대체 구현** | 설계의 `RealValueIndicatorCard` 단순 카드 대신 더 발전된 `IndicatorRow`(토글 펼침 + 차트 + 분기 sparkline + description/관계 설명)로 통합됨 |
| **PR-9 (미니차트 + 정리)** | `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, 차트 색상/PERIOD_OPTIONS, 옛 컴포넌트 3개 삭제 | 컴포넌트 3개 모두 존재. 단 `page.tsx`는 이들을 **렌더하지 않고** IndicatorRow 인라인 차트(1M/1Y/3Y/5Y, recharts AreaChart)로 대체. `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 미삭제(`components/thesis/index.ts:3` `MoonPhase` export 유지, list/page.tsx에서 빈 상태 fallback 사용 중) | **B: 부분 구현 (페이지 통합 방식 변형)** | 차트 토글이 페이지 전역이 아닌 각 지표 row의 개별 토글로 이동. 5Y 기간 추가(설계는 30D 상한). PR-9 §6-8 의 OverallMoon 삭제는 미실행 — 빈 상태 EmptyTheses에서 사용 |
| **PR-10 (AI 모니터링 파이프라인)** | `generate_thesis_summaries` Celery + 동기 Gemini + 변화 있는 가설만 + `notable_changes`를 alert 이벤트에서 변환 | `thesis/tasks/summary.py` (143 lines) 구현 — Gemini 2.5 Flash 동기 호출, `force` 플래그, 80~200자 한글 요약, GOOGLE_AI_API_KEY/GEMINI_API_KEY fallback, soft_time_limit=300s, max_retries=2. `__init__.py:6`에 등록 | **A: 완전 구현** | 설계의 `_build_user_prompt`보다 단순(notable_changes 상위 3개만 인용). `notable_changes` 데이터 흐름은 snapshot_builder/alert_engine 측에서 채워야 함 — 본 보고서는 그 부분 미검증 |

### 4. 백엔드 코드 상태 (thesis/)

| 영역 | 설계 요구사항 | 실제 구현 위치 | 갭 분류 |
|------|--------------|---------------|---------|
| **모델 7개 (설계 4.2)** | Thesis, ThesisPremise, ThesisIndicator, IndicatorReading, ThesisSnapshot, ThesisAlert, ThesisFollow, PopularThesisCache | `thesis/models/__init__.py` 12개 export (설계 7 + 특허 3 + KeywordCache + 기타) | **A: 완전 + 확장** |
| **v2.3.2 신규 필드** | epsilon/window/decay/min/max_valid_value/max_change_pct/allow_extreme_jump/is_paused/override_score, asof/validation_status, asof_date/data_coverage/universe_snapshot/ordered_indicator_ids, target_id/cooldown_hours | `indicator.py:81-89`, `monitoring.py:15-19, 76-77`, `thesis.py:127-128`, `IndicatorReading.VALIDATION_STATUS_CHOICES` 8종 | **A: 완전** |
| **특허 모델** | HypothesisEvent, ValidityRecord, InvestorDNA | `learning.py` 완전 구현 (153 lines, accuracy_rate/top_down_ratio property 포함) | **A: 완전** |
| **services/** (설계 4.1 + 수학 모델) | thesis_builder, indicator_matcher, arrow_calculator, monitoring_engine, news_connector, summary_generator | 19개 서비스 (`thesis_builder.py` 79KB, `prompt_builder.py` 49KB, `indicator_matcher.py`, `arrow_calculator.py`, `alert_engine.py`, `data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `quarterly_metric_fetcher.py`, `snapshot_builder.py`, `thesis_state_machine.py`, `llm_postprocess.py`, `builder_events.py`, `builder_state.py`, `keyword_cache.py`, `keyword_collectors/`, `keyword_hint.py`) | **A: 완전 + 확장** (Builder Phase A/B/C 적용) |
| **Celery 태스크 (수학 모델 7)** | update_indicator_readings (18:00), calculate_scores (18:15), create_snapshots_and_alerts (18:30), generate_thesis_summaries (18:35) | `tasks/eod_pipeline.py` (3개) + `tasks/summary.py` (1개) | **A: 완전** |
| **API (설계 6.1) — 가설 CRUD + close** | POST/GET/GET-id/PATCH/POST-close | `thesis_views.py:ThesisViewSet` (close action + 이벤트 기록) | **A: 완전** |
| **API — 대화** | conversation/start/, conversation/respond/ | `conversation_views.py` (wizard/llm dual mode, sanitize 보안) + `NewsIssuesView` + `SuggestThesesView` | **A: 완전 + 확장** |
| **API — 전제 CRUD** | GET/POST/PATCH/DELETE | `ThesisPremiseViewSet` (HypothesisEvent 자동 기록) | **A: 완전** |
| **API — 지표 CRUD + auto** | GET/POST/PATCH/DELETE + auto_recommend | `ThesisIndicatorViewSet.auto` (indicator_matcher 호출) | **A: 완전** |
| **API — 대시보드** | GET /{id}/dashboard/ (카드뷰만 — Phase 1) | `DashboardView` (히트맵 응답 + 분기 지표 + ai_summary + notable_changes + description + recommendation_reason 모두 포함) | **A: 완전 + 확장** |
| **API — 알림** | GET /alerts/, PATCH /alerts/{aid}/read/ | `AlertListView`, `AlertReadView` (50개 제한, 미읽음 우선) | **A: 완전** |
| **API — readings (PR-7)** | GET /{id}/indicators/{iid}/readings/?days=14 | `IndicatorReadingsView` + 최대 1825일(5Y) + FMP fallback | **A: 완전 + 확장** (설계는 days≤90, 실제 1825) |
| **API — 스냅샷 히스토리** | GET /{id}/snapshots/ | **미구현** (모델은 있음) | **C: 미구현** |
| **API — [근거] 설명** | GET /{id}/indicators/{iid}/explanation/ | **미구현** (description은 dashboard에서 내려옴) | **C: 미구현** |
| **API — 인기 가설** | GET /popular/, POST /popular/{id}/follow/ | **미구현** (PopularThesisCache 모델은 있음) | **C: 미구현** |
| **API — 템플릿** | GET /templates/, GET /templates/{type}/ | **미구현** | **C: 미구현** |
| **API — 오늘 이슈** | GET /daily-issues/ | **NewsIssuesView**로 대체 구현 (`/conversation/news-issues/`) — Gemini로 한국어 변환 | **A: 완전 (경로 다름)** |
| **API — InvestorDNA / ValidityRecord 노출** | 없음 (학습용) | 백엔드 자동 갱신만 (`thesis_views.py:_update_investor_dna`). REST 노출 없음 | **C: 미구현 (의도적)** |

### 5. 프론트엔드 코드 상태

| 영역 | 설계 요구사항 | 실제 구현 위치 | 갭 분류 |
|------|--------------|---------------|---------|
| **라우팅 6경로** | /thesis, /thesis/new, /thesis/alerts, /thesis/[id], /thesis/[id]/indicators, /thesis/[id]/close | `app/thesis/(list)/page.tsx`, `app/thesis/(list)/alerts/page.tsx`, `app/thesis/new/page.tsx`, `app/thesis/[thesisId]/page.tsx`, `app/thesis/[thesisId]/indicators/page.tsx`, `app/thesis/[thesisId]/close/page.tsx` | **A: 완전** |
| **빌더 (경로 1~5)** | 뉴스/내 생각/인기/템플릿/Chain Sight 5개 진입점 | EntryPointGrid 2개(뉴스/자유입력만 노출, 인기/템플릿/Chain Sight 진입점 미구현) + builder/ 9컴포넌트 | **B: 부분 구현** (3개 진입점 미노출) |
| **대시보드 v2 (Phase 3 리디자인)** | DashboardPageHeader + DashboardHeader + AISummarySection + NotableChangesSection + RealValueIndicatorCard | DashboardPageHeader + DashboardHeader + AISummarySection + NotableChangesSection + **IndicatorRow** (RealValueIndicatorCard 대체, 분기 sparkline + 인라인 area chart + description 포함) | **A: 완전 (확장 변형)** |
| **차트 토글 / 기간 / 미니차트 (PR-9)** | ChartToggleButton + PeriodSelector + IndividualMiniCharts을 page 전역 | 컴포넌트 3개 파일 존재하나 **`page.tsx`에서 미사용** — IndicatorRow row 단위 인라인 차트로 통합 | **B: 부분 구현 (사용처 변경)** |
| **달 위상 (MoonPhase)** | 삭제 권고 (PR-9 §6-8) | `components/thesis/common/MoonPhase.tsx` 잔존 + `components/thesis/index.ts:3` export 유지 + `app/thesis/(list)/page.tsx:140` 빈 상태에서 사용 | **B: 부분 정리 (대시보드 제거 ✓, 목록 빈 상태 잔존)** |
| **알림 화면** | 필터 3탭 + 카드 + 읽음 처리 + 빈 상태 | `alerts/page.tsx` + AlertCard + AlertFilterTabs + EmptyAlerts | **A: 완전** |
| **마감 화면** | OutcomeSelector + 최종 확인 다이얼로그 | `close/page.tsx` + OutcomeSelector + CloseConfirmDialog | **A: 완전** |
| **지표 설정** | 지표 카드 토글/삭제 + AI 추천 바텀시트 | `indicators/page.tsx` + IndicatorSetupCard + AddIndicatorSheet + RecommendCard | **A: 완전** |
| **롱프레스 용어 설명** | 설계 2.4 — 모든 버튼 롱프레스 → 팝업 | builder에 BottomSheet 존재. 일관 적용 여부 본 감사 범위 외 | **B: 부분 (감사 범위 외)** |
| **세 가지 뷰** | 카드뷰/히트맵/그래프뷰 전환 | 카드(IndicatorRow) **만**. heatmap/graph 탭 없음. 백엔드 heatmap 응답은 무시됨 | **C: 미구현** |
| **InvestorDNA / 마감 아카이브 / 회고 화면** | Phase 3 원안 FE-PR-10/11 | **미구현** (Phase 3 리디자인이 원안을 대체했기 때문) | **D: 폐기/대체** |
| **인기 가설 / 템플릿** | 설계 2.3 경로 3·4 | 미구현 — 그 어디서도 `/popular`, `/templates` 사용 흔적 없음 | **C: 미구현** |
| **Chain Sight ↔ Thesis 연동** | 설계 2.3 경로 5 | Chain Sight 측 entry 없음 (frontend grep 결과 chainsight 내부 GraphMiniView에서 thesis 연결 없음) | **C: 미구현** |

---

## Phase 3 미구현 항목 상세

### 3-A. Phase 3 ‘원안’ (FE-PR-7~11) — 전면 폐기/대체

> Phase2_completion_summary.md §8 의 5개 PR(3탭 / 히트맵 / 히스토리 / 마감 아카이브 / DNA 프로필)은 2026-03-18 FINAL 리디자인 문서로 **공식 대체**되었다. 따라서 “미구현”이 아니라 **D: 폐기/대체**.

| 원안 PR | 원안 내용 | 대체 결과 |
|---------|----------|----------|
| FE-PR-7 (대시보드 탭 구조) | 3탭(관제/상세/히스토리) + 전제 CRUD | **단일 페이지** 로 회귀(IndicatorRow에 토글 펼침으로 상세/차트 통합) |
| FE-PR-8 (히트맵 + 지표 상세 편집) | Finviz 스타일 히트맵 + weight/direction 편집 | **백엔드 heatmap 응답만** 존재. FE 시각화·편집 미진입 |
| FE-PR-9 (히스토리 탭) | recharts 라인 차트 + 스냅샷 타임라인 | **IndicatorRow row 단위 area chart**(1M/1Y/3Y/5Y) + QuarterlySparkline로 통합. 스냅샷 타임라인 없음 |
| FE-PR-10 (마감 아카이브 + 요약) | 마감 가설 목록 + ValidityMatrix | **미구현**. 마감 페이지(close/page.tsx)는 있으나 아카이브 보기 화면 없음 |
| FE-PR-11 (투자자 DNA 프로필) | AccuracyRing + CategoryChart | **미구현**. InvestorDNA 모델은 마감 시 자동 갱신되지만 UI 노출 0% |

### 3-B. Phase 3 ‘리디자인’ (PR-7~10) — 잔여 갭

| 항목 | 설계 요구 | 실제 | 분류 | 권고 |
|------|----------|------|------|------|
| `RealValueIndicatorCard` 사용처 | 대시보드의 단위 카드 | 컴포넌트 + 테스트는 있으나 `app/thesis/[thesisId]/page.tsx`에서 **import 안 됨** | B | 둘 중 하나 결정: ① IndicatorRow 단일화 + RealValueIndicatorCard 삭제, ② RealValueIndicatorCard 도로 채택 |
| `ChartToggleButton` + `PeriodSelector` + `IndividualMiniCharts` 통합 | page.tsx에 전역 차트 영역 | 3개 컴포넌트 파일은 존재하나 page.tsx에서 미사용 | B | 마찬가지 — 대체된 IndicatorRow row-level 차트로 결정한 뒤 잔존 코드 정리 |
| OverallMoon / DashboardIndicatorCard / RecentChange 삭제 (§6-8) | 3 파일 DELETE | 디렉토리 ls 시 미존재(이미 삭제됨 ✓). `MoonPhase`는 `app/thesis/(list)/page.tsx:140` 빈 상태에서 잔존 | B | 빈 상태에서도 사용한다면 의도 유지 / 아니면 삭제. `components/thesis/index.ts:3`도 동시 정리 |
| `scoreToPhaseMeta()` 삭제 (§6-8) | utils.ts 정리 | 본 감사 범위 외 (utils.ts 직접 미열람) | – | 별도 점검 필요 |
| `notable_changes` 백엔드 생성 흐름 | snapshot_builder/alert_engine에서 alert 이벤트 → snapshot.notable_changes 변환 | `snapshot_builder.py` 존재하나 본 감사에서 흐름 미검증. monitoring_views.py:189-193은 “있으면 노출” 패턴 | B | snapshot 생성 시점에 실제로 채워지는지 별도 무결성 점검 |
| AI summary cost 가드 | 변화 있는 가설만 호출 | `summary.py`는 `force` 없으면 “이미 있는 것 skip”만 하고 “변화 없으면 skip”은 미적용 | B | 비용 절감 트리거 추가 권고 (snapshot.notable_changes empty면 skip) |
| `description` / `recommendation_reason` 응답 | 설계 외 추가 응답 | `monitoring_views.py:172-173`에서 노출. `IndicatorRow` 펼침 영역에서 표시 | A (확장) | 확장 의도 유지 |
| `IndicatorReadingsView` 일 수 상한 | 설계 `days=14` 최대 90 | 실제 최대 1825(5Y) + FMP fallback | A (확장) | 확장 의도 유지. 단 캐싱 정책 명시 권고 |

### 3-C. 설계 4.4 Neo4j 가설 그래프

| 항목 | 설계 | 실제 | 분류 |
|------|------|------|------|
| (Thesis)-[HAS_PREMISE]→(Premise) | Phase 3 (Week 19~20) | thesis 측에서 Neo4j 동기화 트랙 없음 (chain_sight 측만) | **C: 미구현** |
| (Thesis)-[SIMILAR_TO]→(Thesis) | Phase 3 | 미구현 | **C: 미구현** |
| (Indicator)-[CORRELATES_WITH]→(Indicator) | Phase 3 | 미구현 | **C: 미구현** |

### 3-D. Phase 2의 잔여 미구현 (Phase 3 진입 전 보강 후보)

| 항목 | 설계 | 실제 | 권고 |
|------|------|------|------|
| 히트맵 뷰 (설계 3.4) | Finviz 스타일 그리드 | 백엔드 응답만 | FE 시각화 단발 PR (~150줄) |
| 그래프 뷰 (설계 3.4) | 시계열 선 + 지지/중립/반박 Y축 | row 단위 차트로 대체 (다른 형태) | 의도적 우회 — 결정 명시 권고 |
| 스냅샷 히스토리 API (설계 6.1) | GET /{id}/snapshots/ | 미구현 | API 추가 + 히스토리 FE 진입 시 묶음 |
| [근거] 설명 API (설계 6.1, 6.2) | GET /{id}/indicators/{iid}/explanation/ | description 응답으로 대체 | 의도적 단순화 / 신규 PR 불필요 |
| DNA 슬라이더 (통합 로드맵 2.3) | personalization_weight UI | 미구현 (필드는 모델에 있음) | Phase 4 진입 시 묶음 |
| 역제안 Contrarian Nudge (2.4) | 안 쓰는 유형 지표 1개 끼워넣기 | 미구현 | – |
| 상관계수 자동 할인 (수학 모델 Phase 2) | 60일 |ρ|≥0.9 → 1/√k | 미구현 (services/correlation 부재) | Phase 4 |
| Adaptive Decay/Window | 변동성 기반 | 미구현 | Phase 4 |

### 3-E. Phase 4 (Week 21+) — 전부 미진입

| 항목 | 상태 |
|------|------|
| DNA 벡터화 (16차원) | C: 미구현 |
| 유효성 벡터화 (6차원) | C: 미구현 |
| 합성 에이전트 + Online LR | C: 미구현 |
| 반대 가설 자동 생성 | C: 미구현 |
| 과거 유사 상황 검색 (벡터) | C: 미구현 |
| Change Point Detection / 칼만 필터 | C: 미구현 |

---

## 부록 A — 분류 기호 정의

- **A: 완전 구현** — 설계 요구사항을 만족(또는 확장)하며 현재 채택 경로에서 활용됨
- **B: 부분 구현** — 일부 컴포넌트만 작성됐거나, 작성됐으나 사용처에서 미통합 / 의도적 단순화
- **C: 미구현** — 설계에 있으나 아직 미진입
- **D: 폐기/대체** — 설계가 후속 문서로 공식 교체되어 더 이상 구현 대상이 아님

## 부록 B — 권고 후속 작업 (감사 결과 도출)

1. **Phase 3 리디자인 잔여 코드 정리 (1 PR, ~100줄 삭제)**
   - `RealValueIndicatorCard.tsx` + 테스트 / `ChartToggleButton.tsx` / `PeriodSelector.tsx` / `IndividualMiniCharts.tsx` 중 IndicatorRow 단일화 결정 후 일괄 삭제
   - `MoonPhase` 빈 상태 사용 여부 의사결정 + barrel export 동기화
2. **`notable_changes` 데이터 흐름 무결성 점검** (별도 감사)
   - snapshot_builder가 실제 alert 이벤트를 `notable_changes`로 변환·저장하는지 확인
3. **`generate_thesis_summaries` 비용 가드 보강 (1 PR, ~10줄)**
   - `notable_changes` 비었으면 skip하는 트리거 추가
4. **Phase 2 잔여 단발 PR — 히트맵 FE 시각화** (백엔드 응답 활용)
5. **Phase 3 ‘원안’ DNA 프로필 채택 여부 결정**
   - Phase2_completion_summary.md §8 의 FE-PR-11 은 폐기됐으나 모델·계산은 살아있음. 활용처가 없으면 DECISIONS.md에 명시적으로 “Phase 4까지 보류” 기록 권고
