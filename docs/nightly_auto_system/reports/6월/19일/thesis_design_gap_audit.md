# Thesis Control 설계 갭 감사

> 감사일: 2026-06-20 (야간 자동 시스템)
> 대상 소스: `/Users/byeongjinjeong/Desktop/stock_vis`
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드)
> 성격: **읽기 전용 감사. 코드 수정 없음.**

---

## 0. 가장 중요한 발견 — "Phase 3"는 4개 문서에서 서로 다른 뜻 (용어 drift)

이 감사의 핵심 결론. "Thesis Control Phase 3"라는 표현이 **4개의 다른 의미**로 쓰이고 있어, "Phase 3 진행 중"이라는 CLAUDE.md 기술이 실제 코드와 어긋난다.

| 출처 | "Phase 3"의 정의 | 실제 구현 상태 |
|------|------------------|---------------|
| **A. `design.md §7`** | 커뮤니티 + 고도화 (인기 가설, 팔로우, 템플릿, Chain Sight 연동, 마감 복기, Neo4j 가설 그래프) | ❌ 거의 미구현 |
| **B. `integrated_roadmap.md §3`** | 합성 에이전트 부트스트래핑 + Online LR 가중치 학습 + 합성/실제 블렌딩 | ❌ 미구현 |
| **C. `Phase2_completion_summary.md §8` (= CLAUDE.md "깊이+회고+프로필 FE-PR-7~11")** | FE-PR-7 탭구조 / FE-PR-8 히트맵 / FE-PR-9 히스토리탭 / FE-PR-10 마감아카이브+ValidityMatrix / FE-PR-11 투자자 DNA 프로필 | ❌ 미구현 (대체됨) |
| **D. `phase3_frontend_redesign.md` (PR-7~10)** | 대시보드 리디자인 — 내부 점수 숨기고 **실제 값**(환율/VIX/지수) 표시 + AI 요약 + 미니차트 | ✅ **완전 구현** |

**결론**: 실제로 구현된 "Phase 3"는 **D(대시보드 리디자인)**이다. CLAUDE.md가 "진행 중"으로 표기한 **C(깊이+회고+프로필 FE-PR-7~11)**는 D로 **방향 전환(pivot)되어 폐기·대체**되었고, 개별 항목은 미구현 상태로 남아 있다. 즉 **CLAUDE.md 구현 상태 표기가 stale**이다.

---

## 1. 요약 — Phase별 / 트랙별 구현률

Thesis Control은 단일 Phase 축이 아니라 **3개의 병행 트랙**으로 진행됐다. 트랙별로 보아야 정확하다.

### 트랙 1 — 관제 엔진 + 핵심 UX 루프 (design.md Phase 1~2)
| 구간 | 구현률 | 비고 |
|------|--------|------|
| Phase 1 기반 구조 (CRUD, 빌더, 화살표 엔진, 카드 대시보드, EOD Celery) | **~100% (A)** | models/views/services/tasks 전부 존재 |
| Phase 2 모니터링 강화 (스냅샷, 알림 11종, AI 요약, 실제값 대시보드) | **~95% (A)** | snapshots/explanation 전용 엔드포인트만 누락 |

### 트랙 2 — LLM 대화형 빌더 재설계 (talking_builder v4)
| 구간 | 구현률 | 비고 |
|------|--------|------|
| Phase A-MVP (PR-1~3) one-shot proposal | **100% (A)** | `thesis_builder.py`, `prompt_builder.py` 등 |
| Phase A-Hardening (PR-4~7) | **100% (A)** | `builder_stats` command 포함 |
| Phase B (PR-8~12) Keyword Enrichment | **~90% (A)** | `keyword_cache`, `keyword_collectors/`, `keyword_hint` 존재. PR-12 멀티턴(선택)만 불명 |
| Phase C (C-1~8) 고급 (Health Report, 스트리밍) | **0% (C)** | 미착수 |

