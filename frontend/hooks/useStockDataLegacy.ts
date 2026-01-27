'use client';

/**
 * Legacy adapter for useStockData
 * Provides backward compatibility with old useState-based API
 *
 * @deprecated Use useStockData (TanStack Query version) instead
 */

import { useMemo } from 'react';
import { useStockData } from './useStockData';
import { DataStatus, DataError, LoadingProgress } from '@/components/common/DataLoadingState';
import { DataFreshness, DataSource } from '@/components/common/DataSourceBadge';
import { StockQuote, StockOverview } from '@/services/stock';

export interface StockMeta {
  source: DataSource;
  syncedAt: string | null;
  freshness: DataFreshness;
  canSync: boolean;
}

export interface StockDataState {
  quote: StockQuote | null;
  overview: StockOverview | null;
  meta: StockMeta | null;
  status: DataStatus;
  error: DataError | null;
  progress: LoadingProgress | null;
}

interface UseStockDataOptions {
  autoSync?: boolean;
  onError?: (error: DataError) => void;
}

/**
 * Legacy wrapper that transforms TanStack Query API to old useState-based API
 */
export function useStockDataLegacy(symbol: string, options: UseStockDataOptions = {}) {
  const { onError } = options;

  const {
    overview,
    isLoading,
    isError,
    error: queryError,
    meta: queryMeta,
    refetch,
  } = useStockData(symbol);

  // Transform meta to legacy format
  const meta: StockMeta | null = useMemo(() => {
    if (!queryMeta) return null;
    return {
      source: queryMeta.source as DataSource,
      syncedAt: queryMeta.synced_at,
      freshness: queryMeta.freshness,
      canSync: queryMeta.can_sync,
    };
  }, [queryMeta]);

  // Transform error to legacy format
  const error: DataError | null = useMemo(() => {
    if (!queryError) return null;
    return {
      code: queryError.code,
      message: queryError.message,
      canRetry: queryError.canRetry,
      details: queryError.details,
    };
  }, [queryError]);

  // Derive quote from overview (legacy behavior)
  const quote: StockQuote | null = useMemo(() => {
    if (!overview) return null;
    return {
      symbol: overview.symbol,
      stock_name: overview.stock_name,
      real_time_price: overview.market_capitalization ? 0 : 0, // Placeholder
      high_price: 0,
      low_price: 0,
      open_price: 0,
      previous_close: 0,
      volume: 0,
      change: 0,
      change_percent: '0%',
      market_capitalization: overview.market_capitalization,
      pe_ratio: overview.pe_ratio,
      dividend_yield: overview.dividend_yield,
      week_52_high: overview.week_52_high,
      week_52_low: overview.week_52_low,
    };
  }, [overview]);

  // Determine status
  const status: DataStatus = useMemo(() => {
    if (isLoading) return 'loading';
    if (isError) return 'error';
    if (!overview) return 'empty';
    return 'success';
  }, [isLoading, isError, overview]);

  // Progress is not supported in new API
  const progress: LoadingProgress | null = null;

  // Call onError callback when error changes
  useMemo(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

  const state: StockDataState = {
    quote,
    overview,
    meta,
    status,
    error,
    progress,
  };

  return {
    ...state,
    reload: refetch,
    retry: refetch,
  };
}

export default useStockDataLegacy;
