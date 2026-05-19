# Beat Schedule Audit (2026-05-19)

**대상**: `config/celery.py` `app.conf.beat_schedule` (60+ 항목)
**Timezone**: `CELERY_TIMEZONE = 'America/New_York'` (모든 `crontab(hour=...)`은 NY 시간 = EST/EDT)
**Scheduler 실제 소스**: `django_celery_beat.schedulers:DatabaseScheduler` (DB `PeriodicTask`가 진실의 소스, dict는 reference)
**범위**: 코드 수정 없음, 읽기 전용 감사

---

## 0. Executive Summary

| 항목 | 결과 |
|------|------|
| 총 beat 항목 수 | 64 개 |
| 시장 시간(9–16 ET) 분당 트리거 | **최대 약 110~117회/시간** (`refresh-market-pulse-cache` 60회/시간 단일 기여 + 5분/10분/15분 묶음) |
| **P0 위험** | 12:00 ET 동시 점화 12개 태스크 / 18:30 ET EOD+thesis 6개 동시 / `refresh-market-pulse-cache` 분당 6 FMP 엔드포인트 추정 |
| **P1 위험** | 16:30 ET Gemini `analyze-news-deep` 폭주 (50 articles, 15 RPM 분담 필요) / Saturday 02:00–05:00 ET chainsight + validation 직렬 의존 |
| **P2 위험** | neo4j queue solo pool에 14:45 / 12:30 / 18:45 동시 sync 트리거 (큐 직렬화로 흡수되지만 시간 지연 발생) |
| Alpha Vantage 의존 beat | **0개** (스케줄 상 직접 AV 호출 태스크 없음 — beat 한도 위험 없음) |
| FRED 의존 beat | 3개 (`update-economic-indicators`, `update-economic-calendar`, `refresh-market-pulse-cache` 내부) |
| neo4j queue beat 항목 | 8개 (`sec-sync-dirty-neo4j` 5분 주기 포함) |

---

## 1. API 의존성 매핑

### 1.1 FMP (Starter: 300 calls/min, 10,000 calls/day) 의존 태스크

| 태스크 | 스케줄 (NY) | 일 호출 추정 | 비고 |
|--------|-------------|--------------|------|
| `update-realtime-prices` | `*/5 9-16 1-5` | 96/일 | 배치 quote |
| `update-daily-prices` | `17:00 1-5` | 1/일 | |
| `update-market-indices` | `*/5 9-16 1-5` | 96/일 | `fmp.get_market_indices` |
| `refresh-market-pulse-cache` | `* 9-16 1-5` | **480/일** | 내부에서 6 FMP 엔드포인트 호출 (indices/sectors/forex/commodities/dxy/calendar) → **분당 ~6 FMP, 시간당 ~360 호출, 일 ~2,880 호출** |
| `sync-daily-market-movers` | `07:30 1-5` | 1/일 | |
| `keyword-generation-pipeline` | `08:00 daily` | 1/일 | mover 기반 |
| `sync-sp500-financials` | `20:00 1-5` | 1/일 (101 종목/회) | 5일 1회전 설계 |
| `sync-sp500-eod-prices` | `18:00 1-5` | 1/일 (500 종목) | |
| `collect-sp500-news-fmp-*` (×5) | `06:15, 10:15, 13:15, 15:15, 17:15 1-5` | 5/일 | orchestrator, 종목별 fan-out |
| `collect-press-releases-fmp` | `07:45 1-5` (max_symbols=50) | 1/일 | |
| `collect-general-news-fmp-*` (×3) | `06:45, 12:30, 17:45 1-5` | 3/일 | |
| `sync-supply-chain-batch` | 매월 15일 03:00 | 월 1회 | |
| `chainsight-price-co-movement` | 토 03:00 | 주 1회 | |
| `extract-news-relations` | `09:00 daily` | 1/일 | 최근 24h |

**일일 FMP 호출 총합 추정**: 2,880 (market_pulse) + 96 (realtime quotes) + 96 (indices) + ~500 (eod prices) + ~500 (sp500 news fan-out) + 기타 = **약 4,500~6,000 calls/day**. Starter 10,000/day 대비 50~60% 사용. 캐싱 효과 미반영 시 80% 근접 가능.

