# Thesis Control 설계 갭 감사

> 감사일: 2026-05-15
> 대상: `/Users/byeongjinjeong/Desktop/stock_vis` (실코드) vs `docs/thesis_control/` (설계 문서)
> 방식: 코드 수정 없이 읽기 전용 cross-reference

---

## 요약 (Phase별 구현률)

| Phase | 영역 | 설계 문서 | 구현률 | 비고 |
|-------|------|-----------|--------|------|
| Phase 1 | MVP (가설 CRUD + 대화형 빌더 + 지표 매칭 + 화살표 엔진 + 일별 Celery) | `thesis_control_design.md §7`, `phase1_frontend_FE_PR_1~5` | **완전 구현 (~95%)** | 모든 핵심 모델/뷰/태스크 존재, 마이그레이션 0001~0009 |
| Phase 1 보강 (이벤트/유효성/DNA) | 통합 로드맵 §1.2~1.4 | `integrated_roadmap.md` | **부분 구현 (~70%)** | 모델 3개 모두 존재(`learning.py`), 마감 시 자동 갱신 로직과 UI 노출 없음 |
| Phase 2 (모니터링 강화) | 히트맵·그래프뷰, 알림, 일일 요약, 뉴스 진입 | `thesis_control_design.md §7 Phase 2` + FE-PR-1~6 | **부분 구현 (~75%)** | 알림/일일 요약/뉴스 이슈는 구현. 히트맵/그래프뷰는 백엔드만, FE 없음 |
| Phase 2 (LLM 빌더) | one-shot proposal | `phase_a_llm_builder.md`, `talking_builder/` | **완전 구현 (~95%)** | A-MVP, A-Hardening, B(Keyword cache) 모두 완료 |
| Phase 3 — 대시보드 리디자인 (PR-7~10) | 실제 값 카드 + AI 분석 + 미니차트 | `thesis_control_phase3_frontend_redesign.md` | **완전 구현 (~90%)** | PR-7~9 모두 완료, PR-10(AI 파이프라인) 부분만 |
| Phase 3 — Phase2 완료 보고서의 FE-PR-7~11 | 3탭 구조 + 히트맵 + 히스토리 + 마감 아카이브 + DNA 프로필 | `Phase2_completion_summary.md §8` | **미구현 (0%)** | 별개의 "Phase 3" 계획이며 거의 폐기/대체된 것으로 추정 |
| Phase 3 (설계서 §7) — 커뮤니티/Neo4j/복기 | 인기 가설, 따라하기, 템플릿, Chain Sight 연동, Neo4j | `thesis_control_design.md §7 Phase 3` | **미구현 (~10%)** | DB 모델만 일부 존재(`PopularThesisCache`, `ThesisFollow`). API/UI/Neo4j 미구현 |
| Phase 4 (지능화) | 합성 에이전트, 벡터 스코어링, 유사도 추천 | `integrated_roadmap.md §3~4` | **미구현 (0%)** | 예정대로 미착수 |

**핵심 관찰:**
"Phase 3"가 문서 간 두 가지 정의로 나뉘어 있음.
1. **`thesis_control_phase3_frontend_redesign.md`의 Phase 3** = 대시보드 시각화 교체(달 위상 → 실제 값) → **사실상 완료**
2. **`Phase2_completion_summary.md §8`의 Phase 3 계획표(FE-PR-7~11)** + **`thesis_control_design.md §7 Phase 3`의 커뮤니티 단계** → **대부분 미구현**

코드 베이스의 실제 흐름은 (1)로 진행되었고, (2)의 깊이/회고/프로필 계열 기능은 PR을 만들지 않고 폐기 또는 보류된 것으로 보임. 사용자가 질문한 "Phase 3 (깊이 + 회고 + 프로필)"는 (2)에 해당하므로 갭이 크다.

---

## 문서별 상태 테이블

### A. 설계서 (plan/)

