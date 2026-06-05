# Beat Schedule 감사 보고서

- **대상 파일**: `config/celery.py` (`app.conf.beat_schedule`, 라인 141~820)
- **감사일**: 2026-06-05
- **감사 범위**: 읽기 전용 정적 분석 (코드 변경 없음)
- **태스크 총수**: 75개 beat 엔트리 (point/interval 포함)

---

## 0. 가장 먼저 — 2가지 구조적 전제 (이 보고서 해석에 필수)

### ⚠️ 전제 1 — 이 dict는 런타임에 **실행되지 않는다**

`config/settings.py`:
```
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

때문에 Beat의 **진실의 소스는 DB `django_celery_beat.PeriodicTask` 테이블**이다.
`config/celery.py`의 `beat_schedule` dict는 celery.py 라인 124~140 주석이 명시하듯
**"원래 설계된 스케줄의 선언적 reference"** 일 뿐이다.

> **따라서 이 감사는 "설계 의도(reference)"에 대한 분석이다.**
> 실제 운영 스케줄과 drift가 있을 수 있다. 운영 부하의 정확한 판단을 위해서는
> 아래 명령으로 DB 실측을 **반드시 교차검증**해야 한다 (이번 감사 범위 밖 — 읽기전용):
> ```bash
> python manage.py shell -c "from django_celery_beat.models import PeriodicTask; \
> import json; print(json.dumps({p.name: {'task':p.task,'cron':str(p.crontab),'enabled':p.enabled} \
> for p in PeriodicTask.objects.all()}, ensure_ascii=False, indent=2))"
> # 그 후 위 결과의 키 집합 vs config dict 키 집합 diff
> ```

### ⚠️ 전제 2 — 모든 시각은 **America/New_York (NY)** 기준이다

`config/settings.py:489 → CELERY_TIMEZONE = 'America/New_York'`

- 대부분 주석은 "EST/ET"로 표기 → NY 벽시계와 일치 (DST는 자동 처리, 정상).
- **그러나 일부 주석이 "UTC"로 오기되어 있다 (아래 F-7 발견 참조).**
- 본 보고서의 히트맵/시각은 모두 NY 기준. (KST = NY + 13h(EST)/+14h(EDT 오기))

---

## 1. Rate Limit 초과 구간 분석

### 1-A. FMP (Starter: 300 calls/min, 10,000/day)

FMP를 **직접 호출**하는 beat 태스크:

| 태스크 | NY 시각 | 호출 규모(추정) | 비고 |
|--------|---------|----------------|------|
| `update-realtime-prices` | `*/5` 09–16 평일 | 추적 심볼 수만큼 | 분당 반복 |
| `update-market-indices` | `*/5` 09–16 평일 | 지수 소수 | realtime과 **동일 분(:00,:05…)에 동시 발사** |
| `collect-sp500-news-fmp-*` | 06:15·10:15·13:15·15:15·17:15 평일 | S&P500 ≈500심볼 | batch `rate_limit='100/m'` + CircuitBreaker 내장 |
| `collect-general-news-fmp-*` | 06:45·12:30·17:45 평일 | 50건 | CircuitBreaker |
| `collect-press-releases-fmp` | 07:45 평일 | 50심볼 | CircuitBreaker |
| `sync-daily-market-movers` | 07:30 평일 | gainers/losers | |
| `update-daily-prices` | 17:00 평일 | 추적 심볼 | |
| `sync-sp500-eod-prices` | **18:00 평일** | **≈500심볼** | 18시 폭주 구간 |
| `sync-sp500-financials` | 20:00 평일 | 101심볼/일(5일 1회전) | |
| `sync-sp500-constituents` | 매월1일 02:00 | 1회 | |

**판정**:
- 🟡 **장중 `*/5` 동시 발사 (P1)**: `update-realtime-prices` + `update-market-indices`가
  매 5분 같은 분에 발사. `update-realtime-prices`의 **심볼 수가 미확인**(코드 추가 검증 필요).
  추적 심볼이 수백 개라면 단일 분(minute) 윈도우에서 300/min 근접 가능.
  → **실측 필요**: `update_realtime_with_provider`가 1회 호출당 소비하는 FMP call 수.
- 🟢 **S&P500 뉴스 orchestrator**: chord batch가 `rate_limit='100/m'`로 Celery 레벨에서
  자체 제어 + CircuitBreaker("fmp") 적용 → 300/min 한도 내 안전. (단 ~5분 이상 장시간 실행)
- 🟠 **18:00 EOD 동시 발사 (P1)**: `sync-sp500-eod-prices`(≈500 call)가 18:00에 시작.
  500 call ÷ 300/min ≈ **최소 100초 소요**. 같은 18:00에 `thesis-update-readings`(지표 수집,
  일부 FMP 의존 가능)가 동시 시작 → 합산 시 18:00~18:02 윈도우 한도 압박.
- 🟢 **일일 총량**: 10,000/day 한도 대비 합산 추정치(financials 101 + eod 500 + 뉴스 5회×~500 +
  realtime 장중 누적)는 realtime 심볼 수에 좌우. realtime이 대량이면 **일일 한도도 재검토 필요**.

### 1-B. Gemini (Free: 15 RPM, 1,500 RPD)

Gemini를 호출하는 beat 태스크:

| 태스크 | NY 시각 | 호출 규모(추정) | RPD 기여 |
|--------|---------|----------------|----------|
| `enrich-relationship-keywords` | 05:30 (daily, neo4j큐) | limit=100 관계 | ~100 |
| `keyword-generation-pipeline` | 08:00 (daily) | gainers 키워드 | 가변 |
| `analyze-news-deep` | 08:30·10:30·12:30·14:30·16:30·18:30 평일 | max 50건/회 ×6 | **≤300** |
| `extract-news-relations` | 09:00 (daily) | 최근24h 뉴스 | 가변(LLM 추정) |
| `extract-daily-news-keywords` | 16:45 (daily) | 당일 뉴스 키워드 | 가변(대량 가능) |
| `thesis-generate-summaries` | 18:35 평일 | 가설 수만큼 | 가변 |
| `refresh-korean-overviews-monthly` | **매월1일 03:00** | **≈500기업** | **≤500 (월1)** |

**판정**:
- 🟢 **16:30 vs 16:45 충돌 회피 (해결됨)**: 라인 290~292 주석대로
  `extract-daily-news-keywords`를 16:30→16:45로 이동하여 `analyze-news-deep`(16:30)과
  15분 분리 → Gemini 15 RPM 2배 초과 위험 이미 차단. (과거 audit P0 #8 반영)
- 🟡 **18:30~18:35 근접 (P2)**: `analyze-news-deep`(18:30, ≤50건) 종료 전
  `thesis-generate-summaries`(18:35) 시작 가능. analyze가 5분 내 미완료 시 15 RPM 동시 압박.
  단 둘 다 동기 순차 호출이라 폭주보단 **지연 누적** 성격.
- 🔴 **매월 1일 RPD 폭발 위험 (P1)**: `refresh-korean-overviews-monthly`(03:00, ≈500 call)가
  매월 1일에만 발사. 같은 1일에는 다른 월간 태스크들도 몰림.
  500(overviews) + 평상 일일 Gemini(analyze 300 + enrich 100 + keywords/relations/summaries 가변)
  → **1,500 RPD 한도 초과 가능**. 월초 1일 Gemini 일일 한도 모니터링 필수.
- 🟡 **15 RPM 페이싱**: `analyze-news-deep` 50건, `enrich`(100건), `overviews`(500건)는
  각각 15 RPM 한도상 최소 4·7·34분 페이싱 필요 → 내부 sleep/배치 페이싱 구현 여부 확인 권장.

### 1-C. Alpha Vantage (5 calls/min)

**판정**: 🟢 **beat 스케줄에 AV 직접 의존 태스크 없음.**
- `update-realtime-prices`/`update-daily-prices`는 `update_realtime_with_provider`(FMP Provider) 사용.
- AV는 ad-hoc/수동 동기화 경로에서만 사용되는 것으로 보임 → beat rate limit 무관.
- (참고: AV 의존 태스크가 DB `PeriodicTask`에 별도 등록돼 있지 않은지 전제1 교차검증 시 같이 확인)

### 1-D. 기타 외부 API (한도 명시 없음, 참고)

- **FRED** (`update-economic-indicators` 06·12·18·22, `update-economic-calendar` 01:00): 호출 빈도 낮음, 안전.
- **Finnhub (60/min) + Marketaux (2,500/day)**: `collect-daily/market/category-news`.
  라인 148·431 주석이 `time.sleep(2)`로 Finnhub 60/min 준수 명시 → 자체 제어됨. 🟢

---

## 2. Queue 몰림 분석 (default vs neo4j)

### neo4j 큐 (solo pool, **동시 1개만** 처리 — 직렬)

neo4j 큐로 라우팅되는 beat 태스크 (`task_routes` 라인 43~61 기준):

| 태스크 | NY 시각 | 특성 |
|--------|---------|------|
| `sec-sync-dirty-neo4j` | **`*/5` 24시간 전체** | **288회/일 — neo4j 큐 최대 점유자** |
| `sync-news-to-neo4j` | :45 (08·10·12·14·16·18) 평일 | max 100건 |
| `chainsight-sync-profiles-neo4j` | 12:00 daily | |
| `chainsight-sync-relations-neo4j` | 12:30 daily | |
| `enrich-relationship-keywords` | 05:30 daily | **Gemini(느림)+neo4j 큐** |
| `cleanup-expired-news-relationships` | 04:00 daily | |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | |
| `neo4j-health-check` | `*/6h` | |

**판정**:
- 🔴 **`sec-sync-dirty-neo4j` */5 + solo pool 백로그 (P1)**:
  neo4j 큐는 동시 1개 직렬 처리인데 `sec-sync-dirty`가 5분마다 무한 투입.
  점(point) 동기화 태스크가 **5분 이상 걸리면 다음 sec-dirty가 큐에서 대기 → 백로그 누적**.
  `sec-sync-dirty`는 `expires=240`(4분)이라 **4분 넘게 밀린 인스턴스는 만료/드롭** → SEC 증거 동기화 누락 가능.
- 🔴 **05:30 `enrich-relationship-keywords` 큐 블로킹 (P1)**:
  이 태스크는 **Gemini 호출(100건, 15 RPM 기준 최소 ~7분)** 이면서 neo4j 큐에 있음.
  solo pool에서 실행 중 ~7분간 neo4j 큐 전체 점유 → 그 사이 `sec-sync-dirty`(05:30·05:35) **1~2회 드롭**.
- 🟠 **12:00 / 12:30 동시 몰림 (P2)**:
  - 12:00: `sec-sync-dirty`(12:00) + `chainsight-sync-profiles-neo4j`(12:00) 동시 큐 진입 → 직렬 처리.
  - 12:30: `sec-sync-dirty`(12:30) + `chainsight-sync-relations-neo4j`(12:30), 직후 12:45 `sync-news-to-neo4j`.
  - 프로파일/관계 풀 그래프 동기화가 길면 그 사이 sec-dirty 백로그·드롭.

### default 큐

- 장중(09–16): `refresh-market-pulse-cache`가 **매 분(*/1) = 60회/hr** + realtime/indices(*/5) +
  portfolio(*/10) + screener-alerts(*/15) → default 큐 상시 회전.
  🟡 cache 갱신이 외부 API 미사용·경량이면 무해하나, **매분 실행은 worker 1개 점유 시간 가산** → 18:00 배치 폭주와 겹치진 않음(장중 종료).
- 🟠 **18:00 default 큐 폭주 (P1)**: 18:00~18:45에 thesis 4종 + eod 파이프라인 + analyze(Gemini) +
  market-news + eod-prices(FMP 대량)이 default 큐로 집중 (히트맵 §3 참조).

---

## 3. 시간대별 API 호출 히트맵 (NY 기준, 평일)

### 3-A. Point/Batch 태스크 발사 수 (장중 interval 제외, 배치 폭주 가시화)

```
NY  │ 발사  │ 막대 (■ = 1 태스크)                         │ 비고
────┼───────┼─────────────────────────────────────────────┼──────────────────
00  │  0    │                                             │
01  │  1    │ ■                                           │ econ-calendar
02  │  0    │                                             │ (월1/토 추가)
03  │  0    │                                             │ (일/월1 추가:ML·overviews)
04  │  1    │ ■                                           │ cleanup-news(neo4j) (+주말 다수)
05  │  1    │ ■                                           │ enrich(Gemini+neo4j) (+토/일)
06  │  5    │ ■■■■■                                        │ FRED·뉴스·FMP-0615·cat-high·gen-news
07  │  6    │ ■■■■■■                                       │ digest·heat·cat-med·movers·cat-low·press
08  │  5    │ ■■■■■                                        │ keyword(G)·market-news·classify·analyze(G)·neo4j
09  │  2    │ ■■            ┊장중 interval 시작┊            │ sentiment·relations(G)
10  │  5    │ ■■■■■         ┊                  ┊            │ co-ment·fmp-1015·classify·analyze(G)·neo4j
11  │  1    │ ■            ┊                  ┊            │ relation-confidence
12  │  9    │ ■■■■■■■■■     ┊   ★PEAK #2★     ┊            │ FRED·뉴스·FMP·analyze(G)·neo4j×3·sec-seed
13  │  3    │ ■■■          ┊                  ┊            │ fmp-1315·cat-high·seed-selection
14  │  5    │ ■■■■■        ┊                  ┊            │ news·classify·analyze(G)·neo4j
15  │  2    │ ■■           ┊                  ┊            │ market-news·fmp-1515
16  │  6    │ ■■■■■■        ┊장중 interval 종료┊            │ breadth·heatmap·classify·analyze(G)·kw(G)·neo4j
17  │  4    │ ■■■■                                         │ daily-prices(FMP)·cat-high·fmp-1715·gen-news
18  │ 12    │ ■■■■■■■■■■■■   ★★ PEAK #1 ★★                 │ FRED·news·eod-prices(FMP500)·thesis×4·analyze(G)·eod·neo4j
19  │  2    │ ■■                                           │ ml-labels·backfill-accuracy
20  │  1    │ ■                                           │ sp500-financials(FMP 101)
21  │  0    │                                             │
22  │  1    │ ■                                           │ FRED
23  │  0    │                                             │
```

### 3-B. Interval 태스크 부하 밴드 (시간당 발사 횟수)

```
태스크                         │ 적용 시간대        │ 회/hr │ 큐
───────────────────────────────┼────────────────────┼───────┼───────
sec-sync-dirty-neo4j  (*/5)    │ 00–23 전체·매일    │  12   │ neo4j ◀ 24h 상시
check-pipeline-alerts (*/30)   │ 00–23 전체·매일    │   2   │ default
refresh-market-pulse  (*/1)    │ 09–16 평일         │  60   │ default ◀ 장중 최대
update-realtime       (*/5)    │ 09–16 평일         │  12   │ default(FMP)
update-market-indices (*/5)    │ 09–16 평일         │  12   │ default(FMP)
calculate-portfolio   (*/10)   │ 09–16 평일         │   6   │ default
check-screener-alerts (*/15)   │ 09–16 평일         │   4   │ default
───────────────────────────────┴────────────────────┴───────┴───────
⇒ 장중(09–16) default 큐 interval 합산 ≈ 94회/hr + point 배치
⇒ neo4j 큐는 24시간 12회/hr(sec-dirty)가 기저 부하
```

### 3-C. 피크 시간대 식별

| 순위 | NY 시각 | 부하 성격 | 핵심 리스크 |
|------|---------|-----------|-------------|
| 🥇 **18:00** | 배치 폭주 #1 (point 12 + neo4j + Gemini + FMP500) | FMP 18:00 EOD 500심볼 + thesis 4단 의존 체인 + analyze(Gemini) 동시 | API+큐+의존성 삼중 압박 |
| 🥈 **12:00** | 배치 폭주 #2 (point 9 + 장중 interval 94/hr) | FRED+FMP+Gemini(analyze) + neo4j×3 동시 + 장중 default 큐 회전 | neo4j 직렬 백로그 + default 혼잡 |
| 🥉 **06:00–08:00** | 아침 수집 폭주 (3시간 16 태스크) | 뉴스(Finnhub/Marketaux)+FMP+Gemini 수집 집중 | rate limit보단 worker 처리량 |

---

## 4. 스케줄 겹침 / 의존성 분석

이 시스템은 **명시적 체이닝(chord/chain) 대신 "시각 간격"으로 선후관계를 암묵 표현**한다.
선행 태스크가 간격 내 미완료 시 후속이 **불완전/stale 데이터로 실행**되는 race가 구조적으로 내재.

### 🔴 P1 — 18:00 EOD 의존 체인 (시각 간격 의존, 명시 체이닝 없음)

```
18:00 sync-sp500-eod-prices  (FMP ≈500심볼, ≥100초 소요, 한도시 더 지연)
   └─30분 간격─▶ 18:30 run-eod-pipeline        (EOD 가격 읽어 시그널 계산)
   └─30분 간격─▶ 18:30 update-sp500-change-percent (주석:"EOD sync 직후")
