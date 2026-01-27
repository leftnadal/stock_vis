# LLM 키워드 시스템 - 프론트엔드

## 개요

Market Movers 종목에 대해 LLM이 생성한 투자 시그널 키워드를 표시하는 시스템입니다.

## 컴포넌트 구조

```
components/keywords/
├── KeywordTag.tsx          # 개별 키워드 태그 (툴팁, 호버 효과)
├── KeywordList.tsx         # 키워드 리스트 (로딩/에러 상태 처리)
└── README.md               # 이 문서

components/market-pulse/
├── MoverCard.tsx                      # 기본 카드 (개별 조회)
├── MoverCardWithBatchKeywords.tsx     # 배치 최적화 카드
├── MarketMoversSection.tsx            # 기존 섹션
└── MarketMoversSectionOptimized.tsx   # 배치 최적화 섹션 (권장)
```

## 사용법

### 1. 개별 종목 키워드 조회 (기본)

```tsx
import { useKeywords } from '@/hooks/useKeywords';
import { KeywordList } from '@/components/keywords/KeywordList';

function MyComponent({ symbol }: { symbol: string }) {
  const { data, isLoading, error } = useKeywords(symbol);
  const keywords = data?.data?.keywords ?? [];

  return (
    <KeywordList
      keywords={keywords}
      isLoading={isLoading}
      error={error}
      maxVisible={3}
      size="sm"
    />
  );
}
```

### 2. 배치 조회 (N+1 쿼리 방지 - 권장)

```tsx
import { useBatchKeywords } from '@/hooks/useKeywords';
import { KeywordList } from '@/components/keywords/KeywordList';

function MyComponent({ symbols }: { symbols: string[] }) {
  const { data, isLoading, error } = useBatchKeywords(symbols);
  const keywordsMap = data?.data ?? {};

  return (
    <>
      {symbols.map(symbol => (
        <div key={symbol}>
          <h3>{symbol}</h3>
          <KeywordList
            keywords={keywordsMap[symbol]?.keywords ?? []}
            isLoading={isLoading}
            error={error}
            maxVisible={3}
          />
        </div>
      ))}
    </>
  );
}
```

### 3. Market Movers에 통합 (최종 사용법)

**방법 A: 기존 MoverCard 사용 (개별 조회)**

```tsx
import { MoverCard } from '@/components/market-pulse/MoverCard';

<MoverCard mover={mover} showKeywords={true} />
```

**방법 B: 배치 최적화 버전 사용 (권장)**

```tsx
import { MarketMoversSectionOptimized } from '@/components/market-pulse/MarketMoversSectionOptimized';

// app/market-pulse/page.tsx 에서
<MarketMoversSectionOptimized />
```

## 컴포넌트 Props

### KeywordTag

| Prop | Type | Default | 설명 |
|------|------|---------|------|
| keyword | Keyword | (required) | 키워드 객체 |
| onClick | (keyword: Keyword) => void | undefined | 클릭 핸들러 |
| showTooltip | boolean | true | 툴팁 표시 여부 |
| showConfidence | boolean | false | 신뢰도 표시 여부 |
| size | 'sm' \| 'md' | 'sm' | 크기 |

### KeywordList

| Prop | Type | Default | 설명 |
|------|------|---------|------|
| keywords | Keyword[] | (required) | 키워드 배열 |
| isLoading | boolean | false | 로딩 상태 |
| error | Error \| null | null | 에러 객체 |
| onKeywordClick | (keyword: Keyword) => void | undefined | 클릭 핸들러 |
| maxVisible | number | undefined | 최대 표시 개수 |
| showConfidence | boolean | false | 신뢰도 표시 여부 |
| emptyMessage | string | '키워드가 없습니다' | 빈 상태 메시지 |
| layout | 'horizontal' \| 'vertical' | 'horizontal' | 레이아웃 |
| size | 'sm' \| 'md' | 'sm' | 크기 |

