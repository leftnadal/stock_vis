import { useQuery } from '@tanstack/react-query';
import { eodService } from '@/services/eodService';
import type { EODDashboardData, SignalCardDetail } from '@/types/eod';

const QUERY_KEYS = {
  dashboard: ['eod-dashboard'] as const,
  signalDetail: (signalId: string) => ['eod-signal-detail', signalId] as const,
  stockHistory: (symbol: string) => ['eod-stock-history', symbol] as const,
} as const;

export function useEODDashboard() {
  return useQuery<EODDashboardData>({
    queryKey: QUERY_KEYS.dashboard,
    queryFn: () => eodService.getDashboard(),
    staleTime: Infinity, // 정적 파일 → 새로고침으로 갱신
    retry: 1,
  });
}

export function useSignalDetail(signalId: string) {
  return useQuery<SignalCardDetail>({
    queryKey: QUERY_KEYS.signalDetail(signalId),
    queryFn: () => eodService.getSignalDetail(signalId),
    staleTime: Infinity,
    enabled: !!signalId,
  });
}

export function useStockHistory(symbol: string) {
  return useQuery({
    queryKey: QUERY_KEYS.stockHistory(symbol),
    queryFn: () => eodService.getStockHistory(symbol),
    staleTime: Infinity,
    enabled: !!symbol,
  });
}
