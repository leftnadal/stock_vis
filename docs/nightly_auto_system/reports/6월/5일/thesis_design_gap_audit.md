# Thesis Control 설계 갭 감사

> 감사일: 2026-06-05
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/`(백엔드) + `frontend/**/thesis`(프론트엔드)
> 성격: **읽기 전용 감사** (코드 일절 수정 없음)
> 분류: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체
> 방법: 설계 문서 정독 후 실제 모델·URL·뷰·컴포넌트 인벤토리로 독립 검증 (전일 보고서 재검증 포함)

---

## 0. 가장 중요한 발견 — "Phase 3"·"FE-PR-7~11" 삼중 정의

이 프로젝트에서 **"Phase 3"는 4개 문서가 서로 다른 의미로 사용**하며, **번호 FE-PR-7~11은 두 번 재정의**되었다. CLAUDE.md의 *"Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11) 진행 중"* 표기는 **실제 구현 상태와 불일치**한다. 그 번호가 가리키던 5개 PR은 단 하나도 구현되지 않았고, 실제로 구현된 "Phase 3"는 전혀 다른 트랙(대시보드 리디자인)이다.

| "Phase 3" 출처 | 정의 내용 | 작성일 | 실제 구현 |
|---|---|---|---|
| `design.md` §7 Phase 3 | 커뮤니티 + 고도화 (인기 가설·템플릿·Chain Sight 연동·마감 복기·Neo4j 관계) | 2026-02-27 | ❌ 거의 미구현 (모델만) |
| `Phase2_completion_summary.md` §8 (FE-PR-7~11) | **깊이 + 회고 + 프로필** (탭구조·히트맵·히스토리·마감아카이브·DNA프로필) | 2026-03-16 | ❌ 미구현 (D로 대체) |
| `phase3_frontend_redesign.md` (PR-7~10) | **대시보드 리디자인** (실제값 카드·AI분석·미니차트) | 2026-03-18 | ✅ 구현됨 |
| `integrated_roadmap.md` §3 Phase 3 | 합성 에이전트 + 자동학습 (Online LR·블렌딩) — 특허 레이어 | (특허) | ❌ 미구현 |

### 결정적 타임라인

```
03-16  Phase 2 완료. FE-PR-7~11 = "깊이+회고+프로필"로 계획 수립
        ↓ (2일 후 방향 전환)
03-18  phase3_frontend_redesign.md 작성
        → "달 위상/내부 점수가 매일 똑같은 화면을 만든다" 문제 제기
        → 같은 번호대(PR-7~10)를 "실제 값 대시보드 리디자인"으로 재정의
        → 원래 FE-PR-7~11 (탭/히트맵/히스토리/아카이브/DNA)은 사실상 폐기
03-19  빌더 재설계 v4 작성. "선행조건: FE-PR-7~11 완료 후"라 적었으나
        실제로는 빌더가 먼저 진행됨 (문서-실행 불일치)