**분당 피크 (9–16 ET)**:
- `refresh-market-pulse-cache` 분당 6 FMP
- 5분마다 동시 점화 시점(:00, :05, ...): + `update-realtime-prices` + `update-market-indices` = **약 8 FMP/분**
- 10분 묶음 시점(:00, :10, ...): + `calculate-portfolio-values` (FMP 추정 없음, DB 위주)
- 15분 시점(:00, :15, ...): + `check-screener-alerts`
- → **순간 피크 약 10~12 FMP/분** (300/min 한도의 4% — 안전 마진 충분)

**한도 초과 위험**: ❌ 없음 (Starter 300/min). 단, 일일 한도 60% 상시 점유 → 추가 dev 호출이나 batch 실행 시 한도 근접 가능. ⚠️

### 1.2 Gemini Free (15 RPM, 1500 RPD) 의존 태스크

| 태스크 | 스케줄 (NY) | 일 호출 추정 | 비고 |
|--------|-------------|--------------|------|
| `analyze-news-deep-batch` | `:30 of 8,10,12,14,16,18 1-5` | **6×50 = 300/일** | max_articles=50, **15 RPM 한도와 충돌** |
| `classify-news-batch` | `:15 of 8,10,12,14,16,18 1-5` | hours=3 윈도, 가변 | 분류 LLM |
| `extract-daily-news-keywords` | `16:45 daily` | 1회당 대량 | 키워드 추출 |
| `keyword-generation-pipeline` | `08:00 daily` | 1회당 대량 | mover 키워드 |
| `extract-news-relations` | `09:00 daily` | 1회 (24h 윈도) | |
| `enrich-relationship-keywords` | `05:30 daily` (limit=100) | 100/일 | neo4j queue |
| `thesis-generate-summaries` | `18:35 1-5` | 활성 thesis 수 | |
| `chainsight-co-mentions` | `10:00 daily` | 1회당 대량 | days_back=7 |
| `refresh-korean-overviews-monthly` | 매월 1일 03:00 | 500 종목 | 월 1회 폭주 |
| `train-importance-model` / `train-lightgbm-model` | 일 03:00, 04:30 | ML 학습 (LLM 미사용 추정) | |

**15 RPM 충돌 분석**:
- **16:30 ET `analyze-news-deep-batch` (50 articles)**:
  최저 처리 시간 = ⌈50/15⌉ = **4분**. 동시간대 16:30~16:34 사이 thesis 등 다른 LLM 태스크 없음 (✓).
  과거 16:30에 동시 점화되던 `extract-daily-news-keywords`는 audit P0 #8(2026-04-26)로 **16:45로 분산 완료** (코멘트에 명시).
- **18:30 + 18:35 ET 클러스터** ⚠️:
  - 18:30 `analyze-news-deep-batch` (50 articles → ~4분 소요)
  - 18:35 `thesis-generate-summaries` (활성 thesis × Gemini 1회씩)
  → analyze-news-deep가 종료되기 전 thesis-generate-summaries 점화 → **분당 15 RPM 초과 위험**. P1.
- **08:00 ET 클러스터**:
  - 08:00 `keyword-generation-pipeline` (Gemini 다회)
  - 08:15 `classify-news-batch`
  - 08:30 `analyze-news-deep-batch`
  → 8:00–8:15 사이 키워드 파이프가 진행 중일 때 8:15 classify 시작 → 일부 overlap. 키워드 파이프 길이에 따라 P2.

**일일 RPD 한도**: 6회 × 50 = 300 (analyze-deep) + classify(가변) + keywords(대량) + thesis(가변) + chainsight + extract-relations + enrich(100) + monthly(500/30일=17 평균) → **추정 600~1000 RPD**. 1500 RPD 한도 내이나 60~70% 점유.

### 1.3 Alpha Vantage (5 calls/min)

**beat 스케줄 내 AV 의존 태스크 없음** (확인: `grep -i "alpha_vantage\|AlphaVantage" macro/tasks.py stocks/tasks.py` → 결과 0). 한도 초과 위험 ❌ 없음.

### 1.4 FRED (사실상 무제한이나 응답 지연 가능)

| 태스크 | 스케줄 | 비고 |
|--------|--------|------|
| `update-economic-indicators` | `0 6,12,18,22 1-5` | 평일 4회 |
| `update-economic-calendar` | `01:00 daily` | |
| `refresh-market-pulse-cache` 내부 | 분당 (시장시간) | **~7 FRED/분** (vix, yield_spread, rates, inflation, employment, gdp, vix 재호출) |

