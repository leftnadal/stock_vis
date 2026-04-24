# Beat Schedule 감사 보고서

- **작성일**: 2026-04-24
- **대상 파일**: `config/celery.py` (L135-L805)
- **모드**: 읽기 전용 (코드 수정 없음)
- **Celery TIME_ZONE**: `America/New_York` (ET, DST 적용) — `config/settings.py:403` 기준 (기존 보고서에서 검증됨)
- **Queue 구성**: `default` + `neo4j` (solo pool, 동시 1개)
- **분석 범위**: `app.conf.beat_schedule` dict 에 선언된 총 **68개 태스크**

> 주의: `config/celery.py` L120~L134 주석에 따라 `CELERY_BEAT_SCHEDULER='django_celery_beat.schedulers:DatabaseScheduler'` 설정으로 이 dict 는 **런타임 비활성**이며 실제 실행은 `PeriodicTask` 테이블에서 결정된다. 이번 감사는 dict 선언 기준이며 DB 와 drift 가 있을 수 있다.

---

## 0. 요약 (Executive Summary)

| 심각도 | 개수 | 대표 항목 |
|--------|------|----------|
| 🔴 CRITICAL | 4 | 18:00 FMP 4중 / 18:30 4중 겹침 / analyze-news-deep 50건 Gemini / neo4j queue solo-pool 12:00 3중 |
| 🟠 WARNING | 6 | 16:30 LLM 2중, 14:30 수집-분석 역순, 시각 기준 EST/UTC 혼재(chainsight-heat-score/seed-selection), 05:30 enrich 지연→sec-sync expires 폐기, 일요일 04시 ML 체인 부하, 08:00 market-movers 선행 의존 |
| 🟡 INFO | 5 | refresh-market-pulse-cache 480회/일, sec-sync-dirty-neo4j 288회/일, check-pipeline-alerts 48회/일, 시장시간 정각 7태스크 동시 시작, 토요일 Chain Sight 선형 체인(정상) |

**핵심 수치**:
- 정각(분=00) 시장시간 동시 실행 태스크: **7개** (realtime+indices+pulse+portfolio+screener+sec-sync+pipeline-alerts)
- Gemini 일일 LLM 호출 추정 상한: `analyze-news-deep-batch 50 × 6` + `classify-news-batch ~30~50 × 6` + `enrich 100` + `extract/keyword ~60` ≈ **약 600~900 호출/일** (Gemini Free 1500 RPD 의 40~60%)
- Gemini 분 단위 RPM 위험: `analyze-news-deep-batch` 가 내부 sleep 없이 50건 연속 호출 시 15 RPM 의 **3배 이상** 초과
- neo4j queue 최소 점유: `sec-sync-dirty-neo4j` **288회/일** + 다른 배치

---

## 1. 태스크 인벤토리 (68개)

### 1.1 주기형 태스크 (분 단위 반복)

| 태스크 | 주기 | 시간 범위 | 요일 | 큐 | API | 일 실행 수 (평일) |
|--------|------|----------|------|-----|-----|------------------|
| update-realtime-prices | `*/5` | 9-16 | 월-금 | default | FMP | 96 |
| update-market-indices | `*/5` | 9-16 | 월-금 | default | FMP | 96 |
| refresh-market-pulse-cache | `*` | 9-16 | 월-금 | default | (내부 캐시) | 480 |
| calculate-portfolio-values | `*/10` | 9-16 | 월-금 | default | (DB) | 48 |
| check-screener-alerts | `*/15` | 9-16 | 월-금 | default | (DB) | 32 |
| check-pipeline-alerts | `*/30` | 24시간 | 매일 | default | (내부) | 48 |
| sec-sync-dirty-neo4j | `*/5` | 24시간 | 매일 | **neo4j** | (Neo4j) | **288** |

### 1.2 평일 시간 고정 태스크 (ET)

