# Celery Beat Schedule 감사 보고서

- **작성일**: 2026-05-30
- **대상**: `config/celery.py` `app.conf.beat_schedule` (86개 항목)
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (settings.py:489) — **모든 `crontab(hour=...)`는 NY 시간으로 해석됨**

---

## 0. 감사 전제 (Critical Caveat)

> **⚠️ 이 보고서의 1차 분석 대상인 `beat_schedule` dict는 런타임에 무시된다.**
> `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` (settings.py:490) 설정으로
> Beat는 DB의 `django_celery_beat.PeriodicTask` 테이블을 진실의 소스로 사용한다. (celery.py:123-140 주석 참조, common-bug #28)
>
> 따라서 본 보고서는 **"설계 의도된 스케줄 선언"**을 분석한 것이며,
> **실제 운영 스케줄은 DB와의 diff 검증이 선행되어야 한다.** (아래 §5 권고 참조)

### 0-1. 타임존 해석 불일치 (P1 — 설계 의도 오류 의심)

`CELERY_TIMEZONE`이 `America/New_York`이므로 모든 `hour` 값은 NY 기준이다.
그런데 **일부 태스크 주석은 "UTC"로 표기**되어 있어, 작성자의 의도와 실제 실행 시각이 어긋날 가능성이 있다.

| 태스크 | 주석 표기 | 실제 실행 (NY) | 의도가 UTC였다면 실제 NY 시각 |
|--------|----------|---------------|------------------------------|
| `chainsight-heat-score-daily` | "07:00 UTC" | **NY 07:00** | 02:00~03:00 (의도와 4~5h 차이) |
| `chainsight-seed-selection` | "13:00 UTC" | **NY 13:00** | 08:00~09:00 |
| `chainsight-neo4j-dirty-sync` | "04:30 UTC" | **NY 04:30** | 00:30 |

> 의존성 순서(heat → seed)는 NY 해석에서도 07:00 → 13:00으로 유지되므로 **기능 파손은 없으나**,
> 시각 의도가 틀어진 채 운영 중일 수 있다. DB의 PeriodicTask `timezone` 필드까지 교차 확인 필요.

---

## 1. Rate Limit 초과 구간 분석

### 1-1. FMP (Starter Plan: 300 calls/min, 10,000/일)

**FMP 의존 태스크 식별 (12종):**

| 태스크 | 시각(NY) | 호출 규모 | Rate Limit 관리 | 위험도 |
|--------|---------|----------|----------------|--------|
| `update-realtime-prices` | 09–16 매5분 | portfolio 10종목, 1s sleep | ✅ 자체 sleep | 🟢 낮음 |
| `update-market-indices` | 09–16 매5분 | 지수 소수 | (service 내부) | 🟢 낮음 |
| `sync-daily-market-movers` | 07:30 | gainers/losers | (service 내부) | 🟢 낮음 |
| `collect-press-releases-fmp` | 07:45 | 50 symbols | (내부) | 🟡 중간 |
| `collect-general-news-fmp-*` | 06:45 / 12:30 / 17:45 | general feed | (내부) | 🟢 낮음 |
| `collect-sp500-news-fmp-*` | 06:15/10:15/13:15/15:15/17:15 | **S&P500 전체 orchestrator** | (orchestrator 분산 추정) | 🟡 중간 |
| `update-daily-prices` | 17:00 | (= realtime 재사용) | ✅ | 🟢 낮음 |
| `sync-sp500-eod-prices` | 18:00 | **~500종목, 0.3s/종목** | ✅ `REQUEST_DELAY=0.3` → ~200/min | 🟡 중간 |
| `sync-sp500-financials` | 20:00 | **101종목 × ~4 statement** | ✅ 7s countdown 분산 (~8.5/min, 12분 소요) | 🟢 낮음 |
| `sync-sp500-constituents` | 월1일 02:00 | 1회 | ✅ | 🟢 낮음 |

**검증 결과:**
- `sync_sp500_financials`: `apply_async(countdown=i*7)`로 7초 간격 분산 → **모범 사례** (tasks.py:190-196)
- `sync_sp500_eod_prices`: `REQUEST_DELAY=0.3`초/종목 → 단독 실행 시 ~200 calls/min, **300 한도 내 안전**
- `update_realtime_with_provider`: portfolio 최대 10종목 + 1s sleep → 경량 (tasks.py:382-409)

**⚠️ FMP 동시 실행 합산 위험 구간:**

| 시각(NY) | 동시 FMP 태스크 | 합산 추정 | 비고 |
|---------|----------------|----------|------|
| **18:00** | `sync-sp500-eod-prices`(~200/min) + `collect-market-news-evening` + `update-economic-indicators`(FRED) | eod 단독으로도 200/min 점유 | eod가 2.5분간 200/min 유지 중 다른 FMP 호출 겹치면 **300 근접** 🟡 |
| 09–16 매5분 | `realtime`(10) + `market-indices`(소수) | <30/min | 🟢 |
| 17:15 | `collect-sp500-news-fmp-1715` + `collect-general-news-fmp-evening`(17:45 별개) | 분리됨 | 🟢 |

> **결론**: 개별 태스크는 rate limit을 잘 관리하나, **18:00 EOD 윈도우**에서 `sync-sp500-eod-prices`(200/min, 2.5분 지속)와
> 다른 FMP 태스크가 겹치면 합산 300/min에 근접할 수 있다. EOD 전용 윈도우 동안 FMP 태스크 분리 권장.

### 1-2. Gemini (Free Tier: 15 RPM, 1500 RPD)

**Gemini 의존 태스크 식별 (6종):**

| 태스크 | 시각(NY) | 분당 호출 패턴 | 위험도 |
|--------|---------|---------------|--------|
| `enrich-relationship-keywords` | 05:30 | limit=100 | 🟡 |
| `keyword-generation-pipeline` | 08:00 | gainers 키워드 | 🟡 |
| `analyze-news-deep-batch` | **08:30/10:30/12:30/14:30/16:30/18:30** (매2시간) | **max_articles=50** | 🔴 높음 |
| `extract-daily-news-keywords` | 16:45 | daily keywords | 🟡 |
| `thesis-generate-summaries` | 18:35 | thesis 요약 | 🟡 |
| `refresh-korean-overviews-monthly` | 월1일 03:00 | bulk 한글 개요 | 🟡 |

> ※ `classify-news-batch`는 **규칙 엔진**(rule-based, importance_score 계산)으로 **Gemini 미사용** 확인 (news/tasks.py docstring).
> ※ `chainsight-co-mentions`, `extract-news-relations`의 LLM 사용 여부는 별도 task 본문 확인 필요 (미검증).

**Gemini 동시 호출 위험 구간:**

| 시각(NY) | 동시 Gemini 태스크 | 상태 |
|---------|-------------------|------|
| **16:30 + 16:45** | `analyze-news-deep-batch`(50건) + `extract-daily-news-keywords` | ✅ **이미 15분 분산 처리됨** (audit P0 #8, celery.py:290-296) |
| **18:30 + 18:35** | `analyze-news-deep-batch`(50건) + `thesis-generate-summaries` | 🔴 **5분 간격** — analyze 50건이 15 RPM이면 ~3.3분 소요, summaries와 RPM 윈도우 겹칠 수 있음 |
| 08:00 + 08:30 | `keyword-generation` + `analyze-news-deep` | 🟡 30분 간격, 안전 여유 |

> **핵심 리스크 (P1)**: `analyze-news-deep-batch`가 **max_articles=50**인데 Gemini Free 15 RPM 기준
> 50건 처리에 최소 **3분 20초** 소요 (배치당 1 RPM 가정 시). 18:30 시작 → 18:33까지 RPM 윈도우 점유 →
> **18:35 `thesis-generate-summaries`와 충돌 가능**. 16:30 사례처럼 15분 분산이 적용되지 않은 유일한 구간.

**Gemini RPD(1500/일) 누적 점검:**
- `analyze-news-deep-batch` 6회 × 50건 = 300 호출/일 (배치 내부 호출 수에 따라 증폭 가능)
- 기타 Gemini 태스크 합산 시 일일 한도 여유는 있으나, analyze 배치의 내부 article별 호출 수 확인 필요.

### 1-3. Alpha Vantage (5 calls/min)

**beat_schedule 내 Alpha Vantage 직접 의존 태스크 — 식별되지 않음.**
- 모든 가격/재무 동기화는 **FMP Provider** 경로 사용 (`update_realtime_with_provider`, `sync_sp500_*`).
- AV는 CLAUDE.md에 rate limit이 명시되어 있으나, **현재 beat 스케줄에서는 호출 경로가 보이지 않음.**
- ✅ AV 5/min 초과 위험: **해당 없음** (단, 태스크 내부에서 AV fallback을 호출하는 경우가 있다면 별도 추적 필요).

---

## 2. Queue 몰림 분석 (default vs neo4j)

### 2-1. neo4j 큐 (solo pool — 동시 1개 제약) 🔴 핵심 병목

`task_routes`로 neo4j 큐에 라우팅되는 태스크 + `options.queue='neo4j'` 지정 태스크:

| 태스크 | 시각(NY) | 빈도 |
|--------|---------|------|
| `sec-sync-dirty-neo4j` | **매 5분 (상시)** | 12회/시간 = 288회/일 |
| `sync-news-to-neo4j` | 08:45/10:45/12:45/14:45/16:45/18:45 | 6회/일 |
| `neo4j-health-check` | 00:00/06:00/12:00/18:00 (매6h) | 4회/일 |
| `chainsight-sync-profiles-neo4j` | 12:00 | 1회/일 |
| `chainsight-sync-relations-neo4j` | 12:30 | 1회/일 |
| `enrich-relationship-keywords` | 05:30 | 1회/일 |
| `cleanup-expired-news-relationships` | 04:00 | 1회/일 |
| `chainsight-neo4j-dirty-sync` | 일요일 04:30 | 주1회 |

**solo pool 동시 1개 → 직렬화 밀림 구간:**

| 시각(NY) | neo4j 큐 동시 진입 | 밀림 분석 |
|---------|-------------------|----------|
| **12:00** | `sec-sync-dirty-neo4j`(:00) + `neo4j-health-check`(:00) + `chainsight-sync-profiles-neo4j`(:00) | 🔴 3개가 1워커에 큐잉 → health/profiles가 sec-dirty 뒤로 직렬 대기 |
| **12:30** | `sec-sync-dirty-neo4j`(:30) + `chainsight-sync-relations-neo4j`(:30) | 🟡 2개 직렬 |
| **:45 매번** | `sec-sync-dirty-neo4j`(:45) + `sync-news-to-neo4j`(:45) | 🟡 6개 시간대에서 반복 충돌 |
| 18:00 | `sec-sync-dirty-neo4j`(:00) + `neo4j-health-check`(:00) | 🟡 2개 직렬 |

> **핵심 리스크 (P1)**: `sec-sync-dirty-neo4j`가 **매 5분 상시 실행**되면서 solo pool 1슬롯을 주기적으로 점유한다.
> `expires=240`(4분)으로 만료 보호는 있으나, sec-dirty 작업이 길어지면 **`sync-news-to-neo4j`, `chainsight-sync-*`가 밀려
> expires(3600) 내 미실행 → 조용한 스킵** 가능. 특히 12:00은 3중 충돌.
>
> **권고**: neo4j 큐 태스크들의 분(minute) 오프셋을 sec-dirty의 `*/5`(00,05,...,55)와 **겹치지 않게** 재배치
> (예: health-check를 :02, sync-news를 :47 등). 또는 sec-dirty를 별도 큐로 분리.

### 2-2. default 큐 부하

default 큐는 prefork(Linux) / solo(macOS, celery.py:36-37) — macOS 운영 시 default도 동시 1개.
> **macOS 운영 주의**: `IS_MACOS`면 default 큐도 solo pool → 아래 §3 피크 시간대(18:00 13개 태스크)가 **직렬 처리**되어 지연 누적.
> 운영 환경이 macOS인지 Linux(prefork)인지에 따라 피크 부하 체감이 크게 달라짐.

---

## 3. 시간대별 API 호출 히트맵 (평일 Mon–Fri, NY 시간)

### 3-1. One-shot 태스크 밀집도

```
시각(NY) 태스크수  히트맵                              KST(EDT기준+13h)
─────────────────────────────────────────────────────────────────
00:00  │ 1  │ █                                   │ 13:00
01:00  │ 1  │ █                                   │ 14:00
02:00  │ 0  │                                     │ 15:00
03:00  │ 0  │                                     │ 16:00
04:00  │ 1  │ █                                   │ 17:00
05:00  │ 1  │ █                                   │ 18:00
06:00  │ 5  │ █████                               │ 19:00
07:00  │ 6  │ ██████                              │ 20:00
08:00  │ 5  │ █████  ◀ Gemini(keyword+analyze)    │ 21:00
09:00  │ 2  │ ██     ◀ 시장개장 bg 시작           │ 22:00
10:00  │ 5  │ █████  ◀ Gemini(analyze)            │ 23:00
11:00  │ 1  │ █                                   │ 00:00
12:00  │ 10 │ ██████████ ◀ neo4j 3중충돌+Gemini   │ 01:00
13:00  │ 3  │ ███                                 │ 02:00
14:00  │ 5  │ █████  ◀ Gemini(analyze)            │ 03:00
15:00  │ 2  │ ██                                  │ 04:00
16:00  │ 6  │ ██████ ◀ Gemini(analyze+keywords)   │ 05:00
17:00  │ 4  │ ████                                │ 06:00
18:00  │ 13 │ █████████████ ◀◀◀ PEAK             │ 07:00 ★
19:00  │ 2  │ ██                                  │ 08:00
20:00  │ 1  │ █  ◀ financials(분산)               │ 09:00
21:00  │ 0  │                                     │ 10:00
22:00  │ 1  │ █                                   │ 11:00
23:00  │ 0  │                                     │ 12:00
─────────────────────────────────────────────────────────────────
        (+ 상시 배경: sec-dirty-neo4j ×12/h, pipeline-alerts ×2/h)
        (+ 09–16 시장배경: realtime/indices ×12/h, pulse ×60/h,
                            portfolio ×6/h, screener-alerts ×4/h)
```

### 3-2. 리소스별 부하 히트맵 (피크 시간대 집중도)

```
시각(NY)  FMP        Gemini     neo4j큐    default
────────────────────────────────────────────────────
06:00    ██ (2)     ·          ·          ███
07:00    ██ (2)     ·          ·          ████
08:00    ·          █ (1)      █ (1)      ████
10:00    █ (1)      █ (1)      █ (1)      ███
12:00    █ (1)      █ (1)      ███ (3)◀   ██████
14:00    ·          █ (1)      █ (1)      ███
16:00    ·          ██ (2)◀    █ (1)      ████
18:00    ██ (2)     █ (1)      ██ (2)     ██████████ ◀ PEAK
20:00    █ (1)      ·          ·          █
────────────────────────────────────────────────────
```

### 3-3. 피크 시간대 식별

| 순위 | 시각(NY) | KST | 태스크 수 | 주요 부하 |
|------|---------|-----|----------|----------|
| 🥇 **1위** | **18:00–18:45** | 07:00–07:45 | **13개** | EOD 가격(FMP 200/min) + Thesis 파이프라인 4단 + Gemini analyze + neo4j sync |
| 🥈 2위 | 12:00–12:45 | 01:00–01:45 | 10개 | neo4j 3중 충돌 + Gemini analyze + FMP general news |
| 🥉 3위 | 07:00 / 16:00 | 20:00 / 05:00 | 6개 | 뉴스 수집 집중 / Gemini 2종 동시 |

> **최대 피크 = 18:00 NY (= 07:00 KST)**. macOS solo pool 운영 시 13개 태스크가 직렬 처리되어
> 18:00~19:00 사이 지연 누적 위험. Daily report 메일(07:00 KST, 운영 인프라 메모 참조)과 시간대 겹침.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 선행-후속 의존 체인 (시각 간격 검증)

| 체인 | 순서 | 간격 | 판정 |
|------|------|------|------|
| **EOD 가격 → 파생 계산** | `sync-sp500-eod-prices`(18:00) → `update-sp500-change-percent`(18:30) → `run-eod-pipeline`(18:30) | 30분 | 🟡 eod가 ~2.5분 소요라 30분 여유는 충분하나, **change-percent와 eod-pipeline이 18:30 동시 시작** — change-percent가 eod-pipeline보다 먼저 끝난다는 보장 없음 (둘 다 :30) |
| **Thesis 파이프라인** | `thesis-update-readings`(18:00) → `calculate-scores`(18:15) → `create-snapshots`(18:30) → `generate-summaries`(18:35) | 15/15/5분 | 🟡 update-readings가 18:00 FMP 혼잡과 겹침. readings 지연 시 scores가 빈 데이터로 계산될 위험 |
| **News 파이프라인** | collect → `classify`(:15) → `analyze-deep`(:30) → `sync-neo4j`(:45) | 15분씩 | ✅ 잘 분산됨 |
| **Chainsight (heat→seed)** | `heat-score`(07:00) → `seed-selection`(13:00) | 6시간 | ✅ 충분 (단 §0-1 타임존 의도 확인) |
| **Chainsight 동기화** | `sync-profiles-neo4j`(12:00) → `sync-relations-neo4j`(12:30) | 30분 | 🟡 neo4j solo pool에서 sec-dirty와 경합 시 profiles 지연 → relations가 미완 profiles 위에서 동작 가능 |

### 4-2. 데이터 경합 위험 구간

| 시각(NY) | 경합 시나리오 | 위험도 |
|---------|--------------|--------|
| **18:00** | `sync-sp500-eod-prices`가 DailyPrice 쓰는 중 → `thesis-update-readings`가 같은 DailyPrice 읽기 | 🔴 readings가 eod 미완료 데이터를 읽을 수 있음. eod(2.5분) vs readings 시작 동시 → **race condition** |
| **18:30** | `update-sp500-change-percent`(DailyPrice 최신 2일 읽기) + `run-eod-pipeline`(시그널 계산) 동시 | 🟡 둘 다 :30, change-percent 선행 보장 없음 |
| **12:00 / :30** | neo4j sync-profiles → sync-relations가 solo pool에서 직렬 대기 중 sec-dirty 끼어듦 | 🟡 순서 보장 약화 |

> **핵심 리스크 (P1)**: 18:00의 `sync-sp500-eod-prices`(soft_time_limit=1800, 실제 ~2.5분)와
> `thesis-update-readings`(18:00 동시 시작)가 **같은 DailyPrice 테이블을 동시 접근**.
> Thesis가 EOD 갱신 완료 전 읽으면 전일 데이터로 스코어 계산 → 잘못된 알림 발송 가능.
> **권고**: `thesis-update-readings`를 18:05~18:10으로 지연시켜 EOD 완료 후 시작 보장.

---

## 5. 종합 권고 (우선순위순)

| # | 우선순위 | 항목 | 권고 |
|---|---------|------|------|
| 1 | 🔴 P0 | **DB-config drift 검증** | `set(PeriodicTask.objects.values_list('name',flat=True))` vs config dict 키 diff 수동 실행 (celery.py:138 절차). 본 보고서는 config 기준이므로 DB 실제 등록 상태 확인이 선행되어야 함 |
| 2 | 🔴 P1 | **18:00 EOD vs Thesis 경합** | `thesis-update-readings`를 18:05+로 지연 (DailyPrice race 회피) |
| 3 | 🔴 P1 | **18:30 Gemini 충돌** | `analyze-news-deep-batch`(18:30, 50건 ~3.3분)와 `thesis-generate-summaries`(18:35) 간격을 16:30 사례처럼 15분+ 분산 |
| 4 | 🟡 P1 | **neo4j 큐 :00/:45 충돌** | sec-dirty(`*/5`)와 겹치는 health-check(:00), sync-news(:45), chainsight-sync(:00/:30)의 minute 오프셋 재배치 또는 sec-dirty 별도 큐 |
| 5 | 🟡 P2 | **타임존 주석 불일치** | chainsight-heat/seed/dirty의 "UTC" 주석 → 실제 NY 실행. 의도 재확인 후 주석 또는 hour 정정 |
| 6 | 🟡 P2 | **18:30 동시 :30 태스크 선후행** | `update-sp500-change-percent`와 `run-eod-pipeline`을 :30/:35로 분리해 선행 보장 |
| 7 | 🟢 P3 | **macOS solo pool 피크 직렬화** | 운영이 macOS면 18:00 피크 13개 직렬 처리. Linux prefork 운영 전환 또는 피크 분산 검토 |

---

## 부록 A. 전체 태스크 인벤토리 (86개)

| 분류 | 개수 | 외부 의존 |
|------|------|----------|
| Stocks (가격/재무) | 6 | FMP |
| Macro (거시) | 5 | FRED, FMP |
| News 수집 | 13 | FMP, news provider |
| News Intelligence v3 | 11 | Gemini(analyze), 규칙(classify), neo4j |
| FMP 대량 뉴스 | 9 | FMP |
| Chainsight | 13 | Gemini(일부), neo4j |
| SEC Pipeline | 3 | neo4j (sec-dirty `*/5`) |
| Thesis Control | 4 | Gemini(summaries), DailyPrice |
| Screener/Validation | 4 | (내부 계산) |
| RAG/ETF/Supply/기타 | 8 | neo4j, FMP |
| 운영(에러/정리) | 4 | (내부) |

## 부록 B. 검증 출처

- `config/celery.py:141-820` (beat_schedule 전체)
- `config/settings.py:489-497` (CELERY_TIMEZONE, BEAT_SCHEDULER, MAX_TASKS_PER_CHILD)
- `packages/shared/stocks/tasks.py:138-211` (financials 7s 분산)
- `packages/shared/stocks/tasks.py:366-479` (realtime/eod)
- `packages/shared/stocks/services/sp500_eod_service.py:24` (REQUEST_DELAY=0.3)
- `news/tasks.py` (classify=규칙, analyze=gemini)
- `config/celery.py:43-61` (task_routes → neo4j 큐)

> ⚠️ **미검증 항목** (추가 확인 권장): ① DB PeriodicTask 실제 등록 상태 ② `analyze-news-deep-batch` 내부 article별 Gemini 호출 횟수 ③ `chainsight-co-mentions`/`extract-news-relations`의 LLM 사용 여부 ④ `collect_*_news` provider별 실제 FMP vs marketaux/finnhub 분기 ⑤ 운영 OS (macOS solo vs Linux prefork)
