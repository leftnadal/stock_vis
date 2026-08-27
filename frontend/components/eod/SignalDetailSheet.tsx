'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { X, ChevronDown, TrendingUp, AlertTriangle, Layers, ArrowRight } from 'lucide-react';
import { StockRow } from './StockRow';
import { ScannerFilterBar } from './ScannerFilterBar';
import { getAxisCount, type ConfluenceMap } from './confluence';
import {
  applyScannerFilters,
  sortScannerStocks,
  availableSectors,
  DEFAULT_SCANNER_FILTERS,
  type ScannerFilters,
  type ScannerSort,
} from './scannerFilters';
import { useSignalDetail } from '@/hooks/useEODDashboard';
import { SIGNAL_CATEGORY_COLORS, SIGNAL_CATEGORY_LABELS } from '@/types/eod';
import type { SignalCard, SignalStock } from '@/types/eod';

interface SignalDetailSheetProps {
  card: SignalCard;
  onClose: () => void;
  /** 전 카드 합류 지도(useConfluenceMap). 미로딩=undefined → 합류 칩/필터/정렬 자연 비활성(정칙 ⑴). */
  confluenceMap?: ConfluenceMap;
}

// 정직성 한 줄(고정·D-SCANNER-SELECT-UX). 매매 암시 금지.
const HONESTY_LINE = '신호는 주목 후보를 고르는 렌즈이며 수익을 보장하지 않습니다.';

export function SignalDetailSheet({ card, onClose, confluenceMap }: SignalDetailSheetProps) {
  const [filters, setFilters] = useState<ScannerFilters>(DEFAULT_SCANNER_FILTERS);
  const [sortBy, setSortBy] = useState<ScannerSort>('confluence');
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

  // detail에서 종목/정렬 리스트 가져오기 (fallback: preview_stocks)
  const extractSymbols = (list: (string | SignalStock)[]): string[] =>
    list.map((item) => (typeof item === 'string' ? item : item.symbol));

  const stocks = detail?.stocks_by_score ?? card.preview_stocks;
  const rankLists = {
    volume: extractSymbols(detail?.stocks_by_volume ?? card.rank_by_volume),
    return: extractSymbols(detail?.stocks_by_return ?? card.rank_by_return),
    market_cap: extractSymbols(detail?.stocks_by_market_cap ?? card.rank_by_market_cap),
  };

  const sectors = availableSectors(stocks);
  const filteredStocks = applyScannerFilters(stocks, filters, confluenceMap);
  const sortedStocks = sortScannerStocks(filteredStocks, sortBy, confluenceMap, rankLists);

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

        {/* 필터 바 + 정렬 (합류순·거래량·수익률·시총) — 총 N종목은 바 하단 표기 */}
        <ScannerFilterBar
          filters={filters}
          onFiltersChange={setFilters}
          sort={sortBy}
          onSortChange={setSortBy}
          sectors={sectors}
          resultCount={sortedStocks.length}
          totalCount={stocks.length}
        />

        {/* 종목 리스트 */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {isLoading ? (
            <div className="space-y-2 px-3 py-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-[72px] bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : sortedStocks.length === 0 ? (
            <p className="px-4 py-8 text-center text-xs text-gray-400 dark:text-gray-500">
              필터 조건에 맞는 종목이 없습니다.
            </p>
          ) : (
            <div key={`${sortBy}-${filters.minAxes}-${filters.sector}`} className="animate-fadeIn">
              {sortedStocks.map((stock) => (
                <StockRow
                  key={stock.symbol}
                  stock={stock}
                  axisCount={getAxisCount(confluenceMap, stock.symbol)}
                />
              ))}
            </div>
          )}
        </div>

        {/* 축 커버리지 명시(정칙 ⑴ 정보판) + 정직성 한 줄(고정) */}
        <div className="px-5 py-2.5 border-t border-gray-100 dark:border-gray-700 flex-shrink-0 bg-gray-50/70 dark:bg-gray-800/50">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 leading-relaxed">
            이 화면 축: <span className="font-medium">기술 합류 · 섹터 · 뉴스 · 기술(RSI·52주·이동평균)</span>
            <span className="text-gray-400 dark:text-gray-500"> · 미커버(곧): 가치평가 · 퀄리티 · 관계</span>
          </p>
          <p className="mt-1 text-[10px] italic text-gray-400 dark:text-gray-500">{HONESTY_LINE}</p>
        </div>
      </div>
    </div>
  );
}
