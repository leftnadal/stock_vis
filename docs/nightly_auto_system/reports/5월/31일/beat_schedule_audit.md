# Beat 스케줄 감사 보고서

- **대상**: `config/celery.py` → `app.conf.beat_schedule`
- **감사일**: 2026-05-31
- **모드**: 읽기 전용 (코드 수정 없음)
- **태스크 총수**: 67개 항목 (고빈도 7 + 정시성 배치 60)

---

## 0. 핵심 전제 (분석의 토대)

감사에 결정적 영향을 주는 환경 설정 3가지를 먼저 확정한다.

| 항목 | 값 | 출처 | 영향 |
|------|-----|------|------|
| `CELERY_TIMEZONE` | `America/New_York` | `config/settings.py:489` | **모든 crontab `hour`는 NY 시간** |
| `CELERY_BEAT_SCHEDULER` | `DatabaseScheduler` | `config/settings.py:490` | **config dict는 런타임에 무시됨** (DB `PeriodicTask`가 진실의 소스) |
| 워커 풀 | macOS=`solo` / Linux=`prefork` | `config/celery.py:36-37` | **동시성 모델이 OS별로 정반대** |

### ⚠️ 전제 1 — 이 감사는 "선언적 reference"를 본다
`DatabaseScheduler`가 활성화되어 있으므로 **실제 실행 스케줄은 DB `django_celery_beat.PeriodicTask` 테이블**이다. 본 보고서는 `celery.py`의 dict(설계 의도)를 분석한 것이며, **DB와의 drift 여부는 본 감사 범위 밖**이다 (common-bug #28). 운영 검증은 `celery.py:138`의 권고대로 `set(PeriodicTask.objects.values_list('name', flat=True))` vs dict 키 diff로 별도 수행해야 한다.

### ⚠️ 전제 2 — solo vs prefork가 rate limit/큐 분석을 뒤집는다
- **macOS (solo)**: default 큐의 모든 태스크가 **단일 프로세스에서 직렬 실행**. → 동시 API 호출이 원천 불가하므로 **rate limit 초과는 자연 회피**되지만, 같은 시각에 몰린 태스크는 **순차로 밀린다(처리 지연)**.
- **Linux 운영 (prefork)**: 워커 동시성만큼 **병렬 실행**. → 밀림은 줄지만 **동시 API 호출로 rate limit 초과 위험이 실재**한다.

따라서 아래 rate limit 분석은 **"prefork 운영 환경 기준 최악 시나리오"**로 기술하고, solo 환경의 완화 효과를 병기한다.

---

## 1. 시간대별 API 호출 히트맵 (평일, NY 시간 기준)

배경 고빈도 태스크(매분~5분)와 정시성 배치를 분리해 표기한다.

### 1-A. 배경 고빈도 태스크 (상시 부하)

| 태스크 | 주기 | 활성 시간 | 시간당 트리거 | API |
|--------|------|-----------|---------------|-----|
| `refresh-market-pulse-cache` | 매분 | 9–16시 평일 | 60 | 내부 캐시 |
| `update-realtime-prices` | */5 | 9–16시 평일 | 12 | FMP (≤10심볼) |
| `update-market-indices` | */5 | 9–16시 평일 | 12 | FMP |
| `calculate-portfolio-values` | */10 | 9–16시 평일 | 6 | 내부 |
| `check-screener-alerts` | */15 | 9–16시 평일 | 4 | 내부/FMP |
| `check-pipeline-alerts` | */30 | **24시간 매일** | 2 | 내부 |
| `sec-sync-dirty-neo4j` | */5 | **24시간 매일** | 12 | Neo4j 큐 |

### 1-B. 시간대별 정시 배치 히트맵 (평일 기준, █=배치 1개)

```
시  배치수  분포 (█ = 정시성 배치 태스크)        피크
00 │  0                                          
01 │  1  █                                        (calendar)
02 │  1  █                                        (월/토 한정 +2)
03 │  1  █                                        (일/토/월간 한정 +5)
04 │  1  █                                        ★일요일 한정 +10 = 11
05 │  1  █                                        (enrich Gemini)
06 │  6  ██████                                   ◆ 아침 수집 러시
07 │  6  ██████                                   ◆ 아침 수집 러시
08 │  5  █████ ⟵Gemini                            ◆ 분류/분석 시작
09 │  2  ██     + 고빈도 ON ───────────────┐
10 │  5  █████ ⟵Gemini                     │
11 │  1  █                                  │
12 │  9  █████████ ⟵Gemini ⟵Neo4j몰림       │ ★★ 정오 피크
13 │  3  ███                               │ 시장시간
14 │  5  █████ ⟵Gemini                     │ 고빈도
15 │  2  ██                                │ (시간당 94 추가)
16 │  6  ██████ ⟵Gemini×2                   │ ◆ 마감 처리
17 │  4  ████        ← 고빈도 OFF ──────────┘
18 │  9  █████████ ⟵Gemini ⟵FMP대량         ★★ EOD 피크
19 │  2  ██                                        
22 │  1  █                                        
```

### 1-C. 피크 시간대 식별

| 순위 | 시간대 | 동시 부하 | 성격 |
|------|--------|-----------|------|
| 🥇 | **18시 (평일)** | 배치 9개 + EOD 대량 FMP | EOD 가격/지표/뉴스/thesis 집중 |
| 🥈 | **12시 (평일)** | 배치 9개 + 시장시간 고빈도(94/h) + Neo4j 4개 | 정오 종합 러시 |
| 🥉 | **04시 (일요일)** | 배치 11개 (ML 학습 포함) | 주간 ML/Chain Sight 집중 |
| 4 | **9–16시 (평일)** | 시간당 ~94 트리거(대부분 내부) | 시장시간 상시 부하 |
| 5 | **06–08시 (평일)** | 시간당 5–6 배치 | 아침 뉴스 수집 러시 |

---

## 2. Rate Limit 초과 구간 분석

### 2-1. FMP (Starter: 300 calls/분, 10,000/일)

**🔴 위험 구간 ① — 18:00 평일 (EOD 집중)**

같은 분(18:00)에 트리거되는 FMP 의존 태스크:
- `sync-sp500-eod-prices`: 503종목 순차, `REQUEST_DELAY=0.3s` → **분당 ~200 calls** (`sp500_eod_service.py:24,119`)
- `collect-market-news-evening`: FMP 뉴스
- `thesis-update-readings`: active 가설 지표별 `fetch_indicator_value` (가설 수 비례)
- (`update-economic-indicators`는 FRED API라 FMP 무관)

> **prefork 기준**: EOD 단독 ~200/분 + 뉴스 + thesis가 동시 실행되면 **300/분 한도 근접~초과 가능**. EOD는 `soft_time_limit=1800`(30분)이라 200/분이 지속되지는 않지만 **시작 직후 1–2분이 위험**.
> **solo(macOS) 기준**: 직렬화로 자연 회피. 대신 EOD가 30분 풀로 점유하면 후속 `run-eod-pipeline`(18:30)이 밀림 → §4 의존성 참조.

**🟡 주의 구간 ② — 시장시간 매 :00/:05분 (9–16시)**

`update-realtime-prices`(≤10심볼) + `update-market-indices`가 */5로 동시 트리거. 다만 realtime은 포트폴리오 상위 10종목 한정 + 종목당 1s sleep(`tasks.py:382,409`)이라 **실호출량 작음**. `check-screener-alerts`(*/15)까지 겹쳐도 300/분 대비 여유. → **현 구조에서는 안전**.

**🟡 일일 한도(10,000/일)**: 시장시간 realtime/indices(12+12)/h × 8h + EOD 503 + 뉴스 다회 + 재무 101/일 누적. 정밀 합산은 별도 필요하나 **현재 심볼 제한(realtime 10개) 덕에 한도 내로 추정**. realtime이 전종목으로 확대되면 재검토 필요.

### 2-2. Gemini (Free: 15 RPM, 1,500 RPD)

**같은 분(minute) 동시 트리거는 회피되어 있음** — 설계상 분산 양호:

| Gemini 태스크 | 시각 | minute 충돌 |
|---------------|------|-------------|
| `enrich-relationship-keywords` | 05:30 | 단독 |
| `keyword-generation-pipeline` | 08:00 | 단독 |
| `analyze-news-deep-batch` | 08/10/12/14/16/18시 **:30** | 단독 |
| `extract-daily-news-keywords` | 16:**45** | analyze(16:30)와 15분 분산 (audit P0 #8 기록) |
| `thesis-generate-summaries` | 18:**35** | 단독 |
| `chainsight-co-mentions` 등 | 10/11시 | LLM 사용 시 확인 필요 |

> ✅ **RPM(분당)**: 같은 분에 2개 이상 Gemini 태스크가 겹치는 구간 없음. 16:30/16:45 인접 충돌은 이미 15분 분산으로 해소(주석 명시).

> 🔴 **RPM 내부 위험**: 각 태스크 *내부*는 다건 호출. `analyze-news-deep-batch`는 `max_articles=50` → 한 실행이 기사당 1 LLM 호출이면 **단일 태스크가 자체적으로 15 RPM을 초과**한다. 태스크 내부에 throttle/sleep이 없으면 Free Tier에서 429 폭증. → **태스크 내부 rate 제어 검증 필요** (본 감사 범위 밖, 코드 확인 권고).

> 🔴 **RPD(일일 1,500) 위험**: `analyze-news-deep-batch` 평일 6회 × 최대 50 = **300/일**(이것만으로) + `keyword-generation`, `extract-keywords`, `enrich`(limit=100), `thesis-summaries`, chainsight 계열 누적. **Free Tier 1,500 RPD 초과 가능성이 가장 큰 항목**. 유료 키 사용 여부에 따라 영향 달라지므로 **실제 키 등급 확인 필요**.

### 2-3. Alpha Vantage (5 calls/분)

beat_schedule 내 **AV 직접 의존 태스크 식별 안 됨**. 주가/뉴스/지표는 FMP·FRED·Gemini 중심. AV는 일부 service 레이어에서 fallback으로만 쓰일 가능성 → 스케줄 차원의 AV rate 위험은 **현재 없음**. (service 내부 호출은 코드 확인 권고)

---

## 3. Queue 몰림 분석 (default vs neo4j)

### 3-1. neo4j 큐 — solo pool 단일 동시성 (`--pool=solo`, 동시 1개)

neo4j 큐 라우팅 대상 (`celery.py:43-61`) 중 스케줄된 항목:

| 태스크 | 주기 | expires | 비고 |
|--------|------|---------|------|
| `sec-sync-dirty-neo4j` | ***/5 (24/7)** | **240s** | 가장 빈번 |
| `sync-news-to-neo4j` | 08/10/12/14/16시 :45 평일 | 3600s | max 100건 |
| `chainsight-sync-profiles-neo4j` | 12:00 매일 | 3600s | |
| `chainsight-sync-relations-neo4j` | 12:30 매일 | 3600s | |
| `enrich-relationship-keywords` | 05:30 매일 | 3600s | Gemini 동반 |
| `cleanup-expired-news-relationships` | 04:00 매일 | 3600s | |
| `neo4j-health-check` | */6h | — | |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | 3600s | |

**🔴 위험 ① — `sec-sync-dirty-neo4j`의 expires=240s(4분) vs */5(5분) 경계**
solo 큐에서 한 실행이 **4분을 넘기면 다음 트리거가 만료**되어 누락된다. dirty 적체가 크거나 다른 neo4j 태스크가 선점 중이면 **5분 주기를 못 지킴**. 특히 12:45 트리거 시 12:00/12:30 chainsight sync가 solo 큐를 점유 중이면 sec-sync가 뒤로 밀려 240s 만료 가능.

**🔴 위험 ② — 12:00 / 12:30 / 12:45 neo4j 큐 3연속 몰림**
정오에 `chainsight-sync-profiles`(12:00) → `chainsight-sync-relations`(12:30) → `sync-news-to-neo4j`(12:45) + 그 사이 `sec-sync`(*/5: 12:00,12:05…12:45) 가 **모두 단일 solo 워커로 직렬화**. 각 sync가 무거우면 **정오 neo4j 큐가 수십 분 적체**.

### 3-2. default 큐 — OS별 동시성

- **18시/12시 피크**에 default 배치 9개가 동시 트리거. **prefork면 병렬**(rate limit 위험 ↑), **solo(macOS)면 직렬**(처리 지연 ↑). macOS 개발 환경에서 18:00 EOD(최대 30분) 점유 시 18:00~18:30 default 큐 후속 배치 전부 대기.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 🔴 EOD 가격 → 파이프라인 의존 체인 (18:00–19:00 평일)

```
18:00  sync-sp500-eod-prices  (503종목, 최대 30분, FMP)  ──┐ 데이터 생성
18:30  update-sp500-change-percent (DailyPrice 의존)      ─┤ ← EOD 미완료 시 빈 데이터
18:30  run-eod-pipeline       (EOD 가격 의존)             ─┘ ← 동상
19:00  backfill-signal-accuracy (파이프라인 결과 의존)
```
> **경합 시나리오**: EOD가 30분(`time_limit` 한계)까지 걸리면 18:30 후속 2개가 **선행 완료 전 시작** → 당일 변동률/시그널이 **전일 또는 부분 데이터로 계산**될 수 있다. 시간 간격(30분)이 worst-case(`soft_time_limit=1800`)와 동일해 **안전 마진 0**. solo 환경에선 직렬화로 순서는 보장되나 18:30 후속이 그만큼 지연.

### 4-2. 🟡 Thesis EOD 체인 (18:00–18:35 평일) — 설계 양호

```
18:00 thesis-update-readings (지표 fetch)
18:15 thesis-calculate-scores  (readings 의존, +15분)
18:30 thesis-create-snapshots  (scores 의존, +15분)
18:35 thesis-generate-summaries (snapshot 의존, +5분, Gemini) ← P0 #15 반영
```
> 15분 간격은 readings/scores가 빠르면 충분. 단 `update-readings`가 가설·지표 수에 비례(외부 API 다회)하므로 **가설 수 급증 시 15분 초과 → 연쇄 밀림** 가능. 현재는 마진 적정.

### 4-3. 🟡 뉴스 파이프라인 체인 (평일 매 2시간) — 설계 양호

```
:15 classify-news-batch  → :30 analyze-news-deep  → :45 sync-news-to-neo4j
```
> 분류→분석→동기화 15분 간격 stagger 적절. 단 분석(:30)이 50건 처리에 15분 넘기면 :45 동기화가 미완료분을 놓침(다음 사이클 보정되므로 치명적 아님).

### 4-4. 🔴 Chain Sight 타임존 주석 불일치 (잠재 의도 오류)

| 태스크 | 주석 | 실제 실행 (CELERY_TIMEZONE=NY) | 차이 |
|--------|------|-------------------------------|------|
| `chainsight-heat-score-daily` | "07:00 **UTC**" (`celery.py:747`) | NY 07:00 | **주석과 실제 의도 불일치** |
| `chainsight-seed-selection` | "13:00 **UTC**" (`celery.py:754`) | NY 13:00 | 동상 |
| `chainsight-neo4j-dirty-sync` | "04:30 **UTC**" | NY 04:30 | 동상 |

> 모든 crontab이 NY 시간으로 해석되므로 "UTC" 주석 태스크들은 **의도한 UTC 시각보다 4~5시간(DST) 이르게/늦게 실행**된다. heat-score→seed-selection 순서 의존("시드 선정 전")은 둘 다 같은 오프셋이라 **상대 순서는 유지**되나, 외부 데이터 신선도(UTC 기준 일배치)와 어긋날 수 있음. **문서/의도 검증 필요**.

### 4-5. 🟡 일요일 04시 ML/Chain Sight 집중 (11개 배치)

```
03:00 train-importance-model          (ML, CPU 무거움)
03:30 generate-shadow-report
04:00 cleanup-expired-news-rel / check-auto-deploy / sync-institutional(16일)
      / scan-regulatory(월) / chainsight-stale-decay(토)
04:15 generate-weekly-ml-report
04:20 monitor-ml-performance
04:30 train-lightgbm-model / build-patent-network(1일) / chainsight-aggregate
      / chainsight-neo4j-dirty-sync
```
> 04:00~04:30에 ML 학습 2종 + Chain Sight 집계 + 정리 작업이 밀집. solo/저동시성 워커면 **04시~05시 default 큐 장시간 점유**. 시장 영향 없는 새벽이라 우선순위는 낮으나, train-lightgbm(`expires=7200`)이 지연되면 후속 주간 리포트와 순서 역전 가능.

---

## 5. 종합 위험 등급 요약

| # | 위험 | 등급 | 트리거 조건 | 영향 |
|---|------|------|-------------|------|
| 1 | Gemini RPD 1,500 초과 | 🔴 High | Free Tier + analyze-deep 6회/일 누적 | LLM 분석 전면 429 |
| 2 | Gemini 단일 태스크 내부 RPM 초과 | 🔴 High | analyze-deep 50건 내부 throttle 부재 시 | 태스크 실패 |
| 3 | 18:00 EOD 의존 체인 마진 0 | 🔴 High | EOD 30분 풀 점유 | 당일 변동률/시그널 오류 |
| 4 | neo4j solo 큐 정오 몰림 | 🔴 High | 12:00/12:30/12:45 + sec-sync */5 | sec-sync 240s 만료, 적체 |
| 5 | FMP 18:00 동시 호출(prefork) | 🟡 Med | prefork + EOD+뉴스+thesis 동시 | 300/분 근접 |
| 6 | Chain Sight "UTC" 주석 불일치 | 🟡 Med | 항상 | 의도 대비 4~5h offset |
| 7 | 일요일 04시 ML 집중 | 🟡 Med | 저동시성 워커 | 새벽 큐 장시간 점유 |
| 8 | config dict ↔ DB drift | 🟡 Med | DatabaseScheduler | 본 분석과 실제 실행 불일치 가능 |
| 9 | 시장시간 FMP 고빈도 | 🟢 Low | realtime 10종목 제한 | 현재 안전 |
| 10 | Alpha Vantage 스케줄 의존 | 🟢 Low | 직접 의존 없음 | 위험 없음 |

---

## 6. 권고 사항 (조치 아님 — 검증/확인 항목)

> 본 보고서는 읽기 전용 감사이며 아래는 **후속 검증 권고**일 뿐 코드 변경을 수행하지 않았다.

1. **DB drift 검증** — `PeriodicTask` 키 vs dict 키 diff (common-bug #28). 본 분석 전제의 유효성 확인.
2. **Gemini 키 등급 확인** — Free(1,500 RPD)인지 유료인지. Free면 위험 #1·#2가 실재.
3. **analyze-news-deep 내부 throttle 확인** — 50건 처리 시 호출 간 sleep 유무.
4. **EOD 18:00↔18:30 간격 재검토** — `soft_time_limit=1800`과 동일하여 마진 0. 의존 체인 안전화 필요.
5. **neo4j 큐 정오 stagger** — 12:00/12:30/12:45 + sec-sync(240s expires) 경합 측정.
6. **Chain Sight "UTC" 주석 정정** — 실제 NY 실행과 의도 일치 여부 확인.
7. **운영 OS 동시성 명시** — prefork(rate limit 위험) vs solo(밀림 위험) 중 운영 기준 확정.

---

*감사 방법: `config/celery.py` 전수 정독 + `settings.py` 타임존/스케줄러 + `stocks/tasks.py`·`sp500_eod_service.py`·`thesis/tasks/eod_pipeline.py` 호출 패턴 확인. 코드 미변경.*
