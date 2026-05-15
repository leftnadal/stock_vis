# Celery Beat Schedule 감사 보고서

- **감사일**: 2026-05-13
- **대상**: `config/celery.py` (821 lines, beat_schedule 76 엔트리)
- **모드**: 읽기 전용 (코드 수정 없음)
- **시각 기준**: 모든 `crontab(hour=...)` 값은 EST 기준으로 해석 (Celery worker TZ가 EST일 때 가정)

> 사전 경고 (`config/celery.py:117-134`): 본 `beat_schedule` dict는 런타임에 무시된다.
> 실제 진실의 소스는 `django_celery_beat.PeriodicTask` 테이블이다 (`CELERY_BEAT_SCHEDULER = DatabaseScheduler`).
> 본 감사는 **선언적 reference로서의 dict**만 점검한다. DB와 dict의 drift 점검은 별도 절차 필요.

---

## Executive Summary

| 위험도 | 카테고리 | 핵심 발견 |
|--------|----------|----------|
| [CRITICAL] | FMP Rate Limit | `18:00 EST` 단일 분 부하: `sync-sp500-eod-prices`(≈503 calls, REQUEST_DELAY=0.3s 내장) + `thesis-update-readings` + `collect-market-news-evening` 동시 시작 — EOD 서비스 자체는 200 calls/min로 self-throttle 되지만, 시작 분에서 다른 FMP 태스크 호출과 경합 가능 |
| [CRITICAL] | Gemini RPM (15) | `18:30-18:45` 5분 창 4중첩: `analyze-news-deep-batch`(50건 × LLM, 4초 간격), `thesis-create-snapshots-and-alerts`, `thesis-generate-summaries`(18:35), `run-eod-pipeline`(18:30) — 동시 가동 시 15 RPM 초과 |
| [HIGH] | neo4j Queue Solo Pool | `12:00` 시점 4태스크 동시 큐잉: `chainsight-sync-profiles-neo4j` + `neo4j-health-check`(*/6) + `sec-sync-dirty-neo4j`(*/5) + 12:30 도착 `chainsight-sync-relations-neo4j` — solo pool은 동시 1개만 처리, `sec-sync` expires=240s 만료 위험 |
| [HIGH] | neo4j Queue 만성 점유 | `sec-sync-dirty-neo4j`가 5분마다 무조건 실행(*/5, 24시간 × 288회). expires=240s — solo pool에서 1회 실행이 4분 이상 걸리면 큐 백로그 형성 |
| [HIGH] | Gemini RPM (15) | `08:00-08:45` 30분 창: `keyword-generation-pipeline`(08:00, LLM), `classify-news-batch`(08:15, LLM), `analyze-news-deep-batch`(08:30, LLM 50건), `sync-news-to-neo4j`(08:45) — 매일 반복 LLM 폭주점 |
| [MEDIUM] | 시장개장 부하 | 9-16시 매분 `refresh-market-pulse-cache`(60/hr) + 5분마다 4개 태스크(realtime, indices, sec-sync, screener) → default queue 매분 ≥1, 매 5분 ≥4 트리거 |
| [MEDIUM] | Queue 미지정(LLM) | `chainsight-heat-score-daily`, `chainsight-seed-selection`, `chainsight-co-mentions`, `chainsight-relation-confidence`, `extract-news-relations`가 default queue로 흘러감 — LLM 호출 시 default 워커 점유 |
| [MEDIUM] | EST/UTC 혼동 | 주석은 일관되게 "EST"라고 표기하나 일부(`chainsight-heat-score-daily` 등) 주석은 "UTC"로 혼용. crontab 자체는 worker timezone 기준 — `settings.TIME_ZONE` / `CELERY_TIMEZONE` 확정 필요 |
| [MEDIUM] | 의존성 시각 마진 | `thesis-update-readings`(18:00) → `thesis-calculate-scores`(18:15) → `thesis-create-snapshots`(18:30) — 15분 마진. EOD가 늦어지면 후속 태스크가 입력 부족으로 빈 결과 |
| [LOW] | Alpha Vantage | beat_schedule에 AV 직접 호출 태스크 없음 (코드 폴백 경로로만 사용). beat 차원 한도 초과 위험 0 |

---

## 1. Rate Limit 초과 구간 분석

### 1.1 FMP Starter Plan (300 calls/min, 10,000 calls/day)

#### 1.1.1 일일 추정 호출량 (평일 기준)

