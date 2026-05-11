'use client'

import { ArrowLeft, RefreshCw } from 'lucide-react'
import Link from 'next/link'

interface Props {
  isLoading?: boolean
  onRefresh?: () => void
  showRefresh?: boolean
}

export function DashboardPageHeader({
  isLoading = false,
  onRefresh,
  showRefresh = false,
}: Props) {
  return (
    <div className="flex items-center gap-3 py-3 mb-4">
      <Link
        href="/thesis"
        className="p-1 text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft size={20} />
      </Link>
      <span className="text-white text-base font-medium flex-1">관제실</span>
      {showRefresh && onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
          aria-label="새로고침"
        >
          <RefreshCw
            size={16}
            className={isLoading ? 'animate-spin' : ''}
          />
        </button>
      )}
    </div>
  )
}
