# SEC Pipeline + Validation + News 설계 갭 감사

> 감사일: 2026-06-05 · 범위: 읽기 전용 (코드 수정 없음)
> 방법: `docs/*` 설계 문서 + `task_done/` 완료 보고서 ↔ `services/*` 실제 구현 1:1 대조
> 분류 기준: **(A)** 완전 구현 · **(B)** 부분 구현/미연결 · **(C)** 미구현 · **(D)** 폐기/대체

> ⚠️ 구현 위치 주의: 세 앱 모두 PR8a 리팩토링으로 `services/` 하위로 이동했다.
> 루트 `sec_pipeline/`·`validation/` 디렉토리는 `__pycache__` + 빈 `management/`·`migrations/`만 남은 **죽은 스텁**이며 실제 소스가 없다.
> 실제 앱: `services.sec_pipeline` / `services.validation` / `services.news` (`config/settings.py:196,203,205` 등록, `config/urls.py:38,43,45` 라우팅).

---

## 앱별 요약 (구현률)

| 앱 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 실효 구현률 | 한 줄 평 |
|----|:---:|:---:|:---:|:---:|:---:|----|
| **SEC Pipeline** | 16 | 2 | 0 | 1 | **~94%** | 설계 전건 구현. 갭은 "문서가 코드보다 뒤처짐" 방향. 실질 코드 결함은 fuzzy threshold 1건 |
| **Validation** | 11 | 5 | 2 | 1 | **~78% (운영 실효 더 낮음)** | 백엔드 로직 충실하나 **프리셋 배치 미연결 + Beat DB 미등록 + 지표 3개 stub** 등 구조적 단절 다수 |
| **News** | 13 | 2 | 0 | 2 | **~76%** | "plan만 있고 미구현"으로 의심한 3개가 전부 완성됨. 갭은 코드가 아니라 **stale 문서 헤더** |

**종합 결론**
- **미구현(C)은 News 0 / SEC 0 / Validation 2건뿐.** 세 앱 모두 "설계는 했는데 코드가 없다"는 큰 갭은 거의 없다.
- 진짜 리스크는 두 종류로 갈린다:
  1. **문서 정합성 갭** (SEC·News): 코드가 문서를 앞질러서 문서가 stale. → 중복 구현/혼동 유발.
  2. **운영 연결 갭** (Validation): 코드는 있으나 배치/Beat/데이터 파이프라인에 미연결되어 **실제로 안 돌아가는** dead path.
