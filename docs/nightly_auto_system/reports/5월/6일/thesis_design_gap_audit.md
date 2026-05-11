# Thesis Control 설계 갭 감사

> 감사일: 2026-05-07
> 감사 대상: `docs/thesis_control/` 설계 문서 vs `thesis/` (백엔드) + `frontend/components/thesis/` (프론트)
> 모드: 읽기 전용 (코드 수정 없음)

---

## 요약 (Phase별 구현률)

| Phase | 설계 문서 | 핵심 산출물 | 상태 | 구현률 |
|-------|----------|-----------|------|-------|
| **Phase 1 (MVP)** | `thesis_control_design.md` (UX/API/모델) + `thesis_control_implementation_guide.md` (Week 1~6) + `thesis_control_math_model_final.md` (v2.3.2) | 모델/스코어링/CRUD/대화 빌더/Celery 3태스크 | (A) 완전 구현 | ≈95% |
| **Phase 2 (모니터링 강화)** | 통합 로드맵 Week 7~12 | 뉴스 연동/뷰 확장/유효성/DNA 슬라이더/[근거] | (B) 부분 구현 | ≈45% |
| **Phase 3 원안** | `Phase2_completion_summary.md` 끝의 FE-PR-7~11 표 (3탭 + 히트맵 + 히스토리 + 아카이브 + DNA 프로필) | UX 깊이/회고/프로필 | (D) 폐기·대체 | 0% (FE-PR-7~11 원안 미착수, 리디자인으로 대체) |
| **Phase 3 리디자인** | `thesis_control_phase3_frontend_redesign.md` (PR-7~10) | 실제 값 카드/AI 분석/미니차트/AI 파이프라인 | (B) 부분 구현 | ≈75% (PR-7/8/9 구현 + IndicatorRow 추가 / PR-10 미구현) |
| **Phase 4 (지능화)** | 통합 로드맵 Week 21+ | 벡터/Online LR/합성 에이전트/Neo4j | (C) 미구현 | 0% |
| **빌더 재설계 (LLM Phase A)** | `talking_builder/` v4 (one-shot proposal) | LLM 빌더 + Suggestion Mode | (A) 완전 구현 | ≈95% (Phase A 완료) |

