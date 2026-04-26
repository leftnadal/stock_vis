# Thesis Control 설계 갭 감사

> 감사일: 2026-04-27
> 감사 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` 백엔드 + `frontend/components/thesis/` 프론트엔드
> 감사 방식: 읽기 전용 — 코드/문서 미수정
> 분류: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 0. 사전 컨텍스트

### Phase 정의 충돌 사항 (중요)

설계 문서가 두 가지 서로 다른 Phase 3 정의를 가지고 있어 본 감사는 다음과 같이 분리해서 평가한다.

| 출처 | Phase 3 의미 |
|---|---|
| `Phase2_completion_summary.md` (2026-03-16) | **FE-PR-7~11**: 대시보드 탭 구조, 히트맵, 히스토리 차트, 마감 아카이브, 투자자 DNA 프로필 |
| `plan/thesis_control_phase3_frontend_redesign.md` (2026-03-18) | **PR-7~10**: 백엔드 raw_value 확장, AI 분석 카드, 미니차트, AI 모니터링 파이프라인 — 위 Phase 3 계획을 사실상 폐기·재정의 |
| `plan/thesis_control_integrated_roadmap.md` | **Phase 3**: 합성 에이전트 + Online LR + Neo4j 가설 그래프 + 가설 마감 복기 시스템 |

**해석**: redesign 문서가 원래의 FE-PR-7~11(탭/히트맵/DNA)을 폐기하고 "내부 점수 숨기고 실제 값 보여주기"로 방향 전환. 일부(실제 값 카드, 미니차트)는 PR-7~9으로 구현 완료. 나머지(통합 로드맵 Phase 3 항목)는 미진행.

---

## 1. 요약 (Phase별 구현률)

| Phase | 백엔드 | 프론트엔드 | 종합 |
|---|---|---|---|
| **Phase 1 — MVP (수학 엔진 + 이벤트 수집)** | 95% (A) | 95% (A) | **A** 완전 구현 |
| **Phase 2 — 모니터링 강화 + 개인화 시작** | 50% (B) | 40% (B) | **B** 부분 구현 |
| **Phase 3 — 커뮤니티 + 지능 강화 (통합 로드맵)** | 5% (C) | 0% (C) | **C** 거의 미구현 |
| **Phase 3 redesign — 실제 값 대시보드 (PR-7~9)** | 100% (A) | 100% (A) | **A** 완전 구현 |
| **Phase 3 redesign — AI 모니터링 파이프라인 (PR-10)** | 5% (C) | n/a | **C** 미구현 |
| **Phase A — LLM 빌더** | 100% (A) | 100% (A) | **A** 완전 구현 |
| **Phase B — Keyword Enrichment** | 100% (A) | n/a | **A** 완전 구현 (백엔드만) |
| **Phase 4 — 벡터 스코어링** | 0% (C) | 0% (C) | **C** 미진행 |

세부 근거는 §2 참조.

---

## 2. 문서별 상태 테이블

### 2.1 핵심 설계 문서 (5개)

| 문서 | 상태 | 핵심 미반영 항목 |
|---|---|---|
| `plan/thesis_control_design.md` (v1.0, 2026-02-27) — 원본 설계 | **B** 부분 | 히트맵/그래프뷰, [근거] 설명 API, 인기/템플릿/Chain Sight 진입 5경로 중 2경로(news, free_input)만 구현 |
| `plan/thesis_control_implementation_guide.md` | **B** 부분 | Section 7 (Phase 3 커뮤니티/Neo4j) 미구현 |
| `plan/thesis_control_integrated_roadmap.md` (수학 모델 v2.3.2 + 특허) | **B** 부분 | Phase 1~A는 완료. Phase 2 (유효성 활성화, DNA 슬라이더) Phase 3 (합성 에이전트, Online LR) 미진행 |
| `plan/thesis_control_math_model_final.md` (v2.3.2) | **A** 완전 | Stage 0~3 + snapshot + alert throttling 모두 구현 (`thesis/services/data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `thesis_state_machine.py`, `alert_engine.py`, `snapshot_builder.py`) |
| `plan/thesis_control_phase3_frontend_redesign.md` (FINAL, 2026-03-18) | **B** 부분 | PR-7~9 완료 (실제 값 카드, 미니차트). PR-10 (Celery `generate_thesis_summaries` + notable_changes 자동 채움) 미구현 |

### 2.2 빌더 재설계 6개 문서 (`plan/talking_builder/redesign_build_plan/`)

