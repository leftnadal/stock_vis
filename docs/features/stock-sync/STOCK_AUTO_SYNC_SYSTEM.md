# Stock Page 자동 데이터 저장 시스템

## 개요

주식 개별 페이지 접근 시 외부 API 응답을 DB에 자동 저장하고, `_meta` 정보를 포함한 표준화된 응답을 반환하는 시스템입니다.

## 시스템 구성

### 1. 예외 처리 (`stocks/exceptions.py`)

표준화된 에러 응답을 위한 커스텀 예외 클래스들:

```python
class StockAPIException(Exception):
    """기본 예외 클래스"""
    code = 'STOCK_ERROR'
    message = '주식 데이터 처리 중 오류가 발생했습니다.'
    status_code = 500
    can_retry = True

    def to_response(self) -> Response:
        """DRF Response 변환"""
        return Response({
            'error': {
                'code': self.code,
                'message': self.message,
                'details': {...}
            }
        }, status=self.status_code)
```

**구현된 예외 클래스**:
- `StockNotFoundError`: 종목을 찾을 수 없을 때
- `ExternalAPIError`: 외부 API 호출 실패
- `RateLimitError`: API Rate Limit 초과
- `DataSyncError`: 데이터 동기화 실패
- `InvalidParameterError`: 잘못된 요청 파라미터
- `DataNotAvailableError`: 데이터 사용 불가 (outdated 등)

### 2. Rate Limiter (`stocks/services/rate_limiter.py`)

Redis 기반 API Rate Limiting:

```python
class APIRateLimiter:
    """Redis 기반 API Rate Limiter"""

    LIMITS = {
        'fmp': {
            'per_minute': 10,
            'per_day': 250,
        },
        'alpha_vantage': {
            'per_minute': 5,
            'per_day': 500,
        },
        'yfinance': {
            'per_minute': 60,
            'per_day': 10000,
        },
    }

    def can_call(self) -> Tuple[bool, Optional[str]]:
        """API 호출 가능 여부 확인"""
        # 분당/일일 제한 확인
        pass

    def record_call(self) -> bool:
        """API 호출 기록"""
        # Redis 카운터 증가
        pass

    def get_usage(self) -> dict:
        """현재 사용량 조회"""
        return {
            'api': self.api_name,
            'minute': {'used': 5, 'limit': 10, 'remaining': 5},
            'day': {'used': 100, 'limit': 250, 'remaining': 150},
            'can_call': True
        }
```

**주요 기능**:
- 분당/일일 API 호출 횟수 추적
- Redis 기반 분산 카운팅
- Rate Limit 상태 조회 및 리셋 시간 제공
- 컨텍스트 매니저 지원 (`RateLimitedAPICall`)

**사용 예시**:
```python
from stocks.services.rate_limiter import check_rate_limit, record_api_call

# Rate Limit 확인
can_call, usage = check_rate_limit('fmp')
if not can_call:
    raise RateLimitError('fmp', usage['minute']['reset_at'])

# API 호출
response = call_external_api()

# 호출 기록
record_api_call('fmp')
```

### 3. Stock Sync Service (`stocks/services/stock_sync_service.py`)

외부 API 응답을 DB에 자동 저장하는 핵심 서비스:

```python
@dataclass
class SyncResult:
    """동기화 결과"""
    success: bool
    source: str  # 'db', 'fmp', 'alpha_vantage'
    synced_at: Optional[datetime] = None
    error: Optional[str] = None
    data: Optional[dict] = None


class StockSyncService:
    """외부 API 응답을 DB에 자동 저장"""

    SYNC_INTERVALS = {
        'overview': timedelta(hours=6),      # 기본 정보: 6시간
        'price': timedelta(hours=1),          # 가격 정보: 1시간
        'financial': timedelta(days=7),       # 재무제표: 7일
    }

    def sync_overview(self, symbol: str, force: bool = False) -> SyncResult:
        """Overview 데이터 동기화 (FMP -> Stock 모델)"""
        # 1. 동기화 필요 여부 확인
        # 2. FMP API 호출
        # 3. Stock 모델 update_or_create
        # 4. 동기화 상태 캐싱
        pass

    def sync_prices(self, symbol: str, days: int = 30, force: bool = False) -> SyncResult:
        """가격 데이터 동기화 (FMP Historical -> DailyPrice 모델)"""
        # 1. 동기화 필요 여부 확인
        # 2. FMP Historical API 호출
        # 3. DailyPrice 모델에 bulk insert
        # 4. 동기화 상태 캐싱
        pass

    def should_sync(self, symbol: str, data_type: str) -> bool:
        """동기화가 필요한지 확인 (캐시 기반)"""
        pass

    def get_freshness(self, symbol: str, data_type: str) -> str:
        """데이터 신선도 확인"""
        # Returns: 'fresh', 'stale', 'expired'
        pass

    def get_sync_meta(self, symbol: str, data_type: str, source: str) -> dict:
        """_meta 정보 생성"""
        return {
            'source': source,
            'synced_at': '2026-01-26T12:00:00Z',
            'freshness': 'fresh',
            'can_sync': True,
        }
```

