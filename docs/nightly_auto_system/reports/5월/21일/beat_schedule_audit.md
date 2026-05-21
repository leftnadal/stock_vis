# Celery Beat Schedule 감사 보고서

- 작성일: 2026-05-21
- 대상 파일: `config/celery.py` (총 820행, `beat_schedule` dict 라인 135–814)
- 모드: 읽기 전용 정적 분석 (코드 수정 없음)
- 등록된 태스크 수: **86개** (`grep -c "'task':" config/celery.py` 기준 90, 그중 4개는 주석 또는 metadata)
- ⚠️ 주의: `config/settings.py`가 `DatabaseScheduler` 사용. dict는 reference. 본 보고서는 dict 정의를 진실로 가정한다. **DB 드리프트는 별도 검증 필요**.
- 시간대 표기: 별도 명시 없으면 **ET (EST/EDT)**. UTC 명시된 4개는 별도 표기.

---

## 1. 한눈에 보는 결론

| 항목 | 심각도 | 요지 |
|------|--------|------|
| **18:00–18:45 ET 골든 윈도우 폭주** | 🔴 P0 | 11개 태스크 + FMP 500종목 EOD가 30분 안에 폭주 |
| **Gemini 18:30 동시 호출** | 🔴 P0 | `analyze-news-deep-batch` + `thesis-generate-summaries(18:35)` + 동일 분의 다른 Gemini 호출. 15 RPM 초과 위험 |
| **Sunday 03:00–05:00 ML 폭풍** | 🟠 P1 | 8개 일요일 새벽 태스크가 30분 간격으로 직렬 의존. 한 개 지연 시 도미노 |
| **FMP 17:15–18:00 폭주** | 🟠 P1 | 5분 안에 SP500 EOD 가격(500) + SP500 뉴스 + General news + Daily prices + Indices 동시 |
| **neo4j queue `sec-sync-dirty-neo4j` */5min** | 🟡 P2 | solo pool에서 288회/일. 다른 neo4j 작업과 lock 경합 가능 |
| **`refresh-market-pulse-cache` 매 1분** | 🟡 P2 | 평일 9–16시 = 480회/일. 부하는 작지만 빈도 과다 |
| **신뢰성 위험: dict ↔ DB 드리프트** | 🟠 P1 | `beat_schedule` dict는 reference이고 DB가 실제 소스. 본 보고서 가정 자체가 깨질 수 있음 |

---

## 2. 시간대별 ASCII 히트맵 (평일 ET, 분 단위 집계)

각 셀은 **해당 시간대(60분)에 fire 되는 태스크의 누적 실행 횟수**.