- 가장 시급한 단일 리스크: **Validation 프리셋 생성기 배치 미연결** + **Beat DatabaseScheduler 미등록(버그 #28)** — task_done은 "완료"를 주장하나 운영 자동화가 끊겨 있다.

---

## SEC Pipeline 상세

설계 문서 17개 PR 보고서(`docs/sec_pipeline/task_done/`) + `sec_pipeline_complete_summary.md` ↔ `services/sec_pipeline/` 대조.

### 구현률 요약

| 분류 | 개수 |
|------|:---:|
| (A) 완전 구현 | 16 |
| (B) 부분/불일치 | 2 |
| (C) 미구현 | 0 |
| (D) 폐기/대체 | 1 (의도된 의사결정) |

→ **설계 스펙 사실상 전건 구현·연결.** 오히려 설계 문서에 없는 post-design 확장(블록리스트, chainsight seeding, 추가 command 3종)이 다수 추가됨. 갭의 방향이 "코드 < 문서"가 아니라 "코드 > 문서".

### PR/기능별 상세

| PR/기능 | 설계 주장 (task_done) | 실제 구현 증거 | 분류 | 비고 |
|---------|----------------------|----------------|:---:|------|
| PR-1 모델 8개 + migration | 8 모델, neo4j_dirty only, unique_together | `models.py` 8 클래스 전부, `migrations/0001_initial.py` 단일 파일, 제약 일치(`models.py:112,215,331`) | A | |
| PR-2 SEC EDGAR 수집+검증 | collector + 3단 추출 + 순서/heading/길이 검증 + edgartools fallback | `collector.py`, `validators.py:21 validate_extracted_sections`, `:89 _check_item_order` | A | |
| PR-3 Track A 키워드+Gemini | normalizer/prompts/extractor/validator_track_a | 4파일 전부. `extractor.py:35 extract_supply_chain`(gemini-2.5-flash, temp 0.1) | A | |
| PR-4 Celery tasks + 예외 | exceptions(4) + collect_and_extract + extract_from_document + sp500 | `tasks.py:23,167`, `exceptions.py`, `sp500.py` | A | |
| PR-5 Gold Set + 평가 | schema + gold_set.json(10종목) + evaluate command | `fixtures/gold_set.json`, `fixtures/gold_set_schema.py`, `management/commands/evaluate_gold_set.py` | A | |
| PR-6 Phase 1 배치 | 15종목 배치 (운영 실행 보고) | 재현 로직 `run_batch_and_report`. 보고서 성격 | A | 코드 산출물 아님 |
| **PR-7 TickerMatcher 3단계** | alias→exact→fuzzy **≥85%**, 큐 적재 | `ticker_matcher.py:112 match`, `:146 match_with_queue` — 단 **`_match_fuzzy(threshold=80)`** | **B** | ⚠️ **핵심 갭**: 도크스트링·보고서는 85%인데 실제 운영 임계값 **80** |
| PR-8 Admin + signal | 8 모델 Admin + UnmatchedQueueAdmin + post_save signal | `admin.py` 8× `@admin.register`, `signals.py:21 on_unmatched_resolved` | A | |
| PR-9 sync_dirty_to_neo4j | 2-Phase + DELETE+CREATE + sole writer | `tasks.py:397 sync_dirty_to_neo4j`, `select_for_update(skip_locked)` | A | |
| PR-10 merger + 큐 command | merge_relationship + calculate_edge_dqs + process_unmatched_queue | `merger.py:36,76`, `management/commands/process_unmatched_queue.py` | A | |
| PR-11~13 Track B + 서비스 | keywords_track_b + Track B extractor + validator + business_model_service(for_api 게이트) | `keywords_track_b.py`, `extractor.py:97 extract_business_model`, `validator_track_b.py`, `packages/shared/metrics/services/business_model_service.py:16,50` | **B** | 경로만 모노레포 prefix(`packages/shared/`)로 이동 — 기능 동등, 문서 경로 stale |
| PR-14 대시보드 + quality_checks | 7체크 + 대시보드 view + dashboard.html | `quality_checks.py:17`, `views.py:16`, `templates/admin/sec_pipeline/dashboard.html` | A | |
| PR-15 on-demand + check_new_filings | on_demand(1년/1시간) + FilingDataView(200/202) + check_new_filings | `on_demand.py:18`, `views.py:29 FilingDataView`(202@:50), `tasks.py:544` | A | View 권한 `IsAdminUser`로 강화(audit P0 #6) |
| PR-16 Intelligence | PipelineDataCollector 5차원 + Reporter + Admin | `intelligence.py:63,148`, `admin.py:159 PipelineIntelligenceReportAdmin` | A | |
| PR-17 E2E chord | generate_intelligence_report + run_batch_and_report + beat(주석) | `tasks.py:580,588`. **단 beat는 주석 아니라 DB 활성** | A | 문서가 현실보다 보수적 |
| 의사결정 001 FMP→SEC EDGAR | FMP Starter 404 → SEC EDGAR 대체 | `collector.py` SEC EDGAR submissions API, `decisions/001_*.md` | **D** | 의도된 대체 |

### 핵심 갭/리스크 (SEC)

1. **(B) Fuzzy threshold 불일치 — 설계 ≥85% vs 코드 80%** (실질 코드 갭 유일)
   - `ticker_matcher.py:234 _match_fuzzy(self, name, threshold=80)`. `match()`가 기본값 호출 → 운영 임계값 **80** 적용.
   - 영향: 설계보다 5%p 느슨 → false positive 소폭 증가. **도크스트링/보고서 수정 or 코드 85 복원 택1 필요.**
2. **(정보) PR-17 "Beat 주석 상태" 주장이 현실과 불일치 — 실제 활성**
   - `config/celery.py:783-802`에 3태스크(`sec-sync-dirty-neo4j` 5분 / `sec-seed-relations-to-chainsight` 12:00 / `sec-check-new-filings` 매월1일) 정의 + **DB PeriodicTask 3건 전부 등록 확인**. DatabaseScheduler가 진실 소스 → 실행 활성. (좋은 방향의 불일치)
3. **(정보) 설계에 없는 post-design 확장** (문서 갭, 코드 정상)
   - `tasks.py:338 seed_relations_to_chainsight`(SEC evidence → chainsight RelationConfidence), `ticker_matcher.py:26 BLOCKED_NAMES`(비상장/일반명사 차단), 추가 command 3종(`rematch_unmatched`/`reprocess_unmatched_queue`/`seed_company_aliases`). 어느 PR 보고서에도 무기재.
4. **(정보) 루트 `sec_pipeline/` 빈 스텁** — `.py` 소스 0건. import 경로상 무해하나 혼동 유발.

---

## Validation 상세

설계 문서(`validation_design.md`, `validation_peer_system.md`, `validation_peer_phase6_7.md`) + task_done 2건 ↔ `services/validation/` 대조.

### 구현률 요약

| 분류 | 개수 |
|------|:---:|
| (A) 완전 구현 | 11 |
| (B) 부분/미연결 | 5 |
| (C) 미구현 | 2 |
| (D) 폐기/대체 | 1 |

→ 백엔드 로직 기준 ~78%(A). 단 **프리셋 배치 미연결 + Beat DB 미등록** 두 구조적 단절로 **운영 실효 구현률은 더 낮다.**

### 기능/Phase별 상세

| 기능/Phase | 설계 주장 | 실제 구현 증거 | 분류 | 비고 |
|---|---|---|:---:|---|
| 종합 요약 (category_signal 신호등) | 7카테고리 percentile 균등평균 → green/yellow/red/gray | `category_signal_calculator.py:80-245`, `models/category_score.py:4-70` | A | 설계 §3.1 충실 |
| 한줄 요약 (rule-based) | green/red/gray 조합 템플릿 | `interpretation.py` + `views.py:120,187` | A | |
| Peer 정보 바 + 신뢰도 | industry+size fallback, confidence high/med/low | `benchmark_calculator.py:select_peers`, `views.py:122-137` | A | `peer_info.confidence`에 high/med/low 대신 `benchmark_basis` 문자열 주입(`views.py:131`) — 의미 경미 불일치 |
| 지표 카드 상세 (5년+peer band+해석) | history 5년 + p25/median/p75 + value_status | `views.py:276-401 _build_metric` | A | 설계 §3.3 응답 구조 일치 |
| value_status 판정 | normal/missing/not_applicable/unstable/low_confidence | `metric_calculator.py:311-431` | **B** | `low_confidence`는 배치 미생성 — 모델 choice에만 존재 |
| 34개 지표 계산 | 7카테고리 × 34지표 | `metric_calculator.py` 33 + `relative_metrics.py:51` = 34 | **B** | **3개 영구 stub**: `sbc_to_revenue`·`buyback_offsets_sbc`(`:241-242` "missing"), `cash_from_ops_trend`(`:408` "Phase 2") → 실효 31개 |
| 산업 위치/순위 | 핵심 지표 rank/total | `views.py:139-166` (5지표 rank) | A | |
| 리더 비교 (대장주 22지표) | market_cap 1위, 우위 카운트, 강·약점 | `views.py:404-528 LeaderComparisonView` | A | "22개" 고정 대신 전체 카테고리 순회 — 실질 동등 |
| 배치 파이프라인 Task 1~6 | chain(fetch→metrics→benchmarks→relative→signals→peer_cache→log) | `tasks.py:23-178` | A | 설계 §6.1 순서 정확 일치 |
| **Celery Beat 등록** | 일요일 새벽 주간 배치 | `config/celery.py:773-776 validation-weekly-batch` crontab | **B** | ⚠️ **`CELERY_BEAT_SCHEDULER=DatabaseScheduler`(settings.py:490) → dict 무시(버그 #28). `PeriodicTask` DB 등록 증거 없음** → 자동 실행 미보장 (런타임 DB 상태 미확인) |
| **Peer 프리셋 6종 생성** | default/sector_all/size_peers/quality_top/lifecycle/thematic | `preset_generator.py:26-545` 6개 `_generate_*` 전부 구현 | **B** | ⚠️ **배치(tasks.py)에 미연결 — `PresetGenerator` 호출처 0건(grep). 수동 실행만 가능** = dead 연결 |
| 프리셋 목록/선택 API | GET presets, POST/DELETE peer-preference | `api/urls.py:28-33`, `views.py:531-619` | A | 프론트 `validation.ts:46-65` authAxios 연동 |
| 커스텀 Peer (Compute-on-Read) | Redis 캐시 + numpy in-memory | `custom_benchmark_engine.py:30-174`, `views.py:88-103` | A | 설계 §1·§7 충실 |
| **Phase 6 Thematic (LLM 큐레이션)** | Gemini theme_tags 태깅 → 클러스터 | `preset_generator.py:425-524 _generate_thematic` | **D** | **Gemini 방식 폐기, GrowthStage×CapitalDNA 교차로 대체**(task_done 일치). LLM 호출 없음 — 설계 방식 전면 교체 |
| Phase 7 LLM 대화형 필터 | 자연어→Gemini 파싱→필터 API | `llm_peer_filter.py:56-276`, `views.py:622-693 LLMPeerFilterView`, `urls.py:34-38` | **B** | 백엔드 완비. **프론트 UI 미구현**(grep coach 스키마뿐) + foreign_revenue_pct/rd_to_revenue는 chainsight 0건 의존 → 시나리오 일부 0건 |
| **ValidationNewsSummary (뉴스 요약)** | 모델 정의 | `models/news_summary.py:4-50`, migration 0002 | **C** | **Writer 없음**(populating 서비스/태스크 0건). 읽기는 `stocks/serializers.py:271`뿐 — 사실상 빈 테이블 |
| **CompanyMetricLatest (최신값 캐시)** | API 캐시용 | `models/metric_latest.py:4-63` | **C** | API views가 snapshot 직접 조회로 우회 — 모델만 존재, 채우는 로직·소비처 미확인 |

### 핵심 갭/리스크 (Validation)

1. **🔴 프리셋 배치 미연결 (최대 리스크)** — `PresetGenerator` 6종 모두 구현됐으나 `tasks.py` 어디서도 호출 안 됨(`generate_for_symbol*` 호출처 grep 0건). 주간 배치가 프리셋을 갱신하지 않음. task_done의 "2,282개 생성"은 **수동 1회 산물**로 추정, S&P500 구성 변동 시 자동 갱신 안 됨.
2. **🔴 Celery Beat DB 미등록 (버그 #28 정확 해당)** — `validation-weekly-batch`가 config dict(`celery.py:773`)에만 존재. DatabaseScheduler 운영이므로 dict 무시 → **주간 배치 자동 실행 미보장**. `PeriodicTask.objects.create` 흔적 없음. (런타임 DB 상태 미확인 — 검증 필요)
3. **🟡 지표 3개 영구 stub** — `sbc_to_revenue`·`buyback_offsets_sbc`(희석/주주가치 4지표 중 2), `cash_from_ops_trend`(현금흐름 6지표 중 1)가 항상 "missing". 해당 카테고리 신호가 결손 지표로 계산 → **신호 신뢰도 저하**. "34개" 명목 충족이나 실효 31개.
4. **🟡 Phase 6 설계-구현 전면 교체(D)** — 설계서는 Gemini theme_tags 클러스터링, 실제는 GrowthStage×CapitalDNA 교차(LLM 없음). 설계서 미갱신.
5. **🟡 Phase 7 프론트 단절 + 데이터 결손** — `llm-filter` 백엔드 완비됐으나 프론트 호출 코드 없음(dead endpoint). foreign_revenue_pct/rd_to_revenue 필터는 chainsight 데이터 0건 의존(task_done 자인) → 5 시나리오 중 2개 무력.
6. **🟡 죽은 모델 2건(C)** — `ValidationNewsSummary`(writer 없음), `CompanyMetricLatest`(API에서 우회). 마이그레이션·admin·모델만 존재, 데이터 파이프라인 없음.
7. **경미** — `peer_info.confidence`에 benchmark_basis 문자열 주입(`views.py:131`), `value_status.low_confidence` choice 미생성.

---

## News 상세

설계 문서(`docs/news/plan/` 3건 + `docs/features/news/` 2건 + `sub_claude_md/news-insights.md`) ↔ `services/news/` + `frontend/` 대조.

### 구현률 요약

| 분류 | 개수 |
|------|:---:|
| (A) 완전 구현 | 13 |
| (B) 부분 구현 | 2 |
| (C) 미구현 | 0 |
| (D) 폐기/대체 | 2 |

→ **"plan만 있고 미구현"으로 의심한 3개(AI 브리핑 콜드스타트 / 키워드 상세 바텀시트 v2 / 파이프라인 모니터링)는 전부 구현 완료.** C=0. 문서 헤더("구현 대기")가 stale일 뿐 코드는 존재.

### 기능/설계문서별 상세

| 기능/문서 | 설계 주장 | 실제 구현 증거 | 분류 | 비고 |
|-----------|-----------|----------------|:---:|------|
| 키워드 상세 v2 (news_keyword_detail_plan) | `GET /news/keyword-detail/`, search_terms_en 매칭, Gemini 요약, 1h 캐시 | `api/views.py:676-810` 전체, `:732-737` 캐시키, `:812-852` Gemini | A | 설계 초과: `article_ids` 직접조회(`:740`) 우선, 2단 매칭은 레거시 fallback |
| └ search_terms_en 프롬프트 | keyword_extractor 확장 | `keyword_extractor.py:268,283-285,338` | A | reason 필드 동시 구현 |
| 바텀시트 v2 (keyword_detail_bottomsheet_v2) | 가로 Strip + initialIndex/keywords + scrollIntoView + max-w-2xl | `frontend/components/news/KeywordDetailSheet.tsx:15-16,59,73-84,125` | A | DailyKeywordCard 연동 `:157-162` |
| 파이프라인 모니터링 Phase A | collection-logs/pipeline-health/ml-trend/llm-usage API 4 + IsAdminUser | `views.py:1411,1537,1911,2002` + permission 확인 | A | NewsTab sub-tab + admin 컴포넌트 6개 |
| └ Phase 0 _log_collection | 6 누락 태스크 호출 추가 | `tasks.py:179,230,487,543,591,674` | A | 설계 §11 선행 완료 |
| 모니터링 Phase B | task-timeline/neo4j-status/ml-rollback-preview/ml-rollback | `views.py:2134,2202,2276,2325` | A | FE 컴포넌트 존재 |
| 모니터링 Phase C | AlertLog 모델 + alerts API + check_pipeline_alerts | `models.py:553-598`, `views.py:2378,2453`, `tasks.py:1179-1452`(7 트리거), `migrations/0006` | A | beat 등록 `celery.py:428-429`. 설계 "낮음"인데 완전 구현 |
| AI 브리핑 콜드스타트 Phase A | market-feed API + MarketFeedService + reason + 3단 fallback | `services/market_feed.py:23-201`, `views.py:960` | A | FE `frontend/app/news/page.tsx:8,217` |
| └ AINewsBriefingCard | importance 바 + reason + headlines | `frontend/components/news/AINewsBriefingCard.tsx` | A | |
| AI 브리핑 Phase B | UserInterest + interest-options + interests CRUD + PersonalizedFeed | `packages/shared/users/models.py:274`, `urls.py:84-88`, `interest_options.py`, `personalized_feed.py:21-95` | A | migration `0007`. FE InterestSelector/OnboardingBanner |
| News Intelligence Pipeline v3 | Classifier+DeepAnalyzer+MLLabel+Neo4jSync+WeightOptimizer+ProductionManager | `services/news/services/` 6 서비스 전부 | A | ml-status/shadow/weekly/lightgbm `views.py:1178,1212,1276,1311` |
| 멀티 프로바이더 수집 | Finnhub+Marketaux+FMP + dedup + circuit breaker | `providers/{finnhub,fmp,marketaux}.py`, `aggregator.py:16,22-53`, `circuit_breaker.py` | A | migration `0005` |
| News 인사이트(팩트 기반) | stock_insights + /insights/ API + FE | `services/stock_insights.py`, FE StockInsightCard 등 | A | |
| Neo4j 인프라 셋업 (NEWS-INFRASTRUCTURE-SETUP) | docker-compose neo4j + init cypher + settings + 검증 | `docker/docker-compose.yml:46-61`, `scripts/init-neo4j.cypher`, `settings.py:24,90,108,125` | A | 체크리스트 전부 충족 |
| └ 차기 파일 구조 제안 | `news/neo4j_client.py`, `API_request/finnhub_client.py`, GraphQL | 미생성. 대신 `news_neo4j_sync.py` + `providers/`로 대체 | **D** | "예상 구조"일 뿐 계약 아님 — 더 나은 구조로 대체 |
| └ NEWS_PRIMARY/FALLBACK_PROVIDER env | env 기반 우선순위 | aggregator 코드 직접 분기(`:78,88`), env 미사용 | **D** | env → 코드 하드코딩 대체 |
| LLM Usage 토큰 추적 완전성 | Phase 3(DeepAnalyzer) 토큰 → Phase B 통합 예정 | `views.py:2002` llm-usage는 키워드 추출 토큰만 집계 | **B** | 설계 §3.4 명시 한계. DeepAnalyzer 토큰 로깅 미통합 — 비용 가시성 갭 |
| GraphQL API | "고려" 수준 | 미구현 | **B** | 비확정 항목, REST로 커버 |

### 핵심 갭/리스크 (News)

1. **🟡 문서 헤더 stale (최대 리스크 — 문서 정합성)** — 3개 문서가 "구현 대기"/"설계 단계(구현 전)" 헤더를 달고 있으나 **전부 구현 완료**.
   - `news_keyword_detail_plan.md:4` "설계 확정 → 구현 대기"
   - `AI_NEWS_BRIEFING_COLD_START_DESIGN.md:3` "설계 완료, 구현 대기"
   - `news_pipeline_monitoring_design.md:6` "설계 단계 (구현 전)"
   - → 신규 작업자 **중복 구현 위험**. 헤더 "구현 완료"로 갱신 권장.
2. **🟡 LLM Usage Phase 3 토큰 미추적(B)** — `llm-usage`가 키워드 추출 토큰만 집계. DeepAnalyzer(LLM 비용 대부분)는 여전히 미로깅. 설계가 "Phase B 통합"으로 미룬 항목인데 통합 흔적 없음 → 비용 가시성 갭. (설계 §3.4가 한계 명시 → false alarm 아님)
3. **🟢 죽은 코드 없음** — 루트 `news/` 앱 미존재, `services.news`로 단일화. 인프라 doc 제안 경로(`news/neo4j_client.py` 등)는 미생성이나 `news_neo4j_sync.py`+`providers/`로 깔끔히 대체(D).
4. **🟢 API 스펙 1:1 일치** — 설계 14 엔드포인트 전부 `views.py`에 존재, 권한(`IsAdminUser`)까지 일치. 키워드 상세는 오히려 설계 초과 개선.

---

## 부록: 교차 패턴 (3앱 공통 교훈)

| 패턴 | 발생 앱 | 시사점 |
|------|---------|--------|
| **Beat DatabaseScheduler 미등록 (버그 #28)** | Validation 확인 / SEC는 등록됨(대조군) | config dict만 작성하고 `PeriodicTask.objects.create` 누락 시 자동화 침묵 실패. SEC처럼 DB 등록 검증 필수 |
| **코드 > 문서 (stale 문서)** | SEC, News | task_done/plan 헤더가 현실보다 뒤처짐. 중복 구현·혼동 유발 → 완료 시 문서 헤더 갱신 |
| **구현됐으나 미연결 (dead path)** | Validation(프리셋, llm-filter FE), SEC(없음) | "코드 존재 = 동작"이 아님. 호출처 grep로 연결 검증해야 실효 구현률 산출 |
| **루트 빈 스텁 디렉토리** | sec_pipeline/, validation/ | PR8a 이동 잔재. import 무해하나 정리 대상 |

> 본 보고서는 읽기 전용 감사다. 코드 변경 없음. 후속 조치(threshold 수정, Beat DB 등록, 프리셋 배치 연결, 문서 헤더 갱신)는 별도 태스크로 분리 권장.
