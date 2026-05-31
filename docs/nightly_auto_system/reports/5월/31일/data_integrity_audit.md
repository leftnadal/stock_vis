# 데이터 무결성 감사 보고서

> 작성일: 2026-05-31
> 범위: 읽기 전용 정적 감사 (코드 수정 없음)
> 방법: 모델 정의 전수 파싱 (FK/제약/동기화 플래그) + 동기화·upsert 호출부 확인

---

## ⚠️ 사전 정정 — 모델 경로가 monorepo 마이그레이션으로 이동됨

지시서에 명시된 경로(`stocks/models.py`, `chainsight/models.py`, `metrics/models.py` 등)는 **현재 트리에 대부분 존재하지 않습니다.** 진행 중인 monorepo 마이그레이션(PR7)으로 모델이 `packages/shared/`, `apps/` 하위로 이동했습니다. 실제 위치는 다음과 같으며, **이번 감사는 실제 위치 기준으로 전수 수행**했습니다.

| 지시서 경로 | 실제 위치 | 비고 |
|------|------|------|
| stocks/models.py | `packages/shared/stocks/models.py` | |
| users/models.py | `packages/shared/users/models.py` | |
| news/models.py | `news/models.py` | 동일 |
| serverless/models.py | `serverless/models.py` | 동일 |
| rag_analysis/models.py | `rag_analysis/models.py` | 내용은 **analysis 앱**(DataBasket/Session/UsageLog), RAG 전용 모델 없음 |
| sec_pipeline/models.py | `sec_pipeline/models.py` | 동일 |
| graph_analysis/models.py | `services/_dormant/graph_analysis/models.py` | **dormant로 이동(휴면)** |
| chainsight/models.py | `apps/chain_sight/models/*.py` | **패키지 디렉토리 13개 파일** |
| analysis/models.py | (없음) | 내용이 rag_analysis로 통합 |
| thesis/models.py | `thesis/models/*.py` | 패키지 6개 파일 |
| metrics/models.py | `packages/shared/metrics/models/*.py` | 패키지 4개 파일 |
| validation/models.py | `validation/models/*.py` | 패키지 5개 파일 |
| macro/models.py | `macro/models/*.py` | 패키지 2개 파일 |
| apps/portfolio/models.py | `apps/portfolio/models.py` | 동일 |

> **카운트 차이 주의**: 지시서의 "SET_NULL 7곳/3파일, CASCADE 37곳/7파일"은 마이그레이션 **이전** 스냅샷입니다. 실제 현재 트리는 **SET_NULL 17곳, CASCADE 49곳+** 입니다. `--glob **/models.py`만 보면 패키지 디렉토리(`thesis/models/`, `macro/models/`, `apps/chain_sight/models/`)가 누락되어 과소 집계되므로, 본 보고서는 전체 디렉토리 기준 수치를 사용합니다.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 1 | **User 삭제 4~5단계 CASCADE 연쇄** — Wallet→Portfolio→AnalysisRun→{Metric/Card/Comment} 대량 삭제, 복구 불가 |
| 🟠 Medium | 3 | ① Stock 삭제 4단계 sec_pipeline 연쇄 ② SET_NULL orphan 명시적 정리 로직 부재 ③ Neo4j 역방향 불일치(Neo4j有/PG無) 감지 장치 없음 |
| 🟡 Low | 3 | ① graph_analysis(dormant) 잔존 CASCADE ② rag_analysis sync 플래그 지시서 미반영 ③ serverless는 Stock을 FK 아닌 CharField로 참조(정합성 보장 약함) |
| 🟢 양호 | — | upsert 경로 대부분 unique_together와 lookup 키 일치 / neo4j_dirty 단일 소스 통일 / 핵심 시계열 전부 복합 unique |

**정량 인벤토리**
- SET_NULL: **17곳** (10개 모델)
- CASCADE: **49곳+** (Stock·User가 최대 부모)
- Stock 직접 참조: CASCADE 약 30개 모델 + PROTECT 6곳 + SET_NULL 1곳
- Neo4j 동기화 플래그(`neo4j_dirty`): **3개 모델** (CompanyChainProfile, RelationConfidence, SupplyChainEvidence)
- unique 제약: unique_together 40+ / UniqueConstraint 4(portfolio) / unique=True 다수

---

## FK orphan 위험

### SET_NULL 사용처 전수 (17곳 / 10개 모델)

