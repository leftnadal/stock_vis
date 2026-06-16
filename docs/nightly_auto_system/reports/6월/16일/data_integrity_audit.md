# 데이터 무결성 감사 보고서

> 생성일: 2026-06-16
> 범위: 읽기 전용 정적 분석 (코드 수정 없음)
> 대상: 모노레포 전체 (`packages/shared`, `services`, `apps`, `thesis`, `macro`)
> 방법: `on_delete`·`neo4j_dirty`·`unique_together`·`update_or_create` 정적 grep + 핵심 모델/태스크 정독

---

## 요약 (위험도별 이슈 수)

| 위험도 | 수 | 핵심 이슈 |
|--------|----|----------|
| 🔴 High | 3 | ① SET_NULL orphan 후 정리 로직 부재 (sec_pipeline target_company) <br> ② Neo4j ↔ PG 불일치 감지 메커니즘 전무 (단방향 sync) <br> ③ Stock CASCADE 삭제 시 Neo4j 노드/엣지 고아화 |
| 🟠 Medium | 3 | ④ 3~4단계 CASCADE 체인 (Stock→RawDoc→Snapshot→Evidence) <br> ⑤ `update_or_create` race condition (동시 Celery 워커) <br> ⑥ Neo4j sync 재시도 `max_retries=1` 빈약 |
| 🟡 Low | 2 | ⑦ `neo4j_dirty=True` 좀비 row 잔류 (sync 큐 영구 제외) <br> ⑧ 지시서 추정치와 실제 사용처 격차 (SET_NULL 7→17곳, 모노레포 재편 반영 안 됨) |

**전제 정정**: 지시서는 모노레포 재편(`d4407f6`/`da5d992` 병합) 이전 경로를 기준으로 작성됨. 실제 구조는 `stocks/`→`packages/shared/stocks/`, `users/`→`packages/shared/users/`, `chainsight`→`apps/chain_sight/`, `macro`→`apps/market_pulse` + `macro/`로 이동. 본 보고서는 **현재 트리 기준 실측치**를 사용한다.

- `on_delete=SET_NULL` 실측: **17곳 / 11개 파일** (지시서 추정 7곳/3파일)
- `on_delete=CASCADE` 실측: **80곳+ / 20개 파일** (지시서 추정 37곳/7파일). `services/_dormant/graph_analysis`는 휴면 처리되어 운영 영향 없음.

---

## FK orphan 위험

### SET_NULL 사용처 전수 (17곳)

| # | 파일:라인 | 모델.필드 | 참조 대상 | orphan 후 영향 |
|---|-----------|-----------|-----------|----------------|
| 1 | `services/sec_pipeline/models.py:94` | `SupplyChainEvidence.target_company` | `stocks.Stock` | 🔴 **핵심** — 아래 상세 |
| 2 | `services/rag_analysis/models.py:132` | `AnalysisSession.basket` | `DataBasket` | 세션은 보존, 분석 컨텍스트 소실 |
| 3 | `services/rag_analysis/models.py:232` | `UsageLog.session` | `AnalysisSession` | 비용 로그 보존(정상 의도) |
| 4 | `services/rag_analysis/models.py:239` | `UsageLog.message` | `AnalysisMessage` | 비용 로그 보존(정상 의도) |
| 5 | `services/serverless/models.py:660` | `ScreenerAlert.preset` | `ScreenerPreset` | 프리셋 삭제 시 커스텀 필터로 강등(정상 의도) |
| 6 | `services/serverless/models.py:797` | `InvestmentThesis.user` | `users.User` | 탈퇴 후 테제 보존 |
| 7 | `services/serverless/models.py:1353` | `AdminActionLog.user` | `users.User` | 감사 로그 보존(정상 의도) |
| 8 | `apps/chain_sight/models/news_event.py:69` | `ChainNewsEvent.duplicate_of` | self FK | 원본 삭제 시 중복 링크 끊김 |
| 9~17 | `thesis/models/thesis.py:70,77` · `thesis/models/indicator.py:15` · `thesis/models/monitoring.py:66` · `apps/market_pulse/models/anomaly.py:35` · `macro/models/indicators.py:310` · `apps/portfolio/models.py:341,768,870` | 다수 | 다양 | 메타/로그성, 대체로 의도된 보존 |

### 🔴 High: SET_NULL 후 orphan 레코드 정리 로직 부재

**핵심 사례 — `SupplyChainEvidence.target_company`**

```
target_company FK (SET_NULL) ──삭제──> NULL
                                        │
sync_dirty_to_neo4j (tasks.py:430)      ▼
  filter(neo4j_dirty=True, target_company__isnull=False)  ← NULL을 영구 제외
```

