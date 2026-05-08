# Beat Schedule Audit — 2026-05-08

**대상 파일**: `config/celery.py` (820 lines, beat_schedule 90개 항목)
**감사 범위**: Rate Limit, Queue 부하, 시간대 분포, 의존성 충돌
**전제**: `CELERY_BEAT_SCHEDULER = django_celery_beat.schedulers:DatabaseScheduler` — 본 감사는 코드 dict 기준이며, 실제 실행은 DB `PeriodicTask`가 진실의 소스 (drift 가능성 별도 항목으로 명시).
**시간대 가정**: 본 보고서는 모든 `crontab(hour=N)`을 Django `TIME_ZONE` 기준의 단일 시각으로 해석. EST/UTC 라벨 충돌은 §5에서 별도 추적.

---

## 0. 한눈에 보는 결과 (Severity 요약)

| 심각도 | # | 이슈 | 임계도 |
|--------|---|------|--------|
| **P0** | 1 | 17:00 M-F: FMP 5개 태스크 동시/근접 → 300 calls/min 초과 위험 | HIGH |
| **P0** | 2 | 18:00 M-F: FMP S&P 500 EOD + 뉴스 + 시장뉴스 + 거시 → 1분 피크 600 calls/min 추정 | HIGH |
| **P0** | 3 | 18:30 M-F: Gemini 동시 호출 (analyze-deep + thesis-summaries) → 15 RPM 초과 | HIGH |
| **P1** | 4 | 12:00–12:45 매일: Neo4j queue (solo) 4개 태스크 직렬화 + sec-sync-dirty 5분 주기 끼어듦 | MED |
| **P1** | 5 | EST/UTC 라벨 혼용 (chainsight-heat-score 주석 "UTC", 다른 태스크 "EST") | MED |
| **P1** | 6 | sync-news-to-neo4j 08:45 ↔ analyze-news-deep-batch 08:30 (15분) — 50 articles 분석이 15분 내 완료 보장 없음 | MED |
| **P2** | 7 | extract-news-relations(09:00 daily) / chainsight-co-mentions(10:00 daily) — 주말에도 실행되나 뉴스 수집은 평일만 | LOW |
| **P2** | 8 | check-pipeline-alerts */30 + sec-sync-dirty */5 — :30 분에 매시 충돌 (default+neo4j 분리되어 영향 작음) | LOW |
| **P2** | 9 | refresh-market-pulse-cache 매분(*/1) 9-16 M-F — 480 firings/day, 본인은 캐시여도 cascade 호출 시 폭증 | LOW |
| **P2** | 10 | aggregate-weekly-prices(Sat 01:00) ↔ update-economic-calendar(daily 01:00) — 동시 실행 (단순 충돌, 영향 작음) | LOW |

---

## 1. Rate Limit 초과 구간 분석

### 1-A. FMP (Starter Plan: 300 calls/min, 10,000 calls/day)

#### 🔴 P0 #1: 17:00 M-F — FMP 5개 태스크 15분 윈도우 폭주

| 시각 | 태스크 | 추정 FMP 호출량 | 비고 |
|------|--------|----------------|------|
| 17:00 | update-daily-prices (`update_realtime_with_provider`) | **~500 calls** | S&P 500 전 종목 가격 갱신 |
| 17:00 | collect-category-news-high-evening | 50–200 | 카테고리 high 종목 news |
| 17:15 | collect-sp500-news-fmp-1715 (orchestrator) | **~500 calls** | S&P 500 전 종목 news 분산 호출 |
| 17:45 | collect-general-news-fmp-evening | 1–10 | 단일 일반 뉴스 엔드포인트 |

- **위험도**: 17:00–17:01 사이 update-daily-prices가 batch 호출이면 300/min 한도에 직격. orchestrator가 chord 분산이라도 `*/5` 주기의 `update-realtime-prices`(9-16 종료, 17시는 미가동) → 우려 완화. 다만 17:00 `update-daily-prices`만으로도 단발 batch가 300/min을 넘을 수 있음.
- **검증 권장**: `stocks/tasks.py:343 update_realtime_with_provider` 내부 throttle 확인.

