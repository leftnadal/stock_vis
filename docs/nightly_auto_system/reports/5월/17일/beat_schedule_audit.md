# Beat Schedule Audit — 2026-05-17

> **읽기 전용 감사** · 코드/스케줄 수정 없음 · `config/celery.py:135-814` 기준
>
> Beat Scheduler: `django_celery_beat.schedulers:DatabaseScheduler` (`config/settings.py:483`)
> **주의**: `app.conf.beat_schedule` dict는 런타임에 무시됨 — DB의 `PeriodicTask` 테이블이 진실의 소스. 본 보고서는 코드 dict를 reference로 분석하나, 실제 운영 스케줄과의 drift 가능성은 §7 마지막에 명시.

---

## 0. 요약 (Executive Summary)

| 항목 | 값 |
|---|---|
| 전체 beat 엔트리 | **76개** |
| 평일 시장 시간(09:00~16:59 ET) 시간당 평균 태스크 | **~110건/시간** (피크) |
| 야간(00~05 ET) 시간당 평균 | **15~25건/시간** |
| Default queue 적재 | 73개 |
| Neo4j queue 적재 (solo pool) | 10개 (단일 소비자 직렬화 위험) |
| **P0 위험** | Neo4j solo pool 12:00 정각 3중 충돌 + sec-sync-dirty-neo4j 5분 주기 점유 |
| **P0 위험** | Gemini 18:30 analyze-deep(50건) + 18:35 thesis-summaries 5분 갭 — 14:45/16:45 동일 패턴 |
| **P1 위험** | FMP 18:00 정각에 sync-sp500-eod-prices + thesis-update-readings + collect-market-news-evening 동시 → 단일 분 500+ calls 추정 |
| **P1 위험** | 09:00 정각 6종 시작 동시 트리거 + 매분 refresh-market-pulse-cache → backend worker 적체 |

---

## 1. 스케줄 인벤토리 (앱별)

### 1.1 Stocks (5개)
| name | cron | queue | rate-limit 영향 |
|---|---|---|---|
| update-realtime-prices | `*/5` 9-16 Mon-Fri | default | **FMP** (S&P 500 일괄) |
| update-daily-prices | 17:00 Mon-Fri | default | FMP |
| aggregate-weekly-prices | Sat 01:00 | default | DB만 |
| sync-sp500-financials | 20:00 Mon-Fri | default | **FMP** 101개/일 |
| update-sp500-change-percent | 18:30 Mon-Fri | default | DB만 |

### 1.2 Macro (5개)
| name | cron | queue | rate-limit 영향 |
|---|---|---|---|
| update-economic-indicators | 6,12,18,22 :00 Mon-Fri | default | FRED (자체 한도) |
| update-market-indices | `*/5` 9-16 Mon-Fri | default | **FMP** 지수 |
| update-economic-calendar | 매일 01:00 | default | FMP |
| refresh-market-pulse-cache | `*` 매분 9-16 Mon-Fri | default | 캐시 read-only |
| cleanup-old-macro-data | Sun 03:00 | default | DB만 |

### 1.3 RAG Analysis (1개)
| name | cron | queue |
|---|---|---|
| neo4j-health-check | 0,6,12,18 :00 매일 | **neo4j** |

### 1.4 Serverless / Market Movers (10개)
| name | cron | queue | 주요 API |
|---|---|---|---|
| sync-daily-market-movers | 07:30 Mon-Fri | default | FMP |
| keyword-generation-pipeline | 08:00 매일 (gainers) | default | **Gemini** |
| sync-etf-holdings | Mon 06:00 | default | SPDR XLSX |
| sync-supply-chain-batch | 매월 15일 03:00 | default | SEC EDGAR |
| calculate-market-breadth | 16:30 Mon-Fri | default | DB |
| calculate-sector-heatmap | 16:35 Mon-Fri | default | DB |
| check-screener-alerts | `*/15` 9-16 Mon-Fri | default | DB |
| extract-news-relations | 매일 09:00 | default | DB |
| enrich-relationship-keywords | 매일 05:30 | **neo4j** | **Gemini** (limit=100) |
| sync-institutional-holdings | 매월 16일 04:00 | default | SEC 13F |
| scan-regulatory-relationships | Mon 04:00 | default | SEC |
| build-patent-network | 매월 1일 04:30 | default | USPTO |

