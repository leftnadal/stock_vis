# SEC Pipeline + Validation + News 설계 갭 감사

> 작성: 2026-06-08 야간 자동 감사 (읽기 전용, 코드 무수정)
> 범위: `docs/sec_pipeline/` vs `services/sec_pipeline/`, `docs/first_validation_system/` vs `services/validation/`, `docs/news/` vs `services/news/`
> 방법: 설계 문서 + task_done 완료 보고서 cross-reference, 실제 구현 코드 직접 확인

---

## ⚠️ 감사 전제 — monorepo 재구성으로 인한 경로 이동

이 감사의 가장 중요한 발견은 **세 앱 모두 루트 경로에서 사라졌다는 점**이다. 코드는 폐기된 것이 아니라 "서비스 리모델링(데이터 구조 개편, PR8a 트랙)" 과정에서 **monorepo 구조로 이동**했다.

| 설계서가 가리키는 경로 (구) | 실제 구현 위치 (현) | 루트 잔재 |
|---|---|---|
| `sec_pipeline/` | **`services/sec_pipeline/`** (`INSTALLED_APPS: services.sec_pipeline`, PR8a-1 이동) | `.pyc`만 남은 stale 디렉토리 |
| `validation/` | **`services/validation/`** (`INSTALLED_APPS: services.validation`, PR8a-1 이동) | `.pyc`만 남은 stale 디렉토리 |
| `news/` | **`services/news/`** (`INSTALLED_APPS: services.news`, PR8a-2 이동) | 루트 디렉토리 자체 없음 |

추가로 일부 모델/서비스는 `packages/shared/` (metrics, stocks, users)와 `apps/` (chain_sight, market_pulse, portfolio)로 분산되었다. **모든 task_done 완료 보고서의 파일 경로 표기는 이동 전(stale) 경로**이므로, 보고서를 그대로 신뢰하면 "파일이 없다"는 오판이 발생한다.

---

## 앱별 요약 (구현률)

| 앱 | 설계 항목 수 | (A) 완전 | (B) 부분 | (C) 미구현 | (D) 폐기/대체 | 종합 구현률 |
|---|---|---|---|---|---|---|
| **SEC Pipeline** | 17 PR + 7원칙 | 14 (82%) | 3 (18%) | **0** | 1 (FMP→EDGAR, 정당) | **높음** — 기능 미구현 0, 갭은 전부 "배선/단순화" 수준 |
| **Validation** | 32 항목 | 21 (66%) | 7 (22%) | **3 (9%)** | 1 (Phase 6 방식 변경, 정당) | **중간** — 핵심 파이프라인 완성, **Peer 프리셋 확장 트랙 배선 끊김** |
| **News** | 38 항목 | 33 (87%) | 3 (8%) | **0** | 2 (deprecated 잔존) | **매우 높음** — 4개 설계서 거의 1:1 대응, 미구현 0 |

**한 줄 결론**:
- **SEC Pipeline** — 모든 PR 산출물 실재. 갭은 chord 미사용(순차로 단순화), merger dead code, FMP 폐기(정당), fuzzy 임계값 80 vs 85, Gold Set 라벨 미완.
- **Validation** — ⚠️ **유일하게 실질적 미구현(C) 보유 앱**. Peer 프리셋 6종 "생성 로직"은 완성했으나 **배치·조회·Thesis 연동이 전부 끊겨** 프리셋을 바꿔도 화면 데이터가 default로 고정됨.
- **News** — CLAUDE.md "Pipeline v3 (테스트 607개)" 주장 사실 부합. 갭은 설계가 스스로 명시한 한계 3건 + deprecated 코드 미정리 2건뿐.

---

## SEC Pipeline 상세

**실구현**: `services/sec_pipeline/` (32개 .py) + 서비스 레이어 `packages/shared/metrics/services/business_model_service.py`. URL: `config/urls.py:45` → `api/v1/sec-pipeline/`. 결정 문서: `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md`.

