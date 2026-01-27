# Stock-Vis Market Pulse 기능 확장 - 멀티 에이전트 프롬프트

> **버전**: v1.0.0  
> **작성일**: 2025-12-16  
> **목표**: FMP API 기반 실시간 시장 지표(상승/하락/거래량 TOP)를 Market Pulse에 추가

---

## 📋 프로젝트 개요

### 기능 요약
헤더 네비게이션의 **Market Pulse** 페이지에 FMP API를 활용한 실시간 시장 지표 추가:
- 상승률 TOP 종목 (Gainers)
- 하락률 TOP 종목 (Losers)  
- 거래량 TOP 종목 (Most Active)

### 핵심 목표
1. **초보 투자자 교육**: 단순 데이터 나열이 아닌, "왜 이 종목이 움직이는가" 설명
2. **Chain Sight 연계**: 급등/급락 종목을 분석의 시작점으로 활용
3. **DataBasket 통합**: 관심 종목을 바로 분석 바구니에 담기

### FMP API 엔드포인트
```
GET /api/v3/gainers?apikey={API_KEY}     # 상승률 TOP
GET /api/v3/losers?apikey={API_KEY}      # 하락률 TOP  
GET /api/v3/actives?apikey={API_KEY}     # 거래량 TOP
```

### 응답 형식
```json
[
  {
    "symbol": "TSLA",
    "name": "Tesla Inc",
    "price": 250.45,
    "change": 12.50,
    "changesPercentage": 5.26
  }
]
```

---

## 🎯 에이전트별 작업 정의

### 실행 순서
```
Phase 1 (동시 진행)
├── Backend: API 통합, 캐싱, Django REST API
├── Frontend: 컴포넌트, React Query, 실시간 업데이트  
└── Infra: Redis 설정, 환경변수, 모니터링

Phase 2 (Phase 1 완료 후)
├── Investment-Advisor: 교육 콘텐츠, 인사이트 규칙
└── UI-UX-Designer: 디자인 시스템, 인터랙션

Phase 3 (Phase 2 완료 후)
├── QA-Architect: 테스트 전략, 자동화
└── KB-Curator: 문서화, 교육 자료
```

---

## 🤖 Agent 1: Backend Developer

### 컨텍스트
```yaml
프로젝트: Stock-Vis
기술스택: Django 4.2, DRF, PostgreSQL, Redis, Celery
기존구조: apps/stocks/, apps/analysis/, apps/news/
API제한: FMP 무료 티어 250회/일
```

### 작업 목표
FMP API 연동 및 Market Movers 데이터 제공 API 구축

### 세부 작업

#### 1. FMP 서비스 클래스 생성
**파일**: `apps/stocks/services/fmp_service.py`

```python
"""
FMP API 서비스
- 상승/하락/거래량 TOP 종목 조회
- Redis 캐싱으로 API 호출 최소화
- Rate Limit 관리
"""

import httpx
from django.conf import settings
from django.core.cache import cache
from typing import Literal
import logging

logger = logging.getLogger(__name__)


class FMPService:
    """FMP API 클라이언트"""
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    CACHE_TTL = 300  # 5분 캐싱
    
    def __init__(self):
        self.api_key = settings.FMP_API_KEY
        
    async def get_market_movers(
        self, 
        mover_type: Literal['gainers', 'losers', 'actives'],
        limit: int = 10
    ) -> list[dict]:
        """
        시장 주도 종목 조회
        
        Args:
            mover_type: 'gainers' | 'losers' | 'actives'
            limit: 반환할 종목 수 (기본 10개)
            
        Returns:
            종목 리스트 [{symbol, name, price, change, changesPercentage}, ...]
        """
        cache_key = f"fmp:market_movers:{mover_type}"
        
        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached[:limit]
        
        # API 호출
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/{mover_type}",
                    params={"apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()
                
            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: {mover_type}, {len(data)}개 종목")
            
            return data[:limit]
            
        except httpx.HTTPError as e:
            logger.error(f"FMP API 오류: {e}")
            # 캐시된 이전 데이터 반환 시도
            stale = cache.get(f"{cache_key}:stale")
            if stale:
                logger.warning("이전 캐시 데이터 반환")
                return stale[:limit]
            return []
        
    async def get_all_movers(self, limit: int = 10) -> dict:
        """상승/하락/거래량 TOP 전체 조회"""
        import asyncio
        
        gainers, losers, actives = await asyncio.gather(
            self.get_market_movers('gainers', limit),
            self.get_market_movers('losers', limit),
            self.get_market_movers('actives', limit),
            return_exceptions=True
        )
        
        return {
            "gainers": gainers if not isinstance(gainers, Exception) else [],
            "losers": losers if not isinstance(losers, Exception) else [],
            "actives": actives if not isinstance(actives, Exception) else [],
            "cached_at": cache.get("fmp:market_movers:timestamp"),
        }
```

#### 2. Serializer 작성
**파일**: `apps/stocks/serializers/market_movers.py`

```python
from rest_framework import serializers


class MarketMoverSerializer(serializers.Serializer):
    """시장 주도 종목 Serializer"""
    symbol = serializers.CharField()
    name = serializers.CharField()
    price = serializers.FloatField()
    change = serializers.FloatField()
    changes_percentage = serializers.FloatField(source='changesPercentage')
    
    # 프론트엔드를 위한 추가 필드
    direction = serializers.SerializerMethodField()
    formatted_change = serializers.SerializerMethodField()
    
    def get_direction(self, obj) -> str:
        """상승/하락 방향"""
        return 'up' if obj.get('change', 0) >= 0 else 'down'
    
    def get_formatted_change(self, obj) -> str:
        """포맷된 변동률 (+5.26%)"""
        pct = obj.get('changesPercentage', 0)
        sign = '+' if pct >= 0 else ''
        return f"{sign}{pct:.2f}%"


class MarketMoversResponseSerializer(serializers.Serializer):
    """Market Movers API 응답 Serializer"""
    gainers = MarketMoverSerializer(many=True)
    losers = MarketMoverSerializer(many=True)
    actives = MarketMoverSerializer(many=True)
    cached_at = serializers.DateTimeField(allow_null=True)
    last_updated = serializers.DateTimeField()
```