### 1.5 News (수집 + 분석, 21개)
| name | cron | queue | 주요 API |
|---|---|---|---|
| collect-daily-news-morning | 06:00 Mon-Fri | default | FMP/Finnhub/Marketaux |
| collect-daily-news-afternoon | 14:30 Mon-Fri | default | ↑ |
| collect-market-news-{4종} | 08/12/15/18 :00 Mon-Fri | default | ↑ |
| extract-daily-news-keywords | 매일 16:45 | default | **Gemini** |
| collect-category-news-high-{3종} | 06:30/13:00/17:00 Mon-Fri | default | FMP/etc |
| collect-category-news-medium-{2종} | 07:00/14:00 Mon-Fri | default | ↑ |
| collect-category-news-low | 07:30 Mon-Fri | default | ↑ |
| classify-news-batch | 8/10/12/14/16/18 :15 Mon-Fri | default | DB+규칙 엔진 |
| analyze-news-deep-batch | 8/10/12/14/16/18 :30 Mon-Fri | default | **Gemini** (max=50) |
| collect-ml-labels | 19:00 Mon-Fri | default | FMP 가격 |
| sync-news-to-neo4j | 8/10/12/14/16/18 :45 Mon-Fri | **neo4j** | Neo4j (max=100) |
| cleanup-expired-news-relationships | 매일 04:00 | **neo4j** | Neo4j |
| train-importance-model / generate-shadow-report / check-auto-deploy / generate-weekly-ml-report / monitor-ml-performance / train-lightgbm-model | Sun 03:00~04:30 | default | DB/ML |
| check-pipeline-alerts | `*/30` 24/7 | default | DB |
| aggregate-daily-sentiment | 09:00 Mon-Fri | default | DB |

### 1.6 News FMP 대량 수집 (5+1+3=9개)
| name | cron | queue |
|---|---|---|
| collect-sp500-news-fmp-{0615/1015/1315/1515/1715} | Mon-Fri | default — **FMP S&P 500 orchestrator** |
| collect-press-releases-fmp | 07:45 Mon-Fri | default |
| collect-general-news-fmp-{morning/noon/evening} | 06:45/12:30/17:45 Mon-Fri | default |
| archive-old-articles | 매월 1일 02:30 | default |

### 1.7 EOD + Thesis Pipeline (4+4=8개)
| name | cron | queue |
|---|---|---|
| sync-sp500-eod-prices | 18:00 Mon-Fri | default — **FMP 일괄** |
| sync-sp500-constituents | 매월 1일 02:00 | default |
| run-eod-pipeline | 18:30 Mon-Fri | default — DB |
| backfill-signal-accuracy | 19:00 Mon-Fri | default |
| refresh-korean-overviews-monthly | 매월 1일 03:00 | default — **Gemini** |
| thesis-update-readings | 18:00 Mon-Fri | default — **FMP/Finnhub** |
| thesis-calculate-scores | 18:15 Mon-Fri | default |
| thesis-create-snapshots | 18:30 Mon-Fri | default |
| thesis-generate-summaries | 18:35 Mon-Fri | default — **Gemini** |

### 1.8 Chain Sight v2 (10개)
| name | cron | queue |
|---|---|---|
| chainsight-all-profiles | Sat 02:00 | default |
| chainsight-co-mentions | 매일 10:00 | default |
| chainsight-price-co-movement | Sat 03:00 | default |
| chainsight-relation-confidence | 매일 11:00 | default |
| chainsight-stale-decay | Sat 04:00 | default |
| chainsight-aggregate-profiles | Sat 04:30 | default |
| chainsight-sync-profiles-neo4j | 매일 12:00 | **neo4j** |
| chainsight-sync-relations-neo4j | 매일 12:30 | **neo4j** |
| chainsight-heat-score-daily | 매일 07:00 (UTC로 해석 가능, 주석 모호) | default |
| chainsight-seed-selection | 매일 13:00 (UTC?) | default |
| chainsight-neo4j-dirty-sync | Sun 04:30 | **neo4j** |

### 1.9 Validation + SEC Pipeline + 잡무 (6개)
| name | cron | queue |
|---|---|---|
| validation-weekly-batch | Sat 05:00 | default |
| sec-sync-dirty-neo4j | `*/5` 24/7 | **neo4j** — **솔로 pool 상시 점유** |
| sec-seed-relations-to-chainsight | 매일 12:00 | default |
| sec-check-new-filings | 매월 1일 06:00 | default |
| celery-error-digest | 매일 07:00 | default |
| cleanup-task-results | Sun 05:00 | default |