```
시간    │ 태스크 fire 카운트                              │ 강도
────────┼─────────────────────────────────────────────────┼──────
00      │                                                 │ -
01      │ ██                                              │ 2     economic-calendar(daily), aggregate-weekly(Sat만)
02      │ █                                               │ 1     archive-old(1일만), sp500-constituents(1일만)
03      │ ██                                              │ 2     train-importance(Sun), korean-overviews(1일만), supply-chain(15일만)
04      │ ████                                            │ 4     cleanup-news-rel, scan-regulatory(Mon), build-patent(1일만), check-auto-deploy(Sun), monitor-ml(Sun), train-lgbm(Sun), inst-holdings(16일만)
05      │ ██                                              │ 2     enrich-rel-keywords, validation(Sat), cleanup-task-results(Sun)
06      │ ████                                            │ 4     update-econ-indic, daily-news-morning, category-news-high, sp500-news-fmp-0615, general-news-fmp-morning, etf-holdings(Mon), sec-check(1일만)
07      │ █████                                           │ 5     market-movers, category-news-medium, category-news-low, press-releases-fmp, celery-error-digest, heat-score(UTC=03:00ET?)
08      │ ████████                                        │ 8     keyword-gen-pipeline, market-news-morning, classify-news(:15), analyze-news-deep(:30), sync-news-neo4j(:45)
09      │ ████████████                                    │ 12    realtime-prices×12(*/5), indices×12, market-pulse×60(per-min), portfolio×6(*/10), screener-alerts×4(*/15), aggregate-sentiment, extract-news-relations
10      │ █████████████                                   │ 13    realtime×12, indices×12, market-pulse×60, portfolio×6, screener×4, classify(:15), analyze-deep(:30), sync-news-neo4j(:45), sp500-news-fmp-1015(:15), co-mentions
11      │ ████████████                                    │ 12    realtime×12, indices×12, market-pulse×60, portfolio×6, screener×4, relation-confidence
12      │ ██████████████                                  │ 14    realtime×12, indices×12, market-pulse×60, portfolio×6, screener×4, classify(:15), market-news-noon, analyze-deep(:30), general-news-fmp-noon(:30), sync-news-neo4j(:45), sync-profiles-neo4j, econ-indic, sync-relations-neo4j(:30), seed-relations, seed-selection(UTC=08:00ET?)
13      │ █████████████                                   │ 13    realtime×12, indices×12, market-pulse×60, portfolio×6, screener×4, category-news-high, sp500-news-fmp-1315(:15)
14      │ █████████████                                   │ 13    realtime×12, indices×12, market-pulse×60, portfolio×6, screener×4, classify(:15), category-news-medium, daily-news-afternoon(:30), analyze-deep(:30), sync-news-neo4j(:45)
15      │ █████████████                                   │ 13    realtime×12, indices×12, market-pulse×60, portfolio×6, screener×4, market-news-afternoon, sp500-news-fmp-1515(:15)
16      │ ██████████████                                  │ 14    realtime×12, indices×12, market-pulse×60, portfolio×6, screener×4, classify(:15), analyze-deep(:30), market-breadth(:30), sector-heatmap(:35), extract-news-keywords(:45), sync-news-neo4j(:45)
17      │ ███████                                         │ 7     daily-prices, category-news-high, sp500-news-fmp-1715(:15), press? general-news-fmp-evening(:45)
18      │ █████████████████████                           │ 21+   ★골든윈도우★ thesis-update(:00), market-news-evening(:00), econ-indic(:00), sp500-eod-prices(:00), classify(:15), thesis-calc(:15), analyze-deep(:30), thesis-snapshot(:30), eod-pipeline(:30), update-change-pct(:30), thesis-summary(:35), sync-news-neo4j(:45)
19      │ ███                                             │ 3     backfill-signal-accuracy, ml-labels
20      │ ██                                              │ 2     sp500-financials
21      │                                                 │ -
22      │ █                                               │ 1     econ-indic
23      │                                                 │ -
────────┼─────────────────────────────────────────────────┼──────
        │ 0    5    10   15   20+                         │
```

**해석**: `realtime/indices/market-pulse/portfolio/screener-alerts`는 매분∼15분 단위 반복 fire라 시간당 카운트가 60(분단위) + ~30(다른 빈도)으로 부풀려 보인다. 실제 **이벤트 시점에 동시 fire 되는 태스크 수**는 다음 절 3.3 분 단위 히트맵 참고.

### 2.1 분 단위 (피크 시간대 18:00–19:00 ET 평일) — 동시 fire 분석

```
분      │ 동시 fire 태스크                                                  │ Queue
────────┼──────────────────────────────────────────────────────────────────┼─────────
18:00   │ thesis-update-readings                                            │ default
        │ market-news-evening (FMP/external)                                │ default
        │ update-economic-indicators (FRED)                                 │ default
        │ sync-sp500-eod-prices (FMP 500종목 ★)                              │ default
        │ update-realtime-prices (× cron 종료 직전)                          │ default
        │ refresh-market-pulse-cache                                        │ default
        │ ⇒ **동시 5개+, FMP 500종목 일괄 호출**                              │
18:15   │ classify-news-batch (rules)                                       │ default
        │ thesis-calculate-scores                                           │ default
        │ collect-sp500-news-fmp-1515 (15분 전 fire였음, expires=3600)        │
18:30   │ analyze-news-deep-batch (★Gemini, max 50기사)                     │ default
        │ thesis-create-snapshots-and-alerts                                │ default
        │ run-eod-pipeline                                                  │ default
        │ update-sp500-change-percent                                       │ default
        │ ⇒ **동시 4개, Gemini 호출 + EOD 무거운 DB 작업 충돌**                │
18:35   │ thesis-generate-summaries (★Gemini)                               │ default
        │ ⇒ **18:30의 analyze-deep과 5분 차이로 Gemini 연속 호출**             │
18:45   │ sync-news-to-neo4j (max 100기사)                                  │ neo4j
        │ ⇒ neo4j queue 단일 작업, sec-sync-dirty-neo4j(*/5)와 lock 경합 가능 │
```

