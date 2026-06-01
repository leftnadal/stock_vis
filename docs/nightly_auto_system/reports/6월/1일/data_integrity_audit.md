# 데이터 무결성 감사 보고서

> **감사일**: 2026-06-01
> **범위**: FK orphan 위험 / CASCADE 체인 / Neo4j↔PG 동기화 / Unique 제약
> **모드**: 읽기 전용 (코드 수정 없음)
> **비고**: 지시서의 경로 가정(`sec_pipeline/models.py`, `serverless/models.py` 등 루트 기준)은
> monorepo 재편으로 실제와 다름. 실제 경로는 `services/*`, `apps/*`, `packages/shared/*` 기준으로 재매핑하여 감사함.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 이슈 |
|--------|------|------|
| 🔴 High | 2 | ① SET_NULL(`target_company`) 후 Neo4j 엣지 orphan + `neo4j_dirty` 재설정 누락 / ② Stock CASCADE 삭제 시 Neo4j 노드·엣지 orphan (PG↔Neo4j 양방향 reconcile 부재) |
| 🟡 Medium | 3 | ③ `update_or_create` race condition (Celery 중복 실행) / ④ 역방향 불일치(Neo4j→PG) 감지 메커니즘 부재 / ⑤ Neo4j sync task `max_retries=1` |
| 🟢 Low | 2 | ⑥ SET_NULL self-FK 순환 안전 확인 / ⑦ `target_company_name` 잔존 (의도된 설계) |

**핵심 결론**: PostgreSQL 내부 참조 무결성은 CASCADE/SET_NULL로 잘 설계됨.
**가장 큰 위험은 PostgreSQL과 Neo4j 사이의 경계**다. PG의 CASCADE 삭제와 SET_NULL은
Neo4j를 전혀 인지하지 못하므로, PG 행이 사라져도 Neo4j 노드·엣지는 그대로 남는다.
단방향(PG→Neo4j) `neo4j_dirty` 동기화만 존재하고 **역방향·삭제 reconcile이 없다.**

---

## FK orphan 위험

### SET_NULL 사용처 (지시서 명시 7곳 = 정확)

지시서가 지목한 3개 파일 7곳은 정확히 일치한다:

| # | 파일 | 모델.필드 | 대상 | 비고 |
|---|------|-----------|------|------|
| 1 | `services/sec_pipeline/models.py:94` | `SupplyChainEvidence.target_company` | `stocks.Stock` | **🔴 핵심 위험** |
| 2 | `services/serverless/models.py:660` | `ScreenerAlert.preset` | `ScreenerPreset` | 커스텀 필터 fallback (의도) |
| 3 | `services/serverless/models.py:797` | `InvestmentThesis.user` | `users.User` | 작성자 탈퇴 시 테제 보존 |
| 4 | `services/serverless/models.py:1353` | `ServerlessActionLog.user` | `users.User` | 감사 로그 보존 |
| 5 | `services/rag_analysis/models.py:132` | `AnalysisSession.basket` | `DataBasket` | 바스켓 삭제해도 세션 이력 보존 |
| 6 | `services/rag_analysis/models.py:232` | `TokenUsageLog.session` | `AnalysisSession` | 과금 로그 보존 |
| 7 | `services/rag_analysis/models.py:239` | `TokenUsageLog.message` | `AnalysisMessage` | 과금 로그 보존 |

> **추가 발견** (지시서 범위 밖이지만 동일 패턴): SET_NULL은 다른 앱에도 존재한다 —
> `apps/portfolio/models.py`(3곳: `wallet_snapshot_at_execution`, `analysis_run`, `context_analysis_run`),
> `apps/chain_sight/models/news_event.py:69`(self-FK `duplicate_of`),
> `macro/models/indicators.py:310`(`related_indicator`),
> `thesis/models/*`(4곳: `news_source`, `copied_from`, `indicator`, `premise`),
> `apps/market_pulse/models/anomaly.py:26`(`paired_news`).
> 이들은 대부분 "참조 대상 삭제 시 본체 이력 보존"이라는 올바른 의도의 SET_NULL이다.

### SET_NULL 후 orphan 정리 로직 — **부재 (전수 확인)**

