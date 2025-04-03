from django.db import models

# Create your models here.

class Stock(models.Model):
    """
    주식에 대default="USD"한 기본정보를 보여주는 모델
    주식에 대한 실시간 가격(real_time_price)는 주기적으로 업데이트 되나,
    별도의 API 로직을 통해 연동 될수 있음.

    주식의 이름, 상징, 가격, 거래소, 주식 내용 개요, 업데이트 날짜를 포함하고 있음.
    """

    ## 선택
    # 통화 선택
    CURRENCY_CHOICES = (
        ('usd', 'USD'),
        ('won', 'WON'),
    )

    # 주식이름(예: "Apple Inc")
    stock_name = models.CharField(max_length=50)
    
    # 주식 심볼(예: "AAPL" )
    symbol = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    # 거래소 이름(예: "S&P 500" )
    exchange = models.CharField(max_length=20, blank=True, null=True)

    # 섹터 (예: "금융" )
    sector = models.CharField(max_length=100, blank=True, null=True)
    
    # 실시간 가격
    # - 정밀도가 필요한 경우 Decimal Field를 사용할수 있음.
    real_time_price = models.DateTimeField(default=0.0)

    # 통화
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="USD")
    
    # 주식 내용 개요(예: 회사 소개, 사업분야 등)
    overview = models.TextField(blank=True, null=True)

    # 데이터가 언제 마지막으로 업데이트되었는지 추적하고 싶다면
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.symbol})"
    
class BasicFinancialStatement(models.Model):

    """
    밑의 지표(대차대조표, 손익계산서, 현금흐름표)들이 공유하는 기본 정보
    """

    ## 선택
    # 기간 선택
    PERIOD_CHOICES = (
        ('annual', 'Annual'),
        ('quarter', 'Quarterly'),
    )
    # 통화 선택
    CURRENCY_CHOICES = (
        ('usd', 'USD'),
        ('won', 'WON'),
    )
    ## 기본정보
    # 주식
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    # 공시일/발표일
    reported_date = models.DateField(blank=True, null=True)
    # 업데이트 날짜
    created_at = models.DateTimeField(auto_now_add=True)
    # 통화
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="USD")
    # 재무연도 종료일
    fidcal_date_ending = models.DateField(blank=True, null=True)

    ## 기간 정보
    # 기간
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    # 회계연도
    fiscal_year = models.IntegerField(blank=True, null=True)
    # 회계분기
    fiscal_quarter = models.IntegerField(blank=True, null=True)
    # 당기
    current_year = models.IntegerField(blank=True, null=True)
    # 전기
    prior_year = models.IntegerField(blank=True, null=True)

    class Meta:
        abstract = True
    

class HistoricalPrice(models.Model):
    """
    일자별 주가, 주간/월간, 시간, 분간등 여러 주기로 분류할수 있음. 
    """

    # 통화 선택
    CURRENCY_CHOICES = (
        ('usd', 'USD'),
        ('won', 'WON'),
    )

    # 주식
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='price_history')
    # 통화
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="USD")
    # 과거 날짜들
    date = models.DateField()
    # 시가
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    # 고가
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    # 저가
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    # 종가
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()

    
    class Meta:
        # 동일종목의 동일날짜에 가격 기록이 두개가 입력되지 않도록 하는 것. 
        unique_together = ('stock', 'date')

    def __str__(self):
        return f"{self.stock.symbol} - {self.date} (Close: {self.close_price})"
    
class BalanceSheet(BasicFinancialStatement):
    """
    재무제표 중 대차대조표 (연간, 분기)
    """
    
    ## 대차대조표 항목
    # 총 자산
    # - 기업이 보유한 모든 자산의 총합
    total_assets=models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유동자산 총계
    # - 1년 이내에 현금화하거나 사용할 수 있는 자산의 총액
    total_current_assets= models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 현금 및 현금성 자산( in 유동자산)
    # - 기업이 보유한 현금과 단기적으로 현금화 가능한 자산의 가치
    cash_and_cash_equivalents_at_carrying_value = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 현금 및 단기투자 ( in 유동자산)
    # - 현금과 단기투자 자산의 합계
    cash_and_short_term_investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 재고자산 ( in 유동자산)
    # - 판매를 목적으로 보유 중인 상품이나 원자재 등의 가치
    inventory = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유동매출채권  ( in 유동자산)
    # - 고객 등으로부터 단기 내에 회수할 매출채권의 총액
    current_net_receivables = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 비유동자산 총계 
    # - 1년 이상의 장기 보유 자산들의 총합
    total_non_current_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유형자산
    # - 건물, 설비, 기계 등 물리적 자산
    property_plant_equipment = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유형자산 감가상각누계액 ( in 비유동자산)
    # - 유형자산에 대한 지금까지의 감가상각 총액
    accumulated_depreciation_amortization_ppe = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 무형자산 ( in 비유동자산)
    # - 물리적 형태는 없으나 가치가 있는 자산으로, 특허, 저작권, 브랜드 등이 포함
    intangible_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업권 제외 무형자산 ( in 무형자산)
    # - 무형자산 중 영업권을 제외한 나머지 가치
    intangible_assets_excluding_goodwill = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업권 ( in 무형자산)
    # - 주로 기업 인수시 지급한 프리미엄 등으로 발생하는 무형자산
    goodwill = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 투자자산 
    # - 기타 투자 목적의 자산
    investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 장기투자 ( in 투자자산)
    # - 장기간 보유할 목적으로 투자한 자산
    long_term_investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 단기투자 ( in 투자자산)
    # - 단기적인 투자목적으로 보유한 자산
    short_term_investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 기타 비유동 자산
    # - 위에 명시되지 않은 기타 비유동자산 항목
    other_non_current_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    
    def __str__(self):
        return f"[{self.stock.symbol}] {self.period_type} {self.fiscal_year}Q{self.fiscal_quarter}"

