# Beat Schedule 감사 보고서

- **대상**: `config/celery.py` `app.conf.beat_schedule` (선언적 reference dict)
- **작성일**: 2026-06-16
- **모드**: 읽기 전용 (코드 수정 없음)
- **태스크 총수**: 67개 항목 (`schedule` 키 기준)

---

## 0. 분석 전제 (Critical Context)

감사 결과를 읽기 전에 반드시 알아야 할 두 가지 전제.

### 0-1. 이 dict는 런타임에 무시된다 (config ↔ DB drift)

`config/settings.py:`
```python
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

→ **실제 스케줄의 진실의 소스는 DB `django_celery_beat.PeriodicTask` 테이블이다.** `config/celery.py`의 `beat_schedule` dict는 "원래 설계된 스케줄의 선언적 reference"일 뿐, Beat가 실행 시 참조하지 않는다 (common-bugs #28).

> **본 감사는 dict(설계 의도)를 분석한다.** dict와 DB가 어긋나 있으면(drift) 실제 실행 스케줄은 본 보고서와 다를 수 있다. 정확한 운영 부하를 보려면 DB 측 검증이 추가로 필요하다:
> ```python
> # python manage.py shell
> set(PeriodicTask.objects.values_list('name', flat=True)) ^ set(config_dict_keys)
> ```

### 0-2. 모든 crontab 시각은 `America/New_York` (ET) 기준

`config/settings.py:496`:
```python
CELERY_TIMEZONE = 'America/New_York'  # NYSE 시간대
```

→ `crontab(hour=7)` = **07:00 ET**, UTC 아님. 본 보고서의 모든 시각 표기는 ET다.

> 🟡 **문서 drift 발견**: 아래 3개 태스크의 주석은 "UTC"라고 표기하지만 실제로는 ET로 실행된다. 의도와 동작이 어긋날 소지가 있어 정정 필요.
> | 태스크 | 주석 표기 | 실제 실행 (ET) | 실제 UTC 환산 |
> |--------|----------|---------------|--------------|
> | `chainsight-heat-score-daily` | "07:00 UTC" | 07:00 ET | 11:00(EST)/11:00(EDT) UTC |
> | `chainsight-seed-selection` | "13:00 UTC" | 13:00 ET | 17:00 UTC |
> | `chainsight-neo4j-dirty-sync` | "04:30 UTC" (일) | 04:30 ET (일) | 08:30 UTC |
>
> 다행히 의존 순서(heat-score 07:00 → seed-selection 13:00, relations-sync 12:30 → seed 13:00)는 ET 기준으로도 성립하므로 **기능 영향은 없으나** 주석을 ET로 정정 권장.

### 0-3. 실측 검증한 호출량 정정 (이름만으로 오판하기 쉬운 항목)

코드를 직접 확인한 결과, 태스크 이름에서 추정되는 부하와 실제가 다른 항목:

| 태스크 | 이름상 추정 | **실측** |
|--------|-----------|---------|
| `update-realtime-prices` / `update-daily-prices` | S&P 500 전체(~500) FMP 호출 | `update_realtime_with_provider(symbols=None)` → **포트폴리오 종목 `[:10]`개만**, `time.sleep(1)` throttle. FMP 한도 무관 |
| `classify-news-batch` | LLM 분류 | **룰 엔진(`NewsClassifier`)** — Gemini 미사용 (`tasks.py:525-528`) |
| `chainsight-co-mentions` / `chainsight-relation-confidence` | LLM 관계 추출 | 텍스트 동시출현/계산 기반 — Gemini 미사용 |
| 뉴스 수집 (Finnhub 경유) | 무제한 | `time.sleep(2)` 로 Finnhub 60/min 준수 (`tasks.py:148,431`) |

---

## 1. 시간대별 태스크 실행 히트맵 (ET, 평일 기준)

배치(cron 고정시각) 태스크의 시간대별 발화 수. **매분/수분 단위 폴러는 §1-2에서 별도 집계** (히트맵을 왜곡하므로 분리).

```
시(ET) │ 발화수 │ 막대 (■ = 1 task)                          │ 비고
───────┼────────┼────────────────────────────────────────────┼──────────────────
 00    │   1    │ ■                                          │ neo4j health
 01    │   1    │ ■                                          │ econ calendar
 02    │   0    │                                            │ (월/주간 전용)
 03    │   0    │                                            │ (월/주간 전용)
 04    │   1    │ ■                                          │ news rel cleanup
 05    │   1    │ ■                                          │ enrich-kw(Gemini)
 06    │   6    │ ■■■■■■                                      │ 뉴스수집+FRED+health
 07    │   6    │ ■■■■■■                                      │ movers+digest+news
 08    │   5    │ ■■■■■                                       │ Gemini파이프 시작
 09    │   2    │ ■■                          ◀ 장 개장        │ sentiment+relations
 10    │   5    │ ■■■■■                                       │ news v3 + fmp news
 11    │   1    │ ■                                          │ relation-confidence
 12    │  10    │ ■■■■■■■■■■  ◀◀ 2nd PEAK                     │ 정오 대집중 (아래)
 13    │   3    │ ■■■                                         │ seed-selection 등
 14    │   5    │ ■■■■■                                       │ news v3 + fmp news
 15    │   2    │ ■■                                          │ market news + fmp
 16    │   6    │ ■■■■■■                       ◀ 장 마감        │ breadth/heatmap+v3
 17    │   4    │ ■■■■                                        │ daily price + news
 18    │  13    │ ■■■■■■■■■■■■■  ◀◀◀ PEAK                     │ EOD 대집중 (아래)
 19    │   2    │ ■■                                          │ ml labels + accuracy
 20    │   1    │ ■                                          │ sp500 financials
 21    │   0    │                                            │
 22    │   1    │ ■                                          │ FRED econ
 23    │   0    │                                            │
