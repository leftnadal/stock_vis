# SEC Pipeline + Validation + News 설계 갭 감사

> 작성일: 2026-05-16
> 범위: `sec_pipeline/`, `validation/`, `news/` 3개 앱
> 방법: `docs/` 산하 설계서 + `task_done/` 완료 보고서 ↔ 실제 구현 파일 매핑
> 분류 기호: **A** 완전 구현 / **B** 부분 구현 / **C** 미구현 / **D** 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 설계 범위 | A | B | C | D | 구현률 |
|---|---|---:|---:|---:|---:|---:|
| **SEC Pipeline** | 17 PR + 5 향후과제 + 1 결정 | 18 | 1 | 4 | 0 | **78%** (코어 PR 17 = 100%, 향후과제 1/5) |
| **Validation** | 7 Phase + 1차 검증 설계서 | 7 | 0 | 0 | 0 | **100%** (Phase 1~7 백엔드 전수 구현, Thesis 연동 일부 미확인) |
| **News** | 3 Plan + 6 Phase Intelligence | 9 | 0 | 1 | 1 | **82%** (백엔드 95%, 프론트엔드 범위 밖, alphavantage 폐기) |

종합: **3개 앱 모두 설계서가 정의한 백엔드 컴포넌트는 사실상 전부 구현되어 있다.** 미구현은 "향후 과제" 성격(S&P 500 전체 배치, JNJ Item 순서 검증 완화 등 운영/튜닝 항목)이거나 별도 산출물(프론트엔드)에 속한다.

---

## SEC Pipeline 상세

### 컨텍스트

- 설계: `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md` + `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` + 17개 `sec_pr_*.md`
- 구현: `sec_pipeline/` (21 파일, 8 모델, 4 management commands)
- 1일짜리 압축 개발(2026-04-04)이며 task_done 17 PR가 실측 구현과 1:1 대응.

### Phase × 컴포넌트 매트릭스

| PR | 컴포넌트 | 설계서 명세 | 구현 위치 | 분류 |
|---|---|---|---|:---:|
| PR-1 | 8개 모델 + migration | RawDocumentStore, SupplyChainEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, BusinessModelSnapshot, BusinessModelEvidence, PipelineIntelligenceReport | `sec_pipeline/models.py` (RawDocumentStore:15, SupplyChain:61, BMSnapshot:122, BMEvidence:201, FilingProcessLog:231, CompanyAlias:273, UnmatchedQueue:307, IntelligenceReport:351) | **A** |
| PR-2 | SEC EDGAR Collector + 섹션 추출 (regex 3단계 + edgartools fallback) + 사후검증 | `collector.py`, `validators.py` | **A** |
| PR-3 | Track A 추출 (Gemini 2.5 Flash) + Pass 1 키워드 필터 + confidence_grade | `extractor.py`, `prompts.py`, `normalizer.py`, `validator_track_a.py` | **A** |
| PR-4 | Celery tasks (collect, extract) | `tasks.py: collect_and_extract`, `extract_from_document` | **A** |
| PR-5 | Gold Set 10종목 + 평가 커맨드 | `management/commands/evaluate_gold_set.py`, `fixtures/` | **A** |
| PR-6 | 15종목 Phase 1 배치 | `sp500.py` + tasks chord | **A** |
| PR-7 | TickerMatcher 3단계 매칭 (alias → exact → fuzzy) | `ticker_matcher.py` | **A** |
| PR-8 | Admin + post_save signal (CompanyAlias 자동 등록) | `admin.py`, `signals.py`, `management/commands/seed_company_aliases.py` | **A** |
| PR-9 | Neo4j sync (DELETE+CREATE dynamic type) | `tasks.py: sync_dirty_to_neo4j` | **A** |
| PR-10 | 관계 병합 + DQS 계산 + 큐 처리 | `merger.py`, `management/commands/process_unmatched_queue.py`, `rematch_unmatched.py` | **A** |
| PR-11 | Track B 키워드 사전 (5개 필드) | `keywords_track_b.py` | **A** |
| PR-12 | Track B 추출 + validator + BusinessModelSnapshot/Evidence 저장 | `validator_track_b.py`, extractor 확장 | **A** |
| PR-13 | metrics 게이트 (for_api 경계) | `metrics/services/business_model_service.py` | **A** (간접 참조 원칙 5 준수) |
| PR-14 | Admin 대시보드 + 7개 품질 체크 | `quality_checks.py`, `views.py`, `templates/admin/sec_pipeline/dashboard.html` | **A** |
| PR-15 | On-demand filing 수집 + RSS 신규 감지 | `on_demand.py`, `tasks.py: check_new_filings` (RSS 대신 submissions API polling) | **A** (대체 구현, decision 001 연속) |
| PR-16 | Intelligence Report (Gemini 5차원 분석) | `intelligence.py: PipelineDataCollector + PipelineIntelligenceReporter`, `tasks.py: generate_intelligence_report` | **A** |
| PR-17 | E2E batch + chord (run_batch_and_report) | `tasks.py: run_batch_and_report` | **A** |

