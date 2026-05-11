# Celery Beat 스케줄 감사 보고서

- **감사 일자**: 2026-05-04
- **대상**: `config/celery.py` `app.conf.beat_schedule`
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (config/settings.py:413) — 모든 시각은 **ET 기준**
- **스케줄러**: `django_celery_beat.schedulers:DatabaseScheduler` (config dict는 reference, 실제 실행은 DB `PeriodicTask`)
- **모드**: 읽기 전용 (코드 수정 없음)
- **방법**: beat_schedule 정적 분석 → 시간대별 launch 카운트 → API/Queue 부하 추정

> **주의**: 본 보고서는 config dict 기준이다. config/celery.py:118-134 주석에 명시된 대로 DB와 drift가 있을 수 있으므로, 실제 운영 부하는 `PeriodicTask` 테이블과의 diff 검증이 필요하다 (수동 점검 필요 항목 P1).

---

## 0. 요약

| 항목 | 값 |
|---|---|
| 정의된 스케줄 엔트리 | **약 85개** |
| 사용 큐 | `default` (대부분), `neo4j` (--pool=solo, 14개 태스크) |
| 외부 API 의존 태스크 | FMP **17개**, Gemini **8개+**, FRED **3개**, SEC EDGAR **3개**, SPDR **1개**, Marketaux/Finnhub **6개** |
| **Alpha Vantage 직접 의존 스케줄** | **0개** (✅ 단, provider 내부 fallback 호출은 별도) |
| 피크 시간대 | **18:00 ET** (12개 heavy task 동시 dispatch, FMP 500+ 호출 + Gemini + Neo4j) |
| 가장 빈번한 태스크 | `refresh-market-pulse-cache` (매분, 9-16시 → 평일 480회/일) |
| 가장 짧은 expires | `sec-sync-dirty-neo4j` **expires=240s**, 5분 주기 (288회/일) ⚠️ |
| 종합 판정 | **🟠 고위험** — 18:00 burst의 FMP 한도 초과, neo4j 큐 backlog, Gemini 동시 호출 미흡한 분산 |

---

## 1. Rate Limit 초과 위험 분석

### 1.1 FMP (Starter Plan: 300 calls/min)

**스케줄 dispatch 시각별 FMP 의존 태스크 (평일 ET)**

| 시각 | 태스크 | FMP 추정 호출 수 | 비고 |
|---|---|---|---|
| 06:15 | `collect-sp500-news-fmp-0615` (orchestrator) | ~100~500 | S&P 500 종목별 뉴스 fetch |
| 06:45 | `collect-general-news-fmp-morning` | 1~수 | general endpoint |
| 07:30 | `sync-daily-market-movers` | ~10 | gainers/losers/active |
| 07:45 | `collect-press-releases-fmp` (max=50) | 50 | symbol별 press releases |
| 09:00–16:55 (평일) | `update-realtime-prices` (5분 주기) | symbol수 × 96/일 | **한 번에 300+ 우려** |
| 09:00–16:55 (평일) | `update-market-indices` (5분 주기) | 인덱스 수 × 96/일 | 동시 dispatch |
| 10:15 | `collect-sp500-news-fmp-1015` | ~100~500 | |
| 12:30 | `collect-general-news-fmp-noon` | 1~수 | |
| 13:15 | `collect-sp500-news-fmp-1315` | ~100~500 | |
| 15:15 | `collect-sp500-news-fmp-1515` | ~100~500 | |
| 17:00 | `update-daily-prices` | symbol수 | |
| 17:15 | `collect-sp500-news-fmp-1715` | ~100~500 | |
| 17:45 | `collect-general-news-fmp-evening` | 1~수 | |
| **18:00** | `sync-sp500-eod-prices` | **~500** | S&P 500 EOD 일괄 |
| **18:00** | `update-economic-indicators` (FRED, 동일 분) | 0 | FRED는 별도 한도 |
| **18:00** | `thesis-update-readings` | symbol×지표 | **FMP 동시 호출** |
| 20:00 | `sync-sp500-financials` (101개/일) | 101 | 5일 1회전 |

