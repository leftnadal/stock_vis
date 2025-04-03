##1차 작성중

from rest_framework import serializers
from .models import NewsArticle
from stocks.serializers import StockSerializer

class NewsArticleSerializer(serializers.ModelSerializer):
    stock_info = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsArticle
        fields = ['id', 'title', 'content', 'source', 'published_at', 'url', 'stock', 'stock_info']
    
    def get_stock_info(self, obj):
        return {
            'id': obj.stock.id,
            'name': obj.stock.name,
            'symbol': obj.stock.symbol
        }

class NewsArticleListSerializer(serializers.ModelSerializer):
    stock_info = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsArticle
        fields = ['id', 'title', 'source', 'published_at', 'stock', 'stock_info']
    
    def get_stock_info(self, obj):
        return {
            'id': obj.stock.id,
            'name': obj.stock.name,
            'symbol': obj.stock.symbol
        }