| 문서 | 상태 | 비고 |
|---|---|---|
| `00_total_plan.md` (v4) | **A** Phase A-MVP, A-Hardening, B 모두 반영 |
| `01_phase_a_mvp.md` | **A** 완료 (`work_done/phase_a_llm_builder.md`에 완료 보고) |
| `02_phase_a_hardening.md` | **A** 완료 (PR-4~7 적용, `builder_stats` 명령 포함) |
| `03_phase_b_keywords.md` | **A** KeywordCache 모델, keyword_collectors (chain/eod/news), keyword_hint, check_keywords command 모두 구현 — Feature flag만 OFF |
| `04_phase_c_advanced.md` | **C** 미구현 (MiniDashboard, Guided Suggestion, 스트리밍) |
| `05_summary.md` | n/a |

### 2.3 프론트엔드 PR 완료 보고서 (`frontend/task_done/`)

| 보고서 | 코드 일치 여부 |
|---|---|
| `FE-PR-1_routing_common_components.md` | **일치**: 라우팅 7개, common 컴포넌트 5개, authAxios 단일 소스, AuthContext 마이그레이션 모두 확인 |
| `FE-PR-2_thesis_list_page.md` | **일치**: ThesisListCard, TodayChangeCard, EntryPointGrid, sortThesesByPriority, USE_MOCK 분기 모두 확인 |
| `FE-PR-3_builder_implementation.md` (+ `FE-PR-3_plan_review_v3.md`) | **일치**: 6단계 wizard 빌더 컴포넌트 모두 존재. 단 — Phase A LLM 빌더가 추가로 적용되어 빌더 페이지가 1072줄로 확장됨 (LLM proposal/preset/confirm 3턴 모드 추가) |
| `FE-PR-4_indicator_setup.md` | **일치**: IndicatorSetupCard, AddIndicatorSheet, RecommendCard, Route Group `(list)` 분리 모두 확인. 단 — `indicatorMutations.ts` 보고서상 `mutations.ts`로 통합되었어야 하나 두 파일 모두 잔존 |
| `FE-PR-5_dashboard.md` | **부분 폐기**: OverallMoon, DashboardIndicatorCard, RecentChange는 redesign에서 삭제됨. RealValueIndicatorCard, AISummarySection, NotableChangesSection으로 교체 |
| `FE-PR-6_alerts_close_qa.md` | **일치**: AlertCard, AlertFilterTabs, EmptyAlerts, OutcomeSelector, CloseConfirmDialog 모두 확인. mutations.ts 통합 보고했으나 indicatorMutations.ts 잔존 (불일치) |
| `Phase2_completion_summary.md` (2026-03-16) | **부분 폐기**: 마지막 섹션의 FE-PR-7~11 계획(탭/히트맵/DNA)은 2일 후 redesign에서 폐기됨 |

### 2.4 작업 진행 보고서 (`work_done/`)

| 보고서 | 상태 |
|---|---|
| `phase_a_llm_builder.md` (Phase A-MVP + Hardening 완료, 2026-03-20) | **일치**: builder_state.py, prompt_builder.py, llm_postprocess.py, builder_events.py, feature_flags.py, PresetSelector.tsx, IndicatorCard.tsx 모두 코드에 존재. 테스트 104개 보고 |

### 2.5 추가 plan 문서

| 문서 | 상태 |
|---|---|
| `plan/talking_builder/llm_builder_plan.md` | 초기 계획 (Phase A~C). Phase A~B는 `work_done/phase_a_llm_builder.md`로 완료 반영. Phase C 미구현 |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | **A** 완료. metrics fetcher (`thesis/services/quarterly_metric_fetcher.py`), DashboardView 분기 지표 batch 조회, RealValueIndicatorCard + QuarterlySparkline + IndividualMiniCharts 모두 존재 |
| `plan/talking_builder/thesis_builder_redesign_v2.md` | redesign v4가 적용되어 v2는 superseded. 별도 갭 평가 불필요 |
| `thesis_control_user_experience.md` (2026-03-30) | 현재 구현된 UX 묘사 — Suggestion Mode 포함하여 코드와 일치. 단 Step 5 "+ 지표 추가" 시트의 72개 지표 분류 (시장 27 + 거시 11 + 기술 9 + 펀더멘털 11 + 재무체질 14 + 심리 1)는 INDICATOR_CATALOG와 교차검증 미수행 |

