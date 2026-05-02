# Beat Schedule 감사 보고서

- **작성일**: 2026-05-02
- **분석 대상**: `config/celery.py` (line 135–807, 총 73개 beat 항목)
- **작성자**: Claude (read-only audit)
- **변경 사항**: 없음 (읽기 전용)

---

## 0. 분석 환경 (사전 확인)

| 항목 | 값 | 출처 |
|---|---|---|
| `CELERY_TIMEZONE` | `America/New_York` | `config/settings.py:413` |
| `TIME_ZONE` (Django) | `Asia/Seoul` | `config/settings.py:286` |
| `CELERY_BEAT_SCHEDULER` | `django_celery_beat.schedulers:DatabaseScheduler` | `config/settings.py:414` |
| `worker_pool` (macOS) | `solo` (강제) | `config/celery.py:30-31` |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | 100 | `config/settings.py:421` |
| FMP rate-limit | 300/min, 10 000/day, delay 0.2s | `config/settings.py:69-74` |
| Finnhub rate-limit | 60/min | `config/settings.py:84-88` |
| Marketaux rate-limit | 2 500/day | `config/settings.py:89-93` |
| Gemini Free | 15 RPM, 1 500 RPD (코드 주석 확인) | `news/services/news_deep_analyzer.py:39` |
| Alpha Vantage | 5/min (코딩 규칙) — `PROVIDER_RATE_LIMITS`에 미정의 | `CLAUDE.md` |

> ⚠️ **중요 전제 1**: 모든 `crontab(hour=…)`은 **NY 시간**으로 해석됨. 코드 주석에 "UTC"라고 적힌 항목들도 실제로는 NY 시간으로 등록되어 있다 (§3.1 참조).
>
> ⚠️ **중요 전제 2**: `config/celery.py:118-134` 주석대로, `app.conf.beat_schedule` dict는 **DatabaseScheduler 사용 시 런타임에 무시**된다. 이 보고서는 **"설계 의도"**를 분석한 것이며, 실제 동작은 `django_celery_beat.PeriodicTask` 테이블이 결정한다. 본 감사를 통한 위험 평가는 dict와 DB가 **동일하다는 가정** 하에 유효.

---

## 1. 종합 결론 (Executive Summary)

| 등급 | 개수 | 핵심 이슈 |
|------|------|----------|
| **P0 — 즉시 조치 권고** | 4 | 시간대 주석 ↔ 실제 NY time 불일치, 18:00 NY EOD 동시 폭주, neo4j 큐 단일 처리 한계 초과, drift 감지 자동화 부재 |
| **P1 — 곧 점검** | 5 | 08:00–08:30 Gemini 폭탄, 12:00–12:45 neo4j 큐 적체, 일요일 04:00–04:30 ML+Neo4j 동시, 매월 1일 03:00 Gemini bulk 단독, FMP S&P500 5회 orchestrator 누적 부하 |
| **P2 — 모니터링** | 4 | sec-sync-dirty-neo4j */5 24시간, 분당 매크로 cron 5종 중복, expires 미설정 항목, AV 의존 스케줄 부재(=명시적 누락) |

**가장 큰 단일 위험**: **18:00 NY** 시간대에 7개 태스크가 30분 안에 동시 시동된다 (sp500-eod, market-news-evening, FRED, thesis 3종, classify, analyze-deep, news→neo4j). FMP 300/min 한도 내이긴 하나, 단일 워커(macOS solo) 환경에서는 직렬 처리되며 thesis 의존 체인이 ETA를 초과할 가능성이 있다 (§4 참조).

---

## 2. 시간대별 ASCII 히트맵 (평일 NY time 기준)

각 행은 **시작 시각** 기준이며, 카운트는 해당 hour 내 실행 시작되는 태스크 수.

### 2.1 시간대별 태스크 시작 카운트 (default + neo4j queue 합산)

