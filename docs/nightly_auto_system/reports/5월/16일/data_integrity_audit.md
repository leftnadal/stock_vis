# 데이터 무결성 감사 보고서

- **대상**: `/Users/byeongjinjeong/Desktop/stock_vis`
- **작성일**: 2026-05-16
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **범위**: FK orphan 위험, CASCADE 연쇄 삭제, Neo4j↔PG 동기화, UniqueConstraint/race condition

---

## 요약 (위험도별 이슈 수)

| 위험도 | 이슈 수 | 카테고리 |
|--------|--------:|----------|
| 🔴 HIGH | 4 | CASCADE 4단 체인 (`AnalysisRun → DiagnosticCard → ...`), Neo4j 불일치 감지 부재, `bulk_update` 시 `neo4j_dirty` 수동 토글 누락 위험, `StockNews.stock=SET_NULL이 아닌 CASCADE+null=True` 모순 |
| 🟠 MEDIUM | 5 | SET_NULL 후 orphan 청소 잡 부재 (18곳), Stock 삭제 시 fan-out 30+ 테이블, `get_or_create` race (atomic 미사용), `synced_ids` 업데이트 atomic 미보호, signals.py 동기 처리로 다건 update 시 락 경합 가능 |
| 🟡 LOW | 4 | `neo4j_synced_at` NULL 잔존 모니터링 부재, `previous_status` save() 내 SELECT 오버헤드, NewsArticle은 `neo4j_synced` 필드 없이 ID 비교 기반 (반대 방향 청소 불가), bulk insert에서 Meta unique_together 미발동 케이스 |

**실제 발견 수치 (지시서와 차이)**:
- `SET_NULL`: 지시서 7곳/3파일 → **실측 18곳/12파일**
- `CASCADE`: 지시서 37곳/7파일 → **실측 95곳/15파일**

추가 발견된 파일: `marketpulse/`, `thesis/`, `portfolio/`, `chainsight/`, `macro/`, `validation/`, `metrics/`, `users/`, `graph_analysis/`, `news/`, `stocks/`.

---

## FK orphan 위험

### 1.1 SET_NULL 사용처 (전 18곳)

| 모델 / 라인 | 필드 | 부모 삭제 시 효과 |
|---|---|---|
| `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company → Stock` | target ticker 사라지면 `target_company=NULL`, `target_company_name`만 보존 |
| `marketpulse/models/anomaly.py:25` | NewsAnomaly | 뉴스 삭제 시 anomaly만 잔존 |
| `thesis/models/thesis.py:70, 77` | Thesis 부모 참조 2개 | 원본 가설 삭제 후에도 fork본 유지 |
| `thesis/models/indicator.py:15` | IndicatorBinding | catalog 항목 삭제 시 binding은 살아남음 |
| `thesis/models/monitoring.py:66` | MonitoringSnapshot 부모 | 상위 thesis 삭제 후 스냅샷 잔존 |
| `serverless/models.py:660` | `ScreenerAlert.preset → ScreenerPreset` | 프리셋 삭제 시 alert는 `filters_json` fallback (의도된 설계, `get_effective_filters` 참조) |
| `serverless/models.py:808` | `InvestmentThesis.user` | 사용자 탈퇴 후 anonymized thesis 보존 |
| `serverless/models.py:1409` | `AdminActionLog.user` | 감사 목적 — 의도된 보존 |
| `portfolio/models.py:327, 732, 831` | wallet_snapshot, analysis_run, context_analysis_run | run 삭제 후에도 카드/대화 보존 |
| `chainsight/models/news_event.py:54` | `duplicate_of → self` | 원본 이벤트 삭제 시 중복 표시만 풀림 |
| `macro/models/indicators.py:310` | indicator 참조 | 지표 정의 삭제 시 시계열 보존 |
| `rag_analysis/models.py:145` | `AnalysisSession.basket` | basket 삭제 시 세션 자체는 유지 |
| `rag_analysis/models.py:256, 263` | `UsageLog.session`, `UsageLog.message` | 메시지 삭제 후에도 비용 로그 보존 |

### 1.2 Orphan 정리 로직 존재 여부 — 🟠 MEDIUM

- **결론**: 위 18곳 모두 **명시적 orphan cleanup 잡 부재**.
- `grep "orphan|cleanup"` 결과: SET_NULL된 row를 주기적으로 청소하거나 archive하는 Celery beat / management command **0건**.
- 위험:
  - `SupplyChainEvidence.target_company=NULL`이 누적되면 `quality_checks.py:92` 카운터가 부풀어 dirty backlog 알람 오작동 가능.
  - `rag_analysis.UsageLog` orphan은 비용 분석 시 `session__user` join이 NULL이 되어 사용자별 집계가 누락됨.
  - `serverless.InvestmentThesis.user=NULL`은 "anonymized" 의도지만, ownership 검증 로직이 NULL 케이스를 가정 안 하면 권한 우회 가능 (별도 security_audit 참조).
