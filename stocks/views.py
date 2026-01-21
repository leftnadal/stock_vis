import logging
from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.generic import TemplateView, DetailView
from django.http import Http404
from django.core.cache import cache

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement
from .serializers import (
    StockListSerializer, 
    StockHeaderSerializer, 
    StockSearchSerializer, 
    WeeklyChartDataSerializer, 
    ChartDataSerializer, 
    OverviewTabSerializer,
    BalanceSheetTabSerializer,
    IncomeStatementTabSerializer, 
    CashFlowTabSerializer,
)

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

    def get_queryset(self):
        """쿼리셋을 동적으로 필터링하여 반환"""
        queryset = Stock.objects.all()

        # 필터링 파라미터들
        # - sector: 특정 섹터의 주식들만 조회
        # - min_cap: 최소 시가총액 이상의 주식들만 조회

        sector = self.request.GET.get('sector')
        min_market_cap = self.request.GET.get('min_market_cap')

        if sector:
            queryset = queryset.filter(sector__icontains = sector)
        
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
        symbol = self.kwargs.get('symbol','').upper()
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
class StockSearchAPIView(APIView):
    """
        ### 주식 검색 API
        # - 주식 심볼이나 회사명으로 검색
        # - 자동완성 기능을 위한 간단한 정보 변환
    """

    def get(self, request):
        # 검색어 파라미터 받기
        # - 'q' 파라미터로 검색어를 받음 (예: /search/?q=apple)
        query = request.GET.get("q", "").strip()
        
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
                'count': len(stocks),
                'query': query,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Search error for query '{query}': {e}")
            return Response({
                'error': '검색 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
### Stock 차트 관련 view
class StockChartDataAPIView(APIView):
    """
    주식 차트 데이터 API (짧은 캐싱 적용)
    - 표준 기간 옵션 (1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y, max) + 커스텀 일수 모두 지원
    - 일일/주간 가격 데이터 제공
    - 로컬 DB에 없는 종목은 FMP API Fallback
    """
    ## 표준 기간 옵션 정의
    PERIOD_MAPPING = {
        '1d': 1,       # 1일 (장중 차트용)
        '5d': 5,       # 5일
        '1m': 30,      # 1개월
        '3m': 90,      # 3개월
        '6m': 180,     # 6개월
        '1y': 365,     # 1년
        '2y': 730,     # 2년
        '3y': 1095,    # 3년
        '5y': 1825,    # 5년
        'max': None,   # 전체 기간
    }
    def get(self, request, symbol):
        """
        차트 데이터 GET 요청 처리 (짧은 캐싱 적용)
        - URL 경로에서 symbol을 받고, 쿼리 파라미터로 period와 range를 처리
        - 로컬 DB에 없는 종목은 FMP API Fallback
        """
        symbol = symbol.upper()
        try:
            ## 파라미터 처리: 표준 기간 vs 커스텀 일수
            chart_type = request.GET.get('type', 'daily').lower()
            period_param = request.GET.get('period', '3m').lower()
            custom_days = request.GET.get('days')

            ## 캐싱 키 생성 (모든 파라미터 포함)
            cache_key = f"chart_{symbol}_{chart_type}_{period_param}"
            if custom_days:
                cache_key += f"_{custom_days}"

            ## 캐시에서 먼저 확인
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for chart: {symbol} ({chart_type}, {period_param})")
                return Response(cached_data, status=status.HTTP_200_OK)

            ## 날짜범위 계산
            end_date = datetime.now().date()
            start_date, period_display = self._calculate_date_range(period_param, custom_days, end_date)

            ## 로컬 DB 조회 (우선)
            stock = Stock.objects.filter(symbol=symbol).first()

            if stock:
                # 로컬 DB에서 데이터 조회
                if chart_type == "weekly":
                    price_data = self._get_weekly_data(stock, start_date, end_date)
                    serializer = WeeklyChartDataSerializer(price_data, many=True)
                else:
                    price_data = self._get_daily_data(stock, start_date, end_date)
                    serializer = ChartDataSerializer(price_data, many=True)

                response_data = {
                    'symbol': symbol,
                    'period': period_display,
                    'chart_type': chart_type,
                    'data': serializer.data,
                    'count': price_data.count(),
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat(),
                    'available_periods': list(self.PERIOD_MAPPING.keys())
                }
                cache_ttl = 60  # 1분
            else:
                # FMP API Fallback
                response_data = self._get_fmp_chart_data(symbol, period_display, chart_type, start_date, end_date)
                if response_data is None:
                    return Response({
                        'error': f'종목 {symbol}의 차트 데이터를 찾을 수 없습니다.'
                    }, status=status.HTTP_404_NOT_FOUND)
                cache_ttl = 120  # FMP는 2분

            ## 캐시에 저장
            cache.set(cache_key, response_data, cache_ttl)
            logger.info(f"Cache set for chart: {symbol} ({chart_type}, {period_param}) source={'db' if stock else 'fmp'}")

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.info(f"Invalid chart parameter: {e}, symbol: {symbol}")
            return Response({
                'error': f'잘못된 파라미터입니다: {str(e)}',
                'available_periods': list(self.PERIOD_MAPPING.keys())
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Chart data error for {symbol}: {e}", exc_info=True)
            return Response({
                'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_fmp_chart_data(self, symbol, period_display, chart_type, start_date, end_date):
        """FMP API에서 차트 데이터 조회"""
        import httpx
        from django.conf import settings

        api_key = settings.FMP_API_KEY
        if not api_key:
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://financialmodelingprep.com/stable/historical-price-eod/full",
                    params={"symbol": symbol, "apikey": api_key}
                )
                response.raise_for_status()
                fmp_data = response.json()

            if not isinstance(fmp_data, list) or len(fmp_data) == 0:
                return None

            # 날짜 필터링
            filtered_data = []
            for item in fmp_data:
                try:
                    item_date = datetime.strptime(item['date'], '%Y-%m-%d').date()
                    if start_date and item_date < start_date:
                        continue
                    if item_date > end_date:
                        continue
                    filtered_data.append(item)
                except (ValueError, KeyError):
                    continue

            # FMP 데이터를 차트 형식으로 변환
            chart_data = []
            for item in filtered_data:
                chart_data.append({
                    'time': item.get('date'),
                    'open': item.get('open', 0),
                    'high': item.get('high', 0),
                    'low': item.get('low', 0),
                    'close': item.get('close', 0),
                    'volume': item.get('volume', 0),
                })

            return {
                'symbol': symbol,
                'period': period_display,
                'chart_type': chart_type,
                'data': chart_data,
                'count': len(chart_data),
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat(),
                'available_periods': list(self.PERIOD_MAPPING.keys()),
                '_source': 'fmp_historical'
            }

        except Exception as e:
            logger.error(f"FMP chart data error for {symbol}: {e}")
            return None
    
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
                start_date = end_date - timedelta(days= days)
                return start_date, f"{days}일"
            
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError("일수는 숫자여야 합니다.")
                raise
        
        #2. 표준기간 옵션 처리
        if period_param in self.PERIOD_MAPPING:
            days = self.PERIOD_MAPPING[period_param]

            if days is None:
                return None, "전체기간"
            else:
                start_date = end_date - timedelta(days=days)
                return start_date, period_param.upper()
        
        #3. 잘못된 기간 옵션
        available = ', '.join(self.PERIOD_MAPPING.keys())
        raise ValueError(f"지원하지 않는 기간입니다. 사용 가능: {available}")
    

### 주식 상세정보 관련 API
## Overview API
class StockOverviewAPIView(APIView):
    """
    주식 개요 탭 데이터 API(캐싱 적용)
    - 주식의 전반적인 정보 (재무비율, 기술적 지표, 분석가 의견 등)
    - 로컬 DB에 없는 종목은 FMP API에서 실시간 조회
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, symbol):
        """
        ## Overview 데이터 GET 요청 처리(캐싱 적용)
        # - 주식의 전반적인 정보를 OverviewTabSerializer로 직렬화하여 제공
        # - 로컬 DB에 없는 종목은 FMP API Fallback
        """
        symbol = symbol.upper()

        ## 캐싱 키 생성
        cache_key = f"stock_overview_{symbol}"

        ## 캐시에서 먼저 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for overview: {symbol}")
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            ## 주식정보 조회 (로컬 DB 우선)
            stock = Stock.objects.filter(symbol=symbol).first()

            if stock:
                ## 직렬화
                serializer = OverviewTabSerializer(stock)
                response_data = {
                    'symbol': symbol,
                    'tab': 'overview',
                    'data': serializer.data,
                }
            else:
                ## FMP API Fallback (로컬 DB에 없는 종목)
                from .services.fmp_exchange_quotes import FMPExchangeQuotesService
                fmp_service = FMPExchangeQuotesService()
                quote_data = fmp_service.get_quote(symbol)

                if not quote_data:
                    return Response({
                        'error': f'종목 {symbol}을(를) 찾을 수 없습니다.'
                    }, status=status.HTTP_404_NOT_FOUND)

                ## FMP 데이터를 Overview 형식으로 변환
                # Stable API 필드명: changePercentage (Legacy: changesPercentage)
                change_pct = quote_data.get('changePercentage') or quote_data.get('changesPercentage', 0)
                response_data = {
                    'symbol': symbol,
                    'tab': 'overview',
                    'data': {
                        'symbol': symbol,
                        'stock_name': quote_data.get('name', symbol),
                        'real_time_price': quote_data.get('price', 0),
                        'change': quote_data.get('change', 0),
                        'change_percent': f"{change_pct:+.2f}%" if change_pct else "0.00%",
                        'previous_close': quote_data.get('previousClose', 0),
                        'open_price': quote_data.get('open', 0),
                        'high_price': quote_data.get('dayHigh', 0),
                        'low_price': quote_data.get('dayLow', 0),
                        'volume': quote_data.get('volume', 0),
                        'market_capitalization': quote_data.get('marketCap', 0),
                        'pe_ratio': quote_data.get('pe', 0),
                        'eps': quote_data.get('eps', 0),
                        'week_52_high': quote_data.get('yearHigh', 0),
                        'week_52_low': quote_data.get('yearLow', 0),
                        'exchange': quote_data.get('exchange', ''),
                        'avg_volume': quote_data.get('avgVolume') or quote_data.get('priceAvg50', 0),
                        # FMP에서 가져온 데이터임을 표시
                        '_source': 'fmp_realtime',
                    },
                }

            ## 캐시에 저장 (10분 = 600초, FMP는 2분)
            cache_ttl = 600 if stock else 120
            cache.set(cache_key, response_data, cache_ttl)
            logger.info(f"Cache set for overview: {symbol} (source: {'db' if stock else 'fmp'})")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Overview data error for {symbol}: {e}")
            return Response({
                'error': f'개요 데이터 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

## Balance Sheet 탭 데이터 클래스 기반 API 뷰
class StockBalanceSheetAPIView(APIView):
    """
    ## Balance Sheet 탭 데이터 API 뷰 (캐싱 적용)
    # - 대차대조표 데이터 제공 (연간/분기별 선택 가능)
    # - 재무제표 데이터는 자주 변하지 않으므로 1시간 캐싱 적용
    # - Fallback 체인: 로컬 DB → FMP → Alpha Vantage → yfinance
    """

    def get(self, request, symbol):
        """
        대차대조표 데이터 GET 요청 처리
        - 연간/분기별 기간 선택 및 조회 개수 제한 가능
        """
        symbol = symbol.upper()

        ## 요청 파라미터 처리 및 기본값 설정
        period = request.GET.get('period', 'annual').lower()  # 기본: 연간
        limit = int(request.GET.get('limit', 5))  # 기본: 최대 5개

        ## 캐싱 키 생성 (심볼, 기간, 제한수 포함)
        cache_key = f"balance_sheet_{symbol}_{period}_{limit}"

        ## 캐시에서 먼저 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for balance sheet: {symbol} ({period})")
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            ## 로컬 DB 조회 (우선)
            stock = Stock.objects.filter(symbol=symbol).first()
            data = []
            source = 'empty'

            if stock:
                ## 대차대조표 데이터 조회
                db_period = 'quarter' if period == 'quarterly' else period
                balance_sheets = BalanceSheet.objects.filter(
                    stock=stock,
                    period_type=db_period
                ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]

                serializer = BalanceSheetTabSerializer(balance_sheets, many=True)
                data = serializer.data
                source = 'db'

            # 로컬 DB에 없거나 데이터가 비어있으면 Fallback 체인 사용
            if not data:
                from .services.financial_statements_fallback import FinancialStatementsFallbackService
                fallback_service = FinancialStatementsFallbackService()
                data, source = fallback_service.get_balance_sheet(symbol, period, limit)

            ## 응답 데이터 구성
            response_data = {
                'symbol': symbol,
                'tab': 'balance_sheet',
                'period': period,
                'data': data,
                '_source': source
            }

            ## 캐시에 저장 (DB: 1시간, 외부 API: 10분, 빈 데이터: 5분)
            cache_ttl = 3600 if source == 'db' else (600 if source != 'empty' else 300)
            cache.set(cache_key, response_data, cache_ttl)
            logger.info(f"Cache set for balance sheet: {symbol} ({period}, source: {source})")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Balance sheet error for {symbol}: {e}")
            return Response({
                'error': f'대차대조표 데이터 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


## Income Statement 탭 데이터 클래스 기반 API 뷰
class StockIncomeStatementAPIView(APIView):
    """
    ## Income Statement 탭 데이터 API 뷰 (캐싱 적용)
    # - 손익계산서 데이터 제공 (연간/분기별 선택 가능)
    # - 재무제표 데이터는 자주 변하지 않으므로 1시간 캐싱 적용
    # - Fallback 체인: 로컬 DB → FMP → Alpha Vantage → yfinance
    """

    def get(self, request, symbol):
        """
        손익계산서 데이터 GET 요청 처리 ( 캐싱 적용 )
        - 연간/분기별 기간 선택 및 조회 개수 제한 가능
        """
        symbol = symbol.upper()

        # 요청 파라미터 처리 및 기본값 설정
        period = request.GET.get('period', 'annual').lower()  # 기본: 연간
        limit = int(request.GET.get('limit', 5))  # 기본: 최대 5개

        ## 캐싱키 생성
        cache_key = f"incomestatement_{symbol}_{period}_{limit}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for income statement: {symbol} ({period})")
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            ## 로컬 DB 조회 (우선)
            stock = Stock.objects.filter(symbol=symbol).first()
            data = []
            source = 'empty'

            if stock:
                ## 손익계산서 데이터 조회
                db_period = 'quarter' if period == 'quarterly' else period
                income_statements = IncomeStatement.objects.filter(
                    stock=stock,
                    period_type=db_period
                ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]

                serializer = IncomeStatementTabSerializer(income_statements, many=True)
                data = serializer.data
                source = 'db'

            # 로컬 DB에 없거나 데이터가 비어있으면 Fallback 체인 사용
            if not data:
                from .services.financial_statements_fallback import FinancialStatementsFallbackService
                fallback_service = FinancialStatementsFallbackService()
                data, source = fallback_service.get_income_statement(symbol, period, limit)

            ## 응답 데이터 구성
            response_data = {
                'symbol': symbol,
                'tab': 'income_statement',
                'period': period,
                'data': data,
                '_source': source
            }

            ## 캐시에 저장 (DB: 1시간, 외부 API: 10분, 빈 데이터: 5분)
            cache_ttl = 3600 if source == 'db' else (600 if source != 'empty' else 300)
            cache.set(cache_key, response_data, cache_ttl)
            logger.info(f"Cache set for income statement: {symbol} ({period}, source: {source})")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Income statement error for {symbol}: {e}")
            return Response({
                'error': f'손익계산서 데이터 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
## Cash Flow 탭 데이터 클래스 기반 API 뷰
class StockCashFlowAPIView(APIView):
    """
    Cash Flow 탭 데이터 클래스 기반 API 뷰 (캐싱적용)
    - 현금흐름표 데이터 제공 (연간/분기별 선택 가능)
    - Fallback 체인: 로컬 DB → FMP → Alpha Vantage → yfinance
    """

    def get(self, request, symbol):
        """
        현금흐름표 데이터 GET 요청 처리
        - 연간/분기별 기간 선택 및 조회 개수 제한 가능
        """
        symbol = symbol.upper()

        ## 요청 파라미터 처리 및 기본값 설정
        period = request.GET.get('period', 'annual').lower()  # 기본: 연간
        limit = int(request.GET.get('limit', 5))  # 기본: 최대 5개

        ## 캐싱키 생성
        cache_key = f"cash_flow_{symbol}_{period}_{limit}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for cash flow: {symbol} ({period})")
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            ## 로컬 DB 조회 (우선)
            stock = Stock.objects.filter(symbol=symbol).first()
            data = []
            source = 'empty'

            if stock:
                ## 현금흐름표 데이터 조회
                db_period = 'quarter' if period == 'quarterly' else period
                cash_flows = CashFlowStatement.objects.filter(
                    stock=stock,
                    period_type=db_period
                ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]

                serializer = CashFlowTabSerializer(cash_flows, many=True)
                data = serializer.data
                source = 'db'

            # 로컬 DB에 없거나 데이터가 비어있으면 Fallback 체인 사용
            if not data:
                from .services.financial_statements_fallback import FinancialStatementsFallbackService
                fallback_service = FinancialStatementsFallbackService()
                data, source = fallback_service.get_cash_flow(symbol, period, limit)

            ## 응답 데이터 구성
            response_data = {
                'symbol': symbol,
                'tab': 'cash_flow',
                'period': period,
                'data': data,
                '_source': source
            }

            ## 캐시에 저장 (DB: 1시간, 외부 API: 10분, 빈 데이터: 5분)
            cache_ttl = 3600 if source == 'db' else (600 if source != 'empty' else 300)
            cache.set(cache_key, response_data, cache_ttl)
            logger.info(f"Cache set for cash flow: {symbol} ({period}, source: {source})")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Cash flow error for {symbol}: {e}")
            return Response({
                'error': f'현금흐름표 데이터 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
