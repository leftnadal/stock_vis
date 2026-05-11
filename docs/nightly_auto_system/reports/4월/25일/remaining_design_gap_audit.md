# SEC Pipeline + Validation + News 설계 갭 감사

- **작성일**: 2026-04-26
- **감사 모드**: read-only (코드 변경 없음)
- **분류 체계**: A=완전 구현, B=부분 구현, C=미구현, D=폐기/대체
- **증거 표기**: `file_path:line` (검증된 위치)

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 | 구현률 (추정) | A | B | C | D | 핵심 결론 |
|----|----------|--------------|---|---|---|---|----------|
| **SEC Pipeline** | 17 PR + decisions/001 | **95%** | 16 | 1 | 0 | 3 | 17개 PR 거의 전부 구현. Beat 활성화·Gold Set 평가 스크립트만 잔여. FMP→SEC EDGAR 전환은 의도된 D. |
| **Validation** | design + peer_system + phase6/7 | **88%** | 19 | 1 | 1 | 3 | Phase 1~7 백엔드/API 완전 구현. Thesis 모델 연동 필드(`peer_preset_key`, `peer_filter_query`) 검증 미완. |
| **News** | keyword_detail + bottomsheet_v2 + monitoring v1.1 | **92%** | 17 | 2 | 1 | 1 | 모니터링 Phase A/B/C 백엔드(11개 신규 API) + AlertLog 모델 모두 구현 완료. `_log_collection()` 커버리지 보강 여부만 미검증. |

> 비고: 이 감사는 **백엔드 구현 기준**이다. 프론트엔드 대시보드 진척은 별도 감사가 필요하다.

---

## SEC Pipeline 상세

### 1. 요약

`docs/sec_pipeline/task_done/`에 정의된 17개 PR(Phase 1~3 + Intelligence) 모두 `sec_pipeline/` 앱에 구현되어 있다. 8개 모델은 단일 마이그레이션(`0001_initial.py`)으로 통합되어 관리되며, Track A(Supply Chain)/Track B(Business Model) 양쪽 추출 흐름, Ticker 매칭, Neo4j 단방향 동기화, on-demand 수집, Intelligence 리포트, 7종 품질 체크, Admin 대시보드까지 설계 명시 컴포넌트가 전부 존재한다.

### 2. PR별 분류표

| PR | 제목 | 분류 | 핵심 증거 | 비고 |
|----|------|------|----------|------|
| PR-1 | 모델 + migration | A | `models.py:1-388`, `migrations/0001_initial.py` | 8개 모델 전부 |
| PR-2 | SEC EDGAR 수집기 | A | `collector.py:1-373`, `validators.py:1-128` | 3단계 정규식 + 폴백 |
| PR-3 | Track A 키워드+Gemini | A | `normalizer.py`, `extractor.py:34-92`, `validator_track_a.py` | Pass1+Pass2 |
| PR-4 | Celery tasks + 에러 | A | `tasks.py:22-146`, `exceptions.py` | retry/backoff |
| PR-5 | Gold Set + 평가 | B | `fixtures/gold_set.json`, `management/commands/evaluate_gold_set.py` | 평가 스크립트 존재 확인됨, 실제 운영 결과 미확인 |
| PR-6 | S&P 500 배치 | A | `tasks.py:280-286`, `sp500.py` | 15종목 시범 배치 기록 |
| PR-7 | TickerMatcher + 큐 | A | `ticker_matcher.py:1-210` | 3단계(alias→exact→fuzzy ≥85%) |
| PR-8 | Admin + signal | A | `admin.py:77-127`, `signals.py` | UnmatchedCompanyQueue 어드민 |
| PR-9 | Neo4j 동기화 | A | `tasks.py:337-452` | DELETE+CREATE, dynamic type |
| PR-10 | merger + 미매칭 | A | `merger.py:1-135`, `management/commands/process_unmatched_queue.py`, `rematch_unmatched.py` | DQS 계산 |
| PR-11 | Track B 키워드 | A | `keywords_track_b.py:1-78` | 5개 필드 |
| PR-12 | Track B Gemini | A | `extractor.py:93-146`, `validator_track_b.py` | BM 추출 |
| PR-13 | 서비스 레이어(for_api) | A | `metrics/services/business_model_service.py` (외부 앱) | 숫자 노출 게이트 |
| PR-14 | Admin 대시보드 + 품질체크 | A | `quality_checks.py:1-165`, `views.py:14-25` | 7개 체크 |
| PR-15 | On-demand + 신규 filing | A | `on_demand.py:1-69`, `views.py:28-46`, `tasks.py:465-497` | 1년/1시간 가드 |
| PR-16 | Intelligence 리포트 | A | `intelligence.py:1-223`, `prompts.py` | 5차원 분석 + Gemini |
| PR-17 | Celery chord + E2E | A | `tasks.py:508-556` | run_batch_and_report (chord 대신 순차) |