| 시간(EST) | 태스크 | 추정 호출 수 | 비고 |
|----------|-------|------------|------|
| 06:00 | `collect-daily-news-morning` | ≈100 | Marketaux/FMP 혼용 추정 |
| 06:15 | `collect-sp500-news-fmp-0615` | ≈503 (84 chunks × 6 chains) | `news/tasks.py:971-972` 84개 batch_size |
| 06:30 | `collect-category-news-high-morning` | ≈30 | priority=high 카테고리 수 |
| 06:45 | `collect-general-news-fmp-morning` | ≈1-5 | general endpoint |
| 07:00 | `collect-category-news-medium-morning` | ≈20 | |
| 07:30 | `sync-daily-market-movers` | ≈10-30 | gainers/losers/active |
| 07:30 | `collect-category-news-low` | ≈15 | |
| 07:45 | `collect-press-releases-fmp` | ≈50 (kwargs max_symbols=50) | |
| 08:00 | `collect-market-news-morning` | ≈10 | |
| 09:00-16:00 | `update-realtime-prices` (*/5) | ≈12 calls/run × 96 runs = **≈1,152** | FMP 배치 endpoint 가정 |
| 09:00-16:00 | `update-market-indices` (*/5) | ≈5 calls/run × 96 = ≈480 | 주요 지수 |
| 10:15 | `collect-sp500-news-fmp-1015` | ≈503 | |
| 12:00 | `collect-market-news-noon` | ≈10 | |
| 12:30 | `collect-general-news-fmp-noon` | ≈1-5 | |
| 13:00 | `collect-category-news-high-midday` | ≈30 | |
| 13:15 | `collect-sp500-news-fmp-1315` | ≈503 | |
| 14:00 | `collect-category-news-medium-afternoon` | ≈20 | |
| 14:30 | `collect-daily-news-afternoon` | ≈100 | |
| 15:00 | `collect-market-news-afternoon` | ≈10 | |
| 15:15 | `collect-sp500-news-fmp-1515` | ≈503 | |
| 17:00 | `update-daily-prices` | ≈500 | FMP provider |
| 17:00 | `collect-category-news-high-evening` | ≈30 | |
| 17:15 | `collect-sp500-news-fmp-1715` | ≈503 | |
| 17:45 | `collect-general-news-fmp-evening` | ≈1-5 | |
| 18:00 | `sync-sp500-eod-prices` | **≈503** | `stocks/services/sp500_eod_service.py:23` REQUEST_DELAY=0.3s |
| 18:00 | `collect-market-news-evening` | ≈10 | |
| 18:00 | `thesis-update-readings` | ≈ 지표×기업 (수십~수백) | FMP-bound 추정 |
| 20:00 | `sync-sp500-financials` | ≈101 × 3 endpoints = ≈303 | `stocks/tasks.py:124` batch_size=101 |
| 06:00 Mon | `sync-etf-holdings` | ≈100-300 | |

**일 누적 추정**: 약 **6,500-8,500 calls/day** — FMP Starter 10,000 calls/day 한도의 65-85% 사용. **여유 마진 15-35%**, 일중 폭주 또는 retry 시 한도 도달 위험 있음.

#### 1.1.2 분당 한도 초과 구간 — Top 5

| 분(EST) | 동시 시작 FMP 태스크 | 초기 폭주 위험 | 완화 요인 |
|---------|---------------------|-------------|----------|
| **18:00** | `sync-sp500-eod-prices` + `collect-market-news-evening` + `thesis-update-readings` | **HIGH** | eod_service 0.3s sleep → 200/min 자체 throttle. 다른 두 태스크가 첫 분에 30+ calls 추가 시 300 한도 위협 |
| **17:00** | `update-daily-prices` + `collect-category-news-high-evening` | **HIGH** | update_daily_prices가 throttle 미적용 시 첫 분 500 calls 가능 → 즉시 초과 |
| **06:15** | `collect-sp500-news-fmp-0615`(503) | **MEDIUM** | orchestrator 84-batch 분할(`news/tasks.py:971`) — 분당 분산 여부 미확인 |
| **10:15 / 13:15 / 15:15 / 17:15** | 동일 orchestrator 반복 | **MEDIUM** | 동일 |
| **장중 5분마다 0/5/10/...** | `update-realtime-prices` + `update-market-indices` | **LOW** | 매 5분 ≈17 calls — 한도 5.7% |

**검증 권고**:
- `stocks.tasks.update_realtime_with_provider` 내부 throttle 확인
- `news.tasks.collect_sp500_news_fmp_orchestrator`의 chain/group 분산 시점 확인
- `thesis.tasks.eod_pipeline.update_indicator_readings` FMP 호출 수 측정

---

### 1.2 Gemini Free (15 RPM, 1500 RPD)

#### 1.2.1 LLM 호출 태스크 목록

