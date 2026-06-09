# 데이터 무결성 감사 보고서

> 생성일: 2026-06-09 | 범위: PostgreSQL 모델 무결성 + Neo4j 동기화 일관성
> 방식: 읽기 전용 정적 분석 (코드 수정 없음)
> 대상: `packages/shared/`, `apps/`, `services/`, `macro/`, `thesis/` 전 모델

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 2 | serverless 공급망 Neo4j 미가용 시 `is_synced_to_graph=True` 오마킹 / PG↔Neo4j 양방향 드리프트 감지기 부재 |
| 🟡 Medium | 4 | `MATCH`-only Cypher 사일런트 no-op / SET_NULL 후 denormalized 필드 정합 로직 부재 / `update_or_create` race (unique 미보강 케이스) / TTL sweep 단일 큐 의존 |
| 🟢 Low / 양호 | 6 | SET_NULL 보존 설계 의도적 / chain_sight `neo4j_dirty` 자가복구 / TTL cleanup 존재 / CASCADE 체인 최대 3단 (순환 없음) / unique 제약 충실 / PROTECT 7곳 적절 |

**감사 범위 정정 (사전 파악 vs 실측)**
- 지시서 기준 `SET_NULL 7곳 / CASCADE 37곳`이었으나, **서비스 리모델링**(진행 중)으로 디렉토리가 `packages/shared/`·`apps/`·`services/`로 재편되어 실측은 **SET_NULL 17곳 / CASCADE 95곳 / PROTECT 7곳 / DO_NOTHING 0곳**.
- 지시서가 지목한 3개 SET_NULL 파일(`sec_pipeline`, `serverless`, `rag_analysis`)은 모두 실재하며 본 보고서에서 전수 검토. 추가로 `thesis/`, `macro/`, `apps/chain_sight/`, `apps/portfolio/`, `apps/market_pulse/` SET_NULL도 포함.

---

## 1. FK orphan 위험 (SET_NULL)

### 1.1 SET_NULL 전수 분류 (17곳)

| 파일 / 라인 | 필드 | 삭제 시 동작 | 설계 의도 | 판정 |
|------------|------|-------------|----------|------|
| `services/sec_pipeline/models.py:94` | `SupplyChainEvidence.target_company` | Stock 삭제 → FK null | `target_company_name`(CharField) 별도 보존 | 🟡 denormalized 정합 필요 |
| `services/serverless/models.py:660` | `ScreenerAlert.preset` | Preset 삭제 → null, `filters_json`로 폴백 | 커스텀 필터 전환 의도 | 🟢 의도적 |
| `services/serverless/models.py:797` | `InvestmentThesis.user` | User 삭제 → 공개 테제 보존 | `is_public` 테제 유지 | 🟢 의도적 |
| `services/serverless/models.py:1353` | `AdminActionLog.user` | User 삭제 → 감사 로그 보존 | 감사 추적 유지 | 🟢 의도적 |
| `services/rag_analysis/models.py:132` | `AnalysisSession.basket` | Basket 삭제 → 세션 이력 보존 | 탐험 경로 유지 | 🟢 의도적 |
| `services/rag_analysis/models.py:232` | `TokenUsageLog.session` | 세션 삭제 → 과금 로그 보존 | 비용 집계 유지 | 🟢 의도적 |
| `services/rag_analysis/models.py:239` | `TokenUsageLog.message` | 메시지 삭제 → 과금 로그 보존 | 비용 집계 유지 | 🟢 의도적 |
| `macro/models/indicators.py:310` 외 6곳 | thesis/macro/chain_sight/portfolio/market_pulse | 참조 대상 삭제 → null | 스냅샷/이력 보존 | 🟢 의도적 |

### 1.2 SET_NULL 후 orphan 정리 로직 존재 여부

**결론: 전용 orphan cleanup 로직은 존재하지 않으며, 대부분 설계상 불필요하다.**

