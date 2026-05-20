# Thesis Control 설계 갭 감사

> 작성일: 2026-05-20
> 대상: `docs/thesis_control/` 설계 문서 vs `thesis/` 백엔드 + `frontend/components/thesis/` 프론트엔드
> 모드: 읽기 전용 (코드 변경 없음)
> 분류 기준: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 요약 (Phase별 구현률)

| Phase | 영역 | 설계 항목 수 | 구현률 | 비고 |
|-------|------|------------|--------|------|
| **Phase 1 (MVP) — 관제 엔진** | Stage 0~3 + 스냅샷 | 5 | **A** (100%) | v2.3.2 핵심 전부 가동 (Stage 0 validator, Stage 1 robust Z+decay, Stage 2 weighted, Stage 3 state) |
| **Phase 1 — 이벤트/유효성** | HypothesisEvent, ValidityRecord, InvestorDNA | 3 | **A** (100%) | 모델 + view 트리거 + InvestorDNA 자동 갱신 동작 (`thesis_views.py:55,92,107,166,180,215,259,297`) |
| **Phase 2 — 유효성 활성화** | ValidityScore, DNA 슬라이더, 역제안, 상관할인 | 4 | **C** (0%) | 모델/서비스/태스크 모두 부재 — `personalization_weight` 필드만 placeholder로 존재 |
| **Phase 3 (원안) — 깊이+회고+프로필 (FE-PR-7~11)** | 탭 구조, 히트맵, 히스토리, 아카이브, DNA 프로필 | 5 | **D** (폐기) | `thesis_control_phase3_frontend_redesign.md`에서 명시적으로 **대체 결정** |
| **Phase 3 (재설계) — 대시보드 리디자인 (PR-7~10)** | display_unit, raw_value, 미니차트, AI summary 파이프라인 | 4 | **A~B** (~90%) | PR-7/PR-8/PR-10 완전 구현. PR-9 차트는 IndicatorRow 토글 방식으로 변형 |
| **Phase 3 — 합성 에이전트 + Online LR** | SyntheticBootstrapper, is_synthetic, ThesisWeightLearner | 3 | **C** (0%) | 미구현 |
| **Phase 4 — 벡터 스코어링** | DNA 벡터, 유효성 벡터, 코사인 유사도 | 4 | **C** (0%) | 미구현 (의도된 미래 작업) |
| **빌더 재설계 (Phase A~C)** | One-shot LLM proposal, KeywordCache, MiniDashboardPreview | 3 | **A~B** (~70%) | Phase A-MVP/Hardening + Phase B Keyword 완료, Phase C는 미구현 |

**총평**: 설계서가 명시한 Phase 1 (관제 엔진 + 이벤트 수집)와 Phase 3 리디자인(대시보드 + AI 요약)은 거의 완전 구현되었음. Phase 2(유효성 활성화), Phase 3(합성 에이전트), Phase 4(벡터)는 **모델 placeholder만 존재**하고 비즈니스 로직 부재. 원안 FE-PR-7~11(탭/히트맵/히스토리/아카이브/DNA 프로필)은 Phase 3 재설계 채택으로 **공식 폐기**.

---

## 문서별 상태 테이블

### 백엔드 설계 문서

| 문서 | 핵심 항목 | 분류 | 구현 위치 / 근거 |
|------|---------|------|---------------|
| `thesis_control_design.md` | Thesis/ThesisPremise/ThesisIndicator/IndicatorReading/ThesisSnapshot/ThesisAlert 모델 | A | `thesis/models/{thesis,indicator,monitoring}.py` |
| `thesis_control_design.md` §3.4 세 가지 뷰 (카드/히트맵/그래프) | 히트맵·그래프 뷰 | **D 또는 C** | Phase 3 재설계에서 카드뷰 단일화. 히트맵·그래프 미구현 |
| `thesis_control_design.md` §3.5 모바일 제스처 (롱프레스/스와이프/쉐이크) | 6종 제스처 | **C** | builder에 Long-press 일부 있으나 대시보드 제스처 미구현 |
| `thesis_control_implementation_guide.md` | 구현 가이드 (Celery 3 task) | A | `thesis/tasks/` (`eod_pipeline`, `summary`) — eod_pipeline이 update→score→snapshot 통합 |
| `thesis_control_integrated_roadmap.md` Phase 1 | 관제 엔진 + Event + Validity + DNA | A | `thesis/models/learning.py` + `thesis/views/thesis_views.py` |
| `thesis_control_integrated_roadmap.md` Phase 2 | ValidityScore + DNA 슬라이더 + 역제안 | C | 모델/서비스/UI 부재 |
| `thesis_control_integrated_roadmap.md` Phase 3 (특허) | SyntheticBootstrapper + Online LR + 블렌딩 | C | 미구현 |
| `thesis_control_integrated_roadmap.md` Phase 4 | 벡터화 + 코사인 유사도 | C | 미구현 |
| `thesis_control_math_model_final.md` | Stage 0~3 수학 정의 | A | `thesis/services/{data_validator,indicator_scorer,premise_aggregator,thesis_state_machine}.py` |

