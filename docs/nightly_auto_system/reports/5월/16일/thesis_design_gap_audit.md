# Thesis Control 설계 갭 감사

> 감사일: 2026-05-17
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드) 코드 대조
> 모드: 읽기 전용. 코드 수정 없음.
> 분류 기호: **A** 완전 구현 / **B** 부분 구현 / **C** 미구현 / **D** 폐기·대체

---

## 요약 (Phase별 구현률)

| Phase | 설계 의도 | 상태 | 구현률 추정 |
|-------|----------|------|------------|
| Phase 1 MVP (관제 엔진 + 학습 골격) | 가설 CRUD, Stage 0~3 엔진, Celery 3태스크, HypothesisEvent/ValidityRecord/InvestorDNA 골격 | **A 거의 완전 구현** | ~95% |
| Phase 2 (모니터링 강화 + 개인화 시작) | 히트맵/그래프 뷰, [근거] 설명, 뉴스 센티먼트, ValidityScore 활성화, DNA 슬라이더, 상관 할인, Adaptive Decay | **C 대부분 미구현** | ~10% |
| Phase 3 — 원안 (커뮤니티 + 지능 강화) | 인기 가설, 따라하기, 템플릿, Chain Sight 연동, 합성 에이전트, Online LR, Neo4j 가설 관계, 가설 복기 | **D 폐기 — Phase 3 redesign으로 대체** | 폐기됨 |
| Phase 3 — 프론트엔드 원안 (FE-PR-7~11) | 3탭 구조(관제/상세/히스토리) + 전제 CRUD, Finviz 히트맵, 히스토리 차트, 마감 아카이브 ValidityMatrix, DNA 프로필 (AccuracyRing) | **D 폐기 — Phase 3 redesign으로 대체** | 폐기됨 |
| Phase 3 redesign (대시보드 리디자인 PR-7~10) | 실제 값 카드(raw_value), AI 요약 섹션, NotableChanges, 미니차트, OverallMoon 제거 | **A 거의 완전 구현 (백엔드 PR-10 일부만 미흡)** | ~85% |
| Phase 4 (벡터화·고도화) | DNA 벡터, 유효성 벡터, 코사인 유사도, 반대 가설 자동 생성, Change Point Detection, 칼만 필터 | **C 미구현** | 0% |

**한 줄 요약:** Phase 1 골격은 완성, Phase 2 개인화 기능은 데이터 모델만 있고 활성화 미흡, Phase 3 원안은 redesign으로 대체되어 대시보드만 진화하고 커뮤니티/학습 고도화 라인은 사실상 동결.

---

## 문서별 상태 테이블

### 핵심 설계 문서 4종

| 문서 | 주제 | 코드 반영 상태 | 비고 |
|------|------|--------------|------|
| `plan/thesis_control_design.md` | UX/API/모델 (v1.0) | **B 부분 구현** | 모델/API 거의 일치하지만 히트맵/그래프 뷰, 인기 가설, 템플릿, Chain Sight 연동 API 미구현 |
| `plan/thesis_control_implementation_guide.md` | Phase 1~4 통합 구현 순서 | **B 부분 구현** | Phase 1 완료, Phase 2 일부, Phase 3 redesign으로 분기 |
| `plan/thesis_control_integrated_roadmap.md` | 수학모델 + 특허기능 통합 로드맵 | **B 부분 구현** | HypothesisEvent/ValidityRecord/InvestorDNA Phase 1 골격 완성. ValidityScore/합성 에이전트/벡터화 모두 미구현 |
| `plan/thesis_control_math_model_final.md` | v2.3.2 수학 엔진 명세 | **A 완전 구현** | Stage 0~3 (data_validator, indicator_scorer, premise_aggregator, thesis_state_machine), Celery 3태스크, snapshot 모두 코드 존재 |

### Phase 1 프론트엔드 PR 보고서 (`docs/thesis_control/frontend/task_done/`)

