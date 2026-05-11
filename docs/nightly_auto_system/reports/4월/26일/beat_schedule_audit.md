# Beat Schedule Audit — 2026-04-26

**감사 대상**: `config/celery.py` `app.conf.beat_schedule`
**감사 방식**: 읽기 전용 정적 분석 (코드 수정 없음)
**Celery 설정 컨텍스트**:
- `CELERY_TIMEZONE = 'America/New_York'` (`config/settings.py:393`)
- `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` ⇒ **dict는 런타임에서 무시되고 DB의 `PeriodicTask`가 진실의 소스**. 본 감사는 dict의 "선언적 reference" 기준이며, 실제 실행은 DB와 다를 수 있음.
- `IS_MACOS`인 경우 `worker_pool='solo'` 강제 (개발 환경 한정)
- Neo4j 큐 라우팅: 별도 `--pool=solo` 워커 1개 가정

총 등록 항목: **84개** (`grep -c 'schedule' = 89`이지만 docstring·주석 5건 차감)

---

## 1. Executive Summary (TL;DR)

| 위험도 | 항목 | 근거 |
|--------|------|------|
| **🔴 HIGH** | NY 18:00–18:45 동시 폭주 | EOD FMP 500콜 + Gemini LLM + Thesis 3태스크 + News classify/analyze/sync 동시 시작 |
| **🔴 HIGH** | NY 12:00–12:45 neo4j 큐 6중 적체 | solo pool인데 chainsight×2 + sec-seed + sync-news-to-neo4j + neo4j-health-check 겹침 |
| **🔴 HIGH** | `sec-sync-dirty-neo4j` 5분 주기 | 1일 288회 neo4j queue 점유, solo pool에서 1회 실행이 5분 초과 시 즉시 적체 |
| **🟡 MED** | "UTC" 주석 ↔ 실제 NY 시간 드리프트 | `chainsight-heat-score-daily/seed-selection/neo4j-dirty-sync` 주석은 UTC라 적혀있으나 Celery는 NY 타임존에서 실행 |
| **🟡 MED** | FMP 5회 S&P 500 뉴스 폭주 | 6:15/10:15/13:15/15:15/17:15 매번 ~500 콜 → Starter 300/min 한도에 충돌 가능 |
| **🟡 MED** | 일요일 03:00–04:30 ML 훈련 클러스터 | 8개 태스크 직렬 의존 (importance→shadow→deploy→weekly→monitor→lightgbm) — 한 개라도 실패하면 다음 태스크 무근거 실행 |
| **🟢 LOW** | Alpha Vantage 의존 스케줄 | `df85496 refactor: Alpha Vantage provider 전면 제거` 이후 AV는 어떤 Beat 태스크도 사용하지 않음 → **AV rate limit 위험 사실상 0** |

---

## 2. 스케줄 인벤토리 (요약)

### 큐별 분포

| Queue | 태스크 수 | 비고 |
|-------|----------|------|
| default | 76 | prefork (Linux) / solo (macOS) |
| neo4j | 13 | **solo pool 1개 = 동시 처리 1건** |

`task_routes` 기준 neo4j 큐 라우팅 13건:
- `rag_analysis.tasks.{health_check_neo4j, sync_stock_to_neo4j, ...}`
- `news.tasks.{sync_news_to_neo4j, cleanup_expired_news_relationships}`
- `serverless.tasks.enrich_relationship_keywords`
- `chainsight.tasks.sync_tasks.{sync_profiles_to_neo4j, sync_relations_to_neo4j}`
- `chainsight-neo4j-dirty-sync`
- `sec_pipeline.tasks.sync_dirty_to_neo4j`

### 주기별 분포

