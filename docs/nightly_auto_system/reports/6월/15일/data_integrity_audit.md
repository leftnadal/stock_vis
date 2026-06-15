# 데이터 무결성 감사 보고서

> **범위**: PostgreSQL FK 무결성 · CASCADE 연쇄 · Neo4j↔PG 동기화 · Unique 제약/race
> **작성일**: 2026-06-15 (야간 자동 감사)
> **모드**: 읽기 전용 — 코드 수정 없음
> **저장소 구조 주의**: 모노레포 재편으로 실제 경로는 `packages/shared/`, `services/`, `apps/`, `thesis/`, `macro/`에 분산. 지시서가 가정한 경로/건수(SET_NULL 7곳·3파일, CASCADE 37곳·7파일)는 **구버전 기준**이며, 현재 실측은 **SET_NULL 19곳 / CASCADE 96곳 / PROTECT 7곳**.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|-----------|
| 🔴 High | 3 | ① Stock 삭제 시 Neo4j 노드/엣지 고아화 (CASCADE→Neo4j 미전파) · ② SET_NULL된 `target_company`의 Neo4j 엣지 stale 잔존 · ③ PG↔Neo4j 정합성 대조(reconcile) 잡 부재 |
| 🟠 Medium | 4 | ④ Stock 단일 삭제가 8개 앱·15+ 테이블로 광역 연쇄 · ⑤ 3단계 CASCADE 체인 4건 · ⑥ `update_or_create` 비원자성 race(unique 없는 대상) · ⑦ SET_NULL 고아 레코드 정리 잡 부재 |
| 🟡 Low | 3 | ⑧ rag/serverless SET_NULL은 감사로그 의도적 보존(정상) · ⑨ unique_together 커버리지 양호(race 시 IntegrityError로 방어) · ⑩ neo4j_dirty 단일소스 패턴 정착(양호) |

**총평**: PG 내부 FK 무결성과 unique 제약은 **양호**(대부분 의도적 설계, dirty-flag 재시도 견고). 가장 큰 구조적 위험은 **PG→Neo4j 단방향 동기화의 삭제 미전파** — create/update만 `neo4j_dirty`로 추적되고 **DELETE는 어디서도 Neo4j에 반영되지 않아** 좀비 노드/엣지가 누적될 수 있다.

---

## FK orphan 위험

### SET_NULL 사용처 (실측 19곳)

| 파일 | 모델.필드 | 보존 메커니즘 | 정리 잡 | 평가 |
|------|-----------|---------------|---------|------|
| `services/sec_pipeline/models.py:94` | `SupplyChainEvidence.target_company` | `target_company_name`(CharField)에 이름 문자열 보존 + `UnmatchedCompanyQueue` + `rematch_unmatched` 커맨드 | 재매칭 커맨드 존재 | 🟠 PG는 안전하나 **Neo4j 엣지 stale**(아래) |
| `services/rag_analysis/models.py:132` | `AnalysisSession.basket` | 세션은 유지, 바스켓만 끊김 | 없음 | 🟡 의도적(탐험기록 보존) |
| `services/rag_analysis/models.py:232,239` | `TokenUsageLog.session/message` | 사용량 감사로그 보존 | 없음 | 🟡 의도적(과금 감사) |
| `services/serverless/models.py:660` | `ScreenerAlert.preset` | `filters_json`로 폴백(커스텀 필터) | 없음 | 🟢 폴백 설계 양호 |
| `services/serverless/models.py:797,1353` | `InvestmentThesis.user`, `AdminActionLog.user` | 사용자 삭제돼도 테제/감사로그 보존 | 없음 | 🟡 의도적(감사 추적) |
| `macro/`, `thesis/`, `apps/market_pulse/`, `apps/portfolio/`, `apps/chain_sight/news_event.py` | (지표/스냅샷/뉴스이벤트 FK) | 대부분 null 허용 메타 참조 | 없음 | 🟡 의도적 |

### orphan 레코드 정리 로직 존재 여부

