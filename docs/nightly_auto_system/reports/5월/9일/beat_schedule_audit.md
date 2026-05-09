# Beat Schedule 감사 보고서

- 감사일: 2026-05-10
- 감사 대상: `config/celery.py` (820 LOC, 90 schedule entries, 78개 PeriodicTask)
- 모드: 읽기 전용 (코드 수정 없음)
- 시간대: **모든 cron이 서버 timezone 기준** — settings.py 기준 EST/UTC 매핑은 별도 검증 필요

---

## TL;DR

| 영역 | 결론 |
|------|------|
| **FMP Rate Limit (300/min)** | 🔴 **위반 가능성 높음** — 06:15/10:15/13:15/15:15/17:15에 chord 6병렬로 S&P 500 (~503종목) 동시 호출, 1분 내 300 초과 우려 |
| **Gemini Free (15 RPM, 1500 RPD)** | 🟠 **위험** — analyze-news-deep-batch (8,10,12,14,16,18 :30, max_articles=50) 단일 실행이 RPM 한도 초과 가능. 일일 RPD 추정 600~900건 (안전 한도 80% 근접) |
| **Alpha Vantage (5/min)** | 🟢 **AV 의존 스케줄 미발견** — beat_schedule에 직접 호출 태스크 없음 (FMP로 마이그레이션 완료 추정) |
| **neo4j queue (solo pool)** | 🔴 **백로그 위험** — sec-sync-dirty-neo4j 5분 주기(288/일)가 12:00/12:30 chainsight 동기화·05:30 enrich 등 장기 태스크와 동일 큐 점유 |
| **시간대 피크** | 18:00~18:45 (EOD + thesis + analyze-deep + sync-news-neo4j + change-percent — 4분 간격 5개), 06:00~06:50 (sp500-news-fmp + etf-holdings + sec-check + general-news-fmp) |
| **암묵 의존성 위반 가능성** | 🟠 18:30 run-eod-pipeline ↔ 18:30 thesis-create-snapshots 동시 실행 (둘 다 EOD 데이터 필요), 18:00 sync-sp500-eod-prices(503 종목) 완료 전 18:30 후속이 출발할 수 있음 |

**P0 수정 권고 후보 (이 보고서는 권고만, 코드 수정 없음)**:
1. SP500 FMP 뉴스 chord 직렬화 또는 배치 간 sleep 도입
2. analyze-news-deep-batch 내 Gemini 호출 throttle 검증 (코드 본체에서)
3. sec-sync-dirty-neo4j 주기를 5분→10분 또는 큐 분리 검토
4. 18:30 슬롯 분산 (현재 4개 동시, thesis는 18:30→18:40 이동 등)

---

## 1. 전체 스케줄 카탈로그

### 1.1 Continuous (분 단위)

| 태스크 | 주기 | 큐 | API | 일일 실행수 |
|--------|------|----|----|------------|
| `update-realtime-prices` | 5min, 9-16h, Mon-Fri | default | FMP (10종목, 1초 간격) | 96/평일 |
| `update-market-indices` | 5min, 9-16h, Mon-Fri | default | FMP | 96/평일 |
| `refresh-market-pulse-cache` | 1min, 9-16h, Mon-Fri | default | FMP/cache | 480/평일 |
| `calculate-portfolio-values` | 10min, 9-16h, Mon-Fri | default | DB only | 48/평일 |
| `check-screener-alerts` | 15min, 9-16h, Mon-Fri | default | DB only | 32/평일 |
| `check-pipeline-alerts` | 30min, 24h | default | DB only | 48/일 |
| `sec-sync-dirty-neo4j` | **5min, 24h** | **neo4j** | Neo4j | **288/일** |

### 1.2 시간대별 (EST 가정)

> 하단 ASCII 히트맵에 통합. 평일 기준 HH:00~HH:59 동안 발화하는 태스크 수.

---

## 2. 시간대별 ASCII 히트맵 (평일)

