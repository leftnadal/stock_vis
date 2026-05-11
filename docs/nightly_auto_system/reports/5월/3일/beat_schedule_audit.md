# Celery Beat 스케줄 감사 보고서

- 감사 대상: `config/celery.py` `app.conf.beat_schedule` (총 70개 항목)
- 시간대 기준: `CELERY_TIMEZONE = 'America/New_York'` (ET)
- 감사 일자: 2026-05-04
- 모드: 읽기 전용 (코드 수정 없음)

> ⚠️ **중요**: `config/celery.py:118-134` 주석대로, 이 dict는 **런타임에 무시**된다.
> 실제 스케줄러는 `django_celery_beat.PeriodicTask` DB 테이블을 진실의 소스로 사용한다.
> 본 감사는 "선언된 의도"(코드의 dict)를 분석한 것이며, DB의 실제 등록 상태와 drift가 있는지는 별도 점검이 필요하다.

---

## 0. 분석 범위 요약

| 카테고리 | 태스크 수 | 비고 |
|---------|---------|------|
| 인터벌(분 단위) 폴러 | 7개 | `*/1`, `*/5`, `*/10`, `*/15`, `*/30` |
| 평일 디스크리트 배치 | 47개 | M-F 특정 시각 |
| 매일 디스크리트 배치 | 9개 | 7-day |
| 주간 배치 (Mon/Sat/Sun) | 8개 | |
| 월간 배치 (1일, 15일, 16일) | 6개 | |
| **총계** | **70개** | (추정, 신규 항목 수동 카운트) |

**큐 분포:**
- `default` 큐: 약 56개
- `neo4j` 큐: 14개 (solo pool 직렬 실행)

---

## 1. Rate Limit 초과 위험 분석

### 1.1 FMP Starter Plan (300 calls/min)

**FMP 의존 태스크 매핑:**

| 시각(ET) | 태스크 | 추정 호출량 | 위험도 |
|---------|--------|-----------|--------|
| `*/5 9-16 M-F` | `update-realtime-prices` | 배치 quote (1~수회/분) | 🟡 중 |
| `*/5 9-16 M-F` | `update-market-indices` | 인덱스 5~10개 quote | 🟢 저 |
| `06:15 M-F` | `collect-sp500-news-fmp-0615` (orchestrator) | **~500 콜 (S&P 500 fan-out)** | 🔴 고 |
| `06:45 M-F` | `collect-general-news-fmp-morning` | 1~5 | 🟢 저 |
| `07:30 M-F` | `sync-daily-market-movers` | 5~10 | 🟢 저 |
| `07:45 M-F` | `collect-press-releases-fmp` (max_symbols=50) | **~50** | 🟡 중 |
| `10:15 M-F` | `collect-sp500-news-fmp-1015` | **~500** | 🔴 고 |
| `12:30 M-F` | `collect-general-news-fmp-noon` | 1~5 | 🟢 저 |
| `13:15 M-F` | `collect-sp500-news-fmp-1315` | **~500** | 🔴 고 |
| `15:15 M-F` | `collect-sp500-news-fmp-1515` | **~500** | 🔴 고 |
| `17:00 M-F` | `update-daily-prices` | **~500** | 🔴 고 |
| `17:15 M-F` | `collect-sp500-news-fmp-1715` | **~500** | 🔴 고 |
| `17:45 M-F` | `collect-general-news-fmp-evening` | 1~5 | 🟢 저 |
| `18:00 M-F` | `sync-sp500-eod-prices` | **~500** | 🔴 고 |
| `18:00 M-F` | `thesis-update-readings` | 알 수 없음 (지표별 호출) | 🟡 중 |
| `20:00 M-F` | `sync-sp500-financials` | **101 종목 × 4 statement = ~400 콜/일** | 🔴 고 |
| `01:00 daily` | `update-economic-calendar` (FMP/FRED 혼합) | 1~5 | 🟢 저 |

**🔴 핵심 발견 (FMP):**

