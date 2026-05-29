# Celery Beat 스케줄 감사 보고서

- **작성일**: 2026-05-29
- **대상**: `config/celery.py` `beat_schedule` + 실제 런타임 소스 `django_celery_beat.PeriodicTask` (DB)
- **모드**: 읽기 전용 감사 (코드 미수정)
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (DB 104건) + `Asia/Seoul` (DB 5건) — **혼합 타임존**
- **워커 풀**: macOS = `solo`(단일 프로세스), 프로덕션 Linux = `prefork`(다중) — 환경별로 결론이 달라짐

---

## 0. 가장 중요한 전제 — 감사 대상(dict) ≠ 실제 실행(DB)

`config/settings.py`의 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 때문에
**`config/celery.py`의 `beat_schedule` dict은 런타임에 무시됩니다.** 진실의 소스는 DB `PeriodicTask` 테이블입니다.
(이 사실은 `config/celery.py` 117~134행 주석에도 명시됨.)

| 구분 | 개수 |
|------|------|
| `config/celery.py` dict 선언 태스크 | **79** |
| DB `PeriodicTask` 실제 등록 (전부 `enabled=True`) | **109** |
| dict에만 있고 DB에 없음 (= 미실행) | 0 ✅ |
| **DB에만 있고 dict에 없음 (= dict 감사로는 안 보이는 실행 태스크)** | **🔴 23** |

> **결론: `config/celery.py` dict 분석만으로는 실제 부하의 약 72%만 보입니다.** 아래 분석은 DB(진실의 소스)를 기준으로 수행했으며, dict 기준 분석과의 괴리를 별도 표기합니다.

### dict 밖에서 실행 중인 23개 태스크

| 그룹 | 태스크 | 비고 |
|------|--------|------|
| **marketpulse 앱 (dict에 전무)** | `mp_calc_breadth_5min`, `mp_calc_sector_5min`, `mp_calc_regime_15min`, `mp_detect_anomaly_5min`, `mp_calc_concentration_daily`, `mp_fetch_news_hourly`, `mp_sync_yahoo_indicators_daily`, `mp_finalize_daily`, `mp_generate_brief_daily`, `mp_purge_news_daily`, `mp_purge_news_view_log_daily` (11개) | 별도 `marketpulse.tasks.*` 앱. `macro`의 Market Pulse와 **다른 시스템**. 장중 5분/15분 주기로 무시 못할 부하 (`mp_calc_breadth_5min` total_run=2021) |
| **"제거됨" 주석과 모순** | `cleanup-expired-semantic-cache`, `warm-semantic-cache`, `semantic-cache-stats` (3개) | `config/celery.py` 217~218행은 "제거됨(미초기화)"이라고 적혀 있으나 **DB에서 enabled 상태로 neo4j 큐에서 실행 중**. 주석이 현실과 불일치 |
| **🔴 중복 실행 (레거시 잔재)** | `collect-daily-news`, `collect-category-news-medium` (2개) | 접미사 없는 구버전. 접미사 버전(`-morning`)과 **동일 함수·동일 시각** 중복 실행 (§5.1 참조) |
| 야간 자동화 (KST) | `agent-report-data/backend/qa/design-*am-kst`, `metrics-daily-report-7am-kst` (5개) | `Asia/Seoul` 타임존. NY 17:00~18:00에 떨어짐 (§4 참조) |
| 기타 | `chainsight-seed-snapshot-cleanup`(일 13:30), `celery.backend_cleanup`(Celery 내장, 4:00) | |

---

## 1. Rate Limit 초과 구간 분석

### 1.1 FMP (Starter: 300 calls/min, 10,000/day)

**핵심 위험: `collect-sp500-news-fmp-*` 오케스트레이터의 배치 버스트**

- 스케줄: NY **06:15, 10:15, 13:15, 15:15, 17:15** (평일, 1일 5회)
- 동작: `collect_sp500_news_fmp_orchestrator` → S&P500 503종목을 **84개씩 6배치**로 분할, `group`으로 동시 디스패치
- 각 배치(`collect_sp500_news_fmp_batch`)는 84종목을 순차 루프로 FMP 호출 → **최대 504 calls**
- ⚠️ 배치 태스크의 `rate_limit='100/m'`은 **태스크 인스턴스 수(6개)**를 제한할 뿐, 배치 *내부* 종목별 호출(84개)을 제어하지 못함