```

**피크 시간대**: 🔴 **18:00 ET (13개)** ≫ 🟠 12:00 ET (10개) > 06/07/16 ET (6개)

### 1-1. 피크 시간대 상세

**🔴 18:00–18:45 ET — 일일 최대 부하 (매 평일 13태스크)**
```
18:00  sync-sp500-eod-prices        (FMP, S&P500 EOD)   ┐
18:00  update-economic-indicators   (FRED)              │
18:00  collect-market-news-evening  (provider)          │ 18:00 동시 5개
18:00  thesis-update-readings       (DB 지표 수집)        │
18:00  neo4j-health-check           (neo4j queue)       ┘
18:15  thesis-calculate-scores      (스코어 계산)
18:15  classify-news-batch          (룰 엔진)
18:30  run-eod-pipeline             (14 시그널 파이프라인) ┐
18:30  update-sp500-change-percent  (DB 일괄, API無)     │ 18:30 동시 4개
18:30  thesis-create-snapshots      (스냅샷+알림)         │  ⚠ 의존 경합 (§4)
18:30  analyze-news-deep-batch      (Gemini, 50건)       ┘
18:35  thesis-generate-summaries    (Gemini 요약)        ⚠ 18:30 analyze와 5분 간격
18:45  sync-news-to-neo4j           (neo4j queue, 100건)
```

**🟠 12:00–12:45 ET — 정오 집중 (매 평일 10태스크, neo4j queue 과밀)**
```
12:00  update-economic-indicators        (FRED)
12:00  collect-market-news-noon          (provider)
12:00  sec-seed-relations-to-chainsight  (DB 연결)
12:00  chainsight-sync-profiles-neo4j    (neo4j queue) ┐
12:00  neo4j-health-check                (neo4j queue) │ ⚠ neo4j solo 경합
12:00  sec-sync-dirty-neo4j (*/5 발화)    (neo4j queue) ┘   (§3)
12:15  classify-news-batch               (룰 엔진)
12:30  analyze-news-deep-batch           (Gemini, 50건)
12:30  collect-general-news-fmp-noon     (FMP)
12:30  chainsight-sync-relations-neo4j   (neo4j queue) ⚠
12:45  sync-news-to-neo4j                (neo4j queue) ⚠
```

### 1-2. 연속/수분 단위 폴러 (히트맵 별도)

| 태스크 | 주기 | 활성 구간 (ET) | 시간당 발화 | API/부하 |
|--------|------|---------------|-----------|---------|
| `refresh-market-pulse-cache` | `*/1` | 09–16 평일 | 60 | 캐시 갱신 (API無, DB read) |
| `sec-sync-dirty-neo4j` | `*/5` | **24/7** | 12 | **neo4j queue** (§3 핵심) |
| `update-realtime-prices` | `*/5` | 09–16 평일 | 12 | FMP (포트폴리오 10종목) |
| `update-market-indices` | `*/5` | 09–16 평일 | 12 | FMP (지수 소수) |
| `calculate-portfolio-values` | `*/10` | 09–16 평일 | 6 | DB read |
| `check-screener-alerts` | `*/15` | 09–16 평일 | 4 | DB read |
| `check-pipeline-alerts` | `*/30` | 24/7 | 2 | DB read |

> 장중(09–16 ET) 연속 폴러 합계 ≈ **시간당 ~106 발화**. 대부분 캐시/DB이고, FMP는 `*/5` 2종(realtime 10종목 + indices)뿐이라 한도 영향 미미.

### 1-3. 주간/월간 배치 (특정 요일·날짜에만 가산)

히트맵의 평일 일일 부하에 **추가로** 얹히는 배치. 토요일 새벽 02–05 ET와 매월 1일이 별도 피크다.

```
[토요일 새벽] chainsight-all-profiles(02:00) → price-co-movement(03:00)
             → stale-decay(04:00) → aggregate-profiles(04:30)
             → validation-weekly-batch(05:00) + aggregate-weekly-prices(01:00)
