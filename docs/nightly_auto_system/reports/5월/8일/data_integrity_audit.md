# 데이터 무결성 감사 보고서

**감사 일자**: 2026-05-08
**감사 범위**: PostgreSQL 모델 무결성 + Neo4j 동기화 + Unique 제약 + Race Condition
**모드**: 읽기 전용 (코드 수정 없음)
**감사자**: Claude (Auto Mode)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 주요 이슈 |
|-------|------|----------|
| 🔴 **HIGH** | 4 | (1) Stock CASCADE blast radius 30+ 테이블, (2) Neo4j 재시도 max_retries=1, (3) PG↔Neo4j 양방향 불일치 감지 부재, (4) PG orphan 정리 코드 전무 |
| 🟠 **MEDIUM** | 6 | (5) SET_NULL 후 NULL 레코드 정리 누락, (6) RawDocumentStore CASCADE 3단 연쇄, (7) update_or_create transaction.atomic 누락, (8) 사용자 instructions에 명시된 SET_NULL/CASCADE 카운트와 실제 코드 불일치, (9) StockNews.stock null=True인데 symbol 필드 중복, (10) NewsArticle/SentimentHistory/StockKeyword/EODSignal 등 PG↔ 외부소스 검증 없음 |
| 🟡 **LOW** | 5 | (11) UniqueConstraint vs unique_together 혼용, (12) preset_key 마이그레이션 시 동일 그룹 중복 가능성, (13) Stock.symbol primary_key + to_field='symbol' 일관성, (14) BasketItem clean()에서 race condition, (15) AnalysisMessage/UsageLog 4단계 SET_NULL 체인 |