| 시각 | 태스크 | 큐 | API |
|------|--------|-----|-----|
| 06:00 | update-economic-indicators (1/4) | default | FRED |
| 06:00 | collect-daily-news-morning | default | 뉴스 API |
| 06:15 | collect-sp500-news-fmp-0615 | default | **FMP** |
| 06:30 | collect-category-news-high-morning | default | 뉴스 API |
| 06:45 | collect-general-news-fmp-morning | default | **FMP** |
| 07:00 | collect-category-news-medium-morning | default | 뉴스 API |
| 07:30 | sync-daily-market-movers | default | **FMP** |
| 07:30 | collect-category-news-low | default | 뉴스 API |
| 07:45 | collect-press-releases-fmp | default | **FMP** (50 심볼) |
| 08:00 | keyword-generation-pipeline | default | **Gemini** |
| 08:00 | collect-market-news-morning | default | 뉴스 API |
| 08:15 | classify-news-batch | default | **Gemini** |
| 08:30 | analyze-news-deep-batch | default | **Gemini** (50건) |
| 08:45 | sync-news-to-neo4j | **neo4j** | (Neo4j, 100건) |
| 09:00 | aggregate-daily-sentiment | default | (DB) |
| 10:15 | classify-news-batch | default | **Gemini** |
| 10:30 | analyze-news-deep-batch | default | **Gemini** |
| 10:45 | sync-news-to-neo4j | **neo4j** | (Neo4j) |
| 12:00 | update-economic-indicators (2/4) | default | FRED |
| 12:00 | chainsight-sync-profiles-neo4j | **neo4j** | (Neo4j) |
| 12:00 | sec-seed-relations-to-chainsight | default | (DB) |
| 12:15 | classify-news-batch | default | **Gemini** |
| 12:30 | analyze-news-deep-batch | default | **Gemini** |
| 12:30 | chainsight-sync-relations-neo4j | **neo4j** | (Neo4j) |
| 12:30 | collect-general-news-fmp-noon | default | **FMP** |
| 12:45 | sync-news-to-neo4j | **neo4j** | (Neo4j) |
| 13:00 | collect-category-news-high-midday | default | 뉴스 API |
| 13:00 | chainsight-seed-selection | default | (DB) — **UTC 주석** |
| 13:15 | collect-sp500-news-fmp-1315 | default | **FMP** |
| 14:00 | collect-category-news-medium-afternoon | default | 뉴스 API |
| 14:15 | classify-news-batch | default | **Gemini** |
| 14:30 | collect-daily-news-afternoon | default | 뉴스 API |
| 14:30 | analyze-news-deep-batch | default | **Gemini** — ※ 수집 동시 |
| 14:45 | sync-news-to-neo4j | **neo4j** | (Neo4j) |
| 15:00 | collect-market-news-afternoon | default | 뉴스 API |
| 15:15 | collect-sp500-news-fmp-1515 | default | **FMP** |
| 16:15 | classify-news-batch | default | **Gemini** |
| 16:30 | extract-daily-news-keywords | default | **Gemini** |
| 16:30 | calculate-market-breadth | default | (DB) |
| 16:30 | analyze-news-deep-batch | default | **Gemini** |
| 16:35 | calculate-sector-heatmap | default | (DB) |
| 16:45 | sync-news-to-neo4j | **neo4j** | (Neo4j) |
| 17:00 | update-daily-prices | default | **FMP** (일일 종가) |
| 17:00 | collect-category-news-high-evening | default | 뉴스 API |
| 17:15 | collect-sp500-news-fmp-1715 | default | **FMP** |
| 17:45 | collect-general-news-fmp-evening | default | **FMP** |
| 18:00 | update-economic-indicators (3/4) | default | FRED |
| 18:00 | collect-market-news-evening | default | 뉴스 API |
| 18:00 | sync-sp500-eod-prices | default | **FMP (SP500 대량)** |
| 18:00 | thesis-update-readings | default | **FMP/FRED** (지표 대량) |
| 18:15 | classify-news-batch | default | **Gemini** |
| 18:15 | thesis-calculate-scores | default | (DB) |
| 18:30 | update-sp500-change-percent | default | (DB) |
| 18:30 | run-eod-pipeline | default | (DB, 14 시그널) |
| 18:30 | thesis-create-snapshots | default | (DB + Email) |
| 18:30 | analyze-news-deep-batch | default | **Gemini** |
| 18:45 | sync-news-to-neo4j | **neo4j** | (Neo4j) |
| 19:00 | collect-ml-labels | default | (DB) |
| 19:00 | backfill-signal-accuracy | default | (DB) |
| 20:00 | sync-sp500-financials | default | **FMP (101심볼/일)** |
| 22:00 | update-economic-indicators (4/4) | default | FRED |

