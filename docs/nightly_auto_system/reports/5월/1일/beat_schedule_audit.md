# Beat Schedule 감사 보고서

- **대상 파일**: `config/celery.py` (813 lines, beat_schedule = 75개 태스크)
- **감사 일자**: 2026-05-01
- **모드**: 읽기 전용 (코드 수정 없음)
- **시간대 표기**: 모두 EST/ET 기준 (코드의 `crontab(hour=...)` 그대로). UTC 명시 항목만 별도 표기
- **소스 진실**: `config/settings.py`의 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 이므로 `app.conf.beat_schedule` dict는 reference 용도. 실제 실행은 `django_celery_beat.PeriodicTask` DB 테이블 기준 (config/celery.py:118-134 참조). **본 감사는 dict 기준이며 DB와의 drift는 별도 검증 필요**

---

## 0. 감사 결과 요약

| 등급 | 항목 수 | 핵심 문제 |
|------|--------|-----------|
| P0 (즉시 조치) | 4 | EOD 18:30 핫스팟, neo4j solo queue 12:00 적체, FMP 18:00 동시 호출, sec-sync expires 240s 만료 위험 |
| P1 (빠른 조치) | 6 | News v3 :15→:30→:45 처리시간 누적, 일요일 04:00 다중 충돌, 매월1일 03:00 Gemini 폭주, 의존성 비명시 |
| P2 (개선) | 4 | neo4j health check 시간 충돌, */30 알림 점검 trigger 단발성, RPM/RPD 모니터링 부재, day_of_week 누락 일관성 |

---

## 1. 시간대별 ASCII 히트맵 (평일 기준)

각 시간 슬롯에서 **시작되는 distinct 태스크 수** 카운트. `*/5`, `*/15`, `*/30`, `*/1` 같은 분 단위 반복은 시간당 고정 횟수로 합산.

```
시간(ET) | 태스크 수 | 히트맵 (1칸=2개)        | 주요 부하
─────────┼──────────┼─────────────────────────┼──────────────────────────────────
00 :00   |    14    | #######                 │ sec-sync(12)+alerts(2)+nh-hc(0,*/6)
01 :00   |    15    | ########                │ +econ-calendar(매일)
02 :00   |    14    | #######                 │ baseline (월1/토 추가 시 +2~3)
03 :00   |    14    | #######                 │ baseline (일/토/월1 추가 시 +5)
04 :00   |    15    | ########                │ +cleanup-news-rel(매일, neo4j Q)
05 :00   |    15    | ########                │ +enrich-rel-keywords(매일, Gemini)
06 :00   |    21    | ###########             │ daily/sp500-news-fmp + cat-high + gen-news + neo4j-hc
07 :00   |    20    | ##########              │ heat-score+celery-digest+mvers+cat-low+press-rel
08 :00   |    19    | ##########              │ keyword-gen+mkt-news+classify+analyze-deep+sync-neo
09 :00   |   ~110   | ########################│ 9-16시 평일 매분: rt-prices,mkt-idx,pulse,portfolio,scr-alerts
10 :00   |   ~113   | ########################│ +co-mentions+sp500-news-1015+classify/analyze/sync
11 :00   |   ~109   | ########################│ +relation-confidence
12 :00   |   ~121   | ########################│ ★PEAK★ neo4j-hc+econ+mkt-news+chainsight-sync-prof+sec-seed
                                              │   +classify+gen-news-noon+chain-sync-rel+analyze+sync-neo
13 :00   |   ~111   | ########################│ +cat-high-mid+seed-selection(UTC)+sp500-news-1315
14 :00   |   ~113   | ########################│ +cat-med-aft+classify+daily-news-aft+analyze+sync-neo
15 :00   |   ~109   | ########################│ +mkt-news-aft+sp500-news-1515
16 :00   |   ~116   | ########################│ +classify+mkt-breadth+analyze+sec-heatmap+extr-keyword+sync-neo
17 :00   |    18    | #########               │ daily-prices+cat-high-eve+sp500-news-1715+gen-news-eve
18 :00   |    26    | #############           │ ★PEAK★ neo4j-hc+econ+mkt-news+sp500-eod+thesis-read+classify
                                              │   +thesis-calc+analyze+update-pct+run-eod+thesis-snap+sync-neo
19 :00   |    16    | ########                │ +collect-ml-labels+backfill-sig-acc
20 :00   |    15    | ########                │ +sync-sp500-financials
21 :00   |    14    | #######                 │ baseline
22 :00   |    15    | ########                │ +econ-indicators
23 :00   |    14    | #######                 │ baseline
```

