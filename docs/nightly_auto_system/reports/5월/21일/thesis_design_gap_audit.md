# Thesis Control 설계 갭 감사

> 작성일: 2026-05-22
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` + `frontend/components/thesis/` 실제 구현
> 모드: 읽기 전용 (코드 수정 없음)

---

## 요약 (Phase별 구현률)

| Phase | 범위 | 상태 | 구현률 |
|-------|------|------|--------|
| **Phase 1 (MVP — 관제 엔진)** | Django 모델, 가설 CRUD, 대화형 빌더, 수학 엔진(Stage 0–3), Celery 태스크, 카드뷰 대시보드 | (A) 완전 구현 | **~95%** |
| **Phase 2 (모니터링 강화)** | 히트맵·그래프 뷰, 변화 감지·알림, AI 일일 요약, [근거] 캐싱, 뉴스 센티먼트, 오늘 이슈 | (B) 부분 구현 | **~70%** |
| **Phase 2 프론트엔드 (FE-PR-1~6)** | 라우팅 7개, 빌더 6단계, 지표 설정, 카드뷰 대시보드, 알림, 마감 | (A) 완전 구현 | **100%** (보고서 기준) |
| **Phase 3 백엔드 (PR-7)** | `display_unit` 필드, raw_value 응답 확장, IndicatorReadingsView, ai_summary/notable_changes 응답 | (A) 완전 구현 | **100%** |
| **Phase 3 프론트엔드 (PR-8 redesign)** | 실제 값 카드, AI 분석 섹션, 오늘의 변화 섹션 | (B) 부분 구현 | **~60%** (컴포넌트는 존재, 페이지 와이어링은 IndicatorRow로 대체) |
| **Phase 3 프론트엔드 (PR-9 redesign)** | 차트 토글, 기간 선택, 개별 미니차트 | (D) 폐기/대체 | **~30%** (컴포넌트 파일은 존재, 페이지에서 미사용 — IndicatorRow의 내부 차트로 흡수) |
| **Phase 3 백엔드 (PR-10 AI 파이프라인)** | `generate_thesis_summaries` Celery task, notable_changes 연동 | (B) 부분 구현 | **~60%** |
| **Phase 3 — Phase2_completion_summary 표 (FE-PR-7~11)** | 탭 구조·히트맵·히스토리 탭·마감 아카이브·DNA 프로필 | (C) 미구현 | **~10%** (모델만 존재, UI 없음) |
| **Phase 4 (Phase 1 통합 로드맵: 학습/DNA)** | HypothesisEvent, ValidityRecord, InvestorDNA | (A) 완전 구현 (모델·이벤트 기록 측면) | **~80%** (UI/소비 측면 미구현) |
| **Phase 4 통합 로드맵 (Phase 2~4: 유효성 활성화, 합성 에이전트, 벡터화)** | ValidityScore, 슬라이더, 합성 부트스트래퍼, DNA 벡터 | (C) 미구현 | **0%** |
| **LLM Builder Phase A (one-shot proposal)** | builder_state, prompt_builder, llm_postprocess, feature_flags | (A) 완전 구현 | **100%** (work_done 보고서 기준) |
| **LLM Builder Phase B (Keyword Cache & Monitoring)** | KeywordCache, news/eod/chain collectors, hint builder, `check_keywords` cmd | (A) 완전 구현 | **~90%** |
| **LLM Builder Phase C (Health Report, 스트리밍, 멀티턴 수정)** | — | (C) 미구현 | **0%** |
| **Community (인기/템플릿/Chain Sight 연동)** | ThesisFollow, PopularThesisCache 모델 + 진입 경로 3·4·5 | (C) 미구현 | **~10%** (모델만 존재, API/뷰/UI 없음) |
| **분기 지표 대시보드 plan** | metrics data_source, quarterly_metric_fetcher, RATIO_METRICS 변환, QuarterlySparkline | (A) 완전 구현 | **100%** |

전반: Phase 1 + Phase 2 핵심 루프 + 빌더 + 분기 지표 → 완료. Phase 3 대시보드 리디자인은 **컴포넌트는 만들어졌지만 페이지 합류는 다른 패턴(IndicatorRow)으로 대체된 상태**. 학습 레이어(이벤트·DNA) 기록은 되고 있으나 활용 UI는 없음. 커뮤니티/Phase 4 고도화는 미착수.

---

## 문서별 상태 테이블

### 1. 핵심 설계 문서 (`plan/`)

| 문서 | 핵심 내용 | 코드 매핑 | 분류 |
|------|----------|----------|------|
| `thesis_control_design.md` (§4.1 디렉토리) | thesis/ 앱 구조 (models/services/tasks/views/serializers/urls/admin) | 모두 존재. `services/news_connector.py` `services/summary_generator.py`는 명시 이름과 다름 (역할은 `keyword_collectors/news.py` + `tasks/summary.py`로 대체) | (B) 부분 구현 |
| `design.md` (§4.2 모델) Thesis | 13 필드 (description, target/target_type, expected_*, target_date_*, thesis_type, entry_source, source_news, copied_from, status, overall_score, tags, category, alert_preference) | `thesis/models/thesis.py`: status choices가 설계의 `setting_up/active/paused/closed_correct/closed_incorrect/closed_neutral` → 실제는 `setting_up/active/closed/paused` + `outcome` 분리. `overall_score`→`current_score`. `tags`/`category`/`alert_preference` **없음**. `current_state` 추가됨 (v2.3.2). `premise_universe_ids`/`indicator_universe_ids` 추가됨 (v2.3.2) | (B) 부분 구현 — outcome 분리·태그 제거 |
| `design.md` ThesisPremise | `extraction_level`, `current_score`, `current_label`, `explanation` | 실제 모델: `category`, `weight`, `is_active`, `is_paused`. `extraction_level`/`current_score`/`current_label`/`explanation` **없음** | (D) 폐기/대체 — 다른 메타로 대체 |
| `design.md` ThesisIndicator | `support_direction`, `current_arrow_degree`, `current_label`, `rationale`, `context_explanation`, `is_ai_recommended`, `is_active`, `order`, `last_updated` | 실제: `support_direction` ✓, `current_degree`/`current_label`/`current_score`/`current_color` ✓, `recommendation_reason` ✓ (rationale 역할), `display_unit` 추가, v2.3.2 필드(epsilon/window/decay/min/max_valid_value/max_change_pct/allow_extreme_jump/is_paused/override_score) 다수 추가. `is_ai_recommended` **없음** (HypothesisEvent로 대체) | (A) 완전 구현 — 확장됨 |
| `design.md` IndicatorReading | 시계열 모델 | `value`, `raw_value`, `asof`, `validation_status`, `fetched_at` ✓. 단 v2.3.2가 `value`(정규화)와 `raw_value`(원본) 둘 다 저장하는 구조로 확장됨 | (A) 완전 구현 |
| `design.md` ThesisSnapshot | `date`, `overall_score`, `overall_label`, `indicator_scores`, `notable_changes`, `ai_summary` | `asof_date`(rename), `state`(label 대신), `premise_scores`, `indicator_degrees` (indicator_scores 대체), `notable_changes` ✓, `ai_summary` ✓, `data_coverage`/`universe_snapshot`/`ordered_indicator_ids` (v2.3.2) 추가 | (A) 완전 구현 — 확장됨 |
| `design.md` ThesisAlert | 5 alert_type | 실제: 11 alert_type (direction_flip/sharp_move/extreme_volatility/weakest_link/premise_divergence/stale_data/indicator_overlap/indicator_bias/state_change/milestone/needs_review) + `severity` + throttling(`target_id`/`cooldown_hours`) | (A) 완전 구현 — 확장됨 |
| `design.md` ThesisFollow, PopularThesisCache | 커뮤니티 모델 | `thesis/models/community.py`에 존재. API 뷰·serializer·라우팅 **없음** | (C) 미구현 (스켈레톤만) |
| `design.md` §4.4 Neo4j 그래프 | (Thesis)-[HAS_PREMISE]-(Premise) 등 | 검색 결과 thesis 관련 Neo4j sync 코드 없음 | (C) 미구현 |
| `design.md` §5.4 화살표 각도 계산 | normalize→support_direction→degree | `services/arrow_calculator.py` (85 줄) 존재 | (A) 완전 구현 |
| `design.md` §6.1 API 엔드포인트 | 22개 엔드포인트 | `thesis/urls.py`: 가설 CRUD, conversation(start/respond/news-issues/suggest), dashboard, indicator-readings, alerts(list/read), premises/indicators 중첩 라우터, indicators/auto/. `summary`(쉐이크), `popular/`(인기), `templates/`(템플릿), `daily-issues/` (대체: conversation/news-issues 존재) → 부분 차이 | (B) 부분 구현 |
| `thesis_control_math_model_final.md` (v2.3.2) | 3-Stage Pipeline + Stage 0 검증 + Robust Z + 가중평균 + Rule-based State + universe 고정 | `services/data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `thesis_state_machine.py`, `snapshot_builder.py`, `alert_engine.py` — 6개 서비스 모두 존재. `latest_validated_value` property 존재 | (A) 완전 구현 |
| `thesis_control_integrated_roadmap.md` Phase 1 | 관제 엔진 + HypothesisEvent + ValidityRecord + InvestorDNA (기록 단계) | `models/learning.py`에 3개 모델 모두 ✓. `views/thesis_views.py`의 `perform_create/perform_destroy/close`에서 13개 event_type 중 8종 기록 중. close 시 `_compute_validity_score`(2×2 매트릭스) + `_update_investor_dna` 호출 | (A) 완전 구현 |
| `integrated_roadmap.md` Phase 2~4 | ValidityScore 활성화, DNA 슬라이더, 합성 에이전트, Online LR, 벡터화 | 모델·코드 모두 없음 | (C) 미구현 |
| `thesis_control_phase3_frontend_redesign.md` PR-7 | `display_unit` 필드 + DashboardView raw_value 확장 + IndicatorReadingsView | migration 0004/0005 (display_unit), `monitoring_views.py` ✓, URL 등록 ✓. 단 days clamp가 설계 90 → 실제 1825 (5Y) 로 확장됨 (분기 지표 plan 합류 영향) | (A) 완전 구현 |
| `thesis_control_phase3_frontend_redesign.md` PR-8 | RealValueIndicatorCard, AISummarySection, NotableChangesSection | 컴포넌트 3개 모두 신규 생성 ✓. AISummarySection·NotableChangesSection은 `app/thesis/[thesisId]/page.tsx`에 와이어링 ✓. **RealValueIndicatorCard는 페이지에서 미사용**: page.tsx가 `IndicatorRow` (분기 지표 plan 산출물)를 대신 사용. RealValueIndicatorCard는 테스트(`__tests__/thesis/RealValueIndicatorCard.test.tsx`)에서만 호출됨 | (D) 폐기/대체 — 핵심 카드가 IndicatorRow로 대체됨 |
| `phase3_frontend_redesign.md` PR-9 | ChartToggleButton, PeriodSelector, IndividualMiniCharts + Mock readings | 파일 3개 모두 존재, 그러나 `app/thesis/[thesisId]/page.tsx`에 import/render **없음**. IndicatorRow 내부에 자체 차트(`AreaChart` + `DAILY_PERIODS` 1M/1Y/3Y/5Y)가 구현되어 PR-9 디자인을 흡수. PR-9의 7D/14D/30D 토글 모델은 폐기됨 | (D) 폐기/대체 — 차트 패턴 변경 |
| `phase3_frontend_redesign.md` PR-9 삭제 대상 | `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 삭제 + `MoonPhase`/`scoreToPhaseMeta` 검토 | 셋 모두 components/thesis/dashboard/ 에서 **삭제 완료** (grep으로 `.next` 빌드 캐시에만 잔존). `MoonPhase`는 `list/ThesisListCard.tsx` + `(list)/page.tsx`에서 사용 중 → 유지 결정 | (A) 완전 구현 |
| `phase3_frontend_redesign.md` PR-10 (AI 파이프라인) | `generate_thesis_summaries` Celery 07:30 + notable_changes 자동 채움 | `tasks/summary.py` (142 줄) 존재. `services/snapshot_builder.py` (183 줄) 존재. Beat 등록 여부는 본 감사 범위 외 | (B) 부분 구현 — 본문 미확인 |

### 2. 빌더 재설계 (`plan/talking_builder/`)

| 문서 | 코드 매핑 | 분류 |
|------|----------|------|
| `llm_builder_plan.md` (배경) | wizard→one-shot 전환 배경 | (A) 완료 (work_done/phase_a_llm_builder.md) |
| `redesign_build_plan/01_phase_a_mvp.md` | builder_state.py, prompt_builder.py, llm_postprocess.py, builder_events.py, feature_flags.py + thesis_builder LLM mode + match_indicators_for_llm + PresetSelector/IndicatorCard | 백엔드 5개 파일 모두 존재 (prompt_builder 991줄, thesis_builder 2066줄, indicator_matcher 338줄). FE: `PresetSelector.tsx`/`IndicatorCard.tsx` 존재 | (A) 완전 구현 |
| `redesign_build_plan/02_phase_a_hardening.md` (PR-4~7) | normalize/validate 보강 + fallback + 로그 지표 + FE 에러 바운더리 | work_done에 PR-1~3까지 명시 (커밋 `09b0f8b` MVP, `6d72432` Hardening) → 완료 (보고서 기준) | (A) 완전 구현 |
| `redesign_build_plan/03_phase_b_keywords.md` (PR-8~12) | KeywordCache 모델 + Admin + collectors(news/eod/chain) + hint builder + monitoring | migration 0006/0007 (keyword cache, strength), `services/keyword_cache.py`, `keyword_hint.py`, `keyword_collectors/{news,eod,chain}.py`, `management/commands/check_keywords.py` + `keyword_health_check.py` 모두 존재 | (A) 완전 구현 |
| `redesign_build_plan/04_phase_c_advanced.md` | Daily Health Report, 스트리밍, Guided Suggestion, 멀티턴 수정 | 코드 없음 | (C) 미구현 |
| `quarterly_indicator_dashboard_plan.md` | metrics data_source 등록 + quarterly_metric_fetcher + RATIO_METRICS + QuarterlySparkline | migration 0008 (metrics data source), `services/quarterly_metric_fetcher.py` (364줄), `DashboardView`에서 quarterly cache + ratio 변환 ✓, `frontend/components/thesis/dashboard/QuarterlySparkline.tsx` + IndicatorRow 연동 ✓ | (A) 완전 구현 |

### 3. 프론트엔드 Phase 1 (`docs/thesis_control/thesis_control_phase1_frontend_FE_PR_*.md`)

| 문서 | task_done 보고서 | 코드 매핑 | 분류 |
|------|----------------|----------|------|
| FE-PR-1 라우팅 + 공통 컴포넌트 | `FE-PR-1_routing_common_components.md` | `frontend/app/thesis/{layout,page,new/page,(list)/{page,alerts/page},[thesisId]/{page,close/page,indicators/page}}.tsx` 모두 존재. `components/thesis/common/{AlertBell,ArrowIndicator,BottomSheet,IndicatorCard,MoonPhase,ThesisBadge}.tsx` 6개 (설계 5개 + IndicatorCard) | (A) 완전 구현 |
| FE-PR-2 가설 목록 + 오늘의 변화 + 진입점 | `FE-PR-2_thesis_list_page.md` | `components/thesis/list/{EntryPointGrid,ThesisListCard,TodayChangeCard}.tsx` 3개 ✓ | (A) 완전 구현 |
| FE-PR-3 대화형 빌더 (6단계) | `FE-PR-3_builder_implementation.md`/`FE-PR-3_plan_review_v3.md` | `components/thesis/builder/{BottomSheet,ChatBubble,MultiSelectFooter,NewsSelector,OptionButton,PremiseCard,ProgressBar,SuggestionCard,TextInput}.tsx` 9개 ✓ (설계 7개+) | (A) 완전 구현 |
| FE-PR-4 지표 설정 | `FE-PR-4_indicator_setup.md` | `components/thesis/indicators/{AddIndicatorSheet,IndicatorSetupCard,RecommendCard}.tsx` 3개 ✓ | (A) 완전 구현 |
| FE-PR-5 관제실 대시보드 (달 위상 + 화살표) | `FE-PR-5_dashboard.md` | `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` — **삭제됨** (Phase 3 PR-9에서). 현재는 `DashboardHeader`+`AISummarySection`+`NotableChangesSection`+`IndicatorRow`로 완전 교체 | (D) 폐기/대체 — 후속 Phase에서 리디자인 |
| FE-PR-6 알림 + 마감 + API + QA | `FE-PR-6_alerts_close_qa.md` | `components/thesis/alerts/{AlertCard,AlertFilterTabs,EmptyAlerts}.tsx` 3개 ✓, `components/thesis/close/{CloseConfirmDialog,OutcomeSelector}.tsx` 2개 ✓ | (A) 완전 구현 |

### 4. Phase2_completion_summary 미래 계획 표 (FE-PR-7~11)

> Phase2 완료 보고서가 명시한 후속 PR — **`phase3_frontend_redesign.md`(실제 진행된 PR-7~10)와 다른 안**

| FE-PR | 설계 의도 | 구현 상태 |
|-------|----------|----------|
| FE-PR-7 대시보드 탭 구조 + 상세 탭 (3탭: 관제/상세/히스토리) + 전제 CRUD | `app/thesis/[thesisId]/page.tsx`에 탭 구조 없음. 전제 CRUD UI는 빌더 외 별도 없음 (API `ThesisPremiseViewSet`은 존재) | (C) 미구현 |
| FE-PR-8 히트맵 + 지표 상세 편집 (weight/direction) | DashboardView가 `heatmap` 응답을 내려주지만 FE 페이지에서 렌더링 안 함. 지표 편집 UI 없음 (모델·serializer는 weight·support_direction 지원) | (C) 미구현 |
| FE-PR-9 히스토리 탭 (recharts 라인 + 스냅샷 타임라인) | IndicatorRow가 개별 지표별 시계열 차트를 제공하지만 "스냅샷 타임라인" 별도 탭은 없음 | (B) 부분 (지표별 차트만) |
| FE-PR-10 마감 아카이브 + ValidityMatrix 요약 | `close/page.tsx`는 OutcomeSelector만 제공. 마감된 가설 목록·복기 화면 없음 | (C) 미구현 |
| FE-PR-11 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `InvestorDNA` 모델·집계 로직(`_update_investor_dna`)은 존재하지만 API endpoint·UI 없음 | (C) 미구현 |

### 5. 진입 경로 (design.md §2.3)

| 경로 | entry_source choice | 백엔드 | 프론트엔드 | 분류 |
|------|---------------------|--------|-----------|------|
| 1. 📰 오늘 이슈 | `news` | `conversation/news-issues/` (NewsIssuesView) ✓ | EntryPointGrid에 진입점 ✓ | (A) 완전 구현 |
| 2. 💬 내 생각 | `free_input` | LLM `_handle_proposal` + 위자드 fallback ✓ | EntryPointGrid + builder 페이지 ✓ | (A) 완전 구현 |
| 3. 🔥 인기 가설 | `popular` | PopularThesisCache 모델만, 뷰 없음 | UI 없음 | (C) 미구현 |
| 4. 📋 템플릿 | `template` | 라우팅 없음 | UI 없음 | (C) 미구현 |
| 5. 🔗 Chain Sight에서 | `chainsight` | 라우팅 없음 | UI 없음 | (C) 미구현 |

---

## Phase 3 미구현 항목 상세

### A. Phase 3 통합 로드맵 관점 (학습 레이어 활성화)

`thesis_control_integrated_roadmap.md` §3 (Phase 3 = 합성 에이전트 + 자동학습)는 코드/모델 **전무**:

1. **ValidityScore 모델** (집계 테이블, `(thesis_type, indicator_data_key, market_regime)` 유니크) — 없음. 현재는 `ValidityRecord`(원시 기록) 만 쌓고 있음
2. **Celery 주 1회 집계 태스크** (`ValidityRecord → ValidityScore`) — 없음
3. **`indicator_matcher.py`의 유효성 점수 부스트** — `match_indicators_for_premise`/`match_indicators_for_llm`은 키워드 룰 기반이며 ValidityScore 참조 없음
4. **DNA 슬라이더** (`personalization_weight`) — InvestorDNA 모델에 필드는 있으나 (default 0.5) 사용처 없음
5. **역제안 (Contrarian Nudge)** — 코드 없음
6. **합성 에이전트 부트스트래퍼** (`SyntheticBootstrapper`, 20~30개 페르소나, `ValidityRecord.is_synthetic`) — 모델·코드 없음
7. **Online Logistic Regression** (`ThesisWeightLearner`, W_j_suggested) — 코드 없음

### B. Phase 3 프론트엔드 리디자인 관점 (`phase3_frontend_redesign.md`)

| 항목 | 설계 의도 | 실제 상태 |
|------|----------|----------|
| `OverallMoon` 삭제 | 달 위상 추상 제거 | ✅ 삭제됨 (page.tsx, 빌드 캐시 외 없음) |
| `DashboardIndicatorCard` → `RealValueIndicatorCard` 대체 | 실제 값 카드로 교체 | ⚠️ RealValueIndicatorCard는 **생성됐으나 페이지 미사용**. 페이지는 `IndicatorRow`(분기 지표 plan 산출물)로 대체 — 사실상 두 컴포넌트가 같은 목적으로 존재하는 중복 상태. 정리 필요 |
| `RecentChange` → `NotableChangesSection` 대체 | alert_engine 이벤트 기반 | ✅ 완전 구현, page.tsx 와이어링됨 |
| `MoonPhase` 삭제 검토 | 다른 곳 미사용 시 제거 | ❌ 유지 — `list/ThesisListCard.tsx` + `(list)/page.tsx` 가 여전히 사용 중. 설계가 "다른 곳 import 검색 후 결정" 으로 조건부였으므로 유지 결정은 정당함 |
| `scoreToPhaseMeta()` 삭제 | OverallMoon 전용 | 본 감사 미확인 (utils.ts 미열람) |
| `AISummarySection` 생성 + 와이어링 | summary falsy → 미렌더 | ✅ 완전 구현 (`page.tsx:74-78`) |
| `ChartToggleButton` + `PeriodSelector` + `IndividualMiniCharts` 생성 + 와이어링 | 카드 그리드 아래 토글 영역 | ⚠️ **컴포넌트 3개 파일은 존재**하지만 `app/thesis/[thesisId]/page.tsx`에서 import 없음. IndicatorRow가 자체 차트(`DAILY_PERIODS = 1M/1Y/3Y/5Y`)를 갖고 있어 흡수됨. 설계의 7D/14D/30D 모델은 폐기됨 |
| `useAllIndicatorReadings` 훅 추가 | 다수 지표 병렬 fetch | 본 감사 미확인 (queries.ts 미열람). IndicatorRow가 `useIndicatorReadings` 단건 훅을 쓰므로 N건이면 N개 쿼리 발생 추정 |
| `MOCK_READINGS` 추가 | mock 모드 차트 | 본 감사 미확인 |

### C. Phase 3 PR-10 (AI 모니터링 파이프라인)

| 항목 | 설계 | 실제 상태 |
|------|------|----------|
| `generate_thesis_summaries` Celery task (07:30, Gemini Flash, 변화 있는 가설만) | 명세 ✓ | `tasks/summary.py` 142줄 존재. 호출 빈도/Beat 등록은 미확인 |
| `notable_changes` 자동 채움 (alert_engine 이벤트 변환) | snapshot_builder에서 today_alerts 매핑 | `services/snapshot_builder.py` 183줄 존재. 본 감사에서 내부 매핑 로직은 미열람 |
| Weekly Health Check (지표 커버리지·유효성·전제 재검토·상관관계 알림) | 데이터 축적 후 구현 | (C) 미구현 |

### D. Phase2_completion_summary가 약속한 FE-PR-7~11 (위 표 4 참조)

5개 PR 모두 미착수. 가장 큰 갭은:
- **마감 후 복기/아카이브 UI** — 사용자가 마감한 가설을 다시 못 본다 (모델·outcome 필드는 있음)
- **투자자 DNA 프로필 UI** — 학습 데이터는 쌓이는데 사용자는 못 본다. 특허 청구항(독립항 1)과 직결
- **전제 CRUD UI** — 빌더 외에서 전제 수정·추가가 불가 (API는 있음)
- **히트맵 UI** — DashboardView가 응답을 내려주는데 렌더링이 없음
- **스냅샷 타임라인 / 히스토리 탭** — IndicatorRow 차트로 일부 흡수되나 전체 가설 점수 추이는 안 보임

### E. Community 기능 (design.md §2.3 경로 3~5)

ThesisFollow, PopularThesisCache 모델은 있으나:
- `popular/`, `templates/`, `chainsight` 라우팅 0건
- 진입 경로 5개 중 2개만 동작 (`news`, `free_input`)
- Chain Sight ↔ Thesis Control 양방향 연동 없음

### F. Neo4j 가설 그래프 (design.md §4.4)

`(Thesis)-[HAS_PREMISE]-(Premise)`, `(Thesis)-[SIMILAR_TO]-(Thesis)`, `(Indicator)-[CORRELATES_WITH]-(Indicator)` 등 — Thesis 관련 Neo4j sync 코드 없음. 가설 간 연결 제안·유사 가설 추천 불가.

---

## 부록: 핵심 발견 사항 (Tldr)

1. **MVP는 견고하다.** Phase 1·2 + 빌더 + 분기 지표 plan 까지 4개 큰 흐름은 거의 완전 구현됨. 수학 엔진(v2.3.2) 6개 서비스 + 11개 alert_type + Stage 0 검증 + universe 고정 등 백엔드 깊이 충분.
2. **Phase 3 프론트엔드 리디자인이 두 번 갈렸다.** 설계 문서가 두 가지 PR-7~11 안을 제시함:
   - `phase3_frontend_redesign.md` (PR-7~10): 백엔드 + 실제 값 카드 + 미니차트 + AI 파이프라인 → **PR-7·PR-8 일부·삭제 항목은 완료**, **PR-9 차트는 IndicatorRow로 흡수되어 폐기**, **PR-10 부분 완료**
   - `Phase2_completion_summary.md` (FE-PR-7~11): 탭·히트맵·아카이브·DNA → **전부 미구현**
3. **`RealValueIndicatorCard` 와 `IndicatorRow` 중복.** 둘 다 같은 카드 디자인을 표방하지만 페이지는 후자를 사용. 전자는 테스트에서만 호출됨. 정리 후보.
4. **학습 레이어 기록은 되지만 활용은 0**. HypothesisEvent·ValidityRecord·InvestorDNA 모델 + 집계 함수 + close 시 자동 기록까지 모두 동작. 그러나 ValidityScore·DNA 슬라이더·역제안·합성 부트스트래퍼 등 활용 코드는 전무. **특허 청구항 독립항 1·2·3 모두 백엔드 코드 미진**.
5. **Community 기능 사실상 미구현.** 5개 진입 경로 중 2개만 (`news`, `free_input`). 모델은 있어도 뷰·UI 없음.
6. **Neo4j 통합 미진.** 가설 ↔ 전제 ↔ 지표 그래프, 유사 가설 추천 등 §4.4 전체가 코드 없음.
7. **권장 다음 단계** (우선순위 추정):
   - (a) Phase2_completion_summary FE-PR-10 (마감 아카이브) — 학습 데이터를 사용자에게 보여주는 최소한의 UX
   - (b) FE-PR-11 (DNA 프로필) — 특허 청구항 가시화
   - (c) `RealValueIndicatorCard` ↔ `IndicatorRow` 정리 + `ChartToggleButton`/`PeriodSelector`/`IndividualMiniCharts` 사용 여부 결정 (사용 안 하면 삭제, 사용하려면 page.tsx에 와이어링)
   - (d) ValidityScore 집계 태스크 — 데이터가 쌓이고 있으므로 빨리 시작하는 것이 효율적