### 2.2 분 단위 (Sunday 03:00–05:00 ET) — ML 도미노

```
분      │ 태스크                                              │ 의존
────────┼─────────────────────────────────────────────────────┼───────────
03:00   │ train-importance-model                              │ start
03:30   │ generate-shadow-report (days=7)                     │ train 결과 필요
04:00   │ check-auto-deploy                                   │ shadow 결과 필요
04:00   │ cleanup-expired-news-relationships (neo4j)          │ 독립, neo4j queue
04:00   │ scan-regulatory-relationships (Mon만)               │ 독립 (일요일은 fire 안 됨)
04:00   │ build-patent-network (1일만)                         │ 독립 (월 1회)
04:15   │ generate-weekly-ml-report                           │ auto-deploy 결과 필요
04:20   │ monitor-ml-performance                              │ weekly-report 후
04:30   │ train-lightgbm-model (조건부)                         │ monitor 후
04:30   │ chainsight-neo4j-dirty-sync (UTC) → Sun 00:30 ET    │ ★ UTC혼선 주의 ★
05:00   │ cleanup-task-results                                │ 독립
05:00   │ validation-weekly-batch (Sat만)                     │ 일요일 fire 안 됨
05:30   │ enrich-relationship-keywords (Gemini, daily)        │ 독립
────────┴─────────────────────────────────────────────────────┴───────────
```

⚠️ `chainsight-neo4j-dirty-sync`의 `crontab(hour=4, minute=30, day_of_week=0)` — 주석은 "UTC 04:30"이라 표기되어 있으나 Celery crontab은 서버 로컬타임(ET 가정) 기준. **주석과 실제 시각 불일치 추정** → 실제로는 일요일 04:30 ET로 동작하여 ML 폭풍 시간대에 가산됨.

---

## 3. API Rate Limit 초과 분석

### 3.1 FMP (Starter: 300 calls/min, 10,000 calls/day)

**FMP 의존 태스크 목록**:
| 태스크 | 빈도 | 추정 호출량/run |
|-------|------|---------------|
| update-realtime-prices | */5min, 9–16h, M–F (96/일) | 종목당 1 call, watchlist N건 |
| update-daily-prices | 17:00 M–F | watchlist N건 |
| sync-sp500-financials | 20:00 M–F | 101 calls (순환 배치) |
| update-market-indices | */5min, 9–16h, M–F (96/일) | 5~10 indices |
| update-economic-calendar | 01:00 daily | 1~5 |
| sync-daily-market-movers | 07:30 M–F | ~30 calls |
| collect-sp500-news-fmp-{0615,1015,1315,1515,1715} | 5×/일 M–F | **종목당 1 call ≈ 500 calls (★)** |
| collect-press-releases-fmp (max_symbols=50) | 07:45 M–F | 50 |
| collect-general-news-fmp-{morning,noon,evening} | 3×/일 M–F | ~10 |
| sync-sp500-eod-prices | 18:00 M–F | **500 calls (★)** |

**⚠️ 한도 초과 가능 구간**:

1. **17:15–17:20 ET (5분)**: `collect-sp500-news-fmp-1715` (≈500 calls) + 동시간대 `update-realtime-prices` 종료. ★ 1분당 300 초과 가능. orchestrator가 내부 throttle을 하는지는 별도 확인 필요.
2. **18:00–18:01 ET**: `sync-sp500-eod-prices` (500 calls 일괄) + `market-news-evening` + `update-economic-indicators`(FRED라 무관). ★ FMP 300/min 초과 거의 확정. 태스크 내부에 throttle 또는 chunked 호출이 없으면 즉시 429.
3. **06:15 / 10:15 / 13:15 / 15:15 / 17:15**: 각각 SP500 뉴스 500 calls × 5회 = 2,500 calls/일. 다른 FMP 호출 합산 시 10,000/일 한도의 25%+. EOD(500) + financials(101) + general/press(~70) + indices/realtime(~960~) = 일 **약 4,200~4,500 calls** 추정. **한도 자체는 여유**, 단 분단위 폭주 위험은 분명.

