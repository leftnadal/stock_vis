# Beat Schedule Audit Report

- **감사일**: 2026-05-20 (KST), 작성: 2026-05-21
- **대상**: `config/celery.py` `app.conf.beat_schedule` (라인 135–814)
- **태스크 총수**: 71개 (선언적 reference)
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (ET 기준)
- **주의**: `CELERY_BEAT_SCHEDULER = django_celery_beat.schedulers:DatabaseScheduler` → dict는 reference. 본 감사는 dict를 진실의 소스로 가정하며, DB의 `PeriodicTask`와 drift가 있을 수 있음 (수동 diff 필요)

---

## 0. Executive Summary

| 위험도 | 항목 | 비고 |
|--------|------|------|
| 🔴 P0 | **18:30 ET 슈퍼피크** — 4개 태스크 동시 + 30분 갭 의존성 체인 | `sync-sp500-eod-prices(18:00)` → `run-eod-pipeline(18:30)` 30분 내 미완료 시 EOD 파이프라인 빈 데이터 |
| 🔴 P0 | **Gemini 15 RPM 위험** — `analyze-news-deep-batch(max_articles=50)` 분당 50회 호출 가능 | 코드 내부에 rate-limiter 없을 시 15 RPM 3.3배 초과 |
| 🟡 P1 | **Neo4j 큐 적체** — `sec-sync-dirty-neo4j` */5분 24/7 + solo pool 1 동시 | 12:00 ET sync 폭주 시 5분 윈도우 초과 위험 |
| 🟡 P1 | **`hour='8,10,12,14,16,18'` 트리플 체인** — classify(:15) / deep(:30) / sync-neo(:45) 매 2시간 | 분류·분석·동기화가 각 15분 안에 끝나야 다음 라운드 데이터 정합성 보장 |
| 🟡 P1 | **DST 미준수 가능성** — 일부 주석 "UTC"와 실제 `crontab(hour=...)` ET 해석 불일치 | `chainsight-heat-score-daily` 등 주석은 "UTC 07:00"이지만 실제 ET 07:00 = UTC 11:00 (DST 시 12:00) |
| 🟢 P2 | **Alpha Vantage 미사용** — 스케줄에 AV 의존 태스크 없음 | 5 calls/min 한도 위반 없음 |

---

## 1. API 의존성 분류

### 1.1 FMP 의존 태스크 (Starter 300 calls/min, 10k/일)

| 태스크 | 스케줄 (ET) | 추정 호출량 | 비고 |
|--------|-------------|-------------|------|
| `update-realtime-prices` | `*/5 9-16 1-5` | 12 트리거/시간, 종목별 bulk quote | 평일 장중 96 트리거/일 |
| `update-daily-prices` | `17:00 1-5` | 1회/일, EOD batch | |
| `update-market-indices` | `*/5 9-16 1-5` | 12 트리거/시간 | realtime과 동시간 발사 |
| `sync-sp500-financials` | `20:00 1-5` | 101 종목/일, 5일 회전 | 분당 호출 분산 필요 |
| `sync-sp500-eod-prices` | `18:00 1-5` | S&P 500 일괄 | 500종목 bulk 가능 시 안전 |
| `collect-sp500-news-fmp-*` ×5 | `06:15, 10:15, 13:15, 15:15, 17:15` | orchestrator로 청크 | 분당 부하 orchestrator 내부 통제 의존 |
| `collect-press-releases-fmp` | `07:45 1-5` | `max_symbols=50` | |
| `collect-general-news-fmp-*` ×3 | `06:45, 12:30, 17:45` | 일반 뉴스 폴링 | |
| `thesis-update-readings` | `18:00 1-5` | 지표 데이터 수집 | sp500-eod-prices와 **동시간 충돌** |

**리스크**:
- ⚠️ 18:00 ET 정각에 `sync-sp500-eod-prices` + `thesis-update-readings` + `collect-market-news-evening` + `update-economic-indicators`가 동시 발사. FMP가 3개 (FRED는 macro), 동시간 burst가 300 calls/min 안에 들어오는지는 각 태스크 내부 batching 로직에 의존.
- ⚠️ `*/5 9-16` 동시 발사 시(realtime + indices) 매 5분마다 2개 태스크가 같은 시각에 큐잉 → default 워커가 prefork일 경우 동시 실행, FMP 동시 호출 증가.

### 1.2 Gemini 의존 태스크 (Free 15 RPM, 1500 RPD)

