# Thesis Control 설계 갭 감사

> 감사일: 2026-05-13
> 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드) 실제 구현
> 분류: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체
> 작성자: claude (read-only audit, 코드 수정 없음)

---

## 0. 사전 주의: "FE-PR-7~11"이라는 명칭이 두 문서에서 의미가 다름

설계 폴더 안에 같은 번호(FE-PR-7~11)를 다른 의미로 쓰는 두 문서가 공존한다.
보고서 전 구간에서 둘을 구분하기 위해 다음 약칭을 쓴다.

| 약칭 | 출처 | 내용 |
| --- | --- | --- |
| **재설계-PR** | `plan/thesis_control_phase3_frontend_redesign.md` (2026-03-18) | "대시보드 시각 리디자인" = 실제값 카드 + AI 분석 + 미니차트 + AI 요약 파이프라인 (PR-7 백엔드 / PR-8 카드+AI / PR-9 차트+정리 / PR-10 AI 파이프라인) |
| **확장-PR** | `frontend/task_done/Phase2_completion_summary.md` §8 (2026-03-16) | "Phase 3 = 깊이 + 회고 + 프로필" = 탭 구조 + 히트맵 + 히스토리 + 마감 아카이브 + DNA 프로필 (FE-PR-7~11) |

재설계-PR은 Phase 2 완료 이틀 뒤 작성된 후속 계획서이고, 확장-PR은 Phase 2 완료 시점에 제시된 "원래의 Phase 3 로드맵"이다. **두 PR 트랙은 서로 별개의 작업 묶음**이다.

---

## 1. 요약 (Phase별 구현률)

| Phase / 트랙 | 분류 | 비고 |
| --- | --- | --- |
| **Phase 1 (관제 엔진 + 이벤트 수집)** — Roadmap §1 | **A 완전 구현** (~95%) | Stage 0~3 수학 엔진, EOD 3 Task, HypothesisEvent / ValidityRecord / InvestorDNA 모델 모두 존재 |
| **Phase 2 (유효성 활성화 + DNA 슬라이더 + 역제안)** — Roadmap §2 | **C 미구현** | ValidityScore 집계 테이블, personalization slider, contrarian nudge 모두 없음 (DNA 필드만 미리 존재) |
| **Phase 3 (합성 에이전트 + Online LR + 블렌딩)** — Roadmap §3 | **C 미구현** | SyntheticBootstrapper, ValidityWeightLearner, is_synthetic 필드 모두 없음 |
| **Phase 4 (벡터 스코어링)** — Roadmap §4 | **C 미구현** | dna_vector / validity_vector / cosine similarity 모두 없음 |
| **재설계-PR-7~10 (대시보드 시각 리디자인)** | **A 완전 구현 (변형)** | PR-7 백엔드 100%, PR-8/9는 별도 컴포넌트 분리 대신 `IndicatorRow.tsx` 단일 통합 컴포넌트로 변형 구현, PR-10 AI 요약 Celery Task + Beat schedule 등록 완료 |
| **확장-PR-7~11 (Phase 3 깊이/회고/프로필)** | **C 미구현** | 대시보드 탭 구조, Finviz 히트맵 UI, 가설 히스토리 탭, 마감 아카이브 페이지, 투자자 DNA 프로필 페이지 모두 라우트·페이지·컴포넌트 모두 없음 |

전체 구현률 추정: **Phase 1 ✓ + 대시보드 리디자인 ✓ = 약 65%**. Phase 2/3 백엔드 학습 레이어, 확장-PR-7~11 모두 보류 상태.

---

## 2. 문서별 상태 테이블

### 2.1 Roadmap (`plan/thesis_control_integrated_roadmap.md`)

