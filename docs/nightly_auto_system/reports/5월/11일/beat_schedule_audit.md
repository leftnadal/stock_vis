# Celery Beat Schedule 감사 보고서

**감사 일자**: 2026-05-12
**감사 범위**: `config/celery.py` `app.conf.beat_schedule` 전체
**감사 모드**: 읽기 전용 (코드 수정 없음)
**총 등록 태스크 수**: 86개 (schedule 키 90개에서 task_routes 4개 제외)
**Beat Scheduler**: `django_celery_beat.schedulers:DatabaseScheduler` (DB가 진실의 소스, dict는 reference)
**Celery 타임존**: `America/New_York` (NYSE/EST/EDT 기준)
**비고**: `CLAUDE.md`의 일반적 가독성 표기는 EST이며, 본 보고서 시각 표기는 모두 EST/EDT (NY local) 기준이다.

---

## 1. Executive Summary — 위험도 매트릭스

| # | 위험 | 심각도 | 발생 빈도 | 비고 |
|---|------|--------|-----------|------|
| 1 | **18:30~18:35 EST Gemini 동시 호출** (analyze-news-deep-batch + thesis-generate-summaries) | **HIGH** | 평일 매일 | audit P0 #8(16:30/16:45)과 동일 패턴 재발. 5분 간격이 너무 짧다 |
| 2 | **18:00 EST FMP 5중 폭주** (sync-sp500-eod-prices 500종목 + thesis-update-readings + update-economic-indicators + collect-market-news-evening + 17:45 잔여) | **HIGH** | 평일 매일 | 단일 분에 4개 FMP 의존 태스크 동시 트리거 |
| 3 | **enrich-relationship-keywords (05:30 daily) → sec-sync-dirty-neo4j 대량 만료** | **HIGH** | 매일 05:30~05:40 | Gemini 100건 배치 = 6~7분 이상, 같은 neo4j queue + expires=240s |
| 4 | **17:15 EST 500종목 FMP news + 17:45 general-news-fmp + 18:00 EOD prices** | **MEDIUM** | 평일 매일 | 90분 동안 FMP 1000+ 호출 가능성 |
| 5 | **Sunday 04:00~04:30 EST 11+개 태스크 폭주** (월·주·일 배치 중첩) | **MEDIUM** | 매주 일요일 | default queue 동시 실행 부하 |
| 6 | **timezone 표기 drift** — `chainsight-heat-score-daily/-seed-selection/-neo4j-dirty-sync` 주석은 "UTC"이지만 실제 EST | **LOW** | 영구 | 운영자 오인 위험. 실행 시각은 정상 |
| 7 | **sec-sync-dirty-neo4j expires=240s vs schedule=300s** 미스매치 | **LOW** | 늘 | 4분 안에 픽업 안 되면 데이터 누적 후 다음 사이클 처리. 워커 다운 시 데이터 갱신 지연 |
| 8 | **Sunday 03:00 monthly Gemini 폭주** — refresh-korean-overviews-monthly (S&P 500 대량 호출) + train-importance-model | **LOW** | 매월 1일 일요일 | 일치 시 부하 집중 (월 1회) |

> Alpha Vantage(5 calls/min)에 의존하는 Beat 태스크는 **0개**. Beat 자체에는 AV 위험 없음 (온디맨드 엔드포인트만 사용).

---

## 2. 시간대별 부하 히트맵 (EST, 평일 기준)

### 2.1 종합 부하 (단위: 시간당 invocation 수)

범례: `░` 0~3 · `▒` 4~10 · `▓` 11~30 · `█` 31+

