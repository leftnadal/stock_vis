"""
Exchange Quotes Serializers

FMP API Exchange Quotes 데이터를 위한 Serializer
실시간 시세 정보 직렬화
"""
from rest_framework import serializers


class QuoteSerializer(serializers.Serializer):
    """
    실시간 시세 Serializer

    FMP API /quote 응답 필드
    """
    # 기본 정보
    symbol = serializers.CharField()
    name = serializers.CharField(required=False)
    exchange = serializers.CharField(allow_null=True, required=False)

    # 가격 정보
    price = serializers.FloatField(allow_null=True)
    change = serializers.FloatField(allow_null=True, required=False)
    changes_percentage = serializers.FloatField(source='changesPercentage', allow_null=True, required=False)

    # 가격 범위
    day_low = serializers.FloatField(source='dayLow', allow_null=True, required=False)
    day_high = serializers.FloatField(source='dayHigh', allow_null=True, required=False)
    year_low = serializers.FloatField(source='yearLow', allow_null=True, required=False)
    year_high = serializers.FloatField(source='yearHigh', allow_null=True, required=False)

    # 시가/종가
    open = serializers.FloatField(allow_null=True, required=False)
    previous_close = serializers.FloatField(source='previousClose', allow_null=True, required=False)

    # 거래량
    volume = serializers.IntegerField(allow_null=True, required=False)
    avg_volume = serializers.IntegerField(source='avgVolume', allow_null=True, required=False)

    # 기업 정보
    market_cap = serializers.FloatField(source='marketCap', allow_null=True, required=False)
    shares_outstanding = serializers.FloatField(source='sharesOutstanding', allow_null=True, required=False)

    # 밸류에이션
    pe = serializers.FloatField(allow_null=True, required=False)
    eps = serializers.FloatField(allow_null=True, required=False)

    # 시간 정보
    timestamp = serializers.IntegerField(allow_null=True, required=False)

    # 계산 필드
    direction = serializers.SerializerMethodField()
    formatted_change = serializers.SerializerMethodField()
    day_range_percentage = serializers.SerializerMethodField()

    def get_direction(self, obj) -> str:
        """
        변동 방향 반환

        Returns:
            'up' (상승), 'down' (하락), 'neutral' (보합)
        """
        change = obj.get('change', 0)
        if change > 0:
            return 'up'
        elif change < 0:
            return 'down'
        else:
            return 'neutral'

    def get_formatted_change(self, obj) -> str:
        """
        포맷된 변동률 문자열

        Returns:
            예: '+5.23%', '-2.15%', '0.00%'
        """
        pct = obj.get('changesPercentage', 0)
        if pct > 0:
            return f"+{pct:.2f}%"
        else:
            return f"{pct:.2f}%"

    def get_day_range_percentage(self, obj) -> float:
        """
        일중 변동 범위 대비 현재가 위치 (%)

        Returns:
            0 ~ 100 (0: 최저가, 100: 최고가)
        """
        price = obj.get('price')
        day_low = obj.get('dayLow')
        day_high = obj.get('dayHigh')

        if not all([price, day_low, day_high]) or day_high == day_low:
            return 50.0  # 기본값 (중간)

        return ((price - day_low) / (day_high - day_low)) * 100


class IndexQuoteSerializer(serializers.Serializer):
    """
    지수 시세 Serializer

    FMP API /quotes/index 응답 필드
    """
    symbol = serializers.CharField()
    name = serializers.CharField(required=False)
    price = serializers.FloatField(allow_null=True)
    change = serializers.FloatField(allow_null=True, required=False)
    changes_percentage = serializers.FloatField(source='changesPercentage', allow_null=True, required=False)
    day_low = serializers.FloatField(source='dayLow', allow_null=True, required=False)
    day_high = serializers.FloatField(source='dayHigh', allow_null=True, required=False)
    year_low = serializers.FloatField(source='yearLow', allow_null=True, required=False)
    year_high = serializers.FloatField(source='yearHigh', allow_null=True, required=False)
    open = serializers.FloatField(allow_null=True, required=False)
    previous_close = serializers.FloatField(source='previousClose', allow_null=True, required=False)

    # 계산 필드
    direction = serializers.SerializerMethodField()
    formatted_change = serializers.SerializerMethodField()

    def get_direction(self, obj) -> str:
        """변동 방향"""
        change = obj.get('change', 0)
        return 'up' if change >= 0 else 'down'

    def get_formatted_change(self, obj) -> str:
        """포맷된 변동률"""
        pct = obj.get('changesPercentage', 0)
        sign = '+' if pct >= 0 else ''
        return f"{sign}{pct:.2f}%"


class MajorIndicesSerializer(serializers.Serializer):
    """
    주요 지수 응답 Serializer
    """
    sp500 = IndexQuoteSerializer(allow_null=True)
    nasdaq = IndexQuoteSerializer(allow_null=True)
    dow_jones = IndexQuoteSerializer(allow_null=True)


class SectorPerformanceSerializer(serializers.Serializer):
    """
    섹터 성과 Serializer (섹터 ETF 기반)
    """
    sectors = QuoteSerializer(many=True)


class BatchQuotesResponseSerializer(serializers.Serializer):
    """
    일괄 시세 조회 응답 Serializer
    """
    quotes = QuoteSerializer(many=True)
    total_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
