# Beat Schedule 감사 보고서

- **날짜**: 2026-04-24
- **대상**: `config/celery.py` (beat_schedule, 라인 117~788)
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (ET, DST 적용) — `config/settings.py:403`
- **Queue 구성**: `default` + `neo4j`(solo pool, 동시 1개)
- **감사 범위**: 전체 60+ 스케줄 항목, Rate Limit / Queue 경합 / 시간대 분포 / 의존 관계

---

## 1. Executive Summary

**결론**: 피크 시간대(12:00, 18:00, 18:30 ET)에서 **FMP Starter 300 req/min 초과 가능성 높음**, **Gemini Free 15 RPM의 반복적 초과**, **neo4j 큐 solo pool의 12:00 동시 몰림 8건** 등 구조적 리스크 3건이 동시에 존재한다.

**최우선 리스크 TOP 5**:

| 순위 | 구간 | 리스크 | 심각도 |
|------|------|--------|--------|
| 1 | **18:00 ET** | `sync-sp500-eod-prices`(500심볼 FMP) + `thesis-update-readings`(FMP) + `collect-market-news-evening`(FMP) 동시 실행 → FMP 300 RPM 초과 | Critical |
| 2 | **12:00 ET 전후** | neo4j 큐에 `chainsight-sync-profiles-neo4j`, `sec-seed-relations-to-chainsight`, `neo4j-health-check`, `sec-sync-dirty-neo4j`(12:00 tick) 4건 동시 도착 + 12:30 / 12:45 후속 → solo pool 직렬화로 최소 20분 밀림 예상 | Critical |
| 3 | **:30 매시 (08, 10, 12, 14, 16, 18)** | `analyze-news-deep-batch` 최대 50건/회 × 6회 = **Gemini 300 req/회분**. 1회 처리에 15 RPM → 최소 3.3분 지속. 병행 `classify-news-batch`(:15, Gemini)와 간격 15분 → **매시 RPM 한계 이월 위험** | High |
| 4 | **18:00 → 18:30** | `run-eod-pipeline`(18:30)은 `sync-sp500-eod-prices`(18:00) 완료 전제. 500 심볼 FMP 배치가 30분 내 끝난다는 **명시적 가드 없음**(chord/depends_on 미사용) | High |
| 5 | **05:30 ET** | `enrich-relationship-keywords` limit=100 → 100건 LLM 호출. Gemini Free 15 RPM 기준 **최소 6.7분 연속 지속**. 재시도 누적 시 RPD 1500 잠식 | Medium |

---

## 2. Rate Limit 초과 구간 분석

### 2.1 FMP Starter 300 calls/min

#### 위험 구간 A: 18:00 ET (EOD 집중 처리)

| 태스크 | 스케줄 | 추정 FMP 호출량 | 출처 |
|--------|--------|-----------------|------|
| `sync-sp500-eod-prices` | 18:00 Mon-Fri | **~500 calls** (심볼별 `/stable/historical-price-eod`) | 라인 538-541 |
| `collect-market-news-evening` | 18:00 Mon-Fri | 일반 시장 뉴스 배치 | 라인 254-258 |
| `thesis-update-readings` | 18:00 Mon-Fri | 지표별 FMP 재무 호출 | 라인 633-637 |
| `update-economic-indicators` | 18:00 Mon-Fri | FRED API (별도 계정, FMP 미사용) | 라인 160-163 |

**판단**: `sync-sp500-eod-prices`가 단독으로도 500/300 = **2분 이상의 rate limit 슬롯을 점유**. `thesis-update-readings`가 같은 1분 window에 FMP를 호출하면 429가 터진다. FMP `/stable/*` 배치 엔드포인트를 쓰지 않는 한 **동시 실행 충돌 확실**.

**권고**: `thesis-update-readings`를 **18:05 또는 18:10**으로 밀거나, `sync-sp500-eod-prices` 완료를 트리거로 하는 `chord`로 묶어야 안전.

