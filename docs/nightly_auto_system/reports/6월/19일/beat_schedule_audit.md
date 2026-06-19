# Celery Beat 스케줄 감사 보고서

- **작성일**: 2026-06-19
- **대상**: `config/celery.py` → `app.conf.beat_schedule`
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **태스크 수**: 86개 엔트리 (`grep -c 'schedule'` = 90, 그중 4건은 주석/비-엔트리)

---

## ⚠️ 0. 감사의 전제 — 반드시 먼저 읽을 것

### 0-1. 이 dict는 런타임에 **무시될 수 있다** (가장 중요)

`config/celery.py:123-140` 주석 + `settings.py`:

```
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

Beat의 **진실의 소스는 DB의 `django_celery_beat.PeriodicTask` 테이블**이다.
`app.conf.beat_schedule` dict는 "원래 설계된 스케줄의 선언적 reference"로만 존재한다.

> **본 감사는 `config/celery.py`의 선언적 reference를 분석한 것**이며,
> 실제 가동 스케줄과 **drift**가 있을 수 있다. 결론을 운영에 적용하기 전
> 반드시 DB 대조가 필요하다:
> ```bash
> python manage.py shell -c "from django_celery_beat.models import PeriodicTask; \
>   import pprint; pprint.pprint(sorted(PeriodicTask.objects.filter(enabled=True).values_list('name', flat=True)))"
> ```
> 이 결과와 아래 86개 키를 diff 해야 감사가 완결된다. **(미수행 — 본 보고서 범위 밖)**

### 0-2. 모든 시각은 **ET(America/New_York)** 이다 — 주석의 "UTC" 표기는 틀렸다

`settings.py:496` → `CELERY_TIMEZONE = 'America/New_York'`
(`settings.py:296` Django `TIME_ZONE = 'Asia/Seoul'`는 Celery 스케줄에 영향 없음)

→ 모든 `crontab(hour=..)`은 **뉴욕 현지시(ET)** 로 해석된다.

🔴 **불일치 발견**: 아래 3개 태스크 주석은 "UTC"라고 적혀 있으나 실제로는 **ET로 실행**된다.

| 태스크 | 주석 표기 | 실제 실행(ET) | UTC 환산(겨울/EST 기준) |
|--------|----------|--------------|------------------------|
| `chainsight-heat-score-daily` | "매일 07:00 **UTC**" | 07:00 ET | 12:00 UTC |
| `chainsight-seed-selection` | "매일 13:00 **UTC**" | 13:00 ET | 18:00 UTC |
| `chainsight-neo4j-dirty-sync` | "일요일 04:30 **UTC**" | 04:30 ET | 09:30 UTC |

영향: **선후 의존(heat→seed)은 같은 타임존으로 해석되므로 깨지지 않음**(07:00 < 13:00 ET 유지).
그러나 문서가 거짓 → 운영자가 "UTC 07:00 = KST 16:00"로 오인하면 디버깅 시 5시간 어긋난다.
→ **주석 정정 권고**(코드 동작 변경 아님, 문서 수정만). 본 보고서는 이하 전부 **ET 기준**으로 분석.

### 0-3. Alpha Vantage 의존 스케줄 = **0건** (검증 완료)

```
grep -rln "alpha_vantage|alphavantage" --include=tasks.py  → (결과 없음)
```
→ **Beat 스케줄 중 AV를 호출하는 태스크는 없다.** AV(5 calls/min) 한도는
on-demand/Processor 경로에서만 소모되며 **스케줄 감사 대상 아님**. (요청사항 1-③ → 위험 없음)

---

## 1. Rate Limit 초과 구간 분석

### 1-1. FMP (Starter: 300 calls/min, 10,000 calls/day)

#### FMP 호출 태스크 인벤토리 (ET)

| 태스크 | 시각(ET) | 빈도 | 추정 호출량 | 비고 |
|--------|---------|------|------------|------|
| `update-realtime-prices` | */5, 9–16시 평일 | 96/일 | **회당 ≤10** | 포트폴리오 심볼 `[:10]`, `force=False` 캐시우선 → **저부하** ✅ |
| `update-market-indices` | */5, 9–16시 평일 | 96/일 | 회당 소수 (지수 몇 개) | 저부하 |
| `update-daily-prices` | 17:00 평일 | 1/일 | ≤10 | realtime와 동일 함수 |
| `sync-sp500-financials` | 20:00 평일 | 1/일 | **101 심볼 × N**(재무제표 다중 엔드포인트) | `batch_size=101`, 5일 1회전 |
| `sync-sp500-eod-prices` | 18:00 평일 | 1/일 | **~500 심볼** | 🔴 단일 태스크 최대 버스트 |
| `collect-sp500-news-fmp-*` | 06:15/10:15/13:15/15:15/17:15 평일 | **5/일** | **회당 S&P500 전체** | 🔴 orchestrator, 일 호출량 지배 |
| `collect-press-releases-fmp` | 07:45 평일 | 1/일 | `max_symbols=50` | |
| `collect-general-news-fmp-*` | 06:45/12:30/17:45 평일 | 3/일 | general 엔드포인트 | |
| `sync-etf-holdings` | 월 06:00 | 주1 | SPDR/FMP | |
| `sync-sp500-constituents` | 1일 02:00 | 월1 | 1 (구성종목 목록) | |

#### 분/일 한도 평가

- **분당(300/min) 초과 위험**: 🟡 **조건부**.
  `sync-sp500-eod-prices`(500심볼)와 `collect-sp500-news-fmp`(500심볼)가 **per-symbol 루프**로
  무제한 발사되면 500 calls가 1분 내 몰려 300/min을 초과한다. `sync_sp500_financials`는
  내부에 `time.sleep` 스로틀이 보였으나(루프 구조), EOD/뉴스 orchestrator의 내부
  스로틀 여부는 **태스크 코드 추가 확인 필요**(스케줄만으로는 단정 불가).
  → **권고: 세 태스크의 내부 rate-limit/chunk 로직 점검**.

- **일일(10,000/day) 초과 위험**: 🟡 **주의**.
  거친 합산:
  - SP500 뉴스 orchestrator 5회 × ~500 = **~2,500**
  - SP500 EOD 1회 × ~500 = **~500**
  - SP500 financials 101 × (2~4 엔드포인트) = **~200–400**
  - realtime/indices */5 × 8시간 × ≤10 = **~1,000–2,000**(대부분 캐시 → 실호출 적음)
  - general/press/category 뉴스 다수
  → **누적 4,000–6,000/day 추정.** 한도의 40–60%. 현재는 여유가 있으나,
  뉴스 orchestrator가 per-symbol fan-out이고 종목이 늘면 한도에 접근. **모니터링 권고**.

- **동시각 FMP 충돌**: 🔴 **18:00 ET**. `sync-sp500-eod-prices`(500) +
  `thesis-update-readings`(지표용 FMP 가능) + `collect-market-news-evening`이 **동시 발사**.
  EOD 500심볼 버스트가 다른 FMP 태스크와 분당 한도를 공유 → **18:00이 FMP 분당 피크**.

### 1-2. Gemini Free (15 RPM, 1500 RPD)

#### Gemini(LLM) 호출 태스크 (genai 확인: `services/news/tasks.py`, `services/serverless/tasks.py`, `services/sec_pipeline/tasks.py`, `thesis/tasks/summary.py`)

| 태스크 | 시각(ET) | 빈도 | LLM 호출 규모 |
|--------|---------|------|--------------|
| `enrich-relationship-keywords` | 05:30 매일 | 1/일 | `limit=100` → 최대 100 호출 |
| `keyword-generation-pipeline` | 08:00 매일 | 1/일 | gainers 키워드 |
| `classify-news-batch` | 08/10/12/14/16/18시 **:15** 평일 | 6/일 | `hours=3` 분량 분류 |
| `analyze-news-deep-batch` | 08/10/12/14/16/18시 **:30** 평일 | 6/일 | `max_articles=50` → **회당 ≤50 호출** |
| `extract-daily-news-keywords` | 16:45 매일 | 1/일 | 일일 키워드 |
| `chainsight-co-mentions` | 10:00 매일 | 1/일 | CoMention 추출(LLM 여부 확인 필요) |
| `thesis-generate-summaries` | 18:35 평일 | 1/일 | 스냅샷별 요약 |
| `refresh-korean-overviews-monthly` | 1일 03:00 | 월1 | **S&P500 한글 개요 일괄** → 대량 |
| `validation-weekly-batch` | 토 05:00 | 주1 | LLM 필터 |

#### 평가

- **분당(15 RPM) 초과 위험**: 🟡 **태스크 내부 버스트가 관건**.
  스케줄 레벨에서는 이미 **방어 설계**가 보임 — 같은 시(hour)에 `classify`(:15)/`analyze-deep`(:30)/`sync-neo4j`(:45)를
  **15분씩 분산**. 특히 주석(`celery.py:290-296`, audit P0 #8)에 따르면 과거
  16:30 `analyze-deep` + `extract-keywords` 동시호출로 15 RPM 2배 초과가 발생 →
  `extract-keywords`를 16:45로 이동해 **이미 수정**됨. ✅ 좋은 선례.
  - 잔존 리스크: **단일 태스크 내부**. `analyze-news-deep-batch`가 50 articles를
    한 번에 돌리면 50 호출 → **내부에서 15 RPM 스로틀이 없으면 단독으로 초과**.
    스케줄 분산은 태스크 *간* 충돌만 막지, 태스크 *내* 버스트는 못 막는다.
    → **권고: analyze-deep / enrich(100) / korean-overviews의 내부 스로틀 점검**.

- **일일(1500 RPD) 초과 위험**: 🟡 **주의**.
  `analyze-deep` 6 × 50 = **~300** + `enrich` 100 + `classify` 6×다수 +
  키워드/요약/co-mention 등 → **평일 누적 600–1,000 RPD 추정**.
  `refresh-korean-overviews-monthly`(1일)가 겹치는 날은 **S&P500 일괄로 +500급** →
  **월 1일에 1500 RPD 근접/초과 가능**. → **1일자 03:00 한글개요와 당일 뉴스 LLM 합산 모니터링 권고**.

- **동시각 Gemini 피크**: 🟡 **18:30–18:35 ET**. `analyze-news-deep-batch`(18:30) +
  `thesis-generate-summaries`(18:35)가 5분 간격 — 둘 다 LLM. analyze-deep 50건이
  18:35까지 안 끝나면 thesis 요약과 RPM 경합.

### 1-3. Alpha Vantage (5 calls/min)

→ **§0-3 참조. 스케줄 의존 0건. 위험 없음.** ✅

---

## 2. Queue 몰림 분석 — default vs neo4j

### 2-1. neo4j 큐 (solo pool, 동시성 = 1) — 🔴 **최대 병목**

`task_routes`(celery.py:43-61) + 개별 `options.queue`로 neo4j 큐에 라우팅되는 태스크:

| 태스크 | 시각(ET) | 빈도 |
|--------|---------|------|
| `sec-sync-dirty-neo4j` | **\*/5 매일 (24h)** | **288/일** 🔴 |
| `sync-news-to-neo4j` | 8/10/12/14/16/18시 :45 평일 | 6/일 |
| `neo4j-health-check` | */6시 :00 (00/06/12/18) | 4/일 |
| `cleanup-expired-news-relationships` | 04:00 매일 | 1/일 |
| `enrich-relationship-keywords` | 05:30 매일 | 1/일 |
| `chainsight-sync-profiles-neo4j` | 12:00 매일 | 1/일 |
| `chainsight-sync-relations-neo4j` | 12:30 매일 | 1/일 |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | 주1 |

> **참고**: `sec-sync-dirty-neo4j`는 beat `options`에 큐 미지정이나
> `task_routes`(celery.py:60)가 `sync_dirty_to_neo4j → neo4j`로 라우팅 → neo4j 큐 확정.

#### solo pool 직렬 처리에서의 밀림

**solo = 동시 1개**. 즉 모든 neo4j 태스크는 **한 줄로 줄 서서** 처리된다.
`sec-sync-dirty-neo4j`가 5분마다 들어오는데(`expires=240`=4분), **다른 neo4j 태스크가
4분 이상 점유하면 sec-dirty는 만료되어 스킵(누락)** 된다.

🔴 **충돌 핫스팟 (neo4j 큐, ET)**:

| 시각 | 동시 진입 neo4j 태스크 | 위험 |
|------|----------------------|------|
| **12:00** | `neo4j-health-check` + `chainsight-sync-profiles-neo4j` + `sec-sync-dirty`(*/5의 :00) | **3중 직렬**. sync-profiles가 무거우면 health/sec-dirty 밀림·만료 |
| **12:30** | `chainsight-sync-relations-neo4j` + `sec-sync-dirty`(:30) | 2중 |
| **:45 (8~18시)** | `sync-news-to-neo4j` + `sec-sync-dirty`(:45) | news 동기화가 길면 sec-dirty 만료 |
| **04:00–05:30** | `cleanup-expired`(04:00) → (일)`dirty-sync`(04:30) → `enrich`(05:30) | 순차, 간격 양호하나 cleanup 장기화 시 sec-dirty 연쇄 만료 |
| **00/06/18시 :00** | `health-check` + `sec-dirty`(:00) | 2중 |

→ **핵심 리스크**: `sec-sync-dirty-neo4j`의 `expires=240`은 안전밸브이자 **조용한 누락원**.
12:00처럼 무거운 chainsight 동기화와 겹치면 dirty evidence 동기화가 **소리 없이 빠진다**.
→ **권고**: (a) chainsight neo4j 동기화를 :05/:35 등으로 비켜 배치, 또는
(b) sec-dirty `expires`를 늘리거나 빈도 완화, (c) neo4j 워커 동시성 모니터링.

### 2-2. default 큐 — 고빈도 폴러가 시장시간(9–16 ET)을 지배

default 큐의 **상시 폴러**(배치와 별개 계층):

| 태스크 | 빈도 | 시장시간 부하 |
|--------|------|--------------|
| `refresh-market-pulse-cache` | **매분, 9–16시** | **60/시 × 8h = 480/일** 🔴 최다 |
| `update-realtime-prices` | */5, 9–16시 | 12/시 |
| `update-market-indices` | */5, 9–16시 | 12/시 |
| `calculate-portfolio-values` | */10, 9–16시 | 6/시 |
| `check-screener-alerts` | */15, 9–16시 | 4/시 |
| `check-pipeline-alerts` | */30, 24h | 2/시 |
| `sec-sync-dirty-neo4j` | */5, 24h | (neo4j 큐) |

→ default 큐는 **9–16시에 시당 ~94 task firing**(주로 경량 캐시/계산).
대부분 외부 API 없는 내부 연산이라 **부하 자체는 가볍지만**, prefork 워커 수가 부족하면
이 폴러들이 워커 슬롯을 점유해 **같은 시간대 배치(16:30 market-breadth 등)의 시작이 지연**될 수 있다.
→ **권고**: default 워커 동시성(prefork concurrency)이 폴러 + 배치를 흡수하는지 확인.
특히 macOS 개발환경은 `solo` 강제(celery.py:36-37)라 **동시성=1 → 폴러가 배치를 직렬로 막음**(개발환경 한정 심각).

---

## 3. 시간대별 태스크 실행 히트맵 (평일/Mon–Fri, ET 기준)

> **2계층 분리**: 폴러(상시 고빈도)와 디스크리트 배치를 섞으면 그림이 왜곡되므로 분리 표기.
> 월간/주간 전용 태스크(1일·15일·16일·토·일)는 평일 히트맵에서 제외(§4-3 별도).

### 3-A. 디스크리트 배치 태스크 — 시각별 발사 횟수

```
ET  count  bar                                        peak
00 │  1   │█                                          neo4j-health
01 │  1   │█                                          econ-calendar
02 │  0   │
03 │  0   │
04 │  1   │█                                          news-rel cleanup(neo4j)
05 │  1   │█                                          enrich-keywords(neo4j,Gemini)
06 │  5   │█████                                      📰 뉴스수집 클러스터 시작
07 │  6   │██████                                     📰 movers+category+press
08 │  5   │█████                                      🤖 Gemini 진입(keyword/classify/analyze)
09 │  2   │██                                         sentiment+news-relations  ← 시장개장(폴러 ON)
10 │  5   │█████                                      sp500-news-fmp + classify/analyze
11 │  1   │█                                          relation-confidence
12 │ 10   │██████████   ◄── PEAK #1                   🔴 neo4j+news+chainsight+sec 수렴
13 │  4   │████                                       seed-selection + category-high
14 │  4   │████                                       daily-news-pm + classify/analyze
15 │  3   │███                                        market-news-pm + sp500-news-fmp
16 │  6   │██████                                     🔴 EOD 진입: breadth/heatmap/keywords
17 │  4   │████                                       daily-prices + category-high-eve  ← 시장마감(폴러 OFF)
18 │ 12   │████████████ ◄── PEAK #2 (최대)            🔴🔴 EOD 크런치
19 │  2   │██                                         ml-labels + signal-accuracy
20 │  1   │█                                          sp500-financials(FMP 101)
21 │  0   │
22 │  1   │█                                          econ-indicators(22시분)
23 │  0   │
```

**피크 #1 — 12:00시대 (10건)**: neo4j 동기화(profiles/relations/health) + 뉴스(noon/classify/analyze/general)
+ chainsight(co-mention 10시·seed 13시 사이) + sec-seed-relations 가 12:00–12:45에 수렴.
**neo4j 큐(solo) 3중 충돌**이 이 시간대 핵심(§2-1).

**피크 #2 — 18:00시대 (12건, 최대)**: 🔴🔴 **EOD 크런치**. 분 단위:
```
18:00 ×4  econ-indicators / market-news-evening / sync-sp500-eod(FMP 500) / thesis-update-readings
18:15 ×2  classify-news-batch / thesis-calculate-scores
18:30 ×4  analyze-news-deep(Gemini) / run-eod-pipeline / thesis-create-snapshots / update-sp500-change-pct
18:35 ×1  thesis-generate-summaries(Gemini)
18:45 ×1  sync-news-to-neo4j(neo4j)
```
FMP 버스트(18:00) + Gemini 버스트(18:30/35) + thesis 체인 + EOD 파이프라인이 **45분 안에 전부**.

### 3-B. 상시 폴러 계층 (배경 부하)

```
ET   00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
sec-dirty(*/5,neo4j)  ████████████████████████████████████████████████  24h 12/h
pipeline-alert(*/30)  ████████████████████████████████████████████████  24h  2/h
mkt-pulse-cache(*/1)              ·····[██████████████████]·····          9-16 60/h 🔴
realtime-px(*/5)                  ·····[██████████████████]·····          9-16 12/h
mkt-indices(*/5)                  ·····[██████████████████]·····          9-16 12/h
portfolio-val(*/10)               ·····[██████████████████]·····          9-16  6/h
screener-alert(*/15)              ·····[██████████████████]·····          9-16  4/h
```

→ **9–16시(시장시간)**: 디스크리트 배치는 적으나(2~6건/시) **폴러가 시당 ~94 firing**으로 배경 부하 최대.
→ **장 마감 직후 16–20시**: 폴러는 꺼지지만 **디스크리트 배치 폭증(피크 #2)** → 부하 무게중심이 폴러→배치로 이동.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 시간 간격(time-gap) 기반 의존 체인 — 🔴 **체이닝이 아닌 시각 가정**

여러 파이프라인이 `chain()`/`chord` 없이 **"앞 태스크가 N분 내 끝난다"는 가정**으로
시각만 어긋나게 배치되어 있다. 선행이 지연되면 후행이 **stale 데이터로 실행**된다.

| 파이프라인 | 체인(ET) | 가정 간격 | 리스크 |
|-----------|---------|----------|--------|
| **Thesis EOD** | 18:00 readings → 18:15 scores → 18:30 snapshots → 18:35 summaries | 15·15·5분 | readings(FMP 지표 수집)가 15분 초과 시 scores가 빈/구 데이터로 계산 🔴 |
| **EOD Dashboard** | 18:00 sync-sp500-eod(FMP 500) → 18:30 run-eod-pipeline → 19:00 backfill-accuracy | 30·30분 | **EOD 500심볼이 30분 내 완료 가정.** FMP 300/min 스로틀 시 빠듯 → run-eod가 미완 가격으로 시그널 계산 🔴 |
| **News v3** | :15 classify → :30 analyze → :45 sync-neo4j (시간당) | 15·15분 | classify 지연 시 analyze가 미분류분 누락 |
| **Chain Sight 주말** | 토 02:00 profiles → 03:00 co-move → 04:00 decay → 04:30 aggregate | 60분 | 간격 넉넉 ✅ |
| **Chain Sight 일일** | 10:00 co-mention → 11:00 confidence → 12:00 sync-profiles → 12:30 sync-relations | 60·60·30분 | 간격 양호하나 12:00 neo4j 3중충돌(§2-1)과 연동 |
| **Heat→Seed** | 07:00 heat-score → 13:00 seed-selection | 6시간 | 간격 충분 ✅ (단 주석 "UTC" 오기 §0-2) |

→ **권고**: 18:00–18:35 thesis/EOD 체인은 **시각 가정이 가장 빠듯**.
선행 완료를 보장하려면 `chain()`/`chord` 또는 후행 시작 시 선행 완료 플래그 확인 권고.
최소한 **EOD 가격 동기화(18:00)와 run-eod-pipeline(18:30) 간 30분이 500심볼 FMP 스로틀을 견디는지** 실측 필요.

### 4-2. 동일 시각 동시 발사 — 데이터 경합

| 시각(ET) | 동시 태스크 | 경합 종류 |
|---------|------------|----------|
| **12:00** | health-check + sync-profiles-neo4j + sec-dirty (모두 neo4j) + econ-indicators + market-news-noon + sec-seed-relations (default) | neo4j 큐 3중 직렬 + default 3건 |
| **18:00** | sync-sp500-eod + thesis-readings + market-news-evening + econ-indicators | **FMP 동시 발사** + DB write 경합(가격 테이블) |
| **18:30** | run-eod-pipeline + thesis-snapshots + analyze-deep + update-change-pct | EOD 파이프라인 ↔ thesis가 같은 가격/시그널 테이블 read 경합 가능 |
| **09:00** | aggregate-sentiment + extract-news-relations | 같은 뉴스 테이블 read |

→ `update-sp500-change-percent`(18:30)는 `sync-sp500-eod-prices`(18:00)의 DailyPrice에 의존.
EOD가 18:30까지 미완이면 change-percent가 **구 가격으로 계산**. (4-1과 동일 패턴)

### 4-3. 월간/주간 집중일 (평일 히트맵 외)

| 일자(ET) | 겹치는 태스크 | 비고 |
|---------|--------------|------|
| **매월 1일 02:00–04:30** | sync-sp500-constituents(02:00) + archive-articles(02:30) + refresh-korean-overviews(03:00,Gemini대량) + build-patent-network(04:30) + sec-check-filings(06:00) | 🟡 **월초 새벽 집중.** 한글개요 Gemini 대량과 당일 뉴스 LLM 합산 시 1500 RPD 근접(§1-2) |
| **매월 15/16일** | supply-chain-batch(15일 03:00) / institutional-holdings(16일 04:00) | SEC, 분산 양호 ✅ |
| **매주 토 02:00–05:00** | chainsight 5종 체인 + validation(05:00) | 간격 양호 ✅ |
| **매주 일 03:00–05:00** | ML 체인(train→shadow→deploy→report→monitor→lightgbm) 03:00–04:30 + neo4j-dirty(04:30) + cleanup-task-results(05:00) | 🟡 ML 체인 6종이 03:00–04:30 90분에 밀집. 04:30 neo4j-dirty가 ML과 겹침 |

---

## 5. 핵심 발견 요약 (우선순위)

| # | 심각도 | 발견 | 위치 | 권고 |
|---|--------|------|------|------|
| 1 | 🔴 | **이 dict는 런타임에 무시될 수 있음** (DatabaseScheduler) | celery.py:123-140 | DB `PeriodicTask`와 86키 diff 필수 (§0-1) |
| 2 | 🔴 | neo4j 큐 **12:00 3중 직렬** + `sec-dirty` `expires=240` 조용한 누락 | §2-1 | chainsight 동기화 :05/:35로 이동, sec-dirty 빈도/만료 재검토 |
| 3 | 🔴 | **18:00–18:35 EOD 크런치**: FMP 500버스트 + Gemini + thesis/EOD 체인 동시 | §3-A,4-1 | 체인을 `chain()`로, EOD 가격 30분 가정 실측 |
| 4 | 🟡 | thesis/EOD가 `chain` 없이 **시각 가정 의존** → 선행 지연 시 stale | §4-1 | 완료 플래그 또는 chord |
| 5 | 🟡 | FMP 일일 ~4–6k/10k (SP500 뉴스 orchestrator 5회가 지배) | §1-1 | orchestrator 내부 스로틀/chunk 점검, 종목 증가 시 한도 접근 |
| 6 | 🟡 | Gemini **태스크 내부 버스트**(analyze 50/회, enrich 100) 미지의 스로틀 | §1-2 | 태스크 내부 15 RPM 가드 확인 |
| 7 | 🟡 | 월 1일 새벽 한글개요(대량 Gemini) + 당일 뉴스 LLM → 1500 RPD 근접 | §4-3 | 1일자 RPD 모니터링 |
| 8 | 🟢 | 주석 "UTC" 3건이 실제 ET → 문서 오기 (동작은 정상) | §0-2 | 주석 정정 |
| 9 | 🟢 | Alpha Vantage 스케줄 의존 0건 | §0-3 | 조치 불요 |
| 10 | 🟢 | macOS 개발환경 `solo`(동시성1) → 폴러가 배치 직렬 차단 | §2-2 | 개발환경 한정, 운영(Linux prefork) 무관 |

---

## 6. 본 감사의 한계 (정직성 명시)

- 🔴 **DB `PeriodicTask` 미대조** — 실제 가동 스케줄과 drift 가능(§0-1). **본 보고서는 선언적 reference 분석.**
- FMP/Gemini **태스크 내부** 호출량·스로틀은 일부만 확인(realtime `[:10]`, financials `sleep` 확인됨).
  EOD/뉴스 orchestrator의 per-symbol fan-out 정밀 호출수는 **태스크 코드 추가 정독 필요**(스케줄 레벨 추정치).
- 외부 API 한도 환산은 "심볼당 1콜" 등 **보수적 가정** 기반. 배치/캐시로 실호출은 더 적을 수 있음.
- 실행 소요시간(duration) 데이터 없음 → 의존 체인 "지연 시 stale" 리스크는 **구조적 가능성**이지 측정된 사건 아님.

---
*읽기 전용 감사 — 코드/스케줄 변경 없음. config/celery.py:141-820 분석.*
