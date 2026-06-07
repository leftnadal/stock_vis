# Beat Schedule 감사 보고서

- **대상**: `config/celery.py` `app.conf.beat_schedule` (70개 엔트리)
- **작성일**: 2026-06-07
- **모드**: 읽기 전용 (코드 수정 없음)
- **분석 기준**: `CELERY_TIMEZONE = 'America/New_York'` (모든 crontab은 **ET** 기준 해석)

---

## 0. 핵심 결론 (TL;DR)

| # | 심각도 | 발견 | 영향 |
|---|--------|------|------|
| F-1 | 🔴 P0 | **macOS 기본 워커도 사실상 solo (concurrency=1)** | `--concurrency=4`는 무력. default 큐 전체가 직렬 처리 → 18:30/12:00 클러스터 밀림 |
| F-2 | 🔴 P0 | **`beat_schedule` dict는 런타임에 무시됨** (DatabaseScheduler) | 본 감사는 "설계 의도" 분석. 실제 동작은 DB `PeriodicTask`와 대조 필요 |
| F-3 | 🟠 P1 | **18:00 / 18:30 EOD 클러스터 과밀** (default 큐 12개 고정 작업) | solo 직렬 → `run-eod-pipeline`(무거움)이 thesis/analyze 뒤로 밀림 |
| F-4 | 🟠 P1 | **neo4j solo 큐를 `sec-sync-dirty-neo4j`가 5분마다 종일 점유** | `expires=240s` < 5분 간격. 큐 정체 시 조용히 만료/스킵 |
| F-5 | 🟡 P2 | **타임존 주석 오류**: chainsight 주석 "UTC"라 표기, 실제 ET 실행 | heat-score/seed-selection이 의도와 5~6시간 어긋난 시각에 동작 |
| F-6 | 🟡 P2 | **`update-sp500-change-percent` ↔ `run-eod-pipeline` 동일 18:30** | 선행(change_percent) 완료 전 후행 시작 가능 → 데이터 경합 |
| F-7 | 🟢 양호 | **Gemini 15 RPM은 태스크 내부에서 4초 슬립으로 자율 준수** | `analyze_news_deep` 4초 간격(=15 RPM). 16:30 충돌은 16:45 분산으로 기해소 |
| F-8 | 🟢 양호 | **Alpha Vantage는 Beat 스케줄에 의존 태스크 없음** | 거시지표=FRED, 시세=FMP. AV 5/min 한도 압박 없음 |

---

## 1. 런타임 현실 — 분석의 전제 (가장 중요)

### 1-1. dict는 무시된다 (F-2)
```python
# config/settings.py
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```
`beat_schedule` dict는 **선언적 reference**일 뿐, Beat는 DB `django_celery_beat.PeriodicTask`를 진실의 소스로 사용한다. config 주석에도 명시(L124~140). 본 보고서는 **dict = 설계 의도**로 간주하고 분석한다. 실제 위험 확정은 다음으로 교차검증해야 한다:

```text
python manage.py shell
>>> set(PeriodicTask.objects.values_list('name', flat=True)) ^ set(<dict keys>)
```

