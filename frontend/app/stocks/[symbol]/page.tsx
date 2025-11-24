'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { stockService, StockQuote, StockOverview } from '@/services/stock';
import StockChart from '@/components/stock/StockChart';
import {
  Building2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  FileText,
  Newspaper,
  Info,
} from 'lucide-react';

type TabType = 'overview' | 'balance-sheet' | 'income-statement' | 'cash-flow' | 'news';

export default function StockDetailPage() {
  const params = useParams();
  const symbol = params?.symbol as string;

  const [stockQuote, setStockQuote] = useState<StockQuote | null>(null);
  const [stockOverview, setStockOverview] = useState<StockOverview | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (symbol) {
      loadStockData();
    }
  }, [symbol]);

  const loadStockData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Convert symbol to uppercase
      const upperSymbol = symbol.toUpperCase();

      // Load quote and overview data in parallel
      const [quote, overview] = await Promise.all([
        stockService.getStockQuote(upperSymbol),
        stockService.getStockOverview(upperSymbol),
      ]);

      setStockQuote(quote);
      setStockOverview(overview);
    } catch (err) {
      console.error('Failed to load stock data:', err);
      setError('주식 데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return '-';
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatNumber = (value: number | undefined) => {
    if (value === undefined || value === null) return '-';
    return new Intl.NumberFormat('ko-KR').format(value);
  };

  const formatPercent = (value: number | string | undefined) => {
    if (value === undefined || value === null) return '-';
    const numValue = typeof value === 'string' ? parseFloat(value.replace('%', '')) : value;
    return `${numValue > 0 ? '+' : ''}${numValue.toFixed(2)}%`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !stockQuote) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-red-600 dark:text-red-400">{error || '주식을 찾을 수 없습니다.'}</p>
          <button
            onClick={loadStockData}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  const isPositive = stockQuote.change >= 0;

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: Info },
    { id: 'balance-sheet' as TabType, label: 'Balance Sheet', icon: FileText },
    { id: 'income-statement' as TabType, label: 'Income Statement', icon: BarChart3 },
    { id: 'cash-flow' as TabType, label: 'Cash Flow', icon: DollarSign },
    { id: 'news' as TabType, label: 'Stock News', icon: Newspaper },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stock Header - 좌측 상단 기본 정보 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Side - Basic Info (Alpha Vantage GLOBAL_QUOTE) */}
            <div>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                    {stockQuote.stock_name}
                  </h1>
                  <p className="text-lg text-gray-600 dark:text-gray-400 mt-1">
                    {stockQuote.symbol}
                    {stockOverview?.exchange && (
                      <span className="ml-2">• {stockOverview.exchange}</span>
                    )}
                  </p>
                  {stockOverview?.sector && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                      <Building2 className="inline h-4 w-4 mr-1" />
                      {stockOverview.sector} • {stockOverview.industry}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-baseline space-x-4">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(stockQuote.real_time_price)}
                </span>
                <div className={`flex items-center ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                  {isPositive ? (
                    <TrendingUp className="h-5 w-5 mr-1" />
                  ) : (
                    <TrendingDown className="h-5 w-5 mr-1" />
                  )}
                  <span className="text-xl font-medium">
                    {formatCurrency(stockQuote.change)} ({formatPercent(stockQuote.change_percent)})
                  </span>
                </div>
              </div>
            </div>

            {/* Right Side - Key Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">오늘 범위</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatCurrency(stockQuote.low_price)} - {formatCurrency(stockQuote.high_price)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">52주 범위</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatCurrency(stockQuote.week_52_low)} - {formatCurrency(stockQuote.week_52_high)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">거래량</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatNumber(stockQuote.volume)}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">시가</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatCurrency(stockQuote.open_price)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">전일 종가</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatCurrency(stockQuote.previous_close)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">시가총액</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {stockQuote.market_capitalization
                      ? `$${(stockQuote.market_capitalization / 1000000000).toFixed(2)}B`
                      : '-'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stock Chart - 기본 1주일, 1일로 변경 가능 */}
        <StockChart symbol={symbol.toUpperCase()} />

        {/* Tabs Navigation */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm mt-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex space-x-1 px-6 pt-4">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-700 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-400'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:bg-gray-700/50'
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'overview' && stockOverview && (
              <OverviewTab overview={stockOverview} />
            )}
            {activeTab === 'balance-sheet' && (
              <FinancialTab symbol={symbol.toUpperCase()} type="balance-sheet" />
            )}
            {activeTab === 'income-statement' && (
              <FinancialTab symbol={symbol.toUpperCase()} type="income-statement" />
            )}
            {activeTab === 'cash-flow' && (
              <FinancialTab symbol={symbol.toUpperCase()} type="cash-flow" />
            )}
            {activeTab === 'news' && <NewsTab symbol={symbol.toUpperCase()} />}
          </div>
        </div>
      </div>
    </div>
  );
}

// Overview Tab Component - Default로 표시
function OverviewTab({ overview }: { overview: StockOverview }) {
  const formatLargeNumber = (num: number | undefined) => {
    if (!num) return '-';
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    return `$${num.toFixed(2)}`;
  };

  return (
    <div className="space-y-6">
      {/* Company Description */}
      {overview.description && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">회사 소개</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            {overview.description}
          </p>
        </div>
      )}

      {/* Key Metrics Grid */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">주요 지표</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <MetricItem label="P/E Ratio" value={overview.pe_ratio?.toFixed(2) || '-'} />
          <MetricItem label="EPS" value={overview.eps ? `$${overview.eps.toFixed(2)}` : '-'} />
          <MetricItem label="배당수익률" value={overview.dividend_yield ? `${(overview.dividend_yield * 100).toFixed(2)}%` : '-'} />
          <MetricItem label="Beta" value={overview.beta?.toFixed(2) || '-'} />
          <MetricItem label="수익률 (TTM)" value={overview.profit_margin ? `${(overview.profit_margin * 100).toFixed(2)}%` : '-'} />
          <MetricItem label="ROE (TTM)" value={overview.return_on_equity_ttm ? `${(overview.return_on_equity_ttm * 100).toFixed(2)}%` : '-'} />
          <MetricItem label="ROA (TTM)" value={overview.return_on_assets_ttm ? `${(overview.return_on_assets_ttm * 100).toFixed(2)}%` : '-'} />
          <MetricItem label="매출 (TTM)" value={formatLargeNumber(overview.revenue_ttm)} />
          <MetricItem label="EBITDA" value={formatLargeNumber(overview.ebitda)} />
          <MetricItem label="목표주가" value={overview.analyst_target_price ? `$${overview.analyst_target_price.toFixed(2)}` : '-'} />
          <MetricItem label="50일 이평선" value={overview.day_50_moving_average ? `$${overview.day_50_moving_average.toFixed(2)}` : '-'} />
          <MetricItem label="200일 이평선" value={overview.day_200_moving_average ? `$${overview.day_200_moving_average.toFixed(2)}` : '-'} />
        </div>
      </div>
    </div>
  );
}

// Metric Item Component
function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
      <p className="text-sm font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

// Financial Tab Component (Balance Sheet, Income Statement, Cash Flow)
function FinancialTab({ symbol, type }: { symbol: string; type: string }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'annual' | 'quarterly'>('annual');

  useEffect(() => {
    loadFinancialData();
  }, [symbol, type, period]);

  const loadFinancialData = async () => {
    try {
      setLoading(true);
      let response;

      switch (type) {
        case 'balance-sheet':
          response = await stockService.getBalanceSheet(symbol, period);
          break;
        case 'income-statement':
          response = await stockService.getIncomeStatement(symbol, period);
          break;
        case 'cash-flow':
          response = await stockService.getCashFlow(symbol, period);
          break;
        default:
          return;
      }

      setData(response);
    } catch (err) {
      console.error(`Failed to load ${type} data:`, err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">로딩 중...</div>;
  }

  return (
    <div>
      {/* Period Selector */}
      <div className="flex justify-end mb-4">
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

      {/* Financial Data Table */}
      {data.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b dark:border-gray-700">
                <th className="text-left py-2 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  항목
                </th>
                {data.map((item, index) => (
                  <th key={`header-${item.fiscal_date_ending || item.reported_date || index}`} className="text-right py-2 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                    {new Date(item.fiscal_date_ending || item.reported_date).toLocaleDateString('ko-KR', {
                      year: 'numeric',
                      month: 'short',
                    })}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Display first few key metrics */}
              {Object.keys(data[0])
                .filter((key) => !['fiscal_date_ending', 'reported_date', 'fiscal_year', 'fiscal_quarter', 'period_type', 'stock', 'id', 'created_at', 'currency'].includes(key))
                .slice(0, 10)
                .map((key) => (
                  <tr key={key} className="border-b dark:border-gray-700">
                    <td className="py-2 px-4 text-sm text-gray-600 dark:text-gray-400">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                    </td>
                    {data.map((item, index) => (
                      <td key={`${key}-${item.fiscal_date_ending || item.reported_date || index}`} className="text-right py-2 px-4 text-sm text-gray-900 dark:text-white">
                        {typeof item[key] === 'number'
                          ? new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(item[key])
                          : item[key] || '-'}
                      </td>
                    ))}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-center text-gray-500 dark:text-gray-400 py-8">데이터가 없습니다.</p>
      )}
    </div>
  );
}

// News Tab Component
function NewsTab({ symbol }: { symbol: string }) {
  return (
    <div className="text-center py-12">
      <Newspaper className="h-12 w-12 text-gray-400 mx-auto mb-4" />
      <p className="text-gray-500 dark:text-gray-400">
        뉴스 기능은 준비 중입니다.
      </p>
      <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
        {symbol} 관련 뉴스가 곧 제공될 예정입니다.
      </p>
    </div>
  );
}