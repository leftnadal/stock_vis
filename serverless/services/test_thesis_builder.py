"""
Investment Thesis Builder 테스트

USAGE:
    python serverless/services/test_thesis_builder.py
"""

import os
import sys
import django

# Django 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from serverless.services.thesis_builder import ThesisBuilder, create_fallback_thesis
from serverless.models import InvestmentThesis


def test_thesis_builder():
    """ThesisBuilder 테스트"""
    print("=" * 60)
    print("Investment Thesis Builder 테스트")
    print("=" * 60)
    print()

    # 테스트 데이터
    stocks = [
        {
            'symbol': 'AAPL',
            'company_name': 'Apple Inc.',
            'price': 150.25,
            'change_percent': 2.3,
            'sector': 'Technology',
            'pe_ratio': 28.5,
            'roe': 147.0,
            'market_cap': 3000000000000,
        },
        {
            'symbol': 'MSFT',
            'company_name': 'Microsoft Corporation',
            'price': 380.50,
            'change_percent': 1.8,
            'sector': 'Technology',
            'pe_ratio': 35.2,
            'roe': 38.0,
            'market_cap': 2800000000000,
        },
        {
            'symbol': 'GOOGL',
            'company_name': 'Alphabet Inc.',
            'price': 140.75,
            'change_percent': 3.1,
            'sector': 'Technology',
            'pe_ratio': 22.1,
            'roe': 28.5,
            'market_cap': 1800000000000,
        },
    ]

    filters = {
        'pe_max': 40,
        'roe_min': 20,
        'sector': 'Technology',
        'market_cap_min': 1000000000000,
    }

    user_notes = "AI 및 클라우드 관련 기술주에 집중"

    print(f"종목 수: {len(stocks)}")
    print(f"필터 조건: {filters}")
    print(f"사용자 메모: {user_notes}")
    print()

    try:
        # ThesisBuilder 생성
        print("ThesisBuilder 초기화 중...")
        builder = ThesisBuilder(language='ko')
        print("✅ ThesisBuilder 초기화 완료")
        print()

        # 비용 추정
        cost_estimate = builder.estimate_cost(
            num_stocks=len(stocks),
            num_filters=len(filters)
        )
        print("비용 추정:")
        print(f"  - 입력 토큰: {cost_estimate['input_tokens']:,}")
        print(f"  - 출력 토큰: {cost_estimate['output_tokens']:,}")
        print(f"  - 총 토큰: {cost_estimate['total_tokens']:,}")
        print(f"  - 예상 비용: ${cost_estimate['total_cost_usd']:.6f}")
        print()

        # 테제 생성
        print("투자 테제 생성 중...")
        thesis = builder.build_thesis(
            stocks=stocks,
            filters=filters,
            user=None,  # 비인증 사용자
            user_notes=user_notes,
            preset_ids=[1, 2]
        )
        print("✅ 투자 테제 생성 완료")
        print()

        # 결과 출력
        print("=" * 60)
        print("생성된 투자 테제")
        print("=" * 60)
        print(f"ID: {thesis.id}")
        print(f"제목: {thesis.title}")
        print(f"요약: {thesis.summary}")
        print()
        print(f"핵심 지표 ({len(thesis.key_metrics)}개):")
        for idx, metric in enumerate(thesis.key_metrics, 1):
            print(f"  {idx}. {metric}")
        print()
        print(f"추천 종목 ({len(thesis.top_picks)}개): {', '.join(thesis.top_picks)}")
        print()
        print(f"리스크 ({len(thesis.risks)}개):")
        for idx, risk in enumerate(thesis.risks, 1):
            print(f"  {idx}. {risk}")
        print()
        print(f"투자 근거:")
        print(f"  {thesis.rationale}")
        print()
        print(f"LLM 모델: {thesis.llm_model}")
        print(f"생성 시간: {thesis.generation_time_ms}ms")
        print(f"공유 코드: {thesis.share_code}")
        print(f"생성 일시: {thesis.created_at}")
        print()

        # 데이터베이스 저장 확인
        saved_thesis = InvestmentThesis.objects.get(id=thesis.id)
        print(f"✅ 데이터베이스 저장 확인: ID={saved_thesis.id}")
        print()

        return thesis

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_fallback_thesis():
    """폴백 테제 생성 테스트"""
    print("=" * 60)
    print("폴백 테제 생성 테스트")
    print("=" * 60)
    print()

    stocks = [
        {
            'symbol': 'NVDA',
            'company_name': 'NVIDIA Corporation',
            'price': 500.0,
            'change_percent': 5.0,
            'sector': 'Technology',
        },
        {
            'symbol': 'AMD',
            'company_name': 'Advanced Micro Devices',
            'price': 150.0,
            'change_percent': 3.0,
            'sector': 'Technology',
        },
    ]

    filters = {
        'sector': 'Technology',
        'change_percent_min': 2.0,
    }

    try:
        print("폴백 테제 생성 중...")
        fallback = create_fallback_thesis(
            stocks=stocks,
            filters=filters,
            user=None,
            preset_ids=[]
        )
        print("✅ 폴백 테제 생성 완료")
        print()

        print(f"ID: {fallback.id}")
        print(f"제목: {fallback.title}")
        print(f"요약: {fallback.summary}")
        print(f"LLM 모델: {fallback.llm_model}")
        print(f"공유 코드: {fallback.share_code}")
        print()

        return fallback

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # 테스트 실행
    thesis = test_thesis_builder()

    print()
    print()

    fallback = test_fallback_thesis()

    print()
    print("=" * 60)
    print("테스트 완료")
    print("=" * 60)

    # 정리 (테스트 데이터 삭제)
    if thesis:
        print(f"테제 ID={thesis.id} 삭제 중...")
        thesis.delete()
        print("✅ 삭제 완료")

    if fallback:
        print(f"폴백 테제 ID={fallback.id} 삭제 중...")
        fallback.delete()
        print("✅ 삭제 완료")
