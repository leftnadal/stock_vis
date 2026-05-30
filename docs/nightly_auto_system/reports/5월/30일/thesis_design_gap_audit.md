# Thesis Control 설계 갭 감사

> 감사일: 2026-05-31 (읽기 전용)
> 범위: `docs/thesis_control/` 설계 문서 ↔ `thesis/`(백엔드) + `frontend/components/thesis/`·`frontend/app/thesis/`(프론트엔드)
> 분류: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 0. 핵심 결론 (먼저 읽기)

**"Phase 3"라는 이름이 서로 다른 두 설계를 가리킨다.** 이것이 이 감사의 가장 중요한 발견이다.

| 명칭 | 출처 문서 | 내용 | 실제 구현 |
|------|----------|------|----------|
| **Phase 3-A** (구안) | `Phase2_completion_summary.md` §8 | FE-PR-7~11: 탭구조 + 히트맵 + 히스토리 + 마감아카이브 + **DNA 프로필** ("깊이 + 회고 + 프로필") | ❌ **거의 전부 미구현 (C)** |
| **Phase 3-B** (신안, 2026-03-18) | `plan/thesis_control_phase3_frontend_redesign.md` | PR-7~10: 대시보드 리디자인 — 내부 점수 숨기고 **실세계 값**(환율·VIX) 표시 | ✅ **백엔드 완전 + 프론트 대체 구현** |

→ CLAUDE.md가 말하는 "Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"는 **Phase 3-A**를 가리키는데, 실제 코드는 **Phase 3-B 방향으로 진행**되었다. 즉 Phase 3-A는 사실상 **Phase 3-B로 대체(D)**된 것으로 보이나, 두 문서 어디에도 "대체한다"는 명시적 기록이 없어 **설계 정합성 부채**로 남아 있다.

추가로 백엔드 **학습/개인화 레이어**(`integrated_roadmap.md`의 Phase 1)는 모델 + 수집 로직이 **실제로 작동 중**이나, 이를 사용자에게 보여주는 **노출 계층(API·화면)이 전무**하다 → DNA 프로필(FE-PR-11)이 미구현인 직접 원인.

---

## 1. 요약 (Phase별 구현률)

### 1-1. 수학·학습 로드맵 (`thesis_control_integrated_roadmap.md`)

| Phase | 목표 | 구현률 | 비고 |
|-------|------|--------|------|
| **Phase 1** 관제엔진 + 이벤트수집 | Stage 0~3 + HypothesisEvent/ValidityRecord/InvestorDNA | **A (~95%)** | Stage 0~3 서비스 + 학습 모델 3종 + 수집 로직 전부 작동 |
| **Phase 2** 유효성 활성화 + DNA 슬라이더 | ValidityScore 집계 + personalization + 역제안 | **C (~5%)** | `personalization_weight` 필드만 존재. ValidityScore 모델 없음 |
| **Phase 3** 합성에이전트 + Online LR | SyntheticBootstrapper + `is_synthetic` | **C (0%)** | 흔적 없음 |
| **Phase 4** 벡터 스코어링 | DNA 벡터화 + 코사인 유사도 | **C (0%)** | 흔적 없음 |

### 1-2. 프론트엔드 PR 트랙

| 트랙 | 구현률 | 비고 |
|------|--------|------|
| **Phase 2 (FE-PR-1~6)** 핵심 루프 | **A (100%)** | 목록→빌더→지표→대시보드→알림→마감 전부 완료, 완료보고서 6건 존재 |
| **Phase 3-A (FE-PR-7~11)** 깊이+회고+프로필 | **C (~10%)** | 상세 설계 문서조차 없음(§8 표 한 장이 전부). 탭/히트맵/히스토리/아카이브/DNA 화면 모두 미구현 |
| **Phase 3-B (PR-7~10)** 대시보드 리디자인 | **B (~70%)** | 백엔드(PR-7)·AI파이프라인(PR-10) 완전, 프론트(PR-8/9)는 `IndicatorRow` 단일 컴포넌트로 **대체 구현** |

