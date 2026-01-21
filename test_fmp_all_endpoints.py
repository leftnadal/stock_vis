#!/usr/bin/env python
"""
FMP API 전체 엔드포인트 테스트

모든 엔드포인트가 정상 작동하는지 확인합니다.
"""
import os
import sys
import django

# Django 설정 초기화
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from serverless.services.fmp_client import FMPClient, FMPAPIError


def test_quote():
    """실시간 시세 테스트"""
    print("\n=== Testing Quote (AAPL) ===")
    try:
        client = FMPClient()
        quote = client.get_quote('AAPL')

        print(f"✅ Quote 조회 성공")
        print(f"  - Symbol: {quote.get('symbol')}")
        print(f"  - Price: ${quote.get('price'):.2f}")
        print(f"  - Open: ${quote.get('open'):.2f}")
        print(f"  - High: ${quote.get('dayHigh'):.2f}")
        print(f"  - Low: ${quote.get('dayLow'):.2f}")
        print(f"  - Volume: {quote.get('volume'):,}")
        return True
    except FMPAPIError as e:
        print(f"❌ 에러: {e}")
        return False


def test_historical():
    """히스토리 OHLCV 테스트"""
    print("\n=== Testing Historical OHLCV (AAPL, 20 days) ===")
    try:
        client = FMPClient()
        historical = client.get_historical_ohlcv('AAPL', days=20)

        print(f"✅ Historical 조회 성공 ({len(historical)}일)")
        if historical:
            first = historical[0]
            print(f"  - 최신 날짜: {first.get('date')}")
            # 응답 형식 확인을 위해 모든 키 출력
            print(f"  - 전체 필드: {list(first.keys())}")
            # 필드가 있으면 출력
            if first.get('open'):
                print(f"  - Open: ${first.get('open'):.2f}")
                print(f"  - High: ${first.get('high'):.2f}")
                print(f"  - Low: ${first.get('low'):.2f}")
                print(f"  - Close: ${first.get('close'):.2f}")
                print(f"  - Volume: {first.get('volume'):,}")
        return True
    except FMPAPIError as e:
        print(f"❌ 에러: {e}")
        return False


def test_profile():
    """기업 프로필 테스트"""
    print("\n=== Testing Company Profile (AAPL) ===")
    try:
        client = FMPClient()
        profile = client.get_company_profile('AAPL')

        print(f"✅ Profile 조회 성공")
        print(f"  - Symbol: {profile.get('symbol')}")
        print(f"  - Company: {profile.get('companyName')}")
        print(f"  - Sector: {profile.get('sector')}")
        print(f"  - Industry: {profile.get('industry')}")
        print(f"  - Exchange: {profile.get('exchangeShortName')}")
        return True
    except FMPAPIError as e:
        print(f"❌ 에러: {e}")
        return False


def test_market_gainers():
    """상승 TOP 종목 테스트"""
    print("\n=== Testing Market Gainers ===")
    try:
        client = FMPClient()
        gainers = client.get_market_gainers()

        print(f"✅ Market Gainers 조회 성공 ({len(gainers)}개)")
        if gainers:
            first = gainers[0]
            print(f"  - Symbol: {first.get('symbol')}")
            print(f"  - Name: {first.get('name')}")
            print(f"  - Change %: {first.get('changesPercentage'):.2f}%")
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

        print(f"✅ Market Losers 조회 성공 ({len(losers)}개)")
        if losers:
            first = losers[0]
            print(f"  - Symbol: {first.get('symbol')}")
            print(f"  - Name: {first.get('name')}")
            print(f"  - Change %: {first.get('changesPercentage'):.2f}%")
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

        print(f"✅ Market Actives 조회 성공 ({len(actives)}개)")
        if actives:
            first = actives[0]
            print(f"  - Symbol: {first.get('symbol')}")
            print(f"  - Name: {first.get('name')}")
            # volume이 None일 수 있으므로 체크
            if first.get('volume'):
                print(f"  - Volume: {first.get('volume'):,}")
            else:
                print(f"  - Change %: {first.get('changesPercentage'):.2f}%")
        return True
    except FMPAPIError as e:
        print(f"❌ 에러: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("FMP API 전체 엔드포인트 테스트")
    print("=" * 60)

    results = []

    # /api/v3/* 엔드포인트 테스트
    print("\n【 /api/v3/* 엔드포인트 테스트 】")
    results.append(("Quote", test_quote()))
    results.append(("Historical OHLCV", test_historical()))
    results.append(("Company Profile", test_profile()))

    # /stable/* 엔드포인트 테스트
    print("\n【 /stable/* 엔드포인트 테스트 】")
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
        print("✅ 모든 엔드포인트 정상 작동!")
    else:
        print("❌ 일부 엔드포인트 실패 - Legacy 엔드포인트 확인 필요")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
