# Beat Schedule Audit — 2026-05-06

> **Scope**: `config/celery.py` 의 `app.conf.beat_schedule` 전체 (약 60개 태스크)
> **Mode**: Read-only audit — 코드 수정 없음
> **Timezone**: `CELERY_TIMEZONE = 'America/New_York'` (`config/settings.py:413`) — 본 보고서의 모든 시각은 **NY 현지시각 (EST/EDT)** 기준
> **Note**: `config/celery.py:118-134` 주석에 따라 `beat_schedule` dict는 런타임에 무시되며, `django_celery_beat.PeriodicTask` DB 테이블이 진실의 소스. 본 감사는 dict가 DB와 동기화되어 있다고 가정. 마지막 drift 복구는 2026-04-24.

---

## 0. Executive Summary

| 위험 | 등급 | 핵심 |
|------|------|------|
| **18:00–18:45 EST 폭발 구간** | 🔴 P0 | thesis 3태스크 + sp500-eod (500종목) + run-eod-pipeline + market-news + analyze-deep(Gemini) + sync-news-to-neo4j 가 30분 내 동시 점화. FMP/Gemini 동시 부하 + neo4j queue 백로그. |
| **06:15 / 10:15 / 13:15 / 15:15 / 17:15 SP500 뉴스 폭주** | 🔴 P0 | `collect_sp500_news_fmp_orchestrator`가 chord로 503 심볼을 6배치 병렬 → 거의 동시에 503 FMP 호출. Starter 300/min 한도 초과 가능. |
| **02:00–05:30 EST (주말 새벽) 누적 부하** | 🟡 P1 | 일요일 04:00 EST 기준 11개 태스크 동시 실행 (ML 학습 + Chain Sight + 정리 작업). Sat 04:00 도 5개 동시. |
| **neo4j queue 솔로풀 + sec-sync-dirty 5분주기** | 🟡 P1 | `sec_pipeline.tasks.sync_dirty_to_neo4j` 5분마다 + `sync-news-to-neo4j` 짝수시 :45 + Chain Sight 동기화 → solo pool에서 10분 이상 밀림 가능. |
| **Gemini 짝수시 :15/:30 동시 점화** | 🟡 P1 | classify-news (:15) + analyze-deep (:30) + extract-daily-news-keywords (16:45) → 1분 내 50건+ Gemini 호출 시 15 RPM 위반. |
| **timezone 주석 혼선** | 🟢 P2 | 일부 주석은 "EST", 일부는 "ET", 일부는 "UTC" 표기. 실제 스케줄러는 `America/New_York` (DST 자동 적용). 주석과 실제 동작이 일치하지 않을 수 있음 (특히 chainsight-heat-score-daily 주석은 "07:00 UTC"이나 실행은 NY 07:00). |

---

## 1. Rate Limit 초과 구간 분석

### 1.1 FMP (Starter Plan, 300 calls/min)

#### 정기 호출 패턴

| 태스크 | 시각 (NY) | 추정 호출량 | 비고 |
|--------|----------|------------|------|
| `update-realtime-prices` | 평일 09–16시 매 5분 | 최대 10건/회 (포트폴리오 종목, `stocks/tasks.py:358` `[:10]`) | 안전 — 분당 ~2/min |
| `update-market-indices` | 평일 09–16시 매 5분 | ~5건 (지수 심볼) | 안전 |
| `sync-sp500-eod-prices` | 평일 18:00 | **500+ 호출** (chunk 단위) | 주의 — 단일 분에 폭주 시 한도 위협 |
| `sync-sp500-financials` | 평일 20:00 | 101 심볼 × 3–5 endpoint = **300–500 호출** | 5일 순환 — 분 단위 분산 여부 미확인 |
| `collect_sp500_news_fmp_orchestrator` | 평일 06:15/10:15/13:15/15:15/17:15 | **503 호출** (`news/tasks.py:961-980` chord 6배치 병렬) | 🔴 가장 위험 |
| `collect-press-releases-fmp` | 평일 07:45 | max 50 심볼 | 안전 |
| `collect-general-news-fmp-{morning,noon,evening}` | 평일 06:45/12:30/17:45 | 1–3 호출 (general endpoint) | 안전 |
| `thesis-update-readings` | 평일 18:00 | active thesis 지표 수만큼 (FMP/AV/FRED 혼합) | 변동 — 가설 증가 시 폭증 |

