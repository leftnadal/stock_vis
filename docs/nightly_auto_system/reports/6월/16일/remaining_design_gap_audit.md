# SEC Pipeline + Validation + News 설계 갭 감사

> **작성**: 2026-06-16 야간 자동 감사 (읽기 전용, 코드 무수정)
> **대상**: `docs/sec_pipeline/` ↔ `services/sec_pipeline/`, `docs/first_validation_system/` ↔ `services/validation/`, `docs/news/`(+`docs/news_intelligence_plan/`, `docs/features/news/`) ↔ `services/news/`
> **분류 기준**: (A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체

> ⚠️ **선행 발견 — 모노레포 이동(PR8a)**: 최상위 `sec_pipeline/`, `validation/`, `news/` 디렉토리에는 **stale `__pycache__`만 남아 있고 실제 소스가 없다.** 실제 코드는 전부 `services/` 하위로 이동 완료(`config/settings.py:196,200,203,205` — `services.news`/`services.serverless`/`services.validation`/`services.sec_pipeline`). 본 감사는 `services/*` 기준으로 수행했다. **운영 정리 권고: 최상위 빈 디렉토리의 잔존 `__pycache__` 제거** (혼동·import 오작동 방지).

---

## 앱별 요약 (구현률)

| 앱 | 구현률 | A | B | C | D | 한 줄 평 |
|----|--------|---|---|---|---|---------|
| **SEC Pipeline** | **~94%** | 15 | 2 | 0 | 0 | 17개 PR 전부 코드 존재. 단 코드가 문서를 앞서감(미문서 task/command 누적) + Beat "비활성" 보고가 현실과 불일치 + 매칭률 2.7%로 실효 산출 미검증 |
| **Validation** | **~85%** | 다수 | 4 | 2 | 1 | 백엔드 6 PR + Peer Phase 1~7 + FE 컴포넌트 완비. 단 **Thesis 연동 전무(C)**, FE LLM 필터 UI 없음, Phase 6 thematic 설계와 다르게 대체(D), 주간 배치 Beat drift 위험 |
| **News** | **~92%** | 대부분 | 2 | 1 | 1 | Intelligence Pipeline v3 6 Phase + 모니터링 Phase A/B/C(AlertLog 포함) 전체 백엔드 구현. 갭은 AlphaVantage provider 폐기(D), provider별 로깅 미세 불일치, deep-analysis 토큰추적 미반영 |

**종합**: 세 앱 모두 설계의 핵심 기능은 코드로 존재(미구현 C는 소수). 공통 패턴은 **"코드는 됐는데 (1) 문서가 현실을 못 따라감, (2) 후속 연동/사용자 접근 경로가 끊김, (3) self-reported 완료가 실제보다 과장"** 이다.

---

## SEC Pipeline 상세

### 한 줄 요약
17개 PR + 1 decision 중 **A:15 / B:2 / C:0 / D:0 ≈ 94%**. 모든 설계 PR이 코드로 존재하고 task_done 보고서 핵심 주장도 대부분 사실. 다만 코드가 보고서보다 앞서 나갔고(미문서 산출물 누적), "Beat 비활성" 주장이 현재 거짓이 된 것이 핵심 불일치.

### PR/기능별 분류

| PR | 기능 | 분류 | 근거 / 빠진 것 |
|----|------|------|----------------|
| Dec-001 | FMP→SEC EDGAR 메타데이터 전환 | **A** | `collector.py:72 get_filing_metadata`, `:125 _get_cik` (company_tickers.json + submissions API) |
| PR-1 | 8개 모델 + migration | **A** | `models.py` 8개 모델 전부, `migrations/0001_initial.py`. `neo4j_dirty`(`:112`), `unique_together`(`:331`) 일치 |
| PR-2 | EDGAR collector + 섹션추출 + 검증 | **A** | `collector.py:39 SECFilingCollector`(`:322 _find_section_candidates`, fallback `:189`), `validators.py:21/89` |
| PR-3 | Track A 키워드 필터 + Gemini | **A** | `normalizer.py:53/63`, `prompts.py:11`, `extractor.py:18 extract_supply_chain`, `validator_track_a.py` |
| PR-4 | Celery tasks + 4 예외 | **A** | `exceptions.py` 4개, `tasks.py:23/167/649`, `sp500.py:8` |
| PR-5 | Gold Set + 평가 | **A** | `fixtures/gold_set.json`(10심볼 AAPL..AMZN), `fixtures/gold_set_schema.py`, `evaluate_gold_set.py` |
| PR-6 | Phase 1 배치(15종목) | **A** | 실행 기록물(신규 파일 없음, 보고서 일치) |
| PR-7 | TickerMatcher 3단계 | **A** | `ticker_matcher.py:90`(alias/exact/fuzzy) + `match_with_queue`, rapidfuzz |
| PR-8 | Admin 큐 + signal | **A** | `admin.py` 8개 ModelAdmin, `signals.py:21 on_unmatched_resolved`, `apps.py` ready() |
| PR-9 | sync_dirty_to_neo4j | **A** | `tasks.py:398` 2-Phase + select_for_update + DELETE/CREATE dynamic type (MERGE 금지 원칙 준수) |
| PR-10 | merger + 큐 처리 | **A** | `merger.py:36 merge_relationship`, `:76 calculate_edge_dqs`, `process_unmatched_queue.py` |
| PR-11~13 | Track B + 서비스레이어 | **A** | `keywords_track_b.py:9`, `prompts.py:46`, `extractor.py:97 extract_business_model`, `validator_track_b.py`, `metrics/services/business_model_service.py`(`for_api` 게이트 `:16/50`) |
| PR-14 | Admin 대시보드 + 7 품질체크 | **A** | `quality_checks.py:17`(7체크)+`:116`, `views.py:16`, `templates/admin/sec_pipeline/dashboard.html`, `urls.py:8` |
| PR-15 | On-demand + 신규감지 | **B** | `on_demand.py:18`, `views.py:29 FilingDataView`, `tasks.py:544 check_new_filings` 존재. **차이**: ① decision의 "EDGAR RSS"가 아닌 전 종목 submissions 폴링(`:558`) ② 보고서엔 없던 `IsAdminUser` 권한 추가(`views.py:35`) |
| PR-16 | Intelligence Reporter | **A** | `intelligence.py:63/148`(5차원+Gemini sync), `admin.py:159` |
| PR-17 | E2E 배치 체인 + Beat | **B** | `tasks.py:580/589 run_batch_and_report`(순차) 존재. **불일치**: 보고서는 "Beat 비활성"이라 주장하나 `config/celery.py:784,791,799`에 3개 활성 |

### 실제 인벤토리
- **모델 8개** (`services/sec_pipeline/models.py`): `RawDocumentStore`, `SupplyChainEvidence`, `BusinessModelSnapshot`, `BusinessModelEvidence`, `FilingProcessLog`, `CompanyAlias`, `UnmatchedCompanyQueue`, `PipelineIntelligenceReport`
- **API** (`/api/v1/sec-pipeline/`): `GET admin/dashboard/`(staff), `GET filing/<symbol>/`(IsAdminUser, 200/202)
- **Celery 태스크 6 + 1 미문서**: `collect_and_extract`, `extract_from_document`, `sync_dirty_to_neo4j`, `check_new_filings`, `generate_intelligence_report`, `run_batch_and_report` + **`seed_relations_to_chainsight`(`tasks.py:338`, 어떤 PR에도 없음)**
- **관리 커맨드 5개 중 2개만 문서화**: 문서화 `evaluate_gold_set`/`process_unmatched_queue` · **미문서 `rematch_unmatched`/`reprocess_unmatched_queue`/`seed_company_aliases`**

### task_done Cross-Reference
| 항목 | 결과 |
|------|------|
| 8개 모델 (PR-1) / Gold Set 10심볼 (PR-5) / 8 Admin (PR-8) | **일치** |
| `check_new_filings` 명명 (Dec-001 `..._via_fmp`) | **불일치(경미)** — decision 문서가 오래됨, 실제는 EDGAR 폴링 |
| **Beat "주석/비활성" (PR-17)** | **불일치(중요)** — `config/celery.py`에 3개 활성(`sec-sync-dirty-neo4j` 5분, `sec-seed-relations-to-chainsight` 매일12시, `sec-check-new-filings` 매월1일) |
| `seed_relations_to_chainsight` task | **보고서 누락** — 코드+Beat에 존재, 17 PR 어디에도 없음 |
| DQS API 키 (PR-10) | **부분** — `merger.py:137-138` 반환값엔 있으나 노출 엔드포인트 없음 |

### 주요 갭 및 리스크 (Top 5)
1. **[중] Beat 문서-코드 불일치 + 운영 위험** — "비활성" 보고와 달리 3개 활성. 특히 `check_new_filings`(`:558`)가 S&P500 전 종목을 매월 순차 폴링 → SEC rate-limit(10 req/s) 위반·블로킹 우려 (CLAUDE.md 버그 #28 패턴).
2. **[중] 미문서 산출물 3종(drift)** — `seed_relations_to_chainsight` + 커맨드 3종 + `ticker_matcher.BLOCKED_NAMES`가 문서 없이 누적(매칭률 문제 사후 대응).
3. **[높] "완성" 시점 self-reported critical** — health_score 0.2 / 매칭률 2.7%(110건 중 2건). 추출은 작동하나 Neo4j 유효 관계 사실상 2건 → Track A 실효 가치 미검증.
4. **[중] 배치 범위 미달** — 설계는 S&P500 전체이나 실제 RawDocumentStore 15건에서 멈춤(Gemini RPD 제한).
5. **[경] DQS·BM 서비스 API 노출 부재** — `for_api` 게이트는 있으나 서빙 DRF 엔드포인트 없음(백엔드-only).

> 부수: 레거시 명명 잔존(`"fmp_metadata"` stage, `FMPApiError`) — 무해하나 혼동. 테스트는 `tests/unit/sec_pipeline/`에 12+ 파일(앱 내 `tests.py`는 스텁).

---

## Validation 상세

### 한 줄 요약
구현률 **~85%**: 백엔드 6 PR + Peer Phase 1~7 + FE 7 PR 컴포넌트 완비. 단 **(1) Thesis Control 연동 전무(C), (2) FE LLM 대화형 필터 UI 미구현(C), (3) 주간 배치 Beat drift 위험, (4) Phase 5/6/7 핵심 서비스 단위 테스트 0건, (5) Phase 6 thematic이 설계(Gemini)와 다르게 대체(D)**.

### Phase/기능별 분류

**백엔드**
| 기능 (PR) | 분류 | 근거 / 빠진 것 |
|---|---|---|
| BE-PR-1 DB 모델 | **A(위치 분산)** | validation 5개 + `metrics`앱(MetricDefinition·CompanyMetricSnapshot·PeerListCache 등) + `stocks`앱(IndustryClassification). `models/__init__.py:1-14` |
| BE-PR-2 지표 34개 시드 + handling_mode | **A** | `seed_metric_definitions.py` + `seed_validation_data.py:14-71` |
| BE-PR-3 Task1 FMP수집 + Task2 + value_status | **B** | Task1이 "FMP 직접수집" 아닌 `FinancialFetcher.check_and_fetch`(가용성 확인)로 축소 (`tasks.py:24-37`) |
| BE-PR-4 Task3 Peer+Benchmark, Task3.5 상대지표 | **A** | `benchmark_calculator.py`(select_peers, size bucket, confidence `:217-224`), `relative_metrics.py` |
| BE-PR-5 Task4 CategorySignal + Task5/6 + 오케스트레이터 | **B** | Task4 완전. **Task5 no-op**(`tasks.py:108-119`). chain 존재(`:167-176`) |
| BE-PR-6 API 3종 + rule 해석 | **A** | summary/metrics/leader-comparison + `interpretation.py` 3개 rule 함수 |
| 주간 Beat 등록(일 2시) | **B/리스크** | `celery.py:773` dict 존재하나 스케줄=**토 5시**(설계 일 2시), **DatabaseScheduler(`settings.py:497`)라 dict 무시 위험**, PeriodicTask DB 등록 없음(버그 #28) |

**Peer 시스템 (7 Phase)**
| Phase | 분류 | 근거 / 빠진 것 |
|---|---|---|
| Phase 1 default | **A** | `preset_generator._generate_default:89-143` |
| Phase 2 sector_all/size_peers + preset_key | **A** | `_generate_sector_all`, `_generate_size_peers`, 전 테이블 `preset_key` 필드 |
| Phase 3 quality_top/lifecycle + confidence | **A** | `:227`, `:339`, `_calc_confidence:526` |
| Phase 4 UserPeerPreference + 선택 API | **A** | 모델 + `PeerPreferenceView`(POST/DELETE) + `PresetListView` |
| Phase 5 custom Compute-on-Read + Redis | **B** | `CustomBenchmarkEngine.compute_summary`(Redis TTL 3600). **summary만 지원**, metrics/leader 미지원, industry_position 빈배열(`:166`), **테스트 0건** |
| Phase 6 thematic | **D** | 설계=Gemini LLM 큐레이션+theme_tags. **실제=GrowthStage×CapitalDNA 교차조합**(`_generate_thematic:425`), LLM 미사용. task_done은 인정하나 설계서 미갱신 |
| Phase 7 LLM 대화형 필터 | **B** | `llm_peer_filter.py` + `LLMPeerFilterView` 완전. **FE UI 없음, Thesis 연동 없음, 테스트 0건** |
| Phase 7 Thesis 연동(peer_preset_key 등 3필드) | **C** | 코드베이스 grep 0건. 가설 빌더·관제실 Peer 탭 미구현 |

**프론트엔드**
| 기능 | 분류 | 근거 |
|---|---|---|
| FE-PR-2 타입+hooks+API | **A** | `types/validation.ts`, `hooks/useValidation.ts`, `services/validation.ts` |
| FE-PR-3 SignalSummaryCard + PeerContextBar | **A** | + 프리셋 탭 + 커스텀 입력(`PeerContextBar.tsx:33-78`) |
| FE-PR-4 MetricCard + MetricBarChart | **A** | + `MetricInfoTooltip.tsx` |
| FE-PR-5/6 CategorySection/Sidebar/IndustryPosition/Leader | **A** | 전부 존재 |
| FE Phase 7 LLM 필터 UI | **C** | `llm-filter` 호출 코드 0건 |

### 실제 인벤토리
- **모델**(`services/validation/models/`): `CompanyMetricLatest`, `CompanyBenchmarkDelta`(+preset_key), `CategorySignal`(+preset_key), `ValidationNewsSummary`, `PeerPreset`, `UserPeerPreference` + 외부(`metrics`/`stocks` 앱)
- **API**(`api/urls.py`, 6개): `summary`, `metrics?category=`, `leader-comparison`, `presets`, `peer-preference`(POST/DELETE), `llm-filter`(POST)
- **서비스 9개**: benchmark_calculator, category_signal_calculator, custom_benchmark_engine, financial_fetcher, interpretation, llm_peer_filter, metric_calculator, preset_generator, relative_metrics
- **태스크 8개**: fetch_annual_financials(가용성), calculate_derived_metrics, calculate_benchmarks, calculate_relative_metrics, calculate_category_signals, update_peer_list_caches(**no-op**), log_batch_run, run_weekly_validation_batch. **참고: preset_generator를 호출하는 태스크가 chain에 없음**(프리셋 생성 수동/외부 추정)
- **테스트**: `services/validation/tests.py` 빈 파일. 실제는 `tests/unit/validation/` 11파일. **custom_benchmark_engine·llm_peer_filter 직접 테스트 0건**

### task_done Cross-Reference
| 보고서 주장 | 결과 |
|---|---|
| peer_phase6 `_generate_thematic()` 추가 | **코드 일치 / 설계서(Gemini)와 불일치** |
| peer_phase6 "463/503 종목, 2,282 프리셋" | **검증 불가**(런타임 DB 수치) |
| peer_phase7 `llm_peer_filter.py`+`LLMPeerFilterView` | **일치** |
| peer_phase7 지원 필터 9종 | **부분 불일치** — `rd_to_revenue`는 프롬프트에만 있고 execute 핸들러 없음(8종 구현) |
| peer_phase7 "전체 완료" | **불일치(과대)** — Step 7-5 Thesis 연동 미구현 |

### 주요 갭 및 리스크 (Top 5)
1. **[높] 주간 배치 미실행 위험(버그 #28 재발)** — DatabaseScheduler인데 dict만 등록, PeriodicTask DB 등록 없음. 스케줄도 설계(일 2시)와 다른 토 5시.
2. **[높] Phase 7 Thesis 연동 전무** — `peer_preset_key/peer_filter_query/peer_filter_result` 0건. task_done은 "전체 완료" 보고했으나 7-5 누락.
3. **[중] FE LLM 대화형 필터 UI 미구현** — 백엔드 `POST /llm-filter/`만 존재, 사용자 접근 경로 없음.
4. **[중] Phase 5/6/7 핵심 로직 테스트 공백** — custom_benchmark_engine, llm_peer_filter 단위 테스트 0건(LLM JSON 파싱·Redis·percentile 미검증).
5. **[중] thematic 설계-구현 의미 불일치(미반영 대체)** — 설계서 미갱신 + `rd_to_revenue` half-wired.

> 부수(저위험): Task1 가용성 확인으로 축소, Task5 no-op, Custom 엔진 summary만 지원.

---

## News 상세

### 한 줄 요약
구현률 **~92%**. News Intelligence Pipeline v3(6 Phase) + 콜드스타트 AI 브리핑(Phase A/B) + 키워드 상세 bottomsheet 백엔드 + **파이프라인 모니터링 Phase A/B/C 전체(AlertLog·check_pipeline_alerts 포함)**가 백엔드에 모두 구현. 갭은 대부분 경미: AlphaVantage provider 폐기(D), `_log_collection` provider 분리 미세 불일치, deep-analysis 토큰추적 미반영.

### 기능별 분류

| 기능 | 분류 | 근거 / 빠진 것 |
|------|------|----------------|
| Phase 1 규칙엔진(Engine A/B/C, importance_score, percentile) | **A** | `news_classifier.py`, `keyword_sector_map.py`(16섹터); `migrations/0004:127-194` |
| Phase 2 LLM 심층분석(Gemini Tier A/B/C) | **A** | `news_deep_analyzer.py:1-277`; task `analyze_news_deep` `tasks.py:555` |
| Phase 2 ML Label 수집(+24h, confidence) | **A** | `ml_label_collector.py`; `migrations/0004:151-179` |
| Phase 3 Neo4j 통합(NewsEvent, 4관계, TTL, ripple, cleanup) | **A** | `news_neo4j_sync.py:1-1001`; API `news_events`(`views.py:1068`)/`impact-map`(`:1131`) |
| Phase 4 ML 학습 + Shadow Mode(LR, TS-CV, Safety Gate) | **A** | `ml_weight_optimizer.py:1-1401`; `train_importance_model:733`, `generate_shadow_report:769` |
| Phase 5 Production Mode(auto deploy, rollback, 주간리포트) | **A** | `ml_production_manager.py:1-592`; `check_auto_deploy:836`, `monitor_ml_performance:903` |
| Phase 6 LightGBM(확장 feature, A/B, readiness) | **A** | `ml_weight_optimizer.py`; `train_lightgbm_model:941`; API `ml_lightgbm_readiness:1314` |
| 멀티 프로바이더(Finnhub/FMP/Marketaux) | **A** | `providers/{finnhub,fmp,marketaux}.py`, `base.py`; `aggregator.py:28-48`; `migrations/0005` |
| 멀티 프로바이더 — Alpha Vantage | **D** | choice/`alphavantage_id` 필드 잔존(`models.py:34,71`)하나 **provider 소스 없음**(pyc만), 수집 태스크 부재 |
| 키워드 추출(search_terms_en + reason 확장) | **A(초과)** | `keyword_extractor.py:252/268/283-285/338-347`; **article_ids 직접 매핑** 추가(`:154-162`, 설계 외 정확도 개선) |
| 키워드 상세 bottomsheet — 백엔드 API | **A(초과)** | `views.py:677 keyword-detail`(date+index, 캐시키 updated_at epoch, Gemini 요약, article_ids 1차 + search_terms_en fallback) |
| 키워드 bottomsheet v2(가로 Strip, max-w-2xl) | **N/A(FE 전용)** | 백엔드 전제 충족(keywords 배열 전환 지원) |
| AI 뉴스 브리핑 콜드스타트(MarketFeedService) | **A** | `market_feed.py:1-202`; API `market_feed:960`(AllowAny) 3단 fallback |
| 개인화 피드(4단 캐스케이드) | **A** | `personalized_feed.py:21-152`(portfolio→watchlist→interests→market_feed) |
| 관심사 옵션(8테마) | **A** | `interest_options.py:14/72`; API `interest_options:1004` |
| UserInterest 모델 + CRUD | **A** | `packages/shared/users/models.py`, `users/views.py` |
| 종목 인사이트(팩트 중심) | **A** | `stock_insights.py:1-837`; API `insights:857` |
| 모니터링 Phase A(collection-logs, pipeline-health, ml-trend, llm-usage) | **A** | `views.py:1411/1537/1911/2002` — KST cutoff, force_refresh, IsAdminUser |
| 모니터링 Phase 0(`_log_collection` 커버리지) | **B** | 6개 태스크 로깅 추가(`tasks.py:179,230,487,543,591,674`). **빠진것**: provider별 분리 대신 합산 라벨 `"finnhub_marketaux"` → 분해 정밀도 저하 |
| 모니터링 Phase B(task-timeline, neo4j-status, ml-rollback-preview/rollback) | **A** | `views.py:2134/2202/2276/2325`, rollback `confirm:true` 게이팅(`:2336`), IsAdminUser |
| 모니터링 Phase C(AlertLog + alerts API + check_pipeline_alerts) | **A** | `models.py:553-595`(7 TriggerType+4 Severity), API `alerts:2378`/`alerts_resolve:2453`, task `check_pipeline_alerts:1179`(7트리거), Beat `celery.py:428-429` |
| LLM 토큰 추적 — deep_analysis(Phase 3) | **C(설계도 유보)** | `llm-usage`는 키워드추출 토큰만 집계, deep_analysis는 건수만(`coverage_warning`). 설계가 "Phase B 보강" 약속했으나 미반영 |

### 실제 인벤토리
- **모델**(`services/news/models.py`): `NewsArticle:20`(importance/rule/LLM/ML 필드, 4 provider id), `NewsEntity:163`, `DailyNewsKeyword:302`, `MLModelHistory:386`, `NewsCollectionCategory:468`, `NewsCollectionLog:532`, `AlertLog:553` (+ `UserInterest`는 `packages/shared/users/models.py`)
- **API**(`/api/v1/news/`): 공개 `all`/`sources`/`stock/{symbol}`/`trending`/`daily-keywords`(+generate)/`keyword-detail`/`insights`/`market-feed`/`interest-options`/`personalized-feed`/`news-events`(+impact-map)/`ml-status`/`ml-shadow-report`/`ml-weekly-report`/`ml-lightgbm-readiness`; **관리자(IsAdminUser)** `collection-logs`/`pipeline-health`/`ml-trend`/`llm-usage`/`task-timeline`/`neo4j-status`/`ml-rollback-preview`/`ml-rollback`/`alerts`/`alerts/{id}/resolve`
- **서비스 17개**: aggregator, circuit_breaker, deduplicator, interest_options, keyword_extractor, keyword_sector_map, market_feed, ml_label_collector, ml_production_manager, ml_weight_optimizer, news_classifier, news_deep_analyzer, news_neo4j_sync, personalized_feed, sentiment_normalizer, stock_insights, stock_recommender
- **프로바이더**: base, finnhub, fmp, marketaux (활성 4) / `alphavantage.py` **소스 부재**(pyc만)
- **태스크(주요)**: extract_daily_news_keywords, collect_daily/market/category_news, aggregate_daily_sentiment, classify_news_batch, analyze_news_deep, collect_ml_labels, sync_news_to_neo4j, cleanup_expired_news_relationships, train_importance_model, generate_shadow_report, check_auto_deploy, generate_weekly_ml_report, monitor_ml_performance, train_lightgbm_model, collect_sp500_news_fmp_*, **check_pipeline_alerts**
- **마이그레이션**: 0001 initial / 0002 daily_news_keyword / 0003 collection_category / 0004 v3 pipeline / 0005 multi_provider / 0006 alertlog

### 설계 문서별 반영 여부
| 설계 문서 | 반영 |
|----------|------|
| `docs/news_intelligence_plan/*`(phase1~6, FINAL_SUMMARY) | **완전 반영** — AV provider만 폐기 |
| `docs/news/plan/news_keyword_detail_plan.md` | **완전 반영(초과)** — keyword-detail + search_terms_en + article_ids |
| `docs/news/plan/keyword_detail_bottomsheet_v2.md` | **FE 전용** — 백엔드 전제 충족 |
| `docs/news/plan/news_pipeline_monitoring_design.md`(Phase 0/A/B/C) | **백엔드 완전 반영** — 잔여: deep-analysis 토큰추적, provider별 분리 로깅 |
| `docs/features/news/AI_NEWS_BRIEFING_COLD_START_DESIGN.md`(Phase A/B) | **완전 반영** — Phase C(UserBehaviorSignal)는 설계상 별도 이슈 유보 |
| `docs/features/news/NEWS-INFRASTRUCTURE-SETUP.md` | **완전 반영** — GraphQL(optional)만 미도입 |

### 주요 갭 및 리스크 (Top 5)
1. **[중] AlphaVantage provider 폐기 vs 모니터링 설계 불일치** — 모니터링 설계는 AV를 4번째 provider 통계로 가정하나 소스/태스크 제거됨(`models.py:34,71`에 흔적만). `collection-logs.by_provider`에 미출현 → 설계 mock과 어긋남.
2. **[중] `_log_collection` provider 합산 라벨** — `"finnhub_marketaux"` 단일 라벨(`tasks.py:179,230,487`). 설계 §11의 provider별 분리 미준수 → pipeline-health 분해 정확도 저하.
3. **[중] Phase 3 LLM 토큰 미추적** — `llm-usage`가 deep_analysis(LLM 비용 대부분) 건수만 노출 → 비용 가시성 사각.
4. **[낮] 콜드스타트 Phase C(행동 기반) 미구현** — UserBehaviorSignal/PersonalizationEngine 없음(설계상 별도 이슈로 의도된 유보).
5. **[낮] 모니터링 외 데이터 API 보안 일관성** — 신규 모니터링 10개는 IsAdminUser 적용 확인. 단 `ml-status`/`daily-keywords`/`market-feed`/`news-events` 등은 AllowAny 혼재 → ML 버전/배포 상태가 비관리자에 노출 여지(설계 위반 아님, 점검 가치).

> 코드는 일절 수정하지 않음(읽기 전용 감사).

---

## 공통 권고 (Action Items)

| # | 우선순위 | 항목 | 근거 |
|---|---------|------|------|
| 1 | 높음 | **Beat drift 일괄 점검** — SEC 3개 + Validation 1개가 DatabaseScheduler 환경에서 실제 실행 여부 검증, PeriodicTask DB 등록 (버그 #28) | SEC #1, Validation #1 |
| 2 | 높음 | **SEC `check_new_filings` rate-limit 가드** — S&P500 순차 폴링이 SEC 10req/s 위반 가능, 배치 활성 전 throttle 필수 | SEC #1 |
| 3 | 중간 | **Validation Thesis 연동(7-5) 완료 또는 로드맵 명시** — task_done "전체 완료" 표현 정정 | Validation #2 |
| 4 | 중간 | **설계 문서 갱신** — Validation thematic(Gemini→DNA 조합), News AlphaVantage 폐기를 설계서에 반영(문서-코드 괴리 해소) | Validation #5, News #1 |
| 5 | 중간 | **테스트 공백 보강** — Validation custom_benchmark_engine·llm_peer_filter(LLM 파싱/Redis), SEC merger DQS | Validation #4 |
| 6 | 낮음 | **최상위 stale `__pycache__` 정리** — `sec_pipeline/`, `validation/`, `news/` 빈 디렉토리의 pyc 잔존 제거 | 선행 발견 |
| 7 | 낮음 | **백엔드-only API 노출 경로** — SEC DQS/BM 서비스, News deep-analysis 토큰추적 등 소비 경로 연결 | SEC #5, News #3 |
