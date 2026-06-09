# Thesis Control 설계 갭 감사

> 감사일: 2026-06-09
> 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드)
> 성격: **읽기 전용 감사** — 코드 미수정
> 감사자: nightly auto system

---

## 0. 핵심 발견 (TL;DR)

1. **"Phase 3"라는 이름이 두 개의 서로 다른 설계를 가리킨다.** 혼동 주의.
   - **Phase 3-A** = `thesis_control_integrated_roadmap.md`의 Phase 3 → **합성 에이전트 + Online LR (백엔드 ML)** → **미구현 (C)**
   - **Phase 3-B** = `thesis_control_phase3_frontend_redesign.md`의 PR-7~10 → **대시보드 실세계값 리디자인** → **완전 구현 (A)**

2. **`Phase2_completion_summary.md`가 예고한 "Phase 3 = FE-PR-7~11 (깊이+회고+프로필)"은 사실상 폐기/대체되었다 (D).**
   탭 구조·히트맵·히스토리 탭·마감 아카이브·DNA 프로필 화면 중 **단 하나도 구현되지 않았고**, 그 자리를 Phase 3-B(대시보드 리디자인)가 대신했다.

3. **CLAUDE.md의 "진행 중: Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)" 기재는 실제 코드와 불일치(stale)** — 해당 PR들의 산출물이 코드베이스에 존재하지 않음.

---

## 1. 요약 (Phase별 구현률)

| Phase | 설계 출처 | 핵심 내용 | 구현률 | 분류 |
|-------|-----------|-----------|--------|------|
| **Phase 1** | integrated_roadmap §1 | 관제 엔진(Stage 0~3) + 이벤트 수집 + ValidityRecord + InvestorDNA 골격 | **~95%** | **A** 완전 구현 |
| **Phase 2** | integrated_roadmap §2 | ValidityScore 활성화 + DNA 슬라이더 + 역제안 넛지 + 유효성 기반 지표 추천 | **~10%** | **C** 미구현 (필드 골격만) |
| **Phase 3-A** | integrated_roadmap §3 | 합성 에이전트 부트스트래핑 + Online LR + 합성/실데이터 블렌딩 | **0%** | **C** 미구현 |
| **Phase 4** | integrated_roadmap §4 | DNA/유효성 벡터화 + 코사인 유사도 추천 | **0%** | **C** 미구현 |
| **Phase 3-B (대시보드)** | phase3_frontend_redesign PR-7~10 | 실세계값 카드 + AI요약 + 오늘의변화 + 미니차트 | **~95%** | **A** 완전 구현 |
| **FE-PR-7~11 (깊이/회고/프로필)** | Phase2_completion_summary §8 | 탭구조 + 히트맵 + 히스토리 + 마감아카이브 + DNA프로필 | **0%** | **D** 폐기/대체 |
| **Phase A LLM 빌더** (별도 트랙) | work_done/phase_a_llm_builder.md | one-shot LLM 제안형 빌더 (3턴) | **~100%** | **A** 완전 구현 |

---

## 2. 문서별 상태 테이블

