# Thesis Control 설계 갭 감사

> 감사 일자: 2026-04-28
> 감사 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` 백엔드 + `frontend/components/thesis/` 프론트엔드 코드
> 감사자: 읽기 전용 (코드 수정 없음)
> 정책: 분류 (A) 완전 구현 (B) 부분 구현 (C) 미구현 (D) 폐기/대체

---

## 0. 핵심 발견

### "Phase 3"가 두 가지 의미로 혼재되어 있음

설계 문서에서 "Phase 3"는 **시점에 따라 서로 다른 두 가지 계획**을 가리킨다.

| 출처 | "Phase 3" 정의 | 작성 시점 | 상태 |
|---|---|---|---|
| `frontend/task_done/Phase2_completion_summary.md` (§8) | **FE-PR-7~11**: 탭 구조 + 히트맵 편집 + 히스토리 탭 + 마감 아카이브 + DNA 프로필 | 2026-03-16 | **D. 폐기/대체** (후속 리디자인이 대체) |
| `plan/thesis_control_phase3_frontend_redesign.md` | **PR-7~10**: 백엔드 raw_value 확장 + 실제 값 카드 + 미니차트 + AI 파이프라인 | 2026-03-18 | **B. 부분 구현** (PR-7/8 완료, PR-9 변형 구현, PR-10 미구현) |
| `plan/thesis_control_integrated_roadmap.md` (§3) | 합성 에이전트 + Online LR (특허 차별화 레이어) | — | **C. 미구현** (Phase 1 골격만 있음) |

**결론**: 사용자가 "Phase 3 미구현 항목"이라고 부를 때 가리키는 대상은 (1) 옛 FE-PR-7~11 계획인지 (2) 신 redesign PR-7~10 계획인지 (3) 통합 로드맵 Phase 3인지 명시 필요. 본 감사는 **세 갈래 모두**를 분리해 정리한다.

---

## 1. 요약 (Phase별 구현률)

| 계획 트랙 | 구현률 | 비고 |
|---|---|---|
| **Phase 1 MVP** (관제 엔진 + 이벤트/유효성 골격) | **~95%** A | HypothesisEvent/ValidityRecord/InvestorDNA 모델 + signal 통합 완료. EOD 3-task 파이프라인 가동 |
| **Phase 2 — 옛 FE 요약 (FE-PR-7~11)** | **0%** D | 탭/히트맵/히스토리/아카이브/DNA 프로필 화면 — **존재하지 않음. 후속 리디자인이 대체** |
| **Phase 3 — 신 리디자인 (PR-7~10)** | **~70%** B | PR-7 백엔드 ✅, PR-8 카드/AI섹션 ✅, PR-9 차트 ⚠️ 변형 통합, PR-10 AI 파이프라인 ❌ |
| **Phase 2 통합 로드맵 (DNA 슬라이더 + ValidityScore)** | **0%** C | ValidityScore 모델 없음, personalization_weight 필드만 미리 생성됨 |
| **Phase 3 통합 로드맵 (합성 에이전트)** | **0%** C | SyntheticBootstrapper 부재 |
| **Phase 4 통합 로드맵 (벡터 스코어링)** | **0%** C | DNA 벡터화/유효성 벡터 부재 |
| **Talking Builder Redesign — Phase A** | **~100%** A | LLM one-shot proposal 구현 완료 (`work_done/phase_a_llm_builder.md`) |
| **Talking Builder Redesign — Phase B** | **부분** B | KeywordCache 모델 (migration 0006/0007) 존재. 운영 검증/자세한 모니터링은 미확인 |

---

## 2. 문서별 상태 테이블

### 2.1 Plan 문서 (`docs/thesis_control/plan/`)

| 문서 | 상태 | 핵심 내용 | 코드 매핑 |
|---|---|---|---|
| `thesis_control_design.md` (1370L) | A — 종합 설계 | 4-phase 종합 설계 (가설 모델, 관제실, 커뮤니티, 지능화) | thesis/models, views 전반 |
| `thesis_control_implementation_guide.md` (286L) | A | Phase 1 구현 가이드 | EOD pipeline, 3-task |
| `thesis_control_integrated_roadmap.md` (660L) | B (부분) | Phase 1~4 통합 로드맵 (특허 + 수학 모델) | Phase 1만 구현 |
| `thesis_control_math_model_final.md` (1153L) | A | v2.3.2 Stage 0~3 수학 모델 | indicator_scorer, snapshot_builder, data_validator |
| `thesis_control_phase3_frontend_redesign.md` (1095L) | **B (부분)** | 신 Phase 3 — PR-7~10 (실제 값 + AI 분석 + 차트) | frontend dashboard 컴포넌트 |
| `talking_builder/llm_builder_plan.md` (563L) | A | LLM one-shot 빌더 v1 계획 | work_done/phase_a_llm_builder.md 참조 |
| `talking_builder/quarterly_indicator_dashboard_plan.md` (424L) | A | 분기 지표 대시보드 | QuarterlySparkline + IndicatorRow |
| `talking_builder/thesis_builder_redesign_v2.md` (1110L) | A | 빌더 재설계 v2 | thesis/services/thesis_builder.py |
| `talking_builder/redesign_build_plan/00_total_plan.md` (525L) | B | 빌더 v4 — Phase A/B/C/Spike | Phase A 완료, B 부분 |
| `redesign_build_plan/01_phase_a_mvp.md` (287L) | A | Phase A MVP — 2-3일 | 완료 (커밋 09b0f8b) |
| `redesign_build_plan/02_phase_a_hardening.md` (118L) | A | Phase A Hardening | 완료 (커밋 6d72432) |
| `redesign_build_plan/03_phase_b_keywords.md` (299L) | B (부분) | Phase B Keyword Enrichment | KeywordCache 모델만 확인됨 |
| `redesign_build_plan/04_phase_c_advanced.md` (144L) | C | Phase C 고급 기능 | 미착수 |
| `redesign_build_plan/05_summary.md` (100L) | — | 요약 | — |

### 2.2 Frontend 작업 보고서 (`docs/thesis_control/frontend/task_done/`)

| 보고서 | 상태 | 결론 |
|---|---|---|
| `FE-PR-1_routing_common_components.md` (225L) | **A** | 라우팅 7개 + 공통 컴포넌트 5개 + authAxios 공유 모듈 — 완료 |
| `FE-PR-2_thesis_list_page.md` (505L) | **A** | 가설 목록 + 오늘의 변화 + 진입점 — 완료 |
| `FE-PR-3_builder_implementation.md` + `FE-PR-3_plan_review_v3.md` | **A** | 대화형 빌더 6단계 — 완료 |
| `FE-PR-4_indicator_setup.md` (237L) | **A** | 지표 설정 + AI 추천 + Route Group 분리 — 완료 |
| `FE-PR-5_dashboard.md` (299L) | **D (대체)** | 달 위상 + 화살표 대시보드 — **신 Phase 3 리디자인이 OverallMoon/DashboardIndicatorCard/RecentChange 삭제** |
| `FE-PR-6_alerts_close_qa.md` (413L) | **A** | 알림 + 마감 + API 수정 — 완료 |
| `Phase2_completion_summary.md` §8 (FE-PR-7~11) | **D (폐기)** | 탭/히트맵/히스토리/아카이브/DNA 프로필 — **신 Phase 3 리디자인이 다른 방향으로 대체** |

### 2.3 Phase 1 관련 (`docs/thesis_control/*.md` 루트)

| 문서 | 상태 | 비고 |
|---|---|---|
| `thesis_control_phase1_frontend_FE_PR_1~5.md` (총 7012L) | A — Phase 2 완료 | FE-PR-1~6 보고서들과 일치 |
| `thesis_control_phase1_frontend_prompts.md` (1106L) | — | 프론트엔드 프롬프트 (참고용) |
| `thesis_control_phase1_prompts.md` (1243L) | — | 백엔드 프롬프트 (참고용) |
| `thesis_control_user_experience.md` (435L) | — | UX 설계 |

### 2.4 Work Done (`docs/thesis_control/work_done/`)

| 보고서 | 상태 | 비고 |
|---|---|---|
| `phase_a_llm_builder.md` (194L) | A | Phase A MVP + Hardening 완료. 테스트 104개. E2E 검증 완료 |

---

## 3. Phase 3 미구현 항목 상세

### 3.1 신 Phase 3 리디자인 (PR-7~10) — 기준: `plan/thesis_control_phase3_frontend_redesign.md`

#### PR-7: 백엔드 확장 — **A. 완전 구현**

| 항목 | 설계 | 코드 위치 | 상태 |
|---|---|---|---|
| `ThesisIndicator.display_unit` 필드 | §4-1 | `thesis/models/indicator.py:73-76` | ✅ A |
| 마이그레이션 `0004_add_display_unit` | §4-1 | `thesis/migrations/0004_add_display_unit.py` | ✅ A |
| 데이터 마이그레이션 `0005_populate_display_unit` | §4-7 | `thesis/migrations/0005_populate_display_unit.py` | ✅ A |
| `DashboardView` raw_value 필드 4개 | §4-2 | `thesis/views/monitoring_views.py:94-174` | ✅ A |
| `_infer_unit()` fallback | §4-3 | `thesis/views/monitoring_views.py:346-364` | ✅ A |
| `IndicatorReadingsView` (GET readings) | §4-4 | `thesis/views/monitoring_views.py:260-290` | ✅ A (FMP fallback 추가까지 확장) |
| URL 등록 | §4-5 | `thesis/urls.py:30-34` | ✅ A |

#### PR-8: 프론트엔드 카드 + AI 분석 — **A. 완전 구현**

| 항목 | 설계 | 코드 위치 | 상태 |
|---|---|---|---|
| 타입 확장 (DashboardIndicator, NotableChange, IndicatorReadingsResponse) | §5-1 | `frontend/lib/thesis/types.ts` | ✅ A (확인됨, 사용 중) |
| `thesisApi.indicatorReadings` 메서드 | §5-2 | `frontend/lib/thesis/api.ts` | ✅ A |
| `useIndicatorReadings` 쿼리 훅 | §5-3 | `frontend/lib/thesis/queries.ts` (IndicatorRow에서 사용) | ✅ A |
| `formatRawValue` / `formatChangePct` / `supportLabel` 유틸 | §5-4 | `frontend/lib/thesis/utils.ts` (IndicatorRow에서 import) | ✅ A |
| Mock 데이터 확장 | §5-5 | `frontend/lib/thesis/mock.ts` | ✅ A |
| `RealValueIndicatorCard.tsx` | §5-6 | `frontend/components/thesis/dashboard/RealValueIndicatorCard.tsx` | ⚠️ **B 파일 존재하나 사용 안 됨** (IndicatorRow가 동등 기능 통합) |
| `AISummarySection.tsx` | §5-7 | `frontend/components/thesis/dashboard/AISummarySection.tsx` (page.tsx:75에서 사용) | ✅ A |
| `NotableChangesSection.tsx` | §5-8 | `frontend/components/thesis/dashboard/NotableChangesSection.tsx` (page.tsx:81에서 사용) | ✅ A |
| `app/thesis/[thesisId]/page.tsx` 재구성 | §5-9 | `frontend/app/thesis/[thesisId]/page.tsx` | ✅ A (단, IndicatorRow로 변형 통합) |

#### PR-9: 미니차트 + 기간 선택 + 정리 — **B. 부분 구현 (변형됨)**

| 항목 | 설계 | 실제 구현 | 상태 |
|---|---|---|---|
| `ChartToggleButton.tsx` | §6-1 (전체 토글) | `frontend/components/thesis/dashboard/ChartToggleButton.tsx` | ⚠️ **D 파일 존재하나 미사용** — page.tsx에서 import 안 됨 |
| `PeriodSelector.tsx` | §6-2 (7D/14D/30D) | `frontend/components/thesis/dashboard/PeriodSelector.tsx` | ⚠️ **D 파일 존재하나 미사용** — IndicatorRow가 자체적으로 1M/1Y/3Y/5Y 셀렉터 구현 |
| `IndividualMiniCharts.tsx` (지표별 독립 미니차트, 묶음) | §6-5 | `frontend/components/thesis/dashboard/IndividualMiniCharts.tsx` | ⚠️ **D 파일 존재하나 미사용** — IndicatorRow가 행 단위로 인라인 차트 통합 |
| `useAllIndicatorReadings` 훅 | §6-4 | `frontend/lib/thesis/queries.ts` (`useIndicatorReadings` 단일 훅으로 단순화) | B (변형) |
| `CHART_COLORS` / `PERIOD_OPTIONS` 상수 | §6-3 | `frontend/lib/thesis/constants.ts` | 미확인 |
| `MOCK_READINGS` Mock | §6-6 | `frontend/lib/thesis/mock.ts` | 미확인 |
| `OverallMoon.tsx` 삭제 | §6-8 | dashboard 디렉토리에 없음 | ✅ A |
| `DashboardIndicatorCard.tsx` 삭제 | §6-8 | dashboard 디렉토리에 없음 | ✅ A |
| `RecentChange.tsx` 삭제 | §6-8 | dashboard 디렉토리에 없음 | ✅ A |
| `MoonPhase.tsx` (common) 처리 | §6-8 (다른 곳 미사용 시 삭제) | 여전히 존재 + `(list)/page.tsx:140`, `ThesisListCard.tsx:23`에서 사용 | ✅ A (목록 화면용으로 유지가 정답) |
| `scoreToPhaseMeta()` 삭제 | §6-8 | 미확인 | ⚠️ B (확인 필요) |
| 차트 7D/14D/30D 기간 옵션 | §6-3 | IndicatorRow는 30/365/1095/1825일 (1M/1Y/3Y/5Y) | ⚠️ **C 설계 불일치** (장기 분기 지표 대응 위해 의도적으로 변경됨) |

**핵심 변형 결정**: 설계서는 "카드(상단) + 토글버튼 + 기간선택 + 묶음 미니차트(하단)"로 분리했으나, 실제 구현은 **각 지표 카드 자체에 차트가 인라인 통합된 `IndicatorRow`** 단일 컴포넌트로 통합되었음. 결과적으로 ChartToggleButton/PeriodSelector/IndividualMiniCharts/RealValueIndicatorCard 4개 파일은 **고아 코드(orphan)** 상태.

#### PR-10: AI 모니터링 파이프라인 — **C. 미구현**

| 항목 | 설계 | 실제 구현 | 상태 |
|---|---|---|---|
| `generate_thesis_summaries` Celery task (07:30) | §7-1 | **존재하지 않음** (`thesis/tasks/eod_pipeline.py`에 3 task만: update_indicator_readings, calculate_scores, create_snapshots_and_alerts) | ❌ **C** |
| Gemini 2.5 Flash로 ai_summary 생성 | §7-1 | 없음 | ❌ C |
| `ThesisSnapshot.ai_summary` 필드 | (선행 조건) | `thesis/models/monitoring.py:26` 존재 | ✅ A (스키마만) |
| `notable_changes` alert 이벤트 변환 (sharp_move/direction_flip/extreme_volatility) | §7-2 | `snapshot_builder.py:105-122`는 **score-delta 기반** 이벤트 생성 (alert_type/severity/raw_value_before/after 누락) | ⚠️ **B 형식 불일치** |
| Weekly Health Check | §7-3 | 없음 | ❌ C (Phase 2+ 향) |

**PROGRESS.md 자체 인정**: "audit P0 후속 큐 — `#15 thesis generate_thesis_summaries` — Celery task 미구현, AISummarySection이 항상 빈 문자열" (line 63).

**사용자 영향**:
- AISummarySection 컴포넌트는 렌더링되지만 `latest_snapshot.ai_summary`가 항상 빈 문자열이라 실제 화면에서는 빈 박스만 노출됨 (또는 컴포넌트 내부 if 분기로 미렌더 처리되어 사용자에게 보이지 않음). 
- NotableChangesSection은 `notable_changes` JSON이 일부 채워지지만 PR-10 스키마(change_type/severity/description)와 다른 score-delta 포맷이라 프론트가 기대하는 필드 누락 가능성.

---

### 3.2 옛 FE-PR-7~11 (Phase 2 완료 보고서 §8) — **D. 폐기/대체**

`Phase2_completion_summary.md` 마지막 섹션의 계획표:

| PR | 계획 제목 | 핵심 | 코드 존재 여부 | 결론 |
|---|---|---|---|---|
| FE-PR-7 | 대시보드 탭 구조 + 상세 탭 | 3탭 (관제/상세/히스토리) + 전제 CRUD | ❌ 탭 컴포넌트 없음 | **D** 신 리디자인이 단일 화면 + 인라인 차트로 대체 |
| FE-PR-8 | 히트맵 + 지표 상세 편집 | Finviz 스타일 히트맵 + weight/direction 편집 | ❌ 히트맵 편집 UI 없음 (백엔드 응답에 heatmap 객체는 있음) | **D** 리디자인이 raw_value 카드로 대체 |
| FE-PR-9 | 히스토리 탭 | recharts 라인 차트 + 스냅샷 타임라인 | ❌ 히스토리 탭 페이지/컴포넌트 없음 | **D** 차트가 IndicatorRow 인라인으로 흡수 (스냅샷 타임라인은 미구현) |
| FE-PR-10 | 마감 아카이브 + 요약 | 마감 가설 목록 + ValidityMatrix | ❌ `/thesis?status=closed` 같은 아카이브 페이지 없음, ValidityMatrix UI 없음 | **C** 백엔드 ValidityRecord는 있으나 화면 미구현 |
| FE-PR-11 | 투자자 DNA 프로필 | AccuracyRing + CategoryChart + 기술 부채 정리 | ❌ DNA 프로필 페이지/컴포넌트 없음 (백엔드 InvestorDNA 모델만 존재) | **C** 백엔드 모델·집계만 있고 사용자 노출 화면 0% |

**핵심 결론**: 사용자 메모리에 "Phase 3 진행 중 — FE-PR-7~11"로 기록되어 있고 CLAUDE.md(`# CLAUDE.md > 진행 중` 라인)에도 동일 표현이 있으나, 이는 **계획만 존재하던 옛 PR 분기**이며 실제로는 2026-03-18 작성된 신 리디자인 문서(`thesis_control_phase3_frontend_redesign.md`)가 사실상 Phase 3 전체를 대체했다. 마감 아카이브(FE-PR-10) + DNA 프로필(FE-PR-11)은 **두 트랙 어디에도 화면 구현이 없는 진짜 미구현 항목**.

---

### 3.3 통합 로드맵 Phase 2~4 (`integrated_roadmap.md`) — 특허·학습 레이어

#### Phase 1 골격 (이벤트 + 유효성 + DNA) — **A. 거의 완전 구현**

| 항목 | 코드 위치 | 상태 |
|---|---|---|
| `HypothesisEvent` 모델 | `thesis/models/learning.py:7-52` | ✅ A |
| 13종 event_type | learning.py:10-24 | ✅ A |
| `HypothesisEvent.objects.create(...)` 삽입 13곳 | thesis_views.py 7곳 + thesis_builder.py 등 | ✅ A |
| `ValidityRecord` 모델 + 2x2 매트릭스 | learning.py:55-94 | ✅ A |
| 가설 마감 시 ValidityRecord 생성 | thesis_views.py:84-102 | ✅ A |
| `InvestorDNA` 모델 + 집계 필드 | learning.py:97-152 | ✅ A |
| 마감 시 InvestorDNA 갱신 (`_update_investor_dna`) | thesis_views.py:137-141, 293+ | ✅ A |
| `accuracy_rate` / `ai_accept_rate` / `top_down_ratio` properties | learning.py:128-149 | ✅ A |
| Django Admin 등록 | `thesis/admin.py:76` | ✅ A |
| **사용자 노출 UI** | 없음 | ❌ **C** |

#### Phase 2 (DNA 슬라이더 + ValidityScore 활성화) — **C. 미구현**

| 항목 | 설계 | 상태 |
|---|---|---|
| `ValidityScore` 모델 (집계 결과 테이블) | §2.1 | ❌ C |
| 주 1회 ValidityRecord → ValidityScore 집계 Celery task | §2.1 | ❌ C |
| `match_indicators` 유효성 점수 반영 | §2.2 | ❌ C |
| `apply_dna_personalization` 슬라이더 | §2.3 | ❌ C |
| `add_contrarian_nudge` 역제안 | §2.4 | ❌ C |
| 상관계수 자동 할인 / Adaptive Decay / Sustained Extreme | §2.5 | ❌ C |
| `personalization_weight` 필드 | InvestorDNA에 미리 생성됨 (learning.py:124) | ✅ A (스키마만) |

#### Phase 3 (합성 에이전트 + Online LR) — **C. 완전 미구현**

| 항목 | 설계 | 상태 |
|---|---|---|
| `SyntheticBootstrapper` 클래스 | §3.1 | ❌ C |
| `SYNTHETIC_PERSONAS` 20-30개 | §3.1 | ❌ C |
| `ValidityRecord.is_synthetic` 필드 | §3.1 | ❌ C |
| `ThesisWeightLearner` (Online Logistic Regression) | §3.2 | ❌ C |
| 합성/실제 데이터 블렌딩 로직 | §3.3 | ❌ C |

#### Phase 4 (벡터 스코어링) — **C. 완전 미구현**

| 항목 | 설계 | 상태 |
|---|---|---|
| `build_dna_vector` 16차원 | §4.1 | ❌ C |
| `ValidityVector` 6차원 | §4.2 | ❌ C |
| 코사인 유사도 추천 | §4.3 | ❌ C |
| 사용자 유사도 (`find_similar_investors`) | §4.4 | ❌ C |

---

### 3.4 Talking Builder Redesign — Phase B 키워드 모니터링

| 항목 | 설계 (`03_phase_b_keywords.md`) | 코드 매핑 | 상태 |
|---|---|---|---|
| `KeywordCache` 모델 | 4-6 | `thesis/models/keyword.py` (migration 0006) | ✅ A |
| `strength` 필드 (Phase C+이라 했으나 0007에서 추가됨) | C+ | migration 0007 | ✅ A (앞당겨 추가) |
| Source별 TTL (news 24h / eod 24h / chain 7d) | 4-6 | `services/keyword_cache.py` (확인 권장) | B (모델 존재, 운영 검증 미확인) |
| `collect_from_cache` freshness cutoff | 4-6 | `services/keyword_cache.py` | B |
| `build_keyword_hint_block` (role 그룹핑 프롬프트 주입) | 4-5 | `services/keyword_hint.py` 또는 `prompt_builder.py` | B (파일 존재) |
| Replace-all 정책 | 4-6 | (확인 필요) | B |
| `check_keywords` management command | 4-7 | `thesis/management/commands/` 안에 있는지 미확인 | B/C |
| Django Admin 등록 | 4-7 | (확인 필요) | B |
| Layer A/B/C 모니터링 로그 | 4-7 | builder_events.py (`keyword_extracted`/`keyword_extraction_failed`/`keyword_stale_or_missing`) | B (이벤트 정의 여부 확인 필요) |
| Daily Health Report / batch versioning | Phase B 후반 | 없음 | C |

---

## 4. 부록 — 코드 사실 체크리스트

### 4.1 백엔드 thesis 앱 — 마이그레이션 상태

```
0001_initial.py                       ← 모든 모델 (Thesis, Premise, Indicator, Reading, Snapshot, Alert, HypothesisEvent, ValidityRecord, InvestorDNA, Community)
0002_remove_thesissnapshot_date_and_more.py
0003_fix_fk_on_delete_set_null.py
0004_add_display_unit.py              ← Phase 3 PR-7
0005_populate_display_unit.py         ← Phase 3 PR-7 데이터 마이그레이션
0006_add_keyword_cache.py             ← Phase B 키워드
0007_keyword_cache_add_strength.py    ← Phase B+ strength 앞당김
0008_add_metrics_data_source.py       ← 분기 지표
0009_add_recommendation_reason.py     ← 관제실 지표 설명
```

### 4.2 프론트엔드 dashboard 컴포넌트 사용 여부

| 파일 | page.tsx에서 사용? | 결론 |
|---|---|---|
| `AISummarySection.tsx` | ✅ Yes (line 75) | A |
| `NotableChangesSection.tsx` | ✅ Yes (line 81) | A |
| `DashboardHeader.tsx` | ✅ Yes (line 72) | A |
| `DashboardPageHeader.tsx` | ✅ Yes (line 64) | A |
| `IndicatorRow.tsx` | ✅ Yes (line 115) | A — **Phase 3 핵심 통합 컴포넌트** |
| `QuarterlySparkline.tsx` | ✅ (IndicatorRow 내부에서) | A |
| `RealValueIndicatorCard.tsx` | ❌ No — 어디서도 import 안 됨 | **D 고아 (Orphan)** |
| `ChartToggleButton.tsx` | ❌ No | **D 고아** |
| `PeriodSelector.tsx` | ❌ No | **D 고아** |
| `IndividualMiniCharts.tsx` | ❌ No | **D 고아** |

### 4.3 Celery EOD 파이프라인 (`thesis/tasks/eod_pipeline.py`)

```
@shared_task(bind=True, max_retries=3)
def update_indicator_readings(self):       # 18:00 ET
def calculate_scores(self):                 # 18:15 ET
def create_snapshots_and_alerts(self):      # 18:30 ET
```

**누락**: `generate_thesis_summaries` (PR-10, 07:30 KST 예정)

### 4.4 사용자 노출 화면 매핑 (현행)

```
/thesis                          ← (list)/page.tsx + EntryPointGrid + TodayChange + ThesisListCard
/thesis/new?entry={source}       ← 6단계 위자드 + LLM 모드 (Phase A)
/thesis/alerts                   ← (list)/alerts + AlertFilterTabs + AlertCard
/thesis/[thesisId]               ← 단일 페이지 (DashboardHeader + AI섹션 + Notable + IndicatorRow*)
/thesis/[thesisId]/indicators    ← IndicatorSetupCard + AddIndicatorSheet + RecommendCard
/thesis/[thesisId]/close         ← OutcomeSelector + CloseConfirmDialog
```

**누락 화면 (사용자 메모리·계획 대비)**:
- ❌ 마감 아카이브 (`/thesis?status=closed` 또는 `/thesis/archive`)
- ❌ 투자자 DNA 프로필 페이지
- ❌ 가설 회고 / ValidityMatrix 시각화
- ❌ 가설 깊이 보기 / 히스토리 타임라인 / 스냅샷 비교

---

## 5. 사용자 의사결정 권고

### 즉시 액션 후보 (낮은 비용)

1. **고아 컴포넌트 4개 정리 결정**: `RealValueIndicatorCard.tsx` / `ChartToggleButton.tsx` / `PeriodSelector.tsx` / `IndividualMiniCharts.tsx` — IndicatorRow 통합으로 **사실상 폐기**된 것으로 보이므로 (a) 명시적 삭제 PR 또는 (b) 향후 재활용 시 import할 것이라면 README 주석 추가. 현 상태는 코드베이스 노이즈.
2. **`MoonPhase.tsx` + `scoreToPhaseMeta()` 잔존 여부 재확인**: 설계서 §6-8 "다른 곳 미사용 시 삭제" 권고였으나 `(list)` 화면에서 여전히 사용 중. 설계 의도와 다르나 정상 사용이므로 코멘트 추가 정도.

### 사용자 결정 필요 (중간 비용)

3. **PR-10 generate_thesis_summaries 우선순위**: PROGRESS.md `audit P0 #15`로 등록되어 있으며, 이게 빠지면 AISummarySection은 영구 빈 상태. 단순 LLM 호출 추가 + Beat 등록(#28 패턴)이라 1세션 분량.
4. **notable_changes 포맷 통일**: 현 `snapshot_builder.py`는 score-delta 기반, 프론트 타입은 PR-10의 alert-event 기반(`change_type/severity/description`). 둘 중 하나를 진실의 소스로 정해 매핑.

### 큰 결정 (큰 비용)

5. **옛 FE-PR-7~11 vs 신 PR-7~10 트랙 정합성**: CLAUDE.md `## 진행 중`/PROGRESS.md에는 "Phase 3 (FE-PR-7~11)" 표현 잔존. 신 리디자인이 사실상 다 대체했으므로 문서 정리 필요.
6. **마감 아카이브 + DNA 프로필 화면 구현 여부**: 두 트랙 어디에도 우선순위 고정 못 됨. 백엔드 데이터(InvestorDNA, ValidityRecord)는 1년 가까이 축적 중이나 사용자가 볼 수 없는 상태. 특허 차별점이 사용자 가시성과 직결되므로 의사결정 필요.

---

## 6. 감사 한계

- 일부 frontend 유틸/상수 파일(constants.ts, mock.ts) 내부는 grep만 했고 라인별 검증은 미수행. PR-9 §6-3/§6-6 항목 "미확인" 표시.
- `thesis/services/keyword_cache.py` 등 키워드 관련 서비스 파일은 본문 미열람. Phase B 세부 검증 필요 시 후속 감사.
- "사용자 노출 화면"은 라우트 구조 기준이며 모달/바텀시트 내부 화면은 별도 추적 안 됨.
- 통합 로드맵 Phase 1 "InvestorDNA 자동 갱신 signal" 검증 시 `signal` 미발견하여 `views/thesis_views.py`의 `_update_investor_dna()` 직접 호출 방식인 것으로 판단 (signal 등록 없음). 설계 §1.4의 "Celery 또는 signal" 둘 중 직접 호출 채택. 큰 차이 없음.