### 의사결정 반영

- **Decision 001 (FMP → SEC EDGAR 메타데이터)**: ✅ `collector.py` 전면 SEC EDGAR; FMP key 의존성 sec_pipeline에서 제거. 후속(PR-15 check_new_filings_via_fmp) 도 SEC EDGAR submissions API polling 방식으로 대체 구현 → **A** (RSS 대신 더 안정적인 submissions API 채택).

### Celery beat 등록

`config/celery.py`:
- `sync_dirty_to_neo4j` (line 779, 큐: `neo4j`)
- `check_new_filings` (line 793)
- ⚠️ `run_batch_and_report` / `generate_intelligence_report` / `process_unmatched_queue` 는 beat 미등록 (수동 트리거 또는 chord 내부 호출).

### 향후 과제 (설계서 §"향후 과제" 5개)

| # | 과제 | 분류 | 근거 |
|---|---|:---:|---|
| 1 | S&P 500 전체 배치 (현재 15종목) | **C** | 코드는 가능, 운영 결정·Gemini RPD 대기 |
| 2 | Gold Set 라벨 보완 → Precision/Recall 재평가 | **C** | `fixtures/` 라벨 부족, evaluate_gold_set 결과 미공개 |
| 3 | JNJ Item 순서 검증 완화 | **C** | `validators.py` 미수정 (JNJ 1/15 실패 그대로) |
| 4 | 프롬프트 개선 (일반명사 "third parties" 제거) | **C** | `prompts.py` 버전 변경 없음 |
| 5 | CompanyAlias 수동 등록 (TSMC→TSM, Samsung 등) | **B** | Admin 액션 + `seed_company_aliases.py` 존재, 실제 등록 0건(`CompanyAlias.objects.count() = 0`) |

### SEC 결론

코어 17 PR 100% A. 향후 과제 5건 중 4건 C, 1건 B(인프라만 준비). 폐기 사례 없음.

---

## Validation 상세

### 컨텍스트

- 설계: `docs/first_validation_system/validation_design.md`(첫 검증 시스템 전체 청사진), `validation_peer_system.md`(Peer 프리셋 7-Phase v2), `validation_peer_phase6_7.md`, `validation_pr_prompts.md` + `task_done/peer_phase6_thematic.md`, `peer_phase7_llm_filter.md`
- 구현: `validation/` (5 models + 9 services + 4 migrations + API)

### Phase × 컴포넌트 매트릭스

| Phase | 컴포넌트 | 구현 위치 | 분류 |
|---|---|---|:---:|
| **1** default 프리셋 (업종+규모 fallback) | `services/preset_generator.py:80-131 _generate_default`, `services/benchmark_calculator.py:select_peers` + `assign_size_bucket`, `models/peer_preset.py:5-41 PeerPreset` | **A** |
| **1** CompanyBenchmarkDelta + CategorySignal (preset_key 확장) | `models/benchmark_delta.py`, `models/category_score.py` (signal: green/yellow/red/gray, signal_reason 포함), migration 0003·0004 | **A** |
| **2** sector_all, size_peers | `preset_generator.py:133-191 _generate_sector_all/_generate_size_peers` | **A** |
| **3** quality_top, lifecycle + confidence_score | `preset_generator.py:207 _generate_quality_top`, `:301 _generate_lifecycle`, `_calc_confidence` (peer 수 + 업종 순도 + 커버리지 + 특수섹터 페널티) | **A** |
| **4** UserPeerPreference 모델 + API | `models/peer_preset.py:43-67 UserPeerPreference` (mode/preset_key/custom_peers), `api/views.py: PeerPreferenceView POST/DELETE` | **A** |
| **5** custom mode (Compute-on-Read + Redis TTL 1h) | `services/custom_benchmark_engine.py:27-161` (Redis 캐시), `api/views.py: summary` 분기 | **A** |
| **6** thematic 프리셋 (Chain Sight 사업모델 DNA 기반) | `preset_generator.py:377 _generate_thematic` **본문 구현됨** (479줄 파일에서 그 이후가 thematic 실로직). `task_done/peer_phase6_thematic.md` 결과물 일치. ※ 단, "Phase 6은 Chain Sight 데이터 의존" — `chainsight.models.CompanyGrowthStage/CapitalDNA/SensitivityProfile/InsiderSignal` 채워졌는지가 별개 의존성 | **A** (코드) — 데이터 의존은 Chain Sight 갭 감사에서 별도 평가 |
| **7** LLM 대화형 peer 필터 (자연어 → JSON 필터 → 실행) | `services/llm_peer_filter.py:56 parse_filter_with_llm` (Gemini Flash), `:93-264 execute_peer_filter` (Chain Sight 프로필 7종 + foreign_revenue + 섹터 제외 + metric_filters), `api/views.py: LLMPeerFilterView` | **A** |