- Stock이 삭제되면 `target_company`가 NULL이 되지만, `target_company_name`(문자열)은 남아 "댕글링 증거"가 됨.
- Neo4j sync 큐(`sync_dirty_to_neo4j`, `quality_checks.py:93,145`, `intelligence.py:102`)는 **모두 `target_company__isnull=False`로 NULL을 필터링** → 이 레코드는 Neo4j에 영원히 반영되지 않음.
- 만약 삭제 직전 `neo4j_dirty=True`였다면 → **영구 dirty 좀비 row**로 잔류 (이슈 ⑦).
- **정리 로직 부재 확인**: `target_company__isnull=True` AND `neo4j_dirty=True`인 좀비를 청소하거나, Neo4j에서 해당 엣지를 제거하는 cleanup 태스크가 존재하지 않음. 재매칭은 `signals.py`/`ticker_matcher.py`가 `target_company`를 다시 채우면 `neo4j_dirty=True`로 복구하지만, **재매칭이 영원히 일어나지 않을 수도** 있음.

**권고**: 주기적 청소 태스크 (`target_company__isnull=True` & 오래된 dirty → status 격리), 또는 Stock 삭제 시 연관 Neo4j 엣지 제거 신호 추가.

**나머지 16곳**: 대부분 로그·감사·메타성으로 NULL 보존이 의도된 설계(✅). 별도 정리 불필요하나, #8 `duplicate_of` self-FK는 원본 삭제 시 `is_duplicate=True`가 남아 정합성이 깨질 수 있음(🟡).

---

## CASCADE 체인

### 🟠 Medium: 3단계 이상 연쇄 삭제 체인

**체인 1 — SEC 파이프라인 (최대 깊이)**

```
Stock (symbol, PK)
  └─CASCADE─> RawDocumentStore (sec_pipeline/models.py:24)
       ├─CASCADE─> SupplyChainEvidence.source_document (models.py:81)   [2단계]
       └─CASCADE─> BusinessModelSnapshot.source_document (models.py:179)
                    └─CASCADE─> BusinessModelEvidence.snapshot (models.py:241)   [3단계]
```
추가로 `BusinessModelSnapshot.symbol`(:173)과 `SupplyChainEvidence.source_company`(:86)도 **Stock 직참조 CASCADE**. 즉 Stock 한 건 삭제 시 RawDoc 경유 + 직참조 양쪽으로 동일 자식이 삭제됨(중복 경로지만 결과 동일).

**체인 2 — RAG 분석**
```
User ─CASCADE─> AnalysisSession (rag_analysis:128) ─CASCADE─> AnalysisMessage (:177)
User ─CASCADE─> DataBasket (:14) ─CASCADE─> BasketItem (:73)
(UsageLog는 session/message에 SET_NULL → User에는 CASCADE:227, 단 null=True)
```

**체인 3 — 사용자 데이터**
```
User ─CASCADE─> Watchlist (users:191) ─CASCADE─> WatchlistItem (:221)
User ─CASCADE─> Portfolio (:46) ─CASCADE─> (apps/portfolio 12+ CASCADE 자식들)
```
`apps/portfolio/models.py`는 CASCADE 12곳 + UniqueConstraint 4곳으로 가장 조밀한 체인을 가짐. Wallet→거래/포지션 계층이 깊어 단일 User 삭제가 광범위 삭제를 유발.

### Stock 삭제 시 영향 범위 (가장 많은 FK 참조)

Stock은 `to_field="symbol"` 또는 `stocks.Stock` 직참조로 **20곳+ 모델에서 CASCADE 참조**됨:

| 영역 | CASCADE 자식 (대표) |
|------|---------------------|
| stocks | DailyPrice, WeeklyPrice, 재무제표 3종(income/balance/cashflow), StockOverviewKo, EODSignal 등 (`packages/shared/stocks/models.py`) |
| metrics | CompanyMetricSnapshot, PeerMetricBenchmark (`packages/shared/metrics`) |
| chain_sight | CompanyChainProfile, CapitalDNA, GrowthStage, NarrativeTag, Sensitivity, RevenueStructure, InsiderSignal, EventReaction, Attention, ChainNewsEvent (10종, `apps/chain_sight/models/*`) |
| sec_pipeline | RawDocumentStore, SupplyChainEvidence(source), BusinessModelSnapshot |
| news/market_pulse | EntityHighlight 등 |

