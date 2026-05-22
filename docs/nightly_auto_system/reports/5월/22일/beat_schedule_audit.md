# Beat Schedule 감사 보고서

- 감사일: 2026-05-22
- 대상 파일: `config/celery.py` (beat_schedule, 약 70개 태스크)
- 타임존: `CELERY_TIMEZONE = 'America/New_York'` (ET) — 모든 crontab hour 값은 ET 기준
- 스케줄러: `django_celery_beat.schedulers:DatabaseScheduler` — **dict는 reference이고 실제 진실은 DB `PeriodicTask`**.
  본 감사는 config/celery.py dict를 기준으로 작성. DB drift 가능성은 별도 점검 필요.

> ⚠ **본 보고서는 read-only 감사**다. 코드 수정은 없으며, 권고만 기술한다.

---

## 0. 요약 (TL;DR)

| 영역 | 위험도 | 핵심 이슈 |
|------|--------|----------|
| FMP Rate Limit (Starter 300 RPM) | 🟡 MEDIUM | 시장 시간(09–16 ET) realtime+indices 5분 단위 + market-pulse 1분 단위 중첩 → 시간당 ~540 호출 추정, **분당 부담은 안전(피크 분당 ~25)** 이나 :00 정렬 트래픽 쏠림 |
| FMP 배치 피크 | 🟡 MEDIUM | **18:00 ET 동시 점화 4건** (sync-sp500-eod / collect-market-news-evening / update-economic-indicators / thesis-update-readings) + 17:00 EOD 가격 5분 후 17:15 sp500-news → 1분 내 폭주 가능 |
| Gemini Free (15 RPM / 1500 RPD) | 🔴 HIGH | **18:30 analyze-news-deep + 18:35 thesis-generate-summaries 5분 간격** — 두 LLM 배치가 큐에서 겹치면 15 RPM 동시 초과. 16:30/16:45 동일 패턴은 이미 audit P0 #8로 식별·완화됨 |
| Alpha Vantage (5 RPM) | 🟢 LOW | beat_schedule에 AV 의존 직접 호출 없음. 코드 베이스에 잔존 가능하나 스케줄 트리거 없음 |
| Queue (default vs neo4j) | 🟡 MEDIUM | neo4j queue는 solo pool — `sec-sync-dirty-neo4j`가 **5분마다 24시간**(288회/일) 점유. 12:00–12:45 EST에 chainsight sync 2건 + news sync 1건이 같은 큐로 몰림 |
| 스케줄 겹침/의존성 | 🟡 MEDIUM | thesis EOD 파이프라인 (18:00→18:15→18:30→18:35) 4단 직렬 의존성을 **타임 오프셋 15분**으로만 보장 — 선행 태스크가 지연되면 후행은 stale 데이터 사용 |

---

## 1. Rate Limit 초과 구간

### 1.1 FMP (Starter Plan 300 calls/min, 10,000/day)

**분당 한도 (300 RPM) 관점**

| 분 (ET) | 시간대 | 동시 점화 태스크 | FMP 의존 추정 호출 | 비고 |
|---------|--------|-----------------|-------------------|------|
| HH:00 (9–16시) | 시장 시간 | `update-realtime-prices`(\*/5) + `update-market-indices`(\*/5) + `refresh-market-pulse-cache`(\*/1) + `calculate-portfolio-values`(\*/10) | 1 + 1 + 1 + 1 = 4 (배치 단건당 1) | 각 태스크가 내부적으로 S&P 500 503개 심볼을 배치 호출하면 한도 위협 |
| HH:00 분당 | 시장 시간 외 | `refresh-market-pulse-cache` 없음 | 0 | 안전 |
| 06:15 | 평일 | `collect-sp500-news-fmp-0615` | 503 symbols batch | **분당 폭주 위험** — 단일 분에 다수 심볼 |
| 06:45 | 평일 | `collect-general-news-fmp-morning` | 일반 뉴스 1건 | 안전 |
| 07:30 | 평일 | `sync-daily-market-movers` | gainers/losers fetch | 안전 |
| 07:45 | 평일 | `collect-press-releases-fmp` (max_symbols=50) | ~50 calls | 안전 (50 < 300) |
| 10:15 | 평일 | `collect-sp500-news-fmp-1015` | 503 symbols batch | **분당 폭주 위험** |
| 12:30 | 평일 | `collect-general-news-fmp-noon` | 1건 | 안전 |
| 13:15 | 평일 | `collect-sp500-news-fmp-1315` | 503 symbols batch | **분당 폭주 위험** |
| 15:15 | 평일 | `collect-sp500-news-fmp-1515` | 503 symbols batch | **분당 폭주 위험** |
| 17:00 | 평일 | `update-daily-prices` (전 종목 일일 종가) | 503 calls 가능 | **분당 폭주 위험** |
| 17:15 | 평일 | `collect-sp500-news-fmp-1715` | 503 symbols batch | **분당 폭주 위험** |
| 17:45 | 평일 | `collect-general-news-fmp-evening` | 1건 | 안전 |
| 18:00 | 평일 | `sync-sp500-eod-prices` (503 EOD 가격) | 503 calls | **분당 폭주 위험** |
| 20:00 | 평일 | `sync-sp500-financials` (101개/일, 5일 1회전) | ~101 calls | 안전 (101 < 300) |

