# Screener Components

스크리너 업그레이드를 위한 프론트엔드 컴포넌트 모음입니다.

## 구성 요소

### 1. MarketBreadthCard
시장 폭 지표를 게이지 형태로 시각화하는 컴포넌트입니다.

```tsx
import { MarketBreadthCard } from '@/components/screener';
import { useMarketBreadth } from '@/hooks/useMarketBreadth';

function Example() {
  const { data, isLoading, error } = useMarketBreadth();

  return (
    <MarketBreadthCard
      data={data?.data!}
      isLoading={isLoading}
      error={error}
    />
  );
}
```

**Features**:
- 상승/하락 종목 수 표시
- A/D 비율 계산
- 5단계 신호 (strong_bullish, bullish, neutral, bearish, strong_bearish)
- SVG 게이지 시각화 (0-100%)

---

### 2. SectorHeatmap
11개 섹터의 수익률을 Treemap으로 시각화하는 컴포넌트입니다.

```tsx
import { SectorHeatmap } from '@/components/screener';
import { useSectorHeatmap } from '@/hooks/useSectorHeatmap';

function Example() {
  const { data, isLoading, error } = useSectorHeatmap();

  const handleSectorClick = (sector: string) => {
    console.log('Selected sector:', sector);
    // 필터 적용 로직
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

**Features**:
- Recharts Treemap 사용
- 색상: 수익률 (초록=상승, 노랑=보합, 빨강=하락)
- 크기: 시가총액
- 클릭 이벤트로 섹터 필터 적용 가능
- 커스텀 툴팁 (섹터명, 수익률, 종목 수, ETF 심볼)

---

### 3. PresetGallery
스크리너 프리셋을 카드 형태로 표시하는 컴포넌트입니다.

```tsx
import { PresetGallery } from '@/components/screener';
import { useScreenerPresets, useDeletePreset } from '@/hooks/useScreenerPresets';

function Example() {
  const { data, isLoading, error } = useScreenerPresets();
  const deletePresetMutation = useDeletePreset();

  const systemPresets = data?.data.filter(p => p.is_system) || [];
  const userPresets = data?.data.filter(p => !p.is_system) || [];

  const handlePresetClick = (preset: ScreenerPreset) => {
    // preset.filters_json을 스크리너에 적용
  };

  const handleDeletePreset = async (presetId: number) => {
    await deletePresetMutation.mutateAsync(presetId);
  };

  return (
    <PresetGallery
      presets={systemPresets}
      userPresets={userPresets}
      isLoading={isLoading}
      error={error}
      onPresetClick={handlePresetClick}
      onDeletePreset={handleDeletePreset}
    />
  );
}
```

**Features**:
- 카테고리별 분류 (초보자용, 중급자용, 기타, 내 프리셋)
- 아이콘 지원 (trending_up, dollar, shield, zap, target, rocket, heart, star)
- 사용 횟수 표시
- 사용자 프리셋 삭제 기능
- 반응형 그리드 레이아웃

---

### 4. Pagination
스크리너 결과 페이지네이션 컴포넌트입니다.

```tsx
import { Pagination } from '@/components/screener';
import type { PaginationMeta } from '@/types/screener';

function Example() {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // API 호출 후 받은 메타 데이터
  const meta: PaginationMeta = {
    page: 1,
    page_size: 20,
    total_count: 523,
    total_pages: 27,
    has_next: true,
    has_previous: false,
  };

  return (
    <Pagination
      currentPage={meta.page}
      totalPages={meta.total_pages}
      pageSize={meta.page_size}
      totalCount={meta.total_count}
      hasNext={meta.has_next}
      hasPrevious={meta.has_previous}
      onPageChange={(page) => setCurrentPage(page)}
      onPageSizeChange={(size) => setPageSize(size)}
    />
  );
}
```

**Features**:
- 첫/이전/다음/마지막 페이지 버튼
- 페이지 번호 버튼 (최대 7개 표시, 나머지는 ellipsis)
- 페이지 크기 선택 (20, 50, 100)
- 현재 표시 범위 (예: 1-20 / 523)
- 반응형 레이아웃

---

### 5. ScreenerDashboard
모든 컴포넌트를 통합한 대시보드 예제입니다.

```tsx
import { ScreenerDashboard } from '@/components/screener';
import type { ScreenerFilters } from '@/types/screener';

function ScreenerPage() {
  const handleFiltersApply = (filters: ScreenerFilters, sector?: string) => {
    console.log('Applying filters:', filters);
    if (sector) {
      console.log('Sector selected:', sector);
    }
    // 스크리너 실행 로직
  };

  return <ScreenerDashboard onFiltersApply={handleFiltersApply} />;
}
```

---

## API Endpoints

### Market Breadth
```
GET /api/v1/serverless/breadth?date=2026-01-29
```

### Sector Heatmap
```
GET /api/v1/serverless/heatmap/sectors?date=2026-01-29
```

### Presets
```
GET /api/v1/serverless/presets?category=beginner
POST /api/v1/serverless/presets
DELETE /api/v1/serverless/presets/{id}
```

### Screener
```
POST /api/v1/serverless/screener
Body: { filters: {...}, page: 1, page_size: 20 }
```

---

## Type Definitions

모든 타입은 `@/types/screener.ts`에 정의되어 있습니다:
- `MarketBreadthData`, `MarketBreadthResponse`
- `SectorPerformance`, `SectorHeatmapResponse`
- `ScreenerPreset`, `ScreenerPresetsResponse`
- `ScreenerFilters`, `ScreenerStock`, `ScreenerResponse`
- `PaginationMeta`, `PaginationProps`

---

## Hooks

### useMarketBreadth
```tsx
const { data, isLoading, error } = useMarketBreadth(date?: string);
```

### useSectorHeatmap
```tsx
const { data, isLoading, error } = useSectorHeatmap(date?: string);
```

### useScreenerPresets
```tsx
const { data, isLoading, error } = useScreenerPresets(category?: string);
const createMutation = useCreatePreset();
const deleteMutation = useDeletePreset();
```

---

## Styling

모든 컴포넌트는 Tailwind CSS를 사용하며, 다크 모드를 지원합니다.

**사용된 아이콘**:
- lucide-react (TrendingUp, TrendingDown, ChevronLeft, etc.)

**차트 라이브러리**:
- recharts (Treemap)

---

## 향후 작업

1. **Advanced Screener 통합**: 필터 엔진과 페이지네이션을 실제 스크리너 페이지에 통합
2. **사용자 프리셋 생성 UI**: 현재 필터 조합을 프리셋으로 저장하는 모달 추가
3. **필터 UI 개선**: 50개 필터를 직관적으로 선택할 수 있는 ScreenerFilters 컴포넌트
4. **결과 테이블**: ScreenerStock[]을 표시하는 ScreenerTable 컴포넌트 (정렬, CSV 내보내기)
