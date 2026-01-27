# Market Movers 키워드 생성 인프라 설계

## 1. 개요

Market Movers 종목별 AI 생성 키워드 시스템을 위한 Celery 태스크 및 인프라 설계.

- **목적**: 매일 Market Movers TOP 20 종목에 대해 투자자를 위한 3-5개 키워드 자동 생성
- **기술 스택**: Celery + Redis + Claude API (또는 Gemini Flash)
- **실행 주기**: Market Movers 동기화 직후 (매일 07:30 EST 이후)

---

## 2. 데이터베이스 모델 (추가 필요)

### MoverKeyword 모델

```python
# serverless/models.py

class MoverKeyword(models.Model):
    """
    Market Movers 종목별 AI 생성 키워드

    Phase 1: LLM 기반 자동 생성
    Phase 2: 사용자 피드백 기반 최적화
    """
    KEYWORD_STATUS_CHOICES = [
        ('pending', 'Pending'),      # 생성 대기
        ('generated', 'Generated'),  # 생성 완료
        ('failed', 'Failed'),        # 생성 실패
    ]

    date = models.DateField(db_index=True)
    mover_type = models.CharField(max_length=10)  # gainers/losers/actives
    symbol = models.CharField(max_length=10, db_index=True)

    # 키워드
    keywords = models.JSONField(
        help_text="AI 생성 키워드 리스트 (3-5개)"
    )

    # 메타데이터
    status = models.CharField(
        max_length=10,
        choices=KEYWORD_STATUS_CHOICES,
        default='pending'
    )
    model_used = models.CharField(
        max_length=50,
        help_text="사용된 LLM 모델 (gemini-2.5-flash, claude-3-5-haiku 등)"
    )
    generation_cost_usd = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True
    )
    generation_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="생성 소요 시간 (ms)"
    )

    # 피드백 (Phase 2)
    click_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    dislike_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_mover_keyword'
        unique_together = [['date', 'mover_type', 'symbol']]
        ordering = ['date', 'mover_type', 'symbol']
        indexes = [
            models.Index(fields=['date', 'mover_type']),
            models.Index(fields=['symbol', 'date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.date} {self.mover_type} {self.symbol}"
```

---

## 3. Celery 태스크 설계

### 3.1 태스크 구조

```
sync_daily_market_movers (07:30 EST)
    └─ [chain] ─▶ generate_mover_keywords (07:35 EST)
                      ├─ (배치 1) symbols[0:5]
                      ├─ (배치 2) symbols[5:10]
                      ├─ (배치 3) symbols[10:15]
                      └─ (배치 4) symbols[15:20]
```

### 3.2 태스크 코드

