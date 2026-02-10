# ChainSightPanel 컴포넌트

Phase 2.2: Chain Sight DNA 패널 - 연관 종목 분석

## 개요

현재 필터링된 종목들과 연관된 종목을 자동으로 발견하는 패널입니다.

## 기능

1. **섹터 피어**: 동일 섹터에서 유사한 지표를 가진 종목 (최대 5개)
2. **유사 펀더멘탈**: PER/ROE 등 펀더멘탈 프로필이 유사한 종목 (최대 5개)
3. **AI 인사이트**: 연관 종목들의 공통 테마 설명
4. **접기/펼치기**: UI 공간 절약
5. **새로고침**: 실시간 데이터 갱신

## 사용법

```tsx
import { ChainSightPanel } from '@/components/screener';

<ChainSightPanel
  symbols={filteredStocks.map(s => s.symbol)}
  filters={currentFilters}
  isLoading={isLoadingScreener}
  className="mt-4"
/>
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| symbols | string[] | Yes | 현재 필터링된 종목 심볼 목록 |
| filters | ScreenerFilters | Yes | 적용된 필터 조건 |
| isLoading | boolean | No | 로딩 상태 (기본값: false) |
| className | string | No | 추가 CSS 클래스 |

## UI 상태

### 1. 로딩 상태
- 종목 카드 스켈레톤 (3개씩 표시)
- 새로고침 버튼 스피너

### 2. 빈 상태
- symbols 길이 0일 때 표시
- "필터를 조정하여 종목을 검색해보세요" 메시지

### 3. 정상 상태
- 섹터 피어 + 유사 펀더멘탈 섹션
- 각 섹션별 "더보기" 버튼 (3개 초과 시)
- AI 인사이트 패널 (하단)

## API 엔드포인트

```typescript
// POST /api/v1/serverless/chain-sight
{
  symbols: ["AAPL", "MSFT", ...],
  filters: { per_max: 30, roe_min: 15, ... }
}

// Response
{
  success: true,
  data: {
    sector_peers: [
      { symbol: "MSFT", reason: "...", similarity: 0.89, change_percent: 2.1 }
    ],
    fundamental_similar: [...],
    ai_insights: "이 종목들은...",
    chains_count: 8
  }
}
```

## 스타일

- 다크 테마: bg-[#161B22], border-[#30363D]
- 종목 카드: bg-[#0D1117] (hover 시 border 하이라이트)
- AI 인사이트: border-[#1F6FEB]/30, bg-[#1F6FEB]/10

## TODO

- [ ] 백엔드 API 구현 (serverless/views.py)
- [ ] 실제 API 호출로 교체 (현재 mock 데이터)
- [ ] 에러 핸들링 (API 실패 시 UI)
- [ ] 캐싱 전략 (TanStack Query)
- [ ] 종목 카드 툴팁 (similarity 점수 표시)
