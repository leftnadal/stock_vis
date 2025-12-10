'use client'

import { useRouter } from 'next/navigation'
import { Edit2, Trash2, Target, TrendingUp, TrendingDown } from 'lucide-react'
import type { WatchlistItem } from '@/types/watchlist'
import { WATCHLIST_MESSAGES, formatCurrency, formatPercent, formatDate } from '@/constants/watchlist'

interface WatchlistItemRowProps {
  item: WatchlistItem
  onEdit: () => void
  onRemove: () => void
}

export default function WatchlistItemRow({ item, onEdit, onRemove }: WatchlistItemRowProps) {
  const router = useRouter()

  const currentPrice = parseFloat(item.current_price)
  const change = parseFloat(item.change)
  const changePercent = parseFloat(item.change_percent)
  const isPositive = change >= 0

  const handleRowClick = () => {
    router.push(`/stocks/${item.stock_symbol}`)
  }

  return (
    <tr
      onClick={handleRowClick}
      className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors border-b border-gray-200 dark:border-gray-700 last:border-b-0"
    >
      {/* 종목명 */}
      <td className="px-6 py-4">
        <div className="flex flex-col">
          <span className="font-semibold text-gray-900 dark:text-white">
            {item.stock_symbol}
          </span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {item.stock_name}
          </span>
        </div>
      </td>

      {/* 현재가 */}
      <td className="px-6 py-4 text-right">
        <span className="font-medium text-gray-900 dark:text-white">
          {formatCurrency(currentPrice)}
        </span>
      </td>

      {/* 변동 */}
      <td className="px-6 py-4 text-right">
        <div className="flex flex-col items-end space-y-1">
          <div className={`flex items-center space-x-1 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            <span className="font-medium">
              {formatCurrency(Math.abs(change))}
            </span>
          </div>
          <span className={`text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {formatPercent(changePercent)}
          </span>
        </div>
      </td>

      {/* 목표 진입가 */}
      <td className="px-6 py-4 text-right">
        {item.target_entry_price ? (
          <div className="flex flex-col items-end space-y-1">
            <div className="flex items-center space-x-2">
              <Target className="h-4 w-4 text-gray-400" />
              <span className="font-medium text-gray-900 dark:text-white">
                {formatCurrency(parseFloat(item.target_entry_price))}
              </span>
            </div>
            {item.distance_from_entry !== null && (
              <div className="flex items-center space-x-1">
                <span className={`text-sm ${item.is_below_target ? 'text-green-600' : 'text-gray-500 dark:text-gray-400'}`}>
                  {item.is_below_target ? WATCHLIST_MESSAGES.STATUS.TARGET_REACHED : WATCHLIST_MESSAGES.STATUS.PRICE_DIFF(item.distance_from_entry)}
                </span>
              </div>
            )}
          </div>
        ) : (
          <span className="text-gray-400 dark:text-gray-500 text-sm">{WATCHLIST_MESSAGES.STATUS.NOT_SET}</span>
        )}
      </td>

      {/* 메모 */}
      <td className="px-6 py-4">
        {item.notes ? (
          <span className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
            {item.notes}
          </span>
        ) : (
          <span className="text-gray-400 dark:text-gray-500 text-sm">{WATCHLIST_MESSAGES.STATUS.NO_DATA}</span>
        )}
      </td>

      {/* 추가일 */}
      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
        {formatDate(item.added_at)}
      </td>

      {/* 액션 */}
      <td className="px-6 py-4">
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit()
            }}
            className="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            title={WATCHLIST_MESSAGES.LABEL.EDIT}
          >
            <Edit2 className="h-4 w-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onRemove()
            }}
            className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            title={WATCHLIST_MESSAGES.LABEL.REMOVE}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  )
}
