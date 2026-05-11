# Beat Schedule Audit — 2026-04-25

**대상 파일**: `config/celery.py` (총 811 LOC, beat_schedule dict L135–L805)
**스케줄러**: `django_celery_beat.schedulers:DatabaseScheduler` (DB `PeriodicTask` 테이블이 진실의 소스)
**감사 범위**: 평일(Mon–Fri) 정상 가동 가정 + 주말/월간 태스크 별도 표기
**감사 모드**: 읽기 전용. 코드 수정 없음.

> ⚠️ **Drift 주의**: `app.conf.beat_schedule` dict는 런타임에 무시된다(L118–L134 주석). 본 감사는 dict가 DB와 일치한다는 가정 하에 분석. DB와의 diff는 별도 점검 필요.

---

## 0. Executive Summary

| 항목 | 결과 | 근거 |
|------|------|------|
| 총 정의된 태스크 | **약 70개** | beat_schedule dict 키 카운트 |
| Alpha Vantage 의존 스케줄 | **0건** | commit `df85496` AV provider 전면 제거 — `news/migrations/0005`, `news/models.py` 외 잔존 코드 없음 |
| FMP 한도(300/min) **즉시 초과** 위험 | **0건** | 모든 FMP-heavy 태스크가 자체 sleep / `rate_limit` / countdown 분산을 적용 |
| FMP 한도 **잠재 초과**(잠시 65–70% 점유) | **1건** | 18:00 `sync-sp500-eod-prices` 약 200 calls/min × 2.5 min |
| Gemini Free(15 RPM) **초과** 위험 | **2건 잠재** | 16:30, 18:30 `analyze-news-deep` + 동시 LLM 태스크 중첩 |
| Gemini Free(1500 RPD) **초과** 위험 | **0건** | 일일 추정 < 700 calls (분석 결과 §3.2) |
| FRED 한도 초과 | **0건** | 4 fires/day, 호출 수 매우 적음 |
| neo4j queue (solo pool) 백로그 위험 | **2건** | 12:00, 12:45 정각 동시 fire — solo 직렬 처리로 지연 가능 |
| 의존성 깨짐(선행 미완료 시 후속 실행) | **2건 잠재** | thesis EOD 체인(18:00→18:15→18:30 간격 15분), chainsight-co-mentions ↔ classify-news-batch 어긋남 |
| 시간대 피크 | **12:00–12:45 (EST), 18:00–18:45 (EST)** | §2 히트맵 |

핵심 위험은 **(A) 18:00 EST FMP 동시 발사 4건**, **(B) 16:30 EST Gemini 동시 발사 2건**, **(C) neo4j solo pool 12:00 정각 충돌**.

---

## 1. Beat Schedule 인벤토리 (그룹별)

### 1.1 Stocks / Macro (시세 · 거시)
| Beat 키 | task | 스케줄 (EST) | 큐 | API |
|---|---|---|---|---|
| update-realtime-prices | stocks.tasks.update_realtime_with_provider | `*/5 9-16 1-5` | default | FMP |
| update-daily-prices | stocks.tasks.update_realtime_with_provider | `17:00 1-5` | default | FMP |
| aggregate-weekly-prices | stocks.tasks.aggregate_weekly_prices | `01:00 Sat` | default | DB only |
| sync-sp500-financials | stocks.tasks.sync_sp500_financials | `20:00 1-5` | default | FMP (101 × 3–4 endpoints, countdown=i*7) |
| calculate-portfolio-values | users.tasks.calculate_portfolio_values | `*/10 9-16 1-5` | default | DB only |
| update-economic-indicators | macro.tasks.update_economic_indicators | `0 6,12,18,22 1-5` | default | **FRED** |
| update-market-indices | macro.tasks.update_market_indices | `*/5 9-16 1-5` | default | FMP (1 batch / fire) |
| update-economic-calendar | macro.tasks.update_economic_calendar | `01:00 daily` | default | FRED |
| refresh-market-pulse-cache | macro.tasks.refresh_market_pulse_cache | `* 9-16 1-5` | default | DB/Redis only |
| cleanup-old-macro-data | macro.tasks.cleanup_old_data | `03:00 Sun` | default | DB only |

