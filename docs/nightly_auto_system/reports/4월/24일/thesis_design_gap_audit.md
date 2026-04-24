# Thesis Control 설계 갭 감사

> 작성일: 2026-04-24
> 범위: `docs/thesis_control/*` 설계 문서 ↔ `thesis/` 백엔드 + `frontend/components/thesis/` + `frontend/app/thesis/`
> 방식: 읽기 전용 — 코드 수정 없음. Phase 3 두 트랙(Redesign PR-7~10 / 원안 FE-PR-7~11)과 완료 보고서 대조.
> 참고: 2026-04-22 감사(`reports/4월/22일/thesis_design_gap_audit.md`) 대비 **thesis/ · frontend/components/thesis/ · frontend/app/thesis/ 경로에 신규 커밋 없음** (`git log --since="2026-04-22" -- thesis/ frontend/components/thesis/ frontend/app/thesis/` 빈 결과). 본 보고서는 같은 구조에 코드 근거를 재검증하여 갱신.

---

## 요약 (Phase별 구현률)

| Phase / 트랙 | 설계 출처 | 구현률 | 상태 |
|--------------|----------|-------|------|
| **Phase 1 — MVP 관제 엔진 + 이벤트 수집** | `integrated_roadmap.md` Phase 1 | **~95%** | (A) 완전에 가까움 |
| **Phase 3 Redesign PR-7 (백엔드)** | `phase3_frontend_redesign.md` §4 | **100%+** | (A) 완료 + 확장(1825일 readings + FMP fallback) |
| **Phase 3 Redesign PR-8 (실제값 카드 + AI 섹션)** | 같은 문서 §5 | **~80%** | (B/D) AISummary/NotableChanges 완료, `RealValueIndicatorCard`는 `IndicatorRow`로 대체 |
| **Phase 3 Redesign PR-9 (차트 토글 + 기간 선택)** | 같은 문서 §6 | **~50%** | (D) 공용 컴포넌트 3종 존재하나 대시보드 미통합 — `IndicatorRow` 인라인 차트로 대체 |
| **Phase 3 Redesign PR-10 (AI 파이프라인)** | 같은 문서 §7 | **0%** | (C) 미구현 — `generate_thesis_summaries` 태스크 부재, `ai_summary` 항상 `""` |
| **Phase 2/3 원안 FE-PR-7~11 (3탭/히트맵/히스토리/아카이브/DNA)** | `frontend/task_done/Phase2_completion_summary.md` §8 | **~5%** | (C) 거의 전부 미구현 — 백엔드 일부 기반만 준비(heatmap 응답, DNA 모델) |
| **빌더 재설계 Phase A (LLM One-shot)** | `talking_builder/llm_builder_plan.md` + `work_done/phase_a_llm_builder.md` | **100%** | (A) 완료 |
| **빌더 재설계 Phase B (KeywordCache + Collectors)** | `redesign_build_plan/03_phase_b_keywords.md` | **~60%** | (B) 부분 — PR-12 멀티턴 수정 흔적 미확인 |
| **빌더 재설계 Phase C (고급)** | `redesign_build_plan/04_phase_c_advanced.md` | **0%** | (C) 미착수 |
| **커뮤니티 (인기 가설/팔로우/템플릿)** | `thesis_control_design.md` §2.3 경로 3~5 | **~10%** | (C) 모델만 존재 |
| **분기 지표 대시보드 확장** | `talking_builder/quarterly_indicator_dashboard_plan.md` | **~90%** | (A) 거의 완료 |

**총평**: Phase 1 완료 + Phase 3 Redesign 코어(PR-7/8) 완성 + Phase 3 AI 파이프라인(PR-10)과 Phase 3 원안 "깊이/회고/프로필"(FE-PR-7~11)은 본질적으로 **미착수**. 2026-04-22 이후 변화 없음.

---

## 문서별 상태 테이블

### 설계 문서 (`docs/thesis_control/plan/`)

