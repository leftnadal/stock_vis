'use client'

// 보유(WalletHolding) 추가/수정 모달 (Slice 20b, D5 ① 목록+모달).
// 하우스 관용구(overlay+card+X+form+actions, if(!isOpen) return null) 답습 +
// role="dialog"/aria-modal/ESC 닫기 최소 a11y 가산(폼 모달 3종엔 부재라 개선).
import { useEffect, useState } from 'react'
import { X } from 'lucide-react'

import { useCreateHolding, useDeleteHolding, useUpdateHolding } from '@/hooks/useWallet'
import type { Holding } from '@/types/wallet'

interface HoldingModalProps {
  isOpen: boolean
  onClose: () => void
  editing?: Holding | null
}

function todayISO(): string {
  // 모듈 레벨 Date.now() 금지(#24) — 렌더 시점 지역 계산은 OK
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

const INPUT_CLS =
  'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white'

function errorMessage(err: unknown): string {
  const resp = (err as { response?: { data?: unknown } })?.response?.data
  if (resp && typeof resp === 'object') {
    const data = resp as Record<string, unknown>
    if (typeof data.detail === 'string') return data.detail
    if (data.errors && typeof data.errors === 'object') {
      const first = Object.values(data.errors as Record<string, unknown>)[0]
      if (Array.isArray(first)) return String(first[0])
      if (typeof first === 'string') return first
    }
  }
  return '저장 중 오류가 발생했습니다. 입력값을 확인해주세요.'
}

export function HoldingModal({ isOpen, onClose, editing = null }: HoldingModalProps) {
  const isEdit = !!editing
  const [symbol, setSymbol] = useState('')
  const [shares, setShares] = useState('')
  const [avgCost, setAvgCost] = useState('')
  const [firstBoughtAt, setFirstBoughtAt] = useState(todayISO())
  const [thesis, setThesis] = useState('')
  const [error, setError] = useState<string | null>(null)

  const createM = useCreateHolding()
  const updateM = useUpdateHolding()
  const deleteM = useDeleteHolding()
  const saving = createM.isPending || updateM.isPending || deleteM.isPending

  useEffect(() => {
    if (editing) {
      setSymbol(editing.symbol)
      setShares(editing.shares)
      setAvgCost(editing.avg_cost)
      setFirstBoughtAt(editing.first_bought_at ?? todayISO())
      setThesis(editing.investment_thesis ?? '')
    } else {
      setSymbol('')
      setShares('')
      setAvgCost('')
      setFirstBoughtAt(todayISO())
      setThesis('')
    }
    setError(null)
  }, [editing, isOpen])

  // ESC 닫기 (하우스 폼 모달엔 부재 — 최소 a11y 가산)
  useEffect(() => {
    if (!isOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !saving) onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [isOpen, saving, onClose])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!isEdit && !symbol.trim()) {
      setError('종목 심볼을 입력해주세요.')
      return
    }
    if (!(Number(shares) > 0)) {
      setError('수량은 0보다 커야 합니다.')
      return
    }
    if (!(Number(avgCost) > 0)) {
      setError('평단은 0보다 커야 합니다.')
      return
    }
    try {
      if (isEdit && editing) {
        await updateM.mutateAsync({
          id: editing.id,
          input: { shares, avg_cost: avgCost, first_bought_at: firstBoughtAt, investment_thesis: thesis },
        })
      } else {
        await createM.mutateAsync({
          symbol: symbol.trim().toUpperCase(),
          shares,
          avg_cost: avgCost,
          first_bought_at: firstBoughtAt,
          investment_thesis: thesis,
        })
      }
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const handleDelete = async () => {
    if (!editing) return
    if (!window.confirm(`'${editing.symbol}' 보유를 삭제할까요?`)) return
    setError(null)
    try {
      await deleteM.mutateAsync(editing.id)
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={isEdit ? '보유 수정' : '보유 추가'}
        data-testid="holding-modal"
        className="w-full max-w-md rounded-xl bg-white dark:bg-gray-800"
      >
        <div className="flex items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {isEdit ? '보유 수정' : '보유 추가'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="h-symbol" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                종목 심볼 *
              </label>
              <input
                id="h-symbol"
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                disabled={isEdit}
                className={`${INPUT_CLS} disabled:cursor-not-allowed disabled:opacity-60`}
                placeholder="예: AAPL"
                required
              />
              <p className="mt-1 text-xs text-gray-400">
                통화{editing ? ` · ${editing.currency}` : '는 종목에 따라 자동 결정됩니다'}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="h-shares" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  수량 *
                </label>
                <input
                  id="h-shares"
                  type="number"
                  value={shares}
                  onChange={(e) => setShares(e.target.value)}
                  className={INPUT_CLS}
                  placeholder="0"
                  step="0.0001"
                  required
                />
              </div>
              <div>
                <label htmlFor="h-avgcost" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  평단 *
                </label>
                <input
                  id="h-avgcost"
                  type="number"
                  value={avgCost}
                  onChange={(e) => setAvgCost(e.target.value)}
                  className={INPUT_CLS}
                  placeholder="0.00"
                  step="0.0001"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="h-date" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                최초 매수일 *
              </label>
              <input
                id="h-date"
                type="date"
                value={firstBoughtAt}
                onChange={(e) => setFirstBoughtAt(e.target.value)}
                className={INPUT_CLS}
                required
              />
            </div>

            <div>
              <label htmlFor="h-thesis" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                투자 논지 (선택)
              </label>
              <textarea
                id="h-thesis"
                value={thesis}
                onChange={(e) => setThesis(e.target.value)}
                className={INPUT_CLS}
                rows={3}
                placeholder="이 종목을 매수한 근거 — 코치가 대화 맥락으로 활용합니다."
              />
            </div>

            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3" role="alert">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-between">
            <div>
              {isEdit && (
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={saving}
                  className="px-4 py-2 font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
                >
                  삭제
                </button>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 font-medium text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-blue-600 px-6 py-2 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? '저장 중...' : isEdit ? '수정' : '추가'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
