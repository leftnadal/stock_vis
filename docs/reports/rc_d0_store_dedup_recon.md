# RC-D-0 — 관계 store 이중화 전수 실측 보고 (read-only)

> 세션: ops/chainsight 측정 전용. 코드 변경 0 · PG 쓰기 0 · Neo4j 쓰기 0.
> base: origin/main `d2b7ba87` (087c7cd8 ⊆ 확인). worktree `sv-rc-d0` / `monorepo/sess-rc-d0`. 지시서 커밋 `3631bb81`.
> 측정일: 2026-09-07. **캐리오버 금지 준수** — 아래 수치는 전부 본 세션 실측. 과거 스냅샷과 다르면 실측 채택·명시.

## §0 STEP 0
- 0-1 origin/main `d2b7ba87` (087c7cd8 이후 ✓). 0-2 worktree `sv-rc-d0`. 0-3 지시서 `3631bb81`. 0-4 `pytest tests/architecture` **9 passed**·코드 변경 0(health ❌ 신규 0).

## STEP 1 — 코드 전수 조사

### 1-1 두 store 모델·제약
| 항목 | RelationConfidence | StockRelationship |
|---|---|---|
| 좌표 | `apps/chain_sight/models/relation_discovery.py:72` | `services/serverless/models.py:855` |
| db_table | `chainsight_relation_confidence` | `serverless_stock_relationship` |
| 식별 필드 | symbol_a, symbol_b, relation_type (무방향 지향) | source_symbol, target_symbol, relationship_type (방향성) |
| **unique_together** | **`[symbol_a, symbol_b, relation_type]` (존재)** | **`[[source_symbol, target_symbol, relationship_type]]` (존재)** |
| CheckConstraint | `rc_symbol_a_ne_symbol_b` (a≠b, mig 0034) **있음** | **없음** |
| self-loop save() 가드 | 있음(`:268`) | 없음 |
- ⑶ 양측 모두 3필드 유일 제약 **이미 존재**(없다고 전제 금지 — 확인). RC만 self-loop DB/앱 가드 보유.

### 1-2 StockRelationship 직접 소비처 (프로덕션)
`services/serverless/` 내부 전용 — tasks.py, views.py, theme_matching/supply_chain/institutional_holdings/regulatory/keyword_enricher/news_relation_matcher/patent_network/neo4j_chain_sight_service (11파일 ~40참조). 테스트 5파일·마이그 2파일 별도.
- **apps/ 에서 StockRelationship 참조 = 0건** (경계 오염 없음).

### 1-3 write 경로 (전부 Celery 태스크)
`update_or_create`/`get_or_create`/`save`만 — supply_chain_service:321, institutional_holdings_service:448, regulatory_service:559/600, news_relation_matcher:241/274, patent_network_service:388/442, tasks.py:1471(sync_llm_relations), keyword_enricher:340. **프로덕션 create/bulk_create/delete = 0**. 관리 커맨드·뷰 직접 write = 0.

### 1-4 HTTP 서빙 + frontend 실호출
- 읽기 서빙 view 2개: `regulatory-get`(`/api/v1/serverless/regulatory/<symbol>`)·`patent-network-get`(`/api/v1/serverless/patent-network/<symbol>`), 둘 다 AllowAny.
- **frontend 실제 fetch/axios 호출 = 0건** (생성 타입 `schema.yml`/`api-types.ts`에만 존재). → 두 엔드포인트 **프론트 미사용**.

### 1-5 승격 경로
- **StockRelationship ↔ RelationConfidence 동시 참조 파일 = 0건**. 승격/복사 코드 없음. **두 store 완전 분리 파이프라인.**

### 1-6 Neo4j 동기화 2경로
| | (a) serverless `neo4j_chain_sight_service.py` | (b) chain_sight `graph/repository.py`·`neo4j_sync.py` |
|---|---|---|
| 소스 | StockRelationship | RelationConfidence(neo4j_dirty) |
| 노드 라벨 | `:Stock` | `:Stock` |
| **노드 키** | **`symbol`** | **`ticker`** |
| DB | settings.NEO4J_URI 기본DB | 동일 URI 기본DB |
- **판정**: 같은 인스턴스·같은 `:Stock` 라벨이나 **키 프로퍼티 불일치(symbol vs ticker)** → 동일 종목이 별개 노드로 갈라짐. (STEP 4-1로 실증됨)

## STEP 2 — 창고 실측 (PG, SELECT)
### 2-1 StockRelationship = **246,158행** (기대 225,073 ↑)
| type | 행수 |
|---|---|
| HELD_BY_SAME_FUND | 197,034 |
| SAME_REGULATION | **47,346** (기대 26k ↑) |
| CO_MENTIONED | 1,523 |
| SAME_INDUSTRY | 179 · PEER_OF 68 · SUPPLIED_BY 5 · PARTNER_OF/ACQUIRED/INVESTED_IN 각 1 |
- 최다1종 제외 잔여 = 49,124. **상위2종 제외 잔여 = 1,778**(CO_MENTIONED 1,523 + 소수).

