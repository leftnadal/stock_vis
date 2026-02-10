# Market Movers 키워드 생성 시스템 설계

## 개요

Market Movers 각 종목에 대해 LLM이 생성한 3-5개의 핵심 키워드를 제공하는 시스템입니다.

**목표**: 사용자가 한눈에 해당 종목의 급등/급락 이유를 파악할 수 있도록 지원

**예시**:
- NVDA: `["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"]`
- TSLA: `["중국 판매량", "사이버트럭 생산", "FSD 업데이트"]`

---

## 1. 모델 설계

### 1.1 StockKeyword 모델

```python
# serverless/models.py

class StockKeyword(models.Model):
    """
    Market Movers 종목별 AI 생성 키워드

    LLM이 생성한 3-5개의 핵심 키워드를 저장합니다.
    일일 배치로 생성되며, TTL은 7일입니다.
    """

    # 종목 정보 (FK 없이 symbol로 직접 매핑)
    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)

    # 생성 일자
    date = models.DateField(db_index=True)

    # 키워드 리스트 (3-5개)
    keywords = models.JSONField(
        help_text="LLM 생성 키워드 리스트 (3-5개)",
        default=list
    )
    # 예시: ["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"]

    # 메타데이터
    llm_model = models.CharField(
        max_length=50,
        default="gemini-2.5-flash",
        help_text="사용된 LLM 모델"
    )
    generation_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="키워드 생성 소요 시간 (밀리초)"
    )
    prompt_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="입력 토큰 수"
    )
    completion_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="출력 토큰 수"
    )

    # 생성 상태
    STATUS_CHOICES = [
        ('pending', 'Pending'),      # 생성 대기
        ('processing', 'Processing'), # 생성 중
        ('completed', 'Completed'),   # 성공
        ('failed', 'Failed'),         # 실패
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="실패 시 에러 메시지"
    )

    # TTL 관리
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="키워드 만료 시점 (생성일 + 7일)"
    )

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_stock_keyword'
        unique_together = [['symbol', 'date']]
        ordering = ['-date', 'symbol']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['symbol', '-date']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.date}): {len(self.keywords)}개 키워드"

    def save(self, *args, **kwargs):
        """expires_at 자동 설정"""
        if not self.expires_at:
            from datetime import timedelta
            from django.utils import timezone
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
```

### 1.2 MarketMover 관계 설정

**선택 1: FK 없이 symbol로 조인** (권장)
- 장점: 간단한 구조, 독립적 TTL 관리
- 단점: 외래 키 무결성 없음

**선택 2: FK 추가**
```python
# MarketMover 모델에 추가
class MarketMover(models.Model):
    # ... 기존 필드 ...

    @property
    def keywords(self):
        """해당 날짜의 키워드 조회"""
        try:
            kw = StockKeyword.objects.get(symbol=self.symbol, date=self.date)
            return kw.keywords if kw.status == 'completed' else []
        except StockKeyword.DoesNotExist:
            return []
```

**추천: 선택 1** (FK 없이 symbol로 조인)
- Market Movers는 일일 데이터, 키워드는 7일 TTL로 다른 생명주기
- 느슨한 결합이 더 유연함

---

## 2. API 엔드포인트 설계

### 2.1 옵션 A: 기존 엔드포인트에 키워드 포함 (권장)

**장점**:
- 프론트엔드 요청 1회로 모든 데이터 조회
- 네트워크 오버헤드 최소화
- 캐싱 효율 극대화

**단점**:
- 응답 크기 증가 (미미)
- 키워드 없는 경우도 빈 배열 반환

#### 응답 형식

```http
GET /api/v1/serverless/movers?type=gainers&date=2026-01-24
```