### 1.2 News 수집/분석 (Marketaux + Finnhub + FMP)
| Beat 키 | task | 스케줄 (EST) | 큐 | API |
|---|---|---|---|---|
| collect-daily-news-morning | news.tasks.collect_daily_news | `06:00 1-5` | default | Marketaux/Finnhub |
| collect-daily-news-afternoon | 〃 | `14:30 1-5` | default | 〃 |
| collect-market-news-{morning,noon,afternoon,evening} | news.tasks.collect_market_news | `08:00, 12:00, 15:00, 18:00 1-5` | default | 〃 |
| collect-category-news-high-{morning,midday,evening} | news.tasks.collect_category_news | `06:30, 13:00, 17:00 1-5` | default | 〃 |
| collect-category-news-medium-{morning,afternoon} | 〃 | `07:00, 14:00 1-5` | default | 〃 |
| collect-category-news-low | 〃 | `07:30 1-5` | default | 〃 |
| aggregate-daily-sentiment | news.tasks.aggregate_daily_sentiment | `09:00 1-5` | default | DB only |
| extract-daily-news-keywords | news.tasks.extract_daily_news_keywords | `16:30 daily` | default | **Gemini** |
| classify-news-batch | news.tasks.classify_news_batch | `15 8,10,12,14,16,18 1-5` | default | Rules + LLM(부분) |
| analyze-news-deep | news.tasks.analyze_news_deep | `30 8,10,12,14,16,18 1-5` | default | **Gemini** (4초 간격, 50 article max) |
| sync-news-to-neo4j | news.tasks.sync_news_to_neo4j | `45 8,10,12,14,16,18 1-5` | **neo4j** | Neo4j |
| cleanup-expired-news-relationships | 〃 | `04:00 daily` | **neo4j** | Neo4j |
| collect-ml-labels | news.tasks.collect_ml_labels | `19:00 1-5` | default | DB only |
| train-importance-model | news.tasks.train_importance_model | `03:00 Sun` | default | local ML |
| generate-shadow-report | news.tasks.generate_shadow_report | `03:30 Sun` | default | DB only |
| check-auto-deploy | news.tasks.check_auto_deploy | `04:00 Sun` | default | DB only |
| generate-weekly-ml-report | 〃 | `04:15 Sun` | default | DB only |
| monitor-ml-performance | 〃 | `04:20 Sun` | default | DB only |
| train-lightgbm-model | news.tasks.train_lightgbm_model | `04:30 Sun` | default | local ML |
| check-pipeline-alerts | news.tasks.check_pipeline_alerts | `*/30 daily` | default | DB only |
| archive-old-articles | news.tasks.archive_old_articles | `02:30 1st of month` | default | DB only |

### 1.3 FMP 대량 뉴스 (S&P 500 직격)
| Beat 키 | 스케줄 (EST) | API 콜 추정 |
|---|---|---|
| collect-sp500-news-fmp-{0615,1015,1315,1515,1715} | `06:15, 10:15, 13:15, 15:15, 17:15 1-5` | 503 calls/run × 5 = **2,515 calls/day**, `rate_limit='100/m'` 적용 → 5분 분산 |
| collect-press-releases-fmp | `07:45 1-5` | 50 calls/run |
| collect-general-news-fmp-{morning,noon,evening} | `06:45, 12:30, 17:45 1-5` | 1–3 calls/run |

