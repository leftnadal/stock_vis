"""
거시경제 데이터 Celery 태스크

스케줄링된 데이터 업데이트 태스크
"""
import logging
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def update_economic_indicators(self):
    """
    경제 지표 데이터 업데이트 (FRED API)

    실행 주기: 매시간 (FRED 데이터는 일간/월간 업데이트)
    """
    from .services import MacroEconomicService

    try:
        service = MacroEconomicService()

        # 주요 지표 동기화
        indicators = [
            'FEDFUNDS',   # 기준금리
            'DGS2',       # 2년물 국채
            'DGS10',      # 10년물 국채
            'T10Y2Y',     # 장단기 금리차
            'VIXCLS',     # VIX
            'UNRATE',     # 실업률
            'CPIAUCSL',   # CPI
        ]

        total_saved = 0
        for code in indicators:
            try:
                saved = service.sync_indicator_values(code)
                total_saved += saved
                logger.info(f"Synced {code}: {saved} new values")
            except Exception as e:
                logger.error(f"Failed to sync {code}: {e}")
                continue

        # 캐시 무효화
        cache.delete_pattern('macro:*')

        logger.info(f"Economic indicators update complete. Total new values: {total_saved}")
        return {'status': 'success', 'total_saved': total_saved}

    except Exception as e:
        logger.error(f"update_economic_indicators failed: {e}")
        self.retry(countdown=60 * 5)  # 5분 후 재시도


@shared_task(bind=True, max_retries=3)
def update_market_indices(self):
    """
    시장 지수 데이터 업데이트 (FMP API)

    실행 주기: 시장 운영 시간 중 5분마다
    """
    from .services import MacroEconomicService
    from .models import MarketIndex, MarketIndexPrice
    from django.utils import timezone
    from decimal import Decimal

    try:
        service = MacroEconomicService()

        # 시장 지수 가져오기
        indices_data = service.fmp.get_market_indices()

        saved_count = 0
        today = timezone.now().date()

        for symbol, data in indices_data.items():
            try:
                # MarketIndex 생성/조회
                index, _ = MarketIndex.objects.get_or_create(
                    symbol=symbol,
                    defaults={
                        'name': data.get('name', symbol),
                        'category': 'us_equity' if symbol.startswith('^') else 'other',
                    }
                )

                # 가격 저장
                MarketIndexPrice.objects.update_or_create(
                    index=index,
                    date=today,
                    defaults={
                        'close': Decimal(str(data.get('price', 0))),
                        'change': Decimal(str(data.get('change', 0))) if data.get('change') else None,
                        'change_percent': Decimal(str(data.get('change_percent', 0))) if data.get('change_percent') else None,
                    }
                )
                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save index {symbol}: {e}")
                continue

        # 캐시 무효화
        cache.delete_pattern('macro:global_markets*')

        logger.info(f"Market indices update complete. Saved: {saved_count}")
        return {'status': 'success', 'saved': saved_count}

    except Exception as e:
        logger.error(f"update_market_indices failed: {e}")
        self.retry(countdown=60)  # 1분 후 재시도


@shared_task(bind=True)
def update_economic_calendar(self):
    """
    경제 캘린더 업데이트 (FMP API)

    실행 주기: 매일 새벽 1회
    """
    from .services import MacroEconomicService
    from .models import EconomicEvent
    from datetime import date, timedelta
    import hashlib

    try:
        service = MacroEconomicService()

        # 향후 14일간의 이벤트 가져오기
        from_date = date.today()
        to_date = from_date + timedelta(days=14)

        events = service.fmp.get_economic_calendar(from_date, to_date)

        saved_count = 0
        for event_data in events:
            try:
                # 이벤트 ID 생성 (고유성 보장)
                event_str = f"{event_data.get('date')}_{event_data.get('event')}_{event_data.get('country')}"
                event_id = hashlib.md5(event_str.encode()).hexdigest()[:32]

                # 중요도 매핑
                impact = event_data.get('impact', 'Low')
                importance = 'critical' if impact == 'High' else 'high' if impact == 'Medium' else 'medium'

                # 이벤트 저장
                event_date_str = event_data.get('date', '')[:10]
                event_time_str = event_data.get('date', '')[11:16] if len(event_data.get('date', '')) > 10 else None

                from datetime import datetime
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date() if event_date_str else None
                event_time = datetime.strptime(event_time_str, '%H:%M').time() if event_time_str else None

                if event_date:
                    EconomicEvent.objects.update_or_create(
                        event_id=event_id,
                        defaults={
                            'title': event_data.get('event', ''),
                            'event_date': event_date,
                            'event_time': event_time,
                            'importance': importance,
                            'country': event_data.get('country', 'US'),
                            'previous_value': str(event_data.get('previous', '')) if event_data.get('previous') else '',
                            'forecast_value': str(event_data.get('estimate', '')) if event_data.get('estimate') else '',
                            'actual_value': str(event_data.get('actual', '')) if event_data.get('actual') else '',
                        }
                    )
                    saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save event: {e}")
                continue

        # 캐시 무효화
        cache.delete_pattern('macro:economic_calendar*')

        logger.info(f"Economic calendar update complete. Saved: {saved_count}")
        return {'status': 'success', 'saved': saved_count}

    except Exception as e:
        logger.error(f"update_economic_calendar failed: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def refresh_market_pulse_cache():
    """
    Market Pulse 전체 대시보드 캐시 갱신

    실행 주기: 시장 운영 시간 중 1분마다
    """
    from .services import MacroEconomicService

    try:
        # 기존 캐시 삭제
        cache.delete('macro:market_pulse_full')

        # 새 데이터로 캐시 갱신
        service = MacroEconomicService()
        service.get_market_pulse_dashboard()

        logger.info("Market pulse cache refreshed")
        return {'status': 'success'}

    except Exception as e:
        logger.error(f"refresh_market_pulse_cache failed: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_data():
    """
    오래된 데이터 정리

    실행 주기: 매주 일요일
    """
    from .models import IndicatorValue, MarketIndexPrice, EconomicEvent
    from datetime import date, timedelta

    try:
        # 1년 이상 된 일간 데이터 삭제 (최근 데이터만 유지)
        cutoff_date = date.today() - timedelta(days=365)

        deleted_indicators = IndicatorValue.objects.filter(date__lt=cutoff_date).delete()
        deleted_prices = MarketIndexPrice.objects.filter(date__lt=cutoff_date).delete()

        # 지난 이벤트 삭제 (30일 이전)
        event_cutoff = date.today() - timedelta(days=30)
        deleted_events = EconomicEvent.objects.filter(event_date__lt=event_cutoff).delete()

        logger.info(f"Cleanup complete: indicators={deleted_indicators[0]}, prices={deleted_prices[0]}, events={deleted_events[0]}")
        return {
            'status': 'success',
            'deleted_indicators': deleted_indicators[0],
            'deleted_prices': deleted_prices[0],
            'deleted_events': deleted_events[0],
        }

    except Exception as e:
        logger.error(f"cleanup_old_data failed: {e}")
        return {'status': 'error', 'error': str(e)}
