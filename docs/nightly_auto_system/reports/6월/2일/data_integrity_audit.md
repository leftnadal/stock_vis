# 데이터 무결성 감사 보고서

> **감사 일자**: 2026-06-02
> **감사 범위**: PostgreSQL FK 무결성, CASCADE 연쇄, Neo4j↔PG 동기화, Unique 제약/동시성
> **감사 방식**: 읽기 전용 정적 분석 (코드 수정 없음)
> **대상 모델 파일**: 8개 (migrations/test 제외)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 2 | (1) Neo4j 동기화 실패 시 **무한 dirty 잔류** — 개별 레코드 예외가 삼켜져 영구 정체 가능, 재시도 로직 없음 (2) SEC 4단계 CASCADE 체인 — Stock 1건 삭제 시 RawDocumentStore→BusinessModelSnapshot→BusinessModelEvidence 연쇄 소실 |
| 🟡 Medium | 4 | (3) SET_NULL 후 **orphan 정리 로직 전무** (4) `update_or_create` race condition (락/atomic 미적용 다수) (5) PG↔Neo4j 양방향 불일치 **능동 감지 수단 없음** (적체량만 측정) (6) Stock 삭제 영향 범위 광범위 (직간접 30+ 테이블) |
| 🟢 Low | 3 | (7) `_dormant/graph_analysis` 사장 모델의 CASCADE 잔존 (8) SET_NULL FK 일부 인덱스 부재 (9) 일부 unique_together가 nullable 컬럼 포함(부분 유니크 약화) |

**종합 평가**: FK 레벨의 DB 무결성(CASCADE/unique)은 **대체로 견고**. 가장 큰 리스크는 **Neo4j↔PG 이종 저장소 간 일관성** — eventual consistency를 `neo4j_dirty` 단일 플래그에 의존하나, 실패 복구·드리프트 감지가 미흡하다.

---

## FK orphan 위험

### SET_NULL 사용처 (확정 17곳 — 지시서 7곳보다 많음, 코드베이스 재구성 반영)

| 파일 | 라인 | 필드 | 의도 | orphan 위험 |
|------|------|------|------|------------|
| `services/sec_pipeline/models.py` | 94 | `SupplyChainEvidence.target_company → Stock` | 매칭 실패/상폐 종목 보존 | 🟡 target_company=NULL인 evidence 누적, 정리 없음 |
| `services/serverless/models.py` | 660 | `ScreenerAlert.preset → ScreenerPreset` | 프리셋 삭제 시 커스텀 알림 전환 | 🟢 의도된 설계(filters_json fallback) |
| `services/serverless/models.py` | 797 | `InvestmentThesis.user → User` | 익명 테제 보존 | 🟡 user=NULL 테제 orphan화, 소유자 추적 불가 |
| `services/serverless/models.py` | 1353 | `AdminActionLog.user → User` | 감사 로그 보존 | 🟢 의도된 설계(감사 추적은 user 삭제 후에도 유지) |
| `services/rag_analysis/models.py` | 132 | `AnalysisSession.basket → DataBasket` | 바스켓 삭제 후 세션 유지 | 🟡 basket=NULL 세션, 분석 컨텍스트 유실 |
| `services/rag_analysis/models.py` | 232 | `UsageLog.session → AnalysisSession` | 사용량 로그 보존 | 🟢 의도된 설계(과금/사용량 집계 보존) |
| `services/rag_analysis/models.py` | 239 | `UsageLog.message → AnalysisMessage` | 사용량 로그 보존 | 🟢 의도된 설계 |
| `apps/chain_sight/models/news_event.py` | 69 | `ChainNewsEvent.duplicate_of → self` | 중복 원본 삭제 시 단절 | 🟡 자기참조, is_duplicate=True인데 duplicate_of=NULL 모순 상태 가능 |
| `thesis/models/*.py` | 66/15/70/77 | thesis 관련 4곳 | 가설/지표 보존 | 🟢 지시서 범위 외(thesis 도메인) |
| `macro/`, `apps/portfolio/`, `apps/market_pulse/` | 6곳 | — | — | 🟢 지시서 범위 외 |

