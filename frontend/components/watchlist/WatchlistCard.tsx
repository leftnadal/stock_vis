'use client'

import { MoreVertical, ListChecks } from 'lucide-react'
import type { Watchlist } from '@/types/watchlist'

interface WatchlistCardProps {
  watchlist: Watchlist
  isSelected?: boolean
  onClick: () => void
  onEdit: () => void
  onDelete: () => void
}

export default function WatchlistCard({
  watchlist,
  isSelected = false,
  onClick,
  onEdit,
  onDelete
}: WatchlistCardProps) {
  return (
    <div
      onClick={onClick}
      className={`
        bg-white dark:bg-gray-800 rounded-xl p-4 cursor-pointer transition-all
        ${isSelected
          ? 'ring-2 ring-blue-500 shadow-lg'
          : 'hover:shadow-md border border-gray-200 dark:border-gray-700'
        }
      `}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <ListChecks className={`h-5 w-5 ${isSelected ? 'text-blue-600' : 'text-gray-400'}`} />
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {watchlist.name}
            </h3>
          </div>

          {watchlist.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
              {watchlist.description}
            </p>
          )}

          <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
            <div className="flex items-center space-x-1">
              <span className="font-medium text-blue-600 dark:text-blue-400">
                {watchlist.stock_count}
              </span>
              <span>종목</span>
            </div>
            <div className="text-xs">
              {new Date(watchlist.updated_at).toLocaleDateString('ko-KR')}
            </div>
          </div>
        </div>

        <div className="relative group">
          <button
            onClick={(e) => {
              e.stopPropagation()
            }}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
          >
            <MoreVertical className="h-5 w-5" />
          </button>

          {/* Dropdown Menu */}
          <div className="absolute right-0 mt-1 w-32 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 hidden group-hover:block z-10">
            <button
              onClick={(e) => {
                e.stopPropagation()
                onEdit()
              }}
              className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-t-lg"
            >
              수정
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
              className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-b-lg"
            >
              삭제
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