> **TZ 주석 불일치**: 본문 주석 다수가 "EST"라고 표기하나 일부 chainsight 항목은 "UTC"라고 명시. Celery `crontab()` 기본 TZ는 Django `TIME_ZONE` 설정에 종속. 본 보고서는 모든 시간을 **단일 시간대로 해석한 표기 그대로** 다루며, 실제 실행 TZ는 §7에 별도 점검 항목으로 남김.

---

## 2. 시간대별 태스크 트리거 히트맵 (평일 기준, 분당 호출 환산)

`crontab(minute='*/5', hour='9-16')` 같은 반복 패턴은 시간당 누적 트리거 횟수로 환산. 한 번만 발화하는 단일 항목은 1로 카운트. 셀 값 = "시간 동안 트리거되는 태스크 인스턴스 합".

```
Hour | Count  Bar (■=10건)
-----|------+--------------------------------------------------
 00  |   15 | ■▌
 01  |   16 | ■▌
 02  |   16 | ■▌
 03  |   17 | ■▌
 04  |   18 | ■▊
 05  |   17 | ■▌
 06  |   22 | ██▎
 07  |   21 | ██
 08  |   20 | ██
 09  |  110 | ███████████        ◀ 시장 개장 + minute=* 발화
 10  |  113 | ███████████▎
 11  |  109 | ███████████
 12  |  118 | ███████████▊       ◀ PEAK + Neo4j 3중 충돌
 13  |  112 | ███████████▏
 14  |  113 | ███████████▎
 15  |  110 | ███████████
 16  |  115 | ███████████▌       ◀ EOD 시작 + Gemini analyze-deep
 17  |   18 | █▊
 18  |   28 | ██▊                ◀ EOD/Thesis 18:00/18:15/18:30/18:35 클러스터
 19  |   16 | ■▌
 20  |   15 | ■▌                ◀ S&P 재무제표 시작
 21  |   14 | ■▍
 22  |   15 | ■▌
 23  |   14 | ■▍
```

**카운트 산식 (시장 시간 09~16시)**:
- refresh-market-pulse-cache: 60 / hour (분당 1회)
- update-realtime-prices: 12 / hour (5분마다)
- update-market-indices: 12 / hour (5분마다)
- calculate-portfolio-values: 6 / hour (10분마다)
- check-screener-alerts: 4 / hour (15분마다)
- sec-sync-dirty-neo4j: 12 / hour (5분마다, 전 시간대 공통)
- check-pipeline-alerts: 2 / hour (30분마다, 전 시간대 공통)
- + 개별 정각 발화 1~10개

> 09:00~16:00 베이스라인 = **94/hour** (시장 인디케이터 + 공통). 여기에 개별 트리거가 가산되어 110~118/hour. **분당 평균 1.8건의 태스크가 큐에 push**된다.

---

## 3. Rate Limit 초과 구간 분석

### 3.1 FMP (Starter 300 calls/min, 10,000/day)

**위험 윈도우 1: 18:00 정각 동시 트리거**
| 18:00 발화 태스크 | 추정 FMP calls |
|---|---|
| `sync-sp500-eod-prices` | ~500 (S&P 500 EOD batch — orchestrator) |
| `thesis-update-readings` | ~50~200 (지표 카탈로그 의존) |
| `update-economic-indicators` | 0 (FRED) |
| `collect-market-news-evening` | ~10 |
| `collect-general-news-fmp-evening`(17:45 잔재) | ~5 |

→ **분당 600+ calls 추정. 300/min 초과 가능. orchestrator가 내부 throttle을 갖지 않으면 초과 확실.** sync-sp500-eod-prices 코드 내부 페이싱 여부를 §7에서 검증 필요.

**위험 윈도우 2: 09:00 시장 개장 동시 시작**
| 09:00 발화 | 동시성 |
|---|---|
| `update-realtime-prices` 첫 5분 슬롯 | S&P 500 / 5분 (=100 calls?) |
| `update-market-indices` 첫 슬롯 | 5~10 calls |
| `aggregate-daily-sentiment` | 0 |
| `extract-news-relations` | 0 |
| `refresh-market-pulse-cache` 첫 분 | 0 (캐시) |
| `calculate-portfolio-values` 첫 슬롯 | 0~사용자수 |