### 트랙 3 — 대시보드 리디자인 (phase3_frontend_redesign PR-7~10)
| PR | 구현률 | 증거 |
|----|--------|------|
| PR-7 백엔드 (display_unit, IndicatorReadingsView) | **100% (A)** | migration 0004/0005, `IndicatorReadingsView` urls 등록 |
| PR-8 실제값 카드 + AI 요약 | **100% (A)** | `RealValueIndicatorCard`, `AISummarySection`, `NotableChangesSection` |
| PR-9 미니차트 + 기간 선택 | **100% (A)** | `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`, `QuarterlySparkline` |
| PR-10 AI 파이프라인 (generate_thesis_summaries) | **100% (A)** | `thesis/tasks/summary.py` |

### 미구현 트랙 (설계만 존재)
| 트랙 | 구현률 | 비고 |
|------|--------|------|
| 학습/개인화 Phase 2~4 (ValidityScore, DNA 슬라이더, 합성 에이전트, 벡터) | **~5% (C)** | Phase 1 골격(HypothesisEvent/ValidityRecord/InvestorDNA)만 존재 |
| 커뮤니티 (인기 가설, 팔로우, 템플릿) | **~10% (B)** | 모델만 존재, API/FE 0 |
| 원래 FE-PR-7~11 (탭/히트맵/히스토리/아카이브/DNA프로필) | **0% (D)** | 대시보드 리디자인으로 대체 |

---

## 2. 문서별 상태 테이블

| 문서 | 정의한 범위 | 코드 대조 결과 | 분류 |
|------|------------|---------------|------|
| `plan/thesis_control_design.md` | 전체 설계 (플로우, 모델, API, Phase 1~4) | 모델/엔진/핵심 API 구현. 커뮤니티·템플릿·snapshots·explanation API 미구현 | **B 부분** |
| `plan/thesis_control_integrated_roadmap.md` | 학습/개인화 레이어 Phase 1~4 | Phase 1 모델(이벤트/유효성/DNA)만. Phase 2~4 전무 | **B 부분** |
| `plan/thesis_control_math_model_final.md` | v2.3.2 관제 엔진 (Stage 0~3) | `indicator_scorer`, `premise_aggregator`, `data_validator`, `thesis_state_machine`로 구현 | **A 완전** |
| `plan/thesis_control_phase3_frontend_redesign.md` | 대시보드 리디자인 PR-7~10 | 전 PR 구현 확인 | **A 완전** |
| `plan/talking_builder/llm_builder_plan.md` + `thesis_builder_redesign_v2.md` + `redesign_build_plan/` | LLM 빌더 v4 Phase A/B/C | Phase A·B 구현. Phase C 미착수 | **A(A·B) / C(C)** |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 대시보드 | `quarterly_metric_fetcher.py` + `QuarterlySparkline.tsx` 구현 | **A 완전** |
| `frontend/task_done/FE-PR-1 ~ FE-PR-6` | Phase 2 프론트 핵심 루프 (라우팅/목록/빌더/지표/대시보드/알림/마감) | 6개 라우트 + 40개 컴포넌트 전부 구현 | **A 완전** |
| `frontend/task_done/FE-PR-3_plan_review_v3.md` | 빌더 PR-3 리뷰 | 빌더 구현됨 | **A 완전** |
| `Phase2_completion_summary.md §8` ("Phase 3 계획" FE-PR-7~11) | 탭/히트맵/히스토리/아카이브/DNA프로필 | 전부 미구현, 리디자인으로 대체 | **D 폐기/대체** |
| `work_done/phase_a_llm_builder.md` | LLM 빌더 Phase A 완료 보고 | 코드와 일치 (104 테스트 명시) | **A 완전** |

---

## 3. Phase 3 미구현 항목 상세

"Phase 3"의 4개 정의별로, 미구현/대체 항목을 구체적으로 나열한다.

### 3-A. 원래 FE-PR-7~11 (CLAUDE.md "깊이+회고+프로필") — **전부 미구현, 대시보드 리디자인으로 대체 (D)**

`Phase2_completion_summary.md §8`에 명시된 원래 5개 PR. 실제 코드에 대응 컴포넌트/페이지 **없음**.

