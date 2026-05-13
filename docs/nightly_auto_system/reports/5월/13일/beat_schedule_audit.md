# Celery Beat Schedule 감사 보고서

- **감사일**: 2026-05-13
- **대상**: `config/celery.py` (820 lines, 76개 beat_schedule 엔트리)
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **기준 시각대**: 모든 crontab `hour` 값은 EST 기준 (UTC는 별도 표시)

> ⚠️ **중요한 사전 컨텍스트**: `config/celery.py` 117~134행 코멘트에 명시된 대로,
> 본 `beat_schedule` dict는 **런타임에 무시된다**. 실제 진실의 소스는
> `django_celery_beat.PeriodicTask` 테이블이다 (`DatabaseScheduler` 사용).
> 본 보고서는 **선언적 reference로서의 dict**만 감사한다. DB와의 drift는 별도 점검이 필요하다.

---

## Executive Summary

| 위험도 | 카테고리 | 핵심 발견 |
|--------|----------|----------|
| 🔴 **CRITICAL** | FMP Rate Limit | `sync-sp500-eod-prices` (18:00) 500 calls + 동시간 6개 태스크 → 300/min 초과 위험 |
| 🔴 **CRITICAL** | Gemini RPM | 18:30~18:35 5분 창에 `analyze-deep`(50건) + `thesis-summaries` 동시 호출 → 15 RPM 초과 |
| 🟠 **HIGH** | neo4j Queue Solo Pool | 12:00 시점 4개 neo4j 태스크 동시 큐잉, `sec-sync` expires=240초 만료 위험 |
| 🟠 **HIGH** | Gemini RPM | 08:00~08:45 keyword + classify + deep + sync 30분 창에 LLM 호출 집중 |
| 🟡 **MEDIUM** | 시장개장중 부하 | 9-16시 매분 5~6개 default queue 태스크 동시 트리거 |
| 🟡 **MEDIUM** | Queue 미지정 | `chainsight-heat-score-daily`, `chainsight-seed-selection`, `chainsight-co-mentions` 등 무거운 LLM 태스크가 default queue로 흘러감 |
| 🟢 **LOW** | Alpha Vantage | beat_schedule에 AV 직접 호출 없음 (코드 폴백 경로만 의존) |

---

## 1. Rate Limit 초과 구간 분석

### 1.1 FMP Starter Plan (300 calls/min, 10,000 calls/day)

#### 🔴 18:00 EST — 일일 최대 부하 시점

| 태스크 | 추정 FMP 호출량 | 비고 |
|--------|----------------|------|
| `sync-sp500-eod-prices` | **≈500 calls** (S&P 500 종목별) | line 556~560 |
| `collect-market-news-evening` | ≈10 calls | FMP/Marketaux 혼용 추정 |
| `thesis-update-readings` | FMP 의존 (지표 N개) | 알 수 없음, 잠재 위험 |
| `update-economic-indicators` | 0 (FRED API) | 영향 없음 |
| `neo4j-health-check` | 0 | 영향 없음 |

**위험**:
- 500 calls를 단일 분에 일제히 보내면 300/min 초과 → 429 발생 가능
- `sync-sp500-eod-prices` 내부 배치 로직(batch_size, sleep)이 없으면 즉시 한도 초과
- `expires=3600`이라 워커가 살아있으면 결국 완료되겠지만 **다음 18:30 EOD pipeline 진입 직전까지 밀릴 위험**

**검증 권고**:
- `stocks.tasks.sync_sp500_eod_prices` 구현체에 throttle/batch 확인 필요
- FMP rate limit 누적 카운터 모니터링 (Redis 등)

#### 🟠 06:15~17:15 EST — FMP S&P500 News Orchestrator 5회 분산

| 시각 | 태스크 | 추정 호출량 |
|------|--------|------------|
| 06:15 | `collect-sp500-news-fmp-0615` | ≈500 calls (종목별 뉴스) |
| 10:15 | `collect-sp500-news-fmp-1015` | ≈500 |
| 13:15 | `collect-sp500-news-fmp-1315` | ≈500 |
| 15:15 | `collect-sp500-news-fmp-1515` | ≈500 |
| 17:15 | `collect-sp500-news-fmp-1715` | ≈500 |