| 항목 | 설계 위치 | 분류 | 근거 |
| --- | --- | --- | --- |
| Stage 0~3 수학 엔진 (v2.3.2) | §1.1 | A | `thesis/services/snapshot_builder.py`, `arrow_calculator.py`, `data_validator.py`, `premise_aggregator.py`, `thesis_state_machine.py` |
| HypothesisEvent 모델 (13 event_type) | §1.2 | A | `thesis/models/learning.py:7-52` — 13개 choices 모두 존재 |
| ValidityRecord 2×2 매트릭스 | §1.3 | A | `thesis/models/learning.py:55-94`, `thesis_views.py:277-286` (`_compute_validity_score`) |
| InvestorDNA 기본 통계 | §1.4 | A | `thesis/models/learning.py:97-152` (accuracy_rate, ai_accept_rate, top_down_ratio 모두 구현) |
| 가설 close 시 InvestorDNA 자동 갱신 | §1.4 | A | `thesis_views.py:295-336` `_update_investor_dna` |
| **ValidityScore 집계 테이블** (sample_count≥5 활성화) | §2.1 | C | 모델 `learning.py`에 없음. Phase 2 트리거(가설 마감 10건+)에 미도달 가능성 |
| **유효성 점수로 indicator_matcher 개선** | §2.2 | C | `services/indicator_matcher.py`에 `validity_boost` / `confidence` 분기 없음 |
| **DNA 적합도 슬라이더 (personalization_weight 적용)** | §2.3 | C | `InvestorDNA.personalization_weight` 필드만 존재(default=0.5), 실제 매칭 로직에서 사용처 없음 |
| **Contrarian Nudge (역제안)** | §2.4 | C | `indicator_matcher.py`에 `is_nudge` / `nudge_reason` 분기 없음 |
| 상관계수 자동 할인 / Adaptive Decay/Window / Sustained Extreme | §2.5 | C | v2.3.2 정의는 있으나 추가 구현 흔적 없음 |
| **SyntheticBootstrapper (다투자자 페르소나 시뮬레이션)** | §3.1 | C | 신규 service/task 없음 |
| **Online Logistic Regression (ThesisWeightLearner)** | §3.2 | C | `services/`에 없음 |
| **합성/실제 블렌딩 (is_synthetic + blend_ratio)** | §3.3 | C | `ValidityRecord`에 `is_synthetic` 필드 없음 |
| Phase 4: dna_vector / validity_vector / cosine similarity / 사용자 유사도 | §4 | C | 없음 |

### 2.2 핵심 설계서 (`plan/thesis_control_design.md`)

| 항목 | 설계 위치 | 분류 | 근거 |
| --- | --- | --- | --- |
| Thesis / ThesisPremise / ThesisIndicator / IndicatorReading / ThesisSnapshot / ThesisAlert | §4.2 | A | `thesis/models/*.py` — 6개 모두 존재. v2.3.2 추가 필드(epsilon/window/decay/min_valid/max_valid/max_change_pct/validation_status 등) 포함 |
| ThesisFollow / PopularThesisCache (커뮤니티) | §4.2 | B | 모델은 `community.py`에 있음. API/UI는 없음 (인기 가설 진입 경로 3 미구현) |
| 5가지 가설 진입 경로 (news/free_input/popular/template/chainsight) | §2.3 | B | `Thesis.entry_source` 필드 + `ConversationStartView` / `NewsIssuesView` / `SuggestThesesView` 존재. 그러나 popular/template/chainsight 경로의 전용 UI 없음 — frontend `EntryPointGrid.tsx`에 "뉴스 기반 / 자유 입력" 2개만 |
| `[근거] 시스템` (롱프레스 용어 / 전제 탭 설명 / 지표 [근거]) | §2.4 | B | 백엔드 `recommendation_reason` 필드(`indicator.py:58-61`) + 프론트엔드 `IndicatorRow.tsx:158-173` 펼침 영역에 description/recommendation_reason 노출. 다만 "롱프레스 → BottomSheet" 인터랙션은 빌더에만 일부 적용 (`docs/thesis_control/frontend/task_done/FE-PR-3` 참조), 대시보드에는 없음 |
| 모니터링 3개 뷰 (카드뷰 / 히트맵 / 그래프뷰) | §3.4 | B | DashboardView API가 `heatmap.cells`/`rows`/`cols` 반환 (`monitoring_views.py:176-180`, 196-203). 그러나 프론트엔드는 **세로 1xN IndicatorRow 리스트만** 사용 — 히트맵 / 그래프 탭 UI 없음 |
| 모바일 제스처 (롱프레스/스와이프/쉐이크) | §3.5 | B | 빌더에서만 부분 적용. 대시보드는 클릭 토글(`IndicatorRow.tsx:81-84`)로 변형됨 |
| 변화 감지 알림 (direction_flip / sharp_move 등) | §3.7 | A | `ThesisAlert.ALERT_TYPE_CHOICES` 11종 정의 (`monitoring.py:37-49`), `alert_engine.py`에서 생성 |
| 가설 마감 복기 ("가장 유용했던 지표" / "예상과 달랐던 부분") | §3.9 | C | 마감 UI는 outcome 3종(correct/incorrect/neutral) + outcome_note만 받음(`close/page.tsx`). 복기 텍스트 / 지표별 회고 / ValidityMatrix UI 없음 |
| Neo4j 그래프 모델 (Thesis-Premise-Indicator-News) | §4.4 | C | `thesis/`에 Neo4j 연동 코드 없음. 별도 `graph_analysis/` 앱은 있으나 thesis 연결 미구현 |
| Celery Task: scan_thesis_news / update_popular_thesis_cache / prepare_daily_issues | §5.3 | C | EOD 3 task + summary 1 task만 등록됨 (`config/celery.py:651-679`) |
| `generate_thesis_summaries` Celery (AI 일일 요약) | §5.3 | A | `thesis/tasks/summary.py` 완전 구현, Beat schedule `thesis-generate-summaries` 18:35 ET 등록 (`config/celery.py:672-676`) |