| 문서 | 주요 내용 | 구현 상태 | 코드 근거 |
|------|----------|---------|----------|
| `thesis_control_design.md` | UX 플로우, 5가지 진입 경로, 카드/히트맵/그래프 뷰, API 스펙 | **B** | ViewSet/Conversation API 구현. 경로 1(뉴스) / 2(자유입력)만. 경로 3~5(인기/템플릿/Chain Sight) 미구현 |
| `thesis_control_math_model_final.md` (v2.3.2) | Stage 0~3, Robust Z, Snapshot universe, 알림 throttling | **A** | `thesis/services/{data_validator,indicator_scorer,premise_aggregator,thesis_state_machine,alert_engine,snapshot_builder,arrow_calculator}.py` |
| `thesis_control_implementation_guide.md` | Phase 1~4 로드맵 (히트맵/근거/뉴스 센티먼트 포함) | **B** | Phase 1 완료. Phase 2 히트맵 UI/근거 팝업/뉴스 센티먼트 대부분 미구현. Phase 3 합성 에이전트 미구현 |
| `thesis_control_integrated_roadmap.md` | 관제 엔진 + 특허 학습 레이어(DNA/유효성/합성) | **B** | `thesis/models/learning.py`에 `HypothesisEvent/ValidityRecord/InvestorDNA` 존재 + close flow에서 수집. `ValidityScore`/DNA 슬라이더/역제안/합성 에이전트 미구현 |
| `thesis_control_phase3_frontend_redesign.md` | PR-7~10 (display_unit + 실제값 카드 + 차트 토글 + AI 파이프라인) | **B/D** | PR-7/PR-8 완료. PR-9 컴포넌트만 존재·미통합(IndicatorRow 대체). PR-10 미구현 |
| `thesis_control_user_experience.md` | 사용자 경험 여정 (Phase 2 + Suggestion Mode) | **A** | 목록/빌더/지표/대시보드/마감 루프 완성 |

### 빌더 재설계 (`plan/talking_builder/`)

| 문서 | 구현 상태 | 코드 근거 |
|------|---------|----------|
| `llm_builder_plan.md` | **A** | `work_done/phase_a_llm_builder.md` 완료 보고서 존재. `services/{builder_state,prompt_builder,llm_postprocess,builder_events}.py` + `feature_flags.py` 존재 |
| `thesis_builder_redesign_v2.md` | **B** | 전략 문서 — 후속 `redesign_build_plan/`으로 대체 |
| `redesign_build_plan/01_phase_a_mvp.md` (PR-1~3) | **A** | `services/thesis_builder.py:start_llm_conversation/process_llm_turn`. 프론트 `components/thesis/PresetSelector.tsx` + `IndicatorCard.tsx` |
| `redesign_build_plan/02_phase_a_hardening.md` (PR-4~7) | **A** | `thesis/management/commands/builder_stats.py` + fallback/normalize 보강 존재 |
| `redesign_build_plan/03_phase_b_keywords.md` (PR-8~12) | **B** | `services/keyword_cache.py`, `keyword_hint.py`, `keyword_collectors/{chain,eod,news}.py` 존재. PR-12(멀티턴 수정) 흔적 미확인 |
| `redesign_build_plan/04_phase_c_advanced.md` | **C** | Health Report / keyword 고도화 / 스트리밍 미착수 |
| `quarterly_indicator_dashboard_plan.md` | **A** | `services/quarterly_metric_fetcher.py` + DashboardView metrics batch prefetch + `QuarterlySparkline` + `IndicatorRow` 분기 뷰 반영 |

### Phase 2 FE-PR-1~6 완료 보고서 (`frontend/task_done/`)

