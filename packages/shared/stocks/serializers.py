from rest_framework import serializers
from .models import (
    Stock,
    DailyPrice,
    WeeklyPrice,
    BalanceSheet,
    IncomeStatement,
    CashFlowStatement,
)


### 기본 serializer
class StockListSerializer(serializers.ModelSerializer):
    """주식 목록용 간단한 정보(대시보드, 검색등)"""

    change_percent_numeric = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()

    class Meta:
        model = Stock
        fields = [
            "symbol",
            "stock_name",
            "sector",
            "industry",
            "real_time_price",
            "volume",
            "change",
            "change_percent",
            "change_percent_numeric",
            "is_profitable",
            "market_capitalization",
        ]


class StockSearchSerializer(serializers.ModelSerializer):
    """검색용 간단한 정보"""

    change_percent_numeric = serializers.ReadOnlyField()

    class Meta:
        model = Stock
        fields = [
            "symbol",
            "stock_name",
            "sector",
            "real_time_price",
            "change_percent_numeric",
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
            "symbol",
            "stock_name",
            "sector",
            "exchange",
            "currency",
            "real_time_price",
            "price_formatted",
            "change",
            "change_percent",
            "change_percent_numeric",
            "is_profitable",
            "volume",
            "last_updated_display",
        ]

    def get_last_updated_display(self, obj):
        """업데이트 시간 표시 (예: 07/06)"""
        return obj.last_updated.strftime("%m/%d") if obj.last_updated else None

    def get_price_formatted(self, obj):
        """가격 포맷팅"""
        return f"${float(obj.real_time_price):,.2f}"


### ChartDataSerializer - 주식 차트 및 간단한 데이터 사용
class ChartDataSerializer(serializers.ModelSerializer):
    """차트 데이터(Daily / Weekly) 공통"""

    class Meta:
        model = DailyPrice
        fields = [
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]

    def to_representation(self, instance):
        """차트 라이브러리용"""
        return {
            "time": instance.date.strftime("%Y-%m-%d"),
            "open": float(instance.open_price),
            "high": float(instance.high_price),
            "low": float(instance.low_price),
            "close": float(instance.close_price),
            "volume": instance.volume,
        }


class WeeklyChartDataSerializer(ChartDataSerializer):
    """주간 차트 데이터용"""

    class Meta:
        model = WeeklyPrice
        fields = [
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]