| 문서 | 분류 | 비고 |
|------|------|------|
| `plan/thesis_control_design.md` | **(B) 부분 구현** | §2 5가지 진입 경로 중 1개(자유 입력)만 살아남음 — EntryPointGrid가 단일 버튼으로 축소(D). §3 세 가지 뷰(카드/히트맵/그래프) 중 카드뷰만 구현, 히트맵 백엔드만, 그래프뷰 미구현 |
| `plan/thesis_control_implementation_guide.md` | (확인 필요) | 본 감사에서는 미열람 |
| `plan/thesis_control_integrated_roadmap.md` | **(B) 부분 구현** | Phase 1 모델 3개(HypothesisEvent, ValidityRecord, InvestorDNA)는 존재. Phase 2 ValidityScore 모델은 미생성. Phase 3/4 미착수 |
| `plan/thesis_control_math_model_final.md` | **(A) 완전 구현** | v2.3.2 Stage 0~3 모두 구현. `ThesisIndicator`에 epsilon/window/decay/min_valid/max_valid/max_change_pct/allow_extreme_jump 모두 존재. `ThesisSnapshot.asof_date/data_coverage/universe_snapshot/ordered_indicator_ids` 모두 존재 |
| `plan/thesis_control_phase3_frontend_redesign.md` | **(A) 완전 구현** | PR-7(`display_unit` 마이그레이션 `0004/0005`), PR-8(`RealValueIndicatorCard`/`AISummarySection`/`NotableChangesSection`), PR-9(`ChartToggleButton`/`PeriodSelector`/`IndividualMiniCharts`) 모두 존재. PR-10(AI 파이프라인 `generate_thesis_summaries`)도 `tasks/summary.py`로 구현 |
| `plan/talking_builder/llm_builder_plan.md` + `redesign_build_plan/*` | **(A) 완전 구현** | `feature_flags.py`, `builder_state.py`, `prompt_builder.py`, `llm_postprocess.py`, `builder_events.py`, `keyword_cache.py`, `keyword_collectors/{chain,eod,news}.py` 모두 존재. 관리 명령(`check_keywords`, `builder_stats`, `keyword_health_check`) 존재 |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | **(A) 완전 구현** | `quarterly_metric_fetcher.py` 존재, `data_source='metrics'` 마이그레이션 `0008` 적용, 프론트 `QuarterlySparkline`/`is_quarterly` 분기 구현 |
| `plan/talking_builder/thesis_builder_redesign_v2.md` | (확인 필요) | 본 감사에서는 미열람 |

### B. Phase 1 프런트엔드 (docs/thesis_control/*phase1_frontend*)

| 문서 | 분류 | 구현 위치 |
|------|------|----------|
| `thesis_control_phase1_frontend_FE_PR_1.md` (라우팅 + 공통) | **(A) 완전** | `app/thesis/{layout,(list),new,[thesisId]}`, `components/thesis/common/*` |
| `thesis_control_phase1_frontend_FE_PR_2.md` (목록 + 진입점) | **(B) 부분** | `ThesisListCard`, `TodayChangeCard`, `EntryPointGrid` 모두 존재하나 진입점이 1개로 축소 (설계의 5경로 → 1버튼) |
| `thesis_control_phase1_frontend_FE_PR_3.md` (대화형 빌더) | **(A→D) 대체** | 위자드 빌더는 존재하나 메인 경로가 **LLM one-shot 모드**로 교체됨 (`talking_builder` Phase A) |
| `thesis_control_phase1_frontend_FE_PR_4.md` (지표 설정) | **(A) 완전** | `app/thesis/[thesisId]/indicators/page.tsx` 326줄, `AddIndicatorSheet`/`IndicatorSetupCard`/`RecommendCard` |
| `thesis_control_phase1_frontend_FE_PR_5.md` (대시보드 — 달 위상) | **(D) 폐기/대체** | 원래 `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 컴포넌트는 Phase 3 리디자인에서 삭제. `MoonPhase`는 목록 페이지(`ThesisListCard`)에만 잔류 |
| `thesis_control_phase1_frontend_FE_PR_*prompts.md` | (참고용) | 프롬프트 모음, 구현 분류 대상 아님 |

### C. 작업 완료 보고서 (frontend/task_done/)

| 보고서 | 보고된 작업 | 코드상 검증 |
|--------|-----------|-----------|
| `FE-PR-1_routing_common_components.md` | 라우팅 + 공통 컴포넌트 | ✅ `common/{AlertBell,ArrowIndicator,BottomSheet,IndicatorCard,MoonPhase,ThesisBadge}` 모두 존재 |
| `FE-PR-2_thesis_list_page.md` | 목록 페이지 | ✅ 존재 (단, EntryPointGrid 축소됨) |
| `FE-PR-3_builder_implementation.md` + `FE-PR-3_plan_review_v3.md` | 6단계 위자드 빌더 | ✅ `new/page.tsx` 1072줄 (위자드+LLM 두 모드 공존) |
| `FE-PR-4_indicator_setup.md` | 지표 설정 | ✅ `indicators/page.tsx` 326줄 |
| `FE-PR-5_dashboard.md` | 달 위상 대시보드 | ⚠️ 보고서에는 `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 신규 생성으로 적혀 있으나, Phase 3 리디자인에서 **3개 모두 삭제됨**. 보고서가 시점적으로는 옳지만 현재 상태는 다름 |
| `FE-PR-6_alerts_close_qa.md` | 알림 + 마감 + QA | ✅ `alerts/page.tsx`, `close/page.tsx` 모두 존재 |
| `Phase2_completion_summary.md` | Phase 2 종합 + Phase 3 계획(FE-PR-7~11) | ⚠️ §8 Phase 3 계획표는 **사실상 폐기**됨. 실제로 진행된 Phase 3는 `thesis_control_phase3_frontend_redesign.md`(대시보드 리디자인) |

