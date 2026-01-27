/**
 * Integration Example - Stock Detail Page
 * @description 실제 프로덕션 코드에서 공통 컴포넌트를 사용하는 통합 예제
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import {
  DataLoadingState,
  DataSourceBadge,
  CorporateActionBadge,
  StockHeaderSkeleton,
  ChartSkeleton,
} from './index';
import type { CorporateAction } from '@/types/stock';

// Mock API response type
interface StockOverview {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  source: 'db' | 'fmp' | 'alpha_vantage';
  synced_at: string;
  freshness: 'fresh' | 'stale' | 'expired';
  actions?: CorporateAction[];
}

// Mock API function
async function fetchStockOverview(symbol: string): Promise<StockOverview> {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // Simulate random error
  if (Math.random() > 0.8) {
    throw new Error('External API connection failed');
  }

  return {
    symbol,
    name: 'Apple Inc.',
    price: 175.43,
    change: 2.34,
    changePercent: 1.35,
    source: 'fmp',
    synced_at: new Date().toISOString(),
    freshness: 'fresh',
    actions: [
      {
        type: 'split',
        date: '2020-08-31',
        display: '4:1',
        description: '4-for-1 stock split',
        ratio: 4,
      },
      {
        type: 'dividend',
        date: '2024-11-08',
        display: '$0.24',
        description: 'Quarterly dividend',
        amount: 0.24,
      },
    ],
  };
}

/**
 * Example 1: Stock Overview Card (Full Integration)
 */
export function StockOverviewCard({ symbol }: { symbol: string }) {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['stock-overview', symbol],
    queryFn: () => fetchStockOverview(symbol),
    staleTime: 1000 * 60, // 1 minute
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <StockHeaderSkeleton />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <DataLoadingState
          status="error"
          error={{
            code: 'EXTERNAL_API_ERROR',
            message: error?.message || '데이터를 불러오는 중 오류가 발생했습니다',
            canRetry: true,
          }}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  // Success state with data check
  if (!data) {
    return null;
  }

  return (
    <DataLoadingState status="success">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-4">
        {/* Header with data source */}
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {data.name}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">{data.symbol}</p>
          </div>
          <DataSourceBadge
            source={data.source}
            syncedAt={data.synced_at}
            freshness={data.freshness}
          />
        </div>

        {/* Price */}
        <div className="flex items-baseline gap-4">
          <span className="text-4xl font-bold text-gray-900 dark:text-white">
            ${data.price.toFixed(2)}
          </span>
          <span
            className={`text-lg font-semibold ${
              data.change >= 0
                ? 'text-green-600 dark:text-green-400'
                : 'text-red-600 dark:text-red-400'
            }`}
          >
            {data.change >= 0 ? '+' : ''}
            {data.change.toFixed(2)} ({data.changePercent.toFixed(2)}%)
          </span>
        </div>

        {/* Corporate Actions */}
        {data.actions && data.actions.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Recent Corporate Actions
            </h3>
            <div className="flex flex-wrap gap-2">
              {data.actions.map((action, idx) => (
                <CorporateActionBadge
                  key={idx}
                  actionType={action.type}
                  display={action.display}
                />
              ))}
            </div>
          </div>
        )}

        {/* Sync indicator */}
        {isFetching && (
          <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600" />
            업데이트 중...
          </div>
        )}
      </div>
    </DataLoadingState>
  );
}

/**
 * Example 2: Stock Chart with Corporate Actions
 */
interface PriceDataPoint {
  date: string;
  close: number;
  volume: number;
  action?: CorporateAction;
}

export function StockChartWithActions({ symbol }: { symbol: string }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['stock-chart', symbol],
    queryFn: async (): Promise<PriceDataPoint[]> => {
      await new Promise((resolve) => setTimeout(resolve, 1500));

      // Mock chart data
      return Array.from({ length: 90 }, (_, i) => ({
        date: new Date(Date.now() - (90 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        close: 150 + Math.random() * 30,
        volume: 50000000 + Math.random() * 20000000,
        action: i === 45 ? {
          type: 'dividend' as const,
          date: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          display: '$0.24',
          amount: 0.24,
        } : undefined,
      }));
    },
  });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <ChartSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <DataLoadingState
          status="error"
          error={{
            code: 'EXTERNAL_API_ERROR',
            message: error?.message || '차트 데이터를 불러올 수 없습니다',
            canRetry: false,
          }}
        />
      </div>
    );
  }

  // Data check
  if (!data) {
    return null;
  }

  // Count corporate actions
  const actionsCount = data.filter((point) => point.action).length;

  return (
    <DataLoadingState status="success">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Price Chart (90 Days)
          </h3>
          {actionsCount > 0 && (
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {actionsCount} corporate action{actionsCount > 1 ? 's' : ''} detected
            </span>
          )}
        </div>

        {/* Simplified chart visualization */}
        <div className="h-64 bg-gray-50 dark:bg-gray-900 rounded-lg p-4 relative">
          <div className="absolute inset-0 flex items-end justify-around p-4">
            {data.slice(0, 30).map((point, idx) => {
              const height = ((point.close - 150) / 30) * 100;
              return (
                <div key={idx} className="flex flex-col items-center gap-1">
                  <div
                    className="w-2 bg-blue-500 rounded-t"
                    style={{ height: `${Math.max(height, 5)}%` }}
                  />
                  {point.action && (
                    <div className="absolute">
                      <CorporateActionBadge
                        actionType={point.action.type}
                        display={point.action.display}
                        size="sm"
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 text-xs text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded" />
            <span>Price</span>
          </div>
          {actionsCount > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded" />
              <span>Corporate Action</span>
            </div>
          )}
        </div>
      </div>
    </DataLoadingState>
  );
}

/**
 * Example 3: Multi-stock comparison with sync states
 */
export function StockComparison({ symbols }: { symbols: string[] }) {
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
        Stock Comparison
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {symbols.map((symbol) => (
          <StockOverviewCard key={symbol} symbol={symbol} />
        ))}
      </div>
    </div>
  );
}

/**
 * Complete Page Example
 */
export default function StockDetailPageExample() {
  const symbol = 'AAPL';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="container mx-auto py-8 space-y-6">
        <StockOverviewCard symbol={symbol} />
        <StockChartWithActions symbol={symbol} />

        <div className="mt-12">
          <StockComparison symbols={['AAPL', 'MSFT', 'GOOGL']} />
        </div>
      </div>
    </div>
  );
}
