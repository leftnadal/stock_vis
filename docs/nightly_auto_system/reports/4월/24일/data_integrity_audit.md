# 데이터 무결성 감사 보고서

- **감사 일자**: 2026-04-24
- **대상**: /Users/byeongjinjeong/Desktop/stock_vis (브랜치: portfolio)
- **범위**: FK orphan · CASCADE 체인 · Neo4j 동기화 · Unique 제약
- **형식**: 읽기 전용 감사 (코드 수정 없음)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 주요 내용 |
|--------|------|-----------|
| 🔴 High | 3 | check_stale_and_decay에서 `neo4j_dirty` 미설정, 이중 플래그(`neo4j_dirty` + `neo4j_synced`) 동기화 분열, update_or_create race condition 방어 부재 |
| 🟠 Medium | 4 | Neo4j 역방향 불일치(orphan edge) 감지 수단 없음, NewsArticle은 동기화 플래그 자체 부재(ID 집합 대조로 우회), SET_NULL 후 orphan 정리 잡 없음, CompanyAlias unique_together에 country 제외로 의도 충돌 여지 |
| 🟡 Low | 4 | UniqueConstraint 대신 구버전 `unique_together` 전면 사용, Thesis→Indicator→Reading 3단 CASCADE 영향 미검토, docs/portfolio/implementation/models.py는 실제 앱 아님(감사 제외 필요), 기본 auto id FK에 DB-level ON DELETE 외 보호막 없음 |

> 사전 파악 수치는 사용자 제공치(SET_NULL 7, CASCADE 37)보다 실제 소스 전체에서 더 많이 검색됨:
> SET_NULL 13건(주 앱 모델 기준), CASCADE 80건+ (docs/portfolio 제외 ≈ 61건). 아래 본문은 **실제 주 앱 파일만** 대상으로 분석한다.
> (`docs/portfolio/implementation/models.py`는 설계 시안 스켈레톤이며 Django 앱에 등록되지 않음 — 감사 대상에서 제외.)

---

## FK orphan 위험

### SET_NULL 위치 (주 앱 13곳)

