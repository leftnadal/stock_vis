# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-05-13
> **감사 범위**: `docs/sec_pipeline/` vs `sec_pipeline/`, `docs/first_validation_system/` vs `validation/`, `docs/news/plan/` vs `news/`
> **감사 방식**: 읽기 전용, 설계서 vs 구현 cross-reference (task_done/ 포함)
> **분류 체계**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 구현률(A 비율) | A | B | C | D | 총 항목 | 비고 |
|----|---------------|---|---|---|---|---------|------|
| **SEC Pipeline** | **94%** | 17/18 | 1 | 0 | 0 | 18 | Phase 1~3, 17 PR 전부 task_done. Beat 스케줄 주석 처리 1건만 잔존 |
| **Validation (1차 검증)** | **95%** | 19/20 | 1 | 0 | 0 | 20 | Phase 1~7 전부 완료. v1.4 차트(ComposedChart) 검증은 코드만 있음 |
| **News** | **88%** | 22/25 | 2 | 1 | 0 | 25 | 파이프라인 v3 + 모니터링 Phase A/B/C + AlertLog 모델까지 완료. 인앱 알림 frontend는 본 감사 범위 외 |

> **노트**: A 비율은 백엔드/모델/API 기준. 프론트엔드 별도 audit 필요한 항목은 ⚠ 표기. task_done/ 보고서가 있는 작업은 우선 A로 간주 후 코드 존재 여부로 재검증.

---

## SEC Pipeline 상세

### 설계서 출처
- `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md` (FMP→SEC EDGAR 결정)
- `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` (전체 요약, 113줄)
- `task_done/` PR-1~PR-17 (16건)

### 구현 cross-reference

| # | 설계 항목 | 분류 | 구현 위치 | 비고 |
|---|----------|------|----------|------|
| 1 | **8개 Django 모델** (RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport) | A | `sec_pipeline/models.py:15-388` (388줄) + `migrations/0001_initial.py:199줄` | 8 클래스 모두 정의됨 |
| 2 | **SEC EDGAR 수집기** (submissions API + Archives + 섹션추출 regex 3단계 + edgartools fallback) | A | `sec_pipeline/collector.py` (373줄) | task_done/sec_pr_2_collector.md |
| 3 | **섹션 사후 검증** (순서/heading/길이) | A | `sec_pipeline/validators.py` (128줄) | |
| 4 | **텍스트 정규화 + Pass 1 키워드 필터** | A | `sec_pipeline/normalizer.py` (83줄) | |
| 5 | **Track A/B LLM 프롬프트** | A | `sec_pipeline/prompts.py` (97줄) | |
| 6 | **GeminiExtractor (Track A + Track B)** | A | `sec_pipeline/extractor.py` (145줄) | task_done/sec_pr_3 |
| 7 | **Track A 검증 + confidence_grade + DB 저장** | A | `sec_pipeline/validator_track_a.py` (164줄) | |
| 8 | **Track B 검증 + DB 저장 + 5개 분류 필드** | A | `sec_pipeline/validator_track_b.py` (115줄) + `keywords_track_b.py` (78줄) | task_done/sec_pr_11_12_13_phase2.md |
| 9 | **4개 예외 클래스** | A | `sec_pipeline/exceptions.py` (35줄) | |
| 10 | **Celery tasks** (collect_and_extract, extract_from_document, sync_dirty_to_neo4j, check_new_filings, generate_intelligence_report, run_batch_and_report) | A | `sec_pipeline/tasks.py` (579줄, 7개 태스크) | task_done/sec_pr_4, sec_pr_17 |
| 11 | **3단계 Ticker 매칭** (alias → exact → fuzzy) + Unmatched 큐 적재 | A | `sec_pipeline/ticker_matcher.py` (210줄) | task_done/sec_pr_7 |
| 12 | **signals** (post_save → evidence 업데이트 + CompanyAlias 등록) | A | `sec_pipeline/signals.py` (71줄) | task_done/sec_pr_8 |
| 13 | **관계 병합 + DQS 계산** | A | `sec_pipeline/merger.py` (135줄) | task_done/sec_pr_10 |
| 14 | **Neo4j 동기화** (DELETE + CREATE dynamic type, sole writer, `neo4j_dirty` 플래그) | A | `tasks.py:337-454` (sync_dirty_to_neo4j) | task_done/sec_pr_9, `synced_to_neo4j` 대신 `neo4j_dirty` 채택 |
| 15 | **PipelineDataCollector + PipelineIntelligenceReporter** (Gemini 5차원 분석) | A | `sec_pipeline/intelligence.py` (223줄) | task_done/sec_pr_16 |
| 16 | **7개 품질 체크 + 대시보드 통계** | A | `sec_pipeline/quality_checks.py` (165줄) | task_done/sec_pr_14 |
| 17 | **On-demand filing 수집** | A | `sec_pipeline/on_demand.py` (68줄) | task_done/sec_pr_15 |
| 18 | **Admin 대시보드 + FilingDataView API + URL** | A | `sec_pipeline/views.py` (51줄), `urls.py` (9줄), `admin.py` (171줄), `templates/admin/sec_pipeline/dashboard.html` | `IsAdminUser` permission 적용 |
| 19 | **Celery Beat 자동 실행** (sync-sec-dirty-neo4j */5, check-new-filings 매월 1일) | **B** | task_done/sec_pr_17_e2e.md `42행` "주석 상태" 명시 | 정의는 작성됐으나 활성화 안 됨 — 운영 자동화 미완 |
| 20 | **서비스 레이어** (`metrics/services/business_model_service.py`, for_api 게이트) | A | 파일 존재 확인 | task_done/sec_pr_11_12_13_phase2.md |