→ FRED 자체 한도는 여유. 단, 매 분 7회 호출 자체가 외부 의존성 부하/지연 ⚠️.

---

## 2. Queue 부하 분석

### 2.1 default queue (prefork 또는 macOS solo)

대부분의 태스크가 default 큐. 시장 시간(9–16 ET) 분당 트리거가 60(market_pulse)+8(5분 묶음)+α로 집중.

**병렬성 가정**:
- Linux prefork: `concurrency=N` (기본 CPU 코어 수). 60 RPM 미만 처리에 큰 문제 없음.
- macOS solo: 단일 워커, FIFO 처리. `refresh-market-pulse-cache`가 1분당 길게 점유하면 다른 태스크 밀림.

### 2.2 neo4j queue (solo pool 강제, 동시 1개)

| 태스크 | 스케줄 (NY) | 추정 소요 |
|--------|-------------|----------|
| `sec-sync-dirty-neo4j` | `*/5 daily` | **288/일** (모든 5분 슬롯) |
| `neo4j-health-check` | `0 */6 daily` | 4/일 |
| `sync-news-to-neo4j` | `:45 of 8,10,12,14,16,18 1-5` | 6/일, max=100 |
| `cleanup-expired-news-relationships` | `04:00 daily` | 1/일 |
| `enrich-relationship-keywords` | `05:30 daily` (limit=100) | 1/일 |
| `chainsight-sync-profiles-neo4j` | `12:00 daily` | 1/일 |
| `chainsight-sync-relations-neo4j` | `12:30 daily` | 1/일 |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | 1/주 |

**solo pool 직렬화 위험**:
- `sec-sync-dirty-neo4j`가 매 5분 슬롯에 진입 → 다른 neo4j 태스크와 충돌 가능
  - 예: 12:00 ET → `sec-sync-dirty-neo4j` (5분 슬롯 12:00) + `chainsight-sync-profiles-neo4j` (12:00) → 동시 큐 진입, 직렬 처리
  - 예: 18:45 ET → `sec-sync-dirty-neo4j` (18:45) + `sync-news-to-neo4j` (18:45, max=100) → 직렬 처리 시 sec sync 지연
- `sec-sync-dirty-neo4j`의 `expires=240` (4분) → 실행 지연으로 4분 초과 시 **자동 만료 (소실)** 위험. ⚠️ P2

### 2.3 매월 1일 클러스터 (저녁 사용자 영향 없음, 운영 부하)

| 시각 (NY) | 태스크 | 부하 |
|-----------|--------|------|
| 02:00 | `sync-sp500-constituents` | API 1회 |
| 02:30 | `archive-old-articles` | DB 집약 |
| 03:00 | `refresh-korean-overviews-monthly` | **500 종목 Gemini** ⚠️ |
| 04:30 | `build-patent-network` | API 집약 |
| 06:00 | `sec-check-new-filings` | SEC EDGAR |

→ 03:00 한글 개요 생성이 15 RPM 한도 기준 **최소 33분 소요**. 04:30 patent-network와 직접 충돌 없음.

---

## 3. 시간대별 ASCII 히트맵 (NY 시간 기준, 평일)

### 3.1 전체 트리거 수 (1분 주기 포함)

```
Hour  Count  Bar (each ▮ = 5 triggers)
00    14     ▮▮▮
01    15     ▮▮▮
02    14     ▮▮▮
03    14     ▮▮▮
04    15     ▮▮▮
05    15     ▮▮▮
06    19     ▮▮▮▮
07    20     ▮▮▮▮
08    19     ▮▮▮▮
09   110     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮      ◀ market open
10   113     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
11   109     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
12   117     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮ ★   ◀ PEAK (noon cluster)
13   111     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
14   113     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
15   110     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
16   114     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮      ◀ market close + breadth/heatmap
17    18     ▮▮▮
18    27     ▮▮▮▮▮ ★                       ◀ EOD batch + thesis cluster
19    16     ▮▮▮
20    15     ▮▮▮
21    14     ▮▮▮
22    15     ▮▮▮
23    14     ▮▮▮
```

### 3.2 1분 주기 태스크 제거 후 (실제 배치 부하 측정)

