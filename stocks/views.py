##1차 작성중

from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ParseError

from .models import Stock, HistoricalPrice, BalanceSheet, IncomeStatement, CashFlowStatement
from .serializers import (
    StockSerializer, 
    StockDetailSerializer, 
    HistoricalPriceSerializer,
    BalanceSheetSerializer,
    IncomeStatementSerializer,
    CashFlowStatementSerializer
)
from datetime import datetime, timedelta

# 주식 목록 및 검색
class StockList(APIView):
    def get(self, request):
        query = request.query_params.get('query', None)
        sector = request.query_params.get('sector', None)
        
        stocks = Stock.objects.all()
        
        # 검색 기능
        if query:
            stocks = stocks.filter(
                Q(name__icontains=query) | 
                Q(symbol__icontains=query)
            )
            
        # 섹터 필터링
        if sector:
            stocks = stocks.filter(sector=sector)
        
        # 페이지네이션 (간단 구현)
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        stocks = stocks[start:end]
        serializer = StockSerializer(stocks, many=True)
        
        return Response(serializer.data)

# 주식 상세 정보
class StockDetail(APIView):
    def get(self, request, pk):
        try:
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        serializer = StockDetailSerializer(stock)
        
        # 최근 가격 데이터 추가
        recent_prices = HistoricalPrice.objects.filter(
            stock=stock
        ).order_by('-date')[:30]
        price_serializer = HistoricalPriceSerializer(recent_prices, many=True)
        
        # 최근 재무제표 추가
        try:
            latest_balance_sheet = BalanceSheet.objects.filter(
                stock=stock, 
                period_type='annual'
            ).latest('fiscal_year')
            balance_sheet_serializer = BalanceSheetSerializer(latest_balance_sheet)
            balance_sheet_data = balance_sheet_serializer.data
        except BalanceSheet.DoesNotExist:
            balance_sheet_data = None
            
        try:
            latest_income_statement = IncomeStatement.objects.filter(
                stock=stock, 
                period_type='annual'
            ).latest('fiscal_year')
            income_statement_serializer = IncomeStatementSerializer(latest_income_statement)
            income_statement_data = income_statement_serializer.data
        except IncomeStatement.DoesNotExist:
            income_statement_data = None
            
        try:
            latest_cash_flow = CashFlowStatement.objects.filter(
                stock=stock, 
                period_type='annual'
            ).latest('fiscal_year')
            cash_flow_serializer = CashFlowStatementSerializer(latest_cash_flow)
            cash_flow_data = cash_flow_serializer.data
        except CashFlowStatement.DoesNotExist:
            cash_flow_data = None
        
        response_data = {
            "stock": serializer.data,
            "recent_prices": price_serializer.data,
            "balance_sheet": balance_sheet_data,
            "income_statement": income_statement_data,
            "cash_flow": cash_flow_data
        }
        
        # 관련 뉴스 추가
        try:
            from news.models import NewsArticle
            from news.serializers import NewsArticleSerializer
            
            recent_news = NewsArticle.objects.filter(
                stock=stock
            ).order_by('-published_at')[:5]
            news_serializer = NewsArticleSerializer(recent_news, many=True)
            response_data["recent_news"] = news_serializer.data
        except:
            pass
        
        return Response(response_data)

# 주식 가격 이력
class StockPriceHistory(APIView):
    def get(self, request, stock_id):
        try:
            stock = Stock.objects.get(pk=stock_id)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        # 날짜 필터링
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        period = request.query_params.get('period', None)
        
        prices = HistoricalPrice.objects.filter(stock=stock)
        
        # 특정 기간 필터링
        if period:
            today = datetime.now().date()
            if period == '1w':
                start = today - timedelta(days=7)
            elif period == '1m':
                start = today - timedelta(days=30)
            elif period == '3m':
                start = today - timedelta(days=90)
            elif period == '6m':
                start = today - timedelta(days=180)
            elif period == '1y':
                start = today - timedelta(days=365)
            elif period == '5y':
                start = today - timedelta(days=365*5)
            else:
                start = today - timedelta(days=30)  # 기본값: 1개월
                
            prices = prices.filter(date__gte=start)
        else:
            # 시작일, 종료일 직접 지정
            if start_date:
                prices = prices.filter(date__gte=start_date)
            if end_date:
                prices = prices.filter(date__lte=end_date)
        
        prices = prices.order_by('date')
        serializer = HistoricalPriceSerializer(prices, many=True)
        
        return Response({
            "stock": {
                "id": stock.id,
                "name": stock.name,
                "symbol": stock.symbol
            },
            "prices": serializer.data
        })

# 재무제표: 대차대조표
class StockBalanceSheet(APIView):
    def get(self, request, stock_id):
        try:
            stock = Stock.objects.get(pk=stock_id)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        period_type = request.query_params.get('period_type', 'annual')
        
        balance_sheets = BalanceSheet.objects.filter(
            stock=stock,
            period_type=period_type
        ).order_by('-fiscal_year', '-fiscal_quarter')
        
        serializer = BalanceSheetSerializer(balance_sheets, many=True)
        
        return Response({
            "stock": {
                "id": stock.id,
                "name": stock.name,
                "symbol": stock.symbol
            },
            "period_type": period_type,
            "balance_sheets": serializer.data
        })

# 재무제표: 손익계산서
class StockIncomeStatement(APIView):
    def get(self, request, stock_id):
        try:
            stock = Stock.objects.get(pk=stock_id)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        period_type = request.query_params.get('period_type', 'annual')
        
        income_statements = IncomeStatement.objects.filter(
            stock=stock,
            period_type=period_type
        ).order_by('-fiscal_year', '-fiscal_quarter')
        
        serializer = IncomeStatementSerializer(income_statements, many=True)
        
        return Response({
            "stock": {
                "id": stock.id,
                "name": stock.name,
                "symbol": stock.symbol
            },
            "period_type": period_type,
            "income_statements": serializer.data
        })

# 재무제표: 현금흐름표
class StockCashFlow(APIView):
    def get(self, request, stock_id):
        try:
            stock = Stock.objects.get(pk=stock_id)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        period_type = request.query_params.get('period_type', 'annual')
        
        cash_flows = CashFlowStatement.objects.filter(
            stock=stock,
            period_type=period_type
        ).order_by('-fiscal_year', '-fiscal_quarter')
        
        serializer = CashFlowStatementSerializer(cash_flows, many=True)
        
        return Response({
            "stock": {
                "id": stock.id,
                "name": stock.name,
                "symbol": stock.symbol
            },
            "period_type": period_type,
            "cash_flows": serializer.data
        })