#### 위험 구간 B: 17:00~17:45 ET (EOD 뉴스 + 종가 혼재)

| 태스크 | 시각 | 호출 성격 |
|--------|------|----------|
| `update-daily-prices` | 17:00 | FMP 전체 종가 재적용 (FMP provider) |
| `collect-category-news-high-evening` | 17:00 | 카테고리 뉴스 (provider 혼용) |
| `collect-sp500-news-fmp-1715` | 17:15 | FMP S&P 500 뉴스 orchestrator (500 심볼 fan-out) |
| `collect-general-news-fmp-evening` | 17:45 | FMP general news |

**판단**: 17:00 + 17:15 가 15분 간격으로 S&P 500 전체를 훑는 FMP 호출을 연속 트리거. Orchestrator가 내부 sub-task로 throttle 하지 않으면 300 RPM 초과.

#### 위험 구간 C: 09:00~16:00 ET (시장 시간)

| 태스크 | 빈도 | FMP/hour |
|--------|------|----------|
| `update-realtime-prices` | 매 5분 | 12 회/hour |
| `update-market-indices` | 매 5분 | 12 회/hour |
| `refresh-market-pulse-cache` | 매 **1분** | 60 회/hour (외부 API 호출 여부 **확인 필요**) |

**판단**: `refresh-market-pulse-cache`가 캐시 전용이면 무해, 외부 호출 시 **60 req/min 기저 점유**. 정상 상태이면 FMP 여유 있으나, `update-realtime-prices`가 대량 심볼 병렬 fan-out을 하면 300 RPM에 근접.

---

### 2.2 Gemini Free 15 RPM / 1500 RPD

#### 일일 총 LLM 호출 추정

| 태스크 | 시각 (ET) | 호출량 추정 | 주당 RPD |
|--------|-----------|-------------|----------|
| `enrich-relationship-keywords` | 05:30 (매일) | limit=100 → **100 req** | 700 |
| `keyword-generation-pipeline` | 08:00 (매일) | gainers ~5~20 | 35~140 |
| `classify-news-batch` × 6 | :15 (8,10,12,14,16,18) | 배치당 20~50 → 120~300 | 600~1500 |
| `analyze-news-deep-batch` × 6 | :30 (8,10,12,14,16,18) | `max_articles=50` × 6 = **최대 300** | 2100 |
| `sync-news-to-neo4j` × 6 | :45 (8,10,12,14,16,18) | LLM 호출 아님 (DB→Neo4j 전송만) | 0 |
| `extract-daily-news-keywords` | 16:30 (매일) | 일일 뉴스 키워드 배치 | 가변 |
| `extract-news-relations` | 09:00 (매일) | 관계 추출 | 가변 |
| `chainsight-co-mentions` | 10:00 (매일) | 배치 | 가변 |

**일일 추정치**: `analyze-news-deep(300)` + `enrich-relationship-keywords(100)` + `classify-news(120~300)` + 기타(~100) ≈ **620~800 req/day**.

**판단 — RPD**: Free tier **1500 RPD 이내**, 안전 마진 50% 확보. 단, `analyze-news-deep`가 실제 50건을 매번 채우고 재시도가 섞이면 **1000+ 도달 가능**.

**판단 — RPM (훨씬 더 빡빡함)**:
- `analyze-news-deep-batch` 1회가 50건 × 평균 1 LLM req = 50 req → 15 RPM 한계로 **최소 3분 20초 연속 호출** 필요.
- `:15 classify` 완료 후 `:30 analyze` 시작 사이 **간격 15분 — RPM 버킷이 겨우 다 소진되는 속도**. 재시도 1회만 끼어도 초과.
- `05:30 enrich-relationship-keywords(100건)` = 최소 **6분 40초** 연속 호출. 그 사이 `classify-news-batch-morning` 이 **08:15**에 시작하므로 05:30~06:30 구간은 상대적으로 여유 (OK).

