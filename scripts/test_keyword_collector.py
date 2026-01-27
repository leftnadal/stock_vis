#!/usr/bin/env python
"""
Market Movers 키워드 데이터 수집기 테스트 스크립트

Usage:
    python scripts/test_keyword_collector.py
"""
import os
import sys
import django
import logging
from datetime import date

# Django 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from serverless.services.keyword_data_collector import KeywordDataCollector


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_cache_operations():
    """Redis 캐시 작업 테스트"""
    print("\n" + "=" * 60)
    print("1. Redis 캐시 작업 테스트")
    print("=" * 60)

    collector = KeywordDataCollector()

    # 테스트 데이터
    test_date = '2026-01-07'
    test_symbol = 'AAPL'
    test_data = {
        'overview': {
            'market_cap': '2.50T',
            'pe_ratio': 28.5,
        },
        'news': [
            {
                'title': 'Apple announces new product',
                'source': 'Bloomberg',
                'sentiment': 'positive',
            }
        ],
        'indicators': {}
    }

    # 1. 캐시 저장
    print(f"\n[1-1] 캐시 저장: {test_symbol} ({test_date})")
    success = collector.set_cached_context(test_date, test_symbol, test_data)
    print(f"  결과: {'성공' if success else '실패'}")

    # 2. 캐시 조회
    print(f"\n[1-2] 캐시 조회: {test_symbol} ({test_date})")
    cached = collector.get_cached_context(test_date, test_symbol)
    print(f"  결과: {'HIT' if cached else 'MISS'}")
    if cached:
        print(f"  데이터: {cached.keys()}")

    # 3. 캐시 삭제
    print(f"\n[1-3] 캐시 삭제: {test_symbol} ({test_date})")
    success = collector.delete_cached_context(test_date, test_symbol)
    print(f"  결과: {'성공' if success else '실패'}")

    # 4. 삭제 확인
    print(f"\n[1-4] 삭제 확인: {test_symbol} ({test_date})")
    cached = collector.get_cached_context(test_date, test_symbol)
    print(f"  결과: {'HIT (삭제 실패)' if cached else 'MISS (삭제 성공)'}")


def test_batch_contexts():
    """배치 컨텍스트 조회 테스트"""
    print("\n" + "=" * 60)
    print("2. 배치 컨텍스트 조회 테스트")
    print("=" * 60)

    collector = KeywordDataCollector()

    # 테스트 데이터 준비
    test_date = '2026-01-07'
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']

    # 캐시에 데이터 저장
    print(f"\n[2-1] 캐시에 테스트 데이터 저장 ({len(test_symbols)}개)")
    for symbol in test_symbols:
        test_data = {
            'overview': {'symbol': symbol, 'market_cap': '1.0T'},
            'news': [],
            'indicators': {}
        }
        collector.set_cached_context(test_date, symbol, test_data)
    print("  완료")

    # 배치 조회
    print(f"\n[2-2] 배치 컨텍스트 조회")
    contexts = collector.get_batch_contexts(test_date, test_symbols)
    print(f"  조회된 컨텍스트: {len(contexts)}개")

    for ctx in contexts:
        symbol = ctx['overview'].get('symbol', 'Unknown')
        print(f"    - {symbol}")

    # 정리
    print(f"\n[2-3] 캐시 정리")
    for symbol in test_symbols:
        collector.delete_cached_context(test_date, symbol)
    print("  완료")


def test_token_estimation():
    """토큰 추정 테스트"""
    print("\n" + "=" * 60)
    print("3. 토큰 추정 테스트")
    print("=" * 60)

    collector = KeywordDataCollector()

    # 모의 컨텍스트 (20개 종목)
    contexts = []
    for i in range(20):
        contexts.append({
            'overview': {
                'symbol': f'STOCK{i}',
                'market_cap': '1.0T',
                'pe_ratio': 25.0,
                'description': 'A leading company in the technology sector...',
            },
            'news': [
                {
                    'title': 'Company announces new product',
                    'source': 'Bloomberg',
                    'sentiment': 'positive',
                }
            ],
            'indicators': {}
        })

    print(f"\n[3-1] 토큰 추정 (종목 수: {len(contexts)})")
    tokens = collector.estimate_tokens(contexts, include_prompt=True)

    print(f"  컨텍스트 토큰: {tokens['context_tokens']:,}")
    print(f"  프롬프트 토큰: {tokens['prompt_tokens']:,}")
    print(f"  입력 토큰 합계: {tokens['total_input_tokens']:,}")
    print(f"  출력 토큰 예상: {tokens['estimated_output_tokens']:,}")

    # 비용 추정
    INPUT_COST_PER_1M = 0.30
    OUTPUT_COST_PER_1M = 1.20

    input_cost = (tokens['total_input_tokens'] / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (tokens['estimated_output_tokens'] / 1_000_000) * OUTPUT_COST_PER_1M
    total_cost = input_cost + output_cost

    print(f"\n[3-2] 비용 추정 (Gemini 2.5 Flash)")
    print(f"  입력 비용: ${input_cost:.6f}")
    print(f"  출력 비용: ${output_cost:.6f}")
    print(f"  총 비용: ${total_cost:.6f}")


def test_single_collection():
    """단일 종목 수집 테스트 (캐시 모드)"""
    print("\n" + "=" * 60)
    print("4. 단일 종목 수집 테스트 (캐시 모드)")
    print("=" * 60)

    collector = KeywordDataCollector()
    test_date = date.today()
    test_symbol = 'AAPL'

    print(f"\n[4-1] 종목: {test_symbol}, 날짜: {test_date}")
    print("  주의: Alpha Vantage API 키가 필요합니다.")
    print("  캐시가 있으면 API 호출을 건너뜁니다.")

    try:
        result = collector._collect_single(test_symbol, test_date)

        print(f"\n  결과:")
        print(f"    성공: {result['success']}")
        print(f"    캐시 HIT: {result['from_cache']}")
        print(f"    소요 시간: {result['duration_ms']}ms")

        if result['success']:
            print(f"    컨텍스트 키: {result['context'].keys()}")
        else:
            print(f"    에러: {result['error']}")

    except Exception as e:
        print(f"\n  에러: {e}")
        print("  Alpha Vantage API 키가 설정되지 않았거나 Rate Limit 초과일 수 있습니다.")


def main():
    """메인 함수"""
    print("\n" + "=" * 60)
    print("Market Movers 키워드 데이터 수집기 테스트")
    print("=" * 60)

    # 1. Redis 캐시 작업 테스트
    test_cache_operations()

    # 2. 배치 컨텍스트 조회 테스트
    test_batch_contexts()

    # 3. 토큰 추정 테스트
    test_token_estimation()

    # 4. 단일 종목 수집 테스트 (선택적)
    choice = input("\n\n단일 종목 수집 테스트를 실행하시겠습니까? (y/n): ")
    if choice.lower() == 'y':
        test_single_collection()
    else:
        print("\n  스킵")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