#### 🔴 Critical Window: SP500 뉴스 폭주

`collect_sp500_news_fmp_orchestrator` (`news/tasks.py:951-980`):

```
chord(
    collect_sp500_news_fmp_batch.s(batch) for batch in batches  # 6 batches × ~84 symbols
)(collect_sp500_news_fmp_done.si())
```

- **6개 배치가 동시 dispatch** → 워커 가용성에 따라 거의 동시 실행
- 각 배치는 84 심볼을 순차 호출 → 배치 1개당 84 calls/배치 처리시간
- 6배치 병렬 시 첫 1분 내 **6 × N 호출** (N = 분당 처리 가능량)
- 워커가 prefork로 8 concurrent라면 → 동시 8 호출 = 분당 **~480/min 가능 (300/min 초과)**
- 실제로는 평균화되지만 **첫 30초 spike** 시 429 응답 위험

#### 🔴 Critical Window: 17:00–18:30 EST

| 시각 | 태스크 | FMP 호출 |
|------|--------|----------|
| 17:00 | `update-daily-prices` (provider 갱신) | ~10 |
| 17:15 | `collect-sp500-news-fmp-1715` | **503** |
| 17:45 | `collect-general-news-fmp-evening` | 1–3 |
| 18:00 | `sync-sp500-eod-prices` | **500+** |
| 18:00 | `update-market-indices` (마지막 매 5분 슬롯) | ~5 |
| 18:00 | `thesis-update-readings` | 가설 수 의존 |
| 18:00 | `collect-market-news-evening` | ~5 |
| 18:30 | `run-eod-pipeline` | EOD 시그널 (캐시 의존) |

→ **17:15 폭주가 18:00 sync-sp500-eod-prices와 약 45분 간격** — 17:15 chord가 늦어지면 18:00 EOD와 겹치며 **분당 800+ FMP 호출** 가능.

### 1.2 Gemini Free Tier (15 RPM, 1500 RPD)

#### Gemini 사용 태스크 식별

| 태스크 | 시각 (NY) | 호출량 추정 | 비고 |
|--------|----------|------------|------|
| `keyword-generation-pipeline` | 매일 08:00 | mover 종목 수만큼 | gainers만 처리 |
| `analyze-news-deep-batch` | 평일 08:30/10:30/12:30/14:30/16:30/18:30 | **max 50/회** (4초 간격, ~15 RPM) | `news/tasks.py:511-544` |
| `classify-news-batch-morning` | 평일 08:15/10:15/12:15/14:15/16:15/18:15 | Engine A/B/C — 룰 기반 위주 (Gemini 사용 여부 미확인) | `news/tasks.py:469-501` |
| `extract-daily-news-keywords` | 매일 16:45 | 일일 누적 뉴스 (수십~수백) | `config/celery.py:284-291` 주석에 명시: "16:30 analyze-deep와 Gemini 동시 호출 충돌 회피" |
| `chainsight-co-mentions` | 매일 10:00 | 7일치 뉴스 |
| `enrich-relationship-keywords` | 매일 05:30 | limit=100 |
| `bulk_generate_korean_overviews` | 매월 1일 03:00 | S&P 500 전종목 |

#### 🟡 Risk: 짝수시 :15→:30 cascade

```
hh:15  classify-news-batch        (룰 기반 + 일부 Gemini fallback?)
hh:30  analyze-news-deep          (50건, 4초 간격 → 약 3.3분 소요)
```

`analyze_news_deep`는 자체적으로 4초 간격을 두지만:
- 16:30 analyze-deep (50건) + 16:45 extract-daily-news-keywords (수백건) → 16:30~16:50 구간에서 **Gemini 누적 호출 100+** 가능
- 일일 누적: 6 × 50 = 300 (analyze-deep) + extract-keywords + co-mentions + enrich + others → **1500 RPD에 근접**

