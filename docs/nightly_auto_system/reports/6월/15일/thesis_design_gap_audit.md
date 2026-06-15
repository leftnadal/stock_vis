# Thesis Control 설계 갭 감사

> 감사일: 2026-06-15
> 범위: `docs/thesis_control/` 설계 문서 vs `thesis/`(백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/`(프론트엔드)
> 성격: **읽기 전용 감사** — 코드 미수정
> 감사자: nightly auto system
> 직전 감사: 2026-06-09 (결론 일치, 본 회차는 6/15 시점 재검증 + 델타 확인)

---

## 0. 핵심 발견 (TL;DR)

1. **"Phase 3"이라는 이름이 세 개의 서로 다른 설계를 가리킨다.** 혼동의 근원.
   - **Phase 3-A** = `integrated_roadmap.md §3` → **합성 에이전트 + Online LR (백엔드 ML)** → **0% 미구현 (C)**
   - **Phase 3-B** = `phase3_frontend_redesign.md` PR-7~10 → **대시보드 실세계값 리디자인** → **~95% 완전 구현 (A)**
   - **Phase 3-C (질의 대상)** = `Phase2_completion_summary.md §8` FE-PR-7~11 "깊이+회고+프로필" → **0% 폐기/대체 (D)**

2. **사용자 질의의 "Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"은 전건 미착수이며 방향이 폐기되었다 (D).**
   탭 구조·히트맵·히스토리 탭·마감 아카이브·DNA 프로필 화면 중 **단 하나도 구현되지 않았고**, 그 자리를 Phase 3-B(대시보드 리디자인)가 대체했다. PR 번호(7~10)가 우연히 겹쳐 혼동을 키운다.

3. **CLAUDE.md "진행 중: Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)" 기재는 stale(실제 코드와 불일치)** — 해당 PR 산출물이 코드베이스에 부재. → 문서 정정 권고(코드 미수정 원칙상 본 감사는 기록만).

4. **6/9 → 6/15 델타: 실질 변화 없음.** thesis/models 클래스 목록(12개), 프론트엔드 thesis 컴포넌트, `tasks/summary.py`(142줄), 라우트 구조 모두 동일. ValidityScore/합성 에이전트/벡터화/FE-PR-7~11 화면은 6/15에도 부재.

---

## 1. 요약 (Phase별 구현률)

| Phase | 설계 출처 | 핵심 내용 | 구현률 | 분류 |
|-------|-----------|-----------|--------|------|
| **Phase 1** | integrated_roadmap §1 | 관제 엔진(Stage 0~3) + 이벤트 수집 + ValidityRecord + InvestorDNA 골격 | **~95%** | **A** |
| **Phase 2** | integrated_roadmap §2 | ValidityScore 활성화 + DNA 슬라이더 + 역제안 넛지 + 유효성 기반 추천 | **~10%** | **C** (필드 골격만) |
| **Phase 3-A** | integrated_roadmap §3 | 합성 에이전트 부트스트래핑 + Online LR + 합성/실데이터 블렌딩 | **0%** | **C** |
| **Phase 4** | integrated_roadmap §4 | DNA/유효성 벡터화 + 코사인 유사도 추천 | **0%** | **C** |
| **Phase 3-B (대시보드)** | phase3_frontend_redesign PR-7~10 | 실세계값 카드 + AI요약 + 오늘의변화 + 미니차트 | **~95%** | **A** |
| **Phase 3-C / FE-PR-7~11 (깊이/회고/프로필)** | Phase2_completion_summary §8 | 탭구조 + 히트맵 + 히스토리 + 마감아카이브 + DNA프로필 | **0%** | **D** 폐기/대체 |
| **Phase A LLM 빌더** (별도 트랙) | work_done/phase_a_llm_builder.md | one-shot LLM 제안형 빌더 | **~100%** | **A** |

> design.md §7의 Phase 정의(1=MVP / 2=모니터링 / 3=커뮤니티+고도화 / 4=지능화)는 또 다른 4단계 체계로, integrated_roadmap의 Phase 번호와 무관하다. 본 감사는 질의 맥락(FE-PR-7~11 = "깊이+회고+프로필")에 맞춰 Phase2_completion_summary와 integrated_roadmap을 1차 기준으로 사용한다.

---

## 2. 문서별 상태 테이블

| # | 설계 문서 / 대상 | 설계 내용 | 코드 대조 결과 | 분류 |
|---|------------------|-----------|----------------|------|
| 1 | `plan/thesis_control_design.md` §1~6 | 가설 CRUD + 대화형 빌더 + 화살표 엔진 + 관제실 | 모델 12종, views/serializers/services 전부 존재 | **A** |
| 2 | `plan/integrated_roadmap.md §1.2` HypothesisEvent | 단일 이벤트 스트림 | `models/learning.py:7` 존재, 생성 호출 `views/thesis_views.py`·`services/thesis_builder.py` | **A** |
| 3 | `integrated_roadmap §1.3` ValidityRecord | 마감 시 2×2 매트릭스 기록 | `models/learning.py:55` 존재, 마감 시 생성 | **A** |
| 4 | `integrated_roadmap §1.4` InvestorDNA | 이벤트 집계 프로파일 골격 | `models/learning.py:97` 존재, `personalization_weight` 필드(L124)까지 선반영 | **A** |
| 5 | `integrated_roadmap §2.1` ValidityScore | (type×indicator×regime) 집계 테이블 | 모델 없음 (grep 0건) | **C** |
| 6 | `integrated_roadmap §2.3` DNA 적합도 슬라이더 | `apply_dna_personalization()` | 서비스 없음 (필드만 존재) | **C** |
| 7 | `integrated_roadmap §2.4` 역제안 넛지 | `add_contrarian_nudge()` | 없음 | **C** |
| 8 | `integrated_roadmap §3.1` 합성 에이전트 | `SyntheticBootstrapper` + `is_synthetic` 필드 | 없음 (grep 0건) | **C** |
| 9 | `integrated_roadmap §3.2` Online LR | `ThesisWeightLearner` | 없음 | **C** |
| 10 | `integrated_roadmap §4` 벡터 스코어링 | `build_dna_vector()` + 코사인 유사도 | 없음 | **C** |
| 11 | `phase3_frontend_redesign.md` PR-7 | display_unit + IndicatorReadingsView + raw_value | 전부 구현 (migration `0004`/`0005`, `monitoring_views.py` IndicatorReadingsView·`_infer_unit`, urls.py) | **A** |
| 12 | `phase3_frontend_redesign.md` PR-8 | 실세계값 카드 + AI요약 + 오늘의변화 | `RealValueIndicatorCard`/`AISummarySection`/`NotableChangesSection` 존재, 페이지 통합 | **A** |
| 13 | `phase3_frontend_redesign.md` PR-9 | 미니차트 + 기간선택 + 정리 | `ChartToggleButton`/`PeriodSelector`/`IndividualMiniCharts` 존재. OverallMoon/DashboardIndicatorCard/RecentChange 삭제 확인 | **A** |
| 14 | `phase3_frontend_redesign.md` PR-10 | AI요약 파이프라인 + notable_changes 연동 | `tasks/summary.py:generate_thesis_summaries`(142줄, Gemini 동기·멱등) 구현 + Beat 등록(`config/celery.py:680`). **단 notable_changes는 alert 기반이 아닌 score 기반(\|Δscore\|≥0.3)으로 구현** | **B** (방식 변경) |
| 15 | `Phase2_completion_summary.md §8` FE-PR-7 | 대시보드 3탭 + 상세 탭 + 전제 CRUD | 탭 구조 없음, `[thesisId]/page.tsx` 단일 페이지 | **D** |
| 16 | `Phase2_completion_summary.md §8` FE-PR-8 | Finviz 히트맵 + weight/direction 편집 | 히트맵 컴포넌트 없음 | **D** |
| 17 | `Phase2_completion_summary.md §8` FE-PR-9 | 히스토리 탭 (recharts 스냅샷 타임라인) | 히스토리 라우트/컴포넌트 없음 | **D** |
| 18 | `Phase2_completion_summary.md §8` FE-PR-10 | 마감 아카이브 + ValidityMatrix UI | 아카이브 화면 없음, close 페이지는 단건 outcome만 | **D** |
| 19 | `Phase2_completion_summary.md §8` FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | 컴포넌트 전무 (grep 0건) | **D** |
| 20 | `work_done/phase_a_llm_builder.md` | one-shot LLM 제안형 빌더 | 빌더 서비스/컴포넌트 구현됨 | **A** |

---

## 3. Phase 3 미구현 항목 상세

사용자 질의의 "Phase 3 (깊이 + 회고 + 프로필)"은 `Phase2_completion_summary.md §8`이 정의한 **FE-PR-7~11**을 의미한다. 아래는 그 전건 미구현 상세 + 백엔드 Phase 3-A(합성 에이전트) 미구현 상세.

### 3.1 FE-PR-7~11 (깊이 + 회고 + 프로필) — 전건 미구현 / 방향 폐기 (D)

| PR | 설계 화면 | 예상 경로 | 실제 | 미구현 내용 |
|----|-----------|-----------|------|-------------|
| FE-PR-7 | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD | `app/thesis/[thesisId]/page.tsx` 탭화 | 단일 페이지 (탭 없음) | 탭 컨테이너·상세 탭·전제 추가/수정/삭제 UI 전무 |
| FE-PR-8 | Finviz 지표 히트맵 + weight/direction 인라인 편집 | `components/thesis/dashboard/IndicatorHeatmap.tsx` | 파일 없음 | 히트맵·지표 가중치 편집 UI 전무 |
| FE-PR-9 | 히스토리 탭 (recharts 라인 + 스냅샷 타임라인) | `app/thesis/[thesisId]/history/` | 라우트 없음 | ThesisSnapshot 시계열 시각화 전무 (단, `IndividualMiniCharts`로 지표별 raw 시계열은 Phase 3-B에서 별도 구현됨) |
| FE-PR-10 | 마감 가설 아카이브 목록 + ValidityMatrix 표시 | `app/thesis/archive/` | 라우트 없음 | 마감 회고 화면 전무. close 페이지는 단건 outcome 입력만 (`close/page.tsx`) |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | `app/thesis/profile/` 또는 `components/thesis/profile/` | 라우트·컴포넌트 없음 | InvestorDNA 모델은 백엔드에 존재하나 이를 시각화하는 화면 전무 |

**검증 근거 (grep, 6/15):**
`Heatmap`/`ValidityMatrix`/`AccuracyRing`/`CategoryChart`/`HistoryTab`/`DetailTab`/`PremiseEdit` — thesis 도메인 내 매칭 **0건**. `app/thesis` 라우트는 `(list)`/`new`/`[thesisId]`/`[thesisId]/indicators`/`[thesisId]/close`/`alerts` 6종뿐 — 탭·히스토리·아카이브·프로필 라우트 부재.

### 3.2 왜 폐기/대체로 분류하는가 (D 근거)

`Phase2_completion_summary.md`(2026-03-16) 작성 직후, 실제 개발 방향은 FE-PR-7~11(깊이/회고/프로필)이 아니라 **`phase3_frontend_redesign.md`(2026-03-18)의 대시보드 실세계값 리디자인(PR-7~10)으로 전환**되었다. 즉 "Phase 3" 개발 리소스는 회고/프로필이 아닌 **대시보드 UX 재설계**에 투입되었고, 깊이/회고/프로필 트랙은 착수되지 않은 채 미정 상태다. 두 트랙이 동일한 "Phase 3" 명칭 + 겹치는 PR 번호(7~10)를 쓰는 것이 stale 문서의 근본 원인.

### 3.3 백엔드 Phase 3-A (합성 에이전트 + Online LR) — 0% 미구현 (C)

| 설계 (integrated_roadmap §3) | 코드 검증 (6/15) |
|------------------------------|-------------------|
| `SyntheticBootstrapper` (페르소나 시뮬레이션) | 없음 |
| `ValidityRecord.is_synthetic` 필드 (합성 마킹) | `learning.py`에 필드 부재 (grep 0건) |
| `ThesisWeightLearner` (Online Logistic Regression) | 없음 |
| `aggregate_validity_scores()` 블렌딩 | 없음 (`ValidityScore` 테이블 자체 부재) |

전제조건인 **Phase 2(ValidityScore 활성화)**가 미구현이므로 Phase 3-A는 구조적으로 착수 불가 상태. Phase 1에서 ValidityRecord/InvestorDNA "기록"은 동작하나, 이를 **집계·학습·개인화**하는 Phase 2~4 레이어는 전무하다.

---

## 4. 분류 B 항목 상세 (notable_changes 산출 방식 변경)

설계(`phase3_frontend_redesign.md` §7-2)는 `alert_engine` 이벤트(`direction_flip`/`sharp_move`/`extreme_volatility`)를 `NotableChange` 포맷으로 변환하도록 규정했으나, 실제 `services/snapshot_builder.py`(L108~160)는 **이전 스냅샷 대비 `|Δscore| ≥ 0.3`** 기준으로 직접 생성한다. 사용자에게 보이는 결과 표시는 동일하나:

- **트리거 소스 차이**: alert 재활용(설계) → score 변화 직접 계산(구현)
- **원칙 충돌 소지**: 설계의 "내부 점수 숨김·alert 재활용" 의도와 부분 충돌 (score는 내부 점수)
- **기능적 회귀는 아님**. 다만 향후 PR-10 정식 연동/Phase 2 alert 강화 시 재정렬 필요.

---

## 5. 6/9 → 6/15 델타

| 항목 | 6/9 | 6/15 | 변화 |
|------|-----|------|------|
| thesis/models 클래스 수 | 12 | 12 | 없음 |
| ValidityScore 모델 | 부재 | 부재 | 없음 |
| 합성 에이전트/Online LR/벡터화 | 부재 | 부재 | 없음 |
| FE-PR-7~11 화면 (탭/히트맵/히스토리/아카이브/DNA) | 0건 | 0건 | 없음 |
| Phase 3-B 대시보드 컴포넌트 | 구현 | 구현 | 없음 |
| `tasks/summary.py` (PR-10) | 구현·Beat 등록 | 구현·Beat 등록(`config/celery.py:680`) | 없음 |

**결론**: 본 회차는 6/9 감사 결론을 6/15 시점에서 코드 재검증으로 재확인. 그 사이 Thesis Control 도메인에 설계 갭을 좁히는 신규 구현은 없었음.

---

## 6. 권고 (코드 미수정 — 기록만)

1. **CLAUDE.md 정정**: "진행 중: Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)" → 실제는 Phase 3-B(대시보드 리디자인) 완료 + FE-PR-7~11 미착수. stale 기재 갱신 필요.
2. **명명 규칙 정리**: "Phase 3" 3중 의미(3-A 백엔드 ML / 3-B 대시보드 / 3-C 깊이·회고·프로필) + PR 번호 중복(7~10)을 DECISIONS.md에 명문화하여 향후 혼동 차단.
3. **트랙 결정**: 깊이/회고/프로필(FE-PR-7~11) 트랙을 **재개할지 공식 폐기할지** 결정 후 Phase2_completion_summary §8에 상태 표기.
4. **notable_changes(분류 B)**: Phase 2 alert 엔진 강화 시점에 설계대로 alert 기반으로 재정렬할지 score 기반을 정식 채택할지 결정.

---

> 본 감사는 읽기 전용이며 어떠한 코드/문서도 수정하지 않았다. 위 권고는 후속 세션의 판단 자료로만 제공된다.