- **SET_NULL로 null화된 PG 레코드 전용 정리(cleanup) 잡은 없음.** 다만 위 대부분은 **의도적 보존**(감사로그·탐험기록·이름 문자열 보존)이므로 즉시 위험은 아님.
- 유일하게 능동적 고아 정리가 있는 곳은 **Neo4j 측 뉴스**: `services/news/services/news_neo4j_sync.py`
  - `cleanup_expired_relationships()` — 만료 관계 삭제 + 고립 `:NewsEvent` 노드 정리(`orphan_query`, line 707).
- **결론**: PG 측 SET_NULL 고아는 설계상 허용. 위험은 PG가 아니라 **Neo4j 측 stale 엣지**(High ②)에 집중.

---

## CASCADE 체인

### Stock 삭제 영향 범위 (최다 FK 참조: 38건)

`Stock`(PK=`symbol`)은 전 코드베이스에서 가장 많이 참조되는 노드. 단일 Stock 삭제 시 **CASCADE로 8개 앱·15+ 테이블이 연쇄 삭제**:

| 앱 | CASCADE 삭제 대상 |
|----|-------------------|
| `packages/shared/stocks` | DailyPrice(194), 주간가격(306), 재무3종(인용), EODSignal(1015·1063), KoreanOverview |
| `packages/shared/users` | Portfolio(47), WatchlistItem(223) |
| `packages/shared/metrics` | CompanyMetricSnapshot, PeerMetricBenchmark(benchmark.py:12·122) |
| `services/validation` | CompanyMetricLatest, CategorySignal, CompanyBenchmarkDelta, ValidationNewsSummary, PeerPreset |
| `services/sec_pipeline` | RawDocumentStore(26), SupplyChainEvidence.source_company(88), BusinessModelSnapshot(175) |
| `apps/chain_sight` | 프로파일 10종(attention/chain_profile/narrative_tag/sensitivity/growth_stage/event_reaction/capital_dna/revenue_structure/insider_signal) |
| `apps/portfolio` | holdings(92·409·520·594, 일부 PROTECT) |

> Stock 삭제는 사실상 **"기업 데이터 전체 소멸"** 연산. 운영 중 의도치 않은 단일 Stock 삭제가 광범위한 데이터 손실로 이어질 수 있어, 삭제 전 가드(소프트 삭제/관리자 확인) 부재가 🟠 위험.

### 3단계 이상 연쇄 삭제 (4건 확인)

1. **`Stock → RawDocumentStore → SupplyChainEvidence`**
   `services/sec_pipeline/models.py`: Stock CASCADE→RawDocumentStore(26), 그리고 SupplyChainEvidence.source_document CASCADE→RawDocumentStore(83) + source_company CASCADE→Stock(88). Stock 삭제 시 두 경로로 evidence 동시 삭제.
2. **`Stock → BusinessModelSnapshot → BusinessModelEvidence`**
   snapshot.symbol CASCADE→Stock(175), snapshot.source_document CASCADE→RawDocumentStore(181), evidence.snapshot CASCADE→snapshot(243). 3단계.
3. **`NewsArticle → NewsEntity → EntityHighlight`**
   `services/news/models.py`: entity.news CASCADE(176), highlight.news_entity CASCADE(240). 기사 1건 삭제 시 엔티티+하이라이트 전부 소멸.
4. **`User → Watchlist → WatchlistItem`** 및 **`User → AnalysisSession → AnalysisMessage`**
   `users/models.py`(191·221), `rag_analysis/models.py`(129·178). 사용자 삭제가 워치리스트 항목·분석 메시지까지 3단계 연쇄.

> 모든 체인이 의도된 소유 관계(부모 없으면 자식 무의미)라 **설계 자체는 타당**. 다만 ①②(sec) 경로는 삭제 후 **Neo4j 엣지가 남아** stale(High ②) 되는 점이 문제.

### PROTECT (7곳) — 양호 신호

`metrics/metric_snapshot.py:12`, `chain_sight/news_event.py:29`, `portfolio/models.py`(93·410·521·595), `market_pulse/snapshot.py:66`에 PROTECT 적용 — 거래/스냅샷 핵심 참조는 실수 삭제를 방어. 긍정적.

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황 (단일 소스 패턴 — 양호)

