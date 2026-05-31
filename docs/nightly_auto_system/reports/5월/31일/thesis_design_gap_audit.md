# Thesis Control 설계 갭 감사

> 감사일: 2026-06-01
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` 백엔드 + `frontend/components/thesis/` + `frontend/app/thesis/` 구현
> 성격: **읽기 전용 감사** (코드 수정 없음)
> 분류 기준: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## ⚠️ 핵심 발견: "Phase 3" 설계가 둘로 갈라져 있음

감사 중 **동일한 "Phase 3"라는 이름의 서로 다른 두 설계 문서**가 존재함을 확인했다. 이것이 갭 분석의 가장 중요한 맥락이다.

| 구분 | 문서 | 작성일 | Phase 3 정의 | 상태 |
|------|------|--------|-------------|------|
| **원안** | `frontend/task_done/Phase2_completion_summary.md` §8 | 2026-03-16 | **깊이 + 회고 + 프로필** (FE-PR-7~11): 탭구조 / 히트맵 / 히스토리 / 마감아카이브 / 투자자 DNA | **사실상 폐기 (D)** |
| **개정안** | `plan/thesis_control_phase3_frontend_redesign.md` (v1.0 FINAL) | 2026-03-18 | **대시보드 실제값 리디자인** (PR-7~10): 실세계 숫자 카드 / AI 분석 / 오늘의 변화 / 미니차트 / AI 파이프라인 | **대부분 구현 (A/B)** |

> 작성일 2일 차이(03-16 → 03-18)로 **원안 FE-PR-7~11이 개정안 PR-7~10으로 대체**된 것으로 판단된다. CLAUDE.md / MEMORY.md가 여전히 "Phase 3 (깊이+회고+프로필: FE-PR-7~11)"을 "진행 중"으로 표기하고 있어 문서 간 불일치가 존재한다.

추가로 `plan/thesis_control_integrated_roadmap.md`는 **백엔드 학습 레이어**의 Phase 1~4(이벤트수집 → ValidityScore → 합성에이전트 → 벡터스코어링)를 별도 정의한다. 이 "Phase 3"(합성 에이전트)는 또 다른 축이다.

→ **"Phase 3"는 최소 3개 축으로 분기됨**: ① FE 원안(폐기), ② FE 개정안(구현됨), ③ BE 학습 로드맵(Phase 1만 구현).

---

## 1. 요약 (축별 / Phase별 구현률)

### 축 ②: FE 대시보드 리디자인 개정안 (phase3_frontend_redesign, PR-7~10)

| PR | 범위 | 구현률 | 분류 |
|----|------|--------|------|
| PR-7 | 백엔드 (display_unit, raw_value, IndicatorReadingsView) | **100%** | A |
| PR-8 | 프론트 (실제값 카드, AI분석, 오늘의 변화) | **~85%** | B |
| PR-9 | 프론트 (미니차트, 기간선택, 정리) | **~50%** | B |
| PR-10 | 백엔드 AI 파이프라인 (ai_summary, notable_changes) | **~90%** | A/B |
| **소계** | | **~80%** | **대체로 완료** |

### 축 ①: FE 원안 "깊이+회고+프로필" (FE-PR-7~11)

| PR | 범위 | 구현률 | 분류 |
|----|------|--------|------|
| FE-PR-7 | 탭구조(관제/상세/히스토리) + 전제 CRUD | ~10% (BE만) | C/D |
| FE-PR-8 | 히트맵 + 지표 weight/direction 편집 | 0% | C/D |
| FE-PR-9 | 히스토리 탭 (스냅샷 타임라인) | 0% | C/D |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix | 0% | C/D |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing 등) | ~5% (BE 집계만) | C/D |
| **소계** | | **~3%** | **사실상 폐기** |

### 축 ③: BE 학습 레이어 (integrated_roadmap, Phase 1~4)

| Phase | 범위 | 구현률 | 분류 |
|-------|------|--------|------|
| Phase 1 | HypothesisEvent + ValidityRecord + InvestorDNA (기록만) | **100%** | A |
| Phase 2 | ValidityScore 집계 + DNA 슬라이더 + 역제안 | **0%** | C |
| Phase 3 | 합성 에이전트(SyntheticBootstrapper) + Online LR + 블렌딩 | **0%** | C |
| Phase 4 | 벡터 스코어링 (DNA 벡터화, 코사인 유사도) | **0%** | C |

---

## 2. 문서별 상태 테이블

| 설계 문서 | 핵심 내용 | 구현 상태 | 분류 |
|-----------|----------|-----------|------|
| `plan/thesis_control_design.md` | 전체 설계 (모델/Stage 0-3/스냅샷) | 관제 엔진·모델 구현됨 | A |
| `plan/thesis_control_math_model_final.md` | 수학 모델 v2.3.2 (Stage 0-3) | 구현됨 (Phase 1 범위) | A |
| `plan/thesis_control_implementation_guide.md` | 구현 가이드 | 반영됨 | A |
| `plan/thesis_control_integrated_roadmap.md` | BE 학습 Phase 1~4 | Phase 1만 (이하 §4) | B |
| `plan/thesis_control_phase3_frontend_redesign.md` | **FE 개정안 PR-7~10** | 대부분 구현 (§3) | A/B |
| `frontend/task_done/Phase2_completion_summary.md` §8 | **FE 원안 FE-PR-7~11** | 사실상 폐기 (§5) | D |
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 핵심 루프 6개 PR | 완료 (라우트·컴포넌트 확인됨) | A |
| `plan/talking_builder/*` (redesign v2, 5단계 build plan) | LLM 빌더 리디자인 | 별도 트랙 (이번 감사 범위 외, 빌더 컴포넌트 존재 확인) | — |

---

## 3. 축 ②: FE 개정안 PR-7~10 상세 (대체로 구현됨)

### PR-7 백엔드 확장 — (A) 완전 구현

| 설계 항목 | 구현 위치 | 상태 |
|-----------|-----------|------|
| `ThesisIndicator.display_unit` 필드 | migration `0004_add_display_unit` | ✅ A |
| display_unit 데이터 마이그레이션 | migration `0005_populate_display_unit` | ✅ A |
| DashboardView raw_value/previous/change_pct | `thesis/views/monitoring_views.py:94-165` | ✅ A |
| `_infer_unit()` fallback | `monitoring_views.py:352` | ✅ A |
| thesis 응답 ai_summary/notable_changes | `monitoring_views.py:216-217` | ✅ A |
| `IndicatorReadingsView` + URL 등록 | `monitoring_views.py:260` / `urls.py:36-40` | ✅ A |

> **추가 진화**: 설계에 없던 분기지표 처리(`RATIO_METRICS` % 변환, `raw_value_asof`)가 `monitoring_views.py:130-165`에 추가됨. 설계 대비 상향 구현.

### PR-8 프론트 실제값 카드 + AI 분석 — (B) 부분 구현

| 설계 컴포넌트 | 구현 | 페이지 연결 | 상태 |
|--------------|------|------------|------|
| `AISummarySection.tsx` | 존재 | ✅ `page.tsx:75` 사용 | A |
| `NotableChangesSection.tsx` | 존재 | ✅ `page.tsx:81` 사용 | A |
| `RealValueIndicatorCard.tsx` | 존재 + 테스트 존재 | ❌ **page.tsx에서 미사용** | **D(대체)** |

> **갭**: 설계는 지표 카드로 `RealValueIndicatorCard`를 명시했으나, 실제 대시보드(`app/thesis/[thesisId]/page.tsx:115`)는 **`IndicatorRow`**를 사용한다. `RealValueIndicatorCard`는 컴포넌트·테스트만 남고 화면에 연결되지 않은 **고아(orphan) 컴포넌트**다.
> 이는 MEMORY.md `feedback_dashboard_layout`(1xN 세로 나열 + 지표별 토글 차트 + "전분기대비" 라벨) 방향으로 **추가 진화**한 결과로 보인다. 즉 설계 대체이지 누락은 아님.

### PR-9 미니차트 + 기간선택 + 정리 — (B) 부분 구현 (대체)

| 설계 컴포넌트 | 구현 | 페이지 연결 | 상태 |
|--------------|------|------------|------|
| `ChartToggleButton.tsx` | 존재 | ❌ **page.tsx에서 미사용** | D(대체) |
| `PeriodSelector.tsx` | 존재 | ❌ **page.tsx에서 미사용** | D(대체) |
| `IndividualMiniCharts.tsx` | 존재 | ❌ **page.tsx에서 미사용** | D(대체) |
| `OverallMoon.tsx` 삭제 | 디렉터리에 없음 | — | ✅ A |
| `DashboardIndicatorCard.tsx` 삭제 | 디렉터리에 없음 | — | ✅ A |
| `RecentChange.tsx` 삭제 | 디렉터리에 없음 | — | ✅ A |

> **갭**: PR-9의 차트 토글 3종(ChartToggleButton/PeriodSelector/IndividualMiniCharts)이 모두 **page.tsx에 연결되지 않은 고아 컴포넌트**다. 대신 차트는 `IndicatorRow.tsx`가 `QuarterlySparkline`을 **지표별 인라인 토글**로 흡수했다(MEMORY.md `feedback_dashboard_layout` 방향).
> 설계의 "전역 차트 토글 + 통합 기간선택" 모델이 "지표별 개별 토글 차트" 모델로 **대체**됨. 삭제 대상 3종은 설계대로 정상 제거됨.

### PR-10 AI 파이프라인 — (A/B) 구현 (방식 변경)

| 설계 항목 | 구현 | 상태 |
|-----------|------|------|
| `generate_thesis_summaries` AI 요약 task | `thesis/tasks/summary.py` (Gemini 2.5 Flash 동기, 멱등) | ✅ A |
| `notable_changes` 생성 | `thesis/services/snapshot_builder.py:108-160` | ⚠️ B(방식 변경) |

> **갭(경미)**: 설계는 notable_changes를 **alert_engine 이벤트(direction_flip/sharp_move 등) 변환**으로 정의했으나, 구현은 **이전 스냅샷 대비 \|score 변화\| ≥ 0.3** 기준으로 생성한다(`snapshot_builder.py:31, 108`). 결과는 동일 필드를 채우지만 감지 로직이 다름. 기능상 문제 없으나 설계-구현 정의 불일치.

---

## 4. 축 ③: BE 학습 레이어 (integrated_roadmap) 상세

### Phase 1 — (A) 완전 구현

| 모델 | 구현 위치 | 비고 |
|------|-----------|------|
| `HypothesisEvent` | `thesis/models/learning.py:7` | 13개 event_type + 3 인덱스 ✅ |
| `ValidityRecord` | `learning.py:55` | 2×2 매트릭스 점수 ✅ |
| `InvestorDNA` | `learning.py:97` | accuracy_rate/ai_accept_rate/top_down_ratio property ✅ |

**이벤트 emit 실제 연결 확인** (설계 §1.2 "1줄씩 삽입"이 실제로 됨):
- `thesis/services/thesis_builder.py`: 5곳 (`659, 671, 681, 735, 1203`)
- `thesis/views/thesis_views.py`: 9곳 (`62, 114, 127, 173, 187, 222, 237, 266` 등)
- 마감 시 `ValidityRecord.objects.create` (`thesis_views.py:99`) + `_update_investor_dna()` (`thesis_views.py:302-343`) ✅

### Phase 2 — (C) 미구현

| 설계 항목 | 상태 |
|-----------|------|
| `ValidityScore` 모델 (집계 테이블) | ❌ 모델/마이그레이션 없음 (`grep` 결과 0건) |
| ValidityRecord → ValidityScore 주1회 집계 Celery | ❌ 없음 |
| 지표 추천 유효성 부스트 (indicator_matcher) | ❌ 없음 |
| DNA 적합도 슬라이더 (personalization_weight) | ⚠️ 필드만 존재(`learning.py:124`), 로직 없음 |
| 역제안(Contrarian Nudge) | ❌ 없음 |
| 상관계수 할인 / Adaptive Decay / Sustained Extreme / 뉴스 센티먼트 | ❌ 미확인(별도 검증 필요) |

### Phase 3 (BE 합성 에이전트) — (C) 미구현

| 설계 항목 | 상태 |
|-----------|------|
| `SyntheticBootstrapper` (페르소나 시뮬레이션) | ❌ 없음 |
| `ValidityRecord.is_synthetic` 필드 | ❌ 없음 (`grep` 0건) |
| Online Logistic Regression (가중치 학습) | ❌ 없음 |
| 합성/실제 데이터 블렌딩 | ❌ 없음 |

### Phase 4 (벡터 스코어링) — (C) 미구현

DNA 벡터화 / 유효성 벡터 / 코사인 유사도 / 사용자 유사도 모두 ❌.

---

## 5. Phase 3 미구현 항목 상세 (원안 FE-PR-7~11 = "깊이+회고+프로필")

> 사용자가 가장 궁금해한 축. **원안 FE-PR-7~11은 거의 전부 미구현(C)이며, 개정안(§3)으로 대체(D)된 것으로 판단**된다. 라우트는 6개(`(list)`, `new`, `alerts`, `[thesisId]`, `indicators`, `close`)만 존재하고, 탭/히스토리/아카이브/프로필 라우트는 없다.

### FE-PR-7: 대시보드 탭 구조 + 상세 탭 — (C) 미구현 / (D) 대체

- **설계**: 3탭(관제 / 상세 / 히스토리) + 전제 CRUD UI
- **현황**:
  - 탭 구조 ❌ — `app/thesis/[thesisId]/page.tsx`는 단일 스크롤 화면, 탭 컴포넌트(`TabBar`/`activeTab`) 없음.
  - 전제 CRUD — **백엔드만 존재**(`ThesisPremiseViewSet`, `urls.py:47`), **프론트 편집 UI 없음**.
- **분류**: C (탭 UI), 전제 CRUD는 BE만 → B

### FE-PR-8: 히트맵 + 지표 상세 편집 — (C) 미구현

- **설계**: Finviz 스타일 히트맵 + 지표 weight/direction 편집
- **현황**: `frontend/components/thesis/`에 히트맵 컴포넌트 0건(`SectorHeatmap`은 screener 전용, thesis 무관). 지표 weight/direction 편집 UI 없음.
- **분류**: C

### FE-PR-9: 히스토리 탭 — (C) 미구현

- **설계**: recharts 라인 차트 + 스냅샷 타임라인
- **현황**: 히스토리 라우트/컴포넌트 없음. `ThesisSnapshot`은 BE에 일별 저장되나 시계열 조회 API/화면 미연결. (개정안 `IndicatorReadingsView`는 지표 단위 readings만 제공, 가설 스냅샷 타임라인 아님)
- **분류**: C

### FE-PR-10: 마감 아카이브 + 요약 — (C) 미구현

- **설계**: 마감 가설 목록 + ValidityMatrix 시각화
- **현황**: 마감 아카이브 라우트/컴포넌트 없음. `ValidityRecord`(2×2 매트릭스)는 BE에 기록되나 조회 API/화면 없음. ValidityMatrix 컴포넌트 0건.
- **분류**: C

### FE-PR-11: 투자자 DNA 프로필 — (C) 미구현

- **설계**: AccuracyRing + CategoryChart + 기술 부채 정리
- **현황**:
  - 프론트 DNA 컴포넌트(AccuracyRing/CategoryChart/InvestorDNA UI) **0건**.
  - 백엔드: `InvestorDNA` 모델 + `_update_investor_dna()` 집계는 동작하나, **DNA를 노출하는 API 엔드포인트가 `thesis/urls.py`에 없음** + DNA serializer 없음 → 프론트가 가져올 경로 자체가 없음.
- **분류**: C (BE 데이터 집계만 ~5%)

---

## 6. 결론 및 권고 (감사자 관점, 코드 변경 없음)

1. **문서 정합성 갭이 가장 큰 리스크.** CLAUDE.md / MEMORY.md가 "Phase 3 (깊이+회고+프로필: FE-PR-7~11) 진행 중"으로 표기하나, 실제로는 해당 원안이 `phase3_frontend_redesign.md`(실제값 리디자인)로 **대체되어 거의 구현 완료**된 상태다. 두 "Phase 3"를 문서상 명확히 분리(예: "Phase 3-원안(폐기)" / "Phase 3-리디자인(완료)")할 것을 권고.

2. **고아 컴포넌트 4종**: `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`가 구현·일부 테스트까지 되었으나 `page.tsx`에 연결되지 않음. `IndicatorRow` + `QuarterlySparkline`로 대체됨. 의도된 대체인지(→ 컴포넌트 제거) 확인 필요.

3. **BE 학습 레이어는 Phase 1에서 정지.** 이벤트/유효성/DNA "기록"은 완비됐으나(특허 청구항 독립항 1·2의 Phase 1 요소 충족), "활용"(ValidityScore 집계, DNA 슬라이더, 합성 에이전트)은 0%. 데이터는 쌓이고 있으므로 Phase 2 착수 시 활용 가능.

4. **"회고/프로필" 기능은 BE 데이터만 있고 노출 경로가 없음.** ValidityRecord·InvestorDNA를 읽는 API가 부재하여, 원안 FE-PR-10/11을 재개하려면 **API 엔드포인트부터** 필요하다.

---

### 부록: 분류 집계

| 분류 | 건수(대표 항목) |
|------|----------------|
| (A) 완전 구현 | PR-7 백엔드 6항목, PR-8 AI/변화 섹션 2종, PR-10 요약 task, BE Phase 1 모델 3종, FE-PR-1~6 |
| (B) 부분 구현 | PR-8 카드(대체), PR-9 차트(대체), PR-10 notable_changes(방식변경), 전제 CRUD(BE만), DNA(BE 집계만) |
| (C) 미구현 | BE Phase 2/3/4 전체, FE-PR-7 탭, FE-PR-8 히트맵, FE-PR-9 히스토리, FE-PR-10 아카이브, FE-PR-11 DNA UI |
| (D) 폐기·대체 | 원안 FE-PR-7~11 전체(→리디자인), RealValueIndicatorCard·차트토글 3종(→IndicatorRow), OverallMoon/DashboardIndicatorCard/RecentChange(정상 삭제) |