1. **17:00~18:00 ET 1시간 윈도우에 S&P 500 fan-out 3건 연속**:
   - 17:00 `update-daily-prices` (~500)
   - 17:15 `collect-sp500-news-fmp-1715` (~500)
   - 18:00 `sync-sp500-eod-prices` (~500)
   - 18:00 `thesis-update-readings` (지표별 추가 호출)
   - **평균 분당 호출량 가정**: 1500+ 콜이 60분에 분포 → 25 cps 평균은 안전하지만, **태스크 시작 직후 burst가 300/min을 초과할 수 있음**.
   - 검증 필요: orchestrator가 내부적으로 throttle/배치 처리하는지 (`news/services/fmp_news_provider.py` 등 실 구현 확인).

2. **주간 5회 발생하는 SP500 뉴스 orchestrator** (`06:15, 10:15, 13:15, 15:15, 17:15`):
   - 5 × ~500 = 2500 콜/일을 단 5회에 집중. orchestrator가 동기 fan-out이면 분당 한도를 즉시 초과.
   - Starter 300/min 가정 시, 500 콜 처리 = 최소 100초 직렬 실행 필요.

3. **장중 5분 인터벌 burst (`*/5 9-16`)**:
   - `update-realtime-prices` + `update-market-indices` 두 태스크가 동일 minute(:00, :05, …, :55)에 동시 fire.
   - 두 태스크가 모두 batch quote API(`/quote/{symbols}` 콤마 구분)를 사용한다면 콜 수는 각 1~3건/분으로 안전.
   - **개별 종목 API를 사용하면 위험**: 검증 필요.

4. **월 1회 monthly burst** (1일):
   - 02:00 `sync-sp500-constituents` (~500)
   - 03:00 `refresh-korean-overviews-monthly` (Gemini 500 콜)
   - 04:30 `build-patent-network` (USPTO/SEC)
   - 06:00 `sec-check-new-filings` (SEC)
   - FMP는 02:00에 단일 burst라 다른 API와 분리되어 있어 비교적 안전.

**권장 검증 포인트:**
- `serverless/tasks.py` 의 `sync_daily_market_movers`, `collect_sp500_news_fmp_orchestrator` 등이 내부 throttle 사용 여부
- `stocks/tasks.py` 의 `update_realtime_with_provider`, `sync_sp500_eod_prices`, `sync_sp500_financials` 호출 방식 (bulk vs per-symbol)

### 1.2 Gemini Free (15 RPM, 1500 RPD)

**Gemini 의존 태스크 매핑:**

| 시각(ET) | 태스크 | 추정 일일 콜 | 위험도 |
|---------|-------|------------|-------|
| `05:30 daily` | `enrich-relationship-keywords` (limit=100) | **~100** | 🟡 중 |
| `08:00 daily` | `keyword-generation-pipeline` (gainers) | ~10~30 | 🟢 저 |
| `08:30, 10:30, 12:30, 14:30, 16:30, 18:30 M-F` | `analyze-news-deep-batch` (max_articles=50) | **6 × 50 = 300** | 🔴 고 |
| `08:15, 10:15, 12:15, 14:15, 16:15, 18:15 M-F` | `classify-news-batch-morning` (rule + ?) | (룰 우선, Gemini 폴백 시 6×N) | 🟡 중 |
| `09:00 daily` | `extract-news-relations` | (regex 기반 가능, 검증 필요) | 🟡 중 |
| `10:00 daily` | `chainsight-co-mentions` (days_back=7) | 알 수 없음 | 🟡 중 |
| `16:45 daily` | `extract-daily-news-keywords` | ~30~50 | 🟡 중 |
| `1일 03:00 monthly` | `refresh-korean-overviews-monthly` | **~500** (S&P 500) | 🔴 고 (월 1회) |

**🔴 핵심 발견 (Gemini):**

