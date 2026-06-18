# SEC Pipeline + Validation + News 설계 갭 감사

> **감사 일자**: 2026-06-18 (nightly)
> **대상 브랜치**: `monorepo/nightly-20260618`
> **방식**: 읽기 전용 — 설계서/완료보고서 vs 실제 코드 직접 대조 (코드 수정 없음)
> **분류**: (A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체
> **선행 감사**: `docs/nightly_auto_system/reports/6월/16일/remaining_design_gap_audit.md` (SEC Pipeline 부분) — 본 감사가 독립 재검증 + Validation/News 확장

---

## ⚠️ 감사 환경 메모 (중요)

사용자가 지정한 감사 대상 `/Users/byeongjinjeong/Desktop/stock_vis` 의 `sec_pipeline/`·`validation/`·`news/` 디렉토리에는 **소스 `.py` 파일이 존재하지 않는다** (`__pycache__/*.pyc` 캐시 잔재만 남음, git 미추적).

→ 실제 코드는 **monorepo 재편으로 `services/` 하위로 이동**했고, 진실의 소스는 nightly repo다:
- `services/sec_pipeline/` (30 .py 파일)
- `services/validation/` (모델 5 + 서비스 9 + api)
- `services/news/` (providers 4 + services 17 + api)

본 감사는 **nightly repo `services/` 코드 vs `docs/` 설계서** 기준으로 수행했다. Desktop 환경은 재편 이전 stale checkout으로 판단(감사 무의미).

---

## 앱별 요약 (구현률)

| 앱 | 설계 단위 | A | B | C | D | 구현률(A+의도D) | 핵심 리스크 |
|----|----------|---|---|---|---|-----------------|------------|
| **SEC Pipeline** | 17 PR + 결정 1 | 15 | 1 | 0 | 1 | ~94% | merger orphan(파이프라인 미연결), PR-17 문서 Beat 상태 stale |
| **Validation** | 12 구성요소 | 8 | 3 | 0 | 1 | ~75% | 지표 4개 영구 missing, API `confidence` 필드 의미 오류, 프리셋 배치 누락 |
| **News** | 16 기능 | 14 | 1 | 0 | 1 | ~94% | 사실상 전 설계 구현(일부 설계 초과 달성), deep-analysis 토큰 미집계(의도된 한계) |

**총평**: 세 앱 모두 "미구현(C)이 0건"으로, 설계서가 약속한 산출물은 대부분 코드로 실재한다. 갭의 성격은 **(1) 코드가 문서를 앞서간 미문서 산출물**, **(2) 계산 정밀도 타협(placeholder)**, **(3) API 응답 필드 의미 불일치**, **(4) orphan 코드(구현됐으나 파이프라인 미연결)** 의 4종에 집중된다. 즉 "안 만든 것"이 아니라 "연결/정밀도/문서 동기화" 문제다.

---

## SEC Pipeline 상세

**구현률**: A 15 / B 1 / C 0 / D 1 (전체 17 PR + 결정 001)

### PR/기능별 표

| PR/기능 | 설계 산출물 | 코드 위치 | 분류 | 근거 |
|---|---|---|---|---|
| PR-1 모델 | 8개 모델 | `services/sec_pipeline/models.py` | **A** | RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport 전부. `neo4j_dirty` 패턴 준수 |
| PR-2 수집기 | SECFilingCollector + validators | `collector.py:39`, `validators.py:21` | **A** | get_filing_metadata/_get_cik/fetch_filing_html/extract_sections/validate_extracted_sections 존재 |
| PR-3 Track A 추출 | normalizer+prompts+extractor+validator_a | `normalizer.py:63`, `prompts.py:11`, `extractor.py:35`, `validator_track_a.py` | **A** | Pass1 키워드 필터 + Gemini 2.5 Flash JSON + grade/저장 실재 |
| PR-4 Celery tasks | exceptions + collect/extract task + sp500 | `tasks.py:23,167`, `exceptions.py`, `sp500.py` | **A** | retry/backoff(메타3·HTML5·섹션1·LLM2), `_log_stage` FilingProcessLog |
| PR-5 Gold Set | schema+json+evaluate command | `fixtures/gold_set*.py`, `management/commands/evaluate_gold_set.py` | **A** | Precision/Recall 평가(_evaluate_sections/_evaluate_track_a) |
| PR-6 배치 실행 | (운영 작업) | — | **A** | PR-17 `run_batch_and_report`로 코드화 |
| PR-7 TickerMatcher | 3단계 매칭+큐 | `ticker_matcher.py:90` | **A** | _match_alias/_match_exact/_match_fuzzy(rapidfuzz)/match_with_queue |
| PR-8 Admin+signal | admin 8모델 + post_save signal | `admin.py`, `signals.py:22` | **A** | mark_not_public/mark_person/auto_resolve, on_unmatched_resolved |
| PR-9 Neo4j sync | sync_dirty_to_neo4j | `tasks.py:398` | **A** | 2-Phase + select_for_update(skip_locked), DELETE+CREATE, sole writer |
| **PR-10 merger** | merge_relationship + DQS + command | `merger.py:36,76`, `process_unmatched_queue.py` | **B** | 함수·DQS·테스트는 존재하나 **파이프라인(tasks/signals) 어디서도 호출 안 됨 = orphan**. command만 wired |
| PR-11~13 Track B | keywords_b+prompts_b+extractor_b+validator_b+service | `keywords_track_b.py:109`, `extractor.py:97`, `validator_track_b.py`, `packages/shared/metrics/services/business_model_service.py` | **A** | Track B 추출 실본체(스텁 아님). for_api 게이트 작동 |
| PR-14 대시보드 | quality_checks(7) + view + template + url | `quality_checks.py`, `views.py:11`, `templates/admin/sec_pipeline/dashboard.html` | **A** | 7체크 + staff_member_required + config/urls include |
| PR-15 on-demand | on_demand + FilingDataView + check_new_filings | `on_demand.py:18`, `views.py:36`, `tasks.py:544` | **A** | 1년/1시간 중복방지, GET 200/202. **추가**: `IsAdminUser` 권한(문서 외) |
| PR-16 intelligence | DataCollector + Reporter + admin | `intelligence.py:63,148`, `admin.py:159` | **A** | 5차원 수집 + Gemini + trend, severity_badge/regenerate |
| PR-17 e2e | generate_intelligence_report + run_batch_and_report | `tasks.py:580,589` | **A** | 3-Phase 순차. 단위테스트 `tests/unit/sec_pipeline/`(24파일/386 funcs) |
| 결정 001 | FMP→SEC EDGAR 메타데이터 | `collector.py`, `decisions/001` | **D** | 정상 대체. 잔존: stage명 `"fmp_metadata"`, 예외 `FMPApiError` 레거시 명명 |

### 주요 갭

**[B] PR-10 merger — orphan (구현됐으나 미연결)**
`merger.py:36 merge_relationship`, `:76 calculate_edge_dqs` 는 RELATIONSHIP_SPECIFICITY 점수표·bounded boosting·DQS 계산까지 완성됐으나, repo 전체에서 이 함수를 호출하는 곳은 **자기 자신 + 테스트 + 문서뿐**. `tasks.py`/`signals.py`/commands 어디에도 import 없음. → 동일 (source,target,type) 관계 병합·DQS 산출이 실 데이터 흐름에서 일어나지 않음. evidence는 개별 저장만. 추가로 PR-10이 "API 노출"로 표기한 `source_count`/`source_types`를 반환하는 REST 엔드포인트도 없음(`urls.py`엔 dashboard+filing 2개뿐).

**[문서 stale] PR-17 Beat 스케줄 — 문서와 현실 반대**
`sec_pr_17_e2e.md`는 Beat를 "(주석 상태)"로 보고하고 `tasks.py:638-646`도 주석 블록만 있으나, **실제 운영 스케줄은 `config/celery.py`에 활성 등록**:
- `sec-sync-dirty-neo4j` (`*/5분`, neo4j 큐)
- `sec-check-new-filings` (매월1일 06:00)
- `sec-seed-relations-to-chainsight` (매일 12:00)
→ 문서의 "비활성" 표기가 운영 현실과 반대. **문서 수정 필요(운영 영향 O)**.

**[D 잔여] 결정 001 — RSS 미전환**
결정 001은 `check_new_filings`도 SEC EDGAR RSS로 대체하라 명시했으나, 실제는 SEC EDGAR **submissions 폴링**(매월 S&P500 전 종목 `get_filing_metadata` 순회). SEC로 통일은 됐으나 RSS 효율성과는 다른 방식 → rate limit 부하 측면 잔여 과제.

### 설계서에 없는 추가 구현
1. **`seed_relations_to_chainsight` task** (`tasks.py:338`) — SupplyChainEvidence → chain_sight `RelationConfidence` 시드. 17 PR 문서 어디에도 없으나 Beat 활성(매일 12:00). CUSTOMER_OF→SUPPLIES_TO 방향 반전 등 통합 로직 포함. **SEC↔Chain Sight 연결 핵심 산출물인데 미문서**.
2. **management commands 3종**: `rematch_unmatched.py`, `reprocess_unmatched_queue.py`, `seed_company_aliases.py` — 요약서 "향후 과제(CompanyAlias 수동 등록/매칭률 개선)"를 코드화. task_done 미기재.
3. **FilingDataView `IsAdminUser` 권한** — 외부 SEC fetch 비용 방지(audit P0 #6). 설계보다 보수적.

---

## Validation 상세

**구현률**: A 8 / B 3 / C 0 / D 1 (주요 구성요소 12개)

### 구성요소/Phase별 표

| 구성요소 | 설계 명세 | 코드 위치 | 분류 | 근거 |
|---|---|---|---|---|
| Peer 프리셋 6종 | default/sector_all/size_peers/quality_top/lifecycle/thematic | `services/preset_generator.py` | **A** | 6개 _generate_* 메서드 전부. task_done 2,282 프리셋 생성 확인 |
| Compute-on-Read | 커스텀 peer DB 미저장 + numpy + Redis TTL 1h | `services/custom_benchmark_engine.py` | **A** | 벌크 1쿼리 + in-memory percentile + `cache.set(ck, r, 3600)` |
| **지표 계산 (34개)** | §4 7카테고리 34지표 | `services/metric_calculator.py` | **B** | 30개 정상, **4개 결손**: sbc_to_revenue·buyback_offsets_sbc=missing(SBC 필드 부재), cash_from_ops_trend=placeholder("Phase2"). ev_to_ebitda=market_cap/ebitda(순부채 미반영) |
| 벤치마크 델타 | percentile_rank/rank/basis/confidence | `services/benchmark_calculator.py`, `models/benchmark_delta.py` | **A** | peer median/p25/p75 + higher_is_better 반영. basis 3단 fallback(industry_size→industry→sector) |
| 카테고리 시그널 | percentile 평균→green/yellow/red/gray | `services/category_signal_calculator.py`, `models/category_score.py` | **A** | score≥65 green 등 임계 일치, SPECIAL_GRAY_CATEGORIES |
| LLM Peer 필터 (Phase7) | 자연어→JSON→실행, Gemini sync | `services/llm_peer_filter.py`, `api/views.py LLMPeerFilterView` | **A** | genai.Client 동기, thinking_budget=0, Chain Sight/metric/exclude 필터 |
| 커스텀 Peer | mode=custom→Compute-on-Read | `models/peer_preset.py UserPeerPreference`, `api/views.py PeerPreferenceView` | **A** | POST/DELETE + summary 분기 |
| 해석 레이어 | summary/metric/leader 텍스트 | `services/interpretation.py` | **A** | §3.1/3.3/3.5 의사코드와 거의 1:1 |
| **Thematic (Phase6)** | 설계: Gemini theme_tags 태깅 | `preset_generator.py _generate_thematic:425` | **D** | LLM 태깅 대신 chainsight `GrowthStage × CapitalDNA` 교집합으로 **대체**(task_done 명시). 설계의 LLM 파이프라인은 코드에 없음 |
| **REST API** | summary/metrics/leader-comparison(+3) | `api/urls.py`, `api/views.py` | **B** | 6개 전부 존재하나 **summary `peer_info.confidence`에 benchmark_basis 값 주입**(views.py L131). 설계는 high/medium/low → FE 신뢰도 badge 오작동 |
| **배치 파이프라인** | chain(Task 1→6) | `tasks.py run_weekly_validation_batch` | **B** | 6 Task chain + Beat DB 등록 작동(NT-11-1 last_run 6/6). 단 **PresetGenerator가 chain에 미포함** → 프리셋 주간 자동 갱신 안 됨(수동 의존). Task1은 수집 아닌 "가용성 확인"으로 축소 |
| 데이터 모델 | category_signal/value_status/basis/handling_mode | `models/`, migration 0001~0004 | **A** | CategorySignal/benchmark_basis/UserPeerPreference/PeerPreset 존재 |

### 주요 갭

**[B] 지표 34개 중 4개 결손** (`metric_calculator.py`)
- `sbc_to_revenue`·`buyback_offsets_sbc`: 항상 `(None,"missing","SBC 필드 미제공")` — §4.6 희석/주주가치 핵심 2지표 영구 missing → 카테고리 valid count 4→2로 신뢰도 하락.
- `cash_from_ops_trend`(설계명 `ocf_trend_3y`): `_calc_ocf_trend_placeholder()` = missing("Phase2"). **다년 데이터가 fetcher에 있는데도 placeholder**.
- 지표 코드명 ↔ 설계명 불일치: `ocf_trend_3y`→`cash_from_ops_trend`, `shareholder_yield`→`net_shareholder_yield` 등(코드 내부는 일관, 설계서와만 다름).

**[B] API summary `confidence` 필드 의미 오류** (`api/views.py` L128-137)
```python
"confidence": peer_cache.benchmark_basis,   # high/medium/low가 아니라 'industry_size' 등이 들어감
"benchmark_basis": peer_cache.benchmark_basis,
```
`PeerListCache`에 confidence 컬럼이 없어 basis로 대체. BenchmarkCalculator는 `_determine_confidence`로 계산하지만 CompanyBenchmarkDelta에만 저장 → summary가 못 읽음. FE 신뢰도 badge(🟢/🟡/🔴) 설계대로 안 나옴. (leader-comparison도 응답 키가 PR 프롬프트와 달라 FE 계약 확인 필요.)

**[B] 배치 — 프리셋 생성이 주간 chain에 없음** (`tasks.py`)
chain은 fetch→derived→benchmark→relative→signals→peercache→log 7단계. `PresetGenerator.generate_for_symbols` 호출 Task 없음 → sector_all/quality_top/lifecycle/thematic 프리셋이 주간 자동 재계산 안 됨. thematic은 chainsight DNA 변동 시 stale 위험.

**[D] Thematic 방식 대체**: 설계의 Gemini 사업모델 태깅 → `CompanyNarrativeTag.theme_tags` 안 대신, LLM 없이 GrowthStage×CapitalDNA 교집합 클러스터로 대체(task_done 명시 = 미구현 아님).

### 설계서에 없는 추가 구현
1. **`ValidationNewsSummary` 모델** (`models/news_summary.py`): event_count_30d/sentiment_trend/has_regulatory_risk 등 뉴스 연계 캐시. 설계서에 없고 **어떤 task/view에서도 채워지거나 소비 안 됨 = 데드 모델**.
2. **`CategorySignal.contributing_metrics`(JSON)**: 디버깅/투명성용 추가 필드(설계 §7.6에 없음).
3. **`preset_key` 필드(CategorySignal/CompanyBenchmarkDelta)**: Peer v2 멀티프리셋 지원. 단 **API/계산기는 항상 default로만 처리** → 프리셋별 시그널 분기는 모델만 준비, read 경로 미연결(부분 구현).

---

## News 상세

**구현률**: A 14 / B 1 / C 0 / D 1 (주요 기능 16개) — **세 앱 중 최고, 일부 설계 초과 달성**

### 설계서/기능별 표

| 설계서/기능 | 설계 명세 | 코드 위치 | 분류 | 근거 |
|---|---|---|---|---|
| keyword_detail_plan v2 | `GET /news/keyword-detail/`, 2단 매칭, Gemini 요약, analysis=null fallback | `api/views.py:676 keyword_detail`, `:812 _generate_keyword_analysis` | **A** | 엔드포인트·매칭·Gemini(thinking_budget=0)·`cache_key=...:{updated_epoch}`·analysis=null 일치. 초과: `article_ids` 직접조회 추가 |
| keyword_extractor search_terms_en | search_terms_en + reason 필드 | `services/keyword_extractor.py:283,338,347` | **A** | 프롬프트·파싱·FALLBACK 전부 포함 |
| bottomsheet_v2 (FE) | KeywordDetailSheet props, 가로 Strip, scrollIntoView, max-w-2xl | `frontend/components/news/KeywordDetailSheet.tsx`, `thesis/common/BottomSheet.tsx:38` | **A** | initialIndex/keywords·activeIndex·scrollIntoView·max-w-2xl mx-auto |
| Cold Start Phase A | reason, MarketFeedService, `GET /news/market-feed/`(AllowAny), 3단 fallback | `services/market_feed.py:23 get_feed`, `views.py:954` | **A** | is_fallback/fallback_message·3단 fallback·related_symbols 매칭·_get_market_context |
| AINewsBriefingCard 통합 | 미인증→Card, 인증→Banner | `frontend/app/news/page.tsx:201,215` | **A** | `!user ? Card : Banner` 조건부 렌더 |
| Cold Start Phase B | UserInterest, InterestOptions(8테마), PersonalizedFeed(4단), 온보딩 | `packages/shared/users/models.py UserInterest`, `services/interest_options.py`, `personalized_feed.py:24` | **A** | 8테마·4단 캐스케이드(portfolio→watchlist→interest→MarketFeed)·FE InterestSelector/OnboardingBanner |
| Infra Setup | docker neo4j, init cypher, settings, providers | `docker/docker-compose.yml:46`, `scripts/init-neo4j.cypher`, `config/settings.py`, `services/news/providers/` | **A** | neo4j 서비스·NEWS_RATE_LIMITS·finnhub/fmp/marketaux 전부 |
| Infra: GraphQL API(선택) | 그래프용 GraphQL "고려" | — | **D** | 미채택. REST `@action`(news-events/impact-map)로 대체 = 정상 폐기 |
| Monitoring Phase A | collection-logs/pipeline-health/ml-trend/llm-usage API(IsAdminUser) | `views.py:1411,1537,1911,2002` | **A** | 4 API + IsAdminUser 전부 |
| Monitoring Phase A FE | service+hook+6컴포넌트+SubTab | `frontend/services/newsPipelineService.ts`, `hooks/useNewsPipeline.ts`, `components/admin/news/`(12개) | **A** | PipelineStatusBar/MLTrendChart/LLMUsageSummary 등 |
| Monitoring Phase B | task-timeline/neo4j-status/ml-rollback(2단계) | `views.py:2128,2196,2270,2319` | **A** | 4 API + FE TaskTimelineChart/Neo4jStatusCard/MLCompareView. **설계가 미래작업으로 미룬 것 완료** |
| Monitoring Phase C | AlertLog 모델, alerts API, admin, check_pipeline_alerts Beat | `models.py:553`, `views.py:2372,2447`, `admin.py:206`, `tasks.py:1179`, `config/celery.py:428` | **A** | 모델·7 TriggerType·API·admin·Beat 전부. **@infra 담당 미룬 Beat까지 완료** |
| **llm-usage deep-analysis 토큰** | Phase3 토큰 미추적, coverage_warning | `views.py:2002 llm_usage` | **B** | **설계서 §3.4가 명시한 의도된 한계**. 키워드 토큰만 집계, deep-analysis는 건수만. 잔여=NewsDeepAnalyzer 토큰 로깅 추가 |
| Pipeline v3 규칙엔진 | NewsClassifier A/B/C | `services/news_classifier.py` | **A** | classify_news_batch 연동 |
| Pipeline v3 LLM분석 | NewsDeepAnalyzer Tier A/B/C | `services/news_deep_analyzer.py` | **A** | analyze_news_deep 태스크 |
| Pipeline v3 ML/Shadow/Prod | MLWeightOptimizer(LightGBM/SafetyGate), MLProductionManager, MLLabelCollector | `ml_weight_optimizer.py`/`ml_production_manager.py`/`ml_label_collector.py` | **A** | 3서비스 + ml-status/shadow/weekly/lightgbm API(views.py:1175~) |
| Pipeline v3 Neo4j | NewsNeo4jSyncService, Sector Ripple | `news_neo4j_sync.py:25,69`, `views.py:1067,1130` | **A** | is_available·뉴스이벤트/impact-map API |
| Infra CircuitBreaker/Aggregator | 장애격리 + 멀티프로바이더 집계 | `circuit_breaker.py:14`, `aggregator.py:28`, `tasks.py:992,1085,1131` | **A** | is_open/record_failure + finnhub/marketaux/fmp 집계 + dedup |

### 주요 갭

**[B] llm-usage deep-analysis 토큰 미집계** (`api/views.py:2002`)
설계서 `news_pipeline_monitoring_design.md` §3.4가 **명시적으로 선언한 한계** — "NewsDeepAnalyzer(Phase3)의 LLM 호출은 토큰을 저장하지 않는다. 키워드 추출 비용만 반영." 응답 `coverage_warning` + FE 경고 배너로 노출하도록 설계됨. **설계 위반이 아니라 설계대로 구현된 의도된 부분 구현**. 잔여 갭 = NewsDeepAnalyzer 토큰 로깅 추가뿐.

**[D] GraphQL API** — 인프라 설계서가 "선택/고려"로 제안. REST `@action`(news-events/impact-map)으로 대체. GraphQL 의존성/스키마 코드 없음 = 정상 폐기.

**[C] 미구현: 없음.** 감사 5개 설계서 핵심 명세 전부 코드에 존재.

### 설계서에 없는 추가 구현 (설계 초과 달성)
1. **keyword_detail `article_ids` 직접조회 경로**(`views.py:740`): 설계의 2단 매칭은 레거시 fallback으로 강등, article_ids 우선 경로 신규.
2. **Monitoring Phase B/C 완전 구현**: 설계가 "미래작업/@infra 외주"로 표기했으나 감사 시점 **전부 완료**(`config/celery.py:428 check-pipeline-alerts` Beat 등록 포함).
3. **CircuitBreaker task 통합**(`tasks.py:992,1085,1131`): 인프라 설계서는 rate-limit만 언급했으나 프로바이더별 `CircuitBreaker("fmp")` + is_open 스킵 3곳 구현.
4. **FE 컴포넌트 다수**(`components/news/` 24개): NewsEventTimeline/SentimentChart/NewsDetailModal 등 v3 시각화 추가.

---

## 종합 권고 (우선순위)

| 우선 | 앱 | 항목 | 권고 액션 | 영향 |
|------|----|----|-----------|------|
| 🔴 P1 | Validation | API `confidence` 필드 오류(views.py L131) | basis가 아닌 실제 confidence(high/med/low) 반환하도록 수정 — PeerListCache에 confidence 컬럼 추가 or BenchmarkDelta에서 읽기 | FE 신뢰도 badge 오작동 (사용자 노출) |
| 🔴 P1 | SEC | PR-17 Beat 문서 stale | `sec_pr_17_e2e.md`의 "주석 상태" 표기를 "활성(celery.py 등록)"으로 정정 | 운영 오해 방지 |
| 🟡 P2 | SEC | PR-10 merger orphan | merge_relationship/DQS를 extract 파이프라인(tasks.py)에 wire, 또는 "미연결" 명시 | 관계 병합/DQS 미작동 |
| 🟡 P2 | Validation | 프리셋 생성 배치 누락 | run_weekly_validation_batch chain에 PresetGenerator Task 추가(특히 thematic stale 방지) | 프리셋 staleness |
| 🟡 P2 | Validation | preset_key read 경로 미연결 | 멀티프리셋 시그널 분기를 API에 노출하거나 모델 필드 보류 명시 | 모델만 준비된 미사용 스키마 |
| 🟢 P3 | Validation | 지표 4개 결손 | SBC 데이터 소스 확보 후 sbc_to_revenue/buyback_offsets_sbc 구현, cash_from_ops_trend placeholder 해제 | 카테고리 신뢰도 |
| 🟢 P3 | Validation | ValidationNewsSummary 데드 모델 | 채우는 task 연결 or 제거 | 미사용 스키마 정리 |
| 🟢 P3 | News | deep-analysis 토큰 로깅 | NewsDeepAnalyzer에 토큰 집계 추가 → llm-usage 완전성 | 비용 가시성 |
| 🟢 P3 | SEC | 미문서 산출물 3종(seed_relations_to_chainsight 등) | task_done에 문서화 | 추적성 |

> **핵심 결론**: 세 앱 모두 "미구현(C) 0건". 실질 부채는 ① 문서-코드 동기화(SEC Beat, 미문서 task), ② API 응답 계약 정합(Validation confidence), ③ orphan/미연결 코드(merger, preset_key, ValidationNewsSummary) 에 집중. 신규 기능 구현보다 **연결·정정·문서화 작업**이 잔여 과제의 대부분이다.
