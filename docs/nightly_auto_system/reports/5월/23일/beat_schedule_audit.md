# Celery Beat 스케줄 감사 보고서

- 대상: `config/celery.py` `app.conf.beat_schedule`
- 항목 수: **86개**
- 기준 시각: 모두 EST (코멘트 기준) — 단 일부는 UTC 명시
- 감사 일자: 2026-05-23
- 모드: 읽기 전용 (코드 수정 없음)

> ⚠ **하네스 주의**: `config/settings.py`의 `CELERY_BEAT_SCHEDULER='DatabaseScheduler'` 설정으로
> 본 dict는 런타임에 실행되지 않는다. 실제 실행 소스는 `django_celery_beat.PeriodicTask` DB 테이블.
> 본 감사는 **"설계된 스케줄"** 기준으로, 실제 DB drift 가능성은 별도 확인 필요.

---

## 0. Executive Summary

| 등급 | 항목 | 위험 |
|------|------|------|
| **P0** | `update-daily-prices` (17:00) ↔ `sync-sp500-eod-prices` (18:00) 중복 동기화 | FMP 호출 낭비 + 데이터 경합 가능 |
| **P0** | 18:30 EST 동시 5개 default queue 폭주 (run-eod / thesis-snapshot / update-change-pct / analyze-news-deep / [classify 18:15 후속]) | 워커 적체, EOD 지연 가능 |
| **P0** | `sec-sync-dirty-neo4j` 매 5분 + neo4j queue solo pool (1 동시) | Neo4j 큐 점유, 12:00 EST 동기화 묶음 밀림 |
| **P1** | 09:00–16:00 매 1분 `refresh-market-pulse-cache` + 매 5분 FMP(`realtime-prices`/`market-indices`) | FMP burst 분당 합계 동시 발생, batch quote 미사용 시 300 RPM 위협 |
| **P1** | 18:30 `analyze-news-deep-batch` (Gemini 50개) ↔ 18:35 `thesis-generate-summaries` (Gemini) 인접 | Gemini 15 RPM 한도, analyze 완료 전 thesis 시작 가능 |
| **P1** | 12:00 EST neo4j queue 4건 군집 (`chainsight-sync-profiles` + `sec-seed-relations` + 12:15 health + 12:30 `chainsight-sync-relations`) + 매 5분 sec-sync 점유 | Neo4j 큐 적체 |
| **P1** | 매월 1일 03:00 `refresh-korean-overviews-monthly` (S&P 500) ≈ Gemini 1500 RPD의 33% | 같은 날 sync-supply-chain-batch는 15일이라 충돌 없음. 단, 1일이 일요일이면 train-importance-model과 03:00 동시 |
| **P2** | `collect-sp500-news-fmp-orchestrator` 5회/일 (S&P 500 전체) | 종목당 1 call이면 분당 300 RPM 빠듯, orchestrator 분산 전략 검증 필요 |
| **P2** | 09:00 평일 시작 시점 9개 태스크 동시 발생 | default queue burst, FMP 동시 호출 |
| **P2** | 일요일 04:00~04:30 동시 5개 (cleanup-news / check-auto-deploy / scan-regulatory / build-patent[월1일] / chainsight-dirty / train-lightgbm / monitor-ml) | 일요일 새벽 적체 |

---

## 1. 시간대별 ASCII 히트맵 (평일 EST 기준)

각 시간대 "1시간 안에 발생하는 태스크 실행 횟수" (정시 + recurring base 포함)