### 1.4 Serverless / Chain Sight / SEC
| Beat 키 | 스케줄 (EST) | 큐 | API |
|---|---|---|---|
| sync-daily-market-movers | `07:30 1-5` | default | FMP (3 calls) |
| keyword-generation-pipeline | `08:00 daily` | default | **Gemini** |
| sync-etf-holdings | `06:00 Mon` | default | FMP/SPDR XLSX |
| sync-supply-chain-batch | `03:00 day_of_month=15` | default | SEC EDGAR |
| calculate-market-breadth | `16:30 1-5` | default | DB only |
| calculate-sector-heatmap | `16:35 1-5` | default | DB only |
| check-screener-alerts | `*/15 9-16 1-5` | default | DB only |
| sync-sp500-constituents | `02:00 day_of_month=1` | default | FMP |
| sync-sp500-eod-prices | `18:00 1-5` | default | FMP (503 × 0.3s sleep ≈ 200/min for 2.5 min) |
| update-sp500-change-percent | `18:30 1-5` | default | DB only |
| extract-news-relations | `09:00 daily` | default | Gemini (확률) |
| enrich-relationship-keywords | `05:30 daily` | **neo4j** | **Gemini** + Neo4j |
| sync-institutional-holdings | `04:00 day_of_month=16` | default | SEC 13F |
| scan-regulatory-relationships | `04:00 Mon` | default | FMP/SEC |
| build-patent-network | `04:30 day_of_month=1` | default | external |
| run-eod-pipeline | `18:30 1-5` | default | DB/compute |
| backfill-signal-accuracy | `19:00 1-5` | default | DB only |
| refresh-korean-overviews-monthly | `03:00 day_of_month=1` | default | **Gemini** (50 batch) |
| chainsight-all-profiles | `02:00 Sat` | default | DB |
| chainsight-co-mentions | `10:00 daily` | default | DB (NewsEntity) |
| chainsight-price-co-movement | `03:00 Sat` | default | DB |
| chainsight-relation-confidence | `11:00 daily` | default | DB |
| chainsight-stale-decay | `04:00 Sat` | default | DB |
| chainsight-aggregate-profiles | `04:30 Sat` | default | DB |
| chainsight-sync-profiles-neo4j | `12:00 daily` | **neo4j** | Neo4j |
| chainsight-sync-relations-neo4j | `12:30 daily` | **neo4j** | Neo4j |
| chainsight-heat-score-daily | `07:00 daily` | default | DB |
| chainsight-seed-selection | `13:00 daily` | default | DB |
| chainsight-neo4j-dirty-sync | `04:30 Sun` | **neo4j** | Neo4j |
| validation-weekly-batch | `05:00 Sat` | default | FMP heavy |
| sec-sync-dirty-neo4j | `*/5 daily` | **neo4j** | Neo4j |
| sec-seed-relations-to-chainsight | `12:00 daily` | default | DB |
| sec-check-new-filings | `06:00 day_of_month=1` | default | SEC EDGAR |

### 1.5 Thesis Control + 시스템
| Beat 키 | 스케줄 (EST) | API |
|---|---|---|
| thesis-update-readings | `18:00 1-5` | DB/cache |
| thesis-calculate-scores | `18:15 1-5` | DB |
| thesis-create-snapshots | `18:30 1-5` | DB + 알림 |
| neo4j-health-check | `0 */6 daily` | Neo4j |
| celery-error-digest | `07:00 daily` | 이메일 |
| cleanup-task-results | `05:00 Sun` | DB |

---

## 2. 시간대별 ASCII 히트맵 (Mon–Fri 평일 가정)

### 2.1 Beat fire 횟수/시간 (1 실행 = 1 fire, 분 단위 fire는 모두 카운트)

```
Hour │ Fires │ Heatmap (■ = ~10 fires)
─────┼───────┼───────────────────────────────────────────
 00  │   14  │ ■▢
 01  │   15  │ ■▢                                                [economic-calendar]
 02  │   14  │ ■▢
 03  │   14  │ ■▢
 04  │   15  │ ■▢                                                [cleanup-news-relationships]
 05  │   15  │ ■▢                                                [enrich-keywords ★Gemini]
 06  │   19  │ ■■                                                [news 수집 5건 → 6:00,6:15,6:30,6:45]
 07  │   19  │ ■■                                                [movers, low-cat-news, press-releases]
 08  │   19  │ ■■                                                [keyword-pipeline ★Gemini, classify, analyze ★]
 09  │  110  │ ■■■■■■■■■■■                            ◄ 시장 진입 ─ 분당 cache refresh + every 5min FMP
 10  │  112  │ ■■■■■■■■■■■                            ★Gemini analyze + co-mentions
 11  │  109  │ ■■■■■■■■■■■                            relation-confidence
 12  │  117  │ ■■■■■■■■■■■■                          ◄ ★ 정점 ─ FRED + Neo4j 2건 + market-news + classify+analyze
 13  │  111  │ ■■■■■■■■■■■                            chainsight-seed + sp500-news 1315
 14  │  112  │ ■■■■■■■■■■■                            classify + analyze ★Gemini
 15  │  110  │ ■■■■■■■■■■■                            sp500-news 1515
 16  │  114  │ ■■■■■■■■■■■                            ◄ ★ 시장 마감 ─ extract-keywords ★+ analyze ★ 동시
 17  │   18  │ ■■                                                update-daily, sp500-news 1715, general-fmp-evening
 18  │   25  │ ■■■                                              ◄ ★ EOD 정점 ─ FMP 503 + thesis 체인 + market-news
 19  │   16  │ ■▢                                                ml-labels, backfill-signal-accuracy
 20  │   15  │ ■▢                                                sync-sp500-financials (FMP 12분 분산)
 21  │   14  │ ■▢
 22  │   15  │ ■▢                                                update-economic-indicators
 23  │   14  │ ■▢
```

