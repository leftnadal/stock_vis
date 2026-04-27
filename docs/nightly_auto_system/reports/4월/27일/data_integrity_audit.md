# 데이터 무결성 감사 보고서

작성일: 2026-04-27
대상 브랜치: `feature/chainsight-graph-v2`
방식: 정적 분석 (코드 수정 없음, 읽기 전용)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 이슈 수 | 핵심 카테고리 |
|--------|---------|--------------|
| 🔴 **High** | 4 | (1) `RelationConfidence.save()` 무조건 `neo4j_dirty=True`로 덮음 / (2) `update_or_create`가 `select_for_update` 없이 호출 (30+ 곳) / (3) PG↔Neo4j 무결성 감사 메커니즘 부재 / (4) `synced_to_neo4j`와 `neo4j_dirty` 이중 플래그 (DECISIONS의 단일 플래그 원칙 위반 의심) |
| 🟠 **Medium** | 5 | (1) Stock CASCADE 영향 범위 ≥ 30개 모델 (백업/감사 로그도 함께 삭제) / (2) `SET_NULL` 17곳 중 orphan PG 정리 잡 부재 / (3) `sec_pipeline.SupplyChainEvidence.target_company` SET_NULL 후 `target_company_name`만 남는 데이터 보존이 운영 정책에 명문화되지 않음 / (4) Celery 동기화 태스크 `max_retries=2`로 비교적 짧음 (`run_neo4j_dirty_sync`) / (5) `RawDocumentStore.delete()` → `SupplyChainEvidence`/`BusinessModelEvidence` CASCADE 동시 삭제 (재추출 비용 큼) |
| 🟡 **Low** | 3 | (1) `chainsight.ChainNewsEvent`만 `PROTECT` 사용 — Stock 삭제 시 IntegrityError 가능 / (2) `unique_together` 위주 사용 (Django 권장: `UniqueConstraint`) / (3) `news_neo4j_sync`만 orphan 노드 cleanup 존재, 다른 동기화는 없음 |

전수 조사 통계:
- `on_delete` 사용처 총 **122곳** (122 = CASCADE 95 + SET_NULL 17 + PROTECT 7 + 기타 3)
- `update_or_create` 사용처 **30+ 곳**
- `unique_together` 선언 **22+ 곳** / `UniqueConstraint` 선언 **4곳** (portfolio 전용)
- `neo4j_dirty` 플래그: `chainsight.RelationConfidence` + `sec_pipeline.SupplyChainEvidence` 두 모델

---

## FK orphan 위험

### SET_NULL 사용처 전체 (17곳, 11개 파일)

| 파일:Line | 모델.필드 | 참조 | 위험도 | 비고 |
|-----------|-----------|------|--------|------|
| `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | Stock | 🟠 | `target_company_name`(text)만 남음 — 의도된 설계 (소스 기업의 사업관계 evidence는 보존). **Neo4j edge는 자동 삭제되지 않음 (별도 정리 잡 없음)** |
| `serverless/models.py:660` | `ScreenerAlert.preset` | ScreenerPreset | 🟢 | preset 삭제 후 `filters_json`으로 동작 가능 — 설계 의도와 일치 |
| `serverless/models.py:808` | `InvestmentThesis.user` | User | 🟠 | 사용자 탈퇴 후에도 테제 보존. 단 user가 `null`인 테제의 RLS/노출 정책이 코드에 보이지 않음 |
| `serverless/models.py:1409` | `AdminActionLog.user` | User | 🟢 | 감사 로그는 `user=null` 허용이 정상 |
| `rag_analysis/models.py:145` | `AnalysisSession.basket` | DataBasket | 🟠 | basket 삭제 후 `exploration_path` JSONField 안의 `entity_id` 참조는 끊어짐. 세션 내 LLM 컨텍스트 일관성 깨질 수 있음 |
| `rag_analysis/models.py:256, 263` | `UsageLog.session/message` | Session/Message | 🟢 | 비용 추적 보존 — 의도와 일치 |
| `chainsight/models/news_event.py:54` | `ChainNewsEvent.parent` | self | 🟢 | 셀프 FK, parent 삭제 시 child 보존 — OK |
| `macro/models/indicators.py:297` | `EconomicEvent.related_indicator` | EconomicIndicator | 🟢 | OK |
| `portfolio/models.py:327` | `AnalysisRun.wallet_snapshot_at_execution` | WalletSnapshot | 🟢 | OK |
| `portfolio/models.py:732` | `ChatSession.analysis_run` | AnalysisRun | 🟢 | "느슨한 연결" 주석 — OK |
| `portfolio/models.py:831` | `Decision.context_analysis_run` | AnalysisRun | 🟢 | OK |
| `thesis/models/monitoring.py:66` | `Alert.indicator` | ThesisIndicator | 🟠 | indicator가 사라진 alert는 디버깅 시 root cause 추적 어려움 — `target_id` 텍스트 필드만 남음 |
| `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | ThesisPremise | 🟠 | premise 삭제 후 indicator 고아화 가능 — Thesis 빌더 일관성 검토 필요 |
| `thesis/models/thesis.py:70` | `Thesis.source_news` | NewsArticle | 🟢 | OK |
| `thesis/models/thesis.py:77` | `Thesis.copied_from` | self | 🟢 | OK |
| `marketpulse/models/anomaly.py:50` | `AnomalySignal.paired_news` | MarketPulseNews | 🟢 | OK |