```
시각  태스크수  분포
00시  ▓ 15     [neo4j-health, sec-sync×12, alerts×2]
01시  ▓ 15     [update-economic-calendar, sec-sync×12, alerts×2]
02시  ▓ 14     [sec-sync×12, alerts×2  (+monthly: sp500-constituents, archive-old, chainsight-all-profiles Sat)]
03시  ▓ 14     [sec-sync×12, alerts×2  (+Sun: cleanup-old-macro, train-importance, generate-shadow)
                                       (+ month=1: refresh-korean-overviews ← Gemini bulk)
                                       (+ month=15: sync-supply-chain-batch)
                                       (+ Sat: chainsight-price-co-movement)]
04시  ▓ 15     [cleanup-expired-news (neo4j), sec-sync×12, alerts×2
                +Sun: check-auto-deploy, gen-weekly-ml, monitor-ml, train-lightgbm, neo4j-dirty-sync
                +Mon: scan-regulatory-relationships
                +Sat: chainsight-stale-decay, chainsight-aggregate-profiles
                +month=16: sync-institutional-holdings  +month=1: build-patent-network]
05시  ▓ 15     [enrich-relationship-keywords (Gemini+neo4j), sec-sync×12, alerts×2
                +Sun: cleanup-task-results  +Sat: validation-weekly-batch]
06시  ▓ 19     [neo4j-health, collect-daily-news-morning, collect-sp500-news-0615 (FMP×500),
                collect-category-high-morning, collect-general-news-fmp-morning (FMP),
                sec-sync×12, alerts×2  +Mon: sync-etf-holdings (FMP)
                +month=1: sec-check-new-filings]
07시  ▓ 21     [celery-error-digest, chainsight-heat-score, collect-category-medium-morning,
                collect-category-low, sync-daily-market-movers (FMP), collect-press-releases (FMP×50),
                sec-sync×12, alerts×2]
08시  ▓ 19     [keyword-gen (Gemini), collect-market-news, classify-news (Gemini),
                analyze-deep (Gemini), sync-news-neo4j, sec-sync×12, alerts×2]
09시  █ 110    ★ market-pulse×60 + realtime×12(FMP) + indices×12(FMP) + portfolio×6
                + screener×4 + aggregate-sentiment + extract-news-relations + sec×12 + alerts×2
10시  █ 113    market periodic ×94 + chainsight-co-mentions + collect-sp500-news-1015 (FMP×500)
                + classify-news + analyze-deep + sync-news-neo4j + sec×12 + alerts×2
11시  █ 109    market periodic ×94 + chainsight-relation-confidence + sec×12 + alerts×2
12시  █ 117    market periodic ×94 + update-econ-indicators + collect-market-news-noon
                + chainsight-sync-profiles-neo4j + sec-seed-relations + classify-news + analyze-deep
                + collect-general-news-fmp-noon (FMP) + chainsight-sync-relations-neo4j
                + sync-news-neo4j + sec×12 + alerts×2
13시  █ 108    market periodic ×94 + collect-category-high-midday + chainsight-seed-selection
                + collect-sp500-news-1315 (FMP×500) + sec×12 + alerts×2
14시  █ 112    market periodic ×94 + collect-category-medium-afternoon + classify-news
                + collect-daily-news-afternoon + analyze-deep + sync-news-neo4j + sec×12 + alerts×2
15시  █ 107    market periodic ×94 + collect-market-news-afternoon + collect-sp500-news-1515 (FMP×500)
                + sec×12 + alerts×2
16시  █ 115    market periodic ×94 + classify-news + analyze-deep + calculate-market-breadth
                + calculate-sector-heatmap + extract-daily-news-keywords (Gemini)
                + sync-news-neo4j + sec×12 + alerts×2
17시  ▓ 18     [update-daily-prices (FMP), collect-category-high-evening,
                collect-sp500-news-1715 (FMP×500), collect-general-news-fmp-evening (FMP),
                sec×12, alerts×2]
18시  ▓ 28  ⚠  [update-econ-indicators, collect-market-news-evening, thesis-update-readings,
                ★ sync-sp500-eod-prices (FMP×500),
                thesis-calculate-scores, classify-news (Gemini, 18:15),
                ★ analyze-deep (Gemini, 18:30) + run-eod-pipeline + thesis-create-snapshots
                + update-sp500-change-percent (18:30),
                ★ thesis-generate-summaries (Gemini, 18:35) ←★ 18:30과 5분 간격
                sync-news-neo4j (18:45), sec×12, alerts×2]
19시  ▓ 16     [collect-ml-labels, backfill-signal-accuracy, sec×12, alerts×2]
20시  ▓ 15     [sync-sp500-financials (FMP×101), sec×12, alerts×2]
21시  ▓ 14     [sec×12, alerts×2]
22시  ▓ 15     [update-economic-indicators, sec×12, alerts×2]
23시  ▓ 14     [sec×12, alerts×2]
```