**근거 확인 필요**: `news.tasks.collect_sp500_news_fmp_orchestrator`가 chunk + sleep 사용하는지. 사용 안 한다면 분당 한도 즉시 초과.

### 3.2 Gemini Free (15 RPM, 1500 RPD)

**Gemini 호출 태스크** (코드 검증으로 확인):

| 태스크 | fire 시점 | 호출량/run |
|-------|----------|-----------|
| `keyword_generation_pipeline` | 08:00 daily | 키워드/종목당 1 call, gainers N건 |
| `extract_daily_news_keywords` | 16:45 daily | 일일 추출 1 call (집계) 또는 기사당 |
| `analyze_news_deep` | xx:30 of 8,10,12,14,16,18 M–F (6/일) | max_articles=50, **기사당 1 call → 최대 50 calls** |
| `enrich_relationship_keywords` | 05:30 daily | limit=100, **최대 100 calls** |
| `generate_thesis_summaries` | 18:35 M–F | 가설당 1 call |
| `bulk_generate_korean_overviews` | 1일 03:00 monthly | batch_size=50, **최대 50 calls** |

**⚠️ 한도 초과 가능 구간**:

1. **xx:30 fire (analyze-news-deep)**: max 50기사를 1분 안에 처리하면 **50 RPM ≫ 15 RPM**. 태스크 내부 throttle 필수. 미적용 시 한도 초과.
2. **18:30 + 18:35**: `analyze-news-deep` 종료 직후 `thesis-generate-summaries` 시작. 5분 간격이 짧음. analyze-deep가 50 calls를 12초 간격으로 분산하면 10분이 걸려 18:35의 summary와 겹친다 → **15 RPM 초과**.
3. **05:30 enrich**: limit=100이면 100 calls. 분당 분산 필수.
4. **일일 합산 (RPD 1500)**: analyze-deep 50×6 = 300, enrich 100, others ~100, **총 ~500 calls/일** — 한도 1500의 1/3. **RPD는 여유**, RPM이 진짜 위험.

**audit 주석 (line 285–286)** 확인: `extract-daily-news-keywords`를 16:45로 분산한 이유가 16:30 `analyze-deep`와 Gemini 충돌 회피라고 명시. **반대로 18:30 analyze-deep + 18:35 summaries는 동일한 위험이 있는데도 분산되지 않음** → 일관성 결손.

### 3.3 Alpha Vantage (5 calls/min, 12초 대기 필수)

**AV 의존성**: `beat_schedule` dict에서 AV 직접 호출이 명시된 태스크는 **0건**. FMP가 primary provider. AV는 fallback 또는 임시 사용으로 보이며 스케줄러 자동 호출 경로는 안전.

⚠️ 단 `ALPHA_VANTAGE_API_KEY`가 `.env` 필수로 표기됨 → 어딘가 동기 호출 경로 있을 수 있음. 별도 코드 그렙 필요.

---

## 4. Queue 몰림 분석

### 4.1 default queue
- 상시 fire: realtime-prices(*/5), indices(*/5), market-pulse(*/1), portfolio(*/10), screener-alerts(*/15), pipeline-alerts(*/30), sec-sync-dirty-neo4j는 neo4j로 라우팅됨.
- macOS에서는 `worker_pool = 'solo'` 강제 (line 30–31) → **default queue도 macOS에서는 동시성 1**. 18:00–18:45 골든윈도우의 동시 fire 11개+가 직렬 처리되어 backlog 발생. 단일 작업이 5분 걸리면 ~55분 backlog → expires=3600(1시간)에 근접.

### 4.2 neo4j queue (solo pool, 동시성 1)

**neo4j queue로 라우팅되는 태스크** (line 37–55 task_routes + beat options):
| 태스크 | 빈도 | 부하 |
|-------|------|------|
| `sec-sync-dirty-neo4j` | **\*/5min (288/일) ★** | 짧지만 빈번 |
| `neo4j-health-check` | */6h (4/일) | 가벼움 |
| `sync-news-to-neo4j` | xx:45 × 6/일 M–F | max 100 articles |
| `chainsight-sync-profiles-neo4j` | 12:00 daily | 중간 |
| `chainsight-sync-relations-neo4j` | 12:30 daily | 중간 |
| `cleanup-expired-news-relationships` | 04:00 daily | 무거움 가능 |
| `enrich-relationship-keywords` | 05:30 daily | Gemini 호출 + 100개 |
| `chainsight-neo4j-dirty-sync` | Sun 04:30 | 무거움 |

