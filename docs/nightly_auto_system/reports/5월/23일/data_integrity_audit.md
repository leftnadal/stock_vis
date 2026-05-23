# 데이터 무결성 감사 보고서

**일자**: 2026-05-23
**대상**: stock_vis 전체 Django 앱 (read-only audit)
**스코프**: FK 정책 / CASCADE 체인 / Neo4j 동기화 / Unique 제약

---

## 요약 (위험도별 이슈 수)

| 위험도 | 카테고리 | 건수 | 비고 |
|--------|----------|------|------|
| 🔴 HIGH | SET_NULL 후 orphan 수집/cleanup 부재 | 6건 | 모든 SET_NULL 사용처에서 NULL 레코드 청소 잡 없음 |
| 🔴 HIGH | Stock 단일 노드 다중 CASCADE | 30+ FK | Stock 1건 삭제 시 폭발적 연쇄 (재무제표·뉴스·관계·그래프·검증) |
| 🔴 HIGH | Neo4j↔PG 불일치 감지 메커니즘 부재 | 2건 | "PG에는 있지만 Neo4j에는 없는 노드/엣지" 비교 잡 없음 |
| 🟡 MED | Neo4j sync 재시도 정책 약함 | 3건 | 모든 sync 태스크 `max_retries=1`, exponential backoff 없음 |
| 🟡 MED | update_or_create race condition | 69개 파일 | 대부분 unique 제약은 있으나 select_for_update 부재 |
| 🟡 MED | sec_pipeline SET_NULL + 자동 재매칭 신호 의존 | 1건 | ticker 매칭 실패 시 target_company NULL, 매칭 복구는 signals.py 의존 |
| 🟢 LOW | Stock FK to_field='symbol' 혼재 | 8건 | PK(id) 참조와 symbol 참조 혼재 — 마이그레이션 시 주의 |
| 🟢 LOW | PROTECT 사용처 (의도적 보호) | 7건 | portfolio·metrics·marketpulse — 좋은 패턴 |

**총 SET_NULL 사용처**: 18개 위치 (8개 파일)
**총 CASCADE 사용처**: 87+ 위치 (15+ 파일)
**총 UniqueConstraint/unique_together**: 25+ 위치 (12개 파일)

---

## FK orphan 위험

### 1. SET_NULL 사용처 전수 조사

요구사항에 명시된 "7곳, 3개 파일"보다 더 많이 발견됨 — 실제로는 **18개 위치, 8개 파일**.

| # | 파일 | 라인 | FK 대상 | related_name | orphan 처리 여부 |
|---|------|------|---------|--------------|------------------|
| 1 | `marketpulse/models/anomaly.py` | 25 | `marketpulse.MarketPulseNews` | `paired_anomaly_signals` | ❌ 없음 |
| 2 | `serverless/models.py` | 660 | `ScreenerPreset` | `alerts` | ❌ 없음 |
| 3 | `serverless/models.py` | 808 | `users.User` | `investment_theses` | ❌ 없음 (감사 의도적 보존) |
| 4 | `serverless/models.py` | 1409 | `users.User` (AdminActionLog) | (감사 로그) | ❌ 없음 (감사 의도적 보존) |
| 5 | `sec_pipeline/models.py` | 86 | `stocks.Stock` (target_company) | `sec_supply_chain_as_target` | 🟡 signals.py 재매칭 의존 |
| 6 | `thesis/models/thesis.py` | 70 | `news.NewsArticle` | `thesis_sources` | ❌ 없음 |
| 7 | `thesis/models/thesis.py` | 77 | `self` (copied_from) | `copies` | ❌ 없음 |
| 8 | `thesis/models/indicator.py` | 15 | `thesis.ThesisPremise` | `indicators` | ❌ 없음 |
| 9 | `thesis/models/monitoring.py` | 66 | `thesis.ThesisIndicator` | `alerts` | ❌ 없음 |
| 10 | `chainsight/models/news_event.py` | 54 | `self` (duplicate_of) | `duplicates` | ❌ 없음 |
| 11 | `portfolio/models.py` | 327 | `WalletSnapshot` | `analyses_at_time` | ❌ 없음 |
| 12 | `portfolio/models.py` | 732 | `AnalysisRun` (chat_sessions) | — | ❌ 없음 |
| 13 | `portfolio/models.py` | 831 | `AnalysisRun` (decisions) | — | ❌ 없음 |
| 14 | `rag_analysis/models.py` | 145 | `DataBasket` | `sessions` | ❌ 없음 |
| 15 | `rag_analysis/models.py` | 256 | `AnalysisSession` (usage_logs) | — | ❌ 없음 |
| 16 | `rag_analysis/models.py` | 263 | `AnalysisMessage` (usage_logs) | — | ❌ 없음 |
| 17 | `macro/models/indicators.py` | 310 | `EconomicIndicator` | `events` | ❌ 없음 |

