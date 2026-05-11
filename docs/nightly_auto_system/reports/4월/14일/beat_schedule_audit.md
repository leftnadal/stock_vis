# Celery Beat Schedule Audit Report

> **감사일**: 2026-04-14
> **대상 파일**: `config/celery.py` (line 118-781)
> **등록 스케줄**: 63개 beat entry
> **상태**: 읽기 전용 감사 (코드 수정 없음)

---

## 1. 태스크 인벤토리 요약

| 카테고리 | 태스크 수 | 주요 API 의존성 |
|----------|----------|----------------|
| Stocks (주가/재무) | 7 | FMP |
| Macro (거시경제) | 5 | FMP, FRED |
| RAG Analysis | 1 | Neo4j |
| Market Movers + 키워드 | 2 | FMP, Gemini |
| News 수집 | 11 | FMP, Marketaux |
| News Intelligence v3 | 10 | Gemini, Neo4j |
| FMP 대량 뉴스 (S&P 500) | 9 | FMP |
| 데이터 보존 | 1 | - |
| ETF / Supply Chain | 2 | SPDR, SEC EDGAR |
| Screener | 3 | - (DB only) |
| S&P 500 동기화 | 3 | FMP |
| Chain Sight (Phase 6-8) | 3 | Gemini, Neo4j |
| EOD Dashboard | 3 | Gemini (한글 개요) |
| Thesis Control | 3 | FMP (지표) |
| Chain Sight (프로파일/관계) | 7 | Neo4j |
| Validation | 1 | - (DB only) |
| SEC Pipeline | 3 | Neo4j, SEC EDGAR |
| 에러 모니터링/정리 | 2 | - |

---

## 2. Rate Limit 초과 구간 분석

### 2.1 FMP (Starter Plan: 300 calls/min)

#### 내부 Rate Limiter 현황

| 메커니즘 | 위치 | 설정값 |
|----------|------|--------|
| Redis 기반 글로벌 리미터 | `api_request/rate_limiter.py` | 10/min, 250/day (설정값) |
| FMP Client 내장 딜레이 | `api_request/providers/fmp/client.py` | 0.2s per request |
| Circuit Breaker | `news/services/circuit_breaker.py` | 5회 연속 실패 → 5분 차단 |

#### 시간대별 FMP 호출 예상량 (평일 기준)

| 시간대 (ET) | 태스크 | 예상 FMP calls | 위험도 |
|------------|--------|---------------|--------|
| **06:00-07:00** | collect-daily-news + sp500-news-fmp-0615 + general-news-fmp | ~504 | :warning: **HIGH** |
| **07:00-08:00** | market-movers(183) + press-releases(50) + category-news | ~233 | MEDIUM |
| **09:00-16:00** | realtime-prices(10) + market-indices(1) = 11/5min × 12 = 132/hr | ~132/hr | LOW (per hour) |
| **10:15** | sp500-news-fmp-1015 | ~503 | :warning: **HIGH** |
| **13:15** | sp500-news-fmp-1315 | ~503 | :warning: **HIGH** |
| **15:15** | sp500-news-fmp-1515 | ~503 | :warning: **HIGH** |
| **17:00-18:00** | daily-prices(10) + sp500-news-1715(503) + general-news(1) + sp500-eod(500) | ~1014 | :rotating_light: **CRITICAL** |
| **18:00** | sp500-eod-prices(500) + thesis-readings + market-news | ~520+ | :warning: **HIGH** |
| **20:00** | sp500-financials(101, 6/m rate limit) | ~101 (12분 분산) | LOW |

#### :rotating_light: CRITICAL: 17:00-18:00 FMP 폭주 구간

```
17:00  update-daily-prices ................ ~10 calls
17:00  collect-category-news-high-evening . (Marketaux, FMP 아님)
17:15  collect-sp500-news-fmp-1715 ........ ~503 calls (chord 6배치, 100/m)
17:45  collect-general-news-fmp-evening ... ~1 call
18:00  sync-sp500-eod-prices .............. ~500 calls (0.3s delay = 9분 소요)
18:00  thesis-update-readings ............. ~N calls (지표별 FMP)
18:00  collect-market-news-evening ........ ~1 call
─────────────────────────────────────────────────────
총합: ~1,015+ FMP calls in 60분 윈도우
```

**분석**:
- `collect-sp500-news-fmp-1715`는 Celery chord로 6배치 분산, 배치별 `rate_limit='100/m'` 적용
- `sync-sp500-eod-prices`는 0.3s delay로 500건 = ~150초(2.5분) 소요
- 두 태스크가 **동시 실행**되면 FMP client 내장 딜레이(0.2s)만으로는 300/min 초과 가능
- `rate_limiter.py`의 글로벌 리미터(10/min, 250/day)는 **Starter Plan 300/min과 불일치** — 리미터가 과도하게 제한적이거나, 일부 태스크가 글로벌 리미터를 우회

#### FMP 일일 호출 추정 (평일)