##### 탭별 serializer
### Overview serializer
class OverviewTabSerializer(serializers.ModelSerializer):
    """Overview 탭 - 종합 정보"""

    change_percent_numeric = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()
    market_cap_formatted = serializers.SerializerMethodField()
    volume_formatted = serializers.SerializerMethodField()
    korean_overview = serializers.SerializerMethodField()
    dynamic_layers = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            # 기본 정보
            "symbol",
            "stock_name",
            "description",
            "sector",
            "industry",
            "exchange",
            "currency",
            "official_site",
            # 가격 정보
            "real_time_price",
            "change",
            "change_percent",
            "change_percent_numeric",
            "previous_close",
            "week_52_high",
            "week_52_low",
            "volume",
            "volume_formatted",
            # 시장 정보
            "market_capitalization",
            "market_cap_formatted",
            "shares_outstanding",
            # 재무 비율
            "ebitda",
            "pe_ratio",
            "peg_ratio",
            "book_value",
            "eps",
            "dividend_per_share",
            "dividend_yield",
            # 주식 성과
            "revenue_per_share_ttm",
            "profit_margin",
            "is_profitable",
            "operating_margin_ttm",
            "return_on_assets_ttm",
            "return_on_equity_ttm",
            "revenue_ttm",
            "gross_profit_ttm",
            "diluted_eps_ttm",
            "quarterly_earnings_growth_yoy",
            "quarterly_revenue_growth_yoy",
            # 기술적 지표
            "day_50_moving_average",
            "day_200_moving_average",
            "beta",
            # 분석가 정보
            "analyst_target_price",
            "analyst_rating_strong_buy",
            "analyst_rating_buy",
            "analyst_rating_hold",
            "analyst_rating_sell",
            "analyst_rating_strong_sell",
            # 한글 개요
            "korean_overview",
            # 동적 레이어 (validation + chainsight)
            "dynamic_layers",
        ]

    def get_market_cap_formatted(self, obj):
        """시가총액 포맷팅"""
        if obj.market_capitalization:
            cap = float(obj.market_capitalization)
            if cap >= 1e12:
                return f"{cap / 1e12:.1f}조"
            elif cap >= 1e8:
                return f"{cap / 1e8:.1f}억"
            return f"{cap:,.0f}"
        return None

    def get_volume_formatted(self, obj):
        """거래량 포맷팅"""
        if obj.volume:
            vol = obj.volume
            if vol >= 1e6:
                return f"{vol / 1e6:.1f}M"
            elif vol >= 1e3:
                return f"{vol / 1e3:.1f}K"
            return f"{vol:,}"
        return None

    def get_korean_overview(self, obj):
        """한글 기업 개요 (LLM 생성)"""
        try:
            ko = obj.overview_ko
            return {
                "summary": ko.summary,
                "business_model": ko.business_model,
                "competitive_edge": ko.competitive_edge,
                "risk_factors": ko.risk_factors,
                "generated_at": ko.generated_at.isoformat(),
                "llm_model": ko.llm_model,
            }
        except Exception:
            return None

    def get_dynamic_layers(self, obj):
        """동적 레이어: validation + chainsight 모델 데이터.
        6개 모델 중 하나라도 데이터가 있으면 구조체 반환, 전부 없으면 null.
        # TODO: Step 2~4에서 데이터 유입 시 prefetch_related + 캐싱 레이어 적용 필요
        """
        layers = {}
        has_any = False

        # CategorySignal (ForeignKey reverse — 여러 건)
        try:
            signals = list(obj.category_signals.all())
            if signals:
                layers["category_signals"] = [
                    {
                        "category": s.category,
                        "signal": s.signal,
                        "signal_reason": s.signal_reason,
                        "metric_count": s.metric_count,
                        "valid_metric_count": s.valid_metric_count,
                    }
                    for s in signals
                ]
                has_any = True
            else:
                layers["category_signals"] = None
        except Exception:
            layers["category_signals"] = None

        # ValidationNewsSummary (OneToOne)
        try:
            ns = obj.validation_news_summary
            layers["news_summary"] = {
                "event_count_30d": ns.event_count_30d,
                "event_count_90d": ns.event_count_90d,
                "avg_sentiment_30d": float(ns.avg_sentiment_30d)
                if ns.avg_sentiment_30d
                else None,
                "sentiment_trend": ns.sentiment_trend,
                "has_regulatory_risk": ns.has_regulatory_risk,
                "has_exec_change": ns.has_exec_change,
                "has_guidance_cut": ns.has_guidance_cut,
                "recent_highlights": ns.recent_highlights,
            }
            has_any = True
        except Exception:
            layers["news_summary"] = None

        # CompanySensitivityProfile (OneToOne)
        try:
            sp = obj.sensitivity_profile
            layers["sensitivity"] = {
                "rate_sensitivity": sp.rate_sensitivity,
                "forex_sensitivity": sp.forex_sensitivity,
                "commodity_sensitivity": sp.commodity_sensitivity,
                "regulation_type": sp.regulation_type,
                "is_regulated_industry": sp.is_regulated_industry,
                "beta": float(sp.beta) if sp.beta else None,
            }
            has_any = True
        except Exception:
            layers["sensitivity"] = None

        # CompanyGrowthStage (OneToOne)
        try:
            gs = obj.growth_stage
            layers["growth_stage"] = {
                "stage": gs.stage,
                "revenue_cagr_3y": float(gs.revenue_cagr_3y)
                if gs.revenue_cagr_3y
                else None,
                "revenue_cagr_5y": float(gs.revenue_cagr_5y)
                if gs.revenue_cagr_5y
                else None,
                "fcf_trend": gs.fcf_trend,
                "confidence": gs.confidence,
            }
            has_any = True
        except Exception:
            layers["growth_stage"] = None

        # CompanyCapitalDNA (OneToOne)
        try:
            cd = obj.capital_dna
            layers["capital_dna"] = {
                "capital_type": cd.capital_type,
                "rd_to_revenue": float(cd.rd_to_revenue) if cd.rd_to_revenue else None,
                "capex_to_revenue": float(cd.capex_to_revenue)
                if cd.capex_to_revenue
                else None,
                "dividend_payout": float(cd.dividend_payout)
                if cd.dividend_payout
                else None,
                "buyback_yield": float(cd.buyback_yield) if cd.buyback_yield else None,
            }
            has_any = True
        except Exception:
            layers["capital_dna"] = None

        # CompanyNarrativeTag (OneToOne)
        try:
            nt = obj.narrative_tag
            layers["narrative"] = {
                "primary_narrative": nt.primary_narrative,
                "theme_tags": nt.theme_tags,
                "narrative_sentiment": nt.narrative_sentiment,
                "analyst_consensus": nt.analyst_consensus,
                "analyst_revision_trend": nt.analyst_revision_trend,
            }
            has_any = True
        except Exception:
            layers["narrative"] = None

        return layers if has_any else None


