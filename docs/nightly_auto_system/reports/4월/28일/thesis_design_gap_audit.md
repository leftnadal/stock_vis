# Thesis Control 설계 갭 감사

> 감사일: 2026-04-29
> 감사 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드)
> 모드: 읽기 전용
> 비고: 감사 후반에 macOS TCC 권한 문제로 일부 task_done 보고서(`FE-PR-2 ~ FE-PR-6`, `phase_a_llm_builder.md` 등)는 직접 열람하지 못했음. 디렉터리 목록과 메모리 상의 정보, Phase2_completion_summary.md의 cross-reference로 보강.

---

## 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 분류 |
|-------|------|--------|------|
| Phase 1 (MVP) | 백엔드 모델/관제엔진/기본 API | **100%** | (A) 완전 구현 |
| Phase 1 (MVP) | 이벤트 수집 (HypothesisEvent) | **100%** | (A) 완전 구현 |
| Phase 1 (MVP) | ValidityRecord / InvestorDNA 골격 | **100%** | (A) 완전 구현 |
| Phase 1 (MVP) | 5개 진입경로 (news/free/popular/template/chainsight) | **40%** (news, free_input, suggest 위주) | (B) 부분 구현 |
| Phase 2 (모니터링 강화) | 카드뷰 / 알림 / 마감 / 지표 설정 / 빌더 | **100%** | (A) 완전 구현 |
| Phase 2 (모니터링 강화) | 히트맵 API | 50% (응답에는 cells 포함, FE 미렌더) | (B) 부분 구현 |
| Phase 2 (모니터링 강화) | 그래프 뷰 (시계열) | IndicatorRow 안에 흡수 | (D) 폐기/대체 |
| Phase 3 (대시보드 리디자인) | PR-7 백엔드 (display_unit, raw_value) | **100%** | (A) 완전 구현 |
| Phase 3 (대시보드 리디자인) | PR-8 카드 + AI 분석 | **80%** (IndicatorRow가 카드 흡수) | (B) 부분 구현 |
| Phase 3 (대시보드 리디자인) | PR-9 차트 + 정리 | **60%** (컴포넌트 존재, page에 직접 미사용) | (B) 부분 구현 |
| Phase 3 (대시보드 리디자인) | PR-10 AI 모니터링 파이프라인 | **0%** | (C) 미구현 |
| Phase 3 (Phase2_summary 안의 FE-PR-7~11) | 탭 구조 / 히트맵 / 히스토리 / 마감 아카이브 / DNA 프로필 | **0%** | (D) 폐기/대체 — Phase3 redesign 계획서로 대체된 것으로 추정 |
| Phase 3 (커뮤니티) | ThesisFollow / PopularThesisCache 모델 | **100%** (모델만, 노출 API/뷰 없음) | (B) 부분 구현 |
| Phase 4 (지능화) | 합성 에이전트 / 벡터화 / 사용자 유사도 | **0%** | (C) 미구현 |

**전체 평가**: Phase 1·2 핵심 루프는 안정적으로 완료. Phase 3는 두 가지 계획서가 충돌하는데(요약 보고서의 탭 구조 vs `phase3_frontend_redesign.md` 실제값 카드), 코드 상태는 후자(redesign)를 부분 채택한 형태이며, AI 파이프라인(PR-10)은 아직 시작되지 않았음.

---

## 문서별 상태 테이블

### A. 백엔드 모델 (`thesis_control_design.md` §4 vs `thesis/models/`)

