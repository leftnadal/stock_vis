'use client'

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

import type { FlowDetail as Detail } from '@/lib/api/marketPulseV2'

const COLORS = [
  'rgb(99 102 241)', 'rgb(14 165 233)', 'rgb(34 197 94)',
  'rgb(245 158 11)', 'rgb(244 63 94)', 'rgb(168 85 247)',
  'rgb(16 185 129)', 'rgb(234 88 12)', 'rgb(217 70 239)', 'rgb(59 130 246)',
]

export function FlowDetail({ payload }: { payload: Detail }) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">집중도 상세 데이터가 아직 준비되지 않았습니다.</p>
  }

  const holdings = payload.top_holdings ?? []
  const restWeight = Math.max(0, 1 - holdings.reduce((s, h) => s + h.weight, 0))
  const data = [
    ...holdings.map((h) => ({ name: h.symbol, value: h.weight })),
    { name: 'others', value: restWeight },
  ]

  return (
    <div className="grid gap-4">
      <header className="grid grid-cols-3 gap-2 text-center">
        <Metric label="top5" value={payload.top5_weight ?? 0} />
        <Metric label="top10" value={payload.top10_weight ?? 0} />
        <Metric label="HHI" value={payload.hhi ?? 0} digits={4} percent={false} />
      </header>

      <div>
        <p className="text-xs text-slate-500 mb-1">{payload.universe} 상위 10종 + 나머지</p>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90} label>
                {data.map((entry, i) => (
                  <Cell key={entry.name} fill={entry.name === 'others' ? 'rgb(203 213 225)' : COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {holdings.length > 0 ? (
        <div>
          <p className="text-xs text-slate-500 mb-1">상위 보유 종목</p>
          <ul className="text-xs text-slate-700 space-y-0.5">
            {holdings.map((h) => (
              <li key={h.symbol} className="flex justify-between border-b border-slate-100 py-0.5">
                <span className="font-mono">{h.symbol}</span>
                <span>{(h.weight * 100).toFixed(2)}%</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

function Metric({ label, value, digits = 2, percent = true }: { label: string; value: number; digits?: number; percent?: boolean }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-base font-semibold text-slate-900">
        {percent ? `${(value * 100).toFixed(digits)}%` : value.toFixed(digits)}
      </p>
    </div>
  )
}