### 2.3 재설계-PR (`plan/thesis_control_phase3_frontend_redesign.md`)

| 항목 | 설계 위치 | 분류 | 근거 |
| --- | --- | --- | --- |
| **PR-7** `ThesisIndicator.display_unit` 필드 추가 | §4.1 | A | `indicator.py:73-76` |
| PR-7 `_infer_unit()` fallback + 데이터 마이그레이션 | §4.3, §4.7 | A | `monitoring_views.py:346-364` |
| PR-7 DashboardView raw_value / change_pct / raw_value_unit / previous_raw_value | §4.2 | A | `monitoring_views.py:94-174` (분기지표 확장까지 포함 — 설계에 없는 보너스 구현) |
| PR-7 `IndicatorReadingsView` (GET readings/?days=14) | §4.4 | A | `monitoring_views.py:260-290`. 추가로 FMP fallback(`_fetch_fmp_history`)까지 구현 — 설계 범위 초과 |
| PR-7 thesis 응답에 `ai_summary` + `notable_changes` | §4.2 | A | `monitoring_views.py:216-218` |
| **PR-8** `DashboardIndicator` 타입 확장 (raw_value 등 4필드) | §5.1 | A | `frontend/lib/thesis/types.ts` 확인 필요 (코드에서 사용 중) |
| PR-8 `formatRawValue` / `formatChangePct` / `supportLabel` utils | §5.4 | A | `frontend/lib/thesis/utils.ts` 사용 (`IndicatorRow.tsx:11`) |
| PR-8 **`RealValueIndicatorCard.tsx`** (별도 카드 컴포넌트) | §5.6 | **D 폐기·대체** | `components/thesis/dashboard/`에는 `RealValueIndicatorCard.tsx` 파일이 있음 (3014 bytes) — 그러나 page에서 미사용. 실제 사용 컴포넌트는 `IndicatorRow.tsx`로 통합됨. **두 파일이 공존하는 dead-code 가능성** |
| PR-8 `AISummarySection.tsx` | §5.7 | A | `dashboard/AISummarySection.tsx` 존재, page에서 사용 |
| PR-8 `NotableChangesSection.tsx` | §5.8 | A | `dashboard/NotableChangesSection.tsx` 존재, page에서 사용 |
| PR-8 page.tsx에서 `OverallMoon` 제거 + `DashboardIndicatorCard` 교체 | §5.9 | A | `[thesisId]/page.tsx`에서 OverallMoon import 없음, DashboardIndicatorCard 미사용 |
| **PR-9** `ChartToggleButton.tsx` (`ChartToggleButton.tsx` 파일은 존재) | §6.1 | **D 폐기·대체** | `dashboard/ChartToggleButton.tsx` 572bytes 존재. 그러나 page에서 미사용 — 차트 토글은 `IndicatorRow.tsx`의 `expanded` state로 지표 행 단위로 변형됨 |
| PR-9 `PeriodSelector.tsx` (`PeriodSelector.tsx` 파일은 존재) | §6.2 | **D 폐기·대체** | `dashboard/PeriodSelector.tsx` 737bytes 존재. page에서 미사용. 기간 선택은 `IndicatorRow.tsx:15-20`에 1M/1Y/3Y/5Y 인라인 버튼으로 변형됨 (설계는 7D/14D/30D 3옵션) |
| PR-9 `IndividualMiniCharts.tsx` | §6.5 | **D 폐기·대체** | `dashboard/IndividualMiniCharts.tsx` 3572bytes 존재. page에서 미사용. 차트는 `IndicatorRow.tsx`에 `AreaChart` (160px 높이)로 통합 (`IndicatorRow.tsx:196-227`) |
| PR-9 `useAllIndicatorReadings` 훅 | §6.4 | C | `useQueries` 일괄 호출 패턴 없음. 대신 IndicatorRow 단위로 `useIndicatorReadings(expanded && isDaily)` 패턴 사용 (`IndicatorRow.tsx:59-61`) — 펼쳤을 때만 lazy fetch |
| PR-9 `OverallMoon` / `DashboardIndicatorCard` / `RecentChange` 삭제 | §6.8 | B | page에서 import 없음 — 그러나 파일 자체 삭제 여부 미확인. `MoonPhase` 컴포넌트는 `(list)/page.tsx:10`에서 EmptyTheses용으로 여전히 사용 중 |
| **PR-10** `generate_thesis_summaries` Celery task | §7.1 | A | `thesis/tasks/summary.py:79-142` (Gemini 2.5 Flash 동기 호출, 80-200자 요약, force/target_date 옵션) |
| PR-10 `notable_changes` 자동 채움 | §7.2 | B | `snapshot_builder.py:106-119` — alert_engine 이벤트 재활용이 아닌 "이전 score 대비 \|delta\|≥0.3" 단순 규칙으로 변형됨. 설계의 `change_type=sharp_move/direction_flip/threshold_cross/streak` 분기는 없음 |
| PR-10 Weekly Health Check | §7.3 | C | 향후 작업 — 미구현 |

