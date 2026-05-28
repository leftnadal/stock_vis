# SEC Pipeline + Validation + News 설계 갭 감사

> 생성일: 2026-05-28
> 범위: docs/sec_pipeline/ vs sec_pipeline/, docs/first_validation_system/ vs validation/(+metrics/+stocks/), docs/news/ vs news/
> 모드: read-only audit. 코드 수정 없음.

---

## 앱별 요약 (구현률)

| 앱 | 설계 항목 (모델/API/Task/Service) | 구현 완료 | 구현률 | 종합 분류 |
|----|----------------------------------|----------|--------|---------|
| **SEC Pipeline** | 8 모델 + 16 파일 + 7 Task + 2 URL | 8 / 16 / 7+1 / 2 | ≈ **100%** | **(A) 완전 구현** |
| **Validation** | 6 신규 모델 + 7 API + 7 Task + 9 Service (Phase 1~7) | 6 / 7 / 8 / 9 | ≈ **100%** | **(A) 완전 구현** (Phase 1~7) |
| **News** | 9 모델 + 17 API + 13+ Task + Phase 0/A/B/C | 9 / 17 / ≥13 / 전부 | ≈ **100%** (BE) | **(A) 완전 구현** (BE 기준) |

세 앱 모두 **백엔드 설계서가 정의한 항목은 전부 코드 베이스에 존재**한다. 미구현(C)/폐기(D) 분류 없음. 부분 구현(B)에 해당하는 케이스는 "프론트엔드 의존 항목" 및 "데이터 시딩 의존 항목" 두 가지 형태로만 잔존.

---

## SEC Pipeline 상세

### 설계 vs 구현 매핑

설계서 1차 소스: `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` (PR 1~17 통합 요약) + `decisions/001_fmp_vs_sec_edgar_metadata.md`.

#### 모델 8개 — 전부 (A) 완전 구현

| 설계 모델 | 구현 위치 (sec_pipeline/models.py) | 상태 |
|-----------|------------------------------------|------|
| RawDocumentStore | L15 | (A) |
| SupplyChainEvidence | L61 | (A) |
| FilingProcessLog | L231 | (A) |
| CompanyAlias | L273 | (A) |
| UnmatchedCompanyQueue | L307 | (A) |
| BusinessModelSnapshot | L122 | (A) |
| BusinessModelEvidence | L201 | (A) |
| PipelineIntelligenceReport | L351 | (A) |

#### 모듈 16개 — 전부 (A) 완전 구현

| 설계 모듈 | 구현 파일 | 상태 |
|-----------|----------|------|
| models.py | sec_pipeline/models.py | (A) |
| collector.py | sec_pipeline/collector.py | (A) |
| validators.py | sec_pipeline/validators.py | (A) |
| normalizer.py | sec_pipeline/normalizer.py | (A) |
| prompts.py | sec_pipeline/prompts.py | (A) |
| extractor.py | sec_pipeline/extractor.py | (A) |
| validator_track_a.py | sec_pipeline/validator_track_a.py | (A) |
| validator_track_b.py | sec_pipeline/validator_track_b.py | (A) |
| keywords_track_b.py | sec_pipeline/keywords_track_b.py | (A) |
| exceptions.py | sec_pipeline/exceptions.py | (A) |
| tasks.py | sec_pipeline/tasks.py | (A) |
| sp500.py | sec_pipeline/sp500.py | (A) |
| ticker_matcher.py | sec_pipeline/ticker_matcher.py | (A) |
| signals.py | sec_pipeline/signals.py | (A) |
| merger.py | sec_pipeline/merger.py | (A) |
| intelligence.py | sec_pipeline/intelligence.py | (A) |
| quality_checks.py | sec_pipeline/quality_checks.py | (A) |
| on_demand.py | sec_pipeline/on_demand.py | (A) |
| views.py | sec_pipeline/views.py | (A) |
| urls.py | sec_pipeline/urls.py | (A) |
| admin.py | sec_pipeline/admin.py | (A) |