```
- eod-prices가 FMP 한도/CircuitBreaker로 18:30 넘기면 → **eod-pipeline이 미완성 가격으로 계산** (stale risk).
- chord/chain이 아닌 독립 beat 엔트리 → **완료 신호 없이 시각만 믿음**.

### 🔴 P1 — Thesis EOD 4단 파이프라인 (15분 간격 직렬 의존)

```
18:00 thesis-update-readings      (지표 수집)
  └15분▶ 18:15 thesis-calculate-scores     (수집 데이터로 스코어)
    └15분▶ 18:30 thesis-create-snapshots   (스코어로 스냅샷+알림)
      └5분▶ 18:35 thesis-generate-summaries (Gemini 요약)
```
- 각 단계 독립 beat. readings(FMP 지표)가 15분 초과 시 scores가 **부분 데이터로 계산** → 스냅샷·알림·요약까지 오염 전파.
- 18:00에 `sync-sp500-eod-prices`(FMP 대량)와 readings가 **FMP 한도를 공유** → readings 지연 가능성 ↑.

### 🟠 P2 — neo4j 동기화가 분석 완료를 앞지를 위험

```
:30 analyze-news-deep (Gemini, default큐, ≤50건)
  └15분▶ :45 sync-news-to-neo4j (neo4j큐, llm_analyzed=True 건만 동기화)
