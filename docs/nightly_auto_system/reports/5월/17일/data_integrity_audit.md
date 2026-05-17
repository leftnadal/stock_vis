# 데이터 무결성 감사 보고서

- **작성일**: 2026-05-17
- **감사 대상**: stock_vis 백엔드 Django 모델 + Celery 동기화 태스크 (코드 수정 없음, 읽기 전용)
- **스캔 범위**: 전체 앱 `*/models*.py` (테스트/마이그레이션 제외) + `*/tasks.py`, `*/services/*.py`의 sync/dirty/sync 로직

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 영역 |
|--------|------|------|
| 🔴 High | 4 | Neo4j 동기화 플래그 분산, PG↔Neo4j 일관성 검증 부재, update_or_create race condition, Stock CASCADE 폭발 |
| 🟡 Medium | 5 | SET_NULL orphan 누적, bulk_create의 neo4j_dirty 의존, CASCADE 3단계 체인 미문서화, max_retries=1 단일 실패점, sync_flag default 의미 역전 |
| 🟢 Low | 3 | 자기 참조 SET_NULL(NewsEvent), 자식 FK 누락 없음, PROTECT 안전망 일부 적용 |

**사전 파악 정정**: 사용자 지시서의 "SET_NULL 7곳 / CASCADE 37곳"은 부분 스캔(`head -40`) 결과. 실제는 **SET_NULL 17곳(13 파일) / CASCADE 95곳(27 파일)**.

---

## FK orphan 위험

### 1.1 SET_NULL 분포 (17곳, 13 파일)

| 파일:라인 | FK | 부모 모델 → 자식 | orphan 발생 시나리오 |
|-----------|-----|-------------------|----------------------|
| `rag_analysis/models.py:145` | `basket` | DataBasket → AnalysisSession | basket 삭제 → 세션의 컨텍스트 손실, 메시지 히스토리만 남음 |
| `rag_analysis/models.py:256` | `session` | AnalysisSession → UsageLog | 세션 삭제 → 비용 추적 데이터 고아 (집계는 가능) |
| `rag_analysis/models.py:263` | `message` | AnalysisMessage → UsageLog | 메시지 삭제 → 비용 추적 데이터 고아 |
| `serverless/models.py:660` | `preset` | ScreenerPreset → ScreenerAlert | 프리셋 삭제 → 알림이 `filters_json` 폴백, 정의되어 있음 |
| `serverless/models.py:808` | `user` | User → InvestmentThesis | 사용자 탈퇴 → 익명 테제가 남음 (의도된 보존) |
| `serverless/models.py:1409` | `user` | User → AdminActionLog | 관리자 탈퇴 → 감사 추적 보존 (의도됨) |
| `chainsight/models/news_event.py:54` | `duplicate_of` | ChainNewsEvent(self) | 원본 삭제 → 중복 플래그만 남음 (안전) |
| `macro/models/indicators.py:310` | `related_indicator` | EconomicIndicator → EconomicEvent | 지표 삭제 → 이벤트는 관련 지표 정보 손실 |
| `portfolio/models.py:327` | `wallet_snapshot_at_execution` | WalletSnapshot → ? | 스냅샷 삭제 시 실행 시점 자산 분포 손실 |
| `portfolio/models.py:732` | `analysis_run` | AnalysisRun → ChatSession | 분석 삭제 → 대화만 남음 |
| `portfolio/models.py:831` | `context_analysis_run` | AnalysisRun → ? | 컨텍스트 분석 손실 |
| `thesis/models/monitoring.py:66` | `indicator` | ThesisIndicator → ? | 지표 삭제 → 모니터링 레코드 고아 |
| `thesis/models/indicator.py:15` | `premise` | ThesisPremise → ThesisIndicator | 가설 전제 삭제 → 지표 연결 끊김 |
| `thesis/models/thesis.py:70` | `source_news` | NewsArticle → Thesis | 뉴스 삭제 → 진입 출처 손실 |
| `thesis/models/thesis.py:77` | `copied_from` | Thesis(self) → Thesis | 원본 가설 삭제 → 복제본 흔적 손실 |
| `sec_pipeline/models.py:86` | `target_company` | Stock → SupplyChainEvidence | **핵심 의도**: 미매칭 회사명을 임시 보관, post_save 시그널이 매칭 시 다시 채움 |
| `marketpulse/models/anomaly.py:25` | `paired_news` | MarketPulseNews → AnomalySignalLog | 뉴스 삭제 → 이상 신호의 페어 뉴스 손실 |