| 환경 | 결과 |
|------|------|
| macOS `solo` 풀 | 배치가 **순차 실행** → 504 calls가 시간에 분산 → 한도 내 (느릴 뿐) |
| 프로덕션 `prefork` (동시성 C) | C개 배치 병렬 → **분당 300 calls 초과 가능** 🔴 |

- **악화 구간**: 10:15 / 13:15 / 15:15 는 장중(09–16)이라 `update-realtime-prices`(~10종목)·`update-market-indices`가 `*/5`로 동시 발사. 오케스트레이터(504) + 장중 FMP가 **같은 분에 겹침**.

**안전 확인된 FMP 태스크 (self-throttle 내장):**
- `sync-sp500-eod-prices` (18:00): `SP500EODService`가 종목당 `time.sleep(REQUEST_DELAY=0.3)` → 503 × 0.3s ≈ **2.5분, 실효 ~200 calls/min < 300** ✅
- `sync-sp500-financials` (20:00): 101종목/일 순환 배치, 단독 시간대 ✅

**오해 소지 명칭:**
- `update-daily-prices` (17:00) = `update_realtime_with_provider`를 **인자 없이** 호출 → 포트폴리오 상위 10종목만 갱신. **S&P500 일일 종가가 아님** (실제 EOD는 `sync-sp500-eod-prices`).

### 1.2 Gemini Free (15 RPM, 1500 RPD)

**스케줄된 Gemini 태스크 목록 (NY 시각):**

| 태스크 | 시각 | 호출 규모(추정) | self-throttle |
|--------|------|----------------|---------------|
| `enrich-relationship-keywords` | 05:30 매일 | limit=100 → 최대 100 calls | neo4j 큐 |
| `keyword-generation-pipeline` | 08:00 매일 | gainers 키워드 | — |
| `extract-news-relations` | 09:00 매일 | 24h 뉴스 관계 | — |
| `chainsight-co-mentions` | 10:00 매일 | 7일 co-mention | — |
| `analyze-news-deep-batch` | **08/10/12/14/16/18 :30** 평일 (6회) | 최대 50건 × 6 = **300 calls** | ✅ 4초 간격 = 15 RPM |
| `extract-daily-news-keywords` | 16:45 매일 | 일일 키워드 | — |
| `thesis-generate-summaries` | 18:35 평일 | 가설 요약 | — |
| `refresh-korean-overviews-monthly` | 매월 1일 03:00 | S&P500 개요 | — |

> 참고: `classify-news-batch`(:15)는 LLM이 아니라 **규칙 엔진**(`internal`)임을 코드로 확인. Gemini 미사용.

- **RPM 위험 (분당 15)**: `analyze-news-deep`는 단독으로도 4초 간격 = **15 RPM을 풀로 점유**. 따라서 :30 윈도와 **겹치는 다른 Gemini 태스크가 있으면 즉시 15 RPM 2배 초과 → 429**.
  - ✅ **이미 방어된 사례**: `extract-daily-news-keywords`를 16:30 → **16:45**로 이동 (16:30 `analyze-deep`와 15분 분리). 코드 284~291행 주석에 audit P0 #8로 기록됨.
  - ⚠️ 18:30 `analyze-deep` ↔ 18:35 `thesis-generate-summaries`: 5분 간격. `analyze-deep`(50건 × 4s ≈ 3.3분, ~18:33 종료) 직후라 **여유가 5분 미만**. 배치 지연 시 충돌 가능 — 모니터링 권장.
- **RPD 위험 (일 1500)**: `analyze-deep`(~300) + `enrich`(~100) + `co-mentions` + `keyword-pipeline` + `extract-relations` + `extract-keywords` + `thesis-summaries`. 활황일 합산 시 **1500 RPD 근접/초과 가능** → 일일 한도 모니터링 필요.

