# Beat Schedule 감사 보고서

- **대상 파일**: `config/celery.py` (`app.conf.beat_schedule`)
- **감사 일자**: 2026-06-01
- **감사 모드**: 읽기 전용 (코드 변경 없음)
- **태스크 엔트리 수**: 71개 (`grep -c 'schedule'` = 90, 단 `crontab`/주석 매치 포함 — 실제 beat 엔트리는 71개)

---

## ⚠️ 0. 감사의 대전제 (반드시 먼저 읽을 것)

### 0-1. 이 dict는 **런타임에 무시된다**

`config/settings.py:490`:
```python
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

DatabaseScheduler가 활성화되어 있으므로 **진실의 소스는 DB의 `django_celery_beat.PeriodicTask` 테이블**이다.
`config/celery.py`의 `beat_schedule` dict는 파일 주석(L123~140)이 명시하듯 **"원래 설계된 스케줄의 선언적 reference"**일 뿐이다.

> **따라서 본 보고서의 모든 분석은 "설계 의도(intended schedule)"에 대한 것이다.**
> 실제 운영 중 스케줄과 drift가 있을 수 있다 (common-bug #28). 실제 부하를 확정하려면 아래 명령으로 DB를 대조해야 한다:
>
> ```bash
> python manage.py shell -c "
> from django_celery_beat.models import PeriodicTask
> db = set(PeriodicTask.objects.values_list('name', flat=True))
> import config.celery as c
> cfg = set(c.app.conf.beat_schedule.keys())
> print('DB에만 존재:', sorted(db - cfg))
> print('config에만 존재(=실행 안 됨):', sorted(cfg - db))
> "
> ```

### 0-2. 타임존 = **America/New_York** (현재 6월 = EDT, UTC-4)

`config/settings.py:489` → `CELERY_TIMEZONE = 'America/New_York'`
(참고: Django `TIME_ZONE = 'Asia/Seoul'`이지만 Celery beat는 `CELERY_TIMEZONE`을 따른다.)

**모든 `crontab(hour=N)`은 NY 로컬 시각으로 해석된다.** 본 보고서의 히트맵·시각은 전부 **NY 시간(ET)** 기준이다.
KST 환산은 **ET + 13h** (6월 EDT 기준).

---

## 1. Rate Limit 초과 구간 분석

### 1-1. FMP (Starter: 300 calls/min, 10,000 calls/일)

FMP 의존(또는 강하게 의심되는) 스케줄 태스크:

| 시각(ET) | 태스크 | 비고 |
|---|---|---|
| `*/5 09–16` | `update-realtime-prices` | 시장시간 5분마다 |
| `*/5 09–16` | `update-market-indices` | 시장시간 5분마다 |
| 06:15/10:15/13:15/15:15/17:15 | `collect-sp500-news-fmp-*` (5회) | **S&P500 전체 순회** — 건당 호출 多 |
| 06:45/12:30/17:45 | `collect-general-news-fmp-*` (3회) | |
| 07:30 | `sync-daily-market-movers` | |
| 07:45 | `collect-press-releases-fmp` | max_symbols=50 |
| 16:30 | `calculate-market-breadth` | S&P500 가격 집계 |
| 16:35 | `calculate-sector-heatmap` | |
| 17:00 | `update-daily-prices` | |
| 18:00 | `sync-sp500-eod-prices` | **S&P500 EOD 일괄** |
| 20:00(평일) | `sync-sp500-financials` | 101개/일 순환 |
| Mon 06:00 | `sync-etf-holdings` | |

**평가**:
- **분당 300 한도 위반 가능성은 낮음.** 핵심 대량 태스크는 Celery 레벨 throttle이 걸려 있다:
  - `update_financials_with_provider` → `@shared_task(rate_limit="6/m")` (`packages/shared/stocks/tasks.py:550`)
  - FMP 대량 뉴스 계열 → `rate_limit="100/m"` (`services/news/tasks.py:974`)
- **단, 동일 분(minute) 충돌 구간 주의**:
  - **`xx:15` 슬롯**이 상습 충돌점이다. `collect-sp500-news-fmp-*`(:15)가 `classify-news-batch`(:15)와 같은 분에 시작. 둘 다 FMP가 아니더라도, sp500-news는 S&P500 전수 순회라 단일 태스크 내부 호출량이 가장 큼.
  - **18:00 슬롯**: `sync-sp500-eod-prices`(S&P500 EOD 일괄) + `update-economic-indicators`(FRED) + `collect-market-news-evening`이 동시 시작 → FMP 동시 압박 최고점.
- **일일 10,000 한도**: 5분 간격 가격(09–16 = 7시간 → ~84회×2태스크) + EOD 일괄 + 뉴스 5회 순회가 합산되면 일일 한도에 근접할 수 있음. **DB 대조 후 실제 호출량 카운트 권장** (현 보고서로 확정 불가).

### 1-2. Gemini (Free: 15 RPM, 1500 RPD)

Gemini/LLM 의존 태스크:

| 시각(ET) | 태스크 | 내부 호출량 |
|---|---|---|
| 05:30 | `enrich-relationship-keywords` | limit=100 (neo4j 큐) |
| 08:00 | `keyword-generation-pipeline` | gainers |
| 08:30/10:30/12:30/14:30/16:30/18:30 | `analyze-news-deep-batch` (6회) | **max_articles=50** |
| 08:15/10:15/12:15/14:15/16:15/18:15 | `classify-news-batch` (6회) | hours=3 (규칙+LLM) |
| 09:00 | `extract-news-relations` | 24h |
| 10:00 | `chainsight-co-mentions` | days_back=7 |
| 16:45 | `extract-daily-news-keywords` | |
| 18:35 | `thesis-generate-summaries` | |
| 매월1일 03:00 | `refresh-korean-overviews-monthly` | 대량 |

**평가**:
- ✅ **`analyze-news-deep`는 내부에서 4초 간격 throttle**(`services/news/tasks.py:562` "4초 간격으로 RPM 준수") → 15 calls/min을 단일 태스크 내에서 자체 준수. 50건이라도 ~3.3분에 걸쳐 분산되므로 단일 태스크 RPM 위반은 회피.
- ⚠️ **분당 동시 LLM 태스크 누적 위험은 throttle 밖에 존재**. 예: `:30` 슬롯에서 `analyze-news-deep`(LLM)가 도는 동안 다른 LLM 태스크가 겹치면 Gemini 계정 전체 RPM(15)이 합산 초과될 수 있다. throttle은 태스크 **내부**에만 작동하고 **태스크 간**에는 작동하지 않음.
  - 이미 알려진 사례: `extract-daily-news-keywords`를 16:30 → **16:45로 15분 분산**시킨 주석(L290~296, audit P0 #8)이 정확히 이 "태스크 간 Gemini 2배 초과" 문제를 푼 흔적이다. 동일 패턴이 다른 슬롯에서 재발할 수 있음.
- ⚠️ **RPD 1500**: 6회 deep-analyze(각 ≤50) = 최대 300 + classify 6회 + keyword + co-mention + enrich(100) + summaries + relations. 일일 누적이 수백~1000건대로 추정 → 1500 RPD의 절반 이상 소진 가능. **실측 카운트 권장**.

### 1-3. Alpha Vantage (5 calls/min)

- **전용 스케줄 태스크 없음.** AV는 멀티 프로바이더 뉴스 수집의 한 provider로만 존재(`services/news/providers/alphavantage.py`, `models.py`).
- `collect_daily_news` / `collect_market_news`가 provider 라우팅 시 AV로 분기하면 5/min 제약을 받는다. 코드상 `time.sleep(2)`(`tasks.py:149,431`) 등 간격 제어가 있으나 **2초 간격 = 30/min으로 AV 5/min 한도를 초과**할 여지. AV로 라우팅되는 경우 한정 위험 (Finnhub 60/min용 sleep과 혼재).
- **권장**: AV provider 경로의 호출 간격을 12초(=5/min)로 별도 검증.

---

## 2. Queue 몰림 분석 (default vs neo4j)

### 2-1. neo4j 큐 (solo pool, **동시성 1**)

`task_routes`(L43~61)로 neo4j 큐에 배정된 스케줄 태스크:

| 시각(ET) | 태스크 | 주기 |
|---|---|---|
| **`*/5` (하루 종일)** | `sec-sync-dirty-neo4j` | **288회/일** |
| 매 6h (00/06/12/18) | `neo4j-health-check` | |
| 08:45/10:45/12:45/14:45/16:45/18:45 | `sync-news-to-neo4j` (6회) | max_articles=100 |
| 05:30 | `enrich-relationship-keywords` | limit=100 |
| 12:00 | `chainsight-sync-profiles-neo4j` | |
| 12:30 | `chainsight-sync-relations-neo4j` | |
| 04:00 | `cleanup-expired-news-relationships` | |
| Sun 04:30 | `chainsight-neo4j-dirty-sync` | |

**평가 — 가장 큰 구조적 위험 지점**:
- 🔴 **solo pool은 동시 1개만 처리**한다. `sec-sync-dirty-neo4j`가 **5분마다** 큐를 점유하는데, 만약 한 실행이 5분을 초과하면 **즉시 backlog**가 쌓인다 (expires=240s=4분이라 일부는 만료 폐기되지만, 큐 슬롯 경합은 발생).
- 🔴 **`:45` 슬롯 충돌**: `sync-news-to-neo4j`(max_articles=100, 무거움)가 `*/5`의 `xx:45` 실행분(`sec-sync-dirty`)과 **동일 분에 큐 진입** → solo 큐에서 직렬화되어 한쪽이 밀림.
- 🟡 **12:00–12:30**: `chainsight-sync-profiles`(12:00) + `neo4j-health-check`(12:00) + `chainsight-sync-relations`(12:30) + `*/5 sec-sync` 3회분이 30분 내 동일 solo 큐에 집중.

### 2-2. default 큐

- 나머지 ~60개 태스크 전부 default 큐. prefork(Linux) 또는 solo(macOS, `IS_MACOS`)에서 처리.
- ⚠️ **macOS 개발/운영 환경에서는 default 큐도 solo pool**(`config/celery.py:36-37`)이라 **동시성 1**. 이 경우 18:00 피크(아래)의 13개 태스크가 **완전 직렬 처리**되어 후속 태스크가 크게 밀린다.

---

## 3. 시간대별 API 호출 히트맵 (평일, NY/ET 기준)

각 시간대에 **시작되는(fire) 고정-시각 태스크 수**. `*/5`·`*/1` 등 시장시간 연속 태스크는 별도 표기.

```
ET    │ 태스크 발화 수 (평일)                                  │ 강도
──────┼────────────────────────────────────────────────────────┼──────
00 hr │ ▓                                          (health,recur)│ 1  baseline
01 hr │ ▓▓                                       (econ-calendar) │ 1
02 hr │ ▓                                          (recur only)  │ 0  *주말/월초만
03 hr │ ▓                                          (recur only)  │ 0  *주말/월초만
04 hr │ ▓▓                                  (cleanup-news-rel)   │ 1
05 hr │ ▓▓                                  (enrich-kw → neo4j)  │ 1
06 hr │ ██████████                  (econ,daily-news,fmp,cat,gen)│ 6  ★수집시작
07 hr │ ██████████                 (digest,heat,movers,cat,press)│ 6  ★
08 hr │ ████████              (keyword-LLM,mkt-news,classify,deep,n4j)│ 5  ★LLM
09 hr │ ████  +시장연속개시       (sentiment,relations | OPEN)   │ 2 +연속
10 hr │ ████████   +시장연속    (fmp1015,classify,deep,n4j,comention)│ 5 +연속
11 hr │ ▓▓        +시장연속              (relation-confidence)   │ 1 +연속
12 hr │ ██████████████████ +시장연속 (econ,mktnews,classify,gen,deep,n4j,cs-prof,cs-rel,sec-seed,health)│ 9~10 ◆◆PEAK
13 hr │ ██████  +시장연속        (fmp1315,cat-high,cs-seed)      │ 3 +연속
14 hr │ ████████  +시장연속  (daily-aft,cat-med,classify,deep,n4j)│ 5 +연속
15 hr │ ████  +시장연속            (mkt-news,fmp1515)            │ 2 +연속
16 hr │ ████████████ +시장연속(~16)(classify,deep,n4j,kw,breadth,heatmap)│ 6 ★
17 hr │ ████████              (daily-prices,cat-high,fmp1715,gen)│ 4
18 hr │ ██████████████████████████ (econ,mktnews,EOD,thesis×4,classify,deep,n4j,change%,eod-pipe,health)│ 13 ◆◆◆ABSOLUTE PEAK
19 hr │ ████                       (backfill-accuracy,ml-labels) │ 2
20 hr │ ▓▓                                  (sp500-financials)   │ 1
21 hr │ ▓                                          (recur only)  │ 0
22 hr │ ▓▓                                  (econ-indicators)    │ 1
23 hr │ ▓                                          (recur only)  │ 0
──────┴────────────────────────────────────────────────────────┴──────
연속(시장시간 09–16 ET): refresh-market-pulse-cache(*/1!!), realtime-prices(*/5),
                          market-indices(*/5), portfolio(*/10), screener-alerts(*/15)
