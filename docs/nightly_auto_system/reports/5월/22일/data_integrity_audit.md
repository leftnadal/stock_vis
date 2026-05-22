# 데이터 무결성 감사 보고서

> 작성일: 2026-05-22
> 범위: Django ORM 레벨 FK 정책, CASCADE 체인, Neo4j 동기화, Unique 제약
> 도구: 정적 분석 (grep + 코드 읽기, DB 실측 미포함)
> 모드: 읽기 전용

---

## 요약 (위험도별 이슈 수)

| 위험도 | 항목 수 | 대표 이슈 |
|--------|---------|-----------|
| 🔴 High | 4 | Stock CASCADE 폭심도, update_or_create race, 양방향 Neo4j 불일치 미감지, SET_NULL orphan 정리 부재 |
| 🟡 Medium | 5 | 3단계 이상 CASCADE 체인, AnalysisSession SET_NULL 후 usage_logs orphan, ETFProfile 단방향 검증, neo4j_dirty 백로그 모니터링 단편 |
| 🟢 Low | 3 | Unique 제약은 비교적 견고, neo4j_dirty 통일 마이그레이션 완료, PROTECT 7곳 정상 |

**핵심 결론**: CASCADE 정책은 광범위하나 의도적이며 안전성은 stocks.Stock 삭제 시나리오에 집중되어야 함. 가장 큰 운영 리스크는 **update_or_create의 race condition**(40+ 위치, 대부분 비 atomic)과 **PG↔Neo4j 양방향 불일치 감지 부재**.

---

## FK orphan 위험

### SET_NULL 사용처 (총 17곳, 사전 파악된 7곳보다 광범위)

> 사전 파악된 `sec_pipeline/serverless/rag_analysis`는 부분 — 실제로 thesis/portfolio/chainsight/marketpulse/macro 영역에 추가 존재.

| 위치 | 필드 | 부모 모델 | 관리 정책 |
|------|------|----------|-----------|
| `marketpulse/models/anomaly.py:25` | `paired_news` | MarketPulseNews | orphan 정리 로직 없음 |
| `thesis/models/thesis.py:70` | `source_session` | (AnalysisSession 추정) | 없음 |
| `thesis/models/thesis.py:77` | `original_thesis` | Thesis (self) | 없음 — 복제본 무한 누적 가능 |
| `thesis/models/indicator.py:15` | `premise` | ThesisPremise | 없음 |
| `thesis/models/monitoring.py:66` | `indicator` | ThesisIndicator | 없음 |
| `sec_pipeline/models.py:86` | `target_company` | stocks.Stock | `quality_checks.py:144` 측면 카운트만 |
| `serverless/models.py:660` | `preset` (ScreenerAlert) | ScreenerPreset | 없음 |
| `serverless/models.py:808` | (InvestmentThesis 측 stock) | stocks.Stock | 없음 |
| `serverless/models.py:1409` | `user` (AuditLog) | users.User | 의도적 (감사 로그 보존) |
| `macro/models/indicators.py:310` | `related_indicator` | EconomicIndicator | 없음 |
| `chainsight/models/news_event.py:54` | `duplicate_of` | self | 없음 |
| `rag_analysis/models.py:145` | `basket` | DataBasket | 🔴 AnalysisSession orphan |
| `rag_analysis/models.py:256` | `session` (UsageLog) | AnalysisSession | 🔴 UsageLog orphan + null로 추적 단절 |
| `rag_analysis/models.py:263` | `message` (UsageLog) | AnalysisMessage | 🔴 동일 |
| `portfolio/models.py:327` | `wallet_snapshot_at_execution` | WalletSnapshot | 의도적 (이력 보존) |
| `portfolio/models.py:732` | `analysis_run` (ChatSession) | AnalysisRun | 없음 |
| `portfolio/models.py:831` | `context_analysis_run` (Decision) | AnalysisRun | 없음 |

### Orphan 정리 로직 존재 여부

