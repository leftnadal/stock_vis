#!/usr/bin/env python
"""Market Movers 동기화 테스트 스크립트"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from serverless.services.data_sync import MarketMoversSync

if __name__ == '__main__':
    print("Market Movers 동기화 시작...")
    sync = MarketMoversSync()

    try:
        result = sync.sync_daily_movers()
        print(f"\n✅ 동기화 성공!")
        print(f"Gainers: {result['gainers']}")
        print(f"Losers: {result['losers']}")
        print(f"Actives: {result['actives']}")
        print(f"Errors: {result['errors']}")

    except Exception as e:
        print(f"\n❌ 동기화 실패: {e}")
        import traceback
        traceback.print_exc()