#### 🟡 Risk: 03:00–04:30 일요일 LLM 학습 cascade

```
Sun 03:00  train-importance-model
Sun 03:30  generate-shadow-report
Sun 04:00  check-auto-deploy
Sun 04:15  generate-weekly-ml-report
Sun 04:20  monitor-ml-performance
Sun 04:30  train-lightgbm-model
```

ML 학습 자체는 Gemini 미사용으로 보이나, 동시간대 `enrich-relationship-keywords` (05:30, daily) + `chainsight-aggregate-profiles` (Sat 04:30) 와 자원 경합.

### 1.3 Alpha Vantage (5 calls/min)

`config/celery.py` 의 beat_schedule에서 **AV 직접 사용 태스크는 식별되지 않음**.
- `update_realtime_with_provider`는 provider 추상화 — fallback에 AV 포함 가능성 있으나 코드상 12초 대기 패턴 확인 (`stocks/tasks.py:379` `time.sleep(1)`은 AV용이 아님)
- thesis 지표 fetch에서 일부 AV 호출 가능 (`thesis/tasks/eod_pipeline.py:202` `fetch_indicator_value`)
- **결론**: Beat 스케줄 자체는 AV 한도 위협 없음. 단, thesis 지표가 AV 의존 시 18:00 윈도에 추가 부하 가능 — 별도 audit 필요.

---

## 2. Queue 몰림 분석

### 2.1 Queue 분리 정책 (`config/celery.py:37-55`)

- **default queue**: 대부분의 태스크 (prefork 또는 macOS solo)
- **neo4j queue**: Neo4j 동기화 전용 (`--pool=solo`, **동시 1개만 처리**)

### 2.2 neo4j queue 부하

| 태스크 | 주기 | 1회 처리량 |
|--------|------|------------|
| `sec-sync-dirty-neo4j` | **매 5분** (24/7) | dirty evidence 일괄 |
| `neo4j-health-check` | 6시간마다 (00/06/12/18) | 짧음 |
| `sync-news-to-neo4j` | 평일 짝수시 :45 (08–18) | max 100 articles |
| `cleanup-expired-news-relationships` | 매일 04:00 | 정리 작업 |
| `enrich-relationship-keywords` | 매일 05:30 | limit 100 (Gemini + Neo4j) |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | 프로파일 일괄 |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | 관계 일괄 |
| `chainsight-neo4j-dirty-sync` | 일요일 04:30 | 주간 dirty |

#### 🟡 12:00–12:45 EST 폭주

```
12:00  neo4j-health-check
12:00  chainsight-sync-profiles-neo4j   (대용량)
12:30  chainsight-sync-relations-neo4j  (대용량)
12:45  sync-news-to-neo4j                (max 100)
```

solo pool 1 concurrent → 위 4개가 **순차 처리**. 만약 sync-profiles가 30분 이상 걸리면 sync-relations가 12:30 시작 못함. 추가로 `sec-sync-dirty-neo4j`가 5분마다 큐에 쌓임 → **12:00–13:00 사이 15+ 태스크 대기 가능**.

#### 🟡 18:00 EST 짧은 윈도

```
18:00  neo4j-health-check
18:45  sync-news-to-neo4j (max 100, 18:30 analyze-deep 산출물)
```

18:45 sync-news는 18:30 analyze-deep 결과를 Neo4j에 반영. 18:30 analyze-deep가 평균 5–10분 → 18:45에 분석된 뉴스 일부만 반영, 나머지는 다음 cycle (20:45)까지 누락. **단, 19:00 이후 짝수시 cron은 평일에만 실행** → 18:45가 마지막 sync. 누락된 분석 데이터는 다음 평일 08:45까지 미반영 가능.

### 2.3 default queue 부하

`refresh-market-pulse-cache` 가 9–16시 매 분 (8 × 60 = 480/일) — 짧지만 default 큐를 점유. macOS solo pool에서는 직렬 처리되어 다른 태스크 지연 가능.

---

## 3. 시간대별 ASCII 히트맵

### 3.1 평일 (Mon–Fri) 히트맵

