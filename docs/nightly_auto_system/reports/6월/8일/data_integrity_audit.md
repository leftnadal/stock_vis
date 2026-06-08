# 데이터 무결성 감사 보고서

> **생성일**: 2026-06-08
> **범위**: PostgreSQL FK 정책, CASCADE 연쇄, Neo4j ↔ PG 동기화, Unique 제약
> **방식**: 읽기 전용 정적 분석 (코드 수정 없음)
> **대상**: `packages/shared/`, `apps/`, `services/`, `macro/`, `thesis/` 모델 전수

---

## 요약 (위험도별 이슈 수)

> ⚠️ **지시서 수치 정정**: 지시서는 "SET_NULL 7곳/3파일, CASCADE 37곳/7파일, `stocks/models.py` 평면 구조"를 가정했으나, 실제 코드베이스는 `packages/shared/`·`apps/`·`services/` 멀티패키지 구조이며 실측은 아래와 같다.
>
> | 정책 | 실측 (migration 제외) | 지시서 가정 |
> |------|----------------------|-------------|
> | `SET_NULL` | **17곳 / 9파일** | 7곳 / 3파일 |
> | `CASCADE` | **95곳 / 22파일** | 37곳 / 7파일 |
> | `PROTECT` | **7곳** | (미언급) |

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 2 | (H-1) SET_NULL → Neo4j stale edge 미정리 / (H-2) Stock 삭제 시 4단계 CASCADE + Neo4j 미전파 |
| 🟠 Medium | 4 | (M-1) PG↔Neo4j 전역 정합성 reconciliation 부재 / (M-2) sync 태스크 `max_retries=1` 빈약 / (M-3) `update_or_create` 비원자성 race / (M-4) `StockNews.stock` CASCADE+null 혼용 |
| 🟡 Low | 3 | (L-1) `duplicate_of` self-FK SET_NULL 정리 로직 없음 / (L-2) dormant `graph_analysis` CASCADE 8건 잔존 / (L-3) UniqueConstraint vs unique_together 혼용 |

**총평**: PostgreSQL 내부 무결성은 **양호**(unique_together 광범위, SET_NULL 대부분 의도적 audit 보존). 진짜 위험은 **PG ↔ Neo4j 경계**에 집중됨 — 삭제 이벤트가 Neo4j로 전파되지 않아 stale 노드/엣지가 누적될 구조적 공백 존재.

---

## FK orphan 위험

### SET_NULL 사용처 전수 (17곳)

| # | 파일:라인 | 필드 | orphan 정리 로직 | 평가 |
|---|-----------|------|-----------------|------|
| 1 | `services/sec_pipeline/models.py:94` | `SupplyChainEvidence.target_company` | ✅ 부분 (아래 상술) | 🔴 H-1 |
| 2 | `apps/chain_sight/models/news_event.py:69` | `ChainNewsEvent.duplicate_of` (self-FK) | ❌ 없음 | 🟡 L-1 |
| 3 | `services/rag_analysis/models.py:132` | `AnalysisSession.basket` | N/A (의도적) | ✅ |
| 4-5 | `services/rag_analysis/models.py:232,239` | `TokenUsageLog.session/message` | N/A (감사 로그 보존) | ✅ |
| 6 | `services/serverless/models.py:660` | `ScreenerAlert.preset` | N/A (커스텀 필터 폴백) | ✅ |
| 7 | `services/serverless/models.py:797` | `InvestmentThesis.user` | N/A (익명화 보존) | ✅ |
| 8 | `services/serverless/models.py:1353` | `AdminActionLog.user` | N/A (감사 추적 보존) | ✅ |
| 9 | `macro/models/indicators.py:310` | (지표 관계) | N/A | ✅ |
| 10-12 | `thesis/models/{monitoring,indicator,thesis}.py` | 가설 스냅샷 참조 | N/A | ✅ |
| 13 | `thesis/models/thesis.py:77` | (가설 보조 FK) | N/A | ✅ |
| 14-16 | `apps/portfolio/models.py:341,768,870` | 지갑/거래 보조 참조 | N/A | ✅ |
| 17 | `apps/market_pulse/models/anomaly.py:35` | 이상치 참조 | N/A | ✅ |

**판정**: 17건 중 **15건은 의도적 설계** — 부모 삭제 시 로그/감사/스냅샷 레코드를 보존하기 위한 정상적 `SET_NULL` 사용. orphan 정리 로직이 "없는 것"이 아니라 "필요 없는" 케이스.

