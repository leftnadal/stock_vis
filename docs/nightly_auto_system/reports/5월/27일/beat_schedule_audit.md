# Beat Schedule Audit — config/celery.py

**감사 일자**: 2026-05-27
**대상 파일**: `config/celery.py` (820 라인, `app.conf.beat_schedule` 86개 엔트리)
**모드**: 읽기 전용 — 코드 변경 없음

> ⚠️ **드리프트 주의**: `config/settings.py`의 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 때문에 실제 실행 스케줄은 DB `django_celery_beat_periodictask` 테이블이다.
> 본 감사는 코드상 dict를 기준으로 한 "설계 의도" 분석이며, 실제 실행 시 DB 등록 여부와 별개로 잠재 위험을 식별한다. (Bug #28 참조)

---

## 1. 요약

| 지표 | 값 |
|------|----|
| 총 beat 엔트리 | 86개 |
| 기본 queue 엔트리 | 78개 |
| neo4j queue 엔트리 | 10개 (sec-sync-dirty-neo4j 포함) |
| 시장시간(09–16 EST) 분당 트리거 | ~110건/시 |
| 가장 바쁜 시각 | **18:00–18:45 EST** (EOD + Thesis + News 다중 스택) |
| 가장 한가한 시각 | 21:00, 23:00 EST (sec-sync 외 0건) |
| 외부 API 충돌 위험 P0 | **2건** (FMP 18:00 / Gemini 09:00) |
| Queue 몰림 위험 P0 | **1건** (Neo4j 12:00 동시 4건) |

---

## 2. 시간대별 ASCII 히트맵 (평일 EST 기준)

### 2.1 전체 트리거 수 (분당 작업 포함)

```
시각  카운트  히트맵 (1칸 = 약 5건)
00:00   14    █████ (sec-sync ×12 + pipeline-alert ×2)
01:00   15    █████ (+ update-economic-calendar)
02:00   14    █████
03:00   14    █████
04:00   15    █████ (+ cleanup-expired-news-relationships)
05:00   15    █████ (+ enrich-relationship-keywords 05:30)
06:00   19    ███████ (+ news/FRED/FMP cluster)
07:00   20    ███████ (+ market-movers + category-news + press-rel)
08:00   19    ███████ (+ keyword-pipeline + market-news + classify/analyze)
09:00  110    ████████████████████████████████████████████ ★ PEAK
10:00   99    ████████████████████████████████████████
11:00   95    ███████████████████████████████████████
12:00  104    █████████████████████████████████████████ ★ Neo4j 4건 동시
13:00   97    ███████████████████████████████████████
14:00   99    ████████████████████████████████████████
15:00   96    ███████████████████████████████████████
16:00  100    ████████████████████████████████████████ ★ EOD 진입
17:00   18    ██████ (분당 작업 종료 후 sp500-news/일일가)
18:00   27    █████████ ★★ EOD+Thesis+News 폭주
19:00   16    ██████ (+ backfill + ml-labels)
20:00   15    █████ (+ sync-sp500-financials)
21:00   14    █████
22:00   15    █████ (+ update-economic-indicators 22:00)
23:00   14    █████
```

> 09:00–16:55 시간대의 트리거 폭증은 대부분 **무 API 작업**(market-pulse-cache 60/h, portfolio-values 6/h)에서 옴. 아래 2.2의 "외부 API 호출"만 따로 보면 실제 부하는 다르다.

### 2.2 외부 API 호출 트리거만 (FMP + Gemini + FRED + News, 분당 작업 제외)

```
시각  카운트  API     비고
00:00   0     -       sec-sync(neo4j only)
01:00   1     FRED    update-economic-calendar
02:00   0     -
03:00   0     -       (월간 작업만 일부 ‒ refresh-korean-overviews, supply-chain 등)
04:00   1     -       cleanup-expired-news-relationships (Neo4j)
05:00   1     GEM     enrich-relationship-keywords
06:00   5     FMP×3   ★ 06:00/06:15/06:30/06:45 FMP 4건 클러스터
07:00   6     FMP×3   movers + category × 2 + press-releases
08:00   5     GEM+FMP keyword-pipeline + classify-batch + analyze-deep
09:00   2     GEM×2   ★ aggregate-sentiment + extract-news-relations
10:00   5     FMP+GEM sp500-news-1015 + classify + analyze + sync-news-neo4j
11:00   1     -       chainsight-relation-confidence (DB)
12:00   10    Mix     ★★ 10건 동시 (Neo4j 4 + FMP + FRED + GEM)
13:00   3     FMP     chainsight-seed + cat-news-high + sp500-news-1315
14:00   5     GEM     daily-news + classify + analyze + sync-neo4j + cat-news-med
15:00   2     FMP+News market-news-afternoon + sp500-news-1515
16:00   6     GEM+FMP classify + breadth + analyze + heatmap + keywords + sync-neo4j
17:00   4     FMP×4   daily-prices + cat-news-high + sp500-news-1715 + general-news
18:00   13    Mix     ★★★ EOD 폭주: thesis(4) + EOD(2) + news(4) + FRED + neo4j(2)
19:00   2     -       backfill + ml-labels
20:00   1     FMP     ★ sync-sp500-financials (101 종목 × 3 endpoint ≈ 303 calls)
21:00   0     -
22:00   1     FRED    update-economic-indicators
23:00   0     -
```

---

## 3. Rate Limit 초과 구간 분석

### 3.1 FMP (Starter Plan: 300 calls/min, 10,000 calls/일) — **P0 위험**

#### ⚠️ P0-1: 18:00 EST — sync-sp500-eod-prices + thesis-update-readings 동시 실행

- **18:00**: `sync-sp500-eod-prices` → S&P 500 EOD 가격 동기화 = **500+ FMP calls** (단일 분에 폭주 가능)
- **18:00**: `thesis-update-readings` → 지표 readings 갱신, FMP key-metrics/quote 다수 호출 추정
- **18:00**: `collect-market-news-evening` → FMP `/news` 추가
- **분당 300건 한도 초과 가능성 매우 높음**

#### ⚠️ P0-2: 06:00–06:45 EST — 4단 FMP 클러스터

| 시각 | 태스크 | 추정 호출수 |
|------|--------|-----------|
| 06:00 | collect-daily-news-morning | ~50 calls (Marketaux일 가능) |
| 06:15 | **collect-sp500-news-fmp-0615** | **~500 calls (S&P 500 전체 순회)** |
| 06:30 | collect-category-news-high-morning | ~30 calls |
| 06:45 | collect-general-news-fmp-morning | ~10 calls |

6:15 단일 작업이 500 심볼을 분당 300 한도 안에 끝내려면 내부 throttle 필수. 만약 단순 for-loop라면 **1분 내 300+ 호출 보장**.

#### ⚠️ P1: 17:00 / 17:15 / 17:45 EST 연속 FMP 호출

- 17:00 `update-daily-prices` (FMP) + `collect-category-news-high-evening`
- 17:15 `collect-sp500-news-fmp-1715` (500 심볼)
- 17:45 `collect-general-news-fmp-evening`
- 분 단위로 분산되어 있어 P0보다 안전하나, 17:15가 1분 내 끝나지 않으면 17:45와 겹침

#### ⚠️ P1: 20:00 EST — sync-sp500-financials

- 평일 20:00, 101 심볼 × 3 endpoint(income/balance/cashflow) ≈ **303 calls**
- 분당 300 한도와 거의 동일 → 내부 sleep 없으면 즉시 throttle

#### FMP 일일 한도 (10,000 calls/day) 추산

| 카테고리 | 일일 추정 호출수 |
|---------|--------------|
| update-realtime-prices (`*/5`, 9–16h) | 96 × 1 batch = 96 |
| update-market-indices (`*/5`, 9–16h) | 96 × ~10 indices = 960 |
| collect-sp500-news-fmp × 5회 | 5 × 500 = 2,500 |
| sync-sp500-eod-prices | 500 |
| sync-sp500-financials | 303 |
| FMP general-news × 3회 | ~30 |
| sync-daily-market-movers | ~50 |
| thesis-update-readings | ~500 (지표별 다중 호출) |
| collect-press-releases-fmp (max 50) | 50 |
| collect-daily-news × 2회 | ~100 |
| **합계 (평일)** | **~5,100 / 10,000** |

평일 일일 한도는 51% 사용 — 여유 있음. 단 **분당 300 spike**가 18:00, 06:15에 집중.

---

### 3.2 Gemini Free (15 RPM, 1500 RPD) — **P0 위험**

#### ⚠️ P0-3: 09:00 EST — aggregate-daily-sentiment + extract-news-relations 동시

- 둘 다 LLM 호출. 09:00 정각 동시 트리거.
- 각 작업이 분당 8건 이상 호출하면 합산 16 RPM ≥ 15 한도

#### ⚠️ 기존 인지되어 처리된 case

- **16:30 / 16:45 분리** (코드 주석 287–289 라인): `analyze-news-deep-batch (16:30)`과 `extract-daily-news-keywords`가 동시 호출되던 것을 15분 간격으로 분산. ✅ 처리됨.

#### ⚠️ P1: 18:30–18:35 EST — analyze-news-deep + thesis-generate-summaries

- 18:30 `analyze-news-deep-batch` (max_articles=50, 50 Gemini calls)
- 18:35 `thesis-generate-summaries` (LLM)
- 5분 간격이지만 18:30 작업이 5분 안에 끝나지 않으면 충돌 (50건 × 4초 = 200초 = 3분 20초, 가까스로 안전)

#### ⚠️ P1: 12:00 EST — chainsight-co-mentions(10:00) 직후 + sec-seed + classify(12:15)

- 10:00 `chainsight-co-mentions` (LLM 가능)
- 12:00 `sec-seed-relations-to-chainsight` (LLM 추정)
- 분리되어 있어 RPM 충돌은 없음

#### Gemini 일일 한도 (1500 RPD)

| 태스크 | 추정 호출수 |
|--------|-----------|
| classify-news-batch × 6회 | 6 × 30 = 180 |
| analyze-news-deep-batch × 6회 (max 50) | 6 × 50 = 300 |
| keyword-generation-pipeline (gainers) | ~50 |
| aggregate-daily-sentiment | ~30 |
| extract-daily-news-keywords | ~30 |
| extract-news-relations | ~30 |
| chainsight-co-mentions | ~50 |
| enrich-relationship-keywords (limit 100) | 100 |
| thesis-generate-summaries | ~30 |
| sec-seed-relations | ~30 |
| **합계** | **~830 / 1500** |

55% 사용. 안전 — 단 일요일 ML 학습 트리거 시 추가 호출이 있다면 재계산 필요.

---

### 3.3 Alpha Vantage (5 calls/min) — **안전**

- `app.conf.beat_schedule` 내에서 Alpha Vantage를 명시적으로 사용하는 태스크는 **0건**. ✅
- 모든 가격/뉴스 동기화가 FMP로 이전되어 분당 5건 한도 위험 없음.
- 단, `API_request/` 내부에서 fallback으로 AV를 쓰는지 별도 확인 권장 (이 감사 범위 밖).

---

## 4. Queue 몰림 분석

### 4.1 Neo4j Queue (solo pool, 동시성 = 1)

`sec-sync-dirty-neo4j`가 `*/5min`로 24시간 = **288 runs/day**. expires=240s로 5분 안에 시작 못 하면 자동 폐기.

#### ⚠️ P0-4: 12:00 EST — Neo4j queue 4건 동시 트리거

| 12:00 동시 발생 | 추정 소요시간 |
|---------------|-----------|
| sec-sync-dirty-neo4j (정시) | ~30s |
| chainsight-sync-profiles-neo4j | **수 분** (S&P 500 프로파일) |
| sec-seed-relations-to-chainsight | ~1분 |
| neo4j-health-check (`*/6h` 정시) | ~5s |

→ **solo pool 직렬 처리** → chainsight-sync-profiles가 5분 초과하면 12:05 sec-sync-dirty도 큐에 쌓이고 expires=240s 초과로 폐기됨.

#### ⚠️ P1: 12:30 EST — chainsight-sync-relations-neo4j

- 12:00 profiles 동기화가 끝나야 12:30 relations가 시작될 수 있음 (의도된 순서지만 30분 안에 끝나야 함)
- profiles가 30분 넘으면 relations도 밀려서 카스케이드 지연

#### ⚠️ P1: 18:45 EST — sync-news-to-neo4j

- 18:00 EOD + 18:30 thesis-create-snapshots(dirty 기록) 직후
- sec-sync-dirty 정시(18:45)와 동시 → 직렬
- 이 시간대 sec-sync-dirty 적체 가능성 ↑

#### ⚠️ P2: 일요일 04:30 UTC — chainsight-neo4j-dirty-sync

- 일요일 새벽 ML 학습 카스케이드(03:00–05:00)와 별도 timezone(UTC vs EST)
- 04:30 UTC = 23:30 EST (전날) → 다른 시간대, 충돌 없음

#### 신호: sec-sync-dirty-neo4j expires=240s vs schedule=300s

- 다음 실행 60초 전에 만료 → 안전 마진 좁음
- 다른 무거운 neo4j 태스크가 4분 초과 시 적체

### 4.2 Default Queue

- 평일 시장시간 (09–16) 분당 1건 (`refresh-market-pulse-cache`) → 60/h, 1초 미만 처리로 부담 없음
- 가장 큰 peak는 **18:00 EST 4건 동시** (sync-sp500-eod-prices, thesis-update-readings, update-economic-indicators, collect-market-news-evening) — prefork(Linux) 환경에서는 병렬 처리되나, macOS solo pool에서는 직렬

---

## 5. 스케줄 겹침 / 의존성 분석

### 5.1 명시적 의존성 체인

| 체인 | 간격 | 위험 |
|------|------|------|
| 18:00 thesis-update-readings → 18:15 calculate-scores → 18:30 create-snapshots → 18:35 generate-summaries | 15분 / 5분 | 18:00 readings가 15분 초과 시 calculate-scores가 미완료 데이터 사용 |
| 18:00 sync-sp500-eod-prices → 18:30 run-eod-pipeline → 19:00 backfill-signal-accuracy | 30분 / 30분 | 18:00 EOD 500 심볼이 30분 내 못 끝나면 run-eod-pipeline 데이터 부족 |
| 12:00 sync-profiles-neo4j → 12:30 sync-relations-neo4j | 30분 | Neo4j solo + 큰 배치 → 마진 좁음 |
| Sun 03:00 train-importance → 03:30 shadow-report → 04:00 check-auto-deploy → 04:15 weekly-ml → 04:20 monitor-ml → 04:30 train-lightgbm | 30분 / 15분 | 30분 학습이 끝나야 다음 단계 — train-importance가 길어지면 카스케이드 |
| Sat 02:00 chainsight-all-profiles → 03:00 price-co-movement → 04:00 stale-decay → 04:30 aggregate-profiles → 05:00 validation-weekly-batch | 1시간씩 | 안전 마진 OK |

### 5.2 의도되지 않은 동시 실행 (데이터 경합 위험)

| 시각 | 동시 발생 | 경합 대상 |
|------|---------|----------|
| 09:00 | aggregate-daily-sentiment + extract-news-relations | NewsArticle 테이블 read-only, 안전 |
| 10:15 | classify-news-batch + collect-sp500-news-fmp-1015 | NewsArticle 테이블 write 경합 가능 |
| 12:00 | 5건 동시 (위 4.1 참조) | Stock/CompanyProfile 동시 update 가능 |
| 18:00 | sync-sp500-eod-prices + thesis-update-readings | DailyPrice 테이블 — eod-prices는 write, thesis는 read. 18:00 thesis-readings가 미완료 EOD 가격을 읽을 위험 |
| 18:30 | run-eod-pipeline + thesis-create-snapshots + analyze-news-deep-batch + update-sp500-change-percent | EodSignal/ThesisSnapshot/Stock 동시 write |

### 5.3 선행 미완료 위험 (P0)

- **18:00 sync-sp500-eod-prices 미완료 시 18:30 run-eod-pipeline**: EOD pipeline은 당일 DailyPrice를 기반으로 14개 시그널 계산. 500 심볼 30분 한도가 깨지면 부분 데이터로 시그널 생성 → 오신호 위험.
- **18:00 thesis-update-readings 미완료 시 18:15 calculate-scores**: readings 미반영 상태로 score 계산 → 어제 데이터로 today 스코어 산출.

---

## 6. 우선순위별 위험 요약

### P0 (즉시 조치 권고)

1. **18:00 EST FMP 분당 한도 초과**: sync-sp500-eod-prices(500) + thesis-update-readings + collect-market-news-evening 동시 실행 → 분당 300 calls 초과 가능
2. **06:15 EST collect-sp500-news-fmp**: S&P 500 순회가 1분 내 끝나면 보장 초과. 내부 throttle 확인 필요
3. **09:00 EST Gemini 15 RPM 위험**: aggregate-daily-sentiment + extract-news-relations 동시 트리거
4. **12:00 EST Neo4j queue 4건 동시**: solo pool 직렬 처리 → sec-sync-dirty 240s expires 폐기 위험

### P1 (단기 모니터링 권고)

5. **18:00 thesis-readings ↔ sync-sp500-eod-prices 데이터 경합**: thesis가 미완료 EOD 가격을 읽을 위험
6. **18:30 run-eod-pipeline 30분 마감**: sync-sp500-eod-prices 500 호출이 30분 초과 시 부분 데이터 시그널
7. **20:00 sync-sp500-financials 303 calls**: 분당 300 한도와 동일, 내부 sleep 12초 패턴 준수 여부 검증
8. **12:00→12:30 chainsight neo4j 카스케이드**: profiles → relations 30분 마감

### P2 (장기 관찰)

9. **sec-sync-dirty expires=240s vs period=300s** 안전 마진 60초만 남음
10. **Saturday 02:00–05:00 chainsight 카스케이드**: 1시간 간격이지만 chainsight-all-profiles가 1시간 초과 시 후속 작업 카스케이드 지연
11. **dict drift**: 코드에 정의된 86개 엔트리가 DB와 동기 상태인지 정기 점검 (Bug #28)

---

## 7. 추가 발견 사항

### 7.1 timezone 혼재

- 대부분 EST 기준으로 주석에 명시 (예: "07:30 EST")
- 그러나 `chainsight-heat-score-daily` 주석에는 "07:00 UTC", `chainsight-neo4j-dirty-sync`는 "04:30 UTC"
- Celery Beat의 `CELERY_TIMEZONE` 설정에 따라 실제 실행 시각이 결정되므로 settings 확인 필요 (이 감사 범위 밖)

### 7.2 expires 미지정 태스크

- `update-realtime-prices`, `update-market-indices`, `refresh-market-pulse-cache`, `calculate-portfolio-values`, `update-economic-indicators`, `update-economic-calendar`, `cleanup-old-macro-data`, `celery-error-digest`, `cleanup-task-results` 등 9개 태스크에 `options.expires` 없음
- broker 적체 시 무한 대기 가능 — 짧은 주기 태스크에 특히 위험

### 7.3 무 API + 짧은 주기 = 부담 낮음 작업 식별

- `refresh-market-pulse-cache` (1분 주기) — 캐시 전용
- `calculate-portfolio-values` (10분 주기) — DB 전용
- `check-pipeline-alerts` (30분 주기) — 내부 트리거 감지
- 위 작업은 외부 API에 영향 없음, queue 부담만 점검

### 7.4 월간 작업 충돌 가능 시점

- 매월 1일: `archive-old-articles(02:30)` + `sync-sp500-constituents(02:00)` + `refresh-korean-overviews-monthly(03:00)` + `build-patent-network(04:30)` + `sec-check-new-filings(06:00)` — 5건 카스케이드, 정상
- 매월 15일: `sync-supply-chain-batch(03:00)` — 단독
- 매월 16일: `sync-institutional-holdings(04:00)` — 단독

---

## 8. 권고 사항 (변경 금지 — 참고만)

본 감사는 **코드 변경 절대 금지** 원칙에 따라 권고만 기록한다. 후속 조치는 별도 PR/지시서로 분리.

1. **18:00 EST 분산**: sync-sp500-eod-prices를 18:00 → 17:50으로, thesis-update-readings를 18:05로 분리 검토
2. **06:15 sp500-news-fmp 내부 throttle**: 500 심볼을 5초당 25건씩 chunk 처리 (FMP 한도 안전)
3. **09:00 Gemini 분산**: extract-news-relations를 09:30으로 이동
4. **12:00 Neo4j 분산**: sec-seed-relations-to-chainsight를 12:05로, neo4j-health-check를 `minute=0, hour='*/6'` → `minute=5, hour='*/6'`로 시프트
5. **sec-sync-dirty expires 확대**: 240s → 270s (period 300s 대비 10% 마진)
6. **dict ↔ DB 자동 동기화 스크립트**: `python manage.py audit_beat_drift` 같은 management command 추가 (수동 점검 자동화)
7. **expires 미지정 9건에 일괄 기본값 부여**: 짧은 주기는 period 미만으로

---

## 9. 검증 체크리스트 (감사 결과 신뢰도)

- [x] config/celery.py 820라인 전체 읽음
- [x] beat_schedule dict 내 86개 엔트리 추출 완료
- [x] task_routes 12건 + queue=neo4j 명시 옵션 분리 완료
- [x] crontab 표현 시간대별 매핑 완료 (M-F vs daily vs Sat/Sun)
- [x] 외부 API 분류 (FMP/Gemini/FRED/Neo4j-only) 추정 완료
- [ ] **미확인**: 실제 `django_celery_beat.PeriodicTask` DB와의 drift 점검 (DB 접근 권한 필요)
- [ ] **미확인**: 각 태스크 내부 throttle/sleep 로직 (`apps/*/tasks.py` 별도 감사 필요)
- [ ] **미확인**: settings.py의 `CELERY_TIMEZONE` 값

---

**작성자**: Claude (읽기 전용 감사)
**다음 단계**: 본 보고서는 진단만 제공. 코드 변경은 별도 작업 단위로 분리.
