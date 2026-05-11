# 데이터 무결성 감사 보고서

- **감사 일자**: 2026-05-06
- **감사 범위**: stock_vis 전체 (Backend + Neo4j 동기화)
- **모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 이슈 수 | 핵심 키워드 |
|-------|--------|-------------|
| 🔴 **HIGH** | 5 | Neo4j 필드 명명 혼재 / target_company orphan / 재시도 부재 / 4단계 CASCADE / synced_pks 삭제 실패 묻힘 |
| 🟡 **MEDIUM** | 7 | SET_NULL orphan cleanup 부재 / atomic 미적용 update_or_create / PG-Neo4j 불일치 감지 부재 / self-FK 추적 끊김 / Stock 삭제 광범위 / signal 전파 누락 / CompanyChainProfile dirty 패턴 결여 |
| 🟢 **LOW** | 4 | UniqueConstraint 누락 후보 / target_company_name stale / NewsArticle.stock 의도된 null=True / migration legacy 흔적 |

> 사용자 사전 파악(SET_NULL 7곳/3파일, CASCADE 37곳/7파일)은 **outdated** — 실측 SET_NULL 16곳/9파일, CASCADE 80+곳/15+파일.

---

## FK orphan 위험

### SET_NULL 사용처 전수 (16곳, 9개 파일)