### 1-2. 양 큐 모두 concurrency=1 (F-1, P0)
```python
# config/celery.py L36-37
if IS_MACOS:
    app.conf.worker_pool = 'solo'   # ← CLI --pool 미지정 시 이 설정이 적용됨
```
| 워커 | 기동 스크립트 | 실제 동시성 | 비고 |
|------|--------------|------------|------|
| default | `scripts/celery-worker.sh` → `--concurrency=4` | **1 (solo)** | `worker_pool='solo'`가 CLI `--concurrency`를 무력화. **4는 착시** |
| neo4j | `scripts/celery-worker-neo4j.sh` → `--pool=solo --concurrency=1` | **1 (solo)** | 명시적 solo (common-bugs #25) |

> **결론**: 이 macOS 운영 박스에서는 **두 큐 모두 한 번에 1개 태스크만** 처리한다. 동시간대에 N개가 enqueue되면 N개가 **직렬**로 줄선다. 아래 모든 "몰림" 분석의 전제다. (프로덕션 Linux로 이전 시 default는 prefork 4로 복원되어 양상이 달라진다.)

### 1-3. 타임존 (F-5)
`CELERY_TIMEZONE = 'America/New_York'` → 모든 crontab은 **ET**. 그러나 chainsight 일부 엔트리 주석이 "UTC"로 표기됨:

| 엔트리 | 주석 표기 | 실제 실행(ET) | 어긋남 |
|--------|----------|--------------|--------|
| `chainsight-heat-score-daily` | "07:00 UTC" | **07:00 ET** (=12:00 UTC 겨울) | 5h |
| `chainsight-seed-selection` | "13:00 UTC" | **13:00 ET** | 5h |
| `chainsight-neo4j-dirty-sync` | "04:30 UTC" | **04:30 ET** | 5h |

ET 내부 순서(heat-score 07:00 → seed-selection 13:00)는 보존되어 의존성 자체는 깨지지 않으나, **주석의 UTC 표기는 사실과 다르다**. 운영자 혼동·재발 방지를 위해 주석 정정 권장.

---

## 2. Rate Limit 초과 구간 분석

### 2-1. FMP (Starter 300 calls/min, 10,000/일)

**관측된 자율 방어**: `sync_sp500_eod_prices`는 `batch_size=100` + 호출당 `time.sleep(1)` → **≈60 calls/min** (한도의 20%). `sync_sp500_financials`도 호출당 1초 슬립. → **단일 태스크 단독으로는 300/min 초과 없음.**

**위험 = 동시간대 중첩**. solo default 큐에서는 직렬화되어 순간 RPM은 오히려 낮아지지만, **누적 일일 한도(10,000/일)**와 **장중 5분 폴링 누적**이 변수다.

| 시각(ET) | 동시 FMP 태스크 | 평가 |
|----------|----------------|------|
| 06:15 | `collect-sp500-news-fmp-0615` (orchestrator, S&P500) | 단독, orchestrator 청크 처리 → OK |
| 18:00 | `sync-sp500-eod-prices`(500종목) + `collect-market-news-evening` + `update-economic-indicators`(FRED) + `thesis-update-readings` | solo 직렬화로 RPM은 안전하나 **벽시계 지연** 발생 (F-3) |
| 장중 :00,:05… | `update-realtime-prices`(SP500) + `update-market-indices` **동일 분 동시 발화** (둘 다 */5, FMP) | 직렬화. 단 `refresh-market-pulse-cache`(매분)와 합쳐 장중 default 워커 포화 |

> **FMP 결론**: 분당 한도(300) 초과 위험은 **낮음**(태스크 내부 슬립 + solo 직렬). 단 `refresh-market-pulse-cache`가 **매분** `MacroEconomicService.get_market_pulse_dashboard()`를 호출(캐시 delete 후 재빌드) → 장중 FMP/FRED 호출이 시간당 최대 60회 추가될 수 있어 **일일 누적 한도 관점**에서 점검 필요(⚠️ 실호출 여부 미검증, 코드상 캐시 재빌드 확인됨).

### 2-2. Gemini Free (15 RPM, 1500 RPD)

**관측된 자율 방어**: `analyze_news_deep`는 docstring상 "4초 간격으로 RPM 준수" → 60/4 = **정확히 15 RPM**. 16:30 충돌(과거 audit P0 #8)은 `extract-daily-news-keywords`를 16:45로 분산하여 **이미 해소**(config L290~297 주석).

**동시간대 LLM 집중 점검** (분 단위 분리 여부):

| 시각(ET) | Gemini 호출 태스크 | 분 분리 | 평가 |
|----------|-------------------|---------|------|
| 08/10/12/14/16/18 **:30** | `analyze-news-deep-batch` (max 50건 → 최대 50콜) | — | 단일 태스크가 4초 슬립으로 ~3.3분 점유 |
| 16:30 vs 16:45 | analyze-deep(:30) ↔ extract-keywords(:45) | ✅ 15분 | 해소됨 |
| 18:30 vs 18:35 | analyze-deep(:30) ↔ thesis-summaries(:35) | ✅ 5분 | analyze-deep 50건이 3.3분 → 18:35 시작 시 **거의 끝나는 경계** ⚠️ 빠듯 |
| 09:00 | `extract-news-relations` (Gemini) | — | 단독 |
| 10:00 | `chainsight-co-mentions` (Gemini) | — | 단독 |
| 05:30 | `enrich-relationship-keywords` (Gemini, neo4j큐) | — | 단독 |
| 08:00 | `keyword-generation-pipeline` (Gemini) | — | classify(:15) 전, 단독 |
| 월1·03:00 | `refresh-korean-overviews-monthly` (S&P500 한글개요 **대량**) | — | 월1회 대량 → **RPD 1500 소진 위험 최대** ⚠️ |

> **Gemini 결론**: 분당(15 RPM) 충돌은 분 단위 분산으로 관리됨. **주의 2건**:
> 1. **18:30 analyze-deep ↔ 18:35 thesis-summaries**: analyze-deep가 50건 풀로드 시 ~3.3분 → 18:35 thesis 시작과 꼬리 겹침 가능. solo default 큐라 직렬화되긴 하나 두 작업 합산 RPM이 15 경계에 근접.
> 2. **월1회 03:00 korean-overviews**가 같은 날 다른 Gemini 작업과 **일일 1500 RPD**를 공유 → 대량 배치일에 RPD 소진 모니터링 필요.

### 2-3. Alpha Vantage (5 calls/min)
Beat 스케줄 70개 중 **AV 의존 태스크 없음**. 거시지표=FRED(`update-economic-indicators`), 시세=FMP. → **AV 5/min 한도는 Beat에 의해 압박받지 않음** (F-8). `.env`에 키는 존재하나 스케줄 미사용.

---

## 3. Queue 몰림 분석

### 3-1. default 큐 (solo=1) — 시간당 고정 배치 작업 수

장중(09–16)은 `refresh-market-pulse-cache`(매분 60) + `update-realtime-prices`/`update-market-indices`(각 */5 =12) + `portfolio-values`(*/10) + `screener-alerts`(*/15)로 **워커가 거의 상시 점유**. 단발 배치가 끼어들 여지가 적다.

**가장 위험한 고정 클러스터 = 18:00~18:45** (장 마감 후, default 큐):
```
18:00  update-economic-indicators (FRED)
18:00  collect-market-news-evening
18:00  sync-sp500-eod-prices        ← 500종목, sleep(1) → ~8분 점유
18:00  thesis-update-readings
18:15  classify-news-batch
18:15  thesis-calculate-scores
18:30  analyze-news-deep-batch (Gemini ~3.3분)
18:30  update-sp500-change-percent
18:30  run-eod-pipeline             ← 무거움 (시그널 벡터 연산)
18:30  thesis-create-snapshots
18:35  thesis-generate-summaries (Gemini)
18:45  sync-news-to-neo4j (neo4j큐)
```
> **solo 직렬화 영향(F-3)**: 18:00의 `sync-sp500-eod-prices`(~8분)가 워커를 잡으면 18:15·18:30 작업이 **줄줄이 밀린다**. 18:30 4개(analyze/change-percent/eod-pipeline/snapshots)가 한 워커에서 순차 실행 → `run-eod-pipeline` 완료가 19:00 `backfill-signal-accuracy` 시작 시각을 침범할 수 있음. **18:00~19:00은 default 큐 직렬 적체 핫스팟.**

### 3-2. neo4j 큐 (solo=1) — `sec-sync-dirty`의 종일 점유 (F-4)

neo4j 큐 라우팅 태스크(`task_routes` + `options.queue`):
```
sec-sync-dirty-neo4j        */5  종일   expires=240s  ← 하루 288회
sync-news-to-neo4j          8~18 :45    expires=3600  (최대 100건 Neo4j 쓰기)
chainsight-sync-profiles    12:00       expires=3600
chainsight-sync-relations   12:30       expires=3600
enrich-relationship-keywords 05:30      (Gemini + neo4j)
cleanup-expired-news-rel    04:00
chainsight-neo4j-dirty-sync 일 04:30
neo4j-health-check          */6h
```
**충돌 핫스팟 = 12:00~12:45**:
```
12:00  sec-sync-dirty (5분틱)
12:00  chainsight-sync-profiles-neo4j
12:30  sec-sync-dirty (5분틱)
12:30  chainsight-sync-relations-neo4j
12:45  sync-news-to-neo4j (100건 → 수 분 소요 가능)
```
> **위험**: solo neo4j 워커가 `sync-news-to-neo4j`(100건)나 chainsight sync로 4분 이상 점유되면, 그 사이 발화한 `sec-sync-dirty`(expires=240s)는 **시작 전 만료되어 조용히 스킵**된다. → SEC dirty evidence → Neo4j 동기화가 12시대에 1~2틱 누락 가능. 누락 자체는 다음 5분틱이 복구하나(idempotent dirty 플래그), **혼잡 시간대에 동기화 지연이 누적**될 수 있음.

---

## 4. 시간대별 히트맵 (ET, 평일 기준)

### 4-A. 고정 시각 배치 작업 수 (상시 백그라운드 `*/5 sec-sync`·`*/30 alerts` 제외)

```
ET  │ 작업수 │ 막대                          │ 비고
────┼────────┼───────────────────────────────┼──────────────────────
00  │   0    │                               │
01  │   1    │ █                             │ econ-calendar
02  │   0    │                               │
03  │   0    │                               │ (주말/월초 배치 집중)
04  │   1    │ █                             │ cleanup-news-rel(neo4j)
05  │   1    │ █                             │ enrich(Gemini/neo4j)
06  │   5    │ █████                         │ FMP뉴스 다발
07  │   6    │ ██████                        │ movers/digest/heat-score
08  │   5    │ █████                         │ keyword-gen(Gemini)+분류시작
09  │   2    │ ██  ▒장중폴링 시작▒           │ sentiment+relations(Gemini)
10  │   5    │ █████  ▒장중▒                 │ co-mentions(Gemini)
11  │   1    │ █  ▒장중▒                     │ relation-confidence
12  │   9    │ █████████  ▒장중▒             │ ★neo4j 12:00/12:30 충돌
13  │   3    │ ███  ▒장중▒                   │ seed-selection
14  │   5    │ █████  ▒장중▒                 │
15  │   2    │ ██  ▒장중▒                    │
16  │   6    │ ██████  ▒장중末▒              │ breadth/heatmap+분류(Gemini)
17  │   4    │ ████                          │ daily-prices(FMP)
18  │  12    │ ████████████                  │ ★★EOD/thesis 최대 클러스터
19  │   2    │ ██                            │ ml-labels+backfill
20  │   1    │ █                             │ sp500-financials(FMP)
21  │   0    │                               │
22  │   1    │ █                             │ econ-indicators
23  │   0    │                               │
────┴────────┴───────────────────────────────┴──────────────────────
피크: 18시(12) ≫ 12시(9) > 07/16시(6) > 06/08/10/14시(5)
```

### 4-B. 외부 API 압력 (상대값, 평일)

```
ET  │ FMP    │ Gemini │ FRED │ Neo4j(solo)
────┼────────┼────────┼──────┼─────────────
06  │ ███    │        │  █   │  ░(sec */5)
07  │ ██     │        │      │  ░
08  │ ██     │  █     │      │  ░
09  │ ███▒폴링│  █    │      │  ░
10  │ ███▒   │  █     │      │  ░
12  │ ██▒    │  █     │  █   │  ██★ (profiles+relations+sec)
14  │ ██▒    │  █     │      │  ░
16  │ ███▒   │  █     │      │  █ (sync-news :45)
17  │ ██     │        │      │  ░
18  │ ████★  │  █     │  █   │  █ (sync-news :45)
20  │ ██     │        │      │  ░
22  │        │        │  █   │  ░
────┴────────┴────────┴──────┴─────────────
░ = sec-sync-dirty */5 상시 배경 부하 (종일)
★ = 동시간대 경합 핫스팟
```
> ▒폴링▒ = 장중(09–16) `refresh-market-pulse-cache`(매분) + `*/5` 시세 폴링이 default 워커를 상시 점유. 막대 외 상수 부하.

---

## 5. 스케줄 겹침 / 의존성 분석

### 5-1. 데이터 경합 위험 (동일 시각 발화)

| 시각 | 동시 발화 | 경합 위험 | 평가 |
|------|----------|----------|------|
| **18:30** | `update-sp500-change-percent` + `run-eod-pipeline` | `run-eod-pipeline`이 `change_percent` 컬럼을 읽으면 **선행 미완료 데이터** 참조 (F-6) | 🟠 solo 직렬이라 enqueue 순서에 따라 갈림. 순서 비결정적 → **15분 간격 분리 권장** |
| 18:00 | `sync-sp500-eod-prices` + `thesis-update-readings` | thesis가 당일 EOD 가격 필요 시 **동기화 전 stale 가격** 참조 | 🟡 thesis가 기저장 DailyPrice 사용하면 무해. 의존 시 18:00 동시는 위험 |
| 12:00 | `chainsight-sync-profiles-neo4j` + `sec-seed-relations-to-chainsight` | 둘 다 chainsight 데이터 갱신 (다른 큐) | 🟢 큐 분리(neo4j vs default)로 물리 경합 적음 |

### 5-2. 의도된 의존 체인 (양호 — 분 단위 staggering)

```
[뉴스 파이프라인]  collect(:00) → classify(:15) → analyze-deep(:30) → sync-neo4j(:45)
                   ✅ 매 2시간 깔끔한 15분 간격

[thesis EOD]       update-readings(18:00) → calculate-scores(18:15)
                   → create-snapshots(18:30) → generate-summaries(18:35)
                   ✅ 순서 보장. 단 18:00이 sync-sp500-eod-prices와 충돌(5-1)

[chainsight 일일]  co-mentions(10:00) → relation-confidence(11:00)
                   → sync-profiles(12:00) → sync-relations(12:30) → seed-selection(13:00)
                   ✅ ET 내부 순서 보존 (단 주석 "UTC" 오표기 F-5)

[chainsight 주간]  all-profiles(토02:00) → price-co-movement(토03:00)
                   → stale-decay(토04:00) → aggregate-profiles(토04:30) → validation(토05:00)
                   ✅ 토요일 새벽 순차 체인, 한산한 시간대 배치 적절

[EOD 대시보드]     sync-sp500-eod-prices(18:00) → run-eod-pipeline(18:30)
                   → backfill-signal-accuracy(19:00)
                   ⚠️ 18:00 EOD sync(~8분) 지연 시 18:30 pipeline이 미완료 가격 참조 가능
```

> **선행 미완료 → 후행 시작 위험 요약**: solo 직렬 워커에서 staggering은 "선행이 슬롯 시간 내 끝난다"는 가정에 의존한다. `sync-sp500-eod-prices`(~8분)·`run-eod-pipeline`·`analyze-news-deep`(~3.3분)이 **18:00~18:45에 한 워커로 몰리면** 가정이 깨져 후행이 선행 산출물을 못 받을 수 있다. 시각 분리만으로는 불충분, **벽시계 지연**이 진짜 위험.

---

## 6. 권고 (읽기 전용 — 실행은 별도 승인 필요)

| 우선 | 권고 | 근거 |
|------|------|------|
| P0 | DB `PeriodicTask` ↔ dict drift diff 정기 점검 | F-2: dict는 무시됨, 실동작은 DB |
| P1 | 18:30 `update-sp500-change-percent`와 `run-eod-pipeline` 시각 분리(예: 18:30 vs 18:45) | F-6: 데이터 경합 |
| P1 | EOD 18:00~18:45 클러스터를 별도 큐 또는 시간 분산 | F-3: solo 직렬 적체 |
| P1 | `sec-sync-dirty-neo4j` `expires=240s` → 5분틱 정체 시 스킵 모니터링/알림 | F-4: 조용한 만료 |
| P2 | chainsight 주석 "UTC" → "ET" 정정 | F-5: 운영자 혼동 |
| P2 | `refresh-market-pulse-cache` 매분 FMP 실호출 여부 확인 → 일일 한도 영향 | 2-1 ⚠️ 미검증 |
| P2 | 월1 `refresh-korean-overviews`일에 Gemini RPD(1500) 소진 모니터링 | 2-2 ⚠️ |

---

## 7. 부록 — 큐별 태스크 분류

**neo4j 큐 (solo=1, 동시 1개)** — `task_routes` + `options.queue='neo4j'`:
`neo4j-health-check`(*/6h), `cleanup-expired-news-relationships`(04:00), `enrich-relationship-keywords`(05:30), `sync-news-to-neo4j`(8~18 :45), `chainsight-sync-profiles-neo4j`(12:00), `chainsight-sync-relations-neo4j`(12:30), `chainsight-neo4j-dirty-sync`(일 04:30), `sec-sync-dirty-neo4j`(*/5 종일)

**default 큐 (macOS solo=1, Linux prefork=4)** — 나머지 전부 (62개)

---

*본 보고서는 `config/celery.py`의 `beat_schedule` 선언(설계 의도)을 분석한 것이며, 실제 실행 스케줄은 `django_celery_beat.PeriodicTask` 테이블이 결정한다(F-2). 코드는 수정하지 않았다.*
