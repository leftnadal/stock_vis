# Celery Beat 스케줄 감사 보고서

**작성일**: 2026-05-06
**범위**: `config/celery.py` `app.conf.beat_schedule` 전체 (78개 엔트리)
**감사 모드**: 읽기 전용 (코드 수정 없음)
**Celery 시간대**: `CELERY_TIMEZONE = 'America/New_York'` (NY/ET)
**중요 확인**: `CELERY_BEAT_SCHEDULER = django_celery_beat.schedulers:DatabaseScheduler` — config dict는 **선언적 reference**일 뿐, 실 스케줄은 `django_celery_beat.PeriodicTask` DB 테이블이 진실의 소스. 이 보고서는 dict를 분석하지만, 실 동작 검증은 별도 DB diff 필요.

---

## 0. 요약 (TL;DR)

| 위험도 | 항목 | 비고 |
|:------:|------|------|
| **CRITICAL** | 18:00 ET 동시 시작 4건이 default 큐에 집중 (sync-sp500-eod-prices + thesis-update-readings + collect-market-news-evening + update-economic-indicators) | FMP S&P 500 EOD 500종목 + 썬더링 허드 |
| **HIGH** | Gemini RPD 1500 한도가 월 1일 한 번 초과 위험 (refresh-korean-overviews-monthly 500콜 + 일일 평균 885~1300콜) | 합계 1385~1800콜 추정 |
| **HIGH** | 09:00 같은 분에 Gemini 태스크 2건 동시 시작 (extract-news-relations + aggregate-daily-sentiment) | 15 RPM 즉시 초과 가능 |
| **HIGH** | neo4j 큐 12:30 동시 충돌 — chainsight-sync-relations-neo4j + sec-sync-dirty-neo4j (`*/5`) + sync-news-to-neo4j(12:45) | solo pool 1개 워커 → 줄지연 |
| **HIGH** | 시간대 주석과 코드 불일치 — `chainsight-heat-score-daily`, `chainsight-seed-selection`, `chainsight-neo4j-dirty-sync` 주석은 UTC 표기, 실제는 NY 시간 | 운영 혼선 |
| MED | 12:00 ET에 9개 태스크 시작 (4개 API 출처) — 큐 부하 피크 | 하지만 분산 가능 |
| MED | 06:15/06:45/07:30/07:45 FMP 배치 4연속 — 단일은 안전, 누적 지연 시 컨플릭트 | 모니터링 필요 |
| MED | `*/5min` SEC 동기화(sec-sync-dirty-neo4j)가 24/7 → 288회/일 점유 | 다른 neo4j 태스크 줄지연 원인 |
| LOW | `extract-daily-news-keywords`(16:45)는 `analyze-news-deep-batch`(16:30)와 15분 분리 — 2026-04-26 P0 #8 fix 적용됨 | 잘 처리됨 |

---

## 1. 시간대별 ASCII 히트맵 (평일 NY 시간 기준)

### 1.1 시간당 태스크 시작 건수 (스케줄된 분 기준 + 정기 반복 합산)