**Baseline (모든 시간대 공통)**: `sec-sync-dirty-neo4j` (*/5 → 12회/시간) + `check-pipeline-alerts` (*/30 → 2회/시간) = 14회.

**평일 9-16시 추가 부하 (시간당)**:
- `refresh-market-pulse-cache` (`*/1`): **60회**
- `update-realtime-prices` (`*/5`): 12회
- `update-market-indices` (`*/5`): 12회
- `calculate-portfolio-values` (`*/10`): 6회
- `check-screener-alerts` (`*/15`): 4회
- 합계: 시간당 **+94회**

---

## 2. 단일 분 동시 시작 — 핵심 핫스팟

| 분점 | 동시 시작 태스크 | 큐 분포 | 외부 API 부하 |
|------|------------------|---------|----------------|
| **12:00 평일** (7개) | econ-ind, mkt-news-noon, chainsight-sync-prof-neo, sec-seed-rel, alerts, sec-sync, neo4j-hc | default(3) + **neo4j(3)** + 그 외 | FRED, MarketAux, Neo4j 폭주 |
| **18:00 평일** (6개) | econ-ind, mkt-news-eve, sp500-eod-prices, thesis-readings, neo4j-hc, sec-sync | default(4) + neo4j(2) | **FMP 503종목 + thesis 지표 동시** |
| **18:30 평일** (6개) | thesis-snap, run-eod, update-pct, analyze-news-deep, alerts, sec-sync | default(5) + neo4j(1) | **Gemini + FMP + 내부 5종 경합** |
| **04:00 일요일** | cleanup-news-rel, check-auto-deploy, ml-rel(자동배포 후 작업), alerts, sec-sync | neo4j(2) + default(2) | Neo4j cleanup 무거움 |
| **04:30 일요일** | chainsight-neo4j-dirty-sync, train-lightgbm, alerts, sec-sync | neo4j(2) + default(2) | LightGBM CPU 무거움 |
| **03:00 매월1일이 일요일** | cleanup-old-macro, train-importance, refresh-korean-overviews, sec-sync | default(3) | **Gemini 503종목 LLM + 모델학습** |

---

## 3. Rate Limit 초과 위험 분석

### 3.1 FMP (Starter 300 calls/min)

**최대 위험 슬롯: 18:00 평일**

`sync-sp500-eod-prices` (503 종목 EOD) + `thesis-update-readings` (지표 다수 호출) 동시 시작.

- FMP 503 종목 단순 fetch = ~503 calls (배치 가능 시 50/100단위로 축소되지만 코드 미확인)
- 만약 `/stable/historical-price-eod/full?symbol=XXX` 단일 호출 503회 → 분당 한도 ~1분 40초 소요
- 동시에 `thesis-update-readings`이 Stock 단위로 PE/ROE 등 호출하면 50~150 추가 호출
- **10초 윈도우 동시 호출 시 Starter 한도 초과 가능성: 매우 높음**

**13:15, 15:15, 17:15, 10:15, 06:15 평일** (`collect-sp500-news-fmp-XXXX` orchestrator)

- S&P 500 전체 503 종목 뉴스 수집 → 종목당 1 call 가정 시 503 calls
- 분당 300 한도라면 ~1분 41초 소요 → expires=3600초이므로 timeout 자체는 OK
- **그러나 다른 평일 9-16시 매분 태스크 (rt-prices, mkt-idx, pulse-cache 등)와 동시 분산 시 가시적 지연**

**일별 FMP 호출 추정** (평일):
- realtime-prices: 96회 × 503 = ~48,000 (단, 코드상 batch 여부 확인 필요)
- market-indices: 96회 (지수 ~5개 × 96 = 480)
- sp500-news 5회 × 503 = ~2,500
- sp500-financials: 101회/일 (5일 1회전)
- press-releases: 50회/일
- general-news: 3회 × n
- sp500-eod-prices: 503회/일
- thesis-readings: 추정 1,500회/일

