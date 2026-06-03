# 데이터 무결성 감사 보고서

> 감사일: 2026-06-03 · 모드: **읽기 전용 (코드 무수정)** · 대상: Stock-Vis 백엔드 전체 모델 레이어
> 감사 범위: `on_delete` 정책, CASCADE 연쇄, Neo4j↔PG 동기화, Unique/`update_or_create`

> ⚠️ **지시서 경로 불일치 (선결 사항)**
> 지시서가 지목한 경로(`stocks/models.py`, `users/models.py`, `news/models.py` 등)는 **현재 존재하지 않음**.
> "서비스 리모델링(데이터 구조 개편)"으로 디렉토리가 재구성되어 실제 모델은 아래에 위치:
> - `packages/shared/{stocks,users,metrics}/models*.py`
> - `apps/{portfolio,chain_sight,market_pulse}/models*.py`
> - `services/{rag_analysis,serverless,news,sec_pipeline,validation,_dormant/graph_analysis}/models.py`
> - `macro/models/*.py`, `thesis/models/*.py`
>
> 따라서 지시서의 집계 수치(CASCADE 37곳 / SET_NULL 7곳)도 실측과 다름.
> **실측: CASCADE 95곳 · SET_NULL 17곳 · PROTECT 7곳 · DO_NOTHING 0곳** (migrations/test 제외).

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 2 | (H-1) PG CASCADE 삭제가 Neo4j에 전파 안 됨 → orphan edge 영구 잔존 · (H-2) Stock 삭제 시 비-FK `symbol` CharField 다수 dangling |
| 🟠 Medium | 4 | (M-1) SET_NULL 후 주기적 orphan cleanup 부재 · (M-2) Neo4j 역방향(Neo4j→PG) 불일치 감지 메커니즘 없음 · (M-3) `update_or_create` 100곳 비원자성 race · (M-4) sec_pipeline 3단계 CASCADE 체인 (Stock→RawDoc→Evidence) |
| 🟡 Low | 3 | (L-1) dirty sync task가 `self.retry` 미호출(eventual consistency 의존) · (L-2) `_dormant/graph_analysis` 잔존 CASCADE 9곳 · (L-3) AdminActionLog 등 감사로그 user SET_NULL(의도적이나 명문화 부족) |