> **지시서 명시 3개 파일(sec_pipeline, serverless, rag_analysis)의 SET_NULL은 총 7곳**으로 지시서 카운트와 일치. 나머지 10곳은 thesis/macro/portfolio/market_pulse/chainsight에 분포.

### SET_NULL 후 orphan 레코드 정리 로직 — **존재하지 않음** 🟡

전수 검색 결과(`orphan|cleanup|dangling|prune`):

- `null=True`로 전환된 레코드를 **재매칭하거나 정리하는 배치 태스크 부재**.
- 발견된 cleanup 태스크는 모두 **시간 기반 만료** 삭제이지 orphan 정리가 아님:
  - `config/tasks.py:140` `cleanup_old_task_results` — TaskResult 30/90일 만료
  - `packages/shared/users/tasks.py:133` `cleanup_old_portfolio_history` — 시간 기반
  - `apps/chain_sight/tasks/seed_tasks.py:176` `cleanup_seed_snapshots` — retain_days 기반
  - `services/news/tasks.py` `cleanup_expired_news_relationships` — 만료 기반
- **특히 `SupplyChainEvidence.target_company=NULL`**: SEC 파이프라인은 매칭 실패 시 `UnmatchedCompanyQueue`에 적재하고 추후 재매칭하는 구조이나(`quality_checks.py` §5에서 적체 100건 초과 시 알림만), **이미 NULL로 떨어진 기존 evidence를 사후 재연결하는 로직은 코드상 확인되지 않음**. 큐 적재와 NULL FK 보정이 분리되어 있어 orphan이 영구화될 수 있음.

**권고**: ① `target_company__isnull=True` evidence를 주기적으로 `CompanyAlias`/티커 매처로 재시도하는 backfill 태스크 추가. ② `ChainNewsEvent`의 `is_duplicate=True AND duplicate_of__isnull=True` 모순 상태 정합성 체크.

---

## CASCADE 체인

### CASCADE 사용처 (확정 87곳 — 지시서 37곳/7파일은 일부만 반영)

지시서가 명시한 7개 파일(stocks/users/news/serverless/rag_analysis/sec_pipeline/graph_analysis) 외에도 `macro`, `metrics`, `thesis`, `chain_sight`, `portfolio`, `market_pulse`, `validation`에 다수 분포. 핵심은 **Stock/User를 루트로 하는 다단계 연쇄**.

### 🔴 가장 깊은 연쇄: SEC Pipeline 4단계

```
Stock (PK=symbol)
└─CASCADE→ RawDocumentStore (sec_pipeline:26, symbol FK)
   ├─CASCADE→ SupplyChainEvidence (sec_pipeline:88, source_document FK)   [3단계]
   └─CASCADE→ BusinessModelSnapshot (sec_pipeline:181, source_document FK)
              └─CASCADE→ BusinessModelEvidence (sec_pipeline:243, snapshot FK)  [4단계]
```

추가로 `SupplyChainEvidence.source_company`(83)와 `BusinessModelSnapshot.symbol`(175)도 **Stock 직결 CASCADE** → 동일 자식이 **두 경로(Stock 직접 + RawDocumentStore 경유)**로 도달 가능. Django는 중복 삭제를 안전 처리하나, **단일 Stock 삭제가 SEC 도메인 4개 테이블 전부를 비움**.

### User 루트 연쇄 (rag_analysis / serverless)

```
User
├─CASCADE→ DataBasket (rag:14) ─CASCADE→ BasketItem (rag:73)              [3단계]
├─CASCADE→ AnalysisSession (rag:129) ─CASCADE→ AnalysisMessage (rag:178)  [3단계]
│          (UsageLog는 session/message가 SET_NULL → 보존)
└─CASCADE→ ScreenerAlert (serverless:648) ─CASCADE→ AlertHistory (serverless:747)  [3단계]
```

### Stock 삭제 시 영향 범위 — **가장 광범위한 FK 허브** 🟡

`Stock`(PK=`symbol`)을 직접 참조하는 CASCADE FK (직접 자식, 13개 모델 확인):