- **management command 전수 조사**: orphan/cleanup/prune 키워드로 매칭된 것은
  `rag_analysis/.../setup_semantic_cache.py`(캐시 셋업, 무관),
  `sec_pipeline/.../rematch_unmatched.py`(unmatched **재매칭**, orphan 삭제 아님) 뿐.
  **NULL이 된 레코드를 정리·삭제하는 전용 로직은 존재하지 않는다.**
- 대부분의 SET_NULL은 "본체(로그/세션/테제)를 일부러 살려두는" 설계이므로 정리 불필요가 정상.
- **단, #1 `SupplyChainEvidence.target_company`는 예외적으로 위험하다** ↓

### 🔴 High ① — SET_NULL(`target_company`) 후 Neo4j 엣지 orphan

`services/sec_pipeline/models.py:92-99`
```python
target_company = models.ForeignKey(
    "stocks.Stock", on_delete=models.SET_NULL, null=True, ...
)
```

**시나리오**: Stock(A)가 다른 Stock(B)의 10-K supply-chain 타깃이라 `SUPPLIES_TO` 엣지가
Neo4j에 생성된 상태에서 A가 삭제되면:
1. PG에서 `target_company` → `NULL` (SET_NULL)
2. `quality_checks.py:142`에서 해당 evidence는 다시 `unmatched`로 분류됨
3. **그러나 `neo4j_dirty`가 다시 `True`로 세팅되지 않는다** → 동기화 task가
   이 행을 집어들지 않음 (`sync_dirty_to_neo4j`는 `neo4j_dirty=True AND target_company__isnull=False` 필터, `tasks.py:430`)
4. **결과: Neo4j의 `SUPPLIES_TO` 엣지가 영구 잔존** (orphan edge)

> SET_NULL은 DB 시그널일 뿐 `save()`를 호출하지 않으므로 모델의 dirty 토글 로직도 작동하지 않는다.
> 정리하려면 `post_delete`/`pre_delete` 시그널 또는 별도 reconcile job이 필요한데 둘 다 없음.

---

## CASCADE 체인

### CASCADE 사용처 분포 (실측)

`migrations`/`test` 제외 약 90+ 건. 주요 파일:

| 영역 | 파일 | 비고 |
|------|------|------|
| 가격·재무 | `packages/shared/stocks/models.py` (6곳) | Stock → DailyPrice/WeeklyPrice/재무3종/Overview |
| 사용자 | `packages/shared/users/models.py` (6곳) | User/Stock → Portfolio/Watchlist/Interest |
| 포트폴리오 | `apps/portfolio/models.py` (13곳) | User/Stock 기반 분석 트리 |
| SEC | `services/sec_pipeline/models.py` (6곳) | **3단계 연쇄 존재** ↓ |
| Chain Sight | `apps/chain_sight/models/*` (9곳) | Stock → 프로파일 9종 |
| Validation | `services/validation/models/*` (8곳) | Stock → metric/benchmark/score |
| Metrics | `packages/shared/metrics/models/*` (5곳) | Stock → snapshot/benchmark |
| RAG | `services/rag_analysis/models.py` (4곳) | User/Basket/Session 트리 |
| News | `services/news/models.py` (2곳) | Article → Entity → Highlight |
| Macro/Thesis/MarketPulse | 다수 | 내부 트리 |
| `_dormant/graph_analysis` | (8곳) | **휴면 앱** — 영향 평가 제외 |

### 3단계 이상 연쇄 삭제 추적

**가장 깊은 체인 (4-노드 / 3단계 연쇄)** — SEC 파이프라인:
```
Stock (삭제)
 └─[CASCADE]→ RawDocumentStore            (sec_raw_document_store)
      ├─[CASCADE]→ SupplyChainEvidence     (sec_supply_chain_evidence)   ← Neo4j 엣지 연결
      └─[CASCADE]→ BusinessModelSnapshot   (sec_business_model_snapshot)
            └─[CASCADE]→ BusinessModelEvidence (sec_business_model_evidence)
```
- `Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence` = **3단 연쇄**
- 추가 분기: `News` 체인도 `NewsArticle → NewsEntity → NewsEntityHighlight` 3-노드 2단 연쇄.