- **권장 조치**: `target_company__isnull=True` 등을 매일 카운트해서 임계 초과 시 슬랙 알림 (코드 수정 없이 모니터링만).

### 1.3 모순 패턴 발견 — 🔴 HIGH

- `stocks/models.py:888` — `StockNews.stock = ForeignKey('Stock', on_delete=models.CASCADE, null=True, blank=True)`
  - `null=True`이면서 CASCADE는 의도가 흐림. Stock이 NULL인 row는 부모 삭제와 무관하고, Stock이 있으면 CASCADE로 통째 삭제됨.
  - News는 보통 보존해야 하는 데이터(legal/archive). `on_delete=SET_NULL`이 합리적. **현 설정은 Stock 삭제 시 뉴스 이력이 모두 사라짐**.

---

## CASCADE 체인

### 2.1 Stock을 정점으로 한 fan-out (가장 큰 영향)

`Stock.delete()` 호출 시 직접 CASCADE되는 모델 (`*.models.py` 기준, migration 제외, 실측):

| 앱 | 모델 | 라인 | 비고 |
|---|---|---|---|
| stocks | DailyPrice | 133 | to_field=symbol |
| stocks | WeeklyPrice | 244 | to_field=symbol |
| stocks | StockOverviewKo | 699 | OneToOne |
| stocks | EODSignal | 756 | |
| stocks | SignalAccuracy | 801 | |
| stocks | StockNews | 888 | null=True (모순, 1.3 참조) |
| users | Portfolio | 28 | to_field=symbol |
| users | WatchlistItem | 198 | to_field=symbol |
| sec_pipeline | SupplyChainEvidence (source_company) | 82 | CASCADE |
| sec_pipeline | BusinessModelSnapshot | 161 | CASCADE |
| chainsight | CompanyInsiderSignal | insider_signal.py:27 | |
| chainsight | CompanyRevenueStructure | revenue_structure.py:20 | |
| chainsight | CompanyCapitalDNA | capital_dna.py:22 | |
| chainsight | CompanyEventReaction | event_reaction.py:17 | |
| chainsight | CompanyGrowthStage | growth_stage.py:18 | |
| chainsight | CompanySensitivityProfile | sensitivity.py:17 | |
| chainsight | CompanyNarrativeTag | narrative_tag.py:22 | |
| chainsight | CompanyChainProfile | chain_profile.py:12 | OneToOne, neo4j_dirty 동기화 영향 |
| validation | CompanyBenchmarkDelta | benchmark_delta.py:7 | |
| validation | CategoryScore | category_score.py:20 | |
| validation | MetricLatest | metric_latest.py:7 | |
| validation | ValidationNewsSummary | news_summary.py:7 | |
| validation | PeerPreset | peer_preset.py:20, 50 | 2회 (preset 본체 + member) |
| metrics | MetricSnapshot | metric_snapshot.py:19 | |
| metrics | PeerMetricBenchmark | benchmark.py:12 | |
| metrics | StockBenchmark | benchmark.py:100, 107 | 2회 |
| portfolio | WalletItem | 88 | |
| portfolio | (Run 관련 다수) | 391, 564 | |
| graph_analysis | CorrelationEdge | 75, 82 | stock_a + stock_b |
| graph_analysis | (PerStockReport) | 289 | |

**합계**: 단일 `Stock.delete()` 호출 시 **30+ 테이블 row 동시 삭제** + 각 테이블의 reverse FK까지 합치면 50건 이상.

### 2.2 3단계 이상 연쇄 삭제 — 🔴 HIGH 후보

**Chain A — Portfolio AnalysisRun (4단)**:
```
Portfolio (users) → AnalysisRun (portfolio) → MetricResult (portfolio:386)
                                            → DiagnosticCard (portfolio:481)
                                            → (다른 Run 산출물 12종, CASCADE 라인 727 외)
```
- `users.User` 삭제 시: `Portfolio → AnalysisRun → MetricResult/DiagnosticCard/...` 까지 4단 연쇄.
- 위험: `DiagnosticCard.target_stock = on_delete=PROTECT` (portfolio/models.py:495) 이므로 **Stock 삭제는 막히지만, User 삭제는 정상 진행**.