| 도메인 | 모델/테이블 | on_delete |
|--------|------------|-----------|
| stocks | DailyPrice, WeeklyPrice(추정), IncomeStatement/BalanceSheet/CashFlow(period FK), StockOverviewKo(O2O,946), EODSignal 등 6+ | CASCADE |
| users | PortfolioStock(47), WatchlistItem(223) | CASCADE |
| metrics | CompanyMetricSnapshot(13), benchmark(124) | CASCADE (to_field=symbol) |
| validation | metric_latest, category_score, benchmark_delta, news_summary, peer_preset 5개 | CASCADE (to_field=symbol) |
| chain_sight | CompanyChainProfile(O2O,14), narrative_tag, sensitivity, growth_stage, event_reaction, capital_dna, revenue_structure, insider_signal, news_event 9개 | CASCADE (to_field=symbol) |
| sec_pipeline | RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot 3개(+ 손자 evidence) | CASCADE |
| portfolio | 4개 (91/408/519/593) | CASCADE |

**Stock 1건 삭제 시 직접 30+ 테이블, 간접(손자) 포함 35+ 테이블에서 행 삭제 발생**. 추가로 다수가 `to_field="symbol"` (자연키 FK) → 심볼 변경/리네임 시 FK 무결성 재계산 비용 큼.

🔴 **부수 효과**: `CompanyChainProfile`은 Stock과 1:1(CASCADE)이며 `neo4j_dirty` 플래그 보유. **Stock을 PG에서 삭제하면 profile row는 사라지지만, 이미 Neo4j에 push된 `:Stock` 노드/엣지는 PG 삭제를 트리거로 정리되지 않음** → Neo4j 측 고아 노드 발생(아래 §Neo4j 동기화 참조).

**권고**: ① 운영 환경에서 Stock 물리 삭제 대신 **soft-delete(`is_active=False`) 고려**, 또는 ② Stock 삭제 시 Neo4j 노드 동기 삭제를 보장하는 `post_delete` 시그널/태스크 추가. 현재 삭제 경로에 Neo4j 정리 훅 없음.

### 🟢 사장(dormant) 모델 CASCADE

