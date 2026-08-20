# DSS(재무 지지 점수) 구현 보고 (DSS-IMPL-1)

- 실측 시점(machine clock): 2026-08-16 · 데이터 기준일: EstimateSnapshot 6회차(최신 08-14)
- base origin/main `94a5c260` · 브랜치 `monorepo/sess-dss-impl1`
- 결정: D-DSS-AGG(1-B)·D-DSS-SIGNAL(2-A)·D-DSS-LAGPARAM(3-A)·D-DSS-FY-MATCH·D-DSS-ANALYST-FILTER

## 구현 요약 (Slice 1~4)

| Slice | 산출 | 회귀/검증 |
|-------|------|-----------|
| 1 | `eps_diff_at(…, lag_days=None)` 파라미터화(기본 56/63 보존) | C8 **68 pass**(66+2)·compute_c8_from_db SHA256 `f1245b5e…` **IDENTICAL** |
| 2 | `SymbolDemandSignal` + 마이그 0032(additive) | dry-run 신규 테이블 1개만·테이블 diff +1 |
| 3 | `demand_signal` 서비스(classify·compute_anchor·aggregate_breadth·store_for_anchor) | 08-14 적재: SymbolDemandSignal 502·ThemeDemandScore 11 |
| 4 | `dss_backfill.py` 백필(07-24·07-31·08-07) + 검산 + Δ분포 | 전 anchor 검산 **✅ PASS** |

## 적재 결과 (append-only, 무-UPDATE/DELETE)

| anchor(금) | prev | n | up | down | flat | excluded | exclude 사유 | ThemeDemandScore |
|------|------|---|----|----|----|----|------|------|
| 2026-07-24 | 07-17 | 498 | 235 | 172 | 72 | 19 | analyst_delta 19 | 11 |
| 2026-07-31 | 07-24 | 498 | 214 | 124 | 149 | 11 | analyst_delta 11 | 11 |
| 2026-08-07 | 07-31 | 501 | 217 | 124 | 141 | 19 | missing_prev 3·analyst_delta 16 | 11 |
| 2026-08-14 | 08-07 | 502 | 1 | 1 | 498 | 2 | missing_prev 2 | 11 |

- 총 SymbolDemandSignal **1,999행** / ThemeDemandScore **44행**(11섹터×4 anchor). fy=차기 2027 고정 조인.

## 검산 (date-scoped invariant, 정적 행수 게이트 미사용)

전 anchor **✅ PASS**: 각 anchor `up+down+flat+excluded = 매칭 시도 수`, 전 섹터 `breadth ∈ [−1,+1]`, 유효분모 > 0(not_computed 없음), HONA 이른 anchor(07-24·07-31·08-07) 행 부재·08-14만 1행(missing_prev, no_data 해소분).

## Δ분포 — |Δeps/eps_prev| (excluded=false, ε 사후 판정 재료)

- 표본 = **1,948**(4 anchor 유효분모 합) · **0(불변) 비율 = 44.1%**(860/1,948).
- **p50 = 0.00018 · p75 = 0.00323 · p90 = 0.01386 · p99 = 0.08366**.
- ⚠️ 0비율은 08-14 anchor에 크게 편향(아래 특기). 08-14 제외 시 실질 불변 비율은 훨씬 낮음.

## 특기 사항 (설계·데이터)

1. **08-14 near-flat 이상 관측**(코드 아님·데이터 특성): 08-07↔08-14 FY2027 eps_avg **498/500 동일**(직전 07-31↔08-07은 141/498만 동일). 08-14 스냅샷은 별개 수집(created_at 08-14 20:30 UTC)이나 FMP 컨센서스가 거의 무변동 → 08-14 breadth 전 섹터 ≈0(neutral). **원인(FMP 주간 컨센서스 갱신 지연 vs 실제 조용한 개정 주간)은 미판정 — 디렉터/후속 관찰**. Δ분포 0비율 44.1%의 주동인.
2. **유니버스 504 vs 503(+1) = EA**(Electronic Arts, `is_active=False`, 08-14 유니버스 제외·이전 5회차 잔존분). EA는 sector_constituents(is_active=True)에서 빠져 섹터 breadth 미집계(무해).
3. **ε 임계 이연(D-DSS-SIGNAL 2-A)**: 초판 = 부호만. 크기 임계 도입 시 p90(1.4%)~p99(8.4%) 구간이 후보 재료. `direction=0`(불변)이 flat 카운트에 크게 기여(특히 08-14).
4. **BREADTH_TAU=0.10 초판**(D-DSS-AGG): supported/detached 경계. 4 anchor 실측 분포 관측 후 사후 조정 대상.
5. **회귀 안전**: C8 경로 IDENTICAL(SHA256 불변·68 pass). DSS는 additive 신규 테이블·append-only INSERT만 — 기존 파이프라인 무접촉.