종일 연속: sec-sync-dirty-neo4j(*/5, 288회/일), check-pipeline-alerts(*/30)
```

### 피크 시간대 식별

| 순위 | 시각(ET) | KST | 발화 수 | 성격 |
|---|---|---|---|---|
| 🥇 1위 | **18:00–18:45** | 07:00–07:45 | ~13 | **EOD 정산 대폭주**: 가격 EOD + Thesis 4단 파이프라인 + News 분석(LLM) + EOD 대시보드 + FRED |
| 🥈 2위 | **12:00–12:45** | 01:00–01:45 | ~10 | News + Chain Sight neo4j 동기화 + SEC seed + FRED, **시장시간 연속태스크와 중첩** |
| 🥉 3위 | 06:00 / 07:00 / 16:00 | 19/20/05시 | ~6 | 수집 개시 / 장마감 직후 집계 |

> **주의**: 09–16시 피크 수치는 "고정-시각 태스크"만 센 것이다. 실제로는 `refresh-market-pulse-cache`가 **매 1분** 도므로, 12시·16시의 체감 부하는 표기보다 훨씬 높다.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 🔴 의존성 경합 (선행 미완료 위험)

| 후속 태스크 | 선행 태스크 | 간격 | 위험 |
|---|---|---|---|
| **`thesis-update-readings` (18:00)** | `sync-sp500-eod-prices` (18:00) | **0분 (동시)** | 🔴 **동일 분 시작**. thesis 지표 수집이 EOD 가격 적재 완료를 전제하는데 같은 18:00에 시작 → readings가 **구(舊) 가격**으로 계산될 수 있음 |
| `run-eod-pipeline` (18:30) | `sync-sp500-eod-prices` (18:00) | 30분 | 🟡 sync가 30분 내 완료 가정. S&P500 일괄이 지연되면 빈 데이터로 파이프라인 실행 |
| `update-sp500-change-percent` (18:30) | `sync-sp500-eod-prices` (18:00) | 30분 | 🟡 동상 |
| `backfill-signal-accuracy` (19:00) | `run-eod-pipeline` (18:30) | 30분 | 🟢 비교적 여유 |
| `thesis-calculate-scores` (18:15) | `thesis-update-readings` (18:00) | 15분 | 🟡 readings 자체가 EOD에 막히면 연쇄 지연 |
| `thesis-create-snapshots` (18:30) | `thesis-calculate-scores` (18:15) | 15분 | 🟡 연쇄 |
| `thesis-generate-summaries` (18:35) | `thesis-create-snapshots` (18:30) | 5분 | 🟡 **5분은 매우 빠듯** (LLM 호출 포함, snapshot 직후라는 주석 P0 #15) |

> **18:00–18:35의 Thesis 4단 체인 + EOD 3종이 모두 18:00에 시작하는 sync-sp500-eod-prices에 의존**한다. macOS solo pool 환경이면 이 모든 게 직렬화되어 체인 전체가 깨질 수 있다. **선행 완료를 시각 간격으로만 보장**(eta-gap 방식)하고 있어, 데이터 적재 지연 시 보호 장치가 없다 → Celery chain/chord 또는 sentinel 체크 도입 검토 권장.

### 4-2. 🟡 동일 분(minute) 동시 시작 (자원 경합)

| 시각(ET) | 동시 시작 태스크 | 경합 자원 |
|---|---|---|
| **18:00** | econ-indicators, collect-market-news-evening, sync-sp500-eod-prices, thesis-update-readings, neo4j-health-check | FMP + FRED + DB + neo4j 큐 |
| **12:00** | econ-indicators, collect-market-news-noon, chainsight-sync-profiles-neo4j, sec-seed-relations, neo4j-health-check | FMP + neo4j 큐(3개 경합) |
| **09:00** | aggregate-daily-sentiment, extract-news-relations | + 시장 개장 연속태스크 동시 가동 |
| **07:00** | celery-error-digest, chainsight-heat-score-daily, collect-category-news-medium-morning | default 큐 |
| **`xx:15`** | classify-news-batch + collect-sp500-news-fmp-*(:15) | FMP + LLM |
| **`xx:45`** | sync-news-to-neo4j(무거움) + sec-sync-dirty-neo4j(*/5) | **neo4j solo 큐 직렬화** |

### 4-3. 🟡 정상적으로 잘 분산된 체인 (참고 — 양호 사례)

- **Market Movers → Keyword**: `sync-daily-market-movers`(07:30) → `keyword-generation-pipeline`(08:00), 30분 (주석 L237 확인). 🟢
- **주말 Chain Sight 체인** (토): all-profiles(02:00) → price-co-movement(03:00) → stale-decay(04:00) → aggregate-profiles(04:30) → validation-weekly-batch(05:00). 🟢 1시간 간격, profile expires=7200(2h)로 여유.
- **News v3 파이프라인**: classify(:15) → analyze-deep(:30) → sync-neo4j(:45), 15분 간격으로 매 2시간 정연하게 분산. 🟢

### 4-4. 🟡 일요일 ML 체인 — 5분 간격 과밀

```
Sun 03:00 train-importance-model  (expires 7200)
Sun 03:30 generate-shadow-report  (days=7)
Sun 04:00 check-auto-deploy
Sun 04:15 generate-weekly-ml-report
Sun 04:20 monitor-ml-performance   ← 04:15과 5분 간격
Sun 04:30 train-lightgbm-model     (expires 7200)
Sun 04:30 chainsight-neo4j-dirty-sync (neo4j 큐) ← 04:30 동시
```
- 🟡 04:15→04:20→04:30 구간이 5~10분 간격으로 과밀. `train-importance`(03:00)나 `train-lightgbm`이 길어지면 default 큐(특히 macOS solo)에서 후속이 밀림. LightGBM 학습은 CPU 집약적이라 다른 04:30 태스크와 경합.

### 4-5. ⚠️ 타임존 라벨 불일치 (문서 결함, 런타임 영향은 제한적)

`chainsight-heat-score-daily`(L747 "매일 07:00 **UTC**"), `chainsight-seed-selection`(L754 "13:00 **UTC**"), `chainsight-neo4j-dirty-sync`(L761 "일요일 04:30 **UTC**") 등은 주석에 "UTC"로 표기돼 있으나, `CELERY_TIMEZONE=America/New_York`이므로 **실제로는 NY 시간에 발화**한다 (6월 EDT 기준 UTC로는 각각 11:00 / 17:00 / 08:30 UTC).
- 🟢 **상대 순서는 보존**: heat-score(07:00 NY) < seed-selection(13:00 NY)로 "시드 선정 전 heat 계산" 의도는 유지됨.
- 🔴 **혼동 위험**: 운영자가 UTC로 오인하면 디버깅 시 4시간 어긋난 시각을 찾게 됨. 주석을 ET로 통일 권장 (다른 태스크들은 EST/ET 표기와 일관됨).

---

## 5. 종합 결론 및 권고 (읽기 전용 — 조치는 별도 승인 필요)

### 즉시 검증 필요 (P0)
1. **DB drift 대조** (§0-1 명령) — 본 보고서는 reference dict 기준. 실제 `PeriodicTask`와 diff 먼저 확인할 것. 이게 선행되지 않으면 아래 모든 분석이 "설계도"에 불과.
2. **18:00 EOD 정산 체인** (§4-1) — `thesis-update-readings`(18:00)와 `sync-sp500-eod-prices`(18:00) 동시 시작. 선행 의존을 시각 간격에만 의존 → 데이터 race. macOS solo pool에선 직렬화로 더 위험.

### 구조적 위험 (P1)
3. **neo4j solo 큐 backlog** (§2-1) — `sec-sync-dirty-neo4j` */5 + `:45` 무거운 sync-news 충돌. 동시성 1 큐의 직렬화 한계.
4. **Gemini 태스크 간 RPM 합산** (§1-2) — 내부 throttle은 태스크 내부만 보호. `:30` 슬롯 등에서 태스크 간 동시 LLM 호출이 계정 RPM(15) 초과할 수 있음 (이미 16:45 분산 선례 존재).

### 문서/관측성 (P2)
5. **chainsight "UTC" 주석** (§4-5) → ET로 통일.
6. **FMP/Gemini 일일 누적(RPD/일한도)** 실측 카운트 — 현 정적 분석으로는 확정 불가.

---

*본 보고서는 `config/celery.py`의 선언적 스케줄을 정적 분석한 것이며, 운영 중인 `django_celery_beat.PeriodicTask` 실제 등록 상태와는 다를 수 있다. 코드는 변경하지 않았다.*
