'use client'

import Link from 'next/link'
import type { Thesis } from '@/lib/thesis/types'
import { MoonPhase, ThesisBadge } from '@/components/thesis'
import { daysWatching } from '@/lib/thesis/utils'
import { ChevronRight } from 'lucide-react'

interface Props {
  thesis: Thesis
}

export function ThesisListCard({ thesis }: Props) {
  return (
    <Link
      href={`/thesis/${thesis.id}`}
      className="block bg-gray-900 border border-gray-800 rounded-xl p-4
                 active:scale-[0.98] transition-transform"
    >
      <div className="flex items-center gap-3">
        {/* 달 위상 — 왼쪽 고정 */}
        <div className="flex-shrink-0">
          <MoonPhase score={thesis.current_score} size="sm" />
        </div>

        {/* 중앙 정보 */}
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-medium truncate">
            {thesis.title}
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <ThesisBadge state={thesis.current_state} direction={thesis.direction} />
          </div>
          {/* ── 보조 정보: target + 추적 일수 (M3, P1) ── */}
          <p className="text-gray-500 text-xs mt-1">
            {thesis.target?.trim() ? `${thesis.target.trim()} · ` : ''}
            {daysWatching(thesis.created_at)}일째 추적 중
          </p>
        </div>

        {/* 오른쪽 화살표 */}
        <ChevronRight size={16} className="text-gray-600 flex-shrink-0" />
      </div>
    </Link>
  )
}