### 2.2 FMP 호출량 추정 (시간당, 평일)

FMP Starter Plan 한도: **300 calls/min · 10,000 calls/일**

```
시각  추정 calls  비율(1일 한도) 핫스팟
00시       0       0%
01시       0       0%
02시       0       0%  (+monthly: sp500-constituents +1)
03시       0       0%  (+month=1: refresh-korean-overviews Gemini만)
04시       0       0%
05시       0       0%
06시     ~501     5%   ★ collect-sp500-news-fmp-0615 (500) + general-news-fmp-morning + Mon ETF
07시      ~52     0.5% sync-daily-market-movers + press-releases (50)
08시       0       0%
09시   ~150~200    2%  realtime+indices (every 5 min × 12) × n stocks (시장시간 시작)
10시   ~650+      6.5% market periodic + collect-sp500-news-fmp-1015 (500)
11시   ~150       1.5% market periodic
12시   ~155       1.5% market periodic + general-news-fmp-noon
13시   ~650+      6.5% market periodic + collect-sp500-news-fmp-1315 (500)
14시   ~150       1.5% market periodic
15시   ~650+      6.5% market periodic + collect-sp500-news-fmp-1515 (500)
16시   ~150       1.5% market periodic 마지막 시간 (16:55까지)
17시  ~502      5%   ⚠ update-daily-prices + collect-sp500-news-fmp-1715 (500) + general-news-fmp-evening
18시  ~500+     5%+  ★★ sync-sp500-eod-prices (500) + thesis-update-readings
19시       0       0%
20시     ~101     1%   sync-sp500-financials (S&P 500 5일 순환 101개)
21시       0       0%
22시       0       0%
23시       0       0%
```

**일일 합계 추정**: 약 3,800~4,200 calls (10,000 한도 대비 38~42%) — 한도 자체는 여유.
**문제는 분당 분포**: `sync-sp500-eod-prices` 500종목이 `REQUEST_DELAY=0.3s`로 호출되면 ≈ **200 calls/min**. 여기에 `thesis-update-readings`가 동일 분에 시작하면 300 calls/min 초과 가능. **두 태스크는 독립된 워커에서 실행되므로 공유 rate limiter가 없으면 충돌**.

### 2.3 Gemini 호출 분포 (15 RPM · 1,500 RPD)

```
시각   배치                              호출 추정    리스크
05:30  enrich-relationship-keywords      ~100         단독, 6~7분 소요 예상
08:00  keyword-generation-pipeline       ~10~30       단독 시작 → 15분 후 다음 호출
08:15  classify-news-batch               ~20~50       단독
08:30  analyze-news-deep-batch (50건)    ~50          단독
10:15  classify-news-batch               ~20~50       단독
10:30  analyze-news-deep-batch           ~50          단독
12:15  classify-news-batch               ~20~50       단독
12:30  analyze-news-deep-batch           ~50          단독
14:15  classify-news-batch               ~20~50       단독
14:30  analyze-news-deep-batch           ~50          단독
16:15  classify-news-batch               ~20~50       단독
16:30  analyze-news-deep-batch           ~50          ✔ 16:45와 15분 간격 (P0 #8 해소)
16:45  extract-daily-news-keywords       ~30          ✔
18:15  classify-news-batch               ~20~50       단독
18:30  analyze-news-deep-batch (50건)    ~50          ★ 5분 후 thesis-summaries
18:35  thesis-generate-summaries         ~10~50       ★ 18:30과 동일 5분 window
03:00  refresh-korean-overviews-monthly  ~500 (월1)   ※ 월별, RPM_DELAY=4초 자체 제한 확인 필요
```