```
         태스크 발화 빈도 (분 단위 trigger 1회 = 1)
시간 │ 태스크 수 │ 부하 막대
─────┼──────────┼────────────────────────────────────────
 00 │    13   │ ███▌                  [sec×12, neo4j-hc(00:00 매6h 시작 가정)]
 01 │    13   │ ███▌                  [sec×12, calendar(daily)]
 02 │    12   │ ███                   [sec×12]
 03 │    12   │ ███                   [sec×12]
 04 │    13   │ ███▌                  [sec×12, cleanup-news-rel(neo4j)]
 05 │    13   │ ███▌                  [sec×12, enrich-rel-kw(neo4j+Gemini)]
 06 │    18   │ ████▊                 [sec×12, sp500-news-FMP(0615), gen-news-FMP(0645), cat-high(0630), neo4j-hc(0600), daily-news, error-digest]
 07 │    16   │ ████                  [sec×12, cat-medium, cat-low, mover-FMP, press-FMP, heat-score]
 08 │    18   │ ████▊                 [sec×12, market-news-am, classify, analyze-deep⚠Gemini, sync-news-neo4j, keyword-pipeline]
 09 │   ★ 79   │ ████████████████████  [sec×12, realtime×12, indices×12, pulse×60, portfolio×6, screener×4, sentiment, news-rel, ...]
 10 │   ★ 76   │ ███████████████████   [sec×12, realtime×12, indices×12, pulse×60, ...전부 + sp500-news-FMP, classify, analyze-deep⚠Gemini, sync-neo4j, co-mention]
 11 │     74  │ ██████████████████▊   [sec×12, realtime×12, indices×12, pulse×60, rel-confidence]
 12 │   ★ 81  │ ████████████████████▌ [sec×12, realtime×12, indices×12, pulse×60, classify, analyze-deep⚠Gemini, sync-neo4j, gen-news-FMP, neo4j-hc, sync-profiles-neo4j, sync-relations-neo4j, sec-seed]
 13 │     76  │ ███████████████████   [sec×12, ..., cat-high-mid, sp500-news-FMP(1315), seed-selection]
 14 │   ★ 79  │ ████████████████████  [sec×12, ..., cat-medium-pm, classify, analyze-deep⚠Gemini, sync-neo4j, daily-news-pm]
 15 │     76  │ ███████████████████   [sec×12, ..., market-news-pm, sp500-news-FMP(1515)]
 16 │   ★ 80  │ ████████████████████  [sec×12, ..., classify, analyze-deep⚠Gemini, sync-neo4j, breadth, heatmap, extract-daily-kw⚠Gemini]
 17 │    16   │ ████                  [sec×12, daily-prices, cat-high-evening, sp500-news-FMP(1715), gen-news-FMP-evening]
 18 │  ★ 22   │ █████▊                [sec×12, classify, analyze-deep⚠Gemini, sync-neo4j, market-news-evening, sp500-eod, change-pct, eod-pipeline, thesis×3⚠Gemini, indicators, neo4j-hc]
 19 │    14   │ ███▌                  [sec×12, ml-labels, backfill-accuracy]
 20 │    13   │ ███▌                  [sec×12, sp500-financials(101 FMP)]
 21 │    12   │ ███                   [sec×12]
 22 │    13   │ ███▌                  [sec×12, indicators]
 23 │    12   │ ███                   [sec×12]
```

> ★ = 피크 시간대. **09~16시는 분 단위 cache refresh + 5분 주기 가격/지수가 동시 발화하므로 발화 횟수가 매우 많음 (그러나 각 발화는 가벼움 — 10종목 quote 수준).** 18시는 발화 수는 적지만 **무거운 batch가 4분 간격으로 5개 몰림** → 실질 부하 가장 큼.

### 2.1 분 단위 발화 심층

| 분 | 18시 슬롯 (가장 위험) | 비고 |
|----|----------------------|------|
| 00 | sync-sp500-eod-prices (FMP, ~503 종목), thesis-update-readings, market-news-evening, indicators, neo4j-hc, sec-sync | **18:00은 무거운 동기화 다발** |
| 15 | classify-news-batch, thesis-calculate-scores, sec-sync (18:15) | classify는 LLM 사용 시 Gemini 부담 |
| 30 | analyze-news-deep-batch (Gemini, max=50), update-sp500-change-percent, run-eod-pipeline, thesis-create-snapshots, sec-sync (18:30) | **🔴 4개 동시, EOD 의존성 충돌** |
| 35 | thesis-generate-summaries (Gemini) | analyze-deep과 5분차 |
| 45 | sync-news-to-neo4j (neo4j queue) | sec-sync(18:45)와 동일 큐 |