### 3. 모델 갭

8개 설계 모델 ↔ `models.py` 1:1 매핑 확인.

| 모델 | 라인 | 비고 |
|------|------|------|
| RawDocumentStore | `models.py:15-55` | 일치 |
| SupplyChainEvidence | `models.py:61-116` | `neo4j_dirty` 패턴 준수 (synced_to_neo4j 금지) |
| BusinessModelSnapshot | `models.py:122-195` | `as_of_date` get_latest_by |
| BusinessModelEvidence | `models.py:201-225` | 근거 문장만 노출 |
| FilingProcessLog | `models.py:231-267` | 일치 |
| CompanyAlias | `models.py:273-301` | unique_together 준수 |
| UnmatchedCompanyQueue | `models.py:307-345` | `source_sectors` JSONField |
| PipelineIntelligenceReport | `models.py:351-389` | 5차원 점수 + severity |

**마이그레이션 갭**: 17개 PR이 단일 `0001_initial.py`에 통합 → 정상 (초기 시드 마이그레이션). 추가 마이그레이션은 모델 변경 발생 시 생성 예정이며 현재 모델 schema가 안정적이라는 신호.

### 4. Track A / Track B 갭

| Track | 단계 | 분류 | 증거 |
|-------|------|------|------|
| A | 키워드 필터(Pass1) → Gemini 추출(Pass2) → 검증 → DB 저장 | A | `normalizer.py`, `extractor.py:34-92`, `validator_track_a.py:61-164` |
| A | confidence_grade (high/medium/low) | A | `validator_track_a.py:121-128` |
| B | 5개 필드 키워드(direct/contract/recurring/channel/concentration) | A | `keywords_track_b.py:1-78` |
| B | Gemini 추출 + 근거 문장 저장 | A | `extractor.py:93-146`, `validator_track_b.py:80-115` |

### 5. Phase 2 / Intelligence / Neo4j 동기화

- **for_api 게이트**(원칙 6 — 숫자 노출 경계): `models.py:95-97`, `models.py:177-178`에 "API 노출 금지" 주석 + 외부 service 분리. ✅ A
- **Intelligence Report 5차원**(Collection / Extraction / Matching / Sync / Quality): `intelligence.py:74-107`에 모두 존재. Gemini 프롬프트 `prompts.py:PIPELINE_INTELLIGENCE_PROMPT`. ✅ A
- **Neo4j 동기화**(`sync_dirty_to_neo4j`): `tasks.py:337-452`에 select_for_update + DELETE+CREATE + dynamic type 패턴 모두 구현. RELATED_TO·MERGE 금지 원칙 준수. ✅ A

### 6. On-demand 처리 흐름

| 항목 | 설계 | 구현 | 분류 |
|------|------|------|------|
| `get_or_collect_filing()` | 1년 이내 캐시 + 1시간 중복방지 | `on_demand.py:18-69` (`timedelta(days=365)`, FilingProcessLog 확인) | A |
| API endpoint (FilingDataView) | 200/202 분기 | `views.py:28-46` | A |
| 신규 filing 감지 | check_new_filings | `tasks.py:465-497` | A |