### 1.3 매일 고정 (요일 무관)

| 시각 | 태스크 | 비고 |
|------|--------|------|
| 01:00 | update-economic-calendar | FRED |
| 04:00 | cleanup-expired-news-relationships | **neo4j queue** |
| 05:30 | enrich-relationship-keywords | **neo4j queue + Gemini (limit=100)** |
| 07:00 | chainsight-heat-score-daily | 주석 `07:00 UTC` — **시각 기준 혼재** |
| 07:00 | celery-error-digest | ET 기준 |
| 09:00 | extract-news-relations | |
| 10:00 | chainsight-co-mentions | days_back=7 |
| 11:00 | chainsight-relation-confidence | |
| 12:00 | chainsight-sync-profiles-neo4j | |
| 12:30 | chainsight-sync-relations-neo4j | |
| 13:00 | chainsight-seed-selection | 주석 `13:00 UTC` — **시각 기준 혼재** |
| 16:30 | extract-daily-news-keywords | |

### 1.4 요일/월 배치

| 시점 | 태스크 | 비고 |
|------|--------|------|
| 토 01:00 | aggregate-weekly-prices | DB 집계 |
| 토 02:00 | chainsight-all-profiles | Tier A 통합 |
| 토 03:00 | chainsight-price-co-movement | |
| 토 04:00 | chainsight-stale-decay | |
| 토 04:30 | chainsight-aggregate-profiles | |
| 토 05:00 | validation-weekly-batch | |
| 월 04:00 | scan-regulatory-relationships | |
| 월 06:00 | sync-etf-holdings | |
| 일 03:00 | cleanup-old-macro-data | |
| 일 03:00 | train-importance-model | ML |
| 일 03:30 | generate-shadow-report | |
| 일 04:00 | check-auto-deploy | |
| 일 04:15 | generate-weekly-ml-report | |
| 일 04:20 | monitor-ml-performance | |
| 일 04:30 | train-lightgbm-model | ML (CPU 부하 大) |
| 일 04:30 | chainsight-neo4j-dirty-sync | **neo4j queue** |
| 일 05:00 | cleanup-task-results | |
| 매월 1일 02:00 | sync-sp500-constituents | |
| 매월 1일 02:30 | archive-old-articles | |
| 매월 1일 03:00 | refresh-korean-overviews-monthly | **Gemini 대량** |
| 매월 1일 04:30 | build-patent-network | |
| 매월 1일 06:00 | sec-check-new-filings | SEC EDGAR |
| 매월 15일 03:00 | sync-supply-chain-batch | SEC 10-K |
| 매월 16일 04:00 | sync-institutional-holdings | 13F |

### 1.5 Neo4j 전용 (6시간 주기)

| 시각 | 태스크 |
|------|--------|
| 00/06/12/18:00 | neo4j-health-check (`hour=*/6`) |

---

## 2. Rate Limit 분석

### 2.1 FMP (Starter 300 calls/min) 🔴 CRITICAL

**분 단위 피크 지점**:

| 시각 | 동시 FMP 태스크 | 설명 |
|------|-----------------|------|
| 18:00 | 3개 + 뉴스 API | `sync-sp500-eod-prices` (500 심볼) + `thesis-update-readings` (지표 대량) + `collect-market-news-evening` + `update-economic-indicators` |
| 17:00 | 1개 | `update-daily-prices` 만 |
| 17:15/17:45 | 1개/1개 (15~45분 간격) | collect-sp500-news-fmp-1715, collect-general-news-fmp-evening |
| 06:15/06:45 | 분산 | 대체로 분리됨 |
| 09-16 시장시간 5분 주기 | 2개 | `update-realtime-prices` + `update-market-indices` |

**가장 위험**: 18:00 ET — **`sync-sp500-eod-prices`** 와 **`thesis-update-readings`** 가 동시 시작. 각각 S&P 500 전체 및 대량 지표 호출로 수백~수천 call 필요. 태스크 내부 분산 (`time.sleep`, batch API) 없이는 300/min 한도 초과 거의 확실.

**시장시간 `*/5` 호출**: `update-realtime-prices` 가 S&P 500 개별 호출이면 1회 ≈ 500 calls > 300/min. 코드상 `/stable/batch-quote` 사용 여부 검증 필요 (감사 범위 밖).