→ FMP 호출은 100~150 추정. 한도 내. 단 update-realtime-prices가 *모든* S&P 500을 매 5분 호출하면 12회/hour × 500 = 6000 calls/hour → 일일 한도(10000) 1.5시간이면 소진. **실제 구현이 batch 단일 endpoint(quotes batch) 사용 시 1 call/5min로 떨어짐 — 구현 확인 필요.**

**위험 윈도우 3: 매시 :15 collect-sp500-news-fmp-* orchestrator**
- 06:15 / 10:15 / 13:15 / 15:15 / 17:15 (5회/평일)
- S&P 500 orchestrator → 종목당 1 API call이면 500/min 초과. 일반적으로 chunk 단위 throttle 구현 가정.

**일일 누적 FMP 호출 추정 (보수적)**:
- update-realtime-prices: 96 (12×8h) — batch 가정
- update-market-indices: 96
- sync-sp500-eod-prices: ~500
- thesis-update-readings: ~100
- sync-sp500-financials: ~100 (101개/일 명시)
- collect-sp500-news-fmp × 5회: 2,500
- collect-press-releases-fmp: ~50
- collect-general-news-fmp × 3: ~30
- collect-market-news × 4: ~40
- collect-daily-news × 2: ~20
- collect-ml-labels: ~200
- update-economic-calendar: ~5

→ **합계 ≈ 3,700~5,000 calls/day**. 일일 한도 50% 사용. 마진 적정.

### 3.2 Gemini Free (15 RPM / 1,500 RPD)

**Gemini 호출 태스크 인벤토리**:
| task | 시각 | 추정 호출 수 |
|---|---|---|
| `keyword-generation-pipeline` | 08:00 매일 | 변동 (gainers 종목 수) |
| `analyze-news-deep-batch` | 8/10/12/14/16/18 :30 Mon-Fri | **최대 50/회 × 6 = 300/day** |
| `extract-daily-news-keywords` | 16:45 매일 | ~50 |
| `enrich-relationship-keywords` | 05:30 매일 | **최대 100** (limit kwarg) |
| `thesis-generate-summaries` | 18:35 Mon-Fri | 활성 가설 수 (수십~수백) |
| `refresh-korean-overviews-monthly` | 매월 1일 03:00 | ~500 (월 1회) |

**일일 누적**: 평일 기준 300 + 50 + 100 + 가변(thesis/keyword) ≈ **500~800 calls/day** → 1,500 RPD 내. 안전 마진 50%.

**위험 윈도우 — 분당 15 RPM 초과**:

🔴 **P0 #1**: `analyze-news-deep-batch` 단일 실행이 50건 분석 시 **rate-limit 미적용 시 50/분 = 15 RPM 초과**.
- 18:30 발화 → 50건 처리 → 5분 후 18:35 `thesis-generate-summaries` 시작.
- 만약 18:30 배치가 5분 내 미완료 시 두 태스크가 **동일 Gemini API 키 공유 + 동시 호출** → 429.
- 동일 패턴: 14:30 ↔ 14:35(없음), 16:30 ↔ 16:45(extract-daily-news-keywords) → 15분 간격은 P0 #8(주석)로 분산됐으나 **18:30↔18:35는 5분 간격으로 미분산**.

🟡 **P1 #2**: 16:30 `analyze-news-deep-batch` ↔ 16:45 `extract-daily-news-keywords` → 코드 주석에 "audit P0 #8, 2026-04-26"로 15분 분산 완료. 단 분석 배치가 15분 초과 시 여전히 겹침. soft_time_limit=1800s(30분)이므로 **15분 갭은 충돌 회피 보장 안 됨**.

🟡 **P1 #3**: `enrich-relationship-keywords` 05:30 (limit=100) → 분당 15회 throttle 없으면 6.7분 소요. 06:00 `collect-daily-news-morning`(Gemini 미사용)과는 무관하나 enrich가 06:00 넘어가면 Gemini 키 공유 위험. **현재 코드 한정에서 06:00 Gemini 호출 태스크 없음 → 안전**.

### 3.3 Alpha Vantage (5 calls/min)

`grep -r ALPHA_VANTAGE **/tasks.py` → **직접 호출 없음**. `.env.example` 및 worker shell, BACKEND_ARCHITECTURE.md, KEYWORD_DATA_COLLECTION_ARCHITECTURE.md 문서 reference만 존재.