| 문서 | 대조 결과 | 코드 근거 |
|------|---------|----------|
| `FE-PR-1_routing_common_components.md` | **A** | 라우팅 7개 + `lib/api/authAxios.ts` + 공통 컴포넌트 6개(`AlertBell/ArrowIndicator/BottomSheet/IndicatorCard/MoonPhase/ThesisBadge`) 전부 존재 |
| `FE-PR-2_thesis_list_page.md` | **A** | `list/{EntryPointGrid,ThesisListCard,TodayChangeCard}.tsx` + `(list)` 라우트 그룹 + `alerts/` 하위 존재 |
| `FE-PR-3_builder_implementation.md` + `FE-PR-3_plan_review_v3.md` | **A** | `builder/` 하위 9개(`BottomSheet/ChatBubble/MultiSelectFooter/NewsSelector/OptionButton/PremiseCard/ProgressBar/SuggestionCard/TextInput.tsx`) + `/thesis/new` page 존재 |
| `FE-PR-4_indicator_setup.md` | **A** | `indicators/{AddIndicatorSheet,IndicatorSetupCard,RecommendCard}.tsx` + `/thesis/[id]/indicators` 존재 |
| `FE-PR-5_dashboard.md` | **D/A** | 원안의 `OverallMoon`/`DashboardIndicatorCard`/`RecentChange`는 Phase 3 Redesign에 의해 삭제됨. 현 대시보드는 `DashboardHeader/DashboardPageHeader/IndicatorRow/AISummarySection/NotableChangesSection`로 재구성 |
| `FE-PR-6_alerts_close_qa.md` | **A** | `alerts/{AlertCard,AlertFilterTabs,EmptyAlerts}.tsx` + `close/{CloseConfirmDialog,OutcomeSelector}.tsx` + `/thesis/[id]/close` 존재 |
| `Phase2_completion_summary.md` | 요약만 | §8 "Phase 3 계획"(FE-PR-7~11)은 본 감사 기준 거의 미구현 |

---

## Phase 3 미구현 항목 상세

Phase 3은 **두 개의 별개 트랙**이 공존한다. 각각 분리하여 기재.

### A. Phase 3 Redesign — 대시보드 리디자인 (PR-7~10)

> 출처: `plan/thesis_control_phase3_frontend_redesign.md`. Phase 2의 달 위상/화살표/내부 점수 중심 대시보드를 "사용자가 아는 실세계 값" 중심으로 교체하는 트랙.

#### PR-7: 백엔드 확장 — **(A) 완전 구현 + 확장**

| 설계 항목 | 구현 | 코드 근거 |
|---------|------|---------|
| `ThesisIndicator.display_unit` CharField(10) 추가 | ✅ | `thesis/migrations/0004_add_display_unit.py`, `0005_populate_display_unit.py` + `thesis/models/indicator.py:73-76` |
| DashboardView에 `raw_value/raw_value_unit/previous_raw_value/change_pct/raw_value_asof` 필드 | ✅ | `thesis/views/monitoring_views.py:94-165` |
| `_infer_unit()` fallback 함수 | ✅ | `monitoring_views.py:346-364` |
| `IndicatorReadingsView` (`GET /{id}/indicators/{ind}/readings/?days=N`) | ✅ + **확장** | `monitoring_views.py:260-290` · `urls.py:30-34` 등록. `days` 상한이 설계 90 → 실제 **1825(5Y)** |
| thesis 응답에 `ai_summary/notable_changes/snapshot_date` | ✅ | `monitoring_views.py:205-219` (값 공급 파이프라인은 별개 = PR-10) |
| 설계에 없는 FMP 히스토리 fallback | ➕ 추가 구현 | `monitoring_views.py:293-343` `_fetch_fmp_history()` |

→ **설계 준수 + 긍정적 확장**. 단, 확장 내용의 설계 문서 미갱신 → 부수 관찰 §1~2.

#### PR-8: 실제 값 카드 + AI 분석 섹션 — **(B/D) 대체 구현**

| 설계 항목 | 구현 | 비고 |
|---------|------|------|
| `RealValueIndicatorCard.tsx` 대시보드 사용 | ❌ 대체됨 | 파일 존재(`dashboard/RealValueIndicatorCard.tsx`)하나 `app/thesis/[thesisId]/page.tsx`에서 import 안 됨. 2026-04-24 재검증: `frontend/__tests__/thesis/RealValueIndicatorCard.test.tsx` 테스트만 참조 → **사실상 폐기(D)** |
| `AISummarySection.tsx` | ✅ | `page.tsx:75-78` 정상 사용 (snapshotDate prop 포함) |
| `NotableChangesSection.tsx` | ✅ | `page.tsx:81-84` 정상 사용 |
| `formatRawValue`/`formatChangePct`/`supportLabel` 유틸 | ✅ | `lib/thesis/utils.ts` |
| Mock 데이터 확장 | ✅ | `lib/thesis/mock.ts` `MOCK_DASHBOARD`에 필드 추가 |

