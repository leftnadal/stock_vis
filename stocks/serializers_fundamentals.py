"""
Fundamentals Serializers

FMP API Fundamentals 데이터를 위한 Serializer
- Key Metrics: 핵심 재무 지표
- Ratios: 재무 비율
- DCF: Discounted Cash Flow 분석
- Rating: 투자 등급
"""
from rest_framework import serializers


class KeyMetricSerializer(serializers.Serializer):
    """
    핵심 재무 지표 Serializer

    FMP API /key-metrics 응답 필드
    """
    # 기본 정보
    symbol = serializers.CharField()
    date = serializers.DateField()
    calendar_year = serializers.CharField(source='calendarYear', required=False)
    period = serializers.CharField(required=False)

    # 밸류에이션 지표
    revenue_per_share = serializers.FloatField(source='revenuePerShare', allow_null=True, required=False)
    net_income_per_share = serializers.FloatField(source='netIncomePerShare', allow_null=True, required=False)
    operating_cash_flow_per_share = serializers.FloatField(source='operatingCashFlowPerShare', allow_null=True, required=False)
    free_cash_flow_per_share = serializers.FloatField(source='freeCashFlowPerShare', allow_null=True, required=False)
    cash_per_share = serializers.FloatField(source='cashPerShare', allow_null=True, required=False)
    book_value_per_share = serializers.FloatField(source='bookValuePerShare', allow_null=True, required=False)
    tangible_book_value_per_share = serializers.FloatField(source='tangibleBookValuePerShare', allow_null=True, required=False)

    # 주가 배수
    pe_ratio = serializers.FloatField(source='peRatio', allow_null=True, required=False)
    price_to_sales_ratio = serializers.FloatField(source='priceToSalesRatio', allow_null=True, required=False)
    pocf_ratio = serializers.FloatField(source='pocfratio', allow_null=True, required=False)
    pfcf_ratio = serializers.FloatField(source='pfcfRatio', allow_null=True, required=False)
    pb_ratio = serializers.FloatField(source='pbRatio', allow_null=True, required=False)
    ptb_ratio = serializers.FloatField(source='ptbRatio', allow_null=True, required=False)
    ev_to_sales = serializers.FloatField(source='evToSales', allow_null=True, required=False)

    # 수익성 지표
    roe = serializers.FloatField(allow_null=True, required=False)
    roa = serializers.FloatField(allow_null=True, required=False)

    # 기업가치
    market_cap = serializers.FloatField(source='marketCap', allow_null=True, required=False)
    enterprise_value = serializers.FloatField(source='enterpriseValue', allow_null=True, required=False)

    # 재무건전성
    debt_to_equity = serializers.FloatField(source='debtToEquity', allow_null=True, required=False)
    net_debt_to_ebitda = serializers.FloatField(source='netDebtToEBITDA', allow_null=True, required=False)


class RatioSerializer(serializers.Serializer):
    """
    재무 비율 Serializer

    FMP API /ratios 응답 필드
    """
    # 기본 정보
    symbol = serializers.CharField()
    date = serializers.DateField()
    calendar_year = serializers.CharField(source='calendarYear', required=False)
    period = serializers.CharField(required=False)

    # 유동성 비율
    current_ratio = serializers.FloatField(source='currentRatio', allow_null=True, required=False)
    quick_ratio = serializers.FloatField(source='quickRatio', allow_null=True, required=False)
    cash_ratio = serializers.FloatField(source='cashRatio', allow_null=True, required=False)

    # 수익성 비율
    gross_profit_margin = serializers.FloatField(source='grossProfitMargin', allow_null=True, required=False)
    operating_profit_margin = serializers.FloatField(source='operatingProfitMargin', allow_null=True, required=False)
    net_profit_margin = serializers.FloatField(source='netProfitMargin', allow_null=True, required=False)
    return_on_assets = serializers.FloatField(source='returnOnAssets', allow_null=True, required=False)
    return_on_equity = serializers.FloatField(source='returnOnEquity', allow_null=True, required=False)

    # 레버리지 비율
    debt_ratio = serializers.FloatField(source='debtRatio', allow_null=True, required=False)
    debt_equity_ratio = serializers.FloatField(source='debtEquityRatio', allow_null=True, required=False)
    long_term_debt_to_capitalization = serializers.FloatField(source='longTermDebtToCapitalization', allow_null=True, required=False)

    # 효율성 비율
    asset_turnover = serializers.FloatField(source='assetTurnover', allow_null=True, required=False)
    inventory_turnover = serializers.FloatField(source='inventoryTurnover', allow_null=True, required=False)
    receivables_turnover = serializers.FloatField(source='receivablesTurnover', allow_null=True, required=False)

    # 밸류에이션 비율
    price_earnings_ratio = serializers.FloatField(source='priceEarningsRatio', allow_null=True, required=False)
    price_to_book_ratio = serializers.FloatField(source='priceToBookRatio', allow_null=True, required=False)
    price_to_sales_ratio = serializers.FloatField(source='priceToSalesRatio', allow_null=True, required=False)
    dividend_yield = serializers.FloatField(source='dividendYield', allow_null=True, required=False)


