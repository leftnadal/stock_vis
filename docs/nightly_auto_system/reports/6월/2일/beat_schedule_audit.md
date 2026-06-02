# Beat Schedule 감사 보고서

- **대상**: `config/celery.py` `app.conf.beat_schedule` (라인 141~820, 총 64개 태스크)
- **작성일**: 2026-06-02
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **분석 기준 timezone**: `America/New_York` (`config/settings.py:489` `CELERY_TIMEZONE = 'America/New_York'`)

---

## 0. 전제 조건 및 핵심 경고 (반드시 먼저 읽을 것)

### ⚠️ C-0: config dict는 런타임에 무시된다 (분석의 대전제)

`config/settings.py`는 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'`를 사용한다.
따라서 **Beat는 `django_celery_beat.PeriodicTask` DB 테이블을 진실의 소스로 사용**하며,
`config/celery.py`의 `beat_schedule` dict는 코드 주석(124~140줄)에서도 명시하듯 **"원래 설계된 스케줄의 선언적 reference"**일 뿐이다.

> **이 보고서는 `beat_schedule` dict를 "설계 의도"로 간주하고 분석한다.**
> 실제 운영 부하를 정확히 알려면 DB의 `PeriodicTask` 테이블과 dict의 diff를 별도로 검증해야 한다 (아래 §6 권고).

### ⚠️ C-1: 일부 주석의 "UTC" 표기는 실제 실행 시각과 불일치 (라벨링 버그)

`CELERY_TIMEZONE`이 `America/New_York`이므로 **모든 `crontab(hour=N)`은 NY 시간으로 해석**된다.
그런데 아래 3개 태스크의 주석은 "UTC"라고 적혀 있어, 실제 발화 시각과 어긋난다:

| 태스크 | 주석 표기 | 실제 발화 (NY 기준) | 차이 |
|--------|----------|---------------------|------|
| `chainsight-heat-score-daily` (748) | "매일 07:00 UTC" | **07:00 NY** | EDT 기준 UTC로는 11:00 |
| `chainsight-seed-selection` (754) | "매일 13:00 UTC" | **13:00 NY** | EDT 기준 UTC로는 17:00 |
| `chainsight-neo4j-dirty-sync` (761) | "매주 일 04:30 UTC" | **04:30 NY** | EDT 기준 UTC로는 08:30 |

→ 의존성("시드 선정 전" 등)이 NY 기준으로는 성립하지만, 주석을 믿고 운영 판단하면 4시간 오차가 발생한다. **주석 정정 필요** (코드 동작 자체는 NY 시간으로 일관됨).

### 참고: Gemini RPM 제어 방식

`services/news/services/news_deep_analyzer.py:40` → `RPM_DELAY = 4` (호출마다 `time.sleep(4)`).
이는 **태스크 내부의 순차 sleep**이며, **프로세스/태스크 간 글로벌 rate limiter가 아니다.**
→ 서로 다른 Gemini 태스크가 동시에 돌면 각자 4초 간격을 지켜도 **합산 RPM이 15를 초과**할 수 있다. (§1, §4의 핵심 리스크 근거)

---

## 1. Rate Limit 초과 구간 분석

> 모든 시각은 **NY 시간 / 평일(Mon-Fri)** 기준. 호출량은 §부록의 태스크별 추정치 사용.

### 1-A. Gemini Free (15 RPM / 1500 RPD) — 🔴 가장 위험

Gemini를 호출하는 태스크와 발화 시각(분 단위):

