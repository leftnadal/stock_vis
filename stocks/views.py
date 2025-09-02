import json
import logging

from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView, DetailView
from django.http import JsonResponse, Http404

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement
from .serializers import StockListSerializer, StockHeaderSerializer, StockDetailPageSerializer, StockSearchSerializer, WatchListStockSerializer, WeeklyChartDataSerializer, ChartDataSerializer, OverviewTabSerializer

logger = logging.getLogger(__name__)
### 메인 대시보드
class DashboardView(TemplateView):
    """
        ## 대시보드 ( 주요 섹터, 관심 주식 가격 등)
        # - 주요 섹터별 주식과 시가총액 상위 주식들을 보여주는 페이지
        # - React 프론트엔드로 전환 시에는 사용하지 않을 예정
    """

    template_name= 'stocks/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        ## 시가총액 상위 10개 주식 조회
        # 시가총액이 null이 아닌 주식들을 시가총액 내림차순으로 정렬하여 상위 10개 조회
        # - market_capitalization__isnull=False: 시가총액이 비어있지 않은 주식만 필터링
        # - order_by('-market_capitalization'): 시가총액 기준 내림차순 정렬
        top_stocks = Stock.objects.filter(market_capitalization__isnull=False).order_by('-market_capitalization')[:10]

        context.update({'top_stocks' : top_stocks,})

        return context

### 주식 목록 API
class StockListAPIView(generics.ListAPIView):
    """
        ## 주식 목록 조희 API
        # - 전체 주식목록을 pagination으로 조회
        # - 섹터별, 시가총액별 필터링 지원
    """
    serializer_class = StockListSerializer

    def get_request(self, request):
        queryset = Stock.objects.all()

        # 필터링 파라미터들
        # - sector: 특정 섹터의 주식들만 조회
        # - min_cap: 최소 시가총액 이상의 주식들만 조회

        sector = self.request.GET.get('sector')
        min_market_cap = self.request.GET.get('sort_by', 'market_cap')

        if sector:
            queryset = queryset.filter(sector_icontains = sector)
        
        if min_market_cap:
            try:
                min_cap_value = float(min_market_cap)
                queryset = queryset.filter(market_capitalization__gte = min_cap_value)
            except ValueError:
                pass

        ## 시가총액 기준 내림차순 정렬     
        return queryset.order_by('-market_capitalization')
    
### 개별 주식 상세 페이지
class StockDetailView(DetailView):
    """
    개별 주식 상세 페이지
    - 주식 기본 정보, 차트, 재무제표 등을 통합 표시
    - URL에서 symbol 파라미터를 받아서 해당 주식 정보 조회
    - 1번 영역(헤더), 2번 영역(차트), 3번 영역(탭 메뉴)을 모두 포함하는 메인 페이지
    """
    model = Stock
    template_name = 'stocks/stock_detail.html'
    slug_field = 'symbol'  # 모델의 어떤 필드로 조회할지 지정
    slug_url_kwarg = 'symbol'  # URL 패턴의 <str:symbol> 부분과 매핑
    context_object_name = 'stock'  # 템플릿에서 사용할 객체 이름

    def get_object(self, queryset=None):
        """
        주식 심볼을 대문자로 변환하여 조회
        - 대소문자 구분 없이 조회 가능하도록 대문자로 변환 처리
        """
        symbol = self.kwargs.get['symbol',''].upper()
        try:
            return Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            raise Http404(f"주식 '{symbol}'을 찾을 수 없습니다.")

    def get_context_data(self, **kwargs):
        """
        템플릿에 전달할 컨텍스트 데이터 구성
        - 헤더, 초기 차트 데이터, Overview 탭 데이터를 포함
        """
        context = super().get_context_data(**kwargs)
        stock = self.object
        
        # 1번 영역: 헤더 정보용 데이터 (주식명, 가격, 변동률 등)
        # - StockHeaderSerializer를 사용하여 헤더에 필요한 정보만 직렬화
        context['stock_header'] = StockHeaderSerializer(stock).data
        
        # 2번 영역: 초기 차트 데이터 (최근 30일간의 일일 가격 데이터)
        # - 나머지 기간별 차트 데이터는 AJAX로 동적 로딩
        recent_daily_prices = DailyPrice.objects.filter(
            stock=stock
        ).order_by('-date')[:30]  # 최근 30일
        context['initial_chart_data'] = ChartDataSerializer(recent_daily_prices, many=True).data
        
        # 3번 영역: 탭별 초기 데이터 (Overview 탭을 기본으로 표시)
        # - 다른 탭들(Balance Sheet, Income Statement 등)은 AJAX로 로딩
        context['overview_data'] = OverviewTabSerializer(stock).data

        return context


