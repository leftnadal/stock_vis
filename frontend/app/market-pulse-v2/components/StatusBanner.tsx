'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { APIStatus } from '@/lib/api/marketPulseV2'

// MP-UX-S1 Part C: 라벨은 i18n/labels.py(status.*) 단일소스로 이동. 여기서는 색(tone)만 보유.
// (이전 COPY dict가 한글 라벨을 별도 보유 → labels.py와 이중소스였던 것을 해소)
const TONE: Record<APIStatus, string> = {
  OK: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  INSUFFICIENT_DATA: 'bg-amber-50 text-amber-700 border-amber-200',
  STALE: 'bg-amber-50 text-amber-700 border-amber-200',
  FAILED: 'bg-rose-50 text-rose-700 border-rose-200',
  MARKET_CLOSED: 'bg-slate-50 text-slate-600 border-slate-200',
}

export function StatusBanner({
  status, reason, labels,
}: { status: APIStatus; reason?: string; labels?: Record<string, string> }) {
  if (status === 'OK') return null
  const tone = TONE[status] ?? TONE.OK
  const label = translate(`status.${status}`, labels, status)
  return (
    <div className={`mb-3 rounded-md border px-3 py-2 text-sm ${tone}`} role="status">
      <strong className="mr-2">{label}</strong>
      {reason ? <span className="opacity-80">{reason}</span> : null}
    </div>
  )
}