🔴 **PG 측 orphan 정리 로직 없음 — 전수 부재**

- 전체 코드베이스에서 `orphan` 키워드 매칭은 **Neo4j 측만** (news/services/news_neo4j_sync.py:700) — `MATCH (n:NewsEvent) WHERE NOT (n)--() DELETE n` 패턴
- SET_NULL 후 NULL 값 row를 주기적으로 삭제/아카이브하는 management command나 Celery 태스크 없음
- AuditLog/WalletSnapshot처럼 의도적 보존인 경우 외에는 **장기적으로 부풀어 오를 위험** — 특히 rag_analysis(AnalysisSession.basket=NULL, UsageLog.session=NULL) 3건은 누적 시 쿼리 plan 왜곡 가능

### 권고

1. `rag_analysis` 3건은 CASCADE 검토 (UsageLog는 보통 sub-resource — 부모 삭제 시 같이 사라지는 게 자연스러움)
2. `Thesis.original_thesis=SET_NULL`은 복제 트리 추적 목적이라면 의도 명시 주석 필요
3. SET_NULL FK에 대해 분기별 NULL row 카운트 알람(`COUNT(*) WHERE foo_id IS NULL`) 추가

---

## CASCADE 체인

### 통계
- 총 95곳 (32 파일)
- 사전 파악 37곳/7파일은 1차 모델만 — 실제로는 chainsight/marketpulse/macro/thesis/metrics 분산

### Stock 삭제 시 영향 범위 (가장 폭심도 높은 노드)

`stocks.Stock` CASCADE 직접 자식 = **25+ 테이블** (1차 자식만)

| 도메인 | 모델 (대표) |
|--------|------------|
| stocks | DailyPrice, WeeklyPrice, IncomeStatement, BalanceSheet, CashFlow, KoreanOverview, DailyStockSignal, SignalAccuracy, NewsArticle |
| users | Portfolio, WatchlistItem (to_field='symbol') |
| validation | CompanyBenchmarkDelta, CompanyCategoryScore, CompanyMetricLatest, CompanyNewsSummary, PeerPreset, PeerPreference |
| graph_analysis | CorrelationEdge×2 (a/b), PriceCache |
| sec_pipeline | SECFiling.symbol, SupplyChainEvidence.source_company (target은 SET_NULL) |
| chainsight | InsiderSignal, RevenueStructure, CapitalDNA, EventReaction, GrowthStage, Sensitivity, NarrativeTag, ChainProfile (모두 OneToOne — 1:1 삭제) |
| metrics | CompanyMetricBenchmark, MetricBaseline 등 |
| serverless | (간접 to_field='symbol') |

### 3단계 이상 연쇄 삭제

**체인 A — User 삭제 (4단계)**
```
User
 └─ Thesis (CASCADE, thesis/models/thesis.py:11)
     ├─ ThesisPremise (CASCADE, thesis.py:146)
     ├─ ThesisIndicator (CASCADE, indicator.py:10)
     │   └─ ThesisIndicatorReading (CASCADE, indicator.py:124)
     ├─ ThesisSnapshot (CASCADE, monitoring.py:10)
     ├─ ThesisAlert (CASCADE, monitoring.py:61) ─ indicator는 SET_NULL
     └─ ValidityRecord (CASCADE, learning.py:74)
```

**체인 B — User 삭제 (3단계)**
```
User
 └─ Watchlist (CASCADE, users/models.py:171)
     ├─ WatchlistItem (CASCADE, users/models.py:197)
     ├─ CorrelationMatrix (CASCADE, graph_analysis/models.py:20)
     ├─ CorrelationEdge (CASCADE, graph_analysis/models.py:70)
     │   └─ CorrelationAnomaly (CASCADE, graph_analysis/models.py:185)
     └─ GraphMetadata (CASCADE, graph_analysis/models.py:334)
```

