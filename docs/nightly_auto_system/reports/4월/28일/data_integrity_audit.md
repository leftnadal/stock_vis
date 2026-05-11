# 데이터 무결성 감사 보고서

작성일: 2026-04-28
대상 브랜치: `feature/chainsight-graph-v2`
방식: 정적 분석 (코드 수정 없음, 읽기 전용)
이전 보고서 대비: 4월 25/26/27일 보고서와 비교 — 분석 범위 확장 (사전 정보 7곳 SET_NULL / 37곳 CASCADE는 누락치, 실제 17곳 / 80+곳)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 이슈 수 | 핵심 카테고리 |
|--------|---------|--------------|
| 🔴 **High** | 4 | (1) `RelationConfidence.save()`가 무조건 `neo4j_dirty=True` 덮음 + `synced_to_neo4j` / `neo4j_dirty` 이중 플래그 (DECISIONS 단일 플래그 원칙 위반 의심) / (2) `update_or_create` 40+곳 호출 중 다수가 `select_for_update` 보호 없이 `defaults`만 의존 → race 시 마지막 값 손실 가능 / (3) PG ↔ Neo4j 정합성 자동 감지 잡 부재 (count diff/orphan edge 없음) / (4) `chainsight.ChainNewsEvent.symbol` PROTECT → Stock 삭제 사실상 차단 (운영 미문서화) |
| 🟠 **Medium** | 5 | (1) `Stock` 직접 FK 참조 모델 ≥ 28개 (가격·재무·체인사이트·SEC·검증·포트폴리오 동시 삭제) / (2) `SET_NULL` 17곳 중 PG 정리 잡 0건 — Neo4j는 `news_neo4j_sync.py:700` 1곳만 / (3) `RawDocumentStore` CASCADE → `SupplyChainEvidence` + `BusinessModelEvidence` + `BusinessModelSnapshot` 3단계 동시 삭제 (LLM 재추출 비용 큼) / (4) Celery 동기화 태스크 retry 불균일 — `chainsight.run_neo4j_dirty_sync` 단일 함수만, sec는 `max_retries=1` 단발성 / (5) `parent_thesis` SET_NULL 후 사이클/orphan 정리 없음 |
| 🟡 **Low** | 4 | (1) `unique_together` 22+곳 vs `UniqueConstraint` 4곳만 (Django 5.x deprecation) / (2) `to_field='symbol'` 사용 시 cascade 거동 일관성 검토 필요 / (3) `news_neo4j_sync` 외 orphan 노드 cleanup 부재 / (4) `update_or_create` 직후 별도 `save()` 호출 패턴 다수 — 두 번째 save에서 부분 업데이트 race |

전수 조사 통계:
- `on_delete` 사용처 — `CASCADE` 80+, `SET_NULL` 17, `PROTECT` 7, 기타 0 (총 ≈ 104 곳, 마이그레이션/캐시/테스트 제외)
- `update_or_create` 호출 — 40+ (서비스 핫패스), 마이그레이션/테스트 제외 시 30+
- `unique_together` 22+곳, `UniqueConstraint` 4곳 (모두 portfolio)
- `neo4j_dirty` 플래그를 가진 모델: `chainsight.RelationConfidence` + `sec_pipeline.SupplyChainEvidence`

---

## FK orphan 위험

### SET_NULL 사용처 전체 (17곳, 11개 파일)

> 사전 정보의 "7곳, 3개 파일"은 누락치이며 실제 11개 파일에 17곳 분산.