```json
{
  "success": true,
  "data": {
    "date": "2026-01-24",
    "type": "gainers",
    "count": 20,
    "movers": [
      {
        "symbol": "NVDA",
        "company_name": "NVIDIA Corporation",
        "rank": 1,
        "price": 525.32,
        "change_percent": 8.45,
        "volume": 52400000,
        "sector": "Technology",
        "industry": "Semiconductors",
        "indicators": {
          "rvol": "2.34x",
          "trend": "▲0.85",
          "sector_alpha": "+2.3%",
          "etf_sync": "0.82",
          "volatility": "P78"
        },
        "keywords": [
          "AI 반도체 수요",
          "데이터센터 확장",
          "실적 서프라이즈"
        ]
      },
      ...
    ]
  }
}
```

### 2.2 옵션 B: 별도 엔드포인트

**장점**:
- 키워드만 필요할 때 최소 데이터 전송
- 독립적인 캐싱 전략

**단점**:
- 프론트엔드 요청 2회 (Movers + Keywords)
- 추가 API 유지보수

#### 엔드포인트

```http
GET /api/v1/serverless/movers/{symbol}/keywords?date=2026-01-24
```

```json
{
  "success": true,
  "data": {
    "symbol": "NVDA",
    "date": "2026-01-24",
    "keywords": [
      "AI 반도체 수요",
      "데이터센터 확장",
      "실적 서프라이즈"
    ],
    "generated_at": "2026-01-24T08:00:00Z",
    "expires_at": "2026-01-31T08:00:00Z"
  }
}
```

### 2.3 추천: 옵션 A (기존 엔드포인트에 포함)

**이유**:
1. Market Movers 카드 렌더링 시 키워드도 함께 표시되므로 동시 조회가 자연스러움
2. 캐싱 키가 동일 (`movers:{date}:{type}`)하여 관리 간편
3. 프론트엔드 구현 단순화

---

## 3. 서비스 레이어 설계 (3계층)

### 3.1 아키텍처

```
Views (serverless/views.py)
    │ HTTP 요청/응답, 인증
    ▼
Processors (serverless/processors.py) ⭐ 새로 생성
    │ 비즈니스 로직, 키워드 조합
    ▼
Services (serverless/services/)
    ├─ KeywordGenerationService (keyword_service.py)
    │  └─ LLM 호출, 키워드 파싱
    └─ MarketMoversSync (data_sync.py)
       └─ 데이터 동기화 (기존)
```

### 3.2 KeywordGenerationService