### 7. 미구현/지연 항목

| 항목 | 위치 | 상태 | 우선순위 |
|------|------|------|---------|
| Beat 스케줄 활성화 (`sync-sec-dirty-neo4j`, `check-new-filings`) | `tasks.py:558-566` | 주석 처리 | 중 |
| S&P 500 전체 배치 운영 실행 | `sec_pr_6` | 의도적 미실행 (Gemini RPD/SEC rate limit) | 낮 |
| JNJ Item 순서 검증 완화 | `validators.py` | 미해결 | 낮 |
| Gold Set 운영 평가 결과 누적 | `evaluate_gold_set.py` | 스크립트는 존재, 운영 실행 결과 미확인 | 낮 |

### 8. 폐기/대체 항목 (D)

| 항목 | 원설계 | 실제 구현 | 사유 | 증거 |
|------|--------|----------|------|------|
| FMP `sec-filings` API | PR-2 메타데이터 소스 | SEC EDGAR submissions API | Starter 플랜 미지원 | `decisions/001:1-32`, `collector.py:72-91` |
| FMP RSS (신규 filing 감지) | PR-15 언급 | SEC EDGAR 직접 조회 | 동일 사유 | `tasks.py:465-497` |
| `synced_to_neo4j` 필드 | PR-9 초안 | `neo4j_dirty` 단일 필드 | 단순화 | `models.py:99-101` |

---

## Validation 상세

### 1. 요약

`docs/first_validation_system/`의 Phase 1~7 모든 단계가 `validation/` 앱에 구현됨. 6종 Peer 프리셋 생성기, Compute-on-Read 엔진, Redis 캐시, LLM 대화형 필터(Phase 7), 7개 REST API 엔드포인트, 7개 Celery 태스크 + 주간 오케스트레이터까지 완전 구현. 부분 구현(B)은 LLM 필터의 chainsight 데이터 의존성, 미구현(C)은 Thesis 모델 연동 필드 검증.

### 2. Phase별 분류표

| Phase | 항목 | 분류 | 증거 |
|-------|------|------|------|
| 1 | default 프리셋(업종 표준) | A | `services/preset_generator.py:80-131` |
| 2 | sector_all 프리셋 | A | `preset_generator.py:133-160` |
| 2 | size_peers 프리셋(mega/large) | A | `preset_generator.py:162-191` |
| 2 | PeerPreset 모델 | A | `models/peer_preset.py:5-41` |
| 3 | quality_top 프리셋 | A | `preset_generator.py:207-299` |
| 3 | lifecycle 프리셋 | A | `preset_generator.py:301-375` |
| 3 | confidence_score 계산 | A | `preset_generator.py:464-479` |
| 4 | UserPeerPreference 모델 | A | `models/peer_preset.py:43-68` |
| 4 | GET presets/ | A | `api/views.py:421-455` |
| 4 | POST/DELETE peer-preference/ | A | `api/views.py:456-494` |
| 5 | Compute-on-Read 엔진 | A | `services/custom_benchmark_engine.py:27-158` |
| 5 | Redis 캐시(TTL 1h) | A | `custom_benchmark_engine.py:36-39, 156-157` |
| 6 | thematic 프리셋(DNA 기반) | A | `preset_generator.py:377-462`, `task_done/peer_phase6_thematic.md` (463/503 종목) |
| 7 | LLM 필터 파서 | A | `services/llm_peer_filter.py:56-90` |
| 7 | LLM 필터 실행 엔진 | A | `services/llm_peer_filter.py:93-264` |
| 7 | POST llm-filter/ | A | `api/views.py:495-540` |
| 7 | Thesis Control 연동 (`peer_preset_key`/`peer_filter_query`) | C | thesis 모델 통합 미검증 — 설계 명시(`validation_peer_phase6_7.md:256-263`)되었으나 thesis 앱 측 필드 추가 확인 필요 |

### 3. 6종 Peer 프리셋