| 태스크 | 일일 호출수 |
|--------|-----------|
| realtime-prices (96회 × 10) | ~960 |
| market-indices (96회 × 1) | ~96 |
| sp500-news-fmp (5회 × 503) | ~2,515 |
| press-releases (1회 × 50) | ~50 |
| general-news-fmp (3회 × 1) | ~3 |
| market-movers (1회 × 183) | ~183 |
| sp500-eod-prices (1회 × 500) | ~500 |
| sp500-financials (1회 × 101) | ~101 |
| daily-prices (1회 × 10) | ~10 |
| thesis-update-readings (1회) | ~10-50 |
| **일일 총합** | **~4,428-4,468** |

> `rate_limiter.py`의 daily limit 250은 실제 사용량의 ~5.6%에 불과. 글로벌 리미터가 적용되고 있다면 대부분의 FMP 태스크가 실패해야 하므로, **리미터를 우회하는 코드 경로가 존재**하거나 리미터 설정이 비활성 상태일 가능성.

---

### 2.2 Gemini Free Tier (15 RPM, 1,500 RPD)

#### 내부 Rate Limiter 현황

| 태스크 | 딜레이 | RPM 준수 여부 |
|--------|--------|-------------|
| `analyze_news_deep` | 4s per call | 15 RPM 준수 |
| `enrich_relationship_keywords` | 4s per call | 15 RPM 준수 |
| `bulk_generate_korean_overviews` | 4s per call | 15 RPM 준수 |
| `keyword_generation_pipeline` | **딜레이 없음** | :rotating_light: **15 RPM 초과** |

#### :rotating_light: CRITICAL: `keyword_generation_pipeline` Rate Limit 미적용

- 08:00 실행, gainers ~20개 심볼에 대해 Gemini 호출
- `KeywordGenerationService.batch_generate()` 루프에 **sleep/delay 없음**
- 20개 호출이 수 초 내 발사 → **15 RPM 즉시 초과**
- 429 에러 발생 시 retry 로직에 의존하지만, Gemini Free Tier는 burst 허용 불가

#### 시간대별 Gemini 호출 충돌 분석

```
시간(ET)  태스크                          예상 Gemini calls   딜레이
─────────────────────────────────────────────────────────────────────
05:30     enrich-relationship-keywords    100 calls           4s (400s)
08:00     keyword-generation-pipeline     ~20 calls           없음 !!
08:30     analyze-news-deep               ≤50 calls           4s (200s)
10:30     analyze-news-deep               ≤50 calls           4s (200s)
12:30     analyze-news-deep               ≤50 calls           4s (200s)
14:30     analyze-news-deep               ≤50 calls           4s (200s)
16:30     analyze-news-deep               ≤50 calls           4s (200s)
16:30     extract-daily-news-keywords     1 call              -
18:30     analyze-news-deep               ≤50 calls           4s (200s)
─────────────────────────────────────────────────────────────────────
```

**16:30 충돌**: `analyze-news-deep`와 `extract-daily-news-keywords`가 동시 실행. 단, extract는 1회 호출이므로 실질 위험 낮음.

#### Gemini 일일 호출 추정 (평일)

| 태스크 | 일일 호출수 |
|--------|-----------|
| analyze-news-deep (6회 × 50) | ~300 (최대) |
| keyword-generation-pipeline (1회) | ~20 |
| enrich-relationship-keywords (1회) | ~100 |
| extract-daily-news-keywords (1회) | ~1 |
| **일일 총합** | **~421** |

> 1,500 RPD 한도 대비 **~28% 사용** — 일일 한도는 안전. 단, `analyze-news-deep`의 실제 처리량(top 15% 필터)에 따라 변동.

#### 월초 폭주: `bulk_generate_korean_overviews`

- 매월 1일 03:00 실행
- S&P 500 ~503개 심볼 × 1 Gemini call = **503 calls**
- 4s delay 적용 → ~2,012초(33분) 소요
- **이 날의 RPD = 421 + 503 = 924** — 한도 내이지만 여유 줄어듦

---

### 2.3 Alpha Vantage (Free: 5 calls/min, 500 calls/day)

beat_schedule에 **Alpha Vantage를 직접 호출하는 태스크 없음**. 주가/재무 데이터는 FMP Provider로 전환 완료. AV는 on-demand 요청에만 사용될 가능성. **스케줄 기반 AV 위험 없음.**

---

## 3. Queue 몰림 분석

### 3.1 Queue 분류

| Queue | Pool | 동시성 | 등록 태스크 |
|-------|------|--------|-----------|
| **default** | prefork (Linux) / solo (macOS) | 다중 (Linux) / 1 (macOS) | 55개 |
| **neo4j** | solo (명시적) | **항상 1** | 8개 |

### 3.2 Neo4j Queue: Solo Pool 병목 분석

neo4j queue는 `--pool=solo`로 실행되어 **동시 1개 태스크만 처리**. 다음은 neo4j queue에 라우팅되는 beat 태스크:

| 태스크 | 스케줄 | 예상 소요시간 | soft_time_limit |
|--------|--------|-------------|----------------|
| `sec-sync-dirty-neo4j` | **매 5분** (24/7) | 30-120s | 300s |
| `sync-news-to-neo4j` | 2시간마다 :45 (6회/일) | 60-300s | 600s |
| `cleanup-expired-news-rel` | 매일 04:00 | 20-90s | 300s |
| `enrich-relationship-keywords` | 매일 05:30 | 400-600s | 1800s |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | 180-600s | 1800s |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | 120-400s | 1800s |
| `chainsight-neo4j-dirty-sync` | 일요일 04:30 | 120-300s | - |
| `neo4j-health-check` | 6시간마다 | 2-10s | - |

#### :rotating_light: CRITICAL: `sec-sync-dirty-neo4j` 5분 주기 충돌

`sec-sync-dirty-neo4j`가 **24/7 매 5분** 실행되므로, 다른 neo4j 태스크 실행 중에도 계속 enqueue됨.

**시나리오 A — 평일 05:30 (keyword enrichment 블로킹)**:
```
05:25:00  sec-sync-dirty-neo4j 실행 (30-120s)
05:30:00  enrich-relationship-keywords 큐 진입 (400-600s 소요)
          ├─ 05:30 sec-sync-dirty → 큐 대기 (10분 후 실행)
          ├─ 05:35 sec-sync-dirty → 큐 대기
          └─ 05:40 sec-sync-dirty → 큐 대기
05:40:00  enrich 완료 → 밀린 sec-sync 3건 순차 처리
06:00:00  정상 복구 (약 30분 밀림)
```
> `sec-sync-dirty-neo4j`의 expires=240s(4분). 5분 주기에 240s 만료이므로, 큐 대기 중 만료되어 **자동 폐기**될 수 있음. 데이터 누락 위험.

**시나리오 B — 평일 12:00-13:00 (ChainSight 동기화 윈도우)**:
```
12:00:00  chainsight-sync-profiles-neo4j 시작 (180-600s)
12:05:00  sec-sync-dirty → 큐 대기 → 만료 가능 (expires=240s)
12:10:00  sec-sync-dirty → 큐 대기 → 만료 가능
12:10:00  chainsight-sync-profiles 완료 (최선)
12:30:00  chainsight-sync-relations-neo4j 시작 (120-400s)
12:35:00  sec-sync-dirty → 큐 대기
12:45:00  sync-news-to-neo4j → 큐 대기 (expires=3600s, 안전)
12:40:00  chainsight-sync-relations 완료 (최선)
~12:45    밀린 sec-sync + sync-news-to-neo4j 순차 처리
```
> 12:00-13:00 구간에서 **sec-sync-dirty 최대 6건 만료 가능**, sync-news-to-neo4j 1건 지연.

**시나리오 C — 토요일 02:00-05:00 (주간 배치 폭주)**:
```
02:00  chainsight-all-profiles (default queue, neo4j 아님)
03:00  chainsight-price-co-movement (default queue)
04:00  chainsight-stale-decay (default queue)
04:30  chainsight-aggregate-profiles (default queue, 300-900s)
       ※ 토요일 neo4j queue에는 sec-sync-dirty만 실행 → 안전
```
> 토요일은 neo4j queue 부하 낮음. 그러나 default queue에 대량 배치 집중.

**시나리오 D — 일요일 03:00-05:00 (ML 파이프라인 + neo4j)**:
```
03:00  train-importance-model (default)
03:30  generate-shadow-report (default)
04:00  check-auto-deploy (default)
       cleanup-expired-news-relationships (neo4j, 20-90s)
04:15  generate-weekly-ml-report (default)
04:20  monitor-ml-performance (default)
04:30  train-lightgbm-model (default)
       chainsight-neo4j-dirty-sync (neo4j, 120-300s)
05:00  cleanup-task-results (default)
```
> neo4j: 04:00 cleanup(~60s) → 04:30 dirty-sync(~200s). 사이 30분 간격으로 여유 있음. **안전.**

---

### 3.3 Default Queue 부하 분석

macOS 개발환경에서는 default queue도 `solo pool`(1 동시성). 프로덕션 Linux에서는 `prefork` pool.

**평일 09:00-16:00 default queue 부하** (고빈도 태스크):

| 태스크 | 빈도 | 시간당 실행 |
|--------|------|-----------|
| refresh-market-pulse-cache | 매 1분 | 60 |
| update-realtime-prices | 매 5분 | 12 |
| update-market-indices | 매 5분 | 12 |
| calculate-portfolio-values | 매 10분 | 6 |
| check-screener-alerts | 매 15분 | 4 |
| check-pipeline-alerts | 매 30분 | 2 |
| **시간당 총합** | | **96** |

> `refresh-market-pulse-cache`가 **매 1분** 실행 — 시간당 60회. macOS solo pool에서는 다른 태스크의 실행 기회를 지속적으로 점유.

---

## 4. 시간대별 태스크 히트맵 (평일 기준)

> 각 셀의 숫자 = 해당 시간대 태스크 실행 횟수 (고빈도 포함)
> `#` 1개 = 태스크 실행 5회