#### 🔴 P0 #2: 18:00 M-F — FMP 동시 1분 피크

| 시각 | 태스크 | 추정 호출량 | API |
|------|--------|------------|-----|
| 18:00 | sync-sp500-eod-prices | **~500 calls** | FMP /stable/historical-price-full |
| 18:00 | collect-market-news-evening | 1–5 | FMP general |
| 18:00 | thesis-update-readings | 변동 | FMP/내부 (지표 카탈로그 의존) |
| 18:00 | update-economic-indicators | 0 | FRED (FMP 무관) |

- **위험도**: sync-sp500-eod-prices가 동시 batch라면 1분 안에 500 calls → **300/min 한도 1.6× 초과**.
- **추가 부담**: `expires=3600`이라 retry 큐가 쌓이면 다음 분에 재시도 → 더 악화.
- **선행 의존성**: 18:30 run-eod-pipeline은 18:00 EOD 가격 완료 가정. 18:00 batch가 throttle로 30분 초과 시 **stale data로 EOD 파이프라인 실행**.

#### 🟡 P1 #6 인접: 06:00–08:00 M-F 아침 뉴스 폭주대

| 시각 | 태스크 | FMP 호출 |
|------|--------|---------|
| 06:00 | collect-daily-news-morning | 종목수 × 1 |
| 06:00 | sync-etf-holdings (Mon만) | 수~수십 |
| 06:00 | update-economic-indicators | 0 (FRED) |
| 06:15 | collect-sp500-news-fmp-0615 | ~500 (orchestrator) |
| 06:30 | collect-category-news-high-morning | 50–200 |
| 06:45 | collect-general-news-fmp-morning | 1–5 |
| 07:00 | collect-category-news-medium-morning | 50–100 |
| 07:30 | sync-daily-market-movers | 5–20 |
| 07:30 | collect-category-news-low | 30–80 |
| 07:45 | collect-press-releases-fmp (max_symbols=50) | ~50 |
| 08:00 | collect-market-news-morning | 1–5 |

- **분석**: 15분 단위로 분산되어 있어 각 분당 호출은 오케스트레이터의 chord 분산 정책에 의존. 06:15 sp500-news-fmp-0615 single batch 시 P0 수준.

### 1-B. Gemini Free (15 RPM, 1500 RPD)

#### 🔴 P0 #3: 18:30 M-F — Gemini 동시 호출 (5분 간격)

| 시각 | 태스크 | Gemini 사용 | 추정 calls |
|------|--------|------------|-----------|
| 18:15 | classify-news-batch (h=18) | LLM 분류 | 50 articles × 1 call = 50 |
| 18:30 | analyze-news-deep-batch (max_articles=50) | LLM 심층 | 50 articles × N calls |
| 18:30 | thesis-create-snapshots | (LLM 무관) | 0 |
| 18:35 | thesis-generate-summaries | Gemini 요약 | 활성 thesis 수 × 1+ |

- **위험도**: 18:30 시작 analyze-deep이 50 articles × ~2 calls (분석 + 추출) = ~100 calls를 6–10분에 처리하면 평균 10–17 RPM. **15 RPM Free Tier 이미 한계**. 여기에 18:35 thesis-generate-summaries가 병렬 진입 → **확실히 초과**.
- **이미 인지된 충돌**: code line 285–286 주석에 "audit P0 #8, 2026-04-26 — extract-daily-news-keywords를 16:30→16:45 분산"이 있어 동일 패턴 재발.
- **권고**: thesis-generate-summaries를 18:50 또는 19:10으로 분산 (collect-ml-labels 19:00 후).

#### 🟡 Gemini 일일 부하 (1500 RPD)

