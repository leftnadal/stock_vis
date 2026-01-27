"""
거시경제 지표 모델

FRED API, FMP API 데이터를 저장하는 모델 정의
"""
from django.db import models
from django.utils import timezone


class EconomicIndicator(models.Model):
    """
    거시경제 지표 메타데이터

    예: GDP, CPI, Unemployment Rate, Fed Funds Rate, VIX 등
    """

    class IndicatorCategory(models.TextChoices):
        GROWTH = 'growth', 'Growth'  # GDP, 산업생산
        INFLATION = 'inflation', 'Inflation'  # CPI, PCE
        EMPLOYMENT = 'employment', 'Employment'  # 실업률, NFP
        INTEREST_RATE = 'interest_rate', 'Interest Rate'  # Fed Funds, 국채금리
        VOLATILITY = 'volatility', 'Volatility'  # VIX
        SENTIMENT = 'sentiment', 'Sentiment'  # 소비자신뢰지수
        HOUSING = 'housing', 'Housing'  # 주택가격, 착공건수
        TRADE = 'trade', 'Trade'  # 무역수지

    class DataSource(models.TextChoices):
        FRED = 'fred', 'FRED API'
        FMP = 'fmp', 'FMP API'
        CALCULATED = 'calculated', 'Calculated'  # Fear/Greed Index 등

    class UpdateFrequency(models.TextChoices):
        REALTIME = 'realtime', 'Real-time'
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        YEARLY = 'yearly', 'Yearly'

    # 기본 정보
    code = models.CharField(
        max_length=50,
        primary_key=True,
        help_text='FRED 시리즈 ID 또는 커스텀 코드 (예: GDP, UNRATE, FEDFUNDS)'
    )
    name = models.CharField(max_length=200, help_text='지표 이름')
    name_ko = models.CharField(max_length=200, blank=True, help_text='한국어 지표 이름')
    description = models.TextField(blank=True, help_text='지표 설명')

    # 분류
    category = models.CharField(
        max_length=20,
        choices=IndicatorCategory.choices,
        default=IndicatorCategory.GROWTH
    )
    data_source = models.CharField(
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.FRED
    )

    # 업데이트 정보
    update_frequency = models.CharField(
        max_length=20,
        choices=UpdateFrequency.choices,
        default=UpdateFrequency.MONTHLY
    )
    last_updated = models.DateTimeField(null=True, blank=True)

    # 표시 설정
    unit = models.CharField(max_length=50, blank=True, help_text='단위 (%, $, index 등)')
    decimal_places = models.IntegerField(default=2, help_text='소수점 자릿수')
    display_order = models.IntegerField(default=0, help_text='대시보드 표시 순서')
    is_active = models.BooleanField(default=True, help_text='활성화 여부')

    # 캐싱 TTL (초)
    cache_ttl = models.IntegerField(
        default=3600,
        help_text='캐시 유효 시간 (초). 실시간=60, 일간=3600, 월간=86400'
    )

    class Meta:
        db_table = 'macro_economic_indicator'
        verbose_name = 'Economic Indicator'
        verbose_name_plural = 'Economic Indicators'
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.code}: {self.name}"


class IndicatorValue(models.Model):
    """
    경제 지표 시계열 데이터

    각 지표의 날짜별 값을 저장
    """
    indicator = models.ForeignKey(
        EconomicIndicator,
        on_delete=models.CASCADE,
        related_name='values'
    )
    date = models.DateField(help_text='데이터 기준일')
    value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        help_text='지표 값'
    )

    # 추가 정보
    period = models.CharField(
        max_length=20,
        blank=True,
        help_text='기간 정보 (예: 2024Q1, 2024-01)'
    )
    is_preliminary = models.BooleanField(
        default=False,
        help_text='속보치/잠정치 여부'
    )
    revision_date = models.DateField(
        null=True,
        blank=True,
        help_text='수정 발표일 (있는 경우)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'macro_indicator_value'
        verbose_name = 'Indicator Value'
        verbose_name_plural = 'Indicator Values'
        unique_together = ['indicator', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['indicator', '-date']),
            models.Index(fields=['-date']),
        ]

    def __str__(self):
        return f"{self.indicator.code} @ {self.date}: {self.value}"