| 주기 | 태스크 수 | 대표 항목 |
|------|----------|-----------|
| 매분 (9–16시) | 1 | `refresh-market-pulse-cache` (60×8 = 480회/일) |
| 5분 | 4 | `update-realtime-prices`, `update-market-indices`, `sec-sync-dirty-neo4j`(24h), `update-realtime-prices` |
| 10분 | 1 | `calculate-portfolio-values` |
| 15분 | 1 | `check-screener-alerts` |
| 30분 | 1 | `check-pipeline-alerts` (24h) |
| 6시간 | 1 | `neo4j-health-check` (0/6/12/18시) |
| 일별 평일 | 36 | 주력 운영 태스크 |
| 일별 daily(요일 무관) | 12 | `cleanup-expired-news-relationships`, chainsight 관계 등 |
| 주별 (월/일/토) | 14 | ML 훈련, ETF, regulatory, validation 등 |
| 월별 (1일/15일/16일) | 6 | constituents, archive, supply chain, institutional, patent, sec-check |

---

## 3. Rate Limit 초과 구간 분석

### 3.1 FMP (Starter plan 300 calls/min)

#### 일별 FMP 콜 추정 (평일)

| 시간(NY) | 태스크 | 추정 콜 수 | 비고 |
|---------|--------|----------|------|
| 06:00 | `collect-daily-news-morning` | ~100 | Marketaux+FMP 혼합 |
| 06:00 (Mon) | `sync-etf-holdings` | ~30 | SPDR XLSX 다운로드 + FMP 보강 |
| **06:15** | `collect-sp500-news-fmp-0615` | **~500** | orchestrator → 5 chord 배치 (rate_limit=100/m × 5min) |
| 06:45 | `collect-general-news-fmp-morning` | 1 | limit=50 |
| 07:45 | `collect-press-releases-fmp` | ~50 | max_symbols=50 |
| 09:00–16:00 | `update-realtime-prices` × 96 | ~96 | 시장 시간 5분 주기, bulk |
| 09:00–16:00 | `update-market-indices` × 96 | ~96 | 5분 주기 |
| **10:15** | `collect-sp500-news-fmp-1015` | **~500** | |
| 12:30 | `collect-general-news-fmp-noon` | 1 | |
| **13:15** | `collect-sp500-news-fmp-1315` | **~500** | |
| **15:15** | `collect-sp500-news-fmp-1515` | **~500** | |
| 17:00 | `update-daily-prices` | ~1 | bulk 1콜 |
| **17:15** | `collect-sp500-news-fmp-1715` | **~500** | |
| 17:45 | `collect-general-news-fmp-evening` | 1 | |
| **18:00** | `sync-sp500-eod-prices` | **~500** | EOD batch |
| **20:00** | `sync-sp500-financials` | **~101** | 5일 1회전 (101 symbols/day) |

**일일 총합**: 약 **3,200 FMP 콜/일** (평일 기준)

#### 분당 피크 분석

`collect_sp500_news_fmp_batch`에는 `rate_limit='100/m'` 적용 → 워커 단위 분당 100 콜 한도.

**FMP 동시 시작 충돌 윈도우**:
- **18:00 ± 5min**: `sync-sp500-eod-prices` (500 콜, 분당 ~100) + `update-daily-prices` (17:00 끝물 잔여) + 18:00 정시 `update-economic-indicators`(FRED, FMP 아님) → **약 100–150 FMP/min**, 한도 내이지만 동시 작업 다수
- **18:00–18:30**: EOD 가격 sync 진행 중 18:30에 `run-eod-pipeline` 시작 → 가격 sync가 끝나기 전 EOD 파이프라인이 FMP 데이터를 읽으면 **읽기/쓰기 경합** 가능
- **17:15–17:20**: `collect-sp500-news-fmp-1715` (500 콜) + 17:00 `update-daily-prices` 잔여 + 17:45 시작 직전 → **분당 ~100–120 FMP** (한도 내)

**결론**: rate_limit=100/m 데코레이터 덕분에 Starter 300/min 한도는 일반적으로 유지된다. 단, **동일 워커에서만 100/m 적용**되므로 워커가 여러 대인 경우 한도 초과 가능.

