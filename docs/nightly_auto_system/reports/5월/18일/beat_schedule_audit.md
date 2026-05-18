# Beat Schedule 감사 보고서

- **감사일**: 2026-05-18
- **대상 파일**: `config/celery.py` (820 lines, 90 schedule 엔트리)
- **범위**: `app.conf.beat_schedule` 선언적 정의(declared reference)
- **읽기 전용 감사** — 코드 수정 없음

---

## 0. 사전 경고: Schedule Drift Risk (P0)

`config/celery.py:117-134` 주석이 명시하듯, **이 dict는 런타임에서 무시된다**. 진실의 소스는 `django_celery_beat.PeriodicTask` DB 테이블이다(`CELERY_BEAT_SCHEDULER = 'DatabaseScheduler'`).

- 본 감사는 **선언된 의도(intended baseline)** 기준 분석
- 실제 동작 검증은 별도로 다음 명령 필요:
  ```
  python manage.py shell -c "from django_celery_beat.models import PeriodicTask; \
    print(set(PeriodicTask.objects.values_list('name', flat=True)))"
  ```
- 2026-04-24 복구 이력 있음(chainsight-heat-score-daily, sec-seed-relations-to-chainsight)
- 본 보고서 후속으로 dict↔DB diff 명령을 정기 실행할 것을 권고

**Timezone 모호성**: 주석에는 "EST"/"UTC" 혼용이지만 crontab은 `CELERY_TIMEZONE` 단일 값을 따른다. 본 보고서는 **schedule 문자열 그대로의 hour 값**(가상의 단일 TZ)으로 분석한다. 실 TZ 불일치 시 모든 결론은 시간 평행이동만 필요하다.

---

## 1. 전체 태스크 인벤토리 (90 entries)

### 1.1 Rate-limit critical group

| 외부 API | 한도 | 의존 태스크 | 동시 집중 위험 |
|---|---|---|---|
| FMP Starter | 300/min, 10,000/day | update-realtime-prices, update-market-indices, sync-sp500-financials, collect-sp500-news-fmp ×5, collect-press-releases-fmp, collect-general-news-fmp ×3, sync-sp500-eod-prices, run-eod-pipeline | **18:00, 06:00~07:00** |
| Gemini Free | 15 RPM / 1500 RPD | keyword-generation-pipeline, analyze-news-deep-batch ×6, extract-daily-news-keywords, extract-news-relations, chainsight-co-mentions, enrich-relationship-keywords, thesis-generate-summaries, refresh-korean-overviews-monthly | **08:30, 10:30, 12:30, 14:30, 16:30~16:45, 18:30~18:35** |
| Alpha Vantage | 5/min | (beat_schedule에 직접 의존 태스크 **없음**) | 없음 |
| FRED | 별도 한도 관대 | update-economic-indicators (×4/일) | 낮음 |

### 1.2 Queue 분포

| Queue | 태스크 수 | 동시성 |
|---|---|---|
| default | 79 | prefork(Linux) / solo(macOS) |
| neo4j | 11 | **solo (동시 1개 강제)** |

neo4j 큐 태스크 목록:
- `sec-sync-dirty-neo4j` (매 5분, expires=240s — **밀림 시 즉시 만료**)
- `neo4j-health-check` (6시간마다)
- `chainsight-sync-profiles-neo4j` (12:00)
- `chainsight-sync-relations-neo4j` (12:30)
- `sync-news-to-neo4j` (×6/일)
- `cleanup-expired-news-relationships` (04:00)
- `enrich-relationship-keywords` (05:30) ← Gemini와 neo4j 동시
- `chainsight-neo4j-dirty-sync` (Sun 04:30)

---

## 2. 시간대별 API 호출 히트맵 (평일 기준)

가로축: 분 (0-59), 세로축: 시간 (00-23). 각 셀은 해당 시각에 트리거되는 **태스크 수**.