**일반 결론**:

- **SET_NULL 후 정리 잡(예: NULL FK row 삭제, 또는 알람 발송)이 단 한 곳도 정의되어 있지 않다.**
- 대부분의 nullable FK는 "감사 로그 보존" 또는 "관계 끊겨도 본 row는 가치 있음"이라는 의도적 설계지만, **NULL 비율 모니터링이 없어 데이터 품질 저하를 감지할 수 없다**.
- `usage_logs`의 message/session SET_NULL은 메시지 삭제 시 토큰 비용 추적 row가 orphan 토큰으로 남는다 — 비용 합산 시 NULL 그룹을 별도 표기해야 한다.

### 2. 특히 위험한 케이스: `SupplyChainEvidence.target_company` (SET_NULL)

- `sec_pipeline/models.py:86`: 타깃 회사 Stock 삭제 시 NULL이 되어 `sync_dirty_to_neo4j` 필터(`target_company__isnull=False`)에서 자동 제외됨.
- 복구는 `sec_pipeline/signals.py:52`의 ticker 매칭 신호에 의존 — Stock 재생성 시점에만 트리거. **수동 백필 명령 부재.**
- `quality_checks.py:92`에서 `neo4j_dirty=True AND target_company__isnull=False` 개수만 카운트 → orphan(NULL) 개수는 모니터링되지 않음.

**권장**: nightly 잡으로 `SupplyChainEvidence.objects.filter(target_company__isnull=True, target_ticker_raw__in=resolved_tickers)` 재매칭 큐를 보고.

### 3. 자기참조 SET_NULL의 사이클 위험

- `chainsight/models/news_event.py:54` (`duplicate_of`): 마스터 뉴스 삭제 시 자식들이 모두 "is_duplicate=True지만 duplicate_of=NULL" 상태가 됨 → 중복 그래프 끊김.
- `thesis/models/thesis.py:77` (`copied_from`): 원본 삭제 시 복제본 출처 추적 불가.

**권장**: 이런 경우 SET_NULL이 아닌 PROTECT 또는 SET_DEFAULT("__deleted__" 표식) 검토.

---

## CASCADE 체인

### 1. Stock 노드 → 총 30+ 모델로 CASCADE 전파

`stocks.Stock`이 직접 CASCADE FK를 받는 곳 (직접 참조만):

| 앱 | 모델 | 파일 | on_delete |
|----|------|------|-----------|
| stocks | DailyPrice | `stocks/models.py:133` | CASCADE (to_field='symbol') |
| stocks | WeeklyPrice | `stocks/models.py:244` | CASCADE (to_field='symbol') |
| stocks | StockOverviewKo | `stocks/models.py:699` | CASCADE (OneToOne, PK=stock) |
| stocks | (재무제표 3종) | `stocks/models.py:756, 801` | CASCADE |
| stocks | EODSignalSnapshot | `stocks/models.py:888` | CASCADE (nullable) |
| users | Portfolio | `users/models.py:28` | CASCADE (to_field='symbol') |
| users | WatchlistItem | `users/models.py:198` | CASCADE (to_field='symbol') |
| validation | BenchmarkDelta, CategoryScore, MetricLatest, NewsSummary, PeerPreset (2개) | `validation/models/*` | CASCADE (6개) |
| graph_analysis | CorrelationEdge.stock_a, stock_b | `graph_analysis/models.py:77, 84` | CASCADE (2개) |
| graph_analysis | StockPriceCache | `graph_analysis/models.py:291` | CASCADE |
| chainsight | InsiderSignal, RevenueStructure, CapitalDNA, EventReaction, GrowthStage, Sensitivity, NarrativeTag, ChainProfile | `chainsight/models/*` | CASCADE (8개) |
| sec_pipeline | RawDocumentStore, SupplyChainEvidence.source_company, BusinessModelSnapshot.symbol | `sec_pipeline/models.py:25, 82, 161` | CASCADE (3개) |
| metrics | MetricSnapshot | `metrics/models/metric_snapshot.py:19` | CASCADE |
| marketpulse | News (2개) | `marketpulse/models/news.py:90, 95` | CASCADE |
| news | NewsArticle 관련 (2개) | `news/models.py:225, 312` | CASCADE |
| serverless | StockKeyword, ETFHolding 등 (4+) | `serverless/models.py:371, 647, 754, 1078` | CASCADE |
| portfolio | 4종 | `portfolio/models.py:88, 391...` | PROTECT (✅ 안전) |
| chainsight | NewsEvent | `chainsight/models/news_event.py:23` | PROTECT (✅ 안전) |