- **일일 합계**: ≈2,500 calls (일일 한도 10,000의 **25%**)
- 단일 회당 500 calls — 300/min 한도 → 내부 throttling 필수
- 단일 시각에 다른 FMP 태스크와 겹치지는 않으나 (`*:15`는 단독), orchestrator 자체가 long-running

#### 🟡 20:00 EST — `sync-sp500-financials`

- 코멘트에 "101개/일, 5일에 전체 1회전" 명시 (line 159)
- 종목당 4개 statement (income/balance/cashflow/keymetrics) ≈ 404 calls
- 단독 실행 시간대 → 비교적 안전

#### 🟢 시장개장중 (9-16시 EST) — FMP `update-realtime-prices` + `update-market-indices`

- 둘 다 `*/5분` 동시 트리거
- 추정: realtime은 watchlist/portfolio 종목 기준 (수십~수백), indices는 ~10개
- 분당 부하: ≈수십~수백 calls — 한도 내 추정 (구현체 확인 필요)

---

### 1.2 Gemini Free (15 RPM, 1500 RPD)

#### 🔴 18:30 ~ 18:35 EST — 5분 창 LLM 집중

| 시각 | 태스크 | LLM 추정 호출량 |
|------|--------|---------------|
| 18:30 | `analyze-news-deep-batch` | `max_articles=50` → ≈50 calls |
| 18:30 | `run-eod-pipeline` | 내부 LLM 호출 있을 수 있음 |
| 18:35 | `thesis-generate-summaries` | 가설 N개 ≈ N calls |

**위험**:
- 18:30 단일 분에 analyze-deep 50건 발사 시 즉시 15 RPM 초과
- `thesis-summaries`는 audit P0 #15 코멘트(line 672)에 따라 18:30 snapshot 직후 18:35로 분리됨 — 이미 한 차례 분산되어 있으나, 50 articles × 15 RPM 한도 = **3분 이상 소요** 가정 시 18:35와 충돌 가능

#### 🔴 08:00 ~ 08:45 EST — 아침 분석 파이프라인 LLM 폭주

| 시각 | 태스크 | LLM 호출 |
|------|--------|---------|
| 08:00 | `keyword-generation-pipeline` (Gainers) | Gemini |
| 08:15 | `classify-news-batch-morning` (hour='8,10,12,14,16,18') | Gemini (3시간치 뉴스) |
| 08:30 | `analyze-news-deep-batch` (max_articles=50) | Gemini 50 calls |
| 08:35 | (none) | |
| 08:45 | `sync-news-to-neo4j` | 비-LLM |

- 15분 간격으로 분산되어 있으나, `classify-news`는 "3시간치 뉴스" 처리 → 새벽 뉴스 수집량에 따라 수십~수백 articles
- **08:15 classify가 끝나기 전에 08:30 analyze-deep 시작 시 동시 호출 위험**
- 동일한 패턴이 10:00, 12:00, 14:00, 16:00, 18:00에서 반복 (`hour='8,10,12,14,16,18'`)

#### 🟠 16:30 ~ 16:45 EST — 이미 부분 분산됨

- 코멘트(line 285~286)에 audit P0 #8 (2026-04-26) 명시:
  > "16:30 EST에 analyze-news-deep-batch와 Gemini 동시 호출 충돌 → Gemini 15 RPM 2배 초과 위험. 15분 분산하여 회피"
- `extract-daily-news-keywords`는 16:45로 분리됨 ✓
- **다만 08/10/12/14/18시에도 동일 패턴 재현** (위 분석 참조) — **분산 미적용**

#### 🟡 매월 1일 03:00 EST — Korean Overviews 대량 LLM

- `refresh-korean-overviews-monthly` (line 641)
- S&P 500 × 한글 개요 ≈ 500 calls
- **일일 한도 1500 중 1/3 소비** — 단일 일자 집중
- 새벽 시간대라 다른 LLM 태스크와 충돌은 없음

#### 🟡 매일 05:30 EST — `enrich-relationship-keywords`

- `kwargs: {'limit': 100}` (line 589)
- ≈100 LLM calls — neo4j queue + Gemini Free 동시 부담