```
Hour │ :00 :05 :10 :15 :20 :25 :30 :35 :40 :45 :50 :55 │ TOT │ Notes
─────┼───────────────────────────────────────────────────┼─────┼─────────────────────
 00  │  3   1   1   1   1   1   2   1   1   1   1   1   │ 15  │ neo4j-hc + sec5m + alert30m
 01  │  3   1   1   1   1   1   2   1   1   1   1   1   │ 15  │ +econ-calendar
 02  │  1   1   1   1   1   1   2   1   1   1   1   1   │ 13  │ sec5m baseline
 03  │  1   1   1   1   1   1   2   1   1   1   1   1   │ 13  │
 04  │  3   1   1   1   1   1   2   1   1   1   1   1   │ 15  │ +cleanup-news-rel(neo4j)
 05  │  1   1   1   1   1   1   3   1   1   1   1   1   │ 14  │ +enrich-keywords(Gemini+neo4j)
 06  │  4   1   1   2   1   1   2   1   1   2   1   1   │ 18  │ FMP-news+daily-news+cat-hi+gen-news
 07  │  4   1   1   1   1   1   3   1   1   1   1   1   │ 17  │ digest+heat+movers+cat-low+press
 08  │  3   1   1   3   1   1   3   1   1   1   1   1   │ 18  │ keyword-gen+mkt-news+v3-pipeline
 09  │  4   2   2   2   2   2   3   2   2   2   2   2   │ 27  │ +realtime/portfolio/breadth 시작
 10  │  3   2   2   3   2   2   3   2   2   2   2   2   │ 27  │ co-mentions+sp500-fmp+v3
 11  │  2   2   2   2   2   2   3   2   2   2   2   2   │ 25  │
 12  │  6   2   2   3   2   2   4   2   2   3   2   2   │ 32  │ **PEAK** macro+chain-sync+sec-seed
 13  │  3   2   2   3   2   2   3   2   2   2   2   2   │ 27  │ cat-hi-mid+seed+sp500-fmp
 14  │  3   2   2   3   2   2   4   2   2   2   2   2   │ 28  │ daily-pm+v3+cat-medium
 15  │  3   2   2   3   2   2   3   2   2   2   2   2   │ 27  │ mkt-news+sp500-fmp
 16  │  2   2   2   3   2   2   4   2   2   3   2   2   │ 28  │ v3+breadth+heatmap+keywords
 17  │  4   1   1   2   1   1   2   1   1   2   1   1   │ 18  │ daily-close+cat-hi-pm+sp500-fmp
 18  │  6   1   1   3   1   1   6   3   1   3   1   1   │ 28  │ **PEAK** EOD+thesis chain
 19  │  3   1   1   1   1   1   2   1   1   1   1   1   │ 15  │ ml-labels+backfill-acc
 20  │  2   1   1   1   1   1   2   1   1   1   1   1   │ 14  │ sp500-financials
 21  │  1   1   1   1   1   1   2   1   1   1   1   1   │ 13  │
 22  │  2   1   1   1   1   1   2   1   1   1   1   1   │ 14  │ econ-indicators
 23  │  1   1   1   1   1   1   2   1   1   1   1   1   │ 13  │
```

> `:00`이 모든 시간에 ≥1인 이유: `sec-sync-dirty-neo4j` (매 5분) 및 `check-pipeline-alerts` (매 30분)이 baseline 트래픽을 형성.
> 시장시간(9-16)은 realtime/portfolio/market-indices/market-pulse/screener-alerts 5개 cron이 분 단위로 깔린다(market-pulse는 매 분).

### 2.1 Peak 분석

**🔴 12:00 (32 tasks/h, 평일)**
| Min | 태스크 | API |
|---|---|---|
| :00 | update-economic-indicators | FRED |
| :00 | collect-market-news-noon | News provider |
| :00 | chainsight-sync-profiles-neo4j | Neo4j |
| :00 | sec-seed-relations-to-chainsight | DB only |
| :00 | sec-sync-dirty-neo4j | Neo4j |
| :00 | (realtime/portfolio/market-indices/screener-alerts) | FMP |
| :15 | classify-news-batch (8,10,12...) | DB/LLM |
| :30 | analyze-news-deep-batch | **Gemini ×50** |
| :30 | collect-general-news-fmp-noon | FMP |
| :30 | chainsight-sync-relations-neo4j | Neo4j |
| :45 | sync-news-to-neo4j | Neo4j |

**🔴 18:00 (28 tasks/h, 평일) — EOD avalanche**
| Min | 태스크 | API |
|---|---|---|
| :00 | thesis-update-readings | FMP/DB |
| :00 | sync-sp500-eod-prices | **FMP × 500 symbols** |
| :00 | update-economic-indicators | FRED |
| :00 | collect-market-news-evening | News |
| :00 | neo4j-health-check | Neo4j |
| :00 | sec-sync-dirty-neo4j | Neo4j |
| :15 | thesis-calculate-scores | DB only |
| :15 | classify-news-batch | LLM |
| :30 | run-eod-pipeline | DB/계산 |
| :30 | thesis-create-snapshots | DB/알림 |
| :30 | update-sp500-change-percent | DB only |
| :30 | analyze-news-deep-batch | **Gemini ×50** |
| :35 | thesis-generate-summaries | **Gemini × N** |
| :45 | sync-news-to-neo4j | Neo4j |