#### 3. API View 작성
**파일**: `apps/stocks/views/market_movers.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from asgiref.sync import async_to_sync

from ..services.fmp_service import FMPService
from ..serializers.market_movers import MarketMoversResponseSerializer


class MarketMoversView(APIView):
    """
    Market Movers API
    
    GET /api/v1/stocks/market-movers/
    
    Query Parameters:
        - limit: 각 카테고리별 종목 수 (기본 10, 최대 20)
    
    Response:
        {
            "gainers": [...],
            "losers": [...],
            "actives": [...],
            "cached_at": "2025-12-16T10:00:00Z",
            "last_updated": "2025-12-16T10:05:00Z"
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        limit = min(int(request.query_params.get('limit', 10)), 20)
        
        service = FMPService()
        data = async_to_sync(service.get_all_movers)(limit=limit)
        data['last_updated'] = timezone.now()
        
        serializer = MarketMoversResponseSerializer(data)
        return Response(serializer.data)
```

#### 4. URL 등록
**파일**: `apps/stocks/urls.py` (추가)

```python
from .views.market_movers import MarketMoversView

urlpatterns += [
    path('market-movers/', MarketMoversView.as_view(), name='market-movers'),
]
```

#### 5. 환경변수 설정
**파일**: `.env` (추가)

```env
# FMP API
FMP_API_KEY=your_fmp_api_key_here
FMP_CACHE_TTL=300
```

### 산출물 체크리스트
- [ ] `apps/stocks/services/fmp_service.py` 생성
- [ ] `apps/stocks/serializers/market_movers.py` 생성
- [ ] `apps/stocks/views/market_movers.py` 생성
- [ ] `apps/stocks/urls.py` 업데이트
- [ ] `.env` FMP_API_KEY 추가
- [ ] `config/settings/base.py` FMP 설정 추가
- [ ] API 테스트 통과

---

## 🤖 Agent 2: Frontend Developer

### 컨텍스트
```yaml
프로젝트: Stock-Vis Frontend
기술스택: Next.js 14, TypeScript, TailwindCSS, React Query, Zustand
기존구조: src/app/, src/components/, src/hooks/, src/types/
디자인시스템: Chain Sight 철학 (연결된 발견의 흐름)
```

### 작업 목표
Market Pulse 페이지에 Market Movers 섹션 추가

### 세부 작업

#### 1. 타입 정의
**파일**: `src/types/market.ts`

```typescript
/**
 * Market Movers 타입 정의
 */

export interface MarketMover {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changesPercentage: number;
  direction: 'up' | 'down';
  formattedChange: string;
}

export interface MarketMoversResponse {
  gainers: MarketMover[];
  losers: MarketMover[];
  actives: MarketMover[];
  cachedAt: string | null;
  lastUpdated: string;
}

export type MoverType = 'gainers' | 'losers' | 'actives';

export interface MoverTabConfig {
  id: MoverType;
  label: string;
  labelKo: string;
  icon: string;
  color: string;
  description: string;
}

export const MOVER_TABS: MoverTabConfig[] = [
  {
    id: 'gainers',
    label: 'Top Gainers',
    labelKo: '상승 TOP',
    icon: '📈',
    color: 'text-green-500',
    description: '오늘 가장 많이 오른 종목들이에요',
  },
  {
    id: 'losers',
    label: 'Top Losers',
    labelKo: '하락 TOP',
    icon: '📉',
    color: 'text-red-500',
    description: '오늘 가장 많이 내린 종목들이에요',
  },
  {
    id: 'actives',
    label: 'Most Active',
    labelKo: '거래량 TOP',
    icon: '🔥',
    color: 'text-orange-500',
    description: '오늘 가장 활발하게 거래되는 종목들이에요',
  },
];
```

#### 2. API 클라이언트
**파일**: `src/lib/api/market.ts`

```typescript
import { apiClient } from './client';
import type { MarketMoversResponse } from '@/types/market';

/**
 * Market Movers API
 */
export const marketApi = {
  /**
   * 상승/하락/거래량 TOP 종목 조회
   */
  getMarketMovers: async (limit: number = 10): Promise<MarketMoversResponse> => {
    const response = await apiClient.get<MarketMoversResponse>(
      '/stocks/market-movers/',
      { params: { limit } }
    );
    return response.data;
  },
};
```

#### 3. React Query Hook
**파일**: `src/hooks/useMarketMovers.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { marketApi } from '@/lib/api/market';
import type { MarketMoversResponse, MoverType } from '@/types/market';

/**
 * Market Movers 데이터 훅
 */
export function useMarketMovers(limit: number = 10) {
  return useQuery<MarketMoversResponse>({
    queryKey: ['market-movers', limit],
    queryFn: () => marketApi.getMarketMovers(limit),
    staleTime: 5 * 60 * 1000, // 5분
    refetchInterval: 5 * 60 * 1000, // 5분마다 자동 갱신
  });
}

/**
 * 특정 타입의 Movers만 가져오는 훅
 */
export function useMovers(type: MoverType, limit: number = 10) {
  const { data, ...rest } = useMarketMovers(limit);
  
  return {
    data: data?.[type] ?? [],
    ...rest,
  };
}
```

#### 4. Mover Card 컴포넌트
**파일**: `src/components/market-pulse/MoverCard.tsx`

