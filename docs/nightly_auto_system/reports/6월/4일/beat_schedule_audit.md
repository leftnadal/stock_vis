# Beat 스케줄 감사 보고서

- **대상 파일**: `config/celery.py` — `app.conf.beat_schedule`
- **감사 일자**: 2026-06-04
- **감사 유형**: 읽기 전용 (코드 수정 없음)
- **스케줄 항목 수**: 72개 beat 엔트리
- **타임존**: `CELERY_TIMEZONE = 'America/New_York'` (NYSE, ET) — `config/settings.py:489`
  - 시스템 `TIME_ZONE = 'Asia/Seoul'` 이지만 Celery는 ET로 crontab 해석
  - **모든 crontab hour 값은 ET 기준으로 평가됨** (DST 자동 적용)

---

## ⚠️ 0. 감사 전 필수 전제 (Critical Caveat)

이 보고서는 `config/celery.py`의 **선언적 reference dict**를 분석한 것이다. 그러나:

```python
# config/celery.py:124-140
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
# → Beat는 DB의 django_celery_beat.PeriodicTask 테이블을 진실의 소스로 사용
# → 아래 dict는 "원래 설계된 스케줄의 reference"로만 존재 (런타임에 무시됨)
```

**즉 실제로 실행되는 스케줄은 DB `PeriodicTask` 테이블이며, 이 dict와 drift 가능성이 있다** (common-bug #28).
본 감사 결과를 운영에 반영하기 전, 아래 검증을 **반드시** 수행할 것:

```bash
python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import config.celery as c
db_names = set(PeriodicTask.objects.values_list('name', flat=True))
dict_names = set(c.app.conf.beat_schedule.keys())
print('DB에만 존재:', db_names - dict_names)
print('dict에만 존재:', dict_names - db_names)
"
```

→ 이 감사는 "설계 의도(dict)" 기준이다. **DB가 dict와 일치한다는 가정 하에서만 유효**하다.

---

## 1. Rate Limit 초과 구간 분석

### 1-1. 핵심 구조적 결함: Gemini 전역 분산 limiter 부재 🔴 P0

각 LLM 태스크는 **프로세스 로컬 `time.sleep(4)`**로만 15 RPM을 준수한다:

| 서비스 | 위치 | 방식 |
|--------|------|------|
| `news_deep_analyzer.py` | `RPM_DELAY = 4` (L40), `time.sleep(self.RPM_DELAY)` (L99) | 프로세스 로컬 |
| `relationship_keyword_enricher.py` | `CALL_DELAY` (L53), `time.sleep(self.CALL_DELAY)` (L157) | 프로세스 로컬 |

```
grep 결과: 전역 공유 Gemini rate limiter (Redis 기반) → 0건
```

**문제**: 두 개 이상의 Gemini 태스크가 **서로 다른 워커/프로세스에서 동시 실행**되면,
각자 독립적으로 4초 간격을 지키므로 **합산 RPM이 N배로 증가**한다.
2개 동시 = 30 RPM → **Gemini Free 15 RPM의 2배 초과**.

- **dev 환경(macOS)**: `worker_pool = 'solo'` (concurrency 1)로 강제 → 단일 워커 내 직렬 실행 → **현재는 우연히 안전**
- **prod 환경(Linux prefork)**: 멀티 워커 → 구조적으로 노출됨
- **추가 위험**: `enrich_relationship_keywords`는 **neo4j 큐(별도 워커)**에서 Gemini 호출 → default 큐의 Gemini 태스크와 **물리적으로 다른 프로세스** → 시간만 겹치면 즉시 30 RPM

> 현재 스케줄은 P0 #8 수정(2026-04-26)으로 `extract-daily-news-keywords`를 16:45로,
> `analyze-news-deep`를 16:30으로 15분 분리해 **시간 충돌만 회피**한 상태다.
> 근본 원인(전역 limiter 부재)은 미해결 → **스케줄 1줄만 바꿔도 RPM 2배가 조용히 재발**한다.

### 1-2. Gemini 태스크 인벤토리 (시간대 ET)

| 태스크 | 시각(ET) | 큐 | 1회 최대 호출 | 비고 |
|--------|---------|-----|--------------|------|
| `enrich-relationship-keywords` | 05:30 매일 | **neo4j** | ~100 (limit) | 100×4s ≈ **6.6분 점유** |
| `keyword-generation-pipeline` | 08:00 매일 | default | gainers ~20종목 | |
| `analyze-news-deep-batch` | 08/10/12/14/16/18 :30 평일 | default | 50 (max_articles) | 50×4s ≈ 3.3분 |
| `extract-news-relations` | 09:00 매일 | default | LLM relation extractor | |
| `chainsight-co-mentions` | 10:00 매일 | default | days_back=7 | |
| `extract-daily-news-keywords` | 16:45 매일 | default | 배치 | analyze-deep와 15분 간격 |
| `thesis-generate-summaries` | 18:35 평일 | default | thesis 수만큼 | |
| `refresh-korean-overviews-monthly` | 매월 1일 03:00 | default | S&P500 전체 | 월 1회 |

> ✅ `classify-news-batch`는 **LLM 미사용** (rule-based `NewsClassifier`) — Gemini 부하 아님 (오해 주의)

**동시 실행 충돌 매트릭스 (시간 겹침 기준)**:

| 시각 | 동시 Gemini 태스크 | 큐 분리? | 위험 |
|------|-------------------|---------|------|
| 16:30 / 16:45 | analyze-deep / extract-daily-kw | 같은 default, **15분 간격** | ✅ 회피됨 (P0 #8) |
| 08:00 / 08:30 | keyword-pipeline / analyze-deep | 같은 default, **30분 간격** | ✅ 직렬 안전 |
| 09:00 / 10:00 | extract-news-rel / co-mentions | 60분 간격 | ✅ 안전 |
| 05:30 | enrich (neo4j 워커) 단독 | — | ⚠️ 단독이라 현재 OK, but 6.6분 점유 |

→ **현재 시간표상 동시 실행 겹침은 없음.** 단, §1-1 구조적 결함으로 **방어선이 "시간 분리" 하나뿐**.

### 1-3. Gemini RPD (1500/일) 추정

| 태스크 | 일 실행 | 1회 호출 | 일 합계(상한) |
|--------|--------|---------|--------------|
| analyze-news-deep | 6회 | 50 | 300 |
| enrich-relationship-keywords | 1회 | 100 | 100 |
| keyword-generation-pipeline | 1회 | ~40 | ~40 |
| extract-daily-news-keywords | 1회 | ~배치 | ~50 |
| extract-news-relations | 1회 | ~30 | ~30 |
| chainsight-co-mentions | 1회 | ~30 | ~30 |
| thesis-generate-summaries | 1회 | thesis N | 가변 |
| **추정 합계** | | | **~600 + thesis** |

→ **1500 RPD 대비 ~40% 사용**, 헤드룸 충분. 단 thesis 수 증가 + 월1회 korean-overviews(S&P500 전체) 날 주의.

### 1-4. FMP Rate Limit (300/분, 10,000/일) 분석

#### 🔴 P0 — `collect_sp500_news_fmp_orchestrator` 버스트

```python
# services/news/tasks.py:1042-1049
batch_size = 84  # 503 / 6 ≈ 84
batches = [sp500[i:i+84] for i in range(0, len(sp500), 84)]
chord(collect_sp500_news_fmp_batch.s(batch) for batch in batches)(...)
# → 6개 batch 서브태스크를 chord로 동시 디스패치
# collect_sp500_news_fmp_batch: for symbol in symbols → 종목당 FMP 1회 (84회/batch)
```

- **총 호출/run**: 6 batch × 84 = **~504 FMP calls**
- **실행 시각**: 06:15, 10:15, 13:15, 15:15, 17:15 (평일) = **5회/일 × 504 ≈ 2,520 calls/일**
- **버스트 위험 (환경별)**:
  - **prod(prefork, 워커 ≥6)**: 6 batch **병렬** 실행 → 6 종목 동시 처리, calls/sec 급증 → 호출 ~0.4s 가정 시 **약 900~1,200 calls/min** → **FMP 300/min의 3~4배 초과** 🔴
  - **dev(macOS solo)**: 6 batch **직렬** → ~2.5 calls/sec ≈ 150/min → 안전하나 1 run ≈ **3.4분 소요**
- `CircuitBreaker("fmp")`는 **실패 차단용**이지 rate limiter가 아님 → 버스트 미방어

#### FMP 동시 압박 구간 (시장 시간 + 오케스트레이터 겹침)

`10:15`, `13:15`, `15:15`에 sp500-news chord가 다음과 동시:
- `update-realtime-prices` (*/5, 종목당 1 call, `for symbol in symbols`)
- `update-market-indices` (*/5, `get_all_market_quotes()` 벌크 1 call)

→ 10/13/15시 :15분에 **504 버스트 + 시장시간 정기호출 중첩** = FMP 분당 압박 피크.

#### FMP RPD 추정

| 태스크 | 일 호출(추정) |
|--------|--------------|
| sp500-news orchestrator (5회×504) | ~2,520 |
| update-market-indices (*/5, 8h, 벌크) | ~96 |
| update-realtime-prices (*/5, 8h, 포트폴리오 종목) | 가변(포트폴리오 크기 의존) |
| sync-sp500-financials (101/일) | ~101 |
| sync-sp500-eod-prices (벌크 `sync_eod_prices`) | 소량 |
| press-releases(50) + general-news(3회) + movers | ~수백 |
| **합계** | **~3,000~4,000/일** |

→ **10,000 RPD 대비 30~40%**, 일일 예산은 안전. **문제는 분당 버스트(위)**.

### 1-5. Alpha Vantage (5/분)

```
grep alpha_vantage|AlphaVantage|ALPHA_VANTAGE → 태스크 파일 내 0건
```

→ **현재 beat_schedule의 어떤 태스크도 Alpha Vantage를 호출하지 않음.** AV rate limit 위험 **해당 없음**.

---

## 2. Queue 몰림 분석

### 2-1. 큐 구성

| 큐 | 워커 풀 | 동시성 | 라우팅 소스 |
|----|--------|--------|------------|
| `default` | prefork(prod) / solo(macOS) | N / 1 | 기본 |
| `neo4j` | **solo (`--pool=solo`)** | **1 (직렬)** | `task_routes` (L43-61) + `options.queue` |

### 2-2. 🔴 neo4j 큐 = 단일 직렬 워커 = 최대 병목

neo4j 큐로 라우팅되는 태스크 + 실행 빈도:

| 태스크 | 시각(ET) | 1회 소요(추정) |
|--------|---------|---------------|
| `sec-sync-dirty-neo4j` | **매 */5분 (288회/일)** | 짧음, expires=240s(4분) |
| `sync-news-to-neo4j` | 8/10/12/14/16/18 :45 | max 100 articles |
| `enrich-relationship-keywords` | 05:30 | **~6.6분 (100×4s)** |
| `chainsight-sync-profiles-neo4j` | 12:00 | |
| `chainsight-sync-relations-neo4j` | 12:30 | |
| `cleanup-expired-news-relationships` | 04:00 | |
| `neo4j-health-check` | */6h (00/06/12/18:00) | |
| `chainsight-neo4j-dirty-sync` | 일요일 04:30 | |

**모든 위 태스크가 동시성 1짜리 단일 워커에서 직렬 처리됨.**

#### 병목 시나리오 A — enrich가 sec-dirty를 굶김 (05:30)

- 05:30 `enrich-relationship-keywords` 시작 → 단일 neo4j 워커를 **~6.6분 점유**
- 그 사이 `sec-sync-dirty-neo4j`가 05:30, 05:35에 큐 적재 → 워커 점유로 대기
- sec-dirty의 `expires=240s(4분)` → **6.6분 대기 시 만료되어 폐기(discard)** 🟠
- 결과: 05:30~05:37 구간 SEC dirty evidence → Neo4j 동기화 **1~2 사이클 누락** (다음 */5에 복구되나 지연)

#### 병목 시나리오 B — 12:00 정오 neo4j 큐 폭주 (P1)

12:00 ET에 neo4j 큐로 동시 적재:
- `neo4j-health-check` (12:00, */6h)
- `chainsight-sync-profiles-neo4j` (12:00)
- `sec-sync-dirty-neo4j` (12:00, */5)
- (12:30) `chainsight-sync-relations-neo4j` + sec-dirty(12:30)
- (12:45) `sync-news-to-neo4j` + sec-dirty(12:45)

→ 단일 워커 직렬 → 앞선 태스크 지연 시 sec-dirty 만료 위험 + chainsight sync 밀림.
12:00~13:00은 **neo4j 큐 최대 부하 구간**.

### 2-3. default 큐 시간대별 부하

default 큐는 prod prefork 시 동시성이 있으나, **시장시간(09-16 ET)에 고빈도 정기 태스크가 집중**:

| 태스크 | 빈도 | 시장시간 실행/시 |
|--------|------|----------------|
| `refresh-market-pulse-cache` | */1분 9-16 | **60회/시** |
| `update-realtime-prices` | */5분 9-16 | 12회/시 |
| `update-market-indices` | */5분 9-16 | 12회/시 |
| `calculate-portfolio-values` | */10분 9-16 | 6회/시 |
| `check-screener-alerts` | */15분 9-16 | 4회/시 |
| `sec-sync-dirty-neo4j` | */5분 (종일) | 12회/시 (단 neo4j 큐) |
| `check-pipeline-alerts` | */30분 (종일) | 2회/시 |

→ 시장시간 default 큐는 **시당 ~94 firing** (대부분 `refresh-market-pulse-cache` 60 + realtime/indices 24).
`refresh-market-pulse-cache`는 캐시 갱신(외부 API 의존도 낮음, 캐시된 데이터 사용)이라 **외부 API 압박은 낮으나 워커 점유/DB 부하**는 발생.

---

## 3. 시간대별 태스크 실행 히트맵 (평일 ET 기준)

> 단위 = 해당 시(hour)에 **신규 시작되는 beat firing 수** (chord 서브태스크 6개는 별도 표기)
> 기준선(매시 공통) = `check-pipeline-alerts`(2) + `sec-sync-dirty-neo4j`(12) = **14**

```
 ET │ 실행수 │ 히트맵 (1█ ≈ 3 firing)                          │ 비고
────┼────────┼──────────────────────────────────────────────┼──────────────────────────
 00 │   15   │ █████                                          │ neo4j-health-check
 01 │   15   │ █████                                          │ economic-calendar
 02 │   14   │ █████                                          │ (월간/토요일 태스크 거점)
 03 │   14   │ █████                                          │ (일요일 ML/CS 거점)
 04 │   15   │ █████                                          │ cleanup-news-rel
 05 │   15   │ █████                                          │ ★enrich(Gemini,neo4j 6.6분)
 06 │  19+6  │ ███████ +chord6                               │ 🟠FMP아침클러스터+sp500news
 07 │   20   │ ███████                                        │ movers/press/heat/digest 집중
 08 │   19   │ ███████                                        │ kw-pipeline+analyze-deep(Gemini)
 09 │  110   │ ████████████████████████████████████          │ 📈시장시간開 +sentiment
 10 │ 113+6  │ █████████████████████████████████████ +chord6 │ 🔴analyze-deep+co-mention+FMP버스트
 11 │  109   │ ████████████████████████████████████          │ relation-confidence
 12 │  117   │ ██████████████████████████████████████        │ 🔴최대부하: neo4j큐폭주+Gemini+FMP
 13 │ 111+6  │ █████████████████████████████████████ +chord6 │ seed-selection+FMP버스트
 14 │  113   │ █████████████████████████████████████          │ analyze-deep(Gemini)
 15 │ 110+6  │ ████████████████████████████████████ +chord6  │ FMP버스트
 16 │  114   │ █████████████████████████████████████          │ 🔴analyze-deep+extract-kw+breadth+heatmap (시장 마감)
 17 │  18+6  │ ██████ +chord6                                │ FMP버스트 (시장정기호출 종료)
 18 │   26   │ █████████                                      │ 🔴EOD파이프라인 12태스크 집중
 19 │   16   │ █████                                          │ ml-labels+backfill
 20 │   15   │ █████                                          │ sp500-financials(FMP 101)
 21 │   14   │ █████                                          │
 22 │   15   │ █████                                          │ economic-indicators
 23 │   14   │ █████                                          │
```

### 3-1. 히트맵 해석 — "총 firing" vs "외부 API 압박"

위 09~16시 수치(~110)는 대부분 `refresh-market-pulse-cache`(*/1=60/시)와 `sec-dirty`(12/시) 같은
**내부/캐시 태스크**가 부풀린 것이다. **외부 API(FMP/Gemini) 실호출 압박** 기준으로 재정렬하면:

```
외부 API 압박 피크 (실호출 기준)
 ET │ FMP                          │ Gemini              │ 종합
────┼──────────────────────────────┼─────────────────────┼──────────
 06 │ ███ sp500news504+아침클러스터 │ ─                   │ 🟠 FMP
 10 │ ███ sp500news504+시장정기     │ ██ analyze50+comen  │ 🔴 동시
 12 │ ██  시장정기                  │ ██ analyze50        │ 🔴 +neo4j큐
 13 │ ███ sp500news504+시장정기     │ ─                   │ 🟠 FMP
 15 │ ███ sp500news504+시장정기     │ ─                   │ 🟠 FMP
 16 │ ██  breadth/heatmap           │ ██ analyze50+extract│ 🔴 Gemini(15분분리됨)
 17 │ ███ sp500news504              │ ─                   │ 🟠 FMP
 18 │ ██  eod-prices                │ █ thesis-summaries  │ 🟠 EOD
```

**피크 식별**:
- **FMP 분당 버스트 피크**: 10:15 / 13:15 / 15:15 (sp500news chord 504 + 시장정기호출 중첩) — prod prefork에서 300/min 초과
- **neo4j 큐 피크**: 12:00~13:00 (health+chainsight×2+news+sec-dirty 직렬 적체)
- **Gemini 피크**: 16:30/16:45 (analyze-deep + extract-kw, 15분 분리로 회피 중)
- **종합 위험 최고 시각**: **12:00 ET** (FMP+Gemini+neo4j 3종 동시) 및 **18:00 ET** (EOD 파이프라인 데이터 경합)

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-1. 🔴 P0 — EOD 저녁 파이프라인 암묵적 의존 + 동시 시작 경합 (18:00 ET)

18:00에 **동시 시작**되는 태스크 중 데이터 의존 관계:

```
18:00 ┬─ sync-sp500-eod-prices       → DailyPrice 기록 (선행 데이터 소스)
      ├─ thesis-update-readings      → 지표 수집 (DailyPrice 의존 가능성!) ⚠️ 동시 시작
      ├─ update-economic-indicators
      └─ collect-market-news-evening
18:15 ┬─ thesis-calculate-scores     → update-readings 결과 의존
      └─ classify-news-batch
18:30 ┬─ update-sp500-change-percent → sync-eod-prices(DailyPrice) 의존
      ├─ run-eod-pipeline            → sync-eod-prices(DailyPrice) 의존
      ├─ thesis-create-snapshots     → calculate-scores 의존
      └─ analyze-news-deep-batch
18:35 └─ thesis-generate-summaries   → create-snapshots 의존
```

**경합 위험**:
1. **`thesis-update-readings`(18:00)가 `sync-sp500-eod-prices`(18:00)와 동일 분 시작** → thesis 지표가 오늘자 DailyPrice를 참조한다면, EOD 가격 기록 **완료 전에 읽어 stale 데이터** 사용 가능. crontab은 실행 순서 보장 없음.
2. `run-eod-pipeline`/`update-sp500-change-percent`(18:30)는 `sync-eod-prices`(18:00) 완료를 **30분 시간 간격에만 의존** (chain/chord 없음). EOD sync가 지연/실패하면 **stale 데이터로 조용히 진행**.
3. thesis 4단계(18:00→18:15→18:30→18:35)는 **15분 시간 결합**으로만 순서 보장. `update-readings`가 15분 초과 시 `calculate-scores`가 미완성 데이터로 시작.

> **권장(분석)**: 시간 분리 대신 Celery `chain()`/`chord()`로 **데이터 의존을 명시적 체이닝**.
> 예: `sync_eod_prices | (run_eod_pipeline, update_change_percent, thesis_chain)`

### 4-2. 🟠 P1 — Chain Sight 일일 체인 시간 결합

```
10:00 co-mentions → 11:00 relation-confidence("CoMention 후")
                  → 12:00 sync-profiles-neo4j → 12:30 sync-relations-neo4j
                  → 13:00 seed-selection (관계 동기화 의존)
```
- 각 1시간 간격으로 여유 있으나 **명시적 체이닝 부재**. co-mentions(LLM)가 1시간 초과 시 하류 stale.
- `chainsight-heat-score-daily`(07:00) 주석 "시드 선정 전" + `seed-selection`(13:00) — ET 순서는 정상.

### 4-3. 🟠 P1 — neo4j 큐 직렬 경합 (§2-2 참조)

- 05:30 enrich(6.6분) → sec-dirty(expires 4분) 만료 폐기
- 12:00 health + chainsight-profiles + sec-dirty 직렬 적체

### 4-4. ⚠️ 타임존 주석 불일치 (문서 결함)

여러 태스크 주석이 "UTC"라 표기되어 있으나 **실제로는 ET로 실행**됨:

| 태스크 | 주석 표기 | 실제 실행(ET) | 한국시각(KST) |
|--------|----------|--------------|--------------|
| `chainsight-heat-score-daily` | "07:00 UTC" | 07:00 ET | ≈ 20:00~21:00 KST |
| `chainsight-seed-selection` | "13:00 UTC" | 13:00 ET | ≈ 02:00~03:00 KST |
| `chainsight-neo4j-dirty-sync` | "04:30 UTC" | 04:30 ET | ≈ 17:30~18:30 KST |

→ 의존 순서 판단 시 혼란 유발. 코드 동작은 ET로 일관되나 **주석을 ET로 정정 필요** (읽기 전용이므로 미수정, 권고만).

### 4-5. 정상 — 겹침 없으나 클러스터된 구간

- **06:00~07:45 아침 FMP/뉴스 클러스터**: daily-news(06:00) + econ-ind(06:00) + sp500news(06:15) + cat-high(06:30) + gen-news(06:45) + heat-score(07:00) + cat-med(07:00) + error-digest(07:00) + cat-low(07:30) + movers(07:30) + press-rel(07:45). 데이터 경합은 없으나 FMP 분당 압박 누적.

---

## 5. 종합 위험 등급표

| # | 위험 | 등급 | 환경 | 근거 |
|---|------|------|------|------|
| 1 | Gemini 전역 분산 limiter 부재 (프로세스 로컬 sleep만) | 🔴 P0 | prod prefork / 큐 분리 시 | §1-1 |
| 2 | sp500-news chord 6병렬 → FMP 300/min 3~4배 버스트 | 🔴 P0 | prod prefork | §1-4 |
| 3 | EOD 18:00 파이프라인 암묵적 의존 + 동시 시작 (stale 위험) | 🔴 P0 | 전 환경 | §4-1 |
| 4 | neo4j 단일 solo 워커 직렬 병목 (12시 폭주, enrich굶김) | 🟠 P1 | 전 환경 | §2-2 |
| 5 | Chain Sight 일일 체인 시간 결합 (명시적 chain 부재) | 🟠 P1 | 전 환경 | §4-2 |
| 6 | sec-dirty expires=240s가 neo4j 큐 점유 시 만료 폐기 | 🟠 P1 | 전 환경 | §2-2 A |
| 7 | dict vs DB(PeriodicTask) drift 가능성 (실행 진실은 DB) | 🟠 P1 | 전 환경 | §0, bug #28 |
| 8 | 타임존 주석 "UTC" 오기 (실제 ET) | 🟡 P2 | 문서 | §4-4 |
| 9 | Gemini RPD ~600+ (thesis/월간 증가 시 한도 접근) | 🟡 P2 | 부하 증가 시 | §1-3 |

---

## 6. 권고 사항 (분석 — 코드 미수정)

1. **[P0] Gemini 전역 limiter**: Redis 기반 분산 토큰버킷(예: 4초 글로벌 락 또는 `15/min` 셀러리 `task_annotations rate_limit`)으로 전 워커 합산 RPM 통제. 현재 "시간 분리" 방어선은 취약.
2. **[P0] FMP 버스트**: `collect_sp500_news_fmp_orchestrator`의 chord 6병렬을 **순차 chain** 또는 batch당 `rate_limit` 적용. CircuitBreaker는 rate limiter 아님.
3. **[P0] EOD 의존 체이닝**: 18:00~18:35 시간 결합을 `chain()`/`chord()`로 명시화. 특히 `sync-sp500-eod-prices → (thesis-update-readings, run-eod-pipeline, update-change-percent)`.
4. **[P1] neo4j 큐**: enrich를 별도 시간대로 이동하거나, sec-dirty expires를 늘려 굶김 방지. 12시 정오 neo4j 적재 분산.
5. **[P1] DB drift 검증 자동화**: §0 diff 스크립트를 주기 점검(또는 nightly 자동화)으로 편입.
6. **[P2] 주석 정정**: chainsight/sec 태스크의 "UTC" 주석 → "ET"로 통일.

---

## 부록 A — 데이터 소스 (읽기 전용 grep 근거)

| 사실 | 위치 |
|------|------|
| 타임존 ET | `config/settings.py:489` `CELERY_TIMEZONE='America/New_York'` |
| dict 무시(DB가 진실) | `config/celery.py:124-140` |
| Gemini sleep(4) 로컬 | `services/news/services/news_deep_analyzer.py:40,99` / `relationship_keyword_enricher.py:53,157` |
| 전역 limiter 부재 | `grep redis.*gemini / GEMINI_RPM / distributed.*rate` → 0건 |
| chord 6배치 | `services/news/tasks.py:1042-1049` |
| batch 종목당 FMP 1회 | `services/news/tasks.py:1022-1042` (`for symbol in symbols`) |
| classify는 rule-based | `services/news/tasks.py:508+` (`NewsClassifier`) |
| neo4j 큐 라우팅 | `config/celery.py:43-61` task_routes |
| neo4j solo 강제 | `config/celery.py:36-37` (macOS) + `--pool=solo` (CLAUDE.md 운영가이드) |
| AV 미사용 | `grep alpha_vantage` 태스크 파일 → 0건 |
| 실시간가 종목당 호출 | `packages/shared/stocks/tasks.py:366+` (`for symbol in symbols`) |

*— 본 보고서는 읽기 전용 감사이며 어떠한 코드/스케줄도 변경하지 않았습니다.*