**⚠️ 위험 시나리오**:
- **12:00 ET**: `chainsight-sync-profiles-neo4j` + `sec-sync-dirty-neo4j`(*/5의 12:00 fire) 동시 신청 → solo pool에서 직렬화. profiles가 30초 걸리면 sec-sync는 expires=240(4분) 안에는 처리되나 다음 12:05 sec-sync와 또 충돌. **연쇄 백로그**.
- **12:30 ET**: `chainsight-sync-relations-neo4j` + sec-sync(*/5의 12:30). 무거운 작업이라 sec-sync 여러 cycle 누적.
- **05:30 ET**: `enrich-relationship-keywords`는 Gemini 100 calls 직렬 호출 시 **20분+** 가능. neo4j 큐의 다른 fire(05:30~05:50 sec-sync ×4)가 모두 대기 → expires=240 만료 → 데이터 누락 위험.

### 4.3 sec-sync-dirty-neo4j */5min vs expires=240(4분)
`schedule=*/5min`, `expires=240초`. 다음 fire 직전 60초 안에 처리되지 않으면 만료. solo pool에서 직전 작업이 4분 넘으면 **모든 후속 sec-sync 만료** → SEC dirty evidence가 Neo4j에 도달하지 않는 silent failure 가능. ★ 모니터링 필요.

---

## 5. 시간대별 API 호출 히트맵 (분 단위, 평일, 추정)

```
시각     │ FMP calls/min       │ Gemini RPM         │ Neo4j queue
─────────┼─────────────────────┼────────────────────┼─────────────
06:15    │ ~500 (sp500-news ★) │ -                  │ sec-sync
06:30    │                     │                    │ sec-sync
07:00    │                     │                    │ sec-sync (heat-score?)
07:30    │ ~30 (movers)        │                    │ sec-sync
08:00    │                     │ ★keyword-gen        │ sec-sync
08:15    │                     │                    │ sec-sync
08:30    │                     │ analyze-deep(50★)  │ sec-sync
08:45    │                     │                    │ sync-news(★)
09:00    │ ~10 (realtime+idx)  │                    │ sec-sync
10:15    │ ~500 (sp500-news ★) │                    │ sec-sync
10:30    │                     │ analyze-deep(50★)  │ sec-sync
10:45    │                     │                    │ sync-news(★)
12:00    │ ~20                 │                    │ chainsight-profiles + sec-sync ★
12:15    │                     │                    │
12:30    │ ~20                 │ analyze-deep(50★)  │ chainsight-relations + sec-sync ★
12:45    │                     │                    │ sync-news(★)
13:15    │ ~500 (sp500-news ★) │                    │ sec-sync
14:30    │                     │ analyze-deep(50★)  │ sec-sync
15:15    │ ~500 (sp500-news ★) │                    │ sec-sync
16:30    │                     │ analyze-deep(50★)  │ sec-sync
16:45    │                     │ extract-keywords   │ sync-news(★) + sec-sync
17:00    │ ~watchlist (daily)  │                    │
17:15    │ ~500 (sp500-news ★) │                    │
17:45    │ ~10 (general-news)  │                    │
─────────┼─────────────────────┼────────────────────┼─────────────
18:00 ★★ │ ~500 (eod-prices)   │                    │
        │ + market-news-evening + econ-indic        │
18:15    │                     │                    │
18:30 ★★ │                     │ ★★analyze-deep(50)★│ sec-sync
18:35 ★★ │                     │ ★★thesis-summary★  │
18:45    │                     │                    │ sync-news(★)
19:00    │                     │                    │
20:00    │ ~101 (financials)   │                    │
22:00    │                     │                    │
```

**피크 시각 TOP 3**:
1. **18:00 ET** — FMP 500 calls + 동시 4태스크 (★ FMP 300/min 초과 거의 확정)
2. **17:15 / 10:15 / 13:15 / 15:15 / 06:15 ET** — FMP 500 calls × 5회 (★ orchestrator 내부 throttle 의존)
3. **18:30 ET** — Gemini analyze-deep 50 calls 폭주 + 5분 뒤 summary

