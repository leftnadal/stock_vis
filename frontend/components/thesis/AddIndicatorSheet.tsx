'use client'

import { Plus, Check, Sparkles } from 'lucide-react'
import { BottomSheet } from '@/components/thesis/common/BottomSheet'

// INDICATOR_CATALOG 미러 (prompt_builder.py와 동기화)
type Frequency = '일간' | '주간' | '월간' | '분기'
interface CatalogIndicator {
  id: number
  name: string
  category: string
  freq: Frequency
}

const INDICATOR_CATALOG: CatalogIndicator[] = [
  // 시장 데이터: 수급
  { id: 1, name: '외국인 순매수 추이', category: '수급', freq: '일간' },
  { id: 2, name: '기관 순매수 추이', category: '수급', freq: '일간' },
  // 시장 데이터: 주요 지수
  { id: 3, name: 'S&P 500', category: '주요 지수', freq: '일간' },
  { id: 4, name: 'KOSPI 지수', category: '주요 지수', freq: '일간' },
  { id: 12, name: 'NASDAQ', category: '주요 지수', freq: '일간' },
  { id: 13, name: '다우존스', category: '주요 지수', freq: '일간' },
  { id: 14, name: '코스닥 지수', category: '주요 지수', freq: '일간' },
  { id: 15, name: '니케이 225', category: '주요 지수', freq: '일간' },
  { id: 16, name: '항셍 지수', category: '주요 지수', freq: '일간' },
  // 원자재/상품
  { id: 20, name: '금 (Gold)', category: '원자재', freq: '일간' },
  { id: 21, name: '원유 (WTI)', category: '원자재', freq: '일간' },
  { id: 22, name: '은 (Silver)', category: '원자재', freq: '일간' },
  { id: 23, name: '구리 (Copper)', category: '원자재', freq: '일간' },
  { id: 24, name: '천연가스', category: '원자재', freq: '일간' },
  // 암호화폐
  { id: 25, name: '비트코인 (BTC)', category: '암호화폐', freq: '일간' },
  { id: 26, name: '이더리움 (ETH)', category: '암호화폐', freq: '일간' },
  // 거시경제: 금리
  { id: 6, name: '미국 기준금리 (Fed Funds Rate)', category: '금리', freq: '주간' },
  { id: 7, name: '미국 10년 국채 금리', category: '금리', freq: '일간' },
  { id: 30, name: '미국 2년 국채 금리', category: '금리', freq: '일간' },
  { id: 37, name: '30년 모기지 금리', category: '금리', freq: '주간' },
  // 거시경제: 환율/변동성
  { id: 8, name: 'VIX (공포지수)', category: '환율/변동성', freq: '일간' },
  { id: 9, name: '원/달러 환율', category: '환율/변동성', freq: '일간' },
  { id: 38, name: '달러/유로 환율', category: '환율/변동성', freq: '일간' },
  { id: 39, name: '달러 인덱스 (DXY)', category: '환율/변동성', freq: '일간' },
  // 거시경제: 고용/성장/물가
  { id: 31, name: '실업률', category: '고용/성장', freq: '월간' },
  { id: 32, name: '비농업 고용 (NFP)', category: '고용/성장', freq: '월간' },
  { id: 34, name: '실질 GDP', category: '고용/성장', freq: '분기' },
  { id: 35, name: '산업생산지수', category: '고용/성장', freq: '월간' },
  { id: 33, name: '소비자물가지수 (CPI)', category: '물가/주택', freq: '월간' },
  { id: 36, name: '주택착공건수', category: '물가/주택', freq: '월간' },
  // 기술적
  { id: 10, name: 'RSI (14일)', category: '기술적', freq: '일간' },
  { id: 40, name: 'MACD', category: '기술적', freq: '일간' },
  { id: 41, name: '스토캐스틱 %K', category: '기술적', freq: '일간' },
  { id: 42, name: '볼린저 밴드 %B', category: '기술적', freq: '일간' },
  { id: 43, name: 'ATR (평균진폭)', category: '기술적', freq: '일간' },
  { id: 44, name: 'OBV (거래량 누적)', category: '기술적', freq: '일간' },
  { id: 45, name: 'SMA 50일', category: '기술적', freq: '일간' },
  { id: 46, name: 'SMA 200일', category: '기술적', freq: '일간' },
  { id: 47, name: 'EMA 12일', category: '기술적', freq: '일간' },
  // 펀더멘털
  { id: 5, name: 'EPS 추이', category: '펀더멘털', freq: '분기' },
  { id: 50, name: 'PER (주가수익비율)', category: '펀더멘털', freq: '분기' },
  { id: 51, name: 'PBR (주가순자산비율)', category: '펀더멘털', freq: '분기' },
  { id: 52, name: 'ROE (자기자본이익률)', category: '펀더멘털', freq: '분기' },
  { id: 53, name: 'ROA (총자산이익률)', category: '펀더멘털', freq: '분기' },
  { id: 54, name: '부채비율 (Debt/Equity)', category: '펀더멘털', freq: '분기' },
  { id: 55, name: '잉여현금흐름 (FCF)', category: '펀더멘털', freq: '분기' },
  { id: 56, name: '배당수익률', category: '펀더멘털', freq: '분기' },
  { id: 57, name: '영업이익률', category: '펀더멘털', freq: '분기' },
  { id: 58, name: '매출성장률 (YoY)', category: '펀더멘털', freq: '분기' },
  // 펀더멘털 (재무 체질)
  { id: 60, name: '매출총이익률 (Gross Margin)', category: '재무 체질', freq: '분기' },
  { id: 61, name: '순이익률 (Net Margin)', category: '재무 체질', freq: '분기' },
  { id: 62, name: 'ROIC (투하자본이익률)', category: '재무 체질', freq: '분기' },
  { id: 63, name: '유동비율 (Current Ratio)', category: '재무 체질', freq: '분기' },
  { id: 64, name: '이자보상배율', category: '재무 체질', freq: '분기' },
  { id: 65, name: '순부채/EBITDA', category: '재무 체질', freq: '분기' },
  { id: 66, name: 'FCF 마진', category: '재무 체질', freq: '분기' },
  { id: 67, name: 'EV/EBITDA', category: '밸류에이션', freq: '분기' },
  { id: 68, name: 'FCF 수익률', category: '밸류에이션', freq: '분기' },
  { id: 69, name: '영업이익 성장률', category: '성장', freq: '분기' },
  { id: 70, name: '매출채권 회전일수 (DSO)', category: '운영 효율', freq: '분기' },
  { id: 71, name: '총자산회전율', category: '운영 효율', freq: '분기' },
  { id: 72, name: '발생액 비율 (Accruals)', category: '이익 품질', freq: '분기' },
  { id: 73, name: '순주주수익률', category: '주주환원', freq: '분기' },
  // 심리
  { id: 11, name: '뉴스 센티먼트', category: '심리', freq: '일간' },
]