```python
# serverless/tasks.py

import logging
import time
from decimal import Decimal
from typing import List, Dict, Any
from celery import shared_task, chain
from django.utils import timezone

from serverless.models import MarketMover, MoverKeyword
from serverless.services.keyword_generator import KeywordGenerator

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 10,  # 10분 후 재시도
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,  # 최대 1시간
)
def generate_mover_keywords(self, target_date=None, mover_type='gainers'):
    """
    Market Movers 키워드 생성 태스크

    Args:
        target_date: 대상 날짜 (문자열, 기본값: 오늘)
        mover_type: 'gainers', 'losers', 'actives'

    Returns:
        {
            'total': int,
            'success': int,
            'failed': int,
            'skipped': int,
            'total_cost_usd': float,
            'avg_time_ms': int
        }

    Strategy:
        - Idempotent: 이미 생성된 키워드는 스킵
        - 배치 처리: 5개 종목씩 처리
        - Rate Limiting: LLM API 호출 간 1초 대기
        - Cost Tracking: 비용 로깅
    """
    try:
        # 날짜 변환
        if target_date:
            from datetime import datetime
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        logger.info(
            f"🚀 Celery Task 시작: generate_mover_keywords "
            f"(date={target_date}, type={mover_type})"
        )

        # Market Movers 종목 조회 (TOP 20)
        movers = MarketMover.objects.filter(
            date=target_date,
            mover_type=mover_type
        ).order_by('rank')[:20]

        if not movers.exists():
            logger.warning(f"No movers found for {target_date} {mover_type}")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'total_cost_usd': 0.0,
                'avg_time_ms': 0
            }

        # 키워드 생성기 초기화
        generator = KeywordGenerator()

        results = {
            'total': movers.count(),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_cost_usd': 0.0,
            'total_time_ms': 0,
            'avg_time_ms': 0
        }

        # 5개씩 배치 처리
        batch_size = 5
        for i, mover in enumerate(movers):
            try:
                # Idempotent: 이미 생성된 키워드는 스킵
                existing = MoverKeyword.objects.filter(
                    date=target_date,
                    mover_type=mover_type,
                    symbol=mover.symbol,
                    status='generated'
                ).exists()

                if existing:
                    logger.debug(f"Skipping {mover.symbol} - already generated")
                    results['skipped'] += 1
                    continue

                # 키워드 생성
                start_time = time.time()
                result = generator.generate_keywords(mover)
                elapsed_ms = int((time.time() - start_time) * 1000)

                # 저장
                MoverKeyword.objects.update_or_create(
                    date=target_date,
                    mover_type=mover_type,
                    symbol=mover.symbol,
                    defaults={
                        'keywords': result['keywords'],
                        'status': 'generated',
                        'model_used': result['model_used'],
                        'generation_cost_usd': Decimal(str(result['cost_usd'])),
                        'generation_time_ms': elapsed_ms
                    }
                )

                results['success'] += 1
                results['total_cost_usd'] += result['cost_usd']
                results['total_time_ms'] += elapsed_ms

                logger.info(
                    f"✅ {mover.symbol} keywords generated: {result['keywords']} "
                    f"(${result['cost_usd']:.6f}, {elapsed_ms}ms)"
                )

                # Rate Limiting: 배치 내 마지막 종목 제외하고 1초 대기
                if (i + 1) % batch_size != 0 and i < movers.count() - 1:
                    time.sleep(1.0)

            except Exception as e:
                logger.error(f"❌ Failed to generate keywords for {mover.symbol}: {e}")

                # 실패 기록
                MoverKeyword.objects.update_or_create(
                    date=target_date,
                    mover_type=mover_type,
                    symbol=mover.symbol,
                    defaults={
                        'status': 'failed',
                        'keywords': []
                    }
                )

                results['failed'] += 1

        # 평균 계산
        if results['success'] > 0:
            results['avg_time_ms'] = results['total_time_ms'] // results['success']

        logger.info(
            f"✅ Celery Task 완료: {results['success']} success, "
            f"{results['failed']} failed, {results['skipped']} skipped, "
            f"${results['total_cost_usd']:.6f}"
        )

        return results

    except Exception as exc:
        logger.exception(f"❌ 예상치 못한 에러: {exc}")
        raise


@shared_task
def generate_all_mover_keywords(target_date=None):
    """
    모든 타입의 Market Movers 키워드 생성 (Gainers + Losers + Actives)

    Args:
        target_date: 대상 날짜 (문자열, 기본값: 오늘)

    Returns:
        List[AsyncResult]

    Usage:
        from serverless.tasks import generate_all_mover_keywords
        generate_all_mover_keywords.delay()
    """
    logger.info(f"📋 생성 시작: All Market Movers Keywords (date={target_date or 'today'})")

    # 3가지 타입 병렬 실행
    tasks = [
        generate_mover_keywords.delay(target_date, 'gainers'),
        generate_mover_keywords.delay(target_date, 'losers'),
        generate_mover_keywords.delay(target_date, 'actives'),
    ]

    return [task.id for task in tasks]


@shared_task
def regenerate_failed_keywords(target_date=None):
    """
    실패한 키워드 재생성

    Args:
        target_date: 대상 날짜 (문자열, 기본값: 오늘)

    Returns:
        dict: 재생성 결과
    """
    try:
        if target_date:
            from datetime import datetime
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        # 실패한 키워드 조회
        failed_keywords = MoverKeyword.objects.filter(
            date=target_date,
            status='failed'
        )

        if not failed_keywords.exists():
            return {'total': 0, 'success': 0, 'failed': 0}

        generator = KeywordGenerator()
        results = {'total': failed_keywords.count(), 'success': 0, 'failed': 0}

        for keyword_obj in failed_keywords:
            try:
                # Market Mover 조회
                mover = MarketMover.objects.get(
                    date=target_date,
                    mover_type=keyword_obj.mover_type,
                    symbol=keyword_obj.symbol
                )

                # 재생성
                result = generator.generate_keywords(mover)

                # 업데이트
                keyword_obj.keywords = result['keywords']
                keyword_obj.status = 'generated'
                keyword_obj.model_used = result['model_used']
                keyword_obj.generation_cost_usd = Decimal(str(result['cost_usd']))
                keyword_obj.save()

                results['success'] += 1
                time.sleep(1.0)  # Rate limiting

            except Exception as e:
                logger.error(f"Failed to regenerate {keyword_obj.symbol}: {e}")
                results['failed'] += 1

        logger.info(f"Regenerated {results['success']}/{results['total']} keywords")
        return results

    except Exception as e:
        logger.exception(f"Regeneration task failed: {e}")
        raise
```

