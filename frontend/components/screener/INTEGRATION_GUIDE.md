# Screener Components Integration Guide

스크리너 페이지에 새로운 컴포넌트를 통합하는 가이드입니다.

## 1. 전체 페이지 통합 예제

```tsx
'use client';

import { useState } from 'react';
import { AuthGuard } from '@/components/auth/AuthGuard';
import {
  MarketBreadthCard,
  SectorHeatmap,
  PresetGallery,
  Pagination,
  ScreenerDashboard,
} from '@/components/screener';
import { useMarketBreadth } from '@/hooks/useMarketBreadth';
import { useSectorHeatmap } from '@/hooks/useSectorHeatmap';
import { useScreenerPresets } from '@/hooks/useScreenerPresets';
import { screenerService } from '@/services/screenerService';
import type { ScreenerFilters, ScreenerStock } from '@/types/screener';

export default function ScreenerPage() {
  const [filters, setFilters] = useState<ScreenerFilters>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [results, setResults] = useState<ScreenerStock[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // API 호출
  const { data: breadthData } = useMarketBreadth();
  const { data: heatmapData } = useSectorHeatmap();
  const { data: presetsData } = useScreenerPresets();

  // 필터 적용 핸들러
  const handleFiltersApply = async (newFilters: ScreenerFilters) => {
    setFilters(newFilters);
    setPage(1); // 첫 페이지로 리셋
    await runScreener(newFilters, 1, pageSize);
  };

  // 스크리너 실행
  const runScreener = async (
    currentFilters: ScreenerFilters,
    currentPage: number,
    currentPageSize: number
  ) => {
    setIsSearching(true);
    try {
      const response = await screenerService.runScreener(
        currentFilters,
        currentPage,
        currentPageSize
      );
      setResults(response.data.stocks);
      // meta 데이터도 저장하여 Pagination에 전달
    } catch (error) {
      console.error('Screener error:', error);
    } finally {
      setIsSearching(false);
    }
  };

  // 페이지 변경
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    runScreener(filters, newPage, pageSize);
  };

  // 페이지 크기 변경
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setPage(1);
    runScreener(filters, 1, newSize);
  };

  return (
    <AuthGuard>
      <div className="container mx-auto px-4 py-6">
        <h1 className="text-3xl font-bold mb-6">Stock Screener</h1>

        {/* 대시보드 (Market Breadth + Heatmap + Presets) */}
        <ScreenerDashboard onFiltersApply={handleFiltersApply} />

        {/* 스크리너 결과 */}
        <div className="mt-8">
          {isSearching ? (
            <div>Loading...</div>
          ) : (
            <>
              <ScreenerTable stocks={results} />
              <Pagination
                currentPage={page}
                totalPages={10} // API meta에서 가져오기
                pageSize={pageSize}
                totalCount={results.length}
                hasNext={true}
                hasPrevious={page > 1}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            </>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
```

---

## 2. 개별 컴포넌트 통합

### 2.1 Market Breadth Card

기존 페이지에 Market Breadth 카드만 추가:

```tsx
import { MarketBreadthCard } from '@/components/screener';
import { useMarketBreadth } from '@/hooks/useMarketBreadth';

function MyPage() {
  const { data, isLoading, error } = useMarketBreadth();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* 기존 컴포넌트들 */}
      <div className="lg:col-span-1">
        <MarketBreadthCard
          data={data?.data!}
          isLoading={isLoading}
          error={error}
        />
      </div>
    </div>
  );
}
```

---

### 2.2 Sector Heatmap with Filter Integration

섹터 클릭 시 스크리너 필터 자동 적용:

```tsx
import { SectorHeatmap } from '@/components/screener';
import { useSectorHeatmap } from '@/hooks/useSectorHeatmap';

function MyPage() {
  const { data, isLoading, error } = useSectorHeatmap();
  const [sectorFilter, setSectorFilter] = useState<string[]>([]);

  const handleSectorClick = (sector: string) => {
    setSectorFilter([sector]);
    // 스크리너 실행 또는 필터 상태 업데이트
  };

  return (
    <SectorHeatmap
      sectors={data?.data.sectors || []}
      date={data?.data.date}
      isLoading={isLoading}
      error={error}
      onSectorClick={handleSectorClick}
    />
  );
}
```

---

### 2.3 Preset Gallery with Custom Presets

사용자 프리셋 생성/삭제 기능 추가:

```tsx
import { PresetGallery } from '@/components/screener';
import {
  useScreenerPresets,
  useCreatePreset,
  useDeletePreset,
} from '@/hooks/useScreenerPresets';
import type { CreatePresetPayload } from '@/types/screener';

function MyPage() {
  const { data, isLoading, error } = useScreenerPresets();
  const createMutation = useCreatePreset();
  const deleteMutation = useDeletePreset();

  const systemPresets = data?.data.filter((p) => p.is_system) || [];
  const userPresets = data?.data.filter((p) => !p.is_system) || [];

  const handleCreatePreset = async () => {
    const payload: CreatePresetPayload = {
      name: '내 프리셋',
      description_ko: '사용자 정의 필터 조합',
      category: 'custom',
      icon: 'star',
      filters_json: {
        min_market_cap: 1000000000,
        min_pe: 10,
        max_pe: 20,
      },
    };

    try {
      await createMutation.mutateAsync(payload);
      alert('프리셋이 생성되었습니다.');
    } catch (error) {
      alert('프리셋 생성에 실패했습니다.');
    }
  };

  const handleDeletePreset = async (presetId: number) => {
    if (confirm('이 프리셋을 삭제하시겠습니까?')) {
      try {
        await deleteMutation.mutateAsync(presetId);
      } catch (error) {
        alert('프리셋 삭제에 실패했습니다.');
      }
    }
  };

  return (
    <>
      <button onClick={handleCreatePreset}>새 프리셋 만들기</button>
      <PresetGallery
        presets={systemPresets}
        userPresets={userPresets}
        isLoading={isLoading}
        error={error}
        onPresetClick={(preset) => console.log(preset.filters_json)}
        onDeletePreset={handleDeletePreset}
      />
    </>
  );
}
```

---

### 2.4 Pagination with API Meta

백엔드 API 응답의 `meta` 데이터와 연동:

```tsx
import { Pagination } from '@/components/screener';
import { screenerService } from '@/services/screenerService';
import type { PaginationMeta } from '@/types/screener';

function MyPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);

  const runScreener = async () => {
    const response = await screenerService.runScreener({}, page, pageSize);
    setMeta(response.data.meta);
  };

  useEffect(() => {
    runScreener();
  }, [page, pageSize]);

  if (!meta) return <div>Loading...</div>;

  return (
    <Pagination
      currentPage={meta.page}
      totalPages={meta.total_pages}
      pageSize={meta.page_size}
      totalCount={meta.total_count}
      hasNext={meta.has_next}
      hasPrevious={meta.has_previous}
      onPageChange={setPage}
      onPageSizeChange={(size) => {
        setPageSize(size);
        setPage(1); // 페이지 크기 변경 시 첫 페이지로
      }}
    />
  );
}
```

---

## 3. Advanced Usage

### 3.1 필터 초기화 버튼

```tsx
const resetFilters = () => {
  setFilters({});
  setPage(1);
  runScreener({}, 1, pageSize);
};

<button onClick={resetFilters}>필터 초기화</button>;
```

---

### 3.2 프리셋 적용 후 수정

```tsx
const handlePresetClick = (preset: ScreenerPreset) => {
  // 프리셋 필터를 상태에 설정
  setFilters(preset.filters_json);
  // 사용자가 추가 수정 가능하도록 필터 UI 표시
  setShowFilterPanel(true);
};
```

---

### 3.3 날짜 선택 (Historical Data)

```tsx
const [selectedDate, setSelectedDate] = useState<string>();

const { data: breadthData } = useMarketBreadth(selectedDate);
const { data: heatmapData } = useSectorHeatmap(selectedDate);

<input
  type="date"
  value={selectedDate || ''}
  onChange={(e) => setSelectedDate(e.target.value)}
  max={new Date().toISOString().split('T')[0]}
/>;
```

---

## 4. Error Handling

모든 컴포넌트는 `isLoading`, `error` props를 지원합니다:

```tsx
const { data, isLoading, error } = useMarketBreadth();

if (error) {
  return (
    <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
      <p className="text-red-600 dark:text-red-400">
        데이터를 불러오는 중 오류가 발생했습니다.
      </p>
      <button onClick={() => refetch()}>다시 시도</button>
    </div>
  );
}
```

---

## 5. Performance Optimization

### 5.1 Query Stale Time

```tsx
// hooks/useMarketBreadth.ts
staleTime: 5 * 60 * 1000, // 5분 동안 캐시 유지
refetchInterval: 5 * 60 * 1000, // 5분마다 자동 갱신
```

### 5.2 Pagination Optimization

페이지 변경 시 스크롤 최상단으로 이동:

```tsx
const handlePageChange = (newPage: number) => {
  setPage(newPage);
  window.scrollTo({ top: 0, behavior: 'smooth' });
  runScreener(filters, newPage, pageSize);
};
```

---

## 6. Type Safety

모든 타입은 `@/types/screener.ts`에 정의되어 있으므로 타입 안정성이 보장됩니다:

```tsx
import type {
  ScreenerFilters,
  ScreenerStock,
  ScreenerPreset,
  PaginationMeta,
} from '@/types/screener';
```

---

## 7. Next Steps

1. **기존 스크리너 페이지 마이그레이션**: `app/screener/page.tsx`를 새 컴포넌트로 리팩토링
2. **필터 UI 개선**: 50개 필터를 직관적으로 선택할 수 있는 ScreenerFilters 컴포넌트 개발
3. **결과 테이블 최적화**: ScreenerTable에 정렬, CSV 내보내기, 즐겨찾기 추가 기능
4. **모바일 최적화**: 반응형 레이아웃 개선