const INDICATOR_BY_ID = new Map(INDICATOR_CATALOG.map(i => [i.id, i]))

const FREQ_STYLE: Record<Frequency, string> = {
  '일간': 'text-emerald-400 bg-emerald-900/30',
  '주간': 'text-blue-400 bg-blue-900/30',
  '월간': 'text-amber-400 bg-amber-900/30',
  '분기': 'text-gray-400 bg-gray-800',
}

// 키워드 → 지표 ID + 추천 이유
interface KeywordRule {
  keywords: string[]
  indicatorIds: number[]
  reason: string // 왜 이 지표가 관련있는지
}

const KEYWORD_INDICATOR_MAP: KeywordRule[] = [
  { keywords: ['외국인', '외인', '순매수', '순매도', 'foreign'], indicatorIds: [1], reason: '외국인 수급 변화 직접 추적' },
  { keywords: ['기관', '기관투자자', '연기금', '보험', '자산운용'], indicatorIds: [2], reason: '기관 매매 동향 직접 추적' },
  { keywords: ['금리', '연준', 'fomc', 'fed', '기준금리', '금리인하', '금리인상', '이자율', '통화정책'], indicatorIds: [6, 7, 30], reason: '금리 변동이 유동성과 할인율에 영향' },
  { keywords: ['vix', '공포', '변동성', '리스크', '불확실'], indicatorIds: [8], reason: '시장 불확실성/공포 수준 측정' },
  { keywords: ['환율', '달러', '원달러', 'usd', 'krw', '원화', '강달러', '약달러'], indicatorIds: [9, 39], reason: '환율 변동이 수출입/자금흐름에 영향' },
  { keywords: ['s&p', 's&p500', '나스닥', 'nasdaq', '미국시장', '미국 주식', '월가'], indicatorIds: [3, 12], reason: '글로벌 위험선호도 바로미터' },
  { keywords: ['코스피', 'kospi', '한국시장', '종합주가'], indicatorIds: [4], reason: '한국 시장 전체 방향 추적' },
  { keywords: ['유가', '원유', 'wti', '석유', '에너지', 'opec', '오일'], indicatorIds: [21], reason: '에너지 비용/원자재 가격 직접 추적' },
  { keywords: ['금', 'gold', '금값', '안전자산'], indicatorIds: [20], reason: '안전자산 선호도/인플레 헤지 지표' },
  { keywords: ['구리', 'copper', '산업금속', '경기선행'], indicatorIds: [23], reason: '산업 수요 선행 지표 (Dr. Copper)' },
  { keywords: ['천연가스', 'lng', '가스'], indicatorIds: [24], reason: '에너지 비용 변동 추적' },
  { keywords: ['비트코인', 'btc', '암호화폐', '크립토', '코인'], indicatorIds: [25, 26], reason: '위험자산 선호도/유동성 지표' },
  { keywords: ['rsi', 'macd', '기술적', '과매수', '과매도', '이동평균'], indicatorIds: [10, 40], reason: '단기 과매수/과매도 상태 파악' },
  { keywords: ['실적', 'eps', '매출', '영업이익', '순이익', 'earnings', '분기 실적'], indicatorIds: [5, 50, 57, 58, 60, 61, 69], reason: '기업 수익성과 성장 추적' },
  { keywords: ['per', 'pbr', '밸류에이션', '저평가', '고평가', '가치'], indicatorIds: [50, 51, 67, 68], reason: '현재 주가 수준의 적정성 판단' },
  { keywords: ['roe', 'roa', '수익성', '이익률', 'roic', '마진'], indicatorIds: [52, 53, 57, 62, 60, 61], reason: '자본 효율성/수익성 추적' },
  { keywords: ['부채', '레버리지', 'debt', '재무건전', '유동성', '현금'], indicatorIds: [54, 63, 64, 65], reason: '재무 건전성/유동성 리스크 모니터링' },
  { keywords: ['배당', 'dividend', '현금흐름', 'fcf', '자사주', '주주환원'], indicatorIds: [55, 56, 66, 68, 73], reason: '주주환원/현금창출 능력 추적' },
  { keywords: ['회전율', '효율', '재고', '매출채권', '운영'], indicatorIds: [70, 71], reason: '운영 효율성/자산 활용도 추적' },
  { keywords: ['이익 품질', '발생액', 'accrual', '분식', '회계'], indicatorIds: [72, 66], reason: '이익 품질 — 현금 뒷받침 여부 확인' },
  { keywords: ['인플레', 'cpi', '물가', '소비자물가'], indicatorIds: [33], reason: '물가 상승이 소비/금리에 영향' },
  { keywords: ['고용', '실업', 'nfp', '비농업', '일자리'], indicatorIds: [31, 32], reason: '경기 과열/침체 판단 핵심 지표' },
  { keywords: ['gdp', '성장', '경기', '산업생산'], indicatorIds: [34, 35], reason: '경제 성장 속도 직접 측정' },
  { keywords: ['주택', '부동산', '모기지', 'reit'], indicatorIds: [36, 37], reason: '부동산 경기/금리 민감도 추적' },
  { keywords: ['뉴스', '센티먼트', '심리', '여론', '규제', '정책', '정치', '선거'], indicatorIds: [11, 8], reason: '시장 심리/불확실성 변화 감지' },
  { keywords: ['반도체', '테크', 'ai', '엔비디아', 'nvidia', '칩'], indicatorIds: [12, 3], reason: '기술주 동향이 섹터 전체에 영향' },
  { keywords: ['중국', '항셍', '홍콩'], indicatorIds: [16], reason: '중국 시장 리스크/기회 직접 추적' },
  { keywords: ['일본', '니케이', '엔화'], indicatorIds: [15], reason: '일본 경제/엔캐리 트레이드 영향' },
  { keywords: ['광고', '디지털', '플랫폼', 'meta', '구글', 'google'], indicatorIds: [3, 12], reason: '빅테크 주가가 광고 시장 전망 반영' },
]