→ Provider 추상화 fallback 경로에서 호출될 가능성 (e.g., FMP 실패 시 AV 사용). 본 beat schedule 한정 **직접 트리거 없음. 분당 5 calls 초과 위험 = 0**.

> 점검 권고: `stocks.tasks.update_realtime_with_provider` 내부 Provider 체인에서 AV가 backup으로 들어가는지 확인 필요 — beat 스케줄과 무관한 호출 빈도.

---

## 4. Queue 몰림 분석

### 4.1 Default queue (73 entries)

피크 시간대(09~16시) 시간당 ~110 push. **soft_time_limit 가장 긴 태스크**:
- `train-importance-model`: 3600s
- `train-lightgbm-model`: 7200s (`expires`)
- `analyze-news-deep-batch`: 1800s
- `sync-news-to-neo4j`: 600s
- `keyword-generation-pipeline`: ?

평일 09:00~17:00 default worker 처리 부하 = 약 8 × 110 = **880 task/8h**. prefork worker(macOS solo pool 강제, Linux prefork 권장)에서 워커 수가 1~2개면 적체 가능.

### 4.2 Neo4j queue (solo pool, 동시 1개)

**Neo4j queue 트리거 일정 (24시간)**:

```
Time | Task
-----|-----------------------------------------------------------
00:00| neo4j-health-check + sec-sync-dirty
00:05| sec-sync-dirty
00:10| sec-sync-dirty
...   (5분마다 sec-sync-dirty 상시 점유)
04:00| cleanup-expired-news-relationships + sec-sync-dirty 충돌
04:30| Sun: chainsight-neo4j-dirty-sync + sec-sync-dirty 충돌
05:30| enrich-relationship-keywords + sec-sync-dirty 충돌
06:00| neo4j-health-check + sec-sync-dirty 충돌
08:45| sync-news-to-neo4j + sec-sync-dirty 충돌
10:45| sync-news-to-neo4j + sec-sync-dirty 충돌
12:00| neo4j-health-check + chainsight-sync-profiles-neo4j
      + sec-sync-dirty ◀◀◀ 3중 충돌
12:30| chainsight-sync-relations-neo4j + sec-sync-dirty 충돌
12:45| sync-news-to-neo4j + sec-sync-dirty 충돌
14:45| sync-news-to-neo4j + sec-sync-dirty 충돌
16:45| sync-news-to-neo4j + sec-sync-dirty 충돌
18:00| neo4j-health-check + sec-sync-dirty 충돌
18:45| sync-news-to-neo4j + sec-sync-dirty 충돌
```

🔴 **P0 #4 (Neo4j solo pool 적체)**:
- `sec-sync-dirty-neo4j`가 5분마다 `expires=240`로 push → **24시간 동안 매 5분 점유**.
- 다른 9종의 neo4j 태스크는 모두 sec-sync와 race condition.
- sec-sync가 240초(4분) 안에 종료되지 않으면 **다음 sec-sync는 expires로 폐기, 이후 큐는 빈 채로 다른 태스크가 진입 가능**. 하지만 정확히 정각/30분 정각/45분 정각에 발화하는 다른 태스크는 sec-sync 점유 중일 가능성이 높음.
- **12:00 3중 충돌**: neo4j-health-check + chainsight-sync-profiles + sec-sync → 1순위 진입 후 나머지 2개는 queue 적체. 만약 chainsight-sync-profiles가 expires=3600 내 시작 못 하면 폐기.
- expires=240인 sec-sync는 4분 안에 처리 못 받으면 폐기. **사실상 5분 주기 health 카운팅용**으로 동작 가능. 진짜 실패한 sec evidence는 다음 주기에 또 시도되므로 **결과적으로 데이터 유실 위험은 낮음** — 단 dirty queue 길이가 커지면 catch-up 어려움.

🟡 **P1 #5 (sync-news-to-neo4j 직렬화)**:
- 8/10/12/14/16/18시 :45 발화 (6회/평일)
- max_articles=100, sync_batch 실행 시간 미상
- 직전 5분(40, 41, 42, 43, 44분 sec-sync 슬롯)과 충돌 → :45 sec-sync 발화 직전.
- **실제 :45 sec-sync(분 5의 배수: 45) 발화와 동시. 정확히 같은 분에 발화.**

→ `crontab(minute='*/5')`은 0,5,10,...,45,50,55. → `sync-news-to-neo4j`의 minute=45와 정확히 같은 분 — **동분 정면 충돌**.