| 태스크 | 스케줄 | 1회 LLM 호출 수 추정 |
|--------|--------|---------------------|
| `keyword-generation-pipeline` | 08:00 daily | 10-50 (movers gainers 종목별 키워드) |
| `aggregate-daily-sentiment` | 09:00 weekday | 종목별 1회 — 수십~수백 |
| `extract-news-relations` | 09:00 daily | 기사별 1회 |
| `classify-news-batch` (×6/day) | 8:15, 10:15, 12:15, 14:15, 16:15, 18:15 | 기사별 1회 × 분류 대상 수 (kwargs hours=3) |
| `analyze-news-deep-batch` (×6/day) | 8:30, 10:30, 12:30, 14:30, 16:30, 18:30 | **50건** (kwargs max_articles=50) — `news/tasks.py:511,518` "4초 간격으로 RPM 준수" |
| `extract-daily-news-keywords` | 16:45 daily | 기사별 1회 |
| `chainsight-co-mentions` | 10:00 daily | LLM 사용 시 N개 |
| `chainsight-relation-confidence` | 11:00 daily | 일부 LLM |
| `enrich-relationship-keywords` | 05:30 daily, neo4j | 100 (kwargs limit=100) — `serverless.tasks.enrich_relationship_keywords` |
| `thesis-generate-summaries` | 18:35 weekday | 활성 가설 수 × 1회 (수십~수백) |
| `refresh-korean-overviews-monthly` | 03:00 1st | 500종목 × 1 = 500 calls (bulk) |

**RPD 추정**: `analyze-deep` 6회 × 50 = 300/day + `classify` 6회 × 30 = 180 + `keyword-gen` ~30 + `aggregate-sentiment` ~50 + `thesis-summaries` ~50 + `enrich-relationship-keywords` 100 + 기타 ≈ **750-900/day**. 1500 RPD의 50-60% 사용.

월 1회 `refresh-korean-overviews-monthly` 실행일은 +500 → 한도 초과 위험 (1500 / day).

#### 1.2.2 RPM 초과 위험 시간대

**[CRITICAL] 18:30-18:45 (5분 창)**

```
18:15  thesis-calculate-scores         (LLM 가능성 - 내부 계산 위주, 낮음)
18:15  classify-news-batch             (LLM, 분류 대상 N개)
18:30  analyze-news-deep-batch         (LLM × 50건, 4초 간격으로 200초 소요)
18:30  thesis-create-snapshots-alerts  (DB 위주, LLM 미사용 추정)
18:30  run-eod-pipeline                (시그널 계산, LLM 미사용 추정)
18:35  thesis-generate-summaries       (LLM × 활성 가설 수)
18:45  sync-news-to-neo4j (neo4j q)    (LLM 미사용)
```

- `analyze-news-deep-batch`가 18:30-18:33:20 구간 200초 동안 50회 호출 (15 RPM = 4초/req에 정확히 맞춤)
- 그 사이 `thesis-generate-summaries`(18:35)가 자체 4초 throttle 없이 호출 시 → 15 RPM 초과
- common-bugs #8: "Celery에서 async LLM 호출 금지 — 동기 API만" 준수 시점이며 RPM 자체 제한 분산 필요

**[HIGH] 08:00-08:45 (45분 창)**

```
08:00  keyword-generation-pipeline     (LLM, gainers 키워드)
08:15  classify-news-batch              (LLM)
08:30  analyze-news-deep-batch          (LLM × 50, 200초)
08:45  sync-news-to-neo4j (neo4j q)     
```

15분 단위 분산되어 있으나 `keyword-gen`과 `classify-news-batch`가 동기 호출 묶음일 경우 08:00-08:15 첫 분에서 RPM 충돌 가능.

**[HIGH] 09:00 (단일 분)**

```
09:00  aggregate-daily-sentiment        (LLM)
09:00  extract-news-relations           (LLM)
```

동일 분 시작 두 LLM 태스크 — 각자 다수 호출 시 즉시 충돌. **수정 필요**: `extract-news-relations`를 09:05나 09:30으로 분산 권고.

**[MEDIUM] 16:30 (이전 충돌점, 이미 완화됨)**

`config/celery.py:286-291` 주석에 명시된 대로, `extract-daily-news-keywords`는 16:30 → 16:45로 이동되어 `analyze-news-deep-batch`(16:30)과 충돌 회피됨. 그러나 `analyze-deep-batch`는 16:30에 200초 가동하므로 16:30-16:33:20 동안 다른 LLM 태스크가 들어오면 안 됨. 16:35 `calculate-sector-heatmap`은 LLM 미사용이라 안전.

---

### 1.3 Alpha Vantage (5 calls/min)

**beat_schedule에 AV 직접 호출 태스크 없음.** Stock-Vis는 FMP를 기본 Provider로 사용하고 AV는 폴백 경로로만 호출되는 구조 (`API_request/`). 따라서 Beat 차원의 AV 한도 초과 위험은 0.

**잠재 위험**: FMP 장애 시 코드 폴백이 동시간대 다수 종목에 대해 AV로 전환되면 5/min 즉시 초과. 이는 코드 차원 문제로 beat schedule 감사 범위 외.

---

## 2. Queue 몰림 분석