**일 총량 (추정)**: S&P 500 수준의 호출이 하루 ~100회 발생 → 100 × 500 = **50,000 calls/일** 규모. Starter 플랜 일 쿼터 (통상 250K/일) 내이나 분 단위 초과가 실질 리스크.

### 2.2 Gemini Free (15 RPM, 1500 RPD) 🔴 CRITICAL

**LLM 호출 분포**:

| 시각 | 태스크 | 추정 호출 |
|------|--------|----------|
| 05:30 | enrich-relationship-keywords (limit=100) | ~100 |
| 08:00 | keyword-generation-pipeline (gainers) | ~20 |
| 08:15/10:15/12:15/14:15/16:15/18:15 | classify-news-batch × 6 | 각 ~30~50 |
| 08:30/10:30/12:30/14:30/16:30/18:30 | analyze-news-deep-batch (50) × 6 | 각 50 |
| 16:30 | extract-daily-news-keywords | ~30 |
| 매월 1일 03:00 | refresh-korean-overviews-monthly | ~500 (월간 batch) |

**일 총 LLM 호출**: `~100 + ~20 + (30~50)×6 + 50×6 + ~30 ≈ 약 640~760 호출/일` (평일 기준).

→ Gemini Free **1500 RPD 의 ~50%** 사용. 일 쿼터는 여유.

**RPM 위험 (핵심)**:
- `analyze-news-deep-batch` 가 50건을 태스크 내부 sleep 없이 순차 호출 시, 50 call / (LLM 응답 시간 기준 수 십초) = **50 RPM 이상 → 15 RPM 의 3배 초과**.
- Gemini 429 에러 → 태스크 실패 → retry 백오프 → 다음 배치와 겹침 가능.

**16:30 LLM 2중 겹침**:
- `extract-daily-news-keywords` (매일) + `analyze-news-deep-batch` (평일) 동시 시작.
- 양쪽 모두 Gemini 사용 → 단일 태스크보다 RPM 압박 2배.

**권고**: 태스크 내부 `time.sleep(4)` (=15/min 제한) 또는 `@shared_task(rate_limit='15/m')` 적용 여부를 코드에서 재확인 필요.

### 2.3 Alpha Vantage (5 calls/min) 🟡 INFO

beat_schedule dict 에 AV 의존 명시 태스크 없음. 경제지표는 FRED, 가격은 FMP 사용. **beat 스케줄 관점에서 AV rate limit 은 문제 없음**. (온디맨드 호출 경로는 감사 범위 밖.)

---

## 3. Queue 몰림 분석

### 3.1 neo4j queue (solo pool) 🔴 CRITICAL

**고정 점유**:
- `sec-sync-dirty-neo4j`: 5분마다, **288회/일**, `expires=240s`
- `neo4j-health-check`: 6시간마다 (00/06/12/18)

**배치 점유**:
| 시각 | 태스크 |
|------|--------|
| 매일 04:00 | cleanup-expired-news-relationships |
| 매일 05:30 | enrich-relationship-keywords (100 × Gemini) |
| 평일 08:45 / 10:45 / 12:45 / 14:45 / 16:45 / 18:45 | sync-news-to-neo4j (max=100) |
| 매일 12:00 | chainsight-sync-profiles-neo4j |
| 매일 12:30 | chainsight-sync-relations-neo4j |
| 일 04:30 | chainsight-neo4j-dirty-sync |

**12:00 neo4j 3중 겹침**:
- `neo4j-health-check` (6h, 12:00)
- `chainsight-sync-profiles-neo4j` (매일 12:00)
- `sec-sync-dirty-neo4j` (*/5, 12:00)

solo pool 이므로 순차 실행. profiles 가 5분 초과하면 12:05 sec-sync 밀림 → `expires=240s` 로 **만료 폐기 가능성**.

**05:30 경합**:
- enrich-relationship-keywords 가 Gemini 15 RPM 준수 시 100 호출 × 4초 = 약 7분 소요.
- 05:35 / 05:40 sec-sync 가 밀려 expires 로 폐기될 수 있음.

**18:45 / sync-news (max=100)**:
- 100건 Neo4j 업서트 시간이 4분 초과하면 18:50 sec-sync 폐기 위험.

### 3.2 default queue 🟡 INFO

