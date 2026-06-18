# 데이터 무결성 감사 보고서

> **감사 일자**: 2026-06-18
> **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis`
> **감사 범위**: FK orphan · CASCADE 연쇄 · Neo4j↔PG 동기화 · Unique 제약 / race condition
> **방식**: 읽기 전용 정적 분석 (코드 미수정)

---

## ⚠️ 구조 차이 선결 고지

감사 지시서는 평면 구조(`sec_pipeline/models.py`, `serverless/models.py` 등)와 다음 수치를 가정했으나, 실제 코드베이스는 **모노레포로 리모델링**되어 경로·수치가 다르다.

| 항목 | 지시서 가정 | **실측** |
|------|------------|---------|
| SET_NULL | 7곳 / 3개 파일 | **17곳 / 11개 파일** |
| CASCADE | 37곳 / 7개 파일 | **97곳 / 다수 파일** |
| PROTECT | (미언급) | **7곳** |
| 모델 경로 | `<app>/models.py` 평면 | `packages/shared/*`, `apps/*`, `services/*`, `thesis/*`, `macro/*` 분할 |

> 본 보고서는 **실측 기준**으로 작성한다. 지시서 수치로 카운트를 맞추지 않았다.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 **High** | 5 | ① SEC 4단계 연쇄(Stock→RawDocumentStore→…→BusinessModelEvidence, 복구불가 원문 소실) ② User→Wallet/Portfolio→AnalysisRun→MetricResult 5단계(수만 행) ③ MetricDefinition→메트릭 캐시 광역 연쇄(시스템 마비) ④ orphan 정리 로직 전무(InvestmentThesis.user / ThesisIndicator.premise) ⑤ Neo4j 엣지(관계) 무결성 검증 부재 |
| 🟡 **Medium** | 6 | ① User→Thesis→…→IndicatorReading 5단계 ② Stock→EODSignal/SignalAccuracy 고용량 시계열 ③ neo4j sync max_retries=1(2회만) ④ dirty 플래그 누적 모니터링 부재 ⑤ update_or_create 대부분 `transaction.atomic()` 미적용 ⑥ SupplyChainEvidence orphan은 재매칭만 있고 TTL/정리 없음 |
| 🟢 **Low / 양호** | — | SET_NULL 17곳 전부 `null=True` 정상 / 모든 update_or_create lookup 키가 unique 제약으로 보호 / Stock 핵심 데이터 일부 PROTECT 적용 / neo4j_dirty 단일 소스 통일(2026-04-29) |

**총평**: race condition은 unique 제약으로 잘 막혀 있으나, **CASCADE 남용으로 인한 복구 불가능 대량 삭제 위험**과 **orphan/엣지 정리·검증 로직 부재**가 핵심 부채다.

---

## FK orphan 위험

### SET_NULL 전수 (17곳) — `null=True` 위반은 0건 ✓

모든 SET_NULL FK가 `null=True`를 명시하여 **무결성 위반(SET_NULL인데 NOT NULL) 사례는 없음**. 다만 NULL이 된 후 **orphan을 정리하는 로직이 거의 없다**.

| # | 모델.필드 → 부모 | 파일:라인 | 정책 평가 |
|---|------------------|-----------|-----------|
| 1 | `EconomicEvent.related_indicator` → EconomicIndicator | macro/models/indicators.py:310 | 🟢 합리적 |
| 2 | `ThesisAlert.indicator` → ThesisIndicator | thesis/models/monitoring.py:66 | 🟢 경고는 기록 |
| 3 | `ThesisIndicator.premise` → ThesisPremise | thesis/models/indicator.py:15 | 🔴 지표가 premise 없이 고아화 |
| 4 | `Thesis.source_news` → NewsArticle | thesis/models/thesis.py:70 | 🟢 합리적 |
| 5 | `Thesis.copied_from` → Thesis(self) | thesis/models/thesis.py:77 | 🟢 합리적 |
| 6 | `ChainNewsEvent.duplicate_of` → ChainNewsEvent(self) | apps/chain_sight/models/news_event.py:69 | 🟢 합리적 |
| 7 | `AnalysisRun.wallet_snapshot_at_execution` → WalletSnapshot | apps/portfolio/models.py:341 | 🟡 기록 무결성 |
| 8 | `ChatSession.analysis_run` → AnalysisRun | apps/portfolio/models.py:768 | 🟡 기록 보존이면 OK |
| 9 | `Decision.context_analysis_run` → AnalysisRun | apps/portfolio/models.py:870 | 🟢 의사결정 추적 |
| 10 | `AnomalySignalLog.paired_news` → MarketPulseNews | apps/market_pulse/models/anomaly.py:35 | 🟢 감시 기록 |
| 11 | `AnalysisSession.basket` → DataBasket | services/rag_analysis/models.py:132 | 🟡 세션 정책 명확화 필요 |
| 12 | `UsageLog.session` → AnalysisSession | services/rag_analysis/models.py:232 | 🟢 감시 기록 |
| 13 | `UsageLog.message` → AnalysisMessage | services/rag_analysis/models.py:239 | 🟢 감시 기록 |
| 14 | `ScreenerAlert.preset` → ScreenerPreset | services/serverless/models.py:660 | 🟢 커스텀 필터 유지 |
| 15 | `InvestmentThesis.user` → User | services/serverless/models.py:797 | 🔴 사용자 삭제 후 테제 고아(프라이버시) |
| 16 | `AdminActionLog.user` → User | services/serverless/models.py:1353 | 🟢 감사 추적 |
| 17 | `SupplyChainEvidence.target_company` → Stock | services/sec_pipeline/models.py:94 | 🟡 재매칭 사이클 필요 |

### orphan 정리 로직 존재 여부

**대부분 부재.** 발견된 NULL-FK 관련 로직은 다음뿐이다.

- `services/sec_pipeline/management/commands/rematch_unmatched.py:34,52` — `SupplyChainEvidence.objects.filter(target_company__isnull=True)` **재매칭만** 수행, 삭제·정리 없음
- `services/sec_pipeline/quality_checks.py:142` — `target_company__isnull=True` **카운트 모니터링만**
- `services/serverless/tasks.py:905`, `config/tasks.py:140` — 만료 캐시/TaskResult 정리 (**NULL FK 정리 아님**)

| orphan 대상 | 정리 로직 | 위험도 |
|-------------|-----------|--------|
| `InvestmentThesis.user=NULL` | 없음 | 🔴 높음(프라이버시) |
| `ThesisIndicator.premise=NULL` | 없음 | 🔴 높음(지표 고아) |
| `AnalysisRun.wallet_snapshot=NULL` | 없음 | 🟡 기록 무결성 |
| `SupplyChainEvidence.target_company=NULL` | 재매칭만 | 🟡 TTL/정리 없음 |
| `AnalysisSession.basket=NULL` | 없음 | 🟡 |
| `AdminActionLog.user=NULL` / `ChatSession.analysis_run=NULL` | 없음 | 🟢 기록 목적 |

**권고**: ① `InvestmentThesis.user`·`ThesisIndicator.premise` NULL 상태 정책 결정(삭제 vs 보존) ② NULL FK 레코드 주기적 카운트 리포팅 태스크 ③ 보존 데이터에는 TTL(예: 90일 grace) 도입 검토.

---

## CASCADE 체인

총 **97개 CASCADE**. 3단계 이상 연쇄 **5개 식별**. PROTECT 7곳이 Stock 등 핵심 데이터 일부를 방어 중.

### Stock 삭제 시 직접 영향 (Level 1, 20개 모델)

가장 많은 FK 참조 대상. Stock 1건 삭제 시 직접 연쇄되는 주요 자식:

| 자식 모델 | 파일:라인 | 비고 |
|-----------|-----------|------|
| DailyPrice / WeeklyPrice | stocks/models.py:194 / :306 | 🔴 종목당 수천 행(시계열) |
| EODSignal / SignalAccuracy | stocks/models.py:1015 / :1063 | 🔴 매일 생성, 수년치 |
| StockOverviewKo / EODDashboardSnapshot | stocks/models.py:946 / :1153 | 🟡 |
| Portfolio / WatchlistItem | users/models.py:47 / :223 | 🟡 사용자 데이터 |
| CompanyChainProfile / RevenueStructure / InsiderSignal / AttentionScore | apps/chain_sight/models/* | 🟡 1:1·1:N 프로파일 |
| PeerPreset / UserPeerPreference / CompanyMetricLatest / CategorySignal | services/validation/models/* | 🟡 |
| **RawDocumentStore** | services/sec_pipeline/models.py:24 | 🔴 아래 다단 연쇄의 기점 |
| SupplyChainEvidence(source) / BusinessModelSnapshot | services/sec_pipeline/models.py:86 / :173 | 🔴 |

> 단, `WalletHolding`(portfolio:92), `MetricResult`(:409), `DiagnosticCard`(:519), `LLMComment`(:594)는 Stock에 대해 **PROTECT**로 설정되어 Stock 직접 삭제를 차단 ✓.

### 3단계 이상 연쇄 체인 (5건)

**① 🔴 SEC 파이프라인 (최대 4단계, 복구 불가)**
```
Stock → RawDocumentStore (sec_pipeline/models.py:24)
          ├─ SupplyChainEvidence (:82)
          └─ BusinessModelSnapshot (:179)
                └─ BusinessModelEvidence (:241)
```
Stock 1건 → 원문(RawDocumentStore) 수십 + Evidence 수백 + Snapshot 연도별 + Evidence 필드별 = **수천 행**. SEC filing **원문 소실은 복구 불가**.

**② 🔴 포트폴리오 분석 (최대 5단계, 수만 행)**
```
User → Wallet (portfolio/models.py:53) / Portfolio (:231)
        → AnalysisRun (:305)
            ├─ MetricResult (:404)
            ├─ DiagnosticCard (:508)
            ├─ LLMComment (:589)
            └─ StoredAnalysis (:650)
User → Wallet → WalletSnapshot (:169)
```
`MetricResult` = AnalysisRun수 × 지표수 × 종목수 → **수만 행** 가능.

**③ 🟡 Thesis (최대 5단계)**
```
User → Thesis (thesis/models/thesis.py:11)
        → ThesisPremise (:146)
            → ThesisIndicator (indicator.py:13)
                → IndicatorReading (indicator.py:122)
```
IndicatorReading은 일별 기록 → 수천 행.

**④ 🔴 메트릭 정의 광역 연쇄 (2단계, 시스템 마비급)**
```
MetricDefinition → CompanyMetricLatest (validation/models/metric_latest.py:14)
                 → IndustryMetricBenchmark (metrics/models/benchmark.py:74)
```
메트릭 정의 1건 삭제 → **모든 회사 최신값 + 업종 벤치마크** 소실 → 평가 기능 마비.

**⑤ 🟡 거시 지표 카탈로그 연쇄**
```
EconomicIndicator → SectorIndicatorRelation (macro/relationships.py:31)
                  → IndicatorCorrelation (:119,:123)
                  → MacroIndicatorValue (macro/indicators.py:100)
```
공유 카탈로그성 지표가 부모인데 CASCADE → 관계·시계열 동반 소실.

### 위험한 패턴 — 공유/카탈로그 데이터의 CASCADE
- `MetricDefinition`, `EconomicIndicator` 등 **다수가 참조하는 메타데이터**를 CASCADE 부모로 둠 → 1건 삭제가 광역 소실로 전파.
- **권고**: 복구 불가/광역 참조 데이터(SEC 원문, 메트릭 정의, 분석 결과)는 `PROTECT` 또는 soft-delete/archive 패턴으로 전환. 사용자 삭제 시 retention policy(grace period) 명문화.

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황 (단일 소스 통일 완료)

`migration 0008_unify_neo4j_flags`(2026-04-29)로 레거시 `synced_to_neo4j`/`neo4j_synced` 제거, **`neo4j_dirty`(True=동기화필요) 단일 소스화**.

| 모델 | 필드 정의 위치 |
|------|---------------|
| RelationConfidence | apps/chain_sight/models/relation_discovery.py:147 (`save()`에서 항상 True 세팅 :179) |
| CompanyChainProfile | apps/chain_sight/models/chain_profile.py:82 |
| SupplyChainEvidence | services/sec_pipeline/models.py:111 (주석: "synced_to_neo4j 금지") |

- **True(dirty) 세팅**: save() 자동(:179), seed/매칭/신호 처리(`tasks.py:384`, `signals.py:53`, `ticker_matcher.py:171`) 등
- **False(clear) 세팅**: 동기화 성공 건만 `queryset.update(neo4j_dirty=False, neo4j_synced_at=now())` — `neo4j_sync.py:49`, `sec_pipeline/tasks.py:521`, `sync_tasks.py:161`

### 동기화 실패 시 재시도

- 동기화 태스크: `run_neo4j_dirty_sync`(max_retries=2, delay=60 고정), `sync_dirty_to_neo4j`(**max_retries=1**), `sync_profiles_to_neo4j`(**max_retries=1**)
- **자동 재시도 구조 ✓**: 개별 건 실패 시 `synced_pks/ids`에 미포함 → `neo4j_dirty=True` 유지 → 다음 회차 재처리.
- **2-Phase 트랜잭션**(sec_pipeline/tasks.py:426~): Phase A `select_for_update(skip_locked=True)` PG 락(최대 500건) → Phase B Neo4j DELETE+CREATE(MERGE 금지) → Phase C 성공분만 PG flag clear. 부분 실패는 다음 회차로 격리.
- 🟡 **한계**: 상위 sync 태스크 `max_retries=1`로 낮음 + exponential backoff 비일관(하위 collect 단계만 적용). 일시적 Neo4j 다운 시 대량 미동기화 진입 가능.

### PG ↔ Neo4j 불일치 감지

`packages/shared/metrics/services/daily_report.py:288~373` 가 **일일 배치**로 커버리지 갭 감지:
- Stock / Industry / Sector **노드** 차집합(`pg - neo4j`), CompanyChainProfile 미반영, UnmatchedCompanyQueue(status=pending) 리포팅
- 갭 발견 시 권장 action 제시(`seed_neo4j_graph 재실행`, `sync_profiles_to_neo4j 트리거`) — **자동 재조정 아님, 수동 실행**

🔴 **핵심 공백**:
1. **관계(엣지) 무결성 검증 없음** — 노드만 비교. RelationConfidence/SupplyChainEvidence ↔ Neo4j 엣지 카운트 미검증 → 손상/누락 엣지 미감지.
2. **dirty 누적 모니터링 없음** — `neo4j_dirty=True` 적체 추세 미관측.
3. **일일 배치만** — 실시간 감지 없음, 대량 실패 시 최소 1일 후 인지.

**권고**: ① 일일 리포트에 엣지 카운트 비교 + `neo4j_dirty=True` 개수 추가 ② sync 태스크 max_retries 상향 + backoff 통일 ③ 동기화 대기열 임계 알림.

---

## Unique 제약조건

### 현황 — race condition은 사실상 unique 제약으로 방어됨 🟢

`unique_together`/`UniqueConstraint`가 **도메인 전반에 촘촘히 설정**되어 있다 (주요 예):

| 도메인 | 모델 / unique 키 (파일:라인) |
|--------|------------------------------|
| stocks | DailyPrice `[stock,date]`(:246), WeeklyPrice `[stock,date]`(:275) |
| validation | PeerPreset `[symbol,preset_key]`(peer_preset.py:41), MetricLatest `[symbol,metric_code]`(metric_latest.py:57), CategoryScore `[symbol,category,fiscal_year,preset_key]`(category_score.py:64), BenchmarkDelta `[symbol,fiscal_year,metric_code,preset_key]`(benchmark_delta.py:80) |
| sec_pipeline | RawDocumentStore `accession_no`(:30), CompanyAlias `[alias,context_sector]`(:331) |
| news | NewsArticle `url`(:41), NewsEntity `[news,symbol]`(:221), SentimentHistory `[symbol,date]`(:291) |
| serverless | MarketMover `[date,mover_type,symbol]`(:100), StockKeyword `[symbol,date]`(:226), ETFHolding `[etf,stock_symbol,snapshot_date]`(:1069), InstitutionalHolding `[institution_cik,stock_symbol,report_date]`(:1331) |
| market_pulse | BreadthSnapshot `[date,universe]`, RegimeSnapshot `[date]`, BriefingLog/TranslationLog `[date,model_version]` |
| chain_sight | DiscoveredRelation `[symbol_a,symbol_b]`(:25), PriceCoMovement `[symbol_a,symbol_b,period]`(:54) |
| macro | IndicatorValue `[indicator,date]`(:133), IndicatorCorrelation `[indicator_a,indicator_b]`(:165) |
| thesis | ThesisSnapshot `[thesis,asof_date]`(monitoring.py:29), ThesisKeywordCache `[target,source,text]`(keyword.py:42) |

- **부분 unique index(condition=)**: 미사용
- **bulk_create(ignore_conflicts)**: 프로덕션 코드 없음(테스트만)

### update_or_create race condition 분석

조사한 모든 `update_or_create` 호출의 **lookup 키가 위 unique 제약과 일치** → 동시 호출 시 DB UniqueViolation으로 중복 방어됨. **Critical 0건.**

| 호출처 | lookup 키 | unique 보호 | atomic | 동시성 |
|--------|-----------|:-----------:|:------:|--------|
| SentimentHistory (news/tasks.py:314) | symbol,date | ✓ | ✗ | 낮음 |
| NewsEntity (news/services/aggregator.py:393) | news,symbol | ✓ | ✗ | 중간 |
| RawDocumentStore (sec_pipeline/tasks.py:138) | accession_no | ✓ | ✗ | 중간 |
| StockKeyword (serverless/tasks.py:414) | symbol,date | ✓ | ✗ | **높음(배치병렬)** |
| RelationConfidence (sec_pipeline/tasks.py:372) | (migration 확인) | △ | ✗ | 중간 |
| PeerPreset ×6 (validation/preset_generator.py:129~510) | symbol,preset_key | ✓ | ✗ | 배치순차 |
| MarketBreadth (serverless/market_breadth_service.py:122) | date | ✓ | **✓** | — |

🟡 **개선 여지**: 대부분 `transaction.atomic()` 미적용 — unique 제약이 막아주므로 데이터 중복은 없으나, `update_or_create`의 get→create 사이 race 시 IntegrityError 예외가 그대로 태스크를 실패시킬 수 있다. 동시성 높은 `StockKeyword`, 기록형 `SentimentHistory`/`ThesisSnapshot`, 다회 호출 `PeerPreset`는 `atomic()` 래핑 권장. `MarketBreadth`가 모범 사례(atomic 적용).

---

## 부록 — 우선순위 권고 요약

| 순위 | 조치 | 대상 |
|------|------|------|
| 1 | 복구불가/광역 데이터 CASCADE → PROTECT/soft-delete | SEC RawDocumentStore 체인, MetricDefinition 체인 |
| 2 | orphan 정리/정책 수립 | InvestmentThesis.user, ThesisIndicator.premise (+ NULL FK 카운트 리포트) |
| 3 | Neo4j 엣지 무결성 검증 + dirty 누적 모니터링 | daily_report 확장 |
| 4 | 사용자 삭제 retention policy 명문화 | User → 12+ 자식 체인 |
| 5 | sync 태스크 max_retries 상향 + backoff 통일 | sync_dirty_to_neo4j, sync_profiles_to_neo4j |
| 6 | 동시성 높은 update_or_create에 transaction.atomic() | StockKeyword, SentimentHistory, ThesisSnapshot, PeerPreset |

> 본 보고서는 정적 분석 기준이며 코드를 수정하지 않았다. 라인 번호는 감사 시점(2026-06-18) 기준.
