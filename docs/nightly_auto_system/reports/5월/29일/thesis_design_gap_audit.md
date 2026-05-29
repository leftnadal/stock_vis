# Thesis Control 설계 갭 감사

> 감사일: 2026-05-30
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` (백엔드) + `frontend/components/thesis/` · `frontend/app/thesis/` · `frontend/lib/thesis/` (프론트엔드)
> 모드: 읽기 전용 (코드 미수정)
> 방법: 설계 문서 8종 정독 + 백엔드/프론트엔드 코드 인벤토리 교차 대조

---

## 0. 핵심 발견 — "Phase 3"가 3가지 의미로 충돌

이 감사에서 가장 중요한 구조적 문제는 **"Phase 3"라는 용어가 서로 다른 3개의 계획을 동시에 가리킨다**는 점이다. 사용자 지시("Phase 3 = 깊이 + 회고 + 프로필")는 그중 ②번을 지목하지만, 코드에 실제로 들어간 것은 ③번이다.

| 라벨 | 출처 문서 | 내용 | 구현 상태 |
|------|----------|------|----------|
| **Phase 3-①** (백엔드 학습) | `plan/thesis_control_integrated_roadmap.md` §3 | 합성 에이전트 부트스트래핑 + Online Logistic Regression + 합성/실제 블렌딩 | ❌ **미구현 (0%)** |
| **Phase 3-②** (FE 깊이+회고+프로필) | `frontend/task_done/Phase2_completion_summary.md` §8 | FE-PR-7~11: 탭 구조 + 히트맵 + 히스토리 + 마감 아카이브 + 투자자 DNA 프로필 | ❌ **거의 미구현 (~10%)** |
| **Phase 3-③** (대시보드 리디자인) | `plan/thesis_control_phase3_frontend_redesign.md` (v1.0 FINAL) | PR-7~10: 실제값 카드 + AI 요약 + 미니차트 (달위상/내부점수 제거) | ✅ **구현 완료 (PR-7~10 전부)** |

> **충돌 지점**: `Phase2_completion_summary.md`(2026-03-16)는 FE-PR-7~11을 "깊이+회고+프로필"로 정의했으나, 이틀 뒤 작성된 `thesis_control_phase3_frontend_redesign.md`(2026-03-18, v1.0 FINAL)가 **같은 PR 번호(PR-7~10)를 전혀 다른 작업(대시보드 리디자인)에 재할당**했다. 실제 코드는 후자(③)를 따라갔고, 전자(②)의 FE-PR-7~11은 사실상 폐기 또는 미착수 상태로 남았다.
> → **권고**: ②와 ③ 중 어느 것이 현행 로드맵인지 단일 문서로 정본화 필요. 현재 두 문서 모두 `task_done`/`plan`에 살아있어 다음 작업자가 혼동할 위험이 크다.

---

## 1. 요약 (Phase별 구현률)

| Phase | 정의 | 구현률 | 비고 |
|-------|------|--------|------|
| **Phase 1 (MVP / 관제 엔진)** | Stage 0~3 수학엔진 + 이벤트 수집 + ValidityRecord + InvestorDNA 골격 | **~90% (A)** | 핵심 모델·서비스·태스크 전부 구현. `is_synthetic` 필드만 누락 |
| **Phase 2 (유효성 활성화 + DNA 슬라이더)** | ValidityScore 집계 + 지표추천 개인화 + 역제안 넛지 | **~0% (C)** | ValidityScore 모델 자체 부재. 개인화 로직 전무 |
| **Phase 3-① (백엔드 학습)** | 합성 에이전트 + Online LR + 블렌딩 | **0% (C)** | 흔적 없음 |
| **Phase 3-② (FE 깊이+회고+프로필, FE-PR-7~11)** | 탭/히트맵/히스토리/아카이브/DNA 프로필 | **~10% (C)** | 거의 전부 미구현. 일부 mock 데이터 구조만 잔존 |
| **Phase 3-③ (대시보드 리디자인, PR-7~10)** | 실제값 카드·AI요약·미니차트 | **100% (A)** | 백엔드 PR-7 + FE PR-8/9 + Celery PR-10 모두 완료 |
| **Phase 4 (벡터 스코어링)** | DNA 벡터화 + 코사인 유사도 | **0% (C)** | 로드맵상 최후순위, 미착수 정상 |
| **번외: Phase A LLM 빌더** (`work_done/phase_a_llm_builder.md`) | one-shot 제안형 빌더 (3턴) | **100% (A)** | MVP+Hardening 완료, 104 테스트 통과 |

**전체 그림**: Phase 1 관제 엔진과 Phase 3-③ 대시보드 리디자인, 그리고 번외 LLM 빌더는 견고하게 완성됨. 반면 **"지능이 시간이 지날수록 강해진다"는 특허 차별화의 핵심(Phase 2 유효성 활성화 + Phase 3-① 학습)은 데이터 기록만 하고 활용 단계로 진입하지 못한 상태**다. 사용자가 지목한 "깊이+회고+프로필"(Phase 3-②)도 거의 미착수다.

---

## 2. 문서별 상태 테이블

분류: **(A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체**

| 설계 문서 | 정의 내용 | 분류 | 근거 |
|-----------|----------|------|------|
| `plan/thesis_control_design.md` | Thesis Control 전체 설계 (관제 엔진 기반) | **A** | 모델·서비스·뷰·태스크 전반 구현 확인 |
| `plan/thesis_control_math_model_final.md` | 수학모델 v2.3.2 (Stage 0~3) | **A** | `eod_pipeline.py` 3태스크 + scoring 서비스 구현 |
| `plan/thesis_control_implementation_guide.md` | 구현 가이드 | **A** | 실제 코드 구조와 일치 |
| `thesis_control_user_experience.md` | UX 흐름 (목록→빌더→설정→대시보드→알림→마감) | **A** | FE-PR-1~6 핵심 루프 완성 |
| `thesis_control_phase1_frontend_FE_PR_1~5.md` | Phase1 FE 라우팅·목록·빌더·지표·대시보드 | **A** | `frontend/app/thesis/` 라우트 6종 + 컴포넌트 40개 |
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 FE 완료 보고서 6건 | **A** | 보고서 cross-ref 일치 (단, FE-PR-5 OverallMoon은 ③에서 사후 삭제됨) |
| `plan/thesis_control_phase3_frontend_redesign.md` | **Phase 3-③** 대시보드 리디자인 (PR-7~10) | **A** | 아래 §3-③ 상세. 9/9 산출물 구현 + 삭제 대상 3종 실제 삭제 |
| `work_done/phase_a_llm_builder.md` | LLM one-shot 빌더 | **A** | `prompt_builder.py`/`builder_state.py`/`thesis_builder.py` 등 22파일 |
| `plan/talking_builder/redesign_build_plan/*` | 빌더 리디자인 (Phase A~C) | **B** | Phase A·B 완료, Phase C(MiniDashboard/스트리밍) 미확인 |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 대시보드 | **B** | `QuarterlySparkline.tsx` + `quarterly_metric_fetcher.py` 존재 |
| `plan/thesis_control_integrated_roadmap.md` §1 (Phase 1) | 이벤트/유효성/DNA 골격 | **B** | 아래 §3 상세. `is_synthetic` 누락 |
| `plan/thesis_control_integrated_roadmap.md` §2 (Phase 2) | ValidityScore + DNA 슬라이더 + 역제안 | **C** | ValidityScore 모델·서비스 전무 |
| `plan/thesis_control_integrated_roadmap.md` §3 (**Phase 3-①**) | 합성 에이전트 + Online LR | **C** | 흔적 없음 |
| `plan/thesis_control_integrated_roadmap.md` §4 (Phase 4) | 벡터 스코어링 | **C** | 미착수 (정상) |
| `frontend/task_done/Phase2_completion_summary.md` §8 (**Phase 3-②** FE-PR-7~11) | 탭/히트맵/히스토리/아카이브/DNA 프로필 | **C/D** | 거의 미구현 + PR번호가 ③에 재할당되어 사실상 폐기 가능성 |

---

## 3. Phase별 항목 상세

### 3-A. Phase 1 (MVP / 관제 엔진) — 분류 B (~90%, 1건 누락)

| # | 설계 항목 | 분류 | 근거 |
|---|----------|------|------|
| 1 | HypothesisEvent 모델 (13개 event_type) | A | `thesis/models/learning.py:7-52` |
| 2 | ValidityRecord 모델 | **B** | `thesis/models/learning.py:55-94` — **`is_synthetic` 필드 누락** (로드맵 §3.1에서 Phase 3 합성데이터 구분용으로 요구) |
| 3 | InvestorDNA 모델 (+ 3 property) | A | `thesis/models/learning.py:97-152` (accuracy_rate/ai_accept_rate/top_down_ratio 전부) |
| 4 | ThesisSnapshot.ai_summary / notable_changes | A | `thesis/models/monitoring.py:25-26` |
| 5 | Stage 0~3 수학엔진 + Celery 3태스크 | A | `thesis/tasks/eod_pipeline.py` (update_indicator_readings:272 / calculate_scores:374 / create_snapshots_and_alerts:471) |
| 6 | 마감 시 ValidityRecord 생성 + InvestorDNA 갱신 | A | `thesis/views/thesis_views.py:86-103` (ValidityRecord), `:295-336` (`_update_investor_dna`) |

> Phase 1은 사실상 완성. 유일한 갭은 `ValidityRecord.is_synthetic`인데, 이는 Phase 3-① 합성 에이전트 도입 시점에 추가하면 되는 항목이라 현 단계에서는 영향 없음.

### 3-③. Phase 3 대시보드 리디자인 (PR-7~10) — 분류 A (100%)

> 사용자가 "Phase 3"로 인지하지 않았을 수 있으나, **실제 코드에 반영된 유일한 Phase 3**.

| # | 산출물 | 분류 | 근거 |
|---|--------|------|------|
| PR-7 | `ThesisIndicator.display_unit` 필드 | A | `thesis/models/indicator.py:73-76` |
| PR-7 | `IndicatorReadingsView` + URL | A | `thesis/views/monitoring_views.py:260-290`, `thesis/urls.py:30-33` |
| PR-7 | DashboardView raw_value/change_pct/ai_summary/notable_changes | A | `monitoring_views.py:161-164, 216-217` |
| PR-8 | RealValueIndicatorCard / AISummarySection / NotableChangesSection | A | `frontend/components/thesis/dashboard/` 3종 존재 + 사용 |
| PR-8 | utils: formatRawValue/formatChangePct/supportLabel | A | `frontend/lib/thesis/utils.ts:136-176` |
| PR-8 | types: NotableChange/IndicatorReadingPoint/IndicatorReadingsResponse/ChartPeriod | A | `frontend/lib/thesis/types.ts:334-363` |
| PR-9 | ChartToggleButton / PeriodSelector / IndividualMiniCharts | A | dashboard/ 3종 + `useAllIndicatorReadings` (`queries.ts:73-89`) |
| PR-9 | 삭제 대상 OverallMoon/DashboardIndicatorCard/RecentChange | A | grep 결과 파일·import 모두 부재 = 설계대로 삭제 완료 |
| PR-10 | `generate_thesis_summaries` Celery 태스크 | A | `thesis/tasks/summary.py:79-142` (Gemini 동기 호출) |

> 설계서 §10 "절대 하지 말 것"(dashboardV2 별도 메서드 금지, Zustand 금지 등)도 위반 없이 준수됨.

### 3-②. Phase 3 깊이+회고+프로필 (FE-PR-7~11) — 분류 C (~10%) ★사용자 지목 항목★

| # | 설계 항목 (Phase2_summary §8) | 분류 | 근거 / 갭 |
|---|------|------|----------|
| FE-PR-7 | 대시보드 **3탭 구조**(관제/상세/히스토리) + **전제 CRUD** | **C** | 탭 컴포넌트 없음. `[thesisId]/page.tsx`는 단일 순차 렌더. 대시보드 내 전제 추가/수정/삭제 UI 없음 (`builder/PremiseCard.tsx`는 빌더 전용) |
| FE-PR-8 | **Finviz 스타일 히트맵** + 지표 weight/direction 편집 | **B(미약)** | `mock.ts`에 `heatmap` 데이터 구조만 존재. 렌더링 컴포넌트·편집 UI 없음. `IndicatorSetupCard`는 추가/삭제/토글만 |
| FE-PR-9 | **히스토리 탭** (recharts 라인차트 + 스냅샷 타임라인) | **C** | `[thesisId]/history` 라우트 없음. 스냅샷 타임라인 컴포넌트 없음 |
| FE-PR-10 | **마감 아카이브** + ValidityMatrix | **B(미약)** | `[thesisId]/close` 마감 기능만 구현. 마감 가설 아카이브 목록·ValidityMatrix 컴포넌트 없음 |
| FE-PR-11 | **투자자 DNA 프로필** (AccuracyRing + CategoryChart) | **C** | profile 라우트 없음. AccuracyRing/CategoryChart 컴포넌트 없음. **백엔드 InvestorDNA 모델은 있으나 조회 API조차 없어 프론트 연동 불가** |

### 3-②/①. Phase 2 + Phase 3-① 백엔드 학습 레이어 — 분류 C (0%)

> "시간이 지날수록 강해지는 지능" = 특허 독립항 2·3의 핵심. **데이터 기록(Phase 1)은 되고 있으나 활용(Phase 2+)으로 넘어가지 못함.**

| # | 설계 항목 | 분류 | 갭 |
|---|----------|------|-----|
| P2-1 | **ValidityScore 모델** (cumulative_score/sample_count/confidence/is_active) | **C** | 모델 정의·마이그레이션 전무 |
| P2-2 | ValidityRecord→ValidityScore 주간 집계 Celery 태스크 | C | 없음 |
| P2-3 | indicator_matcher 유효성 점수 반영 (validity_boost, core/reference 티어) | C | `indicator_matcher.py`는 키워드룰+Gemini fallback만 |
| P2-4 | DNA 적합도 슬라이더 (apply_dna_personalization) | C | 없음. `personalization_weight` 필드는 모델에 존재하나 미사용 |
| P2-5 | 역제안 넛지 (add_contrarian_nudge) | C | 없음 |
| P3①-1 | **SyntheticBootstrapper** (합성 에이전트 부트스트래핑) | C | 없음 — 특허 독립항 3 신규 청구요소 |
| P3①-2 | **ThesisWeightLearner** (Online Logistic Regression) | C | 없음 |
| P3①-3 | aggregate_validity_scores 합성/실제 블렌딩 | C | 없음 (ValidityScore 부재로 불가) |
| P3①-4 | InvestorDNA 조회 API / 프로필 엔드포인트 | C | `urls.py`에 profile/dna 경로 없음. 마감 시 갱신만 되고 노출 경로 없음 |
| P3①-5 | 마감 아카이브 / ValidityMatrix API | C | 없음 |

---

## 4. 종합 권고

1. **"Phase 3" 용어 정본화 (최우선)** — `integrated_roadmap`(①), `Phase2_completion_summary §8`(②), `phase3_frontend_redesign`(③)이 모두 "Phase 3"·"PR-7~10"을 쓴다. 단일 진실 소스를 정하고 나머지는 `[SUPERSEDED]`/`[폐기]` 표기. 그렇지 않으면 다음 작업자가 PR 번호로 작업을 식별할 수 없다.

2. **사용자 지목 항목(Phase 3-② 깊이+회고+프로필)이 거의 미착수**임을 명확히 인지 — CLAUDE.md "진행 중: Thesis Control Phase 3(깊이+회고+프로필 FE-PR-7~11)" 기재와 실제 코드(~10%) 사이에 큰 괴리. 5건 중 완전 구현 0건, 미약 부분구현 2건(히트맵 mock·마감 close), 미구현 3건(탭·히스토리·DNA 프로필).

3. **DNA 프로필은 백엔드 우선** — InvestorDNA 모델·마감 시 갱신 로직은 이미 있으나 **조회 API가 없어** FE-PR-11(프로필 화면)을 시작할 수 없다. FE 착수 전 `InvestorDNA` GET 엔드포인트 신설이 선행 조건.

4. **특허 차별화 핵심(Phase 2 유효성 활성화)이 데이터 기록 단계에 정체** — ValidityRecord는 마감마다 쌓이고 있으나 집계(ValidityScore)·활용(개인화 추천)이 없어 "쌓기만 하고 안 쓰는" 상태. 가설 마감 N건 축적 여부를 확인하고 Phase 2 집계 태스크 착수 시점 판단 필요.

5. **`ValidityRecord.is_synthetic` 누락**은 Phase 3-① 합성 에이전트 착수 시 데이터 마이그레이션을 동반하므로, Phase 2 모델 작업 시 함께 추가 검토.

---

## 부록: 조사 커버리지

- 정독 설계 문서: `phase3_frontend_redesign.md`, `integrated_roadmap.md`, `Phase2_completion_summary.md`, `phase_a_llm_builder.md` 전문 + 나머지 14개 문서 grep 교차참조
- 백엔드 인벤토리: `thesis/models/` 6파일, `thesis/services/` 22파일, `thesis/views/` 3파일, `thesis/tasks/` 2파일, `thesis/urls.py`
- 프론트엔드 인벤토리: `frontend/app/thesis/` 라우트 6종, `frontend/components/thesis/` 40파일, `frontend/lib/thesis/` 9모듈
- 미조사(범위 외): scoring 서비스 내부 수식 정합성, 테스트 커버리지 수치, Celery Beat 스케줄 실등록 여부