**일일 합계 추정** (월 1회 batch 제외): 약 600~900건 / 1,500 RPD 한도 → **40~60% 사용**. 한도 자체 여유.

⚠ **18:30↔18:35 (5분 간격)**: 두 태스크가 같은 분에 첫 호출을 만들면 60초 내 다수의 Gemini call이 발생할 수 있다. P0 #8에서 16:30↔16:45를 15분으로 분리한 동일 문제가 다른 시간대에서 재발한 상태.

---

## 3. Queue 부하 분석

### 3.1 default queue

가장 큰 부담은 시장시간(9~16시) 매 분마다 작동하는 cron이 동시 트리거되는 것.

**매 정시 시작 시점 (HH:00, 9-16시)에 동시 발화하는 cron**:
1. `refresh-market-pulse-cache` (매분)
2. `update-realtime-prices` (5분 간격, HH:00에 발화)
3. `update-market-indices` (5분 간격, HH:00에 발화)
4. `calculate-portfolio-values` (10분 간격, 짝수 정시 발화)
5. `check-screener-alerts` (15분 간격)
6. `check-pipeline-alerts` (30분 간격, HH:00·HH:30)
7. (그 외 1시간/2시간 정시 발화 태스크들)

→ 시장시간 6개+의 태스크가 동일 epoch에 producer에 enqueue됨. macOS solo pool에서는 직렬 처리. Linux prefork에서는 동시 worker 수만큼 병렬화. **worker concurrency가 6 미만이면 매분 큐 적체.**

### 3.2 neo4j queue (solo pool · 동시 1개)

**고정 트래픽** (24시간):
- `sec-sync-dirty-neo4j` 매 5분: 288회/일 (expires=240s)

**스파이크 (평일)**:
- `neo4j-health-check`: 4회/일 (00:00, 06:00, 12:00, 18:00)
- `sync-news-to-neo4j`: 6회/일 (08:45, 10:45, 12:45, 14:45, 16:45, 18:45) — max 100건
- `chainsight-sync-profiles-neo4j`: 12:00 daily
- `chainsight-sync-relations-neo4j`: 12:30 daily
- `cleanup-expired-news-relationships`: 04:00 daily
- `enrich-relationship-keywords`: 05:30 daily (Gemini 100건 = **6~7분 소요 예상**)

**충돌/만료 시나리오 분석**:

```
시각         사건                                                    sec-sync 5분 슬롯  영향
05:30:00     enrich-relationship-keywords 시작 (6~7분 예상)         05:30, 05:35 슬롯  ★ 2회 expire 가능
12:00:00     chainsight-sync-profiles-neo4j                          12:00, 12:05 슬롯   ※ 길면 expire
12:30:00     chainsight-sync-relations-neo4j                         12:30, 12:35 슬롯   ※ 길면 expire
HH:45 (×6)   sync-news-to-neo4j (100건)                              HH:45 슬롯          ※ 길면 expire
04:00:00     cleanup-expired-news-relationships                      04:00, 04:05 슬롯   ※ 길면 expire
```

**핵심 위험**: `sec-sync-dirty-neo4j`는 `expires=240s` (4분). schedule은 5분. 즉 워커가 다음 사이클까지 픽업하지 못하면 만료되어 **그 사이클의 dirty evidence는 다음 5분 후에야 처리**된다. solo pool에서 다른 neo4j 태스크가 4분 넘게 점유하면 발생.