| 시각(NY) | 태스크 | 추정 LLM 호출 | 소요시간(@4초) |
|----------|--------|--------------|----------------|
| 05:30 | `enrich-relationship-keywords` (limit=100) | ~100 | ~6.7분 (05:30~05:37) |
| 08:00 | `keyword-generation-pipeline` | ~20 | ~1.3분 |
| 08:30 | `analyze-news-deep-batch` | ~50 | ~3.3분 (08:30~08:33) |
| 09:00 | `extract-news-relations` (24h) | ~50-100 | ~3.3~6.7분 |
| 10:30/12:30/14:30/16:30 | `analyze-news-deep-batch` (2시간 주기) | ~50 each | ~3.3분 each |
| 16:45 | `extract-daily-news-keywords` | ~1-2 (배치) | <1분 |
| 18:30 | `analyze-news-deep-batch` | ~50 | ~3.3분 (18:30~18:33) |
| **18:35** | **`thesis-generate-summaries`** | ~10-50 | ~0.7~3.3분 (18:35~) |

**🔴 P0 충돌 후보 — 18:30 ↔ 18:35 (analyze-deep ↔ thesis-summaries)**
- `analyze-news-deep-batch`(50회 @4초) = 정확히 200초 = **18:33:20 종료 예상**.
- `thesis-generate-summaries`(18:35 시작)까지 여유는 약 **1분 40초뿐**.
- analyze-deep가 50개를 초과하거나(`max_articles=50` 상한이지만 재시도·지연 포함), 워커가 밀리면 **두 Gemini 태스크가 겹쳐 합산 RPM > 15** → 429 위험.
- 내부 sleep만으로는 방어 불가(글로벌 limiter 부재). **간격을 18:40 이상으로 벌리거나 단일 큐 직렬화 필요.**

**🟡 P1 — 18:30 analyze-deep ↔ 18:00 thesis-update-readings 잔여**
- 18:00 `thesis-update-readings`는 FMP/FRED 중심이지만 활성 가설 수에 따라 길어지면 18:30대까지 워커 점유 → Gemini 태스크 시작 지연 유발.

