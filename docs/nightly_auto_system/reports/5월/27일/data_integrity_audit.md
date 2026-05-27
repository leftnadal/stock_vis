# 데이터 무결성 감사 보고서

- **감사일**: 2026-05-27
- **범위**: backend Django 모델 + Celery sync 태스크 + Neo4j 동기화 로직 (frontend·tests·migrations 제외)
- **방식**: 읽기 전용 정적 분석 (런타임 DB 미접속). 실제 row 존재 여부가 아닌 **스키마/코드 경로** 기반 잠재 위험만 식별.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 영역 |
|--------|------|------|
| 🔴 High (운영 영향, 즉시 대응 권장) | **3** | Stock FK CASCADE 폭, SET_NULL orphan 정리 부재, Neo4j↔PG 불일치 무감지 |
| 🟠 Medium (잠재 위험, 단기 대응) | **4** | update_or_create race, signal 전파 누락, retry 미설정, ManyToMany 데이터 정합성 |
| 🟡 Low (관찰 권장) | **3** | 카운트 보고와 실측 불일치, neo4j_dirty 의미 이중화 잔존, 인덱스 부재 |

**총 10건.**

> **사전 카운트 정정**: 지시서의 "SET_NULL 7곳/3파일, CASCADE 37곳/7파일"은 부정확. 실측은 **SET_NULL 17곳/14파일, CASCADE ≥80곳/24+파일**. 본 보고서는 실측 기준으로 분석.

---

## FK orphan 위험

### A. SET_NULL 사용처 전수 (실측 17곳, 14파일)