베이스 카운트(상수) — `sec-sync-dirty-neo4j` (12) + `check-pipeline-alerts` (2) = **14 fires/h** 모든 시간대.
시장 시간 오버레이 — `update-realtime-prices` (12) + `update-market-indices` (12) + `refresh-market-pulse-cache` (60) + `calculate-portfolio-values` (6) + `check-screener-alerts` (4) = **+94 fires/h**.

### 2.2 외부 API 호출 추정/시간 (Mon–Fri)

```
Hour │ FMP   │ Gemini │ FRED │ Neo4j │ 주요 이슈
─────┼───────┼────────┼──────┼───────┼──────────────────────────────────────
 00  │   0   │    0   │   0  │   12  │
 01  │   0   │    0   │   1  │   12  │ economic-calendar
 02  │   0   │    0   │   0  │   12  │
 03  │   0   │    0*  │   0  │   12  │ *1st: korean-overviews 50× / Sun: ML
 04  │   0   │    0   │   0  │   13  │ +cleanup-news-rels
 05  │   0   │   ~50  │   0  │   13  │ enrich-relationship (Gemini, 100 limit)
 06  │   0   │    0   │   1  │   12  │ economic-indicators 06:00
 07  │  53   │    0   │   0  │   12  │ market-movers + press-releases 50 + general-fmp-3
 08  │   0   │  ~30   │   0  │   12  │ keyword-pipeline + analyze-news-deep ★
 09  │ 132   │   ~5   │   0  │   12  │ market overlay + extract-news-relations
 10  │ 635   │  ~50   │   0  │   12  │ +sp500-news-1015 (503/5min) + analyze-deep ★ + co-mentions
 11  │ 132   │    0   │   0  │   12  │
 12  │ 134   │  ~50   │   1  │   14  │ ★ analyze-deep + 2 neo4j sync + general-fmp-noon
 13  │ 635   │    0   │   0  │   12  │ +sp500-news-1315
 14  │ 132   │  ~50   │   0  │   12  │ analyze-deep
 15  │ 635   │    0   │   0  │   12  │ +sp500-news-1515
 16  │ 132   │ ~100   │   0  │   12  │ ★ extract-daily-keywords + analyze-deep 동시
 17  │ 516   │    0   │   0  │   12  │ update-daily-10 + sp500-news-1715-503 + general-fmp-3
 18  │ 503   │  ~50   │   1  │   12  │ ★ sync-sp500-eod 503@200/min + thesis 체인 시작
 19  │   0   │    0   │   0  │   12  │
 20  │ 404   │    0   │   0  │   12  │ sync-sp500-financials (12분 분산, ~25/min)
 21  │   0   │    0   │   0  │   12  │
 22  │   0   │    0   │   1  │   12  │ economic-indicators 22:00
 23  │   0   │    0   │   0  │   12  │

★ = 이 시간 동안 RPM/RPS 한도 압박 발생
```

> 주: FMP 컬럼은 **시간 합계**가 아니라 해당 시간 내 발생 총 호출 수 추정. 하나의 fire가 분당 나뉘어 발생하는 경우(rate_limit) 시간 내 분배되어 안전.

---

## 3. Rate Limit 분석

### 3.1 FMP — Starter 300 calls/min