### Orphan 레코드 정리 로직 — **존재하지 않음 (PG)**

조사 결과:
- `grep "orphan|cleanup_orphan|delete_orphan"` 검색 결과 **PG 정리 잡 없음**
- 단 1건만 존재: `news/services/news_neo4j_sync.py:700` — Neo4j(그래프DB) 고립 NewsEvent 노드만 cleanup. PG의 SET_NULL 후 처리는 없음
- 즉, **`SET_NULL`된 17개 컬럼 중 어느 것도 정기적인 무결성 정리(예: `null` 비율 모니터링, 고아 레코드 보고)가 자동화되어 있지 않음**

권장사항 (참고):
- `target_company__isnull=True`로 남은 `SupplyChainEvidence` 누적 모니터링
- `user__isnull=True`인 `InvestmentThesis` / `ScreenerPreset` 노출 정책 명문화

---

## CASCADE 체인

### CASCADE 사용처 (95곳, 14개 파일)

총 **95개** `on_delete=models.CASCADE` 선언. 파일별:

| 파일 | CASCADE 수 |
|------|-----------|
| `portfolio/models.py` | 13 |
| `thesis/models/*.py` | 12 |
| `chainsight/models/*.py` | 11 |
| `serverless/models.py` | 9 |
| `validation/models/*.py` | 8 |
| `stocks/models.py` | 6 |
| `sec_pipeline/models.py` | 6 |
| `graph_analysis/models.py` | 8 |
| `metrics/models/*.py` | 5 |
| `users/models.py` | 5 |
| `rag_analysis/models.py` | 5 |
| `news/models.py` | 2 |
| `macro/models/*.py` | 4 |
| `marketpulse/models/news.py` | 2 |

### Stock 삭제 시 영향 범위 (직접 FK 참조 ≥ 28개 모델)

```
stocks.Stock (DELETE)
├─ stocks.DailyPrice (CASCADE, to_field=symbol) ─────────── 가격 데이터 전부
├─ stocks.WeeklyPrice (CASCADE, to_field=symbol)
├─ stocks.MonthlyPrice (CASCADE, to_field=symbol)
├─ stocks.StockOverviewKorean (CASCADE, OneToOne)
├─ stocks.[BalanceSheet|IncomeStatement|CashFlowStatement] (CASCADE) ── 재무제표 전부
├─ stocks.StockNews (CASCADE, null=True) ───────────── 뉴스도 함께 삭제
├─ stocks.<line 888> StockNews                                 (재게시 외에는 복구 불가)
│
├─ users.Portfolio (CASCADE) ─→ users.<PortfolioItem 추정 자동>
├─ users.WatchlistItem (CASCADE)                  (Watchlist는 user CASCADE만)
│
├─ chainsight.ChainCompanyProfile (CASCADE, primary_key=symbol)
├─ chainsight.NarrativeTag (CASCADE, primary_key=symbol)
├─ chainsight.SensitivityScore (CASCADE, primary_key=symbol)
├─ chainsight.GrowthStage (CASCADE, primary_key=symbol)
├─ chainsight.EventReaction (CASCADE)
├─ chainsight.CapitalDNA (CASCADE, primary_key=symbol)
├─ chainsight.RevenueStructure (CASCADE, primary_key=symbol)
├─ chainsight.InsiderSignal (CASCADE, primary_key=symbol)
├─ chainsight.ChainNewsEvent (PROTECT) ───── ⚠️ Stock.delete()를 차단함! IntegrityError 발생
│
├─ sec_pipeline.RawDocumentStore (CASCADE)
│   ├─ sec_pipeline.SupplyChainEvidence (CASCADE) ──────── 3단계
│   └─ sec_pipeline.BusinessModelEvidence (CASCADE)        3단계
├─ sec_pipeline.BusinessModelSnapshot (CASCADE)
│
├─ validation.PeerPreset (CASCADE)
├─ validation.UserPeerPreference (CASCADE)
├─ validation.NewsSummary (CASCADE, primary_key=symbol)
├─ validation.MetricLatest (CASCADE)
├─ validation.CategoryScore (CASCADE)
├─ validation.BenchmarkDelta (CASCADE)
│
├─ metrics.IndustryMetricBenchmark (CASCADE, to_field=symbol)
├─ metrics.PeerMetricBenchmark (CASCADE)
├─ metrics.MetricSnapshot (CASCADE, to_field=symbol)
│
└─ portfolio.* (다수 — Portfolio→AnalysisRun→MetricResult/DiagnosticCard/ChatSession→Message 까지 4단계)
```

