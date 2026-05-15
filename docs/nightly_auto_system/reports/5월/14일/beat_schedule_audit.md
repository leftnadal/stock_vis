# Beat Schedule Audit — 2026-05-14

> **소스**: `config/celery.py` (820 lines, beat_schedule 항목 64개)
> **시간 단위**: 모든 cron 표현은 **EST (America/New_York)** 기준으로 해석함 (`config/settings.py`의 `CELERY_TIMEZONE` 확인 권장)
> **Drift 주의**: `CELERY_BEAT_SCHEDULER = DatabaseScheduler` 사용. config dict는 reference, 실제 실행은 `django_celery_beat.PeriodicTask` 테이블 기준. 본 감사는 dict를 기준으로 한 "설계상의 분석"임. DB와 diff는 별도 점검 필요 (CLAUDE.md common-bug #28).

---

## 0. 요약 (Executive Summary)

| 항목 | 결과 | 심각도 |
|------|------|--------|
| **FMP 18:00 슬롯 폭주** | sync-sp500-eod-prices(503 symbols) + 4개 task가 동시 실행 → 300 calls/min Starter 한도 초과 가능 | **P0** |
| **Gemini 08:00~08:30, 18:30~18:45** | keyword-gen + analyze-deep + thesis-summaries 동시 호출 → 15 RPM 초과 위험 | **P0** |
| **neo4j queue solo pool 점유** | sec-sync-dirty-neo4j가 24/7 5분마다 → 다른 neo4j 태스크 대기 큐 적체 | **P1** |
| **12:00 슬롯 4중첩** | macro + market-news + chainsight-sync-profiles + sec-seed-relations 동시 | **P1** |
| **데이터 의존성 chain 위험** | thesis-pipeline (18:00→18:15→18:30→18:35) — 선행 실패 시 후행 빈 결과 | **P1** |
| **5분 단위 폴링이 가장 큰 부하원** | 시장시간 동안 realtime-prices + market-indices + market-pulse + portfolio-values + screener-alerts + sec-sync = 시간당 168 runs | **P2** |
| **Alpha Vantage 명시 의존 없음** | beat_schedule 직접 사용 0건. 단, 코드 fallback 경로는 별도 점검 필요 | OK |

---

## 1. Rate Limit 초과 구간 분석

### 1-1. FMP (Starter Plan: 300 calls/min, 10,000 calls/day)

#### FMP 의존 태스크 목록 (확인된 것만)

| 태스크 | 시간 | 추정 호출량 | 비고 |
|-------|------|------------|------|
| update-realtime-prices | 9-16시 매 5분 (평일) | batch quote API 사용 시 1~5/분, 개별 시 503/분 | 시장시간 96 runs/일 |
| update-market-indices | 9-16시 매 5분 (평일) | 4~6 indices = 적은 호출 | 시장시간 96 runs/일 |
| update-daily-prices | 17:00 (평일) | S&P 500 503개 가능 | 1 run/일 |
| sync-sp500-eod-prices | 18:00 (평일) | **S&P 500 503개 — 가장 무거움** | 1 run/일 |
| sync-sp500-financials | 20:00 (평일) | 101개/일 (5일 회전) | 1 run/일 |
| collect-sp500-news-fmp-* | 06:15, 10:15, 13:15, 15:15, 17:15 (평일) | orchestrator + 종목별 fanout | 5 runs/일 |
| collect-press-releases-fmp | 07:45 (평일) | max_symbols=50 | 1 run/일 |
| collect-general-news-fmp-* | 06:45, 12:30, 17:45 (평일) | 단일 호출 | 3 runs/일 |
| collect-market-news-* | 08:00, 12:00, 15:00, 18:00 (평일) | FMP 가능성 | 4 runs/일 |
| collect-category-news-* | 06:30, 07:00, 07:30, 13:00, 14:00, 17:00 (평일) | 카테고리별 fanout | 6 runs/일 |
| thesis-update-readings | 18:00 (평일) | 지표별 FMP 호출 (배치 sync) | 1 run/일 |
| run-eod-pipeline | 18:30 (평일) | 시그널 계산용 | 1 run/일 |

#### 🚨 P0 위험: 18:00 슬롯 폭주

```
18:00:00  sync-sp500-eod-prices         (S&P 500 503 calls, 약 1~2분)
18:00:00  thesis-update-readings        (지표 FMP 호출, 동시 시작)
18:00:00  collect-market-news-evening   (FMP 시장 뉴스)
18:00:00  update-economic-indicators    (FRED, FMP 영향 없음 — OK)
18:15:00  classify-news-batch (Gemini)  (8시간 누적 분류)
18:15:00  thesis-calculate-scores
18:30:00  analyze-news-deep-batch       (Gemini, 최대 50 articles)
18:30:00  run-eod-pipeline              (시그널 계산)
18:30:00  thesis-create-snapshots
18:30:00  update-sp500-change-percent
18:35:00  thesis-generate-summaries     (Gemini)
18:45:00  sync-news-to-neo4j            (neo4j queue, 100 articles)
```

**18:00:00 정각에 503 + N개의 FMP 호출이 큐에 push됨.** sync-sp500-eod-prices가 batch endpoint (`/stable/quote?symbol=AAPL,MSFT,...`)를 묶어서 사용하지 않으면 300 calls/min 한도를 즉시 초과한다. (실제 구현 검증 권장 — `stocks/tasks.py:sync_sp500_eod_prices`)

#### 17:00 슬롯 (보조 위험)

```
17:00:00  update-daily-prices              (FMP)
17:00:00  collect-category-news-high-evening (FMP)
17:15:00  collect-sp500-news-fmp-1715      (FMP, S&P 500 fanout)
17:45:00  collect-general-news-fmp-evening (FMP)
```

→ 동일 분에서 FMP 호출이 503+ 발생 가능. 16:30 calculate-market-breadth, 16:35 calculate-sector-heatmap 잔여 호출과 chain.

#### 시장시간 폴링 부하 (P2, 정상 범위 추정)

매 5분 슬롯(`*:00, *:05, *:10, ...`)에서 동시 실행:
- update-realtime-prices (FMP)
- update-market-indices (FMP)

batch quote endpoint를 쓰면 ~2 calls/min 수준 → 정상. 개별 API라면 1006 calls/min → **명백한 초과**. 코드 확인 필요.

### 1-2. Gemini Free Tier (15 RPM, 1500 RPD)

#### Gemini 의존 태스크 목록 (추정 포함)

| 태스크 | 시간 | LLM 호출량 추정 |
|-------|------|---------------|
| keyword-generation-pipeline | 매일 08:00 | gainers 종목별 키워드 → ~10-30 calls |
| analyze-news-deep-batch | 매 2시간 (8,10,12,14,16,18) :30 | **max_articles=50, 약 50 calls/run** |
| classify-news-batch | 매 2시간 :15 | 분류는 룰 + LLM 보조 가능 |
| extract-daily-news-keywords | 매일 16:45 | 누적 뉴스 키워드 → 다수 calls |
| enrich-relationship-keywords | 매일 05:30 | limit=100 → 최대 100 calls |
| thesis-generate-summaries | 평일 18:35 | 가설별 1 call (가설 수만큼) |
| chainsight-co-mentions | 매일 10:00 | 룰 + LLM 보조 가능 |
| chainsight-relation-confidence | 매일 11:00 | LLM 미사용 가능성 |
| refresh-korean-overviews-monthly | 매월 1일 03:00 | 503 calls × 약 1회 |
| extract-news-relations | 매일 09:00 | 룰 + LLM 보조 가능 |

#### 🚨 P0 위험: analyze-news-deep-batch가 단일 run에서 한도 초과

50 articles를 분석하는데 Gemini Free의 15 RPM을 따르면 **단일 태스크가 200초 이상 sleep 분산** 필요. `news/tasks.py:analyze_news_deep` 내부에서 rate limiting을 어떻게 처리하는지 검증 필요. 만약 throttle 없이 호출하면 **15 RPM 초과로 429 다발 발생**.

#### 🚨 P0 위험: 18:30~18:45 Gemini 5중첩

```
18:30  analyze-news-deep-batch          (50 articles → 50 LLM calls)
18:30  run-eod-pipeline                 (시그널 LLM 사용 가능성)
18:35  thesis-generate-summaries        (가설별 LLM)
18:45  sync-news-to-neo4j               (LLM 미사용 추정)
```

50 articles + 5~10 thesis = **분당 15회를 압도적으로 초과**. 같은 GEMINI_API_KEY를 공유하면 429로 thesis-summaries가 자주 실패할 가능성.

#### 🟡 08:00~08:30 슬롯 (이미 16:30 vs 16:45는 분산 처리됨)

```
08:00  keyword-generation-pipeline      (Gemini)
08:15  classify-news-batch              (분류, LLM 보조)
08:30  analyze-news-deep-batch          (50 LLM calls)
```

코드 주석(line 285-286)에 "16:30 vs 16:45 충돌 회피"가 명시되어 있으나, **08:00~08:30 슬롯에는 동일한 분산 처리가 없음**. keyword-gen 종료 시간이 길어지면 08:30 analyze-deep과 겹친다.

#### Gemini 일일 한도 (1500 RPD)

```
analyze-deep:      6 × 50  = 300
classify-news:     6 × N   ≈ 60~120
keyword-gen:       ~30
extract-keywords:  ~50
enrich-relations:  ~100
thesis-summaries:  ~10~30 (가설 수에 비례)
chainsight-co-mention/relation: 50~150
─────────────────────────────────
일일 합계:         ~600~800 calls/일 (estimate)
```

→ Free Tier 1500 RPD에는 여유 있어 보이지만, 가설/사용자 증가 시 1500 한도 빠르게 도달.

### 1-3. Alpha Vantage (5 calls/min)

**beat_schedule 직접 의존 없음.** 코드 검색 결과 `update_economic_indicators` 등에서 FRED API를 사용하고 AV는 fallback 경로로만 호출됨 (별도 검증 필요 — `API_request/` 디렉터리).

→ 현재 스케줄 자체에는 AV rate limit 위험 없음.

---

## 2. Queue 부하 분석

### 2-1. default queue vs neo4j queue 시간대별 부하

#### neo4j queue 태스크 (solo pool, 동시 1개)

| 태스크 | 빈도 | 일 실행 횟수 |
|-------|------|-------------|
| **sec-sync-dirty-neo4j** | **5분마다 (24/7)** | **288 runs/일** |
| neo4j-health-check | 6시간마다 | 4 runs/일 |
| sync-news-to-neo4j | 평일 6회 (08:45, 10:45, ...) | 6 runs/일 (평일) |
| cleanup-expired-news-relationships | 매일 04:00 | 1 run/일 |
| enrich-relationship-keywords | 매일 05:30 | 1 run/일 |
| chainsight-sync-profiles-neo4j | 매일 12:00 | 1 run/일 |
| chainsight-sync-relations-neo4j | 매일 12:30 | 1 run/일 |
| chainsight-neo4j-dirty-sync | 일요일 04:30 | 1 run/주 |

#### 🚨 P1 위험: neo4j queue solo pool 점유 충돌

`sec-sync-dirty-neo4j`가 매 5분마다 실행되고, 다른 neo4j 태스크(특히 12:00 chainsight-sync-profiles와 12:30 chainsight-sync-relations)가 같은 큐를 사용한다.

- **5분 단위 슬롯 (00, 05, 10, 15, ...)에 sec-sync가 항상 점유**
- 12:00:00에 sec-sync와 chainsight-sync-profiles가 동시 push되면 **신뢰할 수 없는 순서**로 직렬화됨
- chainsight-sync-profiles의 정상 실행 시간이 5분을 넘으면, 다음 sec-sync 슬롯이 밀리면서 expires=240초 만료에 의해 sec-sync skip 가능 (실제 데이터 손실)

**완화책 후보**: sec-sync-dirty-neo4j 빈도를 10~15분으로 늘리거나, chainsight-sync-*를 12:02/12:32처럼 sec-sync 슬롯과 비동기로 배치.

#### default queue 부하

대부분의 태스크가 default queue 사용. 평일 시장시간(9-16시)이 가장 집중:

- 매분: refresh-market-pulse-cache (60 runs/시간)
- 매 5분: update-realtime-prices, update-market-indices (12 runs/시간 × 2)
- 매 10분: calculate-portfolio-values (6 runs/시간)
- 매 15분: check-screener-alerts (4 runs/시간)
- 매 30분: check-pipeline-alerts (2 runs/시간)
- 매 5분: sec-sync-dirty-neo4j (neo4j queue로 격리됨)

= **default queue 시장시간 시간당 ~84 runs (잡 빈도만)**. 추가로 1회성 태스크(분당 한 번 정도 발생)까지 합치면 prefetch_multiplier 설정에 따라 worker 1개가 직렬화 처리 시 분 단위로 queue 적체 가능.

---

## 3. 시간대별 ASCII 히트맵

평일(Mon-Fri) 기준, 각 시간대(00-23, EST)에 cron이 발동하는 **고유 태스크 종류 수** (반복 발생 카운트 아님, 동일 태스크는 1회로 집계).

```
시간  태스크수  ASCII 히트맵 (■=1개)                              주요 태스크
─────────────────────────────────────────────────────────────────────────────
00시   1       ■                                              sec-sync(*/5)
01시   2       ■■                                             sec-sync, economic-calendar
02시   1       ■                                              sec-sync (+ 매월1: sp500-constituents, archive-articles@:30)
03시   1       ■                                              sec-sync (+ 일: train-importance@:00, shadow-report@:30 / 월1: korean-overviews / 토: chainsight-price-co-movement)
04시   2       ■■                                             sec-sync, cleanup-news-relations (+ 일: check-auto-deploy, ml-weekly-report@:15, monitor-ml@:20, train-lightgbm@:30, chainsight-neo4j-dirty@:30)
05시   2       ■■                                             sec-sync, enrich-relationship-keywords@:30 (+ 일: cleanup-task-results / 토: validation-batch)
06시   7       ■■■■■■■                                        collect-daily-news, update-economic-indicators, sec-sync, sp500-news-fmp@:15, cat-news-high@:30, general-news-fmp@:45 (+ 월: sync-etf-holdings)
07시   6       ■■■■■■                                         celery-error-digest, chainsight-heat-score, cat-news-medium, sec-sync, sync-market-movers@:30, cat-news-low@:30, press-releases-fmp@:45
08시   6       ■■■■■■                                         keyword-gen, collect-market-news, sec-sync, classify-news@:15, analyze-deep@:30, sync-news-neo4j@:45
09시   8       ■■■■■■■■                                       시장시작: realtime, market-indices, market-pulse(매분), portfolio-values, screener-alerts, sec-sync, aggregate-sentiment, extract-news-relations
10시   12      ■■■■■■■■■■■■                                   위 +5: sp500-news-fmp@:15, chainsight-co-mentions, classify-news@:15, analyze-deep@:30, sync-news-neo4j@:45
11시   8       ■■■■■■■■                                       위 +1: chainsight-relation-confidence
12시   14      ■■■■■■■■■■■■■■  ← 피크 1                         시장태스크+update-economic-indicators, collect-market-news-noon, classify-news@:15, general-news-fmp@:30, analyze-deep@:30, chainsight-sync-profiles, chainsight-sync-relations@:30, sec-seed-relations, sync-news-neo4j@:45
13시   9       ■■■■■■■■■                                      시장+cat-news-high, sp500-news-fmp@:15, chainsight-seed-selection
14시   12      ■■■■■■■■■■■■                                   시장+cat-news-medium, classify-news@:15, collect-daily-news-afternoon@:30, analyze-deep@:30, sync-news-neo4j@:45
15시   8       ■■■■■■■■                                       시장+collect-market-news-afternoon, sp500-news-fmp@:15
16시   12      ■■■■■■■■■■■■                                   시장+classify-news@:15, analyze-deep@:30, market-breadth@:30, sector-heatmap@:35, extract-news-keywords@:45, sync-news-neo4j@:45
17시   5       ■■■■■                                          update-daily-prices, cat-news-high-evening, sec-sync, sp500-news-fmp@:15, general-news-fmp@:45
18시   13      ■■■■■■■■■■■■■  ← 피크 2 (최대 부하)               update-economic-indicators, collect-market-news, sp500-eod-prices, thesis-update-readings, sec-sync, classify-news@:15, thesis-calculate-scores@:15, analyze-deep@:30, run-eod-pipeline@:30, thesis-snapshots@:30, sp500-change-percent@:30, thesis-summaries@:35, sync-news-neo4j@:45
19시   3       ■■■                                            backfill-signal-accuracy, collect-ml-labels, sec-sync
20시   2       ■■                                             sync-sp500-financials, sec-sync
21시   1       ■                                              sec-sync
22시   2       ■■                                             update-economic-indicators, sec-sync
23시   1       ■                                              sec-sync

────────────────────────────────────────
[24시간 어디서나 깔리는 baseline]
  - sec-sync-dirty-neo4j        : 매 5분 (neo4j queue, 12 runs/시간)
  - check-pipeline-alerts       : 매 30분 (default queue, 2 runs/시간)
────────────────────────────────────────
[시장시간 9-16시 baseline (5개 polling)]
  - refresh-market-pulse-cache  : 매분 (60 runs/시간) ← 가장 자주
  - update-realtime-prices      : 매 5분 (12 runs/시간)
  - update-market-indices       : 매 5분 (12 runs/시간)
  - calculate-portfolio-values  : 매 10분 (6 runs/시간)
  - check-screener-alerts       : 매 15분 (4 runs/시간)
  ─────────────────────────────
  시장시간 시간당 default queue runs (baseline) = ~94+ (1회성 제외)
────────────────────────────────────────
```

**피크 1: 12:00 (14종)** — macro + market-news + chainsight 3종 + sec + news-pipeline 3종 + 시장시간 5종
**피크 2: 18:00 (13종)** — EOD 결산 chain 9종 + macro + news-pipeline 3종 + sec

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 선후행 의존 chain (정상 설계)

코드 주석에 명시되어 있고 의도된 chain:

| Chain | 시간 | 비고 |
|-------|------|------|
| sp500-eod-prices → run-eod-pipeline → backfill-signal-accuracy | 18:00 → 18:30 → 19:00 | EOD 시그널 |
| thesis-update-readings → thesis-calculate-scores → thesis-snapshots → thesis-summaries | 18:00 → 18:15 → 18:30 → 18:35 | Thesis EOD |
| train-importance → shadow-report → check-auto-deploy → weekly-ml-report → monitor-ml → train-lightgbm | 일 03:00 → 03:30 → 04:00 → 04:15 → 04:20 → 04:30 | ML 학습 chain |
| chainsight-all-profiles → chainsight-price-co-movement → chainsight-stale-decay → chainsight-aggregate-profiles | 토 02:00 → 03:00 → 04:00 → 04:30 | Chain Sight 주간 |
| chainsight-co-mentions → chainsight-relation-confidence → chainsight-sync-profiles → chainsight-sync-relations | 10:00 → 11:00 → 12:00 → 12:30 | Chain Sight 일일 |
| collect-daily-news → aggregate-daily-sentiment | 06:00 → 09:00 | 뉴스 감성 |

### 4-2. 🚨 P1 위험: thesis pipeline의 선행 실패 시 후행 빈 데이터

```
18:00  thesis-update-readings           (FMP/지표 fetch)
18:15  thesis-calculate-scores          (← readings 의존)
18:30  thesis-create-snapshots          (← scores 의존)
18:35  thesis-generate-summaries        (← snapshots 의존, Gemini)
```

각 단계 사이 **간격이 15분/15분/5분**이며, **명시적 의존성 체크 없이 cron으로 직렬화**. 만약 18:00 readings가 FMP rate limit으로 retry되어 18:20에 완료되면:

- 18:15 calculate-scores는 이전 데이터로 계산 → 데이터 stale
- 18:30 snapshots도 stale 데이터로 생성
- 18:35 summaries는 stale snapshot 기반 LLM 호출

**Celery chain/chord로 묶이지 않은 cron 직렬화의 전형적인 문제.** 코드 주석은 "X 완료 후"로 표기되지만, 실제 cron 트리거는 시간 기반이지 종료 시그널 기반이 아니다.

### 4-3. 🚨 P1 위험: news pipeline 중첩 (매 2시간)

```
HH:15  classify-news-batch     (3시간 lookback, hours=3)
HH:30  analyze-news-deep-batch (max_articles=50)
HH:45  sync-news-to-neo4j      (max_articles=100, neo4j queue)
```

매 2시간(`8,10,12,14,16,18`)마다 반복. 각 단계의 lookback이 3시간이라 **이전 슬롯과 중복 처리** 가능 (idempotent 가정).

또한 classify가 18:15에 시작하여 18:30 analyze 시작 시 미완료이면, 18:30 analyze는 일부 미분류 article을 처리하지 못함. classify_news가 ~15분 이상 걸리면 systematically miss.

### 4-4. 동시 실행 정상/위험 매트릭스

#### 12:00:00 정각 (5개 동시 발화)

| 태스크 | Queue | API 의존 |
|-------|-------|---------|
| update-economic-indicators | default | FRED |
| collect-market-news-noon | default | NewsAPI/FMP |
| chainsight-sync-profiles-neo4j | **neo4j** | Neo4j |
| sec-seed-relations-to-chainsight | default | DB only |
| refresh-market-pulse-cache (매분) | default | Cache only |
| update-realtime-prices (5분) | default | FMP |
| update-market-indices (5분) | default | FMP |
| calculate-portfolio-values (10분) | default | DB only |
| sec-sync-dirty-neo4j (5분) | **neo4j** | Neo4j |

→ **neo4j queue 12:00:00 슬롯에서 sec-sync vs chainsight-sync-profiles 경쟁.** solo pool 직렬 처리 시 sec-sync(가벼움)가 먼저 픽업되면 chainsight-sync가 대기.

#### 18:00:00 정각 (4개 동시 발화 + EOD chain 시작)

위 1-1 참조.

#### 04:00:00 (일요일 추가 4종)

```
04:00  cleanup-expired-news-relationships  (neo4j queue, 매일)
04:00  check-auto-deploy                   (default, 일요일)
04:00  scan-regulatory-relationships       (default, 월요일)
04:30  build-patent-network                (default, 매월 1일)
04:30  chainsight-aggregate-profiles       (default, 토요일)
04:30  chainsight-neo4j-dirty-sync         (neo4j queue, 일요일)
04:30  train-lightgbm-model                (default, 일요일)
```

→ 04:30:00 일요일에 train-lightgbm (CPU 집약) + chainsight-aggregate (DB 집약) + chainsight-neo4j-dirty-sync (Neo4j) 3종 동시. solo pool macOS 환경이면 worker가 1개라 순차 처리 → 늦은 작업은 expires(3600초)에 의해 skip 가능.

---

## 5. P0/P1/P2 권고 (코드 수정 없음 — 감사 결과만)

### P0 (즉시 검증/대응 필요)

1. **18:00 FMP 폭주 검증**: `stocks/tasks.py:sync_sp500_eod_prices`가 batch quote endpoint를 쓰는지, 503 symbols를 어떻게 분할하는지 확인. 만약 분할 없이 호출하면 300 calls/min 한도 즉시 초과.
2. **analyze-news-deep-batch 내부 throttle 검증**: 50 articles × Gemini Free 15 RPM은 200초 이상 분산 필요. 내부 sleep/throttle 부재 시 429 다발 발생 가능.
3. **18:30~18:35 Gemini 키 분리 검토**: thesis-summaries가 analyze-deep와 동일 GEMINI_API_KEY 사용 시 18:35 thesis가 429로 실패할 확률 높음.

### P1 (이번 분기 내 개선)

4. **thesis-pipeline을 Celery chain으로 변환**: cron 직렬화 대신 `update_readings.si() | calculate_scores.si() | create_snapshots.si() | generate_summaries.si()` 형태로 묶어 선행 실패 시 후행 차단.
5. **sec-sync-dirty-neo4j 빈도 재검토**: 5분 → 10분으로 늘려서 neo4j queue solo pool 점유율 완화. 또는 sec dirty backlog가 실제로 5분 단위로 쌓이는지 메트릭 확인.
6. **12:00:00 슬롯 분산**: chainsight-sync-profiles-neo4j를 12:02:00, chainsight-sync-relations-neo4j를 12:32:00으로 1~2분 shift하여 sec-sync 슬롯과 분리.

### P2 (모니터링 강화)

7. **시장시간 default queue prefetch 모니터링**: 시간당 ~94+ runs가 직렬 처리되는지 worker 수와 prefetch_multiplier 확인.
8. **Gemini 일일 호출 모니터링**: 현재 ~600~800 calls/일 추정. 사용자/가설 증가 시 1500 RPD 한도 추적 필요.
9. **DatabaseScheduler drift 정기 점검**: CLAUDE.md common-bug #28에 따라 `PeriodicTask.objects.values_list('name')` vs config dict keys diff 정기 자동화.

---

## 6. 분석 범위 / 한계

- **분석 대상**: `config/celery.py:135-814`의 `app.conf.beat_schedule` dict 64개 항목
- **분석 미포함**:
  - 실제 `PeriodicTask` DB 테이블 상태 (코드만 보고 dict 기준 분석)
  - 각 태스크 내부 구현(API 호출 패턴, throttle 로직, batch 처리 여부)
  - Celery worker concurrency 설정 (`-c` 옵션, prefetch_multiplier)
  - Redis broker 상태, dead letter queue
  - 실제 production rate limit 사용량 메트릭
- **시간대 가정**: `CELERY_TIMEZONE` 설정값을 확인하지 않았음 — UTC vs EST(NY) 가정 차이에 따라 해석 변동 가능
- **본 감사는 읽기 전용**: 어떤 파일도 수정하지 않았음
