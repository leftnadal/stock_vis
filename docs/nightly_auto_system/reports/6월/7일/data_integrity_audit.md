# 데이터 무결성 감사 보고서

> 생성일: 2026-06-07
> 범위: 읽기 전용 정적 분석 (코드 미수정)
> 대상: FK 무결성 · CASCADE 연쇄 · Neo4j↔PostgreSQL 동기화 · Unique 제약
> 방법: `models*.py` 전수 grep + 핵심 task/service 코드 정독

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 2 | (H-1) CASCADE 삭제 시 Neo4j orphan edge 영구 잔존 / (H-2) SET_NULL orphan 정리·감지 로직 부재 |
| 🟠 Medium | 3 | (M-1) Stock 삭제 영향 범위 26개 모델 직접 CASCADE / (M-2) Neo4j↔PG 양방향 불일치 능동 감지 부재 / (M-3) `neo4j_synced` 필드 없는 모델의 동기화 상태 추적 한계 |
| 🟡 Low | 3 | (L-1) 3단계 CASCADE 체인 4계열 / (L-2) update_or_create race(unique 미보호 소수) / (L-3) sec_pipeline 재시도 max_retries=1 |

### 지시서 수치 vs 실측 차이 (선행 경고)

> **지시서의 디렉토리 경로와 카운트가 현재 코드베이스와 불일치합니다.** 서비스 리모델링(`packages/shared/`, `apps/`, `services/` 3-tier 재배치)이 반영되지 않은 구버전 기준입니다.

| 항목 | 지시서 | 실측 | 차이 |
|------|--------|------|------|
| SET_NULL 사용처 | 7곳 / 3개 파일 | **17곳 / 9개 파일** | +10 |
| CASCADE 사용처 | 37곳 / 7개 파일 | **90+곳 / 20+개 파일** | +53 |
| 경로 예시 | `stocks/models.py` | `packages/shared/stocks/models.py` | 재배치됨 |

본 보고서는 **실측 기준**으로 작성했습니다.

---

## FK orphan 위험

### SET_NULL 사용처 전수 (17곳 / 9개 파일)

| # | 파일:라인 | 모델.필드 | 참조 대상 | NULL 시 보존 의도 |
|---|----------|----------|----------|------------------|
| 1 | `macro/models/indicators.py:310` | (지표 관계) | indicator | 거시 지표 이력 보존 |
| 2 | `thesis/models/monitoring.py:66` | 모니터링 | thesis 관련 | 스냅샷 보존 |
| 3 | `thesis/models/indicator.py:15` | 지표 | catalog | 지표값 보존 |
| 4 | `thesis/models/thesis.py:70` | InvestmentThesis | (상위 참조) | 테제 보존 |
| 5 | `thesis/models/thesis.py:77` | InvestmentThesis | (상위 참조) | 테제 보존 |
| 6 | `apps/chain_sight/models/news_event.py:69` | ChainNewsEvent | self FK(parent) | 이벤트 체인 보존 |
| 7 | `apps/portfolio/models.py:341` | AnalysisRun | wallet_snapshot_at_execution | 실행 시점 스냅샷 |
| 8 | `apps/portfolio/models.py:768` | ChatSession | analysis_run | 세션 대화 보존 |
| 9 | `apps/portfolio/models.py:870` | Decision | context_analysis_run | 의사결정 기록 보존 |
| 10 | `apps/market_pulse/models/anomaly.py:35` | Anomaly | (지표/스냅샷) | 이상치 기록 보존 |
| 11 | `services/rag_analysis/models.py:132` | AnalysisSession | basket | 세션 보존(바스켓 삭제 무관) |
| 12 | `services/rag_analysis/models.py:232` | UsageLog | session | **비용 로그 보존(핵심)** |
| 13 | `services/rag_analysis/models.py:239` | UsageLog | message | **비용 로그 보존(핵심)** |
| 14 | `services/serverless/models.py:660` | ScreenerAlert | preset | 커스텀 필터로 폴백 |
| 15 | `services/serverless/models.py:797` | InvestmentThesis | user | 익명 테제 보존 |
| 16 | `services/serverless/models.py:1353` | (관계 모델) | user | 사용자 삭제 후 데이터 보존 |
| 17 | `services/sec_pipeline/models.py:94` | SupplyChainEvidence | target_company | **`target_company_name` 텍스트로 복원 가능** |