```
시간대  실행수   히트맵 (1칸 ≈ 6 events)
─────  ───────  ─────────────────────────
00:     ~14     ██▌                              [neo4j-health(00)]
01:     ~15     ██▌                              [update-econ-calendar]
02:     ~14     ██▌                              [sp500-constituents 1일, archive 1일/2:30]
03:     ~17     ███                              [cleanup-macro(일), train-importance(일), shadow-report(일/3:30), refresh-korean(월1일), supply-chain(월15일)]
04:     ~18     ███                              [cleanup-news, check-auto-deploy(일), scan-regulatory(월), sync-institutional(월16일), build-patent(월1일/4:30), train-lightgbm(일/4:30), chainsight-dirty(일/4:30)]
05:     ~16     ███                              [cleanup-task-results(일), validation(토), enrich-keywords(5:30)]
06:     ~20     ████                             [update-econ, collect-daily-news, neo4j-health(06), sp500-fmp(6:15), category-high(6:30), general-fmp(6:45), etf-holdings(월), sec-filings(월1일)]
07:     ~20     ████                             [chainsight-heat, error-digest, collect-medium(7:00), market-movers(7:30), category-low(7:30), press-fmp(7:45)]
08:     ~19     ████                             [keyword-gen, market-news, classify-news(8:15), analyze-deep(8:30), sync-news-neo4j(8:45)]
09:     ~110    ██████████████████░░             [9-16시 진입 → +realtime(5분) +market-idx(5분) +pulse(1분) +portfolio(10분) +screener(15분) + aggregate-sentiment + extract-news-relations]
10:     ~100    ██████████████████               [+co-mentions(10:00), classify(10:15), sp500-fmp(10:15), analyze-deep(10:30), sync-neo4j(10:45)]
11:     ~96     ██████████████████               [+relation-confidence(11:00)]
12:     ~108    ██████████████████░              [+update-econ(12), collect-market-news(12), classify(12:15), neo4j-health(12), chainsight-sync-profiles(12), sec-seed-relations(12), chainsight-sync-relations(12:30), general-fmp-noon(12:30), analyze-deep(12:30), sync-neo4j(12:45), chainsight-seed-selection(13 UTC=09 EST?)]
13:     ~102    ██████████████████               [+category-high-midday(13:00), sp500-fmp(13:15), classify(skip — 13 not in cron), analyze-deep(skip)]
14:     ~104    ██████████████████               [+category-medium-afternoon(14:00), classify(14:15), daily-news-afternoon(14:30), analyze-deep(14:30), sync-neo4j(14:45)]
15:     ~98     ██████████████████               [+market-news-afternoon(15:00), sp500-fmp(15:15)]
16:     ~110    ██████████████████░              [+market-breadth(16:30), sector-heatmap(16:35), keywords-extract(16:45), classify(16:15), analyze-deep(16:30), sync-neo4j(16:45)]
17:     ~17     ███                              [update-daily-prices(17:00 ⚠중복), category-high-evening(17:00), sp500-fmp(17:15), general-fmp(17:45)]
18:     ~22     ████                             [update-econ(18), market-news-evening(18), sp500-eod-prices(18 ⚠중복), thesis-readings(18), neo4j-health(18), thesis-scores(18:15), classify(18:15), run-eod(18:30), thesis-snapshots(18:30), update-change-pct(18:30), analyze-deep(18:30), thesis-summaries(18:35), sync-neo4j(18:45)]
19:     ~16     ███                              [collect-ml-labels, backfill-accuracy]
20:     ~15     ███                              [sp500-financials(평일)]
21:     ~14     ██▌
22:     ~15     ██▌                              [update-econ(22)]
23:     ~14     ██▌
```

**상시 recurring base (매 시간 12회 + 2회 = 14)**:
- `sec-sync-dirty-neo4j` 매 5분 → 시간당 12회 (Neo4j queue, solo pool)
- `check-pipeline-alerts` 매 30분 → 시간당 2회

**09–16시 추가 (피크 시간대)**:
- `refresh-market-pulse-cache` 매 1분 → +60회/시간
- `update-realtime-prices` 매 5분 → +12회/시간 (FMP)
- `update-market-indices` 매 5분 → +12회/시간 (FMP)
- `calculate-portfolio-values` 매 10분 → +6회/시간
- `check-screener-alerts` 매 15분 → +4회/시간

**피크 시간대**: **09:00, 12:00, 14:30, 16:30, 18:30** (각각 100+ events/hour)

---

## 2. Rate Limit 초과 구간 분석

### 2-1. FMP Starter Plan (300 calls/min, 10,000 calls/day)

| 시간 | 태스크 | 추정 호출 | 위험 |
|------|--------|---------|------|
| 09:00–16:00 매 5분 | `update-realtime-prices` (S&P 500 = ~500 symbols) | batch quote 사용 시 5 calls / 미사용 시 500 calls | **P1** — batch 사용 여부 검증 필요 |
| 09:00–16:00 매 5분 | `update-market-indices` | ~10 indices = 10 calls | OK |
| 06:15, 10:15, 13:15, 15:15, 17:15 (5회/일) | `collect-sp500-news-fmp-orchestrator` | 종목당 1 call이면 500 calls/run → 분산 시 1.7분, 안 분산 시 한도 초과 | **P2** — orchestrator 분산 로직 확인 필요 |
| 06:45, 12:30, 17:45 (3회/일) | `collect-general-news-fmp` | 1~few calls | OK |
| 07:45 평일 | `collect-press-releases-fmp` (max 50) | 50 calls | OK |
| 18:00 평일 | `sync-sp500-eod-prices` (~500 symbols) | batch 사용 시 5 calls / 미사용 시 500 calls | **P0** — `update-daily-prices` 17:00과 중복, FMP 호출 낭비 |
| 20:00 평일 | `sync-sp500-financials` (101 symbols × ~5 API) | ~505 calls, 2분 소요 (한도 300 RPM 내) | OK |
| 06:00 월요일 | `sync-etf-holdings` | 종목별 holdings call | low traffic 시간대, OK |

