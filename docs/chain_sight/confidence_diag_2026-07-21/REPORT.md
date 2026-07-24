# ⑳-F 카드 데이터 변별력 진단 (read-only) — REPORT

- **일자**: 2026-07-21
- **세션**: 조사 세션 (read-only, 코드 diff 0)
- **대상**: chainsight ego 드릴다운 카드 리스트 "신뢰도 전원 85" 무변별 + 근거0·85 모순 + ⑳-2 S3 지도 튜닝 라이브 미작동
- **데이터 소스**: 로컬 `stock_vis` dev DB (`RelationConfidence` 13,699행), 2026-07-21 실측
- **코드 diff 증빙**: `git status --short` 공백 · `git diff --stat` 공백 (작업트리 clean, SELECT만 수행)

---

## 0. 한 줄 결론

카드가 "신뢰도"로 보여주는 값은 `RelationConfidence.truth_score` **원값**이며, 이 필드는 **연속 신뢰도가 아니라 tier/grade 기반 하드코딩 계단값(35/60/85 등 distinct 6종)**이다. "전원 85"는 **(a) DB 자체가 소수 계단값에 균일하게 몰려 있고, truth 관계 유형(공급/경쟁/의존)이 규칙상 85로 고정되기 때문**이다. API fallback도, 표시 반올림도 아니다. 근본적으로 **서로 다른 소스·스케일의 점수를 한 축(truth_score)에 섞고, 그 축 단일 정렬로 상위 50을 절단**하는 구조 결함이다.

---

## Q1. 신뢰도 값의 실제 분포 — 데이터 계층

### Q1-A. 전체 `RelationConfidence` (n=13,699)

| 필드 | n | distinct | min | max | mean | median | mode |
|---|---|---|---|---|---|---|---|
| `truth_score` | 13,699 | **6** | 0.00 | 85.00 | 44.62 | 60.00 | **60.0 (×6,914)** |
| `market_score` (non-null) | 4,062 | **3** | 35.00 | 85.00 | 46.02 | 35.00 | 35.0 (×2,544) |

- **truth_score 값 종류(distinct=6)**: `60.0`(6,914) · `0.0`(4,062) · `85.0`(2,023) · `35.0`(698) · `0.6`(1) · `0.5`(1)
  → 사실상 **4개 계단값(0 / 35 / 60 / 85)** + 레거시 2행(0.5/0.6, `relation_type="PEER"` 소문자 오타 유형).
- **market_score 값 종류(distinct=3)**: `35.0`(2,544) · `60.0`(1,245) · `85.0`(273) — 동일 계단값.
- `relation_status`: probable 7,935 / confirmed 2,326 / hidden 2,150 / weak 1,288
- `relation_category`: truth 9,637 / market 4,062

### Q1-B. NVDA ego 엣지 (symbol_a='NVDA' OR symbol_b='NVDA', n=224)

| 필드 | n | distinct | min | max | mean | median | mode |
|---|---|---|---|---|---|---|---|
| `truth_score` | 224 | 5 | 0.00 | 85.00 | 20.67 | 0.00 | **0.0 (×125)** |
| `market_score` (non-null) | 125 | 3 | 35.00 | 85.00 | 40.40 | 35.00 | 35.0 (×103) |

- truth_score 분포: `0.0`(125) · `35.0`(71) · `85.0`(21) · `60.0`(6) · `0.6`(1)
- **NVDA ego 224행 중 125행(56%)이 truth_score=0** — 전부 CO_MENTIONED(105) + PRICE_CORRELATED(20). 이들은 값이 `market_score`에만 있다.
- NVDA ego relation_type: CO_MENTIONED 105 / PEER_OF 94 / PRICE_CORRELATED 20 / SUPPLIES_TO 3 / PEER 1 / COMPETES_WITH 1

### Q1-C. relation_type별 truth_score 분포 (핵심 표)

