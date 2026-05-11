'use client'

import Link from 'next/link'
import type { ThesisAlert } from '@/lib/thesis/types'
import { severityToStyle, relativeTime } from '@/lib/thesis/utils'

interface Props {
  alert: ThesisAlert
  onMarkRead?: (alertId: string) => void
}

export function AlertCard({ alert, onMarkRead }: Props) {
  const severity = severityToStyle(alert.severity)

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        alert.is_read
          ? 'bg-gray-900/30 border-gray-800'
          : 'bg-gray-900 border-gray-700'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* severity 배지 + 제목 */}
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${severity.className}`}
            >
              {severity.label}
            </span>
            <span className="text-gray-500 text-[10px]">
              {relativeTime(alert.created_at)}
            </span>
          </div>

          {/* TODO: Phase 3에서 highlight 파라미터 추가 */}
          <Link
            href={`/thesis/${alert.thesis}`}
            className="text-white text-sm font-medium hover:text-blue-400 transition-colors line-clamp-1"
          >
            {alert.title}
          </Link>

          <p className="text-gray-400 text-xs mt-1 line-clamp-2">
            {alert.message}
          </p>
        </div>

        {/* 읽음 처리 버튼 */}
        {!alert.is_read && onMarkRead && (
          <button
            onClick={(e) => {
              e.preventDefault()
              onMarkRead(alert.id)
            }}
            className="flex-shrink-0 text-[10px] text-gray-500 border border-gray-700
                       px-2 py-1 rounded-lg hover:text-gray-300 hover:border-gray-600
                       transition-colors"
          >
            읽음
          </button>
        )}
      </div>
    </div>
  )
}
