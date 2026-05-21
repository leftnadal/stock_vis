# SEC Pipeline + Validation + News 설계 갭 감사

> **작성일**: 2026-05-22 (야간 자동화 5월 21일 리포트 슬롯)
> **범위**: 읽기 전용 감사. 코드 수정 없음.
> **대상 디렉토리**:
> - `docs/sec_pipeline/` vs `sec_pipeline/`
> - `docs/first_validation_system/` vs `validation/` (+ `metrics/`)
> - `docs/news/` vs `news/`

분류 기준:
- **(A) 완전 구현** — 설계서의 모든 명시 항목이 코드/문서에 대응됨
- **(B) 부분 구현** — 핵심은 구현되었으나 일부 명시 항목 누락/미검증
- **(C) 미구현**
- **(D) 폐기/대체**

---

## 앱별 요약 (구현률)

| 앱 | 설계 분량 | 구현 분류 | 구현률(체감) | task_done 커버 |
|----|-----------|-----------|-------------|----------------|
| **SEC Pipeline** | 1개 결정문서 + 17개 PR 완료서 | **(A) 완전 구현** | 100% (배치 결과 포함) | 17/17 PR 정식 기록 |
| **Validation (1차 검증)** | 4개 설계서 (~2,845줄) + 13개 PR 프롬프트 | **(B) 부분 구현 — 코드 OK, 기록 누락** | 코드 ~100%, PR task_done 2/13 | Peer Phase 6/7만 정식 기록 |
| **News (Pipeline Monitoring + Keyword Detail)** | 3개 plan 문서 (~1,456줄) | **(B) 부분 구현 — 코드 OK, 기록 누락** | API/FE ~100% | task_done 폴더 자체 없음 |

**핵심 패턴**: SEC Pipeline만 "설계 → PR → task_done" 사이클이 완비. Validation/News는 코드는 모두 들어왔으나 PR별 완료 보고서가 누락되어 **추적 가능성 갭**이 큰 상태.

---

## SEC Pipeline 상세

### 분류: (A) 완전 구현

설계서(`docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md`) 기준 17 PR이 모두 완료 기록되어 있고, 실제 앱(`sec_pipeline/`) 파일과 1:1 대응.

### 모델 (설계 8개 → 구현 8개, 100%)

| 설계 모델 | 구현 위치 | 비고 |
|-----------|-----------|------|
| RawDocumentStore | `sec_pipeline/models.py:15` | 15건 적재 |
| SupplyChainEvidence | `sec_pipeline/models.py:61` | 110건 |
| BusinessModelSnapshot | `sec_pipeline/models.py:122` | 5건 |
| BusinessModelEvidence | `sec_pipeline/models.py:201` | 25건 |
| FilingProcessLog | `sec_pipeline/models.py:231` | 173건 |
| CompanyAlias | `sec_pipeline/models.py:273` | 0건 (수동 등록 대기) |
| UnmatchedCompanyQueue | `sec_pipeline/models.py:307` | 60건 |
| PipelineIntelligenceReport | `sec_pipeline/models.py:351` | 2건 |

### 파이프라인 구성요소 (설계 16 파일 → 구현 16 파일, 100%)

`collector.py`, `extractor.py`, `validator_track_a.py`, `validator_track_b.py`, `normalizer.py`, `prompts.py`, `keywords_track_b.py`, `merger.py`, `ticker_matcher.py`, `signals.py`, `quality_checks.py`, `intelligence.py`, `on_demand.py`, `exceptions.py`, `tasks.py`, `sp500.py` 전부 존재.

### Celery Task

- `collect_and_extract`, `extract_from_document`, `seed_relations_to_chainsight`, `sync_dirty_to_neo4j`, `check_new_filings`, `generate_intelligence_report`, `run_batch_and_report` — 모두 `sec_pipeline/tasks.py`에 구현.

### API/URL

- `/api/v1/sec-pipeline/admin/dashboard/` (Admin 대시보드, HTML 템플릿)
- `/api/v1/sec-pipeline/filing/<symbol>/` (FilingDataView)
- `config/urls.py:46`에 include 완료.

### task_done cross-reference