### 1.2 orphan 정리 로직 존재 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| PG 측 SET_NULL → null 컬럼 정기 정리 | ❌ **부재** | `cleanup_orphan*`, `purge_null*` 관리 명령 없음 |
| Neo4j 측 orphan 노드 정리 | ⚠️ 1건만 존재 | `news/services/news_neo4j_sync.py:700`만 NewsEvent orphan 노드를 Cypher로 삭제 |
| SEC pipeline 매칭 복원 흐름 | ✅ 존재 | `sec_pipeline/signals.py` post_save 핸들러가 `UnmatchedCompanyQueue` resolved 시 `evidence.target_company` 재바인딩 + `neo4j_dirty=True` |
| usage_log 비용 집계의 orphan 영향 | ⚠️ 분석 누락 | session/message 모두 null인 UsageLog 카운트가 누적될 수 있음. 비용 리포트가 user별로 그룹핑할 때 식별 가능하나 세부 추적 불가 |

**🔴 위험 1**: `rag_analysis.UsageLog`는 session/message 둘 다 SET_NULL — 두 부모가 동시 삭제되면 user 외에 추적 메타가 없는 비용 레코드가 누적. 정리/아카이브 정책 정의 안 됨.

**🟡 위험 2**: SEC pipeline의 `SupplyChainEvidence.target_company` SET_NULL은 의도된 패턴이지만, `UnmatchedCompanyQueue`에 영원히 resolved되지 않은 raw_name이 쌓여도 알림/SLA 없음. `tests/unit/sec_pipeline/test_quality_checks_advanced.py:97`이 50건 임계 알림을 가정하나 실제 운영 알림 라우팅은 미확인.

---

## CASCADE 체인

### 2.1 분포 (95곳, 27 파일)

사용자 지시서의 7 파일을 넘어 다음 파일군 전체에 분포:

```
stocks/, users/, news/, serverless/(11곳), rag_analysis/(5곳),
sec_pipeline/(5곳), graph_analysis/(7곳), metrics/(5곳),
chainsight/(9곳), macro/(5곳), thesis/(15곳),
portfolio/(12곳), marketpulse/(2곳), validation/(8곳)
```

### 2.2 3단계 이상 연쇄 삭제 (High Risk)

#### Chain A: `User` 삭제 시
```
User
 ├─ Portfolio (users.Portfolio, CASCADE)
 ├─ Watchlist (CASCADE)
 │   ├─ WatchlistItem (CASCADE) [stock=CASCADE — Stock도 같이 노출]
 │   ├─ CorrelationMatrix (graph_analysis, CASCADE)
 │   └─ CorrelationEdge (CASCADE)
 │       └─ EdgeAnomaly (graph_analysis, CASCADE)
 ├─ UserStockInterest (CASCADE)
 ├─ Thesis (CASCADE)
 │   ├─ ThesisPremise (CASCADE)
 │   ├─ ThesisIndicator (CASCADE, premise=SET_NULL)
 │   │   └─ IndicatorReading (CASCADE)
 │   ├─ ThesisAlert (CASCADE)
 │   └─ ThesisLearning/Bookmark/Stack (CASCADE)
 ├─ Wallet (portfolio.Wallet, CASCADE) [3단계]
 │   ├─ Holding (CASCADE)
 │   └─ Transaction (CASCADE)
 ├─ AnalysisRun (portfolio, CASCADE)
 │   ├─ MetricResult (CASCADE) [stock=PROTECT — 안전망]
 │   ├─ DiagnosticCard (CASCADE) [target_stock=PROTECT]
 │   ├─ LLMComment (CASCADE) [stock=PROTECT]
 │   ├─ StoredAnalysis (OneToOne, CASCADE)
 │   └─ ChatSession (CASCADE, analysis_run=SET_NULL)
 ├─ AnalysisSession (rag_analysis, CASCADE)
 │   ├─ AnalysisMessage (CASCADE)
 │   │   └─ UsageLog (SET_NULL on message)
 │   └─ UsageLog (SET_NULL on session, CASCADE on user)
 ├─ DataBasket (rag_analysis, CASCADE)
 ├─ ScreenerAlert (serverless, CASCADE)
 │   └─ AlertHistory (CASCADE)
 ├─ PeerPreference (validation, CASCADE)
 └─ AdminActionLog (SET_NULL — 감사 보존)
```

