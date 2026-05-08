# Beat Schedule Audit — 2026-05-08

**대상 파일**: `config/celery.py:135-814` (총 820 lines, beat_schedule 항목 86개)
**감사 범위**: Rate Limit, Queue 부하, 시간대 분포, 의존성 충돌, drift 위험
**전제 조건**:
- `config/settings.py:477` — `CELERY_TIMEZONE = 'America/New_York'` (NYSE 기준 ET)
- `config/settings.py:289` — Django `TIME_ZONE = 'Asia/Seoul'` (일반 ORM/로깅 기준)
- `CELERY_BEAT_SCHEDULER = django_celery_beat.schedulers:DatabaseScheduler` — 본 감사는 코드 dict 기준이며 실제 실행은 DB `PeriodicTask` 테이블이 진실의 소스 (drift 가능성 §6에서 별도 추적)
- macOS는 solo pool 강제 (`celery.py:30-31`), neo4j queue도 `--pool=solo`로 운영 (CLAUDE.md)

> 본 보고서의 모든 시각은 ET (CELERY_TIMEZONE) 기준. UTC/EST/KST 라벨이 코드 주석과 실제 실행 시각과 불일치하는 경우 §5에서 별도 추적.

---

## 0. Severity 요약

| 심각도 | # | 이슈 | 영역 |
|--------|---|------|------|
| **P0** | 1 | 18:00 ET M-F: FMP 의존 태스크 4개 동시 fire (sync-sp500-eod-prices + thesis-update-readings + collect-market-news-evening + neo4j-health-check) → 1분 피크에 300 calls/min 초과 가능 | FMP rate limit |
| **P0** | 2 | 18:30 ET M-F: Gemini 호출 4개 근접 fire (analyze-news-deep-batch 18:30 + thesis-create-snapshots 18:30 + thesis-generate-summaries 18:35 + extract-deep는 16:30) — 50 articles 처리가 5분 내 끝나지 않으면 thesis-generate-summaries가 RPM 한도 초과 | Gemini 15 RPM |
| **P0** | 3 | 12:00 ET 매일: Neo4j queue (solo pool) 3개 태스크 동시 fire (neo4j-health-check + chainsight-sync-profiles-neo4j + sec-seed-relations-to-chainsight 12:00 + sec-sync-dirty 12:00 트리거) → 직렬화 큐잉 + 12:30에 chainsight-sync-relations-neo4j 추가 | Neo4j queue |
| **P1** | 4 | 17:00–17:45 ET M-F: FMP 4개 태스크 (collect-category-news-high-evening + update-daily-prices + collect-sp500-news-fmp-1715 + collect-general-news-fmp-evening) — 45분 윈도우 내 누적 호출 추정 200+ calls | FMP rate limit |
| **P1** | 5 | EST/UTC 라벨 혼용 — `chainsight-heat-score-daily`(741), `chainsight-seed-selection`(749), `chainsight-neo4j-dirty-sync`(756) 주석은 "UTC"이나 실제 ET로 fire | 시간대 라벨 |
| **P1** | 6 | sync-news-to-neo4j(08:45/10:45/...18:45)은 analyze-news-deep-batch(08:30...) 종료 가정 — 50 articles × Gemini 15 RPM ≈ 3-4분 + 분석 외 작업 시 15분 윈도우 부족 | 의존성 |
| **P1** | 7 | sec-sync-dirty-neo4j: `*/5` 분 매시간 24h 실행 → Neo4j queue가 5분 단위로 항상 점유, 다른 Neo4j 태스크의 큐잉 지연 가속 | Queue 몰림 |
| **P2** | 8 | 09:00 ET M-F: realtime-prices(*/5) + market-indices(*/5) + market-pulse(*/1) 동시 시작 → 1분에 6 FMP calls 동시 fire | FMP burst |
| **P2** | 9 | extract-news-relations(09:00 daily), chainsight-co-mentions(10:00 daily), chainsight-sync-{profiles,relations}-neo4j(12:00/12:30 daily) — 토/일에도 fire되지만 선행 뉴스/분류 태스크는 평일만 → 주말은 stale 데이터로 동작 | 의존성 |
| **P2** | 10 | refresh-market-pulse-cache `minute='*'` 9-16 M-F = 480 firings/day — task 자체는 cache 갱신이지만 cascade 호출 시 폭증 위험 (현재 안전, 모니터링 필요) | 부하 |
| **P2** | 11 | aggregate-weekly-prices(Sat 01:00) ↔ update-economic-calendar(daily 01:00) — 토요일 01:00에 동시 fire (영향 작음, DB-only 태스크) | 단순 충돌 |
| **P2** | 12 | check-pipeline-alerts(`*/30`) ↔ sec-sync-dirty(`*/5`) — 매시 :00, :30에 충돌하지만 default vs neo4j 큐 분리되어 영향 미미 | 충돌 (양호) |

