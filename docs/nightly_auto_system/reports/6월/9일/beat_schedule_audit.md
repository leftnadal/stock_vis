# Beat 스케줄 감사 보고서

- **생성일**: 2026-06-09
- **대상**: `config/celery.py` `app.conf.beat_schedule` (86개 항목)
- **유형**: 읽기 전용 감사 (코드 수정 없음)
- **기준 타임존**: `CELERY_TIMEZONE = 'America/New_York'` (config/settings.py:489)

---

## 0. 핵심 전제 / 방법론

### 0-1. 진실의 소스 경고 (P0 메타 이슈)

`config/celery.py:123-140`의 주석이 명시하듯, 이 프로젝트는
`CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'`를
사용한다. **따라서 `app.conf.beat_schedule` dict는 런타임에 무시되며**, 실제
실행 스케줄은 DB `django_celery_beat.PeriodicTask` 테이블이 진실의 소스다.

> **본 감사는 config dict를 "설계 의도(declared reference)"로 간주하고 분석한다.**
> 실제 부하를 단정하려면 `PeriodicTask.objects.all()`과 dict 키의 diff 검증이
> 선행되어야 한다 (공통 버그 #28). dict-DB drift가 있으면 아래 분석과 실제가
> 어긋날 수 있다. → **권고: §6 P0-1 참조**

### 0-2. 타임존 해석 경고 (P0)

모든 `crontab(hour=...)`은 **America/New_York(EST/EDT)** 로 해석된다. 그런데
일부 태스크 주석은 시간대를 **"UTC"** 로 표기한다 — 실제 실행 시각과 불일치:

| 태스크 | 주석 표기 | 실제 실행(NY) |
|--------|-----------|---------------|
| `chainsight-heat-score-daily` | "매일 07:00 **UTC**" (L747) | 07:00 **NY** |
| `chainsight-seed-selection` | "매일 13:00 **UTC**" (L754) | 13:00 **NY** |
| `chainsight-neo4j-dirty-sync` | "일요일 04:30 **UTC**" (L761) | 04:30 **NY** |

→ 주석만 보고 "시드 선정이 관계 동기화(12:00/12:30 NY) 후"라고 판단하면
맞지만, "UTC 기준"으로 외부 시스템과 정합을 맞추려는 의도였다면 **약 4~5시간
오차**. 주석-코드 정합성 점검 필요 (§5-3).

### 0-3. 카운팅 규칙

- 히트맵/카운트는 **평일(Mon–Fri) 1일** 기준 (피크 시나리오).
- 주말 전용/월간 태스크는 해당 요일·날짜에만 가산하며 평일 베이스라인에서 제외.
- `*/N` 반복은 해당 시간대 내 발생 횟수로 환산 (예: `*/5` in 1h = 12회).

---

## 1. 태스크 인벤토리 (86개)

### 1-1. 큐별 분류

| 큐 | 개수 | 동시성 제약 | 비고 |
|----|------|-------------|------|
| **default** (prefork/solo) | 79 | macOS=solo(1), Linux=prefork(N) | 대부분 |
| **neo4j** (solo 강제) | 7 | **동시 1개** | SIGSEGV 방지용 격리 |

**neo4j 큐 라우팅 태스크** (`task_routes` L43-61 + beat `options.queue`):

| 태스크 | 스케줄(NY) | 라우팅 근거 |
|--------|-----------|-------------|
| `neo4j-health-check` | `*/6h`, min0 | options.queue |
| `cleanup-expired-news-relationships` | 매일 04:00 | options.queue |
| `sync-news-to-neo4j` | 8,10,12,14,16,18시 :45 | options.queue |
| `enrich-relationship-keywords` | 매일 05:30 | options.queue |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | options.queue |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | task_routes |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | task_routes |
| **`sec-sync-dirty-neo4j`** | **`*/5분` (24h)** | **task_routes L60** ⚠️ |

> ⚠️ `sec-sync-dirty-neo4j`는 beat에 `options.queue` 미지정이나 `task_routes`의
> `services.sec_pipeline.tasks.sync_dirty_to_neo4j` 매핑(L60)으로 **neo4j 큐에
> 라우팅**된다. **5분마다 = 288회/일**이 동시성 1짜리 neo4j 큐를 점유. → §3-2 핵심.

### 1-2. 외부 API 의존 분류

| API | 한도 | 의존 태스크(주요) |
|-----|------|-------------------|
| **FMP** (Starter) | 300/min, 10k/일 | realtime-prices, market-indices, daily-prices, sp500-financials, sp500-eod-prices, market-movers, **sp500-news-fmp(×5)**, press-releases, general-news-fmp(×3), etf-holdings, sp500-constituents |
| **Gemini** (Free) | 15 RPM, 1500 RPD | keyword-generation, extract-daily-news-keywords, **analyze-news-deep(×6)**, enrich-relationship-keywords, thesis-generate-summaries, refresh-korean-overviews, validation-weekly |
| **FRED** | 관대(120/min) | update-economic-indicators(×4), update-economic-calendar |
| **뉴스 멀티프로바이더** (Marketaux/Finnhub) | 프로바이더별 상이 | collect-daily-news, collect-market-news, collect-category-news |
| **SEC EDGAR** | 10 req/s (fair use) | sync-supply-chain, sync-institutional, sec-check-new-filings, scan-regulatory |
| **Alpha Vantage** | 5/min | **활성 Beat 태스크 직접 의존 없음** (news provider enum으로만 존재, §2-3) |

---

## 2. Rate Limit 초과 구간 분석

### 2-1. FMP (300 calls/min, 10,000/일) — ⚠️ 시장시간 :15분 버스트

**버스트 후보 구간: 시장시간(09–16 NY) 매시 :15분**

`*/5` 페이싱 태스크는 매시 `:00,:05,:10,:15,...`에 발화한다. 시장시간 :15분에는
다음이 **동시 발화**:

| 태스크 | 추정 호출량 |
|--------|-------------|
| `update-realtime-prices` (*/5) | 1~수 콜 (bulk quote 가정) |
| `update-market-indices` (*/5) | 1~수 콜 (지수 소수) |
| `collect-sp500-news-fmp-{1015,1315,1515}` | **최대 ~500콜** (S&P500 전종목 순회) |

→ **`collect-sp500-news-fmp`가 10:15 / 13:15 / 15:15에 시장시간 `*/5` FMP
태스크와 정면 충돌**. orchestrator가 500종목을 무페이싱으로 순회하면 단일 분에
300콜을 초과할 수 있다.

- **완화 요인**: 이름이 `orchestrator`인 점은 내부 청크/sub-task 분산을 시사
  (페이싱 내장 가능성). **검증 필요** — 미페이싱이면 분당 300 초과 확정.
- **17:15 / 06:15**: 시장시간 외라 `*/5` 충돌 없음 → 상대적으로 안전.

**일일 FMP 콜 총량(거친 상한 추정)**:
- sp500-news-fmp 5회 × ~500 = ~2,500
- sp500-eod-prices(18:00) ~500 (bulk면 1)
- sp500-financials(20:00) 101종목 × 3~4 statement = ~350
- realtime/indices `*/5` × 8시간 × 12 × (1~3) = ~수백
- 기타 press/general/movers/etf = ~수백
- **합계 거친 상한 ~4,000~5,000/일** → 10k/일 한도 내. **분당 버스트가 진짜 리스크** (일일 총량 아님).

### 2-2. Gemini (15 RPM, 1500 RPD) — ⚠️ 18:30↔18:35 교차 위험

**단일 태스크는 안전**: `analyze_news_deep`는 **4초 간격 내부 페이싱**
(`tasks.py:561` 주석)으로 단독 실행 시 ≈15 RPM 준수.

**리스크는 태스크 간 동시성**: 각 Gemini 태스크가 독립적으로 ~15 RPM까지
페이싱하므로 **2개가 겹치면 ~30 RPM = 한도 2배 초과**.

| 시각(NY) | 동시 Gemini 태스크 | 상태 |
|----------|--------------------|------|
| 16:30 / 16:45 | analyze-deep(16:30) ↔ extract-keywords(16:45) | ✅ **15분 분산 완료** (L291-292, audit P0 #8) |
| **18:30 / 18:35** | analyze-deep(18:30, 최대50건×4초≈3.3분 → ~18:33 종료) ↔ **thesis-generate-summaries(18:35)** | ⚠️ **마진 ~2분**. analyze-deep가 재시도/50건 초과 시 18:35로 bleed → Gemini 동시 호출 |
| 08:00 / 08:30 | keyword-generation(08:00) ↔ analyze-deep(08:30) | ✅ 30분 간격 |
| 05:30 | enrich-relationship-keywords (limit 100, 단독) | ✅ 고립 |

→ **P1: 18:30 analyze-deep와 18:35 thesis-summaries는 안전 마진이 ~2분에
불과.** analyze-deep 실행시간이 길어지는 날(재시도, 상위 15% 기사 급증) Gemini
RPM 2배 초과 위험. 16:30/16:45처럼 **15분 분산 권고**.

**일일 RPD 추정**:
- analyze-deep 6회 × 최대 50 = 최대 300
- enrich 100 + keyword + extract + thesis-summaries(테제 N건) + classify(룰 기반, LLM 소량)
- **거친 상한 ~600~800/일** → 1500 RPD 한도 내 (여유 있음). **분당 RPM이 병목**.

### 2-3. Alpha Vantage (5 calls/min) — ✅ 활성 의존 없음

`grep` 결과 AV는 `services/news/models.py`(provider enum)와
`packages/shared/api_request/__init__.py`에만 존재. **활성 Beat 태스크 중 AV를
직접 호출하는 항목 미발견** (가격/뉴스 수집이 FMP·멀티프로바이더로 이관됨).
→ AV 5/min 한도는 **현재 Beat 스케줄에서 비활성 리스크**. (수동/온디맨드 경로는
별도 점검 대상이나 본 스케줄 감사 범위 밖.)

### 2-4. FRED — ✅ 안전

`update-economic-indicators` 4회/일(6,12,18,22시) + calendar 1회. FRED는 관대한
한도(~120/min). 충돌 무시 가능.

---

## 3. Queue 몰림 분석

### 3-1. default 큐 시간대별 부하

default 큐의 분당 최대 동시 부하는 **시장시간(09–16)** 에 집중되나, 그 대부분은
`refresh-market-pulse-cache`(**매 1분**, 60회/시)와 `*/5` 캐시/가격 태스크다 —
대체로 짧은 캐시 재계산. **순수 외부 API 부하 피크는 18:00–18:35 EOD 배치 묶음**
(아래 §4 히트맵 H18 참조).

### 3-2. neo4j 큐 — ⚠️ solo pool(동시 1) 밀림 가능성

neo4j 큐는 **`--pool=solo` 강제(동시성 1)**. 처리량이 단일 워커에 직렬화된다.

**상시 점유원**: `sec-sync-dirty-neo4j` **`*/5분` = 288회/일**. 단일 실행이
`expires=240`(4분) 내 끝나야 다음 발화와 안 겹친다. dirty evidence가 많은 날
1회 실행이 4분 초과 → 큐에 적체 + expires로 일부 누락 가능.

**겹침 위험 구간** (neo4j 큐에 동시 진입):

| 시각(NY) | neo4j 큐 동시 후보 |
|----------|---------------------|
| 매시 :45 (8,10,12,14,16,18) | `sync-news-to-neo4j` + 그 분의 `sec-sync-dirty`(:45) |
| **12:00** | `chainsight-sync-profiles-neo4j` + `sec-sync-dirty`(12:00) + (12:00 health 아님) |
| **12:30** | `chainsight-sync-relations-neo4j` + `sec-sync-dirty`(12:30) |
| 매일 04:00 | `cleanup-expired-news-relationships` + `sec-sync-dirty`(04:00) |
| 매일 05:30 | `enrich-relationship-keywords`(무거움, limit 100) + `sec-sync-dirty`(05:30) |
| 0/6/12/18시 :00 | `neo4j-health-check` + `sec-sync-dirty`(:00) |

→ 동시성 1이므로 이들은 **충돌이 아니라 직렬 대기**. 즉 데이터 경합은 없으나
**`sec-sync-dirty`의 5분 주기를 밀어내 SEC→Neo4j 동기화 지연**이 발생. 특히
`enrich-relationship-keywords`(05:30)나 `sync-news-to-neo4j`(:45)가 길면
그 동안 `sec-sync-dirty`가 큐에서 대기 → expires(4분) 만료로 **스킵**될 수 있음.

> **권고**: neo4j 큐의 상시 `*/5분` 폴러(sec-sync-dirty)와 주기적 무거운
> 동기화(enrich, sync-news)의 큐 분리 또는 sec-sync 주기 완화(*/10) 검토.

---

## 4. 시간대별 API 호출 히트맵 (평일, NY 기준)

### 4-1. 전체 태스크 발화 수 / 시간 (모든 큐 포함)

```
시(NY) │ 발화수 │ 막대 (■=2회, 시장시간 cache-refresh 60/h 포함)
───────┼────────┼──────────────────────────────────────────────────
 00    │   15   │ ■■■■■■■
 01    │   15   │ ■■■■■■■            (economic-calendar)
 02    │   14   │ ■■■■■■■            (월간: sp500-constituents/supply-chain)
 03    │   14   │ ■■■■■■■            (Sun/월간 ML·chainsight)
 04    │   15   │ ■■■■■■■            (cleanup-news-rel + Sun/Sat 다수)
 05    │   15   │ ■■■■■■■            (enrich-keywords + Sun cleanup)
 06    │   20   │ ■■■■■■■■■■          ◀ 뉴스수집 묶음 시작
 07    │   20   │ ■■■■■■■■■■          ◀ movers/press/heat/error-digest
 08    │   19   │ ■■■■■■■■■           (keyword-gen + v3 batch 시작)
 09    │  110   │ ████████████████████████████████████████████ ◀ 시장개장(cache 60/h)
 10    │  113   │ █████████████████████████████████████████████
 11    │  109   │ ████████████████████████████████████████████
 12    │  119   │ ███████████████████████████████████████████████ ◀ 피크(neo4j sync 묶음)
 13    │  111   │ ████████████████████████████████████████████
 14    │  113   │ █████████████████████████████████████████████
 15    │  110   │ ████████████████████████████████████████████
 16    │  114   │ █████████████████████████████████████████████ ◀ breadth/heatmap/keywords
 17    │   18   │ ■■■■■■■■■           ◀ 시장마감, daily-prices
 18    │   27   │ ■■■■■■■■■■■■■■      ◀◀ EOD 배치 슈퍼피크(API 밀집)
 19    │   16   │ ■■■■■■■■            (ml-labels, backfill)
 20    │   15   │ ■■■■■■■            (sp500-financials 101종목)
 21    │   14   │ ■■■■■■■
 22    │   15   │ ■■■■■■■            (economic-indicators)
 23    │   14   │ ■■■■■■■
```

> H09–16의 높은 수치는 **`refresh-market-pulse-cache`(매 1분=60/h)** 가 지배.
> 이는 캐시 재계산(외부 API 경량)이라 rate-limit 관점 부하는 아래 4-2가 더 정확.

### 4-2. 외부 API 호출 집약 히트맵 (cache-refresh 등 내부연산 제외)

```
시(NY) │ FMP │ Gemini │ News │ FRED │ neo4j큐 │ 핵심 이벤트
───────┼─────┼────────┼──────┼──────┼─────────┼──────────────────────────
 00    │  .  │   .    │  .   │  .   │  ●12+H  │ health(:00)+secdirty
 01    │  .  │   .    │  .   │  ◐   │  ●12    │ econ-calendar
 04    │  .  │   .    │  .   │  .   │  ●12+1  │ cleanup-news-rel
 05    │  .  │   ◆    │  .   │  .   │  ●12+1  │ enrich-keywords(무거움)
 06    │ ◐◐  │   .    │ ★★★  │  ◐   │  ●12+H  │ daily/cat-news + sp500-news-fmp + general-fmp
 07    │ ◐◐  │   .    │ ★★   │  .   │  ●12    │ movers/press/cat-low/heat/digest
 08    │  .  │   ◆    │ ★    │  .   │  ●12    │ keyword-gen(G) + market-news + v3 classify
 09    │ ◐◐  │   .    │  .   │  .   │  ●12    │ realtime+indices(*/5) + sentiment집계
 10    │ ◐◐★ │   ◆    │  .   │  .   │  ●12+◆  │ sp500-news-fmp-1015 ⚠️ + analyze-deep(G) + sync-news-neo4j
 11    │ ◐◐  │   .    │  .   │  .   │  ●12    │ realtime+indices
 12    │ ◐◐★ │   ◆    │ ★    │  ◐   │ ●12+◆◆+H│ ⚠️FMP+G+neo4j 3중(profiles/relations sync, sec-seed)
 13    │ ◐◐★ │   .    │ ★    │  .   │  ●12    │ sp500-news-fmp-1315 ⚠️ + cat-high + seed-selection
 14    │ ◐◐  │   ◆    │ ★★   │  .   │  ●12+◆  │ daily-news-pm + cat-med + analyze-deep(G)
 15    │ ◐◐★ │   .    │ ★    │  .   │  ●12    │ sp500-news-fmp-1515 ⚠️ + market-news-pm
 16    │ ◐◐  │   ◆    │  .   │  .   │  ●12+◆  │ analyze-deep(16:30,G) + extract-keywords(16:45,G) + breadth/heatmap
 17    │ ◐★  │   .    │ ★    │  .   │  ●12    │ daily-prices + sp500-news-fmp-1715 + general-fmp-pm
 18    │ ★★★ │  ◆◆?   │ ★    │  ◐   │  ●12+◆  │ ◀◀ EOD슈퍼피크: eod-prices+thesis+eod-pipeline + analyze-deep(18:30,G)+thesis-summaries(18:35,G)
 19    │  .  │   .    │  .   │  .   │  ●12    │ ml-labels, backfill-accuracy
 20    │ ★★  │   .    │  .   │  .   │  ●12    │ sp500-financials(101종목, 고립)
 22    │  .  │   .    │  .   │  ◐   │  ●12    │ econ-indicators

범례: ◐ FMP 경량  ★ FMP/뉴스 대량(수십~수백콜)  ◆ Gemini  ● neo4j */5폴러(12/h)
      H neo4j-health-check  ⚠️ = */5 FMP와 sp500-news-fmp 충돌 구간
```

**피크 식별**:
1. **H18 (18:00–18:35 NY)** — 절대 피크. FMP 대량(eod-prices+thesis-readings) +
   Gemini 2종(analyze-deep 18:30 / thesis-summaries 18:35) + EOD 파이프라인.
2. **H12 (12:00–12:45 NY)** — FMP(sp500-news-fmp-X 아님, 12:30 general-fmp) +
   Gemini(analyze-deep) + **neo4j 큐 3중**(profiles/relations sync + sec-seed + secdirty).
3. **H10/H13/H15 :15** — sp500-news-fmp ↔ 시장시간 `*/5` FMP 충돌.

---

## 5. 스케줄 겹침 / 의존성 분석

### 5-1. 선행-후행 의존 체인 (정상 설계된 것)

| 체인 | 순서(NY) | 간격 | 평가 |
|------|----------|------|------|
| EOD 가격→파이프라인→정확도 | eod-prices(18:00) → run-eod-pipeline(18:30) → backfill-accuracy(19:00) | 30분 | ✅ 여유 |
| Thesis EOD | readings(18:00)→scores(18:15)→snapshots(18:30)→summaries(18:35) | 15/15/5분 | ⚠️ summaries 5분 마진 |
| News v3 | classify(:15)→analyze-deep(:30)→sync-neo4j(:45) | 15분씩 | ✅ 매 2시간 정연 |
| ChainSight 일일 | co-mentions(10:00)→relation-confidence(11:00)→sync-neo4j(12:00/12:30) | 1시간+ | ✅ |
| ChainSight 주말 | all-profiles(Sat02:00)→price-co-move(03:00)→stale-decay(04:00)→aggregate(04:30)→validation(05:00) | 정연 | ✅ |
| ML 주간(Sun) | train-importance(03:00)→shadow(03:30)→auto-deploy(04:00)→ml-report(04:15)→monitor(04:20)→lightgbm(04:30) | 정연 | ✅ |
| SEC→ChainSight | sec-seed-relations(12:00) — 시드 선정(13:00) 전 | 1시간 | ✅ (주석상) |

### 5-2. ⚠️ 잠재적 경합 / 마진 부족

1. **thesis-snapshots(18:30) ↔ run-eod-pipeline(18:30)** — **동일 분 발화**.
   둘 다 default 큐. macOS solo(동시1)면 직렬 → 한쪽 지연. 둘 다 DB 집약이라
   데이터 경합보단 처리 지연 이슈. Linux prefork면 병렬 → DB 부하 동시 상승.
2. **thesis-readings(18:00) ↔ sync-sp500-eod-prices(18:00)** — 동일 분. readings가
   FMP 의존이면 eod-prices와 FMP 동시 호출. 둘 다 시장마감 직후 무거움.
3. **analyze-deep(18:30) ↔ thesis-summaries(18:35)** — Gemini 5분 마진 (§2-2).
4. **sp500-news-fmp ↔ 시장 `*/5` FMP** (10:15/13:15/15:15) — FMP 분당 버스트 (§2-1).

### 5-3. 데이터 경합 가능성

- **선행 미완 시 후행 시작**: thesis 체인은 15분 간격이나 `update_indicator_readings`가
  지연되면 `calculate_scores`(18:15)가 **stale/부분 데이터로 계산**할 수 있음.
  태스크 간 명시적 완료 신호(chord/체인) 없이 시각 기반 분산만 사용 → **시각 가정이
  깨지면 정합 깨짐**. (현재 expires만 있고 의존성 lock 없음.)
- neo4j 큐 직렬화 덕에 neo4j 쓰기 경합은 구조적으로 차단(동시1) — 긍정적.

---

## 6. 발견사항 우선순위

### P0 (즉시 검증 권고)

| # | 발견 | 근거 | 권고 |
|---|------|------|------|
| P0-1 | **config dict ≠ DB PeriodicTask 가능성** | DatabaseScheduler 사용, dict 무시 (L123-140, 버그#28) | `set(PeriodicTask.objects.values_list('name',flat=True))` vs dict 키 diff 실행 — 본 감사 결론은 dict 기준이므로 DB와 어긋나면 무효 |
| P0-2 | **주석 "UTC" vs 실제 NY 불일치** | heat-score/seed-selection/neo4j-dirty (L747,754,761) | 주석 수정 또는 의도가 UTC였다면 스케줄 4~5h 조정 |

### P1 (개선 권고)

| # | 발견 | 근거 | 권고 |
|---|------|------|------|
| P1-1 | **sp500-news-fmp ↔ 시장 */5 FMP 버스트** (10:15/13:15/15:15) | §2-1 | orchestrator 페이싱 검증; 미페이싱이면 분당 300 초과. :15→:22 등 비동기 분 이동 |
| P1-2 | **analyze-deep(18:30)↔thesis-summaries(18:35) Gemini 2분 마진** | §2-2 | 16:30/16:45 선례처럼 15분 분산 (예: summaries 18:50) |
| P1-3 | **neo4j 큐 sec-sync-dirty(*/5) 적체** | §3-2 | enrich/sync-news와 큐 분리 또는 sec-sync */10 완화; expires<주기 점검 |
| P1-4 | **H18 EOD 슈퍼피크 동시 발화** (thesis-snapshots+eod-pipeline 18:30) | §5-2 | 분 단위 stagger (eod-pipeline 18:40 등) |

### P2 (관찰)

| # | 발견 | 권고 |
|---|------|------|
| P2-1 | thesis 체인 완료 신호 부재 (시각 가정 의존) | 향후 chord/signature 기반 의존성 전환 검토 |
| P2-2 | AV 한도(5/min) 활성 Beat 무관 | 현 스케줄선 무시 가능; 온디맨드 경로 별도 점검 |
| P2-3 | `refresh-market-pulse-cache` 매 1분(60/h×8h=480/일) | 캐시 재계산 비용·DB 부하 프로파일링 |

---

## 7. 결론

- **rate-limit 단일 최대 리스크**: FMP **분당 버스트**(일일 총량 아님) — 특히
  시장시간 :15분 `sp500-news-fmp` 동시 발화. orchestrator 내부 페이싱 검증이 관건.
- **Gemini**는 일일 RPD 여유, **RPM(분당)** 이 병목. 태스크 간 동시 실행만 막으면
  안전. 18:30/18:35 한 곳만 마진 부족.
- **neo4j 큐**는 동시성 1로 경합은 구조적 차단되나, `sec-sync-dirty(*/5)` 상시
  폴러가 무거운 동기화에 밀려 **SEC 동기화 지연/스킵** 가능.
- **시간대 피크**: H18(EOD 배치) > H12(FMP+Gemini+neo4j 3중) > H10/13/15(:15 FMP 충돌).
- **메타 리스크**: 본 분석은 config dict 기준 — **DB PeriodicTask와의 drift 검증이
  선행되지 않으면 실제 부하와 어긋날 수 있음** (P0-1).

> 본 보고서는 코드를 수정하지 않았으며, `config/celery.py` 정적 분석 + API 의존성
> grep 검증에 기반한다. 정량 콜 수는 "거친 상한 추정"이며, 정밀 측정은 실제
> 태스크 실행 로그(`stocks.log`, `_log_collection`)와 DB 스케줄 대조가 필요하다.