**시장시간 정각 동시 시작 (09-16)**:
- update-realtime-prices
- update-market-indices
- refresh-market-pulse-cache
- calculate-portfolio-values (10분 배수에서만)
- check-screener-alerts (15분 배수에서만)
- sec-sync-dirty-neo4j (→ neo4j queue)
- check-pipeline-alerts (30분 배수에서만)

→ 정각에 최대 **7태스크 동시 시작**. default queue 워커 concurrency 에 따라 병렬/직렬.

**18:30 4중 겹침 (CRITICAL)**:
- `update-sp500-change-percent` (DB)
- `run-eod-pipeline` (14 시그널 벡터)
- `thesis-create-snapshots` (DB + Email)
- `analyze-news-deep-batch` (Gemini)

의존 관계: `run-eod-pipeline` 이 `Stock.change_percent` 를 참조한다면 `update-sp500-change-percent` 완료 후 시작해야 한다. 같은 분 시작은 **경합 가능**.

---

## 4. 시간대별 ASCII 히트맵 (평일 기준)

### 4.1 시간별 태스크 실행 빈도 (시간당 시작 수)

`refresh-market-pulse-cache` 가 시장시간 매 1분 (60회/시간) 기여. `sec-sync-dirty-neo4j` + `check-pipeline-alerts` 는 24h 기본 (12+2 = 14회/시간).

```
시간(ET) | 실행수 | 히트맵
  00    |   14  | ███░░░░░░░░░░░░░░░░░░░░░░░░░░░
  01    |   16  | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (update-economic-calendar, 토: +aggregate-weekly)
  02    |   14~17| ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (토/매월1일 피크)
  03    |   14~22| ██████░░░░░░░░░░░░░░░░░░░░░░░░  (일 ML 2 + 토 1 + 매월1일 2, 매월15일 1)
  04    |   15~23| ██████░░░░░░░░░░░░░░░░░░░░░░░░  ★ 일요일 ML+Neo4j 6중
  05    |   15~17| ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (enrich-relationship-keywords)
  06    |   19   | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (평일 4 + 월 1 + 매월1일 1)
  07    |   17   | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (매일 2 + 평일 3)
  08    |   18   | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (평일 4 + 매일 1)
  09    |  110   | ██████████████████████████████  ★ 시장 개장
  10    |  112   | ██████████████████████████████  ★ (LLM 3회)
  11    |  109   | █████████████████████████████░  ★
  12    |  116   | ██████████████████████████████  ★ neo4j 3중 + FMP
  13    |  111   | ██████████████████████████████  ★
  14    |  113   | ██████████████████████████████  ★ 수집-분석 역순
  15    |  110   | ██████████████████████████████  ★
  16    |  114   | ██████████████████████████████  ★ 장마감 + LLM 2중
  17    |   18   | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (평일 4)
  18    |   23   | █████░░░░░░░░░░░░░░░░░░░░░░░░░  ★ 4중 겹침 (18:30)
  19    |   16   | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (평일 2)
  20    |   15   | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (평일 1)
  21    |   14   | ███░░░░░░░░░░░░░░░░░░░░░░░░░░░
  22    |   15   | ████░░░░░░░░░░░░░░░░░░░░░░░░░░  (update-economic-indicators)
  23    |   14   | ███░░░░░░░░░░░░░░░░░░░░░░░░░░░
```
(1 막대 ≈ 약 4 이벤트. 시장시간은 pulse-cache 1/분이 주 기여.)

### 4.2 분 단위 히트맵 — 시장시간 내부 (예: 10:00-10:59, 평일)