`sec-sync-dirty-neo4j` (12/h), `refresh-market-pulse-cache` (60/h), `check-pipeline-alerts` (2/h) 제거.

```
Hour  Count  Bar (each ▮ = 1 trigger)
00     0
01     1     ▮
02     0
03     0
04     1     ▮
05     1     ▮
06     5     ▮▮▮▮▮
07     6     ▮▮▮▮▮▮
08     5     ▮▮▮▮▮
09    36     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮  ★ realtime+indices+portfolio+screener
10    39     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
11    35     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
12    43     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮ ★★ PEAK
13    37     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
14    39     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
15    36     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
16    40     ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
17     4     ▮▮▮▮
18    13     ▮▮▮▮▮▮▮▮▮▮▮▮▮ ★              ◀ EOD heavy batch
19     2     ▮▮
20     1     ▮
21     0
22     1     ▮
23     0
```

### 3.3 분 단위 동시 점화 핫스팟 (NY 시간)

| 시각 | 동시 점화 태스크 (P0/P1) | 영향 |
|------|--------------------------|------|
| **12:00 ET** | `neo4j-health-check`, `chainsight-sync-profiles-neo4j`, `sec-seed-relations-to-chainsight`, `update-economic-indicators`, `collect-market-news-noon`, `update-realtime-prices`, `update-market-indices`, `calculate-portfolio-values`, `refresh-market-pulse-cache`, `check-pipeline-alerts`, `sec-sync-dirty-neo4j`, `check-screener-alerts` = **12개** | neo4j queue 3개 직렬, default queue 9개 분산 (대부분 5분 주기 정점). FMP ~10 호출 동시 |
| **16:30 ET** | `analyze-news-deep-batch` (50 Gemini), `calculate-market-breadth`, `check-pipeline-alerts`, `sec-sync-dirty-neo4j`, `refresh-market-pulse-cache`, `update-realtime-prices`, `update-market-indices`, `check-screener-alerts` (16:30은 :30 슬롯) | analyze-deep가 ~4분 점유. Gemini 15 RPM 단독 점유 권장 |
| **18:00 ET** | `update-economic-indicators`, `collect-market-news-evening`, `sync-sp500-eod-prices`, `thesis-update-readings`, `neo4j-health-check`, `sec-sync-dirty-neo4j`, `check-pipeline-alerts` = **7개** | sync-sp500-eod-prices가 500종목 FMP fan-out |
| **18:30 ET** | `analyze-news-deep-batch` (50 Gemini), `run-eod-pipeline`, `thesis-create-snapshots`, `update-sp500-change-percent`, `check-pipeline-alerts`, `sec-sync-dirty-neo4j` = **6개** | ⚠️ **Gemini 15 RPM 임박** — 18:35 `thesis-generate-summaries`와 overlap |
| **18:35 ET** | `thesis-generate-summaries` + 18:30 analyze-deep 잔여 | **P1 — Gemini RPM 동시 초과 위험** |
| **08:00 ET** | `keyword-generation-pipeline` (Gemini), `collect-market-news-morning`, `check-pipeline-alerts`, `sec-sync-dirty-neo4j` = 4개 | 08:15 classify-batch와 keyword 파이프 overlap 가능 |

---

## 4. 스케줄 의존성 / 선행-후속 관계 검증

### 4.1 OK인 의존 체인

| 체인 | 시각 | 평가 |
|------|------|------|
| `sync-sp500-eod-prices` → `update-sp500-change-percent` → `run-eod-pipeline` → `backfill-signal-accuracy` | 18:00 → 18:30 → 18:30 → 19:00 | 30분 / 30분 / 30분 간격 ✓ |
| `thesis-update-readings` → `thesis-calculate-scores` → `thesis-create-snapshots` → `thesis-generate-summaries` | 18:00 → 18:15 → 18:30 → 18:35 | 15/15/5분 간격, 마지막이 빠듯 |
| `sync-daily-market-movers` → `keyword-generation-pipeline` | 07:30 → 08:00 | 30분 ✓ |
| `chainsight-co-mentions` → `chainsight-relation-confidence` | 10:00 → 11:00 | 60분 ✓ |
| `chainsight-sync-profiles-neo4j` → `chainsight-sync-relations-neo4j` | 12:00 → 12:30 | 30분 ✓ |
| `train-importance-model` → `generate-shadow-report` → `check-auto-deploy` → `generate-weekly-ml-report` → `monitor-ml-performance` → `train-lightgbm-model` | 일 03:00 → 03:30 → 04:00 → 04:15 → 04:20 → 04:30 | 직렬, 학습이 30분 내 끝나야 함 ⚠️ P2 |