각 셀 = 해당 시각(NY) 정각 ~ 다음 시각 사이에 시작되는 **명시적 beat 태스크 개수**
(매 5분/매분 등 고주기 recurring은 별도 표시)

```
Hour ║ Tasks (count) ║ Bar (■=1)
═════╬═══════════════╬══════════════════════════════════════════════════
 00  ║  0            ║
 01  ║  1            ║ ■                            update-economic-calendar
 02  ║  0            ║
 03  ║  0            ║
 04  ║  1            ║ ■                            cleanup-expired-news-relationships (Neo4j)
 05  ║  1            ║ ■                            enrich-relationship-keywords (Gemini+Neo4j)
 06  ║  7            ║ ■■■■■■■                      🟡 morning surge
 07  ║  6            ║ ■■■■■■                       🟡
 08  ║  5            ║ ■■■■■                        Gemini cascade start
 09  ║  2            ║ ■■                           market open + sentiment
 10  ║  5            ║ ■■■■■                        Gemini + Neo4j + FMP-1015 🟡
 11  ║  1            ║ ■                            chainsight-relation-confidence
 12  ║  9            ║ ■■■■■■■■■                    🔴 NOON SURGE
 13  ║  3            ║ ■■■                          + FMP SP500 news 1315
 14  ║  5            ║ ■■■■■                        Gemini cascade
 15  ║  2            ║ ■■                           + FMP SP500 news 1515
 16  ║  6            ║ ■■■■■■                       breadth+heatmap+keywords+Gemini
 17  ║  4            ║ ■■■■                         + FMP SP500 news 1715 🔴
 18  ║ 12            ║ ■■■■■■■■■■■■                 🔴🔴 PEAK — EOD pipeline + thesis + Gemini + Neo4j
 19  ║  2            ║ ■■                           ml-labels + signal-accuracy
 20  ║  1            ║ ■                            sp500-financials (FMP heavy)
 21  ║  0            ║
 22  ║  1            ║ ■                            update-economic-indicators
 23  ║  0            ║
═════╩═══════════════╩══════════════════════════════════════════════════
+ recurring (always-on):
  - sec-sync-dirty-neo4j         every 5 min,  24/7    → 288/day
  - check-pipeline-alerts        every 30 min, 24/7    → 48/day
  - neo4j-health-check           every 6 h,    24/7    → 4/day
+ recurring (market hours, 09-16 weekday):
  - update-realtime-prices       every 5 min          → 96/day
  - update-market-indices        every 5 min          → 96/day
  - calculate-portfolio-values   every 10 min         → 48/day
  - refresh-market-pulse-cache   every minute         → 480/day
  - check-screener-alerts        every 15 min         → 32/day
```

### 3.2 주말 추가 부하 (Sat/Sun 새벽)

```
        Sat                                Sun
─────── ─────────────────────────────────  ──────────────────────────────────
 01:00   aggregate-weekly-prices            -
 02:00   chainsight-all-profiles            -
 03:00   chainsight-price-co-movement       train-importance-model
 03:30   -                                  generate-shadow-report
 04:00   chainsight-stale-decay             check-auto-deploy
 04:15   -                                  generate-weekly-ml-report
 04:20   -                                  monitor-ml-performance
 04:30   chainsight-aggregate-profiles      train-lightgbm-model
                                            chainsight-neo4j-dirty-sync (Neo4j)
 05:00   validation-weekly-batch            cleanup-task-results
 05:30   enrich-relationship-keywords       enrich-relationship-keywords
─────── ─────────────────────────────────  ──────────────────────────────────
                  Sat 04:00–04:30 = 3 ▢▢▢       Sun 04:00–04:30 = 5 ▣▣▣▣▣  🟡
```

### 3.3 월간 1회성 (1st of month, 03:00–06:00 EST)

```
 02:00  sync-sp500-constituents       (FMP)
 02:30  archive-old-articles          (DB heavy)
 03:00  refresh-korean-overviews      (Gemini, S&P 500 전종목 — 잠재적 RPD 소진)
 03:00  sync-supply-chain-batch       (15일자, S&P 500 상위 100)
 04:00  sync-institutional-holdings   (16일자)
 04:30  build-patent-network          (1일자)
 06:00  sec-check-new-filings         (1일자)
```