**관측**: User 1건 삭제 시 최소 **8개 직계 자식 → 15+ 손자**까지 일시 삭제. portfolio 측에서 `MetricResult.target_stock=PROTECT`로 안전망이 작동하므로, 보유 종목 데이터가 남아있는 사용자는 portfolio 측에서 차단됨.

#### Chain B: `AnalysisRun` 삭제 시 (portfolio)
```
AnalysisRun
 ├─ MetricResult (CASCADE, stock=PROTECT)
 ├─ DiagnosticCard (CASCADE, target_stock=PROTECT)
 ├─ LLMComment (CASCADE, stock=PROTECT)
 ├─ StoredAnalysis (OneToOne, CASCADE)
 ├─ AnalysisRecommendation (CASCADE)
 │   └─ target_stock (PROTECT)
 └─ ChatSession (analysis_run=SET_NULL)
```

**관측**: 4중 PROTECT가 작동하여 비정상 cascade를 차단. **단, 운영자가 AnalysisRun을 강제 삭제하려면 PROTECT가 IntegrityError를 던지므로 별도 정리 명령이 없으면 deletion이 막힘.**

### 2.3 Stock 삭제 영향 범위 (가장 많은 FK 참조 대상)

**Stock 모델은 약 37+ FK/OneToOneField의 타겟**. 직접 CASCADE 자식:

| 앱 | 모델 | on_delete | to_field |
|-----|------|-----------|----------|
| stocks | DailyPrice | CASCADE | symbol |
| stocks | WeeklyPrice | CASCADE | symbol |
| stocks | BalanceSheet | CASCADE | symbol |
| stocks | IncomeStatement | CASCADE | symbol |
| stocks | CashFlowStatement | CASCADE | symbol |
| stocks | OverviewKo (OneToOne) | CASCADE | pk |
| stocks | EODSignal | CASCADE | id |
| stocks | SignalAccuracy | CASCADE | id |
| stocks | StockNews | CASCADE (null=True) | id |
| users | Portfolio.stock | CASCADE | symbol |
| users | WatchlistItem.stock | CASCADE | symbol |
| portfolio | Holding.stock | PROTECT | id |
| portfolio | Transaction.stock | PROTECT | id |
| portfolio | MetricResult.stock | PROTECT | id |
| portfolio | DiagnosticCard.target_stock | PROTECT | id |
| portfolio | LLMComment.stock | PROTECT | id |
| portfolio | AnalysisRecommendation.target_stock | PROTECT | id |
| chainsight | ChainNewsEvent.symbol | **PROTECT** | symbol |
| chainsight | CompanyChainProfile.symbol (OneToOne) | CASCADE | symbol |
| chainsight | CompanyNarrativeTag (OneToOne) | CASCADE | id |
| chainsight | CompanySensitivityProfile (OneToOne) | CASCADE | id |
| chainsight | CompanyGrowthStage (OneToOne) | CASCADE | id |
| chainsight | CompanyCapitalDNA (OneToOne) | CASCADE | id |
| chainsight | CompanyRevenueStructure (OneToOne) | CASCADE | id |
| chainsight | CompanyInsiderSignal (OneToOne) | CASCADE | id |
| chainsight | CompanyEventReaction | CASCADE | id |
| sec_pipeline | RawDocumentStore.symbol | CASCADE | id |
| sec_pipeline | SupplyChainEvidence.source_company | CASCADE | id |
| sec_pipeline | SupplyChainEvidence.target_company | **SET_NULL** | id |
| sec_pipeline | BusinessModelSnapshot.symbol | CASCADE | id |
| graph_analysis | CorrelationEdge.stock_a | CASCADE | id |
| graph_analysis | CorrelationEdge.stock_b | CASCADE | id |
| graph_analysis | NodeAttribute.stock | CASCADE | id |
| metrics | CompanyMetricSnapshot.symbol | CASCADE | id |
| validation | NewsSummary.symbol (OneToOne) | CASCADE | id |
| validation | CompanyMetricLatest.symbol | CASCADE | id |
| validation | CategorySignal.symbol | CASCADE | id |
| validation | CompanyBenchmarkDelta.symbol | CASCADE | id |
| validation | PeerPreset.symbol | CASCADE | id |
| validation | PeerPreference.symbol | CASCADE | id |