| 파일:Line | 모델.필드 | 참조 | 위험도 | 비고 |
|-----------|-----------|------|--------|------|
| `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | Stock | 🟠 | `target_company_name`(text)만 남음 — 의도된 설계. 단 Neo4j edge 자동 삭제 안 됨 (별도 cleanup 잡 없음) |
| `serverless/models.py:660` | `ScreenerAlert.preset` | ScreenerPreset | 🟢 | preset 삭제 후 `filters_json`으로 동작 가능 |
| `serverless/models.py:808` | `InvestmentThesis.user` | User | 🟠 | 사용자 탈퇴 후에도 테제 보존 — `user=null` 노출 정책 미명문화 |
| `serverless/models.py:1409` | `AdminActionLog.user` | User | 🟢 | 감사 로그는 user=null 허용 정상 |
| `rag_analysis/models.py:145` | `AnalysisSession.basket` | DataBasket | 🟠 | `exploration_path` JSON 안의 `entity_id` 끊어짐 — LLM 컨텍스트 일관성 |
| `rag_analysis/models.py:256, 263` | `UsageLog.session/message` | Session/Message | 🟢 | 비용 추적 보존 의도 |
| `chainsight/models/news_event.py:54` | `ChainNewsEvent.duplicate_of` | self | 🟢 | parent 삭제 시 child 보존 |
| `macro/models/indicators.py:297` | `EconomicEvent.related_indicator` | EconomicIndicator | 🟢 | OK |
| `marketpulse/models/anomaly.py:50` | `AnomalySignal.paired_news` | MarketPulseNews | 🟢 | OK |
| `portfolio/models.py:327` | `AnalysisRun.wallet_snapshot_at_execution` | WalletSnapshot | 🟢 | OK |
| `portfolio/models.py:732` | `ChatSession.analysis_run` | AnalysisRun | 🟢 | "느슨한 연결" 주석 |
| `portfolio/models.py:831` | `Decision.context_analysis_run` | AnalysisRun | 🟢 | OK |
| `thesis/models/thesis.py:70` | `Thesis.source_news` | NewsArticle | 🟢 | OK |
| `thesis/models/thesis.py:77` | `Thesis.copied_from` | self (parent_thesis) | 🟠 | self FK SET_NULL 후 사이클/orphan 검사 없음 — 복사 체인 끊어진 thesis가 누적될 위험 |
| `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | ThesisPremise | 🟠 | premise 삭제 후 indicator 고아화 가능 — Thesis 빌더 일관성 검토 필요 |
| `thesis/models/monitoring.py:66` | `Alert.indicator` | ThesisIndicator | 🟠 | indicator 사라진 alert는 root cause 추적 어려움 |

### Orphan 레코드 정리 로직 — **존재하지 않음 (PG 측 0건)**

전수 조사:
- `grep -rn "orphan|cleanup_orphan|delete_orphan"` 결과: PG 정리 잡 **0건**
- 단 1건만 존재: `news/services/news_neo4j_sync.py:700` — Neo4j(그래프DB) 고립 NewsEvent 노드 cleanup. PG의 SET_NULL 후 처리는 **전혀 없음**
- `target_company__isnull=True` 카운트는 `sec_pipeline/quality_checks.py:142-143`, `sec_pipeline/intelligence.py:91-92`에서 **모니터링만** (정리/알림 없음)
- `sec_pipeline/management/commands/rematch_unmatched.py:33-51` — 수동 실행 가능한 재매칭 커맨드 1건 (cron 미등록)

권장:
- `target_company__isnull=True`로 N일 이상 남은 `SupplyChainEvidence` 영구 orphan 정책(삭제/보류 전환/아카이브) 명문화
- `user__isnull=True` `InvestmentThesis` / `ScreenerAlert.preset=null` 노출 정책 명문화
- `ThesisIndicator.premise=null`, `Alert.indicator=null`, `Thesis.copied_from` self-orphan 정기 점검

---

## CASCADE 체인

### CASCADE 사용처 (80+곳, 14개 파일)

> 사전 정보의 "37곳, 7개 파일"은 누락치. 실제 14개 파일.

| 파일 | CASCADE 수 |
|------|-----------|
| `portfolio/models.py` | 13 |
| `thesis/models/*.py` | 11 |
| `chainsight/models/*.py` | 10 |
| `serverless/models.py` | 4 |
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

