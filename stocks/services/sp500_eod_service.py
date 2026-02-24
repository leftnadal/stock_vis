"""
S&P 500 EOD(End of Day) 가격 동기화 서비스

매일 장 마감 후 S&P 500 전종목의 종가를 DailyPrice에 저장합니다.
"""
import logging
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional

from django.db import transaction

from stocks.models import Stock, DailyPrice, SP500Constituent
from serverless.services.fmp_client import FMPClient, FMPAPIError

logger = logging.getLogger(__name__)

# 배치 로깅 사이즈
BATCH_LOG_SIZE = 50
# API 호출 간격 (초) - 200콜/분 안전 마진
REQUEST_DELAY = 0.3


class SP500EODService:
    """S&P 500 전종목 EOD 가격 동기화 서비스"""

    def __init__(self):
        self.fmp_client = FMPClient()

    def sync_eod_prices(self, target_date: Optional[date] = None) -> Dict:
        """
        S&P 500 전종목의 EOD 가격을 DailyPrice에 저장

        Args:
            target_date: 동기화 대상 날짜 (기본: 오늘)

        Returns:
            {
                'target_date': str,
                'total_symbols': int,
                'synced': int,
                'skipped': int,
                'errors': int,
                'stocks_created': int,
                'error_symbols': [str],
            }
        """
        if target_date is None:
            from serverless.services.admin_status_service import last_trading_day
            target_date = last_trading_day()

        logger.info(f"S&P 500 EOD 동기화 시작: {target_date}")

        # 1. 활성 심볼 목록
        active_symbols = list(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
            .order_by('symbol')
        )

        if not active_symbols:
            logger.warning("활성 S&P 500 종목이 없습니다. 먼저 sync_constituents를 실행하세요.")
            return {
                'target_date': str(target_date),
                'total_symbols': 0,
                'synced': 0,
                'skipped': 0,
                'errors': 0,
                'stocks_created': 0,
                'error_symbols': [],
            }

        # 2. 이미 저장된 종목 확인 (idempotent)
        existing = set(
            DailyPrice.objects.filter(date=target_date)
            .values_list('stock__symbol', flat=True)
        )

        stats = {
            'target_date': str(target_date),
            'total_symbols': len(active_symbols),
            'synced': 0,
            'skipped': 0,
            'errors': 0,
            'stocks_created': 0,
            'error_symbols': [],
        }

        for idx, symbol in enumerate(active_symbols, 1):
            # 이미 있으면 skip
            if symbol in existing:
                stats['skipped'] += 1
                continue

            try:
                self._sync_single_symbol(symbol, target_date, stats)
            except Exception as e:
                stats['errors'] += 1
                stats['error_symbols'].append(symbol)
                logger.error(f"[{idx}/{len(active_symbols)}] {symbol} EOD 동기화 실패: {e}")

            # 배치 로깅
            if idx % BATCH_LOG_SIZE == 0:
                logger.info(
                    f"EOD 진행: {idx}/{len(active_symbols)} "
                    f"(synced={stats['synced']}, skipped={stats['skipped']}, errors={stats['errors']})"
                )

            # Rate limiting
            time.sleep(REQUEST_DELAY)

        logger.info(
            f"S&P 500 EOD 동기화 완료: {target_date} - "
            f"synced={stats['synced']}, skipped={stats['skipped']}, "
            f"errors={stats['errors']}, stocks_created={stats['stocks_created']}"
        )
        return stats

    def _sync_single_symbol(self, symbol: str, target_date: date, stats: Dict) -> None:
        """단일 종목 EOD 동기화"""
        # Stock 레코드 확인/생성
        stock = self._ensure_stock_exists(symbol, stats)
        if not stock:
            stats['errors'] += 1
            stats['error_symbols'].append(symbol)
            return

        # FMP에서 최근 5일 데이터 가져오기
        try:
            historical = self.fmp_client.get_historical_ohlcv(symbol, days=5)
        except FMPAPIError as e:
            raise Exception(f"FMP API error for {symbol}: {e}")

        if not historical:
            logger.warning(f"{symbol}: FMP에서 가격 데이터 없음")
            stats['errors'] += 1
            stats['error_symbols'].append(symbol)
            return

        # target_date에 매칭되는 데이터 찾기
        target_str = str(target_date)
        price_data = None
        for entry in historical:
            if entry.get('date') == target_str:
                price_data = entry
                break

        # 정확한 날짜가 없으면 가장 최근 데이터 사용 (주말/공휴일 대비)
        if not price_data and historical:
            price_data = historical[0]
            logger.debug(f"{symbol}: {target_date} 데이터 없음, 최근 데이터({price_data.get('date')}) 사용")

        if not price_data:
            return

        # DailyPrice 저장
        actual_date = price_data.get('date', target_str)
        try:
            actual_date_obj = date.fromisoformat(actual_date)
        except (ValueError, TypeError):
            actual_date_obj = target_date

        with transaction.atomic():
            DailyPrice.objects.update_or_create(
                stock=stock,
                date=actual_date_obj,
                defaults={
                    'open_price': self._to_decimal(price_data.get('open', 0)),
                    'high_price': self._to_decimal(price_data.get('high', 0)),
                    'low_price': self._to_decimal(price_data.get('low', 0)),
                    'close_price': self._to_decimal(price_data.get('close', 0)),
                    'volume': int(price_data.get('volume', 0)),
                },
            )
        stats['synced'] += 1

    def _ensure_stock_exists(self, symbol: str, stats: Dict) -> Optional[Stock]:
        """Stock 레코드가 없으면 FMP 프로필로 자동 생성"""
        try:
            return Stock.objects.get(symbol=symbol.upper())
        except Stock.DoesNotExist:
            pass

        # FMP에서 프로필 가져와서 Stock 생성
        try:
            profile = self.fmp_client.get_company_profile(symbol)
        except FMPAPIError:
            logger.warning(f"{symbol}: 프로필 조회 실패, 최소 정보로 Stock 생성")
            profile = {}

        try:
            stock = Stock.objects.create(
                symbol=symbol.upper(),
                stock_name=profile.get('companyName', symbol)[:200],
                sector=profile.get('sector', '')[:100] if profile.get('sector') else None,
                industry=profile.get('industry', '')[:100] if profile.get('industry') else None,
                exchange=profile.get('exchangeShortName', '')[:50] if profile.get('exchangeShortName') else None,
                description=profile.get('description', '')[:5000] if profile.get('description') else None,
                market_capitalization=self._to_decimal(profile.get('mktCap')) if profile.get('mktCap') else None,
            )
            stats['stocks_created'] += 1
            logger.info(f"{symbol}: Stock 레코드 자동 생성")
            time.sleep(REQUEST_DELAY)  # 프로필 API 호출 후 대기
            return stock
        except Exception as e:
            logger.error(f"{symbol}: Stock 생성 실패: {e}")
            return None

    @staticmethod
    def _to_decimal(value) -> Decimal:
        """안전한 Decimal 변환"""
        if value is None:
            return Decimal('0')
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0')
