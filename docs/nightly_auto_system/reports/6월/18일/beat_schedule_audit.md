# Celery Beat 스케줄 감사 보고서

- **작성일**: 2026-06-18
- **대상**: `config/celery.py` `app.conf.beat_schedule` (전 70개 named 태스크)
- **성격**: 읽기 전용 감사 (코드 수정 없음)
- **감사자**: Claude (nightly auto system)

---

## 0. 핵심 전제 — Timezone과 "진실의 소스"

감사 결과를 읽기 전에 반드시 인지해야 할 두 가지 구조적 사실:

### 0-1. 모든 시간은 ET(America/New_York) 기준

```
config/settings.py:296   TIME_ZONE = 'Asia/Seoul'
config/settings.py:300   USE_TZ = True
config/settings.py:496   CELERY_TIMEZONE = 'America/New_York'   # NYSE 시간대
```

→ `beat_schedule`의 모든 `crontab(hour=...)` 은 **ET로 해석**된다. 본 보고서의 모든 시각은 ET 기준이다. (KST = ET + 13h(EST) / +13h(EDT는 +13 동일, 서머타임 보정은 OS tz DB가 처리). 야간 메일 07:00 KST ↔ ET 18:00 전후 매핑은 이 관계로 성립.)

### 0-2. ⚠️ beat_schedule dict는 런타임에 **무시됨** (DatabaseScheduler)

`config/celery.py:124-140` 주석에 명시:

> `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 때문에 Beat는 DB의 `django_celery_beat.PeriodicTask` 테이블을 진실의 소스로 사용한다. 아래 dict는 "선언적 reference"로만 존재한다.

> **본 감사의 한계**: 이 보고서는 `config/celery.py`의 **dict(설계 의도)** 를 분석한 것이다. 실제 실행 스케줄(DB `PeriodicTask`)과 dict가 **drift** 되어 있으면 본 보고서의 시간대 분석과 실제 실행이 어긋날 수 있다. **정확한 실측 감사를 위해서는 DB의 `PeriodicTask` 테이블과 dict의 diff 확인이 별도로 필요하다** (common-bug #28). 본 보고서는 그 diff를 수행하지 않았다.

---

## 1. Rate Limit 초과 구간 분석

### 1-1. FMP (Starter Plan: 300 calls/min, 10,000 calls/day)

FMP 의존 태스크 식별(태스크명·주석·코드 기준):

| 태스크 | 스케줄 (ET) | 추정 FMP 호출 규모 |
|---|---|---|
| `update-realtime-prices` | 평일 `*/5` 09–16시 | 관심종목/포트폴리오 수 |
| `update-market-indices` | 평일 `*/5` 09–16시 | 지수 소수 |
| `sync-daily-market-movers` | 평일 07:30 | gainers/losers 등 |
| `collect-sp500-news-fmp-*` | 평일 06:15·10:15·13:15·15:15·17:15 | **chord 6배치 × ~84 = 503종목** |
| `collect-press-releases-fmp` | 평일 07:45 | max 50종목 |
| `collect-general-news-fmp-*` | 평일 06:45·12:30·17:45 | 일반 뉴스 |
| `sync-sp500-eod-prices` | 평일 18:00 | S&P500 EOD |
| `sync-sp500-financials` | 평일 20:00 | 101종목/일 (5일 1회전) |
| `update-daily-prices` | 평일 17:00 | provider 동기화 |
| `sync-etf-holdings` | 월 06:00 | ETF holdings |
| `sync-sp500-constituents` | 매월 1일 02:00 | 구성종목 |

#### 🔴 발견 FMP-1: `collect-sp500-news-fmp-*` orchestrator 순간 폭발 위험

`services/news/tasks.py:1022` 확인 결과:

```python
batch_size = 84  # 503 / 6 ≈ 84
chord(collect_sp500_news_fmp_batch.s(batch) for batch in batches)(...)
```

- **503종목을 6배치로 chord fan-out** → 각 배치가 84종목을 순회하며 FMP 호출
- **Linux prefork 워커**: 6배치가 동시 실행 → 단시간에 503 calls 집중 → **300 calls/min 한도 초과 가능성 높음**
- **macOS solo pool**(`celery.py:36-37`): 6배치가 **직렬**화되어 분산됨 → 한도 내 안착 가능
- → **운영 환경(prefork) vs 개발(solo)에서 거동이 완전히 다름.** 배치 내부에 자체 rate limiter가 없으면 운영에서 429/throttle 위험

#### 🟡 발견 FMP-2: 장중 `:15`분 3중 FMP 동시 발생

`*/5` 태스크는 매시 `00,05,10,15,...` 에 실행 → **:15분에 sp500-news-fmp와 겹침**:

- **10:15 / 13:15 / 15:15 ET** 에 동시 발생:
  - `update-realtime-prices` (`*/5` → :15 포함)
  - `update-market-indices` (`*/5` → :15 포함)
  - `collect-sp500-news-fmp-NNNN` (503종목 fan-out)
- 세 FMP 태스크가 같은 분에 출발. orchestrator의 503 calls가 가격 갱신 호출과 한도를 공유 → **장중 FMP 피크 구간**

#### 🟢 양호: 일일 총량 (10,000/day)

대략적 상한 추정 — sp500-news 5회 × 503 + EOD 503 + financials 101 + 장중 가격 갱신(평일 12회/h × 8h × 종목수). 가격 갱신 종목 수가 수십 단위라면 일 총량은 1만 한도 내. **단, 가격 갱신 대상 종목이 수백이면 장중 누적만으로 한도 압박** → 종목 수 실측 필요(본 감사 범위 외).

---

### 1-2. Gemini (Free: 15 RPM / 1,500 RPD)

LLM(Gemini) 의존 태스크 식별:

| 태스크 | 스케줄 (ET) | 호출 규모 |
|---|---|---|
| `analyze-news-deep-batch` | 평일 08·10·12·14·16·18시 **:30** | **max 50건/회** (Gemini 2.5 Flash, `tasks.py:559`) |
| `thesis-generate-summaries` | 평일 18:35 | 가설별 요약 N건 |
| `extract-daily-news-keywords` | 매일 16:45 | 일일 키워드 |
| `keyword-generation-pipeline` | 매일 08:00 | gainers 키워드 |
| `enrich-relationship-keywords` | 매일 05:30 | limit 100 (Gemini Free 명시) |
| `bulk_generate_korean_overviews` | 매월1일 03:00 | S&P500 개요 |
| `extract-news-relations` | 매일 09:00 | 관계 키워드 (LLM 추정) |
| `chainsight-co-mentions` | 매일 10:00 | CoMention (LLM 추정) |

> ✅ **검증**: `classify-news-batch`는 규칙 엔진으로 Gemini 미사용 확인(`tasks.py` grep). LLM은 `analyze_news_deep`만. → `:15` classify와 `:30` analyze가 같은 시간대여도 Gemini 동시 호출은 아님.

#### 🔴 발견 GEMINI-1: 18:30 analyze + 18:35 summaries 5분 간격 충돌

- `analyze-news-deep-batch` 18:**30**, **50건** 처리. 15 RPM 한도면 **최소 50/15 ≈ 3.4분**, 실제로는 프롬프트 지연 포함 더 소요
- `thesis-generate-summaries` 18:**35** 시작 — analyze가 아직 50건을 다 못 끝낸 시점일 가능성 높음
- → **두 Gemini 태스크가 18:35~18:40 구간에서 동시 호출 → 15 RPM 순간 2배 초과 위험.** (주석에 명시된 audit P0 #15가 "snapshot 직후" 배치 사유이나, Gemini 동시성 관점은 미해결)

#### 🟡 발견 GEMINI-2: 16:30 analyze + 16:45 keywords — 기존 회피책의 잔존 리스크

`celery.py:290-296` 주석에 이미 기록된 알려진 충돌:

> 16:30 EST analyze-news-deep-batch와 Gemini 동시 호출 충돌 → 15 RPM 2배 초과 위험. 15분 분산하여 회피 (audit P0 #8)

- 15분 분산했으나, **analyze 50건이 15분 내 완료되지 않으면 16:45 keywords와 여전히 겹침.** 분산 간격(15분)이 최악 처리시간보다 짧을 수 있음 → 마진 부족

#### 🟡 발견 GEMINI-3: RPD(1,500/day) 누적 점검

평일 1일 Gemini 호출 개략 상한:
- analyze 6회 × 50 = **300**
- enrich 100, extract-keywords 배치, keyword-pipeline, extract-relations, co-mentions, thesis-summaries = 수백
- → 합산 **대략 500~900 RPD** 추정. 1,500 한도 내이나 **여유 ~40%**. 뉴스 급증일·재처리·재시도(max_retries) 누적 시 한도 근접 가능 → 모니터링 권장

---

### 1-3. Alpha Vantage (5 calls/min)

> ✅ **양호**: `--include=tasks.py` 전역 grep 결과 `alpha_vantage / ALPHA_VANTAGE / AlphaVantage` **매칭 0건**. 현재 beat_schedule에 AV 직접 의존 스케줄 태스크 없음. (거시지표 `update-economic-indicators`는 FRED API.) → **AV rate limit 충돌 구간 없음.**

---

## 2. Queue 몰림 분석 (default vs neo4j)

### 2-1. neo4j 큐 — solo pool 동시 1개 제약

`celery.py:43-61` task_routes + 개별 `'queue':'neo4j'` 옵션으로 neo4j 큐 라우팅. **이 큐는 `--pool=solo`로 동시 1개만 처리** → 직렬 병목.

neo4j 큐 태스크:

| 태스크 | 스케줄 (ET) | 비고 |
|---|---|---|
| `sec-sync-dirty-neo4j` | **`*/5` 매분(전일)** | **12회/시간 = 288회/일 — 베이스라인 부하** |
| `neo4j-health-check` | `*/6`시 :00 (00·06·12·18) | |
| `sync-news-to-neo4j` | 평일 08·10·12·14·16·18시 **:45** | max 100건 |
| `enrich-relationship-keywords` | 매일 05:30 | Gemini+neo4j 동시 |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | |
| `cleanup-expired-news-relationships` | 매일 04:00 | |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | |

#### 🔴 발견 QUEUE-1: 12:00 ET neo4j 큐 3중 적체

12:00 정각에 neo4j 큐로 동시 투입:
- `chainsight-sync-profiles-neo4j` (12:00)
- `neo4j-health-check` (12:00, `*/6`)
- `sec-sync-dirty-neo4j` (12:00, `*/5`)

→ solo pool 1개이므로 **직렬 대기**. 30분 뒤 12:30 `chainsight-sync-relations-neo4j` + `sec-dirty`(12:30) 또 적체. 12:45 `sync-news-to-neo4j`까지 → **12:00~12:45 neo4j 큐 연속 혼잡**. `sec-sync-dirty`의 `expires:240`(4분)이 짧아, 앞 태스크가 4분 넘게 큐를 점유하면 **dirty sync가 만료 폐기**될 수 있음.

#### 🟡 발견 QUEUE-2: `sec-sync-dirty-neo4j` 베이스라인이 solo 큐를 상시 점유

매 5분 도는 sec-dirty가 neo4j 큐의 상수 부하. 다른 무거운 neo4j 태스크(news 100건 sync, chainsight sync)가 돌 때 sec-dirty가 그 뒤에 쌓이며 `expires:240` 만료 위험. **단일 solo 워커가 neo4j 큐 전체의 직렬 처리량 상한**.

### 2-2. default 큐 — 장중 고빈도 누적

default 큐 장중(09–16, 평일) 베이스라인(분당 환산):
- `refresh-market-pulse-cache` 매분 → **60회/시간**
- `update-realtime-prices` `*/5` → 12
- `update-market-indices` `*/5` → 12
- `calculate-portfolio-values` `*/10` → 6
- `check-screener-alerts` `*/15` → 4
- `check-pipeline-alerts` `*/30`(전일) → 2

→ 장중 default 큐는 **시간당 ~96 태스크 베이스라인**. 여기에 시간대별 단발 태스크가 얹힘. prefork 다중 워커면 흡수 가능하나, **macOS solo(개발)에서는 default도 동시 1개** → 장중 매분 캐시 갱신이 다른 태스크를 밀어낼 수 있음.

---

## 3. 시간대별 API 호출 히트맵 (ET, 평일 기준)

각 시간대에 **트리거되는 named 태스크 수**(장중 반복 태스크는 그 시간 활성 시 1건으로 카운트). 주간(토·일)·월간 단발은 §5 참조.

```
ET  │ 태스크 수 (■=1)                          │ 주요 부하
────┼──────────────────────────────────────────┼─────────────────────
00  │ ■                                        │ baseline(neo4j health)
01  │ ■                                        │ econ-calendar
02  │ ·                                        │ (월간만)
03  │ ·                                        │ (주간/월간만)
04  │ ■                                        │ news-rel cleanup(neo4j)
05  │ ■                                        │ enrich-kw(Gemini+neo4j)
06  │ ■■■■■                                    │ 🟠 뉴스수집+FMP+FRED
07  │ ■■■■■■                                   │ 🟠 카테고리+movers+FMP+digest
08  │ ■■■■■                                    │ 🟠 keyword(G)+분류+analyze(G)
09  │ ■■  +장중baseline 시작                   │ sentiment+relations
10  │ ■■■■■  +baseline                         │ 🟠 co-ment+FMP503+analyze(G)
11  │ ■  +baseline                             │ rel-confidence
12  │ ■■■■■■■■■  +baseline                     │ 🔴🔴 PEAK#2 (FMP+Gemini+neo4j 3중)
13  │ ■■  +baseline                            │ seed+FMP503
14  │ ■■■■■  +baseline                         │ 카테고리+분류+analyze(G)
15  │ ■■  +baseline                            │ market-news+FMP503
16  │ ■■■■■  +baseline끝                       │ 🟠 breadth+heatmap+analyze(G)+kw(G)
17  │ ■■■                                      │ 카테고리+FMP503+FMP general
18  │ ■■■■■■■■■■■■                             │ 🔴🔴🔴 PEAK#1 (EOD+thesis+analyze(G))
19  │ ■■                                       │ backfill+ml-labels
20  │ ■                                        │ sp500-financials(FMP)
21  │ ·                                        │
22  │ ■                                        │ econ-indicators
23  │ ·                                        │
────┴──────────────────────────────────────────┴─────────────────────
상시 baseline(전 시간): sec-sync-dirty-neo4j(*/5), check-pipeline-alerts(*/30)
장중 baseline(09–16): market-pulse-cache(매분)+realtime+indices(*/5)+portfolio(*/10)+screener(*/15)
```

### 피크 시간대 식별

| 순위 | 시각(ET) | named 수 | 동시 부하 성격 |
|---|---|---|---|
| 🥇 **PEAK#1** | **18:00–18:45** | 12 | EOD가격(FMP) + thesis 4단 + analyze(Gemini) + summaries(Gemini) + news-neo4j sync |
| 🥈 **PEAK#2** | **12:00–12:45** | 9 | FMP503 + general-news(FMP) + analyze(Gemini) + neo4j 3중 + FRED |
| 🥉 PEAK#3 | 06:00–07:45 | 11(분산) | 아침 뉴스수집 폭주(FMP·카테고리·일반·press) |
| | 16:30–16:45 | 5 | breadth/heatmap + Gemini 2종(analyze+keywords) |

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 🔴 발견 DEP-1: 18:00–18:45 ET EOD 파이프라인 의존 체인의 시간 압박

```
18:00  sync-sp500-eod-prices (FMP, EOD 가격)  ← 선행 데이터
18:00  thesis-update-readings (지표 수집)
18:15  thesis-calculate-scores               ← readings 완료 가정
18:30  thesis-create-snapshots-and-alerts    ← scores 완료 가정
18:30  run-eod-pipeline (14 시그널)           ← EOD 가격 완료 가정
18:30  update-sp500-change-percent           ← EOD 가격 완료 가정
18:35  thesis-generate-summaries (Gemini)    ← snapshots 완료 가정
18:45  sync-news-to-neo4j
```

- **시간 간격이 15분/5분으로 매우 촘촘.** 각 단계가 "선행 완료"를 **시각 가정**으로만 의존(명시적 chord/chain 아님, 독립 crontab).
- 🔴 **경합 위험**: `sync-sp500-eod-prices`(503종목 FMP)가 18:00 시작해 18:30까지 안 끝나면, **18:30 `run-eod-pipeline`/`update-sp500-change-percent`가 미완성 EOD 가격으로 실행** → 부분 데이터 산출.
- 🔴 **Gemini 경합**(GEMINI-1 재확인): 18:30 analyze(50건) 진행 중 18:35 summaries → 15 RPM 초과.
- 동일 18:00에 `collect-market-news-evening` + `update-economic-indicators`도 추가.

### 4-2. 🟡 발견 DEP-2: 12:00 ET Chain Sight ↔ SEC ↔ neo4j 동시 출발

```
12:00  chainsight-sync-profiles-neo4j (neo4j 큐)
12:00  sec-seed-relations-to-chainsight       ← Chain Sight RelationConfidence 갱신
12:00  collect-market-news-noon (FMP general은 12:30)
12:30  chainsight-sync-relations-neo4j (neo4j 큐)  ← profiles sync 완료 가정
12:30  analyze-news-deep-batch (Gemini)
12:30  collect-general-news-fmp-noon (FMP)
```

- `sec-seed-relations-to-chainsight`와 `chainsight-sync-*-neo4j`가 **같은 Chain Sight 관계 데이터를 읽고/쓰며 12:00–12:30에 교차** → 데이터 경합 가능.
- neo4j 큐 직렬화로 `sync-relations`(12:30)가 `sync-profiles`(12:00) 뒤에 큐잉되는 건 오히려 순서 보장에 유리하나, 그 사이 `sec-sync-dirty`(*/5)가 끼어듦.

### 4-3. 🟡 발견 DEP-3: 뉴스 파이프라인 2시간 사이클의 단계 의존

`classify(:15) → analyze(:30) → sync-neo4j(:45)` 가 08·10·12·14·16·18시 반복. 각 15분 간격으로 **수집→분류→분석→동기화** 단계 가정.
- analyze가 max 50건을 15분 내 못 끝내면 다음 :45 sync가 **미분석 상태로 동기화**하거나, 다음 사이클 :15 classify와 겹침.
- 의존을 crontab 시각으로만 표현 → 처리시간 변동에 취약(soft 의존).

### 4-4. 🟢 양호: 회피 설계가 적용된 구간

- `extract-daily-news-keywords` 16:45: analyze 16:30과 15분 분산(주석 audit P0 #8) — 설계 의도 명확
- `sync-sp500-financials` 101종목/일 5일 1회전: 일 한도 분산 설계
- `aggregate-weekly-prices`: API 호출 없는 DB 집계, 토 01:00 한산 시간

### 4-5. 🟡 발견 DEP-4: 주석의 "UTC" 표기 ↔ 실제 ET 실행 drift 의심

`CELERY_TIMEZONE='America/New_York'`이므로 모든 `hour`는 ET인데, 다음 태스크 주석은 **"UTC"** 로 표기:

| 태스크 | 주석 표기 | 실제 실행(ET) | 의도가 UTC였다면 어긋남 |
|---|---|---|---|
| `chainsight-heat-score-daily` | "매일 07:00 **UTC**" | ET 07:00 | UTC 07:00 ≠ ET 07:00 (약 4–5h 차이) |
| `chainsight-seed-selection` | "매일 13:00 **UTC**" | ET 13:00 | 동일 |
| `chainsight-neo4j-dirty-sync` | "일요일 04:30 **UTC**" | ET 04:30 | 동일 |

- 🟡 주석이 "시드 선정 전 heat score" 같은 **순서 의도**를 담는데, UTC 의도를 ET로 실행하면 의도한 선후 관계가 깨질 수 있음. **주석 오기 vs 실제 의도 불일치를 코드 소유자가 확인 필요.** (단 heat-score 07:00 → seed-selection 13:00 의 6시간 간격은 ET로 해석해도 선후 자체는 유지됨)

---

## 5. 부록 — 주간/월간 단발 태스크 (히트맵 외)

| 시각(ET) | 태스크 | 주기 |
|---|---|---|
| 토 01:00 | aggregate-weekly-prices | 매주 토 |
| 토 02:00 | chainsight-all-profiles | 매주 토 |
| 토 03:00 | chainsight-price-co-movement | 매주 토 |
| 토 04:00 | chainsight-stale-decay | 매주 토 |
| 토 04:30 | chainsight-aggregate-profiles | 매주 토 |
| 토 05:00 | validation-weekly-batch | 매주 토 |
| 일 03:00 | train-importance-model | 매주 일 |
| 일 03:30 | generate-shadow-report | 매주 일 |
| 일 04:00 | check-auto-deploy, cleanup-old-macro-data | 매주 일 |
| 일 04:15 | generate-weekly-ml-report | 매주 일 |
| 일 04:20 | monitor-ml-performance | 매주 일 |
| 일 04:30 | train-lightgbm-model, chainsight-neo4j-dirty-sync | 매주 일 |
| 일 05:00 | cleanup-task-results | 매주 일 |
| 월 04:00 | scan-regulatory-relationships | 매주 월 |
| 월 06:00 | sync-etf-holdings | 매주 월 |
| 1일 02:00 | sync-sp500-constituents | 매월 1일 |
| 1일 02:30 | archive-old-articles | 매월 1일 |
| 1일 03:00 | refresh-korean-overviews-monthly | 매월 1일 |
| 1일 04:30 | build-patent-network | 매월 1일 |
| 1일 06:00 | sec-check-new-filings | 매월 1일 |
| 15일 03:00 | sync-supply-chain-batch | 매월 15일 |
| 16일 04:00 | sync-institutional-holdings | 매월 16일 |

#### 🟡 발견 WEEK-1: 일요일 03:00–05:00 ML 파이프라인 직렬 의존

`train-importance(03:00) → shadow-report(03:30) → check-auto-deploy(04:00) → weekly-ml-report(04:15) → monitor(04:20) → train-lightgbm(04:30)` — 30분/15분/5분 간격 의존 체인. ML 학습이 30분 초과 시 후속 리포트가 **구버전 모델 기준**으로 생성될 위험(DEP-1과 동일 패턴).

#### 🟡 발견 WEEK-2: 토요일 04:00–04:30 neo4j 큐 + Chain Sight 집계 겹침

`chainsight-stale-decay(04:00)` + `chainsight-aggregate-profiles(04:30)` + 일요일과 다른 날이지만 `cleanup-expired-news-relationships(매일 04:00, neo4j)`가 매일 겹침.

---

## 6. 종합 권고 (우선순위순)

| # | 심각도 | 발견 | 권고 |
|---|---|---|---|
| 1 | 🔴 | FMP-1: orchestrator 503 fan-out이 prefork에서 300/min 초과 | 배치 내 rate limiter 확인 / chord 배치 수↑·딜레이 추가 검토 |
| 2 | 🔴 | GEMINI-1: 18:30 analyze + 18:35 summaries 15 RPM 초과 | summaries를 18:45 이후로 이동 또는 동일 큐 직렬화 |
| 3 | 🔴 | DEP-1: 18:00 EOD 가격 미완 시 18:30 파이프라인 부분 실행 | crontab 시각 의존 → 명시적 chain/chord로 전환 검토 |
| 4 | 🟡 | QUEUE-1: 12:00 neo4j 큐 3중 적체 + sec-dirty expires:240 폐기 | neo4j sync 시각 분산 / sec-dirty expires 상향 |
| 5 | 🟡 | DEP-4: 주석 "UTC" ↔ 실제 ET drift | 주석 정정 또는 의도 재확인 |
| 6 | 🟡 | GEMINI-3: RPD 1,500 여유 ~40% | Gemini 일일 호출 카운터 모니터링 |
| 7 | ⚪ | §0-2 dict ↔ DB PeriodicTask drift | **별도 감사 필요** (이 보고서 미수행) |

---

## 7. 감사 한계 명시

1. 본 보고서는 `config/celery.py` **dict(설계 의도)** 기준. 실제 실행은 DB `PeriodicTask`(§0-2). **dict↔DB diff 미수행** — 실제 스케줄과 어긋날 수 있음.
2. 각 태스크의 **실제 API 호출 횟수**는 종목 수·뉴스 건수 등 런타임 데이터에 의존 → 추정값. 정확 측정은 운영 로그(`stocks.log`) / FMP·Gemini 대시보드 카운터 필요.
3. FMP-1의 prefork 동시성 위험은 **운영 환경(Linux prefork) 가정**. 현재 macOS solo 운영 중이면 직렬화로 완화됨(`celery.py:36`).
4. `extract-news-relations`·`chainsight-co-mentions`의 Gemini 사용은 **태스크명 기반 추정**(코드 미확인).

*— 끝. 코드 수정 없음, 읽기 전용 감사 완료.*