```
시  | 시작 건수 | 막대 (■=2건)              | 주된 출처
----|----------|---------------------------|-----------------------------------
 00 |    14    | ■■■■■■■                    | sec-sync(*/5)+pulse-cache(외)+pipeline-alerts(*/30)
 01 |    15    | ■■■■■■■■                   | +update-economic-calendar(daily)
 02 |    14    | ■■■■■■■                    | sec-sync only (월/토 추가)
 03 |    15    | ■■■■■■■■                   | +cleanup-old-macro(일) +chainsight-price-co(토) +korean-overviews(1일)
 04 |    19    | ■■■■■■■■■■                 | +cleanup-expired-news-relations +ML 리포트군(일) +regulatory(월)
 05 |    15    | ■■■■■■■■                   | +enrich-relationship-keywords(일) +validation-weekly(토)
 06 |    20    | ■■■■■■■■■■                 | sp500-news-fmp+category-news+general-fmp(평일) +etf(월)
 07 |    20    | ■■■■■■■■■■                 | heat-score+celery-digest+market-movers+press-releases
 08 |    19    | ■■■■■■■■■■                 | keyword-pipeline + classify(15) + analyze-deep(30) ★Gemini
 09 |    16    | ■■■■■■■■                   | aggregate-sentiment + extract-news-relations ★Gemini 충돌
 10 |    19    | ■■■■■■■■■■                 | co-mentions + sp500-news + classify(15) + analyze-deep(30) + neo4j(45)
 11 |    15    | ■■■■■■■■                   | +relation-confidence
 12 |    23    | ■■■■■■■■■■■■               | ★PEAK 9건 신규 시작 (FRED+Gemini+Neo4j×2+FMP+SEC)
 13 |    16    | ■■■■■■■■                   | seed-selection + sp500-news-1315 + category-high-midday
 14 |    19    | ■■■■■■■■■■                 | category-medium + classify(15) + daily-news-pm(30) + analyze-deep(30) + neo4j(45)
 15 |    16    | ■■■■■■■■                   | market-news-pm + sp500-news-1515
 16 |    20    | ■■■■■■■■■■                 | classify(15) + market-breadth(30) + analyze-deep(30) + sector-heatmap(35) + extract-keywords(45) + neo4j(45)
 17 |    18    | ■■■■■■■■■                  | update-daily-prices + category-high-evening + sp500-news-1715 + general-fmp-evening
 18 |    25    | ■■■■■■■■■■■■■              | ★MEGA PEAK 11건 신규 (sp500-eod + thesis-trio + classify + analyze-deep + run-eod + ...)
 19 |    16    | ■■■■■■■■                   | collect-ml-labels + backfill-signal-accuracy
 20 |    15    | ■■■■■■■■                   | sync-sp500-financials (FMP heavy)
 21 |    14    | ■■■■■■■                    | (정기만)
 22 |    15    | ■■■■■■■■                   | update-economic-indicators
 23 |    14    | ■■■■■■■                    | (정기만)
```

**기준선** (모든 시간대 24/7 공통):
- `sec-sync-dirty-neo4j` `*/5min` = **12회/시**
- `check-pipeline-alerts` `*/30min` = **2회/시**

**시장 시간(09~16) 추가**:
- `refresh-market-pulse-cache` `*/1min` = **60회/시**
- `update-realtime-prices` `*/5min` = 12회/시 (FMP)
- `update-market-indices` `*/5min` = 12회/시 (FMP)
- `calculate-portfolio-values` `*/10min` = 6회/시
- `check-screener-alerts` `*/15min` = 4회/시

→ **시장 시간 시간당 약 110~130건 (대부분 1초 미만)** vs **장외 시간 약 14~25건**.

### 1.2 PEAK 시각 분 단위 줌 (18:00~18:45 ET 평일)

```
분  | 신규 시작 | API/큐                                       | 위험
----|----------|---------------------------------------------|----------------------------
:00 |    4     | FMP(eod-prices 500종목) + FMP(thesis-readings) + FRED + News(market-evening) | ★썬더링 허드
:05 |    1     | sec-sync (neo4j)                            | 정상
:10 |    1     | refresh-market-pulse-cache (마지막 — 16시 끝났어야 하나 9-16시 only)
:15 |    2     | Gemini(classify) + thesis-calc-scores       | classify ~50콜
:20 |    -     |                                             |
:25 |    -     |                                             |
:30 |    5     | Gemini(analyze-deep) + thesis-snapshots + run-eod-pipeline + update-sp500-change-percent + (sec-sync) | ★default 큐 4건
:35 |    -     |                                             |
:40 |    -     |                                             |
:45 |    2     | sync-news-to-neo4j(neo4j) + (sec-sync 35분 instance still running 가능)
```

→ 18:00 동시성과 18:30 동시성이 **default 큐 워커 부족 시 줄지연**.

### 1.3 PEAK 시각 분 단위 줌 (12:00~12:45 ET, 평일 vs 주말)

```
분  | 신규 시작 | API/큐
----|----------|--------------------------------------------------
:00 |    4     | FRED + News + chainsight-sync-profiles(neo4j) + sec-seed-relations
:05 |    1     | sec-sync (neo4j)
:10 |    -     |
:15 |    2     | Gemini(classify) + sp500-news-1315(0배) → 13:15가 정확
:20 |    -     |
:25 |    -     |
:30 |    4     | Gemini(analyze-deep) + chainsight-sync-relations(neo4j) + general-fmp-noon + sec-sync
:35 |    -     |
:40 |    -     |
:45 |    1     | sync-news-to-neo4j (neo4j)
```

