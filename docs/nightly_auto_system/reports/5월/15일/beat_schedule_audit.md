# Beat Schedule Audit — 2026-05-15

> **소스**: `config/celery.py` (820 lines, beat_schedule 항목 64개, `grep -c 'schedule' = 90` 일치)
> **타임존**: `config/settings.py:482` → `CELERY_TIMEZONE = 'America/New_York'` (NYSE 시간대) — **모든 cron은 EST/EDT 기준**
> **Scheduler**: `config/settings.py:483` → `django_celery_beat.schedulers:DatabaseScheduler` — config dict는 reference, **실제 실행은 `django_celery_beat.PeriodicTask` DB 테이블 기준**
> **파일 수정일**: `config/celery.py` mtime 2026-05-11 (5월 14일 감사와 동일 본문). 본 감사는 **2026-05-15 시점 재검증 + 신규 관점 보강**.

---

## 0. 요약 (Executive Summary)

| # | 항목 | 결과 | 심각도 |
|---|------|------|--------|
| 1 | **18:00:00 FMP 4중첩** | `sync-sp500-eod-prices`(503) + `thesis-update-readings` + `collect-market-news-evening` + `update-economic-indicators` 동시 발화 → Starter 300/min 한도 초과 가능 | **P0** |
| 2 | **18:30:00 Gemini 다중 발화 + 18:35 thesis-summaries 인접** | `analyze-news-deep-batch`(50 articles) 시작 5분 뒤 `thesis-generate-summaries` 시작 → 동일 GEMINI_API_KEY 공유 시 15 RPM 초과로 429 다발 위험 | **P0** |
| 3 | **08:00~08:30 Gemini 3중 chain** | `keyword-generation-pipeline` → `classify-news-batch` → `analyze-news-deep-batch` 간 15분 간격, 코드 주석에 명시된 분산 처리(16:30 vs 16:45)가 이 슬롯엔 적용 안 됨 | **P0** |
| 4 | **12:00:00 슬롯 14종 발화 (피크 1)** | macro + market-news + chainsight 3종 + sec + 시장폴링 5종 동시. neo4j queue에서 `sec-sync-dirty-neo4j` vs `chainsight-sync-profiles-neo4j` 경쟁 | **P1** |
| 5 | **thesis 4단계 cron 직렬화** | `update-readings`→`calculate-scores`→`create-snapshots`→`generate-summaries` 가 15분/15분/5분 간격 cron으로만 묶임. 선행 실패 시 stale data로 후행 실행 | **P1** |
| 6 | **`sec-sync-dirty-neo4j` 24/7 5분 주기** | 288 runs/일. neo4j queue solo pool 점유 → 12:00 chainsight neo4j sync와 충돌. `expires=240`로 만료 짧음 → 밀리면 silent skip(데이터 손실 가능성) | **P1** |
| 7 | **시장시간 default queue 분당 1+ runs** | `refresh-market-pulse-cache` 매분 + 5분/10분/15분 폴링 합산 → 시간당 94+ runs (1회성 제외). solo pool macOS 환경이면 단일 worker 직렬화 | **P2** |
| 8 | **`extract-news-relations`의 day_of_week 누락** | 09:00 daily(주말 포함). 토일에는 시장 폴링/뉴스 수집이 없는 상태에서 단독 실행. 의도는 평일 추정 — 코드 주석은 "뉴스 수집 후"라 명시 | **P2** |
| 9 | **`chainsight-heat-score-daily` 등 UTC/EST 혼동 주석** | 코드 주석은 "07:00 UTC"이지만 `CELERY_TIMEZONE = America/New_York` → 실제 발화는 **07:00 EST/EDT** (UTC 11:00 또는 12:00). 운영 의도와 실행 시각 어긋날 수 있음 | **P2** |
| 10 | **Alpha Vantage 직접 의존 0건** | beat_schedule에 AV 호출 태스크 없음. fallback 경로(코드 내부)는 본 감사 범위 외 | OK |
| 11 | **DatabaseScheduler drift 위험 잔존** | config dict 64개 ↔ DB `PeriodicTask` diff 자동화 없음. 2026-04-24에 2개 누락 복구 이력 있음 (`chainsight-heat-score-daily`, `sec-seed-relations-to-chainsight`) | **P1** |

---

## 1. Rate Limit 초과 구간 분석

### 1-1. FMP (Starter Plan: 300 calls/min, 10,000 calls/day)

#### FMP 의존 태스크 인벤토리