⚠️ **연쇄 폭발 위험**: 단일 Stock 삭제 = 수천~수만 row(가격·재무·시그널) + 10여 개 chain_sight 프로파일 동시 삭제. `DB_CASCADE`는 트랜잭션 단위라 대형 종목(AAPL 등) 삭제 시 **장시간 락**. 운영 상 Stock 하드 삭제는 사실상 금지되어야 하며, soft-delete(`is_active` 플래그) 패턴 미적용은 잠재 위험.

⚠️ **Neo4j 누락**: Stock CASCADE 삭제는 PG row만 제거하고 **Neo4j `:Stock` 노드와 엣지는 잔류** → 이슈 ③ (아래).

---

## Neo4j 동기화

### 설계 현황 — `neo4j_dirty` 단일 소스 (audit P0 #9, 2026-04-29)

| 앱 | 모델 | dirty 필드 | sync 태스크 |
|----|------|-----------|-------------|
| sec_pipeline | `SupplyChainEvidence` | `neo4j_dirty`(:112) + `neo4j_synced_at`(:113), 인덱스 有 | `sync_dirty_to_neo4j` (tasks.py:397) |
| chain_sight | `RelationConfidence` | `neo4j_dirty`(relation_discovery.py:148) | `sync_dirty_relations` (services/neo4j_sync.py:22) |
| chain_sight | `CompanyChainProfile` | `neo4j_dirty`(chain_profile.py:84) | `sync_profiles_to_neo4j` (tasks/sync_tasks.py:108) |

- ✅ **단일 소스 통일 완료**: `synced_to_neo4j` 폐기, `neo4j_synced`(반전 의미) → `neo4j_dirty`로 마이그레이션(`migrations/0008_unify_neo4j_flags.py`). 의미 일관성 확보.
- ✅ **save() 우회 처리**: `queryset.update()`는 `save()` 미호출 → dirty 자동 세팅 안 됨. 이를 인지하고 `relation_tasks.py:415,421` 등에서 **수동 `neo4j_dirty=True` 토글**. `bulk_update` 케이스도 `relation_discovery.py:178`에서 명시 처리. (양호)
- ✅ **idempotent sync**: `sync_dirty_to_neo4j`는 DELETE+CREATE 패턴(MERGE 금지), `select_for_update(skip_locked=True)` 2-Phase로 동시성 안전.

### 🟠 Medium: 재시도 메커니즘 빈약 (`max_retries=1`)

- 세 sync 태스크 모두 `max_retries=1` (sync_tasks.py:107, tasks.py:397). 1회 재시도만.
- 다만 **실패 건은 `neo4j_dirty=True`로 잔류** → 다음 Celery Beat 주기에 자동 재포함(eventual consistency). 즉 단건 실패는 self-healing.
- 개별 row 실패는 `try/except`로 격리되어 배치 전체가 죽지 않음(neo4j_sync.py:43, tasks.py:514). 양호.
- ⚠️ 단, **백오프 없는 즉시 재시도 1회**라 Neo4j 일시 다운 시 해당 배치 전량이 dirty로 남아 다음 주기까지 지연. backoff/주기 단축 고려 여지.

### 🔴 High: PG ↔ Neo4j 불일치 감지 메커니즘 전무

- 동기화는 **PG → Neo4j 단방향**. `tasks.py:410` 주석에 "Phase 1에서 이 함수가 Neo4j SOLE WRITER" 명시.
- **불일치 감지 수단 부재**:
  - 현재 모니터링(`quality_checks.py`, `intelligence.py`)은 **dirty backlog count만** 측정 (`neo4j_dirty=True` 건수). "PG엔 있는데 Neo4j에 없다/반대"를 직접 비교하지 않음.
  - `neo4j_dirty=False`인데 실제 Neo4j 엣지가 없는 경우(write 유실) → **영원히 감지 안 됨** (dirty=False라 sync 큐에서 제외).
- **🔴 Neo4j 고아 노드/엣지**: Stock·관계가 PG에서 CASCADE/SET_NULL로 사라져도 Neo4j 정리 트리거 없음. `sync_dirty_to_neo4j`는 "추가/갱신"만 하고, 삭제는 `relation_status`가 weak/stale/hidden일 때만(`neo4j_sync.py:80` `_delete_edge`). **PG row 자체 삭제 → Neo4j orphan**.
  - 부분 완화: `sec_pipeline/tasks.py:471` DELETE+CREATE는 `source='sec_10k'` 엣지를 매 sync마다 지우므로 **재sync되는 엣지에 한해** 자정작용 있음. 그러나 source row가 PG에서 사라지면 재sync가 안 일어나 orphan 영구화.