### 2.4 확장-PR (`frontend/task_done/Phase2_completion_summary.md` §8) — Phase 3 = 깊이 + 회고 + 프로필

| FE-PR | 제목 | 분류 | 근거 |
| --- | --- | --- | --- |
| **FE-PR-7** 대시보드 탭 구조 + 상세 탭 (3탭: 관제/상세/히스토리) + 전제 CRUD | **C 미구현** | `[thesisId]/page.tsx`는 단일 페이지. `Tabs` 컴포넌트 없음. 전제 CRUD는 API(`ThesisPremiseViewSet`)는 있으나 UI에서 호출 없음 |
| **FE-PR-8** Finviz 스타일 히트맵 + 지표 상세 편집 (weight / support_direction 토글) | **C 미구현** | DashboardView가 `heatmap.cells` 반환은 하지만 프론트엔드 페이지에서 사용 안 함. 지표 편집은 `[thesisId]/indicators/page.tsx`에 토글/삭제만 — weight/support_direction 편집 UI 없음 (모델 필드 자체는 `indicator.py:48-65` 존재) |
| **FE-PR-9** 히스토리 탭 + recharts 라인 차트 + 스냅샷 타임라인 | **C 미구현** | 가설 단위 스냅샷 히스토리 페이지 없음. 개별 지표 시계열 차트만 IndicatorRow 펼침에 존재 (`IndicatorRow.tsx:196-227`). `ThesisSnapshot.overall_score` 타임라인 시각화 컴포넌트 없음 |
| **FE-PR-10** 마감 아카이브 + 요약 ValidityMatrix | **C 미구현** | `/thesis/archive/` 라우트 없음 (`frontend/app/thesis/`에 존재 안 함). closed 가설은 `(list)/page.tsx`에서 `t.status === 'active'`로 필터되어 목록에서 빠짐 — closed 가설 별도 진입점 없음. ValidityMatrix UI 없음 |
| **FE-PR-11** 투자자 DNA 프로필 (AccuracyRing + CategoryChart + 기술 부채 정리) | **C 미구현** | `/thesis/dna/` 또는 `/thesis/profile/` 라우트 없음. `InvestorDNA` API endpoint 없음 (`thesis/urls.py`, `views/`에서 노출 안 됨). 프로필 페이지 / 시각화 컴포넌트 전무 |