| 태스크 이름 | cron 발화 시각 (EST) | 빈도 | 1회 추정 호출량 | 일 호출량 추정 |
|-----------|-------------------|------|---------------|---------------|
| `update-realtime-prices` | `*/5 9-16 1-5` | 시장시간 5분 | batch quote 사용 시 1~5, 개별 시 503 | 96 × N |
| `update-market-indices` | `*/5 9-16 1-5` | 시장시간 5분 | 4~6 indices | 96 × 6 ≈ 576 |
| `update-daily-prices` | `17:00 1-5` | 1회/일 | 가능 503 (batch) | 1 |
| `sync-sp500-eod-prices` | `18:00 1-5` | 1회/일 | **503 (S&P 500 전수)** ★최대★ | 1 |
| `sync-sp500-financials` | `20:00 1-5` | 1회/일 | 101 (5일 회전) | 1 |
| `collect-sp500-news-fmp-*` | `06:15,10:15,13:15,15:15,17:15 1-5` | 5회/일 | orchestrator + fanout | 5 |
| `collect-press-releases-fmp` | `07:45 1-5` | 1회/일 | max_symbols=50 | 1 |
| `collect-general-news-fmp-*` | `06:45,12:30,17:45 1-5` | 3회/일 | 단건 | 3 |
| `collect-market-news-*` | `08:00,12:00,15:00,18:00 1-5` | 4회/일 | FMP 또는 NewsAPI | 4 |
| `collect-category-news-*` | 06:30/07:00/07:30/13:00/14:00/17:00 (평일) | 6회/일 | 카테고리별 fanout | 6 |
| `thesis-update-readings` | `18:00 1-5` | 1회/일 | 지표별 sync (FMP 의존 다수) | 1 |
| `run-eod-pipeline` | `18:30 1-5` | 1회/일 | 시그널 계산용 (FMP 가능) | 1 |
| `sync-etf-holdings` | `06:00 day_of_week=1` | 주 1회 | ETF holdings | 0.2 |

#### 🚨 P0 #1 — 18:00:00 슬롯 4중첩 (그대로 잔존)

```text
18:00:00  sync-sp500-eod-prices              ← S&P 500 503 symbols
18:00:00  thesis-update-readings             ← 지표 다수 FMP 호출
18:00:00  collect-market-news-evening        ← FMP 시장뉴스 1건
18:00:00  update-economic-indicators         ← FRED (FMP 영향 없음)
+ 시장폴링 잔여(시장은 16시 마감이라 18시엔 없음)
+ check-pipeline-alerts (18:00 */30)
+ sec-sync-dirty-neo4j (*/5, 18:00 슬롯 포함)
```

**위험 핵심**: `sync-sp500-eod-prices`가 batch quote endpoint(`/stable/quote?symbol=...`)를 묶지 않고 개별 호출하면 분당 503회 → 300/min 한도 1.68배 초과. 다른 3개와 합치면 더 심각.

**검증 필요 파일** (코드 수정 금지, 읽기만):
- `stocks/tasks.py::sync_sp500_eod_prices` — batch 분할 여부
- `thesis/tasks/eod_pipeline.py::update_indicator_readings` — 지표당 호출 횟수와 throttle

#### 17:00:00 보조 위험

```text
17:00:00  update-daily-prices                    (FMP, batch 가능)
17:00:00  collect-category-news-high-evening     (FMP fanout)
17:15:00  collect-sp500-news-fmp-1715            (FMP orchestrator)
17:45:00  collect-general-news-fmp-evening       (FMP 1건)
```

17:00:00 동시 2개 + 17:15/17:45 분산. 16:30 `calculate-market-breadth`와 16:35 `calculate-sector-heatmap`도 FMP/DB 의존 가능 → chain risk.

#### 시장시간(09-16) 폴링 부하

매 5분 슬롯에서 `update-realtime-prices` + `update-market-indices` 동시. 1분 슬롯엔 `refresh-market-pulse-cache` (캐시만, 보통 FMP 미접근).

- batch quote endpoint 사용 시: ≈ 2 calls/min → 안전
- 개별 quote 호출 시: ≈ 1006 calls/min → **명백히 300/min 초과**

→ `stocks/tasks.py::update_realtime_with_provider` 내부 batch 사용 여부 확인 필요.

#### 일 한도(10,000 calls/day) 추정

```
sync-sp500-eod-prices     1 ×  503  =  503
update-daily-prices       1 × ~503  =  503  (S&P 500 전수면)
시장 폴링                  96 ×    2 =  192  (batch 가정)
sync-sp500-financials     1 ×  101  =  101
collect-sp500-news 5종    5 × ~100  =  500
collect-press-releases    1 ×   50  =   50
collect-category-news 6종 6 × ~100  =  600
기타                              ≈  200
─────────────────────────────────────────
일일 합계 추정             ≈ 2,650 calls/일 (batch 기준)
                          ≈ 12,000+ calls/일 (개별 호출 시)
```