→ 매월 1일 03:00에 `refresh-korean-overviews-monthly` 가 S&P 500 전종목에 대해 Gemini 호출 → **Free Tier 1500 RPD 단일 태스크로 소진 가능**. 다른 LLM 태스크와 충돌 시 다음날까지 lockout.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4.1 명시적 Cascade (의도된 순차)

```
06:00 collect-daily-news-morning
   ↓ (2시간 15분 후)
08:15 classify-news-batch         ← morning 뉴스 분류
   ↓ (15분 후)
08:30 analyze-news-deep           ← Tier A/B/C 심층 분석
   ↓ (15분 후)
08:45 sync-news-to-neo4j          ← Neo4j 이벤트 노드 적재

18:00 thesis-update-readings      ← FMP 등에서 지표 fetch
   ↓ (15분 후)
18:15 thesis-calculate-scores     ← 점수 계산 (DB read only)
   ↓ (15분 후)
18:30 thesis-create-snapshots     ← 스냅샷 + 알림

18:00 sync-sp500-eod-prices       ← 500종목 EOD
   ↓ (30분 후)
18:30 update-sp500-change-percent ← DB 계산만 (의존)
18:30 run-eod-pipeline            ← EOD 시그널 14개 (의존)
```

### 4.2 ⚠️ 의존성 위반 가능성

#### 🔴 18:00 sync-sp500-eod-prices → 18:30 run-eod-pipeline
- `sync-sp500-eod-prices` soft_time_limit = **1800초 (30분)** (`stocks/tasks.py:421`)
- 정확히 30분 후 `run-eod-pipeline`이 시작 → **타임리미트 정확히 동등**
- FMP 부하 또는 네트워크 지연 시 EOD pipeline이 **stale price**로 동작
- 마진: 0분 — **위험한 설계**

#### 🟡 18:00 thesis-update-readings → 18:15 thesis-calculate-scores
- thesis-update-readings 은 active thesis 수에 따라 시간 변동
- 가설 100개 × 지표 5개 × FMP 호출 1초 = 500초 (8분) — 15분 마진 안에 들어옴
- 그러나 가설 증가 시 마진 소진 가능

#### 🟡 08:15 classify → 08:30 analyze
- classify 처리시간 = 4시간 윈도 분류 (수백 건)
- analyze는 classify 결과 (importance_score 상위 15%) 의존
- 15분 마진 — classify가 길어지면 analyze가 미분류 데이터 처리

#### 🟡 chainsight 12:00 → 12:30 → ... 의존성
- `chainsight-sync-profiles-neo4j` (12:00) → `chainsight-sync-relations-neo4j` (12:30) → `chainsight-seed-selection` (13:00)
- solo pool에서 sync-profiles + sec-sync-dirty (5분 cron) 누적 시 12:30 출발 지연 가능
- seed-selection이 stale relation으로 동작 가능

### 4.3 동시 실행 데이터 경합

#### 🟡 18:00 EST 동시 실행 (NY 6PM)
같은 분에 다음 5개가 점화:
1. `sync-sp500-eod-prices` (FMP, S&P 500 daily price write)
2. `thesis-update-readings` (FMP, IndicatorReading write)
3. `update-economic-indicators` (FRED)
4. `collect-market-news-evening` (FMP)
5. `update-market-indices` (last 5min slot at hour=16, 17 not 18 — 사실상 17:55)

→ FMP 분당 한도 + DB 쓰기 동시성. `Stock` 테이블 동시 락 가능성 (sync-sp500-eod-prices는 DailyPrice, thesis-update-readings는 IndicatorReading — 다른 테이블이라 직접 경합 없음).

#### 🟡 매 정각 (00, 06, 12, 18) Neo4j 헬스체크 + 다른 Neo4j 작업
- 12:00에 `neo4j-health-check` + `chainsight-sync-profiles-neo4j` 동시 큐인 → solo pool 직렬 처리 → health-check 자체는 짧지만 큐 헤드 점유

---

## 5. 권장 조치 (우선순위 순)

### P0 — 즉시 검토

