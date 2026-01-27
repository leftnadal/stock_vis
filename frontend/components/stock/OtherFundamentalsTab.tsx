'use client';

import { useState } from 'react';
import { useFundamentals } from '@/hooks/useFundamentals';
import type { KeyMetric, FinancialRatio, DCFValuation, InvestmentRating } from '@/types/fundamentals';

interface OtherFundamentalsTabProps {
  symbol: string;
}

export default function OtherFundamentalsTab({ symbol }: OtherFundamentalsTabProps) {
  const { data, isLoading, error } = useFundamentals(symbol);
  const [period, setPeriod] = useState<'annual' | 'quarterly'>('annual');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600 dark:text-gray-400">로딩 중...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 dark:text-red-400">데이터를 불러오는 중 오류가 발생했습니다.</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">데이터가 없습니다.</p>
      </div>
    );
  }

  // Get the most recent data
  const latestKeyMetric = data.keyMetrics?.[0];
  const latestRatio = data.ratios?.[0];

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <div className="flex justify-end">
        <div className="flex space-x-2">
          <button
            onClick={() => setPeriod('annual')}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              period === 'annual'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            연간
          </button>
          <button
            onClick={() => setPeriod('quarterly')}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              period === 'quarterly'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            분기
          </button>
        </div>
      </div>

      {/* Investment Rating */}
      {data.rating && <RatingSection rating={data.rating} />}

      {/* DCF Valuation */}
      {data.dcf && <DCFSection dcf={data.dcf} />}

      {/* Key Metrics */}
      {latestKeyMetric && <KeyMetricsSection metric={latestKeyMetric} />}

      {/* Financial Ratios */}
      {latestRatio && <RatiosSection ratio={latestRatio} />}
    </div>
  );
}