| 태스크 | 스케줄 (ET) | 호출 패턴 |
|--------|-------------|----------|
| `keyword-generation-pipeline` | `08:00 daily` | gainers 종목 키워드 생성 |
| `extract-daily-news-keywords` | `16:45 daily` | EOD 키워드 추출 |
| `classify-news-batch` | `:15 of 8,10,12,14,16,18 (1-5)` | 3시간 lookback 분류 |
| `analyze-news-deep-batch` | `:30 of 8,10,12,14,16,18 (1-5)` | **max_articles=50** |
| `aggregate-daily-sentiment` | `09:00 1-5` | 일일 집계 |
| `thesis-generate-summaries` | `18:35 1-5` | 가설별 AI 요약 |
| `enrich-relationship-keywords` | `05:30 daily` | `limit=100` |
| `extract-news-relations` | `09:00 daily` | 24시간 lookback |
| `chainsight-co-mentions` | `10:00 daily` | 7일 lookback |
| `chainsight-relation-confidence` | `11:00 daily` | confidence 갱신 |
| `refresh-korean-overviews-monthly` | `03:00 day_of_month=1` | S&P 500 한글 개요 (월간 burst) |

**리스크 (RPM)**:
- 🔴 `analyze-news-deep-batch`의 `max_articles=50`는 단일 태스크가 50회 LLM 호출. 15 RPM 제한 안에서 처리하려면 내부에 4초 슬립이 필요. 코드 내부 rate-limiter 부재 시 즉시 quota 초과.
- 🟡 08:30 / 10:30 / 12:30 / 14:30 / 16:30 / 18:30 6연쇄. 직전 :15에 `classify-news-batch`도 LLM이면 15분 안에 분류+분석 모두 처리 필요.
- 🟡 18:30 deep + 18:35 thesis-summaries 5분 간격. summaries가 즉시 시작 시 deep batch와 quota 경쟁.
- 16:45 `extract-daily-news-keywords`는 주석에 "16:30 분석과 충돌 회피로 15분 분산"으로 명시. 양호.

**리스크 (RPD)**:
- 일일 추정 (평일 기준):
  - `analyze-news-deep-batch` × 6 × ~50 = 300
  - `classify-news-batch` × 6 × ~50 = 300
  - `keyword-generation-pipeline` × 1 × ~30 = 30
  - `extract-daily-news-keywords` × 1 × ~50 = 50
  - `aggregate-daily-sentiment` × 1 × ~10 = 10
  - `thesis-generate-summaries` × 1 × ~20 = 20
  - `chainsight-co-mentions` + `relation-confidence` + `extract-news-relations` × ~50 = 150
  - `enrich-relationship-keywords` × 100 = 100
  - **소계 ~960/일**, 한도 1500의 64% (정상범위)
- ⚠️ **매월 1일 03:00**: `refresh-korean-overviews-monthly`가 S&P 500 ~500 종목 LLM 호출 → 단일 일 RPD 1500 초과 위험. 청크 분산 또는 다른 일자에 배치 필요.

### 1.3 Alpha Vantage 의존 태스크

- ✅ 스케줄에 명시적 AV 태스크 없음. 5 calls/min 한도 위반 없음. (AV는 API_request/ 내 ad-hoc 호출만 존재)

### 1.4 FRED / SEC EDGAR

| 태스크 | 스케줄 (ET) | 출처 |
|--------|-------------|------|
| `update-economic-indicators` | `:00 of 6,12,18,22 (1-5)` | FRED |
| `update-economic-calendar` | `01:00 daily` | FRED |
| `sync-supply-chain-batch` | `03:00 day 15` | SEC 10-K |
| `sync-institutional-holdings` | `04:00 day 16` | SEC 13F |
| `sec-check-new-filings` | `06:00 day 1` | SEC EDGAR |
| `sec-sync-dirty-neo4j` | `*/5 minutes` | 내부 DB → Neo4j |

---

## 2. Queue 분석

### 2.1 Neo4j Queue (solo pool, 동시성 1)

| 태스크 | 스케줄 (ET) | 동시성 |
|--------|-------------|--------|
| `sec-sync-dirty-neo4j` | `*/5 24/7` | **288 트리거/일** |
| `neo4j-health-check` | `:00 every 6h` | 4/일 |
| `cleanup-expired-news-relationships` | `04:00 daily` | 1/일 |
| `sync-news-to-neo4j` | `:45 of 8,10,12,14,16,18 (1-5)` | 6/일, max_articles=100 |
| `chainsight-sync-profiles-neo4j` | `12:00 daily` | |
| `chainsight-sync-relations-neo4j` | `12:30 daily` | |
| `enrich-relationship-keywords` | `05:30 daily` | limit=100 |
| `chainsight-neo4j-dirty-sync` | `04:30 Sun` | |