```
NY hr | count | bar (1칸=1태스크)              | queue 분포 (D=default, N=neo4j)
------+-------+--------------------------------+--------------------------------
  00  |   0   |                                |
  01  |   2   | ##                             | DD       (weekly+calendar)
  02  |   3   | ###                            | DDD      (월/주 배치)
  03  |   6   | ######                         | DDDDDD   (cleanup+ML+chainsight)
  04  |  11   | ###########                    | DDDDDDDDDDN  ← 일요일 폭탄
  05  |   3   | ###                            | DDN
  06  |   7   | #######                        | DDDDDDD  (FMP+FRED+news 동시)
  07  |   6   | ######                         | DDDDDD
  08  |   5   | #####                          | DDDDDN   ← Gemini 3종 동시
  09  |   2   | ##                             | DD       + 장중 cron 시작
  10  |   5   | #####                          | DDDDN
  11  |   1   | #                              | D
  12  |   8   | ########                       | DDDDDNNN ← neo4j 큐 적체
  13  |   3   | ###                            | DDD
  14  |   5   | #####                          | DDDDN
  15  |   2   | ##                             | DD
  16  |   6   | ######                         | DDDDDN
  17  |   4   | ####                           | DDDD
  18  |  11   | ###########                    | DDDDDDDDDDN  ← EOD 폭탄
  19  |   2   | ##                             | DD
  20  |   1   | #                              | D
  21  |   0   |                                |
  22  |   1   | #                              | D
  23  |   0   |                                |
```

### 2.2 외부 API별 호출 발생 시각 (피크 식별용)

```
시각  | FMP | Gemini | Finnhub/MA | FRED | SEC | Neo4j |
------+-----+--------+-----------+------+-----+-------+ 비고
  01  |  -  |   -    |     -     |  *   |  -  |   -   | calendar
  03  |  -  |  ***   |     -     |  -   |  *  |   -   | korean overviews bulk(매월1) + supply-chain(매월15)
  04  |  -  |   -    |     -     |  -   |  ** |   *   | regulatory + institutional + neo4j cleanup
  05  |  -  |   *    |     -     |  -   |  -  |   *   | enrich-relationship (Gemini, neo4j queue)
  06  |  ** |   -    |    **     |  *   |  *  |   -   | sp500-news-fmp-0615 + general-fmp + 카테고리 + FRED
  07  |  ** |   -    |    **     |  -   |  -  |   -   | press-releases + market-movers + 카테고리
  08  |  *  |  ***   |    **     |  -   |  -  |   *   | keyword-pipeline + classify + analyze-deep
  09  |  ** |   -    |     -     |  -   |  -  |   -   | + 장중 5분/10분/1분 cron 시작
  10  |  ** |   **   |     -     |  -   |  -  |   *   | sp500-news-fmp-1015 + classify + analyze-deep
  12  |  ** |   **   |    **     |  *   |  -  |  ***  | general-fmp + analyze + market-news + neo4j 3종 ★
  13  |  ** |   -    |     -     |  -   |  -  |   -   | sp500-news-fmp-1315 + 카테고리 high
  14  |  -  |   **   |    **     |  -   |  -  |   *   | classify + analyze + daily-news
  15  |  ** |   -    |    **     |  -   |  -  |   -   | sp500-news-fmp-1515 + market-news
  16  |  -  |   **   |     -     |  -   |  -  |   *   | classify + analyze + extract-keywords + breadth/heatmap
  17  |  ** |   -    |    **     |  -   |  -  |   -   | sp500-news-fmp-1715 + general-fmp + daily-prices
  18  | *** |   **   |    **     |  *   |  -  |   *   | sp500-eod ★ + thesis 3종 + market-news + analyze ★★
  19  |  *  |   -    |     -     |  -   |  -  |   -   | ml-labels + signal-accuracy
  20  | *** |   -    |     -     |  -   |  -  |   -   | sp500-financials (101 종목 × 5 endpoint = ~500 calls)
  22  |  -  |   -    |     -     |  *   |  -  |   -   | FRED 22:00
```

기호 의미: `*` = 1태스크, `**` = 2-3태스크, `***` = 4+ 태스크, `★` = 위험 피크.

