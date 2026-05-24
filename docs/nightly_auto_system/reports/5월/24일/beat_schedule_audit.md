# Beat Schedule 감사 보고서

- 대상: `config/celery.py` `app.conf.beat_schedule`
- 총 76 항목 (선언 dict 기준)
- 감사일: 2026-05-24
- 모드: 읽기 전용. 코드 변경 없음.

> ⚠️ **선언 dict의 한계**: `CELERY_BEAT_SCHEDULER = django_celery_beat.schedulers:DatabaseScheduler`
> 가 활성화되어 있으므로, 실제 실행은 `django_celery_beat.PeriodicTask` (DB) 가 진실의 소스다.
> 본 감사는 dict 선언 기준이며, DB와의 drift는 별도 점검이 필요하다 (CLAUDE.md 줄 128~133).
>
> ⚠️ **timezone 모호성**: 주석에 EST/EDT/UTC가 혼재한다. crontab은 Django `TIME_ZONE` 기준
> 으로 평가되므로, 본 보고서는 **선언된 hour 값을 그대로 시간대 축**으로 사용한다.
> 운영 환경의 실제 wall-clock 시각은 settings.py의 `TIME_ZONE` 과 `CELERY_TIMEZONE` 으로
> 다시 확인해야 한다.

---

## 1. 시간대별 태스크 점화(fire) 히트맵 — 평일 기준

각 hour 칸의 숫자 = 해당 hour 동안 (선언상) 점화되는 **점화 횟수 합산** (firings/hour).
`*/5`, `*/10`, `*/15`, `*` 같은 분 단위 반복 태스크는 시간당 횟수를 합산.

```
 hour │ firings  │ load bar (■ = 5 firings)
──────┼──────────┼────────────────────────────────────────────────────────
  00  │    14    │ ■■■
  01  │    14    │ ■■■
  02  │    14    │ ■■■
  03  │    14    │ ■■■
  04  │    15    │ ■■■
  05  │    15    │ ■■■
  06  │    19    │ ■■■■
  07  │    20    │ ■■■■
  08  │    19    │ ■■■■
  09  │   110    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■   ★PEAK
  10  │   113    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  ★PEAK
  11  │   109    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■    ★PEAK
  12  │   117    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  ★PEAK
  13  │   111    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■   ★PEAK
  14  │   113    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  ★PEAK
  15  │   110    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■   ★PEAK
  16  │   114    │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  ★PEAK
  17  │    18    │ ■■■■
  18  │    26    │ ■■■■■                              ◆EOD/Thesis 폭주
  19  │    16    │ ■■■
  20  │    15    │ ■■■
  21  │    14    │ ■■■
  22  │    15    │ ■■■
  23  │    14    │ ■■■
```

> 모든 hour에 기본 14가 깔리는 이유:
> `sec-sync-dirty-neo4j` (`*/5`) 12회 + `check-pipeline-alerts` (`*/30`) 2회 = 14 firings/hour.

### 1.1 시장 시간(09~16시) 폭주의 정체

피크 시간대의 대부분은 다음 4개 태스크가 만든다:

| 태스크 | 점화 | 큐 | 영향 |
|-------|------|-----|------|
| `refresh-market-pulse-cache` | `*` → **60/h** | default | FMP fan-out 가능성 |
| `update-realtime-prices` | `*/5` → 12/h | default | **FMP** |
| `update-market-indices` | `*/5` → 12/h | default | **FMP** |
| `calculate-portfolio-values` | `*/10` → 6/h | default | (내부 계산, API 無) |
| `check-screener-alerts` | `*/15` → 4/h | default | 내부 |
| `sec-sync-dirty-neo4j` | `*/5` → 12/h | **neo4j** | Neo4j |
| `check-pipeline-alerts` | `*/30` → 2/h | default | 내부 |

위 합계 = 108/h. 나머지 ±5는 시간대별 단발 태스크.

### 1.2 분(minute) 격자에서의 동시 점화

시장 시간 매시 **:00 분**에 다음이 동시 점화된다:

```
:00 ─┬─ refresh-market-pulse-cache       (default)
     ├─ update-realtime-prices            (default, FMP)
     ├─ update-market-indices             (default, FMP)
     ├─ calculate-portfolio-values        (default)
     ├─ check-screener-alerts             (default)
     ├─ check-pipeline-alerts             (default)
     └─ sec-sync-dirty-neo4j              (neo4j)
```

매시 **:05, :10, :15, :20, ...** 등 5분 격자 시점에도 비슷한 패턴이 반복된다.
특히 :15 / :30 / :45 는 추가로 News v3 (classify / analyze-deep / sync-neo4j) 가 얹힌다.

---

## 2. Rate Limit 초과 위험 분석

### 2.1 FMP (Starter 300 calls/min, 10,000/일)

| 시점 | 동시 FMP 점화 태스크 | 추정 호출 수 |
|------|---------------------|------------|
| 시장시간 매분 :00 | `refresh-market-pulse-cache` | 1 task fan-out (지수 N개?) |
| 시장시간 매 5분 :00,:05,... | `update-realtime-prices` + `update-market-indices` | 종목 N개 × 2 |
| 평일 06:15 / 10:15 / 13:15 / 15:15 / 17:15 | `collect-sp500-news-fmp-*` (S&P 500 orchestrator) | **fan-out 위험** |
| 평일 06:45 / 12:30 / 17:45 | `collect-general-news-fmp-*` | 단일 batch |
| 평일 07:45 | `collect-press-releases-fmp` (max_symbols=50) | ~50 |
| 평일 18:00 | `sync-sp500-eod-prices` (S&P 500 = 503 종목) | **batch fan-out** |
| 평일 20:00 | `sync-sp500-financials` (101개/일) | ~101 |

**위험 평가**:

1. ⚠️ **HIGH — 시장 시간 매분 :00, :05, :10, :15, ... 5분 격자**
   `refresh-market-pulse-cache` (매 1분) + `update-realtime-prices` (매 5분) + `update-market-indices` (매 5분).
   세 태스크가 같은 :00 / :05 / ... 분에 모두 점화. 각각이 fan-out 형태로 N 호출하면
   1분 안에 300 calls 초과 가능. **각 태스크의 batch 크기 확인 필요**.

2. ⚠️ **HIGH — :15 분 격자 (06:15, 10:15, 13:15, 15:15, 17:15)**
   `collect-sp500-news-fmp-orchestrator` 가 S&P 500 전체를 chunk fan-out 한다면
   분당 300 호출 한계를 즉시 초과한다. orchestrator 내부 rate limiter 존재 여부가 관건.

3. ⚠️ **MEDIUM — 18:00 EOD batch + thesis-update-readings 동시 점화**
   `sync-sp500-eod-prices` (S&P 500 503종목) + `thesis-update-readings` 가 동시 시작.
   thesis가 동일 가격 데이터에 의존한다면 의존성 race (§4 참조).

### 2.2 Gemini Free (15 RPM, 1500 RPD)

LLM 호출이 추정되는 태스크:

| 태스크 | 빈도 | 추정 calls |
|--------|------|----------|
| `analyze-news-deep-batch` (max_articles=50) | 8/10/12/14/16/18시 :30 = **6회/일** | 6 × 50 = **300/일** |
| `classify-news-batch` | 6회/일 :15 | 분류 articles 수 의존 |
| `extract-daily-news-keywords` | 1회/일 16:45 | ? |
| `extract-news-relations` | 1회/일 09:00 | 24h 윈도 |
| `chainsight-co-mentions` | 1회/일 10:00 | 7일 윈도 |
| `enrich-relationship-keywords` | 1회/일 05:30 (limit=100) | **100/일** |
| `thesis-generate-summaries` | 1회/일 평일 18:35 | thesis 수 |
| `keyword-generation-pipeline` | 1회/일 08:00 | mover 종목 수 |
| `bulk_generate_korean_overviews` | 월 1회 03:00 day1 | bulk (수백) |

**위험 평가**:

1. ⚠️ **CRITICAL — :30 분 격자 (analyze-news-deep-batch)**
   매 2시간 :30에 50 articles 처리. 15 RPM 한도면 50 calls = **최소 3.3분 소요**.
   - **08:30** : 첫 점화는 단독 → OK
   - **16:30** : analyze-deep (50 calls) + **16:35 sector-heatmap (FMP)** 동시,
     **16:45 extract-daily-news-keywords (Gemini)** 가 15분 갭으로 따라옴.
     주석 line 286 에 이미 "15분 분산" 처치가 명시되어 있으나, 50 articles 가
     15 RPM 으로 처리되려면 3.3분 → 여유 11분 → **안전선 내**.
   - **18:30** : analyze-deep (50 calls) + thesis-create-snapshots + **18:35 thesis-generate-summaries (LLM)** 동시.
     thesis-generate-summaries 가 analyze-deep 끝나기 전 시작하면 Gemini RPM 충돌.
     **5분 갭은 50 calls 처리에 부족** (3.3분 < 5분 < 단발 50건 처리 시간 보장 안 됨).
     analyze-deep이 평균 5분 이상 걸리면 즉시 RPM 동시 사용 → **⚠️ MEDIUM 위험**.

2. ⚠️ **MEDIUM — 일일 RPD 누적**
   `analyze-news-deep` 300 + `enrich-relationship-keywords` 100 + 그 외 추정 50~100 ≈ **450~500/일**.
   1500 RPD 한도 내. 단, `chainsight-co-mentions` 와 `extract-news-relations` 의
   실제 호출 수가 윈도(7d/24h) 의 뉴스량에 비례 → 일평균 200건만 들어와도 한도 근접 가능.

3. ⚠️ **MEDIUM — 월 1회 03:00 day1 폭주 (bulk_generate_korean_overviews)**
   S&P 500 503종목을 한 번에 처리하면 503 calls × Gemini 15 RPM = **33.5분 직렬 + RPD 차감**.
   같은 03:00 day1 에 `sync-sp500-constituents`, `refresh-korean-overviews-monthly` 가 함께 점화.
   bulk_generate_korean_overviews 의 chunk 처리 / Sleep 로직 존재 여부 확인 필요.

### 2.3 Alpha Vantage (5 calls/min)

선언된 beat 태스크 중 **AV를 명시적으로 호출하는 항목 없음**.
`stocks.tasks.*` 가 Provider 라우팅을 통해 AV로 fall-back 하는 경우는 본 dict 만으로는 판단 불가.

→ 별도 감사: `stocks/providers/` 와 `API_request/alpha_vantage/` 의 호출 빈도가 beat 의
어느 시각에 트리거되는지 추적 필요. **현재 dict 한정으로는 AV 위험 없음**.

---

## 3. Queue 부하 분석

### 3.1 default queue

시장 시간(9~16시) 평균 ~110 firings/hour = **분당 평균 1.8 task**.
:00 / :05 분 격자에 6~7개 동시 점화 (§1.2).
default queue 워커 concurrency 가 4+ 이상이면 처리 가능, **1~2면 backlog 위험**.

### 3.2 neo4j queue (solo pool — 동시 1개)

**가장 큰 구조적 위험**. solo pool 제약상 한 번에 1개 task만 처리.
neo4j queue 라우팅 대상:

| 태스크 | 빈도/일 |
|--------|---------|
| `sec-sync-dirty-neo4j` | **288** (5분마다) |
| `sync-news-to-neo4j` | 6 (:45 매 2시간) |
| `neo4j-health-check` | 4 (6시간마다) |
| `enrich-relationship-keywords` | 1 |
| `chainsight-sync-profiles-neo4j` | 1 |
| `chainsight-sync-relations-neo4j` | 1 |
| `cleanup-expired-news-relationships` | 1 |
| `chainsight-neo4j-dirty-sync` | 1 (Sun) |

**일 총 점화**: ~303 / day → 평균 4.8분당 1건.
solo pool 평균 처리 시간이 < 4분이어야 backlog 없음.

**위험 시점**:

1. ⚠️ **HIGH — 5분마다 sec-sync-dirty-neo4j (expires=240초)**
   240초 expires 는 다음 점화(300초 후) 직전 만료. 실행이 240초 초과하면
   - 다음 firing 이 큐에 enqueue → solo pool 처리 → 이전 expired 작업도 큐에서 만료처리
   - 그러나 다음 :05 firing 이 시작되기 전 :04:00 부근에 만료되므로 **gap 60초** 보장
   - 처리시간이 5분 가까이 증가하면 점진적 backlog → **알림 필요**

2. ⚠️ **HIGH — 12:00 정각**
   - `sec-sync-dirty-neo4j` (:00, m=0)
   - `chainsight-sync-profiles-neo4j` (h=12, m=0)
   - `sec-seed-relations-to-chainsight` (h=12, m=0)
   세 개가 동시 enqueue. solo pool 직렬 처리 → 가장 늦은 작업은 앞 두 개가 끝날 때까지 대기.
   chainsight-sync-relations-neo4j (12:30) 까지 30분 안에 완료되어야 의존성 정상.

3. ⚠️ **MEDIUM — 매시 :45 (analyze-news-deep → sync-news-to-neo4j)**
   sync-news-to-neo4j (m=45) + sec-sync-dirty-neo4j (m=45) 매 2시간 충돌.
   sync-news 가 max_articles=100 의 LLM 결과를 Neo4j 에 적재 → 분량 따라 길어짐.

### 3.3 시간대별 queue 별 부하

```
hour │ default firings │ neo4j firings │ 비고
─────┼─────────────────┼───────────────┼──────────────────────────
 00  │       2         │      12       │
 01  │       2         │      12       │ +economic-calendar
 02  │       2-3       │      12       │ monthly: archive/sp500-cons
 03  │       2-7       │      12       │ Sun: train/shadow, day1: refresh-korean
 04  │       2-13      │      12-14    │ Sun: 6개 ML, +cleanup-news-rel (neo4j)
 05  │       2-3       │      12       │ +enrich-rel-kw (neo4j)
 06  │       6-8       │      12       │ economic/news/etf/sec-filings
 07  │       8         │      12       │ market-movers, category-low, press
 08  │       7         │      12-13    │ +keyword-gen, classify, +sync-news-neo
 09  │       96        │      12       │ ★시장 + aggregate-sentiment + extract-rel
 10  │       99        │      12-13    │ ★시장 + co-mention + classify
 11  │       95        │      12       │ ★시장 + relation-confidence
 12  │       99        │      14-15    │ ★시장 + neo4j 3개 동시 (12:00)
 13  │       97        │      12       │ ★시장 + seed-selection
 14  │       99        │      12-13    │ ★시장 + classify
 15  │       97        │      12       │ ★시장
 16  │      100        │      12-13    │ ★시장 + breadth/heatmap/extract-kw
 17  │       6         │      12       │ daily-prices, category-high
 18  │      14         │      12-13    │ ◆EOD/thesis 폭주 (12 firings @ :00-:35)
 19  │       4         │      12       │ ml-labels, backfill-signal
 20  │       3         │      12       │ sp500-financials
 21  │       2         │      12       │
 22  │       3         │      12       │ economic
 23  │       2         │      12       │
```

---

## 4. 스케줄 의존성 & 데이터 경합

### 4.1 EOD / Thesis 18:00~18:35 폭주

5분 간격으로 7개 태스크가 직선 의존:

```
18:00 ──┬── sync-sp500-eod-prices        (FMP, S&P 500 가격 적재)
        ├── update-economic-indicators   (FRED)
        ├── thesis-update-readings       (지표 데이터 수집)  ← EOD 가격 의존?
        └── collect-market-news-evening  (마켓 뉴스)

18:15 ──── thesis-calculate-scores       ← thesis-update-readings 완료 의존

18:30 ──┬── update-sp500-change-percent  ← sync-sp500-eod-prices 완료 의존
        ├── run-eod-pipeline             ← change-percent 완료 의존?
        ├── thesis-create-snapshots      ← thesis-calculate-scores 완료 의존
        ├── analyze-news-deep-batch      (Gemini)
        └── classify-news-batch(:15)/sync-news-to-neo4j(:45)

18:35 ──── thesis-generate-summaries     (Gemini) ← create-snapshots 의존
```