```python
# serverless/services/keyword_service.py

"""
Market Movers 키워드 생성 서비스
"""
import json
import logging
import time
from typing import List, Dict, Optional
from django.utils import timezone
from datetime import timedelta

from serverless.models import StockKeyword, MarketMover
from rag_analysis.services.llm_service import LLMServiceLite


logger = logging.getLogger(__name__)


class KeywordGenerationService:
    """
    LLM 기반 Market Movers 키워드 생성 서비스

    Features:
    - Gemini 2.5 Flash 사용 (빠르고 저렴)
    - 배치 생성 (일일 60개 종목)
    - 실패 시 fallback 키워드
    - 지수 백오프 재시도
    """

    # 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 투자 분석 전문가입니다.

주어진 종목의 급등/급락 이유를 3-5개의 핵심 키워드로 요약하세요.

## 규칙

1. **간결성**: 각 키워드는 2-6단어 이내
2. **구체성**: 추상적 표현 금지 ("호재" ❌ → "AI 반도체 수요" ✅)
3. **최신성**: 당일 시장 이벤트 반영
4. **객관성**: 확인된 정보만 사용

## 출력 형식

JSON 배열만 반환하세요 (추가 설명 없음):

["키워드1", "키워드2", "키워드3"]

## 예시

입력:
- 종목: NVDA
- 상승률: +8.45%
- 섹터: Technology
- 산업: Semiconductors

출력:
["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"]
"""

    # Fallback 키워드 (LLM 실패 시)
    FALLBACK_KEYWORDS = {
        'gainers': ["급등", "거래량 증가", "모멘텀"],
        'losers': ["급락", "매도 압력", "조정"],
        'actives': ["거래량 급증", "변동성", "투자자 관심"],
    }

    def __init__(self):
        self.llm = LLMServiceLite()

    def generate_keyword(
        self,
        symbol: str,
        company_name: str,
        date,
        mover_type: str,
        change_percent: float,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict:
        """
        단일 종목 키워드 생성

        Args:
            symbol: 종목 심볼
            company_name: 회사명
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'
            change_percent: 변동률
            sector: 섹터
            industry: 산업
            max_retries: 최대 재시도 횟수

        Returns:
            {
                'keywords': [...],
                'status': 'completed' | 'failed',
                'error_message': str,
                'metadata': {...}
            }
        """
        start_time = time.time()

        # 1. 프롬프트 구성
        user_prompt = self._build_prompt(
            symbol, company_name, mover_type, change_percent, sector, industry
        )

        # 2. LLM 호출 (동기)
        try:
            keywords, metadata = self._call_llm_sync(user_prompt, max_retries)

            # 3. 검증
            if not keywords or len(keywords) < 3:
                logger.warning(f"{symbol}: 키워드 부족 ({len(keywords)}개) → Fallback 사용")
                keywords = self.FALLBACK_KEYWORDS.get(mover_type, ["변동성"])
                status = 'failed'
                error_message = "키워드 개수 부족"
            else:
                status = 'completed'
                error_message = None

        except Exception as e:
            logger.exception(f"{symbol} 키워드 생성 실패: {e}")
            keywords = self.FALLBACK_KEYWORDS.get(mover_type, ["변동성"])
            status = 'failed'
            error_message = str(e)
            metadata = {}

        # 4. 소요 시간 계산
        generation_time_ms = int((time.time() - start_time) * 1000)

        return {
            'keywords': keywords,
            'status': status,
            'error_message': error_message,
            'metadata': {
                'generation_time_ms': generation_time_ms,
                'prompt_tokens': metadata.get('input_tokens', 0),
                'completion_tokens': metadata.get('output_tokens', 0),
            }
        }

    def batch_generate(
        self,
        date,
        mover_type: str,
        limit: int = 20
    ) -> Dict[str, int]:
        """
        일괄 키워드 생성 (Celery 태스크용)

        Args:
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'
            limit: 처리 개수 (기본값: 20)

        Returns:
            {'success': 18, 'failed': 2, 'skipped': 0}
        """
        logger.info(f"🔄 키워드 배치 생성 시작: {date} {mover_type} (limit={limit})")

        results = {'success': 0, 'failed': 0, 'skipped': 0}

        # 1. MarketMover 조회
        movers = MarketMover.objects.filter(
            date=date,
            mover_type=mover_type
        ).order_by('rank')[:limit]

        # 2. 각 종목별 키워드 생성
        for mover in movers:
            # 이미 생성된 키워드 스킵
            if StockKeyword.objects.filter(
                symbol=mover.symbol,
                date=date,
                status='completed'
            ).exists():
                logger.debug(f"  ⏭️ {mover.symbol}: 이미 생성됨 (스킵)")
                results['skipped'] += 1
                continue

            # 키워드 생성
            result = self.generate_keyword(
                symbol=mover.symbol,
                company_name=mover.company_name,
                date=date,
                mover_type=mover_type,
                change_percent=float(mover.change_percent),
                sector=mover.sector,
                industry=mover.industry
            )

            # DB 저장
            StockKeyword.objects.update_or_create(
                symbol=mover.symbol,
                date=date,
                defaults={
                    'company_name': mover.company_name,
                    'keywords': result['keywords'],
                    'status': result['status'],
                    'error_message': result['error_message'],
                    'llm_model': 'gemini-2.5-flash',
                    'generation_time_ms': result['metadata'].get('generation_time_ms'),
                    'prompt_tokens': result['metadata'].get('prompt_tokens'),
                    'completion_tokens': result['metadata'].get('completion_tokens'),
                    'expires_at': timezone.now() + timedelta(days=7),
                }
            )

            # 결과 집계
            if result['status'] == 'completed':
                logger.info(f"  ✅ {mover.symbol}: {result['keywords']}")
                results['success'] += 1
            else:
                logger.warning(f"  ⚠️ {mover.symbol}: {result['error_message']}")
                results['failed'] += 1

        logger.info(
            f"✅ 키워드 배치 생성 완료: "
            f"success={results['success']}, failed={results['failed']}, skipped={results['skipped']}"
        )

        return results

    def _build_prompt(
        self,
        symbol: str,
        company_name: str,
        mover_type: str,
        change_percent: float,
        sector: Optional[str],
        industry: Optional[str]
    ) -> str:
        """프롬프트 구성"""
        direction = "급등" if mover_type == "gainers" else "급락" if mover_type == "losers" else "거래량 증가"

        return f"""다음 종목의 {direction} 이유를 3-5개 핵심 키워드로 요약하세요:

종목: {symbol} ({company_name})
변동률: {change_percent:+.2f}%
섹터: {sector or 'N/A'}
산업: {industry or 'N/A'}

JSON 배열만 반환:
["키워드1", "키워드2", "키워드3"]
"""

    def _call_llm_sync(self, prompt: str, max_retries: int) -> tuple:
        """
        LLM 동기 호출 (비동기를 동기로 래핑)

        Returns:
            (keywords: List[str], metadata: Dict)
        """
        import asyncio

        # 비동기 함수 정의
        async def _async_call():
            full_text = ""
            metadata = {}

            async for event in self.llm.generate_stream(
                context=self.SYSTEM_PROMPT,
                question=prompt,
                max_retries=max_retries,
                complexity='simple'  # 단순 키워드 생성
            ):
                if event['type'] == 'delta':
                    full_text += event['content']
                elif event['type'] == 'final':
                    metadata = {
                        'input_tokens': event.get('input_tokens', 0),
                        'output_tokens': event.get('output_tokens', 0),
                    }
                elif event['type'] == 'error':
                    raise Exception(event['message'])

            return full_text, metadata

        # 동기 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            full_text, metadata = loop.run_until_complete(_async_call())
        finally:
            loop.close()

        # JSON 파싱
        keywords = self._parse_keywords(full_text)

        return keywords, metadata

    def _parse_keywords(self, text: str) -> List[str]:
        """
        LLM 응답에서 JSON 배열 파싱

        Args:
            text: LLM 응답 텍스트

        Returns:
            키워드 리스트
        """
        try:
            # JSON 배열 추출 (코드 블록 제거)
            clean_text = text.strip()
            clean_text = clean_text.replace('```json', '').replace('```', '').strip()

            # JSON 파싱
            keywords = json.loads(clean_text)

            # 검증
            if not isinstance(keywords, list):
                raise ValueError("응답이 배열이 아닙니다")

            # 최대 5개로 제한
            return [str(kw).strip() for kw in keywords[:5] if kw]

        except Exception as e:
            logger.warning(f"키워드 파싱 실패: {e}, 원문: {text[:100]}")
            raise
```

