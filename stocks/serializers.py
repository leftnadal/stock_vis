from rest_framework import serializers
from .models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement

### 기본 serializer
class StockListSerializer(serializers.ModelSerializer):
    """ 주식 목록용 간단한 정보(대시보드, 검색등)"""
    change_percent_numeric = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()

    class Meta:
        model = Stock
        fields = [
            'symbol',
            'stock_name', 
            'sector',
            'industry',
            'real_time_price',
            'volume',
            'change',
            'change_percent',
            'change_percent_numeric',
            'is_profitable',
            'market_capitalization',
        ]

class StockSearchSerializer(serializers.ModelSerializer):
    """ 검색용 간단한 정보"""
    change_percent_numeric = serializers.ReadOnlyField()

    class Meta:
        model = Stock
        fields = [
            'symbol',
            'stock_name',
            'sector',
            'real_time_price',
            'change_percent_numeric',
        ]

### 주식 detail page serializer
class StockHeaderSerializer(serializers.ModelSerializer):
    change_percent_numeric = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()
    last_updated_display = serializers.SerializerMethodField()
    price_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            'symbol',
            'stock_name',
            'sector',
            'exchange',
            'currency',
            'real_time_price',
            'price_formatted',
            'change',
            'change_percent',
            'change_percent_numeric',
            'is_profitable',
            'volume',
            'last_updated_display'
        ]

    def get_last_updated_display(self, obj):
        """업데이트 시간 표시 (예: 07/06)"""
        return obj.last_updated.strftime('%m/%d') if obj.last_updated else None
    
    def get_price_formatted(self, obj):
        """ 가격 포맷팅"""
        return f"${float(obj.real_time_price):,.2f}"
    

### ChartDataSerializer - 주식 차트 및 간단한 데이터 사용 
class ChartDataSerializer(serializers.ModelSerializer):
    """ 차트 데이터(Daily / Weekly) 공통"""

    class Meta:
        model = DailyPrice
        fields = [
            'date', 
            'open_price', 
            'high_price', 
            'low_price', 
            'close_price', 
            'volume',
        ]

    def to_representation(self, instance):
        """ 차트 라이브러리용"""
        return {
            'time' : instance.date.strftime('%Y-%M-%D'),
            'open' : float(instance.open_price),
            'high' : float(instance.high_price),
            'low' : float(instance.low_price),
            'close' : float(instance.close_price),
            'volume' : instance.volume
        }
class WeeklyChartDataSerializer(ChartDataSerializer):
    """주간 차트 데이터용"""
    
    class Meta:
        model = WeeklyPrice
        fields = ['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']


##### 탭별 serializer  
### Overview serializer
class OverviewTabSerializer(serializers.ModelSerializer):
    """Overview 탭 - 종합 정보"""
    
    change_percent_numeric = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()
    market_cap_formatted = serializers.SerializerMethodField()
    volume_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = [
            # 기본 정보
            'symbol', 'stock_name', 'description', 'sector', 'industry',
            'exchange', 'currency', 'official_site',
            
            # 가격 정보  
            'real_time_price', 'change', 'change_percent', 'change_percent_numeric',
            'previous_close', 'week_52_high', 'week_52_low',
            'volume', 'volume_formatted', 'avg_volume_30d',
            
            # 시장 정보
            'market_capitalization', 'market_cap_formatted',
            'shares_outstanding',
            
            # 재무 비율
            'ebidta','pe_ratio', 'peg_ratio', 'book_value', 'eps',
            'dividend_per_share', 'dividend_yield',
            
            # 주식 성과
            'revenue_per_share_ttm',
            'profit_margin',
            'operating_margin_ttm',
            'return_on_assets_ttm',
            'return_on_equity_ttm',
            'revenue_ttm',
            'gross_profit_ttm',
            'diluted_eps_ttm',
            'quarterly_earnings_growth_yoy',
            'quarterly_revenue_growth_yoy',

            # 기술적 지표
            'day_50_moving_average', 'day_200_moving_average',
            'beta', 
            
            # 분석가 정보
            'analyst_target_price',
            'analyst_rating_strong_buy', 'analyst_rating_buy',
            'analyst_rating_hold', 'analyst_rating_sell', 'analyst_rating_strong_sell'
        ]
    
    def get_market_cap_formatted(self, obj):
        """시가총액 포맷팅"""
        if obj.market_capitalization:
            cap = float(obj.market_capitalization)
            if cap >= 1e12:
                return f"{cap/1e12:.1f}조"
            elif cap >= 1e8:
                return f"{cap/1e8:.1f}억"
            return f"{cap:,.0f}"
        return None
    
    def get_volume_formatted(self, obj):
        """거래량 포맷팅"""
        if obj.volume:
            vol = obj.volume
            if vol >= 1e6:
                return f"{vol/1e6:.1f}M"
            elif vol >= 1e3:
                return f"{vol/1e3:.1f}K"
            return f"{vol:,}"
        return None