### Stock 삭제 시 영향 범위 (직접 FK ≥ 28개 모델)

```
stocks.Stock (DELETE 시도)
├─ stocks.DailyPrice (CASCADE, to_field=symbol) ─────────── 가격 데이터 전부
├─ stocks.WeeklyPrice (CASCADE, to_field=symbol)
├─ stocks.MonthlyPrice (CASCADE, to_field=symbol)
├─ stocks.StockOverviewKorean (CASCADE, OneToOne, primary_key=symbol)
├─ stocks.[BalanceSheet|IncomeStatement|CashFlowStatement] (CASCADE) ── 재무제표 전부
├─ stocks.StockNews (CASCADE, null=True)                    재게시 외 복구 불가
│
├─ users.Portfolio (CASCADE) → users.PortfolioItem (자동)
├─ users.WatchlistItem (CASCADE)                  (Watchlist는 user CASCADE만)
│
├─ chainsight.ChainCompanyProfile (CASCADE, primary_key=symbol)
├─ chainsight.NarrativeTag (CASCADE, primary_key=symbol)
├─ chainsight.SensitivityScore (CASCADE, primary_key=symbol)
├─ chainsight.GrowthStage (CASCADE, primary_key=symbol)
├─ chainsight.EventReaction (CASCADE)
├─ chainsight.CapitalDNA (CASCADE, primary_key=symbol)
├─ chainsight.RevenueStructure (CASCADE, primary_key=symbol)
├─ chainsight.InsiderSignal (CASCADE)
├─ chainsight.ChainNewsEvent (PROTECT)  🔴 ── Stock.delete()를 차단! IntegrityError
│
├─ sec_pipeline.RawDocumentStore (CASCADE)
│   ├─ sec_pipeline.SupplyChainEvidence (CASCADE, source_company)  3단계
│   │       ↘ target_company는 SET_NULL (target evidence 보존)
│   └─ sec_pipeline.BusinessModelEvidence (CASCADE)                3단계
├─ sec_pipeline.BusinessModelSnapshot (CASCADE)
│
├─ validation.PeerPreset (CASCADE) (admin/seed 프리셋)
├─ validation.UserPeerPreference.target_stock (CASCADE)
├─ validation.NewsSummary (CASCADE)
├─ validation.MetricLatest (CASCADE)
├─ validation.CategoryScore (CASCADE)
├─ validation.BenchmarkDelta (CASCADE)
│
├─ metrics.IndustryMetricBenchmark (CASCADE, to_field=symbol)
├─ metrics.PeerMetricBenchmark (CASCADE)
├─ metrics.MetricSnapshot (CASCADE)
│
├─ portfolio.PortfolioItem (CASCADE)
├─ portfolio.AnalysisRun (다수 FK)                            4단계 시작
│   ├─ portfolio.MetricResult (CASCADE)
│   ├─ portfolio.DiagnosticCard.target_stock (PROTECT)  🔴 ── 동일하게 차단
│   └─ portfolio.ChatSession (CASCADE)
│       └─ portfolio.Message (CASCADE)
└─ portfolio.Decision.target_stock (?)
```

### 3단계 이상 연쇄 삭제 (4건 식별)

1. **Portfolio 체인 (4단계)**
   `Stock → portfolio.AnalysisRun → MetricResult/DiagnosticCard/ChatSession → Message`
   → `DiagnosticCard.target_stock`은 PROTECT라 Stock 삭제 자체가 차단됨 (보호적 부작용)

2. **SEC 파이프라인 체인 (3단계)**
   `Stock → RawDocumentStore (CASCADE) → SupplyChainEvidence + BusinessModelEvidence`
   → `RawDocumentStore` 삭제는 LLM 추출 결과까지 전부 삭제. 재추출 비용 큼 (10-K 1건당 LLM 호출 다수)

3. **Thesis 체인 (3단계)**
   `User → Thesis (CASCADE) → ThesisIndicator (CASCADE) → ThesisAlert (CASCADE)`
   → User 삭제 시 알림 이력까지 사라짐. 감사/회고에 영향

