'use client';

import Link from 'next/link';
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import { ChainSightStock } from '@/types/chainSight';

interface RelatedStockCardProps {
  stock: ChainSightStock;
  onClick?: () => void;
}

/**
 * 관련 종목 카드 컴포넌트
 *
 * 종목 정보를 카드 형태로 표시합니다.
 * 클릭 시 해당 종목 페이지로 이동합니다.
 */
export default function RelatedStockCard({ stock, onClick }: RelatedStockCardProps) {
  const isPositive = (stock.change_percent ?? 0) >= 0;
  const changePercent = stock.change_percent?.toFixed(2) ?? '-';

  // 시가총액 포맷팅
  const formatMarketCap = (mc: number | null) => {
    if (!mc) return '-';
    if (mc >= 1e12) return `$${(mc / 1e12).toFixed(1)}T`;
    if (mc >= 1e9) return `$${(mc / 1e9).toFixed(1)}B`;
    if (mc >= 1e6) return `$${(mc / 1e6).toFixed(1)}M`;
    return `$${mc.toFixed(0)}`;
  };

  // 강도 표시 (0.0 ~ 1.0 -> 진한 색상)
  const strengthOpacity = Math.max(0.3, stock.strength);

  return (
    <Link
      href={`/stocks/${stock.symbol}`}
      onClick={onClick}
      className="group block rounded-lg border border-gray-200 bg-white p-4 transition-all hover:border-blue-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-500"
    >
      <div className="flex items-start justify-between">
        {/* 왼쪽: 종목 정보 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              {stock.symbol}
            </span>
            {/* 강도 인디케이터 */}
            <div
              className="h-2 w-2 rounded-full bg-blue-500"
              style={{ opacity: strengthOpacity }}
              title={`관계 강도: ${(stock.strength * 100).toFixed(0)}%`}
            />
          </div>
          <p className="mt-1 truncate text-sm text-gray-600 dark:text-gray-400">
            {stock.company_name}
          </p>
          {stock.sector && (
            <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-500">
              {stock.sector}
            </p>
          )}
        </div>

        {/* 오른쪽: 가격 정보 */}
        <div className="flex flex-col items-end">
          <span className="text-lg font-semibold text-gray-900 dark:text-white">
            ${stock.current_price?.toFixed(2) ?? '-'}
          </span>
          <div
            className={`flex items-center gap-1 text-sm ${
              isPositive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {isPositive ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            <span>
              {isPositive ? '+' : ''}
              {changePercent}%
            </span>
          </div>
        </div>
      </div>

      {/* 하단: 추가 정보 + 이동 힌트 */}
      <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3 dark:border-gray-700">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          시가총액: {formatMarketCap(stock.market_cap)}
        </span>
        <span className="flex items-center gap-1 text-xs text-blue-500 opacity-0 transition-opacity group-hover:opacity-100">
          탐험하기
          <ArrowRight className="h-3 w-3" />
        </span>
      </div>
    </Link>
  );
}
