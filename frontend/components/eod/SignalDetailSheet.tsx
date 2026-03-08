'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { X, ChevronDown, TrendingUp, AlertTriangle, Layers, ArrowRight } from 'lucide-react';
import { StockRow } from './StockRow';
import { useSignalDetail } from '@/hooks/useEODDashboard';
import { SIGNAL_CATEGORY_COLORS, SIGNAL_CATEGORY_LABELS } from '@/types/eod';
import type { SignalCard, SignalStock, SortOption } from '@/types/eod';

interface SignalDetailSheetProps {
  card: SignalCard;
  onClose: () => void;
}

const SORT_LABELS: Record<SortOption, string> = {
  volume: '거래량 순',
  return: '수익률 순',
  market_cap: '시가총액 순',
};

function sortStocks(
  stocks: SignalStock[],
  rankBy: SortOption,
  rankByVolume: string[],
  rankByReturn: string[],
  rankByMarketCap: string[]
): SignalStock[] {
  const getRankList = (sort: SortOption): string[] => {
    if (sort === 'volume') return rankByVolume;
    if (sort === 'return') return rankByReturn;
    return rankByMarketCap;
  };

  const rankList = getRankList(rankBy);
  if (rankList.length === 0) return stocks;

  const rankMap = new Map(rankList.map((sym, idx) => [sym, idx]));
  return [...stocks].sort((a, b) => {
    const ra = rankMap.has(a.symbol) ? rankMap.get(a.symbol)! : 9999;
    const rb = rankMap.has(b.symbol) ? rankMap.get(b.symbol)! : 9999;
    return ra - rb;
  });
}

export function SignalDetailSheet({ card, onClose }: SignalDetailSheetProps) {
  const [sortBy, setSortBy] = useState<SortOption>('volume');
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [showTip, setShowTip] = useState(false);
  const sheetRef = useRef<HTMLDivElement>(null);

  const { data: detail, isLoading } = useSignalDetail(card.id);

  const categoryColor = SIGNAL_CATEGORY_COLORS[card.category] ?? card.color;
  const categoryLabel = SIGNAL_CATEGORY_LABELS[card.category];

  // ESC 키 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // body scroll lock
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  // 오버레이 클릭 닫기
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  // detail에서 정렬별 종목 가져오기 (fallback: preview_stocks)
  const extractSymbols = (list: (string | SignalStock)[]): string[] =>
    list.map((item) => (typeof item === 'string' ? item : item.symbol));

  const stocks = detail?.stocks_by_score ?? card.preview_stocks;
  const rankByVolume = extractSymbols(detail?.stocks_by_volume ?? card.rank_by_volume);
  const rankByReturn = extractSymbols(detail?.stocks_by_return ?? card.rank_by_return);
  const rankByMarketCap = extractSymbols(detail?.stocks_by_market_cap ?? card.rank_by_market_cap);

  const sortedStocks = sortStocks(stocks, sortBy, rankByVolume, rankByReturn, rankByMarketCap);

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end md:justify-center md:items-end bg-black/50 backdrop-blur-sm"
      onClick={handleOverlayClick}
    >
      {/* 시트 패널 */}
      <div
        ref={sheetRef}
        className="
          w-full md:w-[420px] md:h-full
          bg-white dark:bg-gray-900
          rounded-t-2xl md:rounded-none
          shadow-2xl flex flex-col
          max-h-[90vh] md:max-h-full
          animate-slide-up md:animate-slide-right
        "
        onClick={(e) => e.stopPropagation()}
      >
        {/* 모바일 드래그 핸들 */}
        <div className="flex justify-center pt-2 pb-1 md:hidden">
          <div className="w-10 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />
        </div>

        {/* 헤더 */}
        <div
          className="flex items-start justify-between px-5 pt-5 pb-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0"
          style={{ borderTop: `3px solid ${categoryColor}` }}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span
                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: categoryColor }}
              />
              <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                {categoryLabel}
              </span>
              <span
                className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[11px] font-bold text-white"
                style={{ backgroundColor: categoryColor }}
              >
                {card.count}
              </span>
            </div>
            <h2 className="text-base font-bold text-gray-900 dark:text-white leading-tight">
              {card.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="ml-3 p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
          >
            <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* 교육 팁 (기본 접기) */}
        {(card.education_tip || card.education_risk) && (
          <div className="border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
            <button
              onClick={() => setShowTip((prev) => !prev)}
              className="w-full flex items-center justify-between px-5 py-2.5 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
            >
              <span className="font-medium">투자 팁</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${showTip ? 'rotate-180' : ''}`} />
            </button>
            {showTip && (
              <div className="px-5 pb-3 bg-gray-50 dark:bg-gray-800/50">
                {card.education_tip && (
                  <div className="flex items-start gap-2 mb-1">
                    <TrendingUp className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                      {card.education_tip}
                    </p>
                  </div>
                )}
                {card.education_risk && (
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-amber-600 dark:text-amber-400 leading-relaxed">
                      {card.education_risk}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Chain Sight 섹터 정보 */}
        {card.chain_sight_sectors.length > 0 && (
          <div className="px-5 py-2.5 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
            <div className="flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-purple-500" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Chain Sight 연계:</span>
              <div className="flex flex-wrap gap-1 flex-1">
                {card.chain_sight_sectors.map((sector) => (
                  <Link
                    key={sector}
                    href={`/stocks?sector=${encodeURIComponent(sector)}`}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 border border-purple-100 dark:border-purple-800 hover:bg-purple-100 dark:hover:bg-purple-800/30 cursor-pointer transition-colors"
                  >
                    {sector}
                  </Link>
                ))}
              </div>
              {sortedStocks.length > 0 && (
                <Link
                  href={`/stocks/${sortedStocks[0].symbol}?tab=chain-sight`}
                  className="inline-flex items-center gap-0.5 text-[10px] text-purple-600 dark:text-purple-400 hover:text-purple-700 font-medium whitespace-nowrap"
                >
                  관계 지도
                  <ArrowRight className="w-3 h-3" />
                </Link>
              )}
            </div>
          </div>
        )}

        {/* 정렬 옵션 */}
        <div className="px-5 py-2.5 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between flex-shrink-0">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            총 {sortedStocks.length}종목
          </span>
          <div className="relative">
            <button
              onClick={() => setShowSortMenu((prev) => !prev)}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              {SORT_LABELS[sortBy]}
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showSortMenu ? 'rotate-180' : ''}`} />
            </button>
            {showSortMenu && (
              <div className="absolute right-0 top-full mt-1 z-20 w-36 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg overflow-hidden">
                {(Object.keys(SORT_LABELS) as SortOption[]).map((option) => (
                  <button
                    key={option}
                    onClick={() => { setSortBy(option); setShowSortMenu(false); }}
                    className={`
                      w-full text-left px-3 py-2 text-xs transition-colors
                      ${sortBy === option
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 font-semibold'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }
                    `}
                  >
                    {SORT_LABELS[option]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 종목 리스트 */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {isLoading ? (
            <div className="space-y-2 px-3 py-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-[72px] bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : (
            <div key={sortBy} className="animate-fadeIn">
              {sortedStocks.map((stock) => (
                <StockRow key={stock.symbol} stock={stock} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
