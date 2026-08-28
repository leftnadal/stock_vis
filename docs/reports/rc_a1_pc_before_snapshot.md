# RC-A-1 PART 3 — PRICE_CORRELATED 삭제 전 감사 스냅샷

- 측정: 2026-08-27, read-only (worktree sess-rc-a1, base origin/main d6365630 이후)
- 상태: **pre-0033 (구 스케일 [0,100]), pre-deletion**
- 목적: PC 3,784행 삭제의 사후 감사 기준값 확보. 삭제영향은 scale-independent 구조 지표로 측정.

## 총계
- 총 RC: 17,322
- PRICE_CORRELATED: 3,784 (전량 relation_category="market", serving_layer="context")

## 삭제영향 — market 쌍별 PC 기여 (scale-independent)
| 구분 | 쌍수 | 삭제 효과 |
|------|------|-----------|
| PC 유일 market edge | **3,005** | market_max 소멸(market_edge_count→0) — 해당 쌍 market 신호 제거 |
| PC가 max·co-mention 공존 | 337 | market_max가 co-mention 수준으로 하락 |
| co-mention ≥ PC | 442 | market_max 불변(삭제 무영향) |
| **합(PC 보유 쌍)** | **3,784** | |

→ 최대 효과: **3,005쌍이 현재 market 신호를 PC로만 보유** → 삭제 시 이들의 market_max/relevance_risk 소멸.
  (D2에서 PC는 "관계"가 아니라 확인된 연결의 강도속성(P1B sync_strength)으로 이동됨 — 이 market 신호는
   설계상 잉여로 간주. 최종 삭제 go/no-go 시 이 3,005쌍 영향을 감안.)

## strip_service θ (배지 임계, percentile_cont 0.85 of truth_score)
- 현재 θ = **60.0** (구 스케일 [0,100])
- PC 제외 시 θ' = **85.0** → 삭제 후 예상 **+25.0 상향**
- 원인: PC의 truth_score=0 인 3,784행이 θ 분모에 포함 → θ를 끌어내림. 삭제 시 배지 임계 상향(배지 감소).

## RPS 최신 단면 (period=2026-08-26, 12,059쌍)
- market_max 분포: 85.0→360 / 60.0→1,371 / 35.0→5,055 / 0.0→5,273
- market_edge_count>0 쌍: 6,786

## 사후 감사 지침 (after-snapshot, 병진 배포 후)
0033(scale) + PART3(삭제) 적용 후 재측정하여 이동폭 확인:
1. PRICE_CORRELATED 0행 · 총행 = 17,322(±유입) − 3,784
2. market_edge_count>0 쌍 = 6,786 − (3,005 소멸분) ≈ 3,781 부근 (유입 반영 조정)
3. strip θ 상향 이동 실측 (구60→신 스케일에서 대응값)
4. 주의: 0033이 [0,1]로 스케일 변환하므로 after는 [0,1] 단위 — 구 [0,100] 값과 직접 비교 불가.
   삭제 효과 격리는 "market_edge_count>0 쌍수"·"PC행수 0" 같은 scale-independent 지표로 판정.
