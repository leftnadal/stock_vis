# Beat Schedule 감사 보고서

- **작성일**: 2026-06-03
- **대상**: `config/celery.py` `app.conf.beat_schedule` (전 87개 항목 분석)
- **모드**: 읽기 전용 (코드 수정 없음)
- **기준 timezone**: `CELERY_TIMEZONE = 'America/New_York'` (`config/settings.py:489`)

---

## 0. 전제 — 가장 먼저 알아야 할 것 (Critical Context)

### 0-1. config dict는 런타임에 무시된다 ⚠️

`config/celery.py:124-140` 주석에 명시:

```
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
→ Celery Beat는 DB의 django_celery_beat.PeriodicTask 테이블을 진실의 소스로 사용
→ config dict는 "원래 설계된 스케줄의 선언적 reference"로만 존재
```

**본 보고서는 `config/celery.py` dict(= 설계 의도)를 분석한 것이다.**
실제 실행 스케줄은 DB `PeriodicTask`이며, 둘이 어긋나면(drift) dict의 태스크는 **실행되지 않는다**.
→ 본 보고서의 모든 충돌/부하 진단은 **"DB가 dict와 정합하다는 전제"** 하에서만 유효하다.
정확한 운영 부하를 보려면 다음 diff가 선행되어야 한다 (공통 버그 #28):

```python
# python manage.py shell
from django_celery_beat.models import PeriodicTask
db_keys = set(PeriodicTask.objects.values_list('name', flat=True))
# vs config dict 키 비교
```

### 0-2. 시간대 표기 혼란 (주석 ↔ 실제 불일치) ⚠️

- `CELERY_TIMEZONE = 'America/New_York'` → 모든 `crontab(hour=N)`은 **ET(현재 EDT, UTC-4)** 기준.
- 그러나 일부 주석은 **"UTC"** 라고 적혀 있다. 실제로는 ET로 동작:
  - `chainsight-heat-score-daily` 주석 "매일 07:00 UTC" → **실제 ET 07:00 = UTC 11:00**
  - `chainsight-seed-selection` 주석 "13:00 UTC" → **실제 ET 13:00 = UTC 17:00**
  - `chainsight-neo4j-dirty-sync` 주석 "일요일 04:30 UTC" → **실제 ET 일 04:30**
- 6월은 EDT(UTC-4). **ET → KST 환산 = +13시간** (본 보고서 히트맵에 병기).

> 권장: "UTC" 주석을 "ET"로 정정하거나, 의도가 UTC라면 해당 태스크만 DB에서 timezone 분리.

---

## 1. Rate Limit 초과 구간 분석

### 1-1. API별 태스크 분류 (코드 확인 완료)

| API | 한도 | 의존 태스크 |
|-----|------|------------|
| **FMP** | 300/min, 10,000/day | `update-realtime-prices`(*/5), `update-market-indices`(*/5), `collect-sp500-news-fmp`(×5, 503심볼), `collect-general-news-fmp`(×3), `collect-press-releases-fmp`, `sync-daily-market-movers`, `sync-sp500-financials`(101개), `sync-sp500-eod-prices`(503), `sync-sp500-constituents`, `update-daily-prices`, `refresh-market-pulse-cache`(*/1, 잠재) |
| **Gemini** | 15 RPM, 1500 RPD | `analyze-news-deep`(×6, 50건/회), `keyword-generation-pipeline`, `extract-daily-news-keywords`, `enrich-relationship-keywords`, `thesis-generate-summaries`, `refresh-korean-overviews`(월1회) |
| **FRED** | (관대) | `update-economic-indicators`(×4), `update-economic-calendar` |
| **내부/규칙엔진 (rate limit 무관)** | — | `classify-news-batch`(Engine A/B/C 규칙), `extract-news-relations`(NewsRelationMatcher), chain_sight 관계 태스크 전부, EOD 벡터 연산, ML 학습 |

> **확인 결과**: `classify_news_batch`는 `provider="internal"` 규칙 엔진 — LLM 미사용.
> `extract_news_relations`는 `NewsRelationMatcher.process_recent_news` 키워드 매칭 — LLM/FMP 미사용.
> chain_sight `tasks/` 디렉토리에 Gemini 호출 없음 (통계/그래프 기반).

### 1-2. FMP 초과 위험 구간 🔴

**🔴 H1. `collect-sp500-news-fmp` orchestrator — 503심볼 chord 6배치 병렬**

```python
# services/news/tasks.py:1022
batch_size = 84  # 503/6
chord(collect_sp500_news_fmp_batch.s(batch) for batch in batches)(...)
```

- 6개 배치(각 84심볼)를 **chord로 동시 dispatch**. prefork 워커에서 병렬 실행 시 짧은 구간에 최대 ~503 FMP calls 집중.
- 배치당 84 calls가 1분 내 직렬 호출되면 단일 배치는 한도 내(84<300)지만, **6배치가 겹치고 + 동시간대 시장반복(`*/5` 2종)이 더해지면** 순간 300/min 근접/초과 가능.
- **실행 시각 5회**: ET 06:15 / 10:15 / 13:15 / 15:15 / 17:15
  - **06:15**: 시장 외 → 비교적 안전 (단 06:45 general-news와 인접)
  - **10:15 / 13:15 / 15:15**: ⚠️ **시장시간(9-16)** — `*/5` 가격/지수 호출이 `:15`에 동시 매치 + `refresh-pulse */1` 동시. FMP 동시 압박 최대.

**🟡 H2. 시장시간 `*/5` × 2 + `*/1` 캐시 갱신 상시 부하**

- `update-realtime-prices`(FMP) + `update-market-indices`(FMP): 매 5분 동시 트리거(둘 다 `*/5 9-16`).
- `refresh-market-pulse-cache`: **매 1분**. 내부 `MacroEconomicService.get_market_pulse_dashboard()` 호출 — 캐시 미스 시 FMP/FRED 재호출 가능. 1분 빈도라 누적 호출량 큼.
  - 코드 확인: `cache.delete('macro:market_pulse_full')` 후 재생성 → 매 분 데이터 소스 접근 가능성. **DB read-only인지 외부 API 재호출인지 추가 검증 권장** (rate limit 직결).
- 시장시간(7시간) × 12회/시간(`*/5` 2종 = 24 calls/시간) + `*/1` 60회 → 시간당 호출이 누적. 일일 10,000 cap 대비 여유 확인 필요.

**🟡 H3. ET 17:00~20:00 FMP 배치 집중**

- 17:00 `update-daily-prices` + 17:15 `sp500-news-fmp`(503) + 17:45 `general-news-fmp`
- 18:00 `sync-sp500-eod-prices`(503심볼) ← 가장 무거운 단일 배치
- 20:00 `sync-sp500-financials`(101개)
- 17:15 news(503) ↔ 18:00 eod(503)이 30~45분 내 연속 → 분산되어 있으나 **17:15 배치가 지연되면 18:00 eod와 겹침**.

### 1-3. Gemini 초과 위험 구간 🔴

**🔴 G1. ET `:30` 시각 `analyze-news-deep` 50건/회 — 15 RPM 충돌**

```python
# analyze_news_deep(max_articles=50), hour='8,10,12,14,16,18' minute=30
```

- **50건을 Gemini 2.5 Flash로 순차 분석** → 15 RPM 한도면 최소 50/15 ≈ 3.3분 소요(내부 rate 제어 가정). soft_time_limit=1800s(30분)로 여유는 있으나, **다른 Gemini 태스크와 동시 실행 시 RPM 공유 → 양쪽 모두 throttle**.
- **충돌 지점**:
  - **ET 16:30 `analyze-news-deep`** ↔ **16:45 `extract-daily-news-keywords`** → 주석(`tasks.py:291-292`, audit P0 #8)에 따라 **15분 분산으로 이미 회피 완료**. 단 analyze-deep가 15분 내 못 끝나면 여전히 겹침 (50건 처리가 15분 초과 가능).
  - **ET 18:30 `analyze-news-deep`** ↔ **18:35 `thesis-generate-summaries`(Gemini)** → **5분 간격**. analyze-deep 50건이 5분 내 완료 불가능성 높음 → **RPM 충돌 가능성 높음** 🔴. (주석 audit P0 #15에서 snapshot 직후로 배치했으나 Gemini 동시성은 미고려)
  - **ET 08:00 `keyword-generation-pipeline`(Gemini)** ↔ **08:30 `analyze-news-deep`** → 30분 간격, 비교적 안전.

**🟡 G2. 일일 Gemini RPD 누적**

- `analyze-news-deep` 6회 × 최대 50건 = 300 req/day
- `keyword-generation-pipeline` + `extract-daily-news-keywords` + `enrich-relationship-keywords`(limit=100) + `thesis-generate-summaries`(종목 수만큼)
- `enrich-relationship-keywords`가 limit=100이면 100 req. → **합산 시 1500 RPD에 근접 가능**. 일일 총량 모니터링 권장.

### 1-4. Alpha Vantage 🟢

- **AV 의존 스케줄 태스크 없음**. AV는 `services/news/providers/alphavantage.py` 등 provider로만 존재, beat_schedule에서 직접 호출하는 태스크 미발견.
- → 5 calls/min 제약은 현재 beat 스케줄에서 **리스크 없음**.

---

## 2. Queue 몰림 분석

### 2-1. Queue 배정 현황

| Queue | 태스크 | 비고 |
|-------|--------|------|
| **neo4j** (solo, 동시 1개) | `neo4j-health-check`(*/6h), `sync-news-to-neo4j`(:45 ×6), `cleanup-expired-news-relationships`(4:00), `enrich-relationship-keywords`(5:30), `chainsight-neo4j-dirty-sync`(일 4:30), `sec-sync-dirty-neo4j`(**\*/5 = 24h 상시**) | **solo pool → 직렬 처리** |
| **default** | 나머지 전부 (~80개) | 시장시간 `*/5`,`*/1` 등 |

### 2-2. neo4j queue 밀림 위험 🔴

**solo pool = 동시 1개만 실행.** neo4j queue에 다음이 몰린다:

**🔴 N1. `sec-sync-dirty-neo4j` (*/5, 24시간 상시) 가 queue를 지속 점유**

- 5분마다 실행, `expires=240`(4분). 다른 neo4j 태스크가 실행 중이면 **대기열에 쌓이거나 expire로 유실**.
- 특히 `sync-news-to-neo4j`(:45, max_articles=100)가 4~5분 이상 걸리면 그 사이 `sec-sync-dirty`(:45, :50 트리거)가 밀림.

**🔴 N2. ET 04:00~05:30 neo4j queue 경합 (일요일 최악)**

- 04:00 `cleanup-expired-news-relationships` (neo4j)
- 04:30 `chainsight-neo4j-dirty-sync` (neo4j, 일요일)
- 05:30 `enrich-relationship-keywords` (neo4j, Gemini 동반)
- + `sec-sync-dirty-neo4j` `*/5` 가 04:00,04:05,...,05:30 내내 끼어듦
- → solo pool에서 **직렬화 + cleanup이 길어지면 dirty-sync expire**. 일요일은 chainsight-neo4j-dirty-sync까지 가세.

**🟡 N3. ET `:45` 시각 neo4j 집중**

- `sync-news-to-neo4j`(:45 ×6, hour 8,10,12,14,16,18) + 같은 분 `sec-sync-dirty`(*/5 → :45 매치) → solo에서 직렬. news sync(100건)가 길면 sec-dirty 적체.

**⚠️ N4. chain_sight neo4j sync가 default queue로 감 (queue 미지정)**

- `chainsight-sync-profiles-neo4j`(12:00), `chainsight-sync-relations-neo4j`(12:30)에 `'queue'` 옵션 **없음** → **default queue 실행**.
- Neo4j 쓰기 작업인데 default(prefork)에서 돌면, neo4j queue의 solo 격리 의도와 어긋남. 동일 Neo4j 인스턴스에 default+neo4j 워커가 동시 쓰기 → **경합/락 가능성**. (설계 일관성 검토 권장)

### 2-3. default queue 부하 🟡

- 시장시간(9-16) 매 분: `refresh-pulse`(*/1) 상시 + 매 5분 `*/5` 2종 + 매 10분 portfolio + 매 15분 screener-alerts.
- ET 12:00, 18:00 정각에 단발 태스크 다수 합류 → default 워커 동시성 한도 확인 필요.

---

## 3. 시간대별 API 호출 히트맵 (ET 기준, 평일)

> 분 단위 반복(`*/N`)은 해당 시간대 1회 점유로 카운트. 전역 상시 반복은 별도 표기.
> **전역 상시(24h)**: `sec-sync-dirty-neo4j`(*/5, neo4j), `check-pipeline-alerts`(*/30, default) — 모든 시간대 +2.

```
ET  KST   태스크 수  부하 막대 (단발 트리거 기준, 시장반복 별도 ▓)
00  13:00   0        ·
01  14:00   2        ██                      aggregate-weekly(토)/econ-calendar
02  15:00   3        ███                     sp500-constituents/archive/chainsight-profiles
03  16:00   6        ██████                  cleanup-macro/train-ml/shadow/supply-chain/korean-ovw/co-movement
04  17:00  11        ███████████  🔴         neo4j cleanup + 9개 주간/월간 + dirty-sync(neo4j 경합)
05  18:00   3        ███                     task-results/validation(토)/enrich-kw(Gemini,neo4j)
06  19:00   7        ███████                 econ-ind/daily-news/sp500-news-FMP(503)/cat-high/gen-news-FMP/sec-check/etf
07  20:00   6        ██████                  error-digest/heat-score/cat-med/movers-FMP/cat-low/press-FMP
08  21:00   5+▓      █████                   kw-pipeline(Gemini)/market-news/classify/analyze-deep(Gemini)/news-neo4j
09  22:00   2+▓▓▓▓▓  ██░░░░░  [장개장]        sentiment/news-relations  + 시장반복 5종 시작
10  23:00   5+▓▓▓▓▓  █████░░░░░  🟡          co-mentions/sp500-news-FMP(503):15/classify/analyze-deep:30/news-neo4j:45
11  00:00   1+▓▓▓▓▓  █░░░░░                  relation-confidence
12  01:00   9+▓▓▓▓▓  █████████░░░░░  🔴       econ/market-news/cs-profiles-neo4j/sec-seed/classify/gen-news-FMP/analyze-deep/cs-relations-neo4j/news-neo4j
13  02:00   3+▓▓▓▓▓  ███░░░░░                cat-high/seed-selection/sp500-news-FMP(503):15
14  03:00   5+▓▓▓▓▓  █████░░░░░              cat-med/classify/daily-news/analyze-deep/news-neo4j
15  04:00   2+▓▓▓▓▓  ██░░░░░                 market-news/sp500-news-FMP(503):15
16  05:00   6+▓▓▓▓▓  ██████░░░░░  🟡 [장마감] classify/breadth/analyze-deep:30(Gemini)/heatmap/news-neo4j:45/extract-kw:45(Gemini)
17  06:00   4        ████                    daily-prices-FMP/cat-high/sp500-news-FMP(503):15/gen-news-FMP
18  07:00  12        ████████████  🔴 [최대]  eod-prices-FMP(503)/thesis×4/econ/market-news/eod-pipeline/change%/analyze-deep:30(Gemini)/news-neo4j:45
19  08:00   2        ██                      backfill-accuracy/ml-labels
20  09:00   1        █                       sp500-financials-FMP(101)
21  10:00   0        ·
22  11:00   1        █                       econ-indicators
23  12:00   0        ·
```

(▓ = 시장시간 분단위 반복 5종 동시 가동: realtime-prices, market-indices, market-pulse(*/1), portfolio(*/10), screener-alerts(*/15))

### 피크 시간대 식별

| 순위 | 시각(ET / KST) | 부하 성격 | 핵심 충돌 |
|------|---------------|----------|-----------|
| **1** | **18:00 / 07:00** | 단발 12개 최다 | EOD 파이프라인(eod-prices 503 FMP) + Thesis 4단 체인 + analyze-deep(Gemini) ↔ thesis-summaries(Gemini) 5분 충돌 + news-neo4j |
| **2** | **12:00 / 01:00** | 시장반복 + 단발 9개 | FMP(*/5×2 + general-news) + Gemini(analyze-deep) + neo4j(news/cs-profiles/cs-relations/sec-seed 동시) |
| **3** | **04:00 / 17:00** | neo4j queue 경합 | solo pool에 cleanup+dirty-sync(+일요일 chainsight) 직렬 적체 |
| **4** | **16:00 / 05:00** | 장마감 직후 | 시장반복 + breadth/heatmap + analyze-deep(Gemini) + extract-kw(Gemini) |
| **5** | **10:15·13:15·15:15** | 시장 중 FMP | sp500-news-FMP(503 chord) + 가격 `*/5` 동시 → FMP 순간 압박 |

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 시간 기반 의존 체인 (명시적 의존 아님 → 선행 미완 위험) 🟡

순차 의존을 **고정 시간 간격**으로 처리 → 선행이 늦으면 후속이 빈 데이터로 실행.

**🔴 D1. Thesis EOD 4단 체인 (ET 18:00→18:35, 5~15분 간격)**

```
18:00 thesis-update-readings  (지표 수집)
  └─15분→ 18:15 thesis-calculate-scores   (readings 완료 가정)
       └─15분→ 18:30 thesis-create-snapshots (scores 완료 가정)
            └─5분→ 18:35 thesis-generate-summaries (snapshot 완료 가정, Gemini)
```
- 18:00 readings가 외부 데이터 수집을 15분 내 못 끝내면 **18:15 scores가 stale readings로 계산**.
- 18:35 summaries(Gemini)는 snapshot 후 5분뿐 → snapshot 지연 시 빈 입력. + analyze-deep(18:30 Gemini)와 RPM 경합까지.
- → **Celery chain/chord로 명시적 의존 전환 권장** (현재 시간 간격 의존).

**🔴 D2. EOD Dashboard 체인**

```
18:00 sync-sp500-eod-prices (503심볼 FMP)
  └─30분→ 18:30 run-eod-pipeline (가격 완료 가정)
       └─30분→ 19:00 backfill-signal-accuracy (파이프라인 완료 가정)
18:30 update-sp500-change-percent (eod-prices 의존, DailyPrice 기반)
```
- 503심볼 FMP 수집이 30분 초과하면 18:30 eod-pipeline이 불완전 가격으로 실행.

**🟡 D3. Chainsight 일일 체인 (ET 07:00→13:00)**

```
07:00 heat-score → (10:00 co-mentions → 11:00 relation-confidence)
  → 12:00 sync-profiles-neo4j → 12:30 sync-relations-neo4j → 13:00 seed-selection
12:00 sec-seed-relations-to-chainsight (동시)
```
- seed-selection(13:00)이 sync-relations-neo4j(12:30) 완료 의존. 30분 간격.

**🟡 D4. Chainsight 토요일 새벽 체인 (ET 02:00→05:00)**

```
02:00 all-profiles → 03:00 price-co-movement → 04:00 stale-decay
  → 04:30 aggregate-profiles → 05:00 validation-weekly
```
- all-profiles(전 종목 프로파일)가 1시간 초과하면 price-co-movement와 겹침.

**🟡 D5. 뉴스 파이프라인 체인 (2시간 주기, :15→:30→:45)**

```
:15 classify-news-batch (규칙) → :30 analyze-news-deep (Gemini) → :45 sync-news-to-neo4j
```
- 15분 간격. analyze-deep(50건)가 15분 초과 시 sync-neo4j가 미분석 데이터 동기화.
- 선행 수집(collect-*)도 같은 hour 내 → 수집 지연 시 classify가 빈 큐.

### 4-2. 동시 실행 데이터 경합 🟡

- **🟡 R1. ET 12:00·12:30 Neo4j 동시 쓰기**: `chainsight-sync-profiles-neo4j`(12:00, default) + `sec-seed-relations`(12:00) + `chainsight-sync-relations-neo4j`(12:30, default) + `sync-news-to-neo4j`(12:45, neo4j queue). default와 neo4j 워커가 **동일 Neo4j에 동시 쓰기** → 락 경합 (N4 참조).
- **🟡 R2. 일요일 ET 03:00~05:00 ML 파이프라인 동시**: train-importance(3:00) + shadow-report(3:30) + check-auto-deploy(4:00) + weekly-ml-report(4:15) + monitor-ml(4:20) + train-lightgbm(4:30). 모델 파일 read/write 경합 가능 — 순서 의존이면 시간 간격으로만 보장됨.
- **🟢 R3. update-realtime-prices / update-daily-prices 동일 태스크**: 둘 다 `update_realtime_with_provider` 호출. 17:00 daily는 `*/5 9-16` 종료(16:55) 후라 시간 겹침 없음. 안전.

### 4-3. expires 설정 주의 🟡

- `sec-sync-dirty-neo4j` expires=240(4분)인데 `*/5` 주기 → neo4j solo 적체 시 **실행 전 만료되어 누락**. dirty 동기화가 5분 내 처리 못 되면 다음 주기로 미뤄지지만 그 사이 dirty 누적.
- `refresh-market-pulse-cache`는 expires 미설정 → 적체 시 무한 대기 가능.

---

## 5. 요약 — 우선순위별 권고 (읽기 전용, 조치 제안만)

| # | 심각도 | 항목 | 권고 |
|---|--------|------|------|
| 1 | 🔴 | DB drift 미검증 | **본 분석 유효성의 전제** — `PeriodicTask` vs dict diff 먼저 수행 (버그 #28) |
| 2 | 🔴 | ET 18:30 analyze-deep(Gemini) ↔ 18:35 thesis-summaries(Gemini) 5분 충돌 | Gemini RPM 공유 → summaries를 19:00 이후로 이동 검토 |
| 3 | 🔴 | sp500-news-FMP(503 chord) ↔ 시장 `*/5` (10/13/15:15) | chord 배치 간 rate limit gate, 또는 시장 외 시각 이동 |
| 4 | 🔴 | neo4j solo queue 적체 (sec-dirty */5 + :45 news-sync + 04시대) | sec-dirty 주기 완화(*/10) 또는 neo4j 워커 동시성/별도 큐 분리 검토 |
| 5 | 🟡 | Thesis/EOD 시간 간격 의존 (D1/D2) | Celery `chain`/`chord` 명시적 의존 전환 |
| 6 | 🟡 | chainsight neo4j sync가 default queue (N4) | `'queue':'neo4j'` 명시로 일관성 확보 |
| 7 | 🟡 | refresh-market-pulse-cache */1 FMP/FRED 재호출 여부 | 캐시 갱신이 외부 API 호출인지 검증 (rate limit 직결) |
| 8 | 🟡 | Gemini RPD 1500 근접 가능 (G2) | 일일 Gemini 호출 총량 모니터링 |
| 9 | 🟢 | "UTC" 주석 ↔ ET 실제 동작 불일치 | 주석 정정 (chainsight 3개 태스크) |
| 10 | 🟢 | Alpha Vantage | beat 스케줄 내 직접 의존 없음 — 리스크 없음 |

---

## 부록 A. 분석 방법 / 한계

- **분석 대상**: `config/celery.py:141-820` dict 87개 항목 + 호출 코드 직접 확인(`services/news/tasks.py`, `services/serverless/tasks.py`, `apps/market_pulse/tasks/macro.py`, `thesis/tasks/summary.py`).
- **API 분류 근거**: 태스크 함수 내 provider/LLM 호출 코드 확인 (classify=internal, extract-relations=matcher 규칙엔진 확인 완료).
- **한계**:
  1. **DB `PeriodicTask` 실제 상태 미조회** — dict 기준 설계 의도 분석. 운영 정합성은 별도 diff 필요.
  2. 각 태스크의 **실제 실행 소요시간(런타임 프로파일) 미측정** — 의존 체인 위반은 "가능성"으로 기술.
  3. **워커 동시성(prefork concurrency) 미확인** — chord 6배치 동시 실행 정도가 워커 수에 의존.
  4. `refresh-market-pulse-cache`의 외부 API 재호출 여부는 코드상 단정 불가(추가 검증 표기).
