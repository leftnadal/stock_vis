# Thesis Control 설계 갭 감사

> 감사일: 2026-05-18
> 범위: `docs/thesis_control/` (설계/계획) vs `thesis/` (BE 구현) + `frontend/components/thesis/`, `frontend/app/thesis/`, `frontend/lib/thesis/` (FE 구현)
> 분류 기준: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 요약 (Phase별 구현률)

| 영역 | 설계 항목 | 구현 상태 | 완성도 |
|------|----------|----------|-------|
| **Phase 1 (MVP, 관제 엔진 v2.3.2)** | 모델 + Stage 0~3 + Celery 3 task + 기본 CRUD/대화 API | A 대부분 | **95%** |
| **Phase 1 학습 인프라 (HypothesisEvent / ValidityRecord / InvestorDNA)** | 모델 + 이벤트 기록 + 마감시 갱신 | A | **100%** (BE), C (FE 노출 0%) |
| **Phase 2 BE (뷰 확장 + 유효성 활성화 + 뉴스 연동)** | 히트맵·그래프 API, 유효성 집계, DNA 슬라이더, 뉴스 센티먼트 | B (뉴스 이슈 변환·suggest 일부 / 유효성 집계·DNA 슬라이더 0) | **40%** |
| **Phase 2 FE (FE-PR-1~6)** | 라우팅·목록·빌더·지표·대시보드·알림·마감 | A | **100%** |
| **Phase 3 FE 원안 (FE-PR-7~11: 깊이·회고·프로필)** | 3탭 대시보드, 히스토리, 마감 아카이브, 투자자 DNA | D (전량 폐기 → Phase 3 리디자인으로 대체) | — |
| **Phase 3 FE 리디자인 (PR-7~9: 실제 값 카드 + AI 분석 + 미니차트)** | display_unit, RealValueIndicatorCard, AISummary, NotableChanges, ChartToggle, PeriodSelector, IndividualMiniCharts | A | **100%** |
| **Phase 3 BE PR-10 (AI 모니터링 파이프라인)** | `generate_thesis_summaries`, `notable_changes` 채움 | A (summary task) / B (notable_changes 일부 채움) | **70%** |
| **Phase 3 커뮤니티 (인기 가설 / 따라하기 / 템플릿 / Chain Sight 연동)** | 5개 진입 경로 중 3개 (popular, template, chainsight) | C | **0%** |
| **Phase 3 합성 에이전트 + Online LR (자동 학습)** | SyntheticBootstrapper, ThesisWeightLearner, ValidityScore | C | **0%** |
| **Phase 3 가설 복기 / Neo4j 가설 그래프** | 마감 복기 UI, SIMILAR_TO·OPPOSITE_OF 관계 | C | **0%** |
| **Phase 4 (벡터화, 반대가설 자동생성)** | DNA 16차원, ValidityScore 6차원, Change-Point | C | **0%** |
| **빌더 재설계 v4 (talking_builder)** | Phase A (LLM one-shot, 프리셋, fallback) | A | **100%** |
| **빌더 재설계 v4 Phase B/C** | KeywordCache + collectors + hint builder + monitoring / 멀티턴·스트리밍 | B (KeywordCache 모델만 존재) | **20%** |
| **분기 지표 대시보드** | metrics fetcher, QuarterlySparkline, 다분기 추이 | A | **100%** |

**전체 Phase 1~2 핵심 루프**(가설 세우기→지표→관제→알림→마감)는 **완전 구현**. Phase 3는 **대시보드 리디자인만** 완성되었고, 그 외 Phase 3 항목(커뮤니티·복기·자동학습·DNA UI·Neo4j)은 전부 미구현. 보고된 "Phase 3 진행 중"이라는 표현의 실체는 **Phase 3 대시보드 리디자인 PR-7~9 + AI summary task만** 완성된 상태.

---

## 문서별 상태 테이블

