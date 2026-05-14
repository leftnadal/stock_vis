# Thesis Control 설계 갭 감사

> 감사일: 2026-05-15
> 범위: `docs/thesis_control/` 전체 설계 문서 vs `thesis/` 백엔드 + `frontend/components/thesis/` + `frontend/app/thesis/` 구현
> 모드: 읽기 전용 (코드 수정 없음)

---

## 요약 (Phase별 구현률)

본 프로젝트의 "Phase" 표기는 **두 갈래**로 분기되어 있다. 감사 결과 둘을 분리해서 본다.

### 갈래 A: 백엔드 통합 로드맵 (`thesis_control_integrated_roadmap.md`)

특허(DNA/유효성/합성 에이전트/벡터) + 수학 엔진(v2.3.2) 결합 로드맵.

| Phase | 핵심 목표                                | 구현률      | 비고                                                                |
| ----- | ---------------------------------------- | ----------- | ------------------------------------------------------------------- |
| 1     | 관제 엔진(v2.3.2) + 이벤트 수집 + DNA 골격 | **A 95%**   | 모델/서비스/Celery/Validity/DNA 갱신까지 모두 구현                  |
| 2     | DNA 슬라이더 + ValidityScore + 역제안     | **C 0%**    | `personalization_weight` 필드만 존재. 슬라이더/역제안 UI/로직 없음 |
| 3     | 합성 에이전트 + Online LR + 블렌딩         | **C 0%**    | `SyntheticBootstrapper` 클래스/`is_synthetic` 필드 없음            |
| 4     | DNA 벡터화 + 코사인 유사도 추천            | **C 0%**    | `dna_vector` JSONField 없음, 도메인 분리 안 됨                    |

### 갈래 B: 프론트엔드 Phase 로드맵 (`Phase2_completion_summary.md`)

| Phase | 범위                                | 구현률         | 비고                                                                       |
| ----- | ----------------------------------- | -------------- | -------------------------------------------------------------------------- |
| 1     | 백엔드 핵심 + 화살표                 | **A 100%**     | (BE-PR-1~8) 완료                                                           |
| 2     | FE-PR-1~6 (목록→빌더→지표→대시→알림→마감) | **A 100%**     | 30개 컴포넌트 + 8 라우트 + Mock 모드 완료                                  |
| 3     | FE-PR-7~11 (깊이+회고+프로필)          | **B/D 40%**    | FE-PR-7~9는 **재정의되어** 대시보드 리디자인으로 흡수, FE-PR-10~11은 미착수 |

### 갈래 C: 가설 빌더 재설계 (`talking_builder/redesign_build_plan/`)

| Phase             | 범위                              | 구현률    | 비고                                       |
| ----------------- | --------------------------------- | --------- | ------------------------------------------ |
| A-MVP (PR-1~3)    | LLM one-shot + 프리셋             | **A 100%** | `work_done/phase_a_llm_builder.md`에서 확인 |
| A-Hardening (PR-4~7)| normalize/fallback/로그            | **A 100%** | 동일 보고서 확인                            |
| B (PR-8~12)       | KeywordCache + collectors + 통합   | **B 70%**  | 모델/Admin/관리커맨드/collector 모두 존재. `KEYWORD_HINTS_ENABLED=False`로 운영 OFF |
| C (advanced)      | MiniDashboard, 스트리밍 등         | **C 0%**   | 플래그 정의만, 구현 없음                    |

---

## 문서별 상태 테이블

### 1차 설계 문서

