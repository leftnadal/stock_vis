# Celery Beat Schedule 감사 보고서

- **대상 파일**: `config/celery.py` (794 lines, 68개 beat 엔트리)
- **감사일**: 2026-04-22
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (`config/settings.py:403`)
  - Django `TIME_ZONE = 'Asia/Seoul'` 과 **별도** — beat_schedule의 모든 `crontab()`은 **NY time** 기준
- **Rate Limit 기준값**: FMP 300/min (`config/settings.py:101`, Starter Plan), Gemini Free 15 RPM·1500 RPD, Alpha Vantage 5/min
- **감사 모드**: 읽기 전용. 코드 수정 없음.

---

## 요약 (Executive Summary)

| 구분 | 위험도 | 건수 | 비고 |
|------|-------|------|------|
| Rate Limit 잠재 초과 | HIGH | 3 | FMP 18:00·20:00·평일 매 5분 구간 |
| Gemini RPM 충돌 | MEDIUM | 2 | 16:30, 18:30 LLM 파이프라인 중첩 |
| Neo4j Queue 병목 | HIGH | 2 | 매 5분 `sec-sync-dirty-neo4j` + 장시간 sync 작업 경합 |
| 스케줄 의존성 race | HIGH | 3 | 18:00 readings vs eod-prices, 08:30→08:45 chain |
| 타임존 주석 불일치 | MEDIUM | 3 | `# UTC` 주석 3건이 실제론 NY time |
| 누락된 의존성 체인 | LOW | 1 | v3 뉴스 15분 간격 — LLM 실패 시 sync 스킵 메커니즘 없음 |

핵심 관찰: **스케줄 자체는 대체로 15분·30분 슬롯으로 깔끔히 분리되어 있으나**, 18:00 ~ 18:30 평일 EOD 구간과 매 5분 Neo4j sync가 **단일 실패 지점**이다. Starter Plan 300/min 기준으로 `sync-sp500-eod-prices`(500심볼) 한 건만으로 ~2분 소요되는데 같은 시각 `thesis-update-readings`가 동시에 FMP를 호출한다.

---

## 1. Rate Limit 초과 구간

### 1.1 FMP (Starter Plan: 300 calls/min)

#### HIGH — 평일 18:00 EDT (FMP 동시 버스트)

같은 분에 실행되는 FMP 의존 태스크:

| 태스크 | 라인 | 예상 심볼 수 | 호출량 |
|--------|------|-----------|--------|
| `sync-sp500-eod-prices` | 537-541 | 500 | 500 calls |
| `thesis-update-readings` | 633-637 | N (감시 지표 심볼) | 수십~수백 calls |
| `collect-market-news-evening` | 254-258 | 글로벌 뉴스 1회 | 1-5 calls |
| `update-economic-indicators` | 160-163 | FRED (별도 키) | - |
| `sec-sync-dirty-neo4j` (매 5분 18:00) | 752-756 | - | - |

**위험**:
- `sync-sp500-eod-prices` 단일로도 500/300 = 1.67분 필요 — **단일 태스크 내부에서 rate limit 처리가 없으면** 429 에러 또는 Starter 월 한도 소진.
- `thesis-update-readings`가 동시 시작하면 경합 심화.
- 실제 구현은 `stocks/tasks.py` 의 rate_limit 래퍼 여부 확인 필요 (본 감사는 beat 레벨만 분석).

**권장**:
- `sync-sp500-eod-prices` → 18:00, `thesis-update-readings` → 18:05 로 분리.
- 또는 `thesis-update-readings`가 **DB에 저장된 EOD를 읽는 구조**라면 18:05 이후로 뒤로 밀어야 race 해소.

---

#### HIGH — 평일 20:00 EDT (`sync-sp500-financials`)

| 태스크 | 라인 | 설명 |
|--------|------|------|
| `sync-sp500-financials` | 143-147 | 101 심볼/일 × 재무제표 다중 엔드포인트 |

**위험**:
- 101 심볼 × 재무제표 3~5 엔드포인트 (income, balance, cashflow, metrics, ratios) = **300~500 calls**.
- 300/min 한계에 근접. 재시도 발생 시 초과.
- 20:00에 이 태스크만 실행되는 것은 다행이나, FMP 분당 한도를 꽉 채우는 설계.

