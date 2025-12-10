'use client';

import React, { Component, ReactNode, ErrorInfo } from 'react';

interface ProviderErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ProviderErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorType: 'rate_limit' | 'network' | 'unknown' | null;
}

/**
 * Provider 에러 타입 판별
 */
function getErrorType(error: Error): 'rate_limit' | 'network' | 'unknown' {
  const message = error.message.toLowerCase();

  if (
    message.includes('rate limit') ||
    message.includes('429') ||
    message.includes('too many requests')
  ) {
    return 'rate_limit';
  }

  if (
    message.includes('network') ||
    message.includes('fetch') ||
    message.includes('connection')
  ) {
    return 'network';
  }

  return 'unknown';
}

/**
 * Provider 에러 바운더리 컴포넌트
 *
 * Rate Limit, 네트워크 에러 등을 적절하게 처리하고 사용자에게 안내합니다.
 */
export class ProviderErrorBoundary extends Component<
  ProviderErrorBoundaryProps,
  ProviderErrorBoundaryState
> {
  constructor(props: ProviderErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorType: null,
    };
  }

  static getDerivedStateFromError(error: Error): ProviderErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorType: getErrorType(error),
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Provider Error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorType: null,
    });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    // 커스텀 fallback이 제공된 경우
    if (this.props.fallback) {
      return this.props.fallback;
    }

    // 에러 타입별 기본 UI
    const { errorType, error } = this.state;

    return (
      <div className="p-4 rounded-lg bg-gray-50">
        {errorType === 'rate_limit' ? (
          <RateLimitErrorUI onRetry={this.handleRetry} />
        ) : errorType === 'network' ? (
          <NetworkErrorUI onRetry={this.handleRetry} />
        ) : (
          <GenericErrorUI error={error} onRetry={this.handleRetry} />
        )}
      </div>
    );
  }
}

/**
 * Rate Limit 에러 UI
 */
function RateLimitErrorUI({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="text-center py-6">
      <div className="text-4xl mb-3">⏳</div>
      <h3 className="text-lg font-semibold text-gray-800 mb-2">
        API 호출 한도 초과
      </h3>
      <p className="text-gray-600 text-sm mb-4">
        잠시 후 다시 시도해 주세요. API 호출 빈도가 제한되어 있습니다.
      </p>
      <div className="flex justify-center gap-3">
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          다시 시도
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-4">
        Alpha Vantage: 분당 5회, 일 500회 제한
        <br />
        FMP: 일 250회 제한
      </p>
    </div>
  );
}

/**
 * 네트워크 에러 UI
 */
function NetworkErrorUI({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="text-center py-6">
      <div className="text-4xl mb-3">🌐</div>
      <h3 className="text-lg font-semibold text-gray-800 mb-2">
        연결 오류
      </h3>
      <p className="text-gray-600 text-sm mb-4">
        서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요.
      </p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
      >
        다시 시도
      </button>
    </div>
  );
}

/**
 * 일반 에러 UI
 */
function GenericErrorUI({
  error,
  onRetry,
}: {
  error: Error | null;
  onRetry: () => void;
}) {
  return (
    <div className="text-center py-6">
      <div className="text-4xl mb-3">⚠️</div>
      <h3 className="text-lg font-semibold text-gray-800 mb-2">
        오류가 발생했습니다
      </h3>
      <p className="text-gray-600 text-sm mb-4">
        데이터를 불러오는 중 문제가 발생했습니다.
      </p>
      {error && (
        <details className="text-left text-xs text-gray-500 mb-4 max-w-md mx-auto">
          <summary className="cursor-pointer hover:text-gray-700">
            자세한 오류 정보
          </summary>
          <pre className="mt-2 p-2 bg-gray-100 rounded overflow-x-auto">
            {error.message}
          </pre>
        </details>
      )}
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
      >
        다시 시도
      </button>
    </div>
  );
}

/**
 * Rate Limit 상태 표시 컴포넌트 (인라인)
 */
export function RateLimitWarning({
  remaining,
  limit,
  provider,
}: {
  remaining: number;
  limit: number;
  provider: string;
}) {
  if (remaining > limit * 0.2) return null;

  const isLow = remaining <= limit * 0.1;

  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${
        isLow
          ? 'bg-red-100 text-red-700'
          : 'bg-yellow-100 text-yellow-700'
      }`}
    >
      {isLow ? '⚠️' : '⏳'}
      <span>
        {provider} API 남은 횟수: {remaining}/{limit}
      </span>
    </div>
  );
}

export default ProviderErrorBoundary;
