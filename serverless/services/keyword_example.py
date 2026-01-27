"""
Market Movers 키워드 생성 시스템 - 사용 예시

실제 운영 환경에서 사용할 수 있는 예시 코드 모음
"""

import asyncio
from datetime import date, timedelta
from typing import List, Dict, Any

# Django 초기화 (스탠드얼론 스크립트용)
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from serverless.models import MarketMover, StockKeyword
from serverless.services.keyword_generator import KeywordGeneratorService
from serverless.services.keyword_context import KeywordContextBuilder
from django.utils import timezone


# ========================================
# 예시 1: 배치 키워드 생성
# ========================================

async def example_batch_generation():
    """
    배치 키워드 생성 예시 (20개 종목)
    """
    print("=" * 60)
    print("예시 1: 배치 키워드 생성 (20개 종목)")
    print("=" * 60)

    service = KeywordGeneratorService(language='ko')

    # 2026-01-24 Gainers TOP 20
    mover_date = date(2026, 1, 24)
    mover_type = 'gainers'

    print(f"\n생성 대상: {mover_date} {mover_type.upper()}")

    # 비용 추정
    cost_estimate = service.estimate_batch_cost(num_stocks=20)
    print(f"\n예상 비용:")
    print(f"  - 입력 토큰: {cost_estimate['input_tokens']:,}")
    print(f"  - 출력 토큰: {cost_estimate['output_tokens']:,}")
    print(f"  - 총 토큰: {cost_estimate['total_tokens']:,}")
    print(f"  - 비용: ${cost_estimate['total_cost_usd']:.6f}")

    # 키워드 생성
    print("\n키워드 생성 중...")
    results = await service.generate_keywords_for_movers(
        mover_date=mover_date,
        mover_type=mover_type,
        max_stocks=20
    )

    print(f"\n✅ 생성 완료: {len(results)}개 종목")

    # 결과 샘플 출력
    if results:
        sample = results[0]
        print(f"\n샘플 결과 ({sample['symbol']}):")
        print(f"  키워드:")
        for kw in sample['keywords'][:3]:
            print(f"    - {kw['text']} (카테고리: {kw['category']}, 신뢰도: {kw['confidence']:.2f})")
        print(f"  요약: {sample['summary'][:100]}...")

    return results


# ========================================
# 예시 2: 단일 종목 키워드 생성
# ========================================

async def example_single_generation():
    """
    단일 종목 키워드 생성 예시
    """
    print("\n" + "=" * 60)
    print("예시 2: 단일 종목 키워드 생성")
    print("=" * 60)

    service = KeywordGeneratorService(language='ko')

    # MarketMover 조회
    try:
        mover = MarketMover.objects.filter(
            date=date(2026, 1, 24),
            mover_type='gainers'
        ).first()

        if not mover:
            print("\n⚠️ MarketMover 데이터가 없습니다.")
            return None

        print(f"\n종목: {mover.symbol} - {mover.company_name}")
        print(f"가격: ${mover.price} ({mover.change_percent:+.2f}%)")

        # 키워드 생성
        print("\n키워드 생성 중...")
        result = await service.generate_keywords_single(mover)

        if result:
            print(f"\n✅ 생성 완료")
            print(f"  키워드 수: {len(result['keywords'])}개")
            for kw in result['keywords']:
                print(f"    - {kw['text']} ({kw['category']})")
            print(f"  요약: {result['summary']}")
        else:
            print("\n❌ 키워드 생성 실패")

        return result

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        return None


# ========================================
# 예시 3: 토큰 최적화 비교
# ========================================

def example_token_optimization():
    """
    배치 vs 개별 처리 토큰 비교
    """
    print("\n" + "=" * 60)
    print("예시 3: 토큰 최적화 비교")
    print("=" * 60)

    for num_stocks in [5, 10, 20]:
        comparison = KeywordContextBuilder.compare_batch_vs_individual(
            num_stocks=num_stocks
        )

        print(f"\n{num_stocks}개 종목:")
        print(f"  배치 처리:")
        print(f"    - 토큰: {comparison['batch']['total_tokens']:,}")
        print(f"    - 비용: ${comparison['batch']['cost_usd']:.6f}")
        print(f"  개별 처리:")
        print(f"    - 토큰: {comparison['individual']['total_tokens']:,}")
        print(f"    - 비용: ${comparison['individual']['cost_usd']:.6f}")
        print(f"  절약:")
        print(f"    - 토큰: {comparison['savings']['tokens']:,} ({comparison['savings']['percent']:.1f}%)")
        print(f"    - 비용: ${comparison['savings']['cost_usd']:.6f}")
        print(f"  권장: {comparison['recommendation']}")


# ========================================
# 예시 4: 데이터베이스 저장
# ========================================