### 1.3 Alpha Vantage (5 calls/min)

- **스케줄 의존성 없음** ✅ — `grep` 결과 AV는 `news/models.py`·마이그레이션에만 등장, **beat 태스크 중 AV를 호출하는 것 없음**. AV 5/min 한도는 beat 스케줄과 무관.

---

## 2. Queue 몰림 분석 (default vs neo4j)

### 2.1 neo4j 큐 (solo pool, 동시성 1)

`task_routes`로 neo4j 큐에 격리되는 태스크 (동시 1개만 처리):

| 태스크 | 주기 | 비고 |
|--------|------|------|
| `sec-sync-dirty-neo4j` | **`*/5` 24시간** (288회/일, total_run=**12626**) | expires=240s(4분). 가장 빈번 |
| `neo4j-health-check` | `*/6` (0/6/12/18:00) | |
| `semantic-cache-stats` | `*/6` (0/6/12/18:00) | "제거됨" 주석과 모순, 실제 실행 |
| `sync-news-to-neo4j` | 08/10/12/14/16/18 **:45** 평일 | max_articles=100 |
| `chainsight-sync-profiles-neo4j` | 매일 **12:00** | |
| `chainsight-sync-relations-neo4j` | 매일 **12:30** | |
| `cleanup-expired-news-relationships` | 매일 04:00 | |
| `cleanup-expired-semantic-cache` | 매일 04:00 | "제거됨" 주석 모순 |
| `warm-semantic-cache` | 일요일 04:30 | |
| `chainsight-neo4j-dirty-sync` | 일요일 04:30 | |
| `enrich-relationship-keywords` | 매일 **05:30** | 🔴 **Gemini(최대 100 calls)를 neo4j 큐에서 실행** |

**🔴 위험 1 — 정시 경계 충돌 (0/6/12/18:00):**
이 시각에 `neo4j-health-check` + `semantic-cache-stats` + `sec-sync-dirty-neo4j`(정시도 `*/5`에 포함)가 **동시 도착**. solo 풀이라 직렬 처리 → `sec-sync-dirty`가 밀림.
- **12:00은 최악**: 위 3개 + `chainsight-sync-profiles-neo4j`(12:00) = neo4j 큐에 4개 동시 도착. 12:30엔 `chainsight-sync-relations-neo4j` + `sec-sync-dirty` + `sync-news-to-neo4j`(전 시간 :45 잔여 가능).
- `sec-sync-dirty-neo4j`의 `expires=240s`가 큐 적체 시 **만료(skip)** → 동기화 누락 가능.

**🔴 위험 2 — 05:30 Gemini가 neo4j 큐 점유:**
`enrich-relationship-keywords`가 최대 100 calls의 Gemini 작업을 **neo4j solo 큐**에서 수행 → 수 분간 큐 독점 → 그동안 `sec-sync-dirty-neo4j`(5분 주기) 적체. neo4j 격리 큐에 LLM 태스크를 얹은 **아키텍처 스멜**.

### 2.2 default 큐

- 장중(09–16) **분당 단위 고빈도** 태스크가 집중 (§3 fire-rate 표 참조).
- macOS `solo`에서는 default 큐도 **단일 프로세스 직렬** → 장중 `refresh-market-pulse-cache`(분당 1회) 등이 다른 무거운 태스크 뒤에 밀릴 수 있음.
- 프로덕션 `prefork`에서는 동시 처리되나, §1.1 FMP 버스트가 default 큐에서 발생.

---

## 3. 시간대별 API 호출 히트맵 (NY 시각, 평일 기준)

### 3.1 시간대별 **고유 태스크 수** (월말/주말 제외)

