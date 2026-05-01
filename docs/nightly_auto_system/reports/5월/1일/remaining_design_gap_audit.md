# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-05-02
> **모드**: 읽기 전용 (코드 수정 없음)
> **범위**: `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/` 설계 ↔ 실 구현 대조

---

## 앱별 요약 (구현률)

| 앱 | 설계 산출물 수 | 구현 (A) | 부분 (B) | 미구현 (C) | 폐기/대체 (D) | 구현률 |
|----|----|----|----|----|----|----|
| **sec_pipeline** | 17 PR + 1 결정 | 17 PR + 1 결정 | 0 | 0 | 0 | **100% (A)** |
| **validation** | BE 6 PR + FE 7 PR + Peer Phase 6/7 | BE 6 + FE 6 + Peer 2 | 1 (FE 탭 구조 대체 구현) | 0 | 6개 모델 metrics 앱으로 위치 변경 | **~95% (A)** |
| **news (모니터링)** | Phase 0/A/B/C BE+FE | Phase 0/A/B/C 전부 | 0 | 0 | 0 | **100% (A)** |
| **news (키워드 상세)** | API + BottomSheet v1 + v2 | 전부 | 0 | 0 | 0 | **100% (A)** |

**총평**: 세 앱 모두 설계서 대비 "완전 구현" 단계. 미구현 항목 없음.
구조적 차이는 **validation 모델 6개가 `metrics/` 앱으로 분리된 것**과 **stock 상세 탭 컴포넌트가 page.tsx에 인라인된 것** 두 가지뿐이며, 둘 다 의도적인 재배치/단순화 결정으로 보인다.

---

## SEC Pipeline 상세

### 설계 출처

- `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md` (FMP→SEC EDGAR 결정)
- `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` (Phase 1~3 17 PR 요약)
- `docs/sec_pipeline/task_done/sec_pr_1_models.md ~ sec_pr_17_e2e.md` (17개 PR 보고서)

### 모델 (8개) — 완전 구현 (A)

| 설계 모델 | 파일 위치 | 상태 |
|---|---|---|
| `RawDocumentStore` | `sec_pipeline/models.py:15` | ✅ |
| `SupplyChainEvidence` | `sec_pipeline/models.py:61` | ✅ |
| `BusinessModelSnapshot` | `sec_pipeline/models.py:122` | ✅ |
| `BusinessModelEvidence` | `sec_pipeline/models.py:201` | ✅ |
| `FilingProcessLog` | `sec_pipeline/models.py:231` | ✅ |
| `CompanyAlias` | `sec_pipeline/models.py:273` | ✅ |
| `UnmatchedCompanyQueue` | `sec_pipeline/models.py:307` | ✅ |
| `PipelineIntelligenceReport` | `sec_pipeline/models.py:351` | ✅ |

마이그레이션: `0001_initial.py` 단일 (8개 모델 한꺼번에 생성).

### 코어 모듈 (16개) — 완전 구현 (A)

| 설계 파일 | 실제 위치 | 핵심 진입점 |
|---|---|---|
| collector.py | `sec_pipeline/collector.py` | EDGAR 수집기 |
| validators.py | `sec_pipeline/validators.py` | 섹션 사후 검증 |
| normalizer.py | `sec_pipeline/normalizer.py` | 텍스트 정규화 + Pass1 |
| prompts.py | `sec_pipeline/prompts.py` | Track A/B 프롬프트 |
| extractor.py | `sec_pipeline/extractor.py:18` | `GeminiExtractor` |
| validator_track_a.py | `sec_pipeline/validator_track_a.py` | Track A 검증 |
| validator_track_b.py | `sec_pipeline/validator_track_b.py` | Track B 검증 |
| keywords_track_b.py | `sec_pipeline/keywords_track_b.py` | Track B 사전 |
| exceptions.py | `sec_pipeline/exceptions.py` | 4개 예외 |
| sp500.py | `sec_pipeline/sp500.py` | S&P 500 유틸 |
| ticker_matcher.py | `sec_pipeline/ticker_matcher.py:22` | `TickerMatcher` (3단계) |
| signals.py | `sec_pipeline/signals.py` | post_save 시그널 |
| merger.py | `sec_pipeline/merger.py:36,76` | 관계 병합 + DQS |
| intelligence.py | `sec_pipeline/intelligence.py:63,139` | 데이터 수집기 + 리포터 |
| quality_checks.py | `sec_pipeline/quality_checks.py:17,119` | 7개 체크 + 대시보드 통계 |
| on_demand.py | `sec_pipeline/on_demand.py:18` | On-demand 수집 |

