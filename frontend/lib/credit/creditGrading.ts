// 백엔드 credit_signals grading 규칙의 프론트 미러 — 밴드 문구를 규칙에서 "도출"(손글씨 카피 아님).
//
// 값 출처(read-only): apps/credit_signals/constants.py (Z_YELLOW / Z_ORANGE / HY_OAS_CRISIS_BP)
//                    + services/signal_service.py grade_from_z (분기 구조).
// 백엔드 무변경. 백엔드 상수 변경 시 여기만 동기화하면 모든 밴드 문구가 자동 재도출된다.
//
// grade_from_z 실규칙(그대로 반영):
//   z is None            → gray  (콜드스타트, MIN_OBSERVATIONS=60 미만)
//   z <  Z_YELLOW        → gray  (⚠ signed z — 음수 하방은 미발화, |z| 아님)
//   Z_YELLOW ≤ z < Z_ORANGE → yellow
//   z ≥ Z_ORANGE         → orange (⚠ 상한 없음)
//   orange & signalKey==HY_OAS & value ≥ HY_OAS_CRISIS_BP/100(%) → red (⚠ HY 한정 · 절대 레벨)

export const CREDIT_GRADING = {
  Z_YELLOW: 1.0, // constants.py:Z_YELLOW — 1≤z<2 → yellow
  Z_ORANGE: 2.0, // constants.py:Z_ORANGE — z≥2 → orange
  HY_CRISIS_BP: 800, // constants.py:HY_OAS_CRISIS_BP — red 절대 임계(bp)
  RED_SIGNAL: 'HY_OAS', // grade_from_z — red 승격은 HY_OAS 한정
} as const;

/**
 * 신호별 밴드 문구를 grade_from_z 분기에서 도출.
 * signed z 하방 미발화 · orange 무상한 · red 절대 레벨(HY 한정)이 그대로 드러난다.
 */
export function bandCaption(signalKey: string): string {
  const { Z_YELLOW, Z_ORANGE, HY_CRISIS_BP, RED_SIGNAL } = CREDIT_GRADING;
  const y = String(Z_YELLOW); // "1"
  const o = String(Z_ORANGE); // "2"
  // gray는 signed z<Z_YELLOW (음수 포함) — |z| 아님을 명시. orange는 상한 없음.
  const base = `gray z<${y}(음수 포함) · yellow ${y}≤z<${o} · orange z≥${o}`;
  if (signalKey === RED_SIGNAL) {
    const pct = (HY_CRISIS_BP / 100).toFixed(1);
    return `${base} · red z≥${o} & 값≥${pct}%(${HY_CRISIS_BP}bp)`;
  }
  return base; // 비-HY 신호: red 미발화(HY 한정)
}