`enrich-relationship-keywords`는 Gemini 15 RPM × 100건 = 최소 **6.67분** 소요 — 사실상 보장된 만료.

### 3.3 Queue 분리 권고 후보 (참고용, 본 보고서는 실행 없음)

- 장시간 neo4j 배치(`enrich-relationship-keywords`, `chainsight-sync-*-neo4j`)를 별도 queue(`neo4j-bulk`)로 분리하면 `sec-sync-dirty-neo4j`의 4분 SLA 확보 가능.
- 또는 `sec-sync-dirty-neo4j` schedule을 매 10분으로 완화 + expires=540s로 정렬.

---

## 4. 시간대별 동시 발화 ASCII 히트맵 (5분 해상도 · 평일 EST)

범례: 셀당 동시 발화 cron 개수
`.` 0 · `1`~`9` 개수 · `+` 10개 이상

```
        :00  :05  :10  :15  :20  :25  :30  :35  :40  :45  :50  :55
00시     2    1    1    1    1    1    2    1    1    1    1    1
01시     3    1    1    1    1    1    2    1    1    1    1    1
02시     2    1    1    1    1    1    2    1    1    1    1    1
03시     2    1    1    1    1    1    2    1    1    1    1    1
04시     3    1    1    1    1    1    2    1    1    1    1    1
05시     2    1    1    1    1    1    3    1    1    1    1    1
06시     4    1    1    3    1    1    3    1    1    2    1    1
07시     4    1    1    1    1    1    4    1    1    3    1    1
08시     4    1    1    3    1    1    3    1    1    3    1    1
09시     8    7    7    7    8    7    7    7    7    7    7    7
10시     8    7    7    9    7    7    9    7    7    8    7    7
11시     8    7    7    7    7    7    7    7    7    7    7    7
12시     +    7    7    9    7    7    +    7    7    8    7    7
13시     8    7    7    9    7    7    8    7    7    7    7    7
14時     8    7    7    9    7    7    9    7    7    8    7    7
15時     8    7    7    9    7    7    8    7    7    7    7    7
16時     7    7    7    9    7    7    +    9    7    +    7    7
17時     4    1    1    3    1    1    3    1    1    2    1    1
18時  ★ 6    1    1  ★3    1    1  ★5  ★2    1    3    1    1
19시     4    1    1    1    1    1    2    1    1    1    1    1
20시     3    1    1    1    1    1    2    1    1    1    1    1
21시     2    1    1    1    1    1    2    1    1    1    1    1
22시     3    1    1    1    1    1    2    1    1    1    1    1
23시     2    1    1    1    1    1    2    1    1    1    1    1
```

> 위 표는 schedule이 **트리거**되는 동시 개수이며, 실제 처리 시간(태스크 duration)은 별도. 시장시간(9-16시) 매분 1회 발화 cron(refresh-market-pulse-cache)은 모든 셀에 포함. 5분/10분/15분 단위 cron은 해당 분에만 가산. 시장시간 :15 슬롯이 :00보다 큰 이유: classify-news + collect-sp500-news-fmp-1515 등 다양한 :15 cron이 모이기 때문.

**핫스팟**:
- **9-16시 시장시간 전반**: 매분 7~9개 cron 발화 (대부분 internal cache 갱신이지만 producer 작업량 증가)
- **12:00 / 16:30 / 18:00**: 10+ cron 동시 발화
- **18:00 / 18:30 / 18:35**: EOD 파이프라인 직렬 의존 + Gemini 두 태스크 5분 간격 ⚠

---

## 5. 스케줄 의존성 / 데이터 경합

### 5.1 EOD 직렬 체인 (평일 18:00~19:00)