### 프론트엔드 설계 문서

| 문서 | PR | 분류 | 구현 위치 / 근거 |
|------|-----|------|---------------|
| `thesis_control_phase1_frontend_FE_PR_1.md` | FE-PR-1 라우팅 + 공통 컴포넌트 | A | 8개 라우트 + `components/thesis/common/*` (AlertBell/ArrowIndicator/BottomSheet/IndicatorCard/MoonPhase/ThesisBadge) |
| `thesis_control_phase1_frontend_FE_PR_2.md` | FE-PR-2 가설 목록 | A | `app/thesis/(list)/page.tsx` + `components/thesis/list/{EntryPointGrid,ThesisListCard,TodayChangeCard}.tsx` |
| `thesis_control_phase1_frontend_FE_PR_3.md` | FE-PR-3 대화형 빌더 | A | `app/thesis/new/page.tsx` + `components/thesis/builder/*` (9 컴포넌트) |
| `thesis_control_phase1_frontend_FE_PR_4.md` | FE-PR-4 지표 설정 | A | `app/thesis/[thesisId]/indicators/page.tsx` + `components/thesis/indicators/*` |
| `thesis_control_phase1_frontend_FE_PR_5.md` | FE-PR-5 대시보드 (달위상+화살표) | **D** | Phase 3 재설계로 대체. `OverallMoon`/`DashboardIndicatorCard`/`RecentChange`는 삭제됨 (대시보드 디렉터리에 부재) |
| `thesis_control_phase1_frontend_FE_PR_5.md` | MoonPhase (common) | B | 파일은 잔존 (`components/thesis/common/MoonPhase.tsx`) — 대시보드 메인 흐름에서는 미사용 (잔여 import 정리 누락 가능성) |
| FE-PR-6 알림 + 마감 | 알림 카드/필터, 마감 다이얼로그 | A | `components/thesis/alerts/*` + `components/thesis/close/*` |
| `Phase2_completion_summary.md` §8 원안 FE-PR-7~11 | 탭/히트맵/히스토리/아카이브/DNA 프로필 | **D** | Phase 3 재설계 결정으로 폐기 (아래 상세) |
| `thesis_control_phase3_frontend_redesign.md` PR-7 | 백엔드 display_unit + IndicatorReadingsView | A | `thesis/models/indicator.py:73` (display_unit), `thesis/views/monitoring_views.py:260` (IndicatorReadingsView), `thesis/urls.py:32` |
| `thesis_control_phase3_frontend_redesign.md` PR-8 | RealValueIndicatorCard + AISummarySection + NotableChangesSection | A | 세 컴포넌트 모두 `components/thesis/dashboard/` 존재. 단 대시보드 페이지는 `RealValueIndicatorCard` 대신 `IndicatorRow`로 진화 |
| `thesis_control_phase3_frontend_redesign.md` PR-9 | ChartToggleButton + PeriodSelector + IndividualMiniCharts | B | 3개 컴포넌트 모두 존재. 그러나 대시보드 메인은 IndicatorRow 내부 `QuarterlySparkline` + 토글 차트로 통합되어 별도 토글 패턴 미사용 |
| `thesis_control_phase3_frontend_redesign.md` PR-10 | AI summary 파이프라인 (Celery task) | A | `thesis/tasks/summary.py:79` `generate_thesis_summaries` 동기 Gemini 호출 |

### 빌더 재설계 문서 (`plan/talking_builder/`)

| 문서 | 분류 | 근거 |
|------|------|------|
| `llm_builder_plan.md` (원안) | D | `redesign_build_plan/`으로 진화 |
| `thesis_builder_redesign_v2.md` (v2) | D | v4로 진화 |
| `redesign_build_plan/00_total_plan.md` Phase A-MVP | A | `work_done/phase_a_llm_builder.md` 완료 보고 |
| `redesign_build_plan/02_phase_a_hardening.md` | A | `work_done/phase_a_llm_builder.md` PR-4~7 완료 |
| `redesign_build_plan/03_phase_b_keywords.md` (KeywordCache + collectors) | A | `thesis/services/keyword_cache.py`, `keyword_hint.py`, `keyword_collectors/{chain,eod,news}.py` 존재 |
| `redesign_build_plan/04_phase_c_advanced.md` (MiniDashboard, Guided Suggestion, 스트리밍) | C | 컴포넌트/서비스 부재 |
| `quarterly_indicator_dashboard_plan.md` | A | `thesis/services/quarterly_metric_fetcher.py` + `components/thesis/dashboard/QuarterlySparkline.tsx` |