**FMP 일일 합계 추정**:
- 분당 피크: 09:00 정각 = realtime(5~500) + market-idx(10) + 09:00 시작 시점 모두 합산 → batch 미사용 시 **분당 500+ 가능, 한도 300 초과**
- 일일 합계: realtime 12회/시간 × 7시간 + financials 505 + EOD 500 + sp500-news 2500 (5×500) + 기타 = **약 7,000–8,500 calls/day** (10,000 RPD 한도 70~85%)

**P0 결론**: `update-daily-prices` (17:00) 와 `sync-sp500-eod-prices` (18:00) 중복 — 둘 다 `stocks.tasks.update_realtime_with_provider` 또는 EOD 동기화로 같은 가격 호출. 17:00 태스크 폐기 또는 역할 분리 필요.

### 2-2. Gemini Free Tier (15 RPM, 1500 RPD)

| 시간 | 태스크 | 추정 호출 | 소요 | 위험 |
|------|--------|---------|------|------|
| 05:30 매일 | `enrich-relationship-keywords` (limit=100) | 100 calls | 100/15 = **6.7분 소요** | OK (단일 burst, 한도 내 throttle) |
| 08:00 매일 | `keyword-generation-pipeline` (gainers) | 20~50 calls | 1.3~3.3분 | OK |
| 08:15, 10:15, 12:15, 14:15, 16:15, 18:15 (6회/일) | `classify-news-batch` | 룰엔진 + 일부 LLM | 분류 단계는 LLM 미사용 가능. 검증 필요 | P3 |
| 08:30, 10:30, 12:30, 14:30, 16:30, **18:30** (6회/일) | `analyze-news-deep-batch` (max 50) | 최대 50 calls | 50/15 = **3.3분 소요** | **P1** — 18:30 thesis-summaries 18:35와 인접 |
| **16:45** 매일 | `extract-daily-news-keywords` | Gemini | 1~3분 | OK (16:30 analyze와 15분 간격 ✓ 코멘트 인지) |
| **18:35** 평일 | `thesis-generate-summaries` | thesis 개수만큼 | thesis N개 | **P1** — 18:30 analyze (50개, 3.3분 → 18:33 종료) 이후 1.5분 안에 시작, 큐 적체 시 겹침 |
| 매월 1일 03:00 | `refresh-korean-overviews-monthly` | ~500 calls (S&P 500) | **33분 소요** (분당 15) | **P1** — RPD 1500의 33% 소비, 같은 날 분포 영향 |
| 매월 15일 03:00 | `sync-supply-chain-batch` (top 100) | 100 calls + LLM 분석 | ~7분 + 분석 시간 | OK (1일과 다른 날) |

**Gemini 일일 합계 추정 (평일)**:
- enrich(100) + keyword-gen(20~50) + analyze-deep × 6 (300) + extract-keywords(10~30) + thesis-summaries(N) + extract-news-relations(?) = **약 450–600 calls/day**
- 한도 1500 RPD의 30–40% 사용. **OK**.

**위험**: 매월 1일 + 일요일 겹치면 03:00 동시 = `train-importance-model` + `refresh-korean-overviews-monthly` + `cleanup-old-macro-data` 03개. Gemini 한도는 corean-overviews만 큰 영향, 다른 둘은 LLM 미사용으로 OK.

### 2-3. Alpha Vantage (5 calls/min)

- `app.conf.beat_schedule` 내 AV 사용 태스크 **없음** ✓
- `update-economic-indicators`는 FRED API 사용 (별도 한도)
- AV 의존성은 ad-hoc 호출(API_request/)에 한정될 것으로 추정. 스케줄 차원 위험 없음.

---

## 3. Queue 몰림 분석

### 3-1. neo4j queue (solo pool, 동시 1개)