**Chain B — Chain Sight Saved Path**:
```
User → SavedPath (chainsight/saved_path.py:22) → SavedPathAction (75)
```
- 2단이라 위험 낮음.

**Chain C — sec_pipeline SupplyChain**:
```
Stock (source) → SupplyChainEvidence (sec_pipeline:82, CASCADE)
RawDocumentStore → SupplyChainEvidence (78, CASCADE)
RawDocumentStore → BusinessModelSnapshot (165) → BusinessModelEvidence (213)
```
- Stock + RawDocumentStore 동시 삭제 시 evidence가 양쪽에서 CASCADE — duplicate cascade가 발생해도 ORM은 안전 처리.
- 단, **target_company는 SET_NULL이라 한쪽만 비대칭** — 뒤에서 backfill 시 reverse lookup 어려움.

**Chain D — chainsight CompanyChainProfile → Neo4j**:
```
Stock → CompanyChainProfile (CASCADE) → Neo4j 노드는 자동 삭제 안 됨!
```
- PG에서 profile이 사라져도 Neo4j `:Stock {ticker: ...}` 노드는 살아남음 → **PG/Neo4j 불일치 자연 발생** (3.3 참조).

### 2.3 CASCADE 누락 가능성 — 🟡 LOW

- `validation.PeerPreset` (peer_preset.py:48) `user → CASCADE` — User 삭제 시 모든 프리셋 삭제. 의도된 설계이나 audit 로그가 함께 사라짐. 별도 archive 필요 여부 검토.

---

## Neo4j 동기화

### 3.1 neo4j_dirty 플래그 사용 현황

세 모델이 동일 패턴을 따름:

| 모델 | 파일 | 기본값 | 인덱스 | save() 자동 토글 |
|---|---|---:|---|---|
| `sec_pipeline.SupplyChainEvidence` | models.py:100 | True | ✅ (line 111) | (없음 — `update_or_create` 시 save가 호출되어 default가 작동) |
| `chainsight.RelationConfidence` | relation_discovery.py:130 | True | ✅ (db_index=True) | ✅ **save() 내부에서 강제 True** (line 158) |
| `chainsight.CompanyChainProfile` | chain_profile.py:65 | True | ✅ (db_index=True) | (없음 — default만 의존) |