---

## 4. Celery Beat 스케줄

```python
# config/celery.py

app.conf.beat_schedule = {
    # ... 기존 스케줄 ...

    # ============================================================
    # Market Movers + Keywords 태스크
    # ============================================================

    # Market Movers 동기화 (매일 07:30 EST)
    'sync-market-movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'schedule': crontab(hour=7, minute=30),  # 07:30 EST
        'options': {'expires': 3600}
    },

    # Market Movers 키워드 생성 (매일 07:35 EST)
    'generate-mover-keywords-all': {
        'task': 'serverless.tasks.generate_all_mover_keywords',
        'schedule': crontab(hour=7, minute=35),  # 07:35 EST (동기화 5분 후)
        'options': {'expires': 7200}  # 2시간 후 만료
    },

    # 실패한 키워드 재시도 (매일 08:00 EST)
    'retry-failed-keywords': {
        'task': 'serverless.tasks.regenerate_failed_keywords',
        'schedule': crontab(hour=8, minute=0),  # 08:00 EST
        'options': {'expires': 3600}
    },
}
```

**스케줄 선택 근거**:
- 07:30: Market Movers 동기화 (FMP API에서 데이터 수집)
- 07:35: 키워드 생성 시작 (5분 여유)
- 08:00: 실패 재시도 (25분 여유)

---

## 5. Redis 캐싱 전략

### 5.1 캐시 키 설계

```python
# serverless/services/cache.py

class MoverKeywordCache:
    """Market Movers 키워드 Redis 캐싱"""

    @staticmethod
    def get_cache_key(date, mover_type, symbol=None):
        """캐시 키 생성"""
        if symbol:
            return f"mover:keywords:{date}:{mover_type}:{symbol}"
        else:
            return f"mover:keywords:{date}:{mover_type}:all"

    @staticmethod
    def get_ttl():
        """TTL: 24시간"""
        return 86400

    def get_keywords(self, date, mover_type, symbol):
        """
        종목별 키워드 조회

        Returns:
            List[str] | None
        """
        cache_key = self.get_cache_key(date, mover_type, symbol)
        # Redis GET
        # ...

    def get_all_keywords(self, date, mover_type):
        """
        타입별 전체 키워드 조회 (TOP 20)

        Returns:
            List[Dict] | None
        """
        cache_key = self.get_cache_key(date, mover_type)
        # Redis GET
        # ...

    def set_keywords(self, date, mover_type, keywords_data):
        """
        키워드 캐싱

        Args:
            keywords_data: [
                {'symbol': 'AAPL', 'keywords': ['AI 성장', ...]},
                ...
            ]
        """
        cache_key = self.get_cache_key(date, mover_type)
        ttl = self.get_ttl()
        # Redis SETEX
        # ...
```

### 5.2 캐싱 전략