| PR | 문서 | 상태 |
|----|------|------|
| PR-1 모델 | `sec_pr_1_models.md` | ✓ |
| PR-2 collector | `sec_pr_2_collector.md` | ✓ |
| PR-3 Track A extractor | `sec_pr_3_track_a_extractor.md` | ✓ |
| PR-4 Celery tasks | `sec_pr_4_celery_tasks.md` | ✓ |
| PR-5 Gold set | `sec_pr_5_gold_set.md` | ✓ |
| PR-6 Phase1 batch | `sec_pr_6_phase1_batch.md` | ✓ |
| PR-7 ticker matcher | `sec_pr_7_ticker_matcher.md` | ✓ |
| PR-8 admin/signal | `sec_pr_8_admin_signal.md` | ✓ |
| PR-9 Neo4j sync | `sec_pr_9_neo4j_sync.md` | ✓ |
| PR-10 merger | `sec_pr_10_merger.md` | ✓ |
| PR-11~13 Phase 2 | `sec_pr_11_12_13_phase2.md` | ✓ |
| PR-14 dashboard | `sec_pr_14_dashboard.md` | ✓ |
| PR-15 on-demand | `sec_pr_15_on_demand.md` | ✓ |
| PR-16 intelligence | `sec_pr_16_intelligence.md` | ✓ |
| PR-17 e2e | `sec_pr_17_e2e.md` | ✓ |

### 미해결 항목 (설계서 §향후 과제에 명시, 미구현/추후)

| # | 항목 | 분류 | 비고 |
|---|------|------|------|
| 1 | S&P 500 전체 배치 | (C) 미구현 | Gemini RPD 제한 고려, 현재 15종목까지만 실행 |
| 2 | Gold Set 라벨 보완 → Precision/Recall 재평가 | (C) 미구현 | PR-5 완료 후 후속 |
| 3 | JNJ Item 순서 검증 완화 | (C) 미구현 | 14/15 성공, JNJ만 실패 |
| 4 | 프롬프트 개선 ("third parties" 같은 일반 명사 추출 방지) | (C) 미구현 | 정성적 품질 이슈 |
| 5 | CompanyAlias 수동 등록 (TSMC→TSM, Samsung 등) | (C) 미구현 | 매칭률 3% 원인 — CompanyAlias 0건 |
| 6 | Ticker 매칭률 향상 | (B) 부분 | 110건 중 2건 매칭(3%), 매칭 로직은 구현됨 |

### 설계서에 없으나 구현된 항목

없음 (설계서가 사후 작성된 형태라 매우 정합).

### 갭 요약

- **구조적 갭**: 없음
- **운영 갭**: S&P 500 풀배치 미실행, CompanyAlias 수기 등록 0건 → Phase 1 결과로 보고된 매칭률(3%)이 그대로 잔존
- **결정 기록 갭**: `decisions/001_fmp_vs_sec_edgar_metadata.md` 1건만 존재. 향후 결정 추가 시 같은 폴더 사용 권장

---

## Validation 상세

### 분류: (B) 부분 구현 — 코드는 거의 완전, PR 기록만 누락

설계서 4종:
- `validation_design.md` (1,646줄, v1.4)
- `validation_peer_system.md` (403줄, 프리셋 시스템)
- `validation_peer_phase6_7.md` (382줄, Thematic + LLM 필터)
- `validation_pr_prompts.md` (414줄, 13개 PR 프롬프트)

### 모델 (설계 9개 + Peer 확장 → 구현 위치 분산)

| 설계 모델 | 구현 위치 | 분류 |
|-----------|-----------|------|
| MetricDefinition | `metrics/models/metric_definition.py` | (A) — 앱 분리 결정으로 metrics로 이동 |
| CompanyMetricSnapshot | `metrics/models/metric_snapshot.py` | (A) |
| CompanyMetricLatest | `validation/models/metric_latest.py` | (A) |
| PeerMetricBenchmark | `metrics/models/benchmark.py:96` | (A) |
| IndustryMetricBenchmark | `metrics/models/benchmark.py:57` | (A) |
| CompanyBenchmarkDelta | `validation/models/benchmark_delta.py` | (A) |
| PeerListCache | `metrics/models/benchmark.py:5` | (A) |
| CategorySignal | `validation/models/category_score.py` | (A) — "CategoryScore"에서 이름 변경 |
| BatchJobRun | `metrics/models/batch_job.py` | (A) |
| **PeerPreset** (Peer system v2) | `validation/models/peer_preset.py:5` | (A) |
| **UserPeerPreference** | `validation/models/peer_preset.py:43` | (A) |
| **ValidationNewsSummary** | `validation/models/news_summary.py` | (A) — 설계서 외 추가 |
| IndustryClassification.handling_mode | (외부 `stocks/`?) | 미확인 (감사 범위 외) |

> **구조 결정**: 설계서는 `validation` 단일 앱을 가정했으나 실제로는 **`metrics` 앱이 메타데이터/스냅샷/벤치마크/배치로그를 보유**하고 `validation`은 도출 결과(Latest, Delta, Signal) + Peer 관리만 보유하도록 **분리됨**. 설계서 §7과 표면적으로 다르므로 v1.5 명시 권장.