### 1차 검증 시스템 (Peer 외 기타 컴포넌트)

| 컴포넌트 | 구현 위치 | 분류 |
|---|---|:---:|
| MetricDefinition 34개 지표 × 7 카테고리 | migration 0001 + `services/metric_calculator.py` | **A** |
| ValidationNewsSummary (이벤트/센티먼트 요약) | `models/news_summary.py:4-44` (event_count, sentiment_trend, recent_highlights), migration 0002 | **A** (모델), 배치 연동은 `tasks.py` 확인 시 weekly chain 내부에 호출 |
| MetricLatest (스냅샷 최신값 캐시) | `models/metric_latest.py` | **A** |
| 해석 룰 (Interpretation) | `services/interpretation.py` (rule-based) | **A** |
| 상대 지표 계산 (Relative Metrics) | `services/relative_metrics.py` | **A** |
| Financial Fetcher | `services/financial_fetcher.py` | **A** |
| Category Signal Calculator | `services/category_signal_calculator.py` | **A** |
| Seed 커맨드 | `management/commands/seed_validation_data.py` | **A** |

### API 엔드포인트 매핑 (설계 §7)

| 엔드포인트 | 구현 | 분류 |
|---|---|:---:|
| `GET /api/v1/validation/{symbol}/summary/` | `api/views.py SummaryView` (UserPeerPreference 분기 포함) | **A** |
| `GET /api/v1/validation/{symbol}/presets/` | `api/views.py PresetsView` (confidence_label 포함) | **A** |
| `POST /api/v1/validation/{symbol}/peer-preference/` | `api/views.py PeerPreferenceView.post` | **A** |
| `DELETE /api/v1/validation/{symbol}/peer-preference/` | `api/views.py PeerPreferenceView.delete` (default 리셋) | **A** |
| `POST /api/v1/validation/{symbol}/llm-peer-filter/` | `api/views.py LLMPeerFilterView` (parse → execute → preview/apply) | **A** |

### Celery beat

`config/celery.py:768`: `validation.tasks.run_weekly_validation_batch` — 주 1회 fetch→metrics→benchmarks→relative→signals→cache→log 체인 등록 완료.

### Thesis 연동 (설계 §9 Phase 7 후반 + thesis_control)

- 설계: "LLM 대화형 peer 조정 → Thesis Control 연동"
- 구현: `validation/services/llm_peer_filter.py`는 Thesis 모델에 결과를 저장하지 않음. Thesis 측 `thesis_control/` 또는 `thesis/`에서 호출하는 흐름이 존재하는지는 본 감사 범위 밖. → **B (의문점)** — Validation 자체는 완전하나, end-to-end Thesis 통합 검증 필요.

### Validation 결론

설계서가 명시한 Phase 1~7 + 부수 컴포넌트 모두 백엔드 코드 존재. Explore 초기 보고서가 "Phase 6 미구현 / Phase 7 부분"이라 잘못 분류했으나, `preset_generator.py:377` 이후와 `llm_peer_filter.py:93-264` 본문이 모두 구현되어 있음을 직접 확인 (파일 라인 수 각각 479/264). 단, Phase 6 thematic 실효는 Chain Sight 데이터 적재 여부에 종속.

---

## News 상세

### 컨텍스트