```
분  | 수 | 히트맵                  | 주요 태스크
00 | 7 | █████████████████████   | realtime, indices, pulse, portfolio, screener, sec-sync, pipeline-alerts
01 | 1 | ██                      | pulse
02 | 1 | ██                      | pulse
03 | 1 | ██                      | pulse
04 | 1 | ██                      | pulse
05 | 4 | ████████████            | realtime, indices, pulse, sec-sync
06 | 1 | ██                      | pulse
07 | 1 | ██                      | pulse
08 | 1 | ██                      | pulse
09 | 1 | ██                      | pulse
10 | 5 | ███████████████         | realtime, indices, pulse, portfolio, sec-sync
11 | 1 | ██                      | pulse
12 | 1 | ██                      | pulse
13 | 1 | ██                      | pulse
14 | 1 | ██                      | pulse
15 | 6 | ██████████████████      | realtime, indices, pulse, screener, sec-sync, (매시간별 classify 15분 → 10:15)
16 | 1 | ██                      | pulse
17 | 1 | ██                      | pulse
18 | 1 | ██                      | pulse
19 | 1 | ██                      | pulse
20 | 5 | ███████████████         | realtime, indices, pulse, portfolio, sec-sync
21 | 1 | ██                      | pulse
22 | 1 | ██                      | pulse
23 | 1 | ██                      | pulse
24 | 1 | ██                      | pulse
25 | 4 | ████████████            | realtime, indices, pulse, sec-sync
26 | 1 | ██                      | pulse
27 | 1 | ██                      | pulse
28 | 1 | ██                      | pulse
29 | 1 | ██                      | pulse
30 | 8 | ████████████████████████| ★ realtime, indices, pulse, portfolio, screener, sec-sync, pipeline-alerts, analyze-news-deep (10:30)
31 | 1 | ██                      | pulse
32 | 1 | ██                      | pulse
33 | 1 | ██                      | pulse
34 | 1 | ██                      | pulse
35 | 4 | ████████████            | realtime, indices, pulse, sec-sync
36 | 1 | ██                      | pulse
37 | 1 | ██                      | pulse
38 | 1 | ██                      | pulse
39 | 1 | ██                      | pulse
40 | 5 | ███████████████         | realtime, indices, pulse, portfolio, sec-sync
41 | 1 | ██                      | pulse
42 | 1 | ██                      | pulse
43 | 1 | ██                      | pulse
44 | 1 | ██                      | pulse
45 | 6 | ██████████████████      | realtime, indices, pulse, screener, sec-sync, sync-news-to-neo4j(10:45)
46 | 1 | ██                      | pulse
47 | 1 | ██                      | pulse
48 | 1 | ██                      | pulse
49 | 1 | ██                      | pulse
50 | 4 | ████████████            | realtime, indices, pulse, sec-sync
51-54 | pulse
55 | 4 | ████████████            | realtime, indices, pulse, sec-sync
```

### 4.3 18시 내부 히트맵 (EOD 피크)

```
분 | 수 | 히트맵                    | 태스크
00 | 5 | ███████████████           | update-economic-indicators(FRED), collect-market-news-evening, sync-sp500-eod-prices(FMP), thesis-update-readings(FMP), sec-sync
05 | 1 | ██                        | sec-sync
10 | 1 | ██                        | sec-sync
15 | 3 | █████████                 | classify-news-batch(Gemini), thesis-calculate-scores, sec-sync
20 | 1 | ██                        | sec-sync
25 | 1 | ██                        | sec-sync
30 | 6 | ██████████████████        | ★ update-sp500-change-percent, run-eod-pipeline, thesis-create-snapshots, analyze-news-deep(Gemini), sec-sync, check-pipeline-alerts
35 | 1 | ██                        | sec-sync
40 | 1 | ██                        | sec-sync
45 | 2 | ██████                    | sync-news-to-neo4j(neo4j), sec-sync
50 | 1 | ██                        | sec-sync
55 | 1 | ██                        | sec-sync
```

**18:00 과 18:30 이 하루 최대 밀집도**.

### 4.4 일요일 04시 ML 체인

```
분 | 태스크                                   | 큐
00 | cleanup-expired-news-relationships       | neo4j
00 | check-auto-deploy                        | default
15 | generate-weekly-ml-report                | default
20 | monitor-ml-performance                   | default
30 | train-lightgbm-model                     | default (CPU 부하 大)
30 | chainsight-neo4j-dirty-sync              | neo4j
```

`train-lightgbm-model` + `chainsight-neo4j-dirty-sync` 동시 시작. LightGBM 은 멀티코어 CPU 점유 → 시스템 부하 피크.

---

## 5. 스케줄 겹침 / 의존성 이슈

### 5.1 🔴 CRITICAL — 18:30 4중 겹침