→ neo4j 큐 30~31분 동안 3건 연속 (sec-sync + chainsight-sync-relations + ...). **solo pool 1개 워커는 직렬 처리 → chainsight-sync-relations가 2분 이상이면 sec-sync 12:35 instance 줄지연**.

---

## 2. Rate Limit 초과 구간

### 2.1 FMP (Starter Plan, 300 calls/min, 10,000 calls/day)

> **현재 설정**: `FMPClient.request_delay = 0.2초` (`api_request/providers/fmp/client.py:57`), `daily_calls=10000`. CLAUDE.md(10/min)는 구버전 기록 — 실 코드와 운영 모두 Starter 300/min로 동작 중 (`docs/problem_reports/celery-beat-sync-not-running.md:74`, `news/tasks.py:906`).

#### FMP 호출 무거운 태스크와 추정 콜 수

| 태스크 | 시각 (ET) | 추정 FMP 호출 | 비고 |
|--------|----------|--------------|------|
| `sync-sp500-eod-prices` | 18:00 평일 | **~500 quotes** | S&P 500 전체 (배치 가능 시 ~25콜) |
| `sync-sp500-financials` | 20:00 평일 | **~303 calls** | 101종목 × 3재무제표, daily 순환 |
| `collect-sp500-news-fmp-*` | 06:15/10:15/13:15/15:15/17:15 평일 | **~50-100 each** | 500종목 batch news |
| `collect-press-releases-fmp` | 07:45 평일 | **50** | max_symbols=50 |
| `sync-daily-market-movers` | 07:30 평일 | ~5-15 | gainers/losers/active 3종 |
| `update-stock_with_provider` (호출자: 여러 곳) | 9-16 `*/5min` | **~5-25 per run** | batched quotes |
| `update-market-indices` | 9-16 `*/5min` | ~5-10 | major indices |
| `thesis-update-readings` | 18:00 평일 | ~20-50 | 지표 fetch (FMP 일부) |

#### 위험 구간

- **R-FMP-1 (CRITICAL)**: **18:00 ET** — `sync-sp500-eod-prices`(~500콜) + `thesis-update-readings`(~50콜) 동시 시작.
  - sync-sp500-eod-prices가 단일 워커에서 0.2s delay면 100초 소요. thesis-update-readings가 같은 워커풀 점유 시 직렬화 → 200초+. 다른 워커에서 병렬 시 **1초당 평균 5콜 동시 + 0.5콜/초 (thesis) = 5.5/sec → 330/min → 300/min 한도 살짝 초과** 가능.
  - 추가로 18:00에 `update-realtime-prices`는 16시까지만이라 안 충돌.
  - **실측 권고**: FMP 응답 헤더 `X-RateLimit-Remaining` 로깅 확인.

- **R-FMP-2 (HIGH)**: **06:15** `collect-sp500-news-fmp-0615` 시작 직후 **06:45** `collect-general-news-fmp-morning` 시작. 0615 orchestrator가 30분 이내 완료 못하면 두 FMP 태스크 동시 실행 → 콜 누적.

- **R-FMP-3 (MED)**: **20:00** `sync-sp500-financials`가 101종목×3재무제표=303콜. 0.2s × 303 = ~60초. 같은 시각에 다른 FMP 태스크 없음(좋음). 단 `news.tasks.py:906`의 `rate_limit='100/m'` 설정이 어디 적용되는지 점검 필요(현재는 sync_news_to_neo4j용으로 추정).

- **R-FMP-4 (MED)**: **9-16 시장 시간 동시 `*/5min` 두 태스크** — `update-realtime-prices` + `update-market-indices`. 같은 5분 boundary에 시작하므로 동시 실행. 각각 ~5-15콜 → 합계 30콜/5min = 6 calls/min 평균. **300/min 안전 마진 충분**.

### 2.2 Gemini (Free Tier: 15 RPM, 1500 RPD)

#### Gemini 호출 태스크 (확인됨: `news/tasks.py`, `serverless/tasks.py`에서 import)