async def example_save_to_database():
    """
    키워드를 StockKeyword 모델에 저장하는 예시
    """
    print("\n" + "=" * 60)
    print("예시 4: 데이터베이스 저장")
    print("=" * 60)

    service = KeywordGeneratorService(language='ko')

    # 키워드 생성
    mover_date = date.today()
    results = await service.generate_keywords_for_movers(
        mover_date=mover_date,
        mover_type='gainers',
        max_stocks=5
    )

    print(f"\n생성된 키워드: {len(results)}개")

    # 데이터베이스 저장
    saved_count = 0
    for result in results:
        try:
            # MarketMover 조회 (company_name 가져오기)
            mover = MarketMover.objects.get(
                date=mover_date,
                mover_type='gainers',
                symbol=result['symbol']
            )

            # StockKeyword 생성/업데이트
            keyword_obj, created = StockKeyword.objects.update_or_create(
                symbol=result['symbol'],
                date=mover_date,
                defaults={
                    'company_name': mover.company_name,
                    'keywords': result['keywords'],
                    'llm_model': 'gemini-2.5-flash',
                    'status': 'completed',
                    'expires_at': timezone.now() + timedelta(days=7)
                }
            )

            action = "생성" if created else "업데이트"
            print(f"  ✅ {result['symbol']}: {action} ({len(result['keywords'])}개 키워드)")
            saved_count += 1

        except Exception as e:
            print(f"  ❌ {result['symbol']}: 저장 실패 - {e}")

    print(f"\n총 저장: {saved_count}/{len(results)}")


# ========================================
# 예시 5: 캐시 조회
# ========================================

def example_cache_lookup():
    """
    StockKeyword 캐시 조회 예시
    """
    print("\n" + "=" * 60)
    print("예시 5: 캐시 조회")
    print("=" * 60)

    symbol = 'AAPL'
    today = date.today()

    print(f"\n조회: {symbol} ({today})")

    try:
        keyword_obj = StockKeyword.objects.get(
            symbol=symbol,
            date=today,
            status='completed'
        )

        print(f"\n✅ 캐시 히트!")
        print(f"  키워드 수: {len(keyword_obj.keywords)}개")
        print(f"  생성 시간: {keyword_obj.created_at}")
        print(f"  만료 시간: {keyword_obj.expires_at}")
        print(f"  키워드:")
        for kw in keyword_obj.keywords:
            print(f"    - {kw}")

        return keyword_obj

    except StockKeyword.DoesNotExist:
        print(f"\n⚠️ 캐시 미스 - 키워드 생성 필요")
        return None


# ========================================
# 예시 6: 만료된 캐시 정리
# ========================================

def example_cache_cleanup():
    """
    만료된 StockKeyword 정리 예시
    """
    print("\n" + "=" * 60)
    print("예시 6: 만료된 캐시 정리")
    print("=" * 60)

    now = timezone.now()

    # 만료된 키워드 조회
    expired = StockKeyword.objects.filter(
        expires_at__lt=now
    )

    count = expired.count()
    print(f"\n만료된 키워드: {count}개")

    if count > 0:
        # 삭제
        expired.delete()
        print(f"✅ 삭제 완료")
    else:
        print("만료된 키워드 없음")


# ========================================
# 예시 7: 일일 배치 처리 시뮬레이션
# ========================================

async def example_daily_batch():
    """
    일일 배치 처리 시뮬레이션 (Gainers + Losers + Actives)
    """
    print("\n" + "=" * 60)
    print("예시 7: 일일 배치 처리 시뮬레이션")
    print("=" * 60)

    service = KeywordGeneratorService(language='ko')
    mover_date = date.today()

    total_cost = 0.0
    total_keywords = 0

    for mover_type in ['gainers', 'losers', 'actives']:
        print(f"\n{mover_type.upper()} 처리 중...")

        # 키워드 생성
        results = await service.generate_keywords_for_movers(
            mover_date=mover_date,
            mover_type=mover_type,
            max_stocks=20
        )

        # 비용 추정
        cost = service.estimate_batch_cost(num_stocks=len(results))

        print(f"  - 종목 수: {len(results)}개")
        print(f"  - 비용: ${cost['total_cost_usd']:.6f}")

        total_cost += cost['total_cost_usd']
        total_keywords += len(results)

    print(f"\n{'=' * 60}")
    print(f"일일 총계:")
    print(f"  - 종목 수: {total_keywords}개")
    print(f"  - 총 비용: ${total_cost:.6f}")
    print(f"\n월간 예상 비용 (30일): ${total_cost * 30:.2f}")
    print(f"연간 예상 비용 (365일): ${total_cost * 365:.2f}")


# ========================================
# 메인 실행
# ========================================

async def main():
    """
    모든 예시 실행
    """
    # 예시 1: 배치 키워드 생성
    await example_batch_generation()

    # 예시 2: 단일 종목 키워드 생성
    await example_single_generation()

    # 예시 3: 토큰 최적화 비교
    example_token_optimization()

    # 예시 4: 데이터베이스 저장
    # await example_save_to_database()

    # 예시 5: 캐시 조회
    # example_cache_lookup()

    # 예시 6: 만료된 캐시 정리
    # example_cache_cleanup()

    # 예시 7: 일일 배치 처리 시뮬레이션
    # await example_daily_batch()


if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(main())