### 2.5 보조 문서

| 문서 | 분류 | 비고 |
| --- | --- | --- |
| `plan/thesis_control_math_model_final.md` (v2.3.2) | A | Stage 0~3 모두 코드에 반영 |
| `plan/thesis_control_implementation_guide.md` | A | 핵심 모델·서비스 매핑 일치 |
| `plan/talking_builder/llm_builder_plan.md` + redesign_v2 | A | `thesis/services/thesis_builder.py` (79KB) 대규모 구현됨 |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | A (보너스) | `quarterly_metric_fetcher.py` + DashboardView 분기지표 확장 + `QuarterlySparkline.tsx` 모두 구현됨. **설계 범위 외 추가 작업** |
| `work_done/phase_a_llm_builder.md` | A | LLM 빌더 Phase A 완료 보고 |
| `indicator_catalog_audit 2.md` | — | 본 감사 범위 외 (지표 카탈로그 별도 감사 문서) |

---

## 3. Phase 3 미구현 항목 상세

### 3.1 확장-PR 트랙 (Phase2 summary §8 정의) — 모두 (C) 미구현

#### FE-PR-7: 대시보드 탭 구조 + 전제 CRUD

- **누락 라우트**: 없음 (단일 `[thesisId]/page.tsx`가 모든 뷰 담당)
- **누락 컴포넌트**: `DashboardTabs` 또는 동등한 탭 네비게이션, `PremiseEditor`, `PremiseList`
- **누락 mutation**: 프론트엔드 `lib/thesis/mutations.ts`에 `useAddPremise` / `useRemovePremise` / `useTogglePremise` 등 없음 — `ThesisPremiseViewSet`(`thesis_views.py:147-188`) POST/DELETE는 백엔드 준비 완료
- **재사용 가능 자원**: 백엔드 API 100% 준비됨 + `HypothesisEvent` 자동 기록까지 (`thesis_views.py:165-187`)

#### FE-PR-8: Finviz 히트맵 + 지표 weight/direction 편집

- **백엔드 준비도**: DashboardView가 `{ heatmap: { rows, cols, cells: [{name, color, degree}] } }` 이미 반환(`monitoring_views.py:196-225`)
- **누락 UI**: `Heatmap.tsx` (CSS grid + 셀별 color/degree 매핑), `IndicatorEditSheet` (weight 슬라이더 + support_direction 토글)
- **모델 필드는 이미 존재**: `ThesisIndicator.weight`(default=1.0), `support_direction`(positive/negative) — `indicator.py:48-65`
- **누락 API**: `PATCH /api/v1/thesis/{id}/indicators/{ind_id}/` (DRF `ThesisIndicatorViewSet`은 ModelViewSet이라 자동 지원되지만 frontend에서 호출 안 됨)

#### FE-PR-9: 가설 히스토리 탭 (스냅샷 타임라인)

- **데이터 준비도**: `ThesisSnapshot`은 매일 18:30 ET에 자동 생성(`config/celery.py:665-669`). `overall_score`, `state`, `indicator_degrees`, `notable_changes`, `ai_summary` 모두 누적 중
- **누락 API**: `GET /api/v1/thesis/{id}/snapshots/` 엔드포인트 없음. `ThesisSnapshot` 직접 노출하는 view/serializer 없음
- **누락 UI**: `ThesisHistoryTimeline.tsx` (line chart with score over time), `SnapshotCard` (날짜별 상태/요약 카드)

#### FE-PR-10: 마감 아카이브 + ValidityMatrix

