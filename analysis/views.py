from django.shortcuts import render

# Create your views here.
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Max, Min, Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ParseError

from .models import EconomicIndicator
from stocks.models import Stock, HistoricalPrice
from .serializers import EconomicIndicatorSerializer, IndicatorHistorySerializer

from datetime import datetime, timedelta

# 분석 대시보드 (메인 페이지)
class AnalysisDashboard(APIView):
    def get(self, request):
        # 최근 주요 경제 지표
        recent_indicators = EconomicIndicator.objects.order_by('-date')[:5]
        indicators_serializer = EconomicIndicatorSerializer(recent_indicators, many=True)
        
        # 시장 대표 주식들
        market_leaders = Stock.objects.filter(sector__isnull=False).order_by('-real_time_price')[:5]
        from stocks.serializers import StockSerializer
        market_leaders_serializer = StockSerializer(market_leaders, many=True)
        
        # 최근 거래일 기준 급등/급락 주식
        today = datetime.now().date()
        
        # 주식별 최근 가격 변동률 계산
        price_changes = []
        for stock in Stock.objects.all()[:50]:  # 상위 50개 주식만 확인 (성능 고려)
            try:
                latest_prices = HistoricalPrice.objects.filter(stock=stock).order_by('-date')[:2]
                if len(latest_prices) >= 2:
                    today_price = latest_prices[0].close_price
                    prev_price = latest_prices[1].close_price
                    change_percent = (today_price - prev_price) / prev_price * 100
                    
                    price_changes.append({
                        'stock_id': stock.id,
                        'stock_name': stock.name,
                        'stock_symbol': stock.symbol,
                        'change_percent': float(change_percent),
                        'today_price': float(today_price),
                        'prev_price': float(prev_price),
                        'date': latest_prices[0].date
                    })
            except Exception as e:
                continue
        
        # 급등주 (상위 5개)
        top_gainers = sorted(price_changes, key=lambda x: x['change_percent'], reverse=True)[:5]
        
        # 급락주 (하위 5개)
        top_losers = sorted(price_changes, key=lambda x: x['change_percent'])[:5]
        
        return Response({
            'recent_indicators': indicators_serializer.data,
            'market_leaders': market_leaders_serializer.data,
            'top_gainers': top_gainers,
            'top_losers': top_losers
        })

# 경제 지표 목록
class EconomicIndicatorList(APIView):
    def get(self, request):
        # 고유한 지표 이름 목록
        indicator_names = EconomicIndicator.objects.values_list('indicator_name', flat=True).distinct()
        
        latest_indicators = []
        for name in indicator_names:
            try:
                latest = EconomicIndicator.objects.filter(indicator_name=name).latest('date')
                latest_indicators.append(latest)
            except EconomicIndicator.DoesNotExist:
                continue
        
        serializer = EconomicIndicatorSerializer(latest_indicators, many=True)
        return Response(serializer.data)

# 경제 지표 상세
class EconomicIndicatorDetail(APIView):
    def get(self, request, pk):
        try:
            indicator = EconomicIndicator.objects.get(pk=pk)
        except EconomicIndicator.DoesNotExist:
            raise NotFound("Economic indicator not found")
        
        serializer = EconomicIndicatorSerializer(indicator)
        
        # 같은 지표의 과거 기록 (최대 12개월)
        history = EconomicIndicator.objects.filter(
            indicator_name=indicator.indicator_name
        ).order_by('-date')[:12]
        
        history_serializer = IndicatorHistorySerializer(history, many=True)
        
        return Response({
            'indicator': serializer.data,
            'history': history_serializer.data
        })

# 특정 지표의 히스토리
class IndicatorHistory(APIView):
    def get(self, request, indicator_name):
        # 기간 필터 처리
        months = int(request.query_params.get('months', 12))
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=months*30)
        
        indicators = EconomicIndicator.objects.filter(
            indicator_name=indicator_name,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        if not indicators.exists():
            raise NotFound(f"No data found for indicator: {indicator_name}")
        
        serializer = IndicatorHistorySerializer(indicators, many=True)
        
        latest = indicators.latest('date')
        
        return Response({
            'indicator_name': indicator_name,
            'unit': latest.unit,
            'latest_value': float(latest.value),
            'latest_date': latest.date,
            'data_points': serializer.data
        })

# 시장 트렌드 분석
class MarketTrends(APIView):
    def get(self, request):
        # 섹터별 성과 분석
        sectors = Stock.objects.exclude(
            sector__isnull=True
        ).values_list('sector', flat=True).distinct()
        
        sector_performance = []
        for sector in sectors:
            stocks = Stock.objects.filter(sector=sector)
            
            # 각 섹터별 평균 주가 변동률 계산
            sector_changes = []
            for stock in stocks:
                try:
                    recent_prices = HistoricalPrice.objects.filter(
                        stock=stock
                    ).order_by('-date')[:30]
                    
                    if len(recent_prices) >= 2:
                        first_price = recent_prices.last().close_price
                        last_price = recent_prices.first().close_price
                        change_percent = (last_price - first_price) / first_price * 100
                        sector_changes.append(float(change_percent))
                except Exception:
                    continue
            
            if sector_changes:
                avg_change = sum(sector_changes) / len(sector_changes)
                sector_performance.append({
                    'sector': sector,
                    'avg_change': avg_change,
                    'stock_count': len(stocks)
                })
        
        # 성과 순으로 정렬
        sector_performance.sort(key=lambda x: x['avg_change'], reverse=True)
        
        return Response({
            'sector_performance': sector_performance
        })

# 주식 비교 분석
class StockComparison(APIView):
    def get(self, request):
        # 비교할 주식 ID 목록
        stock_ids = request.query_params.getlist('stocks')
        period = request.query_params.get('period', '1y')
        
        if not stock_ids:
            raise ParseError("Please provide at least one stock ID")
        
        stocks = []
        for stock_id in stock_ids:
            try:
                stock = Stock.objects.get(id=stock_id)
                stocks.append(stock)
            except Stock.DoesNotExist:
                continue
        
        if not stocks:
            raise NotFound("No valid stocks found")
        
        # 기간에 따른 날짜 계산
        end_date = datetime.now().date()
        if period == '1m':
            start_date = end_date - timedelta(days=30)
        elif period == '3m':
            start_date = end_date - timedelta(days=90)
        elif period == '6m':
            start_date = end_date - timedelta(days=180)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == '5y':
            start_date = end_date - timedelta(days=365*5)
        else:
            start_date = end_date - timedelta(days=365)  # 기본값: 1년
        
        # 각 주식별 가격 및 성과 데이터 수집
        from stocks.serializers import StockSerializer, HistoricalPriceSerializer
        
        comparison_data = []
        for stock in stocks:
            prices = HistoricalPrice.objects.filter(
                stock=stock,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')
            
            if prices.exists():
                first_price = prices.first().close_price
                last_price = prices.last().close_price
                change_percent = (last_price - first_price) / first_price * 100
                
                price_serializer = HistoricalPriceSerializer(prices, many=True)
                
                comparison_data.append({
                    'stock': StockSerializer(stock).data,
                    'price_data': price_serializer.data,
                    'change_percent': float(change_percent),
                    'first_price': float(first_price),
                    'last_price': float(last_price)
                })
        
        return Response({
            'period': period,
            'comparison_data': comparison_data
        })