[일요일 새벽] train-importance-model(03:00) → shadow-report(03:30)
             → check-auto-deploy(04:00) → weekly-ml-report(04:15)
             → monitor-ml(04:20) → train-lightgbm(04:30)
             + cleanup-old-macro(03:00) + chainsight-neo4j-dirty-sync(04:30, neo4j)
             + cleanup-task-results(05:00)
[월 1일]     sync-sp500-constituents(02:00) + archive-old-articles(02:30, 1일)
             + refresh-korean-overviews-monthly(03:00, 🔴 Gemini 대량)
             + build-patent-network(04:30) + sec-check-new-filings(06:00)
[월 15/16일] sync-supply-chain-batch(15일 03:00) + sync-institutional-holdings(16일 04:00)
[월요일]     sync-etf-holdings(06:00) + scan-regulatory-relationships(04:00)
```

---

## 2. Rate Limit 초과 구간 분석

### 2-1. Gemini Free (15 RPM / 1500 RPD)

**Gemini 사용 태스크 (실측 확인) — ET:**

| 시각 | 태스크 | 1회 처리량 | 비고 |
|------|--------|----------|------|
| 05:30 | `enrich-relationship-keywords` | limit 100 | neo4j queue |
| 08:00 | `keyword-generation-pipeline` | gainers (~수십) | |
| 08:30/10:30/12:30/14:30/16:30/18:30 | `analyze-news-deep-batch` ×6 | max 50건/회 | |
| 09:00 | `extract-news-relations` | 24h 윈도우 | |
| 16:45 | `extract-daily-news-keywords` | 당일 뉴스 | |
| 18:35 | `thesis-generate-summaries` | 활성 가설 수 | |

**🟢 RPM (분당) — 동시각 충돌 없음 (양호한 설계)**
- Gemini 태스크가 **동일 hh:mm에 겹치지 않도록 stagger** 되어 있음. 가장 근접: 18:30 `analyze-deep` ↔ 18:35 `thesis-summaries` (5분 간격), 16:30 `analyze-deep` ↔ 16:45 `keyword-extract` (15분 — 주석 P0#8에서 의도적 분산).
- **실질 RPM 위험은 태스크 *내부*에 있다**: `analyze-news-deep-batch`가 50건을 한 번에 처리할 때 15 RPM(분당 15콜)을 지키려면 최소 ~3.3분 self-throttle 필요. → 내부 throttle/`time.sleep` 구현 여부 확인 권장 (미구현 시 RESOURCE_EXHAUSTED 발생).

**🟡 RPD (일당) — 평일 정상은 여유, 월 1일은 위험**
- 평일 추정 합계: analyze 6×50=300 + enrich 100 + keyword-gen/extract/relations/summaries ≈ **500–700/일** → 1500 RPD 내 여유.
- 🔴 **월 1일 스파이크**: `refresh-korean-overviews-monthly`(03:00, bulk_generate_korean_overviews)가 S&P500(~503) 한글 개요를 LLM 생성 → 단일 윈도우에서 **+최대 ~500콜**. 당일 일반 부하와 합산 시 **1200–1500 RPD 근접/초과** 가능. → 월 1일 한정 일배치 분산 또는 RPD 모니터링 권장.

### 2-2. FMP (Starter: 300 calls/min, 10,000/일)

**FMP 사용 태스크 — ET:**

| 시각 | 태스크 | 호출 규모 | 위험도 |
|------|--------|----------|-------|
| 09–16 `*/5` | update-realtime-prices | 포트폴리오 10종목 | 🟢 무시 |
| 09–16 `*/5` | update-market-indices | 지수 소수 | 🟢 무시 |
| 06:15/10:15/13:15/15:15/17:15 | `collect-sp500-news-fmp-orchestrator` ×5 | **S&P500 fan-out** | 🟡 검증 필요 |
| 06:45/12:30/17:45 | collect-general-news-fmp ×3 | 일반 뉴스 | 🟢 |
| 07:45 | collect-press-releases-fmp | max_symbols 50 | 🟢 |
| 17:00 | update-daily-prices | 포트폴리오 10종목 | 🟢 |
| 18:00 | `sync-sp500-eod-prices` | **S&P500 EOD** | 🟡 검증 필요 |
| 20:00 | `sync-sp500-financials` | **101종목/일** (5일 1회전) | 🟢 명시적 관리 |

**🟡 검증 필요 2건**:
- `collect-sp500-news-fmp-orchestrator`: "orchestrator" 명칭상 종목별 fan-out 추정. 503종목을 단일 분에 직렬 호출하면 300/min 초과. → 내부 chunk/sub-task/`countdown` 분산 여부 확인 필요. (다른 news 수집은 `time.sleep(2)` throttle 확인됨.)
- `sync-sp500-eod-prices` (18:00): EOD 일괄. FMP `/stable` batch EOD 엔드포인트(콤마 구분 1콜) 사용 시 안전, 종목별 호출 시 300/min 초과. → 구현 확인 필요.
- 🟢 `sync-sp500-financials`는 `batch_size=101`로 5일에 503종목 1회전 — **모범 사례** (의도적 rate 분산, `tasks.py:138-201`).

**일일 한도(10,000/일)**: 위 합산은 수천 수준으로 추정, 여유 있음 (orchestrator가 종목별이라도 5회×503=2,515).

### 2-3. Alpha Vantage (5 calls/min — 12초 대기)

- AV는 `services/news/providers/alphavantage.py`(뉴스 멀티프로바이더)에만 존재. **Beat 스케줄에 AV 전용 태스크는 없다.**
- 🟡 **조건부 위험**: 뉴스 수집 태스크(`collect_daily_news`/`collect_market_news`/`collect_category_news`)가 멀티프로바이더에서 **AV 프로바이더를 활성화**한 경우, 06:00/08:00/12:00 등 뉴스 버스트 시 AV가 5/min(12초/콜)에서 직렬 병목이 된다.
- **현 코드 확인 범위에서 AV 활성 여부 미확정** → 프로바이더 enable/priority 설정 확인 권장. 비활성(FMP/Finnhub 우선)이면 무관.

---

## 3. Queue 몰림 분석 (default vs neo4j)

### 3-1. neo4j queue — solo pool(동시 1개) 제약이 핵심 병목

`config/celery.py:37` → macOS에서 `worker_pool = 'solo'` 강제 (SIGSEGV 방지, bug #25). **neo4j queue 워커는 한 번에 1개 태스크만** 처리.

**neo4j queue 라우팅 태스크 (task_routes + options.queue):**

| 태스크 | 스케줄 (ET) | 비고 |
|--------|-----------|------|
| `sec-sync-dirty-neo4j` | **`*/5` 24/7** | 🔴 5분마다, 상시 점유 시도 |
| `neo4j-health-check` | `*/6h` (00/06/12/18) | |
| `sync-news-to-neo4j` | 08/10/12/14/16/18 :45 | 100건 |
| `cleanup-expired-news-relationships` | 04:00 | |
| `enrich-relationship-keywords` | 05:30 | 🔴 **Gemini(100건)인데 neo4j queue** |
| `chainsight-sync-profiles-neo4j` | 12:00 | |
| `chainsight-sync-relations-neo4j` | 12:30 | |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | |

**🔴 발견 1 — `sec-sync-dirty-neo4j` 상시 점유 + 다른 neo4j 태스크 블로킹**
- `*/5` 24/7로 발화 → solo 워커를 5분마다 점유. 다른 neo4j 태스크가 5분 이상 걸리면 sec-sync가 큐에 밀려 백로그.
- expires=240초(4분) 설정 → 큐에서 4분 넘게 대기하면 **만료되어 스킵**. 즉 긴 neo4j 작업이 돌면 sec dirty sync가 조용히 누락될 수 있음.

**🔴 발견 2 — 12:00 정오 neo4j 3중 충돌**
- 12:00 `neo4j-health-check` + 12:00 `chainsight-sync-profiles-neo4j` + 12:00 `sec-sync-dirty-neo4j`(*/5 발화) → solo 워커에 **3개 동시 큐잉, 직렬 처리**.
- 이어 12:30 `chainsight-sync-relations-neo4j` + sec-sync, 12:45 `sync-news-to-neo4j` + sec-sync. → 12:00–12:45 neo4j queue가 가장 혼잡.

**🟠 발견 3 — `enrich-relationship-keywords`(05:30)가 neo4j queue에서 Gemini 호출**
- Gemini 100건 LLM 작업이 neo4j solo 워커를 장시간 점유 (15 RPM이면 100건 ≈ 7분+). 그동안 05:30/05:35 `sec-sync-dirty-neo4j`가 블로킹·만료될 수 있음.
- 🟡 **설계 의문**: LLM enrichment를 왜 neo4j queue에 두는가? Neo4j 쓰기 때문이라면 분리(LLM은 default, 결과 쓰기만 neo4j) 검토.

### 3-2. default queue

- 위 §1 피크(18:00 13개, 12:00 정오)가 default 워커 부하. default 워커가 단일/소수면 18:00에 `run-eod-pipeline`(무거움) + `analyze-news-deep`(Gemini) + thesis 3종이 직렬 경합.
- 🟡 **워커 동시성(concurrency) 설정 미확인** — macOS solo면 default도 동시 1개 → 18:00 13태스크가 직렬화되어 처리 지연 누적 가능. 18:35 `thesis-generate-summaries`가 18:30 무거운 작업들 뒤에 밀리면 실제 실행이 19시대로 지연될 위험.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 🔴 동일 분(minute) 의존 경합 — EOD 18:30

```
18:30  sync-sp500-eod-prices 결과 의존 체인:
       (18:00 EOD price) → update-sp500-change-percent (18:30) ┐ 둘 다 18:30
                         → run-eod-pipeline           (18:30) ┘ ⚠ 순서 미보장
