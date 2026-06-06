"""
Overview API serializers (PR-I).

소속: apps/market_pulse/api/serializers (app 레이어 응답 직렬화).
역할: 4 카드(Regime/Breadth/Sector/Concentration) + 일일 브리핑 + i18n 라벨을
  하나의 overview 응답으로 묶는 DRF Serializer 정의.
의존: schemas/* Pydantic 검증, i18n/labels.KO_LABELS.
소비처: views/overview.py.
"""

from __future__ import annotations

from rest_framework import serializers


class MetaSerializer(serializers.Serializer):
    status = serializers.CharField()
    status_reason = serializers.CharField(allow_blank=True)
    generated_at = serializers.DateTimeField()
    latency_ms = serializers.IntegerField()
    data_finalized = serializers.BooleanField()
    cache = serializers.CharField(allow_blank=True, required=False)


class TickerItemSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    last_close = serializers.FloatField(allow_null=True)
    change_pct = serializers.FloatField(allow_null=True)
    sector_group = serializers.CharField(allow_null=True)


class NewsItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    category = serializers.CharField()
    title = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    url = serializers.URLField()
    publisher = serializers.CharField(allow_blank=True)
    image_url = serializers.URLField(allow_blank=True, required=False)
    published_at = serializers.DateTimeField()
    tickers = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class AnomalyItemSerializer(serializers.Serializer):
    rule_id = serializers.CharField()
    headline = serializers.CharField()
    threshold = serializers.DictField()
    actual = serializers.FloatField()
    paired_news_id = serializers.IntegerField(allow_null=True)


class AnomalySectionSerializer(serializers.Serializer):
    mode = serializers.CharField()
    overview = serializers.CharField(allow_blank=True)
    sector_highlight = serializers.CharField(allow_blank=True)
    portfolio_action = serializers.CharField(allow_blank=True)
    fired = serializers.ListField(child=AnomalyItemSerializer(), allow_empty=True)


class RegimeCardSerializer(serializers.Serializer):
    regime = serializers.CharField()
    status = serializers.CharField()
    coverage = serializers.FloatField()
    headline = serializers.CharField(allow_blank=True)
    fired_rules = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    transitioned = serializers.BooleanField()


class BreadthCardSerializer(serializers.Serializer):
    universe = serializers.CharField()
    advance = serializers.IntegerField()
    decline = serializers.IntegerField()
    unchanged = serializers.IntegerField()
    total = serializers.IntegerField()
    new_high_52w = serializers.IntegerField()
    new_low_52w = serializers.IntegerField()
    ad_line = serializers.IntegerField()
    ad_line_change = serializers.IntegerField()


class SectorCardItemSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    rel_strength = serializers.FloatField()
    rank = serializers.IntegerField()
    momentum_1d = serializers.FloatField()


class SectorCardSerializer(serializers.Serializer):
    leaders = serializers.ListField(child=SectorCardItemSerializer())
    laggards = serializers.ListField(child=SectorCardItemSerializer())
    cross_dispersion = serializers.FloatField()
    rotation_index = serializers.FloatField()


class ConcentrationHoldingSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    weight = serializers.FloatField()


class FlowCardSerializer(serializers.Serializer):
    universe = serializers.CharField()
    top5_weight = serializers.FloatField()
    top10_weight = serializers.FloatField()
    hhi = serializers.FloatField()
    top_holdings = serializers.ListField(
        child=ConcentrationHoldingSerializer(), allow_empty=True
    )


class BriefCardSerializer(serializers.Serializer):
    headline = serializers.CharField(allow_blank=True)
    content_preview = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    model_version = serializers.CharField(allow_blank=True)


class CardsSerializer(serializers.Serializer):
    regime = RegimeCardSerializer(allow_null=True)
    breadth = BreadthCardSerializer(allow_null=True)
    sector = SectorCardSerializer(allow_null=True)
    flow = FlowCardSerializer(allow_null=True)
    brief = BriefCardSerializer(allow_null=True)


class OverviewResponseSerializer(serializers.Serializer):
    _meta = MetaSerializer()
    ticker_bar = serializers.ListField(child=TickerItemSerializer(), allow_empty=True)
    news = serializers.ListField(child=NewsItemSerializer(), allow_empty=True)
    anomaly = AnomalySectionSerializer()
    cards = CardsSerializer()