---

### 1.3 Alpha Vantage (5 calls/min)

- **beat_schedule에 AV 직접 호출 없음**
- 잠재 위험:
  - `stocks.tasks.update_realtime_with_provider`는 FMP Provider 사용 명시
  - `macro.tasks.update_economic_indicators`는 FRED API 사용
  - AV는 폴백 경로 또는 사용자 트리거 동기화에서만 호출되는 것으로 추정
- **현재 schedule상으로 AV 한도 초과 위험은 낮음** (코드 폴백 경로 확인은 별도 필요)

---

## 2. Queue 몰림 분석

### 2.1 neo4j Queue (solo pool, 동시 1개)

#### 🔴 12:00 EST — neo4j queue 최대 압축 시점

해당 분에 큐잉되는 neo4j 태스크:

| 태스크 | expires | 비고 |
|--------|---------|------|
| `neo4j-health-check` (6시간마다) | 미설정 | health 자체는 가벼움 |
| `chainsight-sync-profiles-neo4j` | 3600 | **무거움** (전체 프로파일) |
| `sec-sync-dirty-neo4j` (매 5분, 12:00도 해당) | **240** | 5분 내 완료 안 되면 만료 |
| `chainsight-sync-relations-neo4j` (12:30) | 3600 | 12:00 작업이 30분 내 안 끝나면 큐 적체 |

**위험 시나리오**:
1. 12:00 `sync-profiles` 시작 (대용량)
2. 12:00 `health-check`, `sec-sync` 큐 대기
3. 12:05 `sec-sync` 다시 큐잉 — 240초 expires
4. 12:10 또 큐잉, 12:15 또 큐잉...
5. `sync-profiles`가 10분 이상 걸리면 **`sec-sync` 연속 만료** → SEC dirty evidence Neo4j 미동기화 누적

#### 🟠 매 5분 `sec-sync-dirty-neo4j` (288회/일)

- expires=240초 (5분 미만)
- solo pool에서 다른 long-running 태스크가 큐를 잡고 있으면 **즉시 만료**
- 가장 위험한 시간대: **12:00 EST 일대 (5~10분간)**

#### 🟡 매 6시간 `neo4j-health-check` (00/06/12/18시)

- 자체는 가벼우나 12:00과 18:00에서 다른 neo4j 태스크와 동시 큐잉

### 2.2 Default Queue

#### 🟠 시장개장중 (09:00 ~ 16:00 EST) 매분 트리거

| 트리거 빈도 | 태스크 |
|------------|--------|
| 매분 | `refresh-market-pulse-cache` (60회/시) |
| `*/5분` | `update-realtime-prices`, `update-market-indices` (2개 × 12회/시) |
| `*/10분` | `calculate-portfolio-values` (6회/시) |
| `*/15분` | `check-screener-alerts` (4회/시) |
| `*/30분` | `check-pipeline-alerts` (2회/시) |
| `*/5분` | `sec-sync-dirty-neo4j` (12회/시, **neo4j queue**) |

**매시 정각에 동시 트리거되는 default 태스크**:
- `refresh-market-pulse-cache` ✓
- `update-realtime-prices` ✓ (*/5분 = :00, :05, ...)
- `update-market-indices` ✓
- `calculate-portfolio-values` ✓ (*/10분 = :00, :10, ...)
- `check-screener-alerts` ✓ (*/15분 = :00, :15, :30, :45)
- `check-pipeline-alerts` ✓ (*/30분 = :00, :30)
- **→ 매시 :00에 6개 동시 큐잉 (시장개장중)**

#### 🟡 default queue로 흘러가는 LLM 태스크 (Queue 미지정)

`task_routes`에 등록되지 않아 default queue로 가는 무거운 태스크:

| 태스크 | 위험 |
|--------|------|
| `chainsight-co-mentions` (10:00) | 뉴스 7일치 LLM 분석 — default queue 점유 |
| `chainsight-heat-score-daily` (07:00) | 무거운 배치 — default queue 점유 |
| `chainsight-seed-selection` (13:00) | 시드 선정 로직 — default queue 점유 |
| `keyword-generation-pipeline` (08:00) | Gemini 호출 — default queue 점유 |
| `extract-daily-news-keywords` (16:45) | Gemini 호출 — default queue 점유 |
| `analyze-news-deep-batch` (×6/day) | Gemini × 50 articles — default queue 점유 |
| `sec-seed-relations-to-chainsight` (12:00) | default queue (neo4j도 호출) |