**RelationConfidence 체인** (`apps/chain_sight`): `update_or_create`로 생성되며
`neo4j_dirty`로 Neo4j 엣지와 연결됨 — 아래 Neo4j 섹션 참조.

### Stock 삭제 시 영향 범위 (최다 FK 참조 허브)

`Stock`은 **시스템 전체의 참조 허브**다. Stock 1건 삭제 시 CASCADE로 함께 삭제되는 테이블:

| 앱 | 삭제되는 데이터 |
|----|----------------|
| stocks | DailyPrice, WeeklyPrice, 재무제표 3종(income/balance/cashflow), CompanyOverviewKo(OneToOne), 기타 |
| users | Portfolio, WatchlistItem, UserInterest(M2M `favorite_stock` 포함) |
| portfolio | Holding 및 하위 분석 트리 |
| sec_pipeline | RawDocumentStore → (Evidence + Snapshot → Evidence) **전체 서브트리** |
| chain_sight | GrowthStage, CapitalDNA, Sensitivity, NarrativeTag, EventReaction, RevenueStructure, InsiderSignal, ChainProfile 등 9종 |
| validation | MetricLatest, BenchmarkDelta, CategoryScore, NewsSummary, PeerPreset |
| metrics | MetricSnapshot, Benchmark |

**주의점 1 — `to_field="symbol"`**: `DailyPrice`/`WeeklyPrice`(`stocks`),
`Portfolio`/`WatchlistItem`(`users`)는 `to_field="symbol"`로 PK(id)가 아닌 `symbol` 컬럼을 참조한다
(`stocks/models.py:194,306`, `users/models.py:47,223`). symbol은 사실상 불변 키로 운용되므로 현재 안전하나,
symbol 갱신 로직이 추가되면 FK 정합성 깨짐 위험 — 변경 금지 불변식으로 유지 권장.

**주의점 2 — 🔴 High ②**: 위 CASCADE는 모두 **PostgreSQL 내부에서만** 작동한다.
chain_sight/sec의 노드·관계는 Neo4j에도 미러링되어 있으나, Stock 삭제 시
**Neo4j의 `:Stock` 노드와 모든 연결 엣지는 그대로 남는다** (CASCADE는 Neo4j를 모름).
→ orphan Neo4j 노드/엣지 누적. 이를 정리하는 `post_delete` 훅이나 reconcile job 없음.

---

## Neo4j 동기화

### `neo4j_dirty` 단일 소스 패턴 (audit P0 #9, 2026-04-29 통일)

과거 `synced_to_neo4j`/`neo4j_synced`(반전 의미)가 혼재했으나
마이그레이션 `chain_sight/0008_unify_neo4j_flags.py`에서 **`neo4j_dirty` 단일 소스**로 통일됨.
의미: `dirty=True` → "동기화 필요". 사용 현황:

| 모델 | 위치 | dirty 토글 방식 |
|------|------|----------------|
| `CompanyChainProfile` | `apps/chain_sight/models/chain_profile.py:84` | `update_or_create` 시 `defaults={"neo4j_dirty":True}` (`sync_tasks.py:40,94`) |
| `RelationConfidence` | `apps/chain_sight/models/relation_discovery.py:148` | `save()` 자동 + `bulk update`는 수동 토글(`relation_tasks.py:421-435`) |
| `SupplyChainEvidence` | `services/sec_pipeline/models.py:112` | `update_or_create`의 `save()`가 자동 `True` |

세 모델 모두 `neo4j_dirty`에 **db_index** 적용 → 큐 조회 성능 확보.

### 동기화 task 및 재시도 메커니즘

| Task | 위치 | 재시도 | 패턴 | 평가 |
|------|------|--------|------|------|
| `sync_profiles_to_neo4j` | `apps/chain_sight/tasks/sync_tasks.py:107` | `max_retries=1` | per-row try/except, 실패 시 dirty 유지 | 🟢 self-healing (다음 주기 재시도) |
| `sync_relations_to_neo4j` | `sync_tasks.py:173` | `max_retries=1` | `sync_dirty_relations()` 위임 + 레거시 1회 정리 | 🟢 |
| `sync_dirty_to_neo4j` (SEC) | `services/sec_pipeline/tasks.py:398` | `max_retries=1` | **2-Phase + `select_for_update(skip_locked=True)`** | 🟢 race 방어 우수 |

