import logging
from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.generic import TemplateView, DetailView
from django.http import Http404
from django.core.cache import cache
from django.utils import timezone

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
from .exceptions import (
    StockNotFoundError,
    ExternalAPIError,
    RateLimitError,
    DataSyncError,
    InvalidParameterError,
)
from .services.stock_sync_service import StockSyncService, SyncResult
from .services.rate_limiter import check_rate_limit, record_api_call

logger = logging.getLogger(__name__)

# 동기화 서비스 싱글톤
_sync_service = None


def get_sync_service() -> StockSyncService:
    """StockSyncService 싱글톤 반환"""
    global _sync_service
    if _sync_service is None:
        _sync_service = StockSyncService()
    return _sync_service
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
            source = 'db'

            if stock:
                # 로컬 DB에서 데이터 조회
                if chart_type == "weekly":
                    price_data = self._get_weekly_data(stock, start_date, end_date)
                    serializer = WeeklyChartDataSerializer(price_data, many=True)
                else:
                    price_data = self._get_daily_data(stock, start_date, end_date)
                    serializer = ChartDataSerializer(price_data, many=True)

                # DB에 데이터가 있으면 사용
                if price_data.count() > 0:
                    response_data = {
                        'symbol': symbol,
                        'period': period_display,
                        'chart_type': chart_type,
                        'data': serializer.data,
                        'count': price_data.count(),
                        'start_date': start_date.isoformat() if start_date else None,
                        'end_date': end_date.isoformat(),
                        'available_periods': list(self.PERIOD_MAPPING.keys()),
                        '_source': 'db'
                    }
                    cache_ttl = 60  # 1분
                else:
                    # DB에 Stock은 있지만 가격 데이터가 없으면 FMP에서 가져오기
                    logger.info(f"No price data in DB for {symbol}, fetching from FMP")
                    response_data = self._get_fmp_chart_data(symbol, period_display, chart_type, start_date, end_date)
                    if response_data is None or len(response_data.get('data', [])) == 0:
                        # FMP에서도 데이터가 없으면 빈 응답 반환
                        response_data = {
                            'symbol': symbol,
                            'period': period_display,
                            'chart_type': chart_type,
                            'data': [],
                            'count': 0,
                            'start_date': start_date.isoformat() if start_date else None,
                            'end_date': end_date.isoformat(),
                            'available_periods': list(self.PERIOD_MAPPING.keys()),
                            '_source': 'empty',
                            '_message': '해당 기간의 차트 데이터가 없습니다.'
                        }
                    cache_ttl = 120  # FMP는 2분
            else:
                # Stock 자체가 없으면 FMP API Fallback
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
    주식 개요 탭 데이터 API(캐싱 적용 + 자동 저장)
    - 주식의 전반적인 정보 (재무비율, 기술적 지표, 분석가 의견 등)
    - 로컬 DB에 없는 종목은 FMP API에서 실시간 조회 후 자동 저장
    - _meta 정보 포함 (source, synced_at, freshness, can_sync)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, symbol):
        """
        ## Overview 데이터 GET 요청 처리(캐싱 + 자동 저장 적용)
        # - 주식의 전반적인 정보를 OverviewTabSerializer로 직렬화하여 제공
        # - 로컬 DB에 없는 종목은 FMP API Fallback + 자동 저장
        """
        symbol = symbol.upper()
        sync_service = get_sync_service()

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
            source = 'db'

            # DB에 Stock이 있지만 가격 데이터가 비어있으면 자동 sync
            needs_price_sync = (
                stock and
                (not stock.real_time_price or float(stock.real_time_price) == 0) and
                (not stock.volume or stock.volume == 0)
            )

            if needs_price_sync:
                logger.info(f"Stock {symbol} exists but price data is empty, triggering auto-sync")
                sync_result = sync_service.sync_overview(symbol, force=True)
                if sync_result.success:
                    stock.refresh_from_db()
                    source = 'fmp'

            if stock:
                ## 직렬화
                serializer = OverviewTabSerializer(stock)
                response_data = {
                    'symbol': symbol,
                    'tab': 'overview',
                    'data': serializer.data,
                }
            else:
                ## FMP API Fallback + 자동 저장
                sync_result = sync_service.sync_overview(symbol, force=True)

                if sync_result.success:
                    # 저장 성공 - DB에서 다시 조회
                    stock = Stock.objects.get(symbol=symbol)
                    serializer = OverviewTabSerializer(stock)
                    response_data = {
                        'symbol': symbol,
                        'tab': 'overview',
                        'data': serializer.data,
                    }
                    source = 'fmp'
                else:
                    # 저장 실패 - FMP에서 직접 조회 (저장 없이)
                    from .services.fmp_exchange_quotes import FMPExchangeQuotesService
                    fmp_service = FMPExchangeQuotesService()
                    quote_data = fmp_service.get_quote(symbol)

                    if not quote_data:
                        raise StockNotFoundError(
                            symbol=symbol,
                            tried_sources=['db', 'fmp']
                        )

                    ## FMP 데이터를 Overview 형식으로 변환
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
                        },
                    }
                    source = 'fmp_realtime'

            ## _meta 정보 추가
            response_data['_meta'] = sync_service.get_sync_meta(symbol, 'overview', source)

            ## 캐시에 저장 (10분 = 600초, FMP는 2분)
            cache_ttl = 600 if source == 'db' else 120
            cache.set(cache_key, response_data, cache_ttl)
            logger.info(f"Cache set for overview: {symbol} (source: {source})")

            return Response(response_data, status=status.HTTP_200_OK)

        except StockNotFoundError as e:
            return e.to_response()
        except Exception as e:
            logger.error(f"Overview data error for {symbol}: {e}")
            return Response({
                'error': {
                    'code': 'OVERVIEW_ERROR',
                    'message': f'개요 데이터 조회 중 오류가 발생했습니다.',
                    'details': {
                        'symbol': symbol,
                        'original_error': str(e),
                        'can_retry': True,
                    }
                }
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


## 데이터 동기화 API
class StockSyncAPIView(APIView):
    """
    주식 데이터 동기화 API
    - 외부 API에서 데이터를 가져와 DB에 저장
    - Rate Limit 체크 포함
    - 공개 데이터 동기화이므로 인증 불필요
    """
    # 공개 주식 데이터 동기화는 인증 없이 허용
    permission_classes = []

    def post(self, request, symbol):
        """
        데이터 동기화 요청

        Request Body:
            {
                "data_types": ["overview", "price"],  # 동기화할 데이터 타입 (선택)
                "force": false  # 강제 동기화 여부 (선택)
            }

        Response:
            {
                "symbol": "AAPL",
                "status": "success" | "partial" | "failed",
                "synced": {
                    "overview": {"success": true, "source": "fmp"},
                    "price": {"success": true, "records": 30}
                },
                "next_sync_available": "2026-01-26T15:00:00Z"
            }
        """
        symbol = symbol.upper()
        sync_service = get_sync_service()

        # 요청 파라미터 파싱
        data_types = request.data.get('data_types', ['overview'])
        force = request.data.get('force', False)

        # Rate Limit 체크
        can_call, usage = check_rate_limit('fmp')
        if not can_call:
            return Response({
                'error': {
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'message': 'API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.',
                    'details': {
                        'usage': usage,
                        'can_retry': True,
                    }
                }
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # 동기화 실행
        results = {}
        all_success = True
        any_success = False

        valid_data_types = ['overview', 'price']

        for data_type in data_types:
            if data_type not in valid_data_types:
                results[data_type] = {
                    'success': False,
                    'error': f'지원하지 않는 데이터 타입: {data_type}'
                }
                continue

            try:
                if data_type == 'overview':
                    result = sync_service.sync_overview(symbol, force=force)
                elif data_type == 'price':
                    result = sync_service.sync_prices(symbol, force=force)

                # API 호출 기록
                record_api_call('fmp')

                results[data_type] = {
                    'success': result.success,
                    'source': result.source,
                    'error': result.error,
                }

                if result.success:
                    any_success = True
                else:
                    all_success = False

            except Exception as e:
                logger.error(f"Sync error for {symbol} ({data_type}): {e}")
                results[data_type] = {
                    'success': False,
                    'error': str(e)
                }
                all_success = False

        # 응답 구성
        if all_success:
            sync_status = 'success'
        elif any_success:
            sync_status = 'partial'
        else:
            sync_status = 'failed'

        return Response({
            'symbol': symbol,
            'status': sync_status,
            'synced': results,
            'next_sync_available': (timezone.now() + timedelta(minutes=5)).isoformat(),
        }, status=status.HTTP_200_OK if any_success else status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, symbol):
        """
        동기화 상태 조회

        Response:
            {
                "symbol": "AAPL",
                "sync_status": {
                    "overview": {"freshness": "fresh", "synced_at": "..."},
                    "price": {"freshness": "stale", "synced_at": "..."}
                },
                "can_sync": true
            }
        """
        symbol = symbol.upper()
        sync_service = get_sync_service()

        # Rate Limit 상태 조회
        can_call, usage = check_rate_limit('fmp')

        sync_status = {}
        for data_type in ['overview', 'price']:
            sync_status[data_type] = {
                'freshness': sync_service.get_freshness(symbol, data_type),
                **sync_service.get_sync_meta(symbol, data_type, 'unknown'),
            }

        return Response({
            'symbol': symbol,
            'sync_status': sync_status,
            'can_sync': can_call,
            'rate_limit': usage,
        }, status=status.HTTP_200_OK)