| 태스크 | 선행 의존 | 리스크 |
|--------|----------|--------|
| update-sp500-change-percent | sync-sp500-eod-prices (18:00) | 30분 여유, OK |
| run-eod-pipeline | sync-sp500-eod-prices + **update-sp500-change-percent** | 같은 분 시작 — **change_percent 갱신 전 참조 가능** |
| thesis-create-snapshots | thesis-calculate-scores (18:15) | 15분 여유, OK |
| analyze-news-deep-batch | 독립 | Gemini + default queue 점유 |

**핵심**: `run-eod-pipeline` 가 `Stock.change_percent` 에 의존한다면 같은 18:30 시작은 race 이다. 의존성 직렬화 (예: chord, chain) 또는 시각 분리 (18:35) 필요.

### 5.2 🔴 CRITICAL — 18:00 FMP 3중 동시

- `sync-sp500-eod-prices` (S&P 500 대량)
- `thesis-update-readings` (지표 대량)
- `collect-market-news-evening` (뉴스 API, FMP 사용 가능)
- (FRED) `update-economic-indicators`

FMP Starter 300/min 한도에서 **분 단위 초과 거의 확실**. 내부 batch API + sleep 전략 없이는 429 에러 다발.

### 5.3 🔴 CRITICAL — 12:00 neo4j 3중

- `neo4j-health-check` (6h, 12:00)
- `chainsight-sync-profiles-neo4j` (12:00)
- `sec-sync-dirty-neo4j` (*/5, 12:00)
- 이어 12:30 `chainsight-sync-relations-neo4j`

solo pool 에서 순차 실행. profiles + relations 배치가 각 수 분 소요 시 그 사이 sec-sync 가 `expires=240s` 로 폐기. **데이터는 dirty 플래그로 복구 가능**하나 **실행 누락 로그 증가**.

### 5.4 🟠 WARNING — 14:30 수집-분석 역순

- `collect-daily-news-afternoon` (14:30) + `analyze-news-deep-batch` (14:30) 동시.
- 14:30 analyze 는 직전 classify (14:15) 기준 이전 배치 처리 → 논리 경합은 낮음.
- 그러나 **14:30 수집분은 classify 를 16:15 까지, analyze 를 16:30 까지 대기** → 처리 지연.

### 5.5 🟠 WARNING — 16:30 LLM 2중

- `extract-daily-news-keywords` (매일) + `analyze-news-deep-batch` (평일) 동시 시작.
- Gemini RPM 경합.

### 5.6 🟠 WARNING — 시각 기준 EST/UTC 혼재

`CELERY_TIMEZONE = 'America/New_York'` 이므로 `crontab(hour=7)` 은 ET 07:00 이다. 그러나 아래 2개 태스크 주석은 UTC 로 표기:

- `chainsight-heat-score-daily`: 주석 "매일 07:00 UTC" — 실제 ET 07:00 실행 (UTC 기준 11:00~12:00 with DST)
- `chainsight-seed-selection`: 주석 "매일 13:00 UTC" — 실제 ET 13:00 실행

→ **주석과 실제 실행시각 불일치**. 주석 의도는 UTC 07:00 (= ET 03:00 EST / 02:00 EDT) 였을 가능성. **주석 수정 또는 crontab 수정 필요** (감사 범위 밖, 별도 PR).

### 5.7 🟠 WARNING — 05:30 enrich → 05:35 sec-sync 폐기

- `enrich-relationship-keywords` (limit=100, Gemini rate-limit 준수 시 ~7분).
- neo4j queue solo pool → 05:35 `sec-sync-dirty-neo4j` 가 밀림 → `expires=240s` 초과 → 폐기.
- 05:40 sec-sync 도 밀릴 가능. **연쇄 skip**.

### 5.8 🟠 WARNING — 일요일 04시 ML 체인 부하

- 04:00 cleanup(neo4j) + check-auto-deploy(default) 병렬
- 04:15 / 04:20 / 04:30 까지 ML 태스크 연쇄
- 04:30 LightGBM + Neo4j dirty sync 동시 → CPU + Neo4j 동시 부하

### 5.9 🟠 WARNING — 08:00 market-movers 선행 의존

- `sync-daily-market-movers` (07:30) → `keyword-generation-pipeline` (08:00, mover_type='gainers')
- 30분 여유. 07:30 FMP batch 가 지연되면 08:00 에 빈/불완전 mover 로 Gemini 호출.

### 5.10 🟡 INFO — 토요일 Chain Sight 선형 체인 (정상)