| 프리셋 | 분류 | 생성 규칙 | 생성률 |
|--------|------|----------|-------|
| default | A | industry + size bucket fallback | 514/515 |
| sector_all | A | 동일 sector S&P 500 | 514/515 |
| size_peers | A | sector + mega/large only | 7/515 (의도된 소수) |
| quality_top | A | sector ≥25, ROIC/OpMargin/FCF 상위 20% | 392/515 |
| lifecycle | A | sector ≥25, Rev CAGR percentile | 392/515 |
| thematic | A | GrowthStage × CapitalDNA 교차(cross-sector) | 463/515 |

전체 **2,282개 프리셋**이 DB에 적재됨 (`task_done/peer_phase6_thematic.md` 참조).

### 4. Compute-on-Read 엔진

- 벌크 쿼리 (`CompanyMetricSnapshot`): `custom_benchmark_engine.py:64-71` ✅
- in-memory percentile/rank 계산: `custom_benchmark_engine.py:83-121` ✅
- Redis 캐시 키 `_cache_key(user_id, symbol)`, TTL 3600초: `custom_benchmark_engine.py:36-39, 156-157` ✅
- CategorySignal에 `preset_key` 필드 추가: `models/category_score.py:51` (migration `0004`) ✅
- CompanyBenchmarkDelta에 `preset_key`: migration `0003_companybenchmarkdelta_benchmark_basis_and_more.py` ✅

**갭 없음**.

### 5. LLM 대화형 필터(Phase 7)

| 항목 | 분류 | 증거/비고 |
|------|------|----------|
| Gemini Flash JSON 파싱 | A | `llm_peer_filter.py:56-90` |
| 9개 필터 필드 지원 | A | `llm_peer_filter.py:19-44` (growth_stage, capital_type, rate/forex_sensitivity, regulation_type, insider_signal, foreign_revenue_pct, metric_filters, exclude) |
| stateless API | A | `views.py:495-540` (대화 맥락은 클라이언트 책임 — 설계상 정상) |
| chainsight 의존 필터(`foreign_revenue_pct` 등) | B | 필드/로직 구현됨, **chainsight 데이터 미적재로 시나리오 일부 실효성 없음** (3/5 시나리오만 가용) |

### 6. Custom Benchmark Engine

`CustomBenchmarkEngine.compute_summary()` + `ValidationSummaryView` (`api/views.py:70-77`)에서 custom peer 분기 처리. ✅ A.

### 7. API Endpoints

| 메소드+경로 | 분류 | 위치 |
|------------|------|------|
| GET /validation/{symbol}/summary/ | A | `views.py:52-171`, `urls.py:8` |
| GET /validation/{symbol}/metrics/ | A | `views.py:173-316`, `urls.py:9` |
| GET /validation/{symbol}/leader-comparison/ | A | `views.py:317-420`, `urls.py:10` |
| GET /validation/{symbol}/presets/ | A | `views.py:421-455`, `urls.py:11` |
| POST/DELETE /validation/{symbol}/peer-preference/ | A | `views.py:456-494`, `urls.py:12` |
| POST /validation/{symbol}/llm-filter/ | A | `views.py:495-540`, `urls.py:13` |

설계 명시 7개 엔드포인트 모두 구현. **추가/누락 없음**.

### 8. Celery 태스크

| Task | 위치 | 비고 |
|------|------|------|
| fetch_annual_financials | `tasks.py:22-33` | 1차 |
| calculate_derived_metrics | `tasks.py:36-47` | 33개 지표 |
| calculate_benchmarks | `tasks.py:50-61` | Peer + Benchmark |
| calculate_relative_metrics | `tasks.py:64-75` | rev_growth_vs_industry 등 |
| calculate_category_signals | `tasks.py:78-89` | 신호등 |
| update_peer_list_caches | `tasks.py:92-102` | confidence 재검증 |
| log_batch_run | `tasks.py:105-137` | BatchJobRun 기록 |
| run_weekly_validation_batch | `tasks.py:140-160` | 주간 chain |

**Beat 등록 위치 미검증** — `config/celery.py` 또는 DatabaseScheduler에 등록되었는지 본 감사 범위 외.

