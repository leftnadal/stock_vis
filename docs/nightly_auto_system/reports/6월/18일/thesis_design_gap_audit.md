# Thesis Control 설계 갭 감사

> **감사 유형**: 읽기 전용 (코드 무변경)
> **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis`
> **감사일**: 2026-06-19
> **범위**: `docs/thesis_control/` 설계 ↔ `thesis/` 백엔드 + `frontend/components/thesis/` 프론트엔드
> **분류 기준**: (A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체

---

## ⚠️ 핵심 발견 (먼저 읽을 것)

**`FE-PR-7 ~ FE-PR-11`은 설계 문서 두 곳에서 서로 다르게 정의되어 있으며, 후자가 전자를 대체(supersede)했다.**

| 정의 출처 | FE-PR-7~11의 의미 | 현재 상태 |
|----------|------------------|----------|
| **원안** `frontend/task_done/Phase2_completion_summary.md` §8 | **깊이 + 회고 + 프로필** — 탭 구조 / Finviz 히트맵 / 히스토리 차트 / 마감 아카이브 / 투자자 DNA 프로필 | ❌ **폐기됨 (D)** — 프론트 미구현 |
| **리디자인** `plan/thesis_control_phase3_frontend_redesign.md` | **실제 값(raw_value) 재설계** — display_unit / 실제값 카드 / AI 요약 / 미니차트 / AI 파이프라인 | ✅ **거의 구현됨 (A/B)** |

즉, 사용자 메모리·CLAUDE.md에 "진행 중"으로 적힌 **"Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"**은 **그 형태 그대로는 구현되지 않았고**, 대신 **"실제 값 리디자인"으로 방향이 전환되어 PR-7~9가 구현 완료, PR-10이 부분 구현, PR-11은 미구현** 상태다. 원안의 핵심 산출물(히트맵/히스토리 탭/DNA 프로필 화면/마감 아카이브/ValidityMatrix UI)은 **현재 코드에 존재하지 않는다.**

회고·프로필의 **백엔드 기록 계층**(`HypothesisEvent`, `ValidityRecord`, `InvestorDNA`)은 모델·마감 훅 수준에서 구현돼 있으나, **API 노출과 프론트 화면이 전혀 없어** 사용자에게 도달하지 못한다(데드 계층).

---

## 1. 요약 (Phase별 구현률)

| Phase | 설계 정의 | 구현률 | 비고 |
|-------|----------|--------|------|
| **Phase 1 (백엔드 관제 엔진)** | EOD 3-task 파이프라인 + 스코어링 + 상태머신 + 알림 | **A — 100%** | `eod_pipeline.py` 3-task, `indicator_scorer`, `thesis_state_machine`, `alert_engine` 전부 존재 |
| **Phase 2 (FE 핵심 루프 FE-PR-1~6)** | 목록→빌더→지표→대시보드→알림→마감 | **A — 100%** | 6개 라우트 + 30+ 컴포넌트 전부 구현 |
| **Phase A (LLM 빌더, 백엔드)** | wizard → LLM one-shot 제안 모드 | **A — 100%** | `builder_state/prompt_builder/llm_postprocess` + FE phase 분기 |
| **Phase B (Keyword Hint)** | KeywordCache + collectors | **B — 부분** | 모델·서비스·command 존재, 단 feature flag `KEYWORD_HINTS_ENABLED=False` (비활성) |
| **Phase 3 — 원안 (깊이+회고+프로필)** | 히트맵/히스토리 탭/DNA/아카이브 | **D — 폐기/대체** | 프론트 산출물 0건, 타입·mock 잔재만 존재 |
| **Phase 3 — 리디자인 (실제값)** | PR-7 BE / PR-8 카드 / PR-9 차트 / PR-10 AI / PR-11 헬스체크 | **B — ~80%** | PR-7·8·9 = A, PR-10 = B, PR-11 = C |
| **로드맵 Phase 3 (합성에이전트+자동학습)** | 합성 페르소나 부트스트랩 + Online Logistic Regression + 3D ValidityScore | **C — 미구현** | 단순 2×2 `_compute_validity_score`만 존재, 자동학습 엔진 없음 |

---

## 2. 문서별 상태 테이블

### 2-A. 설계/계획 문서 (`docs/thesis_control/plan/`, `docs/thesis_control/`)

| 문서 | 정의 내용 | 구현 상태 | 분류 |
|------|----------|----------|------|
| `plan/thesis_control_design.md` | 전체 관제 엔진 + 수학 모델 골격 | 백엔드 엔진 구현 완료 | **A** |
| `plan/thesis_control_math_model_final.md` | Robust Z + Decay + 상태머신 (v2.3.2) | `indicator_scorer.py` / `thesis_state_machine.py`에 구현 | **A** |
| `plan/thesis_control_implementation_guide.md` | 구현 가이드 | Phase 1~2 기준 반영 | **A** |
| `plan/thesis_control_integrated_roadmap.md` | Phase 3 = "합성 에이전트 + 자동학습" | 자동학습 엔진 미구현 (2×2 매트릭스만) | **C** |
| `plan/thesis_control_phase3_frontend_redesign.md` | FE-PR-7~11 = 실제값 리디자인 | PR-7·8·9 구현, PR-10 부분, PR-11 미구현 | **B** |
| `plan/talking_builder/*` | 대화형 빌더 설계 | Phase A로 구현 완료 | **A** |
| `thesis_control_user_experience.md` | UX 시나리오 | 핵심 루프 UX 구현됨 | **A** |
| `thesis_control_phase1_*` (prompts/FE_PR_1~5) | Phase 1~2 프롬프트/지시서 | 구현 완료 후 휘발성 지시서 | **A** |

### 2-B. 완료 보고서 (`docs/thesis_control/frontend/task_done/`, `work_done/`)

| 보고서 | 주장 범위 | 코드 대조 결과 | 분류 |
|--------|----------|--------------|------|
| `Phase2_completion_summary.md` | FE-PR-1~6 완료 + §8에 Phase 3 원안 명시 | FE-PR-1~6 ✅ / §8 Phase 3 원안 ❌ 미구현 | **A** (PR-1~6) |
| `FE-PR-1_routing_common_components.md` | 라우팅 6 + 공통 5 + authAxios | 전부 존재 | **A** |
| `FE-PR-2_thesis_list_page.md` | `/thesis` 목록 3섹션 | `list/` 3컴포넌트 + page.tsx | **A** |
| `FE-PR-3_plan_review_v3.md` | 빌더 구현 계획 리뷰 (H1~H6) | 후속 구현 반영 | **A** |
| `FE-PR-3_builder_implementation.md` | `/thesis/new` 6단계 빌더 | `builder/` 9컴포넌트 + page.tsx | **A** |
| `FE-PR-4_indicator_setup.md` | `/thesis/[id]/indicators` + Route Group | `indicators/` 3컴포넌트 + `(list)` 그룹 | **A** |
| `FE-PR-5_dashboard.md` | `/thesis/[id]` 관제실 | 구현됨(단 OverallMoon/DashboardIndicatorCard는 PR-9 리디자인에서 **삭제됨**) | **A→대체** |
| `FE-PR-6_alerts_close_qa.md` | `/thesis/alerts` + `/close` + API 정합 | `alerts/` 3 + `close/` 2 컴포넌트 | **A** |
| `work_done/phase_a_llm_builder.md` | LLM 빌더 백엔드 (테스트 104) | `services/` 5신규 + FE 분기 | **A** |

> **주의**: `FE-PR-5_dashboard.md`가 완료라 보고한 `OverallMoon.tsx` / `DashboardIndicatorCard.tsx` / `RecentChange.tsx`는 **현재 디렉토리에 존재하지 않는다.** 리디자인 PR-9의 "레거시 삭제" 단계가 실제로 수행되어 `RealValueIndicatorCard` / `IndividualMiniCharts` / `AISummarySection`으로 대체되었음을 코드가 확증한다(보고서 ↔ 코드 정합).

---

## 3. Phase 3 항목별 상세 (A/B/C/D 판정)

### 3-1. 리디자인 트랙 (`thesis_control_phase3_frontend_redesign.md`) — 실제로 진행된 트랙

#### FE-PR-7 (백엔드 확장) — **A 완전 구현**
| 설계 요구 산출물 | 코드 증거 | 판정 |
|-----------------|----------|------|
| `ThesisIndicator.display_unit` 필드 | `models/indicator.py` 필드 존재 + 마이그레이션 `0004_add_display_unit.py` | ✅ A |
| display_unit 데이터 마이그레이션 | `0005_populate_display_unit.py` 존재 | ✅ A |
| `DashboardView` raw_value/change_pct 확장 | `views/monitoring_views.py` DashboardView | ✅ A |
| `IndicatorReadingsView` (`/readings/?days=`) | `views/monitoring_views.py` + `urls.py` 라우트 등록 | ✅ A |
| `_infer_unit()` fallback | 설계 명세대로 구현 추정(View 내) | ✅ A |

#### FE-PR-8 (실제값 카드 + AI 분석) — **A 완전 구현**
| 설계 요구 산출물 | 코드 증거 | 판정 |
|-----------------|----------|------|
| `RealValueIndicatorCard.tsx` | `dashboard/RealValueIndicatorCard.tsx` 존재 (QoQ/YoY + 스파크라인 포함) | ✅ A |
| `AISummarySection.tsx` | `dashboard/AISummarySection.tsx` 존재 | ✅ A |
| `NotableChangesSection.tsx` | `dashboard/NotableChangesSection.tsx` 존재 | ✅ A |
| 타입 확장 (raw_value/notable_changes/ChartPeriod) | `lib/thesis/types.ts` | ✅ A |
| `formatRawValue/formatChangePct/supportLabel` | `lib/thesis/utils.ts` | ✅ A |
| Mock 확장 (ai_summary/notable_changes) | `lib/thesis/mock.ts` | ✅ A |

#### FE-PR-9 (미니차트 + 기간선택 + 레거시 정리) — **A 완전 구현**
| 설계 요구 산출물 | 코드 증거 | 판정 |
|-----------------|----------|------|
| `ChartToggleButton.tsx` | `dashboard/ChartToggleButton.tsx` 존재 | ✅ A |
| `PeriodSelector.tsx` | `dashboard/PeriodSelector.tsx` 존재 | ✅ A |
| `IndividualMiniCharts.tsx` | `dashboard/IndividualMiniCharts.tsx` 존재 (recharts AreaChart) | ✅ A |
| `CHART_COLORS` / `PERIOD_OPTIONS` 상수 | `lib/thesis/constants.ts` | ✅ A |
| 레거시 3종 삭제 (OverallMoon/DashboardIndicatorCard/RecentChange) | 3파일 모두 **부재 확인** = 삭제 완료 | ✅ A |
| (추가) `QuarterlySparkline.tsx` | 설계 외 추가 산출물 — 분기 데이터 시각화 | ✅ (보너스) |

#### FE-PR-10 (AI 모니터링 파이프라인) — **B 부분 구현**
| 설계 요구 산출물 | 코드 증거 | 판정 |
|-----------------|----------|------|
| `generate_thesis_summaries` Celery task | `tasks/summary.py` 구현 + 멱등(force) 처리 | ✅ A |
| Beat 스케줄 등록 | `config/celery.py` `thesis-generate-summaries` 매일 18:35 ET(평일) | ✅ A |
| LLM 프롬프트 (수학엔진+뉴스 키워드) | `summary.py` 내 구현 | ✅ A(추정) |
| `notable_changes` 자동 생성 (alert_engine→NotableChange 변환) | snapshot_builder/eod_pipeline에 변환 로직 명시 확인 안 됨 | ⚠️ **B (미확정)** |

> **B 사유**: `ai_summary` 자동 생성은 task+beat 모두 확인됨. 그러나 설계가 함께 요구한 `notable_changes`의 alert 이벤트 → NotableChange 포맷 변환·저장 로직은 이번 감사에서 명확히 확인되지 않음 → 별도 검증 필요.

#### FE-PR-11 (Weekly Health Check) — **C 미구현 (설계상으로도 "향후")**
| 설계 요구 산출물 | 코드 증거 | 판정 |
|-----------------|----------|------|
| `weekly_health_check` Celery task | 없음 | ❌ C |
| 전제 재검토 제안 / 지표 중복 경고 / 커버리지 알림 | 없음 | ❌ C |

> 설계 문서 자체가 PR-11을 "향후 확장(설계만)"으로 명시했으므로 **계획 대비 갭은 아님**. 단 미구현 상태.

---

### 3-2. 원안 트랙 (`Phase2_completion_summary.md` §8) — 폐기/미구현 항목 상세

> 사용자 메모리·CLAUDE.md의 "Phase 3 (깊이+회고+프로필)" 문구가 가리키는 원안. **리디자인으로 대체되어 프론트 산출물이 전무하다.**

| 원안 PR | 설계 요구 산출물 | 코드 증거 | 판정 |
|---------|-----------------|----------|------|
| FE-PR-7 (원안) | 대시보드 3탭 구조(관제/상세/히스토리) + 전제 CRUD | 탭 구조 컴포넌트 없음 (단일 페이지) | **D 폐기** |
| FE-PR-8 (원안) | **Finviz 스타일 히트맵** + 지표 weight/direction 편집 | `HeatmapCell`/`HeatmapData` 타입 + mock(`mock.ts:614`)만 잔존, **렌더 컴포넌트 0건** | **D 폐기 (데드 타입 잔재)** |
| FE-PR-9 (원안) | **히스토리 탭** (recharts 라인 + 스냅샷 타임라인) | 스냅샷 타임라인 화면 없음 (미니차트로 일부 대체) | **C/D** |
| FE-PR-10 (원안) | **마감 아카이브** 목록 + **ValidityMatrix** UI | 마감 아카이브 라우트 없음(`close/`만 존재), ValidityMatrix UI 없음 | **C 미구현** |
| FE-PR-11 (원안) | **투자자 DNA 프로필** 화면 (AccuracyRing + CategoryChart) | 프로필 라우트·컴포넌트 0건 | **C 미구현** |

**프론트 라우트 실측** (`frontend/app/thesis/`): `(list)`, `(list)/alerts`, `new`, `[thesisId]`, `[thesisId]/close`, `[thesisId]/indicators` — **프로필/아카이브/히스토리/히트맵 라우트 없음.**

---

### 3-3. 회고·프로필 백엔드 기록 계층 — **B (백엔드만, 노출 없음)**

| 설계 개념 | 백엔드 구현 | API 노출 | 프론트 | 종합 판정 |
|----------|-----------|---------|--------|----------|
| **회고 (이벤트 스트림)** | `HypothesisEvent` 모델 (12종 event_type) — 마감 시 기록 | ❌ 조회 API 없음 | ❌ 없음 | **B (데드 계층)** |
| **회고 (유효성 기록)** | `ValidityRecord` + `_compute_validity_score` (2×2) — 마감 시 생성 | ❌ 없음 | ❌ ValidityMatrix UI 없음 | **B** |
| **프로필 (투자자 DNA)** | `InvestorDNA` 모델 + `_update_investor_dna()` — 마감 시 갱신 (accuracy_rate/top_down_ratio 계산 필드) | ❌ GET 엔드포인트 없음 (`urls.py` 무) | ❌ 프로필 화면 없음 | **B (데드 계층)** |

> **판정 근거**: `InvestorDNA`·`ValidityRecord`는 `views/thesis_views.py`의 가설 **마감(close) 액션 내부에서만** 쓰기 호출되며, `thesis/urls.py`에 이를 **읽는 라우트가 단 하나도 없다**. 즉 데이터는 축적되나 사용자에게 노출되지 않는 "쓰기 전용 데드 계층"이다. 원안 Phase 3의 "회고+프로필"은 백엔드 토대만 깔리고 **표현 계층이 통째로 빠진 상태**.

---

### 3-4. 로드맵 Phase 3 (합성 에이전트 + 자동학습) — **C 미구현**

| 설계 요구 (integrated_roadmap §3.0) | 코드 증거 | 판정 |
|-------------------------------------|----------|------|
| 합성 투자자 페르소나 부트스트랩 (20~30 persona LLM 시뮬레이션) | 없음 | ❌ C |
| Online Logistic Regression (전제 가중치 자동학습) | 없음 (가중치 정적) | ❌ C |
| 합성/실제 데이터 블렌딩 (50건 후 합성 0) | `is_synthetic` 필드 없음 | ❌ C |
| 3차원 ValidityScore (thesis_type × indicator × regime) | 단순 2×2 `_compute_validity_score`만 존재 | ❌ C (1×축소 구현) |

---

## 4. 데드 코드·잔재 (정리 후보)

| 항목 | 위치 | 성격 |
|------|------|------|
| `HeatmapCell` / `HeatmapData` 타입 | `lib/thesis/types.ts:150-168` | 원안 히트맵 폐기 후 **렌더 소비처 없는 데드 타입** |
| `heatmap` mock 블록 | `lib/thesis/mock.ts:614` | 데드 mock |
| `InvestorDNA` / `HypothesisEvent` 노출 부재 | `models/learning.py` | 쓰기만 되고 읽는 API/화면 없음 (의도된 미래 계층일 수 있음) |

> ⚠️ 본 감사는 읽기 전용이므로 삭제하지 않음. 정리 시 별도 PR 권장.

---

## 5. 결론 및 권고 (감사 의견)

1. **명명 혼선 해소가 최우선.** `FE-PR-7~11`이 두 문서에서 정반대 의미로 쓰여, 메모리·CLAUDE.md의 "Phase 3 (깊이+회고+프로필) 진행 중" 표기가 **실제 코드 상태(실제값 리디자인 완료)와 불일치**한다. → `DECISIONS.md`에 "Phase 3 원안(깊이+회고+프로필)은 실제값 리디자인으로 대체됨"을 1줄 명문화 권장.

2. **실제값 리디자인은 사실상 완료.** PR-7·8·9 = A, PR-10 = B(notable_changes 변환만 재확인 필요), PR-11 = 설계상 향후. → CLAUDE.md "구현 상태"를 **"Phase 3 리디자인 완료, 원안 보류/폐기"**로 갱신 권장.

3. **회고·프로필은 '백엔드만' 존재하는 데드 계층.** `InvestorDNA`/`ValidityRecord`/`HypothesisEvent`가 축적되지만 노출 API·화면이 0건. 향후 "프로필" 기능을 살리려면 **GET 엔드포인트 + 프론트 라우트 신설**이 필요(현재 가장 큰 미구현 갭).

4. **로드맵 Phase 3(자동학습)은 미착수.** 합성 에이전트·Online LR은 흔적 없음. 가중치는 정적, ValidityScore는 2×2 축소판.

### 갭 요약 한 줄
> **백엔드 관제 엔진·핵심 루프·LLM 빌더·실제값 리디자인 = 구현 완료(A). 원안 "깊이+회고+프로필"의 표현 계층(히트맵/히스토리 탭/마감 아카이브/DNA 프로필 화면) = 전무(C/D). 회고·프로필 데이터 토대는 백엔드에 깔려 있으나 노출 0건(데드 계층, B).**

---

*본 보고서는 코드 무수정 읽기 전용 감사이며, 일부 항목(PR-10 notable_changes 변환, _infer_unit 세부)은 파일 내부 로직 정밀 검증 시 A로 승격될 수 있음.*