**권장**: 태스크 내부에서 `sleep(0.2)` 또는 토큰버킷 적용 확인 필요.

---

#### MEDIUM — 평일 09:00~16:55 EDT (시장 시간 매 5분)

```python
'update-realtime-prices':  crontab(minute='*/5', hour='9-16', day_of_week='1-5')  # line 126
'update-market-indices':   crontab(minute='*/5', hour='9-16', day_of_week='1-5')  # line 168
'refresh-market-pulse-cache': crontab(minute='*', hour='9-16', day_of_week='1-5') # line 180 — 매 1분!
'calculate-portfolio-values': crontab(minute='*/10', hour='9-16', day_of_week='1-5')  # line 152
```

**위험**:
- **매 5분 `:00, :05, :10, ...`** 에 `update-realtime-prices` + `update-market-indices` **동시 실행**.
- `refresh-market-pulse-cache`는 매 1분이지만 캐시 갱신이므로 API 호출 적을 수 있음 (Redis 중심).
- `update-realtime-prices`가 트래킹 심볼 N개를 돌면 500 심볼 watchlist인 경우 5분 안에 끝내기 어려움.

**권장**:
- `update-realtime-prices`는 S&P 500 전체가 아니라 "활성 Watchlist 심볼" 또는 "Mover 심볼"로 좁혀야 함 (`stocks.tasks.update_realtime_with_provider` 실제 대상 확인 필요).
- 시장 시간 중 `refresh-market-pulse-cache`가 매분 FMP를 찌르면 **8시간 × 60 = 480 calls/day 만으로도 한도 영향**. Redis-only 캐시 갱신이 아니라면 분리 필요.

---

#### MEDIUM — 평일 18:30 EDT (EOD 2차 버스트)

```python
'run-eod-pipeline':           hour=18, minute=30  # line 610
'thesis-create-snapshots':    hour=18, minute=30  # line 649
'update-sp500-change-percent': hour=18, minute=30 # line 546
'analyze-news-deep-batch':    hour=18, minute=30  # Gemini — 50 articles
'sec-sync-dirty-neo4j':       18:30 (매 5분 틱)
```

**위험**:
- `run-eod-pipeline` 는 14개 시그널 계산으로 FMP 추가 호출 가능.
- `update-sp500-change-percent` 는 DB-only면 안전. 태스크명만 보면 DB 계산이라 명시됨 (line 543 주석).
- Gemini 경로는 1.2절 참고.

---

### 1.2 Gemini (Free: 15 RPM / 1500 RPD)

#### MEDIUM — 평일 16:30 EDT (LLM 중첩)

| 태스크 | 라인 | LLM 사용 |
|--------|------|---------|
| `extract-daily-news-keywords` | 268-272 | Gemini (뉴스 키워드) |
| `analyze-news-deep-batch` (16:30) | 329-334 | Gemini 50 articles 심층 분석 |
| `calculate-market-breadth` (16:30) | 505-509 | — (계산만, LLM 없음) |
| `calculate-sector-heatmap` (16:35) | 512-516 | — |

**위험**:
- 두 Gemini 태스크가 **같은 분**에 시작. 50개 기사 + 키워드 추출 = 순간 요청이 15 RPM 한도 초과.
- Gemini SDK 자체 backoff이 있어도 실패 재시도 → **다음 LLM 태스크 슬롯(18:30)까지 밀림** 가능.

**권장**:
- `analyze-news-deep-batch` 의 16:30 슬롯만 16:40 으로 이동 (크론: `minute=30` → `minute=40`).

#### LOW — 일일 Gemini RPD 추산

| 태스크 | 일일 호출 (상한) |
|--------|----------------|
| `analyze-news-deep-batch` × 6회 × 50 articles | 300 |
| `extract-daily-news-keywords` | ~50 |
| `enrich-relationship-keywords` (100개) | 100 |
| `keyword-generation-pipeline` | ~30-50 |
| `chainsight-co-mentions` | ~50-100 |
| **합계** | **~530-630 RPD** |

→ 1500 RPD 여유 있음. 단, `refresh-korean-overviews-monthly` (매월 1일 03:00, line 622) 실행일에는 **500심볼×Gemini → 500 RPD 추가**. 이날은 1000 RPD 근접 → 함께 실행되는 일요일 ML 학습과 겹치면 한도 위험.

---

### 1.3 Alpha Vantage (5 calls/min)

