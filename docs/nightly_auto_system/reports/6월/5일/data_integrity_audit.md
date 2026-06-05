# 데이터 무결성 감사 보고서

> **감사일**: 2026-06-05
> **범위**: FK orphan 위험 · CASCADE 체인 · Neo4j↔PG 동기화 · Unique 제약/upsert race
> **모드**: 읽기 전용 (코드 수정 없음)
> **대상 코드**: `packages/shared/`, `apps/`, `services/`, `macro/`, `thesis/` (마이그레이션 제외)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 2 | ① SET_NULL 후 PG orphan 정리 로직 전무 ② Neo4j 단방향 정합성 — "PG에 없고 Neo4j에만 있는" 좀비 엣지 감지/회수 부재 |
| 🟡 Medium | 4 | ③ `update_or_create` 124곳 중 `transaction.atomic` 미동반 다수 (race 시 IntegrityError 가능) ④ Neo4j 동기화 태스크 retry 정책 불균일(max_retries 1~3 혼재) ⑤ 동기화 실패 row 영구 dirty 적체(self-heal은 되나 dead-letter 없음) ⑥ `relation_discovery` 등 symbol 기반 FK 미설정(CharField) → DB 레벨 무결성 보장 없음 |
| 🟢 Low / 양호 | 5 | CASCADE 체인 최대 3단(예측 가능) · PROTECT 적절 배치(회계성 데이터) · unique_together/UniqueConstraint 광범위 설정 · sec_pipeline 2-Phase + `select_for_update(skip_locked)` 모범 패턴 · quality_checks 적체 알림 존재 |

> **지시서 수치와의 차이**: 지시서는 SET_NULL 7곳·CASCADE 37곳을 명시했으나, 실측 결과 **SET_NULL 17곳 · CASCADE 95곳**으로 코드베이스가 확장됨. 또한 디렉터리가 모노레포 구조(`packages/shared`, `apps/`, `services/`)로 재편되어 지시서의 단일 앱 경로(`stocks/models.py` 등)는 현재 `packages/shared/stocks/models.py` 등에 해당. 본 보고서는 **실제 코드 기준**으로 작성.

---

## FK orphan 위험

### SET_NULL 사용처 (실측 17곳, 9개 파일)

| 파일 | 라인 | 필드 | 부모 삭제 시 영향 |
|------|------|------|------------------|
| `macro/models/indicators.py` | 310 | (지표 관련) | null 처리 |
| `thesis/models/monitoring.py` | 66 | `ThesisAlert.indicator` | 지표 삭제 시 알림은 보존, FK만 null |
| `thesis/models/indicator.py` | 15 | `ThesisIndicator.premise` | 전제 삭제 시 지표 보존 |
| `thesis/models/thesis.py` | 70, 77 | `source_news`, `copied_from` | 원본 뉴스/복제원본 삭제 시 가설 보존 |
| `apps/chain_sight/models/news_event.py` | 69 | `duplicate_of` (self FK) | 중복 원본 삭제 시 null |
| `apps/portfolio/models.py` | 341, 768, 870 | `wallet_snapshot_at_execution`, `ChatSession.analysis_run` 등 | 스냅샷/분석 삭제 시 느슨한 연결 유지 |
| `apps/market_pulse/models/anomaly.py` | 26 | (이상치 관련) | null 처리 |
| `services/rag_analysis/models.py` | 132, 232, 239 | `AnalysisSession.basket`, `usage_logs.session/message` | 바스켓/세션 삭제 시 로그 보존 |
| `services/serverless/models.py` | 660, 797, 1353 | `ScreenerAlert.preset`, `InvestmentThesis.user`, `AdminActionLog.user` | 프리셋/유저 삭제 시 레코드 보존 |
| `services/sec_pipeline/models.py` | 94 | `SupplyChainEvidence.target_company` | **종목 삭제 시 증거 보존, 타깃만 null** |

### 🔴 핵심 발견: SET_NULL 후 orphan 정리 로직 **전무**

