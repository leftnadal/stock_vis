"""
뉴스 API Serializers
"""

from rest_framework import serializers
from ..models import NewsArticle, NewsEntity, EntityHighlight, SentimentHistory


class EntityHighlightSerializer(serializers.ModelSerializer):
    """엔티티 하이라이트 Serializer"""

    class Meta:
        model = EntityHighlight
        fields = ['highlight_text', 'sentiment', 'location']


class NewsEntitySerializer(serializers.ModelSerializer):
    """뉴스 엔티티 Serializer (상세)"""
    highlights = EntityHighlightSerializer(many=True, read_only=True)

    class Meta:
        model = NewsEntity
        fields = [
            'symbol',
            'entity_name',
            'entity_type',
            'exchange',
            'country',
            'industry',
            'match_score',
            'sentiment_score',
            'source',
            'highlights'
        ]


class NewsEntitySimpleSerializer(serializers.ModelSerializer):
    """뉴스 엔티티 Serializer (간단)"""

    class Meta:
        model = NewsEntity
        fields = ['symbol', 'entity_name', 'sentiment_score']


class NewsArticleListSerializer(serializers.ModelSerializer):
    """뉴스 리스트용 Serializer (간단)"""
    entities = NewsEntitySimpleSerializer(many=True, read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            'id',
            'url',
            'title',
            'summary',
            'image_url',
            'source',
            'published_at',
            'category',
            'sentiment_score',
            'sentiment_source',
            'is_press_release',
            'entities'
        ]


class NewsArticleDetailSerializer(serializers.ModelSerializer):
    """뉴스 상세용 Serializer"""
    entities = NewsEntitySerializer(many=True, read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            'id',
            'url',
            'title',
            'summary',
            'image_url',
            'source',
            'published_at',
            'language',
            'category',
            'finnhub_id',
            'marketaux_uuid',
            'sentiment_score',
            'sentiment_source',
            'is_press_release',
            'entities',
            'created_at',
            'updated_at'
        ]


class SentimentHistorySerializer(serializers.ModelSerializer):
    """감성 히스토리 Serializer"""

    class Meta:
        model = SentimentHistory
        fields = [
            'symbol',
            'date',
            'avg_sentiment',
            'news_count',
            'positive_count',
            'negative_count',
            'neutral_count'
        ]


class SentimentSummarySerializer(serializers.Serializer):
    """감성 분석 요약 Serializer (계산된 데이터)"""
    symbol = serializers.CharField()
    period = serializers.CharField()  # e.g., "7d", "30d"
    avg_sentiment = serializers.DecimalField(max_digits=4, decimal_places=3)
    news_count = serializers.IntegerField()
    positive_count = serializers.IntegerField()
    negative_count = serializers.IntegerField()
    neutral_count = serializers.IntegerField()
    sentiment_trend = serializers.CharField()  # "improving", "declining", "stable"


class TrendingStockSerializer(serializers.Serializer):
    """트렌딩 종목 Serializer (계산된 데이터)"""
    symbol = serializers.CharField()
    news_count = serializers.IntegerField()
    avg_sentiment = serializers.DecimalField(max_digits=4, decimal_places=3)
    recent_articles = NewsArticleListSerializer(many=True)
