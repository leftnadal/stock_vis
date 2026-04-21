# SEC Pipeline + Validation + News 설계 갭 감사

**감사일**: 2026-04-22
**대상**: `sec_pipeline/`, `validation/`, `news/`
**방법**: 설계 문서(docs/) vs 구현 코드 대조, task_done/ 완료 보고서 cross-reference
**분류 체계**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 | 구현 완성도 | A | B | C | D | 핵심 이슈 |
|----|---------|-----------|---|---|---|---|---------|
| **SEC Pipeline** | 17 PR + 1 decision | **100%** | 17 | 0 | 0 | 1(의도) | Celery Beat 비활성, Gold Set 라벨 부족, 비미국 주식 미등록 |
| **Validation** | 4 설계서 + 2 task_done | **85% (BE)** | 10 | 3 | 7(FE) | 1 | Orchestrator 미구현, News Summary 배치 누락, Beat 스케줄 없음 |
| **News** | 3 설계서 | **95%+ (BE)** | 31 | 2 | 0 | 0 | 바텀시트 FE 미확인, `check_pipeline_alerts` Beat 태스크만 잔여 |

> FE 범위는 별도 감사 대상이며, 본 보고서는 백엔드 구현 기준.

---

## SEC Pipeline 상세

### PR별 매트릭스 (17/17 완전 구현)

| PR | 제목 | 분류 | 구현 위치 | 비고 |
|----|------|------|---------|------|
| 1 | Django 앱 + 8개 모델 | A | `sec_pipeline/models.py:15-351` | RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot 등 |
| 2 | SEC EDGAR 수집 | A | `sec_pipeline/collector.py` (13.6KB) | submissions API, 3단계 섹션 검증 |
| 3 | Track A 추출기 (공급망) | A | `normalizer.py`, `extractor.py`, `validator_track_a.py` | Gemini 2.5 Flash, confidence_grade |
| 4 | Celery tasks | A | `sec_pipeline/tasks.py` + `exceptions.py` | max_retries=3, exponential backoff |
| 5 | Gold Set (10종목) | A | `fixtures/gold_set.json`, `management/commands/evaluate_gold_set.py` | — |
| 6 | Phase 1 배치 (15종목) | A | `tasks.py` collect_and_extract 체이닝 | 14/15 성공 (JNJ 제외) |
| 7 | TickerMatcher (3단계) | A | `sec_pipeline/ticker_matcher.py` | alias → exact → fuzzy, UnmatchedCompanyQueue |
| 8 | Admin 큐 + signal | A | `admin.py`, `signals.py` | post_save signal → evidence 자동 업데이트 |
| 9 | Neo4j 동기화 | A | `tasks.py:338-447` (sync_dirty_to_neo4j) | DELETE+CREATE, dynamic type, select_for_update |
| 10 | 관계 병합 | A | `merger.py` + `process_unmatched_queue.py` | RELATIONSHIP_SPECIFICITY 점수 기반 |
| 11 | Track B 키워드 사전 | A | `keywords_track_b.py` (2.9KB) | 5개 BM 필드 |
| 12 | Track B Gemini + validator | A | `extractor.py:93`, `validator_track_b.py` | extract_business_model, confidence_grade |
| 13 | 서비스 레이어 (for_api 게이트) | A | `metrics/services/business_model_service.py:16` | confidence 숫자 API 미노출 |
| 14 | Admin 대시보드 (7개 품질 체크) | A | `quality_checks.py`, `views.py:15`, `templates/admin/sec_pipeline/dashboard.html` | 수집 실패율, unknown 비율, 매칭률 등 |
| 15 | On-demand 수집 | A | `on_demand.py`, `views.py:28-46` | 200/202 분기, check_new_filings |
| 16 | Intelligence Report (5차원) | A | `intelligence.py` (7.9KB) | PipelineDataCollector + PipelineIntelligenceReporter |
| 17 | E2E + chord | A | `tasks.py:509-545` (run_batch_and_report) | Phase 1/2/3 sequential flow |

### 핵심 원칙 준수 검증