1. **이미 인지된 충돌 회피 사례** (`config/celery.py:286-289` 주석):
   > `16:30 EST analyze-news-deep-batch` ↔ `extract-daily-news-keywords` 가 Gemini 동시 호출 충돌 → 15분 분산하여 16:45로 이동 (audit P0 #8, 2026-04-26).
   - 잘 처리됨. 다른 시간대도 같은 패턴인지 확인 필요.

2. **주중 일일 RPD 추정**:
   - `analyze-news-deep-batch`: 6 × 50 = **300 콜/일** (가장 큰 소비자)
   - `classify-news-batch`: 6 × 미상 (룰 엔진 우선이면 최소, Gemini 폴백 비율에 따라 +0 ~ +300)
   - `enrich-relationship-keywords`: 100
   - `chainsight-co-mentions`, `extract-news-relations`: 미상
   - `keyword-generation-pipeline`, `extract-daily-news-keywords`: ~50
   - **총합 추정: 500~900 콜/일**, 1500 RPD 한도 내. 단, classify가 Gemini 폴백을 적극 사용하면 한도 도달 가능.

3. **15 RPM 동시 호출 위험 윈도우**:
   - `08:15 classify-news-batch-morning` + `08:30 analyze-news-deep-batch` (15분 간격, 안전 마진 충분)
   - `18:15 classify` + `18:30 analyze-deep` + `18:30 thesis-create-snapshots` (Gemini 미사용 추정) — 안전
   - **`18:30 analyze-deep` (50 articles, ~3.3분 소요 가정) + `18:45 sync-news-to-neo4j` (Neo4j 큐, Gemini 무관)** — Gemini 충돌 없음
   - 실측 RPM은 `analyze_news_deep` 내부 throttle 구현 여부에 의존. 50 articles를 1분에 보내면 50 RPM = 한도 3배 초과 → 반드시 `time.sleep(4)` 류 throttle 필요.

4. **월간 burst (1일 03:00)**:
   - `refresh-korean-overviews-monthly` (~500 콜) — 1500 RPD 한도의 1/3 소비.
   - 같은 시각 `train-importance-model` (Sun-only)이 1일 일요일에 떨어지면 추가 부하 가능 (Gemini 미사용 추정).

### 1.3 Alpha Vantage (5 calls/min)

**현재 beat_schedule에는 AV 직접 호출 태스크가 없음.**

- macro/tasks.py의 `update_economic_indicators`는 FRED API 사용 (CLAUDE.md 주석 기준).
- AV 호출이 있다면 ad-hoc/on-demand 호출(API 화면에서 발동)일 가능성. 스케줄 차원에서는 AV 한도 초과 위험 없음.
- **확인 필요**: `API_request/alphavantage_*.py` 사용처와 호출 트리거 (스케줄러 외 경로).

---

## 2. Queue 몰림 분석

### 2.1 default 큐

대부분의 태스크. macOS에서는 `worker_pool='solo'` 강제(코드 30-31줄)로 직렬 실행되며, 프로덕션 Linux에서는 prefork(기본 worker 수만큼 병렬).

**peak 시점 (default 큐):**

| 시각(ET) | 동시 fire 태스크 | 부하 |
|---------|----------------|------|
| **18:00 M-F** | `collect-market-news-evening`, `update-economic-indicators`, `sync-sp500-eod-prices`, `thesis-update-readings` (4개 동시) | 🔴 |
| **18:30 M-F** | `analyze-news-deep-batch`, `run-eod-pipeline`, `update-sp500-change-percent`, `thesis-create-snapshots` (4개 동시) | 🔴 |
| **12:00 daily** | `collect-market-news-noon`, `update-economic-indicators`, `sec-seed-relations-to-chainsight` (+ market-hour intervals) | 🟡 |
| **04:00 Sun** | `cleanup-expired-news-relationships`(neo4j), `check-auto-deploy`, `train-importance-model` 직후 | 🟡 |
| **04:00 Mon** | `cleanup-expired` + `scan-regulatory-relationships` 동시 | 🟢 |

### 2.2 neo4j 큐 (solo pool, 동시 1개)

| 빈도 | 태스크 |
|-----|-------|
| `*/5` (모든 시간) | `sec-sync-dirty-neo4j` — **하루 288회** |
| 6시간마다 | `neo4j-health-check` |
| `04:00 daily` | `cleanup-expired-news-relationships` |
| `05:30 daily` | `enrich-relationship-keywords` (Gemini 호출 + Neo4j 기록) |
| `08:45, 10:45, 12:45, 14:45, 16:45, 18:45 M-F` | `sync-news-to-neo4j` (max_articles=100) |
| `12:00 daily` | `chainsight-sync-profiles-neo4j` |
| `12:30 daily` | `chainsight-sync-relations-neo4j` |
| `Sun 04:30` | `chainsight-neo4j-dirty-sync` |

**🔴 핵심 발견 (Neo4j 큐):**

1. **Solo pool + `sec-sync-dirty-neo4j` 5분 폴링 = 큐 점거**:
   - `sec-sync-dirty-neo4j` 1회가 5분을 초과하면, 다음 firing은 누적된다.
   - `expires=240` 설정으로 4분 이상 묵은 항목은 폐기되므로 **무한 누적은 방지**되나, 결과적으로 sync 누락 발생 가능.
   - 12:00~13:00 ET 윈도우: solo 큐에 4개 큰 태스크(`sync-profiles-neo4j` → `sync-relations-neo4j` → `sync-news-to-neo4j` → `enrich-relationship-keywords`는 05:30이라 미해당) + 12회 `sec-sync-dirty-neo4j` 직렬 실행 → **`sec-sync-dirty` 다수 폐기 가능성 높음**.

2. **05:30 `enrich-relationship-keywords` (Gemini + Neo4j)**:
   - 한 태스크에서 Gemini RPM 한도 + Neo4j 큐 점거 동시 발생.
   - `limit=100` × Gemini 호출(throttle 가정 4초/콜) = **400초 = 6.7분** 큐 점거.
   - 그 사이 `sec-sync-dirty-neo4j` 1~2회 폐기 가능.

3. **18:45 `sync-news-to-neo4j` (max_articles=100)**:
   - 18:30 `analyze-news-deep-batch`가 끝나야 의미 있는 데이터가 쌓임. 15분 간격은 빠듯.

### 2.3 Beat schedule drift 우려 (메타)

`config/celery.py:118-134` 주석:
> 2026-04-24 복구: 누락 상태였던 두 태스크를 DB에 등록 완료.
> Drift 재발 방지 체크는 수동.

- 현재 dict는 70개 정의. DB 등록 상태와 일치하는지는 본 감사 범위 밖.
- 권장: `python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(set(PeriodicTask.objects.values_list('name', flat=True)))"` 출력과 dict 키 set 차집합으로 drift 점검.

---

## 3. 시간대별 ASCII 히트맵

### 3.1 디스크리트 배치 태스크 수 (인터벌 폴러 제외, 평일 기준)

```
시각(ET) | n  | bar
---------+----+--------------------------------
00:00    |  0 |
01:00    |  1 | ▇
02:00    |  0 |
03:00    |  0 |
04:00    |  1 | ▇
05:00    |  1 | ▇
06:00    |  4 | ▇▇▇▇
07:00    |  6 | ▇▇▇▇▇▇
08:00    |  5 | ▇▇▇▇▇
09:00    |  2 | ▇▇
10:00    |  5 | ▇▇▇▇▇
11:00    |  1 | ▇
12:00    |  9 | ▇▇▇▇▇▇▇▇▇
13:00    |  3 | ▇▇▇
14:00    |  5 | ▇▇▇▇▇
15:00    |  2 | ▇▇
16:00    |  6 | ▇▇▇▇▇▇
17:00    |  4 | ▇▇▇▇
18:00    | 11 | ▇▇▇▇▇▇▇▇▇▇▇  ← 최고 피크
19:00    |  2 | ▇▇
20:00    |  1 | ▇
21:00    |  0 |
22:00    |  1 | ▇
23:00    |  0 |
```

**피크 분석:**
- **🔴 18:00 ET (11개)**: EOD 가격 sync + EOD 파이프라인 + Thesis 파이프라인 + News pipeline 18:00 슬롯 + 거시지표 업데이트가 한 시간에 응축. 60분 안에 11개 디스크리트 + 14개 인터벌 = **25개 firing**.
- **🟡 12:00 ET (9개)**: 점심 시간대 multi-pipeline 합류 (News, Macro, Chain Sight Neo4j sync, SEC seed). 시장 시간이라 인터벌 폴러까지 겹침.
- **🟡 07:00 ET (6개)**, **16:00 ET (6개)**: 시장 개장 직전 / 마감 직후 부하.

### 3.2 FMP 호출량 추정 히트맵 (평일, 일일)

```
시각(ET) | FMP 호출 추정     | bar
---------+------------------+----------------------------
06:00    |   ~500 (sp500-news) | ████████████████████
07:00    |   ~50 (press)       | ██
08:00    |    -                |
09:00    |  market-hour ints*  | ▇▇
10:00    |   ~500              | ████████████████████
11:00    |  market-hour ints   | ▇▇
12:00    |   ~5                | ▇
13:00    |   ~500              | ████████████████████
14:00    |  market-hour ints   | ▇▇
15:00    |   ~500              | ████████████████████
16:00    |  market-hour ints   | ▇▇
17:00    |   ~1000 (daily+news)| ████████████████████████████████████████
18:00    |   ~500+thesis?      | ████████████████████+
19:00    |    -                |
20:00    |   ~400 (financials) | ████████████████
```
*market-hour intervals: `update-realtime-prices` + `update-market-indices` 매 5분 (배치 quote 사용 시 ~24콜/시간).

### 3.3 Gemini 호출량 추정 히트맵 (평일, 일일)

```
시각(ET) | Gemini 호출 추정 | bar
---------+-----------------+--------------
05:30    |   ~100          | ██████
08:00    |   ~30           | ██
08:15    |   ?(룰)         | ?
08:30    |   ~50           | ███
10:15    |   ?(룰)         | ?
10:30    |   ~50           | ███
12:15    |   ?(룰)         | ?
12:30    |   ~50           | ███
14:15    |   ?(룰)         | ?
14:30    |   ~50           | ███
16:15    |   ?(룰)         | ?
16:30    |   ~50           | ███
16:45    |   ~30~50        | ██
18:15    |   ?(룰)         | ?
18:30    |   ~50           | ███
```

분당 RPM 관점에서는 분산이 잘 되어 있다. **단, `analyze-news-deep` 내부에서 50개를 동시 fanout하면 instantaneous 50 RPM**이 되어 한도 3배 초과 — throttle 구현 검증 필수.

### 3.4 Neo4j 큐 점유 히트맵

```
시각(ET) | neo4j queue 작업 | bar
---------+-----------------+--------------
모든시간  | sec-sync */5 (12회/h) | ▇▇▇▇▇▇▇▇▇▇▇▇  (상시)
04:00    | + cleanup-expired-news | +██
05:30    | + enrich-rel-keywords (Gemini+heavy) | +████
08:45    | + sync-news-to-neo4j (M-F) | +██
10:45    | + sync-news-to-neo4j | +██
12:00    | + sync-profiles-neo4j | +████
12:30    | + sync-relations-neo4j | +████
12:45    | + sync-news-to-neo4j | +██
14:45    | + sync-news-to-neo4j | +██
16:45    | + sync-news-to-neo4j | +██
18:45    | + sync-news-to-neo4j | +██
Sun 04:30| + chainsight-neo4j-dirty-sync (주간)| +██
```

**12:00~13:00 ET가 Neo4j 큐 최대 부하**: 3개 대형 동기화 + 12회 sec-sync 동시 진행.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4.1 강한 의존 체인 (선행 미완료 시 후속 무의미)

#### A. EOD 가격 → EOD 파이프라인 → 정확도 backfill
```
18:00  sync-sp500-eod-prices (FMP, ~500 콜, 추정 10~30분)
18:30  run-eod-pipeline ←──── 30분 gap. EOD가 30분 초과 시 stale 데이터로 시작
19:00  backfill-signal-accuracy ← EOD 파이프라인 의존
```
- **위험**: FMP rate limit 또는 네트워크 지연 시 18:30 파이프라인이 미반영 EOD로 실행.
- **권장 검증**: `run_eod_pipeline` 첫 단계에서 EOD freshness 체크하는지.

#### B. Thesis 파이프라인 (3단)
```
18:00  thesis-update-readings   (지표별 호출, 가변 시간)
18:15  thesis-calculate-scores  ← 15분 gap
18:30  thesis-create-snapshots  ← 15분 gap
```
- **위험**: readings가 15분 내 안 끝나면 score는 부분 데이터로 계산.

#### C. News Intelligence Pipeline (4단, M-F 격시간 반복)
```
HH:00  collect-market-news-* (4시간마다, 8/12/15/18)
HH:15  classify-news-batch    ← 15분 gap (8/10/12/14/16/18 — collect와 misalign!)
HH:30  analyze-news-deep      ← 분류 후
HH:45  sync-news-to-neo4j     ← 분석 후
```
- **🔴 misalignment**: `collect-market-news`는 4시간 간격(8/12/15/18), classify는 2시간 간격(8/10/12/14/16/18).
  - 10:15 classify는 10:00에 새 수집이 없음 → 8:00 batch 잔여 처리.
  - 14:15 classify도 마찬가지 (14:00 collect 없음. 12:00 → 15:00 사이에 새 데이터 없음).
  - 16:15 classify는 15:00 collect 후 75분 지난 데이터.
- **결과**: classify가 헛돌거나 같은 데이터 재처리 가능. 의도된 설계인지 confirm 필요.

#### D. Chain Sight 일일 사이클
```
09:00  extract-news-relations (24h 윈도우)
10:00  chainsight-co-mentions (7d 윈도우)
11:00  chainsight-relation-confidence (co-mention 후)
12:00  chainsight-sync-profiles-neo4j (Sat 02:00 프로파일 의존!)
12:30  chainsight-sync-relations-neo4j (relation-confidence 후)
13:00  chainsight-seed-selection (관계 동기화 후)
```
- **🔴 stale 위험**: `chainsight-sync-profiles-neo4j`(daily)는 `chainsight-all-profiles`(weekly Sat 02:00) 출력에 의존.
  - 토요일 프로파일 계산이 실패하면 월요일~금요일 내내 stale 프로파일을 Neo4j에 동기화.
  - 권장 검증: 프로파일 생성 실패 시 sync를 skip하는 가드 존재 여부.

#### E. Chain Sight 주말 사이클
```
Sat 02:00 chainsight-all-profiles (대형, 추정 30~60분)
Sat 03:00 chainsight-price-co-movement
Sat 04:00 chainsight-stale-decay
Sat 04:30 chainsight-aggregate-profiles
Sat 05:00 validation-weekly-batch
```
- **위험**: 1시간 gap이 충분한지 측정 자료 없음. profile 생성이 1시간 초과하면 다음 단계 stale.

#### F. ML 학습 (Sun 03:00~04:30)
```
Sun 03:00 train-importance-model
Sun 03:30 generate-shadow-report (학습 모델 사용)
Sun 04:00 check-auto-deploy + cleanup-expired-news-relationships(neo4j 큐)
Sun 04:15 generate-weekly-ml-report
Sun 04:20 monitor-ml-performance (5분 gap → 매우 빠듯)
Sun 04:30 train-lightgbm-model + chainsight-neo4j-dirty-sync(neo4j 큐)
```
- **🟡 04:15 → 04:20 (5분 gap)**: 리포트 생성이 5분 초과하면 모니터링이 stale 리포트를 본다.

### 4.2 동시 시각 발사 (코드 충돌 / DB 경합)

#### 04:00 ET 슬롯 (요일별 다중 fire)
| 요일 | 04:00 동시 fire | 큐 |
|------|---------------|----|
| 매일 | `cleanup-expired-news-relationships` | neo4j |
| Mon | `scan-regulatory-relationships` | default |
| Sun | `check-auto-deploy` | default |
| 16일 | `sync-institutional-holdings` | default |

특정 일에 4개 fire 가능 (예: 16일이 일요일이면 cleanup + check-auto-deploy + sync-institutional-holdings 동시).

#### 18:00 ET 슬롯 (M-F 4개 동시)
- `collect-market-news-evening` (default)
- `update-economic-indicators` (default)
- `sync-sp500-eod-prices` (default, FMP heavy)
- `thesis-update-readings` (default, FMP/internal)
- macOS solo pool에서는 직렬, prefork에서는 병렬 → DB 트랜잭션 경합 위험.

#### 18:30 ET 슬롯 (M-F 4개 동시)
- `analyze-news-deep-batch` (default, Gemini)
- `run-eod-pipeline` (default)
- `update-sp500-change-percent` (default, DailyPrice 읽기)
- `thesis-create-snapshots` (default, snapshot 쓰기)
- **DB 경합 가능**: `update-sp500-change-percent`가 `Stock` 테이블 일괄 update → `thesis-create-snapshots`가 같은 시점에 읽으면 dirty read 또는 lock 대기.

#### 12:00 ET 슬롯 (daily 다중)
- `chainsight-sync-profiles-neo4j` (neo4j 큐)
- `sec-seed-relations-to-chainsight` (default)
- `update-economic-indicators` (default, M-F)
- `collect-market-news-noon` (default, M-F)

#### 07:00 ET 슬롯 (daily 다중)
- `chainsight-heat-score-daily` (default)
- `celery-error-digest` (default)

### 4.3 주석/스케줄 불일치 (BUG 의심)

`config/celery.py:734, 741, 748`:
```python
# Heat Score 배치 (매일 07:00 UTC, 시드 선정 전)
'chainsight-heat-score-daily': { 'schedule': crontab(hour=7, minute=0), ... }

# 시드 선정 (매일 13:00 UTC, 관계 동기화 후)
'chainsight-seed-selection': { 'schedule': crontab(hour=13, minute=0), ... }

# Neo4j dirty 동기화 (매주 일요일 04:30 UTC)
'chainsight-neo4j-dirty-sync': { 'schedule': crontab(hour=4, minute=30, day_of_week=0), ... }
```
- 주석은 **UTC** 기준, 실제 `CELERY_TIMEZONE='America/New_York'`로 fire는 ET.
- 결과: 의도(UTC 07:00)와 실제(ET 07:00 = UTC 12:00, DST 시 11:00)가 **5시간 어긋남**.
- **🔴 P1 버그 후보**: 주석이 잘못된 것인지, 스케줄이 잘못된 것인지 결정 필요.

### 4.4 매월 1일 burst (collision)
```
02:00  sync-sp500-constituents
02:30  archive-old-articles
03:00  refresh-korean-overviews-monthly  (Gemini 500 콜, ~33분 throttle 가정)
04:30  build-patent-network
06:00  sec-check-new-filings
```
- 1일이 일요일에 떨어지는 경우(예: 2026년 11월 1일):
  - 03:00 `refresh-korean-overviews-monthly` + 03:00 `train-importance-model` 동시 fire (큐 같음, 다른 태스크).
  - 03:30 `generate-shadow-report` + Korean overviews 진행 중.
  - 04:00 `cleanup-expired-news-relationships` + `check-auto-deploy` + Korean overviews 진행 중 (Gemini 30분 초과 시).
  - **위험**: Gemini 한도 + 큐 점거 + DB 부하 동시 발생.

---

## 5. 종합 권장 액션 (감사자 시각)

### P0 (즉시 검증 필요)
1. **FMP per-symbol fan-out 호출 검증**:
   - `collect_sp500_news_fmp_orchestrator`, `sync_sp500_eod_prices`, `update_realtime_with_provider`, `sync_sp500_financials` 가 batch endpoint를 사용하는지 per-symbol을 사용하는지 코드 확인.
   - per-symbol이라면 17:00~18:00 ET 윈도우에서 300/min 한도 burst 초과 시점 측정.
2. **`analyze-news-deep-batch` 내부 throttle 확인**:
   - `max_articles=50` × 6회/일 = 300 콜이 분당 15 RPM에 맞춰 throttle 되는지 (`time.sleep(4)` 또는 RPM rate limiter).
3. **Beat schedule DB drift 실측**:
   - `dict 키 set` vs `PeriodicTask.objects.values_list('name', flat=True)` diff 출력. 누락된 태스크가 있으면 prod에서 미실행 중.

### P1 (1주 내 처리)
4. **chainsight-* 3개 태스크의 주석 vs 실제 시각 mismatch 결정**:
   - UTC 의도였다면 `from celery.schedules import crontab; crontab(hour=N, minute=M)`은 CELERY_TIMEZONE 기준이므로 5시간 보정 필요(또는 별도 timezone arg).
   - 또는 주석을 ET로 정정.
5. **News Intelligence Pipeline의 collect ↔ classify 시각 misalign 검토**:
   - 10:15, 14:15 classify가 의도된 reprocess인지, 4시간 간격 collect를 2시간 간격으로 정렬해야 하는지.
6. **18:00/18:30 ET 4-way 동시 fire 직렬화**:
   - `sync-sp500-eod-prices` 완료 후 `run-eod-pipeline` 트리거하는 chain 패턴(`task.signature().on_success(...)`) 도입 검토.

### P2 (모니터링)
7. **Neo4j 큐 sec-sync-dirty 폐기율 모니터링**:
   - 12:00~13:00 ET 윈도우에서 expires=240 폐기 빈도를 메트릭으로 노출.
8. **월간 1일 burst 시 Gemini RPD 사용량 알람**:
   - 1500 RPD의 80% 도달 시 알림.

---

## 6. 부록: 인터벌 폴러 분당 부하 합산

| 폴러 | 분당 fire | 일일 fire | 큐 |
|------|---------|----------|----|
| `refresh-market-pulse-cache` (`*/1 9-16 M-F`) | 1.0 (시장시간 한정) | 480 | default |
| `update-realtime-prices` (`*/5 9-16 M-F`) | 0.2 | 96 | default |
| `update-market-indices` (`*/5 9-16 M-F`) | 0.2 | 96 | default |
| `calculate-portfolio-values` (`*/10 9-16 M-F`) | 0.1 | 48 | default |
| `check-screener-alerts` (`*/15 9-16 M-F`) | 0.067 | 32 | default |
| `check-pipeline-alerts` (`*/30`, all hours) | 0.033 | 48 | default |
| `sec-sync-dirty-neo4j` (`*/5`, all hours) | 0.2 | 288 | neo4j |

**시장시간(09:00~16:59 ET, M-F) 분당 평균 firing 합**:
- default 큐: 1.0 + 0.2 + 0.2 + 0.1 + 0.067 + 0.033 = **1.6/분**
- neo4j 큐: 0.2/분 (sec-sync-dirty)
- 분당 부하는 가벼움. 단, 디스크리트 배치 fire와 같은 분(:00, :15, :30, :45)에 겹치는 burst가 실제 위험원.

---

## 7. 결론

- 70개 항목 중 **5건의 🔴 고위험 패턴** 식별:
  1. 17:00~18:00 ET FMP 1500+ 콜 윈도우
  2. SP500 뉴스 orchestrator 5회 × ~500 콜
  3. `analyze-news-deep-batch` 내부 throttle 미검증 (15 RPM 초과 가능)
  4. Neo4j 큐 12:00~13:00 ET 점거 + sec-sync 폐기 가능
  5. chainsight 3개 태스크 주석/스케줄 timezone 불일치
- **18:00 ET가 평일 절대 피크** (디스크리트 11개 동시 + 인터벌 14개 = 25 firing/시간).
- 위험은 dict 선언 기준이며, **DB의 실제 PeriodicTask drift는 별도 점검 필수**.

— end —