**권고**:
1. PG ↔ Neo4j 정합성 검증 태스크 신설 (PG 엣지 set vs Neo4j 엣지 set diff, 주 1회).
2. Stock/Relation 삭제 시 Neo4j 엣지·노드 제거를 트리거하는 post_delete 시그널 또는 청소 배치.
3. `neo4j_synced_at`이 오래됐는데 dirty=False인 건에 대한 sanity 재검증.

---

## Unique 제약조건

### 현황 — 광범위 적용 (양호)

- `unique_together` / `UniqueConstraint`가 **50곳+ 모델**에 설정됨. 시계열 데이터는 일관되게 `(symbol/stock, date)` 패턴, 재무는 `(stock, period_type, fiscal_year, fiscal_quarter)` 패턴 적용. 설계 일관성 우수.
- `apps/portfolio/models.py`는 `models.UniqueConstraint`(:459,551,611,734) 4곳으로 조건부 unique 활용 (구버전 `unique_together`보다 표현력 높음).
- validation 앱은 `preset_key`를 unique 키에 추가(`benchmark_delta:80`, `category_score:64`)하여 프리셋별 격리 — 멀티 프리셋 충돌 방지 설계 양호.

### 🟠 Medium: `update_or_create` race condition

- `update_or_create` / `get_or_create` 사용처 **70곳+** (validation·serverless·news·chain_sight·macro 전반).
- **구조적 한계**: Django `update_or_create`는 원자적이지 않음 — 내부적으로 `SELECT → (없으면) INSERT → (있으면) UPDATE`. 동시 트랜잭션이 같은 키로 진입하면 **두 번째가 IntegrityError**.
- **다행인 점**: 거의 모든 대상 모델에 대응 `unique_together`가 존재 → DB가 중복 INSERT를 IntegrityError로 차단(데이터 중복은 발생 안 함). 즉 **데이터 무결성은 보장**되나 **태스크가 예외로 실패**할 수 있음.
- **위험 지점 — 동시 Celery 워커**:
  - `services/serverless/tasks.py:414,1471`, `services/news/tasks.py:314`, `apps/chain_sight/tasks/relation_tasks.py:317`(StockKeyword/StockRelationship/SentimentHistory/RelationConfidence) — 같은 종목을 여러 워커가 동시 처리하면 충돌 가능.
  - 대부분 `bind=True, max_retries=3` 재시도로 흡수되나, IntegrityError를 명시 핸들링하는 곳은 확인되지 않음(`rag_analysis/views.py:134`만 주석으로 인지).
- **권고**: 고빈도 동시 경로는 `update_or_create`를 트랜잭션 + `select_for_update`로 감싸거나, PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`(Django 4.1+ `QuerySet.bulk_create(update_conflicts=...)`) 전환 검토.

### 🟡 Low: 마이그레이션 정합성 양호

- `unique_together` 변경 이력이 마이그레이션에 추적됨(예: `validation/migrations/0004`에서 `preset_key` 추가 시 `unique_together=set()`으로 비우고 재설정). 모델 정의와 마이그레이션 상태 일치 확인됨.

---

## 부록: 검증된 양호 항목 (오탐 방지)

- ✅ `neo4j_dirty` 단일 소스 통일 — `synced_to_neo4j` 완전 제거(`migrations/0008`).
- ✅ `queryset.update()`/`bulk_update`에서 dirty 수동 토글 누락 없음.
- ✅ sync 태스크 idempotent (DELETE+CREATE, skip_locked, row별 예외 격리).
- ✅ 실패 건 dirty 잔류로 eventual self-healing.
- ✅ unique 제약 설계 일관성 (시계열·재무·프리셋 패턴화).
- ✅ rag_analysis `UsageLog`의 session/message SET_NULL + User CASCADE는 "비용 로그 보존" 의도에 부합.

---

## 우선순위 권고 (요약)

| 순위 | 조치 | 대상 |
|------|------|------|
| 1 | PG↔Neo4j 정합성 diff 검증 배치 신설 + Stock/Relation 삭제 시 Neo4j orphan 청소 | sec_pipeline, chain_sight |
| 2 | `target_company__isnull=True` 좀비 dirty row 청소 태스크 | sec_pipeline |
| 3 | Stock soft-delete(`is_active`) 패턴 도입 검토 (하드 삭제 락·연쇄폭발 방지) | packages/shared/stocks |
| 4 | 고빈도 동시 `update_or_create`를 `ON CONFLICT` 또는 select_for_update로 강건화 | serverless, news, chain_sight tasks |
| 5 | sync 태스크 `max_retries` 상향 + 지수 백오프 | 3개 sync 태스크 |

> 본 보고서는 정적 분석 기반이며, 실제 orphan/불일치 건수는 운영 DB·Neo4j 대조 쿼리로 별도 정량화 필요.