### 2.3 항상 실행되는 백그라운드 cron (시간대 무관)

| 태스크 | 주기 | Queue | 일일 실행 횟수 | 비고 |
|---|---|---|---|---|
| `sec-sync-dirty-neo4j` | `*/5` (24h) | **neo4j** | 288회 | expires 240s — neo4j 큐 점유율 최대 |
| `check-pipeline-alerts` | `*/30` (24h) | default | 48회 | expires 1500s |

### 2.4 장중 (09–16시 NY) 추가 cron

| 태스크 | 주기 | API | 8시간 합계 |
|---|---|---|---|
| `update-realtime-prices` | `*/5` | FMP | 96회 |
| `update-market-indices` | `*/5` | FMP | 96회 |
| `refresh-market-pulse-cache` | `*/1` | DB only | 480회 |
| `calculate-portfolio-values` | `*/10` | DB only | 48회 |
| `check-screener-alerts` | `*/15` | DB only | 32회 |

→ 장중 매 5분 정각마다 **realtime + indices + pulse-cache + (10분 시 portfolio) + (15분 시 screener)** 동시 시동. macOS solo pool에서는 5분 안에 모두 처리 못 하면 누적 → 다음 cycle drift.

---

## 3. P0 — 즉시 조치 권고

### 3.1 [P0] 시간대 주석 ↔ 실제 NY time 불일치 (3건)

`CELERY_TIMEZONE = America/New_York`인데, 다음 항목들은 주석에 **"UTC"**로 적혀 있다. 실제로는 **NY 시간**으로 등록된다.

| 태스크 | 코드 주석 | 실제 동작 시각 | 의도가 UTC였다면 어긋남 |
|---|---|---|---|
| `chainsight-heat-score-daily` (line 734-739) | "매일 07:00 UTC" | 매일 **NY 07:00** | UTC 07:00 = NY 02:00/03:00 (DST 따라) |
| `chainsight-seed-selection` (line 741-746) | "매일 13:00 UTC" | 매일 **NY 13:00** | UTC 13:00 = NY 08:00/09:00 |
| `chainsight-neo4j-dirty-sync` (line 748-753) | "매주 일요일 04:30 UTC" | 일 **NY 04:30** | UTC 04:30 = NY 23:30(토)/00:30(일) |

**위험**:
- `seed-selection`은 코드 주석상 "관계 동기화 후" 실행이 의도. NY 13:00이라면 `chainsight-sync-relations-neo4j`(NY 12:30) 직후 30분 → 의존성 충족 OK. 그러나 **만약 의도가 UTC 13:00 = NY 08:00이었다면** sync 작업(NY 12:00, 12:30) 이전에 시드 선정이 돌아 데이터 부정합 발생.
- `heat-score-daily`도 "시드 선정 전" 실행이 의도. NY 07:00 < NY 13:00 OK. 그러나 의도가 UTC였다면 순서 뒤바뀜 가능.

**조치**: 주석을 NY 기준으로 수정하거나, 의도가 UTC였다면 `crontab(hour=N, minute=M)`의 N/M을 NY 변환값으로 재등록 (코드 변경 — 본 보고서는 read-only이므로 권고만).

### 3.2 [P0] 18:00 NY EOD 동시 폭주

NY 18:00–18:45 사이 시작되는 태스크 11개. macOS solo pool 1워커 기준, 의존 체인 ETA 위반 위험.

```
18:00  sync-sp500-eod-prices            FMP, ~500 calls  (S&P500 × 1 endpoint)
18:00  thesis-update-readings           FMP/계산         (지표 데이터 수집)
18:00  update-economic-indicators       FRED 4-N calls
18:00  collect-market-news-evening      Finnhub/Marketaux
18:15  thesis-calculate-scores          DB 계산           ← thesis-update-readings 의존
18:15  classify-news-batch              DB(또는 LLM)
18:30  thesis-create-snapshots          DB+알림          ← thesis-calculate-scores 의존
18:30  run-eod-pipeline                 stocks 시그널 14종
18:30  update-sp500-change-percent      DB only
18:30  analyze-news-deep-batch          Gemini, 50 articles × 4s = 200s
18:45  sync-news-to-neo4j               neo4j queue
```