### 🔴 H-1 — `SupplyChainEvidence.target_company` SET_NULL 후 Neo4j stale edge

이것만이 실질적 orphan 위험이다. 흐름:

```
Stock 삭제
 → SupplyChainEvidence.target_company = NULL  (SET_NULL)
 → target_company_name(문자열)은 그대로 남음
 → ❌ neo4j_dirty 플래그는 변하지 않음 (False 유지)
 → ❌ sync_dirty_to_neo4j 가 이 row를 집지 않음 (dirty=False)
 → Neo4j의 (a)-[:SUPPLIES_TO {source:'sec_10k'}]->(b) 엣지가 삭제된 b를 계속 가리킴 = STALE
```

**근거**:
- `tasks.py:428-431` — dirty sync는 `neo4j_dirty=True AND target_company__isnull=False`만 처리. SET_NULL로 NULL이 된 row는 `isnull=True`가 되어 **영구히 sync 대상에서 제외**된다.
- `tasks.py:470-486` — Neo4j 엣지 DELETE는 dirty row를 처리할 때만 실행. 삭제 자체로는 트리거되지 않음.
- SET_NULL은 Django ORM 레벨 동작 → `neo4j_dirty=True`를 자동 세팅하지 않음.

**부분 정리 로직(미스매치 큐)은 존재하지만 방향이 반대**:
- `signals.py:21-60` — `UnmatchedCompanyQueue`가 `matched`로 바뀌면 NULL이던 `target_company`를 **채우고** `neo4j_dirty=True` 세팅 (orphan → 매칭 복구). 정상 작동.
- `management/commands/rematch_unmatched.py` — `target_company__isnull=True` 재매칭 배치.
- 즉 "**미매칭→매칭**" 복구 경로는 있으나, "**기존 매칭 Stock 삭제→Neo4j 엣지 회수**" 경로는 **없음**.

**영향**: Stock delete가 드문 운영(보통 비활성화로 처리)이라 빈도는 낮으나, 발생 시 Neo4j에 잘못된 supply-chain 엣지가 영구 잔존. Chain Sight 그래프 탐색 결과 오염.

---

## CASCADE 체인

### Stock 허브 — 가장 많은 FK 참조 (삭제 폭발 반경)

`stocks.Stock`은 코드베이스 전역에서 참조되는 최상위 허브다. `to_field="symbol"` 또는 PK 참조로 **최소 9개 앱**이 직접 FK를 건다.

**Stock 삭제 시 직접 CASCADE 대상** (1단계):

| 모델 | 파일:라인 | 비고 |
|------|-----------|------|
| `DailyPrice` | `stocks/models.py:194` | 종목당 수천 행 |
| `WeeklyPrice` | `stocks/models.py:306` | |
| `StockOverviewKo` | `stocks/models.py:946` | OneToOne, PK=stock |
| `EODSignal` | `stocks/models.py:1015` | EOD 대시보드 핵심 |
| `SignalAccuracy` | `stocks/models.py:1063` | |
| `StockNews` | `stocks/models.py:1153` | ⚠️ CASCADE + `null=True` (M-4) |
| `Portfolio` | `users/models.py:47` | 사용자 보유 |
| `WatchlistItem` | `users/models.py:223` | |
| `RawDocumentStore` | `sec_pipeline/models.py:24` | → 2단계 연쇄 시작 |
| `SupplyChainEvidence.source_company` | `sec_pipeline/models.py:86` | CASCADE (target은 SET_NULL) |
| `BusinessModelSnapshot` | `sec_pipeline/models.py:173` | → 2단계 연쇄 |
| serverless/validation/metrics/chainsight FK 다수 | (각 앱) | CompanyMetricLatest, CategorySignal, ChainProfile 등 |

### 🔴 H-2 — 3단계 이상 연쇄 삭제

가장 깊은 체인 (4단계):

```
Stock
 └─CASCADE→ RawDocumentStore (sec_filings)            [1]
            └─CASCADE→ BusinessModelSnapshot           [2]
                       └─CASCADE→ BusinessModelEvidence [3]
```
+ 동시에:
```
Stock
 └─CASCADE→ RawDocumentStore                          [1]
            └─CASCADE→ SupplyChainEvidence             [2]  (source_document FK)
```
※ `SupplyChainEvidence`는 `source_document`(CASCADE)와 `source_company`(CASCADE) **이중 CASCADE 경로** — 둘 중 어느 쪽이 삭제돼도 제거됨.