---

## 3. Phase 3 미구현 항목 상세

### 3.1 두 가지 Phase 3 정의의 운명

```
Phase 3 (원안, Phase2_completion_summary.md)
├── FE-PR-7  대시보드 탭 구조 (관제/상세/히스토리)         → 폐기 (D)
├── FE-PR-8  히트맵 + 지표 상세 편집 (weight/direction)   → 폐기 (D)
├── FE-PR-9  히스토리 탭 (recharts 라인 차트)             → 폐기 (D)
├── FE-PR-10 마감 아카이브 + ValidityMatrix              → 미구현 (C)
└── FE-PR-11 투자자 DNA 프로필 (AccuracyRing 등)        → 미구현 (C)

Phase 3 (redesign, thesis_control_phase3_frontend_redesign.md)
├── PR-7  백엔드 (display_unit + raw_value + ai_summary 필드)  → 완료 (A)
├── PR-8  카드 + AI 분석 (실제 값 카드)                          → 완료 (A)
├── PR-9  차트 + 정리 (미니차트 + 토글)                           → 완료 (A)
└── PR-10 AI 모니터링 파이프라인 (Celery generate_thesis_summaries) → 미구현 (C)

Phase 3 (통합 로드맵, integrated_roadmap.md)
├── 인기 가설/따라하기/템플릿/Chain Sight 연동                    → 미구현 (C)
├── 합성 에이전트 부트스트래핑 (SyntheticBootstrapper)            → 미구현 (C)
├── Online Logistic Regression (ThesisWeightLearner)            → 미구현 (C)
├── 가설 마감 복기 시스템 (유용했던 지표 / 예상과 달랐던 부분)         → 미구현 (C)
└── Neo4j 가설 관계 그래프 (SIMILAR_TO/OPPOSITE_OF/HAS_PREMISE)   → 미구현 (C)
```

### 3.2 미구현 항목 — 백엔드

| # | 항목 | 설계 출처 | 영향 | 코드 흔적 |
|---|---|---|---|---|
| B1 | `generate_thesis_summaries` Celery task (07:30) | design 5.3 + redesign PR-10 | 대시보드 `ai_summary` 빈 문자열로 표시됨. 모델 필드 (`ThesisSnapshot.ai_summary`)는 존재하나 채우는 로직 없음 | `config/celery.py`에 beat 등록 안 됨 |
| B2 | `notable_changes` JSON 자동 채움 로직 | redesign PR-10 7-2 | `ThesisSnapshot.notable_changes` 필드 존재. `snapshot_builder.py`에서 alert 이벤트를 변환하여 채워야 하나 미구현 | dashboard view는 `latest_snapshot.notable_changes`를 그대로 응답 → 항상 `[]` |
| B3 | `prepare_daily_issues` Celery task (07:00) | design 5.3 | 대시보드 진입점 "오늘 이슈"가 존재하나, 별도 캐시 갱신 없이 `NewsIssuesView`가 매번 NewsArticle을 조회 | 미등록 |
| B4 | `scan_thesis_news` Celery task (2시간) | design 5.3 | active 가설별 관련 뉴스 알림 미생성. `news_event` alert_type은 모델 choices에는 없고 alert_engine에 트리거 없음 | 미등록 |
| B5 | `update_popular_thesis_cache` Celery task (08:00) | design 5.3 | 인기 가설 기능 자체 없음 | `PopularThesisCache` 모델만 존재 |
| B6 | GET `/{id}/snapshots/` 스냅샷 히스토리 API | design 6.1 | 그래프뷰 데이터 소스 부재. 단 `IndicatorReadingsView`로 지표별 시계열 대체 가능 | 미구현 |
| B7 | GET `/{id}/summary/` AI 요약 API | design 6.1 | dashboard에 인라인 포함되어 별도 엔드포인트 우선순위 낮음 | dashboard에 통합 |
| B8 | GET `/{id}/indicators/{iid}/explanation/` [근거] 설명 API | design 6.1 + 2.4 | UI에 [근거] 버튼 자체가 없음. `recommendation_reason`/`description` 필드는 dashboard에 인라인 포함 | 별도 API 미구현 |
| B9 | GET `/popular/` + POST `/popular/{id}/follow/` + GET `/popular/{id}/detail/` | design 6.1 | 인기 가설 진입점 미구현 | `entry_source`에는 `popular` 등록되어 있으나 작동 경로 없음 |
| B10 | GET `/templates/` + GET `/templates/{type}/` | design 6.1 | 템플릿 진입점 미구현 | `entry_source`에는 `template` 등록되어 있으나 작동 경로 없음 |
| B11 | Chain Sight 양방향 연동 | design 2.3 경로 5 + integrated 3.1 | 미구현 | `entry_source`에 `chainsight` 등록되어 있으나 진입 경로 없음 |
| B12 | Neo4j 가설 관계 그래프 (`SIMILAR_TO`, `OPPOSITE_OF`, `HAS_PREMISE`) | design 4.4 + integrated Section 1.4 | 미구현. `graph_analysis/` 앱 사용 흔적 없음 | 미구현 |
| B13 | ValidityScore 집계 (Phase 2 활성화) | integrated 2.1 | `ValidityRecord` 누적은 되지만 ValidityScore 테이블/태스크 없음 | 모델 미정의 |
| B14 | DNA 슬라이더 + 역제안 (Phase 2) | integrated 2.3~2.4 | `InvestorDNA.personalization_weight` 필드는 존재하나 매칭 로직 미적용 | `indicator_matcher.py`에 적용 흔적 없음 |
| B15 | 합성 에이전트 부트스트래핑 (`SyntheticBootstrapper`, `is_synthetic` 필드) | integrated 3.1 | 미구현 | `ValidityRecord`에 `is_synthetic` 필드 없음 |
| B16 | Online Logistic Regression (`ThesisWeightLearner`) | integrated 3.2 + math model Phase 3 | 미구현 | 미구현 |
| B17 | 상관계수 자동 할인 (60일 \|ρ\|≥0.9 → 1/√k) | math model Phase 2 | 미구현 | `premise_aggregator.py`에 흔적 없음 |
| B18 | Adaptive Decay/Window | math model Phase 2 | 미구현 | indicator는 고정 `epsilon=0.0001, window=60, decay=0.95` |
| B19 | Sustained Extreme alert subtype | math model Phase 2 | 기본 `extreme_volatility`만 존재 | 미구현 |

