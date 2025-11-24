"""
기술적 지표 계산 모듈
RSI, MACD, Bollinger Bands, SMA, EMA 등의 기술적 지표를 계산
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.cache import cache


class TechnicalIndicators:
    """기술적 지표 계산 클래스"""

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> List[Optional[float]]:
        """
        단순 이동 평균 (Simple Moving Average) 계산

        Args:
            prices: 가격 리스트
            period: 이동평균 기간

        Returns:
            SMA 값 리스트
        """
        if len(prices) < period:
            return [None] * len(prices)

        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                avg = sum(prices[i - period + 1:i + 1]) / period
                sma.append(round(avg, 2))

        return sma

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[Optional[float]]:
        """
        지수 이동 평균 (Exponential Moving Average) 계산

        Args:
            prices: 가격 리스트
            period: 이동평균 기간

        Returns:
            EMA 값 리스트
        """
        if len(prices) < period:
            return [None] * len(prices)

        multiplier = 2 / (period + 1)
        ema = [None] * (period - 1)

        # 첫 번째 EMA는 SMA로 시작
        sma = sum(prices[:period]) / period
        ema.append(round(sma, 2))

        # 이후 EMA 계산
        for i in range(period, len(prices)):
            current_ema = (prices[i] * multiplier) + (ema[-1] * (1 - multiplier))
            ema.append(round(current_ema, 2))

        return ema

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
        """
        상대강도지수 (Relative Strength Index) 계산

        Args:
            prices: 가격 리스트
            period: RSI 계산 기간 (기본값: 14일)

        Returns:
            RSI 값 리스트 (0-100)
        """
        if len(prices) < period + 1:
            return [None] * len(prices)

        # 가격 변화 계산
        price_changes = []
        for i in range(1, len(prices)):
            price_changes.append(prices[i] - prices[i-1])

        # 상승과 하락 분리
        gains = [change if change > 0 else 0 for change in price_changes]
        losses = [-change if change < 0 else 0 for change in price_changes]

        rsi = [None] * (period)

        # 첫 번째 평균 상승/하락
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(price_changes) + 1):
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                current_rsi = 100 - (100 / (1 + rs))
                rsi.append(round(current_rsi, 2))

            # 다음 평균 계산 (Smoothed Moving Average)
            if i < len(price_changes):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        return rsi

    @staticmethod
    def calculate_macd(prices: List[float],
                      fast_period: int = 12,
                      slow_period: int = 26,
                      signal_period: int = 9) -> Dict[str, List[Optional[float]]]:
        """
        MACD (Moving Average Convergence Divergence) 계산

        Args:
            prices: 가격 리스트
            fast_period: 빠른 EMA 기간 (기본값: 12일)
            slow_period: 느린 EMA 기간 (기본값: 26일)
            signal_period: 시그널 라인 EMA 기간 (기본값: 9일)

        Returns:
            MACD, Signal, Histogram 값을 포함한 딕셔너리
        """
        if len(prices) < slow_period:
            return {
                'macd': [None] * len(prices),
                'signal': [None] * len(prices),
                'histogram': [None] * len(prices)
            }

        # EMA 계산
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow_period)

        # MACD 라인 계산
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is None or ema_slow[i] is None:
                macd_line.append(None)
            else:
                macd_line.append(round(ema_fast[i] - ema_slow[i], 2))

        # Signal 라인 계산 (MACD의 EMA)
        macd_values = [m for m in macd_line if m is not None]
        if len(macd_values) >= signal_period:
            signal_ema = TechnicalIndicators.calculate_ema(macd_values, signal_period)

            # 전체 길이에 맞게 Signal 라인 조정
            signal_line = []
            signal_idx = 0
            for m in macd_line:
                if m is None:
                    signal_line.append(None)
                else:
                    if signal_idx < len(signal_ema):
                        signal_line.append(signal_ema[signal_idx])
                        signal_idx += 1
                    else:
                        signal_line.append(None)
        else:
            signal_line = [None] * len(prices)

        # Histogram 계산 (MACD - Signal)
        histogram = []
        for i in range(len(prices)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram.append(round(macd_line[i] - signal_line[i], 2))
            else:
                histogram.append(None)

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def calculate_bollinger_bands(prices: List[float],
                                 period: int = 20,
                                 std_dev: float = 2) -> Dict[str, List[Optional[float]]]:
        """
        볼린저 밴드 (Bollinger Bands) 계산

        Args:
            prices: 가격 리스트
            period: 이동평균 기간 (기본값: 20일)
            std_dev: 표준편차 배수 (기본값: 2)

        Returns:
            상단밴드, 중간밴드(SMA), 하단밴드 값을 포함한 딕셔너리
        """
        if len(prices) < period:
            return {
                'upper': [None] * len(prices),
                'middle': [None] * len(prices),
                'lower': [None] * len(prices),
                'bandwidth': [None] * len(prices),
                'percent_b': [None] * len(prices)
            }

        # 중간 밴드 (SMA) 계산
        middle_band = TechnicalIndicators.calculate_sma(prices, period)

        upper_band = []
        lower_band = []
        bandwidth = []
        percent_b = []

        for i in range(len(prices)):
            if i < period - 1:
                upper_band.append(None)
                lower_band.append(None)
                bandwidth.append(None)
                percent_b.append(None)
            else:
                # 표준편차 계산
                window_prices = prices[i - period + 1:i + 1]
                std = np.std(window_prices)

                # 밴드 계산
                upper = middle_band[i] + (std_dev * std)
                lower = middle_band[i] - (std_dev * std)

                upper_band.append(round(upper, 2))
                lower_band.append(round(lower, 2))

                # Bandwidth 계산 (상단 - 하단) / 중간
                if middle_band[i] != 0:
                    bw = ((upper - lower) / middle_band[i]) * 100
                    bandwidth.append(round(bw, 2))
                else:
                    bandwidth.append(None)

                # %B 계산 (현재가격 - 하단) / (상단 - 하단)
                if upper != lower:
                    pb = ((prices[i] - lower) / (upper - lower)) * 100
                    percent_b.append(round(pb, 2))
                else:
                    percent_b.append(None)

        return {
            'upper': upper_band,
            'middle': middle_band,
            'lower': lower_band,
            'bandwidth': bandwidth,
            'percent_b': percent_b
        }

    @staticmethod
    def calculate_stochastic(high_prices: List[float],
                           low_prices: List[float],
                           close_prices: List[float],
                           period: int = 14,
                           smooth_k: int = 3,
                           smooth_d: int = 3) -> Dict[str, List[Optional[float]]]:
        """
        스토캐스틱 오실레이터 (Stochastic Oscillator) 계산

        Args:
            high_prices: 고가 리스트
            low_prices: 저가 리스트
            close_prices: 종가 리스트
            period: 계산 기간 (기본값: 14일)
            smooth_k: %K 평활 기간 (기본값: 3일)
            smooth_d: %D 평활 기간 (기본값: 3일)

        Returns:
            %K와 %D 값을 포함한 딕셔너리
        """
        if len(close_prices) < period:
            return {
                'percent_k': [None] * len(close_prices),
                'percent_d': [None] * len(close_prices)
            }

        raw_k = []

        for i in range(len(close_prices)):
            if i < period - 1:
                raw_k.append(None)
            else:
                # 기간 내 최고가와 최저가
                highest = max(high_prices[i - period + 1:i + 1])
                lowest = min(low_prices[i - period + 1:i + 1])

                if highest != lowest:
                    k = ((close_prices[i] - lowest) / (highest - lowest)) * 100
                    raw_k.append(round(k, 2))
                else:
                    raw_k.append(50)  # 변동이 없을 때 중간값

        # %K 평활화 (SMA)
        percent_k = TechnicalIndicators.calculate_sma(
            [k for k in raw_k if k is not None],
            smooth_k
        )

        # %D 계산 (%K의 SMA)
        percent_d = TechnicalIndicators.calculate_sma(
            percent_k,
            smooth_d
        )

        # 전체 길이에 맞게 조정
        final_k = []
        final_d = []
        k_idx = 0
        d_idx = 0

        for i, k in enumerate(raw_k):
            if k is None:
                final_k.append(None)
                final_d.append(None)
            else:
                if k_idx < len(percent_k):
                    final_k.append(percent_k[k_idx])
                    k_idx += 1
                else:
                    final_k.append(None)

                if d_idx < len(percent_d):
                    final_d.append(percent_d[d_idx])
                    d_idx += 1
                else:
                    final_d.append(None)

        return {
            'percent_k': final_k,
            'percent_d': final_d
        }

    @staticmethod
    def calculate_atr(high_prices: List[float],
                     low_prices: List[float],
                     close_prices: List[float],
                     period: int = 14) -> List[Optional[float]]:
        """
        평균 진폭 지표 (Average True Range) 계산

        Args:
            high_prices: 고가 리스트
            low_prices: 저가 리스트
            close_prices: 종가 리스트
            period: ATR 계산 기간 (기본값: 14일)

        Returns:
            ATR 값 리스트
        """
        if len(close_prices) < period + 1:
            return [None] * len(close_prices)

        true_ranges = []

        for i in range(1, len(close_prices)):
            # True Range 계산
            high_low = high_prices[i] - low_prices[i]
            high_close = abs(high_prices[i] - close_prices[i-1])
            low_close = abs(low_prices[i] - close_prices[i-1])

            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)

        atr = [None]  # 첫 번째 값은 None

        # 첫 번째 ATR은 단순 평균
        first_atr = sum(true_ranges[:period]) / period
        atr.extend([None] * (period - 1))
        atr.append(round(first_atr, 2))

        # 이후 ATR은 지수 이동 평균
        current_atr = first_atr
        for i in range(period, len(true_ranges)):
            current_atr = ((current_atr * (period - 1)) + true_ranges[i]) / period
            atr.append(round(current_atr, 2))

        return atr

    @staticmethod
    def calculate_obv(volumes: List[float], close_prices: List[float]) -> List[float]:
        """
        거래량 균형 지표 (On-Balance Volume) 계산

        Args:
            volumes: 거래량 리스트
            close_prices: 종가 리스트

        Returns:
            OBV 값 리스트
        """
        if len(volumes) != len(close_prices):
            raise ValueError("거래량과 가격 리스트의 길이가 같아야 합니다.")

        if len(close_prices) == 0:
            return []

        obv = [volumes[0]]

        for i in range(1, len(close_prices)):
            if close_prices[i] > close_prices[i-1]:
                # 가격 상승: OBV에 거래량 추가
                obv.append(obv[-1] + volumes[i])
            elif close_prices[i] < close_prices[i-1]:
                # 가격 하락: OBV에서 거래량 차감
                obv.append(obv[-1] - volumes[i])
            else:
                # 가격 변동 없음: OBV 유지
                obv.append(obv[-1])

        return obv

    @staticmethod
    def identify_support_resistance(prices: List[float],
                                   window: int = 20,
                                   num_levels: int = 5) -> Dict[str, List[float]]:
        """
        지지선과 저항선 식별

        Args:
            prices: 가격 리스트
            window: 검색 윈도우 크기
            num_levels: 반환할 레벨 수

        Returns:
            지지선과 저항선 레벨
        """
        if len(prices) < window * 2:
            return {'support': [], 'resistance': []}

        # 로컬 최대값과 최소값 찾기
        highs = []
        lows = []

        for i in range(window, len(prices) - window):
            window_slice = prices[i - window:i + window + 1]

            if prices[i] == max(window_slice):
                highs.append(prices[i])
            elif prices[i] == min(window_slice):
                lows.append(prices[i])

        # 클러스터링으로 주요 레벨 식별
        def cluster_levels(levels: List[float], threshold: float = 0.01) -> List[float]:
            if not levels:
                return []

            sorted_levels = sorted(levels)
            clusters = [[sorted_levels[0]]]

            for level in sorted_levels[1:]:
                if abs(level - clusters[-1][-1]) / clusters[-1][-1] < threshold:
                    clusters[-1].append(level)
                else:
                    clusters.append([level])

            # 각 클러스터의 평균을 대표값으로
            clustered = [sum(cluster) / len(cluster) for cluster in clusters]

            # 빈도순으로 정렬
            clustered.sort(key=lambda x: sum(1 for l in levels if abs(l - x) / x < threshold), reverse=True)

            return clustered[:num_levels]

        support_levels = cluster_levels(lows)
        resistance_levels = cluster_levels(highs)

        return {
            'support': sorted(support_levels),
            'resistance': sorted(resistance_levels, reverse=True)
        }

    @staticmethod
    def calculate_all_indicators(stock_data: pd.DataFrame) -> Dict:
        """
        모든 기술적 지표를 한 번에 계산

        Args:
            stock_data: 주가 데이터 DataFrame (columns: open, high, low, close, volume)

        Returns:
            모든 기술적 지표를 포함한 딕셔너리
        """
        # Decimal 타입을 float으로 변환
        close_prices = [float(x) for x in stock_data['close'].tolist()]
        high_prices = [float(x) for x in stock_data['high'].tolist()]
        low_prices = [float(x) for x in stock_data['low'].tolist()]
        volumes = [float(x) for x in stock_data['volume'].tolist()]

        indicators = {}

        # 이동평균
        indicators['sma_20'] = TechnicalIndicators.calculate_sma(close_prices, 20)
        indicators['sma_50'] = TechnicalIndicators.calculate_sma(close_prices, 50)
        indicators['sma_200'] = TechnicalIndicators.calculate_sma(close_prices, 200)
        indicators['ema_12'] = TechnicalIndicators.calculate_ema(close_prices, 12)
        indicators['ema_26'] = TechnicalIndicators.calculate_ema(close_prices, 26)

        # RSI
        indicators['rsi'] = TechnicalIndicators.calculate_rsi(close_prices)

        # MACD
        macd_result = TechnicalIndicators.calculate_macd(close_prices)
        indicators.update(macd_result)

        # 볼린저 밴드
        bb_result = TechnicalIndicators.calculate_bollinger_bands(close_prices)
        indicators['bb_upper'] = bb_result['upper']
        indicators['bb_middle'] = bb_result['middle']
        indicators['bb_lower'] = bb_result['lower']
        indicators['bb_bandwidth'] = bb_result['bandwidth']
        indicators['bb_percent_b'] = bb_result['percent_b']

        # 스토캐스틱
        stoch_result = TechnicalIndicators.calculate_stochastic(
            high_prices, low_prices, close_prices
        )
        indicators['stoch_k'] = stoch_result['percent_k']
        indicators['stoch_d'] = stoch_result['percent_d']

        # ATR
        indicators['atr'] = TechnicalIndicators.calculate_atr(
            high_prices, low_prices, close_prices
        )

        # OBV
        indicators['obv'] = TechnicalIndicators.calculate_obv(volumes, close_prices)

        # 지지/저항선
        support_resistance = TechnicalIndicators.identify_support_resistance(close_prices)
        indicators['support_levels'] = support_resistance['support']
        indicators['resistance_levels'] = support_resistance['resistance']

        return indicators


class IndicatorSignals:
    """기술적 지표 기반 매매 신호 생성"""

    @staticmethod
    def get_rsi_signal(rsi: float) -> str:
        """
        RSI 기반 매매 신호

        Args:
            rsi: RSI 값

        Returns:
            'buy' (과매도), 'sell' (과매수), 'neutral' (중립)
        """
        if rsi is None:
            return 'neutral'

        if rsi < 30:
            return 'buy'  # 과매도
        elif rsi > 70:
            return 'sell'  # 과매수
        else:
            return 'neutral'

    @staticmethod
    def get_macd_signal(macd: float, signal: float, prev_macd: float, prev_signal: float) -> str:
        """
        MACD 기반 매매 신호

        Args:
            macd: 현재 MACD 값
            signal: 현재 Signal 값
            prev_macd: 이전 MACD 값
            prev_signal: 이전 Signal 값

        Returns:
            'buy' (골든크로스), 'sell' (데드크로스), 'neutral' (중립)
        """
        if None in [macd, signal, prev_macd, prev_signal]:
            return 'neutral'

        # 골든 크로스: MACD가 Signal을 상향 돌파
        if prev_macd <= prev_signal and macd > signal:
            return 'buy'
        # 데드 크로스: MACD가 Signal을 하향 돌파
        elif prev_macd >= prev_signal and macd < signal:
            return 'sell'
        else:
            return 'neutral'

    @staticmethod
    def get_bollinger_signal(price: float, upper: float, lower: float, middle: float) -> str:
        """
        볼린저 밴드 기반 매매 신호

        Args:
            price: 현재 가격
            upper: 상단 밴드
            lower: 하단 밴드
            middle: 중간 밴드

        Returns:
            'buy' (하단 터치), 'sell' (상단 터치), 'neutral' (중립)
        """
        if None in [price, upper, lower, middle]:
            return 'neutral'

        if price <= lower:
            return 'buy'  # 하단 밴드 터치
        elif price >= upper:
            return 'sell'  # 상단 밴드 터치
        else:
            return 'neutral'

    @staticmethod
    def get_stochastic_signal(k: float, d: float) -> str:
        """
        스토캐스틱 기반 매매 신호

        Args:
            k: %K 값
            d: %D 값

        Returns:
            'buy' (과매도), 'sell' (과매수), 'neutral' (중립)
        """
        if None in [k, d]:
            return 'neutral'

        if k < 20 and d < 20:
            return 'buy'  # 과매도
        elif k > 80 and d > 80:
            return 'sell'  # 과매수
        else:
            return 'neutral'

    @staticmethod
    def get_composite_signal(indicators: Dict) -> Dict[str, any]:
        """
        여러 지표를 종합한 매매 신호

        Args:
            indicators: 각종 지표 값을 포함한 딕셔너리

        Returns:
            종합 신호와 개별 신호들
        """
        signals = {}

        # RSI 신호
        if 'rsi' in indicators and indicators['rsi']:
            signals['rsi'] = IndicatorSignals.get_rsi_signal(indicators['rsi'][-1])

        # MACD 신호
        if all(k in indicators for k in ['macd', 'signal']) and len(indicators['macd']) >= 2:
            signals['macd'] = IndicatorSignals.get_macd_signal(
                indicators['macd'][-1],
                indicators['signal'][-1],
                indicators['macd'][-2],
                indicators['signal'][-2]
            )

        # 볼린저 밴드 신호
        if all(k in indicators for k in ['price', 'bb_upper', 'bb_lower', 'bb_middle']):
            signals['bollinger'] = IndicatorSignals.get_bollinger_signal(
                indicators['price'],
                indicators['bb_upper'][-1],
                indicators['bb_lower'][-1],
                indicators['bb_middle'][-1]
            )

        # 스토캐스틱 신호
        if all(k in indicators for k in ['stoch_k', 'stoch_d']):
            signals['stochastic'] = IndicatorSignals.get_stochastic_signal(
                indicators['stoch_k'][-1],
                indicators['stoch_d'][-1]
            )

        # 종합 신호 계산
        buy_count = sum(1 for s in signals.values() if s == 'buy')
        sell_count = sum(1 for s in signals.values() if s == 'sell')

        if buy_count > sell_count and buy_count >= 2:
            composite = 'strong_buy' if buy_count >= 3 else 'buy'
        elif sell_count > buy_count and sell_count >= 2:
            composite = 'strong_sell' if sell_count >= 3 else 'sell'
        else:
            composite = 'neutral'

        return {
            'composite_signal': composite,
            'individual_signals': signals,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'timestamp': datetime.now().isoformat()
        }