# Beat Schedule Audit Report

- **감사 대상**: `config/celery.py` (90개 schedule 인용 + 73개 beat_schedule entry)
- **감사일**: 2026-05-10 (KST)
- **감사자**: Claude (read-only)
- **작업 범위**: Rate Limit, Queue 부하, 시간대별 히트맵, 의존성 / 겹침 분석
- **코드 수정**: ❌ 없음

---

## 0. 사전 점검 사항 (선행 검증)

| 항목 | 값 | 근거 |
|---|---|---|
| `CELERY_TIMEZONE` | `America/New_York` (NYSE 기준) | `config/settings.py:477` |
| Django `TIME_ZONE` | `Asia/Seoul` | `config/settings.py:289` |
| Beat Scheduler | `django_celery_beat.schedulers:DatabaseScheduler` | `celery.py:120-121` 주석 |
| beat_schedule dict | **런타임 무시됨** (DB `PeriodicTask`가 진실의 소스) | `celery.py:118-134` |
| 워커 풀 (macOS) | `solo` 강제 (1 동시) | `celery.py:30-31` |
| Neo4j queue 태스크 | 14개 | `task_routes` + `options.queue` |
| 실행 시각 해석 | beat_schedule 의 `hour=N` = **America/New_York** | `CELERY_TIMEZONE` |

> ⚠️ **첫 번째 발견 / Drift 위험**: `beat_schedule` dict 가 기준이 아니다. 보고서는 dict 의 "선언적 의도" 를 분석하는 것이며, 실제 실행 여부는 DB `PeriodicTask` 와 비교해야 한다. `celery.py:128-133` 주석에 따르면 마지막 동기화 검증은 2026-04-24, 그 이후로 자동 검증 프로세스가 없다.

---

## 1. 태스크 인벤토리 (외부 API 의존성 분류)

### 1.1 FMP 의존 (Starter 300/min, 10,000/일)

| 태스크 | 스케줄 (NY) | 1회 호출량 (추정) | RPM 환산 | 비고 |
|---|---|---|---|---|
| `update-realtime-prices` | 매 5분, 9–16시, M–F | 10 호출 (포트폴리오 top 10) | ~10/min (피크) | `time.sleep(1)` 1초 분산 |
| `update-market-indices` | 매 5분, 9–16시, M–F | 1 batch 호출 (`get_all_market_quotes`) | ~1/min | 단일 batch endpoint |
| `refresh-market-pulse-cache` | **매 1분**, 9–16시, M–F | 5–10 호출 (FG·금리·인플·글로벌·캘린더) | **5–10/min 상시** | cache 미스 시 풀 호출 |
| `update-daily-prices` | 17:00, M–F | 10 호출 | 10/min | top 10 재호출 |
| `sync-sp500-eod-prices` | 18:00, M–F | **503 호출 × 0.3s 간격** | **~200/min × 2.5min** | 2.5분 동안 200 RPM 지속 |
| `update-sp500-change-percent` | 18:30, M–F | 0 (DB 전용) | 0 | API 없음 |
| `sync-sp500-financials` | 20:00, M–F | 101 심볼 × `apply_async(countdown=i*7)` | **~14/min × 12분** | 5일 회전, 심볼당 5+ FMP endpoint → 실제 60–80 RPM 가능 |
| `collect-sp500-news-fmp-{0615,1015,1315,1515,1715}` | 06:15/10:15/13:15/15:15/17:15, M–F | 503 심볼 / chord 6배치 동시 | `rate_limit='100/m'` per worker | macOS solo = 1 worker → **100/min hard cap** |
| `collect-press-releases-fmp` | 07:45, M–F | 50 심볼 직렬 호출 | 짧은 burst (~10–30s 안에 50) | rate_limit 없음 |
| `collect-general-news-fmp-{morning,noon,evening}` | 06:45/12:30/17:45, M–F | 1 호출 | 1 | – |
| `collect-market-news-{morning,noon,afternoon,evening}` | 08:00/12:00/15:00/18:00, M–F | (Finnhub/Marketaux 우선이나 fallback FMP 가능) | 미상 | aggregator service 확인 필요 |
| `sync-daily-market-movers` | 07:30, M–F | gainers/losers/actives endpoint | ~3 호출 | – |
| `keyword-generation-pipeline` | 08:00, **매일** | gainers fetch + Gemini chain | FMP 미상, **Gemini ↑** | mover_type=gainers 만 |
| `thesis-update-readings` | 18:00, M–F | active 가설의 FMP 지표 수만큼 | **rate-limit 없음** (sync loop) | 가설 N개 × 지표 M개 burst 위험 |
| `sync-etf-holdings` | 06:00 월, M | SPDR XLSX + FMP | – | 주1회 |
| `sync-supply-chain-batch` | 03:00 매월 15일 | SEC EDGAR + FMP | – | 월1회 |
| `sync-sp500-constituents` | 02:00 매월 1일 | FMP 1 호출 | – | 월1회 |
| `calculate-market-breadth` | 16:30, M–F | DailyPrice 기반 (FMP 미사용 추정) | – | – |
| `calculate-sector-heatmap` | 16:35, M–F | DailyPrice 기반 | – | – |