**동기화 간격**:
- **Overview**: 6시간마다 갱신
- **Price**: 1시간마다 갱신
- **Financial**: 7일마다 갱신

**Freshness 상태**:
- `fresh`: 동기화 간격 이내
- `stale`: 동기화 간격 초과 (2배 이내)
- `expired`: 동기화 간격 2배 초과

### 4. API Views 통합 (`stocks/views.py`)

모든 API View에 자동 동기화 로직 통합:

```python
def get_sync_service() -> StockSyncService:
    """StockSyncService 싱글톤 반환"""
    global _sync_service
    if _sync_service is None:
        _sync_service = StockSyncService()
    return _sync_service


class StockOverviewAPIView(APIView):
    """
    주식 개요 탭 데이터 API (캐싱 + 자동 저장)
    - 로컬 DB 우선 조회
    - DB에 없으면 FMP API 호출 후 자동 저장
    - _meta 정보 포함
    """

    def get(self, request, symbol):
        symbol = symbol.upper()
        sync_service = get_sync_service()

        # 캐시 확인
        cache_key = f"stock_overview_{symbol}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        try:
            # 로컬 DB 조회
            stock = Stock.objects.filter(symbol=symbol).first()
            source = 'db'

            if stock:
                # DB에 있으면 직렬화
                serializer = OverviewTabSerializer(stock)
                response_data = {
                    'symbol': symbol,
                    'tab': 'overview',
                    'data': serializer.data,
                }
            else:
                # DB에 없으면 FMP API 호출 후 자동 저장
                sync_result = sync_service.sync_overview(symbol, force=True)

                if sync_result.success:
                    # 저장 성공 - DB에서 다시 조회
                    stock = Stock.objects.get(symbol=symbol)
                    serializer = OverviewTabSerializer(stock)
                    response_data = {
                        'symbol': symbol,
                        'tab': 'overview',
                        'data': serializer.data,
                    }
                    source = 'fmp'
                else:
                    # 저장 실패 - FMP에서 직접 조회 (저장 없이)
                    # ... 실시간 데이터 반환
                    source = 'fmp_realtime'

            # _meta 정보 추가
            response_data['_meta'] = sync_service.get_sync_meta(symbol, 'overview', source)

            # 캐시 저장
            cache_ttl = 600 if source == 'db' else 120
            cache.set(cache_key, response_data, cache_ttl)

            return Response(response_data)

        except StockNotFoundError as e:
            return e.to_response()
        except Exception as e:
            logger.error(f"Overview data error for {symbol}: {e}")
            return Response({...}, status=500)
```

## API 응답 형식

### 표준 응답 구조

모든 API 엔드포인트는 `_meta` 필드를 포함:

```json
{
  "symbol": "AAPL",
  "tab": "overview",
  "data": {
    "symbol": "AAPL",
    "stock_name": "Apple Inc.",
    "real_time_price": 150.25,
    "change": 2.5,
    "change_percent": "+1.69%",
    ...
  },
  "_meta": {
    "source": "db",
    "synced_at": "2026-01-26T12:00:00Z",
    "freshness": "fresh",
    "can_sync": true
  }
}
```

### _meta 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 데이터 출처 (`db`, `fmp`, `fmp_realtime`, `alpha_vantage`) |
| `synced_at` | string | 마지막 동기화 시간 (ISO 8601) |
| `freshness` | string | 데이터 신선도 (`fresh`, `stale`, `expired`) |
| `can_sync` | boolean | 수동 동기화 가능 여부 |

### 에러 응답 구조

모든 에러는 표준화된 형식으로 반환:

```json
{
  "error": {
    "code": "STOCK_NOT_FOUND",
    "message": "종목 'XYZ'을(를) 찾을 수 없습니다.",
    "details": {
      "symbol": "XYZ",
      "tried_sources": ["db", "fmp"],
      "can_retry": true
    }
  }
}
```

## 동기화 API

### POST `/api/v1/stocks/api/sync/<symbol>/`

수동 데이터 동기화 요청:

**Request Body**:
```json
{
  "data_types": ["overview", "price"],
  "force": false
}
```

**Response**:
```json
{
  "symbol": "AAPL",
  "status": "success",
  "synced": {
    "overview": {
      "success": true,
      "source": "fmp",
      "error": null
    },
    "price": {
      "success": true,
      "source": "fmp",
      "error": null
    }
  },
  "next_sync_available": "2026-01-26T15:00:00Z"
}
```

