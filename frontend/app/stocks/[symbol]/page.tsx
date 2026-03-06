'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { stockService, StockQuote, StockOverview } from '@/services/stock';
import { AuthGuard } from '@/components/auth/AuthGuard';
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
  Settings2,
  Calculator,
  RefreshCw,
  Compass,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import { ChainSightExplorer } from '@/components/chain-sight';
import UnitSelector from '@/components/financial/UnitSelector';
import FormattedFinancialCell from '@/components/financial/FormattedFinancialCell';
import FieldSettingsModal from '@/components/financial/FieldSettingsModal';
import QuickAddDropdown from '@/components/financial/QuickAddDropdown';
import { useFinancialUnit } from '@/hooks/useFinancialUnit';
import { useFinancialFields } from '@/hooks/useFinancialFields';
import {
  determineOptimalUnit,
  getFormatConfig,
  extractNumericValues,
} from '@/utils/formatters/financialFormatter';
import {
  FinancialTabType,
  getFieldLabel,
  getFieldsForTab,
} from '@/constants/financialDefaults';
import NewsList from '@/components/news/NewsList';
import SentimentChart from '@/components/news/SentimentChart';
import NewsDetailModal from '@/components/news/NewsDetailModal';
import OtherFundamentalsTab from '@/components/stock/OtherFundamentalsTab';
import DataLoadingState, { DataStatus, DataError, LoadingProgress } from '@/components/common/DataLoadingState';
import DataSourceBadge, { DataSourceWithTooltip, DataFreshness, DataSource } from '@/components/common/DataSourceBadge';
import useDataSync from '@/hooks/useDataSync';

type TabType = 'overview' | 'balance-sheet' | 'income-statement' | 'cash-flow' | 'news' | 'other-fundamentals' | 'chain-sight';

interface DataMeta {
  source: DataSource;
  synced_at: string | null;
  freshness: DataFreshness;
  can_sync: boolean;
}