### 1.2 Gemini 의존 (Free 15 RPM / 1500 RPD)

| 태스크 | 스케줄 (NY) | 1회 호출량 | 위험 |
|---|---|---|---|
| `analyze-news-deep-batch` | 매일 **8/10/12/14/16/18시 :30**, M–F | max 50 articles × `RPM_DELAY=4s` | **6회 × 50 = 300 RPD** (1500/3 한도) |
| `extract-daily-news-keywords` | 매일 16:45 | 1회 (extractor 내부에서 N) | audit P0 #8 회피로 16:30 → 16:45 이동됨 |
| `enrich-relationship-keywords` | 매일 05:30 (neo4j queue) | limit=100 × `CALL_DELAY` | **400s = ~6.7분 burst** |
| `keyword-generation-pipeline` | 매일 08:00 | gainers Gemini chain | 미상 — 카운트 추적 부재 |
| `extract-news-relations` | 매일 09:00 | 24h 뉴스 매칭 | rule-based(?) — Gemini 사용 여부 미확인 |
| `generate-thesis-summaries` | 18:35, M–F | active ThesisSnapshot 수만큼 | ⚠️ **`_generate_via_gemini` 에 rate limit 없음** |
| `bulk_generate_korean_overviews` | 03:00 매월 1일 | S&P 500 batch_size=50 | 월1회 — RPD만 신경 |

> 🚨 **Gemini 핵심 위험**: `analyze-news-deep-batch` 는 `RPM_DELAY=4s` 로 14.5 RPM 으로 자체 제어, `enrich-relationship-keywords` 는 4s delay 로 14.5 RPM. 그러나 **`generate-thesis-summaries` 는 rate limit 코드 없음** (`thesis/tasks/summary.py:55–77`). 활성 ThesisSnapshot 이 16개 이상이면 첫 분에 15 RPM 초과 가능.

### 1.3 Alpha Vantage (5/min)

| 결과 | – |
|---|---|
| Beat 스케줄에서 AV 사용 태스크 | **0개** |
| AV 클라이언트 위치 | `api_request/__init__.py:8` (legacy 표시) |
| 결론 | **현재 스케줄에는 AV 호출 없음** → 5 RPM 한도 위배 위험 없음 |

### 1.4 Neo4j queue 전용 (`--pool=solo`, 동시 1)

| 태스크 | 스케줄 (NY) | 동시 충돌 위험 |
|---|---|---|
| `sec-sync-dirty-neo4j` | **매 5분** | ⚠️ 가장 빈번 — 12 fires/hour × 24h |
| `sync-news-to-neo4j` | 매일 8/10/12/14/16/18시 :45, M–F | – |
| `chainsight-sync-profiles-neo4j` | 12:00 매일 | – |
| `chainsight-sync-relations-neo4j` | 12:30 매일 | – |
| `chainsight-neo4j-dirty-sync` | 04:30 일 | – |
| `cleanup-expired-news-relationships` | 04:00 매일 | – |
| `enrich-relationship-keywords` | 05:30 매일 | – |
| `neo4j-health-check` | 매 6시간 (`*/6`) | – |