---

## 6. 스케줄 겹침 / 의존성 분석

### 6.1 묵시적 직렬 의존 (스케줄러는 모름)

| 선행 | 후속 | 간격 | 위험 |
|------|------|------|------|
| `sync-sp500-eod-prices` (18:00) | `run-eod-pipeline` (18:30) | 30분 | EOD가 30분 넘으면 pipeline이 stale price 사용 |
| `sync-sp500-eod-prices` (18:00) | `update-sp500-change-percent` (18:30) | 30분 | 동일 |
| `thesis-update-readings` (18:00) | `thesis-calculate-scores` (18:15) | 15분 | reading이 15분 넘으면 score 결손 |
| `thesis-calculate-scores` (18:15) | `thesis-create-snapshots` (18:30) | 15분 | 동일 |
| `thesis-create-snapshots` (18:30) | `thesis-generate-summaries` (18:35) | 5분 | ★ 5분은 너무 타이트. snapshot 지연 시 summary가 stale 데이터 사용 |
| `train-importance-model` (Sun 03:00) | `generate-shadow-report` (Sun 03:30) | 30분 | train이 30분 넘으면 shadow는 옛 모델 평가 |
| `generate-shadow-report` (Sun 03:30) | `check-auto-deploy` (Sun 04:00) | 30분 | shadow 결과 필요 |
| `check-auto-deploy` (Sun 04:00) | `generate-weekly-ml-report` (Sun 04:15) | 15분 | deploy 상태 필요 |
| `chainsight-co-mentions` (10:00) | `chainsight-relation-confidence` (11:00) | 60분 | 여유 있음 |
| `chainsight-co-mentions` (10:00) | `chainsight-sync-profiles-neo4j` (12:00) | 120분 | 여유 |
| `chainsight-sync-profiles` (12:00) | `chainsight-sync-relations` (12:30) | 30분 | 적절 |
| `aggregate-daily-sentiment` (09:00) | (없음) | - | 단독 |

**구조적 문제**: Celery beat는 **단순 cron 트리거**라 선행 작업 완료 여부를 모른다. Chain/Group/Chord를 안 쓰고 시각 간격으로만 의존을 표현하면 backlog 누적 시 stale 데이터 전파.

### 6.2 동일 데이터 경합

| 자원 | 경합 태스크 | 시점 |
|------|-----------|------|
| `DailyPrice` 테이블 | `sync-sp500-eod-prices`(18:00) write + `run-eod-pipeline`(18:30) read | 30분 간격이라 OK |
| Neo4j writes | `sec-sync-dirty-neo4j`(*/5) + `sync-news-to-neo4j`(xx:45) + chainsight sync | solo queue로 직렬화되어 충돌은 없으나 backlog |
| Gemini quota | `analyze-deep`(18:30) + `thesis-summary`(18:35) | 5분 간격, 한도 공유 |
| FMP quota | EOD(18:00) + sp500-news(17:15) + general(17:45) | 분단위 폭주 |
| `NewsArticle` 테이블 | 다수의 news 수집 태스크가 동시간대 (06:00–07:30 6개+) | UPSERT 충돌 가능, deadlock 위험 |

### 6.3 expires 충돌

| 태스크 | expires | 분석 |
|-------|---------|------|
| `sec-sync-dirty-neo4j` | 240s | 다음 fire(*/5=300s)보다 짧아 정상이지만 solo pool backlog 시 만료 다발 |
| `check-pipeline-alerts` | 1500s | 다음 fire(*/30=1800s)보다 짧음. OK |
| `check-screener-alerts` | 600s | */15min = 900s. OK |
| 18:00–18:45 골든윈도우 태스크들 | 3600s | 1시간 안에 처리되어야 함. solo pool에서 동시 11개+가 5분 평균이라 55분 = 만료 직전 |

---

## 7. 우선 조치 권고 (코드 수정 금지 — 기록만)

### P0 (즉시 조치 권고)