---

## 1. Rate Limit 초과 구간 분석

### 1-A. FMP (Starter Plan: 300 calls/min, 10,000 calls/day)

#### 시간대별 FMP 의존 태스크 매핑

| ET 시각 | 태스크 | 추정 호출량 | 비고 |
|---------|--------|------------|------|
| 06:00 M-F | collect-daily-news-morning | ~50–100 | symbol-by-symbol news fetch |
| 06:15 M-F | collect-sp500-news-fmp-0615 | ~500 (orchestrator 분산) | S&P 500 전체 |
| 06:30 M-F | collect-category-news-high-morning | ~150 | category filter |
| 06:45 M-F | collect-general-news-fmp-morning | ~10 | endpoint 1개 |
| 07:00 M-F | collect-category-news-medium-morning | ~50 | medium priority |
| 07:30 M-F | sync-daily-market-movers + collect-category-news-low | ~30 + ~20 | |
| 07:45 M-F | collect-press-releases-fmp (max 50) | 50 | |
| 09–16 M-F | update-realtime-prices(`*/5`) + update-market-indices(`*/5`) + refresh-market-pulse-cache(`*/1`) | 12+12+60 = **84 calls/시간 baseline** | 매분 1-2 calls |
| 10:15 M-F | collect-sp500-news-fmp-1015 | ~500 | orchestrator |
| 12:30 M-F | collect-general-news-fmp-noon | ~10 | |
| 13:15 M-F | collect-sp500-news-fmp-1315 | ~500 | orchestrator |
| 15:15 M-F | collect-sp500-news-fmp-1515 | ~500 | orchestrator |
| 17:00 M-F | update-daily-prices + collect-category-news-high-evening | ~50 + ~150 | |
| 17:15 M-F | collect-sp500-news-fmp-1715 | ~500 | orchestrator |
| 17:45 M-F | collect-general-news-fmp-evening | ~10 | |
| 18:00 M-F | sync-sp500-eod-prices + thesis-update-readings + collect-market-news-evening | **~500 + ~150 + ~50 = 700+** | **P0 #1** 1분 피크 |
| 19:00 M-F | collect-ml-labels (lookback 2 days) | ~30 | DB 위주 |
| 20:00 M-F | sync-sp500-financials | 101 (5일 1회전) | 분당 분산 |

#### P0 #1: 18:00 ET 1분 피크

```
18:00:00 fire (동시):
  ├─ sync-sp500-eod-prices       → S&P 500 EOD bulk (provider 따라 1-500 calls)
  ├─ thesis-update-readings      → 지표 N개 × symbol M개 (>>100)
  ├─ collect-market-news-evening → ~50 calls
  └─ update-economic-indicators  → FRED (FMP 아님, 영향 분리)
  + neo4j-health-check (Neo4j only, FMP 미관여)
```

**위험**: 4개 태스크가 같은 워커풀에서 시작하면 첫 60초 내에 FMP `300 calls/min` 한도 도달 가능. `sync_sp500_eod_prices`가 batch fetch (예: `/stable/historical-price-eod/full?symbols=...`)로 100 symbols/call이면 5 calls로 끝나지만, symbol-by-symbol이면 500 calls — 코드 미확인이라 쪽수 확인 필요.

**Mitigation 가능 옵션** (제안만, 코드 수정 X):
- thesis-update-readings를 18:05로 5분 시프트
- collect-market-news-evening을 18:10으로 시프트
- sync-sp500-eod-prices 내부 batching 확인 (100 symbols/call 보장 시 안전)

#### P1 #4: 17:00–17:45 ET 누적 부하

```
17:00 update-daily-prices (M-F)              + collect-category-news-high-evening
17:15 collect-sp500-news-fmp-1715            (~500 calls 분산)
17:45 collect-general-news-fmp-evening       (~10 calls)
```

orchestrator가 5 calls/min로 분산한다면 17:15-17:45 동안 100 calls/min 추정. 다른 태스크 합산 시 200 calls/min 윈도우 — 한도 초과 직접 위험은 작으나 마진 적음.

#### P2 #8: 09:00 burst

