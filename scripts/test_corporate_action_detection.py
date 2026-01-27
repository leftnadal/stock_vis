"""
Corporate Action 감지 시스템 통합 테스트

실제 yfinance 데이터를 사용하여 Corporate Action 감지를 테스트합니다.
"""
import os
import django
import sys
from datetime import date

# Django 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from serverless.services.corporate_action_service import CorporateActionService


def test_reverse_split():
    """역분할 감지 테스트 (GRI Bio 사례)"""
    print("\n=== 역분할 감지 테스트 ===")

    service = CorporateActionService()

    # GRI Bio - 1:28 역분할 (2024-01-12)
    symbol = 'GRI'
    target_date = date(2024, 1, 15)  # 역분할 후 며칠 뒤

    print(f"종목: {symbol}")
    print(f"대상 날짜: {target_date}")
    print(f"체크 필요: {service.should_check(2772.0)} (변동률: +2772%)")

    result = service.check_actions(symbol, target_date)

    if result:
        print(f"\n✅ Corporate Action 감지:")
        print(f"  - 날짜: {result['date']}")
        print(f"  - 타입: {result['action_type']}")
        print(f"  - 비율: {result['ratio']}")
        print(f"  - 표시: {result['display_text']}")
    else:
        print("\n❌ Corporate Action 없음")


def test_forward_split():
    """정분할 감지 테스트"""
    print("\n=== 정분할 감지 테스트 ===")

    service = CorporateActionService()

    # AAPL - 4:1 분할 (2020-08-31)
    symbol = 'AAPL'
    target_date = date(2020, 9, 1)

    print(f"종목: {symbol}")
    print(f"대상 날짜: {target_date}")

    result = service.check_actions(symbol, target_date)

    if result:
        print(f"\n✅ Corporate Action 감지:")
        print(f"  - 날짜: {result['date']}")
        print(f"  - 타입: {result['action_type']}")
        print(f"  - 비율: {result['ratio']}")
        print(f"  - 표시: {result['display_text']}")
    else:
        print("\n❌ Corporate Action 없음")


def test_no_action():
    """정상 종목 테스트 (Corporate Action 없음)"""
    print("\n=== 정상 종목 테스트 ===")

    service = CorporateActionService()

    symbol = 'MSFT'
    target_date = date(2026, 1, 20)

    print(f"종목: {symbol}")
    print(f"대상 날짜: {target_date}")
    print(f"체크 필요: {service.should_check(3.5)} (변동률: +3.5%)")

    result = service.check_actions(symbol, target_date)

    if result:
        print(f"\n⚠️ Corporate Action 감지 (예상 밖):")
        print(f"  - 날짜: {result['date']}")
        print(f"  - 타입: {result['action_type']}")
        print(f"  - 표시: {result['display_text']}")
    else:
        print("\n✅ Corporate Action 없음 (정상)")


def test_save_to_db():
    """DB 저장 테스트"""
    print("\n=== DB 저장 테스트 ===")

    service = CorporateActionService()

    # 테스트 데이터
    symbol = 'TEST'
    action_data = {
        'date': date(2026, 1, 20),
        'action_type': 'reverse_split',
        'ratio': 28.0,
        'dividend_amount': None,
        'display_text': '1:28 역분할',
    }

    print(f"종목: {symbol}")
    print(f"데이터: {action_data}")

    try:
        saved = service.save_action(symbol, action_data)
        print(f"\n✅ DB 저장 성공:")
        print(f"  - ID: {saved.id}")
        print(f"  - Symbol: {saved.symbol}")
        print(f"  - Display: {saved.display_text}")
    except Exception as e:
        print(f"\n❌ DB 저장 실패: {e}")


if __name__ == '__main__':
    print("Corporate Action 감지 시스템 통합 테스트")
    print("=" * 50)

    test_reverse_split()
    test_forward_split()
    test_no_action()
    test_save_to_db()

    print("\n" + "=" * 50)
    print("테스트 완료")