| 모델 (파일) | 필드 → 대상 | related_name | null |
|------|------|------|------|
| ScreenerAlert (serverless) | `preset` → ScreenerPreset | alerts | T |
| InvestmentThesis (serverless) | `user` → users.User | investment_theses | T |
| AdminActionLog (serverless) | `user` → users.User | — | T |
| SupplyChainEvidence (sec_pipeline) | `target_company` → stocks.Stock | sec_supply_chain_as_target | T |
| AnalysisSession (rag_analysis) | `basket` → DataBasket | sessions | T |
| UsageLog (rag_analysis) | `session` → AnalysisSession | usage_logs | T |
| UsageLog (rag_analysis) | `message` → AnalysisMessage | usage_logs | T |
| AnalysisRun (portfolio) | `wallet_snapshot_at_execution` → WalletSnapshot | analyses_at_time | T |
| ChatSession (portfolio) | `analysis_run` → AnalysisRun | chat_sessions | T |
| Decision (portfolio) | `context_analysis_run` → AnalysisRun | decisions | T |
| ThesisIndicator (thesis) | `premise` → ThesisPremise | indicators | T |
| ThesisAlert (thesis) | `indicator` → ThesisIndicator | alerts | T |
| HypothesisEvent (thesis) | `thesis` → Thesis | events | T |
| Thesis (thesis) | `source_news` → news.NewsArticle | thesis_sources | T |
| Thesis (thesis) | `copied_from` → self | copies | T |
| EconomicEvent (macro) | `related_indicator` → EconomicIndicator | events | T |
| ChainNewsEvent (chain_sight) | `duplicate_of` → self | duplicates | T |

모두 `null=True`가 정상 설정되어 있어 **SET_NULL 자체로 인한 IntegrityError 위험은 없음**.

### orphan 레코드 정리 로직 — 🟠 명시적 정리 부재

- **명시적 orphan 삭제/정리 태스크는 발견되지 않음.** SET_NULL로 NULL이 된 레코드를 주기적으로 스캔·삭제하는 management command / Celery beat는 없음.
- 단, `sec_pipeline`의 `target_company`(SET_NULL)는 **의도적 설계**(주석: "NULL 허용 — 회사 미식별 케이스"). 게다가 `sec_pipeline/signals.py` + `ticker_matcher.py`에 **재연결(backfill) 경로**가 존재:
  - `qs.update(target_company=target_stock, neo4j_dirty=True)` — 신규 Stock 등록/매칭 성공 시 NULL이던 evidence를 재연결.
  - 즉 sec_pipeline은 "삭제"가 아니라 "재매칭" 전략 → orphan을 **재활용**하므로 누적 자체가 설계 의도.
- 위험: `target_company`가 ① 처음부터 미식별 NULL 인지 ② Stock 삭제로 NULL 된 것인지 **구분 불가**. 후자라면 재매칭 대상이 아닌데 backfill이 잘못 채울 가능성(낮음). 영구 미식별 NULL evidence는 무한 잔존 — 모니터링 권고.
- 그 외 SET_NULL(portfolio analysis_run, thesis indicator/premise 등)도 정리 로직 없음. 대부분 "감사 추적용 이력 보존"이 목적으로 보여 위험은 낮으나, NULL 비율 증가 시 쿼리 효율 저하 가능.

---

## CASCADE 체인

### 🔴 User 삭제 — 최대 깊이 4~5단계 (High)

```
User (AUTH_USER_MODEL) 삭제
├─ Wallet (user, CASCADE)
│   ├─ WalletSnapshot (wallet, CASCADE)
│   ├─ WalletHolding (wallet, CASCADE)          [.stock은 PROTECT]
│   └─ Portfolio (wallet, CASCADE)
│       └─ AnalysisRun (portfolio, CASCADE)      ← 3단계
│           ├─ MetricResult (analysis_run, CASCADE)        ← 4단계
│           ├─ DiagnosticCard (analysis_run, CASCADE)      ← 4단계
│           ├─ LLMComment (analysis_run, CASCADE)          ← 4단계
│           ├─ StoredAnalysis (analysis_run O2O, CASCADE)  ← 4단계
│           └─ ChatSession (analysis_run SET_NULL) → Message(CASCADE)
├─ Thesis (user, CASCADE)
│   ├─ ThesisPremise → ThesisIndicator → IndicatorReading   ← 4단계
│   │                              └─ ThesisAlert
│   ├─ ThesisSnapshot / ValidityRecord
├─ Watchlist (user) → WatchlistItem
├─ DataBasket (user) → BasketItem
├─ ChatSession(user)/Decision(user)/HypothesisEvent(user)/InvestorDNA(user,O2O)
├─ ThesisFollow(user) / SavedPath(user, null=True) → PathAction
└─ ScreenerPreset/ScreenerAlert/InvestmentThesis(SET_NULL)/UserInterest/UserPeerPreference
```