| 시점 | 호출원 | 분당 호출 추정 | 한도 대비 | 판정 |
|------|--------|---------------|-----------|------|
| 06:15–06:20 | sp500-news-0615 (`rate_limit='100/m'`) | ~100/min | 33% | ✅ |
| 09:00–16:00 매분 | update-realtime(10/5min) + market-indices(1/5min) | ~2.2/min 평균 | <1% | ✅ |
| 10:15–10:20 | sp500-news-1015 + market overlay | 100 + 2.2 ≈ 102/min | 34% | ✅ |
| 13:15–13:20 | 〃 1315 | ~102/min | 34% | ✅ |
| 15:15–15:20 | 〃 1515 | ~102/min | 34% | ✅ |
| 17:15–17:20 | 〃 1715 (시장 외) | 100/min | 33% | ✅ |
| **18:00–18:02:30** | **sync-sp500-eod (0.3s sleep, 503 symbols)** | **~200/min × 2.5 min** | **67%** | ⚠️ |
| 20:00–20:12 | sync-sp500-financials (subtask `rate_limit='6/m'` × 3–4 endpoints) | ~20–25/min | 8% | ✅ |
| 07:30 + 07:45 | market-movers(3) + press-releases(50, sequential within ~50s) | ~60/min 순간 | 20% | ✅ |

**위험 평가**:
- ✅ 단독으로 300/min을 즉시 초과하는 태스크는 **없음**.
- ⚠️ **18:00 sync-sp500-eod**가 단일 태스크로 **67% (200/min)** 점유. 같은 분에 다음이 같이 fire됨:
  - `update-economic-indicators` (FRED, 별도 quota — 무관)
  - `collect-market-news-evening` (Marketaux/Finnhub, 별도 quota — 무관)
  - `thesis-update-readings` (DB/cache 위주로 보이나 FMP 의존성 코드 검증 필요)
- 🔍 `thesis-update-readings`가 FMP를 호출한다면 18:00 분당 200 + α → 한도 근접. 별도 점검 권장.

### 3.2 Gemini — Free Tier 15 RPM / 1500 RPD

**RPM(분당) 점검**:
- `analyze_news_deep` 자체적으로 `time.sleep(self.RPM_DELAY=4)` → 단일 태스크 내 ~15 RPM 준수 (`news/services/news_deep_analyzer.py:39,98`).
- 그러나 **동시 다발적인 LLM 태스크가 같은 분에 fire**되는 구간이 존재:

| 시점 | 동시 LLM 태스크 | 각자 RPM | 합산 RPM | 판정 |
|------|----------------|----------|----------|------|
| **08:30** | analyze-news-deep | ~15 | 15 | ✅ |
| **08:00 + 08:15 + 08:30** | keyword-pipeline → classify-batch → analyze-deep (15분 간격) | 15분 분산 | 분리 | ✅ |
| **10:00 + 10:30** | chainsight-co-mentions(LLM 여부 미확인) + analyze-deep | 30분 분산 | 분리 | ✅ |
| **12:30** | analyze-news-deep + chainsight-sync-relations(non-LLM) | 15 | 15 | ✅ |
| **16:30** | **extract-daily-news-keywords + analyze-news-deep 동시 fire** | 15 + 15 | **30** | ⚠️ |
| **18:30** | analyze-news-deep + thesis-create-snapshots(non-LLM) | 15 | 15 | ✅ |

**위험 평가**:
- ⚠️ **16:30**: `extract-daily-news-keywords`(daily)와 `analyze-news-deep`(매 2시간)가 **같은 분에 시작**. 둘 다 Gemini를 사용하며 각자 자체 RPM 관리. **분당 합산 30 RPM → Free Tier 15 RPM 초과 위험**. 429 발생 시 retry로 흡수되나 처리량 저하.
- 🔍 `extract_daily_news_keywords`와 `analyze_news_deep`가 동일 Gemini API key를 공유하면 한도 충돌. 별도 키나 서로 다른 분으로 분리 권장.

**RPD(일일) 점검** (평일 기준):
| 태스크 | 일일 호출 추정 |
|--------|---------------|
| analyze-news-deep × 6/day × 50 article | 300 |
| extract-daily-news-keywords × 1/day | 50–100 |
| keyword-generation-pipeline × 1/day (gainers ~20–30) | 20–30 |
| enrich-relationship-keywords × 1/day × 100 limit | 100 |
| chainsight-co-mentions × 1/day | 50–150 (변동) |
| extract-news-relations × 1/day | 50–100 |
| classify-news-batch × 6/day (룰+부분 LLM) | 0–100 |
| **합계** | **~570–880** |

→ ✅ Free Tier 1500 RPD에 **여유 있음** (40–60% 사용).

### 3.3 Alpha Vantage — 5 calls/min

- ✅ 의존 스케줄 **0건**. AV provider 제거 완료(commit `df85496`). `news/migrations/0005`, `news/models.py`에 잔존 텍스트(legacy migration)만 남음 — 런타임 영향 없음.