| 원칙 | 구현 확인 |
|------|---------|
| `neo4j_dirty`만 사용 (synced_to_neo4j 금지) | ✅ `models.py:100,180` |
| MERGE 금지 (DELETE+CREATE) | ✅ `tasks.py:405-418` |
| Dynamic type (RELATED_TO 고정 금지) | ✅ `tasks.py:418` f-string |
| Sole writer (Phase 1만 쓰기) | ✅ `signals.py`도 dirty flag만 설정 |
| Phase 1 idempotent + select_for_update(skip_locked) | ✅ `tasks.py:365` |

### (D) 의도된 대체 (1건)

- **FMP `sec-filings` → SEC EDGAR submissions API**
  - 근거: `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md`
  - 구현: `collector.py:34` CIK 변환 로직

### 운영 갭 (코드 갭 아님)

| 항목 | 현황 | 영향 |
|------|------|------|
| Celery beat 스케줄 | 주석 처리 (`tasks.py:560-564`) | 자동화 미작동 |
| S&P 500 전체 배치 | 미실행 | Gemini Free Tier 제한 (15RPM/1500RPD) |
| 비미국 주식 매칭 | ~15개 미매칭 (TSMC, Samsung 등) | TickerMatcher 한계 |
| Gold Set Precision | 8.5% | NVDA만 완전 라벨, 나머지 section_presence만 |
| 프롬프트 품질 | "third parties", "OEMs" 등 일반명사 추출 | 설계서에서 개선 과제로 인정 |

---

## Validation 상세

### 기능별 매트릭스

| 영역 | 설계 출처 | 분류 | 구현 위치 | 비고 |
|------|---------|------|---------|------|
| **Peer 프리셋 6종** | `validation_peer_system.md` | A | `services/preset_generator.py` (6개 메서드) | 2,282개 프리셋 생성 (default 514, sector_all 514, thematic 463, quality_top 392, lifecycle 392, size_peers 7) |
| **Compute-on-Read 엔진** | `validation_peer_system.md §1` | A | `services/custom_benchmark_engine.py` (79줄) | Redis TTL 3600초, 벌크 쿼리 + numpy |
| **LLM 대화형 필터 (Phase 7)** | `validation_peer_phase6_7.md` | A | `services/llm_peer_filter.py`, `api/views.py LLMPeerFilterView` | Gemini 2.5 Flash, 8개 필터 차원 |
| **Thematic Peer (Phase 6)** | `validation_peer_phase6_7.md` | D | `preset_generator._generate_thematic()` | 설계: CompanyNarrativeTag 기반 → 구현: **GrowthStage × CapitalDNA 교차 조합**으로 변경 |
| **Custom Peer Group** | `validation_peer_system.md` | A | `models/peer_preset.py` (PeerPreset, UserPeerPreference) | — |
| **Category Signal (7개 카테고리)** | `validation_design.md §3.1` | A | `services/category_signal_calculator.py`, `models/category_score.py` | percentile_rank 평균 → green/yellow/red/gray |
| **Benchmark Delta (preset_key 다중화)** | `validation_design.md` | A | `models/benchmark_delta.py` | migration 0004에서 preset_key 필드 추가 |
| **Interpretation 레이어** | `validation_design.md §3.3,3.5` | A | `services/interpretation.py` (80줄) | generate_summary_text, generate_metric_interpretation, generate_leader_summary |
| **REST API 6개 엔드포인트** | `validation_pr_prompts.md BE-PR-6` | A | `api/views.py` + `api/urls.py` | summary, metrics, leader-comparison, presets, peer-preference, llm-filter 모두 구현 |
| **Task 1: fetch_annual_financials** | `BE-PR-3` | A | `services/financial_fetcher.py` | FMP 수집 |
| **Task 2: calculate_derived_metrics** | `BE-PR-3` | A | `services/metric_calculator.py` | 33개 지표 + value_status |
| **Task 3: calculate_benchmarks** | `BE-PR-4` | A | `services/benchmark_calculator.py` | Peer 선정 + Benchmark |
| **Task 3.5: relative metrics** | `BE-PR-4` | A | `services/relative_metrics.py` | rev_growth_vs_industry |
| **Task 4: calculate_category_signals** | `BE-PR-5` | A | `services/category_signal_calculator.py` | 신호등 계산 |
| **Task 5: update_peer_list_caches** | `BE-PR-5` | B | `tasks.py` | 확인만 존재, Confidence 재검증 로직 미흡 |
| **Task 6: log_batch_run** | `BE-PR-5` | B | `tasks.py` | 기본 로깅만, BatchJobRun 테이블 활용 미완 |
| **Orchestrator (run_weekly_validation_batch)** | `BE-PR-5` | C | `tasks.py` 103줄 이후 미정의 | **누락** — Celery chain 없음 |
| **Celery Beat 스케줄 (일요일 2:00 AM)** | `BE-PR-5` | C | — | **누락** — settings에 schedule 엔트리 없음 |
| **News Summary 배치** | `validation_design.md §5.3` + `BE-PR-5` | B | `models/news_summary.py` (모델만 정의) | **배치 로직 미구현** — news/ 앱 연동 없음 |
| **FE 전체 (FE-PR-1~7)** | `validation_pr_prompts.md` | C | frontend/ | 본 감사 범위 외 (별도 FE 감사 필요) |