**권고**:
1. `analyze-news-deep-batch` `max_articles`를 **30 이하**로 줄이거나, 각 batch 내부에 ≥4초 간격 삽입 (현재 가드 **확인 필요**).
2. `enrich-relationship-keywords` limit=100은 너무 공격적. **25~40**으로 축소 권고.

---

### 2.3 Alpha Vantage 5 calls/min

**Beat schedule 내에서 Alpha Vantage 직접 호출하는 태스크 없음** — 모두 FMP Provider로 통일된 것으로 판단.

**확인 필요**: `stocks.tasks.update_realtime_with_provider`, `stocks.tasks.sync_sp500_eod_prices` 내부 fallback path가 AV로 전환될 수 있는지. 전환 시 `AlphaVantageClient`의 12초 sleep이 EOD 배치를 **500 × 12 = 100분**으로 늘어뜨릴 수 있어 다음 태스크(18:30 EOD pipeline) 침범.

---

## 3. Queue 부하 분석

### 3.1 `neo4j` Queue (solo pool, 동시 1개)

#### Routing 테이블 (라인 37-55)

10건의 태스크가 `neo4j` 큐로 라우팅됨. **solo pool 제약으로 이들은 직렬 실행된다**.

#### neo4j 큐 24시간 타임라인 (평일 기준)

| 시각 ET | 태스크 | expires |
|---------|--------|---------|
| 00:00, 00:05, ... 매 5분 | `sec-sync-dirty-neo4j` (**288회/일**) | 240s |
| 00:00 / 06:00 / 12:00 / 18:00 | `neo4j-health-check` | - |
| 04:00 daily | `cleanup-expired-news-relationships` | 3600s |
| **04:30 Sun** | `chainsight-neo4j-dirty-sync` | 3600s |
| **05:30 daily** | `enrich-relationship-keywords` (100 LLM → 장시간 점유) | 3600s |
| 08:45 / 10:45 / 12:45 / 14:45 / 16:45 / 18:45 Mon-Fri | `sync-news-to-neo4j` | 3600s |
| **12:00 daily** | `chainsight-sync-profiles-neo4j` | 3600s |
| **12:30 daily** | `chainsight-sync-relations-neo4j` | 3600s |

#### Critical 몰림 지점: **12:00 ET**

```
12:00:00  sec-sync-dirty-neo4j          ← 매 5분 tick (점유 ~수초)
12:00:00  neo4j-health-check            ← 6시간 tick
12:00:00  chainsight-sync-profiles-neo4j ← 일일 (heavy: 프로파일 배치 upsert)
12:00:00  sec-seed-relations-to-chainsight ← default 큐이지만 Neo4j DB 접근
12:05:00  sec-sync-dirty-neo4j
12:10:00  sec-sync-dirty-neo4j
12:15:00  sec-sync-dirty-neo4j
12:20:00  sec-sync-dirty-neo4j
12:25:00  sec-sync-dirty-neo4j
12:30:00  chainsight-sync-relations-neo4j ← 일일 (heavy: 관계 엣지 대량 MERGE)
12:30:00  sec-sync-dirty-neo4j
12:45:00  sync-news-to-neo4j             ← max_articles=100 (heavy)
12:45:00  sec-sync-dirty-neo4j
```

**문제**:
- solo pool 1개 워커 가정 시 `chainsight-sync-profiles-neo4j`가 15~30분 소요되면 이 동안 **`sec-sync-dirty-neo4j`(expires=240s)가 줄줄이 만료 폐기**.
- `sec-sync-dirty-neo4j`를 **5분마다 돌리는 것 자체**가 neo4j 큐 혼잡의 주범. dirty flag 기반이면 차라리 이벤트 기반 또는 15분 간격으로 조정.

#### Critical 몰림 지점: **05:30 ET**