**대략 일일 50,000+ FMP 호출** → 월 1,000,000+ 가능. Starter Plan 일별 한도(별도 명시 없으나 분당 300 = 432,000 이론치) 내이지만 **분당 한도 위반은 18:00 슬롯에서 거의 확실**.

### 3.2 Gemini (Free Tier: 15 RPM, 1500 RPD)

**일별 LLM 호출 추정**:
- analyze-news-deep-batch: 6회 × max 50 = 300/일 (평일)
- extract-daily-news-keywords: ~50/일 (1회)
- enrich-relationship-keywords: 100/일 (1회)
- keyword-generation-pipeline (Gainers): ~10/일
- chainsight-co-mentions LLM: 미확인
- chainsight-relation-confidence LLM: 미확인
- refresh-korean-overviews-monthly: **503/월 (월1일 한 번)**
- train-importance-model: ML 학습 (LLM 미사용)
- ML 분석 등 chainsight 관련 LLM 추정 +200~300/일

**총 ~700~800 RPD** → 1500 한도 절반 이하. 그러나 **월 1일은 한도 근접**.

**RPM 위험 슬롯**:

1. **16:30~16:45 동시 호출**:
   - 16:30 `analyze-news-deep-batch` (50개 직렬 LLM)
   - 16:45 `extract-daily-news-keywords` (~50개 LLM)
   - 50개 직렬 호출 = 50/15 RPM = ~3분 20초 → 16:30 시작이 16:33에 끝나야 16:45 시작에 안전
   - **소스 코드 주석 (config/celery.py:285)에 이미 동일 이슈 인지 + 15분 분산 적용 (2026-04-26)**
   - 검증: 50개 RPM 한도 도달 시 backoff 적용 → 5분 이상 길어지면 16:45와 충돌 재발 가능

2. **18:30 + 16:30 동일 패턴**: `analyze-news-deep-batch` 자체가 RPM 한도에 걸리면 다음 사이클(:30)이 누적

3. **매월 1일 03:00 일요일 충돌**: 
   - `refresh-korean-overviews-monthly` (503개 LLM, ~33분) + `train-importance-model` (모델 학습, LLM 미사용 추정)
   - 만약 `train-importance-model`이 Shadow Mode 비교용 LLM 호출을 수반하면 RPM 충돌

### 3.3 Alpha Vantage (5 calls/min)

**검색 결과**: `config/celery.py` beat_schedule 75개 태스크 중 **Alpha Vantage 직접 호출 태스크는 없음** (FRED/FMP/SEC 위주). 단, processor 레벨에서 fallback 호출 가능성 있음 → 코드베이스 별도 점검 권장 (감사 범위 외).

### 3.4 SEC EDGAR (10 req/sec)

`sec-check-new-filings` (월1일 06:00), `sync-supply-chain-batch` (월15일 03:00), `sync-institutional-holdings` (월16일 04:00). 단발성이며 SEC 한도 내 안전.

---

## 4. Queue 몰림 분석

### 4.1 neo4j queue (solo pool, 동시 1개)

**구성**: 11개 태스크가 라우팅됨 (config/celery.py:38-54).

**일별 호출량**:
- `sec_pipeline.tasks.sync_dirty_to_neo4j`: **288회/일** (`*/5`)
- `chainsight.tasks.sync_tasks.sync_profiles_to_neo4j`: 1회/일 (12:00)
- `chainsight.tasks.sync_tasks.sync_relations_to_neo4j`: 1회/일 (12:30)
- `news.tasks.sync_news_to_neo4j`: 6회/일 평일 (8,10,12,14,16,18 :45)
- `news.tasks.cleanup_expired_news_relationships`: 1회/일 (04:00)
- `serverless.tasks.enrich_relationship_keywords`: 1회/일 (05:30)
- `rag_analysis.tasks.health_check_neo4j`: 4회/일 (00,06,12,18시)
- `chainsight-neo4j-dirty-sync`: 1회/주 (일 04:30 UTC)

총 **~302회/일 (평일)** + 약간.

