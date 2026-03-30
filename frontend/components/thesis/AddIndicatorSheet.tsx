'use client'

import { Plus, Check, Sparkles } from 'lucide-react'
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

// 키워드 → 지표 ID 매핑 (indicator_matcher.py KEYWORD_RULES 경량 미러)
const KEYWORD_INDICATOR_MAP: Array<{ keywords: string[]; indicatorIds: number[] }> = [
  { keywords: ['외국인', '외인', '순매수', '순매도', 'foreign'], indicatorIds: [1] },
  { keywords: ['기관', '기관투자자', '연기금', '보험', '자산운용'], indicatorIds: [2] },
  { keywords: ['금리', '연준', 'fomc', 'fed', '기준금리', '금리인하', '금리인상', '이자율', '통화정책'], indicatorIds: [6, 7, 30] },
  { keywords: ['vix', '공포', '변동성', '리스크', '불확실'], indicatorIds: [8] },
  { keywords: ['환율', '달러', '원달러', 'usd', 'krw', '원화', '강달러', '약달러'], indicatorIds: [9, 39] },
  { keywords: ['s&p', 's&p500', '나스닥', 'nasdaq', '미국시장', '미국 주식', '월가'], indicatorIds: [3, 12] },
  { keywords: ['코스피', 'kospi', '한국시장', '종합주가'], indicatorIds: [4] },
  { keywords: ['유가', '원유', 'wti', '석유', '에너지', 'opec', '오일'], indicatorIds: [21] },
  { keywords: ['금', 'gold', '금값', '안전자산'], indicatorIds: [20] },
  { keywords: ['구리', 'copper', '산업금속', '경기선행'], indicatorIds: [23] },
  { keywords: ['천연가스', 'lng', '가스'], indicatorIds: [24] },
  { keywords: ['비트코인', 'btc', '암호화폐', '크립토', '코인'], indicatorIds: [25, 26] },
  { keywords: ['rsi', 'macd', '기술적', '과매수', '과매도', '이동평균'], indicatorIds: [10, 40] },
  { keywords: ['실적', 'eps', '매출', '영업이익', '순이익', 'earnings', '분기 실적'], indicatorIds: [5, 50, 57, 58] },
  { keywords: ['per', 'pbr', '밸류에이션', '저평가', '고평가', '가치'], indicatorIds: [50, 51] },
  { keywords: ['roe', 'roa', '수익성', '이익률'], indicatorIds: [52, 53, 57] },
  { keywords: ['부채', '레버리지', 'debt', '재무건전'], indicatorIds: [54] },
  { keywords: ['배당', 'dividend', '현금흐름', 'fcf'], indicatorIds: [55, 56] },
  { keywords: ['인플레', 'cpi', '물가', '소비자물가'], indicatorIds: [33] },
  { keywords: ['고용', '실업', 'nfp', '비농업', '일자리'], indicatorIds: [31, 32] },
  { keywords: ['gdp', '성장', '경기', '산업생산'], indicatorIds: [34, 35] },
  { keywords: ['주택', '부동산', '모기지', 'reit'], indicatorIds: [36, 37] },
  { keywords: ['뉴스', '센티먼트', '심리', '여론', '규제', '정책', '정치', '선거'], indicatorIds: [11, 8] },
  { keywords: ['반도체', '테크', 'ai', '엔비디아', 'nvidia', '칩'], indicatorIds: [12, 3] },
  { keywords: ['중국', '항셍', '홍콩'], indicatorIds: [16] },
  { keywords: ['일본', '니케이', '엔화'], indicatorIds: [15] },
  { keywords: ['광고', '디지털', '플랫폼', 'meta', '구글', 'google'], indicatorIds: [3, 12] },
]

/**
 * 전제 텍스트 목록에서 관련 지표 ID를 추출 (이미 선택된 것 제외).
 */
function findRelatedIndicatorIds(premiseTexts: string[], alreadySelectedIds: number[]): number[] {
  const excludeSet = new Set(alreadySelectedIds)
  const scoredIds = new Map<number, number>() // id → 매칭 횟수

  const allText = premiseTexts.join(' ').toLowerCase()

  for (const rule of KEYWORD_INDICATOR_MAP) {
    for (const keyword of rule.keywords) {
      if (allText.includes(keyword.toLowerCase())) {
        for (const id of rule.indicatorIds) {
          if (!excludeSet.has(id)) {
            scoredIds.set(id, (scoredIds.get(id) ?? 0) + 1)
          }
        }
        break // 한 rule에서 첫 keyword 매칭이면 충분
      }
    }
  }

  // 매칭 횟수 높은 순으로 정렬
  return [...scoredIds.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id)
}

interface AddIndicatorSheetProps {
  isOpen: boolean
  onClose: () => void
  selectedIds: number[]
  onToggle: (id: number, name: string) => void
  premiseTexts?: string[]  // 현재 전제 텍스트 (관련 지표 추천용)
}

export function AddIndicatorSheet({
  isOpen, onClose, selectedIds, onToggle, premiseTexts = [],
}: AddIndicatorSheetProps) {
  // 관련 지표 추천
  const relatedIds = premiseTexts.length > 0
    ? findRelatedIndicatorIds(premiseTexts, selectedIds)
    : []
  const relatedIndicators = relatedIds
    .map(id => INDICATOR_CATALOG.find(ind => ind.id === id))
    .filter((ind): ind is (typeof INDICATOR_CATALOG)[number] => ind != null)

  // 추천 지표에 포함된 ID (나머지 카탈로그에서 제외)
  const relatedIdSet = new Set(relatedIds)

  const byCategory: Record<string, typeof INDICATOR_CATALOG> = {}
  for (const ind of INDICATOR_CATALOG) {
    if (relatedIdSet.has(ind.id)) continue // 추천에 이미 있으면 카탈로그에서 제외
    if (!byCategory[ind.category]) byCategory[ind.category] = []
    byCategory[ind.category].push(ind)
  }

  const categoryOrder = [
    '수급', '주요 지수', '원자재', '암호화폐',
    '금리', '환율/변동성', '고용/성장', '물가/주택',
    '기술적', '펀더멘털', '심리',
  ]

  function renderButton(ind: { id: number; name: string }, highlight?: boolean) {
    const isSelected = selectedIds.includes(ind.id)
    return (
      <button
        key={ind.id}
        onClick={() => onToggle(ind.id, ind.name)}
        className={`flex items-center justify-between px-2.5 py-2
                   rounded-lg text-left text-xs transition-colors
                   ${isSelected
                     ? 'bg-blue-900/30 border border-blue-500/50 text-blue-300'
                     : highlight
                       ? 'bg-gray-800 border border-gray-600 text-gray-200 hover:border-blue-500/50'
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
  }

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="지표 추가">
      <div className="space-y-4 max-h-[60vh] overflow-y-auto">
        {/* 전제 기반 추천 지표 */}
        {relatedIndicators.length > 0 && (
          <div>
            <p className="text-xs text-blue-400 mb-2 sticky top-0 bg-gray-950 py-1
                          flex items-center gap-1">
              <Sparkles size={12} />
              전제 관련 추천
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {relatedIndicators.map(ind => renderButton(ind, true))}
            </div>
          </div>
        )}

        {/* 전체 지표 카탈로그 */}
        {categoryOrder.map((category) => {
          const indicators = byCategory[category]
          if (!indicators || indicators.length === 0) return null
          return (
            <div key={category}>
              <p className="text-xs text-gray-500 mb-2 sticky top-0 bg-gray-950 py-1">{category}</p>
              <div className="grid grid-cols-2 gap-1.5">
                {indicators.map(ind => renderButton(ind))}
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
