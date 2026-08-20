'use client'

// 결정 일지 게이트 (RECON-SWAP-0813 3-B, 불변 요소) — 마감/재커밋 버튼은 1문장 일지 입력
// 전 비활성. 입력 품질 검증은 하지 않는다(최소 글자수 등 금지 — ADR §6).
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

import { useCreateDecisionJournalEntry, useDecisionJournalEntries } from '@/hooks/useMonitor'
import type { DecisionJournalKind } from '@/types/monitor'

interface DecisionJournalGateProps {
  claimId: string
  onClosed: () => void // 일지 기록 후 마감 흐름(기존 CloseModal)으로 넘긴다
  onRecommitted: () => void // 일지 기록 후 재커밋 흐름(새 Claim 작성, /monitor/new)으로 넘긴다
}

export function DecisionJournalGate({ claimId, onClosed, onRecommitted }: DecisionJournalGateProps) {
  const { data: entries } = useDecisionJournalEntries(claimId)
  const createEntry = useCreateDecisionJournalEntry()
  const [sentence, setSentence] = useState('')
  const [pendingKind, setPendingKind] = useState<DecisionJournalKind | null>(null)

  const gated = sentence.trim() === ''

  async function submit(kind: 'close' | 'recommit') {
    if (gated) return
    setPendingKind(kind)
    try {
      await createEntry.mutateAsync({ claim: claimId, kind, sentence: sentence.trim() })
      setSentence('')
      if (kind === 'close') onClosed()
      else onRecommitted()
    } finally {
      setPendingKind(null)
    }
  }

  return (
    <div
      className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"
      data-testid="decision-journal-gate"
    >
      <h3 className="mb-2 font-medium text-gray-800 dark:text-gray-100">결정 일지</h3>
      <p className="mb-2 text-xs text-gray-400">
        마감·재커밋 전 지금 판단을 한 줄로 남겨 주세요. 나중에 회고할 때 그대로 다시 인용됩니다.
      </p>
      <textarea
        value={sentence}
        onChange={(e) => setSentence(e.target.value)}
        placeholder="예: 근거 3건 중 2건 소멸 — 더 지켜볼 이유가 약해졌다"
        rows={2}
        data-testid="decision-journal-sentence"
        className="mb-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
      />
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => submit('close')}
          disabled={gated || createEntry.isPending}
          data-testid="decision-journal-close-button"
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {createEntry.isPending && pendingKind === 'close' && (
            <Loader2 size={14} className="animate-spin" />
          )}
          마감
        </button>
        <button
          type="button"
          onClick={() => submit('recommit')}
          disabled={gated || createEntry.isPending}
          data-testid="decision-journal-recommit-button"
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 disabled:opacity-40 dark:border-gray-700 dark:text-gray-200"
        >
          {createEntry.isPending && pendingKind === 'recommit' && (
            <Loader2 size={14} className="animate-spin" />
          )}
          재커밋
        </button>
      </div>

      {entries && entries.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1 text-xs text-gray-400" data-testid="decision-journal-history">
          {entries.slice(0, 3).map((e) => (
            <li key={e.id}>
              &ldquo;{e.sentence}&rdquo; · {e.kind}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