| # | 파일:라인 | 모델.필드 | 참조 대상 | 위험도 | 비고 |
|---|----------|----------|----------|-------|------|
| 1 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | `stocks.Stock` | 🔴 | Stock 삭제 시 `target_company=null`만 되고 Neo4j 엣지는 그대로 남음 |
| 2 | `serverless/models.py:660` | `ScreenerAlert.preset` | `ScreenerPreset` | 🟢 | 의도된 fallback (filters_json으로 자동 전환, get_effective_filters 처리) |
| 3 | `serverless/models.py:808` | `InvestmentThesis.user` | `users.User` | 🟡 | User 삭제 후에도 테제는 보존(공개 자료화), 단 `top_picks` JSON 내 사용자 종속 데이터 존재 시 stale |
| 4 | `serverless/models.py:1409` | `SavedPath.user` | `users.User` | 🟡 | 사용자가 저장한 chain path가 익명 영속 — 삭제 cleanup 없음 |
| 5 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | `DataBasket` | 🟡 | basket 삭제 시 세션은 살아있지만 분석 컨텍스트 사라짐 |
| 6 | `rag_analysis/models.py:256` | `UsageLog.session` | `AnalysisSession` | 🟢 | 사용량 로그 영속을 위한 의도된 패턴 |
| 7 | `rag_analysis/models.py:263` | `UsageLog.message` | `AnalysisMessage` | 🟢 | 동일 |
| 8 | `thesis/models/thesis.py:70` | `Thesis.source_news` | `news.NewsArticle` | 🟡 | 진입 출처 추적 끊김 (entry_source='news'인데 source_news=null인 모순 가능) |
| 9 | `thesis/models/thesis.py:77` | `Thesis.copied_from` | `self` (Thesis) | 🟡 | self-FK — 원본 가설 삭제 시 copy 체인 끊김 |
| 10 | `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | `ThesisPremise` | 🟡 | premise 삭제 시 지표는 살아있음 (관제실 표시 정합성 검증 필요) |
| 11 | `thesis/models/monitoring.py:66` | `ThesisAlert.indicator` | `ThesisIndicator` | 🟡 | alert는 보존되지만 어떤 지표 발생인지 추적 불가 |
| 12 | `chainsight/models/news_event.py:54` | `NewsEvent.duplicate_of` | `self` | 🟡 | 중복 root 삭제 시 dedup 체인 끊김 |
| 13 | `macro/models/indicators.py:282` | (확인 필요 — IndicatorValue 류) | (FRED 시리즈) | 🟢 | 지표 메타 삭제 시 값 보존 — 시계열 영속 의도 |
| 14 | `portfolio/models.py:327` | `BalanceAnalysis.wallet_snapshot_at_execution` | `WalletSnapshot` | 🟡 | 스냅샷 삭제 시 분석 자체는 finalized 상태로 영속, 추적성 손실 |
| 15 | `portfolio/models.py:732` | (portfolio 분석 흐름) | (관련 모델) | 🟡 | 동일 패턴 |
| 16 | `portfolio/models.py:831` | (portfolio 분석 흐름) | (관련 모델) | 🟡 | 동일 패턴 |

### Orphan 정리 로직 존재 여부

🔴 **문제**: SET_NULL 후 발생하는 orphan(`null` 채워진 레코드)을 정리하는 management command·Celery 태스크·관리자 화면이 **전무**.

**검증 결과**:
- `Grep "objects.filter(.*__isnull=True).delete"` → 정리 패턴 0건
- `Grep "cleanup|prune|gc_orphan"` → 정리 명령 0건
- `chainsight/services/seed_selection.py` 등에서 `target_company__isnull=False` 필터로 **회피만** 하고 있음

**구체적 결과**:
| 시나리오 | 누적되는 stale 레코드 |
|---------|---------------------|
| Stock 삭제 (델리스팅) | `SupplyChainEvidence` 중 `target_company=null + target_company_name=stale string` |
| User 탈퇴 | `InvestmentThesis`, `SavedPath` 익명 영속 — GDPR/개인정보 cleanup 누락 가능 |
| NewsArticle 삭제 | `Thesis.source_news=null` (진입 출처 추적 불가) |
| Thesis 원본 삭제 | `Thesis.copied_from=null` 자식들 — fork 트리 끊김 |
| ThesisIndicator 삭제 | `ThesisAlert.indicator=null` — 알림은 영원히 남지만 어떤 지표였는지 모름 |

🟡 **권고 (보고서 한정)**: 분기별 cleanup 태스크 추가, 또는 admin UI에 "orphan 통계" 섹션. 현재 코드 수정은 본 감사 범위 밖.

---

## CASCADE 체인

### 사용 통계

- 실측 80+곳, 15개 파일에 분포 (사용자 사전 파악 37곳/7파일은 outdated)
- 가장 많이 사용하는 앱: `portfolio` (12곳), `thesis` (10곳), `chainsight` (10곳), `serverless` (4곳), `validation` (8곳)

### Stock 삭제 시 영향 범위 (가장 위험)

`stocks.Stock`을 PK 또는 `to_field='symbol'`로 참조하는 CASCADE FK는 **20+ 모델**에 산재.

#### 직접 CASCADE되는 모델 (1단계)

| 앱 | 모델 | 예상 행 수(SP500 기준) |
|---|------|---------------------|
| stocks | `DailyPrice`, `WeeklyPrice`, `BalanceSheet`, `IncomeStatement`, `CashFlowStatement`, `StockOverviewKo`, `StockMetric`, `SignalAccuracy`, `NewsArticle`(null=True) | DailyPrice 단독 ~5M+ |
| users | `PortfolioItem`, `WatchlistItem` | 사용자 수 × 평균 보유 수 |
| validation | `BenchmarkDelta`, `CategoryScore`, `CompanyMetricLatest`, `NewsSummary`, `PeerPreset.stock`, `UserPeerPreference.stock` | ~SP500 × 지표 수 |
| sec_pipeline | `SupplyChainEvidence.source_company`(CASCADE), `BusinessModelSnapshot` | SP500 × 분기 |
| chainsight | `InsiderSignal`, `RevenueStructure`, `CapitalDNA`, `EventReaction`, `GrowthStage`, `ChainProfile`, `Sensitivity`, `NarrativeTag` | SP500 × 8 = ~4000 |
| serverless | `SupplyChainEvidence`(source/target_symbol), `ETFHolding`, `ThemeMatch`, `InstitutionalHolding` | SP500 × 카탈로그 |
| metrics | `MetricSnapshot`, `Benchmark` 4종 | SP500 × 지표 × 분기 |

#### 3단계 이상 연쇄 삭제 (CASCADE 체인)

🔴 **HIGH — User 삭제 시 4단계 폭포**:

```
User
 └─CASCADE→ Thesis (thesis/models/thesis.py:11)
     ├─CASCADE→ ThesisPremise (thesis/models/thesis.py:146)
     ├─CASCADE→ ThesisIndicator (indicator.py:10)
     │   └─CASCADE→ IndicatorReading (indicator.py:124)
     ├─CASCADE→ ThesisSnapshot (monitoring.py:10)
     └─CASCADE→ ThesisAlert (monitoring.py:61)