#### CLAUDE.md 표기 vs 실제 한도 갭
CLAUDE.md는 `FMP: 10 calls/분`이라 적혀 있으나 사용자 컨텍스트는 Starter 300/min. **공식 라이트레미트 표기와 운영 한도가 어긋남** — DECISIONS.md/CLAUDE.md 갱신 필요.

---

### 3.2 Gemini Free (15 RPM, 1500 RPD)

#### Gemini 호출 태스크

| 시간(NY) | 태스크 | 호출 수 추정 | 빈도 |
|---------|--------|-------------|------|
| 05:30 | `enrich-relationship-keywords` (limit=100) | ~100 LLM | 1/일 |
| 08:00 | `keyword-generation-pipeline` (gainers) | ~50 LLM | 1/일 |
| 08:30/10:30/12:30/14:30/16:30/18:30 | `analyze-news-deep` (max_articles=50) | 각 ~50 LLM, 4초 간격 | 6/일 평일 |
| 09:00 | `extract-news-relations` (24h) | ~30 LLM | 1/일 |
| 16:30 | `extract-daily-news-keywords` | ~50 LLM | 1/일 |
| 매월 1일 03:00 | `bulk-generate-korean-overviews` (batch=50) | ~500 LLM | 월 1회 |

**일별 RPD 추정** (평일):
- enrich(100) + keyword-pipeline(50) + analyze-deep(50×6=300) + extract-news-relations(30) + extract-daily-keywords(50) ≈ **530 RPD**
- ✅ Free 1500 RPD 한도 내

**분당 RPM 안전성**:
- `analyze_news_deep`은 코드 주석상 "4초 간격으로 RPM 준수" → 60/4 = 15 RPM 정확히 한도. **여유 0**.
- 동일 분에 다른 Gemini 태스크가 겹치면 즉시 한도 초과:
  - **08:30 윈도우**: `analyze-news-deep`(15 RPM) 시작
  - **05:30 윈도우**: `enrich-relationship-keywords` 단독 → 안전
  - **16:30 윈도우**: `extract-daily-news-keywords`(50건) + `analyze-news-deep`(50건) **동시 시작** → ⚠️ **15 RPM 초과 위험**
  - **09:00 윈도우**: `extract-news-relations`(30 LLM) 단독, 16:30 윈도우와 함께 점검 필요

**🔴 16:30 윈도우 충돌 명시**: 두 태스크 모두 LLM 호출이며 동시 시작 → 한 워커 내에서는 직렬화되지만, 별도 워커일 경우 분당 최대 30+ RPM으로 한도 2배 초과.

#### 월 1일 03:00 폭주
`refresh-korean-overviews-monthly` (`bulk_generate_korean_overviews`, batch=50, force=False) — S&P 500 약 500건 한글 개요 생성. **월 1회 ~500 LLM 콜이 단일 시점에 큐에 쌓임**. 만약 4초 간격이면 33분 소요. Gemini RPD 1500 한도의 1/3 소비 → 같은 일요일에 ML 훈련(03:00)이 중첩되면 동일 일자 다른 LLM 잡과 RPD 충돌 가능.

---

### 3.3 Alpha Vantage (5 calls/min)

**결론**: ✅ **이슈 없음**. `df85496 refactor: Alpha Vantage provider 전면 제거` 커밋 이후 모든 Beat 스케줄에서 AV 의존성이 제거됨. `grep alpha_vantage` 결과 0건.

⚠️ 단, CLAUDE.md `### 외부 API Rate Limits` 섹션에는 여전히 `Alpha Vantage: 5 calls/분, 12초 대기 필수` 표기가 남아 있음 → 문서 정리 필요 (감사 범위 외, 별도 PR).

---

## 4. Queue 몰림 분석

### 4.1 default queue (시장 시간 9–16시)

매분 fires (8시간 × 60분 = 480 슬롯):
- `refresh-market-pulse-cache` × 480 (캐시 갱신만, API 콜 없음)

5분 슬롯 fires (8시간 × 12 = 96 슬롯/태스크):
- `update-realtime-prices` × 96
- `update-market-indices` × 96