### 2-2 source_provider × type
sec_13f→HELD_BY_SAME_FUND 197,034 · regulatory_llm→SAME_REGULATION 47,346 · news→CO_MENTIONED 1,523 · fmp→SAME_INDUSTRY 179/PEER_OF 68 · sec_10k→SUPPLIED_BY 5 · news→PARTNER_OF/ACQUIRED/INVESTED_IN.

### 2-3 유입 상태 = **동결 아님(활발)**
최신 discovered_at = **2026-09-05**(CO_MENTIONED). 월별: 06=197,038(13F 벌크)·07=22,513·08=24,924·09=134. HELD/SAME_REG는 여름 벌크, CO_MENTIONED 일일 유입 지속.

### 2-4 RelationConfidence = **13,947행** (기대 13,626 ↑)
- status: confirmed 2,263 · hidden 7,650 · probable 155 · weak 3,879
- type: PEER_OF 9,365 · CO_MENTIONED 4,184 · COMPETES_WITH 159 · SUPPLIES_TO 90 · PARTNER_WITH 89 · DEPENDS_ON 58 · PEER 2
- score_version 3.0 전건. **PRICE_CORRELATED = 0** (RC-A-1 ⑥ 봉인 유지).

### 2-5 교집합
- 타입 교집합 = {CO_MENTIONED, PEER_OF}.
- 무향 심볼쌍: SR distinct 136,196 · RC distinct 12,387 · **양측 공존 = 6,503쌍**.

## STEP 3 — RC-PAIR-DEDUP 프로브 (재정의)
### 3-1 RC 무향 pair 2행+
- **전수 = 1,460쌍** (기대 144는 CP-필터 부분집합값 — 지시서 3-1 기대값이 실은 CP-필터 수치). 전수 분포 {2:1372, 3:80, 4:4, 5:4}.
- **CP∧max>0 필터(앵커 재현) = 144쌍** {2:126, 3:13, 4:5}. 3분류: **ⓐ동방향 111쌍/231행 · ⓑ왕복 24/48 · ⓒ혼합 9/32** (잉여행 167).

### 3-2 발생 writer + 표본
ⓐ "동방향 중복" 표본 3건 — 전부 **같은 pair·같은 방향에 서로 다른 relation_type**:
- (COST,TPR): DEPENDS_ON(0.6) + SUPPLIES_TO(0.85) · first_observed 09-01
- (B,NEM): DEPENDS_ON(0.85) + PARTNER_WITH(0.85) · 08-13
- (AMZN,TTD): COMPETES_WITH(0.85, truth) + CO_MENTIONED(market 0.6) · 05-26/08-23
→ 상이 유형은 상이 파이프라인(SEC 공급망·LLM 관계·news co-mention)이 각자 write(1-3). 단일 pair에 다관계 축적은 설계상 정상.

### 3-3 유일성 제약 적합성 — **재정의**
- **(a,b,relation_type) 진짜 중복 triple = 0** (실측). unique_together `[symbol_a,symbol_b,relation_type]` **이미 존재·완전 충족**.
- **111 "동방향 중복"은 제약 위반이 아니다** — 같은 pair의 **서로 다른 relation_type**(다중 관계). (a,b,relation_type) 제약은 이들을 막지 않으며 막아서도 안 됨(상이 유형=상이 사실). **실효 제약 후보: 없음**(신설 불요). "동방향 중복"은 무향 collapse가 다관계를 1엣지로 접을 때 생기는 **측정 아티팩트**이지 데이터 결함이 아님.

### 3-4 델타 재현 — 산식 확인, 수치는 데이터 성장
| 산식 | 입력행 → 엣지 | 델타 |
|---|---|---|
| `max(truth,market)>0` (backbone 정산식) | 2,418 → 2,251 | **−167** |
| `market_score>0` (지시서 3-4 문구) | 232 → 232 | −0 |
- **정산식 = max(truth,market)>0**. 지시서 "market_score>0" 문구는 오류(truth-only 엣지 제외 → −0). collapse **메커니즘 확인**. 수치 −166→**−167**은 RC-C-1(08-31) 이후 RC +321행 성장분(CP∧max>0 2,365→2,418). CP-필터 잉여행 167 = ⓐ231행−111쌍 + ⓑ44−22? → 실측 잉여행 합 167(ⓐ120+ⓑ24+ⓒ23 = 167, pair별 rows−1 합산).
- ⚠️ **HALT 조건 문구("−166으로 안 떨어지면 HALT") 대비**: 캐리오버 금지 원칙상 −166은 과거 스냅샷·정산식(max>0) 메커니즘은 정상 재현(−167). 디렉터 판정 요청(측정 무결·데이터 성장이 원인).

### 3-5 집계 부풀림
- `apps/chain_sight/services/pair_aggregation.py:84,87` = `truth_max = max(...)`·`market_max = max(...)` — **MAX 사용(합산 아님)**. relevance_opp/risk도 max 기반. edge_count(`truth_edge_count`/`market_edge_count`)는 행수만큼 증가(기여 엣지 카운트, 정당).
- backbone `build_relation_graph`도 pair당 max weight collapse → 점수 부풀림 없음.
- 표본 3건 evidence_count_total 대부분 0(LLM/seed truth 관계).