```

→ 한 사용자 탈퇴로 4단계, 최대 수만 개 행이 단일 트랜잭션에서 삭제. **트랜잭션 락 + WAL 부담** 가능성.

🟡 **MEDIUM — User → Watchlist 체인**:
```
User
 └─CASCADE→ Watchlist (users/models.py:171)
     └─CASCADE→ WatchlistItem (users/models.py:197)
```

🟡 **MEDIUM — User → Portfolio 체인** (12개 CASCADE FK가 portfolio 모델에 분포):
- `Portfolio → PortfolioItem → ...` (portfolio/models.py:54, 85, 163, 222, 292, 388, 483, 561, 622, 727, 772, 821)
- 12-FK 그래프이지만 깊이는 ~3단계로 추정. 정확한 깊이는 portfolio 모델 풀스캔 필요.

🟡 **MEDIUM — Stock → Validation 체인**:
```
Stock
 └─CASCADE→ PeerPreset (peer_preset.py:20)
     └─ UserPeerPreference (peer_preset.py:48 user CASCADE, 50 stock CASCADE)
```

🟡 **MEDIUM — RawDocumentStore 삭제 폭포**:
```
RawDocumentStore (sec_pipeline)
 ├─CASCADE→ SupplyChainEvidence (sec_pipeline/models.py:78)
 │   └─ Stock(source_company) CASCADE / Stock(target_company) SET_NULL
 └─CASCADE→ BusinessModelSnapshot (sec_pipeline/models.py:165)