| 설계 모델/필드 | 구현 위치 | 분류 | 비고 |
|---|---|---|---|
| `Thesis` (전체 필드) | `thesis/models/thesis.py` | (A) | `status` choices가 설계의 `setting_up/active/paused/closed_correct/closed_incorrect/closed_neutral` → 구현은 `setting_up/active/paused/closed` + 별도 `outcome`(correct/incorrect/neutral)로 분리. 의미 동일하나 이름 변경. (D) 부분 |
| `Thesis.thesis_type` (event/trend/comparison/divergence/custom) | 동일 | (A) | |
| `Thesis.entry_source` 5개 | 동일 | (A) | |
| `Thesis.overall_score`/`overall_label` | `current_score` + `current_state` (state machine 8종)으로 확장 | (D) | 설계보다 풍부. v2.3.2 수학모델 반영. |
| `Thesis.alert_preference` | **없음** | (C) | 알림 환경설정(daily/on_change/weekly/off) 미구현 |
| `Thesis.tags`, `Thesis.category` | **없음** | (C) | |
| `Thesis.premise_universe_ids`, `indicator_universe_ids` | 추가됨 | — | 설계에 없는 v2.3.2 추가 필드 (snapshot universe 고정용) |
| `ThesisPremise.extraction_level` (explicit/implicit/ai_suggested) | **없음** (대신 `category` choices) | (D) | 설계의 추출원 추적이 카테고리 분류로 대체됨 |
| `ThesisPremise.current_score`/`current_label`/`explanation` | **없음** | (C) | 전제 단위 모니터링 결과/설명 필드 부재. snapshot의 `premise_scores` JSON으로 우회. |
| `ThesisPremise.weight`, `is_paused` | 추가됨 | — | v2.3.2 추가 |
| `ThesisIndicator` (전체) | `thesis/models/indicator.py` | (A) | |
| `ThesisIndicator.current_arrow_degree` | `current_degree` | (A) | 이름만 다름 |
| `ThesisIndicator.rationale` / `context_explanation` | `recommendation_reason` (단일 필드) | (B) | 설계의 두 필드를 한 필드로 통합. migration 0009로 추가. |
| `ThesisIndicator.is_ai_recommended`, `order` | **없음** | (C) | 일부 누락 (`weight` 보존, `order` 미사용) |
| `ThesisIndicator.display_unit`, v2.3.2 필드들 | 추가됨 (epsilon/window/decay/min/max_valid_value/max_change_pct/allow_extreme_jump/is_paused/override_score) | — | Phase 3 PR-7 + 수학모델 반영 |
| `IndicatorReading` | 동일 | (A) | `validation_status` choices 8종 추가. `value`/`raw_value` 분리 (v2.3.2). |
| `ThesisSnapshot` | `thesis/models/monitoring.py` | (A) | `asof_date`, `data_coverage`, `universe_snapshot`, `ordered_indicator_ids`, `notable_changes`, `ai_summary` 모두 존재 |
| `ThesisAlert` | 동일, alert_type 11종(설계 5종 → 확장) | (A++) | `target_id`, `cooldown_hours` (v2.3.2 throttling) 추가 |
| `ThesisFollow`, `PopularThesisCache` | `thesis/models/community.py` | (A) | 모델만 존재, 사용처 없음 |
| `HypothesisEvent` (`integrated_roadmap.md` §1.2) | `thesis/models/learning.py` | (A) | 13개 event_type 모두 구현, 인덱스 3개 |
| `ValidityRecord` (§1.3) | 동일 | (A) | 2x2 매트릭스 score (`+0.3/-0.2/-0.15/+0.05`) `_compute_validity_score`에서 즉시 결정 |
| `InvestorDNA` (§1.4) | 동일 | (A) | 마감 시 `_update_investor_dna`로 자동 갱신. property: `accuracy_rate`, `ai_accept_rate`, `top_down_ratio` 모두 구현 |
| `Neo4j` 가설 그래프 (§4.4) | **없음** | (C) | thesis 앱에는 Neo4j 연동 코드 없음 |

### B. 백엔드 서비스/태스크 (`design.md` §5 vs `thesis/services/`, `thesis/tasks/`)