| 시각 | 태스크 | 비고 |
|------|--------|------|
| 매 5분 (00–23) | `sec-sync-dirty-neo4j` | **상시 점유** — 288회/일 |
| 매 6시간 (00, 06, 12, 18) | `neo4j-health-check` | sec-sync와 충돌 가능 |
| 매 2시간 평일 (8:45, 10:45, 12:45, 14:45, 16:45, 18:45) | `sync-news-to-neo4j` | sec-sync 5분 슬롯과 정확히 일치 (X:45) |
| 04:00 매일 | `cleanup-expired-news-relationships` | OK |
| 05:30 매일 | `enrich-relationship-keywords` | Gemini + Neo4j |
| 09:00 매일 | `extract-news-relations` | Default queue (코드 확인 필요) |
| **12:00 매일** | `chainsight-sync-profiles-neo4j` + `sec-seed-relations-to-chainsight` (둘 다 12:00) | **동시 발생** |
| 12:30 매일 | `chainsight-sync-relations-neo4j` | 12:00 그룹 후속 |
| 일 04:30 UTC | `chainsight-neo4j-dirty-sync` | 동시간대 train-lightgbm 등 |

**P0 결론**:
- neo4j queue가 매 5분마다 `sec-sync` 점유 → 다른 neo4j 태스크는 평균 2.5분 대기
- 12:00 EST 정각: 2개 동시 + sec-sync(12:00) + 12:00 sync-news-to-neo4j(skip, 12시는 hour 리스트 미포함, 정확히는 14:45가 다음) → 그래도 3건 묶임
- **Neo4j worker 1대 운영 시 처리량 부족 가능성**. 별도 worker 분리 또는 sec-sync 주기 완화 검토 필요.

### 3-2. default queue 적체 구간

**18:30 EST 평일 폭주 (5건 동시)**:
1. `run-eod-pipeline` (EOD 시그널 14개 벡터 계산)
2. `thesis-create-snapshots` (스냅샷 + 알림 발송)
3. `update-sp500-change-percent` (DB 일괄 계산)
4. `analyze-news-deep-batch` (Gemini 50개)
5. `classify-news-batch` 18:15 후속 (15분 안에 끝나야 함, default queue)

→ **5건 동시 발생, EOD 파이프라인 의존 체인 깨질 위험**

**09:00 EST 평일 폭주 (9건 동시)**:
- `aggregate-daily-sentiment`, `extract-news-relations`
- 9-16시 시작: `update-realtime-prices`, `calculate-portfolio-values`, `update-market-indices`, `refresh-market-pulse-cache`, `check-screener-alerts`
- recurring base: `sec-sync-dirty-neo4j`, `check-pipeline-alerts`

→ **default queue worker 수 검증 필요**

**16:30 EST 평일 폭주 (4건)**:
- `analyze-news-deep-batch`, `calculate-market-breadth`, `calculate-sector-heatmap`
- + `classify-news-batch` (16:15 후속)

---

## 4. 시간대별 API 호출 히트맵

### 4-1. FMP 호출 히트맵 (분당 추정)

```
시각        분당 FMP calls        히트맵
─────────  ────────────────────  ───────────────
00–05:00          0              ░░░░░░░░░░
06:00            ~10             █░░░░░░░░░
06:15           ~500 (orch)      ████████░░  ⚠ orch 분산 미확인
06:45            ~20             █░░░░░░░░░
07:30            ~10             █░░░░░░░░░
07:45            ~50             █░░░░░░░░░
09:00–16:00     5~500 매 5분     █████████░  ⚠ batch quote 사용 여부 핵심
10:15           ~500 (orch)      ████████░░
13:15           ~500 (orch)      ████████░░
15:15           ~500 (orch)      ████████░░
17:00            ~500 (daily)    ████████░░  ⚠ EOD 중복
17:15           ~500 (orch)      ████████░░
17:45            ~20             █░░░░░░░░░
18:00            ~500 (eod)      ████████░░  ⚠ EOD 중복
20:00           ~505 (fin) 2분   █████████░
22–23:00          0              ░░░░░░░░░░
```

### 4-2. Gemini 호출 히트맵 (분당 추정, 평일)

```
시각        분당 Gemini calls    히트맵
─────────  ────────────────────  ───────────────
00–04:00          0              ░░░░░░░░░░
05:30           ~15 × 6.7m       █████████░
08:00           ~15 × 3m         █████░░░░░
08:30           ~15 × 3.3m       █████░░░░░  (analyze-deep)
10:30           ~15 × 3.3m       █████░░░░░
12:30           ~15 × 3.3m       █████░░░░░
14:30           ~15 × 3.3m       █████░░░░░
16:30           ~15 × 3.3m       █████░░░░░
16:45           ~15 × 1~3m       ███░░░░░░░  (extract-keywords)
18:30           ~15 × 3.3m       █████░░░░░  (analyze-deep)
18:35           ~15 × Nm         ████░░░░░░  ⚠ 18:33 직후 겹침 가능
```