```
NY시  태스크수  히트맵 (■ = 1 task)                          비고
00 │  6 │ ■■■■■■                                       야간 baseline + */6 neo4j
01 │  5 │ ■■■■■                                        economic-calendar
02 │  4 │ ■■■■                                         baseline
03 │  4 │ ■■■■                                         baseline (주말/월초 배치多)
04 │  7 │ ■■■■■■■                                      cleanup 3종 (neo4j 2)
05 │  5 │ ■■■■■                                        🔴 enrich Gemini@neo4j
06 │ 12 │ ■■■■■■■■■■■■                                 뉴스수집 5종 + 중복1 + econ
07 │ 11 │ ■■■■■■■■■■■                                  movers + 카테고리뉴스 + 중복1
08 │  9 │ ■■■■■■■■■                                    Gemini 파이프라인 시작
09 │ 14 │ ■■■■■■■■■■■■■■                ◀ 장중 시작     intraday(8) + Gemini relations
10 │ 17 │ ■■■■■■■■■■■■■■■■■                            🔴 FMP orchestrator + Gemini deep
11 │ 13 │ ■■■■■■■■■■■■■                                relation-confidence
12 │ 23 │ ■■■■■■■■■■■■■■■■■■■■■■■  ◀◀ 최다 고유태스크   🔴 neo4j 4중 + econ + 뉴스 + Gemini
13 │ 15 │ ■■■■■■■■■■■■■■■                              seed-selection + FMP orchestrator
14 │ 19 │ ■■■■■■■■■■■■■■■■■■■                           뉴스수집 + Gemini deep + mp_purge
15 │ 14 │ ■■■■■■■■■■■■■■                               FMP orchestrator
16 │ 19 │ ■■■■■■■■■■■■■■■■■■■   ◀ 장마감              breadth/heatmap + Gemini deep×2
17 │ 15 │ ■■■■■■■■■■■■■■■                              FMP orch + KST리포트4 + mp
18 │ 19 │ ■■■■■■■■■■■■■■■■■■■  ◀◀ 헤비태스크 피크      🔴 thesis4+eod3+Gemini2+econ+KST
19 │  6 │ ■■■■■■                                       ml-labels + backfill
20 │  5 │ ■■■■■                                        sp500-financials(FMP)
21 │  4 │ ■■■■                                         baseline
22 │  5 │ ■■■■■                                        econ-indicators
23 │  4 │ ■■■■                                         baseline
```

> **피크 해석**
> - **12:00 (23개)**: *고유 태스크 수* 최다. neo4j 큐 4중 충돌 + Gemini deep + 거시지표 + 뉴스. 경합 위험 1순위.
> - **18:00 (19개)**: *무게* 최대 피크. thesis 체인 4 + EOD 파이프라인 3 + Gemini 2 + 거시지표 + FMP 503종목 EOD + KST 리포트. 의존성·경합 위험 1순위 (§5).
> - **14/16시 (각 19개)**: 뉴스 수집·분석 + Gemini deep 집중.

### 3.2 장중(09–16) 실제 **발사 횟수**/시간 — 고유 태스크 수에 안 잡히는 숨은 부하

| 태스크 | 주기 | 시간당 발사 | API |
|--------|------|-----------|-----|
| `refresh-market-pulse-cache` | `*` | **60** | (검증 필요) |
| `update-realtime-prices` | `*/5` | 12 | FMP(~10종목) |
| `update-market-indices` | `*/5` | 12 | FMP |
| `mp_detect_anomaly_5min` | `*/5` | 12 | 내부 |
| `mp_calc_sector_5min` | `*/5` | 12 | 내부 |
| `mp_calc_breadth_5min` | `*/5` | 12 | 내부 |
| `calculate-portfolio-values` | `*/10` | 6 | 내부 |
| `check-screener-alerts` | `*/15` | 4 | 내부 |
| `mp_calc_regime_15min` | `*/15` | 4 | 내부 |
| `sec-sync-dirty-neo4j` | `*/5` | 12 | neo4j |
| `check-pipeline-alerts` | `*/30` | 2 | 내부 |
| `mp_fetch_news_hourly` | `m=5` | 1 | 뉴스 |
| **합계** | | **≈ 149회/시간** | |

> **장중 ≈ 150 발사/시간 vs 장외 ≈ 19 발사/시간.** 고유 태스크 수 히트맵(§3.1)은 이 분당 반복 부하를 1로만 세므로, 실제 처리량 피크는 **장중 09–16 전 구간**임. macOS solo 풀에서는 이 150회가 단일 프로세스에서 직렬 처리됨에 유의.