10분 fires:
- `calculate-portfolio-values` × 48

15분 fires:
- `check-screener-alerts` × 32

**5분 정시(00, 05, 10, ...) 동시 fires**: cache + realtime-prices + market-indices = 3건 이상 같은 분에 같은 워커에 도달. prefork로 워커 수 ≥ 4면 안전, 그러나 macOS solo pool 환경에서는 직렬 실행 → 5분 안에 모두 끝나야 다음 정시 슬롯이 적체되지 않음.

### 4.2 neo4j queue (solo pool, 동시 1건)

#### 일일 fires 합계 (평일)

| 태스크 | 일일 fires | 비고 |
|-------|----------|------|
| `sec-sync-dirty-neo4j` | **288** | 5분마다 24h |
| `sync-news-to-neo4j` | 6 | 매 2시간 :45 |
| `chainsight-sync-profiles-neo4j` | 1 | 12:00 |
| `chainsight-sync-relations-neo4j` | 1 | 12:30 |
| `cleanup-expired-news-relationships` | 1 | 04:00 |
| `enrich-relationship-keywords` | 1 | 05:30 |
| `neo4j-health-check` | 4 | 매 6시간 |
| (Sun) `chainsight-neo4j-dirty-sync` | +1 | 04:30 일요일 |
| **합계** | **~302/일** | |

**solo pool 처리량 한계**: 24시간 = 1440분 = 1440 슬롯 가정. 평균 처리시간 1분이면 302/1440 = 21% 점유 → 단순 평균은 OK.

**그러나 피크 윈도우는 위험**:

#### 12:00–12:45 neo4j 큐 폭주 윈도우

| 시각 | 태스크 | queue |
|------|--------|-------|
| 12:00 | `neo4j-health-check` | neo4j |
| 12:00 | `sync-news-to-neo4j`(직전 10:45 잔여 가능) | neo4j |
| 12:00 | `chainsight-sync-profiles-neo4j` | neo4j |
| 12:00–12:05 | `sec-sync-dirty-neo4j` | neo4j |
| 12:30 | `chainsight-sync-relations-neo4j` | neo4j |
| 12:30 | `sec-seed-relations-to-chainsight` | default (neo4j 큐 라우팅 없음, **그러나 Neo4j DB는 사용**) |
| 12:45 | `sync-news-to-neo4j` | neo4j |

**solo pool 1개로 5–7건 직렬 처리** → 한 건이 5분 초과 시 전체 적체.

#### 18:30–18:45 default+neo4j 동시 폭주

| 시각 | 태스크 | queue | 비고 |
|------|--------|-------|------|
| 18:00 | `update-economic-indicators` | default | FRED |
| 18:00 | `collect-market-news-evening` | default | |
| 18:00 | `sync-sp500-eod-prices` | default | **FMP 500콜** |
| 18:00 | `thesis-update-readings` | default | |
| 18:00 | `neo4j-health-check` | neo4j | |
| 18:15 | `classify-news-batch` | default | |
| 18:15 | `thesis-calculate-scores` | default | thesis-update 종료 의존 |
| 18:30 | `analyze-news-deep` | default | **Gemini 50건** |
| 18:30 | `update-sp500-change-percent` | default | |
| 18:30 | `run-eod-pipeline` | default | EOD 가격 sync 종료 의존 |
| 18:30 | `thesis-create-snapshots` | default | thesis-calculate 종료 의존 |
| 18:45 | `sync-news-to-neo4j` | neo4j | |

**의존성 위반 위험**:
- `sync-sp500-eod-prices`(18:00, ~500 FMP콜, ~5분+)이 끝나기 전 `run-eod-pipeline`(18:30) 시작 → EOD 파이프라인이 **불완전한 가격 데이터를 읽음**. 30분 윈도우는 통상 충분하지만, FMP 응답 지연/재시도 시 부족.
- `thesis-update-readings` → `thesis-calculate-scores` (15분 갭) → `thesis-create-snapshots` (15분 갭) — **체이닝이 시간 기반**. 선행이 늦으면 후행이 빈 데이터로 실행.

