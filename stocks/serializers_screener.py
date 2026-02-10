"""
Stock Screener Serializers

FMP API Stock Screener 데이터를 위한 Serializer
조건별 종목 검색 결과 직렬화
"""
from rest_framework import serializers


class ScreenedStockSerializer(serializers.Serializer):
    """
    스크리너 검색 종목 Serializer

    FMP API /stable/company-screener 응답 필드
    """
    # 기본 정보
    symbol = serializers.CharField()
    company_name = serializers.CharField(source='companyName', required=False)
    sector = serializers.CharField(allow_null=True, required=False)
    industry = serializers.CharField(allow_null=True, required=False)
    exchange = serializers.CharField(allow_null=True, required=False)
    exchange_short_name = serializers.CharField(source='exchangeShortName', allow_null=True, required=False)
    country = serializers.CharField(allow_null=True, required=False)

    # 가격 정보
    price = serializers.FloatField(allow_null=True, required=False)
    change = serializers.FloatField(allow_null=True, required=False)
    changes_percentage = serializers.FloatField(source='changesPercentage', allow_null=True, required=False)
    last_annual_dividend = serializers.FloatField(source='lastAnnualDividend', allow_null=True, required=False)
    previous_close = serializers.FloatField(source='previousClose', allow_null=True, required=False)
    day_high = serializers.FloatField(source='dayHigh', allow_null=True, required=False)
    day_low = serializers.FloatField(source='dayLow', allow_null=True, required=False)
    open_price = serializers.FloatField(source='open', allow_null=True, required=False)

    # 기업 규모
    market_cap = serializers.FloatField(source='marketCap', allow_null=True, required=False)
    volume = serializers.IntegerField(allow_null=True, required=False)

    # 재무 지표
    beta = serializers.FloatField(allow_null=True, required=False)
    pe = serializers.FloatField(allow_null=True, required=False)
    eps = serializers.FloatField(allow_null=True, required=False)

    # Enhanced 필터용 펀더멘탈 지표 (key-metrics-ttm API에서 병합)
    pe_ratio = serializers.FloatField(allow_null=True, required=False)
    pb_ratio = serializers.FloatField(allow_null=True, required=False)
    roe = serializers.FloatField(allow_null=True, required=False)
    roa = serializers.FloatField(allow_null=True, required=False)
    debt_equity = serializers.FloatField(allow_null=True, required=False)
    current_ratio = serializers.FloatField(allow_null=True, required=False)
    profit_margin = serializers.FloatField(allow_null=True, required=False)
    eps_growth = serializers.FloatField(allow_null=True, required=False)
    revenue_growth = serializers.FloatField(allow_null=True, required=False)

    # ETF/펀드 여부
    is_etf = serializers.BooleanField(source='isEtf', default=False, required=False)
    is_fund = serializers.BooleanField(source='isFund', default=False, required=False)
    is_actively_trading = serializers.BooleanField(source='isActivelyTrading', default=True, required=False)

    # 계산 필드
    formatted_market_cap = serializers.SerializerMethodField()
    formatted_volume = serializers.SerializerMethodField()
    dividend_yield = serializers.SerializerMethodField()

    def get_formatted_market_cap(self, obj) -> str:
        """
        시가총액 포맷팅 (억/조 단위)

        Returns:
            예: '$2.5T', '$150.3B', '$5.2M'
        """
        market_cap = obj.get('marketCap')
        if not market_cap:
            return 'N/A'

        if market_cap >= 1_000_000_000_000:  # 1조 이상
            return f"${market_cap / 1_000_000_000_000:.1f}T"
        elif market_cap >= 1_000_000_000:  # 10억 이상
            return f"${market_cap / 1_000_000_000:.1f}B"
        elif market_cap >= 1_000_000:  # 100만 이상
            return f"${market_cap / 1_000_000:.1f}M"
        else:
            return f"${market_cap:.0f}"

    def get_formatted_volume(self, obj) -> str:
        """
        거래량 포맷팅

        Returns:
            예: '25.3M', '1.2B'
        """
        volume = obj.get('volume')
        if not volume:
            return 'N/A'

        if volume >= 1_000_000_000:  # 10억 이상
            return f"{volume / 1_000_000_000:.1f}B"
        elif volume >= 1_000_000:  # 100만 이상
            return f"{volume / 1_000_000:.1f}M"
        elif volume >= 1_000:  # 1천 이상
            return f"{volume / 1_000:.1f}K"
        else:
            return f"{volume:.0f}"

    def get_dividend_yield(self, obj) -> float | None:
        """
        배당률 계산 (lastAnnualDividend / price * 100)

        FMP company-screener API는 dividendYield를 직접 반환하지 않고
        lastAnnualDividend를 반환하므로 수동 계산 필요

        Returns:
            배당률 (%)
        """
        last_annual_dividend = obj.get('lastAnnualDividend')
        price = obj.get('price')

        if last_annual_dividend and price and price > 0:
            return (last_annual_dividend / price) * 100
        return None