| 문서                                       | 라인  | 백엔드 코드 매칭                                                | 프론트엔드 매칭                                                 | 상태  |
| ------------------------------------------ | ----- | --------------------------------------------------------------- | --------------------------------------------------------------- | ----- |
| `plan/thesis_control_design.md`            | 1370  | thesis/models/* (Thesis, Premise, Indicator, Snapshot, Alert)   | app/thesis/* 8 라우트 + components/thesis/* 30개                | **B** |
| `plan/thesis_control_math_model_final.md`  | 1153  | services/{data_validator, indicator_scorer, premise_aggregator, thesis_state_machine, snapshot_builder, alert_engine, arrow_calculator}.py | 내부 점수 미노출 (설계대로)                                     | **A** |
| `plan/thesis_control_integrated_roadmap.md`| 660   | learning.py(HypothesisEvent/ValidityRecord/InvestorDNA) + close API의 갱신 로직 | DNA UI 0%                                                       | **B** |
| `plan/thesis_control_implementation_guide.md`| 286 | Phase 1 작업표 거의 전부 매칭                                   | —                                                               | **A** |
| `plan/thesis_control_phase3_frontend_redesign.md` | 1095 | views/monitoring_views.py(`display_unit`, raw_value, IndicatorReadingsView) | dashboard/{RealValueIndicatorCard, AISummarySection, NotableChangesSection, IndividualMiniCharts, ChartToggleButton, PeriodSelector}.tsx | **A** |
| `thesis_control_user_experience.md`        | 435   | conversation_views.py(NewsIssuesView)                            | app/thesis/new/page.tsx                                          | **B** |

### Phase 1 프론트엔드 FE-PR-1~5 명세 vs Phase 2 완료

| 문서                              | FE-PR | 명세 라인 | 실제 구현 위치                                                  | 상태  |
| --------------------------------- | ----- | --------- | --------------------------------------------------------------- | ----- |
| `thesis_control_phase1_frontend_FE_PR_1.md` | 1     | 1254      | app/thesis/layout.tsx + 5 라우트 + common 컴포넌트 + authAxios | **A** |
| `thesis_control_phase1_frontend_FE_PR_2.md` | 2     | 1171      | list/{ThesisListCard, TodayChangeCard, EntryPointGrid}.tsx     | **A** |
| `thesis_control_phase1_frontend_FE_PR_3.md` | 3     | 1901      | builder/* 9개 + app/thesis/new/page.tsx                        | **A** |
| `thesis_control_phase1_frontend_FE_PR_4.md` | 4     | 1515      | indicators/* 3개 + [thesisId]/indicators/page.tsx               | **A** |
| `thesis_control_phase1_frontend_FE_PR_5.md` | 5     | 1171      | dashboard/* (현재는 리디자인 v2 상태)                            | **D** |

### 가설 빌더 재설계 PR-1~12

| 문서                          | PR        | 실제 구현 위치                                                   | 상태  |
| ----------------------------- | --------- | ---------------------------------------------------------------- | ----- |
| `01_phase_a_mvp.md`           | PR-1~3    | services/{builder_state, prompt_builder, llm_postprocess, builder_events}.py + feature_flags.py + components/thesis/{PresetSelector, IndicatorCard}.tsx | **A** |
| `02_phase_a_hardening.md`     | PR-4~7    | normalize/validate 보강 + `_handle_fallback_choice` + `builder_stats.py` command | **A** |
| `03_phase_b_keywords.md`      | PR-8~12   | models/keyword.py + services/keyword_cache.py + keyword_collectors/{chain,eod,news}.py + management/{check_keywords, keyword_health_check}.py | **B** |
| `04_phase_c_advanced.md`      | C-1~8+    | 플래그 8종 정의만 (`MINI_DASHBOARD_PREVIEW`, `GUIDED_SUGGESTION`, `STREAMING_RESPONSE` 등 모두 False) | **C** |

---

## Phase 3 미구현 항목 상세

### Phase 3의 두 정의

Phase 2 완료 보고서(`Phase2_completion_summary.md`)는 Phase 3를 "FE-PR-7~11"로 정의했지만, 실제 진행은 `thesis_control_phase3_frontend_redesign.md`로 **재정의**되어 PR-7~10이 다음으로 흡수됐다.

| 원본 Phase 3 계획 (FE-PR-7~11)            | 재정의된 Phase 3 (PR-7~10 리디자인) | 실제 결과                                  |
| ----------------------------------------- | ----------------------------------- | ------------------------------------------ |
| FE-PR-7: 대시보드 탭 구조 + 상세 탭         | PR-7: 백엔드 확장 (display_unit, raw_value, IndicatorReadingsView) | **A** 완료 (monitoring_views.py 95~165라인) |
| FE-PR-8: 히트맵 + 지표 상세 편집           | PR-8: RealValueIndicatorCard + AISummarySection + NotableChangesSection | **B** RealValue/AISummary/Notable 모두 구현. 히트맵은 BE `heatmap` 응답은 있으나 FE 렌더링 없음. 지표 상세 편집(weight/direction CRUD UI) 없음 |
| FE-PR-9: 히스토리 탭 (recharts 라인 차트)   | PR-9: IndividualMiniCharts + PeriodSelector + ChartToggleButton | **A** IndicatorRow.tsx 안에 통합되어 1M/1Y/3Y/5Y 토글 차트 구현. 단 ChartToggleButton/IndividualMiniCharts/PeriodSelector는 빈 모듈로 존재만 함 (page.tsx에서 미사용) |
| FE-PR-10: 마감 아카이브 + 요약 + ValidityMatrix | PR-10: AI 요약 파이프라인 (Celery)  | **B** Celery task `generate_thesis_summaries` (tasks/summary.py)는 구현됨. 단 사용자용 "마감 가설 목록 / 회고 / ValidityMatrix" UI는 미구현 |
| FE-PR-11: 투자자 DNA 프로필 (AccuracyRing 등) | (없음)                              | **C** 미착수. `/profile`/`/mypage/dna` 라우트 없음, AccuracyRing/CategoryChart 컴포넌트 없음 |

### 미구현 1순위: DNA 프로필 페이지 (FE-PR-11)

- 백엔드: `InvestorDNA` 모델 + 마감 시 `_update_investor_dna()` 갱신 로직 (thesis_views.py:295) 모두 구현
- 백엔드 API: **없음** — `/api/v1/thesis/dna/` 또는 `/api/v1/users/profile/dna/` 미존재 (urls.py 확인)
- 프론트: 어떤 컴포넌트도 InvestorDNA를 import/조회하지 않음 (`grep InvestorDNA` 결과 0)
- 라우트: `frontend/components/layout/MobileNav.tsx:10` 주석에 "/profile 깨진 라우트 → /mypage" 흔적이 남아 있으나 실제 DNA 화면 라우트는 없음

→ **백엔드는 데이터 수집까지만, 사용자가 자기 DNA를 볼 화면이 없음**

### 미구현 2순위: 마감 아카이브 / 회고 (FE-PR-10 일부)

- `Thesis.status='closed'` 데이터는 쌓이지만, 별도 "닫힌 가설 목록" UI 없음
- 현재 목록(`(list)/page.tsx:38`)은 `status === 'active'`만 필터링 → 마감 가설은 사용자가 다시 볼 수 없음
- 설계 문서 3.9 "가설 마감 — 복기" 화면(가장 유용한 지표/예상과 달랐던 부분 안내) 미구현
- ValidityRecord에 `score` 데이터는 쌓이지만 사용자에게 노출되는 ValidityMatrix UI 없음
- 마감 페이지(`close/page.tsx`)는 outcome 선택과 메모만 지원, 복기 요약 화면 없음

### 미구현 3순위: 히트맵 뷰 (FE-PR-8 일부)

- 설계 문서 3.4의 3개 뷰(카드/히트맵/그래프) 중 카드뷰만 구현
- DashboardView 응답에 `heatmap` 키(rows/cols/cells)는 들어있으나 FE에서 사용 안 함
- 설계 문서 3.4의 그래프뷰(시계열 라인)는 IndicatorRow의 토글 차트로 부분 대체

### 미구현 4순위: 통합 로드맵 Phase 2 (DNA 슬라이더 + ValidityScore)

| 항목                                  | 모델/필드 존재 | 서비스 로직 | UI |
| ------------------------------------- | -------------- | ----------- | --- |
| `ValidityScore` 모델                   | 없음           | 없음        | —   |
| ValidityRecord → ValidityScore 집계 태스크 | 없음           | 없음        | —   |
| `personalization_weight` 슬라이더      | 필드만 존재    | 없음        | 없음 |
| 역제안(Contrarian Nudge)                | —              | 없음        | 없음 |
| 상관계수 자동 할인 / Adaptive Decay / Sustained Extreme | —          | 없음        | —   |
| 뉴스 센티먼트 → Stage 1 입력           | —              | 없음 (별개 sentiment indicator_type만 있음) | — |

### 부분 구현: 빌더 재설계 Phase B

- `KeywordCache` 모델 + Admin 등록 + 인덱스: **완료** (models/keyword.py)
- `keyword_cache.py` 서비스 (SOURCE_TTL, save/collect): **완료**
- collector 3종 (chain.py/eod.py/news.py): **완료** (services/keyword_collectors/)
- `check_keywords` + `keyword_health_check` management command: **완료**
- 빌더 통합 (`build_keyword_hint_block` 등): **완료** (services/keyword_hint.py)
- **운영 OFF**: `feature_flags.py`의 `KEYWORD_HINTS_ENABLED`/`CHAIN_KEYWORDS_ENABLED`/`EOD_KEYWORDS_ENABLED`/`NEWS_KEYWORDS_ENABLED` 4종 모두 `False` (런타임 미주입)
- 설계 문서는 "News → EOD → Chain 순으로 켜면서 효과 확인"을 명시했으나 켜진 흔적 없음

### 진입 경로 5종 vs 실제 진입점 카드

설계 문서 2.3은 5가지 진입 경로를 명세:

| 경로            | 백엔드 지원                                                        | 프론트 UI                                       | 상태  |
| --------------- | ------------------------------------------------------------------ | ----------------------------------------------- | ----- |
| 📰 오늘 이슈    | `NewsIssuesView` (urls.py:25) + `ENTRY_SOURCES` 포함                  | EntryPointGrid의 '뉴스 기반' 카드 + NewsSelector | **A** |
| 💬 내 생각      | LLM proposal (Phase A-MVP 완료)                                     | 자유 입력 카드                                   | **A** |
| 🔥 인기 가설    | `PopularThesisCache` 모델 존재. **API/뷰셋 없음**                    | new/page.tsx:153, 806 자리만 마련. POPULAR_TEMPLATES 4개로 stub | **B** |
| 📋 템플릿       | `entry_source='template'` choices만 존재. 별도 endpoint 없음          | 미구현                                          | **C** |
| 🔗 Chain Sight  | `entry_source='chainsight'` choices만 존재                          | 미구현 (Chain Sight ↔ Thesis 진입 연결 없음)     | **C** |

### 알림 — 부분 구현

설계 문서 3.7 "변화 감지 알림" + 통합 로드맵 5.3 8개 Celery 태스크:

| 태스크                          | 설계                | 구현                                                      | 상태  |
| ------------------------------- | ------------------- | --------------------------------------------------------- | ----- |
| `update_indicator_readings`     | 18:00 ET            | tasks/eod_pipeline.py                                     | **A** |
| `calculate_arrow_degrees`/`calculate_scores` | 18:15 ET | tasks/eod_pipeline.py                                     | **A** |
| `create_daily_snapshots` + `check_thesis_alerts` | 18:30/18:45 | tasks/eod_pipeline.py `create_snapshots_and_alerts`       | **A** |
| `scan_thesis_news`              | 2시간마다           | 없음                                                       | **C** |
| `update_popular_thesis_cache`   | 매일 08:00          | 없음 (PopularThesisCache는 모델만 존재)                   | **C** |
| `prepare_daily_issues`          | 매일 07:00          | 없음 (NewsIssuesView가 즉석 fetch로 대체)                | **C** |
| `generate_thesis_summaries`     | 매일 07:30          | tasks/summary.py 구현됨                                   | **A** |

### Neo4j 가설 관계 그래프

설계 문서 4.4 `(Thesis)-[HAS_PREMISE]->(Premise)` 등 그래프 매핑:

- thesis 앱 내에서 Neo4j 사용 흔적 없음 (`grep -r neo4j thesis/` 결과 0)
- Chain Sight의 Neo4j와 Thesis Control의 가설 그래프는 분리되어 있음
- **D 폐기 가능성 높음**: 통합 로드맵에는 그래프 활용 항목이 없으며, 빌더 재설계는 KeywordCache(Postgres)를 채택

---

## 분류 요약

### (A) 완전 구현

- 수학 엔진 Stage 0~3 (data_validator, indicator_scorer, premise_aggregator, thesis_state_machine, snapshot_builder, alert_engine, arrow_calculator) — `thesis/services/`
- v2.3.2 추가 필드 (epsilon/window/decay/min_max_valid/max_change_pct/allow_extreme_jump/is_paused/override_score, asof, validation_status, asof_date, data_coverage, premise/indicator_universe_ids)
- EOD Celery 파이프라인 3 태스크 + AI 요약 태스크
- HypothesisEvent / ValidityRecord / InvestorDNA 모델 + 마감 시 갱신 로직
- 빌더 LLM 모드 Phase A 전체 (PR-1~7) — 한 줄 입력 → 가설 전체 제안 → 3턴 등록
- FE-PR-1~6 (라우팅 + 목록 + 빌더 + 지표 설정 + 대시보드 + 알림/마감) 핵심 루프
- Phase 3 리디자인 PR-7~10 (display_unit, raw_value, AISummary, NotableChanges, IndicatorRow의 토글 차트, AI 요약 파이프라인)
- KeywordCache 인프라 + 3 collector + 빌더 통합 (코드 기준)

### (B) 부분 구현

- 빌더 진입점: 뉴스/자유입력만 정상, 인기 가설은 stub, 템플릿/Chain Sight 미구현
- Phase B 키워드 시스템: **코드는 있으나 feature flag로 비활성** (운영 미적용)
- 알림 시스템: EOD 파이프라인 알림은 완료, 뉴스 스캔 / 인기 가설 캐시 / daily issues 준비 태스크는 없음
- 대시보드 뷰: 카드뷰만, 히트맵 응답은 있으나 FE 미사용
- PR-9의 빈 모듈: ChartToggleButton/IndividualMiniCharts/PeriodSelector는 파일 존재하나 page.tsx에서 import 안 됨 → IndicatorRow에 통합되며 사실상 deprecated

### (C) 미구현

- FE-PR-10 일부: 마감 가설 아카이브 / 복기 화면 / ValidityMatrix UI
- FE-PR-11 전체: DNA 프로필 페이지 (AccuracyRing, CategoryChart 등)
- DNA API 엔드포인트 (`/dna/`, `/profile/dna/`)
- 통합 로드맵 Phase 2: ValidityScore 모델 + DNA 슬라이더 + 역제안 + Adaptive Decay + 상관 할인 + Sustained Extreme + 뉴스 센티먼트→Stage 1
- 통합 로드맵 Phase 3: SyntheticBootstrapper + Online LR + 합성/실데이터 블렌딩
- 통합 로드맵 Phase 4: DNA/유효성 벡터화 + 코사인 유사도 + 사용자 유사도
- 빌더 Phase C: MiniDashboardPreview, Guided Suggestion (코드는 있음, 플래그 OFF), Streaming, Multi-turn Edit
- 모바일 제스처 일부: 좌우/상하 스와이프, 쉐이크, 롱프레스 상세 차트
- `scan_thesis_news`, `update_popular_thesis_cache`, `prepare_daily_issues` Celery 태스크

### (D) 폐기 / 대체

- 설계 문서 3.2 Moon Phase 메타포: Phase 3 리디자인에서 명시적 제거 (OverallMoon/CombinedNormalizedChart 삭제)
- 설계 문서 3.4 그래프뷰(별도 탭): IndicatorRow 토글 차트로 대체 (탭 구조 폐기)
- 원본 FE-PR-7~11 명세(`Phase2_completion_summary.md` 표): Phase 3 리디자인으로 재정의 → 일부 항목 누락
- 설계 문서 4.4 Neo4j 가설 관계 그래프: 흔적 없음, 통합 로드맵에서도 빠짐 → 사실상 폐기
- Zustand `dashboardStore` (원안에 있었음): 명시적 useState로 대체
- DashboardIndicatorCard / OverallMoon / RecentChange / MoonPhase 일부: Phase 3 리디자인에서 삭제 (목록 페이지의 EmptyTheses에서 MoonPhase는 여전히 사용 중 → 부분 잔존)

---

## 우선순위 권고 (감사 메모)

> 본 감사는 코드 수정을 하지 않으며, 다음 권고는 후속 작업자가 참고할 데이터일 뿐이다.

1. **DNA UI 부재가 가장 큰 갭** — 마감마다 갱신되는 데이터가 사용자에게 노출되지 않음. FE-PR-11 또는 최소 dashboard 한 구석 표시 권장.
2. **마감 가설 아카이브** — 목록에서 `closed` 필터링 + 복기 카드. 백엔드 데이터는 이미 충분.
3. **PR-9 빈 모듈 정리** — ChartToggleButton/IndividualMiniCharts/PeriodSelector는 사용처가 없으므로 삭제하든가 사용처를 명시하든가.
4. **Phase B 키워드 활성화 결정** — 코드를 만들어 둔 채 4개월째 OFF 상태. 켜거나 코드를 보존 모드로 격리할 필요.
5. **인기 가설 / 템플릿 / Chain Sight 진입점** — choices만 있고 동작 없음. 명세를 줄이거나 stub을 구현으로 채울지 결정 필요.
6. **Neo4j 가설 그래프** — 폐기로 문서화하는 게 정직.

---

## 출처

- 백엔드: `thesis/{models,services,views,tasks,urls.py,feature_flags.py,migrations}/`
- 프론트엔드: `frontend/app/thesis/`, `frontend/components/thesis/`, `frontend/lib/thesis/`
- 설계: `docs/thesis_control/plan/*.md`, `docs/thesis_control/plan/talking_builder/**`, `docs/thesis_control/thesis_control_phase1_*.md`, `docs/thesis_control/frontend/task_done/*.md`, `docs/thesis_control/work_done/*.md`