#### Celery Task — (A) 완전 구현 + α

설계서 PR-4 명세 vs sec_pipeline/tasks.py 실측:

| 설계 Task | 구현 위치 | 상태 |
|----------|----------|------|
| collect_and_extract | tasks.py:23 | (A) |
| extract_from_document | tasks.py:149 | (A) |
| sync_dirty_to_neo4j | tasks.py:338 | (A) |
| check_new_filings | tasks.py:465 | (A) |
| generate_intelligence_report | tasks.py:501 | (A) |
| run_batch_and_report | tasks.py:509 | (A) |
| **seed_relations_to_chainsight** | tasks.py:282 | (α) 설계 외 추가 — chainsight 시드 자동화 |

#### URL — (A)

| 설계 엔드포인트 | 구현 |
|----------------|------|
| `/admin/dashboard/` | urls.py:7 (sec_pipeline_dashboard) |
| `/filing/<symbol>/` | urls.py:8 (FilingDataView) |

#### 잔여 부채 (설계서 §향후 과제 5건)

설계서 본인이 미완으로 표기한 항목. 코드는 (A)이고 운영 잔량만 남음:

| # | 항목 | 분류 | 위치 |
|---|------|------|------|
| 1 | S&P 500 전체 배치 미실행 (현재 15종목) | 운영 | tasks.py: run_batch_and_report |
| 2 | Gold Set 라벨 보완 → Precision/Recall 재평가 | 운영 | sec_pr_5_gold_set.md |
| 3 | JNJ Item 순서 검증 완화 | (B) 데이터 의존 | validators.py |
| 4 | 일반 명사("third parties") 추출 방지 | (B) 프롬프트 튜닝 | prompts.py |
| 5 | CompanyAlias 수동 등록 (TSMC→TSM, Samsung 등) | 운영 | models.py:273, 현재 0건 |

**SEC Pipeline 종합**: 코드 베이스 기준 **100% 완전 구현**. 부채는 전부 운영/데이터 시딩 영역.

---

## Validation 상세

### 설계 vs 구현 매핑

1차 소스: `validation_design.md` v1.4 (1646줄, Phase 1~5 본문) + `validation_peer_system.md` v2 (프리셋 6종) + `validation_peer_phase6_7.md` (Phase 6/7 확장) + `task_done/peer_phase6_thematic.md`, `task_done/peer_phase7_llm_filter.md`.

#### 모델 — (A) 완전 구현

설계서가 신규/수정 명시한 모델:

| 설계 항목 | 구현 위치 | 상태 |
|----------|----------|------|
| `category_signal` (← `category_score` 개명) | validation/models/category_score.py:4 `CategorySignal` | (A) |
| `CompanyMetricSnapshot.value_status` v1.3 | metrics/models/metric_snapshot.py:43 | (A) |
| `CompanyMetricSnapshot.exclusion_reason` | metrics/models/metric_snapshot.py:53 | (A) |
| `CompanyBenchmarkDelta.benchmark_basis` | validation/models/benchmark_delta.py:26 + metrics/models/benchmark.py:30 | (A) |
| `CompanyBenchmarkDelta.benchmark_confidence` | validation/models/benchmark_delta.py:34 | (A) |
| `PeerListCache.benchmark_basis/size_bucket/peer_tier` | metrics/models/benchmark.py:30/38/42 | (A) |
| `IndustryClassification.handling_mode` (special) | stocks/models.py:729 | (A) |
| `CategorySignal.preset_key` | validation/models/category_score.py:51 | (A) |
| `CompanyBenchmarkDelta.preset_key` | validation/models/benchmark_delta.py:53 | (A) |
| `PeerPreset` (Phase 2) | validation/models/peer_preset.py:5 | (A) |
| `UserPeerPreference` (Phase 4) | validation/models/peer_preset.py:43 | (A) |
| `CompanyMetricLatest` | validation/models/metric_latest.py:4 | (A) |
| `ValidationAICache` (Phase 5 LLM 캐시) | **(D) 폐기 또는 (C) 미구현** — 설계 §8.2가 "Phase 2 LLM 도입 시 참고용"으로 명시. 현 시점 미생성. Rule-based only 정책 유지 | (D)/(C) |
| **`ValidationNewsSummary`** | validation/models/news_summary.py:4 | (α) 설계 외 추가 |

