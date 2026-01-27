# KeywordDataCollector 구현 완료 보고서

## 완료 사항

### 1. KeywordDataCollector 서비스 구현

**파일**: `serverless/services/keyword_data_collector.py`

**주요 기능**:
- 병렬 데이터 수집 (ThreadPoolExecutor, max_workers=5)
- Overview 수집 (Alpha Vantage)
- News 수집 (MarketAux → Finnhub fallback)
- 에러 핸들링 (개별 실패 시 빈 컨텍스트 반환)

**API 클라이언트 재사용**:
- ✅ `AlphaVantageClient` (api_request/alphavantage_client.py)
- ✅ `MarketauxNewsProvider` (news/providers/marketaux.py)
- ✅ `FinnhubNewsProvider` (news/providers/finnhub.py)

### 2. 데이터 구조

```python
KeywordContext = {
    "AAPL": {
        "overview": {
            "description": "Apple Inc. is a preeminent...",
            "market_cap": "3.67T",
            "pe_ratio": 33.34,
            "52_week_high": 288.62,
            "52_week_low": 168.63,
            "dividend_yield": 0.41
        },
        "news": [
            {
                "title": "...",
                "source": "Bloomberg",
                "sentiment": "positive",
                "published_at": "2026-01-24T10:00:00"
            }
        ],
        "indicators": {}  # MarketMover 모델에서 채움
    }
}
```

### 3. 성능 테스트 결과

| 종목 수 | max_workers | 소요 시간 | 비고 |
|---------|-------------|----------|------|
| 1개 (AAPL) | 1 | 1.2초 | Overview + News 3개 |
| 2개 (AAPL, MSFT) | 2 | 1.1초 | 병렬 처리 효과 |
| 20개 (예상) | 5 | 60-90초 | Alpha Vantage 12초 딜레이 |

**Alpha Vantage Rate Limit**:
- 5 calls/분 (12초 간격)
- 20개 종목 처리 시 약 4분 소요 예상

### 4. 에러 핸들링

#### 개별 종목 실패

```python
# MSFT overview 실패 케이스
{
    "MSFT": {
        "overview": {},  # 빈 dict
        "news": [...],    # 뉴스는 정상 수집
        "indicators": {}
    }
}
```

#### API 클라이언트 없음

- Alpha Vantage 키 없음 → `overview` 빈 dict
- News provider 키 없음 → `news` 빈 list
- **서비스 초기화는 성공** (fallback 전략)

### 5. 로깅

```
INFO - 📊 키워드 데이터 수집 시작: 2개 종목
INFO - ✅ 키워드 데이터 수집 완료: 성공=2, 실패=0, 소요시간=1.12초
```

```
DEBUG -   🔍 AAPL 데이터 수집 시작
DEBUG -     ✓ AAPL overview 수집 완료
DEBUG -     ✓ AAPL 뉴스 3개 수집 완료
DEBUG -   ✓ AAPL 수집 완료 (1.05초)
```

## 사용 예시

### 기본 사용법

```python
from serverless.services import KeywordDataCollector

# 초기화
collector = KeywordDataCollector()

# 20개 종목 병렬 수집
symbols = ['AAPL', 'MSFT', 'GOOGL', ...]
results = collector.collect_batch(symbols, max_workers=5)

# 결과 확인
for symbol, data in results.items():
    print(f"{symbol}: {len(data['overview'])} fields, {len(data['news'])} news")
```

### MarketMover 모델과 통합

```python
from serverless.models import MarketMover
from serverless.services import KeywordDataCollector
from datetime import date

# 오늘의 Gainers
movers = MarketMover.objects.filter(
    date=date.today(),
    mover_type='gainers'
).order_by('rank')[:20]

# 심볼 추출
symbols = [m.symbol for m in movers]

# 추가 데이터 수집
collector = KeywordDataCollector()
enriched_data = collector.collect_batch(symbols)

# MarketMover + 추가 데이터 결합
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
            'trend_strength': float(mover.trend_strength),
            'sector_alpha': float(mover.sector_alpha),
            'etf_sync_rate': float(mover.etf_sync_rate),
            'volatility_pct': int(mover.volatility_pct),
        }
    }

    # LLM 키워드 생성에 context 전달
    # keywords = generate_keywords(context)
```

## 다음 단계

### 1. KeywordGeneratorService 수정

