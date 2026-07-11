// 크레딧 신호 스트립 훅 — staleTime 30분(useNewsStrip 관례). CS-CREDIT-CONSUME.
import { useQuery } from '@tanstack/react-query';

import {
  creditSignalsService,
  type CreditStripResponse,
} from '@/services/creditSignalsService';

export function useCreditSignals() {
  return useQuery<CreditStripResponse>({
    queryKey: ['credit-signals-strip'],
    queryFn: () => creditSignalsService.getCreditStrip(),
    staleTime: 1000 * 60 * 30, // 30분
    retry: 1,
  });
}