| relation_type | n | truth_score distinct | 85점 비율 | 지배값 | 비고 |
|---|---|---|---|---|---|
| **COMPETES_WITH** | 114 | 2 | **110/114 (96%)** | 85 | SEC 10-K, truth |
| **SUPPLIES_TO** | 61 | 3 | **53/61 (87%)** | 85 | SEC 10-K, truth |
| **DEPENDS_ON** | 41 | 3 | **34/41 (83%)** | 85 | SEC 10-K, truth |
| **PARTNER_WITH** | 54 | 3 | **36/54 (67%)** | 85 | SEC 10-K, truth |
| **PEER_OF** | 9,365 | 3 | 1,790/9,365 (19%) | **60 (×6,884)** | peer/industry, truth |
| **CO_MENTIONED** | 278 | 1 | 0 | **truth=0** (market: 35/60/85) | news, market |
| **PRICE_CORRELATED** | 3,784 | 1 | 0 | **truth=0** (market: 35/60/85) | price, market |
| PEER (오타) | 2 | 2 | 0 | 0.5 / 0.6 | 레거시 |

> **결정적 관찰**: 유형마다 truth_score의 소스·스케일·의미가 전부 다르다. 공급/경쟁 계열은 85가 지배(규칙 고정), PEER_OF는 60 지배, market 계열(co-mention/price)은 truth_score가 아예 0이다. **한 축(truth_score)에 이질적 점수가 섞여 있다.**

---

## Q2. 85의 출처 — API/코드 계층

### Q2-1. ego API의 confidence 매핑 — **fallback 없음**

`apps/chain_sight/api/ego_views.py` `EgoGraphView.get()` (⑳-2 카드 리스트 백엔드):

```python
# ego_views.py:88-99 — 정렬·절단
edge_qs = RelationConfidence.objects.filter(Q(symbol_a=symbol) | Q(symbol_b=symbol))
...
edge_rows = list(edge_qs.order_by("-truth_score").values(
    "symbol_a","symbol_b","relation_type","truth_score",
    "evidence_count_total","last_observed_at")[:limit])   # limit 기본 50

# ego_views.py:194-203 — 엣지 payload
edges.append({
    "truth_score": round(e["truth_score"] or 0.0, 2),        # ← DB 원값, round만
    "evidence_count": e.get("evidence_count_total") or 0,
    "last_mentioned": last_obs.date().isoformat() if last_obs else None,
    ...
})
```

- **confidence = `truth_score` DB 원값**. 정규화·클램프·기본값 **없음**. `or 0.0`은 None일 때만 0(85 아님).
- 파일 헤더 주석(`:9`)이 명시: *"truth_score는 미정규화 원값 그대로 노출(정규화는 별도 트랙)."*
- → **"전원 85"는 API fallback이 아니다.** (Neo4j 기반 별도 뷰 `views.py:603-616`도 `ORDER BY r.truth_score DESC`, `min_truth` 기본 35 — 동일 원값 정렬.)

### Q2-2. 85 계단값의 진짜 출처 — tier/grade 하드코딩 (배치 태스크)

`apps/chain_sight/tasks/relation_tasks.py`:

```python
# PEER_OF (truth) — :287-290
if len(peer_sources) >= 2:           # peer + industry 둘 다
    tier, status, score = 1, "confirmed", 85
else:                                # 하나만
    tier, status, score = 2, "probable", 60

# CO_MENTIONED (market) — :328-333  → truth_score=0, market_score=score
if count >= 10:  tier,status,score = 1,"confirmed",85
elif count >= 5: tier,status,score = 2,"probable",60
else:            tier,status,score = 3,"weak",35

# PRICE_CORRELATED (market) — :367-372 → truth_score=0, market_score=score
if corr >= 0.8:  tier,status,score = 1,"confirmed",85
elif corr >= 0.6:tier,status,score = 2,"probable",60
else:            tier,status,score = 3,"weak",35
```

- SEC 10-K 유형(SUPPLIES_TO/COMPETES_WITH/DEPENDS_ON/PARTNER_WITH)은 별도 SEC 파이프라인이 **grade 기반 계단값**으로 부여 — high→85 (테스트 `tests/chainsight/test_t3b_seed_authority.py:86` *"score 85 ≥ HIGHSCORE → confirmed"* 로 검증).
- → **점수는 전부 3~4단 이산 매핑.** 연속 신뢰도가 아니라 규칙 등급. 그래서 distinct 6종에 몰린다.

