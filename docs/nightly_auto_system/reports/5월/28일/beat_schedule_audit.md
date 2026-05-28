# Beat Schedule Audit — 2026-05-28

**범위**: `config/celery.py` `beat_schedule` dict 전체 (74개 정의 + crontab 표현 90개)
**작성 모드**: 읽기 전용 (코드 수정 금지)
**중요 컨텍스트**:
- `config/settings.py`의 `CELERY_BEAT_SCHEDULER = DatabaseScheduler` 때문에 dict는 **런타임에 무시**되고 `django_celery_beat.PeriodicTask` 테이블이 진실의 소스 (Bug #28).
- 본 감사는 **dict 선언(설계 의도)**을 기준으로 한다. 실제 DB 등록 여부와 drift는 별도 검증 필요.
- 시간대 주석은 EST/UTC가 혼재 — crontab 자체는 워커의 `CELERY_TIMEZONE`(미확인) 기준. 본 보고서는 **표기된 시간 그대로** 분석한다.

---

## 0. 요약 (TL;DR)

| 등급 | 카운트 | 핵심 |
|------|--------|------|
| **🔴 P0** | 4건 | 18:00 EOD 동시 폭풍 / sec-sync-dirty 5분 주기 vs neo4j solo pool / FMP S&P 500 뉴스 5회/일 부하 불투명 / 시간대(TZ) 표기 혼재(EST/UTC) |
| **🟠 P1** | 5건 | 16:15–16:45 Gemini 3중 fire / 12:00 Neo4j 큐 3중 충돌 / refresh-market-pulse-cache 매분(시장시간 480회/일) / 09:00 minute=0 6태스크 동시 / 일요일 03:00–04:30 ML+Neo4j 직렬 의존 |
| **🟡 P2** | 4건 | hour='9-16' 정의가 16:55까지로 17시 누락 / Beat dict와 DB 동기화 검증 부재 / Chain Sight EOD pipeline 의존 순서 5분 간격(추월 위험) / sec-sync-dirty expires=240s < 5분 주기 (4초 갭) |
| **🟢 P3** | 2건 | 휴장일·공휴일 가드 부재 / 단일 minute=0 정렬 패턴 → jitter 미사용 |

가장 위험한 단일 구간: **평일 18:00–18:45 ET** (EOD 파이프라인 + 뉴스 분석 + Neo4j sync 6개 직렬, FMP·DB·Neo4j 동시 부하)
가장 만성 위험: **sec-sync-dirty-neo4j 5분 주기**가 neo4j solo pool에서 다른 Neo4j 태스크 모두를 지연 큐잉

---

## 1. 전체 태스크 분류 (74개)

### 1.1 Provider/리소스별 분류

| 카테고리 | 태스크 수 | 주요 태스크 |
|---------|----------|-----------|
| **FMP 호출** | 16 | update-realtime-prices, sync-sp500-eod-prices, sync-sp500-financials, collect-sp500-news-fmp-* (×5), collect-press-releases-fmp, collect-general-news-fmp-* (×3), collect-market-news-* (×4), update-market-indices, sync-etf-holdings |
| **FRED 호출** | 2 | update-economic-indicators, update-economic-calendar |
| **Gemini LLM** | 9 (추정) | keyword-generation-pipeline, extract-daily-news-keywords, classify-news-batch, analyze-news-deep-batch, enrich-relationship-keywords, thesis-generate-summaries, refresh-korean-overviews-monthly, generate-shadow-report, generate-weekly-ml-report |
| **Neo4j 큐 (solo)** | 8 | sec-sync-dirty-neo4j (5min), neo4j-health-check, sync-news-to-neo4j, cleanup-expired-news-relationships, enrich-relationship-keywords, chainsight-sync-profiles-neo4j, chainsight-sync-relations-neo4j, chainsight-neo4j-dirty-sync |
| **내부 계산/집계** | 24 | aggregate-weekly-prices, calculate-portfolio-values, refresh-market-pulse-cache, run-eod-pipeline, backfill-signal-accuracy, calculate-market-breadth, calculate-sector-heatmap, thesis-* (×3), chainsight-* (×7), build-patent-network, scan-regulatory-relationships, sync-institutional-holdings, sync-supply-chain-batch, sync-sp500-constituents, update-sp500-change-percent, validation-weekly-batch, archive-old-articles, cleanup-old-macro-data, check-pipeline-alerts, train-importance-model, train-lightgbm-model, check-auto-deploy, monitor-ml-performance |
| **운영** | 2 | celery-error-digest, cleanup-task-results |

**총 74개 unique schedule** (Schedule expression 카운트 90 ≠ task 수: 일부 동일 task가 다른 시간대에 여러 번 등록 — 예: collect-market-news 4회, collect-sp500-news-fmp 5회, collect-category-news-* 6회)

---

## 2. 시간대별 fire 히트맵 (평일 M-F, EST 표기 기준)

각 셀 = 해당 시간(:00–:59) 안에서 발생하는 **총 fire 수** (반복 태스크 포함). 분 단위 분포는 §3.

```
시간 │ Fire │ 부하 등급  │  히스토그램 (1칸=2 fire)
─────┼──────┼────────────┼──────────────────────────────────────────
 00  │  15  │ 🟢 idle    │ ████████
 01  │  15  │ 🟢 idle    │ ████████        +1 update-economic-calendar
 02  │  14  │ 🟢 idle    │ ███████
 03  │  14  │ 🟢 idle    │ ███████
 04  │  15  │ 🟢 idle    │ ████████        +1 cleanup-expired-news-relationships (Neo4j)
 05  │  15  │ 🟢 idle    │ ████████        +1 enrich-relationship-keywords (Gemini+Neo4j)
 06  │  20  │ 🟡 ramp    │ ██████████      ⚠ 뉴스 4종+health-check 클러스터
 07  │  20  │ 🟡 ramp    │ ██████████      ⚠ market-movers + press-releases + heat-score
 08  │  19  │ 🟡 ramp    │ ██████████      ⚠ Gemini 시작(keyword + classify + analyze)
 09  │ 121  │ 🔴 PEAK    │ █████████████████████████████████████████████████████████████  ★ pulse 60+
 10  │ 125  │ 🔴 PEAK    │ ██████████████████████████████████████████████████████████████ ★ + co-mentions
 11  │ 109  │ 🔴 PEAK    │ ██████████████████████████████████████████████████████
 12  │ 119  │ 🔴 PEAK    │ █████████████████████████████████████████████████████████      ★ Neo4j sync 3중
 13  │ 110  │ 🔴 PEAK    │ ███████████████████████████████████████████████████████
 14  │ 114  │ 🔴 PEAK    │ █████████████████████████████████████████████████████████
 15  │ 110  │ 🔴 PEAK    │ ███████████████████████████████████████████████████████
 16  │ 115  │ 🔴 PEAK    │ █████████████████████████████████████████████████████████      ★ 16:15/16:30/16:45 Gemini 3중
 17  │  18  │ 🟡 cooldown│ █████████       ⚠ 시장시간 외 첫 시간 — daily-prices fire
 18  │  26  │ 🟠 STORM   │ █████████████   ★★ EOD 폭풍 (FMP+Gemini+Neo4j+DB 4중)
 19  │  16  │ 🟡 cooldown│ ████████
 20  │  15  │ 🟡 cooldown│ ████████        +1 sync-sp500-financials (FMP 101 symbols)
 21  │  14  │ 🟢 idle    │ ███████
 22  │  15  │ 🟢 idle    │ ████████        +1 update-economic-indicators
 23  │  14  │ 🟢 idle    │ ███████
─────┴──────┴────────────┴──────────────────────────────────────────
* 09–16시 90+ fire의 80% 이상은 refresh-market-pulse-cache(매분 60건) + 5분주기 4종.
* "Fire" = beat가 trigger를 발사한 횟수. 실제 외부 API 호출 수와 ≠ (각 태스크 내부에서 batch/loop).
```

### 2.1 24/7 상주 부하 (시간대 무관)

| 태스크 | 주기 | 시간당 fire | 비고 |
|--------|------|-----------|------|
| `sec-sync-dirty-neo4j` | `*/5` 매 5분 | **12** | Neo4j solo pool — 단일 워커 |
| `check-pipeline-alerts` | `*/30` 매 30분 | 2 | default queue |
| `refresh-market-pulse-cache` | `*` 매분, 9-16시만 | 60 | 시장시간 한정 |
| `update-realtime-prices` | `*/5` 5분, 9-16시만 | 12 | 5분 × 8시간 = 96회/일 |
| `update-market-indices` | `*/5` 5분, 9-16시만 | 12 | FMP |
| `calculate-portfolio-values` | `*/10` 10분, 9-16시만 | 6 | 내부 |
| `check-screener-alerts` | `*/15` 15분, 9-16시만 | 4 | 내부 |

---

## 3. 분 단위 충돌 분석 (정확히 같은 minute 발사)

### 3.1 🔴 minute=0 정렬 — 매시간 클러스터

평일 09:00, 12:00, 18:00 등 정시 hot-zone:

```
09:00 ET 동시 발사 (M-F):
  ├─ update-realtime-prices      (FMP, hour 9-16, */5)
  ├─ update-market-indices       (FMP, hour 9-16, */5)
  ├─ refresh-market-pulse-cache  (internal, hour 9-16, *)
  ├─ calculate-portfolio-values  (internal, hour 9-16, */10)
  ├─ aggregate-daily-sentiment   (LLM 또는 집계)
  ├─ extract-news-relations      (serverless, args=24h)
  └─ sec-sync-dirty-neo4j        (Neo4j solo pool, */5)

→ Beat → broker fanout 7개 메시지가 같은 timestamp.
  default queue 6개 + neo4j queue 1개.
  default worker가 prefork(prod Linux)면 흡수 가능, macOS solo면 직렬화.
```

```
12:00 ET 동시 발사 (M-F):
  ├─ update-realtime-prices, update-market-indices, pulse, portfolio (시장시간 4개)
  ├─ update-economic-indicators           (FRED)
  ├─ collect-market-news-noon             (FMP)
  ├─ neo4j-health-check                   (Neo4j solo, */6=0,6,12,18)
  ├─ chainsight-sync-profiles-neo4j       (Neo4j solo)
  ├─ sec-seed-relations-to-chainsight     (default)
  └─ sec-sync-dirty-neo4j                 (Neo4j solo, */5)

→ Neo4j 큐에 동시 3개 enqueue. solo pool 처리 시 마지막은 직전 두 개의
  총 소요시간만큼 지연. sync-profiles-neo4j가 분 단위 작업이면
  sec-sync-dirty 다음 발사(12:05)와 겹쳐 backlog.
```

### 3.2 🔴 18:00–18:45 ET EOD 폭풍 — 최우선 위험

평일 18시는 가장 무거운 분당 부하 — 5분 간격 의존 체인이 줄지어 발사:

```
시각      태스크                              Queue   외부 호출    의존 관계
─────────────────────────────────────────────────────────────────────────────
18:00:00  update-economic-indicators          default FRED         독립
18:00:00  collect-market-news-evening         default FMP          독립
18:00:00  neo4j-health-check                  neo4j   Neo4j        독립
18:00:00  sync-sp500-eod-prices               default FMP×500      → 18:30 EOD pipeline
18:00:00  thesis-update-readings              default 내부+API?     → 18:15
18:00:00  sec-sync-dirty-neo4j (*/5)          neo4j   Neo4j        독립

18:15:00  classify-news-batch                 default Gemini       독립(분류기)
18:15:00  thesis-calculate-scores             default 내부          ← thesis-update-readings 완료 가정
18:15:00  sec-sync-dirty-neo4j (*/5)          neo4j   Neo4j        독립

18:30:00  analyze-news-deep-batch             default Gemini×50    독립
18:30:00  run-eod-pipeline                    default 내부+가능 API ← sync-sp500-eod-prices 완료 가정
18:30:00  thesis-create-snapshots             default 내부+이메일   ← thesis-calculate-scores 완료 가정
18:30:00  update-sp500-change-percent         default 내부          ← sync-sp500-eod-prices 완료 가정

18:35:00  thesis-generate-summaries           default Gemini       ← thesis-create-snapshots 완료 가정

18:45:00  sync-news-to-neo4j                  neo4j   Neo4j×100    독립
18:45:00  sec-sync-dirty-neo4j (*/5)          neo4j   Neo4j

─────────────────────────────────────────────────────────────────────────────
위험:
1. 18:00에 sync-sp500-eod-prices가 FMP 500 symbol을 단일 endpoint로
   batch 안 하면 분당 호출 폭증 (FMP 300/min 한도 위협).
2. 18:15 thesis-calculate-scores는 18:00 thesis-update-readings 완료 가정 —
   15분 안에 끝나지 않으면 빈 데이터로 계산. 실제 소요시간 미계측.
3. 18:30 run-eod-pipeline ← 18:00 sync-sp500-eod-prices 완료 가정.
   30분이면 보통 충분하나, EOD 실패 시 빈 DailyPrice로 계산 → 시그널 왜곡.
4. 18:35 thesis-generate-summaries — Gemini와 18:30 analyze-news-deep-batch가
   5분 차로 같은 분당 RPM 윈도우에 들어감.
   15 RPM 한도 안에서 50기사 분석 + summary 동시 진행 시 throttle 가능.
5. 18:45 sync-news-to-neo4j (max_articles=100) + sec-sync-dirty-neo4j 동시 enqueue.
```

### 3.3 🔴 16:15/16:30/16:45 Gemini 3중 — 의도된 분산, 그러나 빠듯

코드 라인 285-286의 주석 그대로:
- `16:15` classify-news-batch (LLM)
- `16:30` analyze-news-deep-batch (Gemini, max_articles=50)
- `16:45` extract-daily-news-keywords (Gemini, comment: "16:30과 충돌 → 15분 분산")

→ 15 RPM 윈도우는 분 단위 sliding이라 30분 간격이면 충분. 그러나:
- analyze-news-deep-batch가 50 articles × 1 LLM call = 50 calls.
  순차로 실행되어도 50 calls는 3.5분 미만에 끝나면 15 RPM 초과 (50/3.5 ≈ 14.3/min, 빠듯).
- extract-daily-news-keywords가 16:45에 시작했을 때 analyze가 늦어져 끝나지 않았으면 동시 호출.

### 3.4 🟠 06:00–07:45 ET 뉴스 수집 클러스터

```
06:00  update-economic-indicators            FRED
06:00  collect-daily-news-morning            ?
06:00  neo4j-health-check                    Neo4j
06:00  sync-etf-holdings (월요일만)          FMP/SPDR
06:00  sec-check-new-filings (매월 1일만)    SEC
06:00  sec-sync-dirty (*/5)                  Neo4j

06:15  collect-sp500-news-fmp-0615           FMP × 500 symbols (orchestrator)

06:30  collect-category-news-high-morning    FMP
06:30  sec-sync-dirty (*/5)                  Neo4j

06:45  collect-general-news-fmp-morning      FMP

07:00  update-economic-indicators (6,12,18,22) → 07시 fire 안 함. 무시.
07:00  collect-category-news-medium-morning  FMP
07:00  chainsight-heat-score-daily           내부 + LLM 가능
07:00  celery-error-digest                   메일

07:30  sync-daily-market-movers              FMP
07:30  collect-category-news-low             FMP

07:45  collect-press-releases-fmp            FMP × 50
```

→ 분당 분산은 잘 되어 있으나 **FMP 호출자가 7개 (06:15, 06:30, 06:45, 07:00, 07:30 ×2, 07:45)**. 각 태스크가 내부적으로 paced/throttled 인지 확인 필요. orchestrator로 표기된 06:15는 paced로 추정.

---

## 4. Rate Limit 초과 위험 분석

### 4.1 FMP — Starter 300 calls/min, 10,000 calls/day

| 시점 | 동시 호출 태스크 | 추정 calls | 위험도 |
|------|---------------|----------|------|
| 06:15 | collect-sp500-news-fmp-orchestrator | ~500 (S&P 500 ÷ batch) | 🟠 orchestrator가 paced 가정 시 안전. **검증 필요**. |
| 09:00–16:00 매 5분 | update-realtime-prices + update-market-indices | 2 (배치) | 🟢 batch endpoint면 안전. |
| 18:00 | sync-sp500-eod-prices + collect-market-news-evening + (실제로 다음 분 18:01에 update-realtime-prices/indices는 안 함, hour 9-16) | ~501 (EOD 500 + news ~1) | 🔴 단일 분당 한도 위협. 내부 batch 확인 필요. |
| 20:00 | sync-sp500-financials | 101 (단일 일 배치) | 🟢 일별 분산이므로 분당 한도 미초과. 단, 1분 내 100+이면 borderline. |

**일별 합계 추정** (대략, 실제는 batch 효율에 의존):

```
update-realtime-prices       96회 × 1 call (batch) = 96
update-market-indices        96회 × 1 call         = 96
update-daily-prices           1 × ~5               = 5
sync-sp500-eod-prices         1 × 500 또는 batch 5 = 5–500
sync-sp500-financials         1 × 101              = 101
collect-sp500-news-fmp        5 × ~500             = ~2500 (가장 큰 항목)
collect-press-releases-fmp    1 × 50               = 50
collect-general-news-fmp      3 × 1 (general)      = 3
collect-market-news           4 × 1                = 4
collect-category-news-*       6 × variable
sync-etf-holdings (월요일)    1 × ~10 ETF
                                                   ────────
                                                   ~3000+ (10,000 daily 한도의 30%, 안전)
```

→ **일 한도는 안전. 분 한도는 18:00·06:15 등에서 borderline. 핵심: sync-sp500-eod-prices와 collect-sp500-news-fmp의 내부 pacing.**

### 4.2 Gemini Free — 15 RPM, 1500 RPD

| 시점 | 동시 LLM 호출 가능성 | 위험도 |
|------|---------|------|
| 16:30 | analyze-news-deep-batch (max 50) | 🟠 단일 태스크 50 calls / 60s = 50 RPM 초과. **내부 throttle 필수**. |
| 16:30~16:45 | analyze 잔여 + extract-daily-news-keywords | 🔴 16:45 시작 시 16:30이 끝나지 않으면 중첩. |
| 18:30 | analyze-news-deep-batch (max 50) | 🟠 위 동일. |
| 18:30~18:35 | analyze 잔여 + thesis-generate-summaries | 🔴 5분 갭은 50 articles 처리 시간(~5분 추정)과 충돌. |
| 일요일 03:30 | generate-shadow-report | 🟢 단일, 한가한 시간 |

**RPD 추정**:
- classify-news-batch × 6일/일 × ~50 = 300
- analyze-news-deep × 6 × 50 = 300
- keyword-generation × 1 × ? = ~20
- extract-daily-news-keywords × 1 × ? = ~50
- enrich-relationship-keywords × 1 × 100 = 100
- thesis-generate-summaries × 1 × ? = ~20
- chainsight-heat-score-daily × 1 = 가변
- 합계 ~800–900 RPD → 1500 한도의 60%, 일별 안전. **단 분당 한도가 항상 위협**.

### 4.3 Alpha Vantage — 5 calls/min

dict 내 AV 직접 호출 태스크 **발견되지 않음** (FMP로 마이그레이션 완료된 것으로 보임). AV 의존 태스크가 있다면 다른 곳에 숨어있을 수 있음 — Provider 추상화 확인 필요.

---

## 5. Neo4j Queue 부하 — Solo Pool 직렬화

`celery -A config worker -Q neo4j -l info --pool=solo` 가정. **동시 처리 1개**.

### 5.1 Neo4j 큐 시간당 enqueue 수

```
시각  │ 큐잉  │ 태스크
──────┼──────┼─────────────────────────────────────
00    │ 12+1 │ sec-sync-dirty×12 + neo4j-health-check
01–03 │ 12   │ sec-sync-dirty
04    │ 13   │ sec-sync + cleanup-expired-news-relationships
05    │ 13   │ sec-sync + enrich-relationship-keywords
06    │ 13   │ sec-sync + neo4j-health-check
07    │ 12   │ sec-sync
08    │ 13   │ sec-sync + sync-news-to-neo4j (08:45)
09–11 │ 12   │ sec-sync
12    │ 15   │ sec-sync + health-check + chainsight-sync-profiles + chainsight-sync-relations(12:30)
                + sync-news-to-neo4j (12:45)
13–15 │ 13   │ sec-sync + sync-news-to-neo4j (intervals)
16    │ 13   │ sec-sync + sync-news-to-neo4j (16:45)
17    │ 12   │ sec-sync
18    │ 14   │ sec-sync + health-check + sync-news-to-neo4j (18:45)
19–23 │ 12   │ sec-sync
일요일 04:30 │ +1 chainsight-neo4j-dirty-sync
```

### 5.2 🔴 sec-sync-dirty-neo4j expires=240s vs schedule */5(=300s)

```python
'schedule': crontab(minute='*/5'),
'options': {'expires': 240}
```

→ 매 5분 발사인데 expires=240초(4분). 다음 발사 1분 전에 만료.
**문제**: 워커가 일시 다운되면 만료된 메시지는 그대로 소실. 5분 윈도우의 sync 결과가 누락. expires가 schedule 주기보다 짧은 것은 의도일 수 있으나(과거 메시지 누적 방지) — 의도 명확화 필요.

### 5.3 큐 추월 시나리오

12:00에 enqueue되는 3개 (`neo4j-health-check`, `chainsight-sync-profiles-neo4j`, `sec-sync-dirty-neo4j`) 직렬 처리 가정:
- health-check ~2s
- sync-profiles-neo4j ~2~10분 (S&P 500 노드 동기화)
- sec-sync-dirty ~수십초

→ sync-profiles가 10분 걸리면 12:05의 sec-sync-dirty가 backlog. 12:10 또 enqueue → 만료된 12:05 메시지는 소실.

### 5.4 12:30 chainsight-sync-relations-neo4j 의존 추월

12:00 sync-profiles-neo4j가 30분 안에 끝나야 12:30 sync-relations-neo4j가 의도대로 동작. 실제 처리시간 미계측이면 위험.

---

## 6. 의존 체인 분석

### 6.1 EOD 파이프라인 (18:00–18:45)

```
sync-sp500-eod-prices (18:00) ─┬─► run-eod-pipeline (18:30)
                               └─► update-sp500-change-percent (18:30)

thesis-update-readings (18:00) ─► thesis-calculate-scores (18:15)
                                  ─► thesis-create-snapshots (18:30)
                                     ─► thesis-generate-summaries (18:35)
```

→ 모두 시간 기반 의존 (chord/chain 없음). 선행 태스크 지연 시 후행이 빈 데이터로 동작.

### 6.2 News Intelligence v3 (매 2시간 :15/:30/:45)

```
classify-news-batch (hh:15) ─► analyze-news-deep-batch (hh:30) ─► sync-news-to-neo4j (hh:45)
                                                                   ★ Neo4j 큐
```

→ 15분 간격이 충분한지 검증 부재. 16:15 분류 미완 시 16:30 분석은 미분류 기사 처리 안 함. 16:30 분석 미완 시 16:45 Neo4j sync는 분석 안 된 기사만 sync.

### 6.3 Chain Sight 주간 파이프라인 (토요일 02:00–05:00)

```
chainsight-all-profiles    (Sat 02:00) ─► chainsight-price-co-movement (Sat 03:00)
                                       ─► chainsight-stale-decay      (Sat 04:00)
                                       ─► chainsight-aggregate-profiles (Sat 04:30)
validation-weekly-batch    (Sat 05:00)  ─► (의존 명시 없음, 시각만)
```

→ 1시간 간격이 충분한지 미계측. S&P 500 profiles 계산이 1시간 넘으면 후행이 부분 데이터로 동작.

### 6.4 일요일 03:00–04:30 ML+Neo4j 직렬 (10건 압축)

```
03:00  cleanup-old-macro-data
03:00  train-importance-model        (ML 학습)
03:30  generate-shadow-report        ← train-importance 완료 가정
04:00  cleanup-expired-news-relationships (Neo4j)
04:00  check-auto-deploy             ← shadow-report 완료 가정
04:15  generate-weekly-ml-report     ← check-auto-deploy 완료 가정
04:20  monitor-ml-performance        ← weekly-report 완료 가정
04:30  train-lightgbm-model
04:30  chainsight-neo4j-dirty-sync   (Neo4j)
05:00  cleanup-task-results
```

→ 5분 간격(04:15→04:20)이 weekly-ml-report 완료에 충분한지 미검증. 직렬 가정인데 시간 의존만으로 묶임.

---

## 7. 발견 사항 정리

### 🔴 P0 (즉시 검증/수정 권장)

**P0-1. 시간대(TZ) 표기 혼재 — EST/UTC**
- 라인 290 주석: `16:45 EST = KST 06:45`
- 라인 744: `Heat Score 배치 (매일 07:00 UTC)` — UTC
- 라인 758: `Neo4j dirty 동기화 (매주 일요일 04:30 UTC)` — UTC
- 다른 모든 주석은 EST 표기
- crontab은 워커의 `CELERY_TIMEZONE`을 따름. settings.py 확인 필요. UTC 워커면 "EST 18:00" 주석은 실제 UTC 18:00 = EST 13:00 → 6시간 오프셋 어긋남.
- **검증**: `grep CELERY_TIMEZONE config/settings*.py` + DB의 `PeriodicTask.crontab.timezone` 확인.

**P0-2. 18:00 EOD 폭풍 — FMP 분당 한도 위협**
- sync-sp500-eod-prices가 batch endpoint 1콜인지 500콜인지 미확인.
- collect-market-news-evening도 동시.
- 내부 pacing 코드 검증 필요 (`stocks/tasks.py::sync_sp500_eod_prices`, `news/tasks.py::collect_market_news`).

**P0-3. sec-sync-dirty-neo4j 5분 주기 vs Neo4j solo pool**
- 24시간 = 288회 enqueue. solo pool로 다른 모든 Neo4j 태스크와 직렬.
- expires=240s < period 300s → 만료 메시지 소실 가능.
- 12:00·18:00에 3중 enqueue.

**P0-4. dict↔DB drift 검증 부재**
- 라인 130~133 주석: "Drift 재발 방지 체크는 수동으로 진행".
- 자동 lint/test 부재. 새 dict 항목 추가 시 DB 미반영이면 그대로 누락.

### 🟠 P1

**P1-1. 16:15/16:30/16:45 + 18:30/18:35 Gemini 15 RPM 빠듯**
- analyze-news-deep-batch가 max_articles=50으로 분당 한도 위협.
- 동일 RPM 윈도우 안 다른 LLM 태스크와 중첩 가능.
- 내부 sleep/retry 정책 검증 필요.

**P1-2. 12:00 minute=0 동시 Neo4j 3중**
- neo4j-health-check + chainsight-sync-profiles-neo4j + sec-sync-dirty-neo4j.
- sync-profiles가 ≥5분이면 다음 sec-sync 만료.

**P1-3. refresh-market-pulse-cache 매분 (시장시간 480회/일)**
- `crontab(minute='*', hour='9-16', day_of_week='1-5')`.
- 캐시 갱신이지만 8시간 × 60 = 480회. 캐시 backend(Redis) 부하 및 backing query 부하 추정 필요.

**P1-4. 09:00 minute=0 6태스크 동시**
- §3.1 참조. default queue worker 동시성 미확인.

**P1-5. 일요일 03:00–04:30 ML+Neo4j 직렬 의존 5분 간격**
- §6.4 참조. ML 학습/리포트가 5분 안에 끝나리란 보장 없음.

### 🟡 P2

**P2-1. `hour='9-16'`은 16:55까지 포함**
- crontab 표기상 9–16시 → 09:00–16:59. "장 마감 16:00 ET" 대비 1시간 추가 fire.
- 실제 시장 시간 = 9:30–16:00 ET. realtime/portfolio/pulse/screener는 9:00~16:59 동안 fire.
- 의도였는지(애프터마켓 5분 데이터 수집?) 모호.

**P2-2. Beat dict↔DB 동기화 자동화 부재** (P0-4와 연결, 우선순위는 자동 검증 도구 도입)

**P2-3. Chain Sight EOD 의존 5분 간격(추월 위험)** (§6.1 동일 패턴)

**P2-4. sec-sync-dirty-neo4j expires=240s < schedule 300s** (P0-3 부속)

### 🟢 P3

**P3-1. 휴장일/공휴일 가드 부재**
- `day_of_week='1-5'`는 평일 모두 발사. 미국 공휴일(Thanksgiving, Christmas 등) 휴장 시 시장 시간 태스크가 빈 데이터로 동작.
- 휴장 캘린더 가드 미발견.

**P3-2. minute=0 정렬, jitter 없음**
- Beat fire timestamp가 동일 minute에 spike. broker(Redis) 입장에서 부하 spike.
- crontab은 jitter 미지원. PeriodicTask 단에서 minute을 분산하거나(예: 18:00 → 18:00, 18:01, 18:02) `task.apply_async(countdown=random.randint(0,30))` 적용 가능.

---

## 8. 시각화: 외부 API 호출 히트맵 (일별 부하 추정)

```
시간 │  FMP    │ Gemini  │ FRED    │ Neo4j Q │
─────┼─────────┼─────────┼─────────┼─────────┤
 00  │   ░     │   ·     │   ·     │ ██      │
 01  │   ░     │   ·     │   ·     │ ██      │
 02  │   ░     │   ·     │   ·     │ ██      │
 03  │   ░     │   ·일요만│   ·     │ ██      │
 04  │   ░     │   ·     │   ·     │ ██▒     │ ← cleanup-expired-news
 05  │   ░     │   ▒일1   │   ·     │ ██▒     │ ← enrich-relationship-keywords
 06  │  ████   │   ·     │   ▓     │ ██▒     │ ← health-check + (sync-etf 월요일)
 07  │  ████   │   ▒     │   ·     │ ██      │ ← market-movers + press-releases
 08  │  ████   │  ████   │   ·     │ ██▒     │ ← keyword + classify + analyze 시작
 09  │  █████  │   ▒     │   ·     │ ██      │
 10  │  █████  │  ████   │   ·     │ ██▒     │
 11  │  █████  │   ·     │   ·     │ ██      │
 12  │  █████  │  ████   │   ▓     │ █████   │ ★ Neo4j 3중
 13  │  █████  │   ·     │   ·     │ ██      │
 14  │  █████  │  ████   │   ·     │ ██      │
 15  │  █████  │   ·     │   ·     │ ██      │
 16  │  █████  │ ██████  │   ·     │ ██▒     │ ★ Gemini 3중 (16:15/30/45)
 17  │  ███    │   ·     │   ·     │ ██      │
 18  │  ████   │ █████   │   ▓     │ ███     │ ★★ EOD 폭풍
 19  │   ░     │   ·     │   ·     │ ██      │
 20  │  ███    │   ·     │   ·     │ ██      │ ← sync-sp500-financials
 21  │   ░     │   ·     │   ·     │ ██      │
 22  │   ░     │   ·     │   ▓     │ ██      │
 23  │   ░     │   ·     │   ·     │ ██      │
─────┴─────────┴─────────┴─────────┴─────────┘

범례: ·  =0    ░ =1-2   ▒/▓ =3-10   ██ =10-50   ████ =50-200   █████/██████ =200+
```

---

## 9. 권장 검증 순서 (코드 수정 전 사실 확인)

1. **TZ 확정**: `grep -n CELERY_TIMEZONE config/settings*.py` + Django shell에서 `PeriodicTask.objects.values('name','crontab__timezone').distinct()`.
2. **DB↔dict drift**: `python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(set(PeriodicTask.objects.values_list('name', flat=True)))"` ⟷ dict 키 비교.
3. **FMP batch 확인**: `stocks/tasks.py::sync_sp500_eod_prices` 내부 — symbol loop인지 batch quote인지.
4. **Gemini throttle 확인**: `news/tasks.py::analyze_news_deep` 내부 sleep/semaphore.
5. **sec-sync-dirty 실측 소요시간**: 최근 7일 TaskResult 평균 — backlog 발생 빈도.
6. **18:00 클러스터 실측**: 같은 분 발사한 6개 태스크의 평균 latency / failure 율.

각 항목 검증 결과에 따라 일부 P0/P1이 false positive로 강등될 수 있음.

---

## 10. 본 감사의 한계

- 코드 수정 금지 — 실측·재현 불가, 정적 분석만.
- DB의 PeriodicTask 실제 등록 상태 미조회 (드리프트 가능성 상존).
- 각 태스크 내부 batch/throttle 코드 미열람 — 외부 API 호출량은 schedule 빈도 기반 **추정**.
- crontab timezone은 settings.py 의존 — 본 보고서는 주석 표기를 그대로 사용.
- "Gemini LLM" 분류는 task 이름 기반 추정. classify-news-batch 등은 LLM/ML 어느 쪽 구현인지 코드 확인 필요.
- 휴장일(NYSE 공휴일) 캘린더 가드 부재는 dict 안에서 확인 — 외부 가드(예: 각 task 진입부에서 holiday check) 가능성 미확인.

---

**작성**: 2026-05-28 (Read-only)
**Source**: `/Users/byeongjinjeong/Desktop/stock_vis/config/celery.py` lines 1-820
**Cross-ref**: CLAUDE.md Bug #28 (Beat schedule drift), Audit P0 #8 (line 285-286), Audit P0 #15 (line 672)