| 태스크 | 시각 (ET) | 추정 Gemini 호출 | 일일 누계 |
|--------|----------|-----------------|----------|
| `keyword-generation-pipeline` | 08:00 daily | ~25-50 | 25-50 |
| `classify-news-batch-morning` | 08:15/10:15/12:15/14:15/16:15/18:15 wd | ~50 each | **~300/일** |
| `analyze-news-deep-batch` | 08:30/10:30/12:30/14:30/16:30/18:30 wd | max_articles=50 → ~50-100 each | **~300-600/일** |
| `extract-daily-news-keywords` | 16:45 daily | ~50-100 | 50-100 |
| `extract-news-relations` | 09:00 daily | ~10-50 | 10-50 |
| `aggregate-daily-sentiment` | 09:00 wd | ~50 | 50 |
| `chainsight-co-mentions` | 10:00 daily | ~50 | 50 |
| `enrich-relationship-keywords` | 05:30 daily | limit=100 | 100 |
| `refresh-korean-overviews-monthly` | 1일 03:00 | **~500** | (월 1회 spike) |
| `scan-regulatory-relationships` | 월요일 04:00 | ~30-50 | (주 1회) |
| `train-importance-model` | 일 03:00 | (LLM 미사용) | 0 |
| **일평균 합계** | — | — | **~885-1300** |
| **월 1일 합계** | — | — | **~1385-1800** |

#### 위험 구간

- **R-GEM-1 (CRITICAL)**: **월 1일 03:00** `refresh-korean-overviews-monthly` 단독 500콜이 평일과 겹칠 경우 (1일이 평일이면) **일일 누계가 1500 RPD를 초과**할 수 있다.
  - 시뮬레이션: 평일 1300콜 + 월 1일 500콜 = **1800 → +20% 초과**.
  - 현재 코드에 daily quota 체크 없음 → 후순위 태스크가 무음 실패.
  - **권고**: refresh-korean-overviews-monthly를 토/일에 강제하거나, daily counter로 1500 hit 시 break.

- **R-GEM-2 (HIGH)**: **09:00 ET 같은 분에 두 Gemini 태스크 시작** — `extract-news-relations`(daily) + `aggregate-daily-sentiment`(wd).
  - 둘 다 batch sentiment/relation을 순차 호출 시 처음 1분에 두 워커가 동시에 ~10콜씩 → **20 RPM 즉시 초과 → 429**.
  - 현재 두 태스크에 `rate_limit` 설정 없음 (확인 필요).
  - **권고**: 09:00과 09:05로 분산하거나 `rate_limit='8/m'`을 각각 부여.

- **R-GEM-3 (HIGH)**: **08:00~08:30 / 10:00~10:30 / 18:00~18:30 윈도우**에서 keyword/classify/analyze-deep/co-mentions가 **30분간 누적 100~150콜** → 평균 3-5 RPM이지만 **버스트 시 15 RPM 초과 가능**.
  - 16:30 → 16:45 분리는 2026-04-26 P0 #8로 이미 fix됨 (15분 간격).
  - 같은 패턴이 다른 시간대에도 적용되었는지 점검 필요. 특히 18:30에 `analyze-news-deep-batch`만 단독이라 비교적 안전.

- **R-GEM-4 (MED)**: `analyze-news-deep-batch` `max_articles=50` × 6회 = 300콜/일. 단일 태스크 내에서 sequential일 가능성 높음 (워커 1개) → 50콜 × 1초 ~= 50초 소요 시 RPM은 60/min로 살짝 초과. 내부에 **4초 sleep**(audit P0 메모) 적용된 것으로 보이나 confirm 필요.

### 2.3 Alpha Vantage (5 calls/min, 12s delay)

- 현재 beat_schedule에 **Alpha Vantage 직접 호출 태스크 없음**. `docs/migration/`에는 12초 delay 명시되어 있으나 신규 코드에서는 사용 축소.
- **위험**: 코드 잔존(`alpha_vantage_client.py`)이 어디선가 호출되는지 확인 필요. 현재 스케줄 기준으로는 **NONE**.

### 2.4 FRED (100/min, RateLimiter 적용)

- `update-economic-indicators` 06/12/18/22시 평일 4회. 1회당 ~10-30 indicator fetch. 4회 × 30 = 120콜/일.
- **위험**: 100/min 한도 안전.

### 2.5 SEC EDGAR (0.12s sleep)