평일 Gemini 호출 추정:
- analyze-news-deep × 6 batches × 50 articles × 2 calls = **600 calls**
- classify-news-batch × 6 × 50 articles × 1 call = **300 calls**
- extract-daily-news-keywords (16:45 daily) × N stocks × 1 = **50–200 calls**
- enrich-relationship-keywords (05:30 daily, limit=100) = **100 calls**
- thesis-generate-summaries (18:35 M-F) × N theses × 1 = **20–100 calls**
- keyword-generation-pipeline (08:00 daily, gainers) = **20–50 calls**
- extract-news-relations (09:00 daily) = LLM 의존도 ?
- refresh-korean-overviews-monthly (1st 03:00) = **100–300 calls (월 1회 spike)**

→ 평일 합계 **1100–1500 calls/day** 추정. **1500 RPD 한도 근접/초과**. 월 1일에는 한국어 overview까지 포함되어 확실 초과.

### 1-C. Alpha Vantage (5 calls/min)

- **결과**: `*/tasks.py`에서 alpha_vantage 직접 호출 **없음** (grep `alpha_vantage|AlphaVantage` 결과 0건).
- AV는 `API_request/` 또는 수동 백테스트 경로에서만 사용 → **beat 스케줄에서는 위반 없음**.
- 단, FMP fallback으로 AV가 호출되는 코드가 있다면 별도 검증 필요 (본 감사 범위 밖).

---

## 2. Queue 몰림 분석

### Neo4j Queue (solo pool, 동시 1개)

#### Neo4j 큐로 라우팅되는 정기 태스크 (총 8개)

| 태스크 | 주기 | 일일 firings |
|--------|------|--------------|
| sec-sync-dirty-neo4j | `*/5` (모든 시각) | **288/day** |
| neo4j-health-check | `0 */6` | 4/day |
| sync-news-to-neo4j | M-F 08/10/12/14/16/18:45 | 6/day |
| chainsight-sync-profiles-neo4j | 12:00 daily | 1/day |
| chainsight-sync-relations-neo4j | 12:30 daily | 1/day |
| enrich-relationship-keywords | 05:30 daily | 1/day |
| cleanup-expired-news-relationships | 04:00 daily | 1/day |
| chainsight-neo4j-dirty-sync | Sun 04:30 | 1/week |

#### 🟡 P1 #4: 12:00 cluster — Neo4j queue serialization

12:00–12:45 동안 neo4j queue 진입 순서:
```
12:00:00  sec-sync-dirty-neo4j  (5분 주기 정시 실행)
12:00:00  neo4j-health-check    (6시간 주기)
12:00:00  chainsight-sync-profiles-neo4j
12:05:00  sec-sync-dirty-neo4j
12:10:00  sec-sync-dirty-neo4j
12:15:00  sec-sync-dirty-neo4j
12:20:00  sec-sync-dirty-neo4j
12:25:00  sec-sync-dirty-neo4j
12:30:00  sec-sync-dirty-neo4j
12:30:00  chainsight-sync-relations-neo4j
12:35:00  sec-sync-dirty-neo4j
12:40:00  sec-sync-dirty-neo4j
12:45:00  sec-sync-dirty-neo4j
12:45:00  sync-news-to-neo4j
```

- chainsight-sync-profiles-neo4j가 30분 초과 시 chainsight-sync-relations-neo4j(12:30) 큐 적체 → expires=3600으로 살아남지만 sync-news-to-neo4j(12:45)와 직렬 경쟁.
- sec-sync-dirty-neo4j `expires=240` (4분) 가 매번 만료 직전이라 워커 한 사이클이 5분 넘으면 **자동 폐기**.

#### 18:00 cluster (Neo4j queue)
```
18:00 neo4j-health-check
18:00 sec-sync-dirty
18:05 sec-sync-dirty
... (5분마다)
18:45 sync-news-to-neo4j
```
- 비교적 가벼운 부하. 단, 18:00 health-check가 무거우면 18:05 sec-sync 4분 expires 위험.

### Default Queue 시간대 분포