### 🔴 H-2 — SET_NULL 후 orphan 정리·감지 로직 부재

**관찰:**
- 17곳 모두 `null=True`로 SET_NULL을 적용하나, **NULL이 된 레코드를 주기적으로 정리(GC)하거나 감지하는 Celery task / management command가 존재하지 않음.**
- `grep`으로 `isnull=True` 기반 cleanup·alert 로직을 추적한 결과:
  - sec_pipeline: `target_company__isnull=True`는 **미매칭 큐(UnmatchedCompanyQueue) 적체 알림**용으로만 사용 (`quality_checks.py:87-89`) — SET_NULL로 풀린 건이 아니라 처음부터 매칭 안 된 건 대상.
  - rag_analysis `UsageLog`: session/message NULL은 **의도적 비용 로그 보존** 설계로 판단(GC 불필요).

**위험 분류:**

| 모델 | NULL orphan 발생 시 | 설계 의도 | 정리 필요성 |
|------|---------------------|----------|-------------|
| `SupplyChainEvidence.target_company` | Stock 삭제 시 NULL | `target_company_name`으로 텍스트 보존 ✅ | 낮음(설계상 정상). 단 **Neo4j 엣지는 별도** → H-1 참조 |
| `rag_analysis.UsageLog` | 세션/메시지 삭제 시 NULL | 비용 감사 추적 보존 ✅ | 낮음 |
| `serverless.InvestmentThesis.user` | 회원 탈퇴 시 NULL | 익명 테제 보존 | **중간** — `user=NULL` 테제가 영구 누적, 소유자 없는 데이터 권한·조회 모호 |
| `portfolio.AnalysisRun.wallet_snapshot` | 스냅샷 삭제 시 NULL | 실행 시점 보존 | 낮음 |

**권고(정보 제공용, 수정 아님):**
1. `user=NULL` InvestmentThesis(serverless)의 누적량 모니터링 쿼리를 nightly 알림에 추가 검토.
2. SET_NULL 컬럼 중 "보존 의도"가 명문화되지 않은 것은 `DECISIONS.md`에 의도 기록 권장.

---

## CASCADE 체인

### 🟠 M-1 — Stock 삭제 시 영향 범위 (직접 CASCADE 26개 모델)

`Stock`(PK=`symbol`, `packages/shared/stocks/models.py:21`)을 **직접 FK로 참조**하는 모델 — 대부분 `to_field="symbol"`:

| 도메인 | 모델(파일) | on_delete |
|--------|-----------|-----------|
| stocks | DailyPrice(194), WeeklyPrice(306), +2개(1015·1063) | CASCADE |
| stocks | (1153, null) | CASCADE(null=True) |
| users | Portfolio(47), WatchlistItem(223) | CASCADE |
| metrics | benchmark(14·124), metric_snapshot(13) | CASCADE |
| chain_sight | chain_profile, narrative_tag, news_event, sensitivity, growth_stage, event_reaction, capital_dna, revenue_structure, insider_signal (9개) | CASCADE |
| validation | peer_preset(×2), news_summary, metric_latest, category_score, benchmark_delta (6개) | CASCADE |
| portfolio | WalletHolding(91), MetricResult(408), LLMComment(593) | CASCADE |
| sec_pipeline | SupplyChainEvidence.source_company(86) | CASCADE |
| sec_pipeline | SupplyChainEvidence.target_company(92) | **SET_NULL** |

**결론:** `Stock.delete()` 1건은 **약 26개 테이블에 CASCADE 전파**. 가장 광범위한 삭제 진앙. 운영 중 종목 상장폐지/심볼 변경 시 이 연쇄가 그대로 발동되므로, **종목 삭제는 반드시 트랜잭션 + 사전 백업 후 수행해야 함** (현재 별도 가드 없음).

### 🟡 L-1 — 3단계 이상 연쇄 삭제 체인 (4계열)

3단계 이상 깊이로 연쇄되는 CASCADE 체인:

```
① User 삭제 → Portfolio 도메인 (최대 4단계)
   User ─CASCADE→ Portfolio ─CASCADE→ AnalysisRun ─CASCADE→ MetricResult
                                                    ├CASCADE→ DiagnosticCard
                                                    ├CASCADE→ LLMComment
                                                    └CASCADE→ StoredAnalysis
   User ─CASCADE→ Wallet ─CASCADE→ WalletHolding / WalletSnapshot
   User ─CASCADE→ ChatSession ─CASCADE→ Message

② User 삭제 → RAG 도메인 (3단계)
   User ─CASCADE→ DataBasket ─CASCADE→ BasketItem
   User ─CASCADE→ AnalysisSession ─CASCADE→ AnalysisMessage
   (UsageLog는 session/message에 SET_NULL → 로그 보존, 끊김)

③ Stock 삭제 → SEC 도메인 (2단계 + Neo4j)
   RawDocumentStore ─CASCADE→ SupplyChainEvidence (문서 삭제 시)
   Stock(source) ─CASCADE→ SupplyChainEvidence

④ User 삭제 → Screener (3단계)
   User ─CASCADE→ ScreenerAlert ─CASCADE→ ScreenerAlertHistory
```

**위험 평가:** 모든 체인이 `null=False` CASCADE로 정합성은 보장됨(orphan FK 미발생). 단 **① 계열은 사용자 1명 삭제 시 6개 테이블 + 멀티턴 대화·진단 카드까지 전량 소멸** — soft-delete 없이 hard-delete만 존재. 회원 탈퇴 정책상 의도된 동작인지 `DECISIONS.md` 확인 권장.

### CASCADE 정합성 — 양호 판정

- 모든 CASCADE FK가 `null=False`(또는 명시적 의도) → DB 레벨 orphan row 미발생.
- `_dormant/graph_analysis`(8곳 CASCADE)는 휴면 앱 → 운영 영향 없음(보고서 카운트에서 제외).

---

## Neo4j 동기화

### 아키텍처 — `neo4j_dirty` 단일 소스 (audit P0 #9, 2026-04-29)

`synced_to_neo4j`/`neo4j_synced`(불리언 정방향) 폐기 → **`neo4j_dirty`(True=동기화 필요) 단일 플래그**로 통일. 3개 모델이 채택:

| 모델 | 파일 | dirty 필드 | synced_at | index | sync task |
|------|------|-----------|-----------|-------|-----------|
| SupplyChainEvidence | `services/sec_pipeline/models.py:112` | ✅ default=True | ✅ | ✅(123) | `sync_dirty_to_neo4j`(tasks.py:397) |
| CompanyChainProfile | `apps/chain_sight/models/chain_profile.py:84` | ✅ db_index=True | ✅ | ✅ | `sync_tasks.py:114` |
| RelationConfidence | `apps/chain_sight/models/relation_discovery.py:148` | ✅ | ✅ | ✅(162) | `neo4j_sync.py:22` |

**dirty 자동 토글 패턴 (정합성 양호):**
- `save()` 경로: `update_or_create` 호출 시 save()가 발동 → dirty=True 자동 (relation_tasks.py:317 주석 명시).
- `queryset.update()`/`bulk_update()` 경로: save() 미발동 → **수동으로 `neo4j_dirty=True` 명시** (relation_tasks.py:421-435, relation_discovery.py:178-179). ✅ 올바르게 처리됨.

### 동기화 실패 시 재시도 메커니즘

| Task | max_retries | 재시도 지연 | row 단위 실패 처리 |
|------|-------------|------------|-------------------|
| `chainsight-neo4j-dirty-sync`(neo4j_dirty_sync_tasks.py:14) | **2** | 60s | service 내 per-row try/except |
| `sync_dirty_to_neo4j`(sec_pipeline tasks.py:397) | **1** | — | per-row try/except, 실패 시 dirty 유지 |
| `sync_dirty_relations`(neo4j_sync.py:33) | (caller 의존) | — | per-row try/except, 성공 PK만 dirty=False |

**자가 치유(self-healing) 설계 — 양호:**
- 핵심 안전장치: **개별 row 동기화 실패 시 해당 레코드의 `neo4j_dirty`를 False로 내리지 않음** (`synced_pks`/`synced_ids`에 성공 건만 추가, neo4j_sync.py:42·48, tasks.py:513·520).
- → 실패 건은 dirty=True로 남아 **다음 배치 자동 재시도**. Task-level retry 횟수와 무관하게 결국 수렴. ✅
- sec_pipeline은 `select_for_update(skip_locked=True)` + 2-Phase(PG lock→Neo4j→PG update)로 동시 실행 충돌 방지. ✅

