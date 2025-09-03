from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

class Stock(models.Model):
    """
    주식에 대한 기본정보를 보여주는 모델
    Alpha Vantage API의 GLOBAL_QUOTE와 OVERVIEW 데이터를 저장
    """

    ## 선택
    # 통화 선택
    CURRENCY_CHOICES = (
        ('USD', 'USD'),
        ('KRW', 'KRW'),
    )

    # === 기본 정보 (OVERVIEW에서 가져옴) ===
    symbol = models.CharField(max_length=20, unique=True, primary_key=True)
    asset_type = models.CharField(max_length=50, blank=True, null=True)
    stock_name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    exchange = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="USD")
    industry = models.CharField(max_length=100, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    official_site = models.URLField(blank=True, null=True)
    fiscal_year_end = models.CharField(max_length=20, blank=True, null=True)
    latest_quarter = models.DateField(blank=True, null=True)

    # === 실시간 가격 정보 (GLOBAL_QUOTE에서 가져옴) ===
    open_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0)
    high_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0)
    low_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0)
    real_time_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0)
    volume = models.BigIntegerField(default=0)
    previous_close = models.DecimalField(max_digits=15, decimal_places=4, default=0.0)
    change = models.DecimalField(max_digits=15, decimal_places=4, default=0.0)
    change_percent = models.CharField(max_length=20, blank=True, null=True)

    # === 재무 비율 정보 (OVERVIEW에서 가져옴) ===
    market_capitalization = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    ebitda = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    peg_ratio = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    book_value = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    dividend_per_share = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    dividend_yield = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    eps = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    revenue_per_share_ttm = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    profit_margin = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    operating_margin_ttm = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    return_on_assets_ttm = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    return_on_equity_ttm = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    revenue_ttm = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    gross_profit_ttm = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    diluted_eps_ttm = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    quarterly_earnings_growth_yoy = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    quarterly_revenue_growth_yoy = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)

    # === 분석가 의견 ===
    analyst_target_price = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    analyst_rating_strong_buy = models.IntegerField(blank=True, null=True)
    analyst_rating_buy = models.IntegerField(blank=True, null=True)
    analyst_rating_hold = models.IntegerField(blank=True, null=True)
    analyst_rating_sell = models.IntegerField(blank=True, null=True)
    analyst_rating_strong_sell = models.IntegerField(blank=True, null=True)

    # === 기술적 지표 ===
    trailing_pe = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    forward_pe = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    price_to_sales_ratio_ttm = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    price_to_book_ratio = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    ev_to_revenue = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    ev_to_ebitda = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    beta = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    week_52_high = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    week_52_low = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    day_50_moving_average = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    day_200_moving_average = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    shares_outstanding = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    dividend_date = models.DateField(blank=True, null=True)
    ex_dividend_date = models.DateField(blank=True, null=True)
    
    # === 메타 정보 ===
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stocks_stock'
        indexes = [
            models.Index(fields=['sector']),
            models.Index(fields=['industry']),
            models.Index(fields=['market_capitalization']),
            models.Index(fields=['last_updated']),
            models.Index(fields=['symbol', 'sector']),  # 복합 인덱스
            models.Index(fields=['real_time_price']),   # 가격 기준 조회용
        ]

    def __str__(self):
        return f"{self.stock_name} ({self.symbol})"

    @property
    def change_percent_numeric(self):
        """퍼센트 문자열을 숫자로 변환"""
        if self.change_percent:
            return float(self.change_percent.rstrip('%'))
        return 0.0

    @property
    def is_profitable(self):
        """수익성 여부 확인"""
        return self.change >= 0
    
# === 가격 데이터 기본 클래스 ===
class BasePriceData(models.Model):
    """
    모든 가격 데이터가 공유하는 기본 필드들
    Abstract 모델로 실제 테이블은 생성되지 않음
    """
    
    # 통화 선택
    CURRENCY_CHOICES = (
        ('USD', 'USD'),
        ('KRW', 'KRW'),
    )

    # 주식 (ForeignKey로 관계 설정)
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, to_field='symbol')
    # 통화
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="USD")
    # 날짜
    date = models.DateField(db_index=True)
    # 시가
    open_price = models.DecimalField(max_digits=15, decimal_places=4)
    # 고가
    high_price = models.DecimalField(max_digits=15, decimal_places=4)
    # 저가
    low_price = models.DecimalField(max_digits=15, decimal_places=4)
    # 종가
    close_price = models.DecimalField(max_digits=15, decimal_places=4)
    # 거래량
    volume = models.BigIntegerField()
    # 생성일
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['stock', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.stock.symbol} - {self.date}: ${self.close_price}"

    @property
    def daily_change(self):
        """일일 변동률 계산"""
        if self.open_price and self.open_price != 0:
            return ((self.close_price - self.open_price) / self.open_price) * 100
        return 0.0

    @property
    def high_low_spread(self):
        """고저가 스프레드 계산"""
        if self.low_price and self.low_price != 0:
            return ((self.high_price - self.low_price) / self.low_price) * 100
        return 0.0


