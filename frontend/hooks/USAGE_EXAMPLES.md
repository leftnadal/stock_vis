# Stock Data Hooks - 사용 예제

## 1. 기본 사용법 (useStockData)

```typescript
'use client';

import { useStockData } from '@/hooks/useStockData';

export default function StockDetailPage({ params }: { params: { symbol: string } }) {
  const { symbol } = params;

  const {
    overview,
    chart,
    financials,
    isLoading,
    isError,
    error,
    meta,
    refetch,
  } = useStockData(symbol);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4">
        <h2 className="text-xl font-bold text-red-600">Error</h2>
        <p>{error?.message}</p>
        {error?.canRetry && (
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">{overview?.stock_name}</h1>
      <p className="text-gray-600">{overview?.symbol}</p>

      {/* Meta 정보 */}
      {meta && (
        <div className="mt-2 text-sm text-gray-500">
          Source: {meta.source} | Freshness: {meta.freshness}
        </div>
      )}

      {/* Chart */}
      {chart && chart.length > 0 && (
        <div className="mt-4">
          <h2 className="text-xl font-semibold">Price Chart</h2>
          {/* 차트 컴포넌트 */}
        </div>
      )}

      {/* Refresh Button */}
      <button
        onClick={() => refetch()}
        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
      >
        Refresh Data
      </button>
    </div>
  );
}
```

---

## 2. 데이터 동기화 (useDataSync)