`enrich-relationship-keywords` limit=100 → Gemini 15 RPM 기준 **~7분 연속 점유** → 05:30~05:37 동안 neo4j 큐 단독 점유. 이 시간대에 `sec-sync-dirty-neo4j`(05:30, 05:35) 2회 폐기 가능.

#### Critical 몰림 지점: **Sunday 04:00~05:00 ET**

```
04:00  cleanup-expired-news-relationships (neo4j)
04:30  chainsight-neo4j-dirty-sync (neo4j)
04:30  train-lightgbm-model (default, but heavy)
05:00  cleanup-task-results (default)
```

Sunday 새벽 neo4j 큐는 2건만 있지만 `chainsight-neo4j-dirty-sync`가 장시간 돌면 이후 `sec-sync-dirty-neo4j` 연속 폐기.

---

### 3.2 `default` Queue

#### 고빈도 태스크 (시장 시간 09:00~16:00 ET, 평일)

| 태스크 | 빈도 | 시간당 회수 |
|--------|------|-------------|
| `refresh-market-pulse-cache` | 매 1분 | **60** |
| `update-realtime-prices` | 매 5분 | 12 |
| `update-market-indices` | 매 5분 | 12 |
| `calculate-portfolio-values` | 매 10분 | 6 |
| `check-screener-alerts` | 매 15분 | 4 |
| **합계 (기저)** | | **94 tasks/hour** |

**판단**: default queue의 워커 concurrency가 2~4면 평균 처리 가능. 단 `refresh-market-pulse-cache`가 매분 60초 이상 걸리면 큐 적체. 현재 `expires` 설정이 없어 **적체된 백로그가 영원히 남는다** — 1분 이내 실패 감지 시 drop 하도록 `expires=50` 권고.

---

## 4. 시간대별 ASCII 히트맵 (평일 기준)

### 4.1 태스크 빈도 (외부 API + LLM + DB 조회 포함)

```
시  |0                                                                                                   124
----+----------------------------------------------------------------------------------------------------
00  |██                                                 (14)
01  |██                                                 (15) update-economic-calendar
02  |██                                                 (14)
03  |██                                                 (14)
04  |██                                                 (15) cleanup-expired-news-relationships
05  |██                                                 (15) enrich-relationship-keywords ⚠
06  |███                                                (20) 뉴스 수집 집중 시작
07  |███                                                (20) movers + press + category
08  |███                                                (19) keyword + market news + LLM 시작
09  |█████████████████████████████████████████          (110) 시장 개장 — 5/10/15분 tick
10  |█████████████████████████████████████████          (112) + co-mentions + LLM
11  |█████████████████████████████████████████          (109) + relation-confidence
12  |█████████████████████████████████████████████      (120) 🔴 FMP+Neo4j+Gemini 동시 피크
13  |█████████████████████████████████████████          (111) + seed-selection
14  |██████████████████████████████████████████████     (124) 🔴 피크 (LLM + 뉴스 수집)
15  |█████████████████████████████████████████          (110)
16  |█████████████████████████████████████████          (112) 🔴 keyword + breadth + heatmap
17  |███                                                (18) EOD FMP 개시
18  |████                                               (26) 🔴🔴 SP500 EOD + thesis + pipeline
19  |██                                                 (16) ML labels + backfill
20  |██                                                 (15) sync-sp500-financials
21  |██                                                 (14)
22  |██                                                 (15) update-economic-indicators
23  |██                                                 (14)
```

(괄호 안은 시간당 총 fire 이벤트 수, 매 분 fire 되는 `refresh-market-pulse-cache`와 `sec-sync-dirty-neo4j`(매 5분) 포함)

### 4.2 외부 API 호출 부하 히트맵 (FMP + Gemini 가중)

