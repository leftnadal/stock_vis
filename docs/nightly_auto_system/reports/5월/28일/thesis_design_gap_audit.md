# Thesis Control 설계 갭 감사

> 감사일: 2026-05-28
> 범위: `docs/thesis_control/` ↔ `thesis/` + `frontend/components/thesis/` + `frontend/app/thesis/`
> 모드: 읽기 전용 (no code edit)
> 분류 기준: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 0. 핵심 발견 (TL;DR)

1. **"Phase 3"는 두 갈래로 분기**되어 문서에 공존한다.
   - **Phase 3-α (대시보드 리디자인)** — `plan/thesis_control_phase3_frontend_redesign.md` (PR-7~10)
     "실제 값 카드 + AI 분석 + 미니차트". → **PR-7/PR-10 완전 구현, PR-8/PR-9 부분 구현(컴포넌트 존재하나 wiring 우회)**
   - **Phase 3-β (깊이 + 회고 + 프로필)** — `frontend/task_done/Phase2_completion_summary.md §8` (FE-PR-7~11)
     "3탭 대시보드 + 히트맵 + 히스토리 + 마감 아카이브 + DNA 프로필". → **전부 미구현 (C)**
2. 사용자가 묻는 "Phase 3 (깊이 + 회고 + 프로필)"은 **Phase 3-β**이며, 프론트 산출물 0건이다. (정식 설계 문서는 Phase2_completion_summary.md §8의 한 표가 유일한 명세.)
3. Phase 3-α PR-8/PR-9 컴포넌트(`RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`)는 **파일은 존재하지만 `app/thesis/[thesisId]/page.tsx`에서 import되지 않는다.** 대시보드 page는 자체 작성된 `IndicatorRow.tsx`(11.5KB)가 카드 + 인라인 차트 + 기간 선택을 통합 흡수했다 — 사실상 PR-8/PR-9 컴포넌트는 **고아(orphan) 상태**.
4. Phase 1 백엔드 학습 인프라(`HypothesisEvent`/`ValidityRecord`/`InvestorDNA`)는 **모델 + 이벤트 기록 훅 + DNA 갱신 로직까지 완전 구현**. 단, 외부 노출 API 없음 → 프론트 활용 불가능 상태로 데이터만 축적 중.
5. `OverallMoon.tsx`/`DashboardIndicatorCard.tsx`/`RecentChange.tsx` 삭제는 완료(파일 부재). `MoonPhase.tsx`는 common/에 잔존(다른 곳에서 미사용일 가능성 — Phase 3-α §2 "import 검색 후 결정" 미이행).

---

## 1. 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 비고 |
|---|---|---|---|
| Phase 1 — 관제 엔진 (v2.3.2) | 백엔드 (Stage 0~3, 스냅샷, EOD pipeline) | **~95% (A)** | `eod_pipeline.py` 3태스크 + `snapshot_builder.py` + `alert_engine.py` 모두 존재 |
| Phase 1 — 이벤트/유효성/DNA 기록 | 백엔드 (HypothesisEvent, ValidityRecord, InvestorDNA) | **~90% (A)** | 모델 + close 시 ValidityRecord 생성 + InvestorDNA 갱신까지. Synthetic flag(`is_synthetic`)는 부재 → Phase 3 합성 에이전트 미선행 |
| Phase 2 — 프론트엔드 핵심 루프 | FE-PR-1~6 (목록·빌더·지표·대시보드·알림·마감) | **~95% (A)** | 6개 task_done 보고서, 모든 라우트 + 30개 컴포넌트 |
| Phase 3-α — 대시보드 리디자인 (PR-7~10) | 백엔드 PR-7/PR-10 + 프론트 PR-8/PR-9 | **~70% (B)** | PR-7 완전 구현(추가 확장까지), PR-10 generate_thesis_summaries 구현. PR-8/PR-9 컴포넌트는 작성됐으나 page.tsx에 wiring 안 됨 |
| Phase 3-β — 깊이 + 회고 + 프로필 (FE-PR-7~11) | 프론트엔드 5개 PR | **~0% (C)** | 라우트/컴포넌트/API 노출 모두 부재. 단 백엔드 데이터 소스(InvestorDNA·ValidityRecord·snapshots)는 존재 |
| Phase 2 — DNA 슬라이더 + 유효성 활성화 | 백엔드 ValidityScore + 추천 로직 | **~0% (C)** | `ValidityScore` 모델/집계 태스크 부재 |
| Phase 3 (수학 모델) — 합성 에이전트 | 백엔드 SyntheticBootstrapper | **0% (C)** | 미구현 |
| Phase 4 — 벡터 스코어링 | 백엔드 DNA 벡터화 | **0% (C)** | 미구현 |

