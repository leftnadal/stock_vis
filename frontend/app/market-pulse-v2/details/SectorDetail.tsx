'use client'

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { SectorDetail as Detail } from '@/lib/api/marketPulseV2'

export function SectorDetail({ payload }: { payload: Detail }) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">섹터 상세 데이터가 아직 준비되지 않았습니다.</p>
  }

  const data = (payload.sectors ?? []).map((s) => ({
    symbol: s.symbol,
    rel_strength: s.rel_strength,
    momentum_5d: s.momentum_5d,
    rank: s.rank,
  }))

  return (
    <div className="grid gap-4">
      <header className="text-xs text-slate-500">
        date {payload.date} · dispersion {(payload.cross_dispersion ?? 0).toFixed(3)} ·
        rotation {(payload.rotation_index ?? 0).toFixed(3)}
      </header>

      <div>
        <p className="text-xs text-slate-500 mb-1">상대 강도 (sector return − SPY return)</p>
        <div style={{ width: '100%', height: 240 }}>
          <ResponsiveContainer>
            <BarChart data={data} layout="vertical" margin={{ left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgb(226 232 240)" />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis dataKey="symbol" type="category" tick={{ fontSize: 10 }} width={50} />
              <Tooltip
                formatter={(v: number) => [`${v >= 0 ? '+' : ''}${v.toFixed(2)}%`, 'rel_strength']}
              />
              <Bar dataKey="rel_strength">
                {data.map((entry) => (
                  <Cell
                    key={entry.symbol}
                    fill={entry.rel_strength >= 0 ? 'rgb(16 185 129)' : 'rgb(244 63 94)'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <p className="text-xs text-slate-500 mb-1">5일 모멘텀</p>
        <div style={{ width: '100%', height: 200 }}>
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgb(226 232 240)" />
              <XAxis dataKey="symbol" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                formatter={(v: number) => [`${v >= 0 ? '+' : ''}${v.toFixed(2)}%`, 'momentum_5d']}
              />
              <Bar dataKey="momentum_5d">
                {data.map((entry) => (
                  <Cell
                    key={entry.symbol}
                    fill={entry.momentum_5d >= 0 ? 'rgb(16 185 129)' : 'rgb(244 63 94)'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