**🔴 P0 위험 — 18:00 ET FMP burst**

- 18:00 동일 분에 `sync-sp500-eod-prices` (≈500 calls) + `thesis-update-readings` (지표 N개 × 종목 M개) 동시 dispatch.
- 두 태스크가 모두 default queue를 공유 → solo pool 또는 prefork 동시성에 따라 **첫 1분 내 500+ 호출 발생 가능**.
- FMP Starter 300/min 초과 시 429 → 재시도 폭주 → 후속 18:30 `run-eod-pipeline` 진입 시 데이터 미완성 위험.
- **권장 검증**: `stocks.tasks.sync_sp500_eod_prices` 내부 batch sleep / chunked 호출 여부 점검 (코드 미확인).

**🟠 P1 위험 — 9:00–16:00 매 5분 burst**

- `update-realtime-prices`와 `update-market-indices`가 **동일 minute** (`*/5`)에 fire → 매 5분 두 태스크가 동시에 FMP를 두드림.
- 거래시간 8시간 × 12회/시 = **192회 dispatch/일**. 각 dispatch에서 watchlist symbol 수에 따라 한도 초과 가능.
- 인덱스+실시간 분리 dispatch (`*/5,1` 같은 offset) 부재.

**🟡 P2 — SP500 News orchestrator 5회 dispatch**

- 06:15 / 10:15 / 13:15 / 15:15 / 17:15 — 각 dispatch에서 S&P 500 종목별 뉴스 fetch.
- 1회 dispatch에서 500개 symbol을 sequential 호출하면 1.7분(300 calls/min 기준) 소요. 거리상 2시간 간격이라 회차 간 충돌 없음.
- **단, 단일 dispatch가 한도를 안 넘는지 orchestrator 내부 throttle 점검 필요**.

### 1.2 Gemini (Free Tier: 15 RPM, 1500 RPD)

**LLM 호출 dispatch 시각 (UTC가 아닌 ET 기준, 평일)**

| 시각 | 태스크 | 추정 LLM 호출 수 | 큐 |
|---|---|---|---|
| 05:30 | `enrich-relationship-keywords` (limit=100) | 100 | neo4j |
| 08:00 | `keyword-generation-pipeline` (gainers) | ~10~30 | default |
| 08:15 | `classify-news-batch-morning` (3h window) | N (수십) | default |
| 08:30 | `analyze-news-deep-batch` (max=50) | **50** | default |
| 09:00 | `extract-news-relations` (24h window) | N (서비스 의존) | default |
| 10:00 | `chainsight-co-mentions` (7d window) | N (서비스 의존) | default |
| 10:15 | `classify-news-batch-morning` | N | default |
| 10:30 | `analyze-news-deep-batch` (50) | 50 | default |
| 11:00 | `chainsight-relation-confidence` | N | default |
| 12:15 | `classify-news-batch-morning` | N | default |
| 12:30 | `analyze-news-deep-batch` (50) | 50 | default |
| 14:15 | `classify-news-batch-morning` | N | default |
| 14:30 | `analyze-news-deep-batch` (50) | 50 | default |
| 16:15 | `classify-news-batch-morning` | N | default |
| 16:30 | `analyze-news-deep-batch` (50) | 50 | default |
| **16:45** | `extract-daily-news-keywords` | N (수십) | default |
| 18:15 | `classify-news-batch-morning` | N | default |
| 18:30 | `analyze-news-deep-batch` (50) | 50 | default |

**🔴 P0 위험 — Gemini 1500 RPD 초과 가능**

- `analyze-news-deep-batch` 단독: 6회 × 50 articles = **300 calls/일** (기사당 1 LLM 호출 가정).
- `enrich-relationship-keywords`: 100 calls/일.
- `classify-news-batch-morning`: 6회 × N (3h 윈도우의 미분류 기사 수) — 변동성 높음.
- `keyword-generation-pipeline` + `extract-daily-news-keywords` + Chain Sight 3종 + sec_pipeline LLM 호출(수동/배치) 합치면 **1500 RPD 임계치 도달 가능**.
- **권장 모니터링**: 일별 Gemini 호출 카운터 로깅 부재 시 추가 필요.