beat_schedule 내 **Alpha Vantage 직접 의존 엔트리 없음**. `sub_claude_md/coding-rules.md` 언급에 따르면 FMP가 주 경로. `sync-sp500-financials` 가 AV 폴백을 쓰는지는 `stocks.tasks.sync_sp500_financials` 구현에서 확인 필요 — beat 레벨에서는 안전.

---

## 2. Queue 몰림 분석

### 2.1 Queue 분포

- **default queue**: 58개 엔트리
- **neo4j queue** (solo pool, 동시 1개): 10개 엔트리
  - `neo4j-health-check`, `sync-news-to-neo4j` (×6/일), `cleanup-expired-news-relationships`, `enrich-relationship-keywords`, `chainsight-sync-profiles-neo4j`, `chainsight-sync-relations-neo4j`, `chainsight-neo4j-dirty-sync`, `sec-sync-dirty-neo4j` (**매 5분**), `chainsight-all-profiles`의 동기화 부분

### 2.2 neo4j queue 병목 — HIGH

**핵심 충돌**: `sec-sync-dirty-neo4j` 가 **매 5분** 자동 실행 → **하루 288회** neo4j queue 점유.

충돌 시나리오:

| 시각 (평일) | neo4j queue 경합 태스크 | 심각도 |
|------------|----------------------|--------|
| 12:00 | `chainsight-sync-profiles-neo4j` + `sec-sync-dirty-neo4j` | HIGH |
| 12:30 | `chainsight-sync-relations-neo4j` + `sec-sync-dirty-neo4j` + (12:00 profiles sync가 미완료일 경우) | HIGH |
| 08:45, 10:45, 12:45, 14:45, 16:45, 18:45 | `sync-news-to-neo4j` + `sec-sync-dirty-neo4j` (같은 :45 5분 틱은 없음 — 여유 있음) | LOW |
| 04:00 | `cleanup-expired-news-relationships` + `sec-sync-dirty-neo4j` + (매주 토 `chainsight-stale-decay`, 매주 월 `scan-regulatory-relationships`, 매월 16일 `sync-institutional-holdings`) | HIGH 주말/월초 |
| 04:30 일요일 | `chainsight-neo4j-dirty-sync` + `chainsight-aggregate-profiles`(토) + `sec-sync-dirty-neo4j` + `train-lightgbm-model`(default queue, 무관) | MEDIUM |
| 05:30 | `enrich-relationship-keywords` (100개 LLM + neo4j write) + `sec-sync-dirty-neo4j` | HIGH |

**핵심 위험**:
1. `chainsight-sync-profiles-neo4j` (12:00) 이 **오래 걸리면** (수백 프로파일 동기화) 12:00 sec-sync-dirty-neo4j 가 큐에 누적. 30분 동안 6번의 sec-sync (12:05/10/15/20/25/30) + chainsight-sync-relations(12:30) 까지 쌓인다.
2. solo pool 은 동시 1개만 처리 → **큐 depth** 가 늘어도 처리는 직렬. 실시간성이 중요한 sec 이벤트가 30분 이상 지연될 수 있음.
3. 각 엔트리 `expires` 옵션:
   - `sec-sync-dirty-neo4j`: **240초 만료** (line 755) — 4분.
   - 즉, 앞선 `chainsight-sync-profiles-neo4j` 처리에 5분 이상 걸리면 **그 다음 틱의 sec-sync가 EXPIRED 로 폐기됨**. **작동 설계로 의도된 것이거나, 사일런트 데이터 누락 버그**.

**권장 확인사항**:
- `chainsight-sync-profiles-neo4j` 평균 실행 시간 측정 (`flower` 또는 `task_result` 테이블).
- 5분 초과면 `sec-sync-dirty-neo4j` expires 를 600초로 올리거나, 전용 queue 추가 분리.

---

### 2.3 default queue 경합

가장 많이 몰리는 시각:

- **평일 :15, :30, :45 (짝수 시간 8·10·12·14·16·18)**: 뉴스 파이프라인 3단계가 순차 실행. 각 단계 안에서 태스크 1개씩이므로 queue 경합은 낮음. 단, 내부 LLM 호출의 긴 꼬리가 문제.
- **일요일 03:00~04:30**: ML 학습 + Shadow 리포트 + Auto Deploy + LightGBM + `cleanup-task-results`(05:00) 직렬 의존 체인이 1시간 30분 예산 안에 들어가야 함.

