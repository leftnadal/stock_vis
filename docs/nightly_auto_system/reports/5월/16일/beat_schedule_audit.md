# Celery Beat Schedule 감사 보고서

- **작성일**: 2026-05-16
- **대상 파일**: `config/celery.py` (820 줄, beat_schedule 86개 등록 키)
- **검토 모드**: Read-only (코드 수정 없음)
- **타임존 설정**: `CELERY_TIMEZONE = 'America/New_York'` (NYSE 기준)
  - Django 본체 `TIME_ZONE = 'Asia/Seoul'`와 다른 것을 인지하고 본 감사는 ET 기준으로 환산
- **Worker 풀**:
  - macOS (개발기): `solo` 강제 (fork SIGSEGV 방지)
  - Linux (운영): `prefork` (기본)
  - **neo4j 큐**: 별도 워커, `--pool=solo` 강제 (동시 처리 = 1)
- **관련 경고**: `beat_schedule` dict는 `DatabaseScheduler` 사용 시 무시됨 (config/celery.py L120-134). 본 감사는 dict 선언을 기준으로 함. **DB의 `PeriodicTask`와의 drift 가능성**은 후속 audit에서 별도 검증 필요.

---

## 0. Executive Summary (요약)

| 항목 | 등급 | 한 줄 요약 |
|---|---|---|
| FMP Rate Limit | 🟡 주의 | 18:00 ET·17:00 ET·08:00 ET·:15 분 windows에서 200~500+ req 동시 발사 가능, 300/min 한도 근접 |
| Gemini Rate Limit | 🔴 위험 | 16:30·18:30 ET에 `analyze-news-deep-batch(50건)` 1회만으로 15 RPM 한도 3배 초과 가능 |
| Alpha Vantage | 🟢 양호 | 명시적 AV 의존 Beat 태스크 없음 (애드혹 호출은 별도 검증 영역) |
| Queue 몰림 (default) | 🔴 위험 | 18:30 ET 슬롯 — 동시 등록 태스크 5개 + 시장시간 마지막 분 잔류 트래픽 충돌 |
| Queue 몰림 (neo4j, solo) | 🟡 주의 | 5분마다 `sec-sync-dirty-neo4j` 상시 점유 + 12:00·12:30·`*45` 분 윈도우 큐 백로그 |
| Schedule Drift | 🔴 위험 | 댓글-실제 timezone 불일치 3건 (chainsight UTC 표기 → 실제 ET 동작) |
| 선후행 의존성 | 🟡 주의 | thesis EOD 4단(18:00→18:35) 간격 5~15분, 선행 지연 시 후속 빈 데이터 위험 |

**P0 (즉시)**: Gemini 폭주 (16:30, 18:30), thesis EOD 의존성 타이밍, chainsight UTC 표기 불일치
**P1 (이번 주)**: 18:00·18:30 default 큐 몰림, neo4j 큐 백로그, train-importance-model → shadow-report 간격
**P2 (백로그)**: 시장시간 5분 단위 FMP 호출 총량 측정, drift 자동 모니터링

---

## 1. Rate Limit 초과 구간 분석

### 1.1 FMP (Starter Plan: 300 calls/min, 10,000/day)

**FMP를 직접 호출하는 Beat 태스크 목록**

| 태스크 | 스케줄 (ET) | 추정 호출량 | 비고 |
|---|---|---|---|
| `update-realtime-prices` | `*/5 9-16 평일` | 시장 종목 수 ≈ 500 / 분기 호출 | 5분마다 batch |
| `update-daily-prices` | `17:00 평일` | 500+ | 단발 |
| `sync-sp500-financials` | `20:00 평일` | 101 (코드 주석: 101개/일) | 순환 배치 5일 1회전 |
| `update-market-indices` | `*/5 9-16 평일` | 지수 ≈ 10 | 5분마다 |
| `sync-daily-market-movers` | `07:30 평일` | gainers/losers ≈ 50 | 시장 개장 전 |
| `collect-sp500-news-fmp-{0615,1015,1315,1515,1715}` | 시간:15 평일 | 1회당 S&P 500 전체 = 500+ (orchestrator) | **하루 5회 폭격** |
| `collect-press-releases-fmp` | `07:45 평일` | max_symbols=50 | 안정적 |
| `collect-general-news-fmp-{morning,noon,evening}` | `06:45·12:30·17:45 평일` | ~10 | 안정 |
| `sync-sp500-eod-prices` | `18:00 평일` | 500 | 단발 |

