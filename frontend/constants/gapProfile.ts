// 갭 체질 배지 상수 (RECON-SWAP-0813 3-A 고지 ⑵) — 종목의 유니버스 대비 갭(오버나이트 점프) 배수.
//
// ⚠️ E-1 실측 파이프라인 미보유 — 종목별 실측 산출 계산기가 아직 없어 유니버스 공통 보수적
// 기본값(1.0배 = "유니버스 평균과 동일 취급")을 쓴다. 실측이 붙으면 이 상수만 교체하면 되고
// 소비 측(컴포넌트)은 무변경이다 — 값 자체가 아니라 "출처를 밝힌 자리채움"이 핵심(E-1 하드코딩 금지).
// 출처: RECON-SWAP-0813 E-1
export const DEFAULT_GAP_MULTIPLIER = 1.0

// 종목별 override — 실측이 들어오면 여기에 { SYMBOL: multiplier } 형태로 추가한다.
// 현재는 빈 맵(전 종목이 기본값을 사용) — 하드코딩된 실측값 없음.
// 출처: RECON-SWAP-0813 E-1
export const GAP_MULTIPLIER_BY_SYMBOL: Record<string, number> = {}

export function gapMultiplierFor(symbol: string): number {
  return GAP_MULTIPLIER_BY_SYMBOL[symbol.toUpperCase()] ?? DEFAULT_GAP_MULTIPLIER
}

export type GapBadgeTone = 'low' | 'mid' | 'high'

// 배수 → 배지 톤. 임계값은 시각 구분용(판정 아님) — 0.8/1.5는 편의상 경계.
export function gapBadgeTone(multiplier: number): GapBadgeTone {
  if (multiplier <= 0.8) return 'low'
  if (multiplier < 1.5) return 'mid'
  return 'high'
}
