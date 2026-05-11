# Thesis Control 설계 갭 감사

> 감사일: 2026-05-06
> 감사자: Claude (read-only audit)
> 대상: `docs/thesis_control/` (설계) vs `thesis/` + `frontend/components/thesis/` + `frontend/app/thesis/` (구현)
> 모드: 읽기 전용 — 코드 변경 없음

---

## 요약 (Phase별 구현률)

| Phase | 설계 영역 | 구현률 | 비고 |
|-------|----------|--------|------|
| **Phase 1 (MVP)** | 모델 + 스코어링 + CRUD + Celery + 이벤트 | **~95%** | 핵심 루프 완성. 일부 API 누락 (`/snapshots/`, `/summary/`) |
| **Phase 2 (모니터링 강화)** | 카드/히트맵/그래프 뷰 + [근거] + 뉴스 + 유효성 + DNA 슬라이더 | **~55%** | FE-PR-1~6 완료. **히트맵·그래프뷰·뉴스 센티먼트·[근거] 시스템·DNA 슬라이더·역제안 미구현** |
| **Phase 3 (Redesign + 커뮤니티 + 지능 강화)** | 대시보드 리디자인 + 인기/템플릿/Chain Sight + 합성 에이전트 + Online LR + 복기 | **~30%** | **Redesign PR-7/PR-8/PR-9 부분 구현, PR-10 미구현. 원안 FE-PR-10/11 (마감 아카이브, DNA 프로필) 미구현. 커뮤니티·합성 에이전트·Neo4j 가설 그래프 전부 미구현** |
| **Phase 4 (지능화)** | 벡터 + 사용자 유사도 + Change Point | **0%** | 미착수 |

### 종합 진단

- **백엔드 코어 엔진** (Stage 0~3, 알림, 스냅샷, 이벤트/유효성/DNA 모델): **거의 완성** ✅
- **프론트엔드 핵심 루프** (목록→빌더→지표→대시보드→알림→마감): **완성** ✅
- **Phase 3 대시보드 Redesign**: PR-7 백엔드 + PR-8 카드 + PR-9 차트(IndicatorRow에 통합)는 구현됐으나, **PR-10 AI 모니터링 파이프라인(`generate_thesis_summaries` Celery, `ai_summary` LLM 생성)은 미구현** → `ai_summary`는 항상 빈 문자열
- **Phase 3 후반 영역** (마감 아카이브, 투자자 DNA 프로필 화면, 인기 가설, 템플릿, Chain Sight 연동, 합성 에이전트 부트스트래핑): **전부 미구현**
- **설계 문서가 진화한 흔적** — 원안 FE-PR-7~11 (탭/히트맵/히스토리/아카이브/DNA)는 `thesis_control_phase3_frontend_redesign.md` v1.0 (2026-03-18)에서 "내부 점수 숨기기 + 실제 값 표시" 방향으로 전면 재설계되어 원안 일부가 폐기됨

---

## 문서별 상태 테이블

### 1. 설계 문서 vs 백엔드 모델