→ batch 사용 시 Starter 10K/day 내 여유. **개별 호출 시 일 한도까지 초과**.

### 1-2. Gemini Free Tier (15 RPM, 1500 RPD, 1M TPM 별도)

#### Gemini 의존 태스크 인벤토리

| 태스크 | 시각 (EST) | LLM 호출 추정 |
|-------|----------|------------|
| `keyword-generation-pipeline` | 매일 08:00 | gainers 종목별 → 10~30 calls |
| `classify-news-batch-morning` | 평일 `8,10,12,14,16,18` :15 | hours=3 lookback, 분류는 룰+LLM 보조 |
| `analyze-news-deep-batch` | 평일 `8,10,12,14,16,18` :30 | **max_articles=50 → 50 calls/run** |
| `extract-daily-news-keywords` | 매일 16:45 | 누적 뉴스 키워드 다수 |
| `enrich-relationship-keywords` | 매일 05:30 | limit=100 |
| `thesis-generate-summaries` | 평일 18:35 | 가설별 1 call (가설 수 비례) |
| `chainsight-co-mentions` | 매일 10:00 | days_back=7, 룰+LLM 보조 |
| `chainsight-relation-confidence` | 매일 11:00 | LLM 미사용 추정 |
| `refresh-korean-overviews-monthly` | 매월 1일 03:00 | 503 calls × 월 1회 |
| `extract-news-relations` | 매일 09:00 | 24h lookback, 룰+LLM 보조 |

#### 🚨 P0 #2 — 18:30 → 18:35 Gemini 인접 폭주

```text
18:30:00  analyze-news-deep-batch          (50 articles → 최대 50 LLM calls)
18:30:00  run-eod-pipeline                 (LLM 사용 가능성 — 시그널 설명?)
18:30:00  thesis-create-snapshots          (스냅샷 자체는 LLM 불요)
18:35:00  thesis-generate-summaries        (가설별 LLM, GEMINI_API_KEY 공유 추정)
```

**시나리오**: 18:30 시작한 `analyze-news-deep-batch`가 throttle 없이 50 calls를 1~2분에 우겨넣으면 분당 RPM 초과 → 429. 그 직후 18:35 `thesis-generate-summaries`가 시작할 때 quota window가 회복되지 않았으면 thesis 가설별 호출이 줄줄이 429.

**검증 필요 파일**:
- `news/tasks.py::analyze_news_deep` — 내부 sleep/throttle 로직 유무
- `thesis/tasks/summary.py::generate_thesis_summaries` — 동일 API KEY 사용 여부

#### 🚨 P0 #3 — 08:00 → 08:15 → 08:30 chain

```text
08:00:00  keyword-generation-pipeline      (Gemini, gainers 종목별)
08:15:00  classify-news-batch-morning      (룰+LLM 보조)
08:30:00  analyze-news-deep-batch          (50 LLM calls)
```

코드 주석(`celery.py:285-286`)에는 "16:30 vs 16:45 충돌 회피"가 명시되어 있지만, **08:00~08:30 슬롯에는 동일한 분산 처리가 없다**. keyword-gen이 종목 수 따라 15분을 넘기면 08:30 analyze-deep와 quota window가 겹친다.

#### 일 한도(1500 RPD) 추정

```
analyze-deep         6 × ~50 = 300 (보수)
classify-news        6 × ~20 = 120
keyword-gen          1 × ~30 =  30
extract-keywords     1 × ~50 =  50
enrich-relations     1 × 100 = 100
thesis-summaries     1 × ~20 =  20 (가설 6개 + 알파)
chainsight-co-mention 1 × ~80=  80
chainsight-relation  1 × ~50 =  50  (LLM 사용 시)
extract-news-relations 1 × ~50= 50
─────────────────────────────
일일 합계 추정               ≈ 800 calls/일
+ 매월 1일 korean-overviews × 503 → 해당일은 1300+
```

→ Free 1500 RPD 내 평일 여유. **매월 1일은 한도 임박 (1300+)**. 가설/사용자 증가 시 단일 키로 한계 도달.

### 1-3. Alpha Vantage (5 calls/min)

**beat_schedule 직접 의존 0건.** macro 태스크는 FRED, stock 태스크는 FMP. AV는 코드 내부 fallback에서만 호출되며 별도 검증 범위.

→ 현재 스케줄 자체에는 AV rate limit 위험 없음.

---

## 2. Queue 부하 분석

### 2-1. neo4j queue (macOS solo pool, 동시 1개)

#### neo4j 라우팅 태스크 인벤토리 (`celery.py:37-55`)