| 설계 서비스 | 구현 | 분류 | 비고 |
|---|---|---|---|
| `thesis_builder.py` (가설 구조화) | 동일 | (A) | wizard 모드 + LLM 모드(phase A) |
| `indicator_matcher.py` | 동일 | (A) | `match_indicators_for_premise`, `match_indicators_for_llm` |
| `arrow_calculator.py` | 동일 | (A) | |
| `monitoring_engine.py` | **이름 다름** → `snapshot_builder.py`, `data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `thesis_state_machine.py`, `alert_engine.py`로 분리 | (A) | 설계보다 모듈화 깊음 (수학모델 v2.3.2 Stage 0~3 반영) |
| `news_connector.py` (뉴스→가설) | **부재** (대신 `keyword_collectors/news.py`, conversation_views의 NewsIssuesView) | (B) | 뉴스 진입점 일부만 구현, 가설 활성화 후 자동 뉴스 매칭은 미구현 |
| `summary_generator.py` (LLM 일일요약) | **부재** | (C) | Phase 3 PR-10에 해당. ai_summary 필드는 비어 있음. |
| `tasks/daily_monitoring.py` | `tasks/eod_pipeline.py` | (A) | 통합형 |
| `tasks/alert_check.py` | `tasks/eod_pipeline.py`에 통합 (snapshot+alert 동시) | (A) | |
| `tasks/news_scan.py` | **부재** | (C) | 2시간마다 가설관련 뉴스 스캔 미구현 |
| Celery 태스크 8종 (design §5.3) — `update_indicator_readings`, `calculate_arrow_degrees`, `create_daily_snapshots`, `check_thesis_alerts`, `scan_thesis_news`, `update_popular_thesis_cache`, `prepare_daily_issues`, `generate_thesis_summaries` | EOD 파이프라인 1개로 통합되어 첫 4개 처리. 나머지 4개 미구현 | (B) | 인기캐시 갱신/오늘이슈 준비/AI요약 생성/뉴스 스캔 미구현 |

추가로 설계에 없는 서비스:
- `quarterly_metric_fetcher.py` — 분기 지표 fetch (FE 분기 차트 지원)
- `keyword_cache.py`, `keyword_hint.py`, `keyword_collectors/` — 키워드 캐시 시스템
- `builder_state.py`, `builder_events.py` — wizard/LLM 상태/이벤트 추적
- `llm_postprocess.py`, `prompt_builder.py` — LLM 응답 후처리 + 지표설명 캐시 (`get_indicator_description`)
- `feature_flags.py` — feature flag 시스템

### C. 백엔드 API (`design.md` §6 vs `thesis/urls.py`, `thesis/views/`)

| 설계 엔드포인트 | 구현 | 분류 |
|---|---|---|
| `POST/GET/GET/PATCH /` (가설 CRUD) | `ThesisViewSet` | (A) |
| `POST /{id}/close/` | `@action close` | (A) |
| `POST /conversation/start/` | `ConversationStartView` | (A) |
| `POST /conversation/respond/` | `ConversationRespondView` | (A) |
| `GET/POST/PATCH/DELETE /{id}/premises/` | `ThesisPremiseViewSet` | (A) |
| `GET/POST/PATCH/DELETE /{id}/indicators/` | `ThesisIndicatorViewSet` | (A) |
| `POST /{id}/indicators/auto/` | `@action auto` | (A) |
| `GET /{id}/dashboard/` | `DashboardView` | (A) |
| `GET /{id}/snapshots/` | **부재** | (C) — 그래프뷰/히스토리용 미구현 |
| `GET /{id}/summary/` (쉐이크) | **부재** | (C) |
| `GET /{id}/indicators/{iid}/readings/` | `IndicatorReadingsView` | (A) — Phase 3 PR-7 |
| `GET /{id}/indicators/{iid}/explanation/` ([근거]) | **부재** (대신 `recommendation_reason`을 dashboard 응답에 포함) | (D) |
| `GET /alerts/`, `PATCH /alerts/{aid}/read/` | `AlertListView`, `AlertReadView` | (A) |
| `GET /daily-issues/` | `NewsIssuesView` (`/conversation/news-issues/` 경로) | (B) — URL 경로 다름 |
| `GET /popular/`, `POST /popular/{id}/follow/`, `GET /popular/{id}/detail/` | **부재** | (C) — 인기 가설 시스템 미노출 |
| `GET /templates/`, `GET /templates/{type}/` | **부재** (대화 흐름에 흡수된 듯) | (C) |
| `POST /conversation/suggest/` (설계 외 추가) | `SuggestThesesView` | — | LLM이 가설 후보 제안 |

### D. Phase 3 대시보드 리디자인 (`thesis_control_phase3_frontend_redesign.md`)

#### PR-7 (백엔드 확장)
| 항목 | 구현 | 분류 |
|---|---|---|
| `ThesisIndicator.display_unit` | migration 0004 + 모델 필드 | (A) |
| 데이터 마이그레이션 (`_infer_unit` 일괄 채움) | migration 0005 | (A) |
| `DashboardView`에 raw_value/previous/change_pct/raw_value_unit 필드 | `monitoring_views.py:94-112, 161-165` | (A) |
| thesis 응답에 ai_summary, notable_changes | 동일, `:216-218` | (A) |
| `IndicatorReadingsView` | 동일, `:260-290` | (A) |
| `_infer_unit()` fallback | 동일, `:346-364` | (A) |
| URL 등록 | `urls.py:30-34` | (A) |

추가로 설계에 없는 부분:
- `_prefetch_quarterly_data` — metrics 소스 분기 데이터 batch 조회 (분기 지표 대시보드 plan에서 유래)
- 분기 지표 확장 필드 (fiscal_label, quarterly_history, is_quarterly, comparison_type)
- `description`, `recommendation_reason` 응답 포함
- FMP 히스토리 fallback (DB readings 부족 시)
- IndicatorReadingsView `days` 상한 90 → 1825(5Y) 확장

#### PR-8 (실제 값 카드 + AI 분석)
| 컴포넌트 | 위치 | 분류 |
|---|---|---|
| `RealValueIndicatorCard.tsx` | `frontend/components/thesis/dashboard/` | (B) — 파일은 존재하나 page.tsx에서는 `IndicatorRow`가 사용됨 |
| `AISummarySection.tsx` | 동일 | (A) — page.tsx에서 사용 중 |
| `NotableChangesSection.tsx` | 동일 | (A) — page.tsx에서 사용 중 |
| `formatRawValue`, `formatChangePct`, `supportLabel` (utils) | `frontend/lib/thesis/utils.ts` (Read 미실행, IndicatorRow에서 import 확인) | (A) |
| Mock 데이터 확장 | `mock.ts` (Read 미실행) | 추정 (A) |

#### PR-9 (미니차트 + 기간 선택 + 정리)
| 항목 | 위치 | 분류 |
|---|---|---|
| `ChartToggleButton.tsx` | `dashboard/` | (B) — 파일 존재, page.tsx에서 사용 안 함 |
| `PeriodSelector.tsx` | 동일 | (B) — 파일 존재, page.tsx에서 사용 안 함 |
| `IndividualMiniCharts.tsx` | 동일 | (B) — 파일 존재, page.tsx에서 사용 안 함 |
| `useAllIndicatorReadings()` 훅 (병렬 fetch) | `queries.ts` | 추정 — IndicatorRow는 `useIndicatorReadings` (단일) 사용 |
| `OverallMoon.tsx` 삭제 | **현재 디렉터리 미존재** ✅ | (A) — 삭제 완료 |
| `DashboardIndicatorCard.tsx` 삭제 | **현재 디렉터리 미존재** ✅ | (A) |
| `RecentChange.tsx` 삭제 | **현재 디렉터리 미존재** ✅ | (A) |
| `MoonPhase.tsx` (common) | 존재 (`common/MoonPhase.tsx`) | (D) — 다른 곳 import 잔존 가능성 (확인 필요) |

**Phase 3 대시보드 실제 상태**: page.tsx는 `RealValueIndicatorCard` 대신 `IndicatorRow`를 사용. `IndicatorRow`는 RealValueIndicatorCard(메인 카드) + ChartToggleButton(클릭 토글) + PeriodSelector(7D/14D/30D 대신 1M/1Y/3Y/5Y) + IndividualMiniCharts(per-row area chart)를 한 컴포넌트로 통합한 디자인. 즉 PR-8/PR-9가 별도 컴포넌트 분리 없이 한 행으로 합쳐진 변형 구현.

→ **분류 (D) 폐기/대체**: 분리된 ChartToggleButton/PeriodSelector/IndividualMiniCharts/RealValueIndicatorCard는 작성됐지만 실제 dashboard page에서는 IndicatorRow 단일 컴포넌트로 통합되어 사용됨. 이 분리 컴포넌트들은 dead code 가능성 — 다른 곳 사용처 확인 필요.

#### PR-10 (AI 모니터링 파이프라인)
| 항목 | 분류 |
|---|---|
| `generate_thesis_summaries` Celery task | (C) — `thesis/tasks/`에 `eod_pipeline.py`만 존재. AI 요약 생성 미구현. |
| `notable_changes`를 `alert_engine` 이벤트 기반으로 변환 | (B/C) — `snapshot_builder.py` 존재. ThesisSnapshot.notable_changes JSONField는 있지만 실제 채워지는지/내용 형식 일치 여부는 코드 추가 확인 필요. dashboard 응답이 `(latest_snapshot.notable_changes or [])[:5]`를 그대로 통과시키므로 골격은 됨. |

### E. 프론트엔드 라우팅 + 컴포넌트 (`Phase2_completion_summary.md` 기준)

| 라우트 | 페이지 | 분류 |
|---|---|---|
| `/thesis` (목록, route group `(list)`) | `app/thesis/(list)/page.tsx` | (A) |
| `/thesis/new?entry={source}` (빌더) | `app/thesis/new/page.tsx` | (A) |
| `/thesis/alerts` | `app/thesis/(list)/alerts/` | (A) |
| `/thesis/[thesisId]` (관제실) | `app/thesis/[thesisId]/page.tsx` | (A) |
| `/thesis/[thesisId]/indicators` (지표 설정) | `app/thesis/[thesisId]/indicators/` | (A) |
| `/thesis/[thesisId]/close` (마감) | `app/thesis/[thesisId]/close/` | (A) |

| 컴포넌트 그룹 (Phase 2 30개) | 현재 카운트 | 분류 |
|---|---|---|
| `common/` 5개 | 6개 (AlertBell, ArrowIndicator, BottomSheet, IndicatorCard, MoonPhase, ThesisBadge) | (A+) |
| `dashboard/` 5개 | 10개 (Phase 3 추가 컴포넌트들 포함) | (A+) |
| `list/` 3개 | 3개 | (A) |
| `indicators/` 3개 | 3개 | (A) |
| `alerts/` 3개 | 3개 | (A) |
| `close/` 2개 | 2개 | (A) |
| `builder/` 7개 | 9개 (BottomSheet, ChatBubble, MultiSelectFooter, NewsSelector, OptionButton, PremiseCard, ProgressBar, SuggestionCard, TextInput) | (A+) |
| `skeleton/` 2개 | 1개 (ThesisSkeleton 단일) | (B) |
| 루트 잡동사니 (AddIndicatorSheet, IndicatorCard, PresetSelector) | 3개 | — | indicators/, common/과 중복 가능 (정리 필요) |

### F. UX/사용자 흐름 (`design.md` §2-3)

| 설계 항목 | 구현 | 분류 |
|---|---|---|
| 진입경로 5종 (news, free_input, popular, template, chainsight) | wizard에서 기본 흐름은 모두 받음, 그러나 popular/template UI 진입점 미노출 | (B) |
| `EntryPointGrid`: 뉴스/자유입력 2개 | Phase2_summary에 명시: 진입점 2개만 노출 | (B) |
| 롱프레스 용어 설명 | 빌더에 `BottomSheet` + long-press explanation 구현 (Phase2_summary §5) | (A) |
| 카드뷰/히트맵/그래프 3뷰 | 카드뷰만(IndicatorRow), 히트맵 API 응답에 `cells` 필드 있으나 FE 미렌더, 그래프 뷰는 IndicatorRow 안에 흡수 | (B/D) |
| Moon Phase 메타포 (전체 흐름) | OverallMoon 컴포넌트 제거됨 (Phase 3 redesign로 대체) | (D) |
| 화살표 시스템 (5단계 각도) | `arrow_calculator` 백엔드 + `ArrowIndicator` 컴포넌트 존재. dashboard에서는 `support.colorClass`(파/빨/회) dot으로 단순화 | (B) |
| 변화 감지 알림 (푸시) | `ThesisAlert` 모델 + AlertList API + AlertCard. 실제 푸시 인프라(웹/앱)는 미확인 | (B) |
| 가설 마감 복기 화면 | `OutcomeSelector`, `CloseConfirmDialog`만. "가장 유용했던 지표 / 예상과 달랐던 부분" 같은 정성 회고 화면은 미구현 | (B) |

---

## Phase 3 미구현 항목 상세

### 1. PR-10 AI 모니터링 파이프라인 — (C) 미구현

**설계 (`phase3_frontend_redesign.md` §7)**:
- Celery task `generate_thesis_summaries` (매일 07:30) — Gemini로 ai_summary 생성
- 변화 있는 가설만 LLM 호출 (비용 절감)
- alert_engine 이벤트(direction_flip/sharp_move/extreme_volatility)를 NotableChange 포맷으로 변환

**현재 상태**:
- `thesis/tasks/`에는 `eod_pipeline.py` 하나만. summary 생성 task 없음.
- `ThesisSnapshot.ai_summary` 필드는 빈 문자열, `notable_changes`는 빈 리스트일 가능성 높음 (코드 추적 필요)
- DashboardView가 빈 ai_summary면 AISummarySection이 컴포넌트 자체를 렌더링 안 하도록 가드되어 있어 사용자에게는 보이지 않음 → 기능적으로는 비활성

**영향**: AI 분석 카드와 오늘의 변화 카드가 mock에서만 채워지고 운영 환경에서는 항상 비어 있음.

### 2. 그래프뷰 / 스냅샷 히스토리 / 요약 API — (C) 미구현

**설계 (§3.4, §6.1)**:
- `GET /{id}/snapshots/` — 그래프뷰용 시계열
- `GET /{id}/summary/` — 쉐이크 시 AI 요약 즉시 반환
- 세 가지 뷰 (카드/히트맵/그래프) 탭 전환

**현재 상태**:
- snapshots 엔드포인트 없음. ThesisSnapshot은 EOD 파이프라인에서 매일 생성되지만 외부 노출 없음.
- summary 엔드포인트 없음. dashboard 응답의 `ai_summary`로 정적 노출.
- 뷰 전환 UI 없음. 카드뷰만.

### 3. 진입경로 3종 (popular / template / chainsight) — (B) 부분 구현

**설계 (§2.3)**:
- 인기 가설 시스템 (PopularThesisCache + follow API)
- 템플릿 시스템 (event/trend/comparison/divergence 4가지 유형)
- Chain Sight에서 직접 진입

**현재 상태**:
- `PopularThesisCache`, `ThesisFollow` 모델은 존재하나 갱신 task와 노출 API 없음
- 템플릿 API/뷰 없음
- Chain Sight ↔ Thesis 연동 코드 미발견
- 프론트 `EntryPointGrid`는 뉴스/자유입력 2종만 (Phase2_summary 명시)

### 4. 가설 마감 복기 시스템 — (B) 부분 구현

**설계 (§3.9)**:
> "가장 유용했던 지표 / 예상과 달랐던 부분 / 정성적 결과 텍스트"

**현재 상태**:
- 마감 자체는 ✅ (close API + OutcomeSelector + ValidityRecord 생성)
- 마감 이후 정성 복기 화면 부재 — 마감 페이지에서 outcome 선택 + 노트 입력으로 끝
- ValidityRecord는 점수만 기록(가장 유용했던 지표 산출 가능 데이터는 있음), 사용자에게 노출되는 화면 없음

### 5. Neo4j 가설 그래프 — (C) 미구현

**설계 (§4.4)**:
- `(Thesis)-[HAS_PREMISE]->(Premise)`
- `(Thesis)-[SIMILAR_TO]->(Thesis)`
- `(Indicator)-[CORRELATES_WITH]->(Indicator)` 등

**현재 상태**: thesis 앱에 Neo4j 연동 코드 없음. graph_analysis/, chainsight/는 별도. Phase 3에서 다룬다고 명시되었지만 미착수.

### 6. Phase 3 redesign 컴포넌트 통합 vs 분리 불일치 — (D) 폐기/대체 가능성

**설계 (`phase3_frontend_redesign.md` §1, §6)**:
- 별도 컴포넌트 4개: `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, `RealValueIndicatorCard`
- page.tsx에서 4개를 위→아래로 배치, `useState(chartVisible/chartPeriod)`로 토글

