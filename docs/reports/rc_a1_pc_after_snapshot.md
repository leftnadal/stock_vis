# RC-A-1 PART 3 — 배포 후 after-snapshot (⑦, read-only)

- 측정: 2026-08-31, read-only · DB write 0
- 배포 정본: `c8dfc627`(병렬 세션, 08-31 11:52) — ②~⑥ 완주
- before 기준: `docs/reports/rc_a1_pc_before_snapshot.md`(08-27, 배포 전·구 스케일)
- 실행 트리: `sv-worker-runtime`(origin/main `8cfbcabb`, 배포 코드)

## 요약 판정 — 전 항목 기대치 부합 ✅
| # | 항목 | 결과 | 기대 |
|---|------|------|------|
| 1 | PRICE_CORRELATED | **0** | 0 ✅ |
| 2 | 총행 정합 | 17,410−3,784=**13,626**=현재 (유입 +0) | 정합 ✅ |
| 3 | score_version / [0,1] 이탈 | 전건 "3.0" / 이탈 **0** | ✅ |
| 4 | market_max 소멸(PC 유일쌍) | market-edge 쌍 6,786→**3,869**(−2,917) · 표본 5쌍 market edge=0 | ✅ |
| 5 | strip θ | **0.85** | 0.60→0.85 ✅ |
| 6 | Neo4j PC 엣지 | **0** | 0 ✅ |
| 7 | 감쇠 게이트 보호 | PEER_OF confirmed **1,790** 보호 · 실 감쇠후보 0 | ✅ |

## [1] 총행 + PRICE_CORRELATED
- 총 RC: **13,626** · PRICE_CORRELATED: **0**(처분 완료)

## [2] 총행 정합
- 배포직전 **17,410** − PC **3,784** = **13,626** = 현재. 배포 후 유입 **+0**.
- relation_type 분포: PEER_OF 9,365 · CO_MENTIONED 3,869 · COMPETES_WITH 150 · PARTNER_WITH 94 · SUPPLIES_TO 90 · DEPENDS_ON 56 · PEER 2

## [3] score_version + 눈금
- version "3.0": **13,626 전건** · [0,1] 밖 값: **0**
- truth max/min = 0.85 / 0.0 · market max/min = 0.85 / 0.35
- ("PEER" 2행 outlier 0.5/0.6는 [0,1] 내라 무이탈 — 설계대로 보존)

## [4] market_max 이동 (PC 유일-market 쌍 소멸)
- market-edge 보유 쌍: before **6,786** → after **3,869** (−2,917)
- 예상(6,786 − PC유일 3,005 = 3,781) + co-mention 유입분 ≈ 3,869 (정합)
- PC-유일 표본 5쌍 — 현재 market edge=0 (market_max 소멸 확인):
  - INCY↔WAT · INCY↔RVTY · DHR↔LH · GL↔PFG · FIS↔IT → 각 market edge **0** (전체 RC edge 1 = PEER_OF만 잔존)

## [5] strip_service θ (percentile_cont 0.85 of truth_score)
- **θ = 0.85** (before 60.0[구 [0,100] 스케일] → 마이그 0.6 → PC 처분 후 0.85[신 스케일])
- PC의 truth=0 3,784행이 θ 분모에서 제거되어 상향 = 배지 폭 복귀(c8dfc627: 2,282행 배지 복귀)

## [6] Neo4j PC 엣지 + 미러 필터 규칙
- Neo4j PRICE_CORRELATED 엣지: **0** (배포 ⑥ Cypher 정리 완료)
- **격차 원인 1줄** (`apps/chain_sight/services/neo4j_sync.py:35-38`):
  ```python
  if rc.relation_status in ("confirmed", "probable"):        # → upsert
  elif rc.relation_category == "market" and rc.relation_status == "weak":  # → upsert
  else:                                                       # hidden/weak(truth)/stale → delete
  ```
  → PC의 대다수(hidden 3,518)는 미러 안 됨 → PG 3,784 ≫ Neo4j 1,356 격차의 구조적 원인.

## [7] 감쇠 리허설 (09-18+ beat 예측)
- **게이트 보호대상 = PEER_OF confirmed 1,790** (last_observed 06-20 동결 → 09-18+ >90d).
  옛 ungated 감쇠라면 이들이 일괄 confirmed→stale 오발(A-0 폭탄 2,054 중 PC 264 처분 후 잔여 1,790).
  `DECAYABLE_RELATION_TYPES` 게이트가 PEER_OF 제외 → **보호**.
- 실제 09-18+ 감쇠 후보(DECAYABLE·>90d): **0** (CO_MENTIONED·SEC계는 재확인으로 신선 유지).
- **예측: 09-19(또는 차기 일요일) 감쇠 beat = `Stale decay: 0건 하향 전이`** — DECAYABLE 외 무접촉.
- 현재 stale 행: 0 (배포 시 PC stale 2행 함께 처분).
- ⚠ 측정 주의: PEER_OF last_observed 06-20 15:00:01 UTC = KST 06-21 → `__date` 룩업 TZ 변환에 유의(UTC datetime cutoff 사용).

## 결론
RC-A-1 배포(눈금 [0,1]·PC 처분·감쇠 게이트)는 **PG·Neo4j·strip·감쇠 전 축에서 정합 확인**. 폭탄(09-18+ 1,790행 오발)은 게이트로 해제됨. 잔여 = RC-NEO4J-WORKER-TREE(병진·별도 트랙).
