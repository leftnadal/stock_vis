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
    """종목 랭킹 1행.

    M1 필드(symbol·name·score·raw_return·volume_z·volatility_pct·
    is_low_liquidity)는 불변 — RD3 회귀 0.

    CS-M2 주도주 지표(선택된 window의 StockLeadershipScore)는 게이트 미달 시
    NULL 가능 → allow_null. 데이터 미존재 시 키는 노출하되 값 None.
    """

    # ── M1 (불변) ──
    symbol = serializers.CharField()
    name = serializers.CharField()
    score = serializers.FloatField()
    raw_return = serializers.FloatField()
    volume_z = serializers.FloatField()
    volatility_pct = serializers.FloatField()
    is_low_liquidity = serializers.BooleanField()

    # ── CS-M2 주도주 지표 (선택 window) ──
    trend_quality = serializers.FloatField(allow_null=True, required=False)
    theme_alpha = serializers.FloatField(allow_null=True, required=False)
    theme_beta = serializers.FloatField(allow_null=True, required=False)
    up_capture = serializers.FloatField(allow_null=True, required=False)
    down_capture = serializers.FloatField(allow_null=True, required=False)
    capture_spread = serializers.FloatField(allow_null=True, required=False)
    is_fallback = serializers.BooleanField(required=False)
