'use client'

import type { BriefCard } from '@/lib/api/marketPulseV2'
import { CardShell } from './CardShell'

export function BriefCardSummary({ data, onOpen }: { data: BriefCard | null; onOpen?: () => void }) {
  return (
    <CardShell titleEn="Briefing" titleKo="브리핑" status={data?.status} onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">브리핑 미생성</p>
      ) : (
        <div>
          {data.headline ? <p className="text-sm font-medium text-slate-900 mb-1">{data.headline}</p> : null}
          {data.content_preview ? <p className="text-xs text-slate-600 line-clamp-3">{data.content_preview}</p> : null}
          <p className="text-[10px] text-slate-400 mt-2">{data.model_version}</p>
        </div>
      )}
    </CardShell>
  )
}