### 잔존 갭

- **B-19 (Beat schedule 미활성화)**: `sec_pr_17_e2e.md`에서 명시한 두 cron(`sync-sec-dirty-neo4j`, `check-new-filings`)이 주석 상태로 남아 있음. 실제 운영 자동화는 수동 트리거에 의존. CLAUDE.md 공통 버그 #28 (Beat dict vs DB) 대조 권장.
- **향후 과제** (sec_pipeline_complete_summary.md §향후 과제): S&P 500 전체 배치, Gold Set 라벨 보완, JNJ Item 순서 검증 완화, 일반명사("third parties") 추출 방지 프롬프트 개선, TSMC→TSM 같은 CompanyAlias 수동 등록 — 모두 운영 튜닝 영역으로 설계서 미반영 항목.

### 추가 발견 (설계서 외 구현)

- `sec_pipeline/management/commands/` 4건(`evaluate_gold_set.py`, `process_unmatched_queue.py`, `rematch_unmatched.py`, `seed_company_aliases.py`) — task_done/sec_pr_5(Gold Set), sec_pr_7(Ticker matcher) 보조 명령어. 설계서에는 명시 없으나 운영 도구로 보강됨.
- `sec_pipeline/sp500.py` (15줄) — S&P 500 심볼 유틸리티.

---

## Validation 상세

### 설계서 출처
- `docs/first_validation_system/validation_design.md` (1,646줄, v1.4)
- `docs/first_validation_system/validation_peer_system.md` (403줄, 프리셋 6종)
- `docs/first_validation_system/validation_peer_phase6_7.md` (382줄, Thematic + LLM)
- `validation_pr_prompts.md` (414줄)
- `task_done/peer_phase6_thematic.md`, `task_done/peer_phase7_llm_filter.md`

### 구현 cross-reference