**다른 깊은 체인**:
| 체인 | 단계 |
|------|------|
| `User → DataBasket → BasketItem` | 3 (`rag_analysis/models.py:14,73`) |
| `User → AnalysisSession → AnalysisMessage` | 3 (`rag_analysis/models.py:129,178`) — 단, `TokenUsageLog.message`는 SET_NULL이라 4단계로 안 내려감 (로그 보존) |
| `User → ScreenerAlert → ScreenerAlertHistory` | 3 (`serverless/models.py:648,747`) |
| `ETFProfile → ETFHolding` | 2 (`serverless/models.py:1050`) |
| Wallet → Transaction → … (`apps/portfolio`, CASCADE 13건) | 2~3 |

**위험 요소**:
1. **PG CASCADE는 정상이나 Neo4j 미전파** — H-1과 동일 구조. `RawDocumentStore`/`SupplyChainEvidence` CASCADE 삭제 시 대응하는 Neo4j 엣지가 제거되지 않음. Neo4j는 "SOLE WRITER via dirty sync" 모델(`tasks.py:410`)이라 PG의 물리 삭제를 인지하는 채널이 전무.
2. **대량 삭제 트랜잭션** — Stock 1건 삭제가 수천~수만 행(DailyPrice 중심) CASCADE를 단일 트랜잭션으로 유발. 운영 DB lock 시간 주의.

**완화 요인**: 운영상 Stock/User 물리 삭제는 거의 없음(비활성 플래그 위주). 그러나 정책으로 보장된 게 아니라 관행이므로 잠재 리스크로 분류.

### 🟡 L-2 — dormant graph_analysis CASCADE 8건

`services/_dormant/graph_analysis/models.py`에 CASCADE 8건이 잔존(`21,71,78,85,179,186,292,335`). `_dormant` 경로 = 미사용 코드지만 migration이 살아있다면 테이블 존재. 정리 대상 후보(스키마 부채).

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황 (3개 모델)

| 모델 | 파일:라인 | 인덱스 | sync 태스크 |
|------|-----------|--------|------------|
| `CompanyChainProfile` | `chain_sight/models/chain_profile.py:84` | ✅ `db_index=True` | `sync_profiles_to_neo4j` |
| `RelationConfidence` | `chain_sight/models/relation_discovery.py:148` | (확인 필요) | `sync_relations_to_neo4j` → `sync_dirty_relations` |
| `SupplyChainEvidence` | `sec_pipeline/models.py:112` | ✅ `Index(['neo4j_dirty'])` | `sync_dirty_to_neo4j` |

**설계 원칙 (양호)**: `synced_to_neo4j`(긍정형) 폐기 → `neo4j_dirty`(부정형, default=True) 단일 소스로 통일. `relation_tasks.py:317` 주석 "audit P0 #9: synced_to_neo4j 제거. update_or_create는 save() 호출하므로 neo4j_dirty=True 자동" — **저장 시 자동 dirty 마킹**이 일관되게 적용됨. ✅

### 동기화 성공/실패 메커니즘

**성공 경로** (`tasks.py:400-456`, `sync_tasks.py:108-170`):
- 2-Phase + `select_for_update(skip_locked=True)` — Phase A에서 PG row lock + dict 복사(최대 500건), Phase B에서 Neo4j 쓰기, Phase C에서 `neo4j_dirty=False` + `neo4j_synced_at`.
- `skip_locked=True` → 동시 워커 충돌 방지 (한 워커가 잡은 row는 다른 워커가 건너뜀). ✅ 동시성 안전.
- DELETE + CREATE 패턴 (MERGE 금지), dynamic relationship type. ✅

**재시도 메커니즘** — 🟠 **M-2 빈약**:
- 두 sync 태스크 모두 `max_retries=1` (`sync_tasks.py:15,107,173`). CLAUDE.md 권장치(`max_retries=3, exponential backoff`)와 **불일치**.
- **단, self-healing 구조로 보완됨**: 실패한 row는 `neo4j_dirty=True`로 남아 다음 Beat 주기에서 자동 재처리. 개별 row 실패가 `except` 블록에서 카운트만 되고 dirty 유지(`sync_tasks.py:165-167`, `tasks.py` 동일 패턴) → **결과적으로 무한 재시도(주기적)**. 따라서 `max_retries=1`은 치명적이지 않으나, 영구 실패 row(예: 깨진 데이터)가 매 주기 재시도되며 backlog를 키울 수 있음.