**위험 1 — 12:00 적체 (P0)**:
- 12:00 동시 큐잉:
  - `chainsight-sync-profiles-neo4j` (503 종목, 큰 작업)
  - `sec-sync-dirty-neo4j` (`*/5` → 12:00 trigger)
  - `neo4j-health-check` (`*/6` → 12시)
- 12:30 추가:
  - `chainsight-sync-relations-neo4j` (관계 다수)
  - `sec-sync-dirty-neo4j`
- 12:45 추가:
  - `news.tasks.sync_news_to_neo4j` (max 100)
  - `sec-sync-dirty-neo4j`

**solo pool은 1개씩 직렬 처리**. `chainsight-sync-profiles-neo4j`가 5분 이상 걸리면 12:05 trigger의 `sec-sync-dirty-neo4j` (expires=240초)는 **만료됨**. 다음 12:10 trigger도 위험.

**검증 방법**: `celery -A config inspect active --queue=neo4j` + `python manage.py shell`에서 TaskResult 만료 카운트 조회.

**위험 2 — sec-sync-dirty-neo4j expires=240초 vs schedule */5 (P0)**:

```python
'sec-sync-dirty-neo4j': {
    ...
    'schedule': crontab(minute='*/5'),
    'options': {'expires': 240}  # 4분
}
```

- schedule = 5분(300초)마다 trigger
- expires = 240초 (4분)
- 의도: 다음 trigger 전에 만료시키자
- **위험**: solo pool에 다른 무거운 태스크가 4분 이상 점유 시 즉시 만료
- 12:00, 12:30, 18:45, 04:00 핫스팟에서 발생 가능성 매우 높음
- 결과: dirty evidence가 5분 단위로 쌓이지 못하고 lag 발생

**위험 3 — 18:45 sync-news-to-neo4j 100건 + 18:30 직전 작업 누적**:
- 18:30 `analyze-news-deep-batch` (50개 LLM) → default queue지만 LLM 응답 시간 분 단위
- 18:45 `sync-news-to-neo4j` (100개) → neo4j queue
- 동시 시각 18:45에 `sec-sync-dirty-neo4j` 도 trigger
- solo pool 처리 중 다음 trigger 누락 위험

### 4.2 default queue

**18:30 평일 동시 실행**:
1. `thesis-create-snapshots` (Gemini 가능, 알림 발송)
2. `run-eod-pipeline` (시그널 14개 계산, 503 종목)
3. `update-sp500-change-percent` (DB 일괄 update)
4. `analyze-news-deep-batch` (Gemini 50개)
5. `check-pipeline-alerts` (가벼움)

**문제**:
- 5개 동시 실행 → prefork 워커 수가 부족하면 큐 적체
- macOS dev 환경에서는 solo pool 강제 (`config/celery.py:30-31`) → **1개씩 직렬 처리** → 약 30분~1시간 누적 지연 가능
- 19:00 `collect-ml-labels`, `backfill-signal-accuracy`이 18:30 작업 미완 상태에서 시작될 가능성

**12:00 평일 동시 실행**:
1. `update-economic-indicators` (FRED)
2. `collect-market-news-noon` (MarketAux/뉴스 API)
3. `sec-seed-relations-to-chainsight` (의존: SEC 데이터 + Chain Sight)
4. `check-pipeline-alerts`

→ default queue 4개. 무거운 작업은 collect-market-news-noon 정도. 상대적 부담 낮음.

---

## 5. 의존성 / 선후관계 분석

### 5.1 EOD Dashboard 체인 (P0)

```
17:00 update-daily-prices (FMP)
  ↓
18:00 sync-sp500-eod-prices (FMP, 503 종목, ~2분)
  ↓ (의존: EOD 가격)
18:30 update-sp500-change-percent (DB)  ←┐
18:30 run-eod-pipeline (시그널 14개)    ←┤ 동시 시작 = 데이터 경합
18:30 thesis-create-snapshots (스냅샷)  ←┘
  ↓
19:00 backfill-signal-accuracy
```

**문제 1**: 18:00 `sync-sp500-eod-prices`가 18:30 이전에 끝나야 함. FMP 한도 가정 시 1.5~2분 소요 → 마진 28분, OK.