// Investment Rating Section
function RatingSection({ rating }: { rating: InvestmentRating }) {
  const getRatingColor = (ratingValue: string) => {
    if (ratingValue.startsWith('A')) return 'text-green-600 dark:text-green-400';
    if (ratingValue.startsWith('B')) return 'text-blue-600 dark:text-blue-400';
    if (ratingValue.startsWith('C')) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getRecommendationColor = (recommendation: string) => {
    if (recommendation.includes('Buy')) return 'text-green-600 dark:text-green-400';
    if (recommendation.includes('Hold')) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">투자 등급</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">등급</p>
          <p className={`text-3xl font-bold ${getRatingColor(rating.rating)}`}>
            {rating.rating}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">점수</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">
            {rating.ratingScore}/100
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">추천</p>
          <p className={`text-xl font-bold ${getRecommendationColor(rating.ratingRecommendation)}`}>
            {rating.ratingRecommendation}
          </p>
        </div>
      </div>
    </div>
  );
}

// DCF Valuation Section
function DCFSection({ dcf }: { dcf: DCFValuation }) {
  const isUndervalued = dcf.premiumDiscount < 0;
  const absDiscount = Math.abs(dcf.premiumDiscount);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">DCF 평가</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">DCF Value</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            ${dcf.dcf.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">현재가</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            ${dcf.stockPrice.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
            {isUndervalued ? '할인율' : '프리미엄'}
          </p>
          <p className={`text-2xl font-bold ${isUndervalued ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {isUndervalued ? '-' : '+'}{absDiscount.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {isUndervalued ? 'Undervalued' : 'Overvalued'}
          </p>
        </div>
      </div>
    </div>
  );
}

// Key Metrics Section
function KeyMetricsSection({ metric }: { metric: KeyMetric }) {
  const formatNumber = (value: number | null) => {
    if (value === null) return '-';
    return value.toFixed(2);
  };

  const formatPercent = (value: number | null) => {
    if (value === null) return '-';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatLargeNumber = (value: number | null) => {
    if (value === null) return '-';
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toFixed(2)}`;
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">핵심 지표</h3>

      {/* Valuation Metrics */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">밸류에이션</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="P/E Ratio" value={formatNumber(metric.peRatio)} />
          <MetricCard label="P/B Ratio" value={formatNumber(metric.pbRatio)} />
          <MetricCard label="EV/EBITDA" value={formatNumber(metric.evToEbitda)} />
          <MetricCard label="Price/Sales" value={formatNumber(metric.priceToSalesRatio)} />
          <MetricCard label="Market Cap" value={formatLargeNumber(metric.marketCapitalization)} />
          <MetricCard label="Enterprise Value" value={formatLargeNumber(metric.enterpriseValue)} />
        </div>
      </div>

      {/* Per Share Metrics */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">주당 지표</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Revenue/Share" value={`$${formatNumber(metric.revenuePerShare)}`} />
          <MetricCard label="Net Income/Share" value={`$${formatNumber(metric.netIncomePerShare)}`} />
          <MetricCard label="FCF/Share" value={`$${formatNumber(metric.freeCashFlowPerShare)}`} />
          <MetricCard label="Book Value/Share" value={`$${formatNumber(metric.bookValuePerShare)}`} />
        </div>
      </div>

      {/* Leverage Metrics */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">레버리지</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Debt/Equity" value={formatNumber(metric.debtToEquity)} />
          <MetricCard label="Debt/Assets" value={formatNumber(metric.debtToAssets)} />
          <MetricCard label="Current Ratio" value={formatNumber(metric.currentRatio)} />
          <MetricCard label="Quick Ratio" value={formatNumber(metric.quickRatio)} />
        </div>
      </div>

      {/* Growth Metrics */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">성장률</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Revenue Growth" value={formatPercent(metric.revenueGrowth)} />
          <MetricCard label="EPS Growth" value={formatPercent(metric.epsgrowth)} />
          <MetricCard label="Op. Income Growth" value={formatPercent(metric.operatingIncomeGrowth)} />
          <MetricCard label="Dividend Yield" value={formatPercent(metric.dividendYield)} />
        </div>
      </div>
    </div>
  );
}

// Financial Ratios Section
function RatiosSection({ ratio }: { ratio: FinancialRatio }) {
  const formatPercent = (value: number | null) => {
    if (value === null) return '-';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatNumber = (value: number | null) => {
    if (value === null) return '-';
    return value.toFixed(2);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">재무 비율</h3>

      {/* Profitability Ratios */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">수익성</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Gross Margin" value={formatPercent(ratio.grossProfitMargin)} />
          <MetricCard label="Operating Margin" value={formatPercent(ratio.operatingProfitMargin)} />
          <MetricCard label="Net Margin" value={formatPercent(ratio.netProfitMargin)} />
          <MetricCard label="EBITDA Margin" value={formatPercent(ratio.ebitdaPerRevenue)} />
        </div>
      </div>

      {/* Return Ratios */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">수익률</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="ROE" value={formatPercent(ratio.returnOnEquity)} />
          <MetricCard label="ROA" value={formatPercent(ratio.returnOnAssets)} />
          <MetricCard label="ROCE" value={formatPercent(ratio.returnOnCapitalEmployed)} />
          <MetricCard label="ROTA" value={formatPercent(ratio.returnOnTangibleAssets)} />
        </div>
      </div>

      {/* Efficiency Ratios */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">효율성</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Asset Turnover" value={formatNumber(ratio.assetTurnover)} />
          <MetricCard label="Inventory Turnover" value={formatNumber(ratio.inventoryTurnover)} />
          <MetricCard label="Receivables Turnover" value={formatNumber(ratio.receivablesTurnover)} />
          <MetricCard label="Payables Turnover" value={formatNumber(ratio.payablesTurnover)} />
        </div>
      </div>

      {/* Coverage Ratios */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">커버리지</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Interest Coverage" value={formatNumber(ratio.interestCoverage)} />
          <MetricCard label="CF/Debt Ratio" value={formatNumber(ratio.cashFlowToDebtRatio)} />
        </div>
      </div>
    </div>
  );
}

// Metric Card Component (reusable)
function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
      <p className="text-sm font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}