**FMP 분당 한도 분석**:
- 18:00 동시: `sp500-eod-prices` (FMP rate_limit `100/m` 적용? → news/tasks.py:906) + `thesis-update-readings` (FMP) + `market-news` (FMP/Finnhub).
- 만약 `sp500-eod-prices`가 batch endpoint로 1회 호출이면 OK. **종목당 호출이라면 500 calls / 300 RPM = 1분 40초 → 다음 cycle까지 안전**.
- 그러나 동시에 thesis-update가 추가 FMP 호출 시 → **300/min 초과 가능성 유의**.

**Thesis 의존 체인 ETA**:
- 18:00 readings → 18:15 scores → 18:30 snapshots. 각 15분.
- readings가 15분 안에 끝나야 scores가 정상 데이터로 돌아감. solo pool에서 sp500-eod와 직렬화되면 readings가 밀린다.

**조치 권고**: 18:00 동시 시동 4개 중 thesis-update-readings를 17:50 또는 17:30으로 분산. 또는 thesis 체인을 chord/group으로 묶어 ETA 무관하게 의존 보장.

### 3.3 [P0] Neo4j 큐 단일 처리 한계 초과 위험 (12:00–12:45)

Neo4j 큐는 **solo pool 1개 워커**에서 처리됨 (`config/celery.py` 주석, `--pool=solo`).

```
NY 12:00–12:45 neo4j queue 진입 작업:
  12:00  chainsight-sync-profiles-neo4j        (S&P500 프로파일)
  12:30  chainsight-sync-relations-neo4j       (관계 그래프)
  12:45  sync-news-to-neo4j (max_articles=100) (뉴스 이벤트)
  매 5분 sec-sync-dirty-neo4j                  (12:00, 12:05, … 12:45 = 10회)
```

**계산**: 12:00–12:45 사이 neo4j 큐에 **약 13개 작업** 적재. solo pool은 동시 1개, 작업당 평균 1–5분 소요 가정 시 직렬 처리 → 큐 누적, `expires` 안에 못 끝나면 silent drop.

**현재 expires 값**:
- `chainsight-sync-profiles-neo4j`: 3600s (1h) — 안전
- `sync-news-to-neo4j`: 3600s — 안전
- `sec-sync-dirty-neo4j`: **240s (4분)** — 위험. 5분 cycle인데 expires 4분이면 1회만 적체되어도 다음 cycle의 dirty 데이터 누락.

**조치 권고**: `sec-sync-dirty-neo4j` expires를 290s로 늘리거나, neo4j 큐를 2개 워커로 분리(prefork 안전 설정 후).

### 3.4 [P0] Drift 감지 자동화 부재

`config/celery.py:128-133` 주석:
> "config dict와 DB `PeriodicTask`가 어긋나면 dict의 태스크는 실행되지 않는다. … Drift 재발 방지 체크는 `python manage.py shell`에서 … 수동 진행."

**위험**: 수동 체크는 사람이 잊으면 실패. 2026-04-24에 이미 2건 누락 사고 발생 기록(주석). 73개 항목 중 몇 개가 DB에 빠졌는지 본 감사로는 확인 불가.

**조치 권고**: `manage.py` 커맨드 `audit_beat_drift` 신설 — `set(PeriodicTask.objects.values_list('name', flat=True)) ^ set(app.conf.beat_schedule.keys())` 출력. CI 또는 매일 cron으로 자동화.

---

## 4. P1 — 곧 점검

### 4.1 [P1] 08:00–08:30 Gemini LLM 동시 폭주

```
08:00  keyword-generation-pipeline      Gemini (Market Movers 키워드)
08:15  classify-news-batch              LLM (분류, hours=3)
08:30  analyze-news-deep-batch          Gemini, max_articles=50, 4초 간격 → 200초 (3.3분) 점유
```

