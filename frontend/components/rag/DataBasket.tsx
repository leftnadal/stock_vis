'use client'

import { ShoppingBasket, X, Trash2 } from 'lucide-react'
import { BasketItem } from './BasketItem'
import { CapacityGauge } from './CapacityGauge'
import type { Basket as BasketType } from '@/types/rag'

interface DataBasketProps {
  basket: BasketType | null
  isOpen: boolean
  onClose: () => void
  onRemoveItem: (itemId: number) => void
  onClear: () => void
}

const MAX_ITEMS = 15

export function DataBasket({
  basket,
  isOpen,
  onClose,
  onRemoveItem,
  onClear,
}: DataBasketProps) {
  const itemCount = basket?.items.length || 0
  const isEmpty = itemCount === 0

  return (
    <>
      {/* 오버레이 */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm dark:bg-black/40"
          onClick={onClose}
        />
      )}

      {/* 사이드 패널 */}
      <div
        className={`fixed right-0 top-0 z-50 h-full w-80 transform border-l border-slate-200 bg-white shadow-xl transition-transform duration-300 ease-in-out dark:border-slate-700 dark:bg-slate-900 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* 헤더 */}
          <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <ShoppingBasket className="h-5 w-5 text-slate-600 dark:text-slate-400" />
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                데이터 바구니
              </h2>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
              aria-label="닫기"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* 용량 게이지 */}
          <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/50">
            {basket ? (
              <>
                <CapacityGauge
                  currentUnits={basket.current_units || 0}
                  maxUnits={basket.max_units || 100}
                  className="mb-3"
                />
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">
                    아이템 수
                  </span>
                  <span
                    className={`font-semibold ${
                      itemCount >= MAX_ITEMS
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-slate-900 dark:text-slate-100'
                    }`}
                  >
                    {itemCount} / {MAX_ITEMS}
                  </span>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">
                  아이템 수
                </span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">
                  0 / {MAX_ITEMS}
                </span>
              </div>
            )}
          </div>

          {/* 아이템 리스트 */}
          <div className="flex-1 overflow-y-auto p-4">
            {isEmpty ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <ShoppingBasket className="h-12 w-12 text-slate-300 dark:text-slate-600" />
                <p className="mt-4 text-sm font-medium text-slate-600 dark:text-slate-400">
                  바구니가 비어있습니다
                </p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
                  분석할 데이터를 추가해보세요
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {basket?.items.map((item) => (
                  <BasketItem
                    key={item.id}
                    item={item}
                    onRemove={onRemoveItem}
                  />
                ))}
              </div>
            )}
          </div>

          {/* 하단 액션 */}
          {!isEmpty && (
            <div className="border-t border-slate-200 p-4 dark:border-slate-700">
              <button
                onClick={onClear}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 dark:border-red-800 dark:bg-red-950/50 dark:text-red-400 dark:hover:bg-red-950"
              >
                <Trash2 className="h-4 w-4" />
                모두 비우기
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
