# Celery Beat 스케줄 감사 보고서

- **작성일**: 2026-06-15
- **대상**: `config/celery.py` → `app.conf.beat_schedule` (선언적 reference dict)
- **유형**: 읽기 전용 감사 (코드 수정 없음)
- **태스크 총수**: 72개 정의 (라인 141~820)

---

## 0. 감사 전제 — 반드시 먼저 읽을 것

이 보고서의 결론을 해석하기 전에 두 가지 구조적 전제를 알아야 한다.

### 전제 A — 이 dict는 런타임에 무시된다 (진실의 소스 불일치)

`config/celery.py` 라인 123~140 주석이 명시하듯:

```
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

설정 때문에 **실제 실행 스케줄의 진실의 소스는 DB의 `django_celery_beat.PeriodicTask` 테이블**이다.
이 `beat_schedule` dict는 "원래 설계된 스케줄의 선언적 reference"일 뿐이다.

> ⚠️ **따라서 본 감사는 "설계 의도(dict)"에 대한 것이며, "실제 운영 스케줄(DB)"과 drift가 있을 수 있다.**
> 정확한 운영 부하를 확정하려면 아래 diff가 선행되어야 한다 (common-bugs #28):
>
> ```python
> # python manage.py shell
> from django_celery_beat.models import PeriodicTask
> db_names = set(PeriodicTask.objects.values_list('name', flat=True))
> # config dict 키 72개와 db_names 비교 — 양방향 차집합 확인
> ```
> 라인 135~137에 2026-04-24 복구 이력(누락 2건 DB 등록)이 기록돼 있어 drift 전례가 실재함.

### 전제 B — 타임존: `crontab(hour=N)`은 **ET(America/New_York)** 기준

`config/settings.py:496` → `CELERY_TIMEZONE = 'America/New_York'`

- 따라서 dict의 모든 `crontab(hour=...)`는 **ET 기준 시각**으로 실행된다.
- ⚠️ **주석의 "UTC" 표기는 실행 시각과 불일치한다.** 일부 Chain Sight/SEC 태스크 주석이
  "07:00 UTC", "13:00 UTC", "04:30 UTC" 라고 적었지만 실제 실행은 **ET 07:00 / 13:00 / 04:30**이다.
  - 해당: `chainsight-heat-score-daily`(라인 747 "07:00 UTC"), `chainsight-seed-selection`(라인 754 "13:00 UTC"),
    `chainsight-neo4j-dirty-sync`(라인 761 "04:30 UTC").
  - 상대 실행 순서(heat-score 07:00 → seed 13:00)는 모두 ET로 통일 해석되므로 **유지**되나,
    운영자가 UTC로 착각하면 실제 시각을 4~5시간 오해할 수 있다 → **문서 신뢰성 P2 결함**.

> 본 보고서의 모든 시각은 **ET 기준**으로 통일 표기한다 (KST = ET + 13~14h).

---

## 1. 인벤토리 요약

| 분류 | 태스크 수 | 비고 |
|------|----------|------|
| 장중 고빈도 반복 (`*/1`~`*/15`, hour 9-16) | 5 | refresh-cache, realtime-prices, market-indices, portfolio-values, screener-alerts |
| 전일 상시 반복 (`*/5`, `*/30`, `*/6h`) | 3 | sec-sync-dirty-neo4j, check-pipeline-alerts, neo4j-health-check |
| 2시간 배치 (8,10,12,14,16,18시) | 3 | classify / analyze-deep / sync-news-neo4j |
| 정시 단발 (특정 hour, 평일/매일) | 약 50 | 뉴스 수집·EOD·thesis·chainsight 등 |
| 주간 (토/일/월) | 약 13 | ML 학습, chainsight 프로파일, validation |
| 월간 (1일/15일/16일) | 6 | constituents, supply-chain, institutional, patent, sec-filings, korean-overviews |

### API 의존성 매핑 (tasks.py grep 기준)

| API | 한도 | Beat에서 의존하는 태스크 (대표) |
|-----|------|-------------------------------|
| **FMP** (Starter) | 300/min, 10k/day | realtime-prices, market-indices, daily-prices, sp500-financials, sp500-eod, sp500-constituents, market-movers, etf-holdings, **collect-sp500-news-fmp ×5**, press-releases-fmp, general-news-fmp ×3 |
| **Gemini** (Free) | 15 RPM, 1500 RPD | keyword-generation-pipeline, **analyze-news-deep ×6**, extract-daily-news-keywords, extract-news-relations, enrich-relationship-keywords, thesis-generate-summaries, refresh-korean-overviews, (chainsight-co-mentions 추정) |
| **Alpha Vantage** | 5/min | **Beat 태스크에서 직접 의존 없음** (`grep -i alpha_vantage --include=tasks.py` → 0건) |
| FRED | 관대 | update-economic-indicators(×4/일), update-economic-calendar |
| SEC EDGAR | 관대(10 rps) | supply-chain, institutional, regulatory, patent, sec-check-new-filings, sec-sync-dirty |
| News (Marketaux/Finnhub) | 별도 | collect-daily/market/category-news |

---

## 2. 시간대별 ASCII 히트맵 (ET 기준, 평일 Mon–Fri)

### 2-A. 전체 태스크 "시간당 실행 횟수" (반복 포함)

장중(09–16) `refresh-market-pulse-cache`가 분당 1회(60/h)라 다른 모든 부하를 압도하므로,
스케일 왜곡을 막기 위해 **상시 반복분(아래)을 제외한 "정시 단발 태스크 시작 수"**로 막대를 그린다.

```
ET  정시단발 시작 태스크 수 (평일)              피크
00 |                                            0
01 |█                                           1   economic-calendar
02 |                                            0   (월간/주말만)
03 |                                            0   (월간/주말만)
04 |█                                           1   cleanup-expired-news-rel
05 |                                            0   (주말만 / enrich 05:30은 매일→ +1)
06 |██████                                      6   ★ 장전 뉴스 러시
07 |█████                                       5   error-digest·movers·category·press
08 |█████                                       5   keyword-pipeline·market-news·classify·analyze·sync
09 |██                                          2   sentiment·news-relations  + 장중반복 개시
10 |████                                        4   co-mentions·sp500-news·classify·analyze
11 |█                                           1   relation-confidence
12 |███████                                     7   ★★ 정오 피크 (아래 §5)
13 |███                                         3   category·seed·sp500-news
14 |███                                         3   category·daily-news·배치
15 |██                                          2   market-news·sp500-news
16 |██████                                      6   breadth·heatmap·keywords·배치
17 |████                                        4   daily-prices·category·sp500-news·general-news
18 |██████████                                 10   ★★★ 최대 피크 (아래 §5)
19 |██                                          2   ml-labels·backfill-accuracy
20 |█                                           1   sp500-financials
21 |                                            0
22 |█                                           1   economic-indicators
23 |                                            0
```

> ⚠️ **주말 04시는 별도 핫스팟**: 토/일에 ML 학습·chainsight 프로파일·patch 정리 등 **11개**가
> 04:00–04:30 창에 몰린다 (check-auto-deploy, cleanup-news-rel, stale-decay, institutional[16일],
> regulatory[월], weekly-ml-report, monitor-ml, train-lightgbm, aggregate-profiles, build-patent[1일],
> neo4j-dirty-sync). 평일 히트맵엔 안 보이지만 운영상 가장 조밀한 배치 윈도우다.

### 2-B. 상시 반복 태스크 "시간당 실행 횟수"

```
태스크                         빈도        00-08  09-16(장중)  17-23
sec-sync-dirty-neo4j (*/5)     12/h        12/h    12/h        12/h   ← 24h 상시, 하루 288회
check-pipeline-alerts (*/30)    2/h         2/h     2/h         2/h   ← 24h 상시
neo4j-health-check (*/6h)       0~1/h      06시1회  12시1회     18시1회
refresh-market-pulse-cache(*/1) -            -      60/h          -   ← 장중만, 압도적
update-realtime-prices (*/5)    -            -      12/h          -
update-market-indices (*/5)     -            -      12/h          -
calculate-portfolio-values(*/10)-            -       6/h          -
check-screener-alerts (*/15)    -            -       4/h          -
```

### 2-C. 외부 API 호출 집중 히트맵 (rate-limit 관점, 평일)

`F`=FMP 의존, `G`=Gemini 의존 태스크가 해당 시간에 **시작**되는 개수.

```
ET   FMP(F)            Gemini(G)        충돌메모
06   FFF   (3)         ·                sp500-news·etf·general-news
07   FF    (2)         ·                movers·press-releases
08   ·                 GG   (2)         keyword-pipeline(:00)+analyze-deep(:30) 30분분리 OK
09   ·                 G    (1)         extract-news-relations
10   F     (1)         G(?) (1)         sp500-news(:15)+co-mentions(:00)
12   F     (1)         G    (1)         general-news(:30)+analyze-deep(:30) ⚠ 동분(:30)
13   F     (1)         ·                sp500-news
15   F     (1)         ·                sp500-news
16   ·                 GG   (2)         analyze-deep(:30)+extract-keywords(:45) 15분분리 OK(P0#8회피)
17   FFF   (3)         ·                daily-prices·sp500-news·general-news
18   FF    (2)         G    (1)         sp500-eod(:00)+thesis-summaries(:35)
20   F     (1)         ·                sp500-financials
+상시 sec-sync-dirty(SEC, */5)는 전 시간대 12/h
```

---

## 3. Rate Limit 분석

### 3-1. FMP (300 calls/min, 10,000 calls/day)

| 구간 | 평가 | 근거 |
|------|------|------|
| 장중 `*/5` realtime+indices 동시 | 🟢 **안전** | `update_realtime_with_provider`는 `Portfolio…distinct()[:10]` → 최대 10콜/실행. `update_market_indices`는 `get_all_market_quotes()` **단일 bulk 1콜**. 합산 ~11콜/5분 ≪ 300/min |
| **`collect-sp500-news-fmp` ×5회/일** | 🟡 **잠재 위험 (P1)** | `collect_sp500_news_fmp_orchestrator`(라인 1022)가 503종목을 **84개씩 6배치로 `chord` 동시 dispatch**. 배치 내부가 심볼당 호출이면 **순간 최대 503콜**이 짧은 창에 집중. macOS solo pool에선 순차라 안전하나, **운영 Linux prefork에선 6배치 동시 → 분당 300 초과 가능**. 배치 내 호출 방식(bulk vs per-symbol)·`rate_limit` 데코레이터 미확인 → 검증 필요 |
| 일일 총량 | 🟡 **모니터링** | sp500-news 5회 + financials(101/일) + eod(503) + movers + etf + general-news ×3 + 장중반복. per-symbol 호출이 섞이면 10k/day 한도 압박 가능. 일일 FMP 콜 카운터 로깅 권고 |

> ✅ **권고**: orchestrator 배치(`collect_sp500_news_fmp_batch`)가 per-symbol 호출인지 bulk인지 확인하고,
> per-symbol이면 6배치 `chord`를 순차 또는 `countdown` 분산으로 변경 검토.

### 3-2. Gemini (15 RPM, 1500 RPD)

| 구간 | 평가 | 근거 |
|------|------|------|
| 16:30 analyze-deep ↔ 16:45 extract-keywords | 🟢 **안전(설계됨)** | 라인 291~292 주석: 과거 동시호출로 15 RPM 2배 초과 → **15분 분산으로 회피(audit P0 #8, 2026-04-26)**. 이미 해결된 패턴 |
| **12:30 analyze-deep ↔ 12:30 동분 태스크** | 🟡 **점검 권고** | analyze-news-deep-batch는 `8,10,12,14,16,18시 :30`. 12:30엔 `collect-general-news-fmp-noon`(:30, FMP)와 동분이나 다른 API라 RPM 무관. 단 `chainsight-co-mentions`(10:00)·`extract-news-relations`(09:00)가 Gemini면 인접 시간대 누적 RPM 확인 필요 |
| **analyze-deep 내부 50건 처리** | 🟡 **RPM 내부 의존** | `max_articles=50`. 50건을 단일 태스크에서 처리 시 내부에 15 RPM throttle이 없으면 분당 초과. 태스크 내부 rate-limit 유무 미확인 |
| **일일 RPD 누적** | 🟡 **모니터링 (P1)** | analyze-deep 6회×최대50 = 최대 300 + enrich(limit=100) + keyword-pipeline + extract-keywords + extract-news-relations + co-mentions + thesis-summaries(스냅샷 종목수만큼) → **합산 수백~1000+/일**. 1500 RPD 한도에 근접 가능. 일일 Gemini 호출 카운터 권고 |

### 3-3. Alpha Vantage (5 calls/min)

🟢 **해당 없음**. `grep -i alpha_vantage --include=tasks.py` 결과 **Beat 태스크에서 직접 의존하는 태스크 0건**.
AV는 온디맨드(API 요청 경로)에서만 쓰이는 것으로 보이며, 스케줄 간격 검증 대상이 없다.
(만약 향후 AV 의존 배치를 추가한다면 12초 간격 강제가 필수임을 명시 — CLAUDE.md 규칙.)

---

## 4. Queue 몰림 분석 (default vs neo4j)

`task_routes`(라인 43~61)로 neo4j 큐에 격리된 태스크 + beat options `queue:'neo4j'` 지정분.
**neo4j 워커는 `--pool=solo` → 동시 1개만 처리** (직렬 큐).

### 4-1. neo4j 큐에 들어가는 Beat 태스크

| 태스크 | 스케줄(ET) | 비고 |
|--------|-----------|------|
| `sec-sync-dirty-neo4j` | **`*/5` 상시** | ⚠️ **주의**: beat options엔 큐 미지정이나 `task_routes`(라인 60)에 `sync_dirty_to_neo4j → neo4j` 등록됨 → **실제 neo4j 큐로 라우팅**. 5분마다 solo 큐 점유 (하루 288회) |
| `sync-news-to-neo4j` | 8,10,12,14,16,18시 :45 | options queue:neo4j |
| `cleanup-expired-news-relationships` | 매일 04:00 | options queue:neo4j |
| `enrich-relationship-keywords` | 매일 05:30 | options queue:neo4j + Gemini |
| `neo4j-health-check` | `*/6h` :00 | options queue:neo4j |
| `chainsight-sync-profiles-neo4j` | 매일 12:00 | task_routes |
| `chainsight-sync-relations-neo4j` | 매일 12:30 | task_routes |
| `chainsight-neo4j-dirty-sync` | 일 04:30 | options queue:neo4j |

### 4-2. neo4j solo 큐 경합 위험 구간

```
ET 12:00 ┌─ chainsight-sync-profiles-neo4j  (대형: 프로파일 전량)
   12:00 ├─ sec-sync-dirty-neo4j (*/5 상시 — 12:00,12:05,…)
   12:30 ├─ chainsight-sync-relations-neo4j (대형: 관계 전량)
   12:30 └─ sec-sync-dirty-neo4j (12:30)
```

> 🟡 **P1 — neo4j 큐 정오 직렬 적체**: solo pool(동시 1개)에서 12:00 sync-profiles(대형)가 길어지면
> 그 뒤로 `sec-sync-dirty`(5분 주기) + 12:30 sync-relations가 **순차 대기**한다.
> sync-profiles가 30분 넘게 걸리면 12:30 sync-relations 시작이 밀리고,
> 그 사이 `sec-sync-dirty`가 매 5분 큐에 쌓여 **적체 → expires(240s) 만료로 일부 스킵** 가능.
> (`sec-sync-dirty` options `expires:240` → 4분 안에 못 잡으면 폐기되어 dirty 동기화 누락 위험.)

> 🟢 **참고 — 의도된 설계**: `neo4j-health-check`가 `*/5분 → */6시간`으로 변경된 이력(라인 216 주석)은
> SIGSEGV 워커 소모를 줄이려는 것. solo 큐 부하를 낮추는 올바른 방향.

### 4-3. default 큐

장중 `refresh-market-pulse-cache`(60/h) + realtime/indices/portfolio가 default 큐를 점유하나,
이들은 가볍고(캐시 재생성/bulk 1콜) 충돌 영향 작음. **default 큐의 진짜 부담은 18시 피크(§5).**

---

## 5. 스케줄 겹침 / 의존성 분석

### 5-1. ★★★ 18:00–18:35 ET — 최대 피크 (default 큐 집중)

```
18:00 ├─ update-economic-indicators (FRED)
      ├─ collect-market-news-evening (News)
      ├─ sync-sp500-eod-prices (FMP, 503종목 대형) ──────┐ 선행
      └─ thesis-update-readings (지표수집) ──┐           │
18:15 ├─ thesis-calculate-scores ───────────┘ 의존        │
      └─ analyze-news-deep-batch(:30 대기)                │
18:30 ├─ update-sp500-change-percent ◀── DailyPrice 의존 ─┘ ⚠
      ├─ run-eod-pipeline ◀────────────── EOD가격 의존 ───┘ ⚠
      └─ thesis-create-snapshots+alerts ◀─ scores 의존
18:35 └─ thesis-generate-summaries (Gemini) ◀─ snapshot 의존
```

> 🔴 **P0 후보 — 18:00 EOD sync vs 18:30 소비자의 30분 의존**:
> - `sync-sp500-eod-prices`(18:00, **503종목 FMP**)가 **30분 내 완료돼야**
>   `update-sp500-change-percent`(18:30, "EOD sync 직후" 주석)와 `run-eod-pipeline`(18:30, "장 마감+2.5h, EOD 동기화 이후" 주석)이 신선한 데이터로 동작.
> - **barrier(체이닝) 없이 시각 오프셋(30분)만으로 의존을 표현** → EOD sync가 지연되면
>   `update-sp500-change-percent`가 **전일/부분 데이터로 계산**할 수 있다 (silent staleness).
> - 동시에 18:00엔 `thesis-update-readings`도 시작 → thesis가 EOD 가격에 의존한다면 18:00 동시 시작은
>   **선행-후행이 같은 시각** → 경합. (thesis-readings가 가격 외 지표만 보면 무관.)
>
> ✅ **권고**: 18:00 sync-sp500-eod-prices → 18:30 소비자들을 **Celery `chord`/`chain`으로 체이닝**하거나,
> 소비자 태스크 진입부에 "오늘자 EOD 적재 완료 여부" 가드를 두어 staleness를 방지.

### 5-2. ★★ 12:00 ET — 정오 피크 (멀티 API + neo4j)

```
12:00 ├─ update-economic-indicators (FRED)
      ├─ collect-market-news-noon (News)
      ├─ chainsight-sync-profiles-neo4j (neo4j solo) ──┐
      ├─ sec-seed-relations-to-chainsight              │ §4.2 경합
      └─ sec-sync-dirty-neo4j (*/5, neo4j solo) ────────┤
12:30 ├─ chainsight-sync-relations-neo4j (neo4j solo) ─┘
      ├─ collect-general-news-fmp-noon (FMP)
      └─ analyze-news-deep-batch (Gemini)
```

다중 API(FRED/News/FMP/Gemini)는 서로 한도 독립이라 rate-limit 충돌은 없으나,
**neo4j solo 큐 적체(§4.2)**가 이 구간의 핵심 리스크.

### 5-3. Chain Sight 일일 의존 체인 — 🟢 순서 정상

```
07:00 heat-score ─→ 10:00 co-mentions ─→ 11:00 relation-confidence
                                          ─→ 12:00 sync-profiles ─→ 12:30 sync-relations
                                          ─→ 13:00 seed-selection
```
시각 오프셋으로 선행→후행 순서가 모두 보존됨(heat 07 < seed 13, co-mention 10 < confidence 11 < sync 12 < seed 13).
단 **§5.1과 동일하게 barrier 없는 시각 의존**이라, 선행이 길어지면 후행이 부분 데이터로 돌 위험은 공통.

### 5-4. 주말 04:00–04:30 — 🟡 ML 배치 직렬 의존

```
일요일: 03:00 train-importance ─→ 03:30 shadow-report ─→ 04:00 check-auto-deploy
        ─→ 04:15 weekly-ml-report ─→ 04:20 monitor-ml ─→ 04:30 train-lightgbm
```
15~30분 간격의 직렬 의존 체인. 학습(train-importance/lightgbm)이 길어지면 뒤 리포트가 밀림.
주말이라 사용자 영향 작으나, **동일하게 barrier 없는 시각 의존** 패턴.

---

## 6. 발견사항 우선순위 종합

| ID | 심각도 | 발견 | 위치 |
|----|--------|------|------|
| F-1 | 🔴 **P0(검증요)** | dict ≠ DB 진실의 소스. 본 감사 결론은 PeriodicTask DB diff로 재확인 필요 | 라인 123~140 |
| F-2 | 🟠 **P1** | 18:00 EOD sync → 18:30 소비자 30분 의존이 barrier 없는 시각 오프셋. 지연 시 silent staleness | §5.1 |
| F-3 | 🟠 **P1** | `collect-sp500-news-fmp` orchestrator 6배치 chord 동시 dispatch → Linux prefork에서 FMP 300/min 순간 초과 가능 | 라인 1042~1049 |
| F-4 | 🟠 **P1** | neo4j solo 큐 12:00 적체 → `sec-sync-dirty`(expires 240s) 만료 스킵 위험 | §4.2 |
| F-5 | 🟡 **P1** | Gemini 일일 RPD 누적(수백~1000+) 1500 한도 근접 가능. 카운터 부재 | §3.2 |
| F-6 | 🟢 **P2** | 주석 "UTC" 표기 ≠ 실제 ET 실행. 운영자 시각 오해 소지 | 라인 747/754/761 |
| F-7 | 🟢 **양호** | 16:30/16:45 Gemini 15분 분산은 과거 P0#8을 올바르게 해결한 설계 | 라인 291~295 |
| F-8 | 🟢 **양호** | 장중 `*/5` FMP 부하는 bulk/포트폴리오 제한으로 한도 대비 충분히 여유 | §3.1 |

---

## 7. 권고 (조치는 본 감사 범위 밖 — 제안만)

1. **(F-1 선행)** `PeriodicTask` ↔ config dict 키 72개 diff를 운영에서 1회 실행해 drift 0 확인.
   정기 drift 체크를 `manage.py` 커맨드로 자동화 검토.
2. **(F-2)** 18:00 EOD sync → 18:30 소비자 체인을 `chain`/`chord`로 묶거나, 소비자 진입부에
   "당일 EOD 적재 완료" 가드 추가.
3. **(F-3)** `collect_sp500_news_fmp_batch` 내부 호출이 per-symbol이면 6배치 chord를
   `countdown` 분산 또는 순차로 전환. FMP 일일 콜 카운터 로깅.
4. **(F-4)** neo4j 큐 12:00 대형 동기화 구간에 `sec-sync-dirty` `expires`를 늘리거나(240s→연장),
   대형 sync를 비-피크 시각으로 이동.
5. **(F-5)** Gemini 일일 호출 카운터 + 1500 RPD 80% 알림 추가.
6. **(F-6)** 주석의 "UTC"를 "ET"로 정정 (문서 신뢰성).

---

*본 보고서는 `config/celery.py`의 선언적 dict와 `tasks.py` 일부 구현 확인에 근거한다.
실제 운영 부하 수치는 PeriodicTask DB 및 호출 로그로 교차검증해야 확정된다.*
