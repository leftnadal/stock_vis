'use client'

import { X, FileText, BarChart3, Link2, Type, TrendingUp, DollarSign, Newspaper, Globe } from 'lucide-react'
import type { BasketItem as BasketItemType } from '@/types/rag'
import { DATA_TYPE_INFO } from '@/types/rag'

interface BasketItemProps {
  item: BasketItemType
  onRemove: (id: number) => void
}

// 레거시 타입 아이콘
const LEGACY_ICON_MAP = {
  stock_data: BarChart3,
  financial: FileText,
  metric: BarChart3,
  url: Link2,
  text: Type,
}

// 새 타입 아이콘
const ICON_MAP: Record<string, any> = {
  overview: FileText,
  price: DollarSign,
  financial_summary: BarChart3,
  financial_full: BarChart3,
  indicator: TrendingUp,
  news: Newspaper,
  macro: Globe,
}

const LEGACY_TYPE_LABEL_MAP = {
  stock_data: '주가 데이터',
  financial: '재무제표',
  metric: '지표',
  url: 'URL',
  text: '텍스트',
}

export function BasketItem({ item, onRemove }: BasketItemProps) {
  // 레거시 타입과 새 타입 모두 지원
  const itemType = item.item_type || item.type || 'text'
  const Icon = ICON_MAP[itemType] || LEGACY_ICON_MAP[itemType as keyof typeof LEGACY_ICON_MAP] || Type
  const typeInfo = DATA_TYPE_INFO[itemType]
  const typeLabel = typeInfo?.label || LEGACY_TYPE_LABEL_MAP[itemType as keyof typeof LEGACY_TYPE_LABEL_MAP] || itemType

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return '방금 전'
    if (diffMins < 60) return `${diffMins}분 전`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}시간 전`
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="group relative flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 transition-all hover:border-slate-300 hover:shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:hover:border-slate-600">
      {/* 아이콘 */}
      <div className="flex-shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 dark:bg-slate-700">
          <Icon className="h-4 w-4 text-slate-600 dark:text-slate-400" />
        </div>
      </div>

      {/* 내용 */}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h4 className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
              {item.title}
            </h4>
            {item.subtitle && (
              <p className="truncate text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {item.subtitle}
              </p>
            )}
            <div className="mt-1 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium dark:bg-slate-700">
                {typeLabel}
              </span>
              {item.data_units && (
                <span className="text-blue-600 dark:text-blue-400 font-medium">
                  {item.data_units}u
                </span>
              )}
              {item.symbol && (
                <span className="font-medium text-green-600 dark:text-green-400">
                  {item.symbol}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {item.source || formatDate(item.snapshot_date || item.added_at)} • {formatDate(item.added_at)}
            </p>
          </div>

          {/* 삭제 버튼 */}
          <button
            onClick={() => onRemove(item.id)}
            className="flex-shrink-0 rounded p-1 text-slate-400 opacity-0 transition-all hover:bg-slate-100 hover:text-slate-600 group-hover:opacity-100 dark:hover:bg-slate-700 dark:hover:text-slate-300"
            aria-label="아이템 제거"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
