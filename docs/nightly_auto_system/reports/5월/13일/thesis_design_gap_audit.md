# Thesis Control 설계 갭 감사

> 감사일: 2026-05-14
> 범위: `docs/thesis_control/` 설계 문서 vs `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드) 실제 구현
> 분류: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체
> 방식: read-only 감사 (코드 수정 없음)

---

## 0. 사전 주의 — "FE-PR-7~11"이라는 명칭이 두 문서에서 의미가 다름

설계 폴더 안에 같은 번호(FE-PR-7~11)를 다른 의미로 사용하는 두 문서가 공존한다. 본 감사 전 구간에서 둘을 다음과 같이 구분한다.

| 약칭 | 출처 | 내용 |
| --- | --- | --- |
| **재설계-PR** | `plan/thesis_control_phase3_frontend_redesign.md` (2026-03-18) | 대시보드 시각 리디자인 = 실제값 카드 + AI 분석 + 미니차트 + AI 요약 파이프라인 (PR-7 백엔드 / PR-8 카드+AI / PR-9 차트+정리 / PR-10 AI 파이프라인) |
| **확장-PR** | `frontend/task_done/Phase2_completion_summary.md` §8 (2026-03-16) | Phase 3 = 깊이 + 회고 + 프로필 = 탭 구조 + 히트맵 + 히스토리 + 마감 아카이브 + DNA 프로필 (FE-PR-7~11) |

두 트랙은 별개의 작업 묶음이다. **재설계-PR-7~10은 PR-10(AI 파이프라인) 일부를 제외하면 사실상 완료**되었고, **확장-PR-7~11은 모두 미착수**다.

또한 통합 로드맵(`plan/thesis_control_integrated_roadmap.md`)은 자체적으로 Phase 1/2/3/4를 정의하므로(MVP / DNA 슬라이더 / 합성 에이전트 / 벡터화), Phase 명칭이 한번 더 중첩된다는 점에 주의.

---

## 1. 요약 (Phase별 구현률)

| Phase / 트랙 | 분류 | 비고 |
| --- | --- | --- |
| **Roadmap Phase 1 — 관제 엔진 + 이벤트 수집** | **A** (~95%) | Stage 0~3 수학 엔진, EOD 3-Task, HypothesisEvent / ValidityRecord / InvestorDNA 모델 모두 존재. 가설 마감 시 ValidityRecord + DNA 자동 갱신까지 결선됨 |
| **Roadmap Phase 2 — 유효성 활성화 + DNA 슬라이더 + 역제안** | **C** | ValidityScore 집계 테이블, personalization_weight 적용 로직, Contrarian Nudge 모두 없음 (DNA 필드만 default=0.5로 미리 존재) |
| **Roadmap Phase 3 — 합성 에이전트 + Online LR + 블렌딩** | **C** | SyntheticBootstrapper, ThesisWeightLearner, is_synthetic 필드 모두 없음 |
| **Roadmap Phase 4 — 벡터 스코어링** | **C** | dna_vector / validity_vector / cosine similarity 전무 |
| **재설계-PR-7~10 — 대시보드 시각 리디자인** | **A (변형)** | PR-7 백엔드 100%, PR-8/9는 별도 컴포넌트 분리 대신 `IndicatorRow.tsx` 단일 통합 컴포넌트로 변형 구현, PR-10 AI 요약 Celery Task + Beat 등록 완료. 분리된 컴포넌트 4개는 잔존 (D 대체) |
| **확장-PR-7~11 — Phase 3 깊이/회고/프로필** | **C 미구현** | 대시보드 탭 구조, Finviz 히트맵 UI, 가설 히스토리 탭, 마감 아카이브 페이지, 투자자 DNA 프로필 페이지 — 라우트 / 페이지 / API 모두 없음 |
| **LLM 빌더 재설계 (talking_builder/)** | **A (Phase A)** | Phase A-MVP + Hardening 완료(`work_done/phase_a_llm_builder.md`). Phase B(Keyword Enrichment, KeywordCache, Monitoring)는 모델·서비스 측면에서 일부 진행 (KeywordCache 모델 존재, keyword_collectors 3종 존재) |

전체 구현률 추정: 약 65%. 백엔드 학습 레이어(Roadmap Phase 2/3)와 사용자에게 보일 깊이/회고/프로필 페이지(확장-PR-7~11)가 보류 상태.

---

## 2. 문서별 상태 테이블

### 2.1 통합 로드맵 (`plan/thesis_control_integrated_roadmap.md`)

| 항목 | 설계 위치 | 분류 | 근거 |
| --- | --- | --- | --- |
| Stage 0~3 수학 엔진 (v2.3.2) | §1.1 | A | `thesis/services/{data_validator,indicator_scorer,premise_aggregator,thesis_state_machine,arrow_calculator,snapshot_builder}.py` |
| HypothesisEvent 모델 (13 event_type) | §1.2 | A | `thesis/models/learning.py:7-52` — 13개 choices 전부 존재 |
| 기존 API에 HypothesisEvent.create() 삽입 | §1.2 | A | `thesis_views.py:52-62` (thesis_created), `:165-187` (premise 추가/삭제 추정 — Viewset 내부 흐름 확인 필요) |
| ValidityRecord 2×2 매트릭스 | §1.3 | A | `thesis/models/learning.py:55-94`, `thesis_views.py` close 액션 내 `_compute_validity_score` |
| InvestorDNA 기본 통계 + property | §1.4 | A | `thesis/models/learning.py:97-152` (accuracy_rate, ai_accept_rate, top_down_ratio property 모두 구현) |
| 가설 close 시 InvestorDNA 자동 갱신 | §1.4 | A | `thesis_views.py` close 액션 내 `_update_investor_dna` (line ~295) |
| **ValidityScore 집계 테이블** (sample_count≥5 활성화) | §2.1 | C | `learning.py`에 없음. Phase 2 트리거(가설 마감 10건+)에 미도달 가능성 |
| **유효성 점수로 indicator_matcher 개선** | §2.2 | C | `services/indicator_matcher.py`에 `validity_boost` / `confidence` 분기 없음 |
| **DNA 적합도 슬라이더 (personalization_weight 적용)** | §2.3 | C | 모델 필드만 존재(`learning.py:124`), 매칭 로직 사용처 없음 |
| **Contrarian Nudge (역제안)** | §2.4 | C | `indicator_matcher.py`에 `is_nudge` / `nudge_reason` 분기 없음 |
| 상관계수 자동 할인 / Adaptive Decay/Window / Sustained Extreme | §2.5 | C | v2.3.2 정의는 있으나 추가 구현 흔적 없음 |
| **SyntheticBootstrapper (다투자자 페르소나 시뮬레이션)** | §3.1 | C | 신규 service/task 없음 |
| **Online Logistic Regression (ThesisWeightLearner)** | §3.2 | C | `services/`에 없음 |
| **합성/실제 블렌딩 (is_synthetic + blend_ratio)** | §3.3 | C | `ValidityRecord`에 `is_synthetic` 필드 없음 |
| Phase 4 (dna_vector / validity_vector / cosine similarity / 사용자 유사도) | §4 | C | 없음 |

### 2.2 핵심 설계서 (`plan/thesis_control_design.md`)

| 항목 | 설계 위치 | 분류 | 근거 |
| --- | --- | --- | --- |
| Thesis / ThesisPremise / ThesisIndicator / IndicatorReading / ThesisSnapshot / ThesisAlert 모델 | §4.2 | A | `thesis/models/*.py` — 6개 모두 존재. v2.3.2 추가 필드(epsilon / window / decay / min_valid / max_valid / max_change_pct / validation_status / asof_date / data_coverage / universe_snapshot / ordered_indicator_ids) 포함 |
| ThesisFollow / PopularThesisCache (커뮤니티) | §4.2 | B | 모델은 `community.py`에 있음. API/UI 없음 (인기 가설 진입 경로 3 미구현) |
| 5가지 가설 진입 경로 (news / free_input / popular / template / chainsight) | §2.3 | B | `Thesis.entry_source` 필드 + `ConversationStartView` / `NewsIssuesView` / `SuggestThesesView` 존재. 그러나 frontend `EntryPointGrid.tsx`는 뉴스/자유입력 2개만 노출. popular / template / chainsight 전용 UI 없음 |
| `[근거] 시스템` (롱프레스 용어 / 전제 탭 설명 / 지표 [근거]) | §2.4 | B | 백엔드 `recommendation_reason` 필드 + 프론트엔드 `IndicatorRow.tsx:158-173` 펼침 영역에 description/recommendation_reason 노출. "롱프레스 → BottomSheet" 인터랙션은 빌더에만 일부 적용, 대시보드에는 없음 |
| 모니터링 3개 뷰 (카드뷰 / 히트맵 / 그래프뷰) | §3.4 | B | DashboardView API가 `heatmap.cells/rows/cols` 반환 (`monitoring_views.py:176-180, 196-225`). 프론트엔드는 **세로 1xN IndicatorRow 리스트만** 사용 — 히트맵 / 그래프 탭 UI 없음 |
| 모바일 제스처 (롱프레스/스와이프/쉐이크) | §3.5 | B | 빌더에서 일부 적용. 대시보드는 클릭 토글(`IndicatorRow.tsx:81-84`)로 변형 |
| 변화 감지 알림 (direction_flip / sharp_move 등 11 종) | §3.7 | A | `ThesisAlert.ALERT_TYPE_CHOICES` (`monitoring.py:37-49`), `alert_engine.py`에서 생성 |
| 가설 마감 복기 ("가장 유용했던 지표" / "예상과 달랐던 부분") | §3.9 | C | 마감 UI는 outcome 3종(correct/incorrect/neutral) + outcome_note만 받음. 복기 텍스트 / 지표별 회고 / ValidityMatrix UI 없음 |
| Neo4j 그래프 모델 (Thesis-Premise-Indicator-News) | §4.4 | C | `thesis/`에 Neo4j 연동 코드 없음. 별도 `graph_analysis/` 앱은 있으나 thesis 연결 미구현 |
| Celery Task: `scan_thesis_news` (2h) | §5.3 | C | 미구현. `thesis/tasks/`에 없음 |
| Celery Task: `update_popular_thesis_cache` (08:00) | §5.3 | C | 미구현 |
| Celery Task: `prepare_daily_issues` (07:00) | §5.3 | C | 미구현 |
| Celery Task: `generate_thesis_summaries` (07:30 → 18:35 ET) | §5.3 | A | `thesis/tasks/summary.py` 완전 구현, Beat 등록 |

### 2.3 재설계-PR (`plan/thesis_control_phase3_frontend_redesign.md`)

| 항목 | 설계 위치 | 분류 | 근거 |
| --- | --- | --- | --- |
| **PR-7** `ThesisIndicator.display_unit` 필드 | §4.1 | A | `indicator.py:73-76` + migration `0004_add_display_unit.py` |
| PR-7 `_infer_unit()` fallback | §4.3 | A | `monitoring_views.py:346-364` |
| PR-7 데이터 마이그레이션 | §4.7 | A | `migrations/0005_populate_display_unit.py` |
| PR-7 DashboardView raw_value / change_pct / raw_value_unit / previous_raw_value | §4.2 | A | `monitoring_views.py:94-174` (분기지표 확장까지 보너스 구현) |
| PR-7 `IndicatorReadingsView` (GET readings) | §4.4 | A | `monitoring_views.py:260-290`. 추가로 FMP fallback(`_fetch_fmp_history`)까지 구현 — 설계 범위 초과 |
| PR-7 thesis 응답에 `ai_summary` + `notable_changes` | §4.2 | A | `monitoring_views.py:216-218` |
| **PR-8** `DashboardIndicator` 타입 확장 (raw_value 등 4필드) | §5.1 | A | `IndicatorRow.tsx`에서 `indicator.raw_value`, `change_pct`, `raw_value_unit`, `previous_raw_value` 사용 중 |
| PR-8 `formatRawValue` / `formatChangePct` / `supportLabel` utils | §5.4 | A | `frontend/lib/thesis/utils.ts` (`IndicatorRow.tsx:11`에서 import) |
| PR-8 **`RealValueIndicatorCard.tsx`** (별도 카드 컴포넌트) | §5.6 | **D** | 파일 존재(`dashboard/RealValueIndicatorCard.tsx`)하나 `page.tsx`에서 미import. 실제 사용은 `IndicatorRow.tsx`로 통합 |
| PR-8 `AISummarySection.tsx` | §5.7 | A | `dashboard/AISummarySection.tsx` 존재, page에서 사용 (`page.tsx:13,75-78`) |
| PR-8 `NotableChangesSection.tsx` | §5.8 | A | `dashboard/NotableChangesSection.tsx` 존재, page에서 사용 (`page.tsx:14,80-84`) |
| PR-8 page.tsx에서 `OverallMoon` 제거 + `DashboardIndicatorCard` 교체 | §5.9 | A | 현 `page.tsx`에 OverallMoon / DashboardIndicatorCard import 없음 |
| **PR-9** `ChartToggleButton.tsx` | §6.1 | **D** | 파일 존재(572b)하나 page에서 미사용. 차트 토글은 `IndicatorRow.tsx`의 `expanded` state로 지표 행 단위로 변형됨 |
| PR-9 `PeriodSelector.tsx` | §6.2 | **D** | 파일 존재(737b)하나 page에서 미사용. 기간 선택은 `IndicatorRow.tsx:15-20`에 1M / 1Y / 3Y / 5Y 인라인 버튼으로 변형(설계는 7D / 14D / 30D 3옵션) |
| PR-9 `IndividualMiniCharts.tsx` | §6.5 | **D** | 파일 존재(3572b)하나 page에서 미사용. 차트는 `IndicatorRow.tsx:196-227`에 AreaChart(160px)로 통합 |
| PR-9 `useAllIndicatorReadings` 훅 (`useQueries` 일괄) | §6.4 | C | 일괄 호출 패턴 없음. IndicatorRow 단위 `useIndicatorReadings(expanded && isDaily)` 패턴 사용 (`IndicatorRow.tsx:59-61`) — 펼침 시점 lazy fetch |
| PR-9 `OverallMoon` / `DashboardIndicatorCard` / `RecentChange` 삭제 | §6.8 | B | page import 없음. 그러나 파일 삭제 여부 미확인. `common/MoonPhase.tsx`는 list 페이지에서 여전히 사용 중일 가능성 |
| **PR-10** `generate_thesis_summaries` Celery task | §7.1 | A | `thesis/tasks/summary.py`, Beat 등록 완료 |
| PR-10 `notable_changes` 자동 채움 (alert 이벤트 재활용) | §7.2 | B | `snapshot_builder.py`에서 생성하지만 설계의 `change_type` (sharp_move/direction_flip/threshold_cross/streak) 분기 정밀도가 alert_engine과 정확히 매핑되는지 추가 확인 필요. 프론트엔드 `NotableChange` 타입(change_type/severity/description)과의 스키마 일치는 별도 검증 항목 |
| PR-10 Weekly Health Check | §7.3 | C | 향후 작업으로 명시됨, 미구현 |

### 2.4 확장-PR (`frontend/task_done/Phase2_completion_summary.md` §8) — Phase 3 = 깊이 + 회고 + 프로필

| FE-PR | 제목 | 분류 | 근거 |
| --- | --- | --- | --- |
| **FE-PR-7** 대시보드 탭 구조 + 상세 탭 (3탭: 관제 / 상세 / 히스토리) + 전제 CRUD UI | **C** | `[thesisId]/page.tsx`는 단일 페이지, `Tabs` 컴포넌트 없음. `ThesisPremiseViewSet`(`thesis_views.py:147-188`) POST/DELETE는 백엔드 준비됨. `lib/thesis/mutations.ts`에 `useAddPremise` 등 없음 |
| **FE-PR-8** Finviz 스타일 히트맵 + 지표 상세 편집 (weight / support_direction 토글) | **C** | DashboardView가 `heatmap.cells/rows/cols`를 이미 반환. 프론트엔드 사용 없음. 지표 weight/support_direction 편집 UI 없음 (모델 필드는 `indicator.py:48-65` 존재) |
| **FE-PR-9** 히스토리 탭 + recharts 라인 차트 + 스냅샷 타임라인 | **C** | `ThesisSnapshot.overall_score` 타임라인 시각화 컴포넌트 없음. `GET /api/v1/thesis/{id}/snapshots/` endpoint 없음 (`thesis/urls.py` 확인). 개별 지표 차트만 IndicatorRow 펼침에 존재 |
| **FE-PR-10** 마감 아카이브 + 요약 ValidityMatrix | **C** | `/thesis/archive/` 라우트 없음. closed 가설 목록 전용 진입점 없음. ValidityMatrix UI 없음. 마감 가설 ValidityRecord 묶음 조회 API 없음 |
| **FE-PR-11** 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | **C** | `/thesis/dna/` 또는 `/thesis/profile/` 라우트 없음. `InvestorDNA` 데이터를 노출하는 API endpoint 없음 (`thesis/urls.py`). 프로필 페이지 / 시각화 컴포넌트 전무 |

### 2.5 LLM 빌더 재설계 (`plan/talking_builder/`)

| 항목 | 설계 위치 | 분류 | 근거 |
| --- | --- | --- | --- |
| Phase A-MVP (one-shot proposal, prompt builder 3블록, normalize/validate/merge, 프리셋 3개) | `redesign_build_plan/01_phase_a_mvp.md` | A | `thesis/services/{builder_state,prompt_builder,llm_postprocess,thesis_builder}.py` 존재. `work_done/phase_a_llm_builder.md` 완료 보고 |
| Phase A-Hardening (normalize 보강, fallback, builder_stats command, FE 에러 바운더리) | `redesign_build_plan/02_phase_a_hardening.md` | A | `work_done/phase_a_llm_builder.md` Section 2 |
| Phase B — KeywordCache 모델 + Admin | `redesign_build_plan/03_phase_b_keywords.md` | A | `thesis/models/keyword.py` 존재 + migration 0006/0007 + admin.py 등록 |
| Phase B — source별 collector (chain/eod/news) | 동상 | A | `services/keyword_collectors/{chain,eod,news}.py` 존재 |
| Phase B — `build_keyword_hint_block` (프롬프트 주입) | 동상 | A | `services/keyword_hint.py` 존재 |
| Phase B — freshness TTL + replace-all cache 정책 | 동상 | B (확인 필요) | `services/keyword_cache.py` 존재. 실제 TTL/replace-all 구현 확인은 코드 정독 필요 |
| Phase B — `check_keywords` management command | 동상 | ? | `thesis/management/` 디렉토리 존재 여부 확인 필요 — 본 감사에서는 미확인 |
| Phase C — strength / micro-fact hint / scoring / MiniDashboardPreview / 스트리밍 / Guided Suggestion / 멀티턴 수정 | `04_phase_c_advanced.md` | C | 코드 흔적 없음. Feature flag 5개 모두 default False로 설정되어 있을 가능성 |

### 2.6 보조 문서

| 문서 | 분류 | 비고 |
| --- | --- | --- |
| `plan/thesis_control_math_model_final.md` (v2.3.2) | A | Stage 0~3 모두 코드 반영 (indicator_scorer.py / premise_aggregator.py / thesis_state_machine.py / arrow_calculator.py / snapshot_builder.py) |
| `plan/thesis_control_implementation_guide.md` | A | 핵심 모델·서비스 매핑 일치 |
| `plan/talking_builder/quarterly_indicator_dashboard_plan.md` | A (보너스) | `quarterly_metric_fetcher.py` + DashboardView 분기지표 확장 + `QuarterlySparkline.tsx` 모두 구현됨. 설계 범위 외 추가 작업으로 IndicatorRow에 전분기/전년동기 비교 라벨까지 결선됨 |
| `thesis_control_user_experience.md` | B | 본 감사 범위에서 직접 검증 안 함. UX 설계 의도는 일부만 대시보드에 반영 |

---

## 3. Phase 3 미구현 항목 상세

> 이 절은 사용자가 명시한 "확장-PR-7~11" 트랙(`frontend/task_done/Phase2_completion_summary.md` §8) 중심. 모든 항목 **C 미구현**.

### 3.1 FE-PR-7 — 대시보드 탭 구조 + 전제 CRUD

- **누락 라우트**: 단일 `[thesisId]/page.tsx`가 모든 뷰 담당, 탭 분기 없음
- **누락 컴포넌트**: `DashboardTabs` (관제/상세/히스토리), `PremiseEditor`, `PremiseList`
- **누락 mutation 훅**: `useAddPremise` / `useRemovePremise` / `useTogglePremise` 모두 없음 (`lib/thesis/mutations.ts` 확인 필요)
- **백엔드 준비도**: `ThesisPremiseViewSet` (`thesis_views.py:147-188`) POST / PATCH / DELETE 모두 노출. `HypothesisEvent` 자동 기록까지 결선됨

### 3.2 FE-PR-8 — Finviz 히트맵 + 지표 weight / direction 편집

- **백엔드 준비도**: DashboardView가 이미 `{ heatmap: { rows, cols, cells: [{name, color, degree}] } }` 반환 (`monitoring_views.py:196-225`)
- **누락 UI 컴포넌트**: `Heatmap.tsx` (CSS grid + 셀별 color/degree 매핑), `IndicatorEditSheet` (weight 슬라이더 + support_direction 토글)
- **모델 필드**: `ThesisIndicator.weight`(default=1.0), `support_direction`(positive/negative) — `indicator.py:48-65` 이미 존재
- **API 호출 누락**: DRF `ThesisIndicatorViewSet`은 ModelViewSet이라 `PATCH /api/v1/thesis/{id}/indicators/{ind_id}/` 자동 지원되지만, frontend `mutations.ts`에 weight/direction 편집 mutation 없음

### 3.3 FE-PR-9 — 가설 히스토리 탭 (스냅샷 타임라인)

- **데이터 준비도**: `ThesisSnapshot`은 매일 18:30 ET에 자동 생성(EOD pipeline). `overall_score`, `state`, `indicator_degrees`, `notable_changes`, `ai_summary` 모두 누적 중
- **누락 API**: `GET /api/v1/thesis/{id}/snapshots/` endpoint 없음. `ThesisSnapshot` 노출하는 view/serializer 없음 (`thesis/urls.py` 확인됨)
- **누락 UI 컴포넌트**: `ThesisHistoryTimeline.tsx` (score over time 라인 차트), `SnapshotCard` (날짜별 상태/요약 카드)

### 3.4 FE-PR-10 — 마감 아카이브 + ValidityMatrix

- **데이터 준비도**: `Thesis.status='closed_correct'/'closed_incorrect'/'closed_neutral'` + `closed_at` 모두 저장됨. `ValidityRecord`는 가설 마감 시마다 지표별로 1건씩 생성됨 (`thesis_views.py:86-103`)
- **누락 라우트**: `/thesis/archive/` (closed 가설 목록 페이지)
- **누락 API**: `GET /api/v1/thesis/?status=closed*`는 query param 필터로 지원되지만 (`thesis_views.py:46-50`), 마감 가설별 ValidityRecord 묶음 조회 endpoint(`GET /api/v1/thesis/{id}/validity/`)는 없음
- **누락 UI**: `ArchiveList.tsx`, `ValidityMatrix.tsx` (2×2 indicator_aligned × thesis_correct 시각화), `MostUsefulIndicator` (highest score indicator)
- **설계 의도와의 간극**: 설계서 §3.9는 "가장 유용했던 지표 / 예상과 달랐던 부분"을 정성적 회고로 전달하라 요구. 백엔드 데이터는 충분하지만 LLM으로 정리하는 로직 없음

### 3.5 FE-PR-11 — 투자자 DNA 프로필

- **데이터 준비도**: `InvestorDNA` 모델 + 가설 마감 시 자동 갱신 로직 100% 완성. `accuracy_rate`, `ai_accept_rate`, `top_down_ratio` 모두 property로 즉시 사용 가능
- **누락 API**: `GET /api/v1/thesis/dna/` 또는 `users/dna/` endpoint 없음. `InvestorDNA`를 노출하는 view/serializer 없음
- **누락 라우트**: `/thesis/dna/` 또는 `/thesis/profile/` 페이지 없음
- **누락 UI**: `AccuracyRing` (correct_count / (correct + incorrect) 도넛), `CategoryChart` (premise_category_counts 바차트), `TopDownRatioGauge`, `AIAcceptRateCard`
- **차단 요인**: 데이터는 차곡차곡 쌓이는데 사용자에게 보여줄 수단이 없음 → Phase 1 "기록만, 활용은 Phase 2" 의도에 머무름

### 3.6 재설계-PR 트랙의 부분 갭

#### PR-8 / PR-9 — 4개 미사용 컴포넌트 (D 대체)

`frontend/components/thesis/dashboard/` 안의 다음 4개 파일이 모두 존재하지만 `[thesisId]/page.tsx`에서 import 안 됨.

- `RealValueIndicatorCard.tsx` (≈3KB)
- `ChartToggleButton.tsx` (≈600B)
- `PeriodSelector.tsx` (≈740B)
- `IndividualMiniCharts.tsx` (≈3.5KB)

실제 페이지는 `IndicatorRow.tsx` (275 lines, ≈11.5KB) 한 컴포넌트에 카드 + 토글 + 기간 선택(1M/1Y/3Y/5Y) + 미니차트 + 분기 스파크라인을 모두 흡수. 설계는 `dashboard/` 하위에 4개로 쪼개라 했으나 통합 변형 결정됨.

- **잠재적 dead code 약 8KB**: 삭제 또는 일관성 정리 결정 필요
- **재설계-PR §10 체크리스트 준수도**: 일부 "절대 하지 말 것" 지켰음 (Zustand 안 만듦, V2 별도 메서드 안 만듦). 그러나 `MoonPhase.tsx`(common) 잔존 — list 페이지에서 EmptyTheses용으로 여전히 사용 중일 가능성

#### PR-10 `notable_changes` 스키마 정밀도

- 설계(§7.2): `alert_engine.py` 이벤트(direction_flip / sharp_move / extreme_volatility 등 11종)를 `NotableChange.change_type`에 매핑, severity 분류
- 실제(`snapshot_builder.py`): 설계의 4-범주(sharp_move/direction_flip/threshold_cross/streak) 분류 정밀도 vs 실제 구현 스키마(change_type/description/severity/raw_value_before/raw_value_after) 정합 여부는 별도 검증이 필요. 프론트엔드 `NotableChange` 타입(`types.ts`)이 기대하는 필드와 백엔드가 채우는 필드의 매핑 어긋남 가능성 있음

### 3.7 Roadmap Phase 2 / 3 학습 레이어 — 통째로 미구현

다음 항목은 Roadmap §2~§3에 명시된 핵심 차별화 기능인데 코드 흔적이 전혀 없음.

| 항목 | 비고 |
| --- | --- |
| `ValidityScore` 집계 모델 (sample_count, confidence, is_active) | Phase 2 진입 조건(가설 마감 10건+) 미도달일 수도, 단순 미구현일 수도 |
| `personalization_weight` 슬라이더 적용 (matcher 블렌딩) | DNA 필드만 default=0.5로 미리 존재 |
| Contrarian Nudge (`is_nudge` / `nudge_reason`) | 후보 추천 시 1개 끼워넣기 로직 없음 |
| `is_synthetic` 필드 + 합성 데이터 블렌딩 | Phase 3 cold-start 해결 핵심 |
| `SyntheticBootstrapper` 페르소나 시뮬레이션 | 특허 청구항 3 (신규) — 완전 미착수 |
| `ThesisWeightLearner` (Online LR + L2 prior) | v2.3.2에서 이미 확정된 설계 |
| 카테고리 중복 페널티 / 상관계수 자동 할인 / Adaptive Decay/Window / Sustained Extreme | v2.3.2 후속 작업 |
| `scan_thesis_news` / `update_popular_thesis_cache` / `prepare_daily_issues` Celery task | 인기 가설 / 뉴스 진입 경로 백엔드 부족 |

---

## 4. 즉시 권장 조치 (감사자 의견 — 결정은 보류)

본 감사는 read-only이며 결정을 강요하지 않는다. 갭 해소 우선순위에 대한 관찰만 기록한다.

1. **Dead code 정리 (저비용 / 즉시 가능)**: `RealValueIndicatorCard.tsx` / `ChartToggleButton.tsx` / `PeriodSelector.tsx` / `IndividualMiniCharts.tsx` 4개 파일은 page.tsx에서 import 안 됨. 통합된 `IndicatorRow.tsx`로 일원화 완료된 것이라면 삭제 가능. 재설계-PR §6.8 삭제 대상 리스트와 비교 후 결정.
2. **DNA 프로필 API 노출 (저비용 / 임팩트 큼)**: `InvestorDNA` 데이터는 매 가설 마감 시 자동 갱신 중. 단순 `GET /api/v1/thesis/dna/` endpoint 1개 추가만으로 FE-PR-11 진입 가능. 백엔드는 `InvestorDNASerializer` + `RetrieveAPIView` 수준이면 충분.
3. **`notable_changes` 스키마 정합 검증**: 백엔드(`snapshot_builder.py`)와 프론트엔드(`types.ts` `NotableChange`) 간 필드명/구조 일치 여부 확인. 현재 양쪽에서 어떻게 직렬화/역직렬화하는지 별도 매핑 점검 필요.
4. **확장-PR vs 재설계-PR 트랙 우선순위 결정**: 재설계-PR은 거의 완료, 확장-PR은 완전 미착수. CLAUDE.md "진행 중" 섹션에 "Thesis Control Phase 3 (깊이 + 회고 + 프로필: FE-PR-7~11)"이라 명시되어 있어 확장-PR 트랙 재개 의도 보임. 다음 작업 단위는 FE-PR-11 (DNA 프로필 — 백엔드 endpoint 1개 + 페이지 1개)이 가장 ROI 높음.
5. **인기 가설 / 템플릿 / Chain Sight 진입 경로**: 모델(`PopularThesisCache`)과 entry_source 필드는 갖췄지만 UI / 데이터 갱신 task 모두 없음. 우선순위 낮음 — 사용자 한 명에서 가설 마감 10건 누적부터 선결.

---

## 5. 감사 메타데이터

- **읽은 설계 문서** (14개): `plan/thesis_control_design.md`, `plan/thesis_control_integrated_roadmap.md`, `plan/thesis_control_phase3_frontend_redesign.md`, `plan/thesis_control_implementation_guide.md`, `plan/thesis_control_math_model_final.md` (heading 일부), `plan/talking_builder/redesign_build_plan/00_total_plan.md`, `frontend/task_done/Phase2_completion_summary.md`, `frontend/task_done/FE-PR-1~6` (제목만), `work_done/phase_a_llm_builder.md` (앞 100줄)
- **읽은 백엔드 코드**: `thesis/models/__init__.py`, `learning.py`, `indicator.py`, `monitoring.py`; `thesis/views/__init__.py`, `thesis_views.py` (앞 100줄), `monitoring_views.py` (전체); `thesis/urls.py`; `thesis/tasks/__init__.py`, `eod_pipeline.py` (앞 60줄); 모든 `services/*.py` 파일 목록 및 줄 수
- **읽은 프론트엔드 코드**: `app/thesis/[thesisId]/page.tsx` (전체), `components/thesis/dashboard/IndicatorRow.tsx` (전체); 디렉토리 트리 전수 조사 (`components/thesis/{builder,dashboard,list,alerts,close,indicators,common,skeleton}/`)
- **확인하지 않은 영역**: `thesis/services/thesis_builder.py` (≈79KB, LLM 빌더 로직 — 본 감사 범위 외), `thesis/services/prompt_builder.py` (≈49KB), 알림 페이지 `(list)/alerts/page.tsx` 내부, 지표 설정 페이지 `[thesisId]/indicators/page.tsx` 내부, 빌더 9개 컴포넌트 세부 동작, `frontend/lib/thesis/{types,api,mutations,queries,utils,mock,constants,conversation}.ts` 내부
- **참고**: `docs/nightly_auto_system/reports/4월/21일~5월/11일` 트리에 같은 주제 thesis_design_gap_audit.md 다수 존재. 본 보고서는 2026-05-14 시점 스냅샷. 이전 보고서와의 diff는 별도 작업 영역.