# === 일일 가격 데이터 ===
class DailyPrice(BasePriceData):
    """
    일일 주가 데이터 (TIME_SERIES_DAILY)
    가장 세밀한 데이터, 거래일 기준
    """

    class Meta:
        db_table = 'stocks_daily_price'
        unique_together = ('stock', 'date')
        indexes = [
            models.Index(fields=['stock', 'date']),
            models.Index(fields=['date', 'volume']),  # 거래량 기준 조회용
            models.Index(fields=['stock', '-date']),  # 최신 데이터 조회용
        ]
        verbose_name = 'Daily Price'
        verbose_name_plural = 'Daily Prices'

    def __str__(self):
        return f"{self.stock.symbol} Daily - {self.date}: ${self.close_price}"


# === 주간 가격 데이터 ===
class WeeklyPrice(BasePriceData):
    """
    주간 주가 데이터 (TIME_SERIES_WEEKLY)
    주 단위 집계 데이터, 매주 금요일 기준
    """
    
    # 해당 주의 첫 거래일
    week_start_date = models.DateField(db_index=True)
    # 해당 주의 마지막 거래일  
    week_end_date = models.DateField(db_index=True)
    # 주간 평균 거래량
    average_volume = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'stocks_weekly_price'
        unique_together = ('stock', 'date')  # date는 주말 날짜 (금요일)
        indexes = [
            models.Index(fields=['stock', 'date']),
            models.Index(fields=['stock', '-date']),
        ]
        verbose_name = 'Weekly Price'
        verbose_name_plural = 'Weekly Prices'

    def __str__(self):
        return f"{self.stock.symbol} Weekly - {self.date}: ${self.close_price}"

class BasicFinancialStatement(models.Model):
    """
    재무제표들이 공유하는 기본 정보
    """

    ## 선택
    # 기간 선택
    PERIOD_CHOICES = (
        ('annual', 'Annual'),
        ('quarterly', 'Quarterly'),
    )
    # 통화 선택
    CURRENCY_CHOICES = (
        ('USD', 'USD'),
        ('KRW', 'KRW'),
    )

    ## 기본정보
    # 주식 (ForeignKey로 관계 설정)
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, to_field='symbol')
    # 공시일/발표일
    reported_date = models.DateField(db_index=True)
    # 업데이트 날짜
    created_at = models.DateTimeField(auto_now_add=True)
    # 통화
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="USD")

    ## 기간 정보
    # 기간
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, db_index=True)
    # 회계연도
    fiscal_year = models.IntegerField(db_index=True)
    # 회계분기 (분기별 데이터의 경우)
    fiscal_quarter = models.IntegerField(
        blank=True, 
        null=True, 
        db_index=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)]
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['stock', 'period_type', 'fiscal_year']),
            models.Index(fields=['reported_date']),
        ]

    
class BalanceSheet(BasicFinancialStatement):
    """
    재무제표 중 대차대조표 (연간, 분기)
    """
    
    ## 대차대조표 항목
    # 총 자산
    total_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유동자산 총계
    total_current_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 현금 및 현금성 자산
    cash_and_cash_equivalents_at_carrying_value = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 현금 및 단기투자
    cash_and_short_term_investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 재고자산
    inventory = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유동매출채권
    current_net_receivables = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 비유동자산 총계 
    total_non_current_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유형자산
    property_plant_equipment = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유형자산 감가상각누계액
    accumulated_depreciation_amortization_ppe = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 무형자산
    intangible_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업권 제외 무형자산
    intangible_assets_excluding_goodwill = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업권
    goodwill = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 투자자산 
    investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 장기투자자산
    long_term_investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 단기투자자산
    short_term_investments = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 기타유동자산
    other_current_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 기타 비유동 자산
    other_non_current_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    
    # 부채 관련
    # 총 부채
    total_liabilities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 총 유동부채
    total_current_liabilities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 매입채무 총액
    current_accounts_payable = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 선수수익(선수금)
    deferred_revenue = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 유동부채
    current_debt = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 단기차입금
    short_term_debt = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 비유동부채
    total_non_current_liabilities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자본리스부채
    capital_lease_obligations = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 장기 차입금
    long_term_debt = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 1년 내 상환해야할 장기차입금
    current_longterm_debt = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 1년 이후 상환 장기차입금
    longterm_debt_noncurrent = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 총차입금
    short_longterm_debt_total = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 기타 유동부채
    other_current_liabilities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 기타 비유동부채
    other_non_current_liabilities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    
    # 자본 관련
    # 자기자본
    total_shareholder_equity = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자사주
    treasury_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 이익잉여금
    retained_earnings = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 보통주 자본금
    common_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 발행주식 수
    common_stock_shares_outstanding = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'stocks_balance_sheet'
        unique_together = ('stock', 'period_type', 'fiscal_year', 'fiscal_quarter')
        indexes = [
            models.Index(fields=['stock', 'fiscal_year']),
            models.Index(fields=['period_type', 'fiscal_year']),
        ]

    def __str__(self):
        quarter_str = f"Q{self.fiscal_quarter}" if self.fiscal_quarter else ""
        return f"[{self.stock.symbol}] {self.period_type} {self.fiscal_year}{quarter_str}"

    