---

## 2. 문서별 상태 테이블

### 2.1 설계 문서 인벤토리

| 문서 | 위치 | 역할 | 구현 매핑 |
|---|---|---|---|
| `thesis_control_design.md` | plan/ | 사용자 플로우/화면 설계 | FE-PR-1~6 (구현 완료) |
| `thesis_control_math_model_final.md` | plan/ | v2.3.2 수학 모델 (Stage 0~3) | Phase 1 백엔드 (A) |
| `thesis_control_implementation_guide.md` | plan/ | 구현 가이드 | Phase 1 (A) |
| `thesis_control_integrated_roadmap.md` | plan/ | Phase 1~4 통합 로드맵 (특허 매핑) | Phase 1 학습 인프라 (A); Phase 2 ValidityScore (C); Phase 3 Synthetic (C); Phase 4 (C) |
| `thesis_control_phase3_frontend_redesign.md` | plan/ | **Phase 3-α** 대시보드 리디자인 PR-7~10 | PR-7 (A), PR-8/9 (B), PR-10 (A) |
| `thesis_control_phase1_prompts.md` | (root) | BE 구현 프롬프트 (Phase 1) | (참고용) |
| `thesis_control_phase1_frontend_prompts.md` | (root) | FE 구현 프롬프트 | FE-PR-1~6 |
| `thesis_control_phase1_frontend_FE_PR_1~5.md` | (root) | 각 PR 사양서 | FE-PR-1~5 (A) — task_done에 보고서 존재 |
| `thesis_control_user_experience.md` | (root) | 화면별 UX 명세 (Phase 2 완료 시점) | Phase 2 화면 (A) |
| `plan/talking_builder/llm_builder_plan.md` | talking_builder/ | 대화형 빌더 LLM 계획 | thesis_builder.py 구현 (~80KB) (A) |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | talking_builder/ | 분기 지표 대시보드 계획 | `quarterly_metric_fetcher.py` + `QuarterlySparkline.tsx` (A) |
| `plan/talking_builder/thesis_builder_redesign_v2.md` | talking_builder/ | 빌더 v2 재설계 | thesis_builder.py (A) |
| `plan/talking_builder/redesign_build_plan/` | talking_builder/ | 빌더 재설계 빌드 플랜 | (참고용) |
| `work_done/phase_a_llm_builder.md` | work_done/ | Phase A 완료 보고 | thesis_builder.py (A) |
| `frontend/task_done/FE-PR-1~6_*.md` | frontend/task_done/ | FE-PR-1~6 완료 보고 | A — 6개 모두 보고서 존재 |
| `frontend/task_done/Phase2_completion_summary.md` | frontend/task_done/ | **§8에서 FE-PR-7~11 (Phase 3-β) 정의** | **C — 0% 구현** |

### 2.2 코드 인벤토리 ↔ 설계 매핑

#### 백엔드 `thesis/`

