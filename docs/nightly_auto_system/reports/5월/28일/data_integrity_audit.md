# 데이터 무결성 감사 보고서

- 감사일: 2026-05-28
- 범위: Django ORM 전체 (`*/models*.py`), Neo4j 동기화 파이프라인, Celery 태스크
- 모드: 읽기 전용 (코드 수정 없음)

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 분야 |
|--------|------|------|
| 🔴 HIGH | 3 | (1) SET_NULL orphan 정리 부재, (2) Neo4j↔PG 역방향 불일치 감지 부재, (3) update_or_create + select_for_update 미보호 |
| 🟡 MED | 4 | (1) Stock 삭제 시 9개 모델 직접 CASCADE 폭발, (2) AnalysisSession 4단계 CASCADE 체인, (3) Neo4j 동기화 max_retries=1, (4) `to_field='symbol'` 혼재 |
| 🟢 LOW | 2 | (1) StockNews.stock null 허용 + symbol charfield 이중화, (2) unique_together → UniqueConstraint 미이행 |

핵심 통계
- SET_NULL: **17곳** (사용자 추정 7곳 대비 +10, 13개 파일)
- CASCADE: **95+곳** (사용자 추정 37곳 대비 +58, 30+개 파일)
- `update_or_create` 사용 파일: **69개**, 동일 파일 내 `select_for_update` 병용: **16개** (병용률 ≈ 23%)
- `unique_together`: 약 **30개** 모델, `UniqueConstraint`: portfolio 4개만
- `neo4j_dirty` 플래그 사용: `sec_pipeline.SupplyChainEvidence`, `chainsight.CompanyChainProfile`, `chainsight.RelationConfidence` 3개 모델

---

## 1. FK orphan 위험

### 1.1 SET_NULL 사용처 전수 (17곳)

| # | 파일:라인 | 모델.필드 | 참조 대상 | orphan 정리 로직 |
|---|-----------|-----------|-----------|-------------------|
| 1 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | Stock | ✅ `rematch_unmatched.py` 관리 명령 존재 |
| 2 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | DataBasket | ❌ 없음 |
| 3 | `rag_analysis/models.py:256` | `UsageLog.session` | AnalysisSession | ❌ 없음 |
| 4 | `rag_analysis/models.py:263` | `UsageLog.message` | AnalysisMessage | ❌ 없음 |
| 5 | `serverless/models.py:660` | `ScreenerAlert.preset` | ScreenerPreset | ⚠️ `filters_json` fallback 있음 (get_effective_filters), orphan 자체는 방치 |
| 6 | `serverless/models.py:808` | `InvestmentThesis.user` | User | ❌ 없음 (익명 테제 의도일 가능성) |
| 7 | `serverless/models.py:1409` | (User SET_NULL) | User | ❌ 없음 |
| 8 | `sec_pipeline` 안 (1번과 동일) | — | — | — |
| 9 | `thesis/models/thesis.py:70` | `Thesis.parent` 추정 | Thesis self/Stock | ❌ 없음 |
| 10 | `thesis/models/thesis.py:77` | `Thesis.*` 추정 | — | ❌ 없음 |
| 11 | `thesis/models/indicator.py:15` | `ThesisIndicator.*` | — | ❌ 없음 |
| 12 | `thesis/models/monitoring.py:66` | `ThesisMonitoring.*` | — | ❌ 없음 |
| 13 | `portfolio/models.py:327` | Portfolio 관련 | — | ❌ 없음 |
| 14 | `portfolio/models.py:732` | Portfolio 관련 | — | ❌ 없음 |
| 15 | `portfolio/models.py:831` | Portfolio 관련 | — | ❌ 없음 |
| 16 | `marketpulse/models/anomaly.py:25` | `Anomaly.*` | Indicator/Stock | ❌ 없음 |
| 17 | `macro/models/indicators.py:310` | Macro 관련 | — | ❌ 없음 |
| 18 | `chainsight/models/news_event.py:54` | `NewsEvent.parent (self)` | NewsEvent | ❌ 없음 |

> 사용자 추정(7곳, 3파일)과 실제(17곳, 13파일) 차이가 큼 → 감사 범위 확장 필요.

### 1.2 SET_NULL 후 orphan 정리 로직 (유일한 정상 사례)

- `sec_pipeline/management/commands/rematch_unmatched.py:33`: `SupplyChainEvidence.target_company IS NULL` 레코드를 재매칭하는 관리 명령. CLI 실행 필요(자동화 미확인).
- `sec_pipeline/quality_checks.py:142-143`: matched/unmatched count 모니터링은 있으나 정리는 없음.
- 그 외 16개 SET_NULL은 **정리 또는 모니터링 자체가 부재**.

