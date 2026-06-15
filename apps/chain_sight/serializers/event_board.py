"""
이벤트 보드 / 랭킹 시리얼라이저 (CS-RD2).
"""

from rest_framework import serializers


class EventBoardItemSerializer(serializers.Serializer):
    """테마 그룹 집계 1행."""

    theme = serializers.CharField()
    member_count = serializers.IntegerField()
    avg_return = serializers.FloatField()
    avg_score = serializers.FloatField()
    high_attention_count = serializers.IntegerField()
    low_attention_count = serializers.IntegerField()


class EventRankingItemSerializer(serializers.Serializer):
    """종목 랭킹 1행."""

    symbol = serializers.CharField()
    name = serializers.CharField()
    score = serializers.FloatField()
    raw_return = serializers.FloatField()
    volume_z = serializers.FloatField()
    volatility_pct = serializers.FloatField()
    is_low_liquidity = serializers.BooleanField()