---

## 3. 시간대별 ASCII 히트맵 (평일 기준, EST)

### 3.1 시간대별 트리거 횟수 (정각만 카운트, 분단위 반복 별도)

```
   각 hour의 :00 ~ :59 사이 트리거되는 distinct task 인스턴스 수 (평일 기준)
   레전드: ▓=10+  █=5-9  ▒=3-4  ░=1-2  ·=0
                       ※ 매분/매5분 반복 태스크는 1개로 카운트

Hour │ 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
─────┼───────────────────────────────────────────────────────────────────────
Cnt  │  2  2  1  1  2  2  6  6  6 10  8  3 10  4  7  5  9  6 12  4  2  1  2  1
     │  ░  ░  ░  ░  ░  ░  █  █  █  ▓  █  ▒  ▓  ▒  █  █  █  █  ▓  ▒  ░  ░  ░  ░
     │
PEAK │                                              ↑                    ↑
     │                                          12:00 (10)         18:00 (12) ← 최대
     │                                                              MOST CRITICAL
```

### 3.2 시간대별 부하 카테고리 분류

```
Hour │ FMP    Gemini  Neo4j   Default  비고
─────┼─────────────────────────────────────────────────────
00   │  ·      ·       █(health) ·     neo4j-health-check
01   │  ·      ·       ·      ░       update-economic-calendar
02   │  ·      ·       ·      ·       (월1일/토만)
03   │  ·      ░(월1)  ·      ░       cleanup-old-macro/train-importance(일)
04   │  ·      ·       █      ░       cleanup-expired-news-relationships
05   │  ·      ░       █      ░       enrich-relationship-keywords(LLM+neo4j)
06   │ ░       ·       █      ░       sp500-news-fmp + neo4j-health + daily-news
07   │ ░       ·       ·      ▒       market-movers + press-releases + heat-score
08   │ ░       ▓       █      ▒       keyword-gen + classify + analyze + sync ← 위험
09   │ █       ░       ·      █       시장개장 + aggregate-sentiment + extract-relations
10   │ ░       ▒       █      █       sp500-news + classify + analyze + sync + co-mentions
11   │ ·       ·       ·      ░       relation-confidence
12   │ ░       ▓       ▓      ▒       sync-profiles + sync-relations + market-news ← 큐 폭주
13   │ ░       ·       ·      ░       sp500-news + seed-selection + high-news
14   │ ░       ▒       █      ▒       daily-news + classify + analyze + sync
15   │ ░       ·       ·      ░       market-news + sp500-news
16   │ ·       ▒       █      ▒       breadth + sector-heat + extract-keywords + analyze
17   │ ░       ·       ·      ░       daily-prices(FMP) + sp500-news + general-news
18   │ ▓       ▓       █      ▓       eod-prices(500FMP) + market-news + classify + analyze ← 최고위험
     │                                + thesis-update + thesis-scores + thesis-snapshot + thesis-summary
19   │ ·       ·       ·      ▒       collect-ml-labels + backfill-signal-accuracy
20   │ █       ·       ·      ░       sync-sp500-financials (FMP 101+)
21   │ ·       ·       ·      ·
22   │ ·       ·       ·      ░       update-economic-indicators
23   │ ·       ·       ·      ·
```

### 3.3 분단위 매시간 반복 태스크 (배경 부하)

```
Time slice           Background tasks (continuous load)
─────────────────────────────────────────────────────────
24/7 every 5min      sec-sync-dirty-neo4j (288/day, expires=240s)  ← solo pool 위험
24/7 every 30min     check-pipeline-alerts (48/day)
9-16 every 1min      refresh-market-pulse-cache  (480/day, 평일)
9-16 every 5min      update-realtime-prices, update-market-indices (각 96/day)
9-16 every 10min     calculate-portfolio-values (48/day)
9-16 every 15min     check-screener-alerts (32/day)
```