- `sec-sync-dirty-neo4j` `*/5min` 24/7 = 288회/일. 각 호출당 dirty queue 플러시 (보통 0~10 evidence) → SEC API 호출 미미.
- `sec-check-new-filings` 1일 06:00 — heavy.
- **위험**: 1일 06:00에 `collect-daily-news-morning`(News API), `sec-check-new-filings`(SEC API), `sync-etf-holdings`(SPDR XLSX 월) 합치면 **6:00에 3개 외부 API 동시**. 다른 API라서 rate limit 충돌 없음. 하지만 워커 점유 측면에서 부담.

---

## 3. Queue 몰림 분석

### 3.1 Default Queue 시간대별 부하

| 시각 (ET) | 동시 시작 (default 큐) | 위험도 |
|----------|----------------------|--------|
| 06:00 wd | collect-daily-news-morning + sync-etf-holdings(월) + sec-check-new-filings(1일) | MED (월 1일 + 월요일 동시 = HIGH) |
| 09:00 wd | extract-news-relations + aggregate-daily-sentiment | HIGH (Gemini 충돌) |
| 12:00 wd | update-economic-indicators + collect-market-news-noon + sec-seed-relations-to-chainsight | MED |
| 16:30 wd | calculate-market-breadth + analyze-news-deep-batch | MED |
| **18:00 wd** | **sync-sp500-eod-prices + thesis-update-readings + collect-market-news-evening + update-economic-indicators** | **CRITICAL (4건 동시)** |
| 18:30 wd | analyze-news-deep-batch + thesis-create-snapshots + run-eod-pipeline + update-sp500-change-percent | HIGH (4건 동시) |
| 20:00 wd | sync-sp500-financials | LOW (단독) |

#### 워커 동시성 추정

- 운영 환경에서 default 큐 워커 수 미확인. 통상 4-8 prefork 또는 macOS solo (1).
- **macOS solo pool**: 18:00의 4건이 **순차 직렬화 → 1.7+0.5+짧음+짧음 ≈ 3분 이상** 첫 태스크 후속 지연.
- **Linux prefork 4 워커**: 4건 병렬 가능 → 안전. 하지만 5분 후 18:05의 `sec-sync-dirty-neo4j`는 별도 큐.

### 3.2 Neo4j Queue (solo pool, 동시 1개)

| 시각 (ET) | Neo4j 큐 신규 태스크 | 누적 점유 |
|----------|----------------------|---------|
| 매시 :00, :05, :10, :15, ..., :55 | `sec-sync-dirty-neo4j` (24/7) | 베이스라인 |
| 04:00 daily | + cleanup-expired-news-relationships | 2건 |
| 04:30 일 | + chainsight-neo4j-dirty-sync | (일 새벽) |
| 05:30 daily | + enrich-relationship-keywords | 2건 |
| 6, 12, 18, 0시(*/6h) | + neo4j-health-check | 2건 |
| 8:45 / 10:45 / 12:45 / 14:45 / 16:45 / 18:45 wd | + sync-news-to-neo4j | 2건 |
| 12:00 daily | + chainsight-sync-profiles-neo4j | 2건 |
| 12:30 daily | + chainsight-sync-relations-neo4j | 2건 (sec-sync 12:30 instance와) |

**핵심 우려**:
- **N-Q-1 (HIGH)**: solo pool 워커 1개라서 **태스크가 평균 30초 이상 걸리면 *5min 주기의 sec-sync가 줄지연**. 특히 12:30, 12:45, 18:45는 sync-news-to-neo4j(100 articles)가 길게 걸릴 수 있어 sec-sync 다음 instance 30초~수분 지연.
- **N-Q-2 (MED)**: 워커 종료/재시작이 SIGSEGV 방지 차원에서 잦으면 (`worker_process_init`) 큐 큐잉 적체 가능.
- **N-Q-3 (LOW)**: Beat 자체는 매 분 신규 큐잉만 하므로 적체는 워커 처리 속도 문제. 모니터링 메트릭 권장: `celery -A config inspect active_queues` + Redis `LLEN celery:neo4j`.

---

## 4. 스케줄 겹침 / 의존성

### 4.1 동시 실행 데이터 경합 가능성