### 구현률
| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 14 PR | 82% |
| (B) 부분/설계차이 | 3 PR (PR-5, 7, 9, 10, 15, 17) | 18% |
| (C) 미구현 | 0 | 0% |
| (D) 폐기/대체 | 1 (FMP 메타데이터/RSS → SEC EDGAR, decision 001) | — |

### PR별 분류표
| 설계 항목 | 분류 | 구현 위치 | 근거/비고 |
|---|---|---|---|
| PR-1 모델 8개 + migration | **A** | `models.py:15-431`, `migrations/0001_initial.py` | 8개 모델 전부. `neo4j_dirty` 플래그, `unique_together`, `source_sectors` JSONField 설계대로 |
| PR-2 수집기+섹션추출+사후검증 | **A**(D요소) | `collector.py`, `validators.py` | 3단계 추출 + `validate_extracted_sections` 3체크 + FAIL/WARN prefix. **메타데이터 소스 FMP→SEC EDGAR 대체** |
| PR-3 Track A 추출 | **A** | `normalizer.py`, `prompts.py`, `extractor.py:35`, `validator_track_a.py` | Gemini-2.5-flash temp 0.1, 자기참조/0.3/grade 검증. `GENERIC_COMPANY_TERMS` 보강 |
| PR-4 Celery tasks + 에러핸들링 | **A** | `exceptions.py`, `tasks.py:22,166`, `sp500.py` | 4개 예외, collect/extract 분리, retry 정책. Beat는 주석(`tasks.py:638-646`) |
| PR-5 Gold Set + 평가 | **B** | `fixtures/gold_set.json`, `gold_set_schema.py`, `commands/evaluate_gold_set.py` | 설계는 "AAPL만 완전 라벨"인데 실제는 AAPL 빈 라벨 + MSFT/NVDA/GOOGL 완전 라벨로 역전. **Track B(business_model) 라벨 전 종목 누락** → Track B 평가 무의미 |
| PR-6 S&P500 배치 실행 | **A**(실행) | task_done 기록 (14/15 수집) | 코드 PR 아닌 실행 PR |
| PR-7 TickerMatcher | **B** | `ticker_matcher.py` | 3단계 매칭 구현. **fuzzy 임계값 설계 ≥85% vs 실제 default 80** (`:234`). 설계外 `BLOCKED_NAMES` 추가 |
| PR-8 Admin 큐 + signal | **A** | `admin.py:100`, `signals.py:21`, `apps.py:9` | list_editable, auto_resolve≥0.90, post_save signal(같은 sector만, dirty flag만) |
| PR-9 sync_dirty_to_neo4j | **B** | `tasks.py:397` | 2-Phase + `select_for_update(skip_locked)`, DELETE+CREATE 멱등. **lock 후 atomic 종료** (설계는 atomic 내 lock). `_to_grade`(`:534`) 정의됐으나 미사용 |
| PR-10 merger + 큐처리 | **B** | `merger.py`, `commands/process_unmatched_queue.py` | 로직은 설계대로(내부/사용자 키 분리). **`merge_relationship`/`calculate_edge_dqs` 프로덕션 호출처 0건 = dead code.** SEC→Chain Sight 연계는 설계外 `seed_relations_to_chainsight`(`tasks.py:338`)가 담당 |
| PR-11 Track B 키워드 사전 | **A** | `keywords_track_b.py` | `BM_KEYWORDS` 5필드, 역방향 표현 포함 |
| PR-12 Track B 추출 | **A** | `prompts.py:46`, `extractor.py:97`, `validator_track_b.py`, `tasks.py:272-333` | Track A 실패해도 Track B 시도. overall=5필드 평균 |
| PR-13 서비스 레이어 | **A** | `packages/shared/metrics/services/business_model_service.py` | `for_api=True`→confidence 제거. **경로만 모노레포 이동(task_done은 stale 표기)** |
| PR-14 Admin 대시보드 + quality_checks | **A** | `admin.py:158`, `quality_checks.py`, `views.py:15`, `templates/admin/sec_pipeline/dashboard.html` | 7체크 + 누적 통계 + 템플릿 전부 |
| PR-15 On-demand + 신규감지 | **B** | `on_demand.py`, `views.py:29`, `tasks.py:543` | 1년/1시간 중복방지, 200/202. **설계 `check_new_filings_via_fmp()`(FMP RSS) → `check_new_filings()`(SEC submissions polling) 대체.** FilingDataView `IsAdminUser` 강화 |
| PR-16 Pipeline Intelligence | **A** | `intelligence.py`, `admin.py:158` | 5차원 수집 + Gemini 리포트 + severity/health 액션 |
| PR-17 Celery chord + E2E | **B** | `tasks.py:588,579` | **PR 제목 "chord 통합"인데 chord/chain 미사용, 순차 동기 호출.** task_done이 "chord 대신 순차(1인 개발 단순성)"로 자인. settings.py Beat 설정 부재 |