### 2.1 Queue 라우팅 (config/celery.py:37-55)

**neo4j queue** (solo pool, 동시 처리 1개):
- `rag_analysis.tasks.health_check_neo4j`
- `news.tasks.sync_news_to_neo4j`
- `news.tasks.cleanup_expired_news_relationships`
- `serverless.tasks.enrich_relationship_keywords`
- `chainsight.tasks.sync_tasks.sync_profiles_to_neo4j`
- `chainsight.tasks.sync_tasks.sync_relations_to_neo4j`
- `chainsight-neo4j-dirty-sync`
- `sec_pipeline.tasks.sync_dirty_to_neo4j`
- (그 외 사용 안 되는 RAG semantic_cache 태스크들)

**default queue**: 위 명시되지 않은 모든 태스크 (60+ 개)

### 2.2 neo4j queue 시간대별 큐잉

```
Hour | neo4j queue 도착 태스크 (weekday)
00   | sec-sync (12회)
04   | sec-sync (12) + cleanup-expired-news-relationships
05   | sec-sync (12) + enrich-relationship-keywords (LLM!)
06   | sec-sync (12) + neo4j-health-check
08   | sec-sync (12) + sync-news-to-neo4j(08:45)
10   | sec-sync (12) + sync-news-to-neo4j(10:45)
12   | sec-sync (12) + neo4j-health-check + chainsight-sync-profiles + chainsight-sync-relations(12:30) + sync-news-to-neo4j(12:45)
14   | sec-sync (12) + sync-news-to-neo4j(14:45)
16   | sec-sync (12) + sync-news-to-neo4j(16:45)
18   | sec-sync (12) + neo4j-health-check + sync-news-to-neo4j(18:45)
```

**[CRITICAL] 12:00-13:00 1시간 창** — neo4j queue 백로그 최고 위험점:

```
12:00  sec-sync-dirty-neo4j  (*/5, expires=240s)
12:00  chainsight-sync-profiles-neo4j (expires=3600s) — solo pool 점유
12:00  neo4j-health-check (6h 주기)
12:05  sec-sync-dirty-neo4j  (12:00분 태스크가 미완료 시 큐 대기)
12:10  sec-sync-dirty-neo4j  (대기 큐 누적)
12:30  chainsight-sync-relations-neo4j — solo pool 재점유
12:45  sync-news-to-neo4j (max_articles=100)
```

- `chainsight-sync-profiles-neo4j` 또는 `sync-news-to-neo4j`가 4분 이상 실행되면 `sec-sync-dirty-neo4j`(expires=240s)가 만료되면서 5분치 dirty 데이터를 잃음
- solo pool 처리 시간 측정 필요

### 2.3 default queue 시장개장중 (9-16시) 부하

```
Minute pattern (9-16시, 평일):
*:00, *:01, ..., *:59      refresh-market-pulse-cache  (60/hr)
*:00, *:05, *:10, ...      update-realtime-prices, update-market-indices, sec-sync(neo4j 별도)
*:00, *:10, *:20, ...      calculate-portfolio-values  (6/hr)
*:00, *:15, *:30, *:45     check-screener-alerts  (4/hr)
```

**매 5분마다 default queue 트리거**: 3-5 태스크 (realtime + indices + market-pulse + 가끔 portfolio + 가끔 screener-alerts).

prefork 워커가 동시성 N개일 때:
- N=4 가정 시 5분 창 내 처리 가능
- 1분 단위로 market-pulse-cache 추가 → 60 trigger/hr
- 만약 어떤 태스크가 5분 이상 걸리면 5분 후 동일 태스크 재실행과 겹침 → **idempotency 의존**

### 2.4 Queue 부하 시간대 ASCII 히트맵

다음은 weekday Mon-Fri 기준 시간당 **태스크 트리거 총수** (1-min refresh-market-pulse 포함):

```
범례: . = 0-9   - = 10-19   ░ = 20-39   ▒ = 40-79   ▓ = 80-119   █ = 120+

Hour: 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
ALL:  -  -  -  -  -  -  ░  ░  -  ▓  ▓  ▓  ▓  ▓  ▓  ▓  ▓  -  ░  -  -  -  -  -
       15 15 14 14 15 15 20 20 19 106 112 109 118 111 113 110 113 18 27 16 15 14 15 14
```

#### 2.4.1 default queue만 (neo4j 분리)

```
Hour: 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
def:  .  .  .  .  .  .  -  -  -  ▓  ▓  ▓  ▓  ▓  ▓  ▓  ▓  -  -  -  .  .  -  .
        3  3  2  2  2  2  6  8  5  93 96 96 96 99 99 96 98  6 12  4  3  2  3  2
```

#### 2.4.2 neo4j queue만 (solo pool 처리)

