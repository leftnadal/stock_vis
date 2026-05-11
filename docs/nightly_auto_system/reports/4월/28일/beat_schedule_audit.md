# Beat Schedule 감사 보고서

- 작성일: 2026-04-28
- 대상: `config/celery.py` `app.conf.beat_schedule` (135-807행)
- 타임존: `CELERY_TIMEZONE = 'America/New_York'` (ET) — 모든 crontab은 ET 기준
- 모드: 읽기 전용 감사 (코드 수정 없음)

> ⚠️ **중요 전제**: `config/settings.py`의 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 설정으로 실제 스케줄은 `django_celery_beat.PeriodicTask` DB 테이블이 진실의 소스다. 이 보고서는 **선언된 의도(reference dict)** 기준 분석이며, 실제 DB 상태와의 drift 가능성이 있다 (celery.py 117-133행 주석 참조).

---

## 1. 요약 (Executive Summary)

| 항목 | 결과 |
|------|------|
| 총 등록된 beat 엔트리 | **78개** |
| Neo4j 큐 라우팅 태스크 | 14개 (task_routes 기반 + options 직접 라우팅 5개 중복 포함) |
| 5분 이하 주기 태스크 | 3개 (`refresh-market-pulse-cache` 1분, `sec-sync-dirty-neo4j` 5분, `update-realtime-prices` 5분, `update-market-indices` 5분) |
| **P0 위험 (즉시 조치)** | 4건 (12시 정각 동시 폭주 / 18시 정각 EOD 폭주 / Gemini :30 배치 RPM 초과 위험 / sec-sync expires<주기) |
| **P1 위험 (점검 필요)** | 5건 (FMP 09-16시 5분 윈도우 / 1일 03시 LLM 500콜 / Neo4j queue solo 적체 / 의존 chain gap / drift 누적) |

---

## 2. 시간대별 ASCII 히트맵 (평일 ET)

태스크 실행 횟수(시간당)를 막대로 표시. 시장 개장 시간(09-16시)은 매분/매5분/매10분 반복 태스크가 누적된다.

```
시  태스크/h  Neo4j Q/h  주요 이벤트
────────────────────────────────────────────────────────────────────────────
00  ███         █████████████      sec*12 + alerts*2 + neo4j-hc
01  █                              economic-calendar(daily) | weekly-agg(Sat)
02  ██                             sp500-constituents(1st) + archive(1st) + chainsight-profiles(Sat)
03  ████        ▓                  korean-overview(1st,LLM 500콜!) + supply(15th) + ML-train(Sun) + co-movement(Sat)
04  ██████      █████████████      cleanup-news-rel + 13F(16th) + reg(Mon) + patent(1st) + ML*4(Sun) + chainsight*3(Sat) + neo4j-dirty(Sun)
05  ███         █████████████      enrich(LLM,daily,neo4j) + validation(Sat) + cleanup-results(Sun)
06  █████       █████████████      daily-news + sp500-news-fmp(0615) + cat-high + general-fmp(0645) + ETF(Mon) + filings(1st) + neo4j-hc
07  █████                          digest + heat-score + cat-medium + market-movers + cat-low + press-fmp
08  █████       █████████████      keyword-pipeline(LLM) + market-news + classify(LLM,:15) + analyze-deep(LLM,:30) + sync-news-neo4j(:45)
09  ██▓▓▓▓▓▓▓   ████████████       sentiment + relations | +60 cache, +12 real, +12 indices, +6 portfolio, +4 alerts/h
10  ███▓▓▓▓▓▓   █████████████      classify+analyze+sync(LLM*2 :15/:30) + sp500-news-fmp(1015) + co-mentions
11  █▓▓▓▓▓▓▓    █████████████      relation-confidence | + 시장 반복
12  ██████▓▓▓▓  █████████████████  ⚠️ market-news + econ + sec-seed + chainsight-prof-neo4j + neo4j-hc + classify + general-fmp + relations-neo4j + analyze(LLM) + sync-news + 시장반복
13  ██▓▓▓▓▓▓    █████████████      cat-high + sp500-news-fmp(1315) + 시장반복
14  ████▓▓▓▓    █████████████      cat-medium + classify(LLM) + daily-news-pm + analyze(LLM) + sync-neo4j + 시장반복
15  ██▓▓▓▓▓▓    █████████████      market-news + sp500-news-fmp(1515) + 시장반복
16  █████▓▓▓▓   █████████████      ⚠️ classify + breadth + analyze(LLM,:30) + sector-heat + extract-kw(LLM,:45) + sync-news + 시장 마지막 시간
17  ████        █                  daily-prices + cat-high-evening + sp500-news-fmp(1715) + general-fmp(1745)
18  ███████████ █████████████████  ⚠️ thesis*3 + sp500-EOD(FMP 500종목!) + change-pct + econ + market-news + classify + analyze(LLM) + sync-news + neo4j-hc + run-eod-pipeline
19  ██                             backfill-signal-accuracy + ml-labels
20  █                              ⚠️ sp500-financials (FMP, 101종목 × 6 endpoint = 606콜)
21              █████████████      sec*12 + alerts*2
22  █                              economic-indicators(FRED)
23              █████████████      sec*12

▓ = 시장시간(09-16시) 반복 태스크 누적: cache 60/h + realtime 12/h + indices 12/h + portfolio 6/h + alerts 4/h
█ Neo4j Q: sec-sync-dirty-neo4j 매5분 = 12/h (지속). 12시/18시는 +health-check + chainsight-sync 2개 추가로 spike
```