---

## 3. 시간대별 ASCII 히트맵 (EDT/EST 기준, 평일)

범례: 각 시간대 버킷에 시작되는 **고유 태스크 수** (매분/매5분/매30분 태스크는 1회로 카운트)

```
시각  │ 밀도 (태스크 시작 수)                    │ 주요 태스크
──────┼─────────────────────────────────────────┼──────────────────────────────────
 00h  │ ·                                       │ (없음)
 01h  │ ▓                                   [1] │ update-economic-calendar(daily)
 02h  │ ·                                       │ 월1/토 한정
 03h  │ ·                                       │ 월1/일 한정 (ML 학습, 한글 개요)
 04h  │ ▓                                   [1] │ cleanup-expired-news-relationships
                                                   + 일 check-auto-deploy
                                                   + 월 scan-regulatory
                                                   + 월16 institutional-holdings
 05h  │ ▓                                   [1] │ enrich-relationship-keywords [Gemini+Neo4j]
                                                   + 토 validation, 일 cleanup-task-results
 06h  │ ▓▓▓▓                                [4] │ economic-indicators, daily-news-morning,
                                                   :15 fmp-sp500 [FMP], :30 category-high,
                                                   :45 general-news-fmp [FMP], 월1 sec-check, 월 etf-holdings
 07h  │ ▓▓▓▓▓                               [5] │ error-digest, heat-score, medium-morning,
                                                   :30 movers [FMP] + low, :45 press-releases [FMP]
 08h  │ ▓▓▓▓                                [4] │ keyword-gen [Gemini], market-news,
                                                   :15 classify, :30 analyze-deep [Gemini],
                                                   :45 sync-news→neo4j
 09h  │ ▓▓▓▓▓▓▓                             [7] │ ▲ 시장 개장. sentiment, extract-news-relations,
                                                   realtime(*5) [FMP], indices(*5) [FMP],
                                                   portfolio(*10), market-pulse(*1), screener-alerts(*15)
 10h  │ ▓▓▓▓▓▓▓▓▓                           [9] │ 9h baseline + fmp-sp500-1015 [FMP], classify:15,
                                                   analyze:30 [Gemini], sync→neo4j:45,
                                                   chainsight-co-mentions(daily)
 11h  │ ▓▓▓▓▓▓▓                             [7] │ 9h baseline + chainsight-relation-confidence
 12h  │ ▓▓▓▓▓▓▓▓▓▓▓                        [11] │ ▲ ▲ 피크. 9h baseline + economic-indicators,
                                                   market-news-noon, general-fmp:30 [FMP],
                                                   classify:15, analyze:30 [Gemini], sync-news:45,
                                                   chainsight-profiles-neo4j, :30 relations-neo4j,
                                                   sec-seed-relations
 13h  │ ▓▓▓▓▓▓▓▓                            [8] │ 9h baseline + category-high-midday,
                                                   fmp-sp500-1315 [FMP], seed-selection
 14h  │ ▓▓▓▓▓▓▓▓▓                           [9] │ 9h baseline + category-medium-afternoon,
                                                   :30 daily-news-afternoon, classify:15,
                                                   analyze:30 [Gemini], sync-news:45
 15h  │ ▓▓▓▓▓▓▓                             [7] │ 9h baseline + market-news-afternoon,
                                                   fmp-sp500-1515 [FMP]
 16h  │ ▓▓▓▓▓▓▓▓▓▓                         [10] │ ▲ 장 마감. market data last ticks,
                                                   :15 classify, :30 analyze [Gemini] +
                                                   extract-daily-keywords [Gemini] +
                                                   calculate-market-breadth,
                                                   :35 calculate-sector-heatmap, :45 sync-news
 17h  │ ▓▓▓▓                                [4] │ update-daily-prices [FMP], category-high-evening,
                                                   fmp-sp500-1715 [FMP], :45 general-fmp [FMP]
 18h  │ ▓▓▓▓▓▓▓▓                            [8] │ ▲ ▲ ▲ EOD 피크. economic-indicators,
                                                   market-news-evening, sync-sp500-eod [FMP 500심볼!],
                                                   thesis-update-readings [FMP],
                                                   :15 classify + thesis-scores,
                                                   :30 analyze [Gemini] + eod-pipeline +
                                                        thesis-snapshots + update-change-percent,
                                                   :45 sync-news→neo4j
 19h  │ ▓▓                                  [2] │ backfill-signal-accuracy, collect-ml-labels
 20h  │ ▓                                   [1] │ ▲ sync-sp500-financials [FMP 500+ calls]
 21h  │ ·                                       │ (없음)
 22h  │ ▓                                   [1] │ economic-indicators
 23h  │ ·                                       │ (없음)
```