**위험**: 단일 User 삭제가 포트폴리오 분석 전체(AnalysisRun 산하 Metric/Card/Comment), 가설 통제실 전체(Thesis 산하), 워치리스트, 데이터바스켓을 **연쇄 물리 삭제**. 분석 비용($)이 든 LLMComment/StoredAnalysis까지 복구 불가능하게 사라짐. 운영 중 GDPR 삭제·실수 삭제 시 영향 최대. → **soft delete 또는 보관 정책 검토 권고.**

### 🟠 Stock 삭제 — sec_pipeline 4단계 연쇄 (Medium)

```
Stock 삭제
├─ RawDocumentStore (symbol, CASCADE)            ← 1단계
│   ├─ SupplyChainEvidence (source_document, CASCADE)   ← 2단계
│   └─ BusinessModelSnapshot (source_document, CASCADE) ← 2단계
│       └─ BusinessModelEvidence (snapshot, CASCADE)    ← 3단계
├─ SupplyChainEvidence (source_company, CASCADE)  [target_company는 SET_NULL]
├─ BusinessModelSnapshot (symbol, CASCADE)
├─ (packages/shared/stocks) DailyPrice, WeeklyPrice, BalanceSheet,
│   IncomeStatement, CashFlowStatement, StockOverviewKo(O2O),
│   EODSignal, SignalAccuracy, StockNews — 전부 CASCADE
├─ (users) Portfolio.stock, WatchlistItem.stock — CASCADE
├─ (validation) CompanyBenchmarkDelta/CategorySignal/CompanyMetricLatest/
│   ValidationNewsSummary(O2O)/PeerPreset/UserPeerPreference — CASCADE
├─ (chain_sight) Capital/Chain/Growth/Insider/Narrative/Revenue/Sensitivity
│   Profile (전부 .symbol O2O), CompanyEventReaction — CASCADE
├─ (metrics) PeerListCache(O2O), PeerMetricBenchmark — CASCADE
└─ (graph_analysis, dormant) CorrelationEdge.stock_a/b → CorrelationAnomaly
```

**PROTECT 방어막(삭제 차단)이 있는 곳** — Stock에 다음 자식이 있으면 삭제가 막힘:
- portfolio: WalletHolding.stock, MetricResult.stock, DiagnosticCard.target_stock, LLMComment.stock
- metrics: CompanyMetricSnapshot.symbol
- chain_sight: ChainNewsEvent.symbol

→ **즉 실제 운영 Stock은 portfolio/metrics/chainsight 자식 때문에 그냥은 삭제 불가(PROTECT)**. 이는 의도된 안전장치로 평가. 다만 PROTECT가 없는 영역(가격/재무/검증/프로파일)은 CASCADE로 대량 삭제됨.

**Stock 직접 참조 최다**: chain_sight 8개 프로파일 + validation 6개 + stocks 9개 + 기타. Stock이 사실상 전 도메인의 루트 엔티티.

### 🟡 기타
- `services/_dormant/graph_analysis`: CASCADE 8곳이 휴면 코드에 잔존. 마이그레이션이 활성이면 불필요한 테이블/제약 유지. 정리 후보.
- serverless/news는 Stock을 **FK가 아닌 `symbol` CharField**로 참조 → Stock 삭제 시 자동 정리 안 됨(orphan 문자열 잔존 가능). 참조 무결성을 DB가 보장하지 않음 → 🟡.

---

## Neo4j 동기화

### 동기화 플래그 현황 — `neo4j_dirty` 단일 소스로 통일됨

| 모델 | 파일 | 플래그 | 인덱스 |
|------|------|------|------|
| CompanyChainProfile | apps/chain_sight/models/chain_profile.py | `neo4j_dirty`(default=True, db_index=True) + `neo4j_synced_at` | ✅ |
| RelationConfidence | apps/chain_sight/models/relation_discovery.py | `neo4j_dirty`(default=True) + `neo4j_synced_at` | ✅ Index(["neo4j_dirty"]) |
| SupplyChainEvidence | sec_pipeline/models.py | `neo4j_dirty`(default=True) + `neo4j_synced_at` | ✅ Index(["neo4j_dirty"]) |

