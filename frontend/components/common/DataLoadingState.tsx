'use client';

import { RefreshCw, AlertCircle, Database, WifiOff, Clock } from 'lucide-react';

export type DataStatus = 'loading' | 'syncing' | 'error' | 'empty' | 'success';

export interface LoadingProgress {
  current: number;
  total: number;
  currentItem: string;
}

export interface DataError {
  code: string;
  message: string;
  canRetry: boolean;
  details?: {
    symbol?: string;
    triedSources?: string[];
    originalError?: string;
  };
}

interface DataLoadingStateProps {
  status: DataStatus;
  progress?: LoadingProgress;
  error?: DataError;
  onRetry?: () => void;
  onSync?: () => void;
  children?: React.ReactNode;
  loadingMessage?: string;
  emptyMessage?: string;
}

// Error code to user-friendly message mapping
const ERROR_MESSAGES: Record<string, { title: string; description: string }> = {
  STOCK_NOT_FOUND: {
    title: '종목을 찾을 수 없습니다',
    description: '입력한 심볼을 확인하거나 다른 종목을 검색해보세요.',
  },
  EXTERNAL_API_ERROR: {
    title: '외부 API 연결 실패',
    description: '데이터 제공 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.',
  },
  RATE_LIMIT_EXCEEDED: {
    title: 'API 요청 한도 초과',
    description: '잠시 후 다시 시도해주세요. (약 1분 후)',
  },
  DATA_SYNC_ERROR: {
    title: '데이터 동기화 실패',
    description: '데이터를 저장하는 중 오류가 발생했습니다.',
  },
  NETWORK_ERROR: {
    title: '네트워크 오류',
    description: '인터넷 연결을 확인해주세요.',
  },
  DEFAULT: {
    title: '오류가 발생했습니다',
    description: '잠시 후 다시 시도해주세요.',
  },
};

export default function DataLoadingState({
  status,
  progress,
  error,
  onRetry,
  onSync,
  children,
  loadingMessage = '데이터를 불러오는 중...',
  emptyMessage = '데이터가 없습니다.',
}: DataLoadingStateProps) {
  // Success state - render children
  if (status === 'success') {
    return <>{children}</>;
  }

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-[200px] flex flex-col items-center justify-center p-8">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-600 dark:text-gray-400 text-sm">{loadingMessage}</p>
        {progress && (
          <div className="mt-4 w-full max-w-xs">
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
              <span>{progress.currentItem}</span>
              <span>
                {progress.current} / {progress.total}
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(progress.current / progress.total) * 100}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Syncing state
  if (status === 'syncing') {
    return (
      <div className="min-h-[200px] flex flex-col items-center justify-center p-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <div className="relative">
          <Database className="h-10 w-10 text-blue-600 dark:text-blue-400" />
          <RefreshCw className="h-5 w-5 text-blue-600 dark:text-blue-400 absolute -top-1 -right-1 animate-spin" />
        </div>
        <p className="text-blue-700 dark:text-blue-300 text-sm mt-4 font-medium">
          데이터 동기화 중...
        </p>
        {progress && (
          <div className="mt-4 w-full max-w-xs">
            <div className="flex justify-between text-xs text-blue-600 dark:text-blue-400 mb-1">
              <span>{progress.currentItem}</span>
              <span>
                {progress.current} / {progress.total}
              </span>
            </div>
            <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
              <div
                className="bg-blue-600 dark:bg-blue-400 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(progress.current / progress.total) * 100}%` }}
              ></div>
            </div>
          </div>
        )}
        <p className="text-blue-500 dark:text-blue-400 text-xs mt-2">
          외부 API에서 최신 데이터를 가져오는 중입니다.
        </p>
      </div>
    );
  }

  // Error state
  if (status === 'error' && error) {
    const errorInfo = ERROR_MESSAGES[error.code] || ERROR_MESSAGES.DEFAULT;

    return (
      <div className="min-h-[200px] flex flex-col items-center justify-center p-8 bg-red-50 dark:bg-red-900/20 rounded-lg">
        <div className="rounded-full bg-red-100 dark:bg-red-800 p-3 mb-4">
          {error.code === 'NETWORK_ERROR' ? (
            <WifiOff className="h-8 w-8 text-red-600 dark:text-red-400" />
          ) : error.code === 'RATE_LIMIT_EXCEEDED' ? (
            <Clock className="h-8 w-8 text-red-600 dark:text-red-400" />
          ) : (
            <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
          )}
        </div>
        <h3 className="text-red-700 dark:text-red-300 font-semibold text-lg mb-1">{errorInfo.title}</h3>
        <p className="text-red-600 dark:text-red-400 text-sm text-center max-w-md mb-4">
          {error.message || errorInfo.description}
        </p>
        {error.details?.triedSources && (
          <p className="text-red-500 dark:text-red-400 text-xs mb-4">
            시도한 소스: {error.details.triedSources.join(', ')}
          </p>
        )}
        <div className="flex gap-3">
          {error.canRetry && onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              다시 시도
            </button>
          )}
          {onSync && (
            <button
              onClick={onSync}
              className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 text-red-600 dark:text-red-400 text-sm font-medium rounded-lg border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
            >
              <Database className="h-4 w-4" />
              수동 동기화
            </button>
          )}
        </div>
      </div>
    );
  }

  // Empty state
  if (status === 'empty') {
    return (
      <div className="min-h-[200px] flex flex-col items-center justify-center p-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        <Database className="h-10 w-10 text-gray-400 dark:text-gray-500 mb-4" />
        <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">{emptyMessage}</p>
        {onSync && (
          <button
            onClick={onSync}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            데이터 동기화
          </button>
        )}
      </div>
    );
  }

  // Default loading skeleton
  return (
    <div className="min-h-[200px] animate-pulse space-y-4 p-4">
      <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
    </div>
  );
}

// Skeleton components for specific use cases
export function StockHeaderSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-4"></div>
      <div className="flex items-baseline gap-4">
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="animate-pulse bg-white dark:bg-gray-800 rounded-lg p-4">
      <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
      ))}
    </div>
  );
}
