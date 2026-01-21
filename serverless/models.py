from django.db import models


class MarketMover(models.Model):
    """
    Market Movers 데이터 (상승/하락/거래량 TOP 종목)

    Phase 1: RVOL, Trend Strength
    Phase 2: Sector Alpha, ETF Sync Rate, Volatility Percentile
    """
    MOVER_TYPE_CHOICES = [
        ('gainers', 'Gainers'),
        ('losers', 'Losers'),
        ('actives', 'Actives'),
    ]

    date = models.DateField(db_index=True)
    mover_type = models.CharField(max_length=10, choices=MOVER_TYPE_CHOICES)
    rank = models.IntegerField()
    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)

    # 가격 정보
    price = models.DecimalField(max_digits=12, decimal_places=2)
    change_percent = models.DecimalField(max_digits=8, decimal_places=2)
    volume = models.BigIntegerField()

    # 섹터/산업 정보
    sector = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    industry = models.CharField(max_length=100, null=True, blank=True)

    # OHLC
    open_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    high = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    low = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Phase 1 지표
    rvol = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Relative Volume: 당일 거래량 / 20일 평균"
    )
    rvol_display = models.CharField(max_length=20, null=True, blank=True)

    trend_strength = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="장중 추세 강도: (종가-시가) / (고가-저가)"
    )
    trend_display = models.CharField(max_length=20, null=True, blank=True)

    # Phase 2 지표 (나중에 추가)
    sector_alpha = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="섹터 대비 초과수익"
    )
    etf_sync_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="ETF 동행률"
    )
    volatility_pct = models.IntegerField(
        null=True,
        blank=True,
        help_text="변동성 백분위 (0-100)"
    )

    # 메타데이터
    data_quality = models.JSONField(
        default=dict,
        help_text="데이터 품질 정보 (has_20d_volume, has_ohlc 등)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_market_mover'
        unique_together = [['date', 'mover_type', 'symbol']]
        ordering = ['date', 'mover_type', 'rank']
        indexes = [
            models.Index(fields=['date', 'mover_type']),
            models.Index(fields=['symbol', 'date']),
        ]

    def __str__(self):
        return f"{self.date} {self.mover_type} #{self.rank} {self.symbol}"


class SectorETFMapping(models.Model):
    """섹터-ETF 매핑 (Phase 2 섹터 알파 계산용)"""
    sector = models.CharField(max_length=50, unique=True)
    etf_symbol = models.CharField(max_length=10)
    sector_name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_sector_etf_mapping'
        ordering = ['sector']

    def __str__(self):
        return f"{self.sector_name} → {self.etf_symbol}"


class StockSectorInfo(models.Model):
    """종목 섹터 정보 (Phase 2용)"""
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    sector = models.CharField(max_length=50, db_index=True)
    industry = models.CharField(max_length=100, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_stock_sector_info'
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} ({self.sector})"


class VolatilityBaseline(models.Model):
    """변동성 백분위 기준 데이터 (Phase 2용)"""
    symbol = models.CharField(max_length=10, db_index=True)
    date = models.DateField()

    # 20일 히스토리 기반 변동성 백분위
    volatility = models.DecimalField(max_digits=8, decimal_places=4)
    percentile = models.IntegerField(help_text="0-100 백분위")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_volatility_baseline'
        unique_together = [['symbol', 'date']]
        ordering = ['symbol', '-date']

    def __str__(self):
        return f"{self.symbol} {self.date} P{self.percentile}"