| 원 계획 | 설계 내용 | 코드 현황 | 분류 |
|---------|----------|----------|------|
| FE-PR-7 | 대시보드 **3탭 구조**(관제/상세/히스토리) + 전제 CRUD UI | 대시보드는 **단일 페이지**. 탭 구조 없음. 전제 편집 UI 없음(빌더에서만 생성) | **C 미구현** |
| FE-PR-8 | **Finviz 스타일 히트맵** + 지표 weight/direction 편집 UI | 히트맵 컴포넌트 없음. weight/direction은 모델 필드만 존재, 프론트 편집 화면 없음 | **C 미구현** |
| FE-PR-9 | **히스토리 탭** (스냅샷 타임라인 + recharts) | 스냅샷 타임라인 화면 없음. 대신 PR-9 `IndividualMiniCharts`가 지표별 readings 차트 제공(다른 기능) | **C 미구현 (부분 대체)** |
| FE-PR-10 | **마감 아카이브** 목록 + **ValidityMatrix** 2×2 시각화 | 마감 **실행** 페이지(`/close`)는 있으나, 마감된 가설 **아카이브 목록**·ValidityMatrix 뷰 없음 | **B 부분 (마감만)** |
| FE-PR-11 | **투자자 DNA 프로필** (AccuracyRing + CategoryChart) | `InvestorDNA` 모델은 존재(백엔드 집계). **프로필 조회 API 없음, 프론트 화면 0** | **C 미구현** |

> **회고(retrospective) 판정**: 별도 회고 화면·모델 없음. 마감 시 `outcome` + `outcome_note`(메모) 수집 + `ValidityRecord` 1건 생성이 전부. "복기 시스템"은 데이터 기록 수준이며 사용자향 회고 UX는 미구현.
> **프로필 판정**: 데이터 레이어(`InvestorDNA`, `accuracy_rate`/`ai_accept_rate`/`top_down_ratio` 프로퍼티)만 존재. 노출 경로(API·화면) 전무.
> **깊이(depth) 판정**: depth/level 개념의 모델·필드·화면 모두 **전무**.

### 3-B. design.md §7 Phase 3 (커뮤니티 + 고도화) — **모델만, API/FE 미구현 (B/C)**

| 항목 | 설계 (design.md) | 코드 현황 | 분류 |
|------|------------------|----------|------|
| 인기 가설 | `GET /popular/`, `GET /popular/{id}/detail/` | `PopularThesisCache` 모델 존재. **View/URL 없음** | **B 부분 (모델만)** |
| 가설 따라하기 | `POST /popular/{id}/follow/` | `ThesisFollow` 모델 존재. **View/URL 없음** | **B 부분 (모델만)** |
| 템플릿 시스템 | `GET /templates/`, `/templates/{type}/` | 모델·View·URL 전무. (`PresetSelector`는 모니터링 단기/중기/장기 프리셋이지 가설 템플릿 아님) | **C 미구현** |
| Chain Sight 연동 진입 | 진입 경로 5 | `Thesis.entry_source`에 `chainsight` enum 값만 존재. 진입 플로우 없음 | **C 미구현** |
| 마감 + 복기 시스템 | 마감 복기 | 마감 기록만 (3-A FE-PR-10 참조) | **B 부분** |
| Neo4j 가설 관계 그래프 | 가설 온톨로지 | 코드 미발견 | **C 미구현** |

### 3-C. integrated_roadmap.md Phase 3 (합성 에이전트 + 자동학습) — **전무 (C)**

| 항목 | 설계 | 코드 현황 | 분류 |
|------|------|----------|------|
| `SyntheticBootstrapper` (페르소나 합성 가설) | roadmap §3.1 | 클래스 없음 | **C 미구현** |
| `ThesisWeightLearner` (Online Logistic Regression) | roadmap §3.2 | 없음 | **C 미구현** |
| 합성/실제 데이터 블렌딩 (`is_synthetic` 필드) | roadmap §3.3 | `ValidityRecord`에 `is_synthetic` 필드 없음 | **C 미구현** |
| (선행) Phase 2 `ValidityScore` 테이블 + DNA 슬라이더 + 역제안 | roadmap §2 | 테이블·로직 없음. `personalization_weight`는 미사용 골격 | **C 미구현** |