### 3.4 hour='8,10,12,14,16,18' 패턴 (2시간 주기, 평일)

```
Time   Task                       Volume      Risk
────────────────────────────────────────────────────────────
08:15  classify-news-batch        3h news     Gemini
08:30  analyze-news-deep-batch    50 articles Gemini × 50 ← 단일 15 RPM 초과 거의 확실
08:45  sync-news-to-neo4j         100 articles neo4j queue
       ↓ (반복: 10/12/14/16/18시)
18:15  classify-news-batch        3h news     Gemini
18:30  analyze-news-deep-batch    50 articles Gemini × 50  ↘
18:35  thesis-generate-summaries  N theses    Gemini      } 5분 창 LLM 폭주
18:45  sync-news-to-neo4j         100 articles neo4j queue
```

---

## 4. 스케줄 겹침 / 의존성 분석

### 4.1 데이터 경합 위험

#### 🔴 18:00 EST — `sync-sp500-eod-prices` vs `thesis-update-readings`

- 18:00 동시 시작 (line 558, line 654)
- `thesis-update-readings`가 DailyPrice를 읽어 지표 계산 시 — **EOD price 동기화 진행 중에 읽으면 stale 데이터**
- 18:15 `thesis-calculate-scores`가 18:00의 readings를 사용 → readings가 늦게 완료되면 score 계산 시점 race

#### 🟠 19:00 EST — `backfill-signal-accuracy` vs `collect-ml-labels`

- 둘 다 평일 19:00 시작 (line 358, line 636)
- 동일한 라벨 데이터를 동시 갱신할 가능성
- 동일 행 UPDATE 경합 우려

#### 🟡 18:30 EST — 동시 3태스크 (EOD)

- `update-sp500-change-percent` (line 565)
- `run-eod-pipeline` (line 629)
- `thesis-create-snapshots` (line 668)
- `analyze-news-deep-batch` (18:30, line 350)
- 4개 동시 트리거 — 모두 default queue, prefork(linux) 환경에서도 동시성 제한
- macOS solo pool 환경에서는 **순차 실행** → 18:30에 시작된 작업이 18:35 `thesis-generate-summaries` 이전에 완료 안 됨

### 4.2 선행→후속 태스크 의존성 점검

#### ⚠️ 선행 미완료 시 후속 시작될 위험

| 후속 태스크 | 시각 | 선행 태스크 | 시각 | Gap | 위험 |
|------------|------|------------|------|-----|------|
| `thesis-calculate-scores` | 18:15 | `thesis-update-readings` | 18:00 | 15분 | readings가 FMP 호출 포함이면 15분 부족 가능 |
| `thesis-create-snapshots` | 18:30 | `thesis-calculate-scores` | 18:15 | 15분 | 일반적 OK |
| `thesis-generate-summaries` | 18:35 | `thesis-create-snapshots` | 18:30 | 5분 | **위험** snapshot이 5분 내 완료 보장 안 됨 |
| `chainsight-sync-relations-neo4j` | 12:30 | `chainsight-sync-profiles-neo4j` | 12:00 | 30분 | profiles 크기 따라 마진 부족 가능 |
| `chainsight-relation-confidence` | 11:00 | `chainsight-co-mentions` | 10:00 | 60분 | OK |
| `analyze-news-deep-batch` | 08:30 | `classify-news-batch-morning` | 08:15 | 15분 | classify 결과 미반영 시 deep 실패 |
| `sync-news-to-neo4j` | 08:45 | `analyze-news-deep-batch` | 08:30 | 15분 | deep 50건이 15분 내 안 끝나면 stale 데이터 sync |
| `aggregate-daily-sentiment` | 09:00 | `collect-daily-news-morning` | 06:00 | 3시간 | OK |
| `extract-news-relations` | 09:00 | `classify-news-batch-morning` | 08:15 | 45분 | OK |
| `run-eod-pipeline` | 18:30 | `sync-sp500-eod-prices` | 18:00 | 30분 | eod-prices 500 FMP calls 시간 마진 |
| `backfill-signal-accuracy` | 19:00 | `run-eod-pipeline` | 18:30 | 30분 | OK |
| `generate-shadow-report` | 03:30(일) | `train-importance-model` | 03:00(일) | 30분 | OK |
| `check-auto-deploy` | 04:00(일) | `generate-shadow-report` | 03:30(일) | 30분 | OK |
| `generate-weekly-ml-report` | 04:15(일) | `check-auto-deploy` | 04:00(일) | 15분 | OK |
| `monitor-ml-performance` | 04:20(일) | `generate-weekly-ml-report` | 04:15(일) | 5분 | 보고서 빌드 5분 마진 부족 가능 |
| `train-lightgbm-model` | 04:30(일) | `monitor-ml-performance` | 04:20(일) | 10분 | OK |
| `chainsight-aggregate-profiles` | 04:30(토) | `chainsight-stale-decay` | 04:00(토) | 30분 | OK |
| `validation-weekly-batch` | 05:00(토) | `chainsight-aggregate-profiles` | 04:30(토) | 30분 | OK |