### 🔴 H-1 — CASCADE 삭제 시 Neo4j orphan edge 영구 잔존

**가장 심각한 무결성 갭.**

**메커니즘:**
1. dirty-sync는 **`neo4j_dirty=True`인 PG 레코드만** 조회해 Neo4j에 반영(`filter(neo4j_dirty=True)`).
2. 그런데 PG에서 레코드가 **CASCADE/직접 DELETE되면**, 그 row 자체가 사라져 더 이상 조회 불가 → dirty 플래그를 세울 기회조차 없음.
3. 반면 Neo4j 엣지 삭제는 **별도의 명시적 쿼리**(`_delete_edge`, sec_pipeline DELETE 쿼리)로만 발생하며, 이는 "레코드가 살아있고 status가 stale/hidden일 때"만 트리거됨.
4. **결과: Stock 삭제 → SupplyChainEvidence CASCADE 삭제 → Neo4j의 `(:Stock)-[:SUPPLIES_TO]->(:Stock)` 엣지는 삭제 트리거 없이 영구 잔존.**

**영향 받는 경로:**
- `Stock` 삭제 → SupplyChainEvidence(source CASCADE) 소멸 → Neo4j SEC 엣지 orphan.
- `Stock` 삭제 → RelationConfidence(symbol_a/b CASCADE 여부 확인 필요) → Neo4j 관계 엣지 orphan.
- `Stock` 삭제 → CompanyChainProfile CASCADE → Neo4j 프로파일 노드 속성 stale.

**왜 감지 안 되나:** dirty backlog 알림(quality_checks.py:91-96)은 "PG에 살아있는 dirty 레코드 수"만 카운트 → 이미 삭제된 레코드는 관측 불가.

**권고(정보 제공용):**
1. Stock/Evidence delete 시 `pre_delete` 시그널로 Neo4j 엣지 동시 삭제, 또는
2. nightly **Neo4j orphan edge 정합성 스윕**: Neo4j의 `source='sec_10k'` 엣지 중 PG에 대응 Evidence 없는 것 탐지·제거 task 신설 검토.

### 🟠 M-2 — Neo4j↔PG 양방향 불일치 능동 감지 부재

현재 불일치 감지 수단:

| 방향 | 감지 수단 | 한계 |
|------|----------|------|
| PG dirty 적체 | `quality_checks` dirty>50 알림 / `intelligence.py:100` | 살아있는 dirty만, 삭제건 누락(H-1) |
| Neo4j 중복 방지 | news: `article_id` Neo4j 존재 확인 후 제외(news_neo4j_sync.py:546) | 단방향(PG→Neo4j 신규만) |
| PG에만/Neo4j에만 존재 | **전용 reconciliation 로직 없음** | 🔴 갭 |

**결론:** "PG에는 있고 Neo4j에 없는" 건은 dirty 재시도로 결국 수렴하나, **"Neo4j에는 있고 PG에 없는"(orphan edge)은 감지·정리 수단이 전무**(= H-1).

### 🟠 M-3 — `neo4j_synced` 필드 없는 모델의 추적 한계

- `news` 도메인(`NewsArticle`)은 **dirty/synced 필드 자체가 없음**(news_neo4j_sync.py:546 주석: "neo4j_synced 필드가 없으므로").
- 동기화 상태를 **Neo4j에 article_id가 존재하는지 매번 조회**해 판정 → 배치마다 Neo4j 왕복 비용, 실패 시 재시도 추적 불가.
- `serverless` supply_chain_service는 `neo4j_synced`를 **응답 dict의 일회성 결과**로만 사용(122-133), 영속 상태 아님.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 — 양호 (커버리지 높음)

도메인별 핵심 제약(대표):

