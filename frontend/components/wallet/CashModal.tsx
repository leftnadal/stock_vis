'use client'

// 현금(CashBalance) 통화별 입력/수정 모달 (Slice 20b). 하우스 관용구 + 최소 a11y.
import { useEffect, useState } from 'react'
import { X } from 'lucide-react'

import { useDeleteCash, useUpsertCash } from '@/hooks/useWallet'
import type { CashBalance, Currency } from '@/types/wallet'

interface CashModalProps {
  isOpen: boolean
  onClose: () => void
  editing?: CashBalance | null
  presetCurrency?: Currency // editing이 없을 때 신규 입력 기본 통화(빈 카드 클릭)
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
  return '저장 중 오류가 발생했습니다.'
}

export function CashModal({ isOpen, onClose, editing = null, presetCurrency = 'USD' }: CashModalProps) {
  const isEdit = !!editing
  const [currency, setCurrency] = useState<Currency>('USD')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string | null>(null)

  const upsertM = useUpsertCash()
  const deleteM = useDeleteCash()
  const saving = upsertM.isPending || deleteM.isPending

  useEffect(() => {
    if (editing) {
      setCurrency(editing.currency)
      setAmount(editing.amount)
    } else {
      setCurrency(presetCurrency)
      setAmount('')
    }
    setError(null)
  }, [editing, isOpen, presetCurrency])

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
    if (!(Number(amount) >= 0)) {
      setError('현금은 0 이상이어야 합니다.')
      return
    }
    try {
      await upsertM.mutateAsync({ currency, amount })
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const handleDelete = async () => {
    if (!editing) return
    if (!window.confirm(`${editing.currency} 현금을 삭제할까요?`)) return
    setError(null)
    try {
      await deleteM.mutateAsync(editing.currency)
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
        aria-label={isEdit ? '현금 수정' : '현금 입력'}
        data-testid="cash-modal"
        className="w-full max-w-sm rounded-xl bg-white dark:bg-gray-800"
      >
        <div className="flex items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {isEdit ? '현금 수정' : '현금 입력'}
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
              <label htmlFor="c-currency" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                통화 *
              </label>
              <select
                id="c-currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value as Currency)}
                disabled={isEdit}
                className={`${INPUT_CLS} disabled:cursor-not-allowed disabled:opacity-60`}
              >
                <option value="USD">USD</option>
                <option value="KRW">KRW</option>
              </select>
            </div>

            <div>
              <label htmlFor="c-amount" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                금액 *
              </label>
              <input
                id="c-amount"
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className={INPUT_CLS}
                placeholder="0"
                step="0.01"
                min="0"
                required
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
                {saving ? '저장 중...' : '저장'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