### 3단계 이상 연쇄 삭제 (4건 식별)

1. **Portfolio 체인 (4단계)**:
   `Stock → portfolio.AnalysisRun (다수 FK) → MetricResult/DiagnosticCard/ChatSession → Message`
   → 단, `DiagnosticCard.target_stock`은 `PROTECT`라서 Stock 삭제 자체가 차단됨 (긍정적)

2. **SEC 파이프라인 체인 (3단계)**:
   `Stock → RawDocumentStore (CASCADE) → SupplyChainEvidence + BusinessModelEvidence`
   → `RawDocumentStore` 삭제는 LLM 추출 결과까지 전부 삭제. **재추출 비용이 크므로 운영상 위험**

3. **Thesis 체인 (3단계)**:
   `User → Thesis (CASCADE) → ThesisIndicator (CASCADE) → ThesisAlert (CASCADE)`
   → User 삭제 시 알림 이력까지 전부 사라짐. 감사/회고 기능에 영향 가능

4. **Chainsight SavedPath 체인 (2단계, 참고)**:
   `User → SavedPath → SavedPathAction` — 단순 2단계지만 사용자 데이터 손실

### 🔴 PROTECT/CASCADE 충돌 — Stock 삭제 시 IntegrityError

`chainsight/models/news_event.py:23`: `ChainNewsEvent.symbol = ForeignKey(..., on_delete=PROTECT, to_field='symbol')`

→ Stock에 ChainNewsEvent가 존재하면 Stock 삭제는 무조건 IntegrityError. 다른 28개 CASCADE 모델은 같이 삭제되지 않음. 즉 **Stock 삭제 자체가 사실상 차단**되며, 운영자가 Stock을 정리하려면 ChainNewsEvent를 먼저 비워야 함. 이 사실이 admin/문서에 명시되어 있는지 별도 확인 필요.

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 사용 현황

| 모델 | 플래그 | 정책 | 비고 |
|------|--------|------|------|
| `chainsight.RelationConfidence` | **`neo4j_dirty` + `synced_to_neo4j` 둘 다 사용** | save()에서 무조건 `neo4j_dirty=True` 세팅 | 🔴 DECISIONS의 "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용" 원칙(`sec_pipeline/models.py:99`)과 불일치. 의도라면 운영 결정 명문화 필요 |
| `sec_pipeline.SupplyChainEvidence` | `neo4j_dirty`만 사용 | 모델에 명시: "synced_to_neo4j 필드 금지" | OK — 단일 플래그 패턴 |

### 동기화 태스크 비교

| 작업 | 위치 | retry 정책 | 트랜잭션 보호 | 비고 |
|------|------|------------|--------------|------|
| `chainsight.run_neo4j_dirty_sync` | `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` | `max_retries=2, default_retry_delay=60` | `transaction.atomic` 없음 | 🟠 sync 도중 PG/Neo4j 분기 시 재시도 부족 가능 |
| `sec_pipeline.sync_dirty_to_neo4j` | `sec_pipeline/tasks.py:340-449` | (별도 명시 없음, 함수 내부) | `transaction.atomic + select_for_update(skip_locked=True)` BATCH=500 | 🟢 모범 패턴: 2-Phase, row lock, dynamic edge type, DELETE+CREATE |

### 🟢 좋은 패턴: `sec_pipeline.sync_dirty_to_neo4j`