### 3.3 미구현 항목 — 프론트엔드

| # | 항목 | 설계 출처 | 영향 | 코드 흔적 |
|---|---|---|---|---|
| F1 | 히트맵 뷰 컴포넌트 | design 3.4 + Phase 2 | dashboard API는 `heatmap` 데이터를 응답하지만 FE는 사용 안 함 | dashboard 페이지가 `IndicatorRow` 세로 나열만 사용 |
| F2 | 그래프뷰 컴포넌트 (전체 지표 시계열 라인) | design 3.4 | 지표별 미니차트(`IndividualMiniCharts`)가 부분 대체 | 폐기 가능성 |
| F3 | 5경로 진입점 (인기/템플릿/Chain Sight) | design 2.3 | EntryPointGrid는 "내 생각"/"오늘 이슈" 2개 + Chain Sight "준비 중" | "준비 중" Toast 표시 |
| F4 | [근거] 버튼/팝업 시스템 (롱프레스 + 자연어 설명) | design 2.4 | 빌더 OptionButton에는 long-press가 있으나 dashboard 지표 카드에는 없음 | 부분 |
| F5 | 가설 마감 후 복기 분석 컴포넌트 (Phase 3 FE-PR-10 원안) | Phase2_summary L137 | close 페이지가 outcome 선택만 받고 마감 후 읽기전용 요약만 표시. "유용했던 지표"/"예상과 달랐던 부분" 분석 화면 없음 | `frontend/components/thesis/close/` 디렉토리에 OutcomeSelector + CloseConfirmDialog만 존재 |
| F6 | 투자자 DNA 프로필 화면 (Phase 3 FE-PR-11 원안) | Phase2_summary L138 + integrated 1.4 | `InvestorDNA` 모델은 존재하나 노출 API/UI 없음. AccuracyRing/CategoryChart 등 미존재 | grep `InvestorDNA` 결과: `thesis/views/thesis_views.py`의 `_update_investor_dna()`만 있음 |
| F7 | 마감 가설 아카이브 페이지 | Phase2_summary L137 | 가설 목록은 `status='active'`만 필터링 표시. 마감된 가설을 모아 보는 화면 없음 | `app/thesis/(list)/page.tsx` line 39: `theses.filter((t) => t.status === 'active')` |
| F8 | DNA 슬라이더 + 역제안 UI | integrated 2.3~2.4 | 미구현 | 미구현 |
| F9 | "내러티브 반감기" 카드 | integrated Phase 2 + design 3.8 | 미구현 | 미구현 |
| F10 | "쉐이크 시 새로고침" + 시간 범위 상하 스와이프 | design 3.5 | 모바일 제스처 미구현 | 미구현 |
| F11 | Moon Phase 메타포 (대시보드 OverallMoon) | design 3.2 + FE-PR-5 | redesign에서 **삭제** (D) — common/MoonPhase.tsx는 ThesisListCard에 잔존 | 부분 폐기 |
| F12 | 화살표 시스템 (UI 노출) | design 3.3 + FE-PR-5 | redesign에서 **삭제** (D) — `ArrowIndicator` 컴포넌트는 잔존하나 dashboard에서 미사용. score는 "지지/반박/중립" 라벨로만 표시 | 부분 폐기 |

