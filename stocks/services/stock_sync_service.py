"""
Stock Sync Service

외부 API 응답을 DB에 자동 저장하는 서비스.
- Overview 데이터 동기화
- 가격 데이터 동기화
- 동기화 상태 관리
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from ..models import Stock, DailyPrice
from .fmp_exchange_quotes import FMPExchangeQuotesService

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """동기화 결과를 담는 데이터 클래스"""
    success: bool
    source: str  # 'db', 'fmp', 'alpha_vantage'
    synced_at: Optional[datetime] = None
    error: Optional[str] = None
    data: Optional[dict] = None


class StockSyncService:
    """외부 API 응답을 DB에 자동 저장하는 서비스"""

    # 동기화 간격 설정 (데이터 타입별)
    SYNC_INTERVALS = {
        'overview': timedelta(hours=6),      # 기본 정보: 6시간
        'price': timedelta(hours=1),          # 가격 정보: 1시간
        'financial': timedelta(days=7),       # 재무제표: 7일
    }

    # 캐시 키 패턴
    SYNC_STATUS_KEY = "sync_status:{symbol}:{data_type}"

    def __init__(self):
        self.fmp_service = FMPExchangeQuotesService()

    def should_sync(self, symbol: str, data_type: str) -> bool:
        """
        동기화가 필요한지 확인.

        Args:
            symbol: 주식 심볼
            data_type: 데이터 타입 ('overview', 'price', 'financial')

        Returns:
            True if sync is needed, False otherwise
        """
        symbol = symbol.upper()
        cache_key = self.SYNC_STATUS_KEY.format(symbol=symbol, data_type=data_type)

        # 캐시에서 마지막 동기화 시간 확인
        last_sync = cache.get(cache_key)
        if last_sync is None:
            return True

        # 동기화 간격 확인
        interval = self.SYNC_INTERVALS.get(data_type, timedelta(hours=6))
        return timezone.now() - last_sync > interval

    def _mark_synced(self, symbol: str, data_type: str) -> None:
        """동기화 완료 표시"""
        symbol = symbol.upper()
        cache_key = self.SYNC_STATUS_KEY.format(symbol=symbol, data_type=data_type)
        # 동기화 간격의 2배 동안 캐시 유지
        interval = self.SYNC_INTERVALS.get(data_type, timedelta(hours=6))
        cache_ttl = int(interval.total_seconds() * 2)
        cache.set(cache_key, timezone.now(), cache_ttl)

    def get_freshness(self, symbol: str, data_type: str) -> str:
        """
        데이터 신선도 확인.

        Returns:
            'fresh': 동기화 간격 이내
            'stale': 동기화 간격 초과
            'expired': 동기화 간격의 2배 초과
        """
        symbol = symbol.upper()
        cache_key = self.SYNC_STATUS_KEY.format(symbol=symbol, data_type=data_type)

        last_sync = cache.get(cache_key)
        if last_sync is None:
            return 'expired'

        interval = self.SYNC_INTERVALS.get(data_type, timedelta(hours=6))
        elapsed = timezone.now() - last_sync

        if elapsed < interval:
            return 'fresh'
        elif elapsed < interval * 2:
            return 'stale'
        else:
            return 'expired'

    def get_sync_meta(self, symbol: str, data_type: str, source: str) -> dict:
        """
        동기화 메타데이터 생성.

        Args:
            symbol: 주식 심볼
            data_type: 데이터 타입
            source: 데이터 소스

        Returns:
            _meta 딕셔너리
        """
        symbol = symbol.upper()
        cache_key = self.SYNC_STATUS_KEY.format(symbol=symbol, data_type=data_type)
        last_sync = cache.get(cache_key)

        return {
            'source': source,
            'synced_at': last_sync.isoformat() if last_sync else None,
            'freshness': self.get_freshness(symbol, data_type),
            'can_sync': True,
        }

    @transaction.atomic
    def sync_overview(self, symbol: str, force: bool = False) -> SyncResult:
        """
        Overview 데이터 동기화 (FMP -> DB).

        Args:
            symbol: 주식 심볼
            force: 강제 동기화 여부

        Returns:
            SyncResult
        """
        symbol = symbol.upper()

        # 동기화 필요 여부 확인
        if not force and not self.should_sync(symbol, 'overview'):
            # 이미 최신 데이터
            stock = Stock.objects.filter(symbol=symbol).first()
            if stock:
                return SyncResult(
                    success=True,
                    source='db',
                    synced_at=stock.last_updated,
                    data={'symbol': symbol, 'status': 'already_fresh'}
                )

        # FMP API 호출
        quote_data = self.fmp_service.get_quote(symbol)

        if not quote_data:
            return SyncResult(
                success=False,
                source='fmp',
                error=f"FMP API에서 {symbol} 데이터를 가져올 수 없습니다."
            )

        try:
            # Stock 모델 업데이트 또는 생성
            stock, created = Stock.objects.update_or_create(
                symbol=symbol,
                defaults=self._map_fmp_to_stock(quote_data)
            )

            # 동기화 완료 표시
            self._mark_synced(symbol, 'overview')

            logger.info(f"Stock overview synced: {symbol} ({'created' if created else 'updated'})")

            return SyncResult(
                success=True,
                source='fmp',
                synced_at=timezone.now(),
                data={
                    'symbol': symbol,
                    'action': 'created' if created else 'updated',
                    'stock_name': stock.stock_name,
                }
            )

        except Exception as e:
            logger.error(f"Failed to sync overview for {symbol}: {e}")
            return SyncResult(
                success=False,
                source='fmp',
                error=str(e)
            )

    def _map_fmp_to_stock(self, fmp_data: dict) -> dict:
        """
        FMP 데이터를 Stock 모델 필드로 매핑.

        Args:
            fmp_data: FMP API 응답 데이터

        Returns:
            Stock 모델 필드 딕셔너리
        """
        def safe_decimal(value, default=0):
            """안전하게 Decimal 변환"""
            try:
                if value is None:
                    return Decimal(default)
                return Decimal(str(value))
            except (ValueError, TypeError):
                return Decimal(default)

        def safe_int(value, default=0):
            """안전하게 int 변환"""
            try:
                if value is None:
                    return default
                return int(value)
            except (ValueError, TypeError):
                return default

        # FMP Stable API 필드명 매핑
        change_pct = fmp_data.get('changePercentage') or fmp_data.get('changesPercentage', 0)

        return {
            'stock_name': fmp_data.get('name', fmp_data.get('symbol', '')),
            'exchange': fmp_data.get('exchange', ''),

            # 실시간 가격 정보
            'real_time_price': safe_decimal(fmp_data.get('price')),
            'open_price': safe_decimal(fmp_data.get('open')),
            'high_price': safe_decimal(fmp_data.get('dayHigh')),
            'low_price': safe_decimal(fmp_data.get('dayLow')),
            'previous_close': safe_decimal(fmp_data.get('previousClose')),
            'change': safe_decimal(fmp_data.get('change')),
            'change_percent': f"{change_pct:+.2f}%" if change_pct else "0.00%",
            'volume': safe_int(fmp_data.get('volume')),

            # 재무 지표
            'market_capitalization': safe_decimal(fmp_data.get('marketCap')),
            'pe_ratio': safe_decimal(fmp_data.get('pe')) if fmp_data.get('pe') else None,
            'eps': safe_decimal(fmp_data.get('eps')) if fmp_data.get('eps') else None,

            # 52주 범위
            'week_52_high': safe_decimal(fmp_data.get('yearHigh')) if fmp_data.get('yearHigh') else None,
            'week_52_low': safe_decimal(fmp_data.get('yearLow')) if fmp_data.get('yearLow') else None,

            # 평균 거래량
            'day_50_moving_average': safe_decimal(fmp_data.get('priceAvg50')) if fmp_data.get('priceAvg50') else None,
            'day_200_moving_average': safe_decimal(fmp_data.get('priceAvg200')) if fmp_data.get('priceAvg200') else None,

            # 메타 정보
            'last_api_call': timezone.now(),
        }

    @transaction.atomic
    def sync_prices(self, symbol: str, days: int = 30, force: bool = False) -> SyncResult:
        """
        가격 데이터 동기화 (FMP Historical -> DailyPrice).

        Args:
            symbol: 주식 심볼
            days: 동기화할 일수
            force: 강제 동기화 여부

        Returns:
            SyncResult
        """
        import httpx
        from django.conf import settings

        symbol = symbol.upper()

        # 동기화 필요 여부 확인
        if not force and not self.should_sync(symbol, 'price'):
            return SyncResult(
                success=True,
                source='db',
                data={'symbol': symbol, 'status': 'already_fresh'}
            )

        # Stock 객체 확인 또는 생성
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            # Overview 먼저 동기화
            overview_result = self.sync_overview(symbol, force=True)
            if not overview_result.success:
                return SyncResult(
                    success=False,
                    source='fmp',
                    error=f"Stock 정보를 먼저 동기화해야 합니다: {overview_result.error}"
                )
            stock = Stock.objects.get(symbol=symbol)

        # FMP Historical API 호출
        api_key = settings.FMP_API_KEY
        if not api_key:
            return SyncResult(
                success=False,
                source='fmp',
                error="FMP API 키가 설정되지 않았습니다."
            )

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(
                    "https://financialmodelingprep.com/stable/historical-price-eod/full",
                    params={"symbol": symbol, "apikey": api_key}
                )
                response.raise_for_status()
                fmp_data = response.json()

            if not isinstance(fmp_data, list) or len(fmp_data) == 0:
                return SyncResult(
                    success=False,
                    source='fmp',
                    error=f"{symbol}의 히스토리 데이터를 찾을 수 없습니다."
                )

            # 지정된 일수만큼 필터링
            cutoff_date = (timezone.now() - timedelta(days=days)).date()

            saved_count = 0
            for item in fmp_data:
                try:
                    item_date = datetime.strptime(item['date'], '%Y-%m-%d').date()
                    if item_date < cutoff_date:
                        continue

                    # DailyPrice 업데이트 또는 생성
                    DailyPrice.objects.update_or_create(
                        stock=stock,
                        date=item_date,
                        defaults={
                            'open_price': Decimal(str(item.get('open', 0))),
                            'high_price': Decimal(str(item.get('high', 0))),
                            'low_price': Decimal(str(item.get('low', 0))),
                            'close_price': Decimal(str(item.get('close', 0))),
                            'volume': int(item.get('volume', 0)),
                        }
                    )
                    saved_count += 1
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to save price for {symbol} on {item.get('date')}: {e}")
                    continue

            # 동기화 완료 표시
            self._mark_synced(symbol, 'price')

            logger.info(f"Price data synced for {symbol}: {saved_count} records")

            return SyncResult(
                success=True,
                source='fmp',
                synced_at=timezone.now(),
                data={
                    'symbol': symbol,
                    'records_saved': saved_count,
                    'days': days,
                }
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP Historical API HTTP error for {symbol}: {e.response.status_code}")
            return SyncResult(
                success=False,
                source='fmp',
                error=f"FMP API 오류: {e.response.status_code}"
            )
        except httpx.TimeoutException:
            logger.error(f"FMP Historical API timeout for {symbol}")
            return SyncResult(
                success=False,
                source='fmp',
                error="FMP API 타임아웃"
            )
        except Exception as e:
            logger.error(f"Failed to sync prices for {symbol}: {e}")
            return SyncResult(
                success=False,
                source='fmp',
                error=str(e)
            )

    def sync_all(self, symbol: str, force: bool = False) -> dict:
        """
        모든 데이터 타입 동기화.

        Args:
            symbol: 주식 심볼
            force: 강제 동기화 여부

        Returns:
            각 데이터 타입별 SyncResult 딕셔너리
        """
        symbol = symbol.upper()

        results = {
            'overview': self.sync_overview(symbol, force),
            'price': self.sync_prices(symbol, force=force),
        }

        # 전체 상태 결정
        all_success = all(r.success for r in results.values())
        partial_success = any(r.success for r in results.values())

        return {
            'symbol': symbol,
            'status': 'success' if all_success else ('partial' if partial_success else 'failed'),
            'synced': {
                key: {
                    'success': result.success,
                    'source': result.source,
                    'error': result.error,
                }
                for key, result in results.items()
            },
            'next_sync_available': (timezone.now() + timedelta(minutes=5)).isoformat(),
        }