```python
# Phase A: PG row lock + dict 복사
with transaction.atomic():
    dirty_qs = (
        SupplyChainEvidence.objects
        .filter(neo4j_dirty=True, target_company__isnull=False)
        .select_for_update(skip_locked=True)[:BATCH_SIZE]
    )
# Phase B: Neo4j 동기화 (try/except + synced_ids 누적)
# Phase C: PG queryset.update(neo4j_dirty=False)  ← save()금지 (덮어쓰기 방지)
```

대비:`chainsight.sync_dirty_relations`은 lock 없이 `iterator(chunk_size=100)`만 사용. 동시 실행 시 같은 row 처리 충돌 가능.

### 동기화 실패 시 재시도 메커니즘

- **Cell 단위 try/except**: 한 row 실패해도 다음 row 진행 (둘 다 동일)
- **Task 단위 재시도**: `chainsight`는 Celery `max_retries=2`만, `sec_pipeline`은 Celery 데코레이터에 retry 옵션 표시 안 됨 (별도 확인 필요)
- 실패한 row는 `neo4j_dirty=True`로 남으므로 **다음 주기에 자연 재처리** — 이 패턴 자체는 OK

### 🔴 PG ↔ Neo4j 불일치 감지 — **메커니즘 부재**

조사 결과:
- PG `neo4j_dirty=False` AND Neo4j 엣지 부재 (어느쪽이 누락됐는지 감지 불가)
- PG에 row가 없는데 Neo4j 엣지가 남아있는 경우 (orphan edge) — `news_neo4j_sync.py:700` 외에는 cleanup 없음
- **정합성 검증 잡 없음** — `intelligence.py:97`이 `neo4j_dirty=False` 카운트만 보고함 (실제 Neo4j 측 카운트와 비교 안 함)

권장 감지 패턴:
- 야간 잡: PG `(symbol_a, symbol_b, relation_type)` vs Neo4j `MATCH (a)-[r]->(b)` count 비교
- `neo4j_synced_at`이 N일 이상 stale인 row 알림

---

## Unique 제약조건

### 선언 현황

- `unique_together`: 22+곳 (Django 4+ 비권장이지만 동작은 정상)
  - `metrics/models/benchmark.py`: 2곳 (industry/peer benchmark)
  - `metrics/models/metric_snapshot.py`: 1곳 (`symbol+fiscal_year+metric_code`)
  - `serverless/models.py`: 11곳 (MarketMover, ETFHolding, ThemeMatch, InstitutionalHolding, LLMExtractedRelation 등)
  - `rag_analysis/models.py:111`: BasketItem 중복 방지
  - `users/models.py`: WatchlistItem (테스트로 검증 — `tests/unit/users/test_watchlist.py:624`)
  - 기타: chain news event, business model evidence

- `UniqueConstraint` (Django 권장): 4곳 — **portfolio/models.py 전용**
  - `MetricResult`: `analysis_run + stock + metric_id`
  - `DiagnosticCard`: `analysis_run + priority`
  - 추가 2곳

🟡 권장: `unique_together` → `UniqueConstraint` 전환 (Django 5.x에서 deprecated 경고).

### `update_or_create` 사용 시 race condition 가능성

검색 결과 **30+곳** 사용. 위험도별:

| 위치 | 트랜잭션 보호 | 위험도 | 비고 |
|------|--------------|--------|------|
| `api_request/stock_service.py` (8곳: Stock, DailyPrice, BalanceSheet 등) | 일부 `with transaction.atomic()` | 🟠 | UNIQUE 제약 의존 → DB 레벨 정합성은 OK, 그러나 IntegrityError 처리 코드 미확인 |
| `serverless/services/*` (15+곳) | 일부 `transaction.atomic` 데코레이터 (`supply_chain_service.py:278`, `relationship_keyword_enricher.py:340` 등) | 🟠 | 동시 실행되는 Celery 태스크 사이에서 race 가능 — `update_or_create`는 Django 내부적으로 `get` → 없으면 `create` → IntegrityError 시 `get` 재시도 (`select_for_update` 미적용) |
| `serverless/services/data_sync.py:53` | `@transaction.atomic` 데코레이터 | 🟢 | OK |
| `metrics/management/commands/seed_metric_definitions.py:518` | 명시적 lock 없음 (관리 커맨드 1회 실행) | 🟢 | 단발성, 충돌 없음 |
| `serverless/tasks.py:393, 1425` (StockKeyword, StockRelationship) | 명시적 보호 없음 | 🟠 | 같은 키 동시 호출 시 race — UNIQUE 위반 시 재시도 필요 |