> Solo pool 제약: 위 태스크들은 직렬화된다. 5분 간격의 `sec-sync-dirty-neo4j` 가 길어지면 다른 neo4j 태스크 밀림.

---

## 2. 시간대별 ASCII 히트맵 (NY 시간, 평일 기준)

표기:
- `█` 매우 높음 (≥10 starts/h 또는 burst >100 호출/min)
- `▓` 높음 (5–9 starts/h)
- `▒` 중간 (2–4 starts/h)
- `░` 낮음 (1 starts/h)
- `·` 없음

### 2.1 Default queue 태스크 시작 빈도 (M–F)

```
시간:  00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
Start: ░  ░  ▒  ▒  ▒  ░  ▒  ▒  █  █  █  ▒  █  ▒  █  █  █  ▒  █  ▒  ░  ·  ░  ·
Rate-poll-load (9-16):
       ·  ·  ·  ·  ·  ·  ·  ·  ·  █  █  █  █  █  █  █  █  ·  ·  ·  ·  ·  ·  ·
                                  ↑─── 매 1min market-pulse, 매 5min realtime+indices ───↑
```

(Rate-poll-load = `refresh-market-pulse-cache(1m)` + `update-realtime-prices(5m)` + `update-market-indices(5m)` + `calculate-portfolio-values(10m)` + `check-screener-alerts(15m)` 동시 부하)

### 2.2 FMP API 부하 (호출/분 추정)

```
시간:  00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
FMP :  ·  ·  ░  ░  ·  ·  ▒  █  █  ▓  █  ▓  ▓  ▒  ▓  █  ▓  █  █  ░  █  ·  ·  ·
                            ↑           ↑           ↑     ↑     ↑  ↑  ↑     ↑
                          07:30/45    10:15        13:15 15:15 17:15│ │     │
                          movers     SP500 news                     │ │ 18:00 폭발
                          + press                                   │ │ EOD+thesis
                          rel                                       │ 17:00 daily
                                                                    │ + 17:15 SP500 news
                                                                    │
                                                                  17–18시 누적
```

**18:00 NY (FMP 피크)**:
- `sync-sp500-eod-prices` 503 × 0.3s = **200/min × 2.5min**
- `thesis-update-readings` 활성 가설 × FMP 지표 (rate limit 없음, burst)
- `collect-market-news-evening` 변동성 있는 호출
- `update-economic-indicators` (FRED, FMP 아님)
- → **추정 250–280 RPM, 300/min 한도에 근접**, 가설/지표 늘어나면 위배 가능

**20:00 NY (FMP 두 번째 피크)**:
- `sync-sp500-financials` 101 심볼 × 7s = 14.4/min, 심볼당 endpoint 5–6개 = **70–85 RPM 지속 12분**
- 다른 동시 태스크 없음 → 안전

### 2.3 Gemini 부하 (RPM 누적)

```
시간:  00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
Gem :  ·  ·  ·  ░  ·  █  ·  ·  █  ·  █  ·  █  ·  █  ·  █  ·  █  ·  ·  ·  ·  ·
                   ↑     ↑           ↑           ↑           ↑           ↑
                 03:00   05:30      08:30       12:30       16:30       18:30
                 (월1)   enrich     analyze     analyze     analyze     analyze
                 KO      (~14.5     (~14.5      …           …           +18:35
                 over    RPM        RPM                                 thesis-
                 view    burst      burst)                              summaries
                         ~7min      ~3.3min                             (no limit!)
```

**05:30 NY**: `enrich-relationship-keywords` (~14.5 RPM × 7분). Gemini 다른 태스크 없음 → 안전.