**Gemini Free 15 RPM** = 4초당 1콜. `analyze-news-deep-batch`는 **단독으로 Gemini RPM의 100% 사용** (4초 간격 코드 = `news/services/news_deep_analyzer.py:39`).

08:00 keyword + 08:15 classify가 끝나기 전에 08:30 analyze-deep 시작 시 **15 RPM 2배 초과** 위험. 이미 `extract-daily-news-keywords`(16:45)는 16:30 deep과 15분 분산하여 회피했다는 주석(line 285-287) 존재 — **08시 구간은 동일한 회피가 누락**.

**조치 권고**: `keyword-generation-pipeline`을 08:00 → 07:50로 이동하거나, Gemini RPM을 통합 관리하는 토큰 버킷 도입.

### 4.2 [P1] 일요일 04:00–04:30 ML+Neo4j 폭탄

```
04:00  cleanup-expired-news-relationships  neo4j queue
04:00  check-auto-deploy                   ML 자동 배포
04:00  scan-regulatory-relationships       (월요일만)
04:15  generate-weekly-ml-report           ML 리포트
04:20  monitor-ml-performance              ML 모니터링
04:30  train-lightgbm-model                LightGBM 학습 (최대 2시간)
04:30  chainsight-neo4j-dirty-sync         neo4j queue
04:30  build-patent-network                (매월 1일만)
04:30  chainsight-aggregate-profiles       (토요일만)
```

→ 일요일 04:00–04:30 사이 **8개 시동**, 그중 2개 neo4j 큐. `train-lightgbm-model`이 2시간 점유하면 04:30–06:30까지 default 큐 다른 작업 지연.

**조치 권고**: ML 학습 작업을 별도 큐(`ml`)로 격리하고 워커 분리.

### 4.3 [P1] 매월 1일 03:00 Gemini Bulk 단독

`refresh-korean-overviews-monthly` (line 641-645): S&P500 = 약 500개 회사 한글 개요 Gemini 생성. 15 RPM × 60분 = 900 RPD. **하루 RPD 1500 한도 60% 단일 작업 점유**. 같은 날 05:30 `enrich-relationship-keywords` (limit=100) + 08:30/10:30/… `analyze-news-deep-batch` 모두 동일 Gemini 키 사용 시 RPD 초과 가능.

**계산**:
- 03:00 korean-overviews bulk: 500 calls
- 05:30 enrich-relationship: 100 calls
- analyze-news-deep × 6회/일 × 50 articles = 300 calls
- extract-daily-news-keywords × 1회: 50–100 calls 추정
- keyword-generation-pipeline × 1회: 50+ calls 추정
- **합계 약 1100+ RPD** ← Gemini Free 1500 RPD의 73% 도달, 매월 1일은 한도 임박.

**조치 권고**: korean-overviews를 매월 1일 → 매월 1·8·15·22일 4분할 (125 calls/회).

### 4.4 [P1] FMP S&P500 News Orchestrator 5회 누적 부하

`collect-sp500-news-fmp-{0615,1015,1315,1515,1715}` × 평일 = **하루 5회 × 500 종목 호출**. 회당 100 calls/m rate_limit이 task에 적용된다 가정해도 5분 소요. 평일 daily call 추정 = 500 × 5 = 2 500. **FMP daily 10 000의 25%를 단일 orchestrator가 점유**.

다른 FMP 의존 작업(realtime, indices, market-movers, financials, eod-prices, press-releases, general-news)와 합산 시 일일 한도 근접 가능.

**조치 권고**: `news/tasks.py`의 orchestrator 호출 수 측정 후, 5회 → 3회(아침/점심/저녁)로 감축 검토.

### 4.5 [P1] sec-sync-dirty-neo4j */5 24시간 vs 다른 neo4j 작업 충돌

