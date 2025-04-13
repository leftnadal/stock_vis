from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ParseError, ValidationError
from rest_framework.pagination import PageNumberPagination

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
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# 커스텀 예외 클래스
class DateFormatError(ValidationError):
    """날짜 형식 오류를 위한 커스텀 예외"""
    default_detail = "Invalid date format. Please use YYYY-MM-DD format."
    default_code = "invalid_date_format"

# 커스텀 페이지네이션 클래스
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# 공통 유틸리티 함수
def get_stock_or_404(stock_id):
    """주식 정보를 가져오거나 404 에러를 발생시키는 유틸리티 함수"""
    try:
        return Stock.objects.get(pk=stock_id)
    except Stock.DoesNotExist:
        raise NotFound(detail="Stock not found", code="stock_not_found")

def parse_date_param(date_str):
    """날짜 문자열을 파싱하는 유틸리티 함수"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise DateFormatError()

# 주식 목록 및 검색
class StockList(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        try:
            query = request.query_params.get('query', None)
            sector = request.query_params.get('sector', None)
            
            # 캐싱 키
            cache_key = f"stock_list:{query}:{sector}:{request.query_params.get('page', 1)}:{request.query_params.get('page_size', 20)}"
            cached_data = cache.get(cache_key)
            
            # 캐싱 데이터 반환
            if cached_data:
                return Response(cached_data)
            
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
            
            # DRF 페이지네이션 사용
            paginator = self.pagination_class()
            paginated_stocks = paginator.paginate_queryset(stocks, request)
            serializer = StockSerializer(paginated_stocks, many=True)
            
            # 결과를 캐시에 저장 (1시간 유효)
            cache.set(cache_key, serializer.data, 3600)
            
            return paginator.get_paginated_response(serializer.data)
        except ValueError:
            raise ParseError(detail="Invalid pagination parameters", code="invalid_pagination")
        except Exception as e:
            logger.error(f"Unexpected error in StockList view: {str(e)}")
            raise ValidationError(detail="An unexpected error occurred", code="unexpected_error")

# 주식 상세 정보
class StockDetail(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        cache_key = f"stock_detail:{pk}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        stock = get_stock_or_404(pk)
        serializer = StockDetailSerializer(stock)
        
        # 최근 가격 데이터 추가 - 쿼리 최적화
        recent_prices = HistoricalPrice.objects.filter(
            stock=stock
        ).order_by('-date')[:30]
        price_serializer = HistoricalPriceSerializer(recent_prices, many=True)
        
        financial_data = {}
        
        # 예외 처리
        try:
            financial_statements = {
                'balance_sheet': BalanceSheet.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year').first(),
                'income_statement': IncomeStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year').first(),
                'cash_flow': CashFlowStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year').first()
            }
            
            # 각 재무제표 직렬화
            for key, statement in financial_statements.items():
                if statement:
                    if key == 'balance_sheet':
                        financial_data[key] = BalanceSheetSerializer(statement).data
                    elif key == 'income_statement':
                        financial_data[key] = IncomeStatementSerializer(statement).data
                    elif key == 'cash_flow':
                        financial_data[key] = CashFlowStatementSerializer(statement).data
                else:
                    financial_data[key] = None
        except Exception as e:
            logger.error(f"Error fetching financial statements for stock {pk}: {str(e)}")
            financial_data = {
                'balance_sheet': None,
                'income_statement': None,
                'cash_flow': None,
                'error': "Unable to fetch financial statements"
            }
        
        response_data = {
            "stock": serializer.data,
            "recent_prices": price_serializer.data,
            **financial_data
        }
        
        # 응답 캐싱 (5분 유효)
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data)

# 주식 가격 이력
class StockPriceHistory(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, stock_id):
        # 유틸리티 함수 사용
        stock = get_stock_or_404(stock_id)
        
        # 날짜 필터링 - 개선된 에러 처리
        try:
            start_date = parse_date_param(request.query_params.get('start_date', None))
            end_date = parse_date_param(request.query_params.get('end_date', None))
            period = request.query_params.get('period', None)
            
            # 캐싱 키 생성
            cache_key = f"price_history:{stock_id}:{start_date}:{end_date}:{period}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response(cached_data)
            
            prices = HistoricalPrice.objects.filter(stock=stock)
            
            # 특정 기간 필터링 - timezone 인식 개선
            if period:
                today = timezone.now().date()  # timezone 인식 날짜 사용
                
                # 기간 매핑 테이블 - 코드 가독성 향상
                period_mapping = {
                    '1w': timedelta(days=7),
                    '1m': timedelta(days=30),
                    '3m': timedelta(days=90),
                    '6m': timedelta(days=180),
                    '1y': timedelta(days=365),
                    '5y': timedelta(days=365*5)
                }
                
                # 매핑 테이블에서 기간 가져오기
                delta = period_mapping.get(period, timedelta(days=30))
                start = today - delta
                    
                prices = prices.filter(date__gte=start)
            else:
                # 시작일, 종료일 직접 지정
                if start_date:
                    prices = prices.filter(date__gte=start_date)
                if end_date:
                    prices = prices.filter(date__lte=end_date)
            
            prices = prices.order_by('date')
            serializer = HistoricalPriceSerializer(prices, many=True)
            
            response_data = {
                "stock": {
                    "id": stock.id,
                    "name": stock.name,
                    "symbol": stock.symbol
                },
                "prices": serializer.data,
                "period": period,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
            
            # 응답 캐싱 (1시간 유효)
            cache.set(cache_key, response_data, 3600)
            
            return Response(response_data)
            
        except DateFormatError as e:
            # 커스텀 예외 사용
            raise e
        except Exception as e:
            logger.error(f"Error in StockPriceHistory view: {str(e)}")
            raise ValidationError(detail="Error retrieving price history", code="price_history_error")

# 재무제표 뷰를 위한 기본 클래스 - 코드 중복 감소
class BaseFinancialStatementView(APIView):
    permission_classes = [IsAuthenticated]
    statement_model = None
    serializer_class = None
    statement_name = ''
    
    def get(self, request, stock_id):
        stock = get_stock_or_404(stock_id)
        period_type = request.query_params.get('period_type', 'annual')
        
        # 캐싱 키
        cache_key = f"{self.statement_name}:{stock_id}:{period_type}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        try:
            statements = self.statement_model.objects.filter(
                stock=stock,
                period_type=period_type
            ).order_by('-fiscal_year', '-fiscal_quarter')
            
            serializer = self.serializer_class(statements, many=True)
            
            response_data = {
                "stock": {
                    "id": stock.id,
                    "name": stock.name,
                    "symbol": stock.symbol
                },
                "period_type": period_type,
                f"{self.statement_name}s": serializer.data
            }
            
            # 응답 캐싱 (1일 유효 - 재무제표는 자주 변경되지 않음)
            cache.set(cache_key, response_data, 86400)
            
            return Response(response_data)
        except Exception as e:
            logger.error(f"Error fetching {self.statement_name} for stock {stock_id}: {str(e)}")
            raise ValidationError(
                detail=f"Error retrieving {self.statement_name} data", 
                code=f"{self.statement_name}_error"
            )

# 재무제표: 대차대조표 - 상속 사용
class StockBalanceSheet(BaseFinancialStatementView):
    statement_model = BalanceSheet
    serializer_class = BalanceSheetSerializer
    statement_name = 'balance_sheet'

# 재무제표: 손익계산서 - 상속 사용
class StockIncomeStatement(BaseFinancialStatementView):
    statement_model = IncomeStatement
    serializer_class = IncomeStatementSerializer
    statement_name = 'income_statement'

# 재무제표: 현금흐름표 - 상속 사용
class StockCashFlow(BaseFinancialStatementView):
    statement_model = CashFlowStatement
    serializer_class = CashFlowStatementSerializer
    statement_name = 'cash_flow'