| 태스크 | 빈도 | 일 실행 횟수 | expires |
|-------|------|-------------|---------|
| **`sec-sync-dirty-neo4j`** | **매 5분 (24/7)** | **288/일** | **240s** |
| `neo4j-health-check` | 6시간 | 4/일 | - |
| `sync-news-to-neo4j` | 평일 6회 (08:45~18:45 :45) | 6/일 | 3600s |
| `cleanup-expired-news-relationships` | 매일 04:00 | 1/일 | 3600s |
| `enrich-relationship-keywords` | 매일 05:30 | 1/일 | 3600s |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | 1/일 | 3600s |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | 1/일 | 3600s |
| `chainsight-neo4j-dirty-sync` | 일요일 04:30 | 1/주 | 3600s |

#### 🚨 P1 #6 — solo pool 점유 + `expires=240` 짧음

- **5분 단위 슬롯(`*/5`)에 `sec-sync-dirty-neo4j`가 항상 점유**.
- 12:00:00에 `sec-sync` + `chainsight-sync-profiles-neo4j` 둘 다 push → solo pool은 직렬화. push 순서/picker policy 따라 `chainsight-sync-profiles`가 1개 뒤로 밀림.
- `chainsight-sync-profiles-neo4j`가 5분 이상 걸리면 12:05의 `sec-sync` 슬롯 도착 → `expires=240`초로 이미 만료 또는 후속 sec-sync 슬롯이 추가 적체.
- **silent skip 위험**: `expires`로 인한 만료는 ack 없이 사라지므로 dirty backlog 누적 후 다음 sync 때까지 Neo4j와 RDB 비동기.

검증 필요:
- 실제 `sec-sync-dirty-neo4j` 평균 실행시간(`logs/celery-worker*.log` 또는 task_results)
- `chainsight-sync-profiles-neo4j`/`sync-relations-neo4j` 실행시간
- macOS solo pool에서 neo4j worker가 별도로 떠 있는지 (worker concurrency `-c` 설정)

### 2-2. default queue

대부분의 64개 태스크가 default queue. 시장시간이 가장 집중.

**시장시간(09:00~16:00 평일) 시간당 baseline runs**

```
refresh-market-pulse-cache     매분    × 60 = 60
update-realtime-prices         5분    × 12 = 12
update-market-indices          5분    × 12 = 12
calculate-portfolio-values    10분    ×  6 =  6
check-screener-alerts         15분    ×  4 =  4
check-pipeline-alerts         30분    ×  2 =  2  (24/7)
─────────────────────────────────────────────
시간당 baseline default queue runs            = 96
```

추가로 매시 :00/:15/:30/:45 1회성 태스크 적체. 단일 worker 직렬화면 `refresh-market-pulse-cache`(매분) 자체로 매분 1슬롯을 항상 점유 → 다른 작업과 충돌 가능.

---

## 3. 시간대별 ASCII 히트맵

평일 기준, 각 시간대(00-23, EST)에 cron이 발동하는 **고유 태스크 종류 수** (반복 발생은 1회 집계).

