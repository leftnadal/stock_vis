// 가격 구간 사다리 (TIMING-P2 §5) — zone_display(BE 완결) 소비, FE는 그리기만.
// ZoneChip(칩) · MiniPriceLadder(카드 수평) · PriceLadder(상세 수직).
import type { PriceZone, ZoneDisplay } from '@/types/monitor'

import { ZONE_LADDER_ORDER, ZONE_TONE, priceVsEntryPct } from '@/lib/monitor/zone'

// ── zone 칩: 라벨 + 진입가 대비 % ──
export function ZoneChip({ zoneDisplay }: { zoneDisplay: ZoneDisplay }) {
  const z = zoneDisplay.zone
  if (!z || !zoneDisplay.label) return null
  const pct = priceVsEntryPct(zoneDisplay)
  return (
    <span
      data-testid="zone-chip"
      data-zone={z}
      className={`inline-flex flex-shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${ZONE_TONE[z].chip}`}
    >
      {zoneDisplay.label}
      {pct != null && (
        <span className="opacity-70">
          {pct >= 0 ? '+' : ''}
          {pct.toFixed(1)}%
        </span>
      )}
    </span>
  )
}

// close(현재가)를 [stop, target] 스케일의 0~1 위치로. 밖이면 클램프.
function markerFraction(zd: ZoneDisplay): number | null {
  const { close, boundaries } = zd
  if (close == null || !boundaries) return null
  const lo = boundaries.stop
  const hi = boundaries.target
  if (hi <= lo) return null
  return Math.max(0, Math.min(1, (close - lo) / (hi - lo)))
}

// ── 카드 수평 미니 사다리: 5구간 밴드 + 현재가 마커 + 3틱(손절/진입/목표) ──
export function MiniPriceLadder({ zoneDisplay }: { zoneDisplay: ZoneDisplay }) {
  const active = zoneDisplay.zone
  if (!active) return null
  const frac = markerFraction(zoneDisplay)
  return (
    <div className="mt-2" data-testid="mini-price-ladder">
      <div className="relative flex h-1.5 overflow-hidden rounded-full">
        {ZONE_LADDER_ORDER.map((z: PriceZone) => (
          <span
            key={z}
            className={`flex-1 ${ZONE_TONE[z].bar} ${z === active ? '' : 'opacity-40'}`}
          />
        ))}
        {frac != null && (
          <span
            data-testid="mini-ladder-marker"
            className={`absolute top-1/2 h-2.5 w-0.5 -translate-y-1/2 rounded ${ZONE_TONE[active].marker}`}
            style={{ left: `${frac * 100}%` }}
          />
        )}
      </div>
      <div className="mt-0.5 flex justify-between text-[9px] text-gray-400">
        <span>손절 {zoneDisplay.boundaries.stop}</span>
        <span>진입 {zoneDisplay.boundaries.entry}</span>
        <span>목표 {zoneDisplay.boundaries.target}</span>
      </div>
    </div>
  )
}

// ── 상세 수직 사다리: 5구간(위=과열, 아래=이탈) + 경계값 + 현재가 마커 + 범례 ──
const VERTICAL_ORDER: PriceZone[] = [...ZONE_LADDER_ORDER].reverse() // 과열 top → 이탈 bottom

export function PriceLadder({ zoneDisplay }: { zoneDisplay: ZoneDisplay }) {
  const active = zoneDisplay.zone
  if (!active) return null
  const { boundaries, close, label } = zoneDisplay
  // 경계값을 위→아래로: target / approach_ceiling / entry / stop
  const boundaryRows: { value: number; label: string }[] = [
    { value: boundaries.target, label: '목표' },
    { value: boundaries.approach_ceiling, label: '접근 상한' },
    { value: boundaries.entry, label: '진입' },
    { value: boundaries.stop, label: '손절' },
  ]
  return (
    <div data-testid="price-ladder">
      <div className="flex gap-3">
        {/* 밴드 스택 */}
        <div className="flex w-24 flex-col overflow-hidden rounded-lg">
          {VERTICAL_ORDER.map((z) => (
            <div
              key={z}
              data-testid={`ladder-band-${z}`}
              className={`flex h-9 items-center justify-center text-[11px] font-medium ${ZONE_TONE[z].bar} ${
                z === active ? 'ring-2 ring-inset ring-gray-800/40 dark:ring-white/40' : 'opacity-50'
              }`}
            >
              {z === active && (close != null ? `${label} · ${close}` : label)}
            </div>
          ))}
        </div>
        {/* 경계값 눈금 */}
        <div className="flex flex-1 flex-col justify-between py-1 text-xs text-gray-500 dark:text-gray-400">
          {boundaryRows.map((b) => (
            <div key={b.label} className="flex items-center gap-2">
              <span className="h-px w-4 bg-gray-300 dark:bg-gray-600" />
              <span className="font-medium text-gray-600 dark:text-gray-300">{b.value}</span>
              <span className="text-gray-400">{b.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
