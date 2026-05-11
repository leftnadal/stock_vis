# Thesis Control 설계 갭 감사

> 감사 일자: 2026-05-02
> 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` 백엔드 + `frontend/components/thesis/` + `frontend/app/thesis/` 구현
> 본 보고서는 **읽기 전용 감사**이며, 코드 변경은 일체 없습니다.

---

## 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 비고 |
|-------|------|--------|------|
| Phase 1 (관제 엔진 v2.3.2) | BE 모델/스코어링/스냅샷/알림 | **A. 완전 구현** (95%) | Stage 0~3, Celery 3태스크, 스냅샷 unique constraint 모두 작동 |
| Phase 1 (이벤트/유효성 인프라) | BE `HypothesisEvent`/`ValidityRecord`/`InvestorDNA` 모델 | **B. 부분 구현** (50%) | 모델은 존재. 그러나 이벤트 기록 hook/마감 시 ValidityRecord 생성/DNA 갱신이 코드상 비어있을 가능성 높음 (감사 범위 외 — 별도 검증 필요) |
| Phase 2 — Builder | FE-PR-1~3 라우팅+공통+빌더 | **A. 완전 구현** | task_done 보고서 + 실제 컴포넌트 일치 |
| Phase 2 — Indicator Setup | FE-PR-4 지표 설정 | **A. 완전 구현** | `indicators/` 컴포넌트 3종 + 페이지 1종 |
| Phase 2 — Dashboard | FE-PR-5 관제실 대시보드 | **A. 완전 구현** | 화살표/달위상/트렌드/내러티브 모두 작동 |
| Phase 2 — Alerts/Close | FE-PR-6 알림+마감 | **A. 완전 구현** | 3탭 필터 + OutcomeSelector + CloseConfirmDialog |
| Phase 3-Redesign (PR-7~9) | 깊이뷰 = "실제값 + AI 분석 + 차트" 리디자인 | **A. 완전 구현** (FE/BE) | RealValueIndicatorCard / AISummarySection / NotableChangesSection / PeriodSelector / IndividualMiniCharts / QuarterlySparkline / `display_unit` 마이그레이션 / DashboardView raw_value+change_pct+fiscal_label 필드 모두 라이브 |
| Phase 3-Redesign (PR-10) | AI 모니터링 파이프라인 (Celery + Gemini) | **C. 미구현** | `generate_thesis_summaries` 태스크 부재. `ThesisSnapshot.ai_summary` 필드는 존재하나 항상 빈 문자열로 저장됨 |
| Phase 3 — Phase2 summary 정의 (FE-PR-7~11) | 탭 구조 / 히트맵 / 히스토리 / 아카이브 / DNA Profile | **C. 거의 전부 미구현** | 라우트/컴포넌트 모두 부재 |
| Phase 2 (Validity Score 활성화 / DNA 슬라이더 / 역제안 / 상관할인 / Adaptive Decay / 뉴스 센티먼트) | 통합 로드맵 §2 | **C. 미구현** | 모델/태스크 모두 부재 |
| Phase 3 (합성 에이전트 / Online LR / 블렌딩) | 통합 로드맵 §3 | **C. 미구현** | `SyntheticBootstrapper`, `ThesisWeightLearner`, `aggregate_validity_scores` 모두 부재 |
| Phase 4 (벡터 스코어링) | 통합 로드맵 §4 | **C. 미구현** | 설계 단계에서 의도된 후순위 |

> **PR 번호 체계 충돌 주의**: "Phase 3"이라는 단어가 두 문서에서 다르게 쓰입니다.
> - **(A)** `thesis_control_phase3_frontend_redesign.md` → PR-7(BE 확장) / PR-8(실제값 카드) / PR-9(미니차트) / PR-10(AI 파이프라인) — *4개 PR, 대시보드 리디자인*
> - **(B)** `frontend/task_done/Phase2_completion_summary.md` 마지막 §3.1 → FE-PR-7(탭 구조) / FE-PR-8(히트맵) / FE-PR-9(히스토리) / FE-PR-10(아카이브) / FE-PR-11(DNA Profile) — *5개 PR, 깊이+회고+프로필*
> 코드와 일치하는 것은 **(A)** 입니다. CLAUDE.md의 "Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"는 **(B)** 체계를 가리키며 사실상 미시작입니다.

---

## 문서별 상태 테이블

### 1) 백엔드 핵심 설계 (`plan/`)

| 문서 | 핵심 산출물 | 매칭 코드 | 상태 |
|------|------------|----------|------|
| `thesis_control_design.md` (1370L) | 모델/뷰/서비스 전체 스펙 | `thesis/models/*`, `thesis/views/*`, `thesis/services/*` | **A. 완전 구현** — Thesis/ThesisPremise/ThesisIndicator/IndicatorReading/ThesisSnapshot/ThesisAlert 모두 존재 |
| `thesis_control_math_model_final.md` (1153L, v2.3.2) | Stage 0~3 스코어링 수식 | `services/data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `thesis_state_machine.py`, `arrow_calculator.py` | **A. 완전 구현** — 9개 서비스 모듈 모두 존재. Robust Z(MAD)+Decay, 가중평균+최약고리, Rule-based 상태, asof_date+universe 고정 모두 코드 확인 |
| `thesis_control_implementation_guide.md` (286L) | 구현 가이드 (Phase 1) | 기존 코드와 일치 | **A. 완전 구현** |
| `thesis_control_integrated_roadmap.md` (660L) | Phase 1~4 통합 로드맵 | Phase 1 BE만 부분 일치 | **B. 부분 구현** (Phase 1 모델만, ValidityScore/Phase 2~4 전부 미구현) |
| `thesis_control_phase3_frontend_redesign.md` (1095L) | PR-7~10 (실제값 카드 + AI + 차트 + 파이프라인) | `dashboard/*.tsx`, `monitoring_views.py`, migration 0004/0005, `eod_pipeline.py` | **B. 부분 구현** — PR-7~9 완료, **PR-10 (AI Celery 파이프라인) 미시작** |
| `thesis_control_user_experience.md` (435L) | UX 흐름 가이드 | Phase 2 흐름과 일치 | **A. 완전 구현** (현재 흐름까지) |

### 2) Phase 1 백엔드 프롬프트 (`thesis_control_phase1_prompts.md`, 1243L)

| 항목 | 매칭 | 상태 |
|------|------|------|
| BE-PR-1 모델 + 마이그레이션 | `thesis/models/`, migration 0001 | A |
| BE-PR-2 Stage 0~3 서비스 | `services/data_validator.py` 외 8개 | A |
| BE-PR-3 Celery 태스크 3종 | `tasks/eod_pipeline.py: update_indicator_readings, calculate_scores, create_snapshots_and_alerts` | A |
| BE-PR-4 API 뷰 (CRUD + 대시보드 + 알림) | `views/thesis_views.py`, `monitoring_views.py`, `conversation_views.py`, `urls.py` | A |
| BE-PR-5 시리얼라이저 | `serializers/*.py` | A |

### 3) Phase 2 프론트엔드 task_done 보고서

| 보고서 | 매칭 컴포넌트/라우트 | 상태 |
|--------|---------------------|------|
| FE-PR-1 (라우팅+공통) | `app/thesis/layout.tsx`, `(list)/`, `[thesisId]/`, `common/{ArrowIndicator,MoonPhase,ThesisBadge,AlertBell,BottomSheet,IndicatorCard}.tsx`, `lib/api/authAxios.ts` | **A** |
| FE-PR-2 (목록 페이지) | `(list)/page.tsx`, `(list)/alerts/page.tsx`, `list/{ThesisListCard,TodayChangeCard,EntryPointGrid}.tsx` | **A** |
| FE-PR-3 (대화형 빌더) | `new/page.tsx`, `builder/{ChatBubble,OptionButton,TextInput,SuggestionCard,PremiseCard,ProgressBar,BottomSheet,MultiSelectFooter,NewsSelector}.tsx` (9개) | **A** |
| FE-PR-4 (지표 설정) | `[thesisId]/indicators/page.tsx`, `indicators/{IndicatorSetupCard,RecommendCard,AddIndicatorSheet}.tsx` | **A** |
| FE-PR-5 (관제실 대시보드) | `[thesisId]/page.tsx`, `dashboard/{DashboardHeader,DashboardPageHeader,IndicatorRow,AISummarySection,NotableChangesSection,ChartToggleButton,PeriodSelector,IndividualMiniCharts,RealValueIndicatorCard,QuarterlySparkline}.tsx` | **A** (PR-5 산출 + PR-7~9 redesign 산출 통합) |
| FE-PR-6 (알림 + 마감) | `(list)/alerts/page.tsx`, `[thesisId]/close/page.tsx`, `alerts/{AlertCard,AlertFilterTabs,EmptyAlerts}.tsx`, `close/{OutcomeSelector,CloseConfirmDialog}.tsx` | **A** |
| `Phase2_completion_summary.md` | Phase 2 종결 선언 + Phase 3 FE-PR-7~11 예고 | A (선언) / **C** (예고된 PR-7~11은 미시작) |

### 4) talking_builder (빌더 v2 리디자인)

| 문서 | 매칭 | 상태 |
|------|------|------|
| `llm_builder_plan.md` (563L) | `services/thesis_builder.py`, `services/llm_postprocess.py`, `services/builder_state.py`, `services/builder_events.py`, `services/prompt_builder.py` | **A. 완전 구현** |
| `thesis_builder_redesign_v2.md` (1110L) | `conversation_views.py: ConversationStartView/RespondView/NewsIssuesView/SuggestThesesView` | **A. 완전 구현** |
| `redesign_build_plan/00_total_plan.md` (525L) | Phase A MVP / Hardening / B Keywords / C Advanced | **B. 부분 구현** — Phase A 완료, B/C 일부만 |
| `redesign_build_plan/01_phase_a_mvp.md` (287L) | 빌더 MVP | **A** (work_done/phase_a_llm_builder.md 기록) |
| `redesign_build_plan/02_phase_a_hardening.md` (118L) | 안정화 | **A** (assumed by completion) |
| `redesign_build_plan/03_phase_b_keywords.md` (299L) | 키워드 캐시 + Strength | **B** — `KeywordCache` 모델 + migration 0006/0007 존재. UI/E2E 검증 필요 |
| `redesign_build_plan/04_phase_c_advanced.md` (144L) | 고급 기능 | **C** (감사 범위 내 매칭 코드 없음) |
| `quarterly_indicator_dashboard_plan.md` (424L) | 분기 지표 대시보드 | **A. 완전 구현** — `quarterly_metric_fetcher.py` + DashboardView의 `is_quarterly`/`fiscal_label`/`quarterly_history` |

---

## Phase 3 미구현 항목 상세

### 3-1. Phase 3-Redesign 문서 기준 — PR-10 AI 파이프라인 (단일 미구현)

**설계 요구사항** (`thesis_control_phase3_frontend_redesign.md` §7, L923~L1095):

| 항목 | 설계 명세 | 현재 상태 |
|------|----------|----------|
| Celery 태스크 `generate_thesis_summaries` | 매일 07:30 KST 실행, Stage3 상태 + raw_value 변화를 Gemini에 전달, 2~3문장 한국어 요약 생성 | **부재** — `tasks/eod_pipeline.py`는 `update_indicator_readings`/`calculate_scores`/`create_snapshots_and_alerts` 3개만 정의 |
| `ThesisSnapshot.ai_summary` 필드 채움 로직 | Celery에서 동기 Gemini 호출 결과 저장 | **부재** — 모델 필드는 존재(`monitoring.py:26`), `snapshot_builder.py`에서는 `defaults={...}`에 `ai_summary` 누락. 항상 모델 default `''` 유지 |
| `notable_changes` 풍부화 | alert_engine 이벤트(direction_flip/sharp_move) 재활용해서 `{indicator_id, type, severity, message}` 구조로 변환 | **부분 구현** — `snapshot_builder.py` L106~L122에서 단순 `\|delta\| ≥ 0.3` 필터로만 채움. AI 풍부화 미적용 |
| Beat schedule 등록 | DatabaseScheduler에 `PeriodicTask.objects.create(...)` (CLAUDE.md 버그 #28 회피) | **부재** |

**FE 영향**: `AISummarySection` 컴포넌트는 정상 동작하지만 응답이 `data.thesis.ai_summary === ''` 이므로 **사용자 화면에서는 항상 빈 섹션** (또는 placeholder만 노출). NotableChanges 역시 단순 score delta만 표시.

### 3-2. CLAUDE.md/Phase2 summary 기준 — FE-PR-7~11 (모두 미구현)

**Phase2_completion_summary.md L129~L137에 정의된 차세대 5개 PR**:

| PR | 설계 의도 | 라우트 부재 | 컴포넌트 부재 | 백엔드 의존성 |
|----|----------|------------|--------------|--------------|
| **FE-PR-7** | 대시보드 탭 구조 (관제/상세/히스토리 3탭) + 전제 CRUD UI | `[thesisId]/(detail)/`, `[thesisId]/history/` 등 미생성. 현재 `[thesisId]/page.tsx`는 단일 화면 | `DashboardTabs`, `DetailTab`, `PremiseEditor` 부재 | 기존 ThesisPremiseViewSet 재활용 가능 (BE OK) |
| **FE-PR-8** | Finviz 스타일 히트맵 + 지표 weight/direction 인라인 편집 | (탭 내부) | `IndicatorHeatmap` (현재 dashboard에 cells 데이터는 응답 중이지만 사각형 렌더링 컴포넌트 없음), `IndicatorWeightSlider` 부재 | ThesisIndicator PATCH 가능 (BE OK) |
| **FE-PR-9** | 히스토리 탭 (recharts 라인 차트 + 스냅샷 타임라인) | `[thesisId]/history/page.tsx` 부재 | `ScoreHistoryChart`, `SnapshotTimeline` 부재 | `ThesisSnapshot` 시계열 조회 API 부재 (`/snapshots/?thesis_id=...` 미정의) |
| **FE-PR-10** | 마감 아카이브 (마감 가설 목록) + ValidityMatrix (2×2) | `(list)/archive/page.tsx` 부재 | `ArchiveList`, `ValidityMatrix2x2`, `RetrospectiveCard` 부재 | `Thesis` 필터 `status=closed`는 가능, **마감 시 ValidityRecord 자동 생성 로직 검증 필요** (`thesis_views.py: @close` 액션이 ValidityRecord/HypothesisEvent를 만드는지 미확인) |
| **FE-PR-11** | 투자자 DNA 프로필 페이지 (AccuracyRing + CategoryChart) | `/thesis/profile/page.tsx` 또는 `/profile/dna` 부재 | `AccuracyRing`, `CategoryChart`, `DNADashboard` 부재 | `InvestorDNA` 모델은 존재. **DNA 조회 API (`/users/me/dna/` 등) 미정의** |

### 3-3. Phase 2 (통합 로드맵 §2) — Phase 3 진입 전 누락된 선행 작업

| 항목 | 설계 명세 (`thesis_control_integrated_roadmap.md` §2) | 현재 상태 |
|------|------|----------|
| `ValidityScore` 모델 (집계 테이블) | `(thesis_type, indicator_data_key, market_regime)` unique + `cumulative_score`/`sample_count`/`confidence`/`is_active` | **부재** — `models/learning.py`에 정의 없음 |
| Celery 주 1회 ValidityRecord → ValidityScore 집계 | `aggregate_validity_scores` 태스크 | **부재** |
| 지표 추천에 유효성 점수 반영 | `indicator_matcher.match_indicators()` 가 `validity_boost` 계산 | **부재** — 현재 `indicator_matcher.py`는 키워드 룰 기반 매칭만 |
| DNA 적합도 슬라이더 (`apply_dna_personalization`) | 0.0~1.0 슬라이더로 객관/개인 블렌딩 | **부재** |
| 역제안 (Contrarian Nudge) (`add_contrarian_nudge`) | 안 쓰는 indicator_type에서 1개 추천 | **부재** |
| 상관계수 자동 할인 (60일 \|ρ\|≥0.9 → 1/√k) | `indicator_scorer.py`에 통합 | **부재** — 현재 v2.3.2 코어만 |
| Adaptive Decay/Window | 변동성 → λ↓, window↓ | **부재** |
| Sustained Extreme | s_decayed≥3 (clip 전) | **부재** (확인 필요) |
| 뉴스 센티먼트 → Stage 1 입력 | LLM 결과를 indicator로 통합 | **부재** |

### 3-4. Phase 3 (통합 로드맵 §3) — 합성 에이전트 + 자동학습

| 항목 | 설계 명세 | 현재 상태 |
|------|----------|----------|
| `SyntheticBootstrapper` | 20~30개 페르소나로 과거 시장 데이터 기반 합성 가설 → ValidityScore 사전 채움 | **부재** |
| `ThesisWeightLearner` (Online LR + L2) | 마감된 가설로 전제 가중치 학습 | **부재** |
| `ValidityRecord.is_synthetic` 필드 | 합성/실제 구분 | **부재** (모델 필드 미존재) |
| `aggregate_validity_scores(blend_ratio=0.3)` 블렌딩 | 실제 sample 늘면 합성 비중 자동 감소 | **부재** |

### 3-5. Phase 1 인프라 — 코드 hook 검증 필요 (감사 범위 외)

> 모델은 모두 존재하지만, **이벤트 기록 hook이 비즈니스 로직에 삽입되었는지**는 본 감사로는 확정 불가. 추가 grep 검증 필요 항목:

| 검증 포인트 | 추정 |
|------------|------|
| `thesis_views.py: ThesisViewSet.create()`에서 `HypothesisEvent.objects.create(event_type='thesis_created', ...)` 호출 여부 | 미검증 |
| `thesis_views.py: @close` 액션에서 `outcome_correct/incorrect/neutral` 이벤트 + `ValidityRecord` 생성 + `InvestorDNA` 갱신 | 미검증 |
| `ThesisIndicatorViewSet.create()` 시 `indicator_added` 이벤트 (`source: 'ai'\|'user'`) | 미검증 |
| `conversation_views.py: SuggestThesesView`에서 `ai_suggestion_shown/accepted/rejected` 기록 | 미검증 |

**권고**: 별도 audit로 `grep -n "HypothesisEvent.objects.create\|ValidityRecord.objects.create\|InvestorDNA" thesis/views/ thesis/services/`를 실행하여 hook 분포 확인 → Phase 2/3 진입 전 선행 조건이므로 **데이터 누락이 누적되면 학습 레이어가 무용지물**.

---

## 분류 요약

### (A) 완전 구현
- BE: Stage 0~3 스코어링 엔진 (v2.3.2), 9개 서비스 모듈, Celery 3태스크, 모든 ViewSet/APIView, 시리얼라이저, 마이그레이션 0001~0009
- BE: `display_unit` 필드 + 마이그레이션 (0004, 0005), `recommendation_reason` (0009), `metrics_data_source` (0008), `KeywordCache` (0006, 0007)
- BE: DashboardView raw_value/change_pct/fiscal_label/quarterly_history/comparison_type 필드 응답
- BE: IndicatorReadingsView (FMP fallback 포함)
- BE: 분기 지표 fetcher + RATIO_METRICS % 변환
- BE: 대화형 빌더 4개 엔드포인트 (start/respond/news-issues/suggest)
- FE: Phase 2 라우팅 7개 (`/thesis`, `/thesis/alerts`, `/thesis/new`, `/thesis/[id]`, `/thesis/[id]/indicators`, `/thesis/[id]/close`)
- FE: 41개 컴포넌트 (builder 9 + dashboard 10 + indicators 3 + list 3 + alerts 3 + close 2 + common 6 + skeleton 1 + AddIndicatorSheet/IndicatorCard/PresetSelector 3 루트 컴포넌트)
- FE: authAxios 단일 소스, JWT 인터셉터, mock 모드, TanStack Query v5
- FE: Phase 3-Redesign PR-7~9 산출물 (RealValueIndicatorCard, AISummarySection, NotableChangesSection, ChartToggleButton, PeriodSelector, IndividualMiniCharts, QuarterlySparkline)

### (B) 부분 구현
- BE 모델 `HypothesisEvent`, `ValidityRecord`, `InvestorDNA` (정의됨, **이벤트 기록 hook 분포는 미검증**)
- talking_builder Phase B Keywords (`KeywordCache` 모델 존재, UI/E2E 미검증)
- `ThesisSnapshot.ai_summary` (필드는 존재, 채움 로직 부재)
- `notable_changes` (단순 delta 필터만, AI 풍부화 부재)

### (C) 미구현
- **Phase 3-Redesign PR-10**: `generate_thesis_summaries` Celery + Beat 등록 + Gemini 동기 호출 + `ai_summary` 채움 + `notable_changes` 풍부화
- **CLAUDE.md/Phase2 summary FE-PR-7**: 대시보드 3탭 구조 + 전제 CRUD UI
- **CLAUDE.md/Phase2 summary FE-PR-8**: Finviz 히트맵 + 지표 weight/direction 인라인 편집
- **CLAUDE.md/Phase2 summary FE-PR-9**: 히스토리 탭 (recharts + 스냅샷 타임라인) + 백엔드 스냅샷 시계열 API
- **CLAUDE.md/Phase2 summary FE-PR-10**: 마감 아카이브 + `ValidityMatrix` UI
- **CLAUDE.md/Phase2 summary FE-PR-11**: 투자자 DNA 프로필 페이지 + `AccuracyRing`/`CategoryChart` + DNA 조회 API
- **통합 로드맵 Phase 2**: `ValidityScore` 모델, 주 1회 집계 태스크, 추천에 유효성 반영, DNA 슬라이더, 역제안, 상관할인, Adaptive Decay, Sustained Extreme, 뉴스 센티먼트
- **통합 로드맵 Phase 3**: `SyntheticBootstrapper`, `ThesisWeightLearner` (Online LR), `ValidityRecord.is_synthetic`, blending policy
- **통합 로드맵 Phase 4**: 벡터화, DNA 16d 벡터, 유효성 6d 벡터, 코사인 유사도 추천

### (D) 폐기/대체
- **PR 번호 체계 충돌**: Phase 3-Redesign (PR-7~10) ↔ Phase2 summary (FE-PR-7~11). 현재 코드에 안착한 것은 전자(Redesign) 체계이며 후자는 아직 진행 안 됨. 두 체계가 같은 번호를 다른 의미로 쓰므로 **차후 PR 번호 재정의 권고** (예: 후자를 FE-PR-12~16으로 리넘버).
- **단일 화면 대시보드 vs 3탭 대시보드**: 현재 `[thesisId]/page.tsx`는 PR-5의 단일 스크롤 화면이며, FE-PR-7이 요구한 3탭 구조는 적용되지 않음. 만약 단일 화면이 최종 결정이라면 FE-PR-7 폐기 검토 필요.

---

## 결론 및 우선순위 권고 (감사관 의견)

1. **즉시 매워야 하는 갭**: Phase 1 이벤트 기록 hook이 실제로 코드에 삽입되어 있는지 확인. 누락 시 Phase 2/3 학습 레이어가 데이터 없이 시작됨 (Cold Start 악화). → 별도 hook 분포 audit 권고.
2. **사용자 화면 영향 가장 큰 갭**: PR-10 (AI 모니터링 파이프라인). FE는 이미 `AISummarySection`을 렌더링하지만 백엔드가 빈 문자열만 반환하므로 사용자 가치 미실현.
3. **CLAUDE.md 표기와 코드 정합성 갭**: CLAUDE.md "Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11) 진행 중" 표기는 **미시작**과 동의어. 실제로는 PR-10 단일 항목이 진행 중인 것으로 표기 수정 권고.
4. **장기 로드맵 (Phase 2~4)** 은 모두 모델 단계조차 미진입. 특허 청구항 (DNA, 적응형 유효성 학습, 합성 에이전트, 벡터 스코어링) 중 Phase 1 이벤트 인프라만 구현된 상태.

---

## 부록: 원시 매핑 표

### 백엔드 파일 인벤토리
```
thesis/models/        community.py, indicator.py, keyword.py, learning.py, monitoring.py, thesis.py
thesis/views/         conversation_views.py, monitoring_views.py, thesis_views.py
thesis/services/      alert_engine.py, arrow_calculator.py, builder_events.py, builder_state.py,
                      data_validator.py, indicator_matcher.py, indicator_scorer.py, keyword_cache.py,
                      keyword_collectors/, keyword_hint.py, llm_postprocess.py, premise_aggregator.py,
                      prompt_builder.py, quarterly_metric_fetcher.py, snapshot_builder.py,
                      thesis_builder.py, thesis_state_machine.py
thesis/serializers/   conversation_serializers.py, indicator_serializers.py,
                      monitoring_serializers.py, thesis_serializers.py
thesis/tasks/         eod_pipeline.py
thesis/migrations/    0001_initial → 0009_add_recommendation_reason (총 9개)
```

### 프론트엔드 파일 인벤토리
```
frontend/app/thesis/
  layout.tsx
  (list)/layout.tsx, (list)/page.tsx, (list)/alerts/page.tsx
  new/page.tsx
  [thesisId]/page.tsx, [thesisId]/indicators/page.tsx, [thesisId]/close/page.tsx

frontend/components/thesis/
  AddIndicatorSheet.tsx, IndicatorCard.tsx, PresetSelector.tsx, index.ts
  alerts/   AlertCard, AlertFilterTabs, EmptyAlerts (3)
  builder/  BottomSheet, ChatBubble, MultiSelectFooter, NewsSelector, OptionButton,
            PremiseCard, ProgressBar, SuggestionCard, TextInput (9)
  close/    CloseConfirmDialog, OutcomeSelector (2)
  common/   AlertBell, ArrowIndicator, BottomSheet, IndicatorCard, MoonPhase, ThesisBadge (6)
  dashboard/ AISummarySection, ChartToggleButton, DashboardHeader, DashboardPageHeader,
             IndicatorRow, IndividualMiniCharts, NotableChangesSection, PeriodSelector,
             QuarterlySparkline, RealValueIndicatorCard (10)
  indicators/ AddIndicatorSheet, IndicatorSetupCard, RecommendCard (3)
  list/     EntryPointGrid, ThesisListCard, TodayChangeCard (3)
  skeleton/ ThesisSkeleton (1)
```

### 부재 확인된 파일 (CLAUDE.md/Phase2 summary FE-PR-7~11 기준)
```
✗ frontend/app/thesis/[thesisId]/(detail)/page.tsx     — FE-PR-7 상세탭
✗ frontend/app/thesis/[thesisId]/history/page.tsx       — FE-PR-9 히스토리탭
✗ frontend/app/thesis/(list)/archive/page.tsx           — FE-PR-10 아카이브
✗ frontend/app/profile/dna/page.tsx                     — FE-PR-11 DNA 프로필
✗ frontend/components/thesis/dashboard/IndicatorHeatmap.tsx — FE-PR-8 Finviz 히트맵
✗ frontend/components/thesis/history/* (디렉토리 자체 부재)
✗ frontend/components/thesis/profile/* (디렉토리 자체 부재)
✗ frontend/components/thesis/archive/* (디렉토리 자체 부재)
```

### 부재 확인된 백엔드 항목
```
✗ thesis/models/learning.py: ValidityScore (Phase 2 집계 테이블)
✗ thesis/models/learning.py: ValidityRecord.is_synthetic (Phase 3 합성 구분)
✗ thesis/models/                                      ThesisRetrospective (회고 모델 — 어디에도 부재)
✗ thesis/services/synthetic_bootstrapper.py           (Phase 3 합성 에이전트)
✗ thesis/services/thesis_weight_learner.py            (Phase 3 Online LR)
✗ thesis/services/validity_aggregator.py              (Phase 2 ValidityScore 집계)
✗ thesis/services/dna_personalizer.py                 (Phase 2 DNA 슬라이더 + 역제안)
✗ thesis/tasks/eod_pipeline.py: generate_thesis_summaries (PR-10 AI 요약)
✗ thesis/tasks/                aggregate_validity_scores (Phase 2 주 1회 집계)
✗ thesis/views/                RetrospectiveView, DNAProfileView, SnapshotHistoryView (FE-PR-9~11 의존)
```