**피크 시간대 식별:**
1. **18:00-18:45** (가장 심각, 점수 11+): 장 마감 EOD 폭주
2. **12:00-12:45** (점수 8+): 정오 동시 폭주
3. **16:15-16:45** (점수 7): Gemini 2회 + EOD 사전 작업
4. **08:00-08:45** (점수 6): LLM chain 시작
5. **20:00** (점수 1이지만 단일 태스크 콜 수 600+): FMP financials 배치
6. **매월 1일 03:00** (점수 3, LLM 500콜): Korean overview 폭증

---

## 3. Rate Limit 초과 구간 분석

### 3-1. FMP (Starter 300 calls/min)

| 시간 | 동시 실행 FMP 의존 태스크 | 추정 콜 수/분 | 위험도 |
|------|---------------------------|---------------|--------|
| **09-16시 매 :00, :05, :10, :15…** | `update-realtime-prices` (S&P 500 분량) + `update-market-indices` | 종목당 1콜 가정 시 **500+** | **P0 가능성** |
| **12:30** | `collect-general-news-fmp-noon` + 12시 누적 | ~100-200 | P1 |
| **17:15** | `collect-sp500-news-fmp-1715` (orchestrator) | 다수 | P1 |
| **17:45** | `collect-general-news-fmp-evening` + 17:15 carryover | 중복 | P1 |
| **18:00** | `sync-sp500-eod-prices` (S&P 500 EOD) + `update-economic-indicators`(FRED, 별도) | 약 500콜 burst | **P0** |
| **20:00** | `sync-sp500-financials` 101종목 × 6 endpoint | **606콜 (병렬 호출 시 분당 한도 위협)** | **P0** |
| **매 :15분 정각 (06,10,13,15,17)** | `collect-sp500-news-fmp-*` orchestrator 시리즈 | 종목당 호출 | P1 |

**P0 — 09-16시 매 5분 윈도우**: `update-realtime-prices` (S&P 500 가정)와 `update-market-indices`가 같은 분에 중복 큐잉. `default` 큐가 단일 워커일 경우 직렬 처리되어 실시간성 훼손 + retry 시 다음 5분 작업과 겹침.

**P0 — 18:00 정각**: `sync-sp500-eod-prices` 단일 태스크가 500종목을 sequential로 호출하면 분당 300 한도 미달이지만, 같은 시각에 `thesis-update-readings`(FMP 가능성)·`update-economic-indicators`(FRED)·`collect-market-news-evening`(외부 News API)이 동시 실행되어 워커·DB connection 경합 발생.