| # | 파일:라인 | 모델.필드 | 참조 타입 | Orphan 정리 로직 |
|---|-----------|-----------|-----------|------------------|
| 1 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | Stock | ❌ 없음 — 심볼 삭제 시 10-K 근거만 남고 target 불명 |
| 2 | `serverless/models.py:660` | `ScreenerAlert.preset` | ScreenerPreset | ⚠️ 프리셋 삭제 시 커스텀 필터(`filters_json`)로 폴백 설계(730: `get_effective_filters`) — 정리 불필요 |
| 3 | `serverless/models.py:808` | `InvestmentThesis.user` | User | ❌ 없음 — 탈퇴자 테제가 고아로 누적 |
| 4 | `serverless/models.py:1409` | `AdminActionLog.user` | User | ✅ 감사 로그는 의도적 보존 — 정상 |
| 5 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | DataBasket | ❌ 바구니 삭제 시 세션 유지되나 `basket=None` 세션의 데이터 근거 소실 |
| 6 | `rag_analysis/models.py:256` | `UsageLog.session` | AnalysisSession | ✅ 비용/토큰 추적 보존 목적 — 정상 |
| 7 | `rag_analysis/models.py:263` | `UsageLog.message` | AnalysisMessage | ✅ 동일 — 정상 |
| 8 | `chainsight/models/news_event.py:54` | `ChainNewsEvent.duplicate_of` | self | ✅ 중복 원본 삭제돼도 파생 이벤트 보존 — 정상 |
| 9 | `thesis/models/thesis.py:70` | `Thesis.source_news` | NewsArticle | ❌ 뉴스 기사 삭제(30일 TTL) 시 진입 근거 추적 불가 |
| 10 | `thesis/models/thesis.py:77` | `Thesis.copied_from` | self | ✅ 원본 테제 삭제돼도 복사본 유지 — 정상 |
| 11 | `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | ThesisPremise | ❌ 전제 삭제 시 지표가 근거 없이 관측만 지속 |
| 12 | `thesis/models/monitoring.py:66` | `ThesisAlert.indicator` | ThesisIndicator | ✅ 지표 제거해도 과거 알림 이력 보존 — 정상 |
| 13 | `macro/models/indicators.py:282` | `EconomicEvent.related_indicator` | EconomicIndicator | ❌ 지표 체계 리팩토링 시 이벤트가 고립 |

### Orphan 정리 잡(cleanup job) 존재 여부

- ❌ **`target_company__isnull=True` 대상 정리 Celery task 부재** (`sec_pipeline`)
  - 있는 것: `SupplyChainEvidence.target_company__isnull=True` **카운트 집계만** (`quality_checks.py:143`, `intelligence.py:98`)
  - 의도: TickerMatcher가 언젠가 매칭되기를 기다리는 구조라 orphan 허용은 설계 의도 (docs/sec_pipeline 참조). 단, 영영 매칭되지 않는 row에 대한 정책(삭제/보류 전환) 미정의.
- ❌ `InvestmentThesis.user=None`, `Thesis.source_news=None`, `ThesisIndicator.premise=None` 고아 레코드를 주기적으로 처리하는 잡이나 API 필터가 발견되지 않음.
- ⚠️ **감지 도구만 존재**: `sec_pipeline/quality_checks.py:90-97`은 `neo4j_dirty + target_company__isnull=False` 50건 초과 시 경고만 남기고, 실제 orphan은 모니터링 사각지대.

---

## CASCADE 체인

### 주요 체인 구조 (주 앱 기준 ≈ 61곳)

#### Stock (`stocks.Stock`) — 삭제 시 최대 영향 범위

Stock은 symbol PK + 다수의 ForeignKey 타깃. 삭제 시 다음이 **모두 즉시 삭제됨**:

| 참조 소스 | 파일:라인 | 비고 |
|-----------|-----------|------|
| DailyPrice, WeeklyPrice | `stocks/models.py:133, 244` | `to_field='symbol'` |
| StockOverviewKo | `stocks/models.py:699` | OneToOne |
| EODSignal, SignalAccuracy | `stocks/models.py:756, 801` | |
| StockNews | `stocks/models.py:888` | `null=True` 허용 |
| Portfolio, WatchlistItem | `users/models.py:28, 198` | `to_field='symbol'` |
| favorite_stock M2M | `users/models.py:17` | through 자동 삭제 |
| RawDocumentStore, SupplyChainEvidence(source), BusinessModelSnapshot | `sec_pipeline/models.py:25, 82, 161` | |
| CompanyChainProfile | `chainsight/models/chain_profile.py:12` | OneToOne PK |
| 7개 chainsight 스냅샷 (growth/capital/sensitivity/revenue/narrative/insider/event) | `chainsight/models/*.py` | 모두 CASCADE |
| CorrelationEdge(stock_a, stock_b), PriceCache | `graph_analysis/models.py:77, 84, 291` | |
| validation.* (BenchmarkDelta, CategoryScore, MetricLatest, NewsSummary, PeerPreset members) | `validation/models/*.py` | |

> **영향도**: AAPL 하나 삭제 시 즉시 연쇄 삭제 대상 **20개 이상의 테이블**. 실제 운영에서 Stock 삭제는 금지 정책이 필요.
> Stock PK는 `symbol` (CharField) 이고 `to_field='symbol'` FK가 섞여 있어 대소문자 변경만으로도 FK 깨짐 가능 — 모델 주석 6(`CLAUDE.md`)의 `symbol.upper()` 규칙과 연결됨.

#### User — 탈퇴 시 연쇄 삭제 체인

```
User CASCADE
├─ Portfolio (users)
├─ Watchlist CASCADE
│  ├─ WatchlistItem
│  ├─ CorrelationMatrix
│  ├─ CorrelationEdge
│  │  └─ CorrelationAnomaly      ← 3단계 체인
│  └─ GraphMetadata
├─ UserInterest
├─ ScreenerPreset (serverless)
├─ ScreenerAlert CASCADE
│  └─ AlertHistory                ← 2단계
├─ DataBasket CASCADE
│  └─ BasketItem                  ← 2단계 (+ AnalysisSession.basket SET_NULL)
├─ AnalysisSession CASCADE
│  ├─ AnalysisMessage             ← 3단계 (via UsageLog SET_NULL)
│  └─ usage_logs (SET_NULL 유지)
├─ PeerPreset / UserPeerPreference (validation)
├─ Thesis CASCADE
│  ├─ ThesisPremise
│  ├─ ThesisIndicator CASCADE
│  │  └─ IndicatorReading         ← 3단계 체인
│  └─ ThesisAlert, ThesisComment, ThesisVote ...
├─ SavedPath CASCADE
│  └─ PathAction                  ← 2단계
└─ InvestmentThesis (SET_NULL 유지)
```

- 🔴 **3단계 이상 연쇄 삭제 경로**:
  1. `User → Thesis → ThesisIndicator → IndicatorReading` (장기 관측 이력 통째 소실)
  2. `User → Watchlist → CorrelationEdge → CorrelationAnomaly` (과거 알림 이력 소실)
  3. `User → AnalysisSession → AnalysisMessage`, 추가로 `UsageLog` (세션 FK)는 `SET_NULL`이지만 message FK도 `SET_NULL`이라 비용 집계는 보존 ✅
- ⚠️ `Thesis`와 `Watchlist`의 체인은 **사용자가 수동으로 Thesis를 지울 때도** 발동 — UI 경고 필요.

#### RawDocumentStore (SEC 10-K 원문)

```
RawDocumentStore CASCADE
├─ SupplyChainEvidence
└─ BusinessModelSnapshot CASCADE
   └─ BusinessModelEvidence        ← 3단계
```
- filing 재처리 시 10-K 재파싱으로 기존 근거를 통째 재생성하는 설계(`sec_pipeline/tasks.py:120 update_or_create`)와 연관. 실수로 `doc.delete()` 호출 시 하류 LLM 비용(Track A+B)이 전부 휘발.

### 3단계 이상 CASCADE 종합

| 체인 | 깊이 | 리스크 |
|------|------|--------|
| User → Thesis → Indicator → Reading | 4 | 관측 로그 전량 소실 |
| User → Watchlist → Edge → Anomaly | 4 | 알림 이력 소실 |
| User → Session → Message | 3 | 대화 컨텍스트 소실 (비용 로그는 보존됨) |
| Stock → RawDoc → Snapshot → Evidence | 4 | 10-K 품질 지표 붕괴 |
| ETFProfile → ETFHolding | 2 | snapshot_date 불변성 유지 |

---

## Neo4j 동기화

### 플래그 패턴 혼재 현황

| 앱 | 모델 | 플래그 필드 | save() 자동 dirty | 정상 여부 |
|----|------|-------------|-------------------|-----------|
| sec_pipeline | `SupplyChainEvidence` | `neo4j_dirty` + `neo4j_synced_at` | ❌ (manual in validator_track_a.py:158) | ✅ `models.py:99` 주석에 "synced_to_neo4j 금지, neo4j_dirty만"으로 원칙 명시 |
| chainsight | `RelationConfidence` | `neo4j_dirty` + `synced_to_neo4j` + `neo4j_synced_at` + `score_version` | ✅ (`save()` 자동 `neo4j_dirty=True`) | 🟠 **2개 플래그 공존** — `synced_to_neo4j`는 중복, 원칙 위반 (`CLAUDE.md` DECISIONS: neo4j_dirty 단일화) |
| chainsight | `CompanyChainProfile` | `neo4j_synced` (+ _at) | ❌ manual | 🟠 패턴 불일치 (`neo4j_dirty` 아님) |
| news | `NewsArticle` | **없음** | ❌ | 🟠 `news_neo4j_sync.py:541-542` 주석: "neo4j_synced 필드가 없으므로 Neo4j에 이미 존재하는 article_id를 제외" — Neo4j 쿼리로 매 배치 대조 |

#### 🔴 High: 이중 플래그 동기화 분열 — `chainsight.RelationConfidence`

- `models/relation_discovery.py:130-134` 두 플래그 동시 존재:
  - `synced_to_neo4j` (legacy, default=False)
  - `neo4j_dirty` (default=True, db_index, `save()` 자동 세팅)
- `services/neo4j_sync.py:23`는 **`neo4j_dirty=True`만** 조회 후 동기화하며, 완료 시 `update()`로 두 필드 동시에 갱신:
  ```
  .update(neo4j_dirty=False, synced_to_neo4j=True, neo4j_synced_at=...)
  ```
- 🔴 **그러나 `check_stale_and_decay` (`tasks/relation_tasks.py:389, 396, 403`)은 decay 시**:
  ```python
  stale.update(relation_status='stale', synced_to_neo4j=False)   # ← neo4j_dirty=True 누락
  ```
  → `queryset.update()`는 `save()` 미호출 → `neo4j_dirty=True` 자동 세팅 안 됨 → `sync_dirty_relations`가 이 row를 집지 못함 → **Neo4j 엣지가 confirmed 상태로 남음** (`_delete_edge` 미호출)
- 대조: `tasks/sync_tasks.py:167`은 올바르게 둘 다 세팅: `.update(synced_to_neo4j=False, neo4j_dirty=True)`
- 정책 충돌: `CLAUDE.md` 및 `models.py:99` 주석의 "synced_to_neo4j 필드 금지" 원칙과 실제 구현 불일치.

### 동기화 실패 재시도 메커니즘

| 태스크 | 파일 | max_retries | 재시도 전략 |
|--------|------|-------------|-------------|
| `sync_dirty_to_neo4j` (SEC) | `sec_pipeline/tasks.py:337` | **1** | soft_time_limit=300, 실패 시 raise → Celery 기본 재시도 |
| `sync_profiles_to_neo4j` | `chainsight/tasks/sync_tasks.py:96` | **1** | iterator + 건별 try/except — 개별 실패는 `fail` 카운트만, 다음 호출에서 `neo4j_synced=False`로 재진입 |
| `sync_relations_to_neo4j` | `chainsight/tasks/sync_tasks.py:147` | **1** | `sync_dirty_relations`에 위임, 동일하게 건별 try/except |
| `sync_dirty_relations` | `chainsight/services/neo4j_sync.py:32` | (Celery 래퍼 없음) | 실패한 pk는 `synced_pks`에 추가되지 않아 `neo4j_dirty=True` 유지 → 다음 주기에 자동 재시도 ✅ |

- ✅ **자동 재시도 패턴**: "건별 try/except + dirty 유지" — 정상 작동
- 🔴 **Decay 케이스 결함** (위 High): dirty가 세팅되지 않으므로 영원히 재시도되지 않음
- ⚠️ Celery `max_retries=1`은 일시적 Neo4j 연결 장애에 대해 자체 지수백오프 재시도 기회를 1회로 제한 — 영속적 재시도는 "dirty 유지 + 다음 Beat 주기"에 의존

### PG ↔ Neo4j 불일치 감지 방법

#### PG → Neo4j (one-way detection, 있음)

- `sec_pipeline/quality_checks.py:91-97`: `SupplyChainEvidence.neo4j_dirty=True AND target_company__isnull=False`가 50건 초과 시 경고 로그
- `sec_pipeline/quality_checks.py:144`: dashboard stats에 `neo4j_synced` / `neo4j_pending` 카운트 노출
- `sec_pipeline/intelligence.py:97-98`: `sync_synced / sync_pending` → LLM 품질 리포트의 `sync_score` 입력

#### Neo4j → PG (역방향, 🟠 Medium 부재)

- **PG에 없는데 Neo4j에 있는 엣지(orphan edge)를 감지하는 코드가 전무**
- `sec_pipeline/tasks.py:400-412`는 `source='sec_10k'` edge를 rel_type 6개 리스트(`KNOWN_TYPES`)로 DELETE 시도해 동기화 전 정리하지만, 리스트에 없는 legacy type(예: `chainsight/tasks/sync_tasks.py:163`의 `RELATED_TO` 일회성 정리 외)은 감지 불가
- `news_neo4j_sync.py:564`는 `_get_existing_event_ids()`로 article_id 집합을 읽어 중복 방지 — **정합성이 아닌 스킵 최적화용**
- **대조 쿼리 cron 부재**: Neo4j에만 있는 Stock 노드 · 엣지를 찾아 경보하는 daily 잡 없음

### 기타 동기화 원칙 준수

- ✅ `sec_pipeline/tasks.py:367` `select_for_update(skip_locked=True)` — 동시 실행 안전
- ✅ Phase A/B/C 분리 패턴 — PG 락 → Neo4j 쓰기 → PG 업데이트 (Celery 중복 실행에 강함)
- ✅ `chainsight/tasks/sync_tasks.py:159-168` 일회성 `RELATED_TO` cleanup을 cache 플래그로 멱등 보장

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 (주 앱)

실제 앱에서 **`UniqueConstraint` 미사용**, 전부 구버전 `unique_together` 사용:

| 앱 | 파일 | 개수 | 예시 |
|----|------|------|------|
| stocks | `models.py` | 5 | `(stock, date)`, `(stock, period_type, fiscal_year, fiscal_quarter)` × 3 |
| users | `models.py` | 4 | `(user, stock)`, `(user, name)`, `(watchlist, stock)`, `(user, interest_type, value)` |
| news | `models.py` | 2 | `(news, symbol)`, `(symbol, date)` |
| serverless | `models.py` | 9 | `(symbol, date, action_type)`, `(date, sector)`, `(institution_cik, stock_symbol, report_date)` 등 |
| graph_analysis | `models.py` | 4 | `(watchlist, date)` × 2, `(watchlist, stock_a, stock_b, date)`, `(stock, date)` |
| sec_pipeline | `models.py` | 1 | `(alias, context_sector)` — ⚠️ `context_country` 필드가 모델에는 있으나 unique key에서 **의도적으로 제외** (주석 `models.py:287`) → 동일 alias가 국가 달라도 하나만 허용 |
| thesis | `models/indicator.py` | 1 | `(indicator, asof)` |
| rag_analysis | `models.py` | 1 | `(basket, item_type, reference_id)` |
| chainsight | `models/*` | 다수 | `(symbol_a, symbol_b)`, `(symbol_a, symbol_b, relation_type)`, `(source, source_id)` 등 |

> `docs/portfolio/implementation/models.py`의 7개 `UniqueConstraint`는 실제 앱 아님 (설계 시안).
> `update_or_create`의 matching key로 쓰이는 unique 조합이 많아, 역으로 **unique_together가 깨지면 update_or_create가 IntegrityError 터짐** → race 발생 시 트랜잭션 실패.

### 🔴 High: update_or_create 관련 Race Condition 방어 현황

#### 통계
- `update_or_create` 총 **49개 파일**에서 사용
- `select_for_update` 병행 사용: **17개 파일** (단 대부분 `update_or_create`와 같은 지점에 쓰이지 않음)

#### Race 위험 구간 (unique_together로 IntegrityError 방어는 되나, 동시성 비용 발생)

| 위치 | 모델 | unique key | 트랜잭션 보호 |
|------|------|-----------|-----------|
| `api_request/alphavantage_service.py:81` | Stock | symbol PK | ❌ 없음 — 동일 심볼 동시 갱신 시 last-write-wins |
| `api_request/alphavantage_service.py:235, 266` | DailyPrice/WeeklyPrice | `(stock, date)` | ❌ 없음 |
| `api_request/alphavantage_service.py:289, 318, 347` | 재무제표 3종 | `(stock, period, year, quarter)` | ❌ 없음 |
| `validation/services/preset_generator.py:118~449` | PeerPreset | (preset name 추정) | ❌ 없음 |
| `validation/services/benchmark_calculator.py:83, 238, 272, 330` | PeerListCache, 3개 Benchmark | 복합 key | ❌ 없음 |
| `news/services/aggregator.py:415, 433` | NewsEntity, EntityHighlight | `(news, symbol)` | ❌ 없음 — 동시 수집 시 중복 대기 |
| `chainsight/tasks/relation_tasks.py:275~367` (3 업소트) | RelationConfidence | `(symbol_a, symbol_b, relation_type)` | ❌ 없음 — 동일 Beat가 여러 worker에서 돌면 충돌 |
| `sec_pipeline/tasks.py:314` | RelationConfidence | 동일 | ❌ 없음 |
| `sec_pipeline/tasks.py:120` | RawDocumentStore | accession_no unique | ❌ 없음 |
| `serverless/services/supply_chain_service.py:328` | StockRelationship | unique_together | ❌ 없음 |

#### ✅ 올바르게 처리된 곳
- `sec_pipeline/tasks.py:362-368` `sync_dirty_to_neo4j` — `transaction.atomic()` + `select_for_update(skip_locked=True)` + `BATCH_SIZE=500`. 다른 태스크가 동일 evidence를 잡으면 skip하고 지나감.

#### Race Condition 실제 영향도

- Django `update_or_create`는 **내부적으로 get → create 후 IntegrityError 캐치 → update 재시도** 구조라 unique key만 지키면 **데이터 무결성은 유지**됨.
- 단, 동시 호출 시:
  1. **듀얼 INSERT 경합** → IntegrityError 캐치 비용 (트랜잭션 낭비)
  2. **중간 UPDATE race**: 두 프로세스가 서로 다른 `defaults`를 들고 같은 row를 update하면 **last write wins** (예: `truth_score`가 뒤늦은 값으로 덮임)
  3. `current_score`, `last_triggered_at`, `use_count` 등 카운터 증가 필드는 원자적 `F()` 연산 미사용 시 손실 가능성

### NewsArticle의 동기화 플래그 부재 (🟠 Medium)

- `news_neo4j_sync.py:541-542` 명시적 주석: "neo4j_synced 필드가 없으므로, Neo4j에 이미 존재하는 article_id를 제외합니다"
- `_get_existing_event_ids()`가 매 배치마다 전체 이벤트 ID를 Neo4j에서 pull — **N+ 라운드트립 비용 + Neo4j 크기 증가 시 OOM 위험**
- 기존 동기화 패턴(`neo4j_dirty`)으로 migrate하지 않은 것은 주석만으로 파악되며 `DECISIONS.md` 관련 결정 기록 대조 필요.

---

## 부록: 교차 정책 충돌

1. **`CLAUDE.md` common-bug #21**: "ETF_PEER→ETFHolding, HAS_THEME→ThemeMatch 분기" → `serverless/models.py`의 `ETFHolding`과 `ThemeMatch` 테이블은 legacy 마커(`LEGACY_KEEP_UNTIL_DC2`)가 붙어 있으나 unique_together는 유지됨. DC-2 완료 후 마이그레이션 누락 시 orphan 가능.
2. **CLAUDE.md KB 규칙 "neo4j_dirty 단일화"** vs **실제 `RelationConfidence.synced_to_neo4j` 잔존** → 본 감사의 High-1 이슈와 직결.
3. **CompanyAlias `(alias, context_sector)` unique**: `context_country`는 참고용이라 unique 포함 안 함(`sec_pipeline/models.py:287`) → 다국적 회사명(예: "Samsung")이 여러 국가에서 추출될 때 첫 번째 등록만 승리. 의도인지 버그인지 확인 필요.

---

## 권장 후속 작업 (본 감사는 코드 수정 없음)

- [HIGH-1] `chainsight/tasks/relation_tasks.py:389, 396, 403` decay update에 `neo4j_dirty=True` 추가 (별도 티켓)
- [HIGH-2] `RelationConfidence.synced_to_neo4j` 제거 마이그레이션 또는 `neo4j_dirty`와 통일 (DECISIONS 동기화)
- [HIGH-3] 핫스팟 `update_or_create` (Stock, DailyPrice, RelationConfidence)에 `transaction.atomic() + select_for_update` 패턴 적용 검토
- [MED-1] Neo4j → PG 역방향 orphan edge/node 감지 daily 잡 신설
- [MED-2] `InvestmentThesis.user=None`, `Thesis.source_news=None`, `ThesisIndicator.premise=None` orphan 정리 정책 문서화
- [MED-3] `NewsArticle`에 `neo4j_synced` 추가 또는 대체 전략 DECISIONS 등재
- [LOW-1] `docs/portfolio/implementation/models.py`를 실제 앱에 등록할 예정이면 `UniqueConstraint`가 최신 표준이므로 기존 앱도 마이그레이션 고려