### 3.4 FRED

- `update-economic-indicators`: 4 fires/day (06, 12, 18, 22). 각 fire당 호출은 macro/services/fred_client에서 `rate_limiter.acquire()`로 제어.
- ✅ FRED 한도(보통 120/min)에 비해 호출 매우 적음.

---

## 4. Queue 분석

### 4.1 default queue
- 65+ 태스크. macOS는 `worker_pool='solo'` 강제되나 Linux 프로덕션은 prefork. 정상.
- 시장 시간(9–16) 분당 fires 평균 ~110 → prefork 4 worker 가정 시 27.5 task/worker/h. 충분히 처리 가능.

### 4.2 neo4j queue (solo pool, 동시 1개)
**queue 라우팅 매핑** (config/celery.py L37–L55):
```
rag_analysis.tasks: health_check, semantic_cache(미초기화), sync/delete/batch_sync_stocks
news.tasks.sync_news_to_neo4j
news.tasks.cleanup_expired_news_relationships
serverless.tasks.enrich_relationship_keywords
chainsight.tasks.sync_tasks.sync_profiles_to_neo4j
chainsight.tasks.sync_tasks.sync_relations_to_neo4j
chainsight-neo4j-dirty-sync
sec_pipeline.tasks.sync_dirty_to_neo4j
```

**평일 hot spot**:
| 분 | 동시 fire | 비고 |
|---|---|---|
| **00, 05, 10, … 매 5분** | `sec-sync-dirty-neo4j` (12/h × 24h = 288/day) | 상시 |
| **00 of every 6h (00, 06, 12, 18)** | + `neo4j-health-check` | 가벼움 |
| **04:00 daily** | `cleanup-expired-news-relationships` + sec-dirty | 4:00 sec-dirty와 동시 |
| **05:30 daily** | `enrich-relationship-keywords` (Gemini + Neo4j, 100 records) + sec-dirty(05:30) | enrich가 길어지면 sec-dirty 백로그 |
| **08:45, 10:45, 12:45, 14:45, 16:45, 18:45** | `sync-news-to-neo4j` (max_articles=100) + sec-dirty(:45) | ⚠️ 100 article × Cypher 쓰기 → 5분 초과 시 다음 sec-dirty(:50) 직렬 대기 |
| **12:00 정각** | `chainsight-sync-profiles-neo4j` + `sec-sync-dirty-neo4j(12:00)` + `neo4j-health-check(12:00)` | ⚠️ **3건 동시 fire — solo 직렬 처리** |
| **12:30 정각** | `chainsight-sync-relations-neo4j` + `sec-sync-dirty-neo4j(12:30)` | ⚠️ |

**위험 평가**:
- ⚠️ **12:00 정각**에 3개 neo4j 태스크가 동시 enqueue. Solo pool은 동시 1개 처리 → 3개가 직렬화. 첫 태스크가 5분 이상 걸리면 다음 sec-dirty(12:05) 도착 시점에 누적 4개 대기.
- ⚠️ **`:45` 시간대 (08:45 등)** `sync-news-to-neo4j`가 100 articles에 대한 Neo4j 쓰기. 평균 article당 Cypher 5–10건이라 가정 시 500–1000 Cypher → solo pool에서 수 분 소요. 그 사이 `sec-sync-dirty-neo4j`(:50)가 도착하여 직렬 대기.
- 🔍 `expires=240` (sec-sync-dirty)는 4분 후 자동 폐기. 직렬 대기 중 만료되면 동기화 누락 가능 → Neo4j와 Postgres 사이 dirty backlog 증가 위험.

---

## 5. 스케줄 겹침 / 의존성 분석

### 5.1 EOD 파이프라인 체인 (18:00–18:30)
```
18:00 ─ thesis-update-readings ──┐
18:00 ─ sync-sp500-eod-prices ───┼─ 같은 minute fires
18:00 ─ collect-market-news-evening
18:00 ─ update-economic-indicators
                                  │
18:15 ─ thesis-calculate-scores  ◄┘ (15분 후)
                                  │
18:30 ─ thesis-create-snapshots  ◄┘ (15분 후)
18:30 ─ run-eod-pipeline
18:30 ─ analyze-news-deep
18:30 ─ update-sp500-change-percent
```