- **설계 양호**: audit P0 #9에서 `synced_to_neo4j`를 제거하고 `neo4j_dirty` 단일 소스로 통일(2026-04-29, migration 0008). 의미 반전(`True=동기화 필요`)을 마이그레이션으로 일괄 변환. CLAUDE.md DECISIONS와 일치.
- serverless `LLMExtractedRelation.is_synced_to_graph`(default=False)는 별도 명명 — 통일 대상에서 제외된 잔존물(🟡 명명 불일치, 기능엔 무해).
- `bulk_update`/`queryset.update()`는 `save()`를 호출하지 않으므로 `neo4j_dirty`가 자동 세팅되지 않음 → 코드에서 **수동 토글**(relation_tasks.py decay, sync_tasks.py). 이 패턴이 누락되면 dirty 누락 위험 → 현재는 주석으로 방어 중.

### 동기화 실패 시 재시도 메커니즘 — 2중 구조 (대체로 양호)

이중 안전망이 실제로 존재함:
- **(1) Celery task 레벨 재시도**: `run_neo4j_dirty_sync`(`max_retries=2, default_retry_delay=60`), `sync_profiles_to_neo4j`/`sync_relations_to_neo4j`(`max_retries=1`), sec_pipeline(`max_retries=3` + 지수 백오프 `countdown=60*(2**retries)`). CLAUDE.md 표준 준수.
- **(2) 레코드 레벨 self-healing 큐**: 동기화 성공 시에만 `neo4j_dirty=False` + `neo4j_synced_at=now()`로 전환(`save(update_fields=["neo4j_dirty","neo4j_synced_at"])` 부분 저장 → 동시성 안전). `filter(neo4j_dirty=True)`로 큐 소비.
- **핵심 뉘앙스**: 동기화 task는 **루프 내부에서 항목별 예외를 try/except로 삼키고 로그만 남김**(`sync_profiles_to_neo4j` 등). 즉 개별 레코드 실패는 `self.retry`를 트리거하지 않고 `neo4j_dirty=True`로 남아 **다음 beat에서 재픽업**됨. task 전체 실패(타임아웃 등)만 `max_retries` 대상. → 항목 단위 복구는 dirty-flag, 작업 단위 복구는 max_retries로 역할 분담(합리적).
- **🟡 잔여 위험**: 영구 실패 항목(잘못된 데이터/존재하지 않는 노드)은 매 beat마다 무한 재시도되며 격리되지 않음 — **실패 카운트/dead-letter 컬럼 없음**. 백로그>50 알림(아래)이 유일한 가시화.

### PG ↔ Neo4j 불일치 감지 — 🟠 단방향만 존재

- **PG→Neo4j pending 감지 O**: `sec_pipeline/quality_checks.py`·`intelligence.py`가 `filter(neo4j_dirty=True, target_company__isnull=False).count()`로 미동기화 건수 집계. **50건 초과 시 백로그 알림**(test_neo4j_dirty_backlog_alert, 경계 50). chain_sight도 `neo4j_dirty=True` count로 pending 추적.
- **Neo4j→PG 역방향 감지 X**: Neo4j에는 존재하나 PG에 없는(또는 PG에서 삭제됐는데 Neo4j에 잔존하는) 노드/관계를 탐지하는 reconciliation 로직 **없음**. PG count vs Neo4j node count 대조 검증 명령도 없음.
- **위험**: PG에서 CASCADE 삭제가 일어나도 Neo4j 그래프에는 고아 노드가 남을 수 있음. 삭제 전파가 Neo4j로 가는 경로(삭제 시 dirty 토글)는 확인되지 않음 → 삭제 동기화 공백. (참고: 운영 메모 "1573 노드/12695 관계"는 적재만 검증, 정합성 자동검증 아님.)
- **권고**: 주기적 PG↔Neo4j count 대조 + orphan node 정리 태스크 신설.

---

## Unique 제약조건

### 핵심 unique_together (시계열·업서트 보호)

