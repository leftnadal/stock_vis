// 일지 kind=open 렌더러 (MON-DETAIL-P1 T2) — 관제 개시 + claim 사전 커밋 요약.
import type { JournalEntry, OpenPayload } from '@/lib/monitor/journal'

const SCENARIO_LABEL: Record<string, string> = {
  new_entry: '신규 매수',
  hold: '보유 관리',
  add_on: '추가 매수',
}

export function OpenEntry({ entry }: { entry: JournalEntry }) {
  const p = entry.payload as OpenPayload
  // hold는 매입가 앵커, 그 외는 진입가.
  const anchorLabel = p.scenario_type === 'hold' ? '매입' : '진입'
  const anchorValue = p.scenario_type === 'hold' ? p.purchase_price : p.entry_price
  const parts: string[] = []
  if (anchorValue) parts.push(`${anchorLabel} ${anchorValue}`)
  if (p.target_price) parts.push(`목표 ${p.target_price}`)
  if (p.stop_price) parts.push(`손절 ${p.stop_price}`)
  return (
    <div data-testid="journal-open">
      <div className="flex items-center gap-1.5">
        <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[11px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
          관제 개시
        </span>
        {p.scenario_type && (
          <span className="text-[11px] text-gray-400">
            {SCENARIO_LABEL[p.scenario_type] ?? p.scenario_type}
          </span>
        )}
      </div>
      {parts.length > 0 && (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{parts.join(' · ')}</p>
      )}
    </div>
  )
}
