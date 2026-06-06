# Thesis Control 설계 갭 감사

> 감사일: 2026-06-06
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/`(백엔드) + `frontend/components/thesis/`(프론트) 코드
> 방식: 읽기 전용 정적 대조 (코드 미수정). 모든 항목 실제 파일 확인 기반.

---

## 0. 핵심 발견 — "Phase 3" 정의 충돌 ⚠️

이 감사의 가장 중요한 결과는 **"Phase 3 / FE-PR-7~11"이 서로 다른 두 문서에서 상반되게 정의**되어 있다는 점이다.

| | 정의 A — "깊이 + 회고 + 프로필" | 정의 B — "Dashboard 실제값 리디자인" |
|---|---|---|
| **출처** | `Phase2_completion_summary.md` §8 (8줄, 표만 존재) + `CLAUDE.md` L159 | `plan/thesis_control_phase3_frontend_redesign.md` (FINAL 1.0, 2026-03-18) |
| **PR 범위** | FE-PR-7 탭구조 / 8 히트맵 / 9 히스토리 / 10 마감아카이브 / 11 투자자DNA | PR-7 백엔드 raw_value / 8 실제값카드 / 9 미니차트 / 10 AI파이프라인 |
| **설계 상세** | **없음** (제목·핵심 한 줄씩만) | **완비** (~830줄, 컴포넌트 props·검증 체크리스트까지) |
| **구현 상태** | **거의 미구현** | **거의 완전 구현** |

→ **실제로 구현된 것은 정의 B**(실제값 리디자인)이며, CLAUDE.md가 "진행 중"이라 표기한 정의 A(깊이/회고/프로필)는 **설계서조차 없는 미착수 상태**다. 같은 "FE-PR-7~9" 번호가 전혀 다른 작업을 가리키므로, 진행률 보고 시 반드시 어느 정의인지 명시해야 한다.

---

## 1. 요약 (Phase별 구현률)

| Phase | 정의 출처 | 구현률 | 비고 |
|-------|----------|--------|------|
| **Phase 1 (백엔드 MVP)** | `integrated_roadmap.md` §1 | **~95% (A)** | 관제엔진 Stage 0~3 + 이벤트수집 + ValidityRecord + InvestorDNA 골격 전부 적재 |
| **Phase 2 (백엔드 개인화)** | `integrated_roadmap.md` §2 | **~5% (C)** | ValidityScore 모델·집계, DNA 슬라이더, 역제안 전부 미구현 (`personalization_weight` 필드만 선적재) |
| **Phase 3-B (Dashboard 리디자인)** | `phase3_frontend_redesign.md` | **~95% (A)** | PR-7~10 전부 구현. 실제 페이지는 `RealValueIndicatorCard` 대신 `IndicatorRow`로 구현(경미한 발산) |
| **Phase 3-A (깊이+회고+프로필)** | `Phase2_completion_summary.md` §8 | **~10% (C)** | 백엔드 데이터(InvestorDNA/ValidityRecord)만 적재, 프론트 화면 0건·노출 API 0건 |
| **Phase 3 (백엔드 로드맵: 합성+학습)** | `integrated_roadmap.md` §3 | **0% (C)** | SyntheticBootstrapper, ThesisWeightLearner, 블렌딩 전무 |
| **Phase 4 (벡터 스코어링)** | `integrated_roadmap.md` §4 | **0% (미착수)** | 정상 — 후속 단계 |

**한 줄 결론**: 백엔드 관제엔진(Phase 1)과 프론트 Dashboard 실제값 리디자인(Phase 3-B)은 사실상 완료. 그러나 CLAUDE.md가 "진행 중"으로 선언한 **"깊이+회고+프로필"(Phase 3-A)과 Phase 2 백엔드 개인화 레이어는 미착수**다.

---

## 2. 문서별 상태 테이블

| 설계 문서 | 핵심 내용 | 대응 구현 | 상태 |
|----------|----------|----------|------|
| `plan/thesis_control_design.md` | 마스터 설계 (관제실 UX 전반) | thesis/ 전반 | (A) 기반 구현 |
| `plan/thesis_control_math_model_final.md` (v2.3.2) | Stage 0~3 수학엔진 | `indicator_scorer.py`, `premise_aggregator.py`, `thesis_state_machine.py`, `data_validator.py` | **(A) 완전** |
| `plan/thesis_control_integrated_roadmap.md` §1 | Phase 1: 이벤트수집/유효성/DNA | `models/learning.py` (HypothesisEvent·ValidityRecord·InvestorDNA), `thesis_views.py` close 훅 | **(A) 완전** |
| `plan/thesis_control_integrated_roadmap.md` §2 | Phase 2: ValidityScore·슬라이더·역제안 | — | **(C) 미구현** |
| `plan/thesis_control_integrated_roadmap.md` §3 | Phase 3: 합성에이전트·Online LR | — | **(C) 미구현** |
| `plan/thesis_control_integrated_roadmap.md` §4 | Phase 4: 벡터화 | — | (미착수) |
| `plan/thesis_control_phase3_frontend_redesign.md` PR-7 | display_unit·raw_value·IndicatorReadingsView | `models/indicator.py:73`, `monitoring_views.py` DashboardView·IndicatorReadingsView, migration 0004/0005 | **(A) 완전** |
| `plan/thesis_control_phase3_frontend_redesign.md` PR-8 | 실제값 카드 + AI분석 + 오늘의변화 | `dashboard/RealValueIndicatorCard·AISummarySection·NotableChangesSection.tsx`, `lib/thesis` 타입·유틸 | **(A) 완전** |
| `plan/thesis_control_phase3_frontend_redesign.md` PR-9 | 미니차트 + 기간선택 + 구컴포넌트 삭제 | `dashboard/ChartToggleButton·PeriodSelector·IndividualMiniCharts.tsx`; OverallMoon·DashboardIndicatorCard·RecentChange 삭제 확인 | **(A) 완전** |
| `plan/thesis_control_phase3_frontend_redesign.md` PR-10 | AI 요약 Celery 파이프라인 | `tasks/summary.py` generate_thesis_summaries (Gemini sync) | **(A) 완전** |
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 프론트 핵심루프 | 목록·빌더·지표설정·대시보드·알림·마감 | **(A) 완전** (완료 보고서 일치) |
| `frontend/task_done/Phase2_completion_summary.md` §8 | **Phase 3-A: FE-PR-7~11 (깊이/회고/프로필)** | — (설계서 없음) | **(C) 미설계·미구현** |
| `plan/talking_builder/*` (00_total_plan, redesign_v2, llm_builder_plan) | LLM 대화형 빌더 재설계 | `thesis_builder.py` LLM 모드 부분 구현 | (B) 부분 — Phase 3-A와 독립 트랙 |
| `work_done/phase_a_llm_builder.md` | LLM 빌더 Phase A | `thesis_builder.py` start_llm_conversation 등 | (B) 부분 |

---

## 3. Phase 3 미구현 항목 상세

### 3-A. "깊이 + 회고 + 프로필" (Phase2_completion_summary §8 정의) — 핵심 갭

> CLAUDE.md가 "진행 중"으로 선언한 FE-PR-7~11. 설계 상세 문서가 **존재하지 않으며**, 프론트 화면도 거의 없다.

| PR (정의 A) | 설계 의도 | 구현 현황 | 분류 |
|------|----------|----------|------|
| **FE-PR-7** 대시보드 탭 구조 + 상세 탭 | 3탭(관제/상세/히스토리) + 전제 CRUD | 대시보드는 **탭 없는 단일 스크롤 페이지**. 전제 CRUD는 백엔드 `ThesisPremiseViewSet`만 존재, 대시보드 상세탭 UI 없음. `IndicatorRow` 확장(지표별 차트 토글)이 "상세"를 부분 대체 | **(C)** 미구현 (IndicatorRow가 부분 대체) |
| **FE-PR-8** 히트맵 + 지표 상세 편집 | Finviz 스타일 히트맵 + weight/direction 편집 | 백엔드 `DashboardView`가 **heatmap 데이터 계산은 수행**하나, 프론트 **히트맵 컴포넌트 없음**. 지표 weight/direction 편집 UI 없음(`IndicatorSetupCard`는 toggle/delete만) | **(B) 부분** — 백엔드 데이터만, 프론트 0 |
| **FE-PR-9** 히스토리 탭 | recharts 라인차트 + 스냅샷 타임라인 | **스냅샷(overall_score) 타임라인 차트 없음**. `IndividualMiniCharts`는 지표 raw_value 시계열로 성격이 다름(스냅샷 점수 히스토리 아님) | **(C)** 미구현 |
| **FE-PR-10** 마감 아카이브 + 요약 | 마감 가설 목록 + ValidityMatrix | 마감 시 `ValidityRecord` 생성은 됨(`thesis_views.py` close). **마감 가설 아카이브 목록 화면·ValidityMatrix UI 없음** | **(C)** 미구현 (데이터 적재만) |
| **FE-PR-11** 투자자 DNA 프로필 | AccuracyRing + CategoryChart + 기술부채 정리 | 백엔드 `InvestorDNA` 모델 + close 시 `_update_investor_dna()` 갱신 **있음**. 그러나 **DNA 노출 API 없음**(urls.py에 프로필 엔드포인트 0), **프론트 프로필 화면·AccuracyRing·CategoryChart 전부 없음** | **(C)** 미구현 (백엔드 적재만, 노출 0) |

**공통 패턴**: Phase 1에서 학습 데이터(InvestorDNA, ValidityRecord)는 **적재(write)되고 있으나, 읽기(read)·시각화 경로가 전무**하다. 즉 데이터는 쌓이는데 사용자에게 보여줄 화면과 API가 없는 "데이터 사일로" 상태.

### 3-B. 백엔드 로드맵 Phase 2~3 (integrated_roadmap 정의) — 학습/개인화 레이어

| 항목 | 설계 위치 | 구현 | 분류 |
|------|----------|------|------|
| `ValidityScore` 모델 | roadmap §2.1 | 모델·마이그레이션 없음 | **(C)** |
| ValidityScore 집계 Celery 태스크 | roadmap §2.1 | 없음 | **(C)** |
| 지표추천 유효성 반영 (`validity_boost`) | roadmap §2.2 | `indicator_matcher.py`는 키워드+Gemini만, 유효성 미반영 | **(C)** |
| DNA 적합도 슬라이더 (`apply_dna_personalization`) | roadmap §2.3 | `personalization_weight` 필드만 선적재(`learning.py:124`), 로직 없음 | **(C)** |
| 역제안 (`add_contrarian_nudge`) | roadmap §2.4 | 없음 | **(C)** |
| 상관 자동할인 / Adaptive Decay / Sustained Extreme / 뉴스센티먼트 | roadmap §2.5 | 뉴스센티먼트 fetch만 부분(`_fetch_news_sentiment_value`), 나머지 없음 | **(C)** 대부분 |
| `SyntheticBootstrapper` (합성 에이전트) | roadmap §3.1 | 없음 — **특허 독립항 3 핵심** | **(C)** |
| `ThesisWeightLearner` (Online LR) | roadmap §3.2 | 없음 | **(C)** |
| 합성/실제 블렌딩 (`aggregate_validity_scores`) | roadmap §3.3 | 없음 | **(C)** |
| `ValidityRecord.is_synthetic` 필드 | roadmap 표 (Phase 3) | 필드 없음 | **(C)** |
| `InvestorDNA.dna_vector` 필드 | roadmap 표 (Phase 4) | 필드 없음 | (미착수) |

### 3-C. 구현되었으나 설계와 발산한 항목 (참고)

| 구현물 | 설계 대비 | 비고 |
|--------|----------|------|
| `dashboard/IndicatorRow.tsx` | redesign 설계엔 없는 컴포넌트 | 실제 대시보드 페이지의 지표 표시 주체. 설계의 `RealValueIndicatorCard`는 존재하나 페이지 1차 렌더는 IndicatorRow가 담당 → **설계서와 실제 구현의 컴포넌트 구성 미세 발산** |
| `dashboard/QuarterlySparkline.tsx` + DashboardView 분기재무 확장(fiscal_label·quarterly_history) | redesign 문서 범위 밖 | 분기 지표 히스토리 기능이 별도로 추가됨 (설계서 미반영 = 문서 부채) |
| `common/MoonPhase.tsx` 잔존 | redesign §2에서 "import 검색 후 삭제 결정" | dashboard의 OverallMoon은 삭제됐으나 common/MoonPhase.tsx는 잔존 — 사용처 확인 필요한 정리 보류 항목 |

---

## 4. 분류 요약 (A/B/C/D)

- **(A) 완전 구현**: 수학엔진 Stage 0~3, Phase 1 이벤트/유효성/DNA 적재, Phase 3-B Dashboard 실제값 리디자인 PR-7~10, FE-PR-1~6 핵심루프
- **(B) 부분 구현**: 히트맵(백엔드 계산만, 프론트 0), LLM 대화형 빌더(talking_builder 트랙), 뉴스센티먼트(fetch만)
- **(C) 미구현**: Phase 3-A 깊이/회고/프로필 화면(FE-PR-7~11 정의 A), Phase 2 백엔드 개인화(ValidityScore·슬라이더·역제안), Phase 3 백엔드 합성·학습(Bootstrapper·LR·블렌딩)
- **(D) 폐기/대체**: OverallMoon·DashboardIndicatorCard·RecentChange (redesign에서 삭제 확정·실제 삭제됨), CombinedNormalizedChart(설계 단계 폐기, 생성 안 됨), Zustand dashboardStore(useState로 대체)

---

## 5. 권고 (감사자 의견 — 실행 아님)

1. **"Phase 3" 명칭 정합화**: CLAUDE.md L159의 "Phase 3 (깊이+회고+프로필: FE-PR-7~11)"와 실제 구현된 "Dashboard 리디자인"이 같은 PR 번호를 공유해 혼선. 둘 중 하나를 "Phase 3-Redesign"/"Phase 3-DRP" 등으로 재명명 권고.
2. **데이터 사일로 해소 우선순위**: InvestorDNA·ValidityRecord가 적재만 되고 노출 0. FE-PR-11(DNA 프로필) + 노출 API가 가장 ROI 높은 다음 작업 후보(데이터는 이미 있음).
3. **설계 부채 문서화**: IndicatorRow·QuarterlySparkline·분기재무 확장은 코드엔 있으나 설계서 미반영. redesign 문서 또는 후속 문서에 사후 반영 필요.
4. **특허 트랙 리스크**: 합성 에이전트(독립항 3)·Online LR(독립항 2)가 0% 구현. 특허 청구 범위와 구현 갭이 가장 큰 영역.

---

*본 보고서는 정적 코드 대조 기반이며 런타임 동작·테스트 통과 여부는 검증하지 않았다. 코드는 일절 수정하지 않았다.*