```
18:00 ┌─ thesis-update-readings (FMP)          ─┐
      ├─ sync-sp500-eod-prices (FMP×500)       ─┤
      └─ update-economic-indicators (FRED)      │
                                                ▼
18:15 ┌─ thesis-calculate-scores                ◀── depends on 18:00 thesis-update-readings
      └─ classify-news-batch (Gemini)
                                                ▼
18:30 ┌─ thesis-create-snapshots                ◀── depends on thesis-calculate-scores
      ├─ analyze-news-deep-batch (Gemini, 50건) │
      ├─ run-eod-pipeline                       ◀── depends on sync-sp500-eod-prices
      └─ update-sp500-change-percent
                                                ▼
18:35 └─ thesis-generate-summaries (Gemini)     ◀── depends on thesis-create-snapshots (← only 5 min)
                                                ▼
18:45 └─ sync-news-to-neo4j (neo4j queue, 100건)
                                                ▼
19:00 └─ backfill-signal-accuracy               ◀── depends on run-eod-pipeline
```

**위험점**:
1. `sync-sp500-eod-prices` 500종목이 30분 안에 완료되지 못하면 `run-eod-pipeline`이 stale 데이터로 시작.
2. `thesis-update-readings` (18:00) → `thesis-calculate-scores` (18:15) 의존성: 15분 안에 FMP 호출이 완료되어야 함. FMP rate limit hit + retry 시 위태.
3. `thesis-create-snapshots` (18:30) → `thesis-generate-summaries` (18:35): 5분만에 스냅샷 생성 + Gemini 요약 generation 완료 가정. snapshot 미완료 시 summaries는 빈 결과나 stale 데이터로 동작.
4. `analyze-news-deep-batch` (18:30, Gemini)와 `thesis-generate-summaries` (18:35, Gemini): **15 RPM 한도 공유 — P0 #8과 동일 패턴 재발**.

### 5.2 뉴스 분류 → Neo4j 파이프라인 (평일 매 2시간)

```
HH:15 classify-news-batch (Gemini)     → news 분류 결과 DB 저장
HH:30 analyze-news-deep-batch (Gemini) → 분류된 기사 50건 심층 분석
HH:45 sync-news-to-neo4j (neo4j queue) → 분석 결과 Neo4j 동기화
```

각 단계 사이 15분 간격이라 정상 처리 시에는 무난하나, `sync-news-to-neo4j`가 100건 처리하면서 4분 초과 시 **그 시각의 `sec-sync-dirty-neo4j`(HH:45 트리거)가 만료**.

### 5.3 Chain Sight Neo4j 동기화 (매일 12:00~12:30)

```
12:00 chainsight-sync-profiles-neo4j  ─┐
                                       ├─ solo pool 직렬화
12:30 chainsight-sync-relations-neo4j ─┘
```

12:00 sync-profiles가 30분 이상 걸리면 sync-relations 시작 지연 + 그 사이 `sec-sync-dirty-neo4j`(12:00, 12:05, 12:10, ..., 12:25) 모두 expire.

### 5.4 일요일 04:00~04:30 ML 파이프라인

```
03:00 train-importance-model
03:30 generate-shadow-report (depends on 03:00)
04:00 check-auto-deploy        (depends on 03:30)
04:00 cleanup-expired-news-relationships (neo4j queue, daily)
04:00 scan-regulatory-relationships (default queue, Mon — 일요일 아님 ✔)
04:15 generate-weekly-ml-report (depends on 04:00 check-auto-deploy)
04:20 monitor-ml-performance   (depends on 04:15)
04:30 train-lightgbm-model     (depends on prior 5 steps)
04:30 chainsight-neo4j-dirty-sync (neo4j queue, Sun)
```

직렬 의존 5단계가 30분 안에 완료되어야 함. ML 학습/리포트 어느 한 단계라도 지연되면 04:30 LightGBM이 stale 데이터 사용. cleanup-expired-news + chainsight-neo4j-dirty-sync가 같은 시간대 neo4j queue에 들어와 04:30~05:00 사이 `sec-sync-dirty-neo4j` 다수 expire.

---

