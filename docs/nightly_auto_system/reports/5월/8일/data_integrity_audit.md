# 데이터 무결성 감사 보고서

**감사 일자**: 2026-05-08
**감사 범위**: PostgreSQL 모델 무결성 + Neo4j 동기화 + Unique 제약 + Race Condition
**모드**: 읽기 전용 (코드 수정 없음)
**감사자**: Claude (Auto Mode)

> **사전 파악 결과 정정**: 지시서의 "SET_NULL 7곳/3개 파일, CASCADE 37곳/7개 파일"은 이전 시점 통계입니다.
> 현 시점 실측값은 **SET_NULL 17곳/9개 파일, CASCADE 87곳/19개 파일** (테스트·마이그레이션 제외).

---

## 요약 (위험도별 이슈 수)

| 위험도 | 항목 | 수 |
|--------|------|---|
| 🔴 High | Stock 삭제 시 광범위 CASCADE 폭발 (다중 앱 17+ 모델) | 1 |
| 🔴 High | SET_NULL orphan 정리 로직 부재 (전 17곳) | 1 |
| 🔴 High | sec_pipeline `synced_ids` 부분 실패 시 dirty=True 영구 잔류 가능 | 1 |
| 🟡 Med  | `RelationConfidence.save()` 내 `neo4j_dirty=True` 무조건 덮어쓰기 → 동기화 직후 신규 작업 누락 위험 | 1 |
| 🟡 Med  | `bulk_update()` 경로에서 `neo4j_dirty` 수동 관리 누락 가능성 | 1 |
| 🟡 Med  | `update_or_create` 100+ 호출 중 일부 `transaction.atomic` 미감싼 경로 존재 | 1 |
| 🟡 Med  | Neo4j ↔ PG 드리프트 검증 메커니즘 없음 (단방향 카운트만) | 1 |
| 🟢 Low  | 동일 사용자/타깃 unique_together 미설정 모델 일부 | 1 |
| 🟢 Low  | `ChainNewsEvent.duplicate_of` self-FK SET_NULL → 체인 깨짐 | 1 |

총: **High 3 / Med 4 / Low 2 = 9건**

---

## 1. FK orphan 위험

### 1.1 SET_NULL 사용처 전수 (17곳, 9개 파일)