### 3.3 MarketMoversProcessor (신규)

```python
# serverless/processors.py

"""
Market Movers 비즈니스 로직 레이어
"""
import logging
from typing import Dict, List, Optional
from django.utils import timezone

from serverless.models import MarketMover, StockKeyword
from serverless.services.keyword_service import KeywordGenerationService


logger = logging.getLogger(__name__)


class MarketMoversProcessor:
    """
    Market Movers 데이터 조합 및 변환 로직

    역할:
    - MarketMover + StockKeyword 조인
    - 응답 형식 구조화
    - 5개 지표 디스플레이 포맷팅
    """

    def __init__(self):
        self.keyword_service = KeywordGenerationService()

    def get_movers_with_keywords(
        self,
        date,
        mover_type: str
    ) -> List[Dict]:
        """
        Market Movers + 키워드 조회

        Args:
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'

        Returns:
            [
                {
                    'symbol': 'NVDA',
                    'company_name': 'NVIDIA Corporation',
                    'rank': 1,
                    'price': 525.32,
                    'change_percent': 8.45,
                    'volume': 52400000,
                    'sector': 'Technology',
                    'industry': 'Semiconductors',
                    'indicators': {...},
                    'keywords': [...]  # ⭐ 추가
                },
                ...
            ]
        """
        # 1. MarketMover 조회
        movers = MarketMover.objects.filter(
            date=date,
            mover_type=mover_type
        ).order_by('rank')

        # 2. 키워드 일괄 조회 (N+1 방지)
        symbols = [m.symbol for m in movers]
        keywords_map = self._get_keywords_map(symbols, date)

        # 3. 조합
        result = []
        for mover in movers:
            result.append({
                'symbol': mover.symbol,
                'company_name': mover.company_name,
                'rank': mover.rank,
                'price': float(mover.price),
                'change_percent': float(mover.change_percent),
                'volume': mover.volume,
                'sector': mover.sector,
                'industry': mover.industry,
                'ohlc': {
                    'open': float(mover.open_price) if mover.open_price else None,
                    'high': float(mover.high) if mover.high else None,
                    'low': float(mover.low) if mover.low else None,
                },
                'indicators': {
                    'rvol': mover.rvol_display,
                    'trend': mover.trend_display,
                    'sector_alpha': self._format_percentage(mover.sector_alpha),
                    'etf_sync': str(mover.etf_sync_rate) if mover.etf_sync_rate else None,
                    'volatility': f"P{mover.volatility_pct}" if mover.volatility_pct else None,
                },
                'keywords': keywords_map.get(mover.symbol, []),  # ⭐ 키워드 추가
            })

        return result

    def _get_keywords_map(
        self,
        symbols: List[str],
        date
    ) -> Dict[str, List[str]]:
        """
        키워드 일괄 조회 (N+1 방지)

        Args:
            symbols: 심볼 리스트
            date: 날짜

        Returns:
            {'NVDA': [...], 'TSLA': [...]}
        """
        keywords_qs = StockKeyword.objects.filter(
            symbol__in=symbols,
            date=date,
            status='completed'
        ).values('symbol', 'keywords')

        return {
            kw['symbol']: kw['keywords']
            for kw in keywords_qs
        }

    def _format_percentage(self, value) -> Optional[str]:
        """Decimal을 % 포맷으로 변환"""
        if value is None:
            return None
        try:
            return f"{value:+.1f}%"
        except (ValueError, TypeError):
            return None
```

