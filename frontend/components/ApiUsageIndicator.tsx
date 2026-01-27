'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiUsageInfo, ProviderType } from '@/types/provider';

// API 사용량 조회 함수
async function fetchApiUsage(): Promise<Record<ProviderType, ApiUsageInfo>> {
  const response = await fetch('/api/v1/admin/providers/rate-limits/', {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to fetch API usage');
  }

  const data = await response.json();

  // Rate limit 데이터를 ApiUsageInfo 형식으로 변환
  const result: Record<string, ApiUsageInfo> = {};

  for (const [provider, status] of Object.entries(data)) {
    const providerStatus = status as any;
    const dailyLimit = providerStatus.limits?.per_day;

    if (dailyLimit) {
      result[provider] = {
        provider: provider as ProviderType,
        daily_calls: dailyLimit.current || 0,
        daily_limit: dailyLimit.limit || 0,
        remaining: dailyLimit.remaining || 0,
        usage_percent:
          dailyLimit.limit > 0
            ? Math.round((dailyLimit.current / dailyLimit.limit) * 100)
            : 0,
        last_request: null,
      };
    }
  }

  return result as Record<ProviderType, ApiUsageInfo>;
}

interface ApiUsageIndicatorProps {
  provider?: ProviderType;
  showLabel?: boolean;
  className?: string;
}

/**
 * API 사용량 인디케이터 컴포넌트
 *
 * 현재 API 호출 횟수와 일일 한도를 시각적으로 표시합니다.
 */
export function ApiUsageIndicator({
  provider = 'alpha_vantage',
  showLabel = true,
  className = '',
}: ApiUsageIndicatorProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['api-usage'],
    queryFn: fetchApiUsage,
    refetchInterval: 60000, // 1분마다 갱신
    staleTime: 30000, // 30초간 fresh
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="h-2 w-16 bg-gray-200 rounded animate-pulse" />
        {showLabel && (
          <span className="text-xs text-gray-400">Loading...</span>
        )}
      </div>
    );
  }

  if (error || !data) {
    return null; // 에러 시 조용히 숨김
  }

  const usage = data[provider];
  if (!usage) return null;

  const { usage_percent, remaining, daily_limit } = usage;

  // 사용량에 따른 색상
  const getColorClass = (percent: number) => {
    if (percent >= 90) return 'bg-red-500';
    if (percent >= 70) return 'bg-yellow-500';
    if (percent >= 50) return 'bg-blue-500';
    return 'bg-green-500';
  };

  const providerLabel = provider === 'alpha_vantage' ? 'AV' : 'FMP';

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {showLabel && (
        <span className="text-xs text-gray-500 font-medium">{providerLabel}</span>
      )}

      {/* Progress Bar */}
      <div className="relative h-2 w-16 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`absolute top-0 left-0 h-full rounded-full transition-all ${getColorClass(
            usage_percent
          )}`}
          style={{ width: `${Math.min(usage_percent, 100)}%` }}
        />
      </div>

      {/* 남은 횟수 */}
      <span className="text-xs text-gray-500">
        {remaining}/{daily_limit}
      </span>
    </div>
  );
}

/**
 * API 사용량 요약 컴포넌트 (Admin 페이지용)
 */
export function ApiUsageSummary({ className = '' }: { className?: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['api-usage'],
    queryFn: fetchApiUsage,
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className={`p-4 bg-white rounded-lg shadow ${className}`}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-32 bg-gray-200 rounded" />
          <div className="h-8 w-full bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-4 bg-red-50 rounded-lg ${className}`}>
        <p className="text-red-600 text-sm">Failed to load API usage</p>
        <button
          onClick={() => refetch()}
          className="text-red-600 underline text-xs mt-1"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className={`p-4 bg-white rounded-lg shadow ${className}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-gray-800">API Usage</h3>
        <button
          onClick={() => refetch()}
          className="text-xs text-blue-600 hover:underline"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {Object.values(data).map((usage) => (
          <div key={usage.provider}>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium capitalize">
                {usage.provider.replace('_', ' ')}
              </span>
              <span
                className={`font-bold ${
                  usage.usage_percent >= 90
                    ? 'text-red-600'
                    : usage.usage_percent >= 70
                    ? 'text-yellow-600'
                    : 'text-green-600'
                }`}
              >
                {usage.usage_percent}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  usage.usage_percent >= 90
                    ? 'bg-red-500'
                    : usage.usage_percent >= 70
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(usage.usage_percent, 100)}%` }}
              />
            </div>

            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>
                Used: {usage.daily_calls} / {usage.daily_limit}
              </span>
              <span>Remaining: {usage.remaining}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 경고 메시지 */}
      {Object.values(data).some((u) => u.usage_percent >= 80) && (
        <div className="mt-4 p-2 bg-yellow-50 rounded text-xs text-yellow-700">
          ⚠️ API usage is high. Consider enabling caching or reducing requests.
        </div>
      )}
    </div>
  );
}

export default ApiUsageIndicator;