```
시  |Low          Med          High         VeryHigh    Peak
----+------------------------------------------------------
00  |░░                                                 (1)
01  |░░                                                 (1)
02  |░                                                  (0)
03  |░                                                  (0)
04  |░░                                                 (1)  neo4j cleanup
05  |████                                               (3)  Gemini enrich (100)  ⚠
06  |██████████                                         (5)  FMP news×3 + FRED
07  |██████████████                                     (7)  FMP movers + press + category
08  |████████████████                                   (8)  FMP news + Gemini classify + analyze
09  |██████████████████                                 (10) 시장 개장 FMP ×30/hour
10  |████████████████████                               (11) FMP + Gemini (classify+analyze)
11  |██████████████                                     (7)  FMP 기저
12  |██████████████████████████                         (13) 🔴 FMP + FRED + Gemini + Neo4j
13  |██████████████████                                 (9)  FMP + sp500-news 1315
14  |██████████████████████                             (11) 🔴 Gemini + 뉴스 대량
15  |██████████████████                                 (9)  FMP + sp500-news 1515
16  |████████████████████                               (11) 🔴 Gemini keywords + breadth
17  |████████████████████                               (10) FMP EOD 개시 + sp500-news 1715
18  |██████████████████████████████████                 (17) 🔴🔴🔴 SP500 EOD+FRED+thesis+news+pipeline
19  |████████                                           (4)  ML labels
20  |████████████                                       (6)  SP500 financials 101심볼
21  |░                                                  (0)
22  |████                                               (2)  FRED
23  |░                                                  (0)
```

(가중치: FMP 호출 1 = 1, Gemini 호출 1 = 1.5, FRED/내부 = 0.3)

### 4.3 neo4j Queue 점유 히트맵 (solo pool, 동시 1건)

```
시  |평일
----+-------------------------------------------------------
00  |████ (sec-sync 12회)
01  |████ (sec-sync 12회)
02  |████
03  |████
04  |██████ (cleanup-expired-news + sec-sync)
05  |██████████████ (enrich-relationship-keywords 7분 점유 ⚠)
06  |██████ (health-check 06:00 + sec-sync)
07  |████
08  |████████ (sync-news-to-neo4j + sec-sync)
09  |████ (sec-sync)
10  |████████ (sync-news-to-neo4j + sec-sync)
11  |████
12  |██████████████████ (🔴 chainsight-profiles + sync-relations + health-check + sync-news + sec-sync)
13  |████
14  |████████
15  |████
16  |████████
17  |████
18  |██████████ (health-check + sync-news + sec-sync)
19  |████
20  |████
21  |████
22  |████
23  |████
```

**최대 부하 지점**: **12:00~12:59 (neo4j solo pool 경쟁 6건 + sec-sync 12회)**

---

## 5. 스케줄 겹침 / 선후 의존성 분석

### 5.1 확인된 의존 체인 (암묵적 순서 의존)

| 선행 | 후속 | 간격 | 위험도 |
|------|------|------|--------|
| `sync-daily-market-movers` (07:30) | `keyword-generation-pipeline` (08:00) | 30분 | OK |
| `sync-sp500-eod-prices` (18:00) | `run-eod-pipeline` (18:30) | **30분** | ⚠ 500 심볼 FMP가 30분에 못 끝날 가능성 (300 RPM × 30min = 9000 이론치지만, 병행 부하로 실제 3~5배 느려짐) |
| `run-eod-pipeline` (18:30) | `backfill-signal-accuracy` (19:00) | 30분 | ⚠ 의존성 불확실 — 파이프라인 완료 가드 없음 |
| `thesis-update-readings` (18:00) | `thesis-calculate-scores` (18:15) | **15분** | ⚠ 지표 수집이 15분 내 끝난다는 보장 없음 |
| `thesis-calculate-scores` (18:15) | `thesis-create-snapshots` (18:30) | 15분 | ⚠ 상동 |
| `classify-news-batch` (:15) | `analyze-news-deep-batch` (:30) | 15분 | ⚠ 50건 분류가 15분 내 완료되어야 다음 단계 시작 |
| `analyze-news-deep-batch` (:30) | `sync-news-to-neo4j` (:45) | 15분 | ⚠ 상동, 추가로 neo4j 큐 경합 |
| `chainsight-co-mentions` (10:00) | `chainsight-relation-confidence` (11:00) | 60분 | OK |
| `chainsight-all-profiles` (Sat 02:00) | `chainsight-price-co-movement` (Sat 03:00) | 60분 | OK |
| `train-importance-model` (Sun 03:00) | `generate-shadow-report` (Sun 03:30) | 30분 | ⚠ 모델 학습이 30분 내 끝난다는 보장 없음 |
| `generate-shadow-report` (Sun 03:30) | `check-auto-deploy` (Sun 04:00) | 30분 | ⚠ 상동 |
| `collect-*-news` (06:00~) | `classify-news-batch` (08:15) | 2h+ | OK (버퍼 충분) |