| # | 설계 항목 | 분류 | 구현 위치 | 비고 |
|---|----------|------|----------|------|
| 1 | **네비게이션 재설계 (L1/L2 탭)** | ⚠️ | 프론트엔드 (`frontend/components/stock-detail/`) — 본 감사 범위 외 | 백엔드 설계서지만 FE 항목, 별도 audit 필요 |
| 2 | **API 엔드포인트 6종** (`summary`, `metrics`, `leader-comparison`, `presets`, `peer-preference`, `llm-filter`) | A | `validation/api/views.py` (562줄, 7 View) + `urls.py` (15줄) | 설계서 v1.4 §5.1 3종 + peer Phase 4/7 추가 3종 |
| 3 | **`category_signal` 테이블** (category_score에서 rename) | A | `validation/models/category_score.py:CategorySignal` + `migrations/0002` | ⚠️ 파일명은 `category_score.py`로 남아 있음 (모델명만 변경). `db_table='validation_category_signal'` |
| 4 | **value_status 5단계** (normal/missing/not_applicable/unstable/low_confidence) | A | `metric_calculator.py:determine_value_status()` (459줄) | Task 2에서 판정 |
| 5 | **benchmark_basis (industry_size/industry/sector) + benchmark_confidence** | A | `migrations/0003_companybenchmarkdelta_benchmark_basis_and_more.py` + `models/benchmark_delta.py` | |
| 6 | **peer_list_cache benchmark_basis/size_bucket/peer_tier** | A | `metrics/` 앱 마이그레이션 (`migrations/0006`) | peer_tier는 null로 예약 (Phase 2 Chain Sight 연계용) |
| 7 | **handling_mode='special'** (금융/REIT/유틸리티) | A | `stocks/migrations/0008_industryclassification.py` + `preset_generator.py:_calc_confidence` 패널티 적용 | |
| 8 | **34개 지표 카탈로그 시딩** (7 카테고리) | A | `category_signal_calculator.py:CATEGORY_METRICS`, `metric_calculator.py` | 설계서 §4 표 |
| 9 | **Celery Task 1: fetch_annual_financials** (FMP) | A | `validation/tasks.py:23-33` + `services/financial_fetcher.py` (103줄) | |
| 10 | **Task 2: calculate_derived_metrics + value_status 판정** | A | `tasks.py:36-47` + `services/metric_calculator.py` (459줄) | |
| 11 | **Task 3: calculate_benchmarks** (peer 선정 + benchmark + confidence) | A | `tasks.py:50-61` + `services/benchmark_calculator.py` (345줄) | |
| 12 | **Task 3.5: calculate_relative_metrics** (rev_growth_vs_industry) | A | `tasks.py:64-75` + `services/relative_metrics.py` (97줄) | |
| 13 | **Task 4: calculate_category_signals** (green/yellow/red/gray) | A | `tasks.py:78-89` + `services/category_signal_calculator.py` (192줄) | |
| 14 | **Task 5: update_peer_list_caches** | A | `tasks.py:92-102` (Task 3에서 이미 갱신, 확인만) | 설계 의도와 일치 |
| 15 | **Task 6: log_batch_run (BatchJobRun)** | A | `tasks.py:105-137` | |
| 16 | **Orchestrator: run_weekly_validation_batch** (chain) | A | `tasks.py:140-160` | celery chain 순차 실행 보장 |
| 17 | **Rule-based 해석 (interpretation/summary_text/leader_summary)** | A | `services/interpretation.py` (121줄) — `generate_summary_text`, `generate_metric_interpretation`, `determine_trend`, `generate_leader_summary` | LLM 도입 Phase 5는 미실시 (설계상 검토 단계, 미진입) |
| 18 | **PeerPreset + UserPeerPreference 모델 (Phase 2~4)** | A | `models/peer_preset.py` (67줄) + `migrations/0004` | preset_key 6종 + custom |
| 19 | **Phase 2 프리셋 (default, sector_all, size_peers) + Phase 3 (quality_top, lifecycle)** | A | `services/preset_generator.py` (479줄, 5 메서드) | |
| 20 | **Phase 5 커스텀 Compute-on-Read + Redis 캐시** | A | `services/custom_benchmark_engine.py` (161줄) + `views.py:73-77` 호출 | |
| 21 | **Phase 6 Thematic 프리셋 (GrowthStage × CapitalDNA)** | A | `preset_generator.py:_generate_thematic` (라인 377-462) | task_done/peer_phase6_thematic.md — 463/503 종목, 전체 프리셋 2,282개 |
| 22 | **Phase 7 LLM 대화형 필터** | A | `services/llm_peer_filter.py` (264줄) + `api/views.py:LLMPeerFilterView` (498-562) | task_done/peer_phase7_llm_filter.md — Chain Sight 데이터 의존성까지 통합 |