---

## Phase 3 미구현 항목 상세

### A. 원안 FE-PR-7~11 (공식 폐기 / 분류 D)

`Phase2_completion_summary.md` §8 — 폐기 사유: `thesis_control_phase3_frontend_redesign.md` §0.1에서 "내부 점수(MoonPhase, 화살표 각도) 추상화를 실세계 값 노출로 전환"하기로 결정. 아래 5개 PR은 모두 **이 결정에 따라 폐기**됨.

| PR | 원안 산출물 | 폐기 사유 |
|----|------------|----------|
| FE-PR-7 | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD | 단일 페이지 + 실값 노출로 단순화 |
| FE-PR-8 | Finviz 스타일 히트맵 + 지표 weight/direction 편집 | 원칙 충돌 (내부 점수 숨김) — 카드뷰만 유지 |
| FE-PR-9 | recharts 라인 차트 + 스냅샷 타임라인 (히스토리 탭) | 지표별 미니차트(IndividualMiniCharts/QuarterlySparkline)로 대체 |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix 시각화 | 미구현. 마감 자체는 `close/page.tsx`에 있으나 아카이브 페이지·ValidityMatrix UI 없음 |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | 백엔드 InvestorDNA는 갱신되지만 **프론트 UI 전혀 없음** |

### B. Phase 3 재설계 (PR-7~10) 부분 갭

| 항목 | 분류 | 상세 |
|------|------|------|
| PR-7 backend display_unit + IndicatorReadingsView | A | `monitoring_views.py:112,135,287` 모두 실값/단위/IndicatorReadingsView 구현 |
| PR-8 RealValueIndicatorCard | **B** | 컴포넌트 파일은 존재 (`RealValueIndicatorCard.tsx`)하지만 실제 대시보드 페이지(`app/thesis/[thesisId]/page.tsx:114`)는 `IndicatorRow`를 사용. 잔존 사용처 없으면 **dead code 가능성** |
| PR-8 AISummarySection | A | `app/thesis/[thesisId]/page.tsx:75` 사용 중 |
| PR-8 NotableChangesSection | A | 같은 파일 line 81 사용 중 |
| PR-9 ChartToggleButton + PeriodSelector + IndividualMiniCharts | **B** | 3개 컴포넌트 파일은 존재하나 대시보드 페이지에서는 import/렌더링되지 않음. IndicatorRow가 자체 토글 차트(QuarterlySparkline + readings AreaChart)를 내장하여 별도 토글 섹션을 흡수함. **컴포넌트 잔존 = dead code 후보** |
| PR-10 generate_thesis_summaries Celery task | A | `thesis/tasks/summary.py` Gemini 2.5 Flash 동기 호출 + idempotent skip + force 옵션 구현 |
| PR-10 notable_changes snapshot_builder 연동 | **B** | `snapshot_builder.py:105~157`에서 score 변화 |Δ|≥0.3 룰로 생성. 단, 설계서가 명시한 `alert_engine` 이벤트(direction_flip/sharp_move/extreme_volatility) 재활용 방식이 아닌 **자체 score-diff 룰**로 구현됨 (사양 vs 구현 차이) |

### C. 통합 로드맵 Phase 2 (DNA 슬라이더 + 유효성 활성화) — 전부 미구현

| 항목 | 분류 | 비고 |
|------|------|------|
| `ValidityScore` 모델 | C | 부재 |
| 주 1회 ValidityRecord→ValidityScore 집계 Celery task | C | 부재 |
| `indicator_matcher` 유효성 부스트 + tier 분류 (core/reference/low_impact) | C | `indicator_matcher.py` 존재하나 keyword 룰 기반, validity_boost 미연결 |
| DNA 적합도 슬라이더 (`personalization_weight`) | C | 필드만 존재 (`learning.py:124`), 슬라이더 UI/적용 로직 없음 |
| Contrarian Nudge (역제안) | C | 부재 |
| 상관계수 60일 자동 할인 (1/√k) | C | 부재 |
| Adaptive Decay/Window (변동성 기반) | C | scoring 모듈에 고정 파라미터만 |
| Sustained Extreme 룰 | C | state_machine에 부재 |
| 뉴스 센티먼트 → Stage 1 입력 | C | 부재 |

### D. 통합 로드맵 Phase 3 특허 기능 — 전부 미구현

| 항목 | 분류 | 비고 |
|------|------|------|
| SyntheticBootstrapper + 20~30개 페르소나 | C | 부재 |
| `ValidityRecord.is_synthetic` 필드 | C | 모델에 미존재 (`learning.py:55-94` 확인) |
| Online Logistic Regression (`ThesisWeightLearner`) | C | 부재 |
| 합성/실제 데이터 블렌딩 (`blend_ratio`) | C | 부재 |