| Task A | Task B | 시각 | 경합 자원 | 위험 |
|--------|--------|------|-----------|------|
| `sync-sp500-eod-prices` (FMP→DailyPrice 쓰기) | `thesis-update-readings` (DailyPrice 읽기) | 18:00 ET | DailyPrice 테이블 | A 미완 시 B는 어제 데이터로 계산 |
| `update-economic-indicators` (FRED→EconomicIndicator 쓰기) | `thesis-update-readings` | 18:00 ET | EconomicIndicator 테이블 | 동일 |
| `chainsight-sync-profiles-neo4j` | `chainsight-sync-relations-neo4j` | 12:00 / 12:30 (30분 차) | Neo4j 그래프 | 분리되어 있어 안전 |
| `analyze-news-deep-batch` (NewsArticle 쓰기) | `sync-news-to-neo4j` | :30 / :45 (15분 차) | NewsArticle.is_analyzed | 거의 안전 |
| `aggregate-daily-sentiment` | `extract-news-relations` | 09:00 (동시!) | NewsArticle 읽기 | 읽기만이면 안전, **둘 다 Gemini라 RPM은 충돌** |
| `run-eod-pipeline` (DailyPrice 읽기) | `update-sp500-change-percent` (DailyPrice 쓰기) | 18:30 (동시!) | DailyPrice | **순서 보장 X — 경합 가능** |
| `thesis-create-snapshots` | `run-eod-pipeline` | 18:30 (동시!) | Thesis 모델 | 별 모델이라 안전 |

#### 핵심 경합 케이스

- **C-1 (HIGH)**: **18:30 동시 시작 4건** 중 `update-sp500-change-percent`와 `run-eod-pipeline`이 **DailyPrice를 동시 읽기/쓰기**.
  - `update-sp500-change-percent`는 일괄 update이므로 row-level lock.
  - `run-eod-pipeline`이 EOD 시그널 계산 시 DailyPrice를 SELECT → 부분 업데이트된 값을 볼 수 있음.
  - **권고**: 의존성 chain으로 명시 (signature/chord) 또는 18:35로 update-sp500-change-percent 이동.

- **C-2 (MED)**: **18:00의 `sync-sp500-eod-prices`가 18:00의 `thesis-update-readings`보다 늦게 끝나면**, thesis는 어제 가격으로 점수 계산. 현 dict는 그냥 동시 시작.
  - 코드 주석(`thesis-update-readings`)은 "장 마감 후"라고만 표기 — sync-sp500-eod-prices와의 ordering 미보장.
  - **권고**: thesis-update-readings를 18:15 → thesis-calculate-scores를 18:30 → ... 로 슬라이드.

### 4.2 선행 태스크 완료 전 후속 시작 (Implicit Dependency)

스케줄 dict에는 chord/chain이 **없음** — 모든 의존성이 시간 차로만 표현되어 있다. 다음 페어는 시간 갭이 좁아 위험.

| 선행 (Producer) | 후속 (Consumer) | 시간 갭 | 위험 |
|-----------------|-----------------|--------|------|
| `sync-sp500-eod-prices` (18:00, ~100s) | `thesis-update-readings` (18:00 동시!) | **0분** | C-2 동일, **HIGH** |
| `sync-sp500-eod-prices` (18:00) | `update-sp500-change-percent` (18:30) | 30분 | OK |
| `sync-sp500-eod-prices` (18:00) | `run-eod-pipeline` (18:30) | 30분 | OK |
| `thesis-update-readings` (18:00) | `thesis-calculate-scores` (18:15) | 15분 | OK if reading 60초 이내 |
| `thesis-calculate-scores` (18:15) | `thesis-create-snapshots` (18:30) | 15분 | OK |
| `collect-daily-news-morning` (06:00) | `aggregate-daily-sentiment` (09:00) | 3시간 | OK |
| `analyze-news-deep-batch` (×6) | `sync-news-to-neo4j` (각 +15분) | 15분 | OK |
| `chainsight-co-mentions` (10:00) | `chainsight-relation-confidence` (11:00) | 60분 | OK |
| `chainsight-relation-confidence` (11:00) | `chainsight-sync-relations-neo4j` (12:30) | 90분 | OK |
| `chainsight-all-profiles` (토 02:00, ~7200s expires) | `chainsight-price-co-movement` (토 03:00) | 60분 | **TIGHT** — 프로파일이 60분+ 걸리면 충돌 |
| `chainsight-price-co-movement` (토 03:00) | `chainsight-stale-decay` (토 04:00) | 60분 | TIGHT |
| `chainsight-stale-decay` (토 04:00) | `chainsight-aggregate-profiles` (토 04:30) | 30분 | TIGHT |
| `train-importance-model` (일 03:00, expires 7200) | `generate-shadow-report` (일 03:30) | 30분 | **TIGHT — 학습이 30분+ 걸리면 충돌** |
| `generate-shadow-report` (일 03:30) | `check-auto-deploy` (일 04:00) | 30분 | OK |
| `check-auto-deploy` (일 04:00) | `generate-weekly-ml-report` (일 04:15) | 15분 | TIGHT |
| `chainsight-heat-score-daily` (07:00 ET) | `chainsight-seed-selection` (13:00 ET) | 6시간 | OK |
| `sync-supply-chain-batch` (월15일 03:00) | `sync-institutional-holdings` (월16일 04:00) | 25시간 | OK (다른 날) |