### 히트맵 해석

**피크 시간대 (태스크 밀도 기준)**:
1. **12:00 EDT (11 tasks)** — 장중 중앙. market data loop + Chain Sight Neo4j sync + 뉴스 파이프라인 + FMP 뉴스. neo4j queue 가장 큰 부하.
2. **16:00 EDT (10 tasks)** — 장 마감. Gemini 2개 중첩.
3. **10·14h (9 tasks)** — 뉴스 파이프라인 + 시장 데이터.
4. **18:00 EDT (8 tasks)** — EOD 파이프라인. **FMP 500심볼 + thesis-readings 동시** = 감사 상 **최대 위험 지점**.

**저밀도 시간대 (여유)**:
- 00, 02, 03, 21, 23시 — 월별/주말 한정 태스크만 존재. 배치 추가 시 여기 활용 가능.

---

## 4. 스케줄 겹침 / 의존성 Race

### 4.1 HIGH — 평일 18:00 EOD Race

```
18:00 sync-sp500-eod-prices     (500심볼 FMP, 예상 ~2분)
18:00 thesis-update-readings    (FMP 호출 — 같은 심볼 세트를 다시 찌를 가능성)
18:15 thesis-calculate-scores   (readings 입력 필요)
18:30 thesis-create-snapshots   (scores 입력 필요)
18:30 run-eod-pipeline          (DailyPrice 입력 필요)
18:30 update-sp500-change-percent (DailyPrice 입력 필요)
```

**문제**:
- `thesis-update-readings` 와 `sync-sp500-eod-prices` 가 **같은 18:00 에 동시** 시작. 만약 thesis가 FMP realtime/historical 을 호출한다면 sync와 rate limit 경합.
- 만약 thesis가 **DailyPrice 테이블을 읽는 구조**라면 sync가 먼저 끝나야 하는데 same-minute 실행이므로 **thesis가 stale 데이터를 읽을 확률** 높음.
- 18:30 `run-eod-pipeline` 과 `update-sp500-change-percent` 도 DailyPrice 의존. 18:00 sync가 15~30분 내 완료해야 함.

**권장**:
- 18:00 → `sync-sp500-eod-prices`
- 18:05 → `thesis-update-readings`
- 18:20 → `run-eod-pipeline` 및 `update-sp500-change-percent`
- 18:25 → `thesis-calculate-scores`
- 18:35 → `thesis-create-snapshots`
(현재 코드는 모두 **정각/15분** 단위로 붙어 있어 안전 버퍼 없음)

### 4.2 HIGH — 뉴스 파이프라인 v3 의존 체인

```
[수집]  매 시간 뉴스 수집 (06·08·10·12·14·15·17·18시 분산)
         ↓
[분류]  :15  classify-news-batch       (매 2시간)
         ↓ 15분
[분석]  :30  analyze-news-deep         (매 2시간, Gemini 50 articles)
         ↓ 15분
[동기화] :45  sync-news-to-neo4j       (매 2시간, neo4j queue)
```

**문제**:
- 50 articles LLM 호출 @ 15 RPM ≈ 3.3분 최소. 16:30 슬롯의 `extract-daily-news-keywords`와 충돌 시 분석 완료가 16:45 를 넘길 수 있음.
- 16:45 `sync-news-to-neo4j` 는 **LLM 분석 결과를 DB에서 읽어 동기화** — 분석 미완료 시 **해당 배치 누락** (다음 18:45 로 밀림).
- 각 태스크 `expires=3600` 이므로 1시간 안에 처리되면 데이터 손실은 없지만 **실시간성 저하**.

**권장**:
- 16:30 Gemini 중첩 해소 (3.2절 참고).
- 또는 `sync-news-to-neo4j` 가 "아직 미처리 기사"를 다음 배치에서 자동 포함하도록 구현 (**beat가 아닌 태스크 로직**).