| 디렉토리/파일 | 설계 매핑 | 상태 |
|---|---|---|
| `models/thesis.py` (Thesis, ThesisPremise) | design.md §3, integrated_roadmap §1.1 | A |
| `models/indicator.py` (ThesisIndicator + display_unit + v2.3.2 필드) | math_model §9, phase3-α PR-7 §4-1 | A |
| `models/indicator.py` (IndicatorReading + validation_status) | math_model §2.2 | A |
| `models/monitoring.py` (ThesisSnapshot, ThesisAlert) | math_model §9, design.md §6 | A — ai_summary/notable_changes/cooldown_hours/target_id 포함 |
| `models/learning.py` (HypothesisEvent, ValidityRecord, InvestorDNA) | integrated_roadmap §1.2~1.4 | A — `is_synthetic` 필드만 누락 (Phase 3 가속용) |
| `models/community.py` (ThesisFollow, PopularThesisCache) | design.md §2.3 경로 3 | A |
| `models/keyword.py` (KeywordCache) | design.md §6 | A |
| `services/indicator_scorer.py` | math_model §3 (Stage 1) | A |
| `services/premise_aggregator.py` | math_model §4 (Stage 2) | A |
| `services/thesis_state_machine.py` | math_model §5 (Stage 3) | A |
| `services/snapshot_builder.py` | math_model §9 | A |
| `services/alert_engine.py` | design.md §6.4 | A — 11개 alert_type 모두 구현 |
| `services/arrow_calculator.py` | design.md §6.2 (화살표) | A |
| `services/data_validator.py` | math_model §2 (Stage 0) | A |
| `services/indicator_matcher.py` | design.md §4 | A |
| `services/thesis_builder.py` (79KB) | llm_builder_plan.md + redesign_v2 | A |
| `services/prompt_builder.py` (49KB) | llm_builder_plan.md | A |
| `services/quarterly_metric_fetcher.py` | quarterly_indicator_dashboard_plan.md | A |
| `views/conversation_views.py` | design.md §2.3 빌더 | A |
| `views/thesis_views.py` (CRUD + close + 이벤트 기록) | integrated_roadmap §1.2 | A |
| `views/monitoring_views.py` (Dashboard, IndicatorReadings, Alerts) | phase3-α PR-7 §4-2/4-4 | A — 추가로 quarterly + FMP fallback 확장 |
| `tasks/eod_pipeline.py` (3 task) | math_model §7 | A |
| `tasks/summary.py` (generate_thesis_summaries) | phase3-α PR-10 §7-1 | A — Gemini 동기, 멱등, NY 18:45 권장 명시 |

#### 프론트엔드 `frontend/components/thesis/`

| 컴포넌트 | 설계 매핑 | 상태 |
|---|---|---|
| `common/AlertBell.tsx`, `ThesisBadge.tsx`, `IndicatorCard.tsx`, `ArrowIndicator.tsx`, `BottomSheet.tsx` | FE-PR-1 | A |
| `common/MoonPhase.tsx` | FE-PR-1, **삭제 후보 (phase3-α §2)** | B — common/에 잔존, dashboard에서는 미사용. 다른 곳 사용 여부 미검증 |
| `list/ThesisListCard.tsx`, `TodayChangeCard.tsx`, `EntryPointGrid.tsx` | FE-PR-2 | A |
| `builder/*.tsx` (9개) | FE-PR-3 | A |
| `indicators/IndicatorSetupCard.tsx`, `AddIndicatorSheet.tsx`, `RecommendCard.tsx` | FE-PR-4 | A |
| `dashboard/DashboardPageHeader.tsx`, `DashboardHeader.tsx` | FE-PR-5 | A |
| `dashboard/IndicatorRow.tsx` (11.5KB) | (설계에 명시 없음 — 자체 통합 작성) | A (사실상 PR-8 카드 + PR-9 차트 통합) |
| `dashboard/QuarterlySparkline.tsx` | quarterly_indicator_dashboard_plan.md | A |
| `dashboard/AISummarySection.tsx` | phase3-α PR-8 §5-7 | A |
| `dashboard/NotableChangesSection.tsx` | phase3-α PR-8 §5-8 | A |
| `dashboard/RealValueIndicatorCard.tsx` | phase3-α PR-8 §5-6 | **D — 고아: IndicatorRow가 흡수, page.tsx에서 import 안 됨** |
| `dashboard/ChartToggleButton.tsx` | phase3-α PR-9 §6-1 | **D — 고아: IndicatorRow의 expand 토글이 대체** |
| `dashboard/PeriodSelector.tsx` | phase3-α PR-9 §6-2 | **D — 고아: IndicatorRow 내 DAILY_PERIODS 인라인이 대체** |
| `dashboard/IndividualMiniCharts.tsx` | phase3-α PR-9 §6-5 | **D — 고아: IndicatorRow 인라인 AreaChart가 대체** |
| `alerts/AlertCard.tsx`, `AlertFilterTabs.tsx`, `EmptyAlerts.tsx` | FE-PR-6 | A |
| `close/CloseConfirmDialog.tsx`, `OutcomeSelector.tsx` | FE-PR-6 | A |
| `skeleton/ThesisSkeleton.tsx` | FE-PR-1 | A |