**🔴 P0 — FMP 한도 근접 의심 구간**

#### (a) 18:00 ET (장 마감 + 2시간)
동시 발사:
- `sync-sp500-eod-prices` (500 calls)
- `update-economic-indicators` (FRED, FMP 아님)
- `collect-market-news-evening` (Marketaux/내부)
- `thesis-update-readings` (지표 데이터 수집 — FMP 가능성)

EOD 500 종목을 1분 안에 호출하면 단일 작업만으로 300/min 초과. → 코드의 **내부 rate limiter** 존재 확인 필요. (본 감사 범위 외, 후속 점검 영역)

#### (b) `*:15 분` 패턴 (06:15, 10:15, 13:15, 15:15, 17:15 ET)
- `collect-sp500-news-fmp-*` orchestrator가 한 번에 S&P 500 종목 뉴스 fan-out 시도. 1분 내 500+ 호출 발생 가능. **운영 부담이 가장 큰 시각대.**
- 10:15, 13:15, 15:15는 시장시간 중복 → `update-realtime-prices`, `update-market-indices`와 합산 시 사실상 300/min 한도를 동시간대 합산해 점유.

#### (c) 시장시간 (09:00~16:55 ET) 분당 합산
| 분 모드 | 동시 실행 |
|---|---|
| `*/5` (00,05,...,55) | realtime-prices + market-indices = 510+ calls 시도 |
| `*/10` | + portfolio-values (내부) |
| `*/15` | + screener-alerts |
| `*` 매분 | + refresh-market-pulse-cache (캐시 갱신, FMP 직접 ✗) |

분당 한도 305+ 가능성. 내부 throttle 부재 시 즉시 한도 초과.

#### (d) 일일 한도 (10,000 calls/day)
대략 산정:
- 시장시간 realtime+indices: 8시간 × 12회/시 × 평균 510 calls/회 = 49,000 (← 명백히 batch 분할 호출이어야 함)
- EOD/financials/news orchestrator: 추가 3,000~5,000
- **상한선 의심**: 코드 내부에서 1회 호출에 여러 ticker를 묶어 보내는 batch 엔드포인트(`/stable/quotes?symbols=A,B,...`)를 쓰지 않는 경우 일일 한도 즉시 초과. 코드 레벨 검증 필요.

---

### 1.2 Gemini (Free: 15 RPM, 1500 RPD)

**Gemini 직간접 호출 Beat 태스크**

| 태스크 | 스케줄 (ET) | 호출량 | 신뢰도 |
|---|---|---|---|
| `keyword-generation-pipeline` | `08:00 매일` | gainers 분량 | 회당 ~10~20 |
| `extract-daily-news-keywords` | `16:45 매일` | 일일 뉴스 | 수십 |
| `analyze-news-deep-batch` | `:30 8,10,12,14,16,18 평일` | **max_articles=50** | **회당 50** |
| `extract-news-relations` | `09:00 매일` | 최근 24h 기사 | 수십 |
| `enrich-relationship-keywords` | `05:30 매일` (neo4j queue) | **limit=100** | 회당 100 |
| `thesis-generate-summaries` | `18:35 평일` | 활성 가설 수 | 회당 5~30 |
| `refresh-korean-overviews-monthly` | `03:00 매월1일` | S&P 500 부분 | 월간 |
| (간접) `classify-news-batch-morning` | `:15 8,10,12,14,16,18 평일` | hours=3 분류 | 룰 기반 위주 |

**🔴 P0 — Gemini 한도 폭주 의심 구간**

#### (a) 16:30 ET 슬롯 (장 마감)
- `analyze-news-deep-batch` (50건) — 1회당 50 LLM 호출 → **15 RPM의 3.3배** (60초 분산 가정 시 50/60 ≈ 50 RPM 등가)
- `extract-daily-news-keywords` (16:45 ET) — 15분 후, 같은 워커 큐 잔여물과 겹칠 위험

