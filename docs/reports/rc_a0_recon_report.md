# RC-A-0 점수 눈금 위생 설계 실측 — 리콘 보고 (read-only)

- 실측일: 2026-08-26 12:35 KST (03:38 UTC)
- worktree: `monorepo/sess-rc-a0-recon` @ `/Users/byeongjinjeong/worktrees/sv-rc-a0` (origin/main `d6365630` 기준)
- DB write 0 · FMP 호출 0 · health 15 OK/1 WARN(#47)/0 ERROR
- RelationConfidence(RC) 총 17,238행 (memory 16,968 → 8월 유입으로 증가)

## STEP 0
- clock 정상 · origin/main `d6365630`(기대 `6f9c902f` 이후 ✓) · 실행트리=origin/main 정합
- worktree 다수(기존 세션 트리) — 예상 밖 없음

---

## PROBE 1 — RC-DECAY-CRIT-PROBE (감쇠 판정 재료)

**함수 위치 정정**: `check_stale_and_decay`는 relation_tasks.py **:289–322** (지시서 :406은 docstring 오프셋; :406은 apply_upward_learning 내부).

### (a) stale 판정 참조 필드 = `last_observed_at` (NOT last_computed_at)
```python
# relation_tasks.py:301-319
confirmed, last_observed_at__lt = now - 90d  →  stale
probable,  last_observed_at__lt = now - 60d  →  weak
weak,      last_observed_at__lt = now - 30d  →  hidden
```
`last_observed_at` = 모델 `auto_now=True` (relation_discovery.py:151). 즉 **"행이 마지막 save()된 시각"** ≠ "관계가 마지막 관측된 시각".

### (b) last_observed_at 실제 갱신 경로 (relation_type별 실측)
| relation_type | n | last_observed min | **last_observed MAX** | 갱신 주체 |
|---|---|---|---|---|
| CO_MENTIONED | 3,697 | 04-12 | **08-25 (fresh)** | update_or_create 매일 save()→auto_now bump |
| SEC 4종(COMPETES/SUPPLIES/DEPENDS/PARTNER) | 390 | 07-31 | **08-25** | SEC seed/8-K 재추출 |
| **PEER_OF** | 9,365 | 04-02 | **2026-06-20 (동결)** | **활성 재기록자 없음** — D2에서 착지루프 제거 |
| **PRICE_CORRELATED** | 3,784 | 04-17 | **2026-06-20 (동결)** | **착지 은퇴** — 신규/갱신 중단 |

- 감쇠 태스크는 `.update()`(bulk) 사용 → auto_now 미발화. 이는 정상(감쇠는 last_observed를 **읽는** 쪽).
- 핵심 결함: PEER_OF·PRICE_CORRELATED는 **어떤 save() 경로도 last_observed를 갱신하지 않아** 2026-06-20(D2 재설계 랜딩)에 **전량 동결**. 이들의 90일 시계는 사실상 "마지막 구조 마이그레이션 이후 경과일"이라는 무의미한 값.

### (c) stale=2가 정합인가? → **아니오. 동결 타이밍의 우연 + 감쇠 시한폭탄**
- 현재 stale 2행 = **둘 다 PRICE_CORRELATED** (CAT↔HUBB, GOOGL↔META), last_observed **2026-05-15**(06-20 대량 재저장보다 이른 동결). 05-15+90d=08-13 → 이미 넘겨 confirmed→stale 전이됨.
- 나머지 confirmed는 last_observed 06-19/06-20 → 90d 도달일 **≈2026-09-18**.
- **감쇠 대상 현재 시뮬**: confirmed→stale 0 · probable→weak 0 · weak→hidden 0 (전부 아직 미도달).
- **confirmed >60d 실측**: PEER_OF 1,790(전량) · PRICE_CORRELATED 264(전량) — 이미 60일 초과, 90일만 남음.
- **⚠️ 시한폭탄**: ~09-18 이후 첫 감쇠 실행 시 **confirmed 2,054행(PEER_OF 1,790 + PRICE_CORRELATED 264)이 단일 배치에서 일괄 confirmed→stale 폭발**. 관계가 변해서가 아니라 auto_now가 D2 랜딩에 동결됐기 때문. → "감쇠 헛돎"이 아니라 "감쇠 오발(false decay) 예약됨".

### (d) 감쇠 실행 시 변하는 것 = `relation_status`만 (+ neo4j_dirty=True)
- **점수(truth_score/market_score) 자체는 불변**. "점수 감쇠"가 아니라 "status 라벨 하향" 전용.

---

## PROBE 2 — RC-INFLOW-EPOCH-PROBE (유입 시점)

### 월별 신규 생성 (first_observed_at, 전 기간)
| 월 | 신규 | 비고 |
|---|---|---|
| 2026-04 | 12,911 | 초기 대량 시드(PEER_OF/PRICE_CORRELATED/CO_MENTIONED) |
| 2026-05 | 529 | |
| 2026-06 | 255 | |
| 2026-07 | **4** | 사실상 유입 정지 |
| 2026-08 | **3,539** | **재점화** |

### 8월 일별 (재점화 실측)
- 08-02: 2 → **08-10: 1,679(점화)** → 이후 매일 56~226 → **08-26(오늘): 142 already**
- 8월 신규 구성: CO_MENTIONED 3,419 + SEC 4종 120
- 마지막 신규 엣지: 2026-08-26 (오늘, 활발)

### 판정 → **"유입 0 / 유니버스 포화" 전제 반증**
- 7월은 실제로 ~0(4행)이었으나 **08-10 co-mention 신규생성 재점화**, 이후 매일 활발.
- RC 13.7k→17.2k 성장분 = **8월 co-mention surge**가 전부.
- upsert 경로(update_relation_confidence:253 update_or_create)는 **막혀있지 않음** — count≥2 신규 쌍 발견 시 정상 생성. 7월 공백의 원인은 경로 차단이 아니라 **뉴스 유니버스/추출의 8월 재개**(08-10 점화). "신규RC 0" 우려는 현시점 데이터로 무효.

---

## STEP A — 변환식 설계 재료

### 7. truth_score의 85 = **(a) 코드 상수 최대** (가중합 아님)
- 분포: `{0.0: 7481, 35: 699, 60: 6925, 85: 2131}` + outlier `{0.5:1, 0.6:1}`. 이산 계단 {0,35,60,85}.
- **Writer 3곳 전부 계단 상수**:
  - SEC seed `services/sec_pipeline/tasks.py:374` — `score_map={"high":85,"medium":60,"low":35}` (SUPPLIES/COMPETES/DEPENDS/PARTNER)
  - SEC 8-K `.../management/commands/extract_8k_relations.py:161` — `85 if conf>=0.8 else 60`
  - CO_MENTIONED `relation_tasks.py:262` — 항상 0
- **PEER_OF 9,365행 truth_score(35/60/85)는 제거된 레거시 경로 산물** — 활성 재기록자 없음. last_observed 06-20 동결과 겹쳐 **완전 휴면 데이터**.
- 임계 단일출처: `upward_learning.py:31 HIGHSCORE_THRESHOLD=85`, `:19 UPWARD_THRESHOLD=60`.
- **⚠️ 스케일 오염 흔적**: relation_type=`"PEER"`(≠PEER_OF) 2행(AAPL↔NVDA=0.6, MSFT↔GOOGL=0.5, 07-16 생성, serving_layer=pending) — [0,1] 스케일이 이미 테이블에 섞여있음. writer는 services/management 밖(일회성 시드 추정).

### 8. market_score — **Writer 1곳** (`relation_tasks.py:246`)
- CO_MENTIONED: count≥10→85 / ≥5→60 / else→35. 분포 {35:5664, 60:1455, 85:362}.
- PRICE_CORRELATED도 market_score 35/60/85 보유(은퇴된 레거시 writer). **truth와 동일 35/60/85 계단** — 두 축 눈금 동일.

### 9. score_version — **분기 코드 0건**
- 전 17,238행 `"2.1"` 단일값. 코드베이스에서 이 필드를 **읽거나 분기하는 곳 없음**. 2.1→3.0 승격 훅 부재 → 정규화 배포 시 버전 게이팅을 새로 만들어야 함(기존 분기에 얹을 수 없음).

### 10. 6 소비처 사용 방식 + 정규화 동반이동 상수
| 소비처 | 읽음 | 방식 | 하드코딩 임계 |
|---|---|---|---|
| **ego_views** (api/ego_views.py) | truth+market | (A)원값+(B)등급+(C)정렬 | **85/60/35 (:46/:48/:50)** ← 유일한 계단 하드코딩 · min_score default 0.0(:114) |
| centrality (services/centrality.py) | truth+market | (D) `max(truth,market)` edge weight(:22) | 없음 |
| **seed_selection** (services/seed_selection.py) | **점수 미소비** | relation_status 문자열만(:271 서열) | 없음(점수) |
| pair_aggregation (services/pair_aggregation.py) | truth+market | (D)max 집계 + **`/100.0`(:24/:25)** | /100 스케일 |
| strip_service (dashboard/services/strip_service.py) | truth만 | (B)동적 θ + (C)정렬 | 없음(θ=percentile 0.85 분포추종) |
| **advisory_engine** (portfolio/services/advisory_engine.py) | truth만 | (D)가중합 `CONF_WEIGHT*conf`(:332) | **CONF_WEIGHT=0.60(:268)** ← 스케일 불일치 최대점 |
| (+expand_service:79) | truth | `0.40*(truth/100)+...` | /100 스케일 |

**정규화 시 동반이동 마스터 리스트**:
1. `ego_views.py:46/48/50` = 85/60/35 (등급 계단)
2. `pair_aggregation.py:24/25` = /100.0 ×2
3. `expand_service.py:79-86` = /100
4. `advisory_engine.py:268` = CONF_WEIGHT 0.60 (+ :330 불변식 주석 0.48/0.20)
5. `ego_views.py:114` = min_score default 0.0
6. `upward_learning.py:31/19` = 85 / 60 (writer측 승급 임계)

**★ 이미 살아있는 눈금 결함**: 실 최대는 85인데 pair_aggregation·expand_service는 `/100`으로 나눔 → 현재 relevance/expansion 점수는 **최대 0.85에 고착**(1.0 미도달). advisory_engine은 원값[0,85]에 0.60을 곱해 타 성분([0,1])과 스케일 불일치. **눈금 위생 문제는 설계 대상이 아니라 이미 발생 중.**

- status↔점수 병행 게이트: **코드베이스에 없음**. seed_selection만 status 문자열 게이트, ego_views의 status는 표시 전용.

---

## STEP B — PRICE_CORRELATED 처분 재료

### 11. PRICE_CORRELATED 3,784행 실측
- 전량 `relation_category="market"`(생성 시 명시, 모델 default "truth" 무시) · truth_score=0 · market_score 35/60/85 · serving_layer="context".
- **3,784쌍 전부 PEER_OF로도 존재 (100% 중복쌍)** → 구조적 잉여. 모든 price-correlated 쌍은 이미 PEER_OF twin 보유.
- 소비처 분기: `pair_aggregation`은 relation_category로만 분기 → **PC는 truth_max에 무기여 / market_max·market_edge_count·relevance_risk에 기여(YES)**. `centrality`는 PC 포함(edge weight=market_score). `mindmap_views`·evidence 경로는 PC 제외(context). `ego_views`는 기본 포함(단 truth=0이라 최하위 랭크).

### 12. 삭제 영향 — RPS 궤적 정합성
- RPS 543,340행(period 07-01~08-25). 컬럼: canonical_a/b·period·truth_max·market_max·relevance_opp/risk·edge_count. **relation_type 컬럼 없음 · RC로의 FK 없음.**
- **삭제 판정**:
  - 과거 스냅샷 = forward-only 불변 → **과거 궤적 정합성 안 깨짐 · 고아행 0**.
  - 미래 배치: PC가 market-max였고 co_mention 부재인 쌍의 `market_max`/`market_edge_count`/`relevance_risk`가 재산정되어 값 이동(co_mention 공존하며 더 큰 쌍은 불변).
  - 부수: centrality PageRank/betweenness 이동, strip_service θ(PC의 truth=0 3,784행이 p85 분모 → 삭제 시 θ 상향).
  - truth 성분·evidence 서빙(mindmap)·RPS 과거행: **무영향**.

---

## 디렉터 회부 요약 (판정 필요 3건)
1. **DECAY-SEMANTIC**: last_observed_at(auto_now="save 시각")로 감쇠 판정 → PEER_OF·PRICE_CORRELATED 2,054행이 ~09-18 일괄 오발 예약. 감쇠 기준을 "증거 관측 시각"으로 분리할지, 재확인 없는 타입을 감쇠 대상에서 뺄지 결정 필요.
2. **SCALE-HYGIENE**: 눈금 [0,85] 이산 계단이 소비처마다 /100·max·×0.60로 제각각. 정규화 목표 눈금([0,1]? [0,100]?)과 위 6개 상수 동반이동 + score_version 게이팅 신설 여부.
3. **PRICE_CORRELATED 처분**: 100% PEER_OF 중복·context 미서빙·market 잉여. 삭제 안전(고아 0·과거궤적 불변)하나 미래 market_max/centrality/θ 이동. 삭제 vs sync_strength 흡수(P1B) 결정.

→ 전 스텝 read-only 완료. A-1(실행)·변환식·처분은 별도 세션 지시서.