**P0 — 20:00 sp500-financials**: 101종목 × 6 endpoint = 약 606콜. `FMP_RATE_LIMIT` 조정 또는 배치 내 자체 throttle 검증 필요. 302 (Premium 심볼) 발생 시 `FMPPremiumError` 즉시 실패 패턴(common-bugs #23) 적용 여부도 확인 필요.

### 3-2. Gemini Free Tier (15 RPM, 1500 RPD)

**RPM 위험 (15회/분):**

| 시각 (ET) | 동시/근접 LLM 태스크 | 추정 콜/분 | 위험도 |
|-----------|---------------------|------------|--------|
| **08:00** | `keyword-generation-pipeline` (Gainers) | ~10-20 | P1 |
| **08:15 / 10:15 / 12:15 / 14:15 / 16:15 / 18:15** | `classify-news-batch` (3시간 분량) | 단일 태스크 내 batched | P1 |
| **08:30 / 10:30 / 12:30 / 14:30 / 16:30 / 18:30** | `analyze-news-deep-batch` (max_articles=50) | **50콜 burst (15 RPM × 3-4분 분산 필요)** | **P0** |
| **16:30 + 16:45** | analyze-deep + extract-daily-news-keywords | 15분 gap 의도적 분리 (주석 명시) ✅ 완화됨 | OK |
| **05:30** | `enrich-relationship-keywords` (limit=100) | 100콜 burst → 약 7분 소요 | P1 |
| **09:00** | `extract-news-relations` | LLM 가능성 | P1 |

**P0 — analyze-news-deep-batch :30 슬롯**: max_articles=50인데 Gemini 15 RPM이면 50콜 처리에 약 3.5분 소요. 태스크 내 self-throttle이 없으면 429 에러 다발. 다음 사이클(2시간 후) 재시도가 누적되면 RPD 한도 압박.

**RPD 위험 (1500/일):**

평일 1일 추정 LLM 콜:
```
classify-news-batch    × 6회 ×  ~30콜 = ~180
analyze-news-deep-batch× 6회 ×  ~50콜 = ~300
keyword-pipeline       × 1회 ×  ~50콜 = ~50
extract-news-keywords  × 1회 ×  ~50콜 = ~50
extract-news-relations × 1회 ×  ~50콜 = ~50
enrich-relation-kw     × 1회 × ~100콜 = ~100
chainsight 관련 태스크  ×          ~30콜 = ~30
─────────────────────────────────────────
일상 평일 합계                       ~760 (1500 한도 51%)
```

**매월 1일 03:00 — `refresh-korean-overviews-monthly`**: S&P 500 종목 한글 개요 = **500콜 burst**. 일상 760 + 500 = 1260 → 1500 RPD 한도 84%. 03시 다른 LLM 작업과 충돌 시 한도 초과 가능. **분할 실행 또는 Pro 티어 검토 필요.**

### 3-3. Alpha Vantage (5 calls/min, 500/day)

`config/celery.py` beat_schedule 내에서 직접 AV를 호출하는 태스크는 **명시적으로 발견되지 않음**. AV 의존성은 `API_request/` 내부에서 fallback 경로로 사용될 가능성이 있으며, beat 레벨 스케줄로는 등록되지 않았다. Alpha Vantage 태스크가 다른 ad-hoc 흐름에서 호출되는지 별도 audit 권고.

---

## 4. Queue 몰림 분석

### 4-1. Neo4j 큐 (solo pool, 동시 1개만 처리)

`config/celery.py` 36-55행 task_routes 기준 + options 직접 라우팅(214/368/375/590/752행).

**상시 부하 (default 워커와 별개로 시간당 12회 sec-sync-dirty 고정):**

| 태스크 | 주기 | 시간당 콜 |
|--------|------|----------|
| `sec-sync-dirty-neo4j` | 5분마다 | **12** |
| `neo4j-health-check` | 6시간마다 (00, 06, 12, 18시 :00) | 1/6h |

**스파이크 시간대:**

- **12:00 정각**: `sec-sync-dirty-neo4j` + `neo4j-health-check` + `chainsight-sync-profiles-neo4j` = 3개 동시 큐잉 → solo 처리로 직렬화 → 마지막 작업이 5분 후 다음 sec-sync에 밀림
- **12:30**: `chainsight-sync-relations-neo4j` + `sec-sync` 5분 카운트 = 2개
- **12:45**: `sync-news-to-neo4j` + `sec-sync` = 2개 (8/10/14/16/18시도 동일)
- **18:00**: `neo4j-health-check` + `sec-sync` = 2개
- **18:45**: `sync-news-to-neo4j` + `sec-sync` = 2개 (이 직전 18:30 EOD 폭주의 잔여 작업이 default 큐에서 처리 중일 가능성)

**P0 — `sec-sync-dirty-neo4j` expires=240 (4분) vs 주기 300초 (5분)**:
solo 큐에서 직전 sec-sync가 4분 이상 걸리면 다음 작업이 만료되어 손실. dirty evidence 누적 → 다음 사이클에서 갑자기 큰 batch → 더 오래 걸림 → 무한 적체.
또한 12시·18시처럼 다른 neo4j 작업과 동시 실행되면 sec-sync 처리가 다음 5분 윈도우를 넘기기 쉬움.

### 4-2. Default 큐

평일 09-16시 시간당 추정 ≥110 태스크 (대부분 cache/계산). 단, 대다수는 짧은 작업이라 default 큐 단일 워커로 처리 가능 추정. 단:

- **18:00-18:45**: `sync-sp500-eod-prices` + `thesis-update-readings` + `update-economic-indicators` + `collect-market-news-evening` + `classify-news` + `analyze-news-deep` (LLM 3-4분) + `run-eod-pipeline` + `update-sp500-change-percent` + `thesis-calculate-scores` + `thesis-create-snapshots` = **default 큐 적체 위험**
- **20:00**: `sync-sp500-financials` 단일 장기 태스크가 다음 sec-sync 또는 22시 econ 태스크와 겹칠 수 있음 (606콜 sequential 시 10분+).

---

## 5. 스케줄 의존성 / 순서 위험

### 5-1. EOD 의존 chain (18:00-19:00)

선언된 순서:
```
17:00 update-daily-prices (FMP)
18:00 sync-sp500-eod-prices (FMP, 메인)
18:00 thesis-update-readings   ← 동시 실행. EOD 가격 미반영 가능
18:15 thesis-calculate-scores  ← 18:00 readings 완료 가정
18:30 thesis-create-snapshots  ← 18:15 scores 완료 가정
18:30 run-eod-pipeline         ← 18:00 EOD prices 완료 가정
19:00 backfill-signal-accuracy ← 18:30 EOD pipeline 완료 가정
```

**P1 위험**:
- `thesis-update-readings`(18:00)가 `sync-sp500-eod-prices`(18:00)와 동시 시작. EOD 가격을 입력으로 쓴다면 **stale 데이터**로 계산됨.
- `run-eod-pipeline`(18:30)이 `sync-sp500-eod-prices`(18:00 시작) 30분 안에 끝났다는 가정. 500종목 시퀀셜이면 30분 초과 가능 → 부분 데이터로 EOD 계산.
- 의존성을 chord/chain으로 묶지 않고 단순 시각 분리 → 시간 초과 시 무방비.

### 5-2. News Intelligence chain (8/10/12/14/16/18시 :15→:30→:45)

```
:15 classify-news-batch  (LLM, 3시간 분량)
:30 analyze-news-deep    (LLM, max=50)
:45 sync-news-to-neo4j   (Neo4j queue)
```

**P1 위험**:
- :15 classify가 30콜 × 4초 = 120초 처리라 :30 전 완료 가능. 단 RPM 한도로 지연 시 :30 analyze가 미분류 데이터로 시작.
- :30 analyze의 50콜 burst가 15 RPM 처리로 약 3.5분 소요 → :45 neo4j-sync가 미분석 데이터 동기화.
- 정확한 입력 검증 없이 시각만 어긋나면 누적 손실 발생.

### 5-3. Chain Sight 일일 chain (10:00-12:30)

```
10:00 chainsight-co-mentions      (뉴스 7일치 분석)
11:00 chainsight-relation-confidence (CoMention 후 갱신)
12:00 chainsight-sync-profiles-neo4j (관계 갱신 후 동기화)
12:30 chainsight-sync-relations-neo4j (프로파일 후)
```

선후 분리는 1시간 gap으로 안전 추정. 단 12:00 동시 다른 태스크 폭주(섹션 4-1)로 sync-profiles가 밀리면 12:30 sync-relations와 직렬 처리 시간 초과 가능.

### 5-4. Drift 위험 (config dict ↔ DB)

celery.py 117-133행 주석:
> "config dict와 DB PeriodicTask가 어긋나면 dict의 태스크는 실행되지 않는다."

2026-04-24 복구 사례 — `chainsight-heat-score-daily`, `sec-seed-relations-to-chainsight` 누락 발견. **주기적 diff 자동화 부재** 자체가 P1 운영 위험. dict 업데이트가 DB에 반영되지 않은 신규 태스크를 잠재적으로 분석에서 누락 가능.

---

## 6. 시간대별 상세 충돌 매트릭스

### 6-1. 12:00 정각 (P0)

| 태스크 | 큐 | 외부 의존 | 비고 |
|--------|-----|---------|------|
| `collect-market-news-noon` | default | News API | |
| `update-economic-indicators` | default | FRED | |
| `sec-seed-relations-to-chainsight` | default | DB | |
| `chainsight-sync-profiles-neo4j` | **neo4j** | DB→Neo4j | |
| `neo4j-health-check` | **neo4j** | Neo4j ping | 6시간마다 |
| `sec-sync-dirty-neo4j` | **neo4j** | Neo4j | 매5분 |
| `update-realtime-prices` | default | FMP | 매5분 (12:00 hit) |
| `update-market-indices` | default | FMP | 매5분 (12:00 hit) |
| `calculate-portfolio-values` | default | DB | 매10분 (12:00 hit) |
| `refresh-market-pulse-cache` | default | DB | 매분 |
| `check-screener-alerts` | default | DB | 매15분 (12:00 hit) |
| `check-pipeline-alerts` | default | DB | 매30분 (12:00 hit) |

**문제**:
- Neo4j queue 3개 직렬 처리 → solo pool에서 sync-profiles가 health-check 뒤에 밀림
- Default queue 7개 + 12:15 classify 추가까지 → 워커 1개일 시 적체

### 6-2. 18:00 정각 (P0, 가장 심각)

| 태스크 | 큐 | 외부 의존 | 비고 |
|--------|-----|---------|------|
| `thesis-update-readings` | default | DB+FMP? | EOD 의존 |
| `sync-sp500-eod-prices` | default | **FMP 500종목** | 메인 EOD 작업 |
| `update-economic-indicators` | default | FRED | |
| `collect-market-news-evening` | default | News API | |
| `neo4j-health-check` | **neo4j** | Neo4j | 6시간마다 |
| `sec-sync-dirty-neo4j` | **neo4j** | Neo4j | 매5분 |

이어서 18:15 (`thesis-calculate-scores`, `classify-news-batch`), 18:30 (`thesis-create-snapshots`, `run-eod-pipeline`, `update-sp500-change-percent`, `analyze-news-deep`), 18:45 (`sync-news-to-neo4j`)가 연쇄.

**문제**:
- 단일 default 워커일 경우 18:00 작업이 18:15 작업 시작 전 완료 어려움
- `sync-sp500-eod-prices`가 18:30 `run-eod-pipeline` 시작 전 완료 보장 없음 (chord/chain 미사용)
- LLM `analyze-news-deep` 50콜이 18:33-18:36 점유 → 18:45 sync-news-to-neo4j는 미완 데이터 동기화 위험

### 6-3. 매월 1일 03:00-06:00 (P1)

매월 1일 새벽 3시간 동안 다음 누적:
- 02:00 sync-sp500-constituents
- 02:30 archive-old-articles
- 03:00 cleanup-old-macro-data (일요일과 겹침 가능)
- 03:00 **refresh-korean-overviews-monthly** (LLM 500콜)
- 03:00 sync-supply-chain-batch (15일에만 — 다른 날)
- 04:00 cleanup-expired-news-relationships
- 04:00 sync-institutional-holdings (16일에만)
- 04:00 scan-regulatory-relationships (월요일에만)
- 04:30 build-patent-network (1일에)
- 05:30 enrich-relationship-keywords (LLM 100콜)
- 06:00 sec-check-new-filings (1일에)

**문제**:
- 1일이 일요일과 겹치면 03:00에 ML 재학습 + Korean overview + macro cleanup 동시
- 03:00 LLM 500콜이 RPD 1500 한도 33% 한 번에 소모 → 일중 다른 LLM 태스크 영향

---

## 7. 권고 (코드 변경 없이 가능한 액션 위주)

### 즉시 (P0)
1. **18:00 EOD chain을 Celery chord/group으로 묶기** — `sync-sp500-eod-prices.s() | run-eod-pipeline.s() | backfill_signal_accuracy.s()` 형태. 시각 기반 의존성 → 명시적 의존성으로 전환.
2. **`sec-sync-dirty-neo4j` expires=240을 270 이상으로 검토** 또는 주기를 7-10분으로 완화. solo 큐 적체 방지.
3. **`analyze-news-deep-batch` 내부 self-throttle 검증** — Gemini 15 RPM 준수 위해 콜 간 4초 sleep 또는 `rate_limit='15/m'` 데코레이터 적용.
4. **`update-realtime-prices`가 실제 호출하는 종목 수 측정** — S&P 500 전체라면 5분 주기 + 300/min 한도 충돌 여부 즉시 검증.

### 점검 (P1)
5. **매월 1일 LLM 폭주 분산** — `refresh-korean-overviews-monthly`를 1일 03:00 단일 실행 대신 매주 토요일 25%씩 4주 분산 또는 Pro 티어 전환.
6. **Drift 자동 감지** — celery.py 주석에 명시된 `set(PeriodicTask) vs config dict` diff를 GitHub Actions 또는 daily Celery 태스크로 자동화.
7. **Neo4j queue 부하 시각화** — 12:00, 18:00 정각 sec-sync 처리 시간 메트릭 수집.
8. **20:00 `sync-sp500-financials` 분할** — 101종목 × 6 endpoint를 5분 chunked 배치로 분산.
9. **`thesis-update-readings`가 sync-sp500-eod-prices에 의존하는지 확인** — 의존하면 18:00→18:10으로 시각 시프트 또는 chain으로 묶기.

---

## 8. 부록 — 전체 태스크 목록 (시각 정렬)

| 시각 | 태스크 | 주기 | 큐 | 외부 의존 |
|------|--------|------|-----|---------|
| 매분 | refresh-market-pulse-cache | 9-16시 평일 | default | - |
| 매5분 | sec-sync-dirty-neo4j | 24h | **neo4j** | Neo4j |
| 매5분 | update-realtime-prices | 9-16시 평일 | default | FMP |
| 매5분 | update-market-indices | 9-16시 평일 | default | FMP |
| 매10분 | calculate-portfolio-values | 9-16시 평일 | default | - |
| 매15분 | check-screener-alerts | 9-16시 평일 | default | - |
| 매30분 | check-pipeline-alerts | 24h | default | - |
| 6시간 | neo4j-health-check | 0/6/12/18 :00 | **neo4j** | Neo4j |
| 01:00 | update-economic-calendar | daily | default | FMP |
| 01:00 | aggregate-weekly-prices | Sat | default | - |
| 02:00 | chainsight-all-profiles | Sat | default | - |
| 02:00 | sync-sp500-constituents | 1st | default | FMP |
| 02:30 | archive-old-articles | 1st | default | - |
| 03:00 | cleanup-old-macro-data | Sun | default | - |
| 03:00 | refresh-korean-overviews-monthly | 1st | default | **Gemini 500콜** |
| 03:00 | chainsight-price-co-movement | Sat | default | - |
| 03:00 | sync-supply-chain-batch | 15th | default | SEC |
| 03:00 | train-importance-model | Sun | default | - |
| 03:30 | generate-shadow-report | Sun | default | - |
| 04:00 | cleanup-expired-news-relationships | daily | **neo4j** | Neo4j |
| 04:00 | sync-institutional-holdings | 16th | default | SEC |
| 04:00 | scan-regulatory-relationships | Mon | default | SEC |
| 04:00 | check-auto-deploy | Sun | default | - |
| 04:00 | chainsight-stale-decay | Sat | default | - |
| 04:15 | generate-weekly-ml-report | Sun | default | - |
| 04:20 | monitor-ml-performance | Sun | default | - |
| 04:30 | train-lightgbm-model | Sun | default | - |
| 04:30 | build-patent-network | 1st | default | - |
| 04:30 | chainsight-aggregate-profiles | Sat | default | - |
| 04:30 | chainsight-neo4j-dirty-sync | Sun | **neo4j** | Neo4j |
| 05:00 | validation-weekly-batch | Sat | default | - |
| 05:00 | cleanup-task-results | Sun | default | - |
| 05:30 | enrich-relationship-keywords | daily | **neo4j** | Gemini, Neo4j |
| 06:00 | collect-daily-news-morning | weekday | default | News API |
| 06:00 | sync-etf-holdings | Mon | default | 외부 |
| 06:00 | sec-check-new-filings | 1st | default | SEC |
| 06:15 | collect-sp500-news-fmp-0615 | weekday | default | FMP |
| 06:30 | collect-category-news-high-morning | weekday | default | News API |
| 06:45 | collect-general-news-fmp-morning | weekday | default | FMP |
| 07:00 | celery-error-digest | daily | default | - |
| 07:00 | chainsight-heat-score-daily | daily | default | - |
| 07:00 | collect-category-news-medium-morning | weekday | default | News API |
| 07:30 | sync-daily-market-movers | weekday | default | FMP |
| 07:30 | collect-category-news-low | weekday | default | News API |
| 07:45 | collect-press-releases-fmp | weekday | default | FMP |
| 08:00 | keyword-generation-pipeline | daily | default | **Gemini** |
| 08:00 | collect-market-news-morning | weekday | default | News API |
| 08:15 | classify-news-batch | weekday 8-18:15 (2h) | default | **Gemini** |
| 08:30 | analyze-news-deep-batch | weekday 8-18:30 (2h) | default | **Gemini 50콜** |
| 08:45 | sync-news-to-neo4j | weekday 8-18:45 (2h) | **neo4j** | Neo4j |
| 09:00 | aggregate-daily-sentiment | weekday | default | - |
| 09:00 | extract-news-relations | daily | default | LLM 가능 |
| 10:00 | chainsight-co-mentions | daily | default | - |
| 10:15 | collect-sp500-news-fmp-1015 | weekday | default | FMP |
| 11:00 | chainsight-relation-confidence | daily | default | - |
| 12:00 | collect-market-news-noon | weekday | default | News API |
| 12:00 | update-economic-indicators | weekday 6/12/18/22 | default | FRED |
| 12:00 | sec-seed-relations-to-chainsight | daily | default | - |
| 12:00 | chainsight-sync-profiles-neo4j | daily | **neo4j** | Neo4j |
| 12:30 | collect-general-news-fmp-noon | weekday | default | FMP |
| 12:30 | chainsight-sync-relations-neo4j | daily | **neo4j** | Neo4j |
| 13:00 | collect-category-news-high-midday | weekday | default | News API |
| 13:00 | chainsight-seed-selection | daily | default | - |
| 13:15 | collect-sp500-news-fmp-1315 | weekday | default | FMP |
| 14:00 | collect-category-news-medium-afternoon | weekday | default | News API |
| 14:30 | collect-daily-news-afternoon | weekday | default | News API |
| 15:00 | collect-market-news-afternoon | weekday | default | News API |
| 15:15 | collect-sp500-news-fmp-1515 | weekday | default | FMP |
| 16:30 | calculate-market-breadth | weekday | default | - |
| 16:35 | calculate-sector-heatmap | weekday | default | - |
| 16:45 | extract-daily-news-keywords | daily | default | **Gemini** |
| 17:00 | update-daily-prices | weekday | default | FMP |
| 17:00 | collect-category-news-high-evening | weekday | default | News API |
| 17:15 | collect-sp500-news-fmp-1715 | weekday | default | FMP |
| 17:45 | collect-general-news-fmp-evening | weekday | default | FMP |
| 18:00 | thesis-update-readings | weekday | default | DB+? |
| 18:00 | sync-sp500-eod-prices | weekday | default | **FMP 500종목** |
| 18:00 | collect-market-news-evening | weekday | default | News API |
| 18:15 | thesis-calculate-scores | weekday | default | - |
| 18:30 | thesis-create-snapshots | weekday | default | - |
| 18:30 | run-eod-pipeline | weekday | default | - |
| 18:30 | update-sp500-change-percent | weekday | default | - |
| 19:00 | backfill-signal-accuracy | weekday | default | - |
| 19:00 | collect-ml-labels | weekday | default | - |
| 20:00 | sync-sp500-financials | weekday | default | **FMP 606콜** |
| 22:00 | update-economic-indicators | weekday | default | FRED |

---

## 9. 검증 명령 (운영 측 후속 작업)

```bash
# 실제 DB 등록 태스크 vs config dict diff (drift 점검)
poetry run python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
from config.celery import app
db = set(PeriodicTask.objects.values_list('name', flat=True))
cfg = set(app.conf.beat_schedule.keys())
print('DB only:', db - cfg)
print('Config only:', cfg - db)
"

# 각 태스크의 실제 평균 실행 시간 측정 (Flower 또는 result backend 조회)
# - 18:00 sync-sp500-eod-prices duration < 30min 확인
# - sec-sync-dirty-neo4j duration < 240s 확인
# - analyze-news-deep-batch duration < 30min 확인

# Gemini 일일 콜 수 추적 (LLM 클라이언트 메트릭)
# - 매월 1일 RPD 1500 한도 근접 모니터링
```

---

**EOR — 감사 종료. 코드 수정 없음.**