- 코드 전수 검색(`orphan`, `__isnull=True` + `delete`/`cleanup`/`prune`) 결과, **PG 측 orphan(부모 null이 된 자식) 레코드를 주기적으로 정리하는 로직이 단 한 곳도 없음**.
- 유일한 `orphan` 키워드는 `services/news/services/news_neo4j_sync.py:707`의 **Neo4j 노드** 정리(`Cleaned up N orphaned NewsEvent nodes`)뿐 — 이는 그래프 노드 청소이지 PG orphan 정리가 아님.
- **의도된 설계인 부분**: rag_analysis `usage_logs`, portfolio `ChatSession` 등은 "감사/이력 보존"이 목적이므로 null 잔존이 정상. 면책.
- **실질 위험 지점**:
  - `sec_pipeline.SupplyChainEvidence.target_company` → SET_NULL. 종목 delisting 시 `target_company=null`이지만 `target_company_name`(문자열)은 보존됨. 이 상태의 evidence는 `quality_checks`의 ticker 매칭률 계산에서 **미매칭으로 카운트**되어 매칭률 지표를 왜곡할 수 있음(라인 73의 `target_company__isnull=False` 필터). null 회수(재매칭 시도) 큐(`UnmatchedCompanyQueue`)는 신규 미매칭만 다루고, **SET_NULL로 사후 null이 된 건은 큐에 재투입되지 않음** → 영구 orphan.
  - `thesis.Thesis.source_news` SET_NULL → 뉴스 정리(retention) 배치가 돌면 가설의 출처 추적이 끊김. 출처 끊긴 가설을 식별하는 모니터링 없음.

> **권고(코드 변경 아님, 후속 태스크 제안)**: ① `target_company__isnull=True AND target_company_name != ''` 조건의 evidence를 주기적으로 재매칭 큐에 재투입하는 reconcile 태스크. ② orphan 카운트를 `quality_checks` 알림에 추가.

---

## CASCADE 체인

### CASCADE 사용처 (실측 95곳, 32개 파일) · PROTECT 7곳 · DO_NOTHING 0곳

### 가장 넓은 팬아웃: `Stock` 삭제

`Stock`(`packages/shared/stocks/models.py`)를 참조하는 FK의 on_delete 분포:

| 참조처 | on_delete | 삭제 영향 |
|--------|-----------|----------|
| `stocks/models.py` DailyPrice(194), 재무(306), Overview(945 O2O), 1015/1063/1153 | **CASCADE** | 주가·재무·개요 전량 삭제 (의도됨) |
| `users/models.py` Portfolio(47), WatchlistItem(223) | **CASCADE** | 사용자 포트폴리오/워치리스트 항목 삭제 |
| `apps/chain_sight/*` 9개 모델 (chain_profile, sensitivity, growth_stage, capital_dna, insider_signal, event_reaction, revenue_structure, narrative_tag) | **CASCADE** | 프로파일·DNA·민감도 등 전량 삭제 |
| `apps/chain_sight/models/news_event.py` (28) | **PROTECT** | ✅ 뉴스이벤트 있으면 종목 삭제 차단 |
| `apps/portfolio/models.py` WalletHolding(93), MetricResult(410), DiagnosticCard(521), LLMComment(595) | **PROTECT** | ✅ 보유/분석결과 있으면 종목 삭제 차단 |
| `services/sec_pipeline` source_company | **CASCADE** / target_company **SET_NULL** | 출처 종목 삭제 시 evidence 삭제, 타깃은 null |

> **모순 지점(주의)**: `Stock`에 대해 일부는 **CASCADE**(chain_sight 9개), 일부는 **PROTECT**(portfolio 4개, chain_sight news_event)가 혼재. 즉 **portfolio 보유분이 있으면 PROTECT가 먼저 종목 삭제를 막으므로**, 실무상 CASCADE 9개 체인은 "보유분 없는 종목"에만 발동. 설계 일관성은 부족하나 PROTECT가 안전 게이트 역할을 하여 **치명적 대량 삭제는 방어됨**. 단, portfolio 데이터가 전혀 없는 종목은 chain_sight 프로파일 9종이 조용히 동반 삭제됨.

### 3단계 이상 연쇄 삭제 추적