1. **17:15 sp500-news chord 처리량 측정**
   - 6배치 병렬 dispatch 시 첫 1분 FMP 호출량 로깅 추가
   - 한도 초과 시 chord → chain 변경 또는 배치당 sleep 추가

2. **18:00 sync-sp500-eod-prices ↔ 18:30 run-eod-pipeline 마진 확보**
   - sync-sp500-eod-prices를 17:50으로 앞당기고 run-eod-pipeline을 18:45로 미루기
   - 또는 chord 종료 시그널로 run-eod-pipeline 트리거 (시간 기반 → 이벤트 기반)

3. **18:00 ~ 18:45 부하 분산**
   - thesis-update-readings를 17:30 또는 19:00으로 이동 (FMP 충돌 회피)
   - sync-news-to-neo4j (18:45) 누락 처리: 19:30 보강 cron 추가 검토

### P1 — 본 배포 전

4. **neo4j queue 우선순위 도입**
   - sec-sync-dirty-neo4j (5분주기) 가 long-running chainsight sync를 막지 않도록 priority queue 분리
   - 또는 chainsight sync 시간을 sec-sync 사이로 정렬 (12:02, 12:32 등)

5. **Gemini RPD 모니터링**
   - 매월 1일 03:00 `refresh-korean-overviews-monthly` + 04:30 ML 학습 + 05:30 enrich + 평일 6 cycle analyze-deep 누적량 일별 트래킹
   - 1500 RPD 도달 시 다음날 00:00 reset까지 lockout — 알림 필요

6. **timezone 주석 정리**
   - 모든 주석을 "EST/EDT" → "NY local (DST 반영)"로 통일
   - "UTC"로 잘못 표기된 항목 (chainsight-heat-score-daily, seed-selection 등) 수정

### P2 — 장기

7. **DB schedule ↔ config dict drift 자동 감지**
   - CI에서 `set(PeriodicTask.objects.values_list('name')) vs config dict.keys()` diff 검사
   - drift 발견 시 빌드 실패

8. **태스크별 평균/p95 실행시간 dashboard**
   - 의존 cascade의 마진 검증 데이터화 (현재는 추정만 가능)

---

## 6. 부록 — 태스크 목록 요약 (총 60개)

| 분류 | 개수 | 비고 |
|------|------|------|
| Stocks | 5 | realtime, daily, weekly, financials, eod, change-percent |
| Macro | 5 | indicators, indices, calendar, pulse-cache, cleanup |
| RAG / Neo4j | 1 | health-check (semantic-cache 폐기됨) |
| Market Movers + Keywords | 2 | sync-movers, keyword-pipeline |
| News 수집 | 12 | daily(2), market(4), category(6) + extract-keywords |
| News Intelligence v3 | 7 | classify, analyze-deep, sync-neo4j, ml-labels, cleanup, train, shadow-report, auto-deploy, weekly-report, monitor, lightgbm, alerts |
| FMP S&P 500 News | 9 | sp500-news×5 + press-releases + general×3 |
| Archive / S&P 500 sync | 4 | archive, etf-holdings, sp500-constituents, sp500-eod |
| Screener | 3 | breadth, sector-heatmap, alerts |
| Supply Chain / Patent / Regulatory / Institutional | 4 | sync-supply, scan-regulatory, build-patent, sync-institutional |
| EOD Dashboard | 2 | run-eod-pipeline, backfill-signal-accuracy |
| Korean Overviews | 1 | bulk_generate (월 1회) |
| Thesis EOD | 3 | readings, scores, snapshots |
| Chain Sight v2 | 10 | profiles, co-mentions, price-comovement, relation-confidence, stale-decay, aggregate-profiles, sync-profiles-neo4j, sync-relations-neo4j, heat-score, seed-selection, neo4j-dirty-sync |
| Validation | 1 | weekly-batch |
| SEC Pipeline | 3 | sync-dirty (5분), seed-relations, check-new-filings |
| Celery 운영 | 2 | error-digest, cleanup-task-results |

---

**감사 종료**: 본 보고서는 정적 분석 결과이며, 실제 워커 로그 (`stocks.log`, Celery error monitor) 와 교차 검증 권장.
