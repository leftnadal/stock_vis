"""
Market Movers Serializers

FMP API Market Movers 데이터를 위한 Serializer
상승/하락/거래량 TOP 종목 데이터 직렬화
"""
from rest_framework import serializers


class MarketMoverSerializer(serializers.Serializer):
    """
    시장 주도 종목 Serializer

    FMP API 응답 필드:
    - symbol: 종목 심볼
    - name: 회사명
    - price: 현재 가격
    - change: 가격 변동
    - changesPercentage: 변동률 (%)
    - exchange: 거래소 (NASDAQ, NYSE 등)
    """
    symbol = serializers.CharField()
    name = serializers.CharField()
    price = serializers.FloatField()
    change = serializers.FloatField()
    changes_percentage = serializers.FloatField(source='changesPercentage')
    exchange = serializers.CharField(required=False, allow_null=True)

    # 추가 계산 필드
    direction = serializers.SerializerMethodField()
    formatted_change = serializers.SerializerMethodField()

    def get_direction(self, obj) -> str:
        """
        변동 방향 반환

        Returns:
            'up' (상승) 또는 'down' (하락)
        """
        return 'up' if obj.get('change', 0) >= 0 else 'down'

    def get_formatted_change(self, obj) -> str:
        """
        포맷된 변동률 문자열

        Returns:
            예: '+5.23%', '-2.15%'
        """
        pct = obj.get('changesPercentage', 0)
        sign = '+' if pct >= 0 else ''
        return f"{sign}{pct:.2f}%"


class MarketMoversResponseSerializer(serializers.Serializer):
    """
    Market Movers API 전체 응답 Serializer

    전체 응답 구조:
    - gainers: 상승 TOP 종목
    - losers: 하락 TOP 종목
    - actives: 거래량 TOP 종목
    - cached_at: 캐시 생성 시간
    - last_updated: API 응답 생성 시간
    """
    gainers = MarketMoverSerializer(many=True)
    losers = MarketMoverSerializer(many=True)
    actives = MarketMoverSerializer(many=True)
    cached_at = serializers.CharField(allow_null=True)
    last_updated = serializers.DateTimeField()