**실패 감지/알림** (`quality_checks.py`, `intelligence.py`):
- `quality_checks.py:93,145` — `neo4j_dirty=True AND target_company__isnull=False` (= `neo4j_pending`) 카운트. **50건 초과 시 backlog 알림** (test `test_neo4j_dirty_backlog_alert`로 검증됨).
- `intelligence.py:102` — sync_score 5차원 헬스 점수에 반영.
- ✅ pending backlog 감지는 작동. unmatched(`isnull=True`)는 의도적으로 제외 — 착시 방지(NT-8 퍼널 재구성과 동일 철학).

### 🟠 M-1 — PG↔Neo4j 전역 reconciliation 부재

**현재 감지 가능한 불일치**:
- ✅ "PG에 dirty 있는데 Neo4j 미반영" → backlog 카운트로 감지 (위).
- ✅ news 도메인 한정: `news_neo4j_sync.py:707` — orphaned NewsEvent 노드 정리 쿼리 존재.

**감지 불가능한 불일치 (공백)**:
- ❌ **"Neo4j에 있는데 PG에서 삭제됨"** (stale 노드/엣지) — H-1/H-2의 결과물. 이를 탐지/정리하는 전역 reconciliation job이 sec_pipeline/chain_sight에 **없음**.
- ❌ PG row count vs Neo4j node/edge count 대조 검증 부재.
- ❌ Neo4j 쓰기는 dirty row 단위 DELETE+CREATE만 수행 → PG에서 물리 삭제된 엔티티는 영원히 Neo4j에 남음.

**권고 (정보)**: 주기적 reconciliation 태스크 — (a) Neo4j `:Stock` ticker 집합 vs PG `Stock.symbol` 집합 차집합 → PG에 없는 Neo4j 노드 정리, (b) `source='sec_10k'` 엣지 중 PG `SupplyChainEvidence`에 대응 row 없는 것 정리. news 도메인의 orphan cleanup 패턴(`news_neo4j_sync.py:707`)을 sec/chainsight에 확장.

---

## Unique 제약조건

### unique_together 현황 (광범위, 양호)

모델 레이어 전반에 **약 50개** `unique_together` 정의 — 시계열/스냅샷/조인 테이블에 일관 적용. 대표:

| 도메인 | 제약 | 파일:라인 |
|--------|------|----------|
| 가격 | `(stock, date)` | `stocks/models.py:246,275` |
| 재무 | `(stock, period_type, fiscal_year, fiscal_quarter)` | `stocks/models.py:492,607,765` |
| EOD 시그널 | `(stock, signal_date, signal_tag)` | `stocks/models.py:1087` |
| 사용자 | `(user, stock)`, `(user, name)`, `(watchlist, stock)`, `(user, interest_type, value)` | `users/models.py:90,201,242,291` |
| RAG | `(basket, item_type, reference_id)` | `rag_analysis/models.py:101` |
| Chain Sight | `(source, source_id)`, `(symbol_a, symbol_b, relation_type)` | `chain_sight/...:79`, `relation_discovery.py:158` |
| SEC | `(alias, context_sector)` — country 제외 의도적 | `sec_pipeline/models.py:331` |
| serverless | `(institution_cik, stock_symbol, report_date)` 등 9건 | `serverless/models.py` |
| validation | `(symbol, fiscal_year, metric_code, preset_key)` 등 5건 | `validation/models/` |

**평가**: 동시 쓰기 충돌 방어선이 DB 레벨에 촘촘히 깔려 있음. update_or_create의 lookup 키와 unique_together가 대부분 정합. ✅

### 🟡 L-3 — UniqueConstraint vs unique_together 혼용

- `apps/portfolio/models.py:460,552,612,735` 4건만 `models.UniqueConstraint` 사용 (조건부/`condition` 가능), 나머지 전 코드베이스는 `unique_together`(레거시 스타일).
- 기능상 문제 없으나 스타일 불일치. Django는 `UniqueConstraint`를 권장(조건부·표현식 지원). 신규 코드 가이드라인 정립 권고(정보).

### 🟠 M-3 — update_or_create / get_or_create race condition

**사용 현황**: 약 **40곳** (`stock_service.py` 7건, `chain_sight/tasks` 8건, `market_pulse/tasks` 다수, `thesis/tasks/eod_pipeline.py` 3건 등).