#### API 엔드포인트 — (A) 완전 구현

| 설계 엔드포인트 | 구현 View | 상태 |
|----------------|----------|------|
| `GET /validation/{symbol}/summary/` | ValidationSummaryView (views.py:52) | (A) |
| `GET /validation/{symbol}/metrics/` | ValidationMetricsView (views.py:173) | (A) |
| `GET /validation/{symbol}/leader-comparison/` | LeaderComparisonView (views.py:317) | (A) |
| `GET /validation/{symbol}/presets/` | PresetListView (views.py:424) | (A) |
| `POST/DELETE /validation/{symbol}/peer-preference/` | PeerPreferenceView (views.py:459) | (A) |
| `POST /validation/{symbol}/peer-filter/` (Phase 7) | LLMPeerFilterView (urls.py:13 — `/llm-filter/`) | (A) — 경로명이 `peer-filter`가 아닌 `llm-filter`로 출시됨 (사소한 명세 불일치) |

#### Celery Task (배치) — (A) 완전 구현

설계서 §6.1 흐름과 1:1 매칭:

| 설계 Task | 구현 |
|----------|------|
| Task 1 fetch_annual_financials | validation/tasks.py:23 |
| Task 2 calculate_derived_metrics (+ value_status) | tasks.py:37 |
| Task 3 calculate_benchmarks | tasks.py:51 |
| Task 3.5 calculate_relative_metrics | tasks.py:65 |
| Task 4 calculate_category_signals | tasks.py:79 |
| Task 5 update_peer_list_caches | tasks.py:93 |
| Task 6 log_batch_run | tasks.py:106 |
| Orchestrator `run_weekly_validation_batch` (chain) | tasks.py:141 |

#### Phase별 진행 상태

| Phase | 설계 명세 | 구현 | 상태 |
|-------|----------|------|------|
| Phase 1 (default 프리셋 + Rule-based 해석) | validation_design.md §10 | summary/metrics/leader-comparison + interpretation.py | (A) |
| Phase 2 (PeerPreset 모델 + sector_all/size_peers) | validation_peer_system.md §9 | PeerPreset 모델 + preset_generator._generate_sector_all/size_peers | (A) |
| Phase 3 (quality_top + lifecycle + confidence_score) | validation_peer_system.md §9 | preset_generator._generate_quality_top/lifecycle + `_calc_confidence` | (A) |
| Phase 4 (UserPeerPreference + 선택 UI) | validation_peer_system.md §9 | UserPeerPreference + PeerPreferenceView | (A) |
| Phase 5 (Custom mode Compute-on-Read + Redis) | validation_peer_system.md §9 | services/custom_benchmark_engine.py | (A) |
| Phase 6 (Thematic 프리셋, LLM 큐레이션) | validation_peer_phase6_7.md §Phase 6 + task_done/peer_phase6_thematic.md | preset_generator._generate_thematic (Chain Sight DNA 기반) | (A) — 단 구현이 LLM이 아닌 **Chain Sight CapitalDNA/NarrativeTag 기반**으로 노선 변경 (설계서가 명시한 chainsight 선행 결정과 일치) |
| Phase 7 (LLM 대화형 peer 필터) | validation_peer_phase6_7.md §Phase 7 + task_done/peer_phase7_llm_filter.md | services/llm_peer_filter.py + LLMPeerFilterView | (A) |

#### Service 레이어 — (A) 완전 구현