### Balance sheet serializer
class BalanceSheetTabSerializer(serializers.ModelSerializer):
    """대차대조표 serializer"""

    class Meta:
        model = BalanceSheet
        fields = "__all__"


### IncomeStatement sheet serializer
class IncomeStatementTabSerializer(serializers.ModelSerializer):
    """손익계산서 serializer"""

    class Meta:
        model = IncomeStatement
        fields = "__all__"


### CashFlowStatement serializer


class CashFlowTabSerializer(serializers.ModelSerializer):
    """현금흐름표 serializer"""

    class Meta:
        model = CashFlowStatement
        fields = "__all__"


### DailyPriceSerializer - 데이터 분석 및 상세 가격 정보 표시용
class DailyPriceSerializer(serializers.ModelSerializer):
    """일일 가격 데이터"""

    stock_symbol = serializers.CharField(source="stock.symbol", read_only=True)
    daily_change = serializers.ReadOnlyField()
    high_low_spread = serializers.ReadOnlyField()

    class Meta:
        model = DailyPrice
        fields = [
            "stock_symbol",
            "currency",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "daily_change",
            "high_low_spread",
            "created_at",
        ]


class WeeklyPriceSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.CharField(source="stock.symbol", read_only=True)

    class Meta:
        model = WeeklyPrice
        fields = [
            "stock_symbol",
            "currency",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "created_at",
        ]


### 관심 주식용 serializer
class WatchListStockSerializer(serializers.ModelSerializer):
    """관심 주식용 serializer"""

    change_percent_numeric = serializers.ReadOnlyField()
    is_profitable = serializers.ReadOnlyField()
    latest_price = serializers.SerializerMethodField()
    chart_data = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            "symbol",
            "stock_name",
            "latest_price",
            "change",
            "change_percent_numeric",
            "is_profitable",
            "volume",
            "market_capitalization",
            "chart_data",
        ]

    def get_latest_price(self, obj):
        """최신 가격 정보"""
        latest = DailyPrice.objects.filter(stock=obj).order_by("-date").first()
        if latest:
            return float(latest.close_price)
        return float(obj.real_time_price or 0)

    def get_chart_data(self, obj):
        """최근 7일 차트 데이터"""
        recent_prices = DailyPrice.objects.filter(stock=obj).order_by("-date")[:7]


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
            raise serializers.ValidationError(f"{value} 주식을 찾을 수 없습니다.")


### 통합 응답용 serializer
class StockDetailPageSerializer(serializers.Serializer):
    """전체 주식 상세 페이지용 통합 데이터"""

    header = StockHeaderSerializer()
    chart_data = ChartDataSerializer(many=True)
    overview = OverviewTabSerializer()
    balance_sheets = BalanceSheetTabSerializer(many=True)
    income_statements = IncomeStatementTabSerializer(many=True)
    cash_flows = CashFlowTabSerializer(many=True)