→ 설계 **목적(실값 표시)은 달성**하나 카드 컴포넌트는 **토글형 행(`IndicatorRow.tsx`)으로 교체**. 이는 메모리 `feedback_dashboard_layout.md`의 "1xN 세로 나열, 지표별 토글 차트, 전분기대비 라벨" 지침을 반영한 결과. **공식 폐기 결정 문서는 부재**.

#### PR-9: 차트 토글 + 기간 선택 + 개별 미니차트 — **(D) 대체 구현**

| 설계 항목 | 구현 | 비고 |
|---------|------|------|
| `ChartToggleButton.tsx` | 파일만 존재 | `app/` 어디에서도 import 없음 (재검증 완료) |
| `PeriodSelector.tsx` | 파일만 존재 | 동일 |
| `IndividualMiniCharts.tsx` | 파일만 존재 | 동일 |
| 대시보드 `page.tsx`에 차트 섹션 삽입 | ❌ | 없음. 대신 `IndicatorRow` 내부에 **지표별 인라인 AreaChart + 기간 [1M/1Y/3Y/5Y]** 토글 구현 (`IndicatorRow.tsx:174-226`) |
| `useIndicatorReadings`/`useAllIndicatorReadings` | 부분 | `useIndicatorReadings`만 `IndicatorRow.tsx:59`에서 사용 |
| `MOCK_READINGS` 생성기 | 존재 | `lib/thesis/mock.ts` |
| `OverallMoon.tsx` 삭제 | ✅ | `components/thesis/dashboard/`에서 제거 확인 |
| `DashboardIndicatorCard.tsx` 삭제 | ✅ | 동일 |
| `RecentChange.tsx` 삭제 | ✅ | 동일 |

→ 차트 접근 기능 목표는 달성하나 **설계 컴포넌트 3종은 dead code 상태**. 정리 대상.

#### PR-10: AI 모니터링 파이프라인 — **(C) 전면 미구현**

| 설계 항목 | 현재 상태 |
|----------|---------|
| `generate_thesis_summaries` Celery 태스크 (매일 07:30) | **없음**. `thesis/tasks/eod_pipeline.py`는 3개 태스크(`update_indicator_readings`/`calculate_scores`/`create_snapshots_and_alerts`)만 존재. 저장소 전역 grep 결과 `generate_thesis_summaries`는 설계 문서·감사 보고서에서만 언급, 구현 0건 |
| `ThesisSnapshot.ai_summary` 채우기 | **비어 있음**. 모델 필드는 존재, 작성 코드 없음. `DashboardView`가 읽지만 항상 `""` |
| `notable_changes`를 alert_engine 이벤트 기반으로 생성 | **대체 구현 존재** — `snapshot_builder.py:105-120`에서 `|curr−prev| ≥ 0.3` 스코어 델타로만 생성. 설계의 `change_type/severity/description/raw_value_before·after` 필드 누락 |
| Weekly Health Check (향후 확장) | **없음** |
| LLM 호출(Gemini 2.5 Flash) | 해당 태스크 부재로 없음 |

→ 프론트엔드 `AISummarySection`은 항상 빈 문자열을 받아 설계대로 `if (!summary) return null`로 미렌더링됨. **대시보드 핵심 UX 공백**.

---

### B. Phase 3 원안 — "깊이 + 회고 + 프로필" (FE-PR-7~11)

> 출처: `frontend/task_done/Phase2_completion_summary.md` §8. Phase 3 Redesign과 **전혀 다른 트랙**으로, 대시보드 리디자인이 채택되며 원안은 사실상 폐기되었을 가능성이 높다. 그러나 **공식 폐기 결정 문서가 없으므로 공식적으로는 미구현(C)**.

