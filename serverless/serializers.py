"""
Serverless App Serializers

Market Movers, Market Breadth, Screener Presets, Sector Heatmap
"""
from rest_framework import serializers
from serverless.models import (
    MarketMover,
    SectorETFMapping,
    StockSectorInfo,
    VolatilityBaseline,
    CorporateAction,
    MarketBreadth,
    ScreenerPreset,
    ScreenerFilter,
    SectorPerformance,
    ScreenerAlert,
    AlertHistory,
    InvestmentThesis,
)


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
            'has_corporate_action',
            'corporate_action_type',
            'corporate_action_display',
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
            # Corporate Action 정보
            'has_corporate_action',
            'corporate_action_type',
            'corporate_action_display',
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


class CorporateActionSerializer(serializers.ModelSerializer):
    """Corporate Action 직렬화"""
    class Meta:
        model = CorporateAction
        fields = [
            'id',
            'symbol',
            'date',
            'action_type',
            'ratio',
            'dividend_amount',
            'display_text',
            'source',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ========================================
# Market Breadth Serializers
# ========================================

class MarketBreadthSerializer(serializers.ModelSerializer):
    """Market Breadth 직렬화"""
    signal_interpretation = serializers.SerializerMethodField()
    advance_percent = serializers.SerializerMethodField()

    class Meta:
        model = MarketBreadth
        fields = [
            'date',
            'advancing_count',
            'declining_count',
            'unchanged_count',
            'new_highs',
            'new_lows',
            'up_volume',
            'down_volume',
            'advance_decline_ratio',
            'advance_decline_line',
            'breadth_signal',
            'signal_interpretation',
            'new_high_low_ratio',
            'volume_ratio',
            'advance_percent',
        ]

    def get_signal_interpretation(self, obj):
        """시그널 해석 반환"""
        from serverless.services.market_breadth_service import MarketBreadthService
        service = MarketBreadthService()
        return service.get_signal_interpretation(obj.breadth_signal)

    def get_advance_percent(self, obj):
        """상승 종목 비율 (%)"""
        total = obj.advancing_count + obj.declining_count + obj.unchanged_count
        if total == 0:
            return 50.0
        return round((obj.advancing_count / total) * 100, 1)


class MarketBreadthHistorySerializer(serializers.ModelSerializer):
    """Market Breadth 히스토리용 간소화 직렬화"""
    class Meta:
        model = MarketBreadth
        fields = [
            'date',
            'advance_decline_ratio',
            'advance_decline_line',
            'breadth_signal',
            'new_highs',
            'new_lows',
        ]


# ========================================
# Screener Preset Serializers
# ========================================

class ScreenerPresetSerializer(serializers.ModelSerializer):
    """스크리너 프리셋 직렬화"""
    owner_email = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_system = serializers.SerializerMethodField()

    class Meta:
        model = ScreenerPreset
        fields = [
            'id',
            'name',
            'description',
            'description_ko',
            'category',
            'icon',
            'filters_json',
            'sort_by',
            'sort_order',
            'is_public',
            'share_code',
            'use_count',
            'view_count',  # Phase 2.1: 조회수 추가
            'last_used_at',
            'owner_email',
            'is_owner',
            'is_system',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'use_count', 'view_count', 'last_used_at', 'created_at', 'updated_at']

    def get_is_system(self, obj):
        """시스템 프리셋 여부 (user가 null이면 시스템 프리셋)"""
        return obj.user is None

    def get_owner_email(self, obj):
        """소유자 이메일 (프라이버시 보호)"""
        if obj.user:
            email = obj.user.email
            # 이메일 마스킹: abc***@domain.com
            parts = email.split('@')
            if len(parts) == 2:
                name = parts[0]
                masked = name[:3] + '***' if len(name) > 3 else name + '***'
                return f"{masked}@{parts[1]}"
        return None

    def get_is_owner(self, obj):
        """요청자가 소유자인지 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class ScreenerPresetCreateSerializer(serializers.ModelSerializer):
    """스크리너 프리셋 생성용 직렬화"""
    class Meta:
        model = ScreenerPreset
        fields = [
            'name',
            'description',
            'description_ko',
            'category',
            'icon',
            'filters_json',
            'sort_by',
            'sort_order',
            'is_public',
        ]

    def validate_filters_json(self, value):
        """필터 JSON 유효성 검증"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("filters_json must be a dictionary")
        return value

    def create(self, validated_data):
        """프리셋 생성 (사용자 자동 설정)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class ScreenerPresetListSerializer(serializers.ModelSerializer):
    """스크리너 프리셋 리스트용 직렬화"""
    is_system = serializers.SerializerMethodField()

    class Meta:
        model = ScreenerPreset
        fields = [
            'id',
            'name',
            'description_ko',
            'category',
            'icon',
            'filters_json',
            'sort_by',
            'sort_order',
            'use_count',
            'view_count',  # Phase 2.1: 조회수 추가
            'is_public',
            'share_code',  # Phase 2.1: 공유 코드 추가
            'is_system',
        ]

    def get_is_system(self, obj):
        """시스템 프리셋 여부 (user가 없으면 시스템 프리셋)"""
        return obj.user is None


# ========================================
# Screener Filter Serializers
# ========================================

class ScreenerFilterSerializer(serializers.ModelSerializer):
    """스크리너 필터 메타데이터 직렬화"""
    class Meta:
        model = ScreenerFilter
        fields = [
            'filter_id',
            'category',
            'label',
            'label_ko',
            'description',
            'description_ko',
            'data_field',
            'api_param',
            'operator_type',
            'unit',
            'min_value',
            'max_value',
            'default_min',
            'default_max',
            'step',
            'options',
            'tooltip_key',
            'is_premium',
            'is_popular',
            'fmp_supported',
        ]


class ScreenerFilterGroupSerializer(serializers.Serializer):
    """카테고리별 필터 그룹 직렬화"""
    category = serializers.CharField()
    category_label = serializers.CharField()
    filters = ScreenerFilterSerializer(many=True)


# ========================================
# Sector Heatmap Serializers
# ========================================

class SectorPerformanceSerializer(serializers.ModelSerializer):
    """섹터 성과 직렬화"""
    name_ko = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    formatted_market_cap = serializers.SerializerMethodField()

    class Meta:
        model = SectorPerformance
        fields = [
            'date',
            'sector',
            'name_ko',
            'return_pct',
            'market_cap',
            'formatted_market_cap',
            'stock_count',
            'etf_symbol',
            'etf_price',
            'etf_change_pct',
            'color',
            'top_gainers',
            'top_losers',
        ]

    def get_name_ko(self, obj):
        """한국어 섹터명"""
        from serverless.services.sector_heatmap_service import SectorHeatmapService
        return SectorHeatmapService.SECTOR_NAMES_KO.get(obj.sector, obj.sector)

    def get_color(self, obj):
        """히트맵 색상"""
        return_pct = float(obj.return_pct)
        if return_pct >= 3.0:
            return '#15803d'
        elif return_pct >= 1.5:
            return '#22c55e'
        elif return_pct >= 0.5:
            return '#86efac'
        elif return_pct >= -0.5:
            return '#fef08a'
        elif return_pct >= -1.5:
            return '#fca5a5'
        elif return_pct >= -3.0:
            return '#ef4444'
        else:
            return '#b91c1c'

    def get_formatted_market_cap(self, obj):
        """포맷팅된 시가총액"""
        cap = obj.market_cap
        if cap >= 1_000_000_000_000:
            return f"${cap / 1_000_000_000_000:.1f}T"
        elif cap >= 1_000_000_000:
            return f"${cap / 1_000_000_000:.1f}B"
        elif cap >= 1_000_000:
            return f"${cap / 1_000_000:.1f}M"
        return f"${cap:,}"


class SectorHeatmapSerializer(serializers.Serializer):
    """섹터 히트맵 전체 직렬화"""
    date = serializers.DateField()
    sectors = SectorPerformanceSerializer(many=True)
    summary = serializers.SerializerMethodField()

    def get_summary(self, obj):
        """히트맵 요약 정보"""
        sectors = obj.get('sectors', [])
        if not sectors:
            return None

        gains = [s for s in sectors if s.return_pct >= 0]
        losses = [s for s in sectors if s.return_pct < 0]
        avg_return = sum(s.return_pct for s in sectors) / len(sectors)

        return {
            'sectors_up': len(gains),
            'sectors_down': len(losses),
            'avg_return_pct': float(avg_return),
            'best_sector': sectors[0].sector if sectors else None,
            'worst_sector': sectors[-1].sector if sectors else None,
        }


# ========================================
# Paginated Screener Response Serializer
# ========================================

class PaginatedScreenerResponseSerializer(serializers.Serializer):
    """페이지네이션된 스크리너 응답"""
    results = serializers.ListField()
    count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    current_page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    filters_applied = serializers.DictField()


# ========================================
# Screener Alert Serializers (Phase 1)
# ========================================

class ScreenerAlertSerializer(serializers.ModelSerializer):
    """스크리너 알림 직렬화"""
    preset_name = serializers.SerializerMethodField()
    can_trigger = serializers.SerializerMethodField()
    cooldown_remaining_hours = serializers.SerializerMethodField()

    class Meta:
        model = ScreenerAlert
        fields = [
            'id',
            'name',
            'description',
            'preset',
            'preset_name',
            'filters_json',
            'alert_type',
            'target_count',
            'target_symbols',
            'is_active',
            'cooldown_hours',
            'last_triggered_at',
            'trigger_count',
            'notify_in_app',
            'notify_email',
            'notify_push',
            'can_trigger',
            'cooldown_remaining_hours',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_triggered_at', 'trigger_count', 'created_at', 'updated_at']

    def get_preset_name(self, obj):
        """프리셋 이름 반환"""
        if obj.preset:
            return f"{obj.preset.icon} {obj.preset.name}"
        return None

    def get_can_trigger(self, obj):
        """알림 발송 가능 여부"""
        return obj.can_trigger()

    def get_cooldown_remaining_hours(self, obj):
        """쿨다운 잔여 시간 (시간)"""
        if not obj.last_triggered_at:
            return 0

        from django.utils import timezone
        from datetime import timedelta

        cooldown_end = obj.last_triggered_at + timedelta(hours=obj.cooldown_hours)
        remaining = cooldown_end - timezone.now()

        if remaining.total_seconds() <= 0:
            return 0
        return round(remaining.total_seconds() / 3600, 1)


class ScreenerAlertCreateSerializer(serializers.ModelSerializer):
    """스크리너 알림 생성용 직렬화"""
    class Meta:
        model = ScreenerAlert
        fields = [
            'name',
            'description',
            'preset',
            'filters_json',
            'alert_type',
            'target_count',
            'target_symbols',
            'cooldown_hours',
            'notify_in_app',
            'notify_email',
            'notify_push',
        ]

    def validate(self, data):
        """알림 설정 유효성 검증"""
        preset = data.get('preset')
        filters_json = data.get('filters_json', {})

        # 프리셋 또는 필터 중 하나는 필수
        if not preset and not filters_json:
            raise serializers.ValidationError(
                "프리셋 또는 커스텀 필터 중 하나는 필수입니다."
            )

        # target_count 검증 (filter_match 타입)
        alert_type = data.get('alert_type', 'filter_match')
        if alert_type == 'filter_match' and not data.get('target_count'):
            data['target_count'] = 1  # 기본값: 1개 이상 매칭 시 알림

        return data

    def create(self, validated_data):
        """알림 생성 (사용자 자동 설정)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class AlertHistorySerializer(serializers.ModelSerializer):
    """알림 이력 직렬화"""
    alert_name = serializers.CharField(source='alert.name', read_only=True)

    class Meta:
        model = AlertHistory
        fields = [
            'id',
            'alert',
            'alert_name',
            'triggered_at',
            'matched_count',
            'matched_symbols',
            'snapshot',
            'status',
            'error_message',
            'read_at',
            'dismissed',
        ]
        read_only_fields = ['id', 'alert', 'triggered_at', 'matched_count',
                          'matched_symbols', 'snapshot', 'status', 'error_message']


class AlertHistoryListSerializer(serializers.ModelSerializer):
    """알림 이력 리스트용 간소화 직렬화"""
    alert_name = serializers.CharField(source='alert.name', read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = AlertHistory
        fields = [
            'id',
            'alert_name',
            'triggered_at',
            'matched_count',
            'status',
            'is_read',
            'dismissed',
        ]

    def get_is_read(self, obj):
        return obj.read_at is not None


# ========================================
# Investment Thesis Serializers (Phase 2)
# ========================================

class InvestmentThesisSerializer(serializers.ModelSerializer):
    """투자 테제 직렬화"""
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentThesis
        fields = [
            'id',
            'title',
            'summary',
            'filters_snapshot',
            'preset_ids',
            'key_metrics',
            'top_picks',
            'risks',
            'rationale',
            'is_public',
            'share_code',
            'view_count',
            'save_count',
            'is_owner',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'view_count', 'save_count', 'created_at', 'updated_at']

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class InvestmentThesisListSerializer(serializers.ModelSerializer):
    """투자 테제 리스트용 간소화 직렬화"""
    class Meta:
        model = InvestmentThesis
        fields = [
            'id',
            'title',
            'summary',
            'top_picks',
            'is_public',
            'view_count',
            'created_at',
        ]