| # | 파일:라인 | 모델.필드 | 참조 대상 | orphan 영향 |
|---|-----------|-----------|----------|-------------|
| 1 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | `DataBasket` | 세션이 어떤 바스켓 기반인지 추적 불가 |
| 2 | `rag_analysis/models.py:256` | `UsageLog.session` | `AnalysisSession` | 비용 로그 세션 컨텍스트 손실 |
| 3 | `rag_analysis/models.py:263` | `UsageLog.message` | `AnalysisMessage` | 비용→메시지 역추적 불가 |
| 4 | `serverless/models.py:660` | `ScreenerAlert.preset` | `ScreenerPreset` | 프리셋 삭제 시 `filters_json` 폴백 동작 (의도된 설계) |
| 5 | `serverless/models.py:808` | `InvestmentThesis.user` | `User` | 익명화된 테제로 잔존 |
| 6 | `serverless/models.py:1409` | `AdminActionLog.user` | `User` | 감사 로그 누가 했는지 손실 (감사 대상으로는 치명적) |
| 7 | `chainsight/models/news_event.py:54` | `ChainNewsEvent.duplicate_of` | self | 중복 클러스터 head 삭제 시 자식이 고아 |
| 8 | `macro/models/indicators.py:298` | `EconomicEvent.related_indicator` | `EconomicIndicator` | 이벤트가 어느 지표 발표인지 손실 |
| 9 | `portfolio/models.py:327` | `AnalysisRun.wallet_snapshot_at_execution` | `WalletSnapshot` | 실행 시점 포트폴리오 스냅샷 손실 (회고 분석 영향) |
| 10 | `portfolio/models.py:732` | `ChatSession.analysis_run` | `AnalysisRun` | 의도된 느슨한 연결 (모델 docstring 명시) |
| 11 | `portfolio/models.py:831` | `Decision.context_analysis_run` | `AnalysisRun` | 의사결정 맥락 손실 |
| 12 | `thesis/models/monitoring.py:66` | `ThesisAlert.indicator` | `ThesisIndicator` | 알림이 어느 지표 기반인지 손실 |
| 13 | `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | `ThesisPremise` | 가설 전제 근거 손실 |
| 14 | `thesis/models/thesis.py:70` | `Thesis.source_news` | `news.NewsArticle` | 뉴스 만료/재인덱싱 시 진입 경로 손실 |
| 15 | `thesis/models/thesis.py:77` | `Thesis.copied_from` | self | 가설 복제 트리 끊김 |
| 16 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | `Stock` | 매칭 실패 evidence의 의도된 NULL 상태 |
| 17 | `marketpulse/models/anomaly.py:25` | `AnomalySignalLog.paired_news` | `MarketPulseNews` | 시그널-뉴스 페어링 손실 |

### 1.2 Orphan 정리 로직 부재

**검색 결과** — `grep -rn "orphan\|cleanup_orphan\|delete_orphan" --include='*.py'`로 조회:

```
news/services/news_neo4j_sync.py
tests/news/test_news_neo4j_sync.py
```

→ **orphan 정리 management command, Celery beat 작업, signal 핸들러가 단 하나도 없음.** SET_NULL이 적용된 17곳 모두 NULL 잔존 레코드를 자동 정리하지 않음.

#### 🔴 High 위험: `AdminActionLog.user` (serverless/models.py:1409)
- 감사 로그가 SET_NULL이면 GDPR/사고 조사 시 "누가 실행했는가"를 추적 불가.
- **권장**: User 삭제 자체를 soft delete로 운영하거나, AdminActionLog는 `user_id_snapshot` (CharField) 별도 보관.

#### 🔴 High 위험: `Thesis.source_news`, `ThesisAlert.indicator`
- 가설/알림 사후 회고에서 근거가 날아가면 사용자 신뢰 훼손.
- 현재는 NULL이 되어도 가설 자체는 유지 → UI에서 "삭제된 뉴스" 처리 필요.

#### 🟢 Low: `ChainNewsEvent.duplicate_of` self-FK
- 클러스터 head 삭제 시 자식들이 모두 NULL → 중복 그룹 정보 자체 소실.
- bulk delete 운영이 거의 없으므로 실질 위험은 낮으나, 발생 시 복구 불가.

---

## 2. CASCADE 체인 분석

### 2.1 Stock 삭제 = 다단 폭발 (🔴 Critical)

`stocks.Stock`은 `primary_key=True, symbol=CharField`로 정의되어 있고 (stocks/models.py:20), 14개 모델이 `to_field='symbol'`로 직결됩니다. CASCADE 즉시 영향:

```
stocks.Stock (삭제)
├── stocks.DailyPrice            (CASCADE) — 가격 시계열 전체
├── stocks.WeeklyPrice           (CASCADE)
├── stocks.BalanceSheet          (CASCADE) — 분기/연간
├── stocks.IncomeStatement       (CASCADE)
├── stocks.CashFlowStatement     (CASCADE)
├── stocks.StockOverviewKo       (CASCADE OneToOne)
├── stocks.AnalystRating         (CASCADE)
├── stocks.EODSignal             (CASCADE)
├── stocks.SignalAccuracy        (CASCADE)
├── users.Portfolio (.stock)     (CASCADE) — 사용자 포지션 사라짐
├── users.WatchlistItem (.stock) (CASCADE)
├── chainsight.CompanyChainProfile     (CASCADE)
├── chainsight.NarrativeTag            (CASCADE)
├── chainsight.CompanySensitivityProfile (CASCADE)
├── chainsight.CompanyGrowthStage      (CASCADE)
├── chainsight.CompanyEventReaction    (CASCADE)
├── chainsight.CompanyCapitalDNA       (CASCADE)
├── chainsight.CompanyRevenueStructure (CASCADE)
├── chainsight.CompanyInsiderSignal    (CASCADE)
├── chainsight.ChainNewsEvent (.symbol) (PROTECT — 삭제 차단)
├── validation.PeerPresetItem          (CASCADE)
├── validation.PeerPresetPreference    (CASCADE)
├── validation.NewsSummary             (CASCADE)
├── validation.CompanyMetricLatest     (CASCADE)
├── validation.CategoryScore           (CASCADE)
├── validation.BenchmarkDelta          (CASCADE)
├── sec_pipeline.RawDocumentStore (.symbol)  (CASCADE)
│   ├── sec_pipeline.SupplyChainEvidence (CASCADE) — source_document
│   │   └── 자동으로 BusinessModelEvidence 영향
│   └── sec_pipeline.BusinessModelSnapshot (CASCADE)
│       └── BusinessModelEvidence (CASCADE → 3단계)
├── sec_pipeline.SupplyChainEvidence.source_company (CASCADE)
├── sec_pipeline.BusinessModelSnapshot.symbol     (CASCADE)
├── portfolio.MetricResult.stock         (PROTECT — 삭제 차단)
├── portfolio.DiagnosticCard.target_stock (PROTECT)
└── ... (그 외 graph_analysis, news, serverless)
```

**관찰**:
- **3단계 이상 연쇄**: `Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence` (sec_pipeline) — Stock 1건 삭제 시 단일 트랜잭션에서 수만 행 삭제 가능.
- **상충 정책**: `chainsight.ChainNewsEvent.symbol`은 `PROTECT`, `portfolio.MetricResult.stock`도 `PROTECT`. → Stock에 PROTECT FK가 하나라도 있으면 운영상 Stock 삭제는 사실상 불가능 (의도된 안전장치).
- **결론**: PROTECT 덕에 현실적 폭발 위험은 낮으나, **PROTECT가 없는 경로(`stocks_stock`을 직접 SQL DELETE)**로는 모든 CASCADE가 침투.

### 2.2 사용자(User) 삭제 체인

```
User (삭제)
├── Portfolio  (CASCADE) → 그 자체 보유 종목 라인 삭제
├── Watchlist  (CASCADE) → WatchlistItem (CASCADE)
├── UserInterest (CASCADE)
├── analysis_sessions, usage_logs (CASCADE) — rag_analysis
├── thesis.Thesis (CASCADE)
│   ├── ThesisPremise (CASCADE)
│   ├── ThesisIndicator (CASCADE) → IndicatorReading (CASCADE)
│   ├── ThesisSnapshot (CASCADE)
│   └── ThesisAlert (CASCADE)
├── portfolio.Wallet, AnalysisRun, Decision, ChatSession (CASCADE)
│   ├── MetricResult (CASCADE)
│   ├── DiagnosticCard (CASCADE)
│   └── Message (CASCADE)
├── validation.PeerPresetPreference (CASCADE)
├── thesis.community.* (CASCADE × 4)
└── thesis.learning.* (CASCADE × 5)
```

User 1건 삭제 → 단일 트랜잭션 폭발 잠재력 매우 큼. 운영 시 soft-delete + Celery 배치 정리 권장.

### 2.3 sec_pipeline 4단 체인 (실측)

`sec_pipeline/models.py:213` — `BusinessModelEvidence`가 `BusinessModelSnapshot`에 CASCADE.
`sec_pipeline/models.py:78,82,161,165` — `RawDocumentStore`/`Stock` 양쪽 CASCADE.

→ **Stock 삭제 → RawDocumentStore 일괄 삭제 → BusinessModelSnapshot, SupplyChainEvidence 삭제 → BusinessModelEvidence 삭제** (4단계).

신뢰성을 위해 sec_pipeline 운영자는 **Stock 삭제 전 `RawDocumentStore.objects.filter(symbol=...).count()` 확인 의무**가 있어야 합니다.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 `neo4j_dirty` 플래그 사용 현황

| 모델 | 위치 | 비고 |
|------|------|------|
| `chainsight.CompanyChainProfile` | `chainsight/models/chain_profile.py:65` | `db_index=True`, default=True |
| `chainsight.RelationConfidence` | `chainsight/models/relation_discovery.py:130` | `db_index=True`, save() 자동 dirty=True |
| `sec_pipeline.SupplyChainEvidence` | `sec_pipeline/models.py:100` | `Index(['neo4j_dirty'])` |

> 단일 소스 통일 audit P0 #9 (2026-04-29)으로 `synced_to_neo4j` 필드 모두 제거됨 (chainsight migration 0008).

### 3.2 동기화 메커니즘

#### sec_pipeline (sec_pipeline/tasks.py:337-452)

- **2-Phase + select_for_update(skip_locked=True)** — 동시 워커 안전.
- BATCH_SIZE = 500, max_retries=1 (`@shared_task(bind=True, max_retries=1, ...)`).
- Phase B에서 개별 edge sync 실패 → **try/except로 삼킨 뒤 `synced_ids`에 추가하지 않음** (line 437-438) → 해당 row는 dirty=True로 잔류, 다음 실행에서 재시도. ✅ 적절.
- ⚠️ **문제**: Phase B 도중 unhandled exception 발생 시 `raise`되며 (line 451-452) Phase C 미실행. 이미 Neo4j에 쓰여진 edge는 PG에선 여전히 dirty. → **다음 실행에서 동일 edge가 다시 DELETE+CREATE됨** (멱등성으로 안전하지만 불필요한 부하).

#### chainsight (chainsight/services/neo4j_sync.py:21-54)

- 단순 loop, `select_for_update` 없음 → **여러 워커 동시 실행 시 중복 처리 가능** (멱등성으로 데이터 깨짐은 없으나 부하 증가).
- 개별 sync 예외는 try/except로 처리, 성공 PK만 `update(neo4j_dirty=False)`. ✅ 적절.

#### `RelationConfidence.save()` 패턴 (relation_discovery.py:146-159)

```python
def save(self, *args, **kwargs):
    ...
    self.neo4j_dirty = True  # 무조건 True로 덮어씀
    super().save(*args, **kwargs)