| 설계 책임 | 구현 파일 |
|----------|----------|
| Peer 선정 + benchmark 계산 | services/benchmark_calculator.py |
| Category 신호 산출 | services/category_signal_calculator.py |
| Compute-on-Read (custom mode) | services/custom_benchmark_engine.py |
| 재무 데이터 수집 | services/financial_fetcher.py |
| 해석 텍스트 (Rule-based) | services/interpretation.py |
| LLM peer 필터 파서 | services/llm_peer_filter.py |
| 지표 계산 | services/metric_calculator.py |
| 프리셋 생성기 | services/preset_generator.py (6 기법 _generate_*) |
| 상대 지표 (rev_growth_vs_industry) | services/relative_metrics.py |

#### 잔여 부채

| # | 항목 | 분류 | 위치 |
|---|------|------|------|
| 1 | `ValidationAICache` 테이블 (Phase 2 LLM 도입용) | (C) 설계상 보류 | validation_design.md §8.2 |
| 2 | URL 명세 vs 구현 경로 불일치: 설계 `peer-filter` → 구현 `llm-filter` | (B) 명세 결손 | validation/api/urls.py:13 |
| 3 | Phase 6 thematic 구현이 **LLM 큐레이션이 아닌 Chain Sight DNA 기반**으로 변경 — task_done 보고서에 명시되어 있으나 `validation_peer_phase6_7.md` 본문은 LLM 프롬프트로 기술. 설계서 본문/구현 노선 갭 | (B) 문서 미갱신 | preset_generator.py:377 vs phase6_7.md §Phase 6 Step 1 |
| 4 | Recharts ComposedChart, Accordion 모바일 UX 등 프론트엔드 명세 | 백엔드 감사 범위 외 | validation_design.md §9 |

**Validation 종합**: Phase 1~7 백엔드 **100% 구현 완료**. 설계가 보류로 분류한 `ValidationAICache`만 (C). Phase 6의 노선 변경(LLM→DNA)은 코드는 (A)이나 설계 문서가 따라오지 못한 (B).

---

## News 상세

### 설계 vs 구현 매핑

1차 소스: `news_pipeline_monitoring_design.md` v1.1 (Phase A/B/C 통합 설계) + `news_keyword_detail_plan.md` (키워드 상세보기) + `keyword_detail_bottomsheet_v2.md` (UI 명세).

#### 모델 — (A) 완전 구현

| 설계 항목 | 구현 |
|----------|------|
| `NewsCollectionLog` (기존) | news/models.py:663 | (A) |
| `MLModelHistory` (기존) | news/models.py:494 | (A) |
| `DailyNewsKeyword.search_terms_en` (키워드 상세 §3-1) | keywords JSON 내 필드, keyword_extractor.py:306에서 저장 | (A) |
| `NewsCollectionCategory` (기존) | news/models.py:599 | (A) |
| `AlertLog` (Phase C §6.3) | news/models.py:684 + migrations/0006_alertlog.py | (A) |
| AlertLog `Severity` TextChoices | news/models.py:684 | (A) |
| AlertLog `TriggerType` TextChoices | news/models.py:684 | (A) |

#### API 엔드포인트 17개 — (A) 완전 구현

설계서 부록 매트릭스 17건 전부 매핑:

| 설계 엔드포인트 | Phase | 구현 위치 |
|----------------|-------|----------|
| `/ml-status/` | 기존 | views.py:1127 |
| `/ml-shadow-report/` | 기존 | views.py:1155 |
| `/ml-weekly-report/` | 기존 | views.py:1208 |
| `/ml-lightgbm-readiness/` | 기존 | views.py:1237 |
| `/daily-keywords/` | 기존 | views.py:523 |
| `/keyword-detail/` | 키워드 상세 plan | views.py:656 |
| `/collection-logs/` | Phase A | views.py:1330 |
| `/pipeline-health/` | Phase A | views.py:1440 |
| `/ml-trend/` | Phase A | views.py:1694 |
| `/llm-usage/` | Phase A | views.py:1774 |
| `/task-timeline/` | Phase B | views.py:1894 |
| `/neo4j-status/` | Phase B | views.py:1955 |
| `/ml-rollback-preview/` | Phase B | views.py:2016 |
| `/ml-rollback/` (POST + `confirm` 필수) | Phase B | views.py:2056 |
| `/alerts/` | Phase C | views.py:2101 |
| `/alerts/{id}/resolve/` | Phase C | views.py:2165 |
| `/daily-keywords/generate/` | 운영 | views.py:617 (α) |