`sec-sync-dirty-neo4j`는 **24시간 5분마다** = 288회/일, neo4j 큐에 항상 적재됨. 다른 neo4j 큐 작업(05:30 enrich, 12:00/12:30 chainsight, 12:45 news-sync, 매일 04:00 cleanup) 시작 시점마다 sec-sync가 큐 앞에 있으면 의존 작업 지연.

**조치 권고**: sec-sync 빈도를 */15로 완화하거나, 큐 우선순위 분리 (`priority` 필드).

---

## 5. P2 — 모니터링

### 5.1 [P2] AV (Alpha Vantage) 의존 스케줄 — 명시적으로 없음

`PROVIDER_RATE_LIMITS`에 AV 미정의, `config/celery.py` 73개 schedule 중 AV 직접 호출 작업 0건. CLAUDE.md는 "Alpha Vantage 5/min, 12초 대기"를 코딩 규칙으로 명시 — **schedule에서 사용 안 함이 의도된 상태인지, 누락인지 확인 필요**.

### 5.2 [P2] expires 미설정 항목

```
update-realtime-prices       expires 없음 (5분 cron)
update-daily-prices          expires 없음
calculate-portfolio-values   expires 없음
update-economic-indicators   expires 없음
update-market-indices        expires 없음
refresh-market-pulse-cache   expires 없음 (1분 cron — 가장 위험)
celery-error-digest          expires 없음
cleanup-task-results         expires 없음
```

**위험**: 워커 다운 후 복구 시, 큐에 쌓인 모든 cron job이 한꺼번에 실행되어 외부 API 폭주 유발. 특히 `refresh-market-pulse-cache`는 1분 cron이라 1시간 다운 시 60개가 동시 실행.

**조치 권고**: 모든 `*/5` 이하 cron에 `expires`를 cron 주기와 동일 값으로 설정.

### 5.3 [P2] 분당 매크로 cron 5종 중복 (장중)

§2.4 표 참조. 5분/10분/15분/1분 cron이 **장중 매 5분 정각에 동시 시동**. macOS solo pool 환경에서는 직렬 처리 → 1분 cron(`refresh-market-pulse-cache`)이 5분 cron 뒤에 밀리면 데이터 신선도 저하.

**조치 권고**: 분당 cron을 별도 worker(`-Q realtime`)로 분리.

### 5.4 [P2] 매월 1일 02:00–04:30 월간 배치 5종

```
02:00  sync-sp500-constituents    (FMP, 1회 호출)
02:30  archive-old-articles       (DB 정리, 6개월 이전)
03:00  refresh-korean-overviews   (Gemini bulk 500)
04:30  build-patent-network       (특허 네트워크 빌드)
06:00  sec-check-new-filings      (SEC 신규 10-K)
```

월 1회만 실행되므로 절대 부하는 낮으나, 매월 1일이 일요일과 겹치는 달에는 주간 ML 작업과 직렬화. 충돌 가능성 모니터링 권장.

---

## 6. 의존성 그래프 (선언적 — 실제 코드상 보장 메커니즘 없음)

다음 의존 체인은 **시간 차로만 보장**되며, 선행 작업이 실패/지연되면 후속이 빈 데이터로 동작.

```
chainsight-co-mentions (10:00)
   └→ chainsight-relation-confidence (11:00)              [1h gap]
        └→ chainsight-sync-profiles-neo4j (12:00)         [1h gap]
             └→ chainsight-sync-relations-neo4j (12:30)   [30m gap]
                  └→ chainsight-seed-selection (13:00)    [30m gap, ※ 주석은 UTC라고 잘못 표기]

thesis-update-readings (18:00)
   └→ thesis-calculate-scores (18:15)                     [15m gap, 회당 평균 ETA 측정 필요]
        └→ thesis-create-snapshots (18:30)                [15m gap]

sync-sp500-eod-prices (18:00)
   └→ run-eod-pipeline (18:30)                            [30m gap, 14개 시그널 계산]
        └→ backfill-signal-accuracy (19:00)               [30m gap]

train-importance-model (일 03:00)
   └→ generate-shadow-report (일 03:30)                   [30m gap]
        └→ check-auto-deploy (일 04:00)                   [30m gap]
             └→ generate-weekly-ml-report (일 04:15)      [15m gap]
                  └→ monitor-ml-performance (일 04:20)    [5m gap ← 너무 짧음]
                       └→ train-lightgbm-model (일 04:30) [10m gap]
```

