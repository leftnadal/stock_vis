'use client'

/**
 * MP2-ANALOG Slice B — 유사 국면 카드(결정론 뷰).
 *
 * 구성: 오늘 국면 4 유효 축 z 막대 + ②C 경보 상태 + ①C 정직 팬(지평별 중앙값·밴드·가용 N·n_eff)
 *   + 이웃 리스트(날짜·거리·20d 수익률). label 슬롯(카테고리·"왜?")은 **비활성**(Slice C 연결점).
 * 순수 뷰(payload prop) — fetch는 AnalogCardContainer.
 */
import { useRegimeAnalog } from '@/hooks/useMarketPulseV2'
import type {
  AnalogFanPoint,
  AnalogNeighbor,
  RegimeAnalogPayload,
} from '@/lib/api/marketPulseV2'

const AXIS_LABEL: Record<string, string> = {
  stress: '스트레스',
  financial: '금융환경',
  return_1d_pct: '1일 수익',
  vol_20d_pct: '20일 변동성',
}
const HORIZON_LABEL: Record<number, string> = { 1: '1d', 5: '5d', 10: '10d', 20: '20d', 60: '60d' }

function pct(v: number | null): string {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}

// 오늘 4축 z 막대(0 중심, ±3 클램프).
function AxisBars({ axes }: { axes: RegimeAnalogPayload['today_axes'] }) {
  const M = 3
  return (
    <div data-testid="analog-axes" className="space-y-1">
      {axes.map((a) => {
        const z = a.z ?? 0
        const clamped = Math.max(-M, Math.min(M, z))
        const leftPct = ((clamped + M) / (2 * M)) * 100
        return (
          <div key={a.axis} className="flex items-center gap-2 text-[11px]">
            <span className="w-16 text-slate-600">{AXIS_LABEL[a.axis] ?? a.axis}</span>
            <div className="relative flex-1 h-2 bg-slate-100 rounded">
              <div className="absolute left-1/2 top-0 h-2 w-px bg-slate-300" />
              <div
                data-testid={`axis-dot-${a.axis}`}
                className={`absolute top-0 h-2 w-2 -ml-1 rounded-full ${
                  a.z == null ? 'bg-slate-300' : 'bg-slate-700'
                }`}
                style={{ left: `${leftPct}%` }}
              />
            </div>
            <span className="w-10 text-right tabular-nums text-slate-500">
              {a.z == null ? '—' : `${a.z > 0 ? '+' : ''}${a.z.toFixed(1)}`}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// ①C 정직 팬(inline SVG): 중앙값 경로 + 25–75% 밴드(√(K/n_eff) 확대 반영값 그대로).
function Fan({ fan }: { fan: AnalogFanPoint[] }) {
  const pts = fan.filter((f) => f.median != null)
  if (pts.length === 0) {
    return (
      <div data-testid="analog-fan-empty" className="text-[11px] text-slate-400 py-3 text-center">
        표본 없음 — 사후 경로 통계 보류
      </div>
    )
  }
  const W = 240
  const H = 96
  const PAD = 6
  const vals: number[] = []
  pts.forEach((f) => {
    if (f.lo != null) vals.push(f.lo)
    if (f.hi != null) vals.push(f.hi)
    if (f.median != null) vals.push(f.median)
  })
  const lo = Math.min(0, ...vals)
  const hi = Math.max(0, ...vals)
  const span = hi - lo || 1
  const n = fan.length
  const xOf = (i: number) => PAD + (i / Math.max(1, n - 1)) * (W - PAD * 2)
  const yOf = (v: number) => PAD + (H - PAD * 2) * (1 - (v - lo) / span)

  const medianPath = fan
    .map((f, i) => (f.median == null ? null : `${xOf(i).toFixed(1)},${yOf(f.median).toFixed(1)}`))
    .filter(Boolean)
    .join(' ')
  const hiPath = fan.map((f, i) => (f.hi == null ? null : [xOf(i), yOf(f.hi)])).filter(Boolean) as number[][]
  const loPath = fan.map((f, i) => (f.lo == null ? null : [xOf(i), yOf(f.lo)])).filter(Boolean) as number[][]
  const band =
    hiPath.length && loPath.length
      ? [...hiPath, ...loPath.reverse()].map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
      : ''

  return (
    <svg data-testid="analog-fan" width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      {/* 0선 */}
      <line x1={PAD} x2={W - PAD} y1={yOf(0)} y2={yOf(0)} stroke="#cbd5e1" strokeDasharray="3 2" />
      {band ? <polygon data-testid="analog-fan-band" points={band} fill="#94a3b8" fillOpacity={0.22} /> : null}
      {medianPath ? <polyline points={medianPath} fill="none" stroke="#334155" strokeWidth={1.5} /> : null}
    </svg>
  )
}

function NeighborRow({ nb }: { nb: AnalogNeighbor }) {
  return (
    <div data-testid={`analog-nb-${nb.date}`} className="flex items-center justify-between text-[11px] py-0.5">
      <span className="tabular-nums text-slate-700">{nb.date}</span>
      {/* label 슬롯(카테고리) — 비활성(Slice C가 cat_slot 채움) */}
      <span data-testid={`analog-cat-${nb.date}`} className="text-[10px] text-slate-300">
        {nb.cat_slot ?? '—'}
      </span>
      <span className="tabular-nums text-slate-500">d {nb.dist.toFixed(2)}</span>
      <span className="tabular-nums text-slate-600">{pct(nb.fwd['20'] ?? null)}</span>
    </div>
  )
}

export function AnalogCard({ payload }: { payload: RegimeAnalogPayload }) {
  if (!payload.available) {
    return (
      <div data-testid="analog-unavailable" className="text-xs text-slate-400 py-4 text-center">
        유사 국면 데이터가 아직 없습니다.
      </div>
    )
  }
  const alert = payload.alert?.on
  return (
    <section data-testid="analog-card" className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">오늘 국면</p>
        {payload.as_of ? <span className="text-[10px] text-slate-400">{payload.as_of}</span> : null}
      </div>
      <AxisBars axes={payload.today_axes} />

      {alert ? (
        <div data-testid="analog-alert" className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] text-amber-800">
          전례 희박 — 최근접 거리 {payload.alert.nearest_dist?.toFixed(2) ?? '—'} &gt; {payload.meta?.tau_alert ?? 0.8}. 사후 통계 보류.
        </div>
      ) : (
        <>
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[11px] font-semibold text-slate-500">그 후 SPY (정직 팬)</p>
              <span className="text-[10px] text-slate-400">이웃 {payload.neighbors.length}</span>
            </div>
            <Fan fan={payload.fan} />
            <div data-testid="analog-fan-legend" className="flex gap-2 mt-1 text-[10px] text-slate-400 flex-wrap">
              {payload.fan.map((f) => (
                <span key={f.horizon} className="tabular-nums">
                  {HORIZON_LABEL[f.horizon] ?? `${f.horizon}d`}: {pct(f.median)} (N{f.n}
                  {f.n_eff !== f.n ? `·neff${f.n_eff}` : ''})
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-500 mb-1">닮은 과거일</p>
            <div className="divide-y divide-slate-100">
              {payload.neighbors.map((nb) => (
                <NeighborRow key={nb.date} nb={nb} />
              ))}
            </div>
            {/* "왜?" 라벨 슬롯 — 비활성(Slice C L3 맥락 연결점) */}
            <button
              type="button"
              data-testid="analog-why-slot"
              disabled
              className="mt-2 text-[10px] text-slate-300 cursor-not-allowed"
            >
              왜? (맥락 준비 중)
            </button>
          </div>
        </>
      )}
    </section>
  )
}

export function AnalogCardContainer() {
  const { data, isLoading, isError } = useRegimeAnalog(true)
  if (isLoading) return <div data-testid="analog-loading" className="text-xs text-slate-400 py-4 text-center">불러오는 중…</div>
  if (isError) return <div data-testid="analog-error" className="text-xs text-rose-600 py-4 text-center">유사 국면을 불러오지 못했습니다.</div>
  if (!data?.data) return null
  return <AnalogCard payload={data.data} />
}