## 6. Timezone 표기 drift (LOW)

`CELERY_TIMEZONE='America/New_York'`이므로 모든 cron은 NY local 시각. 하지만 일부 주석은 "UTC"로 표기되어 있다. **실행은 정상**, 문서 일관성만 문제.

| 태스크 | 주석 | 실제 (NY local) | UTC 환산 (Summer/EDT) |
|--------|------|----------------|---------------------|
| `chainsight-heat-score-daily` | "매일 07:00 UTC" | 07:00 EDT | 11:00 UTC |
| `chainsight-seed-selection` | "매일 13:00 UTC" | 13:00 EDT | 17:00 UTC |
| `chainsight-neo4j-dirty-sync` | "매주 일요일 04:30 UTC" | 04:30 EDT 일요일 | 08:30 UTC |

운영자가 UTC 기준으로 디버깅 시 4~5시간 오차로 오인할 수 있다. **수정 권고**: 주석을 "EST/EDT"로 통일.

---

## 7. 핵심 권고 (실행은 별도 PR 필요)

> 본 감사는 읽기 전용이며, 아래는 권고만 기재.

### P0 (즉시)
1. **`thesis-generate-summaries` 시각을 18:35 → 18:50으로 이동** — `analyze-news-deep-batch`(18:30)와 15분 이상 간격 확보. P0 #8과 동일 원칙 적용.
2. **`sync-sp500-eod-prices`와 `thesis-update-readings`의 FMP rate limit 공유** — 별도 워커에서 실행되면 분당 합산 호출이 300 초과 가능. 공유 rate limiter(예: Redis 기반 token bucket) 또는 시간 분리(18:00 ↔ 18:10).

### P1 (다음 sprint)
3. **`sec-sync-dirty-neo4j` expires를 540s로 늘리거나 schedule을 10분으로 완화** — 현재 `expires=240s < schedule=300s` 미스매치 해소.
4. **장시간 neo4j 배치 분리** — `enrich-relationship-keywords` (6~7분)는 `neo4j-bulk` 등 별도 queue로 격리하여 `sec-sync-dirty-neo4j`의 4분 SLA 보장.
5. **타임존 주석 통일** — "UTC" 주석 3개를 "EST" 또는 "EDT"로 수정.

### P2 (관찰)
6. **시장시간 매분 발화 `refresh-market-pulse-cache` 부하 측정** — 현재 cache hit ratio와 worker concurrency 모니터링. concurrency=4 미만이면 큐 적체.
7. **18:00 EST 5중 트리거 단계화** — 가능하면 thesis-update-readings를 17:50으로, sync-sp500-eod-prices를 18:05로 분산.

---

## 8. 참고

- `config/celery.py:135-814` `app.conf.beat_schedule`
- `config/settings.py:479` `CELERY_TIMEZONE = 'America/New_York'`
- `config/settings.py:480` `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` (dict는 reference, DB가 진실의 소스)
- `stocks/services/sp500_eod_service.py:23` `REQUEST_DELAY = 0.3` (500종목 ≈ 150초)
- `stocks/services/korean_overview_service.py:139` `time.sleep(self.RPM_DELAY)` (Gemini 자체 throttle 존재)
- 기존 audit P0 #8 (2026-04-26): 16:30 analyze-deep ↔ 16:45 extract-keywords 충돌을 15분 분산으로 해소 — 동일 원칙을 18:30↔18:35에 적용 필요

**감사자 노트**: DB의 `PeriodicTask` 테이블과 본 dict의 실제 동기화 여부는 본 감사 범위 밖. `python manage.py shell`에서 다음으로 drift 점검 필요:

```python
from django_celery_beat.models import PeriodicTask
db_names = set(PeriodicTask.objects.values_list('name', flat=True))
config_names = set(app.conf.beat_schedule.keys())  # from config.celery
print("DB only:", db_names - config_names)
print("Config only:", config_names - db_names)
```