4. **Chainsight SavedPath 체인 (2단계, 참고)**
   `User → SavedPath → SavedPathAction` (`chainsight/models/saved_path.py:22, 75`)

### 🔴 PROTECT/CASCADE 충돌 — Stock 삭제 사실상 차단

`chainsight/models/news_event.py:23`
```python
symbol = models.ForeignKey('stocks.Stock', on_delete=models.PROTECT, to_field='symbol', ...)
```
- Stock에 ChainNewsEvent가 1건이라도 있으면 Stock 삭제 → `ProtectedError` 발생, 트랜잭션 전체 롤백
- 다른 28개 CASCADE 모델은 같이 삭제되지 않음
- 이 동작이 admin 화면/운영 매뉴얼에 명시되어 있는지 별도 확인 필요
- 동일 충돌: `marketpulse/models/snapshot.py:81`, `metrics/models/metric_snapshot.py:11`, `portfolio/models.py:90, 393, 495, 566` 도 PROTECT — Stock 삭제 차단 다중 보호막

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 사용 현황

| 모델 | 플래그 | 정책 | 비고 |
|------|--------|------|------|
| `chainsight.RelationConfidence` (`relation_discovery.py:130-134`) | **`neo4j_dirty` + `synced_to_neo4j` 둘 다** | `save()`에서 무조건 `self.neo4j_dirty = True` (line 160) | 🔴 `DECISIONS.md:18` "synced_to_neo4j 대신 채택"과 모순. 필드 동시 보유 → 의미 혼선 (`chainsight/tasks/sync_tasks.py:167`은 둘 다 세팅) |
| `sec_pipeline.SupplyChainEvidence` (`models.py:99-101`) | `neo4j_dirty`만 사용 | 모델 주석에 명시: "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용" | 🟢 단일 플래그 패턴 (DECISIONS 일치) |

### 동기화 태스크 비교

| 작업 | 위치 | retry 정책 | 트랜잭션 보호 | 비고 |
|------|------|-----------|--------------|------|
| `chainsight.run_neo4j_dirty_sync` | `chainsight/tasks/neo4j_dirty_sync_tasks.py:15` | (Celery 기본 retry 명시 없음) | `transaction.atomic` 없음, `iterator(chunk_size=100)`만 | 🟠 동시 실행 시 같은 row 처리 충돌 가능, retry 미명시 |
| `sec_pipeline.sync_dirty_to_neo4j` | `sec_pipeline/tasks.py:337-452` | `max_retries=1, soft_time_limit=300` | `transaction.atomic + select_for_update(skip_locked=True)` BATCH=500 | 🟢 모범 패턴: 2-Phase, row lock, dynamic edge type, DELETE+CREATE |
| `news.news_neo4j_sync` | `news/services/news_neo4j_sync.py:700` | (서비스 직접 호출) | — | 🟢 유일하게 orphan 노드 cleanup 보유 |

### 🟢 sec_pipeline 모범 패턴 (`tasks.py:337-449`)

```python
@shared_task(bind=True, max_retries=1, soft_time_limit=300)
def sync_dirty_to_neo4j(self):
    # Phase A: PG row lock (skip_locked) + dict 복사 (BATCH=500)
    with transaction.atomic():
        dirty_qs = (SupplyChainEvidence.objects
            .filter(neo4j_dirty=True, target_company__isnull=False)
            .select_for_update(skip_locked=True)[:500])
        rows = [<dict 복사>]

    # Phase B: Neo4j (try/except per row, synced_ids 누적)
    # DELETE + CREATE (MERGE 금지, dynamic edge type)

    # Phase C: PG queryset.update() — save() 금지 (덮어쓰기 방지)
    SupplyChainEvidence.objects.filter(id__in=synced_ids).update(
        neo4j_dirty=False, neo4j_synced_at=timezone.now()
    )
```