| 데이터 | Cache Key | TTL | 무효화 조건 |
|--------|-----------|-----|------------|
| 타입별 전체 키워드 | `mover:keywords:{date}:{type}:all` | 24시간 | 새로운 키워드 생성 |
| 종목별 키워드 | `mover:keywords:{date}:{type}:{symbol}` | 24시간 | 종목 키워드 재생성 |

---

## 6. LLM API Rate Limiting

### 6.1 전략 선택: **배치 처리 (5개씩)**

**선택 근거**:
- 20개 종목 × 3타입 = 60개 API 호출/일
- Gemini Flash: 분당 15 RPM (무료 티어)
- Claude Haiku: 분당 5 RPM (Tier 1)
- **배치 5개 + 1초 간격** = 안전한 처리

### 6.2 코스트 분석

| 모델 | Input Tokens | Output Tokens | 단가 ($/1M) | 종목당 비용 |
|------|-------------|---------------|------------|------------|
| Gemini 2.5 Flash | ~500 | ~100 | 0.15/0.60 | $0.00013 |
| Claude 3.5 Haiku | ~500 | ~100 | 0.80/4.00 | $0.00048 |

**일일 비용 추정**:
- Gemini Flash: 60개 × $0.00013 = **$0.0078/일** (~$0.23/월)
- Claude Haiku: 60개 × $0.00048 = **$0.0288/일** (~$0.86/월)

**권장**: **Gemini 2.5 Flash** (비용 효율성 + 속도)

### 6.3 Rate Limiting 구현

