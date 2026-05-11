#!/usr/bin/env python
"""
FMP API 엔드포인트 테스트 스크립트

새로운 /stable/ 엔드포인트가 정상 작동하는지 확인합니다.
"""
import os
import sys
import django

# Django 설정 초기화
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from serverless.services.fmp_client import FMPClient, FMPAPIError


def test_market_gainers():
    """상승 TOP 종목 테스트"""
    print("\n=== Testing Market Gainers ===")
    try:
        client = FMPClient()
        gainers = client.get_market_gainers()

        print(f"✅ 상승 TOP 종목 {len(gainers)}개 조회 성공")
        if gainers:
            print(f"\n예시 데이터 (첫 번째 종목):")
            first = gainers[0]
            print(f"  - Symbol: {first.get('symbol')}")
            print(f"  - Name: {first.get('name')}")
            print(f"  - Price: ${first.get('price'):.2f}")
            print(f"  - Change: {first.get('change'):.2f}")
            print(f"  - Change %: {first.get('changesPercentage'):.2f}%")
            print(f"  - Exchange: {first.get('exchange')}")
        return True
    except FMPAPIError as e:
        print(f"❌ 에러: {e}")
        return False


def test_market_losers():
    """하락 TOP 종목 테스트"""
    print("\n=== Testing Market Losers ===")
    try:
        client = FMPClient()
        losers = client.get_market_losers()

        print(f"✅ 하락 TOP 종목 {len(losers)}개 조회 성공")
        if losers:
            print(f"\n예시 데이터 (첫 번째 종목):")
            first = losers[0]
            print(f"  - Symbol: {first.get('symbol')}")
            print(f"  - Name: {first.get('name')}")
            print(f"  - Price: ${first.get('price'):.2f}")
            print(f"  - Change: {first.get('change'):.2f}")
            print(f"  - Change %: {first.get('changesPercentage'):.2f}%")
            print(f"  - Exchange: {first.get('exchange')}")
        return True
    except FMPAPIError as e:
        print(f"❌ 에러: {e}")
        return False


def test_market_actives():
    """거래량 TOP 종목 테스트"""
    print("\n=== Testing Market Actives ===")
    try:
        client = FMPClient()
        actives = client.get_market_actives()

        print(f"✅ 거래량 TOP 종목 {len(actives)}개 조회 성공")
        if actives:
            print(f"\n예시 데이터 (첫 번째 종목):")
            first = actives[0]
            print(f"  - Symbol: {first.get('symbol')}")
            print(f"  - Name: {first.get('name')}")
            print(f"  - Price: ${first.get('price'):.2f}")
            print(f"  - Change: {first.get('change'):.2f}")
            print(f"  - Change %: {first.get('changesPercentage'):.2f}%")
            print(f"  - Exchange: {first.get('exchange')}")
        return True
    except FMPAPIError as e:
        print(f"❌ 에러: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("FMP API /stable/ 엔드포인트 테스트")
    print("=" * 60)

    results = []
    results.append(("Market Gainers", test_market_gainers()))
    results.append(("Market Losers", test_market_losers()))
    results.append(("Market Actives", test_market_actives()))

    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")

    all_pass = all(success for _, success in results)
    print("\n" + "=" * 60)
    if all_pass:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