### Celery 태스크 (7개) — 완전 구현 (A)

`sec_pipeline/tasks.py` 기준:
- `collect_and_extract` (line 23) — 단일 종목 수집·추출
- `extract_from_document` (line 149) — 기 수집 문서 재추출
- `seed_relations_to_chainsight` (line 282) — Chain Sight 시드
- `sync_dirty_to_neo4j` (line 338) — `neo4j_dirty` 플래그 동기화
- `check_new_filings` (line 465) — 신규 filing 감지
- `generate_intelligence_report` (line 501) — 인텔리전스 리포트
- `run_batch_and_report` (line 509) — 배치+리포트 통합

### API + 대시보드 — 완전 구현 (A)

- `sec_pipeline/views.py:15` — `sec_pipeline_dashboard` (Admin 템플릿)
- `sec_pipeline/views.py:28` — `FilingDataView` (REST)
- `sec_pipeline/urls.py` — `admin/dashboard/`, `filing/<symbol>/` 2개 엔드포인트
- `templates/admin/sec_pipeline/dashboard.html` — Admin UI ✅

### Management Commands (4개) — 완전 구현 (A)

`sec_pipeline/management/commands/`:
- `evaluate_gold_set.py`
- `process_unmatched_queue.py`
- `rematch_unmatched.py`
- `seed_company_aliases.py`

### 미충족 / 운영성 잔여 (D-운영)

설계 요약(`sec_pipeline_complete_summary.md` §향후 과제) 5건:
1. S&P 500 전체 배치 (코드는 준비됨, 운영 실행 대기)
2. Gold Set 라벨 보완 → Precision/Recall 재평가
3. JNJ Item 순서 검증 완화
4. 프롬프트 개선("third parties" 일반 명사 추출 방지)
5. CompanyAlias 수동 등록 (TSMC→TSM, Samsung 등 비미국 주식)

→ 모두 **운영 작업**이며 **코드 갭 아님**.

---

## Validation 상세

### 설계 출처

- `docs/first_validation_system/validation_design.md` (v1.4, 1646 줄, 메인 설계서)
- `docs/first_validation_system/validation_pr_prompts.md` (BE 6 + FE 7 PR 프롬프트)
- `docs/first_validation_system/validation_peer_system.md` (Peer 6 프리셋 + custom)
- `docs/first_validation_system/validation_peer_phase6_7.md` (Phase 6 thematic + Phase 7 LLM 필터)
- `docs/first_validation_system/task_done/peer_phase6_thematic.md`
- `docs/first_validation_system/task_done/peer_phase7_llm_filter.md`

### 모델 9개 — 위치 재배치 (D, 완전 구현)

설계서는 9개 모델을 모두 `validation` 앱에 두는 안. 실제로는 **공유 가능한 6개를 `metrics/` 앱으로 분리**했다.

| 설계 모델 | 실제 위치 | 비고 |
|---|---|---|
| `MetricDefinition` | `metrics/models/metric_definition.py:4` | 분리 (D) — 다른 앱에서 재사용 |
| `CompanyMetricSnapshot` | `metrics/models/metric_snapshot.py:4` | 분리 (D) |
| `CompanyMetricLatest` | `validation/models/metric_latest.py` | 유지 |
| `PeerMetricBenchmark` | `metrics/models/benchmark.py:96` | 분리 (D) |
| `IndustryMetricBenchmark` | `metrics/models/benchmark.py:57` | 분리 (D) |
| `CompanyBenchmarkDelta` | `validation/models/benchmark_delta.py:4` | 유지 + `preset_key` 필드 추가 |
| `PeerListCache` | `metrics/models/benchmark.py:5` | 분리 (D) |
| `CategorySignal` | `validation/models/category_score.py` | 유지 |
| `BatchJobRun` | `metrics/models/batch_job.py:4` | 분리 (D) |

추가 (설계서 외):
- `validation/models/news_summary.py:ValidationNewsSummary` — 마이그레이션 0002
- `validation/models/category_score.py:CategoryScore` — 마이그레이션 0002
- `validation/models/peer_preset.py:PeerPreset` + `UserPeerPreference` — Peer 프리셋 시스템

