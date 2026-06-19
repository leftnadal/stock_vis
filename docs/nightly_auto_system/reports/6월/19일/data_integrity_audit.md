# 데이터 무결성 감사 보고서

- **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis` (모노레포: `apps/`, `services/`, `packages/shared/`)
- **감사 일자**: 2026-06-19
- **감사 범위**: FK orphan, CASCADE 체인, Neo4j↔PG 동기화, Unique 제약 / update_or_create
- **모드**: 읽기 전용 (코드 수정 없음)

> ⚠️ **사전 가정 정정**: 지시서는 "SET_NULL 7곳 / CASCADE 37곳"으로 명시했으나, 실제 코드베이스는 모노레포로 재편되어 **SET_NULL 17곳 / CASCADE 97곳 / PROTECT 7곳**으로 증가. 본 보고서는 실제 현황 기준.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 HIGH | 3 | ① PG↔Neo4j reconciliation 부재(역방향 불일치 미감지) ② Stock 삭제 시 Neo4j 노드/엣지 고아화 ③ `SupplyChainEvidence.target_company` SET_NULL → 영구 stuck-dirty + 고아 엣지 |
| 🟡 MEDIUM | 4 | ④ `update_or_create` 비원자성 race(동시 Celery) ⑤ 3~4단계 CASCADE 체인 의도치 않은 대량 삭제 ⑥ Stock `on_delete` 정책 혼재(PROTECT vs CASCADE) ⑦ SET_NULL 후 일반 orphan 정리 로직 전무 |
| 🟢 LOW | 3 | ⑧ 대부분 SET_NULL은 안전한 선택적/self-ref FK ⑨ `unique_together` 커버리지 양호(60+) ⑩ EOD/leadership/attention은 `update_conflicts` 정식 upsert |

**총괄 판정**: PG 내부 무결성(FK/unique)은 **양호**. 최대 리스크는 **PostgreSQL ↔ Neo4j 이종 저장소 간 일관성** — 단방향 전진 sync만 존재하고 역방향 정합성 검증/정리 메커니즘이 없음.

---

## FK orphan 위험

### SET_NULL 사용처 전수 (17곳, 9개 파일)

| 파일:라인 | 필드 | 대상 | 평가 |
|-----------|------|------|------|
| `macro/models/indicators.py:310` | `related_indicator` | self(EconomicIndicator) | 🟢 self-ref 메타, 안전 |
| `thesis/models/monitoring.py:66` | `indicator` | ThesisIndicator | 🟢 스냅샷 보존 목적 |
| `thesis/models/indicator.py:15` | `premise` | ThesisPremise | 🟢 |
| `thesis/models/thesis.py:70` | NewsArticle | 뉴스 출처 | 🟢 출처 휘발 허용 |
| `thesis/models/thesis.py:77` | self(`copies`) | 원본 가설 | 🟢 복제본 독립 보존 |
| `apps/chain_sight/models/news_event.py:69` | `duplicate_of` | self | 🟢 |
| `apps/portfolio/models.py:341` | `wallet_snapshot_at_execution` | WalletSnapshot | 🟡 스냅샷 삭제 시 실행이력 추적성 상실 |
| `apps/portfolio/models.py:768` | `analysis_run` | AnalysisRun | 🟢 |
| `apps/portfolio/models.py:870` | `context_analysis_run` | AnalysisRun | 🟢 |
| `apps/market_pulse/models/anomaly.py:35` | `paired_news` | MarketPulseNews | 🟢 |
| `services/rag_analysis/models.py:132` | `basket` | DataBasket | 🟢 세션 보존, 바스켓 휘발 허용 |
| `services/rag_analysis/models.py:232` | `session` | AnalysisSession | 🟡 과금 로그 보존용(의도적) |
| `services/rag_analysis/models.py:239` | `message` | AnalysisMessage | 🟡 과금 로그 보존용(의도적) |
| `services/serverless/models.py:660` | `preset` | ScreenerPreset | 🟢 프리셋 삭제 시 커스텀 필터로 전환 |
| `services/serverless/models.py:797` | `user` | User | 🟢 익명 테제 보존 |
| `services/serverless/models.py:1353` | `user` | User | 🟢 감사 로그 보존 |
| **`services/sec_pipeline/models.py:94`** | **`target_company`** | **Stock** | 🔴 **아래 상세 — 영구 stuck-dirty + 고아 Neo4j 엣지** |

### SET_NULL 후 orphan 정리 로직 존재 여부

**결론: 일반 orphan 정리 로직은 전무.** 코드베이스 전체에서 `orphan`/`reconcile`/`prune` 패턴 검색 결과, FK NULL화 후 PostgreSQL 레코드를 정리하는 배치/관리 명령은 **존재하지 않음**. 유일한 정리 로직은 Neo4j 측 고아 노드 삭제(`services/news/services/news_neo4j_sync.py:707`)뿐이며, 이는 PG가 아닌 그래프 노드 대상.

대부분의 SET_NULL은 "출처 휘발 허용 / 로그 보존" 의도라 정리가 불필요하나, **3건은 잠재 부채**:
- `rag_analysis` 과금 로그(`session`/`message` NULL) → 누적되면 dangling 로그 증가(과금 목적상 의도적이나 보존정책 명문화 권장).
- `portfolio.wallet_snapshot_at_execution` → 스냅샷 삭제 시 실행 컨텍스트 추적 불가.

### 🔴 HIGH — `SupplyChainEvidence.target_company` SET_NULL 복합 결함

`services/sec_pipeline/models.py:94`에서 `target_company`가 SET_NULL. Stock 삭제 시:

1. `target_company`가 NULL이 되지만 `neo4j_dirty` 플래그는 그대로 유지될 수 있음.
2. 동기화 태스크 `sync_dirty_to_neo4j`(`tasks.py:430`)는 **`target_company__isnull=False`로 필터** → NULL이 된 row는 **영원히 sync 큐에서 제외 = stuck-dirty**.
3. 이미 Neo4j에 생성된 SEC-origin 엣지(`source: 'sec_10k'`)는 **삭제 트리거가 없어 고아 엣지로 잔존**.

→ PG에서는 종목이 사라졌는데 Neo4j 그래프에는 관계가 남는 전형적 이종 저장소 불일치.

---

## CASCADE 체인

### 사용 현황 (97곳)

도메인별 분포: `apps/portfolio`(21), `apps/chain_sight`(13), `services/validation`(8), `services/_dormant/graph_analysis`(8, 휴면), `services/sec_pipeline`(6), `services/serverless`(4), `services/rag_analysis`(5), `packages/shared/users`(6), `packages/shared/stocks`(5), `macro`(5), `thesis`(8) 등.

### 3단계 이상 연쇄 삭제 체인

| 체인 | 단계 | 영향 |
|------|------|------|
| **User → AnalysisSession → AnalysisMessage** (rag_analysis) | 3 | 사용자 삭제 시 전체 대화 이력 삭제. `AnalysisUsageLog`는 SET_NULL로 체인 차단(과금 보존) ✅ |
| **User → DataBasket → DataBasketItem** (rag_analysis) | 3 | 바스켓·아이템 전량 삭제 |
| **User → ScreenerAlert → ScreenerAlertHistory** (serverless) | 3 | 알림·발동이력 전량 삭제 |
| **NewsArticle → NewsEntity → EntityHighlight** (news) | 3 | 기사 삭제 시 엔티티·하이라이트 연쇄 |
| **User → Wallet → WalletHolding / WalletSnapshot** (portfolio) | 3 | 단, `WalletHolding.stock`은 **PROTECT** → 종목측 삭제 차단 |
| **AnalysisRun → MetricResult / DiagnosticCard / LLMComment** (portfolio) | 2~3 | 각 자식의 2번째 FK(지표정의 등)는 **PROTECT**로 보호 ✅ |
| **ChatSession → Message / Decision** (portfolio) | 3 | `analysis_run`은 SET_NULL로 차단 |

설계상 **PROTECT를 전략적으로 끼워 넣어** 무한 연쇄를 끊은 흔적이 보임(portfolio의 지표정의/종목 참조). 양호한 패턴이나, rag_analysis·serverless·news 체인은 순수 CASCADE로 대량 삭제 노출.

### Stock 삭제 시 영향 범위 (최다 FK 참조)

Stock은 `to_field="symbol"` 기반 다수 FK의 부모. CASCADE 경로:

| 참조 모델 | 정책 | 비고 |
|-----------|------|------|
| `DailyPrice`(stocks:194), `WeeklyPrice`(306) | CASCADE | 가격 시계열 전량 삭제 |
| 재무제표 3종(BS/IS/CF, unique_together period 기반) | CASCADE | |
| `StockOverviewKo`(stocks:946, OneToOne PK) | CASCADE | |
| `EODSignal`(stocks:1087 영역) | CASCADE | |
| `Portfolio.stock`(users:47), `WatchlistItem.stock`(users:223) | CASCADE | 사용자 보유/관심 삭제 |
| `WalletHolding.stock`(portfolio:93) | **PROTECT** | 🟡 **보유 시 Stock 삭제 차단** |
| `sec_pipeline.source_company`(88) | CASCADE | |
| `sec_pipeline.target_company`(94) | SET_NULL | (위 HIGH 참조) |

🟡 **MEDIUM — `on_delete` 정책 혼재**: 동일 Stock에 대해 일부 FK는 CASCADE(가격·포트폴리오·관심), 하나는 PROTECT(WalletHolding), 하나는 SET_NULL(SEC evidence). 즉 **지갑 보유 종목은 삭제가 PROTECT로 막히지만**, 보유가 없으면 가격·재무·시그널·관심까지 무차별 CASCADE. 삭제 동작이 데이터 상태에 따라 비결정적이라 운영 시 혼란 가능. 또한 PROTECT로 막힌 케이스는 **부분 삭제 실패** 후 트랜잭션 롤백 의존.

🔴 **HIGH — Stock 삭제가 Neo4j에 전파 안 됨**: PG에서 Stock CASCADE 삭제가 일어나도 Neo4j `:Stock` 노드 및 모든 엣지는 **그대로 잔존**. 삭제 신호(시그널/태스크)가 없음 → 그래프 고아 노드 누적.

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황

| 모듈 | 모델 | 필드 | 인덱스 |
|------|------|------|--------|
| chain_sight | `CompanyChainProfile`(chain_profile.py:84) | `neo4j_dirty`(default=True), `neo4j_synced_at` | ✅ db_index |
| chain_sight | `RelationConfidence`(relation_discovery.py:148) | `neo4j_dirty`, `neo4j_synced_at` | ✅ Index |
| sec_pipeline | `SupplyChainEvidence`(models.py) | `neo4j_dirty`(default=True), `neo4j_synced_at` | ✅ |

**audit P0 #9(2026-04-29)에서 의미 통일 완료**: 과거 `synced_to_neo4j`(True=완료)를 폐기하고 `neo4j_dirty`(True=동기화 필요) 단일 소스로 반전. `bulk_update`는 `save()`를 호출하지 않으므로 수동 dirty 세팅(relation_discovery.py:179)으로 보강. 양호한 설계.

### 동기화 실패 시 재시도 메커니즘

| 태스크 | 재시도 설계 | 평가 |
|--------|------------|------|
| `sec_pipeline.sync_dirty_to_neo4j` | 2-Phase + `select_for_update(skip_locked=True)`, batch 500, **per-row 실패 시 `synced_ids`에 미포함 → dirty=True 유지 → 다음 beat가 재픽업** | ✅ 견고(idempotent 재픽업이 사실상 재시도) |
| `chain_sight.sync_profiles_to_neo4j` | per-row try/except, 성공만 dirty=False, 실패는 dirty 유지 → 다음 주기 재시도 | ✅ |
| `chain_sight.sync_relations_to_neo4j` | 동일 패턴 | ✅ |

`max_retries=1`로 태스크 레벨 재시도는 최소이나, **dirty 플래그 기반 자가 재픽업**이 실질적 재시도 역할. SEC sync는 `DELETE + CREATE`(MERGE 금지) + dynamic rel-type으로 멱등성 확보. **Phase 1 단일 writer(SOLE WRITER) 규약**도 코드 주석에 명시.

### PG↔Neo4j 불일치 감지 방법

🔴 **HIGH — 역방향/양방향 reconciliation 부재.** 현재 동기화는 **전부 단방향 전진(PG → Neo4j)** 뿐:

| 불일치 시나리오 | 현재 감지/정리 | 결론 |
|------------------|----------------|------|
| PG에 dirty row 있는데 Neo4j 엣지 없음 | dirty 플래그로 재픽업 | ✅ 자동 복구 |
| **PG row 삭제됐는데 Neo4j 엣지 잔존** | 없음(tombstone/삭제 전파 없음) | 🔴 고아 엣지 |
| **Stock CASCADE 삭제됐는데 Neo4j 노드 잔존** | 없음 | 🔴 고아 노드 |
| **`target_company` SET_NULL → stuck dirty** | 없음(`isnull=False` 필터로 영구 제외) | 🔴 |
| 관계 없는 NewsEvent 노드 | `news_neo4j_sync.py:707` orphan_query로 정리 | 🟢 유일한 정리 로직 |
| PG count vs Neo4j count 정합성 대사 | 없음 | 🔴 드리프트 무감지 |

**권장**: ① 주기적 count reconciliation(PG row 수 vs Neo4j 엣지/노드 수) 배치, ② Stock/Evidence 삭제 시 `post_delete` 시그널 또는 tombstone 큐로 Neo4j 삭제 전파, ③ SET_NULL stuck-dirty row를 별도 정리 큐로 회수.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황

- **`unique_together`: 60+곳** (전 도메인 광범위 적용). 시계열은 `(stock|symbol, date)`, 재무는 `(stock, period_type, fiscal_year, fiscal_quarter)`, 검증/지표는 `(symbol, ..., preset_key)` 패턴으로 일관성 양호.
- **`UniqueConstraint`(명명형): 4곳** — `apps/portfolio/models.py`(460/552/612/735)에만 사용. 나머지는 레거시 `unique_together`. 기능상 동일하나 신규 모델은 `UniqueConstraint` 권장(조건부 제약·명명 지원).
- **PROTECT 7곳**: portfolio(WalletHolding.stock, MetricResult/DiagnosticCard/LLMComment의 지표정의 FK) — CASCADE 폭주 방지용 전략 배치. ✅

대표 제약 예시:
- `packages/shared/stocks/models.py`: `(stock,date)` ×3, `(stock,period_type,fiscal_year,fiscal_quarter)` ×3, `(stock,signal_date,signal_tag)`
- `services/serverless/models.py`: `(date,mover_type,symbol)`, `(etf,stock_symbol,snapshot_date)`, `(institution_cik,stock_symbol,report_date)` 등 9건
- `apps/chain_sight/models/relation_discovery.py`: `(symbol_a,symbol_b)`, `(symbol_a,symbol_b,period)`, `(symbol_a,symbol_b,relation_type)`

### update_or_create race condition 가능성

🟡 **MEDIUM** — `update_or_create` **107회**, `get_or_create` 30회 사용.

핵심 리스크: Django의 `update_or_create`는 **원자적이지 않음** (SELECT → 없으면 INSERT, 있으면 UPDATE = 2쿼리). 동시 Celery 워커가 같은 키로 진입 시:
1. **둘 다 INSERT** → `unique_together` 위반 IntegrityError (대부분 unique 제약이 있어 중복 생성은 차단됨, 단 태스크 실패).
2. **둘 다 UPDATE** → lost update(마지막 쓰기 승리).

집중 사용처: `apps/chain_sight/tasks/`(profile/relation/sensitivity/insider/sync), `services/sec_pipeline/`(validator_track_b, tasks). 이들은 대부분 **종목당 단일 beat 태스크**라 실제 동시성은 낮으나, 다음 케이스는 주의:
- `relation_tasks.py:299/335` `RelationConfidence.update_or_create` — 동일 `(symbol_a, symbol_b)` 쌍이 양방향 태스크에서 동시 진입 가능.
- 대부분 호출이 **`transaction.atomic()` 래핑 없이** 단독 실행 → IntegrityError 시 태스크 `max_retries`에 의존(idempotent하므로 재실행 안전하나, 로그 노이즈).

**완화 정상 동작 확인**:
- ✅ `bulk_create(update_conflicts=True)` 정식 upsert 사용처: EOD 파이프라인(`eod_pipeline.py:393`), leadership(`leadership_compute.py:236`), attention(`attention_service.py:158`) — DB 레벨 원자적 upsert로 race-safe.
- ✅ `keyword_cache.py:50` `bulk_create(ignore_conflicts=True)`.

**권장**: 고동시성 가능 경로의 `update_or_create`는 `transaction.atomic()` + `select_for_update`로 감싸거나, unique 키 기준 `bulk_create(update_conflicts=True)`로 전환.

---

## 부록 — 우선 조치 권장 (읽기 전용 제안)

| 우선 | 조치 | 근거 이슈 |
|------|------|----------|
| P0 | Stock/Evidence 삭제 → Neo4j 노드·엣지 삭제 전파(post_delete 시그널 또는 tombstone 큐) | 🔴② 🔴③ |
| P0 | PG↔Neo4j count reconciliation 주기 배치 + 드리프트 알림 | 🔴① |
| P1 | `target_company` NULL stuck-dirty row 회수 큐(`isnull=True & neo4j_dirty=True` 정리) | 🔴③ |
| P1 | 고동시성 `update_or_create`를 atomic/upsert로 전환 | 🟡④ |
| P2 | Stock `on_delete` 정책 일관성 문서화(PROTECT vs CASCADE 혼재 명문화) | 🟡⑥ |
| P2 | SET_NULL 후 dangling 로그 보존정책 명문화(rag 과금 로그) | 🟡⑦ |

> 본 보고서는 정적 분석(grep/모델 정의 검토) 기반이며 실제 DB·Neo4j 인스턴스 대조는 수행하지 않음. 수치형 검증(고아 노드 실측 등)은 운영 인스턴스 대상 별도 reconciliation 스크립트 필요.
