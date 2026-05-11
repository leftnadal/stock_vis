'use client'

import type { APIStatus } from '@/lib/api/marketPulseV2'

const COPY: Record<APIStatus, { label: string; tone: string }> = {
  OK: { label: '정상', tone: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  INSUFFICIENT_DATA: {
    label: '데이터 수집 부족',
    tone: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  STALE: { label: '데이터 오래됨', tone: 'bg-amber-50 text-amber-700 border-amber-200' },
  FAILED: { label: '계산 실패', tone: 'bg-rose-50 text-rose-700 border-rose-200' },
  MARKET_CLOSED: {
    label: '장 마감',
    tone: 'bg-slate-50 text-slate-600 border-slate-200',
  },
}

export function StatusBanner({ status, reason }: { status: APIStatus; reason?: string }) {
  if (status === 'OK') return null
  const { label, tone } = COPY[status] ?? COPY.OK
  return (
    <div className={`mb-3 rounded-md border px-3 py-2 text-sm ${tone}`} role="status">
      <strong className="mr-2">{label}</strong>
      {reason ? <span className="opacity-80">{reason}</span> : null}
    </div>
  )
}