**리스크**:
- 🔴 solo pool은 fork 없이 1개 동시 처리. `sec-sync-dirty-neo4j`가 5분 주기인데 처리 시간이 5분을 넘으면 큐가 즉시 누적.
- 🟡 **12:00–12:45 ET 윈도우 폭주**: `sec-sync-dirty(:00, :05, :10, ...)` + `chainsight-sync-profiles(12:00)` + `chainsight-sync-relations(12:30)` + `sync-news-to-neo4j(12:45)`. 만약 chainsight-sync-profiles가 5분 초과하면 `sec-sync-dirty-neo4j 12:05` 트리거가 expires=240(4분) 안에 시작 못해 만료 폐기. **데이터 손실 위험**.
- 🟡 04:00 cleanup + 04:30 chainsight-neo4j-dirty-sync(Sun) 인접. cleanup이 30분 초과 시 dirty-sync 시작 지연.

### 2.2 Default Queue

- 장중(9–16) 폴링: `refresh-market-pulse-cache` 매분(60/시간) + `update-realtime-prices` */5 + `update-market-indices` */5 + `calculate-portfolio-values` */10 + `check-screener-alerts` */15 = **시간당 94 트리거**.
- 18:30 ET 슈퍼피크에 4개 태스크 동시(아래 §4).
- macOS 환경: `worker_pool='solo'` 강제 (라인 30–31) → **개발 환경에선 default도 solo 1동시**. 프로덕션(Linux)은 prefork 기본값으로 동시 처리.

---

## 3. 시간대별 ASCII 히트맵 (평일 기준, ET)

각 시간대 정각~다음 정각 사이 **트리거되는 태스크 발사 횟수** (market-hours `*/5` 등 폴링 포함).

```
시각   횟수  히트맵 (■=5건)                                            주요 태스크
00 ET    14  ■■                                                          sec-sync(*/5)+pipeline-alerts(*/30)
01 ET    15  ■■■                                                         + update-economic-calendar
02 ET    14  ■■                                                          baseline (월간/주간 태스크는 조건부)
03 ET    14  ■■                                                          (월간: refresh-korean-overviews, supply-chain)
04 ET    15  ■■■                                                         + cleanup-expired-news-relationships
05 ET    15  ■■■                                                         + enrich-relationship-keywords(05:30)
06 ET    18  ■■■■                                                        + daily-news-morning, high-morning(06:30), sp500-news-0615, general-news-morning(06:45)
07 ET    20  ■■■■                                                        + medium-morning, low(07:30), market-movers(07:30), press-releases(07:45), heat-score, error-digest
08 ET    19  ■■■■                                                        + keyword-pipeline, market-news-morning, classify(:15), deep(:30), sync-news-neo4j(:45)
09 ET   122  ■■■■■■■■■■■■■■■■■■■■■■■■■                                   장중 폴링(94) + aggregate-sentiment + extract-news-relations  ⚠️피크
10 ET   113  ■■■■■■■■■■■■■■■■■■■■■■■                                     장중 폴링(94) + co-mentions + sp500-news-1015 + classify/deep/sync-neo
11 ET   109  ■■■■■■■■■■■■■■■■■■■■■■                                      장중 폴링(94) + relation-confidence
12 ET   117  ■■■■■■■■■■■■■■■■■■■■■■■                                     장중 폴링(94) + market-news-noon + econ-indicators + sync-profiles-neo + sec-seed-relations + classify(:15) + general-news-noon(:30) + sync-relations-neo(:30) + deep(:30) + sync-news-neo(:45)  ⚠️Neo4j 폭주
13 ET   111  ■■■■■■■■■■■■■■■■■■■■■■                                      장중 폴링(94) + high-midday + seed-selection + sp500-news-1315
14 ET   112  ■■■■■■■■■■■■■■■■■■■■■■                                      장중 폴링(94) + daily-news-afternoon(:30) + medium-afternoon + classify(:15) + deep(:30)
15 ET   111  ■■■■■■■■■■■■■■■■■■■■■■                                      장중 폴링(94) + market-news-afternoon + sp500-news-1515(:15)
16 ET   113  ■■■■■■■■■■■■■■■■■■■■■■■                                     장중 폴링(94, 16시 inclusive) + classify(:15) + market-breadth(:30) + sector-heatmap(:35) + deep(:30) + extract-daily-keywords(:45)
17 ET    18  ■■■■                                                        + high-evening + daily-prices + sp500-news-1715(:15) + general-news-evening(:45)
18 ET    26  ■■■■■                                                       market-news-evening + econ-indicators + thesis-update + sp500-eod + classify(:15) + thesis-calc(:15) + deep(:30) + run-eod(:30) + thesis-snapshots(:30) + change-percent(:30) + thesis-summaries(:35) + sync-news-neo(:45)  ⚠️배치 슈퍼피크
19 ET    16  ■■■                                                         + ml-labels + backfill-accuracy
20 ET    15  ■■■                                                         + sp500-financials
21 ET    14  ■■                                                          baseline
22 ET    15  ■■■                                                         + econ-indicators
23 ET    14  ■■                                                          baseline
```