**현재 구현**:
- 4개 컴포넌트 파일 모두 존재 (`frontend/components/thesis/dashboard/`)
- 그러나 `app/thesis/[thesisId]/page.tsx`는 `IndicatorRow` 한 컴포넌트만 사용 — IndicatorRow가 카드 + 클릭 토글 + 기간선택 + 차트를 모두 흡수
- `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`가 어디서 사용되는지 확인 필요 (사용되지 않으면 dead code)

**기간 옵션 차이**: 설계 7D/14D/30D → 구현 1M/365D/3Y/5Y (`IndicatorRow.tsx:15-20`). 분기 지표 추가 요구로 장기 차트 옵션이 늘어난 것으로 보임 (분기 지표 대시보드 plan 영향).

### 7. Phase 3 두 계획서 충돌 — 메타 갭

**Phase2_completion_summary.md §8 — FE-PR-7~11 계획**:
- FE-PR-7: 대시보드 탭 구조 (3탭 관제/상세/히스토리)
- FE-PR-8: 히트맵 + 지표 상세 편집
- FE-PR-9: 히스토리 탭 (recharts)
- FE-PR-10: 마감 아카이브 + ValidityMatrix
- FE-PR-11: 투자자 DNA 프로필 (AccuracyRing + CategoryChart)

