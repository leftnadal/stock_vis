# Thesis Control 설계 갭 감사

> 작성일: 2026-04-22
> 범위: `docs/thesis_control/*` 설계 문서 ↔ `thesis/` 백엔드 + `frontend/components/thesis/` 프론트엔드
> 방식: 읽기 전용 — 코드 수정 없음. Phase 3/빌더 재설계/완료 보고서 대조.

---

## 요약 (Phase별 구현률)

| Phase / 트랙 | 설계 출처 | 구현률 | 상태 |
|--------------|----------|-------|------|
| **Phase 1 — MVP 관제 엔진 + 이벤트 수집** | `integrated_roadmap.md` Phase 1 | **~95%** | (A) 완전에 가까움 |
| **Phase 3 Redesign (PR-7/8/9) — 대시보드 리디자인** | `thesis_control_phase3_frontend_redesign.md` | **~70%** | (B) 부분 + (D) IndicatorRow로 대체 |
| **Phase 3 Redesign PR-10 — AI 파이프라인** | 같은 문서 §7 | **0%** | (C) 미구현 |
| **Phase 2/3 원안 FE-PR-7~11 (3탭/히트맵/히스토리/아카이브/DNA)** | `frontend/task_done/Phase2_completion_summary.md` §8 | **~5%** | (C) 거의 전부 미구현 |
| **빌더 재설계 Phase A (LLM One-shot)** | `talking_builder/llm_builder_plan.md`, `work_done/phase_a_llm_builder.md` | **100%** | (A) 완료 |
| **빌더 재설계 Phase B (KeywordCache + Collectors)** | `redesign_build_plan/03_phase_b_keywords.md` | **~60%** | (B) 부분 |
| **빌더 재설계 Phase C (고급)** | `redesign_build_plan/04_phase_c_advanced.md` | **0%** | (C) 미착수 |
| **커뮤니티 (인기 가설/팔로우/템플릿)** | `thesis_control_design.md` §2.3 경로3~5 | **~10%** | (C) 모델만 존재 |
| **분기 지표 대시보드 확장** | `talking_builder/quarterly_indicator_dashboard_plan.md` | **~90%** | (A) 거의 완료 |

전체 평균: **Phase 1 완료 + Phase 3 재설계 코어 완성 + Phase 3 원안 깊이/회고/프로필 기능은 본질적으로 미착수**.

---

## 문서별 상태 테이블

### 설계 문서 (plan/)

| 문서 | 주요 내용 | 구현 상태 | 코드 근거 |
|------|----------|---------|----------|
| `thesis_control_design.md` | UX 플로우, 5가지 진입 경로, 카드/히트맵/그래프 뷰, API 스펙 | **B** | Viewset/conversation API 구현됨. 히트맵/그래프 뷰 미구현. 5 진입 경로 중 경로 1/2만 구현 (news/free_input) |
| `thesis_control_math_model_final.md` (v2.3.2) | Stage 0~3, Robust Z, Snapshot universe, 알림 throttling | **A** | `thesis/services/` 전체 (data_validator, indicator_scorer, premise_aggregator, thesis_state_machine, alert_engine, snapshot_builder, arrow_calculator) |
| `thesis_control_implementation_guide.md` | Phase 1~4 로드맵 | **B** | Phase 1 완료, Phase 2 히트맵/근거/뉴스 센티먼트 대부분 미구현, Phase 3 합성 에이전트 미구현 |
| `thesis_control_integrated_roadmap.md` | 관제 엔진 + 특허 학습 레이어 통합 | **B** | HypothesisEvent/ValidityRecord/InvestorDNA 모델·수집 완료. ValidityScore/DNA 슬라이더/역제안/합성 에이전트 미구현 |
| `thesis_control_phase3_frontend_redesign.md` | PR-7~10 (display_unit + 실제값 카드 + 차트 토글 + AI 파이프라인) | **B/D** | PR-7/PR-8 완료. PR-9는 컴포넌트만 존재·대시보드 미통합(IndicatorRow로 대체). PR-10 미구현 |
| `thesis_control_user_experience.md` | 사용자 경험 여정 (Phase 2 + Suggestion Mode) | **A** | 목록/빌더/지표/대시보드/마감 루프 완성 |

### 빌더 재설계 (plan/talking_builder/)