### 3.4 Views 업데이트

```python
# serverless/views.py (수정)

from serverless.processors import MarketMoversProcessor

@api_view(['GET'])
@permission_classes([AllowAny])
def market_movers_api(request):
    """
    Market Movers API (키워드 포함)

    GET /api/v1/serverless/movers?type=gainers&date=2026-01-24
    """
    # 쿼리 파라미터
    mover_type = request.GET.get('type', 'gainers')
    date_str = request.GET.get('date', timezone.now().date().isoformat())

    # 유효성 검사
    if mover_type not in ['gainers', 'losers', 'actives']:
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_TYPE',
                'message': f"Invalid type: {mover_type}"
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # 캐시 확인
    cache_key = f'movers_with_keywords:{date_str}:{mover_type}'
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"캐시 HIT: {cache_key}")
        return Response(cached)

    # Processor 사용 ⭐
    processor = MarketMoversProcessor()
    movers = processor.get_movers_with_keywords(date_str, mover_type)

    # 응답 데이터
    response_data = {
        'success': True,
        'data': {
            'date': date_str,
            'type': mover_type,
            'count': len(movers),
            'movers': movers
        }
    }

    # 캐시 저장 (5분)
    cache.set(cache_key, response_data, 300)

    return Response(response_data)
```

---

## 4. 캐싱 전략

### 4.1 Redis 캐싱

| 캐시 키 | TTL | 무효화 조건 |
|---------|-----|------------|
| `movers_with_keywords:{date}:{type}` | 300초 (5분) | 1. 새로운 키워드 생성<br>2. 수동 동기화 |
| `keyword:{symbol}:{date}` | 3600초 (1시간) | 거의 없음 (일일 1회 생성) |