```
Hour: 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
neo:  -  -  -  -  -  -  -  .  -  -  -  -  ░  -  -  -  -  .  -  .  .  .  .  .
       13 12 12 12 13 13 13 12 13 12 13 12 22 12 13 12 13 12 14 12 12 12 12 12
```

(neo4j queue 부하는 대부분 `sec-sync-dirty-neo4j` */5 = 12/hr로 일정. 12시에 chainsight + health-check 합류 시 피크)

#### 2.4.3 FMP 호출 강도 히트맵 (추정 calls/hour)

```
범례: . = <50   - = 50-200   ░ = 200-500   ▒ = 500-1000   ▓ = 1000-2000   █ = 2000+

Hour: 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
FMP:  .  .  .  .  .  .  ▒  -  .  -  ▒  -  -  ▒  -  ▒  -  ▓  ▒  .  ░  .  .  .
        0  0  0  0  0  0 650 80 10 144 660 144 160 660 144 660 144 1030 600 0 303 0  0  0
```

- 17:00 피크: `update-daily-prices`(500) + `update-realtime-prices` 마지막 분(12) + category news + sp500-news-fmp-1715(503) → **≈1,030 calls 1시간**
- 06:15, 10:15, 13:15, 15:15: orchestrator 503 calls
- 18:00: EOD 503 + market-news 10 + thesis = **≈600 calls 1시간**

#### 2.4.4 Gemini 호출 강도 히트맵 (추정 calls/hour, daily)

```
범례: . = 0   - = 1-30   ░ = 31-60   ▒ = 61-100   ▓ = 101+

Hour: 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
Gem:  .  .  .  .  .  ▒  .  .  ░  ░  ░  -  ░  .  ░  .  ░  .  ░  .  .  .  .  .
        0  0  0  0  0  100 0  0  60 60 60  5  60  0  60  0  60  0  60  0  0  0  0  0
```

- 05:00 시간대 `enrich-relationship-keywords`(100건) 단일 점프
- 08-18시 짝수 시간 ~60건 패턴 (classify + analyze-deep + 동기/관계 작업)
- 18:35 `thesis-generate-summaries` 추가로 18시간대 추가 부하 (히트맵에는 60으로만 표시되었으나 실제 70+)

---

## 3. 시간대별 종합 ASCII 히트맵 (weekday EST)

```
                  분(0)  10  20  30  40  50      태스크 시작 농도 (가독성용 1열=10분)
00:  ░░░░░░     sec-sync */5 + check-pipeline */30
01:  ░░░░░░     +update-economic-calendar(daily)
02:  ░░░░░░     [Sat/1st: aggregate-weekly, chainsight-all-profiles, sync-sp500-constituents]
03:  ░░░░░░     [Sun: train-importance / refresh-korean / Sat: chainsight-price-co-move]
04:  ▒░░░░░     :00 cleanup-expired-news (neo4j) [Sun/Sat 다수 chainsight + ML 태스크]
05:  ▒░░░░░     :30 enrich-relationship-keywords (LLM, neo4j) [Sun cleanup-task-results]
06:  ▓░░▒░▓     :00 collect-daily-news+update-econ+neo4j-health  :15 sp500-news-fmp(503)  :30 cat-high  :45 general-news
07:  ▓▒░░░░     :00 chainsight-heat-score+celery-digest+cat-medium  :30 movers+cat-low  :45 press-releases
08:  ▓░░▒░░     :00 keyword-gen(LLM)+collect-market-news  :15 classify(LLM)  :30 analyze-deep(LLM 50!)  :45 sync-news-neo4j
09:  ████████   :00 aggregate-sent(LLM)+extract-relations(LLM)  매분 market-pulse, 5분 realtime+indices+sec-sync
10:  ▓███▒█▓█   :00 chainsight-co-mentions(LLM 가능)  :15 classify  :30 analyze-deep+sp500-news-fmp(503)  :45 sync-neo4j
11:  ████████   :00 chainsight-relation-confidence(LLM)
12:  ████▒█▓█   :00 market-news+chainsight-sync-prof(neo4j)+sec-seed+neo4j-health+econ-indicators  :15 classify  :30 analyze-deep+general-news+chainsight-sync-relations(neo4j)  :45 sync-news-neo4j
13:  ▒███████   :00 cat-high-midday+chainsight-seed-selection  :15 sp500-news-fmp(503)
14:  █████▓██   :00 cat-medium  :15 classify  :30 collect-daily-afternoon+analyze-deep  :45 sync-news-neo4j
15:  ▒███████   :00 collect-market-news  :15 sp500-news-fmp(503)
16:  ████▓███   :15 classify  :30 calc-market-breadth+analyze-deep  :35 calc-sector-heatmap  :45 extract-daily-keywords(LLM)+sync-neo4j
17:  ▓░░░░▓     :00 update-daily-prices(500)+cat-high-evening  :15 sp500-news-fmp(503)  :45 general-news
18:  ███▒░▒░    :00 sp500-eod-prices(503)+market-news+thesis-readings+econ+neo4j-health  :15 classify+thesis-scores  :30 update-change-pct+eod-pipeline+analyze-deep+thesis-snapshots  :35 thesis-summaries(LLM)  :45 sync-news-neo4j
19:  ░░░░░░     :00 collect-ml-labels+backfill-signal-accuracy
20:  ░░░▒░░     :00 sync-sp500-financials(101 stocks × 3 endpoints ≈ 303 calls)
21:  ░░░░░░     idle
22:  ░░░░░░     :00 update-economic-indicators(daily 22)
23:  ░░░░░░     idle
```