function StockDetailContent() {
  const params = useParams();
  const symbol = params?.symbol as string;

  const [stockQuote, setStockQuote] = useState<StockQuote | null>(null);
  const [stockOverview, setStockOverview] = useState<StockOverview | null>(null);
  const [dataMeta, setDataMeta] = useState<DataMeta | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [status, setStatus] = useState<DataStatus>('loading');
  const [error, setError] = useState<DataError | null>(null);
  const [progress, setProgress] = useState<LoadingProgress | null>(null);

  // Use sync hook
  const {
    sync,
    isSyncing,
    status: syncStatus,
    results: syncResults,
  } = useDataSync(symbol, {
    onSuccess: () => {
      // Reload data after successful sync
      loadStockData();
    },
  });

  const loadStockData = useCallback(async () => {
    if (!symbol) {
      setStatus('empty');
      return;
    }

    try {
      setStatus('loading');
      setError(null);
      setProgress({ current: 0, total: 2, currentItem: 'Quote 데이터 로딩 중...' });

      const upperSymbol = symbol.toUpperCase();

      // Step 1: Load quote data
      setProgress({ current: 1, total: 2, currentItem: 'Quote 데이터 로딩 중...' });
      const quote = await stockService.getStockQuote(upperSymbol);

      // Step 2: Load overview data with meta
      setProgress({ current: 2, total: 2, currentItem: 'Overview 데이터 로딩 중...' });
      const overviewResponse = await stockService.getStockOverviewWithMeta(upperSymbol);

      setStockQuote(quote);
      setStockOverview(overviewResponse.overview);
      setDataMeta(overviewResponse._meta);
      setStatus('success');
      setProgress(null);
    } catch (err: any) {
      console.error('Failed to load stock data:', err);

      // Parse error response
      const errorData: DataError = err.response?.data?.error || {
        code: 'NETWORK_ERROR',
        message: err.message || '주식 데이터를 불러오는 중 오류가 발생했습니다.',
        canRetry: true,
      };

      setError(errorData);
      setStatus('error');
      setProgress(null);
    }
  }, [symbol]);

  useEffect(() => {
    if (symbol) {
      loadStockData();
    }
  }, [symbol, loadStockData]);

  const handleSync = useCallback(() => {
    sync(['overview', 'price']);
  }, [sync]);

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

  // Loading state
  if (status === 'loading' || isSyncing) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <DataLoadingState
            status={isSyncing ? 'syncing' : 'loading'}
            progress={progress || undefined}
            loadingMessage={`${symbol?.toUpperCase()} 데이터를 불러오는 중...`}
          />
        </div>
      </div>
    );
  }

  // Error state
  if (status === 'error' || !stockQuote) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <DataLoadingState
            status="error"
            error={error || { code: 'STOCK_NOT_FOUND', message: '주식을 찾을 수 없습니다.', canRetry: true }}
            onRetry={loadStockData}
            onSync={handleSync}
          />
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
    { id: 'other-fundamentals' as TabType, label: 'Other Fundamentals', icon: Calculator },
    { id: 'news' as TabType, label: 'Stock News', icon: Newspaper },
    { id: 'chain-sight' as TabType, label: 'Chain Sight', icon: Compass },
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
                  <div className="flex items-center gap-3 mb-1">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                      {stockQuote.stock_name}
                    </h1>
                    {/* Data Source Badge */}
                    {dataMeta && (
                      <DataSourceWithTooltip
                        source={dataMeta.source}
                        syncedAt={dataMeta.synced_at}
                        freshness={dataMeta.freshness}
                        canSync={dataMeta.can_sync}
                        onSync={handleSync}
                      />
                    )}
                  </div>
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
                {/* Sync Button */}
                <button
                  onClick={handleSync}
                  disabled={isSyncing}
                  className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors ${
                    isSyncing
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-700'
                      : 'bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50'
                  }`}
                  title="데이터 새로고침"
                >
                  <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
                  {isSyncing ? '동기화 중...' : '새로고침'}
                </button>
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
            {activeTab === 'overview' && (
              stockOverview ? (
                <OverviewTab overview={stockOverview} />
              ) : (
                <EmptyOverviewData />
              )
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
            {activeTab === 'other-fundamentals' && (
              <OtherFundamentalsTab symbol={symbol.toUpperCase()} />
            )}
            {activeTab === 'news' && <NewsTab symbol={symbol.toUpperCase()} />}
            {activeTab === 'chain-sight' && (
              <ChainSightExplorer symbol={symbol.toUpperCase()} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StockDetailPage() {
  return (
    <AuthGuard>
      <StockDetailContent />
    </AuthGuard>
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
      {/* Korean Overview (LLM 생성) */}
      {overview.korean_overview ? (
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">기업 개요</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-line">
              {overview.korean_overview.summary}
            </p>
          </div>

          {overview.korean_overview.business_model && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1.5 flex items-center gap-1.5">
                <Building2 className="w-4 h-4 text-blue-500" />
                사업 모델
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                {overview.korean_overview.business_model}
              </p>
            </div>
          )}

          {overview.korean_overview.competitive_edge && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1.5 flex items-center gap-1.5">
                <Shield className="w-4 h-4 text-green-500" />
                경쟁 우위
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                {overview.korean_overview.competitive_edge}
              </p>
            </div>
          )}

          {overview.korean_overview.risk_factors && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1.5 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                리스크 요인
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                {overview.korean_overview.risk_factors}
              </p>
            </div>
          )}

          <p className="text-xs text-gray-400 dark:text-gray-500 pt-2 border-t border-gray-100 dark:border-gray-700">
            AI 생성 · {overview.korean_overview.llm_model} · {new Date(overview.korean_overview.generated_at).toLocaleDateString('ko-KR')}
          </p>
        </div>
      ) : overview.description ? (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">회사 소개</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            {overview.description}
          </p>
        </div>
      ) : null}

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

// Empty Overview Data Component
function EmptyOverviewData() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="rounded-full bg-gray-100 dark:bg-gray-700 p-4 mb-4">
        <Info className="h-8 w-8 text-gray-400 dark:text-gray-500" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
        공개된 기업 개요 정보가 없습니다
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-md">
        이 종목의 기업 정보가 아직 수집되지 않았거나,
        데이터 제공자가 해당 정보를 제공하지 않습니다.
      </p>
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
        상단의 &apos;동기화&apos; 버튼을 눌러 데이터를 가져올 수 있습니다.
      </p>
    </div>
  );
}

// Empty Financial Data Component
function EmptyFinancialData({ type }: { type: FinancialTabType }) {
  const typeLabels: Record<FinancialTabType, string> = {
    'balance-sheet': '대차대조표',
    'income-statement': '손익계산서',
    'cash-flow': '현금흐름표',
  };

  const typeName = typeLabels[type] || '재무제표';

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="rounded-full bg-gray-100 dark:bg-gray-700 p-4 mb-4">
        <FileText className="h-8 w-8 text-gray-400 dark:text-gray-500" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
        공개된 {typeName} 정보가 없습니다
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-md">
        이 종목은 아직 {typeName} 데이터가 공시되지 않았거나,
        데이터 제공자가 해당 정보를 제공하지 않습니다.
      </p>
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
        일부 소규모 기업이나 신규 상장 기업의 경우 재무 데이터가 제한적일 수 있습니다.
      </p>
    </div>
  );
}

// Financial Tab Component (Balance Sheet, Income Statement, Cash Flow)
function FinancialTab({ symbol, type }: { symbol: string; type: FinancialTabType }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'annual' | 'quarterly'>('annual');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Use the financial fields hook for this tab type
  const { selectedFields, setSelectedFields, addField } = useFinancialFields(type);

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
      {/* Period Selector and Settings */}
      <div className="flex justify-between items-center mb-4">
        {/* Left: Quick Add + Settings */}
        <div className="flex items-center gap-2">
          {/* Quick Add Dropdown */}
          <QuickAddDropdown
            tabType={type}
            selectedFields={selectedFields}
            onAddField={addField}
          />

          {/* Settings Button */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <Settings2 className="w-4 h-4" />
            전체 설정
          </button>
        </div>

        {/* Period Selector */}
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
        <FinancialTable data={data} tabType={type} selectedFields={selectedFields} />
      ) : (
        <EmptyFinancialData type={type} />
      )}

      {/* Field Settings Modal */}
      <FieldSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        tabType={type}
        selectedFields={selectedFields}
        onSave={setSelectedFields}
      />
    </div>
  );
}

// Financial Table Component with Unit Selector and Field Filtering
interface FinancialTableProps {
  data: any[];
  tabType: FinancialTabType;
  selectedFields: string[];
}

function FinancialTable({ data, tabType, selectedFields }: FinancialTableProps) {
  const [selectedUnit, setSelectedUnit] = useFinancialUnit();
  const excludeKeys = ['fiscal_date_ending', 'reported_date', 'fiscal_year', 'fiscal_quarter', 'period_type', 'stock', 'id', 'created_at', 'currency'];

  // Helper to convert string numbers to actual numbers
  const parseNumericValue = (value: any): number | null => {
    if (value === null || value === undefined || value === '') return null;
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
      const parsed = parseFloat(value);
      return isNaN(parsed) ? null : parsed;
    }
    return null;
  };

  // Check if a value is numeric (number or numeric string)
  const isNumericValue = (value: any): boolean => {
    if (typeof value === 'number') return true;
    if (typeof value === 'string' && value !== '') {
      const parsed = parseFloat(value);
      return !isNaN(parsed);
    }
    return false;
  };

  // Extract all numeric values for auto unit determination (handles string numbers)
  const extractAllNumericValues = (): number[] => {
    const values: number[] = [];
    data.forEach((item) => {
      Object.entries(item).forEach(([key, value]) => {
        if (!excludeKeys.includes(key) && selectedFields.includes(key)) {
          const parsed = parseNumericValue(value);
          if (parsed !== null) {
            values.push(parsed);
          }
        }
      });
    });
    return values;
  };

  const numericValues = extractAllNumericValues();

  // Get format configuration based on selected unit
  const formatConfig = selectedUnit === 'auto'
    ? determineOptimalUnit(numericValues)
    : getFormatConfig(selectedUnit);

  // Filter data keys to only include selected fields that exist in the data
  const availableKeys = Object.keys(data[0]).filter((key) => !excludeKeys.includes(key));
  const displayKeys = selectedFields.filter((key) => availableKeys.includes(key));

  // Handle unit change
  const handleUnitChange = (unit: typeof selectedUnit) => {
    setSelectedUnit(unit);
  };

  // Get unit display label for header
  const getUnitLabel = () => {
    if (selectedUnit === 'auto') {
      return formatConfig.suffix ? `Auto (${formatConfig.suffix})` : 'Auto (Raw)';
    }
    return selectedUnit === 'raw' ? 'Raw' : selectedUnit;
  };

  return (
    <div className="space-y-4">
      {/* Unit Selector with current unit display */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-500 dark:text-gray-400">
          단위: <span className="font-medium text-gray-700 dark:text-gray-300">{getUnitLabel()}</span>
          <span className="ml-4">({displayKeys.length}개 항목 표시)</span>
        </span>
        <UnitSelector selectedUnit={selectedUnit} onChange={handleUnitChange} />
      </div>

      {/* Table */}
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
            {displayKeys.map((key) => (
              <tr key={key} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td className="py-2 px-4 text-sm text-gray-600 dark:text-gray-400">
                  {getFieldLabel(tabType, key)}
                </td>
                {data.map((item, index) => {
                  const rawValue = item[key];
                  const numericValue = parseNumericValue(rawValue);

                  return isNumericValue(rawValue) && numericValue !== null ? (
                    <FormattedFinancialCell
                      key={`${key}-${item.fiscal_date_ending || item.reported_date || index}-${selectedUnit}`}
                      value={numericValue}
                      config={formatConfig}
                    />
                  ) : (
                    <td key={`${key}-${item.fiscal_date_ending || item.reported_date || index}`} className="text-right py-2 px-4 text-sm text-gray-400 dark:text-gray-500">
                      {rawValue || '-'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// News Tab Component
function NewsTab({ symbol }: { symbol: string }) {
  const [selectedNewsId, setSelectedNewsId] = useState<string | null>(null);

  return (
    <div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: News List */}
        <div>
          <NewsList symbol={symbol} onArticleClick={(id) => setSelectedNewsId(id)} />
        </div>

        {/* Right: Sentiment Chart */}
        <div>
          <SentimentChart symbol={symbol} />
        </div>
      </div>

      {/* News Detail Modal */}
      <NewsDetailModal newsId={selectedNewsId} onClose={() => setSelectedNewsId(null)} />
    </div>
  );
}