### Q2-3. 근거 0건 + 85점 모순 — 소스 규명 (실측 레코드)

| 엣지 | type | truth_score | evidence_count_total | evidence_sources | has_supply | basis_summary | last_observed(auto_now) | last_verified |
|---|---|---|---|---|---|---|---|---|
| MU→NVDA | SUPPLIES_TO | **85** | **0** | `{}` | True | "SEC 10-K: We purchase memory from SK Hynix, Micron, Samsung." | 2026-07-20 | **None** |
| ANET→NVDA | COMPETES_WITH | **85** | **0** | `{}` | True | "SEC 10-K: competition also coming from … Dell/EMC …" | 2026-07-20 | **None** |
| TSM→NVDA | SUPPLIES_TO | **85** | **0** | `{}` | True | "SEC 10-K: We utilize foundries such as TSMC, and Samsung" | 2026-07-20 | **None** |
| MU→NVDA | PEER_OF | 85 | 2 | `{'sources':['peer','industry']}` | — | "Peer 관계 + 같은 산업" | 2026-06-20 | None |

**해명**:
1. **"근거 0건"은 "증거 없음"이 아니다.** MU/ANET/TSM 공급·경쟁 엣지는 SEC 10-K 텍스트라는 실제 근거가 `relation_basis_summary`에 존재한다. 그러나 `evidence_count_total` 카운터는 **co-mention/peer/price 같은 "카운트형 증거"만 세고 SEC 텍스트를 세지 않는다** → SEC 유형은 구조적으로 0.
   - 실측: `evidence_count_total=0 AND truth_score>0` 인 행 = **272건**. 전부 SEC 계열(COMPETES_WITH 114 + SUPPLIES_TO 61 + PARTNER_WITH 54 + DEPENDS_ON 41 + PEER 2). PEER_OF(9,365)·CO_MENTIONED(278)·PRICE_CORRELATED(3,784)은 evidence_count_total ≥ 1.
2. **truth_score와 evidence_count는 독립 필드.** truth_score=85는 tier_best=1(SEC grade high)에서 온 고정값이고 카운터와 무관.
3. → **"비교 불가능한 숫자를 한 축에 섞고 있다"는 진단은 사실이다.** truth_score=85가 세 뜻: (i) SEC high-grade 규칙값(evidence 0), (ii) peer+industry 2소스(evidence 2). 그리고 co-mention/price 관계는 truth_score=0으로 같은 축에서 배제된다.

### Q2-4. last_mentioned 07-20 vs 06-20 군집의 의미 — **언급일이 아니다**

- `last_mentioned` = `RelationConfidence.last_observed_at`(`ego_views.py:201`), 이 필드는 모델에서 **`auto_now=True`**(`relation_discovery.py:140`) → **행이 마지막으로 `save()`된 시각**이지 뉴스 언급일이 아니다.
- **07-20 군집** = SEC 파이프라인이 그 행을 마지막 touch한 시각 (SUPPLIES_TO/COMPETES_WITH; `last_computed_at=2026-07-11`, save는 07-20 16:00).
- **06-20 군집** = peer/co-mention 배치가 마지막 실행된 시각 (PEER_OF 등).
- → 카드의 "최근 언급 N일"류 표기는 **파이프라인별 마지막 실행 시각**을 잘못 의미부여한 것. `last_verified_at`은 전 표본 **None**(검증 witness 미기록).

---

## Q3. Peer 편중 — 구성 계층

### NVDA ego 상위 50 실측 (API 재현: `order_by('-truth_score')[:50]`)

- 상위 50 유형 분포: **PEER_OF 46 · SUPPLIES_TO 3 · COMPETES_WITH 1**
- 상위 50 truth_score 분포: **85 ×21 · 60 ×6 · 35 ×23**
- **순위 1~21위 전원 truth_score=85 동점**: MU(SUPPLIES_TO)·ANET(COMPETES)·TSM(SUPPLIES)·FN(SUPPLIES) 4건 외 17건이 PEER_OF(Q/MCHP/TXN/QCOM/…). 22~27위=60 동점(PEER_OF), 28~50위=35 동점(PEER_OF 23건).