- 설계 (Plan): `docs/news/plan/{keyword_detail_bottomsheet_v2,news_keyword_detail_plan,news_pipeline_monitoring_design}.md`
- 설계 (Intelligence): `docs/news_intelligence_plan/{overview,phase1~6,FINAL_SUMMARY}.md`
- 구현: `news/` (1 model 파일 + 4 providers + 17 services + api + 6 migrations)

### Intelligence Phase 매트릭스

| Phase | 설계 산출물 | 구현 위치 | 분류 |
|---|---|---|:---:|
| **Phase 1** Multi-provider 수집 (finnhub, fmp, marketaux, alphavantage) | `providers/{base.py, finnhub.py, fmp.py, marketaux.py}`, `services/aggregator.py`, `tasks.py: collect_daily_news, collect_market_news, collect_category_news, collect_sp500_news_fmp_orchestrator`, migration 0005 | **A** |
| Phase 1 부속: Circuit Breaker | `services/circuit_breaker.py` (FMP rate-limiting: `tasks.py:924, 1009, 1056` 사용) | **A** |
| **Phase 2** 중복 제거 + 센티먼트 정규화 | `services/deduplicator.py`, `services/sentiment_normalizer.py`, `tasks.py: aggregate_daily_sentiment` | **A** |
| **Phase 3** 분류 (Engine A/B/C) + 키워드 추출 | `services/news_classifier.py`, `services/keyword_extractor.py`, `tasks.py: classify_news_batch, extract_daily_news_keywords`, migration 0002·0003 | **A** |
| **Phase 4** Personalized feed + ML Label 수집 | `services/personalized_feed.py`, `services/ml_label_collector.py`, `tasks.py: collect_ml_labels`, `services/market_feed.py` + `services/interest_options.py` | **A** |
| **Phase 5** ML Production (auto deploy + monitoring) | `services/ml_production_manager.py`, `services/ml_weight_optimizer.py`, `tasks.py: check_auto_deploy(395), generate_weekly_ml_report(402), monitor_ml_performance(409)`, migration 0004 | **A** |
| **Phase 6** Deep Analysis + LightGBM + Neo4j sync | `services/news_deep_analyzer.py`, `services/news_neo4j_sync.py`, `tasks.py: analyze_news_deep(349), sync_news_to_neo4j(365), cleanup_expired_news_relationships(373), train_lightgbm_model(416)` | **A** |

### Plan 매트릭스

| Plan | 핵심 설계 | 구현 | 분류 |
|---|---|---|:---:|
| **keyword_detail_bottomsheet_v2** | KeywordDetailSheet 백엔드 (search_terms_en 매칭, article_ids 직접 매칭, Redis 캐시) | `news/api/views.py:655-789 keyword-detail`, `services/keyword_extractor.py:43-45, 256-258` (search_terms_en 저장) | **A** (백엔드). 프론트엔드 컴포넌트(`frontend/`)는 본 감사 범위 밖. |
| **news_keyword_detail_plan** | GET keyword-detail (date + index), Gemini 분석, fallback, Redis epoch invalidation | `views.py:655-803` (Gemini 호출 `_generate_keyword_analysis`, 실패 시 `analysis: null`) | **A** |
| **news_pipeline_monitoring_design** Phase A | collection-logs / pipeline-health / ml-trend / llm-usage 4개 API | `views.py:1329-1893` 4개 @action 모두 구현 | **A** |
| **news_pipeline_monitoring_design** Phase B | task-timeline / neo4j-status / ml-rollback-preview / ml-rollback | `views.py:1893-2055+` 4개 @action 모두 구현 | **A** |
| **news_pipeline_monitoring_design** Phase C | AlertLog 모델 + 트리거 + 알림 API | 모델: `news/models.py:684 AlertLog` + migration 0006_alertlog. 트리거: `tasks.py:1102 check_pipeline_alerts` (7개 TriggerType: CONSECUTIVE_TASK_FAILURE, ML_F1_DECLINE, KEYWORD_EXTRACTION_FAILURE, LLM_ERROR_SPIKE, NEO4J_UNAVAILABLE, COLLECTION_DROP, … `_create_alert_if_new` 중복 억제). 알림 API: `views.py:2124, 2141, 2176` (목록/미해결카운트/resolve). Beat: `celery.py:423 check_pipeline_alerts` 등록 | **A** |

> ※ Explore 보고서는 Phase C를 "(C) 부분"으로 분류했으나, 직접 검증 결과 `check_pipeline_alerts`가 7개 트리거 타입 모두 구현 + beat 등록 + Admin 등록 완료. **A로 정정.**