```
Hour  | Executions | Heatmap                                    | Notes
──────┼────────────┼────────────────────────────────────────────┼──────────────────
00:00 |     14     | ###                                        | sec-sync×12, alerts×2
01:00 |     15     | ###                                        | + econ-calendar
02:00 |     14     | ###                                        | (월초: sp500-constituents, archive)
03:00 |     14     | ###                                        | (월초: korean-overviews, supply-chain)
04:00 |     15     | ###                                        | + cleanup-news-neo4j
05:00 |     15     | ###                                        | + enrich-keywords(Gemini×100)
06:00 |     19     | ####                                       | FRED + news×3 + FMP-news
07:00 |     19     | ####                                       | movers(FMP×183) + press-rel + cat-news
08:00 |     19     | ####                                       | keyword-gen(Gemini!) + classify + deep
09:00 |    110     | ######################                     | MARKET OPEN + sentiment + 고빈도 시작
10:00 |    113     | #######################                    | + co-mentions + classify + deep + FMP-news
11:00 |    109     | ######################                     | + relation-confidence
12:00 |    117     | ########################                   | PEAK: FRED + FMP + neo4j-sync×2 + classify
13:00 |    111     | #######################                    | + cat-news-high + FMP-news + seed-select
14:00 |    113     | #######################                    | + daily-news-pm + classify + deep
15:00 |    110     | ######################                     | + market-news-pm + FMP-news
16:00 |    114     | #######################                    | + breadth + heatmap + keywords(Gemini)
17:00 |     18     | ####                                       | MARKET CLOSE: daily-prices + FMP-news×2
18:00 |     25     | #####                                      | EOD PIPELINE: eod+thesis+sp500 + classify
19:00 |     16     | ####                                       | ml-labels + signal-accuracy
20:00 |     15     | ###                                        | sp500-financials(FMP×101)
21:00 |     14     | ###                                        | sec-sync + alerts only
22:00 |     15     | ###                                        | + FRED indicators
23:00 |     14     | ###                                        | sec-sync + alerts only
──────┴────────────┴────────────────────────────────────────────┴──────────────────

LEGEND:  # = 5 task executions    Market hours: ██ (09-16)
```

### 시간대별 API 호출 히트맵 (FMP 중심, 평일)

```
Hour  | FMP calls  | Heatmap (FMP)                              | Risk
──────┼────────────┼────────────────────────────────────────────┼──────
00-05 |      0     |                                            |
05:30 |      0     |                                            | (Gemini only)
06:00 |   ~504     | ██████████████████████████                 | HIGH
07:00 |   ~233     | ████████████                               | MEDIUM
08:00 |     ~1     | ▏                                          | (Gemini only)
09:00 |   ~132     | ███████                                    | LOW
10:00 |   ~635     | ████████████████████████████████           | HIGH
11:00 |   ~132     | ███████                                    | LOW
12:00 |   ~134     | ███████                                    | LOW
13:00 |   ~635     | ████████████████████████████████           | HIGH
14:00 |   ~132     | ███████                                    | LOW
15:00 |   ~635     | ████████████████████████████████           | HIGH
16:00 |   ~132     | ███████                                    | LOW
17:00 |  ~1014     | ██████████████████████████████████████████ | CRITICAL
18:00 |   ~520     | ██████████████████████████                 | HIGH
19:00 |      0     |                                            |
20:00 |   ~101     | █████                                      | LOW
21-23 |      0     |                                            |
──────┴────────────┴────────────────────────────────────────────┴──────

LEGEND:  █ = ~25 FMP API calls
```

### 시간대별 Gemini 호출 히트맵 (평일)

```
Hour  | Gemini RPM | Heatmap (Gemini)          | Risk
──────┼────────────┼───────────────────────────┼──────
05:30 |   ~15/min  | ███████████████           | (4s delay, 한도 정확히)
08:00 |   >15/min  | ████████████████████      | CRITICAL (no delay!)
08:30 |   ~15/min  | ███████████████           | (4s delay)
10:30 |   ~15/min  | ███████████████           |
12:30 |   ~15/min  | ███████████████           |
14:30 |   ~15/min  | ███████████████           |
16:30 |   ~15/min  | ████████████████          | + extract-keywords(1)
18:30 |   ~15/min  | ███████████████           |
──────┴────────────┴───────────────────────────┴──────

LEGEND:  █ = 1 RPM
```

---

## 5. 스케줄 겹침 / 의존성 분석

### 5.1 선행-후속 의존 관계

아래 태스크들은 **암묵적 의존성**이 있으나 Celery chain/chord가 아닌 **시간 간격**으로만 보장:

| 선행 태스크 | 후속 태스크 | 간격 | 위험 |
|------------|-----------|------|------|
| sync-daily-market-movers (07:30) | keyword-generation-pipeline (08:00) | 30분 | :white_check_mark: 안전 |
| collect-daily-news-morning (06:00) | classify-news-batch (08:15) | 2h15m | :white_check_mark: 안전 |
| classify-news-batch (:15) | analyze-news-deep (:30) | 15분 | :warning: 위험 |
| analyze-news-deep (:30) | sync-news-to-neo4j (:45) | 15분 | :warning: 위험 |
| sync-sp500-eod-prices (18:00) | update-sp500-change-percent (18:30) | 30분 | :warning: 위험 |
| sync-sp500-eod-prices (18:00) | run-eod-pipeline (18:30) | 30분 | :warning: 위험 |
| thesis-update-readings (18:00) | thesis-calculate-scores (18:15) | 15분 | :rotating_light: 위험 |
| thesis-calculate-scores (18:15) | thesis-create-snapshots (18:30) | 15분 | :rotating_light: 위험 |
| chainsight-all-profiles (Sat 02:00) | chainsight-price-co-movement (Sat 03:00) | 1시간 | :white_check_mark: |
| chainsight-co-mentions (10:00) | chainsight-relation-confidence (11:00) | 1시간 | :white_check_mark: |
| train-importance-model (Sun 03:00) | generate-shadow-report (Sun 03:30) | 30분 | :warning: 위험 |
| generate-shadow-report (Sun 03:30) | check-auto-deploy (Sun 04:00) | 30분 | :white_check_mark: |