| 문서 | 구현 상태 | 코드 근거 |
|------|---------|----------|
| `llm_builder_plan.md` | **A** | Phase A 완료 보고서 존재 (work_done/phase_a_llm_builder.md). builder_state.py, prompt_builder.py, llm_postprocess.py, builder_events.py, feature_flags.py 존재 |
| `thesis_builder_redesign_v2.md` | **B** | 전략 문서. v4로 대체됨 |
| `redesign_build_plan/01_phase_a_mvp.md` (PR-1~3) | **A** | 완료 — `services/thesis_builder.py`에 `start_llm_conversation`, `process_llm_turn` 구현. PresetSelector/IndicatorCard 프론트 존재 |
| `redesign_build_plan/02_phase_a_hardening.md` (PR-4~7) | **A** | `management/builder_stats` command 존재, fallback/normalize 보강 코드 존재 |
| `redesign_build_plan/03_phase_b_keywords.md` (PR-8~12) | **B** | `services/keyword_cache.py`, `keyword_hint.py`, `keyword_collectors/{chain,eod,news}.py` 존재. Admin/check_keywords command 존재 여부 추가 확인 필요. 멀티턴 수정(PR-12) 미확인 |
| `redesign_build_plan/04_phase_c_advanced.md` | **C** | 미착수 (Health Report, keyword 고도화, 스트리밍) |
| `quarterly_indicator_dashboard_plan.md` | **A** | `quarterly_metric_fetcher.py` 구현, DashboardView에 metrics batch prefetch + QuarterlySparkline + IndicatorRow 분기 뷰 반영 |

### Phase 1 FE-PR-1~6 완료 보고서 (frontend/task_done/)

| 문서 | 대조 결과 |
|------|---------|
| `FE-PR-1_routing_common_components.md` | **A** — 라우팅 7개 + authAxios + 공통 컴포넌트 6개 (AlertBell, ArrowIndicator, BottomSheet, IndicatorCard, MoonPhase, ThesisBadge) 모두 존재 |
| `FE-PR-2_thesis_list_page.md` | **A** — list/{EntryPointGrid, ThesisListCard, TodayChangeCard} 존재, (list) 라우트 그룹 + alerts 하위 존재 |
| `FE-PR-3_builder_implementation.md` + `FE-PR-3_plan_review_v3.md` | **A** — builder/ 하위 9개 컴포넌트 (BottomSheet, ChatBubble, MultiSelectFooter, NewsSelector, OptionButton, PremiseCard, ProgressBar, SuggestionCard, TextInput). `/thesis/new` 존재 |
| `FE-PR-4_indicator_setup.md` | **A** — indicators/{AddIndicatorSheet, IndicatorSetupCard, RecommendCard} + `/thesis/[id]/indicators` 존재 |
| `FE-PR-5_dashboard.md` | **D/A** — 원안 OverallMoon/DashboardIndicatorCard/RecentChange는 Phase 3 Redesign으로 삭제됨. 현재는 DashboardHeader/DashboardPageHeader/IndicatorRow/AISummarySection/NotableChangesSection으로 대체 |
| `FE-PR-6_alerts_close_qa.md` | **A** — alerts/{AlertCard, AlertFilterTabs, EmptyAlerts} + close/{CloseConfirmDialog, OutcomeSelector} + `/thesis/[id]/close` 존재 |
| `Phase2_completion_summary.md` | 요약만 — Phase 3 예정표(FE-PR-7~11)는 본 감사 기준 거의 미구현 |

---

## Phase 3 미구현 항목 상세

여기서 "Phase 3"은 **두 개의 다른 트랙**이 공존하므로 각각 분리한다.

### A. Phase 3 Redesign (대시보드 리디자인 — PR-7~10)

> 문서: `plan/thesis_control_phase3_frontend_redesign.md`. Phase 2의 달 위상/화살표/내부 점수 중심 대시보드를 "사용자가 아는 실세계 숫자" 중심으로 교체하는 것이 목표.

#### PR-7: 백엔드 확장 — **완전 구현 (A)**

- `ThesisIndicator.display_unit` CharField(10) 추가 → `thesis/models/indicator.py:73-76` 확인
- `DashboardView`에 `raw_value/raw_value_unit/previous_raw_value/change_pct/raw_value_asof` 필드 추가 → `thesis/views/monitoring_views.py:94-174` 확인
- `_infer_unit()` fallback 함수 → `thesis/views/monitoring_views.py:346-364` 확인
- `IndicatorReadingsView` (`GET /{id}/indicators/{ind}/readings/?days=14`) 추가 → `thesis/views/monitoring_views.py:260-291`, `thesis/urls.py:30-34` 확인
- `thesis` 응답에 `ai_summary/notable_changes/snapshot_date` 필드 추가 → `monitoring_views.py:205-219` 확인
- 설계에서 `days` 상한 90일로 되어 있으나 실제 구현은 **1825일(5Y)로 확장**됨 + FMP 히스토리 fallback 추가 (설계 문서와 **확장 불일치**, 긍정적 방향)

#### PR-8: 실제 값 카드 + AI 분석 — **대체 구현 (D)**