**해설**:
- 09–16 ET 구간은 장중 폴링(`refresh-market-pulse-cache` 매분 60회 포함)이 trigger 수를 압도. 실제 부하는 폴링이 가벼우므로 다른 시간대보다 위험하진 않음.
- **18 ET는 폴링 없는데도 12개 distinct 태스크 동시 발사** → 진짜 부하 피크. 30분 의존성 체인까지 겹쳐 가장 위험.
- 12 ET는 Neo4j 큐 4개 + sec-sync */5 가 한 시간대에 응축. solo pool로 처리 못 따라가면 즉시 drift.

---

## 4. 18 ET 슈퍼피크 상세 (P0)

```
18:00 ET ─┬─ thesis-update-readings           (FMP, 지표 데이터)
          ├─ sync-sp500-eod-prices            (FMP, S&P 500 EOD)
          ├─ update-economic-indicators       (FRED)
          ├─ collect-market-news-evening      (뉴스)
          │
18:15 ET ─┬─ classify-news-batch              (Gemini, 3h lookback)
          └─ thesis-calculate-scores          (DB 연산, ⚠️thesis-update의 18:00 결과 의존)
          │
18:30 ET ─┬─ analyze-news-deep-batch          (Gemini, max=50)
          ├─ run-eod-pipeline                 (⚠️sync-sp500-eod-prices의 18:00 결과 의존)
          ├─ thesis-create-snapshots          (⚠️thesis-calculate의 18:15 결과 의존)
          └─ update-sp500-change-percent      (DB 연산, sync-sp500-eod 의존)
          │
18:35 ET ─┬─ thesis-generate-summaries        (Gemini, ⚠️thesis-snapshots 5분 후)
          │
18:45 ET ─┬─ sync-news-to-neo4j               (Neo4j, max=100)
```

**의존성 위험**:
1. `sync-sp500-eod-prices(18:00)` → `run-eod-pipeline(18:30)` / `update-sp500-change-percent(18:30)`: **30분 갭**. S&P 500 500종목 EOD가 30분 안에 안 끝나면 후속 태스크가 stale 데이터로 실행.
2. `thesis-update-readings(18:00)` → `thesis-calculate-scores(18:15)`: **15분 갭**. 지표가 FMP 응답 지연으로 늦으면 score 계산이 빈 readings 위에 동작.
3. `thesis-create-snapshots(18:30)` → `thesis-generate-summaries(18:35)`: **5분 갭**. summary는 LLM 호출이므로 snapshot 직후 시작 시 양쪽 Gemini quota 경쟁 (deep batch 18:30도 동시 진행 중).
4. **`analyze-news-deep-batch(18:30)` + `thesis-generate-summaries(18:35)` 동시 Gemini quota 경쟁**.

**완화 권장**:
- `run-eod-pipeline` 시작 전 `sync-sp500-eod-prices` 완료 검증 가드 추가 (Chord/Group).
- `thesis-generate-summaries` 18:35 → 18:50 또는 19:00으로 이동 (deep batch와 분리).

---

## 5. 12 ET Neo4j 폭주 상세 (P1)

