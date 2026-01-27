# Stock Data Hooks (TanStack Query)

## useStockData

TanStack Query 기반 주식 데이터 조회 훅. Overview, Chart, Financials를 병렬로 fetch합니다.

### 사용법

```typescript
import { useStockData } from '@/hooks/useStockData';

function StockDetailPage({ symbol }: { symbol: string }) {
  const {
    overview,
    chart,
    financials,
    isLoading,
    isError,
    error,
    meta,
    refetch,
  } = useStockData(symbol, {
    chartType: 'daily',
    chartPeriod: '1m',
    financialPeriod: 'annual',
    enabled: true,
  });

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error: {error?.message}</div>;

  return (
    <div>
      <h1>{overview?.stock_name}</h1>
      <p>Price: ${overview?.market_capitalization}</p>

      {/* Meta 정보 */}
      {meta && (
        <div>
          <span>Source: {meta.source}</span>
          <span>Freshness: {meta.freshness}</span>
          <span>Synced at: {meta.synced_at}</span>
        </div>
      )}

      {/* Chart 데이터 */}
      {chart && <StockChart data={chart} />}

      {/* 재무제표 */}
      {financials && (
        <div>
          <BalanceSheet data={financials.balanceSheet} />
          <IncomeStatement data={financials.incomeStatement} />
          <CashFlow data={financials.cashFlow} />
        </div>
      )}

      <button onClick={refetch}>Refresh</button>
    </div>
  );
}
```

### 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `chartType` | `'daily' \| 'weekly'` | `'daily'` | 차트 데이터 타입 |
| `chartPeriod` | `string` | `'1m'` | 차트 기간 (1m, 3m, 6m, 1y 등) |
| `financialPeriod` | `'annual' \| 'quarterly'` | `'annual'` | 재무제표 기간 |
| `enabled` | `boolean` | `true` | 쿼리 활성화 여부 |

### 반환값

| 필드 | 타입 | 설명 |
|------|------|------|
| `overview` | `StockOverview \| null` | 기업 개요 데이터 |
| `chart` | `ChartData[] \| null` | 차트 데이터 |
| `financials` | `FinancialData \| null` | 재무제표 데이터 |
| `isLoading` | `boolean` | 로딩 중 여부 |
| `isError` | `boolean` | 에러 발생 여부 |
| `error` | `StockDataError \| null` | 에러 객체 |
| `meta` | `StockDataMeta \| null` | 데이터 메타 정보 |
| `refetch` | `() => void` | 데이터 재조회 함수 |

### 캐싱 전략

| 데이터 | staleTime | gcTime | 설명 |
|--------|-----------|--------|------|
| Overview | 10분 | 30분 | 기업 기본 정보는 자주 변경되지 않음 |
| Chart | 1분 | 10분 | 가격 데이터는 실시간성 중요 |
| Financials | 1시간 | 2시간 | 재무제표는 분기/연간 업데이트 |

---

## useDataSync

TanStack Query의 useMutation 기반 데이터 동기화 훅. 외부 API에서 최신 데이터를 가져와 DB에 저장합니다.

### 사용법

```typescript
import { useDataSync } from '@/hooks/useDataSync';

function StockSyncButton({ symbol }: { symbol: string }) {
  const { sync, isLoading, isSuccess, isError, result, error } = useDataSync(symbol, {
    onSuccess: (data) => {
      console.log('Sync successful:', data);
      alert('데이터 동기화 완료!');
    },
    onError: (err) => {
      console.error('Sync failed:', err);
      alert('동기화 실패: ' + err.message);
    },
  });

  return (
    <div>
      <button
        onClick={() => sync(['overview', 'price'])}
        disabled={isLoading}
      >
        {isLoading ? '동기화 중...' : '데이터 동기화'}
      </button>

      {isSuccess && result && (
        <div>
          <p>Status: {result.status}</p>
          {Object.entries(result.synced).map(([dataType, info]) => (
            <div key={dataType}>
              {dataType}: {info.success ? '✅' : '❌'}
              {info.source && ` (${info.source})`}
              {info.error && ` - ${info.error}`}
            </div>
          ))}
          {result.next_sync_available && (
            <p>Next sync: {result.next_sync_available}</p>
          )}
        </div>
      )}

      {isError && error && (
        <div>Error: {error.message}</div>
      )}
    </div>
  );
}
```

### 동기화 가능한 데이터 타입

- `overview`: 기업 개요 (가격, 시가총액, 재무 지표 등)
- `price`: 가격 데이터 (일별/주별 OHLCV)
- `balance_sheet`: 재무상태표
- `income_statement`: 손익계산서
- `cash_flow`: 현금흐름표

### 옵션