### 4.3 HIGH — 일요일 ML 체인 (03:00~04:30)

```
03:00 train-importance-model   (ML 학습, default queue)
03:30 generate-shadow-report   (train 결과 필요)
04:00 check-auto-deploy        (shadow 결과 필요)
04:15 generate-weekly-ml-report (auto-deploy 결과 필요)
04:20 monitor-ml-performance    (weekly-ml-report 직후)
04:30 train-lightgbm-model      (조건 체크 후 학습)
```

**문제**:
- `train-importance-model` 이 30분 내 끝나지 않으면 `generate-shadow-report` 는 **이전 주 가중치**를 기준으로 리포트 생성.
- Celery beat 는 **이전 태스크 완료 보장 없음** — crontab 절대 시각 기준.
- `expires`: train 7200초(2시간), shadow 3600초(1시간), auto-deploy 3600 — **expires 는 만료만 막고 의존성은 보장 안 함**.

**권장**:
- 태스크 내부에서 **선행 상태 플래그** 체크 (e.g., `ImportanceModel.latest.updated_at >= today`).
- 또는 `chain()` / `chord()` 로 하나의 워크플로 그룹핑 (beat 에서 3개를 별도 트리거하는 대신 `03:00` 하나만 트리거 + 내부 chain).

### 4.4 MEDIUM — Chain Sight Neo4j 동기화 간격

```
매일 12:00 chainsight-sync-profiles-neo4j   (neo4j queue)
매일 12:30 chainsight-sync-relations-neo4j  (neo4j queue)
```

**문제**:
- profiles sync가 30분 이상 걸리면 relations sync가 대기. 그 사이 `sec-sync-dirty-neo4j` 매 5분이 계속 큐에 쌓임.
- profiles 가 먼저 커밋되어야 relations 쪽 FK 가 유효할 수 있음 — 이 부분은 태스크 구현이 "profile 없어도 relation sync" 하는지 확인 필요.

### 4.5 LOW — `expires` 설계 재검토 필요

| 태스크 | expires | 실행 주기 | 위험 |
|--------|---------|---------|------|
| `sec-sync-dirty-neo4j` | 240s | 5분 | neo4j queue depth 폭증 시 sec 이벤트 유실 (2.2절) |
| `check-pipeline-alerts` | 1500s (25분) | 30분 | 정상 — 주석 일치 |
| `check-screener-alerts` | 600s (10분) | 15분 | 정상 |
| `refresh-market-pulse-cache` | **미지정** | 1분 | 누적 시 큐 부담 (60개/시간) |
| `update-realtime-prices` | **미지정** | 5분 | 장중 누적 시 부담 |

---

## 5. 타임존 주석 불일치 (MEDIUM)

`CELERY_TIMEZONE = 'America/New_York'` 이므로 모든 `crontab()`은 NY time 해석. 그러나 주석은 UTC로 표기된 엔트리 3개:

| 라인 | 엔트리 | 주석 | 실제 실행 (NY) |
|------|--------|------|---------------|
| 715-720 | `chainsight-heat-score-daily` | `# 매일 07:00 UTC` | **매일 07:00 NY** (03:00 UTC 동부표준시) |
| 722-727 | `chainsight-seed-selection` | `# 매일 13:00 UTC` | **매일 13:00 NY** (18:00 UTC 여름) |
| 729-734 | `chainsight-neo4j-dirty-sync` | `# 매주 일요일 04:30 UTC` | **매주 일 04:30 NY** |

**영향**:
- Heat Score 가 07:00 UTC 로 의도되었다면 NY 기준 **02:00** (EST) 또는 **03:00** (EDT) 이 맞음. 현재 07:00 NY 에 실행 중.
- 운영자가 UTC 기준으로 디버깅하면 **5시간** 차이로 혼동.

**권장**: 주석을 `# 매일 07:00 EST` 로 수정하거나, 의도가 UTC 라면 `crontab` 값을 변경 (하지만 본 감사는 코드 수정 없음 → 주석 수정만 제안).

---

## 6. 그 외 관찰

### 6.1 expires 미설정 태스크

`expires` 가 없는 엔트리 (누적 방지 필요):

- `update-realtime-prices` (126)
- `update-daily-prices` (130)
- `calculate-portfolio-values` (150)
- `update-economic-indicators` (160)
- `update-market-indices` (166)
- `update-economic-calendar` (172)
- `refresh-market-pulse-cache` (178)
- `cleanup-old-macro-data` (184)
- `celery-error-digest` (777)
- `cleanup-task-results` (784)