### 1-3. Talking Builder 재설계 (별도 트랙, `plan/talking_builder/`)

| Phase | 구현률 | 비고 |
|-------|--------|------|
| **A-MVP / A-Hardening** (PR-1~7) | **A (100%)** | `work_done/phase_a_llm_builder.md` 완료보고서, 테스트 104건 |
| **B 키워드** (PR-8~12) | **A (~90%)** | `keyword_cache.py` + `keyword_collectors/{news,eod,chain}.py` + `keyword_hint.py` 구현 |
| **C 고급** (Health Report·멀티턴·스트리밍) | **C (0%)** | 미착수 (설계상으로도 "이후") |

---

## 2. 문서별 상태 테이블

| # | 문서 | 다루는 범위 | 구현 상태 | 근거 |
|---|------|------------|-----------|------|
| 1 | `plan/thesis_control_design.md` (1370줄) | 전체 마스터 설계 | **A** | 모델·서비스·API 구조 일치 |
| 2 | `plan/thesis_control_math_model_final.md` (1153줄) | 수학모델 v2.3.2 (Stage 0~3) | **A** | `data_validator`/`indicator_scorer`/`premise_aggregator`/`thesis_state_machine` + 테스트 11종 |
| 3 | `plan/thesis_control_integrated_roadmap.md` (660줄) | 학습/개인화 Phase 1~4 | **Phase1=A, 2~4=C** | §3 참조 |
| 4 | `plan/thesis_control_implementation_guide.md` (286줄) | 구현 가이드 | **A** (참고용) | — |
| 5 | `plan/thesis_control_phase3_frontend_redesign.md` (1095줄) | **Phase 3-B** 대시보드 리디자인 PR-7~10 | **B** | §4 상세 |
| 6 | `thesis_control_phase1_frontend_FE_PR_1~5.md` | FE-PR-1~5 지시서 | **A** | task_done 보고서 5건 |
| 7 | `thesis_control_user_experience.md` (435줄) | UX 시나리오 | **B** (핵심 루프만) | — |
| 8 | `frontend/task_done/FE-PR-1~6_*.md` (7건) | Phase 2 완료보고 | **A** | 실제 컴포넌트와 일치 |
| 9 | `frontend/task_done/Phase2_completion_summary.md` §8 | **Phase 3-A** FE-PR-7~11 계획 | **C** | §3 상세 — 별도 설계문서 부재 |
| 10 | `plan/talking_builder/redesign_build_plan/*` (6건) | LLM 빌더 재설계 A/B/C | **A/B=완료, C=미착수** | §1-3 |
| 11 | `work_done/phase_a_llm_builder.md` | Talking Builder Phase A 완료보고 | **A** | — |

---

## 3. Phase 3 미구현 항목 상세

### 3-A. Phase 3-A (FE-PR-7~11) — "깊이 + 회고 + 프로필" : 거의 전부 미구현 (C)

출처: `Phase2_completion_summary.md` §8. **별도 상세 설계 문서가 존재하지 않으며**, `frontend/task_done/`에도 FE-PR-7 이후 완료보고서가 없다.

| PR | 설계 핵심 | 상태 | 증거 |
|----|----------|------|------|
| **FE-PR-7** 대시보드 탭 구조 + 상세 탭 | 3탭(관제/상세/히스토리) + 전제 CRUD | **C** | `app/thesis/[thesisId]/page.tsx` 단일 화면, 탭 구조 없음. 전제 CRUD UI 없음 (백엔드 `ThesisPremiseViewSet`은 존재) |
| **FE-PR-8** 히트맵 + 지표 상세 편집 | Finviz 히트맵 + weight/direction 편집 | **C** | 히트맵 컴포넌트 없음. `indicators/page.tsx`는 토글/삭제/AI추천만, `weight`·`support_direction` 인라인 편집 UI 없음 |
| **FE-PR-9** 히스토리 탭 | recharts 라인차트 + 스냅샷 타임라인 | **C** | 히스토리 라우트/탭 없음. (`ThesisSnapshot` 모델·데이터는 축적되나 타임라인 화면 부재) |
| **FE-PR-10** 마감 아카이브 + 요약 | 마감 가설 목록 + ValidityMatrix | **C** | 마감 아카이브 라우트 없음(`app/thesis/` 디렉토리에 archive 없음). `close/page.tsx`는 `OutcomeSelector` 마감 액션만 |
| **FE-PR-11** 투자자 DNA 프로필 | AccuracyRing + CategoryChart | **C** | DNA 프로필 화면 없음. **백엔드 노출 API도 없음** (아래 3-C) |