| 시간 | default queue 동시 시작 태스크 수 | 비고 |
|------|------------------------------|------|
| 09:00–16:55 M-F | 5종 intraday (realtime/indices/portfolio/pulse/screener) | 분당 평균 ~80 firings |
| 18:00 M-F | 4 (eod-prices + thesis-readings + market-news + econ-indicators) | **EOD 폭주 시작점** |
| 18:15 M-F | 2 (classify-news + thesis-calculate-scores) | |
| 18:30 M-F | 4 (analyze-deep + run-eod + thesis-snapshots + update-change-percent) | **두 번째 폭주** |
| 18:35 M-F | 1 (thesis-generate-summaries) | Gemini 부담 가중 |
| 19:00 M-F | 2 (collect-ml-labels + backfill-signal-accuracy) | |

---

## 3. 시간대별 ASCII 히트맵 (M-F 평일 기준)

### 3-A. 시간대별 전체 firings (intraday */N 포함)

```
시간   firings  히트맵 (1█ = 5 firings)
00:00     ~16  ███
01:00      ~7  █
02:00      ~7  █  (월별/주말 태스크 평일에는 적음)
03:00      ~7  █
04:00      ~9  █
05:00      ~8  █
06:00     ~10  ██  ← 아침 뉴스 시작
07:00      ~9  █
08:00     ~10  ██  ← 시장 전 LLM 시작
09:00    ~104  █████████████████████ ← MARKET OPEN
10:00    ~106  █████████████████████  (intraday + LLM)
11:00     ~99  ████████████████████
12:00    ~110  ██████████████████████ ← LLM + Neo4j sync 4종 중첩
13:00    ~102  ████████████████████
14:00    ~105  █████████████████████
15:00    ~101  ████████████████████
16:00    ~110  ██████████████████████ ← MARKET CLOSE + EOD 시작 + LLM
17:00     ~12  ██  ← intraday 종료, FMP daily 폭주 (P0 #1)
18:00     ~22  ████ ← EOD 폭주 (P0 #2, #3)
19:00      ~7  █
20:00      ~7  █  (sp500-financials)
21:00      ~6  █
22:00      ~6  █
23:00      ~6  █

상시 background:
- check-pipeline-alerts */30      → 48/day (모든 :00, :30)
- sec-sync-dirty-neo4j */5        → 288/day (모든 :00,05,10,...)
```

### 3-B. API 종류별 시간대 부하 히트맵 (M-F)

```
시간   FMP   Gemini   Neo4j   DB-only   FRED
00:00   ·      ·       █        ·        ·
01:00   ·      ·       ·       █         ·
02:00   ·      ·       ·       ·         ·
03:00   ·      ·       ·       ·         ·
04:00   ·      ·       █       █         ·
05:00   ·      █       █        ·        ·
06:00  ███     ·       █       ·         █
07:00  ███     ·       ·       █         ·
08:00   █      ██      █       ·         ·
09:00  ███     █       ·       █         ·
10:00  ███     ██      █       █         ·
11:00  ███     ·       ·       █         ·
12:00  ███     ██      ███     █         █
13:00  ███     ·       ·       █         ·
14:00  ███     ██      █       █         ·
15:00  ███     ·       ·       █         ·
16:00  ███     ██      █       █         ·
17:00  ████    ·       ·       ·         ·   ← P0 #1 (FMP 단발 폭주)
18:00  ████    ██      █       ███       █   ← P0 #2 + #3
19:00   ·      ·       ·       █         ·
20:00  █       ·       ·       ·         ·
22:00   ·      ·       ·       ·         █

범례: ·=0,  █=1태스크,  ██=2,  ███=3+,  ████=critical (>500 calls/min 가능)
```

### 3-C. Neo4j Queue 단독 히트맵 (solo pool)

```
시간    sec-sync-dirty(*/5)  health  sync-news  chainsight  기타
00     12회                   ✓      ·          ·            ·
04     12회                   ·      ·          ·            cleanup-expired
05     12회                   ·      ·          ·            enrich-relations
06     12회                   ✓      ·          ·            ·
08     12회                   ·      ✓ (08:45)  ·            ·
10     12회                   ·      ✓ (10:45)  ·            ·
12     12회                   ✓      ✓ (12:45)  ✓✓ (00,30)   ← MAX
14     12회                   ·      ✓          ·            ·
16     12회                   ·      ✓          ·            ·
18     12회                   ✓      ✓          ·            ·
일요    +                    +       +          +            chainsight-dirty (04:30)
```