**`sync_dirty_to_neo4j` 강점** (`tasks.py:426-527`):
- Phase A: PG 트랜잭션 안에서 `select_for_update(skip_locked=True)[:500]`으로 행 lock + dict 복사
  → 동시 워커 충돌 방지 (잠긴 행은 skip).
- Phase B: Neo4j는 **DELETE(known_types 전체) + CREATE(dynamic type)** 멱등 패턴.
- Phase C: 성공한 `id`만 `neo4j_dirty=False` 일괄 업데이트 → **부분 실패 시 실패 행은 dirty 유지**.
- Phase B가 PG 트랜잭션 밖이므로 중간 크래시 시 일부 엣지만 DELETE된 상태 가능하나,
  멱등 DELETE+CREATE라 다음 주기에 자동 복구 (dirty=True 유지) → **허용 가능한 위험**.

### 🟡 Medium ⑤ — `max_retries=1` 한계

세 sync task 모두 `max_retries=1`. per-row try/except로 개별 실패는 흡수되지만,
**Neo4j 연결 자체가 죽으면 task 전체가 1회만 재시도**하고 포기한다.
다만 `neo4j_dirty=True`가 유지되므로 **다음 Beat 주기(SEC 5분, chain_sight 주1회)에 재집계**됨.
→ 데이터 유실은 없으나 chain_sight는 복구까지 최대 1주 지연 가능.

### 불일치 감지 메커니즘

| 방향 | 감지 | 위치 |
|------|------|------|
| PG→Neo4j 적체 | ✅ `neo4j_pending` = `dirty=True AND matched` 카운트 | `sec_pipeline/quality_checks.py:144` |
| dirty backlog 알림 | ✅ matched dirty > 50건 시 알림 | 테스트 `test_sec_pipeline_30plus.py:414` 확인 |
| **Neo4j→PG 역방향** | ❌ **부재** | — |
| **PG 삭제 후 Neo4j orphan** | ❌ **부재** | — |

### 🟡 Medium ④ — 역방향·삭제 reconcile 부재

현재 불일치 감지는 **PG→Neo4j 단방향 적체(pending count)만** 본다.
다음은 감지 불가:
1. **Neo4j엔 있는데 PG엔 없는 엣지/노드** (위 High ①②의 결과물) — 카운트·알림 모두 없음.
2. PG `count` vs Neo4j `count` 대조 job 없음.

**권장 (수정 아님, 제안)**: 주기적 reconcile job —
`Neo4j 엣지(source='sec_10k')`의 (source,target) 집합 vs `PG SupplyChainEvidence(dirty=False, matched)` 집합을
대조하여 PG에 없는 Neo4j 엣지를 orphan으로 삭제. Stock `post_delete` 시그널로 Neo4j 노드 정리 훅 추가.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 (실측)

`migrations`/`test` 제외 주요 설정 (정상적으로 풍부하게 설정됨):

| 모델 | 제약 | 위치 |
|------|------|------|
| DailyPrice / WeeklyPrice | `(stock, date)` | `stocks/models.py:246,275` |
| 재무제표 3종 | `(stock, period_type, fiscal_year, fiscal_quarter)` | `stocks/models.py:492,607,765` |
| CompanyOverviewKo | `(stock, date)` | `stocks/models.py:1048` |
| EODSignal | `(stock, signal_date, signal_tag)` | `stocks/models.py:1087` |
| Portfolio / Watchlist / Interest | `(user,stock)` / `(user,name)` / `(user,interest_type,value)` | `users/models.py:90,201,242,291` |
| MetricSnapshot / Benchmark 류 | `(symbol, fiscal_year, metric_code [,preset_key])` | `metrics/models/*` |
| CompanyAlias | `(alias, context_sector)` — country 제외(주석 명시) | `sec_pipeline/models.py:331` |
| ChainNewsEvent | `(source, source_id)` | `chain_sight/.../news_event.py:79` |
| CompanyEventReaction | `(symbol, event_type)` | `event_reaction.py:55` |
| RelationDiscovery / RelationConfidence | `(symbol_a, symbol_b [,period])` | `relation_discovery.py:25,54` |
| ThesisSnapshot / ThesisIndicatorValue 등 | thesis 4종 | `thesis/models/*` |
| Macro 지표 | `(indicator, date)` 등 4종 | `macro/models/*` |

