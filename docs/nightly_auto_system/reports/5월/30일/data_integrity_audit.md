# 데이터 무결성 감사 보고서

- **감사 일자**: 2026-05-30
- **대상**: `/Users/byeongjinjeong/Desktop/stock_vis` (monorepo 마이그레이션 진행 중 — PR3 단계)
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 범위**: FK orphan 위험 / CASCADE 연쇄 삭제 / Neo4j↔PG 동기화 / Unique 제약 + update_or_create

> **⚠️ 지시서 전제와 실제 코드의 불일치 (감사 범위 보정)**
> 지시서는 `SET_NULL 7곳/3파일`, `CASCADE 37곳/7파일`, 모델 경로 `stocks/models.py`·`users/models.py`를 전제했으나, 이는 **monorepo 마이그레이션 이전 기준**입니다. 실측 결과:
> - **`SET_NULL`: 17곳 / 11개 파일** (지시서의 2.4배)
> - **`CASCADE`: ~90곳 / 20+ 파일** (지시서의 2.4배)
> - 핵심 모델은 `packages/shared/stocks/models.py`, `packages/shared/users/models.py`로 이동, `portfolio/`·`marketpulse/`·`thesis/`·`validation/` 등 신규 앱 추가됨.
> 본 보고서는 **실제 코드 기준**으로 작성합니다.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 수 | 핵심 이슈 |
|--------|----|----------|
| 🔴 High | 2 | (1) SET_NULL 후 Neo4j orphan edge 미정리 (sec_pipeline target_company) · (2) `sync_dirty_to_neo4j` 전체 실패 시 재시도 미작동 (max_retries=1 선언만, `self.retry()` 미호출) |
| 🟠 Medium | 4 | (3) Stock 삭제 시 PROTECT/CASCADE/SET_NULL **혼재** — 동작 예측 불가 · (4) PG↔Neo4j **역방향 불일치(Neo4j有/PG無) 감지 메커니즘 부재** · (5) `update_or_create` lookup이 unique 제약 미보장 시 중복 위험 (101건 중 일부) · (6) `ChainNewsEvent.symbol` PROTECT vs 형제 모델 CASCADE 비일관 |
| 🟡 Low | 3 | (7) portfolio User 삭제 시 5단계 CASCADE 체인 · (8) SET_NULL 후 dangling 메타데이터 잔존(target_company_name) · (9) news 동기화는 dirty 플래그 대신 "Neo4j 존재 여부 조회" 방식 — 별도 패턴 |

**총 9개 이슈 (High 2, Medium 4, Low 3)**

---

## FK orphan 위험

### SET_NULL 사용처 전수 (17곳 / 11파일)

| # | 위치 | 필드 | 참조 대상 | orphan 정리 로직 |
|---|------|------|-----------|------------------|
| 1 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | `DataBasket` | ❌ 없음 (세션은 보존, basket만 NULL — 의도적) |
| 2 | `rag_analysis/models.py:256` | `UsageLog.session` | `AnalysisSession` | ❌ 없음 (비용 로그 보존 목적 — 의도적) |
| 3 | `rag_analysis/models.py:263` | `UsageLog.message` | `AnalysisMessage` | ❌ 없음 (동상) |
| 4 | `serverless/models.py:661` | `ScreenerAlert.preset` | `ScreenerPreset` | ❌ 없음 (preset 삭제 시 커스텀 필터로 폴백 — 의도적, `filters_json` 존재) |
| 5 | `serverless/models.py:810` | `InvestmentThesis.user` | `User` | ❌ 없음 (익명화 보존 — 의도적) |
| 6 | `serverless/models.py:1413` | `AdminActionLog.user` | `User` | ❌ 없음 (감사 추적 보존 — **적절**) |
| 7 | `chainsight/models/news_event.py:54` | `ChainNewsEvent.duplicate_of` (self FK) | self | ❌ 없음 (대표 기사 삭제 시 중복 표시만 해제 — 의도적) |
| 8 | `macro/models/indicators.py:310` | indicator 관련 | — | ❌ 없음 |
| 9 | `portfolio/models.py:326` | `AnalysisRun.wallet_snapshot_at_execution` | `WalletSnapshot` | ❌ 없음 (스냅샷 삭제돼도 분석 이력 보존) |
| 10 | `portfolio/models.py:733` | `ChatSession.analysis_run` | `AnalysisRun` | ❌ 없음 |
| 11 | `portfolio/models.py:832` | `Decision.context_analysis_run` | `AnalysisRun` | ❌ 없음 (의사결정 이력 보존) |
| 12 | `thesis/models/monitoring.py:66` | — | — | ❌ 없음 |
| 13 | `thesis/models/indicator.py:15` | — | — | ❌ 없음 |
| 14 | `thesis/models/thesis.py:70` | `Thesis.source_news` | `news.NewsArticle` | ❌ 없음 (뉴스 만료돼도 가설 보존) |
| 15 | `thesis/models/thesis.py:77` | `Thesis.copied_from` (self FK) | self | ❌ 없음 (원본 삭제돼도 복사본 보존) |
| 16 | **`sec_pipeline/models.py:85`** | **`SupplyChainEvidence.target_company`** | **`stocks.Stock`** | ⚠️ **부분적 — 아래 🔴 High #1 참조** |
| 17 | `marketpulse/models/anomaly.py:25` | — | — | ❌ 없음 |