**🔴 위험 3 (Stock CASCADE 폭발)**: Stock 1건 삭제 시 약 **30+ 테이블에 도미노 작용**. 다음 위험이 누적:
- **portfolio의 6개 PROTECT**가 실질 안전망 — 보유/거래/분석 이력이 있는 종목은 삭제 차단됨 (의도된 설계).
- **chainsight의 6개 OneToOne CASCADE**는 의도적 (1:1 프로파일은 종목과 함께 폐기).
- **chainsight.ChainNewsEvent.symbol=PROTECT** 안전망이 작동 — 뉴스 이벤트가 있으면 종목 삭제 차단.
- **validation/metrics CASCADE 6개**는 회복 가능 (재계산 가능한 파생 데이터).
- **stocks 자체의 가격/재무제표 6개 CASCADE는 비가역적** — 가격 히스토리 영구 소실.
- **`to_field='symbol'` 사용** (가격/재무제표/Portfolio/WatchlistItem) — symbol 변경 시 cascade가 따라가지만, symbol upper-case 정규화 위반 시 매칭 실패 가능 (CLAUDE.md `symbol.upper()` 규칙).

---

## Neo4j 동기화

### 3.1 동기화 플래그 패턴 (3가지 공존)

| 패턴 | 사용 모델 | default | 의미 | 단일 소스 통일 여부 |
|------|----------|---------|------|---------------------|
| `neo4j_dirty` | chainsight: RelationConfidence, CompanyChainProfile<br>sec_pipeline: SupplyChainEvidence | `True` (저장 시 자동 더티) | True=동기화 필요 | ✅ audit P0 #9 (2026-04-29)에서 통일됨 |
| `is_synced_to_graph` | serverless: LLMExtractedRelation | `False` | True=동기화 완료 (의미 반전) | ❌ **#27/#28 통일 누락** |
| 별도 sync flag 없음 | serverless: StockRelationship, ETFHolding, ThemeMatch, InstitutionalHolding, CategoryCache, StockKeyword | — | 동기화 추적 불가 | ❌ 동기화 후 어떤 레코드가 반영됐는지 PG 측에서 확인 불가 |

**🔴 위험 4 (플래그 분산)**:
- `chainsight/sec_pipeline`은 `neo4j_dirty=True` 단일 소스로 통일했지만, `serverless`는 두 가지 패턴이 공존.
- `LLMExtractedRelation.is_synced_to_graph`는 `default=False`로, `neo4j_dirty=True`의 역의미. 운영자가 두 패턴을 헷갈리면 한쪽에서는 "이미 동기화됨"으로, 다른쪽에서는 "동기화 안 됨"으로 잘못 판단할 수 있음.
- `StockRelationship` 등 sync 플래그 자체가 없는 모델은 어느 시점 데이터가 Neo4j에 반영됐는지 PG만으로 알 수 없음 — 전수 비교 외에는 검증 불가.

### 3.2 동기화 실패 시 재시도 메커니즘