**메커니즘 위험**:
- Django `update_or_create`/`get_or_create`는 **원자적이지 않음** — 내부적으로 `get()` → 없으면 `create()`. 두 워커가 동시에 같은 키로 진입하면 둘 다 `get()` 실패 → 둘 다 `create()` 시도.
- **방어선**: 대상 모델 대부분에 `unique_together` 존재 → 두 번째 `create()`는 `IntegrityError` 발생(조용한 중복 생성 ❌, 예외 ✅). Django는 unique 충돌 시 `get_or_create`에서 한 번 재조회를 시도하나, `update_or_create`는 그렇지 않아 `IntegrityError`가 호출부로 전파될 수 있음.

**실제 노출도 (낮음~중간)**:
- 대부분 호출이 **Celery Beat 단일 스케줄 태스크**(시계열 sync) → 동일 키 동시 진입 가능성 낮음.
- `relation_tasks.py`의 `get_or_create`(`59,95`)와 `update_or_create`(`193,299,335,374`)는 종목 페어 단위 — 배치 병렬화 시 같은 페어 충돌 이론상 가능. unique_together(`symbol_a, symbol_b, relation_type`)가 최종 방어.
- `stock_service.py`의 가격/재무 update_or_create는 종목 단위 직렬 처리 → 충돌 거의 없음.

**권고 (정보)**: 병렬 배치에서 같은 키 진입 가능한 경로(특히 chain_sight relation)는 `transaction.atomic()` + `IntegrityError` catch-retry 또는 `select_for_update` 패턴 고려. 현재는 unique_together가 데이터 오염은 막고 있으므로 "오염"이 아니라 "예외 전파/태스크 실패" 리스크.

### 🟠 M-4 — `StockNews.stock` CASCADE + null=True 혼용

`stocks/models.py:1153`:
```python
stock = models.ForeignKey("Stock", on_delete=models.CASCADE, null=True, blank=True)
```
- `null=True`이면서 `CASCADE` — 의미 모순적 조합. `symbol`(CharField)을 별도로 들고 계층적 매칭에 쓰는 구조(`null` 허용 = 아직 매칭 안 된 뉴스).
- 위험: stock이 NULL인 뉴스는 Stock 삭제와 무관(고아 아님), stock이 채워진 뉴스는 Stock 삭제 시 함께 삭제됨. 의도는 이해되나 `SET_NULL`이 더 안전한 선택이었을 수 있음(뉴스 원문 보존 관점). 현재 CASCADE면 Stock 삭제 시 매칭된 뉴스 원문 소실.
- 판정: 데이터 보존 정책상 재검토 권고(정보). 기능 버그는 아님.

---

## 부록: 정책 분포 요약

```
on_delete 정책 분포 (migration 제외, 95+17+7 = 119건)
├─ CASCADE   95건 — 시계열/스냅샷/조인 테이블 (소유 관계, 정상)
├─ SET_NULL  17건 — 15건 의도적 audit/log 보존 / 2건 검토대상(H-1, L-1)
└─ PROTECT    7건 — metrics_snapshot, chain news_event, portfolio 4건
                    (참조 무결성 강제: 부모 삭제 차단 — 가장 보수적, 양호)
```

**핵심 결론**:
1. PostgreSQL 내부 무결성은 견고 — unique_together 광범위, SET_NULL은 대부분 의도적 보존 패턴, PROTECT로 핵심 참조 보호.
2. **유일한 구조적 공백은 PG → Neo4j 삭제 전파 부재** (H-1, H-2, M-1). dirty-sync는 "생성/수정"만 전파하고 "삭제"를 전파하지 않음 → stale 노드/엣지 누적 구조. 운영상 물리 삭제가 드물어 현재 영향은 제한적이나, 정책이 아닌 관행에 의존.
3. 즉시 조치 우선순위: (1) Neo4j reconciliation 배치 신설(M-1), (2) sync 태스크 `max_retries` 상향 또는 backlog 영구실패 row 격리(M-2), (3) `StockNews.stock` SET_NULL 전환 검토(M-4).

---
*본 보고서는 정적 분석 기반이며 런타임 데이터(실제 orphan row 수, Neo4j vs PG 카운트 실측)는 포함하지 않음. 수치 검증을 위해서는 `quality_checks.py`의 `neo4j_pending` 카운트와 Neo4j `MATCH (s:Stock) RETURN count(s)` vs PG `Stock.objects.count()` 대조 실행 권장.*