```python
# serverless/services/keyword_generator.py

import time
from anthropic import Anthropic
from google.generativeai import GenerativeModel

class KeywordGenerator:
    """
    Market Movers 키워드 생성기

    LLM을 사용하여 종목별 투자 키워드를 자동 생성합니다.
    """

    # Rate Limiting
    MIN_REQUEST_INTERVAL = 1.0  # 초
    last_request_time = 0

    def __init__(self, model='gemini-2.5-flash'):
        """
        Args:
            model: 'gemini-2.5-flash' | 'claude-3-5-haiku'
        """
        self.model = model

        if 'gemini' in model:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.client = genai.GenerativeModel(model)
        elif 'claude' in model:
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def generate_keywords(self, mover: MarketMover) -> Dict[str, Any]:
        """
        종목 키워드 생성

        Args:
            mover: MarketMover 인스턴스

        Returns:
            {
                'keywords': List[str],  # 3-5개
                'model_used': str,
                'cost_usd': float,
                'input_tokens': int,
                'output_tokens': int
            }
        """
        # Rate Limiting
        self._wait_for_rate_limit()

        # 프롬프트 생성
        prompt = self._build_prompt(mover)

        # LLM 호출
        start_time = time.time()

        if 'gemini' in self.model:
            response = self._call_gemini(prompt)
        else:
            response = self._call_claude(prompt)

        elapsed = time.time() - start_time

        # 키워드 파싱
        keywords = self._parse_keywords(response['text'])

        # 비용 계산
        cost = self._calculate_cost(
            response['input_tokens'],
            response['output_tokens']
        )

        logger.info(
            f"Generated {len(keywords)} keywords for {mover.symbol} "
            f"in {elapsed:.2f}s (${cost:.6f})"
        )

        return {
            'keywords': keywords,
            'model_used': self.model,
            'cost_usd': cost,
            'input_tokens': response['input_tokens'],
            'output_tokens': response['output_tokens']
        }

    def _wait_for_rate_limit(self):
        """Rate Limiting: 요청 간 최소 1초 대기"""
        elapsed = time.time() - self.__class__.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            wait_time = self.MIN_REQUEST_INTERVAL - elapsed
            time.sleep(wait_time)
        self.__class__.last_request_time = time.time()

    def _build_prompt(self, mover: MarketMover) -> str:
        """
        프롬프트 생성

        컨텍스트:
        - 종목명, 섹터, 산업
        - 가격 변동률, 거래량
        - 5개 지표 (RVOL, Trend, Alpha, Sync, Volatility)
        """
        return f"""당신은 미국 주식 투자 전문가입니다.

다음 종목 정보를 바탕으로 투자자가 빠르게 이해할 수 있는 **핵심 키워드 3-5개**를 생성해주세요.

종목 정보:
- 심볼: {mover.symbol}
- 회사명: {mover.company_name}
- 섹터: {mover.sector or 'N/A'}
- 산업: {mover.industry or 'N/A'}
- 가격: ${mover.price}
- 변동률: {mover.change_percent:+.2f}%
- 거래량: {mover.volume:,}

지표:
- RVOL (거래량 배수): {mover.rvol_display or 'N/A'}
- 추세 강도: {mover.trend_display or 'N/A'}
- 섹터 알파: {mover.sector_alpha or 'N/A'}
- ETF 동행률: {mover.etf_sync_rate or 'N/A'}
- 변동성 백분위: {mover.volatility_pct or 'N/A'}

요구사항:
1. 한글로 3-5개 키워드 생성
2. 각 키워드는 2-5단어
3. 투자 관점에서 유용한 정보
4. 간결하고 명확하게
5. JSON 배열 형식으로 출력: ["키워드1", "키워드2", ...]

예시:
["급등 모멘텀", "섹터 강세", "고거래량", "기술적 돌파", "실적 기대감"]

키워드만 출력하고 다른 설명은 추가하지 마세요.
"""

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Gemini API 호출"""
        response = self.client.generate_content(prompt)

        return {
            'text': response.text,
            'input_tokens': response.usage_metadata.prompt_token_count,
            'output_tokens': response.usage_metadata.candidates_token_count
        }

    def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Claude API 호출"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            'text': response.content[0].text,
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens
        }

    def _parse_keywords(self, text: str) -> List[str]:
        """
        LLM 응답에서 키워드 파싱

        Expected format: ["키워드1", "키워드2", ...]
        """
        import json
        import re

        # JSON 배열 추출
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                keywords = json.loads(match.group(0))
                # 3-5개 제한
                return keywords[:5]
            except json.JSONDecodeError:
                pass

        # Fallback: 쉼표 구분 파싱
        keywords = [k.strip().strip('"\'') for k in text.split(',')]
        return keywords[:5]

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """비용 계산 (USD)"""
        if 'gemini-2.5-flash' in self.model:
            input_cost = (input_tokens / 1_000_000) * 0.15
            output_cost = (output_tokens / 1_000_000) * 0.60
        elif 'claude-3-5-haiku' in self.model:
            input_cost = (input_tokens / 1_000_000) * 0.80
            output_cost = (output_tokens / 1_000_000) * 4.00
        else:
            # 기본값
            input_cost = (input_tokens / 1_000_000) * 1.00
            output_cost = (output_tokens / 1_000_000) * 5.00

        return input_cost + output_cost
```

---

## 7. 에러 처리

### 7.1 재시도 전략

```python
@shared_task(
    bind=True,
    max_retries=3,                     # 최대 3회 재시도
    default_retry_delay=60 * 10,       # 10분 간격
    autoretry_for=(Exception,),        # 모든 예외 자동 재시도
    retry_backoff=True,                # Exponential backoff
    retry_backoff_max=3600,            # 최대 1시간
)
```

**Exponential Backoff**:
- 1차 재시도: 10분 후
- 2차 재시도: 20분 후
- 3차 재시도: 40분 후 (최대 1시간)

### 7.2 부분 실패 처리

- **전략**: 개별 종목별 try-except 처리
- **이점**: 일부 실패해도 나머지 종목은 계속 처리
- **기록**: 실패한 종목은 `status='failed'`로 DB 저장

### 7.3 실패 복구

- **자동 재시도**: Celery retry 메커니즘
- **수동 재시도**: `regenerate_failed_keywords` 태스크 (매일 08:00)
- **모니터링**: 실패율이 30% 초과 시 알림

---

## 8. 모니터링

### 8.1 메트릭