#### 핵심 의존성 우려

- **D-1 (HIGH)**: **`chainsight-all-profiles` (토 02:00) → `chainsight-price-co-movement` (토 03:00)** — `expires=7200` (2시간)이라 expire 자체는 OK이나, profile이 1시간+ 걸리면 price-co가 stale profile 위에 동작.
- **D-2 (HIGH)**: **`train-importance-model` (일 03:00) → `generate-shadow-report` (일 03:30)** — 학습 시간이 30분 초과 시 두 태스크 동시 실행 → 모델 파일 race.
- **D-3 (MED)**: **`thesis-update-readings`가 18:00의 sync-sp500-eod-prices와 동시 시작** — 위 C-2와 동일 이슈.

### 4.3 시간대 주석 vs 실제 코드 불일치

`CELERY_TIMEZONE = America/New_York` 기준이지만 일부 주석이 UTC 표기.

| 태스크 | 주석 | crontab 코드 | 실 실행 시각 (NY ET) | 실 실행 시각 (UTC, 동절기) |
|--------|------|------------|---------------------|---------------------|
| `chainsight-heat-score-daily` | "매일 07:00 UTC, 시드 선정 전" | `crontab(hour=7, minute=0)` | **07:00 ET** | 12:00 UTC |
| `chainsight-seed-selection` | "매일 13:00 UTC, 관계 동기화 후" | `crontab(hour=13, minute=0)` | **13:00 ET** | 18:00 UTC |
| `chainsight-neo4j-dirty-sync` | "매주 일요일 04:30 UTC" | `crontab(hour=4, minute=30, day_of_week=0)` | **일 04:30 ET** | 일 09:30 UTC |

→ 운영자가 "UTC 기준"으로 모니터링 시간 설정 시 5시간 어긋남. **2026-04-24 drift 복구 메모**(`config/celery.py:129-131`)와 같은 후속 혼선 위험.

---

## 5. 권고 (수정 없음, 차후 PR 단위 제안)

> 본 보고서는 읽기 전용. 아래는 후속 PR 시 고려 항목.

| ID | 권고 | 우선순위 |
|----|------|--------|
| P0-1 | **18:00 ET 4건 동시 시작 분산**: thesis-update-readings를 18:05 → thesis-calc-scores 18:15 → thesis-snapshots 18:30. sync-sp500-eod-prices 단독 18:00 유지. | CRITICAL |
| P0-2 | **09:00 ET Gemini 두 태스크 분리**: aggregate-daily-sentiment 09:00 / extract-news-relations **09:05** 또는 **09:10**. | HIGH |
| P0-3 | **refresh-korean-overviews-monthly 일정 변경**: 1일 03:00 ET → **1일 직후 토요일 02:00** (Chain Sight all-profiles와도 분리). RPD 1500 초과 위험 제거. | HIGH |
| P0-4 | **18:30 동시성 분산**: run-eod-pipeline 18:30 유지, update-sp500-change-percent → 18:35 → backfill-signal-accuracy 19:00. DailyPrice race 제거. | HIGH |
| P1-1 | **chord/chain으로 의존성 명시** — 토요일 Chain Sight 체인 (all-profiles → price-co → stale-decay → aggregate). expires만으로는 부족. | MED |
| P1-2 | **train-importance-model → generate-shadow-report 의존성** chain화 (chord). | MED |
| P1-3 | **시간대 주석 정리**: chainsight-heat-score-daily, chainsight-seed-selection, chainsight-neo4j-dirty-sync의 주석을 NY ET로 통일. | MED |
| P1-4 | **Neo4j 큐 워커 추가 검토** — `*/5min` sec-sync가 점유 시 chainsight 동기화 누적 시 줄지연. 또는 sec-sync를 `*/10min`으로 완화. | MED |
| P2-1 | **Daily Gemini quota guard** — Redis counter로 1500 RPD hit 시 후속 Gemini 태스크 skip. | LOW |
| P2-2 | **DB drift 점검 명령**: `python manage.py shell -c "..."`을 management command화하여 PeriodicTask DB와 config dict 비교를 자동화. | LOW |