```

→ 10-K 한 건 삭제 = 추출된 모든 evidence + business model snapshot 동시 삭제. **재추출 비용 무거움** 주의.

#### CASCADE 위험 평가

| 위험 | 평가 |
|------|------|
| **무한 루프** | self-FK 사용처 모두 SET_NULL (`Thesis.copied_from`, `NewsEvent.duplicate_of`) → 안전 |
| **데이터 누수** | Stock 삭제 시 SupplyChainEvidence.target만 SET_NULL인데 source는 CASCADE → **비대칭 정리** |
| **Neo4j 비동기화** | CASCADE/SET_NULL 어느 쪽이든 PG에서 사라져도 Neo4j 엣지/노드는 그대로 → reconciliation 필요 |
| **테스트 커버리지** | `tests/`에서 Stock 삭제 시나리오 없음 (`Grep "Stock.*delete"` 결과로 추정) |

---

## Neo4j 동기화

### neo4j_dirty 플래그 사용 현황

#### sec_pipeline (sec_pipeline/models.py:99-101)

```python
# Neo4j 동기화 (synced_to_neo4j 필드 금지 — neo4j_dirty만 사용)
neo4j_dirty = models.BooleanField(default=True)
neo4j_synced_at = models.DateTimeField(null=True, blank=True)
```

✅ 일관된 패턴. 모델 코멘트에 명시. `quality_checks.py:144`에서 `neo4j_synced` 키는 별칭일 뿐 (`neo4j_dirty=False` 카운트).

#### chainsight RelationConfidence (chainsight/models/relation_discovery.py:130-135)

```python
synced_to_neo4j = models.BooleanField(default=False)
neo4j_dirty = models.BooleanField(default=True, db_index=True, ...)
neo4j_synced_at = models.DateTimeField(null=True, blank=True)
```

🔴 **HIGH — 필드 3종이 동시 존재**:
- `neo4j_dirty + synced_to_neo4j` 둘 다 인덱싱
- `save()` override (line 160)에서 `neo4j_dirty=True`만 자동 세팅 (synced_to_neo4j은 수동)
- `services/neo4j_sync.py:47-51`에서 두 값을 동시 업데이트
- `tasks/sync_tasks.py:167`에서 `synced_to_neo4j=False, neo4j_dirty=True` 동시 reset
- CLAUDE.md "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용" 원칙 **위배**
- `migrations/0004_companychainprofile_neo4j_synced_and_more.py:87`에 추가된 legacy 잔존

#### chainsight CompanyChainProfile (chainsight/models/chain_profile.py:64-65)

```python
neo4j_synced = models.BooleanField(default=False, db_index=True)
neo4j_synced_at = models.DateTimeField(null=True, blank=True)
```

🔴 **HIGH — neo4j_dirty 필드 자체가 없음**:
- `tasks/sync_tasks.py:103`에서 `filter(neo4j_synced=False)`로 pending 조회
- 외부 변경 시 `neo4j_synced=False` reset 책임은 호출자 — `update_or_create(defaults={'neo4j_synced': False})`로 매번 reset (sync_tasks.py:33)
- 다른 sec_pipeline/RelationConfidence와 다른 패턴 → **동일 앱 내에서도 패턴 혼재**

### 동기화 실패 시 재시도 메커니즘

| 컴포넌트 | 재시도 정책 | 평가 |
|---------|-----------|------|
| `sec_pipeline.tasks.sync_dirty_to_neo4j` | `max_retries=1, soft_time_limit=300` | 🟡 노드 1회 실패 시 묻힘. dirty 플래그가 다음 주기에 재시도 (자연 fallback) |
| `chainsight.tasks.run_neo4j_dirty_sync` | `max_retries=2, default_retry_delay=60` | 🟢 적절 |
| `sync_dirty_relations` 내부 (services/neo4j_sync.py:42) | `try/except, log+continue` | 🟢 실패 건은 synced_pks에 미추가 → 다음 주기 재시도 |
| `_delete_edge` (services/neo4j_sync.py:90) | `try/except, warning만` | 🔴 **HIGH — 실패해도 synced_pks에 추가됨**. 삭제 실패가 영구히 묻힘 (line 41 `synced_pks.append(rc.pk)`가 try 블록 밖) |
| `sec_pipeline.tasks.sync_dirty_to_neo4j` Phase B | per-row try/except | 🟢 실패 건은 synced_ids 미추가 → 자연 재시도 |

🔴 **상세 — `_delete_edge` 실패 묻힘**:
```python
# chainsight/services/neo4j_sync.py:32-44
for rc in dirty_qs.iterator(chunk_size=100):
    try:
        if rc.relation_status in ('confirmed', 'probable'):
            _upsert_edge(repo, rc)
        elif rc.relation_category == 'market' and rc.relation_status == 'weak':
            _upsert_edge(repo, rc)
        else:
            _delete_edge(repo, rc)   # 내부에서 try/except로 warning만
        synced_pks.append(rc.pk)      # ← _delete_edge 실패해도 도달
    except Exception as e:
        logger.error(f'Failed to sync relation {rc.pk}: {e}')
