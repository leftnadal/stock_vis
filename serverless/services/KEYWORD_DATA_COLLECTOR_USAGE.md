# KeywordDataCollector 사용 가이드

## 개요

`KeywordDataCollector`는 Market Movers 키워드 생성을 위해 외부 API로부터 추가 데이터를 수집하는 서비스입니다.

## 수집 데이터

| 데이터 | API | 필드 | Fallback |
|--------|-----|------|----------|
| **Overview** | Alpha Vantage | description, market_cap, pe_ratio, 52_week_high/low, dividend_yield | 빈 dict |
| **News** | MarketAux → Finnhub | title, source, sentiment, published_at | 빈 list |
| **Indicators** | MarketMover 모델 | RVOL, Trend Strength, Sector Alpha, ETF Sync, Volatility %ile | 빈 dict |

## 기본 사용법

### 1. 단일 배치 수집 (권장)

```python
from serverless.services import KeywordDataCollector

# 초기화
collector = KeywordDataCollector()

# 20개 종목 병렬 수집 (3-5초 소요)
symbols = ['AAPL', 'MSFT', 'GOOGL', ...]  # 최대 20개
results = collector.collect_batch(symbols, max_workers=5)

# 결과 확인
for symbol, data in results.items():
    print(f"{symbol}:")
    print(f"  Overview: {data['overview']}")
    print(f"  News: {len(data['news'])} articles")
    print(f"  Indicators: {data['indicators']}")
```

### 2. MarketMover 모델과 결합

```python
from serverless.models import MarketMover
from serverless.services import KeywordDataCollector

# 오늘의 Gainers 가져오기
movers = MarketMover.objects.filter(
    date=today,
    mover_type='gainers'
).order_by('rank')[:20]

# 심볼 추출
symbols = [m.symbol for m in movers]

# 추가 데이터 수집
collector = KeywordDataCollector()
enriched_data = collector.collect_batch(symbols)

# MarketMover와 결합
for mover in movers:
    context = {
        'basic': {
            'symbol': mover.symbol,
            'company_name': mover.company_name,
            'mover_type': mover.mover_type,
            'change_percent': float(mover.change_percent),
            'sector': mover.sector,
            'industry': mover.industry,
        },
        'overview': enriched_data[mover.symbol]['overview'],
        'news': enriched_data[mover.symbol]['news'],
        'indicators': {
            'rvol': float(mover.rvol) if mover.rvol else None,
            'trend_strength': float(mover.trend_strength) if mover.trend_strength else None,
            'sector_alpha': float(mover.sector_alpha) if mover.sector_alpha else None,
            'etf_sync_rate': float(mover.etf_sync_rate) if mover.etf_sync_rate else None,
            'volatility_pct': int(mover.volatility_pct) if mover.volatility_pct else None,
        }
    }

    # 이제 context를 LLM에 전달하여 키워드 생성
    # keywords = generate_keywords(context)
```

## 응답 구조

### 성공 케이스

```json
{
  "AAPL": {
    "overview": {
      "description": "Apple Inc. designs, manufactures...",
      "market_cap": "2.50T",
      "pe_ratio": 28.5,
      "52_week_high": 199.62,
      "52_week_low": 164.08,
      "dividend_yield": 0.52
    },
    "news": [
      {
        "title": "Apple announces record iPhone sales",
        "source": "Bloomberg",
        "sentiment": "positive",
        "published_at": "2026-01-24T10:00:00"
      },
      {
        "title": "Apple's services revenue grows",
        "source": "Reuters",
        "sentiment": "neutral",
        "published_at": "2026-01-23T15:30:00"
      }
    ],
    "indicators": {}
  }
}
```

### Fallback 케이스 (API 실패)

```json
{
  "XYZ": {
    "overview": {},
    "news": [],
    "indicators": {}
  }
}
```

## 성능 최적화

### 병렬 처리

- **ThreadPoolExecutor** 사용
- 기본 `max_workers=5` (동시 5개 종목)
- 20개 종목 수집 시간: **3-5초**

### Rate Limit 고려

| API | Rate Limit | 처리 시간 |
|-----|------------|----------|
| Alpha Vantage | 5 calls/min (12초 간격) | 종목당 12초+ |
| MarketAux | 100 calls/day (15분 간격) | 종목당 15분+ |
| Finnhub | 60 calls/min (1초 간격) | 종목당 1초 |