---

## 4. 혼합 타임존 주의 (Asia/Seoul 5건)

DB의 5개 태스크는 `Asia/Seoul` 타임존으로 등록됨. KST는 **EDT 대비 +13h(여름)/EST 대비 +14h(겨울)**.

| 태스크 (KST) | KST 시각 | **NY 환산 (현재 EDT)** |
|--------------|---------|----------------------|
| `agent-report-data-6am-kst` | 06:00 | **NY 17:00** |
| `agent-report-backend-615am-kst` | 06:15 | **NY 17:15** |
| `agent-report-qa-630am-kst` | 06:30 | **NY 17:30** |
| `agent-report-design-645am-kst` | 06:45 | **NY 17:45** |
| `metrics-daily-report-7am-kst` | 07:00 | **NY 18:00** |

- 이 5개가 **이미 헤비한 NY 17:00~18:00 마감 클러스터에 추가로 적재**됨 (last_run 21:00~22:00 UTC로 확인).
- ⚠️ **DST 전환 시 1시간 이동**: 겨울(EST)엔 +14h → NY 16:00~17:00로 시프트. 시즌마다 마감 클러스터 위치가 바뀜.

---

## 5. 스케줄 겹침 / 의존성 위험

### 5.1 🔴 [P0] 확정된 중복 실행 (동일 함수 2회)

DB 증거 (last_run·total_run):

| 중복쌍 | 함수 | 시각 | last_run (2026-05-29) |
|--------|------|------|----------------------|
| `collect-daily-news` (run=66) ↔ `collect-daily-news-morning` (run=57) | `news.tasks.collect_daily_news` | NY 06:00 | 10:00:00.123 vs **10:00:00.187** (64ms 차) |
| `collect-category-news-medium` (run=66) ↔ `collect-category-news-medium-morning` (run=57) | `news.tasks.collect_category_news` | NY 07:00 | 11:00:00.148 vs 11:00:00.159 |

- 접미사 없는 구버전(`collect-daily-news`, `collect-category-news-medium`)이 morning/afternoon 분할 리팩터 **이전의 레거시 잔재**로 추정. 같은 함수를 같은 시각에 **2번** 실행 중.
- 영향: 뉴스 수집 API 2배 호출 + 후속 분류/Gemini 분석 부하 2배. (`-morning` 쪽 run=57 < 구버전 66 → 구버전이 먼저 등록되어 더 오래 실행됨)
- **권고(코드 외)**: Django admin에서 레거시 2건(`collect-daily-news`, `collect-category-news-medium`) **disable**. dict에는 이미 분할 버전만 존재하므로 dict 재반영 시 자동 정리됨.

### 5.2 🔴 [P1] 18:30 삼중 동시 + 선행 미보장

| 시각 | 동시 태스크 | 의존 관계 위험 |
|------|-------------|---------------|
| 18:00 | `thesis-update-readings` **와** `sync-sp500-eod-prices` 동시 시작 | thesis 지표 수집이 EOD 가격에 의존한다면, EOD sync(~2.5분 소요)가 **아직 안 끝난 시점에 stale 가격** 읽을 위험 |
| 18:30 | `run-eod-pipeline` + `update-sp500-change-percent` + `thesis-create-snapshots` **동시** | `run-eod-pipeline`이 `Stock.change_percent`를 읽기 전에 `update-sp500-change-percent`가 쓴다는 **순서 보장 없음**(같은 분). read-before-write 경합 가능 |

- 현재는 **시각 간격(분 단위 오프셋)에만 의존**하는 암묵적 순서. 선행 태스크 완료를 신호로 트리거하는 체이닝(`chain`/`chord`)이 아님 → 처리 지연 시 순서 역전 가능.
- `thesis-*` 체인(18:00→18:15→18:30→18:35)은 15분 간격으로 비교적 안전하나, 18:30에 EOD 파이프라인과 큐를 공유하면 지연 전파 가능.

### 5.3 ✅ 이미 방어된 겹침