#### 프론트엔드 `frontend/app/thesis/`

| 라우트 | 설계 매핑 | 상태 |
|---|---|---|
| `(list)/page.tsx` (목록) | FE-PR-2 | A |
| `(list)/alerts/page.tsx` | FE-PR-6 | A |
| `(list)/layout.tsx` | FE-PR-1 | A |
| `layout.tsx` | FE-PR-1 | A |
| `new/page.tsx` (빌더) | FE-PR-3 | A |
| `[thesisId]/page.tsx` (대시보드) | FE-PR-5, phase3-α PR-8 wiring | B — Phase 3-α §5-9 wiring 일부 다름 (RealValueIndicatorCard 미사용, IndicatorRow로 대체) |
| `[thesisId]/indicators/page.tsx` | FE-PR-4 | A |
| `[thesisId]/close/page.tsx` | FE-PR-6 | A |
| `[thesisId]/(history)/`, `[thesisId]/detail/`, `[thesisId]/heatmap/` | FE-PR-7~9 | **C — 라우트 부재** |
| `archive/`, `profile/`, `dna/` 최상위 | FE-PR-10/11 | **C — 라우트 부재** |

---

## 3. Phase 3 미구현 항목 상세 (Phase 3-β: 깊이 + 회고 + 프로필)

> 출처: `frontend/task_done/Phase2_completion_summary.md §8`. 정식 설계서는 부재 (한 표만 존재).

### 3.1 FE-PR-7 — 대시보드 탭 구조 + 상세 탭

**설계 요지**: 단일 대시보드 화면을 **3탭(관제 / 상세 / 히스토리)** 으로 재편 + 상세 탭에서 **전제 CRUD UI** 제공.

**현재 상태**:
- 대시보드 `app/thesis/[thesisId]/page.tsx`는 단일 화면 (탭 컴포넌트 없음).
- 백엔드 `ThesisPremiseViewSet`(`thesis/views/thesis_views.py:147-188`)에 CRUD + 이벤트 기록은 완전 존재 — 프론트 wiring만 빠짐.
- `IndicatorRow.tsx`의 expand 패턴으로 "상세 보기" 일부 흡수, 그러나 전제 편집 UI는 부재.

**갭**:
- [ ] 탭 컨테이너 컴포넌트 (관제/상세/히스토리)
- [ ] 상세 탭: 전제 목록 + 추가/수정/삭제 UI
- [ ] 상세 탭: 가설 메타데이터 편집 (제목/방향/기간/강도)
- [ ] 상세 탭의 mutation 훅 (premiseAdd, premiseUpdate, premiseDelete)

### 3.2 FE-PR-8 — 히트맵 + 지표 상세 편집

**설계 요지**: Finviz 스타일 히트맵 + 지표별 **weight / support_direction** 인라인 편집.

**현재 상태**:
- 백엔드 `DashboardView`가 `heatmap` 객체(rows/cols/cells) 응답에 포함(`monitoring_views.py:196-204, 221-225`) — **이미 전송 중인데 프론트에서 안 쓰고 있음**.
- `ThesisIndicator.weight`(`indicator.py:64`), `support_direction`(`indicator.py:49`) 모델 필드 존재.
- 프론트에 히트맵 컴포넌트 부재.
- 지표 편집은 `indicators/page.tsx`에서 토글/삭제만 가능 (weight, direction 인라인 편집 없음).

**갭**:
- [ ] `HeatmapGrid.tsx` 또는 유사 컴포넌트
- [ ] 지표 weight 슬라이더 + direction 토글 UI
- [ ] `PATCH /indicators/<id>/` 호출 (backend ViewSet은 ModelViewSet이므로 즉시 사용 가능)

### 3.3 FE-PR-9 — 히스토리 탭

**설계 요지**: `ThesisSnapshot` 시계열을 recharts 라인 차트 + 스냅샷 타임라인.

**현재 상태**:
- `ThesisSnapshot`은 일일 생성 중(`tasks/eod_pipeline.py:create_snapshots_and_alerts`).
- 백엔드: 가설별 스냅샷 리스트 API **부재**. `thesis/urls.py:21-46` 검토 결과, snapshot list 엔드포인트 없음. `DashboardView`는 `thesis.snapshots.first()` (최신 1건) 만 노출.
- 프론트: 히스토리 라우트/컴포넌트 부재.
- `IndicatorRow.tsx`가 readings API로 지표별 차트는 보여주지만, **가설 전체 점수의 시계열**은 어디에도 없음.