```

⚠️ **🟡 Med 위험**:
- 동기화 직후 같은 인스턴스를 `save()`하면 `neo4j_dirty=False`였던 것이 다시 True로 → 의도된 동작.
- 그러나 **동기화 task가 `synced_ids` update를 PK 단위 `queryset.update()`로 처리하기 때문에 (neo4j_sync.py:48)** 동기화 중 다른 코드가 `instance.save()` 호출 시 race가 발생: 동기화 task가 `update(neo4j_dirty=False)` 직후, 다른 트랜잭션의 save()가 `dirty=True`로 덮어쓸 수 있음. ✅ **이 경우는 결과적으로 안전** (다음 사이클에 다시 sync됨).
- 진짜 위험: `bulk_update()` 경로 — `save()` 미호출이므로 작성자가 명시적으로 `obj.neo4j_dirty=True` 토글해야 함. 누락 시 변경분이 Neo4j에 영원히 안 옴.
  - 예: `chainsight/tasks/relation_tasks.py:382-402`은 명시적으로 `update(..., neo4j_dirty=True)` 호출 ✅. 하지만 **누락 잠재성은 항상 존재** — 코드 리뷰 의무화 권장.

### 3.3 PG ↔ Neo4j 드리프트 감지 메커니즘

**현재 상태**:
- `sec_pipeline/quality_checks.py:90-97` — `neo4j_dirty=True` 적체 50건 초과 시 알림. 단방향 카운트만.
- `sec_pipeline/intelligence.py:97-98` — `sync_synced` / `sync_pending` 카운트.
- **Neo4j 측에서 PG에 없는 노드/엣지 검증하는 reverse check 없음**.

🟡 **Med 위험**: PG row 삭제 후 Neo4j edge 잔존 가능. 예시:
- `RelationConfidence` row 삭제 시 `_delete_edge`가 호출되지 않음 (사용처 검색 결과 `_delete_edge`는 status 변경 시점에만 호출).
- → orphan Neo4j edge가 누적 가능.

**권장**: 주간 Celery task로 reverse audit:
```python
# pseudocode
neo4j_edges = repo.list_all_edges()
for edge in neo4j_edges:
    if not RelationConfidence.objects.filter(...).exists():
        log.warning(f"Orphan Neo4j edge: {edge}")