09:00 fire 시점에 시장 시간 첫 분 동안:
- update-realtime-prices (1 call, FMP)
- update-market-indices (1 call, FMP)
- refresh-market-pulse-cache (~5 indices)
- aggregate-daily-sentiment (DB only)
- extract-news-relations (DB only)
- 09:00:00–09:00:59 합계 ~7 FMP calls/min — 안전.

#### 일일 FMP 합계 (Starter 10k/day 한도 vs 추정)

| 그룹 | 일일 추정 호출 |
|------|---------------|
| realtime-prices `*/5` × 8h × M-F | 96 calls/day |
| market-indices `*/5` × 8h × M-F | 96 |
| market-pulse-cache `*/1` × 8h × M-F | 480 |
| sp500-news-fmp × 5 (06:15/10:15/13:15/15:15/17:15) | 5 × ~500 = 2,500 |
| daily-news (morning+afternoon) | ~150 |
| market-news × 4 (08/12/15/18) | ~200 |
| category-news (high×3 + medium×2 + low×1) | ~600 |
| sp500-eod-prices | ~500 |
| sp500-financials (101/일) | 101 |
| general-news-fmp × 3 | ~30 |
| press-releases-fmp | ~50 |
| thesis-update-readings | ~500–1000 |
| daily-market-movers | ~30 |
| **합계 추정** | **5,300–6,300 calls/day** |

→ 10,000 cap 대비 53–63% 사용. 헤드룸 있음. **단 분당 한도(300/min)가 P0 #1 시점에 더 위험**.

### 1-B. Gemini Free Tier (15 RPM, 1,500 RPD)

#### Gemini 의존 태스크

| ET 시각 | 태스크 | 추정 RPM 사용 |
|---------|--------|--------------|
| 05:30 daily | enrich-relationship-keywords (limit=100) | 분당 분산 시 안전 |
| 08:00 daily | keyword-generation-pipeline (gainers) | ~10 calls 일시 |
| 08:30/10:30/12:30/14:30/16:30/18:30 M-F | analyze-news-deep-batch (max 50 articles) | **15 RPM 풀 사용 가능** |
| 16:45 daily | extract-daily-news-keywords | ~10 calls |
| 18:35 M-F | thesis-generate-summaries | symbol N개당 1 call |
| 1st of month 03:00 | refresh-korean-overviews-monthly (S&P 500) | 큰 batch, 분당 분산 필요 |

#### P0 #2: 18:30 ET 윈도우

```
18:30:00 fire (동시):
  ├─ analyze-news-deep-batch    → max 50 articles × Gemini call
  ├─ thesis-create-snapshots    → DB 위주 (LLM 미관여)
  ├─ run-eod-pipeline           → 14 시그널 벡터 연산 (LLM 미관여)
  └─ update-sp500-change-percent → DB only

18:35:00 fire:
  └─ thesis-generate-summaries  → Gemini 호출 (symbol 단위)
```

50 articles ÷ 15 RPM = **최소 3.3분 + per-call latency** = 4–5분 소요. 18:35에 thesis-generate-summaries fire 시 analyze가 아직 진행 중이면 RPM 풀 충돌. 코드 주석 (line 672 `audit P0 #15`)이 이전에 같은 위험을 감지했음.

**현재 mitigation**:
- `extract-daily-news-keywords`는 16:30 → 16:45로 분산 완료 (line 286 주석)
- 그러나 18:30/18:35 윈도우는 미해결

#### Gemini RPD 합계

| 태스크 | 일일 calls 추정 |
|--------|----------------|
| analyze-news-deep-batch × 6 (M-F) | 50 × 6 = 300 |
| extract-daily-news-keywords (daily) | ~10 |
| thesis-generate-summaries (M-F) | symbols × 1 |
| keyword-generation-pipeline (daily) | ~10 |
| enrich-relationship-keywords (daily, 100 limit) | ~100 |
| **합계 추정** | **~500–700/day** |

→ 1,500 RPD 한도 33–47% 사용. 헤드룸 있음. 분당 burst가 핵심 리스크.

### 1-C. Alpha Vantage (5 calls/min, 500 calls/day Free)

전수 검색 결과 beat_schedule 내 Alpha Vantage 직접 의존 태스크 **없음**. AV는 ad-hoc API_request 경로에서만 사용 — 스케줄러 부하 없음.

---

## 2. Queue 몰림 분석

### 2-A. neo4j queue (solo pool, 동시 1개 처리)

#### 항상 점유 중인 베이스라인