**체인 C — Stock 삭제 (간접 폭심도)**
```
Stock
 ├─ SECFiling (CASCADE)
 │   └─ (SupplyChainEvidence는 source_document=RawDocumentStore의 CASCADE로도 연결)
 ├─ MetricDefinition 참조 → CompanyMetricBenchmark, CompanyMetricLatest, CompanyBenchmarkDelta
 │   (MetricDefinition.delete()는 별도 — 3-way fan-out)
 └─ ChainProfile (OneToOne) → SavedPath, NarrativeTag 등 chainsight 패밀리 전체
```

### 위험 평가

| 시나리오 | 위험도 | 비고 |
|---------|--------|------|
| `Stock.objects.filter(symbol='X').delete()` | 🔴 High | 25+ 테이블 동시 락 — 실수 시 복구 불가, raw SQL 가드 필요 |
| `User.objects.get(pk=N).delete()` | 🟡 Medium | thesis/portfolio/watchlist 4단계 전파 — 트랜잭션 시간 길어짐 |
| `Watchlist.delete()` | 🟡 Medium | graph_analysis 캐시 동시 삭제 — 재계산 비용 큼 |
| `MetricDefinition.delete()` | 🟡 Medium | validation+metrics 6개 테이블 fan-out |
| `RawDocumentStore.delete()` | 🟢 Low | sec_pipeline 내부 패밀리에 한정 |

### 권고

1. `stocks.Stock`에 대한 `delete()`는 **admin/management command에서만** 허용하고 코드 경로에서는 호출 금지 (현재 가드 없음)
2. User 삭제 시 GDPR 등 보존 의무 데이터(WalletSnapshot, AuditLog)는 이미 SET_NULL이므로 OK — 다만 Thesis CASCADE 4단계는 사용자 탈퇴 UX 검토 필요
3. CASCADE는 PostgreSQL ON DELETE가 아닌 Django ORM 레벨 — 대량 삭제 시 `_raw_delete` 또는 SQL TRUNCATE 검토

---

## Neo4j 동기화

### neo4j_dirty 플래그 사용 현황

| 앱 | 모델 | 필드 | 인덱스 |
|----|------|------|--------|
| sec_pipeline | SupplyChainEvidence | `neo4j_dirty`, `neo4j_synced_at` | ✅ `neo4j_dirty` index (models.py:111) |
| chainsight | RelationConfidence | `neo4j_dirty`, `neo4j_synced_at` | ✅ `neo4j_dirty` index (relation_discovery.py:143) |
| chainsight | CompanyChainProfile | `neo4j_dirty`, `neo4j_synced_at` | ✅ `db_index=True` (chain_profile.py:65) |
| news | NewsArticle | (없음 — `neo4j_synced` 필드 없음, views.py:1989 주석 확인) | ❌ Neo4j 측 존재 여부로 추론 |
| users/stocks | — | (마스터 데이터, 별도 sync 명령) | — |

**통일성**: 2026-04-29 audit P0 #9로 `synced_to_neo4j` → `neo4j_dirty` 단일 소스 통합 (chainsight/migrations/0008). 의미 반전(True=동기화 필요)으로 통일됨.

### 동기화 실패 시 재시도

| 위치 | 메커니즘 |
|------|---------|
| `chainsight/services/neo4j_sync.py:23-50` | `dirty_qs.filter(neo4j_dirty=True)` 조회 후 Neo4j write 성공 시에만 `neo4j_dirty=False` 토글 — 실패 시 다음 주기 재진입 |
| `chainsight/tasks/sync_tasks.py:104-138` | 동일 패턴 (CompanyChainProfile) |
| `sec_pipeline/tasks.py:345-444` | Phase C — 성공 row만 `update(neo4j_dirty=False, neo4j_synced_at=now)` |
| `chainsight/tasks/relation_tasks.py:382-402` | `queryset.update()`는 save() 미호출 — 수동으로 `neo4j_dirty=True` 토글 (주석에 명시) |