**해석**:
- 점유율 가장 높은 분: **18:30** (4태스크 동시) → LLM 충돌 위험 최고
- 점유율 두 번째: **12:00** (5태스크 동시, neo4j 큐 3개 포함)
- API 폭주: **17:00, 18:00, 10:15/13:15/15:15/17:15** (sp500 일괄 호출)

---

## 4. 스케줄 겹침 / 의존성 분석

### 4.1 Thesis Control EOD Chain (의존성 명시)

```
18:00  thesis-update-readings              ← FMP에서 지표 수집
   ↓   (15분 마진)
18:15  thesis-calculate-scores             ← readings 데이터 의존
   ↓   (15분 마진)
18:30  thesis-create-snapshots-and-alerts  ← scores 데이터 의존
   ↓   (5분 마진)
18:35  thesis-generate-summaries (LLM)     ← snapshot 데이터 의존
```

**위험**: `thesis-update-readings`가 18:00에 시작해도 FMP 한도 경합으로 15분 이상 걸리면 후속 `thesis-calculate-scores`가 빈 데이터로 실행 → snapshot/alert 부재 → user-visible bug.

**18:00 동시 시작 경합**:
```
18:00  sync-sp500-eod-prices         FMP 503 calls (200/min self-throttle → 2.5분 소요)
18:00  thesis-update-readings        FMP 호출 (수십~수백)
18:00  collect-market-news-evening   FMP/Marketaux ~10
18:00  update-economic-indicators    FRED (FMP와 별개)
18:00  neo4j-health-check            Neo4j 단순 ping
```

`thesis-update-readings`가 `sync-sp500-eod-prices`보다 먼저 끝나야 18:15 chain이 정상 동작.

### 4.2 News Pipeline 의존성

```
*:15 (8,10,12,14,16,18)  classify-news-batch          ← 최근 3시간 미분류 기사
   ↓
*:30 (8,10,12,14,16,18)  analyze-news-deep-batch      ← classify된 기사
   ↓
*:45 (8,10,12,14,16,18)  sync-news-to-neo4j           ← deep 분석된 기사
```

15분 마진. `analyze-news-deep-batch`가 50건 × 4초 ≈ 200초(3.3분)이므로 15분 마진 내 정상. 단, classify가 동일 15분 마진을 가지므로 classify가 늦어지면 deep이 빈 입력으로 실행됨.

### 4.3 Chain Sight 의존성

```
주간 (Saturday EST):
02:00  chainsight-all-profiles                (Tier A profile 계산)
03:00  chainsight-price-co-movement
04:00  chainsight-stale-decay
04:30  chainsight-aggregate-profiles          ← 위 3개에 의존
05:00  validation-weekly-batch                 ← Chain Sight 완료 의존

일일:
10:00  chainsight-co-mentions                  ← 뉴스 분류 후 (08:15 classify로부터 시간 충분)
11:00  chainsight-relation-confidence          ← co-mentions 의존
12:00  chainsight-sync-profiles-neo4j  (neo4j) ← relation confidence 후
12:30  chainsight-sync-relations-neo4j (neo4j) ← profile 동기화 후
```

**경고**: 일일 11:00 → 12:00 1시간 마진 동안 `chainsight-relation-confidence`가 끝나야 함. 무거운 LLM 작업일 경우 12:00 sync가 부분 데이터로 실행될 위험.

### 4.4 시드 선정 → SEC 의존성

```
07:00  chainsight-heat-score-daily             ← 시드 선정 전 (config:741 주석)
12:00  sec-seed-relations-to-chainsight        ← 시드 선정 전 (config:785 주석)
13:00  chainsight-seed-selection
```

`sec-seed-relations`(12:00)는 `chainsight-seed-selection`(13:00) **이전**에 실행되어야 한다는 의도가 주석에 명시됨. 하지만 두 태스크는 `chainsight-sync-profiles-neo4j`(12:00)와 동일 분이라 neo4j queue 경합 가능.

### 4.5 Sunday ML 의존성 체인