```
sec-sync-dirty-neo4j: schedule=*/5분 (24시간)
  → 일일 288 firings, 평균 5분당 1개 점유
```

만약 처리 시간이 60-120초라면 큐 시간대별 idle 비율 60-80%. 그러나 **다른 neo4j 태스크가 추가되면 직렬화로 지연**.

#### 큐 점유 충돌 매트릭스

| ET 시각 | Neo4j 태스크 (queue 'neo4j') | 비고 |
|---------|------------------------------|------|
| 04:00 daily | cleanup-expired-news-relationships | 단독 |
| 05:30 daily | enrich-relationship-keywords | 단독 |
| **08:45/10:45/12:45/14:45/16:45/18:45 M-F** | sync-news-to-neo4j | 매 2시간 |
| **12:00 daily** | neo4j-health-check + chainsight-sync-profiles-neo4j | **P0 #3 — 2개 동시** |
| 12:30 daily | chainsight-sync-relations-neo4j | 12:45 sync-news 직전 |
| Sun 04:30 | chainsight-neo4j-dirty-sync | 단독 |
| 매 5분 24h | sec-sync-dirty-neo4j | 항상 |
| 06:00/12:00/18:00/00:00 매 6h | neo4j-health-check | 매 6시간 fire |

#### P0 #3: 12:00 ET — Neo4j 큐 직렬화 burst

```
12:00:00 fire 시점:
  큐 동시 인입:
    1. neo4j-health-check          (rag_analysis)
    2. chainsight-sync-profiles-neo4j  (chainsight)
    3. sec-sync-dirty-neo4j        (sec_pipeline, 정기 5분)

12:30:00 fire:
    4. chainsight-sync-relations-neo4j (chainsight)
    5. sec-sync-dirty-neo4j (12:30 정기)

12:45:00 fire:
    6. sync-news-to-neo4j (M-F, max_articles=100)
```

solo pool에서 1, 2, 3은 직렬 실행. health-check가 30초, sync-profiles가 5분, sec-sync-dirty가 1분이면 12:00에 시작한 sync-relations-neo4j는 12:30+@에 fire 후 큐 대기 → 12:45 sync-news 도달 시 또 큐잉. **expires=3600 한도 내라 버려지진 않으나 지연**.

#### sec-sync-dirty-neo4j × neo4j-health-check 정기 충돌

```
00:00, 06:00, 12:00, 18:00 ET:
  - neo4j-health-check fire
  - sec-sync-dirty fire (정기 */5)
  → 동시 인입, 직렬화
```

매일 4회 발생 (영향: 분 단위 지연, 큰 문제 아님).

### 2-B. default queue 부하

#### 시장 시간 (09–16 ET) M-F 분당 베이스라인

| 분 단위 트리거 | 빈도 |
|---------------|------|
| refresh-market-pulse-cache | 매 분 (60/시간) |
| update-realtime-prices | 5분마다 (12/시간) |
| update-market-indices | 5분마다 (12/시간) |
| calculate-portfolio-values | 10분마다 (6/시간) |
| check-screener-alerts | 15분마다 (4/시간) |
| sec-sync-dirty-neo4j | 5분마다 (12/시간, 다른 큐) |
| check-pipeline-alerts | 30분마다 (2/시간) |

→ **default queue: 시장 시간 분당 ~1.6개 태스크 인입** (96/시간). prefork 워커 동시성 충분 시 문제 없음. macOS solo pool에선 직렬화로 백로그 가능.

### 2-C. 시간대별 ASCII 히트맵 (M-F 기준)

각 시각에 fire되는 distinct 태스크 수 (분 단위 분산 무시, hour 기준 집계):

