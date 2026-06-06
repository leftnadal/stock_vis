# 데이터 무결성 감사 보고서

> **작성일**: 2026-06-06
> **범위**: FK orphan / CASCADE 체인 / Neo4j↔PostgreSQL 동기화 / Unique 제약·동시성
> **방식**: 읽기 전용 정적 감사 (코드 수정 없음)
> **주의**: 지시서의 경로 가정(`stocks/models.py`, `users/models.py` 등)은 **서비스 리모델링으로 변경됨**. 실제 모델은 `packages/shared/`, `apps/`, `services/` 3개 레이어로 분산. 본 보고서는 **실제 코드 트리** 기준으로 작성.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 3 | ① Neo4j 드리프트 감지 메커니즘 부재(역방향 orphan), ② PG hard-delete → Neo4j 엣지/노드 미정리, ③ SET_NULL orphan 정리 로직 전무 |
| 🟡 Medium | 4 | ④ Stock 물리 삭제 시 36개 FK 4단계 CASCADE 폭발, ⑤ update_or_create read-modify-write lost-update(select_for_update 부재), ⑥ Neo4j sync 영구 실패 레코드의 무한 silent 재시도, ⑦ bulk_update 시 neo4j_dirty 수동 관리 누락 위험 |
| 🟢 Low / OK | 4 | ⑧ unique_together 커버리지 양호, ⑨ neo4j_dirty 단일 소스 패턴 정착(P0 #9), ⑩ 핵심 sync 서비스 @transaction.atomic 적용, ⑪ SET_NULL 대상에 비정규화 백업 필드(target_company_name) 존재 |

**총평**: FK 레벨 관계 무결성(unique 제약, CASCADE 정의)은 견고. **가장 큰 구조적 취약점은 PostgreSQL ↔ Neo4j 양방향 정합성**으로, 동기화는 push-only(PG→Neo4j MERGE)이며 PG 삭제가 Neo4j에 전파되지 않아 **그래프 orphan이 누적**된다. 드리프트를 탐지하는 reconciliation 명령/태스크가 없어 불일치가 조용히 쌓인다.

---

## FK orphan 위험

### SET_NULL 사용처 (실측 17개 라인 / 9개 파일)

> 지시서가 명시한 "7곳 3파일"은 `sec_pipeline / serverless / rag_analysis` **3개 파일에 한정한 부분집합**이다(sec 1 + serverless 3 + rag 3 = 7 ✓). 실제 코드베이스 전체에는 아래 17개 라인이 존재.

| # | 위치 | 필드 | 참조 대상 | orphan 시 비고 |
|---|------|------|----------|----------------|
| 1 | `services/sec_pipeline/models.py:94` | `SupplyChainEvidence.target_company` | `stocks.Stock` | 🟢 `target_company_name`(비정규화)이 살아남아 의미 보존 |
| 2 | `services/serverless/models.py:660` | `ScreenerAlert.preset` | `ScreenerPreset` | `filters_json` fallback 존재 → 커스텀 필터로 격하 |
| 3 | `services/serverless/models.py:797` | `InvestmentThesis.user` | `users.User` | 익명 테제로 잔존 (소유자 추적 불가) |
| 4 | `services/serverless/models.py:1353` | `AdminActionLog.user` | `users.User` | 감사 로그 작성자 소실 |
| 5 | `services/rag_analysis/models.py:132` | `AnalysisSession.basket` | `DataBasket` | 세션이 데이터 바스켓과 분리(exploration_path는 보존) |
| 6 | `services/rag_analysis/models.py:232` | `TokenUsageLog.session` | `AnalysisSession` | 비용 로그 세션 추적 끊김 |
| 7 | `services/rag_analysis/models.py:239` | `TokenUsageLog.message` | `AnalysisMessage` | 비용 로그 메시지 추적 끊김 |
| 8 | `thesis/models/thesis.py:70` | `Thesis.source_news` | `news.NewsArticle` | 출처 뉴스 소실 |
| 9 | `thesis/models/thesis.py:77` | `Thesis.copied_from` | `self` | 복제 계보 끊김 |
| 10 | `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | `ThesisPremise` | 지표↔전제 연결 소실 |
| 11 | `thesis/models/monitoring.py:66` | `ThesisAlert.indicator` | `ThesisIndicator` | 알림 근거 지표 소실 |
| 12 | `macro/models/indicators.py:310` | `EconomicEvent.related_indicator` | `EconomicIndicator` | 이벤트↔지표 연결 소실 |
| 13 | `apps/chain_sight/models/news_event.py:69` | `ChainNewsEvent.duplicate_of` | `self` | 중복 원본 포인터 소실(is_duplicate 플래그는 잔존) |
| 14 | `apps/market_pulse/models/anomaly.py:35` | `AnomalySignal.paired_news` | `MarketPulseNews` | 페어링된 뉴스 소실 |
| 15-17 | `apps/portfolio/models.py:341/768/870` | `wallet_snapshot_at_execution` 등 | `WalletSnapshot` | 실행 시점 스냅샷 소실 |

### orphan 정리 로직 존재 여부 — **🔴 전무 (High)**

- `__isnull=True` 기반의 **SET_NULL 잔존 레코드 수거(reap) 태스크/management command가 존재하지 않음**. 전체 코드에서 발견된 `__isnull` 용례는 전부 "NULL 제외 필터링"(예: `market_capitalization__isnull=False`)이며, **NULL이 된 FK를 정리하는 용도는 0건**.
- 결과: SET_NULL이 발생하면 해당 row는 `FK=NULL` 상태로 **영구 잔존**. 의도된 설계(soft-detach)일 수 있으나, 정리 정책이 문서화/구현되지 않아 시간이 지날수록 dangling row가 누적된다.
- **완화 요인**: 가장 빈번할 #1 `SupplyChainEvidence.target_company`는 `target_company_name`을 비정규화로 보존하므로 의미 손실은 최소화. #2 `ScreenerAlert.preset`은 `filters_json` fallback 보유.
- **권고(비수정)**: 각 SET_NULL 필드에 대해 "NULL 잔존 허용 vs 주기적 수거" 정책을 명시하고, 수거가 필요한 #4(감사 로그)·#6/#7(비용 로그)은 보존/아카이브 여부를 결정.

---

## CASCADE 체인

### CASCADE 사용처 (실측 약 95개 라인 / 25+ 파일)

> 지시서의 "37곳 7파일"은 일부 레거시 경로 기준. 실제는 리모델링으로 더 광범위.

### 3단계 이상 연쇄 삭제 추적

| 체인 | 단계 | 경로 |
|------|------|------|
| **SEC (Stock 기점)** | **4단계** | `Stock` → `RawDocumentStore` → `BusinessModelSnapshot` → `BusinessModelEvidence` (모두 CASCADE) |
| SEC 보조 | 3단계 | `Stock` → `RawDocumentStore` → `SupplyChainEvidence` (source_company는 별도 직접 CASCADE, target_company는 SET_NULL) |
| **News** | **3단계** | `NewsArticle` → `NewsEntity` → `NewsEntityHighlight` |
| **User/RAG** | **3단계** | `User` → `AnalysisSession` → `AnalysisMessage` (+ `TokenUsageLog`는 SET_NULL로 분리) |
| User/Screener | 3단계 | `User` → `ScreenerAlert` → `ScreenerAlertHistory` |
| User/Basket | 2단계 | `User` → `DataBasket` → `DataBasketItem` (AnalysisSession.basket은 SET_NULL) |
| ETF | 2단계 | `ETFProfile` → `ETFHolding` |
| Thesis | 2단계+ | `Thesis` → `{indicators, alerts, monitoring, learning, community}` 다중 CASCADE 팬아웃 |

### Stock 삭제 영향 범위 — **🟡 가장 많은 FK 참조 (Medium)**

- **Stock으로 향하는 FK ≈ 36개** (코드베이스 내 최대 fan-out). 참조 앱:
  `packages/shared/{stocks,users,metrics}`, `apps/{chain_sight,portfolio}`, `services/{sec_pipeline,validation}`.
- 대부분 `to_field="symbol"` (symbol 기반 FK) 또는 `"stocks.Stock"` 직접 참조이며 **거의 전부 CASCADE**.
- **단일 Stock 물리 삭제 시**: 위 4단계 SEC 체인 + validation 5종(CompanyMetricLatest/CompanyBenchmarkDelta/CategorySignal/CompanyMetricSnapshot 등) + chain_sight 프로파일 8종(GrowthStage/CapitalDNA/Sensitivity/NarrativeTag/EventReaction/RevenueStructure/InsiderSignal/ChainProfile) + Portfolio/Watchlist 보유분까지 **수십 개 테이블에서 동시 삭제**가 폭발.
- **실무 위험도**: Stock은 SP500 유니버스로 **물리 삭제가 드묾** → 일상 위험은 낮음. 그러나 ① soft-delete 패턴 부재, ② Stock 삭제가 **Neo4j :Stock 노드/엣지로 전파되지 않음**(아래 동기화 섹션)이 결합되면, 잘못된 Stock 삭제 1건이 PG 대량 삭제 + Neo4j orphan을 동시에 유발.
- **권고(비수정)**: Stock 삭제는 관리 명령에서 `is_active=False` soft-delete로 우회하거나, 삭제 전 영향 범위 dry-run 카운트를 출력하는 가드를 두는 것을 검토.

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황 — **🟢 단일 소스 패턴 정착 (OK)**

audit **P0 #9 (2026-04-29)** 결정으로 `synced_to_neo4j` 폐기, `neo4j_dirty`(True=동기화 필요)로 의미 통일. 적용 모델:

| 모델 | 위치 | 비고 |
|------|------|------|
| `CompanyChainProfile` | `apps/chain_sight/models/chain_profile.py:84` | `neo4j_dirty`(db_index) + `neo4j_synced_at` |
| `RelationConfidence` | `apps/chain_sight/models/relation_discovery.py:148` | `save()`에서 `neo4j_dirty=True` 자동 세팅 + Index |
| `SupplyChainEvidence` | `services/sec_pipeline/models.py:112` | `neo4j_dirty` + Index (synced_to_neo4j 금지 주석 명시) |

### 동기화 실패 시 재시도 메커니즘 — **🟡 암묵적 재시도만 존재 (Medium)**

- **패턴**: 동기화 성공 row의 pk만 모아 `queryset.update(neo4j_dirty=False)` → **실패 row는 dirty=True 유지 → 다음 Beat 실행에서 재시도** (`neo4j_sync.py:43-57`, `sync_tasks.py:161-167`). save() 대신 update() 사용으로 dirty 덮어쓰기 방지(올바른 구현).
- **재시도 정확성**: ✓ 정상 작동. 예외 발생 시 `synced_pks`에 미추가 → 영구 dirty 유지.
- **약점 #6 (Medium)**: 태스크 레벨 `max_retries=1`이고 relation 레벨 재시도는 **백오프/상한이 없는 무한 재시도**. 영구 실패 레코드(예: Neo4j에 영원히 없는 ticker, 손상된 props)는 **매 Beat마다 조용히(logger.error만) 재시도**되며 dead-letter/poison-pill 격리가 없다. 실패가 누적되면 매 사이클 동일 실패를 반복하며 sync 카운트를 잠식.
- **약점 #7 (Medium)**: `RelationConfidence`는 `save()`에서만 `neo4j_dirty=True`가 자동 세팅됨. `bulk_update()` 경로는 save()를 호출하지 않아 **dirty 플래그를 수동 관리해야 함**(코드 주석 `relation_discovery.py:178-179`에 명시). 신규 bulk 경로 추가 시 dirty 누락 → 동기화 누락 위험.

### PG↔Neo4j 불일치 감지 — **🔴 reconciliation 부재 (High)**

- **단방향 push만 존재**: `neo4j_loader.py`는 PG→Neo4j `MERGE`(node_count/edge_count는 로드 직후 결과 리포팅용일 뿐). dirty sync도 PG→Neo4j 방향.
- **역방향 orphan 미탐지 (🔴)**: "Neo4j에는 있는데 PG에는 없는" 케이스를 **감지·정리하는 메커니즘이 전무**.
  - **PG hard-delete가 Neo4j로 전파되지 않음**: `_delete_edge`는 RelationConfidence의 `relation_status ∈ {hidden, weak, stale}`일 때만 호출됨. **RelationConfidence row가 물리 삭제되면** dirty sync 대상에서 사라져 **Neo4j 엣지가 stale orphan으로 잔존**.
  - **CASCADE 삭제 미전파**: Stock CASCADE 삭제 시 PG에서는 수십 row가 지워지지만 **Neo4j :Stock 노드와 연결 엣지는 그대로 남음**.
- **양방향 카운트 드리프트 명령 없음**: `management/commands/`에 `load_*_to_neo4j`(push)는 있으나 `verify`/`reconcile`/`drift` 명령은 0건. PG count vs Neo4j count를 주기 비교하는 태스크 없음.
- **권고(비수정)**:
  1. PG↔Neo4j 카운트 드리프트 리포트 명령 추가(읽기 전용, 야간 리포트에 편입) — 본 nightly_auto_system 리포트 파이프라인의 자연스러운 확장점.
  2. RelationConfidence/Stock 삭제 시 Neo4j 엣지/노드를 정리하는 신호(pre_delete) 또는 주기적 orphan-node 스윕 검토.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 — **🟢 커버리지 양호 (OK)**

전 코드에서 `UniqueConstraint`(named)는 미사용이고 **레거시 `unique_together`로 일관**. 주요 제약:

| 도메인 | 제약 | 위치 |
|--------|------|------|
| 가격 | `(stock, date)` | `stocks/models.py:246,275` (DailyPrice/주간) |
| 재무 | `(stock, period_type, fiscal_year, fiscal_quarter)` | `stocks/models.py:492,607,765` (3종 재무제표) |
| EOD 시그널 | `(stock, signal_date, signal_tag)` | `stocks/models.py:1087` |
| 지표 스냅샷 | `(symbol, fiscal_year, metric_code)` | `metrics/benchmark.py`, `metric_snapshot.py` |
| 사용자 | `(user, stock)` / `(user, name)` / `(watchlist, stock)` / `(user, interest_type, value)` | `users/models.py:90,201,242,291` |
| Thesis | `(thesis, asof_date)` / `(indicator, asof)` / `(target, source, text)` / `(user, original_thesis)` | `thesis/models/*` |
| Chain Sight | `(source, source_id)` / `(symbol, event_type)` / `(symbol_a, symbol_b)` / `(symbol_a, symbol_b, period)` | `chain_sight/models/*` |
| SEC alias | `(alias, context_sector)` — `context_country`는 의도적 제외 | `sec_pipeline/models.py:331` |
| Macro | `(indicator, date)` / `(index, date)` / `(indicator_a, indicator_b)` 등 | `macro/models/*` |
| Validation | `(symbol, ...)` 다수 | `validation/models/*` |

- 평가: 핵심 시계열·스냅샷 테이블에 자연키 제약이 빠짐없이 설정되어 **중복 삽입 1차 방어선 견고**.
- 마이너: Django 권고는 `UniqueConstraint(name=...)`이나 기능상 문제 없음. 조건부(partial) unique는 없음.

### update_or_create race condition — **🟡 lost-update 위험 (Medium)**

- **규모**: `update_or_create`/`get_or_create` 약 **127개 용례** (60+ 서비스/태스크 파일).
- **원자성**: Django `update_or_create`는 기본적으로 **원자적이지 않음**(get→update/create). unique 제약이 있으면 최악의 경우 **중복 대신 IntegrityError**로 방어되므로(위 unique_together 커버리지 덕분) 중복 생성 위험은 낮음.
- **🟡 핵심 위험 — select_for_update 부재 read-modify-write**: 전 코드에서 `update_or_create` 직전 `select_for_update`로 행 잠금하는 패턴이 **0건**. 따라서 **JSON/카운터 누적 필드의 lost-update** 가능:
  - `UnmatchedCompanyQueue.occurrence_count` 증가, `source_sectors`/`theme_tags` JSON 누적 등 read-then-write 시 동시 실행되면 한쪽 갱신 소실.
  - `RelationConfidence` (`relation_tasks.py:299/335/374`)는 **@transaction.atomic 래핑이 코드상 보이지 않음** → Beat 주기 실행과 수동 트리거가 같은 `(symbol_a, symbol_b)`에 동시 도달 시 IntegrityError 가능(unique 제약이 데이터 손상은 막지만 태스크 예외 유발).
- **🟢 방어 적용된 곳**: `stock_sync_service.py`(`@transaction.atomic`), `institutional_holdings_service.py`(`with transaction.atomic()`) 등 핵심 동기화 서비스는 atomic 블록 내 update_or_create 사용.
- **권고(비수정)**:
  1. 카운터/JSON 누적형 update_or_create(특히 `UnmatchedCompanyQueue`)는 `F()` 표현식 또는 `select_for_update`로 lost-update 방지.
  2. `relation_tasks.py`의 update_or_create를 `transaction.atomic`으로 감싸 동시 트리거 시 IntegrityError를 격리.
  3. update_or_create의 lookup 키가 **반드시 unique 제약과 일치**하는지 점검(불일치 시 중복 생성 통로). 본 정적 감사로는 127건 전수 검증 불가 → 후속 정밀 점검 권고.

---

## 부록: 지시서 ↔ 실제 코드 경로 매핑

| 지시서 가정 경로 | 실제 경로 |
|------------------|----------|
| `stocks/models.py` | `packages/shared/stocks/models.py` |
| `users/models.py` | `packages/shared/users/models.py` |
| `graph_analysis/models.py` | `services/_dormant/graph_analysis/models.py` (휴면) |
| `serverless/models.py` | `services/serverless/models.py` |
| `rag_analysis/models.py` | `services/rag_analysis/models.py` |
| `sec_pipeline/models.py` | `services/sec_pipeline/models.py` |
| (신규) chainsight | `apps/chain_sight/models/*.py` (다중 파일) |

> 지시서의 "SET_NULL 7곳/CASCADE 37곳" 수치는 sec/serverless/rag 3개 파일 한정 부분집합으로, 실제 전체는 SET_NULL 17라인·CASCADE ~95라인. 향후 감사 지시서는 리모델링된 3-레이어 경로 기준으로 갱신 필요.