**공통 문제**: **모든 의존 체인이 `crontab` 간격으로 암묵적 순서를 가정한다**. 선행 실패/지연 시 후속은 **불완전 데이터로 실행**. `chord` / `chain` / `signature.link()`로 명시적 묶음 처리 권고.

### 5.2 동시 시작 충돌

#### 18:00 ET (5건 동시)

- `update-economic-indicators` (FRED)
- `collect-market-news-evening` (provider 혼용)
- `sync-sp500-eod-prices` (FMP heavy)
- `thesis-update-readings` (FMP/DB)
- `neo4j-health-check` (neo4j)

→ **FMP RPM 초과 위험**, neo4j 큐 여유 (단건), default 큐 다건 병렬.

#### 18:30 ET (4건 동시)

- `analyze-news-deep-batch` (Gemini, 최대 50)
- `run-eod-pipeline` (LLM 포함된 뉴스 매핑 5단계)
- `thesis-create-snapshots` (DB)
- `update-sp500-change-percent` (DB)

→ **Gemini 15 RPM 초과 확실**. `analyze-news-deep` + `run-eod-pipeline`이 같은 LLM 자원을 두고 경쟁.

#### 04:00~04:30 Sunday (5건 동시/근접)

- 04:00 `cleanup-expired-news-relationships` (neo4j)
- 04:00 `check-auto-deploy` (default)
- 04:15 `generate-weekly-ml-report` (default)
- 04:20 `monitor-ml-performance` (default)
- 04:30 `train-lightgbm-model` (default, CPU/메모리 heavy)
- 04:30 `chainsight-neo4j-dirty-sync` (neo4j)

→ default 큐에 heavy 학습 작업이 연속 5건. 워커 CPU/메모리 경합 가능성.

#### Saturday 02:00~05:00 Chain Sight 배치

- 02:00 `chainsight-all-profiles` (heavy)
- 03:00 `chainsight-price-co-movement` (heavy, 상관계수 계산)
- 04:00 `chainsight-stale-decay`
- 04:30 `chainsight-aggregate-profiles`
- 05:00 `validation-weekly-batch`

→ 1시간 간격 확보됨. 단 `chainsight-all-profiles`가 1시간 안에 끝난다는 **명시 가드 없음**. 길어지면 `price-co-movement`가 아직 미완성 profile을 참조.

---

## 6. 타임존 / 주말 실행 이슈

| 태스크 | 문제 |
|--------|------|
| `extract-daily-news-keywords` | `crontab(hour=16, minute=30)` — **day_of_week 미지정**. 주말에도 실행되어 빈 뉴스셋에 Gemini 호출 낭비 |
| `chainsight-co-mentions` | 상동, 주말 실행됨 |
| `chainsight-relation-confidence` | 상동 |
| `chainsight-sync-profiles-neo4j` | 상동 |
| `chainsight-sync-relations-neo4j` | 상동 |
| `chainsight-heat-score-daily` | `crontab(hour=7, minute=0)` — 주석은 "UTC"지만 `CELERY_TIMEZONE=America/New_York` → **실제로는 07:00 ET = 12:00 UTC**. 주석과 실제 동작 불일치 |
| `chainsight-seed-selection` | 상동 (13:00 ET = 18:00 UTC, 주석은 UTC 주장) |
| `chainsight-neo4j-dirty-sync` | 상동 (04:30 Sun ET = 09:30 Sun UTC, 주석 UTC 주장) |

