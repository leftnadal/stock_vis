"""
Market Movers 키워드 생성 서비스 사용 예시

V2 (Enhanced) vs V1 (Basic) 비교 및 통합 가이드
"""

import asyncio
from datetime import date
from typing import List, Dict, Any

# V2 (Enhanced) - 풍부한 컨텍스트
from .keyword_generator_v2 import EnhancedKeywordGenerator, generate_keywords_sync_v2

# V1 (Basic) - 기존 단순 버전
from .keyword_generator import KeywordGeneratorService, generate_keywords_sync


# ============================================================
# 사용 예시 1: V2 (Enhanced) - Overview + 뉴스 활용
# ============================================================

async def example_v2_with_enrichment():
    """
    V2 Enhanced 버전 사용 예시 (Overview + 뉴스 보강)

    Use Case:
    - 일일 배치 키워드 생성 (아침 07:30)
    - 최대 품질 키워드 필요
    - 토큰 비용 감당 가능 (일 3회 * 60개 = 180개 종목)
    """
    generator = EnhancedKeywordGenerator(
        language="ko",
        enable_enrichment=True  # Overview + 뉴스 보강 활성화
    )

    today = date.today()

    # Gainers 키워드 생성
    results = await generator.generate_keywords_for_movers(
        mover_date=today,
        mover_type='gainers',
        max_stocks=20
    )

    for result in results:
        print(f"\n{result['symbol']} - {result['summary']}")
        for kw in result['keywords']:
            print(f"  [{kw['category']}] {kw['text']} (confidence: {kw['confidence']:.2f})")

    # 비용 추정
    cost_estimate = generator.estimate_batch_cost(num_stocks=20)
    print(f"\nEstimated cost: ${cost_estimate['total_cost_usd']:.6f}")


# ============================================================
# 사용 예시 2: V2 (Basic) - 지표만 활용
# ============================================================

async def example_v2_without_enrichment():
    """
    V2 Enhanced 버전 사용 예시 (지표만 사용)

    Use Case:
    - 빠른 키워드 생성 필요
    - 토큰 비용 최소화
    - Overview/뉴스 없이도 충분한 품질
    """
    generator = EnhancedKeywordGenerator(
        language="ko",
        enable_enrichment=False  # 보강 비활성화
    )

    today = date.today()

    results = await generator.generate_keywords_for_movers(
        mover_date=today,
        mover_type='losers',
        max_stocks=20
    )

    for result in results:
        print(f"{result['symbol']}: {result['summary']}")


# ============================================================
# 사용 예시 3: Celery 태스크 통합
# ============================================================

def example_celery_task():
    """
    Celery 태스크에서 동기 함수 사용

    @shared_task
    def generate_market_movers_keywords_task(mover_date, mover_type):
        results = generate_keywords_sync_v2(
            mover_date=mover_date,
            mover_type=mover_type,
            language='ko',
            max_stocks=20,
            enable_enrichment=True  # 일일 배치는 풍부한 컨텍스트 사용
        )

        # DB 저장
        from serverless.models import StockKeyword
        from django.utils import timezone
        from datetime import timedelta

        for result in results:
            StockKeyword.objects.update_or_create(
                symbol=result['symbol'],
                date=mover_date,
                defaults={
                    'company_name': '...',
                    'keywords': [kw['text'] for kw in result['keywords']],  # 텍스트만 저장
                    'status': 'completed',
                    'llm_model': 'gemini-2.5-flash-v2',
                    'expires_at': timezone.now() + timedelta(days=7),
                }
            )

        return {'success': len(results)}
    """
    pass


# ============================================================
# 사용 예시 4: V1 vs V2 비교
# ============================================================