**문제 2**: 18:30에 `update-sp500-change-percent`(change_percent 계산)와 `run-eod-pipeline`(시그널 계산, change_percent 사용 가능)이 **동시 시작**. 
- `run-eod-pipeline`이 change_percent를 읽을 때 미완성 데이터를 참조할 위험
- 권장: `update-sp500-change-percent` → `run-eod-pipeline` 직렬화 (예: 18:30 / 18:35)

**문제 3**: 18:00에 `thesis-update-readings`(thesis 지표 데이터 수집)도 시작. 이는 `sync-sp500-eod-prices`와 동일 FMP 키 사용 → API 경합. 또한 thesis-readings가 ROE/PE 등 FMP `/stable/key-metrics-ttm` 호출하면 sp500-eod와 동일 도메인 한도 공유.

### 5.2 Thesis Control 체인

```
18:00 thesis-update-readings    (FMP 추정)
18:15 thesis-calculate-scores   ← readings 의존
18:30 thesis-create-snapshots   ← scores 의존
```

15분 간격 명시적 의존. Readings가 15분 안에 안 끝나면 calculate-scores가 미완성 데이터 사용. 종목 수 / FMP 한도 검증 필요.

### 5.3 News Pipeline v3 :15→:30→:45 패턴 (P1)

```
:15 classify-news-batch       (분류, ML 추정)
:30 analyze-news-deep-batch   (Gemini 50개)
:45 sync-news-to-neo4j        (Neo4j 100개)
```

- 8,10,12,14,16,18시 6회 반복.
- 15분 간격이 빠듯. analyze-deep 50개 × Gemini 평균 5초 = ~4분 16초. RPM 한도 걸리면 더 길어짐.
- 코드 주석(config/celery.py:284-286)에 충돌 회피 이력 있음 → **여전히 잠재 리스크**.
- 처리시간 측정 + 모니터링 필요.

### 5.4 Chain Sight 토요일 체인

```
02:00 chainsight-all-profiles (프로파일 4종)
03:00 chainsight-price-co-movement (1시간 마진)
04:00 chainsight-stale-decay (1시간 마진)
04:30 chainsight-aggregate-profiles (30분 마진, 위 모두 의존)
```

마진 충분. 단, `aggregate-profiles`가 04:00 `stale-decay` 미완 시 잘못된 데이터 집계. 30분 안에 끝나는지 검증 필요.

### 5.5 ML 학습 일요일 체인 (P1)

```
03:00 train-importance-model        (30분 안에 끝나야)
03:30 generate-shadow-report        ← 학습 모델 의존
04:00 check-auto-deploy             ← shadow 의존
04:00 cleanup-expired-news-rel      (동시, neo4j Q)
04:15 generate-weekly-ml-report
04:20 monitor-ml-performance
04:30 train-lightgbm-model          (CPU 무거움)
04:30 chainsight-neo4j-dirty-sync   (UTC, neo4j Q, 동시)
04:30 build-patent-network          (매월 1일 + 일요일 = 우연 충돌)
```

**문제**:
- 04:30에 동시 3개 (lightgbm + chainsight-neo-dirty + build-patent if 1일)
- LightGBM은 CPU 집약. macOS solo pool에서 완전 직렬 → 1시간+ 가능
- expires=7200 (2시간). 일요일 06:00 다음 사이클까지 마진은 있음

### 5.6 매월 1일 누적 부하 (P1)

```
02:00 sync-sp500-constituents     (FMP)
02:30 archive-old-articles        (DB)
03:00 refresh-korean-overviews-monthly (Gemini 503개, ~33분)
04:30 build-patent-network        (무거움)
06:00 sec-check-new-filings       (SEC)
```

- 03:00~06:00에 큰 배치 4개 누적
- 만약 1일이 일요일이면 train-importance-model + Gemini 충돌
- 만약 1일이 토요일이면 02:00 chainsight-all-profiles와 02:00 sync-sp500-constituents 시각 충돌

### 5.7 비명시 의존성 (P2)