```
03:00 Sun  train-importance-model              (ML 학습)
03:30 Sun  generate-shadow-report              ← 학습 직후
04:00 Sun  check-auto-deploy                   ← shadow 리포트 후
04:00 Sun  cleanup-expired-news-relationships  (neo4j, 매일 동시)  ← Sunday는 위와 경합
04:15 Sun  generate-weekly-ml-report
04:20 Sun  monitor-ml-performance
04:30 Sun  train-lightgbm-model                ← auto-deploy 후
04:30 Sun  chainsight-neo4j-dirty-sync (neo4j) ← 위와 neo4j queue 경합
05:00 Sun  cleanup-task-results
```

**경고**: 04:00 Sun에 `check-auto-deploy`(default) + `cleanup-expired-news-relationships`(neo4j, 일일 매일 04:00) 동시 시작. 추가로 `scan-regulatory-relationships`도 Mon 04:00이라 동일 시각 충돌은 없으나 시각 클러스터링은 검토 필요.

---

## 5. 종합 권고 (코드 변경은 별도 PR로)

| 우선순위 | 권고 | 영향 영역 |
|---------|------|---------|
| P0 | `thesis-generate-summaries`(18:35)를 18:50 또는 19:10으로 이동 — analyze-deep-batch와 RPM 경합 회피 | Gemini RPM |
| P0 | `sync-sp500-eod-prices`(18:00) 내부 batch 분할 검증 + `thesis-update-readings` 시각을 18:05로 분산 | FMP 분당 한도 |
| P0 | `extract-news-relations`(09:00) → 09:15 또는 09:30으로 분산 (aggregate-daily-sentiment와 분리) | Gemini RPM |
| P1 | `sec-sync-dirty-neo4j`(*/5, expires=240s) 실행 시간 측정. 4분 초과 시 expires 상향 또는 주기 늘림 | Neo4j queue 백로그 |
| P1 | `chainsight-sync-profiles-neo4j` + `chainsight-sync-relations-neo4j` 시각 분산 (12:00 / 12:30 → 12:15 / 13:00) | Neo4j queue 점유 |
| P1 | `update-daily-prices`(17:00) 내부 throttle 검증. 500 calls 즉시 발사 시 즉시 한도 초과 | FMP 분당 한도 |
| P2 | `chainsight-heat-score-daily`, `chainsight-seed-selection`, `extract-news-relations`, `chainsight-co-mentions`, `chainsight-relation-confidence` 등 LLM/Neo4j 무거운 default-queue 태스크에 `'options': {'queue': 'neo4j'}` 또는 별도 큐 부여 검토 | Queue 격리 |
| P2 | `crontab(hour=7)`, `crontab(hour=12)` 등 주석에 UTC/EST 혼용 — `CELERY_TIMEZONE` 명시 확인 및 주석 통일 | 운영 명확성 |
| P3 | `beat_schedule` dict와 DB `PeriodicTask` 일치 여부 자동 점검 스크립트 추가 — common-bugs #28 재발 방지 | Drift 방지 |
| P3 | `aggregate-daily-sentiment`(09:00, LLM 가능성)과 `extract-news-relations`(09:00) 동시 시작 분리 | Gemini RPM |

---

## 6. 점검 미흡 영역 (후속 감사 필요)

1. **dict vs DB drift**: `django_celery_beat.PeriodicTask`의 실제 등록 내역 미확인. `python manage.py shell`에서 `set(PeriodicTask.objects.values_list('name', flat=True))` 비교 필요
2. **태스크 실측 실행 시간**: 본 보고서의 호출 수 추정은 코드 정적 분석. 실측 Celery Flower 로그 또는 `TaskResult` 테이블 분석 필요
3. **Worker timezone 확정**: `config/settings.py`의 `TIME_ZONE` / `CELERY_TIMEZONE` / `CELERY_ENABLE_UTC` 값 확인 필요 — 본 보고서는 "EST 가정"
4. **FMP API rate limit 실측**: Redis 카운터 또는 FMP 응답 헤더(`X-RateLimit-Remaining` 등)로 분당 사용량 모니터링 권고
5. **task expires 만료 빈도**: Celery Flower에서 `EXPIRED` task 비율 확인 — 본 감사가 우려하는 expires 만료가 실제로 발생하는지

---

## 부록 A. 시간대별 태스크 전수 목록

(이 섹션은 디버깅용 reference. 평일 weekday Mon-Fri 기준)