```text
시각 cnt 히트맵                                       대표 태스크
─────────────────────────────────────────────────────────────────────
00시   1 █                                            sec-sync(*/5)
01시   2 ██                                           sec-sync, economic-calendar(daily 01:00)
02시   1 █                                           sec-sync
       +월: sp500-constituents@:00, archive-articles@:30
       +토: chainsight-all-profiles@:00
03시   1 █                                           sec-sync
       +일: train-importance@:00, shadow-report@:30, cleanup-old-macro@:00
       +월1: korean-overviews@:00
       +15일: sync-supply-chain-batch@:00
       +토: chainsight-price-co-movement@:00
04시   2 ██                                          sec-sync, cleanup-news-relations
       +일: check-auto-deploy@:00, weekly-ml-report@:15,
            monitor-ml@:20, train-lightgbm@:30, chainsight-neo4j-dirty@:30
       +월: scan-regulatory-relations@:00
       +월1: build-patent-network@:30
       +16일: sync-institutional-holdings@:00
       +토: chainsight-stale-decay@:00, chainsight-aggregate@:30
05시   2 ██                                          sec-sync, enrich-relationship-keywords@:30
       +일: cleanup-task-results@:00
       +토: validation-weekly-batch@:00
06시   7 ███████                                     daily-news-morning, eco-indicators,
                                                     sec-sync, sp500-news-fmp@:15,
                                                     cat-news-high@:30, general-news-fmp@:45
       +월: sync-etf-holdings@:00
       +월1: sec-check-new-filings@:00
07시   6 ██████                                      error-digest, heat-score-daily,
                                                     cat-news-medium@:00, sec-sync,
                                                     market-movers@:30, cat-news-low@:30,
                                                     press-releases-fmp@:45
08시   6 ██████                                      keyword-gen, collect-market-news,
                                                     sec-sync, classify-news@:15,
                                                     analyze-deep@:30, sync-news-neo4j@:45
09시   8 ████████                                    [시장 개장]
                                                     realtime, market-indices, market-pulse(매분),
                                                     portfolio-values, screener-alerts, sec-sync,
                                                     aggregate-sentiment, extract-news-relations
10시  12 ████████████                                위 + chainsight-co-mentions,
                                                     sp500-news-fmp@:15, classify-news@:15,
                                                     analyze-deep@:30, sync-news-neo4j@:45
11시   8 ████████                                    위 + chainsight-relation-confidence
12시  14 ██████████████  ← 피크 1                    macro, market-news-noon,
                                                     chainsight-sync-profiles(NJ4),
                                                     sec-seed-relations, +시장폴링5,
                                                     classify-news@:15, general-news-fmp@:30,
                                                     analyze-deep@:30, chainsight-sync-relations@:30(NJ4),
                                                     sync-news-neo4j@:45(NJ4)
13시   9 █████████                                   시장폴링 + cat-news-high@:00,
                                                     seed-selection@:00, sp500-news-fmp@:15
14시  12 ████████████                                시장폴링 + cat-news-medium@:00,
                                                     classify-news@:15, daily-news-pm@:30,
                                                     analyze-deep@:30, sync-news-neo4j@:45
15시   8 ████████                                    시장폴링 + market-news-pm@:00,
                                                     sp500-news-fmp@:15
16시  12 ████████████                                [장 마감] 시장폴링 + classify-news@:15,
                                                     analyze-deep@:30, market-breadth@:30,
                                                     sector-heatmap@:35,
                                                     extract-news-keywords@:45,
                                                     sync-news-neo4j@:45
17시   5 █████                                       update-daily-prices@:00,
                                                     cat-news-high-evening@:00, sec-sync,
                                                     sp500-news-fmp@:15,
                                                     general-news-fmp@:45
18시  13 █████████████  ← 피크 2 (최대 부하)         eco-indicators, market-news-evening,
                                                     sp500-eod-prices, thesis-update-readings,
                                                     sec-sync, classify-news@:15,
                                                     thesis-calculate-scores@:15,
                                                     analyze-deep@:30, run-eod-pipeline@:30,
                                                     thesis-create-snapshots@:30,
                                                     update-sp500-change-percent@:30,
                                                     thesis-generate-summaries@:35,
                                                     sync-news-neo4j@:45
19시   3 ███                                         backfill-signal-accuracy@:00,
                                                     collect-ml-labels@:00, sec-sync
20시   2 ██                                          sync-sp500-financials@:00, sec-sync
21시   1 █                                           sec-sync
22시   2 ██                                          update-economic-indicators@:00, sec-sync
23시   1 █                                           sec-sync

─────────────────────────────────────────────────────────
[24시간 baseline]
  sec-sync-dirty-neo4j   매 5분 (neo4j queue, 288/일)
  check-pipeline-alerts  매 30분 (default queue, 48/일)
─────────────────────────────────────────────────────────
[시장시간 09-16 baseline (default queue)]
  refresh-market-pulse-cache  매분    (60 runs/시간)  ← 가장 자주
  update-realtime-prices       5분    (12 runs/시간)
  update-market-indices        5분    (12 runs/시간)
  calculate-portfolio-values  10분    ( 6 runs/시간)
  check-screener-alerts       15분    ( 4 runs/시간)
  ────────────────────────────────────────
  시장시간 시간당 default queue 발화      ≈ 94 (1회성 제외)
─────────────────────────────────────────────────────────
```

### 3-1. 분 단위 피크 슬롯 표 (12:00, 18:00 정각)