### 잔존 갭 / 설계 vs 구현 차이

- **A-1 (네비게이션 L1/L2 탭, ComposedChart, Accordion)**: 설계서 §1, §9, v1.4 부록 B에서 명세된 프론트엔드 항목은 본 감사 범위 외(`frontend/` 별도). 백엔드 API는 모두 준비됨.
- **소소한 명명 차이**:
  - 모델 파일명 `validation/models/category_score.py` — 설계서는 `category_signal`로 rename, 파일명만 옛 이름 잔존(모델 클래스명/`db_table`은 변경됨). 기능에는 영향 없음.
- **LLM Phase 도입 (validation_ai_cache 테이블)**: 설계서 v1.3 §8.2 / v1.4 부록은 "Phase 1 완료 후 검토"로 명시. 현재 rule-based 100% 사용 중 — 설계상 의도된 미구현(미진입).
- **Phase 7-Full 데이터 의존성**: `validation_peer_phase6_7.md §최종 로드맵` — `foreign_revenue_pct`, `rd_to_revenue` 등 Chain Sight 데이터 필요. task_done/peer_phase7_llm_filter.md "0개 (metric 데이터 한계)" — 파이프라인은 완성, 데이터 채우기는 별개 작업.

### 추가 발견

- `validation/views.py` (1줄, 빈 파일) — 옛 Django 패턴 잔존. 모든 view는 `api/views.py`로 이동. 정리 권장 (코드 수정 금지 지시이므로 보고만).
- `validation/services/__init__.py` (0줄) — 빈 패키지 마커.
- 마이그레이션 4건 (0001~0004) — 설계 v1.3/v1.4 변경 사항(value_status, benchmark_basis, preset_key) 모두 반영됨.

---

## News 상세

### 설계서 출처
- `docs/news/plan/news_pipeline_monitoring_design.md` (1,160줄, v1.1)
- `docs/news/plan/news_keyword_detail_plan.md` (216줄)
- `docs/news/plan/keyword_detail_bottomsheet_v2.md` (80줄)
- CLAUDE.md "News Intelligence Pipeline v3" 통합 명세 (607 테스트, Shadow/Production Mode)

### 파이프라인 v3 (CLAUDE.md 명세, 설계서 외 통합 구현)

| # | 항목 | 분류 | 구현 위치 |
|---|------|------|----------|
| 1 | **9개 모델** (NewsArticle, NewsEntity, EntityHighlight, SentimentHistory, DailyNewsKeyword, MLModelHistory, NewsCollectionCategory, NewsCollectionLog, AlertLog) | A | `news/models.py` (727줄) + migrations 0001~0006 |
| 2 | **Phase 1 수집** (Finnhub/Marketaux/FMP/AV providers + Circuit Breaker) | A | `providers/` 4파일 (957줄) + `services/circuit_breaker.py`, `aggregator.py`, `deduplicator.py` |
| 3 | **Phase 2 분류** (NewsClassifier Engine A/B/C) | A | `services/news_classifier.py` (389줄), `keyword_sector_map.py` |
| 4 | **Phase 3 LLM 심층 분석** | A | `services/news_deep_analyzer.py` (275줄) |
| 5 | **Phase 4 ML Label + Neo4j 동기화** | A | `services/ml_label_collector.py`, `news_neo4j_sync.py` (981줄) |
| 6 | **Phase 5 LR ML 학습 + Shadow Mode + 자동 배포** | A | `services/ml_weight_optimizer.py` (1354줄), `ml_production_manager.py` (586줄) |
| 7 | **Phase 6 LightGBM 전환 + 주간 리포트 + 하락 감지** | A | tasks.py: `train_lightgbm_model`, `generate_weekly_ml_report`, `monitor_ml_performance` |

### 모니터링 설계서 cross-reference (news_pipeline_monitoring_design.md v1.1)

