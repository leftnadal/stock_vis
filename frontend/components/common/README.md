# Common Components

Stock 데이터 로딩/에러 상태 및 Corporate Action 표시를 위한 공통 컴포넌트 라이브러리입니다.

## 컴포넌트 목록

### 1. DataLoadingState

데이터 로딩, 동기화, 에러, 빈 상태를 관리하는 컴포넌트입니다.

#### Props

```typescript
interface DataLoadingStateProps {
  status: 'loading' | 'syncing' | 'error' | 'empty' | 'success';
  progress?: {
    current: number;
    total: number;
    currentItem: string;
  };
  error?: {
    code: string;
    message: string;
    canRetry: boolean;
    details?: {
      symbol?: string;
      triedSources?: string[];
      originalError?: string;
    };
  };
  onRetry?: () => void;
  onSync?: () => void;
  children?: React.ReactNode;
  loadingMessage?: string;
  emptyMessage?: string;
}
```

#### 사용 예시

```tsx
import { DataLoadingState } from '@/components/common';

// 로딩 상태
<DataLoadingState status="loading" loadingMessage="Overview 로딩 중..." />

// 동기화 진행 중
<DataLoadingState
  status="syncing"
  progress={{ current: 5, total: 10, currentItem: 'AAPL' }}
/>

// 에러 상태
<DataLoadingState
  status="error"
  error={{
    code: 'RATE_LIMIT_EXCEEDED',
    message: '잠시 후 다시 시도해주세요',
    canRetry: true,
  }}
  onRetry={() => refetch()}
  onSync={() => syncData()}
/>

// 빈 상태
<DataLoadingState
  status="empty"
  emptyMessage="데이터 없음"
  onSync={() => syncData()}
/>

// 성공 상태 (children 렌더링)
<DataLoadingState status="success">
  <div>Data content here</div>
</DataLoadingState>
```

#### 에러 코드

- `STOCK_NOT_FOUND`: 종목을 찾을 수 없습니다
- `EXTERNAL_API_ERROR`: 외부 API 연결 실패
- `RATE_LIMIT_EXCEEDED`: API 요청 한도 초과
- `DATA_SYNC_ERROR`: 데이터 동기화 실패
- `NETWORK_ERROR`: 네트워크 오류

#### Skeleton 컴포넌트

```tsx
import { StockHeaderSkeleton, ChartSkeleton, TableSkeleton } from '@/components/common';

// 주식 헤더 스켈레톤
<StockHeaderSkeleton />

// 차트 스켈레톤
<ChartSkeleton />

// 테이블 스켈레톤
<TableSkeleton rows={10} />
```

---

### 2. DataSourceBadge

데이터 소스와 동기화 시간을 표시하는 배지 컴포넌트입니다.

#### Props

```typescript
interface DataSourceBadgeProps {
  source: 'db' | 'fmp' | 'fmp_realtime' | 'alpha_vantage' | 'yfinance' | 'unknown';
  syncedAt?: string | Date | null;
  freshness?: 'fresh' | 'stale' | 'expired';
  showTime?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}
```

#### 사용 예시

```tsx
import { DataSourceBadge, DataSourceBadgeCompact, DataSourceWithTooltip } from '@/components/common';

// 기본 배지
<DataSourceBadge
  source="fmp"
  syncedAt="2026-01-26T10:30:00Z"
  freshness="fresh"
/>

// 시간 표시 없음
<DataSourceBadge
  source="db"
  showTime={false}
/>

// 컴팩트 버전
<DataSourceBadgeCompact source="fmp" freshness="stale" />

// 툴팁 버전
<DataSourceWithTooltip
  source="alpha_vantage"
  syncedAt="2026-01-26T08:00:00Z"
  freshness="expired"
  canSync={true}
  onSync={() => syncData()}
/>
```

#### Freshness 기준

- **fresh**: 최신 데이터 (녹색)
- **stale**: 오래된 데이터 (노란색)
- **expired**: 만료된 데이터 (빨간색)

---

### 3. CorporateActionBadge

기업의 주식분할, 배당 등 Corporate Action을 표시하는 배지 컴포넌트입니다.

#### Props

```typescript
interface CorporateActionBadgeProps {
  actionType: 'reverse_split' | 'split' | 'spinoff' | 'dividend';
  display: string;
  size?: 'sm' | 'md';
  showTooltip?: boolean;
  className?: string;
}
```

#### 사용 예시