---

## 5. 시간대별 ASCII 히트맵 (평일 NY 기준)

태스크 fires 카운트 (cache/repeating 5min 포함). `█` = 10건, `▓` = 5건, `▒` = 1건, `·` = 0건.

```
Hour │  Fires │ Bar (1█ ≈ 10 fires)                                   │ Note
─────┼────────┼─────────────────────────────────────────────────────┼──────────────────
 00  │     15 │ █▓                                                    │ sec-sync-dirty 5min×12 + check-pipeline×2 + cron
 01  │     15 │ █▓                                                    │ + update-economic-calendar (1:00)
 02  │     14 │ █▒▒▒▒                                                 │ idle
 03  │     14 │ █▒▒▒▒                                                 │ idle (Sun: +ML 훈련 클러스터)
 04  │     15 │ █▓                                                    │ + cleanup-expired-news-relationships (neo4j)
 05  │     15 │ █▓                                                    │ + enrich-relationship-keywords (neo4j, Gemini 100콜)
 06  │     20 │ ██                                                    │ ⚠ FMP cluster: news + sp500-news + general-news
 07  │     20 │ ██                                                    │ ⚠ Movers + press-releases + categories + heat-score
 08  │     19 │ █▓▒▒▒▒                                                │ keyword-pipeline + classify + analyze (Gemini)
 09  │    110 │ ███████████                                           │ 🔴 시장 개장 + cache 60 + realtime + portfolio
 10  │    113 │ ███████████▒                                          │ 🔴 + chainsight-co-mentions + analyze-news-deep
 11  │    109 │ ██████████▓                                           │ 🔴 + chainsight-relation-confidence
 12  │    118 │ ███████████▓                                          │ 🔴🔴 neo4j 큐 5중 적체 윈도우
 13  │    111 │ ███████████▒                                          │ 🔴 + seed-selection + sp500-news-1315
 14  │    113 │ ███████████▒                                          │ 🔴 + classify + analyze
 15  │    110 │ ███████████                                           │ 🔴 + sp500-news-1515
 16  │    114 │ ███████████▓                                          │ 🔴🔴 시장 마감 + breadth + heatmap + Gemini 2종 동시
 17  │     18 │ █▓▒▒▒                                                 │ ⚠ daily-prices + sp500-news-1715
 18  │     26 │ ██▓▒                                                  │ 🔴🔴 EOD + Gemini + Thesis 3 + neo4j health
 19  │     16 │ █▓▒                                                   │ + ml-labels + backfill-signal-accuracy
 20  │     15 │ █▓                                                    │ + sync-sp500-financials (FMP 101콜)
 21  │     14 │ █▒▒▒▒                                                 │ idle
 22  │     15 │ █▓                                                    │ + update-economic-indicators
 23  │     14 │ █▒▒▒▒                                                 │ idle
─────┴────────┴─────────────────────────────────────────────────────┴──────────────────
```

### API 콜 집중도 히트맵 (외부 API만, 분당 추정 피크)

