/**
 * C-lite (1.6-S0) — 히어로 스트레스 상태 배지 (가산 소품).
 *
 * 소속: market-pulse-v2/cards. 홈 히어로(RegimeCardSummary) 국면 라벨 옆에 스트레스 축
 *   state를 필 배지로 재노출 — StressCard까지 스크롤하지 않아도 최상단에서 스트레스 축 인지.
 * 원칙(불변):
 *   - 판단 로직 신설 0 — 백엔드 level_band를 그대로 표시(FE 점수→상태 재판정 금지).
 *   - 색 하드코딩 0 — `stressAlert` 토큰(stressBandBadgeClass) 재사용(신규 색 상수 정의 금지,
 *     COLOR-TOKEN-UNIFY 착수 시 자동 수렴). 경보색 신규 점유 없음(D-MPS-COLOR).
 *   - 카피 최소 — 기존 `stressBandLabel`(안정/주의/심화, D-MPS-BAND-NAME "위기" 금지)에
 *     축명 "스트레스" 접두만. state당 2어.
 * 부재/스테일(available=false·band 없음)이면 이 컴포넌트를 렌더하지 않는다(히어로 오염 방지) —
 *   호출부에서 band를 넘기지 않음으로 처리.
 */
import type { StressLevelBand } from '@/lib/api/marketPulseV2'

import { stressBandBadgeClass, stressBandLabel } from '../stressAlert'

export function StressHeroBadge({ band }: { band: StressLevelBand }) {
  return (
    <span
      data-testid="stress-hero-badge"
      className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-xs font-medium ${stressBandBadgeClass(band)}`}
    >
      스트레스 {stressBandLabel(band)}
    </span>
  )
}