**갭**:
- [ ] 백엔드: `GET /{thesis_id}/snapshots/?days=N` 추가
- [ ] 프론트: `(history)/page.tsx` 라우트
- [ ] 프론트: overall_score 시계열 LineChart
- [ ] 프론트: notable_changes 타임라인 (날짜 + 변화 카드)

### 3.4 FE-PR-10 — 마감 아카이브 + 요약 (ValidityMatrix)

**설계 요지**: 마감 가설 목록 + 가설별 ValidityMatrix(2×2) 시각화.

**현재 상태**:
- 백엔드: `ThesisViewSet.get_queryset()`이 `?status=closed` 필터 지원(`thesis/views/thesis_views.py:45-50`) — 아카이브 목록 API는 사실상 사용 가능.
- 백엔드: `ValidityRecord` 모델 + close 시 자동 생성(`thesis_views.py:86-103`). thesis_correct/indicator_aligned 매트릭스 데이터 풍부.
- 백엔드: ValidityMatrix 집계 전용 엔드포인트 **부재**.
- 프론트: `archive/` 라우트 없음, `ValidityMatrix.tsx` 컴포넌트 없음.

**갭**:
- [ ] 백엔드: `GET /{thesis_id}/validity-matrix/` 또는 thesis detail에 임베드
- [ ] 프론트: `archive/page.tsx` (`?status=closed` 호출)
- [ ] 프론트: `ValidityMatrix.tsx` (2×2 매트릭스 — aligned×correct)
- [ ] 프론트: 마감 가설 카드 — outcome 배지 + 마감일 + 누적일 + 적중 여부

### 3.5 FE-PR-11 — 투자자 DNA 프로필

**설계 요지**: AccuracyRing + CategoryChart + 전제 카테고리 분포 + AI 수락률.

**현재 상태**:
- 백엔드: `InvestorDNA` 모델 + close 시 자동 갱신(`_update_investor_dna`, `thesis_views.py:295-336`). `accuracy_rate`, `ai_accept_rate`, `top_down_ratio` property 완비.
- 백엔드: DNA를 노출하는 **API 엔드포인트 부재**. URL 라우트 검토 결과 `/dna/`, `/profile/` 라우트 없음.
- 프론트: 프로필 화면 자체 부재.

**갭**:
- [ ] 백엔드: `GET /api/v1/thesis/dna/` 또는 `users/me/dna/` 엔드포인트
- [ ] 백엔드: DNA Serializer (DRF에 ModelSerializer/Serializer 부재)
- [ ] 프론트: 프로필 라우트 (`(list)/profile/page.tsx` 등)
- [ ] 프론트: `AccuracyRing.tsx` (적중률 원형 진행률)
- [ ] 프론트: `CategoryChart.tsx` (premise_category_counts 분포)
- [ ] 프론트: 지표 유형 편향 시각화 + 역제안 안내 (Phase 2 슬라이더 도입 전 준비 단계)

### 3.6 Phase 3-α 잔존 정리 작업

| 항목 | 현재 상태 | 처리 권고 |
|---|---|---|
| `RealValueIndicatorCard.tsx` 고아 | 파일 존재, 사용처 0 (테스트 파일만 import) | 통합 흡수 결정 시 파일 삭제 또는 page.tsx에 wiring |
| `ChartToggleButton.tsx` 고아 | 사용처 0 | 동상 |
| `PeriodSelector.tsx` 고아 | 사용처 0 | 동상 |
| `IndividualMiniCharts.tsx` 고아 | 사용처 0 | 동상 |
| `MoonPhase.tsx` (common/) | dashboard 미사용, 다른 곳 import 여부 미검증 | grep 후 결정 (phase3-α §2 미이행 체크리스트) |
| `_infer_unit()` fallback | `monitoring_views.py:346` 잔존 | 의도된 fallback (phase3-α 명세대로). 유지 |

---

## 4. 백엔드 갭 (수학 모델/로드맵)

### 4.1 Phase 2 (DNA 슬라이더 + 유효성 활성화) — 0% (C)

