# Market Movers LLM 키워드 시스템 - 프론트엔드 설계

## 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [컴포넌트 구조](#컴포넌트-구조)
4. [타입 시스템](#타입-시스템)
5. [API 통합](#api-통합)
6. [성능 최적화](#성능-최적화)
7. [스타일 가이드](#스타일-가이드)
8. [사용 예시](#사용-예시)
9. [백엔드 요구사항](#백엔드-요구사항)
10. [다음 단계](#다음-단계)

---

## 개요

Market Movers 종목에 대해 LLM(Claude)이 생성한 투자 시그널 키워드를 실시간으로 표시하는 프론트엔드 시스템.

### 주요 기능

- **6가지 카테고리 키워드**: 촉매, 기술적, 심리, 거시, 섹터, 리스크
- **실시간 배치 조회**: N+1 쿼리 방지를 위한 배치 API 사용
- **인터랙티브 UI**: 호버 툴팁, 클릭 이벤트, 신뢰도 표시
- **다크모드 지원**: Tailwind CSS 기반 반응형 디자인
- **캐싱 최적화**: TanStack Query로 10분 캐싱

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  Market Movers Page                     │
│              (app/market-pulse/page.tsx)                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│         MarketMoversSectionOptimized                    │
│  - useMarketMovers() → TOP 20 종목 조회                 │
│  - useBatchKeywords(symbols) → 배치 키워드 조회 (1번)   │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌────────────────┐        ┌────────────────┐
│ MoverCardWith  │   x20  │  KeywordList   │
│ BatchKeywords  │ ─────▶ │  (keywords[])  │
└────────────────┘        └────────┬───────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
            ┌──────────────┐              ┌──────────────┐
            │ KeywordTag   │   x3         │ KeywordTag   │
            │ (CATALYST)   │              │ (TECHNICAL)  │
            └──────────────┘              └──────────────┘
```

---

## 컴포넌트 구조

### 1. KeywordTag (components/keywords/KeywordTag.tsx)

개별 키워드 태그 컴포넌트.

**Props**:
```typescript
interface KeywordTagProps {
  keyword: Keyword;
  onClick?: (keyword: Keyword) => void;
  showTooltip?: boolean;
  showConfidence?: boolean;
  size?: 'sm' | 'md';
}
```

**기능**:
- 카테고리별 색상 자동 적용
- 호버 시 툴팁 표시 (카테고리, 설명, 신뢰도)
- 클릭 이벤트 핸들러 (선택)
- 다크모드 지원

**스타일링**:
```tsx
// CATALYST 예시
bg-purple-50 text-purple-700 border-purple-200
dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-700
```

### 2. KeywordList (components/keywords/KeywordList.tsx)

키워드 리스트 컨테이너.

**Props**:
```typescript
interface KeywordListProps {
  keywords: Keyword[];
  isLoading?: boolean;
  error?: Error | null;
  onKeywordClick?: (keyword: Keyword) => void;
  maxVisible?: number;
  showConfidence?: boolean;
  emptyMessage?: string;
  layout?: 'horizontal' | 'vertical';
  size?: 'sm' | 'md';
}
```

**기능**:
- 로딩 상태: 스피너 + "AI 분석 중..."
- 에러 상태: 에러 아이콘 + "키워드 로딩 실패"
- 빈 상태: Sparkles 아이콘 + 커스텀 메시지
- maxVisible 초과 시 "+N" 배지 표시

### 3. MoverCardWithBatchKeywords (components/market-pulse/MoverCardWithBatchKeywords.tsx)

배치 최적화 버전 MoverCard.

**Props**:
```typescript
interface MoverCardWithBatchKeywordsProps {
  mover: MarketMoverItem;
  keywords?: StockKeywords;
  keywordsLoading?: boolean;
  keywordsError?: Error | null;
  showKeywords?: boolean;
}
```

**차이점**:
- 기존 MoverCard: `useKeywords(symbol)` 개별 조회 (N+1 쿼리)
- 신규 버전: 부모에서 `useBatchKeywords()` 결과를 props로 전달

### 4. MarketMoversSectionOptimized (components/market-pulse/MarketMoversSectionOptimized.tsx)

배치 최적화 섹션.

**핵심 로직**:
```typescript
const symbols = useMemo(() => movers.map(m => m.symbol), [movers]);
const { data: batchKeywordsData } = useBatchKeywords(symbols, date);
const keywordsMap = batchKeywordsData?.data ?? {};

// 카드에 전달
<MoverCardWithBatchKeywords
  mover={mover}
  keywords={keywordsMap[mover.symbol]}
  keywordsLoading={keywordsLoading}
/>
```

---

## 타입 시스템

### Keyword 타입 (types/keyword.ts)

```typescript
export enum KeywordCategory {
  CATALYST = 'catalyst',      // 촉매
  TECHNICAL = 'technical',    // 기술적
  SENTIMENT = 'sentiment',    // 심리
  MACRO = 'macro',            // 거시
  SECTOR = 'sector',          // 섹터
  RISK = 'risk',              // 리스크
}

export interface Keyword {
  id: string;
  text: string;               // "어닝 서프라이즈"
  category: KeywordCategory;
  confidence: number;         // 0.0 ~ 1.0
  description?: string;       // 툴팁용 설명
}

export interface StockKeywords {
  symbol: string;
  date: string;
  keywords: Keyword[];
  generated_at: string;
  llm_model?: string;
}
```

### API 응답 타입

**단일 조회**:
```typescript
export interface KeywordAPIResponse {
  success: boolean;
  data?: StockKeywords;
  error?: { code: string; message: string };
}
```

**배치 조회**:
```typescript
export interface BatchKeywordsResponse {
  success: boolean;
  data?: {
    [symbol: string]: StockKeywords;
  };
  error?: { code: string; message: string };
}
```

---

## API 통합

### 1. Service Layer (services/keywordService.ts)

```typescript
export const keywordService = {
  // 단일 조회
  async getKeywords(symbol: string, date?: string): Promise<KeywordAPIResponse>

  // 배치 조회 (권장)
  async getBatchKeywords(request: BatchKeywordsRequest): Promise<BatchKeywordsResponse>

  // 재생성 (관리자)
  async regenerateKeywords(symbol: string, date?: string): Promise<KeywordAPIResponse>

  // 전체 생성 (Celery)
  async generateAllKeywords(type: MoverType, date?: string)
}
```

### 2. Custom Hooks (hooks/useKeywords.ts)

```typescript
// 단일 조회
export function useKeywords(symbol: string, date?: string)

// 배치 조회 (권장)
export function useBatchKeywords(symbols: string[], date?: string)

// Mutation
export function useRegenerateKeywords()
export function useGenerateAllKeywords()
```

**쿼리 키 전략**:
```typescript
const QUERY_KEYS = {
  keywords: (symbol: string, date?: string) =>
    ['keywords', symbol.toUpperCase(), date] as const,

  batchKeywords: (symbols: string[], date?: string) =>
    ['keywords-batch', symbols.map(s => s.toUpperCase()).sort(), date] as const,

  allKeywords: ['keywords'] as const,
};
```

---

## 성능 최적화

### 1. N+1 쿼리 방지

**문제**:
```tsx
// ❌ Bad: 20번의 API 요청
movers.map(mover => <MoverCard mover={mover} />)
// 각 MoverCard 내부에서 useKeywords(symbol) 호출
```

**해결**:
```tsx
// ✅ Good: 1번의 배치 API 요청
const symbols = movers.map(m => m.symbol);
const { data } = useBatchKeywords(symbols);

movers.map(mover => (
  <MoverCardWithBatchKeywords
    mover={mover}
    keywords={data?.[mover.symbol]}
  />
))
```

### 2. React.memo 최적화

모든 컴포넌트는 `memo`로 래핑:
```typescript
export const KeywordTag = memo(function KeywordTag({ ... }) { ... });
export const KeywordList = memo(function KeywordList({ ... }) { ... });
export const MoverCardWithBatchKeywords = memo(function MoverCardWithBatchKeywords({ ... }) { ... });
```

### 3. 캐싱 전략

```typescript
// TanStack Query 설정
{
  staleTime: 10 * 60 * 1000,  // 10분
  enabled: !!symbol,          // symbol이 있을 때만 실행
}
```

**이유**:
- LLM 생성 데이터는 자주 변경되지 않음
- Market Movers는 일일 1회 업데이트 (Celery Beat)
- 5분 캐싱 (FMP API)과 동기화

### 4. useMemo 최적화

```typescript
const symbols = useMemo(() => movers.map(m => m.symbol), [movers]);
const { data } = useBatchKeywords(symbols, date);
```

---

## 스타일 가이드

### 카테고리별 색상

| Category | Light | Dark | Border |
|----------|-------|------|--------|
| CATALYST | purple-50/700 | purple-900/20 + purple-300 | purple-200/700 |
| TECHNICAL | blue-50/700 | blue-900/20 + blue-300 | blue-200/700 |
| SENTIMENT | amber-50/700 | amber-900/20 + amber-300 | amber-200/700 |
| MACRO | emerald-50/700 | emerald-900/20 + emerald-300 | emerald-200/700 |
| SECTOR | indigo-50/700 | indigo-900/20 + indigo-300 | indigo-200/700 |
| RISK | red-50/700 | red-900/20 + red-300 | red-200/700 |

### 신뢰도 색상

```typescript
const confidenceColor = (conf: number) => {
  if (conf >= 0.8) return 'text-emerald-600 dark:text-emerald-400';  // High
  if (conf >= 0.6) return 'text-amber-600 dark:text-amber-400';      // Medium
  return 'text-gray-500 dark:text-gray-400';                         // Low
};
```

### 툴팁 스타일

```tsx
<div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-20 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-[10px] leading-relaxed rounded shadow-lg">
  {/* 내용 */}
  <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
    <div className="w-2 h-2 bg-gray-900 dark:bg-gray-700 rotate-45" />
  </div>
</div>
```

---

## 사용 예시

### 1. MarketMoversSection 교체 (권장)

**기존**:
```tsx
// app/market-pulse/page.tsx
import { MarketMoversSection } from '@/components/market-pulse/MarketMoversSection';

<MarketMoversSection />
```

**신규**:
```tsx
// app/market-pulse/page.tsx
import { MarketMoversSectionOptimized } from '@/components/market-pulse/MarketMoversSectionOptimized';

<MarketMoversSectionOptimized />
```

### 2. 커스텀 페이지에서 사용

```tsx
import { useBatchKeywords } from '@/hooks/useKeywords';
import { KeywordList } from '@/components/keywords/KeywordList';

function MyWatchlistPage() {
  const symbols = ['AAPL', 'TSLA', 'NVDA'];
  const { data, isLoading } = useBatchKeywords(symbols);

  return (
    <>
      {symbols.map(symbol => (
        <div key={symbol}>
          <h3>{symbol}</h3>
          <KeywordList
            keywords={data?.data?.[symbol]?.keywords ?? []}
            isLoading={isLoading}
            maxVisible={5}
            showConfidence={true}
          />
        </div>
      ))}
    </>
  );
}
```

### 3. 키워드 클릭 이벤트

```tsx
import { useRouter } from 'next/navigation';
import { KeywordList } from '@/components/keywords/KeywordList';

function MyComponent({ keywords }: { keywords: Keyword[] }) {
  const router = useRouter();

  const handleKeywordClick = (keyword: Keyword) => {
    // 키워드 클릭 시 필터링 페이지로 이동
    router.push(`/stocks/filter?keyword=${keyword.text}&category=${keyword.category}`);
  };

  return (
    <KeywordList
      keywords={keywords}
      onKeywordClick={handleKeywordClick}
    />
  );
}
```

---

## 백엔드 요구사항

### API 엔드포인트

#### 1. 단일 종목 키워드 조회

```http
GET /api/v1/serverless/keywords/{symbol}?date=2026-01-07
```

**응답**:
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
      }
    ],
    "generated_at": "2026-01-07T10:30:00Z",
    "llm_model": "claude-3-5-sonnet-20241022"
  }
}
```

#### 2. 배치 조회 (중요!)

```http
POST /api/v1/serverless/keywords/batch
Content-Type: application/json

{
  "symbols": ["AAPL", "TSLA", "NVDA"],
  "date": "2026-01-07"
}
```

**응답**:
```json
{
  "success": true,
  "data": {
    "AAPL": {
      "symbol": "AAPL",
      "date": "2026-01-07",
      "keywords": [...]
    },
    "TSLA": {
      "symbol": "TSLA",
      "date": "2026-01-07",
      "keywords": [...]
    }
  }
}
```

#### 3. 키워드 재생성 (관리자)

```http
POST /api/v1/serverless/keywords/{symbol}/regenerate
Content-Type: application/json

{
  "date": "2026-01-07"
}
```

#### 4. Market Movers 전체 키워드 생성 (Celery)

```http
POST /api/v1/serverless/keywords/generate-all
Content-Type: application/json

{
  "type": "gainers",
  "date": "2026-01-07"
}
```

### 데이터베이스 스키마 (예시)

```python
# serverless/models.py

class StockKeyword(models.Model):
    symbol = models.CharField(max_length=10)
    date = models.DateField()
    keywords = models.JSONField()  # [{ id, text, category, confidence, description }]
    generated_at = models.DateTimeField(auto_now_add=True)
    llm_model = models.CharField(max_length=100, default='claude-3-5-sonnet-20241022')

    class Meta:
        unique_together = ('symbol', 'date')
        indexes = [
            models.Index(fields=['symbol', 'date']),
            models.Index(fields=['date']),
        ]
```

### LLM 프롬프트 예시

```python
# serverless/services/keyword_generator.py

KEYWORD_PROMPT = """
Analyze the following stock data and generate 3-5 investment signal keywords.

Stock: {symbol}
Date: {date}
Price Change: {change_percent}%
Volume: {volume}
RVOL: {rvol}
Trend Strength: {trend_strength}
Sector Alpha: {sector_alpha}
ETF Sync Rate: {etf_sync_rate}
Volatility Percentile: {volatility_pct}

Generate keywords in the following categories:
1. CATALYST: Earnings, product launches, M&A
2. TECHNICAL: Chart patterns, breakouts, indicators
3. SENTIMENT: Short interest, momentum, liquidity
4. MACRO: Interest rates, currency, commodities
5. SECTOR: Sector trends, thematic plays
6. RISK: High volatility, overextension warnings

Return JSON:
{{
  "keywords": [
    {{
      "text": "키워드 텍스트 (한글)",
      "category": "catalyst|technical|sentiment|macro|sector|risk",
      "confidence": 0.0-1.0,
      "description": "상세 설명 (1문장)"
    }}
  ]
}}
"""
```

---

## 다음 단계

### Phase 1: 백엔드 API 구현 (@backend, @rag-llm)

- [ ] `/api/v1/serverless/keywords/{symbol}` 엔드포인트
- [ ] `/api/v1/serverless/keywords/batch` 배치 조회
- [ ] `StockKeyword` 모델 생성
- [ ] LLM 프롬프트 설계 및 테스트
- [ ] Celery 태스크: `generate_daily_keywords`

### Phase 2: 프론트엔드 통합 (@frontend)

- [x] 타입 정의 (types/keyword.ts)
- [x] API Service (services/keywordService.ts)
- [x] Custom Hooks (hooks/useKeywords.ts)
- [x] KeywordTag, KeywordList 컴포넌트
- [x] MoverCardWithBatchKeywords 컴포넌트
- [x] MarketMoversSectionOptimized
- [ ] app/market-pulse/page.tsx에서 기존 섹션 교체
- [ ] 키워드 클릭 이벤트 구현 (필터링 페이지 연동)

### Phase 3: QA 및 최적화 (@qa)

- [ ] 단위 테스트: KeywordTag, KeywordList
- [ ] 통합 테스트: API 호출 + 캐싱
- [ ] 성능 테스트: 배치 조회 속도 (20개 종목)
- [ ] 접근성 테스트: ARIA labels, 키보드 내비게이션
- [ ] 다크모드 테스트

### Phase 4: 콘텐츠 검증 (@investment-advisor)

- [ ] 키워드 카테고리 체계 검토
- [ ] 예시 키워드 작성 (카테고리별 10개)
- [ ] 툴팁 설명 문구 검토
- [ ] LLM 프롬프트 피드백

---

## 체크리스트

**프론트엔드 완료**:
- [x] 타입 정의
- [x] API Service
- [x] Custom Hooks
- [x] 기본 컴포넌트 (KeywordTag, KeywordList)
- [x] 배치 최적화 컴포넌트
- [x] 설계 문서 작성

**백엔드 필요**:
- [ ] API 엔드포인트 4개
- [ ] StockKeyword 모델
- [ ] LLM 프롬프트 설계
- [ ] Celery 태스크

**통합 테스트 필요**:
- [ ] API 연동 테스트
- [ ] 배치 조회 성능 테스트
- [ ] 캐싱 동작 확인
- [ ] 에러 핸들링 테스트

---

## 참고 문서

- TanStack Query: https://tanstack.com/query/latest
- Tailwind CSS: https://tailwindcss.com/docs
- Market Movers 5개 지표: `CLAUDE.md` 참고
- RAG Analysis: `docs/RAG_ANALYSIS_PHASE3.md`