| PR | 설계 핵심 | 구현 상태 | 코드/파일 근거 |
|----|---------|---------|-------------|
| **FE-PR-7** | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD UI | **(C) 미구현** | `app/thesis/[thesisId]/` 하위에 `close/`, `indicators/`, `page.tsx`만 존재 — 탭 구조/상세 라우트 없음. 전제 CRUD는 백엔드(`ThesisPremiseViewSet`)만 있고 전용 UI 없음 |
| **FE-PR-8** | Finviz 스타일 히트맵 + 지표 상세 편집(weight/direction) | **(B) 부분** | 백엔드 `DashboardView`에 `heatmap.{rows,cols,cells}` 응답 제공(`monitoring_views.py:221-225`), **프론트 렌더링 없음**. 지표 편집은 toggle/delete만 존재 |
| **FE-PR-9** | 히스토리 탭 — recharts 스냅샷 타임라인 + 라인 차트 | **(C) 미구현** | `/thesis/[id]/history` 라우트 없음, `ThesisSnapshot` 히스토리 조회 API 엔드포인트 없음(`thesis/urls.py`에 snapshots 경로 부재) |
| **FE-PR-10** | 마감 아카이브 + ValidityMatrix 요약 | **(C) 미구현** | `/thesis/archive` 또는 마감 가설 전용 목록/상세 페이지 없음. `ValidityRecord`는 close 시 DB 저장(`thesis_views.py:91 ValidityRecord.objects.create(...)`)되나 조회 API/화면 없음 |
| **FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | **(C) 미구현** | `InvestorDNA` 모델·자동 갱신 함수 존재(`thesis_views.py:138-139` `_update_investor_dna`), 그러나 조회 API/프로필 라우트/컴포넌트 없음. `frontend/app/profile/` 디렉토리 부재 |

### C. 그 외 원안 설계 미구현 영역

| 항목 | 설계 출처 | 상태 | 비고 |
|------|----------|------|------|
| 경로 3: 인기 가설 (`POST /popular/{id}/follow/`) | design §2.3 | **(C)** | `thesis/models/community.py`에 `PopularThesisCache`/`ThesisFollow` 모델 존재, API/UI 없음 |
| 경로 4: 템플릿 가설 (이벤트형/추세형/비교형/괴리형) | design §2.3 | **(C)** | 없음 |
| 경로 5: Chain Sight 연동 양방향 진입 | design §2.3 | **(C)** | 양방향 링크 흔적 없음 |
| 히트맵 뷰 API + UI | design §3.4 | **(B)** | 백엔드 데이터만 제공 (`monitoring_views.py` heatmap 필드) |
| 그래프 뷰 (시계열 라인 전용 뷰) | design §3.4 | **(C)** | 지표별 인라인 차트(`IndicatorRow`)로 일부 대체 |
| [근거] 설명 팝업 (LLM + Redis 캐싱) | design §2.4 | **(C)** | `get_indicator_description`으로 정적 설명만 제공 |
| ValidityScore 집계 + 지표 추천 반영 | roadmap Phase 2 §2.1-2.2 | **(C)** | `ValidityRecord`만 축적. 집계 모델/태스크/추천 반영 없음 |
| DNA 적합도 슬라이더 + Contrarian Nudge | roadmap Phase 2 §2.3-2.4 | **(C)** | `InvestorDNA.personalization_weight` 필드만 존재 |
| 합성 에이전트 부트스트래핑 | roadmap Phase 3 §3.1 | **(C)** | `SyntheticBootstrapper`/`SYNTHETIC_PERSONAS` 없음 |
| Online Logistic Regression (가중치 자동학습) | math model Phase 3 | **(C)** | `ThesisWeightLearner` 없음 |
| Neo4j 가설 관계 그래프 (`SIMILAR_TO`/`OPPOSITE_OF`) | design §4.4 | **(C)** | 없음 |
| DNA 벡터화 / 유효성 벡터화 / 사용자 유사도 | roadmap Phase 4 | **(C)** | 없음 |

---

## 부수 관찰 (설계 ↔ 코드 불일치)