```
00:00  neo4j-health-check (every 6h)
*/30:  check-pipeline-alerts (whole day)
*/5:   sec-sync-dirty-neo4j (whole day, neo4j queue, expires=240s)

01:00  update-economic-calendar (daily)
01:00 Sat  aggregate-weekly-prices

02:00 1st  sync-sp500-constituents
02:00 Sat  chainsight-all-profiles
02:30 1st  archive-old-articles

03:00 1st  refresh-korean-overviews-monthly (LLM bulk 500)
03:00 Sat  chainsight-price-co-movement
03:00 Sun  cleanup-old-macro-data, train-importance-model
03:30 Sun  generate-shadow-report

04:00  cleanup-expired-news-relationships (daily, neo4j)
04:00 Mon  scan-regulatory-relationships
04:00 Sun  check-auto-deploy
04:00 16th sync-institutional-holdings
04:00 Sat  chainsight-stale-decay
04:15 Sun  generate-weekly-ml-report
04:20 Sun  monitor-ml-performance
04:30 1st  build-patent-network
04:30 Sat  chainsight-aggregate-profiles
04:30 Sun  chainsight-neo4j-dirty-sync (neo4j)
04:30 Sun  train-lightgbm-model

05:00 Sat  validation-weekly-batch
05:00 Sun  cleanup-task-results
05:30  enrich-relationship-keywords (daily, neo4j, LLM 100)

06:00  neo4j-health-check (every 6h)
06:00  collect-daily-news-morning, update-economic-indicators
06:00 Mon  sync-etf-holdings
06:00 1st  sec-check-new-filings
06:15  collect-sp500-news-fmp-0615
06:30  collect-category-news-high-morning
06:45  collect-general-news-fmp-morning

07:00  chainsight-heat-score-daily (daily), celery-error-digest (daily)
07:00  collect-category-news-medium-morning
07:30  sync-daily-market-movers, collect-category-news-low
07:45  collect-press-releases-fmp

08:00  keyword-generation-pipeline (LLM), collect-market-news-morning
08:15  classify-news-batch (LLM)
08:30  analyze-news-deep-batch (LLM 50, 4s/req → 200s)
08:45  sync-news-to-neo4j (neo4j)

09:00  aggregate-daily-sentiment (LLM?), extract-news-relations (LLM)
9-16시 매분  refresh-market-pulse-cache
9-16시 5분  update-realtime-prices, update-market-indices
9-16시 10분 calculate-portfolio-values
9-16시 15분 check-screener-alerts

10:00  chainsight-co-mentions (LLM possible)
10:15  classify-news-batch, collect-sp500-news-fmp-1015
10:30  analyze-news-deep-batch
10:45  sync-news-to-neo4j (neo4j)

11:00  chainsight-relation-confidence (LLM possible)

12:00  neo4j-health-check (every 6h), collect-market-news-noon,
       update-economic-indicators, chainsight-sync-profiles-neo4j (neo4j),
       sec-seed-relations-to-chainsight
12:15  classify-news-batch
12:30  analyze-news-deep-batch, collect-general-news-fmp-noon,
       chainsight-sync-relations-neo4j (neo4j)
12:45  sync-news-to-neo4j (neo4j)

13:00  collect-category-news-high-midday, chainsight-seed-selection
13:15  collect-sp500-news-fmp-1315

14:00  collect-category-news-medium-afternoon
14:15  classify-news-batch
14:30  collect-daily-news-afternoon, analyze-news-deep-batch
14:45  sync-news-to-neo4j (neo4j)

15:00  collect-market-news-afternoon
15:15  collect-sp500-news-fmp-1515

16:15  classify-news-batch
16:30  calculate-market-breadth, analyze-news-deep-batch (LLM)
16:35  calculate-sector-heatmap
16:45  extract-daily-news-keywords (LLM), sync-news-to-neo4j (neo4j)

17:00  update-daily-prices (FMP 500), collect-category-news-high-evening
17:15  collect-sp500-news-fmp-1715
17:45  collect-general-news-fmp-evening

18:00  neo4j-health-check (every 6h), collect-market-news-evening,
       sync-sp500-eod-prices (FMP 503), thesis-update-readings (FMP),
       update-economic-indicators
18:15  classify-news-batch, thesis-calculate-scores
18:30  update-sp500-change-percent, run-eod-pipeline,
       analyze-news-deep-batch (LLM), thesis-create-snapshots-and-alerts
18:35  thesis-generate-summaries (LLM)
18:45  sync-news-to-neo4j (neo4j)

19:00  collect-ml-labels, backfill-signal-accuracy

20:00  sync-sp500-financials (FMP 101 stocks × 3 endpoints)

22:00  update-economic-indicators
```

---

## 부록 B. 본 감사가 직접 확인한 파일

- `config/celery.py` (821 lines, 전체)
- `stocks/tasks.py:124-200, 422-460` (sync_sp500_financials, sync_sp500_eod_prices)
- `stocks/services/sp500_eod_service.py:23` (REQUEST_DELAY=0.3)
- `news/tasks.py:511-535, 952-980` (analyze_news_deep, collect_sp500_news_fmp_orchestrator)
- 미확인: thesis-update-readings의 FMP 호출 횟수, sync_etf_holdings 호출 수, update_realtime_with_provider 내부 batch 로직, FMP polygon endpoint 종류
