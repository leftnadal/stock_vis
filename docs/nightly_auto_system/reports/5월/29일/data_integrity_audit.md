# 데이터 무결성 감사 보고서

> **작성일**: 2026-05-29
> **범위**: FK orphan / CASCADE 체인 / Neo4j↔PG 동기화 / Unique 제약
> **방식**: 읽기 전용 정적 분석 (코드 수정 없음)
> **대상 코드**: `*/models.py`, `*/tasks.py`, `*/services/*`, `*/signals.py` (migration·test 제외 집계)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 이슈 |
|--------|------|------|
| 🔴 HIGH | 2 | ① Stock 참조 `PROTECT`↔`CASCADE` 혼재 → 삭제 시 예측 불가/전체 롤백<br>② Neo4j `_delete_edge` 실패가 조용히 묻혀 dirty=False 처리 → stale 엣지 잔존 |
| 🟠 MEDIUM | 4 | ③ Neo4j→PG **역방향 reconciliation 부재**<br>④ `SupplyChainEvidence` unique 제약 부재 → 중복 row 가능<br>⑤ 3단계 CASCADE 체인 (Stock→RawDocumentStore→BusinessModelSnapshot→BusinessModelEvidence)<br>⑥ Neo4j sync 태스크 `max_retries=1` (dirty flag로 부분 보완) |
| 🟢 LOW | 2 | ⑦ SET_NULL 후 dangling FK 정리 로직 부분적 (sec_pipeline만 재매칭 존재)<br>⑧ `UsageLog` session/message SET_NULL 시 비용 추적 연결 단절 |