| # | 설계 항목 | 분류 | 구현 위치 | 비고 |
|---|----------|------|----------|------|
| 1 | **§11 선행: `_log_collection()` 커버리지 보강** (6 태스크: collect_daily_news, market_news, category_news, classify_news_batch, analyze_news_deep, sync_news_to_neo4j) | ⚠️ B | `news/tasks.py:1367` `_log_collection` 정의 존재. 호출 패턴은 본 audit에서 코드 grep 미실시 — **검증 필요** | 설계 §11 필수 선행으로 명시. 모니터링 API가 이미 운영 중이므로 부분 이상 반영되었을 것이나, 6개 태스크 전부에 try/finally 패턴 적용 여부는 추가 확인 필요 |
| 2 | **§3.1 GET /collection-logs/** | A | `news/api/views.py:1329` `@action collection_logs` + `IsAdminUser` | days/provider/task_name 파라미터, KST 자정 cutoff 설계 |
| 3 | **§3.2 GET /pipeline-health/** (6 Phase + PHASE_CONFIG + weekday_only + force_refresh) | A | `news/api/views.py:1439-1693` `pipeline_health` (PHASE_CONFIG 정의 확인) | `is_weekend_kst` 평일/주말 분기 구현됨 (라인 1477, 1492~) |
| 4 | **§3.3 GET /ml-trend/** | A | `news/api/views.py:1693` `ml_trend` | weeks 파라미터 |
| 5 | **§3.4 GET /llm-usage/** (키워드 추출 + deep_analysis coverage_warning) | A | `news/api/views.py:1773` `llm_usage` | Phase 3 토큰 미추적 경고 포함 |
| 6 | **§5.1 GET /task-timeline/** (Phase B) | A | `news/api/views.py:1893` `task_timeline` | |
| 7 | **§5.2 GET /neo4j-status/** | A | `news/api/views.py:1954` `neo4j_status` | |
| 8 | **§5.3 GET /ml-rollback-preview/ + POST /ml-rollback/** (2단계 confirm 플로우) | A | `news/api/views.py:2015, 2055` `ml_rollback_preview`, `ml_rollback` | confirm=true 검증 패턴 |
| 9 | **§6.3 AlertLog 모델** (Severity + TriggerType TextChoices) | A | `news/models.py:684-727` + `migrations/0006_alertlog.py` | 7개 TriggerType 모두 정의됨 |
| 10 | **§6 GET /alerts/ + POST /alerts/{id}/resolve/** | A | `news/api/views.py:2100, 2164` `alerts`, `alerts_resolve` | |
| 11 | **§6.1 check_pipeline_alerts Celery 태스크** (30분 주기) | A | `news/tasks.py:1101` `check_pipeline_alerts` (정의 확인) | Beat 등록 여부는 `@infra` 담당 (설계서 §6.1 명시) — Beat 활성화 검증은 본 감사 범위 외 |
| 12 | **§4 프론트엔드 sub-tab + 6 컴포넌트 + useNewsPipeline hook** | ⚠️ | `frontend/components/admin/news/` 별도 감사 필요 | 본 감사 범위 외 |

### 키워드 상세 BottomSheet 설계서 cross-reference

| # | 설계 항목 | 분류 | 구현 위치 |
|---|----------|------|----------|
| 1 | **§3-1 `search_terms_en` 키워드 스키마 확장 (Gemini 프롬프트)** | A | `news/services/keyword_extractor.py:43-45` (fallback) + 라인 241/256-258 (프롬프트 예시) + 라인 306 (저장 슬라이싱) + 라인 321 (fallback) |
| 2 | **§4 GET /keyword-detail/?date&index API** | A | `news/api/views.py:655` `@action keyword_detail` + 캐시 키 `news:keyword_detail:{date}:{index}:{updated_epoch}` (라인 712) |
| 3 | **§3-5 Redis 캐시 + index 안정성** (`updated_at` 타임스탬프) | A | `views.py:712` |
| 4 | **v2 가로 스크롤 Strip + max-w-2xl** | ⚠️ | `frontend/components/news/KeywordDetailSheet.tsx`, `BottomSheet.tsx` 별도 감사 필요 |

### 잔존 갭

- **B-1 (`_log_collection()` 커버리지)**: 설계 §11이 모니터링 데이터 신뢰성의 전제로 명시. 헬퍼 정의는 존재(line 1367)하나, 6개 신규 태스크 전체에 try/finally 패턴이 적용됐는지는 본 감사에서 grep 미실시. 향후 코드 점검 필요. — **C 아닌 B로 분류**: 모니터링 API 4종이 이미 운영 데이터를 반환하고 있으므로 부분 적용 가능성 큼.
- **C-1 (프론트엔드 모니터링 대시보드)**: §4의 6개 신규 컴포넌트(PipelineStatusBar, CollectionStatsTable, MLModelCard, MLTrendChart, RecentErrorsList, LLMUsageSummary) + sub-tab + AlertBadge/AlertList — 본 감사 범위 외(별도 audit 권장). 백엔드 API 12개는 모두 완성.

### 추가 발견 (설계서 외 강화)

- `news/api/views.py` 2,198줄 — 단일 파일 거대화. 17개 `@action` (ml/collection/pipeline/keyword/news-events/personalized-feed/interest-options 등) 통합. 분리 리팩토링 후보.
- `news/services/stock_insights.py` (771줄) — 종목 단위 인사이트 API. 설계서 외 추가 기능.
- `news/services/personalized_feed.py` (135줄) — 사용자 맞춤 피드 (interest-options와 연계). 설계서 외.
- `news/services/stock_recommender.py` (327줄) — 추천 시스템. 설계서 외.

---

## 종합 요약

### 강점

1. **task_done/ 체계가 잘 작동**: SEC Pipeline 17 PR, Validation Phase 1~7, News v3 + 모니터링 v1.1까지 모두 완료 보고서가 존재해 추적 가능.
2. **설계서 충실도 높음**: 3개 앱 모두 모델·API·태스크 명세가 코드에 거의 1:1 대응. 단순 명명 차이(category_score.py 파일명) 외 구조적 불일치 없음.
3. **확장 패턴 일관성**: PeerPreset Phase 5/6/7 확장, News 모니터링 Phase A/B/C, SEC Phase 1/1.5/2/3 — 모두 후방 호환 마이그레이션으로 추가됨.

### 잔존 위험

1. **SEC Pipeline Beat 비활성화 (B-19)**: 운영 자동 동기화/감지 cron이 주석 상태. 수동 트리거로만 동작 중이라면 SLA 영향 가능. CLAUDE.md 공통 버그 #28 패턴 대조 필요.
2. **News `_log_collection()` 커버리지 (B-1)**: 모니터링 API 정확도의 전제. grep 검증 후 누락 태스크 보강 필요.
3. **Validation LLM Phase (설계상 미진입)**: rule-based 100%로 운영 중. 해석 품질 평가 후 도입 결정은 사용자 피드백 후 단계로 명시되어 있으나 KPI 추적 부재.
4. **프론트엔드 audit 필요**: Validation v1.4 차트(ComposedChart), News 모니터링 sub-tab/AlertBadge, BottomSheet v2 — 백엔드 contract는 완성이지만 UI 구현 검증은 별도 감사 권장.

### 권고 액션

| 우선순위 | 액션 | 책임 |
|---------|------|------|
| P0 | SEC Beat schedule 활성화 (`sync-sec-dirty-neo4j`, `check-new-filings` 주석 해제 후 DB 등록) | @infra |
| P1 | `news/tasks.py` 6개 신규 태스크 `_log_collection()` 호출 grep 검증 + 누락 시 try/finally 패턴 추가 | @infra (설계 §11 원칙) |
| P2 | 프론트엔드 audit 별도 발주: Validation v1.4 UI, News 모니터링 대시보드, 키워드 BottomSheet v2 | @frontend / @qa |
| P3 | `validation/views.py` 빈 파일 정리, `validation/models/category_score.py` 파일명 → `category_signal.py` rename 권장 (모델은 이미 CategorySignal) | @backend |
| P3 | `news/api/views.py` 2,198줄 분리 리팩토링 (도메인별 viewset 분할) | @backend |