- 코드베이스 전체에서 `orphan`/`cleanup_orphan`/`delete_orphan` 키워드는 `services/news/services/news_neo4j_sync.py`(Neo4j TTL 정리, PG와 무관)에만 존재.
- SET_NULL 대상 대다수는 **"부모는 사라져도 자식 레코드는 이력/감사 목적으로 살아남는다"**는 의도적 보존 패턴 → null FK 자체가 정상 종착 상태이므로 별도 정리 불요.

**🟡 단 한 가지 예외 — `SupplyChainEvidence.target_company` (sec_pipeline:94)**
```python
target_company = models.ForeignKey("stocks.Stock", on_delete=models.SET_NULL, null=True, ...)
target_company_name = models.CharField(max_length=200)  # denormalized 백업
```
- Stock 삭제 시 `target_company`는 null이 되지만 `target_company_name`(문자열)은 남는다 → **"이름은 있으나 FK는 끊긴" 반(半)고아 레코드** 발생.
- 이 종목이 나중에 **재등록**되어도 자동 재연결(rebind) 로직이 없어, `target_company`는 영구 null로 남고 Neo4j 동기화 시 타깃 노드 매칭이 이름 기반으로만 가능해진다.
- **권고**: (a) 종목 재등록 시 `target_company_name` 일치 건을 재바인딩하는 backfill, 또는 (b) 본 필드를 의도된 동작으로 명문화. 현재는 암묵적.

---

## 2. CASCADE 체인 분석

### 2.1 CASCADE 사용 현황 (95곳)

가장 밀집된 도메인: `apps/portfolio`(13) > `apps/chain_sight`(10+) > `services/_dormant/graph_analysis`(8, **휴면**) > `services/validation`(7) > `services/sec_pipeline`(6) > `thesis`(9 across 4 files).

> ⚠️ `services/_dormant/graph_analysis/models.py`의 CASCADE 8곳은 **휴면 모듈**(API 미구현, CLAUDE.md 보류 항목). 마이그레이션이 적용돼 있다면 테이블은 존재하므로 삭제 영향은 실재. 활성 코드 경로 없음.

### 2.2 Stock 삭제 시 영향 범위 (최다 FK 참조 허브)

`Stock`(PK=`symbol`)은 직접 CASCADE FK 8건의 직접 부모이며, 도메인 전반의 종착 허브다.

**Stock 삭제 직접 CASCADE 대상 (1단계):**
- `packages/shared/stocks/models.py`: DailyPrice(194), 재무제표 류(306), StockOverviewKO(946, PK=Stock), 1015·1063·1153 등 5건
- `packages/shared/users/models.py`: Portfolio(47), WatchlistItem(223) 2건
- `services/sec_pipeline/models.py`: RawDocumentStore(26, `sec_filings`), SupplyChainEvidence.source_company(88)

**2단계 연쇄 (대표 체인):**
```
Stock 삭제
 └─CASCADE→ RawDocumentStore (sec_filings)
     └─CASCADE→ SupplyChainEvidence.source_document (sec_pipeline:83)
         └─ source_company 또한 Stock CASCADE (동일 Stock이면 1단계에서 이미 삭제)
         └─ target_company 는 SET_NULL (위 1.2 참조)
```
```
User 삭제
 └─CASCADE→ DataBasket (rag:14)
     └─CASCADE→ BasketItem (rag:73)               [3단계]
 └─CASCADE→ AnalysisSession (rag:129)
     └─CASCADE→ AnalysisMessage (rag:178)
         └─ TokenUsageLog.message 는 SET_NULL (보존)  [체인 차단점]
 └─CASCADE→ ScreenerAlert (serverless:648)
     └─CASCADE→ ScreenerAlertHistory (serverless:747)   [3단계]
```

**최대 깊이: 3단계.** 순환 CASCADE 없음. DO_NOTHING 부재 → DB 레벨 무결성은 Django ORM이 일괄 보장.