```typescript
'use client';

import { useStockData, useDataSync } from '@/hooks';
import { useState } from 'react';

export default function StockWithSync({ symbol }: { symbol: string }) {
  const [syncTypes, setSyncTypes] = useState<string[]>(['overview']);

  const {
    overview,
    meta,
    isLoading,
    refetch,
  } = useStockData(symbol);

  const {
    sync,
    isLoading: isSyncing,
    isSuccess: syncSuccess,
    result,
  } = useDataSync(symbol, {
    onSuccess: (data) => {
      console.log('Sync completed:', data);
      alert('데이터가 성공적으로 동기화되었습니다!');
    },
    onError: (err) => {
      console.error('Sync error:', err);
      alert('동기화 실패: ' + err.message);
    },
  });

  const handleSync = () => {
    sync(syncTypes);
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">{overview?.stock_name}</h1>

      {/* 데이터 신선도 표시 */}
      {meta && (
        <div className={`mt-2 p-2 rounded ${
          meta.freshness === 'fresh' ? 'bg-green-100' :
          meta.freshness === 'stale' ? 'bg-yellow-100' :
          'bg-red-100'
        }`}>
          <p className="text-sm">
            Source: {meta.source} | Freshness: {meta.freshness}
          </p>
          <p className="text-xs text-gray-600">
            Last synced: {new Date(meta.synced_at).toLocaleString()}
          </p>
        </div>
      )}

      {/* 동기화 옵션 선택 */}
      <div className="mt-4">
        <h3 className="font-semibold">Sync Options</h3>
        <div className="space-y-2">
          {['overview', 'price', 'balance_sheet', 'income_statement', 'cash_flow'].map((type) => (
            <label key={type} className="flex items-center">
              <input
                type="checkbox"
                checked={syncTypes.includes(type)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSyncTypes([...syncTypes, type]);
                  } else {
                    setSyncTypes(syncTypes.filter((t) => t !== type));
                  }
                }}
                className="mr-2"
              />
              {type}
            </label>
          ))}
        </div>
      </div>

      {/* 동기화 버튼 */}
      <button
        onClick={handleSync}
        disabled={isSyncing || syncTypes.length === 0}
        className={`mt-4 px-4 py-2 rounded text-white ${
          isSyncing || syncTypes.length === 0
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {isSyncing ? 'Syncing...' : 'Sync Data'}
      </button>

      {/* 동기화 결과 */}
      {syncSuccess && result && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
          <h4 className="font-semibold text-green-800">Sync Result</h4>
          <p className="text-sm">Status: {result.status}</p>
          <ul className="mt-2 space-y-1">
            {Object.entries(result.synced).map(([dataType, info]) => (
              <li key={dataType} className="text-sm">
                <span className="font-medium">{dataType}:</span>{' '}
                {info.success ? (
                  <span className="text-green-600">✅ Success</span>
                ) : (
                  <span className="text-red-600">❌ Failed</span>
                )}
                {info.source && ` (from ${info.source})`}
                {info.error && ` - ${info.error}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

---

## 3. 조건부 쿼리 (enabled 옵션)

```typescript
'use client';

import { useStockData } from '@/hooks/useStockData';
import { useState } from 'react';

export default function ConditionalQuery() {
  const [symbol, setSymbol] = useState('');
  const [searchSymbol, setSearchSymbol] = useState('');

  // searchSymbol이 있을 때만 쿼리 실행
  const { overview, isLoading, isError } = useStockData(searchSymbol, {
    enabled: searchSymbol.length > 0,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchSymbol(symbol.toUpperCase());
  };

  return (
    <div className="p-4">
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Enter stock symbol (e.g., AAPL)"
          className="flex-1 px-4 py-2 border rounded"
        />
        <button
          type="submit"
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Search
        </button>
      </form>

      {isLoading && <div className="mt-4">Loading...</div>}

      {isError && (
        <div className="mt-4 text-red-600">
          Stock not found or error occurred
        </div>
      )}

      {overview && (
        <div className="mt-4 p-4 border rounded">
          <h2 className="text-xl font-bold">{overview.stock_name}</h2>
          <p className="text-gray-600">{overview.symbol}</p>
          <p className="mt-2">Sector: {overview.sector}</p>
          <p>Industry: {overview.industry}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 4. 캐시 활용 (여러 컴포넌트에서 동일 데이터 공유)

```typescript
// ParentComponent.tsx
'use client';

import StockHeader from './StockHeader';
import StockChart from './StockChart';
import StockFinancials from './StockFinancials';

export default function StockDetailPage({ symbol }: { symbol: string }) {
  return (
    <div>
      {/* 각 컴포넌트는 독립적으로 useStockData를 호출하지만,
          TanStack Query가 자동으로 캐시를 공유하여 중복 요청을 방지합니다 */}
      <StockHeader symbol={symbol} />
      <StockChart symbol={symbol} />
      <StockFinancials symbol={symbol} />
    </div>
  );
}

// StockHeader.tsx
import { useStockData } from '@/hooks/useStockData';

export default function StockHeader({ symbol }: { symbol: string }) {
  const { overview, meta } = useStockData(symbol); // 캐시된 데이터 사용
  return <h1>{overview?.stock_name}</h1>;
}

// StockChart.tsx
import { useStockData } from '@/hooks/useStockData';

export default function StockChart({ symbol }: { symbol: string }) {
  const { chart } = useStockData(symbol); // 동일한 캐시 사용
  return <div>{/* Chart rendering */}</div>;
}

// StockFinancials.tsx
import { useStockData } from '@/hooks/useStockData';

export default function StockFinancials({ symbol }: { symbol: string }) {
  const { financials } = useStockData(symbol); // 동일한 캐시 사용
  return <div>{/* Financials rendering */}</div>;
}
```

---

## 5. 수동 캐시 무효화

```typescript
'use client';

import { useQueryClient } from '@tanstack/react-query';
import { stockQueryKeys } from '@/hooks/useStockData';

export default function StockAdmin({ symbol }: { symbol: string }) {
  const queryClient = useQueryClient();

  const invalidateOverview = () => {
    queryClient.invalidateQueries({
      queryKey: stockQueryKeys.overview(symbol),
    });
  };

  const invalidateChart = () => {
    queryClient.invalidateQueries({
      queryKey: stockQueryKeys.chart(symbol, 'daily', '1m'),
    });
  };

  const invalidateAll = () => {
    queryClient.invalidateQueries({
      queryKey: stockQueryKeys.all,
    });
  };

  return (
    <div className="p-4 space-y-2">
      <button onClick={invalidateOverview} className="px-4 py-2 bg-blue-600 text-white rounded">
        Invalidate Overview
      </button>
      <button onClick={invalidateChart} className="px-4 py-2 bg-blue-600 text-white rounded">
        Invalidate Chart
      </button>
      <button onClick={invalidateAll} className="px-4 py-2 bg-red-600 text-white rounded">
        Invalidate All Stock Queries
      </button>
    </div>
  );
}
```

---

## 6. 낙관적 업데이트 (Optimistic Update)

```typescript
'use client';

import { useDataSync, useStockData } from '@/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { stockQueryKeys } from '@/hooks/useStockData';

export default function OptimisticUpdate({ symbol }: { symbol: string }) {
  const queryClient = useQueryClient();
  const { overview } = useStockData(symbol);

  const { sync } = useDataSync(symbol, {
    onSuccess: (data) => {
      // 동기화 성공 시 자동으로 캐시가 invalidate되어 refetch됨
      console.log('Data synced successfully');
    },
  });

  const handleSyncWithOptimisticUpdate = () => {
    // 낙관적 업데이트: UI를 즉시 업데이트
    queryClient.setQueryData(stockQueryKeys.overview(symbol), (old: any) => ({
      ...old,
      overview: {
        ...old?.overview,
        // 낙관적으로 업데이트할 필드
      },
      _meta: {
        ...old?._meta,
        freshness: 'fresh',
      },
    }));

    // 실제 동기화 수행
    sync(['overview']);
  };

  return (
    <div className="p-4">
      <h1>{overview?.stock_name}</h1>
      <button
        onClick={handleSyncWithOptimisticUpdate}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        Sync with Optimistic Update
      </button>
    </div>
  );
}
```

---

## 7. 에러 바운더리와 함께 사용

```typescript
'use client';

import { ErrorBoundary } from 'react-error-boundary';
import { useStockData } from '@/hooks/useStockData';

function ErrorFallback({ error, resetErrorBoundary }: any) {
  return (
    <div className="p-4 bg-red-50 border border-red-200 rounded">
      <h2 className="text-xl font-bold text-red-800">Error occurred</h2>
      <p className="text-red-600">{error.message}</p>
      <button
        onClick={resetErrorBoundary}
        className="mt-4 px-4 py-2 bg-red-600 text-white rounded"
      >
        Try again
      </button>
    </div>
  );
}

function StockContent({ symbol }: { symbol: string }) {
  const { overview, isLoading, error } = useStockData(symbol);

  if (isLoading) return <div>Loading...</div>;
  if (error) throw error; // ErrorBoundary가 잡음

  return (
    <div>
      <h1>{overview?.stock_name}</h1>
      <p>{overview?.description}</p>
    </div>
  );
}

export default function StockWithErrorBoundary({ symbol }: { symbol: string }) {
  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={() => window.location.reload()}
    >
      <StockContent symbol={symbol} />
    </ErrorBoundary>
  );
}
```

---

## 8. 레거시 코드 마이그레이션

기존 useState 기반 코드를 사용하는 경우, 레거시 어댑터를 사용하여 점진적으로 마이그레이션할 수 있습니다.

```typescript
// Before (기존 useState 기반)
import { useStockData } from '@/hooks/useStockData'; // old

function OldComponent({ symbol }: { symbol: string }) {
  const { quote, overview, status, error, retry } = useStockData(symbol);

  if (status === 'loading') return <div>Loading...</div>;
  if (status === 'error') return <div>Error: {error?.message}</div>;

  return <div>{overview?.stock_name}</div>;
}
```

```typescript
// After (TanStack Query로 점진적 마이그레이션)
// Step 1: 레거시 어댑터 사용
import { useStockDataLegacy as useStockData } from '@/hooks/useStockDataLegacy';

function TransitionComponent({ symbol }: { symbol: string }) {
  const { quote, overview, status, error, retry } = useStockData(symbol);
  // 기존 코드 그대로 동작
}

// Step 2: 새로운 API로 완전히 마이그레이션
import { useStockData } from '@/hooks/useStockData';

function NewComponent({ symbol }: { symbol: string }) {
  const { overview, isLoading, isError, error, refetch } = useStockData(symbol);

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error: {error?.message}</div>;

  return <div>{overview?.stock_name}</div>;
}
```

---

## 요약

1. **useStockData**: Overview, Chart, Financials를 병렬로 fetch
2. **useDataSync**: 외부 API에서 데이터 동기화
3. **stockQueryKeys**: 쿼리 키 관리
4. **캐싱**: 자동 캐싱으로 중복 요청 방지
5. **에러 처리**: StockDataError 인터페이스 활용
6. **레거시 호환**: useStockDataLegacy로 점진적 마이그레이션