---

## 4. 스케줄 겹침 / 의존성 검증

### 의존성 체인 (시간 순서)

#### EOD 파이프라인 (18:00–19:00 M-F)
```
18:00 sync-sp500-eod-prices  ─┐
18:00 thesis-update-readings  ├→ 18:15 thesis-calculate-scores
18:00 update-econ-indicators ─┘                │
                                                ↓
                                18:30 thesis-create-snapshots ─→ 18:35 thesis-generate-summaries
                                18:30 run-eod-pipeline ────────→ 19:00 backfill-signal-accuracy
                                18:30 update-sp500-change-percent
                                18:30 analyze-news-deep-batch ──→ 18:45 sync-news-to-neo4j
                                18:15 classify-news-batch ──────↗
```

**경고 사항**:
- ① `sync-sp500-eod-prices`(18:00)가 30분 내 미완료 시 `run-eod-pipeline`(18:30)이 stale prices 사용. FMP throttle 시 빈번 발생 가능.
- ② `thesis-update-readings`(18:00) → `thesis-calculate-scores`(18:15) 15분 갭. readings가 지표 카탈로그 전체 갱신이면 부족할 수 있음.
- ③ `analyze-news-deep-batch`(18:30, 50 articles, Gemini 15 RPM 제약 시 ~3.3분/article 간격) → 50개 = 최대 165분 → `sync-news-to-neo4j`(18:45) 시점에 **분석 미완**.
  - 단, sync-news-to-neo4j는 분석 완료된 article만 동기화하면 무해. 동기화 누락 발생 가능성 있음.

#### 주말 ML/Chain Sight 파이프라인 (Sat–Sun 새벽)
```
Sat 02:00 chainsight-all-profiles
Sat 03:00 chainsight-price-co-movement
Sat 04:00 chainsight-stale-decay
Sat 04:30 chainsight-aggregate-profiles ← 위 3개 완료 가정
Sat 05:00 validation-weekly-batch ← Chain Sight 후
Sun 03:00 train-importance-model
Sun 03:30 generate-shadow-report ← 학습 후
Sun 04:00 check-auto-deploy ← shadow report 후
Sun 04:00 cleanup-expired-news-relationships (독립)
Sun 04:00 scan-regulatory-relationships (독립, Mon만)
Sun 04:15 generate-weekly-ml-report ← auto-deploy 후
Sun 04:20 monitor-ml-performance ← weekly report 후
Sun 04:30 train-lightgbm-model ← 모니터링 후
Sun 04:30 chainsight-neo4j-dirty-sync (Neo4j queue)
Sun 05:00 cleanup-task-results
```

**경고 사항**:
- ④ `train-importance-model`(03:00)이 30분 내 학습 미완료 시 `generate-shadow-report`(03:30) 스킵 또는 실패.
- ⑤ Sat 04:30 `chainsight-aggregate-profiles`가 default queue, Sun 04:30 `chainsight-neo4j-dirty-sync`가 neo4j queue — queue 분리되어 충돌 없음.
- ⑥ Sun 04:00 동시 시작: `cleanup-expired-news-relationships`(neo4j) + `check-auto-deploy`(default) + `scan-regulatory-relationships`(default Mon, Sun 미해당). queue 분리되어 안전.