- **데이터 준비도**: `Thesis.status='closed'` + `outcome` + `closed_at` 모두 저장됨. `ValidityRecord`는 가설 마감 시마다 지표별로 1건씩 생성됨(`thesis_views.py:86-103`)
- **누락 라우트**: `/thesis/archive/` (closed 가설 목록 페이지)
- **누락 API**: `GET /api/v1/thesis/?status=closed` 자체는 지원(`thesis_views.py:46-50` query param 필터)되지만, 마감 가설별 ValidityRecord 묶음 조회 endpoint(`GET /api/v1/thesis/{id}/validity/`)는 없음
- **누락 UI**: `ArchiveList.tsx`, `ValidityMatrix.tsx` (2×2 매트릭스 시각화: indicator_aligned × thesis_correct), `MostUsefulIndicator` (highest score indicator)
- **설계 의도**: "가장 유용했던 지표" / "예상과 달랐던 부분" 정성적 회고 (`thesis_control_design.md:646-655`) — 백엔드 데이터는 있지만 LLM으로 정리하는 로직 없음

#### FE-PR-11: 투자자 DNA 프로필

- **데이터 준비도**: `InvestorDNA` 모델 + 가설 마감 시 자동 갱신 로직 100% 완성 (`thesis_views.py:295-336`). `accuracy_rate`, `ai_accept_rate`, `top_down_ratio` 모두 property로 즉시 사용 가능
- **누락 API**: `GET /api/v1/thesis/dna/` 또는 `users/dna/` 엔드포인트 없음. `InvestorDNA`를 노출하는 view/serializer 없음
- **누락 라우트**: `/thesis/dna/` 또는 `/thesis/profile/` 페이지 없음
- **누락 UI**: `AccuracyRing` (correct_count/(correct+incorrect) 도넛), `CategoryChart` (premise_category_counts 바차트), `TopDownRatioGauge`, `AIAcceptRateCard`
- **차단 요인**: 데이터는 차곡차곡 쌓이는데 사용자에게 보여줄 수단이 없음 → Phase 1에서 의도된 "기록만, 활용은 Phase 2" 상태에 머무름

### 3.2 재설계-PR 트랙의 부분 갭

#### PR-8 / PR-9 `RealValueIndicatorCard` / `ChartToggleButton` / `PeriodSelector` / `IndividualMiniCharts` 파일은 존재하지만 미사용

`frontend/components/thesis/dashboard/` 안에 4개 파일이 모두 있으나(`RealValueIndicatorCard.tsx` 3014b, `ChartToggleButton.tsx` 572b, `PeriodSelector.tsx` 737b, `IndividualMiniCharts.tsx` 3572b), `[thesisId]/page.tsx`에서 import되지 않음. 실제로는 `IndicatorRow.tsx`(11496b) 한 컴포넌트가 카드 + 토글 + 기간 선택 + 미니차트를 모두 흡수.

- **잠재적 dead code**: 4개 파일 약 8KB. 삭제 또는 통합 결정 필요
- **설계 PR과 어긋남**: `phase3_frontend_redesign.md §10` 체크리스트의 "절대 하지 말 것" 중 일부는 잘 지킴 (Zustand 안 만듦, V2 별도 메서드 안 만듦), 그러나 "확인할 것" 중 `MoonPhase.tsx` 잔존 여부는 (list)/page.tsx에서 여전히 사용 중

#### PR-10 `notable_changes` 변환 로직이 설계와 다름

- 설계(§7.2): `alert_engine.py` 이벤트 재활용 (alert_type을 NotableChange.change_type으로 매핑, severity 분류)
- 실제(`snapshot_builder.py:105-122`): "이전 스냅샷 score 대비 \|delta\|≥0.3"인 지표만 단순 기록. `change_type` 분류 없이 `{indicator_id, indicator_name, prev_score, curr_score, delta}` 형태
- 영향: 프론트엔드 `NotableChange` 타입의 `change_type` / `description` / `severity` 필드가 백엔드에서 채워지지 않을 수 있음 → `NotableChangesSection.tsx`가 fallback 텍스트로 표시할 가능성

### 3.3 Roadmap Phase 2/3 학습 레이어 — 통째로 미구현

다음 항목은 Roadmap §2~§3에 명시된 핵심 차별화 기능인데 코드 흔적이 전혀 없음:

