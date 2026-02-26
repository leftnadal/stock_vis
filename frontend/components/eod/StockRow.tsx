'use client';

import Link from 'next/link';
import { ArrowUpRight, ArrowDownRight, Network } from 'lucide-react';
import { MiniSparkline } from './MiniSparkline';
import { NewsContextBadge } from './NewsContextBadge';
import { ConfidenceBadge } from './ConfidenceBadge';
import type { SignalStock } from '@/types/eod';

interface StockRowProps {
  stock: SignalStock;
}

function formatPrice(price: number): string {
  if (price >= 1000) {
    return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (price >= 1) return price.toFixed(2);
  return price.toFixed(4);
}

function formatVolume(volume: number): string {
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(0)}K`;
  return volume.toString();
}

export function StockRow({ stock }: StockRowProps) {
  const isPositive = stock.change_percent >= 0;

  return (
    <div className="group px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700/40 rounded-lg transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-600">
      {/* 상단 행: 종목 + 스파크라인 + 가격 */}
      <div className="flex items-center gap-2">
        {/* 종목 정보 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <Link
              href={`/stocks/${stock.symbol}`}
              className="text-sm font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              {stock.symbol}
            </Link>
            {stock.chain_sight_cta && (
              <span title="Chain Sight 연계 분석 가능">
                <Network className="w-3 h-3 text-purple-500 dark:text-purple-400" />
              </span>
            )}
            <ConfidenceBadge score={stock.composite_score} />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[140px]">
            {stock.company_name}
          </p>
        </div>

        {/* 스파크라인 */}
        <div className="flex-shrink-0">
          <MiniSparkline data={stock.mini_chart_20d} width={64} height={24} />
        </div>

        {/* 가격 */}
        <div className="text-right flex-shrink-0 min-w-[72px]">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            ${formatPrice(stock.close_price)}
          </p>
          <div
            className={`inline-flex items-center gap-0.5 text-xs font-semibold ${
              isPositive
                ? 'text-green-600 dark:text-green-400'
                : 'text-red-600 dark:text-red-400'
            }`}
          >
            {isPositive ? (
              <ArrowUpRight className="w-3 h-3" />
            ) : (
              <ArrowDownRight className="w-3 h-3" />
            )}
            {Math.abs(stock.change_percent).toFixed(2)}%
          </div>
        </div>
      </div>

      {/* 시그널 레이블 + 거래량 */}
      <div className="flex items-center justify-between mt-1 mb-1.5">
        <span className="text-[11px] text-blue-600 dark:text-blue-400 font-medium">
          {stock.signal_label}
        </span>
        <span className="text-[11px] text-gray-400 dark:text-gray-500">
          거래량 {formatVolume(stock.volume)}
        </span>
      </div>

      {/* 뉴스 컨텍스트 */}
      {stock.news_context?.headline && (
        <NewsContextBadge news={stock.news_context} />
      )}
    </div>
  );
}