| # | 설계 문서 | 설계 대상 | 코드 대조 결과 | 분류 |
|---|-----------|-----------|----------------|------|
| 1 | `plan/thesis_control_design.md` | 전체 설계 (관제 엔진) | Stage 0~3 서비스 전부 존재 (`data_validator`, `indicator_scorer`, `premise_aggregator`, `thesis_state_machine`, `arrow_calculator`, `snapshot_builder`, `alert_engine`) | **A** |
| 2 | `plan/thesis_control_math_model_final.md` | 수학 모델 v2.3.2 | Stage 0~3 구현 (Phase 2 항목인 상관할인/Adaptive Decay/Sustained Extreme/뉴스 센티먼트는 미반영 추정) | **B** (Phase 1 분량만) |
| 3 | `plan/thesis_control_integrated_roadmap.md` Phase 1 | 이벤트/유효성/DNA 골격 | `learning.py`에 3모델 + `thesis_views.py` close 플로우에 전부 연결 | **A** |
| 4 | `plan/thesis_control_integrated_roadmap.md` Phase 2 | ValidityScore + 슬라이더 + 역제안 | `ValidityScore` 모델 없음, 슬라이더/넛지 로직 없음, 집계 태스크 없음 | **C** |
| 5 | `plan/thesis_control_integrated_roadmap.md` Phase 3-A | 합성 에이전트 + Online LR | `is_synthetic` 필드·`SyntheticBootstrapper`·`ThesisWeightLearner` 전무 | **C** |
| 6 | `plan/thesis_control_integrated_roadmap.md` Phase 4 | 벡터 스코어링 | `dna_vector`/`validity_vector` 전무 | **C** |
| 7 | `plan/thesis_control_phase3_frontend_redesign.md` PR-7 | display_unit + IndicatorReadingsView + raw_value | 전부 구현 (migration 0004/0005, view L260, raw_value L94~165) | **A** |
| 8 | `plan/thesis_control_phase3_frontend_redesign.md` PR-8 | 실세계값 카드 + AI요약 + 오늘의변화 | `RealValueIndicatorCard`/`AISummarySection`/`NotableChangesSection` 존재, 페이지 통합됨 | **A** |
| 9 | `plan/thesis_control_phase3_frontend_redesign.md` PR-9 | 미니차트 + 기간선택 + 정리 | `ChartToggleButton`/`PeriodSelector`/`IndividualMiniCharts` 존재, OverallMoon/DashboardIndicatorCard/RecentChange 삭제 확인 | **A** |
| 10 | `plan/thesis_control_phase3_frontend_redesign.md` PR-10 | AI요약 파이프라인 + notable_changes 연동 | `tasks/summary.py: generate_thesis_summaries` 구현. **단 notable_changes는 alert 기반이 아닌 score 기반(\|Δscore\|≥0.3)으로 구현** | **B** (방식 변경) |
| 11 | `frontend/task_done/FE-PR-1~6` | Phase 2 핵심 루프 (목록~마감) | 6개 라우트 + 30+ 컴포넌트 전부 존재 | **A** |
| 12 | `Phase2_completion_summary.md §8` FE-PR-7 | 대시보드 탭 구조 + 상세 탭 + 전제 CRUD | 탭 구조 없음, `[thesisId]/page.tsx`는 단일 페이지 | **D** |
| 13 | `Phase2_completion_summary.md §8` FE-PR-8 | Finviz 히트맵 + weight/direction 편집 | 히트맵 컴포넌트 없음 | **D** |
| 14 | `Phase2_completion_summary.md §8` FE-PR-9 | 히스토리 탭 (recharts 스냅샷 타임라인) | 히스토리 라우트/컴포넌트 없음 | **D** |
| 15 | `Phase2_completion_summary.md §8` FE-PR-10 | 마감 아카이브 + ValidityMatrix UI | 아카이브 화면 없음, close 페이지는 단건 outcome만 | **D** |
| 16 | `Phase2_completion_summary.md §8` FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | DNA 프로필 화면/API 엔드포인트 없음 | **D** |
| 17 | `plan/talking_builder/` + `work_done/phase_a_llm_builder.md` | LLM one-shot 빌더 + 키워드 enrichment | `prompt_builder`/`llm_postprocess`/`builder_events`/`keyword_collectors` 전부 존재 | **A** |

---

## 3. Phase 3 미구현 항목 상세

사용자 질의의 "Phase 3 (깊이 + 회고 + 프로필)"은 `Phase2_completion_summary.md §8`이 정의한 **FE-PR-7~11**을 의미한다. 아래는 그 전건 미구현 상세 + 백엔드 Phase 3-A(합성 에이전트) 미구현 상세.

### 3.1 FE-PR-7~11 (깊이 + 회고 + 프로필) — 전건 미구현 / 방향 폐기 (D)