| 설계 항목 (설계 문서 4.2 + v2.3.2 + 통합 로드맵) | 구현 위치 | 상태 |
|---|---|---|
| `Thesis` 모델 | `thesis/models/thesis.py` | A. 완전 구현 |
| `ThesisPremise` 모델 | `thesis/models/thesis.py` | A. 완전 구현 |
| `ThesisIndicator` 모델 + `display_unit` 필드 (PR-7) | `thesis/models/indicator.py` + `migrations/0004_add_display_unit.py` | A. 완전 구현 |
| `IndicatorReading` 모델 + asof/validation_status | `thesis/models/indicator.py` | A. 완전 구현 |
| `ThesisSnapshot` 모델 + `asof_date`/`data_coverage`/`universe_snapshot`/`ai_summary`/`notable_changes` | `thesis/models/monitoring.py` | A. 완전 구현 (필드 존재, `ai_summary`는 작성 로직 없음 — PR-10) |
| `ThesisAlert` 모델 + `target_id`/`cooldown_hours` | `thesis/models/monitoring.py` | A. 완전 구현 |
| `ThesisFollow`, `PopularThesisCache` | `thesis/models/community.py` | B. 부분 구현 (모델만, View/API/Celery 갱신 없음) |
| `HypothesisEvent` 모델 + 13가지 event_type | `thesis/models/learning.py` | A. 완전 구현 |
| `ValidityRecord` 모델 (2×2 매트릭스 점수) | `thesis/models/learning.py` | A. 완전 구현 |
| `InvestorDNA` 모델 (premise_category_counts, indicator_type_counts, ai_accept_rate, top_down_ratio) | `thesis/models/learning.py` | A. 완전 구현 |
| `ValidityScore` 모델 (Phase 2) | — | C. 미구현 |
| `is_synthetic` 필드 (Phase 3 합성 에이전트) | — | C. 미구현 |
| `dna_vector`, `validity_vector` (Phase 4) | — | C. 미구현 |
| `KeywordCache` (설계 문서 외 추가) | `thesis/models/keyword.py` (migration 0006/0007) | A. 추가 구현 (LLM 키워드 캐시) |

### 2. 설계 문서 vs 백엔드 서비스 (스코어링 엔진)

| 설계 항목 (수학 모델 v2.3.2) | 구현 위치 | 상태 |
|---|---|---|
| Stage 0: `data_validator.py` | `thesis/services/data_validator.py` | A. 완전 구현 |
| Stage 1: `indicator_scorer.py` (Robust Z + Decay) | `thesis/services/indicator_scorer.py` | A. 완전 구현 |
| Stage 2: `premise_aggregator.py` | `thesis/services/premise_aggregator.py` | A. 완전 구현 |
| Stage 3: `thesis_state_machine.py` | `thesis/services/thesis_state_machine.py` | A. 완전 구현 |
| `arrow_calculator.py` | `thesis/services/arrow_calculator.py` | A. 완전 구현 |
| `alert_engine.py` (throttling) | `thesis/services/alert_engine.py` | A. 완전 구현 |
| `snapshot_builder.py` | `thesis/services/snapshot_builder.py` | A. 완전 구현 |
| `thesis_builder.py` (대화형 LLM) + 이벤트 기록 | `thesis/services/thesis_builder.py` | A. 완전 구현 |
| `indicator_matcher.py` (키워드 룰 + LLM) | `thesis/services/indicator_matcher.py` | A. 완전 구현 |
| `quarterly_metric_fetcher.py` (분기 데이터) | `thesis/services/quarterly_metric_fetcher.py` | A. 추가 구현 (설계 문서엔 없음) |
| `keyword_cache.py`, `keyword_collectors/`, `keyword_hint.py` | `thesis/services/` | A. 추가 구현 |
| `summary_generator.py` (설계 5.4) | — | C. 미구현 (PR-10 LLM AI 요약 파이프라인) |
| `news_connector.py` (설계 5.4) | — | C. 미구현 |
| 상관계수 자동 할인 (Phase 2 — 60일 \|ρ\|≥0.9 → 1/√k) | — | C. 미구현 |
| Adaptive Decay/Window (Phase 2) | — | C. 미구현 |
| Sustained Extreme (Phase 2) | — | C. 미구현 |
| 합성 에이전트 부트스트래퍼 (Phase 3) | — | C. 미구현 |
| Online Logistic Regression (Phase 3) | — | C. 미구현 |

### 3. 설계 문서 vs 백엔드 API (urls.py + views/)