**편중 원인 2가지**:
1. **모수 편중**: PEER_OF가 전체 9,365행으로 압도적(다음 PRICE_CORRELATED 3,784는 truth_score=0이라 정렬서 후순위). 어떤 티커든 PEER_OF가 상위를 채운다.
2. **tie-break 부재**: `order_by("-truth_score")` **단일 키**(`ego_views.py:99`). 85점 21개·60점 6개·35점 23개는 각 그룹 내 순서가 **미정의(PostgreSQL 물리 순서)**. 안정적 2차 정렬 없음 → 어떤 85가 먼저 뜰지 비결정적.

**"전원 85" 사용자 인식 재현**: 카드 상단 21개가 전부 85 → 스크롤 상단만 보면 무변별. 실제로는 85(21)/60(6)/35(23)로 3계단 존재하나, 정렬상 85가 앞을 독점.

---

## Q4. 지도 튜닝 미작동 — 배포/조건 계층

### 소스: 코드는 존재 (반영됨)

`frontend/components/chainsight/MarketGraphCanvas.tsx` (현재 브랜치 `monorepo/sess-20-2-card-drilldown`, 파일 mtime 2026-07-21 09:50 = aa972b5):

```tsx
// :466-471 (⑳-2 S3② radial x/y 동기화)
node.fx = pos.fx; node.fy = pos.fy;
node.x  = pos.fx; node.y  = pos.fy;   // aa972b5에서 추가된 라인
// :481
fg.zoomToFit?.(400, 90);              // padding 80→90 (aa972b5)
```

- `onEngineStop={handleEngineStop}` 연결(`:867` 부근), centerSymbol 변경 시 graphData 재생성 → ForceGraph2D 리마운트 → onEngineStop 발화 조건 성립. **조건 미스 아님.**

### 빌드: 서빙 번들에 **미반영** (재빌드 필요)

- 실서빙 트리(`~/Desktop/stock_vis/frontend/.next`) `BUILD_ID` = `Dwq0DX9YlhYac8GqeiLro`, **파일 시각 2026-05-24 09:41**. 정적 청크 전부 05-24.
- aa972b5 커밋 시각 = **2026-07-21 09:50** ≫ 빌드 시각(05-24). 물리적으로 번들에 포함 불가.
- 추가로 aa972b5는 아직 main 미머지(현재 sess-20-2 브랜치 로컬). :3000이 원본 리포 트리(다른 브랜치)를 서빙하므로 소스에조차 미반영일 수 있음.

**Q4 결론**: **#62 빌드 함정 재발**. 지도 튜닝은 **소스에는 정상 반영, 서빙 번들 미반영** → **FE 재빌드(+ 브랜치 머지) 필수**. 조건 로직 수정은 불필요.

---

## 산출물 2 — 원인 분류 (확정)

"신뢰도 전원 85"의 원인:

| 후보 | 판정 | 근거 |
|---|---|---|
| **(a) DB 자체 균일** | ✅ **확정 (주 원인)** | truth_score distinct 6종(0/35/60/85 지배). truth 관계(공급/경쟁/의존)는 tier1/grade-high → **85 고정**(COMPETES 96%·SUPPLIES 87%). NVDA 상위 21개가 전부 85. tier/grade 하드코딩(`relation_tasks.py:288·329·368`, SEC grade). |
| (b) API 기본값/클램프 | ❌ 아님 | `ego_views.py:198` `round(truth_score or 0.0, 2)` — fallback은 0.0, 85 아님. 정규화/클램프 없음(`:9`). |
| (c) 표시 반올림 | ❌ 아님 | `round(x, 2)`만. 이미 정수 계단값이라 반올림 영향 없음. |

**부속 결함(재설계 필수 입력)**:
- **C1. 이질 점수 혼합축**: 유형별 소스·스케일 상이한 점수를 truth_score 한 축에 섞음.
- **C2. market 관계 배제**: CO_MENTIONED·PRICE_CORRELATED는 truth_score=0 → truth 정렬 카드에서 사실상 안 보임(NVDA 56%).
- **C3. tie-break 부재**: 단일 키 정렬로 동점 순서 비결정적.
- **C4. evidence_count 의미 불일치**: SEC 유형은 근거 존재해도 카운터 0(272건). "근거 0건" 표기가 오해 유발.
- **C5. last_mentioned 오의미**: auto_now 저장 시각을 "최근 언급일"로 표기.