### 4-3. neo4j queue 점유 히트맵

```
00–23 시간대 점유율 (1시간당 점유 분):
00: ████████████████░░░░░░░░ 매 5분 sec-sync (12회) + 00:00 health (~30분 점유)
01: ████████░░░░░░░░░░░░░░░░ 매 5분 sec-sync only
...
04: ████████████░░░░░░░░░░░░ sec-sync + cleanup-expired-news
05: ████████████░░░░░░░░░░░░ sec-sync + 05:30 enrich (6.7분)
06: ████████████████░░░░░░░░ sec-sync + 06:00 health + 06:00 cleanup
08: ████████████████░░░░░░░░ sec-sync + 08:45 sync-news-neo4j
10: ████████████████░░░░░░░░ sec-sync + 10:45 sync-news-neo4j
12: ██████████████████████░░ sec-sync + 12:00 chainsight + 12:00 sec-seed + 12:00 health + 12:30 chainsight-rel
14: ████████████████░░░░░░░░ sec-sync + 14:45 sync-news-neo4j
16: ████████████████░░░░░░░░ sec-sync + 16:45 sync-news-neo4j
18: ████████████████████░░░░ sec-sync + 18:00 health + 18:45 sync-news-neo4j
```

**12:00 EST가 최대 점유 구간** — solo pool 1대로 처리 시 적체 가능.

---

## 5. 스케줄 겹침 / 의존성 분석

### 5-1. 명시적 체인 (정상)

| 체인 | 흐름 | 검증 |
|------|------|------|
| Thesis Control | 18:00 readings → 18:15 scores → 18:30 snapshots → 18:35 summaries | 15분 간격 — 적체 시 위험 |
| News 분석 (매 2시간) | X:15 classify → X:30 analyze-deep → X:45 sync-neo4j | 15분 간격 — Gemini throttle 시 겹침 |
| EOD Dashboard | 17:00 daily-prices → 18:00 sp500-eod → 18:30 run-eod → 18:30 update-change-pct → 19:00 backfill-accuracy | **17:00 ↔ 18:00 중복 P0** |
| Chain Sight 토요일 | 02:00 profiles → 03:00 price-co-move → 04:00 stale-decay → 04:30 aggregate | 1시간 간격 OK |
| Chain Sight 일일 | 10:00 co-mentions → 11:00 relation-confidence → 12:00 sync-profiles → 12:30 sync-relations | 30~60분 간격 OK |
| ML Pipeline (일) | 03:00 train-importance → 03:30 shadow → 04:00 auto-deploy → 04:15 weekly-ml → 04:20 monitor → 04:30 train-lightgbm | 적체 시 짧은 간격 위험 |
| Chain Sight UTC | 07:00 heat-score → 13:00 seed-selection | 6시간 간격 OK |

### 5-2. 의존성 위반 가능성 (선행 미완료 시 후속 시작)

| 후속 | 선행 | 간격 | 위험도 |
|------|------|------|--------|
| `run-eod-pipeline` (18:30) | `sync-sp500-eod-prices` (18:00) | **30분** | **P1** — S&P 500 EOD 500 symbols 처리에 batch 미사용 시 1.7분+, 다른 18:00 태스크와 큐 경쟁 시 30분 초과 가능 |
| `analyze-news-deep-batch` (X:30) | `classify-news-batch` (X:15) | **15분** | **P1** — classify가 룰엔진이면 빠름, 단 적체 시 15분 부족 |
| `thesis-generate-summaries` (18:35) | `thesis-create-snapshots` (18:30) | **5분** | **P2** — snapshots는 DB 작업, 5분 안에 완료 가정 |
| `sec-seed-relations-to-chainsight` (12:00) | `sec-sync-dirty-neo4j` (매 5분) | **5분** | **P2** — 새 evidence 즉시 반영 의도면 OK |
| `chainsight-aggregate-profiles` (토 04:30) | `chainsight-stale-decay` (토 04:00) | **30분** | OK |
| `validation-weekly-batch` (토 05:00) | `chainsight-aggregate-profiles` (토 04:30) | **30분** | OK |
| `check-auto-deploy` (일 04:00) | `generate-shadow-report` (일 03:30) | **30분** | OK |

