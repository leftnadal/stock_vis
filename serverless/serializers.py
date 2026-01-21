"""
Market Movers Serializers
"""
from rest_framework import serializers
from serverless.models import MarketMover, SectorETFMapping, StockSectorInfo, VolatilityBaseline


class MarketMoverSerializer(serializers.ModelSerializer):
    """
    Market Mover 직렬화

    응답 예시:
    {
        "id": 1,
        "date": "2025-01-06",
        "mover_type": "gainers",
        "rank": 1,
        "symbol": "AAPL",
        "company_name": "Apple Inc.",
        "price": "150.00",
        "change_percent": "3.50",
        "volume": 100000000,
        "open_price": "148.50",
        "high": "151.00",
        "low": "148.00",
        "rvol": "2.50",
        "rvol_display": "2.5x",
        "trend_strength": "0.85",
        "trend_display": "▲0.85",
        "data_quality": {"has_20d_volume": true, "has_ohlc": true}
    }
    """
    class Meta:
        model = MarketMover
        fields = [
            'id',
            'date',
            'mover_type',
            'rank',
            'symbol',
            'company_name',
            'price',
            'change_percent',
            'volume',
            'sector',
            'industry',
            'open_price',
            'high',
            'low',
            'rvol',
            'rvol_display',
            'trend_strength',
            'trend_display',
            'sector_alpha',
            'etf_sync_rate',
            'volatility_pct',
            'data_quality',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MarketMoverListSerializer(serializers.ModelSerializer):
    """
    Market Mover 리스트용 간소화 직렬화

    Phase 2: 5개 지표 모두 포함
    """
    # Phase 2 display 필드 추가
    sector_alpha_display = serializers.SerializerMethodField()
    etf_sync_display = serializers.SerializerMethodField()
    volatility_pct_display = serializers.SerializerMethodField()

    class Meta:
        model = MarketMover
        fields = [
            'rank',
            'symbol',
            'company_name',
            'price',
            'change_percent',
            'volume',
            # 섹터/산업 정보
            'sector',
            'industry',
            # Phase 1 지표
            'rvol_display',
            'trend_display',
            # Phase 2 지표 (raw 값)
            'sector_alpha',
            'etf_sync_rate',
            'volatility_pct',
            # Phase 2 지표 (display 값)
            'sector_alpha_display',
            'etf_sync_display',
            'volatility_pct_display',
        ]

    def get_sector_alpha_display(self, obj):
        """섹터 알파 표시 포맷"""
        from serverless.services.indicators import IndicatorCalculator
        calc = IndicatorCalculator()
        return calc.format_sector_alpha_display(obj.sector_alpha)

    def get_etf_sync_display(self, obj):
        """ETF 동행률 표시 포맷"""
        from serverless.services.indicators import IndicatorCalculator
        calc = IndicatorCalculator()
        return calc.format_etf_sync_display(obj.etf_sync_rate)

    def get_volatility_pct_display(self, obj):
        """변동성 백분위 표시 포맷"""
        from serverless.services.indicators import IndicatorCalculator
        calc = IndicatorCalculator()
        return calc.format_volatility_percentile_display(obj.volatility_pct)


class SectorETFMappingSerializer(serializers.ModelSerializer):
    """섹터-ETF 매핑 직렬화 (Phase 2용)"""
    class Meta:
        model = SectorETFMapping
        fields = '__all__'


class StockSectorInfoSerializer(serializers.ModelSerializer):
    """종목 섹터 정보 직렬화 (Phase 2용)"""
    class Meta:
        model = StockSectorInfo
        fields = '__all__'


class VolatilityBaselineSerializer(serializers.ModelSerializer):
    """변동성 백분위 직렬화 (Phase 2용)"""
    class Meta:
        model = VolatilityBaseline
        fields = '__all__'