| 항목 | 비고 |
| --- | --- |
| `ValidityScore` 집계 모델 | Phase 2 진입 조건(10건+ 마감 데이터) 미도달일 수 있음 |
| `personalization_weight` 슬라이더 UI + matcher 적용 | DNA 필드만 default=0.5로 미리 존재 |
| Contrarian Nudge (`is_nudge` / `nudge_reason`) | 후보 추천 시 1개 끼워넣기 로직 없음 |
| `is_synthetic` 필드 + 합성 데이터 블렌딩 | Phase 3 cold-start 해결 핵심 |
| `SyntheticBootstrapper` 페르소나 시뮬레이션 | 특허 청구항 3 (신규) — 완전 미착수 |
| `ThesisWeightLearner` (Online LR + L2 prior) | v2.3.2에서 이미 확정된 설계 |
| 지표 카테고리 중복 페널티 / 상관계수 자동 할인 / Adaptive Decay | v2.3.2 후속 작업 |
| `scan_thesis_news` / `update_popular_thesis_cache` / `prepare_daily_issues` Celery task | 인기 가설/뉴스 진입 경로 백엔드 부족 |

---

## 4. 즉시 권장 조치 (감사자 의견 — 결정은 보류)

본 감사는 read-only이며 결정을 강요하지 않는다. 다음은 갭 해소 우선순위에 대한 관찰만 기록한다.

1. **Dead code 정리**: `RealValueIndicatorCard.tsx` / `ChartToggleButton.tsx` / `PeriodSelector.tsx` / `IndividualMiniCharts.tsx` 4개 파일은 page.tsx에서 import 안 됨. 통합된 `IndicatorRow.tsx`로 일원화 완료된 것이라면 삭제 가능 (`docs/thesis_control/plan/thesis_control_phase3_frontend_redesign.md §6.8` 삭제 대상 리스트와 비교 필요).
2. **DNA 프로필 API 노출**: `InvestorDNA` 데이터는 매 가설 마감 시 자동 갱신 중. 단순 `GET /api/v1/thesis/dna/` endpoint 1개만 추가해도 FE-PR-11 진입 가능.
3. **`notable_changes` 스키마 통일**: 백엔드(`snapshot_builder.py`)와 프론트엔드(`types.ts` `NotableChange`) 간 필드명/구조 일치 여부 확인. 현재는 백엔드가 `delta`/`prev_score`/`curr_score`를, 프론트엔드 타입은 `change_type`/`severity`/`description`을 기대 — 매핑 누락 가능.
4. **확장-PR 트랙 vs 재설계-PR 트랙 우선순위 결정**: 현재 재설계-PR은 거의 완료, 확장-PR은 완전 미착수. CLAUDE.md "진행 중" 섹션은 "Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"이라 명시되어 있어 확장-PR 트랙 재개 의도가 보임.

---

## 5. 감사 메타데이터

- **읽은 설계 문서**: 14개 (plan/ 5 + frontend/task_done/ 8 + work_done/ 1, plan/talking_builder 5개 제외)
- **읽은 백엔드 코드**: `thesis/models/*.py` (6), `thesis/views/*.py` (3), `thesis/services/*.py` (일부 grep), `thesis/tasks/*.py` (2), `thesis/urls.py`, `config/celery.py` (Beat schedule)
- **읽은 프론트엔드 코드**: `app/thesis/(list|new|[thesisId])/*` (6 페이지), `components/thesis/dashboard/IndicatorRow.tsx`, `components/thesis/index.ts`
- **확인하지 않은 영역**: `thesis/services/thesis_builder.py` (79KB, LLM 빌더 로직 — 본 감사 범위 외), 알림 페이지 `(list)/alerts/page.tsx` 내부 구현, 지표 설정 페이지 `[thesisId]/indicators/page.tsx` 내부, builder 9개 컴포넌트 세부 동작
- **참고**: 4월~5월 nightly_auto_system의 thesis_design_gap_audit.md 11건이 같은 폴더 트리에 존재(`docs/nightly_auto_system/reports/4월/21일~5월/11일`). 본 보고서는 그중 가장 최신 시점(5/13) 스냅샷이며, 이전 보고서와의 diff는 별도 작업 영역.