---

## 산출물 3 — ⑳-G 설계 권고 스케치 (명세만, 구현 금지)

> UI 재설계의 1차 입력. 각 항목은 데이터 근거와 연결.

1. **유형별 섹션 분리 (C1 대응)** — 카드를 단일 랭킹이 아니라 관계 유형군으로 분리:
   - **공급망(truth)**: SUPPLIES_TO / DEPENDS_ON / PARTNER_WITH / COMPETES_WITH — "SEC 10-K 근거" 배지 + 근거 문장 노출.
   - **동종·산업(truth)**: PEER_OF.
   - **시장 신호(market)**: CO_MENTIONED / PRICE_CORRELATED — market_score 축으로 별도 표시.
   유형 내에서만 정렬해 이질 점수 비교를 없앤다.

2. **점수 축 분리 (C1/C2)** — truth_score와 market_score를 **다른 시각 채널**로. 신뢰도 숫자 하나로 뭉치지 말고 "관계 등급(높음/보통/약함=tier)" + "근거 유형"으로 표현. market 관계가 truth=0이라 사라지는 문제 제거.

3. **등급 라벨화 (C1)** — 85/60/35 원숫자 대신 tier→라벨(예: 확정/유력/약함). 이산 계단값을 연속 신뢰도인 척하지 않는다. 원점수는 툴팁/보조.

4. **근거 노출 (C4)** — "근거 N건" 대신 `relation_basis_summary`(SEC 문장·"뉴스 동시출현 N회"·"주가 상관 0.75")를 카드 본문에 노출. co-mention은 `co_mention_count`, price는 `correlation` 값이 evidence_sources에 있음.

5. **시간 라벨 정정 (C5)** — "최근 언급일" 표기 폐기 또는 재정의. `last_observed_at`은 배치 실행 시각임을 반영("마지막 갱신")하거나, 진짜 언급일이 필요하면 CoMentionEdge.`last_co_mention_date`(뉴스 실제 최종 동시출현일) 사용 검토.

6. **정렬 tie-break 명세 (C3)** — 유형 내 2차 정렬 키 확정: `evidence_count_total DESC` → `last_observed_at DESC` → symbol. `RelationPairSnapshot.truth_edge_count`(동점 보강도)도 후보. (백엔드 additive 변경, 별도 슬라이스)

7. **RC 정규화 트랙 선행 필요 판정**:
   - **UI 재설계만으로 대부분 해소 가능** (유형 분리 + 등급 라벨 + 축 분리). 정규화 없이도 "무변별" 인식은 제거된다.
   - 단 **유형 간 비교(랭킹 통합)를 원하면 정규화 트랙이 선행 필요** — 현재 truth/market/SEC-grade가 이질 스케일이라 하나의 0~100으로 합치려면 재산정 필요. ⑳-G가 유형 분리 노선을 택하면 정규화는 **불필요/후순위**.

---

## 산출물 4 — Q4 결론

- 지도 튜닝(aa972b5) **소스 정상 반영, 서빙 번들 미반영** → **FE 재빌드 필수**(#62 재발). 조건 로직 수정 불필요.
- 후속: aa972b5~2c74160(sess-20-2 브랜치)의 main 머지 + `frontend` prod 재빌드(`npm run build && npm run start`) 후 라이브 스모크. 배포는 **명시 승인 게이트** 대상(feedback: 배포·공유main 접촉).

---

## DoD 체크

- [x] Q1~Q4 실측 근거(SQL 결과·코드 라인) 전부 기재, 추측 표현 배제
- [x] 분포표(전체/NVDA/유형별) · 원인 분류(a/b/c) · ⑳-G 권고 완성
- [x] 코드 diff 0 증빙 (`git status --short` 공백)
- [x] HALT 조건(데이터 정합 파괴 징후) 미발생 — SELECT만, RC 13,699행 무변경