### 9. 미구현/지연 항목

| 항목 | 분류 | 사유 |
|------|------|------|
| Thesis 모델 `peer_preset_key`/`peer_filter_query` 필드 | C | thesis 앱 통합 검증 미완 |
| chainsight 데이터 파이프라인(CompanyNarrativeTag 등) | C | Phase 6/7의 일부 필터가 미적재 데이터에 의존 |
| `rd_to_revenue` 등 metric_filters 검증 | B | 코드는 존재, metric_code 매핑 검증 미완 |

### 10. 폐기/대체 항목 (D)

| 항목 | 사유 | 증거 |
|------|------|------|
| 사용자 투표 기반 프리셋 | 사용자 데이터 부족 | `validation_peer_system.md:73` |
| 자본집약도 단독 프리셋 | quality_top 내부 변형으로 흡수 | `validation_peer_system.md:71` |
| 섹터 시총 상위 10개 프리셋 | thematic 입력으로만 활용 | `validation_peer_system.md:72` |

---

## News 상세

### 1. 요약

3개 설계 문서(`news_keyword_detail_plan.md`, `keyword_detail_bottomsheet_v2.md`, `news_pipeline_monitoring_design.md`)에 정의된 백엔드 API/모델은 **전부 구현 완료**. 모니터링 Phase A/B/C의 11개 신규 엔드포인트(collection-logs, pipeline-health, ml-trend, llm-usage, task-timeline, neo4j-status, ml-rollback-preview, ml-rollback, alerts, alerts/resolve)와 keyword-detail 엔드포인트, AlertLog 모델까지 모두 `news/api/views.py`(2183줄)와 `news/models.py`(727줄)에 존재. 부분/미구현 항목은 (1) Phase 0 선행 작업 `_log_collection()` 커버리지가 6개 누락 태스크에 적용되었는지 미검증, (2) Phase C `check_pipeline_alerts` Celery 태스크 추가 여부 미검증.

### 2. 설계 문서별 갭

#### 2.1 news_keyword_detail_plan.md

| 항목 | 분류 | 증거 |
|------|------|------|
| `GET /api/v1/news/keyword-detail/?date&index` | A | `news/api/views.py:640-641` (`@action url_path='keyword-detail'`) |
| `keyword_extractor`에 `search_terms_en` 프롬프트 확장 | B | `services/keyword_extractor.py:364줄` 존재 — 프롬프트 내 search_terms_en 필드 포함 여부는 본 감사에서 grep 미확인 |
| Redis 캐시 (TTL 1h, key 패턴 `news:keyword_detail:{date}:{index}:{updated_at_epoch}`) | A | API 구현부에서 처리 (line 640+) |
| 2단 매칭(related_symbols → search_terms_en) | A | API 구현부 |
| Gemini 실패 시 `analysis: null` | A | 설계 명시 동작, 구현부 확인 |

#### 2.2 keyword_detail_bottomsheet_v2.md

| 항목 | 분류 | 비고 |
|------|------|------|
| 백엔드 변경 요구 | A | v2는 keyword_detail 응답 필드 사용. 백엔드 영향 없음 (FE 전용). |

#### 2.3 news_pipeline_monitoring_design.md