class IncomeStatement(BasicFinancialStatement):
    """
    재무제표 중 손익계산서
    Alpha Vantage INCOME_STATEMENT API 데이터 저장
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
    # 영업 이익
    operating_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 판매비 및 관리비
    selling_general_and_administrative = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 연구개발비
    research_and_development = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업 비용
    operating_expenses = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 투자수익(순)
    investment_income_net = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 순이자수익
    net_interest_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 이자수익
    interest_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 이자비용
    interest_expense = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 비이자수익
    non_interest_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 기타 영업외 수익
    other_non_operating_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 감가상각비
    depreciation = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 감가상각 및 상각비
    depreciation_and_amortization = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 세전이익
    income_before_tax = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 법인세비용
    income_tax_expense = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 이자 및 부채비용
    interest_and_debt_expense = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 계속사업순이익
    net_income_from_continuing_operations = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 포괄순이익(세후)
    comprehensive_income_net_of_tax = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # EBIT
    ebit = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # EBITDA
    ebitda = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 당기 순이익
    net_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'stocks_income_statement'
        unique_together = ('stock', 'period_type', 'fiscal_year', 'fiscal_quarter')
        indexes = [
            models.Index(fields=['stock', 'fiscal_year']),
            models.Index(fields=['period_type', 'fiscal_year']),
        ]

    def __str__(self):
        quarter_str = f"Q{self.fiscal_quarter}" if self.fiscal_quarter else ""
        return f"[{self.stock.symbol}] {self.period_type} {self.fiscal_year}{quarter_str}"

    @property
    def gross_profit_margin(self):
        """매출총이익률 계산"""
        if self.total_revenue and self.total_revenue != 0:
            return ((self.gross_profit or 0) / self.total_revenue) * 100
        return None

    @property
    def operating_profit_margin(self):
        """영업이익률 계산"""
        if self.total_revenue and self.total_revenue != 0:
            return ((self.operating_income or 0) / self.total_revenue) * 100
        return None

    @property
    def net_profit_margin(self):
        """순이익률 계산"""
        if self.total_revenue and self.total_revenue != 0:
            return ((self.net_income or 0) / self.total_revenue) * 100
        return None


class CashFlowStatement(BasicFinancialStatement):
    """
    재무제표 중 현금흐름표
    Alpha Vantage CASH_FLOW API 데이터 저장
    """
    
    ## 현금흐름표 항목
    # 영업활동으로 인한 현금흐름
    operating_cashflow = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업활동 관련 지불액
    payments_for_operating_activities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업활동 관련 수익금
    proceeds_from_operating_activities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업부채 변동액
    change_in_operating_liabilities = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 영업자산 변동액
    change_in_operating_assets = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 감가상각, 소모 및 상각비
    depreciation_depletion_and_amortization = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자본적 지출
    capital_expenditures = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 매출채권 변동액
    change_in_receivables = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 재고자산 변동액
    change_in_inventory = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 손익
    profit_loss = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 투자활동으로 인한 현금흐름
    cashflow_from_investment = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 재무활동으로 인한 현금흐름
    cashflow_from_financing = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 단기 부채 상환 관련 수익금
    proceeds_from_repayments_of_short_term_debt = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 보통주 자사주 매입 관련 지불액
    payments_for_repurchase_of_common_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자본 재매입 관련 지불액
    payments_for_repurchase_of_equity = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 우선주 재매입 관련 지불액
    payments_for_repurchase_of_preferred_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 배당금 지급액
    dividend_payout = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 보통주 배당금 지급액
    dividend_payout_common_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 우선주 배당금 지급액
    dividend_payout_preferred_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 보통주 발행 수익금
    proceeds_from_issuance_of_common_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 장기 부채 및 자본증권 발행 수익금 (순액)
    proceeds_from_issuance_of_long_term_debt_and_capital_securities_net = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 우선주 발행 수익금
    proceeds_from_issuance_of_preferred_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자본 재매입을 통한 수익금
    proceeds_from_repurchase_of_equity = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 자사주 매각 수익금
    proceeds_from_sale_of_treasury_stock = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 현금 및 현금성 자산 변동액
    change_in_cash_and_cash_equivalents = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 환율 변동으로 인한 현금흐름 변동액
    change_in_exchange_rate = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    # 순이익
    net_income = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'stocks_cash_flow_statement'
        unique_together = ('stock', 'period_type', 'fiscal_year', 'fiscal_quarter')
        indexes = [
            models.Index(fields=['stock', 'fiscal_year']),
            models.Index(fields=['period_type', 'fiscal_year']),
        ]

    def __str__(self):
        quarter_str = f"Q{self.fiscal_quarter}" if self.fiscal_quarter else ""
        return f"[{self.stock.symbol}] {self.period_type} {self.fiscal_year}{quarter_str}"

    @property
    def free_cash_flow(self):
        """잉여현금흐름 계산"""
        operating_cf = self.operating_cashflow or 0
        capex = self.capital_expenditures or 0
        return operating_cf - capex

    @property
    def cash_flow_to_revenue_ratio(self):
        """현금흐름 대비 매출 비율"""
        if self.operating_cashflow and self.operating_cashflow != 0:
            return self.operating_cashflow
        return None


# === 가격 데이터 매니저 ===
class PriceDataManager:
    """
    가격 데이터 조회를 위한 통합 매니저
    여러 테이블에서 데이터를 조회하는 헬퍼 클래스
    """
    
    @staticmethod
    def get_price_data(symbol, data_type, start_date=None, end_date=None, limit=None):
        """
        통합 가격 데이터 조회
        
        Args:
            symbol: 주식 심볼
            data_type: 'daily', 'weekly'
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 조회 제한 수
        """
        
        model_mapping = {
            'daily': DailyPrice,
            'weekly': WeeklyPrice,
        }
        
        if data_type not in model_mapping:
            raise ValueError(f"Invalid data_type: {data_type}")
        
        model_class = model_mapping[data_type]
        queryset = model_class.objects.filter(stock__symbol=symbol)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
            
        queryset = queryset.order_by('-date')
        
        if limit:
            queryset = queryset[:limit]
            
        return queryset
    
    @staticmethod
    def get_latest_price(symbol, data_type='daily'):
        """최신 가격 데이터 조회"""
        try:
            return PriceDataManager.get_price_data(symbol, data_type, limit=1).first()
        except:
            return None
    
    @staticmethod
    def get_price_range(symbol, days=30, data_type='daily'):
        """특정 기간의 가격 데이터 조회"""
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        return PriceDataManager.get_price_data(
            symbol, data_type, start_date, end_date
        )

    @staticmethod
    def get_model_class(data_type):
        """데이터 타입에 해당하는 모델 클래스 반환"""
        model_mapping = {
            'daily': DailyPrice,
            'weekly': WeeklyPrice,
        }
        
        if data_type not in model_mapping:
            raise ValueError(f"Invalid data_type: {data_type}")
        
        return model_mapping[data_type]


# === 가격 데이터 통합 뷰 (필요시) ===
class PriceDataView(models.Model):
    """
    가격 데이터 통합 뷰 (데이터베이스 뷰)
    모든 가격 데이터를 하나의 뷰로 조회할 때 사용
    읽기 전용 뷰로 실제 테이블은 아님
    """
    stock_symbol = models.CharField(max_length=20)
    data_type = models.CharField(max_length=10)
    date = models.DateField()
    open_price = models.DecimalField(max_digits=15, decimal_places=4)
    high_price = models.DecimalField(max_digits=15, decimal_places=4)
    low_price = models.DecimalField(max_digits=15, decimal_places=4)
    close_price = models.DecimalField(max_digits=15, decimal_places=4)
    volume = models.BigIntegerField()

    class Meta:
        managed = False  # Django가 이 테이블을 관리하지 않음 (DB 뷰)
        db_table = 'price_data_view'

"""
데이터베이스 뷰 생성 SQL (선택사항):

CREATE VIEW price_data_view AS
SELECT 
    stock_id as stock_symbol,
    'daily' as data_type,
    date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume
FROM stocks_daily_price
UNION ALL
SELECT 
    stock_id as stock_symbol,
    'weekly' as data_type,
    date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume
FROM stocks_weekly_price
"""