```
Hour │ FMP/min(peak) │ Gemini/min(peak) │ FRED  │ Neo4j 작업
─────┼───────────────┼──────────────────┼───────┼──────────────
 00  │      0        │       0          │   -   │  sec-sync (5min)
 04  │      0        │       0          │   -   │  + cleanup-news-relations
 05  │      0        │      ~1          │   -   │  + enrich-relations (neo4j+Gemini)
 06  │     ~50       │       0          │  +1   │  -
 06:15│     ~100     │       0          │   -   │  -                    🔴 FMP 한도 33%
 07  │     ~10       │       0          │   -   │  -
 08  │      ~5       │      ~1          │   -   │  -
 08:30│      ~5      │     ~12          │   -   │  -                    🟡 Gemini 80%
 09  │     ~20       │       0          │   -   │  -
 10:15│    ~100      │       0          │   -   │  -                    🔴 FMP 한도 33%
 10:30│      ~5      │     ~12          │   -   │  -                    🟡 Gemini 80%
 12:00│     ~10      │       0          │  +1   │  health+sync×3        🔴 neo4j 5중
 13:15│    ~100      │       0          │   -   │  -                    🔴
 14:30│      ~5      │     ~12          │   -   │  -                    🟡
 15:15│    ~100      │       0          │   -   │  -                    🔴
 16:30│      ~5      │    ~24+          │   -   │  -                    🔴🔴 Gemini 한도 160%
 17:15│    ~100      │       0          │   -   │  -                    🔴
 18:00│    ~100      │       0          │  +1   │  health+(news 18:45)  🔴 EOD 폭주
 18:30│      ~5      │     ~12          │   -   │  -                    🟡
 20:00│     ~20      │       0          │   -   │  -
─────┴───────────────┴──────────────────┴───────┴──────────────
```

🔴 = 한도 30% 이상 / neo4j 큐 3건 이상 적체
🔴🔴 = 한도 위험 또는 즉각적인 racing condition
🟡 = 한도 50–80% (안전마진 부족)

---

## 6. 스케줄 겹침 / 의존성 매트릭스

### 6.1 시간 기반 체이닝 (소프트 의존성)

| 선행 | 선행 종료 SLA | 후행 | 후행 시작 | 갭 | 위험 |
|------|--------------|------|----------|-----|------|
| `sync-sp500-eod-prices` (FMP 500콜) | ~5–10분 | `run-eod-pipeline` | 18:30 | 30분 | 🟡 FMP 지연 시 갭 부족 |
| `update-economic-indicators` (FRED) | ~1분 | `update-economic-calendar` | 1:00 (다음날) | — | ✅ |
| `thesis-update-readings` | ~5–10분 | `thesis-calculate-scores` | 18:15 | 15분 | 🟡 |
| `thesis-calculate-scores` | ~5분 | `thesis-create-snapshots` | 18:30 | 15분 | 🟡 |
| `aggregate-daily-sentiment` | ~3분 | `extract-news-relations` | 9:00 동시 | 0분 | 🔴 동시 시작 |
| `classify-news-batch` (8:15) | ~10분 | `analyze-news-deep` (8:30) | 8:30 | 15분 | 🟡 |
| `analyze-news-deep` (8:30) | ~15분 | `sync-news-to-neo4j` (8:45) | 8:45 | 15분 | 🟡 |
| `train-importance-model` (Sun 3:00) | ~30–60분 | `generate-shadow-report` (Sun 3:30) | 3:30 | 30분 | 🟡 |
| `check-auto-deploy` (Sun 4:00) | ~5분 | `generate-weekly-ml-report` (4:15) | 4:15 | 15분 | ✅ |
| `monitor-ml-performance` (Sun 4:20) | ~3분 | `train-lightgbm-model` (4:30) | 4:30 | 10분 | ✅ |
| `chainsight-co-mentions` (10:00) | ~10분 | `chainsight-relation-confidence` (11:00) | 11:00 | 60분 | ✅ |
| `chainsight-all-profiles` (Sat 2:00) | ~30–60분 | `chainsight-price-co-movement` (Sat 3:00) | 3:00 | 60분 | ✅ |
| `chainsight-stale-decay` (Sat 4:00) | ~5분 | `chainsight-aggregate-profiles` (4:30) | 4:30 | 30분 | ✅ |
| `chainsight-sync-profiles-neo4j` (12:00) | ~5분 | `chainsight-sync-relations-neo4j` (12:30) | 12:30 | 30분 | ✅ |

### 6.2 동시 시작 (zero-gap)