| PR | 설계된 산출물 | 기대 경로(추정) | 실제 | 갭 |
|----|---------------|-----------------|------|-----|
| FE-PR-7 | 대시보드 3탭 (관제/상세/히스토리) + 전제 CRUD | `app/thesis/[thesisId]/page.tsx` 탭화 | 단일 페이지 (탭 없음) | 탭 컨테이너·상세 탭·전제 추가/수정/삭제 UI 전무 |
| FE-PR-8 | Finviz 스타일 지표 히트맵 + weight/direction 인라인 편집 | `components/thesis/dashboard/IndicatorHeatmap.tsx` | 파일 없음 | 히트맵·지표 가중치 편집 UI 전무 |
| FE-PR-9 | 히스토리 탭 (recharts 라인 + 스냅샷 타임라인) | `app/thesis/[thesisId]/history/` | 라우트 없음 | ThesisSnapshot 시계열 시각화 전무 (단, `IndividualMiniCharts`로 지표별 raw 시계열은 별도 구현됨) |
| FE-PR-10 | 마감 가설 아카이브 목록 + ValidityMatrix 표시 | `app/thesis/archive/` | 라우트 없음 | 마감 회고 화면 전무. close 페이지는 단건 outcome 입력만 (`close/page.tsx`) |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `app/thesis/profile/` | 라우트 없음 | `InvestorDNA` 데이터는 백엔드에 축적되나 **이를 노출하는 API·화면 둘 다 없음** |

**근거:**
- `frontend/app/thesis/` 전체 파일: `(list)/page.tsx`, `(list)/alerts/page.tsx`, `new/page.tsx`, `[thesisId]/page.tsx`, `[thesisId]/indicators/page.tsx`, `[thesisId]/close/page.tsx` — Phase 2 루프(FE-PR-1~6)에서 멈춤. 탭/히스토리/아카이브/프로필 라우트 없음.
- 키워드 grep(`히스토리|히트맵|heatmap|DNA|AccuracyRing|CategoryChart|ValidityMatrix|아카이브|archive`) → Phase 3 회고/프로필 관련 매칭 0건.

**해석 (D 폐기/대체):**
`Phase2_completion_summary.md`(2026-03-16) 작성 직후, 실제 개발 방향은 FE-PR-7~11(깊이/회고/프로필)이 아니라 **`phase3_frontend_redesign.md`(2026-03-18)의 대시보드 실세계값 리디자인(PR-7~10)으로 전환**되었다. PR 번호(7~10)가 우연히 겹쳐 더 혼동을 키운다. 즉 "Phase 3" 리소스는 회고/프로필이 아닌 **대시보드 UX 재설계**에 투입되었고, 깊이/회고/프로필 트랙은 착수되지 않은 채 미정 상태.

### 3.2 백엔드 Phase 3-A (합성 에이전트 + Online LR) — 미구현 (C)

| 설계 항목 (integrated_roadmap §3) | 기대 심볼 | 실제 | 갭 |
|-----------------------------------|-----------|------|-----|
| 합성 에이전트 부트스트래핑 | `SyntheticBootstrapper`, `SYNTHETIC_PERSONAS` | 없음 | 콜드스타트 해결 로직 전무 |
| 합성 데이터 마킹 | `ValidityRecord.is_synthetic` | 필드 없음 (`learning.py` 미확인) | 합성/실데이터 구분 불가 |
| Online Logistic Regression | `ThesisWeightLearner` | 없음 | 전제 가중치 자동학습 전무 |
| 합성/실데이터 블렌딩 | `aggregate_validity_scores(blend_ratio)` | 없음 | — |

### 3.3 백엔드 Phase 2 (유효성 활성화) — 골격만 존재 (C)

Phase 3-A의 전제조건인 Phase 2조차 미완이므로 함께 기록한다.

