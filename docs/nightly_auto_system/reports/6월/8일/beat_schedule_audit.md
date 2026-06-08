# Celery Beat 스케줄 감사 보고서

- **생성일**: 2026-06-08
- **대상**: `config/celery.py` `app.conf.beat_schedule` + 실제 DB(`django_celery_beat.PeriodicTask`)
- **모드**: 읽기 전용 (코드 수정 없음)
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (NYSE 기준 ET) — crontab의 `hour`는 **전부 ET로 해석**됨
  - 현재(6월) = EDT → KST = ET + 13h. (겨울 EST = ET + 14h)

---

## ⚠️ 0. 최우선 전제 — 감사 대상은 DB이지 config dict가 아니다

`config/settings.py:490`:
```python
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

이 설정 때문에 **`config/celery.py`의 `beat_schedule` dict는 런타임에 완전히 무시된다.**
진실의 소스(source of truth)는 `django_celery_beat.PeriodicTask` DB 테이블이다.
`celery.py` 상단 주석(L124~140)도 이 사실을 명시하고 있다.

따라서 본 감사는 **양쪽을 모두 조회**해 대조했다.

| 소스 | 항목 수 |
|------|--------|
| `config/celery.py` dict (선언적 reference) | **86** |
| DB `PeriodicTask` (enabled=True, 실제 실행) | **109** |
| **차이 (DB에만 존재 = reference 미반영)** | **23** |
| config dict에만 존재 (DB 미등록 → 절대 실행 안 됨) | **0** |

> 즉 reference dict의 86개는 전부 DB에 있으나, DB에는 **문서화되지 않은 23개 태스크가 추가로 돌고 있다.** 감사·운영의 사각지대다.

---

## 1. 스케줄 Drift 분석 (가장 중요한 발견)

### 1-A. DB에만 존재하는 23개 (reference dict 미반영)

| 분류 | 태스크 | 비고 |
|------|--------|------|
| **Market Pulse (11)** | `mp_calc_breadth_5min`, `mp_calc_sector_5min`, `mp_detect_anomaly_5min` (각 `*/5` 09–16시), `mp_calc_regime_15min` (`*/15` 24시간), `mp_calc_concentration_daily` (17:15), `mp_finalize_daily` (16:30), `mp_generate_brief_daily` (17:15, LLM), `mp_sync_yahoo_indicators_daily` (17:35), `mp_fetch_news_hourly` (매시 :05), `mp_purge_news_daily` (14:00), `mp_purge_news_view_log_daily` (14:05) | **정상 기능**이나 reference dict에 전혀 없음 → 장중 부하의 실제 주범인데 문서엔 안 보임 |
| **Metrics/Harness (5)** | `agent-report-data-6am-kst`(06:00), `agent-report-backend-615am-kst`(06:15), `agent-report-qa-630am-kst`(06:30), `agent-report-design-645am-kst`(06:45), `metrics-daily-report-7am-kst`(07:00) | 야간 자동화/리포트, 정상 |
| **Celery 내장 (1)** | `celery.backend_cleanup` (04:00) | 정상 |
| **Chain Sight (1)** | `chainsight-seed-snapshot-cleanup` (일 13:30) | 정상 |
| **🔴 Orphan / 잘못된 경로 (5)** | 아래 1-B 참조 | **실행 시마다 에러 발생 추정** |

### 1-B. 🔴 잘못된 모듈 경로 태스크 5개 (NotRegistered 에러 추정)

worker는 `services.news.tasks.*` / `services.rag_analysis.tasks.*` 로 태스크를 등록(autodiscover)한다.
그런데 DB에는 `services.` 접두사가 빠진 **구(舊) 경로**로 등록된 태스크가 남아 있다:

| DB 태스크명 | 등록된 task 경로 | 올바른 경로 | 스케줄 | 문제 |
|------------|-----------------|------------|--------|------|
| `cleanup-expired-semantic-cache` | `rag_analysis.tasks.cleanup_expired_semantic_cache` | `services.rag_analysis.tasks.*` | 04:00 매일 | `celery.py` 주석은 "Semantic Cache 제거됨/미초기화"라 했으나 DB에 잔존. 경로도 틀림 → **NotRegistered** |
| `warm-semantic-cache` | `rag_analysis.tasks.warm_semantic_cache` | 〃 | 일 04:30 | 〃 |
| `semantic-cache-stats` | `rag_analysis.tasks.get_semantic_cache_stats` | 〃 | `*/6` 매일 | 〃 |
| `collect-daily-news` | `news.tasks.collect_daily_news` | `services.news.tasks.*` | 06:00 평일 | **`collect-daily-news-morning`(정상 경로, 동일 06:00)과 중복** |
| `collect-category-news-medium` | `news.tasks.collect_category_news` | `services.news.tasks.*` | 07:00 평일 | **`collect-category-news-medium-morning`(정상 경로, 동일 07:00)과 중복** |

**영향**:
- 3개 semantic-cache 태스크: 매 발화 시 worker가 `NotRegistered` 거부 → Celery 에러 로그 누적 (실제 작업 X). 일일 에러 다이제스트(`celery-error-digest`, 07:00) 노이즈 가능성.
- `collect-daily-news`, `collect-category-news-medium`: 정상 경로 버전과 **같은 시각 중복 발화**. 잘못된 경로라 실제 이중 수집은 아니나(에러로 죽음), 06:00/07:00 슬롯에 무의미한 발화 1건씩 추가.

> 권장(차후 수정 시): Django admin → Periodic Tasks 에서 위 5개 row를 **삭제** 또는 올바른 경로로 교정. 본 보고서는 읽기 전용이라 미수정.

---

## 2. Rate Limit 초과 구간 분석

분석 핵심: **rate limit은 "시간대"가 아니라 "특정 분(minute)에 동시 발화하는 태스크 수"** 로 판단해야 한다.
아래는 DB 기준(실제 실행) 분 단위 동시 발화 슬롯이다.

### 2-A. FMP (Starter: 300 calls/분, 10,000 calls/일)

**분당 한도 리스크: 🟡 LOW~MODERATE (자가 스로틀로 대부분 방어됨)**

장중 FMP 동시 발화 최대 슬롯은 **n=6** (예: 10:15, 13:15, 15:15):
```
collect-sp500-news-fmp-{HHMM}, update-market-indices, update-realtime-prices,
mp_calc_breadth_5min, mp_calc_sector_5min, mp_detect_anomaly_5min
```
이 중 실제 FMP API를 무겁게 때리는 것은 일부이며, **코드 레벨 스로틀이 존재**한다:

| 태스크 | 스로틀 | 분당 FMP 상한 |
|--------|--------|--------------|
| `update_realtime_with_provider` (`*/5`) | 종목별 루프 + `time.sleep(1)` (`tasks.py:366` `for symbol ... sleep(1)`) | **≤60/분** (자가 스로틀). 기본 대상 = 포트폴리오 보유 종목(전 종목 아님) |
| `collect_sp500_news_fmp_orchestrator` (`:15`) | `@shared_task(rate_limit="100/m")` (`news/tasks.py:974`) | **≤100/분** |
| `sync_sp500_financials` (20:00) | `time.sleep(1)` 호출 간 (`tasks.py:327`), `batch_size=101` | ≤60/분 |

**최악 슬롯 합산(10:15)**: orchestrator(≤100) + realtime(≤60) + market-indices + news collect ≈ **160/분 추정 < 300/분**. → **헤드룸 존재**.

**일일 한도(10,000) 추정**:
- `update-realtime`: ~12회/시 × 8시간 = 96회. 포트폴리오 N종목 가정(예 30) → ~2,880 calls/일
- `update-market-indices`: 96회 (지수 소량)
- orchestrator: 5회/일 × (84종목 × 6배치, 100/m 스로틀) — 가장 큰 변수
- financials 101 + 기타 news collect
- → **총합은 모니터링 필요하나 10k 이내일 가능성 높음.** 단 orchestrator·realtime의 실제 종목 수에 따라 변동 큼 → **FMP 일일 사용량 대시보드 확인 권장**.

> ⚠️ 불확실성: `update_realtime`의 기본 대상이 포트폴리오 종목이라 N이 사용자 보유에 비례. N이 수백으로 커지면 sleep(1) 때문에 5분(300s) 내 미완료 + 호출량 급증. 현재 N은 작아 안전 추정.

### 2-B. Gemini (Free: 15 RPM, 1500 RPD)

**분당(RPM) 리스크: 🟢 LOW (잘 관리됨)**

LLM(Gemini) 태스크의 분 단위 동시 발화를 전수 조사한 결과 **어느 슬롯도 동시 2건 이상 없음** (전부 n=1):
```
03:00 refresh-korean-overviews | 05:30 enrich-relationship-keywords | 08:00 keyword-generation
08:30 analyze-news-deep | 09:00 extract-news-relations | 10:00 chainsight-co-mentions
10:30 / 12:30 / 14:30 / 16:30 / 18:30 analyze-news-deep | 16:45 extract-daily-news-keywords
17:15 mp_generate_brief_daily | 18:35 thesis-generate-summaries
```
- `analyze-news-deep`(:30)와 `extract-daily-news-keywords`를 16:45로 분산한 과거 조치(P0 #8, 2026-04-26 주석)가 유효하게 작동 중. **15분 간격 유지됨.**
- 단, 각 태스크가 **내부에서 다수 기사를 순회하며 Gemini를 반복 호출**하므로 태스크 1건 = API 1건이 아님. `analyze_news_deep`는 `max_articles=50` → 1회 실행에 최대 ~50 호출. 15 RPM 방어는 태스크 내부 스로틀에 의존(스케줄 레벨에선 안전).

**일일(RPD) 리스크: 🟡 MODERATE — 1500 RPD 근접 가능**
- `analyze-news-deep` 6회/일 × ≤50 = **최대 ~300**
- `enrich-relationship-keywords` (`limit=100`) ~100
- `chainsight-co-mentions`, `extract-news-relations`, `keyword-generation`, `thesis-summaries`, `mp_generate_brief`, `korean-overviews`(월1, 50) 등 가산
- → 바쁜 날 **수백~1000+ RPD** 도달 가능. 1500 RPD 상한에 **여유는 있으나 모니터링 권장**.

### 2-C. Alpha Vantage (5 calls/분)

**리스크: 🟢 없음 (해당 없음)**
- Beat 스케줄에서 AV 의존 태스크 **미발견**. 실시간/EOD/지수 모두 FMP Provider로 이관됨.
- AV 키는 `.env` 필수 항목이나 스케줄러 경로에서는 사용되지 않음.

---

## 3. Queue 몰림 분석

`task_routes`(celery.py:43–61) 기준 큐는 2개: **default**, **neo4j**(`--pool=solo`, 동시 1개).

### 3-A. default queue — 장중 고회전, 경량

장중(09–16 ET) 시간당 총 발화 **150~160회**. 단 대부분 경량·고빈도:

| 태스크 | 빈도 | 시간당 |
|--------|------|--------|
| `refresh-market-pulse-cache` | 매분 (`m=*`) | **60** ← 최대 기여 |
| `update-realtime-prices` / `update-market-indices` | `*/5` | 각 12 |
| `mp_calc_breadth_5min` / `mp_calc_sector_5min` / `mp_detect_anomaly_5min` | `*/5` | 각 12 |
| `calculate-portfolio-values` | `*/10` | 6 |
| `mp_calc_regime_15min` / `check-screener-alerts` | `*/15` | 각 4 |
| `check-pipeline-alerts` | `*/30` | 2 |

→ **결론**: 건수는 많으나 개별 태스크가 가벼움(캐시 갱신·벡터 계산). worker 동시성이 충분하면 몰림 위험 낮음. 단 `refresh-market-pulse-cache`가 분당 1회로 가장 빈번 → 이 태스크 1건 실행시간이 60초를 넘으면 **자기 자신과 겹침**. 실행시간 모니터링 권장.

### 3-B. 🟡 neo4j queue (solo pool, 직렬) — 잠재 밀림

solo pool은 **동시 1개만 처리**. 24시간 내내 baseline ~12건/시 발생:

| 태스크 | 빈도 | 큐 점유 |
|--------|------|--------|
| `sec-sync-dirty-neo4j` (`sync_dirty_to_neo4j`) | **`*/5` 24시간** | 시간당 12건 ← neo4j 큐 상시 점유의 주범 |
| `neo4j-health-check` | `*/6시간` | 소량 |
| `chainsight-sync-profiles-neo4j` (12:00) / `chainsight-sync-relations-neo4j` (12:30) | 1회/일 | 무거움 가능 |
| `sync-news-to-neo4j` (`:45` 8,10,12,14,16,18시) | 6회/일 | `max_articles=100` |
| `enrich-relationship-keywords`(05:30), `cleanup-expired-news-relationships`(04:00), `chainsight-neo4j-dirty-sync`(일 04:30) | | |

**밀림 시나리오**:
- `sec-sync-dirty`가 매 5분(=300s)마다 도는데, **solo pool에서 다른 무거운 neo4j 태스크가 5분 이상 점유하면 sec-sync가 큐에서 대기 → 누적**.
- 특히 **12:00**: `chainsight-sync-profiles-neo4j` + `sec-sync-dirty`(:00 발화) + `sec-seed-relations-to-chainsight`(12:00) 동시 진입 → solo pool 직렬 처리로 대기열 형성.
- `sec-sync-dirty`의 `expires=240`(4분)이라, 밀려서 4분 초과 시 **자동 만료·스킵**됨(데이터 유실은 아니고 다음 5분 주기에 재시도되는 idempotent 구조면 안전).

> 권장 점검: neo4j worker가 단일 solo 프로세스인지, 평균 태스크 실행시간이 5분 미만인지 확인. `sync_profiles`/`sync_relations`가 5분 초과면 sec-sync 만료 빈발 가능.

---

## 4. 시간대별 ASCII 히트맵 (평일, ET 기준)

### 4-A. 전체 발화 횟수 / 시간 (DB 실제 기준)

```
시각(ET)  건수  | 0        10        20        30        40 firings/h
H00       21  | █████
H01       20  | █████
H02       21  | █████
H03       21  | █████          ← 야간 ML 학습 윈도우(일요일 train-*)
H04       25  | ██████         ← cleanup/decay/patent/regulatory 집중
H05       20  | █████
H06       33  | ████████       ← 뉴스 수집 + agent-report + sec-check 시작
H07       27  | ██████         ← market-movers + press-release + digest
H08       24  | ██████         ← 장전 분류/분석 시작
H09  ███  151  | ████████████████████████████████████  ◀ 장 시작, 분당 태스크 폭증
H10  ███  154  | ██████████████████████████████████████
H11  ███  150  | █████████████████████████████████████
H12  ███  160  | ████████████████████████████████████████ ◀◀ PEAK (12:00 동시 17건)
H13  ███  152  | ██████████████████████████████████████
H14  ███  156  | ███████████████████████████████████████
H15  ███  151  | █████████████████████████████████████
H16  ███  156  | ███████████████████████████████████████ ◀ 장 마감 + EOD 계산 시작
H17       26  | ██████         ← daily-prices + concentration + brief + yahoo sync
H18       33  | ████████       ◀ EOD/Thesis 파이프라인 집중 (18:00~18:35)
H19       21  | █████          ← backfill-signal + ml-labels
H20       20  | █████          ← sync-sp500-financials
H21       19  | ████
H22       20  | █████          ← economic-indicators(22:00)
H23       19  | ████
```
> 장중(09–16) 건수는 `refresh-market-pulse-cache`(분당) + `*/5` mp 태스크군이 지배. 절대량보다 **개별 실행시간**이 관건.

### 4-B. FMP 호출 태스크 발화 / 시간

```
시각(ET)  FMP발화 |
H06        5  | ██████        뉴스 orchestrator(06:15) + general/daily/category
H07        5  | ██████        movers + press-release + general(06:45)
H08        1  | ██
H09       24  | ████████████████████████  ◀ 장중 baseline (realtime+indices+mp ×*/5)
H10       25  | █████████████████████████  ◀ +orchestrator(10:15)
H11       24  | ████████████████████████
H12       26  | ██████████████████████████ ◀ +market-news-noon + general-noon
H13       26  | ██████████████████████████ ◀ +category-midday + orchestrator(13:15)
H14       26  | ██████████████████████████
H15       26  | ██████████████████████████ ◀ +market-afternoon + orchestrator(15:15)
H16       26  | ██████████████████████████ ◀ +breadth/heatmap(16:30/35)
H17        4  | ████          daily-prices + category-evening(17:00)
H18        2  | ██            eod-prices(18:00)
H20        1  | ██            financials
```
> "발화"는 ≠ "API 콜". 각 발화는 sleep(1)·rate_limit으로 자가 스로틀됨(2-A 참조).

### 4-C. Gemini(LLM) 호출 태스크 발화 / 시간 — 전부 분산됨(동시 ≤1)

```
03 ▏ korean-overviews(월1)        12 ▏ analyze-deep
05 ▏ enrich-keywords              14 ▏ analyze-deep
08 ▏▏ keyword-gen + analyze-deep  16 ▏▏ analyze-deep + extract-keywords(16:45)
09 ▏ extract-news-relations       17 ▏ mp_generate_brief
10 ▏▏ co-mentions + analyze-deep  18 ▏▏ analyze-deep + thesis-summaries(18:35)
```
> 동일 분 충돌 0건. 단 시간 단위로는 08·10·16·18시에 LLM 2종 근접(15~30분 간격 유지) → RPM 안전, RPD만 누적 주의.

---

## 5. 스케줄 겹침 / 의존성 경합

### 5-A. 🟡 EOD/Thesis 파이프라인 — 동시각 경합 의심

18:00~18:35 ET 사이 EOD 체인이 밀집:

| 시각 | 태스크 | 의존 관계 | 경합 |
|------|--------|----------|------|
| 18:00 | `sync-sp500-eod-prices` (EOD 가격 수집) | 선행 데이터 생성 | **🔴 `thesis-update-readings`와 동일 18:00 발화** |
| 18:00 | `thesis-update-readings` (지표 수집) | EOD 가격을 읽어야 함 | EOD 가격 sync 완료 전 읽으면 **stale 데이터** 가능 |
| 18:15 | `thesis-calculate-scores` | readings 완료 후 | 18:00 readings가 15분 내 끝나야 안전 |
| 18:30 | `run-eod-pipeline` (시그널) + `thesis-create-snapshots` | EOD prices 후 | **동일 18:30 발화** (두 파이프라인 동시) |
| 18:35 | `thesis-generate-summaries` (LLM) | snapshots 후 | snapshot이 5분 내 끝나야 함 |
| 19:00 | `backfill-signal-accuracy` | run-eod-pipeline 후 | 30분 여유, OK |

**핵심 경합**: `sync-sp500-eod-prices`(18:00)와 `thesis-update-readings`(18:00)가 **같은 분 발화**. thesis가 EOD 가격을 입력으로 쓴다면, 가격 sync가 끝나기 전에 읽어 **전일/직전 값으로 계산**될 위험. 현재는 "EOD prices가 빠르게 끝난다"는 암묵적 가정에 의존.

### 5-B. Chain Sight 토요일 새벽 직렬 체인 (정상 설계)

토요일 02:00→03:00→04:00→04:30 (`all-profiles`→`price-co-movement`→`stale-decay`→`aggregate-profiles`)는 1시간 간격으로 충분히 이격됨. 단 `all-profiles`(`expires=7200`=2h)가 2시간 초과하면 후속과 겹침 가능 — 실행시간 모니터링 권장.

### 5-C. 12:00 ET 슈퍼 슬롯 (동시 17건)

`12:00`은 전 슬롯 중 최대 동시 발화(17건): market-news-noon, general-fmp-noon, sec-seed-relations, chainsight-sync-profiles-neo4j, mp 계산군(×3), realtime, indices, refresh-cache 등. default + neo4j 큐 동시 진입. neo4j는 solo라 `sync-profiles`가 길면 `sec-sync-dirty`(12:00 발화) 대기(3-B 참조).

---

## 6. 우선순위 종합 (Findings)

| # | 심각도 | 발견 | 근거 | 비고(읽기전용·미수정) |
|---|--------|------|------|----------------------|
| F1 | 🔴 High | **잘못된 모듈 경로 orphan 5개** (semantic-cache ×3 `rag_analysis.tasks.*`, news ×2 `news.tasks.*`) → 발화 시마다 NotRegistered 에러 추정 | §1-B | admin에서 삭제/경로 교정 필요 |
| F2 | 🟠 Med | **config dict ↔ DB drift 23건** (mp_* 11 등 reference 미반영) | §1-A | 운영 사각지대. dict를 DB와 동기화하거나 dict 삭제 후 DB-only 명문화 |
| F3 | 🟠 Med | **중복 발화** 06:00(`collect-daily-news` ×2), 07:00(`category-medium` ×2) | §1-B | 잘못된 경로 버전 제거 시 자동 해소 |
| F4 | 🟡 Low | **neo4j solo 큐 밀림 잠재** — `sec-sync-dirty`(`*/5` 24h) + 12:00 무거운 sync 직렬 | §3-B | neo4j 태스크 평균 실행시간 <5분 확인 |
| F5 | 🟡 Low | **18:00 EOD-prices ↔ thesis-readings 동일분 경합** | §5-A | thesis를 18:05로 이격하면 안전. 현재 암묵 가정 의존 |
| F6 | 🟡 Watch | **Gemini RPD 누적** — analyze-deep 6×50 등 → 1500 RPD 근접 가능 | §2-B | 실제 일일 호출량 대시보드 확인 |
| F7 | 🟡 Watch | **FMP 일일 한도** — realtime/orchestrator 종목 수에 비례, 변동 큼 | §2-A | FMP 사용량 모니터링 |
| F8 | 🟢 OK | Gemini 분당(RPM) 충돌 0 / Alpha Vantage 의존 0 | §2-B, §2-C | 과거 16:45 분산 조치 유효 |

---

## 7. 방법론 메모

- DB 조회: `PeriodicTask.objects.filter(enabled=True)` 전수(109건), crontab 필드 파싱.
- 히트맵: 평일(`day_of_week`에 1~5 포함) 기준, `*/n`·`a-b`·`a,b,c`·`*` 전개 후 시간/분 슬롯 집계.
- FMP/Gemini/neo4j 분류: task 경로 키워드 매칭(보수적). "발화 횟수"는 스케줄 트리거 수이며 실제 외부 API 콜 수와 다름(태스크 내부 루프·스로틀 별도).
- 코드 스로틀 교차검증: `packages/shared/stocks/tasks.py:327,366`, `services/news/tasks.py:974`.
- 본 보고서는 **읽기 전용**. 어떤 스케줄·코드도 수정하지 않음.