### 3-6 판정 (1줄)
- **점수 부풀림 = N** (pair_aggregation·backbone 모두 MAX). 근거수(edge_count)는 다관계 수만큼 증가하나 정당(중복 아닌 상이 유형). RC-PAIR-DEDUP의 "부풀림" 전제는 **성립하지 않음**.

## STEP 4 — Neo4j 위생 (Cypher read-only)
### 4-1 이중 노드 **확증**
- :Stock 총 **1,680** = `symbol`-키 **1,146** ⊎ `ticker`-키 **534** · **둘 다 보유 = 0** · symbol만 1,146 · ticker만 534.
- → 1-6 판정 실증: serverless(symbol)·chain_sight(ticker) sync가 **완전 분리된 노드 집합** 생성. MERGE가 서로 매칭 안 됨.

### 4-2 관계 타입 (PRICE_CORRELATED=0 재확인 ✓)
PEER_OF 5,314 · CO_MENTIONED 3,032 · BELONGS_TO 968 · HAS_THEME 534 · BELONGS_TO_SECTOR/INDUSTRY 519 · COMPETES_WITH 178 · DIRECTLY_IMPACTS 93 · SUPPLIES_TO 77 · PARTNER_WITH 60 · DEPENDS_ON 47 · CUSTOMER_OF 32 · INDIRECTLY_IMPACTS 5 · SAME_INDUSTRY 1. **PRICE_CORRELATED 0** ✓.
- ⚠️ **HELD_BY_SAME_FUND·SAME_REGULATION(PG 197k+47k)은 Neo4j 미동기** — 대용량 serverless 타입은 PG 전용.

### 4-3 serverless 유래 엣지 (r.source 보유)
HAS_THEME src=etf_holding 534 · COMPETES_WITH/PARTNER_WITH/DEPENDS_ON/CUSTOMER_OF/SUPPLIES_TO src=sec_10k(총 ~219) · **PEER_OF/SAME_INDUSTRY src=test 3건(테스트 데이터 prod 유출)**. backbone 핵심 엣지(PEER_OF 5,312·CO_MENTIONED 3,032 등)는 r.source 없음(chain_sight 유래). → **backbone이 읽는 그래프는 PG(RC) 기반이라 Neo4j 잡음과 무관**(compute-on-read).

### 4-4 유입 스케줄 — **13건 전부 enabled=True**
extract-news-relations@9 · sync-supply-chain-batch@3 · sync-institutional-holdings@4 · scan-regulatory-relationships@4 · build-patent-network@4:30 · enrich-relationship-keywords@5:30 등. → **serverless StockRelationship 지금도 활발히 유입**(D 결정 긴급도 ↑).

## 6. 지시서와 달랐던 점 (실측 우선)
1. SR 총 246,158 (≠225,073) · SAME_REGULATION 47,346 (≠26k) — 데이터 성장.
2. RC 총 13,947 (≠13,626) — +321행.
3. 3-1 전수 pair = 1,460 (지시서 기대 144는 CP-필터 부분집합).
4. **3-4 델타 −167** (≠−166) — 데이터 성장. **market_score>0 문구 오류**(정산식=max>0).
5. RC unique_together `[symbol_a,symbol_b,relation_type]` **이미 존재**(지시서 "없다 전제 금지" 준수 — 존재 확인). 진짜 중복 triple 0.
6. Neo4j 노드 키 불일치(symbol vs ticker) 실증 = 이중 노드 1,146/534/0.

## 7. 디렉터 결정 안건 (사실·후보만, 선택지 미작성)
- **A. 두 store 완전 독립**: 승격 경로 0·동시 참조 0·apps 참조 0·frontend 실호출 0. RC(13,947)와 SR(246,158)은 분리 파이프라인. D 결정(RC=단일 정본) 집행 시 **SR의 197k HELD + 47k SAME_REG(RC 부재·Neo4j 미동기·frontend 미사용)의 처분**이 핵심 미정 사안.
- **B. SR 활발 유입 중**: 13 beat enabled·09-05 최신. 동결 아님 → 단일화 결정 지연 시 계속 성장.
- **C. Neo4j 이중 노드**(symbol 1,146 ⊎ ticker 534, 교집합 0): 별개 그래프 위생 안건. backbone(PG compute-on-read)은 무영향이나 Neo4j 소비처에는 키 통일 필요.
- **D. RC-PAIR-DEDUP 재정의**: 진짜 중복 0·(a,b,type) 제약 이미 충족·부풀림 없음(MAX). "111 동방향 중복"=다관계 아티팩트. 후보 = **RC-PAIR-DEDUP 종결(무조치)** 또는 관찰 유지.
- **E. 잔여 위생**: Neo4j test 엣지 3건 유출(src=test).
- **F. HALT 문구 대비 3-4**: 델타 −167(≠−166)은 데이터 성장·메커니즘 정상. 문구 갱신 여부 판정.

> 처분·통합·삭제·제약 신설은 본 세션 범위 밖. 후보만 등재하고 HALT. push는 "푸시" 대기.