## 키워드 카테고리

| Category | 한글명 | 색상 | 예시 키워드 |
|----------|--------|------|------------|
| CATALYST | 촉매 | Purple | 어닝 서프라이즈, 신제품 발표, M&A |
| TECHNICAL | 기술적 | Blue | 골든크로스, 브레이크아웃, 지지선 이탈 |
| SENTIMENT | 심리 | Amber | 공매도 급증, 모멘텀 강화, 유동성 집중 |
| MACRO | 거시 | Emerald | 금리 인하 수혜, 환율 영향, 원자재 강세 |
| SECTOR | 섹터 | Indigo | 섹터 강세, 테마주, 동종 대비 우위 |
| RISK | 리스크 | Red | 고변동성, 이격도 과도, 단기 과열 |

## 캐싱 전략

```typescript
// TanStack Query 설정
{
  staleTime: 10 * 60 * 1000,  // 10분 (LLM 생성 데이터는 자주 변경되지 않음)
  enabled: !!symbol,          // symbol이 있을 때만 실행
}
```

## 성능 최적화

### N+1 쿼리 방지

Market Movers는 TOP 20 종목을 표시하므로, 각 카드마다 개별 API 호출 시 20번의 요청 발생.

**해결책**: `useBatchKeywords()` 사용

```tsx
// ❌ Bad: N+1 쿼리 (20번 요청)
movers.map(mover => <MoverCard mover={mover} />)

// ✅ Good: 배치 조회 (1번 요청)
const symbols = movers.map(m => m.symbol);
const { data } = useBatchKeywords(symbols);
movers.map(mover => (
  <MoverCardWithBatchKeywords
    mover={mover}
    keywords={data?.[mover.symbol]}
  />
))
```

### memo 최적화

모든 컴포넌트는 `React.memo`로 래핑되어 불필요한 리렌더링 방지.

## 스타일링

Tailwind CSS 사용, 다크모드 지원.

```tsx
// 카테고리별 색상 자동 적용
<KeywordTag keyword={keyword} />

// 커스텀 색상 (선택)
<KeywordTag keyword={{ ...keyword, color: 'bg-pink-500' }} />
```

## API 엔드포인트 (백엔드 구현 필요)

```bash
# 단일 조회
GET /api/v1/serverless/keywords/{symbol}?date=2026-01-07

# 배치 조회
POST /api/v1/serverless/keywords/batch
Body: { "symbols": ["AAPL", "TSLA", ...], "date": "2026-01-07" }

# 재생성 (관리자)
POST /api/v1/serverless/keywords/{symbol}/regenerate
Body: { "date": "2026-01-07" }

# 전체 생성 (Celery)
POST /api/v1/serverless/keywords/generate-all
Body: { "type": "gainers", "date": "2026-01-07" }
```

## 응답 형식

```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "date": "2026-01-07",
    "keywords": [
      {
        "id": "1",
        "text": "어닝 서프라이즈",
        "category": "catalyst",
        "confidence": 0.92,
        "description": "실적 발표 예상치 상회로 강한 상승 모멘텀"
      },
      {
        "id": "2",
        "text": "골든크로스",
        "category": "technical",
        "confidence": 0.85,
        "description": "50일선이 200일선 상향 돌파"
      }
    ],
    "generated_at": "2026-01-07T10:30:00Z",
    "llm_model": "claude-3-5-sonnet-20241022"
  }
}
```

## 다음 단계

1. @backend: API 엔드포인트 구현
2. @rag-llm: LLM 프롬프트 설계 및 키워드 생성 로직
3. @frontend: 기존 MarketMoversSection을 MarketMoversSectionOptimized로 교체
4. @qa: 통합 테스트

## 참고

- TanStack Query Docs: https://tanstack.com/query/latest
- Tailwind CSS: https://tailwindcss.com/docs
- Lucide Icons: https://lucide.dev