```tsx
import {
  CorporateActionBadge,
  CorporateActionBadgeCompact,
  CorporateActionIcon
} from '@/components/common';

// 기본 배지 (툴팁 포함)
<CorporateActionBadge
  actionType="split"
  display="2:1"
/>

<CorporateActionBadge
  actionType="reverse_split"
  display="1:10"
/>

<CorporateActionBadge
  actionType="dividend"
  display="$5.00"
/>

<CorporateActionBadge
  actionType="spinoff"
  display="Company X"
/>

// 툴팁 없음
<CorporateActionBadge
  actionType="split"
  display="2:1"
  showTooltip={false}
/>

// 컴팩트 버전
<CorporateActionBadgeCompact actionType="split" />

// 아이콘만
<CorporateActionIcon actionType="dividend" size="md" />
```

#### Action 타입 설정

| 타입 | 라벨 | 색상 | 아이콘 | 설명 |
|------|------|------|--------|------|
| `reverse_split` | 역분할 | Amber | TrendingUp | 역주식분할 (예: 1:10) |
| `split` | 분할 | Blue | TrendingDown | 주식분할 (예: 2:1) |
| `spinoff` | 분사 | Purple | AlertTriangle | 기업 분사 |
| `dividend` | 배당 | Green | Gift | 특별 배당 |

---

## 통합 사용 예시

### 주식 상세 페이지

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import {
  DataLoadingState,
  DataSourceBadge,
  CorporateActionBadge
} from '@/components/common';

export default function StockDetailPage({ symbol }: { symbol: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => fetchStock(symbol),
  });

  if (isLoading) {
    return <DataLoadingState status="loading" loadingMessage="주식 데이터 로딩 중..." />;
  }

  if (error) {
    return (
      <DataLoadingState
        status="error"
        error={{
          code: 'EXTERNAL_API_ERROR',
          message: error.message,
          canRetry: true,
        }}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <DataLoadingState status="success">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1>{data.name} ({data.symbol})</h1>
          <DataSourceBadge
            source={data.source}
            syncedAt={data.synced_at}
            freshness={data.freshness}
          />
        </div>

        {/* Corporate Actions */}
        {data.actions && data.actions.length > 0 && (
          <div className="flex gap-2">
            {data.actions.map((action, idx) => (
              <CorporateActionBadge
                key={idx}
                actionType={action.type}
                display={action.display}
              />
            ))}
          </div>
        )}

        {/* Rest of content */}
      </div>
    </DataLoadingState>
  );
}
```

### 차트 컴포넌트

```tsx
'use client';

import { DataLoadingState, CorporateActionIcon } from '@/components/common';
import type { CorporateAction } from '@/types/stock';

interface ChartProps {
  data: PriceDataPoint[];
  isLoading: boolean;
}

export default function StockChart({ data, isLoading }: ChartProps) {
  if (isLoading) {
    return <ChartSkeleton />;
  }

  return (
    <div className="relative">
      {/* Chart rendering */}
      <LineChart data={data} />

      {/* Corporate Action markers */}
      {data.map((point, idx) =>
        point.action && (
          <div
            key={idx}
            className="absolute"
            style={{ left: calculatePosition(idx) }}
          >
            <CorporateActionIcon
              actionType={point.action.type}
              size="sm"
            />
          </div>
        )
      )}
    </div>
  );
}
```

---

## 스타일 가이드

- **Dark Mode**: 모든 컴포넌트는 dark mode를 지원합니다.
- **크기**: `sm` (작은 UI), `md` (기본 UI)
- **색상**: Tailwind CSS 기본 팔레트 사용
- **애니메이션**: `transition-all duration-200` (부드러운 호버 효과)

---

## 타입 정의

```typescript
// DataLoadingState
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

// DataSourceBadge
export type DataSource = 'db' | 'fmp' | 'fmp_realtime' | 'alpha_vantage' | 'yfinance' | 'unknown';
export type DataFreshness = 'fresh' | 'stale' | 'expired';

// CorporateActionBadge
export type ActionType = 'reverse_split' | 'split' | 'spinoff' | 'dividend';

// Stock types (from @/types/stock)
export interface CorporateAction {
  type: CorporateActionType;
  date: string;
  display: string;
  description?: string;
  ratio?: number;
  amount?: number;
}
```

---

## Best Practices

1. **상태 관리**: React Query의 `isLoading`, `error` 상태와 함께 사용
2. **에러 핸들링**: 항상 `canRetry`와 `onRetry` 제공
3. **접근성**: 모든 아이콘에 대체 텍스트 제공
4. **성능**: `memo`로 불필요한 리렌더링 방지
5. **일관성**: 프로젝트 전체에서 동일한 컴포넌트 사용

---

## 참고

- 기존 컴포넌트: `KeywordTag`, `SentimentBadge`와 유사한 패턴 사용
- Lucide Icons: https://lucide.dev/
- Tailwind CSS: https://tailwindcss.com/docs