| 시각 (EST) | 동시 발화 태스크 | Queue | API 의존 |
|-----------|-----------------|-------|---------|
| **12:00:00** | `update-economic-indicators` | default | FRED |
| | `collect-market-news-noon` | default | NewsAPI/FMP |
| | `chainsight-sync-profiles-neo4j` | **neo4j** | Neo4j |
| | `chainsight-seed-selection` (코드상 13:00이지만 cron 검증 필요) | default | DB |
| | `sec-seed-relations-to-chainsight` | default | DB |
| | `refresh-market-pulse-cache` | default | cache |
| | `update-realtime-prices` | default | FMP |
| | `update-market-indices` | default | FMP |
| | `calculate-portfolio-values` | default | DB |
| | `sec-sync-dirty-neo4j` | **neo4j** | Neo4j |
| | `check-pipeline-alerts` | default | DB |
| **12:30:00** | `chainsight-sync-relations-neo4j` | **neo4j** | Neo4j |
| | `collect-general-news-fmp-noon` | default | FMP |
| | `analyze-news-deep-batch` (격시) | default | Gemini ★ |
| | `update-realtime-prices` | default | FMP |
| | `update-market-indices` | default | FMP |
| | `calculate-portfolio-values` | default | DB |
| | `refresh-market-pulse-cache` | default | cache |
| | `sec-sync-dirty-neo4j` | **neo4j** | Neo4j |
| | `check-pipeline-alerts` | default | DB |
| **18:00:00** | `sync-sp500-eod-prices` ★ | default | **FMP 503 calls** |
| | `thesis-update-readings` | default | **FMP 지표 다수** |
| | `collect-market-news-evening` | default | NewsAPI/FMP |
| | `update-economic-indicators` | default | FRED |
| | `check-pipeline-alerts` | default | DB |
| | `sec-sync-dirty-neo4j` | **neo4j** | Neo4j |
| **18:30:00** | `analyze-news-deep-batch` ★ | default | **Gemini ~50 calls** |
| | `run-eod-pipeline` | default | FMP/DB |
| | `thesis-create-snapshots` | default | DB |
| | `update-sp500-change-percent` | default | DB |
| | `check-pipeline-alerts` | default | DB |
| | `sec-sync-dirty-neo4j` | **neo4j** | Neo4j |
| **18:35:00** | `thesis-generate-summaries` ★ | default | **Gemini 가설별** |
| **18:45:00** | `sync-news-to-neo4j` | **neo4j** | Neo4j |
| | `sec-sync-dirty-neo4j` (slot) | **neo4j** | Neo4j |

★ = rate-limit 핵심 부담 태스크.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 의도된 선후행 chain (코드 주석 명시)

| Chain | 시각 | 비고 |
|-------|------|------|
| `sp500-eod-prices` → `run-eod-pipeline` → `backfill-signal-accuracy` | 18:00 → 18:30 → 19:00 | EOD 시그널 |
| `thesis-update-readings` → `calculate-scores` → `create-snapshots` → `generate-summaries` | 18:00 → 18:15 → 18:30 → 18:35 | Thesis EOD |
| `train-importance` → `shadow-report` → `check-auto-deploy` → `weekly-ml-report` → `monitor-ml` → `train-lightgbm` | 일 03:00 → 03:30 → 04:00 → 04:15 → 04:20 → 04:30 | ML 학습 |
| `chainsight-all-profiles` → `price-co-movement` → `stale-decay` → `aggregate-profiles` | 토 02:00 → 03:00 → 04:00 → 04:30 | CS 주간 |
| `chainsight-co-mentions` → `relation-confidence` → `sync-profiles` → `sync-relations` | 10:00 → 11:00 → 12:00 → 12:30 | CS 일일 |
| `collect-daily-news` → `aggregate-daily-sentiment` | 06:00 → 09:00 | 뉴스 감성 |
| `keyword-gen` → `classify-news` → `analyze-deep` | 08:00 → 08:15 → 08:30 | 뉴스 분석 진입 |

### 4-2. 🚨 P1 #5 — thesis pipeline cron 직렬화의 한계

```text
18:00  thesis-update-readings       (FMP/지표 fetch, throttle 시 분 단위 잠재 지연)
18:15  thesis-calculate-scores      (← readings 의존)
18:30  thesis-create-snapshots      (← scores 의존)
18:35  thesis-generate-summaries    (← snapshots 의존, Gemini 호출)
```

- 명시적 의존성 체크 없이 **cron 시각만으로 직렬화**.
- 18:00 readings가 FMP rate limit retry로 18:20에 완료되면 → 18:15 calculate-scores는 **이전 EOD 데이터**로 계산 → 18:30 snapshots, 18:35 summaries 모두 **stale data**.
- thesis-generate-summaries가 Gemini 429를 만나면 자동 재시도가 없으면 빈 요약 생성 가능.

**검증 필요**: 각 thesis 태스크 내부에서 "선행 단계의 산출물 존재 여부" 가드가 있는지.

### 4-3. 🚨 P1 #4 — news pipeline 매 2시간 중첩

```text
HH:15  classify-news-batch          (hours=3 lookback)
HH:30  analyze-news-deep-batch      (max_articles=50)
HH:45  sync-news-to-neo4j           (max_articles=100, neo4j queue)
```

평일 `8,10,12,14,16,18` 6회. 각 단계가 3시간 lookback이라 **이전 슬롯과 중복 처리** → idempotent 보장이 필수.