```tsx
'use client';

import { memo } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { MarketMover } from '@/types/market';
import { useDataBasket } from '@/hooks/useDataBasket';

interface MoverCardProps {
  mover: MarketMover;
  rank: number;
  showAddToBasket?: boolean;
}

/**
 * 개별 종목 카드
 * - 호버 시 간단한 정보 표시
 * - 클릭 시 종목 상세 페이지로 이동
 * - DataBasket에 추가 가능
 */
export const MoverCard = memo(function MoverCard({
  mover,
  rank,
  showAddToBasket = true,
}: MoverCardProps) {
  const { addItem } = useDataBasket();
  const isPositive = mover.direction === 'up';
  
  const handleAddToBasket = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    addItem({
      type: 'stock',
      symbol: mover.symbol,
      name: mover.name,
    });
  };
  
  return (
    <Link
      href={`/stocks/${mover.symbol}`}
      className={cn(
        'group flex items-center gap-3 p-3 rounded-lg',
        'bg-gray-800/50 hover:bg-gray-700/50',
        'transition-all duration-200',
        'border border-transparent hover:border-gray-600'
      )}
    >
      {/* 순위 */}
      <span className="w-6 text-center text-sm text-gray-500 font-mono">
        {rank}
      </span>
      
      {/* 종목 정보 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white truncate">
            {mover.symbol}
          </span>
          {showAddToBasket && (
            <button
              onClick={handleAddToBasket}
              className={cn(
                'opacity-0 group-hover:opacity-100',
                'p-1 rounded hover:bg-gray-600',
                'transition-opacity duration-200'
              )}
              title="분석 바구니에 담기"
            >
              🧺
            </button>
          )}
        </div>
        <p className="text-sm text-gray-400 truncate">
          {mover.name}
        </p>
      </div>
      
      {/* 가격 및 변동 */}
      <div className="text-right">
        <p className="font-mono text-white">
          ${mover.price.toLocaleString(undefined, { 
            minimumFractionDigits: 2,
            maximumFractionDigits: 2 
          })}
        </p>
        <p className={cn(
          'text-sm font-mono',
          isPositive ? 'text-green-400' : 'text-red-400'
        )}>
          {mover.formattedChange}
        </p>
      </div>
    </Link>
  );
});
```

#### 5. Market Movers 섹션 컴포넌트
**파일**: `src/components/market-pulse/MarketMoversSection.tsx`

```tsx
'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { useMarketMovers } from '@/hooks/useMarketMovers';
import { MoverCard } from './MoverCard';
import { MOVER_TABS, type MoverType } from '@/types/market';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Market Movers 섹션
 * - 탭으로 상승/하락/거래량 TOP 전환
 * - 초보 투자자를 위한 설명 포함
 */
export function MarketMoversSection() {
  const [activeTab, setActiveTab] = useState<MoverType>('gainers');
  const { data, isLoading, error, dataUpdatedAt } = useMarketMovers(10);
  
  const activeConfig = MOVER_TABS.find(tab => tab.id === activeTab)!;
  const movers = data?.[activeTab] ?? [];
  
  return (
    <section className="bg-gray-900 rounded-xl p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-white">
          📊 오늘의 시장 움직임
        </h2>
        {dataUpdatedAt && (
          <span className="text-xs text-gray-500">
            {new Date(dataUpdatedAt).toLocaleTimeString('ko-KR')} 기준
          </span>
        )}
      </div>
      
      {/* 탭 네비게이션 */}
      <div className="flex gap-2 mb-4">
        {MOVER_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg',
              'text-sm font-medium transition-all duration-200',
              activeTab === tab.id
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            )}
          >
            <span>{tab.icon}</span>
            <span>{tab.labelKo}</span>
          </button>
        ))}
      </div>
      
      {/* 설명 (초보자 교육) */}
      <p className="text-sm text-gray-400 mb-4 p-3 bg-gray-800/50 rounded-lg">
        💡 {activeConfig.description}
        {activeTab === 'gainers' && (
          <span className="block mt-1 text-xs text-gray-500">
            급등 종목은 좋은 뉴스나 실적 발표가 있을 수 있어요. 
            클릭해서 자세히 알아보세요!
          </span>
        )}
        {activeTab === 'losers' && (
          <span className="block mt-1 text-xs text-gray-500">
            급락 종목은 저가 매수 기회일 수도, 피해야 할 신호일 수도 있어요.
            뉴스를 확인해보세요.
          </span>
        )}
        {activeTab === 'actives' && (
          <span className="block mt-1 text-xs text-gray-500">
            거래량이 많다는 건 시장의 관심이 집중되고 있다는 뜻이에요.
          </span>
        )}
      </p>
      
      {/* 종목 리스트 */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-8 text-red-400">
          데이터를 불러오는 중 오류가 발생했어요. 
          잠시 후 다시 시도해주세요.
        </div>
      ) : (
        <div className="space-y-2">
          {movers.map((mover, index) => (
            <MoverCard 
              key={mover.symbol} 
              mover={mover} 
              rank={index + 1} 
            />
          ))}
        </div>
      )}
      
      {/* 푸터 - Chain Sight 연계 */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <p className="text-xs text-gray-500 text-center">
          🔗 종목을 클릭하면 상세 분석 페이지로 이동해요. 
          🧺 버튼으로 분석 바구니에 담아 한번에 비교해보세요!
        </p>
      </div>
    </section>
  );
}
```

#### 6. Market Pulse 페이지 업데이트
**파일**: `src/app/market-pulse/page.tsx` (수정)

```tsx
import { MarketMoversSection } from '@/components/market-pulse/MarketMoversSection';
// ... 기존 import

export default function MarketPulsePage() {
  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <h1 className="text-3xl font-bold text-white mb-8">
        🌍 Market Pulse
      </h1>
      
      {/* 새로 추가: Market Movers 섹션 */}
      <MarketMoversSection />
      
      {/* 기존 섹션들 */}
      {/* ... */}
    </div>
  );
}
```

### 산출물 체크리스트
- [ ] `src/types/market.ts` 생성
- [ ] `src/lib/api/market.ts` 생성
- [ ] `src/hooks/useMarketMovers.ts` 생성
- [ ] `src/components/market-pulse/MoverCard.tsx` 생성
- [ ] `src/components/market-pulse/MarketMoversSection.tsx` 생성
- [ ] `src/app/market-pulse/page.tsx` 업데이트
- [ ] 반응형 레이아웃 확인
- [ ] DataBasket 연동 테스트

