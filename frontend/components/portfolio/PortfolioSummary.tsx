'use client';

import { TrendingUp, TrendingDown, DollarSign, PieChart } from 'lucide-react';

interface PortfolioSummaryProps {
  totalValue?: number;
  totalGain?: number;
  totalGainPercent?: number;
  todayGain?: number;
  todayGainPercent?: number;
}

export default function PortfolioSummary({
  totalValue = 125420.50,
  totalGain = 12420.50,
  totalGainPercent = 10.98,
  todayGain = 1250.30,
  todayGainPercent = 1.02,
}: PortfolioSummaryProps) {
  const isPositiveTotal = totalGain >= 0;
  const isPositiveToday = todayGain >= 0;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
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
          <div className={`flex items-center ${isPositiveTotal ? 'text-green-300' : 'text-red-300'}`}>
            {isPositiveTotal ? (
              <TrendingUp className="h-5 w-5 mr-1" />
            ) : (
              <TrendingDown className="h-5 w-5 mr-1" />
            )}
            <span className="font-semibold">
              {isPositiveTotal ? '+' : ''}{formatCurrency(totalGain)}
            </span>
            <span className="ml-2 text-sm">
              ({isPositiveTotal ? '+' : ''}{totalGainPercent.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      {/* 오늘의 변동 */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-blue-500">
        <div>
          <p className="text-blue-200 text-xs mb-1">오늘의 변동</p>
          <div className={`flex items-center ${isPositiveToday ? 'text-green-300' : 'text-red-300'}`}>
            {isPositiveToday ? (
              <TrendingUp className="h-4 w-4 mr-1" />
            ) : (
              <TrendingDown className="h-4 w-4 mr-1" />
            )}
            <span className="font-semibold text-sm">
              {isPositiveToday ? '+' : ''}{formatCurrency(todayGain)}
            </span>
          </div>
          <span className={`text-xs ${isPositiveToday ? 'text-green-300' : 'text-red-300'}`}>
            {isPositiveToday ? '+' : ''}{todayGainPercent.toFixed(2)}%
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
        <button className="flex-1 bg-green-500 hover:bg-green-600 transition-colors rounded-lg py-2 px-3 text-sm font-medium">
          + 종목 추가
        </button>
      </div>
    </div>
  );
}