⚠️ **위험**:

1. **18:00 동시 점화**: `sync-sp500-eod-prices` (S&P 500 fan-out, 수분 소요) 와
   `thesis-update-readings` 가 동시 시작. thesis 가 오늘자 EOD 가격에 의존하면
   **15분 안에 sp500 EOD 가 끝나지 않으면 thesis-calculate-scores 가 stale 데이터로 계산**.
   현재 schedule 은 chain 의존성을 시간 간격(15분/15분/5분) 으로 추정하는데,
   실제 처리 시간 측정 없이 안전 가정. → **task chain (chord/group) 으로 직접 의존성 명시 권장**.

2. **18:30 동시 점화 5개**: default queue concurrency 가 부족하면 backlog.
   특히 `run-eod-pipeline` 과 `thesis-create-snapshots` 가 동일 시각.

3. **18:35 thesis-generate-summaries (Gemini)** 가 **18:30 analyze-news-deep-batch (Gemini, 50 calls)** 와
   5분만 떨어져 있음. analyze-deep 가 3.3분 초과 시 RPM 동시 사용 → **§2.2 위험 #1**.

### 4.2 Chain Sight 일일 파이프라인

```
09:00 ── extract-news-relations                          (Gemini, 24h)
10:00 ── chainsight-co-mentions                          (Gemini, 7d 윈도)
11:00 ── chainsight-relation-confidence                  ← co-mentions 의존
12:00 ── chainsight-sync-profiles-neo4j   (neo4j)
12:30 ── chainsight-sync-relations-neo4j  (neo4j)        ← profiles 의존
13:00 ── chainsight-seed-selection                       ← relations 의존
```

✅ 의존성 충분히 분리됨 (각 1시간 또는 30분 갭).