| 옵션 | 타입 | 설명 |
|------|------|------|
| `onSuccess` | `(result: SyncResult) => void` | 동기화 성공 시 콜백 |
| `onError` | `(error: Error) => void` | 동기화 실패 시 콜백 |

### 반환값

| 필드 | 타입 | 설명 |
|------|------|------|
| `sync` | `(dataTypes: string[]) => void` | 동기화 실행 함수 |
| `isLoading` | `boolean` | 동기화 중 여부 |
| `isSuccess` | `boolean` | 동기화 성공 여부 |
| `isError` | `boolean` | 동기화 실패 여부 |
| `result` | `SyncResult \| null` | 동기화 결과 |
| `error` | `Error \| null` | 에러 객체 |

### 캐시 무효화

동기화 성공 시 자동으로 관련 쿼리를 invalidate합니다:

- `overview` 동기화 → Overview 쿼리 무효화
- `price` 동기화 → Chart 쿼리 무효화
- 재무제표 동기화 → Financials 쿼리 무효화

---

## 통합 사용 예제

```typescript
import { useStockData, useDataSync } from '@/hooks';

function StockPage({ symbol }: { symbol: string }) {
  const {
    overview,
    isLoading,
    isError,
    error,
    meta,
    refetch,
  } = useStockData(symbol);

  const {
    sync,
    isLoading: isSyncing,
  } = useDataSync(symbol, {
    onSuccess: () => {
      // 동기화 후 자동으로 데이터가 refetch됩니다
      console.log('Sync completed, data will be refreshed automatically');
    },
  });

  if (isLoading) return <LoadingSpinner />;
  if (isError) return <ErrorDisplay error={error} />;

  return (
    <div>
      <h1>{overview?.stock_name}</h1>

      {/* 데이터 소스 및 신선도 표시 */}
      <DataSourceBadge
        source={meta?.source || 'unknown'}
        syncedAt={meta?.synced_at}
        freshness={meta?.freshness || 'expired'}
      />

      {/* 동기화 버튼 */}
      <button
        onClick={() => sync(['overview', 'price'])}
        disabled={isSyncing}
      >
        {isSyncing ? '동기화 중...' : '최신 데이터 가져오기'}
      </button>

      {/* 수동 refetch */}
      <button onClick={refetch}>
        Refresh
      </button>
    </div>
  );
}
```

---

## Query Keys 구조

```typescript
// Query keys factory (export되어 있어 직접 사용 가능)
import { stockQueryKeys } from '@/hooks/useStockData';

// 모든 stock 쿼리
stockQueryKeys.all // ['stock']

// Overview 쿼리
stockQueryKeys.overview('AAPL') // ['stock', 'overview', 'AAPL']

// Chart 쿼리
stockQueryKeys.chart('AAPL', 'daily', '1m') // ['stock', 'chart', 'AAPL', 'daily', '1m']

// Financials 쿼리
stockQueryKeys.financials('AAPL', 'annual') // ['stock', 'financials', 'AAPL', 'annual']

// 수동 invalidation
queryClient.invalidateQueries({ queryKey: stockQueryKeys.overview('AAPL') });
queryClient.invalidateQueries({ queryKey: stockQueryKeys.all }); // 모든 stock 쿼리 무효화
```

---

## 에러 처리

### StockDataError 인터페이스

```typescript
interface StockDataError {
  code: string;
  message: string;
  canRetry: boolean;
  details?: {
    symbol?: string;
    triedSources?: string[];
    originalError?: string;
  };
}
```

### 일반적인 에러 코드

| 코드 | 설명 | 재시도 가능 |
|------|------|-------------|
| `STOCK_NOT_FOUND` | 종목을 찾을 수 없음 | ❌ |
| `EXTERNAL_API_ERROR` | 외부 API 연결 실패 | ✅ |
| `RATE_LIMIT_EXCEEDED` | API 요청 한도 초과 | ✅ (1분 후) |
| `DATA_SYNC_ERROR` | 데이터 동기화 실패 | ✅ |
| `NETWORK_ERROR` | 네트워크 오류 | ✅ |

---

## 마이그레이션 가이드

### 기존 useState 기반 코드

```typescript
// Before (useState)
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  fetchData().then(setData).finally(() => setLoading(false));
}, []);
```

```typescript
// After (TanStack Query)
const { data, isLoading } = useStockData(symbol);
```

### 장점

1. **자동 캐싱**: 중복 요청 방지
2. **백그라운드 refetch**: staleTime 이후 자동 갱신
3. **병렬 fetch**: Promise.all 자동 처리
4. **Optimistic updates**: 낙관적 업데이트 지원
5. **Devtools**: React Query Devtools로 디버깅 가능