**핵심 발견**:
- **5회/일의 `collect-sp500-news-fmp-*` orchestrator** (06:15, 10:15, 13:15, 15:15, 17:15)와 **17:00 daily-prices, 18:00 eod-prices**가 모두 단일 분 내에서 S&P 500 전 종목 호출 가능성 보유.
- 실제 RPM 초과 여부는 orchestrator의 chunk/throttle 구현에 의존(`news.tasks.collect_sp500_news_fmp_orchestrator`). 본 감사 범위 밖.
- **17:00 → 17:15 → 17:45 → 18:00 → 18:30 (run-eod-pipeline)** 의 좁은 윈도우(1시간 30분 내)에 FMP 의존 대형 배치 5개 직렬화 — **하나가 지연되면 도미노**.

**일일 한도 (10,000/day) 관점**
- 시장 시간 5분 단위 호출(`update-realtime-prices`+`update-market-indices` 각각): 8시간 × 12회 × 2 = **192 calls/일**
- `refresh-market-pulse-cache` 매분: 8시간 × 60 = **480 calls/일**
- SP500 news orchestrator 5회 × 503: 이론 **2,515 calls/일** (실제는 배치 호출로 더 적을 것)
- SP500 EOD + daily prices: **~1,000 calls/일**
- 합계 추정: **4,500–6,000 calls/일** → 한도 10,000 대비 60% 여유. 안전 구간.

### 1.2 Gemini Free (15 RPM, 1500 RPD)

**Gemini 의존 태스크**

| 태스크 | 스케줄 (ET) | 빈도/일 | LLM 호출 추정 |
|--------|------------|---------|---------------|
| `keyword-generation-pipeline` | 08:00 daily | 1 | gainers 키워드 — 다수 호출 가능 |
| `analyze-news-deep-batch` | 08:30/10:30/12:30/14:30/16:30/18:30 평일 | 6 | max_articles=50 → 최대 50 LLM 호출 |
| `classify-news-batch` | 08:15/10:15/12:15/14:15/16:15/18:15 평일 | 6 | 룰엔진 우선, LLM 폴백 (잠재 호출) |
| `extract-daily-news-keywords` | 16:45 daily | 1 | 일일 키워드 |
| `enrich-relationship-keywords` | 05:30 daily (limit=100) | 1 | 100건 enrichment |
| `extract-news-relations` | 09:00 daily | 1 | 24h 윈도우 관계 추출 |
| `thesis-generate-summaries` | 18:35 평일 | 1 | 가설별 요약 (다건) |
| `chainsight-co-mentions` | 10:00 daily | 1 | LLM 기반 동시 언급 추출 |
| `bulk_generate_korean_overviews` (refresh-korean-overviews-monthly) | 1일 03:00 월 1회 | 1/월 | 503 심볼 — 일 1500 RPD 초과 위험, 다일 분산 필요 |
| `train-importance-model` / `generate-shadow-report` / `train-lightgbm-model` | 일 03:00/03:30/04:30 | 1주 | ML 학습 (LLM 호출 적음) |

**분당 15 RPM 위반 위험 구간** (가장 위험한 쪽 우선):