#### :rotating_light: 18:00-18:30 EOD 의존성 체인 위험

```
18:00  sync-sp500-eod-prices (500 symbols, 0.3s delay = ~150s 최소)
18:00  thesis-update-readings (FMP 지표 수집)
       │
       ▼ 15분 간격 — 선행 완료 보장 없음
18:15  thesis-calculate-scores
       │
       ▼ 15분 간격
18:30  thesis-create-snapshots
18:30  update-sp500-change-percent (sp500-eod-prices 완료 전제)
18:30  run-eod-pipeline (sp500-eod-prices 완료 전제)
```

- `sync-sp500-eod-prices`는 500 symbols × 0.3s = 최소 150초(2.5분), 최대 9분 소요
- 18:30 후속 태스크들은 EOD 가격이 완료되었다고 가정하지만, **느린 네트워크에서는 18:09~18:15 이후에도 미완료 가능**
- `thesis-update-readings`가 FMP 호출을 병행하면 rate limit 경합 발생

#### :warning: News Intelligence Pipeline v3 15분 체인

```
Every 2 hours:
:15  classify-news-batch (규칙 엔진, Gemini 불필요)
:30  analyze-news-deep (Gemini ≤50 calls, 4s delay = 200s = 3.3분)
:45  sync-news-to-neo4j (neo4j queue, 60-300s)
```

- classify → analyze 간격 15분: classify가 규칙 기반이므로 빠르게 완료(수초). **안전.**
- analyze → sync 간격 15분: analyze가 50건 × 4s = 200s(3.3분)이면 충분. 단, Gemini 응답 지연 시 **200s 초과 가능**.
- sync-news-to-neo4j는 neo4j queue에서 `sec-sync-dirty-neo4j`와 경합.

### 5.2 데이터 경합 가능성

| 경합 쌍 | 공유 리소스 | 위험도 |
|---------|-----------|--------|
| update-realtime-prices + sync-sp500-eod-prices | DailyPrice 테이블 | LOW (시간대 분리) |
| sync-sp500-financials + thesis-update-readings | FMP API rate limit | MEDIUM (20:00 vs 18:00) |
| chainsight-sync-profiles + chainsight-sync-relations | Neo4j Stock 노드 | LOW (30분 분리) |
| sec-sync-dirty-neo4j + sync-news-to-neo4j | Neo4j solo pool | HIGH (매 5분 경합) |
| classify-news-batch + analyze-news-deep | NewsArticle 테이블 | LOW (읽기/쓰기 분리) |

---

## 6. 발견 사항 요약

### CRITICAL (즉시 조치 권장)

| # | 발견 사항 | 영향 |
|---|----------|------|
| C1 | `keyword_generation_pipeline`에 Gemini rate limit 미적용 (delay 없음) | 15 RPM 초과 → 429 에러, 키워드 생성 실패 |
| C2 | 17:00-18:00 FMP 호출 폭주 (~1,014 calls/hr) | 300 calls/min 초과 가능 → 429/데이터 누락 |
| C3 | `sec-sync-dirty-neo4j` expires(240s) < 대형 neo4j 태스크 소요시간(600s) | 5분 주기 태스크가 큐 대기 중 만료 → SEC 데이터 Neo4j 미반영 |

### HIGH (조기 조치 권장)

| # | 발견 사항 | 영향 |
|---|----------|------|
| H1 | `enrich-relationship-keywords`(400-600s)가 neo4j queue 점유 → sec-sync 3-6건 만료 | 05:30-06:10 구간 SEC→Neo4j 동기화 공백 |
| H2 | 18:00-18:30 EOD 의존성 체인이 시간 간격으로만 보장 | 느린 환경에서 선행 미완료 → 잘못된 스코어/시그널 계산 |
| H3 | `rate_limiter.py` FMP 설정(10/min, 250/day)과 실제 사용량(4,400+/day) 불일치 | 리미터 우회 또는 미적용 → 보호 장치 무력화 |
| H4 | `refresh-market-pulse-cache` 매 1분 실행 (macOS solo pool에서 queue 독점) | 개발환경에서 다른 태스크 지연 |

### MEDIUM (개선 권장)