1. **`IndicatorReadingsView` days 상한**: 설계 `min(int(...), 90)` → 실제 `min(..., 1825)` (`monitoring_views.py:269`). 5Y 차트 지원 확장이지만 설계 문서 미갱신.
2. **FMP 히스토리 fallback**: 설계에 없는 `_fetch_fmp_history()`가 `IndicatorReadingsView`에 추가됨(`monitoring_views.py:293-343`). DB readings 부족 시 실시간 FMP 조회. 문서화 필요.
3. **`notable_changes` 생성 기준**: 설계(PR-10)는 alert_engine의 `direction_flip/sharp_move/extreme_volatility` 이벤트 기반, 실제 구현은 `|score 변화| ≥ 0.3` 스칼라 기반(`snapshot_builder.py:105-120`). `change_type`/`severity`/`description`/`raw_value_before·after` 필드 누락 → 프론트 `NotableChange` 타입과 부분 불일치.
4. **`ThesisIndicator.recommendation_reason`**: 설계에 없는 TextField가 존재(`thesis/migrations/0009_add_recommendation_reason.py`, `thesis/models/indicator.py:58-61`) — 메모리 `feedback_suggestion_ux_design.md`의 가설 관계성 강화 반영. `IndicatorRow`가 이를 표시.
5. **`RealValueIndicatorCard.tsx`**: 설계 대상 컴포넌트지만 `page.tsx`에서 사용 안 됨 + 테스트만 남음. 명시적 폐기 결정 문서 부재.
6. **공용 차트 컴포넌트 3개**(`ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`): 설계상 dashboard 하단 공용 차트용이나 `IndicatorRow` 인라인 차트로 대체되어 **미사용 dead code** 상태.
7. **`AISummarySection.snapshotDate` prop**: 설계의 prop은 `summary` 단일이나 실제 컴포넌트는 `{summary, snapshotDate}` 2-prop 형태(`page.tsx:75-78` 호출 형상). 설계 대비 확장이지만 설계 문서 미갱신.

---

## 2026-04-22 감사 대비 변경점

- **코드 변화 없음**: `git log --since="2026-04-22" -- thesis/ frontend/components/thesis/ frontend/app/thesis/` 결과 0건.
- 전역 커밋 중 2026-04-22 이후 유일한 변경은 `b394ee9 docs: 코드베이스 감사 보고서 생성`(문서 전용).
- 따라서 본 감사의 결론과 권고는 22일 감사와 동일하며, **우선순위/미구현 항목 전부가 그대로 이월**됨.

---

## 결론

- **Phase 1 MVP 루프 완성** — 가설 생성 → 지표 설정 → EOD 파이프라인 → 대시보드 → 알림 → 마감 → 학습 데이터(이벤트/유효성/DNA) 축적까지 정상 동작.
- **Phase 3 Redesign은 PR-7/8 완료 + PR-9 대체 + PR-10 전면 미구현**. `AISummarySection`이 항상 비어 렌더링되지 않는 상태가 **가장 큰 가시적 공백**.
- **Phase 2/3 원안 FE-PR-7~11(3탭/히트맵 UI/히스토리/아카이브/DNA)은 본질적으로 미착수**. 백엔드 기반(heatmap 응답, `ValidityRecord`, `InvestorDNA`)은 일부 준비되어 있어 UI만 붙이면 즉시 가치를 낼 수 있는 항목 다수.
- **빌더 재설계는 Phase A 완료, Phase B 부분, Phase C 미착수**.
- **커뮤니티/템플릿/Chain Sight 연동/근거 팝업/ValidityScore 활용/합성 에이전트/벡터화**는 설계 문서에만 존재.

### 착수 우선순위 후보 (감사 관점 권고)

1. **PR-10 AI 파이프라인** — `AISummarySection`의 공백이 설계 의도를 가장 크게 훼손. `create_snapshots_and_alerts`와 같은 EOD 타이밍에 LLM 호출을 끼워넣는 구조로 점증 구현 가능.
2. **아카이브 + DNA 프로필 UI** — DB에 이미 데이터 축적 중(`ValidityRecord`, `InvestorDNA`). 조회 API + 페이지만 추가하면 즉시 가치 발생 (FE-PR-10/FE-PR-11).
3. **공식 폐기 결정 문서화** — `RealValueIndicatorCard`, 공용 차트 3종, 원안 FE-PR-7~11 트랙. `DECISIONS.md`에 "Phase 3 원안 폐기 / 리디자인 채택" 명시하여 혼란 방지. 본 감사 기준 이 결정이 여전히 누락.
4. **히트맵 UI** — 백엔드 응답이 이미 존재하므로 프론트 구현만 추가하면 FE-PR-8의 절반 달성.
5. **설계 문서 갱신** — 부수 관찰 §1~3, 5~7(readings 1825일 상한, FMP fallback, notable_changes 대체 구현, dead code 공식 폐기, AISummarySection prop 확장)을 Phase 3 Redesign 문서에 반영.