**강점**: 실패 시 row가 dirty 상태로 남아 idempotent 재시도 — 멱등성 보장 ✅
**약점**:
- 🟡 백로그 알림은 `sec_pipeline/quality_checks.py:92` 한 곳에만 (matched > 50건 임계치)
- 🟡 chainsight 측 백로그 임계치 알림 없음
- 🔴 Celery 재시도 정책(max_retries=3, backoff)이 명시된 곳 없음 — 5번째 시도 시 토픽이 살아있는지 확인 불가

### PG ↔ Neo4j 불일치 감지

🔴 **양방향 검증 메커니즘 부재**

| 검증 방향 | 존재 여부 | 비고 |
|----------|-----------|------|
| PG dirty=True && Neo4j 미존재 | ✅ 간접 (dirty=True가 곧 미반영 신호) | 단, dirty 토글이 누락된 경우 침묵 |
| PG dirty=False && Neo4j 미존재 (drift) | ❌ 없음 | Neo4j 노드를 외부에서 삭제했을 때 영원히 누락 |
| Neo4j 존재 && PG 미존재 (orphan) | ⚠ Neo4j 측에서만 (news_neo4j_sync.py:700, NewsEvent 한정) | RelationConfidence/ChainProfile은 검증 없음 |

**권고**:
1. 주간 `verify_neo4j_consistency` 태스크 신설 — `PG.count(neo4j_dirty=False)` vs `Neo4j.count(label)` 비교
2. 차이가 N% 초과 시 `neo4j_dirty=True` 일괄 재설정 + 알림 (autoheal)
3. Celery 태스크 재시도 정책 명시 — 현재 `tasks.py`에 backoff 설정 추적 어려움

---

## Unique 제약조건

### unique_together / UniqueConstraint 분포

| 앱 | 개수 | 대표 |
|----|------|------|
| serverless | 10 | MarketMover(date,type,symbol), ETFHolding(etf,stock,snapshot_date), InstitutionalHolding(cik,symbol,report_date), LLMExtractedRelation(source,target,type,source_id) |
| stocks | 4 | DailyPrice(stock,date), WeeklyPrice(stock,date), BalanceSheet(stock,period,year,quarter), 등 |
| users | 4 | Portfolio(user,stock), Watchlist(user,name), WatchlistItem(watchlist,stock), Interest(user,type,value) |
| graph_analysis | 4 | CorrelationMatrix/Edge/PriceCache/GraphMetadata 모두 (watchlist,date) 또는 (stock,date) |
| portfolio | 4 UniqueConstraint | MetricResult/Card/Comment/PercentileCache |
| news | 2 | NewsEntity(news,symbol), SentimentHistory(symbol,date) |
| validation | (FK to_field='symbol' 기반, 별도 unique 없음) | — |
| rag_analysis | 1 | BasketItem(basket,item_type,reference_id) |
| sec_pipeline | 1 | CompanyAlias(alias, context_sector) |

**평가**: 비교적 견고. 대부분 (symbol, date) 또는 (parent, child_id) 패턴으로 합리적.

### update_or_create race condition 위험

📊 **40+ 위치에서 사용 — 대부분 트랜잭션 가드 없음**

| 호출처 카테고리 | 위험도 |
|----------------|--------|
| `validation/services/*` (8건: metric, benchmark, preset, category) | 🔴 High — 일일 배치에서 동일 (symbol, metric_code) 동시 진입 가능 |
| `serverless/services/*` (15건: keyword, supply_chain, regulatory, patent, institutional) | 🟡 Medium — 대부분 단일 워커 |
| `chainsight/tasks/*` | 🟡 Medium — sync_tasks 직렬화 가정 |
| `stocks/tasks.py:99 (WeeklyPrice)`, `news/tasks.py:297 (SentimentHistory)` | 🔴 High — Celery 동시 워커 다수 |
| `macro/services/macro_service.py:410, 501` | 🟡 Medium |
| `graph_analysis/services/correlation_calculator.py:197, 290, 388` | 🟢 Low — 단일 매트릭스 빌더 |

