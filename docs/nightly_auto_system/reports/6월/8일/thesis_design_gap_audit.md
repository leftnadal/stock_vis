# Thesis Control 설계 갭 감사

> 생성일: 2026-06-08 (야간 자동 감사)
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` (백엔드) + `frontend/components/thesis/` (프론트엔드)
> 성격: **읽기 전용 감사** — 코드 수정 없음
> 분류 체계: **(A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체**

---

## ⚠️ 핵심 발견: "Phase 3"가 두 개의 충돌하는 정의를 가짐

이 프로젝트에는 **PR 번호가 겹치는 서로 다른 "Phase 3" 계획이 2개** 존재한다. 이것이 추적성 혼란의 근원이다.

| | **정의 A — 대시보드 실제값 리디자인** | **정의 B — 깊이+회고+프로필** |
|---|---|---|
| 출처 문서 | `plan/thesis_control_phase3_frontend_redesign.md` (2026-03-18) | `frontend/task_done/Phase2_completion_summary.md` §8 (2026-03-16) |
| PR 번호 | PR-7 ~ PR-10 | FE-PR-7 ~ FE-PR-11 |
| 핵심 | 내부 점수 숨기고 실세계 값(환율/VIX/지수) 노출 | 3탭 구조 + 히트맵 + 히스토리 + 마감 아카이브 + 투자자 DNA 화면 |
| **구현 상태** | **(A) 완전 구현** | **(D) 폐기/대체 — 미착수** |

**판정**: CLAUDE.md "진행 중" 항목의 `Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)`는 **정의 B**를 가리키지만, 실제 코드베이스에는 **정의 A(대시보드 실제값 리디자인)**가 구현되어 있다. 03-16에 세운 정의 B 계획이 03-18 리디자인 문서로 **방향 전환**되면서 같은 PR 번호대(7~)를 재사용했고, 정의 B는 착수되지 않았다.

> **권고**: CLAUDE.md 진행 상태 표기를 실제와 일치시킬 것. "FE-PR-7~11 (깊이+회고+프로필)"은 **보류/폐기**, "대시보드 실제값 리디자인(redesign PR-7~10)"은 **완료**로 정정.

---

## 요약 (Phase별 구현률)

### 백엔드 통합 로드맵 (`plan/thesis_control_integrated_roadmap.md`)

| Phase | 범위 | 구현률 | 분류 |
|-------|------|--------|------|
| **Phase 1 (MVP)** | 관제 엔진 v2.3.2 + 이벤트 수집 + ValidityRecord + InvestorDNA 골격 | ~90% | **A** |
| **Phase 2** | ValidityScore 활성화 + DNA 슬라이더 + 역제안 + 상관 할인 | ~0% | **C** |
| **Phase 3 (백엔드)** | 합성 에이전트 부트스트래핑 + Online LR + 블렌딩 | 0% | **C** |
| **Phase 4** | 벡터 스코어링 (DNA/유효성 벡터화 + 코사인 유사도) | 0% | **C** |

### 프론트엔드 대시보드 리디자인 (정의 A, `plan/thesis_control_phase3_frontend_redesign.md`)

| PR | 범위 | 구현률 | 분류 |
|----|------|--------|------|
| **PR-7** | 백엔드: display_unit + IndicatorReadingsView + readings 경로 | 100% | **A** |
| **PR-8** | 프론트: 실제값 카드 + AI 분석 + 오늘의 변화 | 100% | **A** |
| **PR-9** | 프론트: 미니차트 + 기간 선택 + 레거시 정리(삭제 5종) | 100% | **A** |
| **PR-10** | 백엔드: AI 요약 파이프라인(Gemini) + notable_changes 연동 | ~85% | **B** |

### 프론트엔드 깊이+회고+프로필 (정의 B, `Phase2_completion_summary.md` §8)

| PR | 범위 | 구현률 | 분류 |
|----|------|--------|------|
| **FE-PR-7** | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD UI | 0% | **D** |
| **FE-PR-8** | Finviz 스타일 히트맵 + weight/direction 편집 | 0% | **D** |
| **FE-PR-9** | 히스토리 탭 (라인 차트 + 스냅샷 타임라인) | 0% | **D** |
| **FE-PR-10** | 마감 아카이브 + ValidityMatrix | 0% | **D** |
| **FE-PR-11** | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | 0% | **D** |

---

## 문서별 상태 테이블

| 설계 문서 | 주제 | 대조 결과 | 분류 |
|-----------|------|-----------|------|
| `plan/thesis_control_design.md` | 전체 설계(수학 모델 + 모델 스키마) | 모델/Stage 엔진/스냅샷 구현됨 | A |
| `plan/thesis_control_math_model_final.md` | 수학 모델 v2.3.2 (Stage 0~3) | Stage 0~3 엔진 구현(`indicator_scorer`, `arrow_calculator`, `premise_aggregator`, `thesis_state_machine`, `data_validator`) | A |
| `plan/thesis_control_integrated_roadmap.md` | Phase 1~4 로드맵 | Phase 1=A, Phase 2~4=C (아래 상세) | 혼합 |
| `plan/thesis_control_phase3_frontend_redesign.md` | **정의 A** 대시보드 실제값 | PR-7/8/9=A, PR-10=B | A |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 대시보드 | `IndicatorRow`, `QuarterlySparkline` 구현됨 (설계와 일치) | A |
| `plan/talking_builder/llm_builder_plan.md` | LLM 대화형 빌더 | `thesis_builder.py`, `builder_state.py`, `builder_events.py` 구현 | A |
| `plan/talking_builder/thesis_builder_redesign_v2.md` | 빌더 리디자인 v2 | builder 컴포넌트 9종 구현 | A |
| `work_done/phase_a_llm_builder.md` | Phase A LLM 빌더 완료 보고 | 완료 보고서 (구현 일치) | A |
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 프론트 6개 PR | 6개 PR 전건 구현 + 보고서 존재 | A |
| `Phase2_completion_summary.md` §8 | **정의 B** 깊이+회고+프로필 계획 | FE-PR-7~11 미착수, task_done 보고서 부재 | D |

### 백엔드 코드 ↔ 설계 모델 대조 (`thesis/models/`)

| 설계 모델 (로드맵) | 코드 위치 | 분류 |
|--------------------|-----------|------|
| `Thesis`, `ThesisPremise` | `models/thesis.py` | A |
| `ThesisIndicator`, `IndicatorReading` | `models/indicator.py` (`display_unit` 포함 ✅) | A |
| `ThesisSnapshot`, `ThesisAlert` | `models/monitoring.py` (`ai_summary`, `notable_changes` 필드 존재 ✅) | A |
| `HypothesisEvent` (Phase 1) | `models/learning.py:7` ✅ | A |
| `ValidityRecord` (Phase 1) | `models/learning.py:55` ✅ | A |
| `InvestorDNA` (Phase 1) | `models/learning.py:97` ✅ | A |
| `ValidityScore` (Phase 2) | **부재** ❌ | C |
| `SyntheticBootstrapper` / `ThesisWeightLearner` (Phase 3) | **부재** ❌ | C |
| DNA 벡터 / 유효성 벡터 (Phase 4) | **부재** ❌ | C |
| `ThesisFollow`, `PopularThesisCache`, `KeywordCache` | `models/community.py`, `models/keyword.py` (설계 외 추가 구현) | A+ |

---

## Phase 3 미구현 항목 상세

### 1. 정의 B (깊이+회고+프로필 FE-PR-7~11) — 전건 미착수 [D]

코드베이스 전수 검색 결과 정의 B의 어떤 산출물도 존재하지 않는다.

| FE-PR | 설계 항목 | 코드 증거 | 판정 |
|-------|-----------|-----------|------|
| FE-PR-7 | 대시보드 3탭(관제/상세/히스토리) | `app/thesis/[thesisId]/` 단일 page.tsx, 탭 구조 없음 | 미구현 |
| FE-PR-7 | 전제 CRUD UI | `ThesisPremiseViewSet`(백엔드)는 존재하나 전용 편집 화면 없음 | 부분(백엔드만) |
| FE-PR-8 | Finviz 히트맵 + weight/direction 편집 | `components/thesis/` 내 히트맵 0건 (screener/coach 히트맵은 무관) | 미구현 |
| FE-PR-9 | 히스토리 탭 (스냅샷 타임라인) | `ThesisSnapshot` 데이터는 쌓이나 타임라인 UI 없음 | 미구현 |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix | 마감(`close/page.tsx`)은 있으나 아카이브 목록/매트릭스 화면 없음 | 미구현 |
| FE-PR-11 | 투자자 DNA 프로필 화면 | `InvestorDNA` 모델/집계는 있으나 **노출 API·화면 모두 없음** | 미구현 |

> **주의**: 정의 B의 데이터 토대(`InvestorDNA`, `ValidityRecord`, `ThesisSnapshot`)는 백엔드에 이미 존재한다. 즉 **백엔드 데이터는 쌓이는데 프론트 노출이 없는** 상태 — 정의 B는 "데이터 시각화 레이어"만 미구현. 재개 시 모델 변경 없이 화면+조회 API만 추가하면 된다.

### 2. 백엔드 로드맵 Phase 2 — 미구현 [C]

| 설계 항목 | 코드 증거 | 판정 |
|-----------|-----------|------|
| `ValidityScore` 집계 테이블 | grep 0건 — 모델 부재 | 미구현 |
| 주 1회 ValidityRecord→ValidityScore 집계 Celery | 해당 태스크 없음 | 미구현 |
| 지표 추천에 유효성 점수 반영 (`indicator_matcher` 개선) | `indicator_matcher.py`는 키워드 룰 기반만 | 미구현 |
| DNA 적합도 슬라이더 (`personalization_weight` 활용) | 필드는 모델에 존재하나 로직 없음 | 미구현(필드만) |
| 역제안 (Contrarian Nudge) | grep 0건 | 미구현 |
| 상관계수 자동 할인 / Adaptive Decay / Sustained Extreme / 뉴스 센티먼트 | grep 0건 | 미구현 |

### 3. 백엔드 로드맵 Phase 3(합성)·Phase 4(벡터) — 미구현 [C]

합성 에이전트 부트스트래핑, Online Logistic Regression, 합성/실제 블렌딩, DNA/유효성 벡터화, 코사인 유사도 추천 — **전건 미착수**. 전제조건(Phase 2 ValidityScore)이 없어 착수 불가 상태.

---

## 구현 완료 항목 하이라이트 (정의 A + Phase 1)

추적성을 위해 **실제로 완성된 것**을 명시한다.

### Phase 1 백엔드 (이벤트/유효성/DNA) — [A]
- `HypothesisEvent` 기록 코드가 **실제 비즈니스 로직에 다수 삽입됨**: `thesis_views.py`(8건), `thesis_builder.py`(5건) — 설계 1.2 "1줄씩 삽입" 준수 ✅
- 마감 시 `ValidityRecord` 생성 + `_compute_validity_score()` 2×2 매트릭스 (`thesis_views.py:99, 284`) ✅
- `_update_investor_dna()` — 마감 시 `premise_category_counts`/`indicator_type_counts` 집계 (`thesis_views.py:302`) ✅

### 대시보드 실제값 리디자인 (정의 A) — [A]
- **PR-7**: `ThesisIndicator.display_unit` 필드(`indicator.py:73`), `IndicatorReadingsView`(`monitoring_views.py:260`), readings URL(`urls.py:37`) ✅
- **PR-8**: `RealValueIndicatorCard`, `AISummarySection`, `NotableChangesSection` ✅
- **PR-9**: `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts` ✅ + 레거시 삭제 5종(`OverallMoon`, `DashboardIndicatorCard`, `RecentChange`, `CombinedNormalizedChart`, `dashboardStore`) **전건 제거 완료** ✅
- 설계 외 추가: `IndicatorRow`, `QuarterlySparkline`, `DashboardPageHeader` (분기 지표 대시보드 계획 기반)

### PR-10 AI 파이프라인 — [B] (부분/편차)
- `generate_thesis_summaries` Gemini 2.5 Flash **동기 호출** (Bug #8 회피 준수, `tasks/summary.py:55`) ✅
- Celery Beat 등록됨 (`config/celery.py:680`) ✅
- **설계 편차**: redesign 문서 §7-2는 `notable_changes`를 **alert_engine 이벤트(direction_flip/sharp_move/extreme_volatility) 기반**으로 변환하도록 명시했으나, 실제 `snapshot_builder.py:108`은 **"이전 스냅샷 대비 |score 변화| ≥ 0.3"** 기반으로 구현됨. 결과적으로 채워지긴 하나 설계 의도(실제 alert 재활용)와 산출 로직이 다름 → **검증 권고**.

---

## 권고 사항 (수정 없음 — 후속 결정용)

1. **CLAUDE.md 정정** [높음]: "진행 중" 항목의 `Thesis Control Phase 3 (깊이+회고+프로필 FE-PR-7~11)` → 실제는 미착수(보류). 대신 "대시보드 실제값 리디자인(redesign PR-7~10) 완료"를 "완료" 섹션에 반영.
2. **PR 번호 충돌 해소** [중간]: 정의 A(PR-7~10)와 정의 B(FE-PR-7~11)가 같은 번호대를 점유. 정의 B를 재개한다면 FE-PR-12~ 로 재번호 부여 권고.
3. **PR-10 notable_changes 로직 검증** [중간]: 설계(alert 기반) vs 구현(score 변화 0.3 기반) 편차가 의도된 단순화인지 확인. 의도면 redesign 문서 §7-2 갱신, 아니면 alert_engine 연동 보강.
4. **InvestorDNA 노출 경로 부재** [낮음]: 백엔드 DNA 데이터는 마감마다 갱신되는데 조회 API·화면이 없어 "쌓이기만 하는 데이터". 정의 B FE-PR-11 또는 별도 경량 프로필 화면으로 가치 실현 가능.
5. **Phase 2 ValidityScore 부재** [낮음]: Phase 3 백엔드(합성)·Phase 4(벡터)의 전제조건. 로드맵상 "마감 10건+ 축적" 후 착수 예정이므로 데이터 축적 현황 확인 후 판단.

---

## 부록: 검증에 사용한 증거 명령

```
grep "^class " thesis/models/*.py                  # 모델 12종 확인
grep "HypothesisEvent.objects.create" thesis/      # 이벤트 삽입 13+건
grep "display_unit" thesis/models/indicator.py     # PR-7 필드 (line 73)
grep "IndicatorReadingsView" thesis/urls.py        # PR-7 라우트 (line 37)
grep "_generate_via_gemini" thesis/tasks/summary.py # PR-10 Gemini 동기
grep "ValidityScore" thesis/ --include=*.py        # 0건 → Phase 2 부재
grep -rl "OverallMoon|RecentChange|..." frontend/  # 삭제 5종 0건 → PR-9 정리 완료
ls frontend/components/thesis/dashboard/           # 정의 A 컴포넌트 10종
ls docs/thesis_control/frontend/task_done/         # FE-PR-1~6만 (7~11 부재)
```
