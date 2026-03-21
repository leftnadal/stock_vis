'use client'

import { Plus, Check } from 'lucide-react'
import { BottomSheet } from '@/components/thesis/common/BottomSheet'

// INDICATOR_CATALOG 미러 (prompt_builder.py와 동일)
const INDICATOR_CATALOG = [
  { id: 1, name: '외국인 순매수 추이', category: '시장 데이터' },
  { id: 2, name: '기관 순매수 추이', category: '시장 데이터' },
  { id: 3, name: 'S&P 500', category: '시장 데이터' },
  { id: 4, name: 'KOSPI 지수', category: '시장 데이터' },
  { id: 5, name: 'EPS 추이', category: '시장 데이터' },
  { id: 6, name: '미국 기준금리', category: '거시경제' },
  { id: 7, name: '미국 10년 국채 금리', category: '거시경제' },
  { id: 8, name: 'VIX (공포지수)', category: '거시경제' },
  { id: 9, name: '원/달러 환율', category: '거시경제' },
  { id: 10, name: 'RSI (14일)', category: '기술적' },
  { id: 11, name: '뉴스 센티먼트', category: '심리' },
]

interface AddIndicatorSheetProps {
  isOpen: boolean
  onClose: () => void
  selectedIds: number[]
  onToggle: (id: number, name: string) => void
}

export function AddIndicatorSheet({ isOpen, onClose, selectedIds, onToggle }: AddIndicatorSheetProps) {
  // 카테고리별 그룹핑
  const byCategory: Record<string, typeof INDICATOR_CATALOG> = {}
  for (const ind of INDICATOR_CATALOG) {
    if (!byCategory[ind.category]) byCategory[ind.category] = []
    byCategory[ind.category].push(ind)
  }

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="지표 추가">
      <div className="space-y-4 max-h-[50vh] overflow-y-auto">
        {Object.entries(byCategory).map(([category, indicators]) => (
          <div key={category}>
            <p className="text-xs text-gray-500 mb-2">{category}</p>
            <div className="space-y-1.5">
              {indicators.map((ind) => {
                const isSelected = selectedIds.includes(ind.id)
                return (
                  <button
                    key={ind.id}
                    onClick={() => onToggle(ind.id, ind.name)}
                    className={`w-full flex items-center justify-between px-3 py-2.5
                               rounded-lg text-left text-sm transition-colors
                               ${isSelected
                                 ? 'bg-blue-900/30 border border-blue-500/50 text-blue-300'
                                 : 'bg-gray-900 border border-gray-800 text-gray-300 hover:border-gray-600'
                               }`}
                  >
                    <span>{ind.name}</span>
                    {isSelected
                      ? <Check size={14} className="text-blue-400" />
                      : <Plus size={14} className="text-gray-600" />
                    }
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
      <button
        onClick={onClose}
        className="mt-4 w-full py-3 bg-blue-600 text-white text-sm font-medium rounded-xl"
      >
        완료
      </button>
    </BottomSheet>
  )
}