❌ **단**, 12:00 정각에 `sec-sync-dirty-neo4j` + `sec-seed-relations-to-chainsight` + `chainsight-sync-profiles-neo4j`
가 모두 neo4j queue 로 들어감 (§3.2 #2). 12:30 도 동일 — `chainsight-sync-relations-neo4j` + `sec-sync-dirty-neo4j`.

### 4.3 토요일 02:00~05:00 ChainSight 주간 배치

```
Sat 02:00 ── chainsight-all-profiles      (성장단계/자본/민감도/내부자, 7200s expires)
Sat 03:00 ── chainsight-price-co-movement (가격공동변동)
Sat 04:00 ── chainsight-stale-decay       (잠재성 감쇠, 600s expires!)
Sat 04:30 ── chainsight-aggregate-profiles
Sat 05:00 ── validation-weekly-batch      (1차 검증, 14400s expires)
```

⚠️ `chainsight-stale-decay` 의 expires=600초 가 짧다. all-profiles(02:00)/price-co-movement(03:00) 가
오버런하여 04:00 시점까지 default queue 가 막혀 있으면 stale-decay 는 **10분 만에 만료** → skip.

### 4.4 일요일 03:00~05:00 ML 학습 체인

```
Sun 03:00 ── train-importance-model
Sun 03:30 ── generate-shadow-report                ← train 의존
Sun 04:00 ── check-auto-deploy             + cleanup-expired-news-relationships(neo4j)
Sun 04:15 ── generate-weekly-ml-report
Sun 04:20 ── monitor-ml-performance
Sun 04:30 ── train-lightgbm-model                  + chainsight-neo4j-dirty-sync(neo4j)
Sun 05:00 ── cleanup-task-results
```

⚠️ 04:00~04:30 사이 5개 태스크가 5~15분 간격으로 직렬 의존. 각 단계가 빨라야 chain 유지.
`train-lightgbm-model` (expires=7200s) 와 `generate-weekly-ml-report` 가 동시 시작하면 CPU 경합.

### 4.5 ETC 의존성

- **08:00 `keyword-generation-pipeline`** ← 07:30 `sync-daily-market-movers` (30분 갭). movers fan-out 처리 시간 < 30분 가정.
- **16:45 `extract-daily-news-keywords`** ← 16:30 `analyze-news-deep-batch` (15분 갭). §2.2.
- **18:30 `run-eod-pipeline`** ← 18:00 `sync-sp500-eod-prices` + 18:30 `update-sp500-change-percent` (10분/0분).
  eod-pipeline 시작 시점에 change_percent 가 완성된 보장 없음 — **expires=3600 으로 흡수**.

---

## 5. 종합 결론 — 위험도 매트릭스

| # | 위험 | 영역 | 위험도 | 권장 조치 (요약, 코드 변경 X) |
|---|------|------|--------|-----------------------------|
| 1 | 시장시간 매 5분 격자에 `pulse + realtime + indices` 동시 FMP 호출 | FMP | HIGH | 각 태스크 fan-out 크기 측정 → 분당 호출 수 계산 |
| 2 | `collect-sp500-news-fmp-*` :15 격자 5회/일 S&P 500 fan-out | FMP | HIGH | orchestrator 의 chunk/throttle 정책 검증 |
| 3 | `sec-sync-dirty-neo4j` 5분마다 (288/일) + neo4j solo pool | Neo4j | HIGH | 평균 처리시간 모니터링 → 240s 초과 알림 |
| 4 | 12:00 / 12:30 neo4j queue 3-way 충돌 | Neo4j | HIGH | `chainsight-sync-profiles-neo4j` 12:05 로 분산 검토 |
| 5 | 18:30 analyze-deep ↔ 18:35 thesis-summaries Gemini RPM 충돌 | Gemini | MEDIUM | thesis-summaries 5분 → 10분 갭으로 분산 검토 |
| 6 | 18:00 sp500-eod ↔ thesis-update-readings 시간 의존성 묵시 | 의존성 | MEDIUM | task chain (chord) 으로 명시화 검토 |
| 7 | Sun 04:00~04:30 ML 5단계 직렬 의존 | 의존성 | MEDIUM | 각 단계 처리시간 SLA 측정 |
| 8 | Sat 04:00 `chainsight-stale-decay` expires=600s 짧음 | expires | MEDIUM | 02:00/03:00 batch 오버런 시 04:00 backlog → 10분 만료 |
| 9 | 월 1회 03:00 day1: `bulk_generate_korean_overviews` 503종목 | Gemini RPD | MEDIUM | 청크/sleep 로직 검증 |
| 10 | `refresh-market-pulse-cache` 매 1분 (60/h) fan-out 미상 | FMP | MEDIUM | 단일 호출인지 N-fan-out 인지 확인 |
| 11 | DB-dict drift (DatabaseScheduler 사용) | 운영 | MEDIUM | `PeriodicTask.objects.values_list('name', flat=True)` ↔ dict key diff 정기 점검 |
| 12 | Alpha Vantage 호출 위치 불투명 | AV | LOW | provider 라우팅 별도 추적 |

---

## 6. 보조 정보

- **`schedule` 키 등장 횟수**: `grep -c 'schedule' config/celery.py` → 77 (76 task + worker 모듈 1).
- **선언된 task 수**: 76 (Python `app.conf.beat_schedule` dict 의 entry 수).
- **neo4j queue 라우팅**: 16 task (`task_routes` 줄 37~55).
- **macOS solo pool 강제**: 줄 30~31 — 로컬 개발 시 prefork 미사용 → 부하 측정 시 환경 차이 인지 필요.

---

본 보고서는 **선언 dict 기반 정적 분석**이다. 실제 운영 시 확인이 필요한 항목:

1. `PeriodicTask` DB 와 dict 의 일치 여부 (CLAUDE.md 줄 128~133).
2. Django/Celery `TIME_ZONE` 설정 — 모든 hour 주석은 EST/EDT/UTC 가 섞여 있다.
3. 각 태스크의 **실제 처리시간 분포** — 본 보고서의 의존성 충돌은 "장기 실행 시" 발생.
4. default queue 워커 concurrency (`celery -A config worker -c N`) — N 이 작을수록 §3.1 위험 증가.