- **결정 이력**: `audit P0 #9`로 `synced_to_neo4j`/`neo4j_synced`(불리언 의미 반전 혼란) → **`neo4j_dirty` 단일 소스**(True=동기화 필요)로 통일. 코드 주석에 명시 (sec_pipeline `tasks.py:384`, chain_sight `sync_tasks.py:39·193`).
- **sec_pipeline**: `SupplyChainEvidence.neo4j_dirty` + `neo4j_synced_at`. 매칭 성공/저장 시 자동 True. 인덱스 존재(테스트 `test_sec_pipeline_30plus.py:478`로 검증).
- **chainsight**: `CompanyChainProfile.neo4j_dirty`.
- **Beat 스케줄**(`config/celery.py`):
  - `sec-sync-dirty-neo4j` → `sync_dirty_to_neo4j` (5분마다, neo4j 큐)
  - `chainsight-neo4j-dirty-sync` → 주 1회 일요일 04:30 UTC

### 동기화 실패 시 재시도 메커니즘 (견고 — 양호)

- **`sync_dirty_to_neo4j`** (`sec_pipeline/tasks.py:397`): 2-Phase + `select_for_update(skip_locked=True)`, 배치 500.
  - Phase A(PG lock+복사) → Phase B(Neo4j DELETE+CREATE, **행별 try/except**) → Phase C(성공 id만 `neo4j_dirty=False`).
  - **핵심**: Neo4j 쓰기 실패한 행은 `synced_ids`에 안 들어가 **dirty=True 유지** → 다음 5분 beat에서 자동 재시도. **dirty 플래그 자체가 재시도 큐 역할** → idempotent. ✅
- **`sync_profiles_to_neo4j`** (`chain_sight/sync_tasks.py:107`): 프로파일별 try/except, 실패 시 dirty 유지. 동일 패턴. ✅
- 태스크 레벨 `max_retries=1`이지만, 부분 실패가 전체 롤백되지 않고 dirty 플래그로 다음 회차에 흡수되는 설계라 데이터 유실 위험 낮음.

### 불일치 감지 방법 — 🔴 핵심 갭

| 방향 | 현황 | 위험 |
|------|------|------|
| **PG create/update → Neo4j** | `neo4j_dirty` 플래그로 추적 ✅ | 없음 |
| **PG DELETE → Neo4j** | ❌ **미전파**. CASCADE/일반 삭제 시 `neo4j_dirty`가 찍히지 않음(레코드 자체가 사라짐). Neo4j `:Stock` 노드·엣지 그대로 잔존 | 🔴 High ① — 좀비 노드/엣지 누적 |
| **SET_NULL → Neo4j** | `sync_dirty_to_neo4j`가 `target_company__isnull=False`로 **필터**(line 430). target Stock 삭제로 null화되면 그 dirty 행은 **스킵** → 기존 Neo4j 엣지가 **삭제되지 않고 stale 잔존** | 🔴 High ② |
| **Neo4j → PG (역방향)** | ❌ 없음. Neo4j는 다운스트림이라 역검증 잡 부재 | 🟠 |
| **정합성 대조(count/diff)** | ❌ **PG 행수 vs Neo4j 노드/엣지 수를 대조하는 reconcile 잡 없음**. 누락/잉여를 능동 감지할 수단 부재 | 🔴 High ③ |
| 뉴스(부분 보완) | `news_neo4j_sync.cleanup_expired_relationships()` + 고립 노드 정리(`orphan_query:707`) + `_get_existing_event_ids()` 중복 방지 | 🟢 뉴스 도메인만 보완됨 |

> **권고(보고만, 미적용)**: (a) Stock/Evidence 삭제 시 `post_delete` 시그널 또는 tombstone 테이블로 Neo4j DELETE 큐잉, (b) SET_NULL 분기에서 기존 엣지 삭제를 수행하도록 sync 필터 보완, (c) 주기적 reconcile 잡(`PG count` vs `Neo4j MATCH count`)으로 drift 알림.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 (커버리지 양호)