---

## 🤖 Agent 3: Infrastructure Engineer

### 컨텍스트
```yaml
환경: AWS (EC2, ElastiCache, CloudWatch)
캐시: Redis 6.x
CI/CD: GitHub Actions
모니터링: CloudWatch, Sentry
```

### 작업 목표
FMP API 연동을 위한 인프라 설정 및 모니터링

### 세부 작업

#### 1. 환경변수 설정
**파일**: `.env.example` (업데이트)

```env
# ===================
# FMP API 설정
# ===================
FMP_API_KEY=your_api_key_here
FMP_BASE_URL=https://financialmodelingprep.com/api/v3
FMP_CACHE_TTL=300
FMP_DAILY_LIMIT=250

# ===================
# Redis 캐시 설정
# ===================
REDIS_URL=redis://localhost:6379/0
REDIS_MARKET_MOVERS_TTL=300
```

#### 2. Redis 캐시 설정
**파일**: `config/settings/base.py` (추가)

```python
# FMP API 설정
FMP_API_KEY = env('FMP_API_KEY')
FMP_BASE_URL = env('FMP_BASE_URL', default='https://financialmodelingprep.com/api/v3')
FMP_CACHE_TTL = env.int('FMP_CACHE_TTL', default=300)
FMP_DAILY_LIMIT = env.int('FMP_DAILY_LIMIT', default=250)

# Redis 캐시 설정 (Market Movers 전용 키 프리픽스)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'stockvis',
    }
}
```

#### 3. Rate Limit 모니터링
**파일**: `apps/stocks/services/rate_limiter.py`

```python
"""
FMP API Rate Limit 관리
- 일일 호출 횟수 추적
- 제한 초과 시 경고
"""

from django.core.cache import cache
from django.conf import settings
from datetime import date
import logging

logger = logging.getLogger(__name__)


class FMPRateLimiter:
    """FMP API Rate Limiter"""
    
    DAILY_LIMIT = settings.FMP_DAILY_LIMIT
    
    @classmethod
    def get_today_key(cls) -> str:
        return f"fmp:rate_limit:{date.today().isoformat()}"
    
    @classmethod
    def get_usage(cls) -> int:
        """오늘 사용량 조회"""
        return cache.get(cls.get_today_key(), 0)
    
    @classmethod
    def increment(cls) -> int:
        """사용량 증가"""
        key = cls.get_today_key()
        try:
            # atomic increment
            new_count = cache.incr(key)
        except ValueError:
            # 키가 없으면 생성
            cache.set(key, 1, timeout=86400)  # 24시간
            new_count = 1
        
        # 80% 도달 시 경고
        if new_count == int(cls.DAILY_LIMIT * 0.8):
            logger.warning(f"FMP API 일일 한도 80% 도달: {new_count}/{cls.DAILY_LIMIT}")
        
        # 100% 도달 시 에러
        if new_count >= cls.DAILY_LIMIT:
            logger.error(f"FMP API 일일 한도 초과: {new_count}/{cls.DAILY_LIMIT}")
        
        return new_count
    
    @classmethod
    def can_call(cls) -> bool:
        """API 호출 가능 여부"""
        return cls.get_usage() < cls.DAILY_LIMIT
    
    @classmethod
    def get_remaining(cls) -> int:
        """남은 호출 횟수"""
        return max(0, cls.DAILY_LIMIT - cls.get_usage())
```

#### 4. CloudWatch 알람 설정
**파일**: `infrastructure/cloudwatch/fmp_alarms.tf`

```hcl
# FMP API 관련 CloudWatch 알람

resource "aws_cloudwatch_metric_alarm" "fmp_rate_limit_warning" {
  alarm_name          = "stockvis-fmp-rate-limit-warning"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FMPAPIUsage"
  namespace           = "StockVis/API"
  period              = 3600
  statistic           = "Maximum"
  threshold           = 200  # 250의 80%
  alarm_description   = "FMP API 일일 한도 80% 도달"
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "fmp_error_rate" {
  alarm_name          = "stockvis-fmp-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FMPAPIErrors"
  namespace           = "StockVis/API"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "FMP API 에러 급증"
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

### 산출물 체크리스트
- [ ] `.env.example` FMP 설정 추가
- [ ] `config/settings/base.py` FMP/Redis 설정 추가
- [ ] `apps/stocks/services/rate_limiter.py` 생성
- [ ] CloudWatch 알람 설정
- [ ] Sentry 에러 추적 설정
- [ ] GitHub Secrets 업데이트

---

## 🤖 Agent 4: Investment Advisor (AI)

### 컨텍스트
```yaml
역할: 초보 투자자 교육을 위한 인사이트 생성
목표: 단순 데이터가 아닌 "왜"와 "어떻게"를 설명
원칙: Chain Sight - 하나의 발견이 다음 발견으로 연결
```

### 작업 목표
Market Movers 데이터에 교육적 컨텍스트 추가

### 세부 작업

#### 1. 인사이트 규칙 정의
**파일**: `apps/analysis/constants/market_insights.py`

```python
"""
Market Movers 인사이트 규칙
초보 투자자가 데이터를 이해하도록 돕는 설명 생성
"""

# 상승률 기반 인사이트
GAINER_INSIGHTS = {
    'extreme': {  # 20% 이상
        'message': '🚀 급등주 주의! 이 정도 상승은 흔치 않아요.',
        'tip': '뉴스를 꼭 확인하세요. 실적 발표나 M&A 가능성이 있어요.',
        'caution': '단기 급등 후 조정이 올 수 있으니 신중하게 접근하세요.',
    },
    'high': {  # 10-20%
        'message': '📈 강한 상승세를 보이고 있어요.',
        'tip': '섹터 전체가 오르는지, 이 종목만 오르는지 확인해보세요.',
        'caution': None,
    },
    'moderate': {  # 5-10%
        'message': '✨ 건강한 상승이에요.',
        'tip': '거래량도 함께 늘었다면 더 좋은 신호예요.',
        'caution': None,
    },
    'mild': {  # 0-5%
        'message': '📊 소폭 상승했어요.',
        'tip': '장기적인 추세를 함께 보는 게 좋아요.',
        'caution': None,
    },
}