**파일**: `serverless/services/keyword_generator.py`

```python
from serverless.services import KeywordDataCollector

class KeywordGeneratorService:
    def __init__(self):
        self.data_collector = KeywordDataCollector()

    def generate_keywords_batch(self, movers: List[MarketMover]):
        """20개 종목 키워드 일괄 생성"""
        # 1. 심볼 추출
        symbols = [m.symbol for m in movers]

        # 2. 추가 데이터 수집
        enriched_data = self.data_collector.collect_batch(symbols)

        # 3. MarketMover + 추가 데이터 결합
        contexts = []
        for mover in movers:
            context = {
                'basic': self._extract_basic(mover),
                'overview': enriched_data[mover.symbol]['overview'],
                'news': enriched_data[mover.symbol]['news'],
                'indicators': self._extract_indicators(mover),
            }
            contexts.append(context)

        # 4. LLM 호출 (배치)
        keywords = self._call_llm_batch(contexts)

        return keywords
```

### 2. Celery 태스크 통합

**파일**: `serverless/tasks.py`

```python
from celery import shared_task
from serverless.services import KeywordGeneratorService
from serverless.models import MarketMover

@shared_task
def generate_movers_keywords(target_date):
    """Market Movers 키워드 일괄 생성"""
    generator = KeywordGeneratorService()

    for mover_type in ['gainers', 'losers', 'actives']:
        movers = MarketMover.objects.filter(
            date=target_date,
            mover_type=mover_type
        ).order_by('rank')[:20]

        keywords = generator.generate_keywords_batch(movers)

        # 키워드 저장
        for mover, kw in zip(movers, keywords):
            mover.keywords = kw
            mover.save(update_fields=['keywords'])
```

### 3. 캐싱 추가 (선택)

```python
from django.core.cache import cache

def collect_with_cache(self, symbols, cache_ttl=3600):
    """Redis 캐싱 적용"""
    results = {}

    for symbol in symbols:
        cache_key = f'keyword_context:{date.today()}:{symbol}'
        cached = cache.get(cache_key)

        if cached:
            results[symbol] = cached
        else:
            data = self._collect_single(symbol)
            cache.set(cache_key, data, cache_ttl)
            results[symbol] = data

    return results
```

## 비용 분석

### 무료 티어 (일일 Market Movers 동기화)

| API | Free Tier | 20개 종목/일 | 비용 |
|-----|-----------|--------------|------|
| Alpha Vantage | 500 calls/day | 20 calls | $0 |
| MarketAux | 100 calls/day | 20 calls | $0 |
| Finnhub | 60 calls/min | 20 calls | $0 |

**결론**: 무료 티어로 충분

### LLM 비용 (Gemini 2.5 Flash 기준)

| 항목 | 값 |
|------|-----|
| 배치 크기 | 20개 종목 |
| Input 토큰 | ~8,000 토큰 |
| Output 토큰 | ~6,000 토큰 (300 토큰 × 20) |
| 비용 | ~$0.01 / 배치 |
| 월간 비용 (30일) | ~$0.30 |

## 문서

- [사용 가이드](./KEYWORD_DATA_COLLECTOR_USAGE.md)
- [키워드 시스템 요약](./KEYWORD_SYSTEM_SUMMARY.md)
- [키워드 시스템 README](./KEYWORD_SYSTEM_README.md)

## 테스트

```bash
# Django shell 테스트
python manage.py shell -c "
from serverless.services import KeywordDataCollector
collector = KeywordDataCollector()
results = collector.collect_batch(['AAPL', 'MSFT'])
print(results)
"

# 유닛 테스트 작성 필요
# tests/serverless/test_keyword_data_collector.py
```

## 체크리스트

- [x] KeywordDataCollector 서비스 구현
- [x] 기존 API 클라이언트 재사용 (AlphaVantage, MarketAux, Finnhub)
- [x] 병렬 처리 (ThreadPoolExecutor)
- [x] 에러 핸들링 (개별 실패 시 fallback)
- [x] 로깅 (INFO, DEBUG, ERROR)
- [x] 초기화 테스트 (2개 종목)
- [x] 사용 가이드 문서 작성
- [ ] 유닛 테스트 작성
- [ ] KeywordGeneratorService 통합
- [ ] Celery 태스크 통합
- [ ] Redis 캐싱 추가 (선택)