### 4.3 Beat 단일 노드 가정

`celery beat -l info` 단일 인스턴스 가정. DatabaseScheduler 기반이므로 다중 beat 실행 시 lock 경합. 본 보고서는 단일 beat 가정 (`scripts/celery-beat.sh`).

---

## 5. 스케줄 겹침 / 의존성 분석

### 5.1 정각 동시 발화 클러스터

**18:00 정각 (평일)**: 5개 동시 트리거
- `sync-sp500-eod-prices` (FMP 무거움)
- `thesis-update-readings` (FMP)
- `update-economic-indicators` (FRED)
- `collect-market-news-evening` (FMP/외부)
- `neo4j-health-check` (neo4j queue)

→ 의존성: `thesis-update-readings`(18:00) → `thesis-calculate-scores`(18:15) → `thesis-create-snapshots`(18:30) → `thesis-generate-summaries`(18:35). **15분 갭은 readings/scores가 그 안에 끝난다는 가정**. readings는 FMP 호출이 100~200건이면 가능하나, sync-sp500-eod-prices와 동분 발화 → FMP 키 공유 시 throttle. **30분 갭이 안전**.

🔴 **P0 #6**: `run-eod-pipeline`(18:30) ↔ `thesis-create-snapshots`(18:30) ↔ `analyze-news-deep-batch`(18:30) → **정확히 동분 발화**. 3종 모두 무거운 배치. analyze-deep는 Gemini, run-eod는 DB 집약. 의존 관계는 없으나 default worker 풀에서 자원 경합. 5분 뒤 `thesis-generate-summaries`(18:35) → run-eod의 산출물에 의존하지 않으나 Gemini 키 공유.

### 5.2 매분 polling 태스크

`refresh-market-pulse-cache`: `crontab(minute='*')` + `hour='9-16'` → **60회/시간, 평일 8시간 = 480회/일**. expires 미설정. 캐시 갱신은 빠르지만 default worker 풀에 매분 1 push.

`sec-sync-dirty-neo4j`: `crontab(minute='*/5')` → 24×12 = **288회/일, neo4j queue 직렬화**.

### 5.3 종속성 위반 가능성

| 선행 → 후행 | 갭 | 위험 |
|---|---|---|
| sync-sp500-eod-prices(18:00) → run-eod-pipeline(18:30) | 30분 | sync가 30분 초과 시 EOD 파이프라인이 stale 데이터로 시작 |
| thesis-update-readings(18:00) → thesis-calculate-scores(18:15) | 15분 | readings가 15분 초과 시 빈 데이터로 score 계산 |
| analyze-news-deep-batch(8:30) → sync-news-to-neo4j(8:45) | 15분 | analyze가 15분 초과 시 sync가 빈 결과 |
| collect-daily-news(06:00) → classify-news-batch(08:15) | 2h 15m | 안전 |
| aggregate-daily-sentiment(09:00) → extract-news-relations(09:00) | **동시 발화** | sentiment 결과를 relations이 참조하면 race |
| chainsight-co-mentions(10:00) → chainsight-relation-confidence(11:00) | 1h | 안전 |
| chainsight-sync-profiles-neo4j(12:00) → chainsight-sync-relations-neo4j(12:30) | 30분, neo4j queue solo pool 직렬 + sec-sync 점유 | profiles이 30분 초과 시 relations 적체 |

🟡 **P1 #7**: `aggregate-daily-sentiment`와 `extract-news-relations` 모두 09:00 정각. 시장 개장 + minute=0 클러스터에 합류. 코드상 read-only일 수 있으나 직렬 의존 시 race.

🟡 **P1 #8**: `extract-daily-news-keywords`(16:45) ↔ `sync-news-to-neo4j`(16:45) → **동분 발화**. Gemini와 Neo4j 큐로 분리되므로 자원 충돌은 없으나 worker pool은 default 공유 (sync-news-to-neo4j는 routing이 default→neo4j로 작동, extract는 default).

### 5.4 macOS solo pool 영향

`config/celery.py:30-31` — macOS에서는 모든 워커가 solo pool. **동시 처리량 = 1**. 개발 환경에서만 적용되나, 보고서는 운영 Linux prefork 가정 + macOS 단일 환경에서는 **모든 default queue 태스크가 직렬 처리**됨을 기록.