**조치 권고**: Celery `chord`/`chain`으로 묶어 의존 보장 (현재는 실패 시 silent하게 빈 데이터로 진행).

---

## 7. 종합 점수표

| 카테고리 | 항목 수 | 위험 점수 (10점 만점) | 비고 |
|---|---|---|---|
| Rate-limit (FMP) | — | 6/10 | 일일 합계 30% 사용, 18:00 분당 한도 임박 |
| Rate-limit (Gemini Free) | — | 7/10 | 매월 1일 RPD 73% 도달, 08시 RPM 2배 위험 |
| Rate-limit (AV) | — | N/A | schedule에서 미사용 — 의도 확인 필요 |
| Rate-limit (Finnhub/Marketaux) | — | 3/10 | 한도 충분, 충돌 적음 |
| Default queue 부하 | 67개 | 5/10 | 18:00, 04:00 피크 |
| **Neo4j queue 부하** | 6개 + */5 | **8/10** | solo pool 1개로 처리, 12시·sec-sync 적체 |
| 의존 체인 보장 | 4 chain | 6/10 | 시간차 의존, chord 미사용 |
| Drift 자동 감지 | — | 9/10 | 부재, 수동 체크 의존 |
| 시간대 표기 정확도 | 73개 중 3건 | 7/10 | UTC 주석 vs NY 실제 |

---

## 8. 우선순위별 조치 요약

| # | 등급 | 조치 | 예상 영향 |
|---|------|------|----------|
| 1 | P0 | `chainsight-heat-score-daily/seed-selection/neo4j-dirty-sync` 주석 vs 실제 NY 시간 일치 검증 후 수정 | Chain Sight 데이터 순서 보장 |
| 2 | P0 | `manage.py audit_beat_drift` 커맨드 신설 → CI 통합 | 향후 drift 0 사고 |
| 3 | P0 | 18:00 NY 동시 작업 4개를 17:50/18:00/18:10/18:20로 5–10분 간격 분산 | thesis 체인 ETA 안정화 |
| 4 | P0 | `sec-sync-dirty-neo4j` expires 240→290s 또는 `*/5`→`*/15` | 큐 적체로 인한 silent drop 방지 |
| 5 | P1 | `keyword-generation-pipeline` 08:00 → 07:50 이동 | Gemini RPM 회피 |
| 6 | P1 | `refresh-korean-overviews-monthly` 매월 1·8·15·22일 4분할 | RPD 한도 마진 확보 |
| 7 | P1 | LightGBM 학습 작업을 `-Q ml` 큐로 격리 | 일요일 새벽 default 큐 정상화 |
| 8 | P2 | 모든 분 단위 cron에 `expires` 추가 | 워커 복구 시 폭주 방지 |
| 9 | P2 | thesis 체인을 Celery `chain()`으로 묶기 | 의존 명시화 |

---

## 9. 본 감사의 한계

1. **DB 진실 vs config dict 가정**: 실제 `PeriodicTask` 테이블 미조회. dict와 동일하다는 가정 하에 분석.
2. **태스크 내부 호출 수 미측정**: 각 task가 외부 API를 몇 회 호출하는지 코드 정독 미수행. orchestrator/batch task는 문서/주석에 의존.
3. **워커 수/큐 라우팅 운영 환경 미확인**: macOS dev 기준 분석. 운영 Linux는 prefork이므로 동시성 양상이 다를 수 있음.
4. **DST 전환 영향**: NY 시간은 3월/11월 DST 전환 시 일부 작업 중복/누락 가능. 본 감사에서는 미포함.
5. **읽기 전용 원칙**: 본 보고서는 코드/DB/설정을 변경하지 않음. 모든 권고는 별도 후속 PR로 처리 필요.

---

**끝.**
