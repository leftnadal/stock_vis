"""
거시경제 데이터 Serializers
"""
from rest_framework import serializers
from .models import (
    EconomicIndicator,
    IndicatorValue,
    MarketIndex,
    MarketIndexPrice,
    EconomicEvent,
)


class EconomicIndicatorSerializer(serializers.ModelSerializer):
    """경제 지표 시리얼라이저"""

    class Meta:
        model = EconomicIndicator
        fields = [
            'code', 'name', 'name_ko', 'description',
            'category', 'data_source', 'update_frequency',
            'unit', 'last_updated'
        ]


class IndicatorValueSerializer(serializers.ModelSerializer):
    """지표 값 시리얼라이저"""
    indicator_code = serializers.CharField(source='indicator.code', read_only=True)

    class Meta:
        model = IndicatorValue
        fields = ['indicator_code', 'date', 'value', 'period', 'is_preliminary']


class MarketIndexSerializer(serializers.ModelSerializer):
    """시장 지수 시리얼라이저"""

    class Meta:
        model = MarketIndex
        fields = ['symbol', 'name', 'name_ko', 'category']


class MarketIndexPriceSerializer(serializers.ModelSerializer):
    """지수 가격 시리얼라이저"""
    index_symbol = serializers.CharField(source='index.symbol', read_only=True)

    class Meta:
        model = MarketIndexPrice
        fields = [
            'index_symbol', 'date', 'open', 'high', 'low', 'close',
            'change', 'change_percent'
        ]


class EconomicEventSerializer(serializers.ModelSerializer):
    """경제 이벤트 시리얼라이저"""
    surprise = serializers.ReadOnlyField()

    class Meta:
        model = EconomicEvent
        fields = [
            'event_id', 'title', 'title_ko', 'event_date', 'event_time',
            'importance', 'country', 'previous_value', 'forecast_value',
            'actual_value', 'surprise', 'description'
        ]


# ============================================================================
# Dashboard Response Serializers (API 응답용)
# ============================================================================

class FearGreedResponseSerializer(serializers.Serializer):
    """공포/탐욕 지수 응답"""
    value = serializers.IntegerField()
    rule_key = serializers.CharField()
    label = serializers.CharField()
    label_en = serializers.CharField(required=False)
    color = serializers.CharField()
    message = serializers.CharField()
    action_hint = serializers.CharField(required=False)
    vix = serializers.DictField(required=False)
    yield_spread = serializers.DictField(required=False)
    last_updated = serializers.CharField()


class InterestRatesResponseSerializer(serializers.Serializer):
    """금리 대시보드 응답"""
    fed_funds_rate = serializers.FloatField(allow_null=True)
    treasury_2y = serializers.FloatField(allow_null=True)
    treasury_10y = serializers.FloatField(allow_null=True)
    yield_spread = serializers.DictField()
    yield_curve_status = serializers.DictField()
    yield_curve_data = serializers.ListField()
    last_updated = serializers.CharField()


class InflationResponseSerializer(serializers.Serializer):
    """인플레이션 대시보드 응답"""
    inflation = serializers.DictField()
    employment = serializers.DictField()
    gdp = serializers.DictField(allow_null=True)
    last_updated = serializers.CharField()


class GlobalMarketsResponseSerializer(serializers.Serializer):
    """글로벌 시장 대시보드 응답"""
    indices = serializers.DictField()
    global_indices = serializers.DictField()
    sectors = serializers.DictField()
    forex = serializers.DictField()
    commodities = serializers.DictField()
    dxy = serializers.DictField(allow_null=True)
    vix = serializers.DictField(allow_null=True)
    last_updated = serializers.CharField()


class EconomicCalendarResponseSerializer(serializers.Serializer):
    """경제 캘린더 응답"""
    events_by_date = serializers.DictField()
    total_count = serializers.IntegerField()
    from_date = serializers.CharField()
    to_date = serializers.CharField()
    last_updated = serializers.CharField()


class MarketPulseResponseSerializer(serializers.Serializer):
    """Market Pulse 전체 대시보드 응답"""
    fear_greed = serializers.DictField()
    interest_rates = serializers.DictField()
    economy = serializers.DictField()
    global_markets = serializers.DictField()
    calendar = serializers.DictField()
    last_updated = serializers.CharField()