---

## 3. Rate Limit 초과 분석

### 3.1 FMP Starter Plan: 300 calls/min, 10,000 calls/일

#### 3.1.1 위반 가능 핵심 — `collect_sp500_news_fmp_orchestrator` (06:15 / 10:15 / 13:15 / 15:15 / 17:15)

`news/tasks.py:951-980` 구현:

```python
batch_size = 84  # 503 / 6 ≈ 84
batches = [sp500[i:i + batch_size] for i in range(0, len(sp500), batch_size)]
chord(
    collect_sp500_news_fmp_batch.s(batch) for batch in batches
)(collect_sp500_news_fmp_done.si())
```

- **chord = 6개 배치 병렬 디스패치**. 각 배치 84종목 × FMP 호출.
- 평균 워커 처리 속도가 1종목/0.2초만 되어도 → **6 × 84 / (84 × 0.2초) = 30 calls/sec = 1800 calls/min**
- 300 calls/min 한도의 **6배 초과 가능**.
- 일 5회 발화 → 5 × 503 = 2515 calls/일 (이 태스크 단독으로는 RPD 안전, 그러나 **분당 한도가 문제**).

**완화 코드 존재 여부 확인 필요 (감사 범위 외)**: `collect_sp500_news_fmp_batch` 내 sleep, FMP CircuitBreaker, NewsAggregator의 rate-limit, 또는 worker concurrency 제한.

#### 3.1.2 동시 발화 누적 — 06:00~06:50 슬롯

| 시각 | 태스크 | 추정 FMP 호출 |
|------|--------|--------------|
| 06:00 | sync-etf-holdings (Mon) | ~50~150 (S&P SPDR + 주요 ETF) |
| 06:00 | collect-daily-news-morning | 0 (MarketAux 등) |
| 06:00 | neo4j-health-check | 0 |
| 06:15 | collect-sp500-news-fmp-0615 | **~503 (chord)** |
| 06:30 | collect-category-news-high-morning | 가변 (FMP/MarketAux) |
| 06:45 | collect-general-news-fmp-morning | ~수십 (general endpoint) |

**같은 1분(06:15)에 chord가 분당 한도를 초과하면 후속 06:30/06:45가 FMP 429를 받을 가능성**.

#### 3.1.3 18:00 sync-sp500-eod-prices

- `stocks/tasks.py:422` (soft_time_limit=1800s, time_limit=1860s) → 30분 windownormal
- 503 종목, 분당 300 한도 = 최소 1.7분 소요 (이론치). 실제 30분 timeout 잡혀 있는 것은 안전.
- ⚠️ **18:30 run-eod-pipeline / thesis-create-snapshots는 EOD 가격 의존**. 18:00 시작 후 30분 안에 끝나야 18:30 후속이 정합성 유지.

#### 3.1.4 09~16시 5분 주기

- update-realtime-prices: 10종목 × 1초 간격 → 분당 ~10 calls (안전)
- update-market-indices: 지수만 (수십 calls)
- refresh-market-pulse-cache: 1분 주기 → 캐시면 안전, 그러나 cache miss 시 FMP 호출
- 09:00 동시 발화: ~30 calls/min 추정 (안전)

### 3.2 Gemini Free Tier: 15 RPM, 1500 RPD

#### 3.2.1 위험 태스크 매트릭스