**Status Values**:
- `success`: 모든 데이터 타입 동기화 성공
- `partial`: 일부 데이터 타입만 성공
- `failed`: 모든 데이터 타입 동기화 실패

### GET `/api/v1/stocks/api/sync/<symbol>/`

동기화 상태 조회:

**Response**:
```json
{
  "symbol": "AAPL",
  "sync_status": {
    "overview": {
      "freshness": "fresh",
      "source": "db",
      "synced_at": "2026-01-26T12:00:00Z",
      "can_sync": true
    },
    "price": {
      "freshness": "stale",
      "source": "db",
      "synced_at": "2026-01-26T10:00:00Z",
      "can_sync": true
    }
  },
  "can_sync": true,
  "rate_limit": {
    "api": "fmp",
    "minute": {"used": 5, "limit": 10, "remaining": 5},
    "day": {"used": 100, "limit": 250, "remaining": 150},
    "can_call": true
  }
}
```

## 데이터 흐름

### 1. Overview 데이터 조회 플로우

```
Frontend 요청
    │
    ▼
GET /api/v1/stocks/api/overview/AAPL
    │
    ▼
[캐시 확인]
    │
    ├─ Cache Hit ──> 즉시 반환
    │
    └─ Cache Miss
        │
        ▼
    [DB 조회]
        │
        ├─ Stock 존재 ──> 직렬화 반환 (source: 'db')
        │
        └─ Stock 없음
            │
            ▼
        [StockSyncService.sync_overview()]
            │
            ├─ 동기화 필요 여부 확인 (캐시)
            │
            ▼
        [FMP API 호출]
            │
            ├─ Rate Limit 확인
            │
            ▼
        [Stock 모델 update_or_create]
            │
            ▼
        [동기화 상태 캐싱]
            │
            ▼
        응답 반환 (source: 'fmp')
```

### 2. Price 데이터 조회 플로우

```
Frontend 요청
    │
    ▼
GET /api/v1/stocks/api/chart/AAPL?period=3m
    │
    ▼
[캐시 확인]
    │
    ├─ Cache Hit ──> 즉시 반환
    │
    └─ Cache Miss
        │
        ▼
    [Stock 조회]
        │
        ├─ Stock 존재
        │   │
        │   ▼
        │   [DailyPrice 조회]
        │   │
        │   ├─ 데이터 있음 ──> 반환 (source: 'db')
        │   │
        │   └─ 데이터 없음
        │       │
        │       ▼
        │   [FMP Historical API Fallback]
        │       │
        │       ▼
        │   반환 (source: 'fmp_historical')
        │
        └─ Stock 없음 ──> FMP API Fallback
```

## Rate Limit 관리

### API별 제한

| API | 분당 제한 | 일일 제한 |
|-----|----------|----------|
| FMP | 10 calls | 250 calls |
| Alpha Vantage | 5 calls | 500 calls |
| yfinance | 60 calls | 10,000 calls |

### Rate Limit 초과 시 응답

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "FMP API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
    "details": {
      "api_name": "fmp",
      "reset_time": "2026-01-26T12:35:00Z",
      "usage": {
        "minute": {"used": 10, "limit": 10, "remaining": 0},
        "day": {"used": 250, "limit": 250, "remaining": 0}
      },
      "can_retry": true
    }
  }
}
```

## 캐싱 전략

### Redis 캐시 키 패턴

```python
# API 응답 캐시
"stock_overview_{symbol}"          # TTL: 600초 (DB) / 120초 (FMP)
"chart_{symbol}_{type}_{period}"   # TTL: 60초 (DB) / 120초 (FMP)
"balance_sheet_{symbol}_{period}_{limit}"  # TTL: 3600초
"incomestatement_{symbol}_{period}_{limit}"  # TTL: 3600초
"cash_flow_{symbol}_{period}_{limit}"  # TTL: 3600초

# 동기화 상태 캐시
"sync_status:{symbol}:{data_type}"  # TTL: 동기화 간격 * 2