### 주요 갭 상세
1. **PR-17 chord→순차 (B)** — `run_batch_and_report`(`tasks.py:588`)가 `chord`/`chain`/`.si()` 전무, 단일 동기 함수. 보고서가 솔직히 정정 기록해 은폐는 아니나 PR 제목/설계 의도와 불일치. settings.py Celery Beat도 부재(tasks.py 주석으로만).
2. **PR-10 merger dead code (B)** — 병합 로직은 설계대로지만 호출처 0건. 파이프라인에 미연결.
3. **FMP 메타데이터/RSS 폐기 (D)** — decision 001로 SEC EDGAR 전면 대체(정당, 문서화됨). 단 `exceptions.py:19 FMPApiError`는 클래스만 남은 잔재.
4. **PR-7 fuzzy 80 vs 85 (B)** — docstring "≥85%" vs 실제 default 80. 5pt 느슨해 오매칭 위험 소폭 증가.
5. **PR-5 Gold Set 라벨 (B)** — Track B 라벨 전 종목 누락, AAPL/MSFT 라벨 역전. Precision/Recall 재평가는 향후 과제로 자인.

### task_done 보고서 vs 실제 코드 불일치
| 보고서 주장 | 실제 | 판정 |
|---|---|---|
| `sec_pr_17_e2e.md` "Celery chord 통합" | chord/chain 없음, 순차 | **자인 불일치** (본문서 정정) |
| 서비스 레이어 = `metrics/services/...` | `packages/shared/metrics/services/...` | **경로 stale** (기능 동등) |
| `sec_pr_10_merger.md` "구현 완료" | 구현됐으나 호출처 0건 | **부분 불일치** (구현 O, 사용 X) |
| decision 001/FMP 메타데이터 | collector는 SEC EDGAR만, FMPApiError 잔재 | **설계서↔코드 불일치(정당화됨)** |

---

## Validation 상세

**실구현**: `services/validation/` (모델 5 + 서비스 9 + api) + 공유 모델 `packages/shared/metrics/`. URL: `config/urls.py:43` → `api/v1/validation/`. Beat: `config/celery.py:773` (토 05:00).

### 구현률
| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 21 | 66% |
| (B) 부분 구현 | 7 | 22% |
| (C) 미구현 | **3** | **9%** |
| (D) 폐기/대체 | 1 | 3% |

