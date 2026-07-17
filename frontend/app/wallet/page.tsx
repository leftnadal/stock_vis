'use client'

/**
 * My 탭 "지갑" 화면 (Slice 20b).
 *
 * admin 입력 지름길을 대체하는 보유·현금 입력 UI. 4-상태(로딩/에러/빈/성공).
 * 보유 = WalletHolding(티커·수량·평단·통화·논지), 현금 = CashBalance(통화별 KRW/USD).
 * 권유 엔진(19c)이 이 지갑을 입력으로 쓴다 — 저장 후 [코치]의 [지금 진단]으로 반영.
 */

import { useState } from 'react'
import { AlertCircle, Loader2, Plus, Wallet as WalletIcon } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { CashModal } from '@/components/wallet/CashModal'
import { HoldingModal } from '@/components/wallet/HoldingModal'
import { useCash, useHoldings } from '@/hooks/useWallet'
import type { CashBalance, Currency, Holding } from '@/types/wallet'

const CURRENCY_SLOTS: Currency[] = ['USD', 'KRW']

function fmtAmount(v: string): string {
  const n = Number(v)
  if (Number.isNaN(n)) return v
  return n.toLocaleString('ko-KR', { maximumFractionDigits: 2 })
}

function WalletPageContent() {
  const holdingsQuery = useHoldings()
  const cashQuery = useCash()

  const [holdingModalOpen, setHoldingModalOpen] = useState(false)
  const [editingHolding, setEditingHolding] = useState<Holding | null>(null)
  const [cashModalOpen, setCashModalOpen] = useState(false)
  const [editingCash, setEditingCash] = useState<CashBalance | null>(null)
  const [cashPreset, setCashPreset] = useState<Currency>('USD')

  const isLoading = holdingsQuery.isLoading || cashQuery.isLoading
  const isError = holdingsQuery.isError || cashQuery.isError
  const holdings = holdingsQuery.data ?? []
  const cashList = cashQuery.data ?? []
  const cashByCurrency = new Map(cashList.map((c) => [c.currency, c]))

  const openHoldingAdd = () => {
    setEditingHolding(null)
    setHoldingModalOpen(true)
  }
  const openHoldingEdit = (h: Holding) => {
    setEditingHolding(h)
    setHoldingModalOpen(true)
  }
  const openCash = (currency: Currency) => {
    setEditingCash(cashByCurrency.get(currency) ?? null)
    setCashPreset(currency) // 빈 카드 클릭 시 해당 통화로 신규 입력
    setCashModalOpen(true)
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-gray-900 dark:text-gray-100">
            <WalletIcon className="h-5 w-5" />
            지갑
          </h1>
          <p className="text-sm text-gray-500">
            보유 종목과 현금을 입력하세요. 코치의 권유 진단이 이 지갑을 근거로 삼습니다.
          </p>
        </div>
        <button
          type="button"
          data-testid="add-holding-button"
          onClick={openHoldingAdd}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          보유 추가
        </button>
      </div>

      {isLoading && (
        <div
          data-testid="loading-state"
          className="flex flex-col items-center gap-3 rounded-2xl border border-slate-200 bg-white p-10 text-slate-600 dark:border-gray-800 dark:bg-gray-900"
        >
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <p className="text-sm">불러오는 중...</p>
        </div>
      )}

      {!isLoading && isError && (
        <div
          role="alert"
          data-testid="error-state"
          className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-800 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300"
        >
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-medium">지갑 정보를 불러오지 못했습니다.</p>
            <p className="mt-1">잠시 후 다시 시도해 주세요.</p>
          </div>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="flex flex-col gap-6">
          {/* 현금 카드 (통화별) */}
          <section>
            <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">현금</h2>
            <div className="grid grid-cols-2 gap-3" data-testid="cash-cards">
              {CURRENCY_SLOTS.map((cur) => {
                const cash = cashByCurrency.get(cur)
                return (
                  <button
                    key={cur}
                    type="button"
                    data-testid={`cash-card-${cur}`}
                    onClick={() => openCash(cur)}
                    className="flex flex-col items-start rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-300 dark:border-gray-800 dark:bg-gray-900"
                  >
                    <span className="text-[11px] text-gray-400">{cur}</span>
                    {cash ? (
                      <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {fmtAmount(cash.amount)}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">+ 입력</span>
                    )}
                  </button>
                )
              })}
            </div>
          </section>

          {/* 보유 목록 */}
          <section>
            <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">보유 종목</h2>
            {holdings.length === 0 ? (
              <div
                data-testid="holdings-empty"
                className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-400"
              >
                아직 보유 종목이 없어요. <span className="font-medium">[보유 추가]</span>로 입력하세요.
              </div>
            ) : (
              <ul className="flex flex-col gap-2" data-testid="holdings-list">
                {holdings.map((h) => (
                  <li key={h.id}>
                    <button
                      type="button"
                      data-testid={`holding-row-${h.symbol}`}
                      onClick={() => openHoldingEdit(h)}
                      className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-300 dark:border-gray-800 dark:bg-gray-900"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900 dark:text-gray-100">{h.symbol}</span>
                          <span className="rounded-full bg-gray-100 px-1.5 text-[10px] text-gray-500 dark:bg-gray-800">
                            {h.currency}
                          </span>
                        </div>
                        {h.investment_thesis && (
                          <p className="mt-0.5 truncate text-xs text-gray-400">{h.investment_thesis}</p>
                        )}
                      </div>
                      <div className="ml-3 shrink-0 text-right">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {fmtAmount(h.shares)}주
                        </div>
                        <div className="text-xs text-gray-400">평단 {fmtAmount(h.avg_cost)}</div>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      <HoldingModal
        isOpen={holdingModalOpen}
        onClose={() => setHoldingModalOpen(false)}
        editing={editingHolding}
      />
      <CashModal
        isOpen={cashModalOpen}
        onClose={() => setCashModalOpen(false)}
        editing={editingCash}
        presetCurrency={cashPreset}
      />
    </div>
  )
}

export default function WalletPage() {
  return (
    <AuthGuard>
      <WalletPageContent />
    </AuthGuard>
  )
}
