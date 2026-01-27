# Market Movers 키워드 생성 시스템

LLM을 활용하여 Market Movers 종목의 키워드를 자동 생성하는 시스템입니다.

---

## 개요

### 목적
- 5개 지표(RVOL, Trend Strength, Sector Alpha, ETF Sync, Volatility)를 분석하여 투자자가 빠르게 이해할 수 있는 키워드 생성
- 한국어/영어 키워드 지원
- 배치 처리로 비용 최적화

### 주요 기능
- **배치 처리**: 20개 종목 일괄 처리로 토큰 비용 65% 절약
- **Structured Output**: JSON 형식의 일관된 키워드 출력
- **토큰 최적화**: 압축된 컨텍스트 + 배치 프롬프트
- **캐싱**: 7일간 키워드 캐싱 (재생성 방지)

---

## 아키텍처

```
MarketMover 모델 (데이터베이스)
    │
    ▼
KeywordGeneratorService
    │
    ├─ KeywordPromptBuilder → 프롬프트 생성
    │   ├─ 시스템 프롬프트 (지표 해석 가이드)
    │   ├─ 배치 프롬프트 (20개 종목)
    │   └─ 토큰 추정
    │
    ├─ Gemini 2.5 Flash → LLM 호출
    │   ├─ Temperature: 0.3 (일관성)
    │   └─ Max Tokens: 8000
    │
    └─ KeywordResponseParser → 응답 파싱
        ├─ JSON 검증
        └─ 키워드 구조화
    │
    ▼
StockKeyword 모델 (저장)
```

---

## 파일 구조

```
serverless/services/
├── keyword_prompts.py        # 프롬프트 빌더 + 파서
├── keyword_generator.py      # LLM 서비스
├── keyword_context.py        # 컨텍스트 빌더 + 토큰 최적화
└── KEYWORD_SYSTEM_README.md  # 본 문서
```

---

## 사용법

### 1. 배치 키워드 생성 (권장)

```python
from serverless.services.keyword_generator import KeywordGeneratorService
from datetime import date

# 서비스 초기화
service = KeywordGeneratorService(language='ko')

# 2026-01-24 Gainers TOP 20 키워드 생성
results = await service.generate_keywords_for_movers(
    mover_date=date(2026, 1, 24),
    mover_type='gainers',
    max_stocks=20
)

# 결과
# [
#   {
#     'symbol': 'AAPL',
#     'keywords': [
#       {'text': '폭발적 거래량', 'category': '거래량', 'confidence': 0.95},
#       {'text': '강한 상승세', 'category': '추세', 'confidence': 0.90},
#       ...
#     ],
#     'summary': '폭발적 거래량과 강한 상승세를 보이는 기술주 강세 종목'
#   },
#   ...
# ]
```

### 2. 단일 종목 키워드 생성

```python
from serverless.models import MarketMover

# MarketMover 인스턴스 조회
mover = MarketMover.objects.get(
    date=date(2026, 1, 24),
    mover_type='gainers',
    symbol='AAPL'
)

# 키워드 생성
result = await service.generate_keywords_single(mover)

# 결과
# {
#   'symbol': 'AAPL',
#   'keywords': [...],
#   'summary': '...'
# }
```

### 3. 동기 함수 (Celery 태스크용)

```python
from serverless.services.keyword_generator import generate_keywords_sync

# 동기 호출 (Celery에서 사용)
results = generate_keywords_sync(
    mover_date=date(2026, 1, 24),
    mover_type='gainers',
    language='ko',
    max_stocks=20
)
```

### 4. 비용 추정

```python
# 배치 처리 비용 추정
cost_estimate = service.estimate_batch_cost(num_stocks=20)

print(cost_estimate)
# {
#   'input_tokens': 7200,
#   'output_tokens': 6000,
#   'total_tokens': 13200,
#   'input_cost_usd': 0.002160,
#   'output_cost_usd': 0.007200,
#   'total_cost_usd': 0.009360
# }
```

---

## 프롬프트 설계

### 시스템 프롬프트 핵심

1. **지표 해석 가이드** 제공
   - RVOL: 2.0 이상 = 비정상적 관심도
   - Trend Strength: +0.7 이상 = 강한 상승
   - Sector Alpha: 양수 = 섹터 평균 초과
   - ETF Sync Rate: 0.8 이상 = 강한 동조
   - Volatility: 90 이상 = 매우 높은 변동성