- **의존성 risk-1**: `thesis-update-readings`가 15분 내 완료 가정. 만약 FMP/외부 API 의존성으로 지연되면 `thesis-calculate-scores`가 **부분/구 데이터로 실행** → 잘못된 스코어. ⚠️
- **의존성 risk-2**: `run-eod-pipeline`(18:30)는 `sync-sp500-eod-prices`(18:00 시작 ~2.5분 소요) 완료를 가정. 30분 gap 충분.
- **의존성 risk-3**: `update-sp500-change-percent`(18:30)도 EOD 동기화 결과 사용. 마찬가지 30분 gap → 안전.

### 5.2 News 배치 체인
```
:00 ─ collect-market-news (8,12,15,18)
:15 ─ classify-news-batch (8,10,12,14,16,18)  ← 수집 후 15분
:30 ─ analyze-news-deep (8,10,12,14,16,18)    ← 분류 후 15분
:45 ─ sync-news-to-neo4j (8,10,12,14,16,18)   ← 분석 후 15분
```
- 각 단계 15분 gap. classify(룰 + LLM 부분)는 빠름(~수 초). analyze는 4초 × 50 = 200초 ≈ 3.3분 → 15분 gap으로 충분.
- ✅ 체인 자체는 건전.
- ⚠️ classify-batch는 `kwargs={'hours': 3}`이라서 최근 3시간 분량을 매번 처리 → 새 기사 누락은 없으나 **재처리 중복 가능**(중복 처리 대비 idempotent 검증 필요, 본 감사 범위 외).

### 5.3 Chain Sight 의존성
```
NewsEntity(생성 시점: classify-batch 완료 직후 :15+)
   ↓
chainsight-co-mentions (10:00 daily) ─ 10:15 batch 직전 → 10:15 결과 미반영(다음날 처리)
   ↓
chainsight-relation-confidence (11:00 daily) ─ co-mentions 1시간 후, 충분
   ↓
chainsight-sync-relations-neo4j (12:30 daily)
```
- ⚠️ **의존성 risk-4**: `chainsight-co-mentions`(10:00)는 `classify-news-batch`(10:15 → entity 생성)를 **선행**. 10:15 batch 결과는 다음날 10:00에야 반영됨 → **24시간 지연**. 의도한 설계이면 OK, 우연이면 fix 필요.

### 5.4 정각 동시 fire 매트릭스 (가장 위험한 시점)
| 시각 | 동시 fires (default + neo4j) | API/리소스 충돌 |
|------|------------------------------|----------------|
| 06:00 | economic-indicators(FRED) + collect-daily-news + sync-etf-holdings(Mon) + sec-check-new-filings(1st) | FMP/news 다중 |
| 12:00 | economic-indicators + collect-market-news-noon + chainsight-sync-profiles-neo4j + sec-seed-relations + sec-sync-dirty + neo4j-health-check | **neo4j queue 3 동시** |
| 12:30 | analyze-news-deep + chainsight-sync-relations-neo4j + collect-general-news-fmp-noon + sec-sync-dirty + classify-news-batch(12:15+15분=12:30 시작 가정) | neo4j 2 + Gemini |
| 16:30 | extract-daily-news-keywords + analyze-news-deep + calculate-market-breadth | **Gemini 2 동시** ⚠️ |
| 16:35 | calculate-sector-heatmap + sec-sync-dirty | minor |
| 18:00 | sync-sp500-eod-prices + economic-indicators + collect-market-news-evening + thesis-update-readings + sec-sync-dirty | **FMP 200/min** |
| 18:30 | run-eod-pipeline + thesis-create-snapshots + analyze-news-deep + update-sp500-change-percent + sec-sync-dirty | Gemini + DB heavy |

---

## 6. 추가 발견 사항

### 6.1 Beat Schedule Drift
- L118–L134 주석: **dict와 DB가 어긋나면 dict의 태스크는 실행되지 않는다.**
- 2026-04-24 복구 기록: `chainsight-heat-score-daily`, `sec-seed-relations-to-chainsight`가 누락됐다가 DB에 등록됨.
- 🔍 본 감사 시점에도 **DB의 PeriodicTask 집합 vs config dict 키 집합** 일치 여부 미검증. 별도 manage.py shell 점검 필요.