**Stock 1건 삭제 시 영향 추정** (단일 ticker, 5년 데이터 기준):

- DailyPrice: ~1,260행
- 재무제표: ~60행 (분기 4*5*3 + 연간 5*3)
- EODSignalSnapshot: ~1,260행
- News 관련: 수십~수백 행
- Chainsight/Validation/Metrics: 각 1~50행
- **CorrelationEdge: O(N) — N = watchlist의 다른 종목 수, 날짜별로 폭발**

→ **총 수천~수만 행이 한 트랜잭션에서 삭제됨**. 운영 중 Stock 삭제는 사실상 금기.

### 2. 2단계 이상 CASCADE 체인

| 체인 | 영향 |
|------|------|
| `User → Watchlist → WatchlistItem → (Stock)` | User 삭제 시 N개 Watchlist + M개 Item 동시 삭제 |
| `User → Watchlist → CorrelationMatrix + CorrelationEdge` | User 삭제 시 그래프 데이터 전체 삭제 (관계자별 1500+ row) |
| `User → Portfolio → AnalysisRun → MetricResult, CardResult, CommentResult, ChatSession, Decision` | 4단계 CASCADE — User 1명 삭제 시 portfolio/models 12개 FK 연쇄 |
| `RawDocumentStore → SupplyChainEvidence → (Neo4j edge orphan)` | 문서 삭제 시 PG evidence는 사라지지만 **Neo4j 엣지는 그대로 남음** — 동기화 누락 |
| `Stock → CompanyChainProfile → (Neo4j :Stock 속성 stale)` | Stock 삭제 시 PG profile은 사라지지만 Neo4j 노드 속성은 stale 상태 유지 |
| `Stock → SP500Constituent → (외부 종속 잡 영향)` | aggregate_chain_profiles, sync_indicators 등이 SP500 기준으로 동작 |

### 3. PROTECT 사용처 (의도적 안전장치) — ✅

- `chainsight/models/news_event.py:23` (Stock PROTECT) — 뉴스 이벤트는 Stock 삭제 차단
- `metrics/models/metric_snapshot.py:11` (Definition PROTECT)
- `marketpulse/models/snapshot.py:51`
- `portfolio/models.py` 4건 — RV2-b 정책에 따라 Stock 삭제 차단

**권장**: stocks의 직접 자식 중 `Stock`이 비활성화될 수 있는 핵심 데이터(DailyPrice 등)는 그대로 CASCADE 유지, 그러나 **Stock 삭제 자체를 admin에서 차단**하는 가드 추가 권장.

---

## Neo4j 동기화

### 1. neo4j_dirty 플래그 사용 현황 (단일 소스)

audit P0 #9에 따라 `synced_to_neo4j` 필드는 폐기, `neo4j_dirty=True`(동기화 필요)로 단일화됨.

| 모델 | 파일 | dirty 자동 토글 |
|------|------|------------------|
| `RelationConfidence` | `chainsight/models/relation_discovery.py:130` | ✅ save() override (line 158) |
| `CompanyChainProfile` | `chainsight/models/chain_profile.py:65` | 🟡 update_or_create save() 의존 |
| `SupplyChainEvidence` | `sec_pipeline/models.py:100` | 🟡 update_or_create save() 의존 |