# 하락률 기반 인사이트
LOSER_INSIGHTS = {
    'extreme': {  # -20% 이하
        'message': '⚠️ 급락 발생! 무슨 일이 있는지 확인이 필요해요.',
        'tip': '실적 쇼크, 소송, 리콜 등 부정적 뉴스가 있을 수 있어요.',
        'caution': '"싸게 사자"는 위험할 수 있어요. 원인을 먼저 파악하세요.',
    },
    'high': {  # -20% ~ -10%
        'message': '📉 큰 폭의 하락이에요.',
        'tip': '시장 전체가 하락 중인지, 이 종목만 하락하는지 확인하세요.',
        'caution': '하락 원인이 일시적인지 구조적인지 판단이 필요해요.',
    },
    'moderate': {  # -10% ~ -5%
        'message': '🔻 조정 구간이에요.',
        'tip': '최근 많이 올랐던 종목이라면 자연스러운 조정일 수 있어요.',
        'caution': None,
    },
    'mild': {  # -5% ~ 0%
        'message': '📊 소폭 하락했어요.',
        'tip': '하루의 변동으로 판단하기보다 추세를 보세요.',
        'caution': None,
    },
}

# 거래량 기반 인사이트
ACTIVE_INSIGHTS = {
    'mega': {  # 평균의 5배 이상
        'message': '🔥 폭발적인 거래량! 시장의 주목을 받고 있어요.',
        'tip': '기관이나 큰 손이 움직이고 있을 수 있어요.',
        'caution': '거래량 급증 후에는 변동성이 커질 수 있어요.',
    },
    'high': {  # 평균의 2-5배
        'message': '📊 평소보다 거래가 활발해요.',
        'tip': '뉴스나 실적 발표가 있는지 확인해보세요.',
        'caution': None,
    },
    'normal': {
        'message': '📈 정상적인 거래량이에요.',
        'tip': '꾸준한 거래량은 건강한 시장 참여를 의미해요.',
        'caution': None,
    },
}


def get_gainer_insight(change_pct: float) -> dict:
    """상승률에 따른 인사이트 반환"""
    if change_pct >= 20:
        return GAINER_INSIGHTS['extreme']
    elif change_pct >= 10:
        return GAINER_INSIGHTS['high']
    elif change_pct >= 5:
        return GAINER_INSIGHTS['moderate']
    else:
        return GAINER_INSIGHTS['mild']


def get_loser_insight(change_pct: float) -> dict:
    """하락률에 따른 인사이트 반환"""
    if change_pct <= -20:
        return LOSER_INSIGHTS['extreme']
    elif change_pct <= -10:
        return LOSER_INSIGHTS['high']
    elif change_pct <= -5:
        return LOSER_INSIGHTS['moderate']
    else:
        return LOSER_INSIGHTS['mild']
```

#### 2. 교육 콘텐츠 정의 (프론트엔드용)
**파일**: `src/constants/education/marketMovers.ts`

```typescript
/**1
 * Market Movers 교육 콘텐츠
 * 초보 투자자를 위한 용어 설명 및 팁
 */

export const MARKET_MOVERS_EDUCATION = {
  // 용어 설명
  terms: {
    gainer: {
      title: '상승주 (Gainer)',
      simple: '오늘 가격이 오른 주식이에요',
      detail: '전일 종가 대비 현재 가격이 올랐을 때 상승주라고 해요. 좋은 뉴스, 실적 개선, 시장 기대감 등이 원인일 수 있어요.',
    },
    loser: {
      title: '하락주 (Loser)',
      simple: '오늘 가격이 내린 주식이에요',
      detail: '전일 종가 대비 현재 가격이 떨어졌을 때 하락주라고 해요. 부정적 뉴스, 실적 악화, 시장 불안 등이 원인일 수 있어요.',
    },
    active: {
      title: '거래량 상위 (Most Active)',
      simple: '오늘 가장 많이 거래된 주식이에요',
      detail: '거래량이 많다는 건 그만큼 사고 싶은 사람과 팔고 싶은 사람이 많다는 뜻이에요. 시장의 관심이 집중된 종목이죠.',
    },
  },
  
  // 초보자 팁
  tips: [
    {
      id: 'dont-chase',
      title: '급등주 추격 매수 주의',
      content: '이미 많이 오른 주식을 따라 사면 고점에 물릴 수 있어요. 왜 올랐는지 먼저 파악하세요.',
    },
    {
      id: 'check-news',
      title: '뉴스 확인은 필수',
      content: '큰 변동이 있는 종목은 반드시 뉴스를 확인하세요. 클릭하면 관련 뉴스를 볼 수 있어요.',
    },
    {
      id: 'volume-matters',
      title: '거래량도 중요해요',
      content: '가격 변동이 거래량 증가와 함께라면 더 의미 있는 움직임이에요.',
    },
    {
      id: 'sector-check',
      title: '섹터도 살펴보세요',
      content: '이 종목만 오르는지, 같은 업종 전체가 오르는지 비교해보세요.',
    },
  ],
  
  // Chain Sight 연결 힌트
  chainSightHints: {
    gainer: [
      '이 종목과 같은 섹터의 다른 종목도 확인해보세요',
      '관련 뉴스에서 언급된 다른 회사도 있을 수 있어요',
      '경쟁사는 어떻게 움직이고 있는지 비교해보세요',
    ],
    loser: [
      '하락 원인이 업종 전체에 영향을 줄 수 있어요',
      '공급업체나 고객사도 영향받을 수 있어요',
      '비슷한 상황의 과거 사례를 찾아보세요',
    ],
    active: [
      '왜 관심이 집중되는지 뉴스를 확인하세요',
      '기관 투자자 매매 동향도 살펴보세요',
      '관련 ETF도 거래량이 늘었는지 확인해보세요',
    ],
  },
};
```

### 산출물 체크리스트
- [ ] `apps/analysis/constants/market_insights.py` 생성
- [ ] `src/constants/education/marketMovers.ts` 생성
- [ ] 인사이트 API 엔드포인트 연동 (Backend 협업)
- [ ] Chain Sight 연결 로직 정의

---

## 🤖 Agent 5: UI/UX Designer

### 컨텍스트
```yaml
디자인시스템: Effortless Flow 철학
핵심원칙: Low-Action High-Discovery, Chain Sight DNA
컬러: Dark Theme (Gray 900 베이스)
폰트: Pretendard (한글), Inter (영문), JetBrains Mono (숫자)
```

### 작업 목표
Market Movers UI 디자인 시스템 정의

### 세부 작업

#### 1. 컬러 시스템
```css
/* Market Movers 전용 컬러 */
:root {
  /* 상승 */
  --color-gain-primary: #22c55e;    /* green-500 */
  --color-gain-secondary: #86efac;  /* green-300 */
  --color-gain-bg: rgba(34, 197, 94, 0.1);
  
  /* 하락 */
  --color-loss-primary: #ef4444;    /* red-500 */
  --color-loss-secondary: #fca5a5;  /* red-300 */
  --color-loss-bg: rgba(239, 68, 68, 0.1);
  
  /* 거래량 */
  --color-active-primary: #f97316;  /* orange-500 */
  --color-active-secondary: #fdba74; /* orange-300 */
  --color-active-bg: rgba(249, 115, 22, 0.1);
  
  /* 중립/배경 */
  --color-bg-card: #1f2937;         /* gray-800 */
  --color-bg-hover: #374151;        /* gray-700 */
  --color-border: #4b5563;          /* gray-600 */
}
```

#### 2. 카드 디자인 스펙
```
┌─────────────────────────────────────────────────────────┐
│  1   TSLA                                     $250.45  │
│       Tesla Inc                               +5.26%   │
│                                                  🧺    │
└─────────────────────────────────────────────────────────┘

