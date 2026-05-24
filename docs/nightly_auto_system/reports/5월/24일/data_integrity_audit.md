# 데이터 무결성 감사 보고서

- **생성일**: 2026-05-24
- **브랜치**: security/c2-backend-deps
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 범위**: ORM 모델 36개 파일, FK on_delete 정책, Neo4j 동기화, Unique 제약

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|------|------|---------|
| 🔴 P0 (즉시 대응) | 2 | (1) Stock 단건 삭제 시 무경고 대량 CASCADE (15+ 모델, 수십만 row) — PROTECT 가드 없음. (2) PG-Neo4j 능동 reconciliation 부재 — dirty 플래그 유실 시 영구 drift |
| 🟠 P1 (단기) | 4 | (3) SET_NULL orphan 정리 잡 부재 (5종). (4) update_or_create race 가능성 (103건 운영). (5) `RelationConfidence.save()`의 무조건 `dirty=True` → bulk_update 모순. (6) sec_pipeline signal: 같은 `raw_name` 다른 sector 가진 큐 행 처리 시 매번 중복 update 가능 |
| 🟡 P2 (중기) | 3 | (7) Portfolio/ScenarioRun 4단계 CASCADE 체인. (8) `OneToOne` CASCADE (`StockOverviewKo`) — 부모 삭제 시 silent. (9) `stocks.Stock` 직접 FK 6파일 + `symbol` CharField 25+곳 혼재 → 외래키 무결성 누락 |
| ℹ️ INFO | 5 | Wallet→Stock PROTECT, 2-Phase Neo4j sync (sec_pipeline) skip_locked 사용, neo4j_dirty 단일 소스 통일 완료(audit P0 #9), unique_together 광범위 사용, max_retries=2 default_retry_delay=60 등 우수 패턴 |

> 사전 파악 정정: 사용자 명세는 `SET_NULL 7곳/3파일, CASCADE 37곳/7파일`이나 **실제 측정값은 SET_NULL 17곳/9파일, CASCADE 90곳/22파일**(테스트/마이그레이션 제외). 이하 본문은 실측치 기준으로 작성.

---

## 1. FK orphan 위험

### 1-1. SET_NULL 사용처 전체 목록 (17건 / 9파일)

| # | 파일:라인 | 모델·필드 | 정리 잡 | 비고 |
|---|---|---|---|---|
| 1 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | ❌ 없음. 단 `signals.py:on_unmatched_resolved` + `rematch_unmatched` 명령어로 **재매칭** 경로 존재 | 정상 워크플로 — target_company NULL은 "미매칭 큐" 상태. PROD 47% (`quality_checks.py:68`) 게이트로 모니터 |
| 2 | `serverless/models.py:660` | `ScreenerAlert.preset` | ❌ 없음 | `filters_json` fallback 있음 → 동작은 함. 하지만 사용자 "프리셋 기반" 표시가 깨짐 |
| 3 | `serverless/models.py:808` | `InvestmentThesis.user` | ❌ 없음 | `__str__`에서 "Anonymous" 처리 → 화면은 동작. **공유 thesis는 user=NULL이어도 OK 설계** |
| 4 | `serverless/models.py:1409` | `AdminActionLog.user` | ❌ (의도적) | 감사 로그는 사용자 삭제 후에도 보존되어야 함 — 정상 |
| 5 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | ❌ 없음 | basket 삭제 후 session은 남음 → exploration_path는 유지되나 basket 컨텍스트 손실 |
| 6 | `rag_analysis/models.py:256` | `UsageLog.session` | ❌ 없음 | 비용 추적 — 세션 삭제 후 로그 보존 정상 |
| 7 | `rag_analysis/models.py:263` | `UsageLog.message` | ❌ 없음 | 동일 |
| 8 | `marketpulse/models/anomaly.py:25` | `Anomaly.sector_*` (추정) | 확인 안 됨 | 별도 점검 권고 |
| 9 | `thesis/models/thesis.py:70,77` | `Thesis.template`, `parent` | ❌ 없음 | template 삭제 후 사용자 thesis는 보존 — 정상 |
| 10 | `thesis/models/indicator.py:15` | `IndicatorBinding` 관련 | ❌ 없음 | |
| 11 | `thesis/models/monitoring.py:66` | `Snapshot` 관련 | ❌ 없음 | |
| 12 | `macro/models/indicators.py:310` | `IndicatorSeries.parent` (추정) | 확인 안 됨 | |
| 13–15 | `portfolio/models.py:327, 732, 831` | 시나리오/리포트 관련 | ❌ 없음 | UUID PK 사용, 사이드이펙트 적음 |
| 16 | `chainsight/models/news_event.py:54` | `NewsEvent` self-FK (parent) | ❌ 없음 | 자기참조 트리, 정상 |

### 1-2. 핵심 위험: SET_NULL 후 orphan 정리 로직 **전무**

- `grep -rn 'cleanup_orphan\|delete_orphan\|orphan_cleanup'` → **0건**.
- `target_company__isnull=True`로 필터링하는 코드는 다수(`sec_pipeline/intelligence.py`, `quality_checks.py`, `signals.py`)이나 모두 **카운트/리포트용**이지 삭제 잡 아님.
- 영향: 시간이 지나면 `null` 외래키 누적 — 검색 인덱스 효율 저하, dashboard count 왜곡.
- 권고: 사분기 1회 `delete_old_null_fk` 잡 (e.g. `extracted_at < now()-180d AND target_company IS NULL`).

---

## 2. CASCADE 체인 분석

### 2-1. CASCADE 사용처 분포 (90건 / 22 파일)

| 앱 | 건수 | 부모 모델 (대표) |
|----|---|---|
| portfolio | 13 | Wallet, Portfolio, ScenarioRun, AnalysisRun |
| thesis | 12 | Thesis, Indicator (community/monitoring/learning) |
| serverless | 7 | Screener, ETFHolding, ScreenerAlert |
| sec_pipeline | 6 | RawDocumentStore, BusinessModelSnapshot |
| stocks | 6 | Stock 자체 (OneToOne 1건 포함) |
| graph_analysis | 8 | Watchlist 그래프 노드 |
| chainsight | 7 | CompanyChainProfile, RelationConfidence 자식 |
| macro | 4 | IndicatorSeries → IndicatorObservation |
| metrics | 5 | MetricDefinition → Benchmark |
| validation | 6 | PeerPreset, CategoryScore (Stock CASCADE) |
| users | 4 | User → Portfolio/Watchlist/UserInterest |
| rag_analysis | 5 | DataBasket → AnalysisSession → AnalysisMessage |
| news | 2 | NewsArticle |
| marketpulse | 2 | News |

### 2-2. Stock 삭제 시 영향 범위 (최대 폭발 반경)

`Stock`은 `symbol` (CharField, primary_key=True)을 가지며, **직접 FK 참조 15곳** + **`symbol` CharField로 우회 참조 25+곳**.

직접 CASCADE 자식 (Stock 삭제 → 즉시 삭제):

| 자식 모델 | 위치 | 1종목당 예상 row | 비고 |
|---|---|---|---|
| `DailyPrice` | stocks/models.py:133 | ~3,000+ (10년치) | to_field='symbol' |
| `WeeklyPrice` | stocks/models.py | ~520 | to_field='symbol' |
| `BalanceSheet` | stocks/models.py:244 | ~50 (10년×5종) | abstract 상속 |
| `IncomeStatement` | stocks/models.py | ~50 | |
| `CashFlow` | stocks/models.py | ~50 | |
| `StockOverviewKo` | stocks/models.py:699 | 1 | **OneToOne** — silent drop |
| `EODSignal` | stocks/models.py:756 | ~250 (일별) | |
| `SignalAccuracy` | stocks/models.py:801 | ~250 | |
| `StockNews` | stocks/models.py:888 | 변동 | null=True 허용 |
| `WatchlistItem` | users/models.py:198 | 변동 | to_field='symbol' |
| `Portfolio` | users/models.py:28 | 변동 | |
| `SupplyChainEvidence.source_company` | sec_pipeline/models.py:82 | ~수십 | target_company는 SET_NULL |
| `RawDocumentStore` | sec_pipeline/models.py:25 | ~10 | 그리고 자식 `BusinessModelSnapshot` 까지 연쇄 |
| `BusinessModelSnapshot` | sec_pipeline/models.py:161 | ~10 | + 자식 `BusinessModelEvidence` |
| chainsight 7종 (`insider_signal`, `sensitivity`, `growth_stage`, `revenue_structure`, `event_reaction`, `capital_dna`, `narrative_tag`, `chain_profile`) | chainsight/models/*.py | 각 1 | |
| validation 6종 (`PeerMetricBenchmark`, `CategorySignal`, `MetricLatest`, `ValidationNewsSummary`, `PeerPreset`, `UserPeerPreference`) | validation/models/* | 각 1~수십 | |

**다행한 가드**: `portfolio.WalletHolding.stock` → `PROTECT` (`portfolio/models.py:90`). 사용자가 보유 중인 종목은 Stock 단건 삭제로 절대 사라지지 않음. ✅

**위험**: 그 외 모든 자식이 **CASCADE** — 운영자가 admin에서 Stock 1개를 삭제하면 1만+ row가 무경고 삭제. `PROTECT`로 막거나 soft-delete(`is_active`) 패턴 검토 필요.

### 2-3. 3단계 이상 연쇄 삭제 (다단 체인)

| 체인 깊이 | 경로 | 위험 |
|---|---|---|
| 4단계 | `User → Wallet → Portfolio → AnalysisRun → ScenarioResult` | 사용자 탈퇴 시 시뮬레이션 전체 증발 |
| 3단계 | `Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence` | Stock 삭제 → 10-K 원문 + 분류 + 근거 동시 삭제 |
| 3단계 | `User → DataBasket → AnalysisSession → AnalysisMessage` | RAG 대화 이력 완전 삭제 |
| 3단계 | `User → Watchlist → WatchlistItem` (CASCADE→CASCADE) | 정상 |
| 3단계 | `MetricDefinition → PeerMetricBenchmark → ...` | metrics 정의 삭제 시 |

depth 4의 portfolio 체인이 가장 깊고 운영 시점에 가장 자주 트리거됨. 사용자 탈퇴 시 회계용 audit log가 필요한지 확인 필요.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3-1. neo4j_dirty 플래그 사용 현황

audit P0 #9 (2026-04-29)에서 `synced_to_neo4j` 필드 제거 → `neo4j_dirty` 단일 소스 통일 완료. ✅

| 모델 | dirty 필드 | save() 자동 토글 | 비고 |
|------|---|---|---|
| `sec_pipeline.SupplyChainEvidence` | `neo4j_dirty + neo4j_synced_at` | ❌ 명시적 모델 메서드 없음. `update_or_create()` 시 자동 (Django save 호출). `queryset.update()`는 수동 토글 필요 | DB Index O |
| `chainsight.RelationConfidence` | `neo4j_dirty + neo4j_synced_at + score_version` | ✅ `save()` 오버라이드: 무조건 `dirty=True` | DB Index O. **주의: `bulk_update()`는 save 미호출** |
| `chainsight.CompanyChainProfile` | `neo4j_dirty + neo4j_synced_at` | ❌ 수동 | `db_index=True` |

### 3-2. 동기화 실패 시 재시도 메커니즘

**우수 패턴**:
- `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` — `max_retries=2, default_retry_delay=60` (Celery 자동 재시도).
- `sec_pipeline/tasks.py:362` — **2-Phase + `select_for_update(skip_locked=True)`**. Phase A에서 PG row lock + dict 복사 → Phase B에서 Neo4j 동기화 → Phase C에서 PG `dirty=False`. 워커 동시 실행 시에도 안전.
- `chainsight/services/neo4j_sync.py:48` — 성공한 pk만 모아 `queryset.update()`로 일괄 마킹. 실패 건은 dirty=True 유지 → 다음 주기 자동 재시도.

**미흡 패턴**:
- `chainsight/services/neo4j_sync.py:42` — 개별 row 실패 시 `logger.error` 후 다음 row로. **죽은 row 자동 격리/알람 없음**. 같은 row가 매번 실패하면 무한 재시도 + 로그 노이즈.
- `chainsight/tasks/sync_tasks.py:148` (`sync_relations_to_neo4j`) — 레거시 RELATED_TO 1회 정리 cache(`timeout=86400 * 365`) — 1년 유효. cache flush 시 다시 실행됨 (idempotent라 OK).

### 3-3. PG ↔ Neo4j 불일치 감지

**현재 감지 가능한 것**:
- `sec_pipeline/quality_checks.py:90` — `dirty_count > 50` 알람.
- `sec_pipeline/intelligence.py:97-98` — `sync_synced`, `sync_pending` 카운트.
- `chainsight` 측은 `quality_check` 알람 부재.

**감지 불가능한 것** (🔴 P0):
1. **PG에 있고 Neo4j에 없는 경우**: `dirty=False`로 마킹됐는데 실제 Neo4j 엣지가 없는 상황. 예: sync 중 Neo4j 일시 장애로 부분 성공 + Phase C가 완료된 케이스, 또는 Neo4j 수동 정리 후 PG 미반영.
2. **Neo4j에 있고 PG에 없는 경우**: PG row가 삭제됐는데 `_delete_edge` 호출 전 dirty=False였던 경우. PG `RelationConfidence` 삭제 시 Neo4j edge 잔존 (현재 코드에 PG post_delete signal 없음).
3. **속성 drift**: `truth_score` 등이 PG에서 변경됐는데 Neo4j에 미반영 — `save()` 오버라이드가 잡지만 `bulk_update` 우회 시 누락.

**권고**: 주간 reconciliation 잡 — PG `confirmed/probable` 전체 vs Neo4j `MATCH (a)-[r]->(b) WHERE r.source IS NOT NULL` 카운트 비교. 차이 >5%면 알람.

### 3-4. `RelationConfidence.save()`의 무조건 `dirty=True` 모순

`chainsight/models/relation_discovery.py:158`:
```python
def save(self, *args, **kwargs):
    ...
    self.neo4j_dirty = True   # 무조건
    super().save(*args, **kwargs)
```

- `neo4j_sync.py:48`이 `dirty=False`로 마킹 직후, 같은 row의 `score_version` 등 메타 필드를 admin에서 수정하면 다시 dirty=True가 됨 (정상).
- 그러나 sync 작업 자체가 `synced_at`을 업데이트할 때 `save()`를 호출하면 무한 루프. 현재 코드는 `queryset.update()`로 우회 (line 48-51). **이 패턴 유지가 강제 규칙임을 주석에 명시했으나 새 코드 작성자가 모르고 `instance.save()`를 호출하면 무한 dirty 루프 발생 가능**. 

권고: `save()`에 `update_fields` 검사 추가 — `update_fields == {'neo4j_dirty', 'neo4j_synced_at'}`이면 dirty 토글 스킵.

---

## 4. UniqueConstraint / update_or_create 현황

### 4-1. unique_together / UniqueConstraint 분포

총 **57건** (운영 모델 기준, 마이그레이션 중복 제외):

| 패턴 | 건수 | 대표 예 |
|---|---|---|
| `(stock, date)` | 8 | DailyPrice, WeeklyPrice, EODSignal, IndicatorObservation |
| `(stock, period_type, fiscal_year, fiscal_quarter)` | 3 | BalanceSheet, IncomeStatement, CashFlow |
| `(symbol_a, symbol_b, ...)` | 3 | CoMentionEdge, PriceCoMovement, RelationConfidence |
| `(user, X)` | 8 | Watchlist(name), WatchlistItem(stock), Portfolio(stock), UserInterest |
| `(symbol, date, type)` 류 | 10 | serverless 시그널 다수 |
| `(symbol, fiscal_year, metric, preset)` 등 | 6 | validation 4-keys |
| `UniqueConstraint(fields=...)` (명시적) | 5 | portfolio/migrations |

전반적으로 **건전**. unique 제약이 누락된 채 update_or_create를 호출하는 패턴은 발견되지 않음.

### 4-2. update_or_create race condition 가능성

운영 코드 기준 **103건** 사용. Django `update_or_create`는 내부적으로 `SELECT → INSERT/UPDATE` 2단계이며, **명시적 `select_for_update` 없이는 동시 호출 시 IntegrityError 가능**.

샘플링 결과:

| 위치 | unique 제약 | 락 보호 | 평가 |
|---|---|---|---|
| `sec_pipeline/tasks.py:314` (relation seed) | `unique_together=['symbol_a','symbol_b','relation_type']` ✓ | ❌ | DB unique가 catch — Celery 주기 실행이라 충돌 거의 없음. **안전** |
| `sec_pipeline/tasks.py:362` (sync_dirty) | n/a (UPDATE 전용) | ✅ `select_for_update(skip_locked=True)` | **모범 사례** |
| `chainsight/tasks/relation_tasks.py:275, 309, 343` | unique_together ✓ | ❌ | 단일 워커 가정. 다중 워커 + 같은 pair 동시 처리 시 IntegrityError 가능 |
| `chainsight/tasks/sync_tasks.py:84` (`aggregate_chain_profiles`) | `symbol_id` PK | ❌ | 단일 Beat 잡 → 안전 |
| `users/views.py` 다수 | various | ❌ | API 동시 호출 시 race 이론적 가능. 그러나 unique catch 됨 |

**위험 패턴 없음**. 다만 `chainsight/tasks/relation_tasks.py`의 RelationConfidence 생성 루프는 미래에 분산 워커로 갈 경우 `transaction.atomic` + `select_for_update`로 감싸야 함.

### 4-3. `update_or_create`의 dirty 플래그 사이드이펙트

`sec_pipeline/tasks.py:314` — `RelationConfidence.update_or_create()` 호출 시 Django는 내부적으로 `instance.save()` 호출 → `save()` 오버라이드가 `neo4j_dirty=True` 자동 설정. **의도된 동작이며 주석에도 명시됨** (`# audit P0 #9: ... update_or_create의 save()가 neo4j_dirty=True 자동`).

하지만 `defaults`에 변경이 없어 사실상 noop인 경우에도 dirty=True가 됨 → Neo4j 불필요한 재동기화. 큰 손실 아니나 sync 큐 부풀림.

---

## 부록 A. PROTECT 사용처 (양호)

| 위치 | 모델 | 평가 |
|---|---|---|
| `portfolio/models.py:90` | `WalletHolding.stock` → Stock | 🟢 사용자 보유 종목 보호 — 정확한 사용 |
| `portfolio/models.py:393, 495, 566` | 시나리오 stock 참조 | 🟢 |
| `marketpulse/models/snapshot.py:51` | snapshot → indicator | 🟢 |
| `metrics/models/metric_snapshot.py:11` | snapshot → definition | 🟢 |
| `chainsight/models/news_event.py:23` | news_event → stock | 🟢 |

`stocks.Stock` 본체에 대한 PROTECT가 5곳이나 있어 운영자가 admin에서 stock 1개를 삭제 시도 시 *일부 자식이* `IntegrityError`로 막아줌 (PROTECT가 가장 먼저 트리거). 그러나 PROTECT 가드가 없는 자식이 압도적 다수 — 가드는 부분적임.

## 부록 B. 측정 메타데이터

```
SET_NULL  : 17건 / 9파일  (사용자 명세 7건 ≠ 실측 17건)
CASCADE   : 90건 / 22파일 (사용자 명세 37건 ≠ 실측 90건)
PROTECT   : 7건  / 5파일
unique    : 57건 운영 + 30+ 마이그레이션
update_or_create: 103건 운영
select_for_update / transaction.atomic 사용 파일: 28개
neo4j_dirty 운영 코드: 53개 레퍼런스
```

명세-실측 격차는 (1) `**/models/` 하위 분할 파일을 사용자 grep이 놓침 (2) `monitoring.py`, `indicators.py` 등 subdirectory 누락 — 사용자 측 sample이 정확하지 않으니 본 보고서 수치 사용 권고.
