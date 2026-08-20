'use client'

// 근거 목록 — 출처 배지(수동/규칙) + 수동형 유통기한 D-n (RECON-SWAP-0813 3-A).
import { useClaimEvidences } from '@/hooks/useMonitor'
import { evidenceKindToTone, manualExpiryDday } from '@/lib/monitor/evidence'
import { SourceBadge } from '@/components/monitor/SourceBadge'

const OPERATOR_LABEL: Record<string, string> = { gte: '≥', lte: '≤', gt: '>', lt: '<' }

export function EvidenceList({ claimId }: { claimId: string }) {
  const { data: evidences, isLoading } = useClaimEvidences(claimId)

  if (isLoading) {
    return <p className="text-xs text-gray-400">근거를 불러오는 중…</p>
  }
  if (!evidences || evidences.length === 0) {
    return (
      <p className="text-xs text-gray-400" data-testid="evidence-list-empty">
        등록된 근거가 없어요.
      </p>
    )
  }

  return (
    <ul className="flex flex-col gap-2" data-testid="evidence-list">
      {evidences.map((ev) => {
        const dday = ev.kind === 'manual' ? manualExpiryDday(ev) : null
        return (
          <li
            key={ev.id}
            data-testid="evidence-list-item"
            className="flex items-start gap-2 rounded-lg border border-gray-100 px-2.5 py-2 dark:border-gray-800"
          >
            <SourceBadge tone={evidenceKindToTone(ev.kind)} />
            <div className="min-w-0 flex-1 text-xs text-gray-700 dark:text-gray-300">
              {ev.kind === 'auto' ? (
                <span>
                  {ev.indicator ? '지표' : '(지표 삭제됨)'} {OPERATOR_LABEL[ev.operator ?? '']}{' '}
                  {ev.threshold} · 유예 {ev.grace_days}거래일
                </span>
              ) : (
                <>
                  <span>{ev.description}</span>
                  {dday != null && (
                    <span
                      data-testid="evidence-manual-dday"
                      className={`ml-1.5 rounded px-1 py-0.5 text-[10px] font-medium ${
                        dday < 0
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                          : dday <= 7
                            ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                            : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                      }`}
                    >
                      {dday < 0 ? `D+${-dday} 만료` : `D-${dday}`}
                    </span>
                  )}
                </>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
