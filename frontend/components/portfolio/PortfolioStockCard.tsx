'use client';

import { MoreVertical } from 'lucide-react';

interface PortfolioStock {
  symbol: string;
  name: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
  value: number;
  gain: number;
  gainPercent: number;
}

interface PortfolioStockCardProps {
  stock: PortfolioStock;
}

export default function PortfolioStockCard({ stock }: PortfolioStockCardProps) {
  const isPositive = stock.gain >= 0;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 hover:shadow-lg transition-shadow cursor-pointer">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 dark:text-white text-lg">
              {stock.symbol}
            </h3>
            <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              <MoreVertical className="h-5 w-5" />
            </button>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {stock.name}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {/* 현재 가치 */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">보유 가치</span>
          <span className="font-semibold text-gray-900 dark:text-white">
            {formatCurrency(stock.value)}
          </span>
        </div>

        {/* 손익 */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">손익</span>
          <div className="text-right">
            <div className={`font-semibold ${
              isPositive ? 'text-green-600' : 'text-red-600'
            }`}>
              {isPositive ? '+' : ''}{formatCurrency(stock.gain)}
            </div>
            <div className={`text-xs ${
              isPositive ? 'text-green-500' : 'text-red-500'
            }`}>
              {isPositive ? '+' : ''}{stock.gainPercent.toFixed(2)}%
            </div>
          </div>
        </div>

        {/* 보유 정보 */}
        <div className="pt-3 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-gray-500 dark:text-gray-400 text-xs">보유 수량</p>
            <p className="font-medium text-gray-900 dark:text-white">{stock.shares}주</p>
          </div>
          <div>
            <p className="text-gray-500 dark:text-gray-400 text-xs">평균 매입가</p>
            <p className="font-medium text-gray-900 dark:text-white">{formatCurrency(stock.avgPrice)}</p>
          </div>
        </div>

        {/* 현재가 */}
        <div className="flex justify-between items-center pt-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">현재가</span>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {formatCurrency(stock.currentPrice)}
          </span>
        </div>
      </div>
    </div>
  );
}