#### 🔴 가장 위험한 의존성 (Gap 5분 이하)

- **`thesis-create-snapshots` (18:30) → `thesis-generate-summaries` (18:35)**:
  - snapshot 작성 시간이 5분 초과하면 summary가 부분/이전 snapshot 기준으로 생성
  - 동시 시간대에 `analyze-news-deep-batch` (Gemini 50 calls)가 LLM 토큰 점유 → snapshot 안에 LLM 호출이 있다면 더 위험
- **`monitor-ml-performance` (04:20 일) → 5분 마진**

### 4.3 Queue 미지정 — task_routes 누락 의심 케이스

`config/celery.py` line 37~55의 `task_routes`에 등록되지 않았지만 **Neo4j 또는 무거운 LLM을 다루는 것으로 보이는** 태스크:

| 태스크 | 추정 부하 | 현재 큐 |
|--------|----------|---------|
| `chainsight.tasks.profile_tasks.calculate_all_profiles` | 매우 무거움 (S&P500 × 4 profile) | default |
| `chainsight.tasks.relation_tasks.calculate_price_co_movement` | 무거움 (가격 데이터 회귀) | default |
| `chainsight.tasks.relation_tasks.extract_co_mentions` | LLM 사용 추정 | default |
| `chainsight.tasks.relation_tasks.update_relation_confidence` | DB 대량 갱신 | default |
| `chainsight.tasks.relation_tasks.check_stale_and_decay` | DB 갱신 | default |
| `chainsight.tasks.sync_tasks.aggregate_chain_profiles` | DB 집계 | default |
| `chainsight-heat-score-daily` | LLM/계산 | default |
| `chainsight-seed-selection` | 계산 무거움 | default |

→ 무거운 작업이 default queue를 점유하면 시장개장중 가벼운 태스크(realtime price, portfolio)가 밀릴 위험

---

## 5. 우선순위별 권고 (감사 결과)

### P0 (즉시 점검)

1. **18:00 `sync-sp500-eod-prices`의 FMP throttle 검증**
   - 구현체에서 batch + sleep이 있는지 확인
   - 없으면 단일 분에 500 calls → 즉시 한도 초과
   - 검증 명령: `grep -n 'def sync_sp500_eod_prices\|batch_size\|sleep\|time.sleep' stocks/tasks.py`

