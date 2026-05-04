# Thesis Control 설계 갭 감사

> 감사 일자: 2026-05-05
> 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` 백엔드 + `frontend/{components,app,lib}/thesis/` 구현
> 본 보고서는 **읽기 전용 감사**입니다. 코드 변경 없음.
> 분류: **(A)** 완전 구현 / **(B)** 부분 구현 / **(C)** 미구현 / **(D)** 폐기·대체

---

## 0. 사전 컨텍스트 — "Phase 3"의 다중 정의 (재확인)

`docs/thesis_control/` 안에서 "Phase 3"이라는 용어는 **세 문서에서 서로 다른 산출물을 가리킨다.** 본 감사는 세 정의를 모두 평가한다.

| 문서 | "Phase 3"의 의미 | 현재 진행 |
|---|---|---|
| `frontend/task_done/Phase2_completion_summary.md` (2026-03-16) §3 | **FE-PR-7~11**: 대시보드 3탭 / 히트맵 / 히스토리 / 마감 아카이브 / 투자자 DNA 프로필 | **거의 미시작 (C)**, 사실상 폐기 가능성 |
| `plan/thesis_control_phase3_frontend_redesign.md` (2026-03-18, FINAL) | **PR-7~10**: BE raw_value 확장 / 실제값 카드 / 미니차트 / AI 모니터링 파이프라인 | **PR-7~9 완료 (A), PR-10 미구현 (C)** |
| `plan/thesis_control_integrated_roadmap.md` §3 | 합성 에이전트 / Online LR / 가설 복기 / Neo4j 가설 관계 / 커뮤니티(인기·템플릿·Chain Sight) | **거의 미시작 (C)** |

**해석**: redesign 문서가 원안 FE-PR-7~11을 사실상 재정의했으나 공식 폐기 선언이 없어, CLAUDE.md / MEMORY.md / Phase2_summary 표기가 현실과 불일치하는 상태. 실제 진행 중인 항목은 redesign PR-10 단일 산출물(그조차 미시작)이다.

### 5월 3일 → 5월 4일 변동

`git log -- thesis/ frontend/{components,app,lib}/thesis/ docs/thesis_control/` 결과 **5월 3일 ~ 5월 4일 사이 thesis 영역 신규 커밋 0건**, working tree 변경 0건. 마지막 thesis 영역 커밋은 4월 27일 `b3b9bdf` (FMP Starter rate_limit + indicator_catalog 표시 이름 4건 BE/FE 통일). **갭 분포는 5월 3일과 동일하며**, 본 감사는 직접 코드 재검증을 통해 사실 일치를 확인했다 (§5).

---

## 1. 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 등급 |
|-------|------|--------|------|
| Phase 1 — 관제 엔진 (수학 모델 v2.3.2) | Stage 0~3 + Celery 3태스크 + 스냅샷 + 알림 throttling | 95% | **A** |
| Phase 1 — 이벤트/유효성 인프라 | `HypothesisEvent` / `ValidityRecord` / `InvestorDNA` 모델 + 비즈니스 hook | 90% | **A** |
| Phase 2 (BE) — Builder API | conversation start/respond + news-issues + suggest + LLM proposal 모드 | 100% | **A** |
| Phase 2 (FE) — Routing/Common (FE-PR-1) | 라우팅 7개 + common 5개 + authAxios 단일 소스 | 100% | **A** |
| Phase 2 (FE) — Thesis List (FE-PR-2) | `ThesisListCard` / `EntryPointGrid` / `TodayChangeCard` | 100% | **A** |
| Phase 2 (FE) — Builder (FE-PR-3) | 6단계 wizard + LLM one-shot proposal + Mock | 100% | **A** |
| Phase 2 (FE) — Indicator Setup (FE-PR-4) | `IndicatorSetupCard` / `AddIndicatorSheet` / `RecommendCard` | 100% | **A** |
| Phase 2 (FE) — Dashboard (FE-PR-5) | 관제실 단일 화면 — `OverallMoon`/`DashboardIndicatorCard`/`RecentChange`는 redesign에서 폐기 | 80% | **A** (redesign에 흡수) |
| Phase 2 (FE) — Alerts/Close (FE-PR-6) | 알림 3탭 + Outcome 선택 + Close Confirm | 100% | **A** |
| **Phase 3-Redesign — PR-7~9** | 실제값 카드 + AI 분석 슬롯 + 미니차트 + 분기 지표 | 100% | **A** |
| **Phase 3-Redesign — PR-10** | AI 모니터링 파이프라인 (Celery `generate_thesis_summaries`) | 0% | **C** |
| **Phase 3 (Phase2_summary 정의) — FE-PR-7~11** | 탭 / 히트맵 / 히스토리 / 아카이브 / DNA 프로필 | 0% | **C** (사실상 **D** 폐기 가능성) |
| Phase 2 (통합 로드맵) — 유효성 활성화 | `ValidityScore` / DNA 슬라이더 / 역제안 / 상관할인 / Adaptive Decay / 뉴스 센티먼트 | 0% | **C** |
| Phase 3 (통합 로드맵) — 합성 에이전트 + Online LR | `SyntheticBootstrapper` / `ThesisWeightLearner` / 블렌딩 | 0% | **C** |
| Phase 3 (통합 로드맵) — 커뮤니티 + 복기 + Neo4j | 인기 가설 / 템플릿 / Chain Sight 양방향 / 가설 마감 복기 / 가설 관계 그래프 | 0% | **C** |
| Phase 4 — 벡터 스코어링 | DNA 16d / Validity 6d / 코사인 유사도 / 사용자 유사도 | 0% | **C** |
| Phase A — LLM 빌더 (one-shot proposal) | builder_state / prompt_builder / llm_postprocess / builder_events / feature_flags | 100% | **A** |
| Phase B — Keyword Enrichment | `KeywordCache` + collectors (chain/eod/news) + keyword_hint + 운영 commands | 100% (코드) / Flag OFF | **A** (코드) / **B** (롤아웃) |
| Phase C — Advanced Builder | MiniDashboardPreview / GuidedSuggestion / Streaming / MultiTurnEdit | 0% | **C** |

세부 근거는 §2~§5 참조.

---

## 2. 문서별 상태 테이블

### 2.1 핵심 설계 문서 (`docs/thesis_control/plan/`)

| 문서 | 줄 | 핵심 산출물 | 매칭 코드 | 상태 |
|------|----|------------|----------|------|
| `thesis_control_design.md` | 1370 | 모델 / 뷰 / 서비스 / API / UX 전체 스펙 | `thesis/{models,views,services,serializers}/*` | **A** |
| `thesis_control_math_model_final.md` (v2.3.2) | 1153 | Stage 0~3 스코어링 수식 + 스냅샷 / 알림 throttling | `services/{data_validator,indicator_scorer,premise_aggregator,thesis_state_machine,arrow_calculator,snapshot_builder,alert_engine}.py` | **A** |
| `thesis_control_implementation_guide.md` | 286 | Phase 1~4 구현 로드맵 | Phase 1 일치 / Phase 2~4 미시작 | **B** |
| `thesis_control_integrated_roadmap.md` | 660 | 수학 모델 + 특허 기능 통합 (Phase 1~4) | Phase 1 일부 일치 | **B** |
| `thesis_control_phase3_frontend_redesign.md` (FINAL) | 1095 | PR-7~10 (실제값 카드 + AI + 차트 + Celery 파이프라인) | `dashboard/*.tsx`, `monitoring_views.py`, migration 0004/0005 | **B** (PR-7~9 완료, PR-10 부재) |

### 2.2 루트 문서

| 문서 | 상태 | 비고 |
|------|------|------|
| `thesis_control_user_experience.md` (2026-03-30) | **A** | 6단계 흐름 + Suggestion Mode와 일치 |
| `thesis_control_phase1_frontend_FE_PR_1~5.md` | **A** | task_done 보고서와 일치 |
| `thesis_control_phase1_frontend_prompts.md` | n/a | 프롬프트 모음 |
| `thesis_control_phase1_prompts.md` | **A** | 백엔드 BE-PR-1~5 모두 코드에 안착 |

### 2.3 빌더 v2 리디자인 (`plan/talking_builder/`)

| 문서 | 줄 | 매칭 | 상태 |
|------|----|------|------|
| `llm_builder_plan.md` | 563 | `services/{thesis_builder, llm_postprocess, builder_state, builder_events, prompt_builder}.py` | **A** |
| `thesis_builder_redesign_v2.md` | 1110 | `views/conversation_views.py`의 4개 뷰 | **A** |
| `quarterly_indicator_dashboard_plan.md` | 424 | `services/quarterly_metric_fetcher.py` + `DashboardView` 분기 응답 + `QuarterlySparkline.tsx` + `IndicatorRow.tsx` 분기 모드 | **A** |
| `redesign_build_plan/00_total_plan.md` (v4) | 525 | Phase A MVP / A Hardening / B Keywords / C Advanced 종합 | **B** |
| `redesign_build_plan/01_phase_a_mvp.md` | 287 | `work_done/phase_a_llm_builder.md` 와 일치 | **A** |
| `redesign_build_plan/02_phase_a_hardening.md` | 118 | PR-4~7 안정화 적용 | **A** |
| `redesign_build_plan/03_phase_b_keywords.md` | 299 | KeywordCache + Strength + monitoring | **A** (코드) / 운영 flag OFF |
| `redesign_build_plan/04_phase_c_advanced.md` | 144 | MiniDashboard / Guided Suggestion / Streaming | **C** |
| `redesign_build_plan/05_summary.md` | n/a | 요약 | n/a |

### 2.4 프론트엔드 task_done 보고서 (`frontend/task_done/`)

| 보고서 | 코드 일치 | 비고 |
|--------|----------|------|
| `FE-PR-1_routing_common_components.md` | **A** | 라우팅 7개 + common 5개 + `lib/api/authAxios.ts` 단일화 모두 확인 |
| `FE-PR-2_thesis_list_page.md` | **A** | `ThesisListCard` / `TodayChangeCard` / `EntryPointGrid` + USE_MOCK 분기 |
| `FE-PR-3_builder_implementation.md` (+ `FE-PR-3_plan_review_v3.md`) | **A** | 6단계 wizard 빌더 9개 컴포넌트 + Phase A LLM proposal 추가, `app/thesis/new/page.tsx` 가 1072줄로 확장 |
| `FE-PR-4_indicator_setup.md` | **A** | `IndicatorSetupCard` / `AddIndicatorSheet` / `RecommendCard` / Route Group `(list)/` 분리 |
| `FE-PR-5_dashboard.md` | **부분 폐기 (D)** | `OverallMoon` / `DashboardIndicatorCard` / `RecentChange` 는 redesign에서 삭제 명시. `RealValueIndicatorCard` / `AISummarySection` / `NotableChangesSection` 으로 교체. **단** — `app/thesis/[thesisId]/page.tsx` (실측 138줄) 본 코드 경로는 `RealValueIndicatorCard` 가 아닌 **`IndicatorRow` (인라인 토글 차트 포함)** 을 최종 사용 (L11 import, L115 render). `RealValueIndicatorCard.tsx` 는 테스트 1건만 import → 사실상 **dead UI 컴포넌트** (§6 H7) |
| `FE-PR-6_alerts_close_qa.md` | **A (불일치 1건)** | 알림/마감 컴포넌트 모두 확인. **단** — 보고서 §"이동/삭제"에서 `lib/thesis/indicatorMutations.ts → mutations.ts 통합 후 삭제` / `builder/BottomSheet → common/BottomSheet 이동` 으로 기재되어 있으나, **실제로는 두 파일 모두 잔존** (`indicatorMutations.ts` 47줄 + `mutations.ts` 85줄, `builder/BottomSheet.tsx` + `common/BottomSheet.tsx` 모두 존재) |
| `Phase2_completion_summary.md` | **부분 폐기 (D)** | §3 "Phase 3 계획 (FE-PR-7~11)" 은 2일 뒤 redesign 으로 사실상 폐기되었으나 본 보고서는 갱신되지 않음 → CLAUDE.md / MEMORY.md 에 잘못된 진척도 전파 |

### 2.5 작업 진행 보고서 (`work_done/`)

| 보고서 | 상태 |
|--------|------|
| `phase_a_llm_builder.md` (Phase A-MVP + Hardening, 2026-03-20) | **A** — 5개 신규 백엔드 파일 + 4개 프론트엔드 변경 + 테스트 104개 모두 코드와 일치 |

---

## 3. Phase 3 미구현 항목 상세

### 3.1 Phase 3-Redesign 기준 — PR-10 AI 파이프라인 (단일 미구현, 사용자 영향 최대)

설계 출처: `thesis_control_phase3_frontend_redesign.md` §7 (L923~L1095)

| 항목 | 설계 명세 | 현재 상태 (2026-05-04 검증) |
|------|----------|----------|
| Celery `generate_thesis_summaries` | 매일 07:30 KST. Stage 3 상태 + raw_value 변화 → Gemini 2.5 Flash 동기 호출 → 2~3문장 한국어 요약 | **부재** — `tasks/eod_pipeline.py` 463줄 안에 함수 미정의 (grep 결과 0건) |
| `ThesisSnapshot.ai_summary` 채움 로직 | 위 태스크가 저장 | **부재** — `services/snapshot_builder.py` (grep 결과 ai_summary 키 0건). 모델 default `''` 그대로 |
| `notable_changes` 풍부화 | alert_engine 이벤트(direction_flip / sharp_move / extreme_volatility) → `{indicator_id, type, severity, description, raw_value_before/after, change_pct}` 변환 | **부분 (B)** — `snapshot_builder.py` L105~157 의 단순 `\|delta\|≥0.3` 필터로만 채움 (`notable_changes` 변수). severity 분기 / raw_value before/after 매핑 / AI 풍부화 없음 |
| Beat schedule 등록 | DatabaseScheduler에 `PeriodicTask.objects.create(...)` (CLAUDE.md 버그 #28 회피 패턴) | **부재** |

**FE 영향**: `app/thesis/[thesisId]/page.tsx` L74~84 가 `<AISummarySection summary={data.thesis.ai_summary} ... />` 와 `<NotableChangesSection changes={data.thesis.notable_changes} ... />` 를 렌더링 트리에 두고 있으나, 응답 `ai_summary === ''` 이므로 `if (!summary) return null` 분기로 인해 **사용자 화면에서 항상 미렌더링**. → PROGRESS.md "다음 세션 #15" 와 동일 (5주째 동일 상태).

### 3.2 Phase2_summary / CLAUDE.md 기준 — FE-PR-7~11 (모두 미시작)

`Phase2_completion_summary.md` L129~L137 에 정의된 차세대 5개 PR이 어디에도 안착하지 않음.

| PR | 설계 의도 | 부재 라우트 | 부재 컴포넌트 | 백엔드 의존성 |
|----|----------|------------|--------------|--------------|
| **FE-PR-7** | 대시보드 3탭 (관제 / 상세 / 히스토리) + 전제 CRUD UI | `[thesisId]/(detail)/`, `[thesisId]/history/` 미생성. 현재 `[thesisId]/page.tsx`는 단일 스크롤 화면 (138줄) | `DashboardTabs`, `DetailTab`, `PremiseEditor` 부재 | `ThesisPremiseViewSet` 재활용 가능 (BE OK) |
| **FE-PR-8** | Finviz 스타일 히트맵 + 지표 weight/direction 인라인 편집 | (FE-PR-7 탭 내부 가정) | `IndicatorHeatmap` 부재. 단 — `monitoring_views.DashboardView` 응답에 `heatmap.cells` 가 이미 존재 (L195~204) 하나 FE 사용 안 함 → **백엔드 100% 준비, 프론트만 미사용** | `ThesisIndicator` PATCH 가능 (BE OK) |
| **FE-PR-9** | 히스토리 탭 (recharts 라인 차트 + 스냅샷 타임라인) | `[thesisId]/history/page.tsx` 부재 | `ScoreHistoryChart`, `SnapshotTimeline` 부재 | `GET /{id}/snapshots/` API **부재** (`urls.py` 에 라우트 없음) |
| **FE-PR-10** | 마감 아카이브 + ValidityMatrix 2×2 | `(list)/archive/page.tsx` 부재 | `ArchiveList`, `ValidityMatrix2x2`, `RetrospectiveCard` 부재 | `Thesis.status='closed'` 필터는 가능. 마감 시 `ValidityRecord` 자동 생성은 **이미 작동**(§5 검증) |
| **FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `/thesis/profile`, `/profile/dna` 부재 | `AccuracyRing`, `CategoryChart`, `DNADashboard` 부재 | `InvestorDNA` 모델 + 자동 갱신 hook 은 **이미 작동**. **단** — DNA 조회 API (`GET /users/me/dna/` 등) 미정의 |

### 3.3 통합 로드맵 §2 — Phase 2 활성화 (선행 작업 누락)

| 항목 | 설계 (`integrated_roadmap.md` §2) | 현재 상태 |
|------|-----------------------------------|----------|
| `ValidityScore` 모델 (집계 테이블) | `(thesis_type, indicator_data_key, market_regime)` unique + cumulative_score / sample_count / confidence / is_active | **부재** |
| Celery 주 1회 `aggregate_validity_scores` | ValidityRecord → ValidityScore 집계 | **부재** |
| 지표 추천에 유효성 점수 반영 | `match_indicators()` 가 `validity_boost` 계산 → core / reference / low_impact 티어 | **부재** — 현재 키워드 룰 + LLM 매칭만 |
| DNA 적합도 슬라이더 | `apply_dna_personalization(...)` (0~1 블렌딩) | **부재** (`InvestorDNA.personalization_weight` 필드만 존재) |
| 역제안 (Contrarian Nudge) | `add_contrarian_nudge(...)` 안 쓰는 indicator_type 1개 | **부재** |
| 상관계수 자동 할인 | 60일 \|ρ\|≥0.9 → 1/√k | **부재** |
| Adaptive Decay/Window | 변동성 → λ↓, window↓ | **부재** (고정 epsilon=0.0001, window=60, decay=0.95) |
| Sustained Extreme alert subtype | s_decayed≥3 (clip 전) | **부재** (`extreme_volatility` 단일 타입만) |
| 뉴스 센티먼트 → Stage 1 입력 | `news/` SentimentHistory 를 indicator로 통합 | **부재** |

### 3.4 통합 로드맵 §3 — Phase 3 (합성 에이전트 + 자동학습)

| 항목 | 설계 명세 | 현재 상태 |
|------|----------|----------|
| `SyntheticBootstrapper` | 20~30개 페르소나로 과거 시장 데이터 기반 합성 가설 → ValidityScore 사전 채움 (Cold Start 해결, 특허 핵심 차별점) | **부재** |
| `ThesisWeightLearner` (Online LR + L2) | 마감된 가설로 전제 가중치 학습 | **부재** |
| `ValidityRecord.is_synthetic` 필드 | 합성/실제 데이터 구분 | **부재** (모델 필드 미정의) |
| `aggregate_validity_scores(blend_ratio=0.3)` | 실제 sample 늘면 자동 비중 감소 | **부재** |
| Online LR 주간 재학습 Celery + Safety Gate | 일요일 새벽, `should_deploy_weights()` | **부재** |

### 3.5 통합 로드맵 §3 — 커뮤니티 + 복기 + Neo4j

| 항목 | 설계 명세 | 현재 상태 |
|------|----------|----------|
| 인기 가설 시스템 | `GET /popular/`, `POST /popular/{id}/follow/`, `update_popular_thesis_cache` Celery | **부재** (`PopularThesisCache` 모델만 존재) |
| 템플릿 시스템 | `GET /templates/`, `GET /templates/{type}/` (이벤트형/추세형/비교형/괴리형) | **부재** |
| Chain Sight ↔ Thesis 양방향 진입점 | `entry_source='chainsight'` 진입 경로 | **부재** (enum choice 등록만, UI/로직 없음) |
| 가설 마감 복기 시스템 | "유용했던 지표 / 예상과 달랐던 부분" 분석 | **부재** (close 페이지는 outcome 선택만 받음) |
| Neo4j 가설 관계 그래프 | `SIMILAR_TO`, `OPPOSITE_OF`, `HAS_PREMISE` 관계 | **부재** |

### 3.6 통합 로드맵 §4 — Phase 4 (벡터 스코어링)

| 항목 | 현재 상태 |
|------|----------|
| DNA 프로파일 16d 벡터화 | **부재** |
| 유효성 6d 벡터화 (directional_accuracy / magnitude_sensitivity / timing_relevance / regime_stability / user_consensus / decay_rate) | **부재** |
| 코사인 유사도 기반 추천 | **부재** |
| 사용자 유사도 ("나와 비슷한 투자자") | **부재** |
| 반대 가설 자동 생성 / 과거 유사 상황 검색 / Change Point Detection / 칼만 필터 | **부재** |

### 3.7 폐기·대체된 항목 (D) — 잔재 정리 미완료

| 폐기/대체 | 대체 산출물 | 잔재 | 권고 |
|------|------|------|------|
| `OverallMoon.tsx` (대시보드 달 위상) | redesign에서 삭제 명시 | `common/MoonPhase.tsx` 잔존 ((list)/page.tsx + `ThesisListCard.tsx` 가 가설 목록 카드에서만 사용) | 관제실에서는 폐기, 가설 목록에서는 유지 — 의도된 분기인지 확인 필요 |
| `DashboardIndicatorCard.tsx` (화살표 + 트렌드) | `RealValueIndicatorCard.tsx` (정의만) → **실제 사용은 `IndicatorRow.tsx`** | `ArrowIndicator.tsx` 잔존 (관제실 비사용) / `RealValueIndicatorCard.tsx` 잔존 (테스트만 import) | dead UI 컴포넌트 — 삭제 또는 사용 결정 |
| `RecentChange.tsx` (내러티브 텍스트) | `NotableChangesSection.tsx` (구조화 변화 목록) | 삭제 완료 | — |
| `scoreToPhaseMeta()` 유틸 | redesign §10에서 "삭제 가능" 명시 | **`utils.ts` 잔존** + `(list)/page.tsx` / `ThesisListCard.tsx` / `index.ts` / `MoonPhase.tsx` 5개 파일에서 참조 중 | 가설 목록 달 위상 표현이 살아 있어 삭제 시 회귀 위험 — redesign 문서가 "OverallMoon 전용" 이라 단정한 부분이 사실과 다름 |
| `DashboardResponseV2` 별도 응답 타입 | 기존 `DashboardResponse` 에 optional 필드 추가 | 코드와 일치 | — |
| Zustand `dashboardStore.ts` | `useState` 로 대체 | 미생성 — 코드와 일치 | — |
| Phase 3 원안 FE-PR-7~11 | redesign 으로 사실상 폐기 | **공식 폐기 선언 없음** → CLAUDE.md / MEMORY.md / Phase2_summary 표기 불일치 | 보고서 갱신 또는 폐기 선언 필요 |
| `FE-PR-6` 보고서 정리 클레임 | indicatorMutations.ts 통합 / builder/BottomSheet 이동 | 두 파일 모두 잔존 | 보고서·코드 사후 정리 필요 |

---

## 4. 라우트 / 컴포넌트 / 백엔드 부재 인벤토리

### 4.1 부재 라우트 (FE)

```
✗ frontend/app/thesis/[thesisId]/(detail)/                  — FE-PR-7 상세 탭
✗ frontend/app/thesis/[thesisId]/history/                   — FE-PR-9 히스토리 탭
✗ frontend/app/thesis/(list)/archive/                       — FE-PR-10 마감 아카이브
✗ frontend/app/profile/dna/                                 — FE-PR-11 DNA 프로필
✗ frontend/app/thesis/(list)/popular/                       — 통합 로드맵 §3 인기 가설
```

### 4.2 부재 컴포넌트 디렉토리

```
✗ frontend/components/thesis/history/                       (FE-PR-9 의존)
✗ frontend/components/thesis/profile/                       (FE-PR-11 의존)
✗ frontend/components/thesis/archive/                       (FE-PR-10 의존)
✗ frontend/components/thesis/dashboard/IndicatorHeatmap.tsx (FE-PR-8)
✗ frontend/components/thesis/dashboard/PremiseEditor.tsx    (FE-PR-7)
```

### 4.3 부재 백엔드 항목

```
모델
✗ thesis/models/learning.py: ValidityScore                  (Phase 2 집계 테이블)
✗ thesis/models/learning.py: ValidityRecord.is_synthetic    (Phase 3 합성 구분 필드)
✗ thesis/models/                ThesisRetrospective         (마감 회고 모델)

서비스
✗ thesis/services/              synthetic_bootstrapper.py   (Phase 3 합성 에이전트)
✗ thesis/services/              thesis_weight_learner.py    (Phase 3 Online LR)
✗ thesis/services/              validity_aggregator.py      (Phase 2 ValidityScore 집계)
✗ thesis/services/              dna_personalizer.py         (Phase 2 DNA 슬라이더 + 역제안)

Celery 태스크
✗ thesis/tasks/eod_pipeline.py: generate_thesis_summaries   (PR-10 AI 요약, 07:30)
✗ thesis/tasks/                 prepare_daily_issues        (07:00 오늘 이슈 캐시)
✗ thesis/tasks/                 scan_thesis_news            (2시간 간격 가설별 뉴스)
✗ thesis/tasks/                 update_popular_thesis_cache (08:00 인기 가설)
✗ thesis/tasks/                 aggregate_validity_scores   (Phase 2 주 1회 집계)

뷰 / 라우트
✗ thesis/views/                 RetrospectiveView           (FE-PR-10 의존)
✗ thesis/views/                 DNAProfileView              (FE-PR-11 의존)
✗ thesis/views/                 SnapshotHistoryView         (FE-PR-9 의존)
✗ thesis/views/                 PopularThesisView / TemplateView / ChainSightEntryView
```

### 4.4 백엔드 응답에 있으나 FE에서 미사용

```
ThesisSnapshot.universe_snapshot   (수학 모델 v2.3.2 Section 9 — 유니버스 고정)
ThesisSnapshot.ordered_indicator_ids
ThesisSnapshot.data_coverage
DashboardView 응답: heatmap.cells / heatmap.rows / heatmap.cols
DashboardView 응답: indicators[].is_extreme_vol
```

---

## 5. Phase 1 이벤트/유효성 인프라 — 5월 4일 재검증

`thesis/views/thesis_views.py` 와 `thesis/services/thesis_builder.py` 를 본 감사에서 다시 확인. **모두 5월 3일 검증 결과와 동일**.

| 검증 포인트 | 결과 | 위치 |
|------------|------|------|
| `ThesisViewSet.create()` → `thesis_created` | **삽입됨** | `thesis_views.py` L51~61 (perform_create) |
| `ThesisViewSet.close()` → `thesis_closed` + `outcome_correct/incorrect/neutral` + `ValidityRecord` + `InvestorDNA` 갱신 | **모두 삽입됨** | `thesis_views.py` L63~143. 활성 지표마다 ValidityRecord 생성 + 2×2 매트릭스 점수 + thesis.save 후 `_update_investor_dna()` 호출 |
| `ThesisPremiseViewSet.create()` → `premise_added` | **삽입됨** | `thesis_views.py` L158~174 |
| `ThesisPremiseViewSet.destroy()` → `premise_removed` | **삽입됨** | `thesis_views.py` L176~186 |
| `ThesisIndicatorViewSet.create()` → `indicator_added` (또는 AI 인 경우 `ai_suggestion_accepted`) | **삽입됨** | `thesis_views.py` L202~223 (`is_ai_recommended` 플래그로 분기) |
| `ThesisIndicatorViewSet.destroy()` → `indicator_removed` | **삽입됨** | `thesis_views.py` L225~235 |
| `ThesisIndicatorViewSet.auto()` → `ai_suggestion_shown` | **삽입됨** | `thesis_views.py` L237~266 |
| 빌더 이벤트 | **삽입됨** (5건) | `services/thesis_builder.py` L641 / L653 / L663 / L717 / L1177 — `builder_started`, `proposal_shown`, `preset_selected` 등 |
| `_compute_validity_score(aligned, correct)` 2×2 매트릭스 | **구현됨** (0.3 / -0.2 / -0.15 / 0.05) | `thesis_views.py` L274~283 — 통합 로드맵 §1.3 명세 일치 |
| `_update_investor_dna(user, thesis, outcome)` 집계 | **구현됨** | `thesis_views.py` L292~333 — total / closed / correct / incorrect / premise_category_counts / indicator_type_counts / ai_suggestions_shown / accepted 모두 집계 |

**유의점 (Phase 2 진입 전 해소 필요)**:
- `market_regime` 은 현재 고정값 `'normal'` 로 기록 (`thesis_views.py` L94). Phase 2 활성화 시 regime classifier 도입 전까지 regime 분리 데이터 누적 안 됨.
- `_compute_validity_score` 가 `outcome='neutral'` 인 경우의 `thesis_correct` 정의를 별도 처리하지 않고 단순 `False` 로 fallback (`thesis_correct = (outcome == 'correct')`, L82). 신중한 통합 로드맵 적용 시 점수 매트릭스 재정의 필요.

---

## 6. 하네스 일관성 이슈 (참고)

| # | 항목 | 문제 |
|---|------|------|
| H1 | `Phase2_completion_summary.md` §3 (FE-PR-7~11 차세대 계획) | 2일 뒤 redesign 으로 사실상 폐기되었으나 보고서 갱신 없음 → CLAUDE.md / MEMORY.md 에 잘못된 진척도 전파 |
| H2 | `FE-PR-6_alerts_close_qa.md` "indicatorMutations.ts → mutations.ts 통합 후 삭제" / "builder/BottomSheet → common/BottomSheet 이동" | 코드에 두 파일 모두 잔존 — 보고서 사후 정리 필요 |
| H3 | redesign PR-10 (`generate_thesis_summaries`) | 2026-03-18 FINAL 결정 후 약 7주 경과 (5월 4일 기준), PROGRESS.md / TASKQUEUE.md 에 진행 신호 없음 (`PROGRESS.md` audit P0 후속 큐 #15 에만 plain 항목으로 등재). FE 이미 렌더링 코드 들어가 있어 사용자 가치만 비실현 |
| H4 | `feature_flags.py: KEYWORD_HINTS_ENABLED=False` 외 chain/eod/news 모두 OFF | Phase B keyword 인프라 (`KeywordCache` 모델 + collectors 3종 + `check_keywords` / `keyword_health_check` commands) 는 100% 구현되어 있으나 실제 활성화 결정/시점 불명 |
| H5 | `Thesis.entry_source` choices 에 `popular` / `template` / `chainsight` 등록 | 작동 경로 없음 — 사용자가 잘못된 entry_source 로 가설 생성 시 동작 미정의. `thesis_views.py` perform_create 가 entry_source 만 받아 그대로 저장 |
| H6 | CLAUDE.md "구현 상태 요약 — Thesis Control Phase 3 진행 중 (FE-PR-7~11)" | **현실 불일치** — 진행 중 항목은 redesign 체계 PR-10 단일 (그조차 미시작). 표기 수정 권고 |
| H7 | `RealValueIndicatorCard.tsx` 정의 | redesign PR-8 산출물이지만 `app/thesis/[thesisId]/page.tsx` 본 코드 경로에서 미사용 (`IndicatorRow.tsx` 가 대체). 테스트 1건 (`__tests__/thesis/RealValueIndicatorCard.test.tsx`) 만 import → dead UI 컴포넌트 또는 향후 계획 컴포넌트 |
| H8 | `MEMORY.md` "설계 문서: docs/thesis_control/thesis_control_design.md" | **실제 경로는 `docs/thesis_control/plan/thesis_control_design.md`**. 메모리 갱신 필요 |
| H9 | `ValidityRecord.market_regime` 고정값 `'normal'` | Phase 1 코드 hardcoded. Phase 2 활성화 시 regime classifier 도입 전까지 regime 분리 데이터 누적 안 됨 |
| H10 | `scoreToPhaseMeta()` redesign §10 "삭제 가능" 명시 vs 실제 사용 | redesign 문서 단정과 달리 가설 목록 카드(`ThesisListCard.tsx`) + `(list)/page.tsx` + `index.ts` 에서 여전히 사용. 삭제 시 회귀 위험 — redesign 문서 §2 "삭제 대상" 표 갱신 필요 |
| H11 | `Thesis` 모델 status choices | 설계 문서 4.2 (L745~756) 는 `closed_correct/closed_incorrect/closed_neutral` 3종 분리. 실제 모델은 `closed` 단일 상태 + `outcome` 별도 필드로 collapse. **기능 동등하나 설계 문서 불일치 — 문서 갱신 또는 구현 정렬 결정 필요** |
| H12 | `Thesis` 모델 부재 필드 | 설계 4.2 의 `tags` (ArrayField), `category`, `alert_preference`, `overall_label`, `overall_score` (현재는 `current_score` / `current_state` 로 대체) 모두 모델에 없음. UX 영향 작으나 설계 문서와 정합성 어긋남 |

---

## 7. 한 줄 결론 + 우선순위 권고

**Phase 1 (관제 엔진 v2.3.2) + Phase 1 이벤트 인프라 + Phase A LLM 빌더 + Phase B Keyword 인프라 (코드) + Phase 3-Redesign PR-7~9 (실제값 대시보드 + 분기 지표)** 은 완전 구현 (A). **나머지 Phase 2 활성화 (유효성 집계 / DNA 슬라이더 / 상관 할인 / Adaptive Decay / 뉴스 센티먼트), 통합 로드맵 Phase 3 (합성 에이전트 + Online LR + 커뮤니티 + 복기 + Neo4j), Phase 4 (벡터 스코어링), redesign PR-10 (AI 모니터링 파이프라인)** 은 모두 미구현 (C). 5월 3일 → 5월 4일 사이 thesis 영역 변경 0건으로 갭 분포 동일.

### 우선순위 권고

1. **즉시 매워야 할 갭 (사용자 영향 최대)** — redesign PR-10 (`generate_thesis_summaries`). FE 가 이미 `AISummarySection` 을 렌더링 트리에 두고 있고, 백엔드만 빈 문자열을 반환하므로 사용자 가치 미실현. Celery 태스크 + Beat 등록 (DB 기반, CLAUDE.md 버그 #28 회피) 만 추가하면 즉시 가시화. PROGRESS.md "다음 세션 #15" 와 동일.
2. **CLAUDE.md / Phase2_completion_summary.md 정합성** — Phase 3 원안 (FE-PR-7~11) 을 공식 폐기 선언하거나, 살릴 항목만 (예: DNA 프로필) 골라 새 PR 번호로 재정의. 현 표기는 진행 신호도 폐기 신호도 아님.
3. **잔재 컴포넌트 정리** — `RealValueIndicatorCard.tsx` (dead UI) / `indicatorMutations.ts` (보고서는 삭제 클레임) / `builder/BottomSheet.tsx` (보고서는 이동 클레임) 정리 결정. `scoreToPhaseMeta` 가 가설 목록에서 살아 있다는 사실은 redesign 문서 §10 의 "삭제 가능" 단정과 어긋남 — 문서 또는 코드 둘 중 하나 갱신.
4. **Phase 2 활성화 트리거** — Phase 1 이벤트/유효성 hook 이 모두 작동하므로 ValidityRecord 가 누적 중. 마감 가설 10건+ 도달 후 `ValidityScore` 모델 + 주 1회 집계 태스크부터 시작하면 통합 로드맵 §2 진입 가능. 단 `market_regime` 이 고정값이므로 regime classifier 가 §2 시작점 (H9).
5. **장기 로드맵** — 특허 청구항 (DNA / 적응형 유효성 / 합성 에이전트 / 벡터) 은 Phase 1 이벤트 인프라만 안착된 상태. 데이터 축적이 부트스트랩의 전제이므로 Phase 2 진입 전 사용자 베이스 확보 우선.

---

## 부록 A. 백엔드 파일 인벤토리

```
thesis/models/        community.py, indicator.py, keyword.py, learning.py, monitoring.py, thesis.py
thesis/views/         conversation_views.py, monitoring_views.py, thesis_views.py
thesis/services/      alert_engine.py, arrow_calculator.py, builder_events.py, builder_state.py,
                      data_validator.py, indicator_matcher.py, indicator_scorer.py, keyword_cache.py,
                      keyword_collectors/{chain,eod,news}.py, keyword_hint.py, llm_postprocess.py,
                      premise_aggregator.py, prompt_builder.py, quarterly_metric_fetcher.py,
                      snapshot_builder.py, thesis_builder.py, thesis_state_machine.py
thesis/serializers/   conversation_serializers.py, indicator_serializers.py,
                      monitoring_serializers.py, thesis_serializers.py
thesis/tasks/         eod_pipeline.py
thesis/migrations/    0001_initial → 0009_add_recommendation_reason (총 9개)
thesis/management/commands/  builder_stats.py, check_keywords.py, keyword_health_check.py
```

## 부록 B. 프론트엔드 파일 인벤토리

```
frontend/app/thesis/
  layout.tsx
  (list)/{layout.tsx, page.tsx, alerts/page.tsx}
  new/page.tsx
  [thesisId]/{page.tsx, indicators/page.tsx, close/page.tsx}

frontend/components/thesis/
  AddIndicatorSheet.tsx, IndicatorCard.tsx, PresetSelector.tsx, index.ts
  alerts/    AlertCard, AlertFilterTabs, EmptyAlerts
  builder/   BottomSheet, ChatBubble, MultiSelectFooter, NewsSelector, OptionButton,
             PremiseCard, ProgressBar, SuggestionCard, TextInput
  close/     CloseConfirmDialog, OutcomeSelector
  common/    AlertBell, ArrowIndicator, BottomSheet, IndicatorCard, MoonPhase, ThesisBadge
  dashboard/ AISummarySection, ChartToggleButton, DashboardHeader, DashboardPageHeader,
             IndicatorRow, IndividualMiniCharts, NotableChangesSection, PeriodSelector,
             QuarterlySparkline, RealValueIndicatorCard
  indicators/ AddIndicatorSheet, IndicatorSetupCard, RecommendCard
  list/      EntryPointGrid, ThesisListCard, TodayChangeCard
  skeleton/  ThesisSkeleton

frontend/lib/thesis/
  api.ts, constants.ts, conversation.ts, indicatorMutations.ts, mock.ts,
  mutations.ts, queries.ts, types.ts, utils.ts
```

## 부록 C. 4월 26일 → 5월 4일 변동 요약

| 보고서 | 핵심 차이 |
|--------|----------|
| 4월 26일 (2026-04-27) | 최초 갭 분석 — Phase 1 이벤트 hook "검증 필요" |
| 5월 1일 (2026-05-02) | redesign 문서 / Phase2_summary 충돌 명시 — Phase 1 hook 여전히 미검증 |
| 5월 2일 (2026-05-03) | Phase 1 이벤트 hook **모두 검증 완료 (90% A)**. 4월 27일 이후 thesis 영역 코드 변경 1건 (`b3b9bdf` indicator_catalog 표시명 동기화) |
| 5월 3일 (2026-05-04) | 5월 2일 → 5월 3일 사이 thesis 영역 변경 **0건**. §3.7 잔재 항목 재검증 (`scoreToPhaseMeta` 가 5개 파일에서 여전히 사용) + §6 일관성 이슈 H10~H12 신규 추가 |
| **5월 4일 (2026-05-05)** | 5월 3일 → 5월 4일 사이 thesis 영역 변경 **0건** (커밋·working tree 모두). PR-10 미시작 7주 경과 (H3 갱신). 갭 분포는 5월 3일과 동일하며, 본 감사는 Phase 1 hook + redesign PR-7~9 산출물 + redesign PR-10 부재 + Phase2_summary FE-PR-7~11 부재를 모두 직접 코드 재검증 (grep / Read)으로 확인 |