### Celery Task (설계 Task 1~6 → 구현 7개 task)

| 설계 | 구현 (`validation/tasks.py`) | 분류 |
|------|------------------------------|------|
| Task 1 fetch_annual_financials | `fetch_annual_financials` (L22) | (A) |
| Task 2 calculate_derived_metrics | `calculate_derived_metrics` (L36) | (A) |
| Task 3 calculate_benchmarks | `calculate_benchmarks` (L50) | (A) |
| Task 3.5 calculate_relative_metrics | `calculate_relative_metrics` (L64) | (A) |
| Task 4 calculate_category_signals | `calculate_category_signals` (L78) | (A) |
| Task 5 update_peer_list_caches | `update_peer_list_caches` (L92) | (A) |
| Task 6 log_batch_run | `log_batch_run` (L105) | (A) |
| (오케스트레이터) | `run_weekly_validation_batch` (L140) | (A) |

> Celery는 `validation/tasks.py`에 있으나 일부 Phase 5 task는 `metrics/tasks.py`에도 존재 가능 (한 줄만 grep 노출). 분기 책임 명확화 권장.

### 서비스 레이어 (설계 §5.3 + Phase 6/7)

| 컴포넌트 | 구현 | 분류 |
|----------|------|------|
| Peer Preset Generator (6 preset) | `validation/services/preset_generator.py` | (A) |
| Benchmark Calculator | `validation/services/benchmark_calculator.py` | (A) |
| Category Signal Calculator | `validation/services/category_signal_calculator.py` | (A) |
| Custom Benchmark Engine (compute-on-read) | `validation/services/custom_benchmark_engine.py` | (A) |
| Metric Calculator | `validation/services/metric_calculator.py` | (A) |
| Financial Fetcher | `validation/services/financial_fetcher.py` | (A) |
| Relative Metrics | `validation/services/relative_metrics.py` | (A) |
| Interpretation (Rule-based) | `validation/services/interpretation.py` | (A) |
| LLM Peer Filter (Phase 7) | `validation/services/llm_peer_filter.py` | (A) |

### API (설계 §5 + Peer Phase 6/7)

| 엔드포인트 | 구현 | 분류 |
|------------|------|------|
| GET `/api/v1/validation/<symbol>/summary/` | ValidationSummaryView | (A) |
| GET `/api/v1/validation/<symbol>/metrics/` | ValidationMetricsView | (A) |
| GET `/api/v1/validation/<symbol>/leader-comparison/` | LeaderComparisonView | (A) |
| GET `/api/v1/validation/<symbol>/presets/` | PresetListView | (A) |
| POST/DELETE `/api/v1/validation/<symbol>/peer-preference/` | PeerPreferenceView | (A) |
| POST `/api/v1/validation/<symbol>/llm-filter/` | LLMPeerFilterView | (A) |

### Management Command

- `evaluate_gold_set`, `process_unmatched_queue`, `rematch_unmatched`, `seed_company_aliases` — 4개 존재 (sec_pipeline 앱)
- validation 앱 자체: `validation/management/commands/` 디렉토리는 있으나 내용물은 `__pycache__`만 노출됨 (`seed_validation_data` 등 설계 명시 command 존재 여부 추가 확인 필요)
- metrics 앱: `seed_metric_definitions.py` ✓, `send_daily_report.py` ✓

### 프론트엔드 (FE-PR-1~7)

| FE 컴포넌트 (설계) | 구현 | 분류 |
|-------------------|------|------|
| SignalSummaryCard | `frontend/components/validation/SignalSummaryCard.tsx` | (A) |
| PeerContextBar | `PeerContextBar.tsx` | (A) |
| MetricCard | `MetricCard.tsx` | (A) |
| MetricBarChart | `MetricBarChart.tsx` | (A) |
| MetricInfoTooltip | `MetricInfoTooltip.tsx` | (A) |
| CategorySection | `CategorySection.tsx` | (A) |
| CategorySidebar | `CategorySidebar.tsx` | (A) |
| IndustryPosition | `IndustryPosition.tsx` | (A) |
| LeaderComparisonSection | `LeaderComparisonSection.tsx` | (A) |
| 모바일 Accordion (v1.4 명시) | 별도 컴포넌트 미확인 | (B) — CategorySection 내 모바일 분기 가능성 |

### PR task_done cross-reference