크기:
- 높이: 64px (패딩 포함)
- 패딩: 12px 16px
- 보더 라디우스: 8px
- 간격 (카드 간): 8px

폰트:
- 순위: 14px, mono, gray-500
- 심볼: 16px, semibold, white
- 회사명: 14px, regular, gray-400
- 가격: 16px, mono, white
- 변동률: 14px, mono, green-400/red-400

인터랙션:
- 호버: bg-gray-700, border-gray-600
- 클릭: scale 0.98, 200ms
- 바구니 버튼: 호버 시 나타남 (opacity 0 → 1)
```

#### 3. 탭 디자인 스펙
```
┌───────────────────────────────────────────────────────┐
│  [📈 상승 TOP]  [📉 하락 TOP]  [🔥 거래량 TOP]        │
└───────────────────────────────────────────────────────┘

활성 탭:
- 배경: gray-700
- 텍스트: white
- 폰트: 14px, medium

비활성 탭:
- 배경: transparent
- 텍스트: gray-400
- 호버: gray-800, white

전환 애니메이션: 200ms ease-out
```

#### 4. 반응형 브레이크포인트
```
Mobile (< 640px):
- 카드 세로 스택
- 탭 스크롤 가능
- 설명 텍스트 간략화

Tablet (640px - 1024px):
- 2열 그리드
- 탭 전체 표시

Desktop (> 1024px):
- 단일 열 리스트
- 호버 효과 전체 활성화
```

### 산출물 체크리스트
- [ ] Figma 디자인 파일 생성
- [ ] 컴포넌트 라이브러리 업데이트
- [ ] 반응형 디자인 가이드
- [ ] 인터랙션 스펙 문서
- [ ] 접근성 체크리스트 (WCAG 2.1 AA)

---

## 🤖 Agent 6: QA Architect

### 컨텍스트
```yaml
테스트프레임워크: pytest (Backend), Jest/Vitest (Frontend)
E2E: Playwright
CI: GitHub Actions
커버리지목표: 80%
```

### 작업 목표
Market Movers 기능의 테스트 전략 수립 및 자동화

### 세부 작업

#### 1. 백엔드 테스트
**파일**: `apps/stocks/tests/test_market_movers.py`

```python
"""
Market Movers API 테스트
"""

import pytest
from unittest.mock import patch, AsyncMock
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def api_client(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        email='test@test.com', 
        password='testpass123'
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def mock_fmp_response():
    return [
        {
            "symbol": "TSLA",
            "name": "Tesla Inc",
            "price": 250.45,
            "change": 12.50,
            "changesPercentage": 5.26
        },
        {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "price": 175.20,
            "change": 3.50,
            "changesPercentage": 2.04
        },
    ]


class TestMarketMoversAPI:
    """Market Movers API 테스트"""
    
    @pytest.mark.django_db
    @patch('apps.stocks.services.fmp_service.FMPService.get_all_movers')
    async def test_get_market_movers_success(
        self, mock_get_movers, api_client, mock_fmp_response
    ):
        """정상 조회 테스트"""
        mock_get_movers.return_value = {
            'gainers': mock_fmp_response,
            'losers': mock_fmp_response,
            'actives': mock_fmp_response,
            'cached_at': None,
        }
        
        url = reverse('market-movers')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'gainers' in response.data
        assert 'losers' in response.data
        assert 'actives' in response.data
        assert len(response.data['gainers']) == 2
    
    @pytest.mark.django_db
    def test_market_movers_requires_auth(self):
        """인증 필요 테스트"""
        client = APIClient()
        url = reverse('market-movers')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.django_db
    @patch('apps.stocks.services.fmp_service.FMPService.get_all_movers')
    async def test_market_movers_limit_param(
        self, mock_get_movers, api_client, mock_fmp_response
    ):
        """limit 파라미터 테스트"""
        mock_get_movers.return_value = {
            'gainers': mock_fmp_response[:1],
            'losers': mock_fmp_response[:1],
            'actives': mock_fmp_response[:1],
            'cached_at': None,
        }
        
        url = reverse('market-movers')
        response = api_client.get(url, {'limit': 1})
        
        assert response.status_code == status.HTTP_200_OK
        mock_get_movers.assert_called_once_with(limit=1)


class TestFMPService:
    """FMP Service 단위 테스트"""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_get_market_movers_caching(self, mock_get):
        """캐싱 동작 테스트"""
        from apps.stocks.services.fmp_service import FMPService
        from django.core.cache import cache
        
        mock_response = AsyncMock()
        mock_response.json.return_value = [{"symbol": "TEST"}]
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response
        
        service = FMPService()
        
        # 첫 번째 호출 - API 호출됨
        result1 = await service.get_market_movers('gainers')
        assert mock_get.call_count == 1
        
        # 두 번째 호출 - 캐시에서 반환
        result2 = await service.get_market_movers('gainers')
        assert mock_get.call_count == 1  # 추가 호출 없음
        
        cache.clear()
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_get_market_movers_error_handling(self, mock_get):
        """에러 처리 테스트"""
        from apps.stocks.services.fmp_service import FMPService
        import httpx
        
        mock_get.side_effect = httpx.HTTPError("API Error")
        
        service = FMPService()
        result = await service.get_market_movers('gainers')
        
        assert result == []  # 에러 시 빈 리스트 반환
```

#### 2. 프론트엔드 테스트
**파일**: `src/components/market-pulse/__tests__/MarketMoversSection.test.tsx`

```typescript
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketMoversSection } from '../MarketMoversSection';

