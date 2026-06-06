# Beat Schedule Audit — `config/celery.py`

> **감사 유형**: 읽기 전용(코드 수정 없음)
> **대상**: `config/celery.py` `app.conf.beat_schedule` (라인 141~820, 총 71개 엔트리)
> **작성일**: 2026-06-06
> **타임존 기준**: `CELERY_TIMEZONE = 'America/New_York'` (config/settings.py:489) → **모든 crontab `hour=` 값은 ET(미 동부) 기준**
> **DB**: `TIME_ZONE='Asia/Seoul'`, `USE_TZ=True` (앱 레벨), 단 Celery beat는 NY 시간으로 동작

---

## 0. 선결 경고 — 이 dict는 런타임에 무시될 수 있음 ⚠️ (가장 중요)

`config/celery.py:124-140` 주석과 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 설정에 따르면,
**Celery Beat의 진실의 소스는 `django_celery_beat.PeriodicTask` DB 테이블**이고 이 `beat_schedule` dict는
"원래 설계된 스케줄의 선언적 reference"로만 존재한다.

- 본 감사는 **선언적 reference(config dict)** 를 분석한 것이다.
- **실제 운영 스케줄은 DB와 drift 가능성**이 있다 (CLAUDE.md 버그 #28).
- **검증 필수**: `python manage.py shell`에서
  `set(PeriodicTask.objects.values_list('name', flat=True))` ↔ config dict 키 diff.
- 본 보고서의 모든 발견사항은 "DB가 config와 일치한다"는 전제하에서만 유효하다.

---

## 1. 전체 태스크 인벤토리 (71개)

분류 기준: 외부 API 의존성 / 큐 / 빈도

| API 의존 | 큐 | 태스크 수 | 비고 |
|---------|-----|---------|------|
| FMP | default | ~18 | 주가/지수/뉴스/재무/EOD |
| Gemini (LLM) | default+neo4j | ~9 | 키워드/심층분석/요약/관계추출 |
| FRED | default | 1 | update-economic-indicators (4회/일) |
| Alpha Vantage | — | **0** | beat에 AV 직접 의존 태스크 없음 (§2.3) |
| News API (혼합) | default | ~12 | collect_daily/market/category_news (provider 불명확) |
| SEC EDGAR | default | 3 | filing 감지/공급망/13F |
| 외부 API 없음(DB/캐시/ML) | default | ~20 | cache/portfolio/aggregate/train |
| Neo4j 전용 | **neo4j (solo)** | ~9 | §3 |

---

## 2. Rate Limit 초과 분석

### 2.1 FMP (Starter: 300 calls/min, 10,000/일) — ⚠️ 검증 필요(MEDIUM~HIGH)

**(A) 시장시간 중 `*/5` 상시 소비 — 가장 지속적인 FMP 부하**

| 태스크 | 스케줄(ET) | 빈도 |
|--------|-----------|------|
| `update-realtime-prices` | `*/5` 09–16시 평일 | 12회/시 |
| `update-market-indices` | `*/5` 09–16시 평일 | 12회/시 |

→ 매 `:00, :05, :10…` 두 태스크가 **동시 발화**. 09–16시 내내 FMP에 분당 burst 발생.
- **300/min 위반 여부는 내부 구현에 달려 있음** (config에서 확인 불가):
  - `update_realtime_with_provider`가 **FMP batch-quote 엔드포인트(1 call 다심볼)** 를 쓰면 안전.
  - **심볼당 1 call**(S&P 500 = 500심볼)이면 단일 분에 500 calls → **300/min 초과**.
- **검증 항목**: `packages/shared/stocks/tasks.py`의 `update_realtime_with_provider` 내부가
  batch 호출/페이싱하는지 확인.

**(B) 18:00 ET EOD 동시 FMP 수렴 — ⚠️ HIGH 우려**

같은 18:00 분에 FMP를 만지는 태스크가 겹친다:
- `sync-sp500-eod-prices` (18:00, **S&P 500 = 500심볼 일괄**)
- `thesis-update-readings` (18:00, 지표 reading 수집 — FMP 지표 가능성)
- `collect-market-news-evening` (18:00)

→ 500심볼 EOD sync가 페이싱 없으면 **수 분간 300/min 초과 지속** + thesis-readings가 같은 한도를 두고 경합.
- **검증**: eod-prices가 batch/chunk+sleep 구조인지, thesis-readings의 FMP 호출량.

**(C) S&P 500 뉴스 5회 sweep — 설계상 분산 양호 ✓**

`collect-sp500-news-fmp-*` 5개: 06:15 / 10:15 / 13:15 / 15:15 / 17:15 — **모두 `:15`, 최소 2시간 간격**.
각각 500심볼 sweep이지만 서로 겹치지 않게 오프셋됨. **양호** (단, 개별 sweep 내부 페이싱은 별도 확인).

**(D) 일일 총량(10,000/일)**: 인트라데이 `*/5`×2 (~ 약 12×8×2 = 192 발화) + 뉴스 sweep 5회(각 ≤500) + EOD 500 + 재무 101 + 기타.
batch 호출이면 일일 한도 여유, 심볼당 호출이면 뉴스/EOD/재무만으로도 수천 calls → **일일 한도도 검증 대상**.

### 2.2 Gemini Free (15 RPM, 1500 RPD) — ⚠️ HIGH (배치 태스크 내부 페이싱 의존)

config 레벨에서는 태스크 1개=1 발화지만, **태스크 내부에서 루프로 다수 LLM 호출**하는 것이 문제다.

| 태스크 | 스케줄(ET) | 1회 LLM 호출 추정 | RPM 위험 |
|--------|-----------|------------------|---------|
| `analyze-news-deep-batch` | `:30` of 08,10,12,14,16,18 평일 | **max_articles=50** → 최대 50 calls | ⚠️ 50 calls burst → 15 RPM 위반 가능 |
| `enrich-relationship-keywords` | 05:30 매일 | **limit=100** → 최대 100 calls | ⚠️ 100 calls → 페이싱 없으면 위반 |
| `keyword-generation-pipeline` | 08:00 매일 | gainers 다건 | 중 |
| `extract-daily-news-keywords` | 16:45 매일 | 다건 | 중 |
| `extract-news-relations` | 09:00 매일 | 24h 뉴스 | 중 |
| `chainsight-co-mentions` | 10:00 매일 | 7일 뉴스 | 중 |
| `thesis-generate-summaries` | 18:35 평일 | thesis별 | 중 |
| `refresh-korean-overviews-monthly` | 03:00 매월1일 | bulk(다수) | ⚠️ 월간 spike |

- **15 RPM은 config로 강제 불가**. 50/100건 루프 태스크는 **내부에서 ≥4초 간격(≤15 RPM)** 으로 페이싱해야 함.
  → `analyze_news_deep`, `enrich_relationship_keywords` 내부 sleep/rate-limit 검증 필수.

**RPD(1500/일) 추정**: analyze-deep 6회×최대50 = 300 + enrich 100 + keyword/extract/co-mention/summary 등.
정상 분량이면 1500 이내지만 **뉴스 폭주일에는 analyze-deep만으로 RPD 압박** 가능 → 모니터링 권장.

**시간대 충돌(동시 Gemini)**:
- **16:30 analyze-deep(≤50) ↔ 16:45 extract-keywords**: 이미 주석(audit P0 #8, 2026-04-26)에서 15분 분산으로 해소.
  단 **analyze-deep가 15분 초과 실행 시 여전히 16:45와 Gemini 동시 점유** → 잔여 위험.
- **18:30 analyze-deep(≤50) ↔ 18:35 thesis-summaries(5분 간격)**: ⚠️ **16:30 사례와 동일 구조인데 미해소**.
  analyze-deep가 5분 넘으면 thesis-summaries와 Gemini 15 RPM을 공유 → **신규 발견(P-NEW-1)**.
- **10:00 co-mentions ↔ 10:30 analyze-deep ↔ 08:00 keyword**: 오전 Gemini 클러스터.

### 2.3 Alpha Vantage (5 calls/min) — ✓ 무부하

- **beat_schedule 내 AV 직접 의존 태스크 없음**. 주가는 `update_realtime_with_provider`(FMP)로 일원화.
- AV 호출(있다면)은 on-demand/수동 경로 → **스케줄 기반 5/min 압박 없음**.
- **검증**: provider 태스크가 FMP 실패 시 AV로 fallback하지 않는지(있다면 5/min 즉시 위반) 확인.

---

## 3. Queue 몰림 분석 (default vs neo4j)

### 3.1 neo4j 큐 (solo pool, **동시 1개**) — ⚠️ HIGH

neo4j 큐로 라우팅되는 태스크(`task_routes` 라인 43-61 + options queue):

| 태스크 | 스케줄(ET) | 부하 | expires |
|--------|-----------|------|---------|
| `sec-sync-dirty-neo4j` | `*/5` **전 시간/매일** | **288회/일** (지배적) | **240s (4분)** |
| `neo4j-health-check` | `*/6h` (00/06/12/18) | 4회/일 | — |
| `cleanup-expired-news-relationships` | 04:00 매일 | 1 | 3600 |
| `sync-news-to-neo4j` | `:45` of 08,10,12,14,16,18 | 6회 (**max_articles=100**) | 3600 |
| `enrich-relationship-keywords` | 05:30 매일 | 1 (**LLM 100건, 장시간**) | 3600 |
| `chainsight-sync-profiles-neo4j` | 12:00 매일 | 1 | 3600 |
| `chainsight-sync-relations-neo4j` | 12:30 매일 | 1 | 3600 |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | 1 | 3600 |

**핵심 결함 — solo 큐에서 단명(短命) 고빈도 태스크가 장시간 태스크에 굶주림(starvation):**

`sec-sync-dirty-neo4j`는 **expires=240s(4분)** + **5분마다** 발화한다. neo4j 큐는 solo(동시 1).
같은 큐에서 **장시간 태스크**가 워커를 4분 이상 점유하면, 대기 중인 sec-dirty는 **만료되어 조용히 폐기**된다.

장시간 점유 후보 ↔ sec-dirty 충돌 지점:
- **05:30 `enrich-relationship-keywords`** (LLM 100건; 4초 페이싱 시 ~7분) → 05:30/05:35 sec-dirty **드롭 위험** ⚠️
- **`:45` `sync-news-to-neo4j`** (100 articles) → :45/:50 sec-dirty 드롭 위험 ⚠️
- **12:00 sync-profiles + 12:30 sync-relations** → 인접 sec-dirty 지연

→ **결과**: SEC→Neo4j evidence 동기화가 **무음으로 누락**될 수 있음 (실패 로그도 없이 expire).
→ **신규 발견(P-NEW-2, HIGH)**. 권장: sec-dirty를 별도 큐로 분리하거나, 장시간 neo4j 태스크를 전용 윈도로 격리.

**12:00 동시 수렴(neo4j solo)**: `neo4j-health-check`(12:00) + `chainsight-sync-profiles-neo4j`(12:00) + `sec-sync-dirty`(12:00) → 3개 직렬화.

### 3.2 default 큐 — 빈도 최상위는 캐시 갱신

| 태스크 | 스케줄(ET) | 빈도 | 비고 |
|--------|-----------|------|------|
| `refresh-market-pulse-cache` | `*` (매분) 09–16 평일 | **480회/일** | expires 없음 → 백로그 시 누적 |
| `check-pipeline-alerts` | `*/30` 전시간 | 48회/일 | expires 1500 |
| `update-realtime-prices` | `*/5` 09–16 | 96/일 | |
| `update-market-indices` | `*/5` 09–16 | 96/일 | |
| `calculate-portfolio-values` | `*/10` 09–16 | 48/일 | DB 계산 |
| `check-screener-alerts` | `*/15` 09–16 | 32/일 | |

- **Linux(prefork)**: default 큐 동시성 多 → 09–16시 매분 발화 누적 흡수 가능.
- **macOS(solo, `IS_MACOS` → worker_pool='solo', 라인 36-37)**: default도 **동시 1**.
  매분 cache + `:00`마다 cache+realtime+indices(+10분 portfolio+15분 screener) **직렬화** → dev 환경에서 밀림 가능.
  (운영이 Linux면 영향 제한적; **dev에서 재현되는 지연은 정상 동작 아님 주의**)
- `refresh-market-pulse-cache`에 **expires 미설정** → 워커 지연 시 stale 작업도 실행되어 누적 ⚠️ (LOW).

---

## 4. 시간대별 ASCII 히트맵 (평일 ET 기준)

### 4.1 전체 태스크 발화 수 / 시간 (인트라데이 매분 cache 포함)

```
ET   count  bar
00 │   15  ████████
01 │   15  ████████
02 │   14  ███████
03 │   14  ███████
04 │   15  ████████
05 │   15  ████████        ← enrich(LLM,neo4j 장시간) 잠복
06 │   20  ██████████      ← 아침 뉴스 수집 램프 시작
07 │   20  ██████████
08 │   19  ██████████      ← News v3 파이프라인 가동(classify/analyze/sync)
09 │  110  ███████████████████████████████████████████████████████  ← 인트라데이 개시(PEAK 시작)
10 │  113  ████████████████████████████████████████████████████████
11 │  109  ██████████████████████████████████████████████████████
12 │  118  ████████████████████████████████████████████████████████████ ← 정오 수렴(최다)
13 │  111  ███████████████████████████████████████████████████████
14 │  113  ████████████████████████████████████████████████████████
15 │  110  ███████████████████████████████████████████████████████
16 │  114  █████████████████████████████████████████████████████████ ← 마감 직후
17 │   18  █████████        ← 인트라데이 종료, 뉴스 evening
18 │   28  ██████████████   ← EOD 집중(중량 태스크 밀집, §5.1)
19 │   16  ████████
20 │   15  ████████         ← sync-sp500-financials
21 │   14  ███████
22 │   15  ████████         ← economic-indicators(FRED)
23 │   14  ███████
```
> 09–16시 plateau(~110)의 **60/시는 `refresh-market-pulse-cache`(매분)** 가 차지 — 캐시 갱신은 경량(DB/Redis)이라
> "API 압박"과는 별개다. 아래 4.2가 실제 외부 API 압박을 더 잘 보여준다.

### 4.2 외부 API 압박 / 시간 (cache·DB·neo4j-internal 제외, FMP+Gemini+FRED+News)

```
ET   ext   bar
00 │   0
01 │   1   ██              economic-calendar(FMP)
02 │   0                   (월간: sp500-constituents)
03 │   0                   (월간: korean-overviews=Gemini bulk)
04 │   0
05 │   1   ██              enrich-relationship-keywords(Gemini 100)
06 │   5   ██████████      economic-ind(FRED)+뉴스4
07 │   4   ████████        movers+press+category×2
08 │   3   ██████          keyword(LLM)+market-news+analyze-deep(LLM)
09 │  25   ██████████████████████████████████████████████████ ← FMP */5×2 개시 + extract-relations(LLM)
10 │  27   ██████████████████████████████████████████████████████ +sp500-news+analyze-deep+co-mention
11 │  24   ████████████████████████████████████████████████
12 │  28   ████████████████████████████████████████████████████████ ← FMP×2+FRED+뉴스×2+analyze-deep(최다)
13 │  26   ████████████████████████████████████████████████████
14 │  27   ██████████████████████████████████████████████████████
15 │  26   ████████████████████████████████████████████████████
16 │  27   ██████████████████████████████████████████████████████ +analyze-deep+extract-keywords
17 │   4   ████████        daily-prices(FMP)+뉴스3
18 │   6   ████████████    EOD-prices+thesis-readings+analyze-deep+thesis-summaries+economic-ind+뉴스 ← 중량 spike
19 │   1   ██              collect-ml-labels
20 │   1   ██              sync-sp500-financials(101)
21 │   0
22 │   1   ██              economic-indicators(FRED)
23 │   0
```
> 09–16시의 24~28은 대부분 **FMP `*/5`(realtime+indices=24/시)**. 이 구간 FMP 한도 안전성은 §2.1-(A) 검증에 달림.
> 18시 막대는 수치는 낮아도 **개당 무게(500심볼 EOD, LLM 50건, thesis 체인)** 가 커서 실질 피크다.

### 4.3 Gemini(LLM) 발화 / 시간 — 15 RPM 집중 구간

```
ET   LLM   tasks
03 │  ▲    (월간) korean-overviews bulk
05 │  ●    enrich(100건)
08 │  ●●   keyword + analyze-deep(50)
09 │  ●    extract-news-relations
10 │  ●●   co-mentions + analyze-deep(50)
12 │  ●    analyze-deep(50)
14 │  ●    analyze-deep(50)
16 │  ●●   analyze-deep(50) + extract-keywords   ← 15분 분산으로 해소(P0#8)
18 │  ●●   analyze-deep(50) + thesis-summaries   ← ⚠️ 5분 간격, 미해소(P-NEW-1)
```

---

## 5. 스케줄 겹침 / 의존성 분석

### 5.1 EOD 체인(18:00 ET) — ⚠️ 경합·순서 위험 HIGH

설계 의존: `sync-sp500-eod-prices(18:00)` → `update-sp500-change-percent(18:30)` → `run-eod-pipeline(18:30)`

| 문제 | 상세 | 심각도 |
|------|------|--------|
| **18:30 동시 발화 race** | `update-sp500-change-percent`(18:30)와 `run-eod-pipeline`(18:30)이 **같은 분**. eod-pipeline이 change_percent를 읽는데, change-percent 계산 완료 전 시작 시 **stale 데이터** | ⚠️ HIGH |
| **30분 윈도 가정** | eod-pipeline/change-percent는 `sync-sp500-eod-prices`(18:00)가 30분 내 완료 전제. 500심볼 sync가 FMP 한도(§2.1-B)로 지연되면 **불완전 가격 위에서 파이프라인 실행** | ⚠️ HIGH |
| **thesis 체인 경합** | `thesis-update-readings`(18:00)가 같은 18:00 `sync-sp500-eod-prices`와 FMP 경합 → readings 지연 → `thesis-calculate-scores`(18:15)가 미완 readings 위에서 계산 | ⚠️ MEDIUM-HIGH |

> 권장(감사 의견, 수정 아님): eod-pipeline을 change-percent **완료 신호 후** 트리거(chain/chord)하거나 18:30→18:40으로 분리.

### 5.2 thesis EOD 체인(18:00→18:35) — 직렬 의존, 고정 간격

`readings(18:00)` → `scores(18:15)` → `snapshots(18:30)` → `summaries(18:35)`.
15/15/5분 고정 간격. 선행이 간격 초과 시 후행이 미완 데이터로 진행. summaries는 §2.2의 Gemini 충돌도 겹침.

### 5.3 News v3 파이프라인 — 단계 분산 설계 양호 ✓ (자가치유)

`collect(*) → classify(:15) → analyze-deep(:30) → sync-neo4j(:45)` 15분 단계.
- `classify_news_batch(hours=3)` / `analyze(max_articles)` 가 **lookback 기반**이라 일부 지연돼도 다음 사이클이 흡수 → **자가치유**. 양호.
- 단 §3.1의 neo4j 큐 starvation은 sync-neo4j 단계에 별도 영향.

### 5.4 토요일 chainsight 체인 — 장시간 오버런 위험 MEDIUM

`all-profiles(토 02:00, expires 7200=2h)` → `price-co-movement(토 03:00)` → `stale-decay(토 04:00)` → `aggregate-profiles(토 04:30)` → `validation-weekly-batch(토 05:00)`.
- `all-profiles`의 expires가 **2시간**인데 다음 단계가 **1시간 뒤(03:00)** → all-profiles가 1h 초과 시 price-co-movement와 중첩(둘 다 중량 연산). ⚠️

### 5.5 일요일 ML 체인 — 조밀 직렬 의존 MEDIUM

`train-importance-model(일 03:00)` → `shadow-report(03:30)` → `check-auto-deploy(04:00)` → `weekly-ml-report(04:15)` → `monitor-ml(04:20)` → `train-lightgbm(04:30)`.
15~30분 간격으로 6단계 직렬 의존. 한 단계 오버런 시 cascade. `cleanup-task-results(일 05:00)`로 마감.

### 5.6 타임존 주석 불일치 — 운영 혼선 LOW (문서 결함)

`CELERY_TIMEZONE='America/New_York'`이므로 모든 `crontab(hour=N)`은 **ET 발화**인데, 일부 주석은 "UTC"로 표기:
- `chainsight-heat-score-daily` 주석 "매일 07:00 **UTC**" → 실제 **07:00 ET**
- `chainsight-seed-selection` 주석 "13:00 **UTC**" → 실제 **13:00 ET**
- `chainsight-neo4j-dirty-sync` 주석 "04:30 **UTC**" → 실제 **04:30 ET**

→ 기능상 순서(heat 07:00 → seed 13:00)는 보존되나, **운영자 오해 유발**. 주석 정정 권장(코드 동작 변경 없음).

### 5.7 chainsight-co-mentions 선행성 — LOW

`co-mentions(10:00)`는 "뉴스 분류 후"라지만 `classify-news-batch`의 10시 발화는 `:15`(10:15) → co-mentions가 **먼저 실행**.
실제로는 08:15 분류 결과(2h 전) 사용. `days_back=7`이라 허용 범위. 무해하나 주석 의도와 미세 불일치.

---

## 6. 발견사항 요약 (우선순위)

| ID | 발견 | 심각도 | 위치 | 검증/조치 방향(감사 의견) |
|----|------|--------|------|------------------------|
| F-0 | config dict가 DatabaseScheduler로 런타임 무시 가능 — DB drift | **선결** | celery.py:124 | PeriodicTask ↔ dict diff 우선 |
| P-NEW-2 | neo4j solo 큐에서 `sec-sync-dirty`(expires 240s) 가 장시간 태스크에 굶주려 **무음 폐기** | **HIGH** | §3.1 | sec-dirty 큐 분리 / 장시간 태스크 격리 |
| F-EOD | 18:30 change-percent ↔ eod-pipeline race + 18:00 sync 30분 윈도 가정 | **HIGH** | §5.1 | chain 트리거 또는 시차 |
| F-FMP-A | 인트라데이 `*/5`×2 FMP가 심볼당 호출이면 300/min 초과 | **HIGH(검증)** | §2.1-A | batch-quote 사용 여부 확인 |
| F-FMP-B | 18:00 eod-prices(500심볼)+thesis-readings 동시 FMP 경합 | **HIGH(검증)** | §2.1-B | 페이싱/chunk 확인 |
| F-GEM | analyze-deep(50)/enrich(100) 배치 내부 페이싱 없으면 15 RPM 위반 | **HIGH(검증)** | §2.2 | 태스크 내부 sleep 확인 |
| P-NEW-1 | 18:30 analyze-deep ↔ 18:35 thesis-summaries Gemini 5분 간격(16:30 사례 미적용) | MEDIUM | §2.2,§4.3 | 16:30처럼 분산 |
| F-THESIS | thesis 18:00 readings가 FMP 경합으로 지연 시 후속 체인 stale | MEDIUM-HIGH | §5.2 | |
| F-SAT | 토 all-profiles(expires 2h) ↔ price-co-movement(1h 뒤) 중첩 가능 | MEDIUM | §5.4 | 간격 확대 |
| F-TZ | 주석 "UTC" 표기 3건이 실제 ET와 불일치 | LOW(문서) | §5.6 | 주석 정정 |
| F-CACHE | refresh-market-pulse-cache(매분) expires 미설정 → 백로그 누적 | LOW | §3.2 | expires 추가 검토 |

---

## 7. 후속 검증 체크리스트 (코드 수정 전 확인용)

- [ ] `PeriodicTask.objects.values_list('name')` ↔ config dict 키 diff (F-0)
- [ ] `update_realtime_with_provider` — FMP batch-quote vs 심볼당 호출 (F-FMP-A)
- [ ] `sync_sp500_eod_prices` — chunk + sleep 페이싱 유무 (F-FMP-B)
- [ ] `analyze_news_deep`, `enrich_relationship_keywords` — LLM 호출 간 ≥4초 페이싱 (F-GEM)
- [ ] provider 태스크의 FMP→AV fallback 존재 여부 (§2.3)
- [ ] neo4j 큐 워커 평균 작업시간 vs sec-dirty 240s expire 실측 (P-NEW-2)
- [ ] run-eod-pipeline가 change_percent 완료를 보장받는 구조인지 (F-EOD)

---

*본 보고서는 `config/celery.py` 정적 분석 결과이며, 코드/스케줄을 수정하지 않았다. "검증 필요" 항목은 태스크 내부 구현(페이싱/배치)에 결과가 좌우되므로 별도 동적 확인이 필요하다.*