| # | 발견 사항 | 영향 |
|---|----------|------|
| M1 | 12:00-12:45 neo4j queue에 3개 태스크 집중 (profiles + relations + news-sync) | 최대 15분 순차 처리, sec-sync 만료 가능 |
| M2 | sp500-news-fmp 5회/일 각 ~503 FMP calls, 내부 rate_limit='100/m'이지만 chord 6배치 동시 | 600/min capacity → 300/min FMP 한도 초과 가능 |
| M3 | `thesis-calculate-scores`(18:15)가 `thesis-update-readings`(18:00) 완료 전 시작 가능 | 불완전 데이터로 스코어 계산 |

### LOW (참고)

| # | 발견 사항 | 영향 |
|---|----------|------|
| L1 | 일요일 03:00-05:00에 ML 태스크 6개 순차 (default queue) | Linux prefork에서는 문제 없음, macOS에서만 지연 |
| L2 | `collect-press-releases-fmp`(50 symbols)에 call 간 sleep 없음 | FMP client 0.2s delay만 의존 |
| L3 | 월초 1일에 4개 월간 태스크 집중 (02:00-06:00) | 연간 12회, 영향 제한적 |

---

## 7. 권장 사항

> 본 보고서는 읽기 전용 감사이며, 아래는 향후 조치를 위한 제안입니다.

### 즉시 조치

1. **C1**: `keyword_service.py` `batch_generate()` 루프에 `time.sleep(4)` 추가 (Gemini 15 RPM 준수)
2. **C2**: `collect-sp500-news-fmp-1715`를 17:45 → 19:00으로 이동 (sp500-eod-prices와 시간 분리)
3. **C3**: `sec-sync-dirty-neo4j`의 `expires`를 240s → 540s로 증가, 또는 주기를 5분 → 15분으로 완화

### 단기 개선

4. **H1**: `enrich-relationship-keywords`를 neo4j queue에서 default queue로 이동 (Gemini 호출이 주 작업, Neo4j 직접 접근 안 함)
5. **H2**: EOD 18:00 체인을 Celery `chain()`으로 전환: `sync_eod → [change_percent, eod_pipeline, thesis_readings → thesis_scores → thesis_snapshots]`
6. **H3**: `rate_limiter.py`의 FMP 설정값을 실제 Starter Plan에 맞게 재검토 (300/min, 10,000/day?)

### 중기 개선

7. **M1**: 12:00 ChainSight neo4j 동기화 시간대를 새벽(02:00-03:00)으로 이동
8. **M2**: sp500-news-fmp chord의 배치별 `rate_limit`을 `100/m` → `50/m`으로 하향 (6배치 × 50 = 300/m)
9. neo4j queue 모니터링 추가: queue depth > 3 시 알림

---

## Appendix A: 전체 태스크 목록 (63개)