interface RelatedIndicator {
  id: number
  premiseHint: string  // 어떤 전제 때문에 추천되었는지
  reason: string       // 이 지표가 그 전제와 어떤 관계인지
  score: number
}

/**
 * 전제 텍스트에서 관련 지표 ID + 문맥적 이유를 추출 (이미 선택된 것 제외).
 * 각 전제를 개별 매칭하여 "어떤 전제 → 어떤 지표" 연결을 유지.
 */
function findRelatedIndicators(premiseTexts: string[], alreadySelectedIds: number[]): RelatedIndicator[] {
  const excludeSet = new Set(alreadySelectedIds)
  const resultMap = new Map<number, RelatedIndicator>()

  for (const premiseText of premiseTexts) {
    const textLower = premiseText.toLowerCase()
    const premiseHint = premiseText.length > 30
      ? premiseText.slice(0, 30) + '…'
      : premiseText

    for (const rule of KEYWORD_INDICATOR_MAP) {
      let matched = false
      for (const keyword of rule.keywords) {
        if (textLower.includes(keyword.toLowerCase())) {
          matched = true
          break
        }
      }
      if (!matched) continue

      for (const id of rule.indicatorIds) {
        if (excludeSet.has(id)) continue
        const existing = resultMap.get(id)
        if (existing) {
          existing.score += 1
        } else {
          resultMap.set(id, { id, premiseHint, reason: rule.reason, score: 1 })
        }
      }
    }
  }

  return [...resultMap.values()].sort((a, b) => b.score - a.score)
}

