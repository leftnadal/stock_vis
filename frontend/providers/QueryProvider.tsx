'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

import { shouldRetryQuery } from './queryRetry';

interface QueryProviderProps {
  children: ReactNode;
}

export default function QueryProvider({ children }: QueryProviderProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5분 - 거시경제 데이터는 빠르게 변하지 않음
            gcTime: 30 * 60 * 1000,   // 30분 - 캐시를 오래 유지
            refetchOnWindowFocus: false,
            refetchOnReconnect: true, // 네트워크 재연결 시 리페치
            // INC-P16-1 Part A: 429(throttle)는 무재시도, 그 외는 기존 최대 2회 보존.
            retry: shouldRetryQuery,
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