**문제 패턴**: `QuerySet.update()`는 `save()`를 호출하지 않아 `neo4j_dirty` 자동 토글이 안 됨.
이미 인지하여 수동 처리되는 위치들:

- `chainsight/tasks/relation_tasks.py:388, 395, 402` — 명시적으로 `.update(..., neo4j_dirty=True)` 추가
- `sec_pipeline/ticker_matcher.py:99` — `evidence.save(update_fields=['target_company', 'neo4j_dirty'])`

**놓칠 수 있는 곳**: 향후 bulk_update / queryset.update 추가 시 누락 가능 → **테스트로 강제하는 가드 없음**.

### 2. 동기화 실패 시 재시도 메커니즘

| 태스크 | 재시도 정책 | 실패 처리 |
|--------|------------|----------|
| `aggregate_chain_profiles` | `max_retries=1` | try/except로 개별 ticker swallow + log |
| `sync_profiles_to_neo4j` | `max_retries=1` | try/except per row, `neo4j_dirty` 그대로 둠 → 다음 실행 자동 재시도 |
| `sync_relations_to_neo4j` | `max_retries=1` | `sync_dirty_relations()` 위임 |
| `sync_dirty_to_neo4j` (sec_pipeline) | `max_retries=1` | Phase B에서 row별 try/except, `synced_ids`에 누락 시 다음 실행 재처리 |
| `chainsight/tasks/neo4j_dirty_sync_tasks.py` | (스텁 19줄) | 위임 호출만 |

**평가**:

- ✅ "dirty=True 상태로 두면 다음 실행에서 자동 재시도"는 잘 설계됨 (idempotent).
- ❌ Celery 레벨의 `max_retries=1` + exponential backoff 없음 → 일시적 Neo4j 장애(예: 네트워크 1분 단절)도 즉시 실패.
- ❌ 영구 실패 감지 부재 — 동일 row가 N회 연속 실패해도 알람 없음.
- ❌ `synced_at`이 X시간 이상 지난 dirty row 알람 없음.

**권장**:

```python
@shared_task(bind=True, max_retries=3, autoretry_for=(Neo4jError,),
             retry_backoff=True, retry_jitter=True, soft_time_limit=1800)
```

추가로 nightly에서:
```sql
SELECT COUNT(*) FROM sec_supply_chain_evidence
WHERE neo4j_dirty=true AND created_at < NOW() - INTERVAL '24 hours';
```
이 1000건 이상이면 알람.

### 3. PG↔Neo4j 불일치 감지 방법 — **현재 부재**

검색 결과 다음 패턴이 **존재하지 않음**:

- "PG에는 있고 Neo4j에는 없는 노드/엣지 카운트" 비교 잡
- "Neo4j에는 있고 PG에는 없는 (orphan) 노드/엣지" 청소 잡
- `quality_checks.py`는 `neo4j_dirty` 카운트만 함 → 실제 Neo4j 쿼리하지 않음
- `sync_dirty_to_neo4j`에서 DELETE 후 CREATE 사이에 트랜잭션 없음 (Neo4j 세션 분리) → 중간 실패 시 엣지 소실 가능

**권장 점검 잡 (신규)**:

```python
def check_pg_neo4j_consistency():
    pg_count = SupplyChainEvidence.objects.filter(
        neo4j_dirty=False, target_company__isnull=False
    ).count()
    neo4j_count = repo.run_query(
        "MATCH ()-[r]->() WHERE r.source='sec_10k' RETURN count(r) AS c"
    )[0]['c']
    drift = abs(pg_count - neo4j_count)
    if drift > pg_count * 0.05:  # 5% 이상 drift
        alert(f"PG↔Neo4j drift: pg={pg_count}, neo4j={neo4j_count}")
```

### 4. `sync_dirty_to_neo4j`의 트랜잭션 경계 위험

`sec_pipeline/tasks.py:362-446`:

- Phase A: PG `select_for_update(skip_locked=True)` + dict 복사 (트랜잭션 안)
- Phase B: Neo4j DELETE + CREATE (트랜잭션 밖)
- Phase C: 성공 row만 `neo4j_dirty=False`로 토글