대비: `chainsight/services/neo4j_sync.py:21-54`은 lock/atomic 모두 없음.

### 동기화 실패 시 재시도 메커니즘

- **Cell 단위 try/except**: 한 row 실패 시 다음 row 진행 (양쪽 동일)
- **Task 단위 재시도**: `sec_pipeline.sync_dirty_to_neo4j`는 `max_retries=1` (단발성), `chainsight.run_neo4j_dirty_sync`는 명시 없음
- 실패한 row는 `neo4j_dirty=True`로 남으므로 다음 주기 자연 재처리 — 자체 패턴은 OK
- 단, **실패 누적 임계값 알림 없음** — `intelligence.py:97-98`이 카운트만 보고, 알림 트리거 부재

### 🔴 PG ↔ Neo4j 불일치 감지 — **메커니즘 부재**

- PG `neo4j_dirty=False` AND Neo4j 엣지 부재(어느쪽 누락) — 감지 불가
- PG에 row가 없는데 Neo4j 엣지가 남는 경우(orphan edge) — `news_neo4j_sync.py:700` 외 cleanup 없음
- `intelligence.py:97`은 `neo4j_dirty=False` 카운트만 보고, 실제 Neo4j 측 카운트와 비교 안 함
- `sec_pipeline/quality_checks.py:144-147`도 `neo4j_synced` PG-side count만

권장 감지 패턴:
- 야간 잡: PG `(symbol_a, symbol_b, relation_type)` count vs Neo4j `MATCH (a)-[r]->(b)` count 비교
- `neo4j_synced_at`이 N일 이상 stale인 row 알림
- PG 부재 + Neo4j 잔존 edge 정기 cleanup (`news_neo4j_sync.py` 패턴 확장)

---

## Unique 제약조건

### 선언 현황

**`unique_together` 22+곳** (Django 4+ 비권장이지만 동작 정상):
- `graph_analysis/models.py`: 4곳 (51, 127, 316, 390)
- `sec_pipeline/models.py:295` (alias + context_sector)
- `portfolio/models.py:128` (wallet + stock)
- `users/models.py`: 4곳 (71, 179, 217, 265)
- `news/models.py`: 2곳 (292, 380)
- `serverless/models.py`: 11곳 (105, 161, 245, 562, 614, 946, 981, 1100, 1172, 1311, 1389)
- `stocks/models.py`: 6곳 (185, 214, 358, 427, 526, 787, 825)
- `rag_analysis/models.py:111`

**`UniqueConstraint` 4곳 — 모두 portfolio**:
- `portfolio/models.py:438-443` `MetricResult: analysis_run + stock + metric_id` (`unique_metric_result_per_run_stock`)
- `portfolio/models.py:524-525` (DiagnosticCard 추정)
- `portfolio/models.py:582-583`, `700-701`

🟡 권장: `unique_together` → `UniqueConstraint` 전환 (Django 5.x deprecated 경고 예정).

### `update_or_create` 사용 시 race condition

총 **40+ 호출** (마이그레이션/테스트 제외). 위험도별:

| 위치 | 트랜잭션 보호 | 위험도 | 비고 |
|------|--------------|--------|------|
| `validation/services/preset_generator.py` (6곳: 118/147/178/286/362/449) | 명시적 lock 없음 (배치 seed 가정) | 🟡 | 단일 워커 가정이지만 동시 실행 차단 코드 없음 |
| `validation/services/benchmark_calculator.py` (4곳) + `metric_calculator.py` (2곳) | 명시적 lock 없음 | 🟠 | 같은 (stock, metric_id) 동시 호출 시 race |
| `serverless/services/keyword_service.py:202` (StockKeyword) | 없음 | 🟠 | Celery 태스크에서 호출 — 동시 실행 시 race |
| `serverless/services/patent_network_service.py:327, 379` (StockRelationship) | 없음 | 🟠 | 동일 |
| `serverless/services/llm_relation_extractor.py:284` (LLMExtractedRelation) | 없음 | 🟠 | 동일 |
| `serverless/services/corporate_action_service.py:222` | 없음 | 🟠 | 일별 배치라 충돌 가능성 낮음 |
| `marketpulse/calculators/breadth.py:206`, `concentration.py:103`, `sector_flow.py:182` | 없음 | 🟢 | 단일 dispatcher 가정 |
| `marketpulse/tasks/news.py:91`, `briefing.py:45/69`, `regime.py:71` | 없음 | 🟠 | Celery beat에서 호출 — 동시성 가능 |
| `graph_analysis/services/correlation_calculator.py:197, 290, 388` | 없음 | 🟠 | 무거운 배치, 동시 실행 시 PriceCache 충돌 |
| `thesis/services/snapshot_builder.py:146` | 없음 | 🟠 | EOD 파이프라인에서 호출 |
| `validation/api/views.py:475` (UserPeerPreference) | view 단일 트랜잭션 가정 | 🟢 | API endpoint, JWT user 단위 |
| `marketpulse/management/commands/setup_marketpulse_beat.py:207` | 단발성 커맨드 | 🟢 | OK |
| `validation/management/commands/seed_validation_data.py:127` | 단발성 커맨드 | 🟢 | OK |

### 🔴 핵심 위험 패턴

Django `update_or_create` 동작 흐름:
1. `get()` 시도
2. 없으면 `save()` 시도 → IntegrityError 시 `get()` 재시도 (1회)
3. 그래도 실패 시 예외 전파

→ **두 워커가 동시에 같은 unique_keys로 호출** 시 한쪽이 IntegrityError 후 정상 복구되지만:
- `defaults`가 다르면 **마지막에 들어온 값이 보존되지 않을 수 있음** (PostgreSQL UPSERT 의미와 달리 Django는 첫 번째 성공만 보장)
- Race 시간 동안 두 번째 호출은 **이전 값 + 자기 defaults 머지 결과** 가 아닌 **자기 defaults 만** 으로 update

권장 패턴:
```python
with transaction.atomic():
    obj = Model.objects.select_for_update().filter(**unique_keys).first()
    if obj:
        for k, v in defaults.items():
            setattr(obj, k, v)
        obj.save()
    else:
        obj = Model.objects.create(**unique_keys, **defaults)
```
또는 PostgreSQL `ON CONFLICT DO UPDATE` (`bulk_create(update_conflicts=True)`, Django 4.1+).

### 🔴 RelationConfidence.save() 분석 (`relation_discovery.py:148-161`)

```python
def save(self, *args, **kwargs):
    if self.pk:
        old = RelationConfidence.objects.filter(pk=self.pk).values_list(
            'relation_status', flat=True
        ).first()
        if old and old != self.relation_status:
            self.previous_status = old
    self.neo4j_dirty = True   # 🔴 무조건 True로 덮음
    super().save(*args, **kwargs)
```

문제점:
- `update_fields=[...]`로 부분 저장 시에도 `neo4j_dirty`가 강제 True 됨 → save 호출하는 모든 코드가 sync 큐에 다시 들어감
- `chainsight/services/neo4j_sync.py:46-51`은 이를 회피하기 위해 명시적으로 `queryset.update()` 사용 (save 금지) — 우회 패턴이 코드 전반에 일관되게 적용되어 있는지 검토 필요
- `sec_pipeline/tasks.py:324`도 `'synced_to_neo4j': False` 기록 — 두 플래그 의미 중복 흔적

---

## 부록: 모범/위험 코드 위치 인덱스

### 🟢 모범 패턴

- `sec_pipeline/tasks.py:337-452` — 2-Phase Neo4j sync (lock + DELETE+CREATE + queryset.update)
- `chainsight/views/watchlist_views.py:72-122` — `transaction.atomic + select_for_update`
- `users/views.py:692, 861, 927` — Watchlist 동시성 보호
- `portfolio/models.py:438, 524, 582, 700` — `UniqueConstraint` 사용
- `news/services/news_neo4j_sync.py:700` — 유일한 Neo4j orphan cleanup