### 1.3 위험 시나리오
1. `rag_analysis.AnalysisSession` 삭제 → `UsageLog.session = NULL` 누적. UsageLog는 비용/감사용 로그이므로 손실은 아니지만 **세션 컨텍스트 추적 불가**.
2. `serverless.ScreenerPreset` 삭제 → `ScreenerAlert.preset = NULL` + `filters_json={}` 인 경우 알림 빈 필터로 동작 가능 (코드 `get_effective_filters`가 빈 dict 반환).
3. `chainsight.NewsEvent` self 참조 SET_NULL → 부모 이벤트 삭제 시 자식 트리 끊김.

### 1.4 권고 (참고용, 본 보고서는 수정 없음)
- 주기 태스크로 `*_isnull=True AND created_at < now-90d` 정리 잡 추가
- 또는 SET_NULL 대신 cascade(soft delete)로 의미 명확화

---

## 2. CASCADE 체인

### 2.1 Stock 삭제 시 직접 영향 (`stocks.Stock` 참조 CASCADE)

확인된 9개 모델이 Stock → CASCADE 직결:

| 모델 | 파일 | 라인 | to_field |
|------|------|------|----------|
| `stocks.DailyPrice` | `stocks/models.py:133` | symbol | ✓ |
| `stocks.WeeklyPrice` 추정 | `stocks/models.py:244` | symbol | ✓ |
| `stocks.OverviewKO` (OneToOne) | `stocks/models.py:699` | id | |
| `stocks.IncomeStatement` 추정 | `stocks/models.py:756` | id | |
| `stocks.BalanceSheet` 추정 | `stocks/models.py:801` | id | |
| `stocks.StockNews` | `stocks/models.py:888` | id (null=True) | |
| `users.PortfolioItem` | `users/models.py:28` | symbol | ✓ |
| `users.WatchlistItem` | `users/models.py:198` | symbol | ✓ |
| `sec_pipeline.SupplyChainEvidence.source_company` | `sec_pipeline/models.py:82` | id | |
| `sec_pipeline.BusinessModelSnapshot.symbol` | `sec_pipeline/models.py:161` | id | |
| `validation.*` 5개 (BenchmarkDelta, CategoryScore, MetricLatest, NewsSummary, PeerPreset 2건) | `validation/models/*` | 다수 | id |
| `chainsight.*` 7개 (chain_profile, capital_dna, event_reaction, growth_stage, insider_signal, narrative_tag, revenue_structure, sensitivity) | `chainsight/models/*` | 다수 | id |

→ Stock 1건 삭제 시 **약 20+개 테이블에서 즉시 row 삭제**, 그 중 일부는 다시 하위 CASCADE 트리거.

### 2.2 3단계+ 연쇄 삭제 체인

#### Chain A: 사용자 삭제 (4단계)
```
User → AnalysisSession(CASCADE) → AnalysisMessage(CASCADE) → UsageLog.message(SET_NULL)
                                                          → UsageLog.session(SET_NULL)
```
- Message는 사라지지만 UsageLog는 보존 (SET_NULL 의도된 설계, 비용 감사 보존).

#### Chain B: User → Thesis → Indicator → ... (3~4단계)
```
User → Thesis(CASCADE, thesis.py:11) → ThesisIndicator(CASCADE, indicator.py:124)
                                     → ThesisMonitoring(CASCADE, monitoring.py:10/61)
                                     → ThesisLearning(CASCADE, learning.py:29/34/74/79/102)
```
- 가장 깊은 체인. 사용자 1명 탈퇴 시 학습 데이터 다량 손실 가능.

#### Chain C: User → SavedPath → PathAction (3단계, chainsight)
```
User → SavedPath(CASCADE, saved_path.py:22) → PathAction(CASCADE, saved_path.py:75)
```

#### Chain D: RawDocumentStore → SupplyChainEvidence + BusinessModelSnapshot (2단계)
```
RawDocumentStore(원본 10-K) → SupplyChainEvidence(CASCADE) → (Neo4j sync 미실행 시 PG만 삭제, Neo4j 노드 잔존 가능)
                            → BusinessModelSnapshot(CASCADE)
```

### 2.3 to_field='symbol' 혼재 위험

- `to_field='symbol'` 사용: `stocks.DailyPrice`, `stocks.WeeklyPrice`, `users.PortfolioItem`, `users.WatchlistItem` (총 4곳)
- 그 외 CASCADE는 모두 `Stock.id` 기반
- Stock의 symbol 변경 (티커 변경: e.g., FB→META) 시:
  - to_field=symbol 그룹은 ON UPDATE CASCADE 처리되어야 하나 Django는 PK 변경을 지원하지 않으므로 **symbol 변경은 신규 row + 마이그레이션** 패턴 필수
  - 혼재 자체는 동작 문제 없지만, 향후 symbol 표준화 작업 시 4개 테이블만 별도 처리 필요