### 3.4 폐기·대체된 항목 (D)

redesign에서 명시적으로 삭제·대체된 것:

| 폐기 항목 | 대체 |
|---|---|
| `OverallMoon.tsx` (대시보드 달 위상) | 제거 — 가설 목록 카드(`ThesisListCard`)에서만 잔존 |
| `DashboardIndicatorCard.tsx` (화살표 + 트렌드) | `RealValueIndicatorCard.tsx` + `IndicatorRow.tsx` (실제 값 + 변화율) |
| `RecentChange.tsx` (내러티브 텍스트) | `NotableChangesSection.tsx` (구조화된 변화 목록) |
| `scoreToPhaseMeta()` 유틸 | redesign 문서에 "삭제 가능" 명시 — 현재는 `utils.ts` 잔존 여부 미확인 (검증 필요) |
| `DashboardResponseV2` 별도 응답 타입 | 기존 `DashboardResponse`에 optional 필드 추가로 대체 |
| Zustand `dashboardStore.ts` | `useState`로 대체 — Zustand 미도입 확인 |
| Phase 3 원안 FE-PR-7~11 (탭/히트맵/DNA 프로필) | redesign으로 사실상 폐기 |

---

## 4. 하네스 일관성 이슈 (참고)

감사 중 발견된 문서·구현 동기화 갭:

| # | 항목 | 문제 |
|---|---|---|
| H1 | `Phase2_completion_summary.md` Phase 3 계획 (L128~138) | 2일 뒤 redesign으로 폐기되었으나 보고서가 갱신되지 않음 |
| H2 | `FE-PR-6_alerts_close_qa.md`의 "indicatorMutations.ts → mutations.ts 통합 완료" | 코드에는 두 파일 모두 잔존 (`frontend/lib/thesis/indicatorMutations.ts` + `mutations.ts`) — 보고서 기재와 불일치 |
| H3 | redesign 문서의 "PR-10에서 generate_thesis_summaries 구현 예정" | 4월 27일 현재 미진행. PROGRESS.md에 진행 중 표시도 없음 |
| H4 | `feature_flags.py` `KEYWORD_HINTS_ENABLED=False` | Phase B keyword 인프라가 100% 구현되어 있는데 플래그가 OFF — 활성화 결정/시점 불명 |
| H5 | `entry_source` choices에 `popular`/`template`/`chainsight` 등록되어 있으나 진입 경로 없음 | 경로 미구현이지만 enum은 미리 추가됨 — 사용자가 잘못된 entry_source로 가설 생성 시 동작 미정의 |
| H6 | sub_claude_md의 "구현 상태 요약"은 "Thesis Control 프론트엔드 Phase 2 완료, Phase 3 진행 중 (FE-PR-7~11)"으로 표시 | 실제로는 Phase 3 redesign(PR-7~9)이 진행되어 원안과 다름 |

---

## 5. 한 줄 결론

**Phase 1 + Phase A LLM 빌더 + Phase B keyword 인프라 + Phase 3 redesign(PR-7~9 실제 값 대시보드)는 완전 구현, Phase 2 모니터링 강화의 절반(히트맵/그래프뷰/일일 요약/뉴스 스캔/[근거] 시스템) + 통합 로드맵 Phase 3 전반(커뮤니티/합성 에이전트/복기/DNA 프로필/Neo4j) + Phase 4 벡터화는 미진행.** 가장 시급한 한 가지는 PR-10 `generate_thesis_summaries` Celery task — 대시보드 `AISummarySection`이 항상 빈 문자열을 받는 상태이기 때문.