```
- 다른 큐라 병렬이나, analyze가 15분 초과 시 sync가 **그 회차 분석분을 못 잡음** → 다음 회차로 이월(soft).

### 🟠 P2 — Chain Sight 일일 체인 (시각 간격)

```
10:00 co-mentions ▶ 11:00 relation-confidence ▶ 12:00 sync-profiles-neo4j ▶ 12:30 sync-relations-neo4j ▶ 13:00 seed-selection
07:00 heat-score-daily ──────────────────────────────────────────────────────────▶ 13:00 seed-selection
```
- 1시간 간격이라 여유는 있으나, neo4j 큐 백로그(§2) 발생 시 12:00/12:30 동기화 지연 → 13:00 seed가 stale.

### 🟠 P2 — 일요일 ML 체인 (15~30분 간격 6단)

```
03:00 train-importance ▶ 03:30 shadow-report ▶ 04:00 check-auto-deploy
  ▶ 04:15 weekly-ml-report ▶ 04:20 monitor-ml ▶ 04:30 train-lightgbm
```
- 학습(train-importance)이 30분 초과 시 후속 리포트가 **구 모델 기준**으로 생성.

### 🟡 P3 — 동일 분 동시 발사 (worker 경합)

- **18:00**: econ-indicators / market-news-evening / sync-sp500-eod-prices / thesis-update-readings 4종 동시.
- **12:00**: econ-indicators / market-news-noon / sync-profiles-neo4j / sec-seed 4종 동시.
- **09:00**: aggregate-daily-sentiment / extract-news-relations 동시 + 장중 interval 시작.
- default 큐 worker 수가 적으면 동일 분 태스크가 직렬화되어 후속 의존 간격을 잠식.

---

## 5. 추가 발견 (Findings)

| ID | 심각도 | 발견 | 근거 |
|----|--------|------|------|
| **F-1** | 🔴 P1 | `beat_schedule` dict는 런타임 미적용 (DatabaseScheduler). 본 감사=설계 reference. DB 실측 교차검증 필수 | celery.py:124~140, settings.py |
| **F-2** | 🔴 P1 | `sec-sync-dirty-neo4j` `*/5` 24h + neo4j solo 큐 → 점 동기화 5분 초과 시 백로그·`expires=240` 드롭 | celery.py:784~788, 60 |
| **F-3** | 🔴 P1 | `enrich-relationship-keywords`(05:30)가 Gemini(~7분)+neo4j 큐 → 그 사이 sec-dirty 1~2회 드롭 | celery.py:592~597 |
| **F-4** | 🔴 P1 | 매월1일 `refresh-korean-overviews-monthly`(≈500 Gemini) + 평상 Gemini → 1,500 RPD 초과 가능 | celery.py:647~651 |
| **F-5** | 🔴 P1 | 18:00 EOD·Thesis 의존 체인이 chord/chain 아닌 시각 간격 의존 → stale 데이터 race | celery.py:633~683, 561~573 |
| **F-6** | 🟠 P2 | 18:00 FMP(eod 500)+thesis-readings FMP 한도 공유, 12:00 neo4j×3 직렬 몰림 | §2, §3 |
| **F-7** | 🟡 P3 | 주석 TZ 오기: `chainsight-heat-score-daily`(07:00 **UTC**), `seed-selection`(13:00 **UTC**), `neo4j-dirty-sync`(04:30 **UTC**)는 실제 NY 시각 발사 (CELERY_TIMEZONE=NY) | celery.py:747·754·761 vs 489 |
| **F-8** | 🟡 P3 | `update-realtime-prices` 1회 FMP call 수 미확인 → 장중 `*/5` 한도 판정 불가 | 코드 추가 검증 필요 |
| **F-9** | 🟢 정보 | 16:30/16:45 Gemini 충돌은 과거 audit P0 #8로 이미 분산 해결됨 | celery.py:290~297 |
| **F-10** | 🟢 정보 | FMP S&P500 뉴스 batch는 `rate_limit='100/m'`+CircuitBreaker로 자체 제어 | tasks.py:979~1016 |

---

## 6. 권고 (우선순위순, **실행은 별도 — 본 보고서는 읽기전용**)

1. **F-1**: DB `PeriodicTask` vs config dict diff 교차검증을 정기 운영 점검에 편입 (§0 명령).
2. **F-2/F-3**: neo4j 큐에서 `sec-sync-dirty` 주기 완화(`*/5`→`*/15`) 또는 별도 큐 분리 검토.
   `enrich-relationship-keywords`를 neo4j 큐에서 분리(쓰기만 neo4j, Gemini는 default).
3. **F-4**: `refresh-korean-overviews-monthly`를 월1 일괄 대신 일별 분할(예: 일 ~50기업) 검토 → RPD 평탄화.
4. **F-5**: 18:00 EOD·Thesis 체인을 beat 시각 간격 → Celery `chain()`/`chord()` 명시 의존으로 전환 검토.
5. **F-7**: 3개 주석의 "UTC"→"ET(NY)"로 정정 (혼동 방지, 코드 동작 영향 없음).
6. **F-8**: `update_realtime_with_provider`의 심볼당/회당 FMP call 수 측정 → 장중 한도 정밀 판정.

---

*본 보고서는 정적 분석 기반이며 실제 호출량·실행 시간은 측정값이 아닌 추정이다.
정확한 부하 판정은 (1) DB PeriodicTask 실측, (2) 각 태스크 1회 호출량 측정,
(3) Flower/로그 기반 실행시간 관측으로 보강해야 한다.*