→ `:00`에 sp500 500종목 FMP 호출 + realtime/market-indices(시장시간 끝나 미실행 — 16시 종료) + thesis-update-readings(지표별 FMP).
→ `:30`에 EOD pipeline + Gemini 동시 + Neo4j sync 직전.
→ `:35` thesis-generate-summaries는 `:30`의 Gemini 호출과 5분 인접 — **Gemini RPM 분당 한도 분산 효과 없음**.

**🟡 06:00 (18 tasks/h, FMP 부담)**
- 06:00 collect-daily-news-morning(News API + FMP)
- 06:00 sync-etf-holdings(Mon만)
- 06:00 neo4j-health-check
- 06:15 collect-sp500-news-fmp-0615 → **S&P500 500종목 orchestrator**
- 06:30 collect-category-news-high-morning
- 06:45 collect-general-news-fmp-morning

15분 간격으로 FMP 대량 호출 4건 — 06:15 orchestrator가 한도(300/min) 초과 위험 가장 큼.

---

## 3. FMP Rate Limit 초과 구간 (Starter 300/min, 10,000/day)

### 3.1 분당 burst 위험 (P0)

| 시각 | 동시 태스크 | 추정 호출수/분 | 위험 |
|---|---|---|---|
| **18:00:00** | sync-sp500-eod-prices(500) + thesis-update-readings(지표 N×symbol) | **>500 calls/min** | 🔴 한도 초과 거의 확실 |
| **06:15:00** | collect-sp500-news-fmp-0615 orchestrator | **~500 calls** (orchestrator 내부 분산이라면 OK) | 🟡 orchestrator 내부 throttle 검증 필요 |
| **10:15, 13:15, 15:15, 17:15** | sp500-news-fmp orchestrator (×4 추가) | 동일 | 🟡 |
| **09:00:00** | update-realtime-prices(500?) + update-market-indices + portfolio-values + screener-alerts | FMP batch 호출이면 ~2~4건/분 | 🟢 (배치 호출 가정) |
| **18:00:30** | analyze-news-deep-batch(Gemini) + collect-sp500-news-fmp(없음, 17:15 이미 끝) | — | 🟢 |

**검증 필요**:
- `stocks.tasks.sync_sp500_eod_prices` 내부 batching/throttle 로직? → 단일 minute에 500건 직렬 호출이면 한도 초과
- `news.tasks.collect_sp500_news_fmp_orchestrator` 분산 sleep 로직? → 권장: 분당 250건 이하

### 3.2 일일 한도 (10,000/day)

추정 합계 (평일):
- update-realtime-prices: 96 × N (batch당 호출수에 의존)
- sync-sp500-eod-prices: 1 × ~500
- sync-sp500-financials: 1 × ~101 종목 × 3-5 endpoint = ~300-500
- collect-sp500-news-fmp ×5: 5 × ~500 = **~2500**
- collect-general-news-fmp ×3: ~30
- collect-press-releases-fmp: 50
- collect-daily-news (×2): ~500 종목 × 2 = ~1000
- thesis-update-readings: 지표별 호출수에 따라 100~1000+
- run-eod-pipeline: 내부 계산 위주, FMP 호출 적음 추정

**대략 5,000~8,000 calls/day** — 한도 내이지만 여유 적음. realtime-prices가 종목별 호출이면 한계 초과 가능. **batching 여부 확인 필요**.

---

## 4. Gemini Rate Limit (Free 15 RPM, 1500 RPD)

### 4.1 분당 충돌 (RPM 위험)

`analyze-news-deep-batch`는 max 50건. 50건 / 15 RPM = **~3.3분** 소요 (직렬 호출 시). 이론적으로 RPM은 통과.

**P0 위험 구간** — `:30` 분 마크에서 Gemini 동시 호출:

| 시각 | 동시 Gemini 태스크 | 추정 호출수 |
|---|---|---|
| 08:30 | analyze-news-deep-batch (50) | 50 |
| 10:30 | analyze-news-deep-batch (50) | 50 |
| 12:30 | analyze-news-deep-batch (50) | 50 |
| 14:30 | analyze-news-deep-batch (50) | 50 |
| 16:30 | analyze-news-deep-batch (50) | 50 |
| 16:45 | extract-daily-news-keywords | N |
| 18:30 | analyze-news-deep-batch (50) | 50 |
| **18:35** | **thesis-generate-summaries** | N (가설 수) |
| 09:00 | extract-news-relations(24h) | 다수 |
| 10:00 | chainsight-co-mentions(7d) | 다수 |
| 05:30 | enrich-relationship-keywords (limit=100) | 100 |
| 08:00 | keyword-generation-pipeline | N |

**🔴 16:30 ↔ 16:45 (15분 간격) — 주석에서 이미 인지하고 분리한 사례 (P0 #8, 2026-04-26)**. 현 schedule은 OK.

**🟡 18:30 analyze-news-deep + 18:35 thesis-generate-summaries**: 5분 간격은 RPM(15/분)에 영향 없으나, **analyze-deep이 5분 안에 못 끝나면(50건 ÷ 15RPM = 3.3분 — 마진 1.7분뿐) 두 태스크가 동시 호출 → RPM 30 ≫ 15 한도**. → 권장: 18:35 → 18:50 이상으로 이동, 또는 analyze-deep의 max_articles 축소.

**🟡 09:00 extract-news-relations + 09:00 aggregate-daily-sentiment**: 같은 분에 시작. aggregate-sentiment가 LLM을 쓰는지 검증 필요.

### 4.2 일일 한도 (1500 RPD)

추정:
- analyze-news-deep-batch: 6 × 50 = **300**
- extract-daily-news-keywords: ?
- extract-news-relations: 24h 누적, 수십~수백
- chainsight-co-mentions: 7d 누적, 수십~수백
- enrich-relationship-keywords: 최대 100
- keyword-generation-pipeline: 수십
- thesis-generate-summaries: 활성 가설 수
- refresh-korean-overviews-monthly: 1일/월, 500종목 × 1회 = 500 (월 1일 한정 burst)

**평일 평균 500~800 RPD**. **매월 1일 03:00 refresh-korean-overviews-monthly가 500건 burst** — 단일 태스크가 RPD 1/3 소비. RPM 15로 직렬 처리 시 ~33분 소요(이론치). 동시간대 다른 LLM 태스크 없으므로 OK이지만, **태스크 expires=86400s (24시간)** — 첫 시도가 한도 도달해도 expires가 길어 retry 누적 가능.

---

## 5. Alpha Vantage (5/min)

`beat_schedule` 직접 의존 태스크 **0건**. AV 사용은 on-demand만으로 추정. ✅ 안전.

---

## 6. Queue 몰림 분석 — neo4j queue (solo, 1 concurrent)

### 6.1 시간대별 neo4j 큐 점유

```
시각          태스크                                     예상 소요
─────────────────────────────────────────────────────────────────
*:00,05,...  sec-sync-dirty-neo4j (5분마다)             초~분
00:00        neo4j-health-check                          초
04:00        cleanup-expired-news-relationships         분
04:30 Sun    chainsight-neo4j-dirty-sync                분~수십분
05:30        enrich-relationship-keywords (Gemini+Neo4j) **수~수십분** (Gemini RPM 제약)
06:00        neo4j-health-check                          초
08:45        sync-news-to-neo4j (×6 daily at :45)       분
10:45        sync-news-to-neo4j
12:00        chainsight-sync-profiles-neo4j             분~수십분
12:30        chainsight-sync-relations-neo4j            분~수십분
12:45        sync-news-to-neo4j
14:45        sync-news-to-neo4j
16:45        sync-news-to-neo4j
18:00        neo4j-health-check
18:45        sync-news-to-neo4j
```

### 6.2 P0 — sec-sync-dirty-neo4j (5분 cadence, expires=240s)

- **5분 cadence + 4분 만료** = 마진 1분
- 다른 neo4j 태스크가 1분 이상 점유하면 sec-sync는 **즉시 만료되어 누락**
- 위험 시각:
  - 04:00 cleanup-expired-news-relationships와 충돌
  - 05:30 enrich-relationship-keywords (Gemini RPM으로 수십분 점유 가능) → **05:30~06:00 사이 sec-sync 6회 중 일부 만료 거의 확실**
  - 12:00, 12:30 chainsight sync 2건 연속 → 30분간 sec-sync 6회 모두 만료 가능
  - 모든 `:45` sync-news-to-neo4j (6번/일)
- **권장**: sec-sync-dirty-neo4j의 expires 값 상향 또는 cadence 완화(10분), 또는 chainsight sync를 별도 큐로 분리

### 6.3 enrich-relationship-keywords 위험 (05:30)

- neo4j queue + Gemini API 호출 동시 사용
- Gemini RPM 15로 limit=100 처리 시 ~7분 점유
- 이 동안 sec-sync-dirty-neo4j 1~2회 만료
- **권장**: limit을 분당 처리 가능 수(50)로 축소 또는 별도 시간대(예: 02:00)

---

## 7. 스케줄 겹침 / 의존성 검증

### 7.1 의도된 의존성 체인 (정상)

| 체인 | 시각 | 정상 여부 |
|---|---|---|
| sync-sp500-eod-prices(18:00) → update-sp500-change-percent(18:30) → run-eod-pipeline(18:30) → backfill-signal-accuracy(19:00) | 30분 간격 | ✅ |
| thesis-update-readings(18:00) → thesis-calculate-scores(18:15) → thesis-create-snapshots(18:30) → thesis-generate-summaries(18:35) | 15분 간격 | ⚠️ Gemini 충돌(§4.1) |
| classify-news-batch(:15) → analyze-news-deep-batch(:30) → sync-news-to-neo4j(:45) | 15분 간격 | ✅ |
| collect-daily-news(06:00, 14:30) → aggregate-daily-sentiment(09:00) | 비대칭, afternoon news는 같은 날 집계 미반영 | ⚠️ |
| train-importance-model(Sun 03:00) → generate-shadow-report(03:30) → check-auto-deploy(04:00) → generate-weekly-ml-report(04:15) → monitor-ml-performance(04:20) → train-lightgbm-model(04:30) | 30/15/10분 간격 | ✅ (단 train-importance-model 2시간 소요 시 03:30 shadow-report와 충돌 가능 — expires=7200) |
| chainsight-all-profiles(Sat 02:00) → chainsight-price-co-movement(Sat 03:00) → chainsight-stale-decay(Sat 04:00) → chainsight-aggregate-profiles(Sat 04:30) → validation-weekly-batch(Sat 05:00) | 30분~1시간 간격 | ✅ |

### 7.2 동시 시작 (같은 분에 ≥2 태스크) — 데이터 경합 위험

| 시각 | 태스크들 | 경합 분석 |
|---|---|---|
| **18:00:00 평일** | thesis-update-readings, sync-sp500-eod-prices, update-economic-indicators, collect-market-news-evening, neo4j-health-check, sec-sync-dirty-neo4j | **FMP burst 위험**, FMP 한도 진입 시 thesis-readings 일부 데이터 누락 가능 |
| 18:30:00 평일 | thesis-create-snapshots, run-eod-pipeline, update-sp500-change-percent, analyze-news-deep-batch, sec-sync-dirty-neo4j | DB-write 위주, 같은 row 쓰면 충돌. **EOD pipeline과 thesis snapshot이 동일 DailyPrice 의존 시 race** |
| 12:00:00 (everyday) | update-economic-indicators, collect-market-news-noon, chainsight-sync-profiles-neo4j, sec-seed-relations-to-chainsight, sec-sync-dirty-neo4j | DB+Neo4j 동시 쓰기 (chainsight + sec) — **chain_relation table 경합 가능성** |
| 04:00:00 | cleanup-expired-news-relationships(neo4j), check-auto-deploy(Sun), scan-regulatory-relationships(Mon), sync-institutional-holdings(16일), sec-sync-dirty-neo4j | 이론적 충돌 가능, 실제 발생일은 16일+월요일=드물게 |
| 09:00:00 평일 | aggregate-daily-sentiment, extract-news-relations | NewsArticle read 경합 가능, 동일 source data |
| 07:00:00 | celery-error-digest, chainsight-heat-score-daily | 독립 |

### 7.3 정의되지 않은 선행 의존 (race condition 위험)

- **aggregate-daily-sentiment(09:00)** 가 06:00 morning news만 집계? 14:30 afternoon news는 다음 날까지 미반영? → 비즈니스 의도 검증 필요
- **chainsight-co-mentions(10:00)** 는 분류된 뉴스 필요. classify-news-batch는 08:15부터 시작 → 10:00에 충분히 처리됨, OK
- **chainsight-sync-profiles-neo4j(12:00)** 의 선행: chainsight-all-profiles는 토요일에만 → 평일 12:00 sync는 **새 프로파일 없이 기존 데이터만 sync**. 의도된 거라면 OK, 아니면 P1
- **collect-ml-labels(19:00)** lookback_days=2 → 18:00 EOD price sync 완료 가정. ✅

---

## 8. 종합 P0/P1/P2

### P0 (즉시 조치 권고)

| # | 항목 | 근거 |
|---|---|---|
| 1 | **Schedule Drift 검증 자동화** | dict는 무시됨, DB가 진실. diff 명령을 cron화 또는 PR 체크에 포함 |
| 2 | **18:00 FMP burst** | sync-sp500-eod-prices(500) + thesis-update-readings 동시 시작 → FMP 300/min 거의 확실 초과. batching/throttle 검증 또는 18:00 ↔ 18:05 분리 |
| 3 | **sec-sync-dirty-neo4j expires=240s + 5분 cadence** | 마진 1분, 다른 neo4j 태스크 점유 시 즉시 만료 → 누락. expires 상향 또는 cadence 완화 |
| 4 | **05:30 enrich-relationship-keywords** | neo4j queue + Gemini 동시 사용, ~7분 점유. sec-sync 1~2회 만료 위험 |
| 5 | **18:30 analyze-news-deep + 18:35 thesis-generate-summaries** | 5분 간격이 analyze-deep의 이론 처리시간(3.3분)에 마진 1.7분뿐. 지연 시 Gemini RPM 동시 30 ≫ 15 |

### P1 (단기 개선)

| # | 항목 |
|---|---|
| 6 | 12:00 chainsight + sec 동시 시작 → 같은 분 분산(예: chainsight 12:00, sec-seed 12:05) |
| 7 | aggregate-daily-sentiment 09:00 — afternoon news 반영 누락 의도 검증 |
| 8 | refresh-korean-overviews-monthly: 매월 1일 500건 Gemini burst, RPD 1500의 1/3 — 분산 |
| 9 | sp500-news-fmp orchestrator 5회 × 500종목 = 2,500 calls/day FMP, 전체 일일 한도의 25% — orchestrator 내부 throttle 문서화 필요 |
| 10 | chainsight-sync-profiles-neo4j(평일 12:00) — 평일에 새 프로파일이 없는데 매일 sync하는 의도? |

### P2 (관찰)

| # | 항목 |
|---|---|
| 11 | TZ 명세 부재 — 주석의 "EST"/"UTC"가 settings의 `CELERY_TIMEZONE`과 일치하는지 명시 |
| 12 | classify/analyze/sync 트리오(:15/:30/:45 ×6/일)가 LLM 처리 지연 시 다음 :15 cycle과 겹칠 위험 — backpressure 모니터링 |
| 13 | check-pipeline-alerts 매 30분 + expires=1500s(25분) — 8 워커 부족 시 알림 누락 가능 |
| 14 | sec-sync-dirty-neo4j 5분 cadence × 24h = 288회/일 — 빈도 정당성 검증(Tier B 신규 evidence 빈도 대비) |

---

## 9. 추가 검증 권고 명령 (읽기 전용)

```python
# 1. dict ↔ DB drift 검증
from django_celery_beat.models import PeriodicTask
from config.celery import app
dict_keys = set(app.conf.beat_schedule.keys())
db_keys = set(PeriodicTask.objects.values_list('name', flat=True))
print("dict only:", dict_keys - db_keys)
print("DB only:", db_keys - dict_keys)
print("disabled in DB:", set(PeriodicTask.objects.filter(enabled=False).values_list('name', flat=True)))

# 2. FMP 일일 호출 누적 측정 (지난 7일)
#    stocks.log 또는 API_request 로그 grep으로 분당 분포 추출

# 3. neo4j 큐 적재 측정
celery -A config inspect active_queues
celery -A config inspect reserved
```

---

## 10. 요약 (한 줄)

**18:00 EOD avalanche (FMP burst) + 05:30/12:00/12:30 neo4j queue 점유로 인한 sec-sync-dirty-neo4j 만료 누락 + 18:30→18:35 Gemini RPM 마진 부족 — 이 3개가 P0 핵심.** dict↔DB drift는 운영상 모든 결론의 전제조건이므로 자동 검증을 선행할 것.
