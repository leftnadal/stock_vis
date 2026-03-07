#!/usr/bin/env python3
"""
Chain Sight API 접근 테스트 스크립트

Finnhub / FMP API가 무료/Starter 플랜에서 관련 종목 데이터를 제공하는지 확인
"""

import os
import time
import requests
from dotenv import load_dotenv

# .env 로드
load_dotenv()

FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
FMP_API_KEY = os.getenv('FMP_API_KEY')

# 컬러 출력
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def test_api(name: str, url: str, description: str = ""):
    """API 엔드포인트 테스트"""
    print(f"\n{'='*60}")
    print(f"[{name}]")
    if description:
        print(f"  {description}")
    print(f"  URL: {url[:80]}...")
    print('-'*60)

    try:
        response = requests.get(url, timeout=10)
        status = response.status_code

        if status == 200:
            print(f"  {GREEN}✅ 접근 가능 (HTTP {status}){RESET}")

            try:
                data = response.json()

                # 데이터 구조 분석
                if isinstance(data, list):
                    print(f"  📊 응답 타입: Array")
                    print(f"  📊 데이터 건수: {len(data)}개")
                    if len(data) > 0:
                        first_item = data[0]
                        if isinstance(first_item, dict):
                            print(f"  📊 첫 번째 항목 키: {list(first_item.keys())[:5]}")
                        else:
                            print(f"  📊 첫 번째 항목: {first_item}")
                elif isinstance(data, dict):
                    print(f"  📊 응답 타입: Object")
                    print(f"  📊 최상위 키: {list(data.keys())[:5]}")
                    # 배열 필드 찾기
                    for key, value in data.items():
                        if isinstance(value, list):
                            print(f"  📊 '{key}' 배열 길이: {len(value)}개")
                            if len(value) > 0 and isinstance(value[0], dict):
                                print(f"      첫 항목 키: {list(value[0].keys())[:5]}")
                            break

                # 응답 미리보기
                text = str(data)[:200]
                print(f"  📝 응답 미리보기: {text}...")

            except Exception as e:
                print(f"  📝 응답 텍스트: {response.text[:200]}...")

        elif status in [401, 403]:
            print(f"  {RED}❌ 접근 불가 (HTTP {status}) - 유료 전용 또는 인증 실패{RESET}")
            try:
                error_msg = response.json()
                print(f"  📝 에러 메시지: {error_msg}")
            except:
                print(f"  📝 응답: {response.text[:200]}")

        elif status == 429:
            print(f"  {YELLOW}⚠️ Rate Limit 초과 (HTTP {status}){RESET}")
            print(f"  📝 응답: {response.text[:200]}")

        else:
            print(f"  {YELLOW}⚠️ 예상치 못한 응답 (HTTP {status}){RESET}")
            print(f"  📝 응답: {response.text[:200]}")

    except requests.exceptions.Timeout:
        print(f"  {RED}❌ 타임아웃{RESET}")
    except requests.exceptions.RequestException as e:
        print(f"  {RED}❌ 요청 실패: {e}{RESET}")

    time.sleep(1)  # Rate limit 방지


def main():
    print("="*60)
    print("  Chain Sight API 접근 테스트")
    print("="*60)

    # API 키 확인
    print(f"\n📌 API 키 상태:")
    print(f"   FINNHUB_API_KEY: {'✅ 설정됨' if FINNHUB_API_KEY else '❌ 없음'}")
    print(f"   FMP_API_KEY: {'✅ 설정됨' if FMP_API_KEY else '❌ 없음'}")

    if not FINNHUB_API_KEY and not FMP_API_KEY:
        print(f"\n{RED}❌ API 키가 없습니다. .env 파일을 확인하세요.{RESET}")
        return

    # ========================================
    # 1. Finnhub Peers API (무료)
    # ========================================
    if FINNHUB_API_KEY:
        test_api(
            "Finnhub Peers API - AAPL",
            f"https://finnhub.io/api/v1/stock/peers?symbol=AAPL&token={FINNHUB_API_KEY}",
            "동일 산업군의 피어 종목 (무료 예상)"
        )

        test_api(
            "Finnhub Peers API - NVDA",
            f"https://finnhub.io/api/v1/stock/peers?symbol=NVDA&token={FINNHUB_API_KEY}",
            "NVDA 피어 종목 확인"
        )

        # ========================================
        # 2. Finnhub Supply Chain API (유료?)
        # ========================================
        test_api(
            "Finnhub Supply Chain API - AAPL",
            f"https://finnhub.io/api/v1/stock/supply-chain?symbol=AAPL&token={FINNHUB_API_KEY}",
            "공급망 관계 종목 (유료일 수 있음)"
        )
    else:
        print(f"\n{YELLOW}⏭️ Finnhub 테스트 스킵 (API 키 없음){RESET}")

    # ========================================
    # 3. FMP Stock Peers API
    # ========================================
    if FMP_API_KEY:
        test_api(
            "FMP Stock Peers API",
            f"https://financialmodelingprep.com/stable/stock-peers?symbol=AAPL&apikey={FMP_API_KEY}",
            "피어 종목 조회"
        )

        # ========================================
        # 4. FMP ETF Holdings API
        # ========================================
        test_api(
            "FMP ETF Holder API",
            f"https://financialmodelingprep.com/stable/etf-holder?symbol=SPY&apikey={FMP_API_KEY}",
            "SPY ETF 보유 종목"
        )

        # ========================================
        # 추가: FMP에서 관련 종목 찾기에 유용할 수 있는 API들
        # ========================================
        test_api(
            "FMP Company Profile (stable)",
            f"https://financialmodelingprep.com/stable/profile?symbol=AAPL&apikey={FMP_API_KEY}",
            "회사 프로필 (섹터/산업 정보)"
        )

        test_api(
            "FMP Stock Screener - Same Sector",
            f"https://financialmodelingprep.com/stable/company-screener?sector=Technology&marketCapMoreThan=100000000000&limit=10&apikey={FMP_API_KEY}",
            "섹터 기반 스크리닝 (Chain Sight 대안)"
        )
    else:
        print(f"\n{YELLOW}⏭️ FMP 테스트 스킵 (API 키 없음){RESET}")

    # ========================================
    # 결과 요약
    # ========================================
    print("\n" + "="*60)
    print("  테스트 완료")
    print("="*60)
    print("""
📋 결과 해석 가이드:
   ✅ 접근 가능: 무료/Starter 플랜에서 사용 가능
   ❌ 접근 불가: 상위 플랜 필요 (유료)
   ⚠️ Rate Limit: 잠시 후 재시도 필요
""")


if __name__ == "__main__":
    main()