| 시각 | 태스크 | 호출 패턴 추정 | 분당 부담 |
|------|--------|---------------|----------|
| 05:30 | enrich-relationship-keywords (limit=100) | 100 articles, 순차 | 가능: 100/2분 = 50 RPM 🔴 |
| 08:00 | keyword-generation-pipeline | 단일 movers 처리 | 가변 |
| **HH:30 (8,10,12,14,16,18)** | **analyze-news-deep-batch (max_articles=50)** | **50/실행, 6회/일** | **단일 실행이 50 calls 버스트 → 15 RPM 초과 🔴** |
| 16:45 | extract-daily-news-keywords | 일일 분석 | (audit P0 #8 코멘트 — 16:30→16:45 이동으로 Gemini 충돌 회피한 이력 있음) |
| 18:35 | thesis-generate-summaries | 가설별 (사용자 가설 수만큼) | 가변, 18:30 analyze-deep과 5분차 |
| 03:00 매월1일 | bulk_generate_korean_overviews (batch=50) | S&P 500 = 10일치 분량 | 월 1회 |

#### 3.2.2 일일 RPD 추정 (평일)

```
analyze-news-deep-batch: 50 × 6회 = 300
classify-news-batch: 가변 (LLM 여부 코드 미확인) ~ 100-200
extract-daily-news-keywords: ~100
keyword-generation-pipeline (gainers): ~50
enrich-relationship-keywords (limit=100): ~100
thesis-generate-summaries: 가설 수 의존 ~50
─────────────────────────────────────
합계 추정: 700~900 RPD (Free 1500의 50~60%)
```

> Free Tier RPD 1500 한도까지는 여유 있으나, **RPM 15** 한도가 단일 태스크 burst에서 초과될 가능성이 가장 큼.

#### 3.2.3 16:30 ↔ 16:45 이력

`config/celery.py:286-289` 주석:
> 16:30 EST에 analyze-news-deep-batch와 Gemini 동시 호출 충돌 → Gemini 15 RPM 2배 초과 위험. 15분 분산하여 회피 (audit P0 #8, 2026-04-26)

**🟢 이 회피는 적용되어 있음.** 그러나:
- analyze-deep 자체가 50 articles burst → 단독으로 15 RPM 초과 가능. 회피의 본질은 "두 태스크가 같은 분에 안 만나도록"이지 "burst 자체 해소"는 아님.

### 3.3 Alpha Vantage 5 calls/min

- **beat_schedule 내 직접 의존 태스크 없음** — `update-economic-indicators`는 FRED API, `update-economic-calendar`도 별도.
- 코드 본체(API_request/)에 AV 호출이 남아있을 수 있으나 cron 트리거는 없음.
- 🟢 안전.

---

## 4. Queue 부하 분석

### 4.1 default queue

- 24시간 가동, 5분 주기 sec-sync는 neo4j 큐로 분리됨.
- 9-16h 동안 1분 단위 refresh-market-pulse-cache가 쌓임 — 그러나 캐시 hit이 정상이면 가벼움.
- 18:30 슬롯에 무거운 batch 4개 (run-eod-pipeline / thesis-create-snapshots / update-sp500-change-percent / analyze-news-deep) 동시 시작 → **prefork worker concurrency가 4 미만이면 큐잉 발생**.

### 4.2 neo4j queue (solo pool, concurrency=1)

| 태스크 | 주기 | 단일 실행 부담 |
|--------|------|---------------|
| `sec-sync-dirty-neo4j` | 5분 | 가변 (dirty count) — 잦은 체크 |
| `sync-news-to-neo4j` | 6회/일 (08~18 짝수시 :45) | max_articles=100 |
| `chainsight-sync-profiles-neo4j` | 12:00 daily | 503 종목 dirty 시 무거움 |
| `chainsight-sync-relations-neo4j` | 12:30 daily | 관계 수만큼 |
| `enrich-relationship-keywords` | 05:30 daily | limit=100 + Gemini |
| `cleanup-expired-news-relationships` | 04:00 daily | 단일 쿼리 |
| `neo4j-health-check` | 6시간마다 (00,06,12,18) | 가벼움 |
| `chainsight-neo4j-dirty-sync` | Sun 04:30 | 주간 누적 동기화 |

#### 4.2.1 12:00 충돌 핫스팟

```
12:00 ┃ neo4j-health-check (가벼움)
12:00 ┃ chainsight-sync-profiles-neo4j (무거움)
12:00 ┃ sec-seed-relations-to-chainsight (default queue, 충돌 X)
12:00 ┃ sec-sync-dirty-neo4j (5분 주기 ↔ 12:00 자체 발화)
12:30 ┃ chainsight-sync-relations-neo4j (무거움)
12:30 ┃ sec-sync-dirty-neo4j
```

**solo pool 1 concurrency**:
- 12:00 sync-profiles가 5분+ 걸리면 12:05 sec-sync-dirty가 대기.
- 12:30 sync-relations가 길어지면 12:35, 12:40 sec-sync-dirty 누적.
- expires=240s(sec-sync-dirty)이 짧아 누적 시 **만료 폐기됨** (data loss 위험은 낮음, 그러나 Neo4j 동기화 지연).

#### 4.2.2 05:30 enrich + Gemini

- `enrich-relationship-keywords`는 `'queue': 'neo4j'` + Gemini 호출.
- solo pool에서 LLM 응답 대기 중에는 다른 neo4j 태스크 전체 블로킹.
- 05:30 시작 + 100 articles × 평균 응답 5초 → ~8분 점유 → 이 동안 sec-sync-dirty 1~2회 만료.

### 4.3 일주일 누적 (Sunday 04:30 슬롯)

```
Sun 03:00 ┃ train-importance-model (default)
Sun 03:00 ┃ cleanup-old-macro-data
Sun 03:30 ┃ generate-shadow-report
Sun 04:00 ┃ cleanup-expired-news-relationships (neo4j)
Sun 04:00 ┃ check-auto-deploy
Sun 04:15 ┃ generate-weekly-ml-report
Sun 04:20 ┃ monitor-ml-performance
Sun 04:30 ┃ chainsight-neo4j-dirty-sync (neo4j)  🔴
Sun 04:30 ┃ train-lightgbm-model (default)
```

- **Sun 04:30**: dirty-sync는 1주일치 누적 동기화 → 매우 길 수 있음. 그 사이 sec-sync-dirty 5분 주기가 신규 dirty를 쌓고, 본 동기화는 그 이전 것만 처리.

---

## 5. 의존성 / 데이터 경합 분석

### 5.1 EOD 파이프라인 의존 사슬 (평일 18시)

```
17:00 update-daily-prices (FMP, 포트폴리오 10종목)
18:00 sync-sp500-eod-prices (FMP, 503 종목)         ← 30분 timeout
18:00 thesis-update-readings                       ← 가격 데이터 의존
18:00 market-news-evening (수집)
18:00 update-economic-indicators (FRED)
18:15 thesis-calculate-scores                      ← readings 완료 의존
18:15 classify-news-batch
18:30 update-sp500-change-percent                  ← 18:00 EOD 완료 의존
18:30 run-eod-pipeline                             ← EOD 시그널 (가격+거래량 의존)
18:30 thesis-create-snapshots                      ← scores 완료 의존
18:30 analyze-news-deep-batch (Gemini)
18:35 thesis-generate-summaries (Gemini)           ← snapshots 의존
18:45 sync-news-to-neo4j
19:00 backfill-signal-accuracy                     ← run-eod-pipeline 완료 의존
19:00 collect-ml-labels
20:00 sync-sp500-financials (FMP, 101 batch)
```

#### 위험 포인트

1. **18:00 → 18:30 (30분 간격)**: sync-sp500-eod-prices가 30분 안에 안 끝나면 18:30 update-sp500-change-percent / run-eod-pipeline / thesis-create-snapshots가 **부정확한/누락된 EOD 데이터로 실행**.
   - mitigation: 각 태스크 자체에 데이터 검증 로직 있는지 별도 확인 필요.
2. **18:15 → 18:30 (15분 간격)**: thesis-calculate-scores → thesis-create-snapshots. 18:15 시작이 길면 18:30 snapshots가 미완료 score로 실행.
3. **18:30 → 18:35 (5분 간격)**: snapshots → summaries. snapshot DB 트랜잭션이 18:35 전 commit 안 되면 summaries가 빈 데이터로 실행.

### 5.2 News 수집 → 분석 사슬

```
06:00 collect-daily-news-morning
06:15 collect-sp500-news-fmp-0615 (chord)
06:30/06:45 cat-high, gen-news-fmp
07:00~07:30 cat-medium, cat-low
08:00 collect-market-news-morning
08:15 classify-news-batch (HH:15, hours=3)         ← 직전 3시간 수집분 분류
08:30 analyze-news-deep-batch (HH:30)              ← 분류 후 상위 15% 분석
08:45 sync-news-to-neo4j
```

- classify(:15) → analyze(:30) → sync(:45) 15분 간격 정합. 🟢 합리적.
- **단**: 06:15 chord가 06:30까지 완료되어야 08:15 classify가 누락 없이 처리. chord 6배치 병렬 + soft_time_limit 600s = 10분. 안전 마진 5분.

### 5.3 Chain Sight 파이프라인

```
Sat 02:00 chainsight-all-profiles                  (장기, expires=7200=2h)
Sat 03:00 chainsight-price-co-movement
Sat 04:00 chainsight-stale-decay
Sat 04:30 chainsight-aggregate-profiles
Sat 05:00 validation-weekly-batch                  ← 위 모든 것 완료 의존
```

- Sat 02:00 all-profiles가 2시간 timeout → 04:00 stale-decay가 완료 전 출발 가능.
- 🟠 expires=7200 (2시간) 의미는 **2시간 후 만료**, 즉 **2시간 안에 시작 안 되면 폐기**. 실행 시간 보장 X.

### 5.4 일일 Chain Sight (12시 슬롯)

```
10:00 chainsight-co-mentions (24시간 windowwindow)
11:00 chainsight-relation-confidence              ← co-mentions 의존
12:00 chainsight-sync-profiles-neo4j (neo4j queue)
12:30 chainsight-sync-relations-neo4j (neo4j queue) ← profiles 동기화 후
13:00 chainsight-seed-selection                   ← 관계 동기화 후
```

- 🟢 의존 순서 준수. 단, neo4j queue 백로그가 12:00→12:30 사이에 발생하면 12:30 relations 시작 지연 → 13:00 seed-selection이 미동기화 데이터 사용 가능.

---

## 6. P0/P1/P2 권고 (이 보고서는 진단만)

### P0 (즉시 검토)

1. **🔴 collect_sp500_news_fmp_orchestrator의 chord 병렬도** (`news/tasks.py:976`)
   - 현재 6배치 병렬 → FMP 300 RPM 초과 위험.
   - 후속 감사: `collect_sp500_news_fmp_batch` 내부 호출 패턴, FMP NewsAggregatorService의 throttle 여부 확인.
2. **🔴 analyze-news-deep-batch의 50건 burst** (`news/tasks.py:511`)
   - max_articles=50, Gemini per-article 호출이라면 RPM 초과.
   - 후속 감사: 함수 본체에서 sleep/throttle/concurrency 제한 확인.
3. **🟠 18:30 4-task 동시 발화**
   - run-eod-pipeline / thesis-create-snapshots / update-sp500-change-percent / analyze-news-deep-batch
   - prefork worker concurrency가 충분치 않으면 thesis-create-snapshots 지연 → 18:35 summaries 실패.

### P1 (1주 내)

4. **sec-sync-dirty-neo4j 5분 주기 vs solo pool 백로그**
   - 12:00, 12:30, 05:30 슬롯에서 long-running 태스크와 큐 충돌.
   - 권고: 주기를 10분으로 늘리거나, 큐를 분리(neo4j_high_freq).
5. **18:00 sync-sp500-eod-prices 의존 사슬 검증**
   - 30분 timeout 안에 503 종목 완료 보장 안 됨 시 18:30 후속 태스크 데이터 정합성 검증 필요.
6. **05:30 enrich + Gemini이 neo4j queue 점유**
   - 8분 가까이 점유 시 sec-sync-dirty 만료 폐기.
   - 권고: enrich를 default queue로 이동 + Neo4j 쓰기만 별도 short task로 분리.

### P2 (모니터링)

7. **Gemini RPD 추정 700~900/일** — 1500 한도의 50~60%. 알림/회고/모델 다중 호출 추가 시 80% 초과 가능. 일일 사용량 메트릭 수집 권고.
8. **Sat 02:00~05:00 Chain Sight + Validation 사슬** — expires=7200이 실행 보장 아님. PeriodicTask last_run_at 모니터링 필요.
9. **PeriodicTask DB drift** — `config/celery.py:128-134` 주석에 따르면 수동 등록. 자동 검증 스크립트 없음 (이전 감사 P0).

---

## 7. 부록 A — 발화 횟수 카운트 산출 근거

```
sec-sync-dirty-neo4j      = 12 trigger/시간 (5분마다)
realtime/indices/portfolio = 9-16h 평일만, 분 단위 refresh-pulse는 60/시간
```

09시 79개 발화 = 12(sec) + 12(realtime 5min) + 12(indices 5min) + 60(pulse 1min, 09시 한 시간) - 17(겹침 보정) ≈ 79

---

## 8. 부록 B — 누락/관찰 노트

- `update-economic-indicators` cron `hour='6,12,18,22'`는 평일만 (`day_of_week='1-5'`). FRED는 주말 업데이트 없으므로 일관됨.
- `cleanup-expired-news-relationships`는 매일 발화하지만 (`day_of_week` 미지정) sec-sync과 같은 큐(neo4j) 사용.
- `extract-news-relations` (`hour=9`)와 `chainsight-co-mentions` (`hour=10`)는 day_of_week 미지정 → 주말도 발화. 주말 뉴스 적은 것 고려 시 의도된 동작인지 확인 필요.
- `celery-error-digest` (`hour=7`, 매일) — 매주 토요일에는 금요일 에러를 집계, 일요일에는 토요일 에러(없음)를 집계. 의도된 동작 추정.
- `chainsight-heat-score-daily` (`hour=7`, 매일, 주말 포함) ↔ `chainsight-seed-selection` (`hour=13`, 매일). 의존 순서 준수. 주말 데이터 부족 시 무작동 가능.
- 모든 cron의 timezone은 settings.py의 `CELERY_TIMEZONE` 설정에 의존. 본 보고서는 EST 가정으로 분석. UTC 사용 시 모든 시간대 -5 시프트 필요.

---

## 9. 검증 방법 (코드 수정 없이 가능)

```bash
# DB의 PeriodicTask vs config dict drift 확인
python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
from django.conf import settings
from config.celery import app
db_names = set(PeriodicTask.objects.values_list('name', flat=True))
cfg_names = set(app.conf.beat_schedule.keys())
print('DB only:', db_names - cfg_names)
print('Config only:', cfg_names - db_names)
"

# 최근 24h FMP 호출 추정 (collection_logs 테이블 가정)
python manage.py shell -c "
from news.models import CollectionLog
from datetime import timedelta
from django.utils import timezone
since = timezone.now() - timedelta(hours=24)
qs = CollectionLog.objects.filter(created_at__gte=since, source='fmp')
print('24h FMP collections:', qs.count())
print('per task:', list(qs.values('task_name').annotate(c=__import__('django.db.models', fromlist=['Count']).Count('id'))))
"

# Neo4j queue 백로그 (Redis 직접 조회)
redis-cli LLEN neo4j
redis-cli LRANGE neo4j 0 5
```

---

## 10. 감사 결론

**전반 평가**: 🟠 **개선 필요 (구조적 문제 2건, 잠재 위험 5건)**

- 가장 큰 구조적 위험은 **chord 6병렬 FMP 호출** (3.1.1) — 운영 중 FMP 429 발생 시 5회/일 모든 슬롯이 영향.
- 두 번째는 **analyze-deep의 Gemini burst** (3.2.1) — 일 6회 발화가 매번 RPM 한도를 초과할 가능성.
- 세 번째는 **18:30 4-task 동시** (5.1) — concurrency 부족 시 thesis 사슬 깨짐.

이 3건은 코드 본체(`news/tasks.py`, `serverless/services/`, prefork concurrency 설정) 추가 감사로 검증 필요. 이번 감사는 cron 선언만 분석한 결과이므로 실제 구현이 throttle/CircuitBreaker로 완화하고 있는지는 별도 확인.