```
12:00 ET ─┬─ chainsight-sync-profiles-neo4j     (neo4j queue, solo)
          ├─ sec-seed-relations-to-chainsight   (default)
          ├─ collect-market-news-noon           (default)
          ├─ update-economic-indicators         (default)
          └─ sec-sync-dirty-neo4j(*/5)          (neo4j queue)
12:05 ET ─── sec-sync-dirty-neo4j               (neo4j queue, ⚠️solo pool 대기)
12:10 ET ─── sec-sync-dirty-neo4j               (expires=240s → 미실행 시 폐기)
12:15 ET ─┬─ classify-news-batch                (Gemini)
          └─ sec-sync-dirty-neo4j
12:30 ET ─┬─ chainsight-sync-relations-neo4j    (neo4j queue, solo)
          ├─ collect-general-news-fmp-noon
          ├─ analyze-news-deep-batch            (Gemini)
          └─ sec-sync-dirty-neo4j
12:45 ET ─┬─ sync-news-to-neo4j                 (neo4j queue, max=100)
          └─ sec-sync-dirty-neo4j
```

**리스크**:
- Neo4j queue (solo)에 12:00 직후 `chainsight-sync-profiles-neo4j` 처리 중이면 `sec-sync-dirty-neo4j(12:05)`가 큐 대기. `expires: 240s`(4분)이라 처리 못 받으면 **만료 폐기 → SEC dirty evidence 손실**.
- `chainsight-sync-relations-neo4j(12:30)` + `sync-news-to-neo4j(12:45)` + `sec-sync-dirty(every 5min)` 누적 — 13:00까지 queue depth 위험.

**완화 권장**:
- `sec-sync-dirty-neo4j`의 `expires`를 240 → 600 또는 1200으로 확대.
- 또는 chainsight-sync-profiles/relations를 default queue로 분리(다만 Neo4j 동시 쓰기 → race condition 위험. lock 전제 시에만).

---

## 6. 주말/월간 배치 의존성 체인

### 6.1 토요일 02:00–05:00 ET (Chain Sight + Validation 체인)

```
02:00 chainsight-all-profiles               (expires=2h)
03:00 chainsight-price-co-movement          (expires=2h, ⚠️profiles 결과 의존)
04:00 chainsight-stale-decay                (expires=10min)
04:30 chainsight-aggregate-profiles         (expires=1h, ⚠️profiles+relations 의존)
05:00 validation-weekly-batch               (expires=4h, ⚠️chainsight 후행)
```

- `chainsight-all-profiles`가 1시간 초과 시 03:00 price-co-movement가 동시 실행되며 같은 테이블 갱신 → 데이터 경합.
- `chainsight-stale-decay(04:00)`의 `expires=600`(10분)은 직전 작업 지연 시 즉시 폐기됨.

### 6.2 일요일 03:00–05:00 ET (ML 학습 체인)

```
03:00 train-importance-model                (expires=2h)
03:30 generate-shadow-report                (expires=1h, ⚠️train 결과 의존)
04:00 check-auto-deploy                     (expires=1h)
04:15 generate-weekly-ml-report             (expires=1h)
04:20 monitor-ml-performance                (expires=1h)
04:30 train-lightgbm-model                  (expires=2h)
04:30 chainsight-neo4j-dirty-sync           (neo4j queue, ⚠️동시 발사)
05:00 cleanup-task-results
```

- 04:30 정각 동시 발사 2건 (다른 queue라 큐 격리는 OK).
- ML 학습은 메모리·CPU 집중 → 동시에 Neo4j sync 돌면 시스템 부하 spike.

### 6.3 매월 1일 02:00–06:00 ET (월간 burst)

```
02:00 sync-sp500-constituents
02:30 archive-old-articles
03:00 refresh-korean-overviews-monthly       (⚠️Gemini 일일 RPD 1500 위협)
04:30 build-patent-network
06:00 sec-check-new-filings
```

- ⚠️ `refresh-korean-overviews-monthly`가 S&P 500 ~500개 종목을 한번에 LLM 호출 시 일일 RPD 1500 초과 가능. 청크 분산 / 다중 일자 배치 권장.

---

## 7. DST / TZ 일관성 이슈 (P1)

`CELERY_TIMEZONE = 'America/New_York'`이므로 모든 `crontab(hour=N)`은 ET 기준 자동 DST 적용. 하지만 코드 주석에서 TZ 표기가 혼재:

| 태스크 | 주석 표기 | 실제 (ET) | 일치 여부 |
|--------|----------|----------|----------|
| `chainsight-heat-score-daily` | "매일 07:00 UTC" | ET 07:00 = UTC 11:00 (EST) / 12:00 (EDT) | ❌ 주석 오류 |
| `chainsight-seed-selection` | "매일 13:00 UTC" | ET 13:00 = UTC 17:00 / 18:00 | ❌ 주석 오류 |
| `chainsight-neo4j-dirty-sync` | "매주 일요일 04:30 UTC" | ET 04:30 일요일 | ❌ 주석 오류 |
| 그 외 다수 | "EST" / "ET" | ET | ✅ |