### D. work_done/

| 보고서 | 분류 |
|--------|------|
| `work_done/phase_a_llm_builder.md` | **(A) 완료 확인** — PR-1~7 모두 코드상 검증됨 |

---

## Phase 3 미구현 항목 상세

Phase 3는 문서 정의가 충돌하므로 두 갈래로 나눠 본다.

### 갈래 1: `Phase2_completion_summary.md` §8의 FE-PR-7~11 (깊이 + 회고 + 프로필)

이 계획표는 사용자가 질문에서 언급한 **"FE-PR-7~11 설계"**에 해당. **다섯 PR 모두 코드에 없음.**

| PR | 설계 의도 | 코드 상태 | 분류 |
|----|----------|---------|------|
| **FE-PR-7** | 대시보드 3탭 구조 (관제 / 상세 / 히스토리) + 전제 CRUD | 대시보드는 단일 페이지(`[thesisId]/page.tsx`)에 종속. **3탭 없음**. 전제 CRUD API(`ThesisPremiseViewSet`)는 백엔드에 존재하나 프론트 UI 미연결 | **(C) 미구현** |
| **FE-PR-8** | 히트맵 + 지표 상세 편집 (weight/direction) | 백엔드 `DashboardView`가 `heatmap.cells`를 응답에 포함하나, 프론트에서 `HeatmapView` 컴포넌트 자체 없음(`grep -i heat`/`graph` → 0건). 지표 weight/direction 편집 UI 없음 (백엔드 `ThesisIndicatorViewSet` PATCH는 있음) | **(C) 미구현** |
| **FE-PR-9** | 히스토리 탭 (recharts 라인 차트 + 스냅샷 타임라인) | 스냅샷 모델(`ThesisSnapshot`)과 일별 생성 태스크(`create_snapshots_and_alerts`)는 존재하나, 스냅샷 시계열을 노출하는 API 엔드포인트 및 프론트 컴포넌트 부재. `IndividualMiniCharts`는 *지표별* 차트일 뿐 *가설 전체 점수*의 시간 추이를 보여주지 않음 | **(C) 미구현** |
| **FE-PR-10** | 마감 아카이브 + ValidityMatrix | `ValidityRecord` 모델은 존재(2x2 매트릭스 점수 포함), 그러나 마감 시 자동 생성 로직과 마감 가설 목록 UI 없음. `close/page.tsx`는 outcome 선택만 |  **(C) 미구현** |
| **FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `InvestorDNA` 모델은 존재. 자동 갱신 signal/task 없음. 프로필 화면 라우트/컴포넌트 부재 | **(C) 미구현** |

### 갈래 2: `thesis_control_design.md` §7 Phase 3 (커뮤니티 + 고도화)