const mockMoversData = {
  gainers: [
    { symbol: 'TSLA', name: 'Tesla Inc', price: 250.45, change: 12.5, changesPercentage: 5.26, direction: 'up', formattedChange: '+5.26%' },
  ],
  losers: [
    { symbol: 'META', name: 'Meta Platforms', price: 300.00, change: -15.0, changesPercentage: -4.76, direction: 'down', formattedChange: '-4.76%' },
  ],
  actives: [
    { symbol: 'AAPL', name: 'Apple Inc', price: 175.20, change: 3.5, changesPercentage: 2.04, direction: 'up', formattedChange: '+2.04%' },
  ],
  cachedAt: null,
  lastUpdated: '2025-12-16T10:00:00Z',
};

// Mock API
jest.mock('@/lib/api/market', () => ({
  marketApi: {
    getMarketMovers: jest.fn().mockResolvedValue(mockMoversData),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('MarketMoversSection', () => {
  it('기본 탭(상승 TOP)이 선택되어 있어야 함', async () => {
    render(<MarketMoversSection />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('상승 TOP')).toHaveClass('bg-gray-700');
    });
  });
  
  it('종목 카드가 올바르게 렌더링되어야 함', async () => {
    render(<MarketMoversSection />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('TSLA')).toBeInTheDocument();
      expect(screen.getByText('Tesla Inc')).toBeInTheDocument();
      expect(screen.getByText('+5.26%')).toBeInTheDocument();
    });
  });
  
  it('탭 전환이 정상 동작해야 함', async () => {
    render(<MarketMoversSection />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('TSLA')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('하락 TOP'));
    
    await waitFor(() => {
      expect(screen.getByText('META')).toBeInTheDocument();
      expect(screen.getByText('-4.76%')).toBeInTheDocument();
    });
  });
  
  it('로딩 상태가 표시되어야 함', () => {
    render(<MarketMoversSection />, { wrapper: createWrapper() });
    
    // 초기 로딩 시 스켈레톤 표시
    expect(screen.getAllByTestId('skeleton')).toHaveLength(5);
  });
});
```

#### 3. E2E 테스트
**파일**: `e2e/market-pulse.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Market Pulse - Market Movers', () => {
  test.beforeEach(async ({ page }) => {
    // 로그인
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@test.com');
    await page.fill('[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });
  
  test('Market Pulse 페이지 접근 및 Market Movers 표시', async ({ page }) => {
    await page.goto('/market-pulse');
    
    // Market Movers 섹션 확인
    await expect(page.getByText('오늘의 시장 움직임')).toBeVisible();
    
    // 탭 확인
    await expect(page.getByText('상승 TOP')).toBeVisible();
    await expect(page.getByText('하락 TOP')).toBeVisible();
    await expect(page.getByText('거래량 TOP')).toBeVisible();
  });
  
  test('탭 전환 및 데이터 로드', async ({ page }) => {
    await page.goto('/market-pulse');
    
    // 하락 TOP 탭 클릭
    await page.click('text=하락 TOP');
    
    // 하락 종목 데이터 로드 확인
    await expect(page.locator('.text-red-400')).toBeVisible();
  });
  
  test('종목 카드 클릭 시 상세 페이지 이동', async ({ page }) => {
    await page.goto('/market-pulse');
    
    // 첫 번째 종목 카드 클릭
    await page.click('[data-testid="mover-card"]:first-child');
    
    // 상세 페이지로 이동 확인
    await expect(page).toHaveURL(/\/stocks\/.+/);
  });
  
  test('DataBasket에 종목 추가', async ({ page }) => {
    await page.goto('/market-pulse');
    
    // 바구니 버튼 호버 후 클릭
    await page.hover('[data-testid="mover-card"]:first-child');
    await page.click('[data-testid="add-to-basket"]');
    
    // 토스트 메시지 확인
    await expect(page.getByText('분석 바구니에 추가됨')).toBeVisible();
  });
});
```

### 산출물 체크리스트
- [ ] `apps/stocks/tests/test_market_movers.py` 생성
- [ ] `src/components/market-pulse/__tests__/` 테스트 생성
- [ ] `e2e/market-pulse.spec.ts` 생성
- [ ] GitHub Actions CI 파이프라인 업데이트
- [ ] 테스트 커버리지 리포트 설정

---

## 🤖 Agent 7: KB Curator

### 컨텍스트
```yaml
지식베이스: LESSONS_LEARNED.md, patterns/, troubleshooting/
목표: 개발 과정에서 얻은 교훈과 패턴 문서화
```

### 작업 목표
Market Movers 기능 관련 지식 문서화

### 세부 작업

#### 1. 패턴 문서
**파일**: `docs/patterns/external-api-integration.md`

```markdown
# 외부 API 통합 패턴

## 개요
FMP API 통합 경험을 바탕으로 한 외부 API 통합 모범 사례

## 핵심 원칙

### 1. 캐싱 우선
- 모든 외부 API 호출은 캐시를 먼저 확인
- TTL은 데이터 특성에 맞게 설정 (실시간: 5분, 정적: 24시간)
- Stale-While-Revalidate 패턴 적용 가능

### 2. Rate Limit 관리
- 일일/분당 호출 제한 추적
- 80% 도달 시 경고, 100% 도달 시 에러 로깅
- Graceful Degradation: 한도 초과 시 캐시 데이터 반환

### 3. 에러 처리
- 타임아웃 설정 (권장: 10초)
- 재시도 로직 (최대 3회, 지수 백오프)
- Fallback 데이터 제공

## 코드 템플릿

```python
class ExternalAPIService:
    CACHE_TTL = 300
    MAX_RETRIES = 3
    TIMEOUT = 10
    
    async def fetch_with_cache(self, endpoint: str, cache_key: str):
        # 1. 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # 2. Rate Limit 확인
        if not self.rate_limiter.can_call():
            return self._get_fallback(cache_key)
        
        # 3. API 호출 (재시도 포함)
        for attempt in range(self.MAX_RETRIES):
            try:
                data = await self._call_api(endpoint)
                cache.set(cache_key, data, self.CACHE_TTL)
                return data
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    return self._get_fallback(cache_key)
                await asyncio.sleep(2 ** attempt)
```

## 관련 문서
- [FMP API 문서](https://financialmodelingprep.com/developer/docs/)
- [Redis 캐싱 전략](/docs/architecture/caching.md)
```

#### 2. 트러블슈팅 가이드
**파일**: `docs/troubleshooting/fmp-api.md`

```markdown
# FMP API 트러블슈팅 가이드

## 일반적인 문제

### 1. Rate Limit 초과 (429 에러)
**증상**: API 호출 시 429 응답
**원인**: 일일 250회 호출 제한 초과
**해결**:
1. Rate Limit 사용량 확인: `redis-cli GET fmp:rate_limit:2025-12-16`
2. 캐시 TTL 증가 고려
3. 불필요한 API 호출 최소화

### 2. 빈 응답
**증상**: API 응답이 빈 배열
**원인**: 
- 시장 휴장일
- 프리마켓/애프터마켓 시간
**해결**:
- 시장 운영 시간 확인
- 캐시된 이전 데이터 표시

### 3. 타임아웃
**증상**: API 호출 시 타임아웃
**원인**: FMP 서버 응답 지연
**해결**:
1. 타임아웃 값 조정 (기본 10초)
2. 재시도 로직 확인
3. FMP 상태 페이지 확인

## 모니터링

### CloudWatch 알람
- `stockvis-fmp-rate-limit-warning`: 80% 도달
- `stockvis-fmp-error-rate`: 에러 급증

### 로그 확인
```bash
# 백엔드 로그
docker logs stockvis-backend | grep "FMP"

# Redis 캐시 상태
redis-cli KEYS "fmp:*"
```
```

### 산출물 체크리스트
- [ ] `docs/patterns/external-api-integration.md` 생성
- [ ] `docs/troubleshooting/fmp-api.md` 생성
- [ ] `LESSONS_LEARNED.md` 업데이트
- [ ] API 문서 (Swagger/OpenAPI) 업데이트

---

## 📅 실행 계획

### Phase 1: 기반 구축 (1주차)

| 일차 | 에이전트 | 작업 |
|------|----------|------|
| 1-2 | Backend | FMP Service, API View 구현 |
| 1-2 | Frontend | 타입 정의, API 클라이언트 |
| 1-2 | Infra | 환경변수, Redis 설정 |
| 3-4 | Frontend | 컴포넌트 개발 |
| 5 | 전체 | 통합 테스트 |

### Phase 2: 고도화 (2주차)

| 일차 | 에이전트 | 작업 |
|------|----------|------|
| 1-2 | Investment-Advisor | 인사이트 규칙 정의 |
| 1-2 | UI-UX-Designer | 디자인 시스템 정의 |
| 3-4 | Frontend | 인사이트 UI 반영 |
| 5 | QA-Architect | 테스트 자동화 |

### Phase 3: 완성 (3주차)

| 일차 | 에이전트 | 작업 |
|------|----------|------|
| 1-2 | QA-Architect | E2E 테스트, 성능 테스트 |
| 3 | KB-Curator | 문서화 |
| 4-5 | 전체 | 최종 검수 및 배포 |

---

## ✅ 최종 체크리스트

### 기능 요구사항
- [ ] 상승률 TOP 10 표시
- [ ] 하락률 TOP 10 표시
- [ ] 거래량 TOP 10 표시
- [ ] 탭 전환 동작
- [ ] 종목 상세 페이지 연결
- [ ] DataBasket 추가 기능
- [ ] 5분 자동 갱신

### 비기능 요구사항
- [ ] API 응답 시간 < 500ms (P95)
- [ ] 테스트 커버리지 > 80%
- [ ] WCAG 2.1 AA 준수
- [ ] 모바일 반응형 지원

### 문서화
- [ ] API 문서 (Swagger)
- [ ] 컴포넌트 스토리북
- [ ] 트러블슈팅 가이드
- [ ] 릴리즈 노트

---

## 📝 참고 자료

- [FMP API 문서](https://financialmodelingprep.com/developer/docs/)
- [Stock-Vis 아키텍처 문서](/docs/architecture/)
- [Chain Sight 디자인 철학](/docs/design/chain-sight.md)
- [DataBasket 사용 가이드](/docs/features/data-basket.md)