**`thesis_control_phase3_frontend_redesign.md` — PR-7~10 계획**:
- 위와 완전히 다른 방향. 탭 구조 폐기, 단일 페이지에 실제값 카드 + AI 분석 + 미니차트.

**결론**: redesign 계획서가 더 최근(2026-03-18)이며, Phase2 summary의 FE-PR-7~11은 redesign에 의해 폐기된 것으로 보임. 즉 **탭 구조 / DNA 프로필 / 마감 아카이브 / 히트맵 화면 / 지표 상세 편집 화면 모두 (D) 폐기 또는 (C) 미구현**.

DNA 프로필 화면은 Phase 3 redesign에 명시되지 않았으므로 일정상 Phase 4 또는 미정 상태.

---

## 보너스: 설계에 없는 추가 구현 (코드 일치성 ↔ 문서 갱신 부재)

다음 항목들은 코드에 존재하지만 설계 문서에 명시되지 않음 — 문서 동기화가 필요:

1. **분기 지표 시스템** — `quarterly_metric_fetcher.py`, `is_quarterly`/`fiscal_label`/`quarterly_history`/`comparison_type` 응답 필드, `QuarterlySparkline` 컴포넌트, RATIO_METRICS % 변환. (`docs/thesis_control/plan/talking_builder/quarterly_indicator_dashboard_plan.md`로 별도 문서화됨)
2. **LLM 빌더 모드** — `start_llm_conversation`/`process_llm_turn`/`generate_suggestions` (Phase A-MVP). (`work_done/phase_a_llm_builder.md` 존재 — Read 실패로 내용 미확인)
3. **수학 모델 v2.3.2** — Stage 0~3 (data_validator, indicator_scorer, premise_aggregator, thesis_state_machine), 11종 alert_type, throttling, validation_status 8종, universe 고정. (`docs/thesis_control/plan/thesis_control_math_model_final.md`로 별도 문서화)
4. **키워드 캐시 시스템** — `keyword_cache`, `keyword_collectors/`, KeywordCache 모델. 설계서에 없음. migration 0006/0007.
5. **FMP 히스토리 fallback** — DB readings 부족 시 외부 API로 보강. 설계서에 없음.
6. **`recommendation_reason` 단일 필드** — 설계의 `rationale`+`context_explanation` 분리 안 함. migration 0009.
7. **feature_flags.py** — feature flag 시스템 자체.

---

## 권고 (참고용 — 본 보고서는 read-only)

1. **계획서 충돌 해결**: `Phase2_completion_summary.md`의 FE-PR-7~11과 `phase3_frontend_redesign.md`의 PR-7~10이 충돌. 요약 보고서를 갱신하거나 폐기하여 단일 진실 소스 유지.
2. **PR-10 AI 파이프라인 우선**: AI 분석/오늘의 변화는 컴포넌트와 응답 구조가 모두 준비되어 있으므로 `generate_thesis_summaries` Celery task만 구현하면 즉시 활성화.
3. **Phase 3 redesign 컴포넌트 정리**: `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts` 4개가 dead code인지 확인 후 삭제 또는 IndicatorRow를 이들로 분해.
4. **마감 복기/DNA 프로필 로드맵 명시**: `InvestorDNA` 모델은 데이터를 모으고 있지만 노출 UI가 없음. Phase 3 또는 Phase 4 어느 시점에 들어갈지 결정 필요.
5. **인기 가설 / 템플릿 / Chain Sight 연동**: 모델은 만들어져 있으나 노출 경로 0. Phase 3 redesign 계획에서 빠져 있어 보류 상태로 보이는데, 명시적 deprecation 또는 일정 표시 권장.