- 18:15 classify가 ~20분 걸리면 18:30 analyze-deep 시작 시 "방금 분류된 article"이 일부 누락 가능.
- 18:30 analyze-deep이 ~15분 걸리면 18:45 sync-news-to-neo4j 시작 시 "방금 분석된 article"이 일부 누락 가능.

### 4-4. 동시 실행 매트릭스 — 12:00:00 정각 (피크 1)

이미 표 3-1에 명시. **neo4j queue 충돌이 핵심**: `sec-sync-dirty-neo4j`(가벼움, expires=240) vs `chainsight-sync-profiles-neo4j`(무거움, expires=3600). solo pool 직렬화에서 sec-sync가 먼저 픽되면 chainsight가 5분 이상 대기 가능.

### 4-5. 동시 실행 매트릭스 — 04:00 일요일

```text
04:00:00  cleanup-expired-news-relationships  (매일, neo4j queue)
04:00:00  check-auto-deploy                   (일요일, default)
04:30:00  build-patent-network                (월1, default)
04:30:00  chainsight-aggregate-profiles       (토요일, default — 일요일과 다름)
04:30:00  chainsight-neo4j-dirty-sync         (일요일, neo4j queue)
04:30:00  train-lightgbm-model                (일요일, default, CPU 집약)
```

- macOS solo pool 환경에서 일요일 04:30에 `train-lightgbm`(CPU 무거움) + `chainsight-neo4j-dirty-sync`(neo4j queue, 별도 worker) + `cleanup-expired-news-relationships`(neo4j 큐) → 직렬화 시 후행 작업이 `expires=3600`에 의해 skip 가능.
- 매월 1일이 일요일과 겹치면 `build-patent-network`(`expires=86400`)와 위 작업들이 동시.

### 4-6. 🟡 P2 #8 — `extract-news-relations` day_of_week 누락

```python
'extract-news-relations': {
    'task': 'serverless.tasks.extract_news_relations',
    'schedule': crontab(hour=9, minute=0),   # day_of_week 없음 → 매일
    'args': (24,),
    'options': {'expires': 3600}
},
```

09:00 daily(주말 포함). 토일에는 뉴스 수집 cron(`collect-daily-news`, `collect-market-news` 등)이 모두 `day_of_week='1-5'`라서 신규 뉴스가 거의 없다. → **주말 호출은 빈 결과로 종료될 가능성**, 또는 6일 이상 묵은 article을 lookback 24h로 재처리.

코드 주석에도 "뉴스 수집 후"라 명시되어 있어 의도와 어긋남.

### 4-7. 🟡 P2 #9 — UTC vs EST 주석 혼동

```python
# Heat Score 배치 (매일 07:00 UTC, 시드 선정 전)
'chainsight-heat-score-daily': {
    'schedule': crontab(hour=7, minute=0),  # CELERY_TIMEZONE=America/New_York → 07:00 EST
    ...
},
# 시드 선정 (매일 13:00 UTC, 관계 동기화 후)
'chainsight-seed-selection': {
    'schedule': crontab(hour=13, minute=0),  # → 13:00 EST
    ...
},
# Neo4j dirty 동기화 (매주 일요일 04:30 UTC)
'chainsight-neo4j-dirty-sync': {
    'schedule': crontab(hour=4, minute=30, day_of_week=0),  # → 04:30 EST 일요일
    ...
},
```

`CELERY_TIMEZONE = 'America/New_York'` 이므로 **위 cron은 EST/EDT로 해석**됨. 코드 주석은 "UTC"라 명시 → 실제 실행은 **5(EDT) 또는 4(EST) 시간 늦게**. 운영 의도와 어긋날 수 있음 (운영자가 UTC 기대로 모니터링하면 시각 mismatch).

---

## 5. P0/P1/P2 권고 (코드 수정 없음 — 감사 결과만)

### P0 (즉시 검증/대응 필요)

1. **18:00 FMP 4중첩 검증** — `stocks/tasks.py::sync_sp500_eod_prices`의 batch quote endpoint 사용 여부, S&P 500 503개 호출 분할 패턴. 만약 분할 없으면 300/min 즉시 초과.
2. **analyze-news-deep-batch 내부 throttle 검증** — `news/tasks.py::analyze_news_deep`가 Gemini 15 RPM에 맞춘 sleep/throttle을 갖는지. 없으면 429 다발 + 18:35 thesis-summaries 동시 실패 위험.
3. **thesis-summaries Gemini 키 분리 검토** — `thesis/tasks/summary.py`가 동일 GEMINI_API_KEY를 공유하는지. 별도 키 또는 별도 quota window가 필요한지 확인.
4. **`update-realtime-prices` batch quote 검증** — 시장시간 5분 슬롯에서 503개 종목을 어떻게 호출하는지. 개별 호출이면 1006 calls/min 발생.