```
시각  태스크수  히트맵                                         핵심 태스크
00    002       ##                                              sec-dirty(*/5)+pipeline-alerts(*/30)
01    002       ##                                              update-economic-calendar (daily 01:00)
02    001       #                                               sec-dirty (*/5)
03    001       #                                               sec-dirty (*/5)
04    002       ##                                              cleanup-expired-news-relations + sec-dirty
05    002       ##                                              enrich-relationship-keywords (05:30)
06    005       #####                                           daily-news + econ-indicators + sp500-news-0615 + cat-high + general-fmp
07    006       ######                                          heat-score + error-digest + cat-medium + market-movers + cat-low + press-rel
08    005       #####                                           market-news + keyword-pipeline(Gemini) + classify + analyze-deep(Gemini) + sync-news-neo4j
09    007       ####### *                                       sentiment + extract-news-rel + realtime+market+pulse + portfolio + screener-alerts (분 단위)
10    006       ######                                          chainsight-co-mention + sp500-news-1015 + classify + analyze-deep(Gemini) + sync-news-neo4j + 9-16 분 단위
11    005       #####                                           chainsight-relation-conf + 9-16 분 단위
12    009       ######### !! P0#3                               econ-ind + market-news + sec-seed-relations + chainsight-sync-profiles + neo4j-health + classify + general-fmp-noon + chainsight-sync-rel + analyze-deep(Gemini) + sync-news-neo4j
13    005       #####                                           seed-selection + cat-high-midday + sp500-news-1315 + 분 단위
14    006       ######                                          cat-medium-aft + classify + analyze-deep(Gemini) + sync-news-neo4j + daily-news-aft
15    005       #####                                           market-news-aft + sp500-news-1515 + 분 단위
16    007       #######                                         classify + analyze-deep(Gemini) + market-breadth + sector-heatmap + sync-news-neo4j + extract-news-keywords(Gemini) + 분 단위 종료
17    004       ####                                            cat-high-evening + update-daily-prices + sp500-news-1715 + general-fmp-evening
18    012       ############ !!!! P0#1 P0#2                     econ-ind + market-news + thesis-readings + sp500-eod + neo4j-health + classify + thesis-scores + analyze-deep(Gemini) + thesis-snapshots + run-eod-pipeline + update-change-pct + thesis-summaries(Gemini) + sync-news-neo4j
19    002       ##                                              ml-labels + backfill-signal-accuracy
20    001       #                                               sp500-financials
21    000
22    001       #                                               econ-ind 22:00
23    000
```

> `*` = burst 위험, `!!` / `!!!!` = P0 식별