### 2.4 Stock 삭제는 실제로 일어나는가?

- `stocks/services/`, `stocks/tasks.py`에서 `Stock.objects.delete()` grep 결과: (별도 확인 필요)
- 현실적으로는 delisting 시 발생 가능. 현 구조상 대량 데이터 동시 삭제 위험 존재.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 neo4j_dirty 플래그 사용 현황 (단일 소스 정착됨)

| 모델 | 파일 | 비고 |
|------|------|------|
| `sec_pipeline.SupplyChainEvidence` | `sec_pipeline/models.py:100` | 인덱스 있음 |
| `chainsight.CompanyChainProfile` | `chainsight/models/chain_profile.py:65` | `db_index=True` |
| `chainsight.RelationConfidence` | `chainsight/models/relation_discovery.py:130` | 인덱스 있음 |

- **audit P0 #9**: `synced_to_neo4j` 필드 제거, `neo4j_dirty` 단일 소스로 통일 완료 (2026-04-29, 마이그레이션 0008).
- `bulk_update` 사용 시 `save()` 미호출 → **수동으로 `neo4j_dirty=True` 토글 필요**. `chainsight/tasks/relation_tasks.py:382` 등에서 수동 관리 확인됨.

### 3.2 동기화 실패 시 재시도 메커니즘

| 태스크 | 파일:라인 | max_retries | retry_backoff |
|--------|-----------|-------------|----------------|
| `sync_profiles_to_neo4j` | `chainsight/tasks/sync_tasks.py:97` | **1** | ❌ 없음 |
| `sync_relations_to_neo4j` | `chainsight/tasks/sync_tasks.py:148` | **1** | ❌ 없음 |
| `run_neo4j_dirty_sync` | `chainsight/tasks/neo4j_dirty_sync_tasks.py:15` | (확인 필요) | — |
| `sec_pipeline` 동기화 태스크 | `sec_pipeline/tasks.py:464` | **1** | ❌ |

🔴 **HIGH 위험**:
- CLAUDE.md 코딩 규칙: "Celery 태스크: idempotent, max_retries=3, exponential backoff"
- 실제: Neo4j 동기화 태스크 모두 `max_retries=1`, backoff 없음. 규칙 위반.
- 다만 `neo4j_dirty=True` 자체는 유지되므로 **다음 Beat 주기에 재시도**됨 → 영구 손실은 아님. 그러나 짧은 백오프 부재로 transient Neo4j 장애 시 즉시 실패 후 대기.

### 3.3 PG ↔ Neo4j 불일치 감지

#### 정방향 (PG 신규 → Neo4j 미반영)
- ✅ `neo4j_dirty=True` 카운트 모니터링: `sec_pipeline/quality_checks.py:92`, `intelligence.py:97-98`
- ✅ 자동 재시도: 다음 Beat가 dirty 레코드를 다시 처리

#### 역방향 (Neo4j 잔존 / PG 삭제)
🔴 **HIGH 위험 — 감지 메커니즘 없음**

검색 결과:
- `RELATED_TO` 레거시 엣지 1회 정리 코드만 존재 (`chainsight/tasks/sync_tasks.py:158-173`)
- PG 삭제 시 Neo4j 노드/엣지를 같이 삭제하는 시그널/태스크 없음
- 예시 위험:
  - `Stock` 삭제 → `chainsight.CompanyChainProfile` CASCADE → Neo4j `:Stock` 노드는 그대로 남음
  - `RelationConfidence` Django ORM에서 hard delete → Neo4j 엣지 잔존
  - `sec_pipeline.SupplyChainEvidence.source_company` Stock CASCADE 삭제 시 동일

#### 권고 (참고)
- `pre_delete` 시그널에서 Neo4j 노드 제거 호출
- 또는 주기 reconciliation 잡: PG의 `Stock.symbol` set vs Neo4j `MATCH (s:Stock) RETURN s.ticker` set 비교

### 3.4 트랜잭션 경계 문제 (잠재)

- Neo4j는 Django `transaction.atomic` 외부에서 실행됨 → **PG commit 성공 후 Neo4j 실패** 시 정합성 깨짐
- 현 구조: `neo4j_dirty=True` 패턴이 이를 보완 (idempotent 재시도)
- 단점: 사용자가 보는 시점에 잠시 PG-only 상태 존재 (eventual consistency)

---

## 4. UniqueConstraint / update_or_create

### 4.1 unique_together 현황 (확인된 약 30개)