| 시각 | 태스크 | 충돌 |
|------|--------|------|
| **9:00** | `aggregate-daily-sentiment`, `extract-news-relations` | 둘 다 News 테이블 read-heavy + LLM |
| **6:00** | `collect-daily-news-morning`, `update-economic-indicators`, `neo4j-health-check`, (Mon) `sync-etf-holdings` | FMP+FRED 동시 폭주 |
| **8:00** | `keyword-generation-pipeline`(Gemini), `collect-market-news-morning`(news) | Gemini+API 병렬 |
| **12:00** | `neo4j-health-check`, `update-economic-indicators`, `collect-market-news-noon`, `chainsight-sync-profiles-neo4j`, `sec-seed-relations-to-chainsight` | **neo4j 4건 + default 1건** |
| **16:30** | `extract-daily-news-keywords`(Gemini), `analyze-news-deep`(Gemini), `calculate-market-breadth` | **🔴 Gemini RPM 한도 초과 위험** |
| **17:00** | `update-daily-prices`(FMP), `collect-category-news-high-evening`(news API) | |
| **18:00** | 7건 동시 (위 4.2 참조) | **🔴 가장 위험한 윈도우** |
| **Mon 4:00** | `cleanup-expired-news-relationships`(neo4j), `scan-regulatory-relationships` | |
| **Sun 4:00** | `cleanup-expired-news-relationships`(neo4j), `check-auto-deploy` | |
| **Month-1 4:00** | `cleanup-expired-news-relationships`(neo4j), (M16: `sync-institutional-holdings`) | |

### 6.3 데이터 경합 가능성

- **DailyPrice**: `sync-sp500-eod-prices`(18:00 write) ↔ `run-eod-pipeline`(18:30 read) ↔ `backfill-signal-accuracy`(19:00 read) — 시간 갭이 EOD sync 지연 시 부족.
- **News.Article**: `collect-*-news-*`(write) ↔ `classify-news-batch`(read+update) ↔ `analyze-news-deep`(read+update) — `:00 collect → :15 classify → :30 analyze → :45 sync-neo4j` 패턴은 잘 분리됨 ✅
- **ChainProfile**: `chainsight-all-profiles`(Sat 2:00 write) ↔ `chainsight-aggregate-profiles`(Sat 4:30 read) — 갭 충분 ✅
- **Stock.change_percent**: `sync-sp500-eod-prices` → `update-sp500-change-percent`(18:30) — 30분 갭, FMP 지연 시 갭 부족 🟡

---

## 7. 시간대(Timezone) 드리프트 위험

### 7.1 주석 vs 실제 실행 시간 불일치

`CELERY_TIMEZONE = 'America/New_York'`이므로 모든 `crontab(hour=H)`은 NY 시간에서 실행. 그러나 일부 주석이 "UTC"라고 잘못 표기되어 있음:

| 태스크 | 코드 주석 | 실제 실행 (NY) | 차이 |
|--------|----------|----------------|------|
| `chainsight-heat-score-daily` | `매일 07:00 UTC` | NY 07:00 | UTC 환산 시 NY EDT(여름) → 11:00 UTC, EST(겨울) → 12:00 UTC. **주석과 4–5시간 어긋남** |
| `chainsight-seed-selection` | `매일 13:00 UTC` | NY 13:00 | EDT 17:00 UTC, EST 18:00 UTC |
| `chainsight-neo4j-dirty-sync` | `매주 일요일 04:30 UTC` | Sun NY 04:30 | EDT 08:30 UTC, EST 09:30 UTC |

**위험**: 운영자가 주석 기준으로 모니터링 알람을 세팅하면 정확히 4–5시간 어긋남. 또한 시드 선정(13:00) → 관계 갱신(11:00 NY) 의존성이 운영자 기대와 다를 수 있음.

### 7.2 EST/EDT 전환 (DST) 영향

`America/New_York` 타임존은 DST 자동 전환:
- 봄(3월 둘째 일요일): EST → EDT (1시간 앞당김)
- 가을(11월 첫째 일요일): EDT → EST (1시간 늦춤)