> Phase 3의 전제조건인 **Phase 2(유효성 활성화)** 자체가 미구현이라, Phase 3는 착수 불가 상태.

### 3-D. design.md API 명세 대비 누락 엔드포인트 (참고)

`urls.py` 대조 결과, 설계에 있으나 미구현된 엔드포인트:

| 설계 엔드포인트 | 상태 |
|----------------|------|
| `GET /{id}/snapshots/` (스냅샷 히스토리) | ❌ 미등록 |
| `GET /{id}/summary/` (AI 요약 단독 조회) | ❌ 미등록 (요약은 dashboard 응답에 포함) |
| `GET /{id}/indicators/{iid}/explanation/` ([근거] 설명) | ❌ 미등록 |
| `GET /daily-issues/` | △ `/conversation/news-issues/`로 대체 구현 |
| `GET /popular/*`, `/templates/*` | ❌ 미등록 (3-B 참조) |
| `POST /conversation/suggest/` | ✅ 구현됨 (`SuggestThesesView`) |

---

## 4. 진입 경로 5종 구현 현황 (design.md §2.3)

| 경로 | 설계 | 구현 | 분류 |
|------|------|------|------|
| 1. 📰 오늘 이슈 (뉴스) | 메인 경로 | `NewsIssuesView` + `EntryPointGrid` + `NewsSelector` | **A** |
| 2. 💬 내 생각 (자유 입력) | 확신 사용자 | LLM one-shot 빌더 | **A** |
| 3. 🔥 인기 가설 | 초보/구경 | 모델만, 진입 플로우 없음 | **C** |
| 4. 📋 템플릿 | 템플릿 선택 | 미구현 | **C** |
| 5. 🔗 Chain Sight | DNA 연동 | enum 값만 | **C** |

핵심 2개 경로(뉴스·자유입력)는 완성, 커뮤니티/탐색성 3개 경로는 미구현.

---

## 5. 종합 판정

- **실제 출시 가능 핵심 루프**(목록→빌더→지표→대시보드→알림→마감)는 **완전 구현**되어 있고, 관제 수학 엔진(v2.3.2)·LLM 빌더·실제값 대시보드까지 **A 등급**.
- **CLAUDE.md의 "진행 중: Phase 3 (깊이+회고+프로필 FE-PR-7~11)" 표기는 부정확**하다. 해당 계획은 대시보드 리디자인(PR-7~10)으로 **대체 완료**되었고, 원래 항목들(탭/히트맵/히스토리/아카이브/DNA프로필 화면)은 **미구현으로 남았다**. → CLAUDE.md 구현 상태 갱신 권장.
- **미구현 영역의 공통점**: 데이터/모델 레이어는 선제적으로 깔려 있으나(`InvestorDNA`, `ValidityRecord`, `HypothesisEvent`, `ThesisFollow`, `PopularThesisCache`), **노출 경로(API + 프론트 화면)가 없어** 사용자에게 도달하지 못한다. 커뮤니티·DNA 프로필·학습 개인화가 여기에 해당.
- **권장 우선순위**(설계 의존성 기준): ① 커뮤니티 API/FE (모델 완비, 노출만) → ② 투자자 DNA 프로필 화면 (집계 완비, 조회 API+화면만) → ③ 학습 Phase 2(ValidityScore 활성화) → ④ 합성 에이전트(Phase 3).

---

## 부록: 분류 기준

- **(A) 완전 구현** — 설계 의도대로 모델·로직·노출(API/UI)까지 동작
- **(B) 부분 구현** — 일부 계층만 존재 (예: 모델만 있고 API/UI 없음)
- **(C) 미구현** — 설계만 존재, 코드 부재
- **(D) 폐기/대체** — 설계가 다른 방향으로 전환되어 원안은 구현되지 않음
