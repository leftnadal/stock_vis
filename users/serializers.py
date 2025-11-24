from rest_framework import serializers
from .models import User, Portfolio
from stocks.models import Stock

class StockListingField(serializers.RelatedField):
    def to_representation(self, value):
        return {
            'id': value.id,
            'stock_name': value.stock_name,
            'symbol': value.symbol
        }

class UserSerializer(serializers.ModelSerializer):
    """일반 사용자용 시리얼라이저 (제한된 정보만 포함)"""
    favorite_stock = StockListingField(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'user_name', 'nick_name', 'favorite_stock']

class PrivateUserSerializer(serializers.ModelSerializer):
    """소유자/관리자용 시리얼라이저 (개인 정보 포함)"""
    favorite_stock = StockListingField(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'user_name', 'email', 'nick_name', 'favorite_stock', 'is_superuser', 'is_staff', 'date_joined']
        read_only_fields = ['is_superuser', 'is_staff', 'date_joined']


class PortfolioSerializer(serializers.ModelSerializer):
    """포트폴리오 조회용 시리얼라이저"""
    stock_symbol = serializers.CharField(source='stock.symbol', read_only=True)
    stock_name = serializers.CharField(source='stock.stock_name', read_only=True)
    current_price = serializers.DecimalField(source='stock.real_time_price', max_digits=15, decimal_places=4, read_only=True)

    # 계산된 필드들
    total_value = serializers.ReadOnlyField()
    total_cost = serializers.ReadOnlyField()
    profit_loss = serializers.ReadOnlyField()
    profit_loss_percentage = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()

    class Meta:
        model = Portfolio
        fields = [
            'id',
            'stock_symbol',
            'stock_name',
            'quantity',
            'average_price',
            'current_price',
            'total_value',
            'total_cost',
            'profit_loss',
            'profit_loss_percentage',
            'is_profitable',
            'notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PortfolioDetailSerializer(serializers.ModelSerializer):
    """포트폴리오 상세 테이블 뷰용 시리얼라이저"""
    # 기본 정보
    stock_symbol = serializers.CharField(source='stock.symbol', read_only=True)
    stock_name = serializers.CharField(source='stock.stock_name', read_only=True)
    sector = serializers.CharField(source='stock.sector', read_only=True)
    industry = serializers.CharField(source='stock.industry', read_only=True)

    # 가격 정보
    current_price = serializers.DecimalField(source='stock.real_time_price', max_digits=15, decimal_places=4, read_only=True)
    previous_close = serializers.ReadOnlyField()

    # 일일 변동
    daily_change = serializers.ReadOnlyField()
    daily_change_percentage = serializers.ReadOnlyField()
    stock_change = serializers.DecimalField(source='stock.change', max_digits=15, decimal_places=4, read_only=True)
    stock_change_percent = serializers.CharField(source='stock.change_percent', read_only=True)

    # 보유 정보
    total_value = serializers.ReadOnlyField()
    total_cost = serializers.ReadOnlyField()
    profit_loss = serializers.ReadOnlyField()
    profit_loss_percentage = serializers.ReadOnlyField()

    # 목표/손절 정보
    target_achievement_rate = serializers.ReadOnlyField()
    distance_from_target = serializers.ReadOnlyField()
    distance_from_stop_loss = serializers.ReadOnlyField()

    # 포트폴리오 비중
    portfolio_weight = serializers.SerializerMethodField()

    # 추가 지표
    pe_ratio = serializers.DecimalField(source='stock.pe_ratio', max_digits=10, decimal_places=4, read_only=True)
    dividend_yield = serializers.DecimalField(source='stock.dividend_yield', max_digits=10, decimal_places=4, read_only=True)
    week_52_high = serializers.DecimalField(source='stock.week_52_high', max_digits=15, decimal_places=4, read_only=True)
    week_52_low = serializers.DecimalField(source='stock.week_52_low', max_digits=15, decimal_places=4, read_only=True)

    def get_portfolio_weight(self, obj):
        """포트폴리오 내 비중 계산"""
        # context에서 전체 포트폴리오 가치를 가져와서 계산
        total_portfolio_value = self.context.get('total_portfolio_value', 0)
        if total_portfolio_value > 0:
            return (obj.total_value / total_portfolio_value) * 100
        return 0

    class Meta:
        model = Portfolio
        fields = [
            'id',
            # 기본 정보
            'stock_symbol',
            'stock_name',
            'sector',
            'industry',
            # 보유 정보
            'quantity',
            'average_price',
            # 현재 가격 정보
            'current_price',
            'previous_close',
            'stock_change',
            'stock_change_percent',
            # 일일 변동 (보유수량 기준)
            'daily_change',
            'daily_change_percentage',
            # 수익률 정보
            'total_value',
            'total_cost',
            'profit_loss',
            'profit_loss_percentage',
            # 목표/손절 정보
            'target_price',
            'stop_loss_price',
            'target_achievement_rate',
            'distance_from_target',
            'distance_from_stop_loss',
            # 포트폴리오 비중
            'portfolio_weight',
            # 추가 지표
            'pe_ratio',
            'dividend_yield',
            'week_52_high',
            'week_52_low',
            # 메타 정보
            'notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PortfolioCreateUpdateSerializer(serializers.ModelSerializer):
    """포트폴리오 생성/수정용 시리얼라이저"""
    stock = serializers.CharField(max_length=20)  # 심볼을 입력받음

    class Meta:
        model = Portfolio
        fields = ['stock', 'quantity', 'average_price', 'target_price', 'stop_loss_price', 'notes']

    def validate_stock(self, value):
        """주식 심볼 유효성 검사 및 생성"""
        symbol = value.upper()

        # Stock이 이미 있는지 확인
        try:
            stock = Stock.objects.get(symbol=symbol)
            return stock
        except Stock.DoesNotExist:
            # Stock이 없으면 Alpha Vantage API로 유효성 검증 후 생성
            from stocks.views_search import validate_and_create_stock

            stock = validate_and_create_stock(symbol)
            if stock:
                return stock
            else:
                raise serializers.ValidationError(f"주식 심볼 '{value}'는 유효하지 않습니다.")

    def validate_quantity(self, value):
        """수량 유효성 검사"""
        if value <= 0:
            raise serializers.ValidationError("수량은 0보다 커야 합니다.")
        return value

    def validate_average_price(self, value):
        """평균가 유효성 검사"""
        if value <= 0:
            raise serializers.ValidationError("평균 매수가는 0보다 커야 합니다.")
        return value

    def create(self, validated_data):
        """포트폴리오 항목 생성"""
        user = self.context['request'].user
        stock = validated_data['stock']

        # 이미 해당 종목이 포트폴리오에 있는지 확인
        if Portfolio.objects.filter(user=user, stock=stock).exists():
            raise serializers.ValidationError(
                f"'{stock.symbol}' 종목은 이미 포트폴리오에 있습니다. 수정하려면 기존 항목을 수정해주세요."
            )

        return Portfolio.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        """포트폴리오 항목 수정"""
        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.average_price = validated_data.get('average_price', instance.average_price)
        instance.target_price = validated_data.get('target_price', instance.target_price)
        instance.stop_loss_price = validated_data.get('stop_loss_price', instance.stop_loss_price)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()
        return instance


class PortfolioSummarySerializer(serializers.Serializer):
    """포트폴리오 요약 정보 시리얼라이저"""
    total_stocks = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_profit_loss = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_profit_loss_percentage = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_profitable = serializers.BooleanField()