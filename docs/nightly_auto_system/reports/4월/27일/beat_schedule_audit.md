# Beat 스케줄 감사 보고서

- **날짜**: 2026-04-27
- **분석 대상**: `config/celery.py` (813 LOC, 70개 태스크)
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **CELERY_TIMEZONE**: `America/New_York` (NYSE 시간대, DST 적용)
- **CELERY_BEAT_SCHEDULER**: `django_celery_beat.schedulers:DatabaseScheduler` ← **dict는 reference, 실제 진실은 DB**

---

## 0. 요약 (Executive Summary)

| 영역 | 상태 | 핵심 리스크 |
|------|------|-----------|
| FMP rate limit (300/min) | ⚠️ 경고 | `sync-sp500-eod-prices` (18:00 ET), `sync-sp500-financials` (20:00 ET), `collect-sp500-news-fmp-*` (5회/일) — 1분 내 500+ 호출 가능 |
| Gemini Free RPM (15) | 🔴 위험 | `analyze-news-deep-batch` (max=50, 6회/일) 단일 fire가 15 RPM을 즉시 초과. 16:30/16:45 분산은 부분적 완화에 불과 |
| Gemini Free RPD (1500) | ⚠️ 경고 | 일일 LLM 합산 추정 600~1100건, 피크일 한도 근접 |
| Alpha Vantage (5/min) | ✅ 안전 | beat_schedule에 AV 직접 의존 태스크 **없음**. 단, `update_realtime_with_provider` 내부 fallback 경로 미확인 |
| Default queue 부하 | ⚠️ 경고 | 시장 시간대 (09~16 ET) 분당 평균 1.6 태스크, 12:00/16:00 ET 시점 117 태스크/시간 |
| Neo4j queue (solo) | 🔴 위험 | `sec-sync-dirty-neo4j`가 5분마다 → 1일 288회 + 12:00 ET에 3태스크 동시 등록 (solo 직렬화) |
| 스케줄 겹침/의존 | 🔴 위험 | 18:00~18:45 ET EOD 체인이 15분 간격 → 선행 태스크 슬립 시 연쇄 실패. 일요일 04:00~04:30 ML/Chain Sight 동시 폭주 |
| 타임존 라벨 불일치 | ⚠️ 경고 | 일부 태스크 주석은 `UTC`, 일부는 `EST` — 실제 스케줄러는 `America/New_York` 일괄 해석. UTC 라벨 태스크는 **실제 4~5시간 지연 fire** |

> **메타 리스크**: `beat_schedule` dict는 단순 선언 참조이며 실제 schedule 소스는 `django_celery_beat.PeriodicTask` DB 테이블. 본 감사는 dict 기준이므로 DB 등록 누락/추가 항목과 drift 가능성 존재 (코드 주석에서 2026-04-24 drift 복구 사례 확인).

---

## 1. 태스크 인벤토리 (외부 의존도별)

### 1.1 FMP API 직접 호출 (Starter 300 calls/min 가정)

| 태스크 | 스케줄 (ET) | 부하 추정 | 비고 |
|--------|------------|----------|------|
| `update-realtime-prices` | 5분마다, 09~16, mon-fri | quote-batch 1콜/주기 (보통) | 12회/시간 |
| `update-daily-prices` | 17:00 mon-fri | quote-batch 1콜 | |
| `sync-sp500-financials` | 20:00 mon-fri | **101 종목 × ~5 endpoint = ~500 콜** | 청크 분할 시 안전 |
| `update-market-indices` | 5분마다, 09~16, mon-fri | ~10~30 콜/주기 | 12회/시간 |
| `sync-daily-market-movers` | 07:30 mon-fri | gainers/losers/active = ~3~10 콜 | |
| `collect-press-releases-fmp` | 07:45 mon-fri | max_symbols=50 → 50 콜 | |
| `collect-sp500-news-fmp-*` | 06:15 / 10:15 / 13:15 / 15:15 / 17:15 mon-fri | **500 종목/회** (orchestrator) | 청크 분할 필수 |
| `collect-general-news-fmp-*` | 06:45 / 12:30 / 17:45 mon-fri | 단일 endpoint | |
| `sync-sp500-eod-prices` | 18:00 mon-fri | **500 종목 EOD** | 청크 분할 필수 |
| `collect-daily-news-*` | 06:00, 14:30 mon-fri | 종목 N회 (소스 혼합 가능) | |
| `collect-market-news-*` | 08, 12, 15, 18 mon-fri | 단일 endpoint | |
| `collect-category-news-*` | 06:30, 07:00, 07:30, 13:00, 14:00, 17:00 mon-fri | 카테고리 종목 N회 | |