| 보고서 | PR | 상태 | 핵심 파일 |
|--------|-----|------|----------|
| `FE-PR-1_routing_common_components.md` | 라우팅 7개 + 공통 컴포넌트 5개 | **A 완전 구현** | `lib/api/authAxios.ts`, `app/thesis/layout.tsx`, `(list)/layout.tsx` |
| `FE-PR-2_thesis_list_page.md` | 가설 목록 + 오늘의 변화 + 진입점 | **A 완전 구현** | `ThesisListCard.tsx`, `EntryPointGrid.tsx`, `TodayChangeCard.tsx`, `app/thesis/(list)/page.tsx` |
| `FE-PR-3_builder_implementation.md` | 6단계 대화형 빌더 | **A 완전 구현** | `builder/ChatBubble.tsx` 외 7개, `lib/thesis/conversation.ts`, `app/thesis/new/page.tsx` |
| `FE-PR-3_plan_review_v3.md` | 빌더 계획 v3 리뷰 | 메타 문서 | 6 High / 8 Medium / 14 Low 반영 |
| `FE-PR-4_indicator_setup.md` | 지표 설정 (AI 추천 + 토글) | **A 완전 구현** | `indicators/AddIndicatorSheet.tsx`, `IndicatorSetupCard.tsx`, `RecommendCard.tsx` |
| `FE-PR-5_dashboard.md` | 관제실 대시보드 (달 위상 + 화살표) | **D Phase 3 redesign으로 대체** | OverallMoon, DashboardIndicatorCard, RecentChange는 redesign에서 삭제 예정이었으나 일부 잔존(MoonPhase는 ThesisListCard에서 여전히 사용) |
| `FE-PR-6_alerts_close_qa.md` | 알림 + 마감 + QA | **A 완전 구현** | `alerts/AlertCard.tsx`, `close/OutcomeSelector.tsx`, `lib/thesis/mutations.ts` |
| `Phase2_completion_summary.md` | Phase 2 통합 요약 + Phase 3 계획 | 메타 문서 | Phase 3 계획(FE-PR-7~11)은 **redesign으로 폐기** |

### Phase 3 redesign (`plan/thesis_control_phase3_frontend_redesign.md`)

| PR | 범위 | 상태 | 검증 |
|----|------|------|------|
| PR-7 (Backend) | `display_unit` 필드 + `IndicatorReadingsView` + 응답에 `raw_value`/`change_pct` 추가 | **A 완전 구현** | `thesis/migrations/0004_add_display_unit.py`, `0005_populate_display_unit.py` 존재. `urls.py`에 `indicator-readings` 라우트 등록. `monitoring_views.py:364` |
| PR-8 (Frontend 카드+AI분석) | `RealValueIndicatorCard`, `AISummarySection`, `NotableChangesSection` 신규 + `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 삭제 | **B 부분 구현** | 신규 3종 컴포넌트 존재. `app/thesis/[thesisId]/page.tsx`는 `IndicatorRow`를 사용 (RealValueIndicatorCard는 코드는 있으나 페이지에서는 직접 미사용). OverallMoon/DashboardIndicatorCard/RecentChange는 삭제됨 |
| PR-9 (Frontend 차트+정리) | `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, `MOCK_READINGS`, `useAllIndicatorReadings` 훅 | **B 부분 구현** | 3개 컴포넌트 파일 존재. `app/thesis/[thesisId]/page.tsx`에는 import/렌더링 안 됨 → IndicatorRow가 자체 차트 토글을 가짐 (대체 패턴) |
| PR-10 (AI 파이프라인) | `generate_thesis_summaries` Celery task + LLM 호출 + `notable_changes` 백엔드 연동 | **B 부분 구현** | `thesis/tasks/summary.py` 존재, 동기 Gemini 호출 패턴 적용. Beat 스케줄 등록 여부는 별도 확인 필요 |

### 부속 설계 라인