**리스크**: 운영자가 주석을 신뢰하면 UTC 기준 시점에 모니터링이 비어 보일 수 있음. 주석을 ET로 통일 권장.

---

## 8. 의존성 그래프 요약 (선후행이 분리된 태스크)

| 선행 | 후행 | 갭 | 위험 |
|------|------|----|------|
| `sync-sp500-eod-prices(18:00)` | `run-eod-pipeline(18:30)` | 30m | 🔴 P0 — 500종목 sync 미완료 시 빈 데이터 |
| `sync-sp500-eod-prices(18:00)` | `update-sp500-change-percent(18:30)` | 30m | 🟡 P1 — DailyPrice 갱신 의존 |
| `thesis-update-readings(18:00)` | `thesis-calculate-scores(18:15)` | 15m | 🟡 P1 |
| `thesis-calculate-scores(18:15)` | `thesis-create-snapshots(18:30)` | 15m | 🟡 P1 |
| `thesis-create-snapshots(18:30)` | `thesis-generate-summaries(18:35)` | 5m | 🟡 P1 — LLM 큐잉 직후 |
| `classify-news-batch(:15)` | `analyze-news-deep-batch(:30)` | 15m | 🟡 P1 — 매 2시간 6연쇄 |
| `analyze-news-deep-batch(:30)` | `sync-news-to-neo4j(:45)` | 15m | 🟢 — 비교적 안전 |
| `collect-daily-news-morning(06:00)` | `aggregate-daily-sentiment(09:00)` | 3h | 🟢 — 여유 |
| `chainsight-all-profiles(Sat 02:00)` | `chainsight-aggregate-profiles(Sat 04:30)` | 2.5h | 🟡 — `expires=2h`라 profiles가 2h 초과 시 만료 폐기 |
| `chainsight-co-mentions(10:00)` | `chainsight-relation-confidence(11:00)` | 1h | 🟢 |
| `chainsight-sync-profiles-neo4j(12:00)` | `chainsight-sync-relations-neo4j(12:30)` | 30m | 🟡 — Neo4j solo queue 적체 시 |
| `train-importance-model(Sun 03:00)` | `generate-shadow-report(Sun 03:30)` | 30m | 🟡 — `expires=2h` 학습 길어지면 위험 |

---

## 9. 권장 액션 (우선순위)

### P0 (즉시)
1. **`run-eod-pipeline` 시작 가드**: `sync-sp500-eod-prices` 완료 확인 후 진행 (Celery `chain()` 또는 DB 마커 폴링).
2. **`analyze-news-deep-batch` 내부 rate-limiter 검증**: 50 articles × Gemini 호출이 15 RPM을 초과하지 않도록 코드 레벨 확인 → 미존재 시 4초 슬립 추가.
3. **`refresh-korean-overviews-monthly`**: 500종목 Gemini 호출을 5–7일에 청크 분산.

### P1 (이번 주)
4. **`sec-sync-dirty-neo4j` `expires`** 240 → 600s 또는 1200s 확대.
5. **`thesis-generate-summaries`를 18:35 → 18:50**로 분리하여 deep batch와 Gemini quota 경쟁 해소.
6. **`chainsight-stale-decay` `expires`** 600 → 1800s 확대.
7. **주석 TZ 통일**: "UTC" → "ET" (실제 동작 시각 기준).

### P2 (이번 분기)
8. **장중 폴링 통합**: `refresh-market-pulse-cache` 매분 + `update-realtime-prices` */5 + `update-market-indices` */5를 단일 orchestrator로 통합해 FMP burst 평탄화.
9. **dict ↔ DB drift 정기 검증**: `PROGRESS.md`에 주간 점검 항목 추가 (`python manage.py shell`로 diff).

---

## 10. 참고

- 진실의 소스는 `django_celery_beat.PeriodicTask` DB 테이블. 본 보고서는 `config/celery.py` dict 기준이므로 DB와 drift 가능성 존재 (라인 117–134 주석 참조).
- 일부 태스크의 `kwargs`/`args`는 dict에 명시되어 있으나 DB에 등록 시 JSON 직렬화 형식이 다를 수 있음.
- 평일/주말 분기는 `day_of_week='1-5'` 명시된 경우만 추적했으며, 일부 daily 태스크(예: `extract-news-relations`)는 주말에도 발사됨.

— end of audit