**경합 시나리오**:
1. Phase B 중 DELETE 성공, CREATE 직전 워커 죽음 → Neo4j 엣지 손실, `neo4j_dirty=True` 유지 → 다음 실행 시 재CREATE → ✅ 복구됨.
2. Phase B CREATE 성공, Phase C 직전 워커 죽음 → 엣지 정상, `neo4j_dirty=True` 유지 → 다음 실행 시 DELETE+CREATE 재실행 → ✅ idempotent.
3. CREATE에서 `synced_at: datetime()`이 매번 갱신 → row 동일성 비교 시 노이즈.

대체로 안전하나 **타임아웃 안에 1배치(500건)가 끝난다는 가정**에 의존. SOFT_TIME_LIMIT=300초 = row당 0.6초 미만 필요. 큰 배치 시 위험.

---

## Unique 제약조건

### 1. unique_together / UniqueConstraint 핵심 목록

| 앱 | 모델 | 키 | 비고 |
|----|------|-----|------|
| stocks | DailyPrice | `(stock, date)` | OK |
| stocks | WeeklyPrice | `(stock, date)` | OK |
| stocks | BalanceSheet/IncomeStatement/CashFlow | `(stock, period_type, fiscal_year, fiscal_quarter)` | OK |
| users | Portfolio | `(user, stock)` | OK |
| users | Watchlist | `(user, name)` | OK |
| users | WatchlistItem | `(watchlist, stock)` | OK |
| users | Interest | `(user, interest_type, value)` | OK |
| news | NewsEntity | `(news, symbol)` | OK |
| news | SentimentHistory | `(symbol, date)` | OK |
| serverless | MarketMover | `(date, mover_type, symbol)` | OK |
| serverless | VolatilityBaseline | `(symbol, date)` | OK |
| serverless | StockKeyword | `(symbol, date)` | OK |
| serverless | SectorPerformance | `(date, sector)` | OK |
| serverless | CorporateAction | `(symbol, date, action_type)` | OK |
| serverless | StockRelationship | `(source_symbol, target_symbol, relationship_type)` | OK |
| serverless | CategoryCache | `(symbol, date)` | OK |
| serverless | ETFHolding | `(etf, stock_symbol, snapshot_date)` | OK |
| serverless | ThemeMatch | `(stock_symbol, theme_id)` | OK |
| serverless | LLMExtractedRelation | `(source, target, relation_type, source_id)` | OK |
| serverless | InstitutionalHolding | `(institution_cik, stock_symbol, report_date)` | OK |
| sec_pipeline | CompanyAlias | `(alias, context_sector)` | 🟡 (context_country는 키에서 빠짐 — 동일 alias가 다른 국가에서 충돌 가능) |
| graph_analysis | CorrelationMatrix | `(watchlist, date)` | OK |
| graph_analysis | CorrelationEdge | `(watchlist, stock_a, stock_b, date)` | 🟡 (stock_a/stock_b 정규화 없음 — A,B와 B,A 중복 저장 가능) |
| graph_analysis | StockPriceCache | `(stock, date)` | OK |
| graph_analysis | Metadata | `(watchlist, date)` | OK |
| portfolio | WalletStock | `(wallet, stock)` | OK |
| portfolio | MetricResult | `(analysis_run, stock, metric_id)` | OK |
| portfolio | Card | `(analysis_run, priority)` | OK |
| portfolio | Comment | `(analysis_run, stock, metric_id)` | OK |
| portfolio | PercentileCache | `(metric_id, industry_code, date)` | OK |
| rag_analysis | BasketItem | `(basket, item_type, reference_id)` | OK |

### 2. 잠재적 결함 케이스

#### 🟡 CorrelationEdge 정규화 결여

`graph_analysis/models.py:127`:
```python
unique_together = [['watchlist', 'stock_a', 'stock_b', 'date']]
```

`(AAPL, MSFT)`와 `(MSFT, AAPL)`이 모두 저장 가능. `correlation_calculator.py`가 항상 sorted 보장한다면 OK, 그러나 unique 키 자체로는 강제 안 됨.

**권장 검증**:
```sql
SELECT COUNT(*) FROM graph_correlation_edge
WHERE stock_a_id > stock_b_id;  -- 0이어야 함
```

#### 🟡 CompanyAlias의 country 누락

