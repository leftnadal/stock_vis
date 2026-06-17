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

import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail as Detail } from '@/lib/api/marketPulseV2'
import { SectorSparkline } from './SectorSparkline'

export function SectorDetail({ payload, labels }: { payload: Detail; labels?: Record<string, string> }) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">섹터 상세 데이터가 아직 준비되지 않았습니다.</p>
  }

  const data = (payload.sectors ?? []).map((s) => ({
    symbol: s.symbol,
    rel_strength: s.rel_strength,
    momentum_5d: s.momentum_5d,
    rank: s.rank,
  }))

  // MP-UX-S5-B: 섹터별 rel_strength 인라인 스파크라인. BE가 준 sector_history(rank순)
  //   전부 렌더(FE 절단 0, A-1). 최신 rel_strength 수치는 sectors[]에서 심볼로 결합.
  const history = payload.sector_history ?? []
  const relBySymbol = new Map((payload.sectors ?? []).map((s) => [s.symbol, s.rel_strength]))

  return (
    <div className="grid gap-4">
      <header className="text-xs text-slate-500">
        date {payload.date} · {translate('metric.dispersion', labels, 'dispersion')}{' '}
        {(payload.cross_dispersion ?? 0).toFixed(3)} ·{' '}
        {translate('metric.rotation', labels, 'rotation')} {(payload.rotation_index ?? 0).toFixed(3)}
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

      {history.length > 0 ? (
        <div>
          <p className="text-xs text-slate-500 mb-1">섹터별 상대강도 추세 (최근 ≤30일)</p>
          <ul className="grid gap-1">
            {history.map((entry) => {
              const label = translate(`sector.${entry.symbol}`, labels, entry.symbol)
              const rel = relBySymbol.get(entry.symbol)
              return (
                <li key={entry.symbol} className="flex items-center justify-between gap-2">
                  <span className="w-20 shrink-0 text-sm text-slate-800">{label}</span>
                  <span
                    className={`w-16 shrink-0 text-right text-xs font-medium ${
                      rel == null ? 'text-slate-400' : rel >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {rel == null ? '—' : `${rel >= 0 ? '+' : ''}${rel.toFixed(2)}%`}
                  </span>
                  <span className="flex-1 text-right">
                    <SectorSparkline entry={entry} />
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}

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