### E. 통합 로드맵 Phase 4 벡터 — 미구현 (의도된 미래)

| 항목 | 분류 |
|------|------|
| DNA 16차원 벡터화 | C |
| 6차원 ValidityVector | C |
| 코사인 유사도 추천 | C |
| 사용자 유사도 (협업 필터링) | C |

### F. 원안 디자인 §3 모니터링 단계 미구현 항목

| 항목 | 분류 | 비고 |
|------|------|------|
| 히트맵 뷰 | C/D | Phase 3 재설계로 폐기 |
| 그래프 뷰 (Y축 없는 흐름선) | C/D | Phase 3 재설계로 폐기. IndicatorRow의 readings 차트로 대체 |
| 모바일 제스처 (롱프레스 상세차트/좌우 스와이프/상하 스와이프/쉐이크) | C | 빌더에만 일부 구현, 대시보드 부재 |
| 가설 마감 복기 화면 (정성적 회고 — "가장 유용했던 지표/예상과 달랐던 부분") | C | `close/page.tsx`는 outcome 선택만, 복기 페이지 없음 |
| 변화 감지 알림 + 반대 방향 변화 대화 ("이 전제를 다시 생각해볼까요?") | C | AlertCard는 단순 list, 대화형 재검토 UX 없음 |

---

## 추가 발견 사항

1. **잠재적 Dead Code 후보 (검증 필요)**
   - `components/thesis/dashboard/RealValueIndicatorCard.tsx` — `page.tsx`는 `IndicatorRow`로 통합됨
   - `components/thesis/dashboard/ChartToggleButton.tsx`, `PeriodSelector.tsx`, `IndividualMiniCharts.tsx` — 대시보드 메인에서 import 없음
   - `components/thesis/common/MoonPhase.tsx` — Phase 3 재설계 §2에서 "다른 곳 미사용이면 삭제" 지시되었으나 파일 존재

2. **사양 ↔ 구현 차이 (PR-10 notable_changes)**
   - 설계: `alert_engine` 이벤트(direction_flip/sharp_move/extreme_volatility) 변환
   - 구현: `snapshot_builder.py`에서 score 변화 |Δ|≥0.3 룰 자체 계산
   - → 두 방식이 다른 이벤트 집합을 산출할 가능성. 의도된 단순화인지 누락인지 확인 필요

3. **DECISIONS 동기화 권장**
   - 원안 FE-PR-7~11 → 폐기 결정이 `thesis_control_phase3_frontend_redesign.md` 내부 문서에만 있고 `Phase2_completion_summary.md`는 여전히 폐기된 원안을 "계획"으로 명시 → DECISIONS.md 또는 Phase2 요약서 후속 문구 갱신 필요

4. **Phase 2 진입 조건 미충족**
   - 통합 로드맵은 "가설 마감 10건+ 축적 후 Phase 2 진입"을 명시. 현재 ValidityRecord 축적량 미확인. Phase 2 시작 전 데이터 확보 게이트 점검 필요

---

## 부록: 핵심 구현 경로 인덱스

| 기능 | 파일·라인 |
|------|----------|
| Stage 0 Validator | `thesis/services/data_validator.py` |
| Stage 1 Scoring | `thesis/services/indicator_scorer.py` |
| Stage 2 Aggregation | `thesis/services/premise_aggregator.py` |
| Stage 3 State Machine | `thesis/services/thesis_state_machine.py` |
| Snapshot Builder | `thesis/services/snapshot_builder.py:105-157` |
| Alert Engine | `thesis/services/alert_engine.py` |
| Event 기록 | `thesis/views/thesis_views.py:55,107,166,180,215,259` |
| ValidityRecord 생성 | `thesis/views/thesis_views.py:85-103` |
| InvestorDNA 갱신 | `thesis/views/thesis_views.py:296-330` |
| display_unit 필드 | `thesis/models/indicator.py:73` |
| IndicatorReadingsView | `thesis/views/monitoring_views.py:260` |
| AI 요약 Celery task | `thesis/tasks/summary.py:79-142` |
| EOD 파이프라인 | `thesis/tasks/eod_pipeline.py` |
| 대시보드 메인 페이지 | `frontend/app/thesis/[thesisId]/page.tsx` |
| IndicatorRow (실제 사용 카드) | `frontend/components/thesis/dashboard/IndicatorRow.tsx` |
| QuarterlySparkline | `frontend/components/thesis/dashboard/QuarterlySparkline.tsx` |
| 빌더 LLM 서비스 | `thesis/services/thesis_builder.py`, `prompt_builder.py`, `llm_postprocess.py` |
| KeywordCache + collectors | `thesis/services/keyword_cache.py`, `keyword_collectors/{chain,eod,news}.py` |