### 5-3. 동시 실행 데이터 경합 위험

**EOD 18:00 묶음 (5건 동시)**:
- `update-economic-indicators` (FRED)
- `collect-market-news-evening` (news API)
- `sync-sp500-eod-prices` (FMP, ~500 symbols → DB write)
- `thesis-update-readings` (DB read — DailyPrice 의존)
- `neo4j-health-check` (Neo4j queue)

→ `sync-sp500-eod-prices`가 DailyPrice 쓰는 동안 `thesis-update-readings`가 같은 DailyPrice 읽기. **읽기-쓰기 경합** 가능. 단 DailyPrice는 UPSERT라 dirty read 위험 낮음. **P2**.

**18:30 묶음 (4건 default queue)**:
- `run-eod-pipeline` (Signal 14개 → JSON Bake)
- `thesis-create-snapshots` (Snapshot 모델 INSERT)
- `update-sp500-change-percent` (Stock.change_percent UPDATE)
- `analyze-news-deep-batch` (Article LLM 결과 UPDATE)

→ default queue worker 수 확인 필요. concurrency=4 이상 권장. **P0**.

**12:00 EST 묶음 (neo4j queue)**:
- `chainsight-sync-profiles-neo4j`
- `sec-seed-relations-to-chainsight` (default 또는 neo4j?)
- `neo4j-health-check`

→ Neo4j solo pool 1대면 직렬 처리, 12:30 chainsight-sync-relations까지 30분 안에 끝나야 함. **P1**.

### 5-4. 코멘트에 명시된 이전 충돌 (이미 해결됨)

- ✓ 16:30 analyze-news-deep ↔ 16:30 extract-daily-news-keywords → 16:45로 분리 (audit P0 #8, 2026-04-26)
- ✓ 18:35 thesis-summaries 신설 (audit P0 #15)
- ✓ Drift 복구: chainsight-heat-score-daily, sec-seed-relations-to-chainsight DB 등록 (2026-04-24)

---

## 6. 권장 조치 (코드 수정 별도 PR)

### P0 (즉시 검토)
1. **`update-daily-prices` (17:00) ↔ `sync-sp500-eod-prices` (18:00) 중복** — 한쪽 폐기 또는 17:00을 다른 역할로 재정의
2. **18:30 default queue 5건 동시** — `analyze-news-deep-batch` 18:30을 18:50으로 이동 (EOD 묶음과 분리)
3. **sec-sync-dirty-neo4j 매 5분 + Neo4j solo pool** — 주기 10분 완화 또는 neo4j worker 2대 분리

### P1 (이번 슬라이스 내)
4. **FMP batch quote 사용 검증** — `update-realtime-prices`, `sync-sp500-eod-prices`가 `/stable/quote-bulk` 사용하는지 코드 확인
5. **18:35 thesis-summaries 위치 재검토** — 18:30 analyze 50개가 3.3분 소요, 18:35는 18:40 권장
6. **12:00 EST neo4j 묶음 분산** — chainsight-sync-profiles를 11:30, sync-relations를 12:00, sec-seed를 12:30으로 재배치

### P2 (다음 슬라이스)
7. **collect-sp500-news-fmp-orchestrator 분산 로직 검증** — 500 symbols / 분당 300 한도 안에서 처리 보장
8. **09:00 평일 동시 시작 9건** — recurring 태스크의 jitter (`minute=':1'` 등) 도입 검토
9. **일요일 04:00–04:30 ML/Chain Sight 묶음** — 30분 간격 확장 (04:00 → 04:30 → 05:00 등)

### P3 (모니터링)
10. **PeriodicTask DB drift 정기 점검** — `set(PeriodicTask.objects.values_list('name')) vs config dict 키` diff 자동화
11. **classify-news-batch LLM 사용 여부 확인** — 코드 검증 후 Gemini 한도 계산 갱신
12. **extract-news-relations queue 라우팅 확인** — neo4j queue 명시 안 되어 default일 가능성

---

## 7. 참조

- 본 보고서는 `config/celery.py`의 `app.conf.beat_schedule` dict 기준
- 실제 실행은 `django_celery_beat.PeriodicTask` DB가 진실의 소스 — drift 별도 확인 필요
- common-bugs.md #28 (Beat schedule drift) 참조: dict 등록만으로는 실행되지 않음
- 코멘트에 명시된 과거 audit P0 #8, #15 등 인지 완료

— 끝 —