> **권고**: Phase 3-A를 살릴지 폐기할지 명시적 결정이 필요. 살린다면 FE-PR-7~11 상세 설계 문서부터 작성해야 한다(현재 표 한 장뿐). 폐기한다면 `DECISIONS.md`에 "Phase 3-A → Phase 3-B 대체" 기록 권장.

### 3-B. Phase 3-B (PR-7~10) — 대시보드 리디자인 : 부분/대체 구현 (B)

출처: `plan/thesis_control_phase3_frontend_redesign.md`. 실제 채택된 방향.

| PR | 항목 | 상태 | 증거 |
|----|------|------|------|
| **PR-7** 백엔드 확장 | `ThesisIndicator.display_unit` 필드 | **A** | `models/indicator.py:73-76` |
| | `DashboardView` raw_value/change_pct | **A** | `monitoring_views.py` (DashboardView 존재) |
| | `IndicatorReadingsView` | **A** | `urls.py`에 라우트 등록 + 뷰 구현 |
| **PR-8** 실제 값 카드 + AI분석 | `AISummarySection` | **A** | `page.tsx:12,75` 연결됨 (+ 설계에 없던 `snapshotDate` prop 추가) |
| | `NotableChangesSection` | **A** | `page.tsx:13,81` 연결됨 |
| | `RealValueIndicatorCard` | **D (대체)** | 파일·테스트 존재하나 **page에서 미사용**. `IndicatorRow`가 `formatRawValue`+`supportLabel`+`QuarterlySparkline`으로 역할 흡수 |
| **PR-9** 미니차트 + 기간선택 | `IndividualMiniCharts` | **D (대체)** | **어디서도 import 안 됨 (orphan)**. `IndicatorRow`가 `useIndicatorReadings`+`ChevronDown` 접기로 지표별 차트 자체 구현 |
| | `ChartToggleButton` | **D (대체)** | orphan. IndicatorRow 내장 토글로 대체 |
| | `PeriodSelector` | **D (대체)** | orphan |
| | `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 삭제 | **A** | 3개 파일 모두 부재(삭제 완료) |
| **PR-10** AI 파이프라인 | `generate_thesis_summaries` Celery task | **A** | `tasks/summary.py:87`, 멱등 처리 + 테스트 `test_generate_summaries.py` |
| | `notable_changes` 스냅샷 연동 | **A** | `summary.py:45-48`, `snapshot_builder.py` |

> **부채**: `RealValueIndicatorCard`/`IndividualMiniCharts`/`ChartToggleButton`/`PeriodSelector` 4개 컴포넌트가 **orphan 상태**. 설계대로 만들었으나 실제로는 `IndicatorRow` 단일 컴포넌트로 통합되며 버려졌다. `RealValueIndicatorCard.test.tsx`도 죽은 컴포넌트를 테스트 중. **정리(삭제) 또는 page 전환 결정** 필요. `MoonPhase.tsx`(common)는 list 화면(`ThesisListCard`)에서 여전히 사용 중이므로 삭제 대상 아님(설계와 일치).

### 3-C. 백엔드 학습/개인화 레이어 — "작동하나 보이지 않음"

`integrated_roadmap.md` Phase 1의 학습 골격은 **실제로 동작 중**이나, 노출 계층이 없어 사용자 경험으로 이어지지 못한다 — 이것이 FE-PR-11(DNA 프로필) 미구현의 근본 원인.

| 모델/로직 | 상태 | 증거 |
|----------|------|------|
| `HypothesisEvent` 수집 | **A (작동)** | `thesis_views.py`·`thesis_builder.py`에서 생성/전제/지표/AI제안/마감 전 구간 기록 |
| `ValidityRecord` 생성 | **A (작동)** | `thesis_views.py:99` 마감 시 지표별 2×2 매트릭스 점수 기록 |
| `InvestorDNA` 집계 | **A (작동)** | `thesis_views.py:302` `_update_investor_dna()` 마감 시 갱신 (적중률·카테고리·지표유형·AI수락률) |
| **DNA 조회/노출 API** | **C (부재)** | `thesis/serializers/`에 DNA serializer **없음**, `urls.py`에 DNA 엔드포인트 **없음**. 갱신 전용으로만 존재 |
| `ValidityScore` 집계 모델 (Phase 2) | **C** | 모델 자체 부재 → 유효성 점수가 지표 추천에 반영 안 됨 |
| `is_synthetic` 필드 + `SyntheticBootstrapper` (Phase 3) | **C** | `ValidityRecord`에 필드 없음, 합성 부트스트래핑 흔적 없음 |
| `market_regime` | **부분** | `ValidityRecord`에 필드 있으나 `thesis_views.py:102`에서 `'normal'` **하드코딩** (regime 판정 미연동) |

---

## 4. 종합 권고 (우선순위)

1. **[설계 정합성]** "Phase 3"의 이중 의미를 `DECISIONS.md`에 정리 — Phase 3-A(FE-PR-7~11)를 폐기/보류/대체 중 무엇으로 할지 명시. CLAUDE.md 진행 상태("Phase 3 진행 중 FE-PR-7~11")도 실제(3-B 채택)와 어긋나므로 갱신 필요.
2. **[죽은 코드]** Phase 3-B orphan 4종(`RealValueIndicatorCard`+test, `IndividualMiniCharts`, `ChartToggleButton`, `PeriodSelector`) 삭제 또는 page 전환 결정.
3. **[숨은 자산]** `InvestorDNA`가 이미 채워지고 있으므로, DNA 조회 API(serializer+view+url) 1개만 추가하면 FE-PR-11 프로필 화면의 백엔드 의존성이 해소됨 — 가성비 높은 다음 작업 후보.
4. **[데이터 품질]** `ValidityRecord.market_regime` 하드코딩(`'normal'`)을 실제 VIX 레짐 판정과 연동(이미 EOD Dashboard에 VIX 레짐 로직 존재) — 향후 Phase 2 유효성 활성화의 전제.

---

## 부록: 검증에 사용한 실제 증거

- 백엔드 모델: `thesis/models/{learning,indicator,monitoring,community}.py` 정독
- 학습 로직 연결: `thesis/views/thesis_views.py`(close 액션 + `_update_investor_dna`), `thesis/services/thesis_builder.py`(이벤트 기록)
- 프론트 연결: `app/thesis/[thesisId]/page.tsx`(AISummary/NotableChanges만 연결, IndicatorRow 사용), `indicators/page.tsx`, `close/page.tsx`
- orphan 판정: `grep -rl` (RealValueIndicatorCard/IndividualMiniCharts/ChartToggleButton/PeriodSelector → 자기 파일·테스트 외 참조 0)
- 태스크: `thesis/tasks/summary.py`(generate_thesis_summaries)
- 서비스 인벤토리: Stage 0~3(`data_validator`/`indicator_scorer`/`premise_aggregator`/`thesis_state_machine`), 키워드(`keyword_cache`/`keyword_collectors/*`/`keyword_hint`)
- 테스트: `tests/unit/thesis/`(10) + `tests/thesis/`(2)
- 마이그레이션: `thesis/migrations/` 0001~0009 (display_unit 마이그레이션 위치는 추가 확인 권장)