**체인 1 — User 삭제 (CASCADE 4건 fanout):**
```
User ─CASCADE→ Portfolio
User ─CASCADE→ Watchlist ─CASCADE→ WatchlistItem        (2단)
User ─CASCADE→ Wallet ─CASCADE→ WalletHolding           (2단)
                      ─CASCADE→ WalletSnapshot
                      ─CASCADE→ Portfolio(wallet) ─CASCADE→ AnalysisRun
                                                            ├─CASCADE→ MetricResult     (4단)
                                                            ├─CASCADE→ DiagnosticCard   (4단)
                                                            ├─CASCADE→ LLMComment       (4단)
                                                            ├─CASCADE→ StoredAnalysis(O2O)
                                                            └─SET_NULL→ ChatSession.analysis_run
User ─CASCADE→ AnalysisSession(rag) ─SET_NULL→ usage_logs
User ─CASCADE→ analysis_sessions ...
```
- **최대 깊이 4단**: `User→Wallet→Portfolio→AnalysisRun→{MetricResult|DiagnosticCard|LLMComment}`.
- 단, `WalletHolding.stock`·`MetricResult.stock`·`LLMComment.stock`은 **PROTECT**(Stock 측). User 삭제 경로는 Stock을 지우지 않으므로 PROTECT가 발동하지 않음 → User 삭제는 정상 연쇄.
- ChatSession은 SET_NULL로 분기되어 대화 이력은 보존(의도됨).

**체인 2 — Thesis 삭제:**
```
Thesis ─CASCADE→ ThesisPremise
Thesis ─CASCADE→ ThesisIndicator ─CASCADE→ IndicatorReading   (2단)
Thesis ─CASCADE→ ThesisSnapshot
Thesis ─CASCADE→ ThesisAlert (indicator는 SET_NULL 분기)
```
- 최대 2단, 예측 가능. ThesisIndicator.premise는 SET_NULL이라 전제 삭제가 지표를 지우지 않음(느슨).

**체인 3 — NewsArticle 삭제:**
```
NewsArticle ─CASCADE→ NewsEntity ─CASCADE→ EntityHighlight    (2단)
```

