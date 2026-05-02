# Thesis Control 설계 갭 감사

> 감사 일자: 2026-05-03
> 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` 백엔드 + `frontend/{components,app,lib}/thesis/` 구현
> 본 보고서는 **읽기 전용 감사**입니다. 코드 변경 없음.
> 분류: **(A)** 완전 구현 / **(B)** 부분 구현 / **(C)** 미구현 / **(D)** 폐기·대체

---

## 0. 사전 컨텍스트

### Phase 정의 충돌 — "Phase 3"이 세 문서에서 서로 다르게 쓰임

| 문서 | "Phase 3"의 의미 | 진행 상태 |
|---|---|---|
| `frontend/task_done/Phase2_completion_summary.md` (2026-03-16) §3 | **FE-PR-7~11**: 대시보드 탭 구조 / 히트맵 / 히스토리 / 마감 아카이브 / 투자자 DNA 프로필 | **거의 미시작 (C)** |
| `plan/thesis_control_phase3_frontend_redesign.md` (2026-03-18, FINAL) | **PR-7~10**: BE raw_value 확장 / 실제값 카드 / 미니차트 / AI 모니터링 파이프라인 | **PR-7~9 완료 (A), PR-10 미구현 (C)** |
| `plan/thesis_control_integrated_roadmap.md` §3 | **합성 에이전트 + Online LR + 가설 복기 + Neo4j 관계 그래프 + 커뮤니티(인기/템플릿/Chain Sight 연동)** | **거의 미시작 (C)** |

**해석**: redesign 문서가 원안의 FE-PR-7~11(탭/히트맵/DNA)을 **사실상 폐기·재정의**하고 "내부 점수 숨기고 실제 값 보여주기" 방향으로 전환. CLAUDE.md "Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11) 진행 중" 표기는 **현실과 불일치** — 실제로 진행 중인 것은 redesign PR-10 단일 항목뿐이며 그조차 미시작.

### 5월 1일 감사 대비 변경점

5월 1~2일 사이 thesis 영역 git diff: 없음.
4월 26일 이후 변경된 thesis 관련 커밋은 `b3b9bdf` (FMP Starter rate_limit 정정 + indicator_catalog 표시 이름 4건 BE/FE 통일) 단 1건. **설계 갭 분포는 5월 1일 상태와 동일**, 단 본 감사에서 5월 1일 보고서가 "미검증"으로 남긴 Phase 1 이벤트 hook 분포를 추가 검증해 결론을 갱신함 (§5 참조).

---

## 1. 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 등급 |
|-------|------|--------|------|
| Phase 1 — 관제 엔진 (수학 모델 v2.3.2) | Stage 0~3 + Celery 3태스크 + 스냅샷 + 알림 throttling | 95% | **A** |
| Phase 1 — 이벤트/유효성 인프라 | `HypothesisEvent`/`ValidityRecord`/`InvestorDNA` 모델 + 비즈니스 로직 hook | **90%** *(상향)* | **A** |
| Phase 2 — Builder (FE-PR-1~3) | 라우팅 + 공통 컴포넌트 + 6단계 대화형 빌더 | 100% | **A** |
| Phase 2 — Indicator Setup (FE-PR-4) | 지표 설정 페이지 + AI 추천 시트 | 100% | **A** |
| Phase 2 — Dashboard (FE-PR-5) | 관제실 단일 화면 — 단 OverallMoon은 redesign에서 폐기 | 80% | **A** (redesign에 흡수) |
| Phase 2 — Alerts/Close (FE-PR-6) | 알림 3탭 + Outcome 선택 + Close Confirm | 100% | **A** |
| Phase 3-Redesign — PR-7~9 | 실제값 카드 + AI 분석 + 미니차트 + 분기 지표 | 100% | **A** |
| Phase 3-Redesign — PR-10 | AI 모니터링 파이프라인 (Celery `generate_thesis_summaries`) | 0% | **C** |
| Phase 3 — Phase2 summary 정의 (FE-PR-7~11) | 탭 / 히트맵 / 히스토리 / 아카이브 / DNA 프로필 | 0% | **C** (사실상 **D** 폐기 가능성) |
| Phase 2 (통합 로드맵) — 유효성 활성화 | `ValidityScore` / DNA 슬라이더 / 역제안 / 상관할인 / Adaptive Decay / 뉴스 센티먼트 | 0% | **C** |
| Phase 3 (통합 로드맵) — 합성 에이전트 + Online LR | `SyntheticBootstrapper` / `ThesisWeightLearner` / 블렌딩 | 0% | **C** |
| Phase 3 (통합 로드맵) — 커뮤니티 + Neo4j | 인기 가설 / 템플릿 / Chain Sight 양방향 / 가설 관계 그래프 | 0% | **C** |
| Phase 4 — 벡터 스코어링 | DNA 16d / Validity 6d / 코사인 유사도 | 0% | **C** |
| Phase A — LLM 빌더 (one-shot proposal) | builder_state / prompt_builder / llm_postprocess / builder_events / feature_flags | 100% | **A** |
| Phase B — Keyword Enrichment | `KeywordCache` + collectors (chain/eod/news) + keyword_hint + builder_stats / check_keywords commands | 100% (코드) / Flag OFF | **A** (코드) / **B** (롤아웃) |
| Phase C — Advanced Builder | MiniDashboardPreview / GuidedSuggestion / Streaming / MultiTurnEdit | 0% | **C** |

세부 근거는 §2~§4 참조.

---

## 2. 문서별 상태 테이블

### 2.1 핵심 설계 문서 (`docs/thesis_control/plan/`)

| 문서 | 줄 | 핵심 산출물 | 매칭 코드 | 상태 |
|------|----|------------|----------|------|
| `thesis_control_design.md` | 1370 | 모델 / 뷰 / 서비스 / API / UX 전체 스펙 | `thesis/{models,views,services,serializers}/*` | **A** |
| `thesis_control_math_model_final.md` (v2.3.2) | 1153 | Stage 0~3 스코어링 수식 | `services/{data_validator,indicator_scorer,premise_aggregator,thesis_state_machine,arrow_calculator,snapshot_builder,alert_engine}.py` | **A** |
| `thesis_control_implementation_guide.md` | 286 | Phase 1~4 구현 로드맵 | Phase 1 일치 / Phase 2~4 미시작 | **B** |
| `thesis_control_integrated_roadmap.md` | 660 | 수학 모델 + 특허 기능 통합 (Phase 1~4) | Phase 1 BE만 부분 일치 | **B** |
| `thesis_control_phase3_frontend_redesign.md` (FINAL) | 1095 | PR-7~10 (실제값 + AI + 차트 + Celery 파이프라인) | `dashboard/*.tsx`, `monitoring_views.py`, migration 0004/0005 | **B** (PR-7~9 완료, PR-10 부재) |

### 2.2 루트 문서

| 문서 | 상태 | 비고 |
|------|------|------|
| `docs/thesis_control/thesis_control_user_experience.md` (2026-03-30) | **A** | 현재 코드의 6단계 흐름 + Suggestion Mode와 일치. (단 메모리에 기록된 "`docs/thesis_control/thesis_control_design.md`" 경로는 **존재하지 않음** — 실제 설계 파일은 `plan/` 하위) |
| `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_1.md` ~ `FE_PR_5.md` | **A** | task_done 보고서와 일치 |
| `docs/thesis_control/thesis_control_phase1_frontend_prompts.md` | n/a | 프롬프트 모음, 갭 평가 대상 아님 |
| `docs/thesis_control/thesis_control_phase1_prompts.md` | **A** | 백엔드 BE-PR-1~5 모두 코드에 안착 |

### 2.3 빌더 v2 리디자인 (`plan/talking_builder/`)

| 문서 | 줄 | 매칭 | 상태 |
|------|----|------|------|
| `llm_builder_plan.md` | 563 | `services/{thesis_builder,llm_postprocess,builder_state,builder_events,prompt_builder}.py` | **A** |
| `thesis_builder_redesign_v2.md` | 1110 | `views/conversation_views.py` 의 `ConversationStartView/RespondView/NewsIssuesView/SuggestThesesView` | **A** |
| `quarterly_indicator_dashboard_plan.md` | 424 | `services/quarterly_metric_fetcher.py` + DashboardView 분기 분기 데이터 응답 + `QuarterlySparkline.tsx` + `IndicatorRow.tsx` 분기 모드 | **A** |
| `redesign_build_plan/00_total_plan.md` (v4) | 525 | Phase A MVP / A Hardening / B Keywords / C Advanced 종합 | **B** |
| `redesign_build_plan/01_phase_a_mvp.md` | 287 | Phase A MVP — `work_done/phase_a_llm_builder.md` 완료 보고 | **A** |
| `redesign_build_plan/02_phase_a_hardening.md` | 118 | Phase A 안정화 (PR-4~7 적용) | **A** |
| `redesign_build_plan/03_phase_b_keywords.md` | 299 | KeywordCache + Strength + monitoring | **A** (코드) / 운영 flag OFF |
| `redesign_build_plan/04_phase_c_advanced.md` | 144 | MiniDashboard / Guided Suggestion / Streaming | **C** |
| `redesign_build_plan/05_summary.md` | n/a | 요약 | n/a |

### 2.4 프론트엔드 task_done 보고서 (`frontend/task_done/`)

| 보고서 | 코드 일치 | 비고 |
|--------|----------|------|
| `FE-PR-1_routing_common_components.md` | **A** | 라우팅 7개 + common 컴포넌트 5개 + authAxios 단일화 모두 확인 |
| `FE-PR-2_thesis_list_page.md` | **A** | ThesisListCard / TodayChangeCard / EntryPointGrid + USE_MOCK 분기 |
| `FE-PR-3_builder_implementation.md` (+ `FE-PR-3_plan_review_v3.md`) | **A** | 6단계 wizard 빌더 9개 컴포넌트 + Phase A LLM proposal 모드 추가 (page.tsx 1072줄로 확장) |
| `FE-PR-4_indicator_setup.md` | **A** | IndicatorSetupCard / AddIndicatorSheet / RecommendCard / Route Group `(list)` 분리 모두 확인 |
| `FE-PR-5_dashboard.md` | **부분 폐기 (D)** | `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 는 redesign에서 삭제됨. `RealValueIndicatorCard`/`AISummarySection`/`NotableChangesSection` 으로 교체. 단 — page.tsx는 `RealValueIndicatorCard`가 아닌 **`IndicatorRow`**(인라인 토글 차트 포함)를 최종 사용 → `RealValueIndicatorCard.tsx`는 **테스트만 import**하는 dead UI 컴포넌트 |
| `FE-PR-6_alerts_close_qa.md` | **A (불일치 1건)** | 알림/마감 컴포넌트 모두 확인. 단 — 보고서 §"이동/삭제"에서 `lib/thesis/indicatorMutations.ts → mutations.ts 통합 후 삭제" / "builder/BottomSheet.tsx → common/BottomSheet.tsx 이동"으로 기재되어 있으나 **실제로는 두 파일 모두 잔존**(indicatorMutations 47줄 + mutations 85줄, builder/BottomSheet + common/BottomSheet 모두 존재) → 보고서·코드 사후 정리 필요 |
| `Phase2_completion_summary.md` | **부분 폐기 (D)** | §3 "Phase 3 계획 (FE-PR-7~11)"은 2일 뒤 redesign으로 사실상 폐기됨 |

### 2.5 작업 진행 보고서 (`work_done/`)

| 보고서 | 상태 |
|--------|------|
| `phase_a_llm_builder.md` (Phase A-MVP + Hardening, 2026-03-20) | **A** — 5개 신규 백엔드 파일 + 4개 프론트엔드 변경 + 테스트 104개 모두 실제 코드와 일치 |

---

## 3. Phase 3 미구현 항목 상세

### 3.1 Phase 3-Redesign 기준 — PR-10 AI 파이프라인 (단일 미구현)

설계 출처: `thesis_control_phase3_frontend_redesign.md` §7 (L923~L1095)

| 항목 | 설계 명세 | 현재 상태 |
|------|----------|----------|
| Celery `generate_thesis_summaries` | 매일 07:30 KST. Stage 3 상태 + raw_value 변화 → Gemini 2.5 Flash 동기 호출 → 2~3문장 한국어 요약 | **부재** — `tasks/eod_pipeline.py` 에 함수 없음 |
| `ThesisSnapshot.ai_summary` 채움 로직 | 위 태스크에서 저장 | **부재** — `snapshot_builder.py`의 `defaults={...}`에 `ai_summary` 키 없음. 모델 default `''` 그대로 |
| `notable_changes` 풍부화 | alert_engine 이벤트(direction_flip / sharp_move / extreme_volatility)를 `{indicator_id, type, severity, description, raw_value_before/after, change_pct}`로 변환 | **부분 (B)** — `snapshot_builder.py` L106~L122 단순 \|delta\| ≥ 0.3 필터로만 채움. AI 풍부화/severity 분기 없음 |
| Beat schedule 등록 | DatabaseScheduler에 `PeriodicTask.objects.create(...)` (CLAUDE.md 버그 #28 회피 패턴) | **부재** |

**FE 영향**: `app/thesis/[thesisId]/page.tsx` L75~78 에서 `<AISummarySection summary={data.thesis.ai_summary} ... />` 를 렌더링하나, 응답 `ai_summary === ''`이므로 `if (!summary) return null` 분기로 인해 **사용자 화면에서 항상 미렌더링**. `NotableChangesSection`도 단순 score delta 기반으로 동작.

### 3.2 Phase2_summary / CLAUDE.md 기준 — FE-PR-7~11 (모두 미시작)

`Phase2_completion_summary.md` L129~L137 에 정의된 차세대 5개 PR이 어디에도 안착하지 않음. redesign 문서가 사실상 이 계획을 폐기하면서도 공식 폐기 선언이 없어 CLAUDE.md "구현 상태 요약"이 여전히 "Phase 3 진행 중 (FE-PR-7~11)"으로 표기.

| PR | 설계 의도 | 라우트 부재 | 컴포넌트 부재 | 백엔드 의존성 |
|----|----------|------------|--------------|--------------|
| **FE-PR-7** | 대시보드 3탭 구조 (관제 / 상세 / 히스토리) + 전제 CRUD UI | `[thesisId]/(detail)/`, `[thesisId]/history/` 등 미생성. 현재 `[thesisId]/page.tsx`는 단일 스크롤 화면 | `DashboardTabs`, `DetailTab`, `PremiseEditor` 부재 | `ThesisPremiseViewSet` 재활용 가능 (BE OK) |
| **FE-PR-8** | Finviz 스타일 히트맵 + 지표 weight/direction 인라인 편집 | (FE-PR-7 탭 내부) | `IndicatorHeatmap` 부재. `monitoring_views.DashboardView` 응답에 `heatmap.cells`는 이미 존재(L195~204) 하나 FE 사용 안 함 | `ThesisIndicator` PATCH 가능 (BE OK) |
| **FE-PR-9** | 히스토리 탭 (recharts 라인 차트 + 스냅샷 타임라인) | `[thesisId]/history/page.tsx` 부재 | `ScoreHistoryChart`, `SnapshotTimeline` 부재 | `GET /{id}/snapshots/` API 부재 |
| **FE-PR-10** | 마감 아카이브 + ValidityMatrix 2×2 | `(list)/archive/page.tsx` 부재 | `ArchiveList`, `ValidityMatrix2x2`, `RetrospectiveCard` 부재 | `Thesis.status='closed'` 필터는 가능. 마감 시 `ValidityRecord` 자동 생성은 **이미 작동**(§5에서 확인) |
| **FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `/thesis/profile`/`/profile/dna` 부재 | `AccuracyRing`, `CategoryChart`, `DNADashboard` 부재 | `InvestorDNA` 모델 + 자동 갱신 hook은 **이미 작동**. **단 DNA 조회 API (`GET /users/me/dna/` 등) 미정의** |

### 3.3 통합 로드맵 §2 — Phase 2 활성화 (선행 작업 누락)

| 항목 | 설계 (`integrated_roadmap.md` §2) | 현재 상태 |
|------|-----------------------------------|----------|
| `ValidityScore` 모델 (집계 테이블) | `(thesis_type, indicator_data_key, market_regime)` unique + cumulative_score / sample_count / confidence / is_active | **부재** |
| Celery 주 1회 `aggregate_validity_scores` | ValidityRecord → ValidityScore 집계 | **부재** |
| 지표 추천에 유효성 점수 반영 | `indicator_matcher.match_indicators()` 가 `validity_boost` 계산 → core/reference/low_impact 티어 | **부재** — 현재 키워드 룰 + LLM 매칭만 |
| DNA 적합도 슬라이더 | `apply_dna_personalization(...)` (0~1 블렌딩) | **부재** (`InvestorDNA.personalization_weight` 필드만 존재) |
| 역제안 (Contrarian Nudge) | `add_contrarian_nudge(...)` 안 쓰는 indicator_type에서 1개 | **부재** |
| 상관계수 자동 할인 | 60일 \|ρ\|≥0.9 → 1/√k | **부재** |
| Adaptive Decay/Window | 변동성 → λ↓, window↓ | **부재** (고정 epsilon=0.0001, window=60, decay=0.95) |
| Sustained Extreme alert subtype | s_decayed≥3 (clip 전) | **부재** (`extreme_volatility` 단일 타입만) |
| 뉴스 센티먼트 → Stage 1 입력 | `news/` SentimentHistory를 indicator로 통합 | **부재** |

### 3.4 통합 로드맵 §3 — Phase 3 (합성 에이전트 + 자동학습)

| 항목 | 설계 명세 | 현재 상태 |
|------|----------|----------|
| `SyntheticBootstrapper` | 20~30개 페르소나로 과거 시장 데이터 기반 합성 가설 → ValidityScore 사전 채움 (Cold Start 해결) | **부재** |
| `ThesisWeightLearner` (Online LR + L2) | 마감된 가설로 전제 가중치 학습 | **부재** |
| `ValidityRecord.is_synthetic` 필드 | 합성/실제 데이터 구분 | **부재** (모델 필드 미존재) |
| `aggregate_validity_scores(blend_ratio=0.3)` | 실제 sample 늘면 자동 비중 감소 | **부재** |
| Online LR 주간 재학습 Celery + Safety Gate | 일요일 새벽, `should_deploy_weights()` | **부재** |

### 3.5 통합 로드맵 §3 — Phase 3 (커뮤니티 + 복기 + Neo4j)

| 항목 | 설계 명세 | 현재 상태 |
|------|----------|----------|
| 인기 가설 시스템 | `GET /popular/`, `POST /popular/{id}/follow/`, `update_popular_thesis_cache` Celery | **부재** (`PopularThesisCache` 모델만 존재) |
| 템플릿 시스템 | `GET /templates/`, `GET /templates/{type}/` (이벤트형/추세형/비교형/괴리형) | **부재** |
| Chain Sight ↔ Thesis 양방향 진입점 | `entry_source='chainsight'` 진입 경로 | **부재** (enum choice 등록만, 진입 UI/로직 없음) |
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

### 3.7 폐기·대체된 항목 (D)

| 폐기 | 대체 | 잔재 |
|------|------|------|
| `OverallMoon.tsx` (대시보드 달 위상) | redesign에서 삭제 — 가설 목록 카드(`ThesisListCard`)에서만 잔존 | `common/MoonPhase.tsx` 잔존 |
| `DashboardIndicatorCard.tsx` (화살표 + 트렌드) | `RealValueIndicatorCard.tsx` (정의만) → **실제 사용은 `IndicatorRow.tsx`** | `ArrowIndicator.tsx` 잔존 (dashboard 비사용) |
| `RecentChange.tsx` (내러티브 텍스트) | `NotableChangesSection.tsx` (구조화된 변화 목록) | — |
| `scoreToPhaseMeta()` 유틸 | redesign 문서 §10에서 "삭제 가능" 명시 | `utils.ts` 잔존 여부 별도 grep 필요 |
| `DashboardResponseV2` 별도 응답 타입 | 기존 `DashboardResponse`에 optional 필드 추가 | 코드와 일치 |
| Zustand `dashboardStore.ts` | `useState`로 대체 | 미생성 — 코드와 일치 |
| Phase 3 원안 FE-PR-7~11 | redesign으로 사실상 폐기 | **공식 폐기 선언 없음** → CLAUDE.md 표기 불일치 |

---

## 4. 라우트 / 컴포넌트 / 백엔드 부재 인벤토리

### 4.1 부재 라우트

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
✗ thesis/models/learning.py: ValidityScore                  (Phase 2 집계 테이블)
✗ thesis/models/learning.py: ValidityRecord.is_synthetic    (Phase 3 합성 구분 필드)
✗ thesis/models/                ThesisRetrospective         (마감 회고 모델)
✗ thesis/services/              synthetic_bootstrapper.py   (Phase 3 합성 에이전트)
✗ thesis/services/              thesis_weight_learner.py    (Phase 3 Online LR)
✗ thesis/services/              validity_aggregator.py      (Phase 2 ValidityScore 집계)
✗ thesis/services/              dna_personalizer.py         (Phase 2 DNA 슬라이더 + 역제안)
✗ thesis/tasks/eod_pipeline.py: generate_thesis_summaries   (PR-10 AI 요약, 07:30)
✗ thesis/tasks/                 prepare_daily_issues        (07:00 오늘 이슈 캐시)
✗ thesis/tasks/                 scan_thesis_news            (2시간 간격 가설별 뉴스)
✗ thesis/tasks/                 update_popular_thesis_cache (08:00 인기 가설)
✗ thesis/tasks/                 aggregate_validity_scores   (Phase 2 주 1회 집계)
✗ thesis/views/                 RetrospectiveView           (FE-PR-10 의존)
✗ thesis/views/                 DNAProfileView              (FE-PR-11 의존)
✗ thesis/views/                 SnapshotHistoryView         (FE-PR-9 의존)
✗ thesis/views/                 PopularThesisView / TemplateView / ChainSightEntryView
```

---

## 5. 5월 1일 보고서 미검증 항목 — 추가 검증 결과

5월 1일 보고서 §3-5에서 "이벤트 기록 hook이 비즈니스 로직에 삽입되었는지 미검증" 으로 남긴 항목을 본 감사에서 grep + 실제 코드 확인.

| 검증 포인트 | 결과 | 위치 |
|------------|------|------|
| `ThesisViewSet.create()` → `thesis_created` | **삽입됨** | `thesis_views.py` L51~61 (perform_create) |
| `ThesisViewSet.close()` → `thesis_closed` + `outcome_correct/incorrect/neutral` + `ValidityRecord` + `InvestorDNA` 갱신 | **모두 삽입됨** | `thesis_views.py` L63~143 (close action) — 활성 지표마다 ValidityRecord 생성 + 2×2 매트릭스 점수 + thesis.save 후 `_update_investor_dna()` 호출 |
| `ThesisPremiseViewSet.create()` → `premise_added` | **삽입됨** | `thesis_views.py` L158~174 |
| `ThesisPremiseViewSet.destroy()` → `premise_removed` | **삽입됨** | `thesis_views.py` L176~186 |
| `ThesisIndicatorViewSet.create()` → `indicator_added` (또는 AI인 경우 `ai_suggestion_accepted`) | **삽입됨** | `thesis_views.py` L202~223 (`is_ai_recommended` 플래그로 분기) |
| `ThesisIndicatorViewSet.destroy()` → `indicator_removed` | **삽입됨** | `thesis_views.py` L225~235 |
| `ThesisIndicatorViewSet.auto()` → `ai_suggestion_shown` | **삽입됨** | `thesis_views.py` L237~266 |
| `services/thesis_builder.py` 빌더 이벤트 | **삽입됨** (5건) | L641, L653, L663, L717, L1177 — `builder_started/proposal_shown/preset_selected` 등 빌더 진행 이벤트 |
| `_compute_validity_score(aligned, correct)` 2×2 매트릭스 | **구현됨** (0.3 / -0.2 / -0.15 / 0.05) | `thesis_views.py` L274~283 — 통합 로드맵 §1.3 명세와 일치 |
| `_update_investor_dna(user, thesis, outcome)` 집계 | **구현됨** | `thesis_views.py` L292~333 — total / closed / correct / incorrect / premise_category_counts / indicator_type_counts / ai_suggestions_shown/accepted 모두 집계 |

**결론**: 5월 1일 "Phase 1 이벤트 인프라 50%(B)" 평가는 **상향 조정** 필요 → **90%(A)**. 모델·hook·집계 함수 모두 구현 완료. 단 — `market_regime`은 현재 고정값 `'normal'`로 기록되어 Phase 2 활성화 전까지 regime 분리 무의미. `_compute_validity_score` 정의도 `outcome='neutral'`인 경우(thesis_correct 정의 모호)를 별도 처리하지 않고 `False`로 fallback.

---

## 6. 하네스 일관성 이슈 (참고)

| # | 항목 | 문제 |
|---|------|------|
| H1 | `Phase2_completion_summary.md` §3 (FE-PR-7~11 차세대 계획) | 2일 뒤 redesign으로 사실상 폐기되었으나 보고서가 갱신되지 않음 → CLAUDE.md/기억된 메모리 에 잘못된 진척도 전파 |
| H2 | `FE-PR-6_alerts_close_qa.md` "indicatorMutations.ts → mutations.ts 통합 후 삭제" / "builder/BottomSheet → common/BottomSheet 이동" | 코드에 두 파일 모두 잔존 (`lib/thesis/{indicatorMutations.ts(47L), mutations.ts(85L)}` + `components/thesis/builder/BottomSheet.tsx` + `components/thesis/common/BottomSheet.tsx`) — 보고서 사후 정리 필요 |
| H3 | redesign PR-10 (`generate_thesis_summaries`) | 2026-03-18 FINAL 결정 후 약 6주 경과, PROGRESS.md / TASKQUEUE.md 에 진행 신호 없음. FE 이미 렌더링 코드는 들어가 있어 사용자 가치만 비실현 |
| H4 | `feature_flags.py: KEYWORD_HINTS_ENABLED=False` 외 chain/eod/news 모두 OFF | Phase B keyword 인프라(`KeywordCache` 모델 + collectors 3종 + check_keywords command)는 100% 구현되어 있으나 실제 활성화 결정/시점 불명 |
| H5 | `Thesis.entry_source` choices 에 `popular`/`template`/`chainsight` 등록 | 작동 경로 없음 — 사용자가 잘못된 entry_source로 가설 생성 시 동작 미정의 |
| H6 | CLAUDE.md "구현 상태 요약" — "Thesis Control Phase 3 진행 중 (FE-PR-7~11: 깊이 + 회고 + 프로필)" | **현실 불일치** — 진행 중인 것은 redesign 체계 PR-10 단일 항목(그조차 미시작). 표기 수정 권고 |
| H7 | `RealValueIndicatorCard.tsx` 정의 | redesign PR-8 산출물이지만 page.tsx 본 코드 경로에서 미사용 (`IndicatorRow.tsx` 가 대체). 테스트 1건만 import → dead UI 컴포넌트 또는 향후 계획 컴포넌트 |
| H8 | `thesis_control_design.md` 절대 경로 | 메모리(`MEMORY.md`)에 "설계 문서: docs/thesis_control/thesis_control_design.md" 로 기록되어 있으나 **실제 경로는 `docs/thesis_control/plan/thesis_control_design.md`**. 메모리 갱신 필요 |
| H9 | `ValidityRecord.market_regime` 고정값 `'normal'` | Phase 1 코드 hardcoded. Phase 2 활성화 시 regime classifier 도입 전까지 regime 분리 데이터 누적 안 됨 |

---

## 7. 한 줄 결론 + 우선순위 권고

**Phase 1 (관제 엔진 v2.3.2) + Phase 1 이벤트 인프라 + Phase A LLM 빌더 + Phase B Keyword 인프라(코드) + Phase 3-Redesign PR-7~9(실제값 대시보드 + 분기 지표) 는 완전 구현(A). 나머지 Phase 2 활성화(유효성 집계 / DNA 슬라이더 / 상관할인 / Adaptive Decay / 뉴스 센티먼트), 통합 로드맵 Phase 3(합성 에이전트 + Online LR + 커뮤니티 + 복기 + Neo4j), Phase 4(벡터 스코어링), 그리고 redesign PR-10(AI 모니터링 파이프라인)은 모두 미구현(C).**

### 우선순위 권고

1. **즉시 매워야 할 갭 (사용자 영향 최대)** — redesign PR-10. FE는 이미 `AISummarySection`을 렌더링 트리에 두고 있고, 백엔드만 빈 문자열을 반환하므로 사용자 가치 미실현. `generate_thesis_summaries` Celery + Beat 등록(DB 기반, CLAUDE.md 버그 #28 회피) 만 추가하면 즉시 가시화.
2. **CLAUDE.md / Phase2_completion_summary.md 정합성** — Phase 3 원안(FE-PR-7~11)을 공식 폐기 선언하거나, 살릴 항목만 (예: DNA 프로필) 골라 새 PR 번호로 재정의. 현 표기는 진행 신호도 폐기 신호도 아님.
3. **Phase 2 활성화 트리거** — Phase 1 이벤트/유효성 hook이 모두 작동하므로 ValidityRecord가 누적 중. 마감 가설 10건+ 도달 후 `ValidityScore` 모델 + 주 1회 집계 태스크부터 시작하면 통합 로드맵 §2 진입 가능. `market_regime`이 고정값이므로 regime classifier가 §2 시작점.
4. **장기 로드맵** — 특허 청구항(DNA / 적응형 유효성 / 합성 에이전트 / 벡터)은 Phase 1 이벤트 인프라만 안착된 상태. 데이터 축적이 부트스트랩의 전제이므로 Phase 2 진입 전 사용자 베이스 확보 우선.

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

## 부록 C. 4월 26일 → 5월 2일 → 5월 3일 변동 요약

| 보고서 | 핵심 차이 |
|--------|----------|
| 4월 26일 (2026-04-27) | 최초 갭 분석 — Phase 1 이벤트 hook "검증 필요" |
| 5월 1일 (2026-05-02) | redesign 문서 / Phase2_summary 충돌 명시 — Phase 1 hook 여전히 미검증 |
| **5월 2일 (2026-05-03)** | Phase 1 이벤트 hook **모두 검증 완료 (90% A)**. 4월 27일 이후 thesis 영역 코드 변경 1건(`b3b9bdf` indicator_catalog 표시명 동기화)뿐 — 설계 갭은 동일 |