### 4.2 캐시 무효화 로직

```python
# serverless/services/keyword_service.py (추가)

def invalidate_cache_after_generation(self, date, mover_type: str):
    """
    키워드 생성 후 캐시 무효화

    Args:
        date: 날짜
        mover_type: 'gainers', 'losers', 'actives'
    """
    from django.core.cache import cache

    cache_key = f'movers_with_keywords:{date}:{mover_type}'
    cache.delete(cache_key)
    logger.info(f"🗑️ 캐시 무효화: {cache_key}")
```

```python
# serverless/services/keyword_service.py의 batch_generate() 끝에 추가

def batch_generate(self, date, mover_type: str, limit: int = 20) -> Dict[str, int]:
    # ... 키워드 생성 로직 ...

    # 캐시 무효화
    self.invalidate_cache_after_generation(date, mover_type)

    return results
```

---

## 5. 에러 핸들링

### 5.1 Fallback 전략

| 시나리오 | 대응 |
|---------|------|
| **LLM API 실패** | Fallback 키워드 사용 (mover_type 기반) |
| **키워드 파싱 실패** | Fallback 키워드 사용 |
| **Rate Limit** | 지수 백오프 재시도 (1초 → 2초 → 4초) |
| **타임아웃** | Fallback 키워드 + status='failed' 저장 |

### 5.2 Fallback 키워드

```python
FALLBACK_KEYWORDS = {
    'gainers': ["급등", "거래량 증가", "모멘텀"],
    'losers': ["급락", "매도 압력", "조정"],
    'actives': ["거래량 급증", "변동성", "투자자 관심"],
}
```

### 5.3 재시도 로직

```python
# LLMServiceLite에 이미 구현됨
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # 지수 백오프
```

### 5.4 모니터링 지표

```python
# StockKeyword 모델에 저장
- status: 'completed', 'failed'
- error_message: 실패 원인
- generation_time_ms: 생성 소요 시간
- prompt_tokens / completion_tokens: 토큰 사용량
```

---

## 6. 성능 최적화

### 6.1 N+1 쿼리 방지

```python
# ❌ 나쁜 예 (N+1 쿼리)
for mover in movers:
    keywords = StockKeyword.objects.get(symbol=mover.symbol, date=date)

# ✅ 좋은 예 (일괄 조회)
symbols = [m.symbol for m in movers]
keywords_map = {
    kw['symbol']: kw['keywords']
    for kw in StockKeyword.objects.filter(
        symbol__in=symbols, date=date, status='completed'
    ).values('symbol', 'keywords')
}
```

### 6.2 배치 생성 최적화

- **병렬 처리 없음**: LLM API는 순차 호출 (Rate Limit 우회)
- **조기 종료**: 이미 생성된 키워드는 스킵
- **TTL 활용**: 7일 경과 데이터는 자동 삭제 (Celery 태스크)

### 6.3 인덱스 최적화

```python
# StockKeyword 모델 인덱스
indexes = [
    models.Index(fields=['date', 'status']),      # 배치 생성 쿼리
    models.Index(fields=['symbol', '-date']),     # 최신 키워드 조회
    models.Index(fields=['expires_at']),          # TTL 정리 쿼리
]
```

---

## 7. 마이그레이션 계획

### 7.1 마이그레이션 생성

```bash
# 1. 모델 추가 후
python manage.py makemigrations serverless

# 2. 마이그레이션 확인
python manage.py sqlmigrate serverless 0004

# 3. 적용
python manage.py migrate serverless
```

### 7.2 초기 데이터 생성 (선택)

```python
# serverless/management/commands/generate_test_keywords.py

from django.core.management.base import BaseCommand
from serverless.services.keyword_service import KeywordGenerationService
from django.utils import timezone

class Command(BaseCommand):
    help = "테스트용 키워드 생성"

    def handle(self, *args, **options):
        service = KeywordGenerationService()
        today = timezone.now().date()

        for mover_type in ['gainers', 'losers', 'actives']:
            result = service.batch_generate(today, mover_type, limit=5)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{mover_type}: {result['success']}개 성공"
                )
            )
```