```
→ `_delete_edge` 내부 `try` (line 84)가 외부 except로 escape하지 않음 → **삭제 실패가 'synced'로 표시됨**. Neo4j에 stale 엣지가 남아도 `neo4j_dirty=False`가 되어 영구히 미정리.

### PG-Neo4j 불일치 감지 메커니즘

🔴 **HIGH — reconciliation 메커니즘 부재**:
- 명시적 PG↔Neo4j diff 도구 없음 (`Grep "reconcile|consistency_check|drift_detect"` → 0건)
- `sec_pipeline/quality_checks.py:144`는 카운트만 집계 (`evidences.filter(neo4j_dirty=False).count()`) — Neo4j 측 실제 엣지 수와 비교 안 함
- `sync_relations_to_neo4j`의 1회성 `RELATED_TO` 정리(sync_tasks.py:158-171)가 유일한 cleanup. cache flag(`chainsight:related_to_cleanup_v1`)로 1년 lock → 한 번 실행되면 재실행 불가
- **PG에는 있고 Neo4j에는 없는 케이스**: dirty=False인데 실제 Neo4j에 미존재 → 감지 불가
- **Neo4j에는 있고 PG에는 없는 케이스**: PG에서 CASCADE 삭제 후 Neo4j 엣지/노드 잔존 → 감지·삭제 로직 없음

🟡 권고 (보고서 한정): 주 1회 reconciliation 태스크가 필요. 현재 없음.

---

## Unique 제약조건

### unique_together / UniqueConstraint 통계

- `unique_together`: 30+ 곳
- `UniqueConstraint`: 4곳 (모두 portfolio 앱)

### 핵심 제약 분포

| 앱 | 모델 | 제약 키 | 특징 |
|---|------|--------|------|
| stocks | `BalanceSheet/IncomeStatement/CashFlow` | `(stock, period_type, fiscal_year, fiscal_quarter)` | 4-튜플, 견고 |
| stocks | `DailyPrice/WeeklyPrice` | `(stock, date)` | 표준 |
| stocks | `EODSignal` | `(stock, signal_date, signal_tag)` | 견고 |
| serverless | `MarketMover` | `(date, mover_type, symbol)` | 일별/타입별 |
| serverless | `LLMExtractedRelation`(추정) | `(source_symbol, target_symbol, relationship_type)` | 방향성 키 |
| serverless | `InstitutionalHolding` | `(institution_cik, stock_symbol, report_date)` | 13F 표준 |
| chainsight | `RelationConfidence` | `(symbol_a, symbol_b, relation_type)` | normalize_pair로 정규화 |
| chainsight | `NewsEvent` | `(source, source_id)` | 외부 ID 기반 |
| sec_pipeline | `CompanyAlias` | `(alias, context_sector)` | sector별 충돌 방지 |
| validation | (peer_preset) | `(user, preset_id)` 추정 | 검증 필요 |
| graph_analysis | 4개 unique_together | `(watchlist, ..., date)` | 일별 그래프 |

### update_or_create 사용 시 race condition

#### 통계
- 실측 100+ 사용처
- 평가: 핵심 모델은 unique 키가 잘 정의되어 IntegrityError로 fallback 가능. 다만 `transaction.atomic()` 미사용 케이스 다수.

#### Race condition 위험 케이스

🟡 **MEDIUM — atomic 미사용 update_or_create**:

| 파일:라인 | 모델 | atomic 컨텍스트 | 위험 |
|----------|------|----------------|------|
| `validation/services/preset_generator.py:118,147,178,286,362,449` | `PeerPreset` | ❌ 없음 | 동일 user+preset_id 동시 호출 시 IntegrityError. 호출자 catch 없음 |
| `chainsight/tasks/relation_tasks.py:179,275,309,344` | `PriceCoMovement`, `RelationConfidence` | ❌ 없음 | Celery 다중 워커 동시 실행 시 중복 키 |
| `chainsight/tasks/profile_tasks.py:106,180` | `CompanyGrowthStage`, `CompanyCapitalDNA` | ❌ 없음 | 동기 시드 sync 중복 시 |
| `serverless/services/data_sync.py:196` | `MarketMover` | ❌ 없음 | 동일 (date, mover_type, symbol) 동시 업서트 |
| `news/services/aggregator.py:370,388` | `NewsEntity`, `EntityHighlight` | ❌ 없음 | aggregator 다중 실행 시 중복 |

🟢 **LOW — 안전 처리된 케이스**:

| 파일:라인 | 처리 |
|----------|------|
| `api_request/stock_service.py:387-408` | `with transaction.atomic()` + `IntegrityError catch` ✅ |
| `api_request/stock_service.py:481-583` | 재무제표 3종 동일 패턴 ✅ |
| `stocks/services/stock_sync_service.py:171,337` | atomic 안에서 호출 (검증 필요) |
| `chainsight/services/seed_selection.py:411` | `SeedSnapshot` — 시드 1회 호출이라 race 영향 작음 |

#### Django update_or_create 자체 한계

Django 5.1 기준 `update_or_create`는 내부적으로:
1. `get()` (SELECT)
2. 없으면 `create()` (INSERT) / 있으면 `update()` (UPDATE)

→ SELECT와 INSERT 사이에 다른 트랜잭션이 INSERT 성공 시 IntegrityError.
→ `atomic()` + IntegrityError catch + retry가 안전 패턴.
→ 본 코드베이스에는 이 패턴이 일관되게 적용되어 있지 **않음**.

#### unique 누락 후보

| 모델 | 현재 제약 | 의심 누락 |
|-----|---------|---------|
| `users/models.py:256 UserInterest` | `(user, interest_type, value)` | ✅ OK |
| `chainsight/CompanyChainProfile` | (`symbol_id`이 PK?) | 검증 필요 — `update_or_create(symbol=stock, defaults=...)`인데 symbol이 OneToOneField로 추정 |
| `metrics.MetricDefinition` | (확인 필요) | `seed_metric_definitions.py:518` update_or_create 사용, 키 명시되지 않음 |

---

## 종합 권고 (보고서 한정 — 코드 수정 없음)

### 즉시 검토 필요 (HIGH)
1. **chainsight RelationConfidence 필드 통일**: `synced_to_neo4j` 제거 마이그레이션 계획 (CLAUDE.md 원칙 정합) — 단, save() override가 의존하므로 단계적 deprecation 필요.
2. **`_delete_edge` 실패 묻힘 버그** (`chainsight/services/neo4j_sync.py:32-44`): synced_pks 추가를 try 블록 안으로 이동.
3. **CompanyChainProfile에 neo4j_dirty 도입**: 현재 `neo4j_synced=False` 패턴이 다른 chainsight 모델과 불일치.
4. **PG↔Neo4j reconciliation 태스크**: 주 1회, 양방향 카운트 + 샘플링 검증.
5. **User 삭제 4단계 CASCADE 부하 측정**: 운영 사용자 탈퇴 시나리오 부하 테스트 필요.

### 다음 스프린트 (MEDIUM)
6. **SET_NULL orphan cleanup 태스크**: 분기별 또는 월별 schedule.
7. **update_or_create atomic 래핑**: 최소 Celery 태스크 내부 호출 6곳에 적용.
8. **SupplyChainEvidence 비대칭 정리**: source CASCADE / target SET_NULL을 일관 정책으로 정리 (둘 다 SET_NULL + 별도 cleanup, 또는 둘 다 CASCADE).
9. **target_company_name stale 정리**: target_company=null이 된 경우 name 필드도 marker(예: '__deleted__')로 갱신하거나 cleanup.

### 장기 개선 (LOW)
10. Stock 삭제 운영 정책 문서화 (델리스팅 시 수동 archive vs CASCADE).
11. test 커버리지: Stock/User 삭제 시나리오, Neo4j 동기화 실패 후 재시도 시나리오.
12. legacy migration 흔적 정리 (`synced_to_neo4j`).

---

## 부록: 감사 데이터 출처

| 검색 패턴 | 결과 수 | 도구 |
|---------|--------|------|
| `on_delete=models.SET_NULL` | 16곳 / 9 파일 | Grep |
| `on_delete=models.CASCADE` | 80+곳 / 15 파일 | Grep |
| `neo4j_dirty` | 23 매치 | Grep |
| `synced_to_neo4j \| neo4j_synced` | 30+ 매치 | Grep |
| `unique_together \| UniqueConstraint` | 35곳 | Grep |
| `update_or_create(` | 100+ 곳 | Grep (head_limit 100) |
| `cleanup\|prune\|gc_orphan` | 0건 | Grep |
| `reconcile\|consistency_check\|drift_detect` | 0건 | Grep |

> 본 감사는 정적 분석에 한함. 운영 DB의 실제 orphan 행 수, Neo4j 엣지 drift, race condition 발생 빈도는 별도 운영 데이터 점검 필요.
