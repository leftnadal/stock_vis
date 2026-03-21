'use client'

import { Plus, Check } from 'lucide-react'
import { BottomSheet } from '@/components/thesis/common/BottomSheet'

// INDICATOR_CATALOG 미러 (prompt_builder.py와 동기화)
const INDICATOR_CATALOG = [
  // 시장 데이터: 수급
  { id: 1, name: '외국인 순매수 추이', category: '수급' },
  { id: 2, name: '기관 순매수 추이', category: '수급' },
  // 시장 데이터: 주요 지수
  { id: 3, name: 'S&P 500', category: '주요 지수' },
  { id: 4, name: 'KOSPI 지수', category: '주요 지수' },
  { id: 12, name: 'NASDAQ', category: '주요 지수' },
  { id: 13, name: '다우존스', category: '주요 지수' },
  { id: 14, name: '코스닥 지수', category: '주요 지수' },
  { id: 15, name: '니케이 225', category: '주요 지수' },
  { id: 16, name: '항셍 지수', category: '주요 지수' },
  // 원자재/상품
  { id: 20, name: '금 (Gold)', category: '원자재' },
  { id: 21, name: '원유 (WTI)', category: '원자재' },
  { id: 22, name: '은 (Silver)', category: '원자재' },
  { id: 23, name: '구리 (Copper)', category: '원자재' },
  { id: 24, name: '천연가스', category: '원자재' },
  // 암호화폐
  { id: 25, name: '비트코인 (BTC)', category: '암호화폐' },
  { id: 26, name: '이더리움 (ETH)', category: '암호화폐' },
  // 거시경제: 금리
  { id: 6, name: '미국 기준금리', category: '금리' },
  { id: 7, name: '미국 10년 국채', category: '금리' },
  { id: 30, name: '미국 2년 국채', category: '금리' },
  { id: 37, name: '30년 모기지 금리', category: '금리' },
  // 거시경제: 환율/변동성
  { id: 8, name: 'VIX (공포지수)', category: '환율/변동성' },
  { id: 9, name: '원/달러 환율', category: '환율/변동성' },
  { id: 38, name: '달러/유로 환율', category: '환율/변동성' },
  { id: 39, name: '달러 인덱스 (DXY)', category: '환율/변동성' },
  // 거시경제: 고용/성장/물가
  { id: 31, name: '실업률', category: '고용/성장' },
  { id: 32, name: '비농업 고용 (NFP)', category: '고용/성장' },
  { id: 34, name: '실질 GDP', category: '고용/성장' },
  { id: 35, name: '산업생산지수', category: '고용/성장' },
  { id: 33, name: '소비자물가지수 (CPI)', category: '물가/주택' },
  { id: 36, name: '주택착공건수', category: '물가/주택' },
  // 기술적
  { id: 10, name: 'RSI (14일)', category: '기술적' },
  { id: 40, name: 'MACD', category: '기술적' },
  { id: 41, name: '스토캐스틱 %K', category: '기술적' },
  { id: 42, name: '볼린저 밴드 %B', category: '기술적' },
  { id: 43, name: 'ATR (평균진폭)', category: '기술적' },
  { id: 44, name: 'OBV (거래량 누적)', category: '기술적' },
  { id: 45, name: 'SMA 50일', category: '기술적' },
  { id: 46, name: 'SMA 200일', category: '기술적' },
  { id: 47, name: 'EMA 12일', category: '기술적' },
  // 펀더멘털
  { id: 5, name: 'EPS 추이', category: '펀더멘털' },
  { id: 50, name: 'PER (주가수익비율)', category: '펀더멘털' },
  { id: 51, name: 'PBR (주가순자산비율)', category: '펀더멘털' },
  { id: 52, name: 'ROE (자기자본이익률)', category: '펀더멘털' },
  { id: 53, name: 'ROA (총자산이익률)', category: '펀더멘털' },
  { id: 54, name: '부채비율 (D/E)', category: '펀더멘털' },
  { id: 55, name: '잉여현금흐름 (FCF)', category: '펀더멘털' },
  { id: 56, name: '배당수익률', category: '펀더멘털' },
  { id: 57, name: '영업이익률', category: '펀더멘털' },
  { id: 58, name: '매출성장률 (YoY)', category: '펀더멘털' },
  // 심리
  { id: 11, name: '뉴스 센티먼트', category: '심리' },
]

interface AddIndicatorSheetProps {
  isOpen: boolean
  onClose: () => void
  selectedIds: number[]
  onToggle: (id: number, name: string) => void
}

export function AddIndicatorSheet({ isOpen, onClose, selectedIds, onToggle }: AddIndicatorSheetProps) {
  const byCategory: Record<string, typeof INDICATOR_CATALOG> = {}
  for (const ind of INDICATOR_CATALOG) {
    if (!byCategory[ind.category]) byCategory[ind.category] = []
    byCategory[ind.category].push(ind)
  }

  const categoryOrder = [
    '수급', '주요 지수', '원자재', '암호화폐',
    '금리', '환율/변동성', '고용/성장', '물가/주택',
    '기술적', '펀더멘털', '심리',
  ]

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="지표 추가">
      <div className="space-y-4 max-h-[60vh] overflow-y-auto">
        {categoryOrder.map((category) => {
          const indicators = byCategory[category]
          if (!indicators) return null
          return (
            <div key={category}>
              <p className="text-xs text-gray-500 mb-2 sticky top-0 bg-gray-950 py-1">{category}</p>
              <div className="grid grid-cols-2 gap-1.5">
                {indicators.map((ind) => {
                  const isSelected = selectedIds.includes(ind.id)
                  return (
                    <button
                      key={ind.id}
                      onClick={() => onToggle(ind.id, ind.name)}
                      className={`flex items-center justify-between px-2.5 py-2
                                 rounded-lg text-left text-xs transition-colors
                                 ${isSelected
                                   ? 'bg-blue-900/30 border border-blue-500/50 text-blue-300'
                                   : 'bg-gray-900 border border-gray-800 text-gray-300 hover:border-gray-600'
                                 }`}
                    >
                      <span className="truncate">{ind.name}</span>
                      {isSelected
                        ? <Check size={12} className="text-blue-400 flex-shrink-0 ml-1" />
                        : <Plus size={12} className="text-gray-600 flex-shrink-0 ml-1" />
                      }
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
      <button
        onClick={onClose}
        className="mt-4 w-full py-3 bg-blue-600 text-white text-sm font-medium rounded-xl"
      >
        완료 ({selectedIds.length}개 선택)
      </button>
    </BottomSheet>
  )
}
