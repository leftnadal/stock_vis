'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, CheckCircle, XCircle, MinusCircle } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'
import { useThesis } from '@/lib/thesis/queries'
import { useCloseThesis } from '@/lib/thesis/mutations'
import { USE_MOCK, MOCK_THESES } from '@/lib/thesis/mock'
import { stateToDisplay } from '@/lib/thesis/utils'
import { OutcomeSelector, type Outcome } from '@/components/thesis/close/OutcomeSelector'
import { CloseConfirmDialog } from '@/components/thesis/close/CloseConfirmDialog'

const OUTCOME_DISPLAY: Record<string, { icon: typeof CheckCircle; label: string; className: string }> = {
  correct:   { icon: CheckCircle,  label: '적중',   className: 'text-green-400' },
  incorrect: { icon: XCircle,      label: '빗나감', className: 'text-red-400' },
  neutral:   { icon: MinusCircle,  label: '미확정', className: 'text-gray-400' },
}

export default function ThesisClosePage() {
  const params = useParams()
  const router = useRouter()
  const thesisId = params.thesisId as string

  const { data: thesis } = useThesis(thesisId)
  const closeMutation = useCloseThesis(thesisId)

  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [outcomeNote, setOutcomeNote] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)

  // ── Mock 마감 상태 ──
  const [mockClosed, setMockClosed] = useState(false)

  const displayThesis = USE_MOCK
    ? MOCK_THESES.find((t) => t.id === thesisId) ?? MOCK_THESES[0]
    : thesis

  const isClosed = mockClosed || displayThesis?.status === 'closed'

  // ── 이미 마감된 가설: 읽기전용 요약 ──
  if (isClosed && displayThesis) {
    const outcomeKey = displayThesis.outcome ?? 'neutral'
    const display = OUTCOME_DISPLAY[outcomeKey] ?? OUTCOME_DISPLAY.neutral
    const Icon = display.icon

    return (
      <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <Link href="/thesis" className="p-1 text-gray-400 hover:text-white">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="text-white text-base font-medium flex-1">마감 결과</h1>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pt-8 pb-4">
          <div className="text-center mb-8">
            <Icon size={48} className={`mx-auto mb-3 ${display.className}`} />
            <p className={`text-lg font-medium ${display.className}`}>{display.label}</p>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-gray-500 text-xs mb-1">가설</p>
              <p className="text-white text-sm">{displayThesis.title}</p>
            </div>

            {displayThesis.outcome_note && (
              <div>
                <p className="text-gray-500 text-xs mb-1">마감 메모</p>
                <p className="text-gray-300 text-sm">{displayThesis.outcome_note}</p>
              </div>
            )}

            {displayThesis.closed_at && (
              <div>
                <p className="text-gray-500 text-xs mb-1">마감일</p>
                <p className="text-gray-400 text-sm">
                  {new Date(displayThesis.closed_at).toLocaleDateString('ko-KR', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="flex-shrink-0 border-t border-gray-800 bg-gray-950 px-4 py-4">
          <Link
            href="/thesis"
            className="block w-full py-3.5 bg-gray-800 text-gray-300 text-sm text-center
                       font-medium rounded-xl"
          >
            목록으로 돌아가기
          </Link>
        </div>
      </div>
    )
  }

  // ── 마감 진행 ──
  async function handleClose() {
    if (!outcome) return

    if (USE_MOCK) {
      // Mock: 500ms 딜레이 후 성공 시뮬레이션
      await new Promise((r) => setTimeout(r, 500))
      setMockClosed(true)
      setShowConfirm(false)
      toast.success('가설이 마감되었어요')
      return
    }

    try {
      await closeMutation.mutateAsync({
        outcome,
        outcome_note: outcomeNote || undefined,
      })
      setShowConfirm(false)
      toast.success('가설이 마감되었어요')
      router.push('/thesis')
    } catch {
      // onError in mutation handles toast
    }
  }

  return (
    <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950">
      {/* 헤더 */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
        <Link
          href={USE_MOCK ? '/thesis' : `/thesis/${thesisId}`}
          className="p-1 text-gray-400 hover:text-white"
        >
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-white text-base font-medium flex-1">가설 마감</h1>
      </div>

      {/* 본문 */}
      <div className="flex-1 overflow-y-auto px-4 pt-6 pb-4">
        {/* 가설 정보 */}
        {displayThesis && (
          <div className="mb-8">
            <p className="text-gray-500 text-xs mb-1">마감할 가설</p>
            <p className="text-white text-base font-medium">{displayThesis.title}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className={`text-xs px-2 py-0.5 rounded-full border ${
                stateToDisplay(displayThesis.current_state).colorClass
              }`}>
                {stateToDisplay(displayThesis.current_state).label}
              </span>
            </div>
          </div>
        )}

        {/* 결과 선택 */}
        <div className="mb-6">
          <p className="text-gray-300 text-sm font-medium mb-3">결과를 선택해주세요</p>
          <OutcomeSelector value={outcome} onChange={setOutcome} />
        </div>

        {/* 메모 입력 */}
        <div className="mb-6">
          <p className="text-gray-300 text-sm font-medium mb-2">마감 메모 (선택)</p>
          <textarea
            value={outcomeNote}
            onChange={(e) => setOutcomeNote(e.target.value)}
            placeholder="회고나 메모를 남겨두세요..."
            rows={3}
            className="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3
                       text-gray-200 text-sm placeholder-gray-600 resize-none
                       focus:outline-none focus:border-gray-500 transition-colors"
          />
        </div>
      </div>

      {/* 하단 CTA */}
      <div className="flex-shrink-0 border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-2">
        <button
          onClick={() => setShowConfirm(true)}
          disabled={!outcome}
          className={`w-full py-4 text-sm font-medium rounded-xl
                     active:scale-[0.98] transition-transform ${
                       outcome
                         ? 'bg-red-600 text-white'
                         : 'bg-gray-800 text-gray-600 cursor-not-allowed'
                     }`}
        >
          마감하기
        </button>
        <Link
          href={USE_MOCK ? '/thesis' : `/thesis/${thesisId}`}
          className="block w-full py-2 text-gray-500 text-sm text-center"
        >
          돌아가기
        </Link>
      </div>

      {/* 확인 다이얼로그 */}
      <CloseConfirmDialog
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleClose}
        isClosing={closeMutation.isPending}
      />
    </div>
  )
}
