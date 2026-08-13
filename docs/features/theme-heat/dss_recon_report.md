# TH-DSS-IMPL 설계 정찰 보고 (DSS-RECON-1)

- **실측 시점(machine clock)**: 2026-08-13 15:35 (health_check 기준)
- **데이터 기준일**: EstimateSnapshot 최신 회차 = 2026-08-07 (5회차)
- 성격: read-only 정찰 · 결정론 · DB 쓰기 0 · LLM 0 · FMP 실호출 ⑦ 한정 2회. **판정·권고·설계안 없음 — 수치·목록·코드 인용만.**
- 스크립트: `scripts/theme_heat/dss_recon_survey.py`(②④⑤⑥ 재실행 동일).

## STEP 0 — 회차 전수 (데이터 기준일 2026-08-13)

| snapshot_date | 요일 | rows | symbols | FYs |
|------|------|------|---------|-----|
| 2026-07-17 | Fri | 997 | 499 | 2026·2027 |
| 2026-07-24 | Fri | 997 | 499 | 2026·2027 |
| 2026-07-29 | **Wed** | 997 | 499 | 2026·2027 |
| 2026-07-31 | Fri | 997 | 499 | 2026·2027 |
| 2026-08-07 | Fri | 1003 | 502 | 2026·2027 |

- **5회차 확정. 6회차(08-14) 미발화**(실측 08-13 < 08-14). 총 4,991행 / 502 distinct symbol.

## ① DSS 사전 흔적 (전수)

- **TASKQUEUE.md:1132** `## TH-DSS-IMPL — DSS 점수화 구현 (등재, TH-16 2026-07-13)` — "상태: 등재(사분면 가로축). E2 quadrant.dss 채움. **전제: EstimateSnapshot 2회차(7/24 예상) 이상 축적**. 설계 초안 별도 비준." (전제 = 현재 5회차로 충족)
- **모델 기존재**: `apps/chain_sight/models/heat.py:104` `class ThemeDemandScore` — "수요 축 DSS (설계서 §6.2). 주간(금요일 기준일). **Cycle 2 선반영**." status=supported/neutral/detached/not_computed.
- **DECISIONS.md:726** "역방향은 Cycle 2 DSS의 D2(DIO 재고일수)뿐" (부호 표 맥락). **DECISIONS.md:4857** 게이트 후순위 "C4/C8 합류·DSS".
- 전용 설계 스펙 문서(docs/) **없음** — 스펙은 TASKQUEUE 항목 + EstimateSnapshot 설계서 §6.6 주석에 분산.

## ② 커버리지 (축 1: 종목 레벨 성립)

- 회차별: 499/503(**99.2%**) 4회차 → 502/503(**99.8%**) 08-07.
- 종목 관점: **코어(전 5회차 연속) = 499** / 간헐 = 3 / 합집합 = 502. 결측 패턴 = **특정 회차 집중**(간헐 3종이 07-17~07-31 전부 결측, 08-07만 존재 = 신규 편입).
- 섹터별 커버리지(08-07, 분모=유니버스 섹터 종목수): **Industrials 81/83(98%) 외 10개 섹터 100%**. **최소 분모 = Energy 21종** (섹터 breadth 분모 전부 ≥21 = 충분).
- **BRK.B / BF.B**: 둘 다 **08-07 회차에만 존재**(이전 4회차 부재 = 신규 편입 2종 + 1종).

## ③ C8 재사용 표면 (`estimate_revision.py`)

- 재사용 후보 함수:
  - `eps_diff_at(eps_by_date, anchor)` (:46) — 시그니처 `(dict{date:eps}, date)`.
  - `valid_eps_diff_dates` (:62) / `valid_eps_diff_count` (:70).
  - `compute_c8_from_db(symbols, as_of, fiscal_year=None)` (:196) — EstimateSnapshot+DailyPrice → `symbol_series` 로더.
- **lag 하드코딩**: `LAG_PRIMARY_DAYS=56` / `LAG_FALLBACK_DAYS=63` = 모듈 상수(:37-38). `eps_diff_at`는 `for lag in (56, 63)` 고정 순회(:55) — **lag 파라미터 미노출**. → **WoW(7일) 재사용 = 시그니처 파라미터화 리팩터 필요**(현행 재사용 불가).
- **fiscal_year 스코프**: 로더가 `fy = as_of.year+1` 기본, `filter(..., fiscal_year=fy)`(:211,:215) → eps_by_date는 **단일 FY 시리즈**. DSS가 로더 재사용 시 **롤오버 구조적 완화 상속**.
- **DSS 저장 테이블 기존재**: `ThemeDemandScore`(heat.py:104-137) — theme FK(HeatEntity), date(금요일 기준일), score(SmallInt·null=not_computed), status, components(JSON), `unique_together(theme,date)`, index[-date]. **신규 테이블 불요**(ThemeHeatScore와 동형 패턴).