### 4.2 의존 위반 / 경합 위험 ⚠️

| # | 상황 | 위험 |
|---|------|------|
| D1 | `thesis-create-snapshots` (18:30) 미완료 상태에서 `thesis-generate-summaries` (18:35) 시작 | thesis 활성 종목 多 시 snapshot DB write가 5분 초과하면 summary 입력 누락. 토요일 백테스트는 단일 종목이라 OK, 평일 다수 활성 thesis 시 P1 |
| D2 | `analyze-news-deep-batch` (16:30, 50 articles, ≥4분) + `extract-daily-news-keywords` (16:45) | 코멘트에 `extract-daily-news-keywords`를 16:30→16:45로 이동했다고 명시 (audit P0 #8 처리됨) ✓ |
| D3 | `analyze-news-deep-batch` (18:30, ≥4분 Gemini 점유) + `thesis-generate-summaries` (18:35, Gemini 호출) | **P1** — 15 RPM 동시 한도 초과. 분리 또는 직렬화 필요 |
| D4 | `aggregate-daily-sentiment` (09:00) — 선행 `collect-daily-news-morning` (06:00) 후 3시간 → 06:00 수집이 3h 내 끝나야 함 | 통상 OK ✓ |
| D5 | `extract-news-relations` (09:00) — 24h 윈도 → 같은 시각 `aggregate-daily-sentiment`와 동시 점화 | DB read 경합 정도, 큰 문제 없음 |
| D6 | `sec-sync-dirty-neo4j` `expires=240`s, neo4j queue solo pool + 다른 neo4j 태스크 직렬 | **P2** — 5분 슬롯마다 점화되지만 직전 neo4j 작업이 4분 초과 시 expire (해당 슬롯 데이터 다음 슬롯까지 대기). 큐 적체 시 누적 |
| D7 | Saturday 02:00 chainsight-all-profiles → 03:00 price-co-movement → 04:00 stale-decay → 04:30 aggregate → 05:00 validation-weekly-batch | 각 1시간 간격. profile 계산이 1시간 초과 시 직렬 깨짐. 현재 expires=7200(2h) 설정으로 어느 정도 흡수 ✓ |
| D8 | `chainsight-heat-score-daily` (07:00) → `chainsight-seed-selection` (13:00) | 6h 간격 ✓ |
| D9 | `sec-seed-relations-to-chainsight` (12:00) — 코멘트상 "시드 선정 전". 그런데 `chainsight-seed-selection`은 13:00 → 선후 관계 OK ✓ |
| D10 | `collect-sp500-news-fmp-1015` (10:15) + `classify-news-batch` (10:15) | 동시 점화. classify는 직전까지 수집된 분류대상 처리 → 10:15 동시 점화로 신규 기사 분류 누락 가능. 다음 12:15 슬롯에 처리. 운영상 허용 ✓ |
| D11 | `keyword-generation-pipeline` (08:00, daily) — `sync-daily-market-movers` (07:30, weekdays only) | 휴장일에 sync-movers는 안 도는데 keyword-pipeline은 매일 → **일/공휴일에 stale mover 기반 키워드 생성** ⚠️ P2 |
| D12 | `extract-news-relations` (`09:00`, day_of_week 미지정 → daily) — 의존 뉴스 수집은 평일만 | 주말/공휴일에 비효율 호출 (큰 부작용 없으나 무의미한 Gemini 호출 발생). P3 |
| D13 | `chainsight-co-mentions` (`10:00`, daily) / `chainsight-relation-confidence` (`11:00`, daily) — 분류 데이터는 평일 누적 | 주말에 직전 금요일 데이터 7일 윈도 재계산, 멱등이라 OK |
| D14 | `thesis-*` 4개 모두 평일만 → 평일 EOD 의존 ✓ |

---

## 5. 우선순위별 권장 조치 (조치 미수행, 보고서만)

### P0 — 즉시 검토 권장

1. **`refresh-market-pulse-cache` 분당 빈도 재검토**
   매 분 6 FMP + 7 FRED 호출. 시간당 360 FMP, 일 2,880 FMP. Starter 일일 한도 10,000 중 30%를 단일 태스크가 점유.
   - 권장: 5분 또는 캐시 TTL 일치(`CACHE_TTL['realtime']`) 주기로 완화 / 또는 `cache.delete` 제거하고 TTL만으로 갱신
2. **12:00 ET 동시 점화 12개 클러스터 분산**
   neo4j queue 3개(`neo4j-health-check`, `chainsight-sync-profiles-neo4j`, `sec-seed-relations-to-chainsight`)가 동일 분 점화. `sec-sync-dirty-neo4j`의 12:00 슬롯과 합쳐 4개 직렬 → `expires=240`인 sec-sync 만료 위험.
   - 권장: `neo4j-health-check`를 5분 어긋난 슬롯(`*/6 hour, minute=5`)으로 이동
3. **18:30 + 18:35 Gemini overlap (D3)**
   `analyze-news-deep-batch` 50 articles 처리 중 `thesis-generate-summaries` 점화 → 15 RPM 동시 초과.
   - 권장: `thesis-generate-summaries`를 18:45 또는 19:00 EST로 이동 (`backfill-signal-accuracy`는 19:00 — 비-LLM이라 동시 가능)

### P1 — 다음 점검 주기 내

4. **D11: 휴장일 `keyword-generation-pipeline` stale 데이터 사용**
   `sync-daily-market-movers`는 평일만, `keyword-generation-pipeline`은 매일 → 토/일/공휴일에 금요일 mover 재사용.
   - 권장: `day_of_week='1-5'` 추가
5. **D6: `sec-sync-dirty-neo4j` expires=240과 5분 주기 적체**
   neo4j queue solo pool에서 다른 sync 태스크가 4분 초과 시 누적.
   - 권장: `expires` 늘리거나(예: 300) 또는 5분 주기를 7~10분으로 완화
6. **08:00 ET keyword + 08:15 classify Gemini overlap (D11 변형)**
   `keyword-generation-pipeline` 길이가 가변. classify 시작 시점에 keyword 잔여 → 15 RPM 초과 가능성.
   - 권장: classify-batch 시작을 08:30 슬롯에 통합 후 08:30 deep과 직렬화 검토

### P2 — 모니터링 / 추세 관찰

7. **D7: Saturday 02:00–05:00 chainsight 직렬 체인 (1h 간격)**
   `chainsight-all-profiles` (`expires=7200`)가 1시간 초과 시 다음 단계 입력 누락 가능. 현재 처리 시간 미관측 (메트릭 부재).
   - 권장: TaskResult 소요시간 메트릭 수집 후 간격 조정 판단
8. **D12: `extract-news-relations` 주말 무용 호출**
   Gemini 미세 낭비 (큰 비용 없음).
   - 권장: `day_of_week='1-5'`

### P3 — 정보성

9. Alpha Vantage 의존 beat 0개 — 5 calls/min 한도는 beat에서 발생하지 않음. 수동/온디맨드 호출만 주의.
10. `cleanup-task-results` (일요일 05:00) ↔ `validation-weekly-batch` (토요일 05:00) — 다른 요일이라 충돌 없음 ✓

---

## 6. 결론 / 한 줄 요약

> **시장 시간 분당 부하의 50% 이상은 `refresh-market-pulse-cache` 단일 태스크에서 발생하고, 18:30 + 18:35 ET Gemini overlap 및 12:00 ET neo4j queue 4중 직렬이 가장 가시적인 P0 위험.** Rate limit 절대치는 모두 한도 내이지만 `refresh-market-pulse-cache`의 일일 FMP 점유율과 18:30 Gemini 15 RPM 동시 초과는 즉시 분산 검토 권장.

**검증 방법(코드 미수정)**:
- `python manage.py shell -c "from django_celery_beat.models import PeriodicTask; ..."`로 DB 등록 스케줄 ↔ dict drift 재확인
- Celery `TaskResult` 테이블에서 `analyze-news-deep-batch`, `chainsight-all-profiles`, `refresh-market-pulse-cache` 평균 소요시간 추출 → 18:30~18:35 overlap 실측, Saturday 체인 실측

— end of audit —