설계상 `RealValueIndicatorCard.tsx`를 대시보드에서 사용해야 하지만 **실제 대시보드 페이지는 `IndicatorRow.tsx`(토글형 상세)를 사용**한다.
- `components/thesis/dashboard/RealValueIndicatorCard.tsx` — 파일 존재하나 프로덕션 페이지에서 import 안 됨. 테스트 파일에서만 참조 (`__tests__/thesis/RealValueIndicatorCard.test.tsx`). → 사실상 **폐기(D)**
- `AISummarySection.tsx`, `NotableChangesSection.tsx` — 대시보드에서 정상 사용 중 (`app/thesis/[thesisId]/page.tsx:74-84`)
- `formatRawValue/formatChangePct/supportLabel` 유틸 — 구현 확인
- 결과: **설계의 목적(실값 표시)은 달성, 카드 컴포넌트는 교체**. 이는 `feedback_dashboard_layout.md` 메모리("1xN 세로 나열, 지표별 토글 차트") 반영.

#### PR-9: 미니차트 + 기간 선택 — **부분 구현 (B/D)**

- `ChartToggleButton.tsx`, `PeriodSelector.tsx`, `IndividualMiniCharts.tsx` **파일 존재** 그러나 **대시보드 페이지에서 import 안 됨** → 사실상 사용되지 않는 dead code
- 대신 **지표별 인라인 토글 차트**가 `IndicatorRow.tsx` 내부에 직접 구현됨 (AreaChart + 기간 선택 [1M/1Y/3Y/5Y])
- `useIndicatorReadings` hook은 `IndicatorRow.tsx:59`에서 사용 중
- 결과: 설계 의도(차트 접근) 달성하나 **공용 컴포넌트 3개는 미사용 자산**. 정리 대상.

#### PR-10: AI 모니터링 파이프라인 — **전면 미구현 (C)**

| 설계 항목 | 현재 상태 |
|----------|---------|
| `generate_thesis_summaries` Celery task (매일 07:30) | **없음**. `thesis/tasks/eod_pipeline.py`는 3개 태스크 (update_indicator_readings / calculate_scores / create_snapshots_and_alerts)만 존재 |
| `ThesisSnapshot.ai_summary` 채우기 | **비어있음**. 모델 필드는 존재, 작성 코드 없음. DashboardView는 `latest_snapshot.ai_summary` 읽지만 항상 "" |
| `notable_changes`를 alert_engine 이벤트에서 생성 | **대체 구현 존재하나 alert 기반 아님** — `snapshot_builder.py:105-120`에서 |curr−prev| ≥ 0.3 스코어 변화를 감지하여 생성 (단순 스코어 델타 기반, severity/description 필드 없음) |
| Weekly Health Check (향후 확장) | **없음** |

→ 프론트엔드 `AISummarySection`은 항상 "" 를 받으므로 설계대로 `if (!summary) return null`로 미렌더링된다.

---

### B. Phase 3 원안 — "깊이 + 회고 + 프로필" (FE-PR-7~11)

> 출처: `frontend/task_done/Phase2_completion_summary.md` §8 "Phase 3 계획". Phase 3 Redesign과 **전혀 다른 트랙**으로, 현시점 대시보드 리디자인이 채택되면서 원안은 사실상 폐기되었을 가능성이 높다. 그러나 **폐기 결정 문서가 없으므로 공식적으로는 미구현(C)**.

| PR | 설계 핵심 | 구현 상태 | 근거 |
|----|---------|---------|------|
| **FE-PR-7** | 대시보드 3탭 구조 (관제/상세/히스토리) + 전제 CRUD UI | **C 미구현** | 대시보드는 단일 뷰. 전제 CRUD는 백엔드만 있고 전용 UI 없음 |
| **FE-PR-8** | Finviz 스타일 히트맵 + 지표 상세 편집(weight/direction) | **B 부분** | 백엔드 `DashboardView.heatmap`(rows/cols/cells) 응답 필드 존재 (`monitoring_views.py:221-225`), 프론트 렌더링 없음. 지표 편집은 toggle/delete만 있음 |
| **FE-PR-9** | 히스토리 탭 — recharts 스냅샷 타임라인 + 라인 차트 | **C 미구현** | `/thesis/[id]/history` 라우트 없음, `ThesisSnapshot` 히스토리 API 엔드포인트 없음 (`thesis/urls.py`에 snapshots 경로 없음) |
| **FE-PR-10** | 마감 아카이브 + ValidityMatrix 요약 | **C 미구현** | `/thesis/archive` 또는 마감 가설 목록 페이지 없음. `ValidityRecord`는 close 시 DB 저장되나 조회 API/화면 없음 |
| **FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | **C 미구현** | `InvestorDNA` 모델·자동 갱신 signal 존재, 그러나 조회 API/프로필 라우트/컴포넌트 없음 |

### C. 그 외 원안 설계 미구현 영역 (설계 문서 §2.3, §3.4 등)