- `extract-daily-news-keywords` 16:30→16:45 이동으로 `analyze-news-deep`(16:30)와 Gemini 충돌 회피 (코드 주석 audit P0 #8).
- `keyword-generation-pipeline`(08:00)은 `sync-daily-market-movers`(07:30) 30분 후 — 선행 완료 여유 확보.

---

## 6. 종합 우선순위 권고 (모두 코드 외 조치 — 본 감사는 읽기 전용)

| 우선 | 항목 | 조치 |
|------|------|------|
| **P0** | 중복 뉴스 수집 2건 (§5.1) | admin에서 `collect-daily-news`·`collect-category-news-medium` disable |
| **P0** | dict↔DB drift 79↔109 (§0) | `config/celery.py` dict를 DB 실제 상태로 동기화(특히 marketpulse 11종·KST 5종·semantic-cache 3종 반영) 또는 "dict은 reference일 뿐" 명시 강화 |
| **P0** | "제거됨" 주석 모순 (§0, §2.1) | semantic-cache 3종을 실제로 폐기하거나, 살아있음을 주석에 정정 |
| **P1** | FMP orchestrator 버스트 (§1.1) | 프로덕션 prefork에서 배치 *내부* 종목 루프에 호출 간격(throttle) 추가 검토. 10:15/13:15/15:15 장중 겹침 분리 |
| **P1** | neo4j solo 큐 정시 경합 (§2.1) | 12:00 집중 태스크 분산(±5분), `enrich`(Gemini)를 neo4j 큐에서 분리 검토 |
| **P1** | 18:30 read-before-write 경합 (§5.2) | 시각 오프셋 의존 → Celery `chain`/`chord` 명시적 체이닝 전환 검토 |
| **P2** | Gemini RPD 1500 근접 (§1.2) | 일일 호출 합산 모니터링, `enrich` limit·`analyze` max_articles 상한 점검 |
| **P2** | KST 리포트 DST 이동 (§4) | 마감 클러스터(NY 17–18시) 적재 인지, 계절별 위치 변동 모니터링 |
| Info | AV 무의존 (§1.3) / EOD self-throttle 안전 (§1.1) / `update-daily-prices` 명칭 오해 | 변경 불필요, 인지만 |

---

## 부록 A. 검증에 사용한 사실(코드/DB 근거)

- 타임존: `config/settings.py:488 CELERY_TIMEZONE='America/New_York'`, DB CrontabSchedule.timezone 분포 = NY 104 / Seoul 5
- DB 카운트: `PeriodicTask` 109 enabled / 0 disabled
- `update_realtime_with_provider`: 인자 없을 때 `Portfolio … [:10]` → 10종목만 (stocks/tasks.py:343~)
- `collect_sp500_news_fmp_orchestrator`: 503종목 → 84×6 배치 group 디스패치 (news/tasks.py:952~)
- `collect_sp500_news_fmp_batch`: `rate_limit='100/m'`(태스크 인스턴스 한정) + 종목 순차 루프
- `SP500EODService.sync_eod_prices`: 종목별 `time.sleep(REQUEST_DELAY=0.3)` (stocks/services/sp500_eod_service.py:23,91,133)
- `classify_news_batch`: 규칙 엔진(`_log_collection('classify_news_batch','internal',...)`) — Gemini 미사용 (news/tasks.py:469~)
- `analyze_news_deep`: Gemini, 4초 간격 RPM 준수 명시 (news/tasks.py:511~)
- 중복 확정: `collect-daily-news`/`collect-daily-news-morning` 둘 다 `news.tasks.collect_daily_news`, last_run 64ms 차

## 부록 B. 한계

- 본 감사는 **스케줄(시각·주기·큐) 정합성** 중심이며, 각 태스크 *내부*의 실제 외부 API 호출 건수는 코드 정적 분석으로 추정함(런타임 계측 아님).
- `refresh-market-pulse-cache`(분당)·`mp_*`·`mp_fetch_news_hourly`의 외부 API 의존 여부는 추가 코드 검증 권장.
- 월말/월초(dom=1/15/16)·주말(dow=0/6) 전용 배치는 히트맵(평일 기준)에서 제외함.