**시장 시간 9–16시는 NY 로컬이므로 자동으로 시장에 맞춰 이동** ✅. 그러나:
- DST 전환 일요일 새벽 02:30–04:30 윈도우의 ML 훈련 클러스터는 **봄에는 03:00이 건너뛰고**, **가을에는 03:00이 두 번 실행**되는 표준 cron 행동 발생 → `train-importance-model`(Sun 3:00) 등 일년 2회 비정상 실행 가능.

---

## 8. 핵심 권장사항 (우선순위)

### 🔴 즉시 (P0)

1. **NY 16:30 Gemini 충돌 해소**
   - `extract-daily-news-keywords` → 16:35 또는 17:30으로 이동 (`analyze-news-deep` 16:30과 분리)
   - 또는 둘 중 하나에 별도 큐 + 별도 워커 부여

2. **NY 18:00 EOD 폭주 디커플링**
   - `sync-sp500-eod-prices` 종료 시그널을 chord로 chain → `run-eod-pipeline`/`update-sp500-change-percent`/`thesis-update-readings`가 시간 기반 cron이 아닌 chord 후속으로 실행되도록 변경
   - 현재 30분 갭은 FMP 지연 시 부족

3. **`sec-sync-dirty-neo4j` 5분 주기 검증**
   - 1건 평균 처리 시간을 측정해 5분 < 처리시간이면 즉시 적체
   - 권장: 처리 시간 모니터링 메트릭 추가, 적체 시 alert

### 🟡 단기 (P1)

4. **"UTC" 주석 정정**
   - chainsight-heat-score / seed-selection / neo4j-dirty-sync 주석을 "NY"로 수정 또는 명시적으로 UTC 변환값 표기
   - DECISIONS.md에 타임존 표기 규약 추가 ("crontab은 항상 NY")

5. **NY 12:00 neo4j 5중 적체 분산**
   - `chainsight-sync-profiles-neo4j` → 11:30
   - `chainsight-sync-relations-neo4j` → 12:45
   - `sec-seed-relations-to-chainsight` → 12:15 (default 큐이지만 Neo4j DB 사용)

6. **FMP S&P 500 뉴스 5회 → 3회로 감축**
   - 06:15, 13:15, 17:15만 유지 → 일일 1500 콜 (50% 감축)
   - 운영 데이터 검증으로 ROI 확인

### 🟢 중장기 (P2)

7. **DatabaseScheduler ↔ config dict 동기화 자동화**
   - `manage.py audit_beat_schedule` 명령으로 dict ↔ DB diff 출력
   - CI/pre-commit에 통합

8. **CLAUDE.md rate limit 표기 갱신**
   - Alpha Vantage 항목 제거 또는 "사용 안 함" 표기
   - FMP "10 calls/분" → "Starter 300 calls/min" 정정

9. **DST 전환 일요일 ML 훈련 보호**
   - `train-importance-model`을 03:00 → 04:00 이동 (DST 비충돌 안전 윈도우)
   - 또는 `last_run_at` 체크로 idempotent 보호

---

## 9. 부록 — 검증 방법

본 감사는 코드 정적 분석 기반이므로 실제 운영 데이터로 교차 검증 권장:

```sql
-- 실제 DB 등록된 PeriodicTask와 config dict diff
SELECT name FROM django_celery_beat_periodictask WHERE enabled = TRUE;
```

```bash
# 실제 실행 빈도 (TaskResult 기반, 최근 7일)
python manage.py shell -c "
from django_celery_results.models import TaskResult
from django.db.models import Count
from datetime import datetime, timedelta
qs = TaskResult.objects.filter(
    date_done__gte=datetime.now() - timedelta(days=7)
).values('task_name').annotate(c=Count('id')).order_by('-c')
for row in qs[:30]: print(row)
"

# Neo4j 큐 적체 확인 (Redis)
redis-cli LLEN celery:neo4j
```

---

**감사 종료**: 2026-04-26
**다음 감사 권장 시점**: NY 18:00 EOD 폭주 또는 16:30 Gemini 충돌 해소 후 / Beat schedule 추가 변경 시