```
- `run-eod-pipeline`(14 시그널)이 `update-sp500-change-percent`(DailyPrice→change_percent 일괄) 결과를 읽는다면, **둘이 동일 18:30 발화 → 실행 순서 미보장**. solo 워커면 등록 순서대로 직렬화되나 dict 순서상 change-percent(569행)가 eod-pipeline(633행)보다 뒤 → eod-pipeline이 먼저 돌면 change_percent 미반영 데이터로 시그널 계산 위험.
- 🟡 **권장**: change-percent를 18:25로 당기거나 eod-pipeline을 18:35+로 미뤄 명시적 순서 확보. (단 현재 dict 순서/DB 등록 순서에 따라 우연히 맞을 수 있으니 DB 실등록 순서 확인 필요.)

### 4-2. 🟢 잘 설계된 의존 체인 (15분 간격 stagger)

```
thesis EOD:   update-readings(18:00) → calculate-scores(18:15)
              → create-snapshots(18:30) → generate-summaries(18:35)   ✅
news v3:      classify(:15) → analyze-deep(:30) → sync-neo4j(:45)      ✅ 매 2h
ML 주간(일):   train-importance(03:00) → shadow-report(03:30)
              → auto-deploy(04:00) → weekly-report(04:15)
              → monitor(04:20) → lightgbm(04:30)                       ✅