#### Daily Chain Sight (10:00–13:00)
```
10:00 chainsight-co-mentions ─→ 11:00 chainsight-relation-confidence
                                  ↓
                                12:00 chainsight-sync-profiles-neo4j
                                  ↓
                                12:30 chainsight-sync-relations-neo4j
                                  ↓
                                13:00 chainsight-seed-selection
```
- 정상 직렬. **다만 neo4j queue 적체 시(P1 #4) 12:30 sync가 13:00 전 미완료 → seed-selection이 stale relation으로 실행**.

### 동시 시작 충돌 (같은 분에 여러 태스크)

| 시각 | 동시 시작 태스크 | Queue | 영향 |
|------|------------------|-------|------|
| 06:00 M-F | collect-daily-news-morning, update-econ-indicators, neo4j-health-check, sync-etf-holdings(Mon) | mixed | FMP 분산, queue OK |
| 12:00 daily | chainsight-sync-profiles-neo4j, sec-seed-relations-to-chainsight, neo4j-health-check, update-econ-indicators(M-F), collect-market-news-noon(M-F) | **neo4j 3개 + default 2개** | neo4j queue 적체 |
| 18:00 M-F | sync-sp500-eod-prices, thesis-update-readings, collect-market-news-evening, update-econ-indicators, neo4j-health-check | default 4 + neo4j 1 | **P0 #2** |
| 18:30 M-F | analyze-news-deep-batch, run-eod-pipeline, thesis-create-snapshots, update-sp500-change-percent | default 4 | DB 동시 트랜잭션 위험 |
| 04:00 일요 | check-auto-deploy, scan-regulatory(Mon), cleanup-expired-news-relationships, sync-institutional-holdings(16일) | mixed | 월/주 합쳐 6개 (16일 일요) |
| 04:30 일요 | train-lightgbm-model, build-patent-network(1일), chainsight-neo4j-dirty-sync, chainsight-aggregate-profiles(Sat 미해당) | mixed | 1일 일요 시 collision |

---

## 5. 부수 이슈

### 🟡 P1 #5: EST/UTC 라벨 혼용 (의도 vs 실행 시점 불명확)

| 태스크 | 주석 | crontab |
|--------|------|---------|
| chainsight-heat-score-daily | `매일 07:00 UTC` | `hour=7` |
| chainsight-seed-selection | `매일 13:00 UTC` | `hour=13` |
| 그 외 대부분 | `EST` 또는 `EST/ET` | `hour=N` |

- Celery beat는 Django `TIME_ZONE`에 의존. 같은 `hour=7`이 어떤 태스크는 "07:00 UTC", 다른 태스크는 "07:00 EST"라는 주석 모순.
- **검증 필요**: `config/settings.py`의 `TIME_ZONE`과 `CELERY_TIMEZONE` 확인.
- **위험**: EST 가정으로 짠 의존성(예: 18:00 EOD)과 UTC 가정으로 짠 chainsight가 실제로는 동일 시각 → 동시 실행 가능.

### 🟡 P2 #7: 평일 의존 태스크가 daily로 등록

`extract-news-relations`(09:00 daily), `chainsight-co-mentions`(10:00 daily), `chainsight-relation-confidence`(11:00 daily), `chainsight-sync-profiles-neo4j`(12:00 daily), `chainsight-sync-relations-neo4j`(12:30 daily), `chainsight-seed-selection`(13:00 daily), `sec-seed-relations-to-chainsight`(12:00 daily) 모두 `day_of_week` 미지정.

- 토/일 실행 시 신규 뉴스/관계가 거의 없어 빈 작업, 또는 직전 평일 데이터 재처리.
- 자원 낭비는 미미하나 idempotency 미구현 시 중복 데이터 위험.

### 🟡 P2 #9: refresh-market-pulse-cache 매분 실행

```python
'refresh-market-pulse-cache': crontab(minute='*', hour='9-16', day_of_week='1-5'),
```
- 8시간 × 60분 = **480 firings/day**.
- 단순 캐시 갱신이면 무해하나, 내부에서 FMP/DB 다중 호출하면 분당 전체 한도 잠식.
- **검증**: `macro/tasks.py refresh_market_pulse_cache` 내부 API 호출 수.

### 🟡 P2 #10: 01:00 daily 동시 실행

- `update-economic-calendar`(01:00 daily) + `aggregate-weekly-prices`(01:00 Sat). 토요일 새벽 동시. queue 동일(default), 영향 작음.

### Drift 위험 (코드 dict ↔ DB PeriodicTask)

- `config/celery.py:120–134` 주석에 명시된 운영 정책: **DB가 진실의 소스**.
- 본 감사는 코드 dict 기준이므로, 실제 DB 등록 상태와 다를 수 있음.
- **권고**: `manage.py shell`에서 `set(PeriodicTask.objects.values_list('name', flat=True))` ↔ 코드 dict 키 diff를 정기 실행 (현재 수동).

---

## 6. 최우선 권고 (우선순위 순)

### P0 즉시 조치 (1주 내)

1. **18:00 sync-sp500-eod-prices throttle 검증** (P0 #2)
   - `stocks/tasks.py:422 sync_sp500_eod_prices` 내부에 분당 호출 제한 (예: 250/min) 명시 확인.
   - 미존재 시 batch chord size를 `max_concurrency=4` 등으로 강제.

2. **18:30 Gemini 충돌 해소** (P0 #3)
   - `thesis-generate-summaries`를 18:35 → **19:10** (collect-ml-labels 19:00 이후) 이동.
   - 또는 analyze-news-deep-batch `max_articles`를 30으로 축소 (Gemini 일일 부담 동시 완화).

3. **17:00 update-daily-prices throttle 검증** (P0 #1)
   - 동일 함수 `update_realtime_with_provider` 사용, 단발 batch 시 한도 초과.

### P1 단기 조치 (2주 내)

4. **EST/UTC 라벨 통일** (P1 #5) — 모든 주석을 실제 `TIME_ZONE` 기준으로 갱신.
5. **12:00 Neo4j queue 부하 분산** (P1 #4) — chainsight-sync-profiles-neo4j를 11:30 또는 11:45로 이동, sync-news-to-neo4j 12:45 → 13:15.
6. **08:30 → 08:45 갭 검증** (P1 #6) — analyze-news-deep 평균 처리 시간 메트릭 측정 후 sync-news-to-neo4j 시각 조정.

### P2 정리 (1개월 내)

7. 평일 의존 daily 태스크에 `day_of_week='1-5'` 추가 (P2 #7).
8. refresh-market-pulse-cache 내부 호출 감사 → 필요 시 `*/2`로 완화 (P2 #9).
9. Drift 자동 감지 스크립트화 (현재 수동) — `python manage.py audit_beat_schedule_drift` 신설.

---

## 부록 A. 전체 태스크 인벤토리 (90건)

| Category | 갯수 | 비고 |
|----------|------|------|
| Stocks | 5 | realtime/daily/eod/financials/aggregate-weekly |
| Macro | 5 | indicators/indices/calendar/pulse/cleanup |
| Portfolio/Users | 1 | calculate-portfolio-values |
| RAG/Neo4j | 1 | health-check (semantic-cache 3종 제거됨) |
| Market Movers | 2 | sync-daily-market-movers + keyword-pipeline |
| News (collection) | 13 | daily(2) + market(4) + category(3 high + 2 med + 1 low) + press + general(3) + extract-keywords |
| News (intelligence v3) | 9 | classify×6 + analyze-deep×6 + sync-neo4j×6 + cleanup + ml-labels + train + shadow-report + auto-deploy + weekly-report + monitor + lightgbm + alerts |
| FMP S&P 500 News | 5 | orchestrator 5 timing |
| ETF/Supply Chain | 2 | sync-etf-holdings + sync-supply-chain-batch |
| Screener | 3 | breadth + heatmap + alerts |
| S&P 500 Sync | 3 | constituents + eod-prices + change-percent |
| Chain Sight | 11 | profiles + relations 6 + heat + seed + neo4j-sync 3 |
| EOD Dashboard | 3 | run-eod + backfill + korean-overviews |
| Thesis Control | 4 | readings + scores + snapshots + summaries |
| Validation | 1 | weekly-batch |
| SEC Pipeline | 3 | dirty-neo4j + seed-relations + check-new-filings |
| Archive | 1 | archive-old-articles |
| Monitoring | 2 | error-digest + cleanup-task-results |

(중복/카테고리 중복 포함, 최종 키 카운트는 코드 dict 기준 90개)

---

**감사 종료**. 본 보고서는 코드 dict 기준이며, 실제 운영은 `django_celery_beat.PeriodicTask` 테이블이 진실의 소스. P0 권고 시행 전 DB 등록 현황 재확인 필수.