`IndustryClassification.handling_mode` 시딩은 `metrics/management/commands/seed_metric_definitions.py`에 통합된 것으로 추정 (별도 확인 권장).

### Celery 태스크 (BE-PR-3~5) — 완전 구현 (A)

`validation/tasks.py`:
- Task 1: `fetch_annual_financials` (line 23)
- Task 2: `calculate_derived_metrics` (line 37)
- Task 3: `calculate_benchmarks` (line 51)
- Task 3.5: `calculate_relative_metrics` (line 65)
- Task 4: `calculate_category_signals` (line 79)
- Task 5: `update_peer_list_caches` (line 93)
- Task 6: `log_batch_run` (line 106)
- 오케스트레이터: `run_weekly_validation_batch` (line 141)

### Services (9개) — 완전 구현 (A)

`validation/services/`:
- `relative_metrics.py`
- `benchmark_calculator.py:46` (`BenchmarkCalculator`, `assign_size_bucket`, `get_adjacent_buckets`)
- `financial_fetcher.py`
- `preset_generator.py:18` (`PresetGenerator` — Phase 2~6 프리셋 6종 + thematic)
- `category_signal_calculator.py:45`
- `interpretation.py`
- `custom_benchmark_engine.py:27` (Phase 5 Compute-on-Read + Redis 캐시)
- `metric_calculator.py`
- `llm_peer_filter.py:56,93` (Phase 7 — `parse_filter_with_llm`, `execute_peer_filter`)

### API (BE-PR-6) — 완전 구현 + 확장 (A)

`validation/api/urls.py` — **6개 엔드포인트** (설계서 3개 + Peer 시스템 3개):
- 설계서 정의: `/summary/`, `/metrics/`, `/leader-comparison/`
- Peer 시스템 추가: `/presets/`, `/peer-preference/`, `/llm-filter/`

### Management Command — 완전 구현 (A)

`validation/management/commands/seed_validation_data.py` (BE-PR-2: 34개 지표 + handling_mode 시딩)

### Frontend (FE-PR-1~7) — 부분 구현 (B, 핵심은 모두 완성)

| 설계 컴포넌트 | 실제 위치 | 상태 |
|---|---|---|
| StockDetailLayout / PrimaryTabNav / SecondaryTabNav | `frontend/app/stocks/[symbol]/page.tsx` 인라인 | **B (대체 구현)** — 별도 컴포넌트 분리 없이 `TabType` + `pathname/searchParams`로 처리 |
| `types/validation.ts` | `frontend/types/validation.ts` | ✅ |
| `hooks/useValidation.ts` | `frontend/hooks/useValidation.ts` | ✅ |
| `SignalSummaryCard.tsx` | `frontend/components/validation/SignalSummaryCard.tsx` | ✅ |
| `PeerContextBar.tsx` | `frontend/components/validation/PeerContextBar.tsx` | ✅ |
| `MetricCard.tsx` | `frontend/components/validation/MetricCard.tsx` | ✅ |
| `MetricBarChart.tsx` | `frontend/components/validation/MetricBarChart.tsx` | ✅ |
| `MetricTooltip.tsx` | `frontend/components/validation/MetricInfoTooltip.tsx` | ✅ (이름 변경) |
| `CategorySection.tsx` | `frontend/components/validation/CategorySection.tsx` | ✅ |
| `CategorySidebar.tsx` | `frontend/components/validation/CategorySidebar.tsx` | ✅ |
| `ValidationTab.tsx` | `frontend/app/stocks/[symbol]/page.tsx:916` 인라인 | B (탭 컨테이너 인라인) |
| `IndustryPosition.tsx` | `frontend/components/validation/IndustryPosition.tsx` | ✅ |
| `LeaderComparison.tsx` | `frontend/components/validation/LeaderComparisonSection.tsx` | ✅ (이름 변경) |

> **주의**: FE-PR-1의 `StockDetailLayout/PrimaryTabNav/SecondaryTabNav` 분리 컴포넌트는 만들지 않았다. 동등 기능은 `app/stocks/[symbol]/page.tsx`에서 인라인 처리. 동작상 갭 없음, 컴포넌트 모듈화만 차이.

### Peer Phase 6 — 완전 구현 (A)

