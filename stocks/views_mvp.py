"""
MVP용 간소화된 API 엔드포인트
기존 모델을 그대로 사용하되, 필요한 데이터만 추출하여 제공
나중에 'mode' 파라미터로 요약/전체 데이터 전환 가능
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Stock, DailyPrice, BalanceSheet, IncomeStatement, CashFlowStatement
from .serializers import StockListSerializer


class StockMVPListView(APIView):
    """
    MVP용 주식 목록 API
    최소한의 정보만 제공
    """
    def get(self, request):
        # 쿼리 파라미터
        mode = request.GET.get('mode', 'summary')  # summary / full (나중에 확장)
        sector = request.GET.get('sector')
        search = request.GET.get('search')

        # 기본 쿼리셋
        queryset = Stock.objects.all()

        # 필터링
        if sector:
            queryset = queryset.filter(sector=sector)
        if search:
            queryset = queryset.filter(
                Q(symbol__icontains=search) |
                Q(stock_name__icontains=search)
            )

        # MVP: 최대 20개만
        queryset = queryset[:20]

        # 모드별 데이터 구성
        if mode == 'summary':
            # MVP 모드: 필수 필드만
            data = []
            for stock in queryset:
                data.append({
                    'symbol': stock.symbol,
                    'name': stock.stock_name,
                    'sector': stock.sector,
                    'price': float(stock.real_time_price) if stock.real_time_price else 0,
                    'change': float(stock.change) if stock.change else 0,
                    'changePercent': stock.change_percent,
                    'marketCap': float(stock.market_capitalization) if stock.market_capitalization else 0,
                })
        else:
            # 나중에 full 모드 구현
            serializer = StockListSerializer(queryset, many=True)
            data = serializer.data

        return Response({
            'mode': mode,
            'count': len(data),
            'data': data
        })


class StockMVPDetailView(APIView):
    """
    MVP용 주식 상세 정보 API
    RAG 바구니에 담을 핵심 데이터만 제공
    """
    def get(self, request, symbol):
        # 모드 파라미터 (나중에 확장용)
        mode = request.GET.get('mode', 'summary')

        # 주식 정보 조회
        stock = get_object_or_404(Stock, symbol=symbol.upper())

        if mode == 'summary':
            # MVP 모드: RAG용 핵심 데이터만
            data = {
                'basic': {
                    'symbol': stock.symbol,
                    'name': stock.stock_name,
                    'sector': stock.sector,
                    'industry': stock.industry,
                    'description': stock.description[:200] if stock.description else '',  # 200자로 제한
                    'exchange': stock.exchange,
                },
                'price': {
                    'current': float(stock.real_time_price) if stock.real_time_price else 0,
                    'change': float(stock.change) if stock.change else 0,
                    'changePercent': stock.change_percent,
                    'high52Week': float(stock.week_52_high) if stock.week_52_high else 0,
                    'low52Week': float(stock.week_52_low) if stock.week_52_low else 0,
                },
                'valuation': {
                    'marketCap': float(stock.market_capitalization) if stock.market_capitalization else 0,
                    'peRatio': float(stock.pe_ratio) if stock.pe_ratio else 0,
                    'eps': float(stock.eps) if stock.eps else 0,
                    'dividendYield': float(stock.dividend_yield) if stock.dividend_yield else 0,
                    'beta': float(stock.beta) if stock.beta else 0,
                },
                'keyMetrics': {
                    'profitMargin': float(stock.profit_margin) if stock.profit_margin else 0,
                    'returnOnEquity': float(stock.return_on_equity_ttm) if stock.return_on_equity_ttm else 0,
                    'returnOnAssets': float(stock.return_on_assets_ttm) if stock.return_on_assets_ttm else 0,
                }
            }

            # 최신 재무 데이터 1개씩만 추가
            try:
                latest_income = IncomeStatement.objects.filter(
                    stock=stock, period_type='annual'
                ).order_by('-fiscal_year').first()

                if latest_income:
                    data['financials'] = {
                        'revenue': float(latest_income.total_revenue) if latest_income.total_revenue else 0,
                        'netIncome': float(latest_income.net_income) if latest_income.net_income else 0,
                        'fiscalYear': latest_income.fiscal_year
                    }
            except:
                pass

        else:
            # 나중에 full 모드 구현 (모든 필드)
            # 기존 serializer 활용
            from .serializers import OverviewTabSerializer
            serializer = OverviewTabSerializer(stock)
            data = serializer.data

        return Response({
            'mode': mode,
            'symbol': symbol.upper(),
            'data': data
        })


class StockRAGContextView(APIView):
    """
    RAG 시스템용 컨텍스트 데이터 생성
    LLM에 전달할 구조화된 텍스트 생성
    """
    def get(self, request, symbol):
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        mode = request.GET.get('mode', 'summary')

        # 텍스트 컨텍스트 생성
        if mode == 'summary':
            context = f"""
## {stock.stock_name} ({stock.symbol})

### 기본 정보
- 섹터: {stock.sector}
- 산업: {stock.industry}
- 거래소: {stock.exchange}

### 현재 가격 정보
- 현재가: ${stock.real_time_price}
- 변동: {stock.change} ({stock.change_percent})
- 52주 최고/최저: ${stock.week_52_high} / ${stock.week_52_low}

### 가치 평가 지표
- 시가총액: ${stock.market_capitalization:,.0f}
- PER: {stock.pe_ratio}
- EPS: ${stock.eps}
- 배당수익률: {stock.dividend_yield}%
- 베타: {stock.beta}

### 수익성 지표
- 이익률: {stock.profit_margin}%
- ROE: {stock.return_on_equity_ttm}%
- ROA: {stock.return_on_assets_ttm}%
"""
        else:
            # 나중에 full 모드 구현
            context = "Full context mode - To be implemented"

        return Response({
            'symbol': symbol.upper(),
            'mode': mode,
            'context': context.strip(),
            'tokenCount': len(context.split())  # 대략적인 토큰 수
        })


class SectorListView(APIView):
    """
    섹터 목록 API
    """
    def get(self, request):
        sectors = Stock.objects.exclude(
            sector__isnull=True
        ).values_list('sector', flat=True).distinct()

        return Response({
            'sectors': list(sectors)
        })