**권장 설정**:
- `max_workers=3` (Alpha Vantage rate limit 고려)
- 20개 종목 처리: 약 **1-2분** (AlphaVantage 12초 딜레이)

### 캐싱 전략 (향후 개선)

```python
# Redis 캐싱 예시
from django.core.cache import cache

def collect_with_cache(symbols):
    collector = KeywordDataCollector()
    results = {}

    for symbol in symbols:
        cache_key = f'keyword_context:{symbol}'
        cached = cache.get(cache_key)

        if cached:
            results[symbol] = cached
        else:
            data = collector._collect_single(symbol)
            cache.set(cache_key, data, 3600)  # 1시간 캐시
            results[symbol] = data

    return results
```

## 에러 핸들링

### 개별 종목 실패

```python
# 개별 실패는 전체 배치를 중단하지 않음
results = collector.collect_batch(['AAPL', 'INVALID', 'MSFT'])

# INVALID는 빈 컨텍스트 반환
assert results['INVALID'] == {'overview': {}, 'news': [], 'indicators': {}}
```

### API 클라이언트 없음

```python
# API 키가 없어도 서비스 초기화는 성공
# 해당 데이터만 빈 값 반환
collector = KeywordDataCollector()  # OK

# ALPHA_VANTAGE_API_KEY 없으면
results = collector.collect_batch(['AAPL'])
assert results['AAPL']['overview'] == {}  # 빈 dict

# MARKETAUX_API_KEY, FINNHUB_API_KEY 없으면
assert results['AAPL']['news'] == []  # 빈 list
```

## 로깅

### DEBUG 레벨

```
  🔍 AAPL 데이터 수집 시작
    ✓ AAPL overview 수집 완료
    ✓ AAPL 뉴스 3개 수집 완료
  ✓ AAPL 수집 완료 (2.34초)
```

### INFO 레벨

```
📊 키워드 데이터 수집 시작: 20개 종목
✅ 키워드 데이터 수집 완료: 성공=18, 실패=2, 소요시간=65.43초
```

### ERROR 레벨

```
  ❌ XYZ overview 수집 실패: Alpha Vantage error: Invalid API call
  ❌ XYZ 수집 실패: Connection timeout
```

## 테스트

### 유닛 테스트

```bash
# 개별 메서드 테스트
python manage.py test tests.serverless.test_keyword_data_collector

# 특정 테스트
python manage.py test tests.serverless.test_keyword_data_collector.TestKeywordDataCollector.test_fetch_overview
```

### 통합 테스트

```bash
# 실제 API 호출 (API 키 필요)
cd serverless/services
python keyword_data_collector.py
```

## 비용 분석

### API 비용 (무료 티어 기준)

| API | Free Tier | 20개 종목/일 | 비고 |
|-----|-----------|--------------|------|
| Alpha Vantage | 500 calls/day | ✅ 20 calls | OK |
| MarketAux | 100 calls/day | ✅ 20 calls | OK |
| Finnhub | 60 calls/min | ✅ 20 calls | OK |

**결론**: 무료 티어로 충분함 (일일 Market Movers 동기화)

## 향후 개선 사항

1. **Redis 캐싱**
   - Overview: 24시간 캐시
   - News: 1시간 캐시
   - 반복 요청 시 API 호출 절약

2. **데이터베이스 저장**
   - `KeywordContext` 모델 추가
   - 과거 데이터 재사용 가능

3. **감성 분석 강화**
   - Finnhub 뉴스에도 감성 분석 적용 (Gemini API)
   - 종합 감성 점수 계산

4. **추가 데이터 소스**
   - Insider Trading (SEC EDGAR)
   - Social Media Sentiment (Reddit, Twitter)
   - Analyst Ratings (Finnhub)

## 참고 문서

- [KEYWORD_SYSTEM_SUMMARY.md](./KEYWORD_SYSTEM_SUMMARY.md)
- [KEYWORD_SYSTEM_README.md](./KEYWORD_SYSTEM_README.md)
- Alpha Vantage API: https://www.alphavantage.co/documentation/
- MarketAux API: https://www.marketaux.com/documentation
- Finnhub API: https://finnhub.io/docs/api