2. **18:30~18:35 LLM 폭주 분리**
   - `analyze-news-deep-batch` 18:30 + `thesis-generate-summaries` 18:35
   - 5분은 50 articles 처리에 부족
   - 권고: thesis-summaries를 18:50 또는 19:30으로 이동 (audit P0 #8 패턴 재적용)

3. **12:00 neo4j queue 적체 — `sec-sync-dirty-neo4j` expires=240 위험**
   - 12:00에 `chainsight-sync-profiles-neo4j` + `health-check` + `sec-sync` 동시 큐잉
   - solo pool에서 `sync-profiles`가 5분 초과 시 sec-sync 연속 만료
   - 권고: sec-sync expires를 길게 (600초+) 또는 `sync-profiles`를 13:00로 이동

### P1 (1주 내)

4. **08/10/14시대 `analyze-deep` LLM 분산 (`hour='8,10,12,14,16,18'` 패턴 6회 모두)**
   - 16:30대만 분산 적용됨, 나머지 5회 미적용
   - `extract-daily-news-keywords`처럼 `:45`로 분산하거나 max_articles 축소

5. **Queue 라우팅 보완**
   - `chainsight.tasks.profile_tasks.calculate_all_profiles` 등 무거운 chainsight 태스크를 별도 큐(예: `heavy`)로 분리 검토
   - 또는 default queue worker 동시성 증대

### P2 (시간 날 때)

6. **DB scheduler ↔ config dict drift 점검 자동화**
   - `python manage.py shell`에서 diff 명령을 cron 등록
   - line 130~133 코멘트의 "수동 진행" 표현 — 자동화 가치 있음

7. **시장개장중 매분 6개 동시 트리거 정상성 모니터**
   - prefork 환경에서 worker 동시성 부족하면 queue 적체
   - 평균 처리 시간 대시보드 필요

---

## 6. 부록: beat_schedule 엔트리 인벤토리

총 **76개** entry (debug_task 제외)

| 카테고리 | 개수 | 비고 |
|---------|------|------|
| Stocks | 5 | realtime/daily/weekly/financials/portfolio |
| Macro | 5 | economic-indicators/market-indices/calendar/pulse/cleanup |
| RAG Analysis | 1 | health-check (semantic cache 제거됨) |
| Market Movers + Keyword | 2 | sync + keyword-gen |
| News 수집 | 11 | daily(2) + market(4) + category(6) + extract-keywords |
| News Intelligence v3 | 10 | classify/analyze/sync/labels/cleanup/train/shadow/auto-deploy/weekly-report/monitor/lgbm |
| FMP 뉴스 | 9 | sp500-news(5) + press-releases(1) + general-news(3) |
| 데이터 보존 | 1 | archive-old-articles |
| ETF Holdings | 1 | sync-etf-holdings |
| Supply Chain | 1 | sync-supply-chain-batch |
| Screener | 3 | breadth/heatmap/alerts |
| S&P 500 Sync | 3 | constituents/eod-prices/change-percent |
| Chain Sight Phase 6~8 | 4 | extract-news-relations/enrich/institutional/regulatory/patent |
| EOD Dashboard | 3 | run-eod/backfill-accuracy/refresh-korean |
| Thesis EOD | 4 | readings/scores/snapshots/summaries |
| Chain Sight Tier A | 9 | profiles/co-mentions/co-movement/confidence/decay/aggregate/sync-profiles/sync-relations/heat-score/seed |
| Validation | 1 | weekly-batch |
| SEC Pipeline | 3 | sync-dirty/seed-relations/new-filings |
| 에러 모니터링 + 정리 | 2 | error-digest/cleanup-task-results |
| `check-pipeline-alerts` | 1 | 매 30분 |

---

## 7. 감사 한계 및 다음 단계

### 확인하지 못한 항목
- **DB `PeriodicTask` 테이블 실제 등록 상태 vs config dict diff** — 코드 수정 금지 제약으로 미실행
  - 권고 검증 명령(읽기): `python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print('\n'.join(sorted(PeriodicTask.objects.values_list('name', flat=True))))"` 후 dict 키와 비교
- **각 태스크 구현체의 실제 FMP/Gemini 호출 수** — 추정값으로 보고 (`max_articles`, `limit`, `kwargs` 기반)
- **rate limit 누적 모니터링 코드 존재 여부**
- **prefork(Linux) vs solo(macOS) 환경별 동시성 차이** — macOS 강제 solo (line 30~31)

### 후속 감사 권고
1. `stocks.tasks.sync_sp500_eod_prices` 본문에서 FMP batch/throttle 확인
2. `news.tasks.analyze_news_deep` 본문에서 LLM 호출 카운트와 sleep 간격 확인
3. `chainsight.tasks` 모듈의 LLM 호출 인벤토리화
4. Celery task `RATELIMIT` (Celery 내장) 적용 여부 확인 (`app.conf.task_annotations`)

---

**보고 끝.** 본 보고서는 `config/celery.py` 정적 분석만 수행했으며, 코드/스케줄/DB를 일체 수정하지 않았다.
