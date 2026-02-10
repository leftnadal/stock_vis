"""
Market Breadth 계산 서비스 (Lambda 전환 대상)

"지금 시장이 좋은가?"를 한눈에 파악할 수 있는 지표를 계산합니다.

데이터 소스: FMP API (gainers/losers, market performance)
"""
import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple

from django.core.cache import cache
from django.db import transaction

from serverless.models import MarketBreadth
from serverless.services.fmp_client import FMPClient, FMPAPIError


logger = logging.getLogger(__name__)


class MarketBreadthService:
    """
    Market Breadth 계산 서비스

    상승/하락 비율, 신고가/신저가, 거래량 흐름을 분석하여
    시장 건강도를 평가합니다.

    Usage:
        service = MarketBreadthService()
        breadth = service.calculate_daily_breadth()  # 오늘 데이터
        history = service.get_breadth_history(days=30)  # 30일 히스토리
    """

    # 캐시 TTL
    CACHE_TTL_CURRENT = 300  # 5분 (당일 데이터)
    CACHE_TTL_HISTORY = 3600  # 1시간 (히스토리)

    # 시그널 판단 기준
    SIGNAL_THRESHOLDS = {
        'strong_bullish': 2.0,  # A/D ratio >= 2.0
        'bullish': 1.5,         # A/D ratio >= 1.5
        'neutral': 0.67,        # A/D ratio >= 0.67
        'bearish': 0.5,         # A/D ratio >= 0.5
        # 'strong_bearish': below 0.5
    }

    def __init__(self):
        self.fmp_client = FMPClient()

    def calculate_daily_breadth(self, target_date: Optional[date] = None) -> Optional[MarketBreadth]:
        """
        일일 Market Breadth 계산

        Args:
            target_date: 계산 대상 날짜 (기본값: 오늘)

        Returns:
            MarketBreadth 객체 또는 None

        Raises:
            FMPAPIError: FMP API 호출 실패 시
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Market Breadth 계산 시작: {target_date}")

        try:
            # FMP API에서 gainers/losers/actives 데이터 가져오기
            gainers = self.fmp_client.get_market_gainers()
            losers = self.fmp_client.get_market_losers()
            actives = self.fmp_client.get_market_actives()

            # 상승/하락 종목 수 및 거래량 계산
            advancing, declining, unchanged = self._count_advance_decline(gainers, losers, actives)
            up_volume, down_volume = self._calculate_volume_flow(gainers, losers, actives)

            # A/D 비율 계산
            ad_ratio = self._calculate_ad_ratio(advancing, declining)

            # 신고가/신저가 (FMP API에서 직접 지원하지 않으므로 추정)
            new_highs, new_lows = self._estimate_new_highs_lows(gainers, losers)

            # 시그널 판단
            signal = self._determine_signal(ad_ratio, new_highs, new_lows, up_volume, down_volume)

            # 이전 A/D Line 가져오기
            prev_breadth = MarketBreadth.objects.filter(
                date__lt=target_date
            ).order_by('-date').first()

            prev_ad_line = prev_breadth.advance_decline_line if prev_breadth else 0
            ad_line = prev_ad_line + (advancing - declining)

            # 추가 비율 계산
            nh_nl_ratio = None
            if new_lows > 0:
                nh_nl_ratio = Decimal(str(new_highs / new_lows)).quantize(
                    Decimal('0.001'), rounding=ROUND_HALF_UP
                )

            volume_ratio = None
            if down_volume > 0:
                volume_ratio = Decimal(str(up_volume / down_volume)).quantize(
                    Decimal('0.001'), rounding=ROUND_HALF_UP
                )

            # DB 저장 (update_or_create)
            with transaction.atomic():
                breadth, created = MarketBreadth.objects.update_or_create(
                    date=target_date,
                    defaults={
                        'advancing_count': advancing,
                        'declining_count': declining,
                        'unchanged_count': unchanged,
                        'new_highs': new_highs,
                        'new_lows': new_lows,
                        'up_volume': up_volume,
                        'down_volume': down_volume,
                        'advance_decline_ratio': ad_ratio,
                        'advance_decline_line': ad_line,
                        'breadth_signal': signal,
                        'new_high_low_ratio': nh_nl_ratio,
                        'volume_ratio': volume_ratio,
                        'data_source': 'fmp',
                    }
                )

            action = "생성" if created else "업데이트"
            logger.info(f"Market Breadth {action}: {target_date} - {signal} (A/D: {ad_ratio})")

            # 캐시 무효화
            self._invalidate_cache(target_date)

            return breadth

        except FMPAPIError as e:
            logger.error(f"Market Breadth 계산 실패 (FMP API): {e}")
            raise
        except Exception as e:
            logger.exception(f"Market Breadth 계산 중 예기치 않은 오류: {e}")
            return None

    def get_current_breadth(self, target_date: Optional[date] = None) -> Optional[Dict]:
        """
        현재 Market Breadth 조회 (캐시 우선)

        Args:
            target_date: 조회 날짜 (기본값: 오늘)

        Returns:
            Market Breadth 딕셔너리 또는 None
        """
        if target_date is None:
            target_date = date.today()

        cache_key = f'market_breadth:{target_date}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Market Breadth 캐시 HIT: {target_date}")
            return cached

        try:
            breadth = MarketBreadth.objects.get(date=target_date)
            result = self._serialize_breadth(breadth)
            cache.set(cache_key, result, self.CACHE_TTL_CURRENT)
            return result
        except MarketBreadth.DoesNotExist:
            logger.warning(f"Market Breadth 데이터 없음: {target_date}")
            return None

    def get_breadth_history(self, days: int = 30) -> List[Dict]:
        """
        Market Breadth 히스토리 조회

        Args:
            days: 조회 일수 (기본값: 30일)

        Returns:
            Market Breadth 리스트 (최근순)
        """
        cache_key = f'market_breadth_history:{days}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Market Breadth 히스토리 캐시 HIT: {days}일")
            return cached

        start_date = date.today() - timedelta(days=days)
        breadths = MarketBreadth.objects.filter(
            date__gte=start_date
        ).order_by('-date')

        result = [self._serialize_breadth(b) for b in breadths]
        cache.set(cache_key, result, self.CACHE_TTL_HISTORY)
        return result

    def get_breadth_signal(self, breadth: Optional[MarketBreadth] = None) -> str:
        """
        시장 신호 판단

        Args:
            breadth: MarketBreadth 객체 (없으면 오늘 데이터 조회)

        Returns:
            신호 문자열: 'strong_bullish', 'bullish', 'neutral', 'bearish', 'strong_bearish'
        """
        if breadth is None:
            try:
                breadth = MarketBreadth.objects.get(date=date.today())
            except MarketBreadth.DoesNotExist:
                return 'neutral'

        return breadth.breadth_signal

    def get_signal_interpretation(self, signal: str) -> Dict:
        """
        시그널 해석 반환

        Args:
            signal: 시그널 문자열

        Returns:
            해석 딕셔너리 (title, description, color, emoji)
        """
        interpretations = {
            'strong_bullish': {
                'title': '강한 상승세',
                'description': '시장이 전반적으로 매우 강한 상승세입니다. 상승 종목이 하락 종목보다 2배 이상 많습니다.',
                'color': '#22c55e',  # green-500
                'emoji': '🚀',
            },
            'bullish': {
                'title': '상승세',
                'description': '시장이 상승세입니다. 상승 종목이 하락 종목보다 50% 이상 많습니다.',
                'color': '#84cc16',  # lime-500
                'emoji': '📈',
            },
            'neutral': {
                'title': '중립',
                'description': '시장이 방향성 없이 횡보 중입니다. 상승과 하락 종목이 비슷합니다.',
                'color': '#eab308',  # yellow-500
                'emoji': '➡️',
            },
            'bearish': {
                'title': '하락세',
                'description': '시장이 하락세입니다. 하락 종목이 상승 종목보다 많습니다.',
                'color': '#f97316',  # orange-500
                'emoji': '📉',
            },
            'strong_bearish': {
                'title': '강한 하락세',
                'description': '시장이 전반적으로 매우 약합니다. 하락 종목이 상승 종목보다 2배 이상 많습니다.',
                'color': '#ef4444',  # red-500
                'emoji': '💥',
            },
        }
        return interpretations.get(signal, interpretations['neutral'])

    # ========================================
    # Private Methods
    # ========================================

    def _count_advance_decline(
        self,
        gainers: List[Dict],
        losers: List[Dict],
        actives: List[Dict]
    ) -> Tuple[int, int, int]:
        """
        상승/하락/보합 종목 수 계산

        actives 데이터의 changesPercentage를 분석하여 실제 시장 분위기를 추정합니다.
        FMP API는 거래량 상위 종목을 반환하므로, 이 데이터가 시장 전체를 대표한다고 가정합니다.
        """
        # actives에서 상승/하락/보합 비율 계산
        advancing_count = 0
        declining_count = 0
        unchanged_count = 0

        for stock in actives:
            change = stock.get('changesPercentage') or stock.get('changePercentage', 0)
            if change is None:
                change = 0

            if change > 0.1:  # +0.1% 초과 = 상승
                advancing_count += 1
            elif change < -0.1:  # -0.1% 미만 = 하락
                declining_count += 1
            else:  # ±0.1% 이내 = 보합
                unchanged_count += 1

        # actives가 비어있거나 모두 보합인 경우 gainers/losers 사용
        if advancing_count == 0 and declining_count == 0:
            advancing_count = len(gainers)
            declining_count = len(losers)

        # 전체 시장으로 확대 추정 (NYSE + NASDAQ 약 5000개 종목 기준)
        # actives 비율을 전체 시장에 적용
        total_active = advancing_count + declining_count + unchanged_count
        if total_active > 0:
            market_total = 5000  # NYSE + NASDAQ 활성 종목 수 추정
            advancing = int((advancing_count / total_active) * market_total)
            declining = int((declining_count / total_active) * market_total)
            unchanged = int((unchanged_count / total_active) * market_total)
        else:
            # 폴백: 중립 상태
            advancing = 2000
            declining = 2000
            unchanged = 1000

        logger.debug(
            f"Market Breadth 계산: actives {total_active}개 분석 → "
            f"상승 {advancing_count}({advancing}), "
            f"하락 {declining_count}({declining}), "
            f"보합 {unchanged_count}({unchanged})"
        )

        return advancing, declining, unchanged

    def _calculate_volume_flow(
        self,
        gainers: List[Dict],
        losers: List[Dict],
        actives: List[Dict] = None
    ) -> Tuple[int, int]:
        """
        상승/하락 종목 거래량 흐름 계산

        FMP Starter Plan에서는 gainers/losers/actives API 모두 volume 필드가 없습니다.
        대안으로 변동률의 절대값을 가중치로 사용하여 거래량 흐름을 추정합니다.

        가정: 변동률이 클수록 거래량이 많다
        """
        up_volume = 0
        down_volume = 0

        # 1. actives에서 실제 volume 데이터 시도
        if actives:
            for stock in actives:
                volume = stock.get('volume', 0) or 0
                change = stock.get('changesPercentage') or stock.get('changePercentage', 0)
                if change is None:
                    change = 0

                if volume > 0:
                    if change > 0:
                        up_volume += volume
                    elif change < 0:
                        down_volume += volume

        # 2. volume 데이터가 없으면 gainers/losers 시도
        if up_volume == 0 and down_volume == 0:
            up_volume = sum(stock.get('volume', 0) or 0 for stock in gainers)
            down_volume = sum(stock.get('volume', 0) or 0 for stock in losers)

        # 3. 여전히 0인 경우, 변동률 가중치로 추정
        if up_volume == 0 and down_volume == 0:
            # Gainers의 변동률 합산 (변동률 = 거래량 프록시)
            up_weight = sum(
                abs(stock.get('changesPercentage') or stock.get('changePercentage', 0) or 0)
                for stock in gainers
            )
            # Losers의 변동률 합산
            down_weight = sum(
                abs(stock.get('changesPercentage') or stock.get('changePercentage', 0) or 0)
                for stock in losers
            )

            # 가상의 거래량으로 변환 (1% = 100만주 가정)
            base_volume = 1_000_000
            up_volume = int(up_weight * base_volume)
            down_volume = int(down_weight * base_volume)

            logger.debug(
                f"Volume 추정 (변동률 가중치): 상승 {up_weight:.1f}% → {up_volume:,}, "
                f"하락 {down_weight:.1f}% → {down_volume:,}"
            )

        # 최소값 보장 (0 나누기 방지)
        if up_volume == 0:
            up_volume = 1
        if down_volume == 0:
            down_volume = 1

        return up_volume, down_volume

    def _calculate_ad_ratio(self, advancing: int, declining: int) -> Decimal:
        """A/D 비율 계산"""
        if declining == 0:
            return Decimal('10.0')  # 최대값 제한

        ratio = advancing / declining
        return Decimal(str(ratio)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def _estimate_new_highs_lows(
        self,
        gainers: List[Dict],
        losers: List[Dict]
    ) -> Tuple[int, int]:
        """
        52주 신고가/신저가 추정

        Note: FMP 무료 플랜에서는 52주 신고가/신저가 API를 지원하지 않아
              상승/하락 폭으로 추정합니다.
        """
        # 상승률 10% 이상 = 신고가 후보
        new_highs = sum(
            1 for s in gainers
            if s.get('changesPercentage', 0) >= 10.0
        )

        # 하락률 10% 이상 = 신저가 후보
        new_lows = sum(
            1 for s in losers
            if abs(s.get('changesPercentage', 0)) >= 10.0
        )

        return new_highs * 5, new_lows * 5  # 추정치 확장

    def _determine_signal(
        self,
        ad_ratio: Decimal,
        new_highs: int,
        new_lows: int,
        up_volume: int,
        down_volume: int
    ) -> str:
        """시장 신호 판단"""
        ratio = float(ad_ratio)

        # 기본 A/D 비율 기반 판단
        if ratio >= self.SIGNAL_THRESHOLDS['strong_bullish']:
            base_signal = 'strong_bullish'
        elif ratio >= self.SIGNAL_THRESHOLDS['bullish']:
            base_signal = 'bullish'
        elif ratio >= self.SIGNAL_THRESHOLDS['neutral']:
            base_signal = 'neutral'
        elif ratio >= self.SIGNAL_THRESHOLDS['bearish']:
            base_signal = 'bearish'
        else:
            base_signal = 'strong_bearish'

        # 거래량 비율로 조정
        if down_volume > 0:
            volume_ratio = up_volume / down_volume
            if volume_ratio > 2.0 and base_signal == 'bullish':
                return 'strong_bullish'
            if volume_ratio < 0.5 and base_signal == 'bearish':
                return 'strong_bearish'

        # 신고가/신저가 비율로 조정
        if new_lows > 0:
            nh_nl_ratio = new_highs / new_lows
            if nh_nl_ratio > 3.0 and base_signal == 'neutral':
                return 'bullish'
            if nh_nl_ratio < 0.33 and base_signal == 'neutral':
                return 'bearish'

        return base_signal

    def _serialize_breadth(self, breadth: MarketBreadth) -> Dict:
        """MarketBreadth 객체를 딕셔너리로 변환"""
        interpretation = self.get_signal_interpretation(breadth.breadth_signal)

        return {
            'date': breadth.date.isoformat(),
            'advancing_count': breadth.advancing_count,
            'declining_count': breadth.declining_count,
            'unchanged_count': breadth.unchanged_count,
            'advance_decline_ratio': float(breadth.advance_decline_ratio),
            'advance_decline_line': breadth.advance_decline_line,
            'new_highs': breadth.new_highs,
            'new_lows': breadth.new_lows,
            'up_volume': breadth.up_volume,
            'down_volume': breadth.down_volume,
            'breadth_signal': breadth.breadth_signal,
            'signal_interpretation': interpretation,
            'new_high_low_ratio': float(breadth.new_high_low_ratio) if breadth.new_high_low_ratio else None,
            'volume_ratio': float(breadth.volume_ratio) if breadth.volume_ratio else None,
        }

    def _invalidate_cache(self, target_date: date):
        """관련 캐시 무효화"""
        cache.delete(f'market_breadth:{target_date}')
        # 히스토리 캐시도 무효화
        for days in [7, 14, 30, 60, 90]:
            cache.delete(f'market_breadth_history:{days}')