> 코드 주석 (L284-286): "audit P0 #8, 2026-04-26 — analyze-deep와 15분 간격"으로 keyword extraction을 16:45로 분산 완료. **그러나 analyze-deep 자체의 50건/회는 여전히 RPM 초과 위험** — 본 감사의 새 발견.

#### (b) 18:30 ET 슬롯 (장 마감 + 2.5h)
- `analyze-news-deep-batch` (50건) 18:30
- `thesis-generate-summaries` 18:35 — 5분 간격, deep-batch 백로그가 남아있을 가능성

#### (c) 08:30 / 10:30 / 12:30 / 14:30 / 16:30 / 18:30 — 매 2시간 반복
- `analyze-news-deep-batch`(50) + 동일 시각 `classify-news-batch` 분류 결과 의존
- 만약 60초 안에 50건 호출 시도하면 **하루 6회 × 15 RPM 한도 초과 사건 발생 가능**

#### (d) Gemini 일일 한도 (1500 RPD)
산정:
- `analyze-news-deep-batch` 50 × 6 = 300
- `enrich-relationship-keywords` 100
- `extract-news-relations` ~50
- `extract-daily-news-keywords` ~50
- `keyword-generation-pipeline` ~20
- `thesis-generate-summaries` ~30
- 합계 ~550 (월요일은 +`refresh-korean-overviews-monthly` 부분)

→ 일일 한도는 여유 있음. **분당 한도가 병목.** 내부 throttle(backoff/슬립) 또는 sub-task로 분산 적용 여부가 핵심.

---

### 1.3 Alpha Vantage (5 calls/min)

Beat 스케줄 내 AV 직접 호출 태스크 **0건 확인** (`stocks.tasks.*`, `macro.tasks.*` Beat 진입 점에 AV 명시 없음).

- AV는 애드혹/온디맨드 fetch 위주로 사용되는 것으로 보이며, **Beat 측 위험도 없음**.
- 단, `update-economic-indicators`가 FRED를 쓴다고 가정했으나 코드에서 AV 백업 분기 존재 가능 — 본 감사 범위 외.

---

## 2. Queue 몰림 분석

### 2.1 큐 라우팅 (task_routes, L37-55)

**neo4j 큐 라우팅 태스크 (총 13건)**:
- `rag_analysis.tasks.*` (8건) — health_check, semantic_cache, sync_stock 등
- `news.tasks.sync_news_to_neo4j`
- `news.tasks.cleanup_expired_news_relationships`
- `serverless.tasks.enrich_relationship_keywords`
- `chainsight.tasks.sync_tasks.sync_profiles_to_neo4j`
- `chainsight.tasks.sync_tasks.sync_relations_to_neo4j`
- `chainsight-neo4j-dirty-sync` (alias 태스크)
- `sec_pipeline.tasks.sync_dirty_to_neo4j`

**기타 모든 태스크**: `default` 큐

### 2.2 default 큐 시간대별 부하 (평일 기준)

| 시간 (ET) | 동시 등록 태스크 수 | 위험 슬롯 |
|---|---|---|
| 18:30 | **5건 동시** | 🔴 thesis-create-snapshots, run-eod-pipeline, update-sp500-change-percent, analyze-news-deep-batch, +시장시간 직후 잔류 |
| 18:00 | 4건 | 🟡 update-economic-indicators, collect-market-news-evening, sync-sp500-eod-prices, thesis-update-readings |
| 07:00 | 3건 | 🟢 celery-error-digest, chainsight-heat-score-daily, collect-category-news-medium-morning |
| 08:00 | 3건 | 🟢 keyword-generation-pipeline, collect-market-news-morning, update-market-indices(시장 첫 분) |
| 09:00 | 3건 | 🟢 aggregate-daily-sentiment, extract-news-relations, +시장시간 5분 슬롯 |
| 17:00 | 3건 | 🟢 update-daily-prices, collect-category-news-high-evening, +시장 종료 직후 |
| 시장시간 매분 :00 | 2~5건 (분별로 변동) | 🟡 realtime + indices + market-pulse-cache + (5/10/15분 슬롯) |