| PR (`validation_pr_prompts.md`) | task_done 기록 | 분류 |
|-------------------------------|----------------|------|
| BE-PR-1 앱+모델+마이그레이션 | ❌ 없음 | (B) — 코드 구현 OK, 보고서 누락 |
| BE-PR-2 시드 데이터 | ❌ 없음 | (B) |
| BE-PR-3 Task 1-2 | ❌ 없음 | (B) |
| BE-PR-4 Task 3-3.5 | ❌ 없음 | (B) |
| BE-PR-5 Task 4-6 | ❌ 없음 | (B) |
| BE-PR-6 API Views | ❌ 없음 | (B) |
| FE-PR-1~7 | ❌ 없음 | (B) |
| Peer Phase 6 Thematic | ✓ `peer_phase6_thematic.md` | (A) |
| Peer Phase 7 LLM filter | ✓ `peer_phase7_llm_filter.md` | (A) |

### 미해결 / 향후 (설계서 §10 Phase 4/5)

| 항목 | 분류 | 비고 |
|------|------|------|
| 모바일 Accordion UX (v1.4 §3.4 명시) | (B) | 별도 컴포넌트가 없어 검증 필요 |
| Phase 5 LLM 도입 (Phase 2 LLM 해석 v1.3 명시) | (C) | "Phase 4 완료 후" 조건부 |
| LLM Peer Filter — Chain Sight 완성 의존성 (peer_phase6_7.md §11.4) | (A) | 이미 구현되었으나 Chain Sight v2 완료 가정 |
| seed_validation_data command | (B) | 디렉토리는 존재, 파일 명시 미확인 |

### 갭 요약

- **구조적 갭**: 설계서가 `validation` 단독 앱을 가정했으나 실제는 `metrics` + `validation` 두 앱으로 분리. 설계서 갱신 필요.
- **추적 갭**: BE-PR 6건 + FE-PR 7건 모두 task_done 보고서 부재. 코드는 들어왔으나 PR 단위 기록이 끊김.
- **기능 갭**: Phase 5 LLM 해석 도입은 의도된 보류.

---

## News 상세

### 분류: (B) 부분 구현 — 코드는 거의 완전, PR 기록 부재

설계서 3종:
- `news_pipeline_monitoring_design.md` (1,160줄, v1.1) — Phase A/B/C 대시보드 + 알림
- `news_keyword_detail_plan.md` (216줄) — 한국어 키워드 → 영문 기사 매칭
- `keyword_detail_bottomsheet_v2.md` (80줄) — BottomSheet UX v2

### 모델 (설계 vs 구현)

| 설계 모델 | 구현 위치 | 분류 |
|-----------|-----------|------|
| NewsArticle | `news/models.py:19` | (A) |
| NewsEntity | `news/models.py:211` | (A) |
| EntityHighlight | `news/models.py:302` | (A) |
| SentimentHistory | `news/models.py:341` | (A) |
| DailyNewsKeyword | `news/models.py:391` | (A) |
| MLModelHistory | `news/models.py:494` | (A) |
| NewsCollectionCategory | `news/models.py:599` | (A) |
| NewsCollectionLog | `news/models.py:663` | (A) — Phase A 의존 모델 |
| **AlertLog** (Phase C §6.3) | `news/models.py:684` | (A) |

### Phase A — 백엔드 API (설계 §3, 4개 엔드포인트)

| 엔드포인트 | 구현 | 분류 |
|------------|------|------|
| GET `/api/v1/news/collection-logs/` | `NewsViewSet.collection_logs` (L1329) | (A) |
| GET `/api/v1/news/pipeline-health/` | `pipeline_health` (L1439) | (A) |
| GET `/api/v1/news/ml-trend/` | `ml_trend` (L1693) | (A) |
| GET `/api/v1/news/llm-usage/` | `llm_usage` (L1773) | (A) |

### Phase A — 프론트엔드 대시보드 (설계 §4)

| 컴포넌트 | 구현 | 분류 |
|----------|------|------|
| NewsPipelineSubTab | `frontend/components/admin/news/NewsPipelineSubTab.tsx` | (A) |
| CollectionStatsTable | ✓ | (A) |
| PipelineStatusBar | ✓ | (A) |
| LLMUsageSummary | ✓ | (A) |
| RecentErrorsList | ✓ | (A) |
| MLModelCard | ✓ | (A) |
| MLTrendChart | ✓ | (A) |

### Phase B — 백엔드 (설계 §5)

| 엔드포인트 | 구현 | 분류 |
|------------|------|------|
| GET `/api/v1/news/task-timeline/` | `task_timeline` (L1893) | (A) |
| GET `/api/v1/news/neo4j-status/` | `neo4j_status` (L1954) | (A) |
| GET `/api/v1/news/ml-rollback-preview/` | `ml_rollback_preview` (L2015) | (A) |
| POST `/api/v1/news/ml-rollback/` | `ml_rollback` (L2055) | (A) |