| 설계 6.1 엔드포인트 | 실구현 | 상태 |
|---|---|---|
| `POST /` 가설 생성 | `ThesisViewSet` create | A. 완전 |
| `GET /` 가설 목록 | `ThesisViewSet` list | A. 완전 |
| `GET /{id}/`, `PATCH /{id}/` | `ThesisViewSet` retrieve/update | A. 완전 |
| `POST /{id}/close/` | `ThesisViewSet` close action | A. 완전 |
| `POST /conversation/start/`, `/respond/` | `ConversationStartView`, `ConversationRespondView` | A. 완전 |
| `POST /{id}/indicators/auto/` | `ThesisIndicatorViewSet` auto action | A. 완전 |
| `GET /{id}/indicators/`, CRUD | `ThesisIndicatorViewSet` | A. 완전 |
| `GET /{id}/premises/`, CRUD | `ThesisPremiseViewSet` | A. 완전 |
| `GET /{id}/dashboard/` | `DashboardView` (raw_value/AI summary/notable changes 포함) | A. 완전 |
| `GET /{id}/indicators/{iid}/readings/` (PR-7) | `IndicatorReadingsView` (FMP fallback 포함) | A. 완전 |
| `GET /alerts/`, `PATCH /alerts/{aid}/read/` | `AlertListView`, `AlertReadView` | A. 완전 |
| `GET /{id}/snapshots/` (스냅샷 히스토리) | — | C. 미구현 |
| `GET /{id}/summary/` (AI 현재 상태 요약 별도 엔드포인트) | — | B. 부분 (대시보드 응답에 포함, 별도 엔드포인트는 없음) |
| `GET /{id}/indicators/{iid}/explanation/` ([근거]) | — | C. 미구현 |
| `GET /daily-issues/` | `NewsIssuesView` (`/conversation/news-issues/`) | D. 대체 (다른 경로) |
| `POST /conversation/suggest/` (AI 가설 추천) | `SuggestThesesView` | A. 추가 구현 |
| `GET /popular/` 인기 가설 | — | C. 미구현 |
| `POST /popular/{id}/follow/` | — | C. 미구현 |
| `GET /popular/{id}/detail/` | — | C. 미구현 |
| `GET /templates/`, `GET /templates/{type}/` | — | C. 미구현 |

### 4. Celery 태스크 (설계 5.3)

| 설계 태스크 | 구현 | 상태 |
|---|---|---|
| `update_indicator_readings` (18:00 ET) | `thesis/tasks/eod_pipeline.py` | A. 완전 |
| `calculate_arrow_degrees` (18:15 ET) | `calculate_scores` (eod_pipeline) | A. 완전 |
| `create_daily_snapshots` (18:30 ET) | `create_snapshots_and_alerts` (eod_pipeline) | A. 완전 |
| `check_thesis_alerts` (18:45 ET) | `create_snapshots_and_alerts`에 통합 | A. 완전 |
| `scan_thesis_news` (2시간마다) | — | C. 미구현 |
| `update_popular_thesis_cache` (08:00) | — | C. 미구현 |
| `prepare_daily_issues` (07:00) | — | C. 미구현 (NewsIssuesView 응답은 실시간 계산 추정) |
| `generate_thesis_summaries` (07:30) — PR-10 | — | C. 미구현 (`ai_summary` 필드 항상 빈 문자열) |

### 5. 설계 문서 vs 프론트엔드 (FE-PR-1~6 — Phase 2 완료)

| FE-PR | 영역 | 완료 보고서 | 상태 |
|---|---|---|---|
| FE-PR-1 | 라우팅 + 공통 컴포넌트 + authAxios | `task_done/FE-PR-1_routing_common_components.md` | A. 완전 |
| FE-PR-2 | 가설 목록 + 오늘의 변화 + 진입점 | `task_done/FE-PR-2_thesis_list_page.md` | A. 완전 |
| FE-PR-3 | 대화형 빌더 (6단계) | `task_done/FE-PR-3_builder_implementation.md` | A. 완전 |
| FE-PR-4 | 지표 설정 (AI 추천 + 토글/삭제) | `task_done/FE-PR-4_indicator_setup.md` | A. 완전 |
| FE-PR-5 | 관제실 대시보드 (달 위상 + 화살표) | `task_done/FE-PR-5_dashboard.md` | D. **폐기/대체** (Phase 3 redesign이 OverallMoon, DashboardIndicatorCard, RecentChange 모두 제거) |
| FE-PR-6 | 알림 + 마감 + QA | `task_done/FE-PR-6_alerts_close_qa.md` | A. 완전 |