### 2.3 평가

- **🟢 양호**: 가장 위험한 User/Stock 연쇄도 3단계에서 종료되고, 과금·감사·이력 성격 자식은 SET_NULL로 체인을 끊어 데이터 손실을 막는 설계가 일관적.
- **🟡 주의**: Stock 삭제는 8개 직접 자식 + sec_pipeline 2단계까지 대량 삭제를 유발. 운영상 **Stock은 물리 삭제 대신 `is_active` soft-delete 권장** (현재 soft-delete 플래그 확인 안 됨 — `Stock` 모델에 비활성 플래그 부재 시 실수 삭제가 곧 대량 CASCADE).
- **PROTECT 7곳**(metrics/chain_sight/portfolio/market_pulse)은 스냅샷 기준 데이터의 실수 삭제를 막는 적절한 방어선.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 `neo4j_dirty` 플래그 현황

| 모듈 | 모델 | 패턴 | 평가 |
|------|------|------|------|
| `apps/chain_sight` | `CompanyChainProfile`(chain_profile.py:84), `RelationConfidence`(relation_discovery.py:148) | `neo4j_dirty=True` 단일 소스 (audit P0 #9에서 `synced_to_neo4j` 폐기, 의미 반전) | 🟢 모범 |
| `services/sec_pipeline` | `SupplyChainEvidence`(models.py:112) | `neo4j_dirty=True` 기본값 + `neo4j_synced_at` | 🟢 일관 |
| `services/serverless` | `LLMExtractedRelation`(models.py:1231) | `is_synced_to_graph` (역방향 의미: True=완료) | 🔴 동기화 누락 위험 (3.3) |

**db_index**: chain_sight 양 모델 모두 `neo4j_dirty`에 인덱스 부여 → dirty 스윕 쿼리 효율적. ✅

### 3.2 동기화 실패 시 재시도 메커니즘

**🟢 chain_sight — 자가복구 설계 (모범 사례)**
- `sync_profiles_to_neo4j`(sync_tasks.py:108): 레코드별 `try/except`. **성공한 레코드만** `neo4j_dirty=False`로 전환(161행). 실패 시 dirty=True 유지 → 다음 Beat 주기에 자동 재시도.
- `bulk_update`/`queryset.update()`는 `save()` 미호출 → `neo4j_dirty=True`를 **수동 토글**(relation_tasks.py:421/428/435, relation_discovery.py:179)로 정확히 보정. P0 #9 회고 반영 확인.
- Celery: `run_neo4j_dirty_sync`(max_retries=2, delay=60s), `sync_*_to_neo4j`(max_retries=1).
- News 파이프라인 태스크: max_retries=2, exponential-ish backoff(5~10분), `self.retry(exc=exc)` 명시. ✅

### 3.3 🔴 PG↔Neo4j 불일치 발생 지점 (High)

**① serverless 공급망 — Neo4j 미가용 시 오마킹 (`services/serverless/tasks.py:1497-1499`)**
```python
if neo4j.is_available():
    neo4j.create_relationship(...)      # Neo4j 다운이면 SKIP
# ↓ if 블록 "밖" — Neo4j 미작성이어도 무조건 실행
rel.is_synced_to_graph = True
rel.save(update_fields=["is_synced_to_graph"])
```
- Neo4j가 다운된 상태에서 태스크가 돌면 PG `StockRelationship`만 기록되고 Neo4j 엣지는 누락되지만 `is_synced_to_graph=True`로 박제 → **영구 PG-only 고아**. dirty 재시도 대상에서 빠진다(필터가 `is_synced_to_graph=False`이므로).
- chain_sight의 자가복구 패턴(성공 시에만 dirty=False)과 **정반대 안티패턴**.
- **권고**: `is_synced_to_graph=True` 전환을 `if neo4j.is_available()` 블록 **안**으로 이동, 또는 Neo4j 미작성 시 `False` 유지.

**② `MATCH`-only Cypher의 사일런트 no-op (🟡 Medium, sync_tasks.py:157)**
```python
repo.run_query("MATCH (s:Stock {ticker: $ticker}) SET s += $props", ...)
```
- 대상 `:Stock {ticker}` 노드가 Neo4j에 없으면 `MATCH`가 0건 매칭 → `SET`은 no-op이지만 **예외는 안 난다** → `neo4j_dirty=False`로 "성공" 마킹.
- PG에 프로파일이 있어도 Neo4j Stock 노드가 미생성 상태면 속성 동기화가 조용히 누락. `MERGE` 대신 `MATCH`를 쓰는 의도(노드 생성은 별도 시드 책임)는 합리적이나, **시드 누락 시 감지 불가**.
- **권고**: `SET` 후 영향 행수 검증, 또는 시드-동기화 순서 보장(troubleshoot_neo4j_sync_pipeline 메모의 `seed_neo4j_graph` 선행 규칙과 연동).

### 3.4 🔴 양방향 드리프트 감지 메커니즘 부재 (High)

- **PG→Neo4j**: `neo4j_dirty=True` 큐로 단방향 push만 존재.
- **Neo4j→PG (역방향)**: PG에서 레코드가 삭제(CASCADE)되었을 때 대응되는 Neo4j 노드/엣지를 제거하는 로직이 **없다**.
  - 예: Stock 삭제 → PG의 `SupplyChainEvidence`·`RelationConfidence` CASCADE/SET_NULL 처리됨. 그러나 Neo4j의 해당 `:Stock` 노드와 엣지는 **그대로 잔존** → Neo4j-only 고아 누적.
  - 유일한 Neo4j 정리 경로는 **TTL 만료**(news 관계 한정, 3.5) — 구조적 노드/엣지에는 적용 안 됨.
- **불일치 감지 수단**: 정합성 대조(reconciliation) 명령/태스크가 없어, "PG엔 있고 Neo4j엔 없음(또는 반대)"을 능동 탐지할 방법이 부재. 현재는 사후 수동 복구(메모 `troubleshoot_neo4j_sync_pipeline`)에 의존.
- **권고**: 야간 reconciliation 태스크 — ① `count(:Stock)` vs `Stock.objects.count()` 대조 ② dirty=False인데 Neo4j 미존재 노드 리스트업 ③ PG 부재 Neo4j 노드 리스트업. 리포트만 해도 드리프트 가시화.

### 3.5 TTL 기반 Neo4j 정리 (🟢 존재 / 🟡 단일 큐 의존)

- `NewsNeo4jSyncService.cleanup_expired_relationships`(news_neo4j_sync.py:674): `expires_at < datetime()` 관계 `DELETE`. Beat 등록됨(`config/celery.py:378` → `neo4j` 큐).
- `cleanup_expired_semantic_cache`(rag_analysis, neo4j 큐) 동반.
- 🟡 두 정리 태스크 모두 `neo4j` 큐 전용 워커(`--pool=solo`)에 의존 → 해당 워커 미가동 시 만료 관계가 무한 누적. 워커 헬스 모니터링 필요(메모 nightly triage의 좀비 Beat 사례와 동일 위험군).

---

## 4. Unique 제약조건

### 4.1 `unique_together` / `UniqueConstraint` 현황

**UniqueConstraint (4곳, 모두 `apps/portfolio/models.py`)** — 복합 멱등 키:
| 라인 | 제약 | 보호 대상 |
|------|------|----------|
| 460 | `(analysis_run, stock, metric_id)` | 분석 실행별 종목·지표 결과 중복 차단 |
| 552 | `(analysis_run, priority)` | 카드 우선순위 충돌 차단 |
| 612 | `(analysis_run, stock, metric_id)` | 코멘트 중복 차단 |
| 735 | `(metric_id, industry_code, date)` | 퍼센타일 캐시 중복 차단 |

**unique_together (주요)**: macro indicators/relationships(date·indicator 복합 4건), metrics benchmark/snapshot(`symbol·fiscal_year·metric_code` 등 3건), stocks DailyPrice(`stock·date`:246), news, sec_pipeline(`alias·context_sector` — country 미포함, 테스트로 명시 검증됨).

**단일 unique 필드**: `Stock.symbol`(PK), `accession_no`(sec), `share_code`(InvestmentThesis), 각종 `date`/`url` 등 — 자연키 충실히 보호.

**🟢 평가**: 멱등성이 중요한 배치 산출물(분석 결과/벤치마크/캐시)에 복합 unique가 일관 적용되어 있고, `update_or_create`의 lookup 키와 정합. sec_pipeline의 `country` 미포함 의도가 테스트로 박제됨(설계 명확).

### 4.2 `update_or_create` race condition 가능성 (🟡 Medium)

- 전체 **100곳**에서 사용(get_or_create 27곳 별도). 대부분 **단일 워커 배치**(Celery Beat, `--pool=solo` 또는 순차 태스크) 컨텍스트라 동시성이 낮음.
- Django `update_or_create`는 원자적이지 않다(SELECT→없으면 CREATE). **동일 lookup 키로 두 워커가 동시 진입** 시 IntegrityError 또는 마지막-쓰기-승리 가능.
- **방어 현황**:
  - ✅ portfolio/metrics/serverless 등 산출물 테이블은 **lookup 키 = UniqueConstraint/unique_together**로 보강되어 있어, race 시 IntegrityError로 안전 실패(중복 row는 못 만든다).
  - 🟡 **위험 케이스**: lookup 필드 조합에 DB unique 제약이 없는 `update_or_create` 호출. 예 — `LLMExtractedRelation`/`StockRelationship` 동기화(serverless/tasks.py:1473)는 `(source_symbol, target_symbol, relationship_type)` lookup이나 `StockRelationship` 측 복합 unique 제약 명시가 모델에서 확인되지 않음 → 동시 실행 시 중복 관계 row 생성 가능.
- **권고**: ① 모든 `update_or_create` lookup 키 조합에 대응하는 DB unique 제약 1:1 보장(특히 그래프 관계 테이블) ② 고동시성 경로는 `select_for_update()` 또는 unique 제약 + `IntegrityError` 재시도로 감쌀 것.

---

## 부록: 우선순위 권고 요약

| 우선순위 | 항목 | 위치 | 조치 |
|---------|------|------|------|
| P0 | serverless `is_synced_to_graph=True` 오마킹 | serverless/tasks.py:1497 | True 전환을 `if neo4j.is_available()` 안으로 이동 |
| P0 | PG↔Neo4j reconciliation 태스크 신설 | 신규 | 야간 카운트 대조 + 고아 리포트 |
| P1 | `MATCH`-only no-op 감지 | sync_tasks.py:157 | 영향 행수 검증 / 시드 선행 보장 |
| P1 | 그래프 관계 `update_or_create` unique 보강 | StockRelationship 등 | 복합 unique 제약 추가 |
| P2 | sec_pipeline `target_company` 재바인딩 | sec_pipeline/models.py:94 | 종목 재등록 시 backfill 또는 동작 명문화 |
| P2 | Stock soft-delete 도입 검토 | stocks/models.py | 물리 삭제→대량 CASCADE 방지 |
| P2 | neo4j 큐 워커 헬스 모니터링 | infra | TTL/dirty 정리 무한 적체 방지 |

---

*본 보고서는 정적 코드 분석 기반이며, 실제 DB 상태(orphan row 수, Neo4j 노드 카운트)는 측정하지 않았다. P0 reconciliation 태스크 도입 후 실측 수치로 후속 검증 권장.*