**평가**: 모든 CASCADE 체인 **최대 4단(User 경로)**, 나머지는 2단 이하. 순환 참조 없음. PROTECT가 회계성 데이터(보유·분석결과)와 뉴스이벤트에 적절히 배치되어 **의도치 않은 대량 삭제는 구조적으로 차단**됨. 🟢 양호.

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황 (단일 소스 패턴 — audit P0 #9, 2026-04-29)

| 모델 | 위치 | 플래그 | 비고 |
|------|------|--------|------|
| `CompanyChainProfile` | `apps/chain_sight/models/chain_profile.py:84` | `neo4j_dirty`(db_index) + `neo4j_synced_at` | save() 시 자동 dirty |
| `RelationConfidence` | `apps/chain_sight/models/relation_discovery.py:148` | `neo4j_dirty` + `neo4j_synced_at` | `save()`에서 `neo4j_dirty=True` 강제(178~179), bulk_update는 수동 토글 필요 |
| `SupplyChainEvidence` | `services/sec_pipeline/models.py:112` | `neo4j_dirty` + `neo4j_synced_at` | `synced_to_neo4j` 필드 금지 명시 |

- **단일 소스 통일 완료**: `synced_to_neo4j`(역의미 플래그)는 전면 제거되고 `neo4j_dirty`(True=동기화 필요)로 통일. DECISIONS audit P0 #9 반영 확인. 🟢
- **chainsight ↔ sec_pipeline 양쪽 모두 동일 패턴** 사용. 의미 반전 없음.

### 동기화 실패 시 재시도 메커니즘

**sec_pipeline (`tasks.py` sync_dirty_to_neo4j) — 모범 사례 🟢:**
- **2-Phase + `select_for_update(skip_locked=True)`**: Phase A에서 PG row lock + dict 복사(최대 500건) → Phase B Neo4j 동기화 → Phase C 성공분만 `neo4j_dirty=False`.
- **부분 실패 격리**: 개별 row 실패 시 `synced_ids`에 미포함 → 해당 row는 `dirty=True` 잔존 → **다음 beat에서 자동 재시도(self-healing)**.
- DELETE+CREATE 패턴, dynamic type, MERGE 금지 규약 준수.

**chain_sight (`sync_tasks.py`):**
- `sync_profiles_to_neo4j`: profile 단위 try/except, 실패분은 `neo4j_dirty=True` 유지 → 다음 beat 재시도. `max_retries=1`.
- `neo4j_dirty_sync_tasks.py`: `max_retries=2, default_retry_delay=60`.

### 🟡 재시도 정책 불균일 (Medium)

| 태스크 | max_retries | backoff |
|--------|-------------|---------|
| `sync_profiles_to_neo4j` / `sync_relations_to_neo4j` | **1** | 없음 |
| `chainsight-neo4j-dirty-sync` | **2** | `default_retry_delay=60`(고정) |
| `sec_pipeline` 파이프라인 | **3~5** | `countdown=base*(2**retries)` 지수백오프 ✅ |

- CLAUDE.md 규약은 "Celery 태스크: max_retries=3, exponential backoff"인데 **chain_sight Neo4j 태스크는 max_retries 1~2 + 백오프 없음**으로 규약 미준수. 단, dirty 플래그 기반 self-heal이 사실상 무한 재시도 역할을 하므로 실손은 낮음.

### 🔴 PG↔Neo4j 불일치 감지 — **단방향만 존재 (High)**

현재 감지 가능한 것 (PG 기준 forward만):
- `quality_checks.py:93`: `neo4j_dirty=True AND target_company__isnull=False` 건수 > 50 → "Neo4j dirty 적체" 알림.
- `intelligence.py:100`: `sync_synced`(dirty=False) vs `sync_pending`(dirty=True) 카운트 대시보드.

**감지 못 하는 것 (역방향 / 좀비):**
1. **PG에는 dirty=False(동기화 완료 표시)인데 Neo4j 엣지가 실제로 없는 경우** — 예: Neo4j DB 복원/롤백, 수동 삭제, 동기화 후 그래프 장애. PG는 "동기화됨"으로 믿고 다시 안 보냄 → **영구 누락**. 이를 교차 검증(Neo4j 실제 카운트 vs PG dirty=False 카운트 대조)하는 reconcile 로직 없음.
2. **PG에서 삭제되었으나 Neo4j에 남은 좀비 엣지** — `RelationConfidence` row를 PG에서 delete하면 save() 미발생 → Neo4j DELETE가 트리거되지 않음. `sync_dirty_to_neo4j`는 dirty=True row만 처리하므로 **삭제된 row는 영원히 미처리** → Neo4j에 좀비 엣지 잔존. (레거시 `RELATED_TO` 1회 cleanup은 캐시 키로 단발 실행되며 일반 삭제는 미커버.)
3. SET_NULL로 `target_company=null`이 된 sec evidence는 Phase A의 `target_company__isnull=False` 필터에 걸려 **재동기화 대상에서 제외** → Neo4j 엣지가 stale하게 남을 수 있음.

> **권고(후속 태스크)**: ① 주기적 reconcile — `RelationConfidence`/`SupplyChainEvidence`의 dirty=False 집합과 Neo4j 실제 엣지 카운트를 대조해 누락/좀비를 검출하고 누락은 dirty 재설정, 좀비는 DELETE. ② PG delete 시 Neo4j 엣지 제거를 보장하는 soft-delete + tombstone 동기화 패턴 검토(`pre_delete` 시그널 또는 `relation_status='deleted'` + dirty 토글).

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 (양호 🟢)

광범위하게 설정됨 — 주요 항목:

| 모델 | 제약 | 파일 |
|------|------|------|
| `EconomicIndicatorValue` | `(indicator, date)` | macro/indicators.py:133 |
| `MarketIndexValue` | `(index, date)` | macro/indicators.py:257 |
| `IndicatorSectorRel` | `(indicator, sector_code, condition_type)` | macro/relationships.py:94 |
| `IndicatorPairRel` | `(indicator_a, indicator_b)` | macro/relationships.py:165 |
| `IndustryMetricBenchmark` | `(industry, fiscal_year, metric_code)` | metrics/benchmark.py:109 |
| `PeerMetricBenchmark` | `(symbol, fiscal_year, metric_code, preset_key)` | metrics/benchmark.py:173 |
| `CompanyMetricSnapshot` | `(symbol, fiscal_year, metric_code)` | metrics/metric_snapshot.py:73 |
| `DailyPrice` | `(stock, date)` | stocks/models.py:246 |
| `NewsEntity` | `(news, symbol)` | news/models.py:221 |
| `SentimentHistory` | `(symbol, date)` | news/models.py:291 |
| `NewsArticle.url` | `unique=True` | news/models.py:41 |
| `DailyNewsKeyword.date` | `unique=True` | news/models.py:316 |
| `CoMovement/RelationDiscovery` | `(symbol_a, symbol_b[, period])` | relation_discovery.py:25,54 |
| `Portfolio` 등 4종 | `UniqueConstraint` | portfolio/models.py:460,552,612,735 |
| `ChainNewsEvent` | `(source, source_id)` | (test 기준) |
| `CompanyAlias` | `(alias, context_sector)` — country 무관 | sec_pipeline |

### 🟡 update_or_create race condition (124곳 / Medium)

- `update_or_create` **124곳**, `get_or_create` 84곳 사용.
- **Django `update_or_create`는 원자적이지 않음**: 내부적으로 SELECT → (없으면) CREATE → (있으면) UPDATE. 동시 실행 시 두 워커가 동시에 "없음"을 보고 둘 다 CREATE 시도 → unique_together가 있으면 **하나는 IntegrityError**, 없으면 **중복 row**.
- **방어 현황**:
  - 대부분의 upsert 대상 모델이 unique_together/UniqueConstraint를 보유 → DB 레벨에서 중복은 차단되나 **동시성 시 IntegrityError 예외가 표면화**될 수 있음. 호출부에서 retry/except 처리 여부는 케이스별.
  - `transaction.atomic` 동반 호출이 `relation_tasks.py`, `market_pulse/tasks/macro.py`의 update_or_create 주변에 **없음** — 검색 결과 해당 파일에서 atomic 미사용.
  - `select_for_update`는 **7곳만** 사용(rag_analysis basket 2, watchlist 2, sec_pipeline sync 1, +test). 즉 대부분의 update_or_create는 락 없이 실행.
- **실손 평가**: 이들 대부분이 **Celery beat 단일 스케줄로 직렬 실행**(같은 종목을 동시에 두 워커가 처리할 일이 드묾)되어 실제 충돌 확률은 낮음. 단, `solo` 풀이 아닌 다중 워커 환경 + 동일 심볼 중복 enqueue 시 IntegrityError 가능.

> **권고(후속 태스크)**: 고빈도 upsert(예: `IndicatorValue`, `RelationConfidence`)는 `update_or_create`를 `transaction.atomic()` 블록 + `IntegrityError` 재시도로 감싸거나, PostgreSQL `ON CONFLICT`(`QuerySet.bulk_create(update_conflicts=True)`) 패턴으로 전환 검토.

### 🟡 symbol 기반 약결합 FK (Medium)

- `RelationConfidence`, `PriceCoMovement`, `RelationDiscovery`는 종목을 `symbol_a/symbol_b`(**CharField**, FK 아님)로 보관. → 종목이 `Stock` 테이블에서 삭제돼도 **DB 레벨 무결성 검사 없이 문자열만 잔존**. unique_together는 있으나 referential integrity는 없음. delisting 종목의 관계 데이터가 dangling 문자열로 남을 수 있음(Neo4j 좀비 엣지 위험 ②와 연결).

---

## 부록: 실측 통계 요약

| 항목 | 실측값 | 지시서 명시값 |
|------|--------|--------------|
| `on_delete=CASCADE` | 95곳 / 32파일 | 37곳 / 7파일 |
| `on_delete=SET_NULL` | 17곳 / 9파일 | 7곳 / 3파일 |
| `on_delete=PROTECT` | 7곳 | (미명시) |
| `on_delete=DO_NOTHING` | 0곳 | — |
| `update_or_create` | 124곳 | — |
| `get_or_create` | 84곳 | — |
| `select_for_update` | 7곳(비테스트 5) | — |
| `neo4j_dirty` 보유 모델 | 3종(chain_profile, relation_discovery, sec evidence) | — |
| PG orphan 정리 배치 | **0건** | — |
| PG↔Neo4j reconcile 로직 | **0건** (단방향 dirty 적체 알림만) | — |

---

*본 보고서는 정적 코드 분석 기반이며 런타임 데이터(실제 orphan/좀비 건수)는 포함하지 않음. High 항목 ①②는 코드 수정 없이 reconcile/cleanup 태스크 신설로 대응 권장.*