### 7.3 Celery Beat 스케줄 추가

```python
# config/celery.py (추가)

CELERYBEAT_SCHEDULE = {
    # 기존: Market Movers 동기화 (07:30)
    'sync-market-movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'schedule': crontab(hour=7, minute=30),
        'options': {'expires': 3600}
    },

    # 신규: 키워드 생성 (08:00) ⭐
    'generate-mover-keywords': {
        'task': 'serverless.tasks.generate_daily_keywords',
        'schedule': crontab(hour=8, minute=0),
        'options': {'expires': 3600}
    },

    # 신규: 만료 키워드 정리 (매일 02:00) ⭐
    'cleanup-expired-keywords': {
        'task': 'serverless.tasks.cleanup_expired_keywords',
        'schedule': crontab(hour=2, minute=0),
        'options': {'expires': 3600}
    },
}
```

**참고**: tasks.py 구현은 @infra 에이전트가 담당합니다.

---

## 8. 테스트 전략

### 8.1 단위 테스트

```python
# tests/serverless/test_keyword_service.py

from serverless.services.keyword_service import KeywordGenerationService

def test_keyword_generation_success():
    service = KeywordGenerationService()
    result = service.generate_keyword(
        symbol='NVDA',
        company_name='NVIDIA',
        date='2026-01-24',
        mover_type='gainers',
        change_percent=8.45,
        sector='Technology'
    )

    assert result['status'] == 'completed'
    assert len(result['keywords']) >= 3
    assert result['metadata']['generation_time_ms'] > 0

def test_fallback_on_llm_failure():
    # LLM 실패 시뮬레이션
    service = KeywordGenerationService()
    # ... mock LLM to raise exception ...
    result = service.generate_keyword(...)

    assert result['status'] == 'failed'
    assert result['keywords'] == ["급등", "거래량 증가", "모멘텀"]
```

### 8.2 통합 테스트

```python
# tests/serverless/test_movers_with_keywords.py

from django.test import TestCase
from serverless.processors import MarketMoversProcessor

class MoversWithKeywordsTestCase(TestCase):
    def test_get_movers_with_keywords(self):
        # Given: MarketMover + StockKeyword 데이터 준비
        # When: Processor 호출
        processor = MarketMoversProcessor()
        result = processor.get_movers_with_keywords('2026-01-24', 'gainers')

        # Then: 키워드 포함 확인
        assert len(result) > 0
        assert 'keywords' in result[0]
        assert len(result[0]['keywords']) >= 3
```

---

## 9. API 문서화

### 9.1 OpenAPI (Swagger) 스키마

```yaml
# docs/openapi.yaml

paths:
  /api/v1/serverless/movers:
    get:
      summary: Market Movers (키워드 포함)
      parameters:
        - name: type
          in: query
          schema:
            type: string
            enum: [gainers, losers, actives]
        - name: date
          in: query
          schema:
            type: string
            format: date
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
                    properties:
                      movers:
                        type: array
                        items:
                          type: object
                          properties:
                            symbol:
                              type: string
                            keywords:
                              type: array
                              items:
                                type: string
                              example: ["AI 반도체 수요", "데이터센터 확장"]
```

---

## 10. 체크리스트

### Backend 구현

- [ ] **모델 생성**: `StockKeyword` 모델 추가
- [ ] **서비스 레이어**: `KeywordGenerationService` 구현
- [ ] **Processor**: `MarketMoversProcessor` 구현
- [ ] **Views 업데이트**: `market_movers_api()` 수정
- [ ] **Serializer**: `MarketMoverListSerializer`에 키워드 필드 추가 (선택)
- [ ] **캐싱**: 키워드 포함 캐시 키 업데이트
- [ ] **마이그레이션**: 생성 및 적용
- [ ] **단위 테스트**: 키워드 생성 로직 테스트
- [ ] **통합 테스트**: API 응답 검증