### 주식 검색 API    
class StockSearchView(APIView):
    """
        ### 주식 검색 API
        # - 주식 심볼이나 회사명으로 검색
        # - 자동완성 기능을 위한 간단한 정보 변환
    """

    def get(self, request):
        # 검색어 파라미터 받기
        # - 'q' 파라미터로 검색어를 받음 (예: /search/?q=apple)
        query = request.Get.get("q", "").strip()
        
        if not query:
            return Response({
                'result': [],
                'message': '검색어를 입력해주세요',
                
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 너무 짧은 검색어 처리
        if len(query) < 2:
            return Response({
                'results': [],
                'message': '검색어는 2자 이상 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 검색 실행
            # - 주식명 또는 심볼에서 검색어가 포함된 주식들을 조회
            # - 대소문자 구분 없이 검색 (icontains)

            stocks = Stock.objects.filter(
                Q(stock_name__icontains = query) | Q(symbol__icontains = query)
            ).order_by('symbol')[:20]

            # 직렬화
            # - 검색 결과를 JSON 형태로 변환

            serializer = StockSearchSerializer(stocks, many=True)

            return Response({
                'results': serializer.data,
                'count': stocks.count(),
                'query': query,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Search error for query '{query}': {e}")
            return Response({
                'error': '검색 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    




    
### 주식 상세정보 관련 API
class StockOverviewAPIView(APIView):
    """
    주식 개요 탭 데이터 API
    - 주식의 전반적인 정보 (재무비율, 기술적 지표, 분석가 의견 등)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, symbol):
        """
            ## 주식 객체 조회 헬퍼 메서드
            # - 주식 심볼로 Stock 객체 조회
            # - 존재하지 않을 경우 NotFound 발생
        """
        try:
            ## 주식정보 조회
            # - Overview 탭에 표시할 주식의 상세 정보
            stock = get_object_or_404(Stock, symbol=symbol.upper())

            ## 직렬화
            # - 주식의 모든 정보를 json화 시킴.
            serializer = OverviewTabSerializer(stock)

            return Response({
                'symbol' : symbol.upper(),
                'data' : serializer.data,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Overview data error for {symbol}: {e}")
            return Response({
                'error': f'개요 데이터 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




    
### Stock 차트 관련 view
class StockChartDataAPIView(APIView):
    """
    주식 차트 데이터 API
    - 표준 기간 옵션 (1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y, max) + 커스텀 일수 모두 지원
    - 일일/주간 가격 데이터 제공
    - 사용자 친화적이면서 유연한 API
    """
    # 표준 기간 옵션 정의
    PERIOD_MAPPING = {
        '1d': 1,       # 1일 (장중 차트용)
        '5d': 5,       # 5일
        '1m': 30,      # 1개월
        '3m': 90,      # 3개월  
        '6m': 180,     # 6개월
        '1y': 365,     # 1년
        '2y': 730,     # 2년
        '5y': 1825,    # 5년
        'max': None,   # 전체 기간
    }
    def get(self, request, symbol):
        """
        차트 데이터 GET 요청 처리
        - URL 경로에서 symbol을 받고, 쿼리 파라미터로 period와 range를 처리
        """
        try:
            # 주식 객체 조회 (없으면 404 에러)
            stock = get_object_or_404(Stock, symbol=symbol.upper())
            
            ## 파라미터 처리: 표준 기간 vs 커스텀 일수
            chart_type = request.GET.get('type', 'daily').lower()
            period_param = request.GET.get('period', '3m').lower()
            custom_days = request.GET.get('days')

            ## 날짜범위 계산
            end_date = datetime.now().date()
            start_date, period_display = self._calculate_date_range(period_param, custom_days, end_date)

            # 차트타입에 따른 데이터 조회
            if chart_type == "weekly":
                price_data = self._get_weekly_data(stock, start_date, end_date)
                serializer = WeeklyChartDataSerializer(price_data, many=True)
            else:
                price_data = self._get_daily_data(stock, start_date, end_date)
                serializer = ChartDataSerializer(price_data, many=True)
            return Response({
                'symbol': symbol.upper(),
                'period': period_display,
                'chart_type': chart_type,
                'data': serializer.data,
                'count': price_data.count(),
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat(),
                'available_periods': list(self.PERIOD_MAPPING.keys())
            })

        except ValueError as e:
            # 파라미터 관련 오류 (사용자 실수)
            logger.info(f"Invalid chart parameter: {e}, symbol: {symbol}")
            return Response({
                'error': f'잘못된 파라미터입니다: {str(e)}',
                'available_periods': list(self.PERIOD_MAPPING.keys())
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # 예상치 못한 서버 오류
            logger.error(f"Chart data error for {symbol}: {e}", exc_info=True)
            return Response({
                'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_daily_data(self, stock, start_date, end_date):
        """일간 데이터 조회"""
        queryset = DailyPrice.objects.filter(stock=stock)

        if start_date:
            queryset = queryset.filter(
                date__gte = start_date,
                date__lte = end_date
            )
        else:
            queryset = queryset.filter(date__lte = end_date)
        return queryset.order_by('-date')

    def _get_weekly_data(self, stock, start_date, end_date):
        """주간 데이터 조회"""
        queryset = WeeklyPrice.objects.filter(stock=stock)

        if start_date:
            queryset = queryset.filter(
                date__gte = start_date,
                date__lte = end_date 
            )
        else: #전체기간
            queryset = queryset.filter(date__lte = end_date)
        
        return queryset.order_by('-date')
    


    def _calculate_date_range(self, period_param, custom_days, end_date):
        """날짜 범위 계산 - 표준 기간과 커스텀 일수 모두 지원"""

        #1. 커스텀 일수가 지정된 경우 우선 적용
        if custom_days:
            try:
                days = int(custom_days)
                if days <= 0:
                    raise ValueError("일수는 1이상이어야 합니다.")
                if days >3650:
                    raise ValueError("최대 10년까지만 조회가 가능합니다.")
                start_date = end_date - timedelta(custom_days)
                return start_date, f"{days}일"
            
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError("일수는 숫자여야 합니다.")
        
        #2. 표준기간 옵션 처리
        if period_param in self.PERIOD_MAPPING:
            days = self.PERIOD_MAPPING(period_param)

            if days is None:
                return None
            else:
                start_date = end_date - timedelta(days)
                return start_date, period_param.upper()
        
        #3. 잘못된 기간 옵션
        available = ', '.join(self.PERIOD_MAPPING.keys())
        raise ValueError(f"지원하지 않는 기간입니다. 사용 가능: {available}")
    

## 3번 영역: Overview 탭 데이터 클래스 기반 API 뷰
class StockOverviewAPIView(APIView):
    """
    Overview 탭 데이터 클래스 기반 API 뷰
    - 주식의 종합 정보 제공 (가격, 재무비율, 기술적 지표, 분석가 의견 등)
    """
    
    def get(self, request, symbol):
        """
        Overview 데이터 GET 요청 처리
        - 주식의 전반적인 정보를 OverviewTabSerializer로 직렬화하여 제공
        """
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        
        # Overview 데이터 직렬화
        # - 주식의 기본 정보, 가격 정보, 재무 비율, 기술적 지표 등 포함
        serializer = OverviewTabSerializer(stock)
        
        return Response({
            'symbol': symbol.upper(),
            'tab': 'overview',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

## Balance Sheet 탭 데이터 클래스 기반 API 뷰
class StockBalanceSheetAPIView(APIView):
    """
    Balance Sheet 탭 데이터 클래스 기반 API 뷰
    - 대차대조표 데이터 제공 (연간/분기별 선택 가능)
    """
    
    def get(self, request, symbol):
        """
        대차대조표 데이터 GET 요청 처리
        - 연간/분기별 기간 선택 및 조회 개수 제한 가능
        """
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        
        # 요청 파라미터 처리 및 기본값 설정
        period = request.GET.get('period', 'annual').lower()  # 기본: 연간
        limit = int(request.GET.get('limit', 5))  # 기본: 최대 5개
        
        # 대차대조표 데이터 조회
        # - period_type으로 연간/분기별 구분
        # - 최신 데이터부터 내림차순으로 정렬 (회계연도, 분기 순)
        balance_sheets = BalanceSheet.objects.filter(
            stock=stock,
            period_type=period
        ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]
        
        # 대차대조표 데이터 직렬화
        # - 자산, 부채, 자본 관련 모든 항목 포함
        serializer = BalanceSheetTabSerializer(balance_sheets, many=True)
        
        return Response({
            'symbol': symbol.upper(),
            'tab': 'balance_sheet',
            'period': period,
            'data': serializer.data
        }, status=status.HTTP_200_OK)    

## Income Statement 탭 데이터 클래스 기반 API 뷰
class StockIncomeStatementAPIView(APIView):
    """
    Income Statement 탭 데이터 클래스 기반 API 뷰
    - 손익계산서 데이터 제공 (연간/분기별 선택 가능)
    """
    
    def get(self, request, symbol):
        """
        손익계산서 데이터 GET 요청 처리
        - 연간/분기별 기간 선택 및 조회 개수 제한 가능
        """
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        
        # 요청 파라미터 처리 및 기본값 설정
        period = request.GET.get('period', 'annual').lower()  # 기본: 연간
        limit = int(request.GET.get('limit', 5))  # 기본: 최대 5개
        
        # 손익계산서 데이터 조회
        # - period_type으로 연간/분기별 구분
        # - 최신 데이터부터 내림차순으로 정렬 (회계연도, 분기 순)
        income_statements = IncomeStatement.objects.filter(
            stock=stock,
            period_type=period
        ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]
        
        # 손익계산서 데이터 직렬화
        # - 매출, 비용, 이익 관련 모든 항목 포함
        serializer = IncomeStatementTabSerializer(income_statements, many=True)
        
        return Response({
            'symbol': symbol.upper(),
            'tab': 'income_statement',
            'period': period,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
## Cash Flow 탭 데이터 클래스 기반 API 뷰
class StockCashFlowAPIView(APIView):
    """
    Cash Flow 탭 데이터 클래스 기반 API 뷰
    - 현금흐름표 데이터 제공 (연간/분기별 선택 가능)
    """
    
    def get(self, request, symbol):
        """
        현금흐름표 데이터 GET 요청 처리
        - 연간/분기별 기간 선택 및 조회 개수 제한 가능
        """
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        
        # 요청 파라미터 처리 및 기본값 설정
        period = request.GET.get('period', 'annual').lower()  # 기본: 연간
        limit = int(request.GET.get('limit', 5))  # 기본: 최대 5개
        
        # 현금흐름표 데이터 조회
        # - period_type으로 연간/분기별 구분
        # - 최신 데이터부터 내림차순으로 정렬 (회계연도, 분기 순)
        cash_flows = CashFlowStatement.objects.filter(
            stock=stock,
            period_type=period
        ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]
        
        # 현금흐름표 데이터 직렬화
        # - 영업활동, 투자활동, 재무활동 관련 현금흐름 항목 포함
        serializer = CashFlowTabSerializer(cash_flows, many=True)
        
        return Response({
            'symbol': symbol.upper(),
            'tab': 'cash_flow',
            'period': period,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
## 통합 API 클래스 기반 뷰
class StockCompleteDataAPIView(APIView):
    """
    주식 완전 데이터 클래스 기반 API 뷰 (선택사항)
    - 헤더, 차트, 모든 탭 데이터를 한 번에 제공
    - 초기 로딩 시 사용하거나 모바일 앱에서 활용 가능
    """
    
    def get(self, request, symbol):
        """
        완전한 주식 데이터 GET 요청 처리
        - 모든 탭의 데이터를 한 번에 조회하여 제공
        - 네트워크 요청 횟수를 줄일 수 있어 모바일 환경에서 유리
        """
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        
        # 1. 헤더 데이터 (주식 기본 정보 및 현재 가격)
        header_data = StockHeaderSerializer(stock).data
        
        # 2. 최근 30일 차트 데이터 (초기 차트 표시용)
        recent_prices = DailyPrice.objects.filter(
            stock=stock
        ).order_by('-date')[:30]
        chart_data = ChartDataSerializer(recent_prices, many=True).data
        
        # 3. Overview 데이터 (종합 정보)
        overview_data = OverviewTabSerializer(stock).data
        
        # 4. 최근 5년간 연간 재무제표 데이터들
        # - 각 재무제표별로 최신 5개 연도 데이터 조회
        
        # 대차대조표 (Balance Sheet)
        balance_sheets = BalanceSheet.objects.filter(
            stock=stock, period_type='annual'
        ).order_by('-fiscal_year')[:5]
        
        # 손익계산서 (Income Statement)
        income_statements = IncomeStatement.objects.filter(
            stock=stock, period_type='annual'
        ).order_by('-fiscal_year')[:5]
        
        # 현금흐름표 (Cash Flow Statement)
        cash_flows = CashFlowStatement.objects.filter(
            stock=stock, period_type='annual'
        ).order_by('-fiscal_year')[:5]
        
        # 모든 데이터를 포함한 통합 응답
        return Response({
            'symbol': symbol.upper(),
            'header': header_data,
            'chart': chart_data,
            'overview': overview_data,
            'balance_sheets': BalanceSheetTabSerializer(balance_sheets, many=True).data,
            'income_statements': IncomeStatementTabSerializer(income_statements, many=True).data,
            'cash_flows': CashFlowTabSerializer(cash_flows, many=True).data,
        }, status=status.HTTP_200_OK)