class IncomeStatement(BasicFinancialStatement):

    """
    재무제표 중 손익계산서
    """

    ## 손익계산서 항목
    # 총매출
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 매출 총이익
    gross_profit = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 매출 원가
    cost_of_revenue = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 판매된 상품 및 서비스의 원가
    cost_of_goods_and_services_sold = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 판매비 및 관리비
    selling_General_And_Administrative = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업 비용
    operating_expenses = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 연구개발비
    research_and_development = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 감가상각 및 상각비
    depreciation_and_amortization = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 기타 영업외 수익
    other_nonOperating_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 이자비용
    interest_expense = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업 이익
    operating_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 당기 순이익
    net_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # EBITDA(기업의 영업활동 수익성을 평가하기 위해 감가상각 및 상각비를 제외한 이익)
    ebitda = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"[{self.stock.symbol}] {self.period_type} {self.fiscal_year}Q{self.fiscal_quarter}"

class CashFlowStatement(BasicFinancialStatement):

    """
    재무제표 중 현금흐름표
    """
    
    ## 현금흐름표 항목
    # 영업활동으로 인한 현금흐름
    # - 영업활동에서 발생한 순현금 흐름
    operating_cashflow = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업활동 관련 지불액
    # - 영업활동을 위한 지출액
    payments_for_operating_activities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업활동 관련 수익금
    # - 영업활동을 통해 발생한 수익(해당 데이터가 없으면 None)
    proceeds_from_operating_activities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업부채 변동액
    # - 영업활동 관련 부채의 변화액
    change_in_operating_liabilities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업자산 변동액
    # - 영업활동 관련 자산의 변화액
    change_in_operating_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 감가상각, 소모 및 상각비
    # - 유형자산 및 무형자산에 대한 감가상각, 소모, 상각 총액
    depreciation_depletion_and_amortization = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자본적 지출
    # - 설비투자 등 자산 취득에 사용된 현금
    capital_expenditures = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 매출채권 변동액
    # - 매출채권의 변화액
    change_in_receivables = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 재고자산 변동액
    # - 재고자산의 변화액
    change_in_inventory = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 손익
    # - 순이익 또는 순손실 금액
    profit_loss = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 투자활동으로 인한 현금흐름
    # - 투자활동에서 발생한 순현금 흐름
    cashflow_from_investment = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 재무활동으로 인한 현금흐름
    # - 재무활동에서 발생한 순현금 흐름
    cashflow_from_financing = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 단기 부채 상환 관련 수익금
    # - 단기 부채 상환을 통한 현금 유입
    proceeds_from_repayments_of_short_term_debt = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 보통주 자사주 매입 관련 지불액
    # - 보통주 자사주 매입에 사용된 현금 (데이터 없으면 None)
    payments_for_repurchase_of_common_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자본 재매입 관련 지불액
    # - 기타 자본 재매입에 사용된 현금 (데이터 없으면 None)
    payments_for_repurchase_of_equity = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 우선주 재매입 관련 지불액
    # - 우선주 재매입에 사용된 현금 (데이터 없으면 None)
    payments_for_repurchase_of_preferred_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 배당금 지급액
    # - 전체 배당금 지급액
    dividend_payout = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 보통주 배당금 지급액
    # - 보통주에 대한 배당금 지급액
    dividend_payout_common_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 우선주 배당금 지급액
    # - 우선주에 대한 배당금 지급액 (데이터 없으면 None)
    dividend_payout_preferred_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 보통주 발행 수익금
    # - 보통주 발행을 통해 유입된 현금 (데이터 없으면 None)
    proceeds_from_issuance_of_common_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 장기 부채 및 자본증권 발행 수익금 (순액)
    # - 장기 부채 및 자본증권 발행을 통한 순유입 현금
    proceeds_from_issuance_of_long_term_debt_and_capital_securities_net = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 우선주 발행 수익금
    # - 우선주 발행을 통한 유입 현금 (데이터 없으면 None)
    proceeds_from_issuance_of_preferred_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자본 재매입을 통한 수익금
    # - 자본 재매입에 따른 현금 유입
    proceeds_from_repurchase_of_equity = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자사주 매각 수익금
    # - 보유 자사주 매각을 통한 현금 유입 (데이터 없으면 None)
    proceeds_from_sale_of_treasury_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 현금 및 현금성 자산 변동액
    # - 기간 중 현금 및 현금성 자산의 변동액 (데이터 없으면 None)
    change_in_cash_and_cash_equivalents = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 환율 변동으로 인한 현금흐름 변동액
    # - 환율 변화에 따른 현금 흐름 변동 (데이터 없으면 None)
    change_in_exchange_rate = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 순이익
    # - 모든 활동을 합한 최종 순이익
    net_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"[{self.stock.symbol}] {self.period_type} {self.fiscal_year}Q{self.fiscal_quarter}"