### 1.2 Gemini LLM 의존

| 태스크 | 스케줄 (ET) | 추정 LLM 콜 | 비고 |
|--------|------------|------------|------|
| `keyword-generation-pipeline` | 08:00 daily | ~50~100 | gainers 우선 |
| `extract-daily-news-keywords` | 16:45 daily | ~100~200 | 16:30 analyze-deep 충돌 회피 위해 분산 |
| `extract-news-relations` | 09:00 daily | ~50~100 | 24h window |
| `chainsight-co-mentions` | 10:00 daily | ~50~100 | 7일 window |
| `enrich-relationship-keywords` | 05:30 daily | **limit=100** 직접 명시 | neo4j queue 병행 |
| `analyze-news-deep-batch` | **HH:30, HH=8,10,12,14,16,18 mon-fri** | **max_articles=50/회 × 6회 = 300/일** | 🔴 단일 fire가 15 RPM 즉시 초과 |
| `classify-news-batch` | HH:15, HH=8,10,12,14,16,18 mon-fri | 규칙 엔진 우선, LLM 보조 (Pipeline v3) | LLM 비중 미확인 |
| `bulk_generate_korean_overviews` | 1일 03:00 ET (월간) | **500 종목 = 500 콜** | 일일 한도 1500 RPD의 1/3 |

**일일 RPD 합산 추정 (평일)**: 50 + 100 + 100 + 100 + 100 + 300 = **약 750~1100 RPD** → 1500 한도의 50~73%. 월 초 1일에는 `bulk_generate_korean_overviews` 추가로 1500 한도 근접.

### 1.3 Neo4j Queue (solo pool, 동시 1)

| 태스크 | 스케줄 (ET) | 추정 소요 | 부하 |
|--------|------------|----------|------|
| `sec-sync-dirty-neo4j` | **5분마다 (24/7)** | 보통 <30s, 큐 ↑시 ↑ | **288 fire/일** |
| `neo4j-health-check` | 6시간마다 | <5s | 4 fire/일 |
| `sync-news-to-neo4j` | HH:45, HH=8,10,12,14,16,18 mon-fri | max_articles=100 | 6 fire/일 |
| `cleanup-expired-news-relationships` | 04:00 daily | 중간 | |
| `enrich-relationship-keywords` | 05:30 daily | LLM + Neo4j → 길어질 수 있음 | |
| `chainsight-sync-profiles-neo4j` | 12:00 daily | 중간 | |
| `chainsight-sync-relations-neo4j` | 12:30 daily | 중간 | |
| `chainsight-neo4j-dirty-sync` | Sun 04:30 | 주간 큰 배치 | |

### 1.4 외부 API 미사용 (DB 집계/계산)

`aggregate-weekly-prices`, `update-sp500-change-percent`, `calculate-portfolio-values`, `refresh-market-pulse-cache`, `aggregate-daily-sentiment`, `calculate-market-breadth`, `calculate-sector-heatmap`, `run-eod-pipeline`, `backfill-signal-accuracy`, `thesis-*`, `chainsight-heat-score-daily`, `chainsight-seed-selection`, `train-importance-model`, `train-lightgbm-model`, `monitor-ml-performance`, `check-pipeline-alerts`, `cleanup-task-results`, `celery-error-digest`, `archive-old-articles`

---

## 2. 시간대별 부하 히트맵 (평일 기준, ET)

수치는 시간당 fire 횟수 (recurring 태스크 분 단위 합산 + 시간별 단발 태스크). 막대 1칸 ≈ 2 fires.