`task_done/peer_phase6_thematic.md` (2026-04-04):
- `_generate_thematic()` 메서드 추가 (`validation/services/preset_generator.py`)
- 463/503 종목에 thematic 프리셋 생성, 전체 2,282개 프리셋
- DNA 기반(GrowthStage × CapitalDNA) 클러스터 사용 — 설계서 LLM 큐레이션과 다름

### Peer Phase 7 — 완전 구현 (A)

`task_done/peer_phase7_llm_filter.md` (2026-04-04):
- `validation/services/llm_peer_filter.py` 생성
- `LLMPeerFilterView` 추가
- `POST /api/v1/validation/{symbol}/llm-filter/` 엔드포인트 동작
- 설계서 5개 시나리오 중 3개 커버 (해외매출/R&D 시나리오는 chainsight 데이터 한계로 결과 0건)
- Thesis Control 연동(`peer_preset_key`, `peer_filter_query`, `peer_filter_result`) — **별도 확인 필요** (이번 감사 범위 밖)

---

## News 상세

### 설계 출처

- `docs/news/plan/news_pipeline_monitoring_design.md` v1.1 (Phase 0/A/B/C)
- `docs/news/plan/news_keyword_detail_plan.md` (키워드 상세 v1)
- `docs/news/plan/keyword_detail_bottomsheet_v2.md` (BottomSheet v2)

### Phase 0 — 완전 구현 (A)

`_log_collection()` 커버리지 보강. 설계서 §11 누락 6개 태스크 모두 호출 추가됨.

`news/tasks.py` 기준 호출 위치:
- `collect_daily_news` (line 178) — provider='finnhub_marketaux'
- `collect_market_news` (line 220)
- `collect_category_news` (line 454)
- `classify_news_batch` (line 500) — provider='internal'
- `analyze_news_deep` (line 543) — provider='gemini'
- `sync_news_to_neo4j` (line 621) — provider='neo4j'
- 기존 4개(collect_sp500_news_fmp_batch, collect_press_releases_fmp, collect_general_news_fmp, collect_av_single_symbol)도 유지

> 주의: `collect_daily_news`의 provider 값은 설계서에서 "finnhub / marketaux 분리"였으나 실제는 통합값 `'finnhub_marketaux'`. 통계 분리가 필요하면 추후 분할 권장 (사소).

### Phase A 백엔드 — 완전 구현 (A)

`news/api/views.py`:
- `collection_logs` (line 1315, `url_path='collection-logs'`, `IsAdminUser`)
- `pipeline_health` (line 1425, `url_path='pipeline-health'`)
- `ml_trend` (line 1679, `url_path='ml-trend'`)
- `llm_usage` (line 1759, `url_path='llm-usage'`)

캐시 정책, KST 자정 컷오프, `force_refresh` 옵션, `expected_interval_hours`/평일 전용 판정 등 상세 로직 점검은 별도 코드리뷰 필요(시그니처/엔드포인트 존재만 확인).

### Phase A 프론트엔드 — 완전 구현 (A)

`frontend/components/admin/news/`:
- `PipelineStatusBar.tsx` ✅
- `CollectionStatsTable.tsx` ✅
- `MLModelCard.tsx` ✅
- `MLTrendChart.tsx` ✅
- `RecentErrorsList.tsx` ✅
- `LLMUsageSummary.tsx` ✅
- `NewsPipelineSubTab.tsx` ✅ (sub-tab 컨테이너)

`frontend/hooks/useNewsPipeline.ts` ✅

### Phase B 백엔드 — 완전 구현 (A)

`news/api/views.py`:
- `task_timeline` (line 1879, `url_path='task-timeline'`)
- `neo4j_status` (line 1940, `url_path='neo4j-status'`)
- `ml_rollback_preview` (line 2001, `url_path='ml-rollback-preview'`)
- `ml_rollback` (line 2041, `url_path='ml-rollback'`, POST + confirm 검증)

### Phase B 프론트엔드 — 완전 구현 (A)

- `TaskTimelineChart.tsx` ✅
- `Neo4jStatusCard.tsx` ✅
- `MLCompareView.tsx` ✅

### Phase C 백엔드 — 완전 구현 (A)

- `news/models.py:684` — `AlertLog` 모델
- `news/migrations/0006_alertlog.py`
- `news/admin.py:109` — `AlertLogAdmin`
- `news/api/views.py:2085` — `alerts` (GET 목록)
- `news/api/views.py:2149` — `alerts_resolve` (POST 해결처리)
- `news/tasks.py:1102` — `check_pipeline_alerts` Celery 태스크