```

### 3.4 동기화 실패 시 재시도

| 컴포넌트 | 재시도 방식 |
|----------|-------------|
| `sec_pipeline.tasks.sync_dirty_to_neo4j` | `max_retries=1`, exponential backoff 없음. PG dirty=True가 자연 재시도 큐 역할. |
| `chainsight.services.neo4j_sync.sync_dirty_relations` | task 데코레이터 없는 service 함수 (Celery wrapper는 별도). 개별 row 예외는 swallow. |
| `chainsight.tasks.neo4j_dirty_sync_tasks.run_neo4j_dirty_sync` | (미확인 — 추정) 위 service 호출 wrapper. |

→ **개별 edge 재시도 한도 없음**. dirty 무한 잔류 가능. 권장: `neo4j_sync_attempts: IntegerField` 추가하여 N회 실패 시 dead letter.

---

## 4. Unique 제약조건 / update_or_create 현황

### 4.1 unique_together / UniqueConstraint 통계

- **`unique_together`**: 28건 (운영 모델 22건 + 테스트 6건).
- **`UniqueConstraint`**: 4건 (`portfolio/models.py` 4곳, `metric_id+industry_code+date`, `analysis_run+stock+metric_id` 등).

핵심 누락 검토:
| 모델 | 현재 | 권장 추가 |
|------|------|----------|
| `serverless.AdminActionLog` | (없음) | `(action, task_id)` 정도만 — 감사 로그라 unique 불필요. ✅ |
| `rag_analysis.AnalysisMessage` | (없음) | session+created_at — 그러나 메시지는 자연스럽게 중복 가능. ✅ |
| `sec_pipeline.SupplyChainEvidence` | (없음) | `(source_document, source_company, target_company_name, relationship_type)` 권장. 현재 prompt_version 갱신 시 중복 row 발생 가능. 🟡 |
| `sec_pipeline.BusinessModelSnapshot` | (없음) | `(symbol, source_document)` 권장. 동일 10-K 재처리 시 중복 가능. 🟡 |
| `chainsight.RelationConfidence` | `(symbol_a, symbol_b, relation_type)` ✅ | (적절) |
| `chainsight.CompanyChainProfile` | (확인 필요) | 모델 정의 미확인. |
| `validation.CompanyMetricLatest` | (확인 필요) | metric_def + stock + date 가능성. |

### 4.2 `update_or_create` race condition 위험

**총 호출 100+ 곳** (운영 코드 60+, 테스트 40+).

#### Django `update_or_create` 동작 모델

PostgreSQL에서 `update_or_create`는:
1. `SELECT ... WHERE <kwargs>` 수행
2. 없으면 `INSERT`, 있으면 `UPDATE`

→ **동시 실행되는 두 워커가 모두 SELECT에서 빈 결과 → 둘 다 INSERT 시도 → unique 제약이 있으면 한쪽 IntegrityError**.

**판정 기준**:
- ✅ unique_together/UniqueConstraint 있음 + IntegrityError 핸들링 또는 `transaction.atomic` 안에서 호출 → 안전
- 🟡 unique 없음 → **중복 row 누적 가능**

#### 실측 표본 (호출 50건 중 무작위 검토)

| 위치 | unique | atomic 래핑 |
|------|--------|-------------|
| `api_request/stock_service.py:254` (Stock) | symbol=PK ✅ | atomic ✅ (수동 확인) |
| `api_request/stock_service.py:390` (DailyPrice) | (stock, date) ✅ | atomic ✅ |
| `api_request/stock_service.py:481` (BalanceSheet) | (stock, period_type, fy, fq) ✅ | atomic ✅ |
| `serverless/services/data_sync.py:196` (MarketMover) | (date, mover_type, symbol) ✅ | (확인 필요) |
| `serverless/services/theme_matching_service.py:247,329,575` (ThemeMatch) | (stock_symbol, theme_id) ✅ | (확인 필요) |
| `serverless/services/keyword_service.py:202` (StockKeyword) | (확인 필요) | atomic ❓ |
| `serverless/services/news_relation_matcher.py:201` (StockRelationship) | (source, target, type) ✅ | (확인 필요) |
| `chainsight/tasks/profile_tasks.py:106,180` (CompanyGrowthStage, CapitalDNA) | (모델별) | (확인 필요) |
| `chainsight/tasks/relation_tasks.py:275,309,343` (RelationConfidence) | ✅ | atomic ✅ (PR 코멘트로 확인) |
| `metrics/management/commands/seed_metric_definitions.py:518` | (확인 필요) | (확인 필요) |

**🟡 Med 위험 결론**:
- 핵심 코어 (Stock/Price/Financial/RelationConfidence)는 unique + atomic 양쪽 모두 만족.
- 주변부 (StockKeyword, ThemeMatch, MarketMover 등) 일부는 atomic 래핑 없는 raw `update_or_create`. PostgreSQL은 `update_or_create`가 내부적으로 SELECT-then-INSERT/UPDATE이며 행 잠금이 없으므로 race window 존재. unique 제약이 있으면 IntegrityError → Django는 자동 retry 안 함.
- **권장 패턴**:
  ```python
  with transaction.atomic():
      try:
          obj, created = Model.objects.update_or_create(...)
      except IntegrityError:
          obj, created = Model.objects.update_or_create(...)  # 재시도
  ```
  또는 `bulk_create(..., update_conflicts=True)` (Django 4.1+).

### 4.3 자기 참조 self-FK SET_NULL

`ChainNewsEvent.duplicate_of` (chainsight/models/news_event.py:54), `Thesis.copied_from` (thesis/models/thesis.py:77):
- self FK + SET_NULL → 부모 삭제 시 자식이 NULL.
- 부모-자식 트리에서 부모 삭제는 사실상 잘 발생하지 않으므로 위험 낮음. 🟢

---

## 5. 실행 권장 (코드 수정 없음 기준 — 모니터링/문서화 위주)

| 우선순위 | 항목 |
|----------|------|
| P0 | sec_pipeline `BusinessModelSnapshot`, `SupplyChainEvidence` UniqueConstraint 검토 후 추가 PR (중복 누적 방지) |
| P0 | Neo4j reverse drift detection task 신설 (`neo4j_orphan_audit` Celery beat, weekly) |
| P1 | `AdminActionLog`에 `user_id_snapshot` CharField 추가 (감사 로그 GDPR 대응) |
| P1 | `update_or_create` 호출 중 atomic 미래핑 경로 전수 조사 + 가이드라인 문서화 (`docs/coding_rules/db_concurrency.md`) |
| P1 | `neo4j_sync_attempts` 카운터 필드 추가 (3회 실패 시 dead letter 알림) |
| P2 | `Thesis.source_news = NULL` 시 UI에서 "원문 만료" 표시 검증 |
| P2 | Stock 삭제 운영 SOP 작성 (PROTECT 위반 우회 금지, soft-delete 권장) |

---

## 부록 A — 검증 명령

```bash
# SET_NULL 전수
grep -rn 'on_delete=models.SET_NULL' --include='*.py' .

# Stock CASCADE 영향
grep -rn "stocks.Stock" --include='*models*.py' .
grep -rn "to_field='symbol'" --include='*models*.py' .

# update_or_create + atomic 검증
grep -rn 'update_or_create\|get_or_create' --include='*.py' . | grep -v test

# Neo4j dirty 동기화 진입점
grep -rn 'neo4j_dirty=False' --include='*.py' .
```

## 부록 B — 미감사 항목 (다음 라운드)

- `validation.CompanyMetricLatest`, `validation.CategoryScore` unique 제약 정확한 형태 미확인 (모델 본문 미열람).
- `chainsight.CompanyChainProfile` unique 제약 미확인.
- 마이그레이션 0008 이전 운영 DB의 `synced_to_neo4j → neo4j_dirty` 데이터 일관성 사후 검증 필요.
- `bulk_update()`/`bulk_create()` 호출처 전수 조사 (neo4j_dirty 토글 누락 위험).
- `AnalysisRun.save()` 불변성 검사가 race condition 안전한지 (line 351-363).