async def example_compare_v1_v2():
    """
    V1 (Basic) vs V2 (Enhanced) 성능/품질 비교

    | 항목           | V1 (Basic)           | V2 (Enhanced)                    |
    |----------------|----------------------|----------------------------------|
    | 입력 데이터    | 기본 정보 + 지표     | 기본 정보 + 지표 + Overview + 뉴스 |
    | 키워드 카테고리| 없음 (단순 텍스트)   | 6개 카테고리 (event, technical 등) |
    | Confidence     | 없음                 | 0.0~1.0 점수                      |
    | Summary        | 없음                 | 1-2문장 요약                      |
    | 토큰 사용량    | ~150 토큰/종목       | ~200 토큰/종목 (Overview/뉴스 포함) |
    | 비용           | $0.000045/종목       | $0.000060/종목 (+33%)             |
    | 품질           | 기본                 | 높음 (뉴스 기반 이벤트 키워드)     |
    """
    from datetime import date

    today = date.today()
    symbol = 'AAPL'

    # V1 결과
    v1_generator = KeywordGeneratorService()
    # ... (V1은 단일 종목 생성 함수 필요)

    # V2 결과
    v2_generator = EnhancedKeywordGenerator(enable_enrichment=True)
    from serverless.models import MarketMover

    mover = MarketMover.objects.filter(symbol=symbol, date=today).first()
    if mover:
        v2_result = await v2_generator.generate_keywords_single(mover)

        print("=== V2 (Enhanced) ===")
        print(f"Summary: {v2_result['summary']}")
        print("\nKeywords:")
        for kw in v2_result['keywords']:
            print(f"  [{kw['category']}] {kw['text']} (conf: {kw['confidence']:.2f})")


# ============================================================
# 권장 통합 전략
# ============================================================

"""
## 권장 통합 전략

### Phase 1: V2 병렬 운영 (2주)
- V1 유지 (기존 프로덕션)
- V2 실험 (일일 배치 1회)
- 품질 비교 (수동 검토)

### Phase 2: V2 부분 전환 (2주)
- Gainers: V2 (뉴스 중요도 높음)
- Losers: V1 (기존 로직)
- Actives: V1 (기존 로직)

### Phase 3: V2 전환 (1주)
- 모든 mover_type을 V2로 전환
- V1 코드 제거 또는 백업

### Phase 4: 최적화 (지속)
- enable_enrichment 조건부 활성화
  - Gainers: 항상 활성화 (뉴스 필수)
  - Losers: RVOL > 2.0일 때만 활성화
  - Actives: 변동성 상위 10개만 활성화

## Celery Beat 스케줄 예시

```python
# config/celery.py

CELERY_BEAT_SCHEDULE = {
    'generate-market-movers-keywords': {
        'task': 'serverless.tasks.generate_all_keywords_v2',
        'schedule': crontab(hour=7, minute=45),  # 07:45 EST (Movers 동기화 후 15분)
        'options': {'expires': 3600}
    }
}
```

## 태스크 구현 예시

```python
# serverless/tasks.py

from celery import shared_task
from datetime import date
from .services.keyword_generator_v2 import generate_keywords_sync_v2
from .models import StockKeyword
from django.utils import timezone
from datetime import timedelta


@shared_task(bind=True, max_retries=2)
def generate_all_keywords_v2(self):
    '''
    Market Movers 키워드 생성 (V2 Enhanced)

    Gainers/Losers/Actives 각 20개씩 총 60개 종목 처리
    '''
    today = date.today()
    results = {'success': 0, 'failed': 0}

    for mover_type in ['gainers', 'losers', 'actives']:
        try:
            keywords_data = generate_keywords_sync_v2(
                mover_date=today,
                mover_type=mover_type,
                language='ko',
                max_stocks=20,
                enable_enrichment=(mover_type == 'gainers')  # Gainers만 뉴스 보강
            )

            # DB 저장
            for item in keywords_data:
                StockKeyword.objects.update_or_create(
                    symbol=item['symbol'],
                    date=today,
                    defaults={
                        'company_name': '...',  # MarketMover에서 조회
                        'keywords': [kw['text'] for kw in item['keywords']],
                        'status': 'completed',
                        'llm_model': 'gemini-2.5-flash-v2',
                        'expires_at': timezone.now() + timedelta(days=7),
                    }
                )
                results['success'] += 1

        except Exception as e:
            results['failed'] += 1
            logger.exception(f"Failed to generate keywords for {mover_type}: {e}")

    return results
```
"""


# ============================================================
# 실행 예시
# ============================================================

if __name__ == '__main__':
    # 비동기 예시 실행
    asyncio.run(example_v2_with_enrichment())

    # 동기 예시 (Celery 태스크)
    # example_celery_task()
