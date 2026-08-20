'use client'

// 근거 관리 모달 (RECON-SWAP-0813 3-A) — 목록 + 입력 폼 + 고지 2건(관측 불가능 근거 · 갭 체질 배지).
import { AlertCircle, X } from 'lucide-react'

import { EvidenceForm } from '@/components/monitor/evidence/EvidenceForm'
import { EvidenceList } from '@/components/monitor/evidence/EvidenceList'
import { gapBadgeTone, gapMultiplierFor } from '@/constants/gapProfile'

const GAP_TONE_CLASS: Record<string, string> = {
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  mid: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

interface EvidenceModalProps {
  claimId: string
  monitorId: string
  targetRef: string
  onClose: () => void
}

export function EvidenceModal({ claimId, monitorId, targetRef, onClose }: EvidenceModalProps) {
  const multiplier = gapMultiplierFor(targetRef)
  const tone = gapBadgeTone(multiplier)

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center"
      data-testid="evidence-modal"
    >
      <div className="flex max-h-[85vh] w-full max-w-md flex-col overflow-hidden rounded-t-2xl bg-white dark:bg-gray-900 sm:rounded-2xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-gray-100">근거 관리</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            data-testid="evidence-modal-close"
            className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {/* 고지 ⑴ — 관측 불가능한 근거 경고 (불변 요소 아님이지만 고정 문구) */}
          <div
            className="mb-3 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-900/20 dark:text-amber-300"
            data-testid="evidence-notice-unobservable"
          >
            <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
            <span>관측 불가능한 근거는 자동 감시되지 않습니다.</span>
          </div>

          {/* 고지 ⑵ — 갭 체질 배지 */}
          <div
            className="mb-4 flex items-center gap-2 text-xs text-gray-500"
            data-testid="evidence-notice-gap"
          >
            <span>갭 체질</span>
            <span
              data-testid="gap-badge"
              data-tone={tone}
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${GAP_TONE_CLASS[tone]}`}
            >
              유니버스 대비 {multiplier.toFixed(1)}배
            </span>
          </div>

          <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">등록된 근거</h3>
          <div className="mb-5">
            <EvidenceList claimId={claimId} />
          </div>

          <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">근거 추가</h3>
          <EvidenceForm claimId={claimId} monitorId={monitorId} />
        </div>
      </div>
    </div>
  )
}