### 🔴 재검토 권장

- `chainsight/models/relation_discovery.py:148-161` — `save()` 무조건 `neo4j_dirty=True` + `synced_to_neo4j`/`neo4j_dirty` 이중 플래그
- `chainsight/tasks/sync_tasks.py:167` — `synced_to_neo4j=False, neo4j_dirty=True` 동시 세팅
- `chainsight/services/neo4j_sync.py:21-54` — atomic/lock 부재, `iterator(chunk_size=100)`만
- `serverless/services/keyword_service.py:202`, `patent_network_service.py:327/379`, `llm_relation_extractor.py:284` — 핫패스 `update_or_create` 보호 없음
- `chainsight/models/news_event.py:23` — Stock PROTECT (사실상 Stock 삭제 차단), 운영 미문서화
- `thesis/models/indicator.py:15`, `monitoring.py:66`, `thesis/models/thesis.py:77` — SET_NULL 후 정리 로직 없음
- `sec_pipeline/management/commands/rematch_unmatched.py` — 수동 재매칭 커맨드 cron 미등록

### 통계 재확인 명령

```bash
grep -rn "on_delete=models.SET_NULL" --include='*.py' . | grep -v migrations | grep -v __pycache__ | wc -l   # 17
grep -rn "on_delete=models.CASCADE"  --include='*.py' . | grep -v migrations | grep -v __pycache__ | wc -l   # 80+
grep -rn "on_delete=models.PROTECT"  --include='*.py' . | grep -v migrations | grep -v __pycache__ | wc -l   # 7
grep -rn "update_or_create"          --include='*.py' . | grep -v migrations | grep -v __pycache__ | grep -v tests | wc -l   # 40+
grep -rn "neo4j_dirty"               --include='*.py' . | grep -v migrations | grep -v __pycache__ | grep -v tests | wc -l
```

---

## 결론 — 다음 액션 우선순위

1. **🔴 즉시 검토 (High)**
   - `RelationConfidence` 이중 플래그(`synced_to_neo4j` + `neo4j_dirty`) 단일화 정책 결정 → `DECISIONS.md`에 명문화
   - `update_or_create` 핫패스 (`StockKeyword`, `StockRelationship`, `LLMExtractedRelation`, `validation` 6곳) `select_for_update` 또는 `bulk_create(update_conflicts=True)` 도입
   - PG ↔ Neo4j 정합성 야간 감사 잡 추가 (count diff + stale `neo4j_synced_at` + orphan edge 감지)
   - `chainsight.ChainNewsEvent.symbol` PROTECT 정책 운영 문서화 (Stock 삭제 절차)

2. **🟠 운영 정책 명문화 (Medium)**
   - SET_NULL 17곳 영구 orphan 정책 (삭제/보류 전환/아카이브) `DECISIONS.md` 명문화
   - `target_company__isnull=True` `SupplyChainEvidence` 누적 모니터링 임계값 + 알림 (현재 카운트만)
   - `RawDocumentStore.delete()` 시 LLM 추출 결과 동시 삭제 — 재추출 비용 인지 + 보호 정책
   - `chainsight.run_neo4j_dirty_sync`에 `max_retries`/atomic/lock 추가 (`sec_pipeline` 패턴 준용)
   - `parent_thesis` self-orphan 정기 점검 잡

3. **🟡 장기 리팩토링 (Low)**
   - `unique_together` (22+) → `UniqueConstraint` 전환 (Django 5.x deprecation 대비)
   - PG 측 orphan 정리 잡 (현재 Neo4j NewsEvent 1곳만)
   - `to_field='symbol'` cascade 거동 일관성 검토 (FK 6곳 — `users.Portfolio`, `users.WatchlistItem`, `stocks.DailyPrice` 등)