### P1 (이번 분기 내 개선)

5. **thesis pipeline Celery chain화 검토** — cron 직렬화 대신 `signature.si()` 체인으로 묶어 선행 실패 시 후행 차단. 다만 DatabaseScheduler 환경이라 chain은 추가 코드 필요.
6. **`sec-sync-dirty-neo4j` 빈도 재검토** — 5분 → 10~15분 완화 여부 결정. 결정 전 sec dirty backlog 누적 메트릭 확보 필요.
7. **12:00:00 슬롯 분산** — `chainsight-sync-profiles-neo4j` → 12:02, `chainsight-sync-relations-neo4j` → 12:32 등으로 1~2분 shift하여 sec-sync */5 슬롯과 분리.
8. **18:00 슬롯 분산** — `collect-market-news-evening`를 18:05, `thesis-update-readings`를 18:02 등으로 분산해서 `sync-sp500-eod-prices` 단독 슬롯 확보.
9. **DatabaseScheduler drift 자동 점검** — `PeriodicTask.objects.values_list('name')` vs config dict keys diff를 매일 1회 자동 비교 후 Slack/이메일 알림. 2026-04-24 누락 사고 재발 방지.

### P2 (모니터링 강화)

10. **default queue 시장시간 prefetch 모니터링** — 시간당 ~94 baseline runs + 1회성. macOS solo pool 환경에서 단일 worker 직렬화 처리량 측정.
11. **Gemini 일일 호출 모니터링** — 평일 ~800, 매월 1일 ~1300+. korean-overviews-monthly가 1500 RPD 한계에 가까움.
12. **`extract-news-relations` day_of_week 제한 검토** — 주말 무의미 호출 차단을 위해 `day_of_week='1-5'` 추가 여부 결정.
13. **UTC/EST 주석 정정** — `chainsight-heat-score-daily`, `chainsight-seed-selection`, `chainsight-neo4j-dirty-sync` 주석의 "UTC"를 "EST"로 통일 (코드는 정상, 주석만 오해 유발).
14. **`sec-sync-dirty-neo4j` expires=240 적정성 검토** — 5분 주기인데 expires가 4분이라 만료 잦음. 5분 또는 6분으로 늘려 silent skip 줄일지 평가.

---

## 6. 비교: 5월 14일 감사 대비 변경 사항

`config/celery.py` mtime = 2026-05-11. 5월 14일 감사 이후 **수정 없음**.

| 항목 | 5월 14일 감사 | 5월 15일 (본 감사) | 변동 |
|------|-------------|-------------------|------|
| beat_schedule 항목 수 | 64 | 64 | 변동 없음 |
| P0 발견 수 | 3 | 4 (시장폴링 batch 검증 신규 추가) | +1 |
| P1 발견 수 | 3 | 5 (18:00 슬롯 분산, drift 점검 자동화 추가) | +2 |
| P2 발견 수 | 3 | 5 (extract-news-relations 주말, UTC/EST 주석, expires=240 추가) | +2 |
| 12:00 발화 태스크 수 (피크 1) | 14 | 14 | 동일 |
| 18:00 발화 태스크 수 (피크 2) | 13 | 13 | 동일 |
| Gemini 일일 호출 추정 (평일) | ~600~800 | ~800 (보수) + 매월1일 1300+ | 매월1일 부각 |

→ **본 보고서는 5월 14일 결과를 confirm + 4개 신규 위험 추가** (시장 폴링 batch 검증, 18:00 분산, drift 자동화, 주말/주석/expires 미세 항목).

---

## 7. 분석 범위 / 한계

- **분석 대상**: `config/celery.py:135-814`의 `app.conf.beat_schedule` dict 64개 항목 + `task_routes` dict (`:37-55`).
- **분석 미포함**:
  - 실제 `django_celery_beat.PeriodicTask` DB 테이블 상태 (config dict 기준 분석. DB diff는 별도 점검)
  - 각 태스크 내부 구현 (API 호출 패턴, throttle, batch, retry policy)
  - Celery worker concurrency 설정 (`-c`, prefetch_multiplier, `task_acks_late`)
  - Redis broker 상태, dead letter queue, visibility timeout
  - 실제 production rate limit 사용량 메트릭 (FMP/Gemini 대시보드 미접근)
  - `logs/celery-*.log` 실행 시간 통계 (실시간 데이터 미수집)
- **시간대 가정**: `CELERY_TIMEZONE = 'America/New_York'` 확인 완료 (`config/settings.py:482`). 모든 cron은 EST/EDT.
- **본 감사는 읽기 전용**: 어떤 파일도 수정하지 않았음. 본 보고서가 유일한 산출물.