### Balance sheet serializer
class BalanceSheetTabSerializer(serializers.ModelSerializer):
    """ 대차대조표 serializer """

    class Meta:
        model = BalanceSheet
        fields = '__all__'

### IncomeStatement sheet serializer
class IncomeStatementTabSerializer(serializers.ModelSerializer):
    """ 손익계산서 serializer"""

    class Meta:
        model = IncomeStatement
        fields = '__all__'

### CashFlowStatement serializer

class CashFlowTabSerializer(serializers.ModelSerializer):
    """ 현금흐름표 serializer"""

    class Meta:
        model = CashFlowStatement
        fields = '__all__'

### DailyPriceSerializer - 데이터 분석 및 상세 가격 정보 표시용
class DailyPriceSerializer(serializers.ModelSerializer):
    """ 일일 가격 데이터 """
    stock_symbol = serializers.CharField(source='stock.symbol', read_only=True)
    daily_change = serializers.ReadOnlyField()
    high_low_spread = serializers.ReadOnlyField()

    class Meta:
        model = DailyPrice
        fields = [
            'stock_symbol',
            'currency',
            'date',
            'open_price',
            'high_price',
            'low_price', 
            'close_price',
            'volume',
            'daily_change',
            'high_low_spread',
            'created_at'
        ]

class WeeklyPriceSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.CharField(source='stock.symbol', read_only=True)

    class Meta:
        model = WeeklyPrice
        fields = [
            'stock_symbol',
            'currency',
            'date',
            'open_price',
            'high_price',
            'low_price',
            'close_price',
            'volume',
            'created_at',
        ]

### 관심 주식용 serializer
class WatchListStockSerializer(serializers.ModelSerializer):
    """ 관심 주식용 serializer"""

    change_percent_numeric = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()
    latest_price = serializers.SerializerMethodField()
    chart_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = [
            'symbol',
            'stock_name',
            'latest_price',
            'change',
            'change_percent_numeric',
            'is_profitable',
            'volume',
            'market_capitalization',
            'chart_data'
        ]
    
    def get_latest_price(self, obj):
        """최신 가격 정보"""
        latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
        if latest:
            return float(latest.close_price)
        return float(obj.real_time_price or 0)
    
    def get_chart_data(self, obj):
        """최근 7일 차트 데이터"""
        recent_prices = DailyPrice.objects.filter(
            stock=obj
        ).order_by('-date')[:7]

### Sector 성과용 serializer ( 모델이 없는 상태, ₩₩ 추후 추가)
class SectorPerformanceSerializer(serializers.Serializer):
    """섹터 성과용 (모델 없는 데이터)"""
    
    name = serializers.CharField()
    sector_code = serializers.CharField()
    change_percent = serializers.FloatField()
    stock_count = serializers.IntegerField()
    is_positive = serializers.BooleanField()

### 생성/수정용 serializer
class CreateWatchlistSerializer(serializers.Serializer):
    """관심 주식 추가용"""
    
    symbol = serializers.CharField(max_length=20)
    
    def validate_symbol(self, value):
        """주식 심볼 유효성 검사"""
        try:
            Stock.objects.get(symbol=value.upper())
            return value.upper()
        except Stock.DoesNotExist:
            raise serializers.ValidationError(f'{value} 주식을 찾을 수 없습니다.')

### 통합 응답용 serializer
class StockDetailPageSerializer(serializers.Serializer):
    """전체 주식 상세 페이지용 통합 데이터"""
    
    header = StockHeaderSerializer()
    chart_data = ChartDataSerializer(many=True)
    overview = OverviewTabSerializer()
    balance_sheets = BalanceSheetTabSerializer(many=True)
    income_statements = IncomeStatementTabSerializer(many=True)
    cash_flows = CashFlowTabSerializer(many=True)