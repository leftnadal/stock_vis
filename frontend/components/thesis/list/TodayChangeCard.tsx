'use client'

import Link from 'next/link'
import type { ThesisAlert } from '@/lib/thesis/types'
import { relativeTime } from '@/lib/thesis/utils'
import { Bell } from 'lucide-react'

interface Props {
  alert: ThesisAlert
}

export function TodayChangeCard({ alert }: Props) {
  return (
    <Link
      href={`/thesis/${alert.thesis}?highlight=${alert.id}`}
      className="block bg-gray-900 border border-gray-800 rounded-xl p-4
                 active:scale-[0.98] transition-transform"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <Bell size={16} className="text-yellow-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-medium">{alert.title}</p>
          <p className="text-gray-400 text-xs mt-1 line-clamp-1">
            {alert.message}
          </p>
        </div>
        <span className="text-gray-600 text-xs flex-shrink-0 whitespace-nowrap">
          {relativeTime(alert.created_at)}
        </span>
      </div>
    </Link>
  )
}