### 6.2 Timezone 가정
- 모든 crontab의 `hour=`는 **EST/ET** 기준(주석 다수에 명시). Celery `timezone` 설정이 EST로 잡혀 있어야 의도와 일치. 만약 UTC 기본이라면 모든 시간이 5시간(=EST/UTC offset) 어긋남 — `config/settings.py`의 `CELERY_TIMEZONE` 별도 점검 필요.
- 일부 키 코멘트에 "UTC"라 적힌 것이 있음:
  - `chainsight-heat-score-daily` (07:00 UTC)
  - `chainsight-seed-selection` (13:00 UTC)
  - `chainsight-neo4j-dirty-sync` (04:30 UTC)
  → **EST 가정 vs UTC 가정 혼재**. 일관성 검증 필요.

### 6.3 expires 설정 일관성
- 다수 태스크: `expires=3600` (1h). 적정.
- `expires=600` (10min): collect-market-news, check-screener-alerts. 적정.
- `expires=240` (4min): `sec-sync-dirty-neo4j`. **매우 짧음** — neo4j queue 백로그 시 만료 위험.
- `expires=1500` (25min): `check-pipeline-alerts` (다음 fire 전 만료, 적정).
- `expires=14400` (4h): `validation-weekly-batch`. 적정.

### 6.4 Refresh-market-pulse-cache 부하
- `crontab(minute='*', hour='9-16', day_of_week='1-5')` → 매분 fire, 시장 7시간 = **60 × 8 = 480 fires/일**. 시장 시간만 따져도 단일 태스크 fires의 절반 차지.
- 캐시 갱신만 하므로 외부 API 부하 없음. 단, default queue **점유 시간 누적** → 다른 task latency에 영향 가능.
- 🔍 캐시 적중률/갱신 비용 모니터링 권장.

---

## 7. 권고 사항 (감사 결과 → 액션 아이템)

### High Priority
1. **18:00 EST FMP 동시 발사 검증**: `thesis-update-readings`가 FMP를 호출하는지 확인. 호출하면 `sync-sp500-eod-prices` 완료(~18:02:30) 이후로 thesis 체인을 시작하도록 시간 분리.
2. **16:30 EST Gemini 충돌 해소**: `extract-daily-news-keywords`를 16:00 또는 16:45 등 다른 분으로 이동. 또는 `analyze-news-deep` 16:30 회차를 16:45로 늦춤.
3. **neo4j queue 12:00 정각 충돌 완화**: `chainsight-sync-profiles-neo4j`를 12:01 또는 12:02로 옮겨 `sec-sync-dirty-neo4j(12:00)` 및 `neo4j-health-check(12:00)`와 분리.

### Medium Priority
4. **sec-sync-dirty-neo4j `expires=240` 재검토**: solo pool 백로그 발생 시 누락 위험. 600(10min) 정도로 상향 또는 dirty 누적 알림 추가.
5. **`chainsight-co-mentions` 시각 재검토**: 10:00은 10:15 classify-batch보다 빠름. 11:00 또는 13:00으로 옮겨 당일 새 entity 반영. (단, 의도된 24h 지연이면 유지)
6. **timezone 일관성 점검**: UTC/EST 혼재 주석을 EST 기준으로 통일하고 `CELERY_TIMEZONE` 검증.

### Low Priority / Observability
7. **dict ↔ DB drift 정기 점검 스크립트화** — 2026-04-24 복구 사례가 재발하지 않도록.
8. **Gemini 일일 호출 카운터 로깅** — 1500 RPD 60% 사용 추정치 검증.
9. **refresh-market-pulse-cache 적중률 모니터링** — 매분 fire 정당성 검증.

---

## 8. 부록 — 주요 측정값

| 항목 | 값 |
|------|----|
| 총 beat_schedule 키 | ~70 |
| neo4j queue 라우팅 태스크 | 13개 |
| 시장 시간 분당 fires (Mon–Fri 9–16) | ~110 fires/h |
| 평일 일일 sec-sync-dirty fires | 288 (12/h × 24h) |
| 평일 일일 refresh-market-pulse-cache fires | 480 (60/h × 8h) |
| 평일 추정 FMP 호출/일 | ~3,400 (sp500-news 2515 + market overlay ~900 + 기타) |
| 평일 추정 Gemini 호출/일 | ~570–880 |
| 평일 추정 FRED 호출/일 | ~16 (4 fires × 4 indicator) |

— 끝 —