| 항목 | 설계 의도 | 코드 상태 | 분류 |
|------|----------|---------|------|
| 인기 가설 시스템 | 인기 가설 카드 + 추적자 수 + 지지 비율 | `PopularThesisCache` 모델만 존재(`admin.py`에서 list_display 확인됨). 캐시 갱신 태스크/엔드포인트/UI 모두 없음 | **(C) 미구현** |
| 가설 따라하기 | "나도 추적할래" / "내 방식으로 수정" | `ThesisFollow` 모델만 존재. `copied_from` 필드도 `Thesis` 모델에 정의됨. API/UI 미구현 | **(C) 미구현** |
| 템플릿 시스템 | 이벤트형/추세형/비교형/괴리형 4유형 | 모델·뷰·UI 모두 없음 | **(C) 미구현** |
| Chain Sight 진입 | 그래프 노드에서 "📌 가설 세우기" → 자동 컨텍스트 주입 | Chain Sight 노드 ↔ 가설 연계 API 없음. 단, 빌더의 **키워드 힌트 시스템**(`keyword_collectors/chain.py`)이 Neo4j를 사용하는 형태로 부분 대체됨 | **(B) 부분 구현 — 대체** |
| 가설 마감 + 복기 | 마감 시 "가장 유용했던 지표", "예상과 달랐던 부분" 정성 분석 | `close/page.tsx`는 단순 outcome 선택만(212줄). 복기 LLM 호출/요약 표시 미구현. `outcome_note` 필드만 존재 | **(B) 부분 구현** |
| Neo4j 가설 관계 그래프 | `(Thesis)-[SIMILAR_TO]-(Thesis)` 등 | 가설간 관계 노드 생성/조회 로직 없음. Neo4j는 Chain Sight용 키워드 추출에만 사용 | **(C) 미구현** |
| 가설 아카이브 + 학습 이력 | 마감 가설 리스트, 시간순 회고 | `Thesis.status='closed'` 필터 API는 있으나, 회고 화면 없음 | **(C) 미구현** |

### 갈래 3 (참고): 사용자 기대 외 — 5가지 진입 경로의 축소

설계서 §2.3 "5가지 진입 경로"는 강한 UX 차별화 포인트였으나 현 코드에서는 단일 버튼(`EntryPointGrid.tsx` 20줄)으로 통폐합됨. 백엔드 진입 소스 enum(`news/free_input/popular/template/chainsight`)은 그대로 남아있음.

| 진입 경로 | 백엔드 enum | 프런트 UI |
|----------|------------|----------|
| 📰 오늘 이슈 | ✅ `news`, `NewsIssuesView` 존재 | ❌ 진입점 카드 없음 |
| 💬 내 생각 (자유 입력) | ✅ `free_input` | ✅ 단일 버튼 → LLM 모드 |
| 🔥 인기 가설 | ✅ `popular` | ❌ 미구현 |
| 📋 템플릿 | ✅ `template` | ❌ 미구현 |
| 🔗 Chain Sight | ✅ `chainsight` | ❌ 미구현 |

→ **분류: (D) 폐기/대체** — 의도된 축소인지 단순 미완성인지는 코드만으로는 판별 불가. 다만 백엔드 enum이 유지되고 있어 향후 복원 가능성은 열려 있음.

---

## 부록: 분류 (A/B/C/D) 한 줄 요약

- **(A) 완전 구현 (~)** — Phase 1 데이터 모델, v2.3.2 수학 엔진, LLM 빌더(A-MVP+Hardening+B), Phase 3 대시보드 리디자인(real value + AI summary + 미니차트), 분기 지표 fetcher
- **(B) 부분 구현 (~)** — 5가지 진입 경로(자유 입력만), 세 가지 뷰(카드만), 가설 마감 복기(outcome만), Chain Sight 연동(키워드 힌트만), 이벤트/유효성/DNA(모델만)
- **(C) 미구현** — Phase 2 완료 보고서의 FE-PR-7~11(3탭/히트맵/히스토리/마감 아카이브/DNA 프로필) 전체, Phase 3 커뮤니티 단계 전체, Neo4j 가설 관계, Phase 4 합성 에이전트/벡터 스코어링
- **(D) 폐기/대체** — `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` (Phase 3 리디자인으로 삭제), 6단계 위자드 빌더(LLM one-shot이 메인 경로로 대체, 위자드는 fallback으로 잔존), 진입점 5개 카드(단일 버튼으로 축소)
