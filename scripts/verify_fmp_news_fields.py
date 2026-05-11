"""
FMP News API 응답 필드 검증 - 구현 전 실행

사용법:
    python scripts/verify_fmp_news_fields.py

FMP stable API의 뉴스 엔드포인트 응답 필드명을 확인합니다.
"""
import os
import sys
import json
import requests

# Django 설정 로드 (env에서 API 키 가져오기)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

FMP_API_KEY = os.environ.get('FMP_API_KEY')
BASE = "https://financialmodelingprep.com"


def verify_fmp_news():
    """FMP 뉴스 API 3개 엔드포인트 필드 검증"""
    if not FMP_API_KEY:
        print("ERROR: FMP_API_KEY not set in environment")
        return

    endpoints = {
        'stock-news': f"{BASE}/stable/stock-news?symbol=AAPL&limit=1&apikey={FMP_API_KEY}",
        'general-news': f"{BASE}/stable/general-news?limit=1&apikey={FMP_API_KEY}",
        'press-releases': f"{BASE}/stable/press-releases?symbol=AAPL&limit=1&apikey={FMP_API_KEY}",
    }

    for name, url in endpoints.items():
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and data:
                print(f"Keys: {list(data[0].keys())}")
                print(json.dumps(data[0], indent=2, default=str)[:800])
            elif isinstance(data, dict) and 'Error Message' in data:
                print(f"API Error: {data['Error Message']}")
            else:
                print(f"Unexpected response type: {type(data)}")
                print(json.dumps(data, indent=2, default=str)[:500])
        except Exception as e:
            print(f"Request failed: {e}")


if __name__ == '__main__':
    print("FMP News API Field Verification")
    print("=" * 60)
    verify_fmp_news()
    print("\n\nDone! Use the field names above to implement providers.")