### 2.3 neo4j 큐 (solo pool, 동시 1) 부하

| 시간 (ET) | 등록 태스크 |
|---|---|
| **상시 (5분마다)** | `sec-sync-dirty-neo4j` (`*/5`, expires=240s) — **이 1개로 큐의 대부분 점유** |
| 6시간마다 (0/6/12/18) | `neo4j-health-check` |
| 매일 04:00 | `cleanup-expired-news-relationships` |
| 매일 05:30 | `enrich-relationship-keywords` (Gemini + Neo4j, 100건) |
| 매일 12:00 | `chainsight-sync-profiles-neo4j` |
| 매일 12:30 | `chainsight-sync-relations-neo4j` |
| 매일 :45 (8,10,12,14,16,18) | `sync-news-to-neo4j` (max_articles=100) — **하루 6회** |
| 매주 일요일 04:30 | `chainsight-neo4j-dirty-sync` |

**🟡 P1 — neo4j 큐 백로그 위험**

- `sec-sync-dirty-neo4j`가 5분 안에 끝나지 못하면 다음 fire가 queueing → 4분 만료(expires=240s)로 곧 폐기
- **12:00 ET 시점**: `sec-sync-dirty-neo4j` (12:00 fire) + `chainsight-sync-profiles-neo4j` (12:00) + `sec-seed-relations-to-chainsight` (12:00, default 큐) — sec-sync-dirty가 길어지면 chainsight-sync-profiles는 동일 큐 대기
- **12:30 ET**: `chainsight-sync-relations-neo4j` + `sec-sync-dirty` (12:30) — 같은 패턴 재발
- **18:45 ET**: `sync-news-to-neo4j` (100건) + `sec-sync-dirty` (18:45) — sync-news가 무거우면 sec-sync가 expires=240s 안에 발사 못함

→ Neo4j 큐는 sec-sync 5분 주기 + 무거운 chainsight/news 동기화가 같은 슬롯에 집중되면 **연쇄 폐기/지연 발생**. 큐별 워커 분리(또는 sec-sync 주기 완화)를 검토할 가치 있음.

---

## 3. 시간대별 API 호출 히트맵 (평일, ET 기준)

각 칸은 해당 시간대(분 전체)에 fire되는 **고유 태스크 등록 수**. 시장시간(9-16) 셀에는 5/10/15/매분 반복 태스크가 누적되어 실제 fire 횟수는 ()로 표기.

```
시간   태스크수  분포 막대 (■ = 1 unique task, ⊞ = market-hours repeating)
────────────────────────────────────────────────────────────────────
00:00     0
01:00     1     ■                                     (update-economic-calendar 매일)
02:00   0~3     ■■■                                   (월간/주간 야간 정비)
03:00   0~6     ■■■■■■                                (Sun ML 학습 + Sat chainsight + 월간)
04:00   1~11    ■■■■■■■■■■■                           (🔴 일요일 ML 파이프 + Sat decay + Mon scan + 월간)
05:00   1~3     ■■■                                   (enrich-keywords + Sat validation + Sun cleanup)
06:00     6     ■■■■■■                                (news collect 다발 + FMP 0615 + ETF Mon)
07:00     6     ■■■■■■                                (heat-score + error-digest + market-movers + general-fmp)
08:00     5     ■■■■■                                 (🟡 keyword-pipeline + market-news + classify+deep+sync-neo4j)
09:00 ⊞   4 + (12+12+60+6+4) = 98 fires/h            (🔴 시장시작; aggregate-sentiment + extract-news-relations)
10:00 ⊞   5 + 94 = 99                                 (chainsight-co-mentions + classify+deep+sync-neo4j + FMP-1015)
11:00 ⊞   1 + 94 = 95                                 (chainsight-relation-confidence)
12:00 ⊞   7 + 94 = 101                                (🔴 chainsight neo4j sync 2종 + SEC seed + FMP-noon + classify+deep+sync)
13:00 ⊞   3 + 94 = 97                                 (category-high-midday + chainsight-seed + FMP-1315)
14:00 ⊞   5 + 94 = 99                                 (daily-news-afternoon + category-medium + classify+deep+sync)
15:00 ⊞   2 + 94 = 96                                 (market-news-afternoon + FMP-1515)
16:00 ⊞   6 + 94 = 100                                (🔴 마감; breadth + heatmap + classify+deep+keywords+sync-neo4j)
17:00     5     ■■■■■                                 (update-daily-prices + category-high-evening + FMP-1715 + general-fmp)
18:00     7     ■■■■■■■                               (🔴 EOD 폭주; eod-prices + economic + market-news + thesis 3종 + classify+deep+sync)
19:00     2     ■■                                    (collect-ml-labels + backfill-signal-accuracy)
20:00     1     ■                                     (sync-sp500-financials FMP)
21:00     0
22:00     1     ■                                     (update-economic-indicators)
23:00     0
────────────────────────────────────────────────────────────────────
범례: ⊞ = 시장시간 누적 (분당 매분/5분/10분/15분 반복 포함)
      🔴 = P0, 🟡 = P1
```