class DCFSerializer(serializers.Serializer):
    """
    DCF (Discounted Cash Flow) 분석 Serializer

    FMP API /discounted-cash-flow 응답 필드
    """
    symbol = serializers.CharField()
    date = serializers.DateField()
    dcf = serializers.FloatField(allow_null=True)  # 적정 주가
    stock_price = serializers.FloatField(source='Stock Price', allow_null=True, required=False)

    # 계산 필드
    discount_percentage = serializers.SerializerMethodField()
    recommendation = serializers.SerializerMethodField()

    def get_discount_percentage(self, obj) -> float:
        """
        현재가 대비 할인/프리미엄 비율 계산

        Returns:
            양수: 저평가 (Discount)
            음수: 고평가 (Premium)
        """
        dcf = obj.get('dcf')
        stock_price = obj.get('Stock Price')

        if not dcf or not stock_price or stock_price == 0:
            return 0.0

        return ((dcf - stock_price) / stock_price) * 100

    def get_recommendation(self, obj) -> str:
        """
        투자 추천 의견

        Returns:
            'Undervalued' (저평가), 'Overvalued' (고평가), 'Fair' (적정가)
        """
        discount = self.get_discount_percentage(obj)

        if discount > 10:
            return "Undervalued"
        elif discount < -10:
            return "Overvalued"
        else:
            return "Fair"


class RatingSerializer(serializers.Serializer):
    """
    투자 등급 Serializer

    FMP API /rating 응답 필드
    """
    symbol = serializers.CharField()
    date = serializers.DateField()

    # 등급
    rating = serializers.CharField(allow_null=True)  # A+, A, B+, C 등
    rating_score = serializers.IntegerField(source='ratingScore', allow_null=True, required=False)
    rating_recommendation = serializers.CharField(source='ratingRecommendation', allow_null=True, required=False)

    # 세부 점수
    rating_details_dcf_score = serializers.IntegerField(source='ratingDetailsDCFScore', allow_null=True, required=False)
    rating_details_roe_score = serializers.IntegerField(source='ratingDetailsROEScore', allow_null=True, required=False)
    rating_details_roa_score = serializers.IntegerField(source='ratingDetailsROAScore', allow_null=True, required=False)
    rating_details_de_score = serializers.IntegerField(source='ratingDetailsDEScore', allow_null=True, required=False)
    rating_details_pe_score = serializers.IntegerField(source='ratingDetailsPEScore', allow_null=True, required=False)
    rating_details_pb_score = serializers.IntegerField(source='ratingDetailsPBScore', allow_null=True, required=False)


class AllFundamentalsSerializer(serializers.Serializer):
    """
    전체 펀더멘털 데이터 응답 Serializer
    """
    key_metrics = KeyMetricSerializer(many=True)
    ratios = RatioSerializer(many=True)
    dcf = DCFSerializer(allow_null=True)
    rating = RatingSerializer(allow_null=True)