**핵심 결론**:
- **사용자 사전 파악 카운트와 실제 코드 불일치** — SET_NULL은 7곳이 아니라 **17곳 (11개 파일)**, CASCADE는 37곳이 아니라 **80+곳 (25+개 파일)**. 코드베이스가 portfolio/thesis/macro/marketpulse/validation/metrics/chainsight 앱 추가로 크게 확장됨.
- Stock 모델이 시스템의 **single point of failure** — 30+ 테이블이 CASCADE로 종속, Stock 삭제 시 막대한 데이터 손실 위험.
- Neo4j 동기화는 `neo4j_dirty` 단일 소스로 통일됐으나(audit P0 #9), **재시도 정책이 빈약**(max_retries=1) + **양방향 검증 부재**.

---

## 1. FK orphan 위험

### 1.1 SET_NULL 사용처 — 실제 17곳 (11개 파일)

> ⚠️ 사용자 instructions에는 "7곳, 3개 파일"로 명시됐으나 실제 grep 결과는 다음과 같다.

| # | 파일:라인 | 모델.필드 | 부모 모델 | NULL 발생 시점 |
|---|----------|----------|---------|--------------|
| 1 | rag_analysis/models.py:145 | `AnalysisSession.basket` | DataBasket | basket 삭제 → session.basket=NULL |
| 2 | rag_analysis/models.py:256 | `UsageLog.session` | AnalysisSession | session 삭제 시 |
| 3 | rag_analysis/models.py:263 | `UsageLog.message` | AnalysisMessage | message CASCADE 삭제 시 (체인 충돌!) |
| 4 | serverless/models.py:660 | `ScreenerAlert.preset` | ScreenerPreset | 프리셋 삭제 → alert는 custom 필터로 fallback |
| 5 | serverless/models.py:808 | `InvestmentThesis.user` | User | 사용자 탈퇴 시 thesis는 익명 보존 |
| 6 | serverless/models.py:1409 | `AdminActionLog.user` | User | **감사 추적 보존** 의도. 적절. |
| 7 | sec_pipeline/models.py:86 | `SupplyChainEvidence.target_company` | Stock | Ticker 매칭 실패 → NULL 유지 (정상 흐름) |
| 8 | chainsight/models/news_event.py:54 | self FK | self | 부모 이벤트 삭제 시 |
| 9 | macro/models/indicators.py:298 | (Industry sensitivity) | Indicator | 지표 삭제 시 |
| 10 | portfolio/models.py:327 | (PortfolioStock) | - | - |
| 11 | portfolio/models.py:732 | (Coach 관련) | - | - |
| 12 | portfolio/models.py:831 | (Coach 관련) | - | - |
| 13 | thesis/models/monitoring.py:66 | (Thesis snapshot) | - | - |
| 14 | thesis/models/indicator.py:15 | (Indicator data) | - | - |
| 15 | thesis/models/thesis.py:70 | (Thesis 관련) | - | - |
| 16 | thesis/models/thesis.py:77 | (Thesis 관련) | - | - |
| 17 | marketpulse/models/anomaly.py:25 | (Anomaly) | - | - |

### 1.2 SET_NULL 후 orphan 레코드 정리 로직

**🔴 결론: PostgreSQL orphan 정리 management command 또는 Celery 태스크 부재.**

검색 결과 (`orphan|cleanup_orphan|delete_orphan|management/commands.*orphan`):
- **PostgreSQL**: 정리 코드 0건. 모든 17개 SET_NULL 위치는 NULL 레코드를 영구 보존하는 정책.
- **Neo4j**: `news/services/news_neo4j_sync.py:700-711` 1건만 존재 (NewsEvent orphan 노드 삭제).

**구체적 위험 시나리오**:

1. `SupplyChainEvidence.target_company=NULL` 누적 → `quality_checks.py`는 이를 별도 카운트하지만, ETL 결과 매칭 실패율이 누적됨에도 일괄 정리 정책 없음. 시간이 지나면 `target_company__isnull=True`가 dataset의 30%+를 점유할 수 있음.
2. `AnalysisSession.basket=NULL` → 사용자가 basket 삭제 시 session은 살아남지만, exploration_path/messages는 부모 컨텍스트 없이 고립. 분석 세션 복원 불가.
3. `UsageLog.session=NULL` + `UsageLog.message=NULL` → 비용 추적 데이터는 보존되지만 어떤 세션의 비용인지 추적 불가능 (감사용으로는 문제없음, **회계 감사용으로는 문제**).

**권장 후속 작업** (감사 범위 외, 참고용):
- `SupplyChainEvidence`: `created_at` 기준 90일 이상 + `target_company__isnull=True` + `UnmatchedCompanyQueue.status='not_public'` 조건으로 archival/삭제 정책 정의.
- `AnalysisSession`: `basket__isnull=True` AND `updated_at < now-180d` 조건으로 정리.

---

## 2. CASCADE 체인 분석

### 2.1 CASCADE 사용처 — 실제 80+곳 (25+개 파일)

> ⚠️ 사용자 instructions에는 "37곳, 7개 파일"로 명시됐으나 실제는 portfolio(12곳), thesis(11곳), validation(7곳), metrics(5곳), chainsight(8곳), macro(5곳), marketpulse(2곳) 등이 추가되어 **두 배 이상**.

### 2.2 Stock 삭제 시 영향 범위 (🔴 시스템의 SPOF)

**Stock에 직접 CASCADE되는 모델 (30+ 테이블)**:

```
Stock (symbol PK)
├── stocks/
│   ├── DailyPrice (CASCADE, to_field=symbol)
│   ├── WeeklyPrice (CASCADE, to_field=symbol)
│   ├── BalanceSheet (CASCADE, to_field=symbol)
│   ├── IncomeStatement (CASCADE, to_field=symbol)
│   ├── CashFlowStatement (CASCADE, to_field=symbol)
│   ├── StockOverviewKo (OneToOne CASCADE, primary_key)
│   ├── EODSignal (CASCADE)
│   ├── SignalAccuracy (CASCADE)
│   └── StockNews (CASCADE, null=True)
├── users/
│   ├── Portfolio (CASCADE, to_field=symbol)
│   └── WatchlistItem (CASCADE, to_field=symbol)
├── chainsight/
│   ├── CompanyChainProfile (CASCADE)
│   ├── CompanyNarrativeTag (CASCADE)
│   ├── CompanySensitivityProfile (CASCADE)
│   ├── CompanyGrowthStage (CASCADE)
│   ├── CompanyEventReaction (CASCADE)
│   ├── CompanyCapitalDNA (CASCADE)
│   ├── CompanyRevenueStructure (CASCADE)
│   └── CompanyInsiderSignal (CASCADE)
├── sec_pipeline/
│   ├── RawDocumentStore (CASCADE) ← 2단계 fan-out
│   │   ├── SupplyChainEvidence (CASCADE on source_document)
│   │   └── BusinessModelSnapshot (CASCADE) ← 3단계
│   │       └── BusinessModelEvidence (CASCADE)
│   ├── SupplyChainEvidence.source_company (CASCADE)
│   └── BusinessModelSnapshot.symbol (CASCADE)
└── validation/
    ├── PeerListCache (CASCADE)
    ├── ValidationNewsSummary (CASCADE)
    ├── CompanyMetricLatest (CASCADE) ← MetricDefinition도 CASCADE
    ├── CategorySignal (CASCADE)
    └── CompanyBenchmarkDelta (CASCADE)
```

### 2.3 3단계 이상 연쇄 삭제 영향 추적

**CASCADE 체인 1: User 삭제 흐름 (4단계)**
```
User (CASCADE)
  └─→ AnalysisSession (CASCADE) ← rag_analysis
        └─→ AnalysisMessage (CASCADE)
              └─→ UsageLog (SET_NULL on message_id)  ← FK 정책 충돌!
```
**🟡 LOW 위험**: User CASCADE → AnalysisSession CASCADE → AnalysisMessage CASCADE 까지는 의도대로 삭제되지만, UsageLog는 message가 CASCADE로 사라진 직후 SET_NULL 처리되려 함. Django는 이 케이스를 처리하지만, 비용 추적 데이터의 메시지 연결이 끊김.

**CASCADE 체인 2: Stock → SEC 파이프라인 (3단계 fan-out)**
```
Stock (CASCADE)
  └─→ RawDocumentStore (CASCADE)
        ├─→ SupplyChainEvidence (CASCADE on source_document)
        └─→ BusinessModelSnapshot (CASCADE)
              └─→ BusinessModelEvidence (CASCADE)
```
**🟠 MEDIUM 위험**: Stock 1개 삭제 시 → 해당 종목의 모든 10-K 원문 + 추출 결과 + Track A/B 증거가 일괄 소실. 재수집은 외부 SEC EDGAR API 의존이라 시간/비용 부담.

**CASCADE 체인 3: User → Watchlist → Item (3단계)**
```
User (CASCADE)
  └─→ Watchlist (CASCADE, related_name=watchlists)
        └─→ WatchlistItem (CASCADE, related_name=items)
```
**🟡 LOW 위험**: 의도된 동작. unique_together 보호 있음.

**CASCADE 체인 4: User → DataBasket → BasketItem (3단계)**
```
User (CASCADE)
  └─→ DataBasket (CASCADE, related_name=baskets)
        └─→ BasketItem (CASCADE, related_name=items)
```
- 추가로 `AnalysisSession.basket=SET_NULL`이라 basket 삭제는 session 보존, BasketItem만 CASCADE.

**CASCADE 체인 5: ScreenerPreset → Alert → History (3단계 with SET_NULL 분기)**
```
User (CASCADE) ─┬─→ ScreenerPreset (CASCADE)
                 │     └── ScreenerAlert.preset (SET_NULL)  ← 프리셋만 끊고 alert 보존
                 └─→ ScreenerAlert (CASCADE on user)
                       └─→ AlertHistory (CASCADE)
```
**🟡 LOW 위험**: 의도된 분기 처리. preset 삭제 시 alert는 custom 필터로 fallback (`get_effective_filters()`).

### 2.4 Stock 삭제 차단 권장사항 (감사 의견)

**현재 상태**: Stock은 production 환경에서 직접 삭제될 수 있는 안전장치가 없음. 30+ 테이블이 CASCADE로 종속되어 있어, 단 하나의 실수로 종목 1개의 모든 가격/재무/뉴스/시그널/관계/SEC/검증 데이터가 사라짐.

**권장사항**(감사 범위 외):
- Stock 모델에 `is_active` (Soft delete) 패턴 도입 검토.
- 또는 admin / DB level에서 Stock DELETE 권한 회수, `is_active=False`만 허용.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 neo4j_dirty 플래그 사용 현황

**audit P0 #9 (2026-04-29)**: `synced_to_neo4j` (의미: 동기화 완료) 필드를 폐기하고 `neo4j_dirty` (의미: 동기화 필요) **단일 소스**로 통일. Migration `chainsight/0008_unify_neo4j_flags.py`에서 의미 반전 처리 완료.

**현재 사용 위치**:

| 모델 | 파일:라인 | default | 인덱스 | 정책 |
|------|----------|---------|-------|-----|
| `chainsight.CompanyChainProfile` | chain_profile.py:65 | True | `db_index=True` | OneToOne(symbol). update_or_create의 save()가 자동 토글 |
| `chainsight.RelationConfidence` | relation_discovery.py:130 | True | `Index(fields=['neo4j_dirty'])` | save()에서 자동 True 세팅 (line 158) |
| `sec_pipeline.SupplyChainEvidence` | models.py:100 | True | `Index(fields=['neo4j_dirty'])` | ticker_matcher가 신규 매칭 시 True 토글 |

**테스트 커버리지**:
- `tests/unit/sec_pipeline/test_models.py:72` `assert evidence.neo4j_dirty is True`
- `tests/unit/sec_pipeline/test_quality_checks.py:135` 상태 검증

### 3.2 동기화 실패 시 재시도 메커니즘

**🔴 HIGH 위험: 재시도 정책이 빈약**

| 태스크 | 파일:라인 | max_retries | retry_backoff | soft_time_limit |
|-------|----------|-------------|---------------|----------------|
| `aggregate_chain_profiles` | chainsight/tasks/sync_tasks.py:14 | **1** | 없음 | 3600s |
| `sync_profiles_to_neo4j` | chainsight/tasks/sync_tasks.py:97 | **1** | 없음 | 1800s |
| `sync_relations_to_neo4j` | chainsight/tasks/sync_tasks.py:148 | **1** | 없음 | 1800s |
| `sync_dirty_to_neo4j` (SEC) | sec_pipeline/tasks.py:337 | **1** | 없음 | 300s |
| `seed_relations_to_chainsight` | sec_pipeline/tasks.py:281 | **1** | 없음 | 미설정 |

**CLAUDE.md 코딩 규칙 위반**:
> "Celery 태스크: idempotent, max_retries=3, exponential backoff"

모든 Neo4j 동기화 태스크가 `max_retries=1`이며 exponential backoff 없음. Neo4j 일시 장애 시 다음 Celery Beat 주기까지 대기 (보통 1시간+).

**개별 row 실패 처리는 양호한 편**:
- `sec_pipeline/tasks.py:437-438`: row 단위 try/except, 성공한 ID만 `synced_pks` 누적 후 PG 업데이트
- `chainsight/services/neo4j_sync.py:42-43`: 동일 패턴
- `select_for_update(skip_locked=True)` (sec_pipeline/tasks.py:367) — 동시 실행 시 row lock 충돌 방지 (양호)

**dirty flag 자동 재시도 흐름**:
- 실패 row는 `neo4j_dirty=True` 유지 → 다음 batch 주기에 자동 재시도 (✅ 의도된 idempotency)
- 단, 영구 실패 (예: Neo4j 스키마 미스매치) 시 무한 재시도 지옥 가능. dead-letter 정책 없음.

### 3.3 PG ↔ Neo4j 불일치 감지

**🔴 HIGH 위험: 양방향 검증 도구 부재**

**현존하는 검증 (한 방향만)**:
- `sec_pipeline/quality_checks.py:92-146`: PG 측에서 `neo4j_dirty=False` (동기화됨) vs `neo4j_dirty=True, target_company__isnull=False` (동기화 대기) 카운트만 비교.
- `sec_pipeline/intelligence.py:97-98`: `sync_synced` / `sync_pending` 메트릭 노출.

**부재한 검증**:
- ❌ Neo4j에 존재하지만 PG에 없는 엣지/노드 감지 코드 없음.
- ❌ PG `neo4j_dirty=False`이지만 실제 Neo4j에 엣지가 없는 경우 감지 코드 없음 (예: Neo4j 데이터 손실 후 PG 플래그 stale).
- ❌ `chainsight/services/neo4j_sync.py:53` "synced_pks" 추적은 동기화 시점만 보장, **향후 Neo4j 외부 삭제는 감지 불가**.

**실제 발생할 수 있는 시나리오**:
1. Neo4j 인스턴스 데이터 유실 → PG `neo4j_dirty=False` 그대로 → 누락된 데이터 영구히 미동기화.
2. Neo4j에서 admin이 수동 삭제 → PG와 영구 불일치.
3. `sync_dirty_to_neo4j` Phase B 성공 후 Phase C 실패 (예: PG transaction 끊김) → 중복 엣지 가능 (Phase B가 DELETE+CREATE 패턴이라 idempotent하긴 함).

**권장 후속 작업** (감사 범위 외):
- 주 1회 `validate_neo4j_pg_consistency` 태스크 추가:
  - Neo4j MATCH (a)-[r]->(b) WHERE r.source='sec_10k' RETURN count(r)
  - vs `SupplyChainEvidence.objects.filter(neo4j_dirty=False, target_company__isnull=False).count()`
  - 불일치 임계값 초과 시 Slack/email 알림.

### 3.4 레거시 정리 패턴 (양호한 사례 1건)

`chainsight/tasks/sync_tasks.py:158-173`의 `RELATED_TO` 1회 정리:
- `cache.set('chainsight:related_to_cleanup_v1', True, timeout=86400*365)` 1년 캐시 키로 idempotency.
- 기존 레코드 dirty 리셋 후 dynamic type으로 재생성.
- ✅ **사후 마이그레이션 패턴**으로 좋은 사례.

---

## 4. UniqueConstraint / update_or_create 현황

### 4.1 unique_together / UniqueConstraint 설정 현황

**unique_together** 사용 (40+곳 확인). 주요 패턴:

| 모델 | 키 | 비고 |
|------|----|----|
| `DailyPrice`, `WeeklyPrice`, `EODSignal`, `SignalAccuracy` | `(stock, date)` 또는 `(stock, signal_date, signal_tag)` | 시계열 표준 |
| `BalanceSheet`, `IncomeStatement`, `CashFlowStatement` | `(stock, period_type, fiscal_year, fiscal_quarter)` | 재무제표 표준 |
| `Portfolio`, `WatchlistItem`, `UserInterest` | `(user, stock)` 등 | 사용자 데이터 |
| `MarketMover` | `(date, mover_type, symbol)` | 일별 랭킹 |
| `CorporateAction` | `(symbol, date, action_type)` | 같은 날 분할+배당 동시 가능 |
| `LLMExtractedRelation` | `(source_symbol, target_symbol, relation_type, source_id)` | 출처별 중복 허용 |
| `RelationConfidence` (chainsight) | `(symbol_a, symbol_b, relation_type)` | symbol_a < symbol_b 정규화 |
| `ETFHolding` | `(etf, stock_symbol, snapshot_date)` | 일별 holdings |
| `ThemeMatch` | `(stock_symbol, theme_id)` | 테마는 stock당 unique |
| `InstitutionalHolding` | `(institution_cik, stock_symbol, report_date)` | 13F 분기별 |
| `CompanyAlias` (sec) | `(alias, context_sector)` | context_country는 의도적으로 미포함 (line 287 주석) |

**UniqueConstraint** 신식 사용 (portfolio 5곳, validation 일부):
- `portfolio/models.py:439, 525, 583, 701` — `models.UniqueConstraint(fields=..., name=...)`
- 차이점: name 명시 가능, condition (partial unique) 지원.

**🟡 LOW 위험: 혼용 일관성**
- 동일 프로젝트 내 `unique_together` (legacy) vs `UniqueConstraint` (Django 2.2+) 혼용.
- `unique_together`는 Django 5.x에서 deprecated 예정. portfolio만 신식 사용. 추후 통일 검토 필요.

**🟡 LOW 위험: PeerMetricBenchmark unique key 변경**
- `metrics/migrations/0006_alter_peermetricbenchmark_unique_together_and_more.py`
- 이전: `(symbol, fiscal_year, metric_code)`
- 이후: `(symbol, fiscal_year, metric_code, preset_key)`
- 마이그레이션 시 기존 레코드의 `preset_key=NULL` 상태에서 중복 발생 가능성 검토 필요. 마이그레이션 0006이 어떻게 처리했는지는 추가 확인 필요.

### 4.2 update_or_create / get_or_create 사용 시 race condition

**전체 사용 현황**: 83개 파일에서 사용. 주요 hot path:

| 파일:라인 | 모델 | unique key 보호 | transaction.atomic | 위험도 |
|----------|------|--------------|------------------|-------|
| chainsight/tasks/sync_tasks.py:84 | CompanyChainProfile | OneToOne(symbol) | ❌ | 🟡 LOW (단일 워커 가정) |
| sec_pipeline/tasks.py:314 | RelationConfidence | unique_together(3개) | ❌ | 🟠 MEDIUM (병렬 워커 시 IntegrityError 가능) |
| sec_pipeline/ticker_matcher.py:106 | UnmatchedCompanyQueue | raw_company_name only | ❌ | 🟠 MEDIUM (raw_company_name unique 제약 없음) |
| sec_pipeline/signals.py:62 | CompanyAlias | unique_together(alias, context_sector) | ❌ | 🟡 LOW (signal 핸들러는 단일 트랜잭션 안) |
| chainsight/tasks/relation_tasks.py:291 | RelationConfidence | unique_together | ❌ | 🟠 MEDIUM |
| thesis/services/snapshot_builder.py:27 | (snapshot) | unique_together(thesis, asof_date) | 확인 필요 | - |

**🟠 MEDIUM 위험: `transaction.atomic()` 누락**

Django 공식 문서: `update_or_create`는 race condition 시 IntegrityError를 던질 수 있음. 권장 패턴:
```python
with transaction.atomic():
    obj, created = Model.objects.update_or_create(...)
```

`transaction.atomic` 사용처는 29개 파일에서 확인됨. 그러나 `update_or_create` 호출 직접 감싸는 패턴은 일부에 그침.

특히 위험한 케이스:
1. **`UnmatchedCompanyQueue` (ticker_matcher.py:106)**: `raw_company_name`에 unique 제약이 없으므로, 동시에 같은 회사명을 처리하는 두 LLM 추출 작업이 충돌하면 `get_or_create`가 false-create 후 다음 라인의 `occurrence_count += 1` 손실 가능. 두 워커 동시 +1 → 결과 +1 (lost update). `select_for_update` 미사용.
2. **`RelationConfidence` (sec_pipeline/tasks.py:314)**: SEC 파이프라인이 병렬 워커로 실행될 때 같은 (symbol_a, symbol_b, relation_type) 조합이 동시 도달하면 IntegrityError. max_retries=1이라 재시도 후 실패 시 영구 누락.

### 4.3 BasketItem.clean() Race Condition

**🟡 LOW 위험: rag_analysis/models.py:116-127**

```python
def clean(self):
    if self.basket_id and not self.pk:  # 새 아이템
        if not self.basket.can_add_item():  # items.count() < 15
            raise ValidationError(...)
```

- `can_add_item()` 호출 → `save()` 호출 사이에 다른 워커가 동시에 추가하면 16개 이상 가능 (TOCTOU 패턴).
- `MAX_ITEMS=15` 제약이 unique_together로 강제되지 않으므로 race condition 시 위반 가능.
- 영향 범위: 사용자가 동시에 두 탭에서 추가해도 발생.

---

## 부록 A: 확인된 양호한 패턴

1. **`select_for_update(skip_locked=True)` (sec_pipeline/tasks.py:367)** — Neo4j sync에서 동시 실행 보호.
2. **`neo4j_dirty` 단일 소스 통일 (audit P0 #9)** — 의미 충돌 제거 + migration으로 의미 반전 처리.
3. **2-Phase pattern (sec_pipeline/tasks.py:362-445)** — PG lock → Neo4j → PG update의 분리.
4. **DELETE + CREATE pattern (사용자 instructions에 명시된 ⚠️)** — Neo4j MERGE 금지로 dynamic type 일관성 확보.
5. **레거시 1회 정리 with cache 키 (chainsight/tasks/sync_tasks.py:158)** — 마이그레이션 idempotency.

## 부록 B: 데이터 손실 위험 시나리오 정리

| 시나리오 | 영향 | 방어 수준 |
|---------|------|----------|
| Stock.delete() 1회 호출 | 30+ 테이블 데이터 일괄 손실 | ❌ 무방어 |
| Neo4j 인스턴스 재생성 | PG `neo4j_dirty=False`인 데이터 영구 미동기화 | ❌ 양방향 검증 부재 |
| Celery 워커 동시 실행 | update_or_create IntegrityError + max_retries=1 후 영구 실패 | 🟡 부분 (skip_locked 일부, atomic 부족) |
| User.delete() | 4단계 cascade (Session→Message→UsageLog SET_NULL) | 🟢 양호 (의도됨) |
| Migration 롤백 | reverse_code 일부만 정의 | 🟡 부분 (chainsight 0008은 reverse_code 정의됨) |

---

**감사 완료**: 2026-05-08
**다음 권장 감사**: 1주일 후, Stock soft-delete 도입 여부 + Neo4j 양방향 검증 태스크 도입 여부 점검.