03-20  Phase A LLM 빌더 완료
```

**결론:** 코드베이스에 실재하는 "Phase 3"는 **① 대시보드 리디자인(실제 값 카드 + AI분석 + 미니차트)** 과 **② 빌더 재설계(LLM one-shot)** 두 트랙뿐이다. CLAUDE.md·Phase2_summary가 약속한 **"깊이 + 회고 + 프로필"(원 FE-PR-7~11) 5개 PR은 0건 구현**. 특허 핵심인 **학습/개인화 레이어(DNA·유효성 학습·합성 에이전트)는 Phase 1 모델 골격만 존재**하고 집계·API·UI가 전무하다.

---

## 1. 요약 — Phase별 / 트랙별 구현률

### 1.1 프론트엔드 화면 트랙

| 트랙 | 설계 출처 | 구현률 | 비고 |
|---|---|---|---|
| Phase 2 핵심 루프 (목록→빌더→지표→대시보드→알림→마감) | FE-PR-1~6 | **(A) 100%** | 완전 구현, 완료 보고서 6건 |
| 대시보드 리디자인 (실제값/AI분석/미니차트/토글차트) | phase3_redesign PR-7~9 | **(A) ~95%** | 8개 신규 컴포넌트 전부 존재 |
| 빌더 재설계 (LLM one-shot + 키워드) | talking_builder Phase A·B | **(A) A·B 완료 / (C) C 미구현** | MiniDashboard·스트리밍 ❌ |
| **깊이+회고+프로필 (원 FE-PR-7~11)** | Phase2_summary §8 | **(D) 0% — 대체·폐기** | 본 감사 핵심 갭 |
| 다중 뷰 (카드/히트맵/그래프) | design.md §3.4 | **(B) 33%** | 카드뷰만. 히트맵·그래프 ❌ |
| 5개 진입경로 | design.md §2.3 | **(B) 40%** | 뉴스·자유입력만. 인기·템플릿·ChainSight ❌ |

### 1.2 백엔드 엔진 트랙

| 트랙 | 설계 출처 | 구현률 | 비고 |
|---|---|---|---|
| 관제 엔진 (Stage 0~3 + 스냅샷/알림) | math_model / roadmap P1 | **(A) 완료** | EOD 3-task 파이프라인 |
| 대시보드 백엔드 (raw_value·display_unit·readings API) | redesign PR-7 | **(A) 완료** | migration 0004/0005, `IndicatorReadingsView` |
| AI 요약·notable_changes 생성 (PR-10) | redesign PR-10 | **(A) 구현** | `snapshot_builder.py` + `tasks/summary.py` |
| 학습 레이어 — 이벤트/유효성/DNA **기록** | roadmap Phase 1 | **(B) 모델만** | 모델·마감시 갱신 ○, 노출 ✗ |
| 학습 레이어 — ValidityScore 집계·DNA슬라이더·역제안 | roadmap Phase 2 | **(C) 0%** | 모델·서비스 부재 |
| 합성 에이전트·Online LR·블렌딩 | roadmap Phase 3 | **(C) 0%** | — |
| 벡터 스코어링 (DNA벡터·유사도) | roadmap Phase 4 | **(C) 0%** | — |
| 커뮤니티 (인기가설·팔로우 API) | design.md §7 | **(B) 모델만** | `ThesisFollow`/`PopularThesisCache` ○, View·URL ✗ |

> **전일(6/4) 대비 정정:** PR-10을 "task 존재"로만 본 전일 평가를 검증한 결과, `thesis/services/snapshot_builder.py`와 `thesis/tasks/summary.py`가 `notable_changes`/`ai_summary`를 실제 생성·저장하는 것을 확인 → **(A) 구현**으로 상향. 대시보드 리디자인 트랙은 PR-7·8·9·10 모두 코드 존재.

---

## 2. 문서별 상태 테이블

| 설계 문서 | 핵심 내용 | 구현 상태 | 갭 요약 |
|---|---|---|---|
| `plan/thesis_control_design.md` | 전체 컨셉·UX·모델·API | **(B) 부분** | 모델 대부분 ○. 다중뷰·5진입경로·복기·커뮤니티 API ✗ |
| `plan/thesis_control_math_model_final.md` (v2.3.2) | Stage 0~3 관제 엔진 | **(A) 완료** | `indicator_scorer`/`premise_aggregator`/`thesis_state_machine` |
| `plan/thesis_control_integrated_roadmap.md` | Phase 1~4 특허 학습 레이어 | **(B) Phase1 골격만** | Phase 2~4 전부 ✗ (§3-D 상세) |
| `plan/thesis_control_phase3_frontend_redesign.md` | 대시보드 리디자인 PR-7~10 | **(A) 완료** | PR-7·8·9 컴포넌트·필드 + PR-10 생성 task 전부 존재 |
| `plan/thesis_control_implementation_guide.md` | 구현 가이드 | (참고) | — |
| `plan/talking_builder/thesis_builder_redesign_v2.md` | 빌더 재설계 상세 | **(A) Phase A·B** | Phase C ✗ |
| `plan/talking_builder/redesign_build_plan/01~04` | Phase A/B/C PR 스펙 | **(A) A·B / (C) C** | `04_phase_c_advanced` ✗ |
| `plan/talking_builder/llm_builder_plan.md` | LLM 빌더 플랜 | **(A) 완료** | `start_llm_conversation`/`process_llm_turn` |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 대시보드 | **(A) 완료** | `quarterly_metric_fetcher` + `QuarterlySparkline` |
| `thesis_control_user_experience.md` | UX 시나리오 | **(B) 부분** | 핵심 플로우 ○, 근거 시스템·제스처 부분 |
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 완료 보고서 | **(A) 완료** | 6개 PR 전부 구현 확인 |
| `frontend/task_done/Phase2_completion_summary.md` §8 | **FE-PR-7~11 계획** | **(D) 폐기·대체** | 03-18 리디자인으로 교체. 본 감사 핵심 |
| `frontend/task_done/FE-PR-3_plan_review_v3.md` | 빌더 PR 리뷰 | (참고) | — |
| `work_done/phase_a_llm_builder.md` | Phase A 완료 보고서 | **(A) 완료** | 커밋 09b0f8b/6d72432 |

---

## 3. Phase 3 미구현 항목 상세

### (D) 원 FE-PR-7~11 "깊이 + 회고 + 프로필" — 폐기·대체 (구현 0건)

`Phase2_completion_summary.md` §8의 5개 PR. **2026-03-18 리디자인으로 방향이 바뀌어 어느 것도 구현되지 않았다.** CLAUDE.md가 "진행 중"으로 표기한 바로 그 항목이다.

| PR | 설계 내용 | 상태 | 코드 근거 |
|---|---|---|---|
| **FE-PR-7** | 대시보드 **3탭 구조** (관제/상세/히스토리) + 전제 CRUD 탭 | ❌ 미구현 | `app/thesis/[thesisId]/page.tsx` 단일 화면, 탭 컴포넌트 없음 |
| **FE-PR-8** | **히트맵 뷰**(Finviz 스타일) + 지표 weight/direction 편집 | ❌ 미구현 | thesis에 히트맵 컴포넌트 없음(`SectorHeatmap`은 screener 전용). `IndicatorSetupCard`는 토글/삭제만, weight 편집 없음 |
| **FE-PR-9** | **히스토리 탭** — 스냅샷 타임라인 + recharts | ❌ 미구현 | 스냅샷 조회 화면 없음. (지표별 미니차트는 리디자인 PR-9로 별도 구현됨 — 다른 기능) |
| **FE-PR-10** | **마감 아카이브** + 복기 요약 + **ValidityMatrix** | ❌ 미구현 | `close/page.tsx`는 `OutcomeSelector`+`CloseConfirmDialog`(outcome 선택 + note)만. design.md §3.9 "가장 유용했던 지표/예상과 달랐던 부분" 복기 화면·아카이브 목록 없음 |
| **FE-PR-11** | **투자자 DNA 프로필** (AccuracyRing + CategoryChart) | ❌ 미구현 | InvestorDNA 노출 화면·API 0건. retrospective/profile 키워드 thesis 무관 |

> 프론트 인벤토리 재검증: `heatmap`/`히트맵`/`회고`/`복기`/`retrospective` 키워드의 thesis 모듈 매치 **0건** (히트맵은 screener, DNA 매치는 close/mock/types 내 무관 토큰). `frontend/components/thesis/`에 retrospective·profile·heatmap·history 디렉토리 부재.

### (D) design.md §7 Phase 3 "커뮤니티 + 고도화" — 모델만 존재

| 설계 항목 | 상태 | 근거 |
|---|---|---|
| 인기 가설 시스템 / 따라하기 | (B) 모델만 | `ThesisFollow`·`PopularThesisCache` 모델 ○ / `urls.py`에 `popular/` 경로·View **✗** |
| 템플릿 시스템 (진입경로 4) | (C) 미구현 | `templates/` API 없음 |
| Chain Sight 연동 (진입경로 5) | (C) 미구현 | 연동 코드 없음 |
| 가설 마감 + 복기 시스템 | (B) 부분 | close API ○ (ValidityRecord 생성·DNA 갱신 ○) / 복기 **화면** ✗ |
| Neo4j 가설 관계 그래프 | (C) 미구현 | thesis→Neo4j sync 부재 (design.md §4.4) |

### (C) integrated_roadmap.md Phase 2~4 — 특허 학습 레이어 (핵심 미구현)

설계의 **특허 차별점**(독립항 1~3)이며 현재 **Phase 1 골격만** 존재.

**Phase 1 (기록) — (B) 모델·갱신만 구현:**
- ✅ `HypothesisEvent` 모델 + 13개 event_type, 3개 인덱스 (`models/learning.py`)
- ✅ `ValidityRecord` 모델 + 마감 시 2×2 매트릭스 생성
- ✅ `InvestorDNA` 모델 + 마감 시 자동 갱신 (`accuracy_rate`/`ai_accept_rate`/`top_down_ratio` 속성)
- ❌ 이 데이터를 **노출하는 API·화면 전무** → 축적만 되고 활용 0

**Phase 2 (개인화) — (C) 0%:**
- ❌ `ValidityScore` 집계 모델 — `learning.py`에 부재, migration 0009까지 중 없음 (검증: grep 결과 `migrations/0001`·`learning.py` 외 매치 없음)
- ❌ 주 1회 ValidityRecord→ValidityScore 집계 Celery task
- ❌ 지표 추천 유효성 반영(core/reference/low_impact 티어)
- ❌ DNA 적합도 슬라이더 (`personalization_weight` 필드만 존재, 로직 없음)
- ❌ 역제안(Contrarian Nudge)
- ❌ 상관계수 자동 할인 / Adaptive Decay / Sustained Extreme / 뉴스 센티먼트 Stage 1 입력

**Phase 3 (지능) — (C) 0%:**
- ❌ 합성 에이전트 부트스트래핑(`SyntheticBootstrapper`, 20~30 페르소나)
- ❌ `ValidityRecord.is_synthetic` 필드
- ❌ Online Logistic Regression(`ThesisWeightLearner`)
- ❌ 합성/실제 데이터 블렌딩

**Phase 4 (벡터) — (C) 0%:**
- ❌ DNA 16차원 벡터화 / 유효성 6차원 벡터화 / 코사인 유사도 추천 / 사용자 유사도

### (C) design.md §3.4 다중 뷰 — 카드뷰만

| 뷰 | 상태 |
|---|---|
| 카드뷰 (`RealValueIndicatorCard`) | ✅ (A) |
| 히트맵 뷰 (Finviz 스타일) | ❌ (C) — DashboardView 응답에 `heatmap` 키 없음 |
| 그래프 뷰 (지지/중립/반박 라인) | ❌ (C) — 지표별 미니차트로 일부 대체, 통합 그래프뷰 없음 |

### (B) design.md §2.3 5개 진입경로

| 경로 | 상태 | 근거 |
|---|---|---|
| 경로1 오늘 이슈 | ✅ (A) | `NewsSelector` + `NewsIssuesView` + `SuggestThesesView` |
| 경로2 내 생각 | ✅ (A) | 자유입력 → LLM proposal |
| 경로3 인기 가설 | ❌ (C) | `EntryPointGrid` 2개 진입점만, popular API 없음 |
| 경로4 템플릿 | ❌ (C) | — |
| 경로5 Chain Sight | ❌ (C) | — |

### (C) 빌더 재설계 Phase C — 고급 기능

| 항목 | 상태 |
|---|---|
| Phase A (LLM one-shot + 프리셋 + fallback) | ✅ (A) |
| Phase B (KeywordCache + chain/eod/news collectors + Monitoring) | ✅ (A) — migration 0006/0007, `keyword_collectors/`, `check_keywords` |
| Phase C — MiniDashboardPreview | ❌ (C) |
| Phase C — Guided Suggestion | ❌ (C) |
| Phase C — 스트리밍 응답 | ❌ (C) |
| Phase C — keyword strength/micro-fact/scoring | ⚠️ strength 필드만 (migration 0007), 활용 로직 미확인 |

---

## 4. 보조 발견

1. **문서-구현 명명 혼란이 부채로 누적됨.** `phase3_frontend_redesign.md`의 PR-7~10과 `Phase2_summary`의 FE-PR-7~11이 동일 번호·다른 내용. 향후 작업자가 "FE-PR-7"을 어느 쪽으로 해석할지 모호.

2. **빌더 재설계 v4의 선행조건 모순.** "선행조건: FE-PR-7~11 완료 후 착수"(03-19)라 적혔으나, 실제로는 해당 FE-PR-7~11 미착수 상태에서 빌더가 먼저 완료(03-20)됨. 폐기된 선행조건이므로 무효.

3. **학습 데이터는 쌓이는데 출구가 없다.** HypothesisEvent/ValidityRecord/InvestorDNA가 마감마다 기록·갱신되지만 노출 API·화면 0건. "구현하면 즉시 가치"인 상태(원 FE-PR-11 DNA 프로필이 그 출구였음).

4. **마감 복기 격차.** 백엔드 close는 ValidityRecord 생성까지 하나, design.md §3.9의 정성적 복기 화면("가장 유용했던 지표")이 없어 학습 피드백이 사용자에게 전달되지 않음.

5. **(전일 대비 변동 없음)** 6/4 → 6/5 사이 thesis 관련 코드·문서 신규 커밋 없음. 본 감사는 동일 코드 상태를 재검증했고 모든 (A)/(B)/(C)/(D) 판정이 재현됨. 유일한 차이는 PR-10 생성 파이프라인 확인으로 인한 평가 상향(§1.2 주석).

---

## 5. 우선순위 권고 (감사 의견, 실행은 별도 결정)

| 우선순위 | 항목 | 근거 |
|---|---|---|
| P1 | **문서 정합화** — FE-PR-7~11 번호 충돌 해소, CLAUDE.md "Phase 3 진행 중" 표기 현행화 | 비용 0, 향후 모든 작업의 혼란 제거 |
| P2 | **투자자 DNA 프로필 화면/API** (원 FE-PR-11) | 데이터 이미 축적 중, 노출만 하면 됨. 특허 독립항1 핵심 |
| P2 | **마감 복기 화면** (원 FE-PR-10) | ValidityRecord 이미 존재, 화면만 추가 |
| P3 | ValidityScore 집계 (roadmap Phase 2) | 개인화 추천의 토대 |
| P3 | 히트맵/그래프 뷰 (design §3.4) | 다중 뷰 약속 미이행 |
| P4 | 커뮤니티 API(인기 가설), 합성 에이전트(Phase 3), 벡터화(Phase 4) | 장기 고도화 |

---

*본 보고서는 읽기 전용 감사이며 코드를 일절 수정하지 않았다. 모든 "구현됨/미구현" 판정은 `thesis/`(models·views·urls·services·tasks·migrations) 및 `frontend/**/thesis` 실제 파일·모델·URL·컴포넌트 인벤토리 기반이다. 전일(6/4) 보고서의 핵심 주장은 본 세션에서 모델 소스·URL 라우팅·뷰 필드·프론트 키워드로 독립 재검증되어 전부 재현되었다.*