# Rate Limit 캐시
"rate_limit:{api}:minute:{minute}"  # TTL: 60초
"rate_limit:{api}:day:{date}"       # TTL: 86400초
```

### 캐시 TTL 전략

| 데이터 타입 | DB 소스 TTL | 외부 API TTL | 빈 데이터 TTL |
|------------|-------------|-------------|--------------|
| Overview | 600초 (10분) | 120초 (2분) | 300초 (5분) |
| Chart | 60초 (1분) | 120초 (2분) | 60초 (1분) |
| Financial | 3600초 (1시간) | 600초 (10분) | 300초 (5분) |

## 구현 체크리스트

- [x] `stocks/exceptions.py` - 표준화된 예외 클래스
- [x] `stocks/services/rate_limiter.py` - Redis 기반 Rate Limiter
- [x] `stocks/services/stock_sync_service.py` - 자동 동기화 서비스
- [x] `stocks/views.py` - StockOverviewAPIView에 _meta 통합
- [x] `stocks/views.py` - StockSyncAPIView 구현
- [x] `stocks/urls.py` - `/api/v1/stocks/api/sync/<symbol>/` 엔드포인트 추가
- [x] Django check 통과

## 사용 예시

### 1. Frontend에서 Overview 조회

```typescript
// services/stock.ts
export async function getStockOverview(symbol: string) {
  const response = await fetch(`/api/v1/stocks/api/overview/${symbol}/`);
  const data = await response.json();

  // _meta 정보 확인
  if (data._meta.freshness === 'stale') {
    console.warn(`${symbol} 데이터가 오래되었습니다.`);
    // 백그라운드에서 동기화 트리거
    syncStockData(symbol, ['overview']);
  }

  return data;
}

// 수동 동기화
export async function syncStockData(symbol: string, dataTypes: string[]) {
  const response = await fetch(`/api/v1/stocks/api/sync/${symbol}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data_types: dataTypes, force: false })
  });

  return await response.json();
}
```

### 2. Backend에서 Celery Task로 동기화

```python
# stocks/tasks.py
from celery import shared_task
from .services.stock_sync_service import StockSyncService

@shared_task
def sync_stock_data(symbol: str, data_types: list):
    """주식 데이터 동기화 태스크"""
    sync_service = StockSyncService()

    results = {}
    for data_type in data_types:
        if data_type == 'overview':
            results[data_type] = sync_service.sync_overview(symbol)
        elif data_type == 'price':
            results[data_type] = sync_service.sync_prices(symbol)

    return {
        'symbol': symbol,
        'results': results
    }
```

## 모니터링 및 디버깅

### 로그 확인

```python
# stocks.log
INFO [2026-01-26 12:00:00] Stock overview synced: AAPL (created)
INFO [2026-01-26 12:00:05] Price data synced for AAPL: 30 records
WARNING [2026-01-26 12:00:10] Rate limit near: fmp (9/10 per minute)
ERROR [2026-01-26 12:00:15] Failed to sync overview for XYZ: External API error
```

### Redis 상태 확인

```bash
# Rate Limit 확인
redis-cli GET "rate_limit:fmp:minute:202601261200"
# Output: "5"

# 동기화 상태 확인
redis-cli GET "sync_status:AAPL:overview"
# Output: "2026-01-26T12:00:00Z"
```

## 성능 최적화

### 1. Bulk Insert 사용

```python
# Price 데이터 bulk insert (N+1 쿼리 방지)
prices = [
    DailyPrice(stock=stock, date=date, open_price=..., ...)
    for item in fmp_data
]
DailyPrice.objects.bulk_create(prices, ignore_conflicts=True)
```

### 2. 캐시 워밍

```python
# 인기 종목 사전 캐싱
popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
for symbol in popular_symbols:
    sync_service.sync_overview(symbol, force=True)
    sync_service.sync_prices(symbol, days=90, force=True)
```

### 3. 분산 Rate Limiting

Redis를 사용하여 여러 워커 간 Rate Limit 공유:

```python
# Celery Worker 1
limiter = APIRateLimiter('fmp')
if limiter.can_call():
    # API 호출
    limiter.record_call()

# Celery Worker 2
limiter = APIRateLimiter('fmp')
# Worker 1의 호출 카운트 반영됨
if limiter.can_call():
    # API 호출
    limiter.record_call()
```

## 향후 개선 사항

1. **Alpha Vantage 통합**: 현재는 FMP만 지원, Alpha Vantage Fallback 추가
2. **재무제표 동기화**: `sync_financial()` 메서드 구현
3. **배치 동기화**: 여러 종목 동시 동기화 지원
4. **동기화 우선순위**: 인기 종목 우선 동기화
5. **실시간 동기화**: WebSocket으로 실시간 가격 업데이트
6. **동기화 이력**: SyncHistory 모델로 이력 추적

## 참고 자료

- [CLAUDE.md - 프로젝트 개요](../CLAUDE.md)
- [FMP API 문서](https://site.financialmodelingprep.com/developer/docs)
- [Alpha Vantage API 문서](https://www.alphavantage.co/documentation/)
- [Django Cache Framework](https://docs.djangoproject.com/en/5.0/topics/cache/)
- [Redis Rate Limiting Pattern](https://redis.io/docs/manual/patterns/rate-limiter/)