**권고**: `chainsight-*` 3건의 주석/스케줄 타임존을 일치시키거나, `schedule.utc` 명시.

---

## 7. 만료(expires) 설정 누락

`expires` 미설정 태스크 → Redis broker 적체 시 오래된 job이 영원히 대기:

- `update-realtime-prices` (매 5분)
- `calculate-portfolio-values` (매 10분)
- `update-economic-indicators` (4회/일)
- `update-market-indices` (매 5분)
- `update-economic-calendar` (매일 01:00)
- `refresh-market-pulse-cache` (매 분) — **특히 위험**: 1분 주기인데 만료 없음
- `cleanup-old-macro-data` (Sun)
- `neo4j-health-check`
- `celery-error-digest`
- `cleanup-task-results`

**권고**: 반복 주기보다 짧은 `expires` 필수 (예: 매 분 태스크 → `expires=50`).

---

## 8. 개선 권고 요약

### P0 (즉시)

1. **18:00 ET FMP 충돌 해소**: `thesis-update-readings`를 18:05 또는 18:10으로 이동. `sync-sp500-eod-prices`와 `chord`로 묶는 것이 근본책.
2. **neo4j 큐 12:00 ET 몰림 분산**: `chainsight-sync-profiles-neo4j`를 11:30으로, `chainsight-sync-relations-neo4j`를 13:00으로 이동. `neo4j-health-check`는 `hour='1,7,13,19'` 등으로 피크 회피.
3. **`sec-sync-dirty-neo4j` 주기 완화**: 5분 → **15분**으로. expires=240 → 900. dirty flag 누적량이 많지 않으면 이벤트 트리거 고려.
4. **`analyze-news-deep-batch` max_articles**: 50 → **25**. 15 RPM × 15분 = 이론 225 req 마진 확보.

### P1 (1주일 내)

5. **`enrich-relationship-keywords` limit**: 100 → 40.
6. **의존 체인 명시화**: Thesis EOD 3단계, News 분류→분석→동기화 3단계를 `chain()`으로 묶기.
7. **주말 실행 게이팅**: 5개 chainsight 태스크에 `day_of_week='1-5'` 추가 (또는 태스크 내 guard).
8. **`expires` 일괄 설정**: 10개 태스크에 기본값 추가.

### P2 (리팩토링)

9. **FMP 호출 중앙 throttle**: `fmp_rate_limiter` 데코레이터를 모든 FMP 호출 태스크에 강제 적용 (현재 분산된 것으로 추정 — **확인 필요**).
10. **Beat schedule 섹션 분리**: 800줄 단일 dict를 `config/beat_schedules/{stocks,news,chainsight,sec}.py`로 분할하면 동시 실행 파악이 쉬워진다.

---

## 9. 확인 필요 항목 (본 감사에서 미확정)

- `refresh-market-pulse-cache`가 외부 API 호출하는지 또는 캐시 전용인지
- `update-realtime-with-provider`가 실제 1분당 몇 건의 FMP 호출을 내는지
- `run-eod-pipeline` 내부의 LLM 호출 빈도
- FMP `/stable/*` 배치 엔드포인트 사용 여부 (500 심볼을 한 번에 vs. 500회 순차)
- `sec-sync-dirty-neo4j`의 평균 dirty 레코드 건수
- `analyze-news-deep-batch`의 1건당 LLM 호출 수 (1 vs. 여러)

---

_감사자: Beat Schedule Auditor (read-only)_
_대상 파일: `config/celery.py`, `config/settings.py`_
_관련 문서: `docs/architecture/beat_schedule_audit_20260421.md` (이전 버전, 현재 경로에서 삭제됨)_