**🟠 P1 위험 — 8:00–8:30 ET Gemini 동시 호출**

- 08:00 `keyword-generation-pipeline` → 08:15 `classify-news-batch-morning` → 08:30 `analyze-news-deep-batch`.
- 15분 간격이지만, 각 태스크가 자체 throttle 없이 비동기 호출 시 **15 RPM** 초과 위험.
- 4초 spacing 미적용 시 burst 발생.

**✅ 양호 — 16:30 / 16:45 분리 (audit P0 #8, 2026-04-26 적용)**

- `analyze-news-deep-batch` (16:30) ↔ `extract-daily-news-keywords` (16:45) → 15분 간격 적용 완료.
- 코드 주석에 명시: "Gemini 15 RPM 2배 초과 위험 → 15분 분산 회피".

### 1.3 Alpha Vantage (5 calls/min)

**🟢 양호 — beat_schedule에서 AV 직접 의존 스케줄 0건 확인**

- `grep "alpha\|ALPHA\|alphavantage" config/celery.py` → 매치 없음.
- AV 호출은 provider 내부 fallback 또는 수동 트리거에만 존재.
- **별도 점검 권장**: `api_request/providers/alphavantage/` 호출이 다른 태스크 내부에서 사용되는 경우, 그 호출자가 12s sleep 규칙을 따르는지 확인 (스케줄 단위가 아닌 코드 단위 audit, 본 보고서 범위 외).

### 1.4 FRED (정책상 분당 한도 매우 관대)

**🟢 양호** — `update-economic-indicators` 1일 4회 (06,12,18,22 ET), `update-economic-calendar` 1일 1회. FRED 한도 영향 미미.

---

## 2. Queue 몰림 분석

### 2.1 default queue (대다수 태스크)

**18:00–18:45 ET 폭주 구간 (평일)**

| 시각 | 태스크 | 의존성 | 부하 |
|---|---|---|---|
| 18:00 | `collect-market-news-evening` | 외부 API | 중 |
| 18:00 | `update-economic-indicators` | FRED | 저 |
| 18:00 | `sync-sp500-eod-prices` | FMP × ~500 | **🔴 중대** |
| 18:00 | `thesis-update-readings` | FMP × N×M | 중-고 |
| 18:00 | `neo4j-health-check` | neo4j 큐로 라우트 (`*/6` hour) | 별도 |
| 18:15 | `thesis-calculate-scores` | DB only | 중 |
| 18:15 | `classify-news-batch-morning` | Gemini | 중 |
| 18:30 | `run-eod-pipeline` | DB heavy | **고** |
| 18:30 | `thesis-create-snapshots` | DB | 중 |
| 18:30 | `update-sp500-change-percent` | DB | 저 |
| 18:30 | `analyze-news-deep-batch` | Gemini × 50 | 고 |
| 18:45 | `sync-news-to-neo4j` (queue=neo4j) | 별도 | — |

- **6개의 default-queue 태스크가 18:30 동시 dispatch**.
- macOS solo pool: 모두 직렬 실행 → 첫 태스크가 N분 소요 시 후속 태스크는 그만큼 밀림 (expires=3600s가 안전망이지만 데이터 신선도 손실).
- Linux prefork worker concurrency=N 가정 시 N개 동시 실행 가능하나, FMP/Gemini 한도를 코어 수만큼 곱해서 초과.

**🟠 P1 위험 — Thesis EOD 의존 체인의 15분 간격 부족**

- 설계 의도: `thesis-update-readings`(18:00) → `thesis-calculate-scores`(18:15) → `thesis-create-snapshots`(18:30).
- `update-readings`가 FMP × N지표 × M종목으로 15분 내 완료 보장이 없음.
- solo pool에서 18:00의 다른 5개 태스크(EOD prices, market-news 등)가 선행 점유 시 readings 자체가 18:15 시점에도 미완료 → **calculate-scores가 stale data로 실행**.
- 보호 메커니즘: Celery chain 또는 group이 아닌 **독립 cron 등록** → 의존성 misalignment.

**거래시간 9:00–16:55 high-frequency 구간**

- 매분: `refresh-market-pulse-cache` (60/시 × 8시간 = 480회/평일).
- 매 5분: `update-realtime-prices` + `update-market-indices` (24/시 × 8 = 192회/평일).
- 매 10분: `calculate-portfolio-values` (48/평일).
- 매 15분: `check-screener-alerts` (32/평일).
- 매 30분: `check-pipeline-alerts` (24/일, 종일).
- 시간당 dispatch ≈ **115회 (거래시간 평일 기준)**.
- macOS solo pool 환경이면 **반드시 backlog 발생** (1초 평균 처리시간 가정 시 매시간 115초 부하 → 비현실적).
- **권장**: `refresh-market-pulse-cache`의 task 본문이 캐시 hit-only 경량 작업인지 확인 (코드 미확인 항목).

### 2.2 neo4j queue (--pool=solo, 동시 1개)

| 시각 | 태스크 | 빈도 | expires |
|---|---|---|---|
| 매 5분 (전일) | `sec-sync-dirty-neo4j` | **288회/일** | **240s ⚠️** |
| 매 6시간 | `neo4j-health-check` | 4회/일 | (none) |
| 매일 04:00 | `cleanup-expired-news-relationships` | 1 | 3600 |
| 매일 05:30 | `enrich-relationship-keywords` (Gemini+Neo4j) | 1 | 3600 |
| 매일 12:00 | `chainsight-sync-profiles-neo4j` | 1 | 3600 |
| 매일 12:30 | `chainsight-sync-relations-neo4j` | 1 | 3600 |
| 평일 08/10/12/14/16/18:45 | `sync-news-to-neo4j` (max=100) | 6/평일 | 3600 |
| 일요 04:30 | `chainsight-neo4j-dirty-sync` | 1/주 | 3600 |

**🔴 P0 위험 — `sec-sync-dirty-neo4j` expires=240s**

- 5분 주기로 dispatch되는데 expires=240s(4분).
- solo pool에서 직전 작업이 4분을 넘기면 다음 회차는 **expire되어 silent drop**.
- 12:00–12:45 구간에 `chainsight-sync-profiles-neo4j` (12:00) + `chainsight-sync-relations-neo4j` (12:30) + `sync-news-to-neo4j` (12:45)가 같은 큐에 진입 → backlog 시 sec-sync-dirty의 12:05/12:10/12:15/12:20/12:25/12:30/12:35/12:40 회차가 **연쇄 drop 가능**.
- **권장**: expires를 600s 이상으로 늘리거나, sec-sync-dirty를 별도 큐로 분리.

**🟠 P1 위험 — 12:00 peak**

- 하루 중 neo4j 큐 가장 붐비는 구간: 12:00 profile sync + 12:30 relation sync + 12:45 news sync + sec-sync-dirty (12:00, 12:05, ..., 12:55) = **15회 dispatch / 1시간**.
- solo pool로 직렬 처리 → backlog 위험 명백.

**🟢 양호** — 18:45 sync-news-to-neo4j는 18:00–18:30 default queue burst와 큐가 분리되어 있어 영향 적음.

### 2.3 시간대별 task launch 분포

`sec-sync-dirty-neo4j`(매5분), `refresh-market-pulse-cache`(매1분, 9-16시), `check-pipeline-alerts`(매30분), `update-realtime-prices`/`update-market-indices`(매5분, 9-16시), `calculate-portfolio-values`(매10분, 9-16시), `check-screener-alerts`(매15분, 9-16시) 6개 high-frequency를 별도로 두고, "**heavy/discrete task**"만 카운트한 결과:

```
시간(ET) │ heavy 태스크 launch 수 (평일)
─────────┼────────────────────────────────────────────────────────
 00      │ █                                  (1)  neo4j-health
 01      │ █                                  (1)  econ-calendar
 02      │                                    (0)
 03      │                                    (0)
 04      │ █                                  (1)  cleanup-news-rel
 05      │ █                                  (1)  enrich-rel-kw
 06      │ ██████                             (6)  4 news + econ + neo4j-h
 07      │ ██████                             (6)  movers + 2 cat-news + press + heat-score + err-digest
 08      │ █████                              (5)  market-news + kw-pipe + classify + analyze + neo4j-sync
 09      │ ██                                 (2)  sentiment + extract-rel
 10      │ █████                              (5)  sp500-news + co-mention + classify + analyze + neo4j-sync
 11      │ █                                  (1)  rel-confidence
 12      │ ██████████                        (10) econ + market-news + 2 chainsight-sync + sec-seed + general + classify + analyze + news-neo4j + neo4j-h
 13      │ ███                                (3)  cat-news + sp500-news + seed-selection
 14      │ █████                              (5)  daily-news + cat-medium + classify + analyze + neo4j-sync
 15      │ ██                                 (2)  market-news + sp500-news
 16      │ ██████                             (6)  extract-kw + classify + analyze + neo4j-sync + breadth + heatmap
 17      │ ████                               (4)  daily-prices + cat-high + sp500-news + general
 18      │ ████████████                      (12) ★ PEAK ★ market-news + econ + sp500-eod + thesis-readings + thesis-scores + eod-pipe + thesis-snap + change-pct + classify + analyze + news-neo4j + neo4j-h
 19      │ ██                                 (2)  ml-labels + backfill
 20      │ █                                  (1)  sp500-financials
 21      │                                    (0)
 22      │ █                                  (1)  econ-indicators
 23      │                                    (0)
─────────┴────────────────────────────────────────────────────────
```

**고빈도 태스크 포함 전체 launch 합계 (평일, 시간대별)**

```
시간(ET) │ total launch 수 (평일, sec-sync-dirty=12 + check-pipeline=2 기본 포함)
─────────┼────────────────────────────────────────────────────────
 00      │ ███                          15
 01      │ ███                          15
 02      │ ███                          14
 03      │ ███                          14
 04      │ ███                          15
 05      │ ███                          15
 06      │ ████                         20
 07      │ ████                         20
 08      │ ████                         19
 09      │ ██████████████████████      110 ← 거래시간 진입
 10      │ ██████████████████████      113
 11      │ █████████████████████       109
 12      │ ███████████████████████     118 ★ neo4j 큐 + default 동시 피크
 13      │ ██████████████████████      111
 14      │ ██████████████████████      113
 15      │ ██████████████████████      110
 16      │ ██████████████████████      114 ← 거래시간 마지막
 17      │ ████                         18
 18      │ █████                        26 ★ heavy task 피크 (12개)
 19      │ ███                          16
 20      │ ███                          15
 21      │ ███                          14
 22      │ ███                          15
 23      │ ███                          14
─────────┴────────────────────────────────────────────────────────
```

> **해석**: 9–16시는 high-frequency 캐시/실시간 태스크가 부하의 90%를 차지. **18시는 heavy task 12개 동시 dispatch로 default queue가 가장 위험**. 12시는 neo4j queue + default queue 동시 부하 (10 heavy + 12 sec-sync-dirty + 2 chainsight-neo4j-sync) → **neo4j 큐 backlog 위험 1순위**.

---

## 3. 스케줄 겹침 / 의존성 위반

### 3.1 동일 분 dispatch (default queue)

| 시각 | 동시 dispatch 태스크 | 큐 | 위험 |
|---|---|---|---|
| 매 5분 (9-16시) | `update-realtime-prices` + `update-market-indices` + `refresh-market-pulse-cache`(매분) + (매10분일 때) `calculate-portfolio-values` + (매15분일 때) `check-screener-alerts` | default | 🟠 prefork concurrency 의존 |
| 06:00 평일 | `collect-daily-news-morning` + `update-economic-indicators` (+ Mon: `sync-etf-holdings`) (+ Day1: `sec-check-new-filings`) | default | 🟡 |
| 07:00 매일 | `chainsight-heat-score-daily` + `celery-error-digest` (+ 평일: `collect-category-news-medium-morning`) | default | 🟢 부담 적음 |
| 09:00 매일 | `aggregate-daily-sentiment` (평일) + `extract-news-relations` (every day) | default | 🟢 |
| 12:00 매일 | `update-economic-indicators` (평일) + `collect-market-news-noon` (평일) + `chainsight-sync-profiles-neo4j` + `sec-seed-relations-to-chainsight` | default + neo4j | 🟠 |
| 17:00 평일 | `update-daily-prices` + `collect-category-news-high-evening` | default | 🟡 |
| **18:00 평일** | `collect-market-news-evening` + `update-economic-indicators` + `sync-sp500-eod-prices` + `thesis-update-readings` (+ `neo4j-health-check`) | default + neo4j | **🔴 P0** |

### 3.2 의존성 chain (선행 미완료 시 후속 stale)

**Thesis EOD chain** — 의존성 명시되지 않은 시간 기반 trigger:

```
18:00 thesis-update-readings   (FMP heavy, N분 소요)
  ↓ 15분 gap
18:15 thesis-calculate-scores  (readings 완료 가정)
  ↓ 15분 gap
18:30 thesis-create-snapshots  (scores 완료 가정)
```

- **18:00 default queue가 동시에 다른 5개 태스크 처리 중** → readings가 18:15까지 끝날 보장 없음.
- Celery `chain()` 또는 `signature(...).apply_async(countdown=...)` 미사용 → 시간 기반 race.

**Chain Sight 주말 chain (Sat)**:

```
02:00 chainsight-all-profiles
03:00 chainsight-price-co-movement
04:00 chainsight-stale-decay
04:30 chainsight-aggregate-profiles
05:00 validation-weekly-batch
```

- 1시간 간격이라 비교적 안전. 단, `all-profiles`가 1시간 내 완료 보장 없음.

**EOD Dashboard chain**:

```
18:00 sync-sp500-eod-prices  (FMP, ~500 calls)
   ↓ 30분 gap
18:30 run-eod-pipeline       (EOD prices 의존)
   ↓ 30분 gap
19:00 backfill-signal-accuracy
```

- 30분 gap은 비교적 안전하나, FMP rate limit 초과 시 가격 sync 미완료 → EOD 시그널 계산 불일치.

**News Intelligence chain (매 2시간 평일)**:

```
HH:15 classify-news-batch-morning   (Gemini 분류)
HH:30 analyze-news-deep-batch       (Gemini 심층, 분류 후)
HH:45 sync-news-to-neo4j            (분석 결과 → Neo4j)
```

- 15분 간격, 일관된 패턴. **8/10/12/14/16/18시 6회 반복**.
- 위험: classify가 15분 내 미완료 시 analyze가 미분류 데이터 작업 → 결과 빈약.
- 중복 dispatch 시 `expires=3600` 안전망 있음.

**Chain Sight 일일 동기화 chain**:

```
10:00 chainsight-co-mentions          (extract from news)
11:00 chainsight-relation-confidence  (co-mention 후 갱신)
12:00 chainsight-sync-profiles-neo4j  (default → neo4j queue)
12:30 chainsight-sync-relations-neo4j (profile sync 후)
13:00 chainsight-seed-selection       (관계 동기화 후)
```

- 30분~1시간 gap, 안전한 편. 단, 12:00의 sec-seed-relations-to-chainsight 동시 dispatch와 default-queue 경합.

### 3.3 데이터 경합

| 자원 | 경합 태스크 | 경합 종류 |
|---|---|---|
| `Stock.change_percent` (테이블) | `update-realtime-prices` (매5분, FMP) ↔ `update-sp500-change-percent` (18:30, 일괄) | **18:30에 모두 정지된 후 update 가정**. 18:30이 아직 거래시간 후 30분 시점이라 OK. |
| `DailyPrice` | `update-daily-prices` (17:00) ↔ `sync-sp500-eod-prices` (18:00) | **둘 다 EOD 가격 작성**. 두 태스크가 동일 종목 row를 다루면 update 충돌. 타이밍은 분리되었으나 동일 데이터 source가 다중 경로로 진입. |
| Neo4j `Stock` 노드 | `chainsight-sync-profiles-neo4j` (12:00) ↔ `sync-news-to-neo4j` (12:45) ↔ `sec-sync-dirty-neo4j` (12:00,05,...) | solo pool로 직렬화 → 경합 자체는 없으나 backlog 발생 시 신선도 손상 |
| Gemini API 카운터 | 8:00~8:30 + 10:15~10:30 + 12:15~12:30 + 14:15~14:30 + 16:15~16:45 + 18:15~18:30 | 동시 호출 시 RPM 초과. **15분 분산 적용된 곳은 안전**. |

---

## 4. 발견 사항 우선순위

### 🔴 P0 (즉시 조치 권장)

1. **`sec-sync-dirty-neo4j` expires=240s + 5분 주기** (config/celery.py:773-774)
   - solo pool neo4j 큐에서 backlog 시 silent drop. expires를 1200s 이상으로 상향.
2. **18:00 ET FMP burst** (sync-sp500-eod-prices + thesis-update-readings 동시 dispatch)
   - 한 쪽에 1~3분 countdown 추가하거나 chain으로 명시적 직렬화.
3. **Gemini 1500 RPD 임계 추정** (analyze-news-deep-batch 단독 300, 합계 600+/일 가능)
   - 일별 호출 카운터 로깅 + 경보 임계값 설정. Free tier 가정 시 paid 전환 또는 호출 분산.

### 🟠 P1 (1주 이내 검토)

4. **Thesis EOD 15분 간격의 race condition** (18:00→18:15→18:30)
   - Celery `chain()`으로 명시적 의존성 표현. 또는 readings 완료 후 calculate를 signal로 trigger.
5. **9:00–16:00 거래시간 default-queue backlog**
   - `refresh-market-pulse-cache` 매분이 cache hit-only 경량 작업인지 확인. solo pool 환경이면 5분 주기로 완화 검토.
6. **Beat schedule drift** (config dict ↔ DB `PeriodicTask`)
   - config/celery.py:118-134 주석에 명시된 수동 점검을 자동화 (관리 명령 또는 헬스체크).

### 🟡 P2 (모니터링 필요)

7. **`update-realtime-prices` + `update-market-indices` 동일 분 dispatch**
   - 한 쪽에 minute offset (`*/5,2`) 적용으로 burst 분산.
8. **5회 SP500 News orchestrator의 단일 dispatch 내부 throttle**
   - orchestrator 코드 점검 (본 audit 범위 외).

### 🟢 양호 (변경 불필요)

- AV 직접 의존 스케줄 0건.
- FRED 호출 빈도 적정.
- 16:30 ↔ 16:45 Gemini 분산 적용 완료 (audit P0 #8, 2026-04-26).
- 주말 Chain Sight chain 1시간 간격 적정.
- `expires` 값이 대다수 태스크에 적절히 설정됨 (3600s).

---

## 5. 권장 후속 조치 (감사 범위 외)

본 보고서는 **read-only 정적 분석**이다. 다음 항목은 추가 audit 또는 코드 변경이 필요:

1. **DB `PeriodicTask`와 config dict diff 자동화** — `python manage.py check_beat_drift` 같은 관리 명령.
2. **각 태스크의 평균 실행 시간 측정** — `TaskResult` 테이블 분석으로 backlog 실측.
3. **FMP/Gemini 일별 호출 카운터 대시보드** — 한도 초과 사전 경보.
4. **Celery `chain()` / `group()` 적용 후보 식별** — 시간 기반 trigger를 명시적 의존성으로 전환.
5. **AV 호출이 다른 provider 내부에서 발생하는지 별도 audit** — `api_request/providers/alphavantage/` 호출 trace.

---

**감사자**: Claude (Opus 4.7)
**감사 범위**: `config/celery.py:135-807` (beat_schedule)
**참조 문서**: `sub_claude_md/coding-rules.md` (외부 API rate limits), CLAUDE.md (Harness Protocol)
