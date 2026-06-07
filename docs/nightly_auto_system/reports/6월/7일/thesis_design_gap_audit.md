# Thesis Control 설계 갭 감사

> 작성일: 2026-06-08 (야간 자동 감사)
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` (백엔드) + `frontend/components/thesis/` (프론트엔드) 구현 대조
> 성격: **읽기 전용 감사** — 코드 수정 없음
> 분류: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 0. 핵심 발견 — "Phase 3"이 세 갈래로 분기되어 있다

이번 감사의 가장 중요한 발견은 **`docs/thesis_control/` 안에서 "Phase 3"이라는 용어가 서로 다른 3개 트랙을 동시에 가리킨다**는 점이다. 이로 인해 CLAUDE.md의 "진행 중: Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)" 기록이 **실제 구현 현황과 불일치**한다.

| 트랙 | 출처 문서 | 작성일 | "Phase 3" 정의 | 실제 구현 |
|------|-----------|--------|----------------|-----------|
| **A. 깊이+회고+프로필** | `frontend/task_done/Phase2_completion_summary.md` §8 | 2026-03-16 | FE-PR-7~11 = 탭구조 + 히트맵 + 히스토리 + 마감아카이브 + 투자자DNA | ❌ **거의 미구현** |
| **B. 실제값 대시보드 리디자인** | `plan/thesis_control_phase3_frontend_redesign.md` (1.0 FINAL) | 2026-03-18 | PR-7~10 = display_unit + 실제값 카드 + 미니차트 + AI파이프라인 | ✅ **완전 구현** |
| **C. LLM 빌더 재설계** | `plan/talking_builder/redesign_build_plan/` | 2026-03-19 | Phase A/B/C = one-shot proposal 빌더 | ✅ **Phase A+B 완료** |

**결론**: FE-PR-7~11(트랙 A)은 03-18에 **트랙 B(실제값 대시보드)로 PR 번호가 재정의·대체(D)**되었고, 실제 구현은 트랙 B를 따랐다. 즉 CLAUDE.md가 가리키는 "깊이+회고+프로필"은 실질적으로 **방향 전환되어 폐기**된 상태이며, 그 자리에 "실제값 중심 대시보드"가 들어갔다. 별도로 트랙 C(LLM 빌더)가 03-19~20에 추가 구현됐다.

추가로, `plan/thesis_control_integrated_roadmap.md`의 **수학·학습 엔진 기준 Phase 1~4**(관제엔진→유효성활성화→합성에이전트→벡터)는 위 프론트엔드 Phase와 **완전히 다른 축**이다. 이 로드맵 기준으로는 **Phase 1만 부분 완료, Phase 2~4 전부 미착수**다.

---

## 1. 요약 (Phase별 구현률)

### 1.1 프론트엔드 화면 트랙

| 트랙 | 항목 | 구현률 | 분류 |
|------|------|--------|------|
| Phase 2 (핵심 루프) | 목록→빌더→지표→대시보드→알림→마감 (FE-PR-1~6) | **100%** | A |
| Phase 3-A (깊이+회고+프로필) | 탭/히트맵/히스토리/아카이브/DNA (FE-PR-7~11) | **~5%** | C/D |
| Phase 3-B (실제값 대시보드) | PR-7~9 (display_unit + 실제값카드 + 미니차트) | **100%** | A |
| Phase 3-B (PR-10 AI 파이프라인) | generate_thesis_summaries + notable_changes | **~70%** | B |
| Phase C (LLM 빌더) | one-shot proposal (A-MVP + Hardening + B) | **100%** | A |

### 1.2 수학·학습 엔진 트랙 (integrated_roadmap 기준)

| Phase | 항목 | 구현률 | 분류 |
|-------|------|--------|------|
| Phase 1 | 관제엔진(Stage 0~3) + 이벤트수집 + ValidityRecord + InvestorDNA 골격 | **~75%** | B |
| Phase 2 | ValidityScore 집계 + DNA 슬라이더 + 역제안 + 상관할인 + 뉴스센티먼트 | **0%** | C |
| Phase 3 | 합성 에이전트(SyntheticBootstrapper) + Online LR(ThesisWeightLearner) | **0%** | C |
| Phase 4 | DNA 벡터화 + 유효성 벡터화 + 코사인 유사도 | **0%** | C |

### 1.3 한눈에 보는 전체 그림

```
✅ 완전 구현 : Phase 2 핵심 루프 / 실제값 대시보드(3-B) / LLM 빌더(Phase A+B)
🟡 부분 구현 : 관제 엔진 Phase 1(이벤트 기록은 되나 학습 미연결) / AI 파이프라인(PR-10)
❌ 미구현    : 깊이+회고+프로필(3-A) / 유효성 학습 활성화(Phase 2~4 전체)
🔄 대체/폐기 : FE-PR-7~11(원안) → 실제값 대시보드로 전환
```

---

## 2. 문서별 상태 테이블

| 설계 문서 | 정의 범위 | 구현 상태 | 분류 | 근거 |
|-----------|-----------|-----------|------|------|
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 핵심 루프 6 PR | 전건 구현 (라우트 6, 컴포넌트 30+) | **A** | `app/thesis/` 6개 라우트 + `components/thesis/` 전 디렉토리 존재 |
| `frontend/task_done/Phase2_completion_summary.md` §8 | FE-PR-7~11 (깊이+회고+프로필) | 미구현 → 대체됨 | **D** | 히트맵/DNA/히스토리/아카이브/ValidityMatrix 컴포넌트·라우트 전무 |
| `plan/thesis_control_phase3_frontend_redesign.md` | PR-7(BE) | 구현 | **A** | `display_unit` 필드(migration 0004), `IndicatorReadingsView`, readings URL 모두 존재 |
| 〃 | PR-8(실제값카드 + AI분석) | 구현 | **A** | `RealValueIndicatorCard`, `AISummarySection`, `NotableChangesSection` 존재 |
| 〃 | PR-9(미니차트 + 기간선택 + 정리) | 구현 | **A** | `IndividualMiniCharts`, `ChartToggleButton`, `PeriodSelector` 존재 / `OverallMoon`·`DashboardIndicatorCard`·`RecentChange` 삭제 확인 |
| 〃 | PR-10(AI 모니터링 파이프라인) | 부분 구현 | **B** | `generate_thesis_summaries` task + snapshot의 `ai_summary`/`notable_changes` 필드 존재. 단 **Beat 스케줄(07:30) 미등록**, 주간 건강검진 미구현 |
| `plan/talking_builder/redesign_build_plan/01~02` | Phase A-MVP + Hardening (PR-1~7) | 구현 완료 | **A** | `work_done/phase_a_llm_builder.md` 보고 + `builder_state.py`/`prompt_builder.py`/`llm_postprocess.py`/`feature_flags.py` 존재 |
| `plan/talking_builder/redesign_build_plan/03` | Phase B (KeywordCache + collectors, PR-8~12) | 구현 완료 | **A** | `KeywordCache` 모델(migration 0006/0007) + `keyword_collectors/{news,eod,chain}.py` + `keyword_hint.py` 존재 |
| `plan/talking_builder/redesign_build_plan/04` | Phase C (Health Report, 멀티턴, 스트리밍) | 부분/미구현 | **B/C** | 멀티턴 핸들링 일부(`process_llm_turn` fallback) 존재. Health Report·스트리밍 미확인 |
| `plan/thesis_control_integrated_roadmap.md` Phase 1 | 관제엔진 + 이벤트 + ValidityRecord + DNA 골격 | 부분 구현 | **B** | 엔진·이벤트·모델 존재, **InvestorDNA 자동 갱신 로직·signal 누락** |
| 〃 Phase 2 | ValidityScore + DNA 슬라이더 + 역제안 | 미구현 | **C** | `ValidityScore` 모델·마이그레이션·집계 task 전무 |
| 〃 Phase 3 | 합성 에이전트 + Online LR | 미구현 | **C** | `SyntheticBootstrapper`·`ThesisWeightLearner` 전무 |
| 〃 Phase 4 | 벡터 스코어링 | 미구현 | **C** | DNA 벡터화·코사인 유사도 전무 |
| `plan/thesis_control_design.md` / `_math_model_final.md` / `_implementation_guide.md` | 수학 모델 v2.3.2 마스터 설계 | 엔진 부분만 구현 | **B** | Stage 0~3 구현됨. 학습/개인화 레이어 미구현 (위 Phase 2~4와 동일) |

---

## 3. Phase 3 미구현 항목 상세

> 아래는 **CLAUDE.md가 "진행 중"으로 기록한 트랙 A("깊이+회고+프로필", FE-PR-7~11)** 기준 미구현 목록과, **수학 엔진 로드맵 Phase 2~4** 미구현 목록을 분리 정리한다.

### 3.1 트랙 A — 깊이+회고+프로필 (FE-PR-7~11) — 분류 C/D

설계상 5개 PR 전부가 미구현이며, 03-18 리디자인 문서에서 PR 번호가 실제값 대시보드로 재할당되어 **사실상 폐기(D)** 상태다.

| 원안 PR | 설계 항목 | 미구현 증거 | 비고 |
|---------|-----------|-------------|------|
| FE-PR-7 | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD | `[thesisId]/page.tsx`가 **단일 페이지**, 탭 구조 없음 | 대체됨 → 실제값 단일 대시보드 |
| FE-PR-8 | Finviz 스타일 히트맵 + weight/direction 편집 | `HeatmapData`/`HeatmapCell` **타입만 정의**(types.ts), 렌더 컴포넌트 없음. `DashboardResponse.heatmap` 필드는 응답에 있으나 프론트 미사용 | 백엔드 데이터만 존재, UI 死蔵(dead) |
| FE-PR-9 | 히스토리 탭 (라인차트 + 스냅샷 타임라인) | `/thesis/[id]/history` 라우트 없음, 스냅샷 타임라인 UI 없음 | 미구현 |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix | `/thesis/archive` 라우트 없음, `ValidityMatrix` 컴포넌트·타입 없음 | 미구현 |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `/thesis/dna` 라우트 없음, `AccuracyRing`·`CategoryChart`·`InvestorDNA` 타입/컴포넌트 전무 | 미구현 (백엔드 `InvestorDNA` 모델만 존재) |

**판단**: 트랙 A는 "미완성 진행 중"이 아니라 **의도적 방향 전환으로 대체**된 것으로 보인다. CLAUDE.md 구현 상태 표기를 갱신할 필요가 있다 (→ "실제값 대시보드 리디자인 완료 / 깊이+회고+프로필은 보류·재정의").

### 3.2 수학 엔진 로드맵 Phase 1 잔여 (분류 B)

| 항목 | 상태 | 누락 증거 |
|------|------|-----------|
| HypothesisEvent 기록 | ✅ 존재 | `learning.py` 모델 + `builder_events.py log_event()` + close 액션 기록 |
| ValidityRecord 생성 | ✅ 존재 | `learning.py` 모델 + `ThesisViewSet.close`에서 생성 |
| InvestorDNA 모델 | 🟡 골격만 | `learning.py`에 모델 존재. **자동 갱신 signal/task 없음** — 마감 시 DNA 통계(premise_category_counts, indicator_type_counts, ai_accept_rate) 집계 로직 미구현 |
| InvestorDNA 조회 API | ❌ 없음 | DNA 조회 View·URL 없음 (UI 부재와 정합) |

### 3.3 수학 엔진 로드맵 Phase 2~4 (분류 C — 전체 미착수)

| Phase | 미구현 항목 | 누락 증거 |
|-------|-------------|-----------|
| **Phase 2** | `ValidityScore` 집계 모델 | 모델·마이그레이션 없음 |
| Phase 2 | ValidityRecord→ValidityScore 집계 Celery task | task 없음 |
| Phase 2 | 지표 추천 유효성 점수 반영(core/reference/low_impact 티어) | `indicator_matcher`에 validity_boost 로직 없음 |
| Phase 2 | DNA 적합도 슬라이더(personalization_weight 활용) | 필드는 모델에 있으나 사용처 없음 |
| Phase 2 | 역제안(Contrarian Nudge) | 미구현 |
| Phase 2 | 상관계수 자동 할인 / Adaptive Decay / Sustained Extreme / 뉴스 센티먼트 Stage1 입력 | 미구현 (math_model_final 예정 항목) |
| **Phase 3** | `SyntheticBootstrapper` (합성 페르소나 부트스트랩) | 클래스·서비스 없음 — 특허 독립항3 핵심 |
| Phase 3 | `ThesisWeightLearner` (Online Logistic Regression) | 클래스 없음 (builder_state 주석 언급만) |
| Phase 3 | 합성/실제 데이터 블렌딩 (`is_synthetic` 플래그) | ValidityRecord에 해당 필드 없음 |
| **Phase 4** | DNA 벡터화 / 유효성 6차원 벡터 / 코사인 유사도 / 사용자 유사도 | 전무 |

### 3.4 트랙 B(실제값 대시보드) 잔여 (분류 B)

대시보드 자체는 완성이나, 데이터를 채우는 PR-10 파이프라인에 잔여가 있다.

| 항목 | 상태 | 비고 |
|------|------|------|
| `generate_thesis_summaries` task | ✅ 구현 | Gemini 2.5 Flash 동기 호출, 멱등성 처리 |
| `notable_changes` 채우기 | 🟡 부분 | snapshot_builder에서 alert→notable 변환. 실제 동작 여부 데이터 검증 필요 |
| Beat 스케줄(07:30 generate_thesis_summaries) | ❌ 미등록 | tasks 주석에 권장 시간만 명시, DatabaseScheduler 등록 미확인 (common-bug #28 패턴) |
| 주간 건강검진(Weekly Health Check) | ❌ 미구현 | redesign 문서 §7-3, "Phase 2 이후" 명시된 향후 항목 |

---

## 4. 권고 (감사 관점, 실행은 별도)

1. **CLAUDE.md 구현 상태 갱신**: "진행 중: Thesis Control Phase 3 (깊이+회고+프로필: FE-PR-7~11)" → 실제는 "실제값 대시보드 리디자인 완료 / LLM 빌더 Phase A+B 완료 / 깊이+회고+프로필 트랙은 재정의·보류"로 정정 필요. **용어 혼란이 가장 큰 리스크.**
2. **"Phase 3" 명칭 충돌 해소**: 프론트 화면 Phase와 수학엔진 로드맵 Phase를 문서상 명확히 구분(예: "FE-Phase 3" vs "Engine-Phase 3").
3. **死蔵 데이터 정리**: `DashboardResponse.heatmap` / `HeatmapData` 타입은 백엔드가 내려주나 프론트 미사용 — 유지/제거 결정 필요.
4. **Phase 2 학습 활성화가 특허 청구항 핵심**: integrated_roadmap §6 기준 ValidityScore·DNA 슬라이더·합성 에이전트가 특허 독립항 1~3과 직결. 미구현 상태가 길어지면 특허 실시 근거 약화 가능 — 우선순위 재검토 권고.
5. **Beat 스케줄 점검**: `generate_thesis_summaries` 07:30 등록 여부를 `beat_schedule_audit.md`와 교차 확인.

---

## 5. 부록 — 구현 증거 인덱스

**백엔드 (`thesis/`)**
- 모델: `models/thesis.py`(Thesis, ThesisPremise), `models/indicator.py`(ThesisIndicator+display_unit, IndicatorReading), `models/monitoring.py`(ThesisSnapshot+ai_summary/notable_changes, ThesisAlert), `models/learning.py`(HypothesisEvent, ValidityRecord, InvestorDNA), `models/keyword.py`, `models/community.py`
- views: `views/thesis_views.py`(ThesisViewSet.close 포함), `views/monitoring_views.py`(DashboardView, IndicatorReadingsView, Alert*), `views/conversation_views.py`
- services: scoring(`indicator_scorer`, `premise_aggregator`, `snapshot_builder`, `thesis_state_machine`, `arrow_calculator`), 빌더(`thesis_builder`, `builder_state`, `prompt_builder`, `llm_postprocess`, `builder_events`), 매칭(`indicator_matcher`), 알림(`alert_engine`), 검증(`data_validator`), 키워드(`keyword_hint`, `keyword_cache`, `keyword_collectors/`)
- tasks: `summary.py`(generate_thesis_summaries), `eod_pipeline.py`(update_indicator_readings, calculate_scores, create_snapshots_and_alerts)
- migrations: 0001(초기 12모델), 0004/0005(display_unit), 0006/0007(KeywordCache), 0009(recommendation_reason)
- **부재**: ValidityScore 모델, ThesisWeightLearner, SyntheticBootstrapper, InvestorDNA 갱신 task/signal, DNA 조회 view

**프론트엔드 (`frontend/`)**
- 라우트: `app/thesis/(list)/page.tsx`, `(list)/alerts/`, `new/`, `[thesisId]/`, `[thesisId]/indicators/`, `[thesisId]/close/`
- dashboard 컴포넌트: RealValueIndicatorCard, AISummarySection, NotableChangesSection, IndicatorRow, IndividualMiniCharts, QuarterlySparkline, ChartToggleButton, PeriodSelector, DashboardHeader, DashboardPageHeader
- lib: `types.ts`(raw_value/raw_value_unit/change_pct/NotableChange/IndicatorReadingsResponse/HeatmapData), `api.ts`(dashboard, indicatorReadings), `queries.ts`(useDashboard, useIndicatorReadings, useAllIndicatorReadings)
- **부재**: 탭 구조, Heatmap UI, AccuracyRing, CategoryChart, ValidityMatrix, DNA/History/Archive 라우트·컴포넌트·타입
- **삭제 확인**: OverallMoon, DashboardIndicatorCard, RecentChange (PR-9 정리 완료)
</content>
</invoke>
