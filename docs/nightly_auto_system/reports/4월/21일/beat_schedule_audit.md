# Celery Beat 스케줄 감사 보고서

- **감사일**: 2026-04-21
- **대상**: `config/celery.py` (791줄, Beat Schedule 블록: 118~788행)
- **태스크 수**: 총 **78개** beat 엔트리
- **큐 분할**: `default` 71개, `neo4j` 8개 (solo pool, 동시 1개 제약)
- **워커 풀 제약**: macOS에서 `worker_pool = 'solo'` 강제 (Bug #25 대응)
- **감사 범위**: 읽기 전용. 코드 수정 없음.

## 요약 (TL;DR)

| 순위 | 심각도 | 이슈 | 발생 시간대 | 권고 |
|-----|-------|------|-----------|------|
| 1 | **P0** | 시장 시간(09~16시) 분당 태스크 밀도 100+개, 쿼리/캐시 태스크가 동시 폭주 | 평일 09:00–16:59 | `refresh-market-pulse-cache`(매분) 간격 재검토 |
| 2 | **P0** | 18:00/18:15/18:30 EOD 연쇄 — 선행(`thesis-update-readings`, `sync-sp500-eod-prices`)이 503 심볼 순차 처리인데 후속까지 15분 gap | 평일 18:00–18:30 | 의존성을 chord/chain으로 명시 |
| 3 | **P1** | LLM 배치 8,10,12,14,16,18시 30분 (`analyze_news_deep`, 50개/배치) — Gemini 15 RPM 한도 근접, 동일 분(`30분`)에 연쇄 시작 | 평일 `HH:30` × 6회 | `max_articles=50` 배치가 15 RPM × 3.3분 이상 필요 |
| 4 | **P1** | 08:00에 `keyword-generation-pipeline`(Gemini) + `collect-market-news-morning` 겹침, Circuit Breaker 개방 위험 | 평일 08:00 | 분 단위 offset 부여 |
| 5 | **P1** | 12:00에 `neo4j-health-check` + `chainsight-sync-profiles-neo4j` + `sec-seed-relations-to-chainsight` + `collect-market-news-noon` 동시 다발 | 매일 12:00 | neo4j queue 직렬 처리 — 최소 5분 offset 분산 필요 |
| 6 | **P2** | 일요일 03:00~04:30 ML 훈련 체인(7단계, 15분 간격) — `train_importance_model` 실패 시 전체 마비 | 일요일 03:00–04:30 | signatures chain/chord로 의존성 명시 |
| 7 | **P2** | 매월 1일 02:00–06:00 Monthly 태스크 5개 동시 다발 (`sync-sp500-constituents`, `archive-old-articles`, `refresh-korean-overviews-monthly`, `build-patent-network`, `sec-check-new-filings`) | 매월 1일 02:00–06:00 | 날짜 분산 (1, 2, 3일 등) |
| 8 | **P2** | FMP Starter 한도 여유 큼(300 calls/min) — 단, FMP orchestrator chord 시 6배치 × 84심볼 = 병렬 504 calls 순간 burst 가능 | 평일 06:15,10:15,13:15,15:15,17:15 | chord 병렬도 제한 (`concurrency=2`) |
| 9 | **P3** | Alpha Vantage 의존 beat 태스크 **0건** 확인. FRED(`update-economic-indicators`)는 rate limit 여유 | — | 해당 없음 |
| 10 | **P3** | SEC `sec-sync-dirty-neo4j`가 5분마다 neo4j queue에 투입 — queue 밀림 시 expires=240s 초과 drop 위험 | 24×12=**288/일** | expires 상향 또는 deduplication 적용 |

---

## 1. 전체 태스크 카탈로그

### 1-1. 큐 분포

| 큐 | 태스크 수 | 비고 |
|----|---------|------|
| `default` (prefork/solo) | 70 | `task_routes` 미지정 태스크 전부 |
| `neo4j` (solo pool) | 8 | `task_routes` 또는 `options.queue='neo4j'` 명시 |

**neo4j queue 내역** (동시 실행 1개 제약):
1. `neo4j-health-check` — 0,6,12,18시
2. `cleanup-expired-news-relationships` — 매일 04:00
3. `sync-news-to-neo4j` — 평일 8/10/12/14/16/18시 45분 (**6회/일**)
4. `enrich-relationship-keywords` — 매일 05:30
5. `chainsight-sync-profiles-neo4j` — 매일 12:00
6. `chainsight-sync-relations-neo4j` — 매일 12:30
7. `chainsight-neo4j-dirty-sync` — 일요일 04:30
8. `sec-sync-dirty-neo4j` — **5분마다 24시간 = 288회/일**

---

## 2. 시간대별 ASCII 히트맵 (평일 기준, EST)

분당 예상 실행 태스크 **개수** (시장 시간 `refresh-market-pulse-cache` 60회/시간 포함).

```
시간대   | 분당 태스크 개수 (평일)                     | 총계(peak)  | 밀집도
---------|--------------------------------------------|-------------|--------
00 (00시)| ##                                         |   14~15     | 저
01 (01시)| ##                                         |   15~16     | 저
02 (02시)| ##                                         |   14~18 *   | 저(월1일 피크)
03 (03시)| ##                                         |   14~20 *   | 저(일/토 피크)
04 (04시)| ##                                         |   15~26 *   | 중(일요일 7개 ML)
05 (05시)| ##                                         |   15~17     | 저
06 (06시)| ###                                        |   18        | 저
07 (07시)| ###                                        |   19        | 저
08 (08시)| ####                                       |   19        | 중
09 (09시)| #################################  장개장  |  110+       | ★최고
10 (10시)| #################################          |  113        | ★최고
11 (11시)| ################################           |  108        | ★최고
12 (12시)| #####################################      |  122        | ★최고
13 (13시)| #################################          |  110        | ★최고
14 (14시)| ##################################         |  115        | ★최고
15 (15시)| #################################          |  110        | ★최고
16 (16시)| ####################################  장마감|  117        | ★최고
17 (17시)| ###                                        |   18        | 저
18 (18시)| #####                                      |   24(18:30피크)| 중
19 (19시)| ##                                         |   16        | 저
20 (20시)| ##                                         |   15        | 저
21 (21시)| ##                                         |   14        | 저
22 (22시)| ##                                         |   15        | 저
23 (23시)| ##                                         |   14        | 저
---------|--------------------------------------------|-------------|--------
범례: # = 약 5개 태스크/시간, ★ = 집중 구간 100/시간+, * = 월/요일 조건부
```

### 2-1. 피크 분(分) 상세 — 평일 12:00

12시 정각(12:00)에 동시 시작되는 태스크:
```
┌─────────────────────────────────────────────────────────────┐
│ 12:00 EST — 동시 시작 태스크                                  │
├─────────────────────────────────────────────────────────────┤
│ default queue:                                              │
│   - refresh-market-pulse-cache            (내부)            │
│   - update-realtime-prices                (FMP /quote)      │
│   - update-market-indices                 (FMP /quote)      │
│   - calculate-portfolio-values            (내부)            │
│   - check-pipeline-alerts                 (내부 DB)         │
│   - update-economic-indicators            (FRED)            │
│   - collect-market-news-noon              (다수 provider)   │
│   - sec-seed-relations-to-chainsight      (내부)            │
│                                                             │
│ neo4j queue (solo pool, 동시 1개):                           │
│   - neo4j-health-check                    (매 6시간)        │
│   - chainsight-sync-profiles-neo4j        ← 12:00 투입      │
│   - sec-sync-dirty-neo4j                  ← 11:55,12:00 투입│
│                                                             │
│ 12:30 (30초 후 밀집):                                        │
│   - chainsight-sync-relations-neo4j       ← neo4j queue     │
│   - analyze_news_deep_batch               (Gemini LLM)      │
│   - collect-general-news-fmp-noon         (FMP)             │
│   - sec-sync-dirty-neo4j                                    │
│                                                             │
│ 12:45:                                                       │
│   - sync-news-to-neo4j                    ← neo4j queue     │
└─────────────────────────────────────────────────────────────┘
```

**문제**: 12:00–12:45 사이 neo4j queue에 **5개** 태스크가 경합. Solo pool이므로 직렬 처리되고, 각 태스크가 평균 30초~2분 소요되면 **chainsight-sync-relations-neo4j**(12:30 예약)가 `expires=3600`을 초과하지는 않으나, **sec-sync-dirty-neo4j**(expires=240s)는 12:00, 12:05, 12:10 세 건이 큐에 쌓였다가 일부 drop 가능성 있음.

### 2-2. EOD 피크 분(分) 상세 — 평일 18:00~18:45

```
18:00  thesis-update-readings                  ← 선행 지표 수집
       sync-sp500-eod-prices                   ← 503 심볼 순차(time.sleep 존재)
       collect-market-news-evening             ← 다수 provider
       update-economic-indicators              ← FRED
       neo4j-health-check                      ← neo4j queue

18:15  thesis-calculate-scores                 ← 후행, readings 필요
       classify-news-batch-morning             ← 2시간 주기

18:30  thesis-create-snapshots                 ← 후행, scores 필요
       run-eod-pipeline                        ← 다수 서비스 호출
       update-sp500-change-percent             ← DB 일괄 업데이트
       analyze-news-deep-batch                 ← Gemini 50 articles
       (5분 간격 sec-sync-dirty-neo4j)

18:45  sync-news-to-neo4j                      ← neo4j queue
```

**문제**:
- `thesis-update-readings`(18:00)과 `thesis-calculate-scores`(18:15) 사이 15분 gap이 있지만, S&P 500 급 종목에 대해 순차 처리하면 15분을 쉽게 초과. **상호 의존을 Celery chain/chord로 명시하지 않아** beat 시간 기반으로만 "희망" 중. 선행이 밀리면 후행은 빈 데이터로 시작.
- 같은 18:30에 `thesis-create-snapshots`, `run-eod-pipeline`, `update-sp500-change-percent`, `analyze-news-deep-batch` 4개가 동시 투입. default queue 워커 동시성(기본 `CELERY_WORKER_CONCURRENCY` 또는 macOS solo 1개)에 따라 head-of-line blocking.

---

## 3. Rate Limit 분석

### 3-1. FMP Starter Plan (300 calls/min)

**분당 최대 FMP 호출 추정 (평일 장중, `HH:00` 시점)**:

| 태스크 | 심볼 수 × 엔드포인트 | 분당 호출 추정 |
|-------|-----------------|--------------|
| `update-realtime-prices` | Portfolio 상위 10 × `/quote` | ~10 |
| `update-market-indices` | ~8 인덱스 × `/quote` | ~8 |
| `collect-market-news-*` | 분산 schedule | 0~30 |
| `collect-sp500-news-fmp-*` orchestrator(chord 6배치) | 503 × 1 = 504 calls burst | **504** (시작 직후) |
| `sync-sp500-financials` | 101 × 4~6 엔드포인트 | ~600 (20:00만) |
| `sync-sp500-eod-prices` | 503 × 1 = `/historical-price-full` | ~503 (18:00) |

**위험 지점**:
1. **평일 10:15, 13:15, 15:15, 17:15 등 FMP orchestrator 실행 분**: chord가 6 서브태스크를 병렬로 띄우면 순간적으로 분당 300 한도 초과 가능. 서브태스크 내에서 심볼별 `time.sleep`이 들어가 있을 경우에도 첫 10초 버스트에서 초과.
2. **평일 20:00 `sync-sp500-financials`**: 101 심볼 × 여러 엔드포인트 호출 — 단일 워커에서 순차 처리면 `time.sleep` 있으면 안전, 없으면 초과 (코드 점검 필요. 본 감사는 읽기 전용).
3. **평일 18:00 `sync-sp500-eod-prices`**: `REQUEST_DELAY` 상수로 rate limit 보호 있음 (서비스 파일에서 확인: `time.sleep(REQUEST_DELAY)`).

**결론**: 절대 호출 총량은 FMP 한도 내지만, **순간 버스트**(chord orchestrator 시작 시점)가 있고 FMP 서버의 분당 슬라이딩 윈도우 기준으로 경계에 근접.

### 3-2. Gemini Free (15 RPM, 1500 RPD)

**Gemini 호출 beat 태스크**:

| 태스크 | 주기 | 호출/회 추정 | RPM 부하 |
|-------|------|-----------|---------|
| `keyword-generation-pipeline` | 매일 08:00 | gainers 10~20개 | < 15 RPM |
| `extract-daily-news-keywords` | 매일 16:30 | 배치 | 중 |
| `analyze-news-deep-batch` | 평일 8/10/12/14/16/18시 30분 | **max_articles=50** | **50 RPM 초과 위험** |
| `extract-news-relations` | 매일 09:00 | 24시간 뉴스 스캔 | 중 |
| `enrich-relationship-keywords` | 매일 05:30 | limit=100 | **100 RPM 초과 위험** |

**문제 분석 — `analyze-news-deep-batch`**:
- 15 RPM 한도 하에 50개 기사를 순차 분석하려면 최소 50/15 × 60초 ≈ **3분 20초** 필요.
- 2시간 간격으로 예약되어 있으므로 시간상 문제 없으나, **같은 분(:30)에** `update-economic-indicators`, `collect-market-news-*`가 함께 투입되면 LLM Circuit Breaker 발화 가능.

**문제 분석 — `enrich-relationship-keywords`**:
- `limit=100`으로 100개 관계 키워드를 Gemini로 enrichment. 15 RPM이면 **6분 40초** 소요. `expires=3600`이므로 만료 전 완료 가능하지만 **일 1500 RPD의 7% 단일 태스크로 소비**.

**일일 RPD 소비량 추정 (Gemini Free)**:
- `analyze-news-deep-batch`: 50 × 6 = **300**
- `enrich-relationship-keywords`: ~100
- `keyword-generation-pipeline`: ~20
- `extract-news-relations`: ~100
- `extract-daily-news-keywords`: ~50
- **합계: ~570/1500 RPD** (38%) — 여유 있음

**그러나**: `analyze_news_deep`이 만약 `max_articles` 인자 없이 기본값 또는 큰 값으로 호출되면 한도 초과 위험. `kwargs: {'max_articles': 50}`로 명시되어 있어 안전.

### 3-3. Alpha Vantage (5 calls/min)

**본 `celery.py`에서 Alpha Vantage 직접 의존 beat 태스크: 0건 확인됨.**

- 검색 결과: `stocks.tasks.update_realtime_with_provider`는 FMP Provider 사용 (`api_request.stock_service`).
- AV는 사용자 요청 기반 동기 API 호출에만 쓰이는 것으로 판단됨. Beat 스케줄에서는 문제 없음.

---

## 4. Queue 몰림 분석

### 4-1. neo4j queue (solo pool, 동시 1개) 부하

**일일 처리 건수**:
| 태스크 | 빈도 | 일일 실행 |
|-------|-----|---------|
| `sec-sync-dirty-neo4j` | 5분마다 | **288** |
| `sync-news-to-neo4j` | 평일 6회 (8/10/12/14/16/18시 45분) | 평일 6 |
| `neo4j-health-check` | 6시간마다 | 4 |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | 1 |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | 1 |
| `enrich-relationship-keywords` | 매일 05:30 | 1 |
| `cleanup-expired-news-relationships` | 매일 04:00 | 1 |
| `chainsight-neo4j-dirty-sync` | 일요일 04:30 | 일요일 1 |
| **일일 합계 (평일)** | | **~302** |

**동시 1개 제약** 하에서:
- 평균 처리 간격 필요: 86400 / 302 ≈ **286초 (4.8분)/태스크**
- `sec-sync-dirty-neo4j` 빈도가 5분이므로 한 태스크 평균 처리 시간이 **4분 이상 걸리면 큐 영구 밀림**.
- `expires=240s` 설정으로 이미 만료된 `sec-sync-dirty-neo4j`는 drop. 데이터 손실은 없으나(다음 5분 주기가 dirty 재스캔) **observability 상 task_revoked 급증** 예상.

**위험 분(分)**: 12:00, 12:30 (chainsight 동기화 2건), 18:45 (news→neo4j).

### 4-2. default queue 부하

**장중 시간(09:00~16:59) 분당 태스크 투입**:
- 매분: `refresh-market-pulse-cache` = 1
- 5분마다: `update-realtime-prices` + `update-market-indices` + `sec-sync-dirty-neo4j`(default 제외, neo4j queue) = 2
- 10분마다: `calculate-portfolio-values` = 1
- 15분마다: `check-screener-alerts` = 1
- 30분마다: `check-pipeline-alerts` = 1

**평균 분당 default queue 투입량 (장중)**:
- 매분 1 + 5분에 2건 → 매분 0.4 + 10분에 1 → 매분 0.1 + ... ≈ **분당 1.8~2.0개 지속**.

**문제**: `check-pipeline-alerts`는 30분마다 `minute='*/30'` — 시장 시간 외에도 실행. 주간 총 24×2 = 48회/일.

---

## 5. 의존성 / 선후행 분석

### 5-1. 암묵적 의존 체인 (chain/chord 명시 없이 beat 시간 기반)

| 선행 | 후행 | Gap | 위험 |
|-----|------|-----|-----|
| `sync-sp500-eod-prices` (18:00) | `update-sp500-change-percent` (18:30) | 30분 | 503 심볼 순차 + `REQUEST_DELAY`. 15분~30분 소요 추정. 경계 시 후행이 이전 데이터로 실행 |
| `thesis-update-readings` (18:00) | `thesis-calculate-scores` (18:15) | 15분 | **위험**: 지표 수집이 15분 내 끝난다는 보장 없음 |
| `thesis-calculate-scores` (18:15) | `thesis-create-snapshots` (18:30) | 15분 | 동일 문제 |
| `sync-sp500-eod-prices` (18:00) | `run-eod-pipeline` (18:30) | 30분 | run-eod-pipeline은 EOD 가격 필요. 30분 gap 경계 |
| `run-eod-pipeline` (18:30) | `backfill-signal-accuracy` (19:00) | 30분 | 시그널 계산 필요 |
| `collect-category-news-*` (6시대) | `aggregate-daily-sentiment` (09:00) | ≥2시간 | 안전 |
| `extract-news-relations` (09:00) | — | — | Chain Sight 후속 없음 |
| `train-importance-model` (일 03:00) | `generate-shadow-report` (일 03:30) | 30분 | 학습 실패 시 리포트 빈 데이터 |
| `generate-shadow-report` (일 03:30) | `check-auto-deploy` (일 04:00) | 30분 | shadow report 의존 |
| `check-auto-deploy` (일 04:00) | `generate-weekly-ml-report` (일 04:15) | 15분 | 배포 여부 반영 |
| `generate-weekly-ml-report` (일 04:15) | `monitor-ml-performance` (일 04:20) | 5분 | **위험**: 5분 gap |
| `monitor-ml-performance` (일 04:20) | `train-lightgbm-model` (일 04:30) | 10분 | 경계 |

**권고**: 의존 태스크는 Celery `chain()` 또는 `chord()`로 명시해 선행 완료 시그널 기반 트리거. 현재는 **beat 시간 추정**에 의존하여 실패 시 cascade.

### 5-2. 월별 집중 — 매월 1일 02:00~06:00

```
02:00  sync-sp500-constituents           (FMP, 500심볼)
02:30  archive-old-articles              (DB 대량 이동)
03:00  refresh-korean-overviews-monthly  (Gemini, 500심볼 한글 LLM)
04:30  build-patent-network              (외부 API)
06:00  sec-check-new-filings             (SEC EDGAR)
```

**위험**: `refresh-korean-overviews-monthly`는 500 × Gemini 호출. 15 RPM 한도 하에 **33분 이상 소요**. 04:30 `build-patent-network` 시작 전 완료되지 않을 수 있음.

### 5-3. 토요일 집중 — 02:00~05:00 Chain Sight + Validation

```
02:00  chainsight-all-profiles           (GrowthStage + CapitalDNA + Sensitivity + Insider)
03:00  chainsight-price-co-movement      (503 심볼 상관관계 계산, CPU 집약)
04:00  chainsight-stale-decay            (감쇠 업데이트, DB 쓰기)
04:30  chainsight-aggregate-profiles     (집계)
05:00  validation-weekly-batch           (1차 검증, expires=14400)
```

**암묵 의존**: 03:00 price-co-movement → 04:30 aggregate-profiles. 503 심볼 상관관계 계산이 1.5시간을 넘으면 aggregate가 이전 데이터로 실행.

---

## 6. 세부 이슈 표

| # | 심각도 | 태스크 | 문제 | 권고 |
|---|-------|-------|-----|------|
| A1 | P0 | `thesis-update-readings` → `thesis-calculate-scores` → `thesis-create-snapshots` | beat 시간 의존, chain 미사용 | `chain()`으로 묶기 |
| A2 | P0 | `refresh-market-pulse-cache` (매분 × 8시간 = 480회/장중일) | 실시간 필요성 재검토 | 3~5분 간격으로 완화 |
| A3 | P1 | FMP orchestrator chord 6배치 동시 시작 | 순간 300+ calls burst | chord concurrency 제한 또는 배치 지연 |
| A4 | P1 | neo4j queue에 `sec-sync-dirty-neo4j` 288회/일 + expires=240s | drop 가능, observability 저하 | dedup 또는 interval 상향 (10분) |
| A5 | P1 | 일요일 04:15→04:20 `generate-weekly-ml-report`→`monitor-ml-performance` 5분 gap | 선행 지연 시 후행 빈 데이터 | chain 또는 gap 15분 |
| A6 | P1 | 매월 1일 03:00 `refresh-korean-overviews-monthly` 500×Gemini = 33분+ | 04:30 `build-patent-network` 충돌 | 매월 2일로 이동 |
| A7 | P2 | 12:00 동시 투입 (`chainsight-sync-profiles-neo4j`, `neo4j-health-check`, `sec-seed-relations-to-chainsight`, 기타 5개) | queue 경합 | 3~5분 offset |
| A8 | P2 | `aggregate-daily-sentiment` (평일 09:00) vs `chainsight-co-mentions` (매일 10:00, **주말 포함**) | 주말엔 `aggregate-daily-sentiment` 미실행으로 co-mentions가 오래된 데이터 | 주말 매터링 확인 |
| A9 | P2 | `celery-error-digest` (매일 07:00) vs `chainsight-heat-score-daily` (매일 07:00) | 같은 분 시작 (다른 큐지만 DB 경합 가능) | 1~2분 offset |
| A10 | P2 | `update-economic-calendar` (매일 01:00) — `day_of_week` 미지정 (매일) | 주말도 FRED 호출 | 평일 제한 고려 |
| A11 | P3 | `refresh-market-pulse-cache` `minute='*'` (장중) | 캐시 갱신 분당 — 실제 수요 대비 과다 | TTL 기반 lazy refresh |
| A12 | P3 | `aggregate-weekly-prices`(토요일 01:00) vs `update-economic-calendar`(01:00) | 다른 큐/내부 작업이라 큰 문제 없음 | offset 권고 |
| A13 | P3 | `sync-institutional-holdings`(16일 04:00) + `chainsight-stale-decay`(토요일 04:00) 겹칠 수 있음 (16일이 토요일이면) | 드물지만 복합 부하 | 날짜 확인 |

---

## 7. 권고 — 우선순위별

### 즉시 (P0~P1, 이번 주)
1. **EOD 의존 체인 명시화**: `thesis-*` 3개 태스크를 `chain()`으로 묶어 beat에서 18:00 단일 엔트리로 변경.
2. **`refresh-market-pulse-cache` 간격 조정**: 매분 → 5분(또는 TTL 기반). 사용자가 실제 1분 새 데이터를 요구하지 않는다면 80% 부하 감소.
3. **FMP chord burst 완화**: `collect_sp500_news_fmp_orchestrator`의 chord를 `group(...).apply_async(countdown=...)`로 배치 간 10초 지연.
4. **`sec-sync-dirty-neo4j` interval**: 5분 → 10분. 또는 dedup (이미 dirty가 없으면 no-op).

### 중기 (P1~P2, 이번 스프린트)
5. **Monthly 집중 분산**: 매월 1일 2시간 창 5개 태스크를 1/2/3/4/5일로 분산.
6. **일요일 ML 체인 chain화**: `train-importance-model → shadow-report → auto-deploy → weekly-ml-report → monitor-ml-performance → train-lightgbm`을 7단계 chain으로 변환.
7. **12:00 분산**: neo4j 동기화를 12:05, 12:10, 12:15로 5분 offset.
8. **Chain Sight 토요일 체인화**: `all-profiles → price-co-movement → stale-decay → aggregate-profiles`를 chord/chain.

### 장기 (P2~P3, 로드맵)
9. **Neo4j 동시성 확대**: neo4j queue를 solo 1개 → 2개 워커로 확대 검토 (Neo4j 드라이버 thread-safety 확인 필요).
10. **Rate Limit 통합 관리**: 각 task 내부 sleep 대신 `celery_rate_limit` 또는 Redis 기반 토큰 버킷 도입.
11. **Beat 관측성**: beat에 `task_sent` + `task_received` + `task_runtime` Prometheus metric 연동.

---

## 8. 참고 — 비교/검증 자료

- **이미 존재하는 감사**: `docs/infra/beat_schedule_audit.md` (601줄). 본 보고서는 2026-04-21 시점 기준 **재감사**.
- **관련 버그**: 공통 버그 #25 (Celery macOS SIGSEGV). 본 감사의 solo pool 제약 맥락.
- **관련 문서**: `sub_claude_md/architecture.md`, `sub_claude_md/coding-rules.md`.
- **제약 전제**: FMP Starter 300 calls/min, Gemini Free 15 RPM / 1500 RPD, AV 5 calls/min (사용자 명시).

---

## 9. 본 감사의 한계

- **소요 시간 미측정**: 각 태스크의 실제 평균 소요 시간은 `TaskResult` 테이블 또는 Celery metric에서 확인 필요. 본 보고서는 **예약 시점 충돌**만 분석.
- **Circuit Breaker 상태 미반영**: `news.services.circuit_breaker`가 FMP/Gemini 차단 중이면 실제 호출 0. 본 보고서는 **정상 운영 가정**.
- **`api_request.stock_service.get_stock_service()` 실제 rate limit 구현 미확인**: `sync-sp500-financials`의 101심볼 × 엔드포인트 × sleep이 FMP 300/min 한도를 넘는지 확인 필요 (읽기 전용 스코프 초과).
- **코드 수정 스코프 아님**: 본 감사는 문제 식별만. 실제 수정은 후속 PR에서.

---

*End of Audit Report. 2026-04-21*