| 설계 문서 | 의도 | 구현 상태 | 핵심 갭 |
|---------|------|----------|---------|
| `docs/thesis_control/plan/thesis_control_design.md` | UX/모델/API 전체 (Phase 1~4) | B | Phase 3 커뮤니티·복기·Neo4j 미구현, Phase 4 전부 미구현 |
| `docs/thesis_control/plan/thesis_control_math_model_final.md` | v2.3.2 스코어링 엔진 | A | Stage 0~3 + Snapshot + Alert throttling 전체 구현됨 (`data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `thesis_state_machine.py`, `arrow_calculator.py`, `snapshot_builder.py`, `alert_engine.py`). 상관계수 자동 할인·Adaptive Decay·Sustained Extreme(Phase 2 추가분) 흔적 없음 |
| `docs/thesis_control/plan/thesis_control_implementation_guide.md` | Phase 1~4 통합 로드맵 | B | Week 1~6 Phase 1 전부 완료. Week 7~12 Phase 2 중 "유효성 활성화, DNA 슬라이더, 역제안, 상관 할인" 0건 구현. Week 13~20 Phase 3 중 "합성 에이전트, Online LR, 가설 복기, Neo4j 관계 그래프" 0건 |
| `docs/thesis_control/plan/thesis_control_integrated_roadmap.md` | 학습/개인화 레이어 (HypothesisEvent / ValidityRecord / InvestorDNA / ValidityScore / SyntheticBootstrapper / DNA 슬라이더 / 역제안) | B | HypothesisEvent + ValidityRecord + InvestorDNA 모델·기록·집계 모두 구현(A). 그러나 **ValidityScore 모델·집계 태스크 없음**, **SyntheticBootstrapper 없음**, **DNA 슬라이더·역제안 0건**, **Online LR(ThesisWeightLearner) 없음**, **벡터화 0건** |
| `docs/thesis_control/plan/thesis_control_phase3_frontend_redesign.md` | 대시보드 리디자인 PR-7~10 | A (PR-7~9) / B (PR-10) | PR-7~9 완전 구현 (`display_unit` 필드 + migration `0004/0005`, `RealValueIndicatorCard`, `AISummarySection`, `NotableChangesSection`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, `IndicatorReadingsView` 모두 존재). PR-10 중 `generate_thesis_summaries` task는 `thesis/tasks/summary.py`에 있음. `notable_changes` JSONField 채움은 `snapshot_builder.py` 또는 `create_snapshots_and_alerts` 내부에 일부 흐름이 있으나 설계서 그대로의 alert_engine 재활용 패턴인지 확인 필요(부분 충족) |
| `docs/thesis_control/thesis_control_user_experience.md` | 가설 목록·빌더(6단계+제안)·대시보드·마감 UX | A | 6단계 빌더, suggestion mode, 마감 UX 모두 구현. 사용자 흐름 명세 위반 없음 |
| `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_1~5.md` | Phase 1 FE 5 PR | A | 모두 FE-PR-1~5로 완료 |
| `docs/thesis_control/thesis_control_phase1_prompts.md` / `..._frontend_prompts.md` | Claude Code 프롬프트 | A | 결과물 모두 머지됨 |
| `docs/thesis_control/frontend/task_done/FE-PR-1~6_*.md` | Phase 2 핵심 루프 6 PR | A | 컴포넌트 84개, 라우트 6개 페이지 모두 존재 (`/thesis`, `/thesis/new`, `/thesis/alerts`, `/thesis/[id]`, `/thesis/[id]/indicators`, `/thesis/[id]/close`) |
| `docs/thesis_control/frontend/task_done/Phase2_completion_summary.md` | Phase 2 완료 + FE-PR-7~11 계획 표 | D | "FE-PR-7~11 = 3탭/히트맵/히스토리/마감 아카이브/DNA" 계획은 **전량 폐기**되고 Phase 3 리디자인(다른 PR-7~10, 실제 값 + AI 분석 + 미니차트)으로 **대체됨**. 폐기 사실이 `Phase2_completion_summary.md`에 명시되지 않아 문서 자체가 stale |
| `docs/thesis_control/work_done/phase_a_llm_builder.md` | LLM 빌더 Phase A (PR-1~3 + Hardening) | A | `thesis/services/builder_state.py`, `prompt_builder.py`(991줄, INDICATOR_CATALOG 포함), `llm_postprocess.py`, `builder_events.py`, `feature_flags.py` 전부 존재. `thesis_builder.py`(2066줄)에 LLM·wizard 양쪽 흐름 모두 |
| `docs/thesis_control/plan/talking_builder/llm_builder_plan.md` | LLM 빌더 초기 계획 | A | Phase A 완료로 흡수 |
| `docs/thesis_control/plan/talking_builder/thesis_builder_redesign_v2.md` | v2 재설계 (사전 단계) | D | v4(redesign_build_plan)로 대체됨 |
| `docs/thesis_control/plan/talking_builder/redesign_build_plan/00~05` | v4: Phase A-MVP / A-Hardening / B (KeywordCache+collectors) / C (Advanced) | B | Phase A 전부 완료. Phase B 중 `KeywordCache` 모델·`keyword_cache.py` 서비스·`keyword_collectors/chain.py`·`keyword_health_check`/`check_keywords` 관리 명령은 존재(이름 일치). 그러나 news/eod collector 통합, hint builder 프롬프트 주입 검증, Layer A/B/C 모니터링 풀세트 확인 필요. Phase C(멀티턴·스트리밍·Health Report·micro-fact·scoring) 0건 |
| `docs/thesis_control/plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 표시 + 4분기 미니 차트 | A | `quarterly_metric_fetcher.py`(364줄), `_prefetch_quarterly_data`, `QuarterlySparkline.tsx`, `IndicatorRow.tsx`, `fiscal_label/quarterly_history/is_quarterly/comparison_type` 응답 필드 모두 구현 |

---

## Phase 3 미구현 항목 상세

> "Phase 3"는 두 가지 의미가 혼재한다.
> ① 원안 `Phase2_completion_summary.md`의 FE-PR-7~11 = 깊이·회고·프로필 (D, 폐기)
> ② 리디자인 `thesis_control_phase3_frontend_redesign.md`의 PR-7~10 = 실제 값/AI 요약/미니차트 (A, 완성)
> ③ 백엔드 Phase 3 (통합 로드맵 Section 3) = 합성 에이전트 + Online LR + Neo4j (C, 0%)
> 아래는 ①·③에서 끝나지 않은 항목만 정리.

### A. 폐기된 원안 FE-PR-7~11 (Phase2_completion_summary.md 표)

| 원안 PR | 설계 의도 | 상태 | 비고 |
|---------|----------|------|------|
| FE-PR-7 | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD | **D 폐기** | 리디자인이 단일 화면 유지로 결정 (점수·달 위상·탭 제거). `app/thesis/[thesisId]/page.tsx`에 탭 없음 |
| FE-PR-8 | Finviz 스타일 히트맵 + weight/direction 편집 | **D 폐기** | DashboardView가 `heatmap.rows/cols/cells`는 반환하지만 사용처는 단순 grid. 별도 Finviz 히트맵 컴포넌트 없음 |
| FE-PR-9 | 히스토리 탭 (recharts + 스냅샷 타임라인) | **C 미구현** (부분 대체) | `IndividualMiniCharts.tsx`로 지표별 미니차트는 대체. 그러나 "스냅샷 타임라인" UI는 없음 (`ThesisSnapshot` 시계열 노출 0) |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix | **C 미구현** | 마감된 가설 목록 페이지 없음 (`/thesis`는 `status` 필터 쿼리는 가능하나 아카이브 전용 UX 0). ValidityMatrix 시각화 0 |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | **C 미구현** | InvestorDNA 모델·집계는 BE에 100% 있으나 **API 노출 0**, **FE 페이지 0**, **그래프 컴포넌트 0**. 프로젝트 메모리상으로도 `/thesis/profile`류 라우트 없음 |

### B. 백엔드 Phase 3 (integrated_roadmap.md Section 3)

| 항목 | 설계 출처 | 상태 | 코드 위치(있다면) |
|------|----------|------|------|
| `ValidityScore` 모델 (집계 결과 테이블) | integrated_roadmap §2.1 | **C** | 없음. `ValidityRecord`만 있고 집계 태이블 없음 |
| `ValidityScore` 주 1회 집계 Celery task | integrated_roadmap §2.1 / impl_guide Week 9~10 | **C** | `thesis/tasks/` 하 `summary.py`, `eod_pipeline.py` 2개만 존재 |
| 지표 추천에 유효성 점수 반영 (core/reference/low_impact 티어) | integrated_roadmap §2.2 | **C** | `indicator_matcher.py`(338줄)에 validity_boost 흔적 없음 |
| DNA 슬라이더 (personalization_weight 적용) | integrated_roadmap §2.3 | **C** | 모델 필드(`InvestorDNA.personalization_weight`)만 존재. 블렌딩 로직·UI 0 |
| 역제안 (Contrarian Nudge) | integrated_roadmap §2.4 | **C** | 흔적 없음 |
| `support_direction` 확인 UX | math_model §12.5 | **C** | 빌더에 "이 지표가 오르면 유리/불리?" 단계 없음 |
| 상관계수 자동 할인 (60일 \|ρ\|≥0.9 → 1/√k) | math_model Phase 2 | **C** | `premise_aggregator.py`(205줄)에 상관행렬 로직 없음 |
| Adaptive Decay/Window (변동성 기반) | math_model Phase 2 | **C** | `indicator_scorer.py`에 고정 decay만 |
| Sustained Extreme alert subtype | math_model Phase 2 | **C** | `alert_engine.py`에 subtype 분기 없음 |
| 인기 가설 시스템 + `/popular/` API | design §2.3 경로 3 + impl_guide Week 13~14 | **C** | `PopularThesisCache` 모델 있으나 갱신 태스크·View·URL 모두 없음. `thesis/urls.py`에 popular 경로 0 |
| 가설 따라하기 (`POST /popular/{id}/follow/`) | design §2.3 | **C** | `ThesisFollow` 모델 있으나 View 없음 |
| 템플릿 (`/templates/`, 4유형) | design §2.3 경로 4 | **C** | View·데이터·URL 모두 없음 |
| Chain Sight 양방향 연동 | design §2.3 경로 5 | **C** | Chain Sight 그래프 화면에서 "가설 세우기" 진입점 없음, 역방향 추천 없음 |
| 합성 에이전트 부트스트래핑 (SYNTHETIC_PERSONAS, SyntheticBootstrapper) | integrated_roadmap §3.1 | **C** | 흔적 없음 (`grep synthetic` 0건) |
| 합성/실제 블렌딩 (`blend_ratio`, `is_synthetic`) | integrated_roadmap §3.3 | **C** | ValidityRecord에 `is_synthetic` 필드 없음 (`learning.py:55-94`) |
| Online Logistic Regression (`ThesisWeightLearner`, `W_j_suggested`, Safety Gate, 주간 재학습) | math_model Phase 3 / integrated_roadmap §3.2 | **C** | 흔적 없음 (`grep WeightLearner` 0건) |
| 가설 마감 복기 시스템 ("가장 유용했던 지표", "예상과 달랐던 부분") | design §3.9 / impl_guide Week 19~20 | **B** | 마감 자체와 ValidityRecord 기록은 됨. 복기 화면·요약 LLM·아카이브 UI 모두 없음 |
| Neo4j 가설 관계 그래프 (HAS_PREMISE / SIMILAR_TO / OPPOSITE_OF / TRACKED_BY / TRIGGERED_BY) | design §4.4 / impl_guide Week 19~20 | **C** | `thesis/` 내 Neo4j 동기화 0. `keyword_collectors/chain.py`만 Chain Sight Neo4j 참조 |
| Phase 4 (DNA 16차원 벡터, ValidityScore 6차원, 사용자 유사도, 반대가설 자동생성, Change Point, 칼만 필터) | integrated_roadmap §4 / design Phase 4 | **C** | 전부 0% |

### C. 빌더 재설계 v4 잔여 (talking_builder/redesign_build_plan)

| 항목 | Phase | 상태 |
|------|-------|------|
| `KeywordCache` 모델 + Admin | B / PR-8 | **A** (`thesis/models/keyword.py`(46줄) + `keyword_cache.py`(78줄) + migration `0006_add_keyword_cache.py`, `0007_keyword_cache_add_strength.py`) |
| `News`/`EOD`/`Chain` Keyword Collector 3종 통합 | B / PR-9~10 | **B** (`thesis/services/keyword_collectors/chain.py`만 보임. news/eod collector 별도 파일 확인 필요) |
| Keyword Hint 빌더 통합 (`keyword_hint.py`) | B / PR-11 | **A** (`thesis/services/keyword_hint.py`(100줄) 존재) |
| `check_keywords` / `keyword_health_check` 관리 명령 | B 모니터링 | **A** (`thesis/management/commands/check_keywords.py`, `keyword_health_check.py` 존재) |
| 멀티턴 수정 대화 (`Edit` → "다시 만들어줘") | B / PR-12 | **C** (LLM 빌더 흐름은 proposal → preset → confirm 단방향) |
| Daily Health Report / batch versioning | B 후반 | **C** |
| `MiniDashboardPreview`, 스트리밍, Guided Suggestion | C | **C** |
| keyword strength / micro-fact / scoring 고도화 | C+ | **B** (`0007_keyword_cache_add_strength.py`로 strength 필드만 추가됨, 풀파이프라인 사용처 확인 필요) |

---

## 주의 / Stale 문서

1. **`Phase2_completion_summary.md` (2026-03-16)**: §8 "Phase 3 계획" 표(FE-PR-7~11)가 **현실과 다름**. 그 다음 작성된 `thesis_control_phase3_frontend_redesign.md`(2026-03-18)에 의해 전량 폐기되고 다른 의미의 PR-7~10으로 교체. 문서 머리에 "이 계획은 폐기됨" 명시 권장.
2. **`Phase2_completion_summary.md` 표의 컴포넌트 "OverallMoon, DashboardIndicatorCard, RecentChange"** → 리디자인 PR-9에서 **삭제 대상**으로 지정. 현재 코드에 해당 파일 없음(삭제 완료 확인). 그러나 완료 요약에는 여전히 존재한다고 기록됨 → stale.
3. **`docs/thesis_control/work_done/phase_a_llm_builder.md`**는 Phase A-MVP(PR-1~3) + Hardening(PR-4~7)까지 커버. 그러나 redesign_build_plan의 Phase B PR-8~12 완료 보고서가 `work_done/`에 없음. Phase B 진행 정도는 코드로만 추정 가능.
4. **CLAUDE.md의 "Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"** 진행 중 표기는 stale. 실제 Phase 3는 ① 대시보드 리디자인만 완성, ② 깊이·회고·프로필은 모두 폐기 또는 미착수.

---

## 권고 (감사 결과만, 코드 수정 없음)

1. `Phase2_completion_summary.md` §8 표에 "이 PR 시리즈는 thesis_control_phase3_frontend_redesign.md로 대체됨" 1줄 추가.
2. CLAUDE.md "진행 중" 섹션의 Thesis Control Phase 3 항목을 "Phase 3 대시보드 리디자인 완료, 그 외 Phase 3(커뮤니티/복기/DNA UI/Neo4j/자동학습) 미착수"로 정정.
3. `integrated_roadmap.md`에서 정의된 `ValidityScore` 모델·집계 태스크가 빠져 있어 "Phase 2 유효성 활성화"의 모든 후속 작업이 봉인 상태 → Phase 3 진입 전 선결 과제 명시 필요.
4. `PopularThesisCache`·`ThesisFollow` 모델은 만들어졌으나 View/URL 0 → 미사용 모델 처리(삭제 또는 사용처 추가) 결정 필요.