### 🔴 High #1 — SET_NULL 후 Neo4j orphan edge 미정리 (`sec_pipeline`)

`SupplyChainEvidence.target_company`가 `SET_NULL`인데, **Stock 삭제 시점에 `neo4j_dirty=True`로 토글되지 않습니다.**

```python
# sec_pipeline/models.py:84-88
target_company = models.ForeignKey(
    'stocks.Stock', on_delete=models.SET_NULL,
    null=True, blank=True, ...
)
```

**문제 흐름**:
1. Stock 삭제 → `target_company`가 NULL이 됨 (PG 정합성 OK)
2. 그러나 `sync_dirty_to_neo4j`의 Phase A 필터는 `target_company__isnull=False`를 요구 (`sec_pipeline/tasks.py:374`) → **NULL이 된 row는 영구히 동기화 대상에서 제외**
3. 결과: Neo4j에 남아있던 SEC-origin edge가 **재동기화 로직으로는 절대 정리되지 않음**

**완화 요인**: `rag_analysis/signals.py:67`의 `post_delete(Stock)` 시그널이 `delete_stock_from_neo4j`(`DETACH DELETE`)를 호출하므로, **Stock 노드 자체가 삭제되면 연결 edge도 함께 제거**됩니다. 따라서 실제 orphan edge는 "Stock은 살아있는데 target만 NULL이 된" 케이스(예: 수동 FK 해제, 데이터 보정)에서만 발생합니다. 그러나 이 시그널은 PROTECT FK가 막으면 애초에 발화하지 않습니다(아래 Medium #3).

**남는 부채**: SET_NULL된 `SupplyChainEvidence` row는 `target_company_name`만 보존한 채 `neo4j_dirty` 상태가 동결됨 → **dangling 메타데이터(Low #8)**.

---

## CASCADE 체인

### Stock 삭제 영향 범위 (가장 많이 참조됨)

`Stock.symbol`은 **PK이자 unique** (`packages/shared/stocks/models.py:21`). Stock을 참조하는 FK는 앱 전반에 분산:

| 앱 | 참조 모델 | on_delete | 비고 |
|----|-----------|-----------|------|
| stocks (내부) | DailyPrice, WeeklyPrice, 재무3종, EODSignal, StockOverviewKO(OneToOne) 등 | **CASCADE** | 가격/재무 데이터 동반 삭제 |
| users | Portfolio, WatchlistItem | **CASCADE** | |
| chainsight | ChainProfile, NarrativeTag, Sensitivity, GrowthStage, EventReaction, CapitalDNA, RevenueStructure, InsiderSignal (8개) | **CASCADE** | |
| chainsight | **ChainNewsEvent** | **🛑 PROTECT** | 삭제 차단 |
| portfolio | **WalletHolding, MetricResult, DiagnosticCard, LLMComment** (4개) | **🛑 PROTECT** | 삭제 차단 |
| sec_pipeline | RawDocumentStore, SupplyChainEvidence(source), BusinessModelSnapshot | **CASCADE** | source는 CASCADE |
| sec_pipeline | SupplyChainEvidence(target) | **SET_NULL** | |
| validation | PeerPreset(x2), NewsSummary, MetricLatest, CategoryScore, BenchmarkDelta (6개) | **CASCADE** | |

### 🟠 Medium #3 — Stock 삭제 동작이 PROTECT/CASCADE/SET_NULL 혼재

**실질 동작**: Stock에 **WalletHolding(PROTECT)** 또는 **ChainNewsEvent(PROTECT)** 자식이 1건이라도 있으면 → `ProtectedError`로 **삭제 전체가 차단**됩니다. 이 경우:
- CASCADE 자식들(가격/재무/chainsight 8종/validation 6종)은 **삭제되지 않음**
- `post_delete` 시그널도 **발화하지 않음** → Neo4j 노드도 그대로 유지

반대로 PROTECT 자식이 없는 종목(예: 운영 안 하는 신규 심볼)은 ~20개 테이블에 걸쳐 CASCADE가 일제히 발화. **동일한 "Stock 삭제" 연산이 종목 상태에 따라 정반대로 동작** → 운영자가 결과를 예측하기 어렵습니다.

> 권고(감사 의견, 수정 아님): Stock 삭제 정책을 단일화. 모두 PROTECT로 통일하여 "삭제 전 명시적 정리" 강제 또는, soft-delete(`is_active`) 패턴 도입 검토.

### 3단계 이상 연쇄 삭제 — 최장 체인은 portfolio (5단계)

```
User
 └─CASCADE→ Wallet                         (portfolio/models.py:51)
     └─CASCADE→ Portfolio                  (:219)
         └─CASCADE→ AnalysisRun            (:289)
             ├─CASCADE→ MetricResult       (:385)   ← 5단계
             ├─CASCADE→ DiagnosticCard     (:482)
             ├─CASCADE→ LLMComment         (:560)
             └─CASCADE→ StoredAnalysis(1:1)(:621)
     └─CASCADE→ WalletHolding / WalletSnapshot
```

- **User 1건 삭제 → 최대 5단계, 10+ 테이블 연쇄 삭제** (🟡 Low #7)
- 단, `WalletHolding.stock`·`MetricResult.stock`·`DiagnosticCard.target_stock`·`LLMComment.stock`은 모두 **PROTECT(→Stock)** 이므로, User 방향 CASCADE와 Stock 방향 PROTECT가 교차 — User 삭제는 정상 연쇄되나 Stock 삭제는 차단됨.

기타 3단계 체인:
- `User → DataBasket → BasketItem` (rag_analysis, CASCADE 3단)
- `User → AnalysisSession → AnalysisMessage` (rag_analysis, CASCADE 3단)
- `Stock → RawDocumentStore → SupplyChainEvidence / BusinessModelSnapshot → BusinessModelEvidence` (sec_pipeline, CASCADE 4단)

대부분 **자식 보존이 무의미한 상세 레코드**라 CASCADE가 적절. portfolio 5단계만 삭제 비용/감사 추적 관점에서 soft-delete 검토 가치 있음.

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 현황

`neo4j_dirty`(단일 소스, `True=동기화 필요`)는 **3개 모델**에만 존재:

| 모델 | 위치 | 인덱스 | 동기화 태스크 |
|------|------|--------|---------------|
| `CompanyChainProfile.neo4j_dirty` | `chainsight/models/chain_profile.py:65` | ✅ db_index | `chainsight/tasks/sync_tasks.py` |
| `RelationConfidence.neo4j_dirty` | `chainsight/models/relation_discovery.py:130` | ✅ Index | `chainsight/services/neo4j_sync.py` + `neo4j_dirty_sync_tasks.py` |
| `SupplyChainEvidence.neo4j_dirty` | `sec_pipeline/models.py:99` | ✅ Index | `sec_pipeline/tasks.py:sync_dirty_to_neo4j` |

- **설계 일관성 양호**: `synced_to_neo4j`(의미 반전 플래그)는 audit P0 #9에서 전면 제거되고 `neo4j_dirty` 단일 소스로 통일 (코드 주석에 이력 명시). `save()`/`update_or_create`가 자동으로 `dirty=True` 설정, `queryset.update()`·`bulk_update`에서만 수동 토글(`relation_tasks.py:391`, `relation_discovery.py:157`).
- **news 앱은 예외 패턴**: `NewsArticle`에는 `neo4j_synced` 필드가 **없고**, "Neo4j에 이미 존재하는 `article_id`를 조회해 제외"하는 방식(`news/services/news_neo4j_sync.py:542`) — dirty 플래그 패턴과 **불일치**(🟡 Low #9). 매 배치마다 Neo4j 조회 비용 발생.

### 동기화 실패 시 재시도 메커니즘

| 태스크 | max_retries | per-row 실패 처리 | 전체 실패 시 retry |
|--------|-------------|-------------------|--------------------|
| `chainsight-neo4j-dirty-sync` | 2 (`default_retry_delay=60`) | — | shared_task 기본 (예외 전파 시 재시도) |
| `sec_pipeline.sync_dirty_to_neo4j` | **1** | ✅ try/except → `synced_ids` 미포함 → `dirty=True` 유지로 **다음 배치 자동 재처리** (우수) | ⚠️ **`self.retry()` 미호출** |

### 🔴 High #2 — `sync_dirty_to_neo4j` 전체 실패 시 재시도 미작동

```python
# sec_pipeline/tasks.py:346, 455-459
@shared_task(bind=True, max_retries=1, ...)  # ← max_retries 선언됨
def sync_dirty_to_neo4j(self):
    ...
    except Exception as e:
        logger.error(f"sync_dirty_to_neo4j error: {e}")
        # ← self.retry() 호출 없음 / return 없음 (None 반환)
```

- `max_retries=1`을 선언했으나 **`self.retry()`를 호출하지 않아** Neo4j 연결 자체가 끊긴 경우 자동 재시도가 작동하지 않음. 다음 Beat 스케줄까지 대기.
- **완화 요인**: per-row 실패는 `dirty=True`로 남아 다음 실행에서 자연 재처리됨. 따라서 **데이터 유실은 없으나** 복구가 다음 주기까지 지연됨. (Phase A의 `select_for_update(skip_locked=True)` + 2-Phase 패턴은 동시성/잠금 측면에서 잘 설계됨.)

### PG↔Neo4j 불일치 감지 방법

| 방향 | 감지 가능 여부 | 메커니즘 |
|------|----------------|----------|
| **PG有 → Neo4j無** | ✅ 가능 | `neo4j_dirty=True` 필터로 미동기화 큐 조회 (3개 모델). `sec_pipeline/quality_checks.py:95`에서 `dirty & matched > 50건`이면 backlog 알림 |
| **Neo4j有 → PG無 (역방향)** | ⚠️ **부분적/부재** | 정기 reconciliation 잡 없음. `news_neo4j_sync.py:700`의 orphan node 정리(관계 없는 NewsEvent `DELETE`)만 존재. **chainsight/sec_pipeline에는 역방향 정합성 검사 없음** |

### 🟠 Medium #4 — 역방향 불일치 감지 부재

- `delete_stock_from_neo4j`(DETACH DELETE)는 Stock 삭제 시 노드+edge를 정리하지만, **이 시그널이 실패(Neo4j down)하면 PG는 삭제되고 Neo4j에는 노드가 남는** 불일치 발생 가능. 시그널은 `delay()`로 비동기 큐잉만 하고 결과를 검증하지 않음(`rag_analysis/signals.py:75`).
- 정기 reconciliation 잡(PG 전체 ticker ↔ Neo4j Stock 노드 대조)이 없어 **누적 drift를 감지할 수단이 없음**.

> 권고(감사 의견): 야간 배치로 `PG ticker set` vs `Neo4j Stock 노드 set` diff 리포트 추가 검토. SEC edge는 `source='sec_10k'` 태그가 있으므로 `target_company IS NULL`인 evidence에 대응하는 edge를 역추적해 정리하는 잡 추가 검토.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황

- **`unique_together`: 60+ 곳** (앱 전반). 대부분 `(stock, date)`, `(symbol, date)`, `(stock, period_type, fiscal_year, fiscal_quarter)` 등 **시계열/주기 데이터의 자연키**로 적절히 설정됨.
- **`UniqueConstraint`: 4곳** — 모두 `portfolio/models.py` (lines 438, 526, 584, 702). 신규 코드에서 `unique_together`(deprecated 예정) 대신 `UniqueConstraint`(권장 방식) 사용 — **좋은 패턴**.
- 핵심 동기화 모델의 unique 키:
  - `RelationConfidence`: `unique_together = ['symbol_a', 'symbol_b', 'relation_type']` (`relation_discovery.py:139`)
  - `ChainNewsEvent`: `['source', 'source_id']` (`news_event.py:63`)
  - `CompanyAlias`: `[('alias', 'context_sector')]` — `context_country` 의도적 제외 (`sec_pipeline/models.py:294`)
  - `BasketItem`: `['basket', 'item_type', 'reference_id']` (`rag_analysis/models.py:111`)

### update_or_create race condition 가능성

- **비테스트 코드에서 `update_or_create`/`get_or_create` 101회 사용** (serverless·chainsight·validation·marketpulse·sec_pipeline 등).
- **구조적 사실**: Django `update_or_create`는 내부적으로 `get → (없으면) create`이며 **단일 atomic 연산이 아님**. 두 워커가 동시에 같은 키로 진입하면 race 발생 가능.
- **완화 요인 1**: 샘플 검증한 호출들(`RelationConfidence` on `(symbol_a, symbol_b, relation_type)`, `CompanyAlias` on `(alias, context_sector)`, `SupplyChainEvidence`→RelationConfidence 등)은 **lookup 필드가 모두 DB unique 제약으로 보호됨** → race 시 중복 생성 대신 `IntegrityError`로 losing thread가 실패(데이터 정합성은 유지).
- **완화 요인 2**: macOS 운영 환경은 Celery **solo pool**(메모리상 단일 워커)로 동시성이 낮음.

### 🟠 Medium #5 — unique 미보장 lookup의 잠재 중복 위험

- 101건 전수 검증은 본 감사 범위를 초과하나, **lookup 필드 조합에 대응하는 unique 제약이 없는 `update_or_create` 호출이 존재할 경우** race 시 **중복 row 생성**으로 이어집니다(IntegrityError 미발생).
- 특히 `transaction.atomic()` 없이 호출되고 lookup이 단일 비-unique 필드인 케이스가 위험. (예: 다중 워커로 전환하거나 prefork pool로 변경 시 현재화될 수 있는 잠재 부채.)

> 권고(감사 의견, 수정 아님): `update_or_create` lookup 키 ↔ 모델 unique 제약 매핑표를 작성해 미보장 케이스만 선별 점검. 미보장 케이스는 `unique_together` 추가 또는 `transaction.atomic()` + `select_for_update` 래핑.

---

## 종합 권고 (우선순위)

| 우선 | 이슈 | 권고 (감사 의견 — 본 보고서는 수정하지 않음) |
|------|------|----------------------------------------------|
| 1 | 🔴 High #2 | `sync_dirty_to_neo4j` except 블록에 `raise self.retry(exc=e, countdown=60)` 추가 검토 |
| 2 | 🔴 High #1 | Stock `post_delete`/SET_NULL 시 관련 `SupplyChainEvidence`를 `neo4j_dirty=True`로 토글하거나, SEC edge 역정리 잡 추가 검토 |
| 3 | 🟠 Medium #3 | Stock 삭제 정책 단일화(PROTECT 통일 or soft-delete) |
| 4 | 🟠 Medium #4 | PG↔Neo4j 역방향 reconciliation 야간 배치 추가 |
| 5 | 🟠 Medium #5 | `update_or_create` lookup ↔ unique 제약 매핑 검증 |
| 6 | 🟡 Low | news 동기화를 `neo4j_synced` 플래그 패턴으로 통일 / portfolio 5단계 체인 soft-delete 검토 |

---

*본 보고서는 정적 코드 분석 기반의 읽기 전용 감사입니다. 실제 데이터 분포·운영 로그·Neo4j 현황을 반영한 동적 검증은 별도 수행을 권장합니다.*