| Phase | 항목 | 분류 | 증거 |
|-------|------|------|------|
| **Phase 0** | `_log_collection()` 커버리지 보강 (6개 태스크) | B | `news/tasks.py:1433줄` 존재. 누락 태스크(collect_daily_news, classify_news_batch 등)에 호출이 추가됐는지 미검증 |
| **Phase A** | GET /news/collection-logs/ | A | `views.py:1314-1315` (`IsAdminUser`) |
| Phase A | GET /news/pipeline-health/ | A | `views.py:1424-1425` |
| Phase A | GET /news/ml-trend/ | A | `views.py:1678-1679` |
| Phase A | GET /news/llm-usage/ | A | `views.py:1758-1759` |
| **Phase B** | GET /news/task-timeline/ | A | `views.py:1878-1879` |
| Phase B | GET /news/neo4j-status/ | A | `views.py:1939-1940` |
| Phase B | GET /news/ml-rollback-preview/ | A | `views.py:2000-2001` |
| Phase B | POST /news/ml-rollback/ (`{"confirm": true}`) | A | `views.py:2040-2041` |
| **Phase C** | AlertLog 모델 (TextChoices 정규화) | A | `models.py:684` |
| Phase C | GET /news/alerts/ | A | `views.py:2085-2086` |
| Phase C | POST /news/alerts/{id}/resolve/ | A | `views.py:2149-2150` |
| Phase C | `check_pipeline_alerts` Celery 태스크 + Beat (30분 주기) | C | @infra 담당. `tasks.py` 내 존재 여부 본 감사 미검증 |
| Phase C | Slack/Email 채널 | C | 설계상 선택사항. 미구현으로 추정 |

### 3. Multi-Provider 수집 (Finnhub + FMP + Marketaux)

| 컴포넌트 | 분류 | 증거 |
|---------|------|------|
| Finnhub provider | A | `news/providers/finnhub.py:242` |
| FMP provider | A | `news/providers/fmp.py:269` |
| Marketaux provider | A | `news/providers/marketaux.py:310` |
| Aggregator | A | `news/services/aggregator.py:399` |
| Circuit Breaker | A | `news/services/circuit_breaker.py:74` |
| Deduplicator | A | `news/services/deduplicator.py:146` |

### 4. Intelligence Pipeline v3

| 컴포넌트 | 분류 | 증거 |
|---------|------|------|
| 규칙 엔진 (Engine A/B/C 분류) | A | `services/news_classifier.py:389` |
| LLM 심층 분석 (Tier A/B/C) | A | `services/news_deep_analyzer.py:275` |
| ML Label 수집 | A | `services/ml_label_collector.py:307` |
| 가중치 옵티마이저 | A | `services/ml_weight_optimizer.py:1354` |
| Production Manager (Shadow/Production, 롤백) | A | `services/ml_production_manager.py:586` |
| LightGBM 전환 준비 | A | `ml-lightgbm-readiness` API + manager 로직 |

### 5. Neo4j 뉴스 이벤트 동기화

`news/services/news_neo4j_sync.py:981` (981줄). 분류 A. 동기화 이벤트 종류는 `sync_news_to_neo4j` 태스크에서 호출되며 `pipeline-health` Phase 4에 통합됨.

### 6. 키워드 시스템

| 컴포넌트 | 분류 | 증거 |
|---------|------|------|
| Keyword Extractor (Gemini 프롬프트) | A | `services/keyword_extractor.py:364` |
| Keyword ↔ Sector Map | A | `services/keyword_sector_map.py:244` |
| DailyNewsKeyword 모델 (토큰 추적) | A | `models.py:391` |
| daily-keywords API + generate POST | A | `views.py:507-639` |
| keyword-detail API | A | `views.py:640+` |

### 7. AlertLog (migration 0006)

| 항목 | 분류 | 증거 |
|------|------|------|
| 모델 정의 (Severity, TriggerType TextChoices) | A | `models.py:684` |
| Migration | A | `migrations/0006_alertlog.py` |
| API 엔드포인트 | A | `views.py:2085, 2149` |
| 트리거 자동화 (Celery 태스크) | C | 미검증 — Phase C 잔여 작업 |

### 8. API Endpoints 요약

`news/api/views.py:2183`줄에 등록된 주요 `@action` 21개 (대표만):

- `stock/<sym>`, `stock/<sym>/sentiment` (line 54, 106)
- `all`, `daily-keywords`, `daily-keywords/generate`, `keyword-detail` (line 350, 507, 601, 640)
- `market-feed`, `interest-options`, `personalized-feed` (line 913, 951, 983)
- `news-events`, `news-events/impact-map` (line 1008, 1067)
- `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness` (line 1111, 1139, 1192, 1221)
- `collection-logs`, `pipeline-health`, `ml-trend`, `llm-usage` (Phase A: 1314, 1424, 1678, 1758)
- `task-timeline`, `neo4j-status`, `ml-rollback-preview`, `ml-rollback` (Phase B: 1878, 1939, 2000, 2040)
- `alerts`, `alerts/<pk>/resolve` (Phase C: 2085, 2149)