| 문서 | 주제 | 상태 |
|------|------|------|
| `plan/talking_builder/llm_builder_plan.md` | LLM one-shot proposal 빌더 (Phase A) | **A 완전 구현** (`thesis_builder.py` 2066줄, `prompt_builder.py` 991줄) |
| `plan/talking_builder/redesign_build_plan/01_phase_a_mvp.md` | LLM 빌더 MVP | **A 완전 구현** (`work_done/phase_a_llm_builder.md` 보고서 + builder_state/llm_postprocess/prompt_builder) |
| `plan/talking_builder/redesign_build_plan/02_phase_a_hardening.md` | normalize/validate/fallback 보강 | **A 완전 구현** (`management/commands/builder_stats.py` 등) |
| `plan/talking_builder/redesign_build_plan/03_phase_b_keywords.md` | KeywordCache + collector | **A 완전 구현** (`thesis/models/keyword.py`, `services/keyword_collectors/`, `keyword_cache.py`, `keyword_hint.py`, migrations 0006~0008) |
| `plan/talking_builder/redesign_build_plan/04_phase_c_advanced.md` | 멀티턴 수정, 스트리밍 등 | **C 미구현** |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 대시보드 | **A 완전 구현** (`quarterly_metric_fetcher.py`, `QuarterlySparkline.tsx`, migration 0009 등) |

---

## Phase 3 미구현 항목 상세

### 1. Phase 3 — **원안 (커뮤니티 + 지능 강화)**: 거의 전체 미구현 (D 폐기 가능성)

`plan/thesis_control_implementation_guide.md` Section "Phase 3: 커뮤니티 + 지능 강화 (Week 13~20)" 기준.

| 항목 | 설계 요구 | 코드 상태 | 분류 |
|------|----------|----------|------|
| 인기 가설 시스템 | `GET /popular/`, `PopularThesisCache` 활용 + 추적자 수 + 지지 비율 | **모델만 존재** (`thesis/models/community.py`), View/URL/Serializer 없음 | **C 미구현** |
| 가설 따라하기 (`ThesisFollow`) | `POST /popular/{id}/follow/` + 가설 복제 + 수정 | **모델만 존재**, 엔드포인트 없음 | **C 미구현** |
| 가설 따라하기 후 수정 | "내 방식으로 수정" 플로우 | 진입점 라벨에만 'popular' 존재 (`conversation_views.py` ALLOWED_ENTRY_SOURCES), 실제 가설 복제 로직 없음 | **C 미구현** |
| 템플릿 시스템 | `GET /templates/`, 이벤트형/추세형/비교형/괴리형 | `Thesis.entry_source` choices에 `'template'`만 있고 endpoint 없음 | **C 미구현** |
| Chain Sight 양방향 연동 | "삼성전자 노드 탭 → 가설 세우기" + 역방향 진입 | `thesis/services/keyword_collectors/chain.py`에 `Neo4jChainSightService` import 한 곳, **Chain Sight 노드에서 Thesis Control 진입하는 frontend 진입점 없음** | **C 미구현** |
| 합성 에이전트 부트스트래핑 | `SyntheticBootstrapper`, 20~30개 페르소나, `ValidityRecord.is_synthetic` 마킹 | 어떤 파일에도 `synthetic`/`SyntheticBootstrapper` 키워드 없음. `ValidityRecord.is_synthetic` 필드 부재 | **C 미구현** |
| 합성/실제 블렌딩 | `effective_blend = blend_ratio × (1 - real_count/50)` | 없음 | **C 미구현** |
| Online Logistic Regression | `ThesisWeightLearner` + 마감 가설로 가중치 학습 + Safety Gate (`should_deploy_weights`) | 없음 | **C 미구현** |
| W_j_suggested UI | "AI가 이 가중치를 추천해요" | 없음 | **C 미구현** |
| 주간 재학습 Celery 태스크 | 일요일 새벽 | `eod_pipeline.py`, `summary.py`만 있고 학습 태스크 없음 | **C 미구현** |
| 가설 마감 복기 시스템 | "가장 유용했던 지표 / 예상과 달랐던 부분" 정성 복기 | 마감 페이지(`app/thesis/[thesisId]/close/page.tsx`)는 적중/빗나감/미확정 선택만, "유용했던 지표" 표시 없음 | **C 미구현** |
| Neo4j 가설 관계 그래프 | `HAS_PREMISE`, `SIMILAR_TO`, `OPPOSITE_OF`, `TRACKED_BY` 노드/관계 | `thesis/services` `thesis/tasks` 어디에도 neo4j 쓰기 코드 없음 | **C 미구현** |
| 가설 아카이브 + 학습 이력 UI | 마감된 가설 목록 + 정성 회고 | 마감 페이지에 단건 읽기전용 표시만 있음 (`OUTCOME_DISPLAY` dict 분기), **목록·아카이브 화면 별도 없음** | **C 미구현** |
| 라벨 품질 가이드 (수학모델 12.8) | 마감 UX에 적중 기준 한 줄 고정 | 마감 페이지에 정성 문구 없음 | **C 미구현** |