```python
# serverless/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# 키워드 생성 카운터
keyword_generation_counter = Counter(
    'mover_keyword_generation_total',
    'Market Mover 키워드 생성 횟수',
    ['status', 'model']  # status: success/failed/skipped
)

# 키워드 생성 시간
keyword_generation_time = Histogram(
    'mover_keyword_generation_duration_seconds',
    'Market Mover 키워드 생성 시간',
    ['model']
)

# 키워드 생성 비용
keyword_generation_cost = Counter(
    'mover_keyword_generation_cost_usd_total',
    'Market Mover 키워드 생성 비용 (USD)',
    ['model']
)

# 실패율
keyword_failure_rate = Gauge(
    'mover_keyword_failure_rate',
    'Market Mover 키워드 생성 실패율',
    ['date', 'mover_type']
)
```

### 8.2 로깅

```python
logger.info(
    f"✅ {mover.symbol} keywords generated: {result['keywords']} "
    f"(${result['cost_usd']:.6f}, {elapsed_ms}ms)"
)

logger.warning(
    f"⚠️ Keyword generation failure rate: {failure_rate:.2%} "
    f"(threshold: 30%)"
)

logger.error(
    f"❌ Failed to generate keywords for {mover.symbol}: {exc}"
)
```

---

## 9. API 엔드포인트 (추가 필요)

```python
# serverless/api/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from serverless.models import MoverKeyword

@api_view(['GET'])
def get_mover_keywords(request):
    """
    Market Movers 키워드 조회

    Query Params:
        - type: 'gainers' | 'losers' | 'actives' (필수)
        - date: YYYY-MM-DD (선택, 기본값: 오늘)

    Response:
        [
            {
                'symbol': 'AAPL',
                'company_name': 'Apple Inc.',
                'keywords': ['AI 성장', '실적 호조', '프리미엄 밸류', '기술 리더십'],
                'price': 225.50,
                'change_percent': 5.23,
                'sector': 'Technology'
            },
            ...
        ]
    """
    mover_type = request.query_params.get('type', 'gainers')
    date_str = request.query_params.get('date')

    # 날짜 파싱
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = timezone.now().date()

    # 키워드 조회
    keywords = MoverKeyword.objects.filter(
        date=target_date,
        mover_type=mover_type,
        status='generated'
    ).select_related('mover')

    # 시리얼라이즈
    data = [
        {
            'symbol': kw.symbol,
            'keywords': kw.keywords,
            'model_used': kw.model_used,
            'generation_time_ms': kw.generation_time_ms
        }
        for kw in keywords
    ]

    return Response(data)
```

---

## 10. 테스트 커버리지

### 10.1 단위 테스트

```python
# tests/serverless/test_keyword_generator.py

import pytest
from unittest.mock import Mock, patch
from serverless.models import MarketMover
from serverless.services.keyword_generator import KeywordGenerator

@pytest.fixture
def sample_mover():
    return MarketMover(
        symbol='AAPL',
        company_name='Apple Inc.',
        sector='Technology',
        price=225.50,
        change_percent=5.23,
        rvol_display='2.5x',
        trend_display='▲0.85'
    )

class TestKeywordGenerator:

    def test_build_prompt(self, sample_mover):
        """프롬프트 생성 테스트"""
        generator = KeywordGenerator()
        prompt = generator._build_prompt(sample_mover)

        assert 'AAPL' in prompt
        assert 'Technology' in prompt
        assert '5.23%' in prompt

    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_generate_keywords_success(self, mock_generate, sample_mover):
        """키워드 생성 성공 케이스"""
        # Mock response
        mock_response = Mock()
        mock_response.text = '["AI 성장", "실적 호조", "프리미엄 밸류"]'
        mock_response.usage_metadata.prompt_token_count = 500
        mock_response.usage_metadata.candidates_token_count = 100
        mock_generate.return_value = mock_response

        generator = KeywordGenerator(model='gemini-2.5-flash')
        result = generator.generate_keywords(sample_mover)

        assert len(result['keywords']) == 3
        assert result['model_used'] == 'gemini-2.5-flash'
        assert result['cost_usd'] > 0

    def test_parse_keywords_json(self):
        """JSON 파싱 테스트"""
        generator = KeywordGenerator()
        text = '["키워드1", "키워드2", "키워드3"]'
        keywords = generator._parse_keywords(text)

        assert keywords == ["키워드1", "키워드2", "키워드3"]

    def test_parse_keywords_fallback(self):
        """Fallback 파싱 테스트"""
        generator = KeywordGenerator()
        text = '키워드1, 키워드2, 키워드3'
        keywords = generator._parse_keywords(text)

        assert len(keywords) == 3

    def test_calculate_cost_gemini(self):
        """Gemini 비용 계산"""
        generator = KeywordGenerator(model='gemini-2.5-flash')
        cost = generator._calculate_cost(500, 100)

        expected = (500 / 1_000_000) * 0.15 + (100 / 1_000_000) * 0.60
        assert cost == pytest.approx(expected)

    def test_rate_limiting(self):
        """Rate Limiting 테스트"""
        import time

        generator = KeywordGenerator()

        start = time.time()
        generator._wait_for_rate_limit()
        generator._wait_for_rate_limit()
        elapsed = time.time() - start

        # 최소 1초 간격
        assert elapsed >= 1.0
```