| # | Beat Key | Task Path | Schedule | Queue | API |
|---|----------|-----------|----------|-------|-----|
| 1 | update-realtime-prices | stocks.tasks.update_realtime_with_provider | */5 9-16h M-F | default | FMP |
| 2 | update-daily-prices | stocks.tasks.update_realtime_with_provider | 17:00 M-F | default | FMP |
| 3 | aggregate-weekly-prices | stocks.tasks.aggregate_weekly_prices | Sat 01:00 | default | - |
| 4 | sync-sp500-financials | stocks.tasks.sync_sp500_financials | 20:00 M-F | default | FMP |
| 5 | calculate-portfolio-values | users.tasks.calculate_portfolio_values | */10 9-16h M-F | default | - |
| 6 | update-economic-indicators | macro.tasks.update_economic_indicators | 6,12,18,22h M-F | default | FRED |
| 7 | update-market-indices | macro.tasks.update_market_indices | */5 9-16h M-F | default | FMP |
| 8 | update-economic-calendar | macro.tasks.update_economic_calendar | 01:00 daily | default | FRED |
| 9 | refresh-market-pulse-cache | macro.tasks.refresh_market_pulse_cache | */1 9-16h M-F | default | - |
| 10 | cleanup-old-macro-data | macro.tasks.cleanup_old_data | Sun 03:00 | default | - |
| 11 | neo4j-health-check | rag_analysis.tasks.health_check_neo4j | */6h | neo4j | Neo4j |
| 12 | sync-daily-market-movers | serverless.tasks.sync_daily_market_movers | 07:30 M-F | default | FMP |
| 13 | keyword-generation-pipeline | serverless.tasks.keyword_generation_pipeline | 08:00 daily | default | Gemini |
| 14 | collect-daily-news-morning | news.tasks.collect_daily_news | 06:00 M-F | default | Marketaux |
| 15 | collect-daily-news-afternoon | news.tasks.collect_daily_news | 14:30 M-F | default | Marketaux |
| 16 | collect-market-news-morning | news.tasks.collect_market_news | 08:00 M-F | default | Marketaux |
| 17 | collect-market-news-noon | news.tasks.collect_market_news | 12:00 M-F | default | Marketaux |
| 18 | collect-market-news-afternoon | news.tasks.collect_market_news | 15:00 M-F | default | Marketaux |
| 19 | collect-market-news-evening | news.tasks.collect_market_news | 18:00 M-F | default | Marketaux |
| 20 | aggregate-daily-sentiment | news.tasks.aggregate_daily_sentiment | 09:00 M-F | default | - |
| 21 | extract-daily-news-keywords | news.tasks.extract_daily_news_keywords | 16:30 daily | default | Gemini |
| 22 | collect-category-news-high-morning | news.tasks.collect_category_news | 06:30 M-F | default | Marketaux |
| 23 | collect-category-news-high-midday | news.tasks.collect_category_news | 13:00 M-F | default | Marketaux |
| 24 | collect-category-news-high-evening | news.tasks.collect_category_news | 17:00 M-F | default | Marketaux |
| 25 | collect-category-news-medium-morning | news.tasks.collect_category_news | 07:00 M-F | default | Marketaux |
| 26 | collect-category-news-medium-afternoon | news.tasks.collect_category_news | 14:00 M-F | default | Marketaux |
| 27 | collect-category-news-low | news.tasks.collect_category_news | 07:30 M-F | default | Marketaux |
| 28 | classify-news-batch-morning | news.tasks.classify_news_batch | 8,10,12,14,16,18h:15 M-F | default | Rule Engine |
| 29 | analyze-news-deep-batch | news.tasks.analyze_news_deep | 8,10,12,14,16,18h:30 M-F | default | Gemini |
| 30 | collect-ml-labels | news.tasks.collect_ml_labels | 19:00 M-F | default | - |
| 31 | sync-news-to-neo4j | news.tasks.sync_news_to_neo4j | 8,10,12,14,16,18h:45 M-F | neo4j | Neo4j |
| 32 | cleanup-expired-news-relationships | news.tasks.cleanup_expired_news_relationships | 04:00 daily | neo4j | Neo4j |
| 33 | train-importance-model | news.tasks.train_importance_model | Sun 03:00 | default | - |
| 34 | generate-shadow-report | news.tasks.generate_shadow_report | Sun 03:30 | default | - |
| 35 | check-auto-deploy | news.tasks.check_auto_deploy | Sun 04:00 | default | - |
| 36 | generate-weekly-ml-report | news.tasks.generate_weekly_ml_report | Sun 04:15 | default | - |
| 37 | monitor-ml-performance | news.tasks.monitor_ml_performance | Sun 04:20 | default | - |
| 38 | train-lightgbm-model | news.tasks.train_lightgbm_model | Sun 04:30 | default | - |
| 39 | check-pipeline-alerts | news.tasks.check_pipeline_alerts | */30 24/7 | default | - |
| 40 | collect-sp500-news-fmp-0615 | news.tasks.collect_sp500_news_fmp_orchestrator | 06:15 M-F | default | FMP |
| 41 | collect-sp500-news-fmp-1015 | news.tasks.collect_sp500_news_fmp_orchestrator | 10:15 M-F | default | FMP |
| 42 | collect-sp500-news-fmp-1315 | news.tasks.collect_sp500_news_fmp_orchestrator | 13:15 M-F | default | FMP |
| 43 | collect-sp500-news-fmp-1515 | news.tasks.collect_sp500_news_fmp_orchestrator | 15:15 M-F | default | FMP |
| 44 | collect-sp500-news-fmp-1715 | news.tasks.collect_sp500_news_fmp_orchestrator | 17:15 M-F | default | FMP |
| 45 | collect-press-releases-fmp | news.tasks.collect_press_releases_fmp | 07:45 M-F | default | FMP |
| 46 | collect-general-news-fmp-morning | news.tasks.collect_general_news_fmp | 06:45 M-F | default | FMP |
| 47 | collect-general-news-fmp-noon | news.tasks.collect_general_news_fmp | 12:30 M-F | default | FMP |
| 48 | collect-general-news-fmp-evening | news.tasks.collect_general_news_fmp | 17:45 M-F | default | FMP |
| 49 | archive-old-articles | news.tasks.archive_old_articles | 1st 02:30 | default | - |
| 50 | sync-etf-holdings | serverless.tasks.sync_etf_holdings | Mon 06:00 | default | SPDR |
| 51 | sync-supply-chain-batch | serverless.tasks.sync_supply_chain_batch | 15th 03:00 | default | SEC |
| 52 | calculate-market-breadth | serverless.tasks.calculate_daily_market_breadth | 16:30 M-F | default | - |
| 53 | calculate-sector-heatmap | serverless.tasks.calculate_daily_sector_heatmap | 16:35 M-F | default | - |
| 54 | check-screener-alerts | serverless.tasks.check_screener_alerts | */15 9-16h M-F | default | - |
| 55 | sync-sp500-constituents | stocks.tasks.sync_sp500_constituents | 1st 02:00 | default | FMP |
| 56 | sync-sp500-eod-prices | stocks.tasks.sync_sp500_eod_prices | 18:00 M-F | default | FMP |
| 57 | update-sp500-change-percent | update-sp500-change-percent | 18:30 M-F | default | - |
| 58 | extract-news-relations | serverless.tasks.extract_news_relations | 09:00 daily | default | Regex |
| 59 | enrich-relationship-keywords | serverless.tasks.enrich_relationship_keywords | 05:30 daily | neo4j | Gemini |
| 60 | sync-institutional-holdings | serverless.tasks.sync_institutional_holdings | 16th 04:00 | default | SEC |
| 61 | scan-regulatory-relationships | serverless.tasks.scan_regulatory_relationships | Mon 04:00 | default | - |
| 62 | build-patent-network | serverless.tasks.build_patent_network | 1st 04:30 | default | - |
| 63 | run-eod-pipeline | stocks.tasks.run_eod_pipeline | 18:30 M-F | default | - |
| 64 | backfill-signal-accuracy | stocks.tasks.backfill_signal_accuracy | 19:00 M-F | default | - |
| 65 | refresh-korean-overviews-monthly | stocks.tasks.bulk_generate_korean_overviews | 1st 03:00 | default | Gemini |
| 66 | thesis-update-readings | thesis.tasks.eod_pipeline.update_indicator_readings | 18:00 M-F | default | FMP |
| 67 | thesis-calculate-scores | thesis.tasks.eod_pipeline.calculate_scores | 18:15 M-F | default | - |
| 68 | thesis-create-snapshots | thesis.tasks.eod_pipeline.create_snapshots_and_alerts | 18:30 M-F | default | - |
| 69 | chainsight-all-profiles | chainsight.tasks.profile_tasks.calculate_all_profiles | Sat 02:00 | default | - |
| 70 | chainsight-co-mentions | chainsight.tasks.relation_tasks.extract_co_mentions | 10:00 daily | default | - |
| 71 | chainsight-price-co-movement | chainsight.tasks.relation_tasks.calculate_price_co_movement | Sat 03:00 | default | - |
| 72 | chainsight-relation-confidence | chainsight.tasks.relation_tasks.update_relation_confidence | 11:00 daily | default | - |
| 73 | chainsight-stale-decay | chainsight.tasks.relation_tasks.check_stale_and_decay | Sat 04:00 | default | - |
| 74 | chainsight-aggregate-profiles | chainsight.tasks.sync_tasks.aggregate_chain_profiles | Sat 04:30 | default | - |
| 75 | chainsight-sync-profiles-neo4j | chainsight.tasks.sync_tasks.sync_profiles_to_neo4j | 12:00 daily | neo4j | Neo4j |
| 76 | chainsight-sync-relations-neo4j | chainsight.tasks.sync_tasks.sync_relations_to_neo4j | 12:30 daily | neo4j | Neo4j |
| 77 | chainsight-seed-selection | chainsight-seed-selection | 13:00 daily | default | - |
| 78 | chainsight-neo4j-dirty-sync | chainsight-neo4j-dirty-sync | Sun 04:30 | neo4j | Neo4j |
| 79 | validation-weekly-batch | validation.tasks.run_weekly_validation_batch | Sat 05:00 | default | - |
| 80 | sec-sync-dirty-neo4j | sec_pipeline.tasks.sync_dirty_to_neo4j | */5 24/7 | neo4j | Neo4j |
| 81 | sec-seed-relations-to-chainsight | sec-seed-relations-to-chainsight | 12:00 daily | default | - |
| 82 | sec-check-new-filings | sec_pipeline.tasks.check_new_filings | 1st 06:00 | default | SEC |
| 83 | celery-error-digest | config.tasks.send_celery_error_digest | 07:00 daily | default | - |
| 84 | cleanup-task-results | config.tasks.cleanup_old_task_results | Sun 05:00 | default | - |