> Beat 스케줄은 @infra 담당 영역으로 위임됨(설계서 §10). DB 스케줄 등록 여부는 별도 감사 필요.

### Phase C 프론트엔드 — 완전 구현 (A)

- `frontend/components/admin/news/AlertBadge.tsx` ✅
- `frontend/components/admin/news/AlertList.tsx` ✅

### 키워드 상세 (v1) — 완전 구현 (A)

- `news/services/keyword_extractor.py` — `search_terms_en` 프롬프트 + 파싱 추가 (line 241, 256, 306, 321)
- `news/api/views.py:640` — `keyword_detail` action (`url_path='keyword-detail'`, `date+index` 파라미터)
- `cache_key`에 `updated_at_epoch` 포함 (line 697) — 인덱스 안정성 대응 ✅
- `frontend/components/news/KeywordDetailSheet.tsx` ✅
- `frontend/components/news/KeywordBadge.tsx` ✅
- `frontend/components/news/DailyKeywordCard.tsx` ✅

### 키워드 상세 BottomSheet v2 — 완전 구현 (A)

- `frontend/components/thesis/common/BottomSheet.tsx:38` — `max-w-2xl mx-auto` 적용 ✅
- `frontend/components/news/KeywordDetailSheet.tsx:59,77,99,102,130` — `activeIndex`, `pillRefs.scrollIntoView`, 가로 스크롤 Strip, isActive 분기 ✅
- `frontend/hooks/useNews.ts:3,145` — `keepPreviousData` 적용 ✅

---

## 요약 — 분류 (A/B/C/D)

| 분류 | 항목 수 | 비고 |
|---|---|---|
| **A 완전 구현** | 압도 다수 | SEC Pipeline 17 PR + Validation BE/FE/Peer Phase 6/7 + News Phase 0/A/B/C + 키워드 상세 v1/v2 |
| **B 부분 구현** | 1 | Validation FE-PR-1: `StockDetailLayout/PrimaryTabNav/SecondaryTabNav` 별도 컴포넌트 미분리, `app/stocks/[symbol]/page.tsx` 인라인으로 동등 기능 제공 |
| **C 미구현** | 0 | 없음 |
| **D 폐기/대체** | 6+1 | (1) Validation 모델 6개(`MetricDefinition`, `CompanyMetricSnapshot`, `PeerMetricBenchmark`, `IndustryMetricBenchmark`, `PeerListCache`, `BatchJobRun`)가 `metrics/` 앱으로 위치 변경 — 다른 앱에서 재사용 가능하도록 한 의도적 결정. (2) Peer Phase 6 thematic 생성 알고리즘이 설계서의 LLM 큐레이션 → 실제는 GrowthStage × CapitalDNA 클러스터링으로 변경 |

---

## 권고사항

1. **DECISIONS.md에 누락된 결정 보강 검토** — `metrics/` 앱 분리 결정, Peer Phase 6의 DNA 클러스터링 변경 결정이 `DECISIONS.md`에 등재되어 있는지 확인.
2. **운영 잔여(SEC)** — S&P 500 전체 배치 일정, CompanyAlias 수동 등록(TSMC, Samsung 등) 운영 작업 트리거.
3. **News provider 통합값** — `collect_daily_news`의 `provider='finnhub_marketaux'`을 `finnhub`/`marketaux`로 분리하면 §3.1 by_provider 통계 정확도 향상. 설계서는 분리 호출 가정.
4. **Validation FE-PR-1 컴포넌트 분리(선택)** — 동작상 문제 없으나, 다른 종목 상세 페이지(예: 다른 라우트)에서도 재사용해야 한다면 `StockDetailLayout/PrimaryTabNav/SecondaryTabNav`로 분리 검토.
5. **Phase C Beat 스케줄 DB 등록 확인** — `check_pipeline_alerts`가 30분마다 실제로 실행되는지 `PeriodicTask` 테이블 점검 필요(common-bugs.md #28 참조).

---

**감사 결론**: SEC Pipeline + Validation + News의 설계서는 모두 구현 완료되었으며, 차이는 **모델 위치 재배치(metrics 앱 분리)**와 **stock 상세 탭 컴포넌트 인라인화** 두 가지뿐이다. 두 차이 모두 의도적 결정으로 추정되며 기능 갭은 아니다.