**08:30 / 10:30 / 12:30 / 14:30 / 16:30 / 18:30**: `analyze-news-deep-batch` 6회 (M–F).
- 단일 호출당 4초 분산 → 한 묶음당 14.5 RPM × 3.3분 ≈ **48 호출/회**
- 일일 누적 = 6회 × 50 ≈ **300 RPD** (1500/일 한도의 20%) 안전

**16:45 NY**: `extract-daily-news-keywords` 단독 (audit P0 #8 로 16:30 분리됨). 안전.

**18:35 NY** (피크): `generate-thesis-summaries`
- ThesisSnapshot loop, **rate limit 없음**
- 16개 이상 가설 → **첫 분에 15 RPM 초과 위험**
- `analyze-news-deep` 18:30 의 잔여 호출 (18:33:20 종료 예상) 과 거의 안 겹치지만 retry 시 충돌 가능
- 🚨 **P1 위험**

### 2.4 Neo4j queue 부하

```
시간:  00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
Neo :  ░  ░  ░  ░  ▓  ▓  ░  ░  ▒  ░  ▒  ░  ▓  ░  ▒  ░  ▒  ░  ▒  ░  ░  ░  ░  ░
       └────────────────── sec-sync-dirty-neo4j 매 5분 (12 starts/h 상시) ──────┘
                  ↑     ↑           ↑           ↑           ↑           ↑
                  04:00 05:30       08:45       12:00       16:45      18:45
                  expired enrich    sync-news   sync-prof   sync-news  sync-news
                          (30min)              + 12:30      (LLM 후)
                                              relations
```

> Solo 워커가 매 5분 sec-dirty-sync 를 처리하느라, 같은 분에 떨어지는 다른 neo4j 태스크는 **최대 5분 지연** 가능.

---

## 3. Rate Limit 위반 / 근접 구간

### 3.1 FMP — 300/min, 10,000/일

| 시간 (NY) | 추정 RPM | 한도 대비 | 상태 | 권장 |
|---|---|---|---|---|
| 09:00–16:00 (장중) | 17–25 (poll 합산) | 6–8% | 🟢 안전 | – |
| 17:00 | ~12 | 4% | 🟢 안전 | – |
| 17:15 (SP500 news) | 100 (cap) | 33% | 🟢 안전 | rate_limit hard cap |
| **18:00** | **250–280** | **83–93%** | 🟡 **근접** | 분산 또는 thesis-update-readings 지연 |
| 18:15–18:30 | <50 | 17% | 🟢 안전 | – |
| **20:00–20:12** | **70–85** (12분 지속) | 23–28% | 🟢 안전 | – |
| 일일 호출 합계 | ~6,000–7,500 추정 | 60–75% | 🟡 **모니터링 필요** | – |

**🚨 Critical 발견 — 18:00 NY 피크**:

`sync-sp500-eod-prices` 단독으로 0.3s 간격 = 200/min. 동일 시각에 시작하는 다른 FMP 태스크들과 합산하면 한도 근접. 특히 `thesis-update-readings` 는 직렬 sync loop 로 rate limit 코드 부재 (`thesis/tasks/eod_pipeline.py:273-359`). 활성 가설 수가 늘어나면 18:00 첫 분에 burst → FMP 429.

### 3.2 Gemini — 15 RPM, 1500 RPD

| 태스크 | 자체 제어 | 동시 충돌 | 상태 |
|---|---|---|---|
| `analyze-news-deep-batch` | ✅ `RPM_DELAY=4s` | 같은 분에 다른 Gemini 없음 | 🟢 안전 |
| `enrich-relationship-keywords` | ✅ `CALL_DELAY=4s` | – | 🟢 안전 |
| `extract-daily-news-keywords` | – (단발) | – | 🟢 안전 (16:45 분리됨) |
| **`generate-thesis-summaries`** | ❌ **없음** | analyze-deep 18:30 직후 | 🟡 **P1 위험** |
| `bulk_generate_korean_overviews` | 미확인 | 03:00 단독 | 🟢 안전 |

**일일 RPD 누적 추정**:
- analyze-news-deep × 6회/일 × 50 = 300
- enrich-relationship-keywords 1회 × 100 = 100
- extract-daily-news-keywords 1회 × ~1 = 1
- generate-thesis-summaries × 1회 × N (가설 수)
- → **총 ~400–500 RPD**, Free 1500 한도의 30% → **안전**

### 3.3 Alpha Vantage — 5/min

- Beat 스케줄에 호출 없음. **위반 위험 0**.

---

## 4. 시간대별 동시 시작 (Concurrency Hot Spots)

### 4.1 18:00 NY — 최대 충돌 지점 🚨

| 태스크 | 큐 | 자원 | 비고 |
|---|---|---|---|
| `update-economic-indicators` | default | FRED | 가벼움 |
| `collect-market-news-evening` | default | Finnhub/Marketaux/FMP | 중간 |
| `sync-sp500-eod-prices` | default | FMP × 503 | **무거움 (2.5분)** |
| `thesis-update-readings` | default | FMP × N indicators | **rate limit 없음, burst** |

**문제**: macOS solo worker = 동시 1 작업. 위 4개가 같은 분에 시작 → **순차 처리되며 ~3–5분 큐 적체**. 이후 18:15 작업이 늦게 시작됨.

### 4.2 18:15–18:30 NY — EOD 파이프라인 도미노

| 시각 | 태스크 | 의존성 |
|---|---|---|
| 18:15 | `classify-news-batch` (M-F 18:15) | – |
| 18:15 | `analyze-news-deep-batch` (M-F 18:15) | classify 완료 가정 (15분 분리) |
| 18:15 | `thesis-calculate-scores` | **`thesis-update-readings` 18:00 완료 가정** ⚠️ |
| 18:30 | `analyze-news-deep-batch` (스케줄상 :30) | ⚠️ — schedule 충돌 |
| 18:30 | `sync-news-to-neo4j` | analyze 완료 가정 |
| 18:30 | `run-eod-pipeline` | DailyPrice 동기화 완료 가정 |
| 18:30 | `update-sp500-change-percent` | DailyPrice 완료 가정 |
| 18:30 | `thesis-create-snapshots` | scores 완료 가정 |
| 18:35 | `thesis-generate-summaries` | snapshots 완료 가정 |

> ⚠️ **선후 의존성 검증 부재**: 위 태스크들은 시간 분리(15분)로 의존성을 표현하지만, **앞 태스크가 15분을 초과해 끝나지 않으면 후속이 빈 데이터로 실행**. 특히:
> - 18:00 sync-sp500-eod-prices 가 솔로 워커에서 뒤로 밀리면 18:30 run-eod-pipeline 이 어제 데이터로 실행
> - 18:00 thesis-update-readings 가 늦으면 18:15 thesis-calculate-scores 가 stale reading 으로 계산
> - 의존성 보장은 **시간 간격 + idempotent retry** 에만 의존 (chord/chain 미사용)

### 4.3 :15 / :30 / :45 매시 (8/10/12/14/16/18) — News Pipeline v3

같은 분 내에서:
- :15 classify (rule-based, default queue) — 가벼움
- :30 analyze-news-deep (Gemini, default queue) — 3.3분 점유
- :45 sync-news-to-neo4j (neo4j queue) — Solo 워커

> Solo 풀이라 default 워커 한 개가 :30 의 analyze 를 처리하면 :15 의 classify 가 느릴 경우 :30 가 바로 뒤따른다. 큐 분리(neo4j) 덕분에 :45 sync 는 별도 워커.

### 4.4 12:00 NY 동시 다발

같은 시각 시작:
- `update-economic-indicators` (FRED)
- `collect-market-news-noon` (FMP)
- `chainsight-sync-profiles-neo4j` (neo4j queue)
- `sec-seed-relations-to-chainsight` (default)

→ default 워커 3개 직렬. neo4j 분리.

### 4.5 04:00 NY 일요일 새벽 ML 도미노

```
03:00 train-importance-model (sklearn, 30~? min)
03:30 generate-shadow-report (depends 03:00 결과)
04:00 cleanup-expired-news-relationships (neo4j)
04:00 check-auto-deploy (depends 03:30)
04:15 generate-weekly-ml-report
04:20 monitor-ml-performance
04:30 train-lightgbm-model (lightgbm, 시간 미상)
04:30 chainsight-neo4j-dirty-sync (neo4j)
05:00 cleanup-task-results
```

> 03:00 train 이 30분을 초과하면 03:30, 04:00, 04:15, 04:20 가 도미노로 밀림. **time_limit 미설정인 일부 태스크가 위험**.

---

## 5. 잠재적 데이터 경합

| 경합 가능성 | 태스크 A | 태스크 B | 시각 (NY) | 자원 |
|---|---|---|---|---|
| `DailyPrice` 동시 쓰기 | `sync-sp500-eod-prices` | `update-daily-prices` | 17:00 vs 18:00 | 1시간 분리되어 안전 |
| `IndicatorReading` upsert 경쟁 | `thesis-update-readings` (자체 sync loop) | – | 18:00 | 단일 task 내 직렬 |
| `Stock.change_percent` race | `update-realtime-prices` (5분) | `update-sp500-change-percent` | 9–16 vs 18:30 | 시간 분리 |
| `NewsArticle.llm_*` upsert | `analyze-news-deep` | `sync-news-to-neo4j` | :30 vs :45 | 15분 분리 |
| `cache:macro:market_pulse_full` | `refresh-market-pulse-cache` (1분) | API GET 핸들러 | 9–16 | cache.delete + set 사이 race 가능 (window <1s) |
| `chainsight` 프로파일 / 관계 | `chainsight-all-profiles` (Sat 02:00) | `chainsight-co-mentions` (10:00 daily) | 토요일 동시 진행 가능 | 02:00 ~ 04:30 사이 토요일 5개 chainsight 직렬 — 각 7200s soft → 최악 36000s = 10시간 |

---

## 6. 구체적 위반 / 위험 요약 (우선순위)

### P0 (즉시 조치 권장)

1. **`generate-thesis-summaries` 에 Gemini rate limit 부재**
   - 위치: `thesis/tasks/summary.py:55-77`
   - 위험: 활성 ThesisSnapshot 16개 이상 시 첫 분에 15 RPM 초과 → 429
   - 권장: 호출 사이 4s `time.sleep` 또는 `RPM_DELAY` 도입

2. **18:00 NY FMP burst (`sync-sp500-eod-prices` + `thesis-update-readings` 동시)**
   - 추정 250–280 RPM (한도 300의 83–93%)
   - 가설 / 지표 증가 시 한도 초과 가능
   - 권장: thesis-update-readings 를 17:50 또는 19:00 으로 분리

### P1 (모니터링 필요)

3. **`thesis-update-readings` 의 직렬 sync loop, rate limit 부재**
   - 위치: `thesis/tasks/eod_pipeline.py:273-359`
   - FMP 호출이 무제한 burst → 가설 100개 / 지표 5개 시 즉시 500 호출 시도

4. **Beat schedule dict ↔ DB `PeriodicTask` drift 자동 검증 부재**
   - `celery.py:128-133` 에 명시: 마지막 수동 체크 2026-04-24
   - 그 이후 추가된 `chainsight-heat-score-daily`, `sec-seed-relations-to-chainsight` 외에 새 항목이 dict 에는 있지만 DB 에 없을 위험

5. **EOD 파이프라인 의존성이 `crontab` 시간 간격에만 의존**
   - 18:00 → 18:15 → 18:30 → 18:35 의 도미노가 chain/chord 가 아닌 시각 격자
   - 앞 단계가 15분 초과 시 빈/stale 데이터로 후속 실행
   - 권장: chain 또는 sentinel 값(`is_complete`) 체크

### P2 (개선 여지)

6. **`refresh-market-pulse-cache` 1분 주기**
   - 9–16시 매분 5–10 FMP 호출 = 480 RPM 누적 (시장시간 기준 시간당 ~360 호출)
   - 캐시 hit 율 측정 부재 — 실제 외부 호출 빈도 파악 필요

7. **`sec-sync-dirty-neo4j` 5분 주기 + neo4j solo 워커**
   - 다른 neo4j 태스크 (5분 동기화 + 6시간 헬스체크 + 일/주간 작업) 와 큐 경쟁
   - 12 fires/hour × 24h = 288 fires/day, dirty 누적 적으면 빈 실행

8. **하드코딩된 NY hour 와 `# UTC` 주석 불일치**
   - `chainsight-heat-score-daily` 주석: "매일 07:00 UTC" → 실제 07:00 NY (1–2시간 오프셋)
   - `chainsight-seed-selection`, `chainsight-neo4j-dirty-sync` 동일 문제
   - 운영자 혼선 유발

---

## 7. 빈 시간대 (낮은 활용도)

| 시간 (NY) | 빈도 | 활용 가능 |
|---|---|---|
| 21:00–01:00 | 거의 비어있음 (22:00 update-economic-indicators 만) | 무거운 배치 이전 추천 |
| 02:00–05:00 | 새벽 배치 집중 | 추가 부하 회피 |
| 11:00–12:00 (M-F) | poll 외 단일 태스크만 | 적정 |
| 19:00–20:00 (M-F) | collect-ml-labels, backfill-signal-accuracy 둘 | 적정 |

→ **18:00 의 sync-sp500-eod / thesis-update-readings 일부를 19:30 또는 21:00 으로 이동 가능**.

---

## 8. 요약 권장 조치 (코드 수정 없음, 설계 변경 제안)

| # | 조치 | 영향 |
|---|---|---|
| 1 | `generate-thesis-summaries` 에 4s delay 추가 | Gemini 429 방지 |
| 2 | `thesis-update-readings` 시각 17:50 또는 19:00 으로 이동 | 18:00 FMP burst 분산 |
| 3 | EOD 의존성을 chain 으로 묶기 (sync-sp500-eod → run-eod-pipeline → backfill-signal-accuracy) | stale 데이터 위험 제거 |
| 4 | beat_schedule dict ↔ DB drift 검증 자동화 (`manage.py check_beat_drift`) | 누락 태스크 무실행 방지 |
| 5 | `# UTC` 주석을 `# NY (CELERY_TIMEZONE)` 로 통일 | 운영 혼선 제거 |
| 6 | `refresh-market-pulse-cache` 캐시 hit/miss 메트릭 수집 | 1분 주기 적정성 평가 |
| 7 | 18:00 의 4개 동시 시작 → 분/순차 분리 (18:00 / 18:02 / 18:05) | solo 워커 큐 적체 해소 |
| 8 | `thesis-update-readings` 직렬 loop 에 4s sleep + circuit breaker 도입 | FMP burst 위험 차단 |

---

## 9. 통계

- **총 beat_schedule entries**: 약 73개
- **default queue 점유**: ~59개
- **neo4j queue 점유**: ~14개
- **FMP 의존 태스크**: ~16개
- **Gemini 의존 태스크**: ~7개
- **Alpha Vantage 의존 태스크**: 0개
- **Cron 매시 분 폴링 (≥1회/시간)**: 5개 (market-pulse 1m, realtime/indices 5m, portfolio 10m, sec-dirty 5m)

---

**감사 완료**. 본 보고서는 `config/celery.py` 의 `app.conf.beat_schedule` 선언적 dict 를 분석한 결과이며, 실제 실행 일정은 `django_celery_beat.PeriodicTask` DB 테이블을 따릅니다. dict ↔ DB drift 검증이 본 감사 범위 밖이므로 별도 확인이 필요합니다.