→ **사실상 Phase 3 원안 전체가 미착수 또는 모델 골격만 존재.** Phase2_completion_summary.md "8. Phase 3 계획"의 FE-PR-7~11 또한 1건도 구현되지 않음 (대체된 흔적은 다음 항목 참고).

### 2. Phase 3 — **프론트엔드 원안 (FE-PR-7~11)**: 폐기됨 (D)

`Phase2_completion_summary.md` Section 8 "Phase 3 계획"에 정의된 5개 PR.

| PR | 설계 요구 | 코드 흔적 | 분류 |
|----|----------|---------|------|
| FE-PR-7 | 대시보드 3탭 구조 (관제/상세/히스토리) + 전제 CRUD UI | 페이지 라우팅에 탭 구조 없음. 전제 CRUD frontend 없음 (백엔드 `ThesisPremiseViewSet`은 존재) | **D 폐기** |
| FE-PR-8 | Finviz 스타일 히트맵 + 지표 weight/direction 편집 | `HeatmapCell`/`HeatmapData` 타입은 `lib/thesis/types.ts`에 있으나 컴포넌트 없음 | **D 폐기** |
| FE-PR-9 | 히스토리 탭 (recharts 라인 + 스냅샷 타임라인) | 별도 히스토리 페이지 없음. IndicatorRow 내부 차트로 부분 대체 | **D 폐기 (재정의)** |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix UI | 마감 페이지 단건 읽기전용 표시만 있고 아카이브 목록 없음 | **D 폐기** |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `InvestorDNA` 모델은 있고 admin 등록까지만. **DNA 프로필 페이지/컴포넌트 일체 없음** | **D 폐기** |

→ **명백히 `thesis_control_phase3_frontend_redesign.md` (2026-03-18 작성)로 방향 전환됨.** 단, redesign 문서가 이 폐기를 명시적으로 선언하지 않음 — 두 라인의 정합성 갭이 문서 상에 잔존.

### 3. Phase 3 redesign (PR-7~10): 거의 구현되었으나 일부 갭

`plan/thesis_control_phase3_frontend_redesign.md` 기준.

#### PR-7 (백엔드 확장) — **A 완전 구현**

| 항목 | 상태 |
|------|------|
| `ThesisIndicator.display_unit` 필드 | ✓ migration 0004_add_display_unit.py |
| 데이터 마이그레이션 `_infer_unit()` fallback | ✓ migration 0005_populate_display_unit.py |
| Dashboard 응답에 `raw_value`, `raw_value_unit`, `previous_raw_value`, `change_pct` | ✓ `monitoring_views.py` |
| `ai_summary`, `notable_changes` 응답 노출 | ✓ |
| `IndicatorReadingsView` + URL 등록 | ✓ `urls.py`에 `'<uuid:thesis_id>/indicators/<uuid:indicator_id>/readings/'` |

#### PR-8 (프론트엔드 카드+AI분석) — **B 부분 구현 (실제 페이지 사용처 불일치)**

