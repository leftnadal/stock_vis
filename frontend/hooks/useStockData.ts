'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { stockService, StockOverview, ChartData, FinancialStatement, DataMeta } from '@/services/stock';

// Meta information interface
export interface StockDataMeta {
  source: 'db' | 'fmp' | 'alphavantage';
  synced_at: string;
  freshness: 'fresh' | 'stale' | 'expired';
  can_sync: boolean;
}

// Error interface
export interface StockDataError {
  code: string;
  message: string;
  canRetry: boolean;
  details?: {
    symbol?: string;
    triedSources?: string[];
    originalError?: string;
  };
}

// Financial data interface
export interface FinancialData {
  balanceSheet: FinancialStatement[];
  incomeStatement: FinancialStatement[];
  cashFlow: FinancialStatement[];
}

// Return type interface
export interface UseStockDataReturn {
  overview: StockOverview | null;
  chart: ChartData[] | null;
  financials: FinancialData | null;
  isLoading: boolean;
  isError: boolean;
  error: StockDataError | null;
  meta: StockDataMeta | null;
  refetch: () => void;
}

// Query keys factory
export const stockQueryKeys = {
  all: ['stock'] as const,
  overview: (symbol: string) => [...stockQueryKeys.all, 'overview', symbol.toUpperCase()] as const,
  chart: (symbol: string, type: string, period: string) =>
    [...stockQueryKeys.all, 'chart', symbol.toUpperCase(), type, period] as const,
  financials: (symbol: string, period: 'annual' | 'quarterly') =>
    [...stockQueryKeys.all, 'financials', symbol.toUpperCase(), period] as const,
};

/**
 * Hook for fetching stock data with TanStack Query
 * Fetches overview, chart, and financial data in parallel
 */
export function useStockData(
  symbol: string,
  options: {
    chartType?: 'daily' | 'weekly';
    chartPeriod?: string;
    financialPeriod?: 'annual' | 'quarterly';
    enabled?: boolean;
  } = {}
): UseStockDataReturn {
  const {
    chartType = 'daily',
    chartPeriod = '1m',
    financialPeriod = 'annual',
    enabled = true,
  } = options;

  const upperSymbol = symbol?.toUpperCase() || '';
  const queryClient = useQueryClient();

  // Overview query
  const {
    data: overviewData,
    isLoading: overviewLoading,
    isError: overviewError,
    error: overviewErrorData,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: stockQueryKeys.overview(upperSymbol),
    queryFn: async () => {
      const response = await stockService.getStockOverviewWithMeta(upperSymbol);
      return response;
    },
    enabled: enabled && !!upperSymbol,
    staleTime: 1000 * 60 * 10, // 10 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes (was cacheTime)
    retry: 1,
  });

  // Chart query
  const {
    data: chartData,
    isLoading: chartLoading,
    refetch: refetchChart,
  } = useQuery({
    queryKey: stockQueryKeys.chart(upperSymbol, chartType, chartPeriod),
    queryFn: async () => {
      const response = await stockService.getChartData(upperSymbol, chartType, chartPeriod);
      return response.data;
    },
    enabled: enabled && !!upperSymbol,
    staleTime: 1000 * 60, // 1 minute for chart data
    gcTime: 1000 * 60 * 10, // 10 minutes
    retry: 1,
  });

  // Financials query (optional, can be loaded separately)
  const {
    data: financialsData,
    isLoading: financialsLoading,
    refetch: refetchFinancials,
  } = useQuery({
    queryKey: stockQueryKeys.financials(upperSymbol, financialPeriod),
    queryFn: async () => {
      const [balanceSheet, incomeStatement, cashFlow] = await Promise.all([
        stockService.getBalanceSheet(upperSymbol, financialPeriod, 5),
        stockService.getIncomeStatement(upperSymbol, financialPeriod, 5),
        stockService.getCashFlow(upperSymbol, financialPeriod, 5),
      ]);
      return { balanceSheet, incomeStatement, cashFlow };
    },
    enabled: enabled && !!upperSymbol,
    staleTime: 1000 * 60 * 60, // 1 hour for financial data
    gcTime: 1000 * 60 * 60 * 2, // 2 hours
    retry: 1,
  });

  // Parse meta from overview response
  const meta: StockDataMeta | null = overviewData?._meta
    ? {
        source: overviewData._meta.source as 'db' | 'fmp' | 'alphavantage',
        synced_at: overviewData._meta.synced_at || new Date().toISOString(),
        freshness: overviewData._meta.freshness,
        can_sync: overviewData._meta.can_sync,
      }
    : null;

  // Parse error
  const error: StockDataError | null = overviewError
    ? {
        code: (overviewErrorData as any)?.response?.data?.error?.code || 'NETWORK_ERROR',
        message:
          (overviewErrorData as any)?.response?.data?.error?.message ||
          (overviewErrorData as any)?.message ||
          '데이터를 불러오는 중 오류가 발생했습니다.',
        canRetry: true,
        details: (overviewErrorData as any)?.response?.data?.error?.details,
      }
    : null;

  // Refetch all data
  const refetch = () => {
    refetchOverview();
    refetchChart();
    refetchFinancials();
  };

  return {
    overview: overviewData?.overview || null,
    chart: chartData || null,
    financials: financialsData || null,
    isLoading: overviewLoading || chartLoading || financialsLoading,
    isError: overviewError,
    error,
    meta,
    refetch,
  };
}

export default useStockData;