| 도메인 | 제약 | 보호 대상 |
|--------|------|----------|
| stocks | `(stock,date)`×3, `(stock,period_type,fiscal_year,fiscal_quarter)`×3, `(stock,signal_date,signal_tag)` | 시계열/재무/시그널 중복 |
| users | `(user,stock)`, `(user,name)`, `(watchlist,stock)`, `(user,interest_type,value)` | 포트폴리오/관심/워치 중복 |
| metrics | `(industry,fiscal_year,metric_code)`, `(symbol,fiscal_year,metric_code,preset_key)` | 벤치마크 중복 |
| chain_sight | `(source,source_id)`, `(symbol,event_type)`, `(symbol_a,symbol_b[,period/relation_type])` | 관계/이벤트 중복 |
| portfolio | `(wallet,stock)` + UniqueConstraint ×4(459·551·611·734) | 보유/분석 중복 |
| market_pulse | `(date)`, `(date,model_version)`, `(date,universe)`, `(date,market_index)`, `(user,news,viewed_date)` | 일별 스냅샷 중복 |
| rag_analysis | `(basket,item_type,reference_id)` | 바스켓 아이템 중복 |
| serverless | `(date,mover_type,symbol)`, `(symbol,date[,action_type])`, `(etf,stock_symbol,snapshot_date)`, `(stock_symbol,theme_id)`, `(institution_cik,stock_symbol,report_date)` | 무버/ETF/테마/기관 중복 |
| news | `(news,symbol)`, `(symbol,date)`, url unique | 엔티티/키워드 중복 |
| sec_pipeline | `accession_no` unique, `(alias,context_sector)` | 문서/별칭 중복 |
| validation | `(symbol,preset_key)`, `(user,symbol)`, `(symbol,metric_code)`, `(symbol,category,fiscal_year,preset_key)` | 프리셋/지표 중복 |

### 🟡 L-2 — update_or_create race condition

- `update_or_create`/`get_or_create` 사용처 **126건**(비테스트). 대부분 **위 unique_together와 짝**을 이뤄 DB 레벨 원자성 보장 → race 시 IntegrityError로 안전 수렴.
- **잠재 위험(unique 제약 없이 update_or_create):** 동시 호출 시 중복 row 생성 가능. 후보 점검 권장 영역:
  - `apps/market_pulse/calculators/*`(breadth/concentration/sector_flow) — 계산 캐시성 upsert, 동시 Beat 실행 시 점검.
  - `services/serverless/services/keyword_service.py` 등 키워드 upsert — 키 조합이 unique로 보호되는지 확인 권장.
- Django `update_or_create`는 내부적으로 select→insert/update이며 **트랜잭션/SELECT FOR UPDATE 미적용 시 TOCTOU 존재** → unique 제약이 최종 방어선. 제약 있는 곳은 안전, 없는 곳만 잔여 위험.

### 권고(정보 제공용)
- `update_or_create`의 `lookup` 키가 해당 모델의 unique_together와 **정확히 일치**하는지 자동 검증하는 테스트/lint 추가 검토(현재 수동 일치).

---

## 부록 — 검증 명령 (재현용)

```bash
# SET_NULL 전수
grep -rn 'on_delete=models.SET_NULL' --include='*.py' . | grep -v migrations
# CASCADE 전수
grep -rn 'on_delete=models.CASCADE' --include='*.py' . | grep -v migrations
# Stock 참조 FK
grep -rn 'to_field="symbol"' --include='*.py' . | grep -v migrations
# neo4j_dirty 사용 현황
grep -rn 'neo4j_dirty' --include='*.py' . | grep -v migrations
# unique 제약
grep -rn 'unique_together\|UniqueConstraint' --include='*.py' . | grep -v migrations
```

---

## 종합 결론

| 영역 | 판정 | 핵심 |
|------|------|------|
| FK orphan(DB row) | 🟢 양호 | CASCADE는 null=False로 orphan row 미발생 |
| SET_NULL 정리 | 🔴 갭 | NULL orphan GC/감지 로직 부재(H-2), serverless user=NULL 테제 누적 |
| CASCADE 연쇄 | 🟠 주의 | Stock 삭제=26테이블 전파(M-1), User 삭제=4단계 hard-delete |
| **Neo4j 동기화** | 🔴 **최우선** | dirty 자가치유는 양호하나 **CASCADE 삭제→Neo4j orphan edge 영구 잔존(H-1)**, 양방향 reconciliation 부재(M-2) |
| Unique 제약 | 🟢 양호 | 커버리지 높음, update_or_create 대부분 unique로 보호 |

**최우선 후속 검토 1건:** H-1(Neo4j orphan edge). PG hard-delete가 Neo4j와 단절되어 그래프에 유령 관계가 누적되며, 현재 감지 수단이 전무함. nightly orphan-edge 스윕 task 또는 pre_delete 시그널 도입을 다음 스프린트 후보로 권장.

> 본 보고서는 정적 분석 기반이며 코드를 수정하지 않았습니다. 모든 권고는 정보 제공용입니다.