```
02:00 chainsight-all-profiles
03:00 chainsight-price-co-movement
04:00 chainsight-stale-decay
04:30 chainsight-aggregate-profiles
05:00 validation-weekly-batch
```

각 1시간 (또는 30분) 여유. 선형. 정상 설계.

### 5.11 🟡 INFO — 뉴스 v3 파이프라인 (정상)

`hour='8,10,12,14,16,18'` 공통:
- :15 classify (Gemini)
- :30 analyze (Gemini)
- :45 sync-to-neo4j (neo4j queue)

각 15분 간격. 정상 설계. 단 RPM/큐 압박은 섹션 2.2 / 3.1 참조.

---

## 6. 권고 (읽기 전용, 코드 변경 없음)

### 6.1 즉시 조사 필요 (P0)

1. **Gemini 태스크 내부 rate-limit 존재 여부 코드 확인**
   - `analyze-news-deep-batch` 50건 순차 호출 시 15 RPM 준수 확인.
   - `enrich-relationship-keywords` 100건 순차 호출 확인.
   - `classify-news-batch`, `extract-daily-news-keywords` 확인.
2. **FMP 18:00 호출 패턴**: `sync-sp500-eod-prices` / `thesis-update-readings` 가 `/stable/batch-quote` 등 묶음 API 사용 여부.
3. **`run-eod-pipeline` 의 `Stock.change_percent` 의존성**: 18:30 동시 시작이 race 인지 분석.
4. **주석 UTC/ET 불일치**: `chainsight-heat-score-daily` / `chainsight-seed-selection` 의 주석 의도 재확인.

### 6.2 스케줄 재배치 후보 (P1)

- `analyze-news-deep-batch` 16:30 → 16:50 (LLM 2중 해소)
- `run-eod-pipeline` 18:30 → 18:35 (change_percent 직렬화)
- `thesis-update-readings` 18:00 → 18:05 (FMP 피크 분리)
- `sec-sync-dirty-neo4j` `*/5` → `*/10` (neo4j 압박 감소 + expires 폐기 감소)

### 6.3 워커 구성 변경 후보 (P2)

- neo4j queue 전용 워커 2개 (`--pool=solo --concurrency=1` 프로세스 2개).
- default queue 워커 concurrency 를 18:30 4중 기준 재산정.

### 6.4 모니터링 권고 (P3)

- `expires` 만료 폐기 태스크 카운트 주간 보고서 포함.
- FMP/Gemini 분당 호출수 Redis 카운터 + 대시보드.
- neo4j queue 대기 길이 실시간 모니터링.

---

## 7. Drift 점검 (PeriodicTask DB ↔ config dict)

`config/celery.py` L129~L133 주석에 2026-04-24 복구 기록:
> 누락 상태였던 두 태스크를 DB에 등록 완료
> - chainsight-heat-score-daily (NY 07:00, 시드 선정 전)
> - sec-seed-relations-to-chainsight (NY 12:00, 시드 선정 전)

본 감사는 DB 조회 미수행 (읽기 전용 dict 분석). **야간 자동 감사에 drift 체크 루틴 포함 권고**:

```python
# 읽기 전용 체크 (예시)
from django_celery_beat.models import PeriodicTask
from config.celery import app

db_names = set(PeriodicTask.objects.values_list('name', flat=True))
dict_names = set(app.conf.beat_schedule.keys())

print("DB에 없음 (실행 안됨):", dict_names - db_names)
print("dict에 없음 (문서화 누락):", db_names - dict_names)
```

---

## 8. 부록 — 태스크 통계

| 분류 | 수 |
|------|----|
| 주기형 (`*/N` 분) | 7 |
| 평일 시간 고정 | 40+ |
| 매일 고정 (요일 무관) | 11 |
| 주간 배치 (토/일/월) | 14 |
| 월간 배치 (매월 1/15/16일) | 7 |
| Neo4j queue 전용 | 9 |
| **총** | **68** |

| 큐 | 수 |
|----|----|
| default | 59 |
| **neo4j** | **9** |

| API 의존 (추정) | 수 |
|-----------------|----|
| FMP | 14 |
| Gemini | 10 |
| FRED | 4 |
| Neo4j | 9 |

---

**보고서 종료**. 코드는 수정하지 않았다.