```
시간대(ET)  | fires/h | 부하
============================================================================================
00 ET       |   14    | #######                                                  (baseline)
01 ET       |   15    | ########                                                  +econ-calendar
02 ET       |   14    | #######                                                   baseline
03 ET       |   14    | #######                                                   baseline (+월간/주간 추가됨)
04 ET       |   15    | ########                                                  +cleanup-news-rel
05 ET       |   15    | ########                                                  +enrich-rel(LLM)
06 ET       |   19    | ##########                                                +수집 4~5종 +neo4j-health
07 ET       |   20    | ##########                                                +mover, press, error-digest
08 ET       |   19    | ##########                                                +keyword-pipe, classify, analyze, sync-neo4j
09 ET ▼시장 |  110    | #######################################################  +realtime/indices/portfolio/pulse/screener
10 ET       |  113    | #########################################################  +co-mentions(LLM), sp500-news
11 ET       |  110    | #######################################################  +rel-confidence
12 ET       |  117    | ##########################################################  ★PEAK +econ, news, neo4j-sync 3종
13 ET       |  111    | #######################################################  +cat-news, sp500-news, seed-selection
14 ET       |  116    | ##########################################################  +daily-news, classify, analyze, sync-neo4j
15 ET       |  111    | #######################################################  +market-news, sp500-news
16 ET ▲시장 |  117    | ##########################################################  ★PEAK +extract-keywords, breadth, heatmap
17 ET       |   18    | #########                                                 +daily-prices, news 3종
18 ET       |   26    | #############                                             ★EOD 체인 11종 동시 (thesis+eod+sp500-eod)
19 ET       |   16    | ########                                                  +ml-labels, backfill-accuracy
20 ET       |   15    | ########                                                  +sp500-financials (FMP heavy)
21 ET       |   14    | #######                                                   baseline
22 ET       |   15    | ########                                                  +econ-indicators
23 ET       |   14    | #######                                                   baseline
============================================================================================
baseline = 12(sec-sync-dirty-neo4j 5분마다) + 2(check-pipeline-alerts 30분마다)
시장 시간 = 60(market-pulse-cache 1분마다) + 12(realtime) + 12(indices) + 6(portfolio) + 4(screener-alerts) = 94/시간
```

**해석**:
- 시장 시간대 (09~16 ET) 시간당 110+ fire 베이스라인 = 분당 약 1.8개 태스크 생성.
- **12:00 ET**와 **16:00 ET**가 단일 시간대 최대 부하 (117 fires/h).
- **18:00~18:45 ET 구간**에 EOD 파이프라인 11개 태스크가 15분 간격으로 직렬 의존성 가짐 → 그래프 형태 부하는 낮으나 **연쇄 실패 위험은 가장 높음**.

---

## 3. Rate Limit 초과 구간 분석

### 3.1 FMP (300 calls/min Starter)

| 구간 (ET) | 동시 발생 FMP 태스크 | 예상 최대 콜/분 | 결론 |
|-----------|--------------------|----------------|------|
| 09:00 / 09:05 / ... 16:55 | realtime + indices (각 5분 주기) | 30~50 | ✅ 안전 |
| 06:15 mon-fri | sp500-news-fmp-0615 (500 종목) | **청크 미분산 시 500/min** | 🔴 청크 분할 검증 필요 |
| 06:45 mon-fri | general-news-fmp-morning | <20 | ✅ |
| 07:30 mon-fri | sync-daily-market-movers + collect-category-news-low | ~20 | ✅ |
| 07:45 mon-fri | collect-press-releases-fmp (50) | 50 | ✅ |
| 10:15 / 13:15 / 15:15 / 17:15 mon-fri | sp500-news-fmp-* (500) | **청크 미분산 시 500/min** | 🔴 |
| **17:45 mon-fri** | general-news-fmp-evening + collect-category-news-high-evening (17:00 잔여) | <30 | ✅ |
| **18:00 mon-fri** | **sync-sp500-eod-prices** + market-news-evening + 5분 주기 휴지 (시장 종료) | **500 종목 EOD 청크 미분산 시 500/min** | 🔴 |
| **20:00 mon-fri** | **sync-sp500-financials** (101 종목 × 5 endpoint) | **~500/min if 동시** | 🔴 청크 분할 필수 |

**FMP 핵심 권고 (감사 결론)**:
- `collect-sp500-news-fmp-*`, `sync-sp500-eod-prices`, `sync-sp500-financials`는 **공통적으로 500 단위 일괄 처리** 의심. orchestrator 패턴 또는 chord 분할 여부를 implementation 수준에서 별도 점검 필요.
- 5개 sp500-news-fmp 호출은 동일 시간대(HH:15)에 분 단위 충돌 없음 (각 다른 시간대에 fire) — 일별 분산 양호.