| 도메인 | 모델 | unique_together |
|------|------|------|
| stocks | DailyPrice/WeeklyPrice | (stock, date) |
| stocks | BalanceSheet/Income/CashFlow | (stock, period_type, fiscal_year, fiscal_quarter) |
| stocks | EODSignal | (stock, date) / SignalAccuracy (stock, signal_date, signal_tag) |
| users | Portfolio (user,stock) / Watchlist (user,name) / WatchlistItem (watchlist,stock) / UserInterest (user,interest_type,value) |
| serverless | MarketMover (date,mover_type,symbol) / CorporateAction (symbol,date,action_type) / ETFHolding (etf,stock_symbol,snapshot_date) / InstitutionalHolding (institution_cik,stock_symbol,report_date) / LLMExtractedRelation (source_symbol,target_symbol,relation_type,source_id) 외 6 |
| metrics | CompanyMetricSnapshot (symbol,fiscal_year,metric_code) / IndustryMetricBenchmark / PeerMetricBenchmark(+preset_key) |
| validation | CompanyBenchmarkDelta/CategorySignal/CompanyMetricLatest/PeerPreset/UserPeerPreference (전부 symbol+키 조합) |
| macro | IndicatorValue (indicator,date) / MarketIndexPrice (index,date) / IndicatorCorrelation (indicator_a,indicator_b) |
| chain_sight | RelationConfidence (symbol_a,symbol_b,relation_type) / CoMentionEdge (symbol_a,symbol_b) / ChainNewsEvent (source,source_id) / CompanyEventReaction (symbol,event_type) |
| sec_pipeline | CompanyAlias (alias, context_sector) |
| rag_analysis | BasketItem (basket, item_type, reference_id) |
| thesis | ThesisSnapshot (thesis,asof_date) / IndicatorReading (indicator,asof) / ThesisFollow (user,original_thesis) / KeywordCache (target,source,text) |

### UniqueConstraint (Meta.constraints) — portfolio 전용 4건
- MetricResult: `(analysis_run, stock, metric_id)` name=unique_metric_result_per_run_stock
- DiagnosticCard: `(analysis_run, priority)` name=unique_card_priority_per_run
- LLMComment: `(analysis_run, stock, metric_id)` name=unique_comment_per_run_stock_metric
- PercentileCache: `(metric_id, industry_code, date)` name=unique_percentile_cache

### update_or_create / race condition — 🟢 대체로 안전, 일부 점검 필요

- **DB 레벨 보장 양호**: 위 시계열·업서트 모델 대부분 lookup 키가 unique_together와 일치 → 동시 호출 시 최악의 경우 IntegrityError가 나도 **중복 행은 생성 불가**. 야간 자동화(EOD 시그널, 분기 지표, Market Movers)의 핵심 upsert 경로가 여기에 해당.
- **point of attention**:
  - `thesis/services/snapshot_builder.py`: `unique_together=['thesis','asof_date'] 충돌 시 update` — lookup 키 일치 확인됨(안전).
  - `update_or_create`는 Django에서 SELECT→없으면 INSERT 2단계라 **유니크 제약이 lookup 키를 덮지 않으면** 동시성 하에 중복 생성 가능. 유니크 제약이 없는 모델에서 upsert를 한다면 위험 → 본 감사에서 시계열 모델은 전부 제약 보유 확인. **제약 없는 모델의 upsert 호출부는 호출 코드 레벨 개별 점검 권고**(예: 캐시성 테이블).
  - `bulk_update`/`queryset.update()` 경로는 `save()` 미호출이라 `neo4j_dirty` 자동화 우회 → 위 Neo4j 섹션과 연계, 수동 토글 누락 시 동기화 누락(정합성 위험).

---

## 후속 조치 권고 (우선순위)

1. **🔴 User 삭제 정책**: AnalysisRun 산하(비용 발생 LLM 산출물 포함) 4~5단계 CASCADE에 대해 soft delete 또는 보관(archive) 도입 검토.
2. **🟠 Neo4j 양방향 reconciliation**: PG↔Neo4j count 대조 + PG 삭제 시 Neo4j orphan 노드 정리 태스크 신설. 현재는 PG→Neo4j pending(백로그>50 알림)만 존재.
3. **🟠 동기화 실패 격리**: `neo4j_dirty` 영구 실패 항목용 실패 카운트/dead-letter 컬럼 도입(현재 무한 재시도).
4. **🟠 SET_NULL orphan 모니터링**: sec_pipeline target_company 등 영구 NULL 비율 추적, 미식별-vs-삭제유래 구분 플래그 검토.
5. **🟡 정리**: `services/_dormant/graph_analysis` CASCADE 잔존 제거, serverless `is_synced_to_graph` 명명 통일.

---

*본 보고서는 실제 파일(monorepo 이동 후 위치) 전수 파싱 결과이며, 모든 FK/제약/플래그는 코드 원문에서 확인됨. 코드 수정은 일절 수행하지 않음.*