| 의존관계 | 명시 여부 | 위험 |
|---------|----------|------|
| `extract-news-relations` (09:00) → 뉴스 수집 (08:00 mkt-news, 06:00/14:30 daily) | ✓ 시간 분산 | 08:00 분류/분석 미완 시 부정확 |
| `chainsight-co-mentions` (10:00) → analyze-news-deep (08:30) | ✓ 시간 분산 | 8:30 LLM 늦으면 영향 |
| `chainsight-relation-confidence` (11:00) → co-mentions (10:00) | ✓ 1시간 마진 | OK |
| `chainsight-sync-profiles-neo4j` (12:00) → all-profiles (토 02:00) | △ 주중에는 stale 데이터 | 의도된 동작 확인 필요 |
| `keyword-generation-pipeline` (08:00) → sync-daily-market-movers (07:30) | ✓ 30분 마진 | 30분 부족 가능 |
| `aggregate-daily-sentiment` (09:00) → analyze-news-deep (08:30) | ✓ 30분 마진 | OK |
| `validation-weekly-batch` (토 05:00) → chainsight-all-profiles (토 02:00) + co-mentions (10:00) | ✗ co-mentions 후 의존 시 토 10:00 후로 옮겨야 | 문서화 필요 |

---

## 6. 추가 발견사항

### 6.1 day_of_week 누락 일관성 결여 (P2)

평일만 의미 있는데 매일로 설정된 태스크:
- `extract-daily-news-keywords` (16:45, day_of_week 없음 → 매일) — 주말 뉴스 적은데 LLM 호출
- `chainsight-co-mentions` (10:00, 매일) — 주말 뉴스 적음
- `chainsight-relation-confidence` (11:00, 매일)
- `chainsight-sync-profiles-neo4j` (12:00, 매일)
- `chainsight-sync-relations-neo4j` (12:30, 매일)
- `enrich-relationship-keywords` (05:30, 매일)
- `extract-news-relations` (09:00, 매일)
- `sec-seed-relations-to-chainsight` (12:00, 매일)
- `sec-sync-dirty-neo4j` (`*/5`, 매일)
- `cleanup-expired-news-relationships` (04:00, 매일)
- `chainsight-heat-score-daily` (07:00 UTC, 매일)
- `chainsight-seed-selection` (13:00 UTC, 매일)
- `update-economic-calendar` (01:00, 매일) — 주말 캘린더 정보는 적지만 합리적 가능

→ 의도된 매일 실행이라면 OK. 그러나 **`extract-daily-news-keywords`는 평일 한정이 자연** (장 마감 후 의도). 주말 LLM 호출 절약 가능.

### 6.2 시간대 표기 불일치 (P2)

- 대부분 EST 표기 주석
- `chainsight-heat-score-daily`, `chainsight-seed-selection`, `chainsight-neo4j-dirty-sync`만 **UTC** 명시
- 동일 비트 스케줄러 인스턴스에서 EST/UTC 혼용 → 휴면시간 분산 의도면 OK이지만, 의도가 아니면 시간 일관성 어긋남
  - EST 07:00 = UTC 12:00 (DST 시 11:00) → heat-score-daily는 UTC 07:00 = EST 02:00 (DST 시 03:00). 즉 시드 선정(13:00 UTC = EST 09:00 DST 시 08:00) 전 6시간 마진. 의도된 분산.

### 6.3 expires 옵션 일관성 (P2)

| schedule | expires | 적절성 |
|----------|---------|--------|
| `*/5` | 240 | 위험 (4분, schedule 5분) — 마진 1분만 |
| `*/15` | 600 | OK (10분) |
| `*/30` | 1500 | OK (25분) |
| crontab(매시간) | 3600 | OK |
| daily | 3600~86400 | OK |

`sec-sync-dirty-neo4j`만 빡빡. 그러나 의도된 동작(다음 trigger 전 만료)일 가능성. 경고 로그/메트릭 부재가 더 큰 문제.

### 6.4 큐 라우팅 옵션 충돌 (P2)

`sync-news-to-neo4j` 정의에서 두 가지 라우팅 메커니즘 중복:
- `task_routes` (config/celery.py:46): `'news.tasks.sync_news_to_neo4j': {'queue': 'neo4j'}`
- `beat_schedule` (config/celery.py:368): `'options': {'expires': 3600, 'queue': 'neo4j'}`