**위험**: 워커가 장시간 다운되면 누적 태스크가 한꺼번에 실행 → FMP 버스트 초과.

### 6.2 중복 이름 체크

모든 키 고유. 중복 없음.

### 6.3 평일/주말 필터 불일치

- **평일만 실행**이어야 할 일부 태스크가 `day_of_week` 미지정:
  - `extract-daily-news-keywords` (268-272): `day_of_week` 없음 → 주말에도 실행. 주말 뉴스량은 미국장 기준 미미하므로 Gemini RPD 만 소모.
  - `collect-sp500-news-fmp-*` 는 `day_of_week='1-5'` 설정되어 있음 (양호).
  - `extract-news-relations` (555-560): 평일 제한 없음 → 주말에도 실행.
  - `chainsight-co-mentions`, `chainsight-relation-confidence`, `chainsight-sync-profiles/relations-neo4j`, `chainsight-heat-score-daily`, `chainsight-seed-selection`: 모두 주말 실행.
- **의도된 것일 가능성 있음** (주말에도 관계 캐시 유효 유지). 다만 **FMP 키 비용** 관점에서는 주말 실행을 주중으로 제한하면 호출 절감.

### 6.4 월별 배치 오버랩 (매월 1일)

매월 1일 새벽 구간에 집중:

| 시각 | 태스크 |
|------|--------|
| 02:00 | `sync-sp500-constituents` |
| 02:30 | `archive-old-articles` |
| 03:00 | `refresh-korean-overviews-monthly` (Gemini 대량) |
| 04:30 | `build-patent-network` |
| 06:00 | `sec-check-new-filings` |

- `refresh-korean-overviews-monthly` 가 03:00 에 500 심볼 × Gemini → **~3시간 예상** (15 RPM 상한). 04:30 `build-patent-network` 까지 여유 1.5시간만 남음.
- 그 사이 04:00 에 기존 `cleanup-expired-news-relationships` + 매월 16일이 겹치는 날엔 `sync-institutional-holdings` 도.

**권장**: `refresh-korean-overviews-monthly` 를 **주 단위 분할** (매주 125 심볼씩) 하면 Gemini RPD 부하 분산.

---

## 7. Priority Actions (권장 순서)

### P0 — 18:00 EOD Race 해소
`thesis-update-readings` 를 18:00 → 18:05 로 이동 (코드 수정 필요, 본 감사는 권고만).

### P0 — sec-sync-dirty-neo4j expires 재검토
240s 만료는 `chainsight-sync-profiles-neo4j` 장시간 실행 시 데이터 유실 위험. 600s 로 상향 검토.

### P1 — 16:30 Gemini 중첩 분리
`analyze-news-deep-batch` 16:30 슬롯만 16:40 으로 이동.

### P1 — 월별 대량 LLM 분산
`refresh-korean-overviews-monthly` 주 단위 분할.

### P2 — 타임존 주석 정정
3건의 `# UTC` 주석을 `# EST/EDT` 로 수정.

### P2 — expires 누락 보완
`update-realtime-prices`, `update-market-indices`, `refresh-market-pulse-cache` 에 `expires` 추가.

### P2 — 주말 실행 필터
`chainsight-*` daily 태스크와 `extract-news-relations` 에 `day_of_week='1-5'` 추가 여부 검토.

---

## 8. 감사 범위 외 (추후 조사 필요)

본 감사는 `config/celery.py`의 **beat_schedule 선언부**만 분석했다. 아래는 태스크 구현 레벨 확인이 필요한 항목:

1. `update_realtime_with_provider` 실제 심볼 수 (전체 S&P 500 인지 Watchlist-only 인지).
2. `sync_sp500_financials` 내부 rate_limit 핸들링.
3. `thesis.tasks.eod_pipeline.update_indicator_readings` 가 FMP 직접 호출인지 DB 읽기인지.
4. `sync_profiles_to_neo4j` 평균 실행 시간 (flower/task_result 로그 필요).
5. `chainsight-heat-score-daily` / `chainsight-seed-selection` 의 UTC 주석이 실제 의도인지 (코드 작성자 확인 필요).

---

**보고서 끝.**
