from django.shortcuts import render

# Create your views here.
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ParseError

from .models import NewsArticle
from stocks.models import Stock
from .serializers import NewsArticleSerializer, NewsArticleListSerializer

# 모든 뉴스 목록
class NewsList(APIView):
    def get(self, request):
        # 필터링 파라미터
        query = request.query_params.get('query', None)
        stock_id = request.query_params.get('stock_id', None)
        stock_symbol = request.query_params.get('symbol', None)
        source = request.query_params.get('source', None)
        
        news = NewsArticle.objects.all().order_by('-published_at')
        
        # 검색어로 필터링
        if query:
            news = news.filter(
                Q(title__icontains=query) | 
                Q(content__icontains=query)
            )
        
        # 특정 주식으로 필터링
        if stock_id:
            news = news.filter(stock_id=stock_id)
        
        # 주식 심볼로 필터링
        if stock_symbol:
            news = news.filter(stock__symbol=stock_symbol)
        
        # 출처로 필터링
        if source:
            news = news.filter(source=source)
        
        # 페이지네이션 (간단 구현)
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = news.count()
        news = news[start:end]
        
        serializer = NewsArticleListSerializer(news, many=True)
        
        return Response({
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "results": serializer.data
        })

# 뉴스 상세 보기
class NewsDetail(APIView):
    def get(self, request, pk):
        try:
            news_article = NewsArticle.objects.get(pk=pk)
        except NewsArticle.DoesNotExist:
            raise NotFound("News article not found")
        
        serializer = NewsArticleSerializer(news_article)
        
        # 연관 뉴스 (같은 주식에 대한 다른 뉴스)
        related_news = NewsArticle.objects.filter(
            stock=news_article.stock
        ).exclude(id=news_article.id).order_by('-published_at')[:5]
        
        related_serializer = NewsArticleListSerializer(related_news, many=True)
        
        return Response({
            "article": serializer.data,
            "related_news": related_serializer.data
        })

# 특정 주식에 대한 뉴스
class StockNews(APIView):
    def get(self, request, stock_id):
        try:
            stock = Stock.objects.get(pk=stock_id)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        news = NewsArticle.objects.filter(stock=stock).order_by('-published_at')
        
        # 페이지네이션 (간단 구현)
        page_size = int(request.query_params.get('page_size', 15))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = news.count()
        news = news[start:end]
        
        serializer = NewsArticleListSerializer(news, many=True)
        
        return Response({
            "stock": {
                "id": stock.id,
                "name": stock.name,
                "symbol": stock.symbol
            },
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "results": serializer.data
        })

# 최신 뉴스
class LatestNews(APIView):
    def get(self, request):
        count = int(request.query_params.get('count', 10))
        latest_news = NewsArticle.objects.all().order_by('-published_at')[:count]
        
        serializer = NewsArticleListSerializer(latest_news, many=True)
        
        return Response(serializer.data)