| 항목 | 상태 |
|------|------|
| `RealValueIndicatorCard.tsx` 신규 | ✓ 파일 존재, 테스트 존재 (`__tests__/thesis/RealValueIndicatorCard.test.tsx`) |
| `AISummarySection.tsx` 신규 | ✓ |
| `NotableChangesSection.tsx` 신규 | ✓ |
| `OverallMoon.tsx` 삭제 | ✓ 삭제됨 |
| `DashboardIndicatorCard.tsx` 삭제 | ✓ 삭제됨 |
| `RecentChange.tsx` 삭제 | ✓ 삭제됨 |
| `MoonPhase.tsx` 삭제 | **✗ 미삭제** — `ThesisListCard.tsx`, `app/thesis/(list)/page.tsx`에서 여전히 사용 (의도된 잔존: 목록에서 사용) |
| `scoreToPhaseMeta()` 삭제 | **✗ 미삭제** — `lib/thesis/utils.ts`에 존재 (MoonPhase가 사용 중이므로 일관) |
| `app/thesis/[thesisId]/page.tsx`에서 `RealValueIndicatorCard` 사용 | **✗ 불일치** — 실제 페이지는 `IndicatorRow`를 사용. `RealValueIndicatorCard`는 코드는 있으나 페이지에서 import되지 않음 |

→ **갭:** `IndicatorRow.tsx`가 `RealValueIndicatorCard`를 대체 흡수한 것으로 보임. 두 컴포넌트가 공존하며 `RealValueIndicatorCard`는 dead-ish 가능성. 문서·코드 정합성 점검 필요.

#### PR-9 (프론트엔드 미니차트+정리) — **B 부분 구현 (컴포넌트 존재, 페이지 통합 안 됨)**

| 항목 | 상태 |
|------|------|
| `ChartToggleButton.tsx` 신규 | ✓ 파일 존재 |
| `PeriodSelector.tsx` 신규 | ✓ 파일 존재 |
| `IndividualMiniCharts.tsx` 신규 | ✓ 파일 존재 |
| `MOCK_READINGS` mock | 부분 (별도 확인 필요) |
| `useAllIndicatorReadings()` 훅 | 별도 확인 필요 (`lib/thesis/queries.ts`) |
| `app/thesis/[thesisId]/page.tsx`에서 통합 | **✗ 통합 안 됨** — page.tsx에서 3개 컴포넌트 import 없음. `IndicatorRow` 자체 차트 토글이 대체 |
| `CHART_COLORS`, `PERIOD_OPTIONS` constants | 별도 확인 필요 |
| `OverallMoon` / `DashboardIndicatorCard` / `RecentChange` 삭제 | ✓ |

→ **갭:** 차트 인프라(컴포넌트 3종)는 존재하나 페이지 사용처 없음. **dead code 가능성 또는 향후 통합 예정 흔적.** `IndicatorRow`의 차트 통합이 대체 패턴인지 명시적 결정 문서 부재.

#### PR-10 (AI 파이프라인) — **B 부분 구현**