| 항목 | 위치 | 상태 |
|---|---|---|
| `ValidityScore` 모델 | `thesis/models/learning.py` | **부재** |
| ValidityRecord → ValidityScore 주 1회 집계 태스크 | `thesis/tasks/` | **부재** |
| `indicator_matcher`에 validity_boost 반영 | `services/indicator_matcher.py` | **부재** (현재 키워드 룰만) |
| DNA 적합도 슬라이더 (`personalization_weight`) 활용 | — | 필드만 있음, 로직 부재 |
| 역제안 (Contrarian Nudge) | — | 부재 |
| 상관계수 자동 할인 (60일 \|ρ\|≥0.9 → 1/√k) | math_model §10 | **부재** |
| Adaptive Decay/Window | math_model §11 | **부재** |
| Sustained Extreme | math_model §12 | **부재** |

### 4.2 Phase 3 (합성 에이전트 + Online LR) — 0% (C)

- `SyntheticBootstrapper` 부재 (integrated_roadmap §3.1)
- `ValidityRecord.is_synthetic` 필드 부재 → 합성/실제 블렌딩 불가
- Online Logistic Regression `ThesisWeightLearner` 부재

### 4.3 Phase 4 (벡터 스코어링) — 0% (C) — 예정대로 보류

---

## 5. 권고

### 5.1 즉시 결정 필요

1. **Phase 3-α PR-8/PR-9 고아 컴포넌트 처리**: IndicatorRow 통합 작성이 의도였다면 명세 갱신 + 고아 4개 삭제. 명세대로 wiring이 의도였다면 page.tsx 교체. — **현 상태(파일 존재 + 미사용)가 가장 나쁨**.
2. **MoonPhase 잔존 삭제 여부**: `grep -r MoonPhase frontend/` 한 줄로 결정 가능.

### 5.2 Phase 3-β 우선순위 제안 (백엔드 데이터는 이미 있음)

낮은 백엔드 추가비용 순:

1. **FE-PR-10 (마감 아카이브)** — `?status=closed` 이미 지원, ValidityRecord도 있음. ValidityMatrix 집계만 추가하면 즉시 가능.
2. **FE-PR-11 (DNA 프로필)** — InvestorDNA 데이터 완비, 단순 GET 엔드포인트 1개 + Serializer만 추가.
3. **FE-PR-9 (히스토리)** — ThesisSnapshot 시계열 GET 엔드포인트 1개 추가 필요.
4. **FE-PR-7 (탭 구조 + 전제 CRUD)** — 백엔드 100% 준비, 순수 프론트 작업.
5. **FE-PR-8 (히트맵 + 지표 편집)** — heatmap 데이터 이미 송신 중. 가장 UI 비중 큼.

### 5.3 백엔드 Phase 2 진입 신호

`ValidityRecord.objects.count() >= 10` 도달 시 Phase 2 진입 권고(integrated_roadmap §2 전제조건). 현재 카운트 미확인.

---

## 6. 변경 없는 항목 (참고)

- `KeywordCache`, `PopularThesisCache`, `ThesisFollow` — 설계대로 구현, 사용 빈도 미파악.
- `feature_flags.py` — 별도 분석 미수행.
- 테스트(`frontend/__tests__/thesis/RealValueIndicatorCard.test.tsx`) — 고아 컴포넌트에 대한 테스트만 잔존, 다른 dashboard 컴포넌트 테스트 커버리지 미파악.

---

## 부록 A — Phase 3 두 갈래의 정합성 문제

문서 시간선:
- 2026-02-27: `thesis_control_design.md` (Phase 2 기준 설계)
- 2026-03-14~16: FE-PR-5/6 완료 → `Phase2_completion_summary.md` 작성 → **§8에서 "Phase 3" = 깊이/회고/프로필 (FE-PR-7~11)** 으로 정의
- 2026-03-18: `thesis_control_phase3_frontend_redesign.md` 작성 → **"Phase 3" = 대시보드 리디자인 (PR-7~10)** 으로 재정의
- 두 문서가 같은 "Phase 3" 라벨로 충돌하며, 후자가 실제로 부분 구현됨.

**권고**: 명명을 분리하거나 후자를 "Phase 2.5 — 대시보드 리디자인"으로 리네이밍. 그렇지 않으면 다음 세션에서도 동일한 혼동 재발.