### 설계 편차 요약

1. **Thematic 프리셋 생성 방식 변경 (D)**
   - 설계: Gemini 사업모델 태깅 → CompanyNarrativeTag.theme_tags 클러스터링
   - 구현: GrowthStage × CapitalDNA 교차 (Chain Sight DNA 재활용)
   - 판단: 타당 (빠른 구현, 비즈니스 로직 동등, "(beta)" 마크 생략은 개선 필요)

2. **Orchestrator + Beat 부재 (C)** — Critical
   - 설계서 BE-PR-5에서 `run_weekly_validation_batch` Celery chain 명시
   - 현재 `tasks.py`는 개별 @shared_task만 선언, chain 엔드포인트 없음
   - 실무 영향: **503개 종목 × 5년 배치를 수동으로 단계별 실행 필요**

3. **News Summary 연동 공백 (B)**
   - `ValidationNewsSummary` 모델만 정의 (event_count_30d/90d, avg_sentiment_30d 등)
   - news/ 앱에서 집계하는 배치 코드 없음
   - Task 5에 통합되어야 하나 미구현

### 권장 조치 (우선순위)

| 우선순위 | 조치 | 위치 |
|---------|------|------|
| **Critical** | `run_weekly_validation_batch` orchestrator 구현 | `validation/tasks.py` |
| **Critical** | Celery Beat 스케줄 등록 | `config/settings/base.py` CELERY_BEAT_SCHEDULE |
| **High** | News Summary 배치 로직 구현 | `validation/tasks.py` + news/ 연동 |
| **High** | Task 5/6 로직 보강 (Confidence 재검증, BatchJobRun 로깅) | `validation/tasks.py` |
| **Medium** | Thematic "(beta)" 마크 및 품질 문서화 | `preset_generator.py` |

---

## News 상세

### 문서별 매트릭스

#### 1. `news_keyword_detail_plan.md` (216줄) — **(A) 완전 구현**

| 기능 | 분류 | 구현 위치 |
|------|------|---------|
| GET `/keyword-detail?date&index` | A | `views.py:641-774` |
| 2단 매칭 (article_ids → related_symbols → search_terms_en) | A | `views.py:641-774`, `keyword_extractor.py:241-250` |
| Gemini 투자 관점 요약 | A | `views.py:776-814` |
| `updated_at` 기반 캐시 무효화 (TTL 3600s) | A | `views.py:695-701` |

#### 2. `keyword_detail_bottomsheet_v2.md` (80줄) — **(B) 부분 구현**

| 기능 | 분류 | 비고 |
|------|------|------|
| API 데이터 제공 | A | keyword-detail 응답 충분 |
| 가로 스크롤 Strip UI + max-w-2xl | B | FE 컴포넌트 미확인 (백엔드 감사 범위 외) |

#### 3. `news_pipeline_monitoring_design.md` (1160줄) — **(A) 완전 구현**

**Phase A — 기본 모니터링 API (4/4)**

| API | 분류 | 구현 위치 |
|-----|------|---------|
| `GET /collection-logs` | A | `views.py:1315-1422` (provider별 × 일별 집계) |
| `GET /pipeline-health` | A | `views.py:1425-1673` (6 Phase 통합, PHASE_CONFIG `views.py:1446-1453`) |
| `GET /ml-trend` | A | `views.py:1679-1756` (F1 추이 + latest_feature_importance) |
| `GET /llm-usage` | A | `views.py:1759-1874` (토큰 + 심층 분석 + 경고문구) |

**Phase B — 고급 모니터링 API (4/4)**