class MarketIndex(models.Model):
    """
    시장 지수 메타데이터

    S&P 500, 나스닥, 다우, VIX, DXY 등
    """

    class IndexCategory(models.TextChoices):
        US_EQUITY = 'us_equity', 'US Equity'
        GLOBAL_EQUITY = 'global_equity', 'Global Equity'
        VOLATILITY = 'volatility', 'Volatility'
        CURRENCY = 'currency', 'Currency'
        COMMODITY = 'commodity', 'Commodity'
        BOND = 'bond', 'Bond'
        SECTOR = 'sector', 'Sector'

    symbol = models.CharField(
        max_length=20,
        primary_key=True,
        help_text='지수 심볼 (예: SPX, NDX, VIX, DXY)'
    )
    name = models.CharField(max_length=200, help_text='지수 이름')
    name_ko = models.CharField(max_length=200, blank=True, help_text='한국어 지수 이름')

    category = models.CharField(
        max_length=20,
        choices=IndexCategory.choices,
        default=IndexCategory.US_EQUITY
    )

    # FMP API 심볼 (다를 수 있음)
    fmp_symbol = models.CharField(max_length=20, blank=True)

    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'macro_market_index'
        verbose_name = 'Market Index'
        verbose_name_plural = 'Market Indices'
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.symbol}: {self.name}"


class MarketIndexPrice(models.Model):
    """
    시장 지수 가격 데이터
    """
    index = models.ForeignKey(
        MarketIndex,
        on_delete=models.CASCADE,
        related_name='prices'
    )
    date = models.DateField()
    open = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    high = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    low = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    close = models.DecimalField(max_digits=15, decimal_places=4)
    volume = models.BigIntegerField(null=True, blank=True)

    # 변동률
    change = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='전일 대비 변동'
    )
    change_percent = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='전일 대비 변동률 (%)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'macro_market_index_price'
        verbose_name = 'Market Index Price'
        verbose_name_plural = 'Market Index Prices'
        unique_together = ['index', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['index', '-date']),
        ]

    def __str__(self):
        return f"{self.index.symbol} @ {self.date}: {self.close}"


class EconomicEvent(models.Model):
    """
    경제 캘린더 이벤트

    FOMC, 고용보고서, CPI 발표 등 주요 경제 이벤트
    """

    class EventImportance(models.TextChoices):
        CRITICAL = 'critical', 'Critical'  # FOMC, NFP, CPI, GDP
        HIGH = 'high', 'High'  # 소매판매, ISM
        MEDIUM = 'medium', 'Medium'  # 주택지표, PMI
        LOW = 'low', 'Low'  # 기타

    # 기본 정보
    event_id = models.CharField(
        max_length=100,
        unique=True,
        help_text='이벤트 고유 ID'
    )
    title = models.CharField(max_length=300, help_text='이벤트 제목')
    title_ko = models.CharField(max_length=300, blank=True, help_text='한국어 제목')

    # 일정
    event_date = models.DateField(help_text='이벤트 날짜')
    event_time = models.TimeField(null=True, blank=True, help_text='발표 시간 (ET)')
    is_all_day = models.BooleanField(default=False)

    # 중요도 및 국가
    importance = models.CharField(
        max_length=20,
        choices=EventImportance.choices,
        default=EventImportance.MEDIUM
    )
    country = models.CharField(max_length=10, default='US', help_text='국가 코드')

    # 예측치/실제치
    previous_value = models.CharField(max_length=50, blank=True, help_text='이전 발표치')
    forecast_value = models.CharField(max_length=50, blank=True, help_text='예측치')
    actual_value = models.CharField(max_length=50, blank=True, help_text='실제 발표치')

    # 관련 지표
    related_indicator = models.ForeignKey(
        EconomicIndicator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        help_text='관련 경제 지표'
    )

    # 메모/설명
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'macro_economic_event'
        verbose_name = 'Economic Event'
        verbose_name_plural = 'Economic Events'
        ordering = ['event_date', 'event_time']
        indexes = [
            models.Index(fields=['event_date', 'importance']),
            models.Index(fields=['country', 'event_date']),
        ]

    def __str__(self):
        return f"{self.event_date} - {self.title}"

    @property
    def is_past(self) -> bool:
        """이벤트가 지났는지 확인"""
        return self.event_date < timezone.now().date()

    @property
    def surprise(self) -> str | None:
        """예측 대비 서프라이즈 (실제-예측)"""
        if self.actual_value and self.forecast_value:
            try:
                actual = float(self.actual_value.replace('%', '').replace('K', '000'))
                forecast = float(self.forecast_value.replace('%', '').replace('K', '000'))
                diff = actual - forecast
                if diff > 0:
                    return f"+{diff:.2f}"
                return f"{diff:.2f}"
            except ValueError:
                return None
        return None