> 총 84개 entry (beat_schedule dict key 63개 + 일부 다중 스케줄 태스크 포함)

---

## Appendix B: Neo4j Queue 타임라인 (평일)

```
00:00 ┬─ sec-sync-dirty (5분마다, 각 30-120s)
      │   ├─ :00 :05 :10 :15 :20 :25 :30 :35 :40 :45 :50 :55
      │
04:00 ├─ cleanup-expired-news-relationships (20-90s)
      │   └─ sec-sync :00 :05 대기 → cleanup 완료 후 처리
      │
05:30 ├─ enrich-relationship-keywords (400-600s) ★ BOTTLENECK
      │   └─ sec-sync :30 :35 :40 만료(expires=240s), :45 :50 :55 만료
      │   └─ ★ 최대 6건 sec-sync 유실 가능
      │
08:45 ├─ sync-news-to-neo4j #1 (60-300s)
10:45 ├─ sync-news-to-neo4j #2
      │
12:00 ├─ chainsight-sync-profiles-neo4j (180-600s) ★ BOTTLENECK
12:30 ├─ chainsight-sync-relations-neo4j (120-400s)
12:45 ├─ sync-news-to-neo4j #3
      │   └─ sec-sync :00 :05 :10 ... 최대 4건 만료 가능
      │
14:45 ├─ sync-news-to-neo4j #4
16:45 ├─ sync-news-to-neo4j #5
18:45 ├─ sync-news-to-neo4j #6
      │
00:00 └─ (반복)

★ = neo4j solo pool 블로킹으로 sec-sync-dirty 만료 위험 구간
```

---

*감사 완료. 본 문서는 코드 변경 없이 config/celery.py의 beat_schedule 선언만을 기반으로 작성되었으며, 실제 태스크 구현 코드를 참조하여 API 호출 패턴과 소요 시간을 추정하였습니다.*