| API | 분류 | 구현 위치 |
|-----|------|---------|
| `GET /task-timeline` | A | `views.py:1879-1937` (24시간 간트) |
| `GET /neo4j-status` | A | `views.py:1940-1998` |
| `GET /ml-rollback-preview` | A | `views.py:2001-2040` |
| `POST /ml-rollback` | A | `views.py:2041-2081` (2단 confirm) |

**Phase C — 알림 시스템 (3/4)**

| 항목 | 분류 | 구현 위치 |
|------|------|---------|
| `AlertLog` 모델 (7 TriggerType × 4 Severity) | A | `models.py:684-715`, migration `0006_alertlog.py` |
| `GET /alerts` | A | `views.py:2085-2147` |
| `POST /alerts/{id}/resolve` | A | `views.py:2149-2160+` |
| `check_pipeline_alerts` Celery Beat 태스크 | B | **tasks.py 확인 필요** — 설계서 §6.1 "Phase C 신규, Beat 30분" 명시 |

**핵심 서비스 (13/13)**

| 서비스 | 파일 |
|-------|------|
| Circuit Breaker | `services/circuit_breaker.py` |
| Deduplicator | `services/deduplicator.py` |
| Multi-provider (FMP/Finnhub/Marketaux/AlphaVantage) | `providers/*.py`, migration 0005 |
| Sentiment Normalizer | `services/sentiment_normalizer.py` |
| News Classifier (규칙 엔진) | `services/news_classifier.py` |
| News Deep Analyzer (LLM) | `services/news_deep_analyzer.py` |
| ML Label Collector | `services/ml_label_collector.py` |
| ML Weight Optimizer (LightGBM) | `services/ml_weight_optimizer.py` (48KB) |
| ML Production Manager | `services/ml_production_manager.py` |
| News Neo4j Sync | `services/news_neo4j_sync.py` |
| Personalized Feed | `services/personalized_feed.py` |
| Stock Insights | `services/stock_insights.py` |
| Stock Recommender | `services/stock_recommender.py` |

### 마이그레이션 확인 (6/6)

| 마이그레이션 | 상태 |
|-----------|------|
| 0001_initial | ✅ |
| 0002_daily_news_keyword | ✅ |
| 0003_news_collection_category | ✅ |
| 0004_news_intelligence_pipeline_v3 (importance_score, llm_analyzed, ml_label) | ✅ |
| 0005_multi_provider_news_collection (NewsCollectionLog) | ✅ |
| 0006_alertlog | ✅ |

### 운영 품질 확인

- **캐시 정책**: collection-logs 5분(30일 시 30분), pipeline-health 5분 + force_refresh, ml-trend/llm-usage 1시간 ✅
- **보안**: IsAdminUser permission이 pipeline-health, ml-trend, llm-usage, task-timeline, neo4j-status, ml-rollback, alerts 전반에 적용 ✅
- **KST 처리**: TruncDate(tzinfo=KST) 적용 (`views.py:1387`) ✅

### 잔여 확인 항목

- `check_pipeline_alerts` Celery Beat 태스크는 설계서 §6.1에서 "Phase C 신규, Celery Beat 30분마다" 명시. `news/tasks.py`에 구현되었는지 직접 확인 필요(@infra 범위). 없다면 자동 트리거가 동작하지 않으므로 알림은 수동 생성만 가능.

---

## 종합 평가

| 앱 | 백엔드 완성도 | Critical 갭 | Medium 갭 |
|----|-----------|-----------|-----------|
| SEC Pipeline | 100% | 없음 | Celery Beat 활성화, Gold Set 확장 |
| Validation | 85% | Orchestrator + Beat, News Summary 배치 | Task 5/6 보강, Thematic beta 마크 |
| News | 95%+ | 없음 (백엔드 기준) | `check_pipeline_alerts` Beat 태스크 존재 확인 |

**전체 결론**: 3개 앱 모두 백엔드 코드 완성도는 높으며 설계-구현 일치도 우수. 주요 리스크는 **Validation 앱의 orchestrator 부재로 인한 배치 자동화 불가**, 그리고 운영 차원의 Celery Beat 스케줄 미활성화에 집중됨. News와 SEC Pipeline은 코드 레벨에서 갭이 사실상 없고 운영 활성화만 남은 상태.