**상시 fire (시간대 무관)**
- `sec-sync-dirty-neo4j` — `*/5` (전 시간 매 5분, 288회/일)
- `check-pipeline-alerts` — `*/30` (전 시간 매 30분, 48회/일)
- `neo4j-health-check` — `0 */6` (00, 06, 12, 18)
- `refresh-market-pulse-cache` — `* 9-16 1-5` (시장시간 매분, 480회/평일)

**평일 일일 총 fire 횟수 (추정)**
- 시장시간 매분 반복류: 약 ~570 fire
- 시간 단위 발사: 약 ~70
- 상시류 (sec-sync, alerts): 약 ~340
- **합계: 평일 ~ 980 fire/일** (외부 API 호출은 작업당 N건이므로 곱해서 산정 필요)

---

## 4. 스케줄 겹침 / 의존성 분석

### 4.1 강한 의존 체인 (선행 완료 전 후속 시작 위험)

#### 🔴 P0 — Thesis EOD Pipeline (4단)
```
18:00 thesis-update-readings   (지표 수집, FMP/내부)
  ↓ 15분
18:15 thesis-calculate-scores  (계산)
  ↓ 15분
18:30 thesis-create-snapshots  (스냅샷 + 알림)
  ↓ 5분
18:35 thesis-generate-summaries (Gemini, 활성 가설 수만큼 LLM 호출)
```
- 18:00 단계가 FMP 한도(앞서 분석한 18:00 폭주)에 걸려 지연되면 18:15가 빈 데이터로 계산 → 18:30/18:35 모두 garbage → **사일런트 실패** 가능
- 5분 간격(18:30→18:35)은 Gemini 15 RPM 한도와 충돌 가능
- 권장: 각 단계에 직전 단계 산출물 readiness check 필요 (본 감사 범위 외, 코드 점검 사항)

#### 🔴 P0 — News Intelligence 2시간 트리오
```
:15 classify-news-batch        (3시간치)
:30 analyze-news-deep-batch    (Gemini, 50건)
:45 sync-news-to-neo4j         (neo4j queue, 100건)
```
- 8, 10, 12, 14, 16, 18 매 2시간 동일 패턴
- classify가 늦게 끝나면 deep-batch가 분류 안 된 기사를 들고 출발 (max_articles=50 충족 못함)
- deep-batch가 길어지면 sync-news-to-neo4j(45분)가 분석 미완료 기사를 동기화

#### 🟡 P1 — EOD Dashboard
```
18:00 sync-sp500-eod-prices   (FMP 500종목)
  ↓ 30분
18:30 run-eod-pipeline         (14개 시그널 계산)
  ↓ 30분
18:30 update-sp500-change-percent (같은 슬롯, 단순 계산)
  ↓ 30분
19:00 backfill-signal-accuracy
```
- 18:00 EOD가 30분 안에 끝나야 하는데 FMP 한도 충돌 시 위험. **expires=3600s**로 1시간 유효 → 18:30 ~ 19:00 사이 적시성 잃을 수 있음