`sec_pipeline/models.py:295`: `unique_together = [('alias', 'context_sector')]` — 동일 sector 내 미국 회사와 캐나다 회사가 같은 alias를 가지면 충돌.

### 3. update_or_create의 race condition

`update_or_create`는 **69개 파일에서 사용**. 대부분은 unique_together로 보호되지만, Django의 `update_or_create`는 내부적으로:

1. SELECT
2. 없으면 INSERT (IntegrityError catch → retry SELECT/UPDATE)

**고동시 환경에서 위험한 사용처**:

- `sec_pipeline/tasks.py:314` — RelationConfidence update_or_create, 다중 워커 실행 시 동일 (sym_a, sym_b, type) 경합 가능.
- `chainsight/tasks/relation_tasks.py:291` — 유사 패턴.
- `chainsight/tasks/sync_tasks.py:84` — `CompanyChainProfile.update_or_create(symbol=stock, ...)`, 단일 워커이지만 다른 잡(`update_or_create`도 보유)과 경합 가능.
- `serverless/tasks.py`, `news/tasks.py`, `marketpulse/tasks/news.py` — 대량 INSERT 패턴, 동일 키 동시 INSERT 시 `IntegrityError`로 한 쪽 실패.

**Django 기본 동작**:
- `update_or_create`는 IntegrityError를 catch하고 재시도하지만, **PostgreSQL transaction은 IntegrityError 발생 시 abort됨** → 외부 트랜잭션 안에서 사용 시 전체 트랜잭션이 깨질 위험.

**권장**:

1. 다중 워커가 동일 키를 쓸 수 있는 곳은 `select_for_update()` 또는 `INSERT ... ON CONFLICT` (django-pg-bulk-update).
2. `sync_dirty_to_neo4j`처럼 이미 `select_for_update(skip_locked=True)`를 쓰는 패턴을 다른 sync 잡에도 확산.

### 4. unique 제약 부재 의심 케이스

| 모델 | 위치 | 의심 사유 |
|------|------|----------|
| `SupplyChainEvidence` | `sec_pipeline/models.py` | source_document + source_company + target_company + rel_type 키 부재 — 같은 문서에서 동일 관계 중복 추출 가능 |
| `MarketPulseAnomaly` | `marketpulse/models/anomaly.py` | unique 키 부재 (확인 필요) |
| 다수 `AnalysisRun` 자식 모델 | `portfolio/models.py` | 일부는 UniqueConstraint 있음, 일부는 없음 — 일관성 점검 필요 |

---

## 권장 후속 조치 (우선순위)

### 🔴 P0 (1주 내)

1. **PG↔Neo4j drift 감지 잡 추가** (`check_pg_neo4j_consistency`) — nightly 실행, 5% drift 알람.
2. **Neo4j sync 태스크 재시도 정책 강화** — `max_retries=3 + retry_backoff=True + autoretry_for`.
3. **24시간 이상 stuck된 `neo4j_dirty=True` row 알람** — `quality_checks.py`에 추가.
4. **Admin에서 Stock 삭제 차단 가드** — 30+ CASCADE 폭발 위험.

### 🟡 P1 (2주 내)

5. **SET_NULL orphan 카운트 모니터링** — 각 SET_NULL FK 대상의 NULL 비율을 metrics로 노출.
6. **CorrelationEdge 정규화 검증 SQL** — `stock_a_id > stock_b_id` 0건 확인.
7. **update_or_create 경합 위험 위치 5건에 select_for_update 추가** — sec_pipeline, chainsight relation_tasks 우선.
8. **CompanyAlias unique key에 context_country 포함 여부 결정**.

### 🟢 P2 (백로그)

9. **자기참조 SET_NULL (`duplicate_of`, `copied_from`) PROTECT 전환 검토**.
10. **bulk_update/queryset.update에서 neo4j_dirty 누락 감지 테스트** — pytest로 강제.

---

**감사자 노트**: 본 보고서는 코드 정적 분석 기반이며 실제 PG/Neo4j 데이터 카운트는 수행하지 않았다. P0의 drift 감지 잡을 먼저 추가하여 **현재 상태의 baseline**을 확보한 뒤, 다른 정리 작업을 진행하는 것을 권장한다.