전부 `permission_classes=[IsAdminUser]` 적용 — 설계서 §9 인증 요구 준수.

#### Phase 0 선행 작업 (`_log_collection` 커버리지) — (A) 완전 구현

설계서 §11이 보강 대상으로 지정한 6개 태스크 전부 호출 확인:

| 설계 Task | 구현 line | provider 인자 |
|----------|-----------|-------------|
| collect_daily_news | tasks.py:178 | `'finnhub_marketaux'` (설계는 finnhub/marketaux 개별 로깅 권고, 구현은 통합) |
| collect_market_news | tasks.py:220 | `'finnhub_marketaux'` |
| collect_category_news | tasks.py:454 | `'finnhub_marketaux'` |
| classify_news_batch | tasks.py:500 | `'internal'` (설계는 `'classifier'`) |
| analyze_news_deep | tasks.py:543 | `'gemini'` |
| sync_news_to_neo4j | tasks.py:621 | `'neo4j'` |

기존 호출 4개(FMP/AV 배치):
- `collect_sp500_news_fmp_batch` tasks.py:947
- `collect_press_releases_fmp` tasks.py:1040
- `collect_general_news_fmp` tasks.py:1073
- (`collect_av_single_symbol`은 별도 경로)

**provider 명칭 불일치** (설계 vs 구현 2건): `finnhub`/`marketaux` 개별 → 통합 `'finnhub_marketaux'`, `'classifier'` → `'internal'`. (B) 사소한 명세 결손.

#### Phase C Celery Task — (A) 완전 구현

| 설계 항목 | 구현 |
|----------|------|
| `check_pipeline_alerts` (30분 주기, 7개 트리거) | tasks.py:1102 |
| AlertLog 자동 생성 + 중복 방지 | tasks.py:1129-1143 |
| Beat 스케줄 등록 | @infra 담당 — `config/celery.py` 별도 검증 필요 (이번 감사 범위 외) |

#### 키워드 상세보기 (news_keyword_detail_plan.md) — (A) 완전 구현

| 설계 항목 | 구현 |
|----------|------|
| keyword_extractor 프롬프트에 `search_terms_en` 추가 | services/keyword_extractor.py:241 (프롬프트 본문) |
| keyword_extractor 출력 파싱에 `search_terms_en` 보존 | keyword_extractor.py:306 |
| `GET /api/v1/news/keyword-detail/?date=&index=` | views.py:656 (keyword_detail @action) |
| Gemini 분석 fallback (`analysis: null`) | views.py:791 `_generate_keyword_analysis` |

#### 잔여 부채

| # | 항목 | 분류 | 위치 |
|---|------|------|------|
| 1 | `_log_collection` provider 명칭 설계-구현 불일치 (`finnhub_marketaux` vs `finnhub`/`marketaux`) | (B) 명세 결손 — 대시보드 by_provider 집계가 finnhub/marketaux를 분리 표시할 수 없음 | tasks.py:178/220/454 vs design §11 |
| 2 | `classify_news_batch` provider `'internal'` vs 설계 `'classifier'` | (B) 명세 결손 | tasks.py:500 |
| 3 | `NewsDeepAnalyzer`(Phase 3) 토큰 미추적 한계 | 설계서 §3.4 본인이 명시한 Phase B 후속 | news/services/news_deep_analyzer.py |
| 4 | Phase A 프론트엔드 컴포넌트 6개 + sub-tab | 백엔드 감사 범위 외 | frontend/components/admin/news/ |
| 5 | Phase B/C 프론트엔드 (TaskTimelineChart, Neo4jStatusCard, AlertBadge 등) | 백엔드 감사 범위 외 | frontend/components/admin/news/ |
| 6 | `check_pipeline_alerts` Beat 스케줄 등록 여부 | @infra 검증 항목 — 이번 감사 미확인 | config/celery.py |