`services/_dormant/graph_analysis/models.py`에 CASCADE 8곳 잔존. 비활성 앱이나 마이그레이션/테이블이 살아있다면 무결성 부채. INSTALLED_APPS 등록 여부 확인 권고.

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 현황 (audit P0 #9에서 단일 소스로 통일, 2026-04-29)

| 모델 | 플래그 | 인덱스 | 동기화 태스크 |
|------|--------|--------|--------------|
| `apps/chain_sight/CompanyChainProfile` (chain_profile.py:84) | `neo4j_dirty` (default=True) + `neo4j_synced_at` | ✅ db_index=True | `sync_profiles_to_neo4j` (sync_tasks.py:107) |
| `apps/chain_sight/RelationConfidence` (relation_discovery.py:148) | `neo4j_dirty` + `neo4j_synced_at` | ✅ Index(fields=["neo4j_dirty"]) | `sync_dirty_relations` (neo4j_sync.py:22) |
| `services/sec_pipeline/SupplyChainEvidence` | `neo4j_dirty` + `neo4j_synced_at` | ✅ (test 478에서 인덱스 검증) | (quality_checks 적체 모니터만) |

> 설계상 의미 반전 명확히 적용됨: `synced_to_neo4j`(True=완료) → `neo4j_dirty`(True=동기화 필요)로 통일. `update_or_create`/`save()`가 자동으로 dirty=True를 세팅하고, `queryset.update()`/`bulk_update` 경로는 **수동 토글**(relation_tasks.py:421/428/435, relation_discovery.py:178 주석)로 명시 관리 — **이 부분은 잘 설계됨**.

### 🔴 동기화 실패 시 재시도 메커니즘 — **취약**

**(1) 개별 레코드 예외 삼킴 → 영구 dirty 잔류**

`sync_dirty_relations` (neo4j_sync.py:38-43):
```python
except Exception as e:
    logger.error(f"Failed to sync relation {rc.pk}: {e}")   # 로그만, synced_pks에 미추가
```
- 실패한 레코드는 `synced_pks`에서 제외 → `neo4j_dirty=True` 유지(다음 회차 재시도). **자가 치유 측면은 OK**.
- 그러나 **특정 레코드가 영구 실패(malformed data 등)하면 매 회차 무한 재시도**하며, 백오프·실패 카운터·DLQ(dead-letter) 없음 → **dirty 백로그가 줄지 않고 누적**될 수 있음.

`sync_profiles_to_neo4j` (sync_tasks.py:165-167): 동일 패턴. 실패 시 dirty 유지하나 영구 실패 격리 장치 없음.

**(2) 태스크 레벨 재시도 빈약**
- `sync_profiles_to_neo4j`: `max_retries=1` — Neo4j 일시 장애 시 재시도 1회뿐.
- `run_neo4j_dirty_sync`: `max_retries=2, default_retry_delay=60` — 다소 양호하나 `sync_dirty_relations()` 내부 예외를 다시 raise하지 않아(개별 except로 흡수) **태스크 레벨 retry가 사실상 트리거되지 않음**. 태스크는 거의 항상 "성공"으로 종료.
- 대조군: `sec_pipeline/tasks.py`는 `self.retry(countdown=60*(2**retries))` **exponential backoff 적용**(CLAUDE.md 규칙 준수). Neo4j 동기화 태스크들은 이 규칙을 따르지 않음.

**(3) 트랜잭션 경계 없음**: Neo4j upsert 성공 후 `RelationConfidence.update(neo4j_dirty=False)` 사이에 PG 장애가 나면 — Neo4j엔 반영됐는데 PG는 dirty=True 유지 → 다음 회차 **중복 upsert**(멱등이라 데이터 손상은 없으나 불필요한 부하).

### 🟡 PG↔Neo4j 불일치 감지 방법 — **능동 감지 부재, 적체량 추정만**

- **PG→Neo4j 방향**: `neo4j_dirty=True` count로 "아직 안 보낸 양"만 파악. `quality_checks.py:96` `dirty_count > 50`이면 알림. → **백로그 크기**는 알 수 있으나 **실제 동기화 여부 검증 아님**.
- **Neo4j→PG 방향 (고아 노드/엣지)**: **감지 수단 전무**.
  - PG에서 Stock/Relation이 삭제(CASCADE)되어도 Neo4j 노드/엣지를 정리하는 경로 없음.
  - `_delete_edge`(neo4j_sync.py)는 `relation_status`가 hidden/weak/stale일 때만 호출 → **PG row 자체가 사라지면 dirty 플래그도 함께 사라져 삭제 트리거가 영영 발생 안 함**.
- **노드 수 대조(reconciliation) 잡 부재**: PG `Stock.count()` vs Neo4j `MATCH (s:Stock) RETURN count(s)` 비교 같은 정합성 검사 코드 없음. (MEMORY 기록상 운영 Neo4j는 1573 노드/12695 관계 — 수동 확인에 의존)

**권고**:
1. **영구 실패 격리**: `neo4j_sync_attempts`/`last_sync_error` 컬럼 추가, N회 초과 실패 시 dirty=False + `sync_failed=True`로 격리하고 알림.
2. **삭제 동기화**: Stock/Relation `post_delete` 시그널 → Neo4j 노드/엣지 삭제 태스크. 또는 주기적 reconciliation 잡(PG에 없는 Neo4j 노드 정리).
3. **드리프트 대시보드**: PG count vs Neo4j count 일별 비교 + 임계 초과 알림.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 — **커버리지 양호** 🟢

핵심 시계열/스냅샷 테이블에 자연키 유니크가 일관 적용됨:

| 도메인 | 제약 | 위치 |
|--------|------|------|
| stocks 시계열 | `(stock, date)` DailyPrice/WeeklyPrice | stocks/models.py:246,275,1048 |
| stocks 재무 | `(stock, period_type, fiscal_year, fiscal_quarter)` ×3 | stocks/models.py:492,607,765 |
| stocks 시그널 | `(stock, signal_date, signal_tag)` EODSignal | stocks/models.py:1087 |
| users | `(user, stock)`, `(user, name)`, `(watchlist, stock)`, `(user, interest_type, value)` | users/models.py:90,201,242,291 |
| metrics | `(industry, fiscal_year, metric_code)`, `(symbol, fiscal_year, metric_code, preset_key)` | metrics/benchmark.py:109,173 |
| chain_sight | `(symbol_a, symbol_b)`, `(symbol_a, symbol_b, period)`, `(symbol_a, symbol_b, relation_type)`, `(source, source_id)`, `(symbol, event_type)` | relation_discovery.py:25,54,158 / news_event.py:79 / event_reaction.py:55 |
| portfolio | UniqueConstraint 4개 (run+stock+metric, run+priority 등) | portfolio/models.py:460,552,612,735 |
| market_pulse | `(date)`, `(date, model_version)`, `(date, universe)`, `(date, market_index)` | regime/briefing/snapshot |

> **방향성 관계 유의점**: `RelationConfidence`의 `(symbol_a, symbol_b)` 유니크는 무방향 관계(PEER_OF 등)의 경우 `normalize_pair`(symbol_a < symbol_b)로 정렬 후 저장하도록 코드에서 보장(neo4j_sync.py:18). **DB 제약만으로는 (A,B)와 (B,A) 중복을 못 막으나** 애플리케이션 레벨 정규화로 방어 — 코드 경로를 우회한 직접 INSERT 시 중복 가능(🟢 낮은 위험).

### 🟡 update_or_create race condition 가능성

`update_or_create` 사용처 **57개 파일 / get_or_create 포함 127건**. Django의 `update_or_create`는 내부적으로 `select_for_update` 없이 동작(get→없으면 create), **동시 호출 시 race window** 존재:

- **방어된 경우**: unique_together가 있으면 동시 create는 `IntegrityError`로 차단됨(데이터 중복은 방지). 위 표대로 대부분 키 테이블은 유니크 보유 → **중복 row 위험은 낮음**.
- **잔존 위험**:
  1. **lost update**: 두 트랜잭션이 같은 row를 동시에 update_or_create → 한쪽 defaults가 덮어써짐(특히 누적 카운터/집계 필드). 시계열 baking(eod_json_baker, sp500_eod_service)·동기화 태스크(stock_sync_service, data_sync)에서 발생 가능.
  2. **유니크 미보유 + update_or_create**: lookup 키에 unique 제약이 없으면 중복 row 생성 가능. 점검 필요 대상: `serverless/services/*`(theme_matching, supply_chain, regulatory, patent_network), `validation/services/*`. 이들 lookup 키가 모두 unique_together로 보호되는지 개별 확인 권장.
- **락 사용 현황**: `select_for_update`는 단 **3개 파일**(users/views.py, rag_analysis/views.py, sec_pipeline/tasks.py)에서만 사용. `transaction.atomic`은 28개 파일. → **update_or_create 사용처(57) 대비 명시적 동시성 제어 적용률이 낮음**.

**권고**:
1. 누적/카운터성 필드를 update_or_create로 갱신하는 곳은 `F()` 표현식 또는 `select_for_update` + atomic으로 전환.
2. unique 제약 없는 lookup의 update_or_create는 **반드시 해당 키에 UniqueConstraint 추가** (race 시 IntegrityError로 안전 차단).
3. Celery 동기화 태스크의 update_or_create는 `@transaction.atomic` 래핑 + IntegrityError 재시도(get으로 폴백) 패턴 표준화.

---

## 부록: 검증 메타데이터

- **분석 대상 모델 파일**: stocks, users, portfolio, rag_analysis, serverless, news, sec_pipeline, graph_analysis(dormant) + chain_sight(11), thesis(6), macro(3), metrics(3), market_pulse(6), validation(7)
- **SET_NULL 총 17곳** (지시서 명시 3파일은 7곳으로 일치)
- **CASCADE 총 87곳** (지시서 명시 7파일 외 다수)
- **최장 CASCADE 깊이**: 4단계 (Stock→RawDocumentStore→BusinessModelSnapshot→BusinessModelEvidence)
- **neo4j_dirty 모델**: 3개 (CompanyChainProfile, RelationConfidence, SupplyChainEvidence)
- **update_or_create/get_or_create**: 127건 / 57파일
- **본 감사는 정적 코드 분석이며, 실제 DB 상태(orphan row 수, Neo4j 노드 수)는 미측정.** 위 권고의 backfill/reconciliation 잡이 그 측정 수단이 됨.