### 3.2 Gemini Free (15 RPM, 1500 RPD)

#### RPM 초과 위험 (분당)

| 구간 (ET) | 동시 LLM 태스크 | 예상 콜 | RPM 위험 |
|-----------|----------------|--------|---------|
| 05:30 daily | enrich-relationship-keywords (limit=100) | **100 콜 → 약 7분에 걸쳐 throttle** | ⚠️ throttle 의존 |
| 08:00 daily | keyword-generation-pipeline | ~50 | ⚠️ |
| 08:30 mon-fri | analyze-news-deep-batch (max=50) | **50 콜** | 🔴 즉시 RPM 4배 |
| 09:00 daily | extract-news-relations + aggregate-daily-sentiment | ~50 | ⚠️ |
| 10:00 / 10:30 daily | chainsight-co-mentions (10:00) → analyze-news-deep (10:30) | 30분 간격, 50+50 | ⚠️ co-mentions가 30분 초과 시 겹침 |
| 12:30, 14:30, 16:30, 18:30 | analyze-news-deep-batch | **각 50 콜** | 🔴 |
| 16:30 + 16:45 | analyze-news-deep + extract-daily-news-keywords | **15분 분리 (audit P0 #8 완화)** | ⚠️ 15 RPM throttle 시 50 콜 처리에 약 4분 소요 → 16:34에 끝나면 안전, 그 이상 지연 시 16:45와 충돌 |

🔴 **핵심 결론**: `analyze-news-deep-batch`는 `max_articles=50`을 단일 fire에서 처리하면, 모델 호출이 articles 단위 1:1 매핑일 경우 **15 RPM 한도를 즉시 4배 초과**. 내부에 retry/backoff/배치 prompt가 없으면 매 fire마다 60% 이상 실패 가능.

#### RPD (일일 1500) 추정

평일 LLM 콜 합산 (보수적):
- `analyze-news-deep-batch` 6 × 50 = 300
- `enrich-relationship-keywords` = 100
- `extract-news-relations` ≈ 100
- `extract-daily-news-keywords` ≈ 150
- `chainsight-co-mentions` ≈ 100
- `keyword-generation-pipeline` ≈ 50
- `classify-news-batch` (LLM 보조 시) ≈ 0~100

→ **합산 750~900 RPD** (평일 기준, 1500의 50~60%).

월 초 1일 평일이면 `bulk_generate_korean_overviews` (S&P 500 = 500) 추가 → **1250~1400 RPD**, **한도 근접**.

### 3.3 Alpha Vantage (5 calls/min)

beat_schedule에 AV를 직접 의존하는 태스크 명시 **없음**. 위험 영역은 다음 두 곳에 한정됨:
- `update_realtime_with_provider` 내부 provider fallback 경로에 AV가 포함되는지 (코드 미확인)
- 수동 트리거되는 `API_request/` 동기화 (스케줄 외부)

→ **권고**: `stocks/services/providers.py` 또는 유사 모듈에서 AV 우선순위/조건을 확인하여 본 감사 다음 패스에서 보강.

---

## 4. Queue 몰림 분석

### 4.1 default queue

- 베이스라인: 베이스 14/h + 시장 시간대 +94/h.
- **피크 분 (HH:00)**: realtime + indices + portfolio + market-pulse + screener 5종 + 시별 단발 추가 = 분당 6~12 태스크 동시 enqueue.
- **18:00 ET**: 11종 동시 enqueue (thesis-update-readings, sync-sp500-eod-prices, market-news-evening, neo4j-health-check, econ-indicators, ...). EOD 마감 직후 부하 가장 무거움.
- **20:00 ET**: sync-sp500-financials 단일이지만 내부 청크 fan-out 시 default queue 점유 길어짐.

### 4.2 neo4j queue (solo pool, 동시 1개)

solo pool은 fork 비안전성 회피용 — **태스크 간 직렬화** 비용 큼.

베이스라인 부하 (24/7):
- `sec-sync-dirty-neo4j` 5분마다 = 12 fire/h × 24h = **288 fire/일**

겹침 시점:
| 시점 (ET) | neo4j queue 동시 fire |
|-----------|----------------------|
| 매 HH:00 (00, 06, 12, 18) | sec-sync-dirty-neo4j + neo4j-health-check |
| 04:00 daily | sec-sync-dirty + cleanup-expired-news-relationships |
| 05:30 daily | sec-sync-dirty + enrich-relationship-keywords (LLM 포함, 길어짐) |
| 08:45 / 10:45 / 12:45 / 14:45 / 16:45 / 18:45 mon-fri | sec-sync-dirty + sync-news-to-neo4j |
| **12:00 mon-fri** | sec-sync-dirty + chainsight-sync-profiles-neo4j + neo4j-health-check (3종) |
| 12:30 mon-fri | sec-sync-dirty + chainsight-sync-relations-neo4j |
| Sun 04:30 | sec-sync-dirty + chainsight-neo4j-dirty-sync (주간 대형) |

🔴 **위험**: solo pool에서 `chainsight-sync-profiles-neo4j` 또는 `chainsight-neo4j-dirty-sync`가 5분을 초과하면 다음 `sec-sync-dirty-neo4j`(5분 주기)가 큐에 쌓임. expires=240s(4분)이므로 **expires 초과 시 silent drop**. 즉 큐 지연이 길어질수록 SEC dirty 동기화가 무음 누락.

### 4.3 권고 (감사 관점, 코드 변경 없이 운영 모니터링)

1. neo4j queue 길이 메트릭 (Flower or Prometheus) 5분 단위 알림 임계값 5 설정.
2. `sec-sync-dirty-neo4j`의 expires=240 초과 silent drop 로그 추출 (Celery `task_revoked`/expires 이벤트).

---

## 5. 스케줄 겹침 / 의존성 분석

### 5.1 EOD 체인 (18:00~18:45 ET, 평일)

```
18:00  thesis-update-readings        ──┐
18:00  sync-sp500-eod-prices (FMP)   ──┼─→ 둘 다 완료되어야 정확
18:00  collect-market-news-evening   │
18:00  update-economic-indicators    │
18:00  neo4j-health-check (6h)       │
       ↓ 15분
18:15  thesis-calculate-scores       ←── readings 의존 (15분 윈도)
18:15  classify-news-batch
       ↓ 15분
18:30  thesis-create-snapshots       ←── scores 의존 (15분 윈도)
18:30  run-eod-pipeline              ←── sp500-eod-prices 의존 (30분 윈도)
18:30  update-sp500-change-percent   ←── sp500-eod-prices 의존 (30분 윈도)
18:30  analyze-news-deep-batch (LLM, 50 articles → 4분 throttle)
       ↓ 15분
18:45  sync-news-to-neo4j (neo4j queue)  ←── analyze-deep 의존 (15분 윈도)
```

🔴 **위험 시나리오**:
- FMP 응답 지연으로 `sync-sp500-eod-prices`가 30분 초과 → `run-eod-pipeline`이 부분 데이터로 실행.
- `analyze-news-deep-batch`가 Gemini throttle로 5분 이상 소요 → `sync-news-to-neo4j` 18:45가 실행되어도 분석 미완료 데이터 동기화.
- `thesis-update-readings`가 15분 초과 → `thesis-calculate-scores`가 어제 데이터로 계산.

### 5.2 News Pipeline v3 체인 (HH=8,10,12,14,16,18 ET 6회/일)

```
HH:15  classify-news-batch          (규칙 엔진 + LLM 보조)
       ↓ 15분
HH:30  analyze-news-deep-batch      (max=50, LLM ~4분)
       ↓ 15분
HH:45  sync-news-to-neo4j           (neo4j queue, 직전 분석 의존)
```

각 단계 15분 윈도. analyze-deep 4분이면 여유, but 동일 큐 다른 태스크가 점유 시 뒤로 밀림.

### 5.3 일요일 04:00~04:30 ML 폭주

| 시점 | default queue | neo4j queue |
|------|---------------|-------------|
| 04:00 | check-auto-deploy + scan-regulatory + cleanup-expired-news + chainsight-stale-decay | cleanup-expired-news-relationships + sec-dirty + neo4j-health |
| 04:15 | generate-weekly-ml-report | |
| 04:20 | monitor-ml-performance | |
| 04:30 | train-lightgbm-model + chainsight-aggregate-profiles + (1일 시 build-patent-network) + (15일 시 sync-supply-chain-batch) | chainsight-neo4j-dirty-sync |

🔴 **1일 + 일요일 + 15일 일치 (5년에 한 번)**: 04:30에 4개 대형 배치 동시 실행 — 메모리 압박 위험.

### 5.4 타임존 라벨 불일치 (감사 결과)

`CELERY_TIMEZONE = 'America/New_York'`이므로 모든 crontab은 NY 시간 (DST 적용).

| 태스크 | 주석 라벨 | 실제 fire 시간 | drift |
|--------|----------|---------------|-------|
| `chainsight-heat-score-daily` | "07:00 UTC" | **07:00 NY = 11:00~12:00 UTC** | 4~5h 지연 |
| `chainsight-seed-selection` | "13:00 UTC" | **13:00 NY = 17:00~18:00 UTC** | 4~5h 지연 |
| `chainsight-neo4j-dirty-sync` | "04:30 UTC" | **04:30 NY = 08:30~09:30 UTC** | 4~5h 지연 |

⚠️ 주석은 UTC라 적었으나 스케줄러는 NY로 해석 → 운영자가 UTC 기준 모니터링하면 실제 fire를 잘못 추적. **문서/주석 정합 작업 권고** (단, 이 감사는 코드 변경 없으므로 보고만 한다).

### 5.5 reference dict ↔ DB drift 위험

- 코드 주석 (line 117~134): "이 dict는 런타임에 무시된다 ... 2026-04-24 두 태스크 누락 복구."
- `DatabaseScheduler` 사용 시 본 dict는 단순 선언 참조. **실제 진실은 `django_celery_beat.PeriodicTask` DB 테이블**.
- 본 감사는 dict 기준이며, DB와 drift 가능성 존재. 감사 결과를 DB 등록 항목과 대조하는 후속 작업이 필요하다 (`PeriodicTask.objects.values_list('name')` vs dict keys diff).

---

## 6. 권고 사항 (운영 우선순위)

### P0 (즉시 모니터링 필요)

1. **`analyze-news-deep-batch` Gemini RPM 검증**: 단일 fire에서 50건 처리 시 throttle 동작 여부와 실패율을 1주일간 로그 수집. throttle이 없으면 max_articles 축소 또는 chunked schedule 권고 (추후 구현 PR).
2. **`sec-sync-dirty-neo4j` expires=240 초과 silent drop 추적**: Celery `task_revoked` 이벤트 카운트, 일별 grep `stocks.log` 또는 worker log.
3. **`sync-sp500-eod-prices` (18:00 ET) 청크 분산 여부**: implementation 수준에서 chord/group fan-out 확인. 1분 burst 시 FMP 300/min 초과.

### P1 (다음 PR 검토 대상)

4. **18:00~18:45 ET EOD 체인 의존 시간 확장**: 15분 → 20~25분 권고. 또는 Celery chain/chord로 명시적 의존성 표현.
5. **타임존 주석 정합화**: 일부 태스크 주석 "UTC" → 실제 NY 시간으로 변경. 또는 주석에 "NY"/"ET" 명시.
6. **drift 자동 감지 스크립트**: `python manage.py shell -c "..."`로 DB vs dict diff를 weekly 리포트화 (감사 보고서 #7과 연계).

### P2 (장기)

7. **neo4j queue 분리 검토**: `sec-sync-dirty-neo4j` (5분 주기, 짧음) 와 `chainsight-sync-*` (긴 배치) 를 분리하여 짧은 작업이 긴 작업에 막히지 않도록.
8. **Gemini 일일 사용량 대시보드**: 월 초 1일 + bulk overviews + 정상 트래픽 합산이 1500 RPD 한도에 근접 → 한도 모니터링 알림.

---

## 7. 부록 — 시간대별 단발 태스크 인덱스 (평일 기준 ET)

```
01:00  update-economic-calendar (daily)
03:00  cleanup-old-macro-data (Sun), train-importance-model (Sun), refresh-korean-overviews (1st), sync-supply-chain-batch (15th), chainsight-price-co-movement (Sat)
03:30  generate-shadow-report (Sun)
04:00  cleanup-expired-news-relationships (daily, neo4j), check-auto-deploy (Sun), sync-institutional-holdings (16th), scan-regulatory-relationships (Mon), chainsight-stale-decay (Sat)
04:15  generate-weekly-ml-report (Sun)
04:20  monitor-ml-performance (Sun)
04:30  train-lightgbm-model (Sun), chainsight-aggregate-profiles (Sat), chainsight-neo4j-dirty-sync (Sun, neo4j), build-patent-network (1st)
05:00  validation-weekly-batch (Sat), cleanup-task-results (Sun)
05:30  enrich-relationship-keywords (daily, neo4j+LLM)
06:00  collect-daily-news-morning (mon-fri), sync-etf-holdings (Mon), sec-check-new-filings (1st), neo4j-health-check (6h)
06:15  collect-sp500-news-fmp-0615 (mon-fri)
06:30  collect-category-news-high-morning (mon-fri)
06:45  collect-general-news-fmp-morning (mon-fri)
07:00  collect-category-news-medium-morning (mon-fri), chainsight-heat-score-daily (daily, "UTC" 주석 오류), celery-error-digest (daily)
07:30  sync-daily-market-movers (mon-fri), collect-category-news-low (mon-fri)
07:45  collect-press-releases-fmp (mon-fri)
08:00  keyword-generation-pipeline (daily, LLM), collect-market-news-morning (mon-fri)
08:15  classify-news-batch (mon-fri)
08:30  analyze-news-deep-batch (mon-fri, LLM 50)
08:45  sync-news-to-neo4j (mon-fri)
09:00  aggregate-daily-sentiment (mon-fri), extract-news-relations (daily, LLM)
10:00  chainsight-co-mentions (daily, LLM)
10:15/30/45  classify / analyze / sync-neo4j (mon-fri)
11:00  chainsight-relation-confidence (daily)
12:00  update-economic-indicators, collect-market-news-noon, chainsight-sync-profiles-neo4j (neo4j), sec-seed-relations-to-chainsight (daily), neo4j-health-check (6h)
12:15/30/45  classify / analyze / sync-neo4j (mon-fri); 12:30 chainsight-sync-relations-neo4j, collect-general-news-fmp-noon
13:00  collect-category-news-high-midday (mon-fri), chainsight-seed-selection (daily, "UTC" 주석 오류)
13:15  collect-sp500-news-fmp-1315 (mon-fri)
14:00  collect-category-news-medium-afternoon (mon-fri)
14:15/30/45  classify / analyze / sync-neo4j; 14:30 collect-daily-news-afternoon
15:00  collect-market-news-afternoon (mon-fri)
15:15  collect-sp500-news-fmp-1515 (mon-fri)
16:15/30  classify / analyze; 16:30 calculate-market-breadth, 16:35 calculate-sector-heatmap
16:45  extract-daily-news-keywords (daily, LLM), sync-news-to-neo4j (mon-fri)
17:00  update-daily-prices (mon-fri), collect-category-news-high-evening (mon-fri)
17:15  collect-sp500-news-fmp-1715 (mon-fri)
17:45  collect-general-news-fmp-evening (mon-fri)
18:00  thesis-update-readings, sync-sp500-eod-prices (mon-fri, FMP 500 종목), collect-market-news-evening, update-economic-indicators, neo4j-health-check (6h)
18:15  thesis-calculate-scores, classify-news-batch
18:30  thesis-create-snapshots, run-eod-pipeline, update-sp500-change-percent, analyze-news-deep-batch
18:45  sync-news-to-neo4j (mon-fri)
19:00  collect-ml-labels (mon-fri), backfill-signal-accuracy (mon-fri)
20:00  sync-sp500-financials (mon-fri, FMP heavy)
22:00  update-economic-indicators
recurring 5min (24/7): sec-sync-dirty-neo4j (neo4j queue)
recurring 30min (24/7): check-pipeline-alerts
recurring 1min (09~16 ET, mon-fri): refresh-market-pulse-cache
recurring 5min (09~16 ET, mon-fri): update-realtime-prices, update-market-indices
recurring 10min (09~16 ET, mon-fri): calculate-portfolio-values
recurring 15min (09~16 ET, mon-fri): check-screener-alerts
recurring 6h (00, 06, 12, 18 ET, daily): neo4j-health-check
```

---

**감사 종료**. 코드 변경 없음. 후속 PR 검토 시 §6 권고를 우선순위 순서로 처리.
