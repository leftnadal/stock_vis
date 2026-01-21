"""
Market Movers 데이터 동기화 서비스

FMP API로부터 Gainers/Losers/Actives를 가져와서
지표를 계산하고 PostgreSQL에 저장합니다.
"""
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from serverless.models import MarketMover
from serverless.services.fmp_client import FMPClient, FMPAPIError
from serverless.services.indicators import IndicatorCalculator


logger = logging.getLogger(__name__)


# 섹터-ETF 매핑 (Phase 2)
SECTOR_ETF_MAP = {
    'Technology': 'XLK',
    'Financial Services': 'XLF',
    'Healthcare': 'XLV',
    'Consumer Cyclical': 'XLY',
    'Industrials': 'XLI',
    'Energy': 'XLE',
    'Utilities': 'XLU',
    'Consumer Defensive': 'XLP',
    'Real Estate': 'XLRE',
    'Basic Materials': 'XLB',
    'Communication Services': 'XLC',
}


class MarketMoversSync:
    """
    Market Movers 일일 동기화 서비스

    Usage:
        sync = MarketMoversSync()
        result = sync.sync_daily_movers()
        # {'gainers': 20, 'losers': 20, 'actives': 20}
    """

    def __init__(self, api_key: Optional[str] = None):
        self.fmp = FMPClient(api_key=api_key)
        self.calc = IndicatorCalculator()

    @transaction.atomic
    def sync_daily_movers(self, target_date=None) -> Dict[str, int]:
        """
        일일 Market Movers 동기화

        Args:
            target_date: 대상 날짜 (기본값: 오늘)

        Returns:
            {'gainers': 20, 'losers': 20, 'actives': 20}

        Raises:
            FMPAPIError: FMP API 호출 실패 시
        """
        target_date = target_date or timezone.now().date()
        logger.info(f"🔄 Market Movers 동기화 시작: {target_date}")

        results = {'gainers': 0, 'losers': 0, 'actives': 0, 'errors': 0}

        # 1. FMP API에서 3가지 타입 데이터 가져오기
        try:
            movers_data = {
                'gainers': self.fmp.get_market_gainers(),
                'losers': self.fmp.get_market_losers(),
                'actives': self.fmp.get_market_actives(),
            }
        except FMPAPIError as e:
            logger.error(f"❌ FMP API 호출 실패: {e}")
            raise

        # 2. 각 타입별로 종목 처리
        for mover_type, items in movers_data.items():
            logger.info(f"  처리 중: {mover_type} ({len(items)}개 종목)")

            for rank, item in enumerate(items[:20], start=1):  # TOP 20만
                try:
                    self._process_item(target_date, mover_type, rank, item)
                    results[mover_type] += 1
                except Exception as e:
                    logger.error(
                        f"  ⚠️ 종목 처리 실패: {item.get('symbol', 'UNKNOWN')} - {e}"
                    )
                    results['errors'] += 1

        logger.info(
            f"✅ Market Movers 동기화 완료: "
            f"gainers={results['gainers']}, "
            f"losers={results['losers']}, "
            f"actives={results['actives']}, "
            f"errors={results['errors']}"
        )

        return results

    def _process_item(
        self,
        date,
        mover_type: str,
        rank: int,
        item: Dict
    ) -> None:
        """
        개별 종목 처리

        Args:
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'
            rank: 순위 (1-20)
            item: FMP API 응답 데이터
        """
        symbol = item.get('symbol', '').upper()
        if not symbol:
            logger.warning(f"  ⚠️ 심볼 없음: {item}")
            return

        # 1. OHLC 데이터 가져오기
        try:
            quote = self.fmp.get_quote(symbol)
        except FMPAPIError as e:
            logger.warning(f"  ⚠️ {symbol} 시세 조회 실패: {e}")
            quote = {}

        # 2. 20일 히스토리 가져오기
        try:
            historical = self.fmp.get_historical_ohlcv(symbol, days=20)
        except FMPAPIError as e:
            logger.warning(f"  ⚠️ {symbol} 히스토리 조회 실패: {e}")
            historical = []

        # 3. 기업 프로필 (섹터/산업) 가져오기
        try:
            profile = self.fmp.get_company_profile(symbol)
            sector = profile.get('sector')
            industry = profile.get('industry')
        except FMPAPIError as e:
            logger.warning(f"  ⚠️ {symbol} 프로필 조회 실패: {e}")
            profile = {}
            sector = None
            industry = None

        # 4. Phase 1 지표 계산
        rvol = self._calculate_rvol(quote.get('volume', 0), historical)
        trend_strength = self._calculate_trend_strength(item, quote)

        # 5. Phase 2 지표 계산 (profile 재사용)
        sector_alpha = self._calculate_sector_alpha_with_profile(symbol, item, quote, profile)
        etf_sync = self._calculate_etf_sync_with_profile(symbol, historical, profile)
        volatility_pct = self._calculate_volatility_pct(historical)

        # 6. 데이터 품질 정보
        data_quality = {
            'has_20d_volume': len(historical) >= 20,
            'has_ohlc': all([
                quote.get('open'),
                quote.get('dayHigh'),
                quote.get('dayLow')
            ]),
            'historical_days': len(historical),
        }

        # 7. DB 저장
        MarketMover.objects.update_or_create(
            date=date,
            mover_type=mover_type,
            symbol=symbol,
            defaults={
                'rank': rank,
                'company_name': item.get('name', symbol),
                'price': Decimal(str(item.get('price', 0))),
                'change_percent': Decimal(str(item.get('changesPercentage', 0))),
                'volume': quote.get('volume', 0),
                # 섹터/산업 정보
                'sector': sector,
                'industry': industry,
                'open_price': self._to_decimal(quote.get('open')),
                'high': self._to_decimal(quote.get('dayHigh')),
                'low': self._to_decimal(quote.get('dayLow')),
                # Phase 1 지표
                'rvol': rvol,
                'rvol_display': self.calc.format_rvol_display(rvol),
                'trend_strength': trend_strength,
                'trend_display': self.calc.format_trend_display(trend_strength),
                # Phase 2 지표
                'sector_alpha': sector_alpha,
                'etf_sync_rate': etf_sync,
                'volatility_pct': volatility_pct,
                'data_quality': data_quality,
            }
        )

        logger.debug(
            f"  ✓ {symbol}: RVOL={self.calc.format_rvol_display(rvol)}, "
            f"Trend={self.calc.format_trend_display(trend_strength)}"
        )

    def _calculate_rvol(
        self,
        current_volume: int,
        historical: List[Dict]
    ) -> Optional[Decimal]:
        """
        RVOL 계산 헬퍼

        Args:
            current_volume: 당일 거래량
            historical: 히스토리 데이터 리스트

        Returns:
            RVOL 또는 None
        """
        if not historical or len(historical) < 10:
            return None

        volumes = [d.get('volume', 0) for d in historical if d.get('volume')]
        return self.calc.calculate_rvol(current_volume, volumes)

    def _calculate_trend_strength(
        self,
        item: Dict,
        quote: Dict
    ) -> Optional[Decimal]:
        """
        추세 강도 계산 헬퍼

        Args:
            item: FMP Movers 데이터
            quote: FMP Quote 데이터

        Returns:
            추세 강도 또는 None
        """
        # OHLC 데이터 확인
        open_price = quote.get('open') or item.get('price')
        high = quote.get('dayHigh') or item.get('price')
        low = quote.get('dayLow') or item.get('price')
        close = item.get('price')

        if not all([open_price, high, low, close]):
            return None

        return self.calc.calculate_trend_strength(
            float(open_price),
            float(high),
            float(low),
            float(close)
        )

    @staticmethod
    def _to_decimal(value) -> Optional[Decimal]:
        """숫자를 Decimal로 변환 (None 처리)"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

    # ========================================
    # Phase 2 지표 계산 헬퍼
    # ========================================

    def _calculate_sector_alpha_with_profile(
        self,
        symbol: str,
        item: Dict,
        quote: Dict,
        profile: Dict
    ) -> Optional[Decimal]:
        """
        섹터 알파 계산 헬퍼 (profile 재사용)

        Args:
            symbol: 종목 심볼
            item: FMP Movers 데이터
            quote: FMP Quote 데이터
            profile: FMP 기업 프로필 데이터

        Returns:
            섹터 알파 또는 None
        """
        try:
            sector = profile.get('sector')

            if not sector or sector not in SECTOR_ETF_MAP:
                logger.debug(f"  ⚠️ {symbol}: 섹터 정보 없음 또는 미매핑 ({sector})")
                return None

            # 섹터 ETF 심볼 가져오기
            etf_symbol = SECTOR_ETF_MAP[sector]

            # 섹터 ETF 당일 수익률 계산
            etf_quote = self.fmp.get_quote(etf_symbol)
            etf_prev_close = etf_quote.get('previousClose')
            etf_price = etf_quote.get('price')

            if not etf_prev_close or not etf_price:
                logger.debug(f"  ⚠️ {symbol}: ETF {etf_symbol} 가격 데이터 없음")
                return None

            etf_return = ((etf_price - etf_prev_close) / etf_prev_close) * 100

            # 종목 당일 수익률 (이미 item.changesPercentage에 있음)
            stock_return = float(item.get('changesPercentage', 0))

            # 알파 계산
            return self.calc.calculate_sector_alpha(stock_return, etf_return)

        except Exception as e:
            logger.debug(f"  ⚠️ {symbol} 섹터 알파 계산 실패: {e}")
            return None

    def _calculate_etf_sync_with_profile(
        self,
        symbol: str,
        historical: List[Dict],
        profile: Dict
    ) -> Optional[Decimal]:
        """
        ETF 동행률 계산 헬퍼 (profile 재사용)

        Args:
            symbol: 종목 심볼
            historical: 종목 히스토리 데이터
            profile: FMP 기업 프로필 데이터

        Returns:
            ETF 동행률 또는 None
        """
        if not historical or len(historical) < 10:
            return None

        try:
            sector = profile.get('sector')

            if not sector or sector not in SECTOR_ETF_MAP:
                return None

            # 섹터 ETF 심볼 가져오기
            etf_symbol = SECTOR_ETF_MAP[sector]

            # ETF 히스토리 조회 (같은 기간)
            etf_historical = self.fmp.get_historical_ohlcv(etf_symbol, days=len(historical))

            if not etf_historical or len(etf_historical) < 10:
                logger.debug(f"  ⚠️ {symbol}: ETF {etf_symbol} 히스토리 부족")
                return None

            # 종가 리스트 추출
            stock_prices = [float(d['close']) for d in historical if d.get('close')]
            etf_prices = [float(d['close']) for d in etf_historical if d.get('close')]

            # 동행률 계산
            return self.calc.calculate_etf_sync_rate(stock_prices, etf_prices)

        except Exception as e:
            logger.debug(f"  ⚠️ {symbol} ETF 동행률 계산 실패: {e}")
            return None

    def _calculate_volatility_pct(
        self,
        historical: List[Dict]
    ) -> Optional[int]:
        """
        변동성 백분위 계산 헬퍼

        Args:
            historical: 히스토리 데이터

        Returns:
            변동성 백분위 (0-100) 또는 None
        """
        if not historical or len(historical) < 20:
            return None

        try:
            # 1. 각 일자별 변동성 계산 (일중 변동폭 %)
            volatilities = []
            for day in historical:
                high = day.get('high')
                low = day.get('low')
                close = day.get('close')

                if high and low and close and close > 0:
                    # 일중 변동폭 % = (고가 - 저가) / 종가 * 100
                    vol = ((high - low) / close) * 100
                    volatilities.append(vol)

            if len(volatilities) < 20:
                return None

            # 2. 당일 변동성 (최신 데이터)
            current_volatility = volatilities[0] if volatilities else None

            if current_volatility is None:
                return None

            # 3. 백분위 계산 (전체 히스토리 대비)
            return self.calc.calculate_volatility_percentile(
                current_volatility,
                volatilities
            )

        except Exception as e:
            logger.debug(f"  ⚠️ 변동성 백분위 계산 실패: {e}")
            return None