### 🔴 핵심 위험 패턴

`update_or_create`의 Django 구현은 다음과 같음:
1. `get()` 시도
2. 없으면 `save()` 시도 → IntegrityError 시
3. `get()` 재시도 (1회)
4. 그래도 실패하면 예외 전파

→ **두 개 워커가 동시에 같은 키로 호출하면 한쪽이 IntegrityError 후 정상 복구**되지만, defaults가 다르면 **마지막에 들어온 값이 보존되지 않을 수 있음** (PostgreSQL UPSERT 의미와 달리 Django는 첫 번째 성공만 보장).

권장 패턴:
```python
with transaction.atomic():
    obj = Model.objects.select_for_update().filter(**unique_keys).first()
    if obj:
        for k, v in defaults.items(): setattr(obj, k, v)
        obj.save()
    else:
        obj = Model.objects.create(**unique_keys, **defaults)
```
또는 PostgreSQL `ON CONFLICT DO UPDATE`(`bulk_create(update_conflicts=True)` Django 4.1+).

---

## 부록: 모범/위험 코드 위치 인덱스

### 모범 패턴 (참고용)

- `sec_pipeline/tasks.py:340` — 2-Phase Neo4j sync (lock + DELETE+CREATE)
- `chainsight/views/watchlist_views.py:72-122` — `transaction.atomic + select_for_update`
- `users/views.py:692, 861, 927` — Watchlist 동시성 보호
- `portfolio/models.py:438, 524, 582, 700` — `UniqueConstraint` 사용

### 위험 위치 (재검토 권장)

- `chainsight/models/relation_discovery.py:148-161` — `save()`가 항상 `neo4j_dirty=True`로 덮음. 의도한 설계로 보이지만, 외부에서 `update_fields=['neo4j_dirty']`로 부분 업데이트 시 의도와 다르게 동작할 수 있음
- `chainsight/tasks/sync_tasks.py:167` — `synced_to_neo4j=False, neo4j_dirty=True` 동시 세팅 — 두 플래그 의미 중복
- `serverless/tasks.py:393, 1425` — `update_or_create` 명시적 atomic 없음
- `chainsight/services/neo4j_sync.py:32` — `iterator(chunk_size=100)` 사용, lock 없음
- `chainsight/models/news_event.py:23` — `Stock.delete()` 차단 (PROTECT). 운영 시 시스템 동작 명문화 필요

### 통계 재확인 명령

```bash
grep -rn "on_delete=models.SET_NULL" --include='*.py' . | grep -v migrations | grep -v __pycache__ | wc -l   # 17
grep -rn "on_delete=models.CASCADE"  --include='*.py' . | grep -v migrations | grep -v __pycache__ | wc -l   # 95
grep -rn "on_delete=models.PROTECT"  --include='*.py' . | grep -v migrations | grep -v __pycache__ | wc -l   # 7
grep -rn "update_or_create"          --include='*.py' . | grep -v migrations | grep -v __pycache__ | grep -v tests | wc -l
grep -rn "neo4j_dirty"               --include='*.py' . | grep -v migrations | grep -v __pycache__ | grep -v tests | wc -l
```

---

## 결론 요약

1. **즉시 검토 권장 (High)**:
   - `RelationConfidence`의 이중 플래그(`synced_to_neo4j` + `neo4j_dirty`) 단일화 정책 결정
   - PG↔Neo4j 정합성 야간 감사 잡 추가 (count diff + stale 감지)
   - `update_or_create` 핫패스(특히 `StockKeyword`, `StockRelationship`)에 `select_for_update` 또는 `bulk_create(update_conflicts=True)` 도입 검토

2. **운영 정책 명문화 (Medium)**:
   - `Stock.delete()`은 사실상 `ChainNewsEvent` 때문에 차단됨 — 정리 절차 문서화
   - `SupplyChainEvidence.target_company=NULL` 누적분 모니터링 임계값 설정
   - `RawDocumentStore.delete()` 시 LLM 추출 결과 동시 삭제 — 재추출 비용 인지

3. **장기 리팩토링 (Low)**:
   - `unique_together` → `UniqueConstraint` 전환 (Django 5.x deprecation 대비)
   - PG 측 orphan 정리 잡 (현재는 Neo4j NewsEvent만 cleanup)
