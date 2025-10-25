'use client';

import Link from 'next/link';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { StockListItem } from '@/types';

interface StockCardProps {
  stock: StockListItem;
}

export default function StockCard({ stock }: StockCardProps) {
  const isPositive = stock.change > 0;
  const isNegative = stock.change < 0;
  const changePercent = stock.changePercent ? stock.changePercent.toFixed(2) : '0.00';

  const formatMarketCap = (marketCap: number) => {
    if (marketCap >= 1e12) {
      return `${(marketCap / 1e12).toFixed(2)}T`;
    } else if (marketCap >= 1e9) {
      return `${(marketCap / 1e9).toFixed(2)}B`;
    } else if (marketCap >= 1e6) {
      return `${(marketCap / 1e6).toFixed(2)}M`;
    }
    return marketCap.toString();
  };

  return (
    <Link href={`/stocks/${stock.symbol}`}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow duration-200 p-6 cursor-pointer">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {stock.symbol}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {stock.name}
            </p>
          </div>
          <span className="px-2 py-1 text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
            {stock.sector}
          </span>
        </div>

        <div className="flex justify-between items-end">
          <div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              ${stock.price.toFixed(2)}
            </p>
            <div className="flex items-center mt-2 space-x-2">
              {isPositive && <TrendingUp className="h-4 w-4 text-green-500" />}
              {isNegative && <TrendingDown className="h-4 w-4 text-red-500" />}
              {!isPositive && !isNegative && <Minus className="h-4 w-4 text-gray-500" />}

              <span
                className={`text-sm font-medium ${
                  isPositive
                    ? 'text-green-600 dark:text-green-400'
                    : isNegative
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                {isPositive ? '+' : ''}{stock.change.toFixed(2)} ({isPositive ? '+' : ''}{changePercent}%)
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500 dark:text-gray-400">시가총액</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              ${formatMarketCap(stock.marketCap)}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}