# Thesis Control 설계 갭 감사

> 생성일: 2026-06-03
> 유형: 읽기 전용 감사 (코드 수정 없음)
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` (BE) + `frontend/components/thesis/` + `frontend/app/thesis/` (FE)
> 분류 기준: **(A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체**

---

## ⚠️ 0. 가장 중요한 발견 — "Phase 3"가 세 문서에서 서로 다른 의미

감사 과정에서 **"Phase 3"라는 용어가 3개 문서에서 충돌**하는 것을 확인했다. 이 모호성이 갭 분석의 핵심이다.

| 출처 문서 | "Phase 3" 정의 | PR 명명 | 실제 채택 여부 |
|----------|---------------|---------|--------------|
| `frontend/task_done/Phase2_completion_summary.md` §8 | **깊이 + 회고 + 프로필** (3탭 구조 / 히트맵 / 히스토리 / 마감 아카이브 / DNA 프로필 화면) | FE-PR-7 ~ FE-PR-11 | ❌ **폐기/미구현** |
| `plan/thesis_control_phase3_frontend_redesign.md` | **대시보드 리디자인** (실세계 값 카드 / AI 분석 / 미니차트) | PR-7(BE) ~ PR-10(BE) | ✅ **채택·구현됨** |
| `plan/thesis_control_integrated_roadmap.md` §3 | **합성 에이전트 + 자동학습** (SyntheticBootstrapper / Online LR) | (백엔드 로드맵) | ❌ 미착수 |

**결론**: 사용자 질문의 "Phase 3 (깊이 + 회고 + 프로필) FE-PR-7~11"은 `Phase2_completion_summary §8`의 계획을 가리킨다. 그러나 실제 개발은 그 계획을 따르지 않고, **별도로 작성된 `phase3_frontend_redesign.md`(실세계 값 단일 스크롤 대시보드)로 방향을 틀었다.** 따라서 §8의 FE-PR-7~11은 대부분 **(D) 폐기 또는 (C) 미구현** 상태이며, 그 자리를 리디자인 PR-7~10이 채웠다.

---

## 1. 요약 (Phase별 구현률)

### 1.1 프론트엔드 — §8 "깊이+회고+프로필" 계획 (FE-PR-7~11)

| PR | 계획 내용 | 상태 | 비고 |
|----|----------|------|------|
| FE-PR-7 | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD | **D (탭) / B (전제)** | 탭 구조 폐기 → 단일 스크롤. 전제 CRUD는 BE(`ThesisPremiseViewSet`) 존재, 대시보드 내 편집 UI 없음 |
| FE-PR-8 | Finviz 히트맵 + weight/direction 편집 | **C** | BE는 `heatmap` cells 제공하나 FE 히트맵 컴포넌트·편집 UI 없음 |
| FE-PR-9 | 히스토리 탭 + 스냅샷 타임라인 | **C** | BE 스냅샷 데이터 존재, FE 타임라인 화면 없음 (지표별 차트는 IndicatorRow로 대체) |
| FE-PR-10 | 마감 아카이브 목록 + ValidityMatrix | **C** | 마감 가설 목록·ValidityMatrix 컴포넌트 없음. 단건 마감 결과 화면만 존재 |
| FE-PR-11 | 투자자 DNA 프로필(AccuracyRing/CategoryChart) | **C** | BE `InvestorDNA` 완비, FE 프로필 화면/라우트/컴포넌트 전무 |

**§8 계획 구현률: 약 0~10%** (전제 CRUD 백엔드만 일부 충족)

### 1.2 프론트엔드+백엔드 — 리디자인 계획 (phase3_frontend_redesign PR-7~10) ★실제 채택

| PR | 계획 내용 | 상태 | 비고 |
|----|----------|------|------|
| PR-7 (BE) | display_unit 필드 + IndicatorReadingsView + raw_value/change_pct/ai_summary/notable_changes 응답 | **A** | 완전 구현 + **분기지표(quarterly) 확장**까지 추가 |
| PR-8 (FE) | 실세계 값 카드 + AISummarySection + NotableChangesSection | **A (구조 진화)** | `RealValueIndicatorCard` 대신 `IndicatorRow`로 통합 진화 |
| PR-9 (FE) | ChartToggleButton + PeriodSelector + IndividualMiniCharts | **D→A** | 3개 분리 컴포넌트는 **유령화(미사용)**, 기능은 `IndicatorRow` 내부 토글+AreaChart로 흡수 재구현 |
| PR-10 (BE) | generate_thesis_summaries(AI 요약) + notable_changes 연동 | **A / B** | task·Beat 등록 완료. 단 notable_changes **포맷 불일치**(아래 3.6) |

**리디자인 계획 구현률: 약 95%** (포맷 불일치 1건 제외 전건 동작)

### 1.3 백엔드 — 통합 로드맵 학습/개인화 레이어 (Phase 1~4)

| Phase | 계획 내용 | 상태 | 비고 |
|-------|----------|------|------|
| Phase 1 | HypothesisEvent · ValidityRecord · InvestorDNA 모델 + 기록/갱신 | **A** | 모델 3종 + 마감 시 생성/갱신 로직 완비 |
| Phase 2 | ValidityScore · DNA 슬라이더 · 역제안 · 유효성 기반 추천 | **C** | `ValidityScore` 모델 없음. `personalization_weight` 필드만 존재(미사용) |
| Phase 3 | SyntheticBootstrapper · Online LR · 합성/실제 블렌딩 | **C** | 미착수 |
| Phase 4 | DNA 벡터화 · 유효성 벡터 · 코사인 유사도 | **C** | 미착수 |

**학습 레이어 구현률: Phase 1 완료(100%), Phase 2~4 미착수(0%)**

---

## 2. 문서별 상태 테이블

| 설계 문서 | 핵심 내용 | 구현 매핑 | 분류 |
|----------|----------|----------|------|
| `plan/thesis_control_phase3_frontend_redesign.md` | 실세계 값 대시보드 리디자인 PR-7~10 | `monitoring_views.DashboardView`/`IndicatorReadingsView`, `IndicatorRow`, `AISummarySection`, `NotableChangesSection`, `tasks/summary.py` | **A** (대부분) |
| `plan/thesis_control_integrated_roadmap.md` | 관제엔진 + 학습/개인화 4-Phase | Phase 1: `models/learning.py`+`thesis_views.close`. Phase 2~4: 없음 | **B** (P1만) |
| `plan/thesis_control_design.md` | 전체 설계(수학모델 v2.3.2 + 화면) | 수학엔진(Stage0~3) 서비스 구현, 화면은 리디자인으로 대체 | **B** |
| `plan/thesis_control_math_model_final.md` | Stage 0~3 수학 모델 | `data_validator`/`indicator_scorer`/`premise_aggregator`/`thesis_state_machine`/`snapshot_builder` | **A** (코어) |
| `plan/thesis_control_implementation_guide.md` | 구현 가이드 | 3계층 서비스 구조 준수 | **A** |
| `plan/talking_builder/*` (대화형 빌더 재설계) | LLM 빌더 하드닝 + 키워드 | `thesis_builder.py`, `keyword_collectors/`, `keyword_cache.py` | **A** (work_done/phase_a_llm_builder.md 기록) |
| `frontend/task_done/FE-PR-1~6` | Phase 2 핵심 루프(목록→빌더→지표→대시보드→알림→마감) | `app/thesis/*` 6 라우트 + 컴포넌트 30+ | **A** |
| `frontend/task_done/Phase2_completion_summary.md` §8 | Phase 3 FE-PR-7~11 계획(깊이+회고+프로필) | 거의 없음 (리디자인으로 대체) | **C/D** |
| `thesis_control_user_experience.md` | UX 시나리오 | 핵심 루프 동작, 회고/프로필 미반영 | **B** |

---

## 3. Phase 3 미구현 항목 상세

> 아래는 **§8 "깊이+회고+프로필"(FE-PR-7~11)** 계획 기준 미구현 항목과, 리디자인 계획의 잔여 갭이다.

### 3.1 (C) 투자자 DNA 프로필 화면 — FE-PR-11

- **계획**: AccuracyRing(적중률 링) + CategoryChart(전제 카테고리 분포) + AI 수락률 등 DNA 시각화 화면.
- **백엔드 상태**: ✅ 완비. `thesis/models/learning.py:97 InvestorDNA` (total/closed/correct/incorrect, premise_category_counts, indicator_type_counts, ai_accept_rate, top_down_ratio property). 마감 시 `thesis/views/thesis_views.py:302 _update_investor_dna()`로 자동 갱신.
- **프론트 상태**: ❌ 전무.
  - `app/thesis/` 라우트에 `profile`/`dna` 없음 (존재: `(list)`, `new`, `alerts`, `[thesisId]`, `[thesisId]/indicators`, `[thesisId]/close`).
  - `AccuracyRing`, `CategoryChart` 컴포넌트 없음.
  - **DNA 조회 API 엔드포인트도 없음** — `thesis/urls.py`에 InvestorDNA 노출 경로 부재. (BE 모델은 있으나 REST 노출 안 됨)
- **갭 영향**: 특허 독립항 1(투자 DNA 프로파일)의 사용자 대면 부분이 미구현. 데이터는 쌓이는데 노출 경로가 없음.

### 3.2 (C) 마감 아카이브 + ValidityMatrix — FE-PR-10

- **계획**: 마감된 가설 목록(회고 아카이브) + 지표 유효성 2×2 매트릭스 시각화.
- **백엔드 상태**: ✅ 데이터 존재. `ValidityRecord` 마감 시 생성(`thesis_views.py:99`), 가설 `status='closed'` 필터 가능(`get_queryset` status 파라미터 지원).
- **프론트 상태**: ⚠️ 부분.
  - 단건 마감 결과 화면만 존재(`app/thesis/[thesisId]/close/page.tsx` — 이미 마감 시 읽기전용 요약).
  - **마감 가설 전용 목록/아카이브 화면 없음**, `ValidityMatrix` 컴포넌트 없음.
  - 회고 메모(`outcome_note`)는 입력·표시 가능 → "회고"의 최소 형태만 존재.

### 3.3 (C) 히스토리 탭 + 스냅샷 타임라인 — FE-PR-9(§8)

- **계획**: 전체 점수 추이 라인차트 + 스냅샷 타임라인 탭.
- **백엔드 상태**: ✅ `ThesisSnapshot`(asof_date별 overall_score, score_history 계산됨). 단 **스냅샷 시계열 조회 API 없음** (`DashboardView`는 latest 1건만 사용).
- **프론트 상태**: ❌ 히스토리 탭/타임라인 화면 없음.
- **주의**: 지표 *개별* 시계열 차트는 `IndicatorRow` 펼침(1M/1Y/3Y/5Y)으로 구현됨 — 그러나 이는 가설 *전체* 점수 히스토리와는 다른 것.

### 3.4 (C) Finviz 히트맵 + 지표 weight/direction 편집 — FE-PR-8(§8)

- **계획**: 지표 히트맵 그리드 + 가중치/지지방향 인라인 편집.
- **백엔드 상태**: ⚠️ `DashboardView`가 `heatmap: {rows, cols, cells[]}` 응답을 **내려주고 있음**(monitoring_views.py:176, 221). 즉 BE는 준비됨.
- **프론트 상태**: ❌ 히트맵을 렌더하는 컴포넌트 없음 (BE가 보내는 heatmap 필드가 FE에서 미사용 가능성 높음). weight/direction 편집 UI 없음.

### 3.5 (D) 대시보드 3탭 구조 — FE-PR-7(§8)

- **계획**: 관제/상세/히스토리 3탭.
- **실제**: **폐기.** `app/thesis/[thesisId]/page.tsx`는 탭 없는 단일 세로 스크롤(DashboardHeader → AISummarySection → NotableChangesSection → 지표 IndicatorRow 리스트 → 마감 CTA). 리디자인 원칙("내부 점수 숨기고 실세계 값")에 따라 탭 대신 단일 화면으로 의도적 단순화됨.

### 3.6 (B) notable_changes 포맷 불일치 — 리디자인 PR-10 잔여 갭 ★

- **설계(redesign §7-2)**: `notable_changes`를 **alert_engine 이벤트 기반**으로 생성하라.
  포맷: `change_type`('sharp_move'/'direction_flip'...), `description`, `raw_value_before/after`, `severity`('info'/'warning').
  프론트 타입 `NotableChange`(types.ts)도 이 포맷 기대.
- **실제(snapshot_builder.py:108~125)**: **내부 score 기반**으로 생성.
  포맷: `indicator_id`, `indicator_name`, `prev_score`, `curr_score`, `delta` (|score 변화|≥0.3).
- **갭**: ① 키 이름 불일치(`change_type`/`description`/`severity` 누락, `prev_score`/`delta` 등 내부 점수 노출), ② 리디자인 핵심 원칙인 **"내부 점수(score)를 UI/응답에 노출하지 않는다"와 정면 충돌**. 프론트 `NotableChangesSection`이 기대 필드를 못 받아 표시가 깨지거나 빈약할 위험.
- **권고(보고용)**: snapshot_builder의 notable_changes를 alert_engine 이벤트→NotableChange 변환 방식으로 교체하거나, 프론트 타입을 실제 포맷에 맞추거나 둘 중 하나로 정합화 필요.

### 3.7 (D) 유령 컴포넌트 — 리디자인 PR-8/9 잔재

설계대로 생성됐으나 `app/`에서 **import 0건**인 미사용 컴포넌트 (기술 부채):

| 컴포넌트 | 경로 | 상태 |
|---------|------|------|
| `RealValueIndicatorCard.tsx` | `components/thesis/dashboard/` | 미사용 (IndicatorRow로 대체), 테스트만 참조 |
| `ChartToggleButton.tsx` | `components/thesis/dashboard/` | 미사용 (IndicatorRow 내부 토글로 대체) |
| `PeriodSelector.tsx` | `components/thesis/dashboard/` | 미사용 (IndicatorRow 내부 period로 대체) |
| `IndividualMiniCharts.tsx` | `components/thesis/dashboard/` | 미사용 (IndicatorRow 내부 AreaChart로 대체) |

추가 중복: `AddIndicatorSheet.tsx`/`IndicatorCard.tsx`가 `components/thesis/` 루트와 `components/thesis/indicators/` 양쪽에 존재 → 중복 정리 후보.

### 3.8 (C) 백엔드 학습 레이어 Phase 2~4

- `ValidityScore` 모델 미존재 → 유효성 *집계*·지표 추천 boost·DNA 슬라이더·역제안 전부 미구현.
- `InvestorDNA.personalization_weight` 필드는 생성됐으나 **소비 코드 없음**(슬라이더 미연결).
- `is_synthetic` 필드(`ValidityRecord`) 미존재 → 합성 부트스트래핑(특허 독립항 3) 미착수.
- 벡터화/코사인 유사도(Phase 4) 미착수.

---

## 4. 완전 구현(A) 확인 목록 — 참고

리디자인·핵심 루프·학습 Phase 1은 견고하게 구현됨:

- **BE 대시보드 확장**: `display_unit` 필드(migration 0004/0005), `raw_value`/`change_pct`/`raw_value_unit`/`raw_value_asof`, 분기지표(`fiscal_label`/`quarterly_history`/`is_quarterly`/`comparison_type`), `IndicatorReadingsView`(+FMP 히스토리 fallback, 최대 5Y).
- **BE AI 파이프라인**: `tasks/summary.py:generate_thesis_summaries`(멱등, force 옵션) + `config/celery.py:680` Beat 등록 + `tests/thesis/test_generate_summaries.py`.
- **BE 학습 Phase 1**: `HypothesisEvent`(생성·마감·전제·지표·AI상호작용·outcome 전 이벤트 삽입 — `thesis_builder.py`/`thesis_views.py` 다수), `ValidityRecord`(마감 시 2×2 매트릭스 점수 `_compute_validity_score`), `InvestorDNA`(마감 시 `_update_investor_dna` 자동 갱신).
- **FE 대시보드**: `IndicatorRow`(실세계 값 + 전일/전분기/전년동기 비교 라벨 + 지지/반박 + 펼침 차트 + 분기 스파크라인), `AISummarySection`, `NotableChangesSection`, `DashboardHeader`.
- **FE 핵심 루프(FE-PR-1~6)**: 목록·빌더(6단계)·지표설정·대시보드·알림·마감 6 라우트 전건 동작.

---

## 5. 한 줄 결론

> **"깊이+회고+프로필"(§8 FE-PR-7~11)은 사실상 폐기되고, 그 방향성은 `phase3_frontend_redesign`(실세계 값 단일 대시보드, PR-7~10)으로 대체되어 95% 구현됐다.** 회고·프로필의 **데이터 레이어(ValidityRecord/InvestorDNA)는 백엔드에 완비**되어 있으나, **이를 노출하는 화면(DNA 프로필·마감 아카이브·히스토리 타임라인·히트맵)과 조회 API가 전무**한 것이 최대 갭이다. 추가로 ① notable_changes 포맷이 리디자인 "내부 점수 숨김" 원칙과 충돌(B), ② 리디자인 과정의 유령 컴포넌트 4종 정리 필요(D).

---

### 부록: 검증한 파일 (읽기 전용)

- 설계: `phase3_frontend_redesign.md`, `integrated_roadmap.md`, `Phase2_completion_summary.md` (§8)
- BE: `thesis/models/{learning,monitoring,indicator}.py`, `thesis/views/{monitoring_views,thesis_views}.py`, `thesis/urls.py`, `thesis/services/snapshot_builder.py`, `thesis/tasks/summary.py`, `config/celery.py`, `thesis/migrations/*`
- FE: `app/thesis/[thesisId]/page.tsx`, `app/thesis/[thesisId]/close/page.tsx`, `components/thesis/dashboard/IndicatorRow.tsx`, 컴포넌트 트리 전수