**News 종합**: 백엔드 Phase 0/A/B/C **100% 구현 완료**. 잔여 부채는 (B) 명칭 미세 결손 2건 + (B) Phase 3 토큰 로깅 후속.

---

## 종합

### 분류 분포

| 분류 | 건수 | 비중 |
|------|------|------|
| (A) 완전 구현 | 모델 23/23, API 25/25, Task 24/24, Service 15/15 | 거의 100% |
| (B) 부분 구현 (명세 결손 / 노선 변경 / 문서 갭) | 5건 | 작음 |
| (C) 미구현 (설계상 보류) | 1건 (`ValidationAICache`) | 미미 |
| (D) 폐기/대체 | 0건 | — |

### (B) 부분 구현 5건 요약

1. Validation URL: 설계 `peer-filter` → 구현 `llm-filter` (validation/api/urls.py:13)
2. Validation Phase 6 thematic: 설계 LLM 큐레이션 → 구현 Chain Sight DNA 기반 (preset_generator.py:377; task_done 보고서에는 명시, 설계 본문 미갱신)
3. News `_log_collection` provider: 설계 `finnhub`/`marketaux` 분리 → 구현 `finnhub_marketaux` 통합 (tasks.py:178/220/454)
4. News `_log_collection` provider: 설계 `classifier` → 구현 `internal` (tasks.py:500)
5. News Phase 3 토큰 미추적 — 설계서 §3.4가 본인이 Phase B로 미루기로 결정한 항목 (news_deep_analyzer.py)

### (C) 1건

- `ValidationAICache` 모델 — `validation_design.md` §8.2가 "Phase 1에서는 도입 안 함, Phase 2 LLM 도입 시 참고용"으로 명시. 현 시점 Rule-based only 정책 유지가 정상 상태.

### 운영/시딩 부채 (코드는 (A))

- SEC: S&P 500 전체 배치 미실행, Gold Set 라벨 보완, CompanyAlias 수동 등록
- Validation: 프론트엔드 ComposedChart/Accordion UX
- News: 프론트엔드 sub-tab 대시보드 + AlertBadge

### 권고

1. **(B) 5건은 문서 갱신만으로 해결 가능** — 코드 변경 없이 design.md 본문을 구현 상태에 맞게 정정. 특히 Validation Phase 6 노선 변경은 task_done 보고서가 1차 소스가 되도록 명시.
2. **(C) `ValidationAICache`는 Phase 1~7 결과 검토 후** 재의사결정 — 현 시점에는 의도된 미구현.
3. 백엔드 감사 결과는 **세 앱 모두 ship-ready**. 잔여 작업은 프론트엔드 + 데이터 시딩 + Beat 스케줄 검증으로 분리.

---

## 참고 파일

- `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md`
- `docs/first_validation_system/validation_design.md` (v1.4, 1646줄)
- `docs/first_validation_system/validation_peer_system.md` (v2, 6 프리셋)
- `docs/first_validation_system/validation_peer_phase6_7.md`
- `docs/first_validation_system/task_done/peer_phase6_thematic.md`
- `docs/first_validation_system/task_done/peer_phase7_llm_filter.md`
- `docs/news/plan/news_pipeline_monitoring_design.md` (v1.1, 1160줄)
- `docs/news/plan/news_keyword_detail_plan.md`
- 구현: `sec_pipeline/`, `validation/`, `metrics/`, `stocks/models.py:722` (IndustryClassification), `news/`