| 위치 | 패턴 | 강건성 |
|------|------|--------|
| `sec_pipeline/tasks.py:337` `sync_dirty_to_neo4j` | 2-Phase + `select_for_update(skip_locked=True)`, 500건 배치, 성공 ID만 dirty=False 갱신 | ✅ Phase A 락 + 부분 실패 허용 → 다음 실행에서 자연 재시도. `max_retries=1, soft_time_limit=300` |
| `chainsight/services/neo4j_sync.py:21` `sync_dirty_relations` | `iterator(chunk_size=100)` + try/except per row + `queryset.update()`로 dirty=False 일괄 | ⚠️ 단건 실패는 dirty 유지 → 자연 재시도. 단, `synced_pks` 누적 후 `update()` 한 번에 — 실패 인덱스 누락 위험 없음 |
| `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` `run_neo4j_dirty_sync` | `max_retries=2, default_retry_delay=60` | ✅ task-level 재시도까지 적층 |
| `chainsight/tasks/sync_tasks.py:97` `sync_profiles_to_neo4j` | `max_retries=1, soft_time_limit=1800` | 🟡 Neo4j 일시 장애 시 한 번만 재시도. 1800초 동안 행에 걸리면 전체 실패 |
| `serverless/tasks.py:1452` LLM relation sync | `rel.is_synced_to_graph = True; rel.save(update_fields=['is_synced_to_graph'])` | ⚠️ 단건 실패 시 dirty 유지 메커니즘 부재. `save()`가 race로 안 박히면 영구 unsynced 가능성 |

**🟡 위험 5 (max_retries=1 단일 실패점)**: `sync_profiles_to_neo4j`는 SP500 전체를 1회 처리. Neo4j 일시 끊김 시 재시도 1회로 부족할 수 있음. 직후 데이터는 `neo4j_dirty=True`로 유지되므로 결국 다음 Beat 호출에서 회복되지만, **모니터링 알림 없으면 백로그 누적 인지 지연**.

### 3.3 PG ↔ Neo4j 불일치 감지 방법

| 검출 방향 | 존재 여부 | 근거 |
|----------|-----------|------|
| PG에 있지만 Neo4j에 없음 | ❌ **부재** | `reconcile_*`, `pg_vs_neo4j_diff` 명령 없음. `neo4j_dirty=True` 백로그 카운트는 알 수 있으나 "이미 dirty=False인데 Neo4j에 실제 없는" 케이스는 잡지 못함 |
| Neo4j에 있지만 PG에 없음 | ⚠️ **1건만** | `news/services/news_neo4j_sync.py:700` 의 orphan NewsEvent 정리 쿼리만 존재 |
| `neo4j_dirty` 백로그 알림 | ⚠️ 부분 | `tests/unit/sec_pipeline/test_quality_checks_advanced.py:97`이 50건 임계 가정. 실제 알림 라우팅은 운영 도구 영역 |
| Sync 시간 차이 검출 | ⚠️ 간접 | `neo4j_synced_at` 컬럼은 존재. `WHERE neo4j_synced_at < NOW() - INTERVAL '24 hours' AND neo4j_dirty=False` 같은 쿼리 가능하나 정기 잡 없음 |

**🔴 위험 6 (일관성 검증 부재)**: PG-Neo4j 불일치를 능동적으로 검출하는 reconcile cron이 없음. 다음 시나리오에서 사일런트 데이터 손상:
- Neo4j 내부에서 운영자가 수동 DELETE (e.g. Cypher cleanup)
- PG `neo4j_dirty=False` 상태인데 Neo4j edge가 사라진 경우 — 다음 Beat에서 dirty가 다시 True로 가야 sync되는데, 트리거 없음
- `StockRelationship`, `ETFHolding`, `ThemeMatch` 등 sync flag 없는 모델은 검증 도구도 부재

### 3.4 transaction.atomic 외부의 update_or_create