같은 큐 명시라 결과는 동일하지만 **단일 진실 소스 위반**. 미래에 한 곳만 변경되면 drift.

### 6.5 모니터링 부재

- Gemini RPM/RPD 카운터 부재 (코드에 fail-fast 또는 backoff 로직만 있을 가능성)
- FMP 분당 호출 카운터 부재
- neo4j queue 적체 시간 메트릭 부재
- expires 만료 카운트 메트릭 부재

→ 본 감사의 추정치를 검증하려면 위 메트릭 수집이 선행되어야 함.

---

## 7. 권장 조치 (코드 수정 없는 운영 가이드)

### P0 즉시 검증

1. **DB ↔ config dict drift 확인**:
   ```python
   from django_celery_beat.models import PeriodicTask
   from config.celery import app
   db_keys = set(PeriodicTask.objects.values_list('name', flat=True))
   dict_keys = set(app.conf.beat_schedule.keys())
   print("Only in DB:", db_keys - dict_keys)
   print("Only in dict:", dict_keys - db_keys)
   ```

2. **18:00, 18:30 슬롯 실측**:
   - `sync-sp500-eod-prices` 평균 소요시간 측정 (FMP 한도 도달 여부)
   - `analyze-news-deep-batch` Gemini 응답 시간 분포

3. **neo4j queue 12:00 적체 측정**:
   - `chainsight-sync-profiles-neo4j` 평균 소요시간
   - `sec-sync-dirty-neo4j` 만료 카운트 (TaskResult `EXPIRED` 또는 로그)

### P1 단기 개선 후보 (별도 PR)

4. `update-sp500-change-percent`(18:30) → 18:32로 옮겨 `sync-sp500-eod-prices` 완료 보장
5. `run-eod-pipeline`(18:30) → 18:35로 옮겨 change_percent 완료 후 시작
6. `extract-daily-news-keywords`에 `day_of_week='1-5'` 추가 (주말 LLM 절약)
7. `sec-sync-dirty-neo4j` expires=240 → 280으로 마진 확대 + 만료 메트릭 추가
8. 매월 1일이 일요일 충돌 케이스 명시 (코드 또는 PROGRESS.md)

### P2 모니터링 추가

9. Gemini/FMP/Neo4j 호출 카운터 노출 (Prometheus or 로그 기반)
10. neo4j queue 깊이 모니터링
11. EXPIRED 태스크 알림 (현재 task_failure만 모니터링)
12. `task_routes` ↔ `beat_schedule`의 `options.queue` drift 자동 검증 스크립트

---

## 8. 검증 데이터 수집 체크리스트

다음 측정 없이는 본 보고서의 추정치를 단정할 수 없음:

- [ ] DB `PeriodicTask` 실제 활성 스케줄 dump (config dict와 diff)
- [ ] 최근 30일 TaskResult `task_name`별 평균 runtime + p95 + 만료 카운트
- [ ] FMP 분당 호출 분포 (특히 18:00:00~18:01:59 슬롯)
- [ ] Gemini API 응답 헤더의 RPM/RPD 사용량 로그
- [ ] neo4j queue depth 시계열 (Flower 또는 redis-cli `LLEN celery@neo4j`)
- [ ] solo pool 점유 시간 (특히 macOS 환경)

---

## 9. 참고: 외부 API 별 Rate Limit 요약

| API | 한도 | 초과 시 동작 (가정) |
|-----|------|---------------------|
| FMP Starter | 300 calls/min | 429 응답, 코드의 retry 로직에 의존 |
| Gemini Free | 15 RPM, 1500 RPD | 429 응답, exponential backoff |
| Alpha Vantage | 5 calls/min | 429 응답 + 12초 대기 (CLAUDE.md 규칙) |
| FRED | 120 req/min (공식) | 429 응답 |
| SEC EDGAR | 10 req/sec | 429 응답 |
| Neo4j | 자체 호스팅 | DB lock 경합만 위험 |

---

**보고서 끝.** 본 감사는 `config/celery.py:135-807`의 dict 정의를 기준으로 한 정적 분석이며, 실제 PeriodicTask DB 테이블 및 런타임 메트릭과 대조한 동적 검증은 별도로 수행되어야 합니다.
