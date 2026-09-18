# SCB-CONTEXT-S1 §1 실측 보고 — 성적판 카드 "당시 맥락(news)" 층

- 실행: 2026-09-17 18:00 ~ 2026-09-18 KST · 구동 트리 `~/worktrees/sv-scb-s1` · 브랜치 `monorepo/sess-scb-s1`
- `origin/main`(측정 시점 09-17 18:09) = **`e2e4aa9a`** — 디렉터 앵커 `c121e807`에서 9커밋 전진(`is-ancestor` 확인 = 되감김 아님)
- health_check: **✅20 / ⚠1 / ❌0** (⚠1 = `runtime_check` 24h WARN `@2026-09-16T09:43:14Z`, 선존·본 슬라이스 무관)
- 성격: 읽기 전용 실측. **코드 변경 0 · DB 쓰기 0 · 마이그 0 · 외부 콜 0 · 본체 무접촉(#42)**
- 선행: `D-SCB-CONTEXT-SOURCE-1`(2026-09-17) · `docs/mgmt/SCB-CONTEXT-RECON_report.md` · `docs/mgmt/SCB-RECOVER-PROBE_report.md`

> **결론 선반영 (2026-09-18 디렉터 결정)**: 이 실측의 결과로 **S1은 보류되고 S2가 선행**한다.
> 맥락 축 판정 **GREEN → AMBER**(`D-SCB-CONTEXT-SOURCE-1 정정`, DECISIONS 2026-09-18).
> 본 문서는 **S1 재개 시 목업·설계 재료**로 다시 쓰기 위해 남긴다 — 특히 §1-E 원문 3세트.

---

## 1-A 경계 — `apps/portfolio` 가 뉴스를 읽어도 되는가 (셋 분리)

### ① 아키텍처 테스트: **걸리지 않는다 (GREEN)**

`tests/architecture/test_shared_boundary.py`:
- `FORBIDDEN_TOP_SEGMENTS = ("apps", "macro")` — **`services` 없음**
- 스캔 루트 = `SHARED_ROOT = packages/shared` **한 곳뿐** → `apps/*`는 스캔 대상이 아님
- `KNOWN_VIOLATIONS` 실제 원소 **1건**: `("stocks/services/eod_signal_calculator.py", "apps.monitor.models.monitor")`
- ⚠ **docstring stale**: 같은 파일이 *"현재 묵은 부채 5건"* 이라 쓰지만 실제 1건(#1~#5는 주석이 청소 완료 기록). → TASKQUEUE `CB42-STALE-FIX` 묶음에 동반 정정 등재.

`tests/architecture/test_llm_direct_call_boundary.py` — LLM SDK 직접 호출만 검출. 이 슬라이스는 **LLM 호출 0 → 걸리는 조항 없음**.

### ② 선례: **있다 (GREEN)**

AST 전수(`ast.walk`로 Import/ImportFrom, grep 아님):

| 방향 | 건수 | top-level | lazy |
|---|---|---|---|
| `apps/*` → `services.*` | 20 | 1 | 19 |
| `apps/*` → `services.news*` | **16** | 0 | **16** |
| `packages/shared/*` → `services.*` | 14 | 2 | 12 |
| `packages/shared/*` → `services.news*` | **6** | 0 | **6** |

대표 3건:
- `apps/chain_sight/services/story_source.py:91` — `from services.news.models import NewsEntity`
- `apps/dashboard/services/strip_service.py:159` — `from services.news.models import NewsArticle`
- `apps/market_pulse/regime/grounding.py:73` — `from services.news.models import NewsArticle`

**`services.news` 접촉 22건이 예외 없이 전부 lazy.** 왜 lazy인지 설명하는 **코드 주석은 한 건도 없다(미확인)**. 다만 실측 패턴은 명확: **모델 import는 전부 lazy**, top-level 3건은 전부 **순수 함수/서비스**(`peer_adjudicator.py:19` → `services.sec_pipeline.grounding.normalize`, `views_screener.py:18` → `enhanced_screener_service`).

### ③ 규약 문언: **충돌하지 않으나 침묵 (AMBER)**

`docs/claude_project_instructions/project_convention_instruction.md:9` = *"`apps → shared`만 허용."* — 규정 대상은 **shared를 향한 방향**이고 근거 직관도 *"shared가 특정 앱을 알기 시작하면"*이다. **`services/` 층은 규약 문언에 등장하지 않는다.** line 16은 가드를 *"`packages/shared` 안의 `from apps.*`를 AST로 스캔"*으로만 정의한다. 문자 그대로면 `apps → services`도 문언 밖이지만, **가드도 선례도 금지하지 않는다 — 공백이지 금지가 아니다.**

### ★ §0-7 하네스 충돌 상신 → **디렉터 채택(2026-09-18)**

S1 지시서 §3-6 *"어댑터가 필요하면 `packages/shared`에 두되"* 는 `packages/shared/stocks/services/news_source.py:6-8` 원문과 정면 충돌한다:

> 실뉴스(NewsEntity, `services.news`) 기반 구현은 **앱 계층 슬라이스**에서 이 프로토콜을 만족시키는 어댑터를 주입한다 — shared는 `apps.*`/`services.*`를 import하지 않는다 (단방향 경계 · D-BOUNDARY-NO-DYNAMIC-EVASION: 동적 import 우회도 금지).

→ **§3-6 철회. S1 재개 시 어댑터는 앱 계층.** (`D-BOUNDARY-NO-DYNAMIC-EVASION` = DECISIONS 2026-08-31)

---

## 1-B 주입 경로 — 실측 비용

### 현행 응답 (`h=21`, 실호출 1회)

| 항목 | 값 |
|---|---|
| 신호 총 개수 | **315** |
| 심볼 수 | **9** — AAPL·GEV·GOOGL·IONQ·IREN·NVDA·PLTR·TLN·TSLA |
| 응답 바이트 | **87,012 B** |
| 계산 시간 | **204.1 ms** |
| 쿼리 수 | **23** |
| status | scored 117 / pending 198 / **unscoreable 0** |
| verdict | hit 52 / miss 65 / null 198 |
| 신호 1건 | 320 B · 키 10종(`captured_at·cohort·direction·maturity_date·pending_d_day·realized·spot_at_capture·status·target_price·unscoreable_reason`) |
| board | `sample_n=117 · direction_hit 52/117 · avg_target_progress=-21.52 · cross_sectional_ic=-0.1728` |

### 조인 비용 (±3일 창, 신호당 최대 3건)

| 방식 | 쿼리 수 | 실소요 | 비고 |
|---|---|---|---|
| (a) StockNews 신호별 1쿼리 | **315** | **382.2 ms** | 1.21 ms/쿼리 · 회수 907행 |
| (b) StockNews 심볼별 배치 | 9 | 434.6 ms | 전기간(07-31~09-19) 12,709행 **과회수** |
| (c) StockNews 단일 쿼리 | **1** | **41.7 ms** | `symbol__in` + 전기간 · 12,709행 |
| (d) NewsEntity 신호별 1쿼리 | 315(환산) | **~3,017 ms** | 50건 표본 9.58 ms/쿼리 |

`EXPLAIN ANALYZE`:
```
StockNews : Index Scan using stocks_stoc_symbol_ea398f_idx on stocks_stock_news
            Index Cond: symbol='NVDA' AND published_at BETWEEN ...
            Planning 3.867 ms · Execution 0.095 ms
NewsEntity: Nested Loop
            -> Index Scan Backward using news_articles_published_at_dc680f7e (rows=44)
            -> Index Scan using news_entities_news_id_78710381
                 Filter: symbol='NVDA'  ← Rows Removed by Filter: 1 (loops=44)
            Planning 7.431 ms · Execution 0.833 ms
```
→ StockNews는 `(symbol, -published_at)` 복합 인덱스 **직격**. NewsEntity는 시간창을 먼저 훑고 **symbol을 필터로 버린다**(3행 얻는 데 44 loops).

### payload 증가 — **실측(추산 아님)**

실제 뉴스 행을 315개 신호 전부에 붙여 직렬화:

| 항목 | 값 |
|---|---|
| base | 87,012 B |
| 추가 | **+269,950 B** |
| **증가율** | **+310.2%** |
| 총 | 356,962 B |
| 뉴스 1건 평균 | 298 B |
| 신호당 건수 | 3건 292 / 2건 11 / 1건 9 / **0건 3** |

> `SCAN-B2`의 `D-SCAN-R1-CORRECTION` 관찰 ⑵에서 문제가 된 사례가 **+26%**였다. 같은 조건에서 이 슬라이스는 **+310%**.
> **S1 재개 시 상한 = base 대비 +15%(약 +13 KB)** — 인라인 3건은 상한의 **20배**라 재개 시에도 불성립(lazy 로드 전제).

### 후보별

| 후보 | 위치 | 실측 |
|---|---|---|
| **가** | `build_scorecard` 내부 | 모듈 docstring: *"**데이터만 사용한다(재현 좌표 규약, 규칙 2)**. SCORING_VERSION 상수로 버전 박제"* / 함수 docstring: *"computed_at은 뷰가 캐시 저장 직전 주입(**순수성 유지** — 여기선 미포함)"*. 산출 `reproduction`에 `input_rows{ass_rows, daily_price_rows}`·`splits_input_rows`·`git_head`를 박는 **재현 좌표 계약**을 갖는다. 뉴스 ORM 읽기를 넣으면 재현 좌표에 뉴스 축이 **없는 채로** 산출물이 뉴스에 의존한다(계약 불일치). 파일이 `packages/shared` 소속이라 1-A ③ 충돌도 여기서 발생. |
| **나** | `apps/portfolio/api/scorecard.py` 후처리 | 뷰 82줄 전수: ① `h` 파싱·범위검증(1~504) ② `scorecard_cache_key(h)` ③ `cache.get` ④ miss면 `build_scorecard` + `computed_at` 주입 + `cache.set(TTL 24h)` ⑤ `Response`. **그 외 없음.** 조인이 캐시 **안쪽**이면 1-C 문제 발생, **바깥쪽**이면 매 요청 조인 비용(41.7~382 ms). |
| **다** | 신규 엔드포인트 | 신규 라우트 1 + 권한(기존 `IsAuthenticated` 재사용 가능) + 캐시 신규 정의. FE 추가 호출 = **심볼 행 펼칠 때만**(1-F: 펼침이 심볼 레벨) → 최악 9회. 성적판 payload 증가 **0 B**. |

---

## 1-C 캐시 상호작용 — ★ 함정 확인됨

### 키 전 좌표 (`apps/portfolio/api/scorecard.py:39-50`)

```
scoreboard:v{SCORING_VERSION}:h{h}:{AnalystSignalSnapshot.max(captured_at).date()}:{DailyPrice.max(date)}:{StockSplit.max(date)}
```
4좌표 + 버전. `SCORECARD_CACHE_TTL = 60*60*24` (**24h**).

### 뉴스 갱신 시 회전하는가 — **아니오**

**`StockNews`·`NewsArticle`·`NewsEntity` 어느 것도 키에 없다.**

함수 docstring은 *"데이터가 갱신되면 키가 회전 → **낡은 payload 반환 구조적 불가**"* 라고 보증한다. **payload에 뉴스를 넣는 순간 이 보증이 뉴스 축에 대해 거짓이 된다** — 주석과 실제가 갈라지는 것이 함정의 본체다.

**구체적 결과**: 3좌표 중 하나라도 바뀌면 함께 갱신되므로 실질 회전 주기는 **1일**(평일 `DailyPrice.max(date)`·snapshot 날짜가 매일 전진). 즉 **뉴스는 최대 24시간, 실질적으로 다음 EOD 적재까지 고정**된다 — 카드가 "어제 뉴스"를 오늘 내내 보여준다.

### 뉴스 좌표 추가 시 무효화 빈도 (실측)

최근 7일 일별 유입:

| 날짜 | StockNews | NewsArticle | NewsEntity |
|---|---|---|---|
| 09-17 | 103 | 176 | 103 |
| 09-16 | 1,360 | 2,668 | 2,999 |
| 09-15 | 3,355 | 3,000 | 3,355 |
| 09-14 | 2,783 | 2,408 | 2,783 |
| 09-13 | 758 | 533 | 758 |
| 09-12 | 1,316 | 1,000 | 1,316 |
| 09-11 | 3,188 | 2,701 | 3,188 |

좌표 입도별 24시간 무효화 횟수(최근 24h distinct 실측):

| 입도 | StockNews | NewsArticle |
|---|---|---|
| **날짜**(`.date()`) | **1회/일** | 1회/일 |
| **시간** | 10회/일 | 미측정 |
| **분**(= `max(published_at)` 원본) | **230회/일** | **339회/일** |

`max(published_at)`을 그대로 넣으면 **하루 230~339회 재계산**(204 ms + 조인 41.7~382 ms). 날짜로 절삭하면 현행과 같은 1회/일이지만 **당일 유입분이 다음날까지 반영되지 않는다**(문제가 형태만 바뀜).

### 후보별 발생 여부

| 후보 | 발생 | 사유 |
|---|---|---|
| 가 (build_scorecard 내부) | **발생** | 뉴스가 캐시 payload 안에 들어감 |
| 나-안쪽 (캐시 전 조인) | **발생** | 동일 |
| 나-바깥쪽 (캐시 후 조인) | **미발생** | 뉴스가 캐시를 통과하지 않음. 대신 매 요청 조인 비용 |
| 다 (별도 엔드포인트) | **미발생** | 성적판 캐시 무관. 자체 캐시 독립 설계 |

---

## 1-D 원천 — `StockNews` vs `NewsEntity`

| 항목 | StockNews | NewsEntity (+ NewsArticle) |
|---|---|---|
| 행 수 | **117,287** | **632,528** (article 499,980) |
| 최신 발행 | 2026-09-16 18:46 UTC | 2026-09-16 21:41 UTC |
| 고유 심볼 | **6,354** | **12,183** |
| 인덱스 | **`(symbol, -published_at)`** ★ · `(sector,-pub)` · `(industry,-pub)` · `(-pub)` | `(symbol, entity_type)` · `(sentiment_score)` · unique`(news,symbol)` — **`(symbol, published_at)` 없음**(published_at은 article 소유) |
| 카드 제공 필드 | `headline` · `summary` · `source` · `url` · `published_at` · `sentiment`(**문자열**) · `sector` · `industry` | `news__title` · `news__source` · `news__url` · `news__published_at` · `sentiment_score`(**실수**) · `entity_type` |
| 조인 실측 | 1.21 ms/쿼리 · Index Scan | 9.58 ms/쿼리 · Nested Loop |

### 커버리지 교차 — **StockNews ⊂ NewsEntity 실증**

최근 90일, URL 집합 비교:

| 심볼 | StockNews | NewsEntity | URL 교집합 | **SN 전용** | NE 전용 |
|---|---|---|---|---|---|
| AAPL | 2,388 | 5,083 | 2,388 | **0** | 2,695 |
| GEV | 315 | 458 | 315 | **0** | 143 |
| GOOGL | 1,731 | 3,381 | 1,731 | **0** | 1,650 |

**StockNews 전용 행은 3심볼 모두 0건** → StockNews는 NewsEntity의 **부분집합**(`newsfix-sync-stocknews` 물질화 산물). 9심볼 전체 NE/SN 비율 = TLN 1.50 ~ AAPL 2.13.

전 심볼 90일(SN / NE): AAPL 2388/5083 · GEV 315/458 · GOOGL 1731/3381 · IONQ 128/157 · IREN 111/134 · NVDA 5843/10852 · PLTR 785/1271 · TLN 26/39 · TSLA 1382/2955

### 주입 seam (`packages/shared/stocks/services/news_source.py`)

`NewsSource` = `@runtime_checkable Protocol`, 메서드 **3종** — **전부 "최신 1건"만 반환**:
```python
latest_on_date(symbol, target_date) -> Optional[Any]
latest_between(symbol, start_date, end_date) -> Optional[Any]
latest_by_industry_between(industry, start_date, end_date) -> Optional[Any]
```
반환은 duck-typed 객체로 `headline, summary, source, url, sentiment, published_at` 보유.

`tests/unit/stocks/test_eod_news_enricher_source_injection.py`가 증명하는 seam: 가짜 source 주입으로 enricher 관통 — ①실뉴스 매칭 ②무뉴스→profile 폴백 ③match_type/confidence 회귀 보존 ④창 규약(today/7d/30d) ⑤출력 형상 무변 + `EODPipeline`이 `news_source`를 주입받아 보관.

**NewsEntity 어댑터는 만들 수 있다**(필드 1:1 매핑 가능). 제약 2건:
1. 프로토콜이 **1건만** 반환 → 카드에 3건을 보이려면 **프로토콜 확장**(신규 메서드) 필요 = 기존 seam 계약 변경.
2. 어댑터 위치는 **앱 계층**(docstring 명시 · 1-A ★ 참조).

### 판정

| 원천 | 판정 | 사유 |
|---|---|---|
| **StockNews** | **GREEN** | 복합 인덱스 직격 · 1.21 ms · 기존 `StockNewsSource` 재사용 · shared 내부라 경계 문제 0 |
| **NewsEntity** | **AMBER** | 커버리지 1.2~2.1배 우위 · `sentiment_score` 수치 보유. 단 인덱스 부재로 **8배 느림** · 어댑터 신설 · 경계 결정 선행 |

---

## 1-E 목업용 실데이터 3세트 — **제목 원문 그대로 (무가공)**

> 현행 성적판에 `unscoreable`은 **0건**이라 3번째는 `pending`으로 대체.
> `captured_at`은 payload에서 **날짜 문자열**(tz 포함 **0/315**) → ±3일 창은 날짜 기준.
> 두 원천이 **세 세트 모두 동일 5건·동일 순서**를 반환했다(차이는 sentiment 표현형뿐).

### ① 적중(hit) — AAPL

```
direction=up · captured_at=2026-08-03 · spot_at_capture=303.42 · target_price=341.11
maturity_date=2026-09-01 · status=scored · cohort=derived · unscoreable_reason=null · pending_d_day=null
realized: close=325.13 · return_pct=7.16 · target_progress_pct=57.6 · verdict=hit
```
±3일 창 **2026-07-31 ~ 2026-08-06**

| published_at | source | SN `sentiment` / NE `sentiment_score` | TITLE (원문) |
|---|---|---|---|
| 2026-08-06 14:54:41+00 | SeekingAlpha | `''` / `None` | `Apple: Next Month Will Decide Everything` |
| 2026-08-06 14:45:57+00 | Yahoo | `''` / `None` | `Without a new budget iPad, Apple tablet demand slows` |
| 2026-08-06 14:42:51+00 | Benzinga | `''` / `None` | `7 Back-to-School Stocks to Buy Now` |
| 2026-08-06 14:27:04+00 | insurancejournal.com | `'neutral'` / `0.053` | `OpenAI Asks Judge to Toss Apple’s Trade Secrets Lawsuit` |
| 2026-08-06 13:32:59+00 | Yahoo | `''` / `None` | `'Apple is scrambling to get enough memory chips': RAM crisis is causing panic about incoming iPhones and MacBooks, as Microsoft deletes past advice to aim for 32GB ideally` |

URL 원문:
```
https://finnhub.io/api/news?id=03f771aebd433d959395f0c78593db8f3a94274bee77b67b4cc2be042aefa789
https://finnhub.io/api/news?id=4a999dff1a5bb291992f2bcbf103226d199a6e55a9da8abeffb39fb3fa9f1c90
https://finnhub.io/api/news?id=70455ea9442403e8ee75d73866ba28189d67ba110062d3c1e899605d4213a088
https://www.insurancejournal.com/news/national/2026/08/06/880579.htm
https://finnhub.io/api/news?id=b3a81f06f03381c9691dbafa51f1b51d7b50697b9cf9cc802317d57866cf8c67
```
`grades_historical` (snapshot `captured_at=2026-08-05 22:30:27.469207+00`) 원문:
```json
{"date": "2026-08-01", "symbol": "AAPL", "analystRatingsBuy": 22, "analystRatingsHold": 14, "analystRatingsSell": 2, "analystRatingsStrongBuy": 6, "analystRatingsStrongSell": 2}
{"date": "2026-07-01", "symbol": "AAPL", "analystRatingsBuy": 23, "analystRatingsHold": 17, "analystRatingsSell": 2, "analystRatingsStrongBuy": 6, "analystRatingsStrongSell": 2}
```

### ② 빗나감(miss) — GEV  ★ 이 세트가 S1 보류 결정의 실물 근거

```
direction=up · captured_at=2026-08-03 · spot_at_capture=1006.76 · target_price=1256.29
maturity_date=2026-09-01 · status=scored · cohort=derived · unscoreable_reason=null · pending_d_day=null
realized: close=898.53 · return_pct=-10.75 · target_progress_pct=-43.37 · verdict=miss
```
±3일 창 **2026-07-31 ~ 2026-08-06**

| published_at | source | SN / NE | TITLE (원문) |
|---|---|---|---|
| 2026-08-05 22:46:53+00 | Splash247 | `'positive'` / `0.250` | `Valaris lands new contracts as backlog reaches $4.6bn` |
| 2026-08-05 21:41:19+00 | energynews.pro | `'neutral'` / `0.146` | `Terra Innovatum Joins Solactive Index Tracked by Global X Uranium ETF` |
| 2026-08-05 20:23:07+00 | fool.com | `''` / `None` | `Here's Why This AI-Related Power Company's Stock Declined in July` |
| 2026-08-05 16:16:22+00 | Pluang | `'positive'` / `0.441` | `Defiance AI & Power Infrastructure ETF targets growth in AI-driven power and data center sectors, rated BUY despite high valuations.` |
| 2026-08-04 22:06:58+00 | TradingKey | `'neutral'` / `0.132` | `AES Corp (AES) - Stock Score & Comprehensive Stock Analysis` |

URL 원문:
```
https://splash247.com/valaris-lands-new-contracts-as-backlog-reaches-4-6bn
https://energynews.pro/en/terra-innovatum-joins-solactive-index-tracked-by-global-x-uranium-etf
https://www.fool.com/investing/2026/08/06/heres-why-this-ai-related-power-companys-stock-dec
https://pluang.com/en/news-feed/aipo-ekspose-terpadu-revolusi-ai
https://www.tradingkey.com/markets/stocks/aes/stock-analysis
```

> 🔴 **5건 중 GE Vernova를 다룬 제목은 0건이다.** Valaris(시추)·Terra Innovatum(우라늄)·AES(타 유틸리티)·ETF 2건.
> 디렉터가 이 실물로 목업을 그린 결과: *"카드가 '그때 무슨 일이 있었나'라는 제목으로 무관한 기사를 보여준다. 빗나간 신호일수록 사용자가 펼치므로 **가장 중요한 순간에 가장 크게 어긋난다**."*

`grades_historical` (`captured_at=2026-08-05 22:30:32.329296+00`):
```json
{"date": "2026-08-01", "symbol": "GEV", "analystRatingsBuy": 24, "analystRatingsHold": 8, "analystRatingsSell": 0, "analystRatingsStrongBuy": 6, "analystRatingsStrongSell": 0}
{"date": "2026-07-01", "symbol": "GEV", "analystRatingsBuy": 24, "analystRatingsHold": 8, "analystRatingsSell": 0, "analystRatingsStrongBuy": 6, "analystRatingsStrongSell": 0}
```

### ③ 미채점(pending) — AAPL

```
direction=up · captured_at=2026-08-19 · spot_at_capture=310.03 · target_price=340.72
maturity_date=2026-09-17 · status=pending · pending_d_day=0 · realized=null · unscoreable_reason=null · cohort=pinned
```
±3일 창 **2026-08-16 ~ 2026-08-22**

| published_at | source | SN / NE | TITLE (원문) |
|---|---|---|---|
| 2026-08-22 11:23:00+00 | Yahoo! Finance Canada | `'neutral'` / `0.021` | `Jim Cramer Wants You To Look At The Bigger Picture For Apple Inc. (NASDAQ:AAPL)` |
| 2026-08-22 11:08:50+00 | Fortune | `'neutral'` / `0.131` | `Nvidia customers notified about AI-related price hikes above 15%` |
| 2026-08-22 09:06:59+00 | Foreign Policy Journal | `'neutral'` / `0.092` | `Apple (NASDAQ: AAPL) Cuts Over 200 Jobs In Siri And Vision Pro As Company Pivots To AI And Smart Glasses` |
| 2026-08-22 07:37:00+00 | Investing.com | `'positive'` / `0.380` | `Will Apple’s risk appetite change under John Ternus?` |
| 2026-08-22 06:04:59+00 | Top Class Actions | `'negative'` / `-0.620` | `Apple faces class action over alleged ‘bricking’ of older Apple Watch models` |

URL 원문:
```
https://ca.finance.yahoo.com/news/jim-cramer-wants-look-bigger-002325692.html
https://fortune.com/2026/08/22/nvidia-customers-ai-related-price-hikes-15-percent-vera-rubin-grace-blackwell-chips
https://www.foreignpolicyjournal.com/2026/08/22/apple-nasdaq-aapl-cuts-over-200-jobs-in-siri-and-vision-pro-as-company-pivots-to-ai-and-smart-glasses
https://www.investing.com/news/stock-market-news/will-apples-risk-appetite-change-under-john-ternus-4872375
https://topclassactions.com/lawsuit-settlements/lawsuit-news/apple-faces-class-action-over-alleged-bricking-of-older-apple-watch-models
```
`grades_historical` (`captured_at=2026-08-21 23:30:05.237969+00`):
```json
{"date": "2026-08-01", "symbol": "AAPL", "analystRatingsBuy": 22, "analystRatingsHold": 14, "analystRatingsSell": 3, "analystRatingsStrongBuy": 6, "analystRatingsStrongSell": 2}
{"date": "2026-07-01", "symbol": "AAPL", "analystRatingsBuy": 23, "analystRatingsHold": 17, "analystRatingsSell": 2, "analystRatingsStrongBuy": 6, "analystRatingsStrongSell": 2}
```

### 레이아웃 재료 (목업용 사실)

- **뉴스가 `captured_at` 당일이 아니라 창 끝(+3일)에 몰린다** — `-published_at` 정렬이라 "가장 최신"이 먼저 온다. 신호 시점 근처를 보이려면 **정렬 기준이 다른 문제**다.
- 제목 길이 실측: 최단 **32자**(`7 Back-to-School Stocks to Buy Now`), 최장 **192자**(AAPL RAM crisis). **한 줄 고정폭은 성립하지 않는다.**
- `sentiment`: StockNews는 문자열이며 **빈 문자열 `''`이 흔하다**(①은 5건 중 4건). NewsEntity `sentiment_score`는 `None`이 섞이나 값이 있으면 −0.620 ~ 0.441 실수.
- 뉴스 0건 신호 = 315건 중 **3건**.

### ★ 부수 정량화 — 제목 관련성 (지시 범위 밖·하한값)

①~③ 세트를 보고 의심이 생겨 9심볼 315신호 전체(회수 925행)에서 **제목에 심볼 또는 회사명이 등장하는 비율**을 셌다:

| 심볼 | 비율 | 심볼 | 비율 |
|---|---|---|---|
| IREN | 76.2% (80/105) | TSLA | 62.9% (66/105) |
| TLN | 67.8% (59/87) | AAPL | 42.9% (45/105) |
| PLTR | 65.7% (69/105) | GOOGL | 37.1% (39/105) |
| IONQ | 62.1% (64/103) | NVDA | 29.5% (31/105) |
| | | **GEV** | **10.5% (11/105)** |

**전체 464/925 = 50.2%.** 브랜드명·자회사명·제품명을 못 잡으므로 **하한값**. 성적판 카드에 뉴스를 붙이면 **대략 절반은 그 종목 이름이 제목에 없는 기사**가 뜬다.

**이 측정이 이 슬라이스의 방향을 바꿨다.** 교차 근거 = CS-S3 `docs/reports/cs_s3_comention_provenance_recon.md`(09-15 prod) 주어 적중 **18/50 = 36%**(역시 하한값). 두 측정이 **독립적으로 같은 벽**을 가리킨다.

---

## 1-F 프런트 현황

| 파일 | 줄 | 역할 |
|---|---|---|
| `frontend/types/scorecard.ts` | 62 | BE `build_scorecard` 계약을 손으로 유지하는 단일 소스(serializer가 passthrough라 openapi 생성 타입 없음) |
| `frontend/services/scorecardService.ts` | 12 | `authAxios.get('/coach/analyst-scorecard/', {params:{h}})` |
| `frontend/hooks/useScorecard.ts` | 17 | TanStack `useQuery`, 키 `['analyst-scorecard', h]` |
| `frontend/components/scorecard/ScorecardSection.tsx` | 81 | 훅 호출 + 로딩/에러/빈 4상태 + **섹션 접힘**(`useState` + Chevron) |
| `frontend/app/advisory/page.tsx` | 173 | My 탭 권유 화면. `:160`에서 `<ScorecardSection />` 장착 |

**렌더 경로**:
```
app/advisory/page.tsx:160
  └ ScorecardSection            (useAnalystScorecard · 섹션 접힘 useState)
      ├ ScoreStrip              (board 요약)
      └ ScoreboardBoard         (scorecard 전문)
          └ SymbolRow           ★ useState open · button[data-testid=symbol-toggle-{sym}]
              └ {open && sym.signals.map(...)}
                  └ SignalCard  ← 신호 1건 (95줄)
```

**expand 유무**: `SignalCard.tsx`에는 `useState`·`onClick`·`expand`가 **하나도 없다** — props `{ signal }`만 받는 무상태 presentational. **펼침은 심볼 행 레벨**(`ScoreboardBoard.tsx:27` `const [open,setOpen]=useState(false)` · `:34` toggle · `:50` `{open && ...}`). 신호 단위 펼침 추가 시 건드릴 곳 = `components/scorecard/SignalCard.tsx`(자체 상태 신설) 또는 `ScoreboardBoard.tsx`(상위 관리) — **위치만 기록**.

**기존 vitest**: `frontend/__tests__/scorecard/` 5파일 **26건** — `present.test.ts` 11 · `ScorecardSection` 5 · `SignalCard` 5 · `ScoreboardBoard` 3 · `ScoreStrip` 2.

---

## §2 게이트 결과 (2026-09-18 디렉터 판정)

**결정 = S1 보류 · S2 선행(순서 반전).** 가중합 안1 3.20 / 안2 3.55 / 안3 3.05 / **안4(S2 선행) 4.60** — 마진 **1.05 > 1.00 = 자동 결정**.

- `D-SCB-CONTEXT-SOURCE-1` 맥락 축 **GREEN → AMBER**(정정 절 등재, DECISIONS 2026-09-18). 논거 축 판정은 **유지**.
- **S1 선행조건 = "뉴스↔종목 귀속 규칙 교정"**, CS-S3의 **S3-2 결정 사이클과 묶어서** 다룬다(각자 규칙을 만들면 갈라진다).
- **S1 재개 시 payload 상한 = base 87,012 B 대비 +15%(약 +13 KB)** — 본 실측 +310.2%는 상한의 20배.
- S1 지시서 **§3-6 철회** — 어댑터는 **앱 계층**.

### 디렉터 자기정정 (장부 보존)

> recon 지시서(2026-09-10) 맥락 축 질문은 *"심볼+날짜로 뽑을 수 있는가(인덱스 포함)"* 였다. **조회 가능성만 물었고 귀속 정확도는 묻지 않았다.** 그 GREEN을 근거로 `D-SCB-CONTEXT-SOURCE-1`에 "맥락 축 = 즉시 가용"이라 등재했다 — **"검색된다"를 "쓸 만하다"로 치환**한 것이며, 검증 4겹의 **③실질**을 건너뛴 유형이다. 게다가 **CS-S3 보고서는 09-15에 이미 main에 있었다.** S1 지시서를 쓰기 전에 `docs/reports/` 를 훑었으면 발견했다.

### 남은 미지수

**붙일 뉴스가 실제로 "그때 무슨 일이 있었나"에 답하는지의 참값.** 50.2%·36% 둘 다 **하한값**이라 상한을 모른다. GEV 10.5%가 정상 편차인지 매칭 결함인지 **미확인** — 판별은 귀속 규칙 교정 사이클(CS-S3 S3-2 묶음)의 몫이다.