### 10.2 통합 테스트

```python
# tests/serverless/test_keyword_tasks.py

import pytest
from datetime import date
from serverless.models import MarketMover, MoverKeyword
from serverless.tasks import generate_mover_keywords

@pytest.mark.django_db
class TestKeywordTasks:

    def test_generate_mover_keywords_success(self):
        """키워드 생성 태스크 성공"""
        # Given: Market Mover 데이터
        MarketMover.objects.create(
            date=date.today(),
            mover_type='gainers',
            rank=1,
            symbol='AAPL',
            company_name='Apple Inc.',
            price=225.50,
            change_percent=5.23,
            volume=100000000
        )

        # When: 태스크 실행
        result = generate_mover_keywords(target_date=str(date.today()), mover_type='gainers')

        # Then: 키워드 생성 확인
        assert result['success'] >= 1

        keyword = MoverKeyword.objects.get(
            date=date.today(),
            mover_type='gainers',
            symbol='AAPL'
        )
        assert keyword.status == 'generated'
        assert len(keyword.keywords) >= 3

    def test_idempotent(self):
        """Idempotent 테스트 (중복 실행 안전)"""
        # 1차 실행
        result1 = generate_mover_keywords(target_date=str(date.today()), mover_type='gainers')

        # 2차 실행 (중복)
        result2 = generate_mover_keywords(target_date=str(date.today()), mover_type='gainers')

        # 스킵 확인
        assert result2['skipped'] > 0
```

---

## 11. 배포 체크리스트

- [ ] Migration 생성 및 적용 (`MoverKeyword` 모델)
- [ ] `KeywordGenerator` 서비스 구현
- [ ] Celery 태스크 구현 (`serverless/tasks.py`)
- [ ] Celery Beat 스케줄 추가 (`config/celery.py`)
- [ ] Redis 캐싱 로직 구현
- [ ] API 엔드포인트 추가 (`serverless/api/views.py`)
- [ ] 단위/통합 테스트 작성 (최소 90% 커버리지)
- [ ] 환경변수 설정 (`.env.example`)
  - `GEMINI_API_KEY` (권장)
  - `ANTHROPIC_API_KEY` (선택)
- [ ] 로깅 및 모니터링 설정
- [ ] Prometheus 메트릭 추가
- [ ] 프로덕션 배포

---

## 12. 예상 일정

| 주차 | 작업 | 담당 |
|------|------|------|
| Week 1 | DB 모델, Migration, KeywordGenerator 서비스 | @backend |
| Week 2 | Celery 태스크, Beat 스케줄, Rate Limiting | @infra |
| Week 3 | API 엔드포인트, Redis 캐싱, 테스트 | @backend + @qa |
| Week 4 | Frontend 통합, 모니터링, 배포 | @frontend + @infra |

---

## 13. 참고 문서

- Market Movers 5개 지표: `CLAUDE.md`
- FMP API 문서: `docs/FMP_API_GUIDE.md`
- Celery 태스크 패턴: `rag_analysis/tasks.py`
- Cost Tracker: `rag_analysis/services/cost_tracker.py`