| 항목 | 상태 |
|------|------|
| `generate_thesis_summaries` Celery task | ✓ `thesis/tasks/summary.py` 존재, 동기 Gemini 호출 (Bug #8 회피 코멘트 포함) |
| `ThesisSnapshot.ai_summary` 모델 필드 | ✓ |
| `ThesisSnapshot.notable_changes` 모델 필드 | ✓ |
| `notable_changes` 생성 로직 (`alert_engine` 이벤트 → `NotableChange` 포맷 변환) | `snapshot_builder.py`에 통합되었는지 별도 확인 필요 |
| Beat schedule 등록 (NY 18:35 또는 18:45) | **별도 확인 필요** (config/celery.py + DatabaseScheduler) |
| 주간 건강 검진 (Weekly Health Check) | **C 미구현** (PR-10 6-2 "향후 확장" 단계로 명시됨) |

### 4. Phase 2 미구현 — Phase 3 redesign이 Phase 2를 건너뛴 결과

`thesis_control_implementation_guide.md` Phase 2 (Week 7~12) 항목 중 미구현분.

| 항목 | 설계 요구 | 상태 | 분류 |
|------|----------|------|------|
| 히트맵 뷰 API | Finviz 스타일 색상 그리드 | `HeatmapCell`/`HeatmapData` 타입만 frontend에 있음, API 없음 | **C 미구현** |
| 그래프 뷰 API | 시계열 선 그래프 (지지/중립/반박 Y축) | 부분 (`IndicatorReadingsView`로 raw_value 시계열은 제공, 정규화 점수 그래프는 없음) | **B 부분 구현** |
| 스냅샷 히스토리 API | `GET /{id}/snapshots/` | **없음** — `urls.py`에 snapshots 라우트 없음 | **C 미구현** |
| [근거] 설명 시스템 | LLM 생성 + Redis 캐싱 | indicator/premise에 `rationale`/`context_explanation` 필드는 있으나 `lib/thesis/api.ts`에 explanation endpoint 호출 없음 | **C 미구현** |
| 뉴스 센티먼트 지표 | `news/` 앱 `SentimentHistory` 연동 → Stage 1 | 별도 확인 필요 (sentiment indicator type 존재) | **B 부분 구현 가능성** |
| 내러티브 반감기 지표 | `narrative_momentum` from DailyNewsKeyword | 키워드 collector는 있으나 monitoring 지표 등록 미확인 | **C 미구현** |
| 오늘 이슈 API | `GET /daily-issues/` | `NewsIssuesView` 존재 (`conversation/news-issues/`) — 빌더용 진입점, 별도 `/daily-issues/` 라우트는 없음 | **D 대체 (conversation 라우트로 통합)** |
| `ValidityScore` 모델 + 집계 태스크 | `thesis_type × indicator × regime` 3차원, sample_count≥5 활성화 | **모델 자체 부재.** `learning.py`에 `ValidityScore` 클래스 없음 | **C 미구현** |
| 점진적 활성화 (`is_active`) | sample_count ≥ 5 | 모델 부재로 N/A | **C 미구현** |
| 지표 추천에 유효성 반영 | core/reference/low_impact 티어 분류 | `indicator_matcher.py`(338줄)는 키워드 룰 + LLM fallback만, ValidityScore 참조 없음 | **C 미구현** |
| DNA 적합도 슬라이더 (`personalization_weight`) | 0~1 슬라이더 UI + 블렌딩 로직 | 모델 필드만 있음, UI 일체 없음 (`grep dna /frontend` 결과 0건) | **C 미구현 (모델만)** |
| 역제안 (Contrarian Nudge) | "평소 안 쓰는 유형" 1개 끼워넣기 | 없음 | **C 미구현** |
| 상관계수 자동 할인 | 60일 \|ρ\|≥0.9 → 1/√k | `premise_aggregator.py` 확인 필요 (overlap/divergence 관련 alert만 있음) | **C 미구현** |
| Adaptive Decay/Window | 변동성에 따라 λ↓, window↓ | `indicator_scorer.py` 확인 필요 (`MAD_FLOOR`, `effective_window`는 v2.3.2 명세대로 있음) | **B 부분 (정적값)** |
| Sustained Extreme | `s_decayed≥3 (clip전)` → alert subtype | `alert_engine.py`에 `extreme_volatility` alert는 있음. sustained 분기는 별도 확인 필요 | **B 부분** |
| 알림 고도화 (사용자 반응 기반 빈도 조절) | 사용자 dismiss/read 패턴 → COOLDOWN 동적 조절 | 정적 `cooldown_hours` 필드만 있음 | **C 미구현** |
| `support_direction` 확인 UX | "이 지표가 오르면 유리/불리?" 명시 확인 | builder/indicator 화면에 명시 UI 부재 | **C 미구현** |

### 5. Phase 4 — 전체 미구현 (C)

`thesis_control_integrated_roadmap.md` Section 4 기준.

| 항목 | 상태 |
|------|------|
| DNA 벡터화 (16차원) | **C 미구현** (`dna_vector` 필드 없음) |
| 유효성 벡터화 (6차원) | **C 미구현** (`validity_vector` 필드 없음) |
| 코사인 유사도 추천 | **C 미구현** |
| 사용자 유사도 ("나와 비슷한 투자자") | **C 미구현** |
| 반대 가설 자동 생성 | **C 미구현** |
| 과거 유사 상황 검색 (벡터 유사도) | **C 미구현** |
| Change Point Detection (ruptures) | **C 미구현** |
| 칼만 필터 (Stage 1 노이즈 필터링) | **C 미구현** |

---

## 부록: 정합성 이슈 (문서·코드 불일치)

| # | 이슈 | 근거 | 권고 |
|---|------|------|------|
| 1 | `Phase2_completion_summary.md` Section 8 (FE-PR-7~11)이 폐기되었으나 폐기 표기 없음 | `thesis_control_phase3_frontend_redesign.md`가 사실상 대체 | Phase2_completion_summary.md에 "Section 8 폐기 — redesign으로 대체" 명시 |
| 2 | `RealValueIndicatorCard.tsx`가 코드/테스트는 있으나 실제 dashboard 페이지에서 미사용 | `app/thesis/[thesisId]/page.tsx`는 `IndicatorRow.tsx` 사용 | dead code인지 명시적 결정 (삭제 또는 사용 통합) |
| 3 | `ChartToggleButton.tsx`/`PeriodSelector.tsx`/`IndividualMiniCharts.tsx`가 page.tsx에서 미사용 | IndicatorRow가 자체 차트 토글 제공 | 동일 — 통합 또는 삭제 결정 필요 |
| 4 | `phase3_frontend_redesign.md`가 MoonPhase 삭제를 권장했으나 `ThesisListCard.tsx`/`(list)/page.tsx`에서 여전히 사용 | grep 결과 5건 사용 중 | 의도된 잔존이면 redesign 문서에 예외 명시 |
| 5 | `implementation_guide.md` Phase 2~3 항목들이 redesign에 의해 부분 보류된 채 문서가 갱신되지 않음 | Phase 2 항목 중 80%가 미구현 상태 | implementation_guide에 "Phase 2/3 원안: redesign 우선 진행으로 보류" 명시 |
| 6 | `InvestorDNA` 모델은 있고 admin 등록까지 됐으나 frontend DNA UI 일체 부재 | `grep -r "dna\|DNA" frontend/components/thesis frontend/app/thesis frontend/lib/thesis` 결과 0건 | 데이터 축적은 되고 있으니 의도이면 OK, 아니면 Phase 4 진입 전 가시화 검토 |
| 7 | `ThesisFollow`, `PopularThesisCache` 모델만 있고 View/Serializer/URL 없음 | `thesis/views/__init__.py` 미등록 | 모델 정리(unused) 또는 인기 가설 API 착수 결정 |
| 8 | `entry_source` choices에 `popular`, `template`, `chainsight` 가 있으나 해당 진입 플로우 없음 | `conversation_views.py:28` ALLOWED_ENTRY_SOURCES에 포함 + frontend `new/page.tsx`에서 `popular`는 free_input으로 폴백 처리 | 미구현 진입 경로 정리(choices 축소) 또는 구현 |

---

## 결론

- **건강한 영역**: Phase 1 (관제 엔진 v2.3.2 + 학습 모델 골격) 및 LLM 빌더 라인은 완성도 높음. 분기 지표 대시보드, KeywordCache 등 부속 라인도 잘 정착.
- **방향 전환**: Phase 3 원안(커뮤니티 + Online LR + 합성 에이전트 + DNA 프로필 UI)은 **Phase 3 redesign(대시보드 리디자인)으로 사실상 대체**. 단, 두 라인의 정합성 선언이 문서에 부재.
- **죽은 코드 위험**: `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts` 4종이 페이지 미사용 상태 (IndicatorRow가 대체). 명시적 결정 필요.
- **다음 진입 후보**: (a) `ValidityScore` + 합성 에이전트로 Cold Start 해결, (b) 인기 가설/템플릿/Chain Sight 연동(설계는 풍부, 코드 부재), (c) DNA 가시화 UI.