#### 🟡 P1 — Sunday ML Training (좁은 30분 윈도우)
```
03:00 train-importance-model        (expires=7200, 2h)
03:30 generate-shadow-report        ← 학습이 30분 초과 시 모델 미반영 분석
04:00 check-auto-deploy
04:15 generate-weekly-ml-report
04:20 monitor-ml-performance
04:30 train-lightgbm-model          (expires=7200)
```
- importance-model 학습 30분 가정은 데이터 크기 증가 시 깨질 위험
- 04:00 슬롯에는 `cleanup-expired-news-relationships`(평일/주말 무관) + `chainsight-stale-decay(Sat)` + 월간 `sync-institutional-holdings(day=16)` + `scan-regulatory-relationships(Mon)`이 같은 분에 동시 발사

### 4.2 동일 시각 다중 fire (default 큐)

| 시각 (ET) | 동시 fire 태스크 | 비고 |
|---|---|---|
| **18:30 (평일)** | thesis-create-snapshots, run-eod-pipeline, update-sp500-change-percent, analyze-news-deep-batch, (시장시간 막 종료) | 🔴 default 큐 5건 |
| **18:00 (평일)** | update-economic-indicators, collect-market-news-evening, sync-sp500-eod-prices, thesis-update-readings | 🔴 default 큐 4건, FMP/news 혼합 |
| **04:00 매일** | cleanup-expired-news-relationships, +요일별 (Sun: check-auto-deploy, Mon: scan-regulatory, Sat: chainsight-stale, day=16: institutional-holdings) | 🟡 정비 슬롯 폭주 |
| **04:30** | chainsight-aggregate-profiles(Sat), train-lightgbm-model(Sun), chainsight-neo4j-dirty-sync(Sun), build-patent-network(day=1) | 🟡 |
| **12:00 ET 매일** | chainsight-sync-profiles-neo4j (neo4j), sec-seed-relations-to-chainsight (default), update-economic-indicators (평일) | 🟡 큐 분리되어 충돌 적음 |

### 4.3 타임존 표기 ↔ 실제 동작 Drift (🔴 P0)

`CELERY_TIMEZONE='America/New_York'` 기준으로 모든 crontab이 해석되는데, 코드 댓글의 표기가 일관되지 않음:

| 태스크 | 댓글 표기 | 실제 동작 (ET) | 위험 |
|---|---|---|---|
| `chainsight-heat-score-daily` | "매일 07:00 **UTC**" | 07:00 ET (= 12:00 UTC) | 🔴 운영팀이 UTC 기준으로 디버그 시 5시간 오차 |
| `chainsight-seed-selection` | "매일 13:00 **UTC**" | 13:00 ET (= 18:00 UTC) | 🔴 동일 |
| `chainsight-neo4j-dirty-sync` | "일요일 04:30 **UTC**" | 04:30 ET (= 09:30 UTC) | 🔴 동일 |
| 다수의 news/market 태스크 | "EST" | ET (DST 적용) | 🟡 표기 일관성 |

→ **권장(읽기 전용 보고)**: 댓글을 ET로 통일하고, 의도가 UTC였다면 `crontab(...)`의 hour를 변환하거나 별도 timezone 명시. (수정은 본 감사 범위 외)

### 4.4 Drift 위험 (config dict ↔ DB PeriodicTask)

`config/celery.py` L120-134 에 명시된 그대로:
- `DatabaseScheduler` 사용 → **config dict는 reference only, 런타임은 DB가 진실의 소스**
- 2026-04-24 복구 기록: `chainsight-heat-score-daily`, `sec-seed-relations-to-chainsight` 누락 → 수동 복구
- **본 감사로는 DB drift 여부 확인 불가** (read-only 감사). 후속으로 `python manage.py shell`에서 `set(PeriodicTask.objects.values_list('name', flat=True)) ^ config_keys` 비교 권장.

---

## 5. 우선순위별 조치 후보 (수정 제안 — 본 보고서는 권고만, 실행은 별도 PR)