### Phase B — 프론트엔드

| 컴포넌트 | 구현 | 분류 |
|----------|------|------|
| TaskTimelineChart | ✓ | (A) |
| Neo4jStatusCard | ✓ | (A) |
| MLCompareView | ✓ | (A) |

### Phase C — 알림 (설계 §6)

| 항목 | 구현 | 분류 |
|------|------|------|
| AlertLog 모델 | ✓ `news/models.py:684` | (A) |
| GET `/api/v1/news/alerts/` | `alerts` (L2100) | (A) |
| POST `/api/v1/news/alerts/<pk>/resolve/` | `alerts/<id>/resolve` (L2164) | (A) |
| AlertBadge | ✓ | (A) |
| AlertList | ✓ | (A) |
| 알림 채널 (Slack/Email — 설계 §6.2) | 미확인 (Beat schedule 또는 task 측 구현 가능성) | (B) |

### Keyword Detail (`news_keyword_detail_plan.md`)

| 항목 | 구현 | 분류 |
|------|------|------|
| GET `/api/v1/news/keyword-detail/` | `keyword_detail` (L655) | (A) |
| Gemini 한→영 키워드 변환 + 분석 | `_generate_keyword_analysis` (L791) | (A) |
| 캐싱 + index 안정성 (§3-5) | View 내부 구현 (확인 필요) | (B) |
| FE KeywordDetailSheet | `frontend/components/news/KeywordDetailSheet.tsx` | (A) |
| DailyKeywordCard 통합 | `DailyKeywordCard.tsx:157` | (A) |

### BottomSheet v2 (`keyword_detail_bottomsheet_v2.md`)

- `KeywordDetailSheet.tsx` 존재. v2 명세 (drag-to-dismiss / multi-step 등) 세부 적합도는 코드 정밀 검증 필요 → **(B)** 표기.

### 외부 자산 (서비스 레이어, 설계 §2 §5)

설계서가 "기존 자산"이라 표시한 것들 모두 구현 확인:
- `news_classifier.py`, `news_deep_analyzer.py`, `keyword_extractor.py`, `keyword_sector_map.py`, `sentiment_normalizer.py`, `stock_insights.py`, `stock_recommender.py`, `personalized_feed.py`, `market_feed.py`, `interest_options.py`, `news_neo4j_sync.py`, `aggregator.py`, `deduplicator.py`, `circuit_breaker.py`, `ml_label_collector.py`, `ml_production_manager.py`, `ml_weight_optimizer.py`

### PR task_done cross-reference

- **`docs/news/task_done/` 폴더 자체 없음**. plan 디렉토리만 존재.
- §7 "파일 변경 계획"의 Phase 0/A/B/C 각 단계별 PR 분할이 설계되었으나 완료 보고서 부재.

### 선행 작업 — `_log_collection()` 커버리지 (설계 §11)

- 설계서는 "기존 코드에 `_log_collection()` 호출 누락"을 Phase 0 선행으로 정의.
- 실제 적용 여부는 본 감사 범위에서 미확인. **(B)** — `news/tasks.py` 1,433줄 내 `_log_collection` grep으로 cross-check 필요.

### 갭 요약

- **구조적 갭**: 없음 — Phase A/B/C 모든 API endpoint + FE 컴포넌트 구현됨.
- **추적 갭**: task_done 폴더 부재, PR 단위 기록 100% 누락.
- **운영 갭**:
  - Phase C 알림 채널(Slack/Email 발송 측) 구현 미확인
  - Phase 0 선행 `_log_collection()` 커버리지 보강 적용 여부 미확인
  - KeywordDetail 캐싱/index 안정성 (§3-5) 코드 정밀 검증 필요

---

## 종합 권장 액션 (참고용, 본 감사 범위 외)

1. **Validation/News에 `task_done/` 폴더 신설**하여 사후 회고형 PR 보고서 13~20건 작성 — SEC Pipeline 패턴과 일치.
2. **설계서 v1.5 갱신** — Validation은 `metrics` + `validation` 분리 구조 명시, News는 Phase A/B/C 완료 표기.
3. **잔존 운영 항목**:
   - SEC: CompanyAlias 수기 등록(TSMC/Samsung 등) + S&P 500 풀배치
   - Validation: 모바일 Accordion UX 검증, `seed_validation_data` command 존재 확인
   - News: Slack/Email 알림 발송 측 구현 + `_log_collection()` 커버리지 grep 검증