interface AddIndicatorSheetProps {
  isOpen: boolean
  onClose: () => void
  selectedIds: number[]
  onToggle: (id: number, name: string) => void
  premiseTexts?: string[]
}

export function AddIndicatorSheet({
  isOpen, onClose, selectedIds, onToggle, premiseTexts = [],
}: AddIndicatorSheetProps) {
  const relatedItems = premiseTexts.length > 0
    ? findRelatedIndicators(premiseTexts, selectedIds)
    : []
  const relatedIdSet = new Set(relatedItems.map(r => r.id))
  const relatedDataMap = new Map(relatedItems.map(r => [r.id, r]))

  const byCategory: Record<string, CatalogIndicator[]> = {}
  for (const ind of INDICATOR_CATALOG) {
    if (relatedIdSet.has(ind.id)) continue
    if (!byCategory[ind.category]) byCategory[ind.category] = []
    byCategory[ind.category].push(ind)
  }

  const categoryOrder = [
    '수급', '주요 지수', '원자재', '암호화폐',
    '금리', '환율/변동성', '고용/성장', '물가/주택',
    '기술적', '펀더멘털', '재무 체질', '밸류에이션', '성장',
    '운영 효율', '이익 품질', '주주환원', '심리',
  ]

  function renderButton(ind: CatalogIndicator, context?: { premiseHint: string; reason: string }) {
    const isSelected = selectedIds.includes(ind.id)
    const freqStyle = FREQ_STYLE[ind.freq]

    return (
      <button
        key={ind.id}
        onClick={() => onToggle(ind.id, ind.name)}
        className={`flex flex-col items-start px-2.5 py-2 gap-1
                   rounded-lg text-left text-xs transition-colors
                   ${isSelected
                     ? 'bg-blue-900/30 border border-blue-500/50'
                     : context
                       ? 'bg-gray-800 border border-gray-600 hover:border-blue-500/50'
                       : 'bg-gray-900 border border-gray-800 hover:border-gray-600'
                   }`}
      >
        <div className="flex items-center justify-between w-full gap-1">
          <span className={`truncate font-medium ${isSelected ? 'text-blue-300' : 'text-gray-200'}`}>
            {ind.name}
          </span>
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className={`text-[9px] px-1 py-px rounded ${freqStyle}`}>
              {ind.freq}
            </span>
            {isSelected
              ? <Check size={12} className="text-blue-400" />
              : <Plus size={12} className="text-gray-600" />
            }
          </div>
        </div>
        {context && (
          <div className="space-y-0.5 w-full">
            <span className="text-[10px] text-blue-400/70 leading-tight block truncate">
              「{context.premiseHint}」
            </span>
            <span className="text-[10px] text-gray-500 leading-tight block">
              {context.reason}
            </span>
          </div>
        )}
      </button>
    )
  }

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="지표 추가">
      <div className="space-y-4 max-h-[60vh] overflow-y-auto">
        {/* 전제 기반 추천 */}
        {relatedItems.length > 0 && (
          <div>
            <p className="text-xs text-blue-400 mb-2 sticky top-0 bg-gray-950 py-1
                          flex items-center gap-1">
              <Sparkles size={12} />
              전제 관련 추천
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {relatedItems.map(({ id }) => {
                const ind = INDICATOR_BY_ID.get(id)
                if (!ind) return null
                const data = relatedDataMap.get(id)
                return renderButton(ind, data ? { premiseHint: data.premiseHint, reason: data.reason } : undefined)
              })}
            </div>
          </div>
        )}

        {/* 전체 카탈로그 */}
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