위험 패턴 — `chainsight/tasks/relation_tasks.py:275,309`, `chainsight/tasks/profile_tasks.py:106,180`, `serverless/services/keyword_service.py:202` 등에서 `transaction.atomic()` 컨텍스트 없이 `update_or_create()` 호출. Django 4+ 에서도 동시 호출 시 두 트랜잭션이 동시에 SELECT → 한쪽 INSERT 성공 → 다른쪽 IntegrityError 가능.

`chainsight/tasks/relation_tasks.py:291` 주석 — "update_or_create는 save()를 호출하므로 neo4j_dirty=True 자동" — 정상 동작 시 의도대로 작동하지만, 동시성 충돌로 IntegrityError 시 dirty flag가 토글되지 않은 채 태스크 재시도가 시작됨. 재시도가 idempotent라서 결과적으로 회복되지만, sentry/log 잡음.

---

## Unique 제약조건

### 4.1 unique_together 분포 (21곳)

| 앱 | 모델 | unique_together |
|-----|------|-----------------|
| metrics | IndustryMetricBenchmark | `industry, fiscal_year, metric_code` |
| metrics | PeerMetricBenchmark | `symbol, fiscal_year, metric_code, preset_key` |
| metrics | CompanyMetricSnapshot | `symbol, fiscal_year, metric_code` |
| rag_analysis | BasketItem | `basket, item_type, reference_id` |
| serverless | MarketMover | `date, mover_type, symbol` |
| serverless | VolatilityBaseline | `symbol, date` |
| serverless | StockKeyword | `symbol, date` |
| serverless | SectorPerformance | `date, sector` |
| serverless | CorporateAction | `symbol, date, action_type` |
| serverless | StockRelationship | `source_symbol, target_symbol, relationship_type` |
| serverless | CategoryCache | `symbol, date` |
| serverless | ETFHolding | `etf, stock_symbol, snapshot_date` |
| serverless | ThemeMatch | `stock_symbol, theme_id` |
| serverless | LLMExtractedRelation | `source_symbol, target_symbol, relation_type, source_id` |
| serverless | InstitutionalHolding | `institution_cik, stock_symbol, report_date` |
| stocks | DailyPrice | `stock, date` |
| stocks | WeeklyPrice | `stock, date` |
| stocks | EODSignal | `stock, date` |
| stocks | SignalAccuracy | `stock, signal_date, signal_tag` |
| chainsight | ChainNewsEvent | `source, source_id` |
| news | NewsEntity | `news, symbol` |

### 4.2 UniqueConstraint (Meta.constraints) — 4곳

`portfolio/models.py` 만 사용:
- `unique_metric_result_per_run_stock` (analysis_run, stock, metric_id)
- `unique_card_priority_per_run` (analysis_run, priority)
- `unique_comment_per_run_stock_metric` (analysis_run, stock, metric_id)
- `unique_percentile_cache` (metric_id, industry_code, date)

**관측**: 같은 효과인 `unique_together`와 `UniqueConstraint`가 혼재. Django 4.x는 `unique_together`를 deprecate 권고 — 마이그레이션 시 일관성 부재. 기능 영향은 없으나 새 모델 작성 시 표준 부재.

### 4.3 update_or_create race condition 분석

`update_or_create` 호출처 30+ 곳. 동시성 안전 분석:

| 영역 | 위치 | atomic 컨텍스트 | 위험 |
|------|------|-----------------|------|
| `api_request/stock_service.py` | 6곳 | `with transaction.atomic()` 내부 | ✅ 안전 |
| `serverless/services/data_sync.py` | `@transaction.atomic` 데코레이터 | ✅ 안전 |
| `serverless/services/institutional_holdings_service.py:271` | `with transaction.atomic():` | ✅ 안전 |
| `serverless/services/sector_heatmap_service.py:106` | `with transaction.atomic():` | ✅ 안전 |
| `serverless/services/market_breadth_service.py:111` | `with transaction.atomic():` | ✅ 안전 |
| `chainsight/tasks/sync_tasks.py:84` | atomic 없음 | 🟡 SP500 순차 처리, 단일 워커 가정 시 안전. 다중 워커면 race |
| `chainsight/tasks/relation_tasks.py:275,309` | atomic 없음 | ⚠️ 동시 호출 시 IntegrityError |
| `chainsight/tasks/profile_tasks.py:106,180` | atomic 없음 | ⚠️ 동시 호출 시 IntegrityError |
| `chainsight/tasks/insider_tasks.py:117,162` | atomic 없음 | ⚠️ 동시 호출 시 IntegrityError |
| `serverless/tasks.py:393,1425` | atomic 없음 | ⚠️ keyword/relationship 동시 호출 위험 |
| `serverless/services/theme_matching_service.py:247,329,575` | atomic 없음 | ⚠️ 다중 워커에서 race |
| `serverless/services/keyword_service.py:202` | atomic 없음 | ⚠️ 같은 (symbol, date) 동시 호출 위험 |
| `serverless/services/supply_chain_service.py:328` | `@transaction.atomic` (278) | ✅ 안전 |