### Provider 변경

- **alphavantage**: 디스크 실파일 없음(__pycache__만 잔존). `views.py` pipeline-health에 'alpha_vantage' 문자열만 하드코딩됨 → **D** (구현 폐기, 모니터링 메타데이터에 흔적). FMP/Finnhub/Marketaux 3개 체계로 정착.

### Celery beat 등록 (news)

`config/celery.py`에 30+개 등록 — 수집(시간대별 3종), 분류, 분석, ML 학습·모니터링·롤백, 키워드 추출, Neo4j 동기화, 알림(`check_pipeline_alerts:423`), FMP 오케스트레이터, 아카이브 등 풀 커버.

### task_done

`docs/news/task_done/` 디렉터리 비어 있음(목록 출력 없음). News는 `docs/news_intelligence_plan/phase*_completed.md` 6건이 사실상 task_done 역할을 함.

### News 결론

설계 3개 Plan + 6 Phase Intelligence 모두 **A** 백엔드 구현 완료. `alphavantage`는 **D** 폐기. 프론트엔드 KeywordDetailSheet 등은 본 감사 범위(`news/` 백엔드) 밖이므로 별도 frontend 감사 필요.

---

## 횡단 발견 (Cross-cutting)

1. **Explore 에이전트 1차 결과 신뢰성 한계**: Validation Phase 6/7, News Phase C가 모두 "부분/미구현"으로 잘못 분류되었다. 첫 100~110줄만 본 결과. 본 감사에서 라인 수 + 핵심 함수 본문 직접 확인으로 정정했다 (`preset_generator.py` 479줄에 `_generate_thematic` ln 377+, `llm_peer_filter.py` 264줄에 `execute_peer_filter` ln 93+, `news/tasks.py:1102` `check_pipeline_alerts` 본문 + 7 trigger).
2. **모든 앱이 설계서를 충실히 따랐다**: SEC 17/17 PR, Validation 7/7 Phase, News 9/9 산출물. 1차 검증·SEC·News 영역에서 **백엔드 완성도는 사실상 100%**.
3. **운영 미진행 항목**: SEC PR 향후과제(전체 S&P 500 배치, Gold Set 보강, JNJ 검증 완화, 프롬프트 개선), Phase 6 thematic의 데이터 의존(Chain Sight DNA 적재 여부)은 모두 **운영/데이터 단계 갭**이며, 코드는 준비되어 있다.
4. **종속 의문 (Out-of-scope)**: ① Phase 6 thematic이 실효적으로 작동하려면 `chainsight.models.Company*` 4개 테이블이 채워져야 함 — 별도 Chain Sight 감사에서 확인 필요(`docs/nightly_auto_system/reports/5월/15일/chainsight_design_gap_audit.md` 참조 권장). ② Phase 7 LLM 필터 결과를 Thesis Control이 실제로 받아 활용하는지는 thesis 측 감사 영역.
5. **`docs/news/task_done/` 디렉터리는 비어 있음** — News는 `docs/news_intelligence_plan/phase*_completed.md` 6건과 `docs/news/plan/` 3건이 cross-reference 자료 역할.

---

## 권장 후속 작업 (Action Items)

1. **(SEC, 데이터)** S&P 500 전체 배치 1회 수행 → Gold Set 재평가 + Track A/B Precision/Recall 측정.
2. **(SEC, 코드)** `validators.py`의 Item 순서 검증을 "경고 + 통과"로 완화 → JNJ-류 비표준 10-K 흡수.
3. **(SEC, 프롬프트)** `prompts.py` v2: 일반 명사 ("third parties", "various suppliers") 제외 규칙 명시.
4. **(Validation, 데이터)** Chain Sight DNA 4개 테이블 적재 여부 점검 후 Phase 6 thematic preset 실효성 검증.
5. **(Validation, 통합)** Thesis Control이 LLM peer filter 결과를 받는 경로 e2e 테스트 필요.
6. **(News, 정리)** `news/providers/__pycache__/alphavantage.cpython-312.pyc` 잔존 캐시 삭제 + `views.py` 모니터링에서 'alpha_vantage' 라벨 제거 또는 "(legacy)" 표기.
7. **(공통)** Validation/News의 task_done 디렉터리에 본 감사 결과 cross-reference 추가 권장 — 현재 `docs/news/task_done/`은 비어 있음.

---

*감사 종료 — 코드 변경 0건, 읽기 전용.*