| 도메인 | 제약 | 위치 |
|--------|------|------|
| stocks | `(stock,date)`×3, `(stock,period_type,fiscal_year,fiscal_quarter)`×3(재무), `(stock,signal_date,signal_tag)`(EODSignal), `date unique`, `run_id unique` | `packages/shared/stocks/models.py` |
| users | `(user,stock)`, `(user,name)`, `(watchlist,stock)`, `(user,interest_type,value)` | `packages/shared/users/models.py` |
| metrics | `(industry,fiscal_year,metric_code)`, `(symbol,fiscal_year,metric_code,preset_key)`, `(symbol,fiscal_year,metric_code)` | `packages/shared/metrics/models/` |
| macro | `(indicator,date)`, `(index,date)`, `(indicator,sector_code,condition_type)`, `(indicator_a,indicator_b)` | `macro/models/` |
| thesis | `(thesis,asof_date)`, `(indicator,asof)`, `(target,source,text)`, `(user,original_thesis)` | `thesis/models/` |
| sec_pipeline | `(alias,context_sector)` — country는 무관(테스트로 명세 검증) | `sec_pipeline/models.py` |
| chain_sight | `(source+source_id)`(ChainNewsEvent), `(symbol+event_type)`(EventReaction) | `apps/chain_sight/` |

> 시계열·스냅샷·관계 모델 전반에 복합 unique가 촘촘히 적용됨 — 중복 삽입에 대한 **DB 레벨 방어 양호**.

### update_or_create race condition 가능성 (실측 125회 사용)

- **원리**: Django `update_or_create`는 **단일 원자 연산이 아님** — `get`(SELECT) 후 `create`/`update`(INSERT/UPDATE) 2-step. 동시성 하에 두 워커가 모두 get-miss → 둘 다 INSERT 시도.
- **방어 상태**:
  - 🟢 **unique_together가 있는 대상**(EODSignal `(stock,date)`, 각종 snapshot/metric_latest 등 대다수): race 발생해도 두 번째 INSERT가 **IntegrityError로 거부** → 묵시적 중복(silent dup)은 방지. 단, 예외가 항상 catch되진 않아 **태스크 단발 실패** 가능(재시도로 흡수).
  - 🟠 **unique 제약이 없는 대상**: 진짜 중복 row 생성 위험. (대부분 Beat 단일 writer라 실사용 race는 낮음.)
  - `apps/chain_sight/tasks/attention_tasks.py:12` `PeriodicTask.update_or_create` — 모듈/태스크 단발, 단일 writer → 안전.
  - `eod_json_baker.py:569` `EODDashboardSnapshot`(date unique), `snapshot_builder.py:149` `ThesisSnapshot`(`(thesis,asof_date)` unique) — 단일 Beat writer + unique 보장 → 안전.
- **결론**: race는 **이론적으로 존재하나 실질 위험 낮음**(unique 제약 + Beat 단일 writer 조합). 병렬 워커가 같은 키를 동시 쓰는 경로(예: `rematch_unmatched` 병렬화, 멀티 워커 sec 파이프라인)에서만 IntegrityError 단발 실패 주의. 안전성을 더 높이려면 race 다발 구간을 `transaction.atomic()`+`get_or_create` 후 update, 또는 `bulk_create(ignore_conflicts=True)` 패턴으로 보강 권고(보고만).

---

## 부록: 실측 집계

```
SET_NULL  : 19곳  (sec_pipeline·rag_analysis·serverless·macro·thesis·market_pulse·portfolio·chain_sight)
CASCADE   : 96곳  (stocks·users·metrics·validation·sec_pipeline·news·serverless·chain_sight·portfolio·thesis·macro·graph_analysis[dormant])
PROTECT   : 7곳   (metrics·chain_sight·portfolio·market_pulse — 핵심 참조 실수삭제 방어)
Stock FK 참조 : 38건 (최다 — 삭제 영향 최대 노드)
update_or_create : 125회 (테스트 포함)
neo4j_dirty 동기화 잡 : sec(5분) + chainsight(주1회)
```

> 본 보고서는 읽기 전용 감사이며 어떤 코드/스키마도 변경하지 않았다. 권고 사항은 모두 **제안**이며 적용되지 않았다.
