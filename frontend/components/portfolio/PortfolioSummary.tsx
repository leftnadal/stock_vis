'use client';

import { TrendingUp, TrendingDown, DollarSign, PieChart } from 'lucide-react';
import { formatCurrency, formatPercent } from '@/utils/formatters';
import { safeParseFloat } from '@/utils/parsers';
import { isProfit, getProfitSign } from '@/utils/styling';

interface PortfolioSummaryProps {
  totalValue?: number;
  totalGain?: number;
  totalGainPercent?: number;
  todayGain?: number;
  todayGainPercent?: number;
  onAddStock?: () => void;
}

export default function PortfolioSummary({
  totalValue = 125420.50,
  totalGain = 12420.50,
  totalGainPercent = 10.98,
  todayGain = 1250.30,
  todayGainPercent = 1.02,
  onAddStock,
}: PortfolioSummaryProps) {
  const safeGainPercent = safeParseFloat(totalGainPercent);
  const safeTodayGainPercent = safeParseFloat(todayGainPercent);
  const isPositiveTotal = isProfit(totalGain);
  const isPositiveToday = isProfit(todayGain);

  const getTrendIcon = (positive: boolean, size: string = 'h-5 w-5') => {
    return positive
      ? <TrendingUp className={`${size} mr-1`} />
      : <TrendingDown className={`${size} mr-1`} />;
  };

  const getColorClass = (positive: boolean) => {
    return positive ? 'text-green-300' : 'text-red-300';
  };

  return (
    <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-6 text-white mb-6">
      {/* 총 자산 */}
      <div className="mb-6">
        <p className="text-blue-100 text-sm mb-2">총 포트폴리오 가치</p>
        <h2 className="text-3xl md:text-4xl font-bold mb-3">
          {formatCurrency(totalValue)}
        </h2>

        {/* 총 수익 */}
        <div className="flex items-center space-x-4">
          <div className={`flex items-center ${getColorClass(isPositiveTotal)}`}>
            {getTrendIcon(isPositiveTotal)}
            <span className="font-semibold">
              {getProfitSign(totalGain)}{formatCurrency(totalGain)}
            </span>
            <span className="ml-2 text-sm">
              ({formatPercent(safeGainPercent)})
            </span>
          </div>
        </div>
      </div>

      {/* 오늘의 변동 */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-blue-500">
        <div>
          <p className="text-blue-200 text-xs mb-1">오늘의 변동</p>
          <div className={`flex items-center ${getColorClass(isPositiveToday)}`}>
            {getTrendIcon(isPositiveToday, 'h-4 w-4')}
            <span className="font-semibold text-sm">
              {getProfitSign(todayGain)}{formatCurrency(todayGain)}
            </span>
          </div>
          <span className={`text-xs ${getColorClass(isPositiveToday)}`}>
            {formatPercent(safeTodayGainPercent)}
          </span>
        </div>

        <div>
          <p className="text-blue-200 text-xs mb-1">투자 원금</p>
          <div className="flex items-center text-white">
            <DollarSign className="h-4 w-4 mr-1" />
            <span className="font-semibold text-sm">
              {formatCurrency(totalValue - totalGain)}
            </span>
          </div>
          <span className="text-xs text-blue-200">초기 투자금</span>
        </div>
      </div>

      {/* 빠른 액션 버튼들 */}
      <div className="flex space-x-3 mt-6">
        <button className="flex-1 bg-white/20 backdrop-blur hover:bg-white/30 transition-colors rounded-lg py-2 px-3 text-sm font-medium">
          <PieChart className="h-4 w-4 inline mr-1" />
          분석 보기
        </button>
        <button
          onClick={onAddStock}
          className="flex-1 bg-green-500 hover:bg-green-600 transition-colors rounded-lg py-2 px-3 text-sm font-medium"
        >
          + 종목 추가
        </button>
      </div>
    </div>
  );
}