**피크 분석**:
- **18시**: 12개 distinct 태스크 fire — 가장 위험한 시간대 (P0 #1 + P0 #2)
- **12시**: 9개 — Neo4j queue P0 #3
- **09시 / 16시**: 7개 — 시장 시간 분 단위 + 종료 burst

---

## 3. 시간대별 API 호출 히트맵 (FMP 기준, 분당 추정)

```
시각    분당 추정 calls  히트맵 (1당 ~10 calls)              임계
06:00   ~100            ##########                          orchestrator 분산 시 안전
06:15   ~50             #####
06:30   ~150            ###############  <warn>
06:45   ~10             #
07:00   ~50             #####
07:30   ~30             ###
07:45   ~50             #####
08:00   ~50             #####
09:00–16:00 (분 평균)    ~5–10  ##  baseline (realtime + indices + pulse)
10:15   ~100            ##########  <warn>
12:00   ~60             ######
12:30   ~10             #
13:15   ~100            ##########  <warn>
15:00   ~50             #####
15:15   ~100            ##########  <warn>
16:30   ~5              #
17:00   ~200            ####################  <warn-P1#4>
17:15   ~100            ##########
17:45   ~10             #
18:00   ~700            ##################################################################  <CRITICAL P0#1>
19:00   ~30             ###
20:00   ~20             ##
```

**FMP 300 calls/min 한도 위반 위험**:
- **18:00**: 700+ 추정 (sync-sp500-eod-prices의 batch 패턴에 강하게 의존). symbol-by-symbol fetch 시 5초 내 500 calls 가능 → 100% 한도 초과
- **17:00**: 200 (마진 33%)
- **06:30 / 10:15 / 13:15 / 15:15 / 17:15**: 100–150 (orchestrator 내부 분산되면 안전, 동기 fetch 시 위험)

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-A. 동시 fire (같은 분, 같은 day-of-week 매트릭스)

| 시각 | day_of_week | 태스크 | 충돌 종류 |
|------|------------|-------|----------|
| 01:00 ET | Sat | aggregate-weekly-prices + update-economic-calendar(daily) | DB only — 영향 작음 (P2 #11) |
| 04:00 ET | Sun | check-auto-deploy + cleanup-expired-news-relationships(daily) | 다른 큐 — 영향 없음 |
| 04:00 ET | Mon | scan-regulatory-relationships(weekly) + cleanup-expired-news-relationships(daily) | 다른 작업 — 영향 작음 |
| 06:00 ET | M-F | collect-daily-news-morning + update-economic-indicators (모두 데이터 수집) | API 다름 (FMP vs FRED) — 안전 |
| **12:00 ET** | daily | neo4j-health-check + chainsight-sync-profiles-neo4j + sec-seed-relations-to-chainsight + sec-sync-dirty(*/5 정기) + collect-market-news-noon + update-economic-indicators | **P0 #3 Neo4j queue 직렬화** |
| **18:00 ET** | M-F | sync-sp500-eod-prices + thesis-update-readings + collect-market-news-evening + update-economic-indicators + neo4j-health-check + classify-news-batch(18:15) | **P0 #1 FMP burst + 일반 burst** |
| 18:30 ET | M-F | thesis-create-snapshots + run-eod-pipeline + update-sp500-change-percent + analyze-news-deep-batch(Gemini) | **P0 #2 Gemini 충돌 위험 (18:35)** |
| 03:00 ET | Sun | train-importance-model | 단독 |
| 03:00 ET | 1st of month | refresh-korean-overviews-monthly (S&P 500 Gemini) | 큰 batch |

### 4-B. 선후행 의존성 (15-30분 윈도우 가정)

| 선행 → 후행 | 간격 | 위험 |
|------------|------|------|
| 18:00 thesis-update-readings → 18:15 thesis-calculate-scores | 15분 | 500+ symbol 지표 수집이 15분 내 완료 보장 안 됨 |
| 18:15 thesis-calculate-scores → 18:30 thesis-create-snapshots | 15분 | 스코어 계산은 DB 연산, 보통 안전 |
| 18:30 thesis-create-snapshots → 18:35 thesis-generate-summaries | **5분** | 너무 짧음 — snapshot이 5분 내 끝나도 Gemini 호출이 RPM 한도 의존 |
| 18:00 sync-sp500-eod-prices → 18:30 run-eod-pipeline | 30분 | EOD price sync가 30분 안에 완료되어야 함 (S&P 500 batch 패턴 의존) |
| 19:00 collect-ml-labels → train-importance-model (Sun 03:00) | 일주일 | 안전 (주간 배치) |
| 08:15 classify-news-batch → 08:30 analyze-news-deep-batch | 15분 | classify 빠름 (DB filter 위주), 보통 안전 |
| 08:30 analyze-news-deep-batch → 08:45 sync-news-to-neo4j | 15분 | **위험** — 50 articles × Gemini 15 RPM = 최소 3.3분 + per-call latency, 배치 끝나야 sync 의미 있음 (P1 #6) |
| 06:30 collect-category-news-high → 13:00 next collection | 6.5시간 | 안전 |
| Sat 02:00 chainsight-all-profiles → Sat 03:00 price-co-movement | 1시간 | 양호 |
| Sat 04:30 chainsight-aggregate-profiles → Sat 05:00 validation-weekly-batch | 30분 | aggregate가 30분 내 끝나면 안전 |
| 17:00 update-daily-prices → 18:00 sync-sp500-eod-prices | 1시간 | 두 태스크 모두 EOD 가격 — **중복 수집 가능성** (line 147 vs 555) |

### 4-C. 주말 day-of-week 불일치

다음 daily 태스크들은 매일 fire하지만 선행 데이터 (뉴스 수집 등)는 평일만 동작:

| 태스크 | 스케줄 | 의존 데이터 |
|-------|--------|------------|
| neo4j-health-check | 매 6h daily | (독립, 무관) |
| extract-daily-news-keywords | 16:45 daily | 평일만 수집된 뉴스 |
| extract-news-relations | 09:00 daily | 평일 수집 뉴스 |
| chainsight-co-mentions | 10:00 daily | M-F 분류된 뉴스 |
| chainsight-relation-confidence | 11:00 daily | co-mention 결과 |
| chainsight-sync-profiles-neo4j | 12:00 daily | (프로파일은 Sat 02:00 갱신) |
| chainsight-sync-relations-neo4j | 12:30 daily | (관계는 daily 갱신) |
| chainsight-heat-score-daily | 07:00 daily | 누적 데이터 |
| chainsight-seed-selection | 13:00 daily | heat-score 결과 |
| sec-seed-relations-to-chainsight | 12:00 daily | SEC pipeline 출력 |
| sec-sync-dirty-neo4j | */5 daily | dirty flag |
| update-economic-calendar | 01:00 daily | (FRED daily) |
| cleanup-expired-news-relationships | 04:00 daily | (정리 작업) |
| celery-error-digest | 07:00 daily | (정리/리포트) |
| keyword-generation-pipeline | 08:00 daily | mover 데이터 (평일만) |

→ **토/일에는 stale 데이터로 동작하거나 no-op으로 끝남**. 정상 동작이지만 메트릭 노이즈 가능 (P2 #9).

---

## 5. 시간대 라벨 일관성 (코드 주석 vs 실제)

`CELERY_TIMEZONE = 'America/New_York'` 기준에서 코드 주석이 표기한 시간대:

| line | 태스크 | 주석 시간대 | 실제 fire 시각 | 불일치 |
|------|--------|------------|---------------|--------|
| 143 | update-realtime-prices | (없음) | 9-16 ET | OK |
| 162 | sync-sp500-financials | "평일 20:00" | 20:00 ET | OK |
| 191 | update-economic-calendar | "매일 새벽 1시" | 01:00 ET | OK |
| 226 | sync-daily-market-movers | "매일 07:30 EST" | 07:30 ET | OK |
| 234 | keyword-generation-pipeline | "08:00 EST" | 08:00 ET | OK |
| 246 | collect-daily-news-morning | "06:00 EST" | 06:00 ET | OK |
| 289 | extract-daily-news-keywords | "16:45 EST = KST 06:45" | 16:45 ET | OK (KST 환산 정확) |
| 358 | collect-ml-labels | "19:00 EST" | 19:00 ET | OK |
| 374 | cleanup-expired-news-relationships | "04:00 EST" | 04:00 ET | OK |
| 491 | archive-old-articles | "02:30 EST" | 02:30 ET | OK |
| 503 | sync-etf-holdings | "월요일 06:00 EST" | Mon 06:00 ET | OK |
| 526 | calculate-market-breadth | "16:30 ET" | 16:30 ET | OK |
| 551 | sync-sp500-constituents | "매월 1일 02:00 ET" | 1st 02:00 ET | OK |
| 558 | sync-sp500-eod-prices | "매일 18:00 ET" | 18:00 ET | OK |
| 600 | sync-institutional-holdings | "매월 16일 04:00 EST" | 16th 04:00 ET | OK |
| 611 | scan-regulatory-relationships | "월요일 04:00 EST" | Mon 04:00 ET | OK |
| 654 | thesis-update-readings | "18:00 ET" | 18:00 ET | OK |
| 687 | chainsight-all-profiles | "매주 토요일 02:00 EST" | Sat 02:00 ET | OK |
| **741** | **chainsight-heat-score-daily** | **"매일 07:00 UTC"** | **07:00 ET** | **❌ P1 #5** |
| **748** | **chainsight-seed-selection** | **"매일 13:00 UTC"** | **13:00 ET** | **❌ P1 #5** |
| **755** | **chainsight-neo4j-dirty-sync** | **"매주 일요일 04:30 UTC"** | **Sun 04:30 ET** | **❌ P1 #5** |
| 769 | validation-weekly-batch | "매주 토요일 05:00 EST" | Sat 05:00 ET | OK |
| 786 | sec-seed-relations-to-chainsight | "매일 12:00 EST" | 12:00 ET | OK |

**P1 #5 영향**: 741/748/755 line 주석 신뢰 시 운영자가 "UTC 07:00 = ET 02:00 또는 03:00"로 오해 가능. 실제로는 ET 07:00 = UTC 12:00 또는 11:00 (DST에 따라). 주석을 "ET" 또는 "EST" 라벨로 통일하면 drift 해소.

---

## 6. Drift / 선언 vs 실행 위험

### 6-A. config dict ↔ DB PeriodicTask drift

`config/celery.py:118-134` 주석이 직접 명시:

> 이 dict는 런타임에 무시됨. config/settings.py의 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 설정 때문에 Celery Beat는 DB의 `django_celery_beat.PeriodicTask` 테이블을 진실의 소스로 사용한다.

**드리프트 가능성**:
- 본 감사는 dict 기준 — DB에 등록되지 않은 항목은 실제로 fire되지 않음
- 코드는 line 130-131에서 2026-04-24에 chainsight-heat-score-daily, sec-seed-relations-to-chainsight 두 항목이 누락 상태로 발견되어 수동 등록되었다고 기록
- 현재 86개 dict 항목이 모두 DB에 있는지 확인 필요 (코드 수정 금지이므로 본 보고서는 점검 필요 항목으로만 명시)

**검증 명령** (실행은 별도):
```python
from django_celery_beat.models import PeriodicTask
db_names = set(PeriodicTask.objects.values_list('name', flat=True))
config_names = set(app.conf.beat_schedule.keys())
print('Only in DB:', db_names - config_names)
print('Only in config:', config_names - db_names)
```

### 6-B. 함수명 vs task 등록명 불일치

```
'update-sp500-change-percent': {'task': 'update-sp500-change-percent', ...}
'chainsight-heat-score-daily':  {'task': 'chainsight-heat-score-daily', ...}
'chainsight-seed-selection':    {'task': 'chainsight-seed-selection', ...}
'chainsight-neo4j-dirty-sync':  {'task': 'chainsight-neo4j-dirty-sync', ...}
'sec-seed-relations-to-chainsight': {'task': 'sec-seed-relations-to-chainsight', ...}
```

5개 항목은 `app.task(name='...')`로 별칭 등록된 것으로 추정. 다른 항목들은 `'app.tasks.func_name'` 형식. **주의**: 별칭이 등록되지 않으면 NotRegistered 에러 발생. autodiscover 동작 확인 필요.

---

## 7. 권고사항 요약 (코드 수정 없이 다음 단계만)

본 보고서는 read-only이며 다음은 별도 PR/operations 작업으로 분리:

### P0 (즉시)
1. **18:00 ET FMP burst 검증** — `sync_sp500_eod_prices` 내부가 batch fetch (`/stable/historical-price-eod/full?symbols=AAPL,MSFT,...`)인지 symbol-by-symbol인지 확인. symbol-by-symbol이면 분당 한도 즉시 초과 — 운영 로그에서 429 에러 grep 권장.
2. **18:30+18:35 Gemini 직렬화 확인** — `analyze_news_deep` 실제 처리 시간 측정. 5분 초과 시 thesis-generate-summaries를 18:50으로 시프트 (DB PeriodicTask 직접 update).
3. **12:00 Neo4j queue 분산** — chainsight-sync-profiles-neo4j를 12:05로, sec-seed-relations-to-chainsight를 12:10으로 시프트 검토.

### P1 (이번 주)
4. **17:00 누적 모니터링** — FMP `/usage` 엔드포인트로 17:00–18:00 분당 호출량 측정, 200 calls/min 초과 시 sp500-news-1715 fire를 17:30로 시프트.
5. **시간대 라벨 통일** — line 741/748/755 주석을 "UTC" → "ET"로 정정 (코드 주석 수정 작업, 본 PR 범위 외).
6. **sync-news-to-neo4j 윈도우 확장** — `analyze-news-deep-batch` 평균 처리 시간 + 안전 마진으로 :45 → :50 시프트.
7. **sec-sync-dirty-neo4j 빈도 검토** — `*/5` → `*/10` 또는 `*/15`로 완화 가능 여부 확인 (dirty 처리 SLA 의존).

### P2 (월간 retro)
8. 09:00 burst (P2 #8) — 현재 안전, 모니터링 유지.
9. 주말 daily 태스크 (P2 #9) — no-op 시 메트릭 분리하거나 day_of_week='1-5'로 제한.
10. refresh-market-pulse-cache (P2 #10) — 매분 점유, cascade 호출 절대 금지 정책 명문화.
11. P2 #11/12 — 영향 미미, 이슈 추적기에만 기록.

### Drift 방어
12. Drift 점검 cron 추가 — 매주 `config dict vs PeriodicTask` diff 자동 검사 + Slack/메일 알림.

---

## 8. 부록 — 일일 태스크 fire 횟수 합계

| 태스크 분류 | 일일 firings (M-F) | 일일 firings (Sat) | 일일 firings (Sun) |
|------------|--------------------|--------------------|--------------------|
| 분 단위 (`*/N`) 9–16 M-F | 480 + 96 + 96 + 48 + 32 = 752 | 0 | 0 |
| sec-sync-dirty `*/5` 24h | 288 | 288 | 288 |
| check-pipeline-alerts `*/30` 24h | 48 | 48 | 48 |
| 시간 단위 fixed (M-F만) | ~52 | 0 | 0 |
| 시간 단위 fixed (daily) | ~22 | ~22 | ~22 |
| 주간 (Mon/Sat/Sun 한정) | ~0 | ~7 | ~7 |
| **합계 추정** | **~1,162** | **~365** | **~365** |

→ Beat scheduler가 일일 1,000개 이상의 firings를 처리. DatabaseScheduler 부하 — django_celery_beat 인덱스 (`PeriodicTask.last_run_at`) 점검 권장.

---

**감사 완료**: 2026-05-08
**대상 commit**: portfolio 브랜치 (config/celery.py 820 lines, beat_schedule 86개 항목)
**다음 감사 권장**: 1) FMP `/usage` 엔드포인트 실측 데이터 첨부 후 재감사, 2) DB PeriodicTask drift 점검 결과 포함, 3) Gemini RPM 실측 로그 기반 18:30 윈도우 재평가.