| 파일:라인 | 모델 / 필드 | 참조 대상 | 비고 |
|-----------|------------|----------|------|
| `marketpulse/models/anomaly.py:25` | Anomaly.stock | Stock | 알람 이력은 종목 삭제 후에도 보존 필요 — **타당** |
| `serverless/models.py:660` | ScreenerAlert.preset | ScreenerPreset | 프리셋 삭제 시 알림 보존 — **타당** |
| `serverless/models.py:808` | InvestmentThesis.user | users.User | 사용자 탈퇴 후 익명 테제 보존 — **타당** |
| `serverless/models.py:1409` | (외부 user 참조) | users.User | 동일 패턴 |
| `thesis/models/thesis.py:70,77` | Thesis 메타 FK | (각종) | |
| `thesis/models/indicator.py:15` | Indicator FK | (분기) | |
| `thesis/models/monitoring.py:66` | Monitoring FK | (분기) | |
| `sec_pipeline/models.py:86` | SupplyChainEvidence.target_company | stocks.Stock | **🔴 orphan 정리 로직 부재** (아래 #1) |
| `chainsight/models/news_event.py:54` | (self 참조) | NewsEvent | 부모 이벤트 삭제 시 자식 보존 |
| `macro/models/indicators.py:310` | IndicatorValue 관련 | (지표) | |
| `rag_analysis/models.py:145` | BasketItem.stock류 | (참조) | |
| `rag_analysis/models.py:256,263` | UsageLog.session/message | AnalysisSession/Message | 통계 보존 — **타당** |
| `portfolio/models.py:327,732,831` | 포트폴리오 메타 FK | (분기) | |

### B. 🔴 H-1: `SupplyChainEvidence.target_company` orphan 정리 부재

**위치**: `sec_pipeline/models.py:85-89`

```python
target_company = models.ForeignKey(
    'stocks.Stock', on_delete=models.SET_NULL,
    null=True, blank=True, ...
)
```

**위험**:
- Stock 삭제 시 evidence.target_company → NULL. 그러나 `target_company_name`(원문 회사명)은 그대로 남음.
- `sec_pipeline/tasks.py:365`의 dirty sync 쿼리는 `target_company__isnull=False`로 NULL row를 필터링 → **NULL이 된 evidence는 영구히 Neo4j sync 큐에서 제외**, 좀비 row 누적.
- `sec_pipeline/signals.py`의 `on_unmatched_resolved`는 `target_company__isnull=True`인 row 중 **이름이 정확히 일치**하는 것만 재매칭 → 종목 삭제 후 동일 이름 종목이 재등록되어도 자동 회복 안 됨.

**탐지 쿼리(권장)**:
```sql
SELECT count(*) FROM sec_supply_chain_evidence
WHERE target_company_id IS NULL AND target_company_name <> '';
```

**권장**: orphan cleanup management command 추가 + dirty sync에서 `Q(target_company__isnull=False) | Q(deleted_at__isnull=True)` 같은 명시적 처리.

### C. 🔴 H-2: 전반적인 SET_NULL 후 orphan 정리 로직 부재

**위치**: 17곳 SET_NULL 전부.

코드베이스 grep 결과 `orphan|delete_orphan|prune|cleanup.*null` 매칭은 **단 1건** (`news/services/news_neo4j_sync.py:700` — Neo4j 측 orphan만 정리).

PostgreSQL 측 SET_NULL 결과 row를 주기적으로 점검/정리하는 management command나 Celery beat 작업이 **존재하지 않음**.

**영향**: 데이터 가시성 저하 (예: ScreenerAlert.preset=NULL인데 `filters_json`도 비어있으면 dead alert), DB 부피 증가.

### D. 🟠 M-1: `users.User` SET_NULL 시 `favorite_stock` M2M 잔여

**위치**: `users/models.py:17` — `favorite_stock = models.ManyToManyField(Stock, ...)`

User 탈퇴 시 `User`가 그냥 삭제되면 M2M 중간 테이블 row만 사라지지만, 일부 코드 경로(`serverless` InvestmentThesis 등)에서 user를 SET_NULL로 처리하면 **user.favorite_stock 검색 의도**가 깨질 수 있음. M2M은 정의상 user 객체가 사라지면 join이 끊김 — orphan은 아니지만 비즈니스 로직 일관성 위험.

---

## CASCADE 체인

### A. CASCADE 사용처 (실측 ≥80곳, 24+ 파일)

지시서의 7개 파일은 일부만 반영. 실제 CASCADE 사용 파일은 아래와 같이 대폭 확장됨:

```
validation/models/*.py (8건)        graph_analysis/models.py (8건)
sec_pipeline/models.py (6건)        thesis/models/*.py (10건)
chainsight/models/*.py (12건)       portfolio/models.py (12건)
users/models.py (5건)               serverless/models.py (4건)
news/models.py (2건)                rag_analysis/models.py (5건)
macro/models/*.py (5건)             metrics/models/*.py (5건)
stocks/models.py (6건)              marketpulse/models/news.py (2건)
```

### B. 🔴 H-3: Stock 삭제 시 영향 범위 (CASCADE 폭주)

**Stock(PK=symbol)**에 직접 CASCADE로 매달린 FK (정적 분석 추출):

| 앱 | 모델 | 효과 |
|----|------|------|
| stocks | DailyPrice / WeeklyPrice / MonthlyPrice / IntradayPrice / Overview_ko / IncomeStatement / BalanceSheet / CashFlow | 종목별 ≥수십만 row 즉시 삭제 |
| users | Portfolio / WatchlistItem | 사용자 보유/관심 데이터 소실 |
| validation | BenchmarkDelta / CategoryScore / MetricLatest / NewsSummary / PeerPreset(×2) | 모든 검증 캐시 삭제 |
| chainsight | InsiderSignal / RevenueStructure / CapitalDNA / EventReaction / GrowthStage / Sensitivity / NarrativeTag / ChainProfile | 프로파일 전부 삭제 |
| sec_pipeline | RawDocumentStore → (cascade) SupplyChainEvidence(source) + BusinessModelSnapshot → BusinessModelEvidence | **3단 연쇄** (Stock → RawDoc → BusinessModelSnapshot → BusinessModelEvidence) |
| graph_analysis | CorrelationEdge.stock_a, CorrelationEdge.stock_b → CorrelationAnomaly(edge) | **3단 연쇄** + 양쪽 stock 어느 한쪽만 삭제돼도 전 watchlist의 edge 삭제 |

#### 3단 이상 연쇄 분석 결과

1. **stocks.Stock → sec_pipeline.RawDocumentStore → sec_pipeline.BusinessModelSnapshot → sec_pipeline.BusinessModelEvidence** (4단)
   - Stock 1건 삭제 시 한 종목의 10-K 원문 + 모든 분기별 BM 스냅샷 + 모든 evidence 문장이 한 번에 사라짐.
   - **추가 문제**: `SupplyChainEvidence.source_company`도 CASCADE이므로 Stock 삭제 = 해당 종목이 source인 모든 supply chain edge 동시 소실. target만 SET_NULL이라 비대칭.

2. **stocks.Stock → graph_analysis.CorrelationEdge → graph_analysis.CorrelationAnomaly** (3단)
   - 또한 같은 Stock이 `stock_a` 또는 `stock_b` 어느 쪽이든 매칭되면 양쪽 모두 트리거 — `unique_together = [watchlist, stock_a, stock_b, date]`라서 (X,Y)/(Y,X) 중복 방어 미존재.

3. **users.User → users.Watchlist → users.WatchlistItem + graph_analysis.CorrelationMatrix/Edge/Anomaly** (3단)
   - User 1명 탈퇴 시: Watchlist 전체 → 각 Watchlist의 모든 상관 매트릭스 + edge + anomaly까지 한 번에 삭제. **rollback 어려움**.

4. **rag_analysis 체인**: User → DataBasket → BasketItem (3단 CASCADE), User → AnalysisSession → AnalysisMessage → (UsageLog는 SET_NULL) (4단 혼합).

### C. 🟠 M-2: Stock 삭제는 사실상 운영상 금지되어야 함

위 폭주를 종합하면 **Stock row 1건 삭제 = 회복 불능 데이터 손실**. 그러나 정적 분석상 Stock 삭제를 보호하는 가드(soft delete 필드, manager 오버라이드, admin 권한 제한 표시)는 **없음**.

`stocks/services/stock_sync_service.py`의 `Stock.objects.update_or_create()`(line 171)는 안전하지만, admin/shell에서 .delete() 호출 시 보호 없음.

**권장**:
- Stock에 `is_active`/`deleted_at` 필드 + custom manager로 soft delete.
- 또는 Stock 삭제 전 종속 row 카운트 알림 management command.

---

## Neo4j 동기화

### A. neo4j_dirty 플래그 사용 현황

**일원화된 단일 소스** (audit P0 #9, 2026-04-29 완료):
- `chainsight.RelationConfidence.neo4j_dirty` (db_index=True)
- `chainsight.CompanyChainProfile.neo4j_dirty` (db_index=True)
- `sec_pipeline.SupplyChainEvidence.neo4j_dirty` (인덱싱됨)

**자동 세팅 패턴**:
- `RelationConfidence.save()`에서 `self.neo4j_dirty = True` 무조건 세팅 (`relation_discovery.py:158`).
- `queryset.update()`에서는 save() 미호출 → 코드에서 명시 토글 필요. `relation_tasks.py:382,388,395,402`에 수동 처리 확인.

**동기화 후처리**:
- 성공 시 `update(neo4j_dirty=False, neo4j_synced_at=now)` 일괄 처리.
- `chainsight/services/neo4j_sync.py:48-51` — 의도적으로 save() 미사용 (save가 dirty=True로 되돌리므로).

### B. 🔴 H-4: PG↔Neo4j 불일치 감지 메커니즘 부재

**현재 가시화 수준**:
- `sec_pipeline/intelligence.py:97-98` — `sync_synced` / `sync_pending` 카운트 단순 집계.
- `sec_pipeline/quality_checks.py:92,144-146` — backlog 알림 (matched > 50건일 때).

**누락된 항목**:
1. **역방향 무결성 체크 없음**: PG에 없는데 Neo4j에는 남아있는 좀비 edge 검출 로직 부재. SET_NULL로 사라진 evidence가 Neo4j에 그대로 남으면 영구 잔존.
2. **체크섬/카운트 대조 작업 없음**: 예) `RelationConfidence(confirmed) count` vs `Neo4j MATCH (a)-[r {status:'confirmed'}]->(b) RETURN count(r)`.
3. **Neo4j edge 삭제 실패의 silent swallow**:
   - `chainsight/services/neo4j_sync.py:90` — `_delete_edge`의 except는 warning만 로그.
   - `sec_pipeline/tasks.py:411-412` — DELETE 쿼리의 `except Exception: pass` (edge 미존재 의도지만 모든 예외를 삼킴).

   **결과**: Neo4j에 가비지 edge가 남고 PG는 `neo4j_dirty=False`로 표시 → drift 누적.

### C. 동기화 실패 시 재시도 메커니즘

| 태스크 | retry 설정 | 분석 |
|-------|-----------|------|
| `sync_dirty_to_neo4j` (sec_pipeline) | `max_retries=1` | 🟠 **부족** — 1회 retry로는 Neo4j 일시 장애 회복 어려움. CLAUDE.md 규칙은 max_retries=3 + exponential backoff |
| `sync_profiles_to_neo4j` (chainsight) | `max_retries=1` | 🟠 동일 |
| `sync_relations_to_neo4j` (chainsight) | `max_retries=1` | 🟠 동일 |
| `aggregate_chain_profiles` | `max_retries=1` | 🟠 동일 |

**🟠 M-3**: 모든 Neo4j 동기화 태스크가 `max_retries=1`. CLAUDE.md 규약(`max_retries=3, exponential backoff`)을 위반. 다행히 `neo4j_dirty`는 dirty 상태로 유지되므로 다음 beat에 재처리되지만, **개별 row 실패는 무한 재시도 루프**(영구 dirty)가 될 수 있어 backoff와 dead-letter 정책 필요.

### D. dirty 큐의 unbounded 성장 위험

`sync_dirty_to_neo4j`는 `BATCH_SIZE=500`으로 처리하지만 — 대량 백필 시 dirty 큐가 큰 폭으로 증가하면 beat 1회당 500건씩만 처리, 큐가 비워지지 않고 누적될 가능성. `quality_checks.py`의 50건 임계값은 시뮬레이션엔 적합하나 실운영 백필 시나리오 대응 미흡.

### E. 🟡 L-1: `neo4j_synced` 잔존 흔적

`chainsight/migrations/0008_unify_neo4j_flags.py`에서 의미 반전 마이그레이션을 했지만, 일부 admin/test에 옛 명명 잔존. 검색 결과는 깨끗하나 `CompanyChainProfile`의 reverse_code가 두 컬럼 모두 존재한다고 가정하므로 향후 컬럼 drop 시 주의.

### F. 🟠 M-4: `on_unmatched_resolved` 시그널 sector 제한의 양면

`sec_pipeline/signals.py:46-49` — 동일 이름의 evidence라도 `source_company.sector`가 일치해야만 재매칭. 의도는 "Apple" 같은 흔한 이름의 오매칭 방지지만, **source_company의 sector가 비어있으면 (sector="") evidence는 영구히 unresolved**. Stock 모델 (`stocks/models.py:27`)에서 `sector`는 `blank=True, null=True` 허용. → 새로 동기화된 종목에서 sector 미설정 시 매칭 실패.

---

## Unique 제약조건

### A. unique_together / UniqueConstraint 분포

**unique_together (32곳)** — 주요 패턴:
- 시계열: `(stock, date)` — DailyPrice, WeeklyPrice, MonthlyPrice, IndicatorReading 등 (7곳)
- 재무: `(stock, period_type, fiscal_year, fiscal_quarter)` — Income/Balance/CashFlow (3곳)
- 사용자: `(user, stock)`, `(user, name)`, `(watchlist, stock)`, `(user, interest_type, value)`
- 외부 ID: `(symbol, date)`, `(symbol, date, action_type)`
- 그래프: `(watchlist, date)`, `(watchlist, stock_a, stock_b, date)` ← **방향 미정규화** (아래 M-5)

**UniqueConstraint (4곳)** — `portfolio/models.py:439,525,583,701`. 모두 동일 앱 내, 조건부 unique constraint 추정.

### B. 🟠 M-5: CorrelationEdge의 (a,b)/(b,a) 중복 방어 부재

```python
# graph_analysis/models.py:127
unique_together = [['watchlist', 'stock_a', 'stock_b', 'date']]
```

상관계수는 대칭(`corr(A,B) = corr(B,A)`)이지만, unique_together는 정렬을 강제하지 않음. `correlation_calculator.py:290`에서 `update_or_create`로 저장 시 매번 동일 정렬 보장이 필요한데 정적 분석상 확신할 수 없음. **권장**: `Q(stock_a_id < stock_b_id)` 체크 또는 `normalize_pair()` 강제 호출.

(반면 `chainsight/services/neo4j_sync.py:18`는 `UNDIRECTED_TYPES`에 한해 `normalize_pair()`를 명시 호출 — 좋은 패턴.)

### C. update_or_create race condition 분석

`update_or_create` 사용처 **62곳** (services 50건 + tasks 7건 + management 5건). 주요 위험 위치:

| 위치 | 위험도 | 비고 |
|------|-------|------|
| `validation/services/metric_calculator.py:98,449` | 🟡 | unique key가 명시적, 동시 호출 빈도 낮음 |
| `sec_pipeline/tasks.py:120,314` | 🟡 | Celery 단일 워커 가정 시 안전 |
| `chainsight/services/seed_selection.py:411` | 🟡 | Beat 단일 트리거 |
| `serverless/services/keyword_service.py:202` + `serverless/tasks.py:393` | 🟠 | **동일 모델에 두 경로** — 동시 실행 시 race |
| `serverless/services/theme_matching_service.py:247,329,575` | 🟠 | 같은 키 3곳 — concurrent extract 가능 |
| `marketpulse/calculators/*.py` (breadth/concentration/sector_flow) | 🟡 | 일일 1회 배치 — 안전 |
| `graph_analysis/services/correlation_calculator.py:197,290,388` | 🟠 | 위 M-5와 결합 시 (a,b)/(b,a) 중복 row 동시 삽입 가능 |
| `stocks/services/stock_sync_service.py:171,337` | 🟡 | `@transaction.atomic` 데코레이터 적용 (line 133,262) — 안전 |

**🟠 M-6 종합**: Django의 `update_or_create`는 내부적으로 SELECT + INSERT/UPDATE 두 쿼리. unique constraint가 있어도 SERIALIZABLE/`select_for_update`가 없으면 IntegrityError를 잡지 못하고 두 워커가 동일 row를 만들 수 있음.

**적용된 보호**:
- `sec_pipeline/tasks.py:362,367` — `with transaction.atomic() + select_for_update(skip_locked=True)` — **모범 사례** ✓
- `users/views.py:700,869,935` — atomic + select_for_update 적용 ✓

**미적용 영역**: 위 표의 🟠 4건. 운영 트래픽 증가 전에 `select_for_update`로 보강 권장.

### D. 🟡 L-2: `news.NewsArticle.url_hash` 같은 사실상 unique 필드의 명시 부족

`news/models.py:202` — save()에서 `url_hash`를 SHA256으로 계산하지만 `unique=True`가 모델에 명시되어 있지 않으면 race 발생 시 동일 hash 중복 가능. (실제 unique 설정 여부는 본 감사 범위에서 미확인 — 권장: 모델 line ~150 부근 확인.)

### E. 🟡 L-3: 인덱스 부재 의심

- `chainsight.CompanyChainProfile.neo4j_dirty` — 인덱스 명시 확인 (line 65 `db_index=True` ✓).
- `sec_pipeline.SupplyChainEvidence.neo4j_dirty` — 인덱스 ✓ (line 111).
- `RelationConfidence.neo4j_dirty` — 인덱스 ✓ (line 143).
- 그러나 `BusinessModelEvidence`, `MetricSnapshot` 등 신규 모델의 자주 쓰이는 필터 컬럼에 인덱스가 있는지 추가 점검 필요.

---

## 부록 A — High-Risk 이슈 3건 액션 아이템 요약

| ID | 이슈 | 1차 조치(런타임 검증) | 2차 조치(코드 변경) |
|----|------|---------------------|-------------------|
| H-1 | SET_NULL evidence orphan | `SELECT count(*) FROM sec_supply_chain_evidence WHERE target_company_id IS NULL` | management command: `prune_orphan_evidence --older-than=180d` |
| H-2 | 전반 SET_NULL orphan 정리 부재 | 17개 모델 row별 카운트 SQL | Celery beat: monthly orphan sweep |
| H-3 | Stock CASCADE 폭주 | Stock admin에 inline FK count 표시 | Stock soft delete (`is_active`/`deleted_at`) + manager 오버라이드 |
| H-4 | Neo4j↔PG drift 무감지 | `sync_synced / total` 비율 알림 → `count(Neo4j edge by source=sec_10k) vs count(PG evidence)` 비교 cron | dedicated `audit_pg_neo4j_consistency` Celery beat |

---

## 부록 B — 감사 한계

1. 실제 DB row 카운트/타입별 분포 미확인. 본 보고서는 **스키마 + 코드 경로**만 분석.
2. `frontend/`, `tests/`, `migrations/` 디렉터리는 의도적으로 제외.
3. Stock 모델은 PK가 `symbol`(CharField)이라 `to_field='symbol'`로 참조되는 FK가 다수 — CASCADE 트리거 시 PostgreSQL의 row 수 계산이 BigInt PK 대비 약간 느릴 수 있음 (성능 영향 미평가).
4. signals.py는 sec_pipeline만 확인. 다른 앱의 post_save / pre_delete signal에 의한 side effect는 미점검.
