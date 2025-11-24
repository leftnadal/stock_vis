"""
기술적 지표 API 뷰
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.cache import cache
import pandas as pd
from datetime import datetime, timedelta

from .models import Stock, DailyPrice
from .indicators import TechnicalIndicators, IndicatorSignals


class TechnicalIndicatorView(APIView):
    """기술적 지표 계산 API"""

    def get(self, request, symbol):
        """
        특정 종목의 기술적 지표를 반환

        Query Parameters:
            - period: 데이터 기간 (30d, 60d, 90d, 180d, 1y, 2y, max)
            - indicators: 쉼표로 구분된 지표 리스트 (예: rsi,macd,bb)
        """
        symbol = symbol.upper()
        stock = get_object_or_404(Stock, symbol=symbol)

        # 쿼리 파라미터 파싱
        period = request.query_params.get('period', '90d')
        requested_indicators = request.query_params.get('indicators', 'all').split(',')

        # 캐시 키 생성
        cache_key = f"indicators_{symbol}_{period}_{'_'.join(sorted(requested_indicators))}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        # 기간에 따른 날짜 계산
        end_date = datetime.now().date()

        if period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '60d':
            start_date = end_date - timedelta(days=60)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '180d':
            start_date = end_date - timedelta(days=180)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == '2y':
            start_date = end_date - timedelta(days=730)
        else:  # max
            start_date = None

        # 가격 데이터 조회
        query = DailyPrice.objects.filter(stock=stock)
        if start_date:
            query = query.filter(date__gte=start_date)

        prices_data = query.order_by('date').values(
            'date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume'
        )

        if not prices_data:
            return Response(
                {'error': f'No price data available for {symbol}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # DataFrame 생성
        df = pd.DataFrame(list(prices_data))
        df['date'] = pd.to_datetime(df['date'])

        # 기술적 지표 계산
        close_prices = df['close_price'].astype(float).tolist()
        high_prices = df['high_price'].astype(float).tolist()
        low_prices = df['low_price'].astype(float).tolist()
        volumes = df['volume'].astype(float).tolist()

        indicators_data = {
            'symbol': symbol,
            'stock_name': stock.stock_name,
            'period': period,
            'dates': df['date'].dt.strftime('%Y-%m-%d').tolist(),
            'prices': close_prices,
            'current_price': float(stock.real_time_price) if stock.real_time_price else close_prices[-1],
            'indicators': {}
        }

        # 요청된 지표만 계산
        if 'all' in requested_indicators or 'sma' in requested_indicators:
            indicators_data['indicators']['sma_20'] = TechnicalIndicators.calculate_sma(close_prices, 20)
            indicators_data['indicators']['sma_50'] = TechnicalIndicators.calculate_sma(close_prices, 50)
            indicators_data['indicators']['sma_200'] = TechnicalIndicators.calculate_sma(close_prices, 200)

        if 'all' in requested_indicators or 'ema' in requested_indicators:
            indicators_data['indicators']['ema_12'] = TechnicalIndicators.calculate_ema(close_prices, 12)
            indicators_data['indicators']['ema_26'] = TechnicalIndicators.calculate_ema(close_prices, 26)

        if 'all' in requested_indicators or 'rsi' in requested_indicators:
            rsi_values = TechnicalIndicators.calculate_rsi(close_prices)
            indicators_data['indicators']['rsi'] = rsi_values
            if rsi_values and rsi_values[-1] is not None:
                indicators_data['indicators']['rsi_signal'] = IndicatorSignals.get_rsi_signal(rsi_values[-1])

        if 'all' in requested_indicators or 'macd' in requested_indicators:
            macd_result = TechnicalIndicators.calculate_macd(close_prices)
            indicators_data['indicators']['macd'] = macd_result['macd']
            indicators_data['indicators']['macd_signal'] = macd_result['signal']
            indicators_data['indicators']['macd_histogram'] = macd_result['histogram']

            # MACD 매매 신호
            if (len(macd_result['macd']) >= 2 and
                macd_result['macd'][-1] is not None and
                macd_result['signal'][-1] is not None):
                indicators_data['indicators']['macd_trade_signal'] = IndicatorSignals.get_macd_signal(
                    macd_result['macd'][-1],
                    macd_result['signal'][-1],
                    macd_result['macd'][-2] if len(macd_result['macd']) > 1 else 0,
                    macd_result['signal'][-2] if len(macd_result['signal']) > 1 else 0
                )

        if 'all' in requested_indicators or 'bb' in requested_indicators or 'bollinger' in requested_indicators:
            bb_result = TechnicalIndicators.calculate_bollinger_bands(close_prices)
            indicators_data['indicators']['bb_upper'] = bb_result['upper']
            indicators_data['indicators']['bb_middle'] = bb_result['middle']
            indicators_data['indicators']['bb_lower'] = bb_result['lower']
            indicators_data['indicators']['bb_bandwidth'] = bb_result['bandwidth']
            indicators_data['indicators']['bb_percent_b'] = bb_result['percent_b']

            # 볼린저 밴드 신호
            if (bb_result['upper'] and bb_result['upper'][-1] is not None):
                indicators_data['indicators']['bb_signal'] = IndicatorSignals.get_bollinger_signal(
                    close_prices[-1],
                    bb_result['upper'][-1],
                    bb_result['lower'][-1],
                    bb_result['middle'][-1]
                )

        if 'all' in requested_indicators or 'stoch' in requested_indicators or 'stochastic' in requested_indicators:
            stoch_result = TechnicalIndicators.calculate_stochastic(
                high_prices, low_prices, close_prices
            )
            indicators_data['indicators']['stoch_k'] = stoch_result['percent_k']
            indicators_data['indicators']['stoch_d'] = stoch_result['percent_d']

            # 스토캐스틱 신호
            if (stoch_result['percent_k'] and stoch_result['percent_k'][-1] is not None):
                indicators_data['indicators']['stoch_signal'] = IndicatorSignals.get_stochastic_signal(
                    stoch_result['percent_k'][-1],
                    stoch_result['percent_d'][-1] if stoch_result['percent_d'][-1] else 50
                )

        if 'all' in requested_indicators or 'atr' in requested_indicators:
            indicators_data['indicators']['atr'] = TechnicalIndicators.calculate_atr(
                high_prices, low_prices, close_prices
            )

        if 'all' in requested_indicators or 'obv' in requested_indicators:
            indicators_data['indicators']['obv'] = TechnicalIndicators.calculate_obv(
                volumes, close_prices
            )

        if 'all' in requested_indicators or 'support_resistance' in requested_indicators:
            sr_levels = TechnicalIndicators.identify_support_resistance(close_prices)
            indicators_data['indicators']['support_levels'] = sr_levels['support']
            indicators_data['indicators']['resistance_levels'] = sr_levels['resistance']

        # 종합 신호 계산
        composite_input = {
            'price': close_prices[-1] if close_prices else None
        }

        if 'rsi' in indicators_data['indicators']:
            composite_input['rsi'] = indicators_data['indicators']['rsi']
        if 'macd' in indicators_data['indicators']:
            composite_input['macd'] = indicators_data['indicators']['macd']
            composite_input['signal'] = indicators_data['indicators']['macd_signal']
        if 'bb_upper' in indicators_data['indicators']:
            composite_input['bb_upper'] = indicators_data['indicators']['bb_upper']
            composite_input['bb_lower'] = indicators_data['indicators']['bb_lower']
            composite_input['bb_middle'] = indicators_data['indicators']['bb_middle']
        if 'stoch_k' in indicators_data['indicators']:
            composite_input['stoch_k'] = indicators_data['indicators']['stoch_k']
            composite_input['stoch_d'] = indicators_data['indicators']['stoch_d']

        composite_signal = IndicatorSignals.get_composite_signal(composite_input)
        indicators_data['composite_signal'] = composite_signal

        # 캐시에 저장 (5분)
        cache.set(cache_key, indicators_data, 300)

        return Response(indicators_data)


class IndicatorSignalView(APIView):
    """매매 신호 API"""

    def get(self, request, symbol):
        """
        특정 종목의 종합 매매 신호를 반환
        """
        symbol = symbol.upper()
        stock = get_object_or_404(Stock, symbol=symbol)

        # 캐시 확인
        cache_key = f"signal_{symbol}"
        cached_signal = cache.get(cache_key)

        if cached_signal:
            return Response(cached_signal)

        # 최근 100일 데이터로 계산
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=100)

        prices_data = DailyPrice.objects.filter(
            stock=stock,
            date__gte=start_date
        ).order_by('date').values('date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume')

        if not prices_data:
            return Response(
                {'error': f'No price data available for {symbol}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # DataFrame 생성 및 컬럼명 변경
        df = pd.DataFrame(list(prices_data))
        # 컬럼명을 지표 계산에 맞게 변경
        df.rename(columns={
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close'
        }, inplace=True)

        # 모든 지표 계산
        indicators = TechnicalIndicators.calculate_all_indicators(df)
        indicators['price'] = float(stock.real_time_price) if stock.real_time_price else float(df['close'].iloc[-1])

        # 종합 신호 생성
        composite_signal = IndicatorSignals.get_composite_signal(indicators)

        signal_data = {
            'symbol': symbol,
            'stock_name': stock.stock_name,
            'current_price': indicators['price'],
            **composite_signal,
            'recommendation': self._get_recommendation(composite_signal['composite_signal']),
            'confidence': self._calculate_confidence(composite_signal)
        }

        # 캐시에 저장 (1분)
        cache.set(cache_key, signal_data, 60)

        return Response(signal_data)

    def _get_recommendation(self, signal):
        """신호에 따른 추천 문구 생성"""
        recommendations = {
            'strong_buy': '강력 매수 - 여러 지표가 매수 신호를 보이고 있습니다.',
            'buy': '매수 - 기술적 지표가 긍정적입니다.',
            'neutral': '중립 - 명확한 방향성이 없습니다. 관망을 권합니다.',
            'sell': '매도 - 기술적 지표가 부정적입니다.',
            'strong_sell': '강력 매도 - 여러 지표가 매도 신호를 보이고 있습니다.'
        }
        return recommendations.get(signal, '신호 없음')

    def _calculate_confidence(self, composite_signal):
        """신호의 신뢰도 계산 (0-100%)"""
        buy_count = composite_signal.get('buy_count', 0) or 0
        sell_count = composite_signal.get('sell_count', 0) or 0
        total_signals = buy_count + sell_count

        if total_signals == 0:
            return 0

        # 일치하는 신호가 많을수록 신뢰도 증가
        if composite_signal.get('composite_signal') in ['strong_buy', 'strong_sell']:
            base_confidence = 80
        elif composite_signal.get('composite_signal') in ['buy', 'sell']:
            base_confidence = 60
        else:
            base_confidence = 40

        # 신호의 일관성에 따라 추가 점수
        consistency_bonus = (max(buy_count, sell_count) / 4) * 20

        return min(100, base_confidence + consistency_bonus)


class IndicatorComparisonView(APIView):
    """여러 종목의 기술적 지표 비교"""

    def post(self, request):
        """
        여러 종목의 주요 지표를 비교

        Request Body:
            {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "indicators": ["rsi", "macd"]
            }
        """
        symbols = request.data.get('symbols', [])
        indicators = request.data.get('indicators', ['rsi', 'macd'])

        if not symbols:
            return Response(
                {'error': 'No symbols provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        comparison_data = {
            'indicators': indicators,
            'stocks': []
        }

        for symbol in symbols:
            symbol = symbol.upper()

            try:
                stock = Stock.objects.get(symbol=symbol)
            except Stock.DoesNotExist:
                continue

            # 최근 50일 데이터
            prices = DailyPrice.objects.filter(
                stock=stock
            ).order_by('-date')[:50].values_list('close_price', flat=True)

            if not prices:
                continue

            prices_list = list(reversed([float(p) for p in prices]))

            stock_data = {
                'symbol': symbol,
                'stock_name': stock.stock_name,
                'current_price': float(stock.real_time_price) if stock.real_time_price else prices_list[-1],
                'indicators': {}
            }

            # RSI 계산
            if 'rsi' in indicators:
                rsi_values = TechnicalIndicators.calculate_rsi(prices_list)
                if rsi_values and rsi_values[-1] is not None:
                    stock_data['indicators']['rsi'] = rsi_values[-1]
                    stock_data['indicators']['rsi_signal'] = IndicatorSignals.get_rsi_signal(rsi_values[-1])

            # MACD 계산
            if 'macd' in indicators:
                macd_result = TechnicalIndicators.calculate_macd(prices_list)
                if macd_result['macd'] and macd_result['macd'][-1] is not None:
                    stock_data['indicators']['macd'] = macd_result['macd'][-1]
                    stock_data['indicators']['macd_signal_value'] = macd_result['signal'][-1] if macd_result['signal'][-1] else 0
                    stock_data['indicators']['macd_histogram'] = macd_result['histogram'][-1] if macd_result['histogram'][-1] else 0

            # 볼린저 밴드
            if 'bollinger' in indicators:
                bb_result = TechnicalIndicators.calculate_bollinger_bands(prices_list)
                if bb_result['percent_b'] and bb_result['percent_b'][-1] is not None:
                    stock_data['indicators']['bb_percent_b'] = bb_result['percent_b'][-1]
                    stock_data['indicators']['bb_bandwidth'] = bb_result['bandwidth'][-1] if bb_result['bandwidth'][-1] else 0

            comparison_data['stocks'].append(stock_data)

        return Response(comparison_data)