## ④ WoW 매칭 (7일 정확)

- **7일 쌍 = 3건**: (07-17→07-24) · (07-24→07-31) · (07-31→08-07). 각 매칭 **(sym,fy) 997쌍 = distinct 499 종목**.
- **고아 07-29(수)**: ±7일 파트너 부재 확정(07-22·08-05 모두 미스냅샷) → 7일 매칭에서 **구조상 배제**.
- 검산: 3쌍 모두 매칭 distinct symbol(499) ≤ min(양 회차 종목수) ✅. ②의 회차별 존재 499와 정합.
- ※ 산정 주의: 정렬-인접이 아니라 `(d, d+7d)` 존재로 판정해야 07-29가 끼어도 07-24→07-31이 포착됨(정찰 스크립트 초판 버그 수정 반영).

## ⑤ 함정 A — 회계기간 롤오버

- **스키마**: `EstimateSnapshot.fiscal_year = SmallIntegerField`(heat.py:264) — **연도만**. 분기/기말일(period-end date) 필드 **없음**. unique=(symbol, snapshot_date, fiscal_year).
- **수집 경로**: FMP 응답 `date` = 대상기간 종료일(예 '2027-09-27', 월/일 포함). `_fiscal_year(row)`가 `str(date)[:4]`로 **연도만 추출**(estimate_service.py:38-41) → **월/일 폐기**. 저장 필드 = symbol/snapshot_date/fiscal_year/eps_avg/eps_high/eps_low/num_analysts_eps/revenue_avg(파싱 8/8, 원본 date는 fiscal_year로 축약).
- **데이터 관측**: WoW diff 표본 2,991. **fiscal_year 집합 전환 = 0건**(5회차 내 동일종목 FY집합 2026·2027 불변 — 롤오버 **미발생**, 연말/보고 시점 도래 전이라 잠재). `|diff|>직전EPS 30%` 의심 태그 = **13건**(상위: GOOGL/GOOG FY2026 +36%(07-17→24)·INCY FY2026 −40%(07-24→31)·STX FY2027 +24% — 전부 **fiscal_year 불변** = 어닝시즌 개정 정황, 판정 없이 목록만). |diff| 상위 20 = 보고서 스크립트 출력 참조.

## ⑥ 함정 B — 컨센서스 구성 변화

- **스키마**: `num_analysts_eps = IntegerField`(heat.py:268, "C8 신뢰 가중") — **존재**. 수집: FMP `numAnalystsEps` → 저장(estimate_service.py:80).
- **데이터 관측**(WoW 표본 2,991): **unchanged 70.6% / ±1 22.0% / ±2+ 7.3% / null 0.1%** → 인접 회차 간 애널리스트 수 변동 **약 29%**(구성 변화 빈번, 필드 존재로 필터링 가능).

## ⑦ 함정 C — 발표 일정 데이터 가용성

- **코드 흔적 0**: earnings calendar 수집·저장 grep 무결과. FMP client에 earnings calendar 메서드 **부재**(`get_ipos_calendar`만 존재, `get_analyst_estimates` 별개).
- **FMP 실호출 확인**(2회, DB 미저장): `GET /stable/earnings-calendar?from=2026-08-13&to=2026-08-20` → **HTTP 200**, list len=1421. 필드 = `[date, symbol, epsActual, epsEstimated, revenueActual, revenueEstimated, lastUpdated]`. 무파라미터 호출 → 200, len=4000. **Starter 플랜 접근 가능**(미배선 상태).

## 특기 사항 (설계를 좌우할 발견 — 사실 나열)

1. **fiscal_year만 저장, 분기/기말일 폐기**(estimate_service.py:40 `[:4]`) — 롤오버는 연도 단위만 감지 가능. 데이터엔 아직 **0건**(5회차 내 미발생, 잠재).
2. **num_analysts_eps 존재** → 구성 변화(≈29% WoW 변동) 필터 가능.
3. **C8 lag 56/63 하드코딩**(파라미터 미노출) → DSS WoW(7일) 재사용은 시그니처 리팩터 필요.
4. **ThemeDemandScore 테이블 기존재**(Cycle 2 선반영) → DSS 저장 신규 테이블·마이그레이션 불요.
5. **earnings calendar FMP 200 접근 가능**(코드 미배선) → 발표 일정 필터 재료 확보 가능.
6. **커버리지 견고**: 99.2%+ · 섹터 10/11 100%(Industrials 98%) · 최소 분모 Energy 21 · 고아 07-29(수) 1건.