> `RawDocumentStore.accession_no`는 필드 레벨 `unique=True` (`sec_pipeline/models.py:30`).

### 🟡 Medium ③ — `update_or_create` race condition

`update_or_create` 총 **127건** 사용 (test 제외). Django의 `update_or_create`는
**원자적이지 않다** — 내부적으로 `get → (없으면) create` 후 IntegrityError 시 1회 재조회한다.
동시 실행 시 race 위험 지점:

| 호출 | 위치 | unique 보호 | 위험도 |
|------|------|------------|--------|
| `RawDocumentStore` (`accession_no`) | `sec_pipeline/tasks.py:138` | ✅ `unique=True` | 🟢 IntegrityError → 재조회로 수렴 |
| `CompanyChainProfile` (`symbol`) | `chain_sight/tasks/sync_tasks.py:94` | ✅ symbol OneToOne성 | 🟢 |
| `RelationConfidence` (`symbol_a,symbol_b`) | `relation_tasks.py:299,335,374` + `sec_pipeline/tasks.py:372` | ✅ unique_together | 🟡 **다중 경로 동시 호출** |
| `StockRelationship` / `ThemeMatch` / `StockKeyword` | `serverless/services/*` 다수 | ⚠️ 모델별 확인 필요 | 🟡 Celery Beat 중복 실행 시 |
| `SentimentHistory` | `news/tasks.py:314` | `(symbol, date)` unique_together | 🟢 |

**핵심 리스크**: `RelationConfidence`는 **sec_pipeline과 chain_sight 양쪽**에서
서로 다른 task가 같은 `(symbol_a, symbol_b)` 키로 `update_or_create`를 호출한다
(`sec_pipeline/tasks.py:372` + `relation_tasks.py:299/335/374`).
unique_together가 IntegrityError로 중복 생성은 막지만, **두 task가 동시 실행되면
서로의 update를 덮어쓰는 lost-update**가 가능하다 (last-writer-wins).
`neo4j_dirty` 토글이 한쪽에서 누락될 수 있어 동기화 지연으로 이어질 수 있음.

**완화 현황**: 진짜 임계 경로(`Watchlist`, `DataBasket`, SEC sync)는
`select_for_update`로 명시적 lock을 건다 (`users/views.py:735,929`, `rag_analysis/views.py:116,217`,
`sec_pipeline/tasks.py:433`). → 사용자 직접 트리거 경로는 방어됨. **백그라운드 task 간 race가 잔여 위험.**

---

## 부록 — 위험도별 권장 조치 (제안, 코드 미수정)

| # | 위험 | 권장 (제안) |
|---|------|------------|
| ① 🔴 | SET_NULL 후 Neo4j 엣지 orphan | Stock `pre_delete` 시그널에서 해당 evidence `neo4j_dirty=True` 토글 + target NULL 엣지 정리 |
| ② 🔴 | Stock CASCADE → Neo4j orphan | Stock `post_delete` 시그널 → Neo4j `:Stock` 노드+엣지 DETACH DELETE |
| ③ 🟡 | update_or_create lost-update | `RelationConfidence` 단일 writer로 통합하거나 `select_for_update` 적용 |
| ④ 🟡 | 역방향 불일치 미감지 | 주기적 PG↔Neo4j count·집합 대조 reconcile job 신설 |
| ⑤ 🟡 | sync max_retries=1 | Neo4j 연결 예외 한정 backoff 재시도 상향 (현재도 dirty 유지로 유실은 없음) |
| ⑥ 🟢 | SET_NULL self-FK 순환 | `duplicate_of`/`copied_from`는 self 참조이나 순환 삭제 없음 — 안전, 조치 불요 |
| ⑦ 🟢 | `target_company_name` 잔존 | 재매칭(`rematch_unmatched`)용 의도된 설계 — 조치 불요 |

---

*본 보고서는 정적 코드 분석 기반이며 운영 DB 실데이터를 조회하지 않았다.
①②의 실제 orphan 발생 여부는 Neo4j 엣지 수 vs PG 행 수 대조 쿼리로 별도 실측 권장.*