2. **키워드 카테고리** (5개)
   - 거래량, 추세, 섹터, 변동성, 특징

3. **출력 형식** (JSON)
   ```json
   {
     "symbol": "AAPL",
     "keywords": [
       {"text": "폭발적 거래량", "category": "거래량", "confidence": 0.95}
     ],
     "summary": "..."
   }
   ```

### 배치 프롬프트 구조

```
## 종목 #1
# AAPL - Apple Inc.
분류: 상승 종목

## 가격 정보
- 현재가: $180.50
- 등락률: +5.2%
- 거래량: 85,000,000

## 5개 지표
- RVOL: 2.5x
- Trend Strength: ▲0.85
- Sector Alpha: +2.3%
- ETF Sync Rate: 0.75
- Volatility Percentile: 88/100

---

## 종목 #2
...
```

---

## 토큰 최적화 전략

### 1. 배치 처리 vs 개별 처리

| 종목 수 | 배치 토큰 | 개별 토큰 | 절약률 |
|---------|----------|-----------|--------|
| 5개 | 3,700 | 6,500 | 43% |
| 10개 | 6,200 | 13,000 | 52% |
| 20개 | 11,200 | 26,000 | 57% |

**결론**: 5개 이상 종목은 배치 처리 권장

### 2. 컨텍스트 압축

```python
from serverless.services.keyword_context import KeywordContextBuilder

# 압축된 컨텍스트 (토큰 30% 절약)
compact = KeywordContextBuilder.build_compact_context(mover)
# {'symbol': 'AAPL', 'name': 'Apple', 'ind': {'rvol': 2.5, ...}}

# 전체 컨텍스트
full = KeywordContextBuilder.build_full_context(mover)
# {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'indicators': {...}}
```

### 3. 데이터베이스 압축

```python
from serverless.services.keyword_context import KeywordCompressor

# 원본 키워드
keywords = [
    {'text': '폭발적 거래량', 'category': '거래량', 'confidence': 0.95}
]

# 압축 (JSON 크기 40% 절약)
compressed = KeywordCompressor.compress_keywords(keywords)
# [{'t': '폭발적 거래량', 'c': '거래량', 'cf': 0.95}]

# 복원
decompressed = KeywordCompressor.decompress_keywords(compressed)
```

---

## 비용 분석

### Gemini 2.5 Flash 가격 (2025년 1월)

- Input: $0.30 / 1M tokens
- Output: $1.20 / 1M tokens

### 일일 배치 처리 비용 (60개 종목)

```
Gainers 20개 + Losers 20개 + Actives 20개 = 60개

배치 처리 (3회):
- 입력 토큰: 7,200 * 3 = 21,600
- 출력 토큰: 6,000 * 3 = 18,000
- 비용: $0.009360 * 3 = $0.028080

월간 비용 (30일):
- $0.028080 * 30 = $0.84

연간 비용 (365일):
- $0.028080 * 365 = $10.25
```

**결론**: 연간 $10 미만으로 운영 가능

---

## 응답 파싱

### JSON 스키마

```json
{
  "symbol": "AAPL",
  "keywords": [
    {
      "text": "폭발적 거래량",
      "category": "거래량",
      "confidence": 0.95
    }
  ],
  "summary": "폭발적 거래량과 강한 상승세를 보이는 기술주 강세 종목"
}
```

### 유효성 검증

- `symbol`: 필수, 대문자 변환
- `keywords`: 필수, 배열
  - `text`: 필수, 2-4단어
  - `category`: 필수, 5개 카테고리 중 하나
  - `confidence`: 선택, 0.0~1.0 (기본 0.8)
- `summary`: 선택, 1-2문장

### 에러 처리

```python
from serverless.services.keyword_prompts import KeywordResponseParser

# 파싱 시도
result = KeywordResponseParser.parse_single_response(
    response_text,
    language='ko'
)

if result:
    print(f"파싱 성공: {result['symbol']}")
else:
    print("파싱 실패: JSON 형식 오류")
```

---

## 캐싱 전략

### TTL 정책

- **StockKeyword 모델**: 7일간 유지
- **expires_at**: 생성일 + 7일 (자동 설정)

### 캐시 조회 순서

1. **StockKeyword 조회** (symbol + date)
2. 캐시 있음 → 반환
3. 캐시 없음 → LLM 호출 → 저장 → 반환

### 캐시 만료 처리