> **핵심 결론**: 원안 Phase 3 (FE-PR-7~11, "3탭+히트맵+히스토리+아카이브+DNA")는 폐기되고, 그 자리를 `Phase 3 redesign` (실제 값 + 미니차트)이 대체했다. 리디자인은 PR-7/8/9가 구현되고 **PR-10 (`generate_thesis_summaries` Celery 태스크)이 누락** — `AISummarySection`은 항상 빈 문자열을 받아 미렌더링되는 상태(`PROGRESS.md` audit P0 #15와 일치).

---

## 문서별 상태 테이블

### 백엔드 모델 / API / Celery

| 항목 | 설계 문서 (출처) | 현재 구현 | 상태 |
|------|----------------|----------|------|
| Thesis 모델 (필수 필드) | design 4.2 | `thesis/models/thesis.py` | (A) 완전 |
| ThesisPremise (extraction_level 등) | design 4.2 | `thesis.py` (단, `extraction_level`/`current_score`/`current_label`/`explanation` 없음, 대신 `category`/`weight`/`is_paused`) | (B) 부분·대체 |
| ThesisIndicator + v2.3.2 필드 | math 9 | `models/indicator.py` (epsilon/window/decay/min/max_valid_value 등 모두 존재) + `display_unit` (PR-7) + `recommendation_reason` (분기 지표 작업) | (A) 완전 |
| IndicatorReading + validation_status | math 2 | `models/indicator.py` + 8개 status choice | (A) 완전 |
| ThesisSnapshot (asof_date, coverage, universe) | math 9 | `models/monitoring.py` | (A) 완전 |
| ThesisAlert (target_id, cooldown_hours) | math 12.4 | `models/monitoring.py` | (A) 완전 |
| ThesisFollow / PopularThesisCache | design 4.2 (커뮤니티) | `models/community.py` 정의됨, **API/뷰/UI 미연결** | (D) 모델만 존재, 미사용 |
| HypothesisEvent / ValidityRecord / InvestorDNA | guide 1.2~1.4 | `models/learning.py` + `views/thesis_views.py` close()에서 자동 기록 | (A) 완전 (집계만 백엔드) |
| KeywordCache | talking_builder v4 | `models/keyword.py` + 마이그레이션 0006/0007 | (A) 완전 |
| 가설 CRUD + close API | design 6.1 | `views/thesis_views.py` (ModelViewSet + close action + ValidityRecord/InvestorDNA 갱신) | (A) 완전 |
| 전제 CRUD API | design 6.1 | `ThesisPremiseViewSet` (premises router) | (A) 완전 |
| 지표 CRUD + auto 추천 API | design 6.1 | `ThesisIndicatorViewSet` + `auto` action | (A) 완전 |
| 대화형 빌더 API (start/respond) | design 6.1 + talking_builder | `views/conversation_views.py` (wizard + LLM dual mode + `_sanitize_state`) | (A) 완전 |
| 관제실 대시보드 API | design 6.2 | `views/monitoring_views.py` `DashboardView` | (A) 완전 (히트맵 셀 포함) |
| 알림 List/Read API | design 6.1 | `AlertListView` + `AlertReadView` | (A) 완전 |
| 뉴스 이슈 API (`daily-issues`) | design 6.1 | 설계 경로 `/daily-issues/` 대신 `/conversation/news-issues/`로 구현 (Gemini 변환) | (B) 경로 다름·기능 동등 |
| 가설 제안 API (`/conversation/suggest/`) | talking_builder v4 (Suggestion Mode) | `SuggestThesesView` (Gemini one-shot, fallback 포함) | (A) 완전 |
| 인기 가설 API (`/popular/`) | design 6.1 | **미구현** — 라우트 없음 | (C) 미구현 |
| 템플릿 API (`/templates/`) | design 6.1 | **미구현** — 라우트 없음 | (C) 미구현 |
| 스냅샷 히스토리 API (`/{id}/snapshots/`) | design 6.1 | **미구현** — 라우트 없음 (모델만 존재) | (C) 미구현 |
| AI 요약 API (`/{id}/summary/`) | design 6.1 | **미구현** — `summary_generator.py` 없음 | (C) 미구현 |
| 지표 시계열 API (`/{id}/indicators/{iid}/readings/`) | redesign PR-7 4-4 | `IndicatorReadingsView` + FMP fallback | (A) 완전 (5Y까지 확장) |
| [근거] explanation API (`/explanation/`) | design 6.1 | **미구현** — 캐싱 시스템 부재 | (C) 미구현 |
| EOD Pipeline (3 Celery 태스크) | math 7 | `tasks/eod_pipeline.py` (`update_indicator_readings`, `calculate_scores`, `create_snapshots_and_alerts`) | (A) 완전 |
| `generate_thesis_summaries` Celery | redesign PR-10 + design 5.3 | **미구현** — `tasks/` 폴더에 파일 없음. `ThesisSnapshot.ai_summary`는 항상 `''` | (C) 미구현 (PROGRESS audit P0 #15와 일치) |
| `update_popular_thesis_cache` Celery | design 5.3 | **미구현** | (C) 미구현 |
| `prepare_daily_issues` Celery | design 5.3 | **미구현** (실시간 변환만) | (C) 미구현 |
| Validation/Stage 0 (`data_validator.py`) | math Stage 0 | `services/data_validator.py` | (A) 완전 |
| Robust Z + Decay (`indicator_scorer.py`) | math Stage 1 | `services/indicator_scorer.py` | (A) 완전 |
| 가중평균/최약고리 (`premise_aggregator.py`) | math Stage 2 | `services/premise_aggregator.py` | (A) 완전 |
| 상태 머신 (`thesis_state_machine.py`) | math Stage 3 | `services/thesis_state_machine.py` | (A) 완전 |
| 알림 throttling (`alert_engine.py`) | math 12.4 | `services/alert_engine.py` | (A) 완전 |
| Snapshot Builder | math 9 | `services/snapshot_builder.py` | (A) 완전 |
| Indicator Matcher (LLM PK 매칭) | talking_builder Phase A | `services/indicator_matcher.py` + `match_indicators_for_llm` | (A) 완전 |
| Quarterly Metric Fetcher | 분기 지표 추가 작업 | `services/quarterly_metric_fetcher.py` | (A) 완전 (설계 후 추가) |
| Neo4j 가설 관계 그래프 | design 4.4 + guide Phase 3 | **미구현** | (C) 미구현 |
| 합성 에이전트 (Synthetic Bootstrapper) | guide Phase 3 Week 15~16 | **미구현** | (C) 미구현 |
| Online Logistic Regression | guide Phase 3 Week 17~18 | **미구현** | (C) 미구현 |
| ValidityScore 집계 (주간 Celery) | guide Phase 2 Week 9~10 | **미구현** (ValidityRecord 적재만 됨) | (C) 미구현 |
| DNA 슬라이더 personalization_weight | guide Phase 2 Week 9~10 | 모델 필드 존재(`InvestorDNA.personalization_weight`), **블렌딩 로직 미구현** | (B) 모델만 |
| 상관계수 자동 할인 / Adaptive Decay | guide Phase 2 Week 11~12 | **미구현** | (C) 미구현 |

### 프론트엔드 — Phase 1~2 (FE-PR-1~6)

| 항목 | 설계 문서 (출처) | 현재 구현 | 상태 |
|------|----------------|----------|------|
| 라우팅 (7개) + authAxios | FE-PR-1 | `app/thesis/{layout,(list)/{page,alerts/page},new/page,[thesisId]/{page,indicators/page,close/page}}` + `lib/api/authAxios.ts` | (A) 완전 |
| 공통 컴포넌트 (ArrowIndicator/MoonPhase/IndicatorCard/ThesisBadge/AlertBell) | FE-PR-1 | `components/thesis/common/*.tsx` 6개 (BottomSheet 추가) | (A) 완전 |
| Skeleton (Shimmer 3종) | FE-PR-1 | `components/thesis/skeleton/ThesisSkeleton.tsx` | (A) 완전 |
| 가설 목록 페이지 (ThesisListCard + EntryPointGrid + TodayChange) | FE-PR-2 | `app/thesis/(list)/page.tsx` + `components/thesis/list/{ThesisListCard,EntryPointGrid,TodayChangeCard}.tsx` | (A) 완전 |
| 대화형 빌더 6단계 wizard | FE-PR-3 v3 | `app/thesis/new/page.tsx` (1072줄) + `components/thesis/builder/*` (BottomSheet/ChatBubble/MultiSelectFooter/NewsSelector/OptionButton/PremiseCard/ProgressBar/SuggestionCard/TextInput) | (A) 완전 |
| 지표 설정 (AI 추천 + 토글) | FE-PR-4 | `app/thesis/[thesisId]/indicators/page.tsx` + `components/thesis/indicators/{AddIndicatorSheet,IndicatorSetupCard,RecommendCard}.tsx` | (A) 완전 |
| 관제실 대시보드 (OverallMoon + DashboardIndicatorCard + RecentChange) | FE-PR-5 (원안) | OverallMoon/DashboardIndicatorCard/RecentChange는 **모두 폐기됨** (Phase 3 리디자인으로 대체) | (D) 폐기 |
| 알림 페이지 (탭 + 배지 + 읽음) | FE-PR-6 | `app/thesis/(list)/alerts/page.tsx` + `components/thesis/alerts/*` | (A) 완전 |
| 마감 페이지 (Outcome + Confirm) | FE-PR-6 | `app/thesis/[thesisId]/close/page.tsx` + `components/thesis/close/*` | (A) 완전 |
| 통합 mutations (지표 3 + 알림 + 마감) | FE-PR-6 | `lib/thesis/mutations.ts` (85줄) | (A) 완전 |
| 히트맵 뷰 | design 3.4 + Phase 2 (FE-PR-8 원안) | 백엔드 응답엔 `heatmap` 필드 있으나 **프론트 미사용** (컴포넌트 없음) | (C) 미구현 |
| 그래프 뷰 (지지/중립/반박 시계열) | design 3.4 + Phase 2 | **미구현** (컴포넌트 없음) | (C) 미구현 |
| [근거] BottomSheet 시스템 | design 2.4 + Phase 2 | BottomSheet 컴포넌트는 존재하나 **[근거] 콘텐츠는 미연동** (description/recommendation_reason 인라인 표시로 대체) | (B) 부분 |

### 프론트엔드 — Phase 3 원안 (FE-PR-7~11) vs 현재

| FE-PR | 원안 산출물 | 현재 구현 | 상태 |
|-------|-----------|----------|------|
| FE-PR-7 | 대시보드 3탭 구조 (관제/상세/히스토리) + 전제 CRUD | **미구현** — 단일 페이지(`app/thesis/[thesisId]/page.tsx`)에 IndicatorRow expandable로 대체 | (D) 폐기 |
| FE-PR-8 (원안) | Finviz 히트맵 + 지표 weight/direction 편집 | **미구현** — 히트맵 응답은 무시, 편집 UI는 `IndicatorSetupCard`의 토글/삭제로만 존재 | (D) 폐기 |
| FE-PR-9 (원안) | 히스토리 탭 (recharts + 스냅샷 타임라인) | **미구현** — 스냅샷 API조차 없음 | (C) 미구현 |
| FE-PR-10 (원안) | 마감 아카이브 + ValidityMatrix | 마감 페이지만 존재(ValidityRecord 자동 기록), **아카이브 목록/매트릭스 UI 없음** | (C) 미구현 |
| FE-PR-11 (원안) | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | **미구현** — `app/thesis/profile` 라우트 없음, `InvestorDNA` 조회 API도 없음 | (C) 미구현 |

> 원안 5개 FE-PR은 통째로 **(D) 폐기/대체**: `Phase2_completion_summary.md` §8 표에는 남아있지만, 실제로는 `thesis_control_phase3_frontend_redesign.md`로 방향 전환되었다.

### 프론트엔드 — Phase 3 리디자인 (PR-7~10)

| 항목 | 설계 문서 | 현재 구현 | 상태 |
|------|----------|----------|------|
| ThesisIndicator.display_unit 필드 | redesign 4-1 | `models/indicator.py:73-76` + 마이그레이션 0004/0005 (populate) | (A) 완전 |
| `_infer_unit()` fallback | redesign 4-3 | `monitoring_views.py:346` | (A) 완전 |
| DashboardView raw_value 확장 (raw_value/unit/previous/change_pct + ai_summary + notable_changes) | redesign 4-2 | `monitoring_views.py:94-174` 모두 구현 + 분기 지표 확장 (`fiscal_label`/`quarterly_history`/`is_quarterly`/`comparison_type`) + `description`/`recommendation_reason` 추가 | (A) 완전·확장 |
| IndicatorReadingsView | redesign 4-4 | `monitoring_views.py:260` + URL 등록 + FMP 히스토리 fallback (5Y) | (A) 완전·확장 |
| 데이터 마이그레이션 (display_unit populate) | redesign 4-7 | `migrations/0005_populate_display_unit.py` | (A) 완전 |
| 타입 확장 (DashboardIndicator + NotableChange + IndicatorReadingPoint + ChartPeriod) | redesign 5-1 | `lib/thesis/types.ts:115-363` | (A) 완전 |
| `thesisApi.indicatorReadings` | redesign 5-2 | `lib/thesis/api.ts` (확인 필요하나 `useIndicatorReadings`/`useAllIndicatorReadings` 훅 사용 중) | (A) 완전 |
| QUERY_KEYS.readings + `useAllIndicatorReadings`/`useIndicatorReadings` | redesign 5-3, 6-4 | `lib/thesis/queries.ts:13-107` | (A) 완전 |
| `formatRawValue` / `formatChangePct` / `supportLabel` 유틸 | redesign 5-4 | `lib/thesis/utils.ts` (전부 사용 중) | (A) 완전 |
| Mock readings + dashboard 확장 | redesign 5-5, 6-6 | `lib/thesis/mock.ts` (698줄, MOCK_READINGS 포함) | (A) 완전 |
| RealValueIndicatorCard | redesign 5-6 | `components/thesis/dashboard/RealValueIndicatorCard.tsx` (**현재 페이지에서는 IndicatorRow가 사용됨**, RealValueIndicatorCard는 코드만 잔존) | (B) 코드 존재·미사용 |
| AISummarySection | redesign 5-7 | `components/thesis/dashboard/AISummarySection.tsx` + page에서 호출 — **단, 백엔드 `ai_summary`는 빈 문자열 → 항상 미렌더링** | (B) UI 완성·데이터 없음 |
| NotableChangesSection | redesign 5-8 | `components/thesis/dashboard/NotableChangesSection.tsx` + page에서 호출 — **단, snapshot의 notable_changes 스키마가 redesign과 다름**: 실제는 `{indicator_id, indicator_name, prev_score, curr_score, delta}`, 프론트는 `{description, severity, change_type}` 기대. → 이름만 노출되고 description/severity 빈 상태 | (B) 스키마 불일치 |
| `OverallMoon` 삭제 / `DashboardIndicatorCard` 교체 / `RecentChange` 교체 | redesign 5-9, 6-8 | OverallMoon/DashboardIndicatorCard/RecentChange는 **현재 dashboard 폴더에 없음** (정상 삭제됨). MoonPhase는 common에 잔존 (목록/카드용) | (A) 완전 |
| ChartToggleButton + PeriodSelector | redesign 6-1, 6-2 | `components/thesis/dashboard/ChartToggleButton.tsx` (23줄) + `PeriodSelector.tsx` (29줄) — **현재 page.tsx에서는 import 안 함**: IndicatorRow가 행별로 자체 차트를 토글로 펼침 | (B) 코드 존재·미사용 |
| IndividualMiniCharts | redesign 6-5 | `components/thesis/dashboard/IndividualMiniCharts.tsx` (104줄) — **page.tsx에서 미사용** (IndicatorRow 내부 AreaChart로 대체) | (B) 코드 존재·미사용 |
| CHART_COLORS / PERIOD_OPTIONS 상수 | redesign 6-3 | `lib/thesis/constants.ts` | (A) 완전 |
| 미사용 컴포넌트 정리 (OverallMoon/DashboardIndicatorCard/RecentChange 삭제) | redesign 6-8 | 삭제 완료 (현재 폴더에 없음) | (A) 완전 |
| **PR-10 — `generate_thesis_summaries` Celery + LLM 요약 파이프라인** | redesign 7-1 | **미구현** — `thesis/tasks/`에 파일 없음, Beat 등록 없음 | (C) 미구현 |
| **PR-10 — `notable_changes` 알림 이벤트 변환 (snapshot_builder 내) ** | redesign 7-2 | 일부 구현되었으나 **스키마 다름** (alert_engine 이벤트 재활용이 아니라 score delta ≥ 0.3 자체 로직, severity/description/change_type/raw_value 변환 미실행) | (B) 부분·스키마 불일치 |

### 빌더 재설계 (Talking Builder v4 / Phase A LLM)

| 항목 | 설계 문서 | 현재 구현 | 상태 |
|------|----------|----------|------|
| LLM one-shot proposal (Gemini 1회) | `talking_builder/redesign_build_plan/01_phase_a_mvp.md` | `services/thesis_builder.py:start_llm_conversation/process_llm_turn/_handle_proposal` + `prompt_builder.py` + Suggestion API | (A) 완전 |
| BuilderPhase 상태 모델 + 프리셋 | Phase A | `services/builder_state.py` + 프론트 `lib/thesis/types.ts:BuilderPhase` | (A) 완전 |
| INDICATOR_CATALOG PK 매칭 + 키워드 룰 fallback | Phase A | `services/prompt_builder.py` + `services/indicator_matcher.py:match_indicators_for_llm` | (A) 완전 |
| normalize → validate → merge | Phase A | `services/llm_postprocess.py` | (A) 완전 |
| feature flag + wizard fallback | Phase A | `feature_flags.py` (10개) + `_handle_fallback_choice` | (A) 완전 |
| 이벤트 로그 7종 | Phase A | `services/builder_events.py` + `HypothesisEvent.objects.create` 호출부 | (A) 완전 |
| `builder_stats` management command | Phase A Hardening | `thesis/management/commands/` 디렉터리 존재 | (A) 완전 (보고서 §6) |
| KeywordCache + Hint enrichment (Phase B) | `redesign_build_plan/03_phase_b_keywords.md` | `services/keyword_cache.py`, `keyword_collectors/`, `keyword_hint.py` 존재 — 동작 검증은 별도 필요 | (A→B) 거의 완전 |
| 멀티턴 수정 대화 (Phase B) | Phase B | history 필드 존재 + `process_llm_turn` 분기 — 깊이 있는 대화 검증은 별도 | (B) 부분 |
| Daily Health Report / batch versioning (Phase B 후반) | Phase B | **미구현** | (C) 미구현 |
| MiniDashboardPreview / 스트리밍 / Guided Suggestion (Phase C) | Phase C | **미구현** | (C) 미구현 |

---

## Phase 3 미구현 항목 상세

### 원안 Phase 3 (FE-PR-7~11) — **공식 폐기**

근거: `thesis_control_phase3_frontend_redesign.md` §0.1에서 "Phase 2까지 구현된 대시보드가 달 위상(MoonPhase), 화살표 각도(0-180°), 내부 점수(-1~1) 같은 추상적 시각화에 의존하고 있다"는 이유로 원안을 폐기하고 **실제 값(환율/지수/금리)** 중심 리디자인으로 전환. `Phase2_completion_summary.md` §8의 FE-PR-7~11 표는 historical artifact로만 남음.

| FE-PR | 폐기 사유 | 대체 동향 |
|-------|---------|---------|
| FE-PR-7 (3탭 구조 + 전제 CRUD) | 단일 페이지 + IndicatorRow expandable로 깊이 흡수 | IndicatorRow가 클릭 시 차트/설명/관계성 펼침 |
| FE-PR-8 (히트맵 + weight 편집) | "내부 점수 숨기기" 원칙 충돌, 1인 개발자 유지보수 부담 | 미실행 (heatmap 응답 jsonField는 백엔드에 잔존) |
| FE-PR-9 (히스토리 탭) | 스냅샷 시계열보다 raw value 시계열이 사용자에게 직관적 | IndicatorRow의 1M/1Y/3Y/5Y 차트로 대체 |
| FE-PR-10 (아카이브 + ValidityMatrix) | 우선순위 하향 — `ValidityRecord` 적재만 유지 | `views/thesis_views.py:close()`에서 자동 적재 (UI 없음) |
| FE-PR-11 (DNA 프로필) | 우선순위 하향 — `InvestorDNA` 적재만 유지 | `_update_investor_dna()` 호출 (조회 API/UI 없음) |

### Phase 3 리디자인 — 미완 항목

#### 1. **PR-10: `generate_thesis_summaries` Celery 태스크 (Critical)**

- 설계 위치: `thesis_control_phase3_frontend_redesign.md` §7-1 + `thesis_control_design.md` §5.3
- 현재 상태:
  - `ThesisSnapshot.ai_summary` 모델 필드 존재 (`models/monitoring.py:26`)
  - `DashboardView`가 `latest_snapshot.ai_summary if latest_snapshot else ''` 반환 (`monitoring_views.py:216`)
  - 프론트 `AISummarySection`은 `if (!summary) return null`로 빈 문자열에 대해 미렌더링
  - **빈 문자열을 채워줄 Celery 태스크가 존재하지 않음** → 사용자에게 AI 분석이 한 번도 노출되지 않는 상태
- 영향 범위: 대시보드 진입 시 가설 해석 텍스트가 항상 빈 상태. `PROGRESS.md` "audit P0 #15"와 동일.
- 누락 산출물:
  - `thesis/tasks/generate_summaries.py` (또는 `eod_pipeline.py`에 추가 함수)
  - Celery Beat 등록 (`07:30` 권장)
  - LLM 프롬프트 (Gemini 2.5 Flash, 변화 있는 가설만)

#### 2. **PR-10: `notable_changes` 스키마 정합성 (High)**

- 설계 위치: redesign §7-2
- 설계가 요구한 스키마 (`NotableChange` 인터페이스, `types.ts:334-343`):
  ```ts
  { indicator_id, indicator_name, change_type, description,
    raw_value_before, raw_value_after, change_pct, severity }
  ```
- 실제 백엔드가 채우는 스키마 (`snapshot_builder.py:116`):
  ```python
  { 'indicator_id', 'indicator_name', 'prev_score', 'curr_score', 'delta' }
  ```
- 결과:
  - `NotableChangesSection`이 `c.indicator_name`은 표시하나, `c.description`은 `undefined`로 빈 줄, `c.severity === 'warning'`은 항상 false → 항상 회색 Info 아이콘
  - 설계 의도(alert_engine 이벤트 재활용 + raw_value 기반 변동률 노출)가 손실됨
- 권장: `snapshot_builder.py`의 `notable_changes` 생성 로직을 `alert_engine`이 만든 그날의 alert 이벤트(`direction_flip`/`sharp_move`/`extreme_volatility`)를 stringify 하도록 변경하거나, 프론트가 score delta UI에 맞춰 재해석.

#### 3. **사용되지 않는 컴포넌트 잔존 (Medium)**

리디자인 PR-8/9에서 만든 컴포넌트가 **현재 페이지에서 import되지 않음**. `app/thesis/[thesisId]/page.tsx`는 `IndicatorRow`(설계서에 없는 분기 지표 작업의 산출물)로 통합 렌더링.

| 파일 | 상태 |
|------|------|
| `components/thesis/dashboard/RealValueIndicatorCard.tsx` (90줄) | 코드 존재·페이지 미사용 |
| `components/thesis/dashboard/ChartToggleButton.tsx` (23줄) | 코드 존재·페이지 미사용 |
| `components/thesis/dashboard/PeriodSelector.tsx` (29줄) | 코드 존재·페이지 미사용 |
| `components/thesis/dashboard/IndividualMiniCharts.tsx` (104줄) | 코드 존재·페이지 미사용 |

→ 폐기 결정 후 **삭제하거나**, 별도 뷰(예: 카드 그리드 모드)로 다시 노출해야 일관성 회복. 현재는 dead code 위험.

#### 4. **누락된 Phase 2 항목 (Phase 3 리디자인이 점프해서 가린 부분)**

- **히트맵/그래프뷰**: `DashboardView`가 `heatmap.cells` 응답을 만들지만 프론트가 무시. UI 시안과 데이터 모두 존재하나 시각화 컴포넌트만 없음.
- **[근거] BottomSheet**: `BottomSheet` 컴포넌트는 빌더에서 사용 중이나, 지표 [근거] 설명 인터랙션은 미연결. 현재는 설명 텍스트(`description`/`recommendation_reason`)가 IndicatorRow 펼침 영역에 인라인 표시.
- **AI 일일 요약 캐싱**: design 5.5에서 LLM 캐싱 전략 명시. 캐싱 인프라(Redis 키 설계 등) 미구현.
- **뉴스 센티먼트 지표 데이터 연동**: `_fetch_news_sentiment_value` fetcher는 존재하지만, 뉴스 인텔리전스 v3와의 깊은 통합(`narrative_momentum`)은 미구현.
- **DNA 슬라이더 / 역제안 / support_direction 확인 UX**: 모델 필드(`personalization_weight`)와 이벤트 로깅은 있으나, 추천 블렌딩 로직과 UI 슬라이더 모두 없음.

#### 5. **누락된 커뮤니티 (design Phase 3 — guide Week 13~14)**

- **인기 가설 시스템**: `PopularThesisCache` 모델만 존재, `update_popular_thesis_cache` Celery + `/popular/` API + 인기 카드 UI 모두 없음.
- **가설 따라하기/수정**: `Thesis.copied_from`/`ThesisFollow` 모델 존재, API/UI 없음.
- **템플릿 시스템**: 이벤트형/추세형/비교형/괴리형 — `thesis_type` 필드 존재, 템플릿 API/UI 없음. 빌더 진입 5경로 중 경로 4(템플릿)/경로 5(Chain Sight) 미연결.
- **Chain Sight 양방향 진입**: 빌더 페이지에서 `entry=chainsight` 진입은 화이트리스트에 있으나, Chain Sight 화면 측 "📌 가설 세우기" 버튼은 미확인 (별도 감사 필요).

#### 6. **누락된 학습/지능화 (guide Phase 3 Week 15~20 + Phase 4)**

- **Synthetic Bootstrapper / 합성 가설 페르소나**: 미구현
- **Online Logistic Regression (`ThesisWeightLearner`)**: 미구현
- **ValidityScore 주간 집계 Celery**: ValidityRecord 적재까지만, 점수 집계 없음
- **Neo4j 가설 관계 그래프 (SIMILAR_TO/OPPOSITE_OF)**: 미구현
- **벡터 스코어링 (DNA 16차원, Validity 6차원)**: 미구현
- **Change Point Detection / 칼만 필터**: 미구현 (Phase 4)

---

## 핵심 위험 요약

| # | 항목 | 영향 | 우선순위 |
|---|------|------|---------|
| 1 | `generate_thesis_summaries` Celery 미구현 | AI 분석 섹션이 영구 빈 상태 | P0 (PROGRESS audit #15) |
| 2 | `notable_changes` 스키마 BE/FE 불일치 | 오늘의 변화 카드에 설명·severity 누락 | P1 |
| 3 | 미사용 dashboard 컴포넌트 4종 (RealValueIndicatorCard 등) | dead code, 유지보수 혼란 | P2 |
| 4 | 히트맵 응답이 무시되는 dead path | 백엔드 부담 + UI 미노출 | P2 |
| 5 | 인기 가설/템플릿 모델·진입 경로 미연결 | 빌더 5경로 중 3개(popular/template/chainsight) 미작동 | P2 |
| 6 | DNA/ValidityScore 적재만 되고 활용 없음 | 학습 루프 단절 (Phase 2~4 차단) | P3 |

---

## 부록: 폴더 구조 비교

```
설계 문서 트리 (docs/thesis_control/)
├── plan/
│   ├── thesis_control_design.md         ← What (UX/API/모델)
│   ├── thesis_control_implementation_guide.md  ← When (Phase 로드맵)
│   ├── thesis_control_math_model_final.md      ← How (수학 엔진)
│   ├── thesis_control_phase3_frontend_redesign.md ← Phase 3 리디자인
│   ├── thesis_control_integrated_roadmap.md
│   └── talking_builder/                  ← LLM 빌더 재설계 (v4)
├── frontend/task_done/
│   ├── FE-PR-1~6 (Phase 1~2 완료 보고서 6종)
│   ├── FE-PR-3_plan_review_v3.md
│   └── Phase2_completion_summary.md      ← 원안 FE-PR-7~11 표 (폐기)
├── work_done/phase_a_llm_builder.md      ← LLM 빌더 완료
└── thesis_control_user_experience.md     ← 사용자 시나리오

실제 구현 트리
├── thesis/                               ← 백엔드
│   ├── models/         (thesis/indicator/monitoring/community/learning/keyword) ✓
│   ├── views/          (thesis_views/conversation_views/monitoring_views) ✓
│   ├── serializers/    (thesis/indicator/conversation/monitoring) ✓
│   ├── services/       (15개 모듈, 수학 엔진 + LLM 빌더 + KeywordCache 모두 구현)
│   ├── tasks/eod_pipeline.py  ← 3개 EOD 태스크만, generate_summaries 누락
│   └── feature_flags.py
└── frontend/
    ├── app/thesis/
    │   ├── (list)/{page,alerts/page}
    │   ├── new/page.tsx (1072줄)
    │   └── [thesisId]/{page,indicators/page,close/page}
    └── components/thesis/
        ├── common/      (6개)
        ├── builder/     (9개)
        ├── list/        (3개)
        ├── dashboard/   (10개 — RealValueIndicatorCard 등 4개 미사용)
        ├── indicators/  (3개)
        ├── alerts/      (3개)
        ├── close/       (2개)
        └── skeleton/    (1개)
```

**Phase 3 원안의 "탭 구조 / 히트맵 / 히스토리 / 아카이브 / DNA" 5종은 frontend에 단 한 컴포넌트도 존재하지 않음.** Profile 라우트(`app/thesis/profile`)도 부재.