**핵심 발견**
- `on_delete` 실제 분포: **CASCADE 다수 / SET_NULL 17곳 / PROTECT 6곳**. 지시서가 명시한 "SET_NULL 7곳·CASCADE 37곳"은 **사용자 지정 3·7개 파일 기준**과 일치하나, **그 외 앱(thesis/portfolio/macro/marketpulse/metrics/validation/chainsight)에 동일 패턴이 추가 분포**한다. (아래 각 섹션에 "지정 범위 외" 표기)
- Stock PK가 `symbol` (CharField, `primary_key=True`) → `to_field='symbol'` 참조가 광범위. **Stock 삭제 = 대규모 연쇄 + PROTECT 충돌**.
- `neo4j_dirty` 단일 소스 패턴(audit P0 #9)은 잘 정착됨. 다만 **delete 경로의 실패 은닉**과 **역방향 검증 부재**가 약점.

---

## FK orphan 위험

### SET_NULL 사용처 (전체 17곳)

| 파일:라인 | 필드 | 대상 | 지정범위 | 정리 로직 |
|-----------|------|------|:--------:|----------|
| `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | stocks.Stock | ✅ | **있음** (재매칭) |
| `serverless/models.py:660` | `ScreenerAlert.preset` | ScreenerPreset | ✅ | 불필요(설계상) |
| `serverless/models.py:808` | `InvestmentThesis.user` | users.User | ✅ | 없음 |
| `serverless/models.py:1409` | (LLM relation).user | users.User | ✅ | 없음 |
| `rag_analysis/models.py:145` | `AnalysisSession.basket` | DataBasket | ✅ | 없음 |
| `rag_analysis/models.py:256` | `UsageLog.session` | AnalysisSession | ✅ | 없음 ⚠️ |
| `rag_analysis/models.py:263` | `UsageLog.message` | AnalysisMessage | ✅ | 없음 ⚠️ |
| `chainsight/models/news_event.py:54` | `ChainNewsEvent.duplicate_of` (self) | self | 범위 외 | 불필요 |
| `thesis/models/thesis.py:70,77` | (가설 참조 2건) | — | 범위 외 | 미확인 |
| `thesis/models/indicator.py:15` | (지표 참조) | — | 범위 외 | 미확인 |
| `thesis/models/monitoring.py:66` | (모니터링 참조) | — | 범위 외 | 미확인 |
| `macro/models/indicators.py:310` | (지표 참조) | — | 범위 외 | 미확인 |
| `marketpulse/models/anomaly.py:25` | (이상치 참조) | — | 범위 외 | 미확인 |
| `portfolio/models.py:327,732,831` | (포트폴리오 참조 3건) | — | 범위 외 | 미확인 |

> 지시서가 명시한 **3개 파일(sec_pipeline·serverless·rag_analysis) 기준 7곳**은 정확히 일치. 위 표의 나머지 10곳은 추가 발견분.

### SET_NULL 후 orphan(dangling) 정리 로직

**1) `sec_pipeline.SupplyChainEvidence.target_company` — 정리 로직 존재 ✅ (모범 사례)**

target_company가 NULL이 되어도(혹은 처음부터 미매칭) 다음 경로로 복구·관리된다:
- `sec_pipeline/signals.py:21` `on_unmatched_resolved`: `UnmatchedCompanyQueue`가 `matched`로 바뀌면 동일 이름+동일 sector evidence의 `target_company`를 **재연결** (`qs.update(target_company=..., neo4j_dirty=True)`, line 52). sector 경계 밖 전파 차단.
- `sec_pipeline/management/commands/rematch_unmatched.py:33`: `target_company__isnull=True` 전수 재매칭 커맨드.
- `sec_pipeline/quality_checks.py:142-143`, `intelligence.py:91-92`: `matched/unmatched` 카운트 모니터링.

**2) 나머지 SET_NULL — 정리 로직 없음 (대부분 설계상 허용)**

- `rag_analysis.UsageLog.session/message`: SET_NULL은 **로그 보존 목적**으로 의도적. 다만 session/message가 삭제되면 **비용 추적의 세션 귀속이 끊김** → 사후 정산/집계 시 NULL 그룹 처리 필요. (🟢 LOW, 이슈 ⑧)
- `serverless.InvestmentThesis.user` / `ScreenerAlert.preset`: user/preset 삭제 후 NULL 잔존은 정상 동작. 별도 정리 불필요.
- `AnalysisSession.basket`: basket 삭제 시 세션은 유지(NULL). 의도된 동작.

> **판정**: SET_NULL은 본질적으로 "orphan"이 아니라 "NULL 허용 dangling"이므로 무결성 위배는 아님. 단 sec_pipeline 외에는 **NULL 잔존 행을 주기적으로 청소/집계 분리하는 로직이 없어**, 통계·과금 집계에서 NULL 버킷 누락 주의. (🟢 LOW)

---

## CASCADE 체인

### Stock 삭제 영향 범위 (가장 많은 FK 참조)

**Stock PK = `symbol` (CharField, primary_key=True, unique)** — `stocks/models.py:20`. 다수 모델이 `to_field='symbol'`로 직접 참조.

#### (A) Stock 삭제 시 CASCADE로 함께 삭제되는 모델

| 앱 | 모델/필드 | 라인 | 지정범위 |
|----|-----------|------|:--------:|
| stocks | DailyPrice, WeeklyPrice 등 `stock`(to_field=symbol) | 133, 244 | ✅ |
| stocks | `StockOverviewKo` (OneToOne, PK=stock) | 699 | ✅ |
| stocks | financial/news 계열 `stock` 3건 | 756, 801, 888 | ✅ |
| users | `Portfolio.stock`, `WatchlistItem.stock` (to_field=symbol) | 28, 198 | ✅ |
| sec_pipeline | `RawDocumentStore.symbol` | 25 | ✅ |
| sec_pipeline | `SupplyChainEvidence.source_company` (target은 SET_NULL) | 82 | ✅ |
| sec_pipeline | `BusinessModelSnapshot.symbol` | 161 | ✅ |
| graph_analysis | `CorrelationEdge.stock_a`, `stock_b` | 75, 82 | ✅ |
| validation | benchmark_delta / category_score / metric_latest / news_summary / peer_preset×2 | 7,20,7,7,20,50 | 범위 외 |
| chainsight | insider_signal·revenue_structure·capital_dna·event_reaction·growth_stage·narrative_tag·sensitivity·chain_profile (8, 대부분 OneToOne PK=symbol) | — | 범위 외 |
| metrics | `PeerMetricBenchmark`·benchmark 계열 `symbol` | 12, 100 | 범위 외 |

→ Stock 1건 삭제 시 **수십 개 테이블에 걸쳐 CASCADE 전파**. Stock은 사실상 도메인 루트 엔티티.

#### (B) 3단계 이상 연쇄 삭제 (이슈 ⑤, 🟠 MEDIUM)

```
[체인 1] Stock(symbol)
  └─CASCADE→ RawDocumentStore (sec_raw_document_store)
       └─CASCADE→ SupplyChainEvidence            (source_document FK, models.py:78)
       └─CASCADE→ BusinessModelSnapshot          (source_document FK, models.py:165)
            └─CASCADE→ BusinessModelEvidence     (snapshot FK, models.py:213)   ← 4단계
```

```
[체인 2] User
  └─CASCADE→ Watchlist (users)
       └─CASCADE→ CorrelationMatrix              (graph_analysis/models.py:18)
       └─CASCADE→ CorrelationEdge                (graph_analysis/models.py:68)
```

```
[체인 3] User
  └─CASCADE→ AnalysisSession (rag_analysis/models.py:138)
       └─CASCADE→ AnalysisMessage                (models.py:192)
            └─(UsageLog.message는 SET_NULL → 로그 보존)
```

> **체인 1**이 가장 깊다(Stock→문서→스냅샷→근거문장, 최대 4단계). 단일 Stock 삭제가 SEC 파이프라인 산출물 전체를 침묵 삭제. 운영 중 종목 폐지/심볼 변경 시 **대량 silent delete** 위험 → 삭제 전 영향 카운트 확인 절차 권장.

#### (C) 🔴 HIGH — PROTECT ↔ CASCADE 혼재 (이슈 ①)

동일한 `stocks.Stock`을 일부 모델은 CASCADE, 일부는 **PROTECT**로 참조한다:

| 모델 | on_delete | 위치 |
|------|-----------|------|
| `metrics.CompanyMetricSnapshot.symbol` | **PROTECT** | `metrics/models/metric_snapshot.py:11` |
| `chainsight.ChainNewsEvent.symbol` | **PROTECT** | `chainsight/models/news_event.py:23` |
| `portfolio` 4개 모델의 `stock` | **PROTECT** | `portfolio/models.py:90,393,495,566` |
| (위 A의 수십 개 모델) | CASCADE | — |

**위험**: Stock 삭제 시,
1. PROTECT 참조가 **하나라도** 존재하면 `ProtectedError` 발생 → **트랜잭션 전체 롤백** (CASCADE 대상도 삭제 안 됨).
2. 즉 metric_snapshot/news_event/portfolio holding이 있는 종목은 **삭제 자체가 불가**하며, 그 사실이 ORM 레벨에서만 드러난다(사전 차단 로직 없음).
3. 반대로 그 참조들이 비어 있으면 (A)의 대규모 CASCADE가 조용히 실행된다.

→ **삭제 가능 여부가 데이터 상태에 따라 갈리는 비결정적 동작**. 운영 스크립트/관리자 삭제 시 예외 처리 및 사전 점검 필수. on_delete 정책을 종목 루트 기준으로 통일하거나, Stock에 soft-delete(`is_active`) 도입 검토 권장.

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황

`synced_to_neo4j` 폐기 후 **`neo4j_dirty` 단일 소스**로 통일됨 (audit P0 #9, 2026-04-29). 마이그레이션 `chainsight/migrations/0008_unify_neo4j_flags.py`에서 의미 반전까지 정리 완료.

| 모델 | 플래그 필드 | 인덱스 | sync 진입점 |
|------|------------|:------:|-------------|
| `sec_pipeline.SupplyChainEvidence` | `neo4j_dirty` + `neo4j_synced_at` | ✅ (`models.py:111`) | `sec_pipeline/tasks.py` sync_dirty_to_neo4j |
| `chainsight.RelationConfidence` | `neo4j_dirty` + `neo4j_synced_at` | ✅ (`relation_discovery.py:143`) | `chainsight/services/neo4j_sync.py` |
| `chainsight.CompanyChainProfile` | `neo4j_dirty` (db_index) | ✅ | `chainsight/tasks/sync_tasks.py` |

**dirty 자동 세팅 규칙 (정확히 구현됨)**:
- `save()` 경로: `relation_discovery.py:157-158`에서 자동 `neo4j_dirty=True`. update_or_create의 save()도 동일 효과.
- `queryset.update()`/`bulk_update()` 경로: save() 미호출 → **수동 토글** (`relation_tasks.py:388,395,402`, `sync_tasks.py:169`, `signals.py:52`). 주석으로 명시되어 누락 위험 관리됨.

### 동기화 실패 시 재시도 메커니즘

**1) dirty flag = 사실상의 재시도 큐 (견고)**
- 성공한 PK만 `dirty=False`로 마킹 (`neo4j_sync.py:47-51`, `tasks.py:441-445`, `sync_tasks.py:136-138`). 실패분은 dirty=True 유지 → 다음 배치에서 자동 재처리.
- `sec_pipeline/tasks.py`: 2-Phase + `select_for_update(skip_locked=True)` (line 367)로 동시 워커 중복 처리 방지. CREATE 성공분만 `synced_ids` 누적(line 436) → 부분 실패 안전.

**2) 🟠 MEDIUM (이슈 ⑥) — Celery 레벨 재시도 약함**
- `sync_tasks.py:14,97,148` 모두 `max_retries=1`. 태스크 자체 재시도는 1회뿐. dirty flag 패턴이 보완하나, 배치 주기(주 1회 등)가 길면 복구 지연.

**3) 🔴 HIGH (이슈 ②) — delete 경로 실패 은닉**
- `chainsight/services/neo4j_sync.py:84-91` `_delete_edge`: 내부 `try/except`로 **warning 로그만** 남기고 예외를 삼킨다. 상위 `sync_dirty_relations`(line 32-41)는 호출이 예외 없이 끝나면 `synced_pks.append(rc.pk)` → 곧 `dirty=False`.
  → **Neo4j 엣지 삭제가 실패해도 PG는 "동기화 완료"로 마킹**. 결과적으로 hidden/weak/stale 상태인데 Neo4j에 **stale 엣지가 영구 잔존**할 수 있다.
- `sec_pipeline/tasks.py:401-412`도 DELETE를 `except: pass`로 무시하나, 여기서는 직후 CREATE가 성공해야 synced 처리되므로 영향이 제한적(엣지 재생성). 단 **DELETE 성공 + CREATE 실패** 시엔 dirty 유지되어 일시적으로 Neo4j 누락 → 재시도로 복구.

### PG↔Neo4j 불일치 감지 방법

| 방향 | 감지 수단 | 상태 |
|------|-----------|------|
| **PG→Neo4j 미반영 backlog** | `quality_checks.py:92,146` `neo4j_dirty=True & matched>50` 알림; `intelligence.py:98` sync_pending 카운트 | ✅ 있음 |
| **Neo4j→PG 역방향 (Neo4j엔 있고 PG엔 없거나, dirty=False인데 실제 엣지 누락)** | — | ❌ **없음** (이슈 ③, 🟠 MEDIUM) |
| **news orphan 노드** | `news/services/news_neo4j_sync.py:700` orphan NewsEvent 노드 삭제 쿼리 존재 | ✅ 부분적 |

> **권장**: dirty=False인 레코드 표본을 Neo4j에 역조회해 엣지 존재를 검증하는 **주기적 reconciliation 잡** 도입. 특히 ②의 delete 은닉과 결합되면 stale 엣지가 누적되어도 어떤 지표로도 드러나지 않는다.

---

## Unique 제약조건

### 설정 현황 (양호 — 대부분 적절)

핵심 모델에 `unique_together`/`UniqueConstraint`가 폭넓게 적용됨:

| 모델 | 제약 | 위치 |
|------|------|------|
| stocks (DailyPrice/Weekly/Financial×3/Signal) | `(stock, date)` / `(stock, period_type, fiscal_year, fiscal_quarter)` / `(stock, signal_date, signal_tag)` | `stocks/models.py:185,358,427,526,825` |
| users | `(user,stock)` `(user,name)` `(watchlist,stock)` `(user,interest_type,value)` | `users/models.py:71,179,217,265` |
| chainsight.RelationConfidence | `(symbol_a, symbol_b, relation_type)` | `relation_discovery.py:139` |
| chainsight (peer/period/news_event/event_reaction) | `(symbol_a,symbol_b)` / `(…,period)` / `(source,source_id)` / `(symbol,event_type)` | 다수 |
| sec_pipeline | `RawDocumentStore.accession_no` unique / `CompanyAlias (alias, context_sector)` | `models.py:28,295` |
| rag_analysis.BasketItem | `(basket, item_type, reference_id)` | `models.py:111` |
| graph_analysis | `(watchlist,date)` `(watchlist,stock_a,stock_b,date)` `(stock,date)` | `models.py:51,127,316` |
| validation/metrics | `(symbol, fiscal_year, metric_code[, preset_key])` 계열 | 다수 |
| serverless | `(date,mover_type,symbol)` `(etf,stock_symbol,snapshot_date)` `(institution_cik,stock_symbol,report_date)` 등 | 다수 |
| portfolio | `UniqueConstraint` 4종 (percentile_cache, card_priority, comment, metric_result) + `(wallet,stock)` | `models.py:128,439,525,583,701` |

### 🟠 MEDIUM (이슈 ④) — SupplyChainEvidence unique 제약 부재

`sec_pipeline.SupplyChainEvidence`(`models.py:61`)의 `Meta`에는 **인덱스만 있고 unique_together가 없다**.
- 동일 `source_document` + `source_company` + `target_company_name` + `relationship_type` 조합이 재추출되면 **중복 row 생성 가능**.
- 추출은 `create` 기반(update_or_create 아님)으로 보여, 같은 10-K 재처리/재시도 시 중복 누적 위험. → `(source_document, source_company, target_company_name, relationship_type)` 유니크 검토 권장.

### update_or_create / get_or_create race condition

| 호출부 | 키 | DB unique 제약 | race 안전성 |
|--------|----|:--------------:|-------------|
| `sec_pipeline/tasks.py:314` `RelationConfidence.update_or_create(symbol_a, symbol_b, relation_type)` | (symbol_a, symbol_b, relation_type) | ✅ 있음 | **안전** — 동시 insert 시 IntegrityError로 차단, 재조회 가능 |
| `chainsight/tasks/sync_tasks.py:84` `CompanyChainProfile.update_or_create(symbol=stock)` | symbol (OneToOne PK) | ✅ PK | **안전** |
| `sec_pipeline/signals.py:63` `CompanyAlias.get_or_create(alias, context_sector)` | (alias, context_sector) | ✅ 있음 | **안전** (드물게 IntegrityError 가능하나 제약이 최종 방어) |

> **판정**: 점검한 update_or_create/get_or_create 호출은 모두 **대상 키에 DB unique 제약이 존재**하여 race condition 발생 시에도 중복 row가 생기지 않고 IntegrityError로 차단된다. Django `update_or_create`의 일반적 위험(unique 제약 없는 필드 조합)에 해당하는 호출은 발견되지 않음. 단, ④의 `SupplyChainEvidence`처럼 **unique 제약이 없는 모델에 향후 update_or_create를 도입하면** race 위험이 즉시 발생하므로 제약 선설치가 전제.

---

## 권고 우선순위

| 순위 | 이슈 | 조치 |
|------|------|------|
| 1 | ① PROTECT↔CASCADE 혼재 | Stock soft-delete 도입 또는 삭제 전 PROTECT 참조 사전 점검 루틴. on_delete 정책 문서화 |
| 2 | ② delete 실패 은닉 | `_delete_edge` 실패 시 dirty=True 유지(synced_pks 제외)하도록 호출 규약 점검 |
| 3 | ③ 역방향 reconciliation 부재 | dirty=False 표본 Neo4j 역조회 검증 잡 신설 |
| 4 | ④ SupplyChainEvidence unique 부재 | 중복 방지 unique_together 검토 |
| 5 | ⑤ 4단계 CASCADE | Stock 삭제 전 영향 카운트 표시 + 운영 가드 |
| 6 | ⑥ max_retries=1 | dirty backlog 알림 임계/주기 점검으로 보완 |

*본 보고서는 정적 분석 기반이며 실제 DB 상태(NULL 잔존 행 수, stale 엣지 수)는 미측정. 위 ②③ 검증 잡 도입 시 실측 권장.*