class ScreenerRequestSerializer(serializers.Serializer):
    """
    스크리너 요청 파라미터 Serializer (입력 검증용)
    """
    # 시가총액 필터
    market_cap_more_than = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최소 시가총액 (USD)"
    )
    market_cap_lower_than = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최대 시가총액 (USD)"
    )

    # 가격 필터
    price_more_than = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최소 주가 (USD)"
    )
    price_lower_than = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최대 주가 (USD)"
    )

    # 베타 필터
    beta_more_than = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최소 베타"
    )
    beta_lower_than = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최대 베타"
    )

    # 거래량 필터
    volume_more_than = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최소 거래량"
    )
    volume_lower_than = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최대 거래량"
    )

    # 배당 필터
    dividend_more_than = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최소 배당률 (%)"
    )
    dividend_lower_than = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="최대 배당률 (%)"
    )

    # 기타 필터
    is_etf = serializers.BooleanField(
        required=False,
        allow_null=True,
        help_text="ETF 여부"
    )
    is_actively_trading = serializers.BooleanField(
        required=False,
        default=True,
        help_text="활성 거래 종목만"
    )
    sector = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=100,
        help_text="섹터 필터"
    )
    industry = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=100,
        help_text="산업 필터"
    )
    exchange = serializers.ChoiceField(
        required=False,
        allow_null=True,
        choices=['NYSE', 'NASDAQ', 'AMEX', 'ETF', 'TSX'],
        help_text="거래소 필터"
    )
    limit = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        max_value=1000,
        help_text="반환할 종목 수 (최대 1000)"
    )

    # === Enhanced 필터 (추가 API 호출 필요) ===
    pe_ratio_min = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최소 PER (Enhanced)"
    )
    pe_ratio_max = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최대 PER (Enhanced)"
    )
    roe_min = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최소 ROE (%) (Enhanced)"
    )
    roe_max = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최대 ROE (%) (Enhanced)"
    )
    eps_growth_min = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최소 EPS 성장률 (%) (Enhanced)"
    )
    eps_growth_max = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최대 EPS 성장률 (%) (Enhanced)"
    )
    revenue_growth_min = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최소 매출 성장률 (%) (Enhanced)"
    )
    revenue_growth_max = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최대 매출 성장률 (%) (Enhanced)"
    )
    debt_equity_max = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최대 부채비율 (D/E) (Enhanced)"
    )
    current_ratio_min = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최소 유동비율 (Enhanced)"
    )
    rsi_min = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
        help_text="최소 RSI (Enhanced)"
    )
    rsi_max = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
        help_text="최대 RSI (Enhanced)"
    )

    # === 클라이언트 필터 (FMP 응답에 포함) ===
    change_percent_min = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최소 변동률 (%)"
    )
    change_percent_max = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="최대 변동률 (%)"
    )

    def validate(self, attrs):
        """
        복합 필터 검증: min 값이 max 값보다 크면 에러

        - market_cap_more_than < market_cap_lower_than
        - price_more_than < price_lower_than
        - beta_more_than < beta_lower_than
        - volume_more_than < volume_lower_than
        - dividend_more_than < dividend_lower_than
        """
        errors = {}

        # 시가총액 범위 검증
        mcap_min = attrs.get('market_cap_more_than')
        mcap_max = attrs.get('market_cap_lower_than')
        if mcap_min is not None and mcap_max is not None and mcap_min > mcap_max:
            errors['market_cap_more_than'] = '최소 시가총액은 최대 시가총액보다 작아야 합니다.'

        # 주가 범위 검증
        price_min = attrs.get('price_more_than')
        price_max = attrs.get('price_lower_than')
        if price_min is not None and price_max is not None and price_min > price_max:
            errors['price_more_than'] = '최소 주가는 최대 주가보다 작아야 합니다.'

        # 베타 범위 검증
        beta_min = attrs.get('beta_more_than')
        beta_max = attrs.get('beta_lower_than')
        if beta_min is not None and beta_max is not None and beta_min > beta_max:
            errors['beta_more_than'] = '최소 베타는 최대 베타보다 작아야 합니다.'

        # 거래량 범위 검증
        vol_min = attrs.get('volume_more_than')
        vol_max = attrs.get('volume_lower_than')
        if vol_min is not None and vol_max is not None and vol_min > vol_max:
            errors['volume_more_than'] = '최소 거래량은 최대 거래량보다 작아야 합니다.'

        # 배당률 범위 검증
        div_min = attrs.get('dividend_more_than')
        div_max = attrs.get('dividend_lower_than')
        if div_min is not None and div_max is not None and div_min > div_max:
            errors['dividend_more_than'] = '최소 배당률은 최대 배당률보다 작아야 합니다.'

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class ScreenerResponseSerializer(serializers.Serializer):
    """
    스크리너 API 전체 응답 Serializer
    """
    stocks = ScreenedStockSerializer(many=True)
    total_count = serializers.IntegerField()
    filters_applied = serializers.DictField()