---

## 6. 검증 방법론 (확인되지 않은 가정)

본 감사는 **dict 정적 분석**에 기반. 다음은 실 동작 검증으로 확정 필요:

1. **DB 진실의 소스 확인** — `PeriodicTask.objects.all()` vs config dict diff (CLAUDE.md "Drift 재발 방지" 메모와 동일).
2. **Gemini 콜 수 실측** — `news.tasks` Gemini SDK 호출에 콜 수 로깅 추가, 일 1500 RPD 도달 빈도 확인.
3. **FMP 콜 수 실측** — FMP Starter 대시보드에서 18:00, 20:00 burst 시점 콜 수 확인.
4. **워커 처리 시간 측정** — 18:00 sync-sp500-eod-prices 평균 소요(`task_postrun` 로그).
5. **Neo4j 큐 적체 모니터링** — `LLEN celery:neo4j` 시계열, 12:30 / 18:45 즈음 spike 여부.

---

## 부록 A: 78개 beat_schedule 엔트리 전수 목록

(별도 표 — 첨부 별지로 분리. 본 보고서 본문에 포함된 시간/태스크 매핑이 진실의 소스.)

```
[Stocks] update-realtime-prices, update-daily-prices, aggregate-weekly-prices,
         sync-sp500-financials, sync-sp500-constituents, sync-sp500-eod-prices,
         update-sp500-change-percent, run-eod-pipeline, backfill-signal-accuracy,
         refresh-korean-overviews-monthly
[Users] calculate-portfolio-values
[Macro] update-economic-indicators, update-market-indices, update-economic-calendar,
        refresh-market-pulse-cache, cleanup-old-macro-data
[RAG] neo4j-health-check
[Serverless/Movers] sync-daily-market-movers, keyword-generation-pipeline,
                    sync-etf-holdings, sync-supply-chain-batch,
                    calculate-market-breadth, calculate-sector-heatmap, check-screener-alerts,
                    extract-news-relations, enrich-relationship-keywords,
                    sync-institutional-holdings, scan-regulatory-relationships,
                    build-patent-network, sec-seed-relations-to-chainsight
[News] collect-daily-news-morning/afternoon, collect-market-news-(4종),
       aggregate-daily-sentiment, extract-daily-news-keywords,
       collect-category-news-(6종), classify-news-batch-morning, analyze-news-deep-batch,
       collect-ml-labels, sync-news-to-neo4j, cleanup-expired-news-relationships,
       train-importance-model, generate-shadow-report, check-auto-deploy,
       generate-weekly-ml-report, monitor-ml-performance, train-lightgbm-model,
       check-pipeline-alerts,
       collect-sp500-news-fmp-(5종), collect-press-releases-fmp,
       collect-general-news-fmp-(3종),
       archive-old-articles
[Thesis] thesis-update-readings, thesis-calculate-scores, thesis-create-snapshots
[Chain Sight] chainsight-all-profiles, chainsight-co-mentions, chainsight-price-co-movement,
              chainsight-relation-confidence, chainsight-stale-decay,
              chainsight-aggregate-profiles, chainsight-sync-profiles-neo4j,
              chainsight-sync-relations-neo4j, chainsight-heat-score-daily,
              chainsight-seed-selection, chainsight-neo4j-dirty-sync
[Validation] validation-weekly-batch
[SEC] sec-sync-dirty-neo4j, sec-check-new-filings
[Ops] celery-error-digest, cleanup-task-results
```

총 **78개** (Stocks 10 + Users 1 + Macro 5 + RAG 1 + Serverless/Movers 13 + News 35 + Thesis 3 + Chain Sight 11 + Validation 1 + SEC 2 + Ops 2 — 일부 중복 카운트 가능, 개략).