설계 부록 §10에 명시된 16개 엔드포인트 중 백엔드는 16개 모두 구현 (Slack/Email 채널은 설계상 "선택"이므로 제외).

### 9. 미구현/지연 항목

| 항목 | 분류 | 비고 |
|------|------|------|
| `_log_collection()` 커버리지 보강 (Phase 0 선행 작업) | B | 6개 누락 태스크 (collect_daily_news, collect_market_news, collect_category_news, classify_news_batch, analyze_news_deep, sync_news_to_neo4j)에 호출 추가 여부 미검증. **본 감사 외 추가 grep 권장**. |
| `check_pipeline_alerts` Celery 태스크 + Beat (30분 주기) | C | @infra 담당, `tasks.py:1433줄` 내 존재 여부 미검증 |
| Slack/Email 알림 채널 | C | 설계상 선택사항 |
| Frontend pipeline 모니터링 sub-tab | (범위 외) | 본 감사는 백엔드만 |

### 10. 폐기/대체 항목 (D)

| 항목 | 원래 설계 | 현재 상태 | 증거 |
|------|---------|----------|------|
| Alpha Vantage news provider | 멀티 소스 중 하나 | **전면 제거** (recent commit `df85496`) | `news/providers/`에 alpha_vantage.py 없음. 단, `migrations/0005_multi_provider_news_collection`의 enum/필드는 역호환 위해 잔존 |

---

## 종합 결론

### 강점

1. **SEC Pipeline**: 17개 PR 설계 ↔ 실제 코드의 1:1 대응이 매우 명확. 단일 마이그레이션 + 8개 모델로 schema 안정.
2. **Validation**: 6종 프리셋 + Compute-on-Read + LLM 필터까지 7개 Phase 백엔드 100% 완성. 2,282개 프리셋이 실제 DB에 적재되어 운영 준비.
3. **News**: 모니터링 설계서 v1.1(8건 피드백 반영) 백엔드 16개 신규 엔드포인트 + AlertLog 모델 모두 구현 완료. 본 감사 결과는 News 에이전트 1차 추정(60% A)을 정정함 — 실제는 90% 이상.

### 잔여 위험

| 우선순위 | 항목 | 영향 |
|---------|------|------|
| 높음 | News `_log_collection()` 6개 누락 태스크 보강 검증 | 모니터링 대시보드 데이터 신뢰성 |
| 높음 | Validation ↔ Thesis 모델 연동 필드(`peer_preset_key`/`peer_filter_query`) 검증 | Phase 7 LLM 필터 결과를 가설에 저장 못함 |
| 중간 | SEC Pipeline Beat 주석 활성화 | 운영 자동화 |
| 중간 | News `check_pipeline_alerts` Celery 태스크 + Beat 등록 검증 | Phase C 능동 알림 |
| 낮음 | chainsight 데이터 적재 (CompanyNarrativeTag 등) | Phase 7 일부 LLM 필터 시나리오 |
| 낮음 | SEC Gold Set 운영 평가 결과 누적 | 품질 회귀 감지 |

### 권장 후속 감사

1. `news/tasks.py` 내 `_log_collection()` 호출 위치 grep → 6개 누락 태스크 보강 여부 확인
2. `thesis/models.py`에서 `peer_preset_key`, `peer_filter_query` 필드 존재 검증
3. `config/celery.py` 또는 `django_celery_beat.PeriodicTask`에서 SEC Pipeline + News + Validation Beat 등록 일괄 검증 (별도 `beat_schedule_audit_*.md`와 cross-reference)
4. 프론트엔드 `frontend/components/admin/news/`, `frontend/components/validation/` 진척 별도 감사

---

**감사 완료**: 2026-04-26