| 설계 항목 | 기대 | 실제 | 갭 |
|-----------|------|------|-----|
| `ValidityScore` 모델 | (thesis_type×indicator×regime) 집계 테이블 | `models/__init__.py`·`learning.py`에 부재 | ValidityRecord는 쌓이지만 **집계·활성화(sample_count≥5) 미구현** |
| ValidityScore 집계 Celery 태스크 | 주 1회 Record→Score | 없음 | — |
| 유효성 기반 지표 추천 | `match_indicators`에 `validity_boost` | `indicator_matcher`는 LLM/키워드 매칭만, 유효성 부스트 없음 | core/reference/low_impact 티어 분류 없음 |
| DNA 적합도 슬라이더 | `apply_dna_personalization(personalization_weight)` | `personalization_weight=0.5` 필드만 존재, 사용 로직 없음 | 슬라이더 UI·블렌딩 로직 전무 |
| 역제안 넛지 | `add_contrarian_nudge` | 없음 | — |

### 3.4 Phase 3-B (대시보드 리디자인) 내 부분 변경 (B)

완전 구현이나 한 가지 설계 이탈을 명시한다.

- **notable_changes 산출 방식 변경:** 설계(PR-10 §7-2)는 `alert_engine` 이벤트(`direction_flip`/`sharp_move`/`extreme_volatility`)를 `NotableChange` 포맷으로 변환하도록 규정했으나, 실제 `snapshot_builder.py`는 **이전 스냅샷 대비 `|Δscore| ≥ 0.3`** 기준으로 직접 생성한다 (L108~160). 결과 표시는 동일하나 트리거 소스가 alert 기반이 아닌 score 기반 — 설계 의도(내부 점수 숨김·alert 재활용)와 부분 충돌. 기능적 회귀는 아니나 향후 PR-10 정식 연동 시 재정렬 필요.

---

## 4. 권고 (감사 관점, 실행 아님)

1. **CLAUDE.md 상태 정정:** "진행 중: Thesis Control Phase 3 (깊이+회고+프로필 FE-PR-7~11)"은 실제와 불일치. → "Phase 3-B 대시보드 리디자인 완료 / FE-PR-7~11(회고·프로필) 미착수(보류)"로 갱신 권고.
2. **"Phase 3" 명칭 정리:** integrated_roadmap의 Phase 3(ML)와 phase3_frontend_redesign(대시보드)의 동명·동번호 충돌이 추적을 어렵게 함. 문서 상단에 별칭(Phase 3-A/3-B) 명시 권고.
3. **축적 데이터 활용 갭:** `InvestorDNA`/`ValidityRecord`가 close 플로우에서 꾸준히 적립되나 이를 읽는 API·화면이 없어 **데이터만 쌓이고 미사용** 상태. Phase 2 활성화 또는 FE-PR-11(DNA 프로필) 착수 시 즉시 가치화 가능.

---

## 부록: 검증에 사용한 근거 경로

- 백엔드 모델: `thesis/models/__init__.py`, `thesis/models/learning.py` (HypothesisEvent/ValidityRecord/InvestorDNA 3종, ValidityScore 부재)
- 마감 플로우 연결: `thesis/views/thesis_views.py` L62~222 (ValidityRecord/InvestorDNA/HypothesisEvent 생성)
- 대시보드 백엔드: `thesis/views/monitoring_views.py` L94~165(raw_value), L216~217(ai_summary/notable), L260(IndicatorReadingsView), L351(_infer_unit)
- AI 요약 태스크: `thesis/tasks/summary.py` (generate_thesis_summaries)
- notable_changes 생성: `thesis/services/snapshot_builder.py` L108~160 (score 기반)
- 프론트 라우트: `frontend/app/thesis/**` (6 라우트, 탭/히스토리/아카이브/프로필 부재)
- 프론트 컴포넌트: `frontend/components/thesis/**` (Phase 3-B 카드 6종 존재, 회고/프로필/히트맵 부재)
- 마이그레이션: `thesis/migrations/0004_add_display_unit.py`, `0005_populate_display_unit.py`