**✅ 이미 방어된 구간 (P0 #8, 2026-04-26 주석)**
- 16:30 `analyze-news-deep` ↔ 16:45 `extract-daily-news-keywords`: 15분 분산 처리 완료. analyze가 16:33 종료이므로 16:45와 안전.

**RPD 관점**: 일일 총 Gemini ≈ **600~800회 < 1500 RPD** → **일일 한도는 안전**. 문제는 **분 단위 동시성(RPM)**에 국한.

> 월 1회 `refresh-korean-overviews-monthly`(매월 1일 03:00, ~500 Gemini 호출 @4초 = **~33분 단독 점유**)는 단독 실행이라 RPM은 안전하나, 해당일 RPD를 단독으로 ~500 소비 → 같은 날 다른 Gemini 태스크와 합산 시 1500 RPD 근접 가능 (월 1회라 우선순위 낮음).

### 1-B. FMP Starter (300 calls/min, 10,000/일)

FMP 대량 호출 태스크:

| 시각(NY) | 태스크 | 추정 호출 | 내부 제어 |
|----------|--------|-----------|-----------|
| 06:15/10:15/13:15/15:15/17:15 | `collect-sp500-news-fmp-*` (orchestrator) | **~504 each** | chord + `rate_limit='100/m'` (자체 제한) |
| 06:45/12:30/17:45 | `collect-general-news-fmp-*` | ~1 | — |
| 07:45 | `collect-press-releases-fmp` (50 sym) | ~50 | — |
| 09~16 (*/5) | `update-realtime-prices` + `update-market-indices` | 2 calls × 12회/시간 = 24/시간 | — |
| 16:30/16:35 | `calculate-market-breadth` / `sector-heatmap` | 각 1 (bulk) | — |
| 18:00 | `sync-sp500-eod-prices` | 1 (bulk) | — |
| **20:00** | `sync-sp500-financials` | **~101/일** | `rate_limit='6/m'` → **~17분 소요** |

**판정: FMP는 분당 한도(300/min) 위반 위험 낮음.**
- 대량 태스크(`collect-sp500-news-fmp`)는 **`rate_limit='100/m'`로 자체 제한** → 504건이 ~5분에 분산. 단독 실행 시 300/min의 1/3 수준.
- `sync-sp500-financials`도 `6/m`로 강하게 제한.
- **🟡 잠재 충돌**: 같은 분에 `collect-sp500-news-fmp`(100/m) + 장중 `update-realtime`(분당 일부) + `update-market-indices`가 겹치면 합산 가능. 다만 fmp-news 발화(*:15)와 realtime(*/5 = *:00,05,10,15...)이 **:15에서 겹침** → 그 1분만 일시적 합산. 100 + α로 300 한도 내 유지 추정. **모니터링 권장 수준.**
- 일일 총 FMP ≈ 504×5 + 101 + 기타 ≈ **~2,700~3,000/일 < 10,000/일** → 일일 한도 안전.

### 1-C. Alpha Vantage (5 calls/min, 12초 대기)

- 직접적인 AV 전용 스케줄은 명확히 식별되지 않음. `update-realtime-with_provider`는 **Provider 추상화**로 FMP 우선 사용(부록 참조).
- **판정: AV 의존 스케줄 없음 또는 FMP로 대체됨 → AV 5/min 한도 리스크 없음.**
- 단, Provider fallback이 AV로 전환되는 경로가 있다면 `update-realtime-prices`(*/5, 장중)가 5/min을 초과할 수 있으므로 **Provider 우선순위 설정 확인 권장** (코드상 FMP 우선이면 무해).

### 1-D. FRED (`update-economic-indicators`)

- 06/12/18/22시 평일 × 7개 지표 = **회당 7 호출**. FRED는 한도 넉넉(120/min) → **안전**.

---

## 2. Queue 몰림 분석 (default vs neo4j)

### 2-A. neo4j 큐 — 🔴 solo pool 직렬화 병목

neo4j 큐는 **`--pool=solo`(동시 1개)**로 운영(CLAUDE.md). 라우팅 대상(`config/celery.py:43-61`)과 beat 태스크:

| 시각(NY) | 태스크 | neo4j 큐 점유 추정 | 비고 |
|----------|--------|---------------------|------|
| **상시** | `sec-sync-dirty-neo4j` (`*/5`) | 짧음, 12회/시간 | `expires=240`(4분) ← **밀리면 만료 스킵** |
| 6시간마다 | `neo4j-health-check` | 짧음 | — |
| 04:00 | `cleanup-expired-news-relationships` | 중간 | 매일 |
| **05:30** | `enrich-relationship-keywords` | **~6.7분 점유** | Gemini+neo4j 동시 |
| 08:45/10:45/.../18:45 | `sync-news-to-neo4j` (max=100) | 중간~김 | 2시간 주기 |
| 12:00 | `chainsight-sync-profiles-neo4j` | 중간 | 매일 |
| 12:30 | `chainsight-sync-relations-neo4j` | 중간 | 매일 |
| 일 04:30 | `chainsight-neo4j-dirty-sync` | 중간 | 주간 |

**🔴 P0 핵심 리스크 — `sec-sync-dirty-neo4j`의 `expires=240` 만료 스킵**
- `sec-sync-dirty-neo4j`는 **5분마다** 발화하고 **4분 후 만료**된다.
- solo pool에서 `enrich-relationship-keywords`(05:30~05:37, ~6.7분) 또는 긴 `sync-news-to-neo4j`가 큐를 점유하면, 그 사이 발화한 `sec-sync-dirty-neo4j`가 **4분 안에 실행되지 못하고 만료(expire)되어 조용히 누락**된다.
- 결과: SEC dirty evidence의 Neo4j 동기화가 **간헐적으로 건너뛰어짐** → 데이터 정합성 구멍. (장기적으로는 다음 회차가 잡지만, 지연 누적)

**🟡 P1 — 12:00/12:30 neo4j 큐 직렬 적체**
- 12:00 `sync-profiles-neo4j` → 12:30 `sync-relations-neo4j` → 12:45 `sync-news-to-neo4j`(평일)가 30분 내 연속.
- solo 1개이므로 profiles가 길어지면 relations·news가 밀리고, 그 사이 `sec-sync-dirty`(*/5) 3회가 큐에서 경쟁 → 일부 만료.

### 2-B. default 큐 — 🟡 18:30 동시 발화 스파이크

default 큐는 prefork(Linux)지만 **macOS 개발 환경은 solo 강제**(`config/celery.py:36-37`) → 로컬에선 default도 직렬.

**🟡 18:30 NY 동시 발화 4건 (default 큐)**:
- `run-eod-pipeline`
- `thesis-create-snapshots-and-alerts`
- `analyze-news-deep-batch` (Gemini 50회, ~3.3분 점유)
- `update-sp500-change-percent`

→ macOS solo 환경에서는 **이 4건이 순차 처리되며 analyze-deep(3.3분)가 뒤 작업을 지연**시킨다. 18:35 `thesis-generate-summaries`까지 줄줄이 밀릴 수 있음(§1-A P0와 연결).

---

## 3. 시간대별 API 호출 히트맵 (평일 / NY 시간)

> 막대 = 해당 시간대의 **외부 API/LLM 호출 추정 총량**(로그 스케일 감각). 장중 캐시 갱신 등 **API 비호출** 반복 태스크는 제외(§3-B 별도).

### 3-A. 외부 API/LLM 호출량 히트맵

```
시각  호출유형                                          추정호출  막대
00 │                                                      ~0  
01 │ calendar                                             ~1  ▏
02 │ (monthly only)                                       ~0  
03 │ (monthly/weekend only)                               ~0  
04 │ (neo4j cleanup)                                      ~0  
05 │ ░░░░░░░░░░ Gemini enrich(100)                       ~100  █████▏        🔴LLM
06 │ ██████████ FMP-news504 +daily-news +cat +FRED       ~607  ██████████▏  🔴FMP피크
07 │ ███ press-fmp50 +category +movers                   ~131  ███▎
08 │ ░░░ Gemini kw20+deep50 +market-news                  ~71  ██▊          🟡LLM
09 │ ░░ Gemini relations75 +FMP장중24                     ~99  ███▏         🟡LLM
10 │ ██████████ FMP-news504 +deep50 +장중24              ~578  ██████████▏  🔴FMP+LLM
11 │ ▏ 장중24                                              ~24  █▏
12 │ ░ deep50 +FRED7 +FMP장중26 +general-fmp              ~83  ██▌          🟡LLM
13 │ ██████████ FMP-news504 +cat75 +장중24               ~603  ██████████▏  🔴FMP피크
14 │ ░ deep50 +daily-news20 +cat50 +장중24               ~144  ███▋         🟡LLM
15 │ ██████████ FMP-news504 +장중24                      ~529  ██████████▏  🔴FMP피크
16 │ ░ deep50 +kw2 +breadth/heatmap +장중24               ~78  ██▌          🟡LLM+EOD진입
17 │ █████████ FMP-news504 +cat75 +daily-prices          ~580  █████████▊   🔴FMP피크
18 │ ░░ deep50+summaries50(LLM100) +thesis-readings200   ~350  ██████▌      🔴LLM+FMP+EOD집중
19 │ (DB only: ml-labels, backfill)                       ~0  
20 │ ██ FMP financials101 (6/m, 17분 분산)               ~101  ███▏
21 │                                                      ~0  
22 │ FRED7                                                 ~7  ▏
23 │                                                      ~0  
```

**피크 시간대 식별**:
1. **06시 (~607)** — `collect-sp500-news-fmp-0615`(504) + 아침 뉴스/카테고리/FRED 동시 시작. FMP 일일 최대 스파이크.
2. **13시 / 15시 / 17시 (~500~600)** — `collect-sp500-news-fmp`(504) 반복. FMP 집중(자체 rate_limit으로 분산됨).
3. **10시 (~578)** — FMP-news 504 + Gemini analyze-deep 50 **동시 시간대**(분은 10:15 vs 10:30로 분리).
4. **18시 (~350, LLM 100)** — 🔴 **Gemini·FMP·EOD·Thesis 파이프라인 총집결**. 호출 절대량보다 **LLM 동시성·의존성 측면에서 최대 위험 구간**.

### 3-B. 참고: API 비호출 반복 태스크 (장중 9~16시, 부하의 "착시" 주의)

아래는 외부 API를 호출하지 않으나 **워커 슬롯을 점유**하는 고빈도 반복 태스크 → 위 히트맵에서 제외했으나 큐 부하엔 기여:

| 태스크 | 빈도 | 시간당 실행 | API |
|--------|------|------------|-----|
| `refresh-market-pulse-cache` | `*`(매분) @9-16 | **60회/시간** | 없음(캐시) |
| `calculate-portfolio-values` | `*/10` @9-16 | 6회/시간 | 없음(DB) |
| `check-screener-alerts` | `*/15` @9-16 | 4회/시간 | 없음(DB필터) |
| `check-pipeline-alerts` | `*/30`(상시) | 2회/시간 | 없음 |
| `sec-sync-dirty-neo4j` | `*/5`(상시) | 12회/시간 | Neo4j only |

→ **장중(9~16시) 총 태스크 실행 횟수는 시간당 ~110회**에 달하나 대부분 캐시/DB 작업. macOS solo 환경에선 `refresh-market-pulse-cache`(매분)가 큐를 자주 점유 → 다른 default 태스크 지연 요인.

---

## 4. 스케줄 겹침 / 의존성 분석

### 4-A. 의존성 체인 — 선행 미완료 시 후속 빈 데이터 위험

**🔴 P0 — Thesis EOD 파이프라인 (18:00→18:15→18:30→18:35, 15분 간격)**
```
18:00 thesis-update-readings   (FMP+FRED, 활성가설×지표 = 50~200 호출)
  └─ 18:15 thesis-calculate-scores        (readings 의존)
       └─ 18:30 thesis-create-snapshots   (scores 의존)
            └─ 18:35 thesis-generate-summaries (Gemini, snapshot 의존)
```
- **리스크**: `thesis-update-readings`가 50~200 API 호출이면, FMP rate 제한·재시도 포함 시 **15분 내 완료를 보장 못 함**. 미완료 상태로 18:15 `calculate-scores`가 시작하면 **누락 지표로 스코어 계산** → 잘못된 스냅샷·요약 연쇄.
- 현재는 **시간 간격(implicit ordering)**에만 의존하며 **명시적 완료 신호(chain/chord/체인 콜백)가 없음**. → 부하 증가 시 깨질 구조.

**🟡 P1 — News Intelligence 파이프라인 (수집→분류→분석→Neo4j)**
```
*:00 수집 (collect-*) → *:15 classify → *:30 analyze-deep → *:45 sync-news-neo4j  (2시간 주기)
```
- 15분 간격 staggering으로 설계됨(양호). 단 analyze-deep(3.3분)·sync-news가 길어지면 다음 주기와 누적 가능. `expires=3600`으로 일부 방어.

**🟡 P1 — EOD 가격 → EOD 파이프라인**
```
18:00 sync-sp500-eod-prices (FMP bulk, 빠름) → 18:30 run-eod-pipeline (DB 기반)
```
- 30분 간격 + eod-prices가 bulk 1콜이라 빠름 → **양호**. 단 `run-eod-pipeline`은 18:30에 analyze-deep·thesis-snapshots와 **동시 발화**(§2-B).

**🟢 Chain Sight 주말 배치 (토요일)**: `02:00 all-profiles → 03:00 price-co-movement → 04:00 stale-decay → 04:30 aggregate → 05:00 validation` — 1시간씩 충분히 벌려 의존성 안전.

### 4-B. 동시 발화 충돌 매트릭스 (같은 분, 평일 NY)

| 발화 시각 | 동시 태스크 | 리스크 | 등급 |
|-----------|-------------|--------|------|
| **18:30** | run-eod-pipeline, thesis-create-snapshots, analyze-news-deep(Gemini), update-sp500-change-percent | default 큐 4건 직렬(macOS) + Gemini 점유 | 🔴 |
| **18:35** | thesis-generate-summaries(Gemini) — 18:30 analyze-deep 종료(18:33)와 1분40초 간격 | Gemini 합산 RPM 초과 가능 | 🔴 |
| **12:00** | sync-profiles-neo4j, sec-seed-relations, market-news-noon, econ-indicators, (장중 반복) | neo4j 큐 + default 혼잡 | 🟡 |
| **12:30** | sync-relations-neo4j, general-fmp-noon | neo4j 직렬 | 🟡 |
| **06:00** | collect-daily-news, econ-indicators, sync-etf-holdings(월), sec-check-filings(1일) | default 동시 + 06:15 FMP-news 직전 | 🟡 |
| **05:30** | enrich-relationship-keywords (Gemini+neo4j 6.7분) | sec-sync-dirty(*/5) 만료 유발 | 🟡 |
| **04:30** | build-patent-network(1일), chainsight-stale-decay(토), chainsight-aggregate(토), neo4j-dirty-sync(일) | 요일/날짜 분리되어 실제 동시성 낮음 | 🟢 |
| ***:15** | collect-sp500-news-fmp(100/m) + update-realtime-prices(*/5) | FMP 합산 일시 증가 | 🟡 |

---

## 5. 종합 리스크 요약

| ID | 등급 | 구간 | 문제 | 권고 |
|----|------|------|------|------|
| R1 | 🔴 | 18:30↔18:35 | analyze-deep ↔ thesis-summaries Gemini 합산 RPM>15 | 간격 18:40+ 확대 또는 Gemini 전용 단일 큐 직렬화 |
| R2 | 🔴 | 18:00~18:35 | Thesis 파이프라인이 시간 간격에만 의존(명시적 완료 신호 없음) | Celery `chain`/`chord`로 선후 보장 |
| R3 | 🔴 | 상시 neo4j | `sec-sync-dirty-neo4j`(`expires=240`)가 solo 큐 점유 시 만료 스킵 | expires 상향 또는 별도 큐/주기 완화 |
| R4 | 🟡 | 18:30 | default 큐 4건 동시(macOS solo 직렬) | 발화 시각 분산(±5분) |
| R5 | 🟡 | 12:00~12:45 | neo4j 큐 연속 3건 + sec-dirty 경합 | 간격 확대 또는 neo4j 워커 동시성 검토 |
| R6 | 🟡 | C-1 | chainsight 3건 주석 "UTC" 오기 | 주석을 "NY"로 정정 |
| C0 | ⚠️ | 전체 | config dict ≠ 실제 DB 스케줄(DatabaseScheduler) | DB `PeriodicTask` ↔ dict diff 정기 검증 |

**한도 위반 판정 종합**:
- **Gemini RPM(15)**: 🔴 **18:30/18:35 동시성에서 초과 가능** (RPD 1500은 안전).
- **FMP(300/min, 10k/일)**: 🟢 자체 rate_limit으로 분당·일일 모두 한도 내 (*:15 일시 합산만 모니터링).
- **Alpha Vantage(5/min)**: 🟢 전용 스케줄 없음(FMP Provider 우선) — Provider fallback 경로만 확인 권장.
- **Neo4j solo 큐**: 🔴 직렬 병목 + sec-dirty 만료 스킵 (한도가 아닌 **처리량/정합성** 문제).

---

## 6. 검증·후속 권고 (읽기 전용 범위 밖, 별도 작업 제안)

1. **DB ↔ dict drift 검증** (C0):
   `python manage.py shell` →
   `set(PeriodicTask.objects.values_list('name', flat=True))` vs `app.conf.beat_schedule.keys()` diff.
2. **Gemini 글로벌 rate limiter 도입 검토** (R1): 태스크 내부 sleep 대신 Redis 기반 토큰 버킷으로 프로세스 간 RPM 공유.
3. **Thesis 파이프라인 chain 전환** (R2): `update_readings.s() | calculate_scores.s() | create_snapshots.s() | generate_summaries.s()`.
4. **`sec-sync-dirty-neo4j` expires/주기 재조정** (R3): solo 큐 최장 점유(enrich 6.7분)보다 expires를 길게(예: 600초) 또는 주기를 10분으로.
5. **주석 정정** (R6): chainsight 3건 "UTC" → "NY" (코드 변경 아님, 문서/주석만).

---

## 부록: 태스크별 외부 API 의존성 (추정 호출량)

| 태스크 | API | 1회 추정 호출 | 근거 |
|--------|-----|--------------|------|
| update_realtime_with_provider | FMP(우선) | ~10 | stocks/tasks.py:366 |
| sync_sp500_financials | FMP | ~101/일 (6/m) | stocks/tasks.py:138 |
| sync_sp500_eod_prices / constituents | FMP | 1 (bulk) | stocks/tasks.py:432,454 |
| bulk_generate_korean_overviews | **Gemini** | ~500/월 | stocks/tasks.py:790 |
| update_economic_indicators | FRED | ~7 | macro.py:14 |
| update_market_indices | FMP | 1 | macro.py:64 |
| collect_daily_news | Finnhub/Marketaux | ~20 | news/tasks.py:104 |
| collect_market_news | Finnhub/Marketaux | ~1 | news/tasks.py:195 |
| collect_category_news | Finnhub/Marketaux | ~50-100 | news/tasks.py:351 |
| collect_sp500_news_fmp_orchestrator | **FMP** | **~504** (6배치, 100/m) | news/tasks.py:1022 |
| collect_press_releases_fmp | FMP | ~50 | news/tasks.py:1069 |
| collect_general_news_fmp | FMP | ~1 | news/tasks.py:1126 |
| analyze_news_deep | **Gemini** | **~50** (@4초) | news_deep_analyzer.py:40,99 |
| classify_news_batch | 없음(DB) | 0 | news/tasks.py:508 |
| extract_daily_news_keywords | **Gemini** | ~1-2 배치 | news/tasks.py:26 |
| aggregate_daily_sentiment | 없음 | 0 | news/tasks.py:251 |
| collect_ml_labels | 없음(DB) | 0 | news/tasks.py:603 |
| keyword_generation_pipeline | **Gemini** | ~20 | serverless/tasks.py:451 |
| extract_news_relations | **Gemini** | ~50-100 | serverless/tasks.py:1559 |
| enrich_relationship_keywords | **Gemini** | ~100 | serverless/tasks.py:1601 |
| sync_daily_market_movers | FMP | ~1 | serverless/tasks.py:23 |
| sync_etf_holdings | 내부 CSV | ~21 | serverless/tasks.py:942 |
| sync_supply_chain_batch | SEC EDGAR | ~100/월 | serverless/tasks.py:1182 |
| sync_institutional_holdings | SEC 13F | ~20-50/분기 | serverless/tasks.py:1647 |
| build_patent_network | USPTO | ~25-100/월 | serverless/tasks.py:1747 |
| calculate_daily_market_breadth / sector_heatmap | FMP | 각 1 | serverless/tasks.py:490,558 |
| check_screener_alerts | 없음(DB) | 0 | serverless/tasks.py:634 |
| thesis update_indicator_readings | FMP+FRED | ~50-200/일 | thesis/tasks/eod_pipeline.py:274 |
| thesis generate_thesis_summaries | **Gemini** | ~10-50/일 | thesis/tasks/summary.py:79 |
| chain_sight calculate_all_profiles / co_mentions / price_co_movement | 없음(DB) | 0 | chain_sight/tasks/* |

> 호출량은 코드상 루프/배치 크기 기반 **추정치**이며, 활성 종목·가설·뉴스 건수에 따라 변동한다. 정밀 측정은 운영 로그(`stocks.log`) 기준 별도 집계 필요.