---

## 6. 우선순위 별 권고 (참고만, 본 작업은 read-only)

| # | 우선순위 | 항목 | 추후 검토 권고 |
|---|---|---|---|
| 1 | 🔴 P0 | Gemini 18:30↔18:35 5분 갭 (analyze-deep 50건 / thesis-summaries) | 18:35 → 18:50 분산, 또는 analyze-deep 내부 throttle 확인 |
| 2 | 🔴 P0 | Neo4j 12:00 3중 충돌 + sec-sync 5분 주기 점유 | sec-sync 주기를 15분으로 완화 또는 별도 큐 분리 |
| 3 | 🔴 P0 | run-eod-pipeline / thesis-create-snapshots / analyze-news-deep-batch 18:30 동분 발화 | 18:35/18:40으로 5분 stagger |
| 4 | 🟠 P1 | sync-sp500-eod-prices 18:00 + thesis-update-readings 18:00 FMP 동시 호출 | thesis-readings를 18:05로 stagger |
| 5 | 🟠 P1 | sync-news-to-neo4j :45 ↔ sec-sync :45 동분 충돌 | sync-news를 :42 또는 :47로 이동 |
| 6 | 🟠 P1 | 09:00 정각 6종 클러스터 + 매분 refresh-market-pulse-cache | 09:01 stagger |
| 7 | 🟡 P2 | aggregate-daily-sentiment ↔ extract-news-relations 09:00 동시 | 서비스 코드에서 의존성 확인 |
| 8 | 🟡 P2 | analyze-news-deep-batch soft_time_limit=1800s vs 15분 다음 sync 갭 | soft_time_limit 단축 또는 sync 갭 확대 |
| 9 | 🟡 P2 | TZ 주석 EST/UTC 혼재 (chainsight-heat-score-daily 등) | settings TIME_ZONE 확정 + 주석 일관화 |

---

## 7. 추가 검증 필요 (코드 외부 의존)

1. **DatabaseScheduler drift**: `config/celery.py:128-133` 주석 — config dict와 `PeriodicTask` DB 항목이 어긋나면 dict는 무시됨. 본 보고서는 dict 기준이나 **실제 운영 스케줄은 `python manage.py shell`에서 `PeriodicTask.objects.values_list('name','enabled','last_run_at')` 검증 필요**.

2. **TIME_ZONE 확인**: `crontab(hour=N)`의 N이 어느 TZ로 해석되는지. `config/settings.py`의 `CELERY_TIMEZONE` 또는 `TIME_ZONE` 점검.

3. **Provider AV fallback**: `stocks.tasks.update_realtime_with_provider`가 FMP 실패 시 Alpha Vantage 5/min 한도를 침범하는지.

4. **orchestrator 내부 throttle**: `collect_sp500_news_fmp_orchestrator`, `sync_sp500_eod_prices`, `thesis-update-readings`가 내부에서 `time.sleep()` 또는 chunked dispatch를 하는지. 안 한다면 §3.1 P1 #4가 P0로 격상.

5. **분당 Gemini RPM 실측**: `analyze_news_deep`/`enrich_relationship_keywords`/`thesis-generate-summaries`가 15 RPM throttle을 자체 구현했는지 — 없으면 §3.2 P0 #1이 즉시 발생.

6. **expires 240 < scheduling interval 300**의 의미: `sec-sync-dirty-neo4j`는 다음 발화 전 만료 → solo pool이 막혀 있어도 데이터 손실은 없지만 catch-up 누락 발생.

---

## 8. 데이터 정확성 노트

본 보고서의 모든 수치는 `config/celery.py:135-814` 코드 dict 기준. DB `PeriodicTask` 실제 상태와의 drift는 검증하지 않았으며, §7-1에 점검 권고로 남김. dirty/expires 동작은 Celery 공식 문서 기준 의미론으로 해석.

**카운트 메서드**: 시간당 발화 횟수는 `crontab` minute 패턴에서 직접 계산. e.g., `minute='*/5'` = 12/hour, `minute='*'` = 60/hour, `minute=0` = 1/hour. `expires`는 카운트에 영향 없음 (push 시점 기준).

---

*생성: 2026-05-17 · 도구: read-only audit · 입력: `/Users/byeongjinjeong/Desktop/stock_vis/config/celery.py` · 출력: `docs/nightly_auto_system/reports/5월/17일/beat_schedule_audit.md`*