chainsight(토): all-profiles(02:00) → price-co-movement(03:00)
              → stale-decay(04:00) → aggregate(04:30)                  ✅
```
→ 각 단계 15분+ 간격. **선행 태스크가 15분 내 완료된다는 가정**에 의존. 18:00 EOD 가격 동기화나 thesis-update-readings가 15분 초과 시 후속 단계가 stale 데이터로 실행될 수 있음 (가정 위반 시 silent 오류).

### 4-3. 🟡 데이터 경합 가능 지점

| 지점 | 경합 내용 |
|------|----------|
| 18:00 ×5 동시 | sync-sp500-eod-prices(가격 쓰기) ↔ thesis-update-readings(지표 읽기) — readings가 당일 가격 의존 시 race |
| 12:00 ×3 neo4j | profiles-sync ↔ health-check ↔ sec-dirty — 같은 Neo4j 인스턴스 동시 쓰기/읽기 (solo라 직렬화되어 실제 충돌은 회피) |
| 09:00 | aggregate-daily-sentiment ↔ extract-news-relations — 둘 다 당일 뉴스 읽기 (읽기라 안전) |

### 4-4. 🟡 의존 순서 깨짐 의심 — chainsight seed

- `chainsight-seed-selection`(13:00 ET) 주석: "관계 동기화 후". 선행 `chainsight-sync-relations-neo4j`(12:30 ET) → 30분 간격 OK.
- `chainsight-co-mentions`(10:00) → `chainsight-relation-confidence`(11:00, "CoMention 후") → seed(13:00). 체인 성립 ✅.
- 단 §0-2의 UTC 오표기 때문에 *문서만 읽으면* 순서가 깨진 것처럼 보임 (heat-score "07:00 UTC" vs seed "13:00 UTC"). 실제 ET 기준으론 정상.

---

## 5. 우선순위별 권장 조치 (읽기 전용 — 실행 안 함)

| 우선 | 항목 | 조치 |
|------|------|------|
| 🔴 P0 | config dict ↔ DB PeriodicTask **drift 검증** | `manage.py shell`에서 키 diff (§0-1). 본 감사 전제의 정확성이 여기 달림 |
| 🔴 P0 | 18:30 `change-percent` ↔ `run-eod-pipeline` 순서 | DB 등록 순서 확인 후 명시적 분리 (§4-1) |
| 🟠 P1 | `analyze-news-deep` 내부 Gemini RPM throttle | 50건/회가 15 RPM 준수하는지 코드 확인 (§2-1) |
| 🟠 P1 | neo4j queue 12:00 3중 충돌 + sec-dirty 만료 | sec-sync expires=240 vs 정오 백로그 (§3-1) |
| 🟠 P1 | `enrich-relationship-keywords` neo4j queue 점유 | LLM/Neo4j 쓰기 분리 검토 (§3-1 발견3) |
| 🟡 P2 | 월 1일 `refresh-korean-overviews` Gemini RPD 스파이크 | 일배치 분산 또는 모니터링 (§2-1) |
| 🟡 P2 | `collect-sp500-news-fmp-orchestrator` FMP fan-out | chunk/throttle 구현 확인 (§2-2) |
| 🟡 P2 | `sync-sp500-eod-prices` FMP batch 여부 | batch EOD 엔드포인트 사용 확인 (§2-2) |
| 🟡 P2 | AV 프로바이더 활성 여부 | 뉴스 멀티프로바이더 설정 확인 (§2-3) |
| 🟢 P3 | chainsight 3종 "UTC" 주석 → "ET" 정정 | 문서 drift (§0-2) |
| 🟢 P3 | default 워커 concurrency 확인 | 18:00 13태스크 직렬화 지연 (§3-2) |

---

## 부록 A. 감사 방법론 / 한계

- **분석 대상**: `config/celery.py:141-820` `beat_schedule` dict (선언적 reference).
- **실측 교차검증**: `update_realtime_with_provider`(포트폴리오 10종목 cap), `classify_news_batch`(룰 엔진), `sync_sp500_financials`(101 batch), Gemini/FMP/AV 사용처 grep.
- **확인 못 한 부분 (추가 검증 필요)**:
  1. DB `PeriodicTask` 실제 등록 상태 (drift) — 본 감사는 dict 기준.
  2. default/neo4j 워커 concurrency 실제 설정값.
  3. `analyze-news-deep`, `collect-sp500-news-fmp-orchestrator`, `sync-sp500-eod-prices` 내부 호출 패턴(throttle/batch).
  4. AV 프로바이더 enable/priority.
- **시각 기준**: 전부 `America/New_York` (ET), DST 자동 적용.
