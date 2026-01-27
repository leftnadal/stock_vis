'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { stockService } from '@/services/stock';
import { stockQueryKeys } from './useStockData';

// Sync result interface
export interface SyncResult {
  symbol: string;
  synced: Record<string, { success: boolean; source?: string; error?: string }>;
  status: 'success' | 'partial' | 'failed';
  next_sync_available?: string;
}

// Sync variables interface
interface SyncVariables {
  dataTypes: string[];
  force?: boolean;
}

// Options interface
interface UseDataSyncOptions {
  onSuccess?: (result: SyncResult) => void;
  onError?: (error: Error) => void;
}

// Return type interface
export interface UseDataSyncReturn {
  sync: (dataTypes: string[]) => void;
  isLoading: boolean;
  isSyncing: boolean; // Alias for isLoading for backward compatibility
  isSuccess: boolean;
  isError: boolean;
  status: 'idle' | 'pending' | 'success' | 'error'; // Mutation status
  result: SyncResult | null;
  results: SyncResult | null; // Alias for result for backward compatibility
  error: Error | null;
}

/**
 * Hook for syncing stock data from external APIs
 * Uses TanStack Query's useMutation for optimistic updates and cache invalidation
 */
export function useDataSync(symbol: string, options: UseDataSyncOptions = {}): UseDataSyncReturn {
  const { onSuccess, onError } = options;
  const queryClient = useQueryClient();
  const upperSymbol = symbol?.toUpperCase() || '';

  const mutation = useMutation<SyncResult, Error, SyncVariables>({
    mutationFn: async ({ dataTypes, force = false }: SyncVariables) => {
      if (!upperSymbol) {
        throw new Error('Symbol is required');
      }
      return stockService.syncData(upperSymbol, dataTypes, force);
    },
    onSuccess: (data) => {
      // Invalidate related queries to refetch fresh data
      queryClient.invalidateQueries({ queryKey: stockQueryKeys.overview(upperSymbol) });

      // If price data was synced, invalidate chart queries
      if (data.synced.price?.success) {
        queryClient.invalidateQueries({ queryKey: stockQueryKeys.chart(upperSymbol, 'daily', '1m') });
      }

      // If financial data was synced, invalidate financials queries
      if (
        data.synced.balance_sheet?.success ||
        data.synced.income_statement?.success ||
        data.synced.cash_flow?.success
      ) {
        queryClient.invalidateQueries({ queryKey: stockQueryKeys.financials(upperSymbol, 'annual') });
        queryClient.invalidateQueries({ queryKey: stockQueryKeys.financials(upperSymbol, 'quarterly') });
      }

      onSuccess?.(data);
    },
    onError: (error) => {
      console.error('Sync failed:', error);
      onError?.(error);
    },
  });

  // Helper function to trigger sync
  const sync = (dataTypes: string[]) => {
    mutation.mutate({ dataTypes, force: false });
  };

  return {
    sync,
    isLoading: mutation.isPending,
    isSyncing: mutation.isPending, // Alias for backward compatibility
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    status: mutation.status, // 'idle' | 'pending' | 'success' | 'error'
    result: mutation.data || null,
    results: mutation.data || null, // Alias for backward compatibility
    error: mutation.error,
  };
}

export default useDataSync;