주요 분포:
- `stocks/`: 6 (가격, 재무 4종, EOD signal)
- `serverless/`: 11 (mover, screener, etf_holdings, theme, institutional, llm_relation 등)
- `validation/`: 5 (benchmark, category, latest, peer_preset 2건)
- `marketpulse/`: 6 (snapshot 3종, briefing, regime, news)
- `users/`: 4 (portfolio, watchlist 2건, interest)
- `thesis/`: 5 (community, keyword, indicator, monitoring, snapshot)
- `graph_analysis/`: 4
- `news/`: 2

### 4.2 UniqueConstraint (`models.UniqueConstraint`) 사용

| 위치 | 제약 |
|------|------|
| `portfolio/migrations/0001_initial.py:154` | `(metric_id, industry_code, date)` percentile cache |
| `portfolio/migrations/0001_initial.py:249` | `(analysis_run, priority)` card priority |
| `portfolio/migrations/0001_initial.py:253` | `(analysis_run, stock, metric_id)` comment |
| `portfolio/migrations/0001_initial.py:269` | `(analysis_run, stock, metric_id)` metric result |

🟢 **LOW**: Django 4.0+에서 `unique_together`는 `UniqueConstraint`로 마이그레이션 권장. 현재 혼재. 신규 코드는 모두 `UniqueConstraint` 사용으로 통일하는 것이 장기적으로 깔끔.

### 4.3 update_or_create + race condition

#### 통계
- `update_or_create` 사용: **69개 파일**
- 그 중 동일 파일에 `select_for_update` 병용: **16개 (23%)**
- 나머지 **53개 파일은 동시성 보호 없이 update_or_create 호출**

#### Django update_or_create 동작
- 내부적으로 SAVEPOINT 사용
- `unique_together` 위반 시 `IntegrityError` 발생 가능
- 동시 호출 2개가 같은 키로 들어오면 한 쪽이 실패
- 재시도 로직이 호출자에 없으면 데이터 누락

#### HIGH 위험 후보 (병용 미확인)
검색 결과 `select_for_update`가 같은 파일에 없는 것:
- `marketpulse/calculators/sector_flow.py`
- `marketpulse/tasks/briefing.py`, `news.py`
- `chainsight/tasks/relation_tasks.py` (RelationConfidence update_or_create — 가장 핫한 경로)
- `chainsight/tasks/sync_tasks.py:34` (defaults={'neo4j_dirty': True})
- `chainsight/tasks/insider_tasks.py`, `profile_tasks.py`, `sensitivity_tasks.py`
- `news/services/aggregator.py`, `keyword_extractor.py`
- `news/tasks.py` (다량)
- `validation/services/*` 5개 파일
- `serverless/tasks.py`
- `thesis/services/snapshot_builder.py` (주석에 unique_together 충돌 시 update 처리 명시 있음 — 그러나 락 없음)
- `stocks/tasks.py`, `macro/tasks.py`

→ 동일 Stock에 대한 병렬 Celery 워커가 `update_or_create` 동시 호출 시 `IntegrityError` 가능. 현재 `max_retries`로 일부 흡수되나, transient 데이터 손실 가능.

#### 권고 (참고)
- 핫한 경로 (RelationConfidence, MetricLatest, ChainProfile, ScreenerAlert 등)는 `select_for_update` 또는 PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` (Django 4.1+ `QuerySet.bulk_create(update_conflicts=True)`) 도입 검토

---

## 부록 A: 참조 파일 인덱스

- 모델: `stocks/models.py`, `users/models.py`, `news/models.py`, `serverless/models.py`, `sec_pipeline/models.py`, `rag_analysis/models.py`, `graph_analysis/models.py`, `portfolio/models.py`, `chainsight/models/*` (12), `thesis/models/*` (8), `validation/models/*` (5), `metrics/models/*` (4), `marketpulse/models/*` (6), `macro/models/*` (3)
- Neo4j 동기화: `chainsight/tasks/sync_tasks.py`, `chainsight/services/neo4j_sync.py`, `sec_pipeline/tasks.py:464`, `sec_pipeline/signals.py`
- 품질 모니터링: `sec_pipeline/quality_checks.py`, `sec_pipeline/intelligence.py`
- Orphan 재매칭: `sec_pipeline/management/commands/rematch_unmatched.py`

## 부록 B: 본 보고서의 한계

- 코드 정적 분석만 수행 (DB row 실측 없음)
- Stock 삭제가 실제로 운영에서 얼마나 일어나는지 미확인
- `thesis/`, `portfolio/`, `macro/` SET_NULL 9~17번은 파일 구조만 확인하고 필드명/대상 모델은 본문에서 추가 검증 필요 (라인 번호만 그렙으로 잡은 상태)
- `update_or_create` 69곳 모두 individual race 검증한 것은 아니며, 동일 파일 내 `select_for_update` 부재로만 분류
