// 가격 구간 사다리 (TIMING-P2 §5 · HOLD-P1) — zone_display(BE 완결) 소비, FE는 그리기만.
// ZoneChip(칩) · MiniPriceLadder(카드 수평) · PriceLadder(상세 수직).
// HOLD-P1: bands/ticks/rows/marker/anchor_fraction 전부 BE 단일 소스. 라벨 하드코딩 제거
//          (구 응답 폴백만 유지 — new_entry 기존 5구간 동일 재현).
import type { PriceZone, ZoneBand, ZoneDisplay, ZoneTick } from '@/types/monitor'

import { ZONE_LADDER_ORDER, ZONE_TONE, priceVsEntryPct } from '@/lib/monitor/zone'

// ── zone_display 폴백(구 응답 · 수동 목 데이터) — new_entry 기존 표시 재현 ──
function bandsOf(zd: ZoneDisplay): ZoneBand[] {
  if (zd.bands) return zd.bands
  return ZONE_LADDER_ORDER.map((z) => ({ key: z, tone: z, active: z === zd.zone }))
}
function ticksOf(zd: ZoneDisplay): ZoneTick[] {
  if (zd.ticks) return zd.ticks
  const b = zd.boundaries
  return [
    { label: '손절', value: b.stop },
    { label: '진입', value: b.entry },
    { label: '목표', value: b.target },
  ]
}
function rowsOf(zd: ZoneDisplay): ZoneTick[] {
  if (zd.rows) return zd.rows
  const b = zd.boundaries
  return [
    { label: '목표', value: b.target },
    { label: '접근 상한', value: b.approach_ceiling },
    { label: '진입', value: b.entry },
    { label: '손절', value: b.stop },
  ]
}
// 활성 밴드 톤(마커·칩 색). 없으면 zone 폴백.
function activeTone(zd: ZoneDisplay): PriceZone {
  const active = bandsOf(zd).find((x) => x.active)
  return active?.tone ?? zd.zone ?? 'waiting'
}
// 현재가 마커 위치(0~1). BE marker_fraction 우선, 없으면 [stop,target] 기하 계산.
function markerFraction(zd: ZoneDisplay): number | null {
  if (zd.marker_fraction != null) return zd.marker_fraction
  const { close, boundaries } = zd
  if (close == null || !boundaries) return null
  const lo = boundaries.stop
  const hi = boundaries.target
  if (hi <= lo) return null
  return Math.max(0, Math.min(1, (close - lo) / (hi - lo)))
}
// hold 손익 % (칩) — mode=hold면 pnl_pct, 아니면 진입가 대비 %.
function chipPct(zd: ZoneDisplay): number | null {
  if (zd.mode === 'hold' && zd.pnl_pct != null) return zd.pnl_pct
  return priceVsEntryPct(zd)
}

// ── zone 칩: 라벨 + 손익/진입가 대비 % ──
export function ZoneChip({ zoneDisplay }: { zoneDisplay: ZoneDisplay }) {
  const z = zoneDisplay.zone
  if (!z || !zoneDisplay.label) return null
  const pct = chipPct(zoneDisplay)
  const tone = activeTone(zoneDisplay)
  return (
    <span
      data-testid="zone-chip"
      data-zone={z}
      className={`inline-flex flex-shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${ZONE_TONE[tone].chip}`}
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

// ── 카드 수평 미니 사다리: 색 밴드 + 현재가 마커(+hold 매입가 금색 마커) + 3틱 ──
export function MiniPriceLadder({ zoneDisplay }: { zoneDisplay: ZoneDisplay }) {
  if (!zoneDisplay.zone) return null
  const bands = bandsOf(zoneDisplay)
  const ticks = ticksOf(zoneDisplay)
  const frac = markerFraction(zoneDisplay)
  const anchorFrac = zoneDisplay.anchor_fraction // hold 매입가 마커
  const tone = activeTone(zoneDisplay)
  return (
    <div className="mt-2" data-testid="mini-price-ladder">
      <div className="relative flex h-1.5 overflow-hidden rounded-full">
        {bands.map((b) => (
          <span
            key={b.key}
            className={`flex-1 ${ZONE_TONE[b.tone].bar} ${b.active ? '' : 'opacity-40'}`}
          />
        ))}
        {anchorFrac != null && (
          <span
            data-testid="mini-ladder-anchor"
            aria-label="매입가"
            className="absolute top-1/2 z-10 h-3 w-0.5 -translate-y-1/2 rounded bg-amber-500"
            style={{ left: `${anchorFrac * 100}%` }}
          />
        )}
        {frac != null && (
          <span
            data-testid="mini-ladder-marker"
            className={`absolute top-1/2 h-2.5 w-0.5 -translate-y-1/2 rounded ${ZONE_TONE[tone].marker}`}
            style={{ left: `${frac * 100}%` }}
          />
        )}
      </div>
      <div className="mt-0.5 flex justify-between text-[9px] text-gray-400">
        {ticks.map((t) => (
          <span key={t.label}>
            {t.label} {t.value}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── 상세 수직 사다리: 밴드 스택(위=고가측) + 경계값 + 활성 구간 + 현재가/매입가 마커 ──
export function PriceLadder({ zoneDisplay }: { zoneDisplay: ZoneDisplay }) {
  if (!zoneDisplay.zone) return null
  const { close, label } = zoneDisplay
  const bands = [...bandsOf(zoneDisplay)].reverse() // 위=고가측
  const rows = rowsOf(zoneDisplay)
  return (
    <div data-testid="price-ladder">
      <div className="flex gap-3">
        {/* 밴드 스택 */}
        <div className="flex w-24 flex-col overflow-hidden rounded-lg">
          {bands.map((b) => (
            <div
              key={b.key}
              data-testid={`ladder-band-${b.key}`}
              className={`flex h-9 items-center justify-center text-[11px] font-medium ${ZONE_TONE[b.tone].bar} ${
                b.active ? 'ring-2 ring-inset ring-gray-800/40 dark:ring-white/40' : 'opacity-50'
              }`}
            >
              {b.active && (close != null ? `${label} · ${close}` : label)}
            </div>
          ))}
        </div>
        {/* 경계값 눈금 (위→아래) */}
        <div className="flex flex-1 flex-col justify-between py-1 text-xs text-gray-500 dark:text-gray-400">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center gap-2">
              <span className="h-px w-4 bg-gray-300 dark:bg-gray-600" />
              <span className="font-medium text-gray-600 dark:text-gray-300">{r.value}</span>
              <span className="text-gray-400">{r.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