1. **18:30 + 18:35 Gemini 충돌**: `thesis-generate-summaries`를 18:45 또는 19:00으로 분산. (audit 주석 line 285에서 동일 패턴을 16:30→16:45로 분산한 선례 있음 — 일관성 회복.)
2. **18:00 FMP 500 calls + 동시 태스크**: `sync-sp500-eod-prices`를 17:30 또는 19:00으로 분산. EOD pipeline 18:30은 그대로 두고.
3. **`analyze-news-deep` 내부 throttle 확인**: 50 calls/run이 1분 안에 호출되면 Gemini 15 RPM 초과 확정. 12초 sleep 적용 여부 코드 검증 필요. (audit 주석 line 285의 "15 RPM 2배 초과 위험" 인지는 있었음.)
4. **`enrich-relationship-keywords` limit=100**: 12초 sleep × 100 = 20분. 다른 neo4j queue 작업 모두 240s 만료 직격. limit을 30~50으로 축소하거나 chunk + 분산.

### P1 (이번 주 내)

5. **dict ↔ DB 드리프트 점검**: `python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(sorted(set(PeriodicTask.objects.values_list('name', flat=True))))"` 결과를 본 dict 키와 diff. 2026-04-24 복구 사례 재발 방지.
6. **Sunday 03:00–05:00 ML 도미노**: train이 30분 넘을 가능성 — 실측 후 간격 재조정.
7. **`chainsight-neo4j-dirty-sync` UTC vs ET 표기 불일치**: 주석 "UTC 04:30"와 crontab 실제 동작 시각 검증.
8. **sec-sync-dirty-neo4j**/5min expires=240s 만료율 모니터링: Sentry/log로 expired 카운트 추적.

### P2 (관찰)

9. **`refresh-market-pulse-cache` */1min × 480회/일**: 부하 작아도 빈도 과다. */2min 검토.
10. **macOS solo pool 가정**: 프로덕션이 Linux prefork면 default queue 동시성 ≫ 1이라 18:00 골든윈도우 완화. 운영 환경 명확화 필요.

---

## 8. 부록 — 전체 태스크 인벤토리 (스케줄 기준 정렬)

총 **86개** task entry. 빈도 분류:

| 빈도 분류 | 개수 |
|----------|------|
| 분 단위 (*/1, */5, */10, */15, */30) | 8 |
| 시간대 매 시각 (hour='x,y,z'+minute=N) | 4 |
| 일 1회 | 38 |
| 일 2~4회 | 12 |
| 일 5~6회 (xx:15, xx:30, xx:45 of 8,10,12,14,16,18) | 3 |
| 주간 (특정 요일) | 13 |
| 월간 (day_of_month) | 7 |
| 6시간 간격 | 1 |
| **계** | **86** |

### Queue 분포
- **default queue**: 76개
- **neo4j queue (solo)**: 10개 (task_routes 9개 + 명시 options 일부)

### API 의존 분포
- **FMP**: 12개 태스크 (realtime, daily, financials, indices, calendar, movers, sp500-news×5, press, general×3, eod, change-pct via DB)
- **Gemini**: 6개 (keyword-gen, extract-news-kw, analyze-deep, enrich-rel, thesis-summary, korean-overviews)
- **Neo4j**: 10개 (위 큐 동일)
- **FRED**: 2개 (econ-indic, calendar 일부)
- **SEC EDGAR**: 3개 (sec-sync, sec-seed, sec-check + supply-chain monthly)
- **DB only / 내부 계산**: 나머지 ~53개

---

## 9. 검증되지 않은 가정 (후속 코드 그렙 필요)

1. ✅ `sync-sp500-eod-prices` 내부 throttle 사용 여부
2. ✅ `collect_sp500_news_fmp_orchestrator` chunk + sleep 적용 여부
3. ✅ `analyze_news_deep` 내부 Gemini 호출 간격
4. ✅ `enrich_relationship_keywords` 내부 throttle
5. ✅ `chainsight-neo4j-dirty-sync` 실제 fire 시각 (UTC vs ET)
6. ✅ DB `PeriodicTask` 테이블의 실제 등록 상태와 dict 차이
7. ✅ Alpha Vantage 직접 호출 경로 존재 여부 (beat 외부)
8. ✅ macOS vs Linux 운영 환경 — solo pool 강제 여부

---

**보고서 끝**.
