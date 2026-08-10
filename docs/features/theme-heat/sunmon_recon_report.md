# SUNMON-RECON — CORPUS-SUNMON-EMPTYKW 근원 정찰 + 해자 3문항 (2026-08-10)

> **성격**: read-only 정찰. 원인 후보 규명만, 조치는 다음 결정 사이클.
> **세션**: `monorepo/sess-sunmon-recon` · base `a9d7f388`(→ff `85c16572`)
> **STEP 0**: machine clock 2026-08-10 07:31 UTC / 16:31 KST / 03:31 ET · health 13 OK / 2 WARN(#47 실행트리 뒤처짐·blocked pending) / 0 FAIL

---

## ⓐ 해자 3문항 — RelationPairSnapshot 궤적 = 건강 (적립 정상)

| 문항 | 실측 | 판정 |
|---|---|---|
| ① 궤적 타임스탬프 | period 2026-07-01~08-09, **매일 9562행 일관**(무결손). beat `chainsight-pair-aggregation` runs=40, last_run 08-09 15:30 UTC(=11:30 EDT). 필드 `created_at`+`last_observed_at` 보유 | ✅ 매일 적립 |
| ② 저장 경로 | 테이블 **`chainsight_relation_pair_snapshot`** (PostgreSQL), `pair_aggregation.py` `update_or_create` per (canonical_a, canonical_b, period). 총 372,918행 | ✅ 정상 |
| ③ 실패 로그 | 워커 로그 `RelationPairSnapshot 집계: {pairs:9562, created:9562, updated:0}` 매일 성공. **실패·retry 0** | ✅ 무오류 |

**결론**: 버그 #28(적립 침묵) **완전 해소** — 07-01부터 매일 적립. `updated:0`은 정상(period가 unique 키라 매일 신규 append).

**⚠️ 별개 이슈 표면화 — 폭(width) 정체**: 모든 period가 **정확히 9562행 고정**. 깊이(일별 궤적)는 쌓이나 **신규 페어 유입 0** = 유니버스 포화(co-mention 입력 04-25~07-08 단절)의 발현. 해자는 "깊어지되 넓어지지 않음". → `Q19-WIDTH-STAGNATION` 신규 등재, `Q19-DISCOVERY-REACT` 연계.

---

## ⓑ CORPUS-SUNMON-EMPTYKW — 근원 = 추출↔수집 타이밍 레이스 (일요일 공백 오진)

역추적 경로: TNV 0 ← `DailyNewsKeyword.keywords=[]` ← `keyword_extractor` "No news found" ← NewsArticle 창내 0건 **(추출 시점 기준)**.

### 결정적 반증 — 일요일엔 뉴스가 있다

| 날짜 | NewsArticle(KST창) | DailyNewsKeyword | 추출 발화(UTC) | 실제 수집 created_at(UTC) |
|---|---|---|---|---|
| 08-08(Sat) | 1404 | ✅ completed news=100 | 08-07 20:45 | (창 내 조기 수집분 포착) |
| **08-09(Sun)** | **1229** (marketaux) | ❌ failed news=0 | **08-08 20:45** | **08-10 01:01** (30초 버스트) |
| **08-10(Mon)** | 0 (아직) | ❌ failed news=0 | 08-09 20:45 | 미수집(월 06:00 ET 이후 예정) |

일요일(08-09) NewsArticle이 **1229건 존재**하는데도 DailyNewsKeyword 08-09는 "No news found"(news_count=0) → **추출이 수집보다 ~28h 먼저 발화**했기 때문.

### 메커니즘

1. `extract-daily-news-keywords` = **매일 16:45 ET**(`45 16 * * *`), `target_date = timezone.localdate()` **KST**(발화 시각이 KST로는 익일 새벽 → 당일 창 ~5.7h만 경과).
2. `collect-*` 수집 beat 대부분 **`* * 1-5`(평일 전용)** → last_run 전부 08-07(Fri)에서 멈춤. **주말 창은 `collect-av-broad-news`(01:00 UTC 일 1회)·`mp_fetch_news_hourly`로만 늦게** 채워짐.
3. → 08-09 추출(08-08 20:45 UTC)이 08-09 기사 수집(08-10 01:01 UTC, av-broad)보다 이르게 발화 → 창 내 0건 → `status=failed`.
4. **failed 행 재추출 없음** — `keyword_extractor`는 `status=='completed'`만 skip. failed 날짜를 늦게 도착한 기사로 재처리하는 트리거가 **부재** → corpus 영구 공백 고착.

### 원인 후보 (우선순위 — 조치는 다음 사이클)

- **A (주원인)**: failed `DailyNewsKeyword` **재추출/백필 트리거 부재**. 늦게 도착한 기사를 반영 못 해 공백이 고착. (가장 확실·표적 명확)
- **B**: `collect-*` 평일 전용(`1-5`) → 주말 수집을 av-broad(일 1회) 단일 경로에 의존, 추출 시점과 어긋남.
- **C**: `target_date = localdate()` KST가 창을 ~5.7h만 열어 조기 발화 취약성 가중.

---

## 다음 결정 사이클 회부 (이 세션 조치 없음)

1. **SUNMON**: failed 행 재추출 트리거(예: av-broad 수집 후 당일+전일 재추출) 또는 추출 스케줄을 수집 뒤로 이동 — 설계 결정 필요(후보 A/B/C).
2. **해자 폭**: `Q19-WIDTH-STAGNATION` / `Q19-DISCOVERY-REACT`(유니버스 확장·신규 소스)로 9562 고정 타파 — 별도 트랙.

## 부기 — 디렉터 가설 정정
해자 저장 경로 = **PostgreSQL 스냅샷 테이블**(`chainsight_relation_pair_snapshot`), **Neo4j 비의존**. "적립이 Neo4j에 물려 침묵" 가설은 기각(적립은 정상, Neo4j-down과 무관). cf. `D-CS-P1A-RELANDING`(관계 파이프라인 Neo4j 제거).