### Infra 구현 (by @infra)

- [ ] **Celery 태스크**: `generate_daily_keywords` 구현
- [ ] **Celery 태스크**: `cleanup_expired_keywords` 구현
- [ ] **Beat 스케줄**: 08:00 키워드 생성 추가
- [ ] **Beat 스케줄**: 02:00 만료 데이터 정리 추가

### Frontend 구현 (by @frontend)

- [ ] **타입 정의**: `keywords: string[]` 추가
- [ ] **UI 컴포넌트**: MoverCard에 키워드 배지 표시
- [ ] **로딩 상태**: 키워드 없을 때 스켈레톤 UI
- [ ] **에러 핸들링**: Fallback 키워드 표시

---

## 11. 예상 비용 (LLM API)

### Gemini 2.5 Flash 요금

- **Input**: $0.075 / 1M tokens
- **Output**: $0.30 / 1M tokens

### 일일 비용 계산

```
전제:
- 일일 60개 종목 (gainers 20 + losers 20 + actives 20)
- 평균 input 200 tokens / 종목 (프롬프트)
- 평균 output 50 tokens / 종목 (키워드 3-5개)

계산:
- Input: 60 * 200 = 12,000 tokens = $0.0009
- Output: 60 * 50 = 3,000 tokens = $0.0009
- 일일 합계: $0.0018 (약 2.5원)

월간 비용 (30일):
- $0.0018 * 30 = $0.054 (약 75원)
```

**결론**: 거의 무료 수준 (월 100원 미만)

---

## 12. 롤백 계획

### Phase 1: 키워드 없이 배포

```python
# views.py
movers = processor.get_movers_with_keywords(date_str, mover_type)

# keywords 필드가 빈 배열이어도 프론트엔드는 정상 동작
# → Fallback UI: 키워드 섹션 숨김
```

### Phase 2: 문제 발생 시

1. **Celery Beat 비활성화**: `generate-mover-keywords` 스케줄 주석 처리
2. **캐시 무효화**: `cache.clear()` 또는 Redis FLUSHDB
3. **DB 롤백**: `python manage.py migrate serverless 0003` (이전 마이그레이션)

---

## 13. 향후 개선 사항

### Phase 2: 뉴스 기반 키워드

- **데이터 소스**: News API 또는 RSS 피드
- **프롬프트 개선**: 실제 뉴스 헤드라인 포함
- **정확도 향상**: 60% → 90%

### Phase 3: 멀티 언어 지원

- **한국어/영어 자동 감지**
- **번역 API 연동** (Google Translate)

### Phase 4: 사용자 맞춤형

- **선호 키워드 학습** (클릭 추적)
- **개인화된 키워드 순서**

---

## 요약

### 핵심 결정

| 항목 | 결정 사항 | 이유 |
|------|----------|------|
| **모델 관계** | FK 없이 symbol로 조인 | 독립적 TTL, 느슨한 결합 |
| **API 응답** | 기존 엔드포인트에 포함 | 프론트엔드 요청 최소화 |
| **LLM 모델** | Gemini 2.5 Flash | 빠르고 저렴 (월 100원 미만) |
| **Fallback** | mover_type 기반 기본 키워드 | LLM 실패 시 UX 유지 |
| **캐싱** | Redis 5분 TTL | 실시간성과 비용 균형 |
| **배치 생성** | Celery Beat 08:00 | Market Movers 동기화 후 |

### 3계층 아키텍처

```
Views (HTTP) → Processors (비즈니스 로직) → Services (LLM, DB)
                     ↓
              모든 메서드에 return문 필수
```

### 체크리스트 우선순위

1. ✅ **Backend**: 모델 → 서비스 → Processor → Views (4-6시간)
2. ⏳ **Infra**: Celery 태스크 (2시간)
3. ⏳ **Frontend**: UI 컴포넌트 (2시간)