**총평**: `on_delete` 정책 자체는 대체로 합리적이며 `neo4j_dirty` 단일 소스 패턴(audit P0 #9, 2026-04-29)이 잘 정착됨. 다만 **관계형 무결성과 그래프 DB 무결성이 단방향으로만 연결**되어 있어, RDB 삭제가 Neo4j에 반영되지 않는 구조적 공백이 가장 큰 위험.

---

## FK orphan 위험

### SET_NULL 사용처 (실측 17곳)

지시서가 지목한 3개 파일 외에도 macro, thesis, portfolio, market_pulse 등에 분산됨. 핵심 사용처:

| 위치 | 필드 | 의도 | orphan 정리 로직 |
|------|------|------|------------------|
| `services/sec_pipeline/models.py:94` | `SupplyChainEvidence.target_company` | 타깃 미매칭 시 null 보관 후 **나중에 재매칭** | ✅ **존재** — `UnmatchedCompanyQueue` + `ticker_matcher.py`가 재매칭 (의도적 워크플로우) |
| `services/rag_analysis/models.py:132` | `AnalysisSession.basket` | basket 삭제돼도 대화 세션 보존 | ❌ 없음 (의도적 보존 — 대화 이력 유지) |
| `services/rag_analysis/models.py:232,239` | `LLMUsageLog.session/message` | 세션·메시지 삭제돼도 과금 로그 보존 | ❌ 없음 (의도적 — 감사/과금 추적) |
| `services/serverless/models.py:660` | `ScreenerAlert.preset` | 프리셋 삭제 시 커스텀 필터로 강등 | ⚠️ 없음 — null이면 `filters_json`에 의존, 둘 다 비면 무효 알림 잔존 가능 |
| `services/serverless/models.py:797` | `InvestmentThesis.user` | 유저 삭제 시 테제 보존 | ❌ 없음 (익명 테제로 잔존) |
| `services/serverless/models.py:1353` | `AdminActionLog.user` | 감사 로그 — 유저 삭제돼도 이력 유지 | ❌ 없음 (의도적 — 감사 추적이 목적) |
| `macro/models/indicators.py:310`, `thesis/models/{thesis,indicator,monitoring}.py`, `apps/chain_sight/models/news_event.py:69`, `apps/portfolio/models.py:341,768,870`, `apps/market_pulse/models/anomaly.py:26` | 다양 | 참조 대상 보존 | ❌ 없음 |

#### 🟠 M-1: SET_NULL 후 주기적 orphan cleanup 부재
- `grep`으로 `isnull=True` + `delete`/`cleanup`/`orphan` 조합 검색 결과 **0건**.
- 즉 SET_NULL로 FK가 null이 된 레코드를 **주기적으로 청소하거나 모니터링하는 로직이 없음**.
- 대부분은 "의도적 보존"(감사 로그, 과금 로그, 대화 이력)이라 즉각적 위험은 낮음.
- 다만 `ScreenerAlert.preset=null AND filters_json={}` 같은 **양쪽 다 비어 무효가 된 레코드**는 영구 잔존 → 알림 엔진이 무효 알림을 계속 평가할 위험. 모니터링 권장.

**권장 (무수정 원칙 — 제안만)**: SET_NULL 보존이 의도라면 모델 docstring/주석에 "보존 의도"를 명문화(AdminActionLog는 이미 "감사 추적" 주석 있음). 무효화 가능 레코드(ScreenerAlert)는 nightly 헬스체크에 `preset__isnull=True, filters_json={}` 카운트 추가 검토.

---

## CASCADE 체인

### 🟠 M-4 / H-2: Stock 삭제 영향 범위 (가장 많은 참조 대상)

`Stock`을 `on_delete=CASCADE`로 **직접 참조**하는 FK는 7곳, 모두 `packages/shared/`:

| 모델 | 위치 | 참조 방식 |
|------|------|-----------|
| `BasePriceData` → `DailyPrice`, `WeeklyPrice` | `stocks/models.py:194` | `to_field="symbol"` CASCADE |
| `BasicFinancialStatement` → `BalanceSheet`, `IncomeStatement`, `CashFlowStatement` | `stocks/models.py:306` | `to_field="symbol"` CASCADE |
| `EODSignal` | `stocks/models.py:1015` | CASCADE |
| `SignalAccuracy` | `stocks/models.py:1063` | CASCADE |
| `StockNews` | `stocks/models.py:1153` | CASCADE (null 허용) |
| `Portfolio.stock` | `users/models.py:47` | `to_field="symbol"` CASCADE |
| `WatchlistItem.stock` | `users/models.py:223` | `to_field="symbol"` CASCADE |

**Stock 1건 삭제 시 직접 연쇄**: 일봉/주봉 전체 + 3종 재무제표(분기·연간 전체) + EOD 시그널 + 시그널 정확도 + 종목 뉴스 + 모든 유저의 포트폴리오/워치리스트 항목이 한 번에 삭제됨. 사실상 **돌이킬 수 없는 대량 삭제**.

#### 🔴 H-2: 비-FK `symbol` CharField dangling
- serverless / validation / news / sec_pipeline 다수 모델은 종목을 **FK가 아닌 `symbol` CharField**로 보유 (예: `serverless/models.py`의 mover/corporate_action/institutional, `validation/models/*`의 `symbol`).
- 이들은 Stock 삭제 시 **CASCADE도 SET_NULL도 작동하지 않고 문자열만 남는 dangling reference**가 됨.
- 즉 Stock 삭제는 (a) FK 연결분은 과도하게 삭제, (b) 문자열 연결분은 좀비로 잔존 — **비대칭 불일치**.

### 3단계 이상 연쇄 (sec_pipeline)

```
Stock(symbol)
  └─CASCADE→ RawDocumentStore(symbol)          # sec_pipeline/models.py:24
       └─CASCADE→ SupplyChainEvidence           # source_document FK :83
       └─CASCADE→ BusinessModelSnapshot         # source_document FK :181
            └─CASCADE→ BusinessModelEvidence    # snapshot FK :243
```
- **최대 4단계 연쇄**(Stock → RawDoc → Snapshot → BusinessModelEvidence).
- 동시에 `SupplyChainEvidence.source_company`도 Stock을 CASCADE 참조(:88)하므로 Stock 삭제는 두 경로로 동일 Evidence를 친다.
- `target_company`만 SET_NULL(:94)이라, source 측 삭제 시 evidence 자체가 사라지는 반면 target 측 삭제 시는 보존되는 **비대칭 정책** — 의도적이나(미매칭 재처리 워크플로우) 문서화 필요.

### 기타 CASCADE 체인
- `ScreenerPreset → ScreenerAlert(preset은 SET_NULL) / ScreenerAlertHistory(alert CASCADE)` — alert 삭제 시 history 연쇄.
- `ETFProfile → ETFHolding` CASCADE (`serverless/models.py:1050`).
- `NewsArticle → NewsEntity → NewsEntityHighlight` 2단 CASCADE (`news/models.py:176,240`).
- `DataBasket → DataBasketItem` CASCADE / `AnalysisSession → AnalysisMessage` CASCADE (`rag_analysis`).
- **🟡 L-2**: `services/_dormant/graph_analysis/models.py`에 CASCADE 9곳 잔존 — dormant(미사용) 디렉토리이나 마이그레이션엔 살아있을 수 있으므로 정리 대상 후보.

---

## Neo4j 동기화

### 패턴: `neo4j_dirty` 단일 소스 (audit P0 #9, 2026-04-29 정착)
- `synced_to_neo4j`(역의미) → `neo4j_dirty`(True=동기화 필요)로 의미 반전 통일 완료.
- 적용 모델: `apps/chain_sight`(`CompanyChainProfile`, `RelationConfidence`), `services/sec_pipeline`(`SupplyChainEvidence`).
- `save()` 시 자동 `neo4j_dirty=True`, `queryset.update()`/`bulk_update()`는 save 미호출이라 **수동 토글** 처리됨 (relation_tasks.py:415, relation_discovery.py:178에 명시적 주석 — 양호).

### 재시도 메커니즘
| Task | 재시도 설정 | 실패 처리 방식 |
|------|------------|---------------|
| `run_neo4j_dirty_sync` (chain_sight) | `max_retries=2, default_retry_delay=60` | task 레벨 retry 미호출 — `sync_dirty_relations()` 내부에서 개별 relation 실패는 `logger.error`만 하고 **dirty=True 유지** → 다음 주기 자동 재시도 |
| `sync_*` (chain_sight) | `max_retries=1` | 동일 — 성공분만 `update(neo4j_dirty=False)`, 실패분 dirty 유지 |
| sec_pipeline Neo4j sync (tasks.py:397~) | `max_retries=1`, `select_for_update(skip_locked=True)` | Phase A(PG lock)→B(Neo4j upsert)→C(성공분만 dirty=False). 실패분 dirty 유지 |

- **설계 평가**: "성공분만 dirty 해제, 실패분은 dirty 유지 → 다음 배치가 재시도"하는 **eventual consistency 패턴**으로 합리적. partial failure에 안전.
- **🟡 L-1**: dirty sync task가 `self.retry`를 직접 호출하진 않으므로, 동기화 지연은 전적으로 **다음 beat 주기**에 의존. beat가 멈추면 dirty 레코드가 무한 적체. → beat 헬스 모니터링이 안전망이어야 함.

### 🔴 H-1: PG CASCADE 삭제가 Neo4j에 전파되지 않음 (최고 위험)
- `neo4j_dirty` 플래그는 **생성/수정**만 추적. **삭제는 추적하지 않음**.
- PG에서 `Stock`/`RelationConfidence`/`SupplyChainEvidence`가 CASCADE로 삭제되면, 해당 레코드는 사라지지만 **Neo4j의 대응 노드/엣지는 그대로 남음** → orphan edge.
- `neo4j_sync.py`에 `_delete_edge`가 있으나 이는 `relation_status`가 약화(stale/weak/hidden)됐을 때만 호출(:43). **물리 삭제(DELETE) 시점엔 호출되지 않음** (삭제된 행은 dirty 큐에 못 들어감).
- 결과: RDB와 그래프 DB가 **삭제에 대해 영구 불일치**. 시간이 갈수록 Neo4j에 유령 노드/엣지 누적.

#### 🟠 M-2: 역방향(Neo4j→PG) 불일치 감지 메커니즘 없음
- 동기화는 **PG→Neo4j 단방향**. "PG엔 있는데 Neo4j엔 없는" 경우는 dirty 플래그로 잡히지만, "Neo4j엔 있는데 PG엔 없는"(=삭제 누락) 경우를 **탐지하는 reconciliation 로직이 없음**.
- 부분 감지 자산은 존재: `sec_pipeline/quality_checks.py:143`, `intelligence.py:100`이 `neo4j_dirty=False` 카운트를 집계 → "동기화됨" 추정치는 제공하나, **양쪽 카운트 대조(set difference) 검증은 없음**.
- `news/services/news_neo4j_sync.py:546`은 "Neo4j에 이미 존재하는 article_id 제외" 로직으로 중복 방지는 하나, 역시 PG→Neo4j 방향만.

**권장 (제안만)**: nightly에 reconciliation 잡 추가 검토 — (1) PG에서 hard-delete 시 Neo4j 엣지 삭제를 큐잉하는 tombstone/signal, 또는 (2) 주기적으로 Neo4j 노드 ID ↔ PG PK set-diff 비교 후 고아 엣지 리포트. 무수정 원칙상 본 보고서는 탐지 공백만 명시.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황
- **`unique_together`: 약 60곳** (전 앱 분포). 시계열·재무 데이터의 멱등성 키로 일관되게 사용:
  - 가격/시계열: `("stock","date")`, `("symbol","date")` — 중복 적재 방지 (양호).
  - 재무: `("stock","period_type","fiscal_year","fiscal_quarter")` — 4종 모델 동일 키 (일관성 양호).
  - 관계: chain_sight `("symbol_a","symbol_b")`, `(...,"relation_type")` / serverless `("source_symbol","target_symbol","relationship_type")`.
  - 검증: validation `("symbol","fiscal_year","metric_code","preset_key")` 계열.
- **`UniqueConstraint`: 4곳**, 모두 `apps/portfolio/models.py`(460,552,612,735) — 조건부 unique 등 표현이 필요한 신규 모델에서 명시적 사용 (양호).
- **`unique=True`(단일 필드): 16곳**.

> 평가: 멱등성 키 커버리지는 전반적으로 우수. `update_or_create`의 lookup 키가 대부분 `unique_together`와 일치해 무결성 보강.

### 🟠 M-3: update_or_create race condition (100곳)
- 실측 **`update_or_create` 100건 / `get_or_create` 27건**, 거의 전부 `tasks.py`·`services/`(배치/동기화 경로).
- `update_or_create`는 **SELECT → (없으면)INSERT / (있으면)UPDATE**가 단일 트랜잭션 원자 연산이 **아님**. 동일 키에 대해 두 워커가 동시 진입하면:
  - `unique_together`가 있으면 → 두 번째 INSERT가 `IntegrityError`로 실패 (데이터는 안전하나 task 실패).
  - 방어 코드 존재 확인: `rag_analysis/views.py:134`에 "unique_together 제약 위반(중복 아이템)" 처리 코멘트 → 일부 경로는 IntegrityError를 catch.
- **실제 위험도는 낮음**: 대부분 Celery beat 단일 스케줄·종목별 순차 처리라 동일 키 동시성이 드묾. sec_pipeline은 `select_for_update(skip_locked=True)`로 명시적 lock (모범 사례).
- **잔존 위험**: 동일 종목을 두 트리거(수동 sync + beat)가 동시에 칠 때, `unique_together`가 **없는** `update_or_create` 경로(예: 일부 keyword/heatmap 서비스)는 중복 행 생성 가능. lookup 키가 unique 제약으로 뒷받침되는지 경로별 점검 권장.

**권장 (제안만)**: 동시 트리거 가능 경로는 (1) lookup 키를 `unique_together`로 보강하거나, (2) `transaction.atomic()` + `select_for_update`로 감싸는 패턴 통일. sec_pipeline의 `skip_locked` 패턴을 표준으로 확산 검토.

---

## 부록: 실측 집계 vs 지시서

| 항목 | 지시서 | 실측 | 비고 |
|------|--------|------|------|
| SET_NULL | 7곳 / 3파일 | **17곳 / 12+파일** | 리모델링으로 경로·수치 변동 |
| CASCADE | 37곳 / 7파일 | **95곳 / 20+파일** | 동일 |
| PROTECT | (미언급) | **7곳** | metrics, portfolio, market_pulse |
| DO_NOTHING | (미언급) | **0곳** | 없음 (양호) |
| unique_together | — | **~60곳** | |
| UniqueConstraint | — | **4곳** (portfolio) | |
| update_or_create | — | **100건** | |
| neo4j_dirty 적용 | sec_pipeline, chainsight | **확인됨** (단일 소스 통일 완료) | audit P0 #9 |

---

### 우선 조치 권고 (무수정 — 후속 작업 제안)
1. **🔴 H-1 우선**: PG hard-delete → Neo4j orphan edge. nightly reconciliation 또는 삭제 tombstone 설계 검토.
2. **🔴 H-2**: Stock 삭제 정책 재검토 — 비-FK `symbol` CharField dangling. 운영상 Stock은 사실상 삭제 금지(soft-delete) 대상인지 정책 명문화 권장.
3. **🟠 M-2/M-3**: Neo4j 양방향 reconciliation + 동시 트리거 경로 `update_or_create` lock 표준화.

> 본 보고서는 **읽기 전용 정적 분석**이며 실제 DB 상태(orphan 레코드 실측 카운트)는 포함하지 않음. 수치 검증이 필요하면 운영 DB 대상 read-only 쿼리 감사를 별도 수행 권장.