**🔴 위험 7 (race condition)**:
- Celery 동시 워커 + 같은 unique key 동시 호출 → `IntegrityError`
- 재시도(`max_retries=3 + exponential backoff`)가 자연 해소하지만, **logging 잡음 + neo4j_dirty 토글 누락** 가능
- `sec_pipeline/tasks.py:314` 의 `RelationConfidence.objects.update_or_create`는 atomic 없음 — sec → chainsight seed 시 동시 실행되면 충돌 가능

**🟡 위험 8 (bulk_create의 neo4j_dirty 의존)**:
`sec_pipeline/validator_track_a.py:162` `SupplyChainEvidence.objects.bulk_create(evidences)` — `bulk_create`는 `save()` 미호출. 현재 모델 정의에서 `neo4j_dirty = models.BooleanField(default=True)`라서 자동으로 True가 박히지만, **default 변경 시 사일런트 회귀**. `evidences` 객체 생성 시 명시적으로 `neo4j_dirty=True` 박는 것이 안전. (현재 코드는 default 의존)

`graph_analysis/services/correlation_calculator.py:372` `CorrelationEdge.objects.bulk_create(...)` — 동기화 플래그 없음 (Neo4j 동기화 자체가 없으므로 무영향).

`stocks/services/eod_pipeline.py:347` `EODSignal.objects.bulk_create(..., update_conflicts=True)` — Django 4.1+ upsert 패턴. unique_together (`stock, date`) 기반 안전 ✅.

`thesis/services/keyword_cache.py:41` `KeywordCache.objects.bulk_create([...])` — 보조 캐시. 안전.

---

## 부록: 권장 후속 조치 (참고용, 본 보고서는 코드 미수정)

1. **🔴 P0**: `LLMExtractedRelation.is_synced_to_graph` → `neo4j_dirty` 의미 통일 (audit P0 #9 확장). `StockRelationship/ETFHolding/ThemeMatch`도 sync flag 추가.
2. **🔴 P0**: `reconcile_pg_neo4j` 관리 명령 작성 — `neo4j_dirty=False`인 레코드에 대해 Neo4j 실재 여부 표본 검사, 누락 시 dirty 재설정.
3. **🔴 P1**: 동시성 위험이 있는 `update_or_create` 호출처를 `transaction.atomic()` 또는 `IntegrityError` 캐치 + retry 데코레이터로 감싸기.
4. **🟡 P1**: `UsageLog`처럼 SET_NULL 후 null 누적 가능한 테이블에 대해 월간 archive 명령 정의.
5. **🟡 P2**: `unique_together` 신규 사용 금지, `UniqueConstraint`로 통일 가이드.
6. **🟡 P2**: `sync_profiles_to_neo4j` `max_retries=1` 재검토 — 최소 2~3로 상향.
7. **🟢 P3**: `bulk_create(SupplyChainEvidence)` 등 default 의존 코드에 `neo4j_dirty=True` 명시.

---

**감사 종료**. 본 보고서는 읽기 전용 스캔 결과이며, 실제 운영 데이터 카운트(예: 현재 `neo4j_dirty=True` 백로그 건수)는 별도 DB 쿼리로 확인해야 함.
