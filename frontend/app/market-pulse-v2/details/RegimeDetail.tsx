'use client'

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

import type { RegimeDetail as Detail } from '@/lib/api/marketPulseV2'

const KEY_LABELS: Record<string, string> = {
  return_1d_pct: '1d 수익률',
  vol_20d_pct: '20d 변동성',
  drawdown_pct: '52w drawdown',
  nfci: 'NFCI',
  nfci_credit: 'NFCI Credit',
  nfci_leverage: 'NFCI Leverage',
  nfci_risk: 'NFCI Risk',
  hy_oas_pct: 'HY OAS',
  hy_ccc_oas_pct: 'HY CCC OAS',
  t10y2y_pct: 'T10Y2Y',
  t10y3m_pct: 'T10Y3M',
  vix: 'VIX',
  vix3m: 'VIX 3M',
  move: 'MOVE',
}

function normalize(key: string, value: number | null | undefined): number {
  if (value === null || value === undefined) return 0
  // 시각화 단순화: VIX/MOVE는 50으로 max, NFCI는 |1| 기준 50, HY OAS는 8% max 등
  switch (key) {
    case 'vix':
    case 'vix3m':
      return Math.min(100, Math.max(0, (value / 50) * 100))
    case 'move':
      return Math.min(100, Math.max(0, (value / 200) * 100))
    case 'hy_oas_pct':
    case 'hy_ccc_oas_pct':
      return Math.min(100, Math.max(0, (value / 12) * 100))
    case 'nfci':
    case 'nfci_credit':
    case 'nfci_leverage':
    case 'nfci_risk':
      return Math.min(100, Math.max(0, ((value + 1) / 2) * 100))
    case 't10y2y_pct':
    case 't10y3m_pct':
      return Math.min(100, Math.max(0, ((value + 1) / 4) * 100))
    case 'drawdown_pct':
      return Math.min(100, Math.max(0, (Math.abs(value) / 30) * 100))
    case 'return_1d_pct':
    case 'vol_20d_pct':
      return Math.min(100, Math.max(0, (Math.abs(value) / 5) * 100))
    default:
      return 0
  }
}

export function RegimeDetail({ payload }: { payload: Detail }) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">레짐 상세 데이터가 아직 준비되지 않았습니다.</p>
  }

  const inputs = payload.inputs ?? {}
  const radarData = Object.entries(KEY_LABELS).map(([key, label]) => ({
    key: label,
    value: normalize(key, inputs[key]),
    raw: inputs[key],
  }))

  return (
    <div className="grid gap-4">
      <header>
        <p className="text-base font-semibold text-slate-900">{payload.regime}</p>
        <p className="text-xs text-slate-500">
          coverage {((payload.coverage ?? 0) * 100).toFixed(0)}% · streak {payload.hysteresis_streak ?? 0}
          {payload.is_finalized ? ' · finalized' : ''}
        </p>
        {payload.headline ? <p className="text-sm text-slate-700 mt-1">{payload.headline}</p> : null}
      </header>

      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="key" tick={{ fontSize: 10 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} />
            <Radar
              dataKey="value"
              fillOpacity={0.4}
              stroke="rgb(99 102 241)"
              fill="rgb(99 102 241)"
            />
            <Tooltip
              formatter={(value: number, _name: string, props: { payload?: { raw?: number | null } }) => {
                const raw = props.payload?.raw
                return [raw === null || raw === undefined ? '—' : Number(raw).toFixed(3), '값']
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {payload.fired_rules && payload.fired_rules.length > 0 ? (
        <div className="text-xs">
          <p className="text-slate-500 mb-1">발동 룰</p>
          <ul className="grid gap-0.5">
            {payload.fired_rules.map((r) => (
              <li key={r} className="font-mono text-slate-700">{r}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