### 6. Phase 3 Redesign (`thesis_control_phase3_frontend_redesign.md`) PR-7~10

> 원칙: "UI에 보이는 모든 숫자 = 사용자가 아는 실세계 값" / "내부 점수는 UI에서 숨김"

| PR | 영역 | 핵심 산출물 | 상태 |
|---|---|---|---|
| **PR-7** | 백엔드 확장 | `display_unit` 필드, raw_value/change_pct 응답, `IndicatorReadingsView`, `_infer_unit()` fallback, 데이터 마이그레이션 | A. **완전 구현** (`migrations/0004_*`, `0005_populate_display_unit.py`, monitoring_views.py 확장) |
| **PR-8** | 카드 + AI 분석 | `RealValueIndicatorCard`, `AISummarySection`, `NotableChangesSection` + `formatRawValue/formatChangePct/supportLabel` 유틸 | B. **부분** — 컴포넌트 3개 모두 존재. 그러나 `[thesisId]/page.tsx`는 `IndicatorRow` (자체 진화 컴포넌트)를 사용하고 `RealValueIndicatorCard`는 사용하지 않음 → `RealValueIndicatorCard.tsx`가 dead code 가능성 |
| **PR-9** | 미니차트 + 기간 선택 | `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, `useAllIndicatorReadings` 훅, `MOCK_READINGS` | D. **대체 구현** — 컴포넌트 3개 모두 파일은 존재. 그러나 메인 페이지는 `IndicatorRow` 내부에 차트 토글(`useState expanded`) + 자체 기간 선택(`DAILY_PERIODS: 1M/1Y/3Y/5Y`)을 통합. PR-9 설계의 외부 토글(7D/14D/30D)이 행별 토글로 진화. 외부 컴포넌트들은 dead code 가능성 |
| **PR-10** | AI 모니터링 파이프라인 (Celery) | `generate_thesis_summaries` 태스크, alert_engine 이벤트→`notable_changes` 변환 | C. **미구현** — `generate_thesis_summaries` Celery 태스크 부재, `__pycache__/summary.cpython-312.pyc`만 존재(소스 파일 없음). `ThesisSnapshot.ai_summary` 채워지지 않음. `notable_changes`는 score 변화 기준(snapshot_builder.py:106-122)으로 생성되며 redesign이 의도한 alert 이벤트 재활용 방식과 다름 |

### 7. 원안 FE-PR-7~11 (Phase2_completion_summary.md "Phase 3 계획")

> 원안 → Phase 3 redesign으로 전면 재설계되며 일부 폐기

| 원안 PR | 원안 핵심 | Redesign 매핑 | 상태 |
|---|---|---|---|
| FE-PR-7 | 대시보드 탭 구조 (관제/상세/히스토리 3탭) + 전제 CRUD | Redesign에서 탭 구조 폐기 — 단일 페이지에 카드/AI 분석/Notable Changes 통합 | D. **폐기** |
| FE-PR-8 | 히트맵 (Finviz 스타일) + 지표 상세 편집 (weight/direction) | Redesign에서 히트맵 시각화 제거 — 백엔드 `dashboard.heatmap` 응답은 남아 있으나 프론트 사용처 없음 | D. **폐기** |
| FE-PR-9 | 히스토리 탭 (recharts 라인 차트 + 스냅샷 타임라인) | `IndicatorRow` 내부 미니차트로 대체 (단일 지표별, 스냅샷 타임라인 아님) | D. **폐기/일부 대체** |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix 요약 화면 | Redesign에 미포함 | C. **미구현** |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart + 기술 부채 정리) | Redesign에 미포함 | C. **미구현** (백엔드 InvestorDNA 모델은 존재) |

### 8. 프론트엔드 라우팅 (FE-PR-1 정의)

| 라우트 | 페이지 | 상태 |
|---|---|---|
| `/thesis` | (list) 가설 목록 | A. 완전 |
| `/thesis/new?entry=...` | 대화형 빌더 | A. 완전 |
| `/thesis/alerts` | 알림 목록 | A. 완전 |
| `/thesis/[id]` | 대시보드 | A. 완전 (Redesign 적용) |
| `/thesis/[id]/indicators` | 지표 설정 | A. 완전 |
| `/thesis/[id]/close` | 마감 (Outcome 선택) | A. 완전 |
| `/thesis/archive` 또는 `/thesis/closed` | — | C. **미구현** (FE-PR-10 원안) |
| `/thesis/profile` 또는 `/thesis/dna` | — | C. **미구현** (FE-PR-11 원안) |

---

## Phase 3 미구현 항목 상세

### 미구현 1: PR-10 AI 모니터링 파이프라인 (백엔드)

**설계 위치:** `thesis_control_phase3_frontend_redesign.md` Section 7

**누락 산출물:**
- `generate_thesis_summaries` Celery 태스크 (07:30 cron)
  - 입력: 수학 엔진 결과 + DailyNewsKeyword + 전제 텍스트 + raw_value 변화
  - 출력: 2~3문장 요약 → `ThesisSnapshot.ai_summary`
  - LLM: Gemini 2.5 Flash, 변화 있는 가설만 (비용 절감)
- `notable_changes` 재정의 — 현재 `snapshot_builder.py:106-122`는 score 변화(|delta| ≥ 0.3) 기준으로 채우지만, redesign은 `alert_engine` 이벤트(direction_flip/sharp_move/extreme_volatility) 재활용을 명시 (Section 7.2)
- 주간 건강 검진 (Section 7.3) — 미구현

**증거:**
- `thesis/tasks/eod_pipeline.py`에 `generate_thesis_summaries` 없음
- `thesis/tasks/__pycache__/summary.cpython-312.pyc` 존재 (소스 부재 → 삭제된 흔적)
- `DashboardView`가 `latest_snapshot.ai_summary` 그대로 반환하지만 항상 빈 문자열

### 미구현 2: PR-8/PR-9 컴포넌트의 메인 페이지 통합

**문제:** Redesign 설계와 다르게 `[thesisId]/page.tsx`는 `IndicatorRow`만 사용하고 PR-8/PR-9 컴포넌트들은 dead code일 가능성.

**증거:**
- `frontend/components/thesis/dashboard/`에 다음 파일들 존재:
  - `RealValueIndicatorCard.tsx` (PR-8 설계)
  - `ChartToggleButton.tsx` (PR-9 설계)
  - `PeriodSelector.tsx` (PR-9 설계)
  - `IndividualMiniCharts.tsx` (PR-9 설계)
- 그러나 `app/thesis/[thesisId]/page.tsx`는 `IndicatorRow`만 import (RealValueIndicator/ChartToggle/Period/Individual 미사용)
- `IndicatorRow.tsx`는 자체적으로 expanded state + DAILY_PERIODS(1M/1Y/3Y/5Y) + recharts AreaChart + QuarterlySparkline 통합
- → 실질 구현은 IndicatorRow에 모두 흡수됨. PR-8/PR-9 외부 컴포넌트는 미사용 가능성 → 정리 필요

**액션 후보:**
- 사용 여부 확인 후 dead code 삭제, 또는
- IndicatorRow를 RealValueIndicatorCard + 미니차트 조합으로 분해해서 redesign 의도 충족

### 미구현 3: 원안 FE-PR-10 마감 아카이브

**설계 위치:** `Phase2_completion_summary.md` 8절, `thesis_control_design.md` 3.10

**누락 산출물:**
- `/thesis/archive` 또는 `/thesis/closed` 라우트 미존재
- 마감된 가설 목록 화면 — 현재 closed 가설은 단순히 ThesisViewSet list에 섞여 표시될 뿐 별도 아카이브 UI 없음
- ValidityMatrix 요약 (각 마감 가설에 대한 적중/지표 정렬 시각화)
- 복기 시스템 (설계 3.10): "가장 유용했던 지표", "예상과 달랐던 부분"

### 미구현 4: 원안 FE-PR-11 투자자 DNA 프로필

**설계 위치:** `Phase2_completion_summary.md` 8절, 통합 로드맵 1.4

**누락 산출물:**
- `/thesis/profile` 또는 `/thesis/dna` 라우트 미존재
- `AccuracyRing` 컴포넌트 미존재
- `CategoryChart` 컴포넌트 미존재
- DNA 적합도 슬라이더 (`personalization_weight` 필드는 모델에 있으나 UI 부재)
- 역제안 (Contrarian Nudge) 표시 UI

**백엔드 상태:** `InvestorDNA` 모델은 갱신 로직까지 완전 구현 (`thesis_views.py:293-329`). API 엔드포인트만 노출하면 즉시 화면 구성 가능.

### 미구현 5: 설계 문서 6.1의 누락 API

| API | 영향 |
|---|---|
| `GET /{id}/snapshots/` | 시계열 그래프뷰 데이터 부재 (대안: IndicatorRow가 readings API 호출) |
| `GET /{id}/summary/` | 별도 AI 요약 엔드포인트 — 현재 dashboard 응답에만 포함 |
| `GET /{id}/indicators/{iid}/explanation/` | [근거] 시스템 (설계 2.4) — 핵심 학습 UX 누락 |
| `GET /daily-issues/` | 별도 path는 없음, `/conversation/news-issues/`로만 노출 (D. 대체) |

### 미구현 6: Phase 2 후반 미구현 (히트맵·그래프뷰·뉴스 센티먼트·[근거])

**설계 위치:** `thesis_control_implementation_guide.md` Phase 2 Week 7~12

| 항목 | 상태 |
|---|---|
| 히트맵 뷰 API | B. 부분 — 백엔드 `dashboard.heatmap` 응답은 있으나 프론트 사용처 없음 (Redesign으로 폐기) |
| 그래프 뷰 API (시계열 선 그래프) | B. 부분 — IndicatorRow 미니차트가 대체 (단일 지표 단위) |
| `[근거]` 설명 시스템 (LLM + Redis 캐싱) | C. 미구현 — 키워드 캐시(`KeywordCache`)는 있으나 indicator/premise [근거] 미구현 |
| AI 일일 요약 | C. 미구현 (PR-10과 동일) |
| 뉴스 센티먼트 지표 (news/ SentimentHistory → Stage 1 입력) | C. 미구현 |
| 내러티브 반감기 (DailyNewsKeyword → narrative_momentum 지표) | C. 미구현 |
| 오늘 이슈 API | D. 대체 (`/conversation/news-issues/`로만) |

### 미구현 7: Phase 2/3 학습 활성화

| 항목 | 상태 | 비고 |
|---|---|---|
| `ValidityScore` 모델 | C. 미구현 | Phase 2 — `ValidityRecord` 집계 결과 |
| 점진적 활성화 (sample_count ≥ 5) | C. 미구현 | |
| `indicator_matcher`에 유효성 점수 반영 | C. 미구현 | core/reference/low_impact 티어 |
| DNA 적합도 슬라이더 | C. 미구현 | personalization_weight 필드만 존재 |
| 역제안 (Contrarian Nudge) | C. 미구현 | |
| 합성 에이전트 부트스트래퍼 (Phase 3 — 특허 핵심 차별점) | C. 미구현 | `is_synthetic` 필드 모델에 없음 |
| Online Logistic Regression (`ThesisWeightLearner`) | C. 미구현 | |
| `is_synthetic` 필드 추가 | C. 미구현 | |
| 합성/실제 데이터 블렌딩 | C. 미구현 | |

### 미구현 8: Phase 3 커뮤니티 + Chain Sight 연동 + Neo4j

| 항목 | 상태 | 비고 |
|---|---|---|
| 인기 가설 시스템 (`/popular/`) | B. 부분 | 모델만 (`PopularThesisCache`) |
| 가설 따라하기 (`POST /popular/{id}/follow/`) | B. 부분 | 모델만 (`ThesisFollow`) |
| 템플릿 시스템 (이벤트형/추세형/비교형/괴리형) | C. 미구현 | API/View/UI 모두 부재 |
| Chain Sight ↔ Thesis Control 양방향 연동 (entry_source='chainsight') | B. 부분 | `Thesis.entry_source` 필드는 있으나 양방향 진입점 UI 없음 |
| Neo4j 가설 관계 그래프 (HAS_PREMISE, SIMILAR_TO, OPPOSITE_OF) | C. 미구현 | `graph_analysis/`에 thesis 관련 코드 없음 |
| 가설 아카이브 + 학습 이력 UI | C. 미구현 | |

---

## 부록 A: 분류 기준

- **A. 완전 구현**: 설계 의도대로 모델/뷰/UI/태스크가 모두 존재하며 기능적으로 동작
- **B. 부분 구현**: 일부 계층만 (예: 모델만 / API만 / UI만), 또는 핵심 필드는 채워지지만 LLM 생성 등 후속 파이프라인 부재
- **C. 미구현**: 설계 항목이 코드에 없음
- **D. 폐기/대체**: 설계서 후속 버전에서 다른 방식으로 재설계되어 원안이 폐기되거나 대체됨

## 부록 B: 추가 발견 사항 (설계 문서 외 구현)

| 항목 | 위치 | 비고 |
|---|---|---|
| `KeywordCache` 모델 + 키워드 수집 파이프라인 | `thesis/models/keyword.py`, `thesis/services/keyword_*.py` | LLM 키워드 추출 캐싱 — 설계 문서엔 없음 |
| `quarterly_metric_fetcher.py` + 분기 데이터 대시보드 통합 | `thesis/services/`, `IndicatorRow` + `QuarterlySparkline` | 분기 지표 (RATIO_METRICS % 변환, 5Y fallback) — 설계 외 추가 |
| `metrics` data_source + 분기 RATIO_METRICS | `migrations/0008_add_metrics_data_source.py` | |
| `recommendation_reason` 필드 (지표 설명 + 가설 관계성) | `migrations/0009_add_recommendation_reason.py` | DashboardView 응답 포함 |
| `feature_flags.py` | `thesis/feature_flags.py` | 설계 외 |
| FMP 히스토리 API fallback | `monitoring_views.py:_fetch_fmp_history` | DB readings 부족 시 fallback — 설계엔 없음 |

## 부록 C: 결론 — Phase 3 종결을 위한 우선순위

1. **PR-10 AI 모니터링 파이프라인** 구현 — `ai_summary` 빈 문자열 문제 해소 (`generate_thesis_summaries` Celery 태스크)
2. **PR-8/PR-9 dead code 정리** — `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`가 실제 사용되는지 grep 후 미사용 시 제거 또는 메인 페이지 통합
3. **원안 FE-PR-10 (마감 아카이브)** — 마감된 가설 목록 + 복기 화면. 백엔드 `closed_*` status는 이미 존재
4. **원안 FE-PR-11 (투자자 DNA 프로필)** — 백엔드 `InvestorDNA` 갱신 로직 완성, API + 화면만 추가하면 됨
5. **`[근거]` 시스템** (설계 2.4) — 핵심 학습 UX이지만 누락. LLM + Redis 캐싱
6. **`/{id}/snapshots/` 엔드포인트** — 그래프뷰가 폐기됐어도 마감 복기 화면에 필요
7. (Phase 3 후반) Phase 2 마무리 — 뉴스 센티먼트 지표 + 내러티브 반감기