### P0 (즉시)
1. **`analyze-news-deep-batch`의 50건/회 Gemini 폭주**: max_articles=50을 내부 분할(예: 10개씩 6회 fire, 또는 sub-task chunking + sleep)으로 변경하거나, Gemini Pro 유료 RPM으로 전환 결정
2. **타임존 댓글 통일**: chainsight 3개 태스크 댓글의 UTC → ET 정정 (실제 동작 변경 없음, 디버깅 혼란 제거)
3. **Thesis EOD 4단 readiness check**: 각 단계 시작 시 직전 단계 산출물 (TableX의 latest 행) 존재 검증, 없으면 skip + 알림

### P1 (이번 주)
4. **18:00·18:30 ET default 큐 분산**: thesis-update-readings(18:00) → 17:50으로, update-sp500-change-percent(18:30) → 18:40으로 등 분 단위 분산
5. **neo4j 큐 분리 또는 sec-sync 주기 완화**: 5분 → 10분 또는 별도 sec-queue
6. **DB ↔ config drift 자동 모니터**: 일일 cron 또는 health check API에서 set diff 출력

### P2 (백로그)
7. **FMP 호출 총량 계측**: 5분 슬롯에 실제 호출 수 카운터 추가 (Prometheus 등)
8. **AV 의존 코드 경로의 명시화**: Beat 외 호출 경로의 throttle 단일 소스화

---

## 6. 부록 — 전체 86개 태스크 카탈로그 (요약)

(자세한 라우팅 정보는 `config/celery.py` 참조)

### 6.1 기능 영역별 태스크 수

| 영역 | 태스크 수 | 비고 |
|---|---|---|
| Stocks/EOD | 9 | realtime, daily, weekly aggregate, financials, portfolio, eod-pipeline, backfill, korean-overview |
| Macro | 5 | indicators, indices, calendar, market-pulse-cache, cleanup |
| Market Movers + Keyword | 2 | sync-movers, keyword-pipeline |
| News 수집 | 11 | daily 2건, market 4건, category 6건 (high/medium/low), keywords 1건 |
| News Intelligence v3 | 12 | classify, deep, ml-labels, sync-neo4j, cleanup, train, shadow, deploy, monitor, lightgbm, weekly-report, alerts |
| FMP News | 9 | sp500 orchestrator 5건, press releases 1건, general 3건 |
| Archive | 1 | archive-old-articles |
| ETF/Supply Chain | 2 | sync-etf, sync-supply-chain |
| Screener | 3 | breadth, heatmap, alerts |
| S&P 500 sync | 3 | constituents, eod-prices, change-percent |
| Chain Sight v1 | 3 | extract-news-relations, enrich-keywords, sync-institutional |
| Chain Sight Regulatory | 2 | scan-regulatory, build-patent |
| Thesis Control | 4 | readings, scores, snapshots, summaries |
| Chain Sight v2 (Tier A) | 11 | profiles, co-mentions, price-co-movement, confidence, stale-decay, aggregate, sync-profiles, sync-relations, heat-score, seed, neo4j-dirty |
| Validation | 1 | weekly-batch |
| SEC Pipeline | 3 | sync-dirty, seed-relations, check-new-filings |
| RAG | 1 | health-check-neo4j |
| Celery 모니터 | 2 | error-digest, cleanup-task-results |
| **합계** | **84 (등록 키 86 중 일부 그룹화 후)** | |

> 등록 키 86개와 위 합계 차이는 동일 태스크의 시간대별 분리 등록 (예: morning/afternoon 분리)으로 인한 것.

---

## 7. 감사 종료

- **읽기 전용**: 본 보고서는 코드/스케줄 어떤 것도 수정하지 않음
- **후속 권장 감사**:
  1. DB `PeriodicTask` ↔ config dict drift 실측 (코드 외 운영 점검)
  2. FMP/Gemini 내부 throttle 코드 경로 감사 (`API_request/`, `news/services/`, `serverless/services/`)
  3. neo4j 큐 워커 컨커런시 실측 (운영 메트릭)
  4. 시장시간 5분 슬롯의 실제 FMP 호출 카운트 (로그/Prometheus 기반)
