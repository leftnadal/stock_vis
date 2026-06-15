'use client'

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { translate } from '@/lib/i18n/marketPulse'
import type { BreadthDetail as Detail } from '@/lib/api/marketPulseV2'

export function BreadthDetail({ payload, labels }: { payload: Detail; labels?: Record<string, string> }) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">시장 폭 상세 데이터가 아직 준비되지 않았습니다.</p>
  }

  const data = (payload.history_30d ?? []).map((p) => ({
    date: p.date.slice(5),
    advance: p.advance,
    decline: -p.decline,
    ad_line: p.ad_line,
  }))

  return (
    <div className="grid gap-4">
      <header className="grid grid-cols-3 gap-2 text-center">
        <Cell label="상승" value={payload.advance ?? 0} tone="text-emerald-600" />
        <Cell label="하락" value={payload.decline ?? 0} tone="text-rose-600" />
        <Cell
          label={translate('metric.ad_line', labels, 'AD-line')}
          value={payload.ad_line ?? 0}
          sub={(payload.ad_line_change ?? 0) >= 0 ? `+${payload.ad_line_change}` : `${payload.ad_line_change}`}
        />
      </header>

      <div>
        <p className="text-xs text-slate-500 mb-1">{translate('metric.ad_line', labels, 'AD-line')} 30일 추이</p>
        <div style={{ width: '100%', height: 200 }}>
          <ResponsiveContainer>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgb(226 232 240)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="ad_line" stroke="rgb(99 102 241)" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <p className="text-xs text-slate-500 mb-1">신고가 / 신저가 (52주)</p>
        <div className="grid grid-cols-2 gap-2 text-center">
          <Cell label="52w 신고가" value={payload.new_high_52w ?? 0} tone="text-emerald-500" />
          <Cell label="52w 신저가" value={payload.new_low_52w ?? 0} tone="text-rose-500" />
        </div>
      </div>
    </div>
  )
}

function Cell({ label, value, sub, tone }: { label: string; value: number; sub?: string; tone?: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-semibold ${tone ?? 'text-slate-900'}`}>
        {value.toLocaleString()}
        {sub ? <span className="ml-1 text-xs text-slate-500">{sub}</span> : null}
      </p>
    </div>
  )
}
