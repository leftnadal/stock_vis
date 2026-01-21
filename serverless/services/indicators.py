"""
Market Movers 지표 계산 로직

Phase 1: RVOL, Trend Strength
Phase 2: Sector Alpha, ETF Sync Rate, Volatility Percentile

⭐ 중요: AWS Lambda로 전환 시 이 클래스를 그대로 재사용합니다.
Django 의존성 없이 순수 Python으로 작성되었습니다.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
import statistics
import bisect


class IndicatorCalculator:
    """
    Market Movers 지표 계산기

    Django와 AWS Lambda에서 모두 사용 가능하도록 순수 Python으로 작성.
    """

    @staticmethod
    def calculate_rvol(
        current_volume: int,
        historical_volumes: List[int],
        min_periods: int = 10
    ) -> Optional[Decimal]:
        """
        RVOL (Relative Volume) 계산

        당일 거래량을 최근 N일 평균 거래량으로 나눈 값.
        RVOL > 2.0: 평소보다 2배 이상 거래량 증가 (주목 필요)

        Args:
            current_volume: 당일 거래량
            historical_volumes: 과거 거래량 리스트 (최소 min_periods개 필요)
            min_periods: 최소 필요 데이터 개수 (기본 10일)

        Returns:
            RVOL (소수점 2자리) 또는 None (데이터 부족)

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.calculate_rvol(10_000_000, [5_000_000] * 20)
            Decimal('2.00')
            >>> calc.calculate_rvol(10_000_000, [5_000_000] * 5)  # 데이터 부족
            None
        """
        if not historical_volumes or len(historical_volumes) < min_periods:
            return None

        # 0인 거래량 제외
        valid_volumes = [v for v in historical_volumes if v > 0]
        if len(valid_volumes) < min_periods:
            return None

        avg_volume = sum(valid_volumes) / len(valid_volumes)

        # 0 나누기 방지
        if avg_volume == 0:
            return Decimal('1.0')

        rvol = current_volume / avg_volume

        # 소수점 2자리로 반올림
        return Decimal(str(rvol)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_trend_strength(
        open_price: float,
        high: float,
        low: float,
        close: float
    ) -> Optional[Decimal]:
        """
        장중 추세 강도 계산

        (종가 - 시가) / (고가 - 저가)로 계산.
        -1.0 ~ 1.0 범위의 값을 가짐.

        해석:
        - +1.0에 가까울수록: 강한 상승 추세 (시가에서 시작해 고가로 마감)
        - -1.0에 가까울수록: 강한 하락 추세 (시가에서 시작해 저가로 마감)
        - 0.0에 가까울수록: 추세 없음 또는 횡보

        Args:
            open_price: 시가
            high: 고가
            low: 저가
            close: 종가

        Returns:
            추세 강도 (-1.0 ~ 1.0) 또는 None (0 나누기)

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.calculate_trend_strength(100, 110, 100, 110)  # 강한 상승
            Decimal('1.00')
            >>> calc.calculate_trend_strength(110, 110, 100, 100)  # 강한 하락
            Decimal('-1.00')
            >>> calc.calculate_trend_strength(100, 100, 100, 100)  # 변동 없음
            Decimal('0.00')
        """
        if high == low:  # 0 나누기 방지
            return Decimal('0.00')

        strength = (close - open_price) / (high - low)

        # -1.0 ~ 1.0 범위로 클램프
        strength = max(-1.0, min(1.0, strength))

        # 소수점 2자리로 반올림
        return Decimal(str(strength)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def format_rvol_display(rvol: Optional[Decimal]) -> str:
        """
        RVOL 표시 포맷

        Args:
            rvol: RVOL 값

        Returns:
            "2.5x" 형식 또는 "N/A"

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.format_rvol_display(Decimal('2.50'))
            '2.5x'
            >>> calc.format_rvol_display(None)
            'N/A'
        """
        if rvol is None:
            return 'N/A'

        # 소수점 1자리로 표시
        return f'{float(rvol):.1f}x'

    @staticmethod
    def format_trend_display(strength: Optional[Decimal]) -> str:
        """
        추세 강도 표시 포맷

        Args:
            strength: 추세 강도

        Returns:
            "▲0.85" 또는 "▼-0.67" 형식, "N/A"

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.format_trend_display(Decimal('0.85'))
            '▲0.85'
            >>> calc.format_trend_display(Decimal('-0.67'))
            '▼-0.67'
            >>> calc.format_trend_display(None)
            'N/A'
        """
        if strength is None:
            return 'N/A'

        strength_float = float(strength)

        if strength_float >= 0:
            return f'▲{strength_float:.2f}'
        else:
            return f'▼{strength_float:.2f}'

    # ========================================
    # Phase 2 지표 (나중에 구현)
    # ========================================

    @staticmethod
    def calculate_sector_alpha(
        stock_return: float,
        sector_return: float
    ) -> Optional[Decimal]:
        """
        섹터 대비 초과수익 계산

        개별 종목 수익률에서 섹터 수익률을 뺀 값.
        양수: 섹터 평균보다 좋은 성과
        음수: 섹터 평균보다 나쁜 성과

        Args:
            stock_return: 개별 종목 수익률 (%)
            sector_return: 섹터 ETF 수익률 (%)

        Returns:
            초과수익 (%) 또는 None

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.calculate_sector_alpha(5.0, 2.0)  # 종목 +5%, 섹터 +2%
            Decimal('3.00')
            >>> calc.calculate_sector_alpha(-2.0, 1.0)  # 종목 -2%, 섹터 +1%
            Decimal('-3.00')
        """
        if stock_return is None or sector_return is None:
            return None

        alpha = stock_return - sector_return

        # 소수점 2자리로 반올림
        return Decimal(str(alpha)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_etf_sync_rate(
        stock_prices: List[float],
        etf_prices: List[float],
        min_periods: int = 10
    ) -> Optional[Decimal]:
        """
        ETF 동행률 계산

        종목과 섹터 ETF의 가격 움직임 상관관계를 계산.
        피어슨 상관계수의 절댓값을 0-1 범위로 변환.

        해석:
        - 1.0에 가까울수록: 섹터 ETF와 강하게 동조
        - 0.0에 가까울수록: 독립적인 움직임

        Args:
            stock_prices: 종목 가격 리스트 (최근순, 최소 min_periods개)
            etf_prices: 섹터 ETF 가격 리스트 (최근순, 최소 min_periods개)
            min_periods: 최소 필요 데이터 개수 (기본 10일)

        Returns:
            동행률 (0.0 ~ 1.0) 또는 None

        Examples:
            >>> calc = IndicatorCalculator()
            >>> stock = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
            >>> etf = [50, 50.5, 51, 51.5, 52, 52.5, 53, 53.5, 54, 54.5]
            >>> calc.calculate_etf_sync_rate(stock, etf)
            Decimal('1.00')  # 완전 동조
        """
        if not stock_prices or not etf_prices:
            return None

        if len(stock_prices) < min_periods or len(etf_prices) < min_periods:
            return None

        # 길이를 맞춤 (짧은 쪽에 맞춤)
        min_len = min(len(stock_prices), len(etf_prices))
        stock_prices = stock_prices[:min_len]
        etf_prices = etf_prices[:min_len]

        try:
            # 피어슨 상관계수 계산
            correlation = statistics.correlation(stock_prices, etf_prices)

            # 절댓값으로 변환 (방향 무관, 동행 정도만)
            sync_rate = abs(correlation)

            # 0.0 ~ 1.0 범위로 클램프
            sync_rate = max(0.0, min(1.0, sync_rate))

            # 소수점 2자리로 반올림
            return Decimal(str(sync_rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        except (statistics.StatisticsError, ValueError):
            # 표준편차가 0이거나 계산 불가능한 경우
            return None

    @staticmethod
    def calculate_volatility_percentile(
        current_volatility: float,
        historical_volatilities: List[float],
        min_periods: int = 20
    ) -> Optional[int]:
        """
        변동성 백분위 계산

        현재 변동성이 과거 데이터에서 몇 퍼센트에 위치하는지 계산.

        해석:
        - 90 이상: 변동성이 매우 높음 (위험 또는 기회)
        - 50 전후: 평균적인 변동성
        - 10 이하: 변동성이 매우 낮음 (횡보)

        Args:
            current_volatility: 당일 변동성 (예: 일중 변동폭 %)
            historical_volatilities: 과거 변동성 리스트 (최소 min_periods개)
            min_periods: 최소 필요 데이터 개수 (기본 20일)

        Returns:
            백분위 (0-100) 또는 None

        Examples:
            >>> calc = IndicatorCalculator()
            >>> hist = [1.0, 1.5, 2.0, 2.5, 3.0] * 4  # 20개
            >>> calc.calculate_volatility_percentile(3.5, hist)
            100  # 최고 변동성
            >>> calc.calculate_volatility_percentile(1.0, hist)
            0  # 최저 변동성
        """
        if not historical_volatilities or len(historical_volatilities) < min_periods:
            return None

        if current_volatility is None:
            return None

        # 정렬된 리스트에서 현재 값의 위치 찾기
        sorted_vols = sorted(historical_volatilities)
        position = bisect.bisect_left(sorted_vols, current_volatility)

        # 백분위 계산
        percentile = (position / len(sorted_vols)) * 100

        # 0-100 범위로 클램프
        percentile = max(0, min(100, int(round(percentile))))

        return percentile

    # ========================================
    # Phase 2 표시 포맷 함수
    # ========================================

    @staticmethod
    def format_sector_alpha_display(alpha: Optional[Decimal]) -> str:
        """
        섹터 알파 표시 포맷

        Args:
            alpha: 섹터 알파 값

        Returns:
            "+2.5%" 또는 "-1.3%" 형식, "N/A"

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.format_sector_alpha_display(Decimal('2.50'))
            '+2.5%'
            >>> calc.format_sector_alpha_display(Decimal('-1.30'))
            '-1.3%'
        """
        if alpha is None:
            return 'N/A'

        alpha_float = float(alpha)

        if alpha_float >= 0:
            return f'+{alpha_float:.1f}%'
        else:
            return f'{alpha_float:.1f}%'

    @staticmethod
    def format_etf_sync_display(sync_rate: Optional[Decimal]) -> str:
        """
        ETF 동행률 표시 포맷

        Args:
            sync_rate: ETF 동행률 (0.0 ~ 1.0)

        Returns:
            "0.85" 형식 또는 "N/A"

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.format_etf_sync_display(Decimal('0.85'))
            '0.85'
            >>> calc.format_etf_sync_display(None)
            'N/A'
        """
        if sync_rate is None:
            return 'N/A'

        return f'{float(sync_rate):.2f}'

    @staticmethod
    def format_volatility_percentile_display(percentile: Optional[int]) -> str:
        """
        변동성 백분위 표시 포맷

        Args:
            percentile: 백분위 (0-100)

        Returns:
            "87" 형식 또는 "N/A"

        Examples:
            >>> calc = IndicatorCalculator()
            >>> calc.format_volatility_percentile_display(87)
            '87'
            >>> calc.format_volatility_percentile_display(None)
            'N/A'
        """
        if percentile is None:
            return 'N/A'

        return f'{percentile}'