**legacy 제거 흔적** — `synced_to_neo4j` 필드가 `chainsight/migrations/0004_*`에 남아 있으나, 코드에서는 모두 제거됨 (audit P0 #9, 2026-04-29 기록). migration 자체는 보존됨.

### 3.2 동기화 실패 시 재시도

| Task | 위치 | retry 설정 | 백오프 |
|---|---|---|---|
| `sec_pipeline.tasks.sync_dirty_to_neo4j` | tasks.py:337 | `max_retries=1` | 없음 |
| `chainsight.tasks.neo4j_dirty_sync_tasks.run_neo4j_dirty_sync` | line 14 | `max_retries=2, default_retry_delay=60` | 고정 60초 |
| `chainsight.tasks.sync_tasks.sync_profiles_to_neo4j` | line 97 | `max_retries=1` | 없음 |
| `chainsight.tasks.sync_tasks.sync_relations_to_neo4j` | line 148 | `max_retries=1` | 없음 |

**관찰**:
- `max_retries=1`은 한 번만 재시도 — 일시적 Neo4j 끊김에 취약.
- **단위 단건 실패는 try/except로 흡수**됨 (`sec_pipeline/tasks.py:437`, `chainsight/services/neo4j_sync.py:42`) → 실패한 row는 `synced_ids/synced_pks`에 안 들어가서 **다음 사이클에 자동 재시도**되는 자가 치유 패턴 (✅ 좋음).
- `sec_pipeline.tasks.py:362-368`: `transaction.atomic + select_for_update(skip_locked=True)` 사용 (Phase A) — concurrent worker 경합 차단 ✅.
- `chainsight/services/neo4j_sync.py:48`: `RelationConfidence.objects.filter(pk__in=synced_pks).update(...)`에 **`transaction.atomic` 미사용** — Neo4j 쓰기 성공 후 PG 업데이트 직전 worker가 죽으면 PG는 dirty 상태로 남아 **중복 sync 발생**. Neo4j 쪽이 `DELETE + CREATE`로 idempotent이므로 데이터 무결성은 보호되나 **중복 비용** 발생 가능 — 🟠 MEDIUM.

### 3.3 PG↔Neo4j 불일치 감지 — 🔴 HIGH

**현재 감지 메커니즘**:
- `sec_pipeline/quality_checks.py:144` — `neo4j_dirty=False` 카운트만 노출.
- `sec_pipeline/intelligence.py:97-98` — sync_synced/sync_pending 비율 노출.
- **명시적 reconciliation 잡 부재**: PG에는 confirmed인데 Neo4j에 엣지 없는 케이스, 또는 그 반대 케이스를 비교하는 cron 없음.

**위험 시나리오**:
1. **PG는 있고 Neo4j는 없음**:
   - `neo4j_dirty=False, neo4j_synced_at=...`인데 Neo4j 엣지가 누군가 수동 삭제 → 감지 불가.
   - Stock CASCADE 삭제 시 `CompanyChainProfile`은 PG에서 사라지지만 Neo4j 노드는 잔존 (2.2 Chain D).
2. **Neo4j는 있고 PG는 없음**:
   - legacy `RELATED_TO` 엣지 — `sync_tasks.py:159-170` 1회 cleanup으로 처리 (cache key `chainsight:related_to_cleanup_v1`, 1년 timeout). 다른 legacy 타입에는 동일 메커니즘 부재.
3. **NewsArticle ↔ Neo4j**:
   - `news/services/news_neo4j_sync.py:542` 주석: "neo4j_synced 필드가 없으므로, Neo4j에 이미 존재하는 article_id를 제외합니다."
   - **반대 방향 (Neo4j에는 있고 PG는 삭제됨) 청소 로직 없음** — Neo4j에 고아 노드 누적 가능.

**권장 조치 (코드 수정 없이 가능한 부분)**:
- 주 1회 reconciliation 잡: `RelationConfidence.objects.filter(neo4j_dirty=False, relation_status='confirmed').count()` vs Neo4j `MATCH ()-[r]->() RETURN count(r)` 비교 후 임계 초과 시 알림.
- Stock 삭제 이벤트(`post_delete` signal)로 Neo4j 노드 함께 삭제 — 현재 없음.

### 3.4 bulk_update 위험 — 🔴 HIGH

`chainsight/models/relation_discovery.py:157-158` 주석 그대로 인용:
> "neo4j_dirty 자동 세팅 (bulk_update에서는 save() 미호출되므로 수동 관리 필요)"

`chainsight/tasks/relation_tasks.py:382-402`에서는 명시적으로 `.update(neo4j_dirty=True)`를 chaining함 (audit P0 #9 주석). 하지만 **다른 위치에서 향후 bulk_update를 추가할 때 이 규약을 잊어버리면 silent dirty miss 발생** — 코드 컨벤션 강제 수단 없음 (lint rule, pre-commit hook 부재). 신규 개발자가 실수하기 쉬운 함정.

---

## Unique 제약조건

### 4.1 unique_together / UniqueConstraint 현황

**unique_together 사용 (실측, migration 제외, 30+ 곳)**:

| 영역 | 개수 | 대표 패턴 |
|---|---:|---|
| `stocks/models.py` | 6 | `(stock, date)`, `(stock, period_type, fiscal_year, fiscal_quarter)` |
| `serverless/models.py` | 10 | `(date, mover_type, symbol)`, `(symbol, date)`, `(institution_cik, stock_symbol, report_date)` |
| `chainsight/models/*` | 5 | `(symbol_a, symbol_b)`, `(symbol_a, symbol_b, relation_type)` |
| `validation/models/*` | 5 | `(symbol, fiscal_year, metric_code, preset_key)` |
| `thesis/models/*` | 4 | `(thesis, asof_date)`, `(target, source, text)` |
| `macro/models/*` | 4 | `(indicator, date)`, `(indicator_a, indicator_b)` |
| `marketpulse/models/*` | 6 | `(date, universe)`, `(user, news, viewed_date)` |
| `graph_analysis/models.py` | 4 | `(watchlist, stock_a, stock_b, date)` |
| `sec_pipeline/models.py` | 1 | `(alias, context_sector)` |
| `portfolio/models.py` | 1 | `(wallet, stock)` |

**UniqueConstraint 사용 (4곳)** — `portfolio/models.py:439, 525, 583, 701`:
- `unique_metric_result_per_run_stock(analysis_run, stock, metric_id)`
- `unique_card_priority_per_run(analysis_run, priority)`
- 외 2건.

### 4.2 update_or_create race condition — 🟠 MEDIUM

**총 87개 파일에서 `update_or_create`/`get_or_create` 사용** (실측).

**보호 수준 매트릭스**:

| 케이스 | 보호 |
|---|---|
| unique_together + atomic | ✅ 안전 (예: `chainsight.RelationConfidence` `unique_together=['symbol_a','symbol_b','relation_type']` + `tasks/relation_tasks.py:291` 주변) |
| unique_together만 (atomic 없음) | ⚠️ IntegrityError → retry 필요 (Django `update_or_create`가 내부적으로 try하지만 동시 호출 시 race 잔존) |
| unique 제약 자체가 없음 | 🔴 silent duplicate 가능 |

**대표적 위험 지점**:

1. **`chainsight/tasks/sync_tasks.py:84` (`aggregate_chain_profiles`)** — `CompanyChainProfile.objects.update_or_create(symbol=stock, defaults=defaults)`:
   - `symbol`이 OneToOneField + PK이므로 안전 (✅).
   - 단, Celery worker 동일 task가 중복 실행되면 마지막 쓰기가 이긴다 (last-write-wins).

2. **`sec_pipeline/tasks.py:314` (RelationConfidence upsert)** — `update_or_create(symbol_a=, symbol_b=, relation_type=)`:
   - unique_together로 보호 (✅).
   - 단, `transaction.atomic` 없음 → 동시 호출 시 IntegrityError 가능. Django 기본 동작은 한 번 재시도이지만, **여러 worker가 동일 SEC 문서를 처리하면 race**. 현재 `validator_track_a` 호출 빈도가 낮아 실제 발생률은 낮음.

3. **`chainsight/services/neo4j_sync.py:48`** — `RelationConfidence.objects.filter(pk__in=synced_pks).update(...)`:
   - 단순 update는 race 안전 (atomic SQL UPDATE).
   - 단, Neo4j 쓰기 ↔ PG 쓰기 사이에 `transaction.atomic` 없음 → 부분 실패 시 PG/Neo4j 불일치 (3.2 참조).

4. **`sec_pipeline/signals.py:42-53`** — post_save signal 내에서 `SupplyChainEvidence.objects.filter(...).update(target_company=..., neo4j_dirty=True)`:
   - signal은 동기 실행 → admin이 unmatch queue를 빠르게 여러 건 resolve하면 락 경합 가능.
   - 같은 source_company에 대한 다중 update가 겹치면 row lock 대기. 🟠 MEDIUM.

### 4.3 RelationConfidence.save() 내 SELECT — 🟡 LOW

`chainsight/models/relation_discovery.py:148-156`:
```python
def save(self, *args, **kwargs):
    if self.pk:
        try:
            old = RelationConfidence.objects.filter(pk=self.pk).values_list(
                'relation_status', flat=True
            ).first()
            ...
```
- 매 save마다 추가 SELECT 1회 — bulk write 시 N+1 패턴. 단, race 측면 안전 (자기 자신 status 비교).

### 4.4 NewsArticle URL 해시 — 🟡 LOW

`news/models.py:200-205` — `url_hash`가 save()에서 SHA256으로 생성. unique 제약은 별도 확인 필요. 동일 URL을 두 워커가 동시에 insert하면 unique 제약 없으면 중복 가능. (현재 grep 결과로는 unique 미확인 — 별도 점검 권장.)

---

## 부록: 우선순위별 조치 권장 (코드 수정 제안만, 본 보고서는 적용 안 함)

### 🔴 즉시 조치
1. **Stock `post_delete` signal**로 Neo4j 노드 함께 삭제 — chainsight/sec_pipeline에 hook 추가.
2. **PG↔Neo4j reconciliation 주간 잡** — `RelationConfidence(confirmed) ↔ Neo4j edge count` 비교.
3. **`StockNews.stock` on_delete를 `SET_NULL`로 변경** 검토 — 뉴스 이력 보존이 정책일 것.
4. **`chainsight/services/neo4j_sync.py:48` `transaction.atomic` 추가** — Neo4j 성공 시 PG 업데이트 누락 방지 (현 패턴은 idempotent이지만 명시적 안전망 필요).

### 🟠 다음 스프린트
5. 18곳 `SET_NULL` 모델에 대해 orphan 카운트 모니터링 추가 (코드 수정 없이 Grafana 쿼리만).
6. `sec_pipeline.tasks.sync_dirty_to_neo4j` `max_retries`를 2~3으로 상향 (current=1).
7. `bulk_update` 시 `neo4j_dirty` 누락 방지를 위한 lint rule 또는 wrapper 함수 도입.

### 🟡 백로그
8. `RelationConfidence.save()` 내 SELECT를 `__init__`에서 캐시하도록 리팩터.
9. `NewsArticle.url_hash`에 unique 제약 추가 검토.

---

**보고서 종료**.