### 상세 분류표 (핵심 발췌)
| 설계 항목 | 분류 | 구현 위치 | 근거/비고 |
|---|---|---|---|
| 모델 9종 (MetricDefinition~BatchJobRun) | A | `packages/shared/metrics/models/*`, `services/validation/models/*` | `not_applicable_reason`, `value_status`(5단계), `preset_key`, `handling_mode` 전부. 테이블명 prefix 차이만 존재 |
| seed_validation_data (34지표+special) | A | `services/validation/management/commands/seed_validation_data.py` | |
| Task 1 fetch_annual_financials | **B** | `services/validation/services/financial_fetcher.py` | **가용성 체크만.** 설계의 FMP income/balance/cashflow/key-metrics 수집 + snapshot 원값 저장 안 함. missing 종목 자동수집 트리거 주석으로만 |
| Task 2 calculate_derived_metrics | A | `metric_calculator.py` (501줄) | 지표 계산 + value_status |
| Task 3 Peer 선정 + Benchmark | A | `benchmark_calculator.py` | industry_size→industry→sector fallback, percentile/rank/confidence |
| Task 3.5 relative_metrics | A | `relative_metrics.py` | |
| Task 4 category_signals (gray) | A | `category_signal_calculator.py` | special→gray, normal만 포함 |
| Task 5/6 + 오케스트레이터 + Beat | A | `tasks.py`, `config/celery.py:773` | chain(1→2→3→3.5→4→5→6), 토 05:00. Task 5는 no-op |
| API summary/metrics/leader-comparison | A | `api/views.py:63,223,404` | 설계 구조 부합 |
| rule-based 해석 3종 | A | `interpretation.py` | summary/metric/leader |
| Peer 프리셋 6종 생성 로직 | A | `preset_generator.py` | default/sector_all/size_peers/quality_top/lifecycle/thematic |
| **프리셋 배치 파이프라인 연동** | **C** | (없음) | `PresetGenerator`가 task/command/beat 어디서도 호출 안 됨. 주간 batch chain 미포함. 셸 수동 실행만 |
| **Batch preset-aware 계산** | **C** | benchmark/category calc | `preset_key` 사용 0건. delta/signal 항상 `default`로만 저장. 설계 §4/§6 행렬과 불일치 |
| **API 프리셋별 데이터 분기** | **B** | `views.py` summary/metrics | summary는 custom만 분기, **preset 선택 시 preset_key 필터 안 함** → 프리셋 전환해도 default 반환 |
| presets 목록 / peer-preference | A | `views.py:531,572` | |
| Compute-on-Read 커스텀 엔진 | A | `custom_benchmark_engine.py` | numpy in-memory + Redis 캐시(TTL 1h) |
| Phase 6 thematic | **D** | `preset_generator.py:_generate_thematic` | **Gemini theme_tags 태깅 폐기 → GrowthStage×CapitalDNA 조합 대체** (보고서 일치, 정당) |
| Phase 7 LLM 대화형 필터 | A | `llm_peer_filter.py`, `views.py:622` | Gemini sync 파싱 (버그#8 준수) |
| **Phase 7 Thesis Control 연동** | **C** | (없음) | `Thesis.peer_preset_key`/`peer_filter_query`/`peer_filter_result` 미구현. 관제실 Peer 비교 탭 없음 |

### 주요 갭 (C/D) 상세 — ⚠️ Peer 프리셋 트랙 "배선 끊김"
- **GAP-1 (C, 최우선)** — `PresetGenerator.generate_for_symbols()` 호출처 전무. 주간 batch에 프리셋 생성 단계 없음. 셸 수동 실행 의존 → PeerPreset 테이블 stale 위험. (보고서의 "2,282개 프리셋"은 일회성 수동 실행 추정)
- **GAP-2 (C)** — 전체 batch가 preset-aware 아님. `BenchmarkCalculator`/`CategorySignalCalculator`가 항상 default peer로 1세트만 계산. `preset_key` 컬럼은 있으나 항상 `'default'`만 적재. 설계 §4(프리셋별 ~357,000건 배치)와 불일치.
- **GAP-3 (B+C 결합)** — 프리셋 전환이 화면에 반영 안 됨. summary/metrics view가 UserPeerPreference의 preset_key로 delta/signal 필터 안 함. GAP-2와 결합돼 프리셋을 바꿔도 데이터가 default와 동일.
- **GAP-4 (C)** — Phase 7 Thesis Control 연동 부재. `Thesis` 모델 필드 미추가, 빌더 Step 3/관제실 연동 없음. LLM 필터 자체는 동작하나 Thesis 저장 고리 끊김.
- **GAP-5 (D, 정상)** — Phase 6 thematic Gemini 방식 → GrowthStage×CapitalDNA 대체. 보고서·코드 일치, 의도적 변경(LLM 비용/품질 회피). 단 설계서 본문 미갱신.
- **GAP-6 (B)** — Task 1이 FMP 수집 안 함. snapshot 적재가 stocks 앱 별도 경로에 암묵 의존.

### contracts/validation-api.yaml 계약 vs 구현 불일치
1. summary `peer_info.industry` 필드 yaml 누락 (구현 `views.py:130`은 반환).
2. **⚠️ confidence 의미 왜곡 (코드 결함)** — `views.py:131` `"confidence": peer_cache.benchmark_basis`로 채워 confidence 자리에 `industry_size` 같은 basis 값이 들어감. yaml example도 이 버그를 박제. confidence는 high/medium/low여야 함.
3. leader-comparison / metrics / llm-filter / presets 응답 스키마 yaml 미정의 (실제는 풍부한 중첩 구조 반환).

### task_done 보고서 vs 실제
- Phase 6/7 보고서 산출물(`_generate_thematic`, `llm_peer_filter.py`, `LLMPeerFilterView`, `llm-filter/` URL) **전부 코드 실재 확인 ✅** (경로만 stale).
- **보고서가 숨긴 갭**: 두 보고서 모두 "전체 완료" 종결했으나 (a) 프리셋 생성기 배치 미연동, (b) preset_key 조회 미구현, (c) Thesis 연동 미구현을 언급 안 함. **프리셋 시스템은 "생성 로직 완성, 운영 연결 미완" 상태로 종결 처리됨.**

---

## News 상세

**실구현**: `services/news/` (모델+태스크+views+providers 4+services 18+api). URL: `config/urls.py` → `api/v1/news/`. Beat: `config/celery.py:251~496`(평일) + `386~422`(일요일 ML). 설계서 4종: 브리핑 콜드스타트 / 키워드 상세 v2 / 모니터링 대시보드 / Pipeline v3 6-Phase.

### 구현률
| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 33 | 87% |
| (B) 부분 구현 | 3 | 8% |
| (C) 미구현 | **0** | 0% |
| (D) 폐기/대체 | 2 | 5% |

### 기능별 분류표 (핵심 발췌)
| 설계 항목 | 분류 | 구현 위치 | 근거/비고 |
|---|---|---|---|
| 팩트 기반 인사이트 / 수집 카테고리 3타입 | A | `stock_insights.py`, `models.py:468 resolve_symbols()`, `api/views.py:856` | 3타입 분기 전부 |
| 카테고리 우선순위 Beat / collect_category_news | A | `config/celery.py:301~335`, `tasks.py:351` | high(2회)/med/low |
| Engine A/B/C (종목매칭/16섹터/5-factor) | A | `news_classifier.py:5,24,95`, `keyword_sector_map.py` | select_for_analysis 상위 15% |
| NewsArticle v3 필드 | A | `models.py:103~135` | importance_score, rule_sectors/tickers, llm_*, ml_* 전부 |
| LLM 심층 분석 (Gemini Tier A/B/C) | A | `news_deep_analyzer.py`, `tasks.py:555` | |
| ML Label 수집 (+24h 변동폭) | A | `ml_label_collector.py`, `tasks.py:603` | |
| Neo4j 동기화 (NewsEvent+4관계+TTL) | A | `news_neo4j_sync.py:48~51` | DIRECTLY 30/INDIRECTLY 21/CREATES_OPPORTUNITY 14/AFFECTS_SECTOR 21일 (설계 정확 일치) |
| Sector Ripple 2-hop | A | `news_neo4j_sync.py:295` | 20캡 + 0.4 감쇠 |
| MLModelHistory + ML Optimizer(LR+TS-CV+Safety Gate+Smoothing) | A | `models.py:386`, `ml_weight_optimizer.py`, `tasks.py:733` | |
| Shadow Mode / ML Production(auto deploy/rollback) | A | `tasks.py:769`, `ml_production_manager.py` (8 메서드) | |
| Engine C 배포 가중치 자동 적용 | A | `news_classifier.py:152 _load_deployed_weights()` | 폴백 내장 |
| LightGBM (extended/A-B/readiness) | A | `ml_weight_optimizer.py:843~1263`, `tasks.py:941` | 6 메서드 전부 |
| 일요일 ML Beat 6개 / 평일 파이프라인 Beat | A | `config/celery.py:386~422`, `251~496` | train/shadow/deploy/weekly/monitor/lightgbm |
| Pipeline v3 API 6종 | A | `api/views.py:1067~1333` | news-events~lightgbm-readiness |
| AI 브리핑 reason / MarketFeedService / 3단계 Fallback | A | `keyword_extractor.py:48`, `market_feed.py`, `api/views.py:960,584` | is_fallback 플래그 |
| 키워드 상세 v2 (search_terms_en + article_ids 2단 매칭) | A | `keyword_extractor.py:154~162`, `api/views.py:676,733` | Gemini 투자요약 + 캐시 |
| UserInterest / InterestOptions(8테마) / PersonalizedFeed(4단 캐스케이드) | A | `packages/shared/users/models.py:274`, `interest_options.py`, `personalized_feed.py:24` | portfolio>watchlist>interests>market_feed |
| 모니터링 API 전체 (collection-logs/pipeline-health/ml-trend/llm-usage/task-timeline/neo4j-status/ml-rollback) | A | `api/views.py:1411~2325` | 6 Phase + 주말면제 + 2단계 confirm |
| AlertLog + alerts API + check_pipeline_alerts 7트리거 | A | `models.py:553`, `api/views.py:2378`, `tasks.py:1179`, `admin.py:206` | Beat `celery.py:429` |
| 프론트엔드 12종 (브리핑/상세시트/온보딩/ML카드/타임라인/모니터링) | A | `frontend/components/news/*`, `frontend/components/admin/news/*` | 전부 존재 |
| `_log_collection()` 커버리지 보강 | A | `tasks.py:179,230,487,543,591,674` | 설계 지목 6개 누락 태스크 try/finally 삽입 완료 |
| recommendations API | **D** | `api/views.py:1337` (Legacy/Deprecated) | insights/로 대체, NewsBasedStockRecommender 잔존 |
| 구 추천 프론트 컴포넌트 | **D** | `frontend/components/news/` | StockInsightCard/NewsHighlightedStocks 신규 + 구 RecommendationCard/StockRecommendations 병존(미삭제) |

### 부분 구현 (B) — 설계가 스스로 명시한 한계
1. **LLM Usage 토큰 추적 미포함** (`api/views.py:2116`) — 설계 §3.4가 "NewsDeepAnalyzer 토큰 미저장, Phase B 추가" 명시. 키워드 추출 토큰만 집계 + `coverage_warning` 노출. **설계 의도대로의 부분이며 누락 아님.**
2. **Neo4j pending_sync 추정** (`api/views.py:2241`) — 전용 `neo4j_synced` 필드 없어 `llm_analyzed AND updated_at>last_sync`로 근사. 주석에 명시.
3. **Phase 5 ML 학습 last_run 추정** (`api/views.py:1811`) — ML 태스크가 NewsCollectionLog 미기록 → `error_rate=0.0` 하드코딩 + `MLModelHistory.trained_at` 대용.

### 폐기/대체 (D)
1. **recommendations API** — 점수 기반 "추천"→팩트 기반 "인사이트" 전환이 핵심 원칙. view + 서비스가 삭제 안 되고 "Legacy/Deprecated"로 잔존. 동작은 하나 설계 방향과 배치.
2. **구 추천 프론트 컴포넌트 병존** — `RecommendationCard.tsx`/`StockRecommendations.tsx` 미제거.

### services/news/ vs apps/market_pulse/ — **중복 아님, 별개 서브시스템**
| 측면 | `services/news/` (Pipeline v3) | `apps/market_pulse/` (Market Pulse v2) |
|---|---|---|
| 모델 | `NewsArticle` (news_articles, UUID PK) | `MarketPulseNews` (6 TextChoices) |
| 카테고리 | general/company/press_release/forex/crypto/merger | MACRO/GEOPOLITICS/SECTOR/INDEX/MAG7/SMART_MONEY |
| 분류기 | Engine A/B/C (importance_score, ML) | 6-카테고리 keyword/regex |
| 용도 | 종목 인사이트 + ML 파이프라인 + 키워드 | 이상신호↔뉴스 페어링 |

같은 `news_classifier.py` 파일명이지만 로직 완전 상이. 서로 import 안 함. URL hash dedup만 양쪽 독립 구현(코드 중복 O, 충돌 X). `apps/chain_sight/models/news_event.py:ChainNewsEvent`도 제3의 별개 모델.

### 설계 주장 vs 실제 불일치 (코드는 정합, 요약 문서가 구버전)
1. **테스트 "607개"** — 실측 `tests/news/` 600 + `tests/unit/news/` 124 + serverless 26 = 충분히 초과. **과장 아님.** (FINAL_SUMMARY 587 vs sub_claude_md 607 문서 간 ±20 차이는 있으나 실측이 더 큼)
2. FINAL_SUMMARY "POTENTIALLY 14일" vs 실제 `CREATES_OPPORTUNITY` 14일 — **코드 정합, FINAL_SUMMARY 구버전.**
3. ml_production_manager 테스트 수 FINAL_SUMMARY 56 vs 실제 68 — sub_claude_md/실측 일치.
4. interest_options 테마 ID `fintech` → `fintech_payment` — 기능 동일, ID 문자열만.
5. 모니터링 설계 "파이프라인 로직 변경 금지" 준수 — 변경 흔적 없음, `_log_collection()` 호출만 추가.

---

## 종합 권고 (우선순위)

읽기 전용 감사이므로 코드 수정은 하지 않았다. 후속 작업 우선순위만 제시한다.

1. **[Validation, 최우선] Peer 프리셋 배선 복구** — GAP-1(프리셋 생성기 batch 연동) → GAP-2/3(preset-aware 계산·조회) → GAP-4(Thesis 연동). 현재 "프리셋을 바꿔도 화면이 default 고정"은 사용자 체감 결함. 세 앱 통틀어 유일한 실질 미구현(C) 군집.
2. **[Validation] contracts confidence 버그 (`views.py:131`)** — confidence 자리에 benchmark_basis가 들어가는 코드 결함. yaml에도 박제됨. 코드 측 수정 필요.
3. **[SEC] PR-10 merger dead code / PR-17 chord 부재** — 기능 영향은 낮으나 설계-구현 의도 불일치. merger를 파이프라인에 연결하거나 명시적으로 제거 결정 필요.
4. **[SEC] fuzzy 임계값 80 vs 85** — docstring과 코드 정합화 (오매칭 위험 관리).
5. **[News] deprecated 잔존 정리** — recommendations API + 구 프론트 컴포넌트 제거 (기능 무영향, 코드 위생).
6. **[전체] 설계서 본문 + task_done 경로 갱신** — 모든 보고서가 monorepo 이동 전 경로(stale)를 표기. SEC FMP 폐기·Validation Phase 6 방식 변경 등 정당한 D 결정이 설계서 본문에 미반영.

### 분류 D(폐기/대체) 정리 — 모두 정당, 문서 갱신만 필요
- SEC: FMP 메타데이터/RSS → SEC EDGAR (decision 001 문서화 O)
- Validation: Phase 6 thematic Gemini 태깅 → GrowthStage×CapitalDNA (보고서 일치)
- News: recommendations → insights (원칙 전환, 단 구 코드 미제거)