```python
from django.utils import timezone
from serverless.models import StockKeyword

# 만료된 키워드 삭제 (Celery 태스크)
StockKeyword.objects.filter(
    expires_at__lt=timezone.now()
).delete()
```

---

## 데이터베이스 모델

### StockKeyword

```python
class StockKeyword(models.Model):
    """Market Movers 종목별 AI 생성 키워드"""

    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)
    date = models.DateField(db_index=True)

    keywords = models.JSONField(help_text="키워드 리스트 (3-5개)")

    llm_model = models.CharField(max_length=50, default="gemini-2.5-flash")
    generation_time_ms = models.IntegerField(null=True, blank=True)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(null=True, blank=True)

    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['symbol', 'date']]
```

---

## Celery 태스크 인터페이스 (@infra 담당)

```python
# serverless/tasks.py (예시 인터페이스)

from celery import shared_task
from datetime import date
from .services.keyword_generator import generate_keywords_sync

@shared_task(bind=True, max_retries=3)
def generate_daily_keywords(self, mover_date: str, mover_type: str):
    """
    Market Movers 키워드 일일 생성 태스크

    Args:
        mover_date: 'YYYY-MM-DD' 형식
        mover_type: 'gainers', 'losers', 'actives'
    """
    try:
        date_obj = date.fromisoformat(mover_date)

        # 키워드 생성
        results = generate_keywords_sync(
            mover_date=date_obj,
            mover_type=mover_type,
            language='ko',
            max_stocks=20
        )

        # StockKeyword 모델에 저장
        from .models import StockKeyword
        from django.utils import timezone

        for result in results:
            StockKeyword.objects.update_or_create(
                symbol=result['symbol'],
                date=date_obj,
                defaults={
                    'keywords': result['keywords'],
                    'llm_model': 'gemini-2.5-flash',
                    'status': 'completed',
                    'expires_at': timezone.now() + timedelta(days=7)
                }
            )

        return {
            'success': True,
            'count': len(results)
        }

    except Exception as e:
        logger.exception(f"Keyword generation failed: {e}")
        raise self.retry(exc=e, countdown=60)
```

### Celery Beat 스케줄

```python
# config/celery.py

CELERY_BEAT_SCHEDULE = {
    'generate-market-movers-keywords': {
        'task': 'serverless.tasks.generate_daily_keywords_batch',
        'schedule': crontab(hour=8, minute=0),  # 매일 08:00 EST
        'options': {'expires': 3600}
    }
}
```

---

## API 엔드포인트 (선택)

```python
# serverless/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import StockKeyword

@api_view(['GET'])
def get_stock_keywords(request, symbol: str):
    """
    종목 키워드 조회

    GET /api/v1/serverless/keywords/<symbol>/
    """
    from datetime import date

    today = date.today()

    try:
        keyword_obj = StockKeyword.objects.get(
            symbol=symbol.upper(),
            date=today,
            status='completed'
        )

        return Response({
            'symbol': keyword_obj.symbol,
            'keywords': keyword_obj.keywords,
            'date': keyword_obj.date,
            'model': keyword_obj.llm_model
        })

    except StockKeyword.DoesNotExist:
        return Response({
            'error': 'Keywords not found'
        }, status=404)
```

---

## 테스트

### 단위 테스트

```python
# tests/serverless/test_keyword_generator.py

import pytest
from datetime import date
from serverless.services.keyword_generator import KeywordGeneratorService

@pytest.mark.asyncio
async def test_generate_keywords_batch():
    service = KeywordGeneratorService(language='ko')

    results = await service.generate_keywords_for_movers(
        mover_date=date(2026, 1, 24),
        mover_type='gainers',
        max_stocks=5
    )

    assert len(results) == 5
    assert all('symbol' in r for r in results)
    assert all('keywords' in r for r in results)
    assert all(len(r['keywords']) >= 3 for r in results)
```

---

## 향후 개선 사항

### Phase 2 기능

1. **Semantic Cache 통합**
   - RAG Analysis의 Semantic Cache 활용
   - 유사 종목 키워드 재사용

2. **뉴스 컨텍스트 추가**
   - News API 연동
   - 키워드 생성 시 뉴스 헤드라인 포함

3. **다국어 지원 확장**
   - 일본어, 중국어 키워드 생성

4. **키워드 임베딩**
   - 키워드 벡터화
   - 유사 종목 검색 기능

---

## 문의

- **담당**: @rag-llm
- **협업**: @infra (Celery 태스크), @frontend (키워드 UI)