| 항목 | 설계 출처 | 상태 |
|------|----------|------|
| 경로 3: 인기 가설 (POST /popular/{id}/follow/) | design §2.3 | **C** — `PopularThesisCache`/`ThesisFollow` 모델 존재, API/UI 없음 |
| 경로 4: 템플릿 가설 (이벤트형/추세형/비교형/괴리형) | design §2.3 | **C** — 없음 |
| 경로 5: Chain Sight 연동 양방향 진입 | design §2.3 | **C** — 양방향 링크 미확인 |
| 히트맵 뷰 API + UI | design §3.4 | **B** — 백엔드 데이터만 제공 |
| 그래프 뷰(시계열 라인) | design §3.4 | **C** — 지표별 인라인 차트로 일부 대체 |
| [근거] 설명 팝업 (LLM + Redis 캐싱) | design §2.4 | **C** — `get_indicator_description`으로 정적 설명만 제공 |
| ValidityScore 집계 + 지표 추천 반영 | roadmap Phase 2 §2.1-2.2 | **C** — ValidityRecord만 쌓임 |
| DNA 적합도 슬라이더 + Contrarian Nudge | roadmap Phase 2 §2.3-2.4 | **C** |
| 합성 에이전트 부트스트래핑 | roadmap Phase 3 §3.1 | **C** |
| Online Logistic Regression (가중치 자동학습) | math model Phase 3 | **C** |
| Neo4j 가설 관계 그래프 (SIMILAR_TO / OPPOSITE_OF) | design §4.4 | **C** |
| DNA 벡터화 / 유효성 벡터화 / 사용자 유사도 | roadmap Phase 4 | **C** |

---

## 부수 관찰 (설계↔코드 불일치)

1. **IndicatorReadingsView days 상한**: 설계는 `min(int(...), 90)`이나 실제 코드는 `min(..., 1825)` (`monitoring_views.py:269`). 5Y 차트를 위한 확장으로 해석되나 문서 미갱신.
2. **FMP 히스토리 fallback**: 설계에 없는 `_fetch_fmp_history()` 함수가 `IndicatorReadingsView`에 추가됨 (`monitoring_views.py:293-343`). DB readings 부족 시 실시간 FMP 조회. 문서화 필요.
3. **notable_changes 기준**: 설계(PR-10)는 alert_engine의 `direction_flip/sharp_move/extreme_volatility` 이벤트 기반, 실제 구현은 `|score 변화| ≥ 0.3` 스칼라 기반. severity/description/raw_value_before·after 누락.
4. **ThesisIndicator 추가 필드**: 설계에 없는 `recommendation_reason` TextField가 존재 (`indicator.py:58-61`) — `feedback_suggestion_ux_design.md` 메모리에 따른 가설 관계성 강화.
5. **`RealValueIndicatorCard.tsx`**: 설계 대상 컴포넌트지만 `page.tsx`에서 사용 안 됨 + 테스트만 남음. 명시적 폐기 결정 문서 필요.
6. **공용 차트 컴포넌트 3개** (`ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`): 설계상 dashboard 하단 공용 차트용이나 `IndicatorRow` 인라인 차트로 대체되어 **미사용 dead code** 상태.

---

## 결론

- **Phase 1 MVP 루프는 완성** — 가설 생성 → 지표 설정 → EOD 파이프라인 → 대시보드 → 알림 → 마감 → 학습 데이터(이벤트/유효성/DNA) 축적까지 동작.
- **Phase 3 Redesign(대시보드 리디자인)은 PR-7/8 완료 + PR-9 대체 구현 + PR-10 전면 미구현**. AI summary가 핵심 UX인데 파이프라인 없음이 가장 큰 공백.
- **Phase 2/3 원안 깊이 기능군(FE-PR-7~11)은 본질적으로 미착수** — 3탭 구조, 히트맵 UI, 히스토리, 아카이브, DNA 프로필 모두 없음. 백엔드 모델/데이터는 일부 준비되어 있어 UI만 붙이면 되는 항목 존재 (`heatmap` 응답, `ValidityRecord` 조회).
- **빌더 재설계는 Phase A까지 완료, B 부분**. Phase C 미착수.
- **커뮤니티/템플릿/Chain Sight 연동/근거 팝업/ValidityScore 활용/합성 에이전트/벡터화**는 설계 문서에만 존재하고 구현 안 됨.

다음 구현 착수 시 우선순위 후보 (감사 관점, 권장 순서):
1. PR-10 AI 파이프라인 (설계에서 가장 가시적 공백 — AISummarySection이 항상 빈 상태)
2. 아카이브 + DNA 프로필 (이미 DB에 데이터가 쌓이고 있음 — UI만 붙이면 가치 발생)
3. 공식 폐기 결정 문서화 (`RealValueIndicatorCard`, 공용 차트 3종, 원안 FE-PR-7~11) — 혼란 방지
