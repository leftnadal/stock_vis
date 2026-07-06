/**
 * MP2-TREND S2 — 궤적 오버레이 순수 helper (breadth·sector 공용).
 *
 * D-TREND-TOOLTIP: 리드아웃 표기용. D-TREND-BASELINE: 기준선 = A/D선 MA20(2호 몫).
 * FE 판단 파생 금지 — 유일 허용 예외 = 리드아웃 "기준선 대비 ±x.x%"(서빙된 두 per-date 값의 단순 차 표시).
 * 전환일 파생은 BE(previous_regime≠regime) — FE는 표시만.
 */

export interface Vline {
  date: string
  label?: string
}

/** 전환일 목록 → 세로선 오버레이. 라벨 "국면 전환 MM-DD". 빈 배열 graceful(E4). */
export function transitionVlines(dates: string[] = []): Vline[] {
  return dates.map((d) => ({ date: d, label: `국면 전환 ${d.slice(5)}` }))
}

/**
 * 기준선 대비 백분율(단순 차 표시, FE 허용 예외). ma20 없으면 null.
 * (ad_line - ma20) / |ma20| * 100 — 판단 아님, 두 서빙값의 차 표시.
 */
export function baselineDistancePct(
  adLine: number,
  ma20: number | null | undefined,
): number | null {
  if (ma20 == null || ma20 === 0) return null
  return ((adLine - ma20) / Math.abs(ma20)) * 100
}

/** 리드아웃 부기 노트: "기준선 대비 ±x.x%[ · n일째 이탈]". streakDays는 최신일에만 부여. */
export function baselineNote(
  adLine: number,
  ma20: number | null | undefined,
  streakDays?: number,
): string | undefined {
  const pct = baselineDistancePct(adLine, ma20)
  const streakPart = streakDays && streakDays > 0 ? `${streakDays}일째 이탈` : ''
  if (pct == null) return streakPart || undefined
  const sign = pct >= 0 ? '+' : '−'
  const base = `기준선 대비 ${sign}${Math.abs(pct).toFixed(1)}%`
  return streakPart ? `${base} · ${streakPart}` : base
}

/** 이탈 시작일 = 현재 streak가 시작된 날짜(마커 폴백용 vline). streak 0이면 null. */
export function deviationStartDate(
  history: { date: string }[],
  streakDays: number,
): string | null {
  if (!streakDays || streakDays <= 0) return null
  const idx = history.length - streakDays
  return idx >= 0 ? history[idx].date : null
}