1. **🔴 18:30 ET / 18:35 ET 충돌** — `analyze-news-deep-batch`(50 articles 큐잉) + 5분 후 `thesis-generate-summaries`. analyze-deep가 50건을 동기 직렬 호출하면 50건 × ~10초 ≈ 8분 소요 → 18:35 thesis-summaries 시작 시 analyze-deep와 **동시 LLM 호출** 발생. **15 RPM 초과 직접 위험**.
2. **🟡 16:30 / 16:45 ET** — 동일 패턴이었으나 코드 주석 (audit P0 #8, 2026-04-26)에 따라 16:45로 15분 분산 완료. 다만 50건 × 10초 = 500초(8.3분) → 16:30+8.3분 = 16:38까지 점유 → 16:45와 안전 마진은 7분뿐.
3. **🟡 08:00 ET 키워드 생성 + 08:15 classify + 08:30 analyze-deep** — 3건이 30분 내 점화. 큐 백로그에 따라 LLM 동시 호출 가능.
4. **🟢 05:30 enrich-relationship-keywords (limit=100)** — 단독 점화, 100건 처리에 충분한 시간 확보.

**일일 1500 RPD 한도**
- analyze-news-deep 6회 × 최대 50 = **300 calls/일**
- classify-news-batch 6회 × LLM 폴백 비율 (불명) ≈ 100–600 calls/일
- 단건 태스크 합산 ≈ 200–400 calls/일
- **합계 600–1300 calls/일** — 한도 1500에 근접. 월 1회 `bulk_generate_korean_overviews`가 같은 날 점화되면 503건 추가 → **1500 RPD 초과 확정**. 다일 분산 또는 별도 API 키 분리 필요.

### 1.3 Alpha Vantage (5 RPM)

- beat_schedule dict에 **AV를 직접 의존하는 태스크 없음**.
- `stocks/`, `analysis/` 등 코드에 잔존 AV 호출이 있을 수 있으나 스케줄 트리거 없음 → **현재 스케줄러 관점 risk 없음**.
- 권고: AV 호출이 남아있다면 사용 경로(view? 수동? 마이그레이션?) 식별하여 별도 감사.

---

## 2. Queue 몰림 분석

### 2.1 큐 분류

**neo4j queue (solo pool — 동시 1개만 처리)**

| 태스크 | 스케줄 | 부담 |
|--------|--------|------|
| `sec-sync-dirty-neo4j` | 5분마다 24시간 | **288회/일, 큐 점유율 압도적** |
| `cleanup-expired-news-relationships` | 04:00 daily | 1회/일 |
| `sync-news-to-neo4j` | 평일 08:45/10:45/12:45/14:45/16:45/18:45 | 6회/일 |
| `chainsight-sync-profiles-neo4j` | 12:00 daily | 1회/일 |
| `chainsight-sync-relations-neo4j` | 12:30 daily | 1회/일 |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | 1회/주 |
| `neo4j-health-check` | 6시간마다 (00/06/12/18 ET) | 4회/일 |
| `enrich-relationship-keywords` | 05:30 daily | 1회/일 |

**default queue**: 나머지 약 55개 태스크.

### 2.2 Neo4j 큐 충돌 핫스팟

- **12:00 ET ±45분**: `chainsight-sync-profiles-neo4j`(12:00) → `neo4j-health-check`(12:00) → `chainsight-sync-relations-neo4j`(12:30) → `sync-news-to-neo4j`(12:45) → 그 사이 `sec-sync-dirty-neo4j`가 12:00/12:05/12:10/12:15/12:20/12:25/12:30/12:35/12:40/12:45 매 5분 점화. **연속 백로그**.
- solo pool이라 큐잉만 발생하며 충돌은 없으나, `sec-sync-dirty-neo4j`가 매번 4분 이상 걸리면 5분 주기에 따라잡지 못함 → **점진적 백로그 누적 위험**. `expires: 240`(4분)으로 만료 처리되어 자연 드롭되지만, 그러면 sync 누락 발생.
- **18:45 ET** `sync-news-to-neo4j` + `sec-sync-dirty-neo4j`(18:45) 동일 분 점화 → solo pool에서 순차 처리.

### 2.3 default queue 핫스팟

- **18:00 ET**: 평일 동시 점화 5건 (sync-sp500-eod-prices / collect-market-news-evening / update-economic-indicators / thesis-update-readings / **추가 cron 동시 정렬**) — DB 커넥션 풀과 FMP 클라이언트 경합.
- **09:00 ET**: 시장 개장 정렬 — refresh-market-pulse-cache 매분 + realtime-prices 5분 + market-indices 5분 + portfolio 10분 + screener-alerts 15분 + aggregate-daily-sentiment + extract-news-relations. 시장 개장 1분에 7건 동시 큐잉.

---

## 3. 시간대별 ASCII 히트맵

평일 시간당 점화되는 **distinct 태스크 수** (반복 cron은 첫 분 1회로 카운트).
범례: `█` = 4건 이상, `▓` = 3건, `▒` = 2건, `░` = 1건, `·` = 0건.

```
Hour | Tasks                                                                  | Bar
-----+------------------------------------------------------------------------+--------
00 ET| (nothing scheduled)                                                    | ·
01 ET| update-economic-calendar(daily)                                        | ░
02 ET| (monthly: sync-sp500-constituents, archive-old-articles)               | ·  (평일 0건)
03 ET| (weekly Sun + monthly + Sat)                                           | ·
04 ET| cleanup-expired-news-relationships(daily) + weekly/monthly             | ░
05 ET| enrich-relationship-keywords(daily) + weekly                           | ░
06 ET| daily-news-morning + econ-indicators + cat-news-high + sp500-news-fmp  | █  (5건)
     |  + general-news-fmp-morning                                            |
07 ET| celery-error-digest + cat-news-medium + cat-news-low + market-movers   | █  (5건)
     |  + press-releases-fmp + heat-score-daily                               |
08 ET| keyword-gen + market-news-morning + classify-batch + analyze-deep      | █  (5건)
     |  + sync-news-neo4j                                                     |
09 ET| realtime-prices(*/5) + market-indices(*/5) + pulse(*/1) + portfolio   | █  (7+건)
     |  + screener-alerts + sentiment + extract-news-relations                |
10 ET| (시장시간 5건) + classify + analyze-deep + sync-news-neo4j             | █  (8건)
     |  + co-mentions + sp500-news-fmp-1015                                   |
11 ET| (시장시간 5건) + relation-confidence                                   | █  (6건)
12 ET| (시장시간 5건) + econ-indicators + classify + analyze-deep             | █  (10건!)
     |  + market-news-noon + general-news-fmp-noon + sync-news-neo4j          |
     |  + chainsight-sync-profiles + chainsight-sync-relations + sec-seed     |
13 ET| (시장시간 5건) + cat-news-high-midday + sp500-news-fmp-1315            | █  (8건)
     |  + chainsight-seed-selection                                           |
14 ET| (시장시간 5건) + classify + analyze-deep + sync-news-neo4j             | █  (8건)
     |  + daily-news-afternoon + cat-news-medium-afternoon                    |
15 ET| (시장시간 5건) + market-news-afternoon + sp500-news-fmp-1515           | █  (7건)
16 ET| (시장시간 5건) + classify + analyze-deep + extract-daily-keywords      | █  (9건!)
     |  + sync-news-neo4j + market-breadth + sector-heatmap                   |
17 ET| daily-prices(FMP) + cat-news-high-evening + sp500-news-fmp-1715        | █  (4건)
     |  + general-news-fmp-evening                                            |
18 ET| econ-indicators + market-news-evening + classify + analyze-deep        | █  (9건!)
     |  + sync-news-neo4j + sync-sp500-eod + run-eod-pipeline                 |
     |  + thesis(readings+scores+snapshots+summaries)                         |
19 ET| collect-ml-labels + backfill-signal-accuracy                           | ▒
20 ET| sync-sp500-financials                                                  | ░
21 ET| (nothing scheduled)                                                    | ·
22 ET| update-economic-indicators(22:00)                                      | ░
23 ET| (nothing scheduled)                                                    | ·

Always-on (24/7, background):
 - sec-sync-dirty-neo4j:        ████████████████████████  (5분마다, 288회/일)
 - check-pipeline-alerts:       ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  (30분마다, 48회/일)
 - refresh-market-pulse-cache:  ········█████████··········  (09–16 ET 매분, 480회/평일)
```

### 피크 시간대 식별

- **🔴 P0 — 12:00 ET (10건)**: 정오 정렬에 분야가 모두 몰림. 거시 + Chain Sight + 뉴스 + SEC + 시장. neo4j queue 3건 동시 큐잉.
- **🔴 P0 — 16:30 ET (9건)**: 장 마감 정렬 + LLM 분석 + breadth/heatmap. Gemini 부담 정점.
- **🔴 P0 — 18:00 ET (9건)**: EOD 파이프라인 + thesis 직렬 + FMP 503 EOD 가격 + 분류/분석 LLM. **FMP + Gemini 동시 부담**, DB 커넥션 풀 압박.
- **🟡 P1 — 09:00 ET (7건)**: 시장 개장 정렬.
- **🟡 P1 — 13:00 ET / 15:00 ET / 10:00 ET / 14:00 ET**: 시장 시간 + 뉴스 배치 정렬.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4.1 직렬 의존성 (선행 → 후행, 시간 마진)

| 선행 → 후행 | 마진 | 위험 |
|------------|------|------|
| `sync-sp500-eod-prices` 18:00 → `run-eod-pipeline` 18:30 | 30분 | 🟢 충분 (503 종목 가격 30분이면 OK) |
| `run-eod-pipeline` 18:30 → `backfill-signal-accuracy` 19:00 | 30분 | 🟢 |
| `thesis-update-readings` 18:00 → `thesis-calculate-scores` 18:15 | 15분 | 🟡 **마진 좁음**. 18:00 동시 점화 5건과 큐 경합 시 readings 15분 초과 가능 |
| `thesis-calculate-scores` 18:15 → `thesis-create-snapshots` 18:30 | 15분 | 🟡 같은 사유 |
| `thesis-create-snapshots` 18:30 → `thesis-generate-summaries` 18:35 | **5분** | 🔴 **너무 좁음**. snapshot이 5분 초과하면 summaries는 stale snapshot 사용 |
| `analyze-news-deep-batch` 18:30 → `sync-news-to-neo4j` 18:45 | 15분 | 🟡 50건 deep 분석이 15분 초과하면 sync 누락 |
| `analyze-news-deep-batch` 16:30 → `extract-daily-news-keywords` 16:45 | 15분 | 🟡 audit P0 #8로 분산 완료, 마진 좁음 |
| `classify-news-batch` HH:15 → `analyze-news-deep-batch` HH:30 | 15분 | 🟡 분류 결과 기반 deep 분석 → 분류 지연 시 deep는 분류 미반영 데이터 처리 |
| `chainsight-sync-profiles-neo4j` 12:00 → `chainsight-sync-relations-neo4j` 12:30 | 30분 | 🟢 |
| `chainsight-co-mentions` 10:00 → `chainsight-relation-confidence` 11:00 | 60분 | 🟢 |
| Sun ML 파이프라인 03:00 → 03:30 → 04:00 → 04:15 → 04:20 → 04:30 | 각 15–30분 | 🟡 6단 직렬, 1단 지연 시 도미노 |

### 4.2 데이터 경합 (같은 모델/캐시 동시 쓰기)

- **stocks.DailyPrice**: 17:00 `update-daily-prices` + 18:00 `sync-sp500-eod-prices` — **둘 다 동일 일자 종가를 쓸 가능성**. 의도된 이중 안전망인지, 중복인지 확인 필요. 만약 둘 다 upsert면 후자가 전자를 덮어쓰는 정상 동작이나, 17:00이 미장 데이터(시간외)와 섞이면 일관성 문제.
- **news.NewsArticle**: 동일 시간대(06:00/14:30)에 `collect-daily-news` + `collect-sp500-news-fmp-*` + `collect-category-news-*`가 같은 기사를 다른 소스로 수집 → dedup 키 정책에 의존.
- **chainsight 관계**: 12:00 sync_profiles + 12:30 sync_relations가 같은 Stock 노드에 쓰기. solo pool이라 직렬화되긴 함.

### 4.3 명시 검증된 충돌 (코드 주석)

- ✅ `extract-daily-news-keywords` 16:30 → 16:45로 분산 (audit P0 #8, 2026-04-26, Gemini 동시 호출 회피).
- ✅ `chainsight-heat-score-daily` (07:00) + `sec-seed-relations-to-chainsight` (12:00) DB 등록 누락 → 2026-04-24 복구 (PROGRESS 주석).
- ✅ Beat scheduler가 DatabaseScheduler라 dict는 reference → drift 감시 수동 필요.

---

## 5. 권고 사항 (우선순위)

본 보고서는 read-only다. 아래는 권고만 기술한다.

### 🔴 P0
1. **18:30/18:35 thesis-summaries 충돌**: `thesis-generate-summaries`를 18:50 또는 19:05로 이동 권고. analyze-news-deep-batch와 Gemini 15 RPM 동시 초과 차단.
2. **`bulk_generate_korean_overviews` 503 심볼/월 1회**: Gemini 1500 RPD 초과 위험. 다일 분산(예: 매월 1~7일에 503/7≈72건씩) 또는 별도 API 키 필요.

### 🟡 P1
3. **18:00 ET 동시 점화 5건**: thesis-update-readings를 17:55로 5분 당겨 18:00 정점 분산. FMP 클라이언트 + DB 커넥션 풀 경합 완화.
4. **`sec-sync-dirty-neo4j` 5분 주기**: 실행 시간이 평균 3분 이상이면 백로그 누적. 메트릭 측정 후 10분 주기로 완화 검토.
5. **`refresh-market-pulse-cache` 매분 호출**: FMP 일일 한도의 약 5%(480/10000)를 단일 태스크가 소모. 캐시 효과가 명확하지 않다면 5분 주기로 완화.

### 🟢 P2
6. **DB drift 점검 자동화**: `python manage.py shell` 수동 diff → cron으로 정기 점검 + 알람.
7. **classify→analyze→sync 15분 마진**: 50건 처리에 50×10초=8분 소요 기준 마진은 충분하나, 큐 백로그 시점에는 20–30분 마진 권고.

---

## 6. 부록: 태스크 인벤토리 (총 70개)

- **Stocks/Macro**: update-realtime-prices, update-daily-prices, aggregate-weekly-prices, sync-sp500-financials, sync-sp500-constituents, sync-sp500-eod-prices, update-sp500-change-percent, update-economic-indicators, update-market-indices, update-economic-calendar, refresh-market-pulse-cache, cleanup-old-macro-data, calculate-portfolio-values, refresh-korean-overviews-monthly
- **Market Movers / Screener**: sync-daily-market-movers, keyword-generation-pipeline, calculate-market-breadth, calculate-sector-heatmap, check-screener-alerts, sync-etf-holdings, sync-supply-chain-batch
- **News (수집)**: collect-daily-news-morning/afternoon, collect-market-news-morning/noon/afternoon/evening, collect-category-news-high (3) / medium (2) / low (1), collect-sp500-news-fmp (5), collect-press-releases-fmp, collect-general-news-fmp (3)
- **News (분석)**: aggregate-daily-sentiment, extract-daily-news-keywords, classify-news-batch, analyze-news-deep-batch, collect-ml-labels, sync-news-to-neo4j, cleanup-expired-news-relationships, train-importance-model, generate-shadow-report, check-auto-deploy, generate-weekly-ml-report, monitor-ml-performance, train-lightgbm-model, check-pipeline-alerts, archive-old-articles
- **RAG / Neo4j**: neo4j-health-check
- **Chain Sight**: chainsight-all-profiles, chainsight-co-mentions, chainsight-price-co-movement, chainsight-relation-confidence, chainsight-stale-decay, chainsight-aggregate-profiles, chainsight-sync-profiles-neo4j, chainsight-sync-relations-neo4j, chainsight-heat-score-daily, chainsight-seed-selection, chainsight-neo4j-dirty-sync, extract-news-relations, enrich-relationship-keywords, sync-institutional-holdings, scan-regulatory-relationships, build-patent-network
- **Validation**: validation-weekly-batch
- **SEC Pipeline**: sec-sync-dirty-neo4j, sec-seed-relations-to-chainsight, sec-check-new-filings
- **EOD Dashboard**: run-eod-pipeline, backfill-signal-accuracy
- **Thesis Control**: thesis-update-readings, thesis-calculate-scores, thesis-create-snapshots, thesis-generate-summaries
- **운영**: celery-error-digest, cleanup-task-results

---

(끝) — 본 감사는 config/celery.py dict 기준이며, 실제 DB `PeriodicTask` 등록 상태와의 drift는 별도 점검 필요.