**Django update_or_create 동작**:
- 내부적으로 `_for_write=True`로 `get()` → 없으면 `INSERT`, 있으면 `UPDATE`
- **default 격리 수준**(READ COMMITTED)에서 race 가능 — `get()` 결과 None인 두 워커가 동시 INSERT → IntegrityError 발생
- 일부 시점부터 Django는 자동 재시도하지만, **UniqueConstraint 없으면 중복 row 생성** 가능

**Unique 미설정 + update_or_create 사용** 의심 케이스 (추가 검증 필요):
- `serverless/services/regulatory_service.py:480, 521` — StockRelationship `update_or_create` 두 곳에서 호출, 모델은 `unique_together=[source_symbol, target_symbol, relationship_type]` ✅ 보호됨
- `validation/services/benchmark_calculator.py:238` — PeerMetricBenchmark — Unique 확인 필요
- `chainsight/services/seed_selection.py:411` — SeedSnapshot — Unique 확인 필요

**select_for_update 사용**: 48 파일에 atomic 사용 흔적이 있으나, **update_or_create 호출과 1:1 매칭이 거의 안 됨** — 대부분 transaction 외부에서 호출.

### 권고

1. 모든 `update_or_create` 호출 지점은 대응되는 `UniqueConstraint`/`unique_together` 보유 여부 1차 점검 — 없으면 race 시 중복 row
2. Celery 동시 워커가 같은 key로 진입할 수 있는 태스크(`stocks/tasks.py:99`, `news/tasks.py:297`)는 `transaction.atomic` + `select_for_update` 또는 task-level lock 도입
3. `validation/services/preset_generator.py`의 6개 `update_or_create`는 동시 트리거 시나리오 분석 필요 (사용자가 동시에 프리셋 갱신 시)

---

## 부록: 통계 요약

```
on_delete=models.SET_NULL    : 17곳 / 11 파일
on_delete=models.CASCADE     : 95곳 / 32 파일
on_delete=models.PROTECT     : 7곳 / 5 파일 (정상 — MetricDefinition, MarketRegime 등 마스터)
on_delete=models.DO_NOTHING  : 0곳
on_delete=models.SET_DEFAULT : 0곳

unique_together              : ~28곳
UniqueConstraint             : ~6곳 (portfolio 집중)
update_or_create             : ~50곳 (services + tasks)
get_or_create                : 48 파일에 존재 (전수 미카운트)

neo4j_dirty 사용 모델        : 3개 (SupplyChainEvidence, RelationConfidence, CompanyChainProfile)
neo4j_dirty 인덱스           : 3/3 ✅
synced_to_neo4j 잔존        : 0 (2026-04-29 0008 마이그레이션으로 제거 완료)

PG → Neo4j orphan 감지       : ⚠ Neo4j NewsEvent 한정
양방향 drift 감지            : ❌ 없음
```

---

## 다음 액션 우선순위 (감사자 관점)

| # | 우선순위 | 조치 |
|---|---------|------|
| 1 | 🔴 P0 | `stocks.Stock` 직접 `.delete()` 호출 가드 (코드 검색 + admin 권한 분리) |
| 2 | 🔴 P0 | `update_or_create` 사용 모델 전수 UniqueConstraint 매칭 점검 — 누락 시 추가 |
| 3 | 🔴 P1 | PG↔Neo4j 양방향 verify 태스크 신설 (주 1회) + drift 알림 |
| 4 | 🟡 P2 | SET_NULL 17곳에 대한 NULL row 카운트 모니터링 + rag_analysis 3건 CASCADE 재검토 |
| 5 | 🟡 P2 | Celery 태스크 race 의심 4곳에 transaction.atomic + select_for_update 적용 |
| 6 | 🟢 P3 | DECISIONS.md에 "Stock 삭제는 management command만 허용" 